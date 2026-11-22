// Dink.Physics.*: secondary motion of the characters (hair, the Mother's skirt, hit jolt) and the physics assets.
#include "DinkTestHelpers.h"
#include "DinkSecondaryMotion.h"
#include "DinkCreatureClassComponent.h"
#include "AssetCompilingManager.h"
#include "BonePose.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "Misc/MemStack.h"
#include "Misc/ScopeExit.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

namespace DinkSecondaryTest
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

	const TCHAR* const Bodies[] = {
		TEXT("/Game/Dink/Photoreal/Characters/Dink/SK_Dink_Photoreal.SK_Dink_Photoreal"),
		TEXT("/Game/Dink/Photoreal/Characters/Mother/SK_Mother_Photoreal.SK_Mother_Photoreal"),
		TEXT("/Game/Dink/Photoreal/Characters/Milder/SK_Milder_Photoreal.SK_Milder_Photoreal"),
	};

	struct FCVarScope
	{
		IConsoleVariable* Var; FString Old;
		FCVarScope(const TCHAR* Name, const TCHAR* Value) : Var(IConsoleManager::Get().FindConsoleVariable(Name))
		{
			if (Var) { Old = Var->GetString(); Var->Set(Value, ECVF_SetByCode); }
		}
		~FCVarScope() { if (Var) Var->Set(*Old, ECVF_SetByCode); }
	};

	bool AllFinite(const TArray<float>& D) { for (float F : D) if (!FMath::IsFinite(F)) return false; return true; }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicsSpringTest, "Dink.Physics.Spring", DINK_TEST_FLAGS)
