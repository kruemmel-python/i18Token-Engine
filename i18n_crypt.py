#!/usr/bin/env python3
import argparse
from pathlib import Path

# Muss mit CRYPTO_KEY in i18n_engine.h übereinstimmen (0xDEADC0DE)
KEY = 0xDEADC0DE

def xor_crypt(data: bytes) -> bytes:
    out = bytearray(len(data))
    for i in range(len(data)):
        # Little-endian Byte-Extraktion passend zur C++ Logik
        key_byte = (KEY >> ((i % 4) * 8)) & 0xFF
        out[i] = data[i] ^ key_byte
    return bytes(out)

def main():
    parser = argparse.ArgumentParser(description="Encrypt/Decrypt i18n catalogs (XOR)")
    parser.add_argument("input", type=Path, help="Input file (.txt or .bin)")
    parser.add_argument("output", type=Path, help="Output file")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file {args.input} not found.")
        return

    raw = args.input.read_bytes()
    processed = xor_crypt(raw)
    
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(processed)
    print(f"Processed {len(raw)} bytes.\nSaved to {args.output}")

if __name__ == "__main__":
    main()