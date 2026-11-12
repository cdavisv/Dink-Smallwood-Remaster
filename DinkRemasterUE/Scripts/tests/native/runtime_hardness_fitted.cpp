#include "Hardness/DinkHardnessSession.h"
#include <cassert>
#include <iostream>
using namespace DinkHardness;
struct Geometry final:FittedGeometry {
 bool Valid=true;bool Current()const noexcept override{return Valid;}
 const void* BackendTag()const noexcept override{return this;}
};
struct Owner final:PhysicsOwner {
 bool Fail=false,Published=false;std::vector<OwnedRect> Raster;std::size_t Shapes=0;
 int Version()const noexcept override{return 1;} int GetScreen()const noexcept override{return 31;}
 int GetVision()const noexcept override{return 0;}bool IsAuthoredScreen()const noexcept override{return false;}
 void InvalidateForScreenRebuild()noexcept override{}bool HasAdmittedBaseline()const noexcept override{return true;}
 std::uintptr_t GetWorldCookie()const noexcept override{return 1;}
 struct Prepared final:PreparedPhysics {Owner& O;std::vector<OwnedRect> R;std::size_t N;
 Prepared(Owner& In,std::vector<OwnedRect> RR,std::size_t NN):O(In),R(std::move(RR)),N(NN){}
 bool Commit(void* C,PublishFn F)noexcept override {
  if(O.Fail)return false;
  O.Raster=std::move(R);O.Shapes=N;O.Published=true;F(C);return true;
 }};
 std::unique_ptr<PreparedPhysics> Prepare(const std::vector<OwnedRect>& R)override{return PrepareFitted(R,{},{});}
 std::unique_ptr<PreparedPhysics> PrepareFitted(const std::vector<OwnedRect>& R,const std::vector<FittedOwner>& F,
   const std::vector<std::uint8_t>& S)override {
  for(const auto& G:F)if(!G.Geometry||!G.Geometry->Current())return nullptr;
  auto Projected=FittedRasterRects(R,F,S);if(!Projected)return nullptr;
  std::size_t Count=0;for(const auto& G:F)if(std::find(S.begin(),S.end(),G.Code)==S.end())++Count;
  return std::make_unique<Prepared>(*this,std::move(*Projected),Count);
 }
};
static bool Contains(const std::vector<OwnedRect>& RR,int X,int Y,int Code){
 for(const auto& R:RR)if(R.Code==Code&&X>=R.Bounds.Left&&X<R.Bounds.Right&&Y>=R.Bounds.Top&&Y<R.Bounds.Bottom)return true;
 return false;
}
int main(){
 auto GeometryA=std::make_shared<Geometry>(),GeometryB=std::make_shared<Geometry>();
 FittedOwner A{113,123,GeometryA,{10*600+10,10*600+11}};
 FittedOwner B{113,124,GeometryB,{10*600+20}};
 std::vector<Stamp> AS{{{10,10,12,11},113}}, BS{{{20,10,21,11},113}};
 auto Ordered=OrderedStamps({},{{4,13,20,0,0,true,{0,0,100,100},BS},
                                {3,13,10,0,0,true,{0,0,100,100},AS},
                                {5,14,30,0,0,true,{11,10,12,11}}});
 SpriteState Empty(7,13,10,0,0,true,{0,0,100,100});Empty.bFittedStamp=true;
 auto EmptyOrdered=OrderedStamps({},{Empty});assert(EmptyOrdered&&EmptyOrdered->empty());
 assert(Ordered&&Ordered->size()==3&&(*Ordered)[0].Bounds.Left==10&&(*Ordered)[1].Bounds.Left==20&&(*Ordered)[2].Code==114);
 Layers::Pixels Base(240000,0);Base[10*600+10]=2;Base[10*600+11]=3;
 auto Runtime=Session::Create(Base,{},31,0);assert(Runtime);Owner Physics;
 std::vector<Stamp> Stamps=AS;Stamps.insert(Stamps.end(),BS.begin(),BS.end());
 Stamps.push_back({{30,10,32,11},113}); // unrelated same-code contributor
 assert(Runtime->RedrawFitted({},Stamps,Physics,{A,B},{}));
 assert(Runtime->Get(10,10)==113&&Physics.Shapes==2);
 assert(!Contains(Physics.Raster,10,10,113)&&!Contains(Physics.Raster,20,10,113));
 assert(Contains(Physics.Raster,30,10,113));
 auto Before=Runtime->Pixels();Physics.Fail=true;
 assert(!Runtime->RedrawFitted(A.Cells,BS,Physics,{B},{}));assert(Runtime->Pixels()==Before&&Physics.Shapes==2);
 Physics.Fail=false;GeometryB->Valid=false;
 assert(!Runtime->RedrawFitted(A.Cells,BS,Physics,{B},{}));assert(Runtime->Pixels()==Before);
 GeometryB->Valid=true;
 assert(Runtime->RedrawFitted(A.Cells,BS,Physics,{B},{}));
 assert(Runtime->Get(10,10)==2&&Runtime->Get(11,10)==3&&Physics.Shapes==1);
 assert(Contains(Physics.Raster,10,10,2)&&Contains(Physics.Raster,11,10,3));
 assert(Runtime->Get(30,10)==113&&Contains(Physics.Raster,30,10,113)); // preserve unrelated stale owner
 assert(Runtime->RedrawFitted({},BS,Physics,{B},{113}));
 assert(Runtime->Get(20,10)==113&&Physics.Shapes==0&&!Contains(Physics.Raster,30,10,113));
 auto Invalid=B;Invalid.Cells.push_back(Invalid.Cells.front());
 assert(!Runtime->RedrawFitted({},BS,Physics,{Invalid},{}));
 Before=Runtime->Pixels();assert(!Runtime->RedrawFitted({240000},BS,Physics,{B},{}));assert(Runtime->Pixels()==Before);
 std::cout<<"PASS fitted order/same-code residual/water-floor restoration/atomic refusal/prop suppression\n";
}
