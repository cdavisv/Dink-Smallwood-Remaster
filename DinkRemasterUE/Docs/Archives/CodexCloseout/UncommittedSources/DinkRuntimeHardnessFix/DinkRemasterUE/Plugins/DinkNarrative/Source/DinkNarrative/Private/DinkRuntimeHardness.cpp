#include "DinkGameplay.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkStorySubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "Hardness/DinkRuntimeHardnessSource.h"
#include "Hardness/DinkEditorPicture.h"
#include "Hardness/DinkDisplayedHardness.h"
#include "Hardness/DinkHardnessSlots.h"
#include "Dom/JsonObject.h"
#include "Hardness/DinkRuntimeHardnessWorldSubsystem.h"
#include "Hardness/DinkHardnessActivation.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PawnMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "DinkOriginComponent.h"
#include "EngineUtils.h"

namespace
{
enum class EOriginalHardnessPhase { BaseMain, InitialPlacements, Live, Refused };
FString LayerFile(int32 Screen,int32 Vision)
{
    return Vision==0 ? FString::Printf(TEXT("Hardness/SCR_%03d_layers.json"),Screen) :
        FString::Printf(TEXT("Hardness/SCR_%03d_v%d_layers.json"),Screen,Vision);
}
}
struct FDinkHardnessProjection
{
    DinkHardness::Layers Map;
    DinkHardness::Layers::Pixels TileBase;
    DinkHardness::OriginalSlots Slots;
    std::vector<DinkHardness::InitialPlacement> Initial;
    int32 Screen,Vision;
    EOriginalHardnessPhase Phase=EOriginalHardnessPhase::BaseMain;
    bool UnadmittedRead=false;
    FDinkHardnessProjection(DinkHardness::Layers InMap,DinkHardness::Layers::Pixels Base,int32 S)
        : Map(std::move(InMap)),TileBase(std::move(Base)),Screen(S),Vision(0) {}
};
struct FDinkRuntimeHardnessState
{
    DinkHardness::Session Session;
    TSharedPtr<DinkHardness::PhysicsOwner> Owner;
    bool Published=false;
    FDinkRuntimeHardnessState(DinkHardness::Session InSession,TSharedPtr<DinkHardness::PhysicsOwner> InOwner)
        : Session(std::move(InSession)),Owner(MoveTemp(InOwner)) {}
};

void UDinkGameplay::SetHardnessLoading(bool Loading)
{
    bHardnessLoading=Loading;
    APlayerController* PC=Story&&Story->GetWorld()?UGameplayStatics::GetPlayerController(Story->GetWorld(),0):nullptr;
    if(HardnessBlockedController.IsValid()&&(!Loading||HardnessBlockedController.Get()!=PC))
    {HardnessBlockedController->SetIgnoreMoveInput(false);HardnessBlockedController.Reset();}
    if(Loading&&PC&&!HardnessBlockedController.IsValid())
    {
        PC->SetIgnoreMoveInput(true);HardnessBlockedController=PC;
        if(APawn* Pawn=PC->GetPawn())if(auto* Movement=Pawn->GetMovementComponent())Movement->StopMovementImmediately();
    }
}

