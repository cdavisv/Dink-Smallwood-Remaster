// Review console dink.HurtSprite (23 Nov 2026): captures of what a death leaves need to kill script-made sprites
// (Mog of s3-mog on SCR_680 has no placement origin, so dink.Hurt cannot name him). The command finds a sprite by origin,
// handle, script name or `nearest` and deals one of Dink's blows as run_through_tag_list does (D:15520-15590).
#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkStorySubsystem.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkReviewHurtSpriteTest, "Dink.Narrative.Review.HurtSpriteFindsScriptMadeSprites", DINK_TEST_FLAGS)
bool FDinkReviewHurtSpriteTest::RunTest(const FString&)
{
	TestNotNull(TEXT("dink.HurtSprite is registered"), IConsoleManager::Get().FindConsoleObject(TEXT("dink.HurtSprite")));
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	Story->bRunScreenScripts = false;
	Story->bInstantMode = true;
	UDinkDirector* D = Story->GetDirector();
	UDinkGameplay* G = Story->GetGameplay();
	FDinkSprite& Dink = D->GetDink();
	const int32 Here = D->GetCurrentScreen();
	Dink.Screen = Here;
	Dink.X = 300.0;
	Dink.Y = 200.0;

	// two script-made sprites of the same script: the one nearer Dink is chosen; a third on another screen is not
	auto Make = [&](int32 Screen, double X, FName Script, int32 Hp)
	{
		const int32 H = D->CreateVirtualSprite(Screen, X, 200.0);
		FDinkSprite* S = D->FindSprite(H);
		UDinkDirector::InitDumbSprite(*S);
		S->Script = Script;
		S->Props.Add(TEXT("hitpoints"), Hp);
		S->Props.Add(TEXT("defense"), 0);
		S->Props.Add(TEXT("brain"), 9);
		return H;
	};
	const FName Review(TEXT("zz-review-mog")); // no such script in the story: its `hit` is skipped, nothing else runs
	const int32 Far = Make(Here, 560.0, Review, 30);
	const int32 Near = Make(Here, 340.0, Review, 30);
	const int32 Away = Make(Here + 1, 300.0, Review, 30);
	const int32 Rock = Make(Here, 310.0, NAME_None, 0);
	TestEqual(TEXT("by script name: the nearest on Dink's screen"), G->FindReviewSprite(TEXT("zz-review-mog")), Near);
	TestEqual(TEXT("script names ignore case, as DinkC's"), G->FindReviewSprite(TEXT("ZZ-Review-Mog")), Near);
	TestEqual(TEXT("by handle"), G->FindReviewSprite(FString::FromInt(Far)), Far);
	TestEqual(TEXT("`nearest` skips sprites without hitpoints"), G->FindReviewSprite(TEXT("nearest")), Near);
	TestEqual(TEXT("Dink is never a review target"), G->FindReviewSprite(TEXT("1")), 0);
	TestEqual(TEXT("an unknown script finds nothing"), G->FindReviewSprite(TEXT("s9-none")), 0);
	D->FindSprite(Near)->bActive = false;
	TestEqual(TEXT("a dead sprite is skipped"), G->FindReviewSprite(TEXT("zz-review-mog")), Far);
	D->FindSprite(Near)->bActive = true;
	D->FindSprite(Far)->Origin = FDinkOriginId(680, 12);
	TestEqual(TEXT("by placement origin"), G->FindReviewSprite(TEXT("S680_P12")), Far);
	TestTrue(TEXT("the other screen's sprite exists"), D->FindSprite(Away) != nullptr);

	// the blow: hurt_thing (pending damage, applied by the brain), last_hit 1 (add_exp pays Dink), blood once, target set
	const uint32 Blood0 = G->GetBloodSerial();
	TestEqual(TEXT("deals the given damage"), G->ReviewBlow(Near, 7), 7);
	const FDinkSprite* N = D->FindSprite(Near);
	TestEqual(TEXT("pending damage for the brain"), N->Damage, 7);
	TestEqual(TEXT("last_hit is Dink"), N->LastHit, 1);
	TestEqual(TEXT("bleeds once (random_blood after a hurt that hurt)"), G->GetBloodSerial(), Blood0 + 1);
	TestEqual(TEXT("a dead sprite is no target"), G->ReviewBlow(9999, 5), -1);
	TestEqual(TEXT("a nohit sprite without a script is not hit"), (D->FindSprite(Rock)->Props.Add(TEXT("nohit"), 1), G->ReviewBlow(Rock, 5)), 0);
	TestEqual(TEXT("no blood without damage"), G->GetBloodSerial(), Blood0 + 1);

	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkReviewHurtGoblinsMogTest, "Dink.Narrative.Review.HurtSpriteKillsTheGoblinsAndMogComes", DINK_TEST_FLAGS)
