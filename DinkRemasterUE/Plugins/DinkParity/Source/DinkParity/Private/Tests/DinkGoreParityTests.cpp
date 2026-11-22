// Gore parity with 1997 (15 Nov 2026, doc/remaster/GORE_STORY_PARITY.md): the original's hit blood (random_blood,
// dink.cpp:6675) is recorded by the simulation and drawn by UDinkBloodPresenter until the screen changes; sprite-class ground
// decals that replace a card are never smaller than that card's 1997 picture.
#include "DinkTestHelpers.h"
#include "DinkBloodPresenter.h"
#include "DinkDirector.h"
#include "DinkEnvironmentSubsystem.h"
#include "DinkGameplay.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Components/DecalComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHitBloodRulesTest, "Dink.Gore.HitBlood.SpurtSequenceAndSize", DINK_TEST_FLAGS)
bool FDinkHitBloodRulesTest::RunTest(const FString&)
{
	// random_blood: 187 + rand() % 3 unless the sprite sets sp_blood_seq and sp_blood_num (D:6680-6693)
	for (uint32 H = 0; H < 30; ++H)
	{
		const int32 Seq = UDinkBloodPresenter::SpurtSequence(0, 0, H);
		TestTrue(TEXT("default spurt is 187-189"), Seq >= 187 && Seq <= 189);
		const int32 Own = UDinkBloodPresenter::SpurtSequence(500, 2, H);
		TestTrue(TEXT("sp_blood_seq / sp_blood_num are honoured"), Own == 500 || Own == 501);
	}
	TestEqual(TEXT("a blood_seq without blood_num falls back to 187-189"), UDinkBloodPresenter::SpurtSequence(500, 0, 3u), 187);
	// the last frame of 188 is 39 x 56 px; at the placed splats' 2.5 cm/px that is 1.40 m: the decal is 1.15 x that
	TestTrue(TEXT("decal side from the longer side of the 1997 picture"), FMath::IsNearlyEqual(UDinkBloodPresenter::DecalSideCm(39, 56), 56.0 * 2.5 * 1.15, 0.001));
	TestTrue(TEXT("never smaller than the picture"), UDinkBloodPresenter::DecalSideCm(51, 56, 2.5, 0.5) >= 56.0 * 2.5);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCardDecalSquareTest, "Dink.Gore.CardDecal.NeverSmallerThanCard", DINK_TEST_FLAGS)
bool FDinkCardDecalSquareTest::RunTest(const FString&)
{
	FVector Centre;
	double Half = 0.0, Yaw = 0.0;
	// S533_P23: burn hole 158/3, card 4.02 x 3.90 m; the class size was a fixed 120 cm
	UDinkEnvironmentSubsystem::CardDecalSquare(FTransform(FRotator::ZeroRotator, FVector(1000.0, 2000.0, -20.0), FVector(4.0194, 1.0, 3.9)), 0.0, 120.0, 1.15, Centre, Half, Yaw);
	TestTrue(TEXT("covers the card's longer side and the margin"), FMath::IsNearlyEqual(Half, 0.5 * 401.94 * 1.15, 0.01));
	TestTrue(TEXT("the picture's middle lies north of the placement point"), Centre.Equals(FVector(1000.0, 2000.0 - (-20.0 + 195.0), 0.0), 0.01));
	TestTrue(TEXT("unturned screen"), FMath::IsNearlyZero(Yaw, 0.001));
	// a picture smaller than the class size keeps the class size
	UDinkEnvironmentSubsystem::CardDecalSquare(FTransform(FRotator::ZeroRotator, FVector::ZeroVector, FVector(0.5, 1.0, 0.4)), 0.0, 120.0, 1.15, Centre, Half, Yaw);
	TestTrue(TEXT("small pictures keep the class size"), FMath::IsNearlyEqual(Half, 60.0, 0.01));
	// a turned screen turns the offset with it
	UDinkEnvironmentSubsystem::CardDecalSquare(FTransform(FRotator(0.0, 90.0, 0.0), FVector::ZeroVector, FVector(1.0, 1.0, 2.0)), 0.0, 0.0, 1.0, Centre, Half, Yaw);
	TestTrue(TEXT("turned with the screen"), Centre.Equals(FVector(100.0, 0.0, 0.0), 0.01) && FMath::IsNearlyEqual(Yaw, 90.0, 0.001));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHitBloodEventsTest, "Dink.Gore.HitBlood.HurtBleedsWithTheOriginalsDraw", DINK_TEST_FLAGS)