bool UDinkGameplay::BeginOriginalHardnessScreen(int32 Screen,FString& Error,int32 InitialVision)
{
    const auto Previous=HardnessProjection;
    HardnessProjection.Reset();
    auto* Provider=Story&&Story->GetWorld()?Story->GetWorld()->GetSubsystem<UDinkRuntimeHardnessWorldSubsystem>():nullptr;
    const bool Required=Provider&&Provider->RequiresScreenCapability(Screen);
    // Sidecars alone never opt a legacy generated world into a new birth order.
    if(DinkHardness::SelectActivation(Required,HasData())==DinkHardness::Activation::Legacy)
    {SetHardnessLoading(false);Error.Reset();return true;}
    SetHardnessLoading(true);
    auto Fail=[&](const TCHAR* Why){Error=Why;RefuseOriginalHardnessProjection();return false;};
    if(!HasData())return Fail(TEXT("marked hardness world has no gameplay data"));
    FDinkRuntimeHardnessSource Source;
    if(!FDinkRuntimeHardnessSource::Load(FDinkGameplayData::GetDataPath(*LayerFile(Screen,InitialVision)),InitialVision,Source,Error))return false;
    for(const auto* P:Data.GetPlacementsOnScreen(Screen))if(!P->bHasQueSource)return Fail(TEXT("marked hardness world lacks original que source"));
    auto Map=DinkHardness::Layers::Create(Source.TileBase,{});if(!Map)return Fail(TEXT("invalid tile-only hardness baseline"));
    auto New=MakeShared<FDinkHardnessProjection>(std::move(*Map),std::move(Source.TileBase),Screen);
    // Original kill_last_sprite preserves only live sprites (and Dink). UE
    // retained-script handles are not silently mistaken for original live slots.
    if(const auto* D=Director())for(const auto& Pair:D->GetSprites())
    {
        const auto& S=Pair.Value;if(S.Handle==1||!S.bActive)continue;
        const auto Old=Previous.IsValid()&&Previous->Slots.Valid()?Previous->Slots.Slot(S.Handle):std::nullopt;
        if(!S.GetProp(TEXT("live"))||!Old||!New->Slots.Preserve(S.Handle,*Old))New->Slots.Refuse();
    }
    New->Vision=InitialVision;
    HardnessProjection=MoveTemp(New);
    auto Owner=Provider->AcquireOrRearm(Screen,InitialVision,Error);
    if(!Owner.IsValid()||!AdmitRuntimeHardness(Screen,InitialVision,Owner,Error))
    {RefuseOriginalHardnessProjection();return false;}
    SetHardnessLoading(false);Error.Reset();return true;
}

bool UDinkGameplay::RequiresOriginalHardnessScreen(int32 Screen) const
{
    auto* Provider=Story&&Story->GetWorld()?Story->GetWorld()->GetSubsystem<UDinkRuntimeHardnessWorldSubsystem>():nullptr;
    return Provider&&Provider->RequiresScreenCapability(Screen);
}

void UDinkGameplay::ApplyOriginalHardnessVision(int32 Screen,int32 Vision,bool bBackgroundOnly)
{
    if(!Story||!Story->GetWorld()||!UsesOriginalHardnessProjection(Screen)||IsHardnessLoading())return;
    if(!bBackgroundOnly)
        if(auto* Greybox=Story->GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>())Greybox->SetScreenVision(Screen,Vision);
    for(TActorIterator<ADinkPlaceholderActor> It(Story->GetWorld());It;++It)
    {
        if(It->ScreenNumber!=Screen)continue;
        const auto* Placement=It->Origin?Data.FindPlacement(It->Origin->OriginId):nullptr;
        if(DinkHardness::ShouldApplyOriginalVision(bBackgroundOnly,Placement?EffectiveHardnessPlacementType(*Placement):-1))It->ApplyScreenVision(Vision);
    }
}

bool UDinkGameplay::UsesOriginalHardnessProjection(int32 Screen) const
{
    return HardnessProjection.IsValid()&&HardnessProjection->Screen==Screen&&
        HardnessProjection->Phase!=EOriginalHardnessPhase::Refused;
}

int32 UDinkGameplay::EffectiveHardnessPlacementType(const FDinkPlacementInfo& P) const
{
    const auto* W=Story?Story->GetWorldState():nullptr;
    return DinkHardness::ProjectEditorFields(P.Type,P.Hard,P.Seq,P.Frame,
        W?static_cast<int>(W->GetOverrideType(P.Origin)):0,0,0).Type;
}
int32 UDinkGameplay::EffectiveHardnessFlag(const FDinkPlacementInfo& P) const
{
    const auto* Edit=EditorHardness.Find(P.Origin);const auto* W=Story?Story->GetWorldState():nullptr;
    return DinkHardness::ProjectEditorFields(P.Type,P.Hard,P.Seq,P.Frame,
        W?static_cast<int>(W->GetOverrideType(P.Origin)):0,0,0,
        Edit&&Edit->bHardSet?std::optional<int>(Edit->Hard):std::nullopt).Hard;
}
void UDinkGameplay::EffectiveHardnessPicture(const FDinkPlacementInfo& P,int32& Seq,int32& Frame) const
{
    const auto* W=Story?Story->GetWorldState():nullptr;const auto* Edit=EditorHardness.Find(P.Origin);
    const auto Result=DinkHardness::ProjectEditorFields(P.Type,P.Hard,P.Seq,P.Frame,
        W?static_cast<int>(W->GetOverrideType(P.Origin)):0,Edit?Edit->Seq:0,Edit?Edit->Frame:0);
    Seq=Result.Seq;Frame=Result.Frame;
}

