## Purpose

Gib einer KI wie Codex oder Gemini eine glasklare Anleitung, wie sie die vorhandene `i18n_engine.dll` (bzw. `libi18n_engine.so`) in **jedem beliebigen Projekt** nutzen kann. Die KI soll eigenständig eine passende Programmiersprache wählen, die Engine laden, einen Token-Katalog erzeugen und anschließend Beispieltext übersetzen oder rendern können, ohne noch einmal nachschauen zu müssen.

## Kontext

- Die Engine ist standalone (C++17) und liefert eine C-ABI. Die DLL liegt im Projektordner (Windows) oder als `.so` (Linux).  
- Die wichtigsten Hilfs-Skripte sind `i18n_new_token.py` (automatische Token-Erstellung), `i18n_qa.py` (Validierung) und `i18n_crypt.py` (Binary-Release).  
- Tokens sind hexadezimal, 6–32 Zeichen lang, optional mit Parentheses-Label (`TOKEN(Label)`), und der Text folgt nach einem Doppelpunkt, z. B. `deadbeef(Room_Start): Willkommen @feed`. Inline-Referenzen (`@TOKEN`), Platzhalter (`%0`, `%1`) und Escapes (`@@` für ein literal `@`) sind erlaubt.

## Ziel der KI

1. Den Build-Status des Projekts erkennen (DLL/SO vorhanden).  
2. Eine Programmiersprache wählen (z. B. Python, C#, C++), die die DLL über FFI lädt.  
3. Eine gültige `tokens.txt` oder `world.txt` erzeugen, inklusive:
   - Meta-Header (`@meta locale=de_DE`, `@meta fallback=en_US`, `@meta plural=SLAVIC`, `@meta note="Build yyyy-mm-dd"`).  
   - Mindestens drei Token-Einträge mit Referenzen und Platzhaltern.  
   - Einen `QA`-freundlichen Ablauf (keine Lücken in Platzhaltern, keine zyklischen Referenzen).  
4. Die DLL laden (`i18n_new`, `i18n_load_txt_file`, `i18n_translate`, `i18n_translate_plural`, `i18n_check`, `i18n_last_error_copy` etc.).  
5. Die Übersetzung des Tokens durchführen, zuerst `out_buf=null` zum Längen-Check, dann mit Puffer.  
6. Optional: Einen Binary Export (`i18n_crypt.py --strict locales/de.txt releases/de.i18n`) vorbereiten und den Strict-Mode für QA erwähnen.

## Struktur der Antwort

Die KI soll die Aufgabe in klare Schritte aufbauen:

1. **Setup:** Benötigte Abhängigkeiten (z. B. `ctypes`, `ffi`, Build-System).  
2. **Token-Katalog erzeugen:** Beschreibe die Textdatei, zeige Beispiel-Tokens, erkläre `i18n_new_token.py`/Meta-Zeilen.  
3. **DLL laden & verwenden:** Zeige den vollständigen API-Flow (Instanziieren, Laden, Übersetzen, QA, Release) in der gewählten Sprache.  
4. **Testlauf:** Simuliere eine kleine Konsole oder API, die den übersetzten Text zusammen mit Platzhaltern ausgibt.  
5. **Quality Gate:** Zeige, wie `i18n_check` aufgerufen und ausgewertet wird; welchen Exit-Code erwartet man, wie `RESULT_TOO_LARGE` verarbeitet wird.  
6. **Release:** Wenn möglich, beschreibe den Binary-Export und wie der Client die `.i18n`-Datei lädt.

## Details für die Programmiersprache

- **Python (ctypes)**: `ctypes.CDLL("i18n_engine.dll")`, `i18n_new.restype = ctypes.c_void_p`, `i18n_load_txt_file(handle, path.encode(), strict_flag)`, `i18n_translate` im Double-Call-Modus, `create_string_buffer`.  
- **C# (DllImport)**: `[DllImport("i18n_engine.dll")] static extern IntPtr i18n_new();` etc. Nutze `Marshal` für Strings.  
- **C/C++**: `void* i18n_new();`, `int i18n_translate(void* ptr, const char* token, const char** args, int args_len, char* out_buf, int buf_size);` und `i18n_load_txt_file`.

Wenn die KI eine andere Sprache bevorzugt, soll sie das FFI-Modul bzw. per-Platform-Layer beschreiben. Wichtig: Die DLL-Instanz muss am Ende sauber freigegeben werden (z. B. `i18n_free` oder Dispose-Pattern).

## Zusätzliche Hinweise

- Erzeuge immer eine `README`-ähnliche Erklärung zum Ablauf für zukünftige Menschen.  
- Verweise auf vorhandene Tools (z. B. `i18n_qa.py`/`i18n_crypt.py`) mit konkreten Befehlen.  
- The AI soll am Ende mögliche Fehler (z. B. fehlende Token im Katalog) beschreiben und wie man `i18n_last_error_copy` nutzt.

Gib diese Datei als Referenz an die KI weiter, bevor sie mit dem Code startet; so bleibt die Dokumentation konsistent.