bool FDinkHitBloodEventsTest::RunTest(const FString&)
{
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	Story->bRunScreenScripts = false;
	Story->bInstantMode = true;
	UDinkDirector* D = Story->GetDirector();
	UDinkGameplay* G = Story->GetGameplay();
	ADinkPlaceholderActor* Bonca = World->SpawnActor<ADinkPlaceholderActor>();
	Bonca->SetActorLocation(FVector(500.0, 300.0, 0.0));
	Bonca->Origin->OriginId = FDinkOriginId(91, 3);
	Bonca->Brain = 9;
	const int32 H = D->HandleForActor(Bonca);
	FDinkSprite* S = D->FindSprite(H);
	if (!TestNotNull(TEXT("sprite"), S)) return false;
	S->Props.Add(TEXT("hitpoints"), 20);
	S->Props.Add(TEXT("defense"), 0);
	S->X = 320.0;
	S->Y = 200.0;
	// the bonca stands on the screen the player is on (the presenter draws the current screen's blood only)
	S->Screen = D->GetCurrentScreen();

	const uint32 Serial0 = G->GetBloodSerial();
	const int32 Trace0 = G->Events.Num();
	TestEqual(TEXT("a damaging hurt hurts"), G->HurtAndBleed(H, 5), 5);
	TestEqual(TEXT("and bleeds once (D:9953-9954)"), G->GetBloodSerial(), Serial0 + 1);
	const FDinkBloodEvent& E = G->GetBloodEvents().Last();
	TestEqual(TEXT("the hit sprite bled"), E.Sprite, H);
	TestTrue(TEXT("at the sprite's pixel, spurt 40 px up"), E.X == 320.0 && E.Y == 200.0 && E.YOffset == 40);
	TestEqual(TEXT("hurt(0) does not bleed"), G->HurtAndBleed(H, 0), 0);
	TestEqual(TEXT("no blood without damage"), G->GetBloodSerial(), Serial0 + 1);
	G->NoteBlood(H, 40);
	TestEqual(TEXT("blood writes nothing to the gameplay trace"), G->Events.Num(), Trace0);
	// random_blood draws exactly one rand() for its spurt, as the original (D:6693, bug list A25)
	G->SetRandomSeed(4242);
	G->NoteBlood(H, 40);
	const int32 SpurtA = G->GetBloodEvents().Last().Seq;
	const int32 NextA = G->RandomModulo(1000000);
	G->SetRandomSeed(4242);
	const int32 Draw = G->RandomModulo(3);
	const int32 NextB = G->RandomModulo(1000000);
	TestEqual(TEXT("the spurt is 187 + rand() % 3"), SpurtA, 187 + Draw);
	TestEqual(TEXT("one draw, no more"), NextA, NextB);
	S->Props.Add(TEXT("blood_seq"), 500);
	S->Props.Add(TEXT("blood_num"), 2);
	G->NoteBlood(H, 40);
	TestTrue(TEXT("sp_blood_seq / sp_blood_num"), G->GetBloodEvents().Last().Seq == 500 || G->GetBloodEvents().Last().Seq == 501);
	S->Props.Remove(TEXT("blood_seq"));
	S->Props.Remove(TEXT("blood_num"));
	for (int32 I = 0; I < UDinkGameplay::MaxBloodEvents + 10; ++I) G->NoteBlood(H, 40);
	TestEqual(TEXT("the event list is bounded"), G->GetBloodEvents().Num(), UDinkGameplay::MaxBloodEvents);

	// the presenter draws the new events on the current screen as ground decals
	if (UDinkBloodPresenter* Blood = World->GetSubsystem<UDinkBloodPresenter>())
	{
		const int32 Made = Blood->Present(1.f);
		TestTrue(TEXT("decals for the new events"), Made > 0);
		TestTrue(TEXT("kept below the per-screen cap"), Blood->GetDecalCount() <= UDinkBloodPresenter::MaxDecals);
		if (Blood->GetDecalCount() > 0 && Blood->GetDecals().Last())
		{
			Blood->Present(1.f); // the spread finishes
			const UDecalComponent* C = Blood->GetDecals().Last();
			TestTrue(TEXT("at least the 1997 spurt picture (1.40 m)"), 2.0 * C->DecalSize.Y >= 140.0);
			TestTrue(TEXT("under the hit sprite"), FVector::Dist2D(C->GetComponentLocation(), Bonca->GetActorLocation()) < 1.0);
		}
		TestEqual(TEXT("old events are not drawn twice"), Blood->Present(0.f), 0);
	}
	else
	{
		AddWarning(TEXT("blood presenter not created in this world type"));
	}
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHitBloodDataTest, "Dink.Gore.HitBlood.ShippedMaterialsLoad", DINK_TEST_FLAGS)
bool FDinkHitBloodDataTest::RunTest(const FString&)
{
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!TestTrue(TEXT("environment.json reads"), FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Environment/environment.json")))
		&& FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) && Root.IsValid())) return false;
	const TSharedPtr<FJsonObject>* Row = nullptr;
	if (!TestTrue(TEXT("hit_blood section"), Root->TryGetObjectField(TEXT("hit_blood"), Row) && Row)) return false;
	const TArray<TSharedPtr<FJsonValue>>* Paths = nullptr;
	if (!TestTrue(TEXT("materials"), (*Row)->TryGetArrayField(TEXT("materials"), Paths) && Paths && Paths->Num() > 0)) return false;
	for (const TSharedPtr<FJsonValue>& V : *Paths)
	{
		UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, *V->AsString());
		if (TestNotNull(*FString::Printf(TEXT("%s loads"), *V->AsString()), M))
			TestTrue(*FString::Printf(TEXT("%s is a deferred decal"), *V->AsString()), M->GetMaterial() && M->GetMaterial()->MaterialDomain == MD_DeferredDecal);
	}
	const TSharedPtr<FJsonObject>* Px = nullptr;
	TestTrue(TEXT("the three 1997 spurt sequences have their last-frame size"), (*Row)->TryGetObjectField(TEXT("last_frame_px"), Px) && Px
		&& (*Px)->HasField(TEXT("187")) && (*Px)->HasField(TEXT("188")) && (*Px)->HasField(TEXT("189")));
	return true;
}

