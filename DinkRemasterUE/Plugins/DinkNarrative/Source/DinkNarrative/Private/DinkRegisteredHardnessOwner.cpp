#include "Hardness/DinkRegisteredHardnessOwner.h"
#include "DinkArtFamilySubsystem.h"
#include "Hardness/DinkFamilyCollisionFit.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Hardness/DinkHardnessPrismComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/CollisionProfile.h"
#include "DinkCollision.h"
#include "EngineUtils.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "Physics/PhysScene.h"
#include "Physics/Experimental/PhysScene_Chaos.h"
#include "PhysicsEngine/BodySetup.h"
#include "UObject/StrongObjectPtr.h"

namespace
{
bool IsPolicyReference(const UPrimitiveComponent* C,FName Profile,ECollisionChannel Channel,UWorld* World)
{
    FCollisionResponseTemplate Template;
    return C && C->GetWorld()==World && C->Mobility==EComponentMobility::Static &&
        UCollisionProfile::Get()->GetProfileTemplate(Profile,Template) && Template.ObjectType==Channel &&
        C->GetCollisionProfileName()==Profile && C->GetCollisionObjectType()==Channel &&
        C->GetCollisionEnabled()==ECollisionEnabled::QueryAndPhysics && !C->GetGenerateOverlapEvents() &&
        C->GetCollisionResponseToChannels()==Template.ResponseToChannels &&
        C->GetBodyInstance() && !C->GetBodyInstance()->bSimulatePhysics;
}
bool IsFoundationMesh(const UStaticMeshComponent* C, const TCHAR* Tag, const TCHAR* Suffix)
{
    return C && C->GetStaticMesh() && C->ComponentHasTag(Tag) &&
        C->GetStaticMesh()->GetPathName().Contains(TEXT("/RuntimeHardnessV1/")) &&
        C->GetStaticMesh()->GetName().EndsWith(Suffix);
}
struct FPolicy
{
    TWeakObjectPtr<UPrimitiveComponent> Component;
    FName Profile;
    ECollisionChannel ObjectType;
    ECollisionEnabled::Type Enabled;
    FCollisionResponseContainer Responses;
    bool Navigation, Overlaps;
    FTransform Transform;
    explicit FPolicy(UPrimitiveComponent& C) : Component(&C), Profile(C.GetCollisionProfileName()),
        ObjectType(C.GetCollisionObjectType()), Enabled(C.GetCollisionEnabled()), Responses(C.GetCollisionResponseToChannels()),
        Navigation(C.CanEverAffectNavigation()), Overlaps(C.GetGenerateOverlapEvents()), Transform(C.GetComponentTransform()) {}
    bool Unchanged() const
    {
        const auto* C = Component.Get();
        return C && C->GetCollisionProfileName() == Profile && C->GetCollisionObjectType() == ObjectType &&
            C->GetCollisionEnabled() == Enabled && C->GetCollisionResponseToChannels() == Responses &&
            C->CanEverAffectNavigation() == Navigation && C->GetGenerateOverlapEvents() == Overlaps &&
            C->GetComponentTransform().Equals(Transform, 0);
    }
    bool Matches(const UPrimitiveComponent& C, bool Staging) const
    {
        return C.GetCollisionProfileName() == Profile && C.GetCollisionObjectType() == ObjectType &&
            C.GetCollisionEnabled() == Enabled && C.GetCollisionResponseToChannels() == Responses &&
            C.GetGenerateOverlapEvents() == Overlaps &&
            (Staging ? !C.CanEverAffectNavigation() : C.CanEverAffectNavigation() == Navigation);
    }
};
const void* NativeOwnerTag(){static const int Tag=0;return &Tag;}
const void* NativeFitTag(){static const int Tag=0;return &Tag;}
class FNativeFit final : public DinkHardness::FittedGeometry
{
public:
    const FDinkFamilyCollisionFitCandidate Candidate;
    const TWeakObjectPtr<UDinkArtFamilySubsystem> Families;
    const void* const Implicit;
    FNativeFit(const FDinkFamilyCollisionFitCandidate& C,UDinkArtFamilySubsystem& F)
        :Candidate(C),Families(&F),Implicit(C.Geometry.BodySetup->TriMeshGeometries[0].GetReference()){}
    const void* BackendTag() const noexcept override{return NativeFitTag();}
    bool Current() const noexcept override
    {
        if(!Families.IsValid() || !Candidate.Geometry.BodySetup.IsValid())return false;
        const auto* B=Candidate.Geometry.BodySetup.Get();
        if(B->TriMeshGeometries.Num()!=1 || B->TriMeshGeometries[0].GetReference()!=Implicit)return false;
        FString Error;auto C=Candidate;
        if(Families->ValidateCollisionFit(C,C.Sprite,Error))return true;
        C.bVisualApplied=!C.bVisualApplied;
        return Families->ValidateCollisionFit(C,C.Sprite,Error);
    }
};
struct FRegisteredShape
{
    FBodyInstance* Body;
    FPhysicsActorHandle Actor;
    FPhysicsShapeHandle Shape;
    int32 Index;
    bool ActiveWhenAdmitted;
};
struct FBodySet
{
    TArray<TStrongObjectPtr<UDinkHardnessPrismComponent>> Components;
    TArray<FRegisteredShape> Shapes;
    TMap<std::uintptr_t,TWeakObjectPtr<UDinkHardnessPrismComponent>> Fitted;
    TSet<UDinkHardnessPrismComponent*> SuppressedComponents;
    std::vector<DinkHardness::FittedOwner> Fits;
    bool FitsCurrent() const
    {
        for(const auto& F:Fits)
        {
            if(!F.Geometry || F.Geometry->BackendTag()!=NativeFitTag() || !F.Geometry->Current())return false;
            const auto& G=static_cast<const FNativeFit&>(*F.Geometry);
            const auto* Found=Fitted.Find(F.InstanceId);auto* C=Found?Found->Get():nullptr;
            const auto* B=C?C->GetBodySetup():nullptr;
            if(!C || !B || B->TriMeshGeometries.Num()!=1 || !C->ValidateCookedMeshGeometry(*G.Candidate.Geometry.BodySetup.Get()) ||
               !C->GetComponentTransform().Equals(G.Candidate.ProposedWorld,1.e-4))return false;
        }
        return true;
    }

