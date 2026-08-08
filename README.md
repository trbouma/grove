# Grove

Grove is a lean Python [Blossom](https://github.com/hzrd149/blossom)
server. It stores opaque bytes by SHA-256 hash and uses signed Nostr events to
authorize upload, listing, and deletion.

**Acorn controls and encrypts records. Grove stores the resulting opaque
blobs.** Grove does not need an Acorn private key and cannot interpret
Acorn-encrypted content.

## Implemented protocol surface

- BUD-01: `GET /<sha256>` and `HEAD /<sha256>`, including optional extensions
  and byte-range retrieval.
- BUD-02: streaming `PUT /upload` with unchanged byte storage and standard blob
  descriptors.
- BUD-06: `HEAD /upload` policy preflight.
- BUD-11: strict kind `24242` Nostr authorization.
- BUD-12: owner-authorized `DELETE /<sha256>` and authenticated,
  cursor-paginated `GET /list/<pubkey>`.

Grove intentionally does not yet implement mirroring, media transformation,
payments, reporting, or external object storage.

## Run locally

Python 3.11 through 3.13 and Poetry are supported. Python 3.11 is recommended
to match Acorn deployments:

```bash
poetry install
cp .env.example .env
poetry run uvicorn grove.main:app --host 127.0.0.1 --port 8000 --reload
```

Open `http://127.0.0.1:8000/docs` for the generated API documentation.

Run the tests:

```bash
poetry run pytest
```

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `GROVE_DATA_DIR` | `./data` | Persistent SQLite metadata and blob files. |
| `GROVE_DATA_PATH` | `./data` | Docker host directory mounted at `/data`. |
| `GROVE_UID` / `GROVE_GID` | `1000` / `1000` | Container process identity; should own the Docker data path. |
| `GROVE_PUBLIC_URL` | `http://127.0.0.1:8000` | Public base URL used in blob descriptors. |
| `GROVE_SERVER_NAME` | hostname from public URL | Lowercase domain used to validate BUD-11 `server` tags. |
| `GROVE_MAX_BLOB_SIZE` | `104857600` | Maximum blob size in bytes (100 MiB). |
| `GROVE_AUTH_CLOCK_SKEW_SECONDS` | `30` | Permitted future clock skew for authorization events. |

Production deployments should use an HTTPS reverse proxy and set
`GROVE_PUBLIC_URL` to the externally visible URL. Keep `GROVE_DATA_DIR` on a
persistent volume.

For Docker, choose an explicit persistent host directory and ensure it is owned
by the UID and GID used by the container:

```bash
sudo install -d -o "$(id -u)" -g "$(id -g)" /mnt/bitcoin/blossom
```

Then set:

```env
GROVE_DATA_PATH=/mnt/bitcoin/blossom
GROVE_UID=1000
GROVE_GID=1000
```

Use the actual values returned by `id -u` and `id -g` rather than assuming they
are `1000`.

## Storage model

Blob bytes are stored under:

```text
data/blobs/<first-two-hash-characters>/<sha256>
```

`data/grove.db` stores MIME type, size, upload time, and uploader ownership.
If multiple public keys upload the same content, Grove stores one physical
blob and records each owner independently. Deleting one owner's reference does
not remove bytes still owned by another uploader.

The SQLite database uses foreign keys and WAL mode. This is deliberately suited
to a small standalone server or appliance. A future storage adapter can add
PostgreSQL or object storage without changing the Blossom HTTP boundary.

## Authorization policy

Retrieval is public, as expected for ordinary Blossom storage. Upload, list,
and delete require BUD-11 authorization tokens. Grove independently:

- recomputes the Nostr event ID from its canonical fields;
- verifies the BIP-340 Schnorr signature;
- checks kind, creation time, expiration, action and human-readable content;
- enforces optional `server` scope;
- requires the matching `x` hash for upload and deletion; and
- requires a list token to be signed by the public key being listed.

Upload bodies are streamed to a temporary file, hashed as received, flushed to
disk, and moved into content-addressed storage only after the expected digest
and size are verified.

For compatibility with Acorn's current `python-blossom` client, `PUT /upload`
may omit `X-SHA-256` when its signed authorization event contains exactly one
valid `x` hash. Grove treats that signed hash as the expected digest and still
rejects any body that does not match it.

See [SECURITY.md](SECURITY.md) for trust boundaries and residual risks.
