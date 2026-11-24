#include "Greybox/DinkGreyboxSubsystem.h"
#include "DinkCreatureClassComponent.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkLandforms.h"
#include "DinkPerfScope.h"
#include "DinkScreenIndex.h"
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
	TEXT("dink.ScreenInfo"), 0, TEXT("Developer overlay showing the current original screen. 0 = off (default), 1 = on."), ECVF_Default);

void UDinkGreyboxSubsystem::RegisterScreen(ADinkScreenVolume* Screen)
{
	if (!Screen) return;
	Screens.AddUnique(Screen);
	const APlayerController* PC = GetWorld() ? GetWorld()->GetFirstPlayerController() : nullptr;
	const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	Screen->RefreshInteriorWallVisuals(Pawn ? FindScreenAt(Pawn->GetActorLocation()) : nullptr);
}

void UDinkGreyboxSubsystem::UnregisterScreen(ADinkScreenVolume* Screen)
{
	if (Screen) Screen->RefreshInteriorWallVisuals(nullptr);
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

bool UDinkGreyboxSubsystem::GotoScreen(int32 ScreenNumber, float MapX, float MapY, bool bEvenIntoWalls)
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
	FVector Target = Screen->MapPixelToWorld(MapX, MapY) + FVector(0.0, 0.0, HalfHeight + 2.0);
	// A20 (23 Nov 2026): a spot with no floor under it (SCR_471's authored pond, drawn where 1997 has meadow: the authored land has a
	// hole there and the water has no collision) let a teleport fall without end. Such a spot takes the nearest pixel of the same
	// screen that has a floor at the screen's level; a spot with a floor is placed as before.
	if (!HasFloorAt(Screen->MapPixelToWorld(MapX, MapY), Pawn))
	{
		bool bFound = false;
		for (int32 R = 4; R <= 240 && !bFound; R += 4)
		{
			for (int32 K = 0; K < 32 && !bFound; ++K)
			{
				const double A = K * UE_TWO_PI / 32.0;
				const float X = MapX + R * FMath::Cos(A), Y = MapY + R * FMath::Sin(A);
				if (X < 0.f || Y < 0.f || X > 599.f || Y > 399.f) continue;
				const FVector At = Screen->MapPixelToWorld(X, Y);
				// a floor within 1.5 m of the screen's level and room for the capsule on it
				FHitResult Floor;
				FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkGotoFloor), true, Pawn);
				const UCapsuleComponent* Capsule = Pawn->FindComponentByClass<UCapsuleComponent>();
				if (!GetWorld()->LineTraceSingleByChannel(Floor, At + FVector(0.0, 0.0, 150.0), At - FVector(0.0, 0.0, 150.0), ECC_Pawn, Params) ||
					(Capsule && GetWorld()->OverlapBlockingTestByChannel(Floor.ImpactPoint + FVector(0.0, 0.0, HalfHeight + 2.0), FQuat::Identity, ECC_Pawn,
						Capsule->GetCollisionShape(), Params))) continue;
				UE_LOG(LogDink, Log, TEXT("dink.Goto: SCR_%03d %.0f,%.0f has no floor (A20); placed at %.0f,%.0f"), ScreenNumber, MapX, MapY, X, Y);
				Target = At + FVector(0.0, 0.0, HalfHeight + 2.0);
				bFound = true;
			}
		}
	}
	// landforms (a visual layer): the capsule lands on the 1997 floor as always; have the drawn ground there before it arrives
	if (UDinkLandformsSubsystem* Landforms = GetWorld()->GetSubsystem<UDinkLandformsSubsystem>())
	{
		Landforms->EnsureAround(Target);
	}
	if (const bool bPlaced = Pawn->TeleportTo(Target, Pawn->GetActorRotation()); bPlaced || !bEvenIntoWalls)
	{
		return bPlaced;
	}
	// The original puts Dink where it is told, walls or not (load_screen keeps his x and y, sp_x/sp_y set them). The checked teleport
	// refuses a spot whose capsule overlaps a wall (s2-culg.c:43: Dink walked off SCR_238's bottom, load_screen'd onto Nadine's house's
	// bottom wall row): the pawn stayed on the old screen and the script's scene played on the wrong one. Placed without the check.
	UE_LOG(LogDink, Log, TEXT("dink.Goto: SCR_%03d %.0f,%.0f overlaps a wall; placed there unchecked"), ScreenNumber, MapX, MapY);
	return Pawn->TeleportTo(Target, Pawn->GetActorRotation(), false, true);
}

bool UDinkGreyboxSubsystem::HasFloorAt(const FVector& At, const AActor* Ignore) const
{
	// Only a real hole counts as no floor: nothing the player capsule meets (Pawn channel) from 1.5 m above the screen's level to 20 m
	// below it, and the spot is not inside anything (a wall's prism, the low collision). Every other spot is placed as before.
	UWorld* World = GetWorld();
	if (!World) return true;
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkGotoFloor), true, Ignore);
	if (World->LineTraceSingleByChannel(Hit, At + FVector(0.0, 0.0, 150.0), At - FVector(0.0, 0.0, 2000.0), ECC_Pawn, Params)) return true;
	return World->OverlapBlockingTestByChannel(At + FVector(0.0, 0.0, 50.0), FQuat::Identity, ECC_Pawn, FCollisionShape::MakeSphere(10.f), Params);
}

