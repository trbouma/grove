---
title: Production Deployment
description: Deploy Grove behind HTTPS with persistent storage, backups, and one worker.
---

# Production deployment

Grove is intentionally designed for one application process with local SQLite
and filesystem storage.

## Deployment shape

```text
public client
    |
    | HTTPS
    v
reverse proxy
    |
    | private HTTP
    v
Grove (one worker) -> persistent /data
```

Keep the container port on loopback when the reverse proxy runs on the same
host. If the proxy runs on another private machine, bind only to the required
private interface and enforce the path with a firewall or VPN policy.

## Start and update

```bash
docker compose build --pull
docker compose up -d
docker compose ps
docker compose logs --tail=100 grove
```

After changing the source or configuration:

```bash
docker compose build --pull
docker compose up -d --force-recreate
```

Stop the service without deleting its persistent data:

```bash
docker compose down
```

## Nginx example

```nginx
server {
    listen 443 ssl http2;
    server_name blobs.example.com;

    client_max_body_size 100m;

    location / {
        proxy_pass http://127.0.0.1:8200;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_request_buffering off;
    }
}
```

Set the proxy body limit consistently with `GROVE_MAX_BLOB_SIZE`. Disabling
request buffering preserves Grove's streaming-upload behavior.

## Health and observability

Docker probes `GET /health` every 30 seconds. External monitoring can use the
same endpoint:

```bash
curl --fail https://blobs.example.com/health
```

The health check confirms that the process answers HTTP. It does not currently
perform a write/read probe against SQLite and the blob filesystem.

## Backup and recovery

`/data` is the complete persistent state: SQLite metadata plus blob bytes. The
simplest consistent backup is taken while Grove is stopped:

```bash
docker compose stop grove
rsync -a --delete /mnt/bitcoin/blossom/ /backup/grove/
docker compose start grove
```

Test restoration periodically. A backup of only `grove.db` or only `blobs/` is
incomplete. For uninterrupted production backups, use SQLite's online backup
mechanism and coordinate it with a filesystem snapshot of blob data.

## One worker means one worker

Do not add Uvicorn workers or run multiple Grove containers against the same
SQLite database and filesystem. Horizontal operation requires a coordinated
metadata database and storage adapter that Grove does not yet provide.
