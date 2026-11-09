#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "DinkInstanceOriginsComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Greybox/DinkWarpComponent.h"
#include "DinkCoreModule.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "DinkStatsComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "EngineUtils.h"
#include "Misc/App.h"

static TAutoConsoleVariable<int32> CVarDinkScreenInfo(
	TEXT("dink.ScreenInfo"), 1, TEXT("Show the original screen the player is on (greybox). 0 = off."), ECVF_Default);

void UDinkGreyboxSubsystem::RegisterScreen(ADinkScreenVolume* Screen)
{
	Screens.AddUnique(Screen);
}

void UDinkGreyboxSubsystem::UnregisterScreen(ADinkScreenVolume* Screen)
{
	Screens.Remove(Screen);
}

void UDinkGreyboxSubsystem::RegisterVisionPlaceholder(ADinkPlaceholderActor* Placeholder)
{
	VisionPlaceholders.FindOrAdd(Placeholder->ScreenNumber).AddUnique(Placeholder);
}

ADinkScreenVolume* UDinkGreyboxSubsystem::FindScreenAt(const FVector& Location) const
{
	for (const TWeakObjectPtr<ADinkScreenVolume>& Weak : Screens)
	{
		ADinkScreenVolume* Screen = Weak.Get();
		if (!Screen)
		{
			continue;
		}
		const FBox Box = Screen->Bounds->Bounds.GetBox();
		if (Location.X < Box.Min.X || Location.X > Box.Max.X || Location.Y < Box.Min.Y || Location.Y > Box.Max.Y)
		{
			continue;
		}
		if (Screen->ContainsWorldLocation(Location))
		{
			return Screen;
		}
	}
	return nullptr;
}

ADinkScreenVolume* UDinkGreyboxSubsystem::FindScreen(int32 ScreenNumber) const
{
	for (const TWeakObjectPtr<ADinkScreenVolume>& Weak : Screens)
	{
		if (Weak.IsValid() && Weak->ScreenNumber == ScreenNumber)
		{
			return Weak.Get();
		}
	}
	return nullptr;
}

int32 UDinkGreyboxSubsystem::SetScreenVision(int32 ScreenNumber, int32 Value)
{
	int32 Shown = 0;
	if (TArray<TWeakObjectPtr<ADinkPlaceholderActor>>* List = VisionPlaceholders.Find(ScreenNumber))
	{
		for (const TWeakObjectPtr<ADinkPlaceholderActor>& Weak : *List)
		{
			if (ADinkPlaceholderActor* P = Weak.Get())
			{
				P->ApplyScreenVision(Value);
				Shown += P->Vision == Value ? 1 : 0;
			}
		}
	}
	UE_LOG(LogDink, Log, TEXT("SCR_%03d vision %d: %d gated placements shown"), ScreenNumber, Value, Shown);
	return Shown;
}

bool UDinkGreyboxSubsystem::GotoScreen(int32 ScreenNumber, float MapX, float MapY)
{
	ADinkScreenVolume* Screen = FindScreen(ScreenNumber);
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!Screen || !Pawn)
	{
		UE_LOG(LogDink, Warning, TEXT("dink.Goto: screen %d %s, pawn %s"), ScreenNumber, Screen ? TEXT("found") : TEXT("not in this map"),
			Pawn ? TEXT("found") : TEXT("missing"));
		return false;
	}
	float HalfHeight = 0.f;
	if (const UCapsuleComponent* Capsule = Pawn->FindComponentByClass<UCapsuleComponent>())
	{
		HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
	}
	const FVector Target = Screen->MapPixelToWorld(MapX, MapY) + FVector(0.0, 0.0, HalfHeight + 2.0);
	return Pawn->TeleportTo(Target, Pawn->GetActorRotation());
}

bool UDinkGreyboxSubsystem::CanWarp(const APawn* Pawn) const
{
	if (WarpingPawns.Contains(Pawn))
	{
		return false;
	}
	const double* Last = LastWarpTime.Find(Pawn);
	return !Last || GetWorld()->GetTimeSeconds() - *Last >= WarpCooldownSeconds;
}

bool UDinkGreyboxSubsystem::BeginWarp(APawn* Pawn)
{
	if (!CanWarp(Pawn)) { return false; }
	WarpingPawns.Add(Pawn);
	return true;
}

void UDinkGreyboxSubsystem::EndWarp(APawn* Pawn)
{
	WarpingPawns.Remove(Pawn);
}

void UDinkGreyboxSubsystem::NotifyWarped(APawn* Pawn, const UDinkWarpComponent& Warp)
{
	LastWarpTime.Add(Pawn, GetWorld()->GetTimeSeconds());
	NextScreenCheck = 0.0;
}

