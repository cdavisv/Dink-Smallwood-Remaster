// Audio QA (15 Nov 2026): the mixing rules against dink.cpp, the status bar's counting ticks, the footstep / ambience / warp tables,
// and that every sound the presentation layer reproduces from the 1997 engine has an approved take. The rendered runs with a
// recorded device (Scripts/AudioQA/, Docs/Verification/AudioQA_15Nov2026) are the end-to-end proof; these pin the rules.
#include "DinkTestHelpers.h"
#include "DinkAudioLife.h"
#include "DinkAudioSubsystem.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "DSP/DynamicsProcessor.h"
#include "Sound/SoundEffectSubmix.h"
#include "SubmixEffects/AudioMixerSubmixEffectDynamicsProcessor.h"
#include "UObject/StrongObjectPtr.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAudioMixTest, "Dink.Audio.MixFollows1997Curve", DINK_TEST_FLAGS)
bool FDinkAudioMixTest::RunTest(const FString&)
{
	// get_vol (dink.cpp:6368-6389): nothing within 25 px, -4 cB per pixel of the larger axis, floor -100 dB.
	TestEqual(TEXT("10 px: full volume"), FDinkAudioMix::Db1997(10, 0), 0.f);
	TestEqual(TEXT("300 px: -12 dB"), FDinkAudioMix::Db1997(300, 40), -12.f);
	TestEqual(TEXT("the larger axis counts"), FDinkAudioMix::Db1997(-100, 600), -24.f);
	TestEqual(TEXT("floor"), FDinkAudioMix::Db1997(5000, 0), -100.f);
	// The remaster's curve at the outdoor scale (4.38 cm per pixel) stays within 3 dB of the original from beside Dink to a screen away.
	for (const double Px : {30.0, 60.0, 100.0, 200.0, 300.0, 450.0, 600.0})
	{
		const float Remaster = FDinkAudioMix::DbEffect(Px * 4.38), Original = FDinkAudioMix::Db1997(Px, 0);
		TestTrue(FString::Printf(TEXT("%.0f px: remaster %.1f dB vs 1997 %.1f dB"), Px, Remaster, Original), FMath::Abs(Remaster - Original) <= 3.f);
	}
	FSoundAttenuationSettings Effect, Voice;
	FDinkAudioMix::Effect(Effect); FDinkAudioMix::Voice(Voice);
	TestTrue(TEXT("effects: dB falloff (NaturalSound), spatialised"), Effect.DistanceAlgorithm == EAttenuationDistanceModel::NaturalSound && Effect.bSpatialize && Effect.bAttenuate);
	TestTrue(TEXT("speech carries further than effects"), Voice.AttenuationShapeExtents.X > Effect.AttenuationShapeExtents.X && Voice.dBAttenuationAtMax > Effect.dBAttenuationAtMax);
	TestTrue(TEXT("music crossfades"), FDinkAudioMix::MusicFadeInS > 0.f && FDinkAudioMix::MusicFadeOutS > 0.f);
	// playsound(n, min, plus, ...): RandomRange(min, min + plus) (dink.cpp:6620); the remaster ignored plus before.
	FRandomStream R(7);
	TestEqual(TEXT("no plus: the speed itself"), FDinkAudioMix::Frequency(22050, 0, R), 22050);
	int32 Lo = TNumericLimits<int32>::Max(), Hi = 0;
	for (int32 I = 0; I < 200; ++I) { const int32 F = FDinkAudioMix::Frequency(25050, 2000, R); Lo = FMath::Min(Lo, F); Hi = FMath::Max(Hi, F); }
	TestTrue(FString::Printf(TEXT("hurt grunt pitch spread 25050-27050 (got %d-%d)"), Lo, Hi), Lo >= 25050 && Hi <= 27050 && Hi - Lo > 1000);
	// Loudness gains (Scripts/AudioQA/build_mix.py): one per approved effect and music take, none extreme.
	FDinkAudioSelection Selection;
	TestTrue(TEXT("approved.json loads"), Selection.Load(FPaths::ProjectContentDir() / TEXT("Dink/Data/Audio/approved.json")));
	TestTrue(TEXT("mix.json loads"), Selection.LoadMix(FPaths::ProjectContentDir() / TEXT("Dink/Data/Audio/mix.json")));
	for (const auto& Pair : Selection.Sounds)
	{
		const float* G = Selection.SfxGain.Find(Pair.Key);
		TestTrue(FString::Printf(TEXT("effect %s has a gain in 0.3-2.0"), *Pair.Key), G && *G >= .3f && *G <= 2.f);
	}
	for (const auto& Pair : Selection.Music)
	{
		const float* G = Selection.MusicGain.Find(Pair.Value.Asset);
		TestTrue(FString::Printf(TEXT("music %s has a gain in 0.3-2.5"), *Pair.Key), G && *G >= .3f && *G <= 2.5f);
	}
	TestEqual(TEXT("an unknown effect plays at the category volume"), Selection.SfxGainOf(TEXT("999")), 1.f);
	TestTrue(FString::Printf(TEXT("only the outlying voice lines are levelled (%d)"), Selection.VoiceGain.Num()), Selection.VoiceGain.Num() > 0 && Selection.VoiceGain.Num() < 600);
	for (const auto& Pair : Selection.VoiceGain) if (Pair.Value < .1f || Pair.Value > 4.f) AddError(FString::Printf(TEXT("voice %s gain %.3f out of range"), *Pair.Key, Pair.Value));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAudioStatusTicksTest, "Dink.Audio.StatusBarTicksMatch1997", DINK_TEST_FLAGS)