bool FDinkPhysicsSpringTest::RunTest(const FString& Parameters)
{
	const FDinkSpringParams P{ 3.f, .25f, 1.5f, 1.f };
	// settles to rest after a kick, and swings past zero on the way (it is underdamped: hair overshoots once or twice)
	FDinkSpring3 S;
	S.Kick(FVector(60.f, 0.f, 0.f), P);
	float MinX = 0.f;
	for (int32 i = 0; i < 60 * 4; ++i) { S.Step(1.f / 60.f, FVector::ZeroVector, FVector::ZeroVector, P); MinX = FMath::Min(MinX, float(S.X.X)); }
	TestTrue(TEXT("a kicked spring is at rest after 4 s"), S.IsAtRest(.01f));
	TestTrue(TEXT("it overshoots on the way back (a swing, not a creep)"), MinX < -.05f);
	// bounded: a landing at 60 m/s^2 (clamped to the limit), a sustained push, and a frame hitch
	S.Reset();
	float MaxLen = 0.f;
	for (int32 i = 0; i < 120; ++i) { S.Step(i == 60 ? .2f : 1.f / 60.f, FVector(0, 0, -6000.f), FVector(800.f, 0, 0), P); MaxLen = FMath::Max(MaxLen, float(S.X.Size())); }
	TestTrue(FString::Printf(TEXT("offset never passes its limit (%.3f <= %.3f)"), MaxLen, P.Max), MaxLen <= P.Max + 1e-4f);
	// steady lag under a steady acceleration is a / w^2, opposite to it
	S.Reset();
	for (int32 i = 0; i < 600; ++i) S.Step(1.f / 60.f, FVector(100.f, 0, 0), FVector::ZeroVector, P);
	const float Expected = -100.f / FMath::Square(2.f * PI * 3.f);
	TestTrue(FString::Printf(TEXT("steady lag %.4f cm against %.4f cm"), S.X.X, Expected), FMath::IsNearlyEqual(float(S.X.X), Expected, .002f));
	// no NaN: non-finite input resets instead of poisoning the state; huge and zero time steps are harmless
	S.Step(1.f / 60.f, FVector(NAN, 0, 0), FVector::ZeroVector, P);
	TestTrue(TEXT("NaN input leaves a finite state at rest"), !S.X.ContainsNaN() && S.IsAtRest());
	S.Step(1e9f, FVector(1e30f, 0, 0), FVector::ZeroVector, P);
	TestTrue(TEXT("huge step and input stay finite and bounded"), !S.X.ContainsNaN() && S.X.Size() <= P.Max + 1e-4f);
	S.Step(0.f, FVector(10, 0, 0), FVector::ZeroVector, P);
	TestTrue(TEXT("zero step is finite"), !S.X.ContainsNaN());
	S.Kick(FVector(1e30f, 0, 0), P);
	TestTrue(TEXT("a huge kick is capped"), FMath::IsFinite(S.V.X) && S.V.Size() < 1e3f);
	// the wind gust matches the foliage field's range
	float Lo = 10.f, Hi = -10.f;
	for (int32 i = 0; i < 400; ++i) { const float G = FDinkSecondaryMotion::FoliageGust(FVector2D(i * 137.0, i * 59.0), i * .37f); Lo = FMath::Min(Lo, G); Hi = FMath::Max(Hi, G); }
	TestTrue(FString::Printf(TEXT("gust within the foliage's 0.45..1.95 (%.2f..%.2f)"), Lo, Hi), Lo >= .449f && Hi <= 1.951f && Hi - Lo > .5f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicsBodiesTest, "Dink.Physics.SecondaryBodies", DINK_TEST_FLAGS)
bool FDinkPhysicsBodiesTest::RunTest(const FString& Parameters)
{
	using namespace DinkSecondaryTest;
	FAssetCompilingManager::Get().FinishAllCompilation();
	FWorldFixture E;
	// the default breeze would lean the hair of a still body: this test measures motion alone
	FCVarScope NoWind(TEXT("dink.Hair.Wind"), TEXT("0"));
	UDinkSecondaryMotionSubsystem* Sub = E.World->GetSubsystem<UDinkSecondaryMotionSubsystem>();
	if (!TestNotNull(TEXT("secondary motion subsystem exists in a game world"), Sub)) return false;
	int32 Checked = 0;
	for (const TCHAR* Path : Bodies)
	{
		USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, Path);
		if (!Mesh) { AddWarning(FString::Printf(TEXT("skipped %s: not imported"), Path)); continue; }
		AActor* Owner = E.World->SpawnActor<AActor>();
		USkeletalMeshComponent* C = NewObject<USkeletalMeshComponent>(Owner);
		C->SetSkeletalMesh(Mesh);
		Owner->SetRootComponent(C);
		C->RegisterComponent();
		C->SetWorldLocation(FVector(1000.f, 0.f, 0.f));
		C->RefreshBoneTransforms();
		if (!TestTrue(FString::Printf(TEXT("%s is tracked"), *Mesh->GetName()), Sub->Track(C))) continue;
		const FDinkSecondaryBody* B = Sub->FindBody(C);
		const bool bSkirt = B->Profile->bSkirt;
		// at rest: three frames build the history, then nothing moves
		for (int32 i = 0; i < 10; ++i) Sub->StepForTest(1.f / 60.f);
		const TArray<float>& D = C->GetCustomPrimitiveData().Data;
		TestEqual(FString::Printf(TEXT("%s: custom primitive data has the full layout"), *Mesh->GetName()), D.Num(), int32(DinkSecondaryCPD::Count));
		if (D.Num() != DinkSecondaryCPD::Count) continue;
		TestTrue(TEXT("finite"), AllFinite(D));
		TestTrue(TEXT("still body: hair tip offset ~0"), FVector(D[0], D[1], D[2]).Size() < .01f);
		TestEqual(TEXT("hair weight on"), D[DinkSecondaryCPD::HairWeight], 1.f);
		// head centre sits above the neck, in component space, about head height
		using namespace DinkSecondaryCPD;
		const float HeadZ = D[HeadCentre + 2];
		TestTrue(FString::Printf(TEXT("head centre at head height (%.1f cm)"), HeadZ), HeadZ > 140.f && HeadZ < 200.f);
		if (bSkirt)
		{
			const FQuat Q(D[PelvisRotation], D[PelvisRotation + 1], D[PelvisRotation + 2], D[PelvisRotation + 3]);
			TestTrue(TEXT("bind pose: pelvis-rigid rotation is identity"), Q.AngularDistance(FQuat::Identity) < .01f);
			TestTrue(TEXT("bind pose: pelvis-rigid translation is zero"), FVector(D[PelvisTranslation], D[PelvisTranslation + 1], D[PelvisTranslation + 2]).Size() < .05f);
			// heights (z) of the joints the skirt reads
			TestTrue(TEXT("knees below hips, ankles below knees"), D[KneeL + 2] < D[HipL + 2] && D[AnkleL + 2] < D[KneeL + 2] && D[KneeR + 2] < D[HipR + 2] && D[AnkleR + 2] < D[KneeR + 2]);
		}
		// a sprint start, a sudden stop and a turn: bounded, then settles to rest
		float MaxTip = 0.f, MaxSkirt = 0.f;
		FVector Pos = C->GetComponentLocation();
		float Speed = 0.f, Yaw = 0.f;
		for (int32 i = 0; i < 300; ++i)
		{
			const float T = i / 60.f;
			const float Target = T < 1.5f ? 600.f : 0.f;
			Speed = FMath::FInterpConstantTo(Speed, Target, 1.f / 60.f, 2400.f);
			Yaw += (T > .8f && T < 1.1f ? 300.f : 0.f) / 60.f;
			Pos += FRotator(0.f, Yaw, 0.f).Vector() * Speed / 60.f;
			C->SetWorldLocationAndRotation(Pos, FRotator(0.f, Yaw, 0.f));
			Sub->StepForTest(1.f / 60.f);
			const TArray<float>& F = C->GetCustomPrimitiveData().Data;
			if (!AllFinite(F)) { AddError(TEXT("non-finite custom primitive data while moving")); break; }
			MaxTip = FMath::Max(MaxTip, float(FVector(F[0], F[1], F[2]).Size()));
			MaxSkirt = FMath::Max(MaxSkirt, float(FVector(F[DinkSecondaryCPD::SkirtSway], F[DinkSecondaryCPD::SkirtSway + 1], F[DinkSecondaryCPD::SkirtSway + 2]).Size()));
		}
		const float Scale = C->GetComponentScale().X;
		TestTrue(FString::Printf(TEXT("%s: hair lags on the start (%.2f cm)"), *Mesh->GetName(), MaxTip), MaxTip > .1f);
		TestTrue(FString::Printf(TEXT("%s: hair within its limit (%.2f <= %.2f)"), *Mesh->GetName(), MaxTip, B->Profile->Hair.Max / Scale), MaxTip <= B->Profile->Hair.Max / Scale + .01f);
		if (bSkirt) TestTrue(FString::Printf(TEXT("skirt swings and stays bounded (%.2f cm)"), MaxSkirt), MaxSkirt > .3f && MaxSkirt <= B->Profile->Skirt.Max + .01f);
		for (int32 i = 0; i < 60 * 4; ++i) Sub->StepForTest(1.f / 60.f);
		{
			const TArray<float>& F = C->GetCustomPrimitiveData().Data;
			TestTrue(FString::Printf(TEXT("%s: settles after the stop (%.4f cm)"), *Mesh->GetName(), FVector(F[0], F[1], F[2]).Size()), FVector(F[0], F[1], F[2]).Size() < .02f);
			if (bSkirt) TestTrue(TEXT("skirt settles"), FVector(F[DinkSecondaryCPD::SkirtSway], F[DinkSecondaryCPD::SkirtSway + 1], F[DinkSecondaryCPD::SkirtSway + 2]).Size() < .05f);
		}
		// a teleport (screen change, load) restarts the springs instead of flinging them
		Pos += FVector(5000.f, 0.f, 0.f);
		C->SetWorldLocation(Pos);
		for (int32 i = 0; i < 3; ++i) Sub->StepForTest(1.f / 60.f);
		{
			const TArray<float>& F = C->GetCustomPrimitiveData().Data;
			TestTrue(TEXT("a teleport does not fling the hair"), FVector(F[0], F[1], F[2]).Size() < .02f);
		}
		// off switches write zeros
		{
			FCVarScope Hair(TEXT("dink.Hair.Physics"), TEXT("0")), Garment(TEXT("dink.Garment.Physics"), TEXT("0"));
			Pos += FVector(30.f, 0, 0);
			C->SetWorldLocation(Pos);
			for (int32 i = 0; i < 5; ++i) Sub->StepForTest(1.f / 60.f);
			const TArray<float>& F = C->GetCustomPrimitiveData().Data;
			TestEqual(TEXT("dink.Hair.Physics 0: hair weight 0"), F[DinkSecondaryCPD::HairWeight], 0.f);
			TestTrue(TEXT("dink.Garment.Physics 0: skirt off (zero rotation)"), FVector4(F[DinkSecondaryCPD::PelvisRotation], F[DinkSecondaryCPD::PelvisRotation + 1], F[DinkSecondaryCPD::PelvisRotation + 2], F[DinkSecondaryCPD::PelvisRotation + 3]).SizeSquared() == 0.0);
		}
		{
			FCVarScope Q(TEXT("dink.Secondary.Quality"), TEXT("0"));
			Sub->Tick(1.f / 60.f);
			const TArray<float>& F = C->GetCustomPrimitiveData().Data;
			bool bZero = true; for (float V : F) bZero &= V == 0.f;
			TestTrue(TEXT("quality 0 (effects Low) writes all zeros"), bZero);
		}
		// hit jolt: bounded, settles, published for the pose hook; presentation only (the actor and the root/pelvis pose stay)
		const FVector ActorBefore = Owner->GetActorLocation();
		const TArray<FTransform> PoseBefore = C->GetComponentSpaceTransforms();
		Sub->NotifyHit(Owner, FVector(0.f, -1.f, 0.f), 1.f);
		float MaxJolt = 0.f;
		for (int32 i = 0; i < 60; ++i) { Sub->StepForTest(1.f / 60.f); MaxJolt = FMath::Max(MaxJolt, FDinkSecondaryMotion::GetPublishedJolt(C).Size()); }
		TestTrue(FString::Printf(TEXT("a hit jolts (%.2f deg) within the limit"), MaxJolt), MaxJolt > 3.f && MaxJolt <= B->Profile->Jolt.Max + .01f);
		for (int32 i = 0; i < 120; ++i) Sub->StepForTest(1.f / 60.f);
		TestTrue(TEXT("the jolt is over within 3 s"), FDinkSecondaryMotion::GetPublishedJolt(C).Size() < .02f);
		TestTrue(TEXT("presentation only: the actor did not move"), Owner->GetActorLocation().Equals(ActorBefore, .01f));
		const TArray<FTransform>& PoseAfter = C->GetComponentSpaceTransforms();
		bool bPoseSame = PoseAfter.Num() == PoseBefore.Num();
		for (int32 i = 0; bPoseSame && i < PoseAfter.Num(); ++i) bPoseSame &= PoseAfter[i].Equals(PoseBefore[i], 1e-4);
		TestTrue(TEXT("presentation only: no bone of the component's pose was written by the subsystem"), bPoseSame);
		++Checked;
	}
	if (Checked == 0) AddWarning(TEXT("no photoreal character imported: nothing checked"));
	AddInfo(Sub->Report());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicsJoltPoseTest, "Dink.Physics.HitJoltPose", DINK_TEST_FLAGS)
