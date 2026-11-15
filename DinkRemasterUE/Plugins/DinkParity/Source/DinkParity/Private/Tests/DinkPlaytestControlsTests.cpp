// Dink.Gameplay.Controls.*: the player's keyboard and mouse as the game reads them (FDinkNarrativeInputProcessor), on the
// converted story without a world. The tests call the processor's Process* functions, which are exactly what its Slate
// handlers call once they have checked that a game world runs and the console is closed.

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkInventoryComponent.h"
#include "DinkNarrativeInput.h"
#include "DinkPresentationData.h"
#include "DinkStorySubsystem.h"
#include "InputCoreTypes.h"
#include "HAL/PlatformTime.h"

namespace DinkPlaytestControlsTest
{
	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* G = nullptr;
		TSharedPtr<FDinkNarrativeInputProcessor> Input;
		/** Every line put on screen (OnLineShown), robust against the bounded event list. */
		TSharedPtr<TArray<FString>> Shown = MakeShared<TArray<FString>>();
		bool IsValid() const { return Facts && World && Story && Story->IsReady() && G && G->HasData() && Input.IsValid(); }
	};

	/** Story, facts and world state outside any world, seeded; the input processor the game registers, without the click guard. */
	FEnv Make(FAutomationTestBase& Test, bool bInstant, bool bListen = true)
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
		Test.TestTrue(TEXT("gameplay data loaded (Scripts/sync_gameplay_data.py)"), E.G && E.G->HasData());
		E.Input = MakeShared<FDinkNarrativeInputProcessor>(E.Story);
		E.Input->MouseConfirmGuardSeconds = 0.;
		if (bListen && E.Story)
		{
			TSharedPtr<TArray<FString>> Shown = E.Shown;
			E.Story->OnLineShown.AddLambda([Shown](const FDinkLineShown& L) { Shown->Add(L.Text); });
		}
		return E;
	}

	void Settle(FEnv& E)
	{
		E.Story->RunUntilIdle();
		E.G->ProcessDamage();
		E.Story->RunUntilIdle();
	}

	void Frames(FEnv& E, int32 N)
	{
		for (int32 i = 0; i < N; ++i)
		{
			E.Story->Advance(1.0 / 60.0);
		}
	}

	/** Advances 60 Hz frames until Done() or MaxFrames; true if Done. */
	bool FramesUntil(FEnv& E, TFunctionRef<bool()> Done, int32 MaxFrames = 600)
	{
		for (int32 i = 0; i < MaxFrames; ++i)
		{
			if (Done())
			{
				return true;
			}
			E.Story->Advance(1.0 / 60.0);
		}
		return Done();
	}

	bool HasBlockingText(const UDinkStorySubsystem* S)
	{
		for (const FDinkActiveText& T : S->GetActiveTexts())
		{
			if (T.bBlocking)
			{
				return true;
			}
		}
		return false;
	}

	int32 CountKind(const UDinkStorySubsystem* S, FName Kind, int32 From = 0)
	{
		int32 N = 0;
		for (int32 i = From; i < S->Events.Num(); ++i)
		{
			N += S->Events[i].Kind == Kind ? 1 : 0;
		}
		return N;
	}

	TArray<FString> Said(const UDinkStorySubsystem* S, int32 From = 0)
	{
		TArray<FString> Out;
		for (int32 i = From; i < S->Events.Num(); ++i)
		{
			if (S->Events[i].Kind == TEXT("say"))
			{
				Out.Add(S->Events[i].Text);
			}
		}
		return Out;
	}

	int32 CountAttacks(const UDinkGameplay* G, int32 From = 0)
	{
		int32 N = 0;
		for (int32 i = From; i < G->Events.Num(); ++i)
		{
			N += G->Events[i].StartsWith(TEXT("attack with")) ? 1 : 0;
		}
		return N;
	}

	/** Dink west of the sprite's hardbox by Gap pixels, level with it, facing east. */
	void StandWestOf(FEnv& E, int32 Handle, int32 Gap = 20)
	{
		const FDinkSprite* T = E.D->FindSprite(Handle);
		int32 L = 0, Tp = 0, R = 0, B = 0;
		if (T && E.G->GetHardbox(*T, L, Tp, R, B))
		{
			FDinkSprite& Dink = E.D->GetDink();
			Dink.Screen = T->Screen;
			Dink.X = L - Gap;
			Dink.Y = T->Y;
			Dink.Dir = 6;
		}
	}
}

