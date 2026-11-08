#include "DinkPlayerActionComponent.h"
#include "DinkCoreModule.h"
#include "DinkSaveGame.h"
#include "DinkSaveSubsystem.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
const FName PlayerActionSaveKey(TEXT("player_action"));
}

UDinkPlayerActionComponent::UDinkPlayerActionComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = false;
    PrimaryComponentTick.bTickEvenWhenPaused = false;
}

bool UDinkPlayerActionComponent::IsReviewedSequence(int32 Sequence)
{
    return Sequence == 102 || Sequence == 104 || Sequence == 106 || Sequence == 108;
}

bool UDinkPlayerActionComponent::Configure(USkeletalMeshComponent* Mesh, const TMap<int32, UAnimSequence*>& ApprovedActions)
{
    if (!Mesh || !Mesh->GetSkeletalMeshAsset() || ApprovedActions.IsEmpty()) return false;
    for (const auto& Pair : ApprovedActions)
        if (!IsReviewedSequence(Pair.Key) || !Pair.Value || Pair.Value->GetSkeleton() != Mesh->GetSkeletalMeshAsset()->GetSkeleton() ||
            Pair.Value->HasRootMotion() || Pair.Value->GetPlayLength() <= 0) return false;
    Cancel();
    if (Target && Target != Mesh) Target->RemoveTickPrerequisiteComponent(this);
    Target = Mesh;
    Actions.Reset();
    for (const auto& Pair : ApprovedActions) Actions.Add(Pair.Key, Pair.Value);
    Target->AddTickPrerequisiteComponent(this);
    BindSave();
    return true;
}

void UDinkPlayerActionComponent::BindSave()
{
    if (Saves.IsValid() || !GetWorld() || !GetWorld()->GetGameInstance()) return;
    UDinkSaveSubsystem* Subsystem = GetWorld()->GetGameInstance()->GetSubsystem<UDinkSaveSubsystem>();
    if (!Subsystem) return;
    Saves = Subsystem;
    CaptureHandle = Subsystem->OnSnapshotCaptured.AddUObject(this, &UDinkPlayerActionComponent::CaptureSave);
    RestoreHandle = Subsystem->OnSnapshotApplied.AddUObject(this, &UDinkPlayerActionComponent::RestoreSave);
}

bool UDinkPlayerActionComponent::PlaySequence(int32 Sequence)
{
    UAnimSequence* Clip = Actions.FindRef(Sequence);
    if (!Target || !Clip)
    {
        Cancel();
        return false;
    }
    if (IsActionActive() && (!Target->GetSingleNodeInstance() || Target->GetSingleNodeInstance()->GetAnimationAsset() != ActiveClip))
        ResetAction(false);
    if (!IsActionActive())
    {
        if (Target->GetAnimationMode() != EAnimationMode::AnimationBlueprint || !Target->GetAnimClass()) return false;
        OriginalAnimClass = Target->GetAnimClass();
    }
    PlayedMesh = Target->GetSkeletalMeshAsset();
    ActiveClip = Clip;
    ActiveSequence = Sequence;
    ElapsedSeconds = 0;
    PreviousLocation = GetOwner()->GetActorLocation();
    Target->PlayAnimation(Clip, false);
    if (UAnimSingleNodeInstance* Node = Target->GetSingleNodeInstance())
    {
        // One game-time clock owns progress. Never emit animation notifies or double-advance.
        Node->SetPlaying(false);
        Node->SetPosition(0, false);
    }
    SetComponentTickEnabled(true);
    UE_LOG(LogDink, Display, TEXT("Player cosmetic action seq=%d clip=%s"), Sequence, *Clip->GetPathName());
    return true;
}

void UDinkPlayerActionComponent::ResetAction(bool RestoreAnimation)
{
    const bool WasActive = IsActionActive();
    const bool OwnsAnimation = WasActive && Target && Target->GetSingleNodeInstance() &&
        Target->GetSingleNodeInstance()->GetAnimationAsset() == ActiveClip;
    ActiveSequence = 0;
    ElapsedSeconds = 0;
    ActiveClip = nullptr;
    PlayedMesh = nullptr;
    SetComponentTickEnabled(false);
    if (OwnsAnimation && RestoreAnimation && Target && OriginalAnimClass)
        Target->SetAnimInstanceClass(OriginalAnimClass);
    OriginalAnimClass = nullptr;
}

