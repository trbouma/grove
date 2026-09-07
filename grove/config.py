"""Environment-backed Grove configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from grove.identity import service_npub

SERVICE_MANAGEMENT_MODES = {"independent", "mainstay-managed"}


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
    service_nsec: str | None = None
    service_management: str = "independent"

    def __post_init__(self) -> None:
        if self.service_management not in SERVICE_MANAGEMENT_MODES:
            raise ValueError("unsupported Grove service management mode")
        if self.service_management == "mainstay-managed" and not self.service_nsec:
            raise ValueError("mainstay-managed Grove requires GROVE_SERVICE_NSEC")
        if self.service_nsec:
            service_npub(self.service_nsec)

    @property
    def service_npub(self) -> str | None:
        return service_npub(self.service_nsec) if self.service_nsec else None

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
                "GROVE_PUBLIC_URL must be an origin URL without credentials, "
                "path, query, or fragment"
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
            service_nsec=os.getenv("GROVE_SERVICE_NSEC") or None,
            service_management=os.getenv(
                "GROVE_SERVICE_MANAGEMENT", "independent"
            ),
        )
