#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkGreyboxSubsystem.generated.h"

class ADinkScreenVolume;
class ADinkPlaceholderActor;
class UDinkWarpComponent;
class APawn;
class ACharacter;
class UPrimitiveComponent;
class UProceduralMeshComponent;
class ADinkGreyboxScreen;
DECLARE_MULTICAST_DELEGATE_OneParam(FDinkScreenChanged, ADinkScreenVolume*);
/** A map.dat warp moved the player (UDinkAudioLifeSubsystem plays the warp's sound, dink.cpp:15343-15345). */
DECLARE_MULTICAST_DELEGATE_TwoParams(FDinkWarped, APawn*, const UDinkWarpComponent&);

/**
 * Play-time helper for the imported greybox: knows every screen volume, tracks which original
 * screen the player is on (optionally shown by the developer overlay), applies &vision per screen, and keeps
 * a short post-warp cooldown so a warp cannot fire twice in a row.
 *
 * Console commands (PIE / game):
 *   dink.Where                       print the current screen
 *   dink.Goto <screen> [x y]         teleport the player to a screen (map pixels, default centre)
 *   dink.Vision <screen> <value>     show the placements of that &vision value on a screen
 *   dink.ScreenInfo 0|1              on-screen display of the current screen (default 0; developer opt-in)
 */


UCLASS()
class DINKCORE_API UDinkGreyboxSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	FDinkScreenChanged OnScreenChanged;
	FDinkWarped OnWarped;
	void RegisterScreen(ADinkScreenVolume* Screen);
	void UnregisterScreen(ADinkScreenVolume* Screen);
	void RegisterVisionPlaceholder(ADinkPlaceholderActor* Placeholder);

	/** The screen whose quad contains Location (exact test), or nullptr. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Greybox")
	ADinkScreenVolume* FindScreenAt(const FVector& Location) const;

	UFUNCTION(BlueprintCallable, Category = "Dink|Greybox")
	ADinkScreenVolume* FindScreen(int32 ScreenNumber) const;

	/** Shows the placements gated by Value on Screen and hides the other gated ones (0 = default). */
	UFUNCTION(BlueprintCallable, Category = "Dink|Greybox")
	int32 SetScreenVision(int32 ScreenNumber, int32 Value);

	/** Teleports the first local player's pawn to a map pixel of a screen. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Greybox")
	/** Teleports the pawn to a map pixel of a screen. bEvenIntoWalls (a script's load_screen): when the checked teleport refuses the spot
	 *  (the capsule overlaps a wall), the pawn is placed there anyway, as the original places Dink wherever a script puts him. */
	bool GotoScreen(int32 ScreenNumber, float MapX = 300.f, float MapY = 200.f, bool bEvenIntoWalls = false);

	UFUNCTION(BlueprintPure, Category = "Dink|Greybox")
	ADinkScreenVolume* GetCurrentScreen() const { return CurrentScreen.Get(); }
	/**
	 * Looks up the screen under the pawn now instead of at the next check (every 0.25 s) and broadcasts a change. A load
	 * moves the pawn in one step; without this the story saw the old screen for a few frames, "entered" it (mother's scene
	 * and all) and then entered the saved one.
	 */
	void RefreshCurrentScreen();

	/**
	 * Set by the narrative runtime: true while a script carries the pawn through hardness (`move(1, dir, stop, 1)`), when the
	 * original's walk code is not running and so no warp can trigger (special_block, dink.cpp D:15337).
	 */
	TFunction<bool(const APawn*)> WarpSuppressed;

	/**
	 * screenlock(1/0) on an original screen: raises or drops that screen volume's exit barriers. Only one
	 * screen is locked at a time (the original keeps one flag and clears it on every screen load), so
	 * locking a screen unlocks any other. Returns false if the screen is not in this world.
	 */
	UFUNCTION(BlueprintCallable, Category = "Dink|Greybox")
	bool SetScreenLocked(int32 ScreenNumber, bool bLocked);

	/** The screen whose exits are locked, 0 if none. */
	UFUNCTION(BlueprintPure, Category = "Dink|Greybox")
	int32 GetLockedScreen() const { return LockedScreen; }

	/**
	 * A script redrew an original screen's hardness (draw_hard_sprite / draw_hard_map, run by DinkNarrative's UDinkGameplay): its solid
	 * collision follows. Changes is 600 x 400 map pixels, row-major: 0 as baked, 1 now solid, 2 no longer solid. The screen's baked
	 * CollisionSolid (one complex-as-simple trimesh: ground plus 3 m prisms) cannot lose a part, so it is switched off and a runtime mesh
	 * built the same way (ground plus prisms of the baked solid pixels, the changes applied) takes over until RestoreScreenSolidCollision.
	 * False, and nothing done, if the screen is not in this world or its baked collision is already off (a screen with authored collision).
	 */
	bool ApplyScreenSolidChanges(int32 ScreenNumber, const TArray<uint8>& Changes);
	/** The baked solid collision back (a screen load rebuilds the hardness); 0 = every screen. */
	void RestoreScreenSolidCollision(int32 ScreenNumber);
	/** The runtime solid collision of a screen, if ApplyScreenSolidChanges made one (tests). */
	UPrimitiveComponent* GetRuntimeSolidCollision(int32 ScreenNumber) const;
	/** Height of the solid prisms (DinkImport's CollisionHeightM, 3 m), cm. */
	static constexpr float SolidPrismHeightCm = 300.f;

	/**
	 * sp_prop (DinkNarrative's UDinkGameplay::SetPlacementProp, owner decision OD1 of 9 Nov 2026) on a sprite warp: its placement's prop is no
	 * longer 1 (off) or is 1 again (on). special_block runs only for prop 1 (dink.cpp:15337-15341), so a switched-off warp's trigger does not
	 * fire (UDinkWarpComponent::TryWarp, the door retry); its hardbox stays solid. WarpId is the placement's origin text ("S419_P02").
	 * RestoreSpriteWarps (a screen load: load_map reads map.dat's prop anew) switches every one back on.
	 */
	void SetSpriteWarpOn(const FString& WarpId, bool bOn);
	bool IsSpriteWarpOn(const FString& WarpId) const { return !PropOffWarps.Contains(WarpId); }
	void RestoreSpriteWarps() { PropOffWarps.Reset(); }

	bool CanWarp(const APawn* Pawn) const;
	/** Blocks nested overlaps while TeleportTo synchronously updates the pawn's overlaps. */
	bool BeginWarp(APawn* Pawn);
	void EndWarp(APawn* Pawn);
	void NotifyWarped(APawn* Pawn, const UDinkWarpComponent& Warp);
	/** Grows by one with every warp taken (NotifyWarped): the story tells a warp's screen load from an edge crossing by it. */
	int32 GetWarpSerial() const { return WarpSerial; }
	int32 WarpSerial = 0;

	/** Seconds after a warp during which the same pawn cannot warp again. */
	static constexpr double WarpCooldownSeconds = 0.75;

	virtual void Deinitialize() override;

	// UTickableWorldSubsystem
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

