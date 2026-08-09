---
title: Getting Started
description: Run Grove locally with Poetry or Docker Compose.
---

# Getting started

## Run from source

Grove supports Python 3.11 through 3.13. Python 3.11 is recommended when testing
alongside Acorn.

```bash
git clone https://github.com/trbouma/grove.git
cd grove
poetry install
cp .env.example .env
poetry run uvicorn grove.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

Check the service:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

FastAPI's generated API documentation is available at
`http://127.0.0.1:8000/docs`.

## Run the tests

```bash
poetry run pytest
poetry run ruff check .
```

The tests exercise upload, retrieval, `HEAD`, byte ranges, authorization,
server scoping, expiry, hash mismatch, size limits, preflight, Acorn-compatible
upload, shared ownership, deletion, persistence, and CORS.

## Run with Docker Compose

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose logs -f grove
```

The default bind is loopback-only:

```text
127.0.0.1:8000 -> container:8000
```

Use a reverse proxy for public HTTPS rather than exposing the development
server directly.

## Preview this documentation

```bash
poetry install --with docs
poetry run mkdocs serve
```

Then open `http://127.0.0.1:8000`.
