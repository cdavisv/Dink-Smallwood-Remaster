#include "DinkAudioSubsystem.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "Engine/GameInstance.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "AudioDevice.h"
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
DEFINE_LOG_CATEGORY_STATIC(LogDinkPlayback, Log, All);
#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundWave.h"
#include "Sound/SoundAttenuation.h"

FString FDinkAudioSelection::Key(const FString& Raw)
{
 FString Result = Raw; Result.ReplaceInline(TEXT("\\"), TEXT("/"));
 return FPaths::GetCleanFilename(Result).ToLower();
}
bool FDinkAudioSelection::Load(const FString& Filename)
{
 Sounds.Reset(); Music.Reset(); Screens.Reset();
 FString Text; TSharedPtr<FJsonObject> Root;
 if (!FFileHelper::LoadFileToString(Text, *Filename) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid()) return false;
 FString Schema; if (!Root->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-audio/1")) return false;
 auto Read = [&](const TCHAR* Field, TMap<FString, FDinkApprovedSound>& Out)
 {
  const TSharedPtr<FJsonObject>* Map;
  if (!Root->TryGetObjectField(Field, Map)) return;
  for (const auto& Pair : (*Map)->Values)
  {
   const TSharedPtr<FJsonObject>* Value;
   if (!Pair.Value->TryGetObject(Value)) continue;
   FDinkApprovedSound Entry;
   if (!(*Value)->TryGetStringField(TEXT("asset"), Entry.Asset) || !Entry.Asset.StartsWith(TEXT("/Game/Dink/Audio/"))) continue;
   (*Value)->TryGetBoolField(TEXT("loop"), Entry.bLoop);
   Out.Add(Key(FString(Pair.Key.ToView())), Entry);
  }
 };
 Read(TEXT("sounds"), Sounds); Read(TEXT("music"), Music); Read(TEXT("screen_music"), Screens);
 const TSharedPtr<FJsonObject>* Volumes;
 if (Root->TryGetObjectField(TEXT("volumes"), Volumes))
 {
  double V; if ((*Volumes)->TryGetNumberField(TEXT("music"), V)) MusicVolume = FMath::Clamp(V, 0., 1.);
  if ((*Volumes)->TryGetNumberField(TEXT("sfx"), V)) SfxVolume = FMath::Clamp(V, 0., 1.);
 }
 return true;
}
int32 FDinkAudioSelection::SpatialSpriteHandle(int32 Handle, bool bHasBoundActor) { return !bHasBoundActor && Handle >= UDinkDirector::HandleNoSprite ? 0 : Handle; }
const FDinkApprovedSound* FDinkAudioSelection::ResolveMusic(const FString& Raw) const { return Music.Find(Key(Raw)); }
bool FDinkVoiceTable::Load(const FString& Filename)
{
 Lines.Reset(); Volume = 1.f;
 FString Text; TSharedPtr<FJsonObject> Root;
 if (!FFileHelper::LoadFileToString(Text, *Filename) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid()) return false;
 FString Schema; if (!Root->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-voice/1")) return false;
 double V; if (Root->TryGetNumberField(TEXT("volume"), V)) Volume = FMath::Clamp(V, 0., 1.);
 const TSharedPtr<FJsonObject>* Map;
 if (!Root->TryGetObjectField(TEXT("lines"), Map)) return false;
 for (const auto& Pair : (*Map)->Values)
 {
  const TSharedPtr<FJsonObject>* Value;
  if (!Pair.Value->TryGetObject(Value)) continue;
  FDinkVoiceLine Line;
  if (!(*Value)->TryGetStringField(TEXT("asset"), Line.Asset) || !Line.Asset.StartsWith(TEXT("/Game/Dink/Audio/Voice/"))) continue;
  if ((*Value)->TryGetNumberField(TEXT("duration_s"), V)) Line.DurationS = V;
  Lines.Add(FString(Pair.Key.ToView()), Line);
 }
 return true;
}
FDinkVoiceTracker::FChanges FDinkVoiceTracker::Update(const TArray<FDinkActiveText>& Texts, double NowMs, const FDinkVoiceTable& Table)
{
 FChanges Out;
 auto Shown = [&Texts](const FVoice& V) { return Texts.ContainsByPredicate([&V](const FDinkActiveText& T) { return T.Handle == V.Text && T.ExpireMs == V.ExpireMs; }); };
 auto Stop = [this, &Out](int32 Index) { Out.Stopped.Add(Playing[Index].Text); Playing.RemoveAt(Index); };
 // Texts that are gone: timed out -> the recording finishes as a tail; removed early -> it stops.
 for (int32 I = Playing.Num() - 1; I >= 0; --I)
 {
  FVoice& V = Playing[I];
  if (V.bTail || Shown(V)) continue;
  if (NowMs >= V.ExpireMs) V.bTail = true; else Stop(I);
 }
 // New texts, in the order they were shown.
 for (const FDinkActiveText& T : Texts)
 {
  if (const double* Seen = Known.Find(T.Handle); Seen && *Seen == T.ExpireMs) continue;
  Known.Add(T.Handle, T.ExpireMs);
  if (T.LineId.IsEmpty() || !Table.Find(T.LineId)) continue;
  for (int32 I = Playing.Num() - 1; I >= 0; --I)
  {
   // say_xy texts (owner 1000) never kill each other in the engine, so their recordings may overlap.
   if (Playing[I].bTail || (Playing[I].Owner == T.Owner && T.Owner != UDinkDirector::HandleNoSprite)) Stop(I);
  }
  FVoice V; V.Text = T.Handle; V.Owner = T.Owner; V.LineId = T.LineId; V.ExpireMs = T.ExpireMs;
  Playing.Add(V);
  Out.Started.Add(V);
 }
 // A recording started and stopped within this update never plays.
 Out.Started.RemoveAll([this](const FVoice& V) { return !Playing.ContainsByPredicate([&V](const FVoice& P) { return P.Text == V.Text && P.ExpireMs == V.ExpireMs; }); });
 for (auto It = Known.CreateIterator(); It; ++It)
 {
  const int32 Handle = It.Key();
  if (!Texts.ContainsByPredicate([Handle](const FDinkActiveText& T) { return T.Handle == Handle; })) It.RemoveCurrent();
 }
 return Out;
}
void FDinkVoiceTracker::Forget(int32 Text) { Playing.RemoveAll([Text](const FVoice& V) { return V.Text == Text; }); }
bool UDinkAudioSubsystem::DoesSupportWorldType(EWorldType::Type Type) const { return Type == EWorldType::Game || Type == EWorldType::PIE; }
void UDinkAudioSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
 Super::Initialize(Collection);
 Collection.InitializeDependency<UDinkGreyboxSubsystem>();
 Selection.Load(FPaths::ProjectContentDir() / TEXT("Dink/Data/Audio/approved.json"));
 if (Voices.Load(FPaths::ProjectContentDir() / TEXT("Dink/Data/Audio/voice.json"))) UE_LOG(LogDinkPlayback, Log, TEXT("Voice table: %d recorded lines, volume %.2f"), Voices.Lines.Num(), Voices.Volume);
 GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>()->OnScreenChanged.AddUObject(this, &UDinkAudioSubsystem::EnterScreen);
}
void UDinkAudioSubsystem::StopEffect(UAudioComponent* Effect)
{
 if (!IsValid(Effect)) return;
 const bool bRepeat = RepeatEffects.Remove(Effect) > 0;
 Effect->Stop();
 if (bRepeat) Effect->DestroyComponent(); // not auto-destroyed (see ReplaysRepeat)
}
bool UDinkAudioSubsystem::CanPlay() const { return GetWorld() && GetWorld()->GetAudioDevice().IsValid() && !IsRunningDedicatedServer(); }
void UDinkAudioSubsystem::StopAll()
{
 if (Music) { Music->Stop(); Music->DestroyComponent(); } Music = nullptr; PlayingMusic.Reset();
 for (UAudioComponent* Effect : Effects) if (Effect) StopEffect(Effect);
 Effects.Reset(); Ambient.Reset(); EffectSprites.Reset(); RepeatEffects.Reset();
 for (const auto& Pair : VoiceComponents) if (Pair.Value.IsValid()) Pair.Value->Stop();
 VoiceComponents.Reset(); VoiceTracker.Reset();
}
void UDinkAudioSubsystem::StopVoice(int32 Text)
{
 if (TWeakObjectPtr<UAudioComponent> Component; VoiceComponents.RemoveAndCopyValue(Text, Component) && Component.IsValid()) Component->FadeOut(.08f, 0.f);
}
bool UDinkAudioSubsystem::IsVoiceTailPlaying(int32 Text, const FString& LineId) const
{
 const TWeakObjectPtr<UAudioComponent>* Component = VoiceComponents.Find(Text);
 return Component && Component->IsValid() && (*Component)->IsPlaying() && VoiceTracker.IsTail(Text, LineId);
}
void UDinkAudioSubsystem::HandleLineSkipped(int32 Text)
{
 if (!VoiceComponents.Contains(Text)) return;
 StopVoice(Text); VoiceTracker.Forget(Text);
 UE_LOG(LogDinkPlayback, Log, TEXT("Voice of text %d stopped: line skipped"), Text);
}
void UDinkAudioSubsystem::UpdateVoices(UDinkDirector* Director)
{
 UGameInstance* Instance = GetWorld()->GetGameInstance();
 UDinkStorySubsystem* Story = Instance ? Instance->GetSubsystem<UDinkStorySubsystem>() : nullptr;
 if (!Story || Voices.Lines.IsEmpty()) return;
 if (HookedStory.Get() != Story)
 {
  if (UDinkStorySubsystem* Old = HookedStory.Get()) Old->OnLineSkipped.Remove(LineSkippedHandle);
  LineSkippedHandle = Story->OnLineSkipped.AddUObject(this, &UDinkAudioSubsystem::HandleLineSkipped);
  HookedStory = Story;
 }
 for (auto It = VoiceComponents.CreateIterator(); It; ++It)
 {
  if (!It.Value().IsValid() || !It.Value()->IsPlaying()) { VoiceTracker.Forget(It.Key()); It.RemoveCurrent(); }
 }
 const FDinkVoiceTracker::FChanges Changes = VoiceTracker.Update(Story->GetActiveTexts(), Story->GetNowMs(), Voices);
 for (const int32 Text : Changes.Stopped) StopVoice(Text);
 for (const FDinkVoiceTracker::FVoice& V : Changes.Started)
 {
  const FDinkVoiceLine* Line = Voices.Find(V.LineId);
  USoundBase* Sound = Line ? LoadObject<USoundBase>(nullptr, *Line->Asset) : nullptr;
  if (!Sound) { UE_LOG(LogDinkPlayback, Warning, TEXT("Voice %s: recording %s does not load"), *V.LineId, Line ? *Line->Asset : TEXT("?")); VoiceTracker.Forget(V.Text); continue; }
  // Dink is the camera's subject and say_xy texts have no speaker: both play flat. Others speak from where they stand.
  AActor* Actor = Director && V.Owner != 1 && V.Owner != UDinkDirector::HandleNoSprite ? Director->GetActor(V.Owner) : nullptr;
  UAudioComponent* Component = nullptr;
  if (Actor && Actor->GetRootComponent())
  {
   if (!VoiceAttenuation)
   {
    VoiceAttenuation = NewObject<USoundAttenuation>(this);
    VoiceAttenuation->Attenuation.AttenuationShapeExtents = FVector(900.f); VoiceAttenuation->Attenuation.FalloffDistance = 3500.f;
   }
   Component = UGameplayStatics::SpawnSoundAttached(Sound, Actor->GetRootComponent(), NAME_None, FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true, Voices.Volume, 1.f, 0.f, VoiceAttenuation, nullptr, true);
  }
  else Component = UGameplayStatics::SpawnSound2D(GetWorld(), Sound, Voices.Volume, 1.f, 0.f, nullptr, false, true);
  if (!Component) { VoiceTracker.Forget(V.Text); continue; }
  VoiceComponents.Add(V.Text, Component);
  LastVoiceLine = V.LineId;
  UE_LOG(LogDinkPlayback, Log, TEXT("Playing voice %s speaker=%d text=%d %s"), *V.LineId, V.Owner, V.Text, Actor ? TEXT("positional") : TEXT("2d"));
 }
}
void UDinkAudioSubsystem::Deinitialize()
{
 if (UDinkGreyboxSubsystem* Greybox = GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>()) Greybox->OnScreenChanged.RemoveAll(this);
 if (UDinkStorySubsystem* Story = HookedStory.Get()) Story->OnLineSkipped.Remove(LineSkippedHandle);
 HookedStory.Reset();
 StopAll(); Super::Deinitialize();
}
void UDinkAudioSubsystem::PlayMusic(const FDinkApprovedSound& Entry)
{
 if (PlayingMusic == Entry.Asset && Music && Music->IsPlaying()) return;
 if (Music) { Music->Stop(); Music->DestroyComponent(); } Music = nullptr; PlayingMusic.Reset();
 if (!CanPlay()) return;
 if (USoundBase* Sound = LoadObject<USoundBase>(nullptr, *Entry.Asset))
 {
  Music = UGameplayStatics::SpawnSound2D(GetWorld(), Sound, Selection.MusicVolume, 1.f, 0.f, nullptr, false, false);
  if (Music) { PlayingMusic = Entry.Asset; UE_LOG(LogDinkPlayback, Log, TEXT("Playing approved music %s volume=%.2f"), *Entry.Asset, Selection.MusicVolume); }
 }
}
void UDinkAudioSubsystem::EnterScreen(ADinkScreenVolume* Screen)
{
 if (!Screen) return;
 UDinkGreyboxSubsystem* Greybox = GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>();
 for (int32 I = Effects.Num() - 1; I >= 0; --I)
 {
  UAudioComponent* C = Effects[I];
  if (IsValid(C) && C->GetAttachParent() && Greybox->FindScreenAt(C->GetAttachParent()->GetComponentLocation()) != Screen)
  { StopEffect(C); Effects.RemoveAtSwap(I); }
 }
 if (const FDinkApprovedSound* Override = Selection.Screens.Find(FString::FromInt(Screen->ScreenNumber))) { PlayMusic(*Override); return; }
 if (Screen->MusicAction == TEXT("stop")) { if (Music) { Music->Stop(); Music->DestroyComponent(); } Music = nullptr; PlayingMusic.Reset(); return; }
 if (Screen->MusicAction == TEXT("none") || Screen->MusicRaw == 0) return;
 if (const FDinkApprovedSound* Entry = Selection.ResolveMusic(Screen->MusicFile)) PlayMusic(*Entry);
 else if (const FDinkApprovedSound* Raw = Selection.ResolveMusic(FString::FromInt(Screen->MusicRaw))) PlayMusic(*Raw);
}
void UDinkAudioSubsystem::HandleCue(const FString& Cue, UDinkDirector* Director)
{
 if (Director) BoundDirector = Director;
 if (Cue == TEXT("music:stop") || Cue == TEXT("cd:stop")) { if (Music) { Music->Stop(); Music->DestroyComponent(); } Music = nullptr; PlayingMusic.Reset(); return; }
 if (Cue.StartsWith(TEXT("music:"))) { if (const FDinkApprovedSound* Entry = Selection.ResolveMusic(Cue.Mid(6))) PlayMusic(*Entry); return; }
 if (!Cue.StartsWith(TEXT("sound:")) || !CanPlay()) return;
 TArray<FString> Tokens; Cue.Mid(6).ParseIntoArrayWS(Tokens);
 if (Tokens.IsEmpty()) return;
 const FDinkApprovedSound* Entry = Selection.Sounds.Find(Tokens[0]); if (!Entry) return;
 int32 Speed = 22050, Sprite = 0, Repeat = 0;
 for (int32 I = 1; I < Tokens.Num(); ++I)
 {
  if (Tokens[I].StartsWith(TEXT("speed="))) Speed = FCString::Atoi(*Tokens[I].Mid(6));
  else if (Tokens[I].StartsWith(TEXT("sprite="))) Sprite = FCString::Atoi(*Tokens[I].Mid(7));
  else if (Tokens[I] == TEXT("sprite") && I + 1 < Tokens.Num()) Sprite = FCString::Atoi(*Tokens[++I]);
  else if (Tokens[I].StartsWith(TEXT("repeat="))) Repeat = FCString::Atoi(*Tokens[I].Mid(7));
 }
 AActor* Actor = Director && Sprite > 0 ? Director->GetActor(Sprite) : nullptr;
 Sprite = FDinkAudioSelection::SpatialSpriteHandle(Sprite, IsValid(Actor));
 USoundBase* Sound = LoadObject<USoundBase>(nullptr, *Entry->Asset); if (!Sound) return;
 const bool bReplay = FDinkAudioSelection::ReplaysRepeat(Entry->bLoop, Repeat);
 UAudioComponent* Component = nullptr;
 if (Actor && Actor->GetRootComponent())
 {
  USoundAttenuation* Attenuation = NewObject<USoundAttenuation>(this);
  Attenuation->Attenuation.AttenuationShapeExtents = FVector(150.f); Attenuation->Attenuation.FalloffDistance = 2200.f;
  Component = UGameplayStatics::SpawnSoundAttached(Sound, Actor->GetRootComponent(), NAME_None, FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true, Selection.SfxVolume, FDinkAudioSelection::Pitch(Speed), 0.f, Attenuation, nullptr, !bReplay);
 }
 else if (!Sprite) Component = UGameplayStatics::SpawnSound2D(GetWorld(), Sound, Selection.SfxVolume, FDinkAudioSelection::Pitch(Speed), 0.f, nullptr, false, !bReplay);
 if (Component && bReplay) RepeatEffects.Add(Component, FPlatformTime::Seconds());
 if (Component) { UE_LOG(LogDinkPlayback, Log, TEXT("Playing approved sound %s sprite=%d pitch=%.3f repeat=%d"), *Entry->Asset, Sprite, FDinkAudioSelection::Pitch(Speed), Repeat); Effects.Add(Component); if (Sprite) EffectSprites.Add(Component, Sprite); }
}
void UDinkAudioSubsystem::Tick(float DeltaTime)
{
 UDinkDirector* Director = BoundDirector.Get();
 if (!Director && GetWorld()->GetGameInstance())
  if (UDinkStorySubsystem* Story = GetWorld()->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>()) Director = Story->GetDirector();
 if (Director && CanPlay())
 {
  BoundDirector = Director;
  const ADinkScreenVolume* Screen = GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>()->GetCurrentScreen();
  TSet<int32> Wanted;
  for (const auto& Pair : Director->GetSprites())
  {
   const FDinkSprite& Sprite = Pair.Value;
   const int32 Id = Sprite.GetProp(TEXT("sound"));
   if (!Sprite.bActive || !Sprite.Actor.IsValid() || Id <= 0 || !Selection.Sounds.Contains(FString::FromInt(Id)) || !Screen || Sprite.Screen != Screen->ScreenNumber) continue;
   Wanted.Add(Pair.Key);
   auto* Existing = Ambient.Find(Pair.Key);
   // a repeating ambient between two plays is alive (the effects loop below replays it in place)
   if (Existing && Existing->Key == Id && Existing->Value.IsValid() && (Existing->Value->IsPlaying() || RepeatEffects.Contains(Existing->Value.Get()))) continue;
   if (Existing && Existing->Value.IsValid()) StopEffect(Existing->Value.Get());
   const int32 Before = Effects.Num();
   HandleCue(FString::Printf(TEXT("sound:%d speed=22050 sprite=%d repeat=1"), Id, Pair.Key), Director);
   if (Effects.Num() > Before) Ambient.Add(Pair.Key, TPair<int32, TWeakObjectPtr<UAudioComponent>>(Id, Effects.Last().Get()));
  }
  for (auto It = Ambient.CreateIterator(); It; ++It)
   if (!Wanted.Contains(It.Key())) { if (It.Value().Value.IsValid()) StopEffect(It.Value().Value.Get()); It.RemoveCurrent(); }
 }
 if (CanPlay()) UpdateVoices(Director);
 for (int32 I = Effects.Num() - 1; I >= 0; --I)
 {
  UAudioComponent* C = Effects[I];
  if (double* Started = IsValid(C) && !C->IsPlaying() ? RepeatEffects.Find(C) : nullptr)
  {
   // a repeating cue: again from the start, once a full length has passed since the last start (no per-frame replay of a culled one)
   const double Now = FPlatformTime::Seconds();
   if (FDinkAudioSelection::ReplayDue(Now, *Started, C->Sound ? C->Sound->GetDuration() / FMath::Max(C->PitchMultiplier, .01f) : 0.f)) { C->Play(); *Started = Now; }
   continue;
  }
  if (!IsValid(C) || !C->IsPlaying()) { EffectSprites.Remove(C); Effects.RemoveAtSwap(I); continue; }
  if (const int32* Handle = EffectSprites.Find(C); Handle && Director)
  {
   const FDinkSprite* Sprite = Director->FindSprite(*Handle);
   if (!Sprite || !Sprite->bActive) { StopEffect(C); EffectSprites.Remove(C); Effects.RemoveAtSwap(I); }
  }
 }
}
TStatId UDinkAudioSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkAudioSubsystem, STATGROUP_Tickables); }

namespace
{
FAutoConsoleCommandWithWorld DinkAudioStatus(TEXT("dink.Audio"), TEXT("Show approved music and active local effect count."), FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
{
 if (UDinkAudioSubsystem* Audio = World ? World->GetSubsystem<UDinkAudioSubsystem>() : nullptr)
  UE_LOG(LogDinkPlayback, Log, TEXT("Audio music=%s effects=%d approved_sfx=%d voice_lines=%d voices_playing=%d last_voice=%s"), *Audio->GetPlayingMusicAsset(), Audio->GetEffectCount(), Audio->GetSelection().Sounds.Num(), Audio->GetVoices().Lines.Num(), Audio->GetVoiceCount(), *Audio->GetLastVoiceLine());
}));
}
