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
DECLARE_MULTICAST_DELEGATE_OneParam(FDinkScreenChanged, ADinkScreenVolume*);

/**
 * Play-time helper for the imported greybox: knows every screen volume, tracks which original
 * screen the player is on (shown on screen while playing), applies &vision per screen, and keeps
 * a short post-warp cooldown so a warp cannot fire twice in a row.
 *
 * Console commands (PIE / game):
 *   dink.Where                       print the current screen
 *   dink.Goto <screen> [x y]         teleport the player to a screen (map pixels, default centre)
 *   dink.Vision <screen> <value>     show the placements of that &vision value on a screen
 *   dink.ScreenInfo 0|1              on-screen display of the current screen (default 1)
 */


UCLASS()
class DINKCORE_API UDinkGreyboxSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	FDinkScreenChanged OnScreenChanged;
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
	bool GotoScreen(int32 ScreenNumber, float MapX = 300.f, float MapY = 200.f);

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

	bool CanWarp(const APawn* Pawn) const;
	/** Blocks nested overlaps while TeleportTo synchronously updates the pawn's overlaps. */
	bool BeginWarp(APawn* Pawn);
	void EndWarp(APawn* Pawn);
	void NotifyWarped(APawn* Pawn, const UDinkWarpComponent& Warp);

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
	TArray<TWeakObjectPtr<ADinkScreenVolume>> Screens;
	TMap<int32, TArray<TWeakObjectPtr<ADinkPlaceholderActor>>> VisionPlaceholders;
	TMap<TWeakObjectPtr<const APawn>, double> LastWarpTime;
	TSet<TWeakObjectPtr<const APawn>> WarpingPawns;
	TWeakObjectPtr<ADinkScreenVolume> CurrentScreen;
	int32 LockedScreen = 0;
	double NextScreenCheck = 0.0;
};
