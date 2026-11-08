#include "DinkTestHelpers.h"
#include "DinkStatsComponent.h"
#include "DinkCombat.h"

namespace
{
	UDinkStatsComponent* MakeStats(TArray<int32> Rolls)
	{
		UDinkStatsComponent* Stats = NewObject<UDinkStatsComponent>(GetTransientPackage());
		Stats->SetRandomSource(MakeShared<FDinkScriptedRandomSource>(MoveTemp(Rolls)));
		return Stats;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkStatsDefaultsTest, "Dink.Core.Stats.NewGameDefaults", DINK_TEST_FLAGS)
bool FDinkStatsDefaultsTest::RunTest(const FString& Parameters)
{
	// bible 03 section 1 / main.c: strength 3, defense 0, magic 0, life 10/10, level 1, gold 0, exp 0.
	const FDinkStats Stats;
	TestEqual(TEXT("strength"), Stats.Strength, 3);
	TestEqual(TEXT("defense"), Stats.Defense, 0);
	TestEqual(TEXT("magic"), Stats.Magic, 0);
	TestEqual(TEXT("life"), Stats.Life, 10);
	TestEqual(TEXT("lifemax"), Stats.LifeMax, 10);
	TestEqual(TEXT("level"), Stats.Level, 1);
	TestEqual(TEXT("gold"), Stats.Gold, 0);
	TestEqual(TEXT("exp"), Stats.Exp, 0);

	// The defaults agree with the shipped facts table.
	UDinkFactSubsystem* Facts = DinkTest::MakeFacts(*this);
	TestEqual(TEXT("facts strength"), Facts->GetFact(TEXT("strength")), Stats.Strength);
	TestEqual(TEXT("facts defense"), Facts->GetFact(TEXT("defense")), Stats.Defense);
	TestEqual(TEXT("facts magic"), Facts->GetFact(TEXT("magic")), Stats.Magic);
	TestEqual(TEXT("facts life"), Facts->GetFact(TEXT("life")), Stats.Life);
	TestEqual(TEXT("facts lifemax"), Facts->GetFact(TEXT("lifemax")), Stats.LifeMax);
	TestEqual(TEXT("facts level"), Facts->GetFact(TEXT("level")), Stats.Level);
	TestEqual(TEXT("facts gold"), Facts->GetFact(TEXT("gold")), Stats.Gold);
	TestEqual(TEXT("facts exp"), Facts->GetFact(TEXT("exp")), Stats.Exp);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkStatsDamageTest, "Dink.Core.Stats.DamageAndDeath", DINK_TEST_FLAGS)
bool FDinkStatsDamageTest::RunTest(const FString& Parameters)
{
	// Rolls: melee S10 raw 4 (=10); missile S10 raw 0 (=6); scripted hurt blocked pity 0 (=1).
	UDinkStatsComponent* Stats = MakeStats({ 4, 0, 0 });
	FDinkStats Initial;
	Initial.Life = 30;
	Initial.LifeMax = 30;
	Initial.Defense = 2;
	Stats->SetStats(Initial);

	int32 Deaths = 0;
	int32 Changes = 0;
	Stats->OnDiedNative.AddLambda([&Deaths](UDinkStatsComponent*) { ++Deaths; });
	Stats->OnStatsChangedNative.AddLambda([&Changes](UDinkStatsComponent*) { ++Changes; });

	TestEqual(TEXT("melee 10 - 2"), Stats->TakeMeleeHit(10), 8);
	TestEqual(TEXT("life 22"), Stats->Stats.Life, 22);
	TestEqual(TEXT("missile 6 - 2"), Stats->TakeMissileHit(10), 4);
	TestEqual(TEXT("life 18"), Stats->Stats.Life, 18);
	TestEqual(TEXT("scripted hurt 1 vs def 2 -> pity 1"), Stats->TakeScriptedDamage(1), 1);
	TestEqual(TEXT("life 17"), Stats->Stats.Life, 17);
	TestEqual(TEXT("three change events"), Changes, 3);

	// Touch damage and the 400 ms immunity window (scripted source now repeats its last value 0).
	TestEqual(TEXT("touch 5 at t=1000"), Stats->TakeTouchDamage(5, 1000), 3);
	TestTrue(TEXT("immune at 1399"), Stats->IsTouchImmune(1399));
	TestEqual(TEXT("ignored at t=1399"), Stats->TakeTouchDamage(5, 1399), 0);
	TestEqual(TEXT("hits again at t=1400"), Stats->TakeTouchDamage(5, 1400), 3);
	TestEqual(TEXT("touch -1 never hurts"), Stats->TakeTouchDamage(-1, 5000), 0);
	TestEqual(TEXT("life 11"), Stats->Stats.Life, 11);

	TestFalse(TEXT("alive"), Stats->IsDead());
	TestEqual(TEXT("overkill reports life actually lost"), Stats->TakeScriptedDamage(50), 11);
	TestTrue(TEXT("dead"), Stats->IsDead());
	TestEqual(TEXT("life floored at 0"), Stats->Stats.Life, 0);
	TestEqual(TEXT("death fired once"), Deaths, 1);
	Stats->TakeScriptedDamage(50);
	TestEqual(TEXT("no second death"), Deaths, 1);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkStatsProgressionTest, "Dink.Core.Stats.ProgressionAndMagic", DINK_TEST_FLAGS)
bool FDinkStatsProgressionTest::RunTest(const FString& Parameters)
{
	UDinkStatsComponent* Stats = MakeStats({});
	TestEqual(TEXT("needs 100"), Stats->GetExpForNextLevel(), 100);
	TestEqual(TEXT("add 120"), Stats->AddExperience(120), 120);
	TestTrue(TEXT("can level"), Stats->CanLevelUp());
	TestEqual(TEXT("level up"), Stats->LevelUp(EDinkStatChoice::Magic), EDinkLevelUpOutcome::Raised);
	TestEqual(TEXT("magic 1"), Stats->Stats.Magic, 1);
	TestEqual(TEXT("exp 20"), Stats->Stats.Exp, 20);

	// Fireball: cost 100 at magic 1 takes 100 steps (10 s); paused while the inventory is open.
	Stats->SetMagicCost(100);
	for (int32 i = 0; i < 99; ++i)
	{
		Stats->TickMagicCharge(false);
	}
	TestFalse(TEXT("99 steps: not ready"), Stats->CanCastSpell());
	Stats->TickMagicCharge(true);
	TestEqual(TEXT("inventory open pauses"), Stats->Stats.MagicLevel, 99);
	Stats->TickMagicCharge(false);
	TestTrue(TEXT("100 steps: ready"), Stats->CanCastSpell());
	TestTrue(TEXT("cast"), Stats->TryCastSpell());
	TestEqual(TEXT("charge emptied"), Stats->Stats.MagicLevel, 0);
	TestFalse(TEXT("cannot cast again"), Stats->TryCastSpell());

	Stats->SetMagicCost(0);
	TestFalse(TEXT("no spell armed: cannot cast"), Stats->CanCastSpell());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkStatsFactMirrorTest, "Dink.Core.Stats.FactMirror", DINK_TEST_FLAGS)
bool FDinkStatsFactMirrorTest::RunTest(const FString& Parameters)
{
	UDinkFactSubsystem* Facts = DinkTest::MakeFacts(*this);
	UDinkStatsComponent* Stats = MakeStats({});

	Stats->SetFactMirrorTarget(Facts);
	Stats->AddGold(25);
	TestEqual(TEXT("mirror off: gold fact untouched"), Facts->GetFact(TEXT("gold")), 0);

	Stats->bMirrorToFacts = true;
	Stats->AddGold(25);
	TestEqual(TEXT("gold mirrored"), Facts->GetFact(TEXT("gold")), 50);
	Stats->AddExperience(100);
	Stats->LevelUp(EDinkStatChoice::Attack);
	TestEqual(TEXT("strength mirrored"), Facts->GetFact(TEXT("strength")), 4);
	TestEqual(TEXT("level mirrored"), Facts->GetFact(TEXT("level")), 2);
	TestEqual(TEXT("lifemax mirrored"), Facts->GetFact(TEXT("lifemax")), 13);
	TestTrue(TEXT("conditions see stats"), Facts->EvaluateCondition(FDinkFactCondition(TEXT("level"), EDinkCompareOp::GreaterOrEqual, 2)));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkStatsSeededTest, "Dink.Core.Stats.SeededRandomIsDeterministic", DINK_TEST_FLAGS)
bool FDinkStatsSeededTest::RunTest(const FString& Parameters)
{
	auto Fight = [](int32 Seed)
	{
		UDinkStatsComponent* Stats = NewObject<UDinkStatsComponent>(GetTransientPackage());
		Stats->RandomSeed = Seed;
		FDinkStats Big;
		Big.Life = Big.LifeMax = 100000;
		Stats->SetStats(Big);
		TArray<int32> Hits;
		for (int32 i = 0; i < 200; ++i)
		{
			Hits.Add(Stats->TakeMeleeHit(10));
		}
		return Hits;
	};
	const TArray<int32> A = Fight(7);
	TestTrue(TEXT("same seed, same fight"), A == Fight(7));
	TestFalse(TEXT("different seed, different fight"), A == Fight(8));
	int32 Min = MAX_int32, Max = MIN_int32;
	for (int32 Hit : A)
	{
		Min = FMath::Min(Min, Hit);
		Max = FMath::Max(Max, Hit);
	}
	TestEqual(TEXT("S10 vs def 0 min is 6"), Min, 6);
	TestEqual(TEXT("S10 vs def 0 max is 10"), Max, 10);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkStatsFactMirrorTwoWayTest, "Dink.Core.Stats.FactMirrorTwoWay", DINK_TEST_FLAGS)
bool FDinkStatsFactMirrorTwoWayTest::RunTest(const FString& Parameters)
{
	// The fact store is the one source of truth: a script writing &gold reaches the stats, and a
	// reset/restore of the facts is pulled into the stats.
	UDinkFactSubsystem* Facts = DinkTest::MakeFacts(*this);
	UDinkStatsComponent* Stats = MakeStats({});
	Stats->bMirrorToFacts = true;
	Stats->SetFactMirrorTarget(Facts);
	Facts->SetFact(TEXT("gold"), 120);
	TestEqual(TEXT("fact -> stats: gold"), Stats->Stats.Gold, 120);
	Facts->AddToFact(TEXT("strength"), 2);
	TestEqual(TEXT("fact -> stats: strength"), Stats->Stats.Strength, Facts->GetFact(TEXT("strength")));
	Facts->SetFact(TEXT("story"), 5);
	TestEqual(TEXT("a story fact does not touch stats"), Stats->Stats.Gold, 120);
	Stats->AddGold(5);
	TestEqual(TEXT("stats -> fact still works"), Facts->GetFact(TEXT("gold")), 125);

	TMap<FName, int32> Saved = Facts->GetAllFacts();
	Saved.Add(TEXT("gold"), 7);
	Saved.Add(TEXT("life"), 4);
	Facts->RestoreFacts(Saved);
	TestEqual(TEXT("restore pulls gold into stats"), Stats->Stats.Gold, 7);
	TestEqual(TEXT("restore pulls life into stats"), Stats->Stats.Life, 4);
	Facts->ResetToInitialValues();
	TestEqual(TEXT("new game pulls the initial gold"), Stats->Stats.Gold, 0);
	TestEqual(TEXT("new game pulls the initial life"), Stats->Stats.Life, 10);

	// Mirror off: facts do not reach the stats.
	Stats->bMirrorToFacts = false;
	Facts->SetFact(TEXT("gold"), 999);
	TestEqual(TEXT("mirror off: stats untouched"), Stats->Stats.Gold, 0);
	return true;
}
