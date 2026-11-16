// Dink.Parity.DinkC.*: DinkC commands whose remaster semantics differed from the 1997 engine (source/dink/dink.cpp), found by the
// script-runtime audit of 15 Nov 2026 (doc/remaster/DINKC_PARITY.md). Each test runs the real converted scripts headless (standalone
// story, no world) and asserts the engine's behaviour with its dink.cpp lines.

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkNarrativeTypes.h"
#include "DinkStorySubsystem.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Greybox/DinkGreyboxCharacter.h"

namespace DinkCParityTest
{
	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* G = nullptr;
		bool IsValid() const { return Facts && World && Story && Story->IsReady() && D && G; }
	};

	FEnv Make(FAutomationTestBase& Test, bool bInstant)
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
		E.Story->bInstantMode = bInstant;
		E.D = E.Story->GetDirector();
		E.G = E.Story->GetGameplay();
		if (E.G)
		{
			E.G->Adaptation.bEnabled = false; // parity: Classic rules
			E.G->SetRandomSeed(1997);
		}
		return E;
	}

	FDinkCommandResult Run(FEnv& E, FDinkScriptInstance& I, const FString& Text)
	{
		const FDinkStoryLine L = FDinkStoryLine::Parse(FString(TEXT(">> ")) + Text, { TEXT("cmd"), TEXT("src:1") });
		return E.D->Execute(I, L);
	}

	int32 Starts(const FEnv& E, const FString& Script, const FString& Proc, int32 From = 0)
	{
		const FString Path = DinkNarrative::EntryPath(Script, Proc);
		int32 N = 0;
		for (int32 i = From; i < E.Story->Events.Num(); ++i)
		{
			N += (E.Story->Events[i].Kind == FName(TEXT("start")) && E.Story->Events[i].Text == Path) ? 1 : 0;
		}
		return N;
	}

	/** Advance game time in 60 Hz frames. */
	void Frames(FEnv& E, double Seconds)
	{
		for (int32 F = 0, N = FMath::CeilToInt(Seconds * 60.0); F < N; ++F)
		{
			E.Story->Advance(1.0 / 60.0);
		}
	}
}

using namespace DinkCParityTest;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCParityCallbackKilledTest, "Dink.Parity.DinkC.CallbackEndsOnWaitSayAndHit", DINK_TEST_FLAGS)
bool FDinkCParityCallbackKilledTest::RunTest(const FString& Parameters)
{
	// kill_returning_stuff (D:5049-5070) ends a script's set_callback_random timers. wait and the say_stop family call it (D:8043, 7916, 7948,
	// 7973, 7997), and so does the engine before it runs `hit`, `talk` or `damage` in the script (D:15541, 15582, 14217, 14277, hurt D:9968).
	FEnv E = Make(*this, false);
	if (!E.IsValid()) return false;

	// 1. s1-caves.c (SCR_131): main calls noise() once and then set_callback_random("noise", 5000, 10000); noise() does wait(4000), which ends
	// the timer. The original roars at most twice; the remake used to call noise every 5-15 s for as long as Dink stayed in the cave.
	E.Facts->SetFact(TEXT("wizard_see"), 0);
	const int32 From = E.Story->Events.Num();
	const int32 Cave = E.Story->StartProcedure(TEXT("s1-caves"), TEXT("main"), 0, {}, 131, /*bNewInstance*/ true);
	if (!TestTrue(TEXT("s1-caves main starts"), Cave != 0)) return false;
	Frames(E, 90.0);
	TestTrue(TEXT("s1-caves: the callback ran noise at most once in 90 s (its wait(4000) ended the timer)"), Starts(E, TEXT("s1-caves"), TEXT("noise"), From) <= 1);
	if (const FDinkScriptInstance* I = E.Story->FindInstance(Cave))
	{
		TestTrue(TEXT("s1-caves: no set_callback_random timer is left"), I->CallbackProc.IsNone());
	}

	// 2. en-bong.c: main ends with set_callback_random("target", 2000, 0); Dink's hit runs `hit` after kill_returning_stuff, so the Bonca
	// keeps the target `hit` gave it (sp_target(&current_sprite, &enemy_sprite)) instead of re-picking one every 2 s.
	const int32 Bonca = E.D->CreateVirtualSprite(12, 300, 200);
	FDinkSprite* B = E.D->FindSprite(Bonca);
	UDinkDirector::InitDumbSprite(*B);
	B->Props.Add(TEXT("brain"), 9);
	const int32 Caller = E.D->CreateVirtualSprite(12, 100, 100);
	const int32 CallerId = E.Story->StartProcedure(TEXT("s1-brg2"), TEXT("hit"), Caller, {}, 12, true);
	FDinkScriptInstance* CallerI = E.Story->FindInstance(CallerId);
	if (!TestNotNull(TEXT("a caller instance"), CallerI)) return false;
	Run(E, *CallerI, FString::Printf(TEXT("sp_script %d \"en-bong\""), Bonca));
	Frames(E, 1.0); // main: wait(500), then the callback is set
	const FDinkScriptInstance* BI = E.Story->FindInstanceForSprite(Bonca);
	if (!TestNotNull(TEXT("en-bong runs on the Bonca"), BI)) return false;
	TestTrue(TEXT("en-bong: the target callback is set"), BI->CallbackProc == FName(TEXT("target")));
	E.Facts->SetFact(TEXT("enemy_sprite"), 1);
	E.Story->StartProcedure(TEXT("en-bong"), TEXT("hit"), Bonca);
	BI = E.Story->FindInstanceForSprite(Bonca);
	TestTrue(TEXT("en-bong: hit ended the callback (kill_returning_stuff before HIT, D:15582)"), BI && BI->CallbackProc.IsNone());

	// 3. A wait ends the caller's own timer.
	CallerI->CallbackProc = TEXT("main");
	Run(E, *CallerI, TEXT("wait 10"));
	TestTrue(TEXT("wait ends the instance's set_callback_random timer (D:8043)"), CallerI->CallbackProc.IsNone());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCParityLoadScreenUnfreezesTest, "Dink.Parity.DinkC.LoadScreenUnfreezesDink", DINK_TEST_FLAGS)
