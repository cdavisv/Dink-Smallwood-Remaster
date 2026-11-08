#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "DinkOriginId.h"
#include "DinkWorldStateSubsystem.generated.h"

/**
 * Per-placement override, a 1:1 port of the original editor_type values stored in the save's
 * spmap[screen].type[placement] (bible 04 section 2; source/dink/dink.cpp update_play_changes
 * D:5773-5832 and fix_dead_sprites D:917-959).
 *
 * The numeric values are the original ones and must not change: they are what DinkC scripts
 * pass to editor_type() and what parity tests compare against.
 *
 * For ANY non-zero type the original also replaces the placement's sequence/frame with the
 * stored editor_seq/editor_frame and clears its script (update_play_changes, D:5829-5831), so a
 * spawner must not run the placement's original script or brain while it has an override; the
 * look comes from FDinkWorldOverride::Variant.
 */
UENUM(BlueprintType)
enum class EDinkOverrideType : uint8
{
	/** 0: no override, the placement behaves as authored. */
	None = 0                  UMETA(DisplayName = "0 None"),
	/** 1: removed for good (picked-up item, killed unique enemy). */
	RemovedForever = 1        UMETA(DisplayName = "1 Removed forever"),
	/** 2: visible as a live sprite, no hardness. */
	LiveNoHardness = 2        UMETA(DisplayName = "2 Live, no hardness"),
	/** 3: visible as background, no hardness. */
	BackgroundNoHardness = 3  UMETA(DisplayName = "3 Background, no hardness"),
	/** 4: visible as a live sprite, with hardness. */
	LiveHard = 4              UMETA(DisplayName = "4 Live, hard"),
	/** 5: visible as background, with hardness. */
	BackgroundHard = 5        UMETA(DisplayName = "5 Background, hard"),
	/** 6: removed, returns after 5 minutes. */
	RemovedReturn5Min = 6     UMETA(DisplayName = "6 Removed, back after 5 min"),
	/** 7: removed, returns after 3 minutes. */
	RemovedReturn3Min = 7     UMETA(DisplayName = "7 Removed, back after 3 min"),
	/** 8: removed, returns after 1 minute. */
	RemovedReturn1Min = 8     UMETA(DisplayName = "8 Removed, back after 1 min"),
};

/** One stored override. */
USTRUCT(BlueprintType)
struct DINKCORE_API FDinkWorldOverride
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|World")
	FDinkOriginId Origin;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|World")
	EDinkOverrideType Type = EDinkOverrideType::None;

	/** Game-clock time (ms, UDinkWorldStateSubsystem::GetGameTimeMs) when the override was set. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|World")
	int64 SetAtMs = 0;

	/**
	 * Remaster replacement for the original's editor_seq/editor_frame: which visual variant the
	 * placement shows while overridden (e.g. "burnt" for a burned tree). None = default look.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|World")
	FName Variant;

	bool operator==(const FDinkWorldOverride& Other) const
	{
		return Origin == Other.Origin && Type == Other.Type && SetAtMs == Other.SetAtMs && Variant == Other.Variant;
	}
};

/** Last time the player left a screen (needed by the respawn rule). */
USTRUCT(BlueprintType)
struct DINKCORE_API FDinkScreenExitTime
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|World")
	int32 Screen = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|World")
	int64 ExitedAtMs = 0;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDinkOverrideChangedSignature, FDinkOriginId, Origin, EDinkOverrideType, NewType);
DECLARE_MULTICAST_DELEGATE_TwoParams(FDinkOverrideChangedNative, const FDinkOriginId& /*Origin*/, EDinkOverrideType /*NewType*/);

/**
 * World state as "facts plus overrides": the remaster never serialises actors. Every placement
 * converted from the original is spawned as authored, then this table says whether it is gone,
 * hidden for a while, or shown in another state.
 *
 * Game clock: the subsystem keeps its own millisecond clock (the original's g_dinkTick, which is
 * game time and is saved). The game advances it with AdvanceGameTime each frame while play is
 * running; tests set it directly. Wall-clock time is never used.
 *
 * Respawn rule (fix_dead_sprites, dink.cpp D:917-959): when a screen is entered, overrides of
 * type 6/7/8 on it are cleared once the clock is STRICTLY past the reference time + 300/180/60 s.
 * The original's reference time is the last time the player left that screen
 * (update_screen_time, D:1602). Here the reference is the later of that exit time and the time
 * the override was set, which is identical for overrides set while on the screen (the only way
 * the original sets them) and stays safe for overrides set remotely. Type 6 also respawns when
 * the reference is more than 100 s in the future (the original's guard against a clock that
 * went backwards, D:932-933).
 */