bool FDinkPhysicsJoltPoseTest::RunTest(const FString& Parameters)
{
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, DinkSecondaryTest::Bodies[0]);
	if (!Mesh) { AddWarning(TEXT("skipped: hero not imported")); return true; }
	FAssetCompilingManager::Get().FinishAllCompilation();
	USkeletalMeshComponent* C = NewObject<USkeletalMeshComponent>(GetTransientPackage());
	C->SetSkeletalMesh(Mesh);
	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
	TArray<FBoneIndexType> Required;
	for (int32 i = 0; i < Ref.GetNum(); ++i) Required.Add(FBoneIndexType(i));
	FBoneContainer Container(Required, UE::Anim::FCurveFilterSettings(), *Mesh);
	// compact poses allocate on the frame memory stack, as inside an animation evaluation
	FMemMark Mark(FMemStack::Get());
	FCompactPose Pose;
	Pose.SetBoneContainer(&Container);
	Pose.ResetToRefPose();
	const FCompactPose Before = Pose;
	FDinkSecondaryMotion::ApplyToPose(C, Pose);
	bool bSame = true;
	for (FCompactPoseBoneIndex B(0); B.GetInt() < Pose.GetNumBones(); ++B) bSame &= Pose[B].Equals(Before[B], 1e-5);
	TestTrue(TEXT("no published jolt: the pose is untouched"), bSame);
	FDinkSecondaryMotion::PublishJolt(C, FVector3f(-8.f, 3.f, 1.f));
	ON_SCOPE_EXIT { FDinkSecondaryMotion::ForgetMesh(C); };
	FDinkSecondaryMotion::ApplyToPose(C, Pose);
	int32 Changed = 0;
	for (FCompactPoseBoneIndex B(0); B.GetInt() < Pose.GetNumBones(); ++B)
	{
		const FName Name = Ref.GetBoneName(Container.MakeMeshPoseIndex(B).GetInt());
		const bool bMoved = !Pose[B].Equals(Before[B], 1e-5);
		Changed += bMoved;
		if (bMoved) TestTrue(FString::Printf(TEXT("only the chest, neck and head turn (%s)"), *Name.ToString()), Name == TEXT("spine_03") || Name == TEXT("neck_01") || Name == TEXT("head"));
		if (Name == TEXT("root") || Name == TEXT("pelvis")) TestFalse(TEXT("root and pelvis never move"), bMoved);
		TestTrue(TEXT("translations never change"), Pose[B].GetTranslation().Equals(Before[B].GetTranslation(), 1e-4));
	}
	TestEqual(TEXT("three bones jolted"), Changed, 3);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicsMaterialsTest, "Dink.Physics.MotionMaterials", DINK_TEST_FLAGS)
