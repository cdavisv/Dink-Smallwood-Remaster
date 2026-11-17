// dink.Perf.Route <route file> <output prefix>: scripted, repeatable frame-time benchmark (stream perf-stutter, 15 Nov 2026).
//
// The route file has one instruction per line ('#' starts a comment):
//   segment <label>         start a new measured segment (frames before the first segment are not reported)
//   goto <screen> [x y]     teleport to an original screen (dink.Goto), then measuring continues
//   walk <mapx> <mapy> [s] [dir interval]  walk by movement input toward a map pixel of the current screen until it
//                           arrives, changes screen or times out (like dink.WalkTo, but the route waits for it); with
//                           dir and interval, a screenshot strip dir/strip_NNN.png every interval seconds on the way
//   wait <seconds>          let frames run
//   shot <png path>         viewport screenshot without UI (keep it in its own segment: that frame is slow)
//   end                     write the files (also written when the file runs out); `quit` after it exits
//   anything else           a console command (scalability 1, r.ScreenPercentage 50, stat unit, ...)
//
// Output: <prefix>_frames.csv (one row per frame) and <prefix>_summary.json (per segment: avg/p50/p95/p99/max
// frame ms, hitch counts over 33/50/100 ms, thread and GPU ms, draw calls, primitives, memory, sync loads, GC,
// the cost of every DINK_PERF_SCOPE, and each hitch with its likely causes). Scripts/perf/perf_report.py turns
// one or more summaries into the markdown tables.
//
// Presentation/measurement only: it reads timers and walks the pawn with ordinary input; the 1997 simulation
// runs exactly as it would under a player.
#include "DinkPerfScope.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/StaticMesh.h"
#include "DinkCoreModule.h"
#include "DinkLayout.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "DynamicRHI.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "UnrealClient.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMemory.h"
#include "Misc/App.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/OutputDevice.h"
#include "Misc/OutputDeviceRedirector.h"
#include "Misc/Paths.h"
#include "PipelineStateCache.h"
#include "RenderTimer.h"
#include "RHIStats.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "ShaderPipelineCache.h"
#include "UObject/UObjectGlobals.h"
#if WITH_EDITOR
#include "ShaderCompiler.h"
#endif

static TAutoConsoleVariable<int32> CVarDinkPerfFixes(TEXT("dink.Perf.Fixes"), 1,
	TEXT("1 = the perf-stutter optimisations (indexed screen lookups, budgeted neighbour dressing, async preloads, ranged billboarding); 0 = the master 49627fc9 code paths, for before/after measurement. Presentation only."));

namespace DinkPerf
{
	static FScopeStat* GFirstStat = nullptr;

	bool FixesEnabled() { return CVarDinkPerfFixes.GetValueOnGameThread() != 0; }

	static TAutoConsoleVariable<int32> CVarDinkStaticForestShadows(TEXT("dink.Perf.StaticForestShadows"), 1,
		TEXT("1 = wind-swayed vegetation (SM_Veg_* meshes: environment forests and family-art trees and bushes) keeps cached rest-pose virtual shadow pages instead of re-rendering them every frame (components dressed after the change; dink.Perf.Fixes 1)."));

	void CacheVegetationShadows(UPrimitiveComponent& Component, const UStaticMesh* Mesh)
	{
		if (!Mesh || !FixesEnabled() || CVarDinkStaticForestShadows.GetValueOnGameThread() == 0) return;
		if (!Mesh->GetName().StartsWith(TEXT("SM_Veg_"))) return;
		Component.ShadowCacheInvalidationBehavior = EShadowCacheInvalidationBehavior::Static;
	}

	FScopeStat& Register(FScopeStat& Stat)
	{
		Stat.Next = GFirstStat;
		GFirstStat = &Stat;
		return Stat;
	}

	FScopeStat* FirstStat() { return GFirstStat; }
}

