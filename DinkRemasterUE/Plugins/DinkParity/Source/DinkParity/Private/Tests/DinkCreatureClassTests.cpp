// Class rows of creatures.json (DinkCreatureClass.h): every placement of a sprite class and every script-made sprite of
// its sequences is shown by the animated creature, and nothing of the simulation changes.
#include "DinkTestHelpers.h"
#include "DinkCreatureClass.h"
#include "DinkCreatureClassComponent.h"
#include "DinkCreatureComponent.h"
#include "DinkCreaturePresenter.h"
#include "DinkCreatureSubsystem.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkGameplay.h"
#include "DinkOriginComponent.h"
#include "DinkScriptSpriteComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	TSharedPtr<FJsonObject> ParseJson(const FString& Text)
	{
		TSharedPtr<FJsonObject> Object;
		FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Object);
		return Object;
	}

	const TCHAR* ClassRowJson = TEXT(R"({"schema":"dink-creatures/1","classes":[
		{"class":"pillbug","mesh":"/Game/A/SK_Bug.SK_Bug","scale":1.5,"offset_cm":[1,2,3],
		 "locomotion":{"idle":"/Game/A/AN_Idle.AN_Idle","gaits":[{"clip":"/Game/A/AN_Walk.AN_Walk","speed_cm_s":80},{"clip":"/Game/A/AN_Run.AN_Run","speed_cm_s":400}]},
		 "roles":{"walk":{"sequences":[131,133],"locomotion":true},"attack":{"sequences":[135],"clip":"/Game/A/AN_Attack.AN_Attack"}},
		 "corpses":[{"sequences":[141,143],"mesh":"/Game/A/SM_Corpse.SM_Corpse","yaw_offset":90,"decal":{"material":"/Game/A/M_Pool.M_Pool","size_cm":[440,400],"depth_cm":30}}],
		 "materials":{"Body":"/Game/A/MI_Red.MI_Red"}},
		{"class":"duck","mesh":"/Game/A/SK_Duck.SK_Duck",
		 "roles":{"walk":{"sequences":[21,23],"locomotion":{"idle":"/Game/A/AN_DIdle.AN_DIdle","gaits":[{"clip":"/Game/A/AN_DWalk.AN_DWalk","speed_cm_s":60}]}},
		          "headless":{"sequences":[111,113],"mesh":"/Game/A/SK_Headless.SK_Headless","clip":"/Game/A/AN_HRun.AN_HRun","loop":true}}},
		{"class":"pillbug","mesh":"/Game/A/SK_Second.SK_Second","roles":{"walk":{"sequences":[131],"locomotion":true}}},
		{"class":"nolocomotion","mesh":"/Game/A/SK_X.SK_X","roles":{"attack":{"sequences":[500],"clip":"/Game/A/AN_X.AN_X"}}},
		{"class":"twice","mesh":"/Game/A/SK_X.SK_X","locomotion":{"idle":"/Game/A/I.I","gaits":[{"clip":"/Game/A/W.W","speed_cm_s":80}]},
		 "roles":{"walk":{"sequences":[600],"locomotion":true},"attack":{"sequences":[600],"clip":"/Game/A/AN_X.AN_X"}}},
		{"class":"noset","mesh":"/Game/A/SK_X.SK_X","roles":{"walk":{"sequences":[700],"locomotion":true}}},
		{"class":"fallinggaits","mesh":"/Game/A/SK_X.SK_X","locomotion":{"idle":"/Game/A/I.I","gaits":[{"clip":"/Game/A/R.R","speed_cm_s":400},{"clip":"/Game/A/W.W","speed_cm_s":80}]},
		 "roles":{"walk":{"sequences":[800],"locomotion":true}}},
		{"class":"nomesh","mesh":"SK_X","roles":{"walk":{"sequences":[900],"locomotion":true}}}
	]})");

	struct FClassArtMode
	{
		IConsoleVariable* Variable = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.CreatureClassArt"));
		IConsoleVariable* Art = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));
		int32 Previous = Variable ? Variable->GetInt() : 1, PreviousArt = Art ? Art->GetInt() : 1;
		explicit FClassArtMode(int32 Mode) { Set(Mode); if (Art) Art->SetWithCurrentPriority(1); }
		void Set(int32 Mode) { if (Variable) Variable->SetWithCurrentPriority(Mode); }
		~FClassArtMode() { if (Variable) Variable->SetWithCurrentPriority(Previous); if (Art) Art->SetWithCurrentPriority(PreviousArt); }
	};

	bool ShippedPillbugRowReady(FAutomationTestBase& Test)
	{
		FString Text;
		const TSharedPtr<FJsonObject> Manifest = FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/creatures.json"))) ? ParseJson(Text) : nullptr;
		TArray<FDinkCreatureClassBinding> Rows;
		if (Manifest) DinkCreatureClass::ParseBindings(*Manifest, Rows);
		const FDinkCreatureClassBinding* Pillbug = Rows.FindByPredicate([](const FDinkCreatureClassBinding& B) { return B.ClassId == TEXT("pillbug"); });
		if (!Test.TestNotNull(TEXT("creatures.json has a pillbug class row"), Pillbug)) return false;
		FString Package = Pillbug->Mesh;
		Package.Split(TEXT("."), &Package, nullptr);
		if (!FPackageName::DoesPackageExist(Package) || !LoadObject<USkeletalMesh>(nullptr, *Pillbug->Mesh, nullptr, LOAD_NoWarn | LOAD_Quiet))
		{
			Test.AddWarning(TEXT("skipped: the photoreal pillbug is not imported in this checkout"));
			return false;
		}
		return true;
	}

	ADinkPlaceholderActor* SpawnPlacement(UWorld* World, int32 Screen, int32 Index, FName ClassId, int32 Sequence, FName Script, UStaticMesh* CardMesh)
	{
		ADinkPlaceholderActor* Actor = World->SpawnActor<ADinkPlaceholderActor>();
		Actor->Origin->OriginId = FDinkOriginId(Screen, Index);
		Actor->Origin->ClassId = ClassId;
		Actor->Origin->Sequence = Sequence;
		Actor->Origin->Frame = 1;
		Actor->Origin->ScriptName = Script;
		Actor->ScreenNumber = Screen;
		Actor->PlacementKind = TEXT("live");
		Actor->Card->SetStaticMesh(CardMesh);
		Actor->GetRootComponent()->SetMobility(EComponentMobility::Movable);
		return Actor;
	}

	/** A 600 x 400 px screen laid out at 2.5 cm per pixel, registered with the greybox. */
	ADinkScreenVolume* SpawnRoom(UWorld* World, UDinkGreyboxSubsystem* Greybox, int32 Screen, double EastMetres)
	{
		ADinkScreenVolume* Room = World->SpawnActor<ADinkScreenVolume>();
		Room->ScreenNumber = Screen;
		Room->Corners.NW = FVector2D(EastMetres, 0); Room->Corners.NE = FVector2D(EastMetres + 15, 0);
		Room->Corners.SW = FVector2D(EastMetres, 10); Room->Corners.SE = FVector2D(EastMetres + 15, 10);
		Greybox->RegisterScreen(Room);
		return Room;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureClassRowsTest, "Dink.Art.CreatureClass.RowsDecisionsCorpsesAndGaits", DINK_TEST_FLAGS)
