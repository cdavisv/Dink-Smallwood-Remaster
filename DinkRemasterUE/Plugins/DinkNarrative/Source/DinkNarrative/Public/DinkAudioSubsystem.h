#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkAudioSubsystem.generated.h"
class UAudioComponent;
class ADinkScreenVolume;
class UDinkDirector;
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
 const FDinkAudioSelection& GetSelection() const { return Selection; }
 const FString& GetPlayingMusicAsset() const { return PlayingMusic; }
 int32 GetEffectCount() const { return Effects.Num(); }
private:
 FDinkAudioSelection Selection;
 FString PlayingMusic;
 TWeakObjectPtr<UDinkDirector> BoundDirector;
 TMap<TWeakObjectPtr<UAudioComponent>, int32> EffectSprites;
 TMap<int32, TPair<int32, TWeakObjectPtr<UAudioComponent>>> Ambient;
 UPROPERTY(Transient) TObjectPtr<UAudioComponent> Music;
 UPROPERTY(Transient) TArray<TObjectPtr<UAudioComponent>> Effects;
 void EnterScreen(ADinkScreenVolume* Screen);
 void PlayMusic(const FDinkApprovedSound& Entry);
 bool CanPlay() const;
};
