# Token-basierte I18n Engine (Native Core)

<img width="2752" height="1536" alt="Architecture" src="https://github.com/user-attachments/assets/08c402b7-308e-4eeb-9993-5968bc397962" />

![C++](https://img.shields.io/badge/C++-17-blue.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Eine hochperformante, speichersichere und abhängigkeitsfreie **Internationalisierungs-Engine**, geschrieben in C++17.

Diese Engine implementiert das Konzept der **Token-basierten Übersetzung**: Texte werden im Code nicht durch semantische Schlüssel (z.B. `error.network.timeout`), sondern durch stabile, hexadezimale IDs (z.B. `a1b2c3d`) referenziert. Dies entkoppelt die Entwicklung vollständig von redaktionellen Inhalten und ermöglicht eine Behandlung von Texten als reine Daten-Assets.

Die Engine wird als **Shared Library (.dll / .so)** bereitgestellt und bietet ein universelles **C-ABI**, wodurch sie sich nahtlos in C#, Python, Rust, Node.js und andere Sprachen integrieren lässt.

---

## 🚀 Features

*   **Universelle Kompatibilität**: Sauberes C-Interface (`extern "C"`) für maximale Portabilität.
*   **Zero Dependencies**: Basiert rein auf der C++17 Standardbibliothek (STL). Keine externen Abhängigkeiten.
*   **Mächtige Text-Komposition**:
    *   **Positions-Argumente**: `%0`, `%1` für dynamische Werte zur Laufzeit.
    *   **Inline-Referenzen**: `@TOKEN` erlaubt das Einbetten anderer Textbausteine direkt im Katalog.
    *   **Rekursion**: Vollständige Unterstützung verschachtelter Auflösungen (mit Tiefenlimit).
*   **Robustheit & Sicherheit**:
    *   **Zyklus-Erkennung**: Verhindert Endlosschleifen bei zirkulären Referenzen (statisch & zur Laufzeit).
    *   **Speichersicherheit**: Puffer-Überlaufschutz durch striktes Längenmanagement.
    *   **Determinismus**: Sortierte Ausgaben für konsistente Tests und Diffs.
*   **Developer Experience (DX)**:
    *   Integrierte **Statische Analyse** (`check`) validiert den Katalog auf Integrität.
    *   Debug-Funktionen (`print`, `find`) zur Laufzeitinspektion.

---

## 📦 Build & Installation

Das Projekt verfügt über ein Makefile mit automatischer Betriebssystem-Erkennung (Windows/Linux).

### Voraussetzungen
*   C++17 kompatibler Compiler (GCC, Clang, MSVC)
*   Make

### Kompilieren

```bash
make
```

Dies erzeugt im Projektverzeichnis:
*   **Windows**: `i18n_engine.dll` (Statisch gelinkt, standalone)
*   **Linux**: `libi18n_engine.so`

---

## 📄 Katalog-Format (.txt)

Die Engine liest UTF-8 kodierte Textdateien. Das Format ist zeilenbasiert und auf maximale Lesbarkeit sowie Diff-Freundlichkeit optimiert.

### Syntax
```text
TOKEN{optional_variant}(OptionalesLabel): Textinhalt
```

*   **TOKEN**: Hexadezimal, 6–32 Zeichen (case-insensitive).
    *   **Varianten**: Optional kann eine Variante in geschweiften Klammern folgen (z. B. `{one}`, `{other}`, `{zero}`). Die Engine normalisiert alles auf Kleinbuchstaben.
*   **Label**: Optional, in runden Klammern. Dient nur der Dokumentation.
*   **Text**: Der gesamte Rest der Zeile (inkl. Unicode).

### Beispiel (`de.txt`)
```text
# Kommentare beginnen mit #
12fe3e4(AppTitle): Meine Super App
5ad32cdde(BtnClose): Schließen

# Platzhalter für Laufzeit-Argumente (%0, %1, ...)
b16b00b(Welcome): Willkommen, %0!

# Komposition: Referenz auf andere Tokens mit @
# @12fe3e4 wird durch "Meine Super App" ersetzt.
a1b2c3d(Dialog): @12fe3e4 sagt: @b16b00b
```

### Sonderzeichen & Escaping
*   `@TOKEN` → Referenziert einen anderen Token.
*   `@@` → Literal `@`.
*   `\n`, `\t`, `\r` → Steuerzeichen.
*   `\\` → Literal `\`.

### Meta-Header (optional, bis zur ersten Token-Zeile)

Mehrere `@meta`-Zeilen am Datei-Anfang konfigurieren die Engine und werden dauerhaft gespeichert.

```text
@meta locale=de_DE
@meta plural=DEFAULT
@meta fallback=en_US
@meta note=Internal build 2026-01-31
```

*   `locale`: Beschreibt den Zielregion-Code und kann via `i18n_get_meta_locale_copy` abgefragt werden.
*   `plural`: Aktiviert die Pluralregel – gültige Werte: `DEFAULT`, `SLAVIC`, `ARABIC`. strikte Modi (`strict=1`) verbieten unbekannte Regeln.
*   `fallback`: Hinweis auf eine alternative Sprache. Wird gespeichert, aber nicht automatisch geladen.
*   `note`: Freier Text für Build-Informationen. Wird über `i18n_get_meta_note_copy` lesbar gespeichert.

Alle Meta-Werte (Locale, Plural-Regel, Fallback und Note) werden beim Export ins deterministische Binary übernommen und können über die API (`i18n_get_meta_locale_copy`, `i18n_get_meta_fallback_copy`, `i18n_get_meta_note_copy`, `i18n_get_meta_plural_rule`) erneut ausgelesen werden.

Meta-Zeilen nach der ersten Token-Zeile oder unbekannte Schlüssel lösen im Strict Mode einen Fehler aus. Im lenienten Modus werden sie ignoriert.

### Plural-Regeln

Ohne expliziten Variant-Token (`token{one}`) wählt die Meta-Regel den Namen der Variante, die angefragt werden soll:

| Regel | Entscheidungslogik |
|---|---|
| `DEFAULT` | 0→`zero`, 1→`one`, sonst `other` |
| `SLAVIC` | `one`/`few`/`many`, sonst `other` (klassische ru/pl-Formel) |
| `ARABIC` | `zero`, `one`, `two`, `few`, `many`, sonst `other` |

Die Engine versucht zuerst die gewünschte Variante, danach `token{other}` und zuletzt eine vorhandene Variante oder den Basistoken. Die aktive Regel kann über `i18n_get_meta_plural_rule` abgefragt werden.

---

#### Deterministisches Binary-Release

Die neue Binärdatei (Version 2) beginnt mit einem Header, der `locale`, `fallback`, `note` und die `plural`-Regel per Metadatenblock kodiert und neben `entry_count`/`string_table_size` auch das daraus abgeleitete Checksum-Feld enthält.

- Die Metadaten (Längen + Strings) stehen direkt hinter dem Header und werden beim Laden in der Engine rekonstruiert.
- Header, Metadaten, Entry-Table und String-Table werden in einem FNV1a-Hash kombiniert, damit Bitrot bzw. Transferschäden entdeckt werden.
- `i18n_get_meta_*` (inkl. `i18n_get_meta_note_copy`) kann die im Asset gepackten Locale-, Fallback-, Note- und Plural-Werte lesen. Das `@meta note=...` bleibt ebenfalls im Release erhalten.

Für Authentizität (d. h. ausschließlich signierte Pakete freigeben) sollten Sie zusätzlich eine Signatur oder einen HMAC über das Release schreiben. Die eingebaute Checksumme wird nur zum Schutz gegen zufällige Korruption genutzt.

## 🛠 API Referenz

Die öffentliche Schnittstelle ist in `i18n_api.h` definiert.

### Lifecycle

```c
// Erstellt eine neue Engine-Instanz.
void* i18n_new(void);

// Gibt den Speicher der Instanz frei.
void i18n_free(void* ptr);
```

### Laden

```c
// Lädt einen Katalog aus einem String oder einer Datei.
// strict=1: Bricht bei Syntaxfehlern oder Duplikaten sofort ab.
// Rückgabe: 0 bei Erfolg, -1 bei Fehler.
int i18n_load_txt(void* ptr, const char* txt_str, int strict);
int i18n_load_txt_file(void* ptr, const char* path, int strict);
```

### Fehlerbehandlung

```c
// Gibt die letzte Fehlermeldung zurück (Zeiger gültig bis zum nächsten API-Aufruf).
const char* i18n_last_error(void* ptr);

// Kopiert die Fehlermeldung sicher in einen Puffer.
int i18n_last_error_copy(void* ptr, char* out_buf, int buf_size);
```

Der Pointer bleibt bis zum nächsten API-Aufruf auf derselben Engine-Instanz gültig (die Engine ist nicht threadsicher). Verwenden Sie für zuverlässige Diagnostics immer `i18n_last_error_copy`.

### Übersetzung

```c
// Übersetzt einen Token.
// token: Die ID des Tokens (z.B. "b16b00b").
// args: Array von Strings für Platzhalter %0, %1 etc.
// Rückgabe: Benötigte Länge des Ergebnis-Strings (ohne Null-Terminator).
int i18n_translate(void* ptr, const char* token, const char** args, int args_len, char* out_buf, int buf_size);
```

Hinweis: Die Funktion liefert `>=0` für die benötigte Länge oder `-1` (z. B. wenn `RESULT_TOO_LARGE` in `last_error` steht). Prüfen Sie den Rückgabewert und rufen Sie im Fehlerfall `i18n_last_error_copy` auf.

### Meta-Informationen

```c
// Kopiert die im @meta-Header gespeicherten Werte in den Caller-Puffer.
int i18n_get_meta_locale_copy(void* ptr, char* out_buf, int buf_size);
int i18n_get_meta_fallback_copy(void* ptr, char* out_buf, int buf_size);
int i18n_get_meta_note_copy(void* ptr, char* out_buf, int buf_size);
int i18n_get_meta_plural_rule(void* ptr);
uint32_t i18n_abi_version(void);
uint32_t i18n_binary_version_supported_max(void);
```

Mit diesen Funktionen können Clients die registrierte Locale, Fallback-Sprache, Build-Note und Pluralregel zur Laufzeit auslesen und z. B. UI-Labels oder Tests automatisch anpassen.

### Language Specification v1

* **Inline-Refs:** `@TOKEN` wird direkt aufgelöst, `@@` ergibt ein literales `@`. Inline-Refernzen bleiben argumentfrei; die Komposition lebt ausschließlich im Katalog.
* **Platzhalter:** `%0`, `%1`, … werden nur im aktuellen Text interpretiert. Wenn ein referenzierter Token selbst `%` enthält, wird dessen eigener String ausgeführt – es gibt keinen zweiten globalen Pass.
* **Token-Auflösung:** Argumente, die wie `deadbeef` oder `deadbeef{variant}` aussehen, werden als Token angesehen und aufgelöst. Wer ein Literal benötigt, startet das Argument mit `=` (z. B. `=deadbeef`).
* **Overflow-Guard:** Die APIs geben `>=0` bei erfolgreicher Länge zurück, `-1` signalisiert Fehler (z. B. `RESULT_TOO_LARGE`). Die genaue Meldung steht in `i18n_last_error_copy`.

Diese Spezifikation steht in `CONTRACT.md` und ist der Release‑Freeze für die Textkomposition.

### Pluralübersetzung

```c
// Übersetzt mit Count-basierten Varianten (z.B. token{one}, token{other}).
// count steuert, ob {one} oder {other} genommen wird, {zero} wird bei 0 verwendet.
int i18n_translate_plural(void* ptr, const char* token, int count, const char** args, int args_len, char* out_buf, int buf_size);
```

### Diagnose & Tools

```c
// Führt eine statische Analyse des Katalogs durch.
// Prüft auf: Zyklen, fehlende Referenzen (@TOKEN), Platzhalter-Lücken.
// Rückgabe: 0 = OK, >0 = Fehler.
int i18n_check(void* ptr, char* report_buf, int report_size);

// Gibt den gesamten Katalog tabellarisch aus (sortiert).
int i18n_print(void* ptr, char* out_buf, int buf_size);

// Sucht case-insensitive in Tokens, Labels und Texten.
int i18n_find(void* ptr, const char* query, char* out_buf, int buf_size);
```

---

## 🛡️ Statische Analyse (`check`)

Die `i18n_check` Funktion ist ein mächtiges Werkzeug zur Qualitätssicherung. Sie validiert die logische Konsistenz des Katalogs.

**Erkannte Probleme:**
1.  **Missing References (ERROR)**: Ein Text enthält `@deadbeef`, aber dieser Token existiert nicht.
2.  **Cycles (ERROR)**: Zirkuläre Abhängigkeiten (z.B. A -> B -> A).
3.  **Placeholder Gaps (WARN)**: Ein Text nutzt `%0` und `%2`, aber `%1` fehlt.

**Beispiel-Report:**
```text
CHECK: REPORT
------------------------------
WARN b16b00b: Placeholder-Lücke. Gefunden: %0, %2
ERROR a1b2c3d: Missing inline ref @fffffff
ERROR CYCLE: 123456 -> 654321 -> 123456
------------------------------
CHECK: FAIL
```

---

## 🧰 Hilfsskripte

Das Projekt enthält Python-Skripte zur Unterstützung des Workflows:

*   **`i18n_qa.py`**: Führt den QA-Check (`i18n_check`) aus.
*   **`i18n_crypt.py`**: Lädt den Katalog (strict Mode) und exportiert das neue binäre Release-Format über `i18n_export_binary`.
*   **`i18n_new_token.py`**: Generiert neue, einzigartige Tokens.

**Release-Befehl:**
```bash
python i18n_crypt.py --strict locales/de.txt releases/de.i18n
```

**Beispiel Token-Generierung:**
```bash
# Generiert einen neuen Token (prüft 'locale/' auf Duplikate)
python i18n_new_token.py

# Generiert 5 Tokens mit Länge 8
python i18n_new_token.py --count 5 --length 8
```

Der Default für `--length` liegt inzwischen bei 8 hexadezimalen Zeichen, damit Sie bei großen Katalogen weiter genügend Entropie haben.

---

## 💡 Best Practices

1.  **Strict Mode nutzen**: Laden Sie Kataloge in der Entwicklung immer mit `strict=1`, um Syntaxfehler sofort zu erkennen.
2.  **Check im Build**: Integrieren Sie `i18n_check` in Ihre CI/CD-Pipeline, um defekte Übersetzungen zu verhindern.
3.  **Puffer-Management**: Rufen Sie `i18n_translate` oder `i18n_translate_plural` mit `out_buf=NULL` auf, um die benötigte Größe zu ermitteln, falls die Länge unbekannt ist.
4.  **Release-Format**: Exportieren Sie nach QA mit `python i18n_crypt.py ... releases/*.i18n`, damit die Engine das deterministische Binary mit Header & Checksum lädt.
5.  **Fehler-Handling**: Alle Übersetzungsmethoden liefern `-1` bei Fehlern (z. B. `RESULT_TOO_LARGE`). Die Engine räumt den Fehlerstatus zu Beginn jeder API-Operation, so dass nach einem erfolgreichen Call `i18n_last_error_copy` nur dann einen Wert liefert, wenn dieser Call scheiterte. Prüfen Sie den Rückgabewert und lesen Sie die Fehlermeldung per `i18n_last_error_copy` (der Pointer ist nicht threadsicher).
6.  **Integrität vs. Authentizität**: Die eingebaute Checksum verhindert Bitrot, deckt aber keine Manipulation ab; ergänzen Sie Signaturen/HMACs, wenn nur Ihre Pakete laufen dürfen.
7.  **Threading**: Eine Engine-Instanz ist nicht threadsicher; synchronisieren Sie API-Aufrufe extern oder instanziieren Sie pro Thread eine eigene Engine.

8.  **Ergebnisgrößen-Limit**: `i18n_translate`/`i18n_translate_plural` liefern `RESULT_TOO_LARGE`, wenn das Ergebnis >= 16 MiB ist. Dadurch lässt sich dieser Fehler deterministisch triggern und robust behandeln.

---

## Golden Tests & Contract

Die Engine befindet sich im Freeze-Zustand, sobald folgende Artefakte bereitstehen:

* **CONTRACT.md** definiert `ABI-Version`, `Binary-Version`, die `Language Spec v1` (Tokens/@/%/=`-Escape, Meta, Overflow) und einen Freeze-Plan. Jede Änderung am Contract bedeutet ein bewusstes Breaking-Change und erfordert eine neue ABI oder Binary-Version.
* **tests/run_tests.py** lädt fünf Kataloge (`tests/catalogs/*.txt`) im Strict Mode, führt `i18n_check`, `translate` und `translate_plural` aus, verifiziert Meta-Infos (inkl. `note`), `RESULT_TOO_LARGE` sowie `=`-Escapes. Ein grüner Run bedeutet „Asset-Paket ist stabil“ und contract-conform.

Führen Sie `python tests/run_tests.py` aus, bevor Sie neue Compiler-Versionen oder Release-Pakete bauen. Änderungen, die den Contract berühren, müssen vorher dokumentiert und getestet werden.


© 2024 Token-Based I18n Engine Project

