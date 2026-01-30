#include "i18n_engine.h"
#include <algorithm>
#include <fstream>
#include <sstream>
#include <cstring>
#include <cctype>
#include <functional>
#include <cstdint>
#include <filesystem>
#include <limits>

namespace {
constexpr char BINARY_MAGIC[4] = { 'I', '1', '8', 'N' };
constexpr uint8_t BINARY_VERSION_V1 = 1;
constexpr uint8_t BINARY_VERSION_CURRENT = 2;
constexpr uint8_t BINARY_VERSION = BINARY_VERSION_CURRENT;
constexpr size_t BINARY_HEADER_SIZE_V1 = 20;
constexpr size_t BINARY_HEADER_SIZE_V2 = 24;
constexpr size_t BINARY_HEADER_SIZE = BINARY_HEADER_SIZE_V2;
constexpr size_t METADATA_HEADER_SIZE = 6; // locale_len, fallback_len, note_len

uint16_t read_le_u16(const uint8_t* data) {
  return (uint16_t)data[0] | ((uint16_t)data[1] << 8);
}

uint32_t read_le_u32(const uint8_t* data) {
  return (uint32_t)data[0] |
         ((uint32_t)data[1] << 8) |
         ((uint32_t)data[2] << 16) |
         ((uint32_t)data[3] << 24);
}

void append_le_u16(std::vector<uint8_t>& dst, uint16_t value) {
  dst.push_back((uint8_t)(value & 0xFF));
  dst.push_back((uint8_t)((value >> 8) & 0xFF));
}

void append_le_u32(std::vector<uint8_t>& dst, uint32_t value) {
  dst.push_back((uint8_t)(value & 0xFF));
  dst.push_back((uint8_t)((value >> 8) & 0xFF));
  dst.push_back((uint8_t)((value >> 16) & 0xFF));
  dst.push_back((uint8_t)((value >> 24) & 0xFF));
}

uint32_t fnv1a32_append(uint32_t hash, const uint8_t* data, size_t len) {
  uint32_t h = hash;
  for (size_t i = 0; i < len; ++i) {
    h ^= data[i];
    h *= 16777619u;
  }
  return h;
}
} // namespace

void set_engine_error(I18nEngine* eng, const std::string& msg) {
  if (eng) eng->set_last_error(msg);
}

void clear_engine_error(I18nEngine* eng) {
  if (eng) eng->clear_last_error();
}

bool I18nEngine::is_ws(unsigned char c) noexcept { return std::isspace(c) != 0; }
bool I18nEngine::is_digit(unsigned char c) noexcept { return std::isdigit(c) != 0; }
bool I18nEngine::is_xdigit(unsigned char c) noexcept { return std::isxdigit(c) != 0; }
bool I18nEngine::is_digit_uc(char c) noexcept { return std::isdigit((unsigned char)c) != 0; }
bool I18nEngine::is_xdigit_uc(char c) noexcept { return std::isxdigit((unsigned char)c) != 0; }

void I18nEngine::trim_inplace(std::string& s) {
  auto isspace_uc = [](unsigned char c) { return std::isspace(c) != 0; };

  auto it1 = std::find_if_not(s.begin(), s.end(),
                              [&](char ch){ return isspace_uc((unsigned char)ch); });
  auto it2 = std::find_if_not(s.rbegin(), s.rend(),
                              [&](char ch){ return isspace_uc((unsigned char)ch); }).base();

  if (it1 >= it2) { s.clear(); return; }
  s.assign(it1, it2);
}

bool I18nEngine::is_hex_token(const std::string& s) {
  if (s.size() < 6 || s.size() > 32) return false;
  for (unsigned char c : s) if (!is_xdigit(c)) return false;
  return true;
}

void I18nEngine::strip_utf8_bom(std::string& s) {
  if (s.size() >= 3 &&
      (unsigned char)s[0] == 0xEF &&
      (unsigned char)s[1] == 0xBB &&
      (unsigned char)s[2] == 0xBF) {
    s.erase(0, 3);
  }
}

std::string I18nEngine::to_lower_ascii(std::string s) {
  for (char& c : s) c = (char)std::tolower((unsigned char)c);
  return s;
}

std::string I18nEngine::unescape_txt_min(const std::string& s) {
  std::string out;
  out.reserve(s.size());
  for (size_t i = 0; i < s.size(); ++i) {
    if (s[i] == '\\' && i + 1 < s.size()) {
      char c = s[i + 1];
      switch (c) {
        case 'n': out += '\n'; break;
        case 't': out += '\t'; break;
        case 'r': out += '\r'; break;
        case '\\': out += '\\'; break;
        case ':': out += ':'; break;
        default: out += c; break;
      }
      ++i;
    } else {
      out += s[i];
    }
  }
  return out;
}

