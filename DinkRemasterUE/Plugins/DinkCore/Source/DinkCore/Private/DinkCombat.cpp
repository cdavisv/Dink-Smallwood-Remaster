#include "DinkCombat.h"

// Every rule below is documented (with its source line) in DinkCombat.h. Keep integer
// division and the order of RandomModulo calls exactly as the original.

int32 DinkRules::MeleeBaseDamage(int32 Strength, IDinkRandomSource& Rng)
{
	if (Strength <= 0)
	{
		return 0;
	}
	// dink.cpp D:15567: (strength / 2) + ((rand() % ((strength + 1) / 2)) + 1)
	return (Strength / 2) + (Rng.RandomModulo((Strength + 1) / 2) + 1);
}

int32 DinkRules::ApplyDefense(int32 Damage, int32 Defense, IDinkRandomSource& Rng)
{
	// dink.cpp D:6656-6667 hurt_thing
	if (Damage < 1)
	{
		return 0;
	}
	int32 Num = Damage - Defense;
	if (Num < 1)
	{
		Num = 0;
	}
	if (Num == 0)
	{
		if ((Rng.RandomModulo(2) + 1) == 1)
		{
			Num = 1;
		}
	}
	return Num;
}

int32 DinkRules::ResolveMeleeHit(int32 AttackerStrength, int32 TargetDefense, IDinkRandomSource& Rng)
{
	return ApplyDefense(MeleeBaseDamage(AttackerStrength, Rng), TargetDefense, Rng);
}

int32 DinkRules::ResolveMissileHit(int32 MissileStrength, int32 TargetDefense, IDinkRandomSource& Rng, EDinkFixesLevel Fixes)
{
	// dink.cpp D:14363-14394
	if (MissileStrength <= 0)
	{
		return 0;
	}
	int32 Hit = 0;
	if (MissileStrength == 1)
	{
		Hit = MissileStrength - TargetDefense;
	}
	else if (Fixes == EDinkFixesLevel::Latest)
	{
		float FHit = 0.0f;
		FHit += static_cast<float>(MissileStrength) / 2.0f;
		FHit += static_cast<float>(Rng.RandomModulo(static_cast<int32>(static_cast<float>(MissileStrength) * 100 / 2.0f))) / 100;
		FHit += 1.0f;
		Hit = static_cast<int32>(FHit) - TargetDefense;
	}
	else
	{
		Hit = (MissileStrength / 2) + (Rng.RandomModulo(MissileStrength / 2) + 1) - TargetDefense;
	}
	if (Hit < 0)
	{
		Hit = 0;
	}
	return Hit;
}

int32 DinkRules::ResolveTouchDamage(int32 TouchDamage, int32 TargetDefense, IDinkRandomSource& Rng)
{
	// dink.cpp D:15629-15680: 0 = no touch damage, -1 = TOUCH script only, else hurt_thing().
	if (TouchDamage <= 0)
	{
		return 0;
	}
	return ApplyDefense(TouchDamage, TargetDefense, Rng);
}

int32 DinkRules::MagicChargeStep(int32 MagicLevel, int32 Magic, int32 MagicCost)
{
	// dink.cpp D:5935-5940
	if (MagicLevel < MagicCost)
	{
		MagicLevel += Magic;
		if (MagicLevel > MagicCost)
		{
			MagicLevel = MagicCost;
		}
	}
	return MagicLevel;
}

int32 DinkRules::MagicRechargeSteps(int32 MagicCost, int32 Magic)
{
	if (MagicCost <= 0)
	{
		return 0;
	}
	if (Magic <= 0)
	{
		return INDEX_NONE;
	}
	return (MagicCost + Magic - 1) / Magic;
}

float DinkRules::MagicRechargeSeconds(int32 MagicCost, int32 Magic)
{
	if (Magic <= 0)
	{
		return -1.0f;
	}
	return static_cast<float>(FMath::Max(MagicCost, 0)) / (10.0f * static_cast<float>(Magic));
}

