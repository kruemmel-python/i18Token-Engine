#!/usr/bin/env python3
import argparse
import secrets
import re
import sys
from pathlib import Path

# Regex für Token am Zeilenanfang: hex(t) + optional variant + optional label
TOKEN_RE = re.compile(r"^\s*([0-9a-fA-F]{6,32})(?:\{[0-9a-zA-Z_\-]+\})?(?:\(.*\))?\s*:")

def get_existing_tokens(path: Path) -> set[str]:
    tokens = set()
    if not path.exists():
        return tokens
    
    files = []
    if path.is_file():
        files.append(path)
    else:
        files.extend(path.glob("**/*.txt"))
    
    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                m = TOKEN_RE.match(line)
                if m:
                    tokens.add(m.group(1).lower())
        except Exception as e:
            print(f"Warnung: Fehler beim Lesen von {f}: {e}", file=sys.stderr)
    
    return tokens

def generate_token(length: int) -> str:
    # token_hex(n) liefert 2*n Zeichen. Wir brauchen length.
    # (length + 1) // 2 bytes reichen.
    return secrets.token_hex((length + 1) // 2)[:length]

def main():
    parser = argparse.ArgumentParser(description="Generiert einzigartige Hex-Tokens für die i18n Engine.")
    parser.add_argument("path", type=Path, nargs="?", default=Path("locale"), 
                        help="Pfad zur Katalog-Datei oder Ordner (für Duplikat-Check)")
    parser.add_argument("--length", "-l", type=int, default=8, help="Länge des Tokens (6-32)")
    parser.add_argument("--count", "-n", type=int, default=1, help="Anzahl der Tokens")
    
    args = parser.parse_args()

    if args.length < 6 or args.length > 32:
        print("Fehler: Länge muss zwischen 6 und 32 liegen.", file=sys.stderr)
        sys.exit(1)

    existing = get_existing_tokens(args.path)
    
    count = 0
    while count < args.count:
        token = generate_token(args.length)
        if token not in existing:
            print(token)
            existing.add(token) # Verhindert Duplikate im selben Lauf
            count += 1

if __name__ == "__main__":
    main()
