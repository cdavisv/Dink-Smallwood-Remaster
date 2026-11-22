// Neighbour-screen dressing spread over frames (stream perf-stutter, 15 Nov 2026; dink.Perf.Fixes 1).
//
// UDinkEnvironmentSubsystem::ApplyNeighbourFamilies dresses every screen within sight of a newly entered one (town
// houses 160 m, forest and relief 220 m, decals and family meshes 160 m) in the frame the player crosses the screen
// edge: dozens of components registered, water masks loaded synchronously, then a whole-world walk for burnables and
// grass clearings. That frame took 100-200 ms (A15). Here the same per-screen calls run nearest first, with the
// entered screen at once and the others under a ~3 ms budget per frame, and a screen whose water mask or town
// meshes are still loading in the background waits for them (at most 2 s, then it loads them as before). Per screen
// the order is the original's (town, forest, relief, decals, then family meshes), and screens do not read each
// other's dressing, so the dressed result is the same; only the frame it appears in moves. Presentation only.
#include "DinkEnvironmentSubsystem.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkPerfScope.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Engine/AssetManager.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "UObject/Package.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"

static TAutoConsoleVariable<float> CVarDinkNeighbourBudgetMs(TEXT("dink.Perf.NeighbourBudgetMs"), 3.f,
	TEXT("Game-thread milliseconds per frame for dressing the screens around the current one (dink.Perf.Fixes 1). The entered screen is always dressed at once."));

namespace
{
	constexpr double TownRangeCm = 16000.0, ForestRangeCm = 22000.0, ReliefRangeCm = 22000.0, DecalRangeCm = 16000.0, FamilyRangeCm = 16000.0;
	constexpr double MaxWaitSeconds = 2.0;
	// A screen whose ground comes within this distance of the camera can be in view from the play camera (the boom
	// looks over the current screen into its neighbours): it is dressed at once, whatever the budget or the prefetch.
	constexpr double InViewCm = 7000.0;

	FString MaskObjectPath(int32 ScreenNumber)
	{
		return FString::Printf(TEXT("/Game/Dink/_Generated/Screens/SCR_%03d/T_GroundMask_SCR_%03d.T_GroundMask_SCR_%03d"), ScreenNumber, ScreenNumber, ScreenNumber);
	}
}

void UDinkEnvironmentSubsystem::PrefetchTownMeshes()
{
	if (TownPrefetch.IsValid() || TownScreens.IsEmpty()) return;
	TArray<FSoftObjectPath> Paths;
	TSet<FString> Seen;
	for (const TPair<int32, FDinkTownScreen>& Pair : TownScreens)
		for (const FDinkTownModule& M : Pair.Value.Modules)
		{
			if (Seen.Contains(M.Mesh)) continue;
			Seen.Add(M.Mesh);
			const FString Package = M.Mesh.StartsWith(TEXT("/")) ? M.Mesh : TEXT("/Game/Dink/Photoreal/TownExteriors/") + M.Mesh;
			if (FPackageName::DoesPackageExist(Package)) Paths.Emplace(Package + TEXT(".") + FPackageName::GetShortName(Package));
		}
	if (!Paths.IsEmpty()) TownPrefetch = UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths);
}

bool UDinkEnvironmentSubsystem::IsNeighbourReady(int32 ScreenNumber) const
{
	if (TownScreens.Contains(ScreenNumber) && !TownApplied.Contains(ScreenNumber) && TownPrefetch.IsValid() && !TownPrefetch->HasLoadCompleted()) return false;
	if (const TSharedPtr<FStreamableHandle>* Mask = MaskPrefetch.Find(ScreenNumber); Mask && Mask->IsValid() && !(*Mask)->HasLoadCompleted()) return false;
	return true;
}

