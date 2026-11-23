// The hero's mannerism layer is gated on its clips (PR #218 delivers them): without Posture_Timid and Posture_Confident in
// the animation library nothing changes; with them the additive posture, the timid gait layer and the run arms are handed
// to the evaluation, and the posture row keeps only W (A102), the stoop being the clips'. Presentation only.
#include "DinkTestHelpers.h"
#include "DinkArtSubsystem.h"
#include "DinkBodyAnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHeroMannerismLayerTest, "Dink.Animation.HeroMannerismLayerGatedOnClips", DINK_TEST_FLAGS)
bool FDinkHeroMannerismLayerTest::RunTest(const FString&)
{
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
	UDinkArtSubsystem* Art = World->GetSubsystem<UDinkArtSubsystem>();
	USkeletalMesh* Hero = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Hero/Refinements/SK_Dink_Hands.SK_Dink_Hands"));
	if (!TestNotNull(TEXT("art subsystem"), Art) || !TestNotNull(TEXT("hero mesh"), Hero) || Art->GetAnimationLibrary().IsEmpty()) return false;
	const TMap<FName, FDinkBodyClip>& Library = Art->GetAnimationLibrary();
	const bool bClips = Library.Contains(TEXT("Posture_Timid")) && Library.Contains(TEXT("Posture_Confident"));
	AddInfo(FString::Printf(TEXT("mannerism clips in the library: %s"), bClips ? TEXT("yes") : TEXT("no (PR #218 not imported)")));

	AActor* Stage = World->SpawnActor<AActor>();
	USkeletalMeshComponent* Mesh = NewObject<USkeletalMeshComponent>(Stage);
	Stage->SetRootComponent(Mesh);
	Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Mesh->SetSkeletalMesh(Hero);
	Mesh->RegisterComponent();
	Mesh->SetComponentTickEnabled(false);
	Mesh->SetAnimInstanceClass(UDinkBodyAnimInstance::StaticClass());
	UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(Mesh->GetAnimInstance());
	if (!TestTrue(TEXT("hero clip set"), Body && Body->Configure(Library, TEXT("Hero")))) return false;
	TestEqual(TEXT("the layer is on exactly when both posture clips are there"), Body->HasMannerisms(), bClips);

	// The same library without the clips: the layer is off (master before #218).
	TMap<FName, FDinkBodyClip> Without = Library;
	Without.Remove(TEXT("Posture_Timid"));
	UDinkBodyAnimInstance* Plain = NewObject<UDinkBodyAnimInstance>(Mesh);
	TestTrue(TEXT("plain set configures"), Plain->Configure(Without, TEXT("Hero")));
	TestFalse(TEXT("without Posture_Timid nothing changes"), Plain->HasMannerisms());
	if (!bClips) return true;

	auto Step = [&](float Speed, float Confidence, int32 Frames)
	{
		for (int32 I = 0; I < Frames; ++I)
		{
			Mesh->SetWorldLocation(Mesh->GetComponentLocation() + FVector(0, Speed / 60.f, 0));
			Body->SetMotion(Speed, false, Confidence);
			Mesh->TickAnimation(1.f / 60.f, false);
			Mesh->RefreshBoneTransforms();
		}
	};
	Step(0.f, 0.f, 30);
	const FDinkBodyMannerFrame& M = Body->GetFrame().Manner;
	TestTrue(TEXT("standing lad: the additive posture is handed over"), M.IsActive() && M.PostureWeight > .99f);
	TestTrue(TEXT("standing: no gait layer shown"), M.MoveAlpha < .01f);
	Step(600.f, 0.f, 120);
	TestTrue(TEXT("running lad: the timid gait and the run arms"), Body->GetFrame().Manner.Gait > .9f && Body->GetFrame().Manner.RunAlpha > .9f);
	Step(600.f, 1.f, 120);
	TestTrue(TEXT("the hero runs without the timid gait layer"), Body->GetFrame().Manner.Gait < .01f);
	Body->SetMannerScale(.2f);
	Step(0.f, 0.f, 10);
	TestTrue(TEXT("a wall in front takes most of the slump away"), Body->GetFrame().Manner.PostureWeight < .25f);
	return true;
}
