#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DinkStatTypes.h"
#include "DinkRandom.h"
#include "DinkStatsComponent.generated.h"

class UDinkFactSubsystem;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDinkStatsChangedSignature, UDinkStatsComponent*, Component);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDinkDiedSignature, UDinkStatsComponent*, Component);
DECLARE_MULTICAST_DELEGATE_OneParam(FDinkStatsChangedNative, UDinkStatsComponent*);

/**
 * Stats, damage intake, experience, levelling and spell charge for one actor (the player or an
 * enemy). All maths is delegated to DinkRules (DinkCombat.h); this component only holds state,
 * applies results and raises events.
 *
 * Differences from the original's timing, on purpose: damage is applied immediately (the
 * original accumulates sprite.damage and applies it on the target's next brain think), and
 * Life is floored at 0. Death fires when Life drops below 1, as in the original (D:5959-5962).
 *
 * Random source: by default a seeded FDinkStreamRandomSource (seed = RandomSeed). Tests and
 * replays inject their own with SetRandomSource.
 *
 * Fact mirror: with bMirrorToFacts (the player only) the stats and the engine-kind facts
 * strength, defense, magic, life, lifemax, level, exp, gold, magic_level and magic_cost are kept
 * equal in both directions, with the fact store as the one source of truth: every change here is
 * written into UDinkFactSubsystem, and every change of one of those facts (a DinkC/Ink script
 * doing `&gold -= 100`, the narrative layer, a console command) is applied to Stats. After a fact
 * reset or restore (new game, load) Stats are pulled from the facts.
 */
UCLASS(ClassGroup = (Dink), meta = (BlueprintSpawnableComponent))
class DINKCORE_API UDinkStatsComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UDinkStatsComponent();

	/** Current stats. Edit defaults per enemy in data; change at run time through the functions below. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Stats")
	FDinkStats Stats;

	/** Missile formula variant (the base game uses Original). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dink|Stats")
	EDinkFixesLevel FixesLevel = EDinkFixesLevel::Original;

	/** Mirror player stats into the fact subsystem (see class comment). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dink|Stats")
	bool bMirrorToFacts = false;

	/** Seed of the default random source. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dink|Stats")
	int32 RandomSeed = 1997;

	/** Replace the random source (tests, replays). Null restores the default seeded stream. */
	void SetRandomSource(TSharedPtr<IDinkRandomSource> InSource);
	IDinkRandomSource& GetRandomSource();

	/** Explicit fact mirror target; when unset it is found through the owning world's game instance. */
	void SetFactMirrorTarget(UDinkFactSubsystem* InFacts);

	/** Names of the facts the mirror keeps equal to Stats (strength, defense, ... magic_cost). */
	static const TArray<FName>& GetMirroredFactNames();

	/** Writes one mirrored fact's value into Stats; false if Fact is not a mirrored stat. */
	static bool ApplyFactToStats(FDinkStats& InOutStats, FName Fact, int32 Value);

	/** Replaces all stats (load, data setup). Broadcasts a change. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Stats")
	void SetStats(const FDinkStats& NewStats);

	// ---- Damage intake; each returns the life actually lost ----

	/** Hit by a melee attack of AttackerStrength (DinkRules::ResolveMeleeHit). */
	UFUNCTION(BlueprintCallable, Category = "Dink|Combat")
	int32 TakeMeleeHit(int32 AttackerStrength);

	/** Hit by a missile of MissileStrength (DinkRules::ResolveMissileHit). */
	UFUNCTION(BlueprintCallable, Category = "Dink|Combat")
	int32 TakeMissileHit(int32 MissileStrength);

	/**
	 * Contact with a sprite whose touch damage is TouchDamage at game time NowMs. Ignored while the
	 * 400 ms immunity from the previous touch hit lasts (D:15639, 15668).
	 */
	UFUNCTION(BlueprintCallable, Category = "Dink|Combat")
	int32 TakeTouchDamage(int32 TouchDamage, int64 NowMs);

	/** Scripted hurt(): Damage through the defense rule (DinkRules::ApplyDefense). */
	UFUNCTION(BlueprintCallable, Category = "Dink|Combat")
	int32 TakeScriptedDamage(int32 Damage);

	UFUNCTION(BlueprintPure, Category = "Dink|Combat")
	bool IsDead() const { return Stats.Life < 1; }

	/** True while touch damage is ignored. */
	UFUNCTION(BlueprintPure, Category = "Dink|Combat")
	bool IsTouchImmune(int64 NowMs) const { return NowMs < TouchImmuneUntilMs; }

	// ---- Progression ----

	/** Adds experience (capped at 99,999); returns the new total. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Progression")
	int32 AddExperience(int32 Amount);

	UFUNCTION(BlueprintPure, Category = "Dink|Progression")
	bool CanLevelUp() const;

	UFUNCTION(BlueprintPure, Category = "Dink|Progression")
	int32 GetExpForNextLevel() const;

	/** Performs one level-up with the player's choice (DinkRules::ApplyLevelUp). */
	UFUNCTION(BlueprintCallable, Category = "Dink|Progression")
	EDinkLevelUpOutcome LevelUp(EDinkStatChoice Choice);

	UFUNCTION(BlueprintCallable, Category = "Dink|Progression")
	void AddGold(int32 Amount);

	// ---- Magic ----

	/** Arms a spell's cost (spell arm() sets &magic_cost); charge starts from the current level. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Magic")
	void SetMagicCost(int32 Cost);

	/** One 100 ms charge step; does nothing while bInventoryOpen (D:5937). */
	UFUNCTION(BlueprintCallable, Category = "Dink|Magic")
	void TickMagicCharge(bool bInventoryOpen = false);

	UFUNCTION(BlueprintPure, Category = "Dink|Magic")
	bool CanCastSpell() const;

	/** If charged, empties the charge and returns true. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Magic")
	bool TryCastSpell();

	// ---- Events ----

	UPROPERTY(BlueprintAssignable, Category = "Dink|Stats")
	FDinkStatsChangedSignature OnStatsChanged;

	UPROPERTY(BlueprintAssignable, Category = "Dink|Stats")
	FDinkDiedSignature OnDied;

	FDinkStatsChangedNative OnStatsChangedNative;
	FDinkStatsChangedNative OnDiedNative;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	int32 LoseLife(int32 Amount);
	void NotifyChanged();
	UDinkFactSubsystem* ResolveFactMirror() const;
	/** Subscribes to the fact subsystem's change and reset events (once per target). */
	void BindFactMirror(UDinkFactSubsystem* Facts);
	void UnbindFactMirror();
	void HandleFactChanged(FName Fact, int32 OldValue, int32 NewValue);
	void HandleFactsReset();

	TSharedPtr<IDinkRandomSource> RandomSource;
	TWeakObjectPtr<UDinkFactSubsystem> FactMirror;
	TWeakObjectPtr<UDinkFactSubsystem> BoundFacts;
	FDelegateHandle FactChangedHandle;
	FDelegateHandle FactsResetHandle;
	/** True while Stats are being written into the facts (ignore the echo). */
	bool bWritingFacts = false;
	int64 TouchImmuneUntilMs = TNumericLimits<int64>::Lowest();
};