bool I18nEngine::parse_line(const std::string& line_in,
                            std::string& out_token,
                            std::string& out_label,
                            std::string& out_text,
                            std::string& out_err) {
  out_err.clear();
  out_token.clear();
  out_label.clear();
  out_text.clear();

  std::string line = line_in;
  trim_inplace(line);
  if (line.empty()) return false;
  if (line[0] == '#') return false;

  const auto colon = line.find(':');
  if (colon == std::string::npos) {
    out_err = "Kein ':' gefunden.";
    return false;
  }

  std::string head = line.substr(0, colon);
  std::string text = line.substr(colon + 1);
  trim_inplace(head);
  while (!text.empty() && is_ws((unsigned char)text.front())) text.erase(text.begin());

  std::string token;
  std::string label;

  const auto paren_open = head.find('(');
  if (paren_open == std::string::npos) {
    token = head;
  } else {
    token = head.substr(0, paren_open);
    trim_inplace(token);

    const auto paren_close = head.find(')', paren_open + 1);
    if (paren_close == std::string::npos) {
      out_err = "Label '(' ohne schließende ')'.";
      return false;
    }

    label = head.substr(paren_open + 1, paren_close - (paren_open + 1));
    trim_inplace(label);
  }

  std::string base_token;
  std::string variant_token;

  if (token.find('{') != std::string::npos) {
    if (!parse_variant_suffix(token, base_token, variant_token)) {
      out_err = "Token-Variante ist ungültig.";
      return false;
    }
    token = base_token + '{' + variant_token + '}';
  } else {
    base_token = to_lower_ascii(token);
    token = base_token;
  }

  if (!is_hex_token(base_token)) {
    out_err = "Token ist kein gültiger Hex-String (6–32 Zeichen).";
    return false;
  }

  out_token = std::move(token);
  out_label = std::move(label);
  out_text  = unescape_txt_min(text);
  return true;
}

bool I18nEngine::starts_with(const std::string& s, const char* pref) {
  return s.rfind(pref, 0) == 0;
}

bool I18nEngine::parse_meta_line(const std::string& line, std::string& key, std::string& value) {
  key.clear();
  value.clear();

  std::string s = line;
  trim_inplace(s);
  if (!starts_with(s, "@meta")) return false;

  s.erase(0, 5);
  trim_inplace(s);
  if (s.empty()) return false;

  const auto eq = s.find('=');
  if (eq == std::string::npos) return false;

  key = s.substr(0, eq);
  value = s.substr(eq + 1);
  trim_inplace(key);
  trim_inplace(value);
  key = to_lower_ascii(key);

  return !key.empty() && !value.empty();
}

I18nEngine::PluralRule I18nEngine::parse_plural_rule_name(std::string v, bool& ok) {
  ok = true;
  v = to_lower_ascii(std::move(v));
  if (v == "default") return PluralRule::DEFAULT;
  if (v == "slavic")  return PluralRule::SLAVIC;
  if (v == "arabic")  return PluralRule::ARABIC;
  ok = false;
  return PluralRule::DEFAULT;
}

bool I18nEngine::try_parse_inline_token(const std::string& s, size_t at_pos,
                                        std::string& out_token, size_t& out_advance) {
  out_token.clear();
  out_advance = 1;

  if (at_pos >= s.size() || s[at_pos] != '@') return false;
  if (at_pos + 1 >= s.size()) return false;

  // Escape: @@ -> literal '@'
  if (s[at_pos + 1] == '@') {
    out_advance = 2;
    return false;
  }

  // Token: @ + 6..32 hex
  size_t j = at_pos + 1;
  size_t n = 0;
  while (j < s.size() && n < 32 && is_xdigit_uc(s[j])) { ++j; ++n; }
  if (n < 6) return false;

  out_token = s.substr(at_pos + 1, n);
  for (char& c : out_token) c = (char)std::tolower((unsigned char)c);

  size_t advance = 1 + n;
  if (j < s.size() && s[j] == '{') {
    size_t k = j + 1;
    std::string variant;
    while (k < s.size() && s[k] != '}') {
      variant += s[k];
      ++k;
      if (variant.size() > 16) break;
    }
    if (k >= s.size() || s[k] != '}' || variant.empty()) return false;
    for (char& c : variant) c = (char)std::tolower((unsigned char)c);
    if (!is_variant_valid(variant)) return false;
    out_token += '{';
    out_token += variant;
    out_token += '}';
    advance = (k + 1) - at_pos;
  }

  out_advance = advance;
  return true;
}

void I18nEngine::scan_inline_refs(const std::string& text, std::vector<std::string>& out_refs) {
  out_refs.clear();
  for (size_t i = 0; i < text.size();) {
    if (text[i] != '@') { ++i; continue; }

    // @@ = escape
    if (i + 1 < text.size() && text[i + 1] == '@') { i += 2; continue; }

    std::string tok;
    size_t adv = 1;
    if (try_parse_inline_token(text, i, tok, adv)) {
      out_refs.push_back(tok);
      i += adv;
      continue;
    }

    ++i; // einzelnes '@'
  }

  std::sort(out_refs.begin(), out_refs.end());
  out_refs.erase(std::unique(out_refs.begin(), out_refs.end()), out_refs.end());
}

