// Dink.PlayerBlockers.*: the player-only blocking layer (DinkPlayerBlockers.h). Its collision profile blocks Pawn and nothing
// else, and the player capsule blocks against it. A query made without response params blocks against every object type, so
// the NPC and creature moves (UDinkGameplay::AuthoredActorMoveBlocked: Pawn-channel sweeps and overlaps of their bodies) pass
// DinkCollision::IgnorePlayerBlockers(). BlocksOnlyThePlayer spawns a real blocker in a throwaway world: the NPC-style sweep
// and overlap do not hit it (complex or simple tracing; a simple sweep without those responses does), a creature body does
// not respond to it, and a capsule with the player's responses is stopped by it. The table parses, and the shipped table is valid.

#include "DinkTestHelpers.h"
#include "DinkPlayerBlockers.h"
#include "DinkCollision.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "GameFramework/Actor.h"
#include "Misc/FileHelper.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPlayerBlockerProfileTest, "Dink.PlayerBlockers.BlocksOnlyThePlayer", DINK_TEST_FLAGS)
bool FDinkPlayerBlockerProfileTest::RunTest(const FString& Parameters)
{
	FCollisionResponseTemplate Profile;
	if (!TestTrue(TEXT("profile DinkPlayerBlock exists"), UCollisionProfile::Get()->GetProfileTemplate(DinkCollision::ProfilePlayerBlock, Profile))) return false;
	TestEqual(TEXT("object type is the DinkPlayerBlock channel"), Profile.ObjectType.GetValue(), DinkCollision::PlayerBlock);
	TestEqual(TEXT("blocks pawns"), Profile.ResponseToChannels.GetResponse(ECC_Pawn), ECR_Block);
	for (ECollisionChannel C : { ECC_WorldStatic, ECC_WorldDynamic, ECC_Visibility, ECC_Camera, ECC_PhysicsBody, DinkCollision::Projectile, DinkCollision::HardSolid, DinkCollision::HardLow })
		TestEqual(FString::Printf(TEXT("ignores channel %d"), int32(C)), Profile.ResponseToChannels.GetResponse(C), ECR_Ignore);
	TestEqual(TEXT("NPC responses ignore DinkPlayerBlock"), DinkCollision::IgnorePlayerBlockers().CollisionResponse.GetResponse(DinkCollision::PlayerBlock), ECR_Ignore);
	for (ECollisionChannel C : { ECC_WorldStatic, ECC_WorldDynamic, ECC_Pawn, ECC_PhysicsBody, DinkCollision::HardSolid, DinkCollision::HardLow })
		TestEqual(FString::Printf(TEXT("NPC responses still block channel %d (as a query without responses)"), int32(C)),
			DinkCollision::IgnorePlayerBlockers().CollisionResponse.GetResponse(C), ECR_Block);
	const ADinkGreyboxCharacter* Hero = GetDefault<ADinkGreyboxCharacter>();
	const UCapsuleComponent* HeroCapsule = Hero->GetCapsuleComponent();
	TestEqual(TEXT("the player capsule blocks against it"), HeroCapsule->GetCollisionResponseToChannel(DinkCollision::PlayerBlock), ECR_Block);

	// A real blocker (the component the game adds) in a throwaway world: a 1 m square prism, 0-150 cm, at the origin.
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("DinkPlayerBlockerTest"));
	FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
	Context.SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
	AActor* Rock = World->SpawnActor<AActor>();
	if (!TestNotNull(TEXT("blocker owner spawns"), Rock)) return false;
	USceneComponent* Root = NewObject<USceneComponent>(Rock, TEXT("Root"));
	Rock->SetRootComponent(Root);
	Root->RegisterComponent();
	FDinkPlayerBlockerShape Shape;
	Shape.Mesh = TEXT("/Game/Test/Rock.Rock");
	Shape.HullCm = { FVector2D(-50, -50), FVector2D(50, -50), FVector2D(50, 50), FVector2D(-50, 50) };
	Shape.ZLowCm = 0.0;
	Shape.ZHighCm = 150.0;
	UPrimitiveComponent* Blocker = DinkPlayerBlockers::AddShape(*Rock, *Root, FTransform::Identity, Shape);
	if (!TestNotNull(TEXT("the blocker is made"), Blocker)) return false;
	TestEqual(TEXT("blocker object type"), Blocker->GetCollisionObjectType(), DinkCollision::PlayerBlock);
	TestTrue(TEXT("blocker collides"), Blocker->IsCollisionEnabled());

	// The NPC / creature move query, as AuthoredActorMoveBlocked makes it: a body shape swept and overlapped on ECC_Pawn, complex
	// tracing on. With DinkCollision::IgnorePlayerBlockers() neither the sweep nor the overlap sees the blocker, whether the query
	// traces complex or simple geometry.
	const FCollisionShape Body = FCollisionShape::MakeCapsule(20.f, 40.f);
	const FVector From(-200, 0, 60), To(200, 0, 60), Inside(0, 0, 60);
	for (const bool bComplex : { true, false })
	{
		FCollisionQueryParams Params(TEXT("DinkAuthoredActorMovement"), bComplex);
		FHitResult Hit;
		TestFalse(FString::Printf(TEXT("an NPC/creature sweep across the blocker does not hit it (complex %d)"), bComplex),
			World->SweepSingleByChannel(Hit, From, To, FQuat::Identity, ECC_Pawn, Body, Params, DinkCollision::IgnorePlayerBlockers()));
		TestFalse(FString::Printf(TEXT("an NPC/creature body standing in it does not overlap-block (complex %d)"), bComplex),
			World->OverlapBlockingTestByChannel(Inside, FQuat::Identity, ECC_Pawn, Body, Params, DinkCollision::IgnorePlayerBlockers()));
		// Without the responses (the move before the review fix) a query on simple collision does stop at the blocker; record
		// what the complex query and the overlap did then.
		const bool bSweepHit = World->SweepSingleByChannel(Hit, From, To, FQuat::Identity, ECC_Pawn, Body, Params) && Hit.GetComponent() == Blocker;
		const bool bOverlapHit = World->OverlapBlockingTestByChannel(Inside, FQuat::Identity, ECC_Pawn, Body, Params);
		AddInfo(FString::Printf(TEXT("without response params (complex %d): sweep hits the blocker %d, overlap blocks %d"), bComplex, bSweepHit, bOverlapHit));
		if (!bComplex) TestTrue(TEXT("control: a simple-collision Pawn sweep without response params hits the blocker"), bSweepHit);
	}

	// A creature body (DinkCreatureSubsystem: profile Pawn, query only) does not respond to the channel either.
	UCapsuleComponent* Creature = NewObject<UCapsuleComponent>(Rock, TEXT("CreatureBody"));
	Creature->SetCollisionProfileName(TEXT("Pawn"));
	TestEqual(TEXT("a Pawn-profile body ignores DinkPlayerBlock"), Creature->GetCollisionResponseToChannel(DinkCollision::PlayerBlock), ECR_Ignore);

	// The player: a capsule with the player's object type and responses (what CharacterMovement sweeps with) is stopped.
	AActor* Walker = World->SpawnActor<AActor>(FVector(-200, 0, 100), FRotator::ZeroRotator);
	if (!TestNotNull(TEXT("walker spawns"), Walker)) return false;
	UCapsuleComponent* Capsule = NewObject<UCapsuleComponent>(Walker, TEXT("PlayerCapsule"));
	Capsule->InitCapsuleSize(HeroCapsule->GetUnscaledCapsuleRadius(), HeroCapsule->GetUnscaledCapsuleHalfHeight());
	Capsule->SetCollisionObjectType(HeroCapsule->GetCollisionObjectType());
	Capsule->SetCollisionResponseToChannels(HeroCapsule->GetCollisionResponseToChannels());
	Capsule->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	Walker->SetRootComponent(Capsule);
	Capsule->RegisterComponent();
	Walker->SetActorLocation(FVector(-200, 0, 100));
	FHitResult Stop;
	Walker->SetActorLocation(FVector(200, 0, 100), /*bSweep*/ true, &Stop);
	TestTrue(TEXT("the player capsule is stopped by the blocker"), Stop.bBlockingHit && Stop.GetComponent() == Blocker);
	TestTrue(FString::Printf(TEXT("the player capsule stops at the blocker's face (x %.1f)"), Walker->GetActorLocation().X),
		Walker->GetActorLocation().X < -50.0 - HeroCapsule->GetUnscaledCapsuleRadius() + 2.0);
	// The player's sweep query (the capsule's own responses on its object type) hits it.
	FHitResult Hit;
	TestTrue(TEXT("a sweep with the player's responses hits the blocker"),
		World->SweepSingleByChannel(Hit, FVector(-200, 0, 100), FVector(200, 0, 100), FQuat::Identity, HeroCapsule->GetCollisionObjectType(),
			FCollisionShape::MakeCapsule(HeroCapsule->GetUnscaledCapsuleRadius(), HeroCapsule->GetUnscaledCapsuleHalfHeight()), FCollisionQueryParams(NAME_None, false, Walker),
			FCollisionResponseParams(HeroCapsule->GetCollisionResponseToChannels())) && Hit.GetComponent() == Blocker);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPlayerBlockerTableTest, "Dink.PlayerBlockers.Table", DINK_TEST_FLAGS)
