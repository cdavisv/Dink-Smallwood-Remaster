// Dink.Perf.*: performance contracts (stream perf-stutter, 15 Nov 2026).
//   Dink.Perf.Scope.CountsGameThreadCalls     DINK_PERF_SCOPE counts calls and time (the benchmark's per-subsystem costs)
//   Dink.Perf.ScreenEntry.NoSyncLoads         entering the benchmark's screens loads no package synchronously on the
//                                             game thread (A15: every mesh/material a screen needs is loaded before)
//   Dink.Perf.Tick.Bounded                    the real world in PIE ticks a bounded number of actors/components, and no
//                                             placeholder, screen or family-art piece ticks
//   Dink.Perf.Route.WritesSummary             dink.Perf.Route runs a two-line route and writes its csv and json
#include "DinkTestHelpers.h"
#include "DinkPerfScope.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Editor.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Tests/AutomationEditorCommon.h"
#include "Async/Async.h"

namespace
{
	int32 GPerfProbeCalls = 0;
	void PerfProbeFunction()
	{
		DINK_PERF_SCOPE(Dink_Test_PerfProbe);
		++GPerfProbeCalls;
		const double Until = FPlatformTime::Seconds() + 0.0005;   // a known half millisecond inside the scope
		while (FPlatformTime::Seconds() < Until) {}
	}

	const DinkPerf::FScopeStat* FindStat(const TCHAR* Name)
	{
		for (const DinkPerf::FScopeStat* S = DinkPerf::FirstStat(); S; S = S->Next)
			if (FCString::Strcmp(S->Name, Name) == 0) return S;
		return nullptr;
	}

