// Dink.Narrative.Title.*: the remaster's title screen (FDinkTitleScreen, DinkTitleMenu.cpp) on the converted story without a
// world: which rows there are and which do something, the keys, the pages, New Game leaving the newgame start to run as
// before, Quit, and that automation never shows it (so the probe and every other test start straight into the game).

#include "DinkTestHelpers.h"
#include "DinkFactSubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "DinkDirector.h"
#include "DinkNarrativeInput.h"
#include "DinkStorySubsystem.h"
#include "InputCoreTypes.h"
#include "Misc/AutomationTest.h"

namespace DinkTitleTest
{
	struct FEnv
	{
		UDinkStorySubsystem* Story = nullptr;
		UDinkFactSubsystem* Facts = nullptr;
		TSharedPtr<FDinkNarrativeInputProcessor> Input;
	};

	FEnv Make(FAutomationTestBase& Test)
	{
		FEnv E;
		UGameInstance* GI = DinkTest::MakeOuterGameInstance();
		UDinkFactSubsystem* Facts = NewObject<UDinkFactSubsystem>(GI);
		FString Error;
		Test.TestTrue(TEXT("facts table loads"), Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
		UDinkWorldStateSubsystem* World = NewObject<UDinkWorldStateSubsystem>(GI);
		E.Story = NewObject<UDinkStorySubsystem>(GI);
		Test.TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), E.Story->SetupStandalone(Facts, World, &Error));
		E.Story->ResetRuntime();
		E.Story->bNewGamePending = true;
		E.Facts = Facts;
		E.Input = MakeShared<FDinkNarrativeInputProcessor>(E.Story);
		E.Input->MouseConfirmGuardSeconds = 0.;
		return E;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkTitleNeverUnderAutomationTest, "Dink.Narrative.Title.NeverUnderAutomation",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDinkTitleNeverUnderAutomationTest::RunTest(const FString& Parameters)
{
	DinkTitleTest::FEnv E = DinkTitleTest::Make(*this);
	if (!E.Story->IsReady())
	{
		return false;
	}
	TestFalse(TEXT("no world and automation: the title is not wanted"), E.Story->ShouldShowTitle());
	TestFalse(TEXT("nothing opened it"), E.Story->IsTitleOpen());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkTitleRowsAndPagesTest, "Dink.Narrative.Title.RowsAndPages",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDinkTitleRowsAndPagesTest::RunTest(const FString& Parameters)
{
	DinkTitleTest::FEnv E = DinkTitleTest::Make(*this);
	UDinkStorySubsystem* S = E.Story;
	if (!S->IsReady())
	{
		return false;
	}
	TestTrue(TEXT("opens without a world (rules only)"), S->OpenTitle());
	TestTrue(TEXT("open"), S->IsTitleOpen());
	const TArray<FString> Main = S->GetTitleRows();
	TestEqual(TEXT("main page rows"), FString::Join(Main, TEXT("|")), FString(TEXT("New Game|Continue|Controls|Quit")));
	const bool bSaves = S->GetTitleScreen().AnySave();
	TestEqual(TEXT("ten slots read"), S->GetTitleScreen().Slots.Num(), 10);
	TestEqual(TEXT("Continue only with a save"), S->IsTitleRowEnabled(1), bSaves);
	TestEqual(TEXT("starts on Continue when there is a save, else New Game"), S->GetTitleScreen().Selected, bSaves ? 1 : 0);

	// Keys: Down from New Game skips a disabled Continue; Up wraps to Quit.
	S->HighlightTitleRow(0);
	TestEqual(TEXT("hover highlights New Game"), S->GetTitleScreen().Selected, 0);
	TestTrue(TEXT("Down is the title's"), E.Input->ProcessKeyDown(EKeys::Down));
	TestEqual(TEXT("Down: Continue, or Controls when there is no save"), S->GetTitleScreen().Selected, bSaves ? 1 : 2);
	S->HighlightTitleRow(0);
	TestTrue(TEXT("W is the title's"), E.Input->ProcessKeyDown(EKeys::W));
	TestEqual(TEXT("Up from the first row wraps to Quit"), S->GetTitleScreen().Selected, 3);
	TestTrue(TEXT("attack keys do not reach Dink"), E.Input->ProcessKeyDown(EKeys::Q));
	TestTrue(TEXT("Esc on the main page is consumed and does nothing"), E.Input->ProcessKeyDown(EKeys::Escape));
	TestEqual(TEXT("still the main page"), (int32)S->GetTitleScreen().Page, (int32)EDinkTitlePage::Main);
	TestFalse(TEXT("the console key passes"), E.Input->ProcessKeyDown(EKeys::Tilde));
	if (!bSaves)
	{
		TestFalse(TEXT("a disabled row does nothing"), S->ChooseTitleRow(1));
		TestEqual(TEXT("still the main page after a disabled row"), (int32)S->GetTitleScreen().Page, (int32)EDinkTitlePage::Main);
	}

	// Controls page and back.
	TestTrue(TEXT("3 picks Controls"), E.Input->ProcessKeyDown(EKeys::Three));
	TestEqual(TEXT("controls page"), (int32)S->GetTitleScreen().Page, (int32)EDinkTitlePage::Controls);
	TestEqual(TEXT("controls page has Back"), FString::Join(S->GetTitleRows(), TEXT("|")), FString(TEXT("Back")));
	TestTrue(TEXT("Esc goes back"), E.Input->ProcessKeyDown(EKeys::Escape));
	TestEqual(TEXT("main page again"), (int32)S->GetTitleScreen().Page, (int32)EDinkTitlePage::Main);
	TestEqual(TEXT("back on Controls"), S->GetTitleScreen().Selected, 2);

	// Continue page (when there is a save): ten slot rows and Back; empty slots do nothing.
	if (bSaves)
	{
		TestTrue(TEXT("Continue"), S->ChooseTitleRow(1));
		TestEqual(TEXT("continue page"), (int32)S->GetTitleScreen().Page, (int32)EDinkTitlePage::Continue);
		const TArray<FString> Slots = S->GetTitleRows();
		TestEqual(TEXT("ten slots and Back"), Slots.Num(), 11);
		for (int32 i = 0; i < 10; ++i)
		{
			TestTrue(TEXT("slot lines start like the original's savegameinfo"), Slots[i].StartsWith(FString::Printf(TEXT("Slot %d - "), i + 1)));
			TestEqual(TEXT("an empty slot does nothing"), S->IsTitleRowEnabled(i), S->GetTitleScreen().Slots[i].bExists);
		}
		TestTrue(TEXT("Back"), S->ChooseTitleRow(10));
	}

	// Quit runs the hook (the game quits the application).
	int32 Quits = 0;
	S->OnTitleQuit = [&Quits]() { ++Quits; };
	TestTrue(TEXT("Quit"), S->ChooseTitleRow(3));
	TestEqual(TEXT("quit once"), Quits, 1);
	TestTrue(TEXT("the title stays up until the application goes"), S->IsTitleOpen());

	// New Game: the title closes and the newgame start is left to run as with no title.
	S->HighlightTitleRow(0);
	TestTrue(TEXT("Enter picks New Game"), E.Input->ProcessKeyDown(EKeys::Enter));
	TestFalse(TEXT("closed"), S->IsTitleOpen());
	TestTrue(TEXT("the newgame start is still pending (PollScreenChange runs it)"), S->bNewGamePending);
	TestFalse(TEXT("keys are Dink's again: Down is not consumed with no menu"), E.Input->ProcessKeyDown(EKeys::Down));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkTitleBlocksTheStoryTest, "Dink.Narrative.Title.BlocksTheStory",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDinkTitleBlocksTheStoryTest::RunTest(const FString& Parameters)
{
	DinkTitleTest::FEnv E = DinkTitleTest::Make(*this);
	UDinkStorySubsystem* S = E.Story;
	if (!S->IsReady())
	{
		return false;
	}
	S->OpenTitle();
	const double Before = S->GetNowMs();
	for (int32 i = 0; i < 120; ++i)
	{
		S->Advance(1.0 / 60.0);
	}
	TestEqual(TEXT("no story time passes while the title is up"), S->GetNowMs(), Before);
	TestTrue(TEXT("the newgame start waits"), S->bNewGamePending);
	TestFalse(TEXT("no inventory over the title"), S->OpenInventory());
	S->ChooseTitleRow(0);
	S->Advance(1.0 / 60.0);
	TestTrue(TEXT("story time runs after New Game"), S->GetNowMs() > Before);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkShowBmpMapTest, "Dink.Narrative.Presentation.ShowBmpMap",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDinkShowBmpMapTest::RunTest(const FString& Parameters)
{
	// button6.c (the map key): without the map item Dink says so; with it, show_bmp("tiles\\map1.bmp", 1, 0) shows the map until
	// one of the game buttons is pressed (ThinkShowBmp), then the script runs on to kill_this_task.
	DinkTitleTest::FEnv E = DinkTitleTest::Make(*this);
	UDinkStorySubsystem* S = E.Story;
	if (!S->IsReady())
	{
		return false;
	}
	S->bNewGamePending = false;
	TestTrue(TEXT("button6 runs"), S->StartProcedure(TEXT("button6"), TEXT("main"), 1) > 0);
	S->RunUntilIdle();
	TestNull(TEXT("no map item: no picture"), S->GetShownBitmap());

	E.Facts->SetFact(TEXT("s2-map"), 1);
	const int32 Id = S->StartProcedure(TEXT("button6"), TEXT("main"), 1);
	TestTrue(TEXT("button6 runs again"), Id > 0);
	S->RunUntilIdle();
	const FDinkShownBitmap* Bitmap = S->GetShownBitmap();
	TestNotNull(TEXT("the map is on screen while the script waits"), Bitmap);
	if (Bitmap)
	{
		TestTrue(TEXT("it is the world map"), Bitmap->IsWorldMap());
		TestTrue(TEXT("the file the script named"), Bitmap->Name.Contains(TEXT("map1.bmp"), ESearchCase::IgnoreCase));
	}
	TestFalse(TEXT("the console key passes"), E.Input->ProcessKeyDown(EKeys::Tilde));
	TestNotNull(TEXT("still up"), S->GetShownBitmap());
	const double Before = S->GetNowMs();
	for (int32 i = 0; i < 60; ++i)
	{
		S->Advance(1.0 / 60.0);
	}
	TestEqual(TEXT("the game stops behind the map (no story time)"), S->GetNowMs(), Before);
	TestNotNull(TEXT("and the map stays up"), S->GetShownBitmap());
	TestTrue(TEXT("M (the map button) closes it"), E.Input->ProcessKeyDown(EKeys::M));
	S->RunUntilIdle();
	TestNull(TEXT("closed"), S->GetShownBitmap());
	TestNull(TEXT("the script ran on and ended"), S->FindInstance(Id) && S->FindInstance(Id)->IsAlive() ? S->FindInstance(Id) : nullptr);
	return true;
}

namespace DinkTitleTest
{
	int32 BlockingTexts(const UDinkStorySubsystem* S)
	{
		int32 N = 0;
		for (const FDinkActiveText& T : S->GetActiveTexts())
		{
			N += T.bBlocking ? 1 : 0;
		}
		return N;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkShowBmpMapKeepsLineTest, "Dink.Narrative.Presentation.ShowBmpMapKeepsLine",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDinkShowBmpMapKeepsLineTest::RunTest(const FString& Parameters)
{
	// ThinkShowBmp (dink.cpp:16722-16740): the button that closes the map runs on only the script that showed it. A say_stop
	// line that was up when the map opened (Dink is free while an NPC talks, so M opens the map) keeps its text, its voice
	// and its script's wait; closing the map by key or by click must not skip it (review R8, 19 Nov 2026).
	DinkTitleTest::FEnv E = DinkTitleTest::Make(*this);
	UDinkStorySubsystem* S = E.Story;
	if (!S->IsReady())
	{
		return false;
	}
	S->bNewGamePending = false;
	const int32 Mom = S->GetDirector()->CreateVirtualSprite(1, 300, 200);
	const int32 MomTalk = S->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), Mom);
	S->Advance(0.0);
	TestNotNull(TEXT("Mother's talk menu"), S->GetActiveMenu());
	S->Choose(1); // 'Ask about your father': wait(200), then say_stop lines (s1-h1-m.c:109-115)
	S->Advance(0.0);
	S->Advance(0.21);
	const FDinkScriptInstance* Talk = S->FindInstance(MomTalk);
	TestTrue(TEXT("Mother's script waits on a say_stop line"), Talk && Talk->State == EDinkInstanceState::Blocked && Talk->Block == EDinkBlock::Say);
	TestEqual(TEXT("one blocking line on screen"), DinkTitleTest::BlockingTexts(S), 1);

	E.Facts->SetFact(TEXT("s2-map"), 1);
	for (const bool bClick : { false, true })
	{
		const int32 Map = S->StartProcedure(TEXT("button6"), TEXT("main"), 1);
		S->RunUntilIdle();
		TestNotNull(TEXT("the map is up over the line"), S->GetShownBitmap());
		const bool bUsed = bClick ? E.Input->ProcessMouseDown(EKeys::LeftMouseButton) : E.Input->ProcessKeyDown(EKeys::M);
		TestTrue(bClick ? TEXT("a click closes the map") : TEXT("M closes the map"), bUsed);
		TestNull(TEXT("the map is closed"), S->GetShownBitmap());
		TestEqual(TEXT("the say_stop line is still on screen"), DinkTitleTest::BlockingTexts(S), 1);
		Talk = S->FindInstance(MomTalk);
		TestTrue(TEXT("Mother's script still waits on its line"), Talk && Talk->State == EDinkInstanceState::Blocked && Talk->Block == EDinkBlock::Say);
		S->RunUntilIdle();
		TestTrue(TEXT("button6 ran on and ended"), !S->FindInstance(Map) || !S->FindInstance(Map)->IsAlive());
		if (bClick)
		{
			E.Input->ProcessMouseUp(EKeys::LeftMouseButton);
		}
		else
		{
			E.Input->ProcessKeyUp(EKeys::M);
		}
	}
	TestTrue(TEXT("the line is skipped by the skip key as before"), S->SkipDialogue());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAttackKeyMenuGuardTest, "Dink.Narrative.Presentation.AttackKeyMenuGuard",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDinkAttackKeyMenuGuardTest::RunTest(const FString& Parameters)
{
	// The attack key chooses in a menu, but not within MouseConfirmGuardSeconds of the menu appearing (a fight's level-up
	// menu, lraise.c, opens while the player mashes attack). Slate delivers keys before the world ticks, so the key path must
	// observe the screen itself; before review R7 (19 Nov 2026) a key in the menu's first frame chose at once.
	DinkTitleTest::FEnv E = DinkTitleTest::Make(*this);
	UDinkStorySubsystem* S = E.Story;
	if (!S->IsReady())
	{
		return false;
	}
	S->bNewGamePending = false;
	TestTrue(TEXT("escape.c runs"), S->StartProcedure(TEXT("escape"), TEXT("main"), 1000) > 0);
	S->RunUntilIdle();
	const FDinkMenu* M = S->GetActiveMenu();
	TestTrue(TEXT("the main menu is up (no input tick has seen it yet)"), M && M->Choices.Num() == 6);
	E.Input->MouseConfirmGuardSeconds = 30.; // a wide guard: the test cannot be late for it
	TestTrue(TEXT("F in the menu's first frame is used"), E.Input->ProcessKeyDown(EKeys::F));
	E.Input->ProcessKeyUp(EKeys::F);
	S->RunUntilIdle();
	M = S->GetActiveMenu();
	TestTrue(TEXT("but chose nothing: still the main menu"), M && M->Choices.Num() == 6);
	TestTrue(TEXT("Enter is not guarded"), E.Input->ProcessKeyDown(EKeys::Enter));
	E.Input->ProcessKeyUp(EKeys::Enter);
	S->RunUntilIdle();
	M = S->GetActiveMenu();
	TestTrue(TEXT("Enter chose the first option: the ten slots and Nevermind"), M && M->Choices.Num() == 11);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkEscapeMenuControlsTest, "Dink.Narrative.Presentation.EscapeMenuControls",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDinkEscapeMenuControlsTest::RunTest(const FString& Parameters)
{
	// escape.c (Esc / Start): the attack button chooses in a menu as in 1997 ("Ctrl = Attack/choose"), and "View/change
	// gamepad buttons" names the pad key behind each 1997 button instead of "Button N".
	DinkTitleTest::FEnv E = DinkTitleTest::Make(*this);
	UDinkStorySubsystem* S = E.Story;
	if (!S->IsReady())
	{
		return false;
	}
	S->bNewGamePending = false;
	TestTrue(TEXT("escape.c runs"), S->StartProcedure(TEXT("escape"), TEXT("main"), 1000) > 0);
	S->RunUntilIdle();
	const FDinkMenu* M = S->GetActiveMenu();
	TestNotNull(TEXT("the main menu is up"), M);
	if (!M)
	{
		return false;
	}
	TestEqual(TEXT("six options"), M->Choices.Num(), 6);
	E.Input->MouseConfirmGuardSeconds = 0.; // the 0.3 s guard after a menu appears: Dink.Narrative.Presentation.AttackKeyMenuGuard
	TestTrue(TEXT("F is used by the menu"), E.Input->ProcessKeyDown(EKeys::F));
	E.Input->ProcessKeyUp(EKeys::F);
	S->RunUntilIdle();
	M = S->GetActiveMenu();
	TestTrue(TEXT("F chose the first option: the ten slots and Nevermind"), M && M->Choices.Num() == 11);
	if (!M)
	{
		return false;
	}
	TestTrue(TEXT("Nevermind"), S->Choose(10));
	S->RunUntilIdle();
	M = S->GetActiveMenu();
	TestTrue(TEXT("back on the main menu"), M && M->Choices.Num() == 6);
	TestTrue(TEXT("View/change gamepad buttons"), S->Choose(5));
	S->RunUntilIdle();
	M = S->GetActiveMenu();
	TestTrue(TEXT("ten buttons and Nevermind"), M && M->Choices.Num() == 11);
	if (M && M->Choices.Num() == 11)
	{
		TestTrue(FString::Printf(TEXT("button 1 names the pad key (%s)"), *M->Choices[0].Text), M->Choices[0].Text.Contains(TEXT("X / RT - Attack")));
		TestTrue(FString::Printf(TEXT("button 4 is the item screen on RB (%s)"), *M->Choices[3].Text), M->Choices[3].Text.Contains(TEXT("RB - Item Screen")));
	}
	return true;
}
