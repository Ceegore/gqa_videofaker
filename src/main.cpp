#include "graphics.h"
#include <shellapi.h>
#include <memory>
#include <chrono>
#include <thread>
namespace {
using namespace probe;
struct WindowState {
    bool quit=false, minimized=false, resize=false, lostFocus=false, displayChanged=false, armed=false;
    bool startMark=false,endMark=false;
    int width=0,height=0;
};
LRESULT CALLBACK windowProc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp){
    auto* s=reinterpret_cast<WindowState*>(GetWindowLongPtrW(hwnd,GWLP_USERDATA));
    if(msg==WM_NCCREATE){
        const auto* cs=reinterpret_cast<CREATESTRUCTW*>(lp);s=static_cast<WindowState*>(cs->lpCreateParams);
        SetWindowLongPtrW(hwnd,GWLP_USERDATA,reinterpret_cast<LONG_PTR>(s));
    }
    if(s){
        switch(msg){
        case WM_CLOSE: s->quit=true;return 0;
        case WM_DESTROY: s->quit=true;return 0;
        case WM_ENDSESSION: if(wp)s->quit=true;return 0;
        case WM_SIZE:
            s->minimized=wp==SIZE_MINIMIZED;s->width=LOWORD(lp);s->height=HIWORD(lp);s->resize=true;return 0;
        case WM_DISPLAYCHANGE: case WM_DPICHANGED: if(s->armed)s->displayChanged=true;return 0;
        case WM_ACTIVATEAPP: if(wp==FALSE && s->armed)s->lostFocus=true;return 0;
        case WM_KEYDOWN:
            if(wp==VK_ESCAPE)s->quit=true;
            if((lp & (static_cast<LPARAM>(1)<<30))==0){
                if(wp==VK_F8)s->startMark=true;
                if(wp==VK_F9)s->endMark=true;
            }
            return 0;
        case WM_SYSKEYDOWN: if(wp==VK_RETURN)return 0;break;
        case WM_ERASEBKGND: return 1;
        }
    }
    return DefWindowProcW(hwnd,msg,wp,lp);
}
void pump(WindowState& s){MSG m{};while(PeekMessageW(&m,nullptr,0,0,PM_REMOVE)){
    if(m.message==WM_QUIT)s.quit=true;
    TranslateMessage(&m);DispatchMessageW(&m);
}}
struct Handle {HANDLE h=nullptr;~Handle(){if(h && h!=INVALID_HANDLE_VALUE)CloseHandle(h);}};
struct Window {HWND h=nullptr;~Window(){if(h && IsWindow(h))DestroyWindow(h);}};
std::string boolean(bool b){return b?"true":"false";}
int run(HINSTANCE instance,const Options& options){
    Options o=options;
    if(o.runId.empty())o.runId="RUN-"+std::to_string(GetCurrentProcessId())+"-"+std::to_string(qpc());
    if(o.logDir.empty())o.logDir="logs/"+o.runId;
    Log log;
    try { log.open(std::filesystem::path(wide(o.logDir))); }
    catch(const std::exception& e){writeConsole(std::string("Log initialization failed: ")+e.what()+"\n");return 25;}
    Handle mutex{CreateMutexW(nullptr,FALSE,L"Local\\FSEProbe.OneRun.v1")};
    const DWORD mutexError=GetLastError();
    if(!mutex.h || mutexError==ERROR_ALREADY_EXISTS){
        log.event("START_REFUSED","\"reason\":\"INSTANCE_ALREADY_RUNNING_OR_MUTEX_DENIED\"");return 23;
    }
    Window window;
    std::unique_ptr<Graphics> graphics;
    int code=0;
    bool startWritten=false,closed=false;
    try{
        DWORD session=0;(void)ProcessIdToSessionId(GetCurrentProcessId(),&session);
        log.event("START","\"run_id\":"+jsonQuote(o.runId)+",\"pid\":"+std::to_string(GetCurrentProcessId())+
            ",\"process_creation_filetime\":"+jsonQuote(std::to_string(processCreation()))+
            ",\"qpc_frequency\":"+std::to_string(frequency())+",\"version\":"+jsonQuote(Version)+
            ",\"mode\":"+jsonQuote(o.mode)+",\"load\":"+jsonQuote(o.load)+
            ",\"duration\":"+std::to_string(o.seconds)+",\"warmup\":"+std::to_string(o.warmup)+
            ",\"fps_cap\":"+std::to_string(o.fps)+",\"auto_mark\":"+boolean(o.autoMark)+
            ",\"remote_session\":"+boolean(GetSystemMetrics(SM_REMOTESESSION)!=0)+",\"session_id\":"+std::to_string(session));
        startWritten=true;
        if(GetSystemMetrics(SM_REMOTESESSION)!=0 || session==0){
            log.event("ENVIRONMENT_REFUSED","\"reason\":\"REMOTE_OR_NONINTERACTIVE_SESSION\"");code=24;
        }else{
            const auto monitors=displays();
            if(static_cast<std::size_t>(o.monitor)>=monitors.size())throw std::runtime_error("Requested DXGI monitor index is not attached");
            const auto& display=monitors[static_cast<std::size_t>(o.monitor)];
            log.event("DISPLAY_SELECTED",displayFields(display)+",\"index\":"+std::to_string(o.monitor));
            const auto& rect=display.outputDesc.DesktopCoordinates;
            WindowState state;
            WNDCLASSW wc{};wc.lpfnWndProc=windowProc;wc.hInstance=instance;wc.lpszClassName=L"FSEProbeWindow";
            wc.hCursor=LoadCursorW(nullptr,IDC_ARROW);
            if(!RegisterClassW(&wc) && GetLastError()!=ERROR_CLASS_ALREADY_EXISTS)throw std::runtime_error("RegisterClass failed");
            window.h=CreateWindowExW(0,wc.lpszClassName,L"FSEProbe - Click to focus - ESC exits",WS_POPUP,
                rect.left,rect.top,rect.right-rect.left,rect.bottom-rect.top,nullptr,nullptr,instance,&state);
            if(!window.h)throw std::runtime_error("CreateWindowEx failed");
            ShowWindow(window.h,SW_SHOW);UpdateWindow(window.h);
            graphics=std::make_unique<Graphics>();graphics->initialize(window.h,display,o.mode=="legacy-exclusive");
            // Give the operator one bounded chance to activate the window; never steal focus repeatedly.
            const auto focusDeadline=qpc()+10*frequency();
            while(GetForegroundWindow()!=window.h && !state.quit && qpc()<focusDeadline){
                pump(state);
                SceneInfo wait;wait.options=o;wait.width=graphics->width();wait.height=graphics->height();
                graphics->render(wait);(void)graphics->present();
                std::this_thread::sleep_for(std::chrono::milliseconds(20));
            }
            if(GetForegroundWindow()!=window.h || state.quit)throw std::runtime_error("NO_FOCUS: window not activated within 10 seconds");
            if(o.mode=="legacy-exclusive"){
                log.event("REQUEST_FULLSCREEN");
                const HRESULT transition=graphics->enterExclusive();
                log.event("SET_FULLSCREEN_RESULT","\"hresult\":"+jsonQuote(hexValue(static_cast<std::uint32_t>(transition))));
                // Positive status such as MODE_CHANGE_IN_PROGRESS is not success for this test.
                if(transition!=S_OK)throw ApiError("SetFullscreenState (requires S_OK)",transition);
                RECT c{};if(!GetClientRect(window.h,&c))throw std::runtime_error("Client rect unavailable");
                graphics->resize(c.right,c.bottom);
            }
            pump(state);state.resize=false;state.lostFocus=false;state.displayChanged=false;
            bool fullscreen=graphics->fullscreen();
            const bool expected=o.mode=="legacy-exclusive";
            if(fullscreen!=expected)throw std::runtime_error("DXGI state differs from requested mode");
            if(!graphics->correctOutput())throw std::runtime_error("Wrong output after transition");
            state.armed=true;
            log.event("MODE_READY","\"fullscreen\":"+boolean(fullscreen)+",\"focus\":true,\"correct_output\":true,\"swapchain_pointer_diagnostic\":"+jsonQuote(graphics->chainAddress()));
            const auto begin=qpc(),freq=frequency();
            auto nextFrame=begin,lastState=begin,lastFPS=begin;
            std::uint64_t frame=0,fpsFrames=0;
            double fps=0;
            bool marked=false;
            const auto intervalKind=o.autoMark?"AUTOMATIC_DIAGNOSTIC":"OPERATOR_MARKED";
            while(!state.quit){
                pump(state);
                const auto now=qpc();const double seconds=static_cast<double>(now-begin)/static_cast<double>(freq);
                if(state.quit)break;
                if(state.lostFocus || GetForegroundWindow()!=window.h || state.minimized){
                    log.event("LOST_FOCUS");code=21;break;
                }
                if(state.displayChanged){log.event("DISPLAY_CHANGED");code=21;break;}
                if(state.resize){
                    state.resize=false;
                    graphics->resize(state.width,state.height);
                    log.event("RESIZED","\"width\":"+std::to_string(state.width)+",\"height\":"+std::to_string(state.height));
                    if(marked&&!closed){log.event("CAPTURE_INVALIDATED","\"reason\":\"RESIZE\"");code=21;break;}
                }
                fullscreen=graphics->fullscreen();
                if(fullscreen!=expected){log.event("DXGI_LOST","\"fullscreen\":"+boolean(fullscreen));code=21;break;}
                if(now-lastState>=freq/4){
                    const bool correct=graphics->correctOutput();
                    log.event("STATE","\"fullscreen\":"+boolean(fullscreen)+",\"focus\":true,\"correct_output\":"+boolean(correct));
                    lastState=now;if(!correct){code=21;break;}
                }
                if((o.autoMark&&seconds>=o.warmup&&!marked)||state.startMark){
                    state.startMark=false;
                    if(!marked && seconds>=o.warmup && seconds<o.seconds-5){
                        marked=true;log.event("CAPTURE_MARK_START","\"kind\":"+jsonQuote(intervalKind));
                    }else log.event("MARK_REJECTED","\"reason\":\"TOO_EARLY_LATE_OR_DUPLICATE\"");
                }
                if((o.autoMark&&seconds>=o.seconds-3&&!closed)||state.endMark){
                    state.endMark=false;
                    if(marked&&!closed){closed=true;log.event("CAPTURE_MARK_END","\"kind\":"+jsonQuote(intervalKind));}
                    else log.event("MARK_REJECTED","\"reason\":\"NO_ACTIVE_INTERVAL\"");
                }
                if(seconds>=o.seconds)break;
                if(now<nextFrame){
                    const auto ms=static_cast<int>((nextFrame-now)*1000/freq);
                    const DWORD wait=static_cast<DWORD>(std::clamp(ms,1,10));
                    (void)MsgWaitForMultipleObjectsEx(0,nullptr,wait,QS_ALLINPUT,MWMO_INPUTAVAILABLE);continue;
                }
                SceneInfo scene;scene.options=o;scene.width=graphics->width();scene.height=graphics->height();
                scene.frame=frame;scene.seconds=seconds;scene.fps=fps;scene.dxgi=fullscreen;scene.marked=marked;scene.finished=closed;scene.ready=seconds>=o.warmup;
                graphics->render(scene);
                const auto before=qpc();const HRESULT hr=graphics->present();const auto after=qpc();
                log.frame(frame,before,after,hr,fullscreen,GetForegroundWindow()==window.h);
                if(hr!=S_OK){
                    log.event("PRESENT_ERROR","\"hresult\":"+jsonQuote(hexValue(static_cast<std::uint32_t>(hr)))+
                        ",\"device_removed_reason\":"+jsonQuote(hexValue(static_cast<std::uint32_t>(graphics->removedReason()))));
                    code=22;break;
                }
                ++frame;++fpsFrames;
                if(after-lastFPS>=freq){fps=static_cast<double>(fpsFrames)*static_cast<double>(freq)/static_cast<double>(after-lastFPS);fpsFrames=0;lastFPS=after;}
                // No catch-up burst. VSync may reduce frame rate below the cap.
                nextFrame=std::max(nextFrame+freq/o.fps,after);
            }
            state.armed=false;
            if(marked&&!closed)log.event("CAPTURE_INCOMPLETE");
            if(!marked)log.event("NO_CAPTURE_MARKS");
            const HRESULT cleanup=graphics->leaveExclusive();
            log.event("LEAVE_FULLSCREEN_RESULT","\"hresult\":"+jsonQuote(hexValue(static_cast<std::uint32_t>(cleanup))));
            if(cleanup!=S_OK && code==0)code=22;
            graphics.reset();
            // WindowState is stack-owned, so destroy the window before it leaves scope.
            DestroyWindow(window.h);window.h=nullptr;
        }
    }catch(const std::exception& e){
        code=20;
        if(window.h)SetWindowLongPtrW(window.h,GWLP_USERDATA,0);
        try{log.event("APP_ERROR","\"message\":"+jsonQuote(e.what())+
            (graphics?",\"device_removed_reason\":"+jsonQuote(hexValue(static_cast<std::uint32_t>(graphics->removedReason()))):""));}catch(...){ }
        if(graphics){
            const HRESULT h=graphics->leaveExclusive();
            try{log.event("LEAVE_FULLSCREEN_RESULT","\"hresult\":"+jsonQuote(hexValue(static_cast<std::uint32_t>(h))));}catch(...){ }
            graphics.reset();
        }
        // Detach stack-owned state before any destruction after exception unwinding.
        if(window.h){SetWindowLongPtrW(window.h,GWLP_USERDATA,0);DestroyWindow(window.h);window.h=nullptr;}
        writeConsole(std::string("FSEProbe failed: ")+e.what()+"\n");
    }
    if(startWritten){try{log.event("END","\"exit_code\":"+std::to_string(code)+",\"live_verification\":\"NOT_LIVE_VERIFIED\"");}catch(...){code=25;}}
    return code;
}
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,PWSTR commandLine,int show){
    UNREFERENCED_PARAMETER(previous);UNREFERENCED_PARAMETER(commandLine);UNREFERENCED_PARAMETER(show);
    try{
        int count=0;LPWSTR* raw=CommandLineToArgvW(GetCommandLineW(),&count);
        if(!raw)throw std::runtime_error("Cannot parse command line");
        std::vector<std::string> args;
        try{for(int i=1;i<count;++i)args.push_back(probe::utf8(raw[i]));}catch(...){LocalFree(raw);throw;}
        LocalFree(raw);
        const auto o=probe::parse(args);
        if(o.help){probe::writeConsole(probe::Help);return 0;}
        if(o.version){probe::writeConsole(std::string(probe::Version)+"\n");return 0;}
        if(o.selfTest){
            if(probe::parse({}).fps!=60 || probe::jsonQuote("x")!="\"x\"" || probe::frequency()<=0)return 1;
            probe::writeConsole("SELF_TEST_PASS - no GPU, FSE or SAC certification\n");return 0;
        }
        if(o.list){
            const auto list=probe::displays();
            for(std::size_t i=0;i<list.size();++i)probe::writeConsole("{\"index\":"+std::to_string(i)+","+probe::displayFields(list[i])+"}\n");
            return list.empty()?24:0;
        }
        return run(instance,o);
    }catch(const std::exception& e){probe::writeConsole(std::string("FSEProbe: ")+e.what()+"\n");return 2;}
}
