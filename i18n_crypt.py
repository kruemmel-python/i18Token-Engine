#!/usr/bin/env python3
import argparse
import ctypes
import platform
from pathlib import Path
from typing import Optional

DEFAULT_LIB_WINDOWS = "i18n_engine.dll"
DEFAULT_LIB_UNIX = "libi18n_engine.so"


def resolve_engine_path(custom: Optional[Path]) -> Path:
    if custom:
        return custom
    return Path(DEFAULT_LIB_WINDOWS if platform.system() == "Windows" else DEFAULT_LIB_UNIX)


def load_library(lib_path: Path) -> ctypes.CDLL:
    if not lib_path.exists():
        raise FileNotFoundError(f"Library {lib_path} not found.")
    return ctypes.CDLL(str(lib_path))


def last_error(engine, lib):
    buf = ctypes.create_string_buffer(1024)
    lib.i18n_last_error_copy(engine, buf, len(buf))
    return buf.value.decode("utf-8", errors="ignore")


def main():
    parser = argparse.ArgumentParser(
        description="Erstellt ein binäres Release-Katalog (Magic Header + Hash)."
    )
    parser.add_argument("input", type=Path, help="UTF-8 Katalogdatei (.txt)")
    parser.add_argument("output", type=Path, help="Ausgabe-Binärdatei (.bin)")
    parser.add_argument("--library", type=Path, help="Pfad zur i18n-Engine (.dll oder .so)")
    parser.add_argument("--strict", action="store_true", help="strict=1 während des Ladens erzwingen")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input file {args.input} nicht gefunden.")

    lib_path = resolve_engine_path(args.library)
    lib = load_library(lib_path)

    lib.i18n_new.restype = ctypes.c_void_p
    lib.i18n_free.argtypes = [ctypes.c_void_p]
    lib.i18n_last_error_copy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    lib.i18n_load_txt_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    lib.i18n_load_txt_file.restype = ctypes.c_int
    lib.i18n_export_binary.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.i18n_export_binary.restype = ctypes.c_int

    engine = lib.i18n_new()
    if not engine:
        raise SystemExit("Konnte Engine nicht initialisieren.")

    try:
        res = lib.i18n_load_txt_file(engine, str(args.input).encode("utf-8"), 1 if args.strict else 0)
        if res < 0:
            raise SystemExit(f"Fehler beim Laden: {last_error(engine, lib)}")

        args.output.parent.mkdir(parents=True, exist_ok=True)
        res = lib.i18n_export_binary(engine, str(args.output).encode("utf-8"))
        if res < 0:
            raise SystemExit(f"Fehler beim Export: {last_error(engine, lib)}")

        print(f"Binärer Katalog erzeugt: {args.output}")
    finally:
        lib.i18n_free(engine)


if __name__ == "__main__":
    main()
