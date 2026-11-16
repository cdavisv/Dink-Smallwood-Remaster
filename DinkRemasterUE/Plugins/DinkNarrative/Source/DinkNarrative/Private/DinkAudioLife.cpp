#include "DinkAudioLife.h"
#include "DinkAudioSubsystem.h"
#include "DinkCombat.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"
#include "AudioDevice.h"
#include "AudioMixerBlueprintLibrary.h"
#include "SubmixEffects/AudioMixerSubmixEffectDynamicsProcessor.h"
#include "Components/AudioComponent.h"
#include "Components/CapsuleComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMemory.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundConcurrency.h"
#include "UObject/UObjectIterator.h"

DEFINE_LOG_CATEGORY_STATIC(LogDinkAudioLife, Log, All);

static TAutoConsoleVariable<int32> CVarDinkAudioLife(TEXT("dink.Audio.Life"), 1,
	TEXT("1 = footsteps and ambience beds (remaster additions; 0 = off, the bed fades out). The 1997 engine sounds (status ticks, grunts, menu clicks, warps) always play."));

namespace
{
	TSharedPtr<FJsonObject> ReadJson(const FString& Filename, const TCHAR* Schema)
	{
		FString Text; TSharedPtr<FJsonObject> Root; FString Found;
		if (!FFileHelper::LoadFileToString(Text, *Filename) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid()) return nullptr;
		if (!Root->TryGetStringField(TEXT("schema"), Found) || Found != Schema) return nullptr;
		return Root;
	}
	bool ReadTake(const TSharedPtr<FJsonObject>& O, FDinkLifeTable::FTake& Out)
	{
		double Gain = 1.0;
		if (!O.IsValid() || !O->TryGetStringField(TEXT("asset"), Out.Asset) || !Out.Asset.StartsWith(TEXT("/Game/Dink/Audio/"))) return false;
		if (O->TryGetNumberField(TEXT("gain"), Gain)) Out.Gain = FMath::Clamp(float(Gain), 0.f, 4.f);
		return true;
	}
}

bool FDinkAudioSelection::LoadMix(const FString& Filename)
{
	SfxGain.Reset(); MusicGain.Reset(); VoiceGain.Reset();
	const TSharedPtr<FJsonObject> Root = ReadJson(Filename, TEXT("dink-audio-mix/1"));
	if (!Root.IsValid()) return false;
	auto Read = [&Root](const TCHAR* Field, TMap<FString, float>& Out)
	{
		const TSharedPtr<FJsonObject>* Map = nullptr;
		if (!Root->TryGetObjectField(Field, Map)) return;
		for (const auto& Pair : (*Map)->Values)
		{
			double G = 1.0;
			if (Pair.Value->TryGetNumber(G)) Out.Add(FString(Pair.Key.ToView()), FMath::Clamp(float(G), 0.f, 4.f));
		}
	};
	Read(TEXT("sfx"), SfxGain); Read(TEXT("music"), MusicGain); Read(TEXT("voice"), VoiceGain);
	return SfxGain.Num() > 0;
}

// ---------------------------------------------------------------------------------------------------------------------
// FDinkAudioMix

void FDinkAudioMix::Effect(FSoundAttenuationSettings& S)
{
	S.bAttenuate = true;
	S.bSpatialize = true;
	S.DistanceAlgorithm = EAttenuationDistanceModel::NaturalSound;
	S.AttenuationShape = EAttenuationShape::Sphere;
	S.AttenuationShapeExtents = FVector(EffectInnerCm, 0.f, 0.f);
	S.FalloffDistance = EffectFalloffCm;
	S.dBAttenuationAtMax = EffectDbAtMax;
	S.FalloffMode = ENaturalSoundFalloffMode::Continues;
}

void FDinkAudioMix::Voice(FSoundAttenuationSettings& S)
{
	Effect(S);
	S.AttenuationShapeExtents = FVector(VoiceInnerCm, 0.f, 0.f);
	S.FalloffDistance = VoiceFalloffCm;
	S.dBAttenuationAtMax = VoiceDbAtMax;
	S.FalloffMode = ENaturalSoundFalloffMode::Hold;
}

float FDinkAudioMix::Db1997(double DxPixels, double DyPixels)
{
	// get_vol (dink.cpp:6368-6389): -4 per pixel of each axis, the larger loss wins, nothing above -100, floor -10000 (centibels).
	double Vol = -4.0 * FMath::Max(FMath::Abs(DxPixels), FMath::Abs(DyPixels));
	if (Vol > -100.0) Vol = 0.0;
	return float(FMath::Max(Vol, -10000.0) / 100.0);
}

