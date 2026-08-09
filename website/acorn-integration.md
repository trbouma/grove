---
title: Grove and Acorn
description: The confidentiality and availability boundary between Acorn and Grove.
---

# Grove and Acorn

Acorn and Grove have complementary responsibilities.

| Component | Responsibility |
| --- | --- |
| **Acorn** | Encrypts attachments, protects the blob key inside an encrypted private record, signs Blossom authorization, and verifies retrieved content. |
| **Grove** | Stores the opaque bytes, verifies their content hash, records uploader ownership, and returns the same bytes by hash. |
| **Nostr relay** | Stores the encrypted private record containing the blob reference and the information Acorn needs to recover the attachment. |

## Write path

For an Acorn attachment, the intended flow is:

1. Acorn generates an independent random attachment key.
2. Acorn encrypts the original bytes with authenticated encryption.
3. Acorn calculates the ciphertext SHA-256 digest.
4. Acorn signs a short-lived Blossom upload authorization bound to that digest.
5. Grove independently verifies the authorization and uploaded ciphertext.
6. Acorn stores the blob reference, key material, integrity values, and original
   media metadata inside the encrypted private record on its relay.

Grove receives only the output of that process. It cannot reconstruct the
plaintext from the stored object alone.

## Read path

1. Acorn retrieves and decrypts the private record from its relay.
2. It downloads the ciphertext from Grove by SHA-256 hash.
3. It verifies the ciphertext hash and authenticated encryption.
4. Only then does it return the original bytes to the application.

If the private record is unavailable, the Grove blob is normally just opaque
ciphertext. If Grove is unavailable, possession of the private record alone
does not restore the attachment bytes. Durable recovery therefore requires
replication of both relay state and blobs.

## Precise security claim

It is accurate to say:

> Safebox Acorn encrypts attachments before uploading them to Grove.

It is not accurate to say:

> Grove encrypts every blob or guarantees that every stored object is private.

Any compatible client may upload plaintext. Grove is an availability provider,
not the confidentiality boundary.

## Metadata remains visible

Encryption does not conceal every fact. Grove may observe uploader public keys,
ciphertext hashes, object sizes, declared media types, timing, source addresses,
and retrieval patterns. Operators and clients should avoid placing sensitive
meaning in filenames or metadata and should treat access-pattern privacy as a
separate problem.
