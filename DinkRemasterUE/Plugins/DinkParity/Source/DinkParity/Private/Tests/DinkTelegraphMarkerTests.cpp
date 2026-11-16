// Dink.AI.TelegraphMarkerOffByDefault: the adaptation layer's wind-up drew a red wireframe debug sphere over every attacker
// (the greybox's telegraph placeholder). The playthrough QA of 15 Nov 2026 saw it over Seth and the pillbugs in a rendered game.
// It is a debug marker now: off unless dink.TelegraphMarker 1. The wind-up itself (timing, facing) is not touched.
#include "DinkTestHelpers.h"
#include "HAL/IConsoleManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkTelegraphMarkerTest, "Dink.AI.TelegraphMarkerOffByDefault", DINK_TEST_FLAGS)
bool FDinkTelegraphMarkerTest::RunTest(const FString&)
{
	IConsoleVariable* Marker = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.TelegraphMarker"));
	if (!TestNotNull(TEXT("dink.TelegraphMarker exists"), Marker)) return false;
	TestEqual(TEXT("the greybox wind-up marker is off in play by default"), Marker->GetInt(), 0);
	return true;
}
