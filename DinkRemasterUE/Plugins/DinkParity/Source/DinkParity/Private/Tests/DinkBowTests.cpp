// Dink.Gameplay.Bow.*: the bow as the 1997 engine plays it, on the converted item-b1.c (verbatim) and dam-a1.c.
//
//  - activate_bow (dink.cpp:9397-9408): Dink stops on the draw's first picture (seq 0, pseq 100 + dir, pframe 1), g_bowStatus
//    active for the calling script, hitme false, time 0; the script waits (ugly_return(2)).
//  - the 100 ms status timer sets hitme while the bow is drawn (dink.cpp:17339-17344).
//  - process_bow (dink.cpp:14564-14621), Dink's brain every frame while the bow is drawn (14761-14766): a pull every 10 ms of engine time
//    (once a 60 Hz frame) adds 7 once hitme is set, at most 500, pframe = 4 * time / 500 + 1; when the attack key is up (sjoy.letgo[1])
//    the bow is put down, last_power = time and the script runs on at once (run_script).
//  - get_last_bow_power (dink.cpp:9410-9414); item-b1.c `use`: no arrow below 100, else a brain-11 missile (dam-a1) of strength
//    (power / 100) * max(1, strength / 5), tripled one time in three with &bowlore 1 (random(3, 1) == 1), speed 6, range 10, flying.
//  - the arrow is a missile (missile_brain, dink.cpp:14240-14420): hardness 1 stops it (dam-a1 `damage` with &missile_target 0), low
//    hardness 2 does not stop a flyer, and a sprite it reaches takes strength / 2 + rand() % (strength / 2) + 1 - defense, at least 0
//    (dink.cpp:14363-14394).
//
// Headless, with virtual sprites, on SCR_010 (no live placement, no base script) with its hardness replaced by a test map.

