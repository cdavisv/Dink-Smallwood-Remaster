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
bool UDinkAudioSubsystem::DoesSupportWorldType(EWorldType::Type Type) const { return Type == EWorldType::Game || Type == EWorldType::PIE; }
void UDinkAudioSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
 Super::Initialize(Collection);
 Collection.InitializeDependency<UDinkGreyboxSubsystem>();
 Selection.Load(FPaths::ProjectContentDir() / TEXT("Dink/Data/Audio/approved.json"));
 GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>()->OnScreenChanged.AddUObject(this, &UDinkAudioSubsystem::EnterScreen);
}
bool UDinkAudioSubsystem::CanPlay() const { return GetWorld() && GetWorld()->GetAudioDevice().IsValid() && !IsRunningDedicatedServer(); }
void UDinkAudioSubsystem::StopAll()
{
 if (Music) { Music->Stop(); Music->DestroyComponent(); } Music = nullptr; PlayingMusic.Reset();
 for (UAudioComponent* Effect : Effects) if (Effect) Effect->Stop();
 Effects.Reset(); Ambient.Reset(); EffectSprites.Reset();
}
void UDinkAudioSubsystem::Deinitialize()
{
 if (UDinkGreyboxSubsystem* Greybox = GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>()) Greybox->OnScreenChanged.RemoveAll(this);
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
  { C->Stop(); Effects.RemoveAtSwap(I); }
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
 if (Repeat != 0 && !Entry->bLoop)
 {
  if (USoundWave* Wave = Cast<USoundWave>(Sound)) { USoundWave* Loop = DuplicateObject<USoundWave>(Wave, this); Loop->bLooping = true; Sound = Loop; }
 }
 UAudioComponent* Component = nullptr;
 if (Actor && Actor->GetRootComponent())
 {
  USoundAttenuation* Attenuation = NewObject<USoundAttenuation>(this);
  Attenuation->Attenuation.AttenuationShapeExtents = FVector(150.f); Attenuation->Attenuation.FalloffDistance = 2200.f;
  Component = UGameplayStatics::SpawnSoundAttached(Sound, Actor->GetRootComponent(), NAME_None, FVector::ZeroVector, EAttachLocation::KeepRelativeOffset, true, Selection.SfxVolume, FDinkAudioSelection::Pitch(Speed), 0.f, Attenuation, nullptr, true);
 }
 else if (!Sprite) Component = UGameplayStatics::SpawnSound2D(GetWorld(), Sound, Selection.SfxVolume, FDinkAudioSelection::Pitch(Speed));
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
   if (Existing && Existing->Key == Id && Existing->Value.IsValid() && Existing->Value->IsPlaying()) continue;
   if (Existing && Existing->Value.IsValid()) Existing->Value->Stop();
   const int32 Before = Effects.Num();
   HandleCue(FString::Printf(TEXT("sound:%d speed=22050 sprite=%d repeat=1"), Id, Pair.Key), Director);
   if (Effects.Num() > Before) Ambient.Add(Pair.Key, TPair<int32, TWeakObjectPtr<UAudioComponent>>(Id, Effects.Last().Get()));
  }
  for (auto It = Ambient.CreateIterator(); It; ++It)
   if (!Wanted.Contains(It.Key())) { if (It.Value().Value.IsValid()) It.Value().Value->Stop(); It.RemoveCurrent(); }
 }
 for (int32 I = Effects.Num() - 1; I >= 0; --I)
 {
  UAudioComponent* C = Effects[I];
  if (!IsValid(C) || !C->IsPlaying()) { EffectSprites.Remove(C); Effects.RemoveAtSwap(I); continue; }
  if (const int32* Handle = EffectSprites.Find(C); Handle && Director)
  {
   const FDinkSprite* Sprite = Director->FindSprite(*Handle);
   if (!Sprite || !Sprite->bActive) { C->Stop(); EffectSprites.Remove(C); Effects.RemoveAtSwap(I); }
  }
 }
}
TStatId UDinkAudioSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkAudioSubsystem, STATGROUP_Tickables); }

namespace
{
FAutoConsoleCommandWithWorld DinkAudioStatus(TEXT("dink.Audio"), TEXT("Show approved music and active local effect count."), FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
{
 if (UDinkAudioSubsystem* Audio = World ? World->GetSubsystem<UDinkAudioSubsystem>() : nullptr)
  UE_LOG(LogDinkPlayback, Log, TEXT("Audio music=%s effects=%d approved_sfx=%d"), *Audio->GetPlayingMusicAsset(), Audio->GetEffectCount(), Audio->GetSelection().Sounds.Num());
}));
}