    ~FBodySet()
    {
        // Always outside the scene exchange; only this set's owned transient
        // components are retired. Never destroy a control/legacy component.
        for (auto& C : Components) if (IsValid(C.Get())) C->DestroyComponent();
    }
    bool StillRegistered() const
    {
        for (const auto& C : Components)
            if (!IsValid(C.Get()) || !C->IsRegistered() || !C->IsPhysicsStateCreated()) return false;
        for (const auto& S : Shapes)
            if (!S.Body->IsValidBodyInstance() || S.Body->GetPhysicsActorHandle() != S.Actor || !S.Shape.IsValid()) return false;
        return true;
    }
    void SetFlags(bool Active) const
    {
        for (const auto& S : Shapes)
        {
            FPhysicsInterface::SetIsQueryShape(S.Shape, Active && S.ActiveWhenAdmitted);
            FPhysicsInterface::SetIsSimulationShape(S.Shape, Active && S.ActiveWhenAdmitted);
        }
    }
    bool HasFlags(bool Active) const
    {
        for (const auto& S : Shapes)
            if (FPhysicsInterface::IsQueryShape(S.Shape) != (Active && S.ActiveWhenAdmitted) || FPhysicsInterface::IsSimulationShape(S.Shape) != (Active && S.ActiveWhenAdmitted)) return false;
        return true;
    }
    void RefreshAcceleration(FPhysScene& Scene) const
    {
        for (const auto& C : Components) Scene.UpdateActorInAccelerationStructure(C->BodyInstance.GetPhysicsActorHandle());
    }
    void SetNavigation(bool Active) const
    {
        for (const auto& C : Components) C->SetCanEverAffectNavigation(Active && !SuppressedComponents.Contains(C.Get()) && C->DesiredNavigation());
    }
};
}