std::string I18nEngine::resolve_arg(const std::string& arg,
                                    std::unordered_set<std::string>& seen,
                                    int depth) {
  if (!arg.empty() && arg[0] == '=') {
    return arg.substr(1);
  }

  std::string normalized = to_lower_ascii(arg);
  std::string base = normalized;
  std::string variant;
  std::string lookup = normalized;
  if (parse_variant_suffix(normalized, base, variant)) {
    lookup.clear();
    lookup += base;
    lookup += '{';
    lookup += variant;
    lookup += '}';
  } else {
    base = normalized;
  }

  if (!is_hex_token(base)) return arg;

  auto it = catalog.find(lookup);
  if (it == catalog.end()) return arg;

  return translate_impl(lookup, {}, seen, depth + 1);
}

std::string I18nEngine::translate_impl(const std::string& token,
                                       const std::vector<std::string>& args,
                                       std::unordered_set<std::string>& seen,
                                       int depth) {
  if (depth > 32) return "⟦RECURSION_LIMIT⟧";
  if (seen.count(token)) return "⟦CYCLE:" + token + "⟧";
  seen.insert(token);

  auto it = catalog.find(token);
  if (it == catalog.end()) {
    seen.erase(token);
    return "⟦" + token + "⟧";
  }

  const std::string& raw = it->second;
  std::string out;
  out.reserve(raw.size() + 32);

  for (size_t i = 0; i < raw.size();) {
    // --- Inline Token Reference: @deadbeef / @@ ---
    if (raw[i] == '@') {
      std::string ref_tok;
      size_t adv = 1;

      if (try_parse_inline_token(raw, i, ref_tok, adv)) {
        // harte Token-Ref: muss im Catalog sein, sonst sichtbarer Marker
        if (catalog.find(ref_tok) == catalog.end()) out += "⟦MISSING:@" + ref_tok + "⟧";
        else out += translate_impl(ref_tok, {}, seen, depth + 1);

        i += adv;
        continue;
      }

      // @@ -> literal '@'
      if (i + 1 < raw.size() && raw[i + 1] == '@') {
        out += '@';
        i += 2;
        continue;
      }

      // einzelnes '@' ohne gültigen Token: literal
      out += '@';
      ++i;
      continue;
    }

    // --- Placeholder %N ---
    if (raw[i] == '%' && i + 1 < raw.size() && is_digit((unsigned char)raw[i + 1])) {
      size_t j = i + 1;
      int idx = 0;
      while (j < raw.size() && is_digit((unsigned char)raw[j])) {
        idx = idx * 10 + (raw[j] - '0');
        ++j;
      }

      if (idx >= 0 && (size_t)idx < args.size()) out += resolve_arg(args[(size_t)idx], seen, depth);
      else out += "⟦arg:" + std::to_string(idx) + "⟧";

      i = j;
      continue;
    }
    out += raw[i];
    ++i;
  }

  seen.erase(token);
  return out;
}

std::string I18nEngine::read_file_utf8(const char* path, std::string& err) {
  err.clear();
  std::ifstream f(path, std::ios::binary);
  if (!f) { err = "Datei konnte nicht geöffnet werden."; return {}; }
  std::ostringstream ss;
  ss << f.rdbuf();
  if (!f.good() && !f.eof()) { err = "Fehler beim Lesen der Datei."; return {}; }
  return ss.str();
}

const char* I18nEngine::get_last_error() const noexcept { return last_error.c_str(); }

const std::string& I18nEngine::get_meta_note() const noexcept { return meta_note; }

void I18nEngine::set_last_error(std::string msg) { last_error = msg; }

void I18nEngine::clear_last_error() { last_error.clear(); }

const std::string& I18nEngine::get_meta_locale() const noexcept { return meta_locale; }
const std::string& I18nEngine::get_meta_fallback() const noexcept { return meta_fallback; }
I18nEngine::PublicPluralRule I18nEngine::get_meta_plural_rule() const noexcept { return static_cast<PublicPluralRule>(meta_plural); }

