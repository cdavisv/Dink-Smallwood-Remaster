#include "DinkTestHelpers.h"
#include "DinkAudioSubsystem.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkVoicePlayback, "Dink.Audio.VoiceLinesFollowTheirTexts", DINK_TEST_FLAGS)
bool FDinkVoicePlayback::RunTest(const FString&)
{
 // The published table: every approved recording, keyed by the Ink #id tag, Mother's opening lines among them.
 FDinkVoiceTable Published;
 TestTrue(TEXT("published voice table loads"), Published.Load(FPaths::ProjectContentDir() / TEXT("Dink/Data/Audio/voice.json")));
 TestEqual(TEXT("all 2,088 approved recordings are published"), Published.Lines.Num(), 2088);
 const FDinkVoiceLine* Mother = Published.Find(TEXT("s1-h1-m.main.001"));
 TestNotNull(TEXT("Mother's first line has a recording"), Mother);
 if (Mother) TestTrue(TEXT("recording lives under Dink/Audio/Voice/mother"), Mother->Asset.StartsWith(TEXT("/Game/Dink/Audio/Voice/mother/")));
 TestNull(TEXT("system lines are never voiced"), Published.Find(TEXT("1gold.touch.001")));

 FDinkVoiceTable Table;
 for (const TCHAR* Id : {TEXT("a"), TEXT("b"), TEXT("c"), TEXT("d"), TEXT("x1"), TEXT("x2")}) Table.Lines.Add(Id, FDinkVoiceLine{FString(TEXT("/Game/Dink/Audio/Voice/t/")) + Id, 1.f});
 auto Text = [](int32 Handle, int32 Owner, const TCHAR* Id, double ExpireMs) { FDinkActiveText T; T.Handle = Handle; T.Owner = Owner; T.LineId = Id; T.ExpireMs = ExpireMs; return T; };
 FDinkVoiceTracker Tracker;
 TArray<FDinkActiveText> Texts = {Text(50, 7, TEXT("a"), 3000)};
 FDinkVoiceTracker::FChanges C = Tracker.Update(Texts, 0, Table);
 TestTrue(TEXT("a new voiced text starts its recording"), C.Started.Num() == 1 && C.Started[0].LineId == TEXT("a") && C.Stopped.IsEmpty());
 C = Tracker.Update(Texts, 16, Table);
 TestTrue(TEXT("a text already seen does not restart"), C.Started.IsEmpty() && C.Stopped.IsEmpty());
 Texts.Reset();
 C = Tracker.Update(Texts, 3000, Table);
 TestTrue(TEXT("a timed-out text lets its recording finish"), C.Stopped.IsEmpty() && Tracker.Playing.Num() == 1 && Tracker.Playing[0].bTail);
 Texts = {Text(51, 1, TEXT("b"), 6000)};
 C = Tracker.Update(Texts, 3100, Table);
 TestTrue(TEXT("the next speaker cuts the tail"), C.Stopped == TArray<int32>{50} && C.Started.Num() == 1 && C.Started[0].Owner == 1);
 Texts.Reset();
 C = Tracker.Update(Texts, 4000, Table);
 TestTrue(TEXT("a text removed early (skip, kill) stops its recording"), C.Stopped == TArray<int32>{51} && Tracker.Playing.IsEmpty());
 Texts = {Text(52, 7, TEXT("c"), 9000)};
 Tracker.Update(Texts, 4100, Table);
 Texts = {Text(53, 7, TEXT("d"), 9500)}; // say killed the speaker's earlier text
 C = Tracker.Update(Texts, 4200, Table);
 TestTrue(TEXT("a speaker's new line replaces the earlier one"), C.Stopped == TArray<int32>{52} && C.Started.Num() == 1 && C.Started[0].LineId == TEXT("d"));
 Texts.Add(Text(54, UDinkDirector::HandleNoSprite, TEXT("x1"), 9600));
 Texts.Add(Text(55, UDinkDirector::HandleNoSprite, TEXT("x2"), 9600));
 C = Tracker.Update(Texts, 4300, Table);
 TestTrue(TEXT("say_xy recordings do not cut each other or another speaker"), C.Started.Num() == 2 && C.Stopped.IsEmpty() && Tracker.Playing.Num() == 3);
 Texts.Add(Text(56, 9, TEXT("no-recording"), 9700));
 C = Tracker.Update(Texts, 4400, Table);
 TestTrue(TEXT("a line without a recording changes nothing"), C.Started.IsEmpty() && C.Stopped.IsEmpty());
 Texts = {Text(53, 7, TEXT("d"), 9500), Text(54, UDinkDirector::HandleNoSprite, TEXT("x1"), 9600)};
 Tracker.Forget(55);
 Texts.Add(Text(55, 3, TEXT("a"), 12000)); // handle reused by a new text
 C = Tracker.Update(Texts, 4500, Table);
 TestTrue(TEXT("a reused text handle is a new line"), C.Started.Num() == 1 && C.Started[0].Text == 55 && C.Started[0].Owner == 3);
 Texts = {Text(60, 4, TEXT("a"), 20000), Text(61, 4, TEXT("b"), 20000)};
 Tracker.Reset();
 C = Tracker.Update(Texts, 5000, Table);
 TestTrue(TEXT("two lines of one speaker in one frame: only the later plays"), C.Started.Num() == 1 && C.Started[0].Text == 61);
 return true;
}
