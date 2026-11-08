#pragma once

#include "CoreMinimal.h"

class UWorld;

/**
 * Start-up alignment of a PACKAGED game process with the editor's PIE session, so that the probe's traces are byte-identical
 * (Plugins/DinkParity/Docs/packaged_probe.md, "Start-up alignment"). Active only in game builds started with -DinkProbeHold
 * (Scripts/run_packaged_tests.sh passes it); never in the editor, never without the switch. No gameplay code is involved.
 *
 * PIE: the probe's first Update comes right after the first world frame (story clock 16.667 ms), the story ticks before the
 * greybox in every frame, so the new game starts one frame later (33.333 ms) and a teleport is seen by the story two frames
 * after the probe made it. A game process differs in two ways:
 *  1. Its first world frames run before the automation framework can start the test (5 frames at best, 300 without
 *     `Automation ... Now`), so the new game is already under way when the probe starts.
 *  2. The tick order of the two tickables is the other way round: the game's GameInstance creates a throwaway default world first
 *     (UGameInstance::InitializeStandalone), whose greybox subsystem takes an early place in the engine's tickable list that the real
 *     world's greybox then reuses, ahead of the story subsystem. A screen change is then seen one frame earlier than in PIE,
 *     which moves every later timestamp and, through the floating-point phase of the story clock, the draws of the one shared rand().
 * Hold: when the engine has finished starting (before its first tick) the world is paused. The probe's first Update puts the story
 * subsystem back in front of the greybox in the tickable list (remove both, add the story first) and releases the pause; one
 * world frame later (story clock 16.667 ms, as in PIE) the probe begins.
 */
namespace DinkProbeHold
{
	/** Called when the engine loop has finished initialising (module start-up registers it). No-op unless -DinkProbeHold. */
	void Engage();
	/** The probe's Update calls this first. True: the probe must do nothing else this frame. */
	bool Process(UWorld* World);
	bool IsEngaged();
}
