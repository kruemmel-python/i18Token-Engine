⚪ **Whitepaper: Mycelia Matrix & CALR-Architektur**
Version: 1.9.5 "Gold Freeze"

Kategorie: Middleware / Game Engine Architektur

Status: Feature Complete (Engine Core)

1. **Executive Summary**
Die Mycelia Matrix Engine ist ein hybrides System, das native C++-Performance mit datengetriebenen Spiellogiken verbindet. Der Durchbruch liegt in der völligen Entkopplung von Logik und Code. Der native Kern liefert Token-Interpreten und CALR-Skripte; der Host (Python) ist ein minimalistischer Emulator; sämtliche Spielmechaniken, Menüs, Gegnertexte oder sogar Gegner-Grafiken sind rein durch katalogisierte Token konfigurierbar.

2. **Architektur: Drei Säulen**
- **A. Native Kern (“The Processor”)** – C++17-DLL (`i18n_engine`), zuständig für deterministische Token-Auflösung, String-Translation und Binär-Caching. Nach dem Security-Freeze muss er für neue Szenarien nicht verändert werden.
- **B. Host Surrogate (“game.py”)** – Python 3.12 emuliert Menüs, Ressourcen, Kampf-Loop, Fraktionen und World Events, interpretiert aber keine harte Logik mehr. Vergleichbar mit einer CPU, die nur noch Opcodes ausführt.
- **C. Token-Katalog (“Database / RAG-Basis”)** – `.txt`/`.i18n` Dateien (z. B. `rpg_catalog.txt`, `fantasy_rpg.txt`, die Umgebungsevents, Wissenspakete) definiert alles: CALR-Module, Enemy-Scaling-Token, Menü-Layouts, Gegnernamen, ASCII-Art, Lore-Fragment-Shards.
  * Neuer Trend: Das Menü (Token `000M100`/`000M101`) ist vollständig katalogisiert. Um das UI zu verändern (Matrix → Fantasy), reicht ein Austausch der Katalog-Datei. Das Spiel startet mit dem gleichen Python-Code, weil `parse_menu_entries()` die Variantendefinition liest.
  * Alle UI-Labels, Welt-Events, Gegnernamen (`000E70`/`000E71`) und sogar ASCII-Art (Aether-Wächter, Schattenkern) werden über den Katalog gesteuert.

3. **CALR: Binary RAG**
Vor jedem Kampf werden aus Kontext (Fraktionsstand, Wissen, aktives Welt-Event) passende Logic-Module aus dem Katalog zusammengesetzt (`CALR_TEMPLATES`, `CALR_EVENT_BINDINGS`, `CALR_KNOWLEDGE_FRAGMENTS`). Diese Scripts beinhalten Opcodes wie `ATK_ADD`, `STAB_SUB`, `ENEMY_HP_*` und `ENEMY_ATK_*`, die vom Python-Interpreter (`run_script()`) ausgeführt werden. Die Engine generiert so kein Text, sondern flüchtige Logik-Skripte.

4. **Enemy Scaling & Balance**
Die Bibliothek lädt pro Spielerlevel passende Scaling-Tokens (`000S60`, `000S61`, `000S62`). Die CALR-Module legen playerseitige Buffs fest, während die Enemy-Scaling-Token (z. B. `ENEMY_HP_MUL`, `ENEMY_ATK_ADD`) die Gegnerwerte proportional anpassen. So bleiben Kämpfe gleichmäßig herausfordernd, selbst wenn der Charakter über neue modifier ("CALR-Aurora Pulse") verfügt.

5. **Dynamic Sharding & World Events**
Die Welt wird per Shards aufgebaut: `sector_alpha.txt`, `sector_wasteland.txt` etc. Die Navigation lädt jeweils die passende Datei in `_runtime_catalog.txt`, wodurch sich ASCII-Art, Lore und Physik-Token (z. B. `000C12`) in Echtzeit ändern. Welt-Events (`events/world_collapse.txt`, `events/world_aurora.txt`) injizieren weitere Token, verändern Stabilität und geben spezielle Battle-Messages.

6. **Zero-Code Transformation**
Die Menüs sind kataloggesteuert, Wissen und Traits werden per Logbuch (`knowledge.bin`) geschrieben und vom Matrix-Terminal entschlüsselt. Ein Austausch von `rpg_catalog.txt` gegen `fantasy_rpg.txt` genügt, um die gesamte Oberfläche, Gegnernamen und Lore in ein Fantasy-RPG zu verwandeln. Die domänenspezifische Logik bleibt unverändert; nur die Token-Palette verändert sich.

7. **Metriken**
- Logic-Lookup-Latenz: < 0,01 ms pro Token (native C++ Offset).  
- Memory Footprint: < 45 KB für Runtime-Logikdaten (exkl. DLL).  
- Modularity: 100% (alles über Text-Injektion).  
- Security: Binäre Integrität über verschlüsselte Logbücher (`knowledge.bin`); alle neuen Logs sind via `matrix_terminal.py` rekonstruierbar.

8. **Ausblick**
Das Modell eignet sich für jede genreübergreifende Erfahrung, solange ein Katalog mit den gewünschten Tokens existiert. Neue Worlds, Gegner, Menüs oder sogar neue RAG-Weisen (z. B. weitere CALR-Templates) werden ausschließlich durch neue Tokens eingeführt. Entwicklerteams können so hardwareunabhängig experimentieren, ohne den Kern zu touchieren.

Gezeichnet,  
Der Operator  
Leipzig, Januar 2026