bool FDinkPlayerBlockerTableTest::RunTest(const FString& Parameters)
{
	TMap<FString, FDinkPlayerBlockerShape> T;
	TArray<FString> Errors;
	TestTrue(TEXT("parses"), DinkPlayerBlockers::Parse(TEXT(R"({"schema":"dink-player-blockers/1","meshes":[
		{"mesh":"/Game/A.A","hull_cm":[[0,0],[10,0],[0,10]],"z_cm":[-10,150]},
		{"mesh":"/Game/B.B","hull_cm":[[0,0],[10,0]],"z_cm":[0,1]}]})"), T, Errors));
	TestEqual(TEXT("one good row"), T.Num(), 1);
	TestEqual(TEXT("one error"), Errors.Num(), 1);
	FString Text;
	if (FFileHelper::LoadFileToString(Text, *DinkPlayerBlockers::DefaultPath()))
	{
		T.Reset(); Errors.Reset();
		TestTrue(TEXT("shipped table parses"), DinkPlayerBlockers::Parse(Text, T, Errors));
		TestEqual(TEXT("shipped table has no bad rows"), Errors.Num(), 0);
		for (const auto& Pair : T)
			TestTrue(FString::Printf(TEXT("%s exists"), *Pair.Key), FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(Pair.Key)));
	}
	return true;
}
