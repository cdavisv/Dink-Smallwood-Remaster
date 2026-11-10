#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "DinkCollision.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/CollisionProfile.h"
#include "Engine/World.h"

ADinkScreenVolume::ADinkScreenVolume()
{
	PrimaryActorTick.bCanEverTick = false;
	Bounds = CreateDefaultSubobject<UBoxComponent>(TEXT("Bounds"));
	Bounds->SetCollisionProfileName(DinkCollision::ProfileScreenVolume);
	Bounds->SetGenerateOverlapEvents(false);
	Bounds->SetCanEverAffectNavigation(false);
	Bounds->ShapeColor = FColor(80, 200, 255);
	Bounds->bHiddenInGame = true;
	RootComponent = Bounds;

	static const TCHAR* EdgeNames[] = {TEXT("EdgeWall_N"), TEXT("EdgeWall_E"), TEXT("EdgeWall_S"), TEXT("EdgeWall_W")};
	for (const TCHAR* Name : EdgeNames)
	{
		UBoxComponent* Wall = CreateDefaultSubobject<UBoxComponent>(Name);
		Wall->SetupAttachment(Bounds);
		Wall->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Wall->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
		Wall->SetGenerateOverlapEvents(false);
		Wall->SetCanEverAffectNavigation(false);
		Wall->ShapeColor = FColor(255, 60, 60);
		Wall->bHiddenInGame = true;
		Wall->SetBoxExtent(FVector(1.0, 1.0, 1.0));
		EdgeWalls.Add(Wall);
	}
}

bool ADinkScreenVolume::ContainsWorldLocation(const FVector& Location) const
{
	return DinkLayout::ContainsMetres(Corners, DinkLayout::UnrealToMetres(Location), 1e-6);
}

FVector ADinkScreenVolume::MapPixelToWorld(float MapX, float MapY) const
{
	return DinkLayout::MapPixelToUnreal(Corners, MapX, MapY);
}

FString ADinkScreenVolume::Describe() const
{
	FString Text = FString::Printf(TEXT("%s  %s / %s  [%s%s]  music %d"), *ScreenId.ToString(), *RegionName, *AreaName,
		*Kind.ToString(), bIndoor ? TEXT(", indoor") : TEXT(""), MusicRaw);
	if (bEncounter)
	{
		Text += bLocksScreen ? TEXT("  LOCKED FIGHT") : TEXT("  screenlock script");
	}
	if (bLockBarriersUp)
	{
		Text += TEXT("  [EXITS LOCKED]");
	}
	if (VisionValues.Num() > 0)
	{
		Text += TEXT("  visions:");
		for (int32 V : VisionValues)
		{
			Text += FString::Printf(TEXT(" %d"), V);
		}
	}
	return Text;
}