#include "DinkCorpsePresenter.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCorpseSequenceTest, "Dink.Gore.CorpseCard.DeathSequenceAsAddKillSprite", DINK_TEST_FLAGS)
bool FDinkCorpseSequenceTest::RunTest(const FString&)
{
	// what tools/dinkex finds in dink.ini: bonca 551/553/557/559, slayer 645, dragons 212/216 only
	const TSet<int32> Have = {551, 553, 557, 559, 645, 212, 216, 345};
	auto Has = [&Have](int32 Q) { return Have.Contains(Q); };
	TestEqual(TEXT("bonca facing 1"), UDinkCorpsePresenter::DeathSequence(550, 530, 1, Has), 551);
	TestEqual(TEXT("bonca facing 9"), UDinkCorpsePresenter::DeathSequence(550, 530, 9, Has), 559);
	TestEqual(TEXT("dragon facing 4: 214 does not exist, the mirrored 216 is used (D:12392-12404)"), UDinkCorpsePresenter::DeathSequence(210, 200, 4, Has), 216);
	TestEqual(TEXT("dragon facing 8 -> 212"), UDinkCorpsePresenter::DeathSequence(210, 200, 8, Has), 212);
	TestEqual(TEXT("no death base: base_walk + 5 (slayer 640 -> 645)"), UDinkCorpsePresenter::DeathSequence(-1, 640, 3, Has), 645);
	TestEqual(TEXT("Jack (people, walk 340) -> 345"), UDinkCorpsePresenter::DeathSequence(-1, 340, 3, Has), 345);
	TestEqual(TEXT("no death base and no base_walk + 5: the explosion 164 (brain 7, D:12384-12385)"), UDinkCorpsePresenter::DeathSequence(-1, 700, 3, Has), UDinkCorpsePresenter::Explosion);
	TestEqual(TEXT("a death base of 0 has no picture in 1997 either"), UDinkCorpsePresenter::DeathSequence(0, 640, 3, Has), 0);
	TestEqual(TEXT("a direction out of range is 3 (D:12361-12365)"), UDinkCorpsePresenter::DeathSequence(550, 530, 0, Has), 553);
	const FVector2D Size = UDinkCorpsePresenter::CardSizeCm(81, 61, 100);
	TestTrue(TEXT("card at the 1997 picture's size (2.5 cm a pixel)"), FMath::IsNearlyEqual(Size.X, 202.5, 0.01) && FMath::IsNearlyEqual(Size.Y, 152.5, 0.01));
	TestTrue(TEXT("sp_size scales it as the engine does"), FMath::IsNearlyEqual(UDinkCorpsePresenter::CardSizeCm(81, 61, 200).X, 405.0, 0.01));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCorpsePicturesTest, "Dink.Gore.CorpseCard.ShippedPictures", DINK_TEST_FLAGS)
