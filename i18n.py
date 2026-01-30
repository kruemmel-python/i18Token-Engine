import ctypes
from ctypes import c_char_p, c_void_p, c_int, POINTER


class I18nEngine:
    def __init__(self, lib_path="./i18n_engine.dll"):
        self.lib = ctypes.CDLL(lib_path)

        self.lib.i18n_new.restype = c_void_p
        self.lib.i18n_free.argtypes = [c_void_p]

        self.lib.i18n_load_txt_file.argtypes = [c_void_p, c_char_p, c_int]
        self.lib.i18n_load_txt_file.restype = c_int

        self.lib.i18n_translate.argtypes = [c_void_p, c_char_p, POINTER(c_char_p), c_int, c_void_p, c_int]
        self.lib.i18n_translate.restype = c_int
        self.lib.i18n_translate_plural.argtypes = [c_void_p, c_char_p, c_int, POINTER(c_char_p), c_int, c_void_p, c_int]
        self.lib.i18n_translate_plural.restype = c_int
        self.lib.i18n_export_binary.argtypes = [c_void_p, c_char_p]
        self.lib.i18n_export_binary.restype = c_int

        self.lib.i18n_get_meta_locale_copy.argtypes = [c_void_p, c_void_p, c_int]
        self.lib.i18n_get_meta_locale_copy.restype = c_int
        self.lib.i18n_get_meta_fallback_copy.argtypes = [c_void_p, c_void_p, c_int]
        self.lib.i18n_get_meta_fallback_copy.restype = c_int
        self.lib.i18n_get_meta_note_copy.argtypes = [c_void_p, c_void_p, c_int]
        self.lib.i18n_get_meta_note_copy.restype = c_int
        self.lib.i18n_get_meta_plural_rule.argtypes = [c_void_p]
        self.lib.i18n_get_meta_plural_rule.restype = c_int
        self.lib.i18n_last_error_copy.argtypes = [c_void_p, c_void_p, c_int]
        self.lib.i18n_last_error_copy.restype = c_int

        self.instance = self.lib.i18n_new()

    def load_file(self, path, strict=True):
        res = self.lib.i18n_load_txt_file(self.instance, path.encode("utf-8"), 1 if strict else 0)
        return res == 0

    def translate(self, token, args=None):
        args = args or []
        c_args, buffers = self._pack_args(args)
        try:
            needed = self.lib.i18n_translate(self.instance,
                                             token.encode("utf-8"),
                                             c_args,
                                             len(args),
                                             None,
                                             0)
            if needed < 0:
                raise RuntimeError(self._last_error())

            buf = ctypes.create_string_buffer(needed + 1)
            self.lib.i18n_translate(self.instance,
                                    token.encode("utf-8"),
                                    c_args,
                                    len(args),
                                    buf,
                                    len(buf))
            return buf.value.decode("utf-8")
        finally:
            buffers.clear()

    def translate_plural(self, token, count, args=None):
        args = args or []
        c_args, buffers = self._pack_args(args)
        try:
            needed = self.lib.i18n_translate_plural(self.instance,
                                                    token.encode("utf-8"),
                                                    count,
                                                    c_args,
                                                    len(args),
                                                    None,
                                                    0)
            if needed < 0:
                raise RuntimeError(self._last_error())

            buf = ctypes.create_string_buffer(needed + 1)
            self.lib.i18n_translate_plural(self.instance,
                                           token.encode("utf-8"),
                                           count,
                                           c_args,
                                           len(args),
                                           buf,
                                           len(buf))
            return buf.value.decode("utf-8")
        finally:
            buffers.clear()

    def get_meta_locale(self):
        return self._copy_string(lambda buf, size: self.lib.i18n_get_meta_locale_copy(self.instance, buf, size))

    def get_meta_fallback(self):
        return self._copy_string(lambda buf, size: self.lib.i18n_get_meta_fallback_copy(self.instance, buf, size))

    def get_meta_note(self):
        return self._copy_string(lambda buf, size: self.lib.i18n_get_meta_note_copy(self.instance, buf, size))

    def get_meta_plural_rule(self):
        raw = self.lib.i18n_get_meta_plural_rule(self.instance)
        return raw if raw >= 0 else 0

    def export_binary(self, output_path):
        return self.lib.i18n_export_binary(self.instance, output_path.encode("utf-8")) == 0

    def _copy_string(self, copier):
        length = copier(None, 0)
        if length <= 0:
            return ""
        buf = ctypes.create_string_buffer(length + 1)
        copier(buf, len(buf))
        return buf.value.decode("utf-8", errors="ignore")

    def _last_error(self):
        return self._copy_string(lambda buf, size: self.lib.i18n_last_error_copy(self.instance, buf, size))

    def _pack_args(self, args):
        if not args:
            return None, []
        array_type = c_char_p * len(args)
        c_args = array_type()
        buffers = []
        for idx, arg in enumerate(args):
            encoded = (arg or "").encode("utf-8")
            buf = ctypes.create_string_buffer(encoded)
            buffers.append(buf)
            c_args[idx] = ctypes.cast(buf, c_char_p)
        return c_args, buffers

    def __del__(self):
        if hasattr(self, "instance"):
            self.lib.i18n_free(self.instance)


# --- Anwendung ---
engine = I18nEngine()
if engine.load_file("locale/de.txt"):
    print(engine.translate("b16b00b", ["5ad32cdde"]))
