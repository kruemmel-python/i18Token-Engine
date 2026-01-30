#pragma once

#ifdef _WIN32
  #ifdef I18N_EXPORTS
    #define I18N_API __declspec(dllexport)
  #else
    #define I18N_API __declspec(dllimport)
  #endif
#else
  #define I18N_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

I18N_API void* i18n_new(void);
I18N_API void  i18n_free(void* ptr);

// Pointer bleibt gültig bis zur nächsten Operation auf derselben Engine-Instanz.
I18N_API const char* i18n_last_error(void* ptr);

// Sichere Copy-Variante: returns required bytes (ohne NUL), terminates wenn buf_size>0
I18N_API int i18n_last_error_copy(void* ptr, char* out_buf, int buf_size);

I18N_API int i18n_load_txt(void* ptr, const char* txt_str, int strict);
I18N_API int i18n_load_txt_file(void* ptr, const char* path, int strict);
I18N_API int i18n_reload(void* ptr);

// Returns required bytes (without NUL). If out_buf is NULL or buf_size <= 0, only calculates length.
I18N_API int i18n_translate(void* ptr,
                            const char* token,
                            const char** args,
                            int args_len,
                            char* out_buf,
                            int buf_size);

I18N_API int i18n_print(void* ptr, char* out_buf, int buf_size);
I18N_API int i18n_find(void* ptr, const char* query, char* out_buf, int buf_size);
I18N_API int i18n_check(void* ptr, char* report_buf, int report_size);

#ifdef __cplusplus
}
#endif