using namespace DinkPlaytestControlsTest;

// The owner's playtest (14 Nov 2026): "left click should also hit". A left click goes down the same press/release path as F
// (the attack gate, so one attack per press, and the bow draws while it is held); a fast second click, which Slate delivers as a
// double-click, is a press too. With a menu up the click picks the highlighted option, and with a blocking line up it skips the
// line, exactly as Enter does; in neither case does Dink attack.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkControlsLeftClickTest, "Dink.Gameplay.Controls.LeftClickAttacks", DINK_TEST_FLAGS)
bool FDinkControlsLeftClickTest::RunTest(const FString& Parameters)
{
	FEnv E = Make(*this, /*bInstant*/ true);
	if (!E.IsValid())
	{
		return false;
	}
	E.G->StartNewGame();
	Settle(E);
	E.Story->OnScreenEntered(1);
	Settle(E);
	TestEqual(TEXT("new game: the fists are armed"), E.D->GetInventory()->GetArmedItem(), FName(TEXT("item-fst")));
	// s1-sack.c `hit`: "I hate you, sack of feed!" proves the fists' hit reached a target.
	const int32 Sack = E.D->HandleForPlacement(1, 52);
	TestTrue(TEXT("the sack S001_P52 is a sprite"), Sack > 1);
	StandWestOf(E, Sack);
	E.D->GetDink().bFrozen = false;

	int32 From = E.Story->Events.Num();
	int32 AttacksFrom = E.G->Events.Num();
	TestTrue(TEXT("left button down: used"), E.Input->ProcessMouseDown(EKeys::LeftMouseButton));
	TestEqual(TEXT("left button held as the attack input"), E.Input->GetAttackKeyDown(), EKeys::LeftMouseButton);
	TestTrue(TEXT("the attack gate holds the key"), E.G->GetAttackGate().IsHeld());
	Settle(E);
	TestEqual(TEXT("one attack with the fists"), CountAttacks(E.G, AttacksFrom), 1);
	TestTrue(TEXT("s1-sack hit: \"I hate you, sack of feed!\""), Said(E.Story, From).Contains(TEXT("I hate you, sack of feed!")));
	TestFalse(TEXT("a right click does nothing"), E.Input->ProcessMouseDown(EKeys::RightMouseButton));
	E.Input->ProcessMouseUp(EKeys::LeftMouseButton);
	TestFalse(TEXT("the release lets the key go at once"), E.G->GetAttackGate().IsHeld());
	TestFalse(TEXT("no attack input held"), E.Input->GetAttackKeyDown().IsValid());

	// A second click while F is held does not start a second attack (one attack input at a time), and F's own release still works.
	Frames(E, 60);
	AttacksFrom = E.G->Events.Num();
	E.Input->ProcessKeyDown(EKeys::F);
	E.Input->ProcessMouseDown(EKeys::LeftMouseButton);
	TestEqual(TEXT("F then a click: one attack"), CountAttacks(E.G, AttacksFrom), 1);
	E.Input->ProcessMouseUp(EKeys::LeftMouseButton);
	TestEqual(TEXT("the click's release does not let F go"), E.Input->GetAttackKeyDown(), EKeys::F);

	// Down, up, then the double-click event and up (what Slate sends for two quick clicks): two attacks, the second
	// remembered by the gate while the first still locks Dink and started when the lock ends.
	E.Input->ProcessKeyUp(EKeys::F);
	E.Input->UpdateRelease(FPlatformTime::Seconds() + 1.0, /*bAppActive*/ true); // the repeat guard has passed
	TestFalse(TEXT("F let go after the repeat guard"), E.Input->GetAttackKeyDown().IsValid());
	Frames(E, 60);
	E.D->GetDink().bFrozen = false;
	AttacksFrom = E.G->Events.Num();
	E.Input->ProcessMouseDown(EKeys::LeftMouseButton);
	E.Input->ProcessMouseUp(EKeys::LeftMouseButton);
	E.Input->ProcessMouseDown(EKeys::LeftMouseButton); // HandleMouseButtonDoubleClickEvent calls this
	E.Input->ProcessMouseUp(EKeys::LeftMouseButton);
	Frames(E, 60);
	Settle(E);
	TestEqual(TEXT("a double-click is two attacks"), CountAttacks(E.G, AttacksFrom), 2);

	// A menu: the click picks the highlighted option and is not an attack.
	FEnv M = Make(*this, /*bInstant*/ false);
	if (!M.IsValid())
	{
		return false;
	}
	M.G->StartNewGame();
	M.Story->bInstantMode = true;
	Settle(M);
	M.Story->bInstantMode = false;
	const int32 Mom = M.D->CreateVirtualSprite(1, 300, 200);
	M.Story->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), Mom);
	M.Story->RunUntilIdle();
	TestNotNull(TEXT("mother's talk menu is up"), M.Story->GetActiveMenu());
	M.Story->MoveMenuSelection(1); // "Ask about your father"
	AttacksFrom = M.G->Events.Num();
	From = M.Story->Events.Num();
	TestTrue(TEXT("a click on the menu is used"), M.Input->ProcessMouseDown(EKeys::LeftMouseButton));
	TestNull(TEXT("the menu is gone"), M.Story->GetActiveMenu());
	TestEqual(TEXT("no attack from the menu click"), CountAttacks(M.G, AttacksFrom), 0);
	TestFalse(TEXT("the menu click holds no attack key"), M.Input->GetAttackKeyDown().IsValid());
	M.Input->ProcessMouseUp(EKeys::LeftMouseButton);

	// The answer is a say_stop: a blocking line. The click skips it (as Enter does) instead of attacking.
	TestTrue(TEXT("Dink's question is a blocking line"), FramesUntil(M, [&M]() { return HasBlockingText(M.Story); }));
	TestEqual(TEXT("&result 2: the highlighted option was picked"), M.Facts->GetFact(TEXT("result")), 2);
	TestTrue(TEXT("the line is Dink's question"), M.Shown->Contains(TEXT("What kind of a man was father?")));
	const int32 Skips = CountKind(M.Story, TEXT("skip"));
	AttacksFrom = M.G->Events.Num();
	TestTrue(TEXT("a click on a blocking line is used"), M.Input->ProcessMouseDown(EKeys::LeftMouseButton));
	TestEqual(TEXT("the line was skipped"), CountKind(M.Story, TEXT("skip")), Skips + 1);
	TestEqual(TEXT("no attack from the skip click"), CountAttacks(M.G, AttacksFrom), 0);
	M.Input->ProcessMouseUp(EKeys::LeftMouseButton);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkControlsClickNeedsFocusedViewportTest, "Dink.Gameplay.Controls.ClickNeedsFocusedViewport", DINK_TEST_FLAGS)