bool I18nEngine::load_txt_catalog(std::string src, bool strict) {
  clear_last_error();
  if (src.empty()) { set_last_error("src is empty"); return false; }

  catalog.clear();
  labels.clear();
  meta_locale.clear();
  meta_fallback.clear();
  meta_plural = PluralRule::DEFAULT;
  meta_note.clear();
  plural_variants.clear();

  if (looks_like_binary_catalog(src)) {
    return load_binary_catalog(src, strict);
  }

  strip_utf8_bom(src); // BOM entfernen (falls vorhanden)

  size_t start = 0;
  size_t loaded = 0;
  int line_no = 0;

  auto next_line = [&](std::string& out_line) -> bool {
    if (start >= src.size()) return false;
    size_t end = src.find('\n', start);
    if (end == std::string::npos) end = src.size();

    out_line = src.substr(start, end - start);
    if (!out_line.empty() && out_line.back() == '\r') out_line.pop_back();

    start = (end < src.size()) ? end + 1 : src.size();
    return true;
  };

  std::string line;
  bool meta_phase = true;
  bool seen_any_entry = false;
  while (next_line(line)) {
    ++line_no;

    std::string raw = line;
    trim_inplace(raw);
    if (raw.empty()) continue;
    if (raw[0] == '#') continue;

    if (meta_phase) {
      std::string key, value;
      if (parse_meta_line(raw, key, value)) {
        if (seen_any_entry) {
          if (strict) {
            set_last_error("Meta-Zeile nach Einträgen in Zeile " + std::to_string(line_no));
            return false;
          }
          continue;
        }

        if (key == "locale") {
          meta_locale = value;
          continue;
        }
        if (key == "fallback") {
          meta_fallback = value;
          continue;
        }
        if (key == "note") {
          meta_note = value;
          continue;
        }
        if (key == "plural") {
          bool ok = false;
          meta_plural = parse_plural_rule_name(value, ok);
          if (!ok && strict) {
            set_last_error("Unbekannte Plural-Rule '" + value + "' in Zeile " + std::to_string(line_no));
            return false;
          }
          continue;
        }
        if (strict) {
          set_last_error("Unbekannter Meta-Key '" + key + "' in Zeile " + std::to_string(line_no));
          return false;
        }
        continue;
      }
      meta_phase = false;
    }

    std::string token, label, text, err;
    const bool ok = parse_line(line, token, label, text, err);

    if (!ok) {
      if (strict && !err.empty()) {
        set_last_error("Parse-Fehler in Zeile " + std::to_string(line_no) + ": " + err);
        return false;
      }
      continue;
    }

    std::string base_token = token;
    std::string variant_token;
    if (parse_variant_suffix(token, base_token, variant_token)) {
      if (!variant_token.empty()) plural_variants[base_token].insert(variant_token);
    }

    if (catalog.find(token) != catalog.end()) {
      set_last_error("Doppelter Token in Zeile " + std::to_string(line_no) + ": " + token);
      return false;
    }

    catalog.emplace(token, std::move(text));
    if (!label.empty()) labels.emplace(token, std::move(label));
    ++loaded;
    seen_any_entry = true;
  }

  if (loaded == 0) {
    set_last_error("Kein einziger gültiger Eintrag geladen (leerer Katalog?).");
    return false;
  }
  return true;
}

