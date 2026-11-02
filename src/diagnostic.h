#pragma once
#include "core.h"
#include <windows.h>
#include <filesystem>
#include <fstream>
#include <string>
namespace probe {
std::string utf8(const std::wstring& s);
std::wstring wide(const std::string& s);
std::int64_t qpc();
std::int64_t frequency();
std::uint64_t processCreation();
std::string utcNow();
std::string hexValue(std::uint64_t value);
void writeConsole(const std::string& s);
struct ApiError : std::runtime_error {
    HRESULT result;
    ApiError(const std::string& api, HRESULT hr);
};
void check(HRESULT hr, const char* api);
class Log {
    std::ofstream events_, frames_;
    std::uint64_t seq_=0;
public:
    void open(const std::filesystem::path& dir);
    void event(const std::string& name, const std::string& extra="");
    void frame(std::uint64_t index, std::int64_t before, std::int64_t after, HRESULT hr, bool fullscreen, bool focus);
    bool good() const;
};
}
