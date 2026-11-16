// Dink.Animation tests of the leg placement layer (DinkFootPlacement.h, UDinkBodyAnimInstance): two-bone reach and
// knee limits, planted feet that do not slide or spin, pivot steps when turning on the spot, the pelvis on flat ground,
// look-at limits and each character's gait style. Presentation only: none of this touches gameplay.
#include "DinkTestHelpers.h"
#include "DinkArtSubsystem.h"
#include "DinkBodyAnimInstance.h"
#include "DinkFootPlacement.h"
#include "AnimationRuntime.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkTwoBoneIKTest, "Dink.Animation.Legs.TwoBoneIK", DINK_TEST_FLAGS)
bool FDinkTwoBoneIKTest::RunTest(const FString&)
{
	// A 45 + 43 cm leg, knee forward (+Y), hip at 90 cm.
	const FVector Hip(0, 0, 90), Knee(0, 4, 45.2), Ankle(0, 0, 2.5);
	const double A = FVector::Dist(Hip, Knee), B = FVector::Dist(Knee, Ankle);
	FRandomStream Rng(7);
	double WorstLength = 0, WorstMiss = 0, MinFlex = 1e9;
	for (int32 I = 0; I < 2000; ++I)
	{
		const FVector Target = Hip + FVector(Rng.FRandRange(-40.f, 40.f), Rng.FRandRange(-50.f, 50.f), -Rng.FRandRange(20.f, float((A + B) * .95)));
		FVector NK, NA;
		const float Short = FDinkTwoBoneIK::Solve(Hip, Knee, Ankle, Target, FVector::YAxisVector, NK, NA);
		WorstLength = FMath::Max3(WorstLength, FMath::Abs(FVector::Dist(Hip, NK) - A), FMath::Abs(FVector::Dist(NK, NA) - B));
		if (FVector::Dist(Hip, Target) < (A + B) * .9) WorstMiss = FMath::Max(WorstMiss, double(FVector::Dist(NA, Target)) + Short * 0.);
		MinFlex = FMath::Min(MinFlex, double(FDinkTwoBoneIK::Flexion(Hip, NK, NA, FVector::YAxisVector)));
	}
	AddInfo(FString::Printf(TEXT("IK: worst bone length change %.4f cm, worst miss inside 90%% reach %.4f cm, least knee flexion %.2f deg"), WorstLength, WorstMiss, MinFlex));
	TestTrue(TEXT("bone lengths are kept"), WorstLength < .01);
	TestTrue(TEXT("a reachable target is reached"), WorstMiss < .05);
	TestTrue(TEXT("the knee never bends backwards"), MinFlex >= 0.);
	// Soft reach: pulling the target straight down past full extension, the ankle approaches it smoothly (no pop).
	double Prev = -1, WorstJump = 0;
	for (int32 I = 0; I <= 200; ++I)
	{
		const FVector Target = Hip - FVector(0, 0, (A + B) * (.85 + .3 * I / 200.));
		FVector NK, NA;
		FDinkTwoBoneIK::Solve(Hip, Knee, Ankle, Target, FVector::YAxisVector, NK, NA);
		const double D = FVector::Dist(Hip, NA);
		if (Prev >= 0) WorstJump = FMath::Max(WorstJump, D - Prev);
		Prev = D;
		TestTrue(TEXT("never longer than the leg"), D <= A + B + 1e-3);
	}
	const double TargetStep = (A + B) * .3 / 200.;
	AddInfo(FString::Printf(TEXT("IK soft reach: largest ankle step %.4f cm for a target step of %.4f cm"), WorstJump, TargetStep));
	TestTrue(TEXT("the leg straightens smoothly (no knee pop)"), WorstJump <= TargetStep * 1.001);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFootLockTurnTest, "Dink.Animation.Legs.TurnSteps", DINK_TEST_FLAGS)
bool FDinkFootLockTurnTest::RunTest(const FString&)
{
	// A body turning 180 degrees on the spot at 900 deg/s (the player's turn rate) with its feet 12 cm either side.
	FDinkFootLock Locks[2];
	const FDinkFootLockSettings S;
	const float Dt = 1.f / 60.f;
	FVector Last[2];
	bool bLast = false;
	double PinnedSlide = 0, MaxLift = 0;
	int32 BothStepping = 0, StepFrames = 0;
	for (int32 Frame = 0; Frame < 150; ++Frame)
	{
		const float Yaw = FMath::Min(180.f, 900.f * FMath::Max(0, Frame - 20) * Dt);
		int32 Stepping = 0;
		for (int32 F = 0; F < 2; ++F)
		{
			FDinkFootLock::FInput In;
			In.Desired = FRotator(0, Yaw, 0).RotateVector(FVector(0, F == 0 ? 12 : -12, 0));
			In.DesiredYaw = Yaw;
			In.GroundSpeed = 0.f;
			In.bOtherPinned = Locks[1 - F].IsPinned();
			const bool bWasPinned = Locks[F].IsPinned();
			const FDinkFootLock::FOutput Out = Locks[F].Update(In, Dt, S);
			if (bLast && bWasPinned && Locks[F].IsPinned()) PinnedSlide = FMath::Max(PinnedSlide, FVector::Dist2D(Out.Position, Last[F]));
			MaxLift = FMath::Max(MaxLift, double(Out.Lift));
			if (Locks[F].GetState() == FDinkFootLock::EState::Stepping) ++Stepping;
			Last[F] = Out.Position;
			if (Frame == 149) TestTrue(TEXT("both feet end where the turned pose wants them"), FVector::Dist2D(Out.Position, In.Desired) < 1.);
		}
		bLast = true;
		BothStepping += Stepping == 2;
		StepFrames += Stepping > 0;
	}
	const int32 Steps = Locks[0].GetSteps() + Locks[1].GetSteps();
	AddInfo(FString::Printf(TEXT("TURN 180 on the spot: %d pivot steps (%d left, %d right) over %d frames, pinned-foot slide %.4f cm/frame, highest lift %.1f cm, frames with both feet in the air %d"),
		Steps, Locks[0].GetSteps(), Locks[1].GetSteps(), StepFrames, PinnedSlide, MaxLift, BothStepping));
	TestTrue(TEXT("a planted foot does not slide or spin with the body"), PinnedSlide < .001);
	TestTrue(TEXT("the turn is made in a few pivot steps"), Steps >= 2 && Steps <= 10);
	TestTrue(TEXT("both feet step"), Locks[0].GetSteps() > 0 && Locks[1].GetSteps() > 0);
	TestEqual(TEXT("never both feet off the ground at once"), BothStepping, 0);
	TestTrue(TEXT("pivot steps are low"), MaxLift <= 8.);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFootLockWalkTest, "Dink.Animation.Legs.PlantedFoot", DINK_TEST_FLAGS)
