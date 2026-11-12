#include "DinkProbeContactRoute.h"
#include <limits>
#if !defined(DINK_CONTACT_STANDALONE)
#include "Misc/AutomationTest.h"
#endif
#if defined(DINK_CONTACT_STANDALONE) || WITH_DEV_AUTOMATION_TESTS
namespace
{
template<class Check> void Controls(Check Test)
{
    using namespace DinkProbeContactRoute;
    Test(DamageContact(15,1000,true,false,680,680,10),"neutral positive-touch population included independent of HP/nohit/script");
    Test(!DamageContact(15,1000,false,false,680,680,10)&&!DamageContact(1000,1000,true,false,680,680,10)&&!DamageContact(1,1000,true,false,680,680,10),"inactive/player/no-sprite excluded exactly");
    Test(!DamageContact(15,1000,true,true,680,680,10)&&!DamageContact(15,1000,true,false,680,680,-1)&&!DamageContact(15,1000,true,false,681,680,10),"text/non-damage touch/other screen excluded");
    const Grid G{7,7,6,0,0};std::vector<unsigned char> Free(49,1);
    const std::vector<DinkProbeContactRoute::Rect> Boxes{TouchRect(18,18,24,24,0)};
    const int Start=21,Goal=27;const Point Actual=G.Centre(Start);
    std::vector<double> Dist;std::vector<int> Parent;
    Distances(G,Free,Start,Actual,Boxes,Dist,Parent);
    Test(Dist[Goal]>36,"safe endpoint requires detour around intervening contact");
    std::vector<int> Path;
    for(int I=Goal;I!=Start&&I!=-1;I=Parent[I]){Path.insert(Path.begin(),I);if(Path.size()>49)break;}
    Test(RouteSafe(G,Actual,Path,Boxes),"reconstructed parent path is continuously contact safe");
    Test(!RouteSafe(G,Actual,{Goal},Boxes),"safe destination cannot admit a crossed-box shortcut");
    Test(!EdgeSafe({13.6,9.6},{13.6,9.6},{TouchRect(14,10,16,14,0)}),"inclusive integer rounding corner is refused");
    Test(EdgeSafe({13.4,9.4},{13.4,9.4},{TouchRect(14,10,16,14,0)}),"outside rounding envelope remains clear");
    Test(EdgeSafe({19,21},{15,21},Boxes),"already touching can strictly leave nearest face");
    Test(!EdgeSafe({19,21},{27,21},Boxes),"crossing toward far face is not an escape");
    Test(!EdgeSafe({19,21},{19,22},Boxes),"tangential movement without reduced penetration refused");
    auto Neighbour=Boxes;Neighbour.push_back({12,18,16,24});
    Test(!EdgeSafe({19,21},{15,21},Neighbour),"escaping cannot enter neutral adjacent contact");
    const int Trapped=24,Escape=26;
    Distances(G,Free,Trapped,G.Centre(Trapped),Boxes,Dist,Parent);
    Test(Dist[Escape]>0,"inside start has monotonic outward route without clearing masks");
    Path.clear();for(int I=Escape;I!=Trapped&&I!=-1;I=Parent[I]){Path.insert(Path.begin(),I);if(Path.size()>49)break;}
    Test(RouteSafe(G,G.Centre(Trapped),Path,Boxes),"full escape route preserves outward condition");
    Free.assign(49,0);Free[Start]=Free[Goal]=1;
    Distances(G,Free,Start,Actual,{},Dist,Parent);
    Test(Dist[Goal]<0,"disconnected endpoint cannot use nearest-free relocation");
    Test(!EdgeSafe({389,348.64031982421932},{389,345.64031982421864},{TouchRect(361,326,409,346,2)}),"actual first-hit neutral15 paced witness is refused even minimum margin");
    Test(!EdgeSafe({404.57717895087239,216.57719421919626},{406.69848632250182,218.69851685282822},{TouchRect(379,220,427,240,2)}),"actual hostile14 approach witness is refused");
    const DinkProbeContactRoute::Rect RoundedCapsule=TouchRect(10,10,20,20,2+3); // ceil(2.01px), not truncated2
    Test(!EdgeSafe({25.49,15},{25.49,15},{RoundedCapsule}),"ceil capsule plus half-pixel envelope required");
    Test(Free[Start]==1&&Free[Goal]==1,"routing never changes original static mask");
    Free.assign(49,1);const std::vector<DinkProbeContactRoute::Rect> AllBlocked{{-10,-10,60,60}};
    Distances(G,Free,Start,Actual,AllBlocked,Dist,Parent);
    bool ClearReachable=false;for(int I=0;I<49;++I)ClearReachable=ClearReachable||(Dist[I]>=0&&PointClear(G.Centre(I),AllBlocked));
    Test(!ClearReachable,"no contact-free endpoint refuses without clearing hazard mask");
    const Point Offset{2.1,21.5};const std::vector<DinkProbeContactRoute::Rect> FirstCorner{{2.4,21.2,2.6,21.6}};
    Distances(G,Free,Start,Offset,FirstCorner,Dist,Parent);
    Test(Dist[22]>0&&Parent[22]!=Start,"first edge uses actual offset rather than start cell centre");
    Test(EdgeSafe(G.Centre(Start),G.Centre(22),FirstCorner)&&!RouteSafe(G,Offset,{22},FirstCorner),"actual-to-first-centre intersection cannot hide behind safe cell-centre edge");
    const std::vector<DinkProbeContactRoute::Rect> TurnBox{{5,5,7,7}};
    Test(RouteSafe(G,{3,3},{7,8},TurnBox)&&!EdgeSafe({3,3},{9,9},TurnBox),"multiwaypoint safe route still requires paced straight shortcut guard");
    const std::vector<DinkProbeContactRoute::Rect> Overlap{{0,0,10,10},{-4,0,6,10}};
    Test(!EdgeSafe({5,5},{3,5},Overlap),"already inside two boxes cannot escape one by deepening the other");
    Test(EdgeSafe({5,5},{7,5},Overlap),"overlapping traps permit only simultaneously outward escape");
    Free.assign(49,1);Free[1]=Free[7]=0;
    Distances(G,Free,0,G.Centre(0),{},Dist,Parent);
    Test(Dist[8]<0,"diagonal cannot cut between blocked static orthogonal neighbours");
    Test(!EdgeSafe({std::numeric_limits<double>::quiet_NaN(),0},{1,1},{})&&!PointClear({1,1},{{2,0,1,1}}),"nonfinite points and malformed rectangles refuse");
}
}
#if defined(DINK_CONTACT_STANDALONE)
#include <iostream>
int main(){int Failed=0;Controls([&](bool Pass,const char* Name){if(!Pass){std::cerr<<Name<<'\n';++Failed;}});return Failed?1:0;}
#else
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkProbeContactRouteCurrent,"Dink.Gameplay.ProbeContactRoute.CurrentFallback",EAutomationTestFlags_ApplicationContextMask|EAutomationTestFlags::ProductFilter)
bool FDinkProbeContactRouteCurrent::RunTest(const FString& Parameters)
{Controls([&](bool Pass,const char* Name){TestTrue(UTF8_TO_TCHAR(Name),Pass);});return true;}
#endif
#endif
