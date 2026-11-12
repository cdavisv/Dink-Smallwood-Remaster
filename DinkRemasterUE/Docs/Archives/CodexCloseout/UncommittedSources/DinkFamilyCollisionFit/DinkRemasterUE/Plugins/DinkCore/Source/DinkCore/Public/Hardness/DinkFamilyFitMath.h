#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <optional>
#include <vector>

namespace DinkFamilyFit
{
struct Point { double X,Y; };
struct Cell { int X,Y; };
struct Map { Point NW,NE,SW,SE; }; // centimetres; map pixels are0..600 by0..400
inline bool Finite(Point P) { return std::isfinite(P.X)&&std::isfinite(P.Y); }
inline double Cross(Point A,Point B,Point C)
{ return (B.X-A.X)*(C.Y-A.Y)-(B.Y-A.Y)*(C.X-A.X); }
inline std::optional<std::vector<Point>> ConvexHull(std::vector<Point> Points)
{
    if(std::any_of(Points.begin(),Points.end(),[](Point P){return !Finite(P);}))return std::nullopt;
    std::sort(Points.begin(),Points.end(),[](Point A,Point B){return A.X!=B.X?A.X<B.X:A.Y<B.Y;});
    Points.erase(std::unique(Points.begin(),Points.end(),[](Point A,Point B){return A.X==B.X&&A.Y==B.Y;}),Points.end());
    if(Points.size()<3)return std::nullopt;
    std::vector<Point> Hull;
    for(Point P:Points){while(Hull.size()>1&&Cross(Hull[Hull.size()-2],Hull.back(),P)<=0)Hull.pop_back();Hull.push_back(P);}
    const auto Lower=Hull.size();
    for(auto I=Points.rbegin()+1;I!=Points.rend();++I){while(Hull.size()>Lower&&Cross(Hull[Hull.size()-2],Hull.back(),*I)<=0)Hull.pop_back();Hull.push_back(*I);}
    Hull.pop_back();
    if(Hull.size()<3)return std::nullopt;
    for(unsigned I=0;I<Hull.size();++I){const double C=Cross(Hull[I],Hull[(I+1)%Hull.size()],Hull[(I+2)%Hull.size()]);if(!std::isfinite(C)||C<=0)return std::nullopt;}
    return Hull; // strictly convex, counter-clockwise, lexicographically first start
}
inline Point ToWorld(const Map& M,double X,double Y)
{
    const double U=X/600.,V=Y/400.;
    return {(1-U)*(1-V)*M.NW.X+U*(1-V)*M.NE.X+(1-U)*V*M.SW.X+U*V*M.SE.X,
            (1-U)*(1-V)*M.NW.Y+U*(1-V)*M.NE.Y+(1-U)*V*M.SW.Y+U*V*M.SE.Y};
}
inline bool ValidMap(const Map& M)
{
    if(!Finite(M.NW)||!Finite(M.NE)||!Finite(M.SW)||!Finite(M.SE))return false;
    const std::array<Point,4> P{M.NW,M.NE,M.SE,M.SW};
    double Sign=0;
    for(unsigned I=0;I<4;++I){const double C=Cross(P[I],P[(I+1)%4],P[(I+2)%4]);if(!std::isfinite(C)||std::abs(C)<1.e-6)return false;if(!Sign)Sign=C;else if(C*Sign<=0)return false;}
    return true;
}
inline bool Inside(const std::vector<Point>& Hull,Point P)
{
    if(Hull.size()<3||!Finite(P))return false;
    for(unsigned I=0;I<Hull.size();++I){const double C=Cross(Hull[I],Hull[(I+1)%Hull.size()],P);if(!std::isfinite(C)||C<-1.e-7)return false;}
    return true;
}
inline std::optional<std::vector<Cell>> RasterizeCellCentres(const Map& M,const std::vector<Point>& Hull)
{
    if(!ValidMap(M))return std::nullopt;
    const auto Canonical=ConvexHull(Hull);
    if(!Canonical||Canonical->size()!=Hull.size())return std::nullopt;
    for(unsigned I=0;I<Hull.size();++I)
        if((*Canonical)[I].X!=Hull[I].X||(*Canonical)[I].Y!=Hull[I].Y)return std::nullopt;
    std::vector<Cell> Cells;
    // Exact explicit convention: sample pixel centres in world space. This is
    // logical raster approximation, NEVER a replacement for actual mesh physics.
    for(int Y=0;Y<400;++Y)for(int X=0;X<600;++X)
        if(Inside(Hull,ToWorld(M,X+.5,Y+.5)))Cells.push_back({X,Y});
    if(Cells.empty())return std::nullopt;
    return Cells;
}
inline double MaximumCellRadiusCm(const Map& M)
{
    if(!ValidMap(M))return -1;
    double R=0;
    for(int Y:{0,399})for(int X:{0,599})
    {
        const auto Centre=ToWorld(M,X+.5,Y+.5);
        for(int DY:{0,1})for(int DX:{0,1}){const auto Corner=ToWorld(M,X+DX,Y+DY);R=std::max(R,std::hypot(Corner.X-Centre.X,Corner.Y-Centre.Y));}
    }
    return R; // bound for this bilinear cell-centre convention, not mesh tolerance
}
inline bool ScopedOrigin(int Screen,int Placement)
{ return (Screen==31&&Placement==3)||(Screen==209&&Placement==13); }
}