bool FDinkCParityLoadScreenUnfreezesTest::RunTest(const FString& Parameters)
{
	// load_screen is load_map (D:7874-7884), which ends Dink's freeze and move (D:1013-1015). The pits (s1-hole3.c, s6-hole.c, s6-hole2.c,
	// s1-hole.c) freeze Dink, attach to 1000, load the room below and end with kill_this_task and no unfreeze(1): the original leaves Dink
	// free there; the remake kept him frozen because the script still ran when the screen change was noticed (a softlock).
	FEnv E = Make(*this, true);
	if (!E.IsValid()) return false;
	const int32 Pit = E.D->CreateVirtualSprite(209, 283, 297);
	const int32 Id = E.Story->StartProcedure(TEXT("s1-hole3"), TEXT("touch"), Pit, {}, 209, true);
	if (!TestTrue(TEXT("s1-hole3 touch starts"), Id != 0)) return false;
	E.Story->RunUntilIdle();
	TestEqual(TEXT("s1-hole3: Dink is in the room below (&player_map 198)"), E.Facts->GetFact(TEXT("player_map")), 198);
	TestFalse(TEXT("s1-hole3: Dink is not frozen when the script has ended"), E.D->GetDink().bFrozen);

	// A script that freezes Dink again after load_screen keeps him frozen (s2-culg.c:43-45: load_screen(66); freeze(1); draw_screen()).
	const int32 Caller = E.D->CreateVirtualSprite(12, 100, 100);
	FDinkScriptInstance* I = E.Story->FindInstance(E.Story->StartProcedure(TEXT("s1-brg2"), TEXT("hit"), Caller, {}, 12, true));
	if (!TestNotNull(TEXT("a caller instance"), I)) return false;
	E.Facts->SetFact(TEXT("player_map"), 66);
	Run(E, *I, TEXT("freeze 1"));
	Run(E, *I, TEXT("load_screen 66"));
	TestFalse(TEXT("load_screen unfreezes Dink"), E.D->GetDink().bFrozen);
	Run(E, *I, TEXT("freeze 1"));
	TestTrue(TEXT("freeze(1) after load_screen holds"), E.D->GetDink().bFrozen);
	Run(E, *I, TEXT("unfreeze 1"));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCParityStopEntireGameTest, "Dink.Parity.DinkC.StopEntireGamePausesSprites", DINK_TEST_FLAGS)
