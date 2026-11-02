#include "graphics.h"
#include <cstring>
#include "BackgroundVS.h"
#include "BackgroundPS.h"
#include "HudVS.h"
#include "HudPS.h"
namespace probe {
std::vector<Display> displays(){
    ComPtr<IDXGIFactory1> factory;check(CreateDXGIFactory1(IID_PPV_ARGS(factory.GetAddressOf())),"CreateDXGIFactory1");
    std::vector<Display> result;
    for(UINT a=0;;++a){
        ComPtr<IDXGIAdapter1> adapter;HRESULT hr=factory->EnumAdapters1(a,adapter.GetAddressOf());
        if(hr==DXGI_ERROR_NOT_FOUND)break;check(hr,"EnumAdapters1");
        DXGI_ADAPTER_DESC1 ad{};check(adapter->GetDesc1(&ad),"GetDesc1");
        if((ad.Flags&DXGI_ADAPTER_FLAG_SOFTWARE)!=0)continue;
        for(UINT n=0;;++n){
            ComPtr<IDXGIOutput> output;hr=adapter->EnumOutputs(n,output.GetAddressOf());
            if(hr==DXGI_ERROR_NOT_FOUND)break;check(hr,"EnumOutputs");
            DXGI_OUTPUT_DESC od{};check(output->GetDesc(&od),"Output::GetDesc");
            if(od.AttachedToDesktop && od.DesktopCoordinates.right>od.DesktopCoordinates.left && od.DesktopCoordinates.bottom>od.DesktopCoordinates.top)
                result.push_back({adapter,output,ad,od});
        }
    }
    return result;
}
std::string displayFields(const Display& d){
    const auto& r=d.outputDesc.DesktopCoordinates;
    const std::uint64_t luid=(static_cast<std::uint64_t>(static_cast<std::uint32_t>(d.adapterDesc.AdapterLuid.HighPart))<<32)|d.adapterDesc.AdapterLuid.LowPart;
    return "\"gpu\":"+jsonQuote(utf8(d.adapterDesc.Description))+",\"adapter_luid\":"+jsonQuote(hexValue(luid))+
      ",\"output\":"+jsonQuote(utf8(d.outputDesc.DeviceName))+",\"monitor_handle\":"+jsonQuote(hexValue(reinterpret_cast<std::uintptr_t>(d.outputDesc.Monitor)))+
      ",\"desktop_rect\":["+std::to_string(r.left)+","+std::to_string(r.top)+","+std::to_string(r.right)+","+std::to_string(r.bottom)+"]";
}
Graphics::~Graphics(){
    (void)leaveExclusive();
    if(context_){context_->ClearState();context_->Flush();}
}
void Graphics::initialize(HWND hwnd,const Display& output,bool legacy){
    hwnd_=hwnd;display_=output;legacy_=legacy;
    const D3D_FEATURE_LEVEL levels[]={D3D_FEATURE_LEVEL_11_0};D3D_FEATURE_LEVEL obtained{};
    check(D3D11CreateDevice(display_.adapter.Get(),D3D_DRIVER_TYPE_UNKNOWN,nullptr,0,levels,1,D3D11_SDK_VERSION,
        device_.GetAddressOf(),&obtained,context_.GetAddressOf()),"D3D11CreateDevice");
    if(obtained<D3D_FEATURE_LEVEL_11_0)throw std::runtime_error("Feature level 11.0 required");
    check(display_.adapter->GetParent(IID_PPV_ARGS(factory_.GetAddressOf())),"Adapter::GetParent");
    RECT client{};if(!GetClientRect(hwnd,&client))throw std::runtime_error("GetClientRect failed");
    DXGI_SWAP_CHAIN_DESC desc{};
    desc.BufferDesc.Width=static_cast<UINT>(client.right);desc.BufferDesc.Height=static_cast<UINT>(client.bottom);
    desc.BufferDesc.RefreshRate={0,1};desc.BufferDesc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
    desc.SampleDesc.Count=1;desc.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;
    desc.BufferCount=legacy?1u:2u;desc.OutputWindow=hwnd;desc.Windowed=TRUE;
    desc.SwapEffect=legacy?DXGI_SWAP_EFFECT_DISCARD:DXGI_SWAP_EFFECT_FLIP_DISCARD;
    desc.Flags=0; // No ALLOW_MODE_SWITCH: retain desktop resolution/refresh as default.
    check(factory_->CreateSwapChain(device_.Get(),&desc,chain_.GetAddressOf()),"CreateSwapChain");
    check(factory_->MakeWindowAssociation(hwnd,DXGI_MWA_NO_ALT_ENTER),"MakeWindowAssociation");
    check(device_->CreateVertexShader(g_BackgroundVS,sizeof(g_BackgroundVS),nullptr,bgVS_.GetAddressOf()),"BackgroundVS");
    check(device_->CreatePixelShader(g_BackgroundPS,sizeof(g_BackgroundPS),nullptr,bgPS_.GetAddressOf()),"BackgroundPS");
    check(device_->CreateVertexShader(g_HudVS,sizeof(g_HudVS),nullptr,hudVS_.GetAddressOf()),"HudVS");
    check(device_->CreatePixelShader(g_HudPS,sizeof(g_HudPS),nullptr,hudPS_.GetAddressOf()),"HudPS");
    const D3D11_INPUT_ELEMENT_DESC elements[]={
      {"POSITION",0,DXGI_FORMAT_R32G32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0},
      {"COLOR",0,DXGI_FORMAT_R32G32B32A32_FLOAT,0,8,D3D11_INPUT_PER_VERTEX_DATA,0}};
    check(device_->CreateInputLayout(elements,2,g_HudVS,sizeof(g_HudVS),input_.GetAddressOf()),"CreateInputLayout");
    D3D11_BUFFER_DESC bd{};bd.ByteWidth=16;bd.Usage=D3D11_USAGE_DYNAMIC;bd.BindFlags=D3D11_BIND_CONSTANT_BUFFER;bd.CPUAccessFlags=D3D11_CPU_ACCESS_WRITE;
    check(device_->CreateBuffer(&bd,nullptr,constants_.GetAddressOf()),"Create constants");
    bd.ByteWidth=180000u*static_cast<UINT>(sizeof(Vertex));bd.BindFlags=D3D11_BIND_VERTEX_BUFFER;
    check(device_->CreateBuffer(&bd,nullptr,vertices_.GetAddressOf()),"Create vertices");
    D3D11_RASTERIZER_DESC rd{};rd.FillMode=D3D11_FILL_SOLID;rd.CullMode=D3D11_CULL_NONE;rd.DepthClipEnable=TRUE;
    check(device_->CreateRasterizerState(&rd,raster_.GetAddressOf()),"CreateRasterizerState");
    target();
}
void Graphics::target(){
    ComPtr<ID3D11Texture2D> texture;
    check(chain_->GetBuffer(0,IID_PPV_ARGS(texture.GetAddressOf())),"GetBuffer");
    D3D11_TEXTURE2D_DESC d{};texture->GetDesc(&d);width_=static_cast<int>(d.Width);height_=static_cast<int>(d.Height);
    check(device_->CreateRenderTargetView(texture.Get(),nullptr,target_.ReleaseAndGetAddressOf()),"CreateRenderTargetView");
}
HRESULT Graphics::enterExclusive(){return chain_->SetFullscreenState(TRUE,display_.output.Get());}
HRESULT Graphics::leaveExclusive() noexcept{return chain_&&legacy_?chain_->SetFullscreenState(FALSE,nullptr):S_OK;}
void Graphics::resize(int width,int height){
    if(width<=0||height<=0)return;
    context_->OMSetRenderTargets(0,nullptr,nullptr);
    context_->ClearState();target_.Reset();context_->Flush();
    check(chain_->ResizeBuffers(0,static_cast<UINT>(width),static_cast<UINT>(height),DXGI_FORMAT_UNKNOWN,0),"ResizeBuffers");
    target();
}
bool Graphics::fullscreen(){BOOL fs=FALSE;check(chain_->GetFullscreenState(&fs,nullptr),"GetFullscreenState");return fs!=FALSE;}
bool Graphics::correctOutput(){
    ComPtr<IDXGIOutput> current;check(chain_->GetContainingOutput(current.GetAddressOf()),"GetContainingOutput");
    DXGI_OUTPUT_DESC d{};check(current->GetDesc(&d),"Containing output GetDesc");
    return d.Monitor==display_.outputDesc.Monitor;
}
HRESULT Graphics::removedReason()const{return device_?device_->GetDeviceRemovedReason():E_FAIL;}
std::string Graphics::chainAddress()const{return hexValue(reinterpret_cast<std::uintptr_t>(chain_.Get()));}
void Graphics::render(const SceneInfo& s){
    struct Constants{float w,h,time;std::uint32_t loops;};
    static_assert(sizeof(Constants)==16);
    const Constants data{static_cast<float>(width_),static_cast<float>(height_),static_cast<float>(s.seconds),static_cast<std::uint32_t>(loadIterations(s.options.load))};
    D3D11_MAPPED_SUBRESOURCE mapped{};
    check(context_->Map(constants_.Get(),0,D3D11_MAP_WRITE_DISCARD,0,&mapped),"Map constants");
    std::memcpy(mapped.pData,&data,sizeof(data));context_->Unmap(constants_.Get(),0);
    ID3D11RenderTargetView* rtv=target_.Get();context_->OMSetRenderTargets(1,&rtv,nullptr);
    D3D11_VIEWPORT vp{0,0,static_cast<float>(width_),static_cast<float>(height_),0,1};context_->RSSetViewports(1,&vp);
    context_->RSSetState(raster_.Get());context_->OMSetDepthStencilState(nullptr,0);context_->OMSetBlendState(nullptr,nullptr,0xFFFFFFFF);
    context_->IASetInputLayout(nullptr);context_->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    context_->VSSetShader(bgVS_.Get(),nullptr,0);context_->PSSetShader(bgPS_.Get(),nullptr,0);
    ID3D11Buffer* cb=constants_.Get();context_->PSSetConstantBuffers(0,1,&cb);context_->Draw(3,0);
    const auto verts=makeScene(s);
    if(verts.size()>180000)throw std::runtime_error("HUD vertex capacity exceeded");
    if(!verts.empty()){
        check(context_->Map(vertices_.Get(),0,D3D11_MAP_WRITE_DISCARD,0,&mapped),"Map vertices");
        std::memcpy(mapped.pData,verts.data(),verts.size()*sizeof(Vertex));context_->Unmap(vertices_.Get(),0);
        const UINT stride=static_cast<UINT>(sizeof(Vertex)),offset=0;ID3D11Buffer* vb=vertices_.Get();
        context_->IASetVertexBuffers(0,1,&vb,&stride,&offset);context_->IASetInputLayout(input_.Get());
        context_->VSSetShader(hudVS_.Get(),nullptr,0);context_->PSSetShader(hudPS_.Get(),nullptr,0);
        context_->Draw(static_cast<UINT>(verts.size()),0);
    }
}
HRESULT Graphics::present(){return chain_->Present(1,0);}
}