float FDinkAudioMix::DbEffect(double DistanceCm)
{
	const double Alpha = FMath::Clamp((DistanceCm - EffectInnerCm) / EffectFalloffCm, 0.0, 1.0);
	return float(EffectDbAtMax * Alpha);
}

// ---------------------------------------------------------------------------------------------------------------------
// FDinkStatusTicks

bool FDinkStatusTicks::Due(double& Clock, double DeltaSeconds)
{
	Clock += DeltaSeconds;
	if (Clock < PeriodSeconds) return false;
	Clock = FMath::Min(Clock - PeriodSeconds, PeriodSeconds);
	return true;
}

void FDinkStatusTicks::Prime(const FIn& In)
{
	bPrimed = true;
	Raise = In.NextRaise; Exp = In.Exp; Strength = In.Strength; Defense = In.Defense; Magic = In.Magic; Gold = In.Gold;
}

void FDinkStatusTicks::Step(const FIn& In, TArray<FTick>& Out)
{
	if (!bPrimed) { Prime(In); return; }
	auto Walk = [](int32& Shown, int32 Real) { Shown += Shown < Real ? 1 : -1; };
	if (In.NextRaise != Raise) // 5847-5852: the raise mark counts toward next_raise() in 40 steps
	{
		Raise += FMath::Max(1, In.NextRaise / 40);
		if (Raise > In.NextRaise) Raise = In.NextRaise;
		Out.Add({13, 15050});
	}
	if (In.Exp < Exp) Exp = In.Exp; // the level-up took the experience (5866-5870): the 1997 bar restarts at 0 silently
	if (In.Exp != Exp) // 5856-5864: ten points a frame
	{
		Exp = FMath::Min(Exp + 10, In.Exp);
		Out.Add({13, 29050});
	}
	if (In.Strength != Strength) { Walk(Strength, In.Strength); Out.Add({22, 22050}); } // 5895-5901
	if (In.Defense != Defense) { Walk(Defense, In.Defense); Out.Add({22, 22050}); }     // 5903-5909
	if (In.Magic != Magic) { Walk(Magic, In.Magic); Out.Add({22, 22050}); }             // 5911-5917
	if (In.Gold != Gold) // 5919-5933: twenty a frame
	{
		Gold = Gold < In.Gold ? FMath::Min(Gold + 20, In.Gold) : FMath::Max(Gold - 20, In.Gold);
		Out.Add({14, 22050});
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// FDinkLifeTable

TCHAR FDinkLifeTable::SurfaceLetter(const FString& Name)
{
	static const TMap<FString, TCHAR> Letters = {{TEXT("grass"), 'g'}, {TEXT("dirt"), 'd'}, {TEXT("sand"), 's'}, {TEXT("wood"), 'w'},
		{TEXT("stone"), 't'}, {TEXT("snow"), 'n'}, {TEXT("water"), 'a'}};
	const TCHAR* L = Letters.Find(Name);
	return L ? *L : 0;
}

bool FDinkLifeTable::LoadData(const FString& Filename)
{
	Surfaces.Reset(); Beds.Reset(); Warps.Reset();
	const TSharedPtr<FJsonObject> Root = ReadJson(Filename, TEXT("dink-audio-life/1"));
	const TSharedPtr<FJsonObject>* Map = nullptr;
	if (!Root.IsValid() || !Root->TryGetObjectField(TEXT("screens"), Map)) return false;
	for (const auto& Pair : (*Map)->Values)
	{
		const TSharedPtr<FJsonObject>* S = nullptr;
		if (!Pair.Value->TryGetObject(S)) continue;
		const int32 Screen = FCString::Atoi(*FString(Pair.Key.ToView()));
		FString Surface, Bed;
		if ((*S)->TryGetStringField(TEXT("surface"), Surface) && Surface.Len() == 96) Surfaces.Add(Screen, Surface);
		if ((*S)->TryGetStringField(TEXT("ambience"), Bed)) Beds.Add(Screen, FName(*Bed));
	}
	if (Root->TryGetObjectField(TEXT("warps"), Map))
	{
		for (const auto& Pair : (*Map)->Values)
		{
			const TSharedPtr<FJsonObject>* W = nullptr;
			if (!Pair.Value->TryGetObject(W)) continue;
			FWarpSound Sound;
			(*W)->TryGetNumberField(TEXT("sound"), Sound.Sound);
			(*W)->TryGetNumberField(TEXT("speed"), Sound.Speed);
			Warps.Add(FString(Pair.Key.ToView()), Sound);
		}
	}
	return Surfaces.Num() > 0;
}

bool FDinkLifeTable::LoadTakes(const FString& Filename)
{
	Steps.Reset(); BedTakes.Reset();
	const TSharedPtr<FJsonObject> Root = ReadJson(Filename, TEXT("dink-audio-life/1"));
	if (!Root.IsValid()) return false;
	const TSharedPtr<FJsonObject>* Map = nullptr;
	if (Root->TryGetObjectField(TEXT("volumes"), Map))
	{
		double V = 0.0;
		if ((*Map)->TryGetNumberField(TEXT("steps"), V)) StepVolume = FMath::Clamp(float(V), 0.f, 1.f);
		if ((*Map)->TryGetNumberField(TEXT("beds"), V)) BedVolume = FMath::Clamp(float(V), 0.f, 1.f);
	}
	if (Root->TryGetObjectField(TEXT("steps"), Map))
	{
		for (const auto& Pair : (*Map)->Values)
		{
			const TCHAR Letter = SurfaceLetter(FString(Pair.Key.ToView()));
			const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
			if (!Letter || !Pair.Value->TryGetArray(Rows)) continue;
			for (const TSharedPtr<FJsonValue>& Row : *Rows)
			{
				FTake Take;
				if (ReadTake(Row->AsObject(), Take)) Steps.FindOrAdd(int32(Letter)).Add(Take);
			}
		}
	}
	if (Root->TryGetObjectField(TEXT("beds"), Map))
	{
		for (const auto& Pair : (*Map)->Values)
		{
			FTake Take;
			const TSharedPtr<FJsonObject>* O = nullptr;
			if (Pair.Value->TryGetObject(O) && ReadTake(*O, Take)) BedTakes.Add(FName(FString(Pair.Key.ToView())), Take);
		}
	}
	return Steps.Num() > 0 || BedTakes.Num() > 0;
}

TCHAR FDinkLifeTable::SurfaceAt(int32 Screen, double X, double Y) const
{
	const FString* S = Surfaces.Find(Screen);
	if (!S) return 0;
	const int32 Col = FMath::Clamp(FMath::FloorToInt32((X - 20.0) / 50.0), 0, 11);
	const int32 Row = FMath::Clamp(FMath::FloorToInt32(Y / 50.0), 0, 7);
	return (*S)[Row * 12 + Col];
}

// ---------------------------------------------------------------------------------------------------------------------
// UDinkAudioLifeSubsystem

bool UDinkAudioLifeSubsystem::DoesSupportWorldType(EWorldType::Type Type) const { return Type == EWorldType::Game || Type == EWorldType::PIE; }
TStatId UDinkAudioLifeSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkAudioLifeSubsystem, STATGROUP_Tickables); }

void UDinkAudioLifeSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	Collection.InitializeDependency<UDinkGreyboxSubsystem>();
	Collection.InitializeDependency<UDinkAudioSubsystem>();
	const FString Dir = FPaths::ProjectContentDir() / TEXT("Dink/Data/Audio/");
	const bool bData = Table.LoadData(Dir + TEXT("life_data.json"));
	const bool bTakes = Table.LoadTakes(Dir + TEXT("life.json"));
	UE_LOG(LogDinkAudioLife, Log, TEXT("Audio life: %d screens, %d warps, %d step surfaces, %d beds (data %s, takes %s)"), Table.Surfaces.Num(), Table.Warps.Num(),
		Table.Steps.Num(), Table.BedTakes.Num(), bData ? TEXT("ok") : TEXT("missing"), bTakes ? TEXT("ok") : TEXT("missing"));
	Random.Initialize(int32(FPlatformTime::Cycles() & 0x7fffffff));
	PreloadTakes();
	if (UDinkGreyboxSubsystem* Greybox = GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>())
	{
		Greybox->OnScreenChanged.AddUObject(this, &UDinkAudioLifeSubsystem::EnterScreen);
		WarpHandle = Greybox->OnWarped.AddUObject(this, &UDinkAudioLifeSubsystem::HandleWarped);
	}
}

void UDinkAudioLifeSubsystem::Deinitialize()
{
	if (UDinkGreyboxSubsystem* Greybox = GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>())
	{
		Greybox->OnScreenChanged.RemoveAll(this);
		Greybox->OnWarped.Remove(WarpHandle);
	}
	if (Bed) Bed->Stop();
	for (UAudioComponent* C : Fading) if (IsValid(C)) C->Stop();
	if (SweepComponent) SweepComponent->Stop();
	Bed = nullptr; Fading.Reset(); SweepComponent = nullptr;
	Super::Deinitialize();
}

