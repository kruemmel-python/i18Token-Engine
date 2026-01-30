#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <functional>
#include <cstdint>

class I18nEngine {
private:
  std::unordered_map<std::string, std::string> catalog; // token -> text
  std::unordered_map<std::string, std::string> labels;  // token -> label (optional)
  std::string last_error;
  std::string current_path;
  bool current_strict = false;

  // Ein einfacher 4-Byte Key (kann beliebig komplexer sein)
  static constexpr uint32_t CRYPTO_KEY = 0xDEADC0DE;

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
  static bool try_parse_inline_token(const std::string& s, size_t at_pos,
                                     std::string& out_token, size_t& out_advance);
  static void scan_inline_refs(const std::string& text, std::vector<std::string>& out_refs);
  static void xor_crypt(std::string& data);

  std::string resolve_arg(const std::string& arg,
                          std::unordered_set<std::string>& seen,
                          int depth);
  std::string translate_impl(const std::string& token,
                             const std::vector<std::string>& args,
                             std::unordered_set<std::string>& seen,
                             int depth);

public:
  const char* get_last_error() const noexcept;
  bool load_txt_catalog(std::string src, bool strict);
  bool load_txt_file(const char* path, bool strict);
  bool reload();
  std::string translate(const std::string& token_in, const std::vector<std::string>& args);
  std::string dump_table() const;
  std::string find_any(const std::string& query) const;
  std::string check_catalog_report(int& out_code) const;
};