#include "DinkTestHelpers.h"
#include "DinkCombat.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkInventoryComponent.h"
#include "DinkRandom.h"
#include "DinkStorySubsystem.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace DinkBowTest
{
	constexpr int32 TestScreen = 10;

	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* G = nullptr;
		bool IsValid() const { return Facts && World && Story && Story->IsReady() && G && G->HasData(); }
	};

	/**
	 * A new game (fists in slot 1), the bow picked up (slot 2) and armed, Dink on the test screen at (100, 200) facing east, an empty
	 * hardness map there (Wall: a column of that code at engine x 200), adaptation off, then real time (not instant mode).
	 */
	FEnv Make(FAutomationTestBase& Test, int32 WallCode = 0)
	{
		FEnv E;
		UGameInstance* GI = DinkTest::MakeOuterGameInstance();
		E.Facts = NewObject<UDinkFactSubsystem>(GI);
		FString Error;
		Test.TestTrue(TEXT("facts table loads"), E.Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
		E.World = NewObject<UDinkWorldStateSubsystem>(GI);
		E.Story = NewObject<UDinkStorySubsystem>(GI);
		Test.TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), E.Story->SetupStandalone(E.Facts, E.World, &Error));
		E.Story->StorySeed = 1997;
		E.Story->ResetRuntime();
		E.Story->bInstantMode = true;
		E.D = E.Story->GetDirector();
		E.G = E.Story->GetGameplay();
		if (!E.IsValid())
		{
			return E;
		}
		E.G->Adaptation.bEnabled = false;
		TSharedPtr<FDinkHardnessMap> Map = MakeShared<FDinkHardnessMap>();
		Map->Screen = TestScreen;
		Map->Set(0, 0, 0);
		if (WallCode != 0)
		{
			for (int32 Y = 0; Y < FDinkHardnessMap::Height; ++Y)
			{
				for (int32 X = 180; X < 184; ++X) // engine x 200-203
				{
					Map->Set(X, Y, static_cast<uint8>(WallCode));
				}
			}
		}
		const_cast<FDinkGameplayData&>(E.G->GetData()).SetHardnessOverride(TestScreen, Map);
		E.G->StartNewGame();
		E.Story->RunUntilIdle();
		E.Story->OnScreenEntered(TestScreen);
		E.Story->RunUntilIdle();
		FDinkSprite& Dink = E.D->GetDink();
		Dink.Screen = TestScreen;
		Dink.X = 100;
		Dink.Y = 200;
		Dink.Dir = 6;
		Test.TestEqual(TEXT("the bow goes into item slot 2"), E.G->AddItem(TEXT("item-b1"), false), 1);
		E.Story->RunUntilIdle();
		Test.TestTrue(TEXT("arm slot 2 (item-b1)"), E.G->ArmItemSlot(2));
		E.Story->RunUntilIdle();
		E.Story->bInstantMode = false;
		return E;
	}

	void Frame(FEnv& E, int32 N = 1)
	{
		for (int32 i = 0; i < N; ++i)
		{
			E.Story->Advance(1.0 / 60.0);
		}
	}

	int32 FindByScript(const FEnv& E, const TCHAR* Script)
	{
		TArray<int32> Keys;
		E.D->GetSprites().GetKeys(Keys);
		Keys.Sort();
		for (const int32 K : Keys)
		{
			const FDinkSprite* S = E.D->FindSprite(K);
			if (S && S->bActive && S->Script == FName(Script))
			{
				return K;
			}
		}
		return 0;
	}

	/** A still target (brain 10, frozen: it never wanders, so no rand() is drawn for it) with hit points and a hardbox (the pill bug's picture). */
	int32 MakeTarget(FEnv& E, int32 X, int32 Y, int32 Hp, int32 Defense)
	{
		const int32 H = E.D->CreateVirtualSprite(TestScreen, X, Y);
		FDinkSprite& T = *E.D->FindSprite(H);
		UDinkDirector::InitCreatedSprite(T);
		T.bSpawned = false;
		T.bFrozen = true;
		T.Props.Add(TEXT("brain"), 10);
		T.Props.Add(TEXT("hitpoints"), Hp);
		T.Props.Add(TEXT("defense"), Defense);
		T.Props.Add(TEXT("pseq"), 131);
		T.Props.Add(TEXT("pframe"), 1);
		return H;
	}

	/** Holds the attack key for Frames frames, then lets go and runs one frame (the release). Returns the power the script read. */
	int32 Shoot(FEnv& E, int32 Frames)
	{
		E.G->PlayerAttackPress();
		Frame(E, Frames);
		E.G->PlayerAttackRelease();
		Frame(E);
		return E.G->GetLastBowPower();
	}

	void CheckOriginal(FAutomationTestBase& Test, const TCHAR* Script, const TArray<FString>& Strings)
	{
		FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("../bin/dink/story") / (FString(Script) + TEXT(".c")));
		if (!IFileManager::Get().FileExists(*Path))
		{
			Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("../Dink-Smallwood-Remaster/bin/dink/story") / (FString(Script) + TEXT(".c")));
		}
		FString Source;
		if (!FFileHelper::LoadFileToString(Source, *Path))
		{
			Test.AddInfo(FString::Printf(TEXT("data repo not found (%s): verbatim check skipped"), *Path));
			return;
		}
		for (const FString& S : Strings)
		{
			Test.TestTrue(FString::Printf(TEXT("\"%s\" occurs verbatim in %s.c"), *S, Script), Source.Contains(S, ESearchCase::CaseSensitive));
		}
	}
}

