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
	TestTrue(TEXT("schema 2: every relaxed placement has its drawn footprint"), [&Game]() { for (const auto& P : Game.Relaxed) for (const int32 N : P.Value) if (!Game.Feet.Contains(P.Key * 1000 + N)) return false; return true; }());
	TestTrue(TEXT("schema 2: open tiles (grass_rocky, playtest P1) listed, SCR_408 among them"), Game.OpenTiles.Contains(408) && Game.OpenTiles[408].Contains(52));
	// PlayHardness: a relaxed box only at its footprint, an open tile's code nowhere, everything as in 1997 with the layer off
	TestTrue(TEXT("schema 2 parses"), E.G->GetPhysicalPlaySettings().ParseRelaxed(TEXT("{\"screens\": {\"5\": [21]}, \"feet\": {\"5\": {\"21\": [10, 10, 20, 20]}}, \"open_tiles\": {\"5\": [0]}}")));
	Mode.Set(2);
	TestEqual(TEXT("layer on: a relaxed box inside its footprint stays"), E.G->PlayHardness(5, 15, 15, 121), 121);
	TestEqual(TEXT("layer on: a relaxed box outside its footprint is open"), E.G->PlayHardness(5, 30, 30, 121), 0);
	TestEqual(TEXT("layer on: another placement's box stays"), E.G->PlayHardness(5, 30, 30, 122), 122);
	TestEqual(TEXT("layer on: an open tile's low hardness is open"), E.G->PlayHardness(5, 5, 5, 2), 0);
	TestEqual(TEXT("layer on: the next tile's low hardness stays"), E.G->PlayHardness(5, 60, 5, 2), 2);
	Mode.Set(0);
	TestEqual(TEXT("layer off: the relaxed box is the 1997 box"), E.G->PlayHardness(5, 30, 30, 121), 121);
	TestEqual(TEXT("layer off: the open tile is the 1997 tile"), E.G->PlayHardness(5, 5, 5, 2), 2);
	return true;
}

