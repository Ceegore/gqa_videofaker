#include "scene.h"
#include "tiny_font.h"
#include <cmath>
#include <iomanip>
#include <sstream>
namespace probe {
namespace {
struct Canvas {
    float width, height;
    std::vector<Vertex> v;
    void rect(float x, float y, float w, float h, float r, float g, float b) {
        const float l=2*x/width-1, t=1-2*y/height, rr=2*(x+w)/width-1, bb=1-2*(y+h)/height;
        const Vertex a{l,t,r,g,b,1}, d{rr,bb,r,g,b,1}, e{l,bb,r,g,b,1}, f{rr,t,r,g,b,1};
        v.insert(v.end(), {a,f,d,a,d,e});
    }
    void text(const std::string& s, float x, float y, float scale, float r=1, float g=1, float b=1) {
        for (char c : s) {
            auto bits=glyph(c);
            for (int row=0; row<7; ++row) for (int col=0; col<5; ++col)
                if (bits[static_cast<std::size_t>(row)] & (1u << (4-col)))
                    rect(x+static_cast<float>(col)*scale,y+static_cast<float>(row)*scale,scale,scale,r,g,b);
            x += 6*scale;
        }
    }
};
}
std::vector<Vertex> makeScene(const SceneInfo& s) {
    Canvas c{static_cast<float>(s.width),static_cast<float>(s.height),{}};
    c.v.reserve(70000);
    const float w=c.width,h=c.height;
    const float k=std::max(1.0f,std::floor(std::min(w/700.0f,h/400.0f)));
    for(float x=0;x<w;x+=80) c.rect(x,0,1,h,.16f,.22f,.25f);
    for(float y=0;y<h;y+=80) c.rect(0,y,w,1,.16f,.22f,.25f);
    const float phase=static_cast<float>(std::fmod(s.seconds,12.0)/3.0);
    float x=0,y=0;
    if(phase<1){x=(w-48)*phase;}else if(phase<2){x=w-48;y=(h-48)*(phase-1);}
    else if(phase<3){x=(w-48)*(3-phase);y=h-48;}else{y=(h-48)*(4-phase);}
    c.rect(x,y,48,48,.95f,.45f,.1f);
    const float left=44,top=44,line=10*k;
    c.rect(left-12,top-12,std::min(w-88,660*k),12*line+20,.025f,.04f,.07f);
    std::vector<std::string> lines{
        "FSEPROBE - FAKE GAME DATA",
        "RUN " + s.options.runId,
        s.options.mode,
        std::string("DXGI FULLSCREEN ")+(s.dxgi?"TRUE":"FALSE"),
        "PRESENTATION NOT YET INDEPENDENTLY VERIFIED",
        "POST-RUN ETW CHECK REQUIRED",
        "FRAME " + std::to_string(s.frame) + "  FPS " + std::to_string(static_cast<int>(s.fps)),
        "SECONDS " + std::to_string(static_cast<int>(s.seconds)) + "  LOAD " + s.options.load,
        "LEVEL 07  HP " + std::to_string(60+(s.frame/30)%40) + "  SCORE " + std::to_string(s.frame*13),
        s.finished?"INTERVAL CLOSED - KEEP RECORDING 1 SECOND":
          s.marked?"MARKED INTERVAL - F9 TO END":
          s.ready?"READY - START RECORDER THEN F8":"WARMUP - DO NOT MARK YET",
        "F8 START / F9 END / ESC EXIT"
    };
    for(std::size_t i=0;i<lines.size();++i)
        c.text(lines[i],left,top+static_cast<float>(i)*line,k,1,i==4?.7f:1,i==4?.1f:1);
    // Human-readable frame ID above and a 24-bit binary code below (LSB on left).
    const float cell=std::max(6.0f,std::min(24.0f,(w-88)/24));
    for(int bit=0;bit<24;++bit){
        bool on=(s.frame & (std::uint64_t{1}<<bit))!=0;
        c.rect(44+static_cast<float>(bit)*cell,h-70,cell-2,24,on?1.0f:.05f,on?1.0f:.05f,on?1.0f:.05f);
    }
    c.text("FRAME BITS LSB LEFT - SYNTHETIC",44,h-96,k);
    // Keep calibration edges visible even when the moving square reaches a corner.
    // 1px border plus asymmetric corners: cropping and mirroring become obvious.
    c.rect(0,0,w,2,1,1,1);c.rect(0,h-2,w,2,1,1,1);
    c.rect(0,0,2,h,1,1,1);c.rect(w-2,0,2,h,1,1,1);
    c.rect(3,3,24,24,1,0,0);c.rect(w-27,3,24,24,0,1,0);
    c.rect(3,h-27,24,24,0,.4f,1);c.rect(w-27,h-27,24,24,1,1,0);
    c.text("TL",32,6,2);c.text("TR",w-60,6,2);c.text("BL",32,h-22,2);c.text("BR",w-60,h-22,2);
    return c.v;
}
}
