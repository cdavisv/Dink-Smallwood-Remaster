#pragma once
#include <algorithm>
#include <cmath>
#include <functional>
#include <queue>
#include <utility>
#include <vector>
// Test-driver only. Closed half-pixel envelope covers the game's rounded XY
// and inclusive hardbox + (2 + ceil(capsuleRadius / screenCmPerPixel)) test.
namespace DinkProbeContactRoute
{
struct Point { double X,Y; };
inline bool Finite(Point P) { return std::isfinite(P.X)&&std::isfinite(P.Y); }
inline bool DamageContact(int Handle,int NoSprite,bool Active,bool Text,int Screen,int WantedScreen,int Touch)
{ return Handle!=1 && Handle!=NoSprite && Active && !Text && Screen==WantedScreen && Touch>0; }
struct Rect
{
    double L,T,R,B;
    bool Valid() const { return std::isfinite(L)&&std::isfinite(T)&&std::isfinite(R)&&std::isfinite(B)&&L<=R&&T<=B; }
    bool Contains(Point P) const { return P.X>=L&&P.X<=R&&P.Y>=T&&P.Y<=B; }
    double Depth(Point P) const { return Contains(P)?std::min({P.X-L,R-P.X,P.Y-T,B-P.Y}):-1.; }
};
inline Rect TouchRect(int L,int T,int R,int B,int Margin)
{ return {L-Margin-.5,T-Margin-.5,R+Margin+.5,B+Margin+.5}; }
inline bool Intersects(Point A,Point B,Rect Box)
{
    double Lo=0,Hi=1;bool Possible=true;
    const auto Clip=[&](double P,double Delta,double Min,double Max)
    {
        if(Delta==0){Possible=Possible&&P>=Min&&P<=Max;return;}
        double First=(Min-P)/Delta,Last=(Max-P)/Delta;
        if(First>Last)std::swap(First,Last);
        Lo=std::max(Lo,First);Hi=std::min(Hi,Last);
    };
    Clip(A.X,B.X-A.X,Box.L,Box.R);Clip(A.Y,B.Y-A.Y,Box.T,Box.B);
    return Possible&&Lo<=Hi;
}
inline bool EdgeSafe(Point From,Point To,const std::vector<Rect>& Boxes)
{
    if(!Finite(From)||!Finite(To))return false;
    for(const Rect& Box:Boxes)
    {
        if(!Box.Valid())return false;
        if(!Box.Contains(From)){if(Intersects(From,To,Box))return false;continue;}
        // Already touching: strictly decrease penetration along a currently
        // nearest face. The whole straight segment is monotonic outward.
        // All other boxes are checked too: escape cannot enter a new contact.
        const double Depth=Box.Depth(From);
        const bool Outward=(From.X-Box.L==Depth&&To.X<From.X)||(Box.R-From.X==Depth&&To.X>From.X)||
            (From.Y-Box.T==Depth&&To.Y<From.Y)||(Box.B-From.Y==Depth&&To.Y>From.Y);
        if(!Outward||Box.Depth(To)>=Depth)return false;
    }
    return true;
}
inline bool PointClear(Point P,const std::vector<Rect>& Boxes)
{ if(!Finite(P))return false;for(const Rect& Box:Boxes)if(!Box.Valid()||Box.Contains(P))return false;return true; }
struct Grid
{
    int Cols,Rows;double Cell,OriginX,OriginY;
    Point Centre(int I) const { return {OriginX+Cell/2+(I%Cols)*Cell,OriginY+Cell/2+(I/Cols)*Cell}; }
};
inline void Distances(const Grid& G,const std::vector<unsigned char>& Free,int Start,Point Actual,
    const std::vector<Rect>& Boxes,std::vector<double>& Dist,std::vector<int>& Parent)
{
    const int Count=G.Cols*G.Rows;Dist.assign(Count,-1);Parent.assign(Count,-1);
    if(Start<0||Start>=Count||Free.size()!=static_cast<unsigned>(Count))return;
    using Node=std::pair<double,int>;
    std::priority_queue<Node,std::vector<Node>,std::greater<Node>> Heap;
    Dist[Start]=0;Heap.push({0,Start});
    while(!Heap.empty())
    {
        const Node Current=Heap.top();Heap.pop();if(Current.first>Dist[Current.second])continue;
        const int Cx=Current.second%G.Cols,Cy=Current.second/G.Cols;
        const Point From=Current.second==Start?Actual:G.Centre(Current.second);
        for(int Dy=-1;Dy<=1;++Dy)for(int Dx=-1;Dx<=1;++Dx)
        {
            const int Nx=Cx+Dx,Ny=Cy+Dy;
            if((Dx==0&&Dy==0)||Nx<0||Ny<0||Nx>=G.Cols||Ny>=G.Rows)continue;
            const int Next=Ny*G.Cols+Nx;const Point To=G.Centre(Next);
            // Source is actual current position, never a nearest-free relocation.
            // No static mask is cleared; only reached safe edges enter the heap.
            if(!Free[Next]||(Dx&&Dy&&(!Free[Cy*G.Cols+Nx]||!Free[Ny*G.Cols+Cx]))||!EdgeSafe(From,To,Boxes))continue;
            const double Cost=Current.first+std::hypot(To.X-From.X,To.Y-From.Y);
            if(Dist[Next]<0||Cost<Dist[Next]){Dist[Next]=Cost;Parent[Next]=Current.second;Heap.push({Cost,Next});}
        }
    }
}
inline bool RouteSafe(const Grid& G,Point Actual,const std::vector<int>& Path,const std::vector<Rect>& Boxes)
{
    for(int I:Path)
    {
        if(I<0||I>=G.Cols*G.Rows)return false;
        const Point To=G.Centre(I);if(!EdgeSafe(Actual,To,Boxes))return false;Actual=To;
    }
    return true;
}
}
