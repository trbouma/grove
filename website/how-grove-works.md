---
title: How Grove Works
description: Grove's storage, ownership, retrieval, and deletion model.
---

# How Grove works

Grove separates immutable blob bytes from the public keys that claim an
ownership reference to those bytes.

## Upload path

```text
client
  -> signs a short-lived kind 24242 upload authorization
  -> streams bytes to PUT /upload
Grove
  -> validates authorization and expected hash
  -> streams into a temporary file while hashing and counting
  -> rejects mismatched or oversized content
  -> atomically moves valid bytes into content-addressed storage
  -> records blob metadata and uploader ownership in SQLite
```

The upload is never trusted merely because the client supplied a digest. Grove
computes SHA-256 over the body it actually received.

## Filesystem and metadata

Blob bytes are stored under a two-character hash prefix:

```text
data/
├── grove.db
├── blobs/
│   └── ab/
│       └── abcdef...<64-character-sha256>
└── tmp/
```

SQLite records the blob's digest, size, media type, upload time, and its owner
references. Foreign keys and WAL mode are enabled.

## Deduplication and ownership

The same exact ciphertext has the same SHA-256 digest. When two public keys
upload identical bytes, Grove keeps one physical file and records two owner
references.

Deleting a blob is therefore owner scoped:

- the caller must sign a `delete` authorization for that hash;
- Grove removes only that caller's ownership reference; and
- the physical bytes are removed only when no owner references remain.

This is storage accounting, not legal ownership or access control over
retrieval. Blob retrieval is public to anyone who knows the hash.

## Retrieval

`GET /<sha256>` and `HEAD /<sha256>` return the stored bytes and metadata. An
optional filename extension is accepted for client convenience but does not
participate in addressing. Byte ranges are supported by the underlying file
response, which is useful for PDFs, audio, video, and resumable retrieval.

Successful retrievals are marked immutable because a digest path cannot
legitimately change to different bytes. Error and administrative responses use
`Cache-Control: no-store`.

## What Grove deliberately leaves outside

Grove does not decrypt, transform, scan, classify, index, or interpret blob
contents. It does not hold user signing keys. TLS termination, request-rate
controls, network filtering, monitoring, backups, and multi-site replication
remain deployment responsibilities.
