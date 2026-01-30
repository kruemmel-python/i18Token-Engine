import ctypes
from ctypes import c_char_p, c_void_p, c_int, POINTER

class I18nEngine:
    def __init__(self, lib_path="./i18n_engine.dll"):
        # Laden der Library
        self.lib = ctypes.CDLL(lib_path)
        
        # Funktions-Signaturen definieren
        self.lib.i18n_new.restype = c_void_p
        self.lib.i18n_free.argtypes = [c_void_p]
        
        self.lib.i18n_load_txt_file.argtypes = [c_void_p, c_char_p, c_int]
        self.lib.i18n_load_txt_file.restype = c_int
        
        self.lib.i18n_translate.argtypes = [c_void_p, c_char_p, POINTER(c_char_p), c_int, c_char_p, c_int]
        self.lib.i18n_translate.restype = c_int

        self.instance = self.lib.i18n_new()

    def load_file(self, path, strict=True):
        res = self.lib.i18n_load_txt_file(self.instance, path.encode('utf-8'), 1 if strict else 0)
        return res == 0

    def translate(self, token, args=[]):
        # Vorbereitung der Argumente für C-ABI
        c_args = (c_char_p * len(args))(*[a.encode('utf-8') for a in args])
        
        # Erster Aufruf: Benötigte Puffergröße ermitteln
        needed = self.lib.i18n_translate(self.instance, token.encode('utf-8'), c_args, len(args), None, 0)
        
        # Zweiter Aufruf: Mit Puffer abrufen
        buf = ctypes.create_string_buffer(needed + 1)
        self.lib.i18n_translate(self.instance, token.encode('utf-8'), c_args, len(args), buf, len(buf))
        
        return buf.value.decode('utf-8')

    def __del__(self):
        if hasattr(self, 'instance'):
            self.lib.i18n_free(self.instance)

# --- Anwendung ---
engine = I18nEngine()
if engine.load_file("locale/de.txt"):
    # Beispiel: b16b00b(Welcome): Willkommen, %0!
    # sad32cdde(UserName): Ralf
    print(engine.translate("b16b00b", ["sad32cdde"])) 
    # Output: Willkommen, Ralf!