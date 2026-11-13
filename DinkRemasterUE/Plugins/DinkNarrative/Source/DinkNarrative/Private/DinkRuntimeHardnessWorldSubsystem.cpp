#include "Hardness/DinkRuntimeHardnessWorldSubsystem.h"
#include "Hardness/DinkRegisteredHardnessOwner.h"
#include "Hardness/DinkHardnessFoundationSource.h"
#include "DinkArtSubsystem.h"
#include "DinkGameplay.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"

struct UDinkRuntimeHardnessWorldSubsystem::FEntry
{
    TSharedPtr<FDinkRegisteredHardnessOwner> Owner;
    TSharedPtr<FDinkHardnessFoundationSource> Source;
    TWeakObjectPtr<ADinkGreyboxScreen> Host;
    TWeakObjectPtr<ADinkScreenVolume> Volume;
};

bool UDinkRuntimeHardnessWorldSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{ return Type==EWorldType::Game || Type==EWorldType::PIE; }

void UDinkRuntimeHardnessWorldSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    bHostIndexDirty=true;
    if(UWorld* World=GetWorld())
    {
        SpawnHandle=World->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateWeakLambda(this,[this](AActor* Actor)
        { if(Actor&&Actor->IsA<ADinkGreyboxScreen>())bHostIndexDirty=true; }));
    }
    auto Dirty=[this](ULevel*,UWorld* InWorld){ if(InWorld==GetWorld())bHostIndexDirty=true; };
    LevelAddedHandle=FWorldDelegates::LevelAddedToWorld.AddWeakLambda(this,Dirty);
    LevelRemovedHandle=FWorldDelegates::LevelRemovedFromWorld.AddWeakLambda(this,Dirty);
}

void UDinkRuntimeHardnessWorldSubsystem::RebuildHostIndex() const
{
    HostIndex.Reset();
    if(UWorld* World=GetWorld())
        for(TActorIterator<ADinkGreyboxScreen> It(World);It;++It)HostIndex.Add(It->ScreenNumber,*It);
    bHostIndexDirty=false;
}

bool UDinkRuntimeHardnessWorldSubsystem::RequiresScreenCapability(int32 Screen) const
{
    if(!GetWorld())return false;
    if(bHostIndexDirty)RebuildHostIndex();
    bool bStale=false;
    for(auto It=HostIndex.CreateConstKeyIterator(Screen);It;++It)
    {
        const ADinkGreyboxScreen* Host=It.Value().Get();
        if(!Host||Host->ScreenNumber!=Screen){bStale=true;continue;}
        if(Host->ActorHasTag(TEXT("DinkHardnessWorldV1")))return true;
    }
    if(bStale)
    {
        // A host went away or was renumbered after the index was built: one full look, as before the index.
        RebuildHostIndex();
        for(auto It=HostIndex.CreateConstKeyIterator(Screen);It;++It)
            if(const ADinkGreyboxScreen* Host=It.Value().Get();Host&&Host->ActorHasTag(TEXT("DinkHardnessWorldV1")))return true;
    }
    // New Data alone MUST NOT change an old world's placement/main order.
    return false;
}

bool UDinkRuntimeHardnessWorldSubsystem::IsAuthoredCollisionScreen(int32 Screen) const
{
    const auto* Art=GetWorld()?GetWorld()->GetSubsystem<UDinkArtSubsystem>():nullptr;
    return Art && Art->UsesAuthoredCollision(Screen);
}