bool UDinkGameplay::PrepareOriginalHardnessPlacements(int32 Screen,FString& Error)
{
    if(!UsesOriginalHardnessProjection(Screen))return false;
    auto& P=*HardnessProjection;
    auto Fail=[&](const TCHAR* Why){RefuseOriginalHardnessProjection();Error=Why;return false;};
    if(P.Phase!=EOriginalHardnessPhase::BaseMain||!P.Slots.Valid())return Fail(TEXT("original screen birth phase unavailable"));
    const int32 Vision=Story&&Story->GetFacts()?Story->GetFacts()->GetFact(TEXT("vision")):0;
    FDinkRuntimeHardnessSource Source;
    if(!FDinkRuntimeHardnessSource::Load(FDinkGameplayData::GetDataPath(*LayerFile(Screen,Vision)),Vision,Source,Error)||Source.TileBase!=P.TileBase)
        return Fail(TEXT("selected vision tile base differs or is unsupported"));
    P.Vision=Vision;
    const auto* World=Story?Story->GetWorldState():nullptr;
    std::vector<DinkHardness::InitialPlacement> Rows;
    for(const auto* Placement:Data.GetPlacementsOnScreen(Screen))
        if(!World||!World->IsPlacementRemoved(Placement->Origin))Rows.push_back({Placement->Origin.Placement,
            EffectiveHardnessPlacementType(*Placement),Placement->Y,Placement->Que,Placement->Vision});
    auto Ordered=DinkHardness::MixedInitialOrder(std::move(Rows),Vision);
    if(!Ordered)return Fail(TEXT("invalid original initial placement order"));
    std::vector<DinkHardness::Stamp> Stamps;
    for(const auto& Row:*Ordered)
    {
        if(Row.Type==1 ? !P.Slots.ReserveEditor(Row.Owner) : !P.Slots.Scratch())return Fail(TEXT("original sprite slots exhausted"));
        const auto* Placement=Data.FindPlacement(FDinkOriginId(Screen,Row.Owner));
        if(!Placement)return Fail(TEXT("initial placement source missing"));
        if(EffectiveHardnessFlag(*Placement)!=0)continue;
        int32 Seq=0,Frame=0;EffectiveHardnessPicture(*Placement,Seq,Frame);
        FDinkSprite Initial;Initial.X=Placement->X;Initial.Y=Placement->Y;
        Initial.Props.Add(TEXT("pseq"),Seq);Initial.Props.Add(TEXT("pframe"),Frame);
        int32 L=0,T=0,R=0,B=0;if(!GetDisplayedHardnessBox(Initial,L,T,R,B))return Fail(TEXT("initial displayed picture missing"));
        Stamps.push_back({{L,T,R,B},static_cast<std::uint8_t>(100+Row.Owner)});
    }
    auto Next=P.Map;if(!Next.Redraw({0,0,0,0},Stamps))return Fail(TEXT("invalid initial mixed stamps"));
    P.Initial=std::move(*Ordered); // all allocations precede any scene publication
    struct Publish {FDinkHardnessProjection* Target;DinkHardness::Layers* Next;};
    Publish Context{&P,&Next};
    auto Apply=[](void* Raw) noexcept {auto& C=*static_cast<Publish*>(Raw);C.Target->Map=std::move(*C.Next);C.Target->Phase=EOriginalHardnessPhase::InitialPlacements;};
    const auto* Runtime=RuntimeHardness.Find(RuntimeHardnessKey(Screen,Vision));
    if(Runtime&&Runtime->IsValid()&&(*Runtime)->Published)
    {
        if(!(*Runtime)->Session.Redraw({0,0,0,0},Stamps,*(*Runtime)->Owner,&Context,Apply))return Fail(TEXT("initial physical projection refused"));
    }
    else return Fail(TEXT("initial placement physical owner not admitted"));
    Error.Reset();return true;
}

