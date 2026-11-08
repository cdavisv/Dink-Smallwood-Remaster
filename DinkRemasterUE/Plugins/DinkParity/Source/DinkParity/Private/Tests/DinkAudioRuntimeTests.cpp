#include "DinkTestHelpers.h"
#include "DinkAudioSubsystem.h"
#include "DinkDirector.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkApprovedAudioLookup, "Dink.Audio.ApprovedLookupAndCueParity", DINK_TEST_FLAGS)
bool FDinkApprovedAudioLookup::RunTest(const FString&)
{
 FDinkAudioSelection Selection;
 TestTrue(TEXT("published approved manifest loads"), Selection.Load(FPaths::ProjectContentDir() / TEXT("Dink/Data/Audio/approved.json")));
 TestEqual(TEXT("44 approved SFX"), Selection.Sounds.Num(), 44);
 for (const TCHAR* Key : {TEXT("9"), TEXT("44"), TEXT("48"), TEXT("49")}) TestFalse(FString::Printf(TEXT("rejected SFX %s silent"), Key), Selection.Sounds.Contains(Key));
 const FDinkApprovedSound* Ogg = Selection.ResolveMusic(TEXT("SOUND/5.OGG"));
 const FDinkApprovedSound* Midi = Selection.ResolveMusic(TEXT("sound\\5.mid"));
 TestNotNull(TEXT("5.ogg resolves"), Ogg); TestNotNull(TEXT("5.mid resolves"), Midi);
 if (Ogg && Midi) TestNotEqual(TEXT("extensions retain different selections"), Ogg->Asset, Midi->Asset);
 TestNull(TEXT("unknown track remains silent"), Selection.ResolveMusic(TEXT("unknown.mid")));
 TestTrue(TEXT("starting house has explicit approved cue"), Selection.Screens.Contains(TEXT("1")));
 TestEqual(TEXT("original speed reference"), FDinkAudioSelection::Pitch(22050), 1.f);
 TestEqual(TEXT("half original speed"), FDinkAudioSelection::Pitch(11025), .5f);
 TestEqual(TEXT("double original speed"), FDinkAudioSelection::Pitch(44100), 2.f);
 TestEqual(TEXT("global no-sprite sound sentinel"), FDinkAudioSelection::SpatialSpriteHandle(1000), 0);
 TestEqual(TEXT("global attachment sentinel"), FDinkAudioSelection::SpatialSpriteHandle(1007), 0);
 TestEqual(TEXT("real sprite remains positional"), FDinkAudioSelection::SpatialSpriteHandle(7), 7);
 TestEqual(TEXT("bound high actor handle remains positional"), FDinkAudioSelection::SpatialSpriteHandle(1007,true),1007);
 const FString Fixture = FPaths::CreateTempFilename(*FPaths::ProjectSavedDir(), TEXT("audio_selection_"), TEXT(".json"));
 FFileHelper::SaveStringToFile(TEXT(R"JSON({"schema":"dink-audio/1","sounds":{"9":{"asset":"/Game/Dink/Audio/SFX/FutureApprovedPunch","loop":false}},"music":{"5":{"asset":"/Game/Dink/Audio/Music/Story"},"1005":{"asset":"/Game/Dink/Audio/Music/Edge"}}})JSON"), *Fixture);
 FDinkAudioSelection Future;
 TestTrue(TEXT("replacement approval fixture loads"), Future.Load(Fixture));
 TestTrue(TEXT("future explicit approval is not permanently suppressed"), Future.Sounds.Contains(TEXT("9")));
 TestTrue(TEXT("raw1005 retains distinct approved route"), Future.ResolveMusic(TEXT("1005")) && Future.ResolveMusic(TEXT("1005"))->Asset.EndsWith(TEXT("/Edge")));
 IFileManager::Get().Delete(*Fixture);
 FDinkAudioStub Journal; FString Received;
 Journal.Playback = [&Received](const FString& Cue) { Received = Cue; };
 const FString Cue = TEXT("sound:1 speed=22050 random=0 sprite=7 repeat=1"); Journal.Cue(Cue);
 TestEqual(TEXT("playback receives exact journal cue"), Received, Cue);
 TestEqual(TEXT("journal remains unchanged"), Journal.Cues.Last(), Cue);
 UDinkDirector* Director = NewObject<UDinkDirector>();
 Director->Audio.CurrentMusic = TEXT("5.mid");
 const TSharedPtr<FJsonObject> Saved = Director->SaveState();
 FString RestoredCue;
 Director->Audio.Playback = [&RestoredCue](const FString& Cue) { RestoredCue = Cue; };
 Director->Audio.CurrentMusic = TEXT("8.ogg");
 Director->LoadState(Saved);
 TestEqual(TEXT("save restores explicit playback track"), RestoredCue, FString(TEXT("music:5.mid")));
 TestTrue(TEXT("save audio restore does not add classic script cues"), Director->Audio.Cues.IsEmpty());
 Journal.Playback = nullptr; Journal.Cue(TEXT("music:stop"));
 TestEqual(TEXT("worldless/headless recording still works"), Journal.Cues.Num(), 2);
 return true;
}
