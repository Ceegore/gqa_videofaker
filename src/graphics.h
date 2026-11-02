#pragma once
#include "diagnostic.h"
#include "scene.h"
#include <d3d11.h>
#include <dxgi1_2.h>
#include <wrl/client.h>
namespace probe {
using Microsoft::WRL::ComPtr;
struct Display {
    ComPtr<IDXGIAdapter1> adapter;
    ComPtr<IDXGIOutput> output;
    DXGI_ADAPTER_DESC1 adapterDesc{};
    DXGI_OUTPUT_DESC outputDesc{};
};
std::vector<Display> displays();
std::string displayFields(const Display& display);
class Graphics {
    ComPtr<IDXGIFactory1> factory_;
    ComPtr<ID3D11Device> device_;
    ComPtr<ID3D11DeviceContext> context_;
    ComPtr<IDXGISwapChain> chain_;
    ComPtr<ID3D11RenderTargetView> target_;
    ComPtr<ID3D11VertexShader> bgVS_,hudVS_;
    ComPtr<ID3D11PixelShader> bgPS_,hudPS_;
    ComPtr<ID3D11InputLayout> input_;
    ComPtr<ID3D11Buffer> constants_,vertices_;
    ComPtr<ID3D11RasterizerState> raster_;
    Display display_;
    HWND hwnd_=nullptr;
    int width_=0,height_=0;
    bool legacy_=false;
    void target();
public:
    ~Graphics();
    void initialize(HWND hwnd,const Display& output,bool legacy);
    HRESULT enterExclusive();
    HRESULT leaveExclusive() noexcept;
    void resize(int width,int height);
    bool fullscreen();
    bool correctOutput();
    HRESULT removedReason()const;
    std::string chainAddress()const;
    void render(const SceneInfo& s);
    HRESULT present();
    int width()const{return width_;}
    int height()const{return height_;}
};
}