bool FDinkReviewHurtGoblinsMogTest::RunTest(const FString&)
{
	// Takeover A1 (25 Nov 2026): on SCR_680 with &gobpass 1 the capture of 23 Nov killed only the first goblin. Its 150 exp
	// leveled Dink up; lraise.c's menu holds the world with stop_entire_game (D:10099-10108), no brain thinks (D:17414-17423),
	// so the next three blows only piled up as pending damage and the menu was never answered. dink.HurtSprite now refuses a
	// blow while the world is held; with the menu answered every goblin dies and the last die() spawns s3-mog (Mog, en-gmog).
	UGameInstance* GI = DinkTest::MakeOuterGameInstance();
	UDinkFactSubsystem* Facts = NewObject<UDinkFactSubsystem>(GI);
	FString Error;
	TestTrue(TEXT("facts table loads"), Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
	UDinkWorldStateSubsystem* WorldState = NewObject<UDinkWorldStateSubsystem>(GI);
	UDinkStorySubsystem* Story = NewObject<UDinkStorySubsystem>(GI);
	if (!TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), Story->SetupStandalone(Facts, WorldState, &Error))) return false;
	Story->StorySeed = 1997;
	Story->ResetRuntime();
	Story->bInstantMode = true;
	UDinkDirector* D = Story->GetDirector();
	UDinkGameplay* G = Story->GetGameplay();
	if (!TestTrue(TEXT("gameplay data loaded"), D && G && G->HasData())) return false;
	G->Adaptation.bEnabled = false;
	G->SetRandomSeed(1997);
	Facts->SetFact(TEXT("lifemax"), 5000);
	Facts->SetFact(TEXT("life"), 5000);
	Facts->SetFact(TEXT("gobpass"), 1);
	Facts->SetFact(TEXT("update_status"), 1); // as start.c leaves it in a new game: exp levels Dink up (lraise)
	Facts->SetFact(TEXT("level"), 1);
	Facts->SetFact(TEXT("exp"), 0);
	FDinkSprite& Dink = D->GetDink();
	Dink.Screen = 680;
	Dink.X = 337.0;
	Dink.Y = 390.0;
	Story->OnScreenEntered(680);
	Story->RunUntilIdle();

	auto FindScript = [&](const TCHAR* Script)
	{
		for (const TPair<int32, FDinkSprite>& P : D->GetSprites())
		{
			if (P.Value.bActive && P.Value.Script == FName(Script)) return P.Key;
		}
		return 0;
	};
	int32 Menus = 0;
	bool bSawHeld = false;
	// A few seconds of 60 Hz frames, answering the level-up menu ("Increase Attack") whenever it is up.
	auto Play = [&](int32 Frames, TFunctionRef<bool()> Done)
	{
		for (int32 F = 0; F < Frames && !Done(); ++F)
		{
			if (Story->GetActiveMenu())
			{
				bSawHeld |= G->IsReviewBlowHeld();
				Story->Choose(0);
				++Menus;
			}
			Story->Advance(1.0 / 60.0);
		}
	};
	const TCHAR* Goblins[] = { TEXT("S680_P11"), TEXT("S680_P12"), TEXT("S680_P13"), TEXT("S680_P14") };
	for (const TCHAR* Id : Goblins)
	{
		const int32 H = G->FindReviewSprite(Id);
		if (!TestTrue(FString::Printf(TEXT("%s is live"), Id), H > 0)) return false;
		TestTrue(FString::Printf(TEXT("%s has its main's hitpoints"), Id), D->FindSprite(H)->GetProp(TEXT("hitpoints")) > 0);
		Play(600, [&] { return !G->IsReviewBlowHeld(); });
		TestTrue(FString::Printf(TEXT("%s: a blow lands"), Id), G->ReviewBlow(H, 500) > 0);
		Play(600, [&] { const FDinkSprite* S = D->FindSprite(H); return !S || !S->bActive || S->GetProp(TEXT("hitpoints")) <= 0; });
		const FDinkSprite* S = D->FindSprite(H);
		TestTrue(FString::Printf(TEXT("%s dies of one 500 blow"), Id), !S || !S->bActive || S->GetProp(TEXT("hitpoints")) <= 0);
		// The capture's recipe: 1.5 s after a kill (lraise.c waits 1 s before its menu), answering the menu if it is up.
		Play(90, [] { return false; });
	}
	TestTrue(TEXT("the first kill leveled Dink up: the menu held the world (stop_entire_game)"), bSawHeld && Menus >= 1);
	Play(60 * 60, [&] { return FindScript(TEXT("en-gmog")) != 0; });
	const int32 Mog = FindScript(TEXT("en-gmog"));
	TestTrue(TEXT("the last goblin's die() spawned s3-mog: Mog (en-gmog) stands"), Mog != 0);
	if (Mog != 0)
	{
		TestEqual(TEXT("dink.HurtSprite finds Mog by his script"), G->FindReviewSprite(TEXT("en-gmog")), Mog);
	}
	return true;
}
