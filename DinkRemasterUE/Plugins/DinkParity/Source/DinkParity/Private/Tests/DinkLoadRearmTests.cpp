// Dink.Narrative.Load.OriginalRearmDisarmsFirst: an original-style load re-arms the armed item the way load_game does
// (dink.cpp:1435-1439): DISARM on a freshly loaded script, then ARM. The saved strength already holds the sword's +4
// (item-sw1.c arm: &strength += 4, disarm: -= 4), so the load must leave it as saved.
#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkInventoryComponent.h"
#include "DinkStorySubsystem.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkOriginalLoadRearmTest, "Dink.Narrative.Load.OriginalRearmDisarmsFirst", DINK_TEST_FLAGS)
bool FDinkOriginalLoadRearmTest::RunTest(const FString& Parameters)
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
	if (!TestNotNull(TEXT("gameplay"), G))
	{
		return false;
	}
	G->Adaptation.bEnabled = false;
	G->StartNewGame();
	Story->RunUntilIdle();
	TestEqual(TEXT("the sword goes into item slot 2"), G->AddItem(TEXT("item-sw1"), false), 1);
	Story->RunUntilIdle();
	const int32 Before = Facts->GetFact(TEXT("strength"));
	TestTrue(TEXT("arm the sword (slot 2)"), G->ArmItemSlot(2));
	Story->RunUntilIdle();
	const int32 Armed = Facts->GetFact(TEXT("strength"));
	TestEqual(TEXT("item-sw1's arm adds 4 strength"), Armed, Before + 4);

	// What a marked-world load does after restoring the saved facts: the runtime goes (no armed instance), then the re-arm.
	G->RestartOriginalSavedRuntime();
	TestEqual(TEXT("the restart leaves no armed instance"), G->GetWeaponInstance(), 0);
	G->RearmAfterOriginalLoad();
	Story->RunUntilIdle();
	TestEqual(TEXT("load_game's DISARM then ARM leaves the saved strength (dink.cpp:1435-1439)"), Facts->GetFact(TEXT("strength")), Armed);
	const FDinkScriptInstance* Weapon = Story->FindInstance(G->GetWeaponInstance());
	TestTrue(TEXT("the sword is armed again on a live instance"), Weapon && Weapon->IsAlive() && Weapon->Script == FName(TEXT("item-sw1")));
	TestEqual(TEXT("the inventory still arms the sword"), Story->GetDirector()->GetInventory()->GetArmedItem(), FName(TEXT("item-sw1")));

	// Control: arming alone after the restart (what the marked-world load did before) adds the sword's 4 again.
	G->RestartOriginalSavedRuntime();
	G->ArmWeapon();
	Story->RunUntilIdle();
	TestEqual(TEXT("control: ARM without the DISARM adds 4 strength on every load"), Facts->GetFact(TEXT("strength")), Armed + 4);
	Facts->SetFact(TEXT("strength"), Armed);

	// A second load in a row changes nothing either.
	G->RestartOriginalSavedRuntime();
	G->RearmAfterOriginalLoad();
	Story->RunUntilIdle();
	TestEqual(TEXT("two loads in a row: strength still as saved"), Facts->GetFact(TEXT("strength")), Armed);
	return true;
}