void UDinkAudioLifeSubsystem::PreloadTakes()
{
	int32 Missing = 0;
	auto Resolve = [&](FDinkLifeTable::FTake& Take)
	{
		Take.Sound = LoadObject<USoundBase>(nullptr, *Take.Asset, nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (Take.Sound) LifeSounds.Add(Take.Sound);
		else { ++Missing; UE_LOG(LogDinkAudioLife, Warning, TEXT("Audio life: take %s is not imported (Scripts/AudioQA/import_life_audio.sh); dropped"), *Take.Asset); }
		return Take.Sound == nullptr;
	};
	for (auto& Pair : Table.Steps) Pair.Value.RemoveAll(Resolve);
	for (auto It = Table.BedTakes.CreateIterator(); It; ++It) if (Resolve(It.Value())) It.RemoveCurrent();
	UE_LOG(LogDinkAudioLife, Log, TEXT("Audio life: %d takes loaded, %d missing"), LifeSounds.Num(), Missing);
}

UDinkStorySubsystem* UDinkAudioLifeSubsystem::GetStory() const
{
	UGameInstance* Instance = GetWorld() ? GetWorld()->GetGameInstance() : nullptr;
	return Instance ? Instance->GetSubsystem<UDinkStorySubsystem>() : nullptr;
}
UDinkAudioSubsystem* UDinkAudioLifeSubsystem::GetAudio() const { return GetWorld() ? GetWorld()->GetSubsystem<UDinkAudioSubsystem>() : nullptr; }
bool UDinkAudioLifeSubsystem::CanPlay() const { return GetWorld() && GetWorld()->GetAudioDevice().IsValid() && !IsRunningDedicatedServer(); }

void UDinkAudioLifeSubsystem::Cue(int32 Sound, int32 Speed)
{
	// Unpositioned, as SoundPlayEffect(n, speed, 0, 0, 0) plays it; through the playback path, not the cue journal (presentation).
	if (UDinkAudioSubsystem* Audio = GetAudio()) Audio->HandleCue(FString::Printf(TEXT("sound:%d speed=%d sprite=0 repeat=0"), Sound, Speed), nullptr);
}

void UDinkAudioLifeSubsystem::Tick(float DeltaTime)
{
	const double T0 = FPlatformTime::Seconds();
	ReapFading();
	if (Sweep.Num() > 0)
	{
		UpdateSweep();
	}
	else if (CanPlay())
	{
		if (CVarDinkAudioLife.GetValueOnGameThread() == 0 && CurrentBed != NAME_None) SetBed(NAME_None);
		EnsureLimiter();
		UpdateListener();
		UDinkStorySubsystem* Story = GetStory();
		if (Story && Story->IsReady() && Story->GetDirector())
		{
			UpdateEvents(Story);
			UpdateStatus(Story, DeltaTime);
			UpdateMenu(Story);
			UpdateSteps(Story);
			UpdateSoak(Story);
		}
	}
	TickMsTotal += (FPlatformTime::Seconds() - T0) * 1000.0;
	++TickSamples;
}

void UDinkAudioLifeSubsystem::EnsureLimiter()
{
	if (Limiter) return;
	USubmixEffectDynamicsProcessorPreset* Preset = NewObject<USubmixEffectDynamicsProcessorPreset>(this);
	FSubmixEffectDynamicsProcessorSettings S = Preset->Settings;
	S.DynamicsProcessorType = ESubmixEffectDynamicsProcessorType::Limiter;
	S.PeakMode = ESubmixEffectDynamicsPeakMode::Peak;
	S.LinkMode = ESubmixEffectDynamicsChannelLinkMode::Peak;
	S.ThresholdDb = FDinkAudioMix::LimiterCeilingDb;
	S.LookAheadMsec = FDinkAudioMix::LimiterLookAheadMs;
	S.AttackTimeMsec = FDinkAudioMix::LimiterAttackMs;
	S.ReleaseTimeMsec = FDinkAudioMix::LimiterReleaseMs;
	S.KneeBandwidthDb = 0.f;
	S.bAnalogMode = FDinkAudioMix::bLimiterAnalog;
	S.InputGainDb = 0.f;
	S.OutputGainDb = 0.f;
	Preset->SetSettings(S);
	UAudioMixerBlueprintLibrary::AddMasterSubmixEffect(this, Preset);
	Limiter = Preset;
	UE_LOG(LogDinkAudioLife, Log, TEXT("Audio: master limiter at %.1f dBFS"), FDinkAudioMix::LimiterCeilingDb);
}

void UDinkAudioLifeSubsystem::UpdateListener()
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!Pawn || Pawn == ListenerPawn.Get()) return;
	// Distance from Dink (1997 get_vol), direction from the camera (the view of the screen).
	PC->SetAudioListenerAttenuationOverride(Pawn->GetRootComponent(), FVector::ZeroVector);
	ListenerPawn = Pawn;
	UE_LOG(LogDinkAudioLife, Log, TEXT("Audio listener: attenuation measured from %s, panning from the camera"), *Pawn->GetName());
}

