"""Environment-backed Grove configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    public_url: str
    server_name: str
    max_blob_size: int
    auth_clock_skew_seconds: int

    @classmethod
    def from_env(cls) -> Settings:
        public_url = (
            os.getenv("GROVE_PUBLIC_URL", "http://127.0.0.1:8000").strip().rstrip("/")
        )
        parsed = urlsplit(public_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise RuntimeError(
                "GROVE_PUBLIC_URL must be an origin URL without credentials, path, query, or fragment"
            )
        configured_name = os.getenv("GROVE_SERVER_NAME", "").strip().lower().rstrip(".")
        server_name = configured_name or parsed.hostname.lower().rstrip(".")
        if "://" in server_name or "/" in server_name or ":" in server_name:
            raise RuntimeError(
                "GROVE_SERVER_NAME must be a lowercase domain name without a port"
            )
        return cls(
            data_dir=Path(os.getenv("GROVE_DATA_DIR", "./data")).expanduser().resolve(),
            public_url=public_url,
            server_name=server_name,
            max_blob_size=_positive_int("GROVE_MAX_BLOB_SIZE", 100 * 1024 * 1024),
            auth_clock_skew_seconds=_positive_int("GROVE_AUTH_CLOCK_SKEW_SECONDS", 30),
        )
