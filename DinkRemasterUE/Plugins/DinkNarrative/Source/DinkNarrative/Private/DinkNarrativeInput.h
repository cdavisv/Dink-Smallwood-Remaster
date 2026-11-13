#pragma once

#include "CoreMinimal.h"
#include "Framework/Application/IInputProcessor.h"

class UDinkStorySubsystem;

/**
 * Keyboard for the narrative layer, as a Slate input pre-processor so it needs no input assets:
 *   E                talk to the nearest scripted placement in front of the player (DinkC `talk`)
 *   Space/Enter/E    skip the say_stop text being waited on (the original's skip)
 *   Up/Down, W/S     move the menu highlight;  Enter/Space/E pick;  1-9 pick directly
 *   F / Left Ctrl    attack: the armed item's `use` (fists, sword, pig feed...; the original's Ctrl). One attack per
 *                    press, however long the key is held (UDinkGameplay::InputAttackPressed); the key's release lets
 *                    a drawn bow go. A down that follows an up of the same key within RepeatGuardSeconds is an OS
 *                    auto-repeat that was not flagged as one (X11 sends release+press pairs) and counts as still held.
 *   Q                cast the armed spell when charged (the original's Shift)
 * Only acts in a game world, and never while the console is open.
 */
class FDinkNarrativeInputProcessor : public IInputProcessor
{
public:
	explicit FDinkNarrativeInputProcessor(UDinkStorySubsystem* InStory) : Story(InStory) {}

	virtual void Tick(const float DeltaTime, FSlateApplication& SlateApp, TSharedRef<ICursor> Cursor) override;
	virtual bool HandleKeyDownEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent) override;
	virtual bool HandleKeyUpEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent) override;
	static constexpr double RepeatGuardSeconds = 0.04;
	virtual const TCHAR* GetDebugName() const override { return TEXT("DinkNarrativeInput"); }

private:
	TWeakObjectPtr<UDinkStorySubsystem> Story;
	/** The attack key that is down, and a release that is waiting out the repeat guard. */
	FKey AttackKeyDown;
	double PendingReleaseAt = -1.;
	void ReleaseAttack();
};