bool FDinkControlsClickNeedsFocusedViewportTest::RunTest(const FString& Parameters)
{
	// Slate hands the pre-processor every click of the application. The Slate handlers ask AcceptsClick (with whether the
	// click is over the game viewport) before ProcessMouseDown; Tick notes the viewport's focus after each frame's input.
	FDinkNarrativeInputProcessor Input(nullptr);
	TestFalse(TEXT("before any tick has seen the viewport focused, a click on it is the focusing click"), Input.AcceptsClick(true));
	Input.NoteViewportFocus(false);
	TestFalse(TEXT("viewport not focused (another window or an editor panel has focus): the click that focuses it is not game input"), Input.AcceptsClick(true));
	TestFalse(TEXT("viewport not focused, click elsewhere: not game input"), Input.AcceptsClick(false));
	Input.NoteViewportFocus(true);
	TestTrue(TEXT("viewport focused, click on it: game input"), Input.AcceptsClick(true));
	TestFalse(TEXT("viewport focused, click on an editor panel (PIE): not game input"), Input.AcceptsClick(false));
	Input.NoteViewportFocus(false);
	TestFalse(TEXT("focus lost again: the next click is a focusing click again"), Input.AcceptsClick(true));
	return true;
}

// The owner's playtest: "it has you do the pig feeding, but there doesn't seem to be a way to actually push a button to spread
// the feed". The whole first quest by the player's own input: touch the sack (s1-sack touch: add_item item-pig), Enter opens the
// inventory (the game stops), the cursor moves to the feed and the attack key arms it (the same ArmItemSlot as the console's
// dink.Arm), Enter closes it, and on SCR_407 a left click throws the feed (item-pig use: inside_box 200,180-400,306), which starts
// the bully's scene (s1-bul) and sets &pig_story 1.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkControlsPigFeedingTest, "Dink.Gameplay.Controls.PigFeedingByInput", DINK_TEST_FLAGS)
bool FDinkControlsPigFeedingTest::RunTest(const FString& Parameters)
{
	FEnv E = Make(*this, /*bInstant*/ true);
	if (!E.IsValid())
	{
		return false;
	}
	E.G->StartNewGame();
	Settle(E);
	E.Story->OnScreenEntered(1);
	Settle(E);
	const int32 Sack = E.D->HandleForPlacement(1, 52);
	const FDinkSprite* SackSprite = E.D->FindSprite(Sack);
	if (!TestNotNull(TEXT("the sack S001_P52"), SackSprite))
	{
		return false;
	}
	FDinkSprite& Dink = E.D->GetDink();
	Dink.Screen = SackSprite->Screen;
	Dink.X = SackSprite->X;
	Dink.Y = SackSprite->Y;
	E.Story->Advance(0.016);
	Settle(E);
	Frames(E, 30);
	TestEqual(TEXT("touch the sack: item-pig in slot 2"), E.D->GetInventory()->GetItemAt(1), FName(TEXT("item-pig")));
	TestEqual(TEXT("still the fists armed"), E.D->GetInventory()->GetArmedItem(), FName(TEXT("item-fst")));
	TestFalse(TEXT("Dink may act"), Dink.bFrozen);

	// Enter opens the inventory and the game stops.
	TestTrue(TEXT("Enter opens the inventory"), E.Input->ProcessKeyDown(EKeys::Enter));
	TestTrue(TEXT("the inventory is open"), E.Story->IsInventoryOpen());
	const double Paused = E.Story->GetNowMs();
	const int32 MagicLevel = E.Facts->GetFact(TEXT("magic_level"));
	Frames(E, 60);
	TestEqual(TEXT("no game time passes while it is open"), E.Story->GetNowMs(), Paused);
	TestEqual(TEXT("no status update while it is open"), E.Facts->GetFact(TEXT("magic_level")), MagicLevel);
	TestEqual(TEXT("the cursor starts on item slot 1"), E.Story->GetInventoryScreen().Cursor, 1);
	TestFalse(TEXT("on the item panel"), E.Story->GetInventoryScreen().bMagic);
	TestTrue(TEXT("E does nothing while it is open"), E.Input->ProcessKeyDown(EKeys::E));
	TestEqual(TEXT("no attack from the inventory's keys"), CountAttacks(E.G), 0);

	// Right twice: slot 3 is empty; arming it does nothing ("can't arm nothing", dink.cpp:16500).
	E.Input->ProcessKeyDown(EKeys::Right);
	E.Input->ProcessKeyDown(EKeys::Right);
	TestEqual(TEXT("cursor on slot 3"), E.Story->GetInventoryScreen().Cursor, 3);
	E.Input->ProcessKeyDown(EKeys::F);
	TestEqual(TEXT("an empty slot arms nothing"), E.D->GetInventory()->GetArmedItem(), FName(TEXT("item-fst")));
	// Left to slot 2 and the attack key arms the feed.
	E.Input->ProcessKeyDown(EKeys::Left);
	TestEqual(TEXT("cursor on slot 2"), E.Story->GetInventoryScreen().Cursor, 2);
	const int32 Cues = E.D->Audio.Cues.Num();
	TestTrue(TEXT("F on the item screen is used"), E.Input->ProcessKeyDown(EKeys::F));
	TestEqual(TEXT("the feed is armed"), E.D->GetInventory()->GetArmedItem(), FName(TEXT("item-pig")));
	TestEqual(TEXT("&cur_weapon 2"), E.Facts->GetFact(TEXT("cur_weapon")), 2);
	TestTrue(TEXT("the arm sound (18 at 42050, dink.cpp:16479)"), E.D->Audio.Cues.Num() > Cues && E.D->Audio.Cues.Last().StartsWith(TEXT("sound:18 speed=42050")));
	TestTrue(TEXT("still open after arming"), E.Story->IsInventoryOpen());
	E.Input->ProcessKeyUp(EKeys::F);
	TestTrue(TEXT("Enter closes it"), E.Input->ProcessKeyDown(EKeys::Enter));
	TestFalse(TEXT("closed"), E.Story->IsInventoryOpen());
	Frames(E, 6);
	TestTrue(TEXT("game time runs again"), E.Story->GetNowMs() > Paused);

	// SCR_407, in the pen, facing south: a left click throws the feed.
	E.Story->OnScreenEntered(407);
	Settle(E);
	FDinkSprite& DinkIn407 = E.D->GetDink(); // the screen change rebuilds the sprite table: take Dink again
	DinkIn407.X = 300;
	DinkIn407.Y = 250;
	DinkIn407.Dir = 2;
	DinkIn407.bFrozen = false;
	E.Shown->Reset();
	const int32 AttacksFrom = E.G->Events.Num();
	TestTrue(TEXT("left click on SCR_407"), E.Input->ProcessMouseDown(EKeys::LeftMouseButton));
	Settle(E);
	E.Input->ProcessMouseUp(EKeys::LeftMouseButton);
	if (CountAttacks(E.G, AttacksFrom) == 0)
	{
		const FDinkAttackGate& Gate = E.G->GetAttackGate();
		AddInfo(FString::Printf(TEXT("no attack: weapon instance %d, armed %s, frozen %d, bow %d, gate held %d locked %d buffered %d, inventory %d, texts %d"),
			E.G->GetWeaponInstance(), *E.D->GetInventory()->GetArmedItem().ToString(), DinkIn407.bFrozen ? 1 : 0, E.G->IsBowActive() ? 1 : 0,
			Gate.IsHeld() ? 1 : 0, Gate.IsLocked(E.Story->GetNowMs()) ? 1 : 0, Gate.HasBuffered() ? 1 : 0, E.Story->IsInventoryOpen() ? 1 : 0, E.Story->GetActiveTexts().Num()));
		for (int32 i = FMath::Max(0, E.G->Events.Num() - 8); i < E.G->Events.Num(); ++i)
		{
			AddInfo(TEXT("game event: ") + E.G->Events[i]);
		}
	}
	TestEqual(TEXT("the click is one attack with the feed"), CountAttacks(E.G, AttacksFrom), 1);
	TestTrue(TEXT("\"Come on pigs, eat!\""), E.Shown->Contains(TEXT("Come on pigs, eat!")));
	TestTrue(TEXT("the bully says his line"), E.Shown->Contains(TEXT("Well, lookie what we got here.")));
	TestEqual(TEXT("the bully's scene: &pig_story 1"), E.Facts->GetFact(TEXT("pig_story")), 1);
	return true;
}

