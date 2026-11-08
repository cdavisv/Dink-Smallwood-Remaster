#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
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

namespace DinkAuthoredInteractionTest
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
			Actor->Tags.Add(TEXT("DinkAuthoredArt"));
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

using namespace DinkAuthoredInteractionTest;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAuthoredHitTest, "Dink.Gameplay.AuthoredGeometry.HitAndPushUsePhysicalEdge", DINK_TEST_FLAGS)
bool FDinkAuthoredHitTest::RunTest(const FString& Parameters)
{
	FFixture E(*this);
	const int32 Prop = E.Target(FVector(400,0,50));
	TestFalse(TEXT("old huge hardbox cannot cause a hit 350 cm from the physical surface"), E.Hit(Prop));
	E.Mesh(Prop)->SetWorldLocation(FVector(150,0,50));
	TestTrue(TEXT("facing a surface 100 cm away lands the scripted hit"), E.Hit(Prop));
	TestTrue(TEXT("physical hit retains the original scripted line"), E.Story->Events.ContainsByPredicate([](const FDinkNarrativeEvent& Event)
		{ return Event.Kind == TEXT("say") && Event.Text == TEXT("Why must I attack furniture?"); }));
	AStaticMeshActor* Wall = E.World->SpawnActor<AStaticMeshActor>();
	Wall->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
	Wall->GetStaticMeshComponent()->SetStaticMesh(E.Cube);
	Wall->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
	Wall->SetActorScale3D(FVector(.2,2,2));
	Wall->SetActorLocation(FVector(75,0,100));
	TestFalse(TEXT("a nearby physical surface cannot be hit through an intervening wall"), E.Hit(Prop));
	Wall->Destroy();
	E.Pawn->SetActorRotation(FRotator(0,180,0));
	TestFalse(TEXT("facing away cannot hit a nearby authored mesh"), E.Hit(Prop));
	E.Pawn->SetActorRotation(FRotator::ZeroRotator);
	int32 Before = E.G->Events.Num();
	E.G->RunThroughTagListPush(1);
	TestEqual(TEXT("push requires contact rather than the old hardbox"), E.G->Events.Num(), Before);
	E.Mesh(Prop)->SetWorldLocation(FVector(80,0,50));
	E.G->RunThroughTagListPush(1);
	E.Story->RunUntilIdle();
	TestTrue(TEXT("physical contact still runs the original push procedure"), E.G->Events.Num() > Before);
	TestTrue(TEXT("physical push retains the original scripted line"), E.Story->Events.ContainsByPredicate([](const FDinkNarrativeEvent& Event)
		{ return Event.Kind == TEXT("say") && Event.Text == TEXT("This table must be bolted to the ground."); }));

	// Neither undressed nor virtual-sprite parity may inherit the authored-world distance gate.
	E.Mesh(Prop)->SetWorldLocation(FVector(400,0,50));
	E.D->FindSprite(Prop)->Actor->Tags.Remove(TEXT("DinkAuthoredArt"));
	TestTrue(TEXT("undressed sprite preserves the original pixel hit rule"), E.Hit(Prop));
	E.D->FindSprite(Prop)->Actor->Tags.Add(TEXT("DinkAuthoredArt"));
	E.D->GetDink().Actor.Reset();
	TestTrue(TEXT("virtual attacker preserves classic parity"), E.Hit(Prop));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAuthoredPickupTest, "Dink.Gameplay.AuthoredGeometry.PickupUsesRenderedComponentOffset", DINK_TEST_FLAGS)
