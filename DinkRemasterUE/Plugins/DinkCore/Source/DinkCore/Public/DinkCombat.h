#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Math/RandomStream.h"
#include "DinkRandom.h"
#include "DinkStatTypes.h"
#include "DinkCombat.generated.h"

/**
 * The original game's combat and progression maths, ported exactly.
 *
 * Every function cites its source in the original engine (source/dink/dink.cpp in the data
 * repo; "D:n" is the line number used in doc/remaster/bible/04-engine-and-file-formats.md) or
 * in the original DinkC scripts (bin/dink/story). Integer division and the order of random
 * draws are kept, so a scripted IDinkRandomSource reproduces any original roll.
 *
 * These are the "Classic" rules. Re-tuned 3D values belong in data, not in new formulas.
 */
namespace DinkRules
{
	/** &exp is capped here after every gain (add_exp, D:643). */
	inline constexpr int32 MaxExp = 99999;
	/** lraise.c: "if (&level < 32)" raises; at 32 a level-up only resets exp. */
	inline constexpr int32 MaxLevel = 32;
	/** Touch damage gives the player this much immunity (notouch_timer = tick + 400, D:15668). */
	inline constexpr int32 TouchImmunityMs = 400;
	/** A missile hit gives its target this much notouch time (notouch_timer = tick + 100, D:14342). */
	inline constexpr int32 MissileImmunityMs = 100;
	/** Magic charge step (D:5935 runs in the 100 ms status update). */
	inline constexpr int32 MagicTickMs = 100;
	/** Magic resist roll range: random(40, 1) in en-drag.c line 70 and s7-boss.c. */
	inline constexpr int32 MagicResistRange = 40;

	/**
	 * Melee damage before defense, rolled when an attack frame lands
	 * (run_through_tag_list, D:15567):
	 *     strength / 2 + (rand() % ((strength + 1) / 2)) + 1
	 * The original skips the hit entirely when strength is 0 (D:15558); this returns 0 for
	 * strength <= 0 without rolling. Strength 1 always gives 1.
	 */
	DINKCORE_API int32 MeleeBaseDamage(int32 Strength, IDinkRandomSource& Rng);

	/**
	 * Defense subtraction with the pity point (hurt_thing, D:6656-6670):
	 *     if (damage < 1) return 0;            // no roll
	 *     num = damage - defense;
	 *     if (num < 1) num = 0;
	 *     if (num == 0) if ((rand() % 2) + 1 == 1) num = 1;   // 50% chance of 1
	 * Used by melee, touch damage and scripted hurt().
	 */
	DINKCORE_API int32 ApplyDefense(int32 Damage, int32 Defense, IDinkRandomSource& Rng);

	/** A full melee hit: ApplyDefense(MeleeBaseDamage(...)). Draws 1 or 2 values. */
	DINKCORE_API int32 ResolveMeleeHit(int32 AttackerStrength, int32 TargetDefense, IDinkRandomSource& Rng);

	/**
	 * Missile damage (brains 11/17 hitting a sprite, D:14363-14394). No pity point; result >= 0.
	 *     strength == 0 : no damage (D:14363 "if (strength != 0)")
	 *     strength == 1 : 1 - defense
	 *     Original      : strength / 2 + ((rand() % (strength / 2)) + 1) - defense
	 *     Latest fixes  : (int)(strength / 2.0f + (rand() % (int)(strength * 100 / 2.0f)) / 100.0f + 1.0f) - defense
	 * Negative strength returns 0 (undefined in the original).
	 */
	DINKCORE_API int32 ResolveMissileHit(int32 MissileStrength, int32 TargetDefense, IDinkRandomSource& Rng,
		EDinkFixesLevel Fixes = EDinkFixesLevel::Original);

	/**
	 * Touch damage taken by the player inside a sprite's hardbox +-2 px
	 * (run_through_touch_damage_list, D:15629-15680): ApplyDefense(touch_damage, defense).
	 * touch_damage 0 is no damage and -1 only runs the sprite's TOUCH script; both return 0
	 * without rolling. The caller grants TouchImmunityMs of immunity after a hit.
	 */
	DINKCORE_API int32 ResolveTouchDamage(int32 TouchDamage, int32 TargetDefense, IDinkRandomSource& Rng);

	/**
	 * One 100 ms magic charge step (D:5935-5940):
	 *     if (magic_level < magic_cost) { magic_level += magic; if (magic_level > magic_cost) magic_level = magic_cost; }
	 * The original pauses this while the inventory screen is open; callers skip the call then.
	 */
	DINKCORE_API int32 MagicChargeStep(int32 MagicLevel, int32 Magic, int32 MagicCost);

