#include "DinkExpanded.h"
#include "DinkExpandedWorldSubsystem.h"

#include "DinkGameplay.h"
#include "DinkInkStory.h"
#include "DinkSaveGame.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"
#include "DinkOriginComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace DinkExpandedTest
{
	/** A small registry: pack 9 ("testbed"), two screens on one sheet, one placement, one join from 1997 screen 301. */
	const TCHAR* TestbedJson = TEXT(R"({
		"schema": "dink-expanded/1",
		"packs": [{
			"id": "testbed", "number": 9, "name": "Testbed", "wave": "test", "status": "greybox", "draft": true,
			"sheets": [{"id": "main", "kind": "wilderness", "direction": [-1, 0], "gap_m": 1500}],
			"screens": [
				{"screen": 300, "grid": [1, 0], "sheet": "main", "name": "East", "kind": "wilderness", "region": "testbed", "base_script": "x9-base", "music": 1002, "solids": [[0, 0, 600, 30]]},
				{"screen": 268, "grid": [0, 0], "sheet": "main", "name": "West", "kind": "wilderness", "region": "testbed"}
			],
			"placements": [{"screen": 300, "index": 1, "x": 300, "y": 200, "seq": 231, "frame": 1, "brain": 0, "script": "x9-npc", "kind": "npc", "name": "Someone"}],
			"joins": [{"id": "testbed_in", "from": {"screen": 301, "rect": [200, 160, 240, 240]}, "to": {"screen": 300, "point": [520, 200]},
				"back": {"screen": 300, "rect": [570, 160, 600, 240]}, "return": {"screen": 301, "point": [260, 200]}}]
		}]
	})");

	/** Saves and restores the switch state around a test. */
	struct FSwitchGuard
	{
		bool bWas = DinkExpanded::IsEnabled();
		FDinkExpandedRegistry Was = DinkExpanded::GetRegistry();
		FString Story = FDinkInkStory::StoryDataOverrideDir();
		TArray<FString> Extra = FDinkGameplayData::ExtraDataDirs();
		~FSwitchGuard()
		{
			DinkExpanded::ApplySwitch(false);
			if (bWas)
			{
				DinkExpanded::ApplyForTest(Was, Story, Extra.Num() ? Extra.Last() : FString());
			}
			FDinkInkStory::StoryDataOverrideDir() = Story;
			FDinkGameplayData::ExtraDataDirs() = Extra;
		}
	};

	FDinkScreenCorners Rect(double X, double Y, double W, double H)
	{
		FDinkScreenCorners C;
		C.NW = FVector2D(X, Y);
		C.NE = FVector2D(X + W, Y);
		C.SW = FVector2D(X, Y + H);
		C.SE = FVector2D(X + W, Y + H);
		return C;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkExpandedRegistryTest, "Dink.Expanded.Registry",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter)
