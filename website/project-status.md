---
title: Project Status
description: Current Grove capabilities, constraints, and near-term direction.
---

# Project status

Grove is working developer-stage software. It is deployed successfully with
Safebox Acorn, but it remains intentionally small and unaudited.

## Available

- content-addressed local blob storage;
- streaming, hash-verified uploads;
- public retrieval, `HEAD`, and byte ranges;
- BUD-11 signed authorization;
- authenticated owner listing and deletion;
- shared-byte deduplication with independent owner references;
- SQLite WAL metadata and persistent filesystem storage;
- Docker image, Compose deployment, and health check;
- automated unit and integration-style HTTP tests; and
- demonstrated Acorn encrypted-blob compatibility.

## Before a broader production release

- add operator metrics and structured request logging without token leakage;
- add configurable rate limits and per-key storage quotas;
- define retention, abuse-reporting, and operator policy;
- document and test online backup and restoration;
- add live interoperability tests with additional Blossom clients;
- review BUD conformance against the evolving upstream specifications;
- complete threat modelling and independent security review; and
- decide whether mirroring or a storage-adapter interface belongs in Grove's
  deliberately small scope.

## Design direction

Grove should remain understandable. New features belong only when they preserve
the central boundary:

> Store the exact bytes authorized by a key, retrieve them by hash, and avoid
> taking custody of application secrets.

General media processing, application-level indexing, record semantics, and
key custody belong in other components.
