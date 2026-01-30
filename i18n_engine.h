#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <set>
#include <functional>
#include <cstdint>

class I18nEngine {
private:
  enum class PluralRule : uint8_t {
    DEFAULT = 0,
    SLAVIC  = 1,
    ARABIC  = 2
  };

  std::unordered_map<std::string, std::string> catalog; // token -> text (token may carry variant suffix)
  std::unordered_map<std::string, std::string> labels;  // token -> label (optional)
  std::unordered_map<std::string, std::set<std::string>> plural_variants;
  std::string last_error;
  std::string current_path;
  bool current_strict = false;
  std::string meta_locale;
  std::string meta_fallback;
  std::string meta_note;
  PluralRule meta_plural = PluralRule::DEFAULT;

  static bool is_ws(unsigned char c) noexcept;
  static bool is_digit(unsigned char c) noexcept;
  static bool is_xdigit(unsigned char c) noexcept;
  static bool is_digit_uc(char c) noexcept;
  static bool is_xdigit_uc(char c) noexcept;
  static void trim_inplace(std::string& s);
  static bool is_hex_token(const std::string& s);
  static void strip_utf8_bom(std::string& s);
  static std::string to_lower_ascii(std::string s);
  static std::string unescape_txt_min(const std::string& s);
  static bool parse_line(const std::string& line_in,
                         std::string& out_token,
                         std::string& out_label,
                         std::string& out_text,
                         std::string& out_err);
  static std::string read_file_utf8(const char* path, std::string& err);
  bool load_binary_catalog(const std::string& data, bool strict);
  static bool try_parse_inline_token(const std::string& s, size_t at_pos,
                                     std::string& out_token, size_t& out_advance);
  static void scan_inline_refs(const std::string& text, std::vector<std::string>& out_refs);
  static bool looks_like_binary_catalog(const std::string& data) noexcept;
  static bool parse_variant_suffix(const std::string& token, std::string& out_base, std::string& out_variant);
  static bool is_variant_valid(const std::string& variant) noexcept;
  static uint32_t fnv1a32(const uint8_t* data, size_t len) noexcept;
  static bool parse_meta_line(const std::string& line, std::string& key, std::string& value);
  static PluralRule parse_plural_rule_name(std::string v, bool& ok);
  static const char* pick_variant_name(PluralRule rule, int count) noexcept;
  static bool starts_with(const std::string& s, const char* pref);
  void set_last_error(std::string msg);
  void clear_last_error();
  friend void set_engine_error(I18nEngine* eng, const std::string& msg);
  friend void clear_engine_error(I18nEngine* eng);

  std::string resolve_arg(const std::string& arg,
                          std::unordered_set<std::string>& seen,
                          int depth);
  std::string translate_impl(const std::string& token,
                             const std::vector<std::string>& args,
                             std::unordered_set<std::string>& seen,
                             int depth);
public:
  enum class PublicPluralRule : uint8_t {
    DEFAULT = 0,
    SLAVIC  = 1,
    ARABIC  = 2
  };

  const char* get_last_error() const noexcept;
  const std::string& get_meta_locale() const noexcept;
  const std::string& get_meta_fallback() const noexcept;
  const std::string& get_meta_note() const noexcept;
  PublicPluralRule get_meta_plural_rule() const noexcept;
  bool load_txt_catalog(std::string src, bool strict);
  bool load_txt_file(const char* path, bool strict);
  bool reload();
  std::string translate(const std::string& token_in, const std::vector<std::string>& args);
  std::string translate_plural(const std::string& token_in, int count, const std::vector<std::string>& args);
  std::string dump_table() const;
  std::string find_any(const std::string& query) const;
  std::string check_catalog_report(int& out_code) const;
  bool export_binary_catalog(const char* path) const;
};
