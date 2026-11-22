// First launch picks the quality level for this machine (stream perf-stutter, 15-16 Nov 2026).
//
// A fresh install used to start on the engine's defaults (every group Epic at the project's screen percentage), whatever
// the graphics card: 65 fps on an RX 6800 at 2560x1440, about half that on a mid-range card. Now the first launch that
// renders starts at High and, once play has settled, measures the real GPU busy time per frame for five seconds of
// play on an outdoor gameplay screen (frames indoors, paused, between screens or without a pawn do not count; GPU busy
// time, not frame time, so a CPU-bound or vsync-capped machine is not misread). While its median is above
// dink.Perf.AutoDetectTargetMs (13.5 ms: headroom for 60 fps) it steps one level down (High, Medium, Low) and measures
// again. A level change rebuilds every mesh draw command (about 100 ms), so a step down waits for the next screen
// change, where the game redresses the scene anyway, instead of hitching in the middle of a screen. The result is saved with the game's settings ([DinkPerf] FirstRunDone in
// GameUserSettings.ini), so later launches keep it and a player's own choice is never touched again. Epic stays a
// player's choice.
//
// The engine's own synthetic hardware benchmark (UGameUserSettings::RunHardwareBenchmark) is NOT used: on this
// project's Linux Vulkan path (RADV, RX 6800) its GPU test hung the GPU twice in a row (kernel: amdgpu ring gfx timeout
// in the RHI thread, 16 Nov 2026 04:44 and 04:46). Measuring the game itself needs no extra GPU work.
//
// Skipped in the editor, commandlets, automation, -nullrhi runs, with -NoDinkAutoDetect (the benchmark routes pass it),
// or with dink.Perf.AutoDetect 0 in the ini. Presentation only: the 1997 simulation never reads a quality level.
#include "DinkCoreModule.h"
#include "Containers/Ticker.h"
#include "DynamicRHI.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "GameFramework/GameUserSettings.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "Misc/CommandLine.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/CoreMisc.h"
#include "Misc/DelayedAutoRegister.h"
#include "Misc/Parse.h"

// Off by default (16 Nov 2026): the step-down has not yet been seen end to end in a packaged first launch; turn it on with
// -ini:Engine:[ConsoleVariables]:dink.Perf.AutoDetect=1 or DINK_AUTODETECT=1 in Scripts/perf/run_bench.sh to test it.
static TAutoConsoleVariable<int32> CVarDinkAutoDetect(TEXT("dink.Perf.AutoDetect"), 0,
	TEXT("1 = the first launch that renders starts at High and steps down while the measured GPU frame time is above dink.Perf.AutoDetectTargetMs (once; saved). 0 = keep the defaults."));
static TAutoConsoleVariable<float> CVarDinkAutoDetectTargetMs(TEXT("dink.Perf.AutoDetectTargetMs"), 13.5f,
	TEXT("GPU milliseconds per frame the first-run quality detection aims below (13.5 = headroom for 60 fps)."));

namespace
{
	const TCHAR* const Section = TEXT("DinkPerf");
	const TCHAR* const DoneKey = TEXT("FirstRunDone");

	struct FFirstRunDetect
	{
		int32 Level = 2;                 // overall scalability level being measured (High first)
		int32 PendingLevel = -1;         // decided, applied at the next screen change
		int32 DecisionScreen = -1;
		double SettleUntil = 0.0;        // no samples before this (world load, warm-up, a level change)
		TArray<float> GpuMs;
		double Began = 0.0;
		uint64 LastFrame = 0;
	};

	const TCHAR* LevelName(int32 Level)
	{
		static const TCHAR* const Names[] = { TEXT("Low"), TEXT("Medium"), TEXT("High"), TEXT("Epic"), TEXT("Cinematic") };
		return Names[FMath::Clamp(Level, 0, 4)];
	}

	/** The current gameplay screen, or nullptr when the frame must not count (no game world, no pawn, paused, between screens). */
	const ADinkScreenVolume* GameplayScreen()
	{
		UWorld* World = GEngine && GEngine->GameViewport ? GEngine->GameViewport->GetWorld() : nullptr;
		if (!World || !World->IsGameWorld() || World->IsPaused()) return nullptr;
		const APlayerController* PC = World->GetFirstPlayerController();
		if (!PC || !PC->GetPawn()) return nullptr;
		const UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
		return Grey ? Grey->GetCurrentScreen() : nullptr;
	}

