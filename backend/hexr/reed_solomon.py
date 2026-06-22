from reedsolo import RSCodec


# ── How many check bytes we add ───────────────────────────────────────────────
# ECC_SYMBOLS = 20 means we can correct up to 10 corrupted bytes.
# Higher = more resilient, but fewer cells left for actual data.
ECC_SYMBOLS = 20

_codec = RSCodec(ECC_SYMBOLS)


# ── Block 1: Encode ───────────────────────────────────────────────────────────

def encode(data: bytes) -> bytes:
    """Encode data bytes → data bytes + error correction check bytes."""
    encoded = _codec.encode(data)
    return bytes(encoded)


# ── Block 2: Decode ───────────────────────────────────────────────────────────

def decode(encoded: bytes) -> bytes:
    """Decode and error-correct encoded bytes → original data bytes."""
    decoded, _, _ = _codec.decode(encoded)
    return bytes(decoded)


# ── Block 3: Smoke test ───────────────────────────────────────────────────────

if __name__ == "__main__":
    original = b"Hello, HexR!"
    print(f"Original  : {original}")
    print(f"Length    : {len(original)} bytes")

    # Encode
    encoded = encode(original)
    print(f"\nEncoded   : {len(encoded)} bytes  "
          f"({len(original)} data + {ECC_SYMBOLS} check bytes)")
    print(f"Raw bytes : {list(encoded)}")

    # Simulate corruption: flip 8 bytes at random positions
    corrupted = bytearray(encoded)
    damage_positions = [0, 3, 7, 10, 15, 18, 22, 25]
    for pos in damage_positions:
        if pos < len(corrupted):
            corrupted[pos] ^= 0xFF   # XOR with 0xFF flips all bits in that byte
    print(f"\nCorrupted : {list(corrupted)}  ({len(damage_positions)} bytes damaged)")

    # Recover
    recovered = decode(bytes(corrupted))
    print(f"\nRecovered : {recovered}")
    print(f"Match     : {recovered == original}")
