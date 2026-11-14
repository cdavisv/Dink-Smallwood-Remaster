// Dink.AI.*: the original engine's brains (UDinkGameplay, DinkBrains.cpp) headless, on virtual sprites made
// from map.dat's live placements, real scripts and each screen's real hardness map
// (Content/Dink/Data/Gameplay/Hardness), with fixed seeds. The 3D adaptation layer is off (Classic) unless a
// test switches it on. Game time advances in the engine's 60 Hz frames.

#include "DinkTestHelpers.h"
#include "DinkCollision.h"
#include "DinkCombat.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkLayout.h"
#include "DinkRandom.h"
#include "DinkStorySubsystem.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/StaticMeshComponent.h"

namespace DinkAITest
{
	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* G = nullptr;
		bool IsValid() const { return Facts && World && Story && Story->IsReady() && G && G->HasData(); }
	};

	FEnv Make(FAutomationTestBase& Test, int32 Seed = 1997)
	{
		FEnv E;
		UGameInstance* GI = DinkTest::MakeOuterGameInstance();
		E.Facts = NewObject<UDinkFactSubsystem>(GI);
		FString Error;
		Test.TestTrue(TEXT("facts table loads"), E.Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
		E.World = NewObject<UDinkWorldStateSubsystem>(GI);
		E.Story = NewObject<UDinkStorySubsystem>(GI);
		Test.TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), E.Story->SetupStandalone(E.Facts, E.World, &Error));
		E.Story->StorySeed = Seed;
		E.Story->ResetRuntime();
		E.Story->bInstantMode = true;
		E.D = E.Story->GetDirector();
		E.G = E.Story->GetGameplay();
		Test.TestTrue(TEXT("gameplay data loaded (Scripts/sync_gameplay_data.py)"), E.G && E.G->HasData());
		if (E.G)
		{
			E.G->Adaptation.bEnabled = false; // parity: Classic rules
			E.G->SetRandomSeed(Seed);
		}
		return E;
	}

	void Settle(FEnv& E)
	{
		E.Story->RunUntilIdle();
		E.G->ProcessDamage();
		E.Story->RunUntilIdle();
	}

	void Enter(FEnv& E, int32 Screen)
	{
		E.Story->OnScreenEntered(Screen);
		Settle(E);
	}

	/** One 60 Hz engine frame of game time. */
	void Frame(FEnv& E)
	{
		E.Story->Advance(1.0 / 60.0);
	}

	void ToughDink(FEnv& E, int32 Life = 1000)
	{
		E.Facts->SetFact(TEXT("lifemax"), Life);
		E.Facts->SetFact(TEXT("life"), Life);
	}

	int32 FindByScript(const FEnv& E, const TCHAR* Script)
	{
		TArray<int32> Keys;
		E.D->GetSprites().GetKeys(Keys);
		Keys.Sort();
		for (const int32 K : Keys)
		{
			const FDinkSprite& S = E.D->GetSprites()[K];
			if (S.Script == FName(Script) && S.bActive)
			{
				return K;
			}
		}
		return 0;
	}

	/** True if a straight, 2*HalfWidth px wide band from (X0,Y) to (X1,Y) has no hardness. */
	bool BandFree(const FEnv& E, int32 Screen, int32 X0, int32 X1, int32 Y, int32 HalfWidth)
	{
		for (int32 X = FMath::Min(X0, X1); X <= FMath::Max(X0, X1); ++X)
		{
			for (int32 Dy = -HalfWidth; Dy <= HalfWidth; ++Dy)
			{
				if (E.G->GetHard(Screen, X, Y + Dy) != 0)
				{
					return false;
				}
			}
		}
		return true;
	}

	int32 Dist(const FDinkSprite& A, const FDinkSprite& B)
	{
		return FMath::Max(FMath::Abs(FMath::RoundToInt32(A.X - B.X)), FMath::Abs(FMath::RoundToInt32(A.Y - B.Y)));
	}

	bool OnHardness(const FEnv& E, const FDinkSprite& S)
	{
		const int32 Code = E.G->GetHard(S.Screen, FMath::RoundToInt32(S.X), FMath::RoundToInt32(S.Y));
		// get_hard (D:569-575) reads a stamped hardbox of a placement with prop != 0 (a map.dat warp: SCR_003's door S003_P14) as 0 for every
		// sprite, so a villager may stand in the doorway's box; only Dink warps there.
		return Code != 0 && !(Code > 100 && E.G->GetPlacementProp(FDinkOriginId(S.Screen, Code - 100)) != 0);
	}

	/**
	 * The engine's screen: map x 0..599 (engine x 20..619), y 0..399, give or take a step. pill_brain turns back
	 * only once x < 18 (engine), so a pillbug can stand at engine x 17 (map -3) for a think: the slack covers that.
	 */
	bool InScreen(const FDinkSprite& S, int32 Slack)
	{
		return S.X >= 20 - Slack && S.X <= 620 + Slack && S.Y >= -Slack && S.Y <= 400 + Slack;
	}

	/** A Bonca like en-bonc / s1-cavem made directly as a sprite (no script): brain 9, chases Target, melee base 540. */
	int32 MakeBonca(FEnv& E, int32 Screen, int32 X, int32 Y, int32 Target, int32 Strength = 8)
	{
		const int32 H = E.D->CreateVirtualSprite(Screen, X, Y);
		FDinkSprite& S = *E.D->FindSprite(H);
		UDinkDirector::InitCreatedSprite(S);
		S.Props.Add(TEXT("brain"), 9);
		S.Props.Add(TEXT("speed"), 1);
		S.Props.Add(TEXT("timing"), 33);
		S.Props.Add(TEXT("distance"), 50);
		S.Props.Add(TEXT("base_walk"), 530);
		S.Props.Add(TEXT("base_attack"), 540);
		S.Props.Add(TEXT("strength"), Strength);
		S.Props.Add(TEXT("hitpoints"), 20);
		S.Props.Add(TEXT("pseq"), 531);
		S.Props.Add(TEXT("pframe"), 1);
		S.Props.Add(TEXT("target"), Target);
		return H;
	}
}

