#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Sound/SoundAttenuation.h"
#include "DinkAudioLife.generated.h"

class APawn;
class UAudioComponent;
class USoundBase;
class USoundConcurrency;
class ADinkScreenVolume;
class UDinkAudioSubsystem;
class UDinkDirector;
class UDinkStorySubsystem;
class UDinkWarpComponent;

/**
 * Mixing rules of the remaster's sound, in one place and testable without an audio device (Dink.Audio.Mix).
 *
 * 1997 (dink.cpp): an effect tied to a sprite loses 4 centibels per pixel of the larger axis distance from DINK (get_vol,
 * 6368-6389; nothing within 25 px, -24 dB at 600 px, floor -100 dB) and is panned by its x against the screen centre (get_pan,
 * 6339-6366). The remaster used the engine's default listener, the camera 2.4-6.5 m away from Dink, with a linear falloff from
 * there: a sprite beside Dink was already attenuated by the camera's distance. Now distance is measured from Dink (the player
 * controller's attenuation override, set by UDinkAudioLifeSubsystem) on the 1997 curve (dB falling linearly with distance), and
 * panning stays the camera's, which is the screen's view.
 */
struct DINKNARRATIVE_API FDinkAudioMix
{
	// The 1997 curve at the outdoor scale of 4.38 cm per pixel (the common screen scale): -24 dB over 600 px = 2630 cm.
	static constexpr float EffectInnerCm = 150.f;
	static constexpr float EffectFalloffCm = 2600.f;
	static constexpr float EffectDbAtMax = -24.f;
	// Speech stays intelligible across a screen (the dialogue box shows it anyway): -12 dB at 30 m.
	static constexpr float VoiceInnerCm = 600.f;
	static constexpr float VoiceFalloffCm = 3000.f;
	static constexpr float VoiceDbAtMax = -12.f;
	// Music crossfades instead of cutting (1997's playmidi cut the MIDI; a recorded score cut mid-phrase sounds broken).
	static constexpr float MusicFadeInS = 1.0f;
	static constexpr float MusicFadeOutS = 1.5f;
	static constexpr float MusicStopFadeS = 0.6f;
	/** At most this many instances of one one-shot effect at once; a new one stops the oldest (a burst of hits, pig grunts, soak). Repeating cues are exempt. */
	static constexpr int32 MaxSameEffect = 4;
	/** Master limiter: peaks above this are held down (recorded 15 Nov: the fireplace loop panned hard right reached 0 dBFS). */
	static constexpr float LimiterCeilingDb = -1.5f;
	/** Its detector is a brickwall: the engine's "Peak" envelope is a one-pole smoothing of |x|, so with any attack time it lags
	 *  a transient and the peak passes (recorded 16 Nov, runs A2 and C: the -1.5 dBFS limiter with a 1 ms attack let the output
	 *  sit at 0 dBFS in the soak). With a zero attack the envelope is |x| itself and with no look-ahead the gain applies to the
	 *  same sample, so no sample can leave above the ceiling; the digital release recovers in 80 ms.
	 *  Dink.Audio.MasterLimiterHoldsCeiling runs the engine's FDynamicsProcessor with these values. */
	static constexpr bool bLimiterAnalog = false;
	static constexpr float LimiterLookAheadMs = 0.f;
	static constexpr float LimiterAttackMs = 0.f;
	static constexpr float LimiterReleaseMs = 80.f;

	static void Effect(FSoundAttenuationSettings& S);
	static void Voice(FSoundAttenuationSettings& S);
	/** 1997 get_vol in dB for a sprite DxPixels, DyPixels away from Dink. */
	static float Db1997(double DxPixels, double DyPixels);
	/** UE NaturalSound curve with the effect settings, in dB, at DistanceCm from Dink (for the test against Db1997). */
	static float DbEffect(double DistanceCm);
	/** playsound(sound, min, plus, ...) / SoundPlayEffect: the frequency is RandomRange(min, min + plus) (dink.cpp:6620). */
	static int32 Frequency(int32 Min, int32 Plus, FRandomStream& Random) { return Plus > 0 ? Random.RandRange(Min, Min + Plus) : Min; }
};

