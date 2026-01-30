#include "i18n_engine.h"
#include <cstring>
#include <string>

#ifdef _WIN32
  #define EXPORT __declspec(dllexport)
#else
  #define EXPORT
#endif

extern "C" {
  EXPORT void* i18n_new() { return new I18nEngine(); }
  EXPORT void i18n_free(void* ptr) { delete static_cast<I18nEngine*>(ptr); }

  EXPORT const char* i18n_last_error(void* ptr) {
    if (!ptr) return "ptr == nullptr";
    return static_cast<I18nEngine*>(ptr)->get_last_error();
  }

  EXPORT int i18n_last_error_copy(void* ptr, char* out_buf, int buf_size) {
    if (!ptr) return -1;
    auto* e = static_cast<I18nEngine*>(ptr);
    const char* s = e->get_last_error();
    const int len = (int)std::strlen(s);

    if (out_buf && buf_size > 0) {
      const int n = (len < (buf_size - 1)) ? len : (buf_size - 1);
      if (n > 0) std::memcpy(out_buf, s, (size_t)n);
      out_buf[n] = '\0';
    }
    return len;
  }

  // strict = 0/1
  EXPORT int i18n_load_txt(void* ptr, const char* txt_str, int strict) {
    if (!ptr || !txt_str) return -1;
    auto* e = static_cast<I18nEngine*>(ptr);
    return e->load_txt_catalog(txt_str, strict != 0) ? 0 : -1;
  }

  EXPORT int i18n_load_txt_file(void* ptr, const char* path, int strict) {
    if (!ptr || !path) return -1;
    auto* e = static_cast<I18nEngine*>(ptr);
    return e->load_txt_file(path, strict != 0) ? 0 : -1;
  }

  EXPORT int i18n_reload(void* ptr) {
    if (!ptr) return -1;
    auto* e = static_cast<I18nEngine*>(ptr);
    return e->reload() ? 0 : -1;
  }

  EXPORT int i18n_translate(void* ptr,
                            const char* token,
                            const char** args,
                            int args_len,
                            char* out_buf,
                            int buf_size) {
    if (!ptr || !token) return -1;

    std::vector<std::string> vec_args;
    if (args && args_len > 0) {
      vec_args.reserve((size_t)args_len);
      for (int i = 0; i < args_len; ++i) vec_args.emplace_back(args[i] ? args[i] : "");
    }

    auto* e = static_cast<I18nEngine*>(ptr);
    std::string res = e->translate(token, vec_args);

    const int full_len = (int)res.size();
    if (out_buf && buf_size > 0) {
      const int n = (full_len < (buf_size - 1)) ? full_len : (buf_size - 1);
      if (n > 0) std::memcpy(out_buf, res.data(), (size_t)n);
      out_buf[n] = '\0';
    }
    return full_len;
  }

  EXPORT int i18n_print(void* ptr, char* out_buf, int buf_size) {
    if (!ptr) return -1;
    auto* e = static_cast<I18nEngine*>(ptr);
    std::string res = e->dump_table();

    const int full_len = (int)res.size();
    if (out_buf && buf_size > 0) {
      const int n = (full_len < (buf_size - 1)) ? full_len : (buf_size - 1);
      if (n > 0) std::memcpy(out_buf, res.data(), (size_t)n);
      out_buf[n] = '\0';
    }
    return full_len;
  }

  EXPORT int i18n_find(void* ptr, const char* query, char* out_buf, int buf_size) {
    if (!ptr || !query) return -1;
    auto* e = static_cast<I18nEngine*>(ptr);
    std::string res = e->find_any(query);

    const int full_len = (int)res.size();
    if (out_buf && buf_size > 0) {
      const int n = (full_len < (buf_size - 1)) ? full_len : (buf_size - 1);
      if (n > 0) std::memcpy(out_buf, res.data(), (size_t)n);
      out_buf[n] = '\0';
    }
    return full_len;
  }

  EXPORT int i18n_check(void* ptr, char* report_buf, int report_size) {
    if (!ptr) return -1;
    auto* e = static_cast<I18nEngine*>(ptr);

    int code = 0;
    std::string rep = e->check_catalog_report(code);

    const int full_len = (int)rep.size();
    if (report_buf && report_size > 0) {
      const int n = (full_len < (report_size - 1)) ? full_len : (report_size - 1);
      if (n > 0) std::memcpy(report_buf, rep.data(), (size_t)n);
      report_buf[n] = '\0';
    }
    return code;
  }
}