// The item screen's cursor (dink.cpp:16483-16620): 4 x 4 items, 2 x 4 spells to their left; left from the first item column goes to
// the magic panel's right column on the same row, right from there comes back; the edges hold. Digits quick-arm item slots
// outside menus, and pick options inside them. Enter's precedence: menu, then skip, then the inventory; never while frozen.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkControlsInventoryRulesTest, "Dink.Gameplay.Controls.InventoryRules", DINK_TEST_FLAGS)
bool FDinkControlsInventoryRulesTest::RunTest(const FString& Parameters)
{
	FEnv E = Make(*this, /*bInstant*/ true);
	if (!E.IsValid())
	{
		return false;
	}
	E.G->StartNewGame();
	Settle(E);
	E.Story->OnScreenEntered(1);
	Settle(E);
	FDinkSprite& Dink = E.D->GetDink();
	Dink.bFrozen = true;
	TestFalse(TEXT("frozen: Enter does not open the inventory"), E.Input->ProcessKeyDown(EKeys::Enter));
	TestFalse(TEXT("frozen: closed"), E.Story->IsInventoryOpen());
	TestFalse(TEXT("frozen: no quick-arm"), E.Story->QuickArmItemSlot(1));
	Dink.bFrozen = false;

	TestTrue(TEXT("I opens the inventory"), E.Input->ProcessKeyDown(EKeys::I));
	const FDinkInventoryScreen& Inv = E.Story->GetInventoryScreen();
	E.Input->ProcessKeyDown(EKeys::Down);
	TestEqual(TEXT("down: slot 5"), Inv.Cursor, 5);
	E.Input->ProcessKeyDown(EKeys::Left);
	TestTrue(TEXT("left from column 1: the magic panel"), Inv.bMagic);
	TestEqual(TEXT("its right column, same row (curitem = virt * 2 + 2)"), Inv.Cursor, 4);
	E.Input->ProcessKeyDown(EKeys::Left);
	E.Input->ProcessKeyDown(EKeys::Left);
	TestEqual(TEXT("the magic panel's left edge holds"), Inv.Cursor, 3);
	TestTrue(TEXT("still on magic"), Inv.bMagic);
	E.Input->ProcessKeyDown(EKeys::Right);
	E.Input->ProcessKeyDown(EKeys::Right);
	TestFalse(TEXT("right from the magic panel's right column: the items"), Inv.bMagic);
	TestEqual(TEXT("their first column, same row (curitem = virt * 4 + 1)"), Inv.Cursor, 5);
	for (int32 i = 0; i < 5; ++i)
	{
		E.Input->ProcessKeyDown(EKeys::S);
		E.Input->ProcessKeyDown(EKeys::D);
	}
	TestEqual(TEXT("the bottom-right edge holds: slot 16"), Inv.Cursor, 16);
	E.Input->ProcessKeyDown(EKeys::SpaceBar);
	TestEqual(TEXT("an empty slot: the fists stay armed"), E.D->GetInventory()->GetArmedItem(), FName(TEXT("item-fst")));
	TestTrue(TEXT("Escape closes it"), E.Input->ProcessKeyDown(EKeys::Escape));
	TestFalse(TEXT("closed"), E.Story->IsInventoryOpen());
	TestTrue(TEXT("I again: the cursor kept its place"), E.Input->ProcessKeyDown(EKeys::I) && Inv.Cursor == 16);
	E.Input->ProcessKeyDown(EKeys::I);
	TestFalse(TEXT("I closes it too"), E.Story->IsInventoryOpen());

	// Quick-arm outside menus: the same arming as the screen's (dink.Arm's ArmItemSlot).
	E.D->GetInventory()->AddItem(TEXT("item-pig")); // slot 2, without its pickup script
	TestTrue(TEXT("2 quick-arms slot 2"), E.Input->ProcessKeyDown(EKeys::Two));
	TestEqual(TEXT("the feed is armed"), E.D->GetInventory()->GetArmedItem(), FName(TEXT("item-pig")));
	TestFalse(TEXT("3: an empty slot"), E.Input->ProcessKeyDown(EKeys::Three));
	TestEqual(TEXT("still the feed"), E.D->GetInventory()->GetArmedItem(), FName(TEXT("item-pig")));
	TestTrue(TEXT("1 quick-arms the fists"), E.Input->ProcessKeyDown(EKeys::One));
	TestEqual(TEXT("the fists are armed"), E.D->GetInventory()->GetArmedItem(), FName(TEXT("item-fst")));

	// A menu keeps Enter and the digits.
	FEnv M = Make(*this, /*bInstant*/ false);
	if (!M.IsValid())
	{
		return false;
	}
	M.G->StartNewGame();
	M.Story->bInstantMode = true;
	Settle(M);
	M.Story->bInstantMode = false;
	const int32 Mom = M.D->CreateVirtualSprite(1, 300, 200);
	M.Story->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), Mom);
	M.Story->RunUntilIdle();
	TestNotNull(TEXT("menu up"), M.Story->GetActiveMenu());
	M.D->GetDink().bFrozen = false; // even if Dink could act, the menu comes first
	TestTrue(TEXT("2 with a menu up picks option 2"), M.Input->ProcessKeyDown(EKeys::Two));
	TestFalse(TEXT("no inventory from the digit"), M.Story->IsInventoryOpen());
	TestTrue(TEXT("Dink's question (a blocking line) is up"), FramesUntil(M, [&M]() { return HasBlockingText(M.Story); }));
	TestEqual(TEXT("&result 2"), M.Facts->GetFact(TEXT("result")), 2);
	M.D->GetDink().bFrozen = false;
	const int32 Skips = CountKind(M.Story, TEXT("skip"));
	TestTrue(TEXT("Enter on a blocking line"), M.Input->ProcessKeyDown(EKeys::Enter));
	TestEqual(TEXT("Enter skipped the line"), CountKind(M.Story, TEXT("skip")), Skips + 1);
	TestFalse(TEXT("and did not open the inventory"), M.Story->IsInventoryOpen());
	return true;
}