namespace
{
	TAutoConsoleVariable<int32> CVarDinkLegacyCardsCurrentScreen(TEXT("dink.LegacyCardsCurrentScreen"), 1,
		TEXT("Render original sprite cards only on the current logical screen; authored geometry remains visible. 0 restores original visibility."));
	// 0 = leave the sprite cards as imported (all facing south); 1 = turn the cards near the camera to face it.
	TAutoConsoleVariable<int32> CVarDinkBillboard(TEXT("dink.Billboard"), 1,
		TEXT("Greybox: turn placement sprite cards within dink.BillboardRange to face the camera (presentation only)."));
	TAutoConsoleVariable<float> CVarDinkBillboardRange(TEXT("dink.BillboardRange"), 6000.f,
		TEXT("Greybox: distance in cm within which sprite cards face the camera."));

	/** Presentation only: gameplay works in screen pixels and never reads a card's rotation. */
	void FaceCardsToCamera(UWorld& World)
	{
		// Nothing draws under -nullrhi (the headless tests and probe): do not walk 5,846 actors every frame for it.
		if (CVarDinkBillboard.GetValueOnGameThread() == 0 || World.GetNetMode() == NM_DedicatedServer || !FApp::CanEverRender())
		{
			return;
		}
		const APlayerController* PC = World.GetFirstPlayerController();
		if (!PC || !PC->PlayerCameraManager)
		{
			return;
		}
		const FVector Camera = PC->PlayerCameraManager->GetCameraLocation();
		const double RangeSq = FMath::Square(double(CVarDinkBillboardRange.GetValueOnGameThread()));
		for (TActorIterator<ADinkPlaceholderActor> It(&World); It; ++It)
		{
			UStaticMeshComponent* Card = It->Card;
			// Authored meshes have real geometry and collision; rotating them like sprite cards
			// would turn beds, tables and doorways as the camera moves.
			if (!Card || !Card->GetVisibleFlag() || !Card->GetStaticMesh() || It->IsHidden() || It->ActorHasTag(TEXT("DinkAuthoredArt")))
			{
				continue;
			}
			const FVector To = (Camera - Card->GetComponentLocation()) * FVector(1, 1, 0);
			if (To.SizeSquared() > RangeSq || To.SizeSquared() < 1.0)
			{
				continue;
			}
			// The unit card's face normal is local +Y: yaw it so +Y points at the camera.
			const double Yaw = FMath::RadiansToDegrees(FMath::Atan2(-To.X, To.Y));
			if (FMath::Abs(FRotator::NormalizeAxis(Card->GetComponentRotation().Yaw - Yaw)) < 0.5)
			{
				continue;
			}
			if (Card->Mobility != EComponentMobility::Movable)
			{
				Card->SetMobility(EComponentMobility::Movable);
			}
			Card->SetWorldRotation(FRotator(0.0, Yaw, 0.0));
		}
	}
}

void UDinkGreyboxSubsystem::UpdateLegacyCardVisibility(int32 ActiveScreenNumber)
{
	// Keep this independent of actor-hidden/vision, component-hidden and collision state.
	// Those layers belong to scripts and authored replacements and must never be restored by culling.
	if (ActiveScreenNumber <= 0 || CVarDinkLegacyCardsCurrentScreen.GetValueOnGameThread() == 0)
	{
		for (const auto& Entry : LegacyCardVisibility)
			if (UPrimitiveComponent* Component=Entry.Key.Get()) Component->SetVisibility(Entry.Value);
		LegacyCardVisibility.Reset();
		return;
	}
	auto Apply=[&](UPrimitiveComponent* Component,int32 ScreenNumber,bool bAuthored)
	{
		if (!Component) return;
		if (bAuthored || ScreenNumber <= 0)
		{
			if (const bool* Original=LegacyCardVisibility.Find(Component))
			{
				Component->SetVisibility(*Original);
				LegacyCardVisibility.Remove(Component);
			}
			return;
		}
		const bool* Original=LegacyCardVisibility.Find(Component);
		if (!Original) Original=&LegacyCardVisibility.Add(Component,Component->GetVisibleFlag());
		const bool bVisible=*Original && ScreenNumber==ActiveScreenNumber;
		if (Component->GetVisibleFlag()!=bVisible) Component->SetVisibility(bVisible);
	};
	for (TActorIterator<ADinkPlaceholderActor> It(GetWorld());It;++It)
		Apply(It->Card,It->ScreenNumber,It->ActorHasTag(TEXT("DinkAuthoredArt")));
	for (TActorIterator<ADinkGreyboxScreen> It(GetWorld());It;++It)
	{
		// Use original instance origin metadata; do not touch arbitrary authored ISMs on this actor.
		TSet<FName> OriginalNames;
		if (It->InstanceOrigins) for (const FDinkInstanceOrigin& Origin:It->InstanceOrigins->Origins) OriginalNames.Add(Origin.ComponentName);
		TInlineComponentArray<UInstancedStaticMeshComponent*> Components(*It);
		for (UInstancedStaticMeshComponent* Component:Components)
			if (OriginalNames.Contains(Component->GetFName())) Apply(Component,It->ScreenNumber,It->ActorHasTag(TEXT("DinkAuthoredArt")));
	}
	for (auto It=LegacyCardVisibility.CreateIterator();It;++It) if (!It.Key().IsValid()) It.RemoveCurrent();
}

