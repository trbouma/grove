---
title: Security
description: Grove's security properties, trust boundaries, and residual risks.
---

# Security

Grove's security model is intentionally narrow: verify who authorized a storage
operation, verify the exact bytes received, and avoid claiming confidentiality
that the server does not provide.

## What Grove enforces

- Blob identity is the SHA-256 digest of the exact stored bytes.
- Uploads are streamed, independently hashed, and rejected on mismatch.
- Kind `24242` event IDs are reconstructed before signature verification.
- Upload and delete authorization is scoped to the relevant digest.
- Optional `server` tags restrict cross-server token replay.
- Listing requires the requested public key to sign its own authorization.
- Only an uploader can remove its owner reference.
- Validated hashes—not filenames—construct filesystem paths.
- Temporary files are removed after failed uploads.
- A configurable per-blob limit bounds each upload.

## What Grove can observe

Grove sees the bytes it stores, public keys, hashes, sizes, declared media
types, timestamps, source addresses, and access patterns. If a client uploads
plaintext, Grove can read it. Applications handling confidential material must
encrypt before upload.

Retrieval is public. Anyone who learns a blob hash can download the bytes.
Client-side encryption is therefore mandatory for confidential content.

## Operator authority

The operator controls availability. It can delete, withhold, inspect, retain,
or fail to replicate stored data. Content addressing detects substitution but
does not compel storage. Clients that require continuity should replicate
ciphertext across independent Blossom servers and verify hashes after
retrieval.

## Current residual risks

- Authorization tokens are replayable until expiration.
- No per-key quota or request-rate limit is implemented.
- SQLite and filesystem storage support one Grove process only.
- MIME type and traffic metadata may reveal information even for ciphertext.
- A server or backup compromise can destroy availability.
- Grove performs no malware scanning or content moderation.
- The project has not received an independent security audit.

Use a reverse proxy for TLS, request-rate controls, and public-network
hardening. Run Grove with a dedicated unprivileged identity, protect `/data`,
and use only non-critical data until the deployment has been reviewed for its
intended threat environment.

[Read the complete repository security statement](https://github.com/trbouma/grove/blob/main/SECURITY.md){ .md-button .md-button--primary }