// Presentation data (Content/Dink/Data/Presentation): readable item names for the inventory screen and speaker names for the
// dialogue box's name plate, by Ink line id (speakers.csv, Scripts/export_presentation_data.py from the voice ledger).
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPresentationDataTest, "Dink.Narrative.Presentation.NamesTables", DINK_TEST_FLAGS)
bool FDinkPresentationDataTest::RunTest(const FString& Parameters)
{
	const FDinkPresentationData& Data = FDinkPresentationData::Get();
	TestTrue(TEXT("items.csv loaded"), Data.NumItems() >= 17);
	TestTrue(TEXT("speakers.csv loaded"), Data.NumSpeakers() > 1500);
	TestEqual(TEXT("item-pig"), Data.ItemName(TEXT("item-pig")), FString(TEXT("Pig Feed")));
	TestEqual(TEXT("item-sw1"), Data.ItemName(TEXT("item-sw1")), FString(TEXT("Longsword")));
	TestEqual(TEXT("item-fb (a spell)"), Data.ItemName(TEXT("item-fb")), FString(TEXT("Fireball")));
	TestEqual(TEXT("a D-Mod's unknown item: derived"), Data.ItemName(TEXT("item-golden-key")), FString(TEXT("Golden key")));
	TestFalse(TEXT("no icon yet (art follow-up)"), Data.ItemIcon(TEXT("item-pig")).IsValid());
	TestEqual(TEXT("mother's line"), Data.SpeakerName(TEXT("s1-h1-m.talk.005"), 7), FString(TEXT("Mother")));
	TestEqual(TEXT("Dink by line id"), Data.SpeakerName(TEXT("s1-h1-m.talk.004"), 1), FString(TEXT("Dink")));
	TestEqual(TEXT("Dink without a line id"), Data.SpeakerName(FString(), 1), FString(TEXT("Dink")));
	TestEqual(TEXT("someone unknown: no name plate"), Data.SpeakerName(TEXT("no-such.line.001"), 9), FString());
	FDinkPresentationData Local;
	TestTrue(TEXT("quoted names with commas parse"), Local.LoadSpeakers(TEXT("line_id,name\nx.talk.001,\"Guard, the Second\"\n")));
	TestEqual(TEXT("quoted name"), Local.SpeakerName(TEXT("x.talk.001"), 3), FString(TEXT("Guard, the Second")));
	return true;
}

