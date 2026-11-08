#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "DinkSaveGame.h"
#include "DinkSaveSubsystem.generated.h"

/** Fired after a snapshot was captured (add module state to Save->SubsystemState). */
DECLARE_MULTICAST_DELEGATE_OneParam(FDinkSaveCapturedNative, UDinkSaveGame* /*Save*/);
/** Fired after a snapshot was applied (restore module state from Save->SubsystemState). */
DECLARE_MULTICAST_DELEGATE_OneParam(FDinkSaveAppliedNative, const UDinkSaveGame* /*Save*/);

/**
 * Save and load for the running game: gathers the fact and world-state subsystems of this game
 * instance plus the player actor's UDinkStatsComponent / UDinkInventoryComponent into a
 * UDinkSaveGame and back.
 *
 * The original has 10 save slots at the save machines plus quicksave/autosave in the HD
 * version; slot naming is the caller's business here.
 */
UCLASS()
class DINKCORE_API UDinkSaveSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	/** Builds the context for this game instance and Player (Player may be null: no stats/inventory). */
	FDinkSaveContext MakeContext(AActor* Player) const;

	/** Captures the current game. Player's transform is stored if Player is given. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Save")
	UDinkSaveGame* CaptureSnapshot(AActor* Player, int32 CurrentScreen);

	/** Applies Save to this game instance and Player (moves Player to the saved transform). */
	UFUNCTION(BlueprintCallable, Category = "Dink|Save")
	bool ApplySnapshot(UDinkSaveGame* Save, AActor* Player);

	UFUNCTION(BlueprintCallable, Category = "Dink|Save")
	bool SaveToSlot(const FString& SlotName, AActor* Player, int32 CurrentScreen);

	/** Loads, migrates and applies. Returns the loaded save (nullptr on failure). */
	UFUNCTION(BlueprintCallable, Category = "Dink|Save")
	UDinkSaveGame* LoadFromSlot(const FString& SlotName, AActor* Player);

	/** Modules outside DinkCore (DinkNarrative) store their state through these. */
	FDinkSaveCapturedNative OnSnapshotCaptured;
	FDinkSaveAppliedNative OnSnapshotApplied;
};