bool DinkRules::CanCastSpell(int32 MagicLevel, int32 MagicCost)
{
	return MagicLevel >= MagicCost;
}

bool DinkRules::RollMagicResist(int32 Magic, IDinkRandomSource& Rng)
{
	// en-drag.c 70-76: &resist = random(40, 1); if (&resist > &magic) harm; else resisted.
	const int32 Resist = Rng.RandomModulo(MagicResistRange) + 1;
	return !(Resist > Magic);
}

float DinkRules::MagicResistChance(int32 Magic)
{
	return static_cast<float>(FMath::Clamp(Magic, 0, MagicResistRange)) / static_cast<float>(MagicResistRange);
}

int32 DinkRules::ExpForNextLevel(int32 Level)
{
	// dink.cpp D:235-243 next_raise
	const int64 Clamped = FMath::Clamp(Level, 0, 199);
	const int64 Num = (100 * Clamped) * Clamped;
	return static_cast<int32>(FMath::Min<int64>(Num, MaxExp));
}

int32 DinkRules::AddExperience(int32 CurrentExp, int32 Amount)
{
	// dink.cpp D:623-643 add_exp
	if (Amount <= 0)
	{
		return CurrentExp;
	}
	const int64 Sum = static_cast<int64>(CurrentExp) + Amount;
	return static_cast<int32>(FMath::Min<int64>(Sum, MaxExp));
}

bool DinkRules::CanLevelUp(const FDinkStats& Stats)
{
	return Stats.Exp >= ExpForNextLevel(Stats.Level);
}

EDinkLevelUpOutcome DinkRules::ApplyLevelUp(FDinkStats& Stats, EDinkStatChoice Choice)
{
	if (!CanLevelUp(Stats))
	{
		return EDinkLevelUpOutcome::NotReady;
	}
	// dink.cpp D:5869
	Stats.Exp -= ExpForNextLevel(Stats.Level);

	// story/lraise.c raise()
	if (Stats.Level < MaxLevel)
	{
		Stats.Level += 1;
		switch (Choice)
		{
		case EDinkStatChoice::Attack:  Stats.Strength += 1; break;
		case EDinkStatChoice::Defense: Stats.Defense += 1; break;
		case EDinkStatChoice::Magic:   Stats.Magic += 1; break;
		}
		Stats.LifeMax += 3;
		return EDinkLevelUpOutcome::Raised;
	}
	Stats.Exp = 0;
	return EDinkLevelUpOutcome::AtCap;
}

// ---- Blueprint wrappers ----

int32 UDinkCombatLibrary::RollMeleeHit(int32 AttackerStrength, int32 TargetDefense, FRandomStream& Stream)
{
	FDinkStreamRandomSource Source(Stream);
	const int32 Result = DinkRules::ResolveMeleeHit(AttackerStrength, TargetDefense, Source);
	Stream = Source.GetStream();
	return Result;
}

int32 UDinkCombatLibrary::RollMissileHit(int32 MissileStrength, int32 TargetDefense, FRandomStream& Stream, EDinkFixesLevel Fixes)
{
	FDinkStreamRandomSource Source(Stream);
	const int32 Result = DinkRules::ResolveMissileHit(MissileStrength, TargetDefense, Source, Fixes);
	Stream = Source.GetStream();
	return Result;
}

int32 UDinkCombatLibrary::RollTouchDamage(int32 TouchDamage, int32 TargetDefense, FRandomStream& Stream)
{
	FDinkStreamRandomSource Source(Stream);
	const int32 Result = DinkRules::ResolveTouchDamage(TouchDamage, TargetDefense, Source);
	Stream = Source.GetStream();
	return Result;
}

bool UDinkCombatLibrary::RollMagicResist(int32 Magic, FRandomStream& Stream)
{
	FDinkStreamRandomSource Source(Stream);
	const bool bResult = DinkRules::RollMagicResist(Magic, Source);
	Stream = Source.GetStream();
	return bResult;
}