bool FDinkFootLockWalkTest::RunTest(const FString&)
{
	// One stance of a walk: the pose's foot drifts 0.5 cm per frame (what the motion capture does), then lifts.
	FDinkFootLock Lock;
	const FDinkFootLockSettings S;
	const float Dt = 1.f / 60.f;
	FVector Prev = FVector::ZeroVector;
	double PinnedSlide = 0, WorstJump = 0;
	for (int32 Frame = 0; Frame < 60; ++Frame)
	{
		FDinkFootLock::FInput In;
		const bool bStance = Frame < 30;
		In.Desired = FVector(Frame * .5, 0, bStance ? 0 : (Frame - 30) * 1.5);
		In.Height = float(In.Desired.Z);
		In.GroundSpeed = bStance ? 30.f * .5f * 0.f + 20.f : 160.f;
		In.bStanding = false;
		const bool bWas = Lock.IsPinned();
		const FDinkFootLock::FOutput Out = Lock.Update(In, Dt, S);
		if (Frame > 0 && bWas && Lock.IsPinned()) PinnedSlide = FMath::Max(PinnedSlide, FVector::Dist2D(Out.Position, Prev));
		if (Frame > 0) WorstJump = FMath::Max(WorstJump, FVector::Dist2D(Out.Position, Prev));
		Prev = Out.Position;
		if (Frame == 29) TestTrue(TEXT("pinned through the stance"), Lock.IsPinned());
		if (Frame == 59) TestTrue(TEXT("let go once lifted, back on the pose's foot"), !Lock.IsPinned() && FVector::Dist2D(Out.Position, In.Desired) < .01);
	}
	AddInfo(FString::Printf(TEXT("STANCE: pinned slide %.4f cm/frame, largest frame-to-frame move of the shown foot %.2f cm"), PinnedSlide, WorstJump));
	TestTrue(TEXT("no slide while planted"), PinnedSlide < .001);
	TestTrue(TEXT("the let-go is a blend, not a jump"), WorstJump < 3.5);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFootPlantCountTest, "Dink.Animation.Legs.FootPlants", DINK_TEST_FLAGS)
