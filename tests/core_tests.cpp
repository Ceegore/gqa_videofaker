#include "core.h"
#include "scene.h"
#include "tiny_font.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
int main() {
    int checks=0;
    auto check=[&](bool ok){++checks;if(!ok)throw std::runtime_error("core assertion "+std::to_string(checks));};
    check(probe::parse({}).mode=="legacy-exclusive");
    check(probe::parse({"--mode","borderless-control","--load","medium"}).load=="medium");
    check(probe::loadIterations("high")==32);
    check(probe::jsonQuote("a\n\"\\\t")=="\"a\\n\\\"\\\\\\t\"");
    const std::vector<std::vector<std::string>> invalid={
        {"--fps-cap","0"},{"--fps-cap","60.0"},{"--monitor","-1"},{"--load","max"},
        {"--mode","exclusive"},{"--duration","15","--warmup","12"},{"--strict"},
        {"--run-id","../../bad"},{"--mode"},{"--fps-cap","60","--fps-cap","30"}
    };
    for(const auto& v:invalid){bool threw=false;try{(void)probe::parse(v);}catch(const std::runtime_error&){threw=true;}check(threw);}
    for(char ch='A';ch<='Z';++ch){for(auto bits:probe::glyph(ch))check(bits<32);}
    probe::SceneInfo s;s.options.runId="0123456789abcdef";
    for(int i=0;i<13;++i){s.seconds=i;s.frame=static_cast<std::uint64_t>(i)*60;
        auto vertices=probe::makeScene(s);check(!vertices.empty());check(vertices.size()<180000);
        check(vertices.size()%3==0);
        for(const auto& v:vertices){check(std::isfinite(v.x)&&std::isfinite(v.y));check(v.a==1);}
    }
    std::cout<<"CORE_PASS "<<checks<<" assertions\n";
    return 0;
}
