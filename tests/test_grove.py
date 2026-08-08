from __future__ import annotations

import base64
import hashlib
import json
import time

from coincurve import PrivateKey, PublicKeyXOnly
from starlette.testclient import TestClient

from grove.config import Settings
from grove.main import create_app


def signing_key() -> PrivateKey:
    return PrivateKey()


def public_key(key: PrivateKey) -> str:
    return PublicKeyXOnly.from_secret(key.secret).format().hex()


def authorization(
    key: PrivateKey,
    action: str,
    *,
    blob_hash: str | None = None,
    server: str | None = "grove.example",
    expires: int | None = None,
    content: str | None = None,
) -> str:
    tags = [["t", action], ["expiration", str(expires or int(time.time()) + 300)]]
    if blob_hash:
        tags.append(["x", blob_hash])
    if server:
        tags.append(["server", server])
    created_at = int(time.time()) - 1
    pubkey = public_key(key)
    content = content or f"{action.title()} Blossom blob"
    serialized = json.dumps(
        [0, pubkey, created_at, 24242, tags, content],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    event_id = hashlib.sha256(serialized.encode()).hexdigest()
    event = {
        "id": event_id,
        "pubkey": pubkey,
        "created_at": created_at,
        "kind": 24242,
        "tags": tags,
        "content": content,
        "sig": key.sign_schnorr(bytes.fromhex(event_id)).hex(),
    }
    encoded = (
        base64.urlsafe_b64encode(json.dumps(event, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )
    return f"Nostr {encoded}"


def settings(tmp_path, *, max_size: int = 1024 * 1024) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        public_url="https://grove.example",
        server_name="grove.example",
        max_blob_size=max_size,
        auth_clock_skew_seconds=30,
    )


def upload(client: TestClient, key: PrivateKey, body: bytes, media_type="text/plain"):
    digest = hashlib.sha256(body).hexdigest()
    response = client.put(
        "/upload",
        content=body,
        headers={
            "Authorization": authorization(key, "upload", blob_hash=digest),
            "X-SHA-256": digest,
            "Content-Type": media_type,
        },
    )
    return digest, response


def test_upload_get_head_range_list_and_delete(tmp_path) -> None:
    key = signing_key()
    body = b"Grove stores opaque bytes exactly as received."
    with TestClient(create_app(settings(tmp_path))) as client:
        digest, response = upload(client, key, body)
        assert response.status_code == 201
        assert response.json() == {
            "url": f"https://grove.example/{digest}.txt",
            "sha256": digest,
            "size": len(body),
            "type": "text/plain",
            "uploaded": response.json()["uploaded"],
        }

        retrieved = client.get(f"/{digest}.ignored")
        assert retrieved.status_code == 200
        assert retrieved.content == body
        assert retrieved.headers["content-type"] == "text/plain; charset=utf-8"
        assert retrieved.headers["access-control-allow-origin"] == "*"

        head = client.head(f"/{digest}.txt")
        assert head.status_code == 200
        assert head.content == b""
        assert head.headers["content-length"] == str(len(body))
        assert head.headers["accept-ranges"] == "bytes"

        partial = client.get(f"/{digest}", headers={"Range": "bytes=6-11"})
        assert partial.status_code == 206
        assert partial.content == b"stores"
        assert partial.headers["content-range"] == f"bytes 6-11/{len(body)}"

        listed = client.get(
            f"/list/{public_key(key)}",
            headers={"Authorization": authorization(key, "list")},
        )
        assert listed.status_code == 200
        assert [item["sha256"] for item in listed.json()] == [digest]

        deleted = client.delete(
            f"/{digest}",
            headers={"Authorization": authorization(key, "delete", blob_hash=digest)},
        )
        assert deleted.status_code == 204
        missing = client.get(f"/{digest}")
        assert missing.status_code == 404
        assert missing.headers["cache-control"] == "no-store"


def test_authorization_is_required_scoped_and_cryptographically_bound(tmp_path) -> None:
    key = signing_key()
    body = b"authorization test"
    digest = hashlib.sha256(body).hexdigest()
    with TestClient(create_app(settings(tmp_path))) as client:
        missing = client.put("/upload", content=body, headers={"X-SHA-256": digest})
        assert missing.status_code == 401
        assert missing.headers["www-authenticate"] == "Nostr"

        wrong_server = client.put(
            "/upload",
            content=body,
            headers={
                "X-SHA-256": digest,
                "Authorization": authorization(
                    key, "upload", blob_hash=digest, server="other.example"
                ),
            },
        )
        assert wrong_server.status_code == 401

        expired = client.put(
            "/upload",
            content=body,
            headers={
                "X-SHA-256": digest,
                "Authorization": authorization(
                    key, "upload", blob_hash=digest, expires=int(time.time()) - 1
                ),
            },
        )
        assert expired.status_code == 401

        header = authorization(key, "upload", blob_hash=digest)
        encoded = header.split(" ", 1)[1]
        event = json.loads(
            base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        )
        event["tags"][-2][1] = "00" * 32
        tampered = (
            base64.urlsafe_b64encode(json.dumps(event, separators=(",", ":")).encode())
            .decode()
            .rstrip("=")
        )
        rejected = client.put(
            "/upload",
            content=body,
            headers={"X-SHA-256": digest, "Authorization": f"Nostr {tampered}"},
        )
        assert rejected.status_code == 401
        assert "event id does not match" in rejected.headers["x-reason"]


def test_hash_mismatch_size_limit_and_upload_preflight(tmp_path) -> None:
    key = signing_key()
    body = b"12345"
    digest = hashlib.sha256(body).hexdigest()
    with TestClient(create_app(settings(tmp_path, max_size=4))) as client:
        preflight = client.head(
            "/upload",
            headers={
                "Authorization": authorization(key, "upload", blob_hash=digest),
                "X-SHA-256": digest,
                "X-Content-Length": str(len(body)),
                "X-Content-Type": "text/plain",
            },
        )
        assert preflight.status_code == 413

        too_large = client.put(
            "/upload",
            content=body,
            headers={
                "Authorization": authorization(key, "upload", blob_hash=digest),
                "X-SHA-256": digest,
            },
        )
        assert too_large.status_code == 413

    with TestClient(create_app(settings(tmp_path / "other"))) as client:
        wrong_hash = "00" * 32
        mismatch = client.put(
            "/upload",
            content=body,
            headers={
                "Authorization": authorization(key, "upload", blob_hash=wrong_hash),
                "X-SHA-256": wrong_hash,
            },
        )
        assert mismatch.status_code == 409


def test_upload_accepts_acorn_style_signed_hash_without_hash_header(tmp_path) -> None:
    key = signing_key()
    body = b"Acorn python-blossom compatibility"
    digest = hashlib.sha256(body).hexdigest()
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.put(
            "/upload",
            content=body,
            headers={
                "Authorization": authorization(key, "upload", blob_hash=digest),
                "Content-Type": "application/octet-stream",
            },
        )
        assert response.status_code == 201
        assert response.json()["sha256"] == digest
        assert client.get(f"/{digest}").content == body


def test_shared_blob_survives_until_last_owner_deletes_it(tmp_path) -> None:
    first = signing_key()
    second = signing_key()
    body = b"same content"
    with TestClient(create_app(settings(tmp_path))) as client:
        digest, created = upload(client, first, body)
        assert created.status_code == 201
        _, existing = upload(client, second, body)
        assert existing.status_code == 200

        first_delete = client.delete(
            f"/{digest}",
            headers={"Authorization": authorization(first, "delete", blob_hash=digest)},
        )
        assert first_delete.status_code == 204
        assert client.get(f"/{digest}").status_code == 200

        unauthorized_delete = client.delete(
            f"/{digest}",
            headers={"Authorization": authorization(first, "delete", blob_hash=digest)},
        )
        assert unauthorized_delete.status_code == 404

        second_delete = client.delete(
            f"/{digest}",
            headers={
                "Authorization": authorization(second, "delete", blob_hash=digest)
            },
        )
        assert second_delete.status_code == 204
        assert client.get(f"/{digest}").status_code == 404


def test_storage_survives_application_restart_and_cors_preflight(tmp_path) -> None:
    key = signing_key()
    configured = settings(tmp_path)
    body = b"persistent"
    with TestClient(create_app(configured)) as client:
        digest, response = upload(client, key, body)
        assert response.status_code == 201

    with TestClient(create_app(configured)) as client:
        assert client.get(f"/{digest}").content == body
        options = client.options(
            "/upload",
            headers={
                "Origin": "https://client.example",
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "Authorization,X-SHA-256",
            },
        )
        assert options.status_code == 200
        assert options.headers["access-control-allow-origin"] == "*"
        assert (
            "authorization" in options.headers["access-control-allow-headers"].lower()
        )
