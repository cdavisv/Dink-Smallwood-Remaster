#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "DinkFactTypes.h"
#include "DinkFactSubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FDinkFactChangedSignature, FName, Fact, int32, OldValue, int32, NewValue);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FDinkFactsResetSignature);

/** Native change delegate: (fact, old value, new value). */
DECLARE_MULTICAST_DELEGATE_ThreeParams(FDinkFactChangedNative, FName /*Fact*/, int32 /*OldValue*/, int32 /*NewValue*/);
DECLARE_MULTICAST_DELEGATE(FDinkFactsResetNative);

/** One row of the initial-values table. */
USTRUCT(BlueprintType)
struct DINKCORE_API FDinkFactDefinition
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Facts")
	FName Name;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Facts")
	int32 InitialValue = 0;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Facts")
	EDinkFactKind Kind = EDinkFactKind::Story;
};

/**
 * Quest/story state as integer facts, the remaster's port of the original DinkC global
 * variables (make_global_int in story/main.c).
 *
 * Facts are keyed by the ORIGINAL variable name without '&' (story, old_womans_duck, s2-nad).
 * Names are case-insensitive (FName), and every entry point also accepts a leading '&'.
 * Reading an undeclared fact returns 0; writing one creates it as EDinkFactKind::Undeclared
 * (expanded content may add facts; a warning is logged so typos show up).
 *
 * On Initialize the subsystem loads Content/Dink/Data/Facts/dink_globals.csv (generated from
 * the data repo, see AGENTS.md) and resets every fact to its initial value, as a new game in
 * the original does. Save/load goes through UDinkSaveGame, which calls GetAllFacts/RestoreFacts.
 *
 * Engine-kind facts (strength, life, gold...) exist here for name parity with the original
 * scripts. The player's UDinkStatsComponent is the authority for those values and mirrors
 * them into this subsystem when its bMirrorToFacts is set.
 */
UCLASS()
class DINKCORE_API UDinkFactSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	// USubsystem
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;

	/** Absolute path of the shipped initial-values table (ProjectContentDir/Dink/Data/Facts/dink_globals.csv). */
	static FString GetDefaultInitialFactsPath();

	/**
	 * Replaces the initial-values table from a CSV file and resets all facts to it.
	 * Format: optional '#' comment lines, a header row starting with "name", then
	 * "name,initial[,kind[,...]]" rows; kind is "story" (default) or "engine".
	 * Returns false (and leaves the current table untouched) on any error.
	 */
	bool LoadInitialFactsFromFile(const FString& Path, FString* OutError = nullptr);

	/** Same as LoadInitialFactsFromFile, from CSV text. */
	bool LoadInitialFactsFromString(const FString& CsvText, FString* OutError = nullptr);

	/** New game: every fact back to its initial value; undeclared facts are dropped. Broadcasts OnFactsReset. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Facts")
	void ResetToInitialValues();

	/** Value of Fact, or 0 if it does not exist. */
	UFUNCTION(BlueprintPure, Category = "Dink|Facts")
	int32 GetFact(FName Fact) const;

	/** True and the value if the fact exists. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Facts")
	bool TryGetFact(FName Fact, int32& OutValue) const;

	UFUNCTION(BlueprintPure, Category = "Dink|Facts")
	bool HasFact(FName Fact) const;

	/** Sets Fact. Broadcasts change delegates only if the value changed. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Facts")
	void SetFact(FName Fact, int32 Value);

	/** Fact += Delta (DinkC "&x += n"); returns the new value. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Facts")
	int32 AddToFact(FName Fact, int32 Delta);

	UFUNCTION(BlueprintPure, Category = "Dink|Facts")
	bool EvaluateCondition(const FDinkFactCondition& Condition) const;

	/** True if every condition holds (an empty list is true). */
	UFUNCTION(BlueprintPure, Category = "Dink|Facts")
	bool EvaluateAll(const TArray<FDinkFactCondition>& Conditions) const;

	/** Current values of every fact. */
	const TMap<FName, int32>& GetAllFacts() const { return Values; }

	/** Initial-values table as loaded. */
	const TMap<FName, FDinkFactDefinition>& GetDefinitions() const { return Definitions; }

	UFUNCTION(BlueprintPure, Category = "Dink|Facts")
	EDinkFactKind GetFactKind(FName Fact) const;

	/**
	 * Load path: resets to initial values, then overlays Saved. Facts in the save that are not
	 * in the table are kept (as Undeclared). Broadcasts OnFactsReset once, no per-fact events.
	 */
	void RestoreFacts(const TMap<FName, int32>& Saved);

	/** Delegate fired when one specific fact changes. */
	FDinkFactChangedNative& OnFactChangedNative(FName Fact);

	/** Fired for every fact change (native). */
	FDinkFactChangedNative OnAnyFactChangedNative;

	/** Fired after ResetToInitialValues / RestoreFacts (native). */
	FDinkFactsResetNative OnFactsResetNative;

	/** Fired for every fact change (Blueprint). */
	UPROPERTY(BlueprintAssignable, Category = "Dink|Facts")
	FDinkFactChangedSignature OnFactChanged;

	/** Fired after a reset or a load (Blueprint). */
	UPROPERTY(BlueprintAssignable, Category = "Dink|Facts")
	FDinkFactsResetSignature OnFactsReset;

private:
	void BroadcastReset();

	TMap<FName, FDinkFactDefinition> Definitions;
	TMap<FName, int32> Values;
	TMap<FName, FDinkFactChangedNative> PerFactDelegates;
};
