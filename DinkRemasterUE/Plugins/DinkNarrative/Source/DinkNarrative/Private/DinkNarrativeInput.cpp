// Keyboard and mouse of the narrative layer (FDinkNarrativeInputProcessor): bindings and precedence are in the header.

#include "DinkNarrativeInput.h"
#include "DinkInputBindings.h"
#include "DinkGameplay.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "Engine/Console.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"
#include "Layout/WidgetPath.h"
#include "Widgets/SViewport.h"

namespace
{
	bool IsConfirmKey(const FKey& Key)
	{
		return DinkInput::IsBound(Key, DinkInput::EAction::Confirm);
	}

	bool IsAttackKey(const FKey& Key)
	{
		return DinkInput::IsBound(Key, DinkInput::EAction::Attack);
	}

	/** 1-9 -> 0..8, 0 -> 9, anything else -> INDEX_NONE. */
	int32 DigitIndex(const FKey& Key)
	{
		static const FKey Digits[] = { EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four, EKeys::Five, EKeys::Six, EKeys::Seven, EKeys::Eight, EKeys::Nine, EKeys::Zero };
		for (int32 i = 0; i < UE_ARRAY_COUNT(Digits); ++i)
		{
			if (Key == Digits[i])
			{
				return i;
			}
		}
		return INDEX_NONE;
	}

	/**
	 * Who may skip a blocking line. While Dink is held (frozen in a cutscene, or a script waits for a button: wait_for_button)
	 * every confirm key and the left click skip, as in 1997. While he can move freely (a line spoken in passing, a cave's
	 * muttering, a shopkeeper's answer), only Space and gamepad A skip, so Enter, E, F and the click keep their own jobs
	 * (items, talk, attack). Owner's playtest decision, 15 Nov 2026.
	 */
	bool IsDinkHeld(UDinkStorySubsystem& S)
	{
		UDinkDirector* D = S.GetDirector();
		return (D && D->GetDink().bFrozen) || S.HasButtonWait();
	}

	bool IsFreeSkipKey(const FKey& Key)
	{
		return Key == EKeys::SpaceBar || Key == EKeys::Gamepad_FaceButton_Bottom;
	}

	/**
	 * ShownSerial of the newest blocking text on screen, 0 if none. Not its handle: a skipped say_stop's handle goes to the next line
	 * in the same frame (UDinkDirector::AllocateHandle), so a handle would not show that a new line appeared.
	 */
	int32 NewestBlockingText(const UDinkStorySubsystem& S)
	{
		const TArray<FDinkActiveText>& Texts = S.GetActiveTexts();
		for (int32 i = Texts.Num() - 1; i >= 0; --i)
		{
			if (Texts[i].bBlocking)
			{
				return FMath::Max(1, Texts[i].ShownSerial);
			}
		}
		return 0;
	}
}

bool FDinkNarrativeInputProcessor::IsGameInputAllowed() const
{
	const UDinkStorySubsystem* S = Story.Get();
	const UWorld* World = S ? S->GetWorld() : nullptr;
	if (!S || !S->IsReady() || !World || !World->IsGameWorld())
	{
		return false;
	}
	if (const UGameViewportClient* Viewport = World->GetGameViewport())
	{
		if (Viewport->ViewportConsole && Viewport->ViewportConsole->ConsoleState != NAME_None)
		{
			return false;
		}
	}
	return true;
}

void FDinkNarrativeInputProcessor::ObserveScreen(double Now)
{
	const UDinkStorySubsystem* S = Story.Get();
	if (!S || !S->IsReady())
	{
		return;
	}
	const FDinkMenu* Menu = S->GetActiveMenu();
	const int32 MenuInstance = Menu ? Menu->InstanceId : 0;
	if (MenuInstance != SeenMenuInstance)
	{
		SeenMenuInstance = MenuInstance;
		MenuSeenAt = Now;
	}
	const int32 Blocking = NewestBlockingText(*S);
	if (Blocking != SeenBlockingText)
	{
		SeenBlockingText = Blocking;
		BlockingTextSeenAt = Now;
	}
}

