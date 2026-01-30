# Token-basierte I18n Engine (Native Core)

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
TOKEN(OptionalesLabel): Textinhalt
```

*   **TOKEN**: Hexadezimal, 6–32 Zeichen (case-insensitive).
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

---

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

### Übersetzung

```c
// Übersetzt einen Token.
// token: Die ID des Tokens (z.B. "b16b00b").
// args: Array von Strings für Platzhalter %0, %1 etc.
// Rückgabe: Benötigte Länge des Ergebnis-Strings (ohne Null-Terminator).
int i18n_translate(void* ptr, const char* token, const char** args, int args_len, char* out_buf, int buf_size);
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
*   **`i18n_crypt.py`**: Verschlüsselt Kataloge für den Release.
*   **`i18n_new_token.py`**: Generiert neue, einzigartige Tokens.

**Beispiel Token-Generierung:**
```bash
# Generiert einen neuen Token (prüft 'locale/' auf Duplikate)
python i18n_new_token.py

# Generiert 5 Tokens mit Länge 8
python i18n_new_token.py --count 5 --length 8
```

---

## 💡 Best Practices

1.  **Strict Mode nutzen**: Laden Sie Kataloge in der Entwicklung immer mit `strict=1`, um Syntaxfehler sofort zu erkennen.
2.  **Check im Build**: Integrieren Sie `i18n_check` in Ihre CI/CD-Pipeline, um defekte Übersetzungen zu verhindern.
3.  **Puffer-Management**: Rufen Sie `i18n_translate` mit `out_buf=NULL` auf, um die benötigte Größe zu ermitteln, falls die Länge unbekannt ist.

---

© 2024 Token-Based I18n Engine Project