void UDinkGreyboxSubsystem::RefreshCurrentScreen()
{
	UWorld* World = GetWorld();
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!Pawn)
	{
		UpdateLegacyCardVisibility(0);
		return;
	}
	ADinkScreenVolume* Screen = FindScreenAt(Pawn->GetActorLocation());
	if (Screen != CurrentScreen.Get())
	{
		CurrentScreen = Screen;
		OnScreenChanged.Broadcast(Screen);
		UE_LOG(LogDink, Log, TEXT("Entered %s"), Screen ? *Screen->Describe() : TEXT("no screen"));
	}
	UpdateLegacyCardVisibility(Screen ? Screen->ScreenNumber : 0);
}

void UDinkGreyboxSubsystem::ObserveDoorMovement(ACharacter* Character)
{
    if (DoorMovementPawn.Get()==Character) return;
    if (DoorMovementPawn.IsValid())
        DoorMovementPawn->OnCharacterMovementUpdated.RemoveDynamic(this,&UDinkGreyboxSubsystem::CaptureDoorMovement);
    DoorMovementPawn=Character; DoorMovementFrame=MAX_uint64; DoorMovementIntent=FVector::ZeroVector;
    if (Character)
        Character->OnCharacterMovementUpdated.AddDynamic(this,&UDinkGreyboxSubsystem::CaptureDoorMovement);
}

void UDinkGreyboxSubsystem::CaptureDoorMovement(float DeltaSeconds,FVector,FVector)
{
    ACharacter* Hero=DoorMovementPawn.Get();
    const UCharacterMovementComponent* Movement=Hero ? Hero->GetCharacterMovement() : nullptr;
    DoorMovementFrame=MAX_uint64; DoorMovementIntent=FVector::ZeroVector;
    if (!Movement || DeltaSeconds<=SMALL_NUMBER) return;
    DoorMovementIntent=Movement->GetCurrentAcceleration(); DoorMovementIntent.Z=0;
    DoorMovementLocation=Hero->GetActorLocation(); DoorMovementFrame=GFrameCounter;
}

void UDinkGreyboxSubsystem::Deinitialize()
{
    ObserveDoorMovement(nullptr);
    Super::Deinitialize();
}

void UDinkGreyboxSubsystem::RetryOverlappingDoor()
{
    ACharacter* Hero=DoorMovementPawn.Get();
    const APlayerController* PC=GetWorld()->GetFirstPlayerController();
    const UCharacterMovementComponent* Movement=Hero ? Hero->GetCharacterMovement() : nullptr;
    if (!Hero || !PC || PC->GetPawn()!=Hero || !Hero->IsPlayerControlled() || PC->IsMoveInputIgnored() ||
        !Movement || !Movement->IsActive() || !Movement->IsComponentTickEnabled() || Movement->MovementMode==MOVE_None ||
        DoorMovementFrame!=GFrameCounter || DoorMovementIntent.IsNearlyZero() || !CanWarp(Hero) ||
        FVector::DistSquared(Hero->GetActorLocation(),DoorMovementLocation)>1. ||
        (WarpSuppressed && WarpSuppressed(Hero))) return;
    const UDinkStatsComponent* Stats=Hero->FindComponentByClass<UDinkStatsComponent>();
    if (Stats && Stats->IsDead()) return;
    const ADinkScreenVolume* Physical=FindScreenAt(Hero->GetActorLocation());
    if (!Physical) return;
    const FVector Intent=DoorMovementIntent.GetSafeNormal2D();
    TArray<UPrimitiveComponent*> Overlaps; Hero->GetOverlappingComponents(Overlaps);
    UDinkWarpComponent* Best=nullptr; double BestDistance=TNumericLimits<double>::Max();
    for (UPrimitiveComponent* Component:Overlaps)
    {
        auto* Warp=Cast<UDinkWarpComponent>(Component);
        if (!IsValid(Warp) || !Warp->bTriggerEnabled || Warp->TriggerMode!=TEXT("walk_in") ||
            (Warp->Kind!=TEXT("door") && Warp->Kind!=TEXT("exit")) || Warp->SourceScreen!=Physical->ScreenNumber ||
            !Warp->IsOverlappingActor(Hero)) continue;
        const FVector Approach=Warp->GetRetryApproachDirection(Hero);
        if (Approach.IsNearlyZero() || FVector::DotProduct(Intent,Approach)<=.5f) continue;
        const double Distance=FVector::DistSquared2D(Hero->GetActorLocation(),Warp->GetComponentLocation());
        if (!Best || Distance<BestDistance || (Distance==BestDistance && Warp->WarpId.Compare(Best->WarpId)<0))
        { Best=Warp; BestDistance=Distance; }
    }
    // Exactly one attempt, including failure: another overlapping destination must not be substituted.
    if (Best) Best->TryWarp(Hero);
}

