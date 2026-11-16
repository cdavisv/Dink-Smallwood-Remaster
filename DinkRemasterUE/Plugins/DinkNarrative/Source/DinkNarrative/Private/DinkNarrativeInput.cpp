// Keyboard and mouse of the narrative layer (FDinkNarrativeInputProcessor): bindings and precedence are in the header.

#include "DinkNarrativeInput.h"
#include "DinkInputBindings.h"
#include "DinkGameplay.h"
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
		ProcessMouseDown(MouseEvent.GetEffectingButton());
	}
	return false;
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

	if (S->IsInventoryOpen())
	{
		// The item screen (dink.cpp:16409-16636): cursor keys, the attack button arms, Enter closes.
		if (DinkInput::IsBound(Key, DinkInput::EAction::Inventory) || Key == EKeys::Escape || Key == EKeys::Gamepad_FaceButton_Right)
		{
			S->CloseInventory();
			return true;
		}
		if (Key == EKeys::Left || Key == EKeys::A || Key == EKeys::Gamepad_DPad_Left)
		{
			S->MoveInventoryCursor(-1, 0);
			return true;
		}
		if (Key == EKeys::Right || Key == EKeys::D || Key == EKeys::Gamepad_DPad_Right)
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
		if (Digit != INDEX_NONE && Digit < 9)
		{
			S->Choose(Digit);
			return true;
		}
		return false;
	}
	if (bConfirm && S->SkipDialogue())
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
	if (NewestBlockingText(*S) != 0 && ClickGuarded(BlockingTextSeenAt))
	{
		return false;
	}
	if (S->SkipDialogue())
	{
		return true;
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
