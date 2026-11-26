// Takeover A4 (25 Nov 2026): the old man (class npc_old_man, picture 231-239) stands bent over his cane in AN_Stoop_Stand, an
// idle clip only; his walk and jog are the shared motion capture, so he straightened up whenever he walked. A class locomotion
// set may carry a `posture` (DinkCreatureClass.h): the clip's spine, neck and head away from the reference pose, laid over the
// gaits in their share. This proves the row and dumps the pose (Saved/Animation/oldman_walk_posture.txt). Presentation only.
#include "DinkTestHelpers.h"
#include "DinkCreatureClass.h"
#include "DinkCreatureClassComponent.h"
#include "DinkCreatureSubsystem.h"
#include "AssetCompilingManager.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace DinkCreaturePostureTest
{
	TSharedPtr<FJsonObject> Parse(const FString& Text)
	{
		TSharedPtr<FJsonObject> Object;
		FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Object);
		return Object;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreaturePostureRowTest, "Dink.Art.CreatureClass.WalkPostureRows", DINK_TEST_FLAGS)
bool FDinkCreaturePostureRowTest::RunTest(const FString&)
{
	using namespace DinkCreaturePostureTest;
	const TSharedPtr<FJsonObject> Manifest = Parse(TEXT(R"({"schema":"dink-creatures/1","classes":[
		{"class":"stooped","mesh":"/Game/A/SK_A.SK_A","locomotion":{"idle":"/Game/A/AN_Stoop.AN_Stoop","gaits":[{"clip":"/Game/A/AN_Walk.AN_Walk","speed_cm_s":200}],
		 "posture":{"weight":0.5}},"roles":{"walk":{"sequences":[231],"locomotion":true}}},
		{"class":"own","mesh":"/Game/A/SK_A.SK_A","locomotion":{"idle":"/Game/A/AN_I.AN_I","gaits":[{"clip":"/Game/A/AN_Walk.AN_Walk","speed_cm_s":200}],
		 "posture":{"clip":"/Game/A/AN_Bent.AN_Bent","bones":["spine_03","head"],"weight":4}},"roles":{"walk":{"sequences":[241],"locomotion":true}}},
		{"class":"plain","mesh":"/Game/A/SK_A.SK_A","locomotion":{"idle":"/Game/A/AN_I.AN_I","gaits":[{"clip":"/Game/A/AN_Walk.AN_Walk","speed_cm_s":200}]},
		 "roles":{"walk":{"sequences":[251],"locomotion":true}}},
		{"class":"badclip","mesh":"/Game/A/SK_A.SK_A","locomotion":{"idle":"/Game/A/AN_I.AN_I","gaits":[{"clip":"/Game/A/AN_Walk.AN_Walk","speed_cm_s":200}],
		 "posture":{"clip":"AN_Bent"}},"roles":{"walk":{"sequences":[261],"locomotion":true}}}
	]})"));
	if (!TestTrue(TEXT("manifest parses"), Manifest.IsValid())) return false;
	TArray<FDinkCreatureClassBinding> Rows;
	TArray<FString> Problems;
	DinkCreatureClass::ParseBindings(*Manifest, Rows, &Problems);
	auto Find = [&](const TCHAR* Id) { return Rows.FindByPredicate([Id](const FDinkCreatureClassBinding& B) { return B.ClassId == FName(Id); }); };
	const FDinkCreatureClassBinding* Stooped = Find(TEXT("stooped"));
	const FDinkCreatureClassBinding* Own = Find(TEXT("own"));
	const FDinkCreatureClassBinding* Plain = Find(TEXT("plain"));
	if (!TestNotNull(TEXT("stooped row"), Stooped) || !TestNotNull(TEXT("own row"), Own) || !TestNotNull(TEXT("plain row"), Plain)) return false;
	TestEqual(TEXT("posture without a clip is the idle"), Stooped->Locomotion.PostureClip, FString(TEXT("/Game/A/AN_Stoop.AN_Stoop")));
	TestEqual(TEXT("its weight"), Stooped->Locomotion.PostureWeight, .5f);
	TestEqual(TEXT("no bones named: the default chain"), Stooped->Locomotion.PostureBones.Num(), 0);
	TestEqual(TEXT("a clip of its own"), Own->Locomotion.PostureClip, FString(TEXT("/Game/A/AN_Bent.AN_Bent")));
	TestEqual(TEXT("weight clamped to 1"), Own->Locomotion.PostureWeight, 1.f);
	TestTrue(TEXT("named bones"), Own->Locomotion.PostureBones.Num() == 2 && Own->Locomotion.PostureBones[1] == FName(TEXT("head")));
	TestTrue(TEXT("a set without posture has none"), Plain->Locomotion.PostureClip.IsEmpty() && Plain->Locomotion.PostureWeight == 0.f);
	TestNull(TEXT("a posture clip that is no /Game/ path refuses the row"), Find(TEXT("badclip")));

	FString Text;
	TArray<FDinkCreatureClassBinding> Shipped;
	if (TestTrue(TEXT("creatures.json"), FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/creatures.json")))))
		DinkCreatureClass::ParseBindings(*Parse(Text), Shipped);
	const FDinkCreatureClassBinding* OldMan = Shipped.FindByPredicate([](const FDinkCreatureClassBinding& B) { return B.ClassId == FName(TEXT("npc_old_man")); });
	if (TestNotNull(TEXT("npc_old_man row"), OldMan))
		TestTrue(TEXT("the old man walks with his stoop (AN_Stoop_Stand, weight 1)"), OldMan->Locomotion.PostureClip.EndsWith(TEXT("AN_Stoop_Stand.AN_Stoop_Stand")) &&
			OldMan->Locomotion.PostureWeight == 1.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreaturePostureOldManTest, "Dink.Art.CreatureClass.OldManKeepsHisStoopWalking", DINK_TEST_FLAGS)
bool FDinkCreaturePostureOldManTest::RunTest(const FString&)
{
	IConsoleVariable* ClassArt = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.CreatureClassArt"));
	IConsoleVariable* ArtOn = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));
	IConsoleVariable* Posture = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.CreatureClass.WalkPosture"));
	if (!TestNotNull(TEXT("dink.CreatureClass.WalkPosture registered"), Posture)) return false;
	const int32 ClassBefore = ClassArt ? ClassArt->GetInt() : 1, ArtBefore = ArtOn ? ArtOn->GetInt() : 1, PostureBefore = Posture->GetInt();
	if (ClassArt) ClassArt->SetWithCurrentPriority(2);
	if (ArtOn) ArtOn->SetWithCurrentPriority(1);
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	ON_SCOPE_EXIT
	{
		GI->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false);
		if (ClassArt) ClassArt->SetWithCurrentPriority(ClassBefore);
		if (ArtOn) ArtOn->SetWithCurrentPriority(ArtBefore);
		Posture->SetWithCurrentPriority(PostureBefore);
	};
	UDinkCreatureSubsystem* Creatures = World->GetSubsystem<UDinkCreatureSubsystem>();
	if (!TestNotNull(TEXT("creature subsystem"), Creatures)) return false;
	Creatures->OnWorldBeginPlay(*World);
	FAssetCompilingManager::Get().FinishAllCompilation();
	AActor* Actor = World->SpawnActor<AActor>();
	USceneComponent* Root = NewObject<USceneComponent>(Actor);
	Actor->SetRootComponent(Root);
	Root->RegisterComponent();
	DinkCreatureClass::FSpriteView View;
	View.PSeq = 231;
	UDinkCreatureClassComponent* Body = Creatures->PresentScriptSprite(Actor, View, 0.f, 0.f, 100);
	if (!Body)
	{
		AddWarning(TEXT("skipped: the old man's figure is not imported in this checkout (npc_old_man did not dress picture 231)"));
		return true;
	}
	TestEqual(TEXT("class"), Body->GetClassId(), FName(TEXT("npc_old_man")));
	Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	const float Dt = 1.f / 60.f;
	struct FShape { float HeadOverPelvis = 0.f, HeadAhead = 0.f, PostureWeight = 0.f; };
	auto Run = [&](float SpeedCm, int32 Frames, int32 Seq)
	{
		FDinkCreatureSpriteState State;
		State.Seq = Seq;
		State.PSeq = 231;
		State.PFrame = 1;
		State.Dir = 3;
		FShape Sum;
		int32 N = 0;
		for (int32 F = 0; F < Frames; ++F)
		{
			Actor->SetActorLocation(Actor->GetActorLocation() + FVector(SpeedCm * Dt, 0.0, 0.0));
			Body->ApplySpriteState(State);
			Body->Present(Dt);
			Body->TickAnimation(Dt, false);
			Body->RefreshBoneTransforms();
			if (F < Frames / 2) continue; // settled: the second half of the run
			const FVector Head = Body->GetBoneLocation(TEXT("head")), Pelvis = Body->GetBoneLocation(TEXT("pelvis"));
			const FVector Facing = Body->GetComponentRotation().RotateVector(FVector(0.0, 1.0, 0.0)); // the figures face +Y (yaw -90)
			Sum.HeadOverPelvis += float(Head.Z - Pelvis.Z);
			Sum.HeadAhead += float(FVector::DotProduct(FVector(Head - Pelvis) * FVector(1, 1, 0), Facing.GetSafeNormal2D()));
			if (const UDinkCreatureAnimInstance* A = Cast<UDinkCreatureAnimInstance>(Body->GetAnimInstance())) Sum.PostureWeight += A->GetPosture().Weight;
			++N;
		}
		Sum.HeadOverPelvis /= FMath::Max(N, 1); Sum.HeadAhead /= FMath::Max(N, 1); Sum.PostureWeight /= FMath::Max(N, 1);
		return Sum;
	};
	Posture->SetWithCurrentPriority(1);
	const FShape Stand = Run(0.f, 120, 0);
	const FShape Walk = Run(180.f, 240, 233);
	Posture->SetWithCurrentPriority(0);
	const FShape Straight = Run(180.f, 240, 233);
	Posture->SetWithCurrentPriority(1);
	const FString Dump = FString::Printf(TEXT("old man (npc_old_man), world cm, mean over the settled half of each run\n")
		TEXT("case                         head over pelvis   head ahead of pelvis   posture weight\n")
		TEXT("standing (AN_Stoop_Stand)    %8.1f           %8.1f               %5.2f\n")
		TEXT("walking 180 cm/s, posture    %8.1f           %8.1f               %5.2f\n")
		TEXT("walking 180 cm/s, without    %8.1f           %8.1f               %5.2f\n"),
		Stand.HeadOverPelvis, Stand.HeadAhead, Stand.PostureWeight, Walk.HeadOverPelvis, Walk.HeadAhead, Walk.PostureWeight,
		Straight.HeadOverPelvis, Straight.HeadAhead, Straight.PostureWeight);
	FFileHelper::SaveStringToFile(Dump, *(FPaths::ProjectSavedDir() / TEXT("Animation/oldman_walk_posture.txt")));
	AddInfo(Dump);
	TestTrue(TEXT("standing: no walking posture (the idle holds the stoop)"), Stand.PostureWeight < .05f);
	TestTrue(TEXT("walking: the posture is laid over the gait, in the gaits' share (at 180 cm/s the idle keeps a quarter)"), Walk.PostureWeight > .5f);
	TestTrue(TEXT("without the posture the walk straightens him (the 23 Nov finding)"), Straight.HeadOverPelvis - Stand.HeadOverPelvis > 4.f);
	TestTrue(TEXT("with it the head stays down: at least 4 cm lower than the straight walk"), Straight.HeadOverPelvis - Walk.HeadOverPelvis > 4.f);
	TestTrue(TEXT("and forward of the pelvis as he stands"), Walk.HeadAhead > Straight.HeadAhead + 3.f);
	return true;
}