using namespace DinkAITest;

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIPillbugChaseTest, "Dink.AI.Monster.PillbugChasesWithinHardness", DINK_TEST_FLAGS)
bool FDinkAIPillbugChaseTest::RunTest(const FString& Parameters)
{
	// A pillbug (en-pill, brain 9 from its script, no base_attack) with Dink as target walks at him and never
	// stands on a hard pixel or leaves its screen; with no target it wanders diagonally (pill_brain, D:12887).
	FEnv E = Make(*this, 1997);
	if (!E.IsValid())
	{
		return false;
	}
	ToughDink(E);
	Enter(E, 278);
	const int32 Bug = E.D->HandleForPlacement(278, 4);
	FDinkSprite* B = E.D->FindSprite(Bug);
	if (!TestTrue(TEXT("pillbug S278_P04 is a sprite running en-pill (brain 9)"), B && B->Script == FName(TEXT("en-pill")) && B->GetProp(TEXT("brain")) == 9))
	{
		return false;
	}
	TestFalse(TEXT("the pillbug starts on free ground"), OnHardness(E, *B));
	// Dink 150 px away along a clear band, as a player standing in the open.
	FDinkSprite& Dink = E.D->GetDink();
	int32 Chosen = 0;
	for (const int32 Dx : { 150, -150, 120, -120, 100, -100 })
	{
		const int32 X = FMath::RoundToInt32(B->X) + Dx;
		if (X > 40 && X < 600 && BandFree(E, 278, FMath::RoundToInt32(B->X), X, FMath::RoundToInt32(B->Y), 12))
		{
			Chosen = X;
			break;
		}
	}
	if (!TestTrue(TEXT("a clear spot for Dink beside the pillbug"), Chosen != 0))
	{
		return false;
	}
	Dink.Screen = 278;
	Dink.X = Chosen;
	Dink.Y = B->Y;
	B->Props.Add(TEXT("target"), 1); // what sp_target(&current_sprite, 1) in en-pill main does half the time
	const int32 Start = Dist(*B, Dink);
	int32 Closest = Start, OnHard = 0, OffScreen = 0;
	for (int32 F = 0; F < 60 * 30; ++F)
	{
		Frame(E);
		B = E.D->FindSprite(Bug);
		if (!B || !B->bActive)
		{
			break;
		}
		Closest = FMath::Min(Closest, Dist(*B, E.D->GetDink()));
		OnHard += OnHardness(E, *B) ? 1 : 0;
		OffScreen += InScreen(*B, 4) ? 0 : 1;
	}
	AddInfo(FString::Printf(TEXT("pillbug: start %d px from Dink, closest %d px in 30 s"), Start, Closest));
	TestTrue(TEXT("it closes on Dink (within 10 px)"), Closest <= 10);
	TestEqual(TEXT("frames it stood on a hard pixel"), OnHard, 0);
	TestEqual(TEXT("frames it was off its screen"), OffScreen, 0);
	TestTrue(TEXT("touching Dink cost him life (touch damage 1)"), E.Facts->GetFact(TEXT("life")) < 1000);

	// Without a target: a long wander stays on free ground and on the screen, and walks diagonally only.
	// (A pillbug that never chased: no target, standing still. One that chased keeps its last cardinal step
	// until a walk cycle ends and it rolls a diagonal; and autoreverse_diag has no answer for 2/6/8, so such a
	// pillbug can keep pushing into a wall with dir 0 - the engine's behaviour, not tested here.)
	B = E.D->FindSprite(Bug);
	B->Props.Add(TEXT("target"), 0);
	B->Props.Add(TEXT("mx"), 0);
	B->Props.Add(TEXT("my"), 0);
	B->Props.Add(TEXT("seq"), 0);
	B->SeqOrig = 0;
	B->Dir = 0;
	TSet<int32> Dirs;
	FString FirstOff;
	OnHard = OffScreen = 0;
	const double X0 = B->X, Y0 = B->Y;
	double Travelled = 0.0;
	double Px = B->X, Py = B->Y;
	E.D->GetDink().X = 1000; // far away (no touch)
	for (int32 F = 0; F < 60 * 120; ++F)
	{
		Frame(E);
		B = E.D->FindSprite(Bug);
		OnHard += OnHardness(E, *B) ? 1 : 0;
		OffScreen += InScreen(*B, 4) ? 0 : 1;
		if (!InScreen(*B, 4) && FirstOff.IsEmpty())
		{
			FirstOff = FString::Printf(TEXT("off screen at %.0f,%.0f dir %d mx %d my %d"), B->X, B->Y, B->Dir, B->GetProp(TEXT("mx")), B->GetProp(TEXT("my")));
			AddInfo(FirstOff);
		}
		if (B->GetProp(TEXT("mx")) != 0 || B->GetProp(TEXT("my")) != 0)
		{
			Dirs.Add(B->Dir);
		}
		Travelled += FMath::Abs(B->X - Px) + FMath::Abs(B->Y - Py);
		Px = B->X;
		Py = B->Y;
	}
	TestEqual(TEXT("wander: frames on a hard pixel"), OnHard, 0);
	TestEqual(TEXT("wander: frames off the screen"), OffScreen, 0);
	TestTrue(TEXT("wander: it moved"), Travelled > 100.0);
	bool bOnlyDiagonal = true;
	for (const int32 Dir : Dirs)
	{
		bOnlyDiagonal &= Dir == 1 || Dir == 3 || Dir == 7 || Dir == 9;
	}
	TestTrue(FString::Printf(TEXT("wander: diagonal directions only (%d seen)"), Dirs.Num()), bOnlyDiagonal && Dirs.Num() >= 2);
	AddInfo(FString::Printf(TEXT("wander: %.0f px in 120 s from %.0f,%.0f"), Travelled, X0, Y0));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIPeopleTest, "Dink.AI.People.VillagerWandersInBounds", DINK_TEST_FLAGS)