TArray<int32> UDinkGameplay::OriginalHardnessPlacementOrder(int32 Screen) const
{
    TArray<int32> Out;
    if(UsesOriginalHardnessProjection(Screen))for(const auto& P:HardnessProjection->Initial)if(P.Type==1)Out.Add(P.Owner);
    return Out;
}
void UDinkGameplay::BindOriginalHardnessPlacement(const FDinkOriginId& Origin,int32 Handle)
{
    if(!UsesOriginalHardnessProjection(Origin.Screen))return;
    auto& P=*HardnessProjection;
    if(P.Phase!=EOriginalHardnessPhase::InitialPlacements||!P.Slots.BindEditor(Origin.Placement,Handle))
    {RefuseOriginalHardnessProjection();return;}
    // update_play_changes has already selected the persisted numeric picture.
    if(auto* S=Director()?Director()->FindSprite(Handle):nullptr)
    {
        const auto* Source=Data.FindPlacement(Origin);
        if(!Source){RefuseOriginalHardnessProjection();return;}
        int32 Seq=0,Frame=0;EffectiveHardnessPicture(*Source,Seq,Frame);
        S->Props.Add(TEXT("pseq"),Seq);S->Props.Add(TEXT("pframe"),Frame);
        S->Props.Add(TEXT("hard"),EffectiveHardnessFlag(*Source));S->Props.Add(TEXT("que"),Source->Que);
        const auto* W=Story?Story->GetWorldState():nullptr;
        if(W&&W->GetOverrideType(Origin)!=EDinkOverrideType::None)S->Script=NAME_None;
    }
}
bool UDinkGameplay::FinishOriginalHardnessPlacements(int32 Screen,FString& Error)
{
    if(!UsesOriginalHardnessProjection(Screen)||HardnessProjection->Phase!=EOriginalHardnessPhase::InitialPlacements||
        !HardnessProjection->Slots.Valid()||!HardnessProjection->Slots.Bound())
    {RefuseOriginalHardnessProjection();Error=TEXT("initial original slot bindings incomplete");return false;}
    HardnessProjection->Phase=EOriginalHardnessPhase::Live;
    ApplyOriginalHardnessVision(Screen,HardnessProjection->Vision,false);
    Error.Reset();return true;
}

void UDinkGameplay::RecordOriginalHardnessBirth(int32 Handle)
{
    if(!HardnessProjection.IsValid())return;
    const auto* S=Director()?Director()->FindSprite(Handle):nullptr;
    if(S&&(S->Screen==HardnessProjection->Screen||S->bText)&&HardnessProjection->Phase!=EOriginalHardnessPhase::Refused)
        if(!HardnessProjection->Slots.Birth(Handle))RefuseOriginalHardnessProjection();
}
void UDinkGameplay::RecordOriginalHardnessRelease(int32 Handle)
{if(HardnessProjection.IsValid())HardnessProjection->Slots.Release(Handle);}
void UDinkGameplay::RecordOriginalHardnessReactivation(int32 Handle)
{if(HardnessProjection.IsValid()&&!HardnessProjection->Slots.Reactivate(Handle))RefuseOriginalHardnessProjection();}
void UDinkGameplay::OriginalHardnessVisionChanged(int32 Vision)
{
    if(!HardnessProjection.IsValid()||HardnessProjection->Vision==Vision)return;
    if(DinkHardness::SelectVisionTransition(HardnessProjection->Phase==EOriginalHardnessPhase::BaseMain,false)==DinkHardness::VisionTransition::RebindBase)
    {
        // Ordinary base-main &vision chooses the upcoming placement pass; keep
        // its tile/draw journal, but never keep publishing an old-vision owner.
        for(auto& Pair:HardnessOwners)if(Pair.Value.IsValid())Pair.Value->InvalidateForScreenRebuild();
        SetHardnessLoading(true);RuntimeHardness.Reset();
        auto* Provider=Story&&Story->GetWorld()?Story->GetWorld()->GetSubsystem<UDinkRuntimeHardnessWorldSubsystem>():nullptr;
        FString Error;FDinkRuntimeHardnessSource Source;
        if(!Provider||!FDinkRuntimeHardnessSource::Load(FDinkGameplayData::GetDataPath(*LayerFile(HardnessProjection->Screen,Vision)),Vision,Source,Error)||
            Source.TileBase!=HardnessProjection->TileBase)
        {RefuseOriginalHardnessProjection();return;}
        HardnessProjection->Vision=Vision;
        auto Owner=Provider->AcquireOrRearm(HardnessProjection->Screen,Vision,Error);
        if(!Owner.IsValid()||!AdmitRuntimeHardness(HardnessProjection->Screen,Vision,Owner,Error))
        {RefuseOriginalHardnessProjection();return;}
        SetHardnessLoading(false);return;
    }
    // Ordinary live &vision assignment is lazy in the original engine. It
    // changes filtering for a future draw/rebuild, not the published hit map.
    // force_vision has an explicit full-screen coordinator in Story instead.
}