struct FDinkRegisteredHardnessOwner::FImpl
{
    FDinkHardnessWorldDefinition Definition;
    TWeakObjectPtr<UWorld> World;
    FTransform HostTransform;
    FDinkScreenCorners Corners;
    TArray<FPolicy> Policies;
    TSharedPtr<FBodySet> Active = MakeShared<FBodySet>();
    bool Admitted = false, Preparing = false;
    explicit FImpl(FDinkHardnessWorldDefinition D) : Definition(MoveTemp(D)) {}
    bool FastValid() const
    {
        const auto* H = Definition.Host.Get(); const auto* S = Definition.Screen.Get();
        if (!H || !S || !World.IsValid() || H->GetWorld() != World.Get() || S->GetWorld() != World.Get() ||
            !H->GetActorTransform().Equals(HostTransform, 0) || !(S->Corners == Corners)) return false;
        for (const auto& P : Policies) if (!P.Unchanged()) return false;
        return true;
    }
    bool ValidateFoundation(FString& Error)
    {
        if (!FastValid() || !Definition.IsAuthoredCollisionScreen || Definition.IsAuthoredCollisionScreen())
        { Error = TEXT("authored/changed/expired world cannot admit legacy hardness proxies"); return false; }
        // A disabled old mesh is still an old mesh. New staged generations need
        // explicitly identified floor/fill components, never an aggregate toggle.
        for (TActorIterator<ADinkGreyboxScreen> It(World.Get()); It; ++It)
            if (It->ScreenNumber == Definition.Screen->ScreenNumber)
            {
                if ((It->CollisionSolid && It->CollisionSolid->GetStaticMesh() &&
                     !IsFoundationMesh(It->CollisionSolid, TEXT("DinkHardnessFixedFloorFillV1"), TEXT("_FixedSolidV1"))) ||
                    (It->CollisionLow && It->CollisionLow->GetStaticMesh() &&
                     !IsFoundationMesh(It->CollisionLow, TEXT("DinkHardnessFixedWaterV1"), TEXT("_FixedLowV1"))))
                { Error = TEXT("legacy aggregate mesh remains; new staged generation required"); return false; }
            }
        if (!Definition.VerifyImmutableFoundation || !Definition.VerifyImmutableFoundation(Error)) return false;
        return true;
    }
    struct FPrepared final : DinkHardness::PreparedPhysics
    {
        TSharedPtr<FDinkRegisteredHardnessOwner> Owner;
        TSharedPtr<FBodySet> Old, Next;
        bool Committed = false;
        FPrepared(TSharedPtr<FDinkRegisteredHardnessOwner> O, TSharedPtr<FBodySet> N)
            : Owner(MoveTemp(O)), Old(Owner->Impl->Active), Next(MoveTemp(N)) {}
        ~FPrepared() override { Owner->Impl->Preparing = false; }
        bool Commit(void* Context, PublishFn Publish) noexcept override
        {
            auto& I = *Owner->Impl;
            if (Committed || !IsInGameThread() || !I.Admitted || !I.FastValid() ||
                !Old->StillRegistered() || !Next->StillRegistered() || !Next->FitsCurrent() || !Publish) return false;
            FPhysScene* Scene = I.World->GetPhysicsScene();
            bool Published = false;
            const bool Acquired = FPhysicsCommand::ExecuteWrite(Scene, [&]() {
                if (!I.FastValid() || !Old->StillRegistered() || !Next->StillRegistered() ||
                    !Old->HasFlags(true) || !Next->HasFlags(false) || !Next->FitsCurrent()) return;
                Old->SetFlags(false); Next->SetFlags(true);
                Old->RefreshAcceleration(*Scene); Next->RefreshAcceleration(*Scene);
                if (!Next->HasFlags(true) || !Old->HasFlags(false))
                {
                    Next->SetFlags(false); Old->SetFlags(true);
                    Next->RefreshAcceleration(*Scene); Old->RefreshAcceleration(*Scene);
                    return;
                }
                I.Active = Next; // Old remains strongly retained by this transaction
                Publish(Context); // logical/session/adapter publication INSIDE scene write
                Published = true;
            });
            Committed = Acquired && Published;
            if (Committed)
            {
                // Standard asynchronous UE nav updates, separate from physical
                // scene atomicity. Eventual nav behavior needs actual validation.
                Old->SetNavigation(false); Next->SetNavigation(true);
            }
            return Committed;
        }
    };
};

