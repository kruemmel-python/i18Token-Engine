import ctypes
import os
import threading
import platform

class I18nEngine:
    def __init__(self, lib_path=None):
        # Falls kein Pfad angegeben wurde, wähle die passende Endung für das OS
        if lib_path is None:
            ext = ".so" if platform.system() == "Linux" else ".dll"
            lib_path = f"./i18n_engine{ext}"
            
        lib_path = os.path.abspath(lib_path)
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Library nicht gefunden: {lib_path}")
            
        self._lib_path = lib_path
        self.lib = ctypes.CDLL(lib_path)
        
        # Deine originalen Signaturen
        self.lib.i18n_new.restype = ctypes.c_void_p
        self.lib.i18n_free.argtypes = [ctypes.c_void_p]
        self.lib.i18n_load_txt_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        self.lib.i18n_last_error.argtypes = [ctypes.c_void_p]
        self.lib.i18n_last_error.restype = ctypes.c_char_p
        self.lib.i18n_translate.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_char_p), ctypes.c_int,
            ctypes.c_char_p, ctypes.c_int
        ]
        
        self._ptr = self.lib.i18n_new()
        self._ptr_lock = threading.RLock()
        self._cache = {}
        self._cache_lock = threading.RLock()

    def load_file(self, path: str):
        path_bytes = os.path.abspath(path).encode("utf-8")
        with self._ptr_lock:
            success = self.lib.i18n_load_txt_file(self._ptr, path_bytes, 0) != -1
        if success:
            self.invalidate_cache()
        return success

    def hot_reload_file(self, path: str):
        def worker():
            if not self.load_file(path):
                err = self.last_error()
                print(f"[I18nEngine] Hot reload failed: {err}")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread

    def translate(self, token: str, args=None) -> str:
        args = args or []
        token_upper = str(token).upper()
        args_tuple = tuple(str(a) for a in args)
        key = (token_upper, args_tuple)
        
        with self._cache_lock:
            cached = self._cache.get(key)
        if cached is not None:
            return cached

        c_args = (ctypes.c_char_p * len(args))(*[a.encode("utf-8") for a in args_tuple])
        
        with self._ptr_lock:
            ptr = self._ptr
        
        size = self.lib.i18n_translate(ptr, token_upper.encode("utf-8"), c_args, len(args), None, 0)
        
        if size < 0:
            result = f"⟦{token_upper}⟧"
        else:
            buf = ctypes.create_string_buffer(size + 1)
            self.lib.i18n_translate(ptr, token_upper.encode("utf-8"), c_args, len(args), buf, size + 1)
            result = buf.value.decode("utf-8").replace("\\n", "\n")

        with self._cache_lock:
            self._cache[key] = result
        return result

    def invalidate_cache(self):
        with self._cache_lock:
            self._cache.clear()

    def last_error(self):
        if not hasattr(self, "_ptr") or not self._ptr:
            return "Engine nicht initialisiert"
        err_ptr = self.lib.i18n_last_error(self._ptr)
        return err_ptr.decode("utf-8") if err_ptr else ""

    def __del__(self):
        if hasattr(self, "_ptr") and self._ptr:
            self.lib.i18n_free(self._ptr)