bool FDinkAIPeopleTest::RunTest(const FString& Parameters)
{
	// SmileStein (S003_P23, s1-h3-of, brain 16 in map.dat) in his house: people_brain sits and walks in turn
	// (find_action, D:13046) for 10 simulated minutes, never on a hard pixel, never off the screen; freeze
	// (a talk) stops him; his talk does not turn him to face Dink (run_through_tag_list_talk does not, D:14171).
	FEnv E = Make(*this, 7);
	if (!E.IsValid())
	{
		return false;
	}
	Enter(E, 3);
	const int32 Man = E.D->HandleForPlacement(3, 23);
	FDinkSprite* M = E.D->FindSprite(Man);
	if (!TestTrue(TEXT("SmileStein is brain 16"), M && M->GetProp(TEXT("brain")) == 16))
	{
		return false;
	}
	E.D->GetDink().X = 1000; // out of the way
	int32 OnHard = 0, OffScreen = 0, Sitting = 0, Walking = 0;
	double Travelled = 0.0, Px = M->X, Py = M->Y;
	for (int32 F = 0; F < 60 * 600; ++F)
	{
		Frame(E);
		M = E.D->FindSprite(Man);
		OnHard += OnHardness(E, *M) ? 1 : 0;
		OffScreen += InScreen(*M, 4) ? 0 : 1;
		Sitting += M->Action == 1 ? 1 : 0;
		Walking += M->Action == 2 ? 1 : 0;
		Travelled += FMath::Abs(M->X - Px) + FMath::Abs(M->Y - Py);
		Px = M->X;
		Py = M->Y;
	}
	AddInfo(FString::Printf(TEXT("SmileStein: %.0f px walked, %d frames sitting, %d walking in 10 min"), Travelled, Sitting, Walking));
	TestEqual(TEXT("frames on a hard pixel"), OnHard, 0);
	TestEqual(TEXT("frames off the screen"), OffScreen, 0);
	TestTrue(TEXT("he walks"), Travelled > 50.0 && Walking > 0);
	TestTrue(TEXT("he sits and thinks"), Sitting > 0);

	// freeze (what a talk script does with freeze(&current_sprite)): no movement.
	E.D->FindSprite(Man)->bFrozen = true;
	const double Fx = E.D->FindSprite(Man)->X, Fy = E.D->FindSprite(Man)->Y;
	for (int32 F = 0; F < 60 * 10; ++F)
	{
		Frame(E);
	}
	TestTrue(TEXT("frozen: he does not move"), E.D->FindSprite(Man)->X == Fx && E.D->FindSprite(Man)->Y == Fy);
	E.D->FindSprite(Man)->bFrozen = false;
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIDuckPigTest, "Dink.AI.Animals.DuckAndPig", DINK_TEST_FLAGS)
bool FDinkAIDuckPigTest::RunTest(const FString& Parameters)
{
	// duck_brain (D:12723): wanders in directions 1,3,4,6,7,9 (never straight up or down), quacks (sound 1) when
	// it pauses; pig_brain (D:13356): diagonals only, oinks (sounds 2-5). Both stay on free ground and on screen.
	FEnv E = Make(*this, 11);
	if (!E.IsValid())
	{
		return false;
	}
	E.D->GetDink().X = 1000;
	struct FCase { int32 Screen; int32 Placement; int32 Brain; TSet<int32> Allowed; const TCHAR* Sound; };
	const FCase Cases[] = {
		{ 2, 24, 3, { 1, 3, 4, 6, 7, 9 }, TEXT("(duck)") },
		{ 407, 2, 4, { 1, 3, 7, 9 }, TEXT("(pig)") },
	};
	for (const FCase& C : Cases)
	{
		Enter(E, C.Screen);
		E.D->GetDink().X = 1000;
		const int32 H = E.D->HandleForPlacement(C.Screen, C.Placement);
		FDinkSprite* S = E.D->FindSprite(H);
		if (!TestTrue(FString::Printf(TEXT("S%03d_P%02d is brain %d"), C.Screen, C.Placement, C.Brain), S && S->GetProp(TEXT("brain")) == C.Brain))
		{
			continue;
		}
		const int32 Cues0 = E.D->Audio.Cues.Num();
		TSet<int32> Dirs;
		int32 OnHard = 0, OffScreen = 0, Sounds = 0;
		double Travelled = 0.0, Px = S->X, Py = S->Y;
		for (int32 F = 0; F < 60 * 180; ++F)
		{
			Frame(E);
			S = E.D->FindSprite(H);
			if (S->GetProp(TEXT("mx")) != 0 || S->GetProp(TEXT("my")) != 0)
			{
				Dirs.Add(S->Dir);
			}
			OnHard += OnHardness(E, *S) ? 1 : 0;
			OffScreen += InScreen(*S, 4) ? 0 : 1;
			Travelled += FMath::Abs(S->X - Px) + FMath::Abs(S->Y - Py);
			Px = S->X;
			Py = S->Y;
		}
		for (int32 i = FMath::Max(0, Cues0 - 0); i < E.D->Audio.Cues.Num(); ++i)
		{
			Sounds += E.D->Audio.Cues[i].Contains(C.Sound) ? 1 : 0;
		}
		bool bAllowed = true;
		FString Seen;
		for (const int32 Dir : Dirs)
		{
			bAllowed &= C.Allowed.Contains(Dir);
			Seen += FString::Printf(TEXT(" %d"), Dir);
		}
		AddInfo(FString::Printf(TEXT("brain %d: %.0f px in 3 min, directions%s, %d sounds"), C.Brain, Travelled, *Seen, Sounds));
		TestTrue(FString::Printf(TEXT("brain %d: walks"), C.Brain), Travelled > 50.0);
		TestTrue(FString::Printf(TEXT("brain %d: only its directions"), C.Brain), bAllowed && Dirs.Num() >= 2);
		TestTrue(FString::Printf(TEXT("brain %d: makes its sound"), C.Brain), Sounds > 0);
		TestEqual(FString::Printf(TEXT("brain %d: frames on hardness"), C.Brain), OnHard, 0);
		TestEqual(FString::Printf(TEXT("brain %d: frames off screen"), C.Brain), OffScreen, 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIAttackDamageTest, "Dink.AI.Attack.DamageFormula", DINK_TEST_FLAGS)
bool FDinkAIAttackDamageTest::RunTest(const FString& Parameters)
{
	// A brain-9 monster in range starts base_attack+dir (cardinal, get_distance_and_dir), and its hit lands
	// when the animation reaches the special frame (542 frame 5: 4 x 75 ms): hurt_thing(strength/2 +
	// rand()%((strength+1)/2) + 1) minus Dink's defense, 1 at 50% when that is below 1 (D:15560, 6656). The
	// melee hit gives no immunity (only touch damage does: 400 ms, D:15652).
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	Enter(E, 100); // the cave: no placement there runs at &wizard_see 0
	FDinkSprite& Dink = E.D->GetDink();
	Dink.Screen = 100;
	Dink.X = 300;
	Dink.Y = 200;
	ToughDink(E, 100);
	E.Facts->SetFact(TEXT("defense"), 0);
	// Bonca 40 px east, same row: distance 40 < 50 -> it attacks west (4) at once.
	const int32 Bonca = MakeBonca(E, 100, 340, 200, 1, 8);
	auto Script = MakeShared<FDinkScriptedRandomSource>(TArray<int32>{ 3 });
	E.G->SetRandomSource(Script); // every rand() % n gives 3 % n
	double HitAt = -1.0;
	const double T0 = E.Story->GetNowMs();
	int32 Life = 100;
	for (int32 F = 0; F < 60 && HitAt < 0.0; ++F)
	{
		Frame(E);
		if (E.Facts->GetFact(TEXT("life")) < Life)
		{
			HitAt = E.Story->GetNowMs() - T0;
			Life = E.Facts->GetFact(TEXT("life"));
		}
	}
	const FDinkSprite* B = E.D->FindSprite(Bonca);
	TestEqual(TEXT("it attacks westwards (dir 4, seq 544)"), B->Dir, 4);
	// strength 8: 4 + (3 % 4) + 1 = 8; defense 0 -> 8
	TestEqual(TEXT("melee damage = 8/2 + rand()%4 + 1 - 0"), 100 - Life, 8);
	AddInfo(FString::Printf(TEXT("the hit landed %.0f ms after the attack began"), HitAt));
	TestTrue(TEXT("on the special frame: about 4 x 75 ms in (frame-rounded)"), HitAt >= 280.0 && HitAt <= 400.0);

	// Defense 6: 8 - 6 = 2.
	E.Facts->SetFact(TEXT("defense"), 6);
	E.Facts->SetFact(TEXT("life"), 100);
	for (int32 F = 0; F < 60 * 3 && E.Facts->GetFact(TEXT("life")) == 100; ++F)
	{
		Frame(E);
	}
	TestEqual(TEXT("defense 6: 2 damage"), 100 - E.Facts->GetFact(TEXT("life")), 2);
	// Defense 20: below 1 -> 1 when rand()%2 + 1 == 1 (3 % 2 = 1 -> 2: no damage), so nothing.
	E.Facts->SetFact(TEXT("defense"), 20);
	E.Facts->SetFact(TEXT("life"), 100);
	int32 Attacks = 0;
	for (int32 F = 0; F < 60 * 3; ++F)
	{
		Frame(E);
		Attacks += E.G->Events.Num() > 0 && E.G->Events.Last().StartsWith(TEXT("hit 1 by")) ? 1 : 0;
	}
	TestEqual(TEXT("defense 20: the 50% pity point misses with rand() = 3"), E.Facts->GetFact(TEXT("life")), 100);
	TestTrue(TEXT("it kept attacking (no immunity after a melee hit)"), Attacks >= 2);

	// Touch damage: notouch 400 ms after each touch (D:15652).
	E.Facts->SetFact(TEXT("defense"), 0);
	E.Facts->SetFact(TEXT("life"), 100);
	FDinkSprite* BB = E.D->FindSprite(Bonca);
	BB->Props.Add(TEXT("base_attack"), -1); // no melee now
	BB->Props.Add(TEXT("target"), 0);
	BB->bFrozen = true;
	BB->Props.Add(TEXT("touch_damage"), 4);
	Dink.X = BB->X;
	Dink.Y = BB->Y;
	for (int32 F = 0; F < 60; ++F) // one second
	{
		Frame(E);
	}
	const int32 Touches = (100 - E.Facts->GetFact(TEXT("life"))) / 4;
	AddInfo(FString::Printf(TEXT("touch damage 4 for 1 s: %d touches"), Touches));
	TestTrue(TEXT("touch: once per 400 ms immunity (2 or 3 in a second)"), Touches >= 2 && Touches <= 3);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIBoncaKillsIdleDinkTest, "Dink.AI.Bonca.KillsIdleDink", DINK_TEST_FLAGS)
bool FDinkAIBoncaKillsIdleDinkTest::RunTest(const FString& Parameters)
{
	// en-bonc on SCR_029 (strength 8, touch 4, attack wait random(4000,0) from its `attack`) against a new
	// game's unarmed Dink who stands still: 10 life, defense 0. The numbers imply: it walks the gap at
	// speed 1 every 33 ms (30 px/s), its first hit lands ~0.3 s after it comes within 50 px, each hit takes
	// 5..8 and touches take 4 per 400 ms, so two hits (or one and a touch) kill him; the second attack comes
	// within 4.4 s of the first. Upper bound: walk + 0.4 + 4.4 s (+ re-aims).
	FEnv E = Make(*this, 1997);
	if (!E.IsValid())
	{
		return false;
	}
	Enter(E, 29);
	const int32 Bonca = E.D->HandleForPlacement(29, 3);
	FDinkSprite* B = E.D->FindSprite(Bonca);
	if (!TestTrue(TEXT("S029_P03 is en-bonc, brain 9, strength 8"), B && B->Script == FName(TEXT("en-bonc")) && B->GetProp(TEXT("brain")) == 9 && B->GetProp(TEXT("strength")) == 8))
	{
		return false;
	}
	// The other Boncas on the screen stay out of it.
	for (const int32 P : { 4, 5, 6, 7 })
	{
		if (FDinkSprite* O = E.D->FindSprite(E.D->HandleForPlacement(29, P)))
		{
			O->bFrozen = true;
		}
	}
	FDinkSprite& Dink = E.D->GetDink();
	Dink.Screen = 29;
	Dink.X = B->X - 80;
	Dink.Y = B->Y;
	TestTrue(TEXT("a clear band between them"), BandFree(E, 29, FMath::RoundToInt32(Dink.X), FMath::RoundToInt32(B->X), FMath::RoundToInt32(B->Y), 8));
	E.Facts->SetFact(TEXT("lifemax"), 10);
	E.Facts->SetFact(TEXT("life"), 10);
	E.Facts->SetFact(TEXT("defense"), 0);
	B->Props.Add(TEXT("target"), 1); // a Bonca hit by Dink (or en-bonc's neighbours') locks on like this
	const double T0 = E.Story->GetNowMs();
	double DeadAt = -1.0;
	for (int32 F = 0; F < 60 * 30 && DeadAt < 0.0; ++F)
	{
		Frame(E);
		if (E.Facts->GetFact(TEXT("life")) < 1)
		{
			DeadAt = (E.Story->GetNowMs() - T0) / 1000.0;
		}
	}
	// Walk: 30 px at 30 px/s, at most twice that (it re-aims only every 200 ms and wanders in between);
	// two hits always kill (5 + 5 >= 10), the second at most attack wait 4 s + the hit frame after the first.
	const double Walk = (80.0 - 50.0) / 30.0;
	const double Bound = 2.0 * Walk + 0.35 + 4.0 + 0.35 + 1.0;
	for (const FString& Ev : E.G->Events)
	{
		if (Ev.StartsWith(TEXT("hit 1 by")) || Ev.StartsWith(TEXT("touch damage")) || Ev.StartsWith(TEXT("dink -")))
		{
			AddInfo(Ev);
		}
	}
	AddInfo(FString::Printf(TEXT("idle Dink died after %.2f s (bound %.1f s)"), DeadAt, Bound));
	TestTrue(TEXT("the Bonca kills him"), DeadAt > 0.0);
	TestTrue(TEXT("not before the walk and the first hit frame"), DeadAt >= 0.28);
	TestTrue(TEXT("within the time the original numbers imply"), DeadAt <= Bound);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIBoncaPlayerWinsTest, "Dink.AI.Bonca.AttackingDinkWins", DINK_TEST_FLAGS)
bool FDinkAIBoncaPlayerWinsTest::RunTest(const FString& Parameters)
{
	// Martridge's trial: the cave Bonca (s1-cavem on SCR_100, &wizard_see 2: strength 4, touch 2, 20 hp,
	// distance 50) against Dink with what a player has then: fists, strength 3 + 1 from Martridge's red potion,
	// 10 life. Dink stands toe to toe, 40 px from it on its row (inside its attack distance 50, outside its
	// touch box), facing it, and punches every 450 ms. The Bonca chases its duck first (sp_target(sp(36))),
	// then Dink once he hits it (run_through_tag_list sets its target), and fights back.
	FEnv E = Make(*this, 1997);
	if (!E.IsValid())
	{
		return false;
	}
	E.G->StartNewGame();
	Settle(E);
	E.Facts->SetFact(TEXT("wizard_see"), 2);
	E.Facts->SetFact(TEXT("strength"), 4);
	E.Facts->SetFact(TEXT("lifemax"), 10);
	E.Facts->SetFact(TEXT("life"), 10);
	Enter(E, 100);
	const int32 Bonca = FindByScript(E, TEXT("s1-cavem"));
	if (!TestTrue(TEXT("the cave Bonca is there at &wizard_see 2"), Bonca != 0))
	{
		return false;
	}
	TestFalse(TEXT("SCR_100 is not a locked fight (s1-cavem never calls screenlock)"), E.G->IsScreenLocked());
	FDinkSprite& Dink = E.D->GetDink();
	Dink.Screen = 100;
	double NextPunch = 0.0;
	bool bWon = false;
	int32 Punches = 0;
	for (int32 F = 0; F < 60 * 90 && !bWon; ++F)
	{
		Frame(E);
		const FDinkSprite* B = E.D->FindSprite(Bonca);
		if (!B || !B->bActive || E.Facts->GetFact(TEXT("wizard_see")) == 3)
		{
			bWon = true;
			break;
		}
		if (E.Facts->GetFact(TEXT("life")) < 1)
		{
			break;
		}
		// Stand 40 px west (or east if that is hard) of it on its row, facing it.
		const int32 Bx = FMath::RoundToInt32(B->X), By = FMath::RoundToInt32(B->Y);
		const bool bWest = E.G->GetHard(100, Bx - 40, By) == 0;
		Dink.X = bWest ? Bx - 40 : Bx + 40;
		Dink.Y = By;
		Dink.Dir = bWest ? 6 : 4;
		const double Now = E.Story->GetNowMs();
		if (Now >= NextPunch)
		{
			E.G->PlayerAttack();
			++Punches;
			NextPunch = Now + 450.0;
		}
	}
	AddInfo(FString::Printf(TEXT("%s after %d punches; Dink's life %d/10, &wizard_see %d"), bWon ? TEXT("won") : TEXT("lost"), Punches,
		E.Facts->GetFact(TEXT("life")), E.Facts->GetFact(TEXT("wizard_see"))));
	TestTrue(TEXT("Dink kills the Bonca"), bWon);
	TestTrue(TEXT("and lives"), E.Facts->GetFact(TEXT("life")) > 0);
	TestEqual(TEXT("its die: &wizard_see 3"), E.Facts->GetFact(TEXT("wizard_see")), 3);
	TestTrue(TEXT("it fought back: its attack procedure ran (sound 31)"), E.D->Audio.Cues.ContainsByPredicate([](const FString& C) { return C.StartsWith(TEXT("sound:31")); }));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIMissileHardnessTest, "Dink.AI.Missile.WallsAndLowHardness", DINK_TEST_FLAGS)
bool FDinkAIMissileHardnessTest::RunTest(const FString& Parameters)
{
	// missile_brain (D:14240) + check_if_move_is_legal (D:13416): a missile flies its mx per think; a wall
	// (hardness 1) stops it (no script: gone at once; with one: `damage` with &missile_target 0); low
	// hardness 2 (water, fences) lets a flying missile (sp_flying 1, as every player missile sets) pass,
	// while a non-flying one is held at its edge. Found on real screens' hardness.
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	E.D->GetDink().X = 2000;
	// Find a row with: 40 free px, then a solid (1) wall; and a row with 40 free, a low (2) run, then 40 free.
	auto Find = [&E](int32 Code, int32& OutScreen, int32& OutX, int32& OutY) -> bool
	{
		// SCR_013 and SCR_014 have such rows (found once with a scan of every screen); then a few more.
		TArray<int32> Candidates = { 13, 14 };
		for (int32 Screen = 1; Screen <= 40; ++Screen)
		{
			Candidates.AddUnique(Screen);
		}
		for (const int32 Screen : Candidates)
		{
			if (!E.G->GetData().GetHardness(Screen, 0))
			{
				continue;
			}
			for (int32 Y = 60; Y < 340; Y += 7)
			{
				for (int32 X = 80; X < 560; ++X)
				{
					if (E.G->GetHard(Screen, X, Y) != Code)
					{
						continue;
					}
					bool bOk = true;
					for (int32 K = 1; K <= 40 && bOk; ++K)
					{
						bOk = E.G->GetHard(Screen, X - K, Y) == 0;
					}
					if (bOk && Code == 2)
					{
						int32 End = X;
						while (End < X + 30 && E.G->GetHard(Screen, End, Y) == 2) { ++End; }
						for (int32 K = 0; K < 40 && bOk; ++K)
						{
							bOk = E.G->GetHard(Screen, End + K, Y) == 0;
						}
						bOk &= End < X + 30;
					}
					if (bOk)
					{
						OutScreen = Screen; OutX = X; OutY = Y;
						return true;
					}
					break; // next row
				}
			}
		}
		return false;
	};
	auto Missile = [&E](int32 Screen, int32 X, int32 Y, bool bFlying)
	{
		const int32 H = E.D->CreateVirtualSprite(Screen, X, Y);
		FDinkSprite& M = *E.D->FindSprite(H);
		UDinkDirector::InitCreatedSprite(M);
		M.Props.Add(TEXT("brain"), 11);
		M.Props.Add(TEXT("timing"), 0);
		M.Props.Add(TEXT("speed"), 6);
		M.Props.Add(TEXT("mx"), 6);
		M.Props.Add(TEXT("my"), 0);
		M.Props.Add(TEXT("flying"), bFlying ? 1 : 0);
		M.Props.Add(TEXT("brain_parm"), 1);
		return H;
	};
	int32 Ws = 0, Wx = 0, Wy = 0;
	if (TestTrue(TEXT("a screen row with a solid wall"), Find(1, Ws, Wx, Wy)))
	{
		Enter(E, Ws);
		E.D->GetDink().X = 2000;
		const int32 M = Missile(Ws, Wx - 36, Wy, true);
		double MaxX = 0;
		for (int32 F = 0; F < 30; ++F)
		{
			Frame(E);
			MaxX = FMath::Max(MaxX, E.D->FindSprite(M)->X);
		}
		AddInfo(FString::Printf(TEXT("wall: SCR_%03d x %d y %d; missile reached x %.0f"), Ws, Wx, Wy, MaxX));
		TestFalse(TEXT("a wall stops a flying missile (gone, no script)"), E.D->FindSprite(M)->bActive);
		TestTrue(TEXT("it never passed the wall"), MaxX < Wx);
	}
	int32 Ls = 0, Lx = 0, Ly = 0;
	if (TestTrue(TEXT("a screen row with low hardness and free ground behind"), Find(2, Ls, Lx, Ly)))
	{
		Enter(E, Ls);
		E.D->GetDink().X = 2000;
		const int32 Fly = Missile(Ls, Lx - 36, Ly, true);
		const int32 Walk = Missile(Ls, Lx - 36, Ly, false);
		for (int32 F = 0; F < 20; ++F)
		{
			Frame(E);
		}
		const FDinkSprite* A = E.D->FindSprite(Fly);
		const FDinkSprite* B = E.D->FindSprite(Walk);
		AddInfo(FString::Printf(TEXT("low: SCR_%03d x %d y %d; flying at %.0f, non-flying at %.0f"), Ls, Lx, Ly, A->X, B->X));
		TestTrue(TEXT("a flying missile crosses low hardness"), A->X > Lx + 20);
		TestTrue(TEXT("a non-flying one is held at its edge (still there, the engine's behaviour)"), B->bActive && B->X < Lx);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIScreenlockTest, "Dink.AI.Screenlock.FightsLockAndUnlock", DINK_TEST_FLAGS)
bool FDinkAIScreenlockTest::RunTest(const FString& Parameters)
{
	// en-bonc1 on SCR_302 (two Boncas, main: screenlock(1)) and en-pill1 on SCR_270: Dink cannot leave while
	// a brain-9 monster lives; the last one's `die` calls screenlock(0) and plays sound 43 (the "secret found"
	// cue). A screen load clears the lock (load_map, D:1016). Sprite warps are not refused in the original
	// (special_block / process_warp_man never read screenlock), so the remaster does not refuse them either.
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	ToughDink(E);
	E.Facts->SetFact(TEXT("strength"), 60);
	E.G->StartNewGame();
	Settle(E);
	struct FCase { int32 Screen; const TCHAR* Script; };
	for (const FCase& C : { FCase{ 302, TEXT("en-bonc1") }, FCase{ 270, TEXT("en-pill1") } })
	{
		Enter(E, C.Screen);
		TestTrue(FString::Printf(TEXT("SCR_%d: locked on entry"), C.Screen), E.G->IsScreenLocked());
		TestFalse(FString::Printf(TEXT("SCR_%d: Dink cannot leave"), C.Screen), E.G->CanDinkLeaveScreen());
		int32 Killed = 0;
		for (int32 Round = 0; Round < 20; ++Round)
		{
			const int32 Foe = FindByScript(E, C.Script);
			if (!Foe)
			{
				break;
			}
			const bool bLast = [&E, Foe]()
			{
				int32 N = 0;
				for (const TPair<int32, FDinkSprite>& P : E.D->GetSprites())
				{
					N += P.Value.bActive && P.Value.GetProp(TEXT("brain")) == 9 && P.Key != 1 ? 1 : 0;
				}
				return N == 1;
			}();
			const FDinkSprite* T = E.D->FindSprite(Foe);
			FDinkSprite& Dink = E.D->GetDink();
			int32 L = 0, Tp = 0, R = 0, B = 0;
			E.G->GetHardbox(*T, L, Tp, R, B);
			Dink.X = L - 10;
			Dink.Y = T->Y;
			Dink.Dir = 6;
			E.G->PlayerAttack();
			Settle(E);
			const FDinkSprite* After = E.D->FindSprite(Foe);
			if (!After || !After->bActive)
			{
				++Killed;
				if (!bLast)
				{
					TestTrue(FString::Printf(TEXT("SCR_%d: still locked while another monster lives"), C.Screen), E.G->IsScreenLocked());
				}
			}
		}
		TestTrue(FString::Printf(TEXT("SCR_%d: monsters killed"), C.Screen), Killed >= 1);
		TestFalse(FString::Printf(TEXT("SCR_%d: unlocked after the last one"), C.Screen), E.G->IsScreenLocked());
		TestTrue(FString::Printf(TEXT("SCR_%d: sound 43 played"), C.Screen), E.D->Audio.Cues.ContainsByPredicate([](const FString& Cue) { return Cue.StartsWith(TEXT("sound:43")); }));
	}
	// A screen load clears a lock (load_map, D:1016): lock by hand, then walk into Dink's house.
	E.G->SetScreenLock(true);
	TestTrue(TEXT("locked by hand"), E.G->IsScreenLocked());
	Enter(E, 1);
	TestFalse(TEXT("a screen load clears screenlock"), E.G->IsScreenLocked());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIScreenlockBarrierTest, "Dink.AI.Screenlock.BarrierBlocksExits", DINK_TEST_FLAGS)
bool FDinkAIScreenlockBarrierTest::RunTest(const FString& Parameters)
{
	// The greybox side: a screen volume raises a blocking slab on each open edge while locked (pawns and
	// projectiles stop at it) and drops it on unlock. In a throwaway game world.
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("DinkScreenlockTest"));
	FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
	Context.SetCurrentWorld(World);
	ADinkScreenVolume* Volume = World->SpawnActor<ADinkScreenVolume>();
	if (!TestNotNull(TEXT("screen volume spawns"), Volume))
	{
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
		return false;
	}
	Volume->ScreenNumber = 302;
	Volume->Corners.NW = FVector2D(0, 0);
	Volume->Corners.NE = FVector2D(60, 0);
	Volume->Corners.SW = FVector2D(0, 40);
	Volume->Corners.SE = FVector2D(60, 40);
	UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
	if (Greybox)
	{
		Greybox->RegisterScreen(Volume);
	}
	// A walker's trace across the north edge (map y 0) at map x 300, 1 m above the ground.
	const FVector Inside = DinkLayout::MapPixelToUnreal(Volume->Corners, 300, 20) + FVector(0, 0, 100);
	const FVector Outside = DinkLayout::MapPixelToUnreal(Volume->Corners, 300, -20) + FVector(0, 0, 100);
	auto Blocked = [World, &Inside, &Outside](ECollisionChannel Channel)
	{
		FHitResult Hit;
		return World->LineTraceSingleByChannel(Hit, Inside, Outside, Channel);
	};
	TestFalse(TEXT("open before the lock"), Blocked(ECC_Pawn));
	const bool bLocked = Greybox ? Greybox->SetScreenLocked(302, true) : (Volume->SetLockBarriers(true), true);
	TestTrue(TEXT("lock found the screen"), bLocked);
	TestEqual(TEXT("one slab per open edge"), Volume->LockBarriers.Num(), 4);
	TestTrue(TEXT("locked: a walker is stopped at the edge"), Blocked(ECC_Pawn));
	TestTrue(TEXT("locked: a projectile too"), Blocked(DinkCollision::Projectile));
	if (Greybox)
	{
		TestEqual(TEXT("the greybox knows the locked screen"), Greybox->GetLockedScreen(), 302);
		Greybox->SetScreenLocked(0, false);
	}
	else
	{
		Volume->SetLockBarriers(false);
	}
	TestFalse(TEXT("unlocked: open again"), Blocked(ECC_Pawn));
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIAdaptationTest, "Dink.AI.Adaptation.WindUpAndAttackerCap", DINK_TEST_FLAGS)
bool FDinkAIAdaptationTest::RunTest(const FString& Parameters)
{
	// Three Boncas around Dink. Classic (layer off): they attack at once and together. Layer on (the data file's
	// numbers): every attack is preceded by a wind-up of WindUpMs during which the attacker stands still, and
	// never more than MaxAttackers wind up or attack him at once.
	FDinkAdaptationSettings File;
	TestTrue(TEXT("Content/Dink/Data/AI/adaptation.ini loads"), File.Load(FDinkAdaptationSettings::DefaultPath()));
	TestTrue(TEXT("the data file turns the layer on for play"), File.bEnabled);
	for (const bool bLayer : { false, true })
	{
		FEnv E = Make(*this, 3);
		if (!E.IsValid())
		{
			return false;
		}
		if (bLayer)
		{
			E.G->Adaptation = File;
		}
		Enter(E, 100);
		ToughDink(E);
		FDinkSprite& Dink = E.D->GetDink();
		Dink.Screen = 100;
		Dink.X = 300;
		Dink.Y = 200;
		TArray<int32> Boncas = { MakeBonca(E, 100, 340, 200, 1, 4), MakeBonca(E, 100, 260, 200, 1, 4), MakeBonca(E, 100, 300, 240, 1, 4) };
		int32 MaxAt = 0, WindUps = 0, Attacks = 0, FirstAttackFrame = -1;
		bool bMovedWhileWinding = false;
		TMap<int32, FVector2D> WindPos;
		for (int32 F = 0; F < 60 * 20; ++F)
		{
			Frame(E);
			MaxAt = FMath::Max(MaxAt, E.G->CountAttackers(1, 0));
			for (const int32 H : Boncas)
			{
				const FDinkSprite* B = E.D->FindSprite(H);
				if (B->bWindingUp)
				{
					if (const FVector2D* P = WindPos.Find(H))
					{
						bMovedWhileWinding |= P->X != B->X || P->Y != B->Y;
					}
					WindPos.Add(H, FVector2D(B->X, B->Y));
				}
				else
				{
					WindPos.Remove(H);
				}
			}
		}
		for (const FString& Ev : E.G->Events)
		{
			WindUps += Ev.StartsWith(TEXT("wind-up")) ? 1 : 0;
		}
		for (const FString& Ev : E.G->Events)
		{
			Attacks += Ev.StartsWith(TEXT("hit 1 by")) ? 1 : 0;
		}
		AddInfo(FString::Printf(TEXT("layer %s: at most %d attacking at once, %d wind-ups, %d hits on Dink in 20 s"), bLayer ? TEXT("on") : TEXT("off"), MaxAt, WindUps, Attacks));
		if (bLayer)
		{
			TestTrue(TEXT("on: never more than MaxAttackers at once"), MaxAt <= File.MaxAttackers);
			TestTrue(TEXT("on: attacks are telegraphed"), WindUps >= Attacks && WindUps > 0);
			TestFalse(TEXT("on: a winding-up attacker stands still"), bMovedWhileWinding);
		}
		else
		{
			TestTrue(TEXT("off: all three attack at once (the original has no cap)"), MaxAt >= 3);
			TestEqual(TEXT("off: no wind-ups"), WindUps, 0);
		}
		TestTrue(TEXT("they hit Dink"), Attacks > 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIOverrideTest, "Dink.AI.Override.FrozenAndScriptedMove", DINK_TEST_FLAGS)
bool FDinkAIOverrideTest::RunTest(const FString& Parameters)
{
	// Every brain looks at move_active first and at freeze next (D:12920...): a frozen monster does not move
	// (a scripted move still would), and a move/move_stop walks it in a straight line however its brain wants
	// to go; the brain takes over again when the move ends.
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	Enter(E, 100);
	ToughDink(E);
	FDinkSprite& Dink = E.D->GetDink();
	Dink.Screen = 100;
	Dink.X = 250;
	Dink.Y = 200;
	const int32 Bonca = MakeBonca(E, 100, 400, 200, 1, 4);
	E.D->FindSprite(Bonca)->bFrozen = true;
	for (int32 F = 0; F < 120; ++F)
	{
		Frame(E);
	}
	TestTrue(TEXT("frozen: it stays put"), E.D->FindSprite(Bonca)->X == 400 && E.D->FindSprite(Bonca)->Y == 200);
	TestEqual(TEXT("frozen: no attack"), E.Facts->GetFact(TEXT("life")), 1000);
	// A scripted move away from Dink while it targets him: the move wins.
	FDinkSprite* B = E.D->FindSprite(Bonca);
	B->bFrozen = false;
	B->Props.Add(TEXT("speed"), 1);
	E.D->StartMove(*B, 6, 460);
	bool bStraight = true;
	for (int32 F = 0; F < 60 * 3 && E.D->IsMoving(Bonca); ++F)
	{
		Frame(E);
		bStraight &= E.D->FindSprite(Bonca)->Y == 200;
	}
	TestFalse(TEXT("the move ended"), E.D->IsMoving(Bonca));
	TestTrue(TEXT("it walked straight east, away from its target"), bStraight && E.D->FindSprite(Bonca)->X >= 459);
	// The brain again: it turns back to Dink.
	const double After = E.D->FindSprite(Bonca)->X;
	for (int32 F = 0; F < 60 * 4; ++F)
	{
		Frame(E);
	}
	TestTrue(TEXT("after the move the brain chases Dink again"), E.D->FindSprite(Bonca)->X < After - 20);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAIDeterminismTest, "Dink.AI.Determinism.SameSeedSameOutcome", DINK_TEST_FLAGS)
bool FDinkAIDeterminismTest::RunTest(const FString& Parameters)
{
	// The same seed gives the same fight frame for frame; another seed gives another.
	auto Run = [this](int32 Seed)
	{
		FEnv E = Make(*this, Seed);
		FString Trace;
		if (!E.IsValid())
		{
			return Trace;
		}
		Enter(E, 29);
		E.Facts->SetFact(TEXT("lifemax"), 40);
		E.Facts->SetFact(TEXT("life"), 40);
		FDinkSprite& Dink = E.D->GetDink();
		Dink.Screen = 29;
		const FDinkSprite* B = E.D->FindSprite(E.D->HandleForPlacement(29, 3));
		Dink.X = B->X - 90;
		Dink.Y = B->Y;
		E.D->FindSprite(E.D->HandleForPlacement(29, 3))->Props.Add(TEXT("target"), 1);
		for (int32 F = 0; F < 60 * 15; ++F)
		{
			Frame(E);
			if (F % 30 == 0)
			{
				for (const int32 P : { 3, 4, 5, 6, 7 })
				{
					if (const FDinkSprite* S = E.D->FindSprite(E.D->HandleForPlacement(29, P)))
					{
						Trace += FString::Printf(TEXT("%d:%.0f,%.0f;"), P, S->X, S->Y);
					}
				}
				Trace += FString::Printf(TEXT("life %d|"), E.Facts->GetFact(TEXT("life")));
			}
		}
		return Trace;
	};
	const FString A = Run(1997), B = Run(1997), C = Run(2024);
	TestTrue(TEXT("a trace was recorded"), A.Len() > 100);
	TestEqual(TEXT("same seed, same positions and life every half second"), A, B);
	TestNotEqual(TEXT("another seed, another fight"), A, C);
	return true;
}
