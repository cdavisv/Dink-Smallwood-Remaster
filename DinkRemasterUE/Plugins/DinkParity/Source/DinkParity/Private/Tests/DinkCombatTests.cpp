// Combat and progression formulas against values computed by hand from the original rules
// (doc/remaster/bible/03 section 1 and 04 section 3; source/dink/dink.cpp lines cited in DinkCombat.h).
// FDinkScriptedRandomSource replays raw rand() values; each rule reduces them with % n as the
// original does, and the source records every n so the tests also check the rolled range.

#include "DinkTestHelpers.h"
#include "DinkCombat.h"
#include "DinkRandom.h"

namespace
{
	int32 Melee(int32 Strength, int32 Defense, TArray<int32> Rolls, TArray<int32>* OutModuli = nullptr, int32* OutConsumed = nullptr)
	{
		FDinkScriptedRandomSource Rng(MoveTemp(Rolls));
		const int32 Result = DinkRules::ResolveMeleeHit(Strength, Defense, Rng);
		if (OutModuli) { *OutModuli = Rng.RequestedModuli; }
		if (OutConsumed) { *OutConsumed = Rng.Consumed(); }
		return Result;
	}

	int32 Missile(int32 Strength, int32 Defense, TArray<int32> Rolls, EDinkFixesLevel Fixes = EDinkFixesLevel::Original, TArray<int32>* OutModuli = nullptr)
	{
		FDinkScriptedRandomSource Rng(MoveTemp(Rolls));
		const int32 Result = DinkRules::ResolveMissileHit(Strength, Defense, Rng, Fixes);
		if (OutModuli) { *OutModuli = Rng.RequestedModuli; }
		return Result;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCombatMeleeTest, "Dink.Core.Combat.Melee", DINK_TEST_FLAGS)
bool FDinkCombatMeleeTest::RunTest(const FString& Parameters)
{
	TArray<int32> Moduli;
	int32 Consumed = 0;

	// strength/2 + rand()%((strength+1)/2) + 1
	// Strength 3 (new game): 1 + [0,1] + 1 = 2..3, roll range 2.
	TestEqual(TEXT("S3 min"), Melee(3, 0, { 0 }, &Moduli), 2);
	TestTrue(TEXT("S3 rolls % 2"), Moduli == TArray<int32>{ 2 });
	TestEqual(TEXT("S3 max"), Melee(3, 0, { 1 }), 3);
	// Strength 10: 5 + [0,4] + 1 = 6..10.
	TestEqual(TEXT("S10 min"), Melee(10, 0, { 0 }, &Moduli), 6);
	TestTrue(TEXT("S10 rolls % 5"), Moduli == TArray<int32>{ 5 });
	TestEqual(TEXT("S10 max"), Melee(10, 0, { 4 }), 10);
	TestEqual(TEXT("S10 raw rand 7 -> 7 % 5 = 2"), Melee(10, 0, { 7 }), 8);
	// Strength 1: 0 + rand()%1 + 1 = always 1.
	TestEqual(TEXT("S1 always 1"), Melee(1, 0, { 12345 }, &Moduli), 1);
	TestTrue(TEXT("S1 rolls % 1"), Moduli == TArray<int32>{ 1 });
	// Strength 2: 1 + rand()%1 + 1 = 2.
	TestEqual(TEXT("S2 always 2"), Melee(2, 0, { 99 }), 2);
	// Strength 0: the original skips the hit; no roll.
	TestEqual(TEXT("S0 no damage"), Melee(0, 0, { 1 }, &Moduli, &Consumed), 0);
	TestEqual(TEXT("S0 does not roll"), Consumed, 0);

	// Defense subtracts.
	TestEqual(TEXT("S10 max vs defense 3"), Melee(10, 3, { 4 }), 7);
	TestEqual(TEXT("S10 min vs defense 5"), Melee(10, 5, { 0 }), 1);

	// Defense >= damage: 0, then a 50% chance of 1: (rand()%2)+1 == 1, i.e. rand()%2 == 0.
	TestEqual(TEXT("S3 (2) vs defense 5, pity roll 0 -> 1"), Melee(3, 5, { 0, 0 }, &Moduli), 1);
	TestTrue(TEXT("pity rolls % 2 after damage roll"), Moduli == (TArray<int32>{ 2, 2 }));
	TestEqual(TEXT("S3 (2) vs defense 5, pity roll 1 -> 0"), Melee(3, 5, { 0, 1 }), 0);
	TestEqual(TEXT("S3 (3) vs defense 3 (equal), pity roll 0 -> 1"), Melee(3, 3, { 1, 0 }), 1);
	TestEqual(TEXT("S3 (3) vs defense 3 (equal), pity roll 1 -> 0"), Melee(3, 3, { 1, 1 }), 0);
	TestEqual(TEXT("S1 vs defense 1, pity roll 0 -> 1"), Melee(1, 1, { 0, 0 }), 1);
	TestEqual(TEXT("S1 vs defense 100, pity roll 1 -> 0"), Melee(1, 100, { 0, 1 }), 0);
	TestEqual(TEXT("defense higher than damage, no pity win"), Melee(10, 50, { 4, 3 }), 0);
	TestEqual(TEXT("defense higher than damage, pity win (raw 2 % 2 = 0)"), Melee(10, 50, { 4, 2 }), 1);

	// Negative defense adds damage (the original does no clamping).
	TestEqual(TEXT("negative defense"), Melee(3, -2, { 0 }), 4);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCombatDefenseRuleTest, "Dink.Core.Combat.DefenseRule", DINK_TEST_FLAGS)
bool FDinkCombatDefenseRuleTest::RunTest(const FString& Parameters)
{
	// hurt_thing: damage < 1 returns 0 without the pity roll.
	{
		FDinkScriptedRandomSource Rng({ 0 });
		TestEqual(TEXT("0 damage -> 0"), DinkRules::ApplyDefense(0, 0, Rng), 0);
		TestEqual(TEXT("-3 damage -> 0"), DinkRules::ApplyDefense(-3, 0, Rng), 0);
		TestEqual(TEXT("no roll for damage < 1"), Rng.Consumed(), 0);
	}
	{
		FDinkScriptedRandomSource Rng({ 0 });
		TestEqual(TEXT("5 - 2 = 3"), DinkRules::ApplyDefense(5, 2, Rng), 3);
		TestEqual(TEXT("no roll when damage gets through"), Rng.Consumed(), 0);
	}
	{
		FDinkScriptedRandomSource Rng({ 0, 1, 0, 1 });
		TestEqual(TEXT("blocked, roll 0 -> 1"), DinkRules::ApplyDefense(4, 4, Rng), 1);
		TestEqual(TEXT("blocked, roll 1 -> 0"), DinkRules::ApplyDefense(4, 9, Rng), 0);
		TestEqual(TEXT("blocked, roll 0 -> 1 (scripted hurt)"), DinkRules::ApplyDefense(20, 30, Rng), 1);
		TestEqual(TEXT("blocked, roll 1 -> 0 (scripted hurt)"), DinkRules::ApplyDefense(20, 30, Rng), 0);
		TestEqual(TEXT("one roll each"), Rng.Overruns, 0);
	}

	// Over many seeded rolls the pity point lands about half the time.
	FDinkStreamRandomSource Stream(42);
	int32 Ones = 0;
	const int32 Trials = 20000;
	for (int32 i = 0; i < Trials; ++i)
	{
		Ones += DinkRules::ApplyDefense(1, 5, Stream);
	}
	TestTrue(FString::Printf(TEXT("pity rate ~50%% (%d / %d)"), Ones, Trials), Ones > Trials * 0.47 && Ones < Trials * 0.53);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCombatMissileTest, "Dink.Core.Combat.Missile", DINK_TEST_FLAGS)
bool FDinkCombatMissileTest::RunTest(const FString& Parameters)
{
	TArray<int32> Moduli;

	// Original (fixes level 0, what the base game runs): strength/2 + rand()%(strength/2) + 1 - defense.
	// Fireball, strength 10: 5 + [0,4] + 1 = 6..10.
	TestEqual(TEXT("fireball min"), Missile(10, 0, { 0 }, EDinkFixesLevel::Original, &Moduli), 6);
	TestTrue(TEXT("fireball rolls % 5"), Moduli == TArray<int32>{ 5 });
	TestEqual(TEXT("fireball max"), Missile(10, 0, { 4 }), 10);
	// Hellfire, strength 40 vs defense 10: 20 + [0,19] + 1 - 10 = 11..30.
	TestEqual(TEXT("hellfire min vs def 10"), Missile(40, 10, { 0 }), 11);
	TestEqual(TEXT("hellfire max vs def 10"), Missile(40, 10, { 19 }), 30);
	// Strength 5: 2 + [0,1] + 1 = 3..4 (integer maths can never reach 5).
	TestEqual(TEXT("S5 original min"), Missile(5, 0, { 0 }), 3);
	TestEqual(TEXT("S5 original max"), Missile(5, 0, { 1 }), 4);
	// Strength 2 and 3: S/2 = 1, rand()%1 = 0 -> 2.
	TestEqual(TEXT("S2"), Missile(2, 0, { 7 }), 2);
	TestEqual(TEXT("S3"), Missile(3, 0, { 7 }), 2);
	// Strength 1 is special-cased: 1 - defense, no roll.
	TestEqual(TEXT("S1 vs 0"), Missile(1, 0, {}, EDinkFixesLevel::Original, &Moduli), 1);
	TestEqual(TEXT("S1 does not roll"), Moduli.Num(), 0);
	TestEqual(TEXT("S1 vs 1"), Missile(1, 1, {}), 0);
	// Strength 0: no damage.
	TestEqual(TEXT("S0"), Missile(0, 0, { 1 }, EDinkFixesLevel::Original, &Moduli), 0);
	TestEqual(TEXT("S0 does not roll"), Moduli.Num(), 0);

	// Defense higher than damage: clamped to 0, and missiles have NO pity point.
	TestEqual(TEXT("S1 vs defense 5 -> 0, no pity"), Missile(1, 5, { 0, 0 }, EDinkFixesLevel::Original, &Moduli), 0);
	TestEqual(TEXT("no pity roll"), Moduli.Num(), 0);
	TestEqual(TEXT("acid rain (6) vs defense 20 -> 0"), Missile(6, 20, { 2, 0 }, EDinkFixesLevel::Original, &Moduli), 0);
	TestEqual(TEXT("only the damage roll"), Moduli.Num(), 1);

	// Latest fixes (float variant): (int)(S/2.0 + (rand() % (int)(S*100/2.0)) / 100.0 + 1) - defense.
	// Strength 5: modulus 250; 2.5 + [0, 2.49] + 1 = 3.5..5.99 -> 3..5.
	TestEqual(TEXT("S5 latest min"), Missile(5, 0, { 0 }, EDinkFixesLevel::Latest, &Moduli), 3);
	TestTrue(TEXT("S5 latest rolls % 250"), Moduli == TArray<int32>{ 250 });
	TestEqual(TEXT("S5 latest 0.50 -> 4"), Missile(5, 0, { 50 }, EDinkFixesLevel::Latest), 4);
	TestEqual(TEXT("S5 latest max -> 5"), Missile(5, 0, { 249 }, EDinkFixesLevel::Latest), 5);
	TestEqual(TEXT("S10 latest max vs def 2"), Missile(10, 2, { 499 }, EDinkFixesLevel::Latest), 8);
	TestEqual(TEXT("S1 latest still 1 - defense"), Missile(1, 0, {}, EDinkFixesLevel::Latest), 1);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCombatTouchTest, "Dink.Core.Combat.Touch", DINK_TEST_FLAGS)
bool FDinkCombatTouchTest::RunTest(const FString& Parameters)
{
	FDinkScriptedRandomSource Rng({ 0, 1 });
	TestEqual(TEXT("touch 5 vs defense 2"), DinkRules::ResolveTouchDamage(5, 2, Rng), 3);
	TestEqual(TEXT("touch 0: none"), DinkRules::ResolveTouchDamage(0, 0, Rng), 0);
	TestEqual(TEXT("touch -1: script only"), DinkRules::ResolveTouchDamage(-1, 0, Rng), 0);
	TestEqual(TEXT("no rolls so far"), Rng.Consumed(), 0);
	TestEqual(TEXT("touch 2 vs defense 4, pity 0 -> 1"), DinkRules::ResolveTouchDamage(2, 4, Rng), 1);
	TestEqual(TEXT("touch 2 vs defense 4, pity 1 -> 0"), DinkRules::ResolveTouchDamage(2, 4, Rng), 0);
	TestEqual(TEXT("immunity 400 ms"), DinkRules::TouchImmunityMs, 400);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCombatMagicTest, "Dink.Core.Combat.Magic", DINK_TEST_FLAGS)
bool FDinkCombatMagicTest::RunTest(const FString& Parameters)
{
	// One 100 ms step: magic_level += magic, capped at cost; nothing once charged.
	TestEqual(TEXT("step from 0"), DinkRules::MagicChargeStep(0, 1, 100), 1);
	TestEqual(TEXT("step caps at cost"), DinkRules::MagicChargeStep(99, 5, 100), 100);
	TestEqual(TEXT("charged stays"), DinkRules::MagicChargeStep(100, 5, 100), 100);
	TestEqual(TEXT("magic 0 never charges"), DinkRules::MagicChargeStep(0, 0, 100), 0);

	// seconds = cost / (10 x magic): the bible's examples.
	TestEqual(TEXT("fireball (100) at magic 1 = 10 s"), DinkRules::MagicRechargeSeconds(100, 1), 10.0f);
	TestEqual(TEXT("hellfire (2000) at magic 10 = 20 s"), DinkRules::MagicRechargeSeconds(2000, 10), 20.0f);
	TestEqual(TEXT("acid rain (1000) at magic 5 = 20 s"), DinkRules::MagicRechargeSeconds(1000, 5), 20.0f);
	TestEqual(TEXT("100 at magic 3 = 3.33 s nominal"), DinkRules::MagicRechargeSeconds(100, 3), 100.0f / 30.0f);
	TestTrue(TEXT("magic 0: never (negative)"), DinkRules::MagicRechargeSeconds(100, 0) < 0.0f);

	// Exact steps agree with simulating the step function.
	TestEqual(TEXT("fireball steps"), DinkRules::MagicRechargeSteps(100, 1), 100);
	TestEqual(TEXT("hellfire steps"), DinkRules::MagicRechargeSteps(2000, 10), 200);
	TestEqual(TEXT("100 at magic 3 = 34 steps (3.4 s)"), DinkRules::MagicRechargeSteps(100, 3), 34);
	TestEqual(TEXT("cost 0 = 0 steps"), DinkRules::MagicRechargeSteps(0, 3), 0);
	TestEqual(TEXT("magic 0 = never"), DinkRules::MagicRechargeSteps(100, 0), int32(INDEX_NONE));
	for (const TPair<int32, int32>& Case : TArray<TPair<int32, int32>>{ { 100, 1 }, { 100, 3 }, { 200, 7 }, { 2000, 10 }, { 1000, 6 } })
	{
		int32 Level = 0;
		int32 Steps = 0;
		while (!DinkRules::CanCastSpell(Level, Case.Key) && Steps < 100000)
		{
			Level = DinkRules::MagicChargeStep(Level, Case.Value, Case.Key);
			++Steps;
		}
		TestEqual(FString::Printf(TEXT("simulated steps cost %d magic %d"), Case.Key, Case.Value), Steps, DinkRules::MagicRechargeSteps(Case.Key, Case.Value));
	}

	// Resist: random(40,1) = rand()%40 + 1; resisted unless the roll is above magic.
	{
		FDinkScriptedRandomSource Rng({ 0, 0, 1, 39, 39, 38 });
		TestFalse(TEXT("magic 0, roll 1 -> harm"), DinkRules::RollMagicResist(0, Rng));
		TestTrue(TEXT("magic 1, roll 1 -> resisted"), DinkRules::RollMagicResist(1, Rng));
		TestFalse(TEXT("magic 1, roll 2 -> harm"), DinkRules::RollMagicResist(1, Rng));
		TestTrue(TEXT("magic 40, roll 40 -> resisted"), DinkRules::RollMagicResist(40, Rng));
		TestFalse(TEXT("magic 39, roll 40 -> harm"), DinkRules::RollMagicResist(39, Rng));
		TestTrue(TEXT("magic 39, roll 39 -> resisted"), DinkRules::RollMagicResist(39, Rng));
		TestTrue(TEXT("rolls % 40"), Rng.RequestedModuli.Num() == 6 && Rng.RequestedModuli[0] == 40);
	}
	TestEqual(TEXT("resist chance magic 0"), DinkRules::MagicResistChance(0), 0.0f);
	TestEqual(TEXT("resist chance magic 10"), DinkRules::MagicResistChance(10), 0.25f);
	TestEqual(TEXT("resist chance magic 40"), DinkRules::MagicResistChance(40), 1.0f);
	TestEqual(TEXT("resist chance capped"), DinkRules::MagicResistChance(55), 1.0f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCombatExperienceTest, "Dink.Core.Progression.Experience", DINK_TEST_FLAGS)
bool FDinkCombatExperienceTest::RunTest(const FString& Parameters)
{
	// next_raise: 100 * level^2, capped at 99,999.
	TestEqual(TEXT("level 1 -> 100"), DinkRules::ExpForNextLevel(1), 100);
	TestEqual(TEXT("level 2 -> 400"), DinkRules::ExpForNextLevel(2), 400);
	TestEqual(TEXT("level 3 -> 900"), DinkRules::ExpForNextLevel(3), 900);
	TestEqual(TEXT("level 10 -> 10,000"), DinkRules::ExpForNextLevel(10), 10000);
	TestEqual(TEXT("level 31 -> 96,100"), DinkRules::ExpForNextLevel(31), 96100);
	TestEqual(TEXT("level 32 -> 102,400 capped to 99,999"), DinkRules::ExpForNextLevel(32), 99999);
	TestEqual(TEXT("level 0 -> 0"), DinkRules::ExpForNextLevel(0), 0);
	TestEqual(TEXT("level 500 clamps, no overflow"), DinkRules::ExpForNextLevel(500), 99999);

	int64 Total = 0;
	for (int32 Level = 1; Level <= 31; ++Level)
	{
		Total += DinkRules::ExpForNextLevel(Level);
	}
	TestEqual(TEXT("levels 1-31 total 1,041,600 (bible 03)"), Total, int64(1041600));

	// add_exp: only positive gains, capped after adding.
	TestEqual(TEXT("add 50"), DinkRules::AddExperience(10, 50), 60);
	TestEqual(TEXT("cap"), DinkRules::AddExperience(99990, 20), 99999);
	TestEqual(TEXT("at cap"), DinkRules::AddExperience(99999, 1), 99999);
	TestEqual(TEXT("zero ignored"), DinkRules::AddExperience(70, 0), 70);
	TestEqual(TEXT("negative ignored"), DinkRules::AddExperience(70, -30), 70);
	TestEqual(TEXT("huge gain, no overflow"), DinkRules::AddExperience(99000, MAX_int32), 99999);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCombatLevelUpTest, "Dink.Core.Progression.LevelUp", DINK_TEST_FLAGS)
bool FDinkCombatLevelUpTest::RunTest(const FString& Parameters)
{
	// New game, 150 exp: level 2, exp 50, chosen stat +1, max life +3, life NOT healed.
	{
		FDinkStats Stats;
		Stats.Exp = 150;
		Stats.Life = 4;
		TestTrue(TEXT("can level"), DinkRules::CanLevelUp(Stats));
		TestEqual(TEXT("raised"), DinkRules::ApplyLevelUp(Stats, EDinkStatChoice::Attack), EDinkLevelUpOutcome::Raised);
		TestEqual(TEXT("level 2"), Stats.Level, 2);
		TestEqual(TEXT("exp keeps the remainder"), Stats.Exp, 50);
		TestEqual(TEXT("strength 3 -> 4"), Stats.Strength, 4);
		TestEqual(TEXT("defense unchanged"), Stats.Defense, 0);
		TestEqual(TEXT("lifemax 10 -> 13"), Stats.LifeMax, 13);
		TestEqual(TEXT("life not healed"), Stats.Life, 4);
		TestFalse(TEXT("50 < 400: cannot level again"), DinkRules::CanLevelUp(Stats));
		TestEqual(TEXT("not ready"), DinkRules::ApplyLevelUp(Stats, EDinkStatChoice::Attack), EDinkLevelUpOutcome::NotReady);
		TestEqual(TEXT("not ready changes nothing"), Stats.Level, 2);
	}
	{
		FDinkStats Stats;
		Stats.Exp = 100;
		DinkRules::ApplyLevelUp(Stats, EDinkStatChoice::Defense);
		TestEqual(TEXT("defense choice"), Stats.Defense, 1);
		TestEqual(TEXT("exactly enough -> 0 left"), Stats.Exp, 0);
		Stats.Exp = 400;
		DinkRules::ApplyLevelUp(Stats, EDinkStatChoice::Magic);
		TestEqual(TEXT("magic choice"), Stats.Magic, 1);
		TestEqual(TEXT("level 3"), Stats.Level, 3);
		TestEqual(TEXT("lifemax 16"), Stats.LifeMax, 16);
	}
	// Level 31 -> 32 is the last real raise.
	{
		FDinkStats Stats;
		Stats.Level = 31;
		Stats.Exp = 96100 + 7;
		Stats.LifeMax = 100;
		TestEqual(TEXT("31 -> 32 raised"), DinkRules::ApplyLevelUp(Stats, EDinkStatChoice::Attack), EDinkLevelUpOutcome::Raised);
		TestEqual(TEXT("level 32"), Stats.Level, 32);
		TestEqual(TEXT("exp 7"), Stats.Exp, 7);
		TestEqual(TEXT("lifemax 103"), Stats.LifeMax, 103);
	}
	// At level 32: next is 99,999 (capped); reaching it only resets exp ("What a gyp!").
	{
		FDinkStats Stats;
		Stats.Level = 32;
		Stats.Exp = 99998;
		TestFalse(TEXT("32 at 99,998: not ready"), DinkRules::CanLevelUp(Stats));
		Stats.Exp = DinkRules::AddExperience(Stats.Exp, 5000);
		TestEqual(TEXT("exp capped at 99,999"), Stats.Exp, 99999);
		const FDinkStats Before = Stats;
		TestEqual(TEXT("at cap"), DinkRules::ApplyLevelUp(Stats, EDinkStatChoice::Attack), EDinkLevelUpOutcome::AtCap);
		TestEqual(TEXT("still 32"), Stats.Level, 32);
		TestEqual(TEXT("exp reset to 0"), Stats.Exp, 0);
		TestEqual(TEXT("no stat gain"), Stats.Strength, Before.Strength);
		TestEqual(TEXT("no life gain"), Stats.LifeMax, Before.LifeMax);
	}
	return true;
}