bool FDinkAudioStatusTicksTest::RunTest(const FString&)
{
	auto Count = [](const TArray<FDinkStatusTicks::FTick>& T, int32 Sound, int32 Speed) { return T.FilterByPredicate([&](const FDinkStatusTicks::FTick& X) { return X.Sound == Sound && X.Speed == Speed; }).Num(); };
	FDinkStatusTicks S;
	FDinkStatusTicks::FIn In; In.NextRaise = 100; In.Strength = 3; In.Defense = 0; In.Magic = 0; In.Gold = 0; In.Exp = 0;
	TArray<FDinkStatusTicks::FTick> Out;
	S.Step(In, Out);
	TestEqual(TEXT("the first look primes silently (a loaded game does not count up from zero)"), Out.Num(), 0);
	In.Gold = 50; In.Strength = 5; In.Exp = 25;
	for (int32 Frame = 0; Frame < 10; ++Frame) S.Step(In, Out);
	TestEqual(TEXT("gold 0 -> 50 in steps of 20: three ticks of 14 (dink.cpp:5919-5933)"), Count(Out, 14, 22050), 3);
	TestEqual(TEXT("strength 3 -> 5: two ticks of 22 (5895-5901)"), Count(Out, 22, 22050), 2);
	TestEqual(TEXT("exp 0 -> 25 in steps of 10: three ticks of 13 at 29050 (5856-5864)"), Count(Out, 13, 29050), 3);
	TestEqual(TEXT("nothing else"), Out.Num(), 8);
	Out.Reset();
	// A level-up (the game's): exp 95 -> 5, next raise 100 -> 400. The bar restarts silently, the raise mark counts in 40ths.
	In.Exp = 95; for (int32 Frame = 0; Frame < 10; ++Frame) S.Step(In, Out);
	Out.Reset();
	In.Exp = 5; In.NextRaise = 400;
	for (int32 Frame = 0; Frame < 60; ++Frame) S.Step(In, Out);
	TestEqual(TEXT("raise mark 100 -> 400 by 10 a frame: thirty ticks of 13 at 15050 (5847-5852)"), Count(Out, 13, 15050), 30);
	TestEqual(TEXT("no experience ticks for the drop"), Count(Out, 13, 29050), 0);
	// The update itself runs 8.6 times a second (game clock +16 ms a frame, more than 100 ms since the last: dink.cpp:17304, 17343-17346).
	double Clock = 0.0;
	int32 Updates60 = 0, Updates30 = 0, MaxPerFrame = 0;
	for (int32 Frame = 0; Frame < 60; ++Frame) Updates60 += FDinkStatusTicks::Due(Clock, 1.0 / 60.0) ? 1 : 0;
	TestTrue(FString::Printf(TEXT("one second at 60 fps: 8 or 9 status updates (got %d)"), Updates60), Updates60 >= 8 && Updates60 <= 9);
	Clock = 0.0;
	for (int32 Frame = 0; Frame < 30; ++Frame) { const int32 N = FDinkStatusTicks::Due(Clock, 1.0 / 30.0) ? 1 : 0; Updates30 += N; MaxPerFrame = FMath::Max(MaxPerFrame, N); }
	TestTrue(FString::Printf(TEXT("one second at 30 fps: still 8 or 9 (got %d), never two in one frame"), Updates30), Updates30 >= 8 && Updates30 <= 9 && MaxPerFrame <= 1);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAudioLifeTablesTest, "Dink.Audio.LifeTablesAndEngineSounds", DINK_TEST_FLAGS)
