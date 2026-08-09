---
title: Configuration
description: Grove environment variables and safe operational defaults.
---

# Configuration

Grove is configured entirely through environment variables.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROVE_DATA_DIR` | `./data` | Runtime directory containing `grove.db`, blobs, and temporary uploads. Docker fixes this to `/data`. |
| `GROVE_DATA_PATH` | `./data` | Host path mounted at `/data` by Docker Compose. |
| `GROVE_UID` | `1000` | Container user ID; should own the host data directory. |
| `GROVE_GID` | `1000` | Container group ID; should own the host data directory. |
| `GROVE_BIND_ADDRESS` | `127.0.0.1` | Host interface used by the Docker port mapping. |
| `GROVE_PORT` | `8000` | Host port mapped to container port `8000`. |
| `GROVE_IMAGE` | `safebox-grove:local` | Docker image name. |
| `GROVE_PUBLIC_URL` | `http://127.0.0.1:8000` | External origin placed in blob descriptors. No path, query, fragment, or credentials. |
| `GROVE_SERVER_NAME` | Public URL hostname | Optional lowercase hostname used to validate BUD-11 `server` tags. No scheme or port. |
| `GROVE_MAX_BLOB_SIZE` | `104857600` | Maximum accepted blob size in bytes. |
| `GROVE_AUTH_CLOCK_SKEW_SECONDS` | `30` | Permitted future skew for signed authorization timestamps. |

## Persistent Docker path

Create a directory owned by the identity used in the container:

```bash
sudo install -d \
  -o "$(id -u)" \
  -g "$(id -g)" \
  /mnt/bitcoin/blossom
```

Then configure:

```env
GROVE_DATA_PATH=/mnt/bitcoin/blossom
GROVE_UID=1000
GROVE_GID=1000
```

Use the values from `id -u` and `id -g`; do not assume they are `1000`.

## Public deployment example

```env
GROVE_DATA_PATH=/mnt/bitcoin/blossom
GROVE_UID=1000
GROVE_GID=1000
GROVE_BIND_ADDRESS=127.0.0.1
GROVE_PORT=8200
GROVE_PUBLIC_URL=https://blobs.example.com
GROVE_SERVER_NAME=blobs.example.com
GROVE_MAX_BLOB_SIZE=104857600
GROVE_AUTH_CLOCK_SKEW_SECONDS=30
```

`GROVE_PUBLIC_URL` determines returned blob URLs. `GROVE_SERVER_NAME` determines
which server-scoped authorization tokens are accepted. They should describe the
same public service.
