#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
import sys

# Regex für Token-Definition: TOKEN(Label): Text
DEF_RE = re.compile(r"^\s*([0-9a-fA-F]{6,32})(?:\((.*?)\))?\s*:\s*(.*)$")
# Regex für Referenzen: @TOKEN
REF_RE = re.compile(r"@([0-9a-fA-F]{6,32})")

def generate_dot(path: Path) -> str:
    if not path.exists():
        return ""

    files = [path] if path.is_file() else list(path.glob("**/*.txt"))
    
    nodes = {} # token -> label
    edges = [] # (source, target)

    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                m = DEF_RE.match(line)
                if m:
                    token = m.group(1).lower()
                    label = m.group(2) or ""
                    text = m.group(3)
                    
                    nodes[token] = label
                    
                    # Suche nach Referenzen im Text
                    for ref in REF_RE.findall(text):
                        edges.append((token, ref.lower()))
        except Exception as e:
            print(f"Warnung bei {f}: {e}", file=sys.stderr)

    # DOT Format generieren
    lines = ["digraph I18nDependencies {", "  rankdir=LR;", "  node [shape=box, style=filled, fillcolor=white];"]
    
    for token, label in nodes.items():
        lbl_str = f"{token}\\n({label})" if label else token
        lines.append(f'  "{token}" [label="{lbl_str}"];')

    for src, dst in edges:
        # Nur Kanten zeichnen, wenn Ziel auch existiert (oder als Missing markieren)
        if dst not in nodes:
             lines.append(f'  "{dst}" [label="{dst}\\n(MISSING)", fillcolor=red];')
        lines.append(f'  "{src}" -> "{dst}";')

    lines.append("}")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Generiert einen Graphviz DOT-Graph der Token-Abhängigkeiten.")
    parser.add_argument("path", type=Path, nargs="?", default=Path("locale"), help="Pfad zu Katalog-Datei oder Ordner")
    parser.add_argument("--output", "-o", type=Path, default=Path("i18n_graph.dot"), help="Ausgabe-Datei")
    
    args = parser.parse_args()
    
    dot_content = generate_dot(args.path)
    args.output.write_text(dot_content, encoding="utf-8")
    
    print(f"Graph gespeichert in: {args.output}")
    print("Visualisieren mit: dot -Tpng i18n_graph.dot -o graph.png")

if __name__ == "__main__":
    main()