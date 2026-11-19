// Dink.PhysicalPlay.*: the physical play layer (doc/remaster/PHYSICAL_PLAY_LAYER.md). With it on, Dink's blows and the touches on him
// use the drawn geometry of ANY drawn target (not only authored art); with it off (the default under automation, so the probe and
// parity tests) the 1997 pixel boxes decide. What a hit or touch does is the 1997 path either way.
#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkCollision.h"
#include "DinkStorySubsystem.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Engine/Engine.h"
#include "AssetCompilingManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

#include "HAL/IConsoleManager.h"
namespace DinkPhysicalPlayTest
{
	/** A real physics world with deliberately stale legacy sprite boxes. No generated map/art required. */
	struct FFixture
	{
		UWorld* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* G = nullptr;
		APawn* Pawn = nullptr;
		UStaticMesh* Cube = nullptr;

		explicit FFixture(FAutomationTestBase& Test)
		{
			UGameInstance* GI = DinkTest::MakeOuterGameInstance();
			UDinkFactSubsystem* Facts = NewObject<UDinkFactSubsystem>(GI);
			FString Error;
			Test.TestTrue(TEXT("initial facts load"), Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
			Story = NewObject<UDinkStorySubsystem>(GI);
			Test.TestTrue(TEXT("standalone story loads"), Story->SetupStandalone(Facts, NewObject<UDinkWorldStateSubsystem>(GI), &Error));
			Story->bInstantMode = true;
			D = Story->GetDirector();
			G = Story->GetGameplay();
			World = UWorld::CreateWorld(EWorldType::Game, false);
			GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
			Pawn = World->SpawnActor<APawn>();
			UCapsuleComponent* Body = NewObject<UCapsuleComponent>(Pawn, TEXT("Body"));
			Body->InitCapsuleSize(28.f, 96.f);
			Pawn->SetRootComponent(Body);
			Body->SetCollisionProfileName(TEXT("Pawn"));
			Body->RegisterComponent();
			Pawn->SetActorLocation(FVector(0,0,96));
			D->GetDink().Actor = Pawn;
			D->GetDink().Screen = 1;
			D->GetDink().X = 20;
			D->GetDink().Y = 0;
			D->GetDink().Dir = 6;
			Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
			FAssetCompilingManager::Get().FinishAllCompilation();
			Test.TestNotNull(TEXT("cube geometry"), Cube);
			Test.TestNotNull(TEXT("real physics scene"), World->GetPhysicsScene());
		}
		~FFixture() { if (World) { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); } }

		int32 Target(const FVector& MeshOffset, const FVector& Scale = FVector::OneVector, FName Script = TEXT("s1-h1-4"))
		{
			AStaticMeshActor* Actor = World->SpawnActor<AStaticMeshActor>();
			UStaticMeshComponent* Mesh = Actor->GetStaticMeshComponent();
			Mesh->SetMobility(EComponentMobility::Movable);
			USceneComponent* Origin = NewObject<USceneComponent>(Actor, TEXT("PlacementOrigin"));
			Actor->SetRootComponent(Origin);
			Origin->RegisterComponent();
			Mesh->AttachToComponent(Origin, FAttachmentTransformRules::KeepWorldTransform);
			Mesh->SetStaticMesh(Cube);
			Mesh->SetCollisionProfileName(TEXT("BlockAll"));
			Mesh->SetRelativeScale3D(Scale);
			Mesh->SetWorldLocation(MeshOffset);
			const int32 Handle = D->HandleForActor(Actor);
			FDinkSprite* S = D->FindSprite(Handle);
			S->Actor = Actor;
			S->Screen = 1;
			S->X = 20;
			S->Y = 0;
			S->Script = Script;
			// This old bed picture has a much wider pixel hardbox than the physical test prop.
			S->Props.Add(TEXT("pseq"), 64);
			S->Props.Add(TEXT("pframe"), 3);
			return Handle;
		}
		UStaticMeshComponent* Mesh(int32 Handle) const { return Cast<AStaticMeshActor>(D->FindSprite(Handle)->Actor.Get())->GetStaticMeshComponent(); }
		bool Hit(int32 Handle)
		{
			const int32 Before = G->Events.Num();
			G->RunThroughTagList(1);
			Story->RunUntilIdle();
			const FString Prefix = FString::Printf(TEXT("hit %d by 1"), Handle);
			for (int32 I = Before; I < G->Events.Num(); ++I) { if (G->Events[I].StartsWith(Prefix)) { return true; } }
			return false;
		}
	};
}