FDinkRegisteredHardnessOwner::FDinkRegisteredHardnessOwner(FDinkHardnessWorldDefinition D)
    : Impl(MakeUnique<FImpl>(MoveTemp(D))) {}
FDinkRegisteredHardnessOwner::~FDinkRegisteredHardnessOwner() = default;

TSharedPtr<FDinkRegisteredHardnessOwner> FDinkRegisteredHardnessOwner::Create(FDinkHardnessWorldDefinition D, FString& Error)
{
    if (!IsInGameThread() || !D.Host.IsValid() || !D.Screen.IsValid() || !D.Host->GetRootComponent() ||
        D.Host->GetRootComponent()->Mobility != EComponentMobility::Static ||
        !D.Host->GetActorTransform().GetScale3D().Equals(FVector::OneVector, 0) ||
        !D.Host->GetActorTransform().GetRotation().Equals(FQuat::Identity, 0) ||
        !D.Host->ActorHasTag(TEXT("DinkHardnessWorldV1")) || !D.SolidPolicy.IsValid() || !D.LowPolicy.IsValid() ||
        D.ImmutableFloorFill.IsEmpty() || !FMath::IsFinite(D.HeightCm) || D.HeightCm <= 0)
    { Error = TEXT("explicit staged world definition and immutable floor/fill required"); return nullptr; }
    if (!IsPolicyReference(D.SolidPolicy.Get(),DinkCollision::ProfileHardSolid,DinkCollision::HardSolid,D.Host->GetWorld()) ||
        !IsPolicyReference(D.LowPolicy.Get(),DinkCollision::ProfileHardLow,DinkCollision::HardLow,D.Host->GetWorld()))
    { Error=TEXT("exact solid/low profile/object/all-channel policy references required"); return nullptr; }
    auto Result = TSharedPtr<FDinkRegisteredHardnessOwner>(new FDinkRegisteredHardnessOwner(MoveTemp(D)));
    auto& I = *Result->Impl;
    I.World = I.Definition.Host->GetWorld();
    I.HostTransform = I.Definition.Host->GetActorTransform(); I.Corners = I.Definition.Screen->Corners;
    I.Policies.Emplace(*I.Definition.SolidPolicy.Get()); I.Policies.Emplace(*I.Definition.LowPolicy.Get());
    for (const auto& C : I.Definition.ImmutableFloorFill)
    {
        const auto* Mesh = Cast<UStaticMeshComponent>(C.Get());
        if ((!IsFoundationMesh(Mesh, TEXT("DinkHardnessFixedFloorFillV1"), TEXT("_FixedSolidV1")) &&
             !IsFoundationMesh(Mesh, TEXT("DinkHardnessFixedWaterV1"), TEXT("_FixedLowV1"))) ||
            !C.IsValid() || C->GetWorld() != I.World.Get() || !C->IsRegistered() || !C->IsPhysicsStateCreated())
        { Error = TEXT("immutable foundation bodies missing"); return nullptr; }
        I.Policies.Emplace(*C.Get());
    }
    if (!I.ValidateFoundation(Error)) return nullptr;
    I.Admitted = true; Error.Reset(); return Result;
}
int FDinkRegisteredHardnessOwner::GetScreen() const noexcept { return Impl->Definition.Screen.IsValid() ? Impl->Definition.Screen->ScreenNumber : 0; }
int FDinkRegisteredHardnessOwner::GetVision() const noexcept { return Impl->Definition.Vision; }
bool FDinkRegisteredHardnessOwner::IsAuthoredScreen() const noexcept
{ return !Impl->Definition.IsAuthoredCollisionScreen || Impl->Definition.IsAuthoredCollisionScreen(); }
std::uintptr_t FDinkRegisteredHardnessOwner::GetWorldCookie() const noexcept { return reinterpret_cast<std::uintptr_t>(Impl->World.Get()); }
bool FDinkRegisteredHardnessOwner::HasAdmittedBaseline() const noexcept { return Impl->Admitted && Impl->FastValid(); }
void FDinkRegisteredHardnessOwner::InvalidateForScreenRebuild() noexcept { Impl->Admitted = false; }
bool FDinkRegisteredHardnessOwner::RearmForScreenBuild(int32 Vision, FString& Error)
{
    if (!IsInGameThread() || Impl->Preparing || !Impl->ValidateFoundation(Error)) return false;
    Impl->Definition.Vision = Vision; Impl->Admitted = true; return true;
}