/**
 * The status bar's counting sounds (update_status_all, dink.cpp:5835-5935), one status update at a time: the shown experience,
 * strength, defense, magic and gold walk toward the real values and every step plays a tick. The update runs only when the game
 * clock (16 ms a frame) has passed the last one by more than 100 ms (dink.cpp:17303-17346): every 7th frame, 8.6 times a second
 * (Due). The remaster's HUD shows the new
 * values at once (no counting); only the sounds are reproduced, from the facts, never writing them (the level-up itself is the
 * game's: this mirror only follows it).
 */
struct DINKNARRATIVE_API FDinkStatusTicks
{
	struct FIn
	{
		int32 Exp = 0, NextRaise = 0, Strength = 0, Defense = 0, Magic = 0, Gold = 0;
	};
	struct FTick
	{
		int32 Sound = 0, Speed = 22050;
	};
	bool bPrimed = false;
	int32 Raise = 0, Exp = 0, Strength = 0, Defense = 0, Magic = 0, Gold = 0;
	/** Shows the values without counting (game start, load, new game). */
	void Prime(const FIn& In);
	/** One status update: the sounds dink.cpp plays for it, in its order. */
	void Step(const FIn& In, TArray<FTick>& Out);
	/** 7 frames of the 60 Hz game clock: 16 ms each by the integer tick, more than 100 ms since the last update (dink.cpp:17304, 17343-17346). */
	static constexpr double PeriodSeconds = 7.0 / 60.0;
	/** Advances Clock by DeltaSeconds; true when a status update is due (at most one per call, so ticks never stack in one frame). */
	static bool Due(double& Clock, double DeltaSeconds);
};

/** Content/Dink/Data/Audio/life_data.json (Scripts/AudioQA/build_life_data.py) and life.json (register_life_audio.py). */
struct DINKNARRATIVE_API FDinkLifeTable
{
	struct FTake
	{
		FString Asset;
		float Gain = 1.f;
		USoundBase* Sound = nullptr; // resolved once at start; kept alive by UDinkAudioLifeSubsystem::LifeSounds
	};
	struct FWarpSound
	{
		int32 Sound = 7, Speed = 12000;
	};
	TMap<int32, FString> Surfaces;         // screen -> 96 letters, 12 x 8 tiles of 50 px, row by row
	TMap<int32, FName> Beds;               // screen -> sea, cave, wind, meadow, none
	TMap<FString, FWarpSound> Warps;       // map.dat warp origin (S439_P13) -> its sound
	TMap<int32, TArray<FTake>> Steps;      // surface letter -> takes
	TMap<FName, FTake> BedTakes;
	float StepVolume = .55f, BedVolume = .5f;
	bool LoadData(const FString& Filename);
	bool LoadTakes(const FString& Filename);
	/** The surface letter under engine pixel X, Y (x with the 20 px status bar) of a screen; 0 when unknown. */
	TCHAR SurfaceAt(int32 Screen, double X, double Y) const;
	FName BedOf(int32 Screen) const { const FName* B = Beds.Find(Screen); return B ? *B : FName(TEXT("none")); }
	static TCHAR SurfaceLetter(const FString& Name);
};

/**
 * Sound the 1997 engine made that no script asks for, and sound the remaster adds to make the world feel inhabited. All of it is
 * presentation: it reads the game's state and never writes it (the probe traces are unchanged; the cue journal is not written).
 *  - the status bar's counting ticks (FDinkStatusTicks), Dink's hurt grunts (hurt 15/16 at 25050-27050, dink.cpp:14706-14709),
 *    the talk menu's move and pick clicks (11 at dink.cpp:15975/16026/16033, 17 at 16158), the warp sound of a map.dat door
 *    (7 at 12000 or the warp's own sound, dink.cpp:15343-15345);
 *  - footsteps by the ground under Dink's feet (the 1997 tile class), ambience beds per screen (sea, wind, cave, meadow);
 *  - the listener: distance measured from Dink, panning from the camera (FDinkAudioMix);
 *  - QA: dink.AudioQA.Sweep plays a list of assets one by one (the coverage table's "heard" proof), dink.AudioQA.Soak stresses the
 *    audio for N seconds, dink.AudioQA.Stats prints counts, memory and the game-thread cost.
 */
