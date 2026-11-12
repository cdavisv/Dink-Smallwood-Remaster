#include "Hardness/DinkFamilyFitMath.h"
#include <cassert>
#include <iostream>
#include <fstream>
#include <limits>
using namespace DinkFamilyFit;
std::vector<Point> Barrel(Point At,double Yaw)
{
    std::vector<Point> P;
    for(int I=0;I<64;++I){const double A=I*6.283185307179586/64+Yaw;P.push_back({At.X+41.973323822*std::cos(A),At.Y+42.229946136*std::sin(A)});}
    return *ConvexHull(std::move(P));
}
int main(int Argc,char** Argv)
{
    if(Argc==2)
    {
        std::ifstream Input(Argv[1]);double X=0,Y=0,Z=0,Low=1.e9,High=-1.e9;
        std::vector<Point> Points;
        const Map M{{0,0},{4125,0},{0,2750},{4125,2750}};const auto At=ToWorld(M,300,316);
        while(Input>>X>>Y>>Z){Points.push_back({At.X+X,At.Y+Y});Low=std::min(Low,Z);High=std::max(High,Z);}
        assert(Points.size()>1000&&High-Low>100&&High-Low<102);
        const auto Hull=ConvexHull(std::move(Points));assert(Hull&&Hull->size()>8);
        const auto Cells=RasterizeCellCentres(M,*Hull);assert(Cells&&Cells->size()>50&&Cells->size()<200);
        std::cout<<"PASS actual FBX projected with production math cells="<<Cells->size()<<" hull="<<Hull->size()<<" height="<<High-Low<<"\n";return 0;
    }
    assert(Argc==1);
    assert(ScopedOrigin(31,3)&&ScopedOrigin(209,13));
    assert(!ScopedOrigin(1,3)&&!ScopedOrigin(31,13)&&!ScopedOrigin(209,3));
    const Map Square{{219424.86,-159458.1},{223549.86,-159458.1},{219424.86,-156708.1},{223549.86,-156708.1}};
    const auto Ground=ToWorld(Square,300,316);const auto Shape=Barrel(Ground,32*3.141592653589793/180);
    auto Cells=RasterizeCellCentres(Square,Shape);assert(Cells&&Cells->size()>50&&Cells->size()<200);
    int L=600,T=400,R=0,B=0;
    for(auto C:*Cells){L=std::min(L,C.X);R=std::max(R,C.X+1);T=std::min(T,C.Y);B=std::max(B,C.Y+1);assert(Inside(Shape,ToWorld(Square,C.X+.5,C.Y+.5)));}
    assert(R-L<15&&B-T<15);assert((R-L)*(B-T)<37*21); // old audited777pixel box is not reused
    assert(std::abs(MaximumCellRadiusCm(Square)-std::hypot(6.875/2,6.875/2))<1.e-8);
    // Real warped209 corners; no rounded "m_per_px" or uniform-width shortcut.
    const Map Warped{{64030.12,12138.16},{68724.60,12116.35},{63521.16,14891.94},{68465.66,14849.07}};
    const auto Ground209=ToWorld(Warped,396,306);const auto P209=Barrel(Ground209,134*3.141592653589793/180);
    auto W=RasterizeCellCentres(Warped,P209);assert(W&&W->size()>50&&W->size()<200);
    assert(MaximumCellRadiusCm(Warped)>4&&MaximumCellRadiusCm(Warped)<8);
    // Fitted visual/physical anchor is script ground, never whole card image
    // centre(−13pixels: original173 pivot41 vs56px image centre28).
    assert(std::abs(Ground.X-(ToWorld(Square,300,316).X-89.44))>89);
    assert(std::abs(Ground209.X-(Ground209.X-105.82))>105);
    auto Reverse=Shape;std::reverse(Reverse.begin(),Reverse.end());assert(!RasterizeCellCentres(Square,Reverse));
    auto Invalid=Shape;Invalid[0].X=std::numeric_limits<double>::quiet_NaN();assert(!ConvexHull(Invalid));
    assert(!ConvexHull({{0,0},{1,1},{2,2}}));
    assert(!ConvexHull({{-1.e308,-1.e308},{1.e308,-1.e308},{1.e308,1.e308},{-1.e308,1.e308}}));
    Map Folded=Square;std::swap(Folded.NE,Folded.SE);assert(!ValidMap(Folded));
    Map Singular{{0,0},{1,0},{0,0},{1,0}};assert(!ValidMap(Singular));
    auto Triangle=ConvexHull({{0,0},{.01,0},{0,.01}});assert(Triangle&&!RasterizeCellCentres(Square,*Triangle));
    const auto Unique=ConvexHull({{0,0},{1,0},{1,1},{0,1},{0,0},{.5,.5}});assert(Unique&&Unique->size()==4);
    std::cout<<"PASS actual convex/raster/map boundary math, two audited scales, ground-anchor regression, explicit cell-centre convention\n";
}