bool FDinkAudioLifeTablesTest::RunTest(const FString&)
{
	const FString Dir = FPaths::ProjectContentDir() / TEXT("Dink/Data/Audio/");
	FDinkLifeTable T;
	TestTrue(TEXT("life_data.json loads"), T.LoadData(Dir + TEXT("life_data.json")));
	TestEqual(TEXT("a surface grid for every screen"), T.Surfaces.Num(), 644);
	TestEqual(TEXT("a sound for every map.dat warp"), T.Warps.Num(), 134);
	TestEqual(TEXT("Dink's room is wood"), int32(T.SurfaceAt(1, 320, 200)), int32(TCHAR('w')));
	TestEqual(TEXT("the cave is stone"), int32(T.SurfaceAt(131, 320, 200)), int32(TCHAR('t')));
	TestEqual(TEXT("SCR_424 is open water"), int32(T.SurfaceAt(424, 320, 200)), int32(TCHAR('a')));
	TestEqual(TEXT("pixels past the edge clamp"), int32(T.SurfaceAt(1, -40, 900)), int32(T.SurfaceAt(1, 20, 399)));
	TestTrue(TEXT("indoor screens have no bed"), T.BedOf(1) == FName(TEXT("none")));
	TestTrue(TEXT("caves drip"), T.BedOf(131) == FName(TEXT("cave")));
	if (const FDinkLifeTable::FWarpSound* Door = T.Warps.Find(TEXT("S439_P13")))
	{
		TestTrue(TEXT("a door with no sound of its own plays 7 at 12000 (dink.cpp:15343-15344)"), Door->Sound == 7 && Door->Speed == 12000);
	}
	else AddError(TEXT("warp S439_P13 missing"));
	TestTrue(TEXT("life.json loads"), T.LoadTakes(Dir + TEXT("life.json")));
	for (const TCHAR L : {'g', 'd', 's', 'w', 't', 'n', 'a'})
	{
		const TArray<FDinkLifeTable::FTake>* Takes = T.Steps.Find(int32(L));
		TestTrue(FString::Printf(TEXT("surface %c has at least two step takes"), L), Takes && Takes->Num() >= 2);
	}
	TSet<FName> Beds;
	for (const auto& Pair : T.Beds) Beds.Add(Pair.Value);
	for (const FName& B : Beds) if (B != FName(TEXT("none"))) TestTrue(FString::Printf(TEXT("bed %s has a take"), *B.ToString()), T.BedTakes.Contains(B));
	auto Exists = [](const FString& Asset) { return FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(Asset)); };
	int32 Missing = 0;
	for (const auto& Pair : T.Steps) for (const FDinkLifeTable::FTake& Take : Pair.Value) Missing += Exists(Take.Asset) ? 0 : 1;
	for (const auto& Pair : T.BedTakes) Missing += Exists(Pair.Value.Asset) ? 0 : 1;
	TestEqual(TEXT("every life take is imported (Scripts/AudioQA/import_life_audio.sh)"), Missing, 0);
	// Every engine sound the presentation layer reproduces has an approved take (a rejected one would stay silent).
	FDinkAudioSelection Approved;
	TestTrue(TEXT("approved.json loads"), Approved.Load(Dir + TEXT("approved.json")));
	TSet<int32> Engine = {9, 11, 13, 14, 15, 16, 17, 22};   // 9: the engine's default hit (dink.cpp:14284, 14308, 14356, 15551)
	for (const auto& Pair : T.Warps) Engine.Add(Pair.Value.Sound);
	for (const int32 Id : Engine) TestTrue(FString::Printf(TEXT("engine sound %d is approved"), Id), Approved.Sounds.Contains(FString::FromInt(Id)));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAudioLimiterTest, "Dink.Audio.MasterLimiterHoldsCeiling", DINK_TEST_FLAGS)