	void Finish(FFirstRunDetect& D, UGameUserSettings& Settings, const TCHAR* Why, float MedianMs)
	{
		Settings.SetOverallScalabilityLevel(D.Level);
		Settings.SaveSettings();
		GConfig->SetBool(Section, DoneKey, true, GGameUserSettingsIni);
		GConfig->Flush(false, GGameUserSettingsIni);
		UE_LOG(LogDink, Display, TEXT("DINK FIRST RUN: auto-detect done: %s (%s; GPU median %.1f ms, target %.1f ms, %.0f s)"), LevelName(D.Level), Why, MedianMs,
			CVarDinkAutoDetectTargetMs.GetValueOnGameThread(), FPlatformTime::Seconds() - D.Began);
	}

	bool Step(TSharedRef<FFirstRunDetect> D)
	{
		UGameUserSettings* Settings = GEngine ? GEngine->GetGameUserSettings() : nullptr;
		if (!Settings) return false;
		const double Now = FPlatformTime::Seconds();
		if (Now - D->Began > 600.0) { Finish(*D, *Settings, TEXT("time limit, kept the last measured level"), 0.f); return false; }
		if (D->LastFrame == GFrameCounter) return true;
		D->LastFrame = GFrameCounter;
		const ADinkScreenVolume* Screen = GameplayScreen();
		if (D->PendingLevel >= 0)
		{
			// apply the step down where the scene changes anyway
			if (!Screen || Screen->ScreenNumber == D->DecisionScreen) return true;
			D->Level = D->PendingLevel;
			D->PendingLevel = -1;
			Settings->SetOverallScalabilityLevel(D->Level);
			Settings->ApplySettings(false);
			D->SettleUntil = Now + 3.0;
			D->GpuMs.Reset();
			return true;
		}
		if (!Screen || Screen->bIndoor || Now < D->SettleUntil) return true;
		const float Gpu = float(FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0)));
		if (Gpu > 0.f) D->GpuMs.Add(Gpu);
		if (D->GpuMs.Num() < 150) return true;   // about five seconds of outdoor play at 30 fps, less time when faster
		TArray<float> Sorted = D->GpuMs;
		Sorted.Sort();
		const float Median = Sorted[Sorted.Num() / 2];
		if (Median <= CVarDinkAutoDetectTargetMs.GetValueOnGameThread() || D->Level == 0)
		{
			Finish(*D, *Settings, D->Level == 0 ? TEXT("lowest level") : TEXT("within the target"), Median);
			return false;
		}
		UE_LOG(LogDink, Display, TEXT("DINK FIRST RUN: auto-detect: GPU median %.1f ms at %s -> %s (applied at the next screen change)"), Median,
			LevelName(D->Level), LevelName(D->Level - 1));
		D->PendingLevel = D->Level - 1;
		D->DecisionScreen = Screen->ScreenNumber;
		return true;
	}
}

static FDelayedAutoRegisterHelper GDinkFirstRunSettings(EDelayedRegisterRunPhase::EndOfEngineInit, []
{
	if (GIsEditor || IsRunningCommandlet() || GIsAutomationTesting || !FApp::CanEverRender() || CVarDinkAutoDetect.GetValueOnGameThread() == 0
		|| FParse::Param(FCommandLine::Get(), TEXT("NoDinkAutoDetect")))
	{
		return;
	}
	UGameUserSettings* Settings = GEngine ? GEngine->GetGameUserSettings() : nullptr;
	bool bDone = false;
	GConfig->GetBool(Section, DoneKey, bDone, GGameUserSettingsIni);
	if (!Settings || bDone) return;
	// settings saved by an earlier version (a player who already chose): keep them, and never detect on this machine
	TArray<FString> Saved;
	if (GConfig->GetSection(TEXT("ScalabilityGroups"), Saved, GGameUserSettingsIni) && !Saved.IsEmpty())
	{
		GConfig->SetBool(Section, DoneKey, true, GGameUserSettingsIni);
		return;
	}
	TSharedRef<FFirstRunDetect> D = MakeShared<FFirstRunDetect>();
	D->Began = FPlatformTime::Seconds();
	D->SettleUntil = D->Began + 10.0;
	Settings->SetOverallScalabilityLevel(D->Level);
	Settings->ApplySettings(false);
	UE_LOG(LogDink, Display, TEXT("DINK FIRST RUN: starting at quality level %d, measuring the GPU frame time in play"), D->Level);
	FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([D](float) { return Step(D); }));
});
