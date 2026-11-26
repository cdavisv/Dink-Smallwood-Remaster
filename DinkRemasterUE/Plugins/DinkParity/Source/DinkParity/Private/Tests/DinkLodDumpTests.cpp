// Takeover A5 (25 Nov 2026): dink.LodDump, the skeletal LOD screen sizes of the people meshes and the LOD the play camera
// shows at play distance (DinkLodDump.h). The rule is the engine's (FSkeletalMeshObject::UpdateMinDesiredLODLevel); this checks
// the maths on known numbers and writes the shipped meshes' table (Saved/Art/lod_screen_sizes.txt) headless.
#include "DinkTestHelpers.h"
#include "DinkLodDump.h"
#include "HAL/IConsoleManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkLodDumpTest, "Dink.Art.LodScreenSizesDump", DINK_TEST_FLAGS)
bool FDinkLodDumpTest::RunTest(const FString&)
{
	TestNotNull(TEXT("dink.LodDump is registered"), IConsoleManager::Get().FindConsoleObject(TEXT("dink.LodDump")));
	// 90 degrees horizontal on 16:9: ScreenMultiple = 0.5 * 16/9; a 100 cm radius at 1000 cm covers (0.0889)^2 = 0.0079.
	const float R2 = DinkLodDump::ScreenRadiusSquared(100.f, 1000.f, 90.f, 16.f / 9.f);
	TestTrue(FString::Printf(TEXT("screen radius squared %.5f"), R2), FMath::IsNearlyEqual(R2, FMath::Square(.5f * 16.f / 9.f * .1f), 1.e-5f));
	// screen sizes 1, 0.3, 0.15, 0.1: an LOD is used while the screen radius is below half its size (0.15, 0.075, 0.05)
	const TArray<float> Sizes = {1.f, .3f, .15f, .1f};
	TestEqual(TEXT("radius 0.0889: LOD1's half size 0.15 > 0.0889 but LOD2's 0.075 is not: LOD1"), DinkLodDump::PickLod(Sizes, R2), 1);
	TestEqual(TEXT("close up: LOD0"), DinkLodDump::PickLod(Sizes, FMath::Square(.4f)), 0);
	TestEqual(TEXT("far: the last LOD"), DinkLodDump::PickLod(Sizes, FMath::Square(.01f)), 3);
	TestEqual(TEXT("one LOD: always 0"), DinkLodDump::PickLod({1.f}, 0.f), 0);
	const FString Text = DinkLodDump::Write(nullptr, {300.f, 500.f, 800.f, 1200.f, 2000.f});
	TArray<FString> Lines;
	Text.ParseIntoArrayLines(Lines);
	for (const FString& L : Lines) AddInfo(L);
	TestTrue(TEXT("the dump lists the people meshes"), Lines.Num() > 8 && Text.Contains(TEXT("SK_OldMan_Photoreal")) && Text.Contains(TEXT("SK_Maiden")));
	TestFalse(TEXT("every listed mesh loads"), Text.Contains(TEXT("not loaded")));
	return true;
}