bool FDinkCParityStopEntireGameTest::RunTest(const FString& Parameters)
{
	// stop_entire_game(1) (D:10099-10108): while its menu is up no sprite thinks (ThinkSprite(h, true), D:17423: no brain, no animation, no
	// kill timer, no touch damage) until the first frame without a menu (D:17431-17440). lraise.c's level-up menu uses it.
	FEnv E = Make(*this, false);
	if (!E.IsValid()) return false;
	E.Facts->SetFact(TEXT("level"), 1);
	const int32 Victim = E.D->CreateVirtualSprite(12, 300, 200);
	FDinkSprite* V = E.D->FindSprite(Victim);
	UDinkDirector::InitDumbSprite(*V);
	const int32 Id = E.Story->StartProcedure(TEXT("lraise"), TEXT("raise"), UDinkDirector::HandleNoSprite, {}, 12, true);
	if (!TestTrue(TEXT("lraise raise starts"), Id != 0)) return false;
	for (int32 F = 0; F < 600 && !E.Story->GetActiveMenu(); ++F) E.Story->Advance(1.0 / 60.0);
	if (!TestNotNull(TEXT("the level-up menu is up"), E.Story->GetActiveMenu())) return false;
	TestTrue(TEXT("stop_entire_game(1) is in force"), E.D->bStopEntireGame);
	V = E.D->FindSprite(Victim);
	V->KillAtMs = E.Story->GetNowMs() + 100.0; // an sp_kill timer due in 100 ms
	Frames(E, 1.0);
	V = E.D->FindSprite(Victim);
	TestTrue(TEXT("while the menu is up, the sprite's kill timer does not run"), V && V->bActive);
	E.Story->Choose(0); // "Increase Attack"
	Frames(E, 0.5);
	TestFalse(TEXT("the first frame without a menu clears stop_entire_game"), E.D->bStopEntireGame);
	V = E.D->FindSprite(Victim);
	TestTrue(TEXT("and the game runs on: the kill timer removed the sprite"), !V || !V->bActive);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCParityDoorHardForBrainsTest, "Dink.Parity.DinkC.WarpBoxIsHardForBrains", DINK_TEST_FLAGS)
