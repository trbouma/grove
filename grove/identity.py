"""Persistent Nostr identity binding for a Grove service instance."""

from __future__ import annotations

import json
import os
from pathlib import Path

from coincurve import PrivateKey, PublicKeyXOnly

BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def service_npub(secret: str) -> str:
    """Derive the NIP-19 npub for a hex or nsec-encoded private key."""

    key_bytes = _private_key_bytes(secret)
    public_key = PublicKeyXOnly.from_secret(key_bytes).format()
    return _bech32_encode("npub", _convert_bits(public_key, 8, 5))


def bind_service_identity(data_dir: Path, *, npub: str | None) -> None:
    """Bind persistent Grove data to one configured service identity."""

    path = data_dir / "service-identity.json"
    if path.is_file():
        try:
            recorded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("Grove service identity sentinel is invalid") from exc
        recorded_npub = recorded.get("npub") if isinstance(recorded, dict) else None
        if not isinstance(recorded_npub, str) or not recorded_npub:
            raise RuntimeError("Grove service identity sentinel is invalid")
        if npub is None:
            raise RuntimeError(
                "GROVE_SERVICE_NSEC is required for the recorded Grove identity"
            )
        if recorded_npub != npub:
            raise RuntimeError(
                "GROVE_SERVICE_NSEC does not match the recorded Grove identity"
            )
        return

    if npub is None:
        return
    data_dir.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"schema": "org.mainstay.service-identity", "npub": npub}) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _private_key_bytes(secret: str) -> bytes:
    value = secret.strip()
    if value.startswith("nsec1"):
        hrp, words = _bech32_decode(value)
        if hrp != "nsec":
            raise ValueError("GROVE_SERVICE_NSEC is invalid")
        raw = bytes(_convert_bits(words, 5, 8, pad=False))
    else:
        try:
            raw = bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError("GROVE_SERVICE_NSEC is invalid") from exc
    if len(raw) != 32:
        raise ValueError("GROVE_SERVICE_NSEC is invalid")
    try:
        PrivateKey(raw)
    except ValueError as exc:
        raise ValueError("GROVE_SERVICE_NSEC is invalid") from exc
    return raw


def _bech32_polymod(values: list[int]) -> int:
    checksum = 1
    generators = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for index, generator in enumerate(generators):
            if (top >> index) & 1:
                checksum ^= generator
    return checksum


def _hrp_expand(hrp: str) -> list[int]:
    return [ord(char) >> 5 for char in hrp] + [0] + [ord(char) & 31 for char in hrp]


def _bech32_encode(hrp: str, values: list[int]) -> str:
    checksum_input = _hrp_expand(hrp) + values
    polymod = _bech32_polymod(checksum_input + [0] * 6) ^ 1
    checksum = [(polymod >> (5 * (5 - index))) & 31 for index in range(6)]
    return hrp + "1" + "".join(BECH32_CHARSET[value] for value in values + checksum)


def _bech32_decode(value: str) -> tuple[str, list[int]]:
    if value.lower() != value and value.upper() != value:
        raise ValueError("GROVE_SERVICE_NSEC is invalid")
    normalized = value.lower()
    separator = normalized.rfind("1")
    if separator < 1 or separator + 7 > len(normalized):
        raise ValueError("GROVE_SERVICE_NSEC is invalid")
    hrp = normalized[:separator]
    try:
        data = [BECH32_CHARSET.index(char) for char in normalized[separator + 1 :]]
    except ValueError as exc:
        raise ValueError("GROVE_SERVICE_NSEC is invalid") from exc
    if _bech32_polymod(_hrp_expand(hrp) + data) != 1:
        raise ValueError("GROVE_SERVICE_NSEC is invalid")
    return hrp, data[:-6]


def _convert_bits(
    values: bytes | list[int], from_bits: int, to_bits: int, *, pad: bool = True
) -> list[int]:
    accumulator = 0
    bit_count = 0
    result: list[int] = []
    maximum = (1 << to_bits) - 1
    for value in values:
        if value < 0 or value >> from_bits:
            raise ValueError("GROVE_SERVICE_NSEC is invalid")
        accumulator = (accumulator << from_bits) | value
        bit_count += from_bits
        while bit_count >= to_bits:
            bit_count -= to_bits
            result.append((accumulator >> bit_count) & maximum)
    if pad and bit_count:
        result.append((accumulator << (to_bits - bit_count)) & maximum)
    elif not pad and (
        bit_count >= from_bits or (accumulator << (to_bits - bit_count)) & maximum
    ):
        raise ValueError("GROVE_SERVICE_NSEC is invalid")
    return result