void UDinkGreyboxSubsystem::SetSpriteWarpOn(const FString& WarpId, bool bOn)
{
	if (bOn)
	{
		PropOffWarps.Remove(WarpId);
	}
	else
	{
		PropOffWarps.Add(WarpId);
	}
	UE_LOG(LogDink, Log, TEXT("Warp %s %s by sp_prop"), *WarpId, bOn ? TEXT("on") : TEXT("off"));
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
	++WarpSerial;
	OnWarped.Broadcast(Pawn, Warp);
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
	DINK_PERF_SCOPE(Dink_Greybox_FaceCards);
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
			// Hidden replacement cards retain their frozen fitted pose even when screen culling restores bVisible.
			if (!Card || !Card->IsVisible() || !Card->GetStaticMesh() || It->IsHidden() || It->ActorHasTag(TEXT("DinkAuthoredArt")))
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
		// The 1997 pictures of script-created sprites that have no family mesh (UDinkArtFamilySubsystem::DressScriptSprite).
		TArray<TWeakObjectPtr<UStaticMeshComponent>>& Pictures = UDinkArtFamilySubsystem::ScriptPictureCards();
		for (int32 I = Pictures.Num() - 1; I >= 0; --I)
		{
			UStaticMeshComponent* Card = Pictures[I].Get();
			if (!Card || Card->GetWorld() != &World)
			{
				if (!Card) Pictures.RemoveAtSwap(I);
				continue;
			}
			const AActor* Owner = Card->GetOwner();
			// A script character or creature body took the sprite over: its own layer draws it.
			// (a class row's body adds no actor tag: it is found by its component)
			const bool bTaken = Owner && (Owner->ActorHasTag(TEXT("DinkHumanoid")) || Owner->ActorHasTag(TEXT("DinkScriptHumanoid")) ||
				Owner->ActorHasTag(TEXT("DinkCreature")) || Owner->ActorHasTag(TEXT("DinkAuthoredArt")) ||
				Owner->FindComponentByClass<UDinkCreatureClassComponent>() != nullptr);
			if (bTaken != Card->bHiddenInGame) Card->SetHiddenInGame(bTaken);
			if (bTaken) continue;
			const FVector To = (Camera - Card->GetComponentLocation()) * FVector(1, 1, 0);
			if (To.SizeSquared() < 1.0) continue;
			const double Yaw = FMath::RadiansToDegrees(FMath::Atan2(-To.X, To.Y));
			if (FMath::Abs(FRotator::NormalizeAxis(Card->GetComponentRotation().Yaw - Yaw)) >= 0.5) Card->SetWorldRotation(FRotator(0.0, Yaw, 0.0));
		}
	}
}

void UDinkGreyboxSubsystem::FaceNearbyCardsToCamera(UWorld& World)
{
	DINK_PERF_SCOPE(Dink_Greybox_FaceNearbyCards);
	// The same rule as FaceCardsToCamera, over the cards within reach instead of the whole world's 5,800 placements.
	if (CVarDinkBillboard.GetValueOnGameThread() == 0 || World.GetNetMode() == NM_DedicatedServer || !FApp::CanEverRender()) return;
	const APlayerController* PC = World.GetFirstPlayerController();
	if (!PC || !PC->PlayerCameraManager) return;
	const FVector Camera = PC->PlayerCameraManager->GetCameraLocation();
	const double Range = double(CVarDinkBillboardRange.GetValueOnGameThread());
	const double RangeSq = FMath::Square(Range);
	constexpr double MoveCm = 500.0;   // regather before the camera has moved this far: no card can enter the range unseen
	const double Now = World.GetTimeSeconds();
	if (Now >= NextBillboardGather || FVector::DistSquared2D(Camera, BillboardGatherAt) > FMath::Square(MoveCm))
	{
		NextBillboardGather = Now + 0.5;
		BillboardGatherAt = Camera;
		BillboardCards.Reset();
		const double ReachSq = FMath::Square(Range + MoveCm);
		if (UDinkScreenIndexSubsystem* Index = UDinkScreenIndexSubsystem::Get(&World))
			for (const TWeakObjectPtr<ADinkPlaceholderActor>& Weak : Index->AllPlaceholders())
			{
				const ADinkPlaceholderActor* P = Weak.Get();
				if (P && P->Card && FVector::DistSquared2D(P->Card->GetComponentLocation(), Camera) <= ReachSq) BillboardCards.Add(Weak);
			}
	}
	for (const TWeakObjectPtr<ADinkPlaceholderActor>& Weak : BillboardCards)
	{
		ADinkPlaceholderActor* P = Weak.Get();
		UStaticMeshComponent* Card = P ? P->Card.Get() : nullptr;
		static const FName AuthoredTag(TEXT("DinkAuthoredArt"));
		if (!Card || !Card->IsVisible() || !Card->GetStaticMesh() || P->IsHidden() || P->ActorHasTag(AuthoredTag)) continue;
		const FVector To = (Camera - Card->GetComponentLocation()) * FVector(1, 1, 0);
		if (To.SizeSquared() > RangeSq || To.SizeSquared() < 1.0) continue;
		const double Yaw = FMath::RadiansToDegrees(FMath::Atan2(-To.X, To.Y));
		if (FMath::Abs(FRotator::NormalizeAxis(Card->GetComponentRotation().Yaw - Yaw)) < 0.5) continue;
		if (Card->Mobility != EComponentMobility::Movable) Card->SetMobility(EComponentMobility::Movable);
		Card->SetWorldRotation(FRotator(0.0, Yaw, 0.0));
	}
}