bool FDinkCParityDoorHardForBrainsTest::RunTest(const FString& Parameters)
{
	// check_if_move_is_legal reads get_hard (D:13503, 527-546): a map.dat warp's stamped hardbox (prop 1) is hard for every brain's move;
	// only Dink's walk reads it through get_hard_play (D:548-580), which makes it 0 and a warp. SCR_003's door S003_P14 fills map x 0-60,
	// y 149-200 (code 114). A missile (brain 11) flying west at y 175 must stop at the box, not fly through the door.
	FEnv E = Make(*this, true);
	if (!E.IsValid()) return false;
	if (!TestTrue(TEXT("gameplay data loaded"), E.G->HasData())) return false;
	TestEqual(TEXT("S003_P14's box is in the hit map (engine x 50, y 175)"), E.G->GetHard(3, 50, 175), 114);
	TestEqual(TEXT("S003_P14 is a warp (prop 1)"), E.G->GetPlacementProp(FDinkOriginId(3, 14)), 1);
	const int32 M = E.D->CreateVirtualSprite(3, 130, 175);
	FDinkSprite* S = E.D->FindSprite(M);
	UDinkDirector::InitCreatedSprite(*S); // a missile is add_sprite's (D:14231)
	S->Props.Add(TEXT("brain"), 11);
	S->Props.Add(TEXT("timing"), 0);
	S->Props.Add(TEXT("speed"), 4);
	S->Props.Add(TEXT("mx"), -4);
	S->Props.Add(TEXT("my"), 0);
	S->Props.Add(TEXT("pseq"), 504);
	S->Props.Add(TEXT("pframe"), 1);
	double MinX = S->X;
	for (int32 F = 0; F < 60; ++F)
	{
		E.G->ThinkSprite(M, 1000.0 + F * 1000.0 / 60.0);
		S = E.D->FindSprite(M);
		if (!S || !S->bActive) break;
		MinX = FMath::Min(MinX, S->X);
	}
	TestTrue(FString::Printf(TEXT("the missile flew west over the open floor (min engine x %.0f)"), MinX), MinX <= 100.0);
	TestTrue(FString::Printf(TEXT("the missile never entered the door's box (min engine x %.0f, the box ends at 80)"), MinX), MinX >= 81.0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCParitySetDinkSpeedTest, "Dink.Parity.DinkC.SetDinkSpeedScalesWalk", DINK_TEST_FLAGS)
bool FDinkCParitySetDinkSpeedTest::RunTest(const FString& Parameters)
{
	// set_dink_speed (D:7563-7575) sets dinkspeed, which every frame becomes Dink's walk speed (D:17311-17321): 12, 6, 3 px for 1, 2, 3, else
	// 1; 0 is ignored. item-bt.c (Herb's boots, s1-boot.c) arms with set_dink_speed(2) and disarms with 3: twice as fast while worn. The remake
	// only recorded it, so the boots did nothing.
	TestEqual(TEXT("dinkspeed 3 (main.c) is the normal speed"), UDinkDirector::DinkSpeedScale(3), 1.f);
	TestEqual(TEXT("dinkspeed 2 (the boots) is twice as fast"), UDinkDirector::DinkSpeedScale(2), 2.f);
	TestEqual(TEXT("dinkspeed 1 is four times as fast"), UDinkDirector::DinkSpeedScale(1), 4.f);
	TestEqual(TEXT("dinkspeed 4 is 1 px per frame"), UDinkDirector::DinkSpeedScale(4), 1.f / 3.f);

	FEnv E = Make(*this, true);
	if (!E.IsValid()) return false;
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	if (!TestNotNull(TEXT("world"), World)) return false;
	FActorSpawnParameters Spawn;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ADinkGreyboxCharacter* Hero = World->SpawnActor<ADinkGreyboxCharacter>(FVector(0, 0, 96), FRotator::ZeroRotator, Spawn);
	if (!TestNotNull(TEXT("hero"), Hero)) { GI->Shutdown(); return false; }
	E.D->GetDink().Actor = Hero;
	const int32 Caller = E.D->CreateVirtualSprite(12, 100, 100);
	FDinkScriptInstance* I = E.Story->FindInstance(E.Story->StartProcedure(TEXT("s1-brg2"), TEXT("hit"), Caller, {}, 12, true));
	if (TestNotNull(TEXT("a caller instance"), I))
	{
		E.Story->StartProcedure(TEXT("item-bt"), TEXT("arm"), UDinkDirector::HandleNoSprite, {}, 12, true);
		E.Story->RunUntilIdle();
		TestEqual(TEXT("item-bt arm: the boots double Dink's top speed"), Hero->DinkSpeedScale, 2.f);
		TestEqual(TEXT("and his run speed with no person steering is 12 m/s"), Hero->DesiredTopSpeed(), ADinkGreyboxCharacter::RunSpeed * 2.f);
		Run(E, *I, TEXT("set_dink_speed 0"));
		TestEqual(TEXT("set_dink_speed(0) is ignored (D:7568)"), Hero->DinkSpeedScale, 2.f);
		E.Story->StartProcedure(TEXT("item-bt"), TEXT("disarm"), UDinkDirector::HandleNoSprite, {}, 12, true);
		E.Story->RunUntilIdle();
		TestEqual(TEXT("item-bt disarm: back to the normal speed"), Hero->DinkSpeedScale, 1.f);
	}
	E.D->GetDink().Actor = nullptr;
	Hero->Destroy();
	GI->Shutdown();
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCParityScriptAttachTest, "Dink.Parity.DinkC.ScriptAttachMovesCurrentSprite", DINK_TEST_FLAGS)
bool FDinkCParityScriptAttachTest::RunTest(const FString& Parameters)
{
	// script_attach(n) sets the instance's sprite (D:8075-8087), which is what &current_sprite reads; after script_attach(1000) every
	// sp_*(&current_sprite, ..) is sp_*(1000, ..) and change_sprite ignores it (D:5396-5403; s1-ltr.c:9-10 says so: "now &current_sprite
	// won't work"). s1-mh-f.c:33-40: Martridge's scroll attaches to 1000 and then sets brain 12 on &current_sprite, so in the engine the scroll
	// stays on the floor. Bug A47, decided by the coordinator on 15 Nov 2026: the engine's behaviour is live.
	FEnv E = Make(*this, true);
	if (!E.IsValid()) return false;
	E.Facts->SetFact(TEXT("wizard_see"), 3);
	const int32 Scroll = E.D->CreateVirtualSprite(6, 300, 200);
	FDinkSprite* S = E.D->FindSprite(Scroll);
	UDinkDirector::InitDumbSprite(*S);
	S->Props.Add(TEXT("brain"), 0);
	S->Script = TEXT("s1-mh-f");
	const int32 Id = E.Story->StartProcedure(TEXT("s1-mh-f"), TEXT("talk"), Scroll, {}, 6, true);
	if (!TestTrue(TEXT("s1-mh-f talk starts"), Id != 0)) return false;
	E.Story->RunUntilIdle();
	TestEqual(TEXT("the scroll was read (&wizard_see 4)"), E.Facts->GetFact(TEXT("wizard_see")), 4);
	S = E.D->FindSprite(Scroll);
	if (!TestNotNull(TEXT("the scroll sprite"), S)) return false;
	TestTrue(TEXT("the scroll is still on the floor (active)"), S->bActive);
	TestEqual(TEXT("sp_brain(&current_sprite, 12) after script_attach(1000) did not reach it (brain 0)"), S->GetProp(TEXT("brain")), 0);
	TestFalse(TEXT("Dink is free again (unfreeze(1))"), E.D->GetDink().bFrozen);

	// The value itself: a script attached to 1000 reads &current_sprite as 1000 on its next line.
	const int32 Caller = E.D->CreateVirtualSprite(12, 100, 100);
	FDinkScriptInstance* I = E.Story->FindInstance(E.Story->StartProcedure(TEXT("s1-brg2"), TEXT("hit"), Caller, {}, 12, true));
	if (!TestNotNull(TEXT("a caller instance"), I)) return false;
	Run(E, *I, TEXT("script_attach 1000"));
	TestEqual(TEXT("&current_sprite is 1000 after script_attach(1000)"), I->Vars.FindRef(TEXT("current_sprite")), 1000);
	return true;
}