bool UDinkGameplay::AdmitRuntimeHardness(int32 Screen,int32 Vision,
                                        TSharedPtr<DinkHardness::PhysicsOwner> Owner,FString& Error)
{
    auto Fail=[&](const TCHAR* Why){Error=Why;return false;};
    if(!Owner.IsValid()||Owner->Version()!=1||!Owner->HasAdmittedBaseline()||Owner->IsAuthoredScreen()||
        Owner->GetScreen()!=Screen||Owner->GetVision()!=Vision||!Story||!Story->GetWorld()||
        Owner->GetWorldCookie()!=reinterpret_cast<std::uintptr_t>(Story->GetWorld()))return Fail(TEXT("staged owner-separated capability required"));
    if(!UsesOriginalHardnessProjection(Screen)||HardnessProjection->Vision!=Vision||
        !HardnessProjection->Slots.Valid()||!HardnessProjection->Slots.Bound()||HardnessProjection->UnadmittedRead)
        return Fail(TEXT("complete original phase/slots/projection required before publication; rebuild under loading gate"));
    if(HardnessProjection->Phase==EOriginalHardnessPhase::InitialPlacements)return Fail(TEXT("initial slot binding in progress"));
    FDinkRuntimeHardnessSource Selected;
    if(!FDinkRuntimeHardnessSource::Load(FDinkGameplayData::GetDataPath(*LayerFile(Screen,Vision)),Vision,Selected,Error)||
        Selected.TileBase!=HardnessProjection->TileBase)return Fail(TEXT("selected source tile baseline unavailable/drifted"));
    const int64 Key=RuntimeHardnessKey(Screen,Vision);
    if(RuntimeHardness.Contains(Key))return Fail(TEXT("screen/vision already admitted"));
    if(const auto* Old=HardnessOwners.Find(Screen);Old&&*Old!=Owner)return Fail(TEXT("another retained body owner exists"));
    auto New=DinkHardness::Session::CreateProjected(HardnessProjection->Map,Screen,Vision);
    if(!New)return Fail(TEXT("projected session invalid"));
    auto Candidate=MakeShared<FDinkRuntimeHardnessState>(std::move(*New),Owner);
    RuntimeHardness.Reserve(RuntimeHardness.Num()+1);HardnessOwners.Reserve(HardnessOwners.Num()+1);
    RuntimeHardness.Add(Key,Candidate); // invisible until allocation-free scene callback
    if(!Candidate->Session.Redraw({0,0,0,0},{},*Owner,Candidate.Get(),[](void* Raw) noexcept {
        static_cast<FDinkRuntimeHardnessState*>(Raw)->Published=true;
    }))
    {RuntimeHardness.Remove(Key);return Fail(TEXT("initial physical projection refused"));}
    HardnessOwners.Add(Screen,Owner);Error.Reset();return true;
}