bool FDinkCorpsePicturesTest::RunTest(const FString&)
{
	const FString Dir = FPaths::ProjectContentDir() / TEXT("Dink/Data/Sprites/Death");
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!TestTrue(TEXT("death_pictures.json reads"), FFileHelper::LoadFileToString(Text, *(Dir / TEXT("death_pictures.json")))
		&& FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) && Root.IsValid())) return false;
	const TSharedPtr<FJsonObject>* Table = nullptr;
	if (!TestTrue(TEXT("pictures"), Root->TryGetObjectField(TEXT("pictures"), Table) && Table)) return false;
	// every monster and person the scripts can kill whose 1997 corpse is a picture
	for (const int32 Seq : {551, 553, 557, 559, 645, 765, 785, 805, 825, 661, 681, 701, 212, 216, 225, 335, 345, 365, 415})
	{
		TestTrue(*FString::Printf(TEXT("picture %d listed"), Seq), (*Table)->HasField(FString::FromInt(Seq)));
		TestTrue(*FString::Printf(TEXT("picture %d.png present"), Seq), FPaths::FileExists(Dir / FString::Printf(TEXT("%d.png"), Seq)));
	}
	TestTrue(TEXT("the card mesh of the greybox exists"), FPackageName::DoesPackageExist(TEXT("/Game/Dink/_Generated/Shared/SM_DinkCard")));
	TestTrue(TEXT("the sprite card material of the greybox exists"), FPackageName::DoesPackageExist(TEXT("/Game/Dink/_Generated/Shared/M_DinkSprite")));
	return true;
}

