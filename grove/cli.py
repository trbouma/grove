"""Command-line entry point for running Grove locally."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlsplit

import uvicorn

from grove.config import Settings
from grove.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="grove",
        description="Run the Grove Blossom server.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="bind host")
    parser.add_argument("--port", type=int, default=8000, help="bind port")
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="directory for SQLite metadata and blob files",
    )
    parser.add_argument(
        "--public-url",
        default=None,
        help="public origin URL used in blob descriptors",
    )
    parser.add_argument(
        "--server-name",
        default=None,
        help="BUD-11 server tag name; defaults to the public URL hostname",
    )
    parser.add_argument(
        "--max-blob-size",
        type=int,
        default=100 * 1024 * 1024,
        help="maximum accepted blob size in bytes",
    )
    parser.add_argument(
        "--auth-clock-skew-seconds",
        type=int,
        default=30,
        help="permitted future clock skew for authorization events",
    )
    args = parser.parse_args()

    public_url = (args.public_url or f"http://{args.host}:{args.port}").rstrip("/")
    parsed = urlsplit(public_url)
    server_name = (args.server_name or (parsed.hostname or "")).lower().rstrip(".")

    settings = Settings(
        data_dir=Path(args.data_dir).expanduser().resolve(),
        public_url=public_url,
        server_name=server_name,
        max_blob_size=args.max_blob_size,
        auth_clock_skew_seconds=args.auth_clock_skew_seconds,
    )
    uvicorn.run(create_app(settings), host=args.host, port=args.port)