void UDinkGameplay::RecordEditorHardness(const FDinkOriginId& Origin, int32 Value)
{
    if (Origin.IsValid() && Origin.Placement<=99)
    {
        auto& State = EditorHardness.FindOrAdd(Origin);
        State.Hard = Value;
        State.bHardSet = true;
    }
}

int32 UDinkGameplay::EditorHardnessPicture(const FDinkOriginId& Origin, bool bSequence, int32 Value)
{
    if (!Origin.IsValid() || Origin.Placement>99) return -1;
    if (Value == -1)
    {
        const auto* State = EditorHardness.Find(Origin);
        int32 Stored = State ? (bSequence ? State->Seq : State->Frame) : 0;
        return DinkHardness::ChangeEditorPicture(Origin.Placement, bSequence, Value, Stored);
    }
    auto& State = EditorHardness.FindOrAdd(Origin);
    int32& Field = bSequence ? State.Seq : State.Frame;
    return DinkHardness::ChangeEditorPicture(Origin.Placement, bSequence, Value, Field);
}

bool UDinkGameplay::TryRuntimeHardnessCode(int32 Screen,int32 Vision,int32 X,int32 Y,int32& Code) const
{
    // The displayed/admitted epoch is independent of a later lazy fact write.
    const int32 AdmittedVision=UsesOriginalHardnessProjection(Screen)?HardnessProjection->Vision:Vision;
    const auto* State=RuntimeHardness.Find(RuntimeHardnessKey(Screen,AdmittedVision));
    if(!State||!State->IsValid()||!(*State)->Published)
    {
        if(UsesOriginalHardnessProjection(Screen))
        {HardnessProjection->UnadmittedRead=true;const_cast<UDinkGameplay*>(this)->RefuseOriginalHardnessProjection();}
        return false;
    }
    if(!UsesOriginalHardnessProjection(Screen)||
        !HardnessProjection->Slots.Valid()||!(*State)->Owner.IsValid()||!(*State)->Owner->HasAdmittedBaseline()||(*State)->Owner->GetVision()!=AdmittedVision||
        (*State)->Owner->GetWorldCookie()!=reinterpret_cast<std::uintptr_t>(Story?Story->GetWorld():nullptr))
    {const_cast<UDinkGameplay*>(this)->RefuseOriginalHardnessProjection();return false;}
    Code=(*State)->Session.Get(X,Y);return true;
}

bool UDinkGameplay::BuildHardnessDrawStamps(int32 Screen,int32 Vision,
    std::vector<DinkHardness::Stamp>& Out,FString& Error) const
{
    auto Fail=[&](const TCHAR* Why){Error=Why;return false;};
    if(!UsesOriginalHardnessProjection(Screen)||!HardnessProjection->Slots.Valid())return Fail(TEXT("original slot projection unavailable"));
    const auto* D=Director();if(!D)return Fail(TEXT("director unavailable"));
    const auto* World=Story?Story->GetWorldState():nullptr;
    std::vector<DinkHardness::SpriteState> Background,Live;
    for(const auto* P:Data.GetPlacementsOnScreen(Screen))
    {
        if((P->Vision!=0&&P->Vision!=Vision)||EffectiveHardnessPlacementType(*P)==1||
            (World&&World->IsPlacementRemoved(P->Origin))||EffectiveHardnessFlag(*P)!=0)continue;
        int32 Seq=0,Frame=0;EffectiveHardnessPicture(*P,Seq,Frame);
        FDinkSprite S;S.X=P->X;S.Y=P->Y;S.Props.Add(TEXT("pseq"),Seq);S.Props.Add(TEXT("pframe"),Frame);
        int32 L=0,T=0,R=0,B=0;if(!GetDisplayedHardnessBox(S,L,T,R,B))return Fail(TEXT("background displayed picture missing"));
        Background.push_back({P->Origin.Placement,P->Origin.Placement,P->Y,P->Que,0,true,{L,T,R,B}});
    }
    for(const auto& Pair:D->GetSprites())
    {
        const auto& S=Pair.Value;if(!S.bActive||S.bText||S.Screen!=Screen)continue;
        const auto Slot=HardnessProjection->Slots.Slot(S.Handle);
        // Unborn/initial-background placement bindings are cached UE references,
        // not active original sprites. They must not enter fill_hard_sprites.
        if(S.Origin.IsValid()&&!Slot)continue;
        int Hard=S.GetProp(TEXT("hard"),1),Owner=0;
        if(S.Origin.IsValid())
        {
            const auto* P=Data.FindPlacement(S.Origin);if(!P)return Fail(TEXT("live editor source missing"));
            Hard=EffectiveHardnessFlag(*P);Owner=P->Origin.Placement;
        }
        if(Hard!=0)continue;
        if(!Slot)return Fail(TEXT("active dynamic sprite has no original birth identity"));
        int32 L=0,T=0,R=0,B=0;if(!GetDisplayedHardnessBox(S,L,T,R,B))return Fail(TEXT("live displayed picture missing"));
        Live.push_back({*Slot,Owner,FMath::RoundToInt32(S.Y),S.GetProp(TEXT("que")),Hard,true,{L,T,R,B}});
    }
    auto Ordered=DinkHardness::OrderedStamps(std::move(Background),std::move(Live));
    if(!Ordered)return Fail(TEXT("invalid original redraw order"));Out=std::move(*Ordered);return true;
}