bool FDinkCreatureClassRowsTest::RunTest(const FString&)
{
	const TSharedPtr<FJsonObject> Manifest = ParseJson(ClassRowJson);
	if (!TestTrue(TEXT("fixture parses"), Manifest.IsValid())) return false;
	TArray<FDinkCreatureClassBinding> Rows;
	TArray<FString> Problems;
	TestEqual(TEXT("two rows kept"), DinkCreatureClass::ParseBindings(*Manifest, Rows, &Problems), 2);
	TestEqual(TEXT("six rows refused, each with its reason"), Problems.Num(), 6);
	if (Rows.Num() != 2) return false;
	const FDinkCreatureClassBinding& Bug = Rows[0];
	TestEqual(TEXT("first row of a class wins"), Bug.Mesh, FString(TEXT("/Game/A/SK_Bug.SK_Bug")));
	TestEqual(TEXT("scale read"), Bug.Scale, 1.5);
	TestEqual(TEXT("offset read"), Bug.OffsetCm, FVector(1, 2, 3));
	TestEqual(TEXT("two gaits, slowest first"), Bug.Locomotion.Gaits.Num(), 2);
	TestEqual(TEXT("material override read"), Bug.Materials.FindRef(TEXT("Body")), FString(TEXT("/Game/A/MI_Red.MI_Red")));
	TestTrue(TEXT("walk sequences are the locomotion role"), Bug.RoleFor(131) && Bug.RoleFor(131)->bLocomotion && Bug.RoleFor(133) == Bug.RoleFor(131));
	TestTrue(TEXT("attack sequence is a one-shot clip"), Bug.RoleFor(135) && !Bug.RoleFor(135)->bLocomotion && !Bug.RoleFor(135)->bLoop);
	TestNull(TEXT("unknown sequence has no role"), Bug.RoleFor(21));
	const FDinkCreatureClassBinding& Duck = Rows[1];
	TestTrue(TEXT("a role may carry its own locomotion set"), Duck.RoleFor(21) && Duck.RoleFor(21)->bLocomotion && Duck.RoleFor(21)->Locomotion.IsSet() && !Duck.Locomotion.IsSet());
	TestTrue(TEXT("a role may swap the mesh and loop a clip"), Duck.RoleFor(111) && Duck.RoleFor(111)->bLoop && Duck.RoleFor(111)->Mesh == TEXT("/Game/A/SK_Headless.SK_Headless"));

	// placements
	const TSet<FString> Precedence = { TEXT("S438_P03") };
	const FDinkCreatureClassBinding* Found = nullptr;
	TestTrue(TEXT("any placement of the class is bound"), DinkCreatureClass::Decide(Rows, TEXT("pillbug"), TEXT("S527_P04"), Precedence, true, Found) == EDinkCreatureClassDecision::Bound && Found == &Bug);
	TestTrue(TEXT("on any screen"), DinkCreatureClass::Decide(Rows, TEXT("pillbug"), TEXT("S030_P03"), Precedence, true, Found) == EDinkCreatureClassDecision::Bound);
	TestTrue(TEXT("an origin another manifest names keeps its binding"), DinkCreatureClass::Decide(Rows, TEXT("pillbug"), TEXT("S438_P03"), Precedence, true, Found) == EDinkCreatureClassDecision::OriginPrecedence && !Found);
	TestTrue(TEXT("a hardness proxy has no picture to replace"), DinkCreatureClass::Decide(Rows, TEXT("pillbug"), TEXT("S527_P04"), Precedence, false, Found) == EDinkCreatureClassDecision::NoPicture && !Found);
	TestTrue(TEXT("other classes keep their cards"), DinkCreatureClass::Decide(Rows, TEXT("slime_blue"), TEXT("S527_P04"), Precedence, true, Found) == EDinkCreatureClassDecision::NoRow);
	TestTrue(TEXT("no class, no row"), DinkCreatureClass::Decide(Rows, NAME_None, TEXT("S527_P04"), Precedence, true, Found) == EDinkCreatureClassDecision::NoRow);

	// script-made sprites
	DinkCreatureClass::FSpriteView View;
	View.PSeq = 133;
	TestTrue(TEXT("a script sprite with the class's picture"), DinkCreatureClass::FindBySprite(Rows, View) == &Bug);
	View = DinkCreatureClass::FSpriteView(); View.Seq = 23; View.PSeq = 400;
	TestTrue(TEXT("the animating sequence counts before the still picture"), DinkCreatureClass::FindBySprite(Rows, View) == &Duck);
	View = DinkCreatureClass::FSpriteView(); View.PSeq = 400; View.BaseWalk = 130;
	TestTrue(TEXT("any picture with the class's walk base"), DinkCreatureClass::FindBySprite(Rows, View) == &Bug);
	View = DinkCreatureClass::FSpriteView(); View.PSeq = 400; View.BaseWalk = 110;
	TestNull(TEXT("a walk base that only reaches a clip role binds nothing"), DinkCreatureClass::FindBySprite(Rows, View));
	View = DinkCreatureClass::FSpriteView(); View.PSeq = 164;
	TestNull(TEXT("an effect sprite binds nothing"), DinkCreatureClass::FindBySprite(Rows, View));

	// roles
	View = DinkCreatureClass::FSpriteView(); View.Seq = 135; View.PSeq = 131;
	TestTrue(TEXT("the animating sequence chooses the role"), DinkCreatureClass::RoleForSprite(Bug, View) == Bug.RoleFor(135));
	View.Seq = 0;
	TestTrue(TEXT("a still sprite shows its picture's role"), DinkCreatureClass::RoleForSprite(Bug, View) == Bug.RoleFor(131));
	View.PSeq = 999;
	TestTrue(TEXT("an unknown picture keeps the creature standing"), DinkCreatureClass::RoleForSprite(Bug, View) == Bug.RoleFor(131));

	// corpses: add_kill_sprite (dink.cpp:12359-12404)
	TestNotNull(TEXT("death base 140 facing 1 is corpse 141"), Bug.CorpseFor(140, 1));
	TestNotNull(TEXT("facing 7 falls back to the mirrored 143"), Bug.CorpseFor(140, 7));
	TestNotNull(TEXT("facing 9 falls back to the mirrored 141"), Bug.CorpseFor(140, 9));
	TestNotNull(TEXT("a direction out of range is taken as 3"), Bug.CorpseFor(140, 0));
	TestNull(TEXT("facing 2 has no death picture, mirrored or not"), Bug.CorpseFor(140, 2));
	TestNull(TEXT("no base_death, no corpse of this row"), Bug.CorpseFor(-1, 1));
	TestNull(TEXT("another death base is another creature's"), Bug.CorpseFor(660, 1));
	TestTrue(TEXT("the corpse's ground decal is read"), Bug.Corpses[0].DecalMaterial == TEXT("/Game/A/M_Pool.M_Pool") && Bug.Corpses[0].DecalSizeCm == FVector2D(440, 400) && Bug.Corpses[0].DecalDepthCm == 30.0);
	{
		// a decal without a material or a size refuses the row, as any other broken reference does
		TArray<FDinkCreatureClassBinding> Broken;
		TArray<FString> Why;
		const TSharedPtr<FJsonObject> Bad = ParseJson(TEXT(R"({"classes":[{"class":"x","mesh":"/Game/A/SK_X.SK_X","locomotion":{"idle":"/Game/A/I.I","gaits":[{"clip":"/Game/A/W.W","speed_cm_s":80}]},
			"roles":{"walk":{"sequences":[600],"locomotion":true}},"corpses":[{"sequences":[610],"mesh":"/Game/A/SM_C.SM_C","decal":{"material":"/Game/A/M.M","size_cm":[440]}}]}]})"));
		TestEqual(TEXT("a corpse decal without a size pair refuses its row"), Bad.IsValid() ? DinkCreatureClass::ParseBindings(*Bad, Broken, &Why) : -1, 0);
		TestEqual(TEXT("with one reason"), Why.Num(), 1);
	}

	// pill_brain turns the direction to a diagonal before the corpse is made, so a pillbug that chases (cardinal
	// directions, get_distance_and_dir) always leaves one; dragon_brain does not
	for (const int32 Dir : { 0, 1, 2, 3, 4, 6, 7, 8, 9 })
		TestNotNull(FString::Printf(TEXT("a pill brain killed facing %d leaves the corpse"), Dir), Bug.CorpseFor(140, DinkCreatureClass::KillDir(9, Dir)));
	TestEqual(TEXT("4 becomes 1"), DinkCreatureClass::KillDir(9, 4), 1);
	TestEqual(TEXT("6 becomes 9"), DinkCreatureClass::KillDir(9, 6), 9);
	TestEqual(TEXT("8 becomes 7"), DinkCreatureClass::KillDir(16, 8), 7);
	TestEqual(TEXT("dragon brain keeps the direction"), DinkCreatureClass::KillDir(10, 6), 6);
	TestEqual(TEXT("131 faces 1"), DinkCreatureClass::DirOfSequence(131), 1);
	TestEqual(TEXT("a sequence ending in 5 or 0 has no facing"), DinkCreatureClass::DirOfSequence(135) + DinkCreatureClass::DirOfSequence(140), 0);
	TestEqual(TEXT("east is yaw 0"), DinkCreatureClass::DirYawDegrees(6), 0.0);
	TestEqual(TEXT("south is yaw 90"), DinkCreatureClass::DirYawDegrees(2), 90.0);
	TestEqual(TEXT("north-west is yaw -135"), DinkCreatureClass::DirYawDegrees(7), -135.0);

	// gaits: the blended stride covers the speed exactly
	const float Speeds[] = { 80.f, 400.f }, Strides[] = { 30.f, 150.f };
	for (const float Speed : { 0.f, 4.f, 20.f, 80.f, 200.f, 400.f, 900.f })
	{
		float Idle = 0.f, Cycles = 0.f;
		TArray<float, TInlineAllocator<4>> Weights;
		DinkCreatureClass::SolveGaits(Speed, 5.f, Speeds, Strides, Idle, Weights, Cycles);
		const FString Label = FString::Printf(TEXT("%.0f cm/s"), Speed);
		TestTrue(Label + TEXT(": weights sum to one"), FMath::IsNearlyEqual(Idle + Weights[0] + Weights[1], 1.f, 1e-4f));
		if (Speed <= 5.f)
		{
			TestTrue(Label + TEXT(": stands"), Idle == 1.f && Cycles == 0.f);
			continue;
		}
		TestTrue(Label + TEXT(": moving shows a gait"), Weights[0] + Weights[1] > 0.f && Cycles > 0.f);
		if (Speed >= 80.f)
		{
			const float Stride = Speed >= 400.f ? 150.f : FMath::Lerp(30.f, 150.f, (Speed - 80.f) / 320.f);
			TestTrue(Label + TEXT(": cadence x stride is the speed (no foot sliding)"), FMath::IsNearlyEqual(Cycles * Stride, Speed, 0.01f));
			TestEqual(Label + TEXT(": no standing pose in a gait"), Idle, 0.f);
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureClassDressTest, "Dink.Art.CreatureClass.ShippedRowsDressEveryPlacementAndNothingElse", DINK_TEST_FLAGS)
bool FDinkCreatureClassDressTest::RunTest(const FString&)
{
	if (!ShippedPillbugRowReady(*this)) return true;
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	if (!TestNotNull(TEXT("card mesh"), Plane)) return false;
	for (const int32 Mode : { 1, 0, 2 })
	{
		FClassArtMode Art(Mode);
		UGameInstance* GI = NewObject<UGameInstance>(GEngine);
		GI->InitializeStandalone();
		UWorld* World = GI->GetWorld();
		ON_SCOPE_EXIT { GI->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
		UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
		Story->bRunScreenScripts = false; Story->bNewGamePending = false; Story->bInstantMode = true;
		// two screens far apart, the origin-bound pillbug of Stonebrook, a hardness proxy, and a sprite of another class
		ADinkPlaceholderActor* First = SpawnPlacement(World, 527, 4, TEXT("pillbug"), 131, TEXT("en-pill"), Plane);
		ADinkPlaceholderActor* Second = SpawnPlacement(World, 30, 3, TEXT("pillbug"), 133, TEXT("en-pill2"), Plane);
		ADinkPlaceholderActor* OriginBound = SpawnPlacement(World, 438, 3, TEXT("pillbug"), 131, TEXT("en-pill"), Plane);
		ADinkPlaceholderActor* Proxy = SpawnPlacement(World, 527, 5, TEXT("pillbug"), 131, NAME_None, Plane);
		Proxy->PlacementKind = TEXT("hardness_only");
		ADinkPlaceholderActor* Other = SpawnPlacement(World, 527, 6, TEXT("slime_blue"), 651, TEXT("en-slimb"), Plane);
		First->SetActorLocation(FVector(1000, 0, 0));
		Second->SetActorLocation(FVector(90000, 0, 0));
		const TArray<FName> TagsBefore = First->Tags;
		const ECollisionEnabled::Type CardCollision = First->Card->GetCollisionEnabled();
		const FName CardProfile = First->Card->GetCollisionProfileName();
		const int32 ComponentsBefore = First->GetComponents().Num();
		UDinkCreatureSubsystem* Creatures = World->GetSubsystem<UDinkCreatureSubsystem>();
		Creatures->OnWorldBeginPlay(*World);
		FAssetCompilingManager::Get().FinishAllCompilation();
		const FString Label = FString::Printf(TEXT("dink.CreatureClassArt %d: "), Mode);
		if (Mode != 2)
		{
			// 1 needs a renderer (the tests run without one), 0 is off: headless runs keep the cards, as on master.
			TestEqual(Label + TEXT("no class row bound in a headless run"), Creatures->GetClassBindings().Num(), 0);
			TestNull(Label + TEXT("no body"), UDinkCreatureSubsystem::FindClassBody(First));
			TestFalse(Label + TEXT("card stays"), First->Card->bHiddenInGame);
			TestNotNull(Label + TEXT("the origin row still animates its pillbug"), OriginBound->FindComponentByClass<UDinkCreatureComponent>());
			continue;
		}
		TestEqual(Label + TEXT("two placements dressed"), Creatures->GetClassPlacementCount(), 2);
		for (ADinkPlaceholderActor* Actor : { First, Second })
		{
			UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(Actor);
			if (!TestNotNull(Label + TEXT("placement of the class has its creature"), Body)) continue;
			TestEqual(Label + TEXT("class"), Body->GetClassId(), FName(TEXT("pillbug")));
			TestTrue(Label + TEXT("the photoreal mesh on the 43-bone rig"), Body->GetSkeletalMeshAsset() && Body->GetSkeletalMeshAsset()->GetName() == TEXT("SK_Pillbug_Photoreal") && Body->GetSkeletalMeshAsset()->GetRefSkeleton().GetNum() == 43);
			TestTrue(Label + TEXT("the card's picture is hidden"), Actor->Card->bHiddenInGame);
			TestEqual(Label + TEXT("the body collides with nothing"), Body->GetCollisionEnabled(), ECollisionEnabled::NoCollision);
			TestFalse(Label + TEXT("the body generates no overlaps"), Body->GetGenerateOverlapEvents());
			TestEqual(Label + TEXT("the body stands on the placement"), Body->GetShownLocation(), Actor->GetActorLocation());
			TestEqual(Label + TEXT("standing: idle only"), Body->GetLayers().Num(), 1);
			TestEqual(Label + TEXT("the body ticks at the end of the frame, after the story has moved its actor"), int32(Body->PrimaryComponentTick.TickGroup), int32(TG_PostUpdateWork));
			TestEqual(Label + TEXT("role"), Body->GetRoleName(), FName(TEXT("walk")));
		}
		TestEqual(Label + TEXT("the picture's facing is kept until the sprite turns: 131 faces south-west"), UDinkCreatureSubsystem::FindClassBody(First)->GetShownYaw(), 135.f);
		TestEqual(Label + TEXT("133 faces south-east"), UDinkCreatureSubsystem::FindClassBody(Second)->GetShownYaw(), 45.f);
		// nothing gameplay reads has changed
		TestTrue(Label + TEXT("actor tags unchanged (no DinkCreature, no DinkAuthoredArt)"), First->Tags == TagsBefore);
		TestEqual(Label + TEXT("card collision unchanged"), First->Card->GetCollisionEnabled(), CardCollision);
		TestEqual(Label + TEXT("card collision profile unchanged"), First->Card->GetCollisionProfileName(), CardProfile);
		TestEqual(Label + TEXT("one component added, the body"), First->GetComponents().Num(), ComponentsBefore + 1);
		TestNull(Label + TEXT("no body boxes"), First->FindComponentByClass<UBoxComponent>());
		TestFalse(Label + TEXT("actor still visible"), First->IsHidden());
		// precedence and exclusions
		TestNull(Label + TEXT("the origin row keeps its pillbug"), UDinkCreatureSubsystem::FindClassBody(OriginBound));
		TestNotNull(Label + TEXT("which the origin layer animates"), OriginBound->FindComponentByClass<UDinkCreatureComponent>());
		TestTrue(Label + TEXT("with its own tag"), OriginBound->ActorHasTag(TEXT("DinkCreature")));
		TestNull(Label + TEXT("a hardness proxy gets no creature"), UDinkCreatureSubsystem::FindClassBody(Proxy));
		TestNull(Label + TEXT("another class keeps its card"), UDinkCreatureSubsystem::FindClassBody(Other));
		TestFalse(Label + TEXT("and its picture"), Other->Card->bHiddenInGame);
	}
	return true;
}

namespace
{
	/** Three pillbugs with the real en-pill script and pill brain on an empty synthetic screen (no hardness in the way), chasing Dink. */
	struct FPillbugScene
	{
		UGameInstance* GI = nullptr;
		UWorld* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* Game = nullptr;
		UDinkCreatureSubsystem* Creatures = nullptr;
		UDinkCreaturePresenter* Presenter = nullptr;
		ADinkScreenVolume* Room = nullptr;
		TArray<ADinkPlaceholderActor*> Bugs;
		TArray<int32> Handles;
		AActor* Dink = nullptr;
		static constexpr int32 Screen = 999;

		bool Start(UStaticMesh* Plane)
		{
			GI = NewObject<UGameInstance>(GEngine);
			GI->InitializeStandalone();
			World = GI->GetWorld();
			Story = GI->GetSubsystem<UDinkStorySubsystem>();
			Story->bRunScreenScripts = false; Story->bNewGamePending = false; Story->bInstantMode = true;
			Story->GetFacts()->SetFact(TEXT("life"), 100); Story->GetFacts()->SetFact(TEXT("lifemax"), 100);
			Story->GetFacts()->SetFact(TEXT("update_status"), 0); Story->GetFacts()->SetFact(TEXT("player_map"), Screen);
			D = Story->GetDirector();
			Game = Story->GetGameplay();
			Game->Adaptation.bEnabled = false;
			Game->SetRandomSeed(1997);
			Room = SpawnRoom(World, World->GetSubsystem<UDinkGreyboxSubsystem>(), Screen, 0);
			Dink = World->SpawnActor<AActor>();
			USceneComponent* Root = NewObject<USceneComponent>(Dink);
			Dink->SetRootComponent(Root); Root->RegisterComponent();
			Dink->SetActorLocation(Room->MapPixelToWorld(480, 300));
			D->GetDink().Actor = Dink; D->GetDink().Screen = Screen; D->GetDink().X = 500; D->GetDink().Y = 300;
			const FVector2D Starts[] = { FVector2D(126, 108), FVector2D(363, 186), FVector2D(233, 364) };
			for (int32 Index = 0; Index < 3; ++Index)
			{
				ADinkPlaceholderActor* Bug = SpawnPlacement(World, Screen, 4 + Index, TEXT("pillbug"), 131, TEXT("en-pill"), Plane);
				Bugs.Add(Bug);
				const int32 Handle = D->HandleForActor(Bug);
				Handles.Add(Handle);
				FDinkSprite* Sprite = D->FindSprite(Handle);
				Sprite->Screen = Screen; Sprite->X = Starts[Index].X; Sprite->Y = Starts[Index].Y;
				D->SyncActorToSprite(*Sprite);
				Story->StartProcedure(TEXT("en-pill"), TEXT("main"), Handle);
				Story->RunUntilIdle();
				D->FindSprite(Handle)->Props.Add(TEXT("target"), 1); // en-pill.c targets Dink on a coin toss; every bug chases here
			}
			Creatures = World->GetSubsystem<UDinkCreatureSubsystem>();
			Presenter = World->GetSubsystem<UDinkCreaturePresenter>();
			Creatures->OnWorldBeginPlay(*World);
			FAssetCompilingManager::Get().FinishAllCompilation();
			return Presenter != nullptr;
		}

		void Step(float Dt)
		{
			Story->Tick(Dt);
			if (UDinkCreatureSubsystem::IsClassArtAllowed())
			{
				Presenter->Present();
				for (ADinkPlaceholderActor* Bug : Bugs)
					if (UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(Bug)) Body->TickComponent(Dt, LEVELTICK_All, nullptr);
			}
		}

		/** Everything the simulation holds about the scene's sprites and the player. */
		FString Snapshot() const
		{
			FString Text = FString::Printf(TEXT("life %d exp %d | "), Story->GetFacts()->GetFact(TEXT("life")), Story->GetFacts()->GetFact(TEXT("exp")));
			TArray<int32> Keys;
			D->GetSprites().GetKeys(Keys);
			Keys.Sort();
			for (const int32 Key : Keys)
			{
				const FDinkSprite& S = *D->FindSprite(Key);
				TArray<FName> Names;
				S.Props.GetKeys(Names);
				Names.Sort([](const FName& A, const FName& B) { return A.LexicalLess(B); });
				Text += FString::Printf(TEXT("#%d a%d %.3f,%.3f d%d dmg%d "), Key, S.bActive ? 1 : 0, S.X, S.Y, S.Dir, S.Damage);
				for (const FName& Name : Names) Text += FString::Printf(TEXT("%s=%d "), *Name.ToString(), S.Props[Name]);
				if (const AActor* Actor = S.Actor.Get()) Text += FString::Printf(TEXT("@%s h%d c%d r%s "), *Actor->GetActorLocation().ToCompactString(), Actor->IsHidden() ? 1 : 0, Actor->GetActorEnableCollision() ? 1 : 0, *Actor->GetActorRotation().ToCompactString());
				Text += TEXT("| ");
			}
			return Text;
		}

		void Stop()
		{
			World->GetSubsystem<UDinkGreyboxSubsystem>()->UnregisterScreen(Room);
			GI->Shutdown();
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureClassFollowTest, "Dink.Art.CreatureClass.BodyFollowsSpriteLeavesCorpseAndDressesScriptSprites", DINK_TEST_FLAGS)
bool FDinkCreatureClassFollowTest::RunTest(const FString&)
{
	if (!ShippedPillbugRowReady(*this)) return true;
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	FClassArtMode Art(2);
	FPillbugScene Scene;
	if (!TestTrue(TEXT("scene starts"), Scene.Start(Plane))) return false;
	ON_SCOPE_EXIT { Scene.Stop(); };
	UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(Scene.Bugs[0]);
	if (!TestNotNull(TEXT("the placement has its creature"), Body)) return false;
	const FDinkSprite* Sprite = Scene.D->FindSprite(Scene.Handles[0]);
	TestEqual(TEXT("en-pill made it a pill brain"), Sprite->GetProp(TEXT("brain")), 9);

	// two seconds of the real brain at a 90 Hz render rate (frames with and without an engine step)
	const float Dt = 1.f / 90.f;
	double Path = 0.0, Shown = 0.0, MaxStep = 0.0, Time = 0.0, MaxLag = 0.0;
	int32 Standing = 0, Frames = 0;
	for (int32 Frame = 0; Frame < 180; ++Frame)
	{
		const FVector SpriteBefore = Scene.Bugs[0]->GetActorLocation(), BodyBefore = Body->GetShownLocation();
		Scene.Step(Dt);
		Time += Dt;
		if (Time < 0.5) continue;
		++Frames;
		Path += FVector::DistXY(SpriteBefore, Scene.Bugs[0]->GetActorLocation());
		const double BodyStep = FVector::DistXY(BodyBefore, Body->GetShownLocation());
		Shown += BodyStep;
		MaxStep = FMath::Max(MaxStep, BodyStep);
		MaxLag = FMath::Max(MaxLag, FVector::DistXY(Body->GetShownLocation(), Scene.Bugs[0]->GetActorLocation()));
		Standing += Body->GetCyclesPerSecond() <= 0.f;
	}
	const double SpriteSpeed = Path / (Frames * Dt), BodySpeed = Shown / (Frames * Dt);
	AddInfo(FString::Printf(TEXT("sprite %.1f cm/s, body %.1f cm/s, largest body step %.2f cm, largest lag %.1f cm, cadence %.2f cycles/s"), SpriteSpeed, BodySpeed, MaxStep, MaxLag, Body->GetCyclesPerSecond()));
	TestTrue(TEXT("the brain walks the sprite"), SpriteSpeed > 50.0);
	TestTrue(TEXT("the body covers the same ground as the sprite"), FMath::Abs(BodySpeed - SpriteSpeed) < SpriteSpeed * 0.05);
	TestTrue(TEXT("pixel steps are shown as continuous motion: no body step beyond 1.5x the mean"), MaxStep < 1.5 * SpriteSpeed * Dt + 0.01);
	TestTrue(TEXT("the body trails the sprite by about speed x smooth time, never more"), MaxLag < SpriteSpeed * 0.1 * 1.3 + 3.0);
	TestEqual(TEXT("a walking sprite never shows the standing pose alone"), Standing, 0);
	TestEqual(TEXT("role"), Body->GetRoleName(), FName(TEXT("walk")));
	TestTrue(TEXT("the cycle advances by distance over stride"), Body->GetCyclesPerSecond() > 0.f);
	float Weight = 0.f;
	for (const FDinkCreaturePoseLayer& Layer : Body->GetLayers()) Weight += Layer.Weight;
	TestTrue(TEXT("layer weights sum to one"), FMath::IsNearlyEqual(Weight, 1.f, 1e-3f));
	FQuat Facing;
	if (TestTrue(TEXT("the director knows the sprite's facing"), Scene.D->GetSpriteFacingRotation(*Sprite, Facing)))
		TestTrue(TEXT("the body faces the sprite's direction"), FMath::Abs(FRotator::NormalizeAxis(Body->GetShownYaw() - float(Facing.Rotator().Yaw))) < 1.f);
	TestEqual(TEXT("the body takes the sprite's size"), Body->GetSizePercent(), Sprite->GetProp(TEXT("size"), 100));
	TestEqual(TEXT("the sprite keeps its speed"), Sprite->GetProp(TEXT("speed")), 1);
	TestEqual(TEXT("the sprite keeps its walk base"), Sprite->GetProp(TEXT("base_walk")), 130);
	TestTrue(TEXT("the placeholder actor is not turned by the layer"), Scene.Bugs[0]->GetActorRotation().IsNearlyZero());

	// a kill by damage leaves the carcass where the body stood (add_kill_sprite), the actor goes as before
	const FVector Stood = Body->GetShownLocation();
	TestEqual(TEXT("no corpse while everything lives"), Scene.Creatures->GetCorpseCount(), 0);
	Scene.Game->HurtThing(Scene.Handles[0], 100);
	Scene.Game->ProcessDamage();
	Scene.Story->RunUntilIdle();
	TestFalse(TEXT("the simulation removed the sprite"), Scene.D->FindSprite(Scene.Handles[0])->bActive);
	TestTrue(TEXT("its actor is hidden, as without the layer"), Scene.Bugs[0]->IsHidden());
	Scene.Presenter->Present();
	TestEqual(TEXT("one carcass"), Scene.Creatures->GetCorpseCount(), 1);
	Scene.Presenter->Present();
	TestEqual(TEXT("and only one"), Scene.Creatures->GetCorpseCount(), 1);
	TestEqual(TEXT("its blood pool lies under it as a ground decal"), Scene.Creatures->GetCorpseDecalCount(), 1);
	UStaticMeshComponent* Carcass = nullptr;
	for (TActorIterator<AActor> It(Scene.World); It; ++It)
		if (UStaticMeshComponent* Found = It->FindComponentByTag<UStaticMeshComponent>(TEXT("DinkCreatureCorpse"))) Carcass = Found;
	if (TestNotNull(TEXT("the carcass exists in the world"), Carcass))
	{
		TestTrue(TEXT("it lies where the body stood"), FVector::DistXY(Carcass->GetComponentLocation(), Stood) < 1.0);
		TestTrue(TEXT("it is the burst pillbug"), Carcass->GetStaticMesh() && Carcass->GetStaticMesh()->GetName() == TEXT("SM_Pillbug_Corpse_PR"));
		TestEqual(TEXT("it collides with nothing"), Carcass->GetCollisionEnabled(), ECollisionEnabled::NoCollision);
		TestFalse(TEXT("the pool decal is not projected onto the carcass itself"), bool(Carcass->bReceivesDecals));
	}
	// a sprite a script removes leaves nothing (sp_active 0 is not a kill)
	Scene.D->DeactivateSprite(Scene.Handles[1], 0);
	Scene.Presenter->Present();
	TestEqual(TEXT("a removed sprite leaves no carcass"), Scene.Creatures->GetCorpseCount(), 1);
	// a pillbug without a death sequence leaves no carcass (s1-fmons.c gives no base_death: the original plays burst 164)
	Scene.D->FindSprite(Scene.Handles[2])->Props.Add(TEXT("base_death"), -1);
	Scene.Game->HurtThing(Scene.Handles[2], 100);
	Scene.Game->ProcessDamage();
	Scene.Story->RunUntilIdle();
	Scene.Presenter->Present();
	TestEqual(TEXT("no base_death, no carcass"), Scene.Creatures->GetCorpseCount(), 1);

	// a script-made pillbug gets the body, its greybox marker goes, and it stands on the ground under the lifted actor
	FDinkScriptInstance Caller; Caller.Id = 900001; Caller.Sprite = 1; Caller.Screen = FPillbugScene::Screen;
	Scene.D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> create_sprite 320 200 9 133 1"), { TEXT("cmd"), TEXT("src:1") }));
	Scene.D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> create_sprite 100 100 0 164 1"), { TEXT("cmd"), TEXT("src:2") }));
	Scene.Presenter->Present();
	int32 Made = 0, Effects = 0;
	for (const auto& Pair : Scene.D->GetSprites())
	{
		AActor* Actor = Pair.Value.Actor.Get();
		if (!Pair.Value.bSpawned || !Actor) continue;
		UDinkCreatureClassComponent* Spawned = UDinkCreatureSubsystem::FindClassBody(Actor);
		if (Pair.Value.GetProp(TEXT("pseq")) != 133)
		{
			++Effects;
			TestNull(TEXT("an effect sprite gets no creature"), Spawned);
			continue;
		}
		++Made;
		if (!TestNotNull(TEXT("the script-made pillbug has its creature"), Spawned)) continue;
		TestEqual(TEXT("facing of picture 133"), Spawned->GetShownYaw(), 45.f);
		TestTrue(TEXT("on the ground, 60 cm under the script actor"), FMath::IsNearlyEqual(Spawned->GetShownLocation().Z, Actor->GetActorLocation().Z - 60.0, 0.01));
		const ADinkScriptSpriteActor* Script = Cast<ADinkScriptSpriteActor>(Actor);
		TestTrue(TEXT("marker hidden"), Script && Script->Marker->bHiddenInGame);
	}
	TestEqual(TEXT("one script-made pillbug"), Made, 1);
	TestEqual(TEXT("one effect sprite"), Effects, 1);

	// leaving the screen drops the carcasses, as the original drops its corpse sprites
	Scene.Story->GetFacts()->SetFact(TEXT("player_map"), 998);
	Scene.Presenter->Present();
	TestEqual(TEXT("carcasses go with the screen"), Scene.Creatures->GetCorpseCount(), 0);
	TestEqual(TEXT("and their blood"), Scene.Creatures->GetCorpseDecalCount(), 0);
	TestEqual(TEXT("nothing followed on a screen without sprites"), Scene.Presenter->GetFollowedCount(), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureClassParityTest, "Dink.Art.CreatureClass.SimulationIdenticalWithAndWithoutTheLayer", DINK_TEST_FLAGS)
bool FDinkCreatureClassParityTest::RunTest(const FString&)
{
	if (!ShippedPillbugRowReady(*this)) return true;
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	// The same four seconds twice: cards (layer off), then creatures presented every frame. Every sprite property,
	// position, actor transform and the player's facts must match frame for frame.
	TArray<FString> Traces[2];
	int32 Bodies[2] = { 0, 0 };
	for (int32 Run = 0; Run < 2; ++Run)
	{
		FClassArtMode Art(Run == 0 ? 0 : 2);
		FPillbugScene Scene;
		if (!TestTrue(TEXT("scene starts"), Scene.Start(Plane))) return false;
		ON_SCOPE_EXIT { Scene.Stop(); };
		for (ADinkPlaceholderActor* Bug : Scene.Bugs) Bodies[Run] += UDinkCreatureSubsystem::FindClassBody(Bug) != nullptr;
		const float Dt = 1.f / 60.f;
		for (int32 Frame = 0; Frame < 240; ++Frame)
		{
			if (Frame == 60) { Scene.Game->HurtThing(Scene.Handles[0], 3); Scene.Game->ProcessDamage(); Scene.Story->RunUntilIdle(); }
			if (Frame == 120) { Scene.Game->HurtThing(Scene.Handles[1], 100); Scene.Game->ProcessDamage(); Scene.Story->RunUntilIdle(); }
			if (Frame == 150) Scene.D->DeactivateSprite(Scene.Handles[2], 0);
			if (Frame == 160)
			{
				FDinkScriptInstance Caller; Caller.Id = 900001; Caller.Sprite = 1; Caller.Screen = FPillbugScene::Screen;
				Scene.D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> create_sprite 320 200 9 133 1"), { TEXT("cmd"), TEXT("src:1") }));
			}
			Scene.Step(Dt);
			Traces[Run].Add(Scene.Snapshot());
		}
		if (Run == 1) TestEqual(TEXT("the kill left its carcass in the presented run"), Scene.Creatures->GetCorpseCount(), 1);
	}
	TestEqual(TEXT("layer off: cards"), Bodies[0], 0);
	TestEqual(TEXT("layer on: three creatures"), Bodies[1], 3);
	int32 Different = 0;
	for (int32 Frame = 0; Frame < Traces[0].Num(); ++Frame)
	{
		if (Traces[0][Frame] == Traces[1][Frame]) continue;
		if (++Different == 1) AddError(FString::Printf(TEXT("frame %d differs:\ncards    %s\ncreature %s"), Frame, *Traces[0][Frame], *Traces[1][Frame]));
	}
	TestEqual(TEXT("frames that differ"), Different, 0);
	TestTrue(TEXT("the trace is not empty and the sprites moved"), Traces[0].Num() == 240 && Traces[0][0] != Traces[0][239]);
	return true;
}
