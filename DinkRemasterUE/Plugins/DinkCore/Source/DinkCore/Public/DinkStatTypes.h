#pragma once

#include "CoreMinimal.h"
#include "DinkStatTypes.generated.h"

/**
 * Stat block shared by the player and by enemies. Defaults are the original new-game values
 * (story/main.c make_global_int lines 9-29; bible 03 section 1).
 *
 * The original game keeps these as globals (&strength, &life, ...) for the player and as sprite
 * fields (strength, defense, hitpoints, touch_damage) for everything else.
 */
USTRUCT(BlueprintType)
struct DINKCORE_API FDinkStats
{
	GENERATED_BODY()

	/** Attack. &strength / sp_strength. New game: 3. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Stats")
	int32 Strength = 3;

	/** Flat damage reduction. &defense / sp_defense. New game: 0. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Stats")
	int32 Defense = 0;

	/** Magic recharge rate per 100 ms and resist chance. &magic. New game: 0. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Stats")
	int32 Magic = 0;

	/** &life (player) / sp_hitpoints (others). New game: 10. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Stats")
	int32 Life = 10;

	/** &lifemax. New game: 10. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Stats")
	int32 LifeMax = 10;

	/** &level. New game: 1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Stats")
	int32 Level = 1;

	/** &exp, capped at 99,999. New game: 0. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Stats")
	int32 Exp = 0;

	/** &gold. New game: 0. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Stats")
	int32 Gold = 0;

	/** Current spell charge, &magic_level. Climbs by Magic every 100 ms up to MagicCost. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Stats")
	int32 MagicLevel = 0;

	/** Charge the armed spell needs, &magic_cost (set by the spell's arm() procedure). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Stats")
	int32 MagicCost = 0;

	/** Damage dealt to the player on contact (sp_touch_damage). 0 none, -1 only runs the touch script. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Stats")
	int32 TouchDamage = 0;

	bool operator==(const FDinkStats& Other) const
	{
		return Strength == Other.Strength && Defense == Other.Defense && Magic == Other.Magic
			&& Life == Other.Life && LifeMax == Other.LifeMax && Level == Other.Level && Exp == Other.Exp
			&& Gold == Other.Gold && MagicLevel == Other.MagicLevel && MagicCost == Other.MagicCost
			&& TouchDamage == Other.TouchDamage;
	}
	bool operator!=(const FDinkStats& Other) const { return !(*this == Other); }
};

/** The stat the player picks on level-up (lraise.c menu: &result 1, 2, 3). */
UENUM(BlueprintType)
enum class EDinkStatChoice : uint8
{
	Attack  UMETA(DisplayName = "Increase Attack"),
	Defense UMETA(DisplayName = "Increase Defense"),
	Magic   UMETA(DisplayName = "Increase Magic"),
};

/** What a level-up did. */
UENUM(BlueprintType)
enum class EDinkLevelUpOutcome : uint8
{
	/** Not enough experience; nothing changed. */
	NotReady,
	/** Level +1, chosen stat +1, max life +3. */
	Raised,
	/** Already at the level cap: experience reset to 0 ("What a gyp!"). */
	AtCap,
};

/** Which version of the original missile formula to use (the engine's m_use_latest_fixes_level). */
UENUM(BlueprintType)
enum class EDinkFixesLevel : uint8
{
	/** 0: what the base game runs (the global is zero-initialised and no base script changes it). */
	Original = 0,
	/** 1: the HD engine's float variant, opt-in per DMOD with set_use_latest_fixes_level(1). */
	Latest = 1,
};