bool FDinkAuthoredPickupTest::RunTest(const FString& Parameters)
{
	FFixture E(*this);
	const int32 Food = E.Target(FVector(400,0,10), FVector(.2), TEXT("sfood"));
	E.Story->GetFacts()->SetFact(TEXT("life"), 5);
	E.Story->GetFacts()->SetFact(TEXT("lifemax"), 10);
	E.D->FindSprite(Food)->Props.Add(TEXT("touch_damage"), -1);
	E.G->RunThroughTouchDamageList(1);
	E.Story->RunUntilIdle();
	TestEqual(TEXT("stale original hardbox cannot collect food at a remote mesh"), E.Story->GetFacts()->GetFact(TEXT("life")), 5);
	E.Mesh(Food)->SetWorldLocation(FVector(45,0,10));
	E.D->FindSprite(Food)->Props.Add(TEXT("touch_damage"), 2);
	E.G->RunThroughTouchDamageList(1);
	TestFalse(TEXT("damaging touch requires physical body contact, not pickup hand reach"), E.D->GetDink().bNoTouch);
	E.D->FindSprite(Food)->Props.Add(TEXT("touch_damage"), -1);
	E.G->RunThroughTouchDamageList(1);
	E.Story->RunUntilIdle();
	TestEqual(TEXT("food within hand reach of its actual component is collected"), E.Story->GetFacts()->GetFact(TEXT("life")), 8);
	TestEqual(TEXT("original pickup procedure disables touch after consumption"), E.D->FindSprite(Food)->GetProp(TEXT("touch_damage")), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAuthoredTalkTest, "Dink.Gameplay.AuthoredGeometry.TalkUsesVisibleGeometryAndBodyProxy", DINK_TEST_FLAGS)
bool FDinkAuthoredTalkTest::RunTest(const FString& Parameters)
{
	FFixture E(*this);
	const int32 Far = E.Target(FVector(400,0,50));
	TestEqual(TEXT("authored talk ignores the old remote hardbox"), E.G->FindTalkTarget(1), 0);
	// Make the origin near while the mesh remains far. The old nearest-actor fallback used this origin.
	UStaticMeshComponent* Remote = E.Mesh(Far);
	TestFalse(TEXT("3.5 m legacy actor-origin fallback cannot bypass the authored gate"), E.Story->TryTalk(E.Pawn));
	Remote->SetWorldLocation(FVector(150,0,50));
	const int32 Near = E.Target(FVector(100,0,50));
	TestEqual(TEXT("nearest actual authored surface wins over handle order"), E.G->FindTalkTarget(1), Near);
	E.Pawn->SetActorRotation(FRotator(0,180,0));
	TestEqual(TEXT("authored talk is directional"), E.G->FindTalkTarget(1), 0);
	E.Pawn->SetActorRotation(FRotator::ZeroRotator);
	E.D->DeactivateSprite(Far, 0);
	E.D->DeactivateSprite(Near, 0);

	// An authored NPC hides its old card and explicitly supplies a physics body proxy.
	const int32 NPC = E.Target(FVector(600,0,50), FVector::OneVector, TEXT("s1-h1-m"));
	E.Mesh(NPC)->SetHiddenInGame(true);
	E.Mesh(NPC)->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	AActor* Actor = E.D->FindSprite(NPC)->Actor.Get();
	UCapsuleComponent* Body = NewObject<UCapsuleComponent>(Actor, TEXT("AuthoredBody"));
	Body->InitCapsuleSize(28.f, 85.f);
	Body->ComponentTags.Add(TEXT("DinkAuthoredInteraction"));
	Body->SetCollisionProfileName(TEXT("Pawn"));
	Body->RegisterComponent();
	Body->SetWorldLocation(FVector(120,0,85));
	TestEqual(TEXT("NPC capsule is used instead of its hidden card"), E.G->FindTalkTarget(1), NPC);
	Actor->Tags.Remove(TEXT("DinkAuthoredArt"));
	TestEqual(TEXT("ordinary undressed NPC retains its original talk rule"), E.G->FindTalkTarget(1), NPC);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAuthoredRestoreCollisionTest, "Dink.Gameplay.AuthoredGeometry.RestoredInactiveActorCannotBlock", DINK_TEST_FLAGS)
bool FDinkAuthoredRestoreCollisionTest::RunTest(const FString& Parameters)
{
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	if (!TestNotNull(TEXT("real game world"), World) || !TestNotNull(TEXT("story subsystem"), Story)) { return false; }
	Story->bRunScreenScripts = false;
	ADinkPlaceholderActor* Prop = World->SpawnActor<ADinkPlaceholderActor>();
	Prop->Origin->OriginId = FDinkOriginId(1,22);
	Prop->Origin->ScriptName = TEXT("s1-h1-4");
	Prop->Card->SetMobility(EComponentMobility::Movable);
	Prop->Card->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")));
	Prop->Card->SetRelativeLocation(FVector(0,0,50));
	Prop->Card->SetCollisionProfileName(TEXT("BlockAll"));
	FAssetCompilingManager::Get().FinishAllCompilation();
	UDinkDirector* D = Story->GetDirector();
	const int32 Handle = D->HandleForActor(Prop);
	const TSharedPtr<FJsonObject> Active = D->SaveState();
	D->FindSprite(Handle)->bActive = false;
	const TSharedPtr<FJsonObject> Inactive = D->SaveState();
	auto Blocks = [World]()
	{
		FHitResult Hit;
		return World->LineTraceSingleByChannel(Hit, FVector(-200,0,50), FVector(200,0,50), ECC_Visibility, FCollisionQueryParams(TEXT("AuthoredRestore"), true));
	};
	TestTrue(TEXT("authored prop initially blocks the path"), Blocks());
	D->LoadState(Inactive);
	TestFalse(TEXT("inactive saved prop no longer blocks after rebind"), Blocks());
	TestTrue(TEXT("inactive saved prop is hidden"), Prop->IsHidden());
	D->LoadState(Active);
	TestTrue(TEXT("loading an earlier active save restores the physical prop"), Blocks());
	TestFalse(TEXT("active saved prop is visible again"), Prop->IsHidden());
	D->FindSprite(Handle)->Props.Add(TEXT("nodraw"), 1);
	D->LoadState(D->SaveState());
	TestTrue(TEXT("nodraw remains hidden"), Prop->IsHidden());
	TestTrue(TEXT("nodraw retains the original blocking intent"), Blocks());
	Prop->Vision = 1;
	Story->GetFacts()->SetFact(TEXT("vision"), 0);
	D->LoadState(Active);
	TestFalse(TEXT("a hidden vision variant stays nonblocking"), Blocks());
	Story->GetFacts()->SetFact(TEXT("vision"), 1);
	D->LoadState(Active);
	TestTrue(TEXT("the restored matching vision variant blocks"), Blocks());
	Prop->Destroy();
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAuthoredTabletopPickupTest, "Dink.Gameplay.AuthoredGeometry.TabletopPickupPreservesGroundAndWallLimits", DINK_TEST_FLAGS)
bool FDinkAuthoredTabletopPickupTest::RunTest(const FString& Parameters)
{
	FFixture E(*this);
	const int32 Food = E.Target(FVector(90,0,10), FVector(.2), TEXT("sfood"));
	E.Story->GetFacts()->SetFact(TEXT("life"), 5);
	E.Story->GetFacts()->SetFact(TEXT("lifemax"), 10);
	E.D->FindSprite(Food)->Props.Add(TEXT("touch_damage"), -1);
	auto Touch = [&E]() { E.G->RunThroughTouchDamageList(1); E.Story->RunUntilIdle(); };
	Touch();
	TestEqual(TEXT("ground pickup 80 cm from the body center remains out of reach"), E.Story->GetFacts()->GetFact(TEXT("life")), 5);
	auto Obstacle = [&E](const FVector& Location, const FVector& Scale)
	{
		AStaticMeshActor* Actor = E.World->SpawnActor<AStaticMeshActor>();
		Actor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
		Actor->GetStaticMeshComponent()->SetStaticMesh(E.Cube);
		Actor->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
		Actor->SetActorScale3D(Scale);
		Actor->SetActorLocation(Location);
		return Actor;
	};
	Obstacle(FVector(180,0,45), FVector(2.4,1.2,.9)); // table: top90cm, near edge60cm
	AActor* Chair = Obstacle(FVector(45,0,55), FVector(.2,1,1.1)); // a110cm back blocks walking
	E.Mesh(Food)->SetWorldLocation(FVector(200,0,100));
	Touch();
	TestEqual(TEXT("remote raised food still cannot be collected"), E.Story->GetFacts()->GetFact(TEXT("life")), 5);
	E.Mesh(Food)->SetWorldLocation(FVector(110,0,100));
	FHitResult BodyHit;
	const FCollisionQueryParams BodyParams(TEXT("TabletopPickupBody"), true, E.Pawn);
	TestTrue(TEXT("the pawn cannot walk through the chair to reach the tabletop item"), E.World->SweepSingleByChannel(BodyHit,
		E.Pawn->GetActorLocation(), E.Pawn->GetActorLocation() + FVector(110,0,0), FQuat::Identity, ECC_Pawn,
		FCollisionShape::MakeCapsule(28,96), BodyParams));
	TestEqual(TEXT("the chair is the actual body obstruction"), BodyHit.GetActor(), Chair);
	AActor* Wall = Obstacle(FVector(70,0,100), FVector(.2,1,2));
	Touch();
	TestEqual(TEXT("elevated hand reach does not pass through a full-height wall"), E.Story->GetFacts()->GetFact(TEXT("life")), 5);
	Wall->Destroy();
	Touch();
	TestEqual(TEXT("shoulder-height reach over the chair collects food on the table"), E.Story->GetFacts()->GetFact(TEXT("life")), 8);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAuthoredHumanoidMovementTest, "Dink.Gameplay.AuthoredGeometry.HumanoidBrainAvoidsNewChair", DINK_TEST_FLAGS)
bool FDinkAuthoredHumanoidMovementTest::RunTest(const FString& Parameters)
{
	UStaticMesh* ChairMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Dink/Kits/Stonebrook/SM_Chair_Oak_01.SM_Chair_Oak_01"));
	if (!ChairMesh) { AddWarning(TEXT("skipped: authored chair not imported")); return true; }
	FAssetCompilingManager::Get().FinishAllCompilation();
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
	Screen->Corners.NW = FVector2D(0,0);
	Screen->Corners.NE = FVector2D(26.25,0);
	Screen->Corners.SW = FVector2D(0,17.5);
	Screen->Corners.SE = FVector2D(26.25,17.5);
	Greybox->RegisterScreen(Screen);
	ADinkPlaceholderActor* NPC = World->SpawnActor<ADinkPlaceholderActor>();
	NPC->GetRootComponent()->SetMobility(EComponentMobility::Movable);
	NPC->Card->SetMobility(EComponentMobility::Movable);
	NPC->Card->SetHiddenInGame(true);
	NPC->Tags.Add(TEXT("DinkHumanoid"));
	NPC->Tags.Add(TEXT("DinkAuthoredArt"));
	UCapsuleComponent* Body = NewObject<UCapsuleComponent>(NPC, TEXT("AuthoredBody"));
	Body->SetupAttachment(NPC->GetRootComponent());
	Body->InitCapsuleSize(28,85);
	Body->SetRelativeLocation(FVector(0,0,85));
	Body->SetCollisionProfileName(TEXT("Pawn"));
	Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Body->ComponentTags.Add(TEXT("DinkAuthoredInteraction"));
	Body->RegisterComponent();
	NPC->SetActorLocation(Screen->MapPixelToWorld(301,150));
	const int32 Handle = D->HandleForActor(NPC);
	AStaticMeshActor* Chair = World->SpawnActor<AStaticMeshActor>();
	Chair->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
	Chair->GetStaticMeshComponent()->SetStaticMesh(ChairMesh);
	Chair->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
	Chair->SetActorLocation(Screen->MapPixelToWorld(301,207));
	Chair->SetActorRotation(FRotator(0,180,0));
	D->GetDink().Screen = 1;
	D->GetDink().X = 321;
	D->GetDink().Y = 300;
	auto Reset = [&](bool NoHard, bool Virtual)
	{
		NPC->SetActorLocation(Screen->MapPixelToWorld(301,150));
		FDinkSprite* S = D->FindSprite(Handle);
		S->Actor = Virtual ? nullptr : NPC;
		S->Screen = 1; S->X = 321; S->Y = 150;
		S->bMoving = false;
		S->Props.Add(TEXT("brain"), 0);
		S->Props.Add(TEXT("follow"), 1);
		S->Props.Add(TEXT("speed"), 1);
		S->Props.Add(TEXT("base_walk"), -1);
		S->Props.Add(TEXT("move_nohard"), NoHard ? 1 : 0);
	};
	auto Walk = [&]() { for (int32 Frame = 0; Frame < 80; ++Frame) { G->ThinkSprite(Handle, Frame * (1000.0/60.0)); } };
	TestEqual(TEXT("the added chair has no legacy pixel hardness north of the table"), G->GetHard(1,321,200), 0);
	Reset(false,false);
	Walk();
	const FCollisionQueryParams Params(TEXT("HumanoidChairPenetration"), true, NPC);
	TestFalse(TEXT("authored humanoid body never enters the new chair"), World->OverlapBlockingTestByChannel(Body->GetComponentLocation(), FQuat::Identity,
		ECC_Pawn, FCollisionShape::MakeCapsule(28,85), Params));
	TestTrue(TEXT("normal brain movement stops before the chair, not at the later old table box"), D->FindSprite(Handle)->Y < 200.0);
	Reset(true,false);
	Walk();
	TestTrue(TEXT("move_nohard still intentionally crosses authored obstacles"), D->FindSprite(Handle)->Y > 220.0);
	Reset(false,true);
	Walk();
	TestEqual(TEXT("virtual classic movement still stops at the original table boundary"), D->FindSprite(Handle)->Y, 209.0);
	Reset(false,false);
	D->StartMove(*D->FindSprite(Handle), 2, 230);
	D->Tick(1000,1000);
	D->Tick(1000,2000);
	TestEqual(TEXT("existing scripted cutscene movement remains unaltered"), D->FindSprite(Handle)->Y, 230.0);
	Greybox->UnregisterScreen(Screen);
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureHiddenProxyTest,"Dink.Gameplay.AuthoredGeometry.HiddenCreatureBoxUsesPhysicalEdge",DINK_TEST_FLAGS)
bool FDinkCreatureHiddenProxyTest::RunTest(const FString&)
{
 FFixture E(*this); const int32 Handle=E.Target(FVector(600,0,50));
 AActor* Actor=E.D->FindSprite(Handle)->Actor.Get();
 E.Mesh(Handle)->SetHiddenInGame(true); E.Mesh(Handle)->SetCollisionEnabled(ECollisionEnabled::NoCollision);
 UBoxComponent* Body=NewObject<UBoxComponent>(Actor); Body->SetupAttachment(Actor->GetRootComponent()); Body->SetBoxExtent(FVector(60,25,40));
 Body->SetCollisionProfileName(TEXT("Pawn")); Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly); Body->SetHiddenInGame(true);
 Body->ComponentTags.Add(TEXT("DinkAuthoredInteraction")); Body->RegisterComponent(); Body->SetWorldLocation(FVector(150,0,40));
 TestTrue(TEXT("explicit hidden box proxy answers near physical hit"),E.Hit(Handle));
 Body->SetWorldRotation(FRotator(0,90,0));
 TestFalse(TEXT("rotating long body moves its near edge outside fist reach"),E.Hit(Handle));
 Body->SetWorldRotation(FRotator::ZeroRotator); Body->SetWorldLocation(FVector(260,0,40));
 TestFalse(TEXT("huge old picture box cannot hit far hidden proxy"),E.Hit(Handle));
 Actor->Tags.Remove(TEXT("DinkAuthoredArt"));
 TestTrue(TEXT("undressed classic hit still uses original hardbox"),E.Hit(Handle));
 return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureBoxMovementTest,"Dink.Gameplay.AuthoredGeometry.CreatureBrainSweepsRotatedFootprint",DINK_TEST_FLAGS)
