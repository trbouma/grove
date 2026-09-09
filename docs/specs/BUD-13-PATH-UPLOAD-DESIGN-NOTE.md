# BUD-13 Path-Based Upload Design Note

Status: recommended for tracking; not recommended for immediate advertised
support  
Date: 2026-09-09

## Purpose

This note records Grove's recommended response to
[Blossom pull request 100](https://github.com/hzrd149/blossom/pull/100), which
introduces draft BUD-13 path-based blob upload.

Grove is an independently addressable Blossom service in the Mainstay product
family. Its protocol choices should preserve the family principle of **good
boundaries, not barriers**: compatible enough to participate in the Blossom
ecosystem, but small enough that its storage, identity, and security boundary
remain auditable.

## Current Grove Behavior

Grove currently implements BUD-02 upload through `PUT /upload`, with BUD-11
authorization and streamed hash verification. `X-SHA-256` is accepted when a
client supplies it.

For Safebox Acorn compatibility, Grove also accepts an upload without
`X-SHA-256` when the signed upload authorization contains exactly one valid
`x` tag. Grove treats that signed hash as the expected digest, computes
SHA-256 over the received bytes, and rejects mismatches before persistence.

The current advertised protocol surface is therefore:

- BUD-01 retrieval through `GET /<sha256>[.ext]` and
  `HEAD /<sha256>[.ext]`;
- BUD-02 upload through `PUT /upload`;
- BUD-06 preflight through `HEAD /upload`;
- BUD-11 authorization through kind `24242` Nostr events; and
- BUD-12 owner listing and owner-scoped deletion.

Grove intentionally does not implement BUD-04 mirroring, BUD-05 media
transformation, BUD-07 payments, BUD-09 reports, quotas, or an external object
storage backend.

## Upstream Proposal

Blossom pull request 100 adds a draft optional BUD-13 endpoint,
`PUT /<sha256>`, as a migration path away from `PUT /upload`. The PR was
opened on 2026-04-11, marked ready for review on 2026-07-30, and had no
recorded reviews when this note was written.

The draft BUD-13 text says it supersedes the `PUT /upload` definition from
BUD-02 while allowing servers to keep `PUT /upload` for compatibility. It also
keeps BUD-06 `HEAD /upload` as the portable preflight mechanism.

BUD-13 is broader than the simple binary upload endpoint. It optionally allows
remote-source upload through repeated `url` query parameters:

```http
PUT /<sha256>?url=https%3A%2F%2Fcdn.example%2Fblob.bin
```

That mode folds a mirroring-like workflow into the same path-addressed upload
endpoint.

## Recommendation

Do not add BUD-13 to Grove's advertised protocol surface yet.

Track the upstream PR and prepare to implement the binary form of
`PUT /<sha256>` once the draft is merged, has interoperable client demand, or
is needed by Acorn. When implemented, keep `PUT /upload` indefinitely as a
compatibility endpoint unless the Blossom ecosystem clearly deprecates it.

Do not implement the optional remote-source `url` mode as part of the first
BUD-13 adoption. That mode reintroduces the policy and security surface of
mirroring, including:

- origin fetch failures;
- MIME inference from remote responses;
- response-size enforcement before and during streaming;
- private-network blocking;
- DNS rebinding concerns;
- redirect policy;
- abuse reporting; and
- operational monitoring for server-initiated network traffic.

Grove has intentionally deferred BUD-04 mirroring. Adding remote fetch support
through BUD-13 would therefore be a scope expansion, not a simple upload
migration.

## Rationale

BUD-13's main benefit is protocol clarity. The expected content address is
visible in the HTTP path, so the server can authorize and reject malformed
requests without depending on an optional hash header. That aligns well with
content-addressed storage.

For Grove, the immediate practical benefit is small. Grove already has a safe
compatibility path for clients that omit `X-SHA-256`: it derives the expected
digest from exactly one signed BUD-11 `x` tag and still verifies the streamed
body. This keeps Acorn working without adding another write method.

The implementation cost for binary upload is modest, but not zero.
`PUT /<sha256>` would share a path pattern already used by `GET`, `HEAD`, and
`DELETE`. FastAPI can route distinct methods cleanly, but the behavior must be
explicit in tests so invalid paths, extension handling, authorization errors,
CORS preflights, and hash mismatches remain predictable.

The upstream status argues for patience. PR 100 is still open and unreviewed,
and BUD-13 is draft and optional. A follow-on draft for multipart
`PATCH /<sha256>` is referenced from the PR, which suggests the upload surface
is still settling.

## Acceptance Criteria for Future Adoption

If Grove adopts BUD-13 binary upload, the implementation should:

- advertise BUD-13 only after the endpoint is complete and tested;
- accept `PUT /<sha256>` with a lowercase 64-character digest and no extension;
- require the BUD-11 `upload` authorization to include a matching `x` tag;
- ignore `X-SHA-256` for path authority, or reject it when present and
  different from the path digest;
- continue computing the digest over the exact received bytes;
- return `409 Conflict` without persistence when the body does not match the
  path digest;
- preserve existing `201 Created` and `200 OK` descriptor behavior;
- continue supporting `PUT /upload`;
- keep `HEAD /upload` as the documented preflight path;
- reject `url` query parameters with a clear `400 Bad Request` until Grove
  deliberately implements remote-source mirroring; and
- cover CORS preflight behavior for both `/upload` and `/<sha256>`.

## Decision

Grove should treat BUD-13 as a likely future compatibility endpoint, not as an
urgent feature. The next action is to monitor the Blossom PR and revisit
implementation when the draft stabilizes or when a real Grove or Acorn client
needs path-based upload.
