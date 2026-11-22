// The player controller's move input (SetIgnoreMoveInput is a counter) has two reasons to be held: Dink is frozen (freeze(1)) and the
// hardness loading gate is closed. UDinkDirector::UpdatePlayerMoveHold keeps ONE count for both and recomputes it from them, so a
// reset, a load, an opened gate or a lost pawn link can never strand it (follow-up of alpha bug A19, PR #130). And 1997's load_map
// clears Dink's freeze on every screen load (dink.cpp:1013-1015), also while a script survives the load.

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkStorySubsystem.h"
#include "DinkNarrativeTypes.h"
#include "DinkFactSubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Misc/ScopeExit.h"

namespace DinkMoveHoldTest
{
	UDinkStorySubsystem* MakeStory(FAutomationTestBase& Test)
	{
		UGameInstance* GI = DinkTest::MakeOuterGameInstance();
		UDinkFactSubsystem* Facts = NewObject<UDinkFactSubsystem>(GI);
		FString Error;
		Test.TestTrue(TEXT("facts load"), Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
		UDinkStorySubsystem* Story = NewObject<UDinkStorySubsystem>(GI);
		return Test.TestTrue(TEXT("story loads"), Story->SetupStandalone(Facts, NewObject<UDinkWorldStateSubsystem>(GI), &Error)) ? Story : nullptr;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkMoveHoldTest, "Dink.Input.MoveHoldFollowsItsReasons", DINK_TEST_FLAGS)
bool FDinkMoveHoldTest::RunTest(const FString& Parameters)
{
	UDinkStorySubsystem* Story = DinkMoveHoldTest::MakeStory(*this);
	if (!Story) return false;
	UDinkDirector* D = Story->GetDirector();
	UDinkGameplay* G = Story->GetGameplay();

	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
	ACharacter* Pawn = World->SpawnActor<ACharacter>();
	APlayerController* PC = World->SpawnActor<APlayerController>();
	if (!TestNotNull(TEXT("pawn"), Pawn) || !TestNotNull(TEXT("controller"), PC)) return false;
	PC->Possess(Pawn);
	D->GetDink().Actor = Pawn;
	UCharacterMovementComponent* Movement = Pawn->GetCharacterMovement();
	const float Gravity = Movement->GravityScale;

	// Both reasons at once, then each gone: one count, given back when the last reason goes.
	G->GateOriginalHardnessTransition();
	TestTrue(TEXT("the closed hardness gate holds the controller"), PC->IsMoveInputIgnored());
	D->SetFrozen(1, true);
	TestEqual(TEXT("freeze(1) takes Dink's gravity"), Movement->GravityScale, 0.f);
	D->SetFrozen(1, false);
	TestTrue(TEXT("unfreeze: the gate still holds"), PC->IsMoveInputIgnored());
	TestEqual(TEXT("unfreeze gives the gravity back"), Movement->GravityScale, Gravity);
	G->FinishLegacyHardnessLoad(1); // no marked world here: the gate opens
	TestFalse(TEXT("gate open and Dink free: released"), PC->IsMoveInputIgnored());

	// Exactly one count is taken: another holder of the same counter keeps its own.
	PC->SetIgnoreMoveInput(true); // someone else's hold
	D->SetFrozen(1, true);
	G->GateOriginalHardnessTransition();
	D->SetFrozen(1, false);
	G->FinishLegacyHardnessLoad(1);
	TestTrue(TEXT("our reasons gone, the other holder's count is left"), PC->IsMoveInputIgnored());
	PC->SetIgnoreMoveInput(false);
	TestFalse(TEXT("and when it lets go the controller is free (we gave back exactly what we took)"), PC->IsMoveInputIgnored());

	// A possession's ClientRestart zeroes the counter (ResetIgnoreInputFlags) while a reason still holds: the hold is taken again.
	D->SetFrozen(1, true);
	PC->ResetIgnoreMoveInput();
	TestFalse(TEXT("the counter was zeroed behind the hold's back"), PC->IsMoveInputIgnored());
	D->UpdatePlayerMoveHold();
	TestTrue(TEXT("the next update takes the hold again"), PC->IsMoveInputIgnored());
	D->SetFrozen(1, false);
	TestFalse(TEXT("and unfreeze gives it back"), PC->IsMoveInputIgnored());

	// Dink's pawn changes while he is frozen: the gravity goes back to the old pawn and is taken from the new one.
	D->SetFrozen(1, true);
	TestEqual(TEXT("frozen: the pawn has no gravity"), Movement->GravityScale, 0.f);
	ACharacter* Pawn2 = World->SpawnActor<ACharacter>();
	if (!TestNotNull(TEXT("second pawn"), Pawn2)) return false;
	UCharacterMovementComponent* Movement2 = Pawn2->GetCharacterMovement();
	const float Gravity2 = Movement2->GravityScale;
	PC->UnPossess();
	PC->Possess(Pawn2);
	D->GetDink().Actor = Pawn2;
	D->UpdatePlayerMoveHold();
	TestEqual(TEXT("the old pawn has its gravity back"), Movement->GravityScale, Gravity);
	TestEqual(TEXT("the new pawn has none while Dink is frozen"), Movement2->GravityScale, 0.f);
	TestTrue(TEXT("and the controller is still held"), PC->IsMoveInputIgnored());
	D->SetFrozen(1, false);
	TestEqual(TEXT("unfreeze: the new pawn has its gravity back"), Movement2->GravityScale, Gravity2);
	TestFalse(TEXT("and the controller is free"), PC->IsMoveInputIgnored());
	PC->UnPossess();
	PC->Possess(Pawn);
	D->GetDink().Actor = Pawn;

	// A gate still closed over a sprite reset (a load, a restart) keeps holding, and opening it later releases: no stranded count.
	G->GateOriginalHardnessTransition();
	D->ResetSprites();
	TestTrue(TEXT("a reset leaves the closed gate's hold"), PC->IsMoveInputIgnored());
	G->FinishLegacyHardnessLoad(1);
	TestFalse(TEXT("the gate opens after the reset: released"), PC->IsMoveInputIgnored());

	// The controller changed while the gate is closed (a new possession): the hold moves with it.
	D->GetDink().Actor = Pawn;
	G->GateOriginalHardnessTransition();
	APlayerController* PC2 = World->SpawnActor<APlayerController>();
	if (!TestNotNull(TEXT("second controller"), PC2)) return false;
	PC->UnPossess();
	PC2->Possess(Pawn);
	D->UpdatePlayerMoveHold();
	TestFalse(TEXT("the old controller is given back its count"), PC->IsMoveInputIgnored());
	TestTrue(TEXT("the new one is held"), PC2->IsMoveInputIgnored());
	G->FinishLegacyHardnessLoad(1);
	TestFalse(TEXT("gate open: the new controller is free"), PC2->IsMoveInputIgnored());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFreezeFallbackGravityTest, "Dink.Input.ResetRestoresGravityWithoutPawnLink", DINK_TEST_FLAGS)
bool FDinkFreezeFallbackGravityTest::RunTest(const FString& Parameters)
{
	UDinkStorySubsystem* Story = DinkMoveHoldTest::MakeStory(*this);
	if (!Story) return false;
	UDinkDirector* D = Story->GetDirector();

	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
	ACharacter* Pawn = World->SpawnActor<ACharacter>();
	APlayerController* PC = World->SpawnActor<APlayerController>();
	if (!TestNotNull(TEXT("pawn"), Pawn) || !TestNotNull(TEXT("controller"), PC)) return false;
	PC->Possess(Pawn);
	UCharacterMovementComponent* Movement = Pawn->GetCharacterMovement();
	const float Gravity = Movement->GravityScale;

	// Dink's pawn link is gone before the reset (UDinkDirector::ResetSprites' old fallback branch restored no gravity).
	D->GetDink().Actor = Pawn;
	D->SetFrozen(1, true);
	TestEqual(TEXT("frozen: no gravity"), Movement->GravityScale, 0.f);
	D->GetDink().Actor = nullptr;
	D->ResetSprites();
	TestFalse(TEXT("pawn link gone: the reset still releases the controller"), PC->IsMoveInputIgnored());
	TestEqual(TEXT("and gives the gravity back"), Movement->GravityScale, Gravity);

	// Dink's whole record is gone before the reset.
	D->GetDink().Actor = Pawn;
	D->SetFrozen(1, true);
	TestEqual(TEXT("frozen again: no gravity"), Movement->GravityScale, 0.f);
	D->Sprites.Remove(1);
	D->ResetSprites();
	TestFalse(TEXT("record gone: the reset releases the controller"), PC->IsMoveInputIgnored());
	TestEqual(TEXT("and gives the gravity back"), Movement->GravityScale, Gravity);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkScreenLoadUnfreezeTest, "Dink.Input.ScreenLoadClearsFreeze", DINK_TEST_FLAGS)
bool FDinkScreenLoadUnfreezeTest::RunTest(const FString& Parameters)
{
	UDinkStorySubsystem* Story = DinkMoveHoldTest::MakeStory(*this);
	if (!Story) return false;
	UDinkDirector* D = Story->GetDirector();
	Story->OnScreenEntered(209);

	// s1-hole3's touch (the pit of SCR_209): freeze(1), the fall's wait(2000), script_attach(1000), load_screen to SCR_198. Here the
	// instance is attached to 1000 from the start, so it survives screen changes and is still running when one comes.
	const int32 Id = Story->StartProcedure(TEXT("s1-hole3"), TEXT("touch"), UDinkDirector::HandleNoSprite, {}, 209, /*bNewInstance*/ true);
	if (!TestTrue(TEXT("s1-hole3 touch starts"), Id != 0)) return false;
	Story->RunUntilIdle();
	const FDinkScriptInstance* I = Story->FindInstance(Id);
	TestTrue(TEXT("the pit froze Dink"), D->GetDink().bFrozen);
	TestTrue(TEXT("and waits out the fall (a running survivor)"), I && I->IsAlive() && I->State == EDinkInstanceState::Blocked);

	// A screen load by walking or a warp: load_map clears the freeze although the script survives (dink.cpp:1013-1015).
	Story->OnScreenEntered(210);
	TestFalse(TEXT("a screen load clears Dink's freeze, as load_map does"), D->GetDink().bFrozen);
	I = Story->FindInstance(Id);
	TestTrue(TEXT("the surviving script still runs"), I && I->IsAlive());

	// dink_can_walk_off_screen(1) (s2-culg.c:37-39 walks a frozen Dink off the bottom with a script that survives): the original
	// loads no screen at an edge then (dink.cpp:14056), so the remaster's edge change does not clear the freeze.
	D->SetFrozen(1, true);
	D->bDinkCanWalkOffScreen = true;
	D->StartMove(D->GetDink(), 2, 700, 1); // s2-culg.c:38 move(1, 2, 700, 1)
	Story->OnScreenEntered(211);
	TestTrue(TEXT("walking off the screen by script: the freeze stays"), D->GetDink().bFrozen);
	TestTrue(TEXT("and so does the scripted move"), D->GetDink().bMoving && D->GetDink().bMoveNoHard);
	D->bDinkCanWalkOffScreen = false;

	// load_map also stops Dink's scripted move (move_active and move_nohard false, dink.cpp:1013-1014): a walk or warp screen load.
	Story->OnScreenEntered(212);
	TestFalse(TEXT("a screen load stops Dink's scripted move"), D->GetDink().bMoving);
	TestFalse(TEXT("and clears its nohard"), D->GetDink().bMoveNoHard);
	TestFalse(TEXT("and his freeze"), D->GetDink().bFrozen);
	D->StartMove(D->GetDink(), 6, 900, 1);
	{
		FDinkScriptInstance Mover;
		Mover.Sprite = UDinkDirector::HandleNoSprite;
		Story->GetFacts()->SetFact(TEXT("player_map"), 213);
		D->Execute(Mover, FDinkStoryLine::Parse(TEXT(">> load_screen"), { TEXT("cmd"), TEXT("src:1") }));
	}
	TestFalse(TEXT("load_screen stops Dink's scripted move when it runs"), D->GetDink().bMoving || D->GetDink().bMoveNoHard);
	Story->OnScreenEntered(213);

	// The greybox reports a new screen up to ~0.25 s after the crossing. A freeze or move started after the crossing (Esc runs
	// escape.c, whose freeze(1) comes at once; the death script; a spell) is not one load_map would have cleared.
	Story->NoteScreenCrossing();
	D->SetFrozen(1, true); // escape.c:7, after the crossing
	Story->OnScreenEntered(214);
	TestTrue(TEXT("a freeze taken after the crossing survives the late screen entry"), D->GetDink().bFrozen);
	Story->NoteScreenCrossing(); // frozen before this crossing
	Story->OnScreenEntered(215);
	TestFalse(TEXT("a freeze from before the crossing is cleared"), D->GetDink().bFrozen);
	Story->NoteScreenCrossing();
	D->StartMove(D->GetDink(), 6, 900, 0); // a move started after the crossing
	Story->OnScreenEntered(216);
	TestTrue(TEXT("a move started after the crossing goes on"), D->GetDink().bMoving);
	Story->OnScreenEntered(217); // no crossing noted (a teleport): everything Dink has is from before
	TestFalse(TEXT("the next load stops it"), D->GetDink().bMoving);

	// dink_can_walk_off_screen spares only edge crossings: a warp still runs load_map (dink.cpp:15724).
	TestFalse(TEXT("edge crossing while walking off by script: no load_map"), UDinkStorySubsystem::IsLoadMapEntry(false, false, false, true));
	TestTrue(TEXT("a warp while walking off by script: load_map"), UDinkStorySubsystem::IsLoadMapEntry(false, false, true, true));
	TestTrue(TEXT("an edge crossing: load_map"), UDinkStorySubsystem::IsLoadMapEntry(false, false, false, false));
	TestFalse(TEXT("force_vision: no load_map"), UDinkStorySubsystem::IsLoadMapEntry(true, false, true, false));
	TestFalse(TEXT("the screen a script's load_screen loaded: already done"), UDinkStorySubsystem::IsLoadMapEntry(false, true, false, false));

	// A script's load_screen clears it at once (dink.cpp:7874-7878); a freeze the script takes after it survives the screen entry.
	D->SetFrozen(1, true);
	Story->GetFacts()->SetFact(TEXT("player_map"), 198);
	FDinkScriptInstance Caller;
	Caller.Sprite = UDinkDirector::HandleNoSprite;
	D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> load_screen"), { TEXT("cmd"), TEXT("src:1") }));
	TestFalse(TEXT("load_screen clears the freeze when it runs"), D->GetDink().bFrozen);
	D->SetFrozen(1, true); // the script freezes him again before the screen is entered
	Story->OnScreenEntered(198);
	TestTrue(TEXT("the screen it loaded is entered: the script's new freeze stays"), D->GetDink().bFrozen);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkScriptlessEntryOpensGateTest, "Dink.Input.ScriptlessScreenEntryOpensHardnessGate", DINK_TEST_FLAGS)
bool FDinkScriptlessEntryOpensGateTest::RunTest(const FString& Parameters)
{
	// dink.ScreenScripts 0 (capture runs): a marked screen's entry closes the hardness gate and only the placement pass, which does not
	// run without scripts, would open it again; Dink stayed held (move_ignored=1) on SCR_539, 666 and 383 after dink.Goto (alpha A86).
	UDinkStorySubsystem* Story = DinkMoveHoldTest::MakeStory(*this);
	if (!Story) return false;
	UDinkDirector* D = Story->GetDirector();
	UDinkGameplay* G = Story->GetGameplay();
	Story->bRunScreenScripts = false;
	G->GateOriginalHardnessTransition(); // what the entry of a marked screen does first
	D->SetFrozen(1, true);               // the opening scene's freeze, left behind when screen scripts were switched off
	Story->OnScreenEntered(539);
	TestFalse(TEXT("scriptless entry: the hardness gate is open again"), G->IsHardnessLoading());
	TestFalse(TEXT("and load_map cleared Dink's freeze"), D->GetDink().bFrozen);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWalkOffScreenHoldTest, "Dink.Input.WalkOffScreenLoadsNoScreen", DINK_TEST_FLAGS)
bool FDinkWalkOffScreenHoldTest::RunTest(const FString& Parameters)
{
	// dink_can_walk_off_screen(1): did_player_cross_screen returns at once (dink.cpp:14056), so walking over an edge loads no screen.
	// s2-culg.c:37-43 walks Dink 700 px south off SCR_238 while the screen fades, then load_screen's Nadine's house (SCR_066); the
	// remaster entered the screen south of 238 (SCR_270: its scripts ran, its screenlock came on, Dink's pixels moved to it).
	TestTrue(TEXT("an edge crossing while walking off: not entered"), UDinkStorySubsystem::IsHeldWalkOff(true, false, false));
	TestFalse(TEXT("a warp while walking off: entered (dink.cpp:15724)"), UDinkStorySubsystem::IsHeldWalkOff(true, true, false));
	TestFalse(TEXT("the screen a script's load_screen loaded: entered"), UDinkStorySubsystem::IsHeldWalkOff(true, false, true));
	TestFalse(TEXT("an edge crossing without the flag: entered"), UDinkStorySubsystem::IsHeldWalkOff(false, false, false));

	UDinkStorySubsystem* Story = DinkMoveHoldTest::MakeStory(*this);
	if (!Story) return false;
	UDinkDirector* D = Story->GetDirector();
	Story->OnScreenEntered(238);
	FDinkScriptInstance Caller;
	Caller.Sprite = UDinkDirector::HandleNoSprite;
	D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> dink_can_walk_off_screen 1"), { TEXT("cmd"), TEXT("src:1") }));
	TestTrue(TEXT("the flag is set"), D->bDinkCanWalkOffScreen);
	// What PollScreenChange does when the pawn's ground is SCR_270's: Dink stays on 238.
	D->WalkOffHeldScreen = 238;
	TestEqual(TEXT("held past the edge: the current screen is still 238"), D->GetCurrentScreen(), 238);
	// s2-culg.c:42-43: &player_map = 66; load_screen(66). The screen he is on is now the loaded one, before the greybox reports it.
	Story->GetFacts()->SetFact(TEXT("player_map"), 66);
	D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> load_screen"), { TEXT("cmd"), TEXT("src:1") }));
	TestEqual(TEXT("load_screen while held: Dink is on the loaded screen"), D->GetCurrentScreen(), 66);
	TestFalse(TEXT("the loaded screen is entered, not held (a script's load_screen)"), UDinkStorySubsystem::IsHeldWalkOff(D->bDinkCanWalkOffScreen, false, D->GetScriptLoadedScreen() == 66));
	D->WalkOffHeldScreen = 238;
	D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> dink_can_walk_off_screen 0"), { TEXT("cmd"), TEXT("src:1") }));
	TestEqual(TEXT("dink_can_walk_off_screen(0) lets the next crossing check load the screen"), D->WalkOffHeldScreen, int32(INDEX_NONE));
	D->WalkOffHeldScreen = 238;
	Story->OnScreenEntered(66);
	TestEqual(TEXT("a screen entry ends the hold"), D->WalkOffHeldScreen, int32(INDEX_NONE));
	return true;
}
