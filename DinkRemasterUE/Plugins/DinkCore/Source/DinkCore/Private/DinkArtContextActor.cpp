#include "DinkArtContextActor.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "TimerManager.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"

ADinkArtContextActor::ADinkArtContextActor()
{
    PrimaryActorTick.bCanEverTick = false;
    USceneComponent *Root = CreateDefaultSubobject<USceneComponent>(TEXT("ContextRoot"));
    Root->SetMobility(EComponentMobility::Static);
    Root->PrimaryComponentTick.bCanEverTick = false;
    SetRootComponent(Root);
    SetActorHiddenInGame(true);
    SetActorEnableCollision(false);
    Tags.Add(TEXT("DinkAuthoredArt"));
    Tags.Add(TEXT("DinkArtContext"));
}
void ADinkArtContextActor::BeginPlay()
{
    Super::BeginPlay();
    Greybox = GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>();
    if (Greybox.IsValid())
        ScreenHandle = Greybox->OnScreenChanged.AddUObject(this, &ADinkArtContextActor::ScreenChanged);
    UpdateVisibility();
    // A first controller can be replaced while the selected room stays unchanged.
    // One bounded context-level refresh observes that lifecycle without mesh ticks.
    GetWorld()->GetTimerManager().SetTimer(ControllerRefreshTimer, this,
        &ADinkArtContextActor::UpdateVisibility, .25f, true);
}
void ADinkArtContextActor::ConfigureOwnerScreen(int32 ScreenNumber)
{
    OwnerScreenNumber = ScreenNumber > 0 ? ScreenNumber : 0;
    if (HasActorBegunPlay())
        UpdateVisibility();
}
UStaticMeshComponent *ADinkArtContextActor::AddRenderOnlyMesh(UStaticMesh *Mesh, const FTransform &Transform)
{
    if (!IsValid(Mesh) || Transform.ContainsNaN())
        return nullptr;
    UStaticMeshComponent *Component = NewObject<UStaticMeshComponent>(this);
    AddInstanceComponent(Component);
    Component->SetupAttachment(GetRootComponent());
    Component->SetMobility(EComponentMobility::Static);
    Component->SetStaticMesh(Mesh);
    Component->SetWorldTransform(Transform);
    Component->SetCollisionProfileName(TEXT("NoCollision"));
    Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Component->SetGenerateOverlapEvents(false);
    Component->SetCanEverAffectNavigation(false);
    Component->SetCastHiddenShadow(false);
    Component->SetAffectIndirectLightingWhileHidden(false);
    Component->PrimaryComponentTick.bCanEverTick = false;
    Component->RegisterComponent();
    return Component;
}
void ADinkArtContextActor::ScreenChanged(ADinkScreenVolume *)
{
    UpdateVisibility();
}
void ADinkArtContextActor::PawnChanged(APawn *)
{
    UpdateVisibility();
}
void ADinkArtContextActor::UpdateVisibility()
{
    APlayerController *PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
    if (PC != BoundController.Get())
    {
        if (BoundController.IsValid())
            BoundController->GetOnNewPawnNotifier().Remove(PawnHandle);
        PawnHandle.Reset();
        BoundController = PC;
        if (PC)
            PawnHandle = PC->GetOnNewPawnNotifier().AddUObject(this, &ADinkArtContextActor::PawnChanged);
    }
    const APawn *Pawn = PC ? PC->GetPawn() : nullptr;
    const ADinkScreenVolume *Screen = Greybox.IsValid() ? Greybox->GetCurrentScreen() : nullptr;
    // The screen subsystem deliberately updates at0.25s intervals. The exact pawn
    // location prevents showing stale context during possession/load transitions.
    const bool Visible = OwnerScreenNumber > 0 && Pawn && Screen && Screen->ScreenNumber == OwnerScreenNumber &&
                         Greybox->FindScreenAt(Pawn->GetActorLocation()) == Screen;
    SetActorHiddenInGame(!Visible);
}
void ADinkArtContextActor::EndPlay(const EEndPlayReason::Type Reason)
{
    SetActorHiddenInGame(true);
    if (UWorld* World=GetWorld()) World->GetTimerManager().ClearTimer(ControllerRefreshTimer);
    if (Greybox.IsValid())
        Greybox->OnScreenChanged.Remove(ScreenHandle);
    if (BoundController.IsValid())
        BoundController->GetOnNewPawnNotifier().Remove(PawnHandle);
    ScreenHandle.Reset();
    PawnHandle.Reset();
    Super::EndPlay(Reason);
}