bool FDinkExpandedRegistryTest::RunTest(const FString& Parameters)
{
	FDinkExpandedRegistry R;
	FString Error;
	TestTrue(FString::Printf(TEXT("testbed parses (%s)"), *Error), R.LoadFromJson(DinkExpandedTest::TestbedJson, Error));
	TestEqual(TEXT("one pack"), R.Packs.Num(), 1);
	TestEqual(TEXT("two screens"), R.NumScreens(), 2);
	TestTrue(TEXT("300 is a pack screen"), R.IsPackScreen(300));
	TestFalse(TEXT("301 (1997) is not"), R.IsPackScreen(301));
	TestTrue(TEXT("x9- is the pack's script namespace"), R.IsPackScript(TEXT("x9-npc")));
	TestFalse(TEXT("1997 scripts are not pack scripts"), R.IsPackScript(TEXT("s2-signe")));
	TestEqual(TEXT("join parsed"), R.Packs[0].Joins.Num(), 1);
	TestEqual(TEXT("join from 1997 screen 301"), R.Packs[0].Joins[0].FromScreen, 301);

	// Namespace and shape rules.
	auto Broken = [&](const TCHAR* From, const TCHAR* To)
	{
		FDinkExpandedRegistry B;
		FString E;
		const bool bOk = B.LoadFromJson(FString(DinkExpandedTest::TestbedJson).Replace(From, To), E);
		return !bOk && !E.IsEmpty();
	};
	TestTrue(TEXT("a base script outside x9- is refused"), Broken(TEXT("\"x9-base\""), TEXT("\"s1-base\"")));
	TestTrue(TEXT("a screen number past 768 is refused"), Broken(TEXT("\"screen\": 268"), TEXT("\"screen\": 900")));
	TestTrue(TEXT("a join from a pack screen is refused"), Broken(TEXT("\"from\": {\"screen\": 301"), TEXT("\"from\": {\"screen\": 268")));
	TestTrue(TEXT("a placement on a 1997 screen is refused"), Broken(TEXT("\"placements\": [{\"screen\": 300"), TEXT("\"placements\": [{\"screen\": 301")));
	TestTrue(TEXT("a wrong schema is refused"), Broken(TEXT("dink-expanded/1"), TEXT("dink-expanded/0")));
	TestTrue(TEXT("two screens on one grid cell are refused"), Broken(TEXT("\"grid\": [0, 0]"), TEXT("\"grid\": [1, 0]")));

	R.FilterPacks({TEXT("other")});
	TestEqual(TEXT("pack filter keeps only named packs"), R.Packs.Num(), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkExpandedSwitchTest, "Dink.Expanded.Switch",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter)
bool FDinkExpandedSwitchTest::RunTest(const FString& Parameters)
{
	DinkExpandedTest::FSwitchGuard Guard;
	const FString BaseStory = FPaths::ProjectContentDir() / TEXT("Dink/Data/Story/dink.json");
	const FString BasePlacements = FPaths::ProjectContentDir() / TEXT("Dink/Data/Gameplay/placements.csv");

	// Off: nothing hooked, the 1997 paths exactly.
	DinkExpanded::ApplySwitch(false);
	TestFalse(TEXT("off"), DinkExpanded::IsEnabled());
	TestTrue(TEXT("off: no story override"), FDinkInkStory::StoryDataOverrideDir().IsEmpty());
	TestEqual(TEXT("off: no extra gameplay dir"), FDinkGameplayData::ExtraDataDirs().Num(), 0);
	TestEqual(TEXT("off: the 1997 story file"), FDinkInkStory::GetDataPath(TEXT("dink.json")), BaseStory);
	TestEqual(TEXT("off: the 1997 placements"), FDinkGameplayData::GetDataPath(TEXT("placements.csv")), BasePlacements);
	TestEqual(TEXT("off: registry empty"), DinkExpanded::GetRegistry().Packs.Num(), 0);

	// On with a directory that holds no story: the override only answers for files it has.
	FDinkExpandedRegistry R;
	FString Error;
	R.LoadFromJson(DinkExpandedTest::TestbedJson, Error);
	const FString Empty = FPaths::ProjectIntermediateDir() / TEXT("DinkExpandedTestEmpty");
	DinkExpanded::ApplyForTest(R, Empty, Empty);
	TestTrue(TEXT("on"), DinkExpanded::IsEnabled());
	TestEqual(TEXT("on: a file the override lacks falls back to 1997"), FDinkInkStory::GetDataPath(TEXT("dink.json")), BaseStory);
	TestEqual(TEXT("on: 1997 gameplay files stay 1997"), FDinkGameplayData::GetDataPath(TEXT("placements.csv")), BasePlacements);

	// Off again: hooks cleared.
	DinkExpanded::ApplySwitch(false);
	TestTrue(TEXT("off again: no story override"), FDinkInkStory::StoryDataOverrideDir().IsEmpty());
	TestEqual(TEXT("off again: no extra gameplay dir"), FDinkGameplayData::ExtraDataDirs().Num(), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkExpandedLayoutTest, "Dink.Expanded.Layout",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter)
bool FDinkExpandedLayoutTest::RunTest(const FString& Parameters)
{
	FDinkExpandedRegistry R;
	FString Error;
	R.LoadFromJson(DinkExpandedTest::TestbedJson, Error);
	// The same 1997 world at two scales (as feat/world-scale may change them): the packs follow, nothing is hard-coded.
	for (const double Scale : {1.0, 1.6})
	{
		TArray<DinkExpanded::FBaseScreen> Base;
		for (int32 i = 0; i < 6; ++i)
		{
			Base.Add({301 + i, TEXT("wilderness"), DinkExpandedTest::Rect(i * 41.25 * Scale, 0, 41.25 * Scale, 27.5 * Scale)});
		}
		Base.Add({100, TEXT("settlement"), DinkExpandedTest::Rect(0, 27.5 * Scale, 60 * Scale, 40 * Scale)});
		const TMap<int32, FDinkScreenCorners> L = DinkExpanded::LayoutPackScreens(Base, R);
		TestEqual(TEXT("both pack screens laid out"), L.Num(), 2);
		const FDinkScreenCorners* East = L.Find(300);
		const FDinkScreenCorners* West = L.Find(268);
		if (!East || !West)
		{
			return false;
		}
		TestEqual(TEXT("width = median 1997 wilderness width"), FVector2D::Distance(East->NW, East->NE), 41.25 * Scale, 1e-6);
		TestEqual(TEXT("height = median 1997 wilderness height"), FVector2D::Distance(East->NW, East->SW), 27.5 * Scale, 1e-6);
		TestTrue(TEXT("grid neighbours share an edge"), West->NE.Equals(East->NW, 1e-6));
		// Direction (-1, 0): east edge of the sheet is the gap west of the 1997 world's west edge.
		TestTrue(FString::Printf(TEXT("sheet is at least 1500 m clear of the 1997 world (scale %.1f)"), Scale), East->NE.X <= -1500.0 + 1e-3);
		TestTrue(TEXT("and not much further (bisection is tight)"), East->NE.X >= -1500.0 - 0.01);
	}
	TestEqual(TEXT("no screen of a kind: the plan's default"), DinkExpanded::MedianScreenSize({}, TEXT("interior")).X, 600 * 0.025 * 1.75, 1e-9);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkExpandedWorldTest, "Dink.Expanded.World",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter)
bool FDinkExpandedWorldTest::RunTest(const FString& Parameters)
{
	DinkExpandedTest::FSwitchGuard Guard;
	FDinkExpandedRegistry R;
	FString Error;
	R.LoadFromJson(DinkExpandedTest::TestbedJson, Error);
	DinkExpanded::ApplyForTest(R, FString(), FString());

	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("DinkExpandedWorldTest"));
	FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
	Context.SetCurrentWorld(World);
	ON_SCOPE_EXIT
	{
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
	};
	// Two 1997 screens: 301 (the join's) and 302.
	for (int32 i = 0; i < 2; ++i)
	{
		ADinkScreenVolume* V = World->SpawnActor<ADinkScreenVolume>();
		V->ScreenNumber = 301 + i;
		V->Kind = TEXT("wilderness");
		V->Corners = DinkExpandedTest::Rect(i * 41.25, 0, 41.25, 27.5);
	}
	UDinkExpandedWorldSubsystem* Packs = World->GetSubsystem<UDinkExpandedWorldSubsystem>();
	if (!TestNotNull(TEXT("world subsystem exists while the switch is on"), Packs))
	{
		return false;
	}
	TestEqual(TEXT("two pack screens built"), Packs->BuildPacks(*World), 2);
	int32 PackVolumes = 0;
	for (TActorIterator<ADinkScreenVolume> It(World); It; ++It)
	{
		if (It->ScreenNumber == 301)
		{
			TestTrue(TEXT("the 1997 volume keeps its corners"), It->Corners == DinkExpandedTest::Rect(0, 0, 41.25, 27.5));
		}
		if (R.IsPackScreen(It->ScreenNumber))
		{
			++PackVolumes;
			TestTrue(TEXT("pack volume is west of the 1997 world by the gap"), It->Corners.NE.X <= -1500.0 + 1e-3);
			if (It->ScreenNumber == 300)
			{
				TestTrue(TEXT("base script from the pack"), It->BaseScript == FName(TEXT("x9-base")));
				TestEqual(TEXT("music file of raw 1002"), It->MusicFile, FString(TEXT("sound/2.ogg")));
			}
		}
	}
	TestEqual(TEXT("pack volumes in the world"), PackVolumes, 2);
	bool bFoundNpc = false;
	for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
	{
		if (It->Origin && It->Origin->OriginId == FDinkOriginId(300, 1))
		{
			bFoundNpc = true;
			TestTrue(TEXT("placement carries its script"), It->Origin->ScriptName == FName(TEXT("x9-npc")));
		}
	}
	TestTrue(TEXT("placement S300_P01 spawned"), bFoundNpc);
	const ADinkExpandedJoinActor* In = Packs->FindJoin(TEXT("testbed_in"), TEXT("in"));
	const ADinkExpandedJoinActor* Out = Packs->FindJoin(TEXT("testbed_in"), TEXT("out"));
	if (!TestNotNull(TEXT("1997-side trigger"), In) || !TestNotNull(TEXT("pack-side trigger"), Out))
	{
		return false;
	}
	// The 1997 side sits on screen 301 at map (220, 200) of its corners, whatever they are.
	const FVector Expected = DinkLayout::MapPixelToUnreal(DinkExpandedTest::Rect(0, 0, 41.25, 27.5), 220, 200);
	TestTrue(TEXT("1997-side trigger at the anchor's map pixel"), FVector::Dist2D(In->GetActorLocation(), Expected) < 1.0);
	FVector Arrival;
	Packs->MapPixelToWorld(300, FVector2D(520, 200), Arrival);
	TestTrue(TEXT("warp lands on the pack point"), FVector::Dist2D(In->Warp->DestLocation, Arrival) < 1.0);
	TestTrue(TEXT("warp kind"), In->Warp->Kind == FName(TEXT("pack_join")));
	const FVector Back = DinkLayout::MapPixelToUnreal(DinkExpandedTest::Rect(0, 0, 41.25, 27.5), 260, 200);
	TestTrue(TEXT("the way back lands on the 1997 return point"), FVector::Dist2D(Out->Warp->DestLocation, Back) < 1.0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkExpandedSaveTest, "Dink.Expanded.Save",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter)
bool FDinkExpandedSaveTest::RunTest(const FString& Parameters)
{
	FDinkExpandedRegistry R;
	FString Error;
	R.LoadFromJson(DinkExpandedTest::TestbedJson, Error);
	int32 Screen = 0;
	FVector2D Point;
	TestTrue(TEXT("a pack screen has a 1997 return point"), UDinkExpandedGameSubsystem::FindReturnPoint(R, 268, Screen, Point));
	TestEqual(TEXT("return screen"), Screen, 301);

	UDinkSaveGame* Base = NewObject<UDinkSaveGame>();
	Base->CurrentScreen = 412;
	TestFalse(TEXT("a 1997 save is left alone"), UDinkExpandedGameSubsystem::MakeSaveSafe(Base, R, FTransform(FVector(1, 2, 3)), 301));
	TestEqual(TEXT("1997 save screen unchanged"), Base->CurrentScreen, 412);
	TestFalse(TEXT("no expanded state in a 1997 save"), Base->SubsystemState.Contains(TEXT("expanded")));

	UDinkSaveGame* Inside = NewObject<UDinkSaveGame>();
	Inside->CurrentScreen = 300;
	Inside->PlayerTransform = FTransform(FVector(-170000, 1000, 90));
	const FTransform Safe(FVector(5000, 1000, 90));
	TestTrue(TEXT("a save inside the pack is rewritten"), UDinkExpandedGameSubsystem::MakeSaveSafe(Inside, R, Safe, 301));
	TestEqual(TEXT("its screen is the 1997 return screen"), Inside->CurrentScreen, 301);
	TestTrue(TEXT("its transform is the return point"), Inside->PlayerTransform.GetLocation().Equals(Safe.GetLocation()));
	const FString* State = Inside->SubsystemState.Find(TEXT("expanded"));
	TestTrue(TEXT("the pack position is kept for packs-on loads"), State && State->Contains(TEXT("\"screen\":300")));
	return true;
}

#endif