	bool LoadGreyboxWorld(FAutomationTestBase& Test)
	{
		const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
		if (!IFileManager::Get().FileExists(*File))
		{
			Test.AddWarning(TEXT("skipped: greybox world not imported (Scripts/import_greybox.sh --region all)"));
			return false;
		}
		if (!Test.TestNotNull(TEXT("real world map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
		FAssetCompilingManager::Get().FinishAllCompilation();
		return true;
	}

	UWorld* ReadyPlayWorld()
	{
		UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
		UDinkStorySubsystem* Story = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		return Story && !Story->bNewGamePending ? World : nullptr;
	}

	/** The benchmark route's screens (Scripts/perf/make_route.py STOPS) and one walked neighbour of each kind. */
	const int32 GEntryScreens[] = { 438, 439, 312, 650, 530, 98, 579, 527 };

	class FDinkPerfScreenEntryCheck : public IAutomationLatentCommand
	{
	public:
		explicit FDinkPerfScreenEntryCheck(FAutomationTestBase* InTest) : Test(InTest) {}
		bool Update() override
		{
			if (Began == 0) Began = FPlatformTime::Seconds();
			if (FPlatformTime::Seconds() - Began > 240)
			{
				Test->AddError(FString::Printf(TEXT("screen entry check timed out at stop %d"), Stop));
				DinkPerf::SetSyncLoadCounting(false);
				return true;
			}
			UWorld* World = ReadyPlayWorld();
			UDinkGreyboxSubsystem* Grey = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
			if (!Grey) return false;
			if (Stop < 0)
			{
				// let the start screen settle (its own dressing is begin-play work, not screen entry)
				if (++Frames < 60) return false;
				DinkPerf::SetSyncLoadCounting(true);
				Stop = 0;
				Frames = 0;
			}
			if (Stop >= int32(UE_ARRAY_COUNT(GEntryScreens)))
			{
				DinkPerf::SetSyncLoadCounting(false);
				Test->AddInfo(FString::Printf(TEXT("%d synchronous package loads while entering %d screens"), DinkPerf::GSyncLoadsCounted, int32(UE_ARRAY_COUNT(GEntryScreens))));
				for (const FString& P : DinkPerf::GSyncLoadPackages) Test->AddError(FString::Printf(TEXT("synchronous load on screen entry: %s"), *P));
				Test->TestEqual(TEXT("no synchronous package load on screen entry"), DinkPerf::GSyncLoadsCounted, 0);
				return true;
			}
			const int32 Target = GEntryScreens[Stop];
			if (!bIssued)
			{
				if (!Grey->GotoScreen(Target, 300.f, 200.f)) Test->AddWarning(FString::Printf(TEXT("screen %d not in this world"), Target));
				bIssued = true;
				Frames = Waited = 0;
				return false;
			}
			const ADinkScreenVolume* Current = Grey->GetCurrentScreen();
			if (Current && Current->ScreenNumber == Target) ++Frames;
			// stay 40 frames after the screen is entered: dressing, grass cells, corpses and swaps all run by then
			if (Frames > 40 || ++Waited > 600)
			{
				if (Frames <= 40) Test->AddWarning(FString::Printf(TEXT("screen %d never became current"), Target));
				++Stop;
				bIssued = false;
			}
			return false;
		}
	private:
		FAutomationTestBase* Test;
		double Began = 0;
		int32 Stop = -1, Frames = 0, Waited = 0;
		bool bIssued = false;
	};

	class FDinkPerfTickCheck : public IAutomationLatentCommand
	{
	public:
		explicit FDinkPerfTickCheck(FAutomationTestBase* InTest) : Test(InTest) {}
		bool Update() override
		{
			if (Began == 0) Began = FPlatformTime::Seconds();
			if (FPlatformTime::Seconds() - Began > 120) { Test->AddError(TEXT("tick check timed out")); return true; }
			UWorld* World = ReadyPlayWorld();
			if (!World || ++Frames < 90) return false;
			// What ticks on the generated world's static actors (placements, screen volumes, greybox screens) is the live
			// presentation of sprites, by design: creature bodies, humanoids, and the player blockers at 5 Hz. Anything else
			// ticking there is an error by name; the actors themselves must not tick; the per-frame set must stay bounded.
			// DinkFlickerLightComponent: the firelight of placed effect rows (PR #166: the burning house, hearths); a flicker is per frame
			// by nature and there are a dozen of them in the whole world
			static const TCHAR* const Allowed[] = { TEXT("DinkCreatureComponent"), TEXT("DinkCreatureClassComponent"), TEXT("DinkHumanoidComponent"), TEXT("DinkFlickerLightComponent") };
			int32 Actors = 0, TickingActors = 0, EveryFrame = 0, Slow = 0, StaticActorTicks = 0;
			TMap<FString, int32> ByClass, Unexpected;
			for (TActorIterator<AActor> It(World); It; ++It)
			{
				++Actors;
				const bool bStatic = It->IsA<ADinkPlaceholderActor>() || It->IsA<ADinkScreenVolume>() || It->IsA<ADinkGreyboxScreen>();
				if (It->IsActorTickEnabled())
				{
					++TickingActors;
					ByClass.FindOrAdd(It->GetClass()->GetName())++;
					if (bStatic && It->PrimaryActorTick.TickInterval < 0.1f) ++StaticActorTicks;
				}
				TInlineComponentArray<UActorComponent*> Components(*It);
				for (UActorComponent* C : Components)
				{
					if (!C->IsComponentTickEnabled()) continue;
					const FString Name = C->GetClass()->GetName();
					const bool bSlow = C->PrimaryComponentTick.TickInterval >= 0.1f;
					(bSlow ? Slow : EveryFrame)++;
					ByClass.FindOrAdd(Name)++;
					bool bAllowed = bSlow;   // a 5 Hz component (the player blockers) is not a per-frame cost
					for (const TCHAR* A : Allowed) bAllowed |= Name == A;
					if (bStatic && !bAllowed) Unexpected.FindOrAdd(Name)++;
				}
			}
			ByClass.ValueSort([](int32 A, int32 B) { return A > B; });
			FString Top;
			int32 Shown = 0;
			for (const TPair<FString, int32>& P : ByClass) { if (Shown++ < 12) Top += FString::Printf(TEXT("%s %d, "), *P.Key, P.Value); }
			Test->AddInfo(FString::Printf(TEXT("%d actors, %d ticking actors, %d components ticking every frame, %d at 10 Hz or less; most: %s"),
				Actors, TickingActors, EveryFrame, Slow, *Top));
			Test->TestEqual(TEXT("no placement, screen volume or greybox screen actor ticks every frame"), StaticActorTicks, 0);
			for (const TPair<FString, int32>& P : Unexpected)
				Test->AddError(FString::Printf(TEXT("%d %s components tick on placement/screen actors (not live sprite presentation)"), P.Value, *P.Key));
			// 644 screens with ~5,800 placements: the per-frame set stays with the live sprites, not with the map
			// (15 Nov 2026 benchmark: about 160 creature bodies, 11 authored creatures, a few humanoids)
			Test->TestTrue(FString::Printf(TEXT("components ticking every frame bounded (%d <= 800)"), EveryFrame), EveryFrame <= 800);
			Test->TestTrue(FString::Printf(TEXT("ticking actors bounded (%d <= 300)"), TickingActors), TickingActors <= 300);
			return true;
		}
	private:
		FAutomationTestBase* Test;
		double Began = 0;
		int32 Frames = 0;
	};

	class FDinkPerfRouteCheck : public IAutomationLatentCommand
	{
	public:
		FDinkPerfRouteCheck(FAutomationTestBase* InTest, FString InPrefix) : Test(InTest), Prefix(MoveTemp(InPrefix)) {}
		bool Update() override
		{
			if (Began == 0) Began = FPlatformTime::Seconds();
			if (FPlatformTime::Seconds() - Began > 120) { Test->AddError(TEXT("route check timed out")); return true; }
			UWorld* World = ReadyPlayWorld();
			if (!World) return false;
			if (!bStarted)
			{
				const FString Route = Prefix + TEXT("_route.txt");
				FFileHelper::SaveStringToFile(FString(TEXT("segment test:steady:start\nwait 0.5\nend\n")), *Route);
				GEngine->Exec(World, *FString::Printf(TEXT("dink.Perf.Route %s %s"), *Route, *Prefix));
				bStarted = true;
				return false;
			}
			const FString Summary = Prefix + TEXT("_summary.json");
			if (!IFileManager::Get().FileExists(*Summary)) return false;
			FString Json, Csv;
			Test->TestTrue(TEXT("summary readable"), FFileHelper::LoadFileToString(Json, *Summary));
			Test->TestTrue(TEXT("frames csv written"), FFileHelper::LoadFileToString(Csv, *(Prefix + TEXT("_frames.csv"))));
			TArray<FString> Lines;
			Csv.ParseIntoArrayLines(Lines);
			Test->TestTrue(FString::Printf(TEXT("frames recorded (%d)"), Lines.Num() - 1), Lines.Num() > 2);
			Test->TestTrue(TEXT("summary names the segment"), Json.Contains(TEXT("test:steady:start")));
			Test->TestTrue(TEXT("summary has percentiles"), Json.Contains(TEXT("p99_ms")));
			return true;
		}
	private:
		FAutomationTestBase* Test;
		FString Prefix;
		double Began = 0;
		bool bStarted = false;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPerfScopeTest, "Dink.Perf.Scope.CountsGameThreadCalls", DINK_TEST_FLAGS)
bool FDinkPerfScopeTest::RunTest(const FString&)
{
	PerfProbeFunction();
	const DinkPerf::FScopeStat* Stat = FindStat(TEXT("Dink_Test_PerfProbe"));
	if (!TestNotNull(TEXT("the scope registers itself on first use"), Stat)) return false;
	const uint64 Calls = Stat->Calls;
	const uint64 Cycles = Stat->Cycles;
	for (int32 I = 0; I < 3; ++I) PerfProbeFunction();
	TestEqual(TEXT("three more calls counted"), int64(Stat->Calls), int64(Calls + 3));
	const double Ms = FPlatformTime::ToMilliseconds64(Stat->Cycles - Cycles);
	TestTrue(FString::Printf(TEXT("time accumulates (%.3f ms for three 0.5 ms calls)"), Ms), Ms >= 1.4);
	TestTrue(TEXT("longest call recorded"), FPlatformTime::ToMilliseconds64(Stat->MaxCycles) >= 0.45);
	// a scope entered on another thread is traced but not counted (the totals are game-thread only)
	const uint64 Before = Stat->Calls;
	Async(EAsyncExecution::Thread, [] { PerfProbeFunction(); }).Wait();   // its own thread: a task could be retracted onto this one
	TestEqual(TEXT("a call on a worker thread is not counted"), int64(Stat->Calls), int64(Before));
	int32 Registered = 0;
	for (const DinkPerf::FScopeStat* S = DinkPerf::FirstStat(); S; S = S->Next) Registered += FCString::Strcmp(S->Name, TEXT("Dink_Test_PerfProbe")) == 0;
	TestEqual(TEXT("one registration per call site"), Registered, 1);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPerfScreenEntryTest, "Dink.Perf.ScreenEntry.NoSyncLoads", DINK_TEST_FLAGS)
bool FDinkPerfScreenEntryTest::RunTest(const FString&)
{
	if (!LoadGreyboxWorld(*this)) return true;
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FDinkPerfScreenEntryCheck(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPerfTickTest, "Dink.Perf.Tick.Bounded", DINK_TEST_FLAGS)
bool FDinkPerfTickTest::RunTest(const FString&)
{
	if (!LoadGreyboxWorld(*this)) return true;
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FDinkPerfTickCheck(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPerfRouteTest, "Dink.Perf.Route.WritesSummary", DINK_TEST_FLAGS)
bool FDinkPerfRouteTest::RunTest(const FString&)
{
	if (!LoadGreyboxWorld(*this)) return true;
	const FString Prefix = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("Automation/DinkPerfRouteTest"));
	IFileManager::Get().Delete(*(Prefix + TEXT("_summary.json")));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FDinkPerfRouteCheck(this, Prefix));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
