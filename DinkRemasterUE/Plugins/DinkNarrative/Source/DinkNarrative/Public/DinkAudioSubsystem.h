#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkAudioSubsystem.generated.h"
class UAudioComponent;
class USoundAttenuation;
class ADinkScreenVolume;
class UDinkDirector;
class UDinkStorySubsystem;
struct FDinkActiveText;
struct DINKNARRATIVE_API FDinkApprovedSound
{
 FString Asset;
 bool bLoop = false;
};
/** Approved audio lookup is independent of the audio device and original cue recording. */
struct DINKNARRATIVE_API FDinkAudioSelection
{
 TMap<FString, FDinkApprovedSound> Sounds, Music, Screens;
 float MusicVolume = .35f, SfxVolume = .8f;
 bool Load(const FString& Filename);
 static FString Key(const FString& Raw);
 const FDinkApprovedSound* ResolveMusic(const FString& Raw) const;
 static int32 SpatialSpriteHandle(int32 Handle, bool bHasBoundActor = false);
 static float Pitch(int32 OriginalSpeed) { return OriginalSpeed > 0 ? FMath::Clamp(OriginalSpeed / 22050.f, .125f, 4.f) : 1.f; }
 /**
  * A repeating cue (playsound's repeat argument, a sprite's sp_sound) of a sound that is not itself a loop is replayed by the
  * subsystem each time it ends, on a component that is not auto-destroyed. It used to play a duplicate of the SoundWave with
  * bLooping set, which a cooked game cannot do: a cooked SoundWave has no editor data to duplicate, and the packaged game died
  * with a fatal error in USoundWave::Serialize on the first screen with an ambient sound (SCR_036, Terris; playthrough QA 15 Nov 2026).
  */
 static bool ReplaysRepeat(bool bAssetLoops, int32 Repeat) { return Repeat != 0 && !bAssetLoops; }
 /** When a finished repeating one-shot may start again: a full played length (the sound's duration over its pitch, at least 0.1 s) after its last start. */
 /** kill_repeat_sounds' rule (dink.cpp:6414): a full screen build stops a repeating cue that no sprite owns; one started in the same frame belongs to the new screen. */
 static bool StopsOnScreenBuild(int32 Repeat, int32 OwnerSprite, bool bStartedThisFrame) { return Repeat != 0 && OwnerSprite == 0 && !bStartedThisFrame; }
 static bool ReplayDue(double NowSeconds, double LastStartSeconds, float DurationSeconds)
 { return NowSeconds - LastStartSeconds >= FMath::Max(0.1, double(DurationSeconds)); }
};
/** One spoken line's recording (Content/Dink/Data/Audio/voice.json, written by Scripts/import_voice.py). */
struct DINKNARRATIVE_API FDinkVoiceLine
{
 FString Asset;
 float DurationS = 0.f;
};
/** Ink line id (#id tag, "s1-h1-m.main.001") -> recording. */
struct DINKNARRATIVE_API FDinkVoiceTable
{
 TMap<FString, FDinkVoiceLine> Lines;
 float Volume = 1.f;
 bool Load(const FString& Filename);
 const FDinkVoiceLine* Find(const FString& LineId) const { return Lines.Find(LineId); }
};
/**
 * Which voice recordings start and stop, decided from the story's text list alone (no audio device, so it is testable).
 * The story's timing is the 1997 engine's and is never changed for a voice: a recording follows its text.
 *  - A new text whose line has a recording starts it; it first stops the speaker's earlier recording (a say kills the
 *    speaker's text, D:7756) and any leftover tail of a text that has already timed out.
 *  - A text removed before its time (say/say_stop killing it, the player skipping, a load) stops its recording.
 *  - A text that times out lets its recording finish (400 of the 2,088 recordings run a little past their text).
 */