bool FDinkAudioLimiterTest::RunTest(const FString&)
{
	// The master limiter (UDinkAudioLifeSubsystem::EnsureLimiter) is the engine's submix dynamics processor; this drives the same
	// FDynamicsProcessor with the same values on a hard case: 6 channels at 48 kHz, a burst of hits and a hard-panned tone
	// summed to +6 dBFS (the run A2 soak reached full scale). Every output sample after the look-ahead must stay at the ceiling.
	struct FCfg { bool bAnalog; float LookAheadMs, AttackMs; };
	auto Run = [](const FCfg& C)
	{
		const int32 Rate = 48000, Ch = 6, Frames = Rate;
		Audio::FDynamicsProcessor P;
		P.Init(float(Rate), Ch);
		P.SetProcessingMode(Audio::EDynamicsProcessingMode::Limiter);
		P.SetThreshold(FDinkAudioMix::LimiterCeilingDb);
		P.SetKneeBandwidth(0.f);
		P.SetLookaheadMsec(C.LookAheadMs);
		P.SetAttackTime(C.AttackMs);
		P.SetReleaseTime(FDinkAudioMix::LimiterReleaseMs);
		P.SetPeakMode(Audio::EPeakMode::Peak);
		P.SetChannelLinkMode(Audio::EDynamicsProcessorChannelLinkMode::Peak);
		P.SetAnalogMode(C.bAnalog);
		P.SetInputGain(0.f); P.SetOutputGain(0.f);
		TArray<float> In, Out;
		In.SetNumZeroed(Frames * Ch); Out.SetNumZeroed(Frames * Ch);
		FRandomStream R(1997);
		const float Hot = FMath::Pow(10.f, 6.f / 20.f);
		for (int32 F = 0; F < Frames; ++F)
		{
			const float T = float(F) / Rate;
			// a 220 Hz tone hard right from 0.1 s, a noise hit with a 5 ms decay every 70 ms on both fronts
			const float Tone = T > 0.1f ? 0.6f * Hot * FMath::Sin(2.f * PI * 220.f * T) : 0.f;
			const float Ph = FMath::Fmod(T, 0.07f);
			const float Hit = Hot * FMath::Exp(-Ph / 0.005f) * R.FRandRange(-1.f, 1.f);
			In[F * Ch + 0] = Hit;
			In[F * Ch + 1] = FMath::Clamp(Tone + Hit, -Hot, Hot);
		}
		P.ProcessAudio(In.GetData(), In.Num(), Out.GetData());
		float Peak = 0.f;
		const int32 Skip = FMath::CeilToInt(C.LookAheadMs * Rate / 1000.f) * Ch;
		for (int32 I = Skip; I < Out.Num(); ++I) Peak = FMath::Max(Peak, FMath::Abs(Out[I]));
		return 20.f * FMath::LogX(10.f, FMath::Max(Peak, 1e-9f));
	};
	const float Game = Run({FDinkAudioMix::bLimiterAnalog, FDinkAudioMix::LimiterLookAheadMs, FDinkAudioMix::LimiterAttackMs});
	const float Before = Run({true, 3.f, 1.f});   // the 15 Nov configuration (analog detector, 1 ms attack, 3 ms look-ahead)
	AddInfo(FString::Printf(TEXT("+6 dBFS hits and tone: output peak %.2f dBFS with the game's limiter, %.2f dBFS with the 15 Nov configuration"), Game, Before));
	TestTrue(FString::Printf(TEXT("output peak %.2f dBFS never passes the %.1f dBFS ceiling"), Game, FDinkAudioMix::LimiterCeilingDb),
		Game <= FDinkAudioMix::LimiterCeilingDb + 0.05f);
	TestTrue(TEXT("the 15 Nov configuration let peaks through (the defect this pins)"), Before > FDinkAudioMix::LimiterCeilingDb + 1.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAudioLimiterPresetTest, "Dink.Audio.MasterLimiterPresetHoldsCeiling", DINK_TEST_FLAGS)
bool FDinkAudioLimiterPresetTest::RunTest(const FString&)
{
	// Bug A164: the recorded game output passed the -1.5 dBFS ceiling whatever limiter values the code set. The effect instance on
	// the master bus is made the way UAudioMixerBlueprintLibrary::AddMasterSubmixEffect makes it (AudioMixerBlueprintLibrary.cpp:
	// 86-98: CreateInstance, SetEnabled) and runs through FSoundEffectSubmix::ProcessAudio, which applies the preset's settings
	// (Update -> OnPresetChanged) as the audio render thread does. CreateInstance's first instance runs USoundEffectPreset::Init,
	// which copies the preset's Settings property over what SetSettings stored; so a preset given its values only by SetSettings
	// runs the engine defaults (a -6 dB compressor). Same +6 dBFS signal as MasterLimiterHoldsCeiling, 6 channels, 1024-frame blocks.
	auto Run = [](USoundEffectSubmixPreset* Preset, bool& bProcessed)
	{
		const int32 Rate = 48000, Ch = 6, Block = 1024, Frames = Rate;
		FSoundEffectSubmixInitData Init;
		Init.SampleRate = float(Rate);
		Init.ParentPresetUniqueId = Preset->GetUniqueID();
		TSharedPtr<FSoundEffectSubmix, ESPMode::ThreadSafe> Fx = USoundEffectPreset::CreateInstance<FSoundEffectSubmixInitData, FSoundEffectSubmix>(Init, *Preset);
		Fx->SetEnabled(true);
		FRandomStream R(1997);
		const float Hot = FMath::Pow(10.f, 6.f / 20.f);
		Audio::FAlignedFloatBuffer In, Out;
		float Peak = 0.f;
		bProcessed = true;
		for (int32 F0 = 0; F0 < Frames; F0 += Block)
		{
			In.Reset(); In.AddZeroed(Block * Ch); Out.Reset(); Out.AddZeroed(Block * Ch);
			for (int32 F = 0; F < Block; ++F)
			{
				const float T = float(F0 + F) / Rate;
				const float Tone = T > 0.1f ? 0.6f * Hot * FMath::Sin(2.f * PI * 220.f * T) : 0.f;
				const float Hit = Hot * FMath::Exp(-FMath::Fmod(T, 0.07f) / 0.005f) * R.FRandRange(-1.f, 1.f);
				In[F * Ch + 0] = Hit;
				In[F * Ch + 1] = FMath::Clamp(Tone + Hit, -Hot, Hot);
			}
			FSoundEffectSubmixInputData InData;
			InData.NumFrames = Block; InData.NumChannels = Ch; InData.NumDeviceChannels = Ch; InData.AudioBuffer = &In;
			FSoundEffectSubmixOutputData OutData;
			OutData.AudioBuffer = &Out; OutData.NumChannels = Ch;
			bProcessed &= Fx->ProcessAudio(InData, OutData);
			for (const float V : Out) Peak = FMath::Max(Peak, FMath::Abs(V));
		}
		USoundEffectPreset::UnregisterInstance(Fx);
		return 20.f * FMath::LogX(10.f, FMath::Max(Peak, 1e-9f));
	};

	TStrongObjectPtr<USoundEffectSubmixPreset> Game(FDinkAudioMix::MakeLimiterPreset(GetTransientPackage()));
	bool bGameProcessed = false;
	const float GameDb = Run(Game.Get(), bGameProcessed);
	const FSubmixEffectDynamicsProcessorSettings Used = CastChecked<USubmixEffectDynamicsProcessorPreset>(Game.Get())->GetSettings();
	TestTrue(TEXT("the instance processed every block"), bGameProcessed);
	TestTrue(TEXT("after the instance's Init the preset still holds the limiter values"),
		Used.DynamicsProcessorType == ESubmixEffectDynamicsProcessorType::Limiter && FMath::IsNearlyEqual(Used.ThresholdDb, FDinkAudioMix::LimiterCeilingDb)
		&& FMath::IsNearlyEqual(Used.AttackTimeMsec, FDinkAudioMix::LimiterAttackMs) && FMath::IsNearlyEqual(Used.LookAheadMsec, FDinkAudioMix::LimiterLookAheadMs)
		&& Used.bAnalogMode == FDinkAudioMix::bLimiterAnalog);
	TestTrue(FString::Printf(TEXT("output peak %.2f dBFS never passes the %.1f dBFS ceiling"), GameDb, FDinkAudioMix::LimiterCeilingDb),
		GameDb <= FDinkAudioMix::LimiterCeilingDb + 0.05f);

	// The code before 16 Nov: the same values through SetSettings only.
	USubmixEffectDynamicsProcessorPreset* OldRaw = NewObject<USubmixEffectDynamicsProcessorPreset>(GetTransientPackage());
	TStrongObjectPtr<USoundEffectSubmixPreset> Old(OldRaw);
	OldRaw->SetSettings(CastChecked<USubmixEffectDynamicsProcessorPreset>(Game.Get())->Settings);
	bool bOldProcessed = false;
	const float OldDb = Run(Old.Get(), bOldProcessed);
	const FSubmixEffectDynamicsProcessorSettings OldUsed = OldRaw->GetSettings();
	AddInfo(FString::Printf(TEXT("+6 dBFS hits and tone through the master-bus effect instance: %.2f dBFS out with MakeLimiterPreset, %.2f dBFS with SetSettings only (the instance ran type %d at %.1f dB)"),
		GameDb, OldDb, int32(OldUsed.DynamicsProcessorType), OldUsed.ThresholdDb));
	TestTrue(TEXT("SetSettings alone is overwritten by the first instance's Init (the defect this pins)"),
		OldUsed.DynamicsProcessorType != ESubmixEffectDynamicsProcessorType::Limiter && OldDb > FDinkAudioMix::LimiterCeilingDb + 1.f);
	return true;
}