#if !UE_BUILD_SHIPPING
namespace
{
	/** Log lines that explain a long frame (editor compile waits, shader/PSO compiles, streaming flushes, GC). */
	class FHitchLogCapture final : public FOutputDevice
	{
	public:
		FCriticalSection Lock;
		TArray<FString> Lines;
		virtual void Serialize(const TCHAR* V, ELogVerbosity::Type Verbosity, const FName& Category) override
		{
			static const FName Interesting[] = { TEXT("LogStaticMesh"), TEXT("LogShaderCompilers"), TEXT("LogStreaming"),
				TEXT("LogTexture"), TEXT("LogMaterial"), TEXT("LogRHI"), TEXT("LogVulkanRHI"), TEXT("LogGarbage"),
				TEXT("LogAudioMixer"), TEXT("LogAssetCompiler"), TEXT("LogSkeletalMesh"), TEXT("LogNanite"), TEXT("LogPSO") };
			bool bKeep = (Verbosity & ELogVerbosity::VerbosityMask) <= ELogVerbosity::Warning;
			for (const FName& Name : Interesting) bKeep |= Category == Name;
			if (!bKeep)
			{
				bKeep = FCString::Strifind(V, TEXT("Waiting on")) || FCString::Strifind(V, TEXT("Flush")) || FCString::Strifind(V, TEXT("hitch"));
			}
			if (!bKeep) return;
			FScopeLock Scoped(&Lock);
			if (Lines.Num() < 12) Lines.Add(FString::Printf(TEXT("%s: %s"), *Category.ToString(), V).Left(220));
		}
		virtual bool CanBeUsedOnAnyThread() const override { return true; }
		virtual bool CanBeUsedOnMultipleThreads() const override { return true; }
	};

	/** One capture device for the process: GLog keeps a raw pointer, so it must outlive any route. */
	FHitchLogCapture& HitchLog() { static FHitchLogCapture Device; return Device; }

	struct FFrame
	{
		uint64 Frame = 0;
		double Time = 0.0, FrameMs = 0.0, GameMs = 0.0, RenderMs = 0.0, RhiMs = 0.0, GpuMs = 0.0, GcMs = 0.0;
		int32 Segment = -1, Draws = 0, Prims = 0, AsyncPackages = 0, SyncLoads = 0, Screen = -1, PsoPrecache = 0, ShaderJobs = 0, PendingInView = 0, LateInView = 0;
		bool bScreenChanged = false;
	};

	struct FHitch
	{
		int32 FrameIndex = 0;
		TArray<FString> SyncLoads, LogLines, Scopes;
	};

	struct FSegment
	{
		FString Label;
		double StartTime = 0.0, EndTime = 0.0;
		uint64 MemStartMB = 0, MemEndMB = 0, MemPeakMB = 0;
		TMap<FString, double> ScopeMs;      // total ms per scope in this segment
		TMap<FString, double> ScopeMaxMs;   // longest single frame of that scope in this segment
		TMap<FString, int64> ScopeCalls;
		TArray<FString> SyncLoads;
		int32 GcCount = 0;
	};

	struct FRoute : public TSharedFromThis<FRoute>
	{
		TArray<FString> Lines;
		int32 Next = 0;
		FString Prefix;
		TWeakObjectPtr<UWorld> World;
		double WaitUntil = 0.0;
		// walking
		bool bWalking = false;
		FVector WalkTarget = FVector::ZeroVector;
		int32 WalkStartScreen = -1;
		double WalkUntil = 0.0;
		FString WalkShotDir;                 // walk ... <dir> <interval>: a screenshot strip while walking
		double WalkShotInterval = 0.0, NextWalkShot = 0.0;
		int32 WalkShotIndex = 0;
		// recording
		TArray<FFrame> Frames;
		TArray<FSegment> Segments;
		TArray<FHitch> Hitches;
		TArray<FString> FrameSyncLoads;
		double GcStart = 0.0, FrameGcMs = 0.0;
		int32 FrameGcCount = 0;
		int32 LastScreen = -1;
		uint64 LastFrame = 0;
		double LastTime = 0.0;
		TMap<const DinkPerf::FScopeStat*, uint64> LastCycles;
		TMap<const DinkPerf::FScopeStat*, uint64> LastCalls;
		FDelegateHandle SyncHandle, PreGcHandle, PostGcHandle;
		bool bFinished = false;
	};

	int32 CurrentScreenNumber(UWorld* World)
	{
		const UDinkGreyboxSubsystem* Grey = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
		const ADinkScreenVolume* Screen = Grey ? Grey->GetCurrentScreen() : nullptr;
		return Screen ? Screen->ScreenNumber : -1;
	}

	uint64 UsedMB() { return FPlatformMemory::GetStats().UsedPhysical / (1024 * 1024); }

