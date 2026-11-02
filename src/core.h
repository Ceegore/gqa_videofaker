#pragma once
#include <algorithm>
#include <charconv>
#include <cstdint>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace probe {
inline constexpr char Version[] = "0.1.0";
struct Options {
    std::string mode = "legacy-exclusive", load = "low", runId, logDir;
    int monitor = 0, seconds = 60, warmup = 8, fps = 60;
    bool autoMark = false, help = false, version = false, selfTest = false, list = false;
};
inline std::string jsonQuote(std::string_view s) {
    std::string r = "\"";
    constexpr char hex[] = "0123456789abcdef";
    for (const unsigned char c : s) {
        switch (c) {
        case '\"': r += "\\\""; break;
        case '\\': r += "\\\\"; break;
        case '\n': r += "\\n"; break;
        case '\r': r += "\\r"; break;
        case '\t': r += "\\t"; break;
        default:
            if (c < 32) { r += "\\u00"; r += hex[c >> 4]; r += hex[c & 15]; }
            else r += static_cast<char>(c);
        }
    }
    return r + "\"";
}
inline int number(std::string_view s, int low, int high) {
    int v = 0;
    auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), v);
    if (ec != std::errc{} || p != s.data() + s.size() || v < low || v > high)
        throw std::runtime_error("Invalid integer/range: " + std::string(s));
    return v;
}
inline Options parse(const std::vector<std::string>& args) {
    Options o;
    std::set<std::string> seen;
    for (std::size_t i = 0; i < args.size(); ++i) {
        const auto& a = args[i];
        if (!seen.insert(a).second) throw std::runtime_error("Duplicate option: " + a);
        if (a == "--help") { o.help = true; continue; }
        if (a == "--version") { o.version = true; continue; }
        if (a == "--self-test") { o.selfTest = true; continue; }
        if (a == "--list-monitors") { o.list = true; continue; }
        if (a == "--auto-mark") { o.autoMark = true; continue; }
        if (a != "--mode" && a != "--load" && a != "--run-id" && a != "--log-dir" &&
            a != "--monitor" && a != "--duration" && a != "--warmup" && a != "--fps-cap")
            throw std::runtime_error("Unknown option: " + a);
        if (++i == args.size()) throw std::runtime_error("Missing value: " + a);
        const auto& v = args[i];
        if (a == "--mode") o.mode = v;
        else if (a == "--load") o.load = v;
        else if (a == "--run-id") o.runId = v;
        else if (a == "--log-dir") o.logDir = v;
        else if (a == "--monitor") o.monitor = number(v, 0, 31);
        else if (a == "--duration") o.seconds = number(v, 15, 300);
        else if (a == "--warmup") o.warmup = number(v, 3, 60);
        else if (a == "--fps-cap") o.fps = number(v, 15, 120);
    }
    if (o.mode != "legacy-exclusive" && o.mode != "borderless-control")
        throw std::runtime_error("Mode must be legacy-exclusive or borderless-control");
    if (o.load != "off" && o.load != "low" && o.load != "medium" && o.load != "high")
        throw std::runtime_error("Load must be off, low, medium or high");
    if (o.seconds < o.warmup + 8) throw std::runtime_error("Duration must exceed warmup by at least 8 seconds");
    if (!o.runId.empty()) {
        if (o.runId.size() > 48 || o.runId.size() < 4) throw std::runtime_error("Run ID length: 4..48");
        for (const unsigned char c : o.runId)
            if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
                  (c >= '0' && c <= '9') || c == '-' || c == '_'))
                throw std::runtime_error("Run ID must contain only ASCII letters, numbers, _ or -");
    }
    return o;
}
inline int loadIterations(const std::string& s) {
    if (s == "off") return 0;
    if (s == "low") return 4;
    if (s == "medium") return 12;
    if (s == "high") return 32;
    throw std::runtime_error("Unknown load");
}
inline constexpr char Help[] =
    "FSEProbe 0.1.0 - DXGI diagnostic; NO live ETW verification\n"
    "--mode legacy-exclusive|borderless-control  (default legacy-exclusive)\n"
    "--load off|low|medium|high                  (default low)\n"
    "--monitor 0..31 --list-monitors             (DXGI enumeration, not Settings numbering)\n"
    "--duration 15..300 --warmup 3..60           (seconds; defaults 60/8)\n"
    "--fps-cap 15..120                          (default 60; VSync always ON)\n"
    "--run-id ID --log-dir PATH --auto-mark\n"
    "--help --version --self-test\n"
    "F8: operator interval start; F9: operator interval end; ESC: exit\n"
    "Manual markers are NOT recorder API timestamps. Auto marks are diagnostic only.\n"
    "App exit 0 means clean execution, NEVER FSE_VERIFIED. Use offline classifier.\n";
}