TSharedPtr<DinkHardness::PhysicsOwner> UDinkRuntimeHardnessWorldSubsystem::AcquireOrRearm(
    int32 Screen,int32 Vision,FString& Error)
{
    auto Fail=[&Error](const TCHAR* Why)->TSharedPtr<DinkHardness::PhysicsOwner>{Error=Why;return nullptr;};
    UWorld* World=GetWorld();
    if(!IsInGameThread() || !World || !RequiresScreenCapability(Screen))return Fail(TEXT("no explicit runtime-hardness world capability"));
    const auto* Art=World->GetSubsystem<UDinkArtSubsystem>();
    if(!Art || !Art->HasCompletedInitialApplication())return Fail(TEXT("art collision application not complete; hold loading gate"));
    if(Art->UsesAuthoredCollision(Screen))return Fail(TEXT("authored collision screen excludes legacy proxy activation"));
    ADinkGreyboxScreen* Host=nullptr;ADinkScreenVolume* Volume=nullptr;
    for(TActorIterator<ADinkGreyboxScreen> It(World);It;++It)
        if(It->ScreenNumber==Screen && It->ActorHasTag(TEXT("DinkHardnessWorldV1")))
        {if(Host)return Fail(TEXT("ambiguous versioned hardness host"));Host=*It;}
    for(TActorIterator<ADinkScreenVolume> It(World);It;++It)
        if(It->ScreenNumber==Screen){if(Volume)return Fail(TEXT("ambiguous logical screen volume"));Volume=*It;}
    if(!Host || !Volume || !Host->CollisionSolid || !Host->CollisionLow)return Fail(TEXT("versioned screen components missing"));
    auto Source=MakeShared<FDinkHardnessFoundationSource>();
    const FString File=FDinkGameplayData::GetDataPath(*FString::Printf(TEXT("Hardness/Foundations/SCR_%03d.json"),Screen));
    if(!FDinkHardnessFoundationSource::Load(File,Screen,*Source,Error)||
        !Source->VerifyGameplayInputs(Error)||!Source->VerifyInstances(*Volume,*Host,Error))return nullptr;
    if(auto* Existing=Owners.Find(Screen))
    {
        const auto& Entry=**Existing;
        if(Entry.Host.Get()!=Host || Entry.Volume.Get()!=Volume || Entry.Source->SourceTextSha1!=Source->SourceTextSha1)
            return Fail(TEXT("hardness generation changed; explicit world rebuild required"));
        if(!Entry.Owner->RearmForScreenBuild(Vision,Error))return nullptr;
        return Entry.Owner;
    }
    const TWeakObjectPtr<UWorld> WeakWorld=World;
    const TWeakObjectPtr<ADinkGreyboxScreen> WeakHost=Host;
    const TWeakObjectPtr<ADinkScreenVolume> WeakVolume=Volume;
    FDinkHardnessWorldDefinition Definition;
    Definition.Host=Host;Definition.Screen=Volume;Definition.SolidPolicy=Host->CollisionSolid;
    Definition.LowPolicy=Host->CollisionLow;Definition.Vision=Vision;Definition.HeightCm=Source->HeightCm;
    Definition.ImmutableFloorFill.Add(Host->CollisionSolid);
    if(Host->CollisionLow->GetStaticMesh())Definition.ImmutableFloorFill.Add(Host->CollisionLow);
    Definition.IsAuthoredCollisionScreen=[WeakWorld,Screen] {
        const auto* Art=WeakWorld.IsValid()?WeakWorld->GetSubsystem<UDinkArtSubsystem>():nullptr;
        return !Art || !Art->HasCompletedInitialApplication() || Art->UsesAuthoredCollision(Screen);
    };
    Definition.VerifyImmutableFoundation=[Source,WeakHost,WeakVolume](FString& OutError) {
        if(!WeakHost.IsValid()||!WeakVolume.IsValid()){OutError=TEXT("foundation actor lifetime expired");return false;}
        return Source->VerifyGameplayInputs(OutError)&&Source->VerifyInstances(*WeakVolume.Get(),*WeakHost.Get(),OutError);
    };
    auto Owner=FDinkRegisteredHardnessOwner::Create(MoveTemp(Definition),Error);
    if(!Owner)return nullptr;
    auto Entry=MakeShared<FEntry>();Entry->Owner=Owner;Entry->Source=Source;Entry->Host=Host;Entry->Volume=Volume;
    Owners.Add(Screen,Entry);Error.Reset();return Owner;
}

void UDinkRuntimeHardnessWorldSubsystem::Deinitialize()
{
    for(auto& Pair:Owners)if(Pair.Value && Pair.Value->Owner)Pair.Value->Owner->InvalidateForScreenRebuild();
    Owners.Reset();
    if(UWorld* World=GetWorld();World&&SpawnHandle.IsValid())World->RemoveOnActorSpawnedHandler(SpawnHandle);
    FWorldDelegates::LevelAddedToWorld.Remove(LevelAddedHandle);
    FWorldDelegates::LevelRemovedFromWorld.Remove(LevelRemovedHandle);
    HostIndex.Reset();bHostIndexDirty=true;
    Super::Deinitialize();
}