bool FDinkNarrativeInputProcessor::ClickGuarded(double SeenAt) const
{
	return MouseConfirmGuardSeconds > 0. && SeenAt >= 0. && FPlatformTime::Seconds() - SeenAt < MouseConfirmGuardSeconds;
}

void FDinkNarrativeInputProcessor::ReleaseAttack()
{
	AttackKeyDown = FKey();
	PendingReleaseAt = -1.;
	if (UDinkStorySubsystem* S = Story.Get(); S && S->IsReady())
	{
		S->GetGameplay()->InputAttackReleased();
	}
}

bool FDinkNarrativeInputProcessor::PressAttack(const FKey& Key)
{
	UDinkStorySubsystem* S = Story.Get();
	if (!S)
	{
		return false;
	}
	if (AttackKeyDown == Key)
	{
		// Still the same press: an auto-repeat whose key-up is waiting out the guard.
		PendingReleaseAt = -1.;
		return true;
	}
	if (AttackKeyDown.IsValid())
	{
		return true; // another attack input is already down
	}
	AttackKeyDown = Key;
	PendingReleaseAt = -1.;
	S->GetGameplay()->InputAttackPressed();
	return true;
}

void FDinkNarrativeInputProcessor::Tick(const float DeltaTime, FSlateApplication& SlateApp, TSharedRef<ICursor> Cursor)
{
	const double Now = FPlatformTime::Seconds();
	ObserveScreen(Now);
	UpdateRelease(Now, SlateApp.IsActive());
	NoteViewportFocus(IsViewportFocused(SlateApp));
}

TSharedPtr<SViewport> FDinkNarrativeInputProcessor::GameViewportWidget() const
{
	const UDinkStorySubsystem* S = Story.Get();
	const UWorld* World = S ? S->GetWorld() : nullptr;
	const UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
	return Viewport ? Viewport->GetGameViewportWidget() : nullptr;
}

bool FDinkNarrativeInputProcessor::IsViewportFocused(FSlateApplication& SlateApp) const
{
	const TSharedPtr<SViewport> Widget = GameViewportWidget();
	return Widget.IsValid() && SlateApp.IsActive()
		&& (Widget->HasAnyUserFocusOrFocusedDescendants() || Widget->HasMouseCapture());
}

bool FDinkNarrativeInputProcessor::IsOverGameViewport(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) const
{
	const TSharedPtr<SViewport> Widget = GameViewportWidget();
	if (!Widget.IsValid())
	{
		return false;
	}
	if (Widget->HasMouseCapture())
	{
		return true; // the camera's mouse look holds the cursor: the click goes to the viewport wherever it is
	}
	const FWidgetPath Path = SlateApp.LocateWindowUnderMouse(MouseEvent.GetScreenSpacePosition(), SlateApp.GetInteractiveTopLevelWindows(), false, MouseEvent.GetUserIndex());
	return Path.IsValid() && Path.ContainsWidget(Widget.Get());
}

void FDinkNarrativeInputProcessor::UpdateRelease(double Now, bool bAppActive)
{
	// A release that outlived the repeat guard is real; so is losing the window (no key-up will come).
	if ((PendingReleaseAt >= 0. && Now >= PendingReleaseAt) || (AttackKeyDown.IsValid() && !bAppActive))
	{
		ReleaseAttack();
	}
}

// ---- Slate entry points: game world and console checks only ----

bool FDinkNarrativeInputProcessor::HandleKeyDownEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent)
{
	return IsGameInputAllowed() && ProcessKeyDown(InKeyEvent.GetKey(), InKeyEvent.IsRepeat());
}

bool FDinkNarrativeInputProcessor::HandleKeyUpEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent)
{
	ProcessKeyUp(InKeyEvent.GetKey());
	return false;
}