bool FDinkCreatureBoxMovementTest::RunTest(const FString&)
{
 UGameInstance* GI=NewObject<UGameInstance>(GEngine); GI->InitializeStandalone(); UWorld* World=GI->GetWorld();
 UDinkStorySubsystem* Story=GI->GetSubsystem<UDinkStorySubsystem>(); Story->bRunScreenScripts=false;
 UDinkDirector* D=Story->GetDirector(); UDinkGameplay* G=Story->GetGameplay();
 UDinkGreyboxSubsystem* Greybox=World->GetSubsystem<UDinkGreyboxSubsystem>(); ADinkScreenVolume* Screen=World->SpawnActor<ADinkScreenVolume>();
 Screen->ScreenNumber=1; Screen->Corners.NW=FVector2D(0,0); Screen->Corners.NE=FVector2D(26.25,0); Screen->Corners.SW=FVector2D(0,17.5); Screen->Corners.SE=FVector2D(26.25,17.5); Greybox->RegisterScreen(Screen);
 ADinkPlaceholderActor* Pig=World->SpawnActor<ADinkPlaceholderActor>(); Pig->GetRootComponent()->SetMobility(EComponentMobility::Movable); Pig->Card->SetHiddenInGame(true);
 Pig->Tags.Add(TEXT("DinkCreature")); Pig->Tags.Add(TEXT("DinkAuthoredArt"));
 UBoxComponent* Body=NewObject<UBoxComponent>(Pig); Body->SetupAttachment(Pig->GetRootComponent()); Body->SetBoxExtent(FVector(80,25,35)); Body->SetRelativeLocation(FVector(0,0,35));
 Body->SetCollisionProfileName(TEXT("Pawn")); Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly); Body->ComponentTags.Add(TEXT("DinkAuthoredInteraction")); Body->RegisterComponent();
 const FVector Start=Screen->MapPixelToWorld(301,150); Pig->SetActorLocation(Start); const int32 Handle=D->HandleForActor(Pig);
 auto Wall=[&](float X) { AStaticMeshActor* A=World->SpawnActor<AStaticMeshActor>(); A->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable); A->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"))); A->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll")); A->SetActorScale3D(FVector(.1,10,2)); A->SetActorLocation(Start+FVector(X,200,100)); return A; };
 Wall(-45); Wall(45); FAssetCompilingManager::Get().FinishAllCompilation();
 D->GetDink().Screen=1; D->GetDink().X=321; D->GetDink().Y=300;
 auto Reset=[&](bool NoHard) { Pig->SetActorLocation(Start); FDinkSprite* S=D->FindSprite(Handle); S->Screen=1; S->X=321; S->Y=150; S->Props.Add(TEXT("brain"),0); S->Props.Add(TEXT("follow"),1); S->Props.Add(TEXT("speed"),1); S->Props.Add(TEXT("base_walk"),-1); S->Props.Add(TEXT("move_nohard"),NoHard ? 1 : 0); };
 auto Walk=[&]() { for (int32 I=0;I<35;++I) G->ThinkSprite(Handle,I*1000./60.); };
 Reset(false); Walk();
 TestTrue(TEXT("long pig facing south fits80cm aisle using rotated50cm width"),D->FindSprite(Handle)->Y>=184.);
 TestTrue(TEXT("creature actor follows original brain facing"),FMath::IsNearlyEqual(Pig->GetActorRotation().Yaw,90.,.1));
 TestTrue(TEXT("actual body world rotation matches validated facing"),Body->GetComponentQuat().AngularDistance(FRotator(0,90,0).Quaternion())<.001);
 const FCollisionQueryParams ActualParams(TEXT("ActualCreatureBody"),true,Pig);
 TestFalse(TEXT("actual committed body has no corridor penetration"),World->OverlapBlockingTestByChannel(Body->GetComponentLocation(),Body->GetComponentQuat(),ECC_Pawn,FCollisionShape::MakeBox(Body->GetScaledBoxExtent()),ActualParams));
 D->GetDink().X=221; D->GetDink().Y=D->FindSprite(Handle)->Y;
 const FVector BeforeTurn=Pig->GetActorLocation();
 G->ThinkSprite(Handle,1000.);
 TestTrue(TEXT("deferred fence turn moves at most one original pixel"),FVector::Dist2D(Pig->GetActorLocation(),BeforeTurn)<=4.375+.01);
 TestTrue(TEXT("unsafe fence turn keeps safe physical facing"),FMath::IsNearlyEqual(Pig->GetActorRotation().Yaw,90.,.1));
 TestFalse(TEXT("deferred turn leaves real body clear"),World->OverlapBlockingTestByChannel(Body->GetComponentLocation(),Body->GetComponentQuat(),ECC_Pawn,FCollisionShape::MakeBox(Body->GetScaledBoxExtent()),ActualParams));
 for (int32 I=0;I<40;++I) G->ThinkSprite(Handle,1100.+I*17.);
 TestTrue(TEXT("current-facing footprint stays inside fence inner edge"),Body->GetComponentLocation().X-Body->GetScaledBoxExtent().Y>=Start.X-40.-.01);
 const FVector AtFence=Pig->GetActorLocation();
 for (int32 I=0;I<5;++I) G->ThinkSprite(Handle,2000.+I*17.);
 TestTrue(TEXT("blocked current-facing steps stop at the fence"),Pig->GetActorLocation().Equals(AtFence,.01));
 TestFalse(TEXT("repeated blocked turns never penetrate fence"),World->OverlapBlockingTestByChannel(Body->GetComponentLocation(),Body->GetComponentQuat(),ECC_Pawn,FCollisionShape::MakeBox(Body->GetScaledBoxExtent()),ActualParams));
 D->GetDink().X=321; D->GetDink().Y=300;
 Reset(false); Body->SetRelativeRotation(FRotator(0,90,0)); Walk();
 TestTrue(TEXT("relative proxy rotation exposes160cm width and blocks same aisle"),D->FindSprite(Handle)->Y<=151.);
 Reset(true); Walk();
 TestTrue(TEXT("explicit move_nohard retains original obstacle override"),D->FindSprite(Handle)->Y>=184.);
 Greybox->UnregisterScreen(Screen); GI->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); return true;
}
