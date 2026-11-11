#include "Modules/ModuleManager.h"
#include "Misc/CoreDelegates.h"
#include "DinkProbeHold.h"

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
	}

	virtual void ShutdownModule() override
	{
		#if WITH_DEV_AUTOMATION_TESTS
		DinkStopAttackQueueObserver();
		#endif
		FCoreDelegates::OnFEngineLoopInitComplete.Remove(InitCompleteHandle);
	}

private:
	FDelegateHandle InitCompleteHandle;
};

IMPLEMENT_MODULE(FDinkProbeModule, DinkProbe)