bool UDinkGameplay::RedrawRuntimeHardness(int32 Handle,FString& Error)
{
    auto Fail=[&](const TCHAR* Why){Error=Why;return false;};
    const auto* D=Director();const auto* Target=D?D->FindSprite(Handle):nullptr;
    if(!Target)return Fail(TEXT("draw_hard_sprite target missing"));
    const int32 Vision=Story&&Story->GetFacts()?Story->GetFacts()->GetFact(TEXT("vision")):0;
    if(!UsesOriginalHardnessProjection(Target->Screen))
        return Fail(TEXT("layered source/original phase unavailable; legacy collision unchanged"));
    int32 L=0,T=0,R=0,B=0;if(!GetDisplayedHardnessBox(*Target,L,T,R,B))return Fail(TEXT("displayed clear picture source missing"));
    std::vector<DinkHardness::Stamp> Ordered;
    if(!BuildHardnessDrawStamps(Target->Screen,Vision,Ordered,Error))return false;
    auto Next=HardnessProjection->Map;
    const DinkHardness::Rect Clear{L,T,R,B};if(!Next.Redraw(Clear,Ordered))return Fail(TEXT("logical redraw refused"));
    const auto* State=RuntimeHardness.Find(RuntimeHardnessKey(Target->Screen,HardnessProjection->Vision));
    if(!State||!State->IsValid()||!(*State)->Published)
    {
        RefuseOriginalHardnessProjection();
        return Fail(TEXT("physical owner not admitted; redraw not published"));
    }
    auto& Runtime=**State;
    if(!Runtime.Owner.IsValid()||Runtime.Owner->GetWorldCookie()!=reinterpret_cast<std::uintptr_t>(Story?Story->GetWorld():nullptr))
        return Fail(TEXT("physical world capability expired"));
    struct Publish{FDinkHardnessProjection* Target;DinkHardness::Layers* Next;};
    Publish Context{HardnessProjection.Get(),&Next};
    if(!Runtime.Session.Redraw(Clear,Ordered,*Runtime.Owner,&Context,[](void* Raw)noexcept{
        auto& C=*static_cast<Publish*>(Raw);C.Target->Map=std::move(*C.Next);
    }))return Fail(TEXT("physical redraw refused; map/journal unchanged"));
    // fill_back_sprites redraws the current background vision. It does not
    // delete/recreate previously born live sprites after a lazy fact write.
    ApplyOriginalHardnessVision(Target->Screen,Vision,true);
    Error.Reset();return true;
}