bool I18nEngine::load_binary_catalog(const std::string& data, bool strict) {
  clear_last_error();
  if (data.size() < BINARY_HEADER_SIZE_V1) {
    set_last_error("Binär-Format: Header zu kurz.");
    return false;
  }

  const uint8_t* raw = reinterpret_cast<const uint8_t*>(data.data());
  if (std::memcmp(raw, BINARY_MAGIC, 4) != 0) {
    set_last_error("Unbekanntes Binär-Format.");
    return false;
  }

  const uint8_t version = raw[4];
  if (version != BINARY_VERSION_V1 && version != BINARY_VERSION) {
    set_last_error("Binär-Format-Version nicht unterstützt.");
    return false;
  }

  meta_locale.clear();
  meta_fallback.clear();
  meta_note.clear();
  meta_plural = PluralRule::DEFAULT;

  const uint8_t flags = raw[5];
  (void)flags;
  uint8_t plural_rule = 0;
  size_t header_size = (version == BINARY_VERSION_V1) ? BINARY_HEADER_SIZE_V1 : BINARY_HEADER_SIZE_V2;
  uint32_t metadata_size = 0;
  if (version >= BINARY_VERSION_CURRENT) {
    plural_rule = raw[6];
    metadata_size = read_le_u32(raw + 20);
    if (metadata_size > data.size() - header_size) {
      set_last_error("Binär-Format: Metadata block zu groß.");
      return false;
    }
    if (metadata_size > 0 && metadata_size < METADATA_HEADER_SIZE) {
      set_last_error("Binär-Format: Metadata block zu kurz.");
      return false;
    }
  }

  if (plural_rule <= static_cast<uint8_t>(PluralRule::ARABIC)) meta_plural = static_cast<PluralRule>(plural_rule);
  const uint32_t entry_count = read_le_u32(raw + 8);
  const uint32_t string_table_size = read_le_u32(raw + 12);
  const uint32_t checksum = read_le_u32(raw + 16);

  size_t metadata_block_offset = header_size;
  if (version >= BINARY_VERSION_CURRENT && metadata_size > 0) {
    if (metadata_block_offset + metadata_size > data.size()) {
      set_last_error("Binär-Format: Metadata block überläuft.");
      return false;
    }
    const uint8_t* meta_ptr = raw + metadata_block_offset;
    const uint16_t locale_len = read_le_u16(meta_ptr);
    const uint16_t fallback_len = read_le_u16(meta_ptr + 2);
    const uint16_t note_len = read_le_u16(meta_ptr + 4);
    const size_t expected = METADATA_HEADER_SIZE + locale_len + fallback_len + note_len;
    if (expected != metadata_size) {
      set_last_error("Binär-Format: Metadata-Länge inkonsistent.");
      return false;
    }
    size_t cursor = metadata_block_offset + METADATA_HEADER_SIZE;
    if (locale_len > 0) meta_locale.assign(reinterpret_cast<const char*>(raw + cursor), locale_len);
    cursor += locale_len;
    if (fallback_len > 0) meta_fallback.assign(reinterpret_cast<const char*>(raw + cursor), fallback_len);
    cursor += fallback_len;
    if (note_len > 0) meta_note.assign(reinterpret_cast<const char*>(raw + cursor), note_len);
    cursor += note_len;
    (void)cursor;
  }

  size_t entry_table_offset = metadata_block_offset + metadata_size;
  size_t offset = entry_table_offset;
  struct EntryInfo {
    std::string base;
    std::string variant;
    uint32_t text_offset;
    uint32_t text_length;
  };

  std::vector<EntryInfo> entries;
  entries.reserve(entry_count);

  for (uint32_t i = 0; i < entry_count; ++i) {
    if (offset >= data.size()) {
      set_last_error("Binär-Format: Eintragstabelle zu kurz.");
      return false;
    }

    const uint8_t token_len = raw[offset++];
    if (token_len < 6 || token_len > 32) {
      set_last_error("Binär-Format: Ungültige Token-Länge.");
      return false;
    }

    if (offset + token_len > data.size()) {
      set_last_error("Binär-Format: Token-Länge überschreitet Daten.");
      return false;
    }

    std::string base(reinterpret_cast<const char*>(raw + offset), token_len);
    offset += token_len;
    base = to_lower_ascii(base);

    const uint8_t variant_len = raw[offset++];
    std::string variant;
    if (variant_len > 0) {
      if (offset + variant_len > data.size()) {
        set_last_error("Binär-Format: Variant-Länge überschreitet Daten.");
        return false;
      }
      variant.assign(reinterpret_cast<const char*>(raw + offset), variant_len);
      offset += variant_len;
      variant = to_lower_ascii(variant);
      if (!is_variant_valid(variant)) {
        set_last_error("Binär-Format: Variant enthält ungültige Zeichen.");
        return false;
      }
    }

    if (!is_hex_token(base)) {
      set_last_error("Binär-Format: Token ist kein Hex-String.");
      return false;
    }

    if (offset + 8 > data.size()) {
      set_last_error("Binär-Format: Eintrag zu kurz.");
      return false;
    }

    const uint32_t text_offset = read_le_u32(raw + offset);
    offset += 4;
    const uint32_t text_length = read_le_u32(raw + offset);
    offset += 4;

    entries.push_back({ base, variant, text_offset, text_length });
  }

  const size_t strings_base = offset;
  if (strings_base + string_table_size > data.size()) {
    set_last_error("Binär-Format: String-Table zu kurz.");
    return false;
  }

  uint32_t computed_checksum = 0;
  if (version == BINARY_VERSION_V1) {
    computed_checksum = fnv1a32(raw + strings_base, string_table_size);
  } else {
    computed_checksum = 2166136261u;
    if (metadata_size > 0) computed_checksum = fnv1a32_append(computed_checksum, raw + metadata_block_offset, metadata_size);
    computed_checksum = fnv1a32_append(computed_checksum, raw + entry_table_offset, strings_base - entry_table_offset);
    computed_checksum = fnv1a32_append(computed_checksum, raw + strings_base, string_table_size);
  }

  if (computed_checksum != checksum) {
    if (strict) {
      set_last_error("Binär-Format: Checksum stimmt nicht.");
      return false;
    }
  }

  catalog.clear();
  labels.clear();
  plural_variants.clear();

  for (const auto& entry : entries) {
    if ((uint64_t)entry.text_offset + entry.text_length > string_table_size) {
      set_last_error("Binär-Format: Text-Offset außerhalb der String-Table.");
      return false;
    }

    const char* text_ptr = reinterpret_cast<const char*>(raw + strings_base + entry.text_offset);
    std::string value(text_ptr, entry.text_length);

    std::string key = entry.base;
    if (!entry.variant.empty()) {
      key += '{';
      key += entry.variant;
      key += '}';

      plural_variants[entry.base].insert(entry.variant);
    }

    if (catalog.find(key) != catalog.end()) {
      set_last_error("Binär-Format: Doppelte Einträge.");
      return false;
    }

    catalog.emplace(std::move(key), std::move(value));
  }

  if (catalog.empty()) {
    set_last_error("Binär-Format: Kein Eintrag enthalten.");
    return false;
  }

  return true;
}

bool I18nEngine::load_txt_file(const char* path, bool strict) {
  clear_last_error();
  if (!path) { set_last_error("path == nullptr"); return false; }
  
  // Pfad und Modus für Reload speichern
  current_path = path;
  current_strict = strict;

  std::string err;
  std::string data = read_file_utf8(path, err);
  if (!err.empty()) { set_last_error(err); return false; }

  return load_txt_catalog(std::move(data), strict);
}

bool I18nEngine::reload() {
  if (current_path.empty()) { set_last_error("No file loaded yet"); return false; }
  // Nutzt den gespeicherten Pfad und Strict-Mode
  return load_txt_file(current_path.c_str(), current_strict);
}

std::string I18nEngine::translate(const std::string& token_in, const std::vector<std::string>& args) {
  std::string token = to_lower_ascii(token_in);
  std::unordered_set<std::string> seen;
  return translate_impl(token, args, seen, 0);
}

