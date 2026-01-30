# CONTRACT v1 – Freeze des i18nToken Core

## ABI-Version
1

## Binary-Format Version
2 (Magic `I18N`, Meta-Block, Entry Table, String Table, kombinierte FNV1a-Checksum, integrierte Meta-Informationen)

## Language Spec v1

1. **Inline-Referenzen**: `@TOKEN` löst die gewünschte Zeile sofort auf, `@@` ergibt ein literal `@`. Inline-Refs dürfen keine Argumente tragen, die Komposition wird vollständig im Katalog modelliert.
2. **Platzhalter**: `%0`, `%1`, … werden ausschließlich innerhalb des aktuellen Strings entschlüsselt. Referenzierten Tokens wird ihre eigene `%`-Verarbeitung überlassen; es gibt keinen zweiten globalen Ersatzlauf.
3. **Argumentauflösung**: `resolve_arg` interpretiert Argumente, die wie `deadbeef` oder `deadbeef{variant}` aussehen, als Tokens, solange sie gültige Hex-Strings sind. Der Escape `=` (z. B. `=deadbeef`) deaktiviert die Token-Auflösung und gibt das Literal aus.
4. **Meta-Header**: `@meta locale=`, `@meta fallback=`, `@meta plural=`, `@meta note=` dürfen nur vor der ersten Token-Zeile stehen. Die Werte wandern in den Binär-Header und lassen sich via `i18n_get_meta_*` wieder auslesen.
5. **Fehlerverhalten**: `i18n_translate*` und `i18n_check` liefern `-1` bei Fehlern (z. B. `RESULT_TOO_LARGE`). Die letzte Fehlermeldung (siehe `i18n_last_error_copy`) bleibt bis zum nächsten Aufruf auf derselben Engine-Instanz gültig. Die Engine ist nicht threadsicher.
6. **Meta-Note**: Der freie `@meta note` wird explizit gespeichert und kopierbar gemacht, damit Tests und UI-Inspektoren Build-Kontext erhalten.

## Freeze-Plan

1. **Golden Tests:** `tests/run_tests.py` lädt alle Kataloge in `tests/catalogs/` im Strict Mode, verifiziert QA-Reports, tokenbasiertes Argumentverhalten, Meta-Werte (Locale/Fallback/Note/Plural) und die korrekte `RESULT_TOO_LARGE`-Fehlermeldung. Jeder erfolgreiche Lauf signalisiert „Asset-Paket stabil“.
2. **Contract Guard:** Jede Änderung am Contract (ABI, Binary oder Language Spec) muss dokumentiert und durch Golden Tests bestätigt werden. Nach einer Contract-Änderung incrementieren Sie entweder die ABI-Version [API/Schnittstelle] oder die Binary-Version [Release-Format].
3. **Freeze-Kriterien:**  
   * API und Binary bleiben unverändert, solange `CONTRACT.md` nicht angepasst wird.  
   * Neue Features interessieren nur dann, wenn sie vorher durch Contract-Revision freigegeben werden.  
   * Einhaltung des Contract-Textes (Inline-Refs, Placeholder-Policy, Meta-Header, Overflow-Handling) ist Voraussetzung für produktive Releases.

Jede zukünftige Entwicklung beginnt hier: Contract-Änderung → Tests `tests/run_tests.py` → Release.