	/**
	 * Number of 100 ms steps to charge a spell of MagicCost from 0 at the given Magic stat:
	 * ceil(cost / magic). INDEX_NONE if Magic <= 0 (never charges), 0 if cost <= 0.
	 */
	DINKCORE_API int32 MagicRechargeSteps(int32 MagicCost, int32 Magic);

	/**
	 * Documented recharge rule, seconds = cost / (10 x magic) (bible 03 section 1, from D:5935).
	 * Fireball (100) at magic 1 = 10 s; Hellfire (2000) at magic 10 = 20 s. Returns a negative
	 * value if Magic <= 0. The exact in-game time is MagicRechargeSteps * 0.1 s, which rounds
	 * this up to the next 100 ms when cost is not a multiple of magic.
	 */
	DINKCORE_API float MagicRechargeSeconds(int32 MagicCost, int32 Magic);

	/** A spell can be cast when magic_level >= magic_cost (D:14906-14943). */
	DINKCORE_API bool CanCastSpell(int32 MagicLevel, int32 MagicCost);

	/**
	 * Dragon/Seth magic resist roll (en-drag.c lines 70-76, s7-boss.c):
	 *     &resist = random(40, 1);   // rand() % 40 + 1, so 1..40
	 *     if (&resist > &magic) -> harm, else "Magic resisted."
	 * Returns true when resisted.
	 */
	DINKCORE_API bool RollMagicResist(int32 Magic, IDinkRandomSource& Rng);

	/** Probability of RollMagicResist: clamp(magic, 0, 40) / 40. */
	DINKCORE_API float MagicResistChance(int32 Magic);

	/**
	 * Experience needed for the next level (next_raise, D:235-243):
	 *     num = 100 * level * level; if (num > 99999) num = 99999;
	 * Level is clamped to 0..199 (the original asserts that range).
	 */
	DINKCORE_API int32 ExpForNextLevel(int32 Level);

	/**
	 * Experience gain (add_exp, D:615-646): only positive amounts count, and the total is capped
	 * at 99,999 after adding. (The original also requires the kill's last_hit to be the player.)
	 */
	DINKCORE_API int32 AddExperience(int32 CurrentExp, int32 Amount);

	/** True when Exp has reached the threshold for the next level (D:5866: g_guiExp >= g_guiRaise). */
	DINKCORE_API bool CanLevelUp(const FDinkStats& Stats);

	/**
	 * Level-up (D:5869 then story/lraise.c raise()):
	 *     &exp -= next_raise();
	 *     if (&level < 32) { &level += 1; chosen stat += 1; &lifemax += 3; }   // life is not healed
	 *     else { &exp = 0; say("What a gyp!") }
	 * Does nothing and returns NotReady if CanLevelUp is false.
	 */
	DINKCORE_API EDinkLevelUpOutcome ApplyLevelUp(FDinkStats& Stats, EDinkStatChoice Choice);
}

/** Blueprint access to DinkRules. Rolls take an FRandomStream so results are reproducible. */
UCLASS()
class DINKCORE_API UDinkCombatLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = "Dink|Combat")
	static int32 RollMeleeHit(int32 AttackerStrength, int32 TargetDefense, UPARAM(ref) FRandomStream& Stream);

	UFUNCTION(BlueprintCallable, Category = "Dink|Combat")
	static int32 RollMissileHit(int32 MissileStrength, int32 TargetDefense, UPARAM(ref) FRandomStream& Stream,
		EDinkFixesLevel Fixes = EDinkFixesLevel::Original);

	UFUNCTION(BlueprintCallable, Category = "Dink|Combat")
	static int32 RollTouchDamage(int32 TouchDamage, int32 TargetDefense, UPARAM(ref) FRandomStream& Stream);

	UFUNCTION(BlueprintCallable, Category = "Dink|Combat")
	static bool RollMagicResist(int32 Magic, UPARAM(ref) FRandomStream& Stream);

	UFUNCTION(BlueprintPure, Category = "Dink|Combat")
	static float GetMagicRechargeSeconds(int32 MagicCost, int32 Magic) { return DinkRules::MagicRechargeSeconds(MagicCost, Magic); }

	UFUNCTION(BlueprintPure, Category = "Dink|Combat")
	static float GetMagicResistChance(int32 Magic) { return DinkRules::MagicResistChance(Magic); }

	UFUNCTION(BlueprintPure, Category = "Dink|Progression")
	static int32 GetExpForNextLevel(int32 Level) { return DinkRules::ExpForNextLevel(Level); }
};
