// Lightweight named timing scopes for the perf benchmark (dink.Perf.Route) and Unreal Insights.
//
//   void UMySubsystem::Tick(float DeltaTime) { DINK_PERF_SCOPE(Dink_Environment_Tick); ... }
//
// Each scope costs two cycle-counter reads and adds a CPU trace event (visible in Insights with -trace=cpu).
// The totals are game-thread only (every Dink tick runs there); a scope entered on another thread is traced
// but not counted. dink.Perf.Route reads the totals per frame to attribute hitches and per-segment costs.
#pragma once

#include "CoreMinimal.h"
#include "HAL/PlatformTime.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace DinkPerf
{
	struct FScopeStat
	{
		const TCHAR* Name = nullptr;
		uint64 Cycles = 0;   // total since start
		uint64 Calls = 0;
		uint64 MaxCycles = 0; // longest single call since start
		FScopeStat* Next = nullptr;
	};

	/** Adds the stat to the global list (once per call site) and returns it. */
	DINKCORE_API FScopeStat& Register(FScopeStat& Stat);
	/** Head of the registered list (game thread). */
	DINKCORE_API FScopeStat* FirstStat();

	struct FScope
	{
		FScopeStat& Stat;
		const uint64 Start;
		const bool bCount;
		explicit FScope(FScopeStat& In) : Stat(In), Start(FPlatformTime::Cycles64()), bCount(IsInGameThread()) {}
		~FScope()
		{
			if (!bCount) return;
			const uint64 Took = FPlatformTime::Cycles64() - Start;
			Stat.Cycles += Took;
			++Stat.Calls;
			Stat.MaxCycles = FMath::Max(Stat.MaxCycles, Took);
		}
	};
}

// Counting scopes exist outside Shipping (Development, DebugGame, Test, the editor); a Shipping build keeps only the
// Insights trace event.
#ifndef DINK_PERF_SCOPES
#define DINK_PERF_SCOPES (!UE_BUILD_SHIPPING)
#endif

#if DINK_PERF_SCOPES
#define DINK_PERF_SCOPE(Name) \
	static DinkPerf::FScopeStat& UE_JOIN(DinkPerfStat_, __LINE__) = DinkPerf::Register(*new DinkPerf::FScopeStat{TEXT(#Name)}); \
	TRACE_CPUPROFILER_EVENT_SCOPE(Name); \
	DinkPerf::FScope UE_JOIN(DinkPerfScope_, __LINE__)(UE_JOIN(DinkPerfStat_, __LINE__))
#else
#define DINK_PERF_SCOPE(Name) TRACE_CPUPROFILER_EVENT_SCOPE(Name)
#endif

namespace DinkPerf
{
	/** Counts synchronous package loads on the game thread while on (Dink.Perf tests, dink.Perf.SyncLoads). */
	DINKCORE_API void SetSyncLoadCounting(bool bOn);
	extern DINKCORE_API int32 GSyncLoadsCounted;
	extern DINKCORE_API TArray<FString> GSyncLoadPackages;

	/**
	 * Screens within the camera's view reach that are still waiting to be dressed this frame (set by the environment's
	 * neighbour queue every tick, 0 on the master path, which dresses everything in the entry frame). dink.Perf.Route
	 * records it per frame: any frame above 0 is a frame where cards could turn into meshes in view.
	 */
	extern DINKCORE_API int32 GPendingInView;
	/** In-view screens dressed this frame AFTER the frame the queue was made (each one is a possible pop-in in view). */
	extern DINKCORE_API int32 GLateInViewDressed;
}

namespace DinkPerf
{
	/**
	 * dink.Perf.Fixes (default 1): the perf-stutter stream's optimisations. 0 restores the code paths as they were on
	 * master 49627fc9 (whole-world walks on screen entry, every-frame card billboarding over the whole world, dressing
	 * of every neighbour screen in the entry frame, synchronous loads of town meshes and water masks), so one build
	 * measures before and after. Presentation only either way: the 1997 simulation never reads any of it.
	 */
	DINKCORE_API bool FixesEnabled();

	/**
	 * dink.Perf.StaticForestShadows (default 1, under dink.Perf.Fixes): a wind-swayed vegetation mesh (an SM_Veg_* mesh:
	 * trees, bushes, ferns, thorns, forest strips) keeps cached virtual shadow pages in its rest pose instead of having
	 * them re-rendered every frame (39 of 52 ms of GPU time in the pine forest at Epic, 15 Nov benchmark). Call before
	 * the component is registered. Decided by mesh, never per placement; the mesh itself still sways.
	 */
	DINKCORE_API void CacheVegetationShadows(class UPrimitiveComponent& Component, const class UStaticMesh* Mesh);
}