ADinkArtContextActor *ADinkArtContextActor::CreateFromManifest(UWorld &World, const TSharedPtr<FJsonObject> &Manifest,
                                                               const TMap<FString, UStaticMesh *> &Meshes,
                                                               int32 OwnerScreen)
{
    if (!Manifest.IsValid())
        return nullptr;
    FString Schema, Visibility;
    bool RenderOnly = false;
    double ExplicitScreen = 0;
    const TSharedPtr<FJsonObject> *Context = nullptr;
    if (OwnerScreen <= 0 || !Manifest->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-art/1") ||
        !Manifest->TryGetNumberField(TEXT("screen"), ExplicitScreen) || ExplicitScreen != OwnerScreen ||
        !Manifest->TryGetObjectField(TEXT("context"), Context) ||
        !(*Context)->TryGetStringField(TEXT("visibility"), Visibility) || Visibility != TEXT("owner_screen_only") ||
        !(*Context)->TryGetBoolField(TEXT("render_only"), RenderOnly) || !RenderOnly)
        return nullptr;
    for (const TCHAR *Key : {TEXT("replacements"), TEXT("warp_overrides"), TEXT("hide_origins"),
                             TEXT("hide_screen_visuals"), TEXT("authored_collision_screens"),
                             TEXT("preserve_low_collision_screens"), TEXT("lights"), TEXT("postprocess")})
        if (Manifest->HasField(Key))
            return nullptr;
    const TArray<TSharedPtr<FJsonValue>> *Elements = nullptr;
    if (!Manifest->TryGetArrayField(TEXT("elements"), Elements) || Elements->IsEmpty())
        return nullptr;
    struct FPrepared
    {
        UStaticMesh *Mesh;
        FTransform Transform;
    };
    TArray<FPrepared> Prepared;
    for (const auto &Value : *Elements)
    {
        if (Value->Type != EJson::Object)
            return nullptr;
        const auto Row = Value->AsObject();
        bool Collision = true, CameraOccluder = true;
        FString Path;
        if (!Row->TryGetBoolField(TEXT("collision"), Collision) || Collision ||
            !Row->TryGetBoolField(TEXT("camera_occluder"), CameraOccluder) || CameraOccluder ||
            !Row->TryGetStringField(TEXT("mesh"), Path))
            return nullptr;
        UStaticMesh *const *Mesh = Meshes.Find(Path);
        if (!Mesh || !IsValid(*Mesh))
            return nullptr;
        TArray<FVector> Vectors;
        for (const TCHAR *Key : {TEXT("world_cm"), TEXT("rotation_deg"), TEXT("scale")})
        {
            const TArray<TSharedPtr<FJsonValue>> *XYZ = nullptr;
            if (!Row->TryGetArrayField(Key, XYZ) || XYZ->Num() != 3)
                return nullptr;
            for (const auto &Number : *XYZ)
                if (Number->Type != EJson::Number || !FMath::IsFinite(Number->AsNumber()) ||
                    (FCString::Strcmp(Key, TEXT("scale")) == 0 && Number->AsNumber() <= 0))
                    return nullptr;
            Vectors.Emplace((*XYZ)[0]->AsNumber(), (*XYZ)[1]->AsNumber(), (*XYZ)[2]->AsNumber());
        }
        const FVector &R = Vectors[1];
        Prepared.Add({*Mesh, FTransform(FRotator(R.X, R.Y, R.Z), Vectors[0], Vectors[2])});
    }
    ADinkArtContextActor *Actor = World.SpawnActor<ADinkArtContextActor>();
    if (!Actor)
        return nullptr;
    for (const FPrepared &Row : Prepared)
        if (!Actor->AddRenderOnlyMesh(Row.Mesh, Row.Transform))
        {
            Actor->Destroy();
            return nullptr;
        }
    Actor->ConfigureOwnerScreen(OwnerScreen);
    return Actor;
}