void UDinkGameplay::RefuseOriginalHardnessProjection()
{
    for(auto& Pair:HardnessOwners)if(Pair.Value.IsValid())Pair.Value->InvalidateForScreenRebuild();
    RuntimeHardness.Reset();
    if(HardnessProjection.IsValid())
    {HardnessProjection->Phase=EOriginalHardnessPhase::Refused;SetHardnessLoading(true);}
}
void UDinkGameplay::InvalidateRuntimeHardnessForScreenLoad(bool bResetTransientEditorHard)
{
    RefuseOriginalHardnessProjection();
    if(bResetTransientEditorHard)for(auto& Pair:EditorHardness)Pair.Value.bHardSet=false;
    // Owner registry deliberately retains registered bodies. The world provider
    // must hold its loading gate until a complete new phase is re-admitted.
}

void UDinkGameplay::RestartOriginalSavedRuntime()
{
    // Original saves playerInfo/editor pictures, not runtime script IDs,
    // projectiles, bow state or the prior hit map. Keep only numeric pictures.
    auto Pictures=MoveTemp(EditorHardness);
    Reset();
    EditorHardness=MoveTemp(Pictures);
    for(auto& Pair:EditorHardness)Pair.Value.bHardSet=false;
}

void UDinkGameplay::SaveEditorPictures(TSharedRef<FJsonObject> State) const
{
    TArray<FDinkOriginId> Keys;
    EditorHardness.GetKeys(Keys); Keys.Sort();
    TArray<TSharedPtr<FJsonValue>> Pictures;
    for (const auto& Key : Keys)
    {
        const auto& Picture = EditorHardness[Key];
        TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
        O->SetStringField(TEXT("origin"), Key.ToString());
        O->SetNumberField(TEXT("seq"), Picture.Seq);
        O->SetNumberField(TEXT("frame"), Picture.Frame);
        Pictures.Add(MakeShared<FJsonValueObject>(O));
    }
    State->SetArrayField(TEXT("hardnessEditorPicturesV1"), Pictures);
    // Deliberately no hit map, runtime hard flags, physics objects or residual pixels.
}

void UDinkGameplay::LoadEditorPictures(const TSharedPtr<FJsonObject>& State)
{
    const TArray<TSharedPtr<FJsonValue>>* Pictures = nullptr;
    if (!State->TryGetArrayField(TEXT("hardnessEditorPicturesV1"), Pictures)) return; // older saves: zero defaults
    for (const auto& Value : *Pictures)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) continue;
        const auto O = Value->AsObject();
        FString OriginText; FDinkOriginId Origin;
        double Seq = 0, Frame = 0;
        if (!O->TryGetStringField(TEXT("origin"), OriginText) || !FDinkOriginId::Parse(OriginText, Origin) ||
            !O->TryGetNumberField(TEXT("seq"), Seq) || !FMath::IsFinite(Seq) || Seq < 0 || Seq > 65535 || FMath::FloorToDouble(Seq) != Seq ||
            !O->TryGetNumberField(TEXT("frame"), Frame) || !FMath::IsFinite(Frame) || Frame < 0 || Frame > 255 || FMath::FloorToDouble(Frame) != Frame)
            continue;
        auto& Picture = EditorHardness.FindOrAdd(Origin);
        Picture.Seq = static_cast<int32>(Seq);
        Picture.Frame = static_cast<int32>(Frame);
        // Load never restores transient bHardSet or a previous hit map.
    }
}

bool UDinkGameplay::GetDisplayedHardnessBox(const FDinkSprite& Sprite, int32& L, int32& T, int32& R, int32& B) const
{
    auto Bounds = DinkHardness::DisplayedBounds(Sprite.GetProp(TEXT("pseq")), Sprite.GetProp(TEXT("pframe")),
        FMath::RoundToInt32(Sprite.X), FMath::RoundToInt32(Sprite.Y), [this](int Seq, int Frame) -> std::optional<DinkHardness::Rect> {
            const FDinkFrameInfo* F = Data.FindFrame(Seq, Frame);
            if (!F) return std::nullopt;
            return DinkHardness::Rect{F->Left,F->Top,F->Right,F->Bottom};
        });
    if (!Bounds) return false;
    L=Bounds->Left; T=Bounds->Top; R=Bounds->Right; B=Bounds->Bottom;
    return true;
}
