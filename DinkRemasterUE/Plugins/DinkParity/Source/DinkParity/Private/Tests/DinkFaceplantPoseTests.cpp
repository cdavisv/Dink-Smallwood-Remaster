// Takeover A2 (25 Nov 2026): Botch_Faceplant through the body layer (UDinkBodyAnimInstance, #230's mannerism runtime) against
// the clip's own pose. In the game of 23 Nov the hero ended propped on his fists with the shins in the air while the clip lies
// flat (Docs/Verification/HeroMannerismClips_23Nov2026, sheet 07). This dump plays the clip on the hero as the character does
// (full body, the posture row, the arm fade, the mannerism layer, the leg layer) and samples the clip alone, and writes the
// component-space bone heights at chosen times to Saved/Animation/faceplant_pose.txt. Presentation only.
#include "DinkTestHelpers.h"
#include "DinkArtSubsystem.h"
#include "DinkBodyAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"

namespace DinkFaceplantPose
{
	static const TCHAR* const Bones[] = {TEXT("root"), TEXT("pelvis"), TEXT("spine_04"), TEXT("head"), TEXT("hand_l"), TEXT("hand_r"),
		TEXT("thigh_l"), TEXT("calf_l"), TEXT("calf_r"), TEXT("foot_l"), TEXT("foot_r"), TEXT("ball_l"), TEXT("ball_r")};
	constexpr int32 NumBones = UE_ARRAY_COUNT(Bones);

	struct FPose { float Z[NumBones]; };

	FPose Read(const USkeletalMeshComponent* Mesh)
	{
		FPose P;
		const TArray<FTransform>& CS = Mesh->GetComponentSpaceTransforms();
		for (int32 i = 0; i < NumBones; ++i)
		{
			const int32 Index = Mesh->GetBoneIndex(Bones[i]);
			P.Z[i] = CS.IsValidIndex(Index) ? float(CS[Index].GetLocation().Z) : -999.f;
		}
		return P;
	}

	FString Row(const TCHAR* Label, float T, const FPose& P)
	{
		FString S = FString::Printf(TEXT("%-26s t=%4.2f"), Label, T);
		for (int32 i = 0; i < NumBones; ++i) S += FString::Printf(TEXT(" %7.1f"), P.Z[i]);
		return S;
	}

	USkeletalMeshComponent* MakeMesh(UWorld* World, USkeletalMesh* Hero)
	{
		AActor* Stage = World->SpawnActor<AActor>();
		USkeletalMeshComponent* Mesh = NewObject<USkeletalMeshComponent>(Stage);
		Stage->SetRootComponent(Mesh);
		Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		Mesh->SetSkeletalMesh(Hero);
		Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision); // the other cases' bodies are no ground for this one's feet
		Mesh->RegisterComponent();
		Mesh->SetComponentTickEnabled(false);
		return Mesh;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFaceplantPoseTest, "Dink.Animation.FaceplantLiesAsItsClip", DINK_TEST_FLAGS)