using namespace DinkBowTest;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBowChargeTest, "Dink.Gameplay.Bow.ChargeTiming", DINK_TEST_FLAGS)
bool FDinkBowChargeTest::RunTest(const FString& Parameters)
{
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	const int32 Weapon = E.G->GetWeaponInstance();
	TestTrue(TEXT("item-b1 is armed (its instance lives)"), Weapon != 0 && E.D->GetInventory()->GetArmedItem() == TEXT("item-b1"));

	// The press runs `use`: activate_bow blocks the script and draws the bow (dink.cpp:9397-9408).
	TestTrue(TEXT("the attack key runs item-b1 use"), E.G->PlayerAttackPress());
	TestTrue(TEXT("activate_bow: the bow is drawn"), E.G->IsBowActive());
	TestEqual(TEXT("for the weapon's script instance"), E.G->GetBowInstance(), Weapon);
	const FDinkScriptInstance* I = E.Story->FindInstance(Weapon);
	TestTrue(TEXT("the script waits in activate_bow (ugly_return(2))"), I && I->State == EDinkInstanceState::Blocked && I->Block == EDinkBlock::Bow);
	TestEqual(TEXT("Dink's animation stops: seq 0"), E.D->GetDink().GetProp(TEXT("seq")), 0);
	TestEqual(TEXT("the draw picture: pseq 100 + dir"), E.D->GetDink().GetProp(TEXT("pseq")), 106);
	TestEqual(TEXT("pframe 1"), E.D->GetDink().GetProp(TEXT("pframe")), 1);
	TestEqual(TEXT("time 0"), E.G->GetBowPower(), 0);
	// While drawn, the brain does nothing else (dink.cpp:14761-14766): no second `use`, no spell, no talk.
	TestFalse(TEXT("no second use while drawn"), E.G->PlayerAttack());
	TestFalse(TEXT("no cast while drawn"), E.G->PlayerCastMagic());

	// Hold: nothing until the first 100 ms status tick sets hitme, then 7 a frame up to 500.
	TArray<int32> Power;
	for (int32 F = 0; F < 100; ++F)
	{
		Frame(E);
		Power.Add(E.G->GetBowPower());
	}
	int32 Still = 0;
	while (Still < Power.Num() && Power[Still] == 0)
	{
		++Still;
	}
	TestTrue(FString::Printf(TEXT("hitme comes with the first status tick: %d frames at power 0 (at most 7 = 116 ms)"), Still), Still >= 1 && Still <= 7);
	bool bSteps = true;
	int32 Full = INDEX_NONE;
	for (int32 F = Still; F < Power.Num(); ++F)
	{
		const int32 Expected = FMath::Min(UDinkGameplay::BowMaxPower, UDinkGameplay::BowPullPerTick * (F - Still + 1));
		bSteps &= Power[F] == Expected;
		if (Full == INDEX_NONE && Power[F] == UDinkGameplay::BowMaxPower)
		{
			Full = F + 1;
		}
	}
	TestTrue(TEXT("then 7 a frame (a pull every 10 ms, one per 60 Hz frame), capped at 500"), bSteps);
	TestEqual(TEXT("500 is reached 72 pulls after hitme (7 x 71 = 497)"), Full - Still, 72);
	AddInfo(FString::Printf(TEXT("full draw %d frames after the press = %.3f s; 100 power (one arrow) after %d frames = %.3f s"), Full, Full / 60.0, Still + 15, (Still + 15) / 60.0));
	TestEqual(TEXT("the picture follows the draw: pframe 5 at full power"), E.D->GetDink().GetProp(TEXT("pframe")), 5);
	TestTrue(TEXT("still drawn while the key is held"), E.G->IsBowActive());
	TestEqual(TEXT("no arrow before the release"), FindByScript(E, TEXT("dam-a1")), 0);

	// The release: the bow is put down at the next frame, last_power = time, the script runs on and shoots (strength 3: power 5 * max(1, 3 / 5)).
	E.G->PlayerAttackRelease();
	Frame(E);
	TestFalse(TEXT("released: the bow is down"), E.G->IsBowActive());
	TestEqual(TEXT("get_last_bow_power = 500"), E.G->GetLastBowPower(), 500);
	const int32 Arrow = FindByScript(E, TEXT("dam-a1"));
	const FDinkSprite* A = E.D->FindSprite(Arrow);
	if (TestNotNull(TEXT("an arrow (brain 11, dam-a1)"), A))
	{
		TestEqual(TEXT("brain 11"), A->GetProp(TEXT("brain")), 11);
		TestEqual(TEXT("strength (500 / 100) * max(1, 3 / 5) = 5"), A->GetProp(TEXT("strength")), 5);
		TestEqual(TEXT("speed 6"), A->GetProp(TEXT("speed")), 6);
		TestEqual(TEXT("range 10"), A->GetProp(TEXT("range")), 10);
		TestEqual(TEXT("flying"), A->GetProp(TEXT("flying")), 1);
		TestEqual(TEXT("brain_parm 1: it never hits Dink"), A->GetProp(TEXT("brain_parm")), 1);
		TestTrue(TEXT("it leaves 30 px ahead of Dink (east) and flies east"), A->X >= 130 && A->GetProp(TEXT("mx")) == 6);
	}
	TestTrue(TEXT("the weapon's script is idle again (not waiting)"), E.Story->FindInstance(Weapon) && E.Story->FindInstance(Weapon)->State != EDinkInstanceState::Blocked);

	// A tap (PlayerAttack: press and let go at once): the release comes at the next frame with time 0: no arrow (item-b1.c:13-16).
	for (int32 F = 0; F < 200; ++F)
	{
		Frame(E); // the first arrow flies past x 1000, where missile_brain ends it (dink.cpp:14319)
	}
	TestEqual(TEXT("the first arrow is gone past x 1000"), FindByScript(E, TEXT("dam-a1")), 0);
	TestTrue(TEXT("a tap draws the bow"), E.G->PlayerAttack() && E.G->IsBowActive());
	Frame(E);
	TestFalse(TEXT("and lets go at the next frame"), E.G->IsBowActive());
	TestEqual(TEXT("with power 0"), E.G->GetLastBowPower(), 0);
	TestEqual(TEXT("no arrow below 100"), FindByScript(E, TEXT("dam-a1")), 0);
	// At most 14 pulls (98) shoot nothing either; 15 and more (105) do: power 1 * max(1, 3 / 5 = 0 -> 1) = 1. (Shoot holds N frames and
	// releases on the next, whose pull still counts; hitme takes 1-7 of them.)
	const int32 Low = Shoot(E, 14);
	TestTrue(FString::Printf(TEXT("a short draw (%d) shoots nothing"), Low), Low < 100 && FindByScript(E, TEXT("dam-a1")) == 0);
	Frame(E, 10);
	const int32 Short = Shoot(E, 21);
	TestTrue(FString::Printf(TEXT("15 pulls and more shoot (%d)"), Short), Short >= 100 && FindByScript(E, TEXT("dam-a1")) != 0);
	CheckOriginal(*this, TEXT("item-b1"), { TEXT("activate_bow();"), TEXT("&mypower = get_last_bow_power();"), TEXT("if (&mypower < 100)"), TEXT("&mypower / 100;"), TEXT("&temp / 5;") });
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBowDamageTest, "Dink.Gameplay.Bow.ArrowDamageAndBowLore", DINK_TEST_FLAGS)
bool FDinkBowDamageTest::RunTest(const FString& Parameters)
{
	// Seth's numbers (s7-boss.c:22-23: 300 hp, defense 25) at strength 25 (item-b1 has no bonus: (500 / 100) * (25 / 5) = 25):
	//   no lore:             25 / 2 + rand() % 12 + 1 - 25 = -12 .. -1, so 0 (probe_route.md 2.6: "never");
	//   lore, power shot:    75 / 2 + rand() % 37 + 1 - 25 = 13 .. 49;
	//   lore, no power shot: 25 as without lore.
	struct FCase
	{
		const TCHAR* Name;
		int32 BowLore;
		TArray<int32> Rolls;
		int32 Strength;
		int32 Damage;
		TArray<int32> Moduli;
	};
	const TArray<FCase> Cases = {
		{ TEXT("no bow lore, best roll"), 0, { 11 }, 25, 0, { 12 } },
		{ TEXT("bow lore, power shot (random(3,1) = 1), worst roll"), 1, { 0, 0 }, 75, 13, { 3, 37 } },
		{ TEXT("bow lore, power shot, best roll"), 1, { 0, 36 }, 75, 49, { 3, 37 } },
		{ TEXT("bow lore, no power shot (random(3,1) = 2)"), 1, { 1, 11 }, 25, 0, { 3, 12 } },
	};
	for (const FCase& Case : Cases)
	{
		FEnv E = Make(*this);
		if (!E.IsValid())
		{
			return false;
		}
		E.Facts->SetFact(TEXT("strength"), 25);
		E.Facts->SetFact(TEXT("bowlore"), Case.BowLore);
		const int32 Target = MakeTarget(E, 320, 200, 300, 25);
		TSharedRef<FDinkScriptedRandomSource> Rolls = MakeShared<FDinkScriptedRandomSource>(Case.Rolls);
		E.G->SetRandomSource(Rolls);
		Shoot(E, 100);
		const int32 Arrow = FindByScript(E, TEXT("dam-a1"));
		const FDinkSprite* A = E.D->FindSprite(Arrow);
		TestEqual(FString::Printf(TEXT("%s: arrow strength"), Case.Name), A ? A->GetProp(TEXT("strength")) : -1, Case.Strength);
		Frame(E, 60);
		const FDinkSprite* T = E.D->FindSprite(Target);
		TestEqual(FString::Printf(TEXT("%s: Seth-like target (defense 25) loses %d"), Case.Name, Case.Damage), T ? 300 - T->GetProp(TEXT("hitpoints")) : -1, Case.Damage);
		TestTrue(FString::Printf(TEXT("%s: the arrow is gone (dam-a1 damage: sp_active 0)"), Case.Name), FindByScript(E, TEXT("dam-a1")) == 0);
		auto Join = [](const TArray<int32>& V) { FString Out; for (const int32 X : V) { Out += FString::Printf(TEXT("%d "), X); } return Out; };
		TestEqual(FString::Printf(TEXT("%s: the draws are the lottery's and the missile's, in that order"), Case.Name), Join(Rolls->RequestedModuli), Join(Case.Moduli));
	}
	// A weaker target and Dink's strength 9 (as in chapter 7): (500 / 100) * (9 / 5) = 5, against defense 0: 2 + rand() % 2 + 1.
	{
		FEnv E = Make(*this);
		if (!E.IsValid())
		{
			return false;
		}
		E.Facts->SetFact(TEXT("strength"), 9);
		const int32 Target = MakeTarget(E, 320, 200, 50, 0);
		E.G->SetRandomSource(MakeShared<FDinkScriptedRandomSource>(TArray<int32>{ 1 }));
		Shoot(E, 100);
		Frame(E, 60);
		TestEqual(TEXT("strength 9: the arrow does 5 / 2 + 1 + 1 = 4 to defense 0"), 50 - E.D->FindSprite(Target)->GetProp(TEXT("hitpoints")), 4);
	}
	CheckOriginal(*this, TEXT("item-b1"), { TEXT("if (&bowlore == 1)"), TEXT("&temp = random(3, 1);"), TEXT("&mypower * 3;"), TEXT("sp_strength(&junk, &mypower);") });
	CheckOriginal(*this, TEXT("s7-boss"), { TEXT("sp_hitpoints(&current_sprite, 300);"), TEXT("sp_defense(&current_sprite, 25);") });
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBowHardnessTest, "Dink.Gameplay.Bow.ArrowRespectsHardness", DINK_TEST_FLAGS)
bool FDinkBowHardnessTest::RunTest(const FString& Parameters)
{
	// missile_brain + check_if_move_is_legal (dink.cpp:14240-14300, 13416): a wall (hardness 1) between Dink and the target stops the
	// arrow (dam-a1 `damage` with &missile_target 0: it stops where it is, brain 0, nohit, the script ends); low hardness (2: water,
	// fences) does not stop it (item-b1.c sp_flying(&junk, 1)), and it hits the target behind.
	for (const int32 Code : { 1, 2 })
	{
		FEnv E = Make(*this, Code);
		if (!E.IsValid())
		{
			return false;
		}
		E.Facts->SetFact(TEXT("strength"), 25);
		E.Facts->SetFact(TEXT("bowlore"), 1);
		const int32 Target = MakeTarget(E, 320, 200, 300, 0);
		E.G->SetRandomSource(MakeShared<FDinkScriptedRandomSource>(TArray<int32>{ 0, 0 }));
		Shoot(E, 100);
		const int32 Arrow = FindByScript(E, TEXT("dam-a1"));
		double MaxX = 0.0;
		for (int32 F = 0; F < 60; ++F)
		{
			Frame(E);
			if (const FDinkSprite* A = E.D->FindSprite(Arrow))
			{
				MaxX = FMath::Max(MaxX, A->X);
			}
		}
		const int32 Lost = 300 - E.D->FindSprite(Target)->GetProp(TEXT("hitpoints"));
		AddInfo(FString::Printf(TEXT("hardness %d at x 200: the arrow got to x %.0f, the target lost %d"), Code, MaxX, Lost));
		if (Code == 1)
		{
			TestTrue(TEXT("a wall stops the arrow before it"), MaxX < 200.0);
			TestEqual(TEXT("the target behind the wall is not hit"), Lost, 0);
			const FDinkSprite* A = E.D->FindSprite(Arrow);
			TestTrue(TEXT("the arrow stuck in the wall (dam-a1: sp_brain 0, sp_speed 0)"), !A || A->GetProp(TEXT("brain")) == 0);
		}
		else
		{
			TestTrue(TEXT("a flying arrow crosses low hardness"), MaxX > 204.0);
			TestEqual(TEXT("and hits the target behind it: 75 / 2 + 0 + 1 = 38 to defense 0"), Lost, 38);
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBowItemWiringTest, "Dink.Gameplay.Bow.ItemUseAndDisarm", DINK_TEST_FLAGS)
bool FDinkBowItemWiringTest::RunTest(const FString& Parameters)
{
	// item-b1.c `arm` (the bow's pictures, no stat bonus), `use` (activate_bow), `disarm` (kill_this_task). Arming the fists runs the
	// bow's disarm (arm_weapon, dink.cpp:7850-7870): its instance ends; a bow drawn by that instance is put down without an arrow.
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	TestEqual(TEXT("item-b1 arm: no strength bonus (new game strength 3)"), E.Facts->GetFact(TEXT("strength")), 3);
	TestEqual(TEXT("&cur_weapon = 2"), E.Facts->GetFact(TEXT("cur_weapon")), 2);
	const int32 Bow = E.G->GetWeaponInstance();
	TestTrue(TEXT("the drawn bow belongs to item-b1's instance"), E.G->PlayerAttackPress() && E.G->GetBowInstance() == Bow);
	Frame(E, 30);
	TestTrue(TEXT("arm the fists (slot 1) while drawn"), E.G->ArmItemSlot(1));
	const FDinkScriptInstance* Old = E.Story->FindInstance(Bow);
	TestTrue(TEXT("item-b1 disarm: kill_this_task ends its instance"), !Old || !Old->IsAlive());
	E.G->PlayerAttackRelease();
	Frame(E);
	TestFalse(TEXT("the bow is put down"), E.G->IsBowActive());
	TestEqual(TEXT("no arrow"), FindByScript(E, TEXT("dam-a1")), 0);
	TestTrue(TEXT("fists armed"), E.D->GetInventory()->GetArmedItem() == FName(TEXT("item-fst")));
	// And back: the bow draws again, and its last power is what the next shot reads.
	TestTrue(TEXT("arm the bow again"), E.G->ArmItemSlot(2));
	const int32 Power = Shoot(E, 40);
	TestTrue(FString::Printf(TEXT("a new draw after re-arming (%d)"), Power), Power > 100 && FindByScript(E, TEXT("dam-a1")) != 0);
	CheckOriginal(*this, TEXT("item-b1"), { TEXT("void disarm(void)"), TEXT("kill_this_task();") });
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBowInitPoseTest, "Dink.Gameplay.Bow.InitSequenceHardbox", DINK_TEST_FLAGS)
bool FDinkBowInitPoseTest::RunTest(const FString& Parameters)
{
	// s7-mil.c:9-13 loads Seth's pictures with init("load_sequence_now ..."); dink.ini has 581-589 but not 580, the pose he holds while he winds
	// up a bomb (s7-boss.c:45-66). figure_out (dink.cpp:2335-2344) reads a sequence that is not active yet from the line and gives every frame the
	// line's hardbox (LoadSpriteSingleFrame, dink.cpp:1899-1922). Before, the remaster only recorded the line: Seth in his pose had no hardbox
	// and arrows passed through him.
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	E.Facts->SetFact(TEXT("strength"), 25);
	E.Facts->SetFact(TEXT("bowlore"), 1);
	const int32 Seth = MakeTarget(E, 320, 200, 300, 25);
	FDinkSprite& S = *E.D->FindSprite(Seth);
	S.Props.Add(TEXT("seq"), 0);
	S.Props.Add(TEXT("pseq"), 580);
	S.Props.Add(TEXT("pframe"), 1);
	int32 L = 0, T = 0, R = 0, B = 0;
	TestFalse(TEXT("before the init line, pose 580 has no hardbox (dink.ini lacks it)"), E.G->GetHardbox(S, L, T, R, B));
	TestTrue(TEXT("s7-mil.c's line for 580 defines it"), E.G->ApplyInitLine(TEXT("load_sequence_now graphics\\effects\\magic\\pose 580 75 41 129 -30 -16 31 10")));
	TestFalse(TEXT("a sequence dink.ini has (581) is left alone"), E.G->ApplyInitLine(TEXT("load_sequence_now graphics\\effects\\magic\\seth1w 581 75 43 133 -19 -16 23 16")));
	TestFalse(TEXT("a line without an animation's numbers defines nothing"), E.G->ApplyInitLine(TEXT("load_sequence_now graphics\\foo 590 NOTANIM")));
	if (TestTrue(TEXT("pose 580 has the line's hardbox"), E.G->GetHardbox(*E.D->FindSprite(Seth), L, T, R, B)))
	{
		TestTrue(FString::Printf(TEXT("-30 -16 31 10 around 320,200 (%d %d %d %d)"), L, T, R, B), L == 290 && T == 184 && R == 351 && B == 210);
	}
	const FDinkFrameInfo* Walk = E.G->GetData().FindFrame(581, 1);
	TestTrue(TEXT("581 keeps dink.ini's box"), Walk && Walk->Left == -15 && Walk->Bottom == 17);
	// An arrow (power shot) now meets him in his pose: 75 / 2 + 0 + 1 - 25 = 13.
	E.G->SetRandomSource(MakeShared<FDinkScriptedRandomSource>(TArray<int32>{ 0, 0 }));
	Shoot(E, 100);
	Frame(E, 60);
	TestEqual(TEXT("the arrow hits Seth's pose: 13"), 300 - E.D->FindSprite(Seth)->GetProp(TEXT("hitpoints")), 13);
	CheckOriginal(*this, TEXT("s7-mil"), { TEXT("pose 580 75 41 129 -30 -16 31 10") });
	return true;
}
