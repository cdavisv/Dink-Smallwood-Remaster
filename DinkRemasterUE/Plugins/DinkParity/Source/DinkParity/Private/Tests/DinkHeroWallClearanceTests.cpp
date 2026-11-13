// Hero wall clearance (owner report 9 Nov 2026: head and shoulder pushed into an interior wall).
// Mesh-only: the capsule, its movement and every probe trace stay exactly as before.
#include "DinkTestHelpers.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "AssetCompilingManager.h"
#include "GameFramework/PlayerController.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHeroWallClearanceTest, "Dink.Movement.WallClearance", DINK_TEST_FLAGS)
bool FDinkHeroWallClearanceTest::RunTest(const FString&)
{
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	if (!TestNotNull(TEXT("world"), World) || !TestNotNull(TEXT("real physics scene"), World->GetPhysicsScene())) return false;
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	FAssetCompilingManager::Get().FinishAllCompilation();
	if (!TestNotNull(TEXT("cube geometry"), Cube)) return false;

	FActorSpawnParameters Spawn;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ADinkGreyboxCharacter* Hero = World->SpawnActor<ADinkGreyboxCharacter>(FVector(0, 0, 96), FRotator::ZeroRotator, Spawn);
	APlayerController* PC = World->SpawnActor<APlayerController>();
	World->AddController(PC);
	PC->Possess(Hero);
	if (!TestNotNull(TEXT("hero"), Hero) || !TestTrue(TEXT("player possesses the hero"), Hero->GetController() == PC)) return false;
	// Stand-in for the lean/hunch/gait reach: an authored mesh offset 22 cm forward carries the
	// head 30+ cm ahead of the capsule axis, past the 28 cm capsule (as the hunch and the
	// stop lurch do in the game). The character composes everything on top of it.
	// (22 cm since the animation pass: the mesh is no longer pitched forward as a whole.)
	Hero->GetMesh()->SetRelativeLocation(FVector(22, 0, -96));
	const FVector Capsule = Hero->GetActorLocation();
	auto Run = [&](int32 Frames) { for (int32 I = 0; I < Frames; ++I) Hero->Tick(1.f / 60.f); };

	Run(30);
	TestEqual(TEXT("no wall: no pull-back"), Hero->GetWallPullback(), 0.f);
	TestEqual(TEXT("no wall: lean untouched"), Hero->GetWallLeanDamping(), 0.f);
	const double FreeHeadX = Hero->GetHeadReachPoint().X;
	TestTrue(FString::Printf(TEXT("fixture head reaches past the capsule (%.1f cm)"), FreeHeadX), FreeHeadX > 32.);

	// A wall whose face is 1 cm in front of the capsule (where walking into it stops the pawn).
	const double WallX = 29.;
	AStaticMeshActor* Wall = World->SpawnActor<AStaticMeshActor>(FVector(WallX + 10., 0, 100), FRotator::ZeroRotator, Spawn);
	UStaticMeshComponent* WallMesh = Wall->GetStaticMeshComponent();
	WallMesh->SetMobility(EComponentMobility::Movable);
	WallMesh->SetStaticMesh(Cube);
	WallMesh->SetCollisionProfileName(TEXT("BlockAll"));
	Wall->SetActorScale3D(FVector(.2, 3., 3.)); // 20 cm thick, 3 m wide and tall

	Run(2);
	const FVector Head = Hero->GetHeadReachPoint();
	TestTrue(FString::Printf(TEXT("head stays on the pawn's side of the wall (head %.1f, wall %.1f)"), Head.X, WallX),
		Head.X + ADinkGreyboxCharacter::WallProbeRadius - .5 <= WallX);
	TestTrue(FString::Printf(TEXT("mesh pulled back by the overlap (%.1f cm)"), Hero->GetWallPullback()),
		Hero->GetWallPullback() > FreeHeadX - WallX && Hero->GetWallPullback() <= Hero->MaxWallPullback);
	Run(30);
	TestTrue(TEXT("lean is held back at the wall"), Hero->GetWallLeanDamping() > .5f);
	TestTrue(TEXT("still clear of the wall after the lean settles"),
		Hero->GetHeadReachPoint().X + ADinkGreyboxCharacter::WallProbeRadius - .5 <= WallX);
	TestTrue(TEXT("capsule never moves (wall)"), Hero->GetActorLocation().Equals(Capsule, 0.));

	// Clear again: the pull-back eases out (no pop) and returns to zero.
	Wall->Destroy();
	Run(1);
	TestTrue(TEXT("release is smoothed, not a pop"), Hero->GetWallPullback() > 0.f);
	Run(180);
	TestTrue(FString::Printf(TEXT("no wall: offset back to zero (%.4f)"), Hero->GetWallPullback()), Hero->GetWallPullback() < .01f);
	TestTrue(TEXT("no wall: head back at its free reach"), FMath::IsNearlyEqual(Hero->GetHeadReachPoint().X, FreeHeadX, 2.));
	TestTrue(TEXT("capsule never moves (released)"), Hero->GetActorLocation().Equals(Capsule, 0.));

	// Not the player: an unpossessed copy at the same wall keeps its mesh where it is.
	AStaticMeshActor* Wall2 = World->SpawnActor<AStaticMeshActor>(FVector(WallX + 10., 0, 100), FRotator::ZeroRotator, Spawn);
	Wall2->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
	Wall2->GetStaticMeshComponent()->SetStaticMesh(Cube);
	Wall2->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
	Wall2->SetActorScale3D(FVector(.2, 3., 3.));
	PC->UnPossess();
	Run(10);
	TestEqual(TEXT("not the player: clearance off"), Hero->GetWallPullback(), 0.f);
	TestTrue(TEXT("capsule never moves (unpossessed)"), Hero->GetActorLocation().Equals(Capsule, 0.));

	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}