#include "DinkFactSubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCorpseCardWorldTest, "Dink.Gore.CorpseCard.KilledSlayerLeavesItsPicture", DINK_TEST_FLAGS)
bool FDinkCorpseCardWorldTest::RunTest(const FString&)
{
	if (!FPackageName::DoesPackageExist(TEXT("/Game/Dink/_Generated/Shared/SM_DinkCard")))
	{
		AddWarning(TEXT("skipped: the generated world (card mesh) is not imported"));
		return true;
	}
	constexpr int32 Screen = 998;
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	Story->bRunScreenScripts = false;
	Story->bInstantMode = true;
	Story->GetFacts()->SetFact(TEXT("player_map"), Screen);
	UDinkDirector* D = Story->GetDirector();
	UDinkGameplay* G = Story->GetGameplay();
	ADinkScreenVolume* Room = World->SpawnActor<ADinkScreenVolume>();
	Room->ScreenNumber = Screen;
	Room->Corners.NW = FVector2D(0, 0); Room->Corners.NE = FVector2D(15, 0);
	Room->Corners.SW = FVector2D(0, 10); Room->Corners.SE = FVector2D(15, 10);
	World->GetSubsystem<UDinkGreyboxSubsystem>()->RegisterScreen(Room);
	// a slayer: brain 9, no death base, base_walk 640 -> its 1997 corpse is picture 645 (add_kill_sprite D:12369-12380)
	ADinkPlaceholderActor* Slayer = World->SpawnActor<ADinkPlaceholderActor>();
	Slayer->Origin->OriginId = FDinkOriginId(Screen, 3);
	Slayer->ScreenNumber = Screen;
	Slayer->Brain = 9;
	const int32 H = D->HandleForActor(Slayer);
	FDinkSprite* S = D->FindSprite(H);
	if (!TestNotNull(TEXT("sprite"), S)) return false;
	S->Screen = Screen;
	S->X = 320.0;
	S->Y = 200.0;
	S->Props.Add(TEXT("brain"), 9);
	S->Props.Add(TEXT("hitpoints"), 100);
	S->Props.Add(TEXT("defense"), 0);
	S->Props.Add(TEXT("base_walk"), 640);
	S->Props.Add(TEXT("base_death"), -1);
	UDinkCorpsePresenter* Corpses = World->GetSubsystem<UDinkCorpsePresenter>();
	if (!TestNotNull(TEXT("corpse presenter"), Corpses)) return false;
	Corpses->Present(0.f);
	TestEqual(TEXT("no card while it lives"), Corpses->GetCardCount(), 0);
	G->HurtThing(H, 500);
	G->ProcessDamage();
	Story->RunUntilIdle();
	TestFalse(TEXT("the simulation killed it"), D->FindSprite(H) && D->FindSprite(H)->bActive);
	TestEqual(TEXT("one card made"), Corpses->Present(0.f), 1);
	TestEqual(TEXT("the card stays"), Corpses->GetCardCount(), 1);
	if (Corpses->GetCardCount() == 1 && Corpses->GetCards()[0])
	{
		const FVector Scale = Corpses->GetCards()[0]->GetComponentScale();
		// picture 645 is 94 x 67 px at 2.5 cm a pixel
		TestTrue(TEXT("at the 1997 picture's size"), FMath::IsNearlyEqual(Scale.X, 2.35, 0.01) && FMath::IsNearlyEqual(Scale.Z, 1.675, 0.01));
		// 645's registration point is (62, 28) in 94 x 67 px (dink.ini offsets, get_box D:3164-3260): the picture lies 15 px west and
		// 39 px south of its middle-bottom foot as 1997 draws it, so the card stands on (305, 239), not on the sprite's point
		FVector Foot;
		TestTrue(TEXT("pixel to world"), D->PixelToWorld(Screen, 305.0, 239.0, Foot));
		TestTrue(TEXT("the card stands where 1997 drew the picture's foot"), FVector::Dist2D(Corpses->GetCards()[0]->GetComponentLocation(), Foot) < 1.0);
	}
	TestEqual(TEXT("not left twice"), Corpses->Present(0.f), 0);
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCorpseCardFirstBlowTest, "Dink.Gore.CorpseCard.GoblinKilledByItsFirstBlow", DINK_TEST_FLAGS)
bool FDinkCorpseCardFirstBlowTest::RunTest(const FString&)
{
	// A goblin is made with brain 16 and its `hit` makes it brain 9; a single blow can kill it before the presenter sees brain 9. The 1997
	// kill leaves its corpse whatever the blow count (people_brain D:13099-13109 after brain 0, pill_brain 12901-12910; add_kill_sprite
	// with no death base: base_walk + 5, 12369-12383): the goblin of base_walk 760 leaves picture 765. Before 16 Nov the presenter required
	// the brain of its last reading and left nothing (seen on SCR_680, PR #188).
	if (!FPackageName::DoesPackageExist(TEXT("/Game/Dink/_Generated/Shared/SM_DinkCard")))
	{
		AddWarning(TEXT("skipped: the generated world (card mesh) is not imported"));
		return true;
	}
	constexpr int32 Screen = 998;
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	Story->bRunScreenScripts = false;
	Story->bInstantMode = true;
	Story->GetFacts()->SetFact(TEXT("player_map"), Screen);
	UDinkDirector* D = Story->GetDirector();
	UDinkGameplay* G = Story->GetGameplay();
	ADinkScreenVolume* Room = World->SpawnActor<ADinkScreenVolume>();
	Room->ScreenNumber = Screen;
	Room->Corners.NW = FVector2D(0, 0); Room->Corners.NE = FVector2D(15, 0);
	Room->Corners.SW = FVector2D(0, 10); Room->Corners.SE = FVector2D(15, 10);
	World->GetSubsystem<UDinkGreyboxSubsystem>()->RegisterScreen(Room);
	UDinkCorpsePresenter* Corpses = World->GetSubsystem<UDinkCorpsePresenter>();
	if (!TestNotNull(TEXT("corpse presenter"), Corpses)) return false;
	for (const int32 BrainAtKill : { 9, 16 })
	{
		ADinkPlaceholderActor* Goblin = World->SpawnActor<ADinkPlaceholderActor>();
		Goblin->Origin->OriginId = FDinkOriginId(Screen, 10 + BrainAtKill);
		Goblin->ScreenNumber = Screen;
		Goblin->Brain = 16;
		const int32 H = D->HandleForActor(Goblin);
		FDinkSprite* S = D->FindSprite(H);
		if (!TestNotNull(TEXT("sprite"), S)) return false;
		S->Screen = Screen;
		S->X = 200.0 + 60.0 * BrainAtKill;
		S->Y = 200.0;
		S->Props.Add(TEXT("brain"), 16);
		S->Props.Add(TEXT("hitpoints"), 30);
		S->Props.Add(TEXT("defense"), 0);
		S->Props.Add(TEXT("base_walk"), 760);
		S->Props.Add(TEXT("base_death"), -1);
		const int32 Before = Corpses->GetCardCount();
		Corpses->Present(0.f); // its last reading: brain 16
		S->Props.Add(TEXT("brain"), BrainAtKill); // what the frame of the blow leaves (its `hit` ran: 9; or nothing: 16)
		G->HurtThing(H, 500);
		G->ProcessDamage();
		Story->RunUntilIdle();
		TestFalse(*FString::Printf(TEXT("brain %d at the kill: the simulation killed it"), BrainAtKill), D->FindSprite(H) && D->FindSprite(H)->bActive);
		Corpses->Present(0.f);
		TestEqual(*FString::Printf(TEXT("brain %d at the kill: its corpse picture is left"), BrainAtKill), Corpses->GetCardCount(), Before + 1);
	}
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGoreDecalOpensGrassTest, "Dink.Gore.Grass.CorpsePoolOpensTheCarpet", DINK_TEST_FLAGS)
bool FDinkGoreDecalOpensGrassTest::RunTest(const FString&)
{
	// The grass carpet opens over placed ground decals; a corpse pool, hit blood or Dink's death pool (tagged by
	// UDinkEnvironmentSubsystem::OpenGrassUnder) must open it too, or the blood only tints the grass tips and SCR_680 shows less blood than
	// the 1997 picture 765 (PR #188 review). An untagged decal opens nothing.
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkEnvironmentSubsystem* Env = World ? World->GetSubsystem<UDinkEnvironmentSubsystem>() : nullptr;
	if (!TestNotNull(TEXT("environment subsystem"), Env)) return false;
	AActor* Holder = World->SpawnActor<AActor>();
	USceneComponent* Root = NewObject<USceneComponent>(Holder);
	Holder->SetRootComponent(Root);
	Root->RegisterComponent();
	Env->GatherGrassClearsNow();
	const int32 Before = Env->NumGrassClears();
	UDecalComponent* Plain = NewObject<UDecalComponent>(Holder);
	Plain->DecalSize = FVector(40.0, 60.0, 60.0);
	Plain->RegisterComponent();
	Env->GatherGrassClearsNow();
	TestEqual(TEXT("an untagged decal opens nothing"), Env->NumGrassClears(), Before);
	UDecalComponent* Pool = NewObject<UDecalComponent>(Holder);
	Pool->DecalSize = FVector(40.0, 60.0, 60.0);
	Pool->RegisterComponent();
	UDinkEnvironmentSubsystem::OpenGrassUnder(Pool);
	TestTrue(TEXT("the pool carries the clearing tag"), Pool->ComponentHasTag(UDinkEnvironmentSubsystem::GrassClearTag));
	Env->GatherGrassClearsNow();
	TestEqual(TEXT("the tagged pool opens one clearing"), Env->NumGrassClears(), Before + 1);
	Pool->DestroyComponent();
	Env->GatherGrassClearsNow();
	TestEqual(TEXT("and it closes when the pool goes (screen change)"), Env->NumGrassClears(), Before);
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkKillBurstTest, "Dink.Gore.KillBurst.SimulationMakesSequence164", DINK_TEST_FLAGS)
bool FDinkKillBurstTest::RunTest(const FString&)
{
	// add_kill_sprite (dink.cpp:12359-12419): a killed sprite with no death base and no base_walk + 5 in dink.ini gets the blood burst:
	// add_sprite(x, y, 5, 164, 1) in the first free slot (the dead sprite is still active then, D:12909-12911), speed 0, base_walk 0,
	// seq 164, brain 7 (plays once, then goes), its size; add_exp after it; no rand(). One with base_walk + 5 gets its corpse picture
	// instead (a card, UDinkCorpsePresenter) and no burst sprite.
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	Story->bRunScreenScripts = false;
	Story->bInstantMode = true;
	UDinkDirector* D = Story->GetDirector();
	UDinkGameplay* G = Story->GetGameplay();
	if (!TestNotNull(TEXT("gameplay"), G)) return false;
	TestTrue(TEXT("dink.ini defines 164 (the burst) and 645 (the slayer's corpse, base_walk 640 + 5)"), G->GetData().SeqExists(164) && G->GetData().SeqExists(645));
	TestFalse(TEXT("and no 995"), G->GetData().SeqExists(995));
	auto Kill = [&](int32 BaseWalk, int32 Size) -> TPair<int32, int32>
	{
		const int32 H = D->CreateVirtualSprite(12, 320.0, 200.0);
		FDinkSprite* S = D->FindSprite(H);
		S->Props.Add(TEXT("brain"), 9);
		S->Props.Add(TEXT("hitpoints"), 10);
		S->Props.Add(TEXT("defense"), 0);
		S->Props.Add(TEXT("base_walk"), BaseWalk);
		S->Props.Add(TEXT("base_death"), -1);
		S->Props.Add(TEXT("size"), Size);
		const int32 Expected = D->AllocateHandle();
		G->HurtThing(H, 500);
		G->ProcessDamage();
		Story->RunUntilIdle();
		return TPair<int32, int32>(H, Expected);
	};
	const TPair<int32, int32> NoPicture = Kill(990, 80);
	TestFalse(TEXT("the sprite without a death picture is dead"), D->FindSprite(NoPicture.Key) && D->FindSprite(NoPicture.Key)->bActive);
	const FDinkSprite* Burst = D->FindSprite(NoPicture.Value);
	if (TestNotNull(TEXT("a burst sprite in the first free slot"), Burst))
	{
		TestEqual(TEXT("seq 164"), Burst->GetProp(TEXT("pseq")), 164);
		TestEqual(TEXT("brain 7"), Burst->GetProp(TEXT("brain")), 7);
		TestEqual(TEXT("speed 0"), Burst->GetProp(TEXT("speed")), 0);
		TestEqual(TEXT("the dead sprite's size"), Burst->GetProp(TEXT("size")), 80);
		TestTrue(TEXT("where it died"), FMath::IsNearlyEqual(Burst->X, 320.0) && FMath::IsNearlyEqual(Burst->Y, 200.0));
	}
	int32 Bursts = 0;
	for (const TPair<int32, FDinkSprite>& P : D->GetSprites()) if (P.Value.bActive && P.Value.GetProp(TEXT("pseq")) == 164) ++Bursts;
	const TPair<int32, int32> Slayer = Kill(640, 100);
	int32 After = 0;
	for (const TPair<int32, FDinkSprite>& P : D->GetSprites()) if (P.Value.bActive && P.Value.GetProp(TEXT("pseq")) == 164) ++After;
	TestTrue(TEXT("a sprite with base_walk + 5 (645) makes no burst"), After <= Bursts);
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGoreOffSwitchesTest, "Dink.Gore.OffSwitches.ClearAndConsume", DINK_TEST_FLAGS)
bool FDinkGoreOffSwitchesTest::RunTest(const FString&)
{
	// dink.HitBlood 0 and dink.CorpseCards 0 (Tick calls Suppress while a switch is off): what is drawn goes, and what happens while
	// the switch is off is never drawn later. The blood lies where random_blood drew it, even after the hit sprite walked on.
	if (!FPackageName::DoesPackageExist(TEXT("/Game/Dink/_Generated/Shared/SM_DinkCard")))
	{
		AddWarning(TEXT("skipped: the generated world (card mesh) is not imported"));
		return true;
	}
	constexpr int32 Screen = 998;
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	Story->bRunScreenScripts = false;
	Story->bInstantMode = true;
	Story->GetFacts()->SetFact(TEXT("player_map"), Screen);
	UDinkDirector* D = Story->GetDirector();
	UDinkGameplay* G = Story->GetGameplay();
	ADinkScreenVolume* Room = World->SpawnActor<ADinkScreenVolume>();
	Room->ScreenNumber = Screen;
	Room->Corners.NW = FVector2D(0, 0); Room->Corners.NE = FVector2D(15, 0);
	Room->Corners.SW = FVector2D(0, 10); Room->Corners.SE = FVector2D(15, 10);
	World->GetSubsystem<UDinkGreyboxSubsystem>()->RegisterScreen(Room);
	UDinkBloodPresenter* Blood = World->GetSubsystem<UDinkBloodPresenter>();
	UDinkCorpsePresenter* Corpses = World->GetSubsystem<UDinkCorpsePresenter>();
	if (!TestNotNull(TEXT("blood presenter"), Blood) || !TestNotNull(TEXT("corpse presenter"), Corpses)) return false;
	ADinkPlaceholderActor* Slayer = World->SpawnActor<ADinkPlaceholderActor>();
	Slayer->Origin->OriginId = FDinkOriginId(Screen, 4);
	Slayer->ScreenNumber = Screen;
	Slayer->Brain = 9;
	const int32 H = D->HandleForActor(Slayer);
	FDinkSprite* S = D->FindSprite(H);
	if (!TestNotNull(TEXT("sprite"), S)) return false;
	S->Screen = Screen;
	S->X = 320.0;
	S->Y = 200.0;
	S->Props.Add(TEXT("brain"), 9);
	S->Props.Add(TEXT("hitpoints"), 100);
	S->Props.Add(TEXT("defense"), 0);
	S->Props.Add(TEXT("base_walk"), 640);
	S->Props.Add(TEXT("base_death"), -1);
	Blood->Present(0.f);
	Corpses->Present(0.f);

	// hit at (320, 200), then the sprite walks on before the presenter's frame
	TestEqual(TEXT("the hit hurts"), G->HurtAndBleed(H, 5), 5);
	S->X = 100.0;
	S->Y = 100.0;
	FVector Moved;
	if (D->PixelToWorld(Screen, 100.0, 100.0, Moved)) Slayer->SetActorLocation(Moved);
	TestEqual(TEXT("one decal"), Blood->Present(1.f), 1);
	FVector HitAt;
	TestTrue(TEXT("pixel to world"), D->PixelToWorld(Screen, 320.0, 200.0, HitAt));
	if (Blood->GetDecalCount() == 1 && Blood->GetDecals()[0])
		TestTrue(TEXT("the blood lies where the hit was, not where the sprite went"), FVector::Dist2D(Blood->GetDecals()[0]->GetComponentLocation(), HitAt) < 1.0);

	Blood->Suppress();
	TestEqual(TEXT("blood off: the decals go"), Blood->GetDecalCount(), 0);
	G->HurtAndBleed(H, 5);
	Blood->Suppress(); // a frame while the switch is off
	TestEqual(TEXT("a hit made while blood was off is not drawn when it comes back"), Blood->Present(1.f), 0);
	G->HurtAndBleed(H, 5);
	TestEqual(TEXT("blood on again: a new hit bleeds"), Blood->Present(1.f), 1);

	G->HurtThing(H, 500);
	G->ProcessDamage();
	Story->RunUntilIdle();
	TestEqual(TEXT("the kill leaves its card"), Corpses->Present(0.f), 1);
	Corpses->Suppress();
	TestEqual(TEXT("corpse cards off: the card goes"), Corpses->GetCardCount(), 0);
	TestEqual(TEXT("and does not come back with the switch"), Corpses->Present(0.f), 0);
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}
