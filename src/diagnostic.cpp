#include "diagnostic.h"
#include <iomanip>
#include <sstream>
#include <limits>
namespace probe {
std::string utf8(const std::wstring& s) {
    if (s.empty()) return {};
    if (s.size()>static_cast<std::size_t>(std::numeric_limits<int>::max())) throw std::runtime_error("UTF16 input too long");
    const int len=static_cast<int>(s.size());
    const int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,s.data(),len,nullptr,0,nullptr,nullptr);
    if(n<=0)throw std::runtime_error("Invalid UTF16");
    std::string r(static_cast<std::size_t>(n),'\0');
    if(WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,s.data(),len,r.data(),n,nullptr,nullptr)!=n)
        throw std::runtime_error("UTF16 conversion failed");
    return r;
}
std::wstring wide(const std::string& s) {
    if(s.empty())return {};
    if(s.size()>static_cast<std::size_t>(std::numeric_limits<int>::max()))throw std::runtime_error("UTF8 input too long");
    const int len=static_cast<int>(s.size());
    const int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),len,nullptr,0);
    if(n<=0)throw std::runtime_error("Invalid UTF8");
    std::wstring r(static_cast<std::size_t>(n),L'\0');
    if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),len,r.data(),n)!=n)
        throw std::runtime_error("UTF8 conversion failed");
    return r;
}
std::int64_t qpc(){LARGE_INTEGER n{};if(!QueryPerformanceCounter(&n))throw std::runtime_error("QPC unavailable");return n.QuadPart;}
std::int64_t frequency(){LARGE_INTEGER n{};if(!QueryPerformanceFrequency(&n)||n.QuadPart<=0)throw std::runtime_error("QPC frequency unavailable");return n.QuadPart;}
std::uint64_t processCreation(){
    FILETIME c{},e{},k{},u{};
    if(!GetProcessTimes(GetCurrentProcess(),&c,&e,&k,&u))throw std::runtime_error("GetProcessTimes failed");
    return (static_cast<std::uint64_t>(c.dwHighDateTime)<<32)|c.dwLowDateTime;
}
std::string utcNow(){
    FILETIME ft{};SYSTEMTIME st{};GetSystemTimePreciseAsFileTime(&ft);FileTimeToSystemTime(&ft,&st);
    std::ostringstream s;s<<std::setfill('0')<<std::setw(4)<<st.wYear<<'-'<<std::setw(2)<<st.wMonth<<'-'<<std::setw(2)<<st.wDay
      <<'T'<<std::setw(2)<<st.wHour<<':'<<std::setw(2)<<st.wMinute<<':'<<std::setw(2)<<st.wSecond<<'.'<<std::setw(3)<<st.wMilliseconds<<'Z';
    return s.str();
}
std::string hexValue(std::uint64_t v){std::ostringstream s;s<<"0x"<<std::hex<<std::uppercase<<v;return s.str();}
ApiError::ApiError(const std::string& api,HRESULT hr):std::runtime_error(api+" failed: "+hexValue(static_cast<std::uint32_t>(hr))),result(hr){}
void check(HRESULT hr,const char* api){if(FAILED(hr))throw ApiError(api,hr);}
void writeConsole(const std::string& s){
    HANDLE h=GetStdHandle(STD_OUTPUT_HANDLE);
    if(h==nullptr || h==INVALID_HANDLE_VALUE){AttachConsole(ATTACH_PARENT_PROCESS);h=GetStdHandle(STD_OUTPUT_HANDLE);}
    if(h!=nullptr && h!=INVALID_HANDLE_VALUE){DWORD written=0;(void)WriteFile(h,s.data(),static_cast<DWORD>(s.size()),&written,nullptr);}
}
void Log::open(const std::filesystem::path& dir){
    std::filesystem::create_directories(dir);
    if(std::filesystem::exists(dir/L"app.jsonl")||std::filesystem::exists(dir/L"frames.csv"))
        throw std::runtime_error("Refusing to overwrite prior evidence: choose a new run directory");
    events_.open(dir/L"app.jsonl",std::ios::out|std::ios::binary);
    frames_.open(dir/L"frames.csv",std::ios::out|std::ios::binary);
    frames_<<"FrameIndex,BeforeQPC,AfterQPC,HResult,Fullscreen,Focus\n";
    frames_.flush();
    if(!good())throw std::runtime_error("Cannot create diagnostic logs");
}
void Log::event(const std::string& name,const std::string& extra){
    events_<<"{\"schema\":1,\"seq\":"<<seq_++<<",\"qpc\":"<<qpc()<<",\"utc\":"<<jsonQuote(utcNow())<<",\"event\":"<<jsonQuote(name);
    if(!extra.empty())events_<<','<<extra;
    events_<<"}\n";events_.flush();
    if(!events_)throw std::runtime_error("Event log write failed");
}
void Log::frame(std::uint64_t index,std::int64_t before,std::int64_t after,HRESULT hr,bool fullscreen,bool focus){
    frames_<<index<<','<<before<<','<<after<<','<<hexValue(static_cast<std::uint32_t>(hr))<<','<<fullscreen<<','<<focus<<'\n';
    frames_.flush();
    if(!frames_)throw std::runtime_error("Frame log write failed");
}
bool Log::good()const{return events_.good()&&frames_.good();}
}
