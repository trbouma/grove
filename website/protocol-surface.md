---
title: Protocol Surface
description: Grove's implemented Blossom endpoints and authorization behavior.
---

# Protocol surface

Grove implements a bounded subset of the
[Blossom Upgrade Documents](https://github.com/hzrd149/blossom).

| Method | Path | Authorization | Behavior |
| --- | --- | --- | --- |
| `GET` | `/<sha256>[.ext]` | Public | Retrieve exact bytes; supports byte ranges. |
| `HEAD` | `/<sha256>[.ext]` | Public | Retrieve headers without the body. |
| `PUT` | `/upload` | Signed `upload` event | Stream and store a hash-verified blob. |
| `HEAD` | `/upload` | Signed `upload` event | Validate hash, size, type, and policy before upload. |
| `GET` | `/list/<pubkey>` | Signed `list` event from that pubkey | Return cursor-paginated owner descriptors. |
| `DELETE` | `/<sha256>[.ext]` | Signed `delete` event | Remove the caller's owner reference. |
| `GET` | `/health` | Public | Return `{"status":"ok"}`. |
| `GET` | `/` | Public | Return server name, version, and implemented BUD identifiers. |

## Authorization

Authenticated endpoints use:

```http
Authorization: Nostr <base64-encoded-kind-24242-event>
```

Grove validates:

- canonical event-ID reconstruction;
- BIP-340 Schnorr signature;
- kind `24242`;
- creation time and one expiration tag;
- exactly the required `t` action;
- an optional `server` scope matching the configured hostname;
- lowercase SHA-256 values in `x` tags; and
- action-specific ownership and hash requirements.

Authorization tokens are bearer values until they expire. Clients should keep
their lifetime short and include the `server` tag to prevent cross-server
replay.

## Upload compatibility

`X-SHA-256` is accepted when supplied. For compatibility with Acorn's current
`python-blossom` client, Grove also accepts an upload without that header when
the signed authorization contains exactly one valid `x` hash. The body is still
independently hashed and rejected if it differs.

## Blob descriptor

A successful upload returns:

```json
{
  "url": "https://grove.example/<sha256>.pdf",
  "sha256": "<64 lowercase hexadecimal characters>",
  "size": 12345,
  "type": "application/pdf",
  "uploaded": 1786200000
}
```

## Deliberately absent

Grove does not currently implement BUD-04 mirroring, BUD-05 media
transformation, BUD-07 payments, BUD-09 reports, quotas, or an object-storage
backend. These omissions keep the first implementation small and auditable.