bool FDinkNarrativeInputProcessor::HandleMouseButtonDownEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent)
{
	// Slate routes every click of the application here (editor panels in PIE, the click that focuses the window): only a
	// click on the focused game viewport is game input.
	if (IsGameInputAllowed() && AcceptsClick(IsOverGameViewport(SlateApp, MouseEvent)))
	{
		const UDinkStorySubsystem* S = Story.Get();
		if (S && S->IsTitleOpen())
		{
			if (MouseEvent.GetEffectingButton() == EKeys::LeftMouseButton)
			{
				ProcessTitlePointer(MouseEvent.GetScreenSpacePosition(), /*bClick*/ true);
			}
			return false;
		}
		ProcessMouseDown(MouseEvent.GetEffectingButton());
	}
	return false; // never consumed: the viewport needs the click for focus and mouse capture
}

bool FDinkNarrativeInputProcessor::HandleMouseButtonUpEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent)
{
	ProcessMouseUp(MouseEvent.GetEffectingButton());
	return false;
}

bool FDinkNarrativeInputProcessor::HandleMouseButtonDoubleClickEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent)
{
	// Slate turns the second of two quick clicks into a double-click instead of a down: it is still a press.
	if (IsGameInputAllowed() && AcceptsClick(IsOverGameViewport(SlateApp, MouseEvent)))
	{
		const UDinkStorySubsystem* S = Story.Get();
		if (S && S->IsTitleOpen())
		{
			// On the title the first click already picked the row (and may have changed the page): the second half of a
			// double-click picks nothing more.
			return false;
		}
		ProcessMouseDown(MouseEvent.GetEffectingButton());
	}
	return false;
}

bool FDinkNarrativeInputProcessor::HandleMouseMoveEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent)
{
	const UDinkStorySubsystem* S = Story.Get();
	if (S && S->IsTitleOpen() && IsGameInputAllowed() && IsOverGameViewport(SlateApp, MouseEvent))
	{
		ProcessTitlePointer(MouseEvent.GetScreenSpacePosition(), /*bClick*/ false);
	}
	return false; // the cursor still moves
}

bool FDinkNarrativeInputProcessor::ProcessTitleKey(const FKey& Key)
{
	UDinkStorySubsystem* S = Story.Get();
	if (!S || !S->IsTitleOpen())
	{
		return false;
	}
	using DinkInput::EAction;
	if (DinkInput::IsBound(Key, EAction::MenuUp))
	{
		S->MoveTitleSelection(-1);
		return true;
	}
	if (DinkInput::IsBound(Key, EAction::MenuDown))
	{
		S->MoveTitleSelection(1);
		return true;
	}
	if (Key == EKeys::Escape || Key == EKeys::BackSpace || Key == EKeys::Gamepad_FaceButton_Right)
	{
		S->TitleBack();
		return true;
	}
	if (IsConfirmKey(Key) || IsAttackKey(Key))
	{
		S->ConfirmTitle();
		return true;
	}
	if (const int32 Digit = DigitIndex(Key); Digit != INDEX_NONE)
	{
		S->ChooseTitleRow(Digit);
		return true;
	}
	// Dink's own keys do nothing on the title; anything else (the console key) passes on.
	return DinkInput::IsBound(Key, EAction::Talk) || DinkInput::IsBound(Key, EAction::Magic) || DinkInput::IsBound(Key, EAction::Map)
		|| DinkInput::IsBound(Key, EAction::Inventory) || DinkInput::IsBound(Key, EAction::MainMenu);
}

bool FDinkNarrativeInputProcessor::ProcessTitlePointer(const FVector2D& ScreenPos, bool bClick)
{
	UDinkStorySubsystem* S = Story.Get();
	if (!S || !S->IsTitleOpen())
	{
		return false;
	}
	const int32 Row = S->GetTitleScreen().RowAt(ScreenPos);
	if (Row == INDEX_NONE)
	{
		return false;
	}
	if (bClick)
	{
		S->ChooseTitleRow(Row);
	}
	else
	{
		S->HighlightTitleRow(Row); // hover moves the highlight as the arrow keys do
	}
	return true;
}

bool FDinkNarrativeInputProcessor::HandleMouseWheelOrGestureEvent(FSlateApplication& SlateApp, const FPointerEvent& InWheelEvent, const FPointerEvent* InGestureEvent)
{
	// Only consumed while a menu uses it; otherwise the wheel zooms the camera as before.
	return !InGestureEvent && IsGameInputAllowed() && IsOverGameViewport(SlateApp, InWheelEvent) && ProcessWheel(InWheelEvent.GetWheelDelta());
}

