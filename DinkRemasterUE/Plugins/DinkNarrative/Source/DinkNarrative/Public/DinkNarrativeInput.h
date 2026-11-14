#pragma once

#include "CoreMinimal.h"
#include "InputCoreTypes.h"
#include "Framework/Application/IInputProcessor.h"

class UDinkStorySubsystem;

/**
 * Keyboard and mouse for the narrative layer, as a Slate input pre-processor so it needs no input assets.
 *
 * Bindings (14 Nov 2026, owner playtest):
 *   E                talk to the nearest scripted placement in front of the player (DinkC `talk`)
 *   F / Left Ctrl /  attack: the armed item's `use` (fists, sword, pig feed...; the original's Ctrl). One attack per press,
 *   left click       however long the key is held (UDinkGameplay::InputAttackPressed); the release lets a drawn bow go.
 *                    A key down that follows an up of the same key within RepeatGuardSeconds is an OS auto-repeat that
 *                    was not flagged as one (X11 sends release+press pairs) and counts as still held. A fast second click
 *                    arrives from Slate as a double-click: it is a press like any other.
 *   Q                cast the armed spell when charged (the original's Shift)
 *
 * Precedence, first match wins (the console is never touched: nothing acts while it is open):
 *   1. Menu (choice):    Up/Down, W/S or the mouse wheel move the highlight; Enter, Space, E or left click pick it;
 *                        1-9 pick directly.
 *   2. Blocking text or wait_for_button: Enter, Space, E or left click skip it (the original's skip).
 *   3. Otherwise:        E talks; F / Ctrl / left click attack; Q casts.
 * Mouse buttons are never consumed: the click still reaches the viewport, which needs it for focus and mouse capture
 * (the camera's mouse look). A left click on a menu or a skippable line within MouseConfirmGuardSeconds of it appearing
 * is ignored, so a player hammering the attack button does not pick the first option by accident.
 *
 * The Slate handlers only check that a game world is running and the console is closed, then call the Process*
 * functions, which tests drive directly (they need no world).
 */
class DINKNARRATIVE_API FDinkNarrativeInputProcessor : public IInputProcessor
{
public:
	explicit FDinkNarrativeInputProcessor(UDinkStorySubsystem* InStory) : Story(InStory) {}

	virtual void Tick(const float DeltaTime, FSlateApplication& SlateApp, TSharedRef<ICursor> Cursor) override;
	virtual bool HandleKeyDownEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent) override;
	virtual bool HandleKeyUpEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent) override;
	virtual bool HandleMouseButtonDownEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) override;
	virtual bool HandleMouseButtonUpEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) override;
	virtual bool HandleMouseButtonDoubleClickEvent(FSlateApplication& SlateApp, const FPointerEvent& MouseEvent) override;
	virtual bool HandleMouseWheelOrGestureEvent(FSlateApplication& SlateApp, const FPointerEvent& InWheelEvent, const FPointerEvent* InGestureEvent) override;
	virtual const TCHAR* GetDebugName() const override { return TEXT("DinkNarrativeInput"); }

	static constexpr double RepeatGuardSeconds = 0.04;
	/** Clicks this soon after a menu or a skippable line appeared do not pick or skip it (tests set 0). */
	double MouseConfirmGuardSeconds = 0.3;

	/** A key went down (after the world/console checks). True if the narrative layer used it (the key is consumed). */
	bool ProcessKeyDown(const FKey& Key, bool bRepeat = false);
	void ProcessKeyUp(const FKey& Key);
	/** A mouse button went down (a double-click counts as a down). True if it did something; the caller never consumes it. */
	bool ProcessMouseDown(const FKey& Button);
	void ProcessMouseUp(const FKey& Button);
	/** Wheel: Delta > 0 is up. True if a menu or the inventory used it. */
	bool ProcessWheel(float Delta);
	/** Tick's release check: a key-up that outlived the repeat guard at Now, or the window lost (no key-up will come), lets the attack go. */
	void UpdateRelease(double Now, bool bAppActive);
	/** The attack input currently held (F, Left Ctrl or the left mouse button), invalid if none. */
	const FKey& GetAttackKeyDown() const { return AttackKeyDown; }

private:
	TWeakObjectPtr<UDinkStorySubsystem> Story;
	/** The attack key that is down, and a release that is waiting out the repeat guard. */
	FKey AttackKeyDown;
	double PendingReleaseAt = -1.;
	/** What was on screen last tick, and since when (for the click guard). */
	int32 SeenMenuInstance = 0;
	int32 SeenBlockingText = 0;
	double MenuSeenAt = -1.;
	double BlockingTextSeenAt = -1.;
	void ReleaseAttack();
	bool PressAttack(const FKey& Key);
	/** Story ready, a game world, the console closed. */
	bool IsGameInputAllowed() const;
	void ObserveScreen(double Now);
	bool ClickGuarded(double SeenAt) const;
};
