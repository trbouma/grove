---
title: BUD-13 Path-Based Upload
description: Why Grove should track path-based Blossom uploads without rushing them into the advertised surface.
---

# BUD-13 path-based upload

Grove should follow the Blossom protocol as it matures, but it should not turn
every draft into an immediate production promise.

[Blossom pull request 100](https://github.com/hzrd149/blossom/pull/100)
introduces draft BUD-13, a path-based upload endpoint:

```http
PUT /<sha256>
```

The idea is attractive. A content-addressed storage service already names
bytes by SHA-256. Putting the expected digest in the route makes the upload
path easier to reason about than relying on an optional `X-SHA-256` header.

For Grove, the right posture is deliberate adoption, not immediate expansion.

## Why this matters

Grove's job in the Mainstay product family is narrow: store exact opaque bytes,
verify their digest, record owner references, and retrieve the same bytes by
hash. Acorn protects confidentiality. Spurline preserves signed relay events.
Mainstay and Safebox Web provide the user and operator experience.

That boundary is what makes Grove useful. It can be replaced, audited, and
operated independently because it does not become the application, key
custodian, media processor, or general cloud drive.

BUD-13 fits that boundary when it means binary path-based upload. It becomes a
larger decision when it includes remote-source `url` uploads, because then
Grove would initiate network fetches and inherit the security surface of
mirroring.

## Recommended action

Grove should track BUD-13 and be ready to implement the binary
`PUT /<sha256>` form after the upstream draft stabilizes or a real client needs
it. Grove should keep `PUT /upload` for compatibility.

Grove should not advertise BUD-13 today, and it should not implement
remote-source `?url=` upload as a side effect of adopting the path-based route.
That belongs in a separate mirroring decision with its own abuse, network, and
operator-policy review.

[Read the detailed design note](https://github.com/trbouma/grove/blob/main/docs/specs/BUD-13-PATH-UPLOAD-DESIGN-NOTE.md){ .md-button .md-button--primary }
[Review Grove's protocol surface](../protocol-surface.md){ .md-button }
