#pragma once

#include "CoreMinimal.h"

/**
 * Story-beat captures for rendered play-throughs (playthrough QA, 15 Nov 2026). Off unless the game is started with
 * -DinkBeatShots=<dir> or the console runs `dink.BeatShots <dir>` (`dink.BeatShots off` stops it). While on, a core ticker watches
 * the running game and takes a viewport screenshot WITH the UI (dialogue box, menus) into <dir> at every story beat:
 * a change of &story, the first arrival on each screen, a load, a menu, a locked fight (screenlock), a level-up, a
 * death (Dink's life reaching 0), a script error, every probe step done, and every 60 s of wall time. Each shot logs one line
 * `DINK BEAT: <n> <kind> <detail> screen=<s> story=<st> life=<l> gold=<g> t=<story ms> file=<png>`. Frames longer than 200 ms of
 * wall time are logged as `DINK HITCH: <ms> ms screen=<s>` (always on while beats are on).
 *
 * Nothing here changes the game: it reads the story subsystem and the facts, never writes them, so probe traces do not move.
 */
namespace DinkBeatCapture
{
	/** Queue a shot now (the probe calls it when a step is done). No-op while beats are off. */
	void Request(const FString& Kind, const FString& Detail, int32 DelayFrames = 0);
	bool IsOn();
	/** Registers the ticker and reads -DinkBeatShots= (module start-up). */
	void Startup();
	void Shutdown();
}