// The voice playback hook: every spoken line put on screen is broadcast with its line id, speaker and name; a skip is broadcast
// too. Listening changes nothing: the same lines, in the same order, at the same times as without a listener.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkLineShownHookTest, "Dink.Narrative.Presentation.LineShownHook", DINK_TEST_FLAGS)
bool FDinkLineShownHookTest::RunTest(const FString& Parameters)
{
	auto Run = [this](bool bListen, TArray<FDinkLineShown>& Shown, TArray<int32>& Skipped, TArray<FString>& Trace)
	{
		FEnv E = Make(*this, /*bInstant*/ false, /*bListen*/ false);
		if (!E.IsValid())
		{
			return;
		}
		E.G->StartNewGame();
		E.Story->bInstantMode = true;
		Settle(E);
		E.Story->bInstantMode = false;
		if (bListen)
		{
			E.Story->OnLineShown.AddLambda([&Shown](const FDinkLineShown& L) { Shown.Add(L); });
			E.Story->OnLineSkipped.AddLambda([&Skipped](int32 Handle) { Skipped.Add(Handle); });
		}
		const int32 From = E.Story->Events.Num();
		const int32 Mom = E.D->CreateVirtualSprite(1, 300, 200);
		E.Story->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), Mom);
		E.Story->RunUntilIdle();
		E.Story->Choose(1); // "Ask about your father"
		for (int32 i = 0; i < 1800; ++i)
		{
			Frames(E, 1);
			if (i == 30)
			{
				E.Story->SkipDialogue(); // the player skips the first line half a second in
			}
			if (i > 60 && E.Story->GetActiveTexts().Num() == 0 && !E.Story->GetActiveMenu() && !E.D->GetDink().bFrozen)
			{
				break;
			}
		}
		for (int32 i = From; i < E.Story->Events.Num(); ++i)
		{
			const FDinkNarrativeEvent& Ev = E.Story->Events[i];
			Trace.Add(FString::Printf(TEXT("%.0f %s %s %s"), Ev.TimeMs, *Ev.Kind.ToString(), *Ev.Text, *Ev.Detail));
		}
	};
	TArray<FDinkLineShown> Shown, Unused;
	TArray<int32> Skipped, UnusedSkips;
	TArray<FString> WithListener, Without;
	Run(true, Shown, Skipped, WithListener);
	Run(false, Unused, UnusedSkips, Without);
	TestEqual(TEXT("listening changes nothing in the story's events and times"), WithListener, Without);
	TestEqual(TEXT("four lines shown"), Shown.Num(), 4);
	if (Shown.Num() == 4)
	{
		TestEqual(TEXT("first: Dink's question, by id"), Shown[0].LineId, FString(TEXT("s1-h1-m.talk.004")));
		TestEqual(TEXT("Dink speaks"), Shown[0].Speaker, 1);
		TestEqual(TEXT("name plate Dink"), Shown[0].SpeakerName, FString(TEXT("Dink")));
		TestTrue(TEXT("say_stop: blocking"), Shown[0].bBlocking);
		TestEqual(TEXT("second: mother's answer"), Shown[1].LineId, FString(TEXT("s1-h1-m.talk.005")));
		TestEqual(TEXT("name plate Mother"), Shown[1].SpeakerName, FString(TEXT("Mother")));
		TestEqual(TEXT("the text"), Shown[1].Text, FString(TEXT("He was a peasant like us.")));
		TestTrue(TEXT("expiry is the engine's (at least 2.7 s)"), Shown[1].ExpireMs - Shown[1].ShownMs >= 2700.0);
	}
	TestEqual(TEXT("one skip broadcast"), Skipped.Num(), 1);
	if (Skipped.Num() == 1 && Shown.Num() > 0)
	{
		TestEqual(TEXT("the skipped line is the first"), Skipped[0], Shown[0].TextHandle);
	}
	return true;
}