bool FDinkPhysicsMaterialsTest::RunTest(const FString& Parameters)
{
#if WITH_EDITORONLY_DATA
	struct FRow { const TCHAR* Path; bool bExpect; };
	const FRow Rows[] = {
		{ TEXT("/Game/Dink/Photoreal/Characters/Dink/M_Dink_PR_Hair.M_Dink_PR_Hair"), true },
		{ TEXT("/Game/Dink/Photoreal/Characters/Mother/M_Mother_PR_Hair.M_Mother_PR_Hair"), true },
		{ TEXT("/Game/Dink/Photoreal/Characters/Milder/M_Milder_PR_Hair.M_Milder_PR_Hair"), true },
		{ TEXT("/Game/Dink/Photoreal/Characters/Mother/M_Mother_PR_Outfit.M_Mother_PR_Outfit"), true },
		{ TEXT("/Game/Dink/Photoreal/Characters/Dink/M_Dink_PR_Outfit.M_Dink_PR_Outfit"), false },
	};
	for (const FRow& R : Rows)
	{
		const UMaterial* M = LoadObject<UMaterial>(nullptr, R.Path);
		if (!M) { AddWarning(FString::Printf(TEXT("skipped %s: not imported"), R.Path)); continue; }
		const bool bWpo = M->GetEditorOnlyData()->WorldPositionOffset.IsConnected();
		TestEqual(FString::Printf(TEXT("%s: world position offset %s"), R.Path, R.bExpect ? TEXT("connected") : TEXT("absent")), bWpo, R.bExpect);
	}
#endif
	return true;
}

