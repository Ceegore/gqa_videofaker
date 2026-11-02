#pragma once
#include "core.h"
#include <vector>
namespace probe {
struct Vertex { float x, y, r, g, b, a; };
struct SceneInfo {
    int width=1280, height=720;
    std::uint64_t frame=0;
    double seconds=0, fps=0;
    bool dxgi=false, marked=false, finished=false, ready=false;
    Options options;
};
std::vector<Vertex> makeScene(const SceneInfo& s);
}