bool FDinkFootPlantCountTest::RunTest(const FString&)
{
	const FDinkFootLockSettings S;
	const float Dt = 1.f / 60.f;
	// A reset (a warp, a spawn) followed by a standing pose is no footstep.
	FDinkFootLock Lock;
	Lock.Reset();
	for (int32 I = 0; I < 30; ++I) { FDinkFootLock::FInput In; Lock.Update(In, Dt, S); }
	TestTrue(TEXT("pinned standing after a reset"), Lock.IsPinned());
	TestEqual(TEXT("no footstep without a lifted foot"), Lock.GetPlants(), 0);
	// A walking stance whose ground speed flickers around the lock threshold: one plant, no let-go until the lift.
	FDinkFootLock Walk;
	int32 Releases = 0;
	bool bWasPinned = false;
	for (int32 I = 0; I < 90; ++I)
	{
		FDinkFootLock::FInput In;
		In.bStanding = false;
		const int32 Phase = I % 45;            // 0-14 swing (lifted), 15-44 stance
		In.Height = Phase < 15 ? 8.f : 0.f;
		In.GroundSpeed = Phase < 15 ? 300.f : (I % 2 ? 30.f : 34.f);
		// The pose's foot travels during the swing and stands (in the world) during the stance.
		In.Desired = FVector((I / 45) * 120.f + (Phase < 15 ? Phase * 8.f : 120.f), 0, In.Height);
		Walk.Update(In, Dt, S);
		if (bWasPinned && !Walk.IsPinned() && Phase >= 16) ++Releases;
		bWasPinned = Walk.IsPinned();
	}
	AddInfo(FString::Printf(TEXT("FLICKER: 2 stances, %d plants, %d let-gos inside a stance"), Walk.GetPlants(), Releases));
	TestEqual(TEXT("one footstep per stance"), Walk.GetPlants(), 2);
	TestEqual(TEXT("the pin does not chatter"), Releases, 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGaitStyleTest, "Dink.Animation.Legs.GaitStyle", DINK_TEST_FLAGS)
bool FDinkGaitStyleTest::RunTest(const FString&)
{
	FDinkGaitStyle::Reload();
	const FDinkGaitStyle Timid = FDinkGaitStyle::For(TEXT("Hero"), 0.f), Confident = FDinkGaitStyle::For(TEXT("Hero"), 1.f);
	const FDinkGaitStyle Mother = FDinkGaitStyle::For(TEXT("NpcF"), 1.f), Milder = FDinkGaitStyle::For(TEXT("NpcM"), 1.f);
	AddInfo(FString::Printf(TEXT("STYLE hero timid stride %.2f width %.1f uneven %.2f; confident stride %.2f width %.1f; Mother stride %.2f width %.1f; Milder stride %.2f width %.1f chest %.2f"),
		Timid.Stride, Timid.WidthCm, Timid.Uneven, Confident.Stride, Confident.WidthCm, Mother.Stride, Mother.WidthCm, Milder.Stride, Milder.WidthCm, Milder.ChestSwing));
	TestTrue(TEXT("a timid Dink takes shorter (so quicker) steps than a confident one"), Timid.Stride < Confident.Stride - .05f);
	TestTrue(TEXT("a timid Dink's steps are uneven, a confident one's are not"), Timid.Uneven > .02f && Confident.Uneven < .01f);
	TestTrue(TEXT("Mother takes short steps, narrow under her skirt"), Mother.Stride < .95f && Mother.WidthCm < 0.f);
	TestTrue(TEXT("Milder walks wide with a swagger"), Milder.WidthCm > 2.f && Milder.ChestSwing > 1.3f && Milder.Stride >= 1.f);
	return true;
}

namespace DinkMotionRealismTest
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

	/** Heel and ball of each foot in world space; planted while both are within 1.5 cm of the floor on consecutive frames. */
	struct FWorldSlide
	{
		TArray<double> Slides;
		TArray<int32> SlideFrames;
		int32 Frame = 0;
		FVector Prev[4];
		bool bPrev[4] = {false, false, false, false};
		int32 Bones[2] = {INDEX_NONE, INDEX_NONE};
		FVector Local[4];
		void Init(USkeletalMeshComponent* Mesh)
		{
			const FReferenceSkeleton& Ref = Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
			for (int32 S = 0; S < 2; ++S)
			{
				Bones[S] = Ref.FindBoneIndex(S == 0 ? TEXT("foot_l") : TEXT("foot_r"));
				if (Bones[S] == INDEX_NONE) continue;
				const FTransform Rest = FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, Bones[S]);
				const FVector Ankle = Rest.GetLocation();
				Local[S * 2] = Rest.InverseTransformPosition(FVector(Ankle.X, Ankle.Y - 7.8, 0.));
				Local[S * 2 + 1] = Rest.InverseTransformPosition(FVector(Ankle.X, Ankle.Y + 14.9, 0.));
			}
		}
		void Sample(USkeletalMeshComponent* Mesh)
		{
			++Frame;
			const double Floor = Mesh->GetComponentLocation().Z;
			for (int32 S = 0; S < 2; ++S)
			{
				if (Bones[S] == INDEX_NONE) continue;
				const FTransform Foot = Mesh->GetBoneTransform(Bones[S]);
				const FVector H = Foot.TransformPosition(Local[S * 2]), B = Foot.TransformPosition(Local[S * 2 + 1]);
				const bool bFlat = H.Z - Floor < 1.5 && B.Z - Floor < 1.5;
				if (bFlat && bPrev[S * 2]) { Slides.Add((FVector::Dist2D(H, Prev[S * 2]) + FVector::Dist2D(B, Prev[S * 2 + 1])) * .5); SlideFrames.Add(Frame * 2 + S); }
				Prev[S * 2] = H; Prev[S * 2 + 1] = B;
				bPrev[S * 2] = bPrev[S * 2 + 1] = bFlat;
			}
		}
		double Median() const { if (Slides.IsEmpty()) return 0; TArray<double> C = Slides; C.Sort(); return C[C.Num() / 2]; }
		/** Skims: a foot within 1.5 cm of the floor that moves more than SkimCm in a frame (2.4 m/s) is in its swing, brushing
		 * the floor as it comes down or goes, not standing; the capture does that with the layer off as much as on, so it is
		 * counted on its own and the planted mean is taken without it. */
		static constexpr double SkimCm = 4.0;
		int32 Skims() const { int32 N = 0; for (double D : Slides) N += D > SkimCm; return N; }
		double Mean() const { double T = 0; int32 N = 0; for (double D : Slides) if (D <= SkimCm) { T += D; ++N; } return N ? T / N : 0; }
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkLegLayerEngineTest, "Dink.Animation.Legs.InEngine", DINK_TEST_FLAGS)
bool FDinkLegLayerEngineTest::RunTest(const FString&)
{
	using namespace DinkMotionRealismTest;
	FWorldFixture Fixture;
	UWorld* World = Fixture.World;
	UDinkArtSubsystem* Art = World ? World->GetSubsystem<UDinkArtSubsystem>() : nullptr;
	USkeletalMesh* Hero = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Hero/Refinements/SK_Dink_Hands.SK_Dink_Hands"));
	if (!TestNotNull(TEXT("art subsystem"), Art) || !TestNotNull(TEXT("hero mesh"), Hero) || Art->GetAnimationLibrary().IsEmpty())
		return false;
	IConsoleVariable* Legs = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Anim.Legs"));
	if (!TestNotNull(TEXT("dink.Anim.Legs"), Legs)) return false;
	const int32 LegsBefore = Legs->GetInt();
	ON_SCOPE_EXIT { Legs->Set(LegsBefore, ECVF_SetByCode); };
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
	const float Dt = 1.f / 60.f;
	const int32 Pelvis = Hero->GetRefSkeleton().FindBoneIndex(TEXT("pelvis"));
	auto Step = [&](float Speed, float Confidence, const FVector& Move, float YawDeltaDeg)
	{
		Mesh->SetWorldLocationAndRotation(Mesh->GetComponentLocation() + Move, Mesh->GetComponentRotation() + FRotator(0, YawDeltaDeg, 0));
		Body->SetMotion(Speed, false, Confidence);
		Mesh->TickAnimation(Dt, false);
		Mesh->RefreshBoneTransforms();
	};
	// Walking on flat ground: planted-foot slide in the world with the layer off and on; knee limits; pelvis motion.
	for (const float Confidence : {0.f, 1.f})
		for (const float Speed : {120.f, 170.f, 600.f})
		{
			double Median[2], Mean[2], Cadence[2];
			int32 Skims[2] = {0, 0};
			for (int32 On = 0; On < 2; ++On)
			{
				Legs->Set(On, ECVF_SetByCode);
				Mesh->SetWorldLocationAndRotation(FVector::ZeroVector, FRotator::ZeroRotator);
				FWorldSlide Probe; Probe.Init(Mesh);
				double MinKnee = 1e9, PelvisMin = 1e9, PelvisMax = -1e9, Offset = 0;
				TArray<FDinkLegTelemetry> Seen;
				for (int32 I = 0; I < 30; ++I) Step(0.f, Confidence, FVector::ZeroVector, 0.f);
				for (int32 I = 0; I < 240; ++I)
				{
					// The mesh faces +Y.
					Step(Speed, Confidence, FVector(0, Speed * Dt, 0), 0.f);
					if (I < 60) continue;
					Probe.Sample(Mesh);
					Seen.Add(Body->GetLegTelemetry());
					if (On)
					{
						const FDinkLegTelemetry& T = Body->GetLegTelemetry();
						if (T.bValid) { MinKnee = FMath::Min3(MinKnee, double(T.KneeFlexDeg[0]), double(T.KneeFlexDeg[1])); Offset = FMath::Max(Offset, double(FMath::Abs(T.PelvisOffsetCm))); }
					}
					const double Z = Mesh->GetBoneTransform(Pelvis).GetLocation().Z;
					PelvisMin = FMath::Min(PelvisMin, Z); PelvisMax = FMath::Max(PelvisMax, Z);
				}
				Median[On] = Probe.Median(); Mean[On] = Probe.Mean(); Cadence[On] = Body->GetCyclesPerSecond(); Skims[On] = Probe.Skims();
				if (On && Seen.Num() > 0)
				{
					// Where the slide is: the five largest samples with the foot's pin state on that frame (telemetry lags a frame).
					TArray<int32> Order;
					for (int32 I = 0; I < Probe.Slides.Num(); ++I) Order.Add(I);
					Order.Sort([&Probe](int32 A, int32 B) { return Probe.Slides[A] > Probe.Slides[B]; });
					FString Top;
					for (int32 I = 0; I < FMath::Min(5, Order.Num()); ++I)
					{
						const int32 Code = Probe.SlideFrames[Order[I]], Fr = Code / 2 - 1, Side = Code % 2;
						const FDinkLegTelemetry& Tm = Seen[FMath::Clamp(Fr, 0, Seen.Num() - 1)];
						Top += FString::Printf(TEXT(" %.2fcm@%d%s(state %d w %.2f)"), Probe.Slides[Order[I]], Fr, Side ? TEXT("R") : TEXT("L"), Tm.State[Side], Tm.LockWeight[Side]);
					}
					const FDinkLegTelemetry& Last = Seen.Last();
					AddInfo(FString::Printf(TEXT("LEGS diag speed %.0f conf %.0f: releases lifted %d ran-off %d too-far %d; largest:%s"), Speed, Confidence, Last.Releases[0], Last.Releases[1], Last.Releases[2], *Top));
				}
				AddInfo(FString::Printf(TEXT("LEGS %s confidence %.0f speed %.0f: planted slide median %.3f mean %.3f cm/frame (%d samples, %d skims), cadence %.3f cycles/s, pelvis bob %.1f cm%s"),
					On ? TEXT("on ") : TEXT("off"), Confidence, Speed, Median[On], Mean[On], Probe.Slides.Num(), Skims[On], Cadence[On], PelvisMax - PelvisMin,
					On ? *FString::Printf(TEXT(", least knee flexion %.1f deg, largest pelvis offset %.2f cm"), MinKnee, Offset) : TEXT("")));
				if (On)
				{
					TestTrue(TEXT("no hyperextended knee"), MinKnee >= 0.);
					TestTrue(TEXT("on flat ground the pelvis keeps the clip's height (within 3 cm)"), Offset < 3.);
					TestTrue(TEXT("the pelvis bobs like a person's (1 to 12 cm)"), PelvisMax - PelvisMin > 1. && PelvisMax - PelvisMin < 12.);
				}
			}
			// Walking: the layer holds the feet (warp, pins), so they must slide less. Running: the layer leaves the stance to
			// the capture by design (no warp, no new pins), so it must be no worse; 18-20 samples per run, hence the tolerance.
			if (Speed < 300.f) TestTrue(TEXT("planted feet slide less with the layer than without"), Mean[1] <= Mean[0] + .02);
			else TestTrue(TEXT("a run's feet slide no worse with the layer"), Mean[1] <= Mean[0] * 1.25 + .05);
			TestTrue(TEXT("no more feet brushing the floor with the layer than without"), Skims[1] <= Skims[0] + 2);
			if (Speed < 300.f) TestTrue(TEXT("a walking planted foot holds (mean below 0.25 cm/frame)"), Mean[1] < .25);
			if (Confidence == 0.f && Speed == 170.f) TestTrue(TEXT("a timid Dink steps quicker than the clip at the same speed"), Cadence[1] > Cadence[0] * 1.05);
		}
	// Identity: with nothing to change (flat ground, no pin, no style) the layer shows the clip as it is.
	{
		IConsoleVariable* Lock = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Anim.FootLock"));
		IConsoleVariable* Style = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Anim.Style"));
		const int32 LockBefore = Lock->GetInt(), StyleBefore = Style->GetInt();
		Lock->Set(0, ECVF_SetByCode); Style->Set(0, ECVF_SetByCode);
		const FReferenceSkeleton& Ref = Hero->GetRefSkeleton();
		const int32 T = Ref.FindBoneIndex(TEXT("thigh_l")), K = Ref.FindBoneIndex(TEXT("calf_l")), F = Ref.FindBoneIndex(TEXT("foot_l"));
		for (const float Speed : {0.f, 170.f})
		{
			TArray<double> Knee[2], PelvisZ[2];
			for (int32 On = 0; On < 2; ++On)
			{
				Legs->Set(On, ECVF_SetByCode);
				Body->Configure(Art->GetAnimationLibrary(), TEXT("Hero"));
				Mesh->SetWorldLocationAndRotation(FVector(0, 0, 1000.0 * (On + 1)), FRotator::ZeroRotator);
				for (int32 I = 0; I < 150; ++I)
				{
					Step(Speed, .5f, FVector(0, Speed * Dt, 0), 0.f);
					const FVector Hp = Mesh->GetBoneTransform(T).GetLocation(), Kp = Mesh->GetBoneTransform(K).GetLocation(), Fp = Mesh->GetBoneTransform(F).GetLocation();
					Knee[On].Add(FDinkTwoBoneIK::Flexion(Hp, Kp, Fp, Mesh->GetComponentTransform().TransformVectorNoScale(FVector::YAxisVector)));
					PelvisZ[On].Add(Mesh->GetBoneTransform(Pelvis).GetLocation().Z - Mesh->GetComponentLocation().Z);
				}
			}
			double WorstKnee = 0, WorstPelvis = 0;
			for (int32 I = 5; I < Knee[0].Num(); ++I)
			{
				WorstKnee = FMath::Max(WorstKnee, FMath::Abs(Knee[1][I] - Knee[0][I]));
				WorstPelvis = FMath::Max(WorstPelvis, FMath::Abs(PelvisZ[1][I] - PelvisZ[0][I]));
			}
			AddInfo(FString::Printf(TEXT("IDENTITY at %.0f cm/s, layer on (no pin, no style) against off: worst knee difference %.3f deg, worst pelvis difference %.3f cm"), Speed, WorstKnee, WorstPelvis));
			TestTrue(TEXT("the knees are the clip's (within 0.5 deg)"), WorstKnee < .5);
			TestTrue(TEXT("the pelvis is the clip's (within 0.2 cm)"), WorstPelvis < .2);
		}
		Lock->Set(LockBefore, ECVF_SetByCode); Style->Set(StyleBefore, ECVF_SetByCode);
	}
	// Turning on the spot at the player's turn rate: pivot steps, the planted feet stay put.
	Legs->Set(1, ECVF_SetByCode);
	Mesh->SetWorldLocationAndRotation(FVector::ZeroVector, FRotator::ZeroRotator);
	for (int32 I = 0; I < 40; ++I) Step(0.f, 0.f, FVector::ZeroVector, 0.f);
	const int32 Steps0 = Body->GetLegTelemetry().Steps[0] + Body->GetLegTelemetry().Steps[1];
	int32 Both = 0;
	FVector Last[2];
	double PinnedSlide = 0;
	for (int32 I = 0; I < 120; ++I)
	{
		const FDinkLegTelemetry Prior = Body->GetLegTelemetry();
		Step(0.f, 0.f, FVector::ZeroVector, I < 12 ? 15.f : 0.f);
		Mesh->TickAnimation(0.f, false); // publishes the evaluated telemetry to the game thread
		const FDinkLegTelemetry& T = Body->GetLegTelemetry();
		Both += T.State[0] == 2 && T.State[1] == 2;
		for (int32 F = 0; F < 2; ++F)
		{
			if (I > 0 && Prior.State[F] == 1 && T.State[F] == 1 && Prior.LockWeight[F] > .99f && T.LockWeight[F] > .99f)
				PinnedSlide = FMath::Max(PinnedSlide, FVector::Dist2D(T.FootWorld[F], Last[F]));
			Last[F] = T.FootWorld[F];
		}
	}
	const int32 Steps = Body->GetLegTelemetry().Steps[0] + Body->GetLegTelemetry().Steps[1] - Steps0;
	AddInfo(FString::Printf(TEXT("TURN 180 in place at 900 deg/s (timid): %d pivot steps, pinned ankle slide %.3f cm/frame, frames with both feet stepping %d"), Steps, PinnedSlide, Both));
	TestTrue(TEXT("turning on the spot is done in pivot steps"), Steps >= 2 && Steps <= 10);
	TestTrue(TEXT("a pinned foot stays put while the body turns"), PinnedSlide < .3);
	TestEqual(TEXT("never both feet stepping at once"), Both, 0);
	// Look-at limits, measured on the drawn head: its forward axis (the reference pose's +Y) in the body's frame.
	const int32 HeadBone = Hero->GetRefSkeleton().FindBoneIndex(TEXT("head"));
	const FVector HeadForward = FAnimationRuntime::GetComponentSpaceTransformRefPose(Hero->GetRefSkeleton(), HeadBone).GetRotation().UnrotateVector(FVector::YAxisVector);
	auto HeadAngles = [&](float& OutYaw, float& OutPitch)
	{
		const FVector W = Mesh->GetBoneTransform(HeadBone).GetRotation().RotateVector(HeadForward);
		const FVector L = Mesh->GetComponentTransform().InverseTransformVectorNoScale(W);
		OutYaw = FMath::RadiansToDegrees(FMath::Atan2(float(L.X), float(L.Y)));   // + to the left
		OutPitch = FMath::RadiansToDegrees(FMath::Atan2(float(L.Z), float(FVector(L.X, L.Y, 0).Size())));
	};
	Mesh->SetWorldLocationAndRotation(FVector::ZeroVector, FRotator::ZeroRotator);
	Body->SetLookAt(FVector::ZeroVector, 0.f);
	for (int32 I = 0; I < 5; ++I) Step(0.f, 1.f, FVector::ZeroVector, 0.f);
	float Yaw0 = 0.f, Pitch0 = 0.f;
	HeadAngles(Yaw0, Pitch0);
	struct FCase { FVector Where; float WantYawSign; float WantPitchSign; };
	for (const FCase& Case : {FCase{FVector(300, -200, 160), 1.f, 0.f}, FCase{FVector(-300, 100, 160), -1.f, 0.f}, FCase{FVector(0, 120, -200), 0.f, -1.f}, FCase{FVector(0, 150, 600), 0.f, 1.f}})
	{
		Body->SetLookAt(Mesh->GetComponentTransform().TransformPosition(Case.Where), 1.f);
		for (int32 I = 0; I < 3; ++I) Step(0.f, 1.f, FVector::ZeroVector, 0.f);
		float Yaw = 0.f, Pitch = 0.f;
		HeadAngles(Yaw, Pitch);
		const float DYaw = FMath::FindDeltaAngleDegrees(Yaw0, Yaw), DPitch = Pitch - Pitch0;
		AddInfo(FString::Printf(TEXT("LOOK at %s (component space): drawn head turned %.1f deg (left +), tipped %.1f deg (up +)"), *Case.Where.ToString(), DYaw, DPitch));
		TestTrue(TEXT("the head turns at most 72 degrees"), FMath::Abs(DYaw) <= 72.f);
		TestTrue(TEXT("the head tips at most 32 down and 22 up"), DPitch <= 22.f && DPitch >= -32.f);
		if (Case.WantYawSign != 0.f) TestTrue(TEXT("the head turns towards the target's side, near the limit"), DYaw * Case.WantYawSign > 50.f);
		if (Case.WantPitchSign != 0.f) TestTrue(TEXT("the head tips towards the target"), DPitch * Case.WantPitchSign > 10.f);
	}
	Body->SetLookAt(FVector::ZeroVector, 0.f);
	return true;
}
