import ctypes
import os

class I18nEngine:
    def __init__(self, lib_path="./i18n_engine.dll"):
        lib_path = os.path.abspath(lib_path)
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"DLL nicht gefunden: {lib_path}")
        self.lib = ctypes.CDLL(lib_path)
        self.lib.i18n_new.restype = ctypes.c_void_p
        self.lib.i18n_free.argtypes = [ctypes.c_void_p]
        self.lib.i18n_load_txt_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self.lib.i18n_translate.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, 
            ctypes.POINTER(ctypes.c_char_p), ctypes.c_int, 
            ctypes.c_char_p, ctypes.c_int
        ]
        self._ptr = self.lib.i18n_new()

    def load_file(self, path: str):
        return self.lib.i18n_load_txt_file(self._ptr, os.path.abspath(path).encode('utf-8'), 0) != -1

    def translate(self, token: str, args: list = []) -> str:
        token_upper = str(token).upper()
        c_args = (ctypes.c_char_p * len(args))(*[str(a).encode('utf-8') for a in args])
        size = self.lib.i18n_translate(self._ptr, token_upper.encode('utf-8'), c_args, len(args), None, 0)
        if size < 0: return f"⟦{token_upper}⟧"
        buf = ctypes.create_string_buffer(size + 1)
        self.lib.i18n_translate(self._ptr, token_upper.encode('utf-8'), c_args, len(args), buf, size + 1)
        return buf.value.decode('utf-8').replace("\\n", "\n")

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr:
            self.lib.i18n_free(self._ptr)