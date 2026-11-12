#include "Hardness/DinkHardnessSession.h"
#include "Hardness/DinkEditorPicture.h"
#include "Hardness/DinkDisplayedHardness.h"
#include <cassert>
#include <iostream>
using namespace DinkHardness;
struct FakePhysics : PhysicsOwner
{
    int V=1, S=209, Vis=0, Prepares=0, Commits=0;
    bool Authored=false, Fail=false, FailCommit=false;
    Layers::Pixels Visible=Layers::Pixels(600*400,0);
    struct Prepared : PreparedPhysics
    {
        FakePhysics& Owner; Layers::Pixels Next;
        Prepared(FakePhysics& O, Layers::Pixels N) : Owner(O), Next(std::move(N)) {}
        bool Commit(void* Context, PublishFn Publish) noexcept override
        {
            if(Owner.FailCommit) return false;
            Owner.Visible=std::move(Next); ++Owner.Commits;
            Publish(Context); return true;
        }
    };
    bool Admitted=true;
    void InvalidateForScreenRebuild() noexcept override { Admitted=false; }
    bool HasAdmittedBaseline() const noexcept override { return Admitted; }
    std::uintptr_t GetWorldCookie() const noexcept override { return 1; }
    int Version() const noexcept override { return V; }
    int GetScreen() const noexcept override { return S; }
    int GetVision() const noexcept override { return Vis; }
    bool IsAuthoredScreen() const noexcept override { return Authored; }
    std::unique_ptr<PreparedPhysics> Prepare(const std::vector<OwnedRect>& Rects) override
    {
        ++Prepares;
        if(Fail) return nullptr;
        Layers::Pixels Next(600*400,0);
        for(const auto& R:Rects)
            for(int Y=R.Bounds.Top;Y<R.Bounds.Bottom;++Y)
                for(int X=R.Bounds.Left;X<R.Bounds.Right;++X) Next[Y*600+X]=R.Code;
        return std::make_unique<Prepared>(*this,std::move(Next));
    }
};
int main()
{
    auto Picture=[](int Seq,int Frame)->std::optional<Rect> {
        if(Seq==32 && Frame==1) return Rect{-48,-13,46,23};
        if(Seq==173 && Frame==1) return Rect{-17,-15,20,6};
        return std::nullopt;
    };
    const auto Displayed=DisplayedBounds(32,1,416,306,Picture);
    assert(Displayed && Displayed->Right-Displayed->Left==94 && Displayed->Bottom-Displayed->Top==36);
    const auto Empty=DisplayedBounds(0,1,416,306,Picture);
    assert(Empty && Empty->Right==Empty->Left && Empty->Bottom==Empty->Top);
    std::int32_t Stored=7;
    assert(ChangeEditorPicture(0,true,55,Stored)==-1 && Stored==7);
    assert(ChangeEditorPicture(-1,true,55,Stored)==-1 && Stored==7);
    assert(ChangeEditorPicture(100,true,55,Stored)==-1 && Stored==7);
    assert(ChangeEditorPicture(1,true,-1,Stored)==7 && Stored==7);
    assert(ChangeEditorPicture(99,true,65537,Stored)==1);
    assert(ChangeEditorPicture(1,true,-2,Stored)==65534);
    assert(ChangeEditorPicture(1,false,257,Stored)==1);
    assert(ChangeEditorPicture(99,false,-2,Stored)==254);
    Layers::Pixels Base(600*400,0); Base[300*600+390]=2;
    Stamp Barrel{{379,291,416,312},113}, Behind{{400,300,430,320},114};
    auto Runtime=Session::Create(Base,{Barrel},209,0);
    auto Other=Session::Create(Base,{Behind},210,2);
    FakePhysics Physics;
    assert(Runtime && Other && Runtime->Redraw({0,0,0,0},{},Physics));
    auto LogicalBefore=Runtime->Pixels(), PhysicalBefore=Physics.Visible;
    Physics.Fail=true;
    assert(!Runtime->Redraw(Barrel.Bounds,{},Physics));
    assert(Runtime->Pixels()==LogicalBefore && Physics.Visible==PhysicalBefore && Physics.Commits==1);
    struct PublishedContext { Session* Runtime; FakePhysics* Physics; int Calls; };
    PublishedContext Context{&*Runtime,&Physics,0};
    auto Publish=[](void* Raw) noexcept {
        auto& P=*static_cast<PublishedContext*>(Raw);
        assert(P.Runtime->Pixels()==P.Physics->Visible); ++P.Calls;
    };
    Physics.Fail=false; Physics.FailCommit=true;
    assert(!Runtime->Redraw(Barrel.Bounds,{},Physics,&Context,Publish));
    assert(Context.Calls==0);
    assert(Runtime->Pixels()==LogicalBefore && Physics.Visible==PhysicalBefore && Physics.Commits==1);
    Physics.FailCommit=false; Physics.Authored=true;
    int Calls=Physics.Prepares;
    assert(!Runtime->Redraw(Barrel.Bounds,{},Physics) && Physics.Prepares==Calls);
    Physics.Authored=false; Physics.S=210;
    assert(!Runtime->Redraw(Barrel.Bounds,{},Physics) && Physics.Prepares==Calls);
    Physics.S=209; Physics.Vis=1;
    assert(!Runtime->Redraw(Barrel.Bounds,{},Physics) && Physics.Prepares==Calls);
    Physics.Vis=0; Physics.V=0;
    assert(!Runtime->Redraw(Barrel.Bounds,{},Physics) && Physics.Prepares==Calls);
    Physics.V=1;
    assert(Runtime->Redraw(Barrel.Bounds,{},Physics,&Context,Publish));
    assert(Context.Calls==1);
    assert(Runtime->Pixels()==Physics.Visible && Runtime->Get(390,300)==2);
    assert(Other->Get(405,305)==114 && Other->GetVision()==2);
    auto Journal=Layers::Create(Base,{Barrel});
    assert(Journal && Journal->Redraw({390,300,391,301},{}));
    auto Projected=Session::CreateProjected(std::move(*Journal),209,0);
    assert(Projected && Projected->Get(390,300)==2 && Projected->Get(400,300)==113);
    auto Ordered=OrderedStamps({{2,2,50,0,0,true,Behind.Bounds},{1,1,50,0,0,true,Barrel.Bounds}},
                              {{4,4,10,0,0,true,Behind.Bounds},{3,0,10,0,0,true,Barrel.Bounds},
                               {5,0,22024,0,0,true,Barrel.Bounds}});
    assert(Ordered && Ordered->size()==4);
    assert((*Ordered)[0].Code==101 && (*Ordered)[1].Code==102 && (*Ordered)[2].Code==1 && (*Ordered)[3].Code==104);
    assert(!OrderedStamps({{1,100,0,0,0,true,Barrel.Bounds}},{}));
    std::cout << "PASS session isolation/transaction/refusal/authored exclusion/version/scene binding/order\n";
}
