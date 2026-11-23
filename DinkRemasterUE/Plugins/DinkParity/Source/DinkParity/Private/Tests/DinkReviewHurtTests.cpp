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