std::string I18nEngine::translate_plural(const std::string& token_in,
                                         int count,
                                         const std::vector<std::string>& args) {
  std::string normalized = to_lower_ascii(token_in);
  std::string base;
  std::string variant;
  std::string lookup;
  if (parse_variant_suffix(normalized, base, variant) && !variant.empty()) {
    lookup = base + "{" + variant + "}";
  } else {
    base = normalized;
    const std::string desired = base + "{" + pick_variant_name(meta_plural, count) + "}";
    if (catalog.find(desired) != catalog.end()) {
      lookup = desired;
    } else if (catalog.find(base + "{other}") != catalog.end()) {
      lookup = base + "{other}";
    } else {
      const auto it = plural_variants.find(base);
      if (it != plural_variants.end() && !it->second.empty()) {
        lookup = base + '{' + *it->second.begin() + '}';
      } else {
        lookup = base;
      }
    }
  }

  std::unordered_set<std::string> seen;
  return translate_impl(lookup, args, seen, 0);
}

std::string I18nEngine::dump_table() const {
  std::string out;
  out.reserve(catalog.size() * 64);

  out += "Token        | Label                  | Inhalt\n";
  out += "------------------------------------------------------------\n";

  // Determinismus: Sortiere Keys
  std::vector<std::string> keys;
  keys.reserve(catalog.size());
  for (const auto& kv : catalog) keys.push_back(kv.first);
  std::sort(keys.begin(), keys.end());

  for (const auto& token : keys) {
    const std::string& text = catalog.at(token);
    auto itL = labels.find(token);
    const std::string label = (itL != labels.end()) ? itL->second : "";

    out += token;
    if (token.size() < 12) out.append(12 - token.size(), ' ');
    out += " | ";

    out += label;
    if (label.size() < 22) out.append(22 - label.size(), ' ');
    out += " | ";

    out += text;
    out += "\n";
  }

  return out;
}

std::string I18nEngine::find_any(const std::string& query) const {
  std::string q = query;
  for (char& c : q) c = (char)std::tolower((unsigned char)c);

  std::string out;

  // Determinismus: Sortiere Keys
  std::vector<std::string> keys;
  keys.reserve(catalog.size());
  for (const auto& kv : catalog) keys.push_back(kv.first);
  std::sort(keys.begin(), keys.end());

  for (const auto& token : keys) {
    const std::string& text = catalog.at(token);

    std::string t = text;
    for (char& c : t) c = (char)std::tolower((unsigned char)c);

    std::string lbl;
    auto itL = labels.find(token);
    if (itL != labels.end()) lbl = itL->second;
    std::string l = lbl;
    for (char& c : l) c = (char)std::tolower((unsigned char)c);

    if (t.find(q) != std::string::npos || (!l.empty() && l.find(q) != std::string::npos)) {
      out += token;
      out += "(";
      out += lbl;
      out += "): ";
      out += text;
      out += "\n";
    }
  }

  if (out.empty()) out = "(keine Treffer)\n";
  return out;
}

