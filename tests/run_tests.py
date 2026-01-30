import ctypes
import os
import sys

BASE_DIR = os.path.dirname(__file__)
lib_name = "i18n_engine.dll" if os.name == "nt" else "libi18n_engine.so"
LIB_PATH = os.path.join(BASE_DIR, "..", lib_name)

if not os.path.exists(LIB_PATH):
    print(f"🚫 Library '{LIB_PATH}' fehlt. Bitte vorher 'make' ausführen.")
    sys.exit(1)

lib = ctypes.CDLL(LIB_PATH)

lib.i18n_new.restype = ctypes.c_void_p
lib.i18n_free.argtypes = [ctypes.c_void_p]
lib.i18n_load_txt_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
lib.i18n_load_txt_file.restype = ctypes.c_int
lib.i18n_translate.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
lib.i18n_translate.restype = ctypes.c_int
lib.i18n_translate_plural.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_char_p), ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
lib.i18n_translate_plural.restype = ctypes.c_int
lib.i18n_check.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
lib.i18n_check.restype = ctypes.c_int
lib.i18n_last_error_copy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
lib.i18n_last_error_copy.restype = ctypes.c_int
lib.i18n_get_meta_locale_copy.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
lib.i18n_get_meta_locale_copy.restype = ctypes.c_int
lib.i18n_get_meta_fallback_copy.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
lib.i18n_get_meta_note_copy.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
lib.i18n_get_meta_note_copy.restype = ctypes.c_int
lib.i18n_get_meta_plural_rule.argtypes = [ctypes.c_void_p]
lib.i18n_get_meta_plural_rule.restype = ctypes.c_int
lib.i18n_abi_version.restype = ctypes.c_uint32
lib.i18n_binary_version_supported_max.restype = ctypes.c_uint32


def last_error(engine):
    buf = ctypes.create_string_buffer(512)
    lib.i18n_last_error_copy(engine, buf, len(buf))
    return buf.value.decode("utf-8", errors="ignore")


def prepare_args(args):
    if not args:
        return None, []
    array_type = ctypes.c_char_p * len(args)
    arr = array_type()
    buffers = []
    for idx, arg in enumerate(args):
        buf = ctypes.create_string_buffer(arg.encode("utf-8"))
        buffers.append(buf)
        arr[idx] = ctypes.cast(buf, ctypes.c_char_p)
    return arr, buffers


def translate(engine, token, args=None):
    args = args or []
    arr, buffers = prepare_args(args)
    needed = lib.i18n_translate(engine, token.encode("utf-8"), arr, len(args), None, 0)
    if needed < 0:
        raise RuntimeError(last_error(engine))
    buf = ctypes.create_string_buffer(needed + 1)
    lib.i18n_translate(engine, token.encode("utf-8"), arr, len(args), buf, len(buf))
    return buf.value.decode("utf-8")


def translate_plural(engine, token, count, args=None):
    args = args or []
    arr, buffers = prepare_args(args)
    needed = lib.i18n_translate_plural(engine, token.encode("utf-8"), count, arr, len(args), None, 0)
    if needed < 0:
        raise RuntimeError(last_error(engine))
    buf = ctypes.create_string_buffer(needed + 1)
    lib.i18n_translate_plural(engine, token.encode("utf-8"), count, arr, len(args), buf, len(buf))
    return buf.value.decode("utf-8")


def load_catalog(engine, fname):
    path = os.path.join(BASE_DIR, "catalogs", fname)
    if lib.i18n_load_txt_file(engine, path.encode("utf-8"), 1) != 0:
        raise RuntimeError(f"Load failed for {fname}: {last_error(engine)}")
    return path


def run_check(engine):
    buf = ctypes.create_string_buffer(8192)
    code = lib.i18n_check(engine, buf, len(buf))
    return code, buf.value.decode("utf-8")


def check_meta(engine):
    buf = ctypes.create_string_buffer(128)
    lib.i18n_get_meta_locale_copy(engine, buf, len(buf))
    locale = buf.value.decode("utf-8")
    buf = ctypes.create_string_buffer(128)
    lib.i18n_get_meta_fallback_copy(engine, buf, len(buf))
    fallback = buf.value.decode("utf-8")
    buf = ctypes.create_string_buffer(128)
    lib.i18n_get_meta_note_copy(engine, buf, len(buf))
    note = buf.value.decode("utf-8")
    return locale, fallback, note, lib.i18n_get_meta_plural_rule(engine)


def ensure_contract():
    expected_abi = 1
    expected_binary = 2
    abi = lib.i18n_abi_version()
    max_bin = lib.i18n_binary_version_supported_max()
    if abi != expected_abi or max_bin != expected_binary:
        raise RuntimeError(f"Contract mismatch ABI={abi}({expected_abi}), binary={max_bin}({expected_binary})")


def main():
    ensure_contract()
    tests = [
        ("good_minimal.txt", True),
        ("missing_ref.txt", False),
        ("cycle.txt", False),
        ("plural_variants.txt", True),
        ("args_token_resolution.txt", True),
    ]
    failures = 0
    for fname, should_pass in tests:
        engine = lib.i18n_new()
        try:
            load_catalog(engine, fname)
            code, report = run_check(engine)
            ok = (code == 0)
            if ok != should_pass:
                print(f"❌ {fname}: expected pass={should_pass} but code={code}")
                print(report)
                failures += 1
                continue
            if should_pass and fname == "good_minimal.txt":
                assert translate(engine, "a1b2c3") == "Hallo Welt"
                locale, fallback, note, plural = check_meta(engine)
                assert locale == "de_DE"
                assert fallback == "en_US"
                assert note == "Training 2026"
                assert plural == 0
            if fname == "plural_variants.txt":
                result = translate_plural(engine, "c1c1c1", 2, ["2"])
                assert "2" in result
            if fname == "args_token_resolution.txt":
                assert translate(engine, "aa11bb", ["deadbeef"]) == "Wert Bedeutungsstring"
                assert translate(engine, "cc22dd", ["=deadbeef"]) == "Literal deadbeef"
        except Exception as exc:
            print(f"❌ {fname}: {exc}")
            failures += 1
        finally:
            lib.i18n_free(engine)
    if failures:
        print(f"\n{failures} Tests failed.")
        sys.exit(1)
    print("\n✅ Golden Tests passed.")


if __name__ == "__main__":
    main()