// The layer's parts: Collision, Touch and Bodies on in play (PR #160), Hits and CreatureReach on too (owner decision 19 Nov 2026:
// drawn contact for both sides), each switchable by its console variable, all inert while the layer is off.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicalPlayPartsTest, "Dink.PhysicalPlay.Parts", DINK_TEST_FLAGS)
bool FDinkPhysicalPlayPartsTest::RunTest(const FString& Parameters)
{
	using EPart = UDinkGameplay::EPhysicalPlayPart;
	DinkPhysicalPlayTest::FFixture E(*this);
	FDinkPhysicalPlaySettings Game;
	Game.Load();
	TestTrue(TEXT("the game's ini: Collision, Touch and Bodies on"), Game.bCollision && Game.bTouch && Game.bBodies);
	TestTrue(TEXT("the game's ini: Hits and CreatureReach on (owner decision 19 Nov 2026, drawn contact for both)"), Game.bHits && Game.bCreatureReach);
	const FDinkPhysicalPlaySettings Defaults;
	TestTrue(TEXT("the code's defaults match the ini (a missing key behaves as shipped: review of 22 Nov, nit 9)"),
		Defaults.bCollision && Defaults.bTouch && Defaults.bBodies && Defaults.bHits && Defaults.bCreatureReach);
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
	TestFalse(TEXT("layer on: a part the settings switch off is off"), E.G->IsPhysicalPlayPartOn(EPart::Hits));
	TestFalse(TEXT("layer on: CreatureReach off in these settings"), E.G->IsPhysicalPlayPartOn(EPart::CreatureReach));
	E.G->GetPhysicalPlaySettings().bHits = Game.bHits; E.G->GetPhysicalPlaySettings().bCreatureReach = Game.bCreatureReach;
	TestTrue(TEXT("layer on, the game's ini: Hits on"), E.G->IsPhysicalPlayPartOn(EPart::Hits));
	TestTrue(TEXT("layer on, the game's ini: CreatureReach on"), E.G->IsPhysicalPlayPartOn(EPart::CreatureReach));
	E.G->GetPhysicalPlaySettings().bHits = false; E.G->GetPhysicalPlaySettings().bCreatureReach = false;
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
	FDinkPhysicalPlayModeScope Hits(0, TEXT("dink.PhysicalPlay.Hits"));
	TestTrue(TEXT("layer on, part Hits off: the 1997 box decides, the far prop is hit"), E.Hit(Prop));
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
	S->Props.Add(TEXT("touch_damage"), 10); // a foe (finding 7 of 22 Nov: a harmless body carries no blocker)

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

	// review of 22 Nov 2026, finding 7: bodies that may stand in a doorway for good carry no blocker
	S->bFrozen = true;
	E.G->UpdateCreatureBodyBlockers();
	TestNull(TEXT("a frozen creature (sp_freeze, a cut-scene) blocks nothing"), UDinkGameplay::FindCreatureBodyBlocker(BugActor));
	S->bFrozen = false;
	S->Props.Add(TEXT("touch_damage"), 0);
	E.G->UpdateCreatureBodyBlockers();
	TestNull(TEXT("a harmless creature (no touch damage, no attack, not after Dink: a duck, a pig) blocks nothing"), UDinkGameplay::FindCreatureBodyBlocker(BugActor));
	S->Props.Add(TEXT("target"), 1);
	E.G->UpdateCreatureBodyBlockers();
	TestNotNull(TEXT("one that targets Dink blocks again"), UDinkGameplay::FindCreatureBodyBlocker(BugActor));
	S->Props.Add(TEXT("target"), 0);
	S->Props.Add(TEXT("touch_damage"), 10);
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

// Missiles at Dink (part CreatureReach, drawn contact for both: owner decision 19 Nov 2026). missile_brain hits Dink where the missile's
// pixel is inside his 1997 box (28 x 18 px) grown by its sp_range; with the layer on it must meet his drawn body (the capsule, grown by
// the range in cm), so a fireball passing beside him on screen no longer burns him. Layer off (the probe) or the part off: the 1997 box.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicalPlayMissileTest, "Dink.PhysicalPlay.MissileAtDrawnDink", DINK_TEST_FLAGS)
bool FDinkPhysicalPlayMissileTest::RunTest(const FString& Parameters)
{
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	UDinkDirector* D = Story->GetDirector();
	UDinkGameplay* G = Story->GetGameplay();
	Story->bRunScreenScripts = false;
	UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
	ADinkScreenVolume* Screen = World->SpawnActor<ADinkScreenVolume>();
	Screen->ScreenNumber = 1;
	Screen->Corners.NW = FVector2D(0, 0);
	Screen->Corners.NE = FVector2D(26.25, 0);
	Screen->Corners.SW = FVector2D(0, 17.5);
	Screen->Corners.SE = FVector2D(26.25, 17.5);
	Greybox->RegisterScreen(Screen);
	APawn* Pawn = World->SpawnActor<APawn>();
	UCapsuleComponent* Body = NewObject<UCapsuleComponent>(Pawn, TEXT("Body"));
	Body->InitCapsuleSize(28.f, 96.f);
	Pawn->SetRootComponent(Body);
	Body->RegisterComponent();
	FDinkSprite& Dink = D->GetDink();
	Dink.Actor = Pawn;
	Dink.Screen = 1;
	Dink.X = 320;
	Dink.Y = 200;
	Pawn->SetActorLocation(Screen->MapPixelToWorld(300, 200) + FVector(0, 0, 96));
	FVector P0, P1;
	TestTrue(TEXT("the screen maps pixels"), D->PixelToWorld(1, 320, 200, P0) && D->PixelToWorld(1, 321, 200, P1));
	const double CmPerPx = FVector::Dist2D(P0, P1);
	FDinkSprite Missile;
	Missile.Handle = 50;
	Missile.Screen = 1;
	auto At = [&](double Dx, double Dy) { Missile.X = Dink.X + Dx; Missile.Y = Dink.Y + Dy; return Missile; };
	// 12 px right of his point: inside his 1997 box (-14..14), beside his drawn body (the capsule's 28 cm)
	TestTrue(FString::Printf(TEXT("the test missile passes beside the drawn Dink (%.1f cm/px)"), CmPerPx), 12.0 * CmPerPx > 28.0 + 5.0 && 2.0 * CmPerPx < 28.0);
	FDinkPhysicalPlayModeScope Mode(0);
	FDinkPhysicalPlayModeScope Reach(1, TEXT("dink.PhysicalPlay.CreatureReach"));
	TestTrue(TEXT("layer off: the 1997 box decides, the missile beside him hits"), G->MissileHitsTarget(At(12, 0), Dink, 0));
	TestTrue(TEXT("layer off: a missile on him hits"), G->MissileHitsTarget(At(2, 0), Dink, 0));
	TestFalse(TEXT("layer off: a missile off his 1997 box misses"), G->MissileHitsTarget(At(20, 0), Dink, 0));
	Mode.Set(2);
	Reach.Set(0);
	TestTrue(TEXT("layer on, part CreatureReach off: the 1997 box decides"), G->MissileHitsTarget(At(12, 0), Dink, 0));
	Reach.Set(1);
	TestFalse(TEXT("layer on: the missile beside his drawn body misses"), G->MissileHitsTarget(At(12, 0), Dink, 0));
	TestFalse(TEXT("layer on: 8 px above his point (inside the 1997 box) misses too"), 8.0 * CmPerPx > 28.0 && G->MissileHitsTarget(At(0, -8), Dink, 0));
	TestTrue(TEXT("layer on: a missile on his drawn body hits"), G->MissileHitsTarget(At(2, 0), Dink, 0));
	TestTrue(TEXT("layer on: sp_range grows the drawn body (range 10 reaches 12 px off)"), G->MissileHitsTarget(At(12, 0), Dink, 10));
	Dink.Actor.Reset();
	TestTrue(TEXT("layer on, no drawn Dink: the 1997 box decides"), G->MissileHitsTarget(At(12, 0), Dink, 0));
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

// Review of the delta (23 Nov 2026, A): the 1997 fallback for a drawn target no one can walk to (DrawnTargetUnreachableInPlay) must
// never land a blow through a wall. A creature 3 m away, penned in on all four sides: with low pen walls (DinkHardLow: a ditch, water;
// Dink cannot enter, sight passes) the 1997 blow box lands, as on SCR_190; with the pen wall between them solid (Visibility) or a drawn
// hull (DinkPlayerBlock), it does not.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicalPlayNoHitThroughWallTest, "Dink.PhysicalPlay.NoFallbackThroughWalls", DINK_TEST_FLAGS)
bool FDinkPhysicalPlayNoHitThroughWallTest::RunTest(const FString& Parameters)
{
	DinkPhysicalPlayTest::FFixture E(*this);
	FDinkPhysicalPlayModeScope Mode(2);
	FDinkPhysicalPlayModeScope Hits(1, TEXT("dink.PhysicalPlay.Hits"));
	const int32 Bug = E.Target(FVector(300, 0, 25), FVector(0.5), TEXT("en-pill"));
	FDinkSprite* S = E.D->FindSprite(Bug);
	S->bActive = true;
	S->Props.Add(TEXT("brain"), 9);
	S->Props.Add(TEXT("hitpoints"), 5000);
	E.Mesh(Bug)->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	auto Wall = [&](const FVector& At, const FVector& Scale, FName Profile)
	{
		AStaticMeshActor* W = E.World->SpawnActor<AStaticMeshActor>();
		UStaticMeshComponent* M = W->GetStaticMeshComponent();
		M->SetMobility(EComponentMobility::Movable);
		M->SetStaticMesh(E.Cube);
		M->SetCollisionProfileName(Profile);
		M->SetHiddenInGame(true);
		M->SetWorldScale3D(Scale);
		W->SetActorLocation(At);
		return M;
	};
	// the pen: 10 cm walls 1.5 m from the creature's centre (wider than Dink's reach of 85 cm plus his capsule), 2.5 m tall
	UStaticMeshComponent* Near = Wall(FVector(150, 0, 125), FVector(0.1, 3.1, 2.5), DinkCollision::ProfileHardLow);
	Wall(FVector(450, 0, 125), FVector(0.1, 3.1, 2.5), DinkCollision::ProfileHardLow);
	Wall(FVector(300, 150, 125), FVector(3.1, 0.1, 2.5), DinkCollision::ProfileHardLow);
	Wall(FVector(300, -150, 125), FVector(3.1, 0.1, 2.5), DinkCollision::ProfileHardLow);
	TestTrue(TEXT("the penned creature is in Dink's 1997 blow box"), E.G->LegacyHitBoxContains(*E.D->FindSprite(Bug), 20, 0, 6, 0));
	TestTrue(TEXT("low pen (a ditch): unreachable, sight clear: the 1997 box lands the blow"), E.Hit(Bug));
	Near->SetCollisionProfileName(TEXT("BlockAll"));
	TestTrue(TEXT("(still alive and active for the next blows)"), E.D->FindSprite(Bug) && E.D->FindSprite(Bug)->bActive);
	TestFalse(TEXT("a solid wall between them: no blow through it"), E.Hit(Bug));
	Near->SetCollisionProfileName(DinkCollision::ProfilePlayerBlock);
	TestFalse(TEXT("a drawn hull (a fence, a pine) between them: no blow through it"), E.Hit(Bug));
	return true;
}