void UDinkPlayerActionComponent::Cancel()
{
    ResetAction(true);
}

void UDinkPlayerActionComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(DeltaTime, TickType, TickFunction);
    if (!IsActionActive() || !Target || !ActiveClip) return;
    UAnimSingleNodeInstance* Node = Target->GetSingleNodeInstance();
    if (Target->GetAnimationMode() != EAnimationMode::AnimationSingleNode || !Node || Node->GetAnimationAsset() != ActiveClip)
    {
        ResetAction(false); // An external replacement owns the new animation; leave it intact.
        return;
    }
    if (Target->GetSkeletalMeshAsset() != PlayedMesh)
    {
        const bool Compatible = Target->GetSkeletalMeshAsset() && PlayedMesh &&
            Target->GetSkeletalMeshAsset()->GetSkeleton() == PlayedMesh->GetSkeleton();
        ResetAction(Compatible);
        return;
    }
    const FVector Location = GetOwner()->GetActorLocation();
    if (FVector::DistSquared(Location, PreviousLocation) > FMath::Square(200.)) { Cancel(); return; }
    PreviousLocation = Location;
    ElapsedSeconds += FMath::Max(0.f, DeltaTime);
    if (ElapsedSeconds >= ActiveClip->GetPlayLength()) { Cancel(); return; }
    Node->SetPosition(float(ElapsedSeconds), false);
}

void UDinkPlayerActionComponent::CaptureSave(UDinkSaveGame* Save)
{
    if (!Save) return;
    Save->SubsystemState.Remove(PlayerActionSaveKey);
    if (!IsActionActive() || !ActiveClip || !Target || !Target->GetSingleNodeInstance() ||
        Target->GetSingleNodeInstance()->GetAnimationAsset() != ActiveClip) return;
    const TSharedRef<FJsonObject> State = MakeShared<FJsonObject>();
    State->SetStringField(TEXT("schema"), TEXT("dink-player-action/1"));
    State->SetNumberField(TEXT("sequence"), ActiveSequence);
    State->SetNumberField(TEXT("elapsed_s"), ElapsedSeconds);
    State->SetStringField(TEXT("animation"), ActiveClip->GetPathName());
    FString Json;
    FJsonSerializer::Serialize(State, TJsonWriterFactory<>::Create(&Json));
    Save->SubsystemState.Add(PlayerActionSaveKey, Json);
}

void UDinkPlayerActionComponent::RestoreSave(const UDinkSaveGame* Save)
{
    Cancel(); // Old/idle saves also cancel any action from the discarded scene.
    const FString* Json = Save ? Save->SubsystemState.Find(PlayerActionSaveKey) : nullptr;
    if (!Json) return;
    TSharedPtr<FJsonObject> State;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Json), State) || !State) return;
    FString Schema, Path;
    double Sequence = 0, Elapsed = 0;
    if (!State->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-player-action/1") ||
        !State->TryGetStringField(TEXT("animation"), Path) || !State->TryGetNumberField(TEXT("sequence"), Sequence) ||
        !State->TryGetNumberField(TEXT("elapsed_s"), Elapsed) || !FMath::IsFinite(Elapsed) || Elapsed < 0 ||
        !FMath::IsFinite(Sequence) || Sequence < 0 || Sequence > MAX_int32 || Sequence != FMath::FloorToDouble(Sequence)) return;
    UAnimSequence* Clip = Actions.FindRef(int32(Sequence));
    if (!Clip || Clip->GetPathName() != Path || Elapsed >= Clip->GetPlayLength() || !PlaySequence(int32(Sequence))) return;
    ElapsedSeconds = Elapsed;
    PreviousLocation = GetOwner()->GetActorLocation();
    if (UAnimSingleNodeInstance* Node = Target->GetSingleNodeInstance()) Node->SetPosition(float(Elapsed), false);
}

void UDinkPlayerActionComponent::OnUnregister()
{
    Cancel();
    if (Target) Target->RemoveTickPrerequisiteComponent(this);
    if (UDinkSaveSubsystem* Subsystem = Saves.Get())
    {
        Subsystem->OnSnapshotCaptured.Remove(CaptureHandle);
        Subsystem->OnSnapshotApplied.Remove(RestoreHandle);
    }
    Saves.Reset();
    Super::OnUnregister();
}