	double Percentile(TArray<double> Values, double P)
	{
		if (Values.IsEmpty()) return 0.0;
		Values.Sort();
		const double Rank = P * (Values.Num() - 1);
		const int32 Lo = FMath::FloorToInt32(Rank), Hi = FMath::Min(Lo + 1, Values.Num() - 1);
		return FMath::Lerp(Values[Lo], Values[Hi], Rank - Lo);
	}

	void Sample(FRoute& R)
	{
		UWorld* World = R.World.Get();
		const double Now = FPlatformTime::Seconds();
		FFrame F;
		F.Frame = GFrameCounter;
		F.Time = Now;
		F.FrameMs = (Now - R.LastTime) * 1000.0;
		F.GameMs = FPlatformTime::ToMilliseconds(GGameThreadTime);
		F.RenderMs = FPlatformTime::ToMilliseconds(GRenderThreadTime);
		F.RhiMs = FPlatformTime::ToMilliseconds(GRHIThreadTime);
		F.GpuMs = FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0));
		F.Draws = GNumDrawCallsRHI[0];
		F.Prims = GNumPrimitivesDrawnRHI[0];
		F.AsyncPackages = GetNumAsyncPackages();
		F.SyncLoads = R.FrameSyncLoads.Num();
		F.GcMs = R.FrameGcMs;
		F.Segment = R.Segments.Num() - 1;
		F.Screen = CurrentScreenNumber(World);
		F.PendingInView = DinkPerf::GPendingInView;
		F.LateInView = DinkPerf::GLateInViewDressed;
		DinkPerf::GLateInViewDressed = 0;
		F.bScreenChanged = F.Screen != R.LastScreen;
		F.PsoPrecache = int32(PipelineStateCache::NumActivePrecacheRequests());
		F.ShaderJobs = int32(FShaderPipelineCache::NumPrecompilesRemaining());
#if WITH_EDITOR
		if (GShaderCompilingManager) F.ShaderJobs += GShaderCompilingManager->GetNumRemainingJobs();