void UDinkGreyboxSubsystem::UpdateLegacyCardVisibility(int32 ActiveScreenNumber)
{
	DINK_PERF_SCOPE(Dink_Greybox_LegacyCards);
	if (DinkPerf::FixesEnabled() && bTickRefresh && ActiveScreenNumber > 0 && ActiveScreenNumber == LastLegacyScreen && GetWorld()->GetTimeSeconds() < NextLegacyFullPass
		&& CVarDinkLegacyCardsCurrentScreen.GetValueOnGameThread() != 0)
	{
		return;   // same screen: the cards' visibility is what the last pass left (authored tags settle at play start)
	}
	LastLegacyScreen = ActiveScreenNumber;
	NextLegacyFullPass = GetWorld()->GetTimeSeconds() + 2.0;
	// Keep this independent of actor-hidden/vision, component-hidden and collision state.
	// Those layers belong to scripts and authored replacements and must never be restored by culling.
	// The flicker light and smoke plume of a placed effect hang under its card (#166): they follow the card's flag, both ways
	// (UDinkArtFamilySubsystem::FollowCardVisibility; SetVisibility below does not propagate, so other children keep theirs).
	if (ActiveScreenNumber <= 0 || CVarDinkLegacyCardsCurrentScreen.GetValueOnGameThread() == 0)
	{
		for (const auto& Entry : LegacyCardVisibility)
			if (UPrimitiveComponent* Component=Entry.Key.Get())
			{
				Component->SetVisibility(Entry.Value);
				UDinkArtFamilySubsystem::FollowCardVisibility(Component);
			}
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
	{
		Apply(It->Card,It->ScreenNumber,It->ActorHasTag(TEXT("DinkAuthoredArt")));
		UDinkArtFamilySubsystem::FollowCardVisibility(It->Card);
	}
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
	DINK_PERF_SCOPE(Dink_Greybox_RefreshScreen);
	UWorld* World = GetWorld();
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!Pawn)
	{
		for (const auto& Weak : Screens) if (ADinkScreenVolume* Volume = Weak.Get()) Volume->RefreshInteriorWallVisuals(nullptr);
		LastWallScreen = nullptr;
		WallScreenCount = -1;
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
	// Screen-entry callbacks can move the pawn synchronously. Use its actual
	// physical screen now, not a cached room or the room before those callbacks.
	const ADinkScreenVolume* Physical = FindScreenAt(Pawn->GetActorLocation());
	// the 644 volumes' wall visuals depend only on the physical screen: walk them when it (or the set) changes
	if (!DinkPerf::FixesEnabled() || !bTickRefresh || !Physical || Physical != LastWallScreen.Get() || Screens.Num() != WallScreenCount
		|| Physical->Sheet != LastWallSheet || Physical->InteriorId != LastWallInterior || Physical->bIndoor != bLastWallIndoor)
	{
		LastWallScreen = Physical;
		LastWallSheet = Physical ? Physical->Sheet : NAME_None;
		LastWallInterior = Physical ? Physical->InteriorId : NAME_None;
		bLastWallIndoor = Physical && Physical->bIndoor;
		WallScreenCount = Screens.Num();
		for (const auto& Weak : Screens) if (ADinkScreenVolume* Volume = Weak.Get()) Volume->RefreshInteriorWallVisuals(Physical);
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
        if (!IsValid(Warp) || !Warp->bTriggerEnabled || !IsSpriteWarpOn(Warp->WarpId) || Warp->TriggerMode!=TEXT("walk_in") ||
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
	DINK_PERF_SCOPE(Dink_Greybox_Tick);
	UWorld* World = GetWorld();
	if (DinkPerf::FixesEnabled()) FaceNearbyCardsToCamera(*World); else FaceCardsToCamera(*World);
    APlayerController* IntentPC=World->GetFirstPlayerController();
    ObserveDoorMovement(IntentPC ? Cast<ACharacter>(IntentPC->GetPawn()) : nullptr);
	const double Now = World->GetTimeSeconds();
	if (Now < NextScreenCheck)
	{
		return;
	}
	NextScreenCheck = Now + 0.25;
	bTickRefresh = true;
	RefreshCurrentScreen();
	bTickRefresh = false;
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
