// Dink.Narrative.Placement.OverrideClearsScript: a placement with an editor override is born without its script, as
// update_play_changes (dink.cpp:5773-5831) makes it on every screen load (strcpy_safe(script, ""), 5831). An opened chest
// (ch3-ap: editor_type 4, editor_frame 6) must not run its main again, and keeps no hit to make its potion a second time.
#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkStorySubsystem.h"
#include "DinkWorldStateSubsystem.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkOverrideClearsScriptTest, "Dink.Narrative.Placement.OverrideClearsScript", DINK_TEST_FLAGS)
bool FDinkOverrideClearsScriptTest::RunTest(const FString& Parameters)
{
	UGameInstance* GI = DinkTest::MakeOuterGameInstance();
	UDinkFactSubsystem* Facts = NewObject<UDinkFactSubsystem>(GI);
	FString Error;
	TestTrue(TEXT("facts table loads"), Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
	UDinkWorldStateSubsystem* World = NewObject<UDinkWorldStateSubsystem>(GI);
	UDinkStorySubsystem* Story = NewObject<UDinkStorySubsystem>(GI);
	if (!TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), Story->SetupStandalone(Facts, World, &Error)))
	{
		return false;
	}
	Story->ResetRuntime();
	Story->bInstantMode = true;
	UDinkGameplay* G = Story->GetGameplay();
	if (!TestTrue(TEXT("gameplay data"), G && G->HasData()))
	{
		return false;
	}
	G->Adaptation.bEnabled = false;
	G->StartNewGame();
	Story->RunUntilIdle();

	// SCR_536, the duck pen: two all-potion chests. P29 (ch3-ap) was opened on an earlier visit, P31 (ch1-ap) was not.
	const FDinkOriginId Opened(536, 29), Closed(536, 31);
	World->SetOverride(Opened, EDinkOverrideType::LiveHard, FName(TEXT("frame6")));
	Story->OnScreenEntered(536);
	Story->RunUntilIdle();

	auto SpriteFor = [&](const FDinkOriginId& Origin) -> const FDinkSprite*
	{
		for (const TPair<int32, FDinkSprite>& Pair : Story->GetDirector()->GetSprites())
		{
			if (Pair.Value.bActive && Pair.Value.Origin == Origin) { return &Pair.Value; }
		}
		return nullptr;
	};
	auto InstancesOf = [&](FName Script, int32 Handle)
	{
		int32 N = 0;
		for (const TUniquePtr<FDinkScriptInstance>& I : Story->GetInstances())
		{
			N += (I->IsAlive() && I->Script == Script && I->Sprite == Handle) ? 1 : 0;
		}
		return N;
	};
	const FDinkSprite* Chest = SpriteFor(Opened);
	if (TestNotNull(TEXT("the opened chest is still a live sprite (editor_type 4)"), Chest))
	{
		TestEqual(TEXT("update_play_changes cleared the opened chest's script (dink.cpp:5831)"), Chest->Script, FName());
		TestEqual(TEXT("so its main did not run again"), InstancesOf(TEXT("ch3-ap"), Chest->Handle), 0);
	}
	const FDinkSprite* Control = SpriteFor(Closed);
	if (TestNotNull(TEXT("control: the unopened chest is a live sprite"), Control))
	{
		TestEqual(TEXT("control: a placement without an override keeps its script"), Control->Script, FName(TEXT("ch1-ap")));
		TestEqual(TEXT("control: its main ran"), InstancesOf(TEXT("ch1-ap"), Control->Handle), 1);
	}
	return true;
}