struct DINKNARRATIVE_API FDinkVoiceTracker
{
 struct FVoice
 {
  int32 Text = 0;
  int32 Owner = 0;
  FString LineId;
  double ExpireMs = 0.0;
  bool bTail = false;
 };
 struct FChanges
 {
  TArray<FVoice> Started;
  TArray<int32> Stopped; // text handles
 };
 TArray<FVoice> Playing;
 FChanges Update(const TArray<FDinkActiveText>& Texts, double NowMs, const FDinkVoiceTable& Table);
 /** The recording of this text ended or could not play. */
 void Forget(int32 Text);
 /** The text has timed out and its recording is still finishing (the dialogue box keeps showing it meanwhile). */
 bool IsTail(int32 Text, const FString& LineId) const { return Playing.ContainsByPredicate([&](const FVoice& V) { return V.bTail && V.Text == Text && V.LineId == LineId; }); }
 void Reset() { Playing.Reset(); Known.Reset(); }
private:
 TMap<int32, double> Known; // text handle -> ExpireMs of every text already seen
};
/** Local audio playback; the classic director's cue journal remains authoritative. */
UCLASS()
class DINKNARRATIVE_API UDinkAudioSubsystem : public UTickableWorldSubsystem
{
 GENERATED_BODY()
public:
 virtual void Initialize(FSubsystemCollectionBase& Collection) override;
 virtual void Deinitialize() override;
 virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
 virtual void Tick(float DeltaTime) override;
 virtual TStatId GetStatId() const override;
 void HandleCue(const FString& Cue, UDinkDirector* Director);
 void StopAll();
 /** kill_repeat_sounds: stops the repeating cues no sprite owns (screen change, force_vision's rebuild). */
 void StopOwnerlessRepeats();
 const FDinkAudioSelection& GetSelection() const { return Selection; }
 const FString& GetPlayingMusicAsset() const { return PlayingMusic; }
 int32 GetEffectCount() const { return Effects.Num(); }
 const FDinkVoiceTable& GetVoices() const { return Voices; }
 int32 GetVoiceCount() const { return VoiceComponents.Num(); }
 const FString& GetLastVoiceLine() const { return LastVoiceLine; }
 /**
  * True while the recording of a text that has already timed out is still audible. The dialogue box (DinkNarrativeOverlay.cpp)
  * keeps that line up until the recording ends or another line takes the box, so the words and the voice end together;
  * the story's timing is not touched (the text itself is gone from GetActiveTexts()).
  */
 bool IsVoiceTailPlaying(int32 Text, const FString& LineId) const;
private:
 FDinkAudioSelection Selection;
 FDinkVoiceTable Voices;
 FDinkVoiceTracker VoiceTracker;
 FString LastVoiceLine;
 TMap<int32, TWeakObjectPtr<UAudioComponent>> VoiceComponents; // text handle -> recording
 FString PlayingMusic;
 TWeakObjectPtr<UDinkDirector> BoundDirector;
 TMap<TWeakObjectPtr<UAudioComponent>, int32> EffectSprites;
 TMap<int32, TPair<int32, TWeakObjectPtr<UAudioComponent>>> Ambient;
 UPROPERTY(Transient) TObjectPtr<UAudioComponent> Music;
 UPROPERTY(Transient) TArray<TObjectPtr<UAudioComponent>> Effects;
 /**
  * Effects replayed when they end (FDinkAudioSelection::ReplaysRepeat) -> wall-clock time of their last start; not auto-destroyed,
  * so StopEffect destroys them. A replay waits at least the sound's own length since the last start, so a one-shot the audio
  * engine culls at once (out of range, inaudible) is not restarted every frame.
  */
 TMap<TObjectKey<UAudioComponent>, double> RepeatEffects;
 /** Repeating cues no sprite owns (2D) -> frame they started; a full screen build stops them (StopOwnerlessRepeats). */
 TMap<TObjectKey<UAudioComponent>, uint64> OwnerlessRepeats;
 void StopEffect(UAudioComponent* Effect);
 UPROPERTY(Transient) TObjectPtr<USoundAttenuation> VoiceAttenuation;
 UPROPERTY(Transient) TObjectPtr<USoundAttenuation> EffectAttenuation;
 void EnterScreen(ADinkScreenVolume* Screen);
 void PlayMusic(const FDinkApprovedSound& Entry);
 bool CanPlay() const;
 void UpdateVoices(UDinkDirector* Director);
 void StopVoice(int32 Text);
 /** UDinkStorySubsystem::OnLineSkipped: the player skipped a line; its recording stops in the same frame. */
 void HandleLineSkipped(int32 Text);
 TWeakObjectPtr<UDinkStorySubsystem> HookedStory;
 FDelegateHandle LineSkippedHandle;
};
