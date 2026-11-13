#include "DinkTestHelpers.h"
#include "DinkHumanoidComponent.h"
#include "DinkArtSubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/StaticMeshComponent.h"
#include "Animation/BlendSpace.h"
#include "AssetCompilingManager.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

namespace DinkHumanoidPresentationTest
{
	struct FWorldFixture
	{
		UWorld* World = nullptr;
		FWorldFixture()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false);
			GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
		}
		~FWorldFixture()
		{
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHumanoidLocomotionTest, "Dink.Art.HumanoidPresentation.ActorOwnedLocomotion", DINK_TEST_FLAGS)
bool FDinkHumanoidLocomotionTest::RunTest(const FString& Parameters)
{
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
	UBlendSpace* Locomotion = LoadObject<UBlendSpace>(nullptr, TEXT("/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run.BS_Idle_Walk_Run"));
	if (!Mesh || !Locomotion)
	{
		AddWarning(TEXT("skipped: template locomotion content missing; run Scripts/copy_template_content.sh"));
		return true;
	}
	FAssetCompilingManager::Get().FinishAllCompilation();
	if (!TestTrue(TEXT("reference mesh and blend space share their skeleton"), Mesh->GetSkeleton() == Locomotion->GetSkeleton())) { return false; }
	DinkHumanoidPresentationTest::FWorldFixture E;
	AActor* Owner = E.World->SpawnActor<AActor>();
	USceneComponent* Root = NewObject<USceneComponent>(Owner, TEXT("ScriptOrigin"));
	Owner->SetRootComponent(Root);
	Root->RegisterComponent();
	UDinkHumanoidComponent* Human = NewObject<UDinkHumanoidComponent>(Owner, TEXT("AuthoredHumanoid"));
	Human->SetupAttachment(Root);
	Human->RegisterComponent();
	Human->Configure(Mesh, Locomotion);
	TestNull(TEXT("script actor is deliberately not an APawn"), Cast<APawn>(Owner));
	TestEqual(TEXT("humanoid uses single-node animation on an actor"), Human->GetAnimationMode(), EAnimationMode::AnimationSingleNode);
	if (!TestNotNull(TEXT("single-node animation instance exists without pawn ownership"), Human->GetSingleNodeInstance())) { return false; }
	TestTrue(TEXT("the configured blend space is actually playing"), Human->GetSingleNodeInstance()->GetAnimationAsset() == Locomotion && Human->GetSingleNodeInstance()->IsPlaying());
	int32 SpeedAxis = INDEX_NONE;
	for (int32 Axis = 0; Axis < 3; ++Axis)
	{
		if (Locomotion->GetBlendParameter(Axis).DisplayName.Contains(TEXT("Speed"))) { SpeedAxis = Axis; }
	}
	if (!TestTrue(TEXT("reference blend space has a named Speed axis"), SpeedAxis != INDEX_NONE)) { return false; }
	TestTrue(TEXT("test speed lies inside the reference blend-space range"), Locomotion->GetBlendParameter(SpeedAxis).Max >= 200.f);
	auto CheckInput = [this, Human, SpeedAxis](float Expected, const TCHAR* Description)
	{
		TestTrue(FString(Description) + TEXT(": actual world displacement measured"), FMath::IsNearlyEqual(Human->GetLocomotionSpeed(), Expected, .01f));
		UAnimSingleNodeInstance* Animation = Human->GetSingleNodeInstance();
		if (!TestNotNull(TEXT("animation instance remains present"), Animation)) { return; }
		FVector Position, Filtered;
		Animation->GetBlendSpaceState(Position, Filtered);
		TestTrue(FString(Description) + TEXT(": actual animation Speed input"), FMath::IsNearlyEqual(Position[SpeedAxis], double(Expected), .01));
		for (int32 Axis = 0; Axis < 3; ++Axis)
		{
			if (Axis != SpeedAxis) { TestTrue(TEXT("movement speed never drives the Direction or unused axis"), FMath::IsNearlyZero(Position[Axis])); }
		}
	};
	Human->TickComponent(.25f, LEVELTICK_All, nullptr);
	CheckInput(0, TEXT("first sample starts idle"));
	Owner->SetActorLocation(FVector(30,40,0)); // 50 cm in a quarter second: a normal 2 m/s walk
	Human->TickComponent(.25f, LEVELTICK_All, nullptr);
	CheckInput(200, TEXT("scripted actor movement animates walking"));
	Human->TickComponent(.25f, LEVELTICK_All, nullptr);
	CheckInput(0, TEXT("standing returns to idle"));
	Owner->SetActorLocation(FVector(1030,40,0), false, nullptr, ETeleportType::TeleportPhysics);
	Human->TickComponent(.1f, LEVELTICK_All, nullptr);
	CheckInput(0, TEXT("teleport is not a burst of running"));
	Owner->SetActorLocation(FVector(1040,40,0));
	Human->TickComponent(.1f, LEVELTICK_All, nullptr);
	CheckInput(100, TEXT("ordinary locomotion resumes immediately after teleport"));
	TestEqual(TEXT("ordinary mother-speed movement retains natural rate"),Human->GetSingleNodeInstance()->GetPlayRate(),1.f);
	// Sustain actual fast motion briefly before checking the observed gait/cadence.
    for (int32 Frame=0;Frame<5;++Frame) { Owner->AddActorWorldOffset(FVector(100,0,0)); Human->TickComponent(.05f,LEVELTICK_All,nullptr); }
	const float RunMax=Locomotion->GetBlendParameter(SpeedAxis).Max;
	TestTrue(TEXT("fixture exceeds maximum authored gait"),RunMax<2000.f);
	TestTrue(TEXT("fast scripted actor cadence follows measured motion above blendspace maximum"),FMath::IsNearlyEqual(Human->GetSingleNodeInstance()->GetPlayRate(),FMath::Clamp(2000.f/RunMax,1.f,3.f),.01f));
	FVector FastPosition,FastFiltered; Human->GetSingleNodeInstance()->GetBlendSpaceState(FastPosition,FastFiltered);
	TestTrue(TEXT("high-speed gait input stays at authored maximum"),FMath::IsNearlyEqual(FastPosition[SpeedAxis],double(RunMax),.01));
	Owner->AddActorWorldOffset(FVector(1000,0,0)); Human->TickComponent(.05f,LEVELTICK_All,nullptr);
	TestEqual(TEXT("teleport restores natural playback rate"),Human->GetSingleNodeInstance()->GetPlayRate(),1.f);
	Human->Configure(Mesh, Locomotion);
	Owner->SetActorLocation(FVector(1060,40,0));
	Human->TickComponent(.1f, LEVELTICK_All, nullptr);
	CheckInput(0, TEXT("reconfiguration resets the motion sample"));
	TestEqual(TEXT("reconfiguration restores natural playback rate"),Human->GetSingleNodeInstance()->GetPlayRate(),1.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHumanoidFacingTest, "Dink.Art.HumanoidPresentation.BrainTurnsHumanoidButNotFurniture", DINK_TEST_FLAGS)
bool FDinkHumanoidFacingTest::RunTest(const FString& Parameters)
{
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	UDinkGreyboxSubsystem* Greybox = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
	if (!TestNotNull(TEXT("game world"), World) || !TestNotNull(TEXT("story"), Story) || !TestNotNull(TEXT("screen subsystem"), Greybox)) { return false; }
	Story->bRunScreenScripts = false;
	ADinkScreenVolume* Screen = World->SpawnActor<ADinkScreenVolume>();
	Screen->ScreenNumber = 1;
	Screen->Corners.NW = FVector2D(0,0);
	Screen->Corners.NE = FVector2D(60,0);
	Screen->Corners.SW = FVector2D(0,40);
	Screen->Corners.SE = FVector2D(60,40);
	Greybox->RegisterScreen(Screen);
	UDinkDirector* D = Story->GetDirector();
	ADinkPlaceholderActor* NPC = World->SpawnActor<ADinkPlaceholderActor>();
	NPC->Origin->OriginId = FDinkOriginId(1,26);
	NPC->Origin->ScriptName = TEXT("s1-h1-m");
	NPC->Brain = 16;
	NPC->Tags.Add(TEXT("DinkAuthoredArt"));
	NPC->Tags.Add(TEXT("DinkHumanoid"));
	const int32 NPCHandle = D->HandleForActor(NPC);
	ADinkPlaceholderActor* Furniture = World->SpawnActor<ADinkPlaceholderActor>();
	Furniture->Origin->OriginId = FDinkOriginId(1,22);
	Furniture->Origin->ScriptName = TEXT("s1-h1-4");
	Furniture->Tags.Add(TEXT("DinkAuthoredArt"));
	Furniture->GetRootComponent()->SetMobility(EComponentMobility::Movable);
	Furniture->Card->SetMobility(EComponentMobility::Movable);
	Furniture->SetActorRotation(FRotator(0,23,0));
	const int32 FurnitureHandle = D->HandleForActor(Furniture);
	D->SpriteProperty(nullptr, TEXT("dir"), NPCHandle, 8);
	TestTrue(TEXT("original north-facing brain direction turns the humanoid actor"), FVector::DotProduct(NPC->GetActorForwardVector(), FVector(0,-1,0)) > .999);
	D->SpriteProperty(nullptr, TEXT("dir"), FurnitureHandle, 8);
	TestTrue(TEXT("the same sprite property never rotates authored furniture"), FMath::IsNearlyEqual(Furniture->GetActorRotation().Yaw, 23.0, .01));
	D->SpriteProperty(nullptr, TEXT("dir"), NPCHandle, 6);
	TestTrue(TEXT("another original brain direction turns the humanoid east"), FVector::DotProduct(NPC->GetActorForwardVector(), FVector(1,0,0)) > .999);
	TestTrue(TEXT("turning leaves the original NPC script attached"), D->FindSprite(NPCHandle)->Script == TEXT("s1-h1-m"));
	NPC->SetActorLocation(Screen->MapPixelToWorld(301,150));
	FDinkSprite* Moving=D->FindSprite(NPCHandle); Moving->X=321; Moving->Y=150; Moving->Screen=1;
	Moving->Props.Add(TEXT("brain"),0); Moving->Props.Add(TEXT("follow"),1); Moving->Props.Add(TEXT("speed"),1); Moving->Props.Add(TEXT("base_walk"),-1);
	D->GetDink().Screen=1; D->GetDink().X=321; D->GetDink().Y=300;
	Story->GetGameplay()->ThinkSprite(NPCHandle,1000.);
	TestTrue(TEXT("normal accepted brain movement commits humanoid facing without sp_dir"),Moving->Y>150. && FVector::DotProduct(NPC->GetActorForwardVector(),FVector(0,1,0))>.999);

	Greybox->UnregisterScreen(Screen);
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPlayerArtAnimationTest, "Dink.Art.HumanoidPresentation.OptionalPlayerMeshKeepsAnimationAndCapsule", DINK_TEST_FLAGS)
bool FDinkPlayerArtAnimationTest::RunTest(const FString& Parameters)
{
	USkeletalMesh* Reference = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
	UClass* AnimClass = LoadClass<UAnimInstance>(nullptr, TEXT("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed_C"));
	if (!Reference || !AnimClass)
	{
		AddWarning(TEXT("skipped: template player content missing; run Scripts/copy_template_content.sh"));
		return true;
	}
	FAssetCompilingManager::Get().FinishAllCompilation();
	DinkHumanoidPresentationTest::FWorldFixture E;
	ADinkGreyboxCharacter* Player = E.World->SpawnActor<ADinkGreyboxCharacter>();
	USkeletalMeshComponent* Body = Player->GetMesh();
	Body->SetSkeletalMesh(Reference);
	Body->SetAnimInstanceClass(AnimClass);
	UAnimInstance* Animation = Body->GetAnimInstance();
	if (!TestNotNull(TEXT("reference player's animation instance exists"), Animation)) { return false; }
	const FTransform Transform = Body->GetRelativeTransform();
	const float Radius = Player->GetCapsuleComponent()->GetScaledCapsuleRadius();
	const float HalfHeight = Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	UDinkArtSubsystem* Art = E.World->GetSubsystem<UDinkArtSubsystem>();
	IConsoleVariable* Enabled = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));
	if (!TestNotNull(TEXT("art subsystem"), Art) || !TestNotNull(TEXT("optional art switch"), Enabled)) { return false; }
	const int32 OldEnabled = Enabled->GetInt();
	ON_SCOPE_EXIT { Enabled->SetWithCurrentPriority(OldEnabled); };
	Enabled->SetWithCurrentPriority(0);
	TestFalse(TEXT("disabled optional art leaves the template as a playable fallback"), Art->ApplyPlayer(*Body));
	TestEqual(TEXT("fallback keeps the reference mesh"), Body->GetSkeletalMeshAsset(), Reference);
	TestEqual(TEXT("fallback keeps the live animation instance"), Body->GetAnimInstance(), Animation);
	Enabled->SetWithCurrentPriority(1);
	FString Text;
	TSharedPtr<FJsonObject> Manifest;
	const TSharedPtr<FJsonObject>* Row = nullptr;
	FString Path;
	const bool bHasPlayer = FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/characters.json"))) &&
		FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) && Manifest &&
		Manifest->TryGetObjectField(TEXT("player"), Row) && Row && (*Row)->TryGetStringField(TEXT("mesh"), Path);
	const bool bApplied = Art->ApplyPlayer(*Body);
	TestEqual(TEXT("an optional player mapping applies exactly when installed"), bApplied, bHasPlayer);
	if (bHasPlayer)
	{
		USkeletalMesh* Expected = LoadObject<USkeletalMesh>(nullptr, *Path);
		TestNotNull(TEXT("authored player mesh loads"), Expected);
		TestEqual(TEXT("player receives the authored mesh"), Body->GetSkeletalMeshAsset(), Expected);
	}
	else
	{
		TestEqual(TEXT("missing optional mapping preserves the reference mesh"), Body->GetSkeletalMeshAsset(), Reference);
	}
	if (bApplied && !Art->GetAnimationLibrary().IsEmpty())
	{
		// Animation pass imported: the player runs the native body animation with the hero clip set.
		const UDinkBodyAnimInstance* Native = Cast<UDinkBodyAnimInstance>(Body->GetAnimInstance());
		TestTrue(TEXT("the authored player runs the native body animation"), Native && Native->IsConfigured() && Native->HasClip(TEXT("Fist_Jab")));
	}
	else
	{
		TestEqual(TEXT("mesh swap retains the current animation instance"), Body->GetAnimInstance(), Animation);
		TestEqual(TEXT("mesh swap retains the existing animation blueprint class"), Body->GetAnimClass(), AnimClass);
	}
	TestEqual(TEXT("mesh swap retains blueprint animation mode"), Body->GetAnimationMode(), EAnimationMode::AnimationBlueprint);
	TestTrue(TEXT("authored player stays in the existing capsule/mesh coordinate frame"), Body->GetRelativeTransform().Equals(Transform, .001));
	TestEqual(TEXT("authored player never changes the movement capsule radius"), Player->GetCapsuleComponent()->GetScaledCapsuleRadius(), Radius);
	TestEqual(TEXT("authored player never changes the movement capsule height"), Player->GetCapsuleComponent()->GetScaledCapsuleHalfHeight(), HalfHeight);
	return true;
}