void UDinkEnvironmentSubsystem::QueueNeighbourScreens(const FVector& Around, int32 CurrentNumber)
{
	PrefetchTownMeshes();
	PendingNeighbours.Reset();
	PendingCurrentScreen = CurrentNumber;
	const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
	for (int32 Index = 0; Index < Screens.Num(); ++Index)
	{
		const FScreenInfo& Screen = Screens[Index];
		const double DistSq = FVector::DistSquared2D(Screen.Centre, Around);
		if (DistSq >= FMath::Square(FMath::Max(ForestRangeCm, ReliefRangeCm))) continue;
		PendingNeighbours.Add({Index, DistSq, Now});
		// the shore mask of a water screen still to be dressed: load it in the background now
		if (!ReliefApplied.Contains(Screen.Number) && WaterTileRects.Contains(Screen.Number) && WaterTileMaterial && !MaskPrefetch.Contains(Screen.Number))
		{
			const FString Path = MaskObjectPath(Screen.Number);
			if (FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(Path)))
				MaskPrefetch.Add(Screen.Number, UAssetManager::GetStreamableManager().RequestAsyncLoad(FSoftObjectPath(Path)));
		}
	}
	PendingNeighbours.Sort([](const FPendingNeighbour& A, const FPendingNeighbour& B) { return A.DistSq < B.DistSq; });
	bNeighbourFollowUp = true;
	NeighbourQueueFrame = GFrameCounter;
}

void UDinkEnvironmentSubsystem::ApplyNeighbourScreen(const FScreenInfo& Screen, double DistSq)
{
	DINK_PERF_SCOPE(Dink_Env_ApplyNeighbourScreen);
	// the radii and conditions of ApplyNeighbourFamilies, for one screen
	if (!TownScreens.IsEmpty() && DistSq < FMath::Square(TownRangeCm)) ApplyTownHouses(Screen.Number, Screen.Corners);
	if (!ForestTrees.IsEmpty() && DistSq < FMath::Square(ForestRangeCm)) ApplyForest(Screen.Number, Screen.Corners);
	if ((!ReliefRocks.IsEmpty() || !WaterTileRects.IsEmpty()) && DistSq < FMath::Square(ReliefRangeCm)) ApplyRelief(Screen.Number, Screen.Corners);
	if (!DecalClasses.IsEmpty() && DistSq < FMath::Square(DecalRangeCm)) ApplyDecals(Screen.Number);
	UDinkArtFamilySubsystem* Families = GetWorld()->GetSubsystem<UDinkArtFamilySubsystem>();
	if (Families && Families->IsReady() && DistSq < FMath::Square(FamilyRangeCm) && !Families->IsScreenApplied(Screen.Number)) Families->ApplyScreen(Screen.Number);
	MaskPrefetch.Remove(Screen.Number);   // the texture is referenced by the sheet's material now (or not needed)
}

void UDinkEnvironmentSubsystem::DrainNeighbourScreens()
{
	if (PendingNeighbours.IsEmpty() && !bNeighbourFollowUp) return;
	DINK_PERF_SCOPE(Dink_Env_DrainNeighbours);
	const double Start = FPlatformTime::Seconds();
	const double Budget = FMath::Max(0.0, double(CVarDinkNeighbourBudgetMs.GetValueOnGameThread())) / 1000.0;
	const double Now = GetWorld()->GetTimeSeconds();
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	const FVector2D Camera = PC && PC->PlayerCameraManager ? FVector2D(PC->PlayerCameraManager->GetCameraLocation()) : FVector2D(Screens[PendingNeighbours.IsEmpty() ? 0 : PendingNeighbours[0].ScreenIndex].Centre);
	auto InView = [&](const FPendingNeighbour& Item)
	{
		return ScreenBounds.IsValidIndex(Item.ScreenIndex) && ScreenBounds[Item.ScreenIndex].ComputeSquaredDistanceToPoint(Camera) < FMath::Square(InViewCm);
	};
	bool bOverBudget = false, bDressedSeen = false;
	DinkPerf::GLateInViewDressed = 0;
	for (int32 I = 0; I < PendingNeighbours.Num();)
	{
		const FPendingNeighbour Item = PendingNeighbours[I];
		const FScreenInfo& Screen = Screens[Item.ScreenIndex];
		const bool bCurrent = Screen.Number == PendingCurrentScreen;
		const bool bSeen = InView(Item);
		const bool bForce = bCurrent || bSeen || Now - Item.Since > MaxWaitSeconds;
		// past the budget only what can be seen is still dressed this frame
		if ((bOverBudget && !bSeen && !bCurrent) || (!bForce && !IsNeighbourReady(Screen.Number))) { ++I; continue; }
		PendingNeighbours.RemoveAt(I);
		ApplyNeighbourScreen(Screen, Item.DistSq);
		bDressedSeen |= bCurrent || bSeen;
		if (bSeen && !bCurrent && GFrameCounter != NeighbourQueueFrame) ++DinkPerf::GLateInViewDressed;
		bOverBudget = FPlatformTime::Seconds() - Start > Budget;
	}
	if (bDressedSeen)
	{
		// what master did right after dressing, now for the screens the camera can see: their burnables and the grass
		// clearings of their low props and decals, before UpdateGrass builds cells over them later this tick
		FindBurnables();
		if (!bGrassSourcesStale) GatherGrassClears();
	}
	DinkPerf::GPendingInView = 0;
	for (const FPendingNeighbour& Item : PendingNeighbours) DinkPerf::GPendingInView += InView(Item);
	if (!PendingNeighbours.IsEmpty()) return;
	if (PendingNeighbours.IsEmpty() && bNeighbourFollowUp)
	{
		// what the entry frame did after dressing: burnables and the clearings of the props dressed just now
		bNeighbourFollowUp = false;
		FindBurnables();
		if (!bGrassSourcesStale) GatherGrassClears();
	}
}

