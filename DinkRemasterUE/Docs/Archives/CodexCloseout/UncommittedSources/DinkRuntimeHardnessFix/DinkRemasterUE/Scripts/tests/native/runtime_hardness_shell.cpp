#include "Hardness/DinkHardnessShell.h"
#include "Hardness/DinkHardnessAuthority.h"
#include <string>
#include <cassert>
#include <iostream>
#include <limits>
using namespace DinkHardness;
float Ray(ShellPoint Origin,ShellPoint Direction,const ShellTriangle& T)
{
    const auto E1=Subtract(T[1],T[0]),E2=Subtract(T[2],T[0]),P=Cross(Direction,E2);
    const float Det=Dot(E1,P); if(std::abs(Det)<1e-6f) return -1;
    const auto S=Subtract(Origin,T[0]); const float U=Dot(S,P)/Det;
    const auto Q=Cross(S,E1); const float V=Dot(Direction,Q)/Det,Distance=Dot(E2,Q)/Det;
    return U>=0 && V>=0 && U+V<=1 && Distance>=0 ? Distance : -1;
}
int main()
{
    const std::vector<std::string> Authority{"art/stonebrook.json","art/exterior.json"};
    assert(ExactAuthorityPaths(Authority,Authority));
    assert(!ExactAuthorityPaths(Authority,std::vector<std::string>{"art/exterior.json"})); // omit authored house
    assert(!ExactAuthorityPaths(Authority,std::vector<std::string>{"art/stonebrook.json","art/exterior.json","art/exterior.json"}));
    assert(!ExactAuthorityPaths(std::vector<std::string>{},std::vector<std::string>{}));
    std::array<ShellPoint,8> V{{{0,0,0},{37,0,0},{37,21,0},{0,21,0},
                                {0,0,300},{37,0,300},{37,21,300},{0,21,300}}};
    const auto Shell=OpenPrismShell(V); assert(Shell && Shell->size()==10);
    int Tops=0,Sides=0; float Hit=-1;
    for(const auto& T:*Shell)
    {
        const auto N=Cross(Subtract(T[1],T[0]),Subtract(T[2],T[0]));
        assert(N.Z>=0); // no bottom or inverted top
        if(T[0].Z==300 && T[1].Z==300 && T[2].Z==300) { ++Tops; assert(N.Z>0); }
        else ++Sides;
        const float D=Ray({18,10,-1},{0,0,1},T); if(D>=0 && (Hit<0 || D<Hit)) Hit=D;
    }
    assert(Tops==2 && Sides==8 && Hit==301); // low-object-only ray has NO floor face at1
    const ShellTriangle IncorrectConvexBottom{{V[0],V[2],V[1]}};
    assert(Ray({18,10,-1},{0,0,1},IncorrectConvexBottom)==1);
    auto Bad=V; Bad[0].X=std::numeric_limits<float>::quiet_NaN(); assert(!OpenPrismShell(Bad));
    Bad=V; Bad[1]=Bad[0]; Bad[5]=Bad[4]; assert(!OpenPrismShell(Bad));
    auto Skew=V; Skew[1].Y=2; Skew[5].Y=2; Skew[2].X=41; Skew[6].X=41;
    assert(OpenPrismShell(Skew));
    std::cout<<"PASS original open-bottom shell / cooking winding / low-only below ray / closed-hull negative control / skew / invalid\n";
}
