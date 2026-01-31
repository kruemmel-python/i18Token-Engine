# i18n Engine – ausführliche Anleitung

Der `i18n_engine`-Stack ist eine binär-katalogbasierte Übersetzungs- und Logik-Engine. Die Texte, Module und sogar die Spiellogik werden ausschließlich durch Token-Sequenzen („Binär-Strings“) gesteuert, während der Host-Code (C++, Python, C#) nur als Interpreter fungiert. Diese Anleitung führt vom DLL-Build über die Python-Integration bis zum konsolenbasierten Spiel und dem Matrix-Terminal durch die wichtigsten Schritte.

---

## 1. Build der DLL (`i18n_engine.dll` / `libi18n_engine.so`)

1. **Toolchain**: Benötigt wird ein C++17-kompatibler Compiler (`g++`, `clang++`, `cl.exe`). Das mitgelieferte `Makefile` nutzt `g++`, kann aber ebenso gegen `cl.exe` angepasst werden.
2. **Makefile-Workflow**:
   * `make` kompiliert `i18n_engine.cpp` + `i18n_api.cpp` zu einer Shared Library (Windows `.dll`, Unix `.so`).
   * `make` startet nach dem Linken automatisch `python i18n_qa.py`, damit jede Token-Änderung automatisch geprüft wird.
   * `make clean` entfernt die alte Ziel-Datei (`i18n_engine.dll` oder `libi18n_engine.so`).
3. **Die Dateien, die der Linker nutzt** (siehe `Makefile`):
   ```
   i18n_engine.cpp    # Kernlogik / Token-Interpreter
   i18n_api.cpp       # C-API-Export
   i18n_engine.h      # Header mit Structs, Flags, Export-Makros
   i18n_qa.py         # QA-Skript (lädt `i18n.py` + Test-Kataloge)
   Makefile           # Compiler-Flags, Targets (Construction-Plan)
   ```
4. **Output**:
   * DLL / Shared Library (`i18n_engine.dll` oder `libi18n_engine.so`) im Projektroot.
   * Die Bibliothek kann sofort via `i18n_wrapper.py`, `I18n.cs` oder andere Language-Bindings geladen werden.
5. **Hilfstools**: `i18n_new_token.py`, `i18n_viz.py` und `i18n_crypt.py` erstellen neue Token, visualisieren die Katalogstruktur oder kompilieren `.i18n`-Pakete.

---

## 2. Verzeichnisstruktur für den Build (Root-Verzeichnis `D:/i18Token`)

```
D:/i18Token/
├── Makefile
├── i18n_engine.cpp
├── i18n_engine.h
├── i18n_api.cpp
├── i18n_api.h
├── i18n_qa.py
├── i18n.py
├── i18n_engine.dll        # Ergebnis nach `make`
├── locale/
│   └── de.txt            # Beispiel-Token-Katalog
├── tests/
│   └── catalogs/          # qa-Kataloge, die `i18n_qa.py` lädt
├── matrix_terminal.py     # Eigenständiges Analysewerkzeug
├── Beispiel_Programm_Python/
│   └── ... (s. Abschnitt 3)
├── README.md
├── CONTRACT.md
└── www/                   # Dokumentation & Demo-Seiten
```

> **Hinweis**: Der `make`-Target verarbeitet ausschließlich die oben gelisteten Quell- und Header-Dateien. Dokumentationen oder Zip-Archive wirken nicht auf den Build. Die erzeugte DLL (`i18n_engine.dll`) wird anschließend in das Python-Spiel (Ordner `Beispiel_Programm_Python`) kopiert oder verlinkt.

---

## 3. Python-Runtime & Spiel (`Beispiel_Programm_Python`)

Das Konsolen-RPG (`game.py`) nutzt `i18n_wrapper.py` (`ctypes`-Binding) um Tokens zu interpretieren. Diese Dateien müssen neben `game.py` liegen, damit die Matrix vollständig funktioniert:

``` 
Beispiel_Programm_Python/
├── game.py
├── i18n_wrapper.py
├── i18n_engine.dll           # Kopie der DLL aus dem Root
├── rpg_catalog.txt          # Master-Katalog (Tokens, Shards, Events)
├── _runtime_catalog.txt     # Generierte Laufzeitebene (Shards/Events/Knowledge)
├── _terminal_catalog.txt    # Temporärer Katalog für das Terminal
├── sector_alpha.txt         # Shard-Datei (Alpha-Prime)
├── sector_wasteland.txt     # Shard-Datei (Daten-Wüste)
├── events/
│   ├── world_aurora.txt     # Aurora-Pulse Event-Schicht
│   └── world_collapse.txt   # Matrix Collapse Event
├── knowledge/
│   ├── knowledge_package_1.txt
│   └── knowledge_package_2.txt
├── knowledge.bin           # Logbuch (wird beim Spiel geschrieben)
├── savegame.raw           # Persistenter Spielstand
├── world_event.raw        # Aktuell aktives Welt-Event
├── matrix_terminal.py     # Terminal Tool (auch hier nutzbar)
└── sector*.txt           # Zusätzliche Shard-Definitionen (optional)
```

> **Neues Menü-Feature:** Das Hauptmenü wird jetzt ebenfalls aus dem Katalog gezogen. Die Tokens `000M100` (Header) und `000M101` (Nummerierte Optionen im Format `1:SCAN:Sektor scannen|...`) definieren die sichtbaren Menüs. Damit reicht ein Austausch von `rpg_catalog.txt`, um die UI komplett auf ein neues Setting (z. B. Fantasy) umzuziehen.

### Runtime-Workflow
1. `python game.py` startet die Matrix-Konsole. Menüoptionen: 1=Scan/Battle, 2=Navigation/Shards, 3=NPC & Shop, 4=Status & Quests, 5=Highscores, 6=Speichern, 7=World-Events.
2. Das Spiel lädt `BASE_CATALOG`, baut `_runtime_catalog.txt` aus aktiven Shards, Events und Knowledge-Paketen und führt Token-Skripte (CALR, Traits, Module) über `execute_token_script()` aus.
3. `matrix_terminal.py` liest `knowledge.bin` + `savegame.raw`, löst Token-IDs auf und visualisiert Status & Logs.
4. Beim Speichern schreibt `game.py` `savegame.raw` (leveled Stats) sowie `knowledge.bin` (Knowledge-Log). Diese Dateien erlauben externen Tools oder „Decrypter“ den Zugriff auf Spielwissen.
5. `events/`-Dateien und `world_event.raw` persistieren globale Zustände; bei Aktivierung werden deren Token in `_runtime_catalog.txt` gemerged.

> **Best Practice**: Kopiere die aktuell gebaute `i18n_engine.dll` aus dem Root in diesen Ordner. Alternativ kannst du das Python-Spiel direkt aus dem Projektroot starten, solange `sys.path` die DLL findet.

---

## 4. Matrix-Terminal („Decrypter“) & Logs

`matrix_terminal.py` zeigt `knowledge.bin` und `savegame.raw` im Klartext. Wichtig:

- Die Terminal-Version lädt dieselben Knowledge-Pakete wie das Spiel und baut `_terminal_catalog.txt` (s. `build_catalog()`).
- Der Output listet:
  1. Alle Knowledge-Pakete (`knowledge.bin` enthält `pkg_id:tok1,tok2,...`)
  2. Die aufgelösten Sätze (via `engine.translate(tok)`)
  3. Die Savegame-Stats (`lvl`, `xp`, `hp`, `max_hp`, `atk`, `credits`, `kills`, `kits`, `qi_target`, `qi_kills`)

Durch dieses Tool lässt sich jeder Knowledge/Log-Token rekonstruieren—ideal für Debugging, Guides oder das externe „Matrix-Terminal“.

---

## 5. Glossar der Konzepte

1. **Token-Scripting**: Module wie `000E10: Instabiler Kern|ATK_ADD:15|HP_SUB:5` werden durch `run_script()` interpretiert. Befehle (`ATK_ADD`, `STAB_SUB`, `REPAIR`, `DEF_ADD`, `CRIT_MUL` etc.) verändern Player-, Boss- oder Weltwerte.
2. **CALR (Context-Aware Logic Retrieval)**: Die Funktion `compose_calr_script()` kombiniert Fraktions-Ruf (`faction_standing`), Knowledge-Token und Welt-Events zu neuen Scripts (ähnlich einem RAG-Modell). Das Ergebnis wird unmittelbar vor jedem Kampf ausgeführt (`execute_dynamic_script()`).
3. **Shard-System**: Navigation lädt Shards, z. B. `sector_alpha.txt`, `sector_wasteland.txt`. Die Token `000W10`, `000W11` enthalten Dateiname + Metadata (NAME, TYPE). `apply_shard_token()` und `refresh_runtime_catalog()` injizieren die entsprechende Datei in `_runtime_catalog.txt`.
4. **World Events**: Aktiviert über Menü (Option 7). `world_event.raw` speichert das Token; zugehörige Datei in `events/` liefert zusätzliche Tokens, Physik-Shift und `battle_message_token`.
5. **Faction & Shop**: `FACTION_SHOP_DEALS` bestimmt, welche Items bei welchem Ruf freigegeben sind. Die Tokens `000G21`, `000C20` usw. zeigen den Ruf und die Shoptexte. Einige Items gewähren Rabatt bei hohem Standing (`threshold` + `discount`).
6. **Knowledge & Logs**: Knowledge-Pakete (`knowledge_package_*.txt`) enthalten Listen von Token-IDs. Beim Kauf schreibt `unlock_knowledge()` diese IDs in `knowledge.bin` und in den Logbuchtext (_Matrix-Terminal_). Diese Tokens treiben z. B. neue Dialoglinien (`knowledge_dialogue_lines()`) oder CALR-Fragmente voran.

---

## 6. Workflow für Entwickler / Studios

1. **DLL neu bauen**:  
   ```bash
   make clean
   make
   ```
   Die neue `i18n_engine.dll` kann sofort in `Beispiel_Programm_Python/` kopiert werden.
2. **Neue Tokens**: Ergänze `rpg_catalog.txt` mit `000Mxx` oder `000Exx` (Scripting, Lore). Nutze `i18n_crypt.py`, um künftige `.i18n`-Pakete zu erzeugen.
3. **Neue Shards/Events**:  
   * Schreibe `sector_*.txt`, definiere `000Wxx`-Token (Dateiname, NAME, TYPE).  
   * Füge Events unter `events/` hinzu und registriere sie in `WORLD_EVENTS`.
   * `refresh_runtime_catalog()` zieht neue Dateien automatisch ins Runtime-Set.
4. **Knowledge-System erweitern**:  
   * Neue `.txt` in `knowledge/` mit Token IDs.  
   * Ergänze `KNOWLEDGE_PACKAGES` in `game.py`.  
   * Linke `knowledge.bin` & `Matrix-Terminal` für Reports.
5. **CALR weiterdenken**: Trage neue `CALR_TEMPLATES`/`CALR_EVENT_BINDINGS` ein. Dadurch erstellt die Engine neue Scripts auf Basis von Reputation + World Event + Knowledge.

---

## 7. Fazit

Die DLL liefert den „Hardware-Layer“, deine `.txt`-Kataloge das „BIOS“. Mit `make`, `game.py`, `matrix_terminal.py`, `events/` und `knowledge.bin` entsteht ein vollständiges Ökosystem, das über Tokens gesteuert wird. Jeder neue Token, jede neue Shard oder jedes Event wird sofort ausgeführt – ohne tiefere Code-Änderungen. Schreibe neue Tokens → kompiliere mit `i18n_crypt.py` → lade sie über `load_file()` – und die Pipeline versteht sie.