// ---- The bindings ----

void FDinkNarrativeInputProcessor::ProcessKeyUp(const FKey& Key)
{
	if (AttackKeyDown.IsValid() && Key == AttackKeyDown)
	{
		PendingReleaseAt = FPlatformTime::Seconds() + RepeatGuardSeconds;
	}
}

bool FDinkNarrativeInputProcessor::ProcessKeyDown(const FKey& Key, bool bRepeat)
{
	UDinkStorySubsystem* S = Story.Get();
	if (!S || !S->IsReady() || bRepeat)
	{
		return false;
	}
	const bool bConfirm = IsConfirmKey(Key);
	const int32 Digit = DigitIndex(Key);

	if (S->IsTitleOpen())
	{
		return ProcessTitleKey(Key);
	}
	if (S->GetShownBitmap())
	{
		// A show_bmp picture (the map): any of the six game buttons closes it (ThinkShowBmp, dink.cpp:16722-16740); the
		// script that showed it runs on. Other keys (the console key) pass.
		using DinkInput::EAction;
		if (bConfirm || IsAttackKey(Key) || DinkInput::IsBound(Key, EAction::Talk) || DinkInput::IsBound(Key, EAction::Magic)
			|| DinkInput::IsBound(Key, EAction::Inventory) || DinkInput::IsBound(Key, EAction::MainMenu) || DinkInput::IsBound(Key, EAction::Map))
		{
			S->SkipDialogue();
			return true;
		}
		return false;
	}
	if (S->IsInventoryOpen())
	{
		// The item screen (dink.cpp:16409-16636): cursor keys, the attack button arms, Enter closes.
		if (DinkInput::IsBound(Key, DinkInput::EAction::Inventory) || Key == EKeys::Escape || Key == EKeys::Gamepad_FaceButton_Right)
		{
			S->CloseInventory();
			return true;
		}
		if (Key == EKeys::Left || Key == EKeys::A || Key == EKeys::Gamepad_DPad_Left || Key == EKeys::Gamepad_LeftStick_Left)
		{
			S->MoveInventoryCursor(-1, 0);
			return true;
		}
		if (Key == EKeys::Right || Key == EKeys::D || Key == EKeys::Gamepad_DPad_Right || Key == EKeys::Gamepad_LeftStick_Right)
		{
			S->MoveInventoryCursor(1, 0);
			return true;
		}
		if (DinkInput::IsBound(Key, DinkInput::EAction::MenuUp))
		{
			S->MoveInventoryCursor(0, -1);
			return true;
		}
		if (DinkInput::IsBound(Key, DinkInput::EAction::MenuDown))
		{
			S->MoveInventoryCursor(0, 1);
			return true;
		}
		if (IsAttackKey(Key) || Key == EKeys::SpaceBar)
		{
			S->ArmInventorySelection();
			return true;
		}
		if (Digit != INDEX_NONE)
		{
			S->QuickArmItemSlot(Digit + 1);
			return true;
		}
		// Nothing else acts while the game is paused.
		return DinkInput::IsBound(Key, DinkInput::EAction::Talk) || DinkInput::IsBound(Key, DinkInput::EAction::Magic) || DinkInput::IsBound(Key, DinkInput::EAction::MainMenu) || DinkInput::IsBound(Key, DinkInput::EAction::Map);
	}

	if (S->GetActiveMenu())
	{
		if (DinkInput::IsBound(Key, DinkInput::EAction::MenuUp))
		{
			S->MoveMenuSelection(-1);
			return true;
		}
		if (DinkInput::IsBound(Key, DinkInput::EAction::MenuDown))
		{
			S->MoveMenuSelection(1);
			return true;
		}
		if (bConfirm)
		{
			S->ChooseSelected();
			return true;
		}
		// The attack button chooses too (1997: button 1 picks in the talk menu, dink.cpp:16153; escape.c's help says
		// "Ctrl = Attack/choose"), not within the click guard of the menu appearing (a fight's level-up menu, lraise.c).
		if (IsAttackKey(Key))
		{
			if (!ClickGuarded(MenuSeenAt))
			{
				S->ChooseSelected();
			}
			return true;
		}
		if (Digit != INDEX_NONE && Digit < 9)
		{
			S->Choose(Digit);
			return true;
		}
		return false;
	}
	if (bConfirm && (IsFreeSkipKey(Key) || IsDinkHeld(*S)) && S->SkipDialogue())
	{
		return true;
	}
	if (DinkInput::IsBound(Key, DinkInput::EAction::Inventory))
	{
		// The original's Enter (button 4) opens the item screen from Dink's brain (dink.cpp:14946-14960).
		return S->OpenInventory();
	}
	if (Digit != INDEX_NONE)
	{
		return S->QuickArmItemSlot(Digit + 1);
	}
	if (DinkInput::IsBound(Key, DinkInput::EAction::Talk))
	{
		const UWorld* World = S->GetWorld();
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		return S->TryTalk(PC ? PC->GetPawn() : nullptr);
	}
	// Shift holds the third-person walk gait; Q remains the spell control.
	if (IsAttackKey(Key))
	{
		return PressAttack(Key);
	}
	if (DinkInput::IsBound(Key, DinkInput::EAction::Magic))
	{
		return S->GetGameplay()->PlayerCastMagic();
	}
	// The original's script buttons (human_brain, dink.cpp:14871-14875, 14985-14993): Esc / Start the main menu, M / Back the map.
	if (DinkInput::IsBound(Key, DinkInput::EAction::MainMenu))
	{
		return S->RunPlayerButton(5);
	}
	if (DinkInput::IsBound(Key, DinkInput::EAction::Map))
	{
		return S->RunPlayerButton(6);
	}
	return false;
}