void ADinkScreenVolume::SetLockBarriers(bool bLocked)
{
	if (bLocked == bLockBarriersUp && (!bLocked || LockBarriers.Num() > 0))
	{
		return;
	}
	bLockBarriersUp = bLocked;
	if (bLocked && LockBarriers.Num() == 0)
	{
		// Edges N, E, S, W in map pixels, the same order as EdgeWalls.
		static const FVector2D EdgePx[4][2] = { {{0, 0}, {600, 0}}, {{600, 0}, {600, 400}}, {{600, 400}, {0, 400}}, {{0, 400}, {0, 0}} };
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		constexpr double HeightCm = 160.0;
		constexpr double ThicknessCm = 30.0;
		for (int32 E = 0; E < 4; ++E)
		{
			const bool bHasWall = EdgeWalls.IsValidIndex(E) && EdgeWalls[E] && EdgeWalls[E]->GetCollisionEnabled() != ECollisionEnabled::NoCollision;
			if (bHasWall)
			{
				continue; // the original cannot leave through that edge anyway
			}
			const FVector A = DinkLayout::MapPixelToUnreal(Corners, EdgePx[E][0].X, EdgePx[E][0].Y);
			const FVector B = DinkLayout::MapPixelToUnreal(Corners, EdgePx[E][1].X, EdgePx[E][1].Y);
			const FVector Along = (B - A) * FVector(1, 1, 0);
			UStaticMeshComponent* Slab = NewObject<UStaticMeshComponent>(this, *FString::Printf(TEXT("LockBarrier_%d"), E));
			Slab->SetMobility(EComponentMobility::Movable);
			Slab->SetStaticMesh(Cube);
			Slab->SetCollisionProfileName(DinkCollision::ProfileHardSolid);
			Slab->SetCanEverAffectNavigation(false);
			Slab->SetupAttachment(RootComponent);
			Slab->RegisterComponent();
			// The cube is 100 cm: scale it to the edge's length, the slab's thickness and height.
			Slab->SetWorldLocationAndRotation((A + B) * 0.5 + FVector(0, 0, HeightCm * 0.5), FRotator(0.0, Along.Rotation().Yaw, 0.0));
			Slab->SetWorldScale3D(FVector(Along.Size() / 100.0, ThicknessCm / 100.0, HeightCm / 100.0));
			LockBarriers.Add(Slab);
		}
	}
	for (UStaticMeshComponent* Slab : LockBarriers)
	{
		if (Slab)
		{
			Slab->SetVisibility(bLocked);
			Slab->SetHiddenInGame(!bLocked);
			Slab->SetCollisionEnabled(bLocked ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
		}
	}
}

void ADinkScreenVolume::SetInteriorWallVisualsHidden(bool bHideVisuals)
{
	bInteriorWallVisualsHidden = bHideVisuals;
	ApplyInteriorWallVisibility();
}

void ADinkScreenVolume::RefreshInteriorWallVisuals(const ADinkScreenVolume* ActiveScreen)
{
	const bool bIndoorOwner = bIndoor && ScreenNumber > 0 && ActiveScreen &&
		ActiveScreen->bIndoor && ActiveScreen->ScreenNumber > 0 && ActiveScreen->GetWorld() == GetWorld();
	const bool bJoinedInterior = bIndoorOwner && !InteriorId.IsNone() && !Sheet.IsNone() &&
		Sheet.ToString().StartsWith(TEXT("interior:")) && InteriorId == ActiveScreen->InteriorId && Sheet == ActiveScreen->Sheet;
	bInteriorWallContextVisible = bIndoorOwner && (ActiveScreen == this || bJoinedInterior);
	ApplyInteriorWallVisibility();
}

void ADinkScreenVolume::ApplyInteriorWallVisibility()
{
	const bool bHidden = bInteriorWallVisualsHidden || !bInteriorWallContextVisible;
	for (UStaticMeshComponent* Visual : InteriorWallVisuals)
	{
		if (Visual) Visual->SetHiddenInGame(bHidden);
	}
}

void ADinkScreenVolume::BeginPlay()
{
	Super::BeginPlay();
	if (UDinkGreyboxSubsystem* Greybox = GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>())
	{
		Greybox->RegisterScreen(this);
	}
	// Interiors sit on their own in the sky: show their closed edges as plain walls so a room reads as a
	// room (presentation only; the invisible edge-wall boxes already do the blocking).
	if (bIndoor)
	{
		UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
		for (int32 E = 0; Cube && E < EdgeWalls.Num(); ++E)
		{
			const UBoxComponent* Wall = EdgeWalls[E];
			if (!Wall || Wall->GetCollisionEnabled() == ECollisionEnabled::NoCollision)
			{
				continue;
			}
			UStaticMeshComponent* Shown = NewObject<UStaticMeshComponent>(this, *FString::Printf(TEXT("InteriorWall_%d"), E));
			Shown->SetMobility(EComponentMobility::Movable);
			Shown->SetStaticMesh(Cube);
			Shown->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Shown->SetCanEverAffectNavigation(false);
			Shown->SetHiddenInGame(bInteriorWallVisualsHidden || !bInteriorWallContextVisible);
			InteriorWallVisuals.Add(Shown);
			Shown->SetupAttachment(RootComponent);
			Shown->RegisterComponent();
			Shown->SetWorldLocationAndRotation(Wall->GetComponentLocation(), Wall->GetComponentRotation());
			Shown->SetWorldScale3D(Wall->GetScaledBoxExtent() / 50.0);
		}
	}
}

void ADinkScreenVolume::EndPlay(const EEndPlayReason::Type Reason)
{
	if (UWorld* World = GetWorld())
	{
		if (UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>())
		{
			Greybox->UnregisterScreen(this);
		}
	}
	Super::EndPlay(Reason);
}