void UDinkAudioLifeSubsystem::UpdateEvents(UDinkStorySubsystem* Story)
{
	const TArray<FDinkNarrativeEvent>& Ev = Story->Events;
	auto Mark = [&]()
	{
		EventsAtTime = 0;
		EventTimeMs = Ev.Num() ? Ev.Last().TimeMs : -1.0;
		for (int32 J = Ev.Num() - 1; J >= 0 && Ev[J].TimeMs == EventTimeMs; --J) ++EventsAtTime;
	};
	if (EventTimeMs < 0.0 || (Ev.Num() && Ev.Last().TimeMs < EventTimeMs)) { Mark(); Status.bPrimed = false; return; } // first look, or a new game restarted the clock
	int32 I = Ev.Num();
	while (I > 0 && Ev[I - 1].TimeMs >= EventTimeMs) --I;
	int32 Skip = EventsAtTime;
	static const FName Game(TEXT("game")), Load(TEXT("load")), Choose(TEXT("choose")), Respawn(TEXT("respawn"));
	for (int32 J = I; J < Ev.Num(); ++J)
	{
		const FDinkNarrativeEvent& E = Ev[J];
		if (E.TimeMs == EventTimeMs && Skip > 0) { --Skip; continue; }
		if (E.Kind == Game && E.Text.StartsWith(TEXT("dink -")) && E.Text.EndsWith(TEXT(" life")))
		{
			// human_brain took damage (dink.cpp:14706-14709): grunt 15 or 16, SoundPlayEffect(n, 25050, 2000): 25050-27050 Hz.
			// The pick is presentation's own random, not the game's rand() (the simulation's sequence stays the probe's).
			Cue(Random.RandRange(15, 16), FDinkAudioMix::Frequency(25050, 2000, Random));
		}
		else if (E.Kind == Choose)
		{
			Cue(17, 22050); // talk menu pick (dink.cpp:16158)
			MenuInstance = 0; // a menu the same script opens next is a new one (no move click for it)
		}
		else if (E.Kind == Load || E.Kind == Respawn || (E.Kind == Game && E.Text.StartsWith(TEXT("new game"))))
		{
			Status.bPrimed = false; // the bar shows the loaded values at once
		}
	}
	Mark();
}

void UDinkAudioLifeSubsystem::UpdateStatus(UDinkStorySubsystem* Story, float DeltaTime)
{
	const UDinkFactSubsystem* Facts = Story->GetFacts();
	if (!Facts) return;
	FDinkStatusTicks::FIn In;
	In.Exp = Facts->GetFact(TEXT("exp"));
	In.NextRaise = DinkRules::ExpForNextLevel(FMath::Max(1, Facts->GetFact(TEXT("level"))));
	In.Strength = Facts->GetFact(TEXT("strength"));
	In.Defense = Facts->GetFact(TEXT("defense"));
	In.Magic = Facts->GetFact(TEXT("magic"));
	In.Gold = Facts->GetFact(TEXT("gold"));
	if (!Status.bPrimed) { Status.Prime(In); StatusClock = 0.0; return; }
	if (!FDinkStatusTicks::Due(StatusClock, DeltaTime)) return; // 8.6 updates a second, as the 1997 status timer
	TArray<FDinkStatusTicks::FTick> Ticks;
	Status.Step(In, Ticks);
	for (const FDinkStatusTicks::FTick& T : Ticks) Cue(T.Sound, T.Speed);
}

void UDinkAudioLifeSubsystem::UpdateMenu(UDinkStorySubsystem* Story)
{
	const FDinkMenu* Menu = Story->GetActiveMenu();
	if (!Menu) { MenuInstance = 0; return; }
	if (Menu->InstanceId == MenuInstance && Menu->Selected != MenuSelected) Cue(11, 22050); // the highlight moved (dink.cpp:15975, 16026, 16033)
	MenuInstance = Menu->InstanceId;
	MenuSelected = Menu->Selected;
}

