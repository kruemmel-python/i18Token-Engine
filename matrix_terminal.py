import argparse
from pathlib import Path
from typing import List

from i18n_wrapper import I18nEngine
import game


def read_logbook(path: Path):
    entries = []
    if not path.exists():
        return entries
    with path.open("rb") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            pkg_id, rest = line.split(b":", 1)
            tokens = rest.decode("utf-8").split(",") if rest else []
            entries.append((pkg_id.decode("utf-8"), tokens))
    return entries


def build_catalog(engine: I18nEngine, knowledge_ids: List[str]):
    texts = [game.BASE_CATALOG.read_text()]
    for pkg_id in knowledge_ids:
        pkg = game.KNOWLEDGE_PACKAGES.get(pkg_id)
        if pkg and pkg["file"].exists():
            texts.append(pkg["file"].read_text())
    temp = Path("_terminal_catalog.txt")
    temp.write_text("\n".join(texts))
    engine.load_file(str(temp))


def print_savegame(path: Path):
    if not path.exists():
        print("savegame.raw nicht gefunden.")
        return
    data = path.read_text().split(",")
    if len(data) < 10:
        print("Savegame unvollständig.")
        return
    stats = list(map(float, data[:10]))
    print("Savegame:")
    labels = ["lvl", "xp", "hp", "max_hp", "atk", "credits", "kills", "kits", "qi_target", "qi_kills"]
    for label, value in zip(labels, stats):
        print(f"  {label}: {int(value)}")
    if len(data) > 10 and data[10]:
        print("Achievements:", data[10].split(";"))
    if len(data) > 11 and data[11]:
        print("Trait bits:", data[11])
    if len(data) > 12 and data[12]:
        print("Knowledge pkgs:", data[12].split(";"))


def main():
    parser = argparse.ArgumentParser(description="Matrix Terminal: Analysiert Wissen und Savegame.")
    default_dir = Path(__file__).resolve().parent
    parser.add_argument("--game-dir", default=str(default_dir), help="Spielverzeichnis")
    args = parser.parse_args()
    base = Path(args.game_dir).resolve()
    logbook = base / "knowledge.bin"
    savegame = base / "savegame.raw"
    knowledge_ids = [pkg for pkg, _ in read_logbook(logbook)]
    engine = I18nEngine()
    build_catalog(engine, knowledge_ids)
    print("=== Matrix-Terminal ===")
    print("Logbucheinträge:")
    for pkg_id, tokens in read_logbook(logbook):
        resolved = ", ".join(engine.translate(tok) for tok in tokens)
        print(f"  [{pkg_id}] {resolved}")
    print()
    print_savegame(savegame)


if __name__ == "__main__":
    main()