private:
    void ObserveDoorMovement(ACharacter* Character);
    void RetryOverlappingDoor();
    UFUNCTION()
    void CaptureDoorMovement(float DeltaSeconds, FVector OldLocation, FVector OldVelocity);
    TWeakObjectPtr<ACharacter> DoorMovementPawn;
    FVector DoorMovementIntent=FVector::ZeroVector;
    FVector DoorMovementLocation=FVector::ZeroVector;
    uint64 DoorMovementFrame=MAX_uint64;
	void UpdateLegacyCardVisibility(int32 ActiveScreenNumber);
	TMap<TWeakObjectPtr<UPrimitiveComponent>, bool> LegacyCardVisibility;
	// perf-stutter (dink.Perf.Fixes): billboard only the cards near the camera, gathered twice a second; the legacy card
	// pass runs in full when the screen changes and every 2 s, not every 0.25 s.
	void FaceNearbyCardsToCamera(UWorld& World);
	TArray<TWeakObjectPtr<class ADinkPlaceholderActor>> BillboardCards;
	FVector BillboardGatherAt = FVector(1e30);
	double NextBillboardGather = 0.0;
	int32 LastLegacyScreen = INDEX_NONE;
	TWeakObjectPtr<const class ADinkScreenVolume> LastWallScreen;
	FName LastWallSheet, LastWallInterior;
	bool bLastWallIndoor = false;
	int32 WallScreenCount = -1;
	// the caches above apply only to the 0.25 s refresh from Tick; an explicit RefreshCurrentScreen (tests, save restore)
	// always walks everything, as before
	bool bTickRefresh = false;
	double NextLegacyFullPass = 0.0;
	TArray<TWeakObjectPtr<ADinkScreenVolume>> Screens;
	TMap<int32, TArray<TWeakObjectPtr<ADinkPlaceholderActor>>> VisionPlaceholders;
	TMap<TWeakObjectPtr<const APawn>, double> LastWarpTime;
	TSet<TWeakObjectPtr<const APawn>> WarpingPawns;
	TWeakObjectPtr<ADinkScreenVolume> CurrentScreen;
	int32 LockedScreen = 0;
	double NextScreenCheck = 0.0;
	/** Sprite warps an sp_prop switched off until the next screen load. */
	TSet<FString> PropOffWarps;

	ADinkGreyboxScreen* FindGreyboxScreen(int32 ScreenNumber) const;
	/** Which map pixels the baked CollisionSolid covers with a prism, by line traces at the pixel centres (computed once per screen). */
	const TBitArray<>* BakedSolidMask(int32 ScreenNumber);
	struct FRuntimeSolid
	{
		TWeakObjectPtr<UProceduralMeshComponent> Mesh;
		TWeakObjectPtr<UPrimitiveComponent> Baked;
	};
	TMap<int32, FRuntimeSolid> RuntimeSolids;
	TMap<int32, TBitArray<>> BakedSolidMasks;
};
