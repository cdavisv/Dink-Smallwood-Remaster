#pragma once
#include <array>
#include <cmath>
#include <optional>
#include <utility>
namespace DinkHardness
{
struct ShellPoint { float X,Y,Z; };
using ShellTriangle = std::array<ShellPoint,3>;
using PrismShell = std::array<ShellTriangle,10>;
inline ShellPoint Subtract(ShellPoint A,ShellPoint B) { return {A.X-B.X,A.Y-B.Y,A.Z-B.Z}; }
inline ShellPoint Cross(ShellPoint A,ShellPoint B) { return {A.Y*B.Z-A.Z*B.Y,A.Z*B.X-A.X*B.Z,A.X*B.Y-A.Y*B.X}; }
inline float Dot(ShellPoint A,ShellPoint B) { return A.X*B.X+A.Y*B.Y+A.Z*B.Z; }
// Exact original top+four-sides, NO bottom. Triangles include StaticMesh's
// bFlipNormals=true cooking swap (StaticMesh.cpp9343; ChaosCooking.cpp41).
inline std::optional<PrismShell> OpenPrismShell(const std::array<ShellPoint,8>& V)
{
    for(const auto& P:V) if(!std::isfinite(P.X)||!std::isfinite(P.Y)||!std::isfinite(P.Z)) return std::nullopt;
    PrismShell Result{}; unsigned N=0;
    auto Quad=[&](std::array<ShellPoint,4> P,ShellPoint Out) {
        if(Dot(Cross(Subtract(P[1],P[0]),Subtract(P[3],P[0])),Out)<0) std::swap(P[1],P[3]);
        Result[N++]={P[2],P[0],P[1]}; Result[N++]={P[3],P[0],P[2]};
    };
    Quad({V[4],V[5],V[6],V[7]},{0,0,1});
    ShellPoint Centre{0,0,0};
    for(unsigned I=0;I<4;++I) { Centre.X+=V[I].X*.25f; Centre.Y+=V[I].Y*.25f; }
    for(unsigned I=0;I<4;++I)
    {
        const unsigned J=(I+1)%4;
        ShellPoint Out{(V[I].X+V[J].X)*.5f-Centre.X,(V[I].Y+V[J].Y)*.5f-Centre.Y,0};
        Quad({V[I],V[J],V[J+4],V[I+4]},Out);
    }
    for(const auto& T:Result)
        if(Dot(Cross(Subtract(T[1],T[0]),Subtract(T[2],T[0])),Cross(Subtract(T[1],T[0]),Subtract(T[2],T[0])))==0)
            return std::nullopt;
    return Result;
}
}
