# i18n Engine – README

Diese Repository-Fragmente bilden die `i18n_engine`-Pipeline, eine binär-basierte Übersetzungs‑/Tokenmaschine, die in C++ entwickelt ist und als DLL (bzw. im C#/.NET-Wrapper) an jede Plattform angebunden werden kann. Das Ziel ist eine Engine für Gameplay-Logik, bei der Texte, Module und sogar prozedurale Szenarien vollständig über Token‑Sequenzen gesteuert werden.

## Inhalt
1. Überblick über die Komponenten
2. Build: DLL & Wrapper
3. Runtime-Setup & Beispiele
4. Extending the catalog / Tokens
5. Tools & Nebenprojekte (Game, Matrix-Terminal, Events)
6. FAQ & Cheatsheet

## 1. Überblick
- `i18n_engine.cpp` / `.h`: Kernimplementation der DLL; das `Makefile` erzeugt über `g++`/`clang++` (oder `msvc`) `i18n_engine.dll`.
- `i18n_wrapper.py` / `I18n.cs`: High-Level-API, die die native DLL lädt und `translate(token)` sowie `load_file(path)` bereitstellt.
- `i18n_new_token.py` / `i18n_viz.py` / `i18n_crypt.py`: Hilfsprogramme zum Generieren neuer Token, Visualisieren des Katalogs und Kompilieren in binäre `.i18n`-Dateien.
- `www/` enthält HTML-Dokumentation und Demoseiten.
- `Beispiel_Programm_Python/` nutzt die DLL über `i18n_wrapper.py` für ein konsolenbasiertes RPG (Kampfsystem, Shops, Fraktionen, Events).

## 1.1 Verzeichnisstruktur (Auszug)
```
D:.
├───Makefile
├───README.md
├───CONTRACT.md
├───i18n_engine.cpp
├───i18n_engine.h
├───i18n_api.cpp
├───i18n_api.h
├───I18n.cs
├───i18n.py
├───i18n_qa.py
├───i18n_viz.py
├───i18n_new_token.py
├───i18n_crypt.py
├───locale/
│   └───de.txt
├───releases/
│   └───(hier entstehen .i18n-Dateien nach Export)
├───tests/
│   ├───run_tests.py
│   └───catalogs/
│       ├───good_minimal.txt
│       ├───missing_ref.txt
│       ├───cycle.txt
│       ├───plural_variants.txt
│       └───args_token_resolution.txt
├───www/
│   └───assets
├───Beispiel_Programm_Python/
│   ├───events/
│   │   ├───world_collapse.txt
│   │   └───world_aurora.txt
│   ├───knowledge/
│   │   ├───knowledge_package_1.txt
│   │   └───knowledge_package_2.txt
│   ├───__pycache__/
│   │   ├───game.cpython-311.pyc
│   │   └───i18n_wrapper.cpython-311.pyc
│   ├───game.py
│   ├───rpg_catalog.txt
│   ├───_runtime_catalog.txt
│   ├───_terminal_catalog.txt
│   ├───i18n_engine.dll
│   ├───i18n_wrapper.py
│   ├───matrix_terminal.py
│   ├───sector_alpha.txt
│   ├───sector_wasteland.txt
│   ├───savegame.raw
│   ├───knowledge.bin
│   └───world_event.raw
```

## 2. Build: DLL & Wrapper
1. **Compiler**: Nutze einen kompatiblen C++17/C++20-Compiler. Unter Windows ist `cl.exe` (Visual Studio) oder `g++` (MSYS2) geeignet, unter Linux `g++`/`clang++`.
2. **Makefile**: Führe `make` (bzw. `nmake`) aus. Der Default-Target kompiliert `i18n_engine.dll` (Windows) oder `libi18n_engine.so` (Linux) aus den Quelltexten `i18n_engine.cpp` + `i18n_api.cpp`. Beispiel:
   ```bash
   make clean
   make
   ```
3. **Makefile-Inputs**: Beim Aufruf von `make` sind folgende Dateien beteiligt:
   ```
   i18n_engine.cpp    # Übersetzer-Logik
   i18n_api.cpp       # API-Glue für DLL Export
   i18n_engine.h      # Header mit Export-Definitionen
   i18n_qa.py         # QA-Skript, läuft automatisch nach Build
   ```
4. **DLL-Verwendung**: Die DLL exportiert eine einfache C-API (`translate`, `load_file`, `set_locale`). Sie liegt nach dem Build im Projektroot (`i18n_engine.dll` oder `.so`).
5. **Python/CS Wrapper**: `i18n_wrapper.py` nutzt `ctypes` und `I18n.cs` `[DllImport]`, solange die DLL neben dem Wrapper liegt. Keine Kompilierung notwendig.

-## 3. Runtime-Setup & Beispiele
-`Beispiel_Programm_Python/game.py`: Startpunkt für das RPG. Abhängigkeiten: Python 3.11+ und alle folgenden Dateien im `Beispiel_Programm_Python`-Ordner:
-```
-Beispiel_Programm_Python/
-├───game.py
-├───rpg_catalog.txt
-├───_runtime_catalog.txt
-├───i18n_engine.dll
-├───i18n_wrapper.py
-├───matrix_terminal.py         # optional für Analyse
-├───events/
-│   ├───world_collapse.txt
-│   └───world_aurora.txt
-├───knowledge/
-│   ├───knowledge_package_1.txt
-│   └───knowledge_package_2.txt
-├───sector_alpha.txt
-├───sector_wasteland.txt
-├───savegame.raw             # wird beim ersten Speichern erzeugt
-├───knowledge.bin           # Logbuch-Datei (optional)
-└───world_event.raw         # Welt-Event-Status (wird von Menü gepflegt)
-```
-`game.py` lädt `i18n_engine.dll`, `rpg_catalog.txt`, `sector_*.txt`, `knowledge/*.txt` und `events/*.txt`. Ohne diese Dateien arbeitet das Token-Interpreter nicht.
-Weitere Hinweise:
-  - `player.save_game()` / `load_game()` verwenden `savegame.raw`.
-  - `matrix_terminal.py` konsumiert `knowledge.bin` und `savegame.raw` zum Debuggen.
-  - Token-Skripte (`000E10`–`000Mxx`) und Fraktionen (`000Gxx`) steuern Traits, Shop-Logik, Events und Welt-Kataloge.
-  - CLI-Menü 1–7 deckt Scan/Battle, Navigation, NPC, Status, Highscores, Speichern und Welt-Events ab.
- `matrix_terminal.py` liest `knowledge.bin` und `savegame.raw`, übersetzt Tokens und stellt ein Terminal zur Verfügung.

## 3. Runtime-Setup & Beispiele
`Beispiel_Programm_Python/game.py` (menübasierte Spielschleife). Um das Spiel zu starten, kopiere/halte die folgenden Dateien im selben Verzeichnis wie `game.py`:
```
game.py
rpg_catalog.txt
_runtime_catalog.txt
_terminal_catalog.txt
i18n_engine.dll
i18n_wrapper.py
matrix_terminal.py                     # optional
sector_alpha.txt
sector_wasteland.txt
knowledge/
events/
savegame.raw (wird beim ersten Speichern erstellt)
knowledge.bin (optional für Logs)
world_event.raw                        # speichert aktives Welt-Event
```
`game.py` lädt die DLL/Kataloge per `i18n_wrapper`, initialisiert Shards, Traits, Fraktionen und Events. Ohne eine der genannten Dateien (insbesondere `i18n_engine.dll`, `rpg_catalog.txt` und die `events/`/`knowledge/`-Sets) funktionieren Features wie Fraktionsshop oder World Events nicht.

## 4. Catalog & Tokens
1. `rpg_catalog.txt`: Zentrale Token-Definitionen – `@meta`-Zeilen, `000100` etc. Jede Zeile `TOKEN_ID: Übersetzung`.
2. Neue Tokens:
   - **Logik**: `000E10`–`000E99` liefern `ATK_ADD`, `STAB_SUB` etc. (Script-Interpreter `execute_token_script`).
   - **Events/Fraktionen**: `000Wxx`, `000Gxx`.
3. **Shard-Dateien** (`sector_alpha.txt`, `sector_wasteland.txt`): Nachladen erlaubt situative Überschreibungen (ASCII-Art, Physiktexte).
4. **Knowledge Packages**: `knowledge/*.txt` und `.i18n` mit `create_binary_package` → dienen als „verschlüsselte Logs“.

## 5. Tools & Erweiterungen
- `i18n_crypt.py` generiert `.i18n` aus `.txt` (verschlüsselt/kompiliert).
- `matrix_terminal.py`: GUI-less Terminal, lädt `knowledge.bin`, baut temporäre Kataloge, zeigt `savegame.raw`.
- `events/`: Enthält `world_collapse.txt`, `world_aurora.txt` – bei aktivem Event werden diese Token in `_runtime_catalog.txt` gemerged.
- `www/docs.html`: Web-Dokumentation – Menüstruktur spiegelt `rpg_catalog` wider.

## 6. Workflow & Tipps
1. **Neue Sprache/Token**: Schreibe neue Zeilen in `.txt`, kompiliere mit `python i18n_crypt.py --strict`.
2. **DLL neu bauen**: `make clean && make release`. DLL im Python-Verzeichnis ablegen (z.B. `Beispiel_Programm_Python/`).
3. **Spiel testen**:  
   ```bash
   cd Beispiel_Programm_Python
   python game.py           # Startet Matrix-Konsole (Menü 1–7)
   python matrix_terminal.py   # Analysiert Logs & Savegames
   ```
4. **Fraktionen**: Shop-Angebote tauchen erst auf, wenn `player.faction_standing[faction] ≥ threshold`. Die `000G21`-Zeilen im Status zeigen Level.
5. **World Events**: Menüoption 7 steuert globale Token; jedes Event hat eigene `000C10`/`000C12`-Beschreibung.

## 7. FAQ
- **Wie füge ich neue Shards hinzu?**  
  1. Neue `.txt` in Root schreiben.  
  2. Token-Definitionen in `rpg_catalog.txt` unter `000W10/000W11` ergänzen.  
  3. In `SHARD_TOKENS` den Token registrieren.  
- **Wie knüpfe ich ein neues Event?**  
  1. Datei unter `events/` ablegen, Tokens definieren (`000C10`, `000WXX`).  
  2. In `WORLD_EVENTS` eintragen (Dateipfad, Bonuswerte, Token).  
  3. Menüoption 7 benutzt `translate_with_fallback` + `refresh_runtime_catalog`.
- **Was tun, wenn Token als `⟦000x⟧` erscheinen?**  
  1. Sicherstellen, dass `_runtime_catalog.txt` die Zeile enthält.  
  2. `translate_with_fallback` nimmt den statischen Katalog als Fallback, `CATALOG_CACHE` erlaubt Offline-Lookups.

## 8. Contribution
- Fork, ändere `rpg_catalog.txt`, verfasse neue `events/*.txt`, baue DLL neu, und paste deine Änderungen.  
- Öffne Pull Request mit:  
   1. Beschreibung der neuen Token/Events.  
   2. Liste der betroffenen Module (`game.py`, `matrix_terminal.py`, `events/*`).  
   3. „Showcase“-Schritte (z. B. wie man Fragment X aus dem Shop kauft).

Für Entwickler oder Studios: Nutzt die Engine als „BIOS“, der Python-Core bleibt schlank, das Gameplay wird komplett über „Token-Aktivitäten“ gesteuert.
