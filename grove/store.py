"""Filesystem blob storage with small SQLite ownership metadata."""

from __future__ import annotations

import mimetypes
import os
import sqlite3
import tempfile
import time
from collections.abc import AsyncIterable
from pathlib import Path


class BlobTooLarge(ValueError):
    pass


class HashMismatch(ValueError):
    pass


def normalized_media_type(value: str | None) -> str:
    media_type = str(value or "").split(";", 1)[0].strip().lower()
    if (
        not media_type
        or "/" not in media_type
        or any(char in media_type for char in "\r\n")
    ):
        return "application/octet-stream"
    return media_type


def media_extension(media_type: str) -> str:
    overrides = {
        "application/octet-stream": ".bin",
        "image/jpeg": ".jpg",
        "text/plain": ".txt",
    }
    extension = overrides.get(media_type) or mimetypes.guess_extension(
        media_type, strict=False
    )
    if not extension or not extension.startswith("."):
        return ".bin"
    return extension.lower()


class BlobStore:
    def __init__(self, data_dir: Path, public_url: str) -> None:
        self.data_dir = data_dir
        self.blob_dir = data_dir / "blobs"
        self.temp_dir = data_dir / "tmp"
        self.database_path = data_dir / "grove.db"
        self.public_url = public_url.rstrip("/")

    def initialize(self) -> None:
        self.blob_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS blob (
                    sha256 TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    media_type TEXT NOT NULL,
                    uploaded INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS blob_owner (
                    sha256 TEXT NOT NULL,
                    pubkey TEXT NOT NULL,
                    uploaded INTEGER NOT NULL,
                    PRIMARY KEY (sha256, pubkey),
                    FOREIGN KEY (sha256) REFERENCES blob(sha256) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS ix_blob_owner_pubkey_uploaded
                    ON blob_owner(pubkey, uploaded DESC, sha256);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def path_for(self, sha256: str) -> Path:
        return self.blob_dir / sha256[:2] / sha256

    def get(self, sha256: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT sha256, size, media_type, uploaded FROM blob WHERE sha256 = ?",
                (sha256,),
            ).fetchone()
        if row is None or not self.path_for(sha256).is_file():
            return None
        return dict(row)

    def descriptor(self, blob: dict, *, uploaded: int | None = None) -> dict:
        extension = media_extension(blob["media_type"])
        return {
            "url": f"{self.public_url}/{blob['sha256']}{extension}",
            "sha256": blob["sha256"],
            "size": blob["size"],
            "type": blob["media_type"],
            "uploaded": blob["uploaded"] if uploaded is None else uploaded,
        }

    async def upload(
        self,
        chunks: AsyncIterable[bytes],
        *,
        expected_hash: str,
        media_type: str,
        owner_pubkey: str,
        max_size: int,
        expected_size: int | None,
    ) -> tuple[dict, bool]:
        import hashlib

        digest = hashlib.sha256()
        size = 0
        file_descriptor, temporary_name = tempfile.mkstemp(
            dir=self.temp_dir, prefix="upload-"
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(file_descriptor, "wb") as target:
                async for chunk in chunks:
                    size += len(chunk)
                    if size > max_size:
                        raise BlobTooLarge(f"Blob exceeds the {max_size}-byte limit")
                    digest.update(chunk)
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            if expected_size is not None and size != expected_size:
                raise ValueError("Content-Length does not match the uploaded body")
            actual_hash = digest.hexdigest()
            if actual_hash != expected_hash:
                raise HashMismatch("X-SHA-256 does not match the uploaded body")

            existing = self.get(actual_hash)
            created = existing is None
            uploaded = int(time.time())
            final_path = self.path_for(actual_hash)
            final_path.parent.mkdir(parents=True, exist_ok=True)
            if created:
                os.replace(temporary_path, final_path)
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO blob(sha256, size, media_type, uploaded)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(sha256) DO NOTHING
                    """,
                    (actual_hash, size, media_type, uploaded),
                )
                connection.execute(
                    """
                    INSERT INTO blob_owner(sha256, pubkey, uploaded)
                    VALUES (?, ?, ?)
                    ON CONFLICT(sha256, pubkey) DO NOTHING
                    """,
                    (actual_hash, owner_pubkey, uploaded),
                )
                connection.commit()
            blob = self.get(actual_hash)
            if blob is None:
                raise RuntimeError("Blob metadata could not be persisted")
            return self.descriptor(blob), created
        finally:
            temporary_path.unlink(missing_ok=True)

    def list_for_owner(
        self,
        pubkey: str,
        *,
        cursor: str | None,
        limit: int,
        since: int | None,
        until: int | None,
    ) -> list[dict]:
        conditions = ["o.pubkey = ?"]
        values: list[object] = [pubkey]
        if cursor:
            cursor_row = None
            with self._connect() as connection:
                cursor_row = connection.execute(
                    "SELECT uploaded FROM blob_owner WHERE pubkey = ? AND sha256 = ?",
                    (pubkey, cursor),
                ).fetchone()
            if cursor_row is None:
                return []
            conditions.append("(o.uploaded < ? OR (o.uploaded = ? AND o.sha256 < ?))")
            values.extend([cursor_row["uploaded"], cursor_row["uploaded"], cursor])
        if since is not None:
            conditions.append("o.uploaded >= ?")
            values.append(since)
        if until is not None:
            conditions.append("o.uploaded <= ?")
            values.append(until)
        values.append(limit)
        query = f"""
            SELECT b.sha256, b.size, b.media_type, b.uploaded AS blob_uploaded,
                   o.uploaded AS owner_uploaded
            FROM blob_owner o JOIN blob b ON b.sha256 = o.sha256
            WHERE {" AND ".join(conditions)}
            ORDER BY o.uploaded DESC, o.sha256 DESC
            LIMIT ?
        """
        with self._connect() as connection:
            rows = connection.execute(query, values).fetchall()
        return [
            self.descriptor(
                {
                    "sha256": row["sha256"],
                    "size": row["size"],
                    "media_type": row["media_type"],
                    "uploaded": row["blob_uploaded"],
                },
                uploaded=row["owner_uploaded"],
            )
            for row in rows
        ]

    def delete_for_owner(self, sha256: str, pubkey: str) -> bool:
        with self._connect() as connection:
            owned = connection.execute(
                "SELECT 1 FROM blob_owner WHERE sha256 = ? AND pubkey = ?",
                (sha256, pubkey),
            ).fetchone()
            if owned is None:
                return False
            connection.execute(
                "DELETE FROM blob_owner WHERE sha256 = ? AND pubkey = ?",
                (sha256, pubkey),
            )
            owners_remaining = connection.execute(
                "SELECT 1 FROM blob_owner WHERE sha256 = ? LIMIT 1", (sha256,)
            ).fetchone()
            if owners_remaining is None:
                connection.execute("DELETE FROM blob WHERE sha256 = ?", (sha256,))
            connection.commit()
        if owners_remaining is None:
            self.path_for(sha256).unlink(missing_ok=True)
        return True