bool FDinkNarrativeInputProcessor::ProcessMouseDown(const FKey& Button)
{
	UDinkStorySubsystem* S = Story.Get();
	if (!S || !S->IsReady() || Button != EKeys::LeftMouseButton)
	{
		return false;
	}
	ObserveScreen(FPlatformTime::Seconds());
	// Never an attack while the title is up, nor from the rest of the click (or double-click) that closed it.
	if (S->IsTitleOpen() || ClickGuarded(S->GetTitleScreen().ClosedAt))
	{
		return S->IsTitleOpen();
	}
	if (S->IsInventoryOpen())
	{
		S->ArmInventorySelection(); // the item screen's attack button
		return true;
	}
	// A left click confirms what is on screen as Enter does; only when nothing waits for it is it the attack.
	if (S->GetActiveMenu())
	{
		return !ClickGuarded(MenuSeenAt) && S->ChooseSelected();
	}
	// The click skips only while Dink is held (a cutscene); while he moves freely it is the attack (IsDinkHeld).
	if (IsDinkHeld(*S))
	{
		if (NewestBlockingText(*S) != 0 && ClickGuarded(BlockingTextSeenAt))
		{
			return false;
		}
		if (S->SkipDialogue())
		{
			return true;
		}
	}
	return PressAttack(Button);
}

void FDinkNarrativeInputProcessor::ProcessMouseUp(const FKey& Button)
{
	// No OS auto-repeat on mouse buttons: the release is real at once (it lets a drawn bow go).
	if (AttackKeyDown.IsValid() && Button == AttackKeyDown)
	{
		ReleaseAttack();
	}
}

bool FDinkNarrativeInputProcessor::ProcessWheel(float Delta)
{
	UDinkStorySubsystem* S = Story.Get();
	if (!S || !S->IsReady() || FMath::IsNearlyZero(Delta))
	{
		return false;
	}
	if (S->IsTitleOpen())
	{
		S->MoveTitleSelection(Delta > 0.f ? -1 : 1);
		return true;
	}
	if (S->IsInventoryOpen())
	{
		S->MoveInventoryCursor(0, Delta > 0.f ? -1 : 1);
		return true;
	}
	if (S->GetActiveMenu())
	{
		S->MoveMenuSelection(Delta > 0.f ? -1 : 1);
		return true;
	}
	return false;
}
