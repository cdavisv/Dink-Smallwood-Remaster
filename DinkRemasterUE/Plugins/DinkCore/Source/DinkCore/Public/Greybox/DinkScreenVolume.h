#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DinkLayout.h"
#include "DinkScreenVolume.generated.h"

class UBoxComponent;
class UStaticMeshComponent;

/**
 * One original screen (600x400 px of the 1997 map). The screen survives the remaster as the
 * logical unit for music, enemy reset, quest-state variants (&vision) and locked fights
 * (REMASTER_PLAN section 2). Its true footprint is the convex quad Corners (the layout is a rubber
 * sheet, so screens are slightly non-rectangular); the box component is only the bounding box,
 * for the editor and for broad-phase queries. Use ContainsWorldLocation for the exact test.
 */
UCLASS()
class DINKCORE_API ADinkScreenVolume : public AActor
{
	GENERATED_BODY()

public:
	ADinkScreenVolume();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	TObjectPtr<UBoxComponent> Bounds;

	/** Original screen number 1..768 (map.dat / &player_map). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	int32 ScreenNumber = 0;

	/** "SCR_412". */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FName ScreenId;

	/** Region key from tools/analyse regions.toml (stonebrook, terris_wilds, ...). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FName Region;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FString RegionName;

	/** Sub-area name (e.g. "Dink's house (burning-house set)"). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FString AreaName;

	/** settlement, wilderness, sea, dungeon, interior. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FName Kind;

	/** Layout sheet (mainland, joppa, darklands, snow_isle, fragments, interior:INT_nnn). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FName Sheet;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	bool bIndoor = false;

	/** Raw music value of the screen (N or N-1000 plays N.mid; 0 none; see tools/dinkex). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	int32 MusicRaw = 0;

	/** none, stop or play. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FName MusicAction;

	/** Original file the engine would play (sound/N.mid or .ogg), empty if none. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FString MusicFile;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FName BaseScript;

	/** A `screenlock` script runs on this screen (tools/analyse encounters.json). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	bool bEncounter = false;

	/** The screenlock actually locks the exits (screenlock(1)). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	bool bLocksScreen = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	TArray<FName> EncounterScripts;

	/** Interior set (INT_nnn) for indoor screens, None outdoors. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FName InteriorId;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FString InteriorName;

	/** Non-zero &vision values that gate placements on this screen. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	TArray<int32> VisionValues;

	/** For each vision value, the DinkC assignments that select it ("s1-h1-s:6 [(&story == 3)]"). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	TArray<FString> VisionRules;

	/** Screen corners in world metres (x east, y south). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	FDinkScreenCorners Corners;

	/**
	 * Invisible walls on the screen edges (north, east, south, west) that the player must not
	 * cross: where the grid neighbour is missing, on another layout sheet, or not part of this
	 * import. The original cannot leave a screen towards a missing neighbour either.
	 */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Screen")
	TArray<TObjectPtr<UBoxComponent>> EdgeWalls;

	/**
	 * Locked fight (DinkC screenlock(1), D:10083): the original clamps Dink at the screen edge instead of
	 * loading the neighbour (did_player_cross_screen, D:14049). Here: a blocking barrier on every edge that
	 * has no edge wall of its own (the open exits), visible as a grey placeholder slab (the engine's basic cube) (the plan's thorn
	 * barrier comes later). Created on first use; screenlock(0) or a screen load (load_map resets
	 * screenlock, D:1016) removes it.
	 */
	UFUNCTION(BlueprintCallable, Category = "Dink|Screen")
	void SetLockBarriers(bool bLocked);

	UFUNCTION(BlueprintPure, Category = "Dink|Screen")
	bool AreLockBarriersUp() const { return bLockBarriersUp; }

	/** The barrier slabs (one per open edge; empty until the screen was first locked). */
	UPROPERTY(Transient, VisibleInstanceOnly, BlueprintReadOnly, Category = "Dink|Screen")
	TArray<TObjectPtr<UStaticMeshComponent>> LockBarriers;

	/** Hide presentation-only indoor cubes when authored art replaces this screen.
	 * Safe before BeginPlay and for already-created visuals; physical edge walls are untouched. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Screen")
	void SetInteriorWallVisualsHidden(bool bHideVisuals);

	/** Exact test against the screen quad (ignores Z). */
	UFUNCTION(BlueprintPure, Category = "Dink|Screen")
	bool ContainsWorldLocation(const FVector& Location) const;

	/** Map pixel (0..600, 0..400) to world location on this screen. */
	UFUNCTION(BlueprintPure, Category = "Dink|Screen")
	FVector MapPixelToWorld(float MapX, float MapY) const;

	/** One-line description for logs and the on-screen display. */
	FString Describe() const;

protected:
	bool bInteriorWallVisualsHidden = false;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> InteriorWallVisuals;

	bool bLockBarriersUp = false;
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
};