std::string I18nEngine::check_catalog_report(int& out_code) const {
  out_code = 0;

  if (catalog.empty()) {
    out_code = 2;
    return "CHECK: FAIL\nGrund: Katalog ist leer oder nicht geladen.\n";
  }

  size_t warnings = 0;
  size_t errors = 0;

  std::string report;
  report.reserve(catalog.size() * 96);
  report += "CHECK: REPORT\n";
  report += "------------------------------\n";

  auto scan_placeholders = [](const std::string& s, std::vector<int>& idxs) -> bool {
    idxs.clear();
    for (size_t i = 0; i < s.size();) {
      if (s[i] == '%' && i + 1 < s.size() && std::isdigit((unsigned char)s[i + 1])) {
        size_t j = i + 1;
        int idx = 0;
        while (j < s.size() && std::isdigit((unsigned char)s[j])) {
          if (idx > 1000000) idx = 1000000;
          else idx = idx * 10 + (s[j] - '0');
          ++j;
        }
        idxs.push_back(idx);
        i = j;
        continue;
      }
      ++i;
    }
    if (idxs.empty()) return false;
    std::sort(idxs.begin(), idxs.end());
    idxs.erase(std::unique(idxs.begin(), idxs.end()), idxs.end());
    return true;
  };

  std::vector<int> idxs;
  std::vector<std::string> refs;
  std::unordered_map<std::string, std::vector<std::string>> edges;
  edges.reserve(catalog.size());

  for (const auto& kv : catalog) {
    const std::string& token = kv.first;
    const std::string& text  = kv.second;

    if (scan_placeholders(text, idxs)) {
      bool gap = false;
      int expect = 0;
      for (int got : idxs) { if (got != expect) { gap = true; break; } ++expect; }
      if (gap) {
        ++warnings;
        report += "WARN "; report += token;
        report += ": Placeholder-Lücke. Gefunden: ";
        for (size_t i = 0; i < idxs.size(); ++i) {
          report += "%"; report += std::to_string(idxs[i]);
          if (i + 1 < idxs.size()) report += ", ";
        }
        report += "\n";
      }
    }

    scan_inline_refs(text, refs);
    if (!refs.empty()) edges.emplace(token, refs);

    for (const auto& r : refs) {
      if (catalog.find(r) == catalog.end()) {
        ++errors;
        report += "ERROR "; report += token;
        report += ": Missing inline ref @"; report += r;
        report += "\n";
      }
    }
  }

  enum class Color : unsigned char { White, Gray, Black };
  std::unordered_map<std::string, Color> color;
  color.reserve(catalog.size());
  for (const auto& kv : catalog) color.emplace(kv.first, Color::White);

  std::vector<std::string> stack;
  stack.reserve(64);

  auto dump_cycle = [&](const std::string& start) {
    auto it = std::find(stack.begin(), stack.end(), start);
    report += "ERROR CYCLE: ";
    if (it == stack.end()) { report += start; report += "\n"; return; }
    for (; it != stack.end(); ++it) {
      report += *it;
      report += " -> ";
    }
    report += start;
    report += "\n";
  };

  std::function<void(const std::string&)> dfs = [&](const std::string& u) {
    color[u] = Color::Gray;
    stack.push_back(u);

    auto itE = edges.find(u);
    if (itE != edges.end()) {
      for (const auto& v : itE->second) {
        if (catalog.find(v) == catalog.end()) continue;
        auto cv = color[v];
        if (cv == Color::White) dfs(v);
        else if (cv == Color::Gray) { ++errors; dump_cycle(v); }
      }
    }

    stack.pop_back();
    color[u] = Color::Black;
  };

  for (const auto& kv : catalog) {
    const auto& tok = kv.first;
    if (color[tok] == Color::White) dfs(tok);
  }

  report += "------------------------------\n";
  report += "Tokens: "; report += std::to_string(catalog.size()); report += "\n";
  report += "Warnings: "; report += std::to_string(warnings); report += "\n";
  report += "Errors: "; report += std::to_string(errors); report += "\n";

  if (errors > 0) {
    report += "CHECK: FAIL\n";
    out_code = 3;
  } else if (warnings > 0) {
    report += "CHECK: OK (mit Warnungen)\n";
    out_code = 0;
  } else {
    report += "CHECK: OK\n";
    out_code = 0;
  }

  return report;
}

bool I18nEngine::looks_like_binary_catalog(const std::string& data) noexcept {
  if (data.size() < BINARY_HEADER_SIZE_V1) return false;
  if (std::memcmp(data.data(), BINARY_MAGIC, 4) != 0) return false;
  const uint8_t version = static_cast<uint8_t>(data[4]);
  return version == BINARY_VERSION_V1 || version == BINARY_VERSION;
}

bool I18nEngine::parse_variant_suffix(const std::string& token,
                                      std::string& out_base,
                                      std::string& out_variant) {
  const size_t open = token.find('{');
  const size_t close = (open != std::string::npos) ? token.find('}', open + 1) : std::string::npos;
  if (open == std::string::npos || close == std::string::npos || close != token.size() - 1) {
    return false;
  }

  out_base = token.substr(0, open);
  out_variant = token.substr(open + 1, close - open - 1);
  if (out_variant.empty()) return false;

  out_base = to_lower_ascii(out_base);
  out_variant = to_lower_ascii(out_variant);

  return is_variant_valid(out_variant) && !out_base.empty();
}

const char* I18nEngine::pick_variant_name(PluralRule rule, int count) noexcept {
  if (count < 0) return "other";

  switch (rule) {
    case PluralRule::DEFAULT:
      if (count == 0) return "zero";
      if (count == 1) return "one";
      return "other";

    case PluralRule::SLAVIC: {
      const int mod10 = count % 10;
      const int mod100 = count % 100;
      if (mod10 == 1 && mod100 != 11) return "one";
      if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return "few";
      if (mod10 == 0 || (mod10 >= 5 && mod10 <= 9) || (mod100 >= 11 && mod100 <= 14)) return "many";
      return "other";
    }

    case PluralRule::ARABIC: {
      const int mod100 = count % 100;
      if (count == 0) return "zero";
      if (count == 1) return "one";
      if (count == 2) return "two";
      if (mod100 >= 3 && mod100 <= 10) return "few";
      if (mod100 >= 11 && mod100 <= 99) return "many";
      return "other";
    }
  }
  return "other";
}

bool I18nEngine::is_variant_valid(const std::string& variant) noexcept {
  if (variant.empty() || variant.size() > 16) return false;
  for (char c : variant) {
    const unsigned char uc = (unsigned char)c;
    if (!(std::islower(uc) || std::isdigit(uc) || c == '_' || c == '-')) return false;
  }
  return true;
}

uint32_t I18nEngine::fnv1a32(const uint8_t* data, size_t len) noexcept {
  uint32_t hash = 2166136261u;
  for (size_t i = 0; i < len; ++i) {
    hash ^= data[i];
    hash *= 16777619u;
  }
  return hash;
}

