"""Strict BUD-11 Nostr authorization validation."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from dataclasses import dataclass

from coincurve import PublicKeyXOnly

AUTH_KIND = 24242
MAX_AUTH_TOKEN_BYTES = 32_768


class AuthorizationError(ValueError):
    """Raised when a Blossom authorization token is invalid."""


@dataclass(frozen=True)
class Authorization:
    event_id: str
    pubkey: str
    action: str
    expires_at: int
    blob_hashes: tuple[str, ...]


def _hex(value: object, length: int, label: str) -> str:
    text = str(value or "")
    if len(text) != length or text != text.lower():
        raise AuthorizationError(f"{label} must be lowercase hexadecimal")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise AuthorizationError(f"{label} must be lowercase hexadecimal") from exc
    return text


def _decode_header(header: str | None) -> dict:
    if not header:
        raise AuthorizationError("Nostr authorization is required")
    scheme, separator, token = header.partition(" ")
    if not separator or scheme.lower() != "nostr" or not token:
        raise AuthorizationError("Authorization must use the Nostr scheme")
    if len(token) > MAX_AUTH_TOKEN_BYTES * 2:
        raise AuthorizationError("Authorization token is too large")
    # BUD-11 specifies unpadded base64url. The current python-blossom client
    # used by Acorn emits standard padded base64, so accept either alphabet
    # strictly while rejecting whitespace and mixed/invalid characters.
    urlsafe = re.fullmatch(r"[A-Za-z0-9_-]+={0,2}", token) is not None
    standard = re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", token) is not None
    if not (urlsafe or standard):
        raise AuthorizationError("Authorization token is not valid base64")
    try:
        padding = "=" * (-len(token) % 4)
        raw = base64.b64decode(
            token + padding,
            altchars=b"-_" if urlsafe else None,
            validate=True,
        )
    except Exception as exc:
        raise AuthorizationError("Authorization token is not valid base64") from exc
    if len(raw) > MAX_AUTH_TOKEN_BYTES:
        raise AuthorizationError("Authorization token is too large")
    try:
        event = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthorizationError("Authorization token is not valid JSON") from exc
    if not isinstance(event, dict):
        raise AuthorizationError("Authorization token must contain a Nostr event")
    return event


def _tags(event: dict) -> list[list[str]]:
    tags = event.get("tags")
    if not isinstance(tags, list):
        raise AuthorizationError("Authorization event tags are invalid")
    result: list[list[str]] = []
    for tag in tags:
        if (
            not isinstance(tag, list)
            or not tag
            or not all(isinstance(value, str) for value in tag)
        ):
            raise AuthorizationError("Authorization event tags are invalid")
        result.append(tag)
    return result


def _values(tags: list[list[str]], name: str) -> list[str]:
    return [tag[1] for tag in tags if tag[0] == name and len(tag) >= 2]


def validate_authorization(
    header: str | None,
    *,
    action: str,
    server_name: str,
    blob_hash: str | None = None,
    expected_pubkey: str | None = None,
    now: int | None = None,
    clock_skew_seconds: int = 30,
) -> Authorization:
    """Validate a canonical signed kind-24242 BUD-11 token."""

    event = _decode_header(header)
    event_id = _hex(event.get("id"), 64, "Event id")
    pubkey = _hex(event.get("pubkey"), 64, "Public key")
    signature = _hex(event.get("sig"), 128, "Signature")
    if event.get("kind") != AUTH_KIND:
        raise AuthorizationError("Authorization event kind must be 24242")
    created_at = event.get("created_at")
    if not isinstance(created_at, int) or isinstance(created_at, bool):
        raise AuthorizationError("Authorization created_at is invalid")
    content = event.get("content")
    if not isinstance(content, str) or not content.strip():
        raise AuthorizationError("Authorization content must explain its intended use")
    tags = _tags(event)

    canonical = json.dumps(
        [0, pubkey, created_at, AUTH_KIND, tags, content],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    computed_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if computed_id != event_id:
        raise AuthorizationError("Authorization event id does not match its contents")
    try:
        valid_signature = PublicKeyXOnly(bytes.fromhex(pubkey)).verify(
            bytes.fromhex(signature), bytes.fromhex(event_id)
        )
    except Exception as exc:
        raise AuthorizationError("Authorization signature is invalid") from exc
    if not valid_signature:
        raise AuthorizationError("Authorization signature is invalid")

    current_time = int(time.time()) if now is None else now
    if created_at > current_time + clock_skew_seconds:
        raise AuthorizationError("Authorization event was created in the future")
    expiration_values = _values(tags, "expiration")
    if len(expiration_values) != 1:
        raise AuthorizationError("Authorization must contain one expiration tag")
    try:
        expires_at = int(expiration_values[0])
    except ValueError as exc:
        raise AuthorizationError("Authorization expiration is invalid") from exc
    if expires_at <= current_time:
        raise AuthorizationError("Authorization token has expired")

    actions = _values(tags, "t")
    if actions != [action]:
        raise AuthorizationError(f"Authorization action must be {action}")
    server_values = _values(tags, "server")
    if server_values and server_name not in server_values:
        raise AuthorizationError("Authorization token is scoped to another server")
    if any(
        value != value.lower() or "://" in value or "/" in value or ":" in value
        for value in server_values
    ):
        raise AuthorizationError(
            "Authorization server tags must be lowercase domain names"
        )

    hash_values = _values(tags, "x")
    for value in hash_values:
        _hex(value, 64, "Authorization blob hash")
    if blob_hash is not None:
        normalized_hash = _hex(blob_hash, 64, "Blob hash")
        if normalized_hash not in hash_values:
            raise AuthorizationError("Authorization is not scoped to this blob")
    if expected_pubkey is not None and pubkey != _hex(
        expected_pubkey, 64, "Expected public key"
    ):
        raise AuthorizationError(
            "Authorization public key does not match the requested owner"
        )
    return Authorization(
        event_id=event_id,
        pubkey=pubkey,
        action=action,
        expires_at=expires_at,
        blob_hashes=tuple(hash_values),
    )
