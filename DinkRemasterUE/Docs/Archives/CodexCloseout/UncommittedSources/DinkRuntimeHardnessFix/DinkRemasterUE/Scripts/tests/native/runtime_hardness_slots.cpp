#include "Hardness/DinkHardnessSlots.h"
#include "Hardness/DinkHardnessActivation.h"
#include "Hardness/DinkHardnessSession.h"
#include "Hardness/DinkDisplayedHardness.h"
#include <cassert>
#include <iostream>
using namespace DinkHardness;
struct Physical : PhysicsOwner
{
    bool Fail=false;Layers::Pixels Visible=Layers::Pixels(240000,0);int Publishes=0;
    struct Prepared : PreparedPhysics {
        Physical& P;Layers::Pixels Next;
        Prepared(Physical& Owner,Layers::Pixels Pixels):P(Owner),Next(std::move(Pixels)){}
        bool Commit(void* Context,PublishFn Publish) noexcept override {
            if(P.Fail)return false;
            P.Visible=std::move(Next);Publish(Context);++P.Publishes;return true;
        }
    };
    int Version()const noexcept override{return 1;}
    bool HasAdmittedBaseline()const noexcept override{return true;}
    void InvalidateForScreenRebuild()noexcept override{}
    std::uintptr_t GetWorldCookie()const noexcept override{return 1;}
    int GetScreen()const noexcept override{return 209;}
    int GetVision()const noexcept override{return 0;}
    bool IsAuthoredScreen()const noexcept override{return false;}
    std::unique_ptr<PreparedPhysics> Prepare(const std::vector<OwnedRect>& Rects)override {
        Layers::Pixels Next(240000,0);
        for(const auto&R:Rects)for(int Y=R.Bounds.Top;Y<R.Bounds.Bottom;++Y)
            for(int X=R.Bounds.Left;X<R.Bounds.Right;++X)Next[Y*600+X]=R.Code;
        return std::make_unique<Prepared>(*this,std::move(Next));
    }
};
int main()
{
    // Partial migration: new data does not change an old world's sprite order
    // or replace its authored/aggregate collision. A marked incomplete world
    // must refuse instead of quietly taking that legacy path.
    static_assert(SelectActivation(false,false)==Activation::Legacy);
    static_assert(SelectActivation(false,true)==Activation::Legacy);
    static_assert(SelectActivation(true,false)==Activation::Refuse);
    static_assert(SelectActivation(true,true)==Activation::Projected);
    const auto Missing=DisplayedBounds(173,99,416,306,[](int,int)->std::optional<Rect>{return std::nullopt;});
    assert(!Missing); // no invented init-sequence/first-frame hardness box

    static_assert(SelectVisionTransition(true,false)==VisionTransition::RebindBase);
    static_assert(SelectVisionTransition(false,false)==VisionTransition::PreservePublished);
    static_assert(SelectVisionTransition(false,true)==VisionTransition::RebuildScreen);
    struct CallerState {int Sprite=42,AttachedTo=42,Id=71;};
    CallerState Caller;PreserveForceVisionCaller(Caller,1000);
    assert(Caller.Sprite==1000&&Caller.AttachedTo==1000&&Caller.Id==71);
    static_assert(ShouldApplyOriginalVision(true,0));
    static_assert(!ShouldApplyOriginalVision(true,1)); // redraw leaves born live actors alone
    static_assert(ShouldApplyOriginalVision(false,1)); // force/full admission applies all
    static_assert(!ApplyFactVisionImmediately(true));
    static_assert(ApplyFactVisionImmediately(false));
    static_assert(RestartOriginalScreenOnLoad(true)); // same-screen load also rebuilds
    static_assert(!RestartOriginalScreenOnLoad(false));
    struct LiveState {int Screen=1,Handle=72;double X=230,Y=177;};
    LiveState Live;CarryLiveScreenIdentity(Live,209);
    assert(Live.Screen==209&&Live.Handle==72&&Live.X==230&&Live.Y==177);
    OriginalSlots Slots;
    assert(Slots.Birth(900)); // original base-main birth takes slot2 before placements
    auto Order=MixedInitialOrder({{1,1,200,0,0},{2,1,100,0,0},{3,0,90,0,0},{4,1,2,0,2}},0);
    assert(Order&&Order->size()==3&&(*Order)[0].Owner==3&&(*Order)[1].Owner==2);
    for(const auto&P:*Order)assert(P.Type==1?Slots.ReserveEditor(P.Owner):Slots.Scratch());
    // UE handles still bind in original UE data order1then2; hardness slots do not.
    assert(Slots.BindEditor(1,2)&&Slots.BindEditor(2,3)&&Slots.Bound());
    assert(Slots.Slot(900)==2&&Slots.Slot(3)==3&&Slots.Slot(2)==4);
    Rect Box{379,291,416,312};
    auto Tied=OrderedStamps({},{{*Slots.Slot(2),1,150,0,0,true,Box},{*Slots.Slot(3),2,150,0,0,true,Box}});
    assert(Tied&&(*Tied)[0].Code==102&&(*Tied)[1].Code==101);
    // Text is also an occupied original slot; deactivation makes the FIRST free slot reusable.
    assert(Slots.Birth(1001)&&Slots.Slot(1001)==5);
    Slots.Release(3);assert(Slots.Birth(4)&&Slots.Slot(4)==3);
    assert(!Slots.Reactivate(3)&&!Slots.Valid()); // never renumber UE handle to conceal reuse
    OriginalSlots Capacity;for(int I=2;I<300;++I)assert(Capacity.Birth(1000+I));
    assert(!Capacity.Scratch()&&!Capacity.Valid());
    assert(!MixedInitialOrder({{1,1,0,0,0},{1,0,0,0,0}},0));
    auto Que=MixedInitialOrder({{1,1,10,200,0},{2,1,50,0,0},{3,1,0,20000,0}},0);
    assert(Que&&Que->size()==2&&(*Que)[0].Owner==2);

    // update_play_changes: persistent type/pictures override transient hard only at redraw/build.
    auto Flat=ProjectEditorFields(1,0,173,1,3,173,6,0);
    auto Stump=ProjectEditorFields(0,0,32,1,4,20,29,1);
    assert(Flat.Type==0&&Flat.Hard==1&&Flat.Seq==173&&Flat.Frame==6&&Flat.ClearScript);
    assert(Stump.Type==1&&Stump.Hard==0&&Stump.Seq==20&&Stump.Frame==29&&Stump.ClearScript);
    assert(ProjectEditorFields(1,0,1,1,6,0,0).Removed);
    assert(ProjectEditorFields(1,0,1,1,0,0,0,1).Hard==1);
    assert(ProjectEditorFields(1,0,1,1,0,0,0,-1).Hard==-1); // inactive setter result in smallMap
    auto None=ProjectEditorFields(1,0,32,1,0,20,29);
    assert(None.Seq==32&&None.Frame==1&&!None.ClearScript);

    Layers::Pixels Base(240000,0);Base[300*600+390]=2;
    auto Journal=Layers::Create(Base,{});assert(Journal); // BASE MAIN is tile-only
    Stamp A{Box,101},B{Box,102};
    assert(Journal->Redraw({0,0,0,0},{A,B})); // INITIAL mixed rank: live A then background B
    assert(Journal->Get(390,300)==102);
    assert(Journal->Redraw(Box,{B,A})); // DRAW: background then active, different top owner
    assert(Journal->Get(390,300)==101);
    // sp_hard1 alone does not call Redraw. Late admission must retain the journal,
    // not infer softness from current flags or reset to vanilla sidecar stamps.
    auto SessionBefore=Session::CreateProjected(*Journal,209,0);assert(SessionBefore&&SessionBefore->Get(390,300)==101);
    assert(Journal->Redraw(Box,{}));assert(Journal->Get(390,300)==2);
    auto Admitted=Session::CreateProjected(*Journal,209,0);assert(Admitted);
    Physical P;bool Published=false;
    auto Publish=[](void* C)noexcept{*static_cast<bool*>(C)=true;};
    P.Fail=true;assert(!Admitted->Redraw({0,0,0,0},{},P,&Published,Publish)&&!Published&&P.Publishes==0);
    P.Fail=false;assert(Admitted->Redraw({0,0,0,0},{},P,&Published,Publish));
    assert(Published&&P.Visible[300*600+390]==2&&Admitted->Get(390,300)==2);
    // Saved background-nohard initial build never seeds the old barrel stamp.
    auto Reload=Layers::Create(Base,{});assert(Reload);if(Flat.Hard==0)Reload->Redraw({0,0,0,0},{{Box,113}});
    assert(Reload->Get(390,300)==2);
    std::cout<<"PASS original slots/base-main/mixed-vs-draw/persisted projection/late admission/transaction\n";
}