/** Report only (cannot fail): every body and constraint of the character and creature physics assets, and the human
 * constraints wider than a human joint range (half-angles in degrees, swing about each side of the reference, twist
 * about the bone). No physics asset simulates anywhere in the game today. */
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicsLimitsTest, "Dink.Report.PhysicsConstraints", DINK_TEST_FLAGS)
bool FDinkPhysicsLimitsTest::RunTest(const FString& Parameters)
{
	struct FRange { const TCHAR* Prefix; float Swing, Twist; };
	static const FRange Ranges[] = {
		{ TEXT("spine"), 35.f, 35.f }, { TEXT("neck"), 50.f, 70.f }, { TEXT("head"), 50.f, 70.f }, { TEXT("clavicle"), 30.f, 30.f },
		{ TEXT("upperarm"), 100.f, 90.f }, { TEXT("lowerarm"), 80.f, 90.f }, { TEXT("hand"), 75.f, 35.f }, { TEXT("thigh"), 90.f, 50.f },
		{ TEXT("calf"), 80.f, 20.f }, { TEXT("foot"), 50.f, 30.f }, { TEXT("ball"), 45.f, 10.f },
	};
	const TCHAR* const Assets[] = {
		TEXT("/Game/Dink/Photoreal/Characters/Dink/SK_Dink_Photoreal_PhysicsAsset.SK_Dink_Photoreal_PhysicsAsset"),
		TEXT("/Game/Dink/Photoreal/Characters/Mother/SK_Mother_Photoreal_PhysicsAsset.SK_Mother_Photoreal_PhysicsAsset"),
		TEXT("/Game/Dink/Photoreal/Characters/Milder/SK_Milder_Photoreal_PhysicsAsset.SK_Milder_Photoreal_PhysicsAsset"),
		TEXT("/Game/Dink/Hero/Refinements/SK_Dink_Hands_PhysicsAsset.SK_Dink_Hands_PhysicsAsset"),
		TEXT("/Game/Dink/Creatures/Pig/SK_Pig_PhysicsAsset.SK_Pig_PhysicsAsset"),
		TEXT("/Game/Dink/Creatures/Pillbug/SK_Pillbug_PhysicsAsset.SK_Pillbug_PhysicsAsset"),
	};
	auto MotionName = [](EAngularConstraintMotion M) { return M == ACM_Free ? TEXT("free") : M == ACM_Locked ? TEXT("locked") : TEXT("limited"); };
	int32 Over = 0;
	for (const TCHAR* Path : Assets)
	{
		const UPhysicsAsset* PA = LoadObject<UPhysicsAsset>(nullptr, Path);
		if (!PA) { AddWarning(FString::Printf(TEXT("missing %s"), Path)); continue; }
		const bool bHuman = !FString(Path).Contains(TEXT("Creatures"));
		FString Table = FString::Printf(TEXT("%s: %d bodies, %d constraints\n"), *PA->GetName(), PA->SkeletalBodySetups.Num(), PA->ConstraintSetup.Num());
		for (const USkeletalBodySetup* Body : PA->SkeletalBodySetups)
		{
			if (!Body) continue;
			const FKAggregateGeom& G = Body->AggGeom;
			Table += FString::Printf(TEXT("  body %s: %d capsule %d box %d sphere %d convex %d tapered\n"), *Body->BoneName.ToString(),
				G.SphylElems.Num(), G.BoxElems.Num(), G.SphereElems.Num(), G.ConvexElems.Num(), G.TaperedCapsuleElems.Num());
		}
		for (const UPhysicsConstraintTemplate* C : PA->ConstraintSetup)
		{
			if (!C) continue;
			const FConstraintInstance& I = C->DefaultInstance;
			const FConeConstraint& Cone = I.ProfileInstance.ConeLimit;
			const FTwistConstraint& Twist = I.ProfileInstance.TwistLimit;
			const FString Bone = I.ConstraintBone1.ToString();
			Table += FString::Printf(TEXT("  joint %s-%s: swing1 %s %.0f, swing2 %s %.0f, twist %s %.0f\n"), *Bone, *I.ConstraintBone2.ToString(),
				MotionName(Cone.Swing1Motion), Cone.Swing1LimitDegrees, MotionName(Cone.Swing2Motion), Cone.Swing2LimitDegrees, MotionName(Twist.TwistMotion), Twist.TwistLimitDegrees);
			if (!bHuman) continue;
			for (const FRange& R : Ranges)
			{
				if (!Bone.StartsWith(R.Prefix)) continue;
				auto Bad = [&](EAngularConstraintMotion M, float Deg, float Max) { return M == ACM_Free || (M == ACM_Limited && Deg > Max + .5f); };
				if (Bad(Cone.Swing1Motion, Cone.Swing1LimitDegrees, R.Swing) || Bad(Cone.Swing2Motion, Cone.Swing2LimitDegrees, R.Swing) || Bad(Twist.TwistMotion, Twist.TwistLimitDegrees, R.Twist))
				{
					++Over;
					AddWarning(FString::Printf(TEXT("%s %s: beyond a human range (swing <= %.0f, twist <= %.0f)"), *PA->GetName(), *Bone, R.Swing, R.Twist));
				}
				break;
			}
		}
		AddInfo(Table);
	}
	// Reported, not failed: no physics asset simulates anywhere in the game (no ragdoll, no physical animation), so the
	// limits shape nothing a player sees today. The row and the fix plan are in the hair-cloth-physics notes.
	AddInfo(FString::Printf(TEXT("%d human constraints beyond a human range"), Over));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicsLoosePartsTest, "Dink.Physics.LooseParts", DINK_TEST_FLAGS)