void UDinkAudioLifeSubsystem::UpdateSteps(UDinkStorySubsystem* Story)
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	ACharacter* Hero = PC ? Cast<ACharacter>(PC->GetPawn()) : nullptr;
	if (!Hero || !Hero->GetCharacterMovement() || !Hero->GetCapsuleComponent() || CVarDinkAudioLife.GetValueOnGameThread() == 0) { bHaveFoot = false; return; }
	const FVector Foot = Hero->GetActorLocation() - FVector(0.0, 0.0, Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
	const double Moved = bHaveFoot ? FVector::Dist2D(Foot, LastFoot) : 0.0;
	LastFoot = Foot;
	bHaveFoot = true;
	const double Speed = Hero->GetVelocity().Size2D();
	if (Moved > 300.0 || !Hero->GetCharacterMovement()->IsMovingOnGround() || Speed < 30.0) { StepDistance = 0.0; return; } // warped, airborne or standing
	StepDistance += Moved;
	const double Stride = FMath::Clamp(Speed * 0.45, 50.0, 110.0); // about 70 cm a step at a 1.5 m/s walk
	if (StepDistance < Stride) return;
	StepDistance -= Stride;
	const FDinkSprite* Dink = static_cast<const UDinkDirector*>(Story->GetDirector())->FindSprite(1);
	if (!Dink) return;
	TCHAR Surface = Table.SurfaceAt(Dink->Screen, Dink->X, Dink->Y);
	if (Surface == '-' || Surface == 0) Surface = 't';
	const TArray<FDinkLifeTable::FTake>* Takes = Table.Steps.Find(int32(Surface));
	if (!Takes || Takes->IsEmpty()) return;
	const FDinkLifeTable::FTake& Take = (*Takes)[Random.RandRange(0, Takes->Num() - 1)];
	USoundBase* Sound = Take.Sound;
	if (!Sound) return;
	if (!StepAttenuation)
	{
		StepAttenuation = NewObject<USoundAttenuation>(this);
		FDinkAudioMix::Effect(StepAttenuation->Attenuation);
		StepConcurrency = NewObject<USoundConcurrency>(this);
		StepConcurrency->Concurrency.MaxCount = 3;
		StepConcurrency->Concurrency.ResolutionRule = EMaxConcurrentResolutionRule::StopOldest;
	}
	StepFoot ^= 1;
	const FVector Side = Hero->GetActorRightVector() * (StepFoot ? 10.0 : -10.0);
	UGameplayStatics::PlaySoundAtLocation(this, Sound, Foot + Side, Take.Gain * Table.StepVolume, Random.FRandRange(.94f, 1.06f), 0.f, StepAttenuation, StepConcurrency);
	++StepCount;
	UE_LOG(LogDinkAudioLife, Verbose, TEXT("Step %c on SCR_%03d at %.0f,%.0f: %s"), Surface, Dink->Screen, Dink->X, Dink->Y, *Take.Asset);
}

void UDinkAudioLifeSubsystem::EnterScreen(ADinkScreenVolume* Screen)
{
	if (Screen && Sweep.IsEmpty()) SetBed(CVarDinkAudioLife.GetValueOnGameThread() ? Table.BedOf(Screen->ScreenNumber) : FName(NAME_None));
}

void UDinkAudioLifeSubsystem::SetBed(FName Name)
{
	if (Name == CurrentBed && IsValid(Bed) && Bed->IsPlaying()) return;
	if (IsValid(Bed)) { Bed->FadeOut(2.f, 0.f); Fading.Add(Bed); }
	Bed = nullptr;
	CurrentBed = Name;
	const FDinkLifeTable::FTake* Take = Table.BedTakes.Find(Name);
	USoundBase* Sound = Take && CanPlay() ? Take->Sound : nullptr;
	if (!Sound) return;
	Bed = UGameplayStatics::CreateSound2D(this, Sound, Take->Gain * Table.BedVolume, 1.f, 0.f, nullptr, false, false);
	if (Bed)
	{
		Bed->FadeIn(2.f, 1.f, Random.FRandRange(0.f, 20.f)); // start somewhere in the loop: two screens of the same bed never sound alike
		UE_LOG(LogDinkAudioLife, Log, TEXT("Ambience bed %s: %s volume=%.3f"), *Name.ToString(), *Take->Asset, Take->Gain * Table.BedVolume);
	}
}

void UDinkAudioLifeSubsystem::HandleWarped(APawn* Pawn, const UDinkWarpComponent& Warp)
{
	// special_block (dink.cpp:15337-15345): a touched map.dat warp plays its own sound, or 7 (the door) at 12000 when it has none.
	if (const FDinkLifeTable::FWarpSound* W = Table.Warps.Find(Warp.WarpId))
	{
		Cue(W->Sound, W->Speed);
		UE_LOG(LogDinkAudioLife, Log, TEXT("Warp sound %d at %d for %s"), W->Sound, W->Speed, *Warp.WarpId);
	}
}

