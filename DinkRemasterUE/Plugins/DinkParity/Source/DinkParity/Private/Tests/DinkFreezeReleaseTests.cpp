// Dink.Input.FreezeReleasedByReset: a freeze holds the player controller's move input (SetIgnoreMoveInput is a counter). A sprite
// reset (a load: LoadState, a restart: ResetRuntime) used to drop the director's note of it without releasing the controller, so
// after escape.c's "Load a previously saved game" (escape.c freezes Dink first) the player could never walk again (alpha bug A19,
// seen in the 15 Nov 2026 soak). load_game's load_map clears Dink's freeze in the original (dink.cpp:1013-1015).

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "DinkFactSubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFreezeReleaseTest, "Dink.Input.FreezeReleasedByReset", DINK_TEST_FLAGS)
bool FDinkFreezeReleaseTest::RunTest(const FString& Parameters)
{
	UGameInstance* GI = DinkTest::MakeOuterGameInstance();
	UDinkFactSubsystem* Facts = NewObject<UDinkFactSubsystem>(GI);
	FString Error;
	TestTrue(TEXT("facts load"), Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
	UDinkStorySubsystem* Story = NewObject<UDinkStorySubsystem>(GI);
	if (!TestTrue(TEXT("story loads"), Story->SetupStandalone(Facts, NewObject<UDinkWorldStateSubsystem>(GI), &Error))) return false;
	UDinkDirector* D = Story->GetDirector();

	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
	ACharacter* Pawn = World->SpawnActor<ACharacter>();
	APlayerController* PC = World->SpawnActor<APlayerController>();
	if (!TestNotNull(TEXT("pawn"), Pawn) || !TestNotNull(TEXT("controller"), PC)) return false;
	PC->Possess(Pawn);
	D->GetDink().Actor = Pawn;
	const float Gravity = Pawn->GetCharacterMovement()->GravityScale;

	D->SetFrozen(1, true);
	TestTrue(TEXT("freeze(1) holds the controller's move input"), PC->IsMoveInputIgnored());
	TestEqual(TEXT("and takes Dink's gravity"), Pawn->GetCharacterMovement()->GravityScale, 0.f);

	D->ResetSprites(); // what LoadState and ResetRuntime do
	TestFalse(TEXT("a sprite reset releases the controller"), PC->IsMoveInputIgnored());
	TestEqual(TEXT("and gives Dink his gravity back"), Pawn->GetCharacterMovement()->GravityScale, Gravity);

	// the next freeze and unfreeze still pair up on the controller's counter
	D->GetDink().Actor = Pawn;
	D->SetFrozen(1, true);
	TestTrue(TEXT("frozen again"), PC->IsMoveInputIgnored());
	D->SetFrozen(1, false);
	TestFalse(TEXT("and free again"), PC->IsMoveInputIgnored());
	return true;
}
