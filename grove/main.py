"""FastAPI application implementing Grove's Blossom protocol surface."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from grove import __version__
from grove.auth import AuthorizationError, validate_authorization
from grove.config import Settings
from grove.store import BlobStore, BlobTooLarge, HashMismatch, normalized_media_type

BLOB_PATH = re.compile(r"^(?P<sha256>[0-9a-f]{64})(?:\.[A-Za-z0-9]{1,16})?$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")


def _error(status_code: int, reason: str, **headers: str) -> JSONResponse:
    return JSONResponse(
        {"error": reason},
        status_code=status_code,
        headers={"X-Reason": reason, **headers},
    )


def _blob_hash(blob_path: str) -> str | None:
    match = BLOB_PATH.fullmatch(blob_path)
    return match.group("sha256") if match else None


def _integer_header(value: str | None, name: str, *, required: bool) -> int | None:
    if value is None:
        if required:
            raise ValueError(f"{name} is required")
        return None
    try:
        result = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if result < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return result


def _authorize(
    request: Request,
    authorization: str | None,
    *,
    action: str,
    blob_hash: str | None = None,
    expected_pubkey: str | None = None,
):
    settings: Settings = request.app.state.settings
    try:
        return validate_authorization(
            authorization,
            action=action,
            server_name=settings.server_name,
            blob_hash=blob_hash,
            expected_pubkey=expected_pubkey,
            clock_skew_seconds=settings.auth_clock_skew_seconds,
        )
    except AuthorizationError as exc:
        return _error(401, str(exc), **{"WWW-Authenticate": "Nostr"})


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings or Settings.from_env()
    store = BlobStore(configured.data_dir, configured.public_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store.initialize()
        yield

    app = FastAPI(
        title="Grove",
        description="A lean Blossom server for opaque, content-addressed blobs.",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.settings = configured
    app.state.store = store
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "HEAD", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=[
            "Accept-Ranges",
            "Content-Length",
            "Content-Range",
            "Content-Type",
            "X-Reason",
        ],
        max_age=86400,
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        # BUD-01 requires this header on every response, even when a client did
        # not send an Origin header (CORSMiddleware adds it only conditionally).
        response.headers.setdefault("Access-Control-Allow-Origin", "*")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        cacheable_blob = (
            request.method in {"GET", "HEAD"}
            and _blob_hash(request.url.path.lstrip("/")) is not None
            and response.status_code in {200, 206}
        )
        response.headers.setdefault(
            "Cache-Control",
            "public, max-age=31536000, immutable" if cacheable_blob else "no-store",
        )
        return response

    @app.get("/")
    async def server_information():
        return {
            "name": "Grove",
            "version": __version__,
            "description": "Blossom blobs stored simply",
            "buds": ["01", "02", "06", "11", "12"],
        }

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.head("/upload")
    async def upload_preflight(
        request: Request,
        authorization: str | None = Header(default=None),
        x_sha_256: str | None = Header(default=None, alias="X-SHA-256"),
        x_content_length: str | None = Header(default=None, alias="X-Content-Length"),
        x_content_type: str | None = Header(default=None, alias="X-Content-Type"),
    ):
        if not x_sha_256 or not HEX_64.fullmatch(x_sha_256):
            return _error(400, "X-SHA-256 must be a lowercase SHA-256 digest")
        try:
            size = _integer_header(x_content_length, "X-Content-Length", required=True)
        except ValueError as exc:
            return _error(411 if x_content_length is None else 400, str(exc))
        if size is not None and size > configured.max_blob_size:
            return _error(
                413, f"Blob exceeds the {configured.max_blob_size}-byte limit"
            )
        if not x_content_type:
            return _error(400, "X-Content-Type is required")
        auth = _authorize(request, authorization, action="upload", blob_hash=x_sha_256)
        if isinstance(auth, Response):
            return auth
        return Response(status_code=200)

    @app.put("/upload")
    async def upload_blob(
        request: Request,
        authorization: str | None = Header(default=None),
        x_sha_256: str | None = Header(default=None, alias="X-SHA-256"),
        content_length: str | None = Header(default=None, alias="Content-Length"),
    ):
        if x_sha_256 is not None and not HEX_64.fullmatch(x_sha_256):
            return _error(400, "X-SHA-256 must be a lowercase SHA-256 digest")
        auth = _authorize(request, authorization, action="upload", blob_hash=x_sha_256)
        if isinstance(auth, Response):
            return auth
        if x_sha_256 is None:
            # BUD-02 makes X-SHA-256 optional. Acorn's python-blossom client
            # supplies the digest only in the signed BUD-11 x tag, so accept
            # that unambiguous form without weakening content verification.
            if len(auth.blob_hashes) != 1:
                return _error(
                    401,
                    "Upload authorization must contain exactly one blob hash when X-SHA-256 is absent",
                )
            x_sha_256 = auth.blob_hashes[0]
        try:
            expected_size = _integer_header(
                content_length, "Content-Length", required=False
            )
        except ValueError as exc:
            return _error(400, str(exc))
        if expected_size is not None and expected_size > configured.max_blob_size:
            return _error(
                413, f"Blob exceeds the {configured.max_blob_size}-byte limit"
            )
        try:
            descriptor, created = await store.upload(
                request.stream(),
                expected_hash=x_sha_256,
                media_type=normalized_media_type(request.headers.get("content-type")),
                owner_pubkey=auth.pubkey,
                max_size=configured.max_blob_size,
                expected_size=expected_size,
            )
        except BlobTooLarge as exc:
            return _error(413, str(exc))
        except HashMismatch as exc:
            return _error(409, str(exc))
        except ValueError as exc:
            return _error(400, str(exc))
        return JSONResponse(descriptor, status_code=201 if created else 200)

    @app.get("/list/{pubkey}")
    async def list_blobs(
        request: Request,
        pubkey: str,
        authorization: str | None = Header(default=None),
        cursor: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
        since: int | None = Query(default=None, ge=0),
        until: int | None = Query(default=None, ge=0),
    ):
        if not HEX_64.fullmatch(pubkey):
            return _error(400, "Public key must be lowercase hexadecimal")
        if cursor is not None and not HEX_64.fullmatch(cursor):
            return _error(400, "Cursor must be a lowercase SHA-256 digest")
        auth = _authorize(
            request,
            authorization,
            action="list",
            expected_pubkey=pubkey,
        )
        if isinstance(auth, Response):
            return auth
        return store.list_for_owner(
            pubkey,
            cursor=cursor,
            limit=limit,
            since=since,
            until=until,
        )

    @app.get("/{blob_path}")
    async def get_blob(blob_path: str):
        sha256 = _blob_hash(blob_path)
        if sha256 is None:
            return _error(400, "Blob path must contain a lowercase SHA-256 digest")
        blob = store.get(sha256)
        if blob is None:
            return _error(404, "Blob not found")
        return FileResponse(
            store.path_for(sha256),
            media_type=blob["media_type"],
            headers={"Accept-Ranges": "bytes"},
        )

    @app.head("/{blob_path}")
    async def head_blob(blob_path: str):
        sha256 = _blob_hash(blob_path)
        if sha256 is None:
            return _error(400, "Blob path must contain a lowercase SHA-256 digest")
        blob = store.get(sha256)
        if blob is None:
            return _error(404, "Blob not found")
        return Response(
            status_code=200,
            media_type=blob["media_type"],
            headers={
                "Content-Length": str(blob["size"]),
                "Accept-Ranges": "bytes",
            },
        )

    @app.delete("/{blob_path}")
    async def delete_blob(
        request: Request,
        blob_path: str,
        authorization: str | None = Header(default=None),
    ):
        sha256 = _blob_hash(blob_path)
        if sha256 is None:
            return _error(400, "Blob path must contain a lowercase SHA-256 digest")
        auth = _authorize(request, authorization, action="delete", blob_hash=sha256)
        if isinstance(auth, Response):
            return auth
        if not store.delete_for_owner(sha256, auth.pubkey):
            return _error(404, "Blob not found for this owner")
        return Response(status_code=204)

    return app


app = create_app()
