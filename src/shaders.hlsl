// Original synthetic renderer. No texture assets, fonts, or runtime shader compiler.
cbuffer FrameParameters : register(b0) {
    float2 resolution;
    float seconds;
    uint iterations;
};
struct BackgroundVertex { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; };
BackgroundVertex BackgroundVS(uint id : SV_VertexID) {
    BackgroundVertex o;
    float2 p = float2((id << 1) & 2, id & 2);
    o.uv = p;
    o.pos = float4(p * float2(2,-2) + float2(-1,1), 0, 1);
    return o;
}
float4 BackgroundPS(BackgroundVertex v) : SV_TARGET {
    float2 p = v.uv * 2 - 1;
    float f = .15 + .05 * sin(seconds + p.x * 4);
    // Fixed upper bound. Output depends on work, preventing dead-code removal.
    [loop] for (uint i=0; i<32; ++i) {
        if (i >= iterations) break;
        p = float2(sin(p.y*2.13 + f + seconds*.05), cos(p.x*1.97-f));
        f = frac(f + dot(p,p)*.013 + .009);
    }
    float pulse = floor(fmod(seconds, 6.0)) / 6.0;
    return float4(.025 + f*.18, .04+f*.14, .08+pulse*.10+f*.10, 1);
}
struct HudInput { float2 pos : POSITION; float4 color : COLOR0; };
struct HudVertex { float4 pos : SV_POSITION; float4 color : COLOR0; };
HudVertex HudVS(HudInput v) {
    HudVertex o; o.pos=float4(v.pos,0,1); o.color=v.color; return o;
}
float4 HudPS(HudVertex v) : SV_TARGET { return v.color; }
