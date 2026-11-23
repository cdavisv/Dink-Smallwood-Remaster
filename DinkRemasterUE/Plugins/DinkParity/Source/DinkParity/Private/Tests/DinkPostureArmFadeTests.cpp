// A102 (23 Nov 2026): the posture's W (upper arms brought in towards the trunk, animation_natural.json posture.<set>[3])
// gives way while an action clip plays and while the body runs, so W can be raised for the idle and the walk without
// laying both hands on the belly in the jog and the wind-ups. Presentation only: nothing here touches gameplay.
#include "DinkTestHelpers.h"
#include "DinkArtSubsystem.h"
#include "DinkBodyAnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPostureArmFadeRuleTest, "Dink.Animation.Posture.ArmFadeRule", DINK_TEST_FLAGS)
bool FDinkPostureArmFadeRuleTest::RunTest(const FString&)
{
	const FVector2f Fade(UDinkBodyAnimInstance::DefaultArmFadeAction, UDinkBodyAnimInstance::DefaultArmFadeRun);
	TestEqual(TEXT("standing and walking keep W"), UDinkBodyAnimInstance::ArmPostureScale(0.f, 0.f, Fade), 1.f);
	TestTrue(TEXT("a full action takes W away"), FMath::IsNearlyZero(UDinkBodyAnimInstance::ArmPostureScale(1.f, 0.f, Fade)));
	TestTrue(TEXT("a full run keeps 0.3 of W"), FMath::IsNearlyEqual(UDinkBodyAnimInstance::ArmPostureScale(0.f, 1.f, Fade), .3f, 1.e-5f));
	TestTrue(TEXT("half a run keeps 0.65"), FMath::IsNearlyEqual(UDinkBodyAnimInstance::ArmPostureScale(0.f, .5f, Fade), .65f, 1.e-5f));
	TestTrue(TEXT("half an action while running"), FMath::IsNearlyEqual(UDinkBodyAnimInstance::ArmPostureScale(.5f, 1.f, Fade), .15f, 1.e-5f));
	TestEqual(TEXT("fade [0, 0] keeps W in every state"), UDinkBodyAnimInstance::ArmPostureScale(1.f, 1.f, FVector2f(0.f, 0.f)), 1.f);
	TestTrue(TEXT("weights outside 0..1 are clamped"), FMath::IsNearlyEqual(UDinkBodyAnimInstance::ArmPostureScale(3.f, -2.f, Fade), 0.f));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPostureArmFadeEngineTest, "Dink.Animation.Posture.ArmFadeInEngine", DINK_TEST_FLAGS)
bool FDinkPostureArmFadeEngineTest::RunTest(const FString&)
{
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
	UDinkArtSubsystem* Art = World->GetSubsystem<UDinkArtSubsystem>();
	USkeletalMesh* Hero = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Hero/Refinements/SK_Dink_Hands.SK_Dink_Hands"));
	if (!TestNotNull(TEXT("art subsystem"), Art) || !TestNotNull(TEXT("hero mesh"), Hero) || Art->GetAnimationLibrary().IsEmpty())
		return false;
	// The data hook: posture.<set>.arm_fade, else the default.
	const FVector2f HeroFade = Art->GetAnimationArmFade(TEXT("Hero"));
	TestTrue(TEXT("hero arm fade in 0..1"), HeroFade.X >= 0.f && HeroFade.X <= 1.f && HeroFade.Y >= 0.f && HeroFade.Y <= 1.f);
	TestEqual(TEXT("a set without a row takes the default"), Art->GetAnimationArmFade(TEXT("NoSuchSet")),
		FVector2f(UDinkBodyAnimInstance::DefaultArmFadeAction, UDinkBodyAnimInstance::DefaultArmFadeRun));

	AActor* Stage = World->SpawnActor<AActor>();
	USkeletalMeshComponent* Mesh = NewObject<USkeletalMeshComponent>(Stage);
	Stage->SetRootComponent(Mesh);
	Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Mesh->SetSkeletalMesh(Hero);
	Mesh->RegisterComponent();
	Mesh->SetComponentTickEnabled(false);
	Mesh->SetAnimInstanceClass(UDinkBodyAnimInstance::StaticClass());
	UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(Mesh->GetAnimInstance());
	if (!TestTrue(TEXT("hero clip set"), Body && Body->Configure(Art->GetAnimationLibrary(), TEXT("Hero")))) return false;
	const float Dt = 1.f / 60.f, W = 10.f;
	Body->SetPosture(FVector4f(0.f, 0.f, 0.f, W));
	Body->SetArmFade(FVector2f(UDinkBodyAnimInstance::DefaultArmFadeAction, UDinkBodyAnimInstance::DefaultArmFadeRun));
	auto Run = [&](float Speed, int32 Frames)
	{
		for (int32 I = 0; I < Frames; ++I)
		{
			Mesh->SetWorldLocation(Mesh->GetComponentLocation() + FVector(0, Speed * Dt, 0));
			Body->SetMotion(Speed, false, 0.f);
			Mesh->TickAnimation(Dt, false);
			Mesh->RefreshBoneTransforms();
		}
		return Body->GetFrame().Posture.W;
	};
	const int32 Arm = Hero->GetRefSkeleton().FindBoneIndex(TEXT("upperarm_l"));
	TestTrue(TEXT("standing: W whole"), FMath::IsNearlyEqual(Run(0.f, 90), W, .01f));
	const FQuat ArmIdle = Mesh->GetBoneTransform(Arm).GetRotation();
	TestTrue(TEXT("walking at 150 cm/s: W whole (no run gait)"), FMath::IsNearlyEqual(Run(150.f, 120), W, .01f));
	const float Jog = Run(600.f, 180);
	AddInfo(FString::Printf(TEXT("W at the jog %.2f (scale %.3f)"), Jog, Body->GetArmPostureScale()));
	TestTrue(TEXT("jogging at 600 cm/s: about 0.3 of W"), Jog > .25f * W && Jog < .45f * W);
	TestTrue(TEXT("back to a stand: W whole again"), FMath::IsNearlyEqual(Run(0.f, 240), W, .05f));
	// An action clip (the landing) takes W away while it plays at full weight.
	if (TestTrue(TEXT("Land clip"), Body->PlayAction(TEXT("Land"), false, 1.f, .05f, .2f)))
	{
		float Least = W;
		for (int32 I = 0; I < 20 && Body->IsActionActive(); ++I) Least = FMath::Min(Least, Run(0.f, 1));
		TestTrue(TEXT("during the action W gives way"), Least < .2f * W);
		Run(0.f, 120);
		TestTrue(TEXT("after the action W is whole"), FMath::IsNearlyEqual(Body->GetFrame().Posture.W, W, .01f));
	}
	// [0, 0] keeps the old behaviour: W in every state.
	Body->SetArmFade(FVector2f(0.f, 0.f));
	TestTrue(TEXT("fade off: the jog keeps W"), FMath::IsNearlyEqual(Run(600.f, 180), W, .01f));
	// W itself moves the upper arm (a sanity check that the posture is applied at all).
	Body->SetPosture(FVector4f(0.f, 0.f, 0.f, 0.f));
	Run(0.f, 240);
	const FQuat ArmNoW = Mesh->GetBoneTransform(Arm).GetRotation();
	TestTrue(TEXT("W turns the upper arm"), ArmIdle.AngularDistance(ArmNoW) > FMath::DegreesToRadians(3.f));
	return true;
}
