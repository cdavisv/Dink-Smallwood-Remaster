#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "DinkExpanded.h"
#include "DinkExpandedWorldSubsystem.generated.h"

class ADinkScreenVolume;
class UDinkWarpComponent;
class UDinkSaveGame;

/** The pack-side and 1997-side triggers of one designed join (overlay actors; no 1997 data changes). */
UCLASS(NotPlaceable, Transient)
class DINKEXPANDED_API ADinkExpandedJoinActor : public AActor
{
	GENERATED_BODY()
public:
	ADinkExpandedJoinActor();
	UPROPERTY(VisibleAnywhere, Category = "Dink|Expanded")
	TObjectPtr<UDinkWarpComponent> Warp;
	/** Join id and side ("in" on the 1997 screen, "out" on the pack screen). */
	UPROPERTY(VisibleAnywhere, Category = "Dink|Expanded")
	FString JoinId;
	UPROPERTY(VisibleAnywhere, Category = "Dink|Expanded")
	FName Side;
	/** Pack fact that must be at least RequiresAtLeast for the "in" side to warp (None = always). */
	FName RequiresFact;
	int32 RequiresAtLeast = 0;
	/** The condition holds (set by UDinkExpandedWorldSubsystem::RefreshJoinConditions). */
	bool bConditionMet = true;
	/** A locked fight on the trigger's own screen (screenlock(1)) closes it, as it closes every exit of that screen (D:14049). */
	virtual void Tick(float DeltaSeconds) override;
};

/**
 * Builds the active content packs into a game world when it begins play (only while the DinkExpanded switch is on; off, the
 * subsystem is not even created): one ADinkScreenVolume per pack screen on its pack sheet (DinkExpanded::LayoutPackScreens, beyond
 * the loaded 1997 world), a greybox ground slab, solid blocks for the hardness rectangles, edge walls where no pack neighbour is, one
 * ADinkPlaceholderActor per placement (origin S<screen>_P<index>, script, so the 1997 director runs it like any placement), and the
 * designed joins' triggers (UDinkWarpComponent, kind "pack_join"). The 1997 actors are only read (their corners), never changed.
 */
UCLASS()
class DINKEXPANDED_API UDinkExpandedWorldSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;

	/** Builds the packs now (OnWorldBeginPlay calls it; tests call it on a test world). Returns the screens built. */
	int32 BuildPacks(UWorld& World);

	/** World corners of the built pack screens. */
	const TMap<int32, FDinkScreenCorners>& GetPackCorners() const { return PackCorners; }
	const TArray<TObjectPtr<AActor>>& GetSpawned() const { return Spawned; }
	ADinkExpandedJoinActor* FindJoin(const FString& JoinId, FName Side) const;

	/** World location of a map pixel on a 1997 screen of this world or a built pack screen (false if neither). */
	bool MapPixelToWorld(int32 Screen, const FVector2D& MapPixel, FVector& OutWorld) const;

	/** Re-evaluates the joins' fact conditions (bound to fact changes while the world runs). */
	void RefreshJoinConditions();

private:
	TMap<int32, FDinkScreenCorners> PackCorners;
	TMap<int32, FDinkScreenCorners> BaseCorners;
	UPROPERTY(Transient)
	TArray<TObjectPtr<AActor>> Spawned;
	UPROPERTY(Transient)
	TArray<TObjectPtr<ADinkExpandedJoinActor>> Joins;
	FDelegateHandle FactHandle;
	bool bBuilt = false;
};

/**
 * Saves made inside a pack: the snapshot's own screen and transform are rewritten to the join's 1997 return point, so a save loads
 * into the 1997 world when the packs are off (or the plugin is gone); the real pack position goes into SubsystemState["expanded"]
 * and is restored on load while the packs are on. Script instances of pack scripts in the narrative state are left out by the
 * 1997 loader when the story does not hold them (UDinkStorySubsystem::LoadStateFromJson).
 */
UCLASS()
class DINKEXPANDED_API UDinkExpandedGameSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()
public:
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** Rewrites a snapshot taken on a pack screen (tests call it directly). Returns true if the save was inside a pack. */
	static bool MakeSaveSafe(UDinkSaveGame* Save, const FDinkExpandedRegistry& Registry, const FTransform& ReturnTransform, int32 ReturnScreen);
	/** The 1997 screen and map pixel a pack screen leads back to (the first join of its pack). */
	static bool FindReturnPoint(const FDinkExpandedRegistry& Registry, int32 PackScreen, int32& OutScreen, FVector2D& OutPoint);

private:
	void HandleCaptured(UDinkSaveGame* Save);
	void HandleApplied(const UDinkSaveGame* Save);
	FDelegateHandle CapturedHandle;
	FDelegateHandle AppliedHandle;
};
