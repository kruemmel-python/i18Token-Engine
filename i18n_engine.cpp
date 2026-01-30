#include "i18n_engine.h"
#include <algorithm>
#include <fstream>
#include <sstream>
#include <cstring>
#include <cctype>
#include <functional>
#include <cstdint>

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

  if (!is_hex_token(token)) {
    out_err = "Token ist kein gültiger Hex-String (6–32 Zeichen).";
    return false;
  }

  token = to_lower_ascii(std::move(token));

  out_token = std::move(token);
  out_label = std::move(label);
  out_text  = unescape_txt_min(text);
  return true;
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

  out_advance = 1 + n;
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

void I18nEngine::xor_crypt(std::string& data) {
  for (size_t i = 0; i < data.size(); ++i) {
    data[i] ^= ((CRYPTO_KEY >> ((i % 4) * 8)) & 0xFF);
  }
}

std::string I18nEngine::resolve_arg(const std::string& arg,
                                    std::unordered_set<std::string>& seen,
                                    int depth) {
  if (!is_hex_token(arg)) return arg;

  std::string tok = to_lower_ascii(arg);
  if (catalog.find(tok) == catalog.end()) return arg;

  return translate_impl(tok, {}, seen, depth + 1);
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

bool I18nEngine::load_txt_catalog(std::string src, bool strict) {
  last_error.clear();
  if (src.empty()) { last_error = "src is empty"; return false; }

  catalog.clear();
  labels.clear();

  // Heuristik: Wenn das erste Byte >= 0x80 ist (und kein BOM), ist es wahrscheinlich verschlüsselt.
  // (Klartext-Kataloge beginnen meist mit '#' (0x23) oder Token-Hex-Digits (ASCII))
  bool looks_encrypted = true;
  if (src.size() >= 3 && (unsigned char)src[0] == 0xEF && (unsigned char)src[1] == 0xBB && (unsigned char)src[2] == 0xBF) {
    looks_encrypted = false; // BOM vorhanden -> Klartext
  } else if ((unsigned char)src[0] < 0x80) {
    looks_encrypted = false; // ASCII Start -> Klartext
  }

  if (looks_encrypted) xor_crypt(src);
  strip_utf8_bom(src); // BOM entfernen (falls im Klartext oder nach Entschlüsselung vorhanden)

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
  while (next_line(line)) {
    ++line_no;

    std::string token, label, text, err;
    const bool ok = parse_line(line, token, label, text, err);

    if (!ok) {
      if (strict && !err.empty()) {
        last_error = "Parse-Fehler in Zeile " + std::to_string(line_no) + ": " + err;
        return false;
      }
      continue;
    }

    if (catalog.find(token) != catalog.end()) {
      last_error = "Doppelter Token in Zeile " + std::to_string(line_no) + ": " + token;
      return false;
    }

    catalog.emplace(token, std::move(text));
    if (!label.empty()) labels.emplace(token, std::move(label));
    ++loaded;
  }

  if (loaded == 0) {
    last_error = "Kein einziger gültiger Eintrag geladen (leerer Katalog?).";
    return false;
  }
  return true;
}

bool I18nEngine::load_txt_file(const char* path, bool strict) {
  last_error.clear();
  if (!path) { last_error = "path == nullptr"; return false; }
  
  // Pfad und Modus für Reload speichern
  current_path = path;
  current_strict = strict;

  std::string err;
  std::string data = read_file_utf8(path, err);
  if (!err.empty()) { last_error = err; return false; }

  return load_txt_catalog(std::move(data), strict);
}

bool I18nEngine::reload() {
  if (current_path.empty()) { last_error = "No file loaded yet"; return false; }
  // Nutzt den gespeicherten Pfad und Strict-Mode
  return load_txt_file(current_path.c_str(), current_strict);
}

std::string I18nEngine::translate(const std::string& token_in, const std::vector<std::string>& args) {
  std::string token = to_lower_ascii(token_in);
  std::unordered_set<std::string> seen;
  return translate_impl(token, args, seen, 0);
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