bool I18nEngine::export_binary_catalog(const char* path) const {
  if (!path || catalog.empty()) return false;

  struct ExportEntry {
    std::string base;
    std::string variant;
    std::string text;
    uint32_t text_offset;
    uint32_t text_length;
  };

  std::vector<ExportEntry> entries;
  entries.reserve(catalog.size());

  for (const auto& kv : catalog) {
    std::string base;
    std::string variant;
    if (!parse_variant_suffix(kv.first, base, variant)) {
      base = kv.first;
      variant.clear();
    }

    if (base.empty() || !is_hex_token(base)) return false;

    entries.push_back({ base, variant, kv.second, 0, 0 });
  }

  std::sort(entries.begin(), entries.end(), [](const ExportEntry& a, const ExportEntry& b) {
    if (a.base != b.base) return a.base < b.base;
    return a.variant < b.variant;
  });

  uint32_t current_offset = 0;
  for (auto& entry : entries) {
    entry.text_offset = current_offset;
    entry.text_length = (uint32_t)entry.text.size();
    current_offset += entry.text_length;
  }

  std::vector<uint8_t> entry_table;
  entry_table.reserve(entries.size() * 64);

  for (const auto& entry : entries) {
    entry_table.push_back((uint8_t)entry.base.size());
    entry_table.insert(entry_table.end(), entry.base.begin(), entry.base.end());
    entry_table.push_back((uint8_t)entry.variant.size());
    entry_table.insert(entry_table.end(), entry.variant.begin(), entry.variant.end());
    append_le_u32(entry_table, entry.text_offset);
    append_le_u32(entry_table, entry.text_length);
  }

  std::vector<uint8_t> string_table;
  string_table.reserve(current_offset);
  for (const auto& entry : entries) {
    string_table.insert(string_table.end(), entry.text.begin(), entry.text.end());
  }

  const size_t cap_locale = std::min(meta_locale.size(), (size_t)std::numeric_limits<uint16_t>::max());
  const size_t cap_fallback = std::min(meta_fallback.size(), (size_t)std::numeric_limits<uint16_t>::max());
  const size_t cap_note = std::min(meta_note.size(), (size_t)std::numeric_limits<uint16_t>::max());
  const uint16_t locale_len = (uint16_t)cap_locale;
  const uint16_t fallback_len = (uint16_t)cap_fallback;
  const uint16_t note_len = (uint16_t)cap_note;

  std::vector<uint8_t> metadata_block;
  metadata_block.reserve(METADATA_HEADER_SIZE + cap_locale + cap_fallback + cap_note);
  append_le_u16(metadata_block, locale_len);
  append_le_u16(metadata_block, fallback_len);
  append_le_u16(metadata_block, note_len);
  if (locale_len > 0) metadata_block.insert(metadata_block.end(), meta_locale.begin(), meta_locale.begin() + locale_len);
  if (fallback_len > 0) metadata_block.insert(metadata_block.end(), meta_fallback.begin(), meta_fallback.begin() + fallback_len);
  if (note_len > 0) metadata_block.insert(metadata_block.end(), meta_note.begin(), meta_note.begin() + note_len);
  const uint32_t metadata_size = (uint32_t)metadata_block.size();

  uint32_t checksum = 2166136261u;
  if (metadata_size > 0) checksum = fnv1a32_append(checksum, metadata_block.data(), metadata_block.size());
  checksum = fnv1a32_append(checksum, entry_table.data(), entry_table.size());
  checksum = fnv1a32_append(checksum, string_table.data(), string_table.size());

  uint8_t plural_rule = static_cast<uint8_t>(meta_plural);
  if (plural_rule > static_cast<uint8_t>(PluralRule::ARABIC)) plural_rule = static_cast<uint8_t>(PluralRule::DEFAULT);

  std::vector<uint8_t> header;
  header.reserve(BINARY_HEADER_SIZE);
  header.insert(header.end(), BINARY_MAGIC, BINARY_MAGIC + 4);
  header.push_back(BINARY_VERSION);
  header.push_back(0);
  header.push_back(plural_rule);
  header.push_back(0);
  append_le_u32(header, (uint32_t)entries.size());
  append_le_u32(header, (uint32_t)string_table.size());
  append_le_u32(header, checksum);
  append_le_u32(header, metadata_size);

  std::vector<uint8_t> buffer;
  buffer.reserve(header.size() + metadata_block.size() + entry_table.size() + string_table.size());
  buffer.insert(buffer.end(), header.begin(), header.end());
  if (metadata_size > 0) buffer.insert(buffer.end(), metadata_block.begin(), metadata_block.end());
  buffer.insert(buffer.end(), entry_table.begin(), entry_table.end());
  buffer.insert(buffer.end(), string_table.begin(), string_table.end());

  std::filesystem::path out_path(path);
  if (out_path.has_parent_path()) {
    std::filesystem::create_directories(out_path.parent_path());
  }

  std::ofstream out(out_path, std::ios::binary);
  if (!out) return false;
  out.write(reinterpret_cast<const char*>(buffer.data()), (std::streamsize)buffer.size());
  return out.good();
}