std::unique_ptr<DinkHardness::PreparedPhysics> FDinkRegisteredHardnessOwner::Prepare(const std::vector<DinkHardness::OwnedRect>& Candidate)
{ return PrepareFitted(Candidate,{},{}); }

std::unique_ptr<DinkHardness::PreparedPhysics> FDinkRegisteredHardnessOwner::PrepareFitted(
    const std::vector<DinkHardness::OwnedRect>& Candidate,const std::vector<DinkHardness::FittedOwner>& Fits,
    const std::vector<std::uint8_t>& SuppressedCodes)
{
    auto& I = *Impl;
    if (!IsInGameThread() || I.Preparing || !I.Admitted || !I.FastValid() || IsAuthoredScreen()) return nullptr;
    TSet<uint8> Suppressed;
    TSet<std::uintptr_t> Instances;
    for(uint8 Code:SuppressedCodes){if(Code<101 || Code>199 || Suppressed.Contains(Code))return nullptr;Suppressed.Add(Code);}
    for(const auto& Fit:Fits)
    {
        if(Fit.Code<101 || Fit.Code>199 || !Fit.InstanceId || Instances.Contains(Fit.InstanceId) || !Fit.Geometry ||
           Fit.Geometry->BackendTag()!=NativeFitTag() || !Fit.Geometry->Current())return nullptr;
        const auto& G=static_cast<const FNativeFit&>(*Fit.Geometry);
        if(G.Candidate.World.Get()!=I.World.Get() || G.Candidate.Sprite.CurrentScreen!=GetScreen() ||
           reinterpret_cast<std::uintptr_t>(G.Candidate.Actor.Get())!=Fit.InstanceId)return nullptr;
        if(Fit.Cells.empty() || Fit.Cells.size()!=static_cast<std::size_t>(G.Candidate.LogicalCells.Num()))return nullptr;
        int Previous=-1;for(std::size_t N=0;N<Fit.Cells.size();++N)
        {
            const int Cell=Fit.Cells[N];const auto P=G.Candidate.LogicalCells[static_cast<int32>(N)];
            if(Cell<=Previous || Cell>=240000 || Cell!=P.Y*600+P.X)return nullptr;
            Previous=Cell;
        }
        Instances.Add(Fit.InstanceId);
    }
    auto Raster=DinkHardness::FittedRasterRects(Candidate,Fits,SuppressedCodes);if(!Raster)return nullptr;
    TMap<uint8, TArray<TArray<FVector>>> Groups;
    for (const auto& R : *Raster)
    {
        if (!(R.Code == 1 || R.Code == 2 || R.Code == 3 || (R.Code >= 101 && R.Code <= 199)) ||
            R.Bounds.Left < 0 || R.Bounds.Top < 0 || R.Bounds.Left >= R.Bounds.Right || R.Bounds.Right > 600 ||
            R.Bounds.Top >= R.Bounds.Bottom || R.Bounds.Bottom > 400) return nullptr;
        if(Suppressed.Contains(R.Code))continue;
        const auto& Bounds=R.Bounds;
        TArray<FVector> Vertices;
        for (const FIntPoint P : {FIntPoint(Bounds.Left,Bounds.Top), FIntPoint(Bounds.Right,Bounds.Top),
                                 FIntPoint(Bounds.Right,Bounds.Bottom), FIntPoint(Bounds.Left,Bounds.Bottom)})
            Vertices.Add(I.HostTransform.InverseTransformPosition(I.Definition.Screen->MapPixelToWorld(P.X,P.Y)));
        for (int32 N=0;N<4;++N)
            Vertices.Add(I.HostTransform.InverseTransformPosition(I.Definition.Screen->MapPixelToWorld(
                N==0 || N==3 ? Bounds.Left : Bounds.Right, N<2 ? Bounds.Top : Bounds.Bottom) + FVector(0,0,I.Definition.HeightCm)));
        Groups.FindOrAdd(R.Code).Add(MoveTemp(Vertices));
    }
    auto Next = MakeShared<FBodySet>();
    TArray<uint8> Codes; Groups.GetKeys(Codes); Codes.Sort();
    for (uint8 Code : Codes)
    {
        AActor* Host = I.Definition.Host.Get();
        const FName Name = MakeUniqueObjectName(Host, UDinkHardnessPrismComponent::StaticClass(),
            FName(*FString::Printf(TEXT("HardnessV1_S%03d_C%03d"), GetScreen(), Code)));
        auto* C = NewObject<UDinkHardnessPrismComponent>(Host, Name, RF_Transient);
        C->HardnessCode = Code;
        C->ComponentTags.Add(TEXT("DinkHardnessOwnedV1"));
        Next->Components.Emplace(C); // cleanup on every refusal owns only these new components
        C->SetupAttachment(Host->GetRootComponent());
        const UPrimitiveComponent& Policy = *(Code == 2 ? I.Definition.LowPolicy.Get() : I.Definition.SolidPolicy.Get());
        if (!C->PrepareGeometry(Groups[Code], Policy)) return nullptr;
        Host->AddInstanceComponent(C); C->RegisterComponent();
        const FPolicy& Expected = I.Policies[Code == 2 ? 1 : 0];
        if (!C->FinalizeRegisteredPreparation(Policy) || !Expected.Matches(*C, true)) return nullptr;
        bool Captured = false;
        FBodyInstance* Body = C->GetBodyInstance();
        FPhysicsCommand::ExecuteRead(Body->GetPhysicsActorHandle(), [&](const FPhysicsActorHandle& Actor) {
            TArray<FPhysicsShapeHandle> Shapes;
            FPhysicsInterface::GetAllShapes_AssumedLocked(Actor, Shapes);
            for (int32 N=0;N<Shapes.Num();++N) Next->Shapes.Add({Body,Actor,Shapes[N],N,true});
            Captured = !Shapes.IsEmpty();
        });
        if (!Captured) return nullptr;
    }
    // Fitted instances live in the SAME inert body set as legacy shells.
    // Same code can own multiple distinct actor instances; no code-level merge.
    Next->Fits=Fits;
    for(const auto& Fit:Fits)
    {
        const auto& G=static_cast<const FNativeFit&>(*Fit.Geometry);
        AActor* Host=I.Definition.Host.Get();
        auto* C=NewObject<UDinkHardnessPrismComponent>(Host,NAME_None,RF_Transient);
        C->HardnessCode=Fit.Code;C->ComponentTags.Add(TEXT("DinkHardnessOwnedV1"));
        Next->Components.Emplace(C);
        C->SetupAttachment(Host->GetRootComponent());
        C->SetRelativeTransform(G.Candidate.ProposedWorld.GetRelativeTransform(I.HostTransform));
        const auto& Policy=*I.Definition.SolidPolicy.Get();
        if(!C->PrepareCookedMeshGeometry(*G.Candidate.Geometry.BodySetup.Get(),Policy))return nullptr;
        Host->AddInstanceComponent(C);C->RegisterComponent();
        if(!C->FinalizeRegisteredPreparation(Policy) || !I.Policies[0].Matches(*C,true))return nullptr;
        bool Captured=false;auto* Body=C->GetBodyInstance();
        FPhysicsCommand::ExecuteRead(Body->GetPhysicsActorHandle(),[&](const FPhysicsActorHandle& Actor){
            TArray<FPhysicsShapeHandle> Shapes;FPhysicsInterface::GetAllShapes_AssumedLocked(Actor,Shapes);
            for(int32 N=0;N<Shapes.Num();++N)Next->Shapes.Add({Body,Actor,Shapes[N],N,!Suppressed.Contains(Fit.Code) && G.Candidate.Sprite.Hard==0});
            Captured=Shapes.Num()==1;
        });
        if(!Captured)return nullptr;
        Next->Fitted.Add(Fit.InstanceId,C);
        if(Suppressed.Contains(Fit.Code) || G.Candidate.Sprite.Hard!=0)Next->SuppressedComponents.Add(C);
    }
    if(!Next->FitsCurrent())return nullptr;
    I.Preparing = true;
    return std::make_unique<FImpl::FPrepared>(AsShared(), MoveTemp(Next));
}