bool FDinkFaceplantPoseTest::RunTest(const FString&)
{
	using namespace DinkFaceplantPose;
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
	UDinkArtSubsystem* Art = World->GetSubsystem<UDinkArtSubsystem>();
	// The mesh the game shows (UDinkArtSubsystem: dink.PhotorealHero 1 puts SK_Dink_Photoreal on the player when it is imported).
	USkeletalMesh* Hero = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Photoreal/Characters/Dink/SK_Dink_Photoreal.SK_Dink_Photoreal"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!Hero) Hero = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Hero/Refinements/SK_Dink_Hands.SK_Dink_Hands"));
	if (Hero) AddInfo(FString::Printf(TEXT("hero mesh %s"), *Hero->GetName()));
	if (!TestNotNull(TEXT("art subsystem"), Art) || !TestNotNull(TEXT("hero mesh"), Hero) || Art->GetAnimationLibrary().IsEmpty()) return false;
	const TMap<FName, FDinkBodyClip>& Library = Art->GetAnimationLibrary();
	const FDinkBodyClip* Clip = Library.Find(TEXT("Botch_Faceplant"));
	if (!Clip || !Clip->IsValid())
	{
		AddInfo(TEXT("Botch_Faceplant is not in the animation library (PR #218 not imported): nothing to compare"));
		return true;
	}
	UAnimSequence* Sequence = Cast<UAnimSequence>(Clip->Sequence.Get());
	if (!TestNotNull(TEXT("the clip is an anim sequence"), Sequence)) return false;
	const float Times[] = {.34f, .8f, 1.2f, 1.6f, 2.f, Clip->Duration - .05f};

	// The clip alone.
	USkeletalMeshComponent* Alone = MakeMesh(World, Hero);
	Alone->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	Alone->PlayAnimation(Sequence, false);
	TArray<FPose> Own;
	for (const float T : Times)
	{
		Alone->SetPosition(T, false);
		Alone->TickAnimation(0.f, false);
		Alone->RefreshBoneTransforms();
		Own.Add(Read(Alone));
	}

	// Through the body layer, as ADinkGreyboxCharacter plays it (PlayBotch), the timid lad standing on level ground.
	IConsoleVariable* Legs = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Anim.Legs"));
	IConsoleVariable* Lying = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Anim.LegsOffLying"));
	if (!TestNotNull(TEXT("dink.Anim.LegsOffLying registered"), Lying)) return false;
	const int32 LegsWas = Legs ? Legs->GetInt() : 1, LyingWas = Lying->GetInt();
	ON_SCOPE_EXIT { if (Legs) Legs->Set(LegsWas, ECVF_SetByCode); Lying->Set(LyingWas, ECVF_SetByCode); };
	// bFloor: a drawn floor 10 cm above the capsule's (an interior's planks, landforms) that the feet's ground traces find, the
	// mesh counted as on screen (the traces run only for a body that was rendered: UpdateLegInput).
	struct FCase { const TCHAR* Name; int32 Legs; int32 Lying; bool bPosture; float Manner; bool bFloor; };
	const FCase Cases[] = {{TEXT("game (all layers)"), 1, 1, true, 1.f, false}, {TEXT("23 Nov (legs on lying)"), 1, 0, true, 1.f, false},
		{TEXT("game, floor +10 cm"), 1, 1, true, 1.f, true}, {TEXT("23 Nov, floor +10 cm"), 1, 0, true, 1.f, true},
		{TEXT("no leg layer"), 0, 1, true, 1.f, false}, {TEXT("no posture row"), 1, 1, false, 1.f, false}, {TEXT("no mannerism layer"), 1, 1, true, 0.f, false}};
	UStaticMeshComponent* Floor = nullptr;
	if (UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")))
	{
		AActor* FloorActor = World->SpawnActor<AActor>();
		Floor = NewObject<UStaticMeshComponent>(FloorActor);
		FloorActor->SetRootComponent(Floor);
		Floor->SetStaticMesh(Cube);
		Floor->SetCollisionProfileName(TEXT("BlockAll"));
		Floor->SetWorldScale3D(FVector(40.0, 40.0, .1));
		Floor->SetWorldLocation(FVector(0.0, 0.0, 10.0 - 5.0)); // the unit cube is 100 cm: 10 cm thick, its top at +10
		Floor->RegisterComponent();
		Floor->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	}
	TArray<FPose> FloorGame;
	TArray<float> FloorShare;
	TArray<float> LyingShare;
	TArray<FString> Lines;
	FString Head = FString::Printf(TEXT("%-26s       "), TEXT("bone heights (cm)"));
	for (const TCHAR* B : Bones) Head += FString::Printf(TEXT(" %7.7s"), B);
	Lines.Add(Head);
	for (int32 i = 0; i < UE_ARRAY_COUNT(Times); ++i) Lines.Add(Row(TEXT("clip alone"), Times[i], Own[i]));
	TArray<FPose> Game;
	for (const FCase& Case : Cases)
	{
		if (Legs) Legs->Set(Case.Legs, ECVF_SetByCode);
		Lying->Set(Case.Lying, ECVF_SetByCode);
		if (Case.bFloor && !Floor) continue;
		if (Floor) Floor->SetCollisionEnabled(Case.bFloor ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
		USkeletalMeshComponent* Mesh = MakeMesh(World, Hero);
		Mesh->SetAnimInstanceClass(UDinkBodyAnimInstance::StaticClass());
		UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(Mesh->GetAnimInstance());
		if (!TestTrue(TEXT("hero clip set"), Body && Body->Configure(Library, TEXT("Hero")))) return false;
		FVector4f Posture = Art->GetAnimationPosture(TEXT("Hero"), 0.f);
		if (Body->HasMannerisms()) Posture = FVector4f(0.f, 0.f, 0.f, Posture.W);
		Body->SetPosture(Case.bPosture ? Posture : FVector4f(0, 0, 0, 0));
		Body->SetArmFade(Art->GetAnimationArmFade(TEXT("Hero")));
		Body->SetMannerScale(Case.Manner);
		auto Tick = [&]
		{
			if (Case.bFloor) Mesh->SetLastRenderTime(float(World->GetTimeSeconds()));
			Body->SetMotion(0.f, false, 0.f);
			Mesh->TickAnimation(1.f / 60.f, false);
			Mesh->RefreshBoneTransforms();
		};
		for (int32 F = 0; F < 60; ++F) Tick();
		if (!TestTrue(TEXT("Botch_Faceplant plays"), Body->PlayAction(TEXT("Botch_Faceplant"), true, 1.f, .04f, .25f))) return false;
		Body->SetActionRushWhenMoving(2.5f);
		float Now = 0.f;
		for (int32 i = 0; i < UE_ARRAY_COUNT(Times); ++i)
		{
			while (Now + 1.f / 120.f < Times[i]) { Tick(); Now += 1.f / 60.f; }
			const FPose P = Read(Mesh);
			Lines.Add(Row(Case.Name, Body->GetActionTime(), P) + FString::Printf(TEXT("  leg share %.2f"), Body->GetLegTelemetry().LegShare));
			if (&Case == &Cases[0]) { Game.Add(P); LyingShare.Add(Body->GetLegTelemetry().LegShare); }
			if (&Case == &Cases[2]) { FloorGame.Add(P); FloorShare.Add(Body->GetLegTelemetry().LegShare); }
		}
	}
	const FString Path = FPaths::ProjectSavedDir() / TEXT("Animation/faceplant_pose.txt");
	FFileHelper::SaveStringToFile(FString::Join(Lines, TEXT("\n")) + TEXT("\n"), *Path);
	for (const FString& L : Lines) AddInfo(L);

	// While he lies (the clip's posture_off_s .. posture_on_s) and at the end of the clip, the body layer's pose is the clip's:
	// every bone height within 6 cm, the feet and shins on the ground with the trunk (not propped on the fists).
	for (int32 i = 1; i < UE_ARRAY_COUNT(Times) - 2; ++i)
	{
		for (int32 b = 1; b < NumBones; ++b)
		{
			TestTrue(FString::Printf(TEXT("t=%.2f %s: %.1f cm in the game, %.1f cm in the clip"), Times[i], Bones[b], Game[i].Z[b], Own[i].Z[b]),
				FMath::Abs(Game[i].Z[b] - Own[i].Z[b]) <= 6.f);
		}
	}
	// With ground traces under a raised floor: the lying pose is the clip's lifted by the floor's 10 cm at most.
	for (int32 i = 1; i < FloorGame.Num() - 2; ++i)
	{
		for (int32 b = 1; b < NumBones; ++b)
		{
			TestTrue(FString::Printf(TEXT("floor, t=%.2f %s: %.1f cm in the game, %.1f cm in the clip"), Times[i], Bones[b], FloorGame[i].Z[b], Own[i].Z[b]),
				FMath::Abs(FloorGame[i].Z[b] - Own[i].Z[b]) <= 12.f && FMath::Abs((FloorGame[i].Z[b] - FloorGame[i].Z[1]) - (Own[i].Z[b] - Own[i].Z[1])) <= 6.f);
		}
	}
	TestTrue(FString::Printf(TEXT("lying (t=1.2) the leg layer has given way (share %.2f)"), LyingShare.IsValidIndex(2) ? LyingShare[2] : -1.f),
		LyingShare.IsValidIndex(2) && LyingShare[2] < .05f);
	return true;
}
