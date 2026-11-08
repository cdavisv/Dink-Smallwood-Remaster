#include "DinkTestHelpers.h"
#include "DinkWorldStateSubsystem.h"

namespace
{
	const FDinkOriginId Duck(37, 4);
	const FDinkOriginId Rock(37, 12);
	const FDinkOriginId Elsewhere(412, 3);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldOverrideTypesTest, "Dink.Core.WorldState.TypeRules", DINK_TEST_FLAGS)
bool FDinkWorldOverrideTypesTest::RunTest(const FString& Parameters)
{
	using W = UDinkWorldStateSubsystem;
	// Values must match the original editor_type numbers.
	TestEqual(TEXT("type 1 value"), static_cast<int32>(EDinkOverrideType::RemovedForever), 1);
	TestEqual(TEXT("type 5 value"), static_cast<int32>(EDinkOverrideType::BackgroundHard), 5);
	TestEqual(TEXT("type 8 value"), static_cast<int32>(EDinkOverrideType::RemovedReturn1Min), 8);

	TestEqual(TEXT("6 = 5 min"), W::GetRespawnDelayMs(EDinkOverrideType::RemovedReturn5Min), int64(300000));
	TestEqual(TEXT("7 = 3 min"), W::GetRespawnDelayMs(EDinkOverrideType::RemovedReturn3Min), int64(180000));
	TestEqual(TEXT("8 = 1 min"), W::GetRespawnDelayMs(EDinkOverrideType::RemovedReturn1Min), int64(60000));
	TestEqual(TEXT("1 never"), W::GetRespawnDelayMs(EDinkOverrideType::RemovedForever), int64(INDEX_NONE));

	const EDinkOverrideType All[] = {
		EDinkOverrideType::None, EDinkOverrideType::RemovedForever, EDinkOverrideType::LiveNoHardness,
		EDinkOverrideType::BackgroundNoHardness, EDinkOverrideType::LiveHard, EDinkOverrideType::BackgroundHard,
		EDinkOverrideType::RemovedReturn5Min, EDinkOverrideType::RemovedReturn3Min, EDinkOverrideType::RemovedReturn1Min };
	//                           0      1      2      3      4      5      6      7      8
	const bool Removed[]    = { false, true,  false, false, false, false, true,  true,  true  };
	const bool Hard[]       = { false, false, false, false, true,  true,  false, false, false };
	const bool Background[] = { false, false, false, true,  false, true,  false, false, false };
	for (int32 i = 0; i < UE_ARRAY_COUNT(All); ++i)
	{
		TestEqual(FString::Printf(TEXT("type %d removed"), i), W::IsRemovedType(All[i]), Removed[i]);
		TestEqual(FString::Printf(TEXT("type %d hardness"), i), W::ForcesHardness(All[i]), Hard[i]);
		TestEqual(FString::Printf(TEXT("type %d background"), i), W::IsBackgroundType(All[i]), Background[i]);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldOverrideSetGetTest, "Dink.Core.WorldState.SetGetClear", DINK_TEST_FLAGS)
bool FDinkWorldOverrideSetGetTest::RunTest(const FString& Parameters)
{
	UDinkWorldStateSubsystem* World = DinkTest::MakeWorldState();
	TArray<TPair<FDinkOriginId, EDinkOverrideType>> Events;
	World->OnOverrideChangedNative.AddLambda([&Events](const FDinkOriginId& Origin, EDinkOverrideType Type) { Events.Add({ Origin, Type }); });

	World->SetGameTimeMs(5000);
	World->SetOverride(Duck, EDinkOverrideType::RemovedForever);
	World->SetOverride(Rock, EDinkOverrideType::BackgroundHard, TEXT("cracked"));
	World->SetOverride(Elsewhere, EDinkOverrideType::LiveNoHardness);

	TestTrue(TEXT("duck removed"), World->IsPlacementRemoved(Duck));
	TestFalse(TEXT("rock not removed"), World->IsPlacementRemoved(Rock));
	TestFalse(TEXT("untouched placement not removed"), World->IsPlacementRemoved(FDinkOriginId(37, 1)));
	TestEqual(TEXT("rock type"), World->GetOverrideType(Rock), EDinkOverrideType::BackgroundHard);

	FDinkWorldOverride Entry;
	TestTrue(TEXT("rock entry exists"), World->TryGetOverride(Rock, Entry));
	TestEqual(TEXT("timestamp is game time"), Entry.SetAtMs, int64(5000));
	TestEqual(TEXT("variant stored"), Entry.Variant, FName(TEXT("cracked")));

	const TArray<FDinkWorldOverride> OnScreen = World->GetOverridesOnScreen(37);
	TestEqual(TEXT("two overrides on screen 37"), OnScreen.Num(), 2);
	if (OnScreen.Num() == 2)
	{
		TestTrue(TEXT("sorted by placement"), OnScreen[0].Origin == Duck && OnScreen[1].Origin == Rock);
	}

	World->SetOverride(Rock, EDinkOverrideType::None);
	TestEqual(TEXT("setting None clears"), World->GetOverrideType(Rock), EDinkOverrideType::None);
	World->ClearOverride(Rock); // already clear: no event
	TestEqual(TEXT("events: 3 sets + 1 clear"), Events.Num(), 4);
	if (Events.Num() == 4)
	{
		TestTrue(TEXT("clear event"), Events[3].Key == Rock && Events[3].Value == EDinkOverrideType::None);
	}

	AddExpectedMessage(TEXT("invalid origin"), EAutomationExpectedErrorFlags::Contains, 1);
	World->SetOverride(FDinkOriginId(0, 0), EDinkOverrideType::RemovedForever);
	TestEqual(TEXT("invalid origin ignored"), World->NumOverrides(), 2);

	World->ResetState();
	TestEqual(TEXT("reset clears"), World->NumOverrides(), 0);
	TestEqual(TEXT("reset clock"), World->GetGameTimeMs(), int64(0));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldRespawnTimingTest, "Dink.Core.WorldState.RespawnTiming", DINK_TEST_FLAGS)
bool FDinkWorldRespawnTimingTest::RunTest(const FString& Parameters)
{
	struct FCase { EDinkOverrideType Type; int64 Delay; };
	const FCase Cases[] = {
		{ EDinkOverrideType::RemovedReturn5Min, 300000 },
		{ EDinkOverrideType::RemovedReturn3Min, 180000 },
		{ EDinkOverrideType::RemovedReturn1Min, 60000 },
	};
	for (const FCase& Case : Cases)
	{
		const int32 TypeNum = static_cast<int32>(Case.Type);
		UDinkWorldStateSubsystem* World = DinkTest::MakeWorldState();

		// Killed at t=10 s, the player stays on the screen until t=40 s, then leaves.
		World->SetGameTimeMs(10000);
		World->SetOverride(Duck, Case.Type);
		World->SetGameTimeMs(40000);
		World->NotifyScreenExited(37);
		TestEqual(FString::Printf(TEXT("type %d: exit time recorded"), TypeNum), World->GetScreenExitTimeMs(37), int64(40000));

		// The timer counts from the exit (fix_dead_sprites uses spmap[].last_time) and is strict.
		World->SetGameTimeMs(40000 + Case.Delay);
		TestEqual(FString::Printf(TEXT("type %d: not back at exactly exit + delay"), TypeNum), World->ProcessRespawns(37).Num(), 0);
		TestTrue(FString::Printf(TEXT("type %d: still removed"), TypeNum), World->IsPlacementRemoved(Duck));

		World->SetGameTimeMs(40000 + Case.Delay + 1);
		TestEqual(FString::Printf(TEXT("type %d: other screens untouched"), TypeNum), World->ProcessRespawns(412).Num(), 0);
		const TArray<FDinkOriginId> Back = World->ProcessRespawns(37);
		TestEqual(FString::Printf(TEXT("type %d: back 1 ms later"), TypeNum), Back.Num(), 1);
		TestFalse(FString::Printf(TEXT("type %d: override cleared"), TypeNum), World->IsPlacementRemoved(Duck));

		// Without a recorded exit the timer counts from when the override was set.
		UDinkWorldStateSubsystem* World2 = DinkTest::MakeWorldState();
		World2->SetGameTimeMs(1000);
		World2->SetOverride(Rock, Case.Type);
		World2->SetGameTimeMs(1000 + Case.Delay);
		TestEqual(FString::Printf(TEXT("type %d: no exit, at delay"), TypeNum), World2->ProcessRespawns(37).Num(), 0);
		World2->AdvanceGameTime(1);
		TestEqual(FString::Printf(TEXT("type %d: no exit, delay + 1"), TypeNum), World2->ProcessRespawns(37).Num(), 1);

		// An exit recorded before the kill does not shorten the timer.
		UDinkWorldStateSubsystem* World3 = DinkTest::MakeWorldState();
		World3->NotifyScreenExited(37); // t = 0
		World3->SetGameTimeMs(500000);
		World3->SetOverride(Rock, Case.Type);
		World3->SetGameTimeMs(500000 + Case.Delay);
		TestEqual(FString::Printf(TEXT("type %d: stale exit ignored"), TypeNum), World3->ProcessRespawns(37).Num(), 0);
	}

	// Type 1 never comes back; types 2-5 are not timed.
	UDinkWorldStateSubsystem* World = DinkTest::MakeWorldState();
	World->SetOverride(Duck, EDinkOverrideType::RemovedForever);
	World->SetOverride(Rock, EDinkOverrideType::LiveHard);
	World->NotifyScreenExited(37);
	World->SetGameTimeMs(int64(1000) * 60 * 60 * 24 * 365);
	TestEqual(TEXT("permanent overrides survive a year"), World->ProcessRespawns(37).Num(), 0);
	TestEqual(TEXT("both still there"), World->NumOverrides(), 2);

	// Negative deltas do not run the clock backwards.
	World->SetGameTimeMs(100);
	World->AdvanceGameTime(-50);
	TestEqual(TEXT("negative advance ignored"), World->GetGameTimeMs(), int64(100));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldClockSkewTest, "Dink.Core.WorldState.ClockSkewGuard", DINK_TEST_FLAGS)
bool FDinkWorldClockSkewTest::RunTest(const FString& Parameters)
{
	// dink.cpp D:933, type 6 only: respawn if dinkTick + 400000 < last_time + 300000,
	// i.e. the clock is more than 100 s behind the reference time.
	FDinkWorldOverride Five;
	Five.Origin = Duck;
	Five.Type = EDinkOverrideType::RemovedReturn5Min;
	Five.SetAtMs = 500000;
	TestTrue(TEXT("type 6: clock 100.001 s behind -> respawn"), UDinkWorldStateSubsystem::ShouldRespawn(Five, INDEX_NONE, 399999));
	TestFalse(TEXT("type 6: clock exactly 100 s behind -> stays"), UDinkWorldStateSubsystem::ShouldRespawn(Five, INDEX_NONE, 400000));
	TestFalse(TEXT("type 6: clock 1 s behind -> stays"), UDinkWorldStateSubsystem::ShouldRespawn(Five, INDEX_NONE, 499000));

	FDinkWorldOverride Three = Five;
	Three.Type = EDinkOverrideType::RemovedReturn3Min;
	TestFalse(TEXT("type 7 has no skew guard"), UDinkWorldStateSubsystem::ShouldRespawn(Three, INDEX_NONE, 0));

	FDinkWorldOverride Forever = Five;
	Forever.Type = EDinkOverrideType::RemovedForever;
	TestFalse(TEXT("type 1 never"), UDinkWorldStateSubsystem::ShouldRespawn(Forever, INDEX_NONE, 0));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldExportImportTest, "Dink.Core.WorldState.ExportImport", DINK_TEST_FLAGS)
bool FDinkWorldExportImportTest::RunTest(const FString& Parameters)
{
	UDinkWorldStateSubsystem* Source = DinkTest::MakeWorldState();
	Source->SetGameTimeMs(1234);
	Source->SetOverride(Elsewhere, EDinkOverrideType::RemovedReturn3Min);
	Source->SetOverride(Duck, EDinkOverrideType::RemovedForever, TEXT("headless"));
	Source->NotifyScreenExited(37);
	Source->AdvanceGameTime(10);

	TArray<FDinkWorldOverride> Overrides = Source->ExportOverrides();
	TestEqual(TEXT("two exported"), Overrides.Num(), 2);
	if (Overrides.Num() == 2)
	{
		TestTrue(TEXT("export sorted by origin"), Overrides[0].Origin == Duck);
	}

	// A corrupt entry is dropped on import.
	FDinkWorldOverride& Bad = Overrides.AddDefaulted_GetRef();
	Bad.Origin = FDinkOriginId(999, 1);
	Bad.Type = EDinkOverrideType::RemovedForever;

	UDinkWorldStateSubsystem* Target = DinkTest::MakeWorldState();
	AddExpectedMessage(TEXT("dropped override"), EAutomationExpectedErrorFlags::Contains, 1);
	Target->ImportState(Overrides, Source->ExportScreenExitTimes(), Source->GetGameTimeMs());
	TestEqual(TEXT("clock restored"), Target->GetGameTimeMs(), int64(1244));
	TestEqual(TEXT("valid overrides restored"), Target->NumOverrides(), 2);
	TestEqual(TEXT("exit time restored"), Target->GetScreenExitTimeMs(37), int64(1234));
	TestTrue(TEXT("same export after round trip"), Target->ExportOverrides() == Source->ExportOverrides());
	return true;
}