UCLASS()
class DINKCORE_API UDinkWorldStateSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	/** Respawn delays of the timed types, from fix_dead_sprites (D:932, 943, 953). */
	static constexpr int64 Respawn5MinMs = 300000;
	static constexpr int64 Respawn3MinMs = 180000;
	static constexpr int64 Respawn1MinMs = 60000;
	/** Type 6 clock-skew guard: dinkTick + 400000 < last_time + 300000 (D:933). */
	static constexpr int64 ClockSkewGuardMs = 100000;

	// ---- Clock ----

	UFUNCTION(BlueprintPure, Category = "Dink|World")
	int64 GetGameTimeMs() const { return GameTimeMs; }

	UFUNCTION(BlueprintCallable, Category = "Dink|World")
	void SetGameTimeMs(int64 NewTimeMs) { GameTimeMs = NewTimeMs; }

	/** Advances the game clock; negative deltas are ignored. */
	UFUNCTION(BlueprintCallable, Category = "Dink|World")
	void AdvanceGameTime(int64 DeltaMs);

	// ---- Overrides ----

	/** Sets (or with Type None, clears) the override of Origin, stamped with the current game time. */
	UFUNCTION(BlueprintCallable, Category = "Dink|World")
	void SetOverride(const FDinkOriginId& Origin, EDinkOverrideType Type, FName Variant = NAME_None);

	UFUNCTION(BlueprintCallable, Category = "Dink|World")
	void ClearOverride(const FDinkOriginId& Origin);

	/** Override type of Origin (None if not overridden). */
	UFUNCTION(BlueprintPure, Category = "Dink|World")
	EDinkOverrideType GetOverrideType(const FDinkOriginId& Origin) const;

	UFUNCTION(BlueprintCallable, Category = "Dink|World")
	bool TryGetOverride(const FDinkOriginId& Origin, FDinkWorldOverride& OutOverride) const;

	/** True if the placement must not be spawned now (type 1, 6, 7 or 8). */
	UFUNCTION(BlueprintPure, Category = "Dink|World")
	bool IsPlacementRemoved(const FDinkOriginId& Origin) const;

	/** All overrides on one screen, sorted by placement. */
	UFUNCTION(BlueprintCallable, Category = "Dink|World")
	TArray<FDinkWorldOverride> GetOverridesOnScreen(int32 Screen) const;

	// ---- Screen visits and respawn ----

	/** Call when the player leaves a screen (port of update_screen_time). */
	UFUNCTION(BlueprintCallable, Category = "Dink|World")
	void NotifyScreenExited(int32 Screen);

	/**
	 * Call when a screen is (re)entered, before its placements spawn (port of fix_dead_sprites).
	 * Clears every timed override on Screen whose time is up; returns the origins cleared.
	 */
	UFUNCTION(BlueprintCallable, Category = "Dink|World")
	TArray<FDinkOriginId> ProcessRespawns(int32 Screen);

	/** Last exit time of Screen, or INDEX_NONE if never left. */
	UFUNCTION(BlueprintPure, Category = "Dink|World")
	int64 GetScreenExitTimeMs(int32 Screen) const;

	// ---- Save support ----

	/** Snapshot of every override, sorted by origin. */
	TArray<FDinkWorldOverride> ExportOverrides() const;
	TArray<FDinkScreenExitTime> ExportScreenExitTimes() const;

	/** Replaces the whole state (load path). Invalid origins and None types are dropped. */
	void ImportState(const TArray<FDinkWorldOverride>& InOverrides, const TArray<FDinkScreenExitTime>& InExitTimes, int64 InGameTimeMs);

	/** New game: no overrides, clock 0. */
	UFUNCTION(BlueprintCallable, Category = "Dink|World")
	void ResetState();

	int32 NumOverrides() const { return Overrides.Num(); }

	// ---- Rules (static, used by tests and by spawners) ----

	/** 300000/180000/60000 for types 6/7/8, INDEX_NONE otherwise. */
	static int64 GetRespawnDelayMs(EDinkOverrideType Type);

	/** Types 1, 6, 7, 8: the placement is absent. */
	static bool IsRemovedType(EDinkOverrideType Type);

	/** Types 6, 7, 8. */
	static bool IsTimedType(EDinkOverrideType Type) { return GetRespawnDelayMs(Type) != INDEX_NONE; }

	/** Types 4 and 5 force hardness on, 2 and 3 force it off; None and removed types return false. */
	static bool ForcesHardness(EDinkOverrideType Type);

	/** Types 3 and 5 turn the placement into background (no brain/script). */
	static bool IsBackgroundType(EDinkOverrideType Type);

	/**
	 * The respawn test for one override, given the screen's last exit time (INDEX_NONE if never)
	 * and the current time. Pure function of its inputs.
	 */
	static bool ShouldRespawn(const FDinkWorldOverride& Override, int64 InScreenExitMs, int64 NowMs);

	/** Fired whenever an override is set, changed or cleared (native). */
	FDinkOverrideChangedNative OnOverrideChangedNative;

	UPROPERTY(BlueprintAssignable, Category = "Dink|World")
	FDinkOverrideChangedSignature OnOverrideChanged;

private:
	void Broadcast(const FDinkOriginId& Origin, EDinkOverrideType Type);

	TMap<FDinkOriginId, FDinkWorldOverride> Overrides;
	TMap<int32, int64> ScreenExitMs;
	int64 GameTimeMs = 0;
};
