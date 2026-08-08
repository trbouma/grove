# Grove Security

Grove is an opaque storage service. Its principal security boundary is between
clients that control Nostr signing keys and a server that stores bytes without
understanding their meaning.

## Security properties

- Blobs are addressed by the SHA-256 digest of their exact bytes.
- Upload authorization is bound to the expected digest before the body is read.
- The body is independently hashed during streaming and rejected on mismatch.
- Nostr authorization event IDs are recomputed before BIP-340 signature
  verification; supplied IDs are never trusted on their own.
- Upload and deletion tokens are scoped to a particular blob hash.
- A valid `server` tag prevents a token from being replayed against another
  Blossom domain.
- Only an uploader can remove its ownership reference.
- Blob paths are derived only from validated lowercase hashes, not user
  filenames.
- Temporary uploads are removed after failures.
- Configurable size limits bound disk consumption per request.

## Trust boundaries

Grove sees blob bytes, public keys, MIME types, sizes, hashes and request
metadata. It does not provide encryption. Applications such as Acorn must
encrypt sensitive content before upload and should avoid revealing sensitive
meaning in MIME types or surrounding metadata.

Public retrieval means anyone who knows or discovers a hash can request its
bytes. Encryption is therefore mandatory for confidential material.

The operator controls availability and may delete, withhold, inspect, or fail
to replicate stored bytes. Clients requiring continuity should replicate blobs
across independent Blossom servers and verify their hashes after retrieval.

## Residual risks

- Authorization tokens remain replayable until their expiration. Clients
  should use short expirations and a `server` tag.
- SHA-256 filenames reveal when two uploads contain identical bytes. Encrypting
  with randomized nonces normally prevents equality leakage between otherwise
  identical plaintexts.
- A valid uploader can consume storage up to operational quotas. Grove includes
  a per-blob size limit but does not yet implement per-key quotas or rate limits.
- SQLite and local filesystem storage are designed for one Grove process.
  Multiple workers or hosts require a coordinated metadata and storage adapter.
- Grove does not perform malware scanning because transforming or interpreting
  opaque blobs would violate its minimal storage boundary. Operators should
  isolate the service accordingly.

## Reporting vulnerabilities

Please report security issues privately to the repository owner before opening
a public issue containing exploit details.
