// Keyboard and mouse of the narrative layer (FDinkNarrativeInputProcessor): bindings and precedence are in the header.

#include "DinkNarrativeInput.h"
#include "DinkGameplay.h"
#include "DinkStorySubsystem.h"
#include "Engine/Console.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"

namespace
{
	bool IsConfirmKey(const FKey& Key)
	{
		return Key == EKeys::Enter || Key == EKeys::SpaceBar || Key == EKeys::E;
	}

	bool IsAttackKey(const FKey& Key)
	{
		return Key == EKeys::F || Key == EKeys::LeftControl;
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

	/** Handle of the newest blocking text on screen, 0 if none. */
	int32 NewestBlockingText(const UDinkStorySubsystem& S)
	{
		const TArray<FDinkActiveText>& Texts = S.GetActiveTexts();
		for (int32 i = Texts.Num() - 1; i >= 0; --i)
		{
			if (Texts[i].bBlocking)
			{
				return Texts[i].Handle;
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
	if (IsGameInputAllowed())
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
	if (IsGameInputAllowed())
	{
		ProcessMouseDown(MouseEvent.GetEffectingButton());
	}
	return false;
}

bool FDinkNarrativeInputProcessor::HandleMouseWheelOrGestureEvent(FSlateApplication& SlateApp, const FPointerEvent& InWheelEvent, const FPointerEvent* InGestureEvent)
{
	// Only consumed while a menu uses it; otherwise the wheel zooms the camera as before.
	return !InGestureEvent && IsGameInputAllowed() && ProcessWheel(InWheelEvent.GetWheelDelta());
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

	if (S->GetActiveMenu())
	{
		if (Key == EKeys::Up || Key == EKeys::W)
		{
			S->MoveMenuSelection(-1);
			return true;
		}
		if (Key == EKeys::Down || Key == EKeys::S)
		{
			S->MoveMenuSelection(1);
			return true;
		}
		if (bConfirm)
		{
			S->ChooseSelected();
			return true;
		}
		const int32 Digit = DigitIndex(Key);
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
	if (Key == EKeys::E)
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
	if (Key == EKeys::Q)
	{
		return S->GetGameplay()->PlayerCastMagic();
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
	// A left click confirms what is on screen exactly as Enter does; only when nothing waits for it is it the attack.
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
	if (S->GetActiveMenu())
	{
		S->MoveMenuSelection(Delta > 0.f ? -1 : 1);
		return true;
	}
	return false;
}