void UDinkGreyboxSubsystem::Tick(float DeltaTime)
{
	UWorld* World = GetWorld();
	FaceCardsToCamera(*World);
    APlayerController* IntentPC=World->GetFirstPlayerController();
    ObserveDoorMovement(IntentPC ? Cast<ACharacter>(IntentPC->GetPawn()) : nullptr);
	const double Now = World->GetTimeSeconds();
	if (Now < NextScreenCheck)
	{
		return;
	}
	NextScreenCheck = Now + 0.25;
	RefreshCurrentScreen();
    // UWorld ticks tickable subsystems after actor movement. Only an actual movement
    // callback from THIS frame supplies intent; no stale LastInput/velocity fallback.
    if (DeltaTime>SMALL_NUMBER) RetryOverlappingDoor();
	const APlayerController* PC = World->GetFirstPlayerController();
	const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!Pawn)
	{
		return;
	}
	ADinkScreenVolume* Screen = CurrentScreen.Get();
	if (GEngine && CVarDinkScreenInfo.GetValueOnGameThread() != 0)
	{
		GEngine->AddOnScreenDebugMessage(int32(0x0D1E5C), 0.5f, FColor(255, 230, 120),
			Screen ? Screen->Describe() : FString(TEXT("(between screens)")));
	}
}

bool UDinkGreyboxSubsystem::SetScreenLocked(int32 ScreenNumber, bool bLocked)
{
	if (bLocked && LockedScreen != 0 && LockedScreen != ScreenNumber)
	{
		if (ADinkScreenVolume* Old = FindScreen(LockedScreen))
		{
			Old->SetLockBarriers(false);
		}
	}
	ADinkScreenVolume* Screen = FindScreen(ScreenNumber);
	if (Screen)
	{
		Screen->SetLockBarriers(bLocked);
	}
	if (bLocked)
	{
		LockedScreen = Screen ? ScreenNumber : 0;
	}
	else if (LockedScreen == ScreenNumber || ScreenNumber == 0)
	{
		if (ADinkScreenVolume* Old = LockedScreen != 0 ? FindScreen(LockedScreen) : nullptr)
		{
			Old->SetLockBarriers(false);
		}
		LockedScreen = 0;
	}
	UE_LOG(LogDink, Log, TEXT("screenlock %d on screen %d%s"), bLocked ? 1 : 0, ScreenNumber, Screen ? TEXT("") : TEXT(" (not in this world)"));
	return Screen != nullptr;
}

TStatId UDinkGreyboxSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkGreyboxSubsystem, STATGROUP_Tickables);
}

bool UDinkGreyboxSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

static UDinkGreyboxSubsystem* GreyboxFor(UWorld* World)
{
	return World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
}

static FAutoConsoleCommandWithWorldAndArgs GDinkGotoCommand(
	TEXT("dink.Goto"), TEXT("dink.Goto <screen> [mapX mapY]: teleport the player to an original screen (greybox)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (UDinkGreyboxSubsystem* G = GreyboxFor(World); G && Args.Num() >= 1)
		{
			const float X = Args.Num() >= 3 ? FCString::Atof(*Args[1]) : 300.f;
			const float Y = Args.Num() >= 3 ? FCString::Atof(*Args[2]) : 200.f;
			G->GotoScreen(FCString::Atoi(*Args[0]), X, Y);
		}
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkVisionCommand(
	TEXT("dink.Vision"), TEXT("dink.Vision <screen> <value>: show the placements gated by that &vision value (greybox)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (UDinkGreyboxSubsystem* G = GreyboxFor(World); G && Args.Num() >= 2)
		{
			G->SetScreenVision(FCString::Atoi(*Args[0]), FCString::Atoi(*Args[1]));
		}
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkWhereCommand(
	TEXT("dink.Where"), TEXT("dink.Where: print the original screen the player is on (greybox)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&, UWorld* World)
	{
		if (UDinkGreyboxSubsystem* G = GreyboxFor(World))
		{
			const ADinkScreenVolume* S = G->GetCurrentScreen();
			UE_LOG(LogDink, Display, TEXT("%s"), S ? *S->Describe() : TEXT("not on a screen"));
		}
	}));