#endif
		R.LastScreen = F.Screen;
		R.LastTime = Now;

		// scope deltas of this frame
		TArray<TPair<double, FString>> FrameScopes;
		for (const DinkPerf::FScopeStat* S = DinkPerf::FirstStat(); S; S = S->Next)
		{
			const uint64 Cycles = S->Cycles - R.LastCycles.FindRef(S);
			const uint64 Calls = S->Calls - R.LastCalls.FindRef(S);
			R.LastCycles.Add(S, S->Cycles);
			R.LastCalls.Add(S, S->Calls);
			if (!Calls) continue;
			const double Ms = FPlatformTime::ToMilliseconds64(Cycles);
			FrameScopes.Emplace(Ms, S->Name);
			if (F.Segment >= 0)
			{
				FSegment& Seg = R.Segments[F.Segment];
				Seg.ScopeMs.FindOrAdd(S->Name) += Ms;
				Seg.ScopeCalls.FindOrAdd(S->Name) += int64(Calls);
				double& Max = Seg.ScopeMaxMs.FindOrAdd(S->Name);
				Max = FMath::Max(Max, Ms);
			}
		}
		TArray<FString> LogLines;
		{
			FScopeLock Scoped(&HitchLog().Lock);
			LogLines = MoveTemp(HitchLog().Lines);
			HitchLog().Lines.Reset();
		}
		if (F.Segment >= 0)
		{
			FSegment& Seg = R.Segments[F.Segment];
			const uint64 Mem = UsedMB();
			Seg.MemPeakMB = FMath::Max(Seg.MemPeakMB, Mem);
			Seg.GcCount += R.FrameGcCount;
			for (const FString& P : R.FrameSyncLoads) if (Seg.SyncLoads.Num() < 200) Seg.SyncLoads.AddUnique(P);
			R.Frames.Add(F);
			if (F.FrameMs > 33.4)
			{
				FHitch H;
				H.FrameIndex = R.Frames.Num() - 1;
				H.SyncLoads = R.FrameSyncLoads;
				if (H.SyncLoads.Num() > 20) H.SyncLoads.SetNum(20);
				H.LogLines = MoveTemp(LogLines);
				FrameScopes.Sort([](const TPair<double, FString>& A, const TPair<double, FString>& B) { return A.Key > B.Key; });
				for (const TPair<double, FString>& S : FrameScopes)
					if (S.Key >= 1.0 && H.Scopes.Num() < 6) H.Scopes.Add(FString::Printf(TEXT("%s %.1f ms"), *S.Value, S.Key));
				R.Hitches.Add(MoveTemp(H));
			}
		}
		R.FrameSyncLoads.Reset();
		R.FrameGcMs = 0.0;
		R.FrameGcCount = 0;
	}

	void BeginSegment(FRoute& R, const FString& Label)
	{
		const double Now = FPlatformTime::Seconds();
		if (!R.Segments.IsEmpty())
		{
			R.Segments.Last().EndTime = Now;
			R.Segments.Last().MemEndMB = UsedMB();
		}
		FSegment& Seg = R.Segments.AddDefaulted_GetRef();
		Seg.Label = Label;
		Seg.StartTime = Now;
		Seg.MemStartMB = Seg.MemPeakMB = UsedMB();
		UE_LOG(LogDink, Display, TEXT("DINK PERF: segment %s"), *Label);
	}

	FString CvarString(const TCHAR* Name)
	{
		const IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(Name);
		return V ? V->GetString() : FString(TEXT("?"));
	}

	void WriteResults(FRoute& R)
	{
		if (!R.Segments.IsEmpty())
		{
			R.Segments.Last().EndTime = FPlatformTime::Seconds();
			R.Segments.Last().MemEndMB = UsedMB();
		}
		// frames.csv
		FString Csv = TEXT("frame,t,segment,frame_ms,game_ms,render_ms,rhi_ms,gpu_ms,draws,prims,async_pkgs,sync_loads,gc_ms,pso_precache,shader_jobs,screen,screen_changed,pending_in_view,late_in_view_dressed\n");
		const double T0 = R.Frames.IsEmpty() ? 0.0 : R.Frames[0].Time;
		for (const FFrame& F : R.Frames)
		{
			Csv += FString::Printf(TEXT("%llu,%.4f,%s,%.2f,%.2f,%.2f,%.2f,%.2f,%d,%d,%d,%d,%.2f,%d,%d,%d,%d,%d,%d\n"), F.Frame, F.Time - T0,
				*R.Segments[F.Segment].Label, F.FrameMs, F.GameMs, F.RenderMs, F.RhiMs, F.GpuMs, F.Draws, F.Prims, F.AsyncPackages,
				F.SyncLoads, F.GcMs, F.PsoPrecache, F.ShaderJobs, F.Screen, F.bScreenChanged ? 1 : 0, F.PendingInView, F.LateInView);
		}
		FFileHelper::SaveStringToFile(Csv, *(R.Prefix + TEXT("_frames.csv")));

		// summary.json
		TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
		Root->SetStringField(TEXT("route"), R.Lines.IsEmpty() ? FString() : FString::Join(R.Lines, TEXT("\n")));
		Root->SetStringField(TEXT("build"), WITH_EDITOR ? TEXT("editor") : TEXT("packaged"));
		Root->SetStringField(TEXT("rhi"), GDynamicRHI ? GDynamicRHI->GetName() : TEXT("none"));
		Root->SetStringField(TEXT("adapter"), GRHIAdapterName);
		Root->SetNumberField(TEXT("cores"), FPlatformMisc::NumberOfCores());
		Root->SetNumberField(TEXT("worker_threads"), FPlatformMisc::NumberOfWorkerThreadsToSpawn());
		if (GEngine && GEngine->GameViewport && GEngine->GameViewport->Viewport)
		{
			const FIntPoint Size = GEngine->GameViewport->Viewport->GetSizeXY();
			Root->SetStringField(TEXT("viewport"), FString::Printf(TEXT("%dx%d"), Size.X, Size.Y));
		}
		TArray<TSharedPtr<FJsonValue>> Segs;
		for (int32 Index = 0; Index < R.Segments.Num(); ++Index)
		{
			const FSegment& S = R.Segments[Index];
			TArray<double> Ms, Game, Render, Rhi, Gpu, Draws, Prims;
			int32 Over33 = 0, Over50 = 0, Over100 = 0, SyncLoads = 0, PendingFrames = 0, LateDressed = 0;
			double GcMs = 0.0, MaxMs = 0.0;
			for (const FFrame& F : R.Frames)
			{
				if (F.Segment != Index) continue;
				Ms.Add(F.FrameMs); Game.Add(F.GameMs); Render.Add(F.RenderMs); Rhi.Add(F.RhiMs); Gpu.Add(F.GpuMs);
				Draws.Add(F.Draws); Prims.Add(F.Prims);
				Over33 += F.FrameMs > 33.4; Over50 += F.FrameMs > 50.0; Over100 += F.FrameMs > 100.0;
				SyncLoads += F.SyncLoads; GcMs += F.GcMs; MaxMs = FMath::Max(MaxMs, F.FrameMs); PendingFrames += F.PendingInView > 0; LateDressed += F.LateInView;
			}
			auto Mean = [](const TArray<double>& V) { double Sum = 0; for (double X : V) Sum += X; return V.IsEmpty() ? 0.0 : Sum / V.Num(); };
			TSharedRef<FJsonObject> J = MakeShared<FJsonObject>();
			J->SetStringField(TEXT("label"), S.Label);
			J->SetNumberField(TEXT("frames"), Ms.Num());
			J->SetNumberField(TEXT("seconds"), S.EndTime - S.StartTime);
			J->SetNumberField(TEXT("fps"), Ms.IsEmpty() ? 0.0 : 1000.0 / Mean(Ms));
			J->SetNumberField(TEXT("avg_ms"), Mean(Ms));
			J->SetNumberField(TEXT("p50_ms"), Percentile(Ms, 0.50));
			J->SetNumberField(TEXT("p95_ms"), Percentile(Ms, 0.95));
			J->SetNumberField(TEXT("p99_ms"), Percentile(Ms, 0.99));
			J->SetNumberField(TEXT("max_ms"), MaxMs);
			J->SetNumberField(TEXT("hitches_33"), Over33);
			J->SetNumberField(TEXT("hitches_50"), Over50);
			J->SetNumberField(TEXT("hitches_100"), Over100);
			J->SetNumberField(TEXT("game_ms"), Mean(Game));
			J->SetNumberField(TEXT("render_ms"), Mean(Render));
			J->SetNumberField(TEXT("rhi_ms"), Mean(Rhi));
			J->SetNumberField(TEXT("gpu_ms"), Mean(Gpu));
			J->SetNumberField(TEXT("gpu_p95_ms"), Percentile(Gpu, 0.95));
			J->SetNumberField(TEXT("game_p95_ms"), Percentile(Game, 0.95));
			J->SetNumberField(TEXT("draws"), Mean(Draws));
			J->SetNumberField(TEXT("prims"), Mean(Prims));
			J->SetNumberField(TEXT("mem_start_mb"), double(S.MemStartMB));
			J->SetNumberField(TEXT("mem_end_mb"), double(S.MemEndMB));
			J->SetNumberField(TEXT("mem_peak_mb"), double(S.MemPeakMB));
			J->SetNumberField(TEXT("sync_loads"), SyncLoads);
			J->SetNumberField(TEXT("frames_undressed_in_view"), PendingFrames);
			J->SetNumberField(TEXT("late_in_view_dressed"), LateDressed);
			J->SetNumberField(TEXT("gc_count"), S.GcCount);
			J->SetNumberField(TEXT("gc_ms"), GcMs);
			TArray<TSharedPtr<FJsonValue>> Loads;
			for (const FString& P : S.SyncLoads) Loads.Add(MakeShared<FJsonValueString>(P));
			J->SetArrayField(TEXT("sync_load_packages"), Loads);
			TSharedRef<FJsonObject> Scopes = MakeShared<FJsonObject>();
			for (const TPair<FString, double>& P : S.ScopeMs)
			{
				TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
				O->SetNumberField(TEXT("ms_per_frame"), Ms.IsEmpty() ? 0.0 : P.Value / Ms.Num());
				O->SetNumberField(TEXT("max_frame_ms"), S.ScopeMaxMs.FindRef(P.Key));
				O->SetNumberField(TEXT("calls_per_frame"), Ms.IsEmpty() ? 0.0 : double(S.ScopeCalls.FindRef(P.Key)) / Ms.Num());
				Scopes->SetObjectField(P.Key, O);
			}
			J->SetObjectField(TEXT("scopes"), Scopes);
			Segs.Add(MakeShared<FJsonValueObject>(J));
		}
		Root->SetArrayField(TEXT("segments"), Segs);
		TArray<TSharedPtr<FJsonValue>> Hitches;
		for (const FHitch& H : R.Hitches)
		{
			const FFrame& F = R.Frames[H.FrameIndex];
			TSharedRef<FJsonObject> J = MakeShared<FJsonObject>();
			J->SetStringField(TEXT("segment"), R.Segments[F.Segment].Label);
			J->SetNumberField(TEXT("t"), F.Time - T0);
			J->SetNumberField(TEXT("frame_ms"), F.FrameMs);
			J->SetNumberField(TEXT("game_ms"), F.GameMs);
			J->SetNumberField(TEXT("render_ms"), F.RenderMs);
			J->SetNumberField(TEXT("gpu_ms"), F.GpuMs);
			J->SetNumberField(TEXT("gc_ms"), F.GcMs);
			J->SetNumberField(TEXT("screen"), F.Screen);
			J->SetBoolField(TEXT("screen_changed"), F.bScreenChanged || (H.FrameIndex > 0 && R.Frames[H.FrameIndex - 1].bScreenChanged));
			J->SetNumberField(TEXT("async_pkgs"), F.AsyncPackages);
			J->SetNumberField(TEXT("pso_precache"), F.PsoPrecache);
			J->SetNumberField(TEXT("shader_jobs"), F.ShaderJobs);
			auto Arr = [](const TArray<FString>& In) { TArray<TSharedPtr<FJsonValue>> Out; for (const FString& S : In) Out.Add(MakeShared<FJsonValueString>(S)); return Out; };
			J->SetArrayField(TEXT("sync_loads"), Arr(H.SyncLoads));
			J->SetArrayField(TEXT("log"), Arr(H.LogLines));
			J->SetArrayField(TEXT("scopes"), Arr(H.Scopes));
			Hitches.Add(MakeShared<FJsonValueObject>(J));
		}
		Root->SetArrayField(TEXT("hitches"), Hitches);
		TSharedRef<FJsonObject> Settings = MakeShared<FJsonObject>();
		for (const TCHAR* Name : { TEXT("sg.ResolutionQuality"), TEXT("sg.ShadowQuality"), TEXT("sg.GlobalIlluminationQuality"),
			TEXT("sg.ReflectionQuality"), TEXT("sg.FoliageQuality"), TEXT("sg.EffectsQuality"), TEXT("sg.PostProcessQuality"),
			TEXT("sg.TextureQuality"), TEXT("sg.ShadingQuality"), TEXT("sg.ViewDistanceQuality"), TEXT("r.ScreenPercentage"),
			TEXT("r.DynamicGlobalIlluminationMethod"), TEXT("r.ReflectionMethod"), TEXT("r.Shadow.Virtual.Enable"),
			TEXT("r.AntiAliasingMethod"), TEXT("dink.GrassDensity"), TEXT("t.MaxFPS"), TEXT("r.VSync") })
			Settings->SetStringField(Name, CvarString(Name));
		Root->SetObjectField(TEXT("settings_at_end"), Settings);
		// every Dink switch as it stood at the end (the other streams' layers: dink.Anim.*, dink.Hair.*, dink.World.*,
		// audio life, ...), so their cost is visible per run
		TSharedRef<FJsonObject> DinkSettings = MakeShared<FJsonObject>();
		IConsoleManager::Get().ForEachConsoleObjectThatStartsWith(FConsoleObjectVisitor::CreateLambda([&DinkSettings](const TCHAR* Name, IConsoleObject* Object)
		{
			if (IConsoleVariable* V = Object ? Object->AsVariable() : nullptr) DinkSettings->SetStringField(Name, V->GetString());
		}), TEXT("dink."));
		Root->SetObjectField(TEXT("dink_settings"), DinkSettings);
		FString Json;
		const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Json);
		FJsonSerializer::Serialize(Root, Writer);
		FFileHelper::SaveStringToFile(Json, *(R.Prefix + TEXT("_summary.json")));
		UE_LOG(LogDink, Display, TEXT("DINK PERF: wrote %s_summary.json (%d segments, %d frames, %d hitches over 33 ms)"), *R.Prefix,
			R.Segments.Num(), R.Frames.Num(), R.Hitches.Num());
	}

	void Finish(TSharedRef<FRoute> R)
	{
		if (R->bFinished) return;
		R->bFinished = true;
		WriteResults(*R);
		FCoreDelegates::OnSyncLoadPackage.Remove(R->SyncHandle);
		FCoreUObjectDelegates::GetPreGarbageCollectDelegate().Remove(R->PreGcHandle);
		FCoreUObjectDelegates::GetPostGarbageCollect().Remove(R->PostGcHandle);
		if (GLog) GLog->RemoveOutputDevice(&HitchLog());
	}

	bool StepWalk(FRoute& R, double Now)
	{
		UWorld* W = R.World.Get();
		APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
		APawn* Pawn = PC ? PC->GetPawn() : nullptr;
		if (!Pawn) { R.bWalking = false; return false; }
		const int32 Screen = CurrentScreenNumber(W);
		const FVector To = R.WalkTarget - Pawn->GetActorLocation();
		const TCHAR* Result = nullptr;
		if (Screen != R.WalkStartScreen) Result = TEXT("screen changed");
		else if (To.Size2D() < 12.0) Result = TEXT("arrived");
		else if (Now > R.WalkUntil) Result = TEXT("timed out");
		if (Result)
		{
			UE_LOG(LogDink, Display, TEXT("DINK PERF: walk %s, now on screen %d"), Result, Screen);
			R.bWalking = false;
			return false;
		}
		Pawn->AddMovementInput(To.GetSafeNormal2D(), 1.f);
		if (!R.WalkShotDir.IsEmpty() && Now >= R.NextWalkShot)
		{
			R.NextWalkShot = Now + R.WalkShotInterval;
			FScreenshotRequest::RequestScreenshot(FString::Printf(TEXT("%s/strip_%03d.png"), *R.WalkShotDir, R.WalkShotIndex++), false, false);
		}
		return true;
	}

	bool TickRoute(TSharedRef<FRoute> R)
	{
		if (R->bFinished) return false;
		UWorld* World = R->World.Get();
		if (!World)
		{
			Finish(R);
			return false;
		}
		if (R->LastFrame != GFrameCounter)
		{
			R->LastFrame = GFrameCounter;
			Sample(*R);
		}
		const double Now = FPlatformTime::Seconds();
		if (R->bWalking && StepWalk(*R, Now)) return true;
		while (R->Next < R->Lines.Num())
		{
			if (Now < R->WaitUntil) return true;
			FString Line = R->Lines[R->Next++].TrimStartAndEnd();
			int32 Hash;
			if (Line.FindChar(TEXT('#'), Hash)) Line = Line.Left(Hash).TrimEnd();
			if (Line.IsEmpty()) continue;
			TArray<FString> Args;
			Line.ParseIntoArrayWS(Args);
			const FString Op = Args[0].ToLower();
			if (Op == TEXT("segment"))
			{
				BeginSegment(*R, Args.Num() > 1 ? Line.RightChop(8).TrimStart() : FString::Printf(TEXT("segment_%d"), R->Segments.Num()));
				continue;
			}
			if (Op == TEXT("wait"))
			{
				R->WaitUntil = Now + (Args.Num() > 1 ? FCString::Atod(*Args[1]) : 1.0);
				return true;
			}
			if (Op == TEXT("goto"))
			{
				GEngine->Exec(World, *(TEXT("dink.Goto ") + Line.RightChop(5)));
				continue;
			}
			if (Op == TEXT("walk") && Args.Num() >= 3)
			{
				const UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
				const ADinkScreenVolume* Screen = Grey ? Grey->GetCurrentScreen() : nullptr;
				if (!Screen) { UE_LOG(LogDink, Warning, TEXT("DINK PERF: walk without a current screen")); continue; }
				R->WalkTarget = DinkLayout::MapPixelToUnreal(Screen->Corners, FCString::Atod(*Args[1]), FCString::Atod(*Args[2]));
				R->WalkStartScreen = Screen->ScreenNumber;
				R->WalkUntil = Now + (Args.Num() > 3 ? FCString::Atod(*Args[3]) : 8.0);
				R->WalkShotDir = Args.Num() > 5 ? Args[4] : FString();
				R->WalkShotInterval = Args.Num() > 5 ? FMath::Max(0.05, FCString::Atod(*Args[5])) : 0.0;
				R->NextWalkShot = Now;
				R->WalkShotIndex = 0;
				R->bWalking = true;
				return true;
			}
			if (Op == TEXT("shot") && Args.Num() >= 2)
			{
				// viewport without UI; give it half a second (put shots in their own segment: the frame is slow)
				FScreenshotRequest::RequestScreenshot(Line.RightChop(5).TrimStartAndEnd(), false, false);
				R->WaitUntil = Now + 0.5;
				return true;
			}
						if (Op == TEXT("end"))
			{
				Finish(R);
				continue;   // a `quit` may follow
			}
			UE_LOG(LogDink, Display, TEXT("DINK PERF: exec %s"), *Line);
			GEngine->Exec(World, *Line);
		}
		if (Now < R->WaitUntil || R->bWalking) return true;
		Finish(R);
		return false;
	}
}

