// Dink.Input.*: the narrative layer's controls (DinkInput::Bindings, used by FDinkNarrativeInputProcessor) cover every action of the
// original that the remaster has, on the keyboard and on a standard gamepad, without taking a button the character's own mappings use.

#include "DinkTestHelpers.h"
#include "DinkInputBindings.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkInputGamepadTest, "Dink.Input.GamepadAndKeyboardBindings", DINK_TEST_FLAGS)
bool FDinkInputGamepadTest::RunTest(const FString& Parameters)
{
	using DinkInput::EAction;
	using DinkInput::IsBound;
	const TCHAR* Names[] = { TEXT("confirm"), TEXT("menu up"), TEXT("menu down"), TEXT("talk"), TEXT("attack"), TEXT("magic"), TEXT("main menu"), TEXT("map") };
	for (int32 A = 0; A <= static_cast<int32>(EAction::Map); ++A)
	{
		bool bKeyboard = false, bGamepad = false;
		for (const TPair<FKey, EAction>& B : DinkInput::Bindings())
		{
			if (static_cast<int32>(B.Value) == A)
			{
				(B.Key.IsGamepadKey() ? bGamepad : bKeyboard) = true;
			}
		}
		TestTrue(FString::Printf(TEXT("%s has a keyboard key"), Names[A]), bKeyboard);
		TestTrue(FString::Printf(TEXT("%s has a gamepad button"), Names[A]), bGamepad);
	}
	// The keyboard keys of the 14 Nov 2026 build stay as they were.
	TestTrue(TEXT("F and Left Ctrl attack"), IsBound(EKeys::F, EAction::Attack) && IsBound(EKeys::LeftControl, EAction::Attack));
	TestTrue(TEXT("E talks"), IsBound(EKeys::E, EAction::Talk));
	TestTrue(TEXT("Q casts"), IsBound(EKeys::Q, EAction::Magic));
	TestTrue(TEXT("Enter, Space and E pick"), IsBound(EKeys::Enter, EAction::Confirm) && IsBound(EKeys::SpaceBar, EAction::Confirm) && IsBound(EKeys::E, EAction::Confirm));
	// The gamepad layout.
	TestTrue(TEXT("X attacks (held: the bow draws)"), IsBound(EKeys::Gamepad_FaceButton_Left, EAction::Attack));
	TestTrue(TEXT("the right trigger attacks too"), IsBound(EKeys::Gamepad_RightTrigger, EAction::Attack));
	TestTrue(TEXT("B talks"), IsBound(EKeys::Gamepad_FaceButton_Right, EAction::Talk));
	TestTrue(TEXT("Y casts"), IsBound(EKeys::Gamepad_FaceButton_Top, EAction::Magic));
	TestTrue(TEXT("A picks and skips"), IsBound(EKeys::Gamepad_FaceButton_Bottom, EAction::Confirm));
	TestTrue(TEXT("Start opens the main menu (escape.c), Esc on the keyboard"), IsBound(EKeys::Gamepad_Special_Right, EAction::MainMenu) && IsBound(EKeys::Escape, EAction::MainMenu));
	TestTrue(TEXT("Back shows the map (button6.c), M on the keyboard"), IsBound(EKeys::Gamepad_Special_Left, EAction::Map) && IsBound(EKeys::M, EAction::Map));
	TestTrue(TEXT("the d-pad moves a menu's highlight"), IsBound(EKeys::Gamepad_DPad_Up, EAction::MenuUp) && IsBound(EKeys::Gamepad_DPad_Down, EAction::MenuDown));
	// The character's own gamepad mappings (ADinkGreyboxCharacter: run on the left shoulder, jump on A) are never a talk, attack or magic
	// button: the pre-processor would eat them before Enhanced Input sees them.
	for (const FKey& Own : { EKeys::Gamepad_LeftShoulder, EKeys::Gamepad_FaceButton_Bottom })
	{
		for (const EAction A : { EAction::Talk, EAction::Attack, EAction::Magic, EAction::MainMenu, EAction::Map })
		{
			TestFalse(FString::Printf(TEXT("%s is not bound to %s"), *Own.ToString(), Names[static_cast<int32>(A)]), IsBound(Own, A));
		}
	}
	// One gamepad button, one world action.
	for (const TPair<FKey, EAction>& B : DinkInput::Bindings())
	{
		if (!B.Key.IsGamepadKey() || B.Value == EAction::Confirm || B.Value == EAction::MenuUp || B.Value == EAction::MenuDown)
		{
			continue;
		}
		int32 WorldActions = 0;
		for (const EAction A : { EAction::Talk, EAction::Attack, EAction::Magic, EAction::MainMenu, EAction::Map })
		{
			WorldActions += IsBound(B.Key, A) ? 1 : 0;
		}
		TestEqual(FString::Printf(TEXT("%s has one world action"), *B.Key.ToString()), WorldActions, 1);
	}
	return true;
}

// Esc / Start and M / Back run the original's button scripts as human_brain does (dink.cpp:14871-14875, 14985-14993; not while frozen,
// in a menu or drawing the bow, 14740-14766): escape.c opens its main menu, button6.c says Dink has no map yet.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkInputButtonScriptsTest, "Dink.Input.MainMenuAndMapButtons", DINK_TEST_FLAGS)
bool FDinkInputButtonScriptsTest::RunTest(const FString& Parameters)
{
	UGameInstance* GI = DinkTest::MakeOuterGameInstance();
	UDinkFactSubsystem* Facts = NewObject<UDinkFactSubsystem>(GI);
	FString Error;
	TestTrue(TEXT("facts table loads"), Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
	UDinkWorldStateSubsystem* World = NewObject<UDinkWorldStateSubsystem>(GI);
	UDinkStorySubsystem* Story = NewObject<UDinkStorySubsystem>(GI);
	if (!TestTrue(TEXT("story loads"), Story->SetupStandalone(Facts, World, &Error)))
	{
		return false;
	}
	Story->ResetRuntime();
	Story->bInstantMode = true;
	Story->GetDirector()->SetFrozen(1, true);
	TestFalse(TEXT("frozen: Esc does nothing"), Story->RunPlayerButton(5));
	Story->GetDirector()->SetFrozen(1, false);
	TestTrue(TEXT("Esc runs escape.c main"), Story->RunPlayerButton(5));
	Story->RunUntilIdle();
	const FDinkMenu* Menu = Story->GetActiveMenu();
	if (TestNotNull(TEXT("its main menu is open"), Menu))
	{
		TestTrue(TEXT("with the original's first choice"), Menu->Choices.Num() > 0 && Menu->Choices[0].Text.Contains(TEXT("Load a previously saved game")));
		TestFalse(TEXT("a second Esc while the menu is open does nothing"), Story->RunPlayerButton(5));
		Story->Choose(Menu->Choices.Num() >= 5 ? 4 : Menu->Choices.Num() - 1); // "Continue"
		Story->RunUntilIdle();
	}
	TestTrue(TEXT("M runs button6.c main"), Story->RunPlayerButton(6));
	Story->RunUntilIdle();
	bool bSaid = false;
	for (const FDinkNarrativeEvent& E : Story->Events)
	{
		bSaid |= E.Kind == TEXT("say") && E.Text.Contains(TEXT("I don't own a map yet."));
	}
	TestTrue(TEXT("without a map: \"I don't own a map yet.\""), bSaid);
	return true;
}