namespace { constexpr double ScreenGridCm = 2500.0; }

const TArray<int32>& UDinkEnvironmentSubsystem::ScreensNear(const FVector2D& WorldXY) const
{
	static const TArray<int32> None;
	if (ScreenGridCount != ScreenBounds.Num())
	{
		ScreenGrid.Reset();
		for (int32 Index = 0; Index < ScreenBounds.Num(); ++Index)
		{
			const FBox2D& B = ScreenBounds[Index];
			if (!B.bIsValid) continue;
			const int32 X0 = FMath::FloorToInt32(B.Min.X / ScreenGridCm), X1 = FMath::FloorToInt32(B.Max.X / ScreenGridCm);
			const int32 Y0 = FMath::FloorToInt32(B.Min.Y / ScreenGridCm), Y1 = FMath::FloorToInt32(B.Max.Y / ScreenGridCm);
			for (int32 Y = Y0; Y <= Y1; ++Y)
				for (int32 X = X0; X <= X1; ++X) ScreenGrid.FindOrAdd(FIntPoint(X, Y)).Add(Index);   // ascending: indices in order
		}
		ScreenGridCount = ScreenBounds.Num();
	}
	const TArray<int32>* Found = ScreenGrid.Find(FIntPoint(FMath::FloorToInt32(WorldXY.X / ScreenGridCm), FMath::FloorToInt32(WorldXY.Y / ScreenGridCm)));
	return Found ? *Found : None;
}

void UDinkEnvironmentSubsystem::PreloadScatterMaterials()
{
	// BuildGrassCell swaps each grass material for its "_Scatter" twin; loading the twin there stalled the first cell
	// built after the start (79 ms in the 15 Nov editor benchmark). Same lookup, once, before the first cell.
	if (bScatterPreloaded) return;
	bScatterPreloaded = true;
	DINK_PERF_SCOPE(Dink_Env_PreloadScatter);
	for (const TArray<TObjectPtr<UStaticMesh>>* List : {&GrassMeshes, &GrassShortMeshes, &GrassDryMeshes, &GrassRankMeshes, &AccentMeshes})
		for (const UStaticMesh* Mesh : *List)
		{
			if (!Mesh) continue;
			for (const FStaticMaterial& Slot : Mesh->GetStaticMaterials())
			{
				const UMaterialInterface* Authored = Slot.MaterialInterface;
				if (!Authored) continue;
				const FString Twin = Authored->GetOutermost()->GetName() + TEXT("_Scatter");
				TObjectPtr<UMaterialInterface>& Cached = ScatterMaterials.FindOrAdd(Twin);
				if (!Cached && FPackageName::DoesPackageExist(Twin))
					Cached = LoadObject<UMaterialInterface>(nullptr, *(Twin + TEXT(".") + FPackageName::GetShortName(Twin)));
			}
		}
}