static FAutoConsoleCommandWithWorldAndArgs GDinkPerfRouteCommand(
	TEXT("dink.Perf.Route"), TEXT("dink.Perf.Route <route file> <output prefix>: run a scripted benchmark route and write <prefix>_frames.csv and <prefix>_summary.json."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || Args.Num() < 2) { UE_LOG(LogDink, Warning, TEXT("dink.Perf.Route <route file> <output prefix>")); return; }
		TSharedRef<FRoute> R = MakeShared<FRoute>();
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *Args[0])) { UE_LOG(LogDink, Warning, TEXT("DINK PERF: cannot read %s"), *Args[0]); return; }
		Text.ParseIntoArrayLines(R->Lines, false);
		R->Prefix = Args[1];
		R->World = World;
		R->LastTime = FPlatformTime::Seconds();
		R->LastFrame = GFrameCounter;
		R->LastScreen = CurrentScreenNumber(World);
		for (const DinkPerf::FScopeStat* S = DinkPerf::FirstStat(); S; S = S->Next) { R->LastCycles.Add(S, S->Cycles); R->LastCalls.Add(S, S->Calls); }
		TWeakPtr<FRoute> Weak = R;
		R->SyncHandle = FCoreDelegates::OnSyncLoadPackage.AddLambda([Weak](const FString& Package)
		{
			if (TSharedPtr<FRoute> P = Weak.Pin()) if (P->FrameSyncLoads.Num() < 64) P->FrameSyncLoads.Add(Package);
		});
		R->PreGcHandle = FCoreUObjectDelegates::GetPreGarbageCollectDelegate().AddLambda([Weak]()
		{
			if (TSharedPtr<FRoute> P = Weak.Pin()) P->GcStart = FPlatformTime::Seconds();
		});
		R->PostGcHandle = FCoreUObjectDelegates::GetPostGarbageCollect().AddLambda([Weak]()
		{
			if (TSharedPtr<FRoute> P = Weak.Pin()) { P->FrameGcMs += (FPlatformTime::Seconds() - P->GcStart) * 1000.0; ++P->FrameGcCount; }
		});
		if (GLog && !GLog->IsRedirectingTo(&HitchLog())) GLog->AddOutputDevice(&HitchLog());
		UE_LOG(LogDink, Display, TEXT("DINK PERF: route %s (%d lines) -> %s"), *Args[0], R->Lines.Num(), *R->Prefix);
		FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([R](float) { return TickRoute(R); }));
	}));

#endif // !UE_BUILD_SHIPPING

// Counts synchronous package loads on the game thread while it is on (test and console use).
namespace DinkPerf
{
	DINKCORE_API int32 GSyncLoadsCounted = 0;
	DINKCORE_API int32 GPendingInView = 0;
	DINKCORE_API int32 GLateInViewDressed = 0;
	DINKCORE_API TArray<FString> GSyncLoadPackages;
	static FDelegateHandle GSyncCountHandle;
	DINKCORE_API void SetSyncLoadCounting(bool bOn)
	{
		if (bOn && !GSyncCountHandle.IsValid())
		{
			GSyncLoadsCounted = 0;
			GSyncLoadPackages.Reset();
			GSyncCountHandle = FCoreDelegates::OnSyncLoadPackage.AddLambda([](const FString& Package)
			{
				++GSyncLoadsCounted;
				if (GSyncLoadPackages.Num() < 256) GSyncLoadPackages.Add(Package);
			});
		}
		else if (!bOn && GSyncCountHandle.IsValid())
		{
			FCoreDelegates::OnSyncLoadPackage.Remove(GSyncCountHandle);
			GSyncCountHandle.Reset();
		}
	}
}
