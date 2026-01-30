import ctypes
import platform
import sys

# Konfiguration
LIB_PATH = "./i18n_engine.dll" if platform.system() == "Windows" else "./libi18n_engine.so"
CATALOG_PATH = "locale/de.txt"

def run_health_check():
    try:
        lib = ctypes.CDLL(LIB_PATH)
    except OSError:
        print(f"❌ Fehler: Library '{LIB_PATH}' nicht gefunden. Zuerst 'make' ausführen!")
        sys.exit(1)

    # API Setup
    lib.i18n_new.restype = ctypes.c_void_p
    lib.i18n_last_error_copy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    lib.i18n_last_error_copy.restype = ctypes.c_int
    lib.i18n_check.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    lib.i18n_check.restype = ctypes.c_int
    lib.i18n_load_txt_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]

    engine = lib.i18n_new()
    
    # 1. Katalog laden
    if lib.i18n_load_txt_file(engine, CATALOG_PATH.encode('utf-8'), 1) != 0:
        buf = ctypes.create_string_buffer(1024)
        lib.i18n_last_error_copy(engine, buf, len(buf))
        err = buf.value.decode('utf-8', errors='replace')
        print(f"❌ Kritischer Ladefehler in {CATALOG_PATH}: {err}")
        sys.exit(1)

    # 2. Check ausführen (Puffer für Report reservieren)
    report_buf = ctypes.create_string_buffer(8192)
    exit_code = lib.i18n_check(engine, report_buf, len(report_buf))

    # 3. Ergebnis auswerten
    report_str = report_buf.value.decode('utf-8')
    print(report_str)

    if exit_code != 0:
        print("🛑 BUILD ABGEBROCHEN: Der I18n-Katalog enthält Fehler!")
        sys.exit(exit_code)
    
    print("✅ QA-Check bestanden: Katalog ist konsistent.")
    sys.exit(0)

if __name__ == "__main__":
    run_health_check()
