#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "DinkStatTypes.h"
#include "DinkInventoryComponent.h"
#include "DinkWorldStateSubsystem.h"
#include "DinkSaveGame.generated.h"

class UDinkFactSubsystem;
class UDinkWorldStateSubsystem;
class UDinkStatsComponent;
class UDinkInventoryComponent;

/** The live objects a save is captured from and applied to. Any pointer may be null (that part is skipped). */
struct DINKCORE_API FDinkSaveContext
{
	UDinkFactSubsystem* Facts = nullptr;
	UDinkWorldStateSubsystem* WorldState = nullptr;
	UDinkStatsComponent* PlayerStats = nullptr;
	UDinkInventoryComponent* PlayerInventory = nullptr;
};

/**
 * A saved game. Same model as the original save (player_info in dink.h): player stats,
 * inventory, the global variables and the per-screen placement overrides, plus where the player
 * stands. The 3D world itself is never serialised; it is rebuilt from data + this.
 *
 * Versioning: SaveVersion is written with every save. After loading, call
 * MigrateToCurrentVersion(), which runs one step per version (FromVersion -> FromVersion + 1) up
 * to CurrentVersion and refuses saves from a newer build. Add a step every time the layout or
 * meaning of a field changes, and bump CurrentVersion. Never edit an existing step. Changing a
 * default value of a saved struct field also needs a step: values equal to the default may not
 * be written, so old saves would silently pick up the new default.
 *
 * Version history:
 *   0  Prototype layout: fact keys kept the DinkC '&' prefix ("&story").
 *   1  Fact keys are the bare original names ("story").
 *   2  Adds SubsystemState (text blobs of other modules, e.g. the narrative runtime's Ink state);
 *      older saves simply have none. (current)
 */
UCLASS(BlueprintType)
class DINKCORE_API UDinkSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	static constexpr int32 CurrentVersion = 2;

	UDinkSaveGame();

	/**
	 * Layout version this object holds. New instances are CurrentVersion; the class default is
	 * INDEX_NONE on purpose: tagged-property serialisation may skip values equal to the class
	 * default, so the default must never be a real version or old saves would load as current.
	 */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Save")
	int32 SaveVersion = INDEX_NONE;

	/** When the save was written (UTC). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Save")
	FDateTime SavedAtUtc;

	/** All fact values by original name (no '&'). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Save")
	TMap<FName, int32> Facts;

	/** Per-placement overrides (the original spmap types). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Save")
	TArray<FDinkWorldOverride> Overrides;

	/** Last exit time per screen (the original spmap[].last_time). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Save")
	TArray<FDinkScreenExitTime> ScreenExitTimes;

	/** Game clock in ms (the original g_dinkTick). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Save")
	int64 GameTimeMs = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Save")
	FDinkStats PlayerStats;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Save")
	FDinkInventoryState Inventory;

	/** Original screen number the player is on (&player_map). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Save")
	int32 CurrentScreen = 1;

	/** Player transform in the remaster world. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Save")
	FTransform PlayerTransform;

	/**
	 * Opaque text state of modules DinkCore does not know, keyed by owner (e.g. "narrative": the
	 * DinkNarrative story subsystem's JSON with the Ink state and its script instances). Filled and
	 * read through UDinkSaveSubsystem's capture/apply delegates. Added in version 2.
	 */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Save")
	TMap<FName, FString> SubsystemState;

	/** Copies the state of every non-null object in Context into this save and stamps it CurrentVersion. */
	void CaptureFrom(const FDinkSaveContext& Context);

	/** Pushes this save into every non-null object in Context. The save must be at CurrentVersion. */
	bool ApplyTo(const FDinkSaveContext& Context) const;

	/**
	 * Brings an older save up to CurrentVersion in place. Returns false (save unchanged) if
	 * SaveVersion is negative or newer than this build understands. OutLog lists the steps run.
	 */
	bool MigrateToCurrentVersion(TArray<FString>* OutLog = nullptr);

	/** Serialises to bytes (UGameplayStatics::SaveGameToMemory). */
	static bool SaveToBytes(UDinkSaveGame* Save, TArray<uint8>& OutBytes);

	/** Deserialises from bytes and migrates; nullptr on failure. */
	static UDinkSaveGame* LoadFromBytes(const TArray<uint8>& Bytes, TArray<FString>* OutLog = nullptr);

private:
	/** Step 0 -> 1: strip '&' from fact keys. */
	void MigrateV0ToV1();

	/** Step 1 -> 2: SubsystemState added; older saves have none, so nothing to convert. */
	void MigrateV1ToV2();
};