UCLASS()
class DINKNARRATIVE_API UDinkAudioLifeSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	const FDinkLifeTable& GetTable() const { return Table; }
	FName GetBed() const { return CurrentBed; }
	int32 GetStepCount() const { return StepCount; }
	double GetTickMsAverage() const { return TickSamples ? TickMsTotal / TickSamples : 0.0; }

	/** Plays the assets of a plan file (lines: kind, key, asset, volume, seconds; tab separated) one after another, 2D. */
	bool StartSweep(const FString& PlanFile, float GapSeconds);
	void StartSoak(float Seconds);
	void LogStats() const;

	/** One status frame from the given facts (tests): the ticks it plays. */
	void StepStatus(const FDinkStatusTicks::FIn& In, TArray<FDinkStatusTicks::FTick>& Out) { Status.Step(In, Out); }

private:
	FDinkLifeTable Table;
	FDinkStatusTicks Status;
	FRandomStream Random;
	double StatusClock = 0.0;
	// story events already seen (they are appended in time order)
	double EventTimeMs = -1.0;
	int32 EventsAtTime = 0;
	int32 MenuInstance = 0, MenuSelected = 0;
	TWeakObjectPtr<APawn> ListenerPawn;
	FVector LastFoot = FVector::ZeroVector;
	bool bHaveFoot = false;
	double StepDistance = 0.0;
	int32 StepCount = 0, StepFoot = 0;
	FName CurrentBed = NAME_None;
	FDelegateHandle WarpHandle;
	double TickMsTotal = 0.0;
	int64 TickSamples = 0;

	struct FSweepItem
	{
		FString Kind, Key, Asset;
		float Volume = 1.f, Seconds = 1.f;
	};
	TArray<FSweepItem> Sweep;
	int32 SweepNext = 0;
	double SweepAt = 0.0;
	float SweepGap = 0.5f;
	double SoakUntil = 0.0, SoakNextCue = 0.0, SoakNextMusic = 0.0, SoakNextStats = 0.0;

	/** Every footstep and bed take, loaded once at start (no synchronous load on a screen change or a step). */
	UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> LifeSounds;
	void PreloadTakes();
	/** Master-bus peak limiter (FDinkAudioMix::LimiterCeilingDb): summed sounds and hard-panned peaks never clip the output. */
	UPROPERTY(Transient) TObjectPtr<class USoundEffectSubmixPreset> Limiter;
	void EnsureLimiter();
	UPROPERTY(Transient) TObjectPtr<UAudioComponent> Bed;
	UPROPERTY(Transient) TArray<TObjectPtr<UAudioComponent>> Fading;
	UPROPERTY(Transient) TObjectPtr<UAudioComponent> SweepComponent;
	UPROPERTY(Transient) TObjectPtr<USoundConcurrency> StepConcurrency;
	UPROPERTY(Transient) TObjectPtr<USoundAttenuation> StepAttenuation;

	UDinkStorySubsystem* GetStory() const;
	UDinkAudioSubsystem* GetAudio() const;
	bool CanPlay() const;
	void Cue(int32 Sound, int32 Speed);
	void UpdateListener();
	void UpdateEvents(UDinkStorySubsystem* Story);
	void UpdateStatus(UDinkStorySubsystem* Story, float DeltaTime);
	void UpdateMenu(UDinkStorySubsystem* Story);
	void UpdateSteps(UDinkStorySubsystem* Story);
	void EnterScreen(ADinkScreenVolume* Screen);
	void SetBed(FName Name);
	void HandleWarped(APawn* Pawn, const UDinkWarpComponent& Warp);
	void UpdateSweep();
	void UpdateSoak(UDinkStorySubsystem* Story);
	void ReapFading();
};