void UDinkAudioLifeSubsystem::ReapFading()
{
	for (int32 I = Fading.Num() - 1; I >= 0; --I)
	{
		UAudioComponent* C = Fading[I];
		if (!IsValid(C) || !C->IsPlaying()) { if (IsValid(C)) C->DestroyComponent(); Fading.RemoveAtSwap(I); }
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// QA: sweep, soak, stats

bool UDinkAudioLifeSubsystem::StartSweep(const FString& PlanFile, float GapSeconds)
{
	TArray<FString> Lines;
	if (!FFileHelper::LoadFileToStringArray(Lines, *PlanFile)) { UE_LOG(LogDinkAudioLife, Error, TEXT("AUDIOQA sweep: cannot read %s"), *PlanFile); return false; }
	Sweep.Reset();
	for (const FString& Line : Lines)
	{
		TArray<FString> F;
		Line.ParseIntoArray(F, TEXT("\t"), false);
		if (F.Num() < 5 || Line.StartsWith(TEXT("#"))) continue;
		FSweepItem Item;
		Item.Kind = F[0]; Item.Key = F[1]; Item.Asset = F[2];
		Item.Volume = FCString::Atof(*F[3]); Item.Seconds = FMath::Max(.05f, FCString::Atof(*F[4]));
		Sweep.Add(Item);
	}
	SweepNext = 0; SweepAt = FPlatformTime::Seconds() + 1.0; SweepGap = FMath::Max(.1f, GapSeconds);
	if (UDinkAudioSubsystem* Audio = GetAudio()) { Audio->StopAll(); Audio->SetSuspended(true); }
	SetBed(NAME_None);
	UE_LOG(LogDinkAudioLife, Display, TEXT("AUDIOQA sweep start: %d items from %s, gap %.2f s, device %s"), Sweep.Num(), *PlanFile, SweepGap, CanPlay() ? TEXT("yes") : TEXT("NO"));
	return Sweep.Num() > 0;
}

void UDinkAudioLifeSubsystem::UpdateSweep()
{
	const double Now = FPlatformTime::Seconds();
	if (Now < SweepAt) return;
	if (IsValid(SweepComponent)) { SweepComponent->Stop(); SweepComponent->DestroyComponent(); }
	SweepComponent = nullptr;
	if (SweepNext >= Sweep.Num())
	{
		UE_LOG(LogDinkAudioLife, Display, TEXT("AUDIOQA sweep done: %d items"), Sweep.Num());
		Sweep.Reset();
		if (UDinkAudioSubsystem* Audio = GetAudio()) Audio->SetSuspended(false);
		return;
	}
	const FSweepItem& Item = Sweep[SweepNext++];
	const double L0 = FPlatformTime::Seconds();
	USoundBase* Sound = LoadObject<USoundBase>(nullptr, *Item.Asset);
	const double LoadMs = (FPlatformTime::Seconds() - L0) * 1000.0;
	float Played = 0.f;
	if (Sound && CanPlay())
	{
		SweepComponent = UGameplayStatics::SpawnSound2D(this, Sound, Item.Volume, 1.f, 0.f, nullptr, false, false);
		Played = FMath::Min(Item.Seconds, Sound->GetDuration() > 0.f && Sound->GetDuration() < 3600.f ? Sound->GetDuration() : Item.Seconds);
	}
	UE_LOG(LogDinkAudioLife, Display, TEXT("AUDIOQA sweep %d/%d %s %s %s volume=%.3f play=%.3f load_ms=%.2f %s"), SweepNext, Sweep.Num(), *Item.Kind, *Item.Key, *Item.Asset,
		Item.Volume, Played, LoadMs, Sound ? (SweepComponent ? TEXT("playing") : TEXT("no-device")) : TEXT("MISSING"));
	SweepAt = FPlatformTime::Seconds() + Played + SweepGap;
}

void UDinkAudioLifeSubsystem::StartSoak(float Seconds)
{
	const double Now = FPlatformTime::Seconds();
	SoakUntil = Now + Seconds; SoakNextCue = Now; SoakNextMusic = Now; SoakNextStats = Now;
	UE_LOG(LogDinkAudioLife, Display, TEXT("AUDIOQA soak start: %.0f s"), Seconds);
	LogStats();
}

void UDinkAudioLifeSubsystem::UpdateSoak(UDinkStorySubsystem* Story)
{
	if (SoakUntil <= 0.0) return;
	const double Now = FPlatformTime::Seconds();
	UDinkAudioSubsystem* Audio = GetAudio();
	UDinkDirector* Director = Story->GetDirector();
	if (!Audio || !Director) return;
	if (Now >= SoakUntil)
	{
		SoakUntil = 0.0;
		LogStats();
		Audio->StopAll();
		UE_LOG(LogDinkAudioLife, Display, TEXT("AUDIOQA soak done"));
		LogStats();
		return;
	}
	TArray<FString> Ids;
	Audio->GetSelection().Sounds.GetKeys(Ids);
	if (Now >= SoakNextCue && Ids.Num())
	{
		SoakNextCue = Now + .08;
		// a positional cue on a live sprite of this screen half the time, a repeating one now and then (stopped with its owner)
		TArray<int32> Handles;
		const FDinkSprite* DinkSprite = static_cast<const UDinkDirector*>(Director)->FindSprite(1);
		const int32 Screen = DinkSprite ? DinkSprite->Screen : 0;
		for (const auto& Pair : Director->GetSprites()) if (Pair.Value.bActive && Pair.Value.Screen == Screen && Pair.Value.Actor.IsValid()) Handles.Add(Pair.Key);
		const int32 Sprite = Handles.Num() && Random.FRand() < .5f ? Handles[Random.RandRange(0, Handles.Num() - 1)] : 0;
		const int32 Repeat = Sprite && Random.FRand() < .05f ? 1 : 0;
		Audio->HandleCue(FString::Printf(TEXT("sound:%s speed=%d random=2000 sprite=%d repeat=%d"), *Ids[Random.RandRange(0, Ids.Num() - 1)], Random.RandRange(11025, 44100), Sprite, Repeat), Director);
	}
	if (Now >= SoakNextMusic)
	{
		SoakNextMusic = Now + 15.0;
		TArray<FString> Music;
		Audio->GetSelection().Music.GetKeys(Music);
		if (Music.Num()) Audio->HandleCue(TEXT("music:") + Music[Random.RandRange(0, Music.Num() - 1)], Director);
		SetBed(Random.FRand() < .5f ? FName(TEXT("sea")) : FName(TEXT("wind")));
	}
	if (Now >= SoakNextStats) { SoakNextStats = Now + 10.0; LogStats(); }
}

void UDinkAudioLifeSubsystem::LogStats() const
{
	int32 Components = 0, Playing = 0;
	for (TObjectIterator<UAudioComponent> It; It; ++It)
	{
		if (It->GetWorld() != GetWorld()) continue;
		++Components;
		Playing += It->IsPlaying() ? 1 : 0;
	}
	const UDinkAudioSubsystem* Audio = GetAudio();
	const FPlatformMemoryStats Mem = FPlatformMemory::GetStats();
	UE_LOG(LogDinkAudioLife, Display, TEXT("AUDIOQA stats components=%d playing=%d effects=%d voices=%d music=%s bed=%s fading=%d steps=%d life_tick_ms=%.4f used_physical_mb=%.1f"),
		Components, Playing, Audio ? Audio->GetEffectCount() : -1, Audio ? Audio->GetVoiceCount() : -1, Audio ? *Audio->GetPlayingMusicAsset() : TEXT("-"),
		*CurrentBed.ToString(), Fading.Num(), StepCount, GetTickMsAverage(), Mem.UsedPhysical / (1024.0 * 1024.0));
}

namespace
{
	UDinkAudioLifeSubsystem* Life(UWorld* World) { return World ? World->GetSubsystem<UDinkAudioLifeSubsystem>() : nullptr; }
#if !UE_BUILD_SHIPPING
	FAutoConsoleCommandWithWorldAndArgs DinkAudioQASweep(TEXT("dink.AudioQA.Sweep"),
		TEXT("dink.AudioQA.Sweep <plan.tsv> [gap seconds]: play every asset of a plan (kind, key, asset, volume, seconds) one by one, 2D, logging each start (Scripts/AudioQA/audio_coverage.py writes the plan)."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UDinkAudioLifeSubsystem* L = Life(World); L && Args.Num() > 0) L->StartSweep(Args[0], Args.Num() > 1 ? FCString::Atof(*Args[1]) : .6f);
		}));
	FAutoConsoleCommandWithWorldAndArgs DinkAudioQASoak(TEXT("dink.AudioQA.Soak"), TEXT("dink.AudioQA.Soak <seconds>: fire a random sound cue every 80 ms (half on live sprites, some repeating), change music every 15 s, log stats every 10 s."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UDinkAudioLifeSubsystem* L = Life(World)) L->StartSoak(Args.Num() > 0 ? FCString::Atof(*Args[0]) : 600.f);
		}));
#endif
	FAutoConsoleCommandWithWorld DinkAudioQAStats(TEXT("dink.AudioQA.Stats"), TEXT("Audio components, playing sounds, music, bed, steps, game-thread cost, memory."),
		FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World) { if (UDinkAudioLifeSubsystem* L = Life(World)) L->LogStats(); }));
}
