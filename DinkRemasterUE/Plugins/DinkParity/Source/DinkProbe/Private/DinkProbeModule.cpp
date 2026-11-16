#include "Modules/ModuleManager.h"
#include "Misc/CoreDelegates.h"
#include "DinkProbeHold.h"
#include "DinkBeatCapture.h"

#if WITH_DEV_AUTOMATION_TESTS
void DinkStopAttackQueueObserver();
#endif

// The tests register themselves through IMPLEMENT_SIMPLE_AUTOMATION_TEST in DinkProbeTests.cpp.
class FDinkProbeModule : public FDefaultModuleImpl
{
public:
	virtual void StartupModule() override
	{
		// Packaged-game start-up alignment with PIE; a no-op unless the game was started with -DinkProbeHold.
		InitCompleteHandle = FCoreDelegates::OnFEngineLoopInitComplete.AddStatic(&DinkProbeHold::Engage);
		// Story-beat screenshots for rendered play-throughs; a no-op unless -DinkBeatShots=<dir> or dink.BeatShots turns it on.
		DinkBeatCapture::Startup();
	}

	virtual void ShutdownModule() override
	{
		#if WITH_DEV_AUTOMATION_TESTS
		DinkStopAttackQueueObserver();
		#endif
		DinkBeatCapture::Shutdown();
		FCoreDelegates::OnFEngineLoopInitComplete.Remove(InitCompleteHandle);
	}

private:
	FDelegateHandle InitCompleteHandle;
};

IMPLEMENT_MODULE(FDinkProbeModule, DinkProbe)