namespace
{
	struct FDinkPhysicalPlayModeScope
	{
		IConsoleVariable* Var = nullptr;
		int32 Old = -1;
		explicit FDinkPhysicalPlayModeScope(int32 Mode, const TCHAR* Name = TEXT("dink.PhysicalPlay")) { Var = IConsoleManager::Get().FindConsoleVariable(Name); if (Var) { Old = Var->GetInt(); Var->Set(Mode, ECVF_SetByConsole); } }
		void Set(int32 Mode) { if (Var) Var->Set(Mode, ECVF_SetByConsole); }
		~FDinkPhysicalPlayModeScope() { if (Var) Var->Set(Old, ECVF_SetByConsole); }
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicalPlaySwitchTest, "Dink.PhysicalPlay.Switch", DINK_TEST_FLAGS)
bool FDinkPhysicalPlaySwitchTest::RunTest(const FString& Parameters)
{
	DinkPhysicalPlayTest::FFixture E(*this);
	FDinkPhysicalPlayModeScope Mode(-1);
	TestNotNull(TEXT("console variable dink.PhysicalPlay"), Mode.Var);
	E.G->GetPhysicalPlaySettings().Mode = 1;
	TestFalse(TEXT("auto is off under automation (the probe and parity tests)"), E.G->IsPhysicalPlayActive());
	Mode.Set(2);
	TestTrue(TEXT("2 forces it on"), E.G->IsPhysicalPlayActive());
	Mode.Set(0);
	TestFalse(TEXT("0 is off"), E.G->IsPhysicalPlayActive());
	FDinkPhysicalPlaySettings S;
	TestTrue(TEXT("relaxed list parses"), S.ParseRelaxed(TEXT("{\"screens\": {\"214\": [5, 6], \"7\": []}}")));
	TestTrue(TEXT("relaxed placement listed"), S.Relaxed.Contains(214) && S.Relaxed[214].Contains(6) && !S.Relaxed[214].Contains(7));
	TestFalse(TEXT("bad json refused"), S.ParseRelaxed(TEXT("{")));
	FDinkPhysicalPlaySettings Game;
	Game.Load();
	TestTrue(TEXT("the game's relaxed list loads (Content/Dink/Data/Play/relaxed_hardboxes.json)"), Game.Relaxed.Num() > 100);
	return true;
}

// The layer's parts (coordinator decision on PR #160, 16 Nov 2026): Collision, Touch and Bodies on in play, Hits and CreatureReach off,
// each switchable by its console variable, all inert while the layer is off.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicalPlayPartsTest, "Dink.PhysicalPlay.Parts", DINK_TEST_FLAGS)
bool FDinkPhysicalPlayPartsTest::RunTest(const FString& Parameters)
{
	using EPart = UDinkGameplay::EPhysicalPlayPart;
	DinkPhysicalPlayTest::FFixture E(*this);
	FDinkPhysicalPlaySettings Game;
	Game.Load();
	TestTrue(TEXT("the game's ini: Collision, Touch and Bodies on"), Game.bCollision && Game.bTouch && Game.bBodies);
	TestTrue(TEXT("the game's ini: Hits and CreatureReach off (owner's open choice)"), !Game.bHits && !Game.bCreatureReach);
	FDinkPhysicalPlayModeScope Mode(0);
	FDinkPhysicalPlayModeScope Hits(1, TEXT("dink.PhysicalPlay.Hits"));
	FDinkPhysicalPlayModeScope Bodies(-1, TEXT("dink.PhysicalPlay.Bodies"));
	FDinkPhysicalPlayModeScope Touch(-1, TEXT("dink.PhysicalPlay.Touch"));
	FDinkPhysicalPlayModeScope Collision(-1, TEXT("dink.PhysicalPlay.Collision"));
	FDinkPhysicalPlayModeScope Reach(-1, TEXT("dink.PhysicalPlay.CreatureReach"));
	TestTrue(TEXT("every part's console variable exists"), Hits.Var && Bodies.Var && Touch.Var && Collision.Var && Reach.Var);
	E.G->GetPhysicalPlaySettings().bCollision = true; E.G->GetPhysicalPlaySettings().bTouch = true; E.G->GetPhysicalPlaySettings().bBodies = true;
	E.G->GetPhysicalPlaySettings().bHits = false; E.G->GetPhysicalPlaySettings().bCreatureReach = false;
	TestFalse(TEXT("layer off: a part forced on is inert"), E.G->IsPhysicalPlayPartOn(EPart::Hits));
	Mode.Set(2);
	Hits.Set(-1);
	TestTrue(TEXT("layer on: Collision on"), E.G->IsPhysicalPlayPartOn(EPart::Collision));
	TestTrue(TEXT("layer on: Touch on"), E.G->IsPhysicalPlayPartOn(EPart::Touch));
	TestTrue(TEXT("layer on: Bodies on"), E.G->IsPhysicalPlayPartOn(EPart::Bodies));
	TestFalse(TEXT("layer on: Hits off by default"), E.G->IsPhysicalPlayPartOn(EPart::Hits));
	TestFalse(TEXT("layer on: CreatureReach off by default"), E.G->IsPhysicalPlayPartOn(EPart::CreatureReach));
	Hits.Set(1); Reach.Set(1); Bodies.Set(0); Touch.Set(0); Collision.Set(0);
	TestTrue(TEXT("console 1 turns Hits on"), E.G->IsPhysicalPlayPartOn(EPart::Hits));
	TestTrue(TEXT("console 1 turns CreatureReach on"), E.G->IsPhysicalPlayPartOn(EPart::CreatureReach));
	TestFalse(TEXT("console 0 turns Bodies off"), E.G->IsPhysicalPlayPartOn(EPart::Bodies));
	TestFalse(TEXT("console 0 turns Touch off"), E.G->IsPhysicalPlayPartOn(EPart::Touch));
	TestFalse(TEXT("console 0 turns Collision off"), E.G->IsPhysicalPlayPartOn(EPart::Collision));
	// Touch off with the layer on: the 1997 touch box collects food drawn 4 m away again
	const int32 Food = E.Target(FVector(400, 0, 10), FVector(.2), TEXT("sfood"));
	E.Story->GetFacts()->SetFact(TEXT("life"), 5);
	E.Story->GetFacts()->SetFact(TEXT("lifemax"), 10);
	E.D->FindSprite(Food)->Props.Add(TEXT("touch_damage"), -1);
	E.G->RunThroughTouchDamageList(1);
	E.Story->RunUntilIdle();
	TestTrue(TEXT("layer on, Touch off: the 1997 box collects the far food"), E.Story->GetFacts()->GetFact(TEXT("life")) > 5);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicalPlayHitTest, "Dink.PhysicalPlay.HitAtDrawnContact", DINK_TEST_FLAGS)
bool FDinkPhysicalPlayHitTest::RunTest(const FString& Parameters)
{
	DinkPhysicalPlayTest::FFixture E(*this);
	FDinkPhysicalPlayModeScope Mode(0);
	// an unauthored drawn prop 4 m away whose 1997 box (an old bed picture, sprite on Dink's own pixel) contains Dink
	const int32 Prop = E.Target(FVector(400, 0, 50));
	TestTrue(TEXT("layer off: the 1997 box decides, the far prop is hit"), E.Hit(Prop));
	Mode.Set(2);
	FDinkPhysicalPlayModeScope Hits(-1, TEXT("dink.PhysicalPlay.Hits"));
	TestTrue(TEXT("layer on, part Hits off (the default): the 1997 box decides, the far prop is hit"), E.Hit(Prop));
	Hits.Set(1);
	TestFalse(TEXT("layer on, part Hits on: the prop 4 m away is out of reach"), E.Hit(Prop));
	E.Mesh(Prop)->SetWorldLocation(FVector(150, 0, 50));
	TestTrue(TEXT("layer on: reach touching the drawn prop lands the hit"), E.Hit(Prop));
	TestTrue(TEXT("the 1997 hit procedure ran"), E.Story->Events.ContainsByPredicate([](const FDinkNarrativeEvent& Event)
		{ return Event.Kind == TEXT("say") && Event.Text == TEXT("Why must I attack furniture?"); }));
	E.Pawn->SetActorRotation(FRotator(0, 180, 0));
	TestFalse(TEXT("layer on: facing away does not hit"), E.Hit(Prop));
	E.Pawn->SetActorRotation(FRotator::ZeroRotator);
	E.D->GetDink().Actor.Reset();
	TestTrue(TEXT("no drawn attacker: the 1997 box decides"), E.Hit(Prop));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicalPlayTouchTest, "Dink.PhysicalPlay.TouchAtDrawnContact", DINK_TEST_FLAGS)
bool FDinkPhysicalPlayTouchTest::RunTest(const FString& Parameters)
{
	DinkPhysicalPlayTest::FFixture E(*this);
	FDinkPhysicalPlayModeScope Mode(2);
	const int32 Food = E.Target(FVector(400, 0, 10), FVector(.2), TEXT("sfood"));
	E.Story->GetFacts()->SetFact(TEXT("life"), 5);
	E.Story->GetFacts()->SetFact(TEXT("lifemax"), 10);
	E.D->FindSprite(Food)->Props.Add(TEXT("touch_damage"), -1);
	E.G->RunThroughTouchDamageList(1);
	E.Story->RunUntilIdle();
	TestEqual(TEXT("layer on: food drawn 4 m away is not collected through its 1997 box"), E.Story->GetFacts()->GetFact(TEXT("life")), 5);
	E.Mesh(Food)->SetWorldLocation(FVector(45, 0, 10));
	E.G->RunThroughTouchDamageList(1);
	E.Story->RunUntilIdle();
	TestEqual(TEXT("layer on: touching the drawn food collects it (the 1997 touch procedure)"), E.Story->GetFacts()->GetFact(TEXT("life")), 8);
	const int32 Far = E.Target(FVector(400, 0, 10), FVector(.2), TEXT("sfood"));
	E.D->FindSprite(Far)->Props.Add(TEXT("touch_damage"), -1);
	Mode.Set(0);
	E.G->RunThroughTouchDamageList(1);
	E.Story->RunUntilIdle();
	TestTrue(TEXT("layer off: the 1997 box collects the far food"), E.Story->GetFacts()->GetFact(TEXT("life")) > 8);
	return true;
}

// Bug A21 (owner decision 16 Nov 2026): with the layer on a living creature body stops Dink (he cannot stand on or inside a
// pillbug); it never traps him, it does not stop the creature, and with the layer off (the probe) nothing is made.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicalPlayCreatureBodyTest, "Dink.PhysicalPlay.CreatureBodyBlocksDink", DINK_TEST_FLAGS)
bool FDinkPhysicalPlayCreatureBodyTest::RunTest(const FString& Parameters)
{
	DinkPhysicalPlayTest::FFixture E(*this);
	FDinkPhysicalPlayModeScope Mode(0);
	// The player capsule answers the player-only channel, as ADinkGreyboxCharacter's does.
	UCapsuleComponent* Capsule = Cast<UCapsuleComponent>(E.Pawn->GetRootComponent());
	Capsule->SetCollisionResponseToChannel(DinkCollision::PlayerBlock, ECR_Block);
	// A pillbug-sized body: the 1 m cube scaled to 1.2 x 0.6 x 0.4 m, its centre 3 m in front of Dink (+X).
	const int32 Bug = E.Target(FVector(300, 0, 20), FVector(1.2, 0.6, 0.4), TEXT("en-pill"));
	AActor* BugActor = E.D->FindSprite(Bug)->Actor.Get();
	BugActor->Tags.AddUnique(TEXT("DinkCreature"));
	E.Mesh(Bug)->SetCollisionEnabled(ECollisionEnabled::NoCollision); // a creature's drawn body has no collision of its own
	FDinkSprite* S = E.D->FindSprite(Bug);
	S->bActive = true;
	S->Props.Add(TEXT("brain"), 9);

	E.G->UpdateCreatureBodyBlockers();
	TestNull(TEXT("layer off: no body blocker (the probe kites creatures through the 1997 rules)"), UDinkGameplay::FindCreatureBodyBlocker(BugActor));

	Mode.Set(2);
	{
		FDinkPhysicalPlayModeScope Bodies(0, TEXT("dink.PhysicalPlay.Bodies"));
		E.G->UpdateCreatureBodyBlockers();
		TestNull(TEXT("layer on, part Bodies off: no body blocker"), UDinkGameplay::FindCreatureBodyBlocker(BugActor));
	}
	E.G->UpdateCreatureBodyBlockers();
	UBoxComponent* Box = UDinkGameplay::FindCreatureBodyBlocker(BugActor);
	if (!TestNotNull(TEXT("layer on: the living creature carries a body blocker"), Box)) return true;
	TestEqual(TEXT("player-only profile"), Box->GetCollisionProfileName(), DinkCollision::ProfilePlayerBlock);
	TestEqual(TEXT("the creature's moves (WorldDynamic) pass it"), Box->GetCollisionResponseToChannel(ECC_WorldDynamic), ECR_Ignore);
	TestEqual(TEXT("missiles pass it"), Box->GetCollisionResponseToChannel(DinkCollision::Projectile), ECR_Ignore);
	TestTrue(TEXT("Dink cannot step onto it"), Box->CanCharacterStepUpOn == ECB_No);

	FHitResult Hit;
	E.Pawn->SetActorLocation(FVector(500, 0, 96), true, &Hit);
	const double StopX = E.Pawn->GetActorLocation().X;
	TestTrue(TEXT("walking at the bug, Dink is stopped"), Hit.bBlockingHit);
	// body front at 300 - 60 = 240 cm; blocker 3 cm inside it (243); capsule radius 28: Dink stops at about 215 cm
	TestTrue(FString::Printf(TEXT("at the drawn body, not inside it and not short of it (stopped at %.1f cm)"), StopX), StopX > 205.0 && StopX < 216.0);

	// The bug walks into Dink: its blocker lets him go until he is clear (never a trap).
	BugActor->SetActorLocation(BugActor->GetActorLocation() - FVector(60, 0, 0));
	E.G->UpdateCreatureBodyBlockers();
	TestEqual(TEXT("a body that walked into Dink does not hold him"), Box->GetCollisionEnabled(), ECollisionEnabled::NoCollision);
	E.Pawn->SetActorLocation(FVector(0, 0, 96), true, &Hit);
	TestFalse(TEXT("he walks out of it freely"), Hit.bBlockingHit);
	E.G->UpdateCreatureBodyBlockers();
	TestEqual(TEXT("clear of it, the body blocks again"), Box->GetCollisionEnabled(), ECollisionEnabled::QueryAndPhysics);

	S->Props.Add(TEXT("brain"), 0);
	E.G->UpdateCreatureBodyBlockers();
	TestNull(TEXT("a dead creature (brain 0) blocks nothing"), UDinkGameplay::FindCreatureBodyBlocker(BugActor));
	S->Props.Add(TEXT("brain"), 9);
	E.G->UpdateCreatureBodyBlockers();
	TestNotNull(TEXT("alive again: blocker back"), UDinkGameplay::FindCreatureBodyBlocker(BugActor));
	Mode.Set(0);
	E.G->UpdateCreatureBodyBlockers();
	TestNull(TEXT("layer switched off: every body blocker removed"), UDinkGameplay::FindCreatureBodyBlocker(BugActor));
	return true;
}