std::optional<DinkHardness::FittedOwner> FDinkRegisteredHardnessOwner::MakeFittedOwner(
    const FDinkFamilyCollisionFitCandidate& Candidate,UDinkArtFamilySubsystem& Families,uint8 Code,FString& Error)
{
    if(Candidate.bReleaseOnly || Code<101 || Code>199 || !Candidate.Actor.IsValid() ||
       !Families.ValidateCollisionFit(Candidate,Candidate.Sprite,Error))return std::nullopt;
    auto Geometry=std::make_shared<const FNativeFit>(Candidate,Families);
    if(!Geometry->Current())return std::nullopt;
    std::vector<int> Cells;Cells.reserve(Candidate.LogicalCells.Num());
    for(const auto& P:Candidate.LogicalCells)Cells.push_back(P.Y*600+P.X);
    return DinkHardness::FittedOwner{Code,reinterpret_cast<std::uintptr_t>(Candidate.Actor.Get()),Geometry,std::move(Cells)};
}
UPrimitiveComponent* FDinkRegisteredHardnessOwner::FindFittedPrimitive(std::uintptr_t InstanceId) const
{
    if(!IsInGameThread() || !HasAdmittedBaseline() || !Impl->Active->StillRegistered() ||
       !Impl->Active->HasFlags(true))return nullptr;
    bool Current=false;for(const auto& Fit:Impl->Active->Fits)
        if(Fit.InstanceId==InstanceId && Fit.Geometry && Fit.Geometry->Current()){Current=true;break;}
    const auto* Found=Impl->Active->Fitted.Find(InstanceId);
    return Current && Found ? Found->Get() : nullptr;
}

const void* FDinkRegisteredHardnessOwner::BackendTag() const noexcept{return NativeOwnerTag();}
FDinkRegisteredHardnessOwner* FDinkRegisteredHardnessOwner::CheckedOwner(DinkHardness::PhysicsOwner* Owner)
{return Owner && Owner->BackendTag()==NativeOwnerTag() ? static_cast<FDinkRegisteredHardnessOwner*>(Owner) : nullptr;}
