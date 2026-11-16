// Dink.Audio.RepeatReplaysWithoutDuplicate: a repeating cue (playsound's repeat argument, a sprite's sp_sound: the save machine,
// fires) of a sound that is not a loop asset is replayed when it ends. It used to play DuplicateObject(SoundWave) with bLooping
// set; a cooked game cannot duplicate a cooked SoundWave and the packaged game died with a fatal error in USoundWave::Serialize
// on the first screen with an ambient sound (SCR_036 in Terris, right after the toll bridge; playthrough QA 15 Nov 2026).
// The rendered packaged probe run is the end-to-end proof; this pins the policy and that the duplicate path is gone.
#include "DinkTestHelpers.h"
#include "DinkAudioSubsystem.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAudioRepeatTest, "Dink.Audio.RepeatReplaysWithoutDuplicate", DINK_TEST_FLAGS)
bool FDinkAudioRepeatTest::RunTest(const FString&)
{
	TestTrue(TEXT("a repeating cue of a one-shot asset is replayed"), FDinkAudioSelection::ReplaysRepeat(false, 1));
	TestFalse(TEXT("a loop asset loops by itself"), FDinkAudioSelection::ReplaysRepeat(true, 1));
	TestFalse(TEXT("a one-shot cue plays once"), FDinkAudioSelection::ReplaysRepeat(false, 0));
	// A culled one-shot ends at once: it may start again only a full length after its last start, never every frame.
	TestFalse(TEXT("no replay one frame after the start"), FDinkAudioSelection::ReplayDue(10.0 + 1.0 / 60.0, 10.0, 2.5f));
	TestTrue(TEXT("a replay after a full length"), FDinkAudioSelection::ReplayDue(12.5, 10.0, 2.5f));
	TestFalse(TEXT("a zero-length sound waits 0.1 s"), FDinkAudioSelection::ReplayDue(10.05, 10.0, 0.f));
	// A pitched cue (speed 44100 = pitch 2) plays a 2.5 s sound in 1.25 s; the subsystem passes duration / pitch.
	const float Played = 2.5f / FDinkAudioSelection::Pitch(44100);
	TestTrue(TEXT("a pitch-2 repeat replays after its played 1.25 s"), FDinkAudioSelection::ReplayDue(11.25, 10.0, Played));
	TestFalse(TEXT("and not before"), FDinkAudioSelection::ReplayDue(11.2, 10.0, Played));
	// kill_repeat_sounds (dink.cpp:6410-6424, run by every full screen build at 6750 and by force_vision at 8497): a repeating cue
	// that no sprite owns stops, whether or not its asset loops (the warp machines' sound 34 is a loop asset), unless the new
	// screen itself started it in that frame; owned or one-shot cues are not touched.
	TestTrue(TEXT("an ownerless repeat stops on a screen build"), FDinkAudioSelection::StopsOnScreenBuild(1, 0, false));
	TestFalse(TEXT("a repeat a sprite owns does not"), FDinkAudioSelection::StopsOnScreenBuild(1, 23, false));
	TestFalse(TEXT("a one-shot does not"), FDinkAudioSelection::StopsOnScreenBuild(0, 0, false));
	TestFalse(TEXT("a repeat the new screen started in this frame does not"), FDinkAudioSelection::StopsOnScreenBuild(1, 0, true));
	FString Source;
	if (FFileHelper::LoadFileToString(Source, *(FPaths::ProjectPluginsDir() / TEXT("DinkNarrative/Source/DinkNarrative/Private/DinkAudioSubsystem.cpp"))))
	{
		TestFalse(TEXT("no SoundWave is duplicated at run time (cooked games cannot)"), Source.Contains(TEXT("DuplicateObject")));
		TestTrue(TEXT("the screen build and force_vision run kill_repeat_sounds"), Source.Contains(TEXT("StopOwnerlessRepeats();")));
	}
	else
	{
		AddWarning(TEXT("DinkAudioSubsystem.cpp not found beside the plugin (packaged run): only the policy is checked"));
	}
	return true;
}