bool FDinkPhysicsLoosePartsTest::RunTest(const FString& Parameters)
{
	using namespace DinkSecondaryTest;
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Photoreal/Creatures/Pillbug/SK_Pillbug_Photoreal.SK_Pillbug_Photoreal"));
	if (!Mesh) Mesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Creatures/Pillbug/SK_Pillbug.SK_Pillbug"));
	if (!Mesh) { AddWarning(TEXT("skipped: no pillbug imported")); return true; }
	FAssetCompilingManager::Get().FinishAllCompilation();
	FWorldFixture E;
	UDinkSecondaryMotionSubsystem* Sub = E.World->GetSubsystem<UDinkSecondaryMotionSubsystem>();
	AActor* Owner = E.World->SpawnActor<AActor>();
	USkeletalMeshComponent* C = NewObject<USkeletalMeshComponent>(Owner);
	C->SetSkeletalMesh(Mesh);
	// loose parts reach a pose only through a native Dink animation instance, as class-bound creatures have
	C->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	C->SetAnimInstanceClass(UDinkCreatureAnimInstance::StaticClass());
	Owner->SetRootComponent(C);
	C->RegisterComponent();
	C->RefreshBoneTransforms();
	TestNotNull(TEXT("the body runs the creature animation instance"), Cast<UDinkCreatureAnimInstance>(C->GetAnimInstance()));
	if (!TestTrue(TEXT("pillbug tracked"), Sub && Sub->Track(C))) return false;
	const FDinkSecondaryBody* B = Sub->FindBody(C);
	TestEqual(TEXT("three chains (two antennae, tail)"), B->Profile->Chains.Num(), 3);
	// scuttle off and stop: the antennae lag, stay bounded, settle
	FVector Pos = C->GetComponentLocation();
	float Speed = 0.f, MaxLag = 0.f;
	for (int32 i = 0; i < 240; ++i)
	{
		Speed = FMath::FInterpConstantTo(Speed, i < 60 ? 150.f : 0.f, 1.f / 60.f, 1500.f);
		Pos.X += Speed / 60.f;
		C->SetWorldLocation(Pos);
		Sub->StepForTest(1.f / 60.f);
		for (const FDinkSpring3& S : B->ChainSprings) { MaxLag = FMath::Max(MaxLag, float(S.X.Size())); TestFalse(TEXT("finite"), S.X.ContainsNaN()); }
	}
	TestTrue(FString::Printf(TEXT("antennae lag on the start and stop (%.2f cm) within the limit"), MaxLag), MaxLag > .3f && MaxLag <= B->Profile->Chain.Max + .01f);
	for (int32 i = 0; i < 300; ++i) Sub->StepForTest(1.f / 60.f);
	float Rest = 0.f;
	for (const FDinkSpring3& S : B->ChainSprings) Rest = FMath::Max(Rest, float(S.X.Size()));
	TestTrue(FString::Printf(TEXT("settled (%.4f cm)"), Rest), Rest < .02f);
	// the pose hook turns only chain bones
	FDinkSecondaryMotion::Publish(C, FVector3f::ZeroVector, B->Profile, { FVector3f(0, 0, 2), FVector3f(0, 0, 2), FVector3f(0, 0, 1) });
	ON_SCOPE_EXIT { FDinkSecondaryMotion::ForgetMesh(C); };
	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
	TArray<FBoneIndexType> Required;
	for (int32 i = 0; i < Ref.GetNum(); ++i) Required.Add(FBoneIndexType(i));
	FBoneContainer Container(Required, UE::Anim::FCurveFilterSettings(), *Mesh);
	// compact poses allocate on the frame memory stack, as inside an animation evaluation
	FMemMark Mark(FMemStack::Get());
	FCompactPose Pose;
	Pose.SetBoneContainer(&Container);
	Pose.ResetToRefPose();
	const FCompactPose Before = Pose;
	FDinkSecondaryMotion::ApplyToPose(C, Pose);
	int32 Moved = 0;
	for (FCompactPoseBoneIndex I(0); I.GetInt() < Pose.GetNumBones(); ++I)
	{
		if (Pose[I].Equals(Before[I], 1e-5)) continue;
		++Moved;
		const FString Name = Ref.GetBoneName(Container.MakeMeshPoseIndex(I).GetInt()).ToString();
		TestTrue(FString::Printf(TEXT("only loose-part bones turn (%s)"), *Name), Name.StartsWith(TEXT("antenna")) || Name == TEXT("tail"));
	}
	TestEqual(TEXT("five loose-part bones turned"), Moved, 5);
	{
		FCVarScope Off(TEXT("dink.LooseParts.Physics"), TEXT("0"));
		Sub->StepForTest(1.f / 60.f);
		FCompactPose P2; P2.SetBoneContainer(&Container); P2.ResetToRefPose();
		FDinkSecondaryMotion::ApplyToPose(C, P2);
		bool bSame = true;
		for (FCompactPoseBoneIndex I(0); I.GetInt() < P2.GetNumBones(); ++I) bSame &= P2[I].Equals(Before[I], 1e-5);
		TestTrue(TEXT("dink.LooseParts.Physics 0 leaves the pose alone"), bSame);
	}
	return true;
}
