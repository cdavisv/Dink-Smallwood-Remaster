#include "DinkTestHelpers.h"
#include "DinkBodyAnimInstance.h"
#include "DinkGameplay.h"
#include "DinkHumanoidComponent.h"
#include "DinkPlayerActionComponent.h"
#include "DinkMotionEstimate.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAttackGateTest, "Dink.Animation.AttackGate", DINK_TEST_FLAGS)
bool FDinkAttackGateTest::RunTest(const FString&)
{
	using EPress = FDinkAttackGate::EPress;
	FDinkAttackGate Gate;
	TestTrue(TEXT("a press while idle starts an attack"), Gate.Press(1000.) == EPress::Start);
	Gate.Started(1000., 400.);
	int32 Repeats = 0;
	for (double T = 1000.; T < 6000.; T += 16.)
	{
		// The key stays down: OS auto-repeat keeps sending key-downs, the game keeps ticking.
		if (Gate.Press(T) != EPress::Ignored) ++Repeats;
		if (Gate.TakeBuffered(T)) ++Repeats;
	}
	TestEqual(TEXT("a held key never repeats, at any cadence"), Repeats, 0);
	Gate.Release();
	TestTrue(TEXT("after the lock a new press starts at once"), Gate.Press(6000.) == EPress::Start);
	Gate.Started(6000., 400.);
	Gate.Release();
	TestTrue(TEXT("a press during the lock is remembered"), Gate.Press(6100.) == EPress::Buffered && Gate.HasBuffered());
	Gate.Release();
	TestTrue(TEXT("more presses during the same lock do not stack"), Gate.Press(6200.) == EPress::Buffered);
	Gate.Release();
	TestFalse(TEXT("the remembered press waits for the lock"), Gate.TakeBuffered(6399.));
	TestTrue(TEXT("it starts the moment the lock ends"), Gate.TakeBuffered(6400.));
	Gate.Started(6400., 400.);
	TestFalse(TEXT("and only once"), Gate.TakeBuffered(6800.) || Gate.TakeBuffered(9000.));
	TestTrue(TEXT("the combo window: next press right at the lock's end starts"), Gate.Press(6800.) == EPress::Start);
	Gate.Started(6800., 0.);
	Gate.Release();
	TestTrue(TEXT("an item without an attack sequence does not lock"), Gate.Press(6800.) == EPress::Start);
	Gate.Reset();
	TestTrue(TEXT("reset forgets everything"), !Gate.IsHeld() && !Gate.HasBuffered() && !Gate.IsLocked(0.));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAttackComboTest, "Dink.Animation.Combo", DINK_TEST_FLAGS)
bool FDinkAttackComboTest::RunTest(const FString&)
{
	FDinkAttackCombo Combo;
	Combo.WindowSeconds = .95f;
	const FName Fist(TEXT("Fist")), Sword(TEXT("Sword"));
	TestEqual(TEXT("first attack"), Combo.Advance(10., Fist), 0);
	TestEqual(TEXT("second, 0.4 s later"), Combo.Advance(10.4, Fist), 1);
	TestEqual(TEXT("third"), Combo.Advance(10.8, Fist), 2);
	TestEqual(TEXT("wraps"), Combo.Advance(11.2, Fist), 0);
	TestEqual(TEXT("a pause resets the combo"), Combo.Advance(12.5, Fist), 0);
	TestEqual(TEXT("continues again"), Combo.Advance(13., Fist), 1);
	TestEqual(TEXT("changing weapon restarts"), Combo.Advance(13.3, Sword), 0);
	TestEqual(TEXT("a clock that went back (load) restarts"), Combo.Advance(2., Sword), 0);
	TestEqual(TEXT("fists: jab"), UDinkPlayerActionComponent::ClipFor(TEXT("item-fst"), 0), FName(TEXT("Fist_Jab")));
	TestEqual(TEXT("fists: cross"), UDinkPlayerActionComponent::ClipFor(TEXT("item-fst"), 1), FName(TEXT("Fist_Cross")));
	TestEqual(TEXT("fists: swing"), UDinkPlayerActionComponent::ClipFor(TEXT("item-fst"), 2), FName(TEXT("Fist_Swing")));
	TestEqual(TEXT("every sword uses the sword cuts"), UDinkPlayerActionComponent::ClipFor(TEXT("item-sw3"), 2), FName(TEXT("Sword_Chop")));
	TestTrue(TEXT("bow and magic have no melee clip"), UDinkPlayerActionComponent::ClipFor(TEXT("item-b1"), 0).IsNone() &&
		UDinkPlayerActionComponent::ClipFor(TEXT("magic"), 0).IsNone());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGaitBlendTest, "Dink.Animation.GaitBlend", DINK_TEST_FLAGS)
bool FDinkGaitBlendTest::RunTest(const FString&)
{
	const float Speeds[] = {90.f, 200.f, 600.f}, Strides[] = {90.f, 150.f, 350.f};
	for (float Speed = 0.f; Speed <= 800.f; Speed += 12.5f)
	{
		float Idle = 0.f, Cycles = 0.f;
		TArray<float, TInlineAllocator<4>> W;
		FDinkGaitBlend::Solve(Speed, Speeds, Strides, Idle, W, Cycles);
		float Sum = Idle, Stride = 0.f;
		// The stride a mix covers: weighted between gaits; below the slowest gait the mix with the standing pose covers W^SlowStridePower of it.
		for (int32 I = 0; I < W.Num(); ++I) { Sum += W[I]; Stride += (Idle > 0.f ? FMath::Pow(W[I], FDinkGaitBlend::SlowStridePower) : W[I]) * Strides[I]; TestTrue(TEXT("weights are 0..1"), W[I] >= 0.f && W[I] <= 1.f); }
		TestTrue(TEXT("weights sum to one"), FMath::IsNearlyEqual(Sum, 1.f, 1e-4f));
		// Stride of the blended pose (idle contributes none) times the cadence must be the speed: no sliding.
		if (Speed >= 1.f) TestTrue(FString::Printf(TEXT("stride matches speed at %.1f cm/s"), Speed), FMath::IsNearlyEqual(Stride * Cycles, Speed, .01f * FMath::Max(Speed, 1.f)));
		else TestTrue(TEXT("standing still is the idle alone"), Idle == 1.f && Cycles == 0.f);
	}
	float Idle = 0.f, Cycles = 0.f;
	TArray<float, TInlineAllocator<4>> W;
	FDinkGaitBlend::Solve(600.f, Speeds, Strides, Idle, W, Cycles);
	TestTrue(TEXT("the run speed is the run clip alone"), W[2] == 1.f && W[0] == 0.f && W[1] == 0.f);
	FDinkGaitBlend::Solve(NAN, Speeds, Strides, Idle, W, Cycles);
	TestTrue(TEXT("a bad speed stands still"), Idle == 1.f);
	return true;
}

namespace DinkNpcPresentation
{
	/** The trailing follower of animation pass 1 (removed in pass 2), kept here only so the test can measure what it did. */
	struct FRoundOneFollower
	{
		float ComfortSpeed = 125.f, MaxLag = 180.f, Acceleration = 420.f, Deceleration = 380.f, Speed = 0.f;
		FVector Visual = FVector::ZeroVector;
		FVector Update(const FVector& Target, float TargetSpeed, float Dt)
		{
			FVector To = Target - Visual; To.Z = 0.;
			const float Distance = float(To.Size());
			float Desired = Distance > .5f ? ComfortSpeed : 0.f;
			Desired = FMath::Min(Desired, FMath::Sqrt(2.f * Deceleration * Distance));
			const float Hurry = FMath::SmoothStep(MaxLag * .7f, MaxLag, Distance);
			Desired = FMath::Max(Desired, FMath::Lerp(Desired, TargetSpeed, Hurry) + FMath::Max(0.f, Distance - MaxLag) * 3.f);
			Speed = FMath::FInterpConstantTo(Speed, Desired, Dt, Desired > Speed ? Acceleration : Deceleration);
			if (Distance > KINDA_SMALL_NUMBER) Visual += To / Distance * FMath::Min(Speed * Dt, Distance);
			return Visual;
		}
	};

	/** The scripted position of a wandering townsperson, as the brains produce it: whole pixels on 60 Hz engine frames. */
	struct FScript
	{
		double CmPerPixel = 4.375, Pace = 1., Carry = 0.;
		int32 Frames = 0; FIntPoint Pixel = FIntPoint(300, 200);
		/** Walks east for 4 s, stands 1.5 s, walks south-east for 4 s, stands 1.5 s (in engine frames; a paced sprite takes a share of them). */
		void RunTo(double Seconds)
		{
			while ((Frames + 1) / 60. <= Seconds)
			{
				++Frames;
				const double T = FMath::Fmod(Frames / 60., 11.);
				const FIntPoint Step = T < 4. ? FIntPoint(1, 0) : (T < 5.5 ? FIntPoint(0, 0) : (T < 9.5 ? FIntPoint(1, 1) : FIntPoint(0, 0)));
				Carry += Pace;
				if (Carry >= 1.) { Carry -= 1.; Pixel += Step; }
			}
		}
		/** Steady walking due east (the diagonal leg is 1.41 times faster, as in the original, and is left out of the statistics). */
		bool Walking(double Seconds) const { const double T = FMath::Fmod(Seconds, 11.); return T > .9 && T < 3.6; }
		FVector Location() const { return FVector(Pixel.X * CmPerPixel, Pixel.Y * CmPerPixel, 0.); }
	};

	struct FJitter { double Mean = 0, Deviation = 0, WorstChange = 0, Still = 0; int32 Samples = 0; };

	/** Frame-to-frame speed of the shown body while the script walks steadily, at a render frame rate. */
	template <typename PresenterType>
	FJitter Measure(double Pace, double Fps, PresenterType&& Present)
	{
		FScript Script; Script.Pace = Pace;
		FDinkMotionEstimate Estimate;
		TArray<double> Speeds;
		FVector Previous = Script.Location();
		double PreviousSpeed = 0; FJitter Out; int32 StillFrames = 0;
		const double Dt = 1. / Fps;
		for (int32 I = 1; I * Dt < 22.; ++I)
		{
			Script.RunTo(I * Dt);
			const float Observed = Estimate.Update(Script.Location(), float(Dt));
			const FVector Body = Present(Script.Location(), Observed, float(Dt));
			const double Speed = FVector::Dist2D(Body, Previous) / Dt;
			if (Script.Walking(I * Dt) && Script.Walking((I - 1) * Dt))
			{
				Speeds.Add(Speed);
				Out.WorstChange = FMath::Max(Out.WorstChange, FMath::Abs(Speed - PreviousSpeed));
				StillFrames += Speed < 1.;
			}
			Previous = Body; PreviousSpeed = Speed;
		}
		for (const double V : Speeds) Out.Mean += V / Speeds.Num();
		for (const double V : Speeds) Out.Deviation += FMath::Square(V - Out.Mean) / Speeds.Num();
		Out.Deviation = FMath::Sqrt(Out.Deviation); Out.Samples = Speeds.Num(); Out.Still = double(StillFrames) / FMath::Max(1, Speeds.Num());
		return Out;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNpcSmoothPresentationTest, "Dink.Animation.NpcSmoothPresentation", DINK_TEST_FLAGS)
bool FDinkNpcSmoothPresentationTest::RunTest(const FString&)
{
	using namespace DinkNpcPresentation;
	const double HumanPace = 120. / (60. * 4.375); // Mother: 120 cm/s instead of 262.5
	for (const double Fps : {60., 144., 47.})
	{
		const FJitter Glued = Measure(1., Fps, [](const FVector& P, float, float) { return P; });
		FRoundOneFollower Old; Old.Visual = FScript().Location();
		const FJitter RoundOne = Measure(1., Fps, [&Old](const FVector& P, float Speed, float Dt) { return Old.Update(P, Speed, Dt); });
		const FJitter GluedPaced = Measure(HumanPace, Fps, [](const FVector& P, float, float) { return P; });
		FDinkBodySmoother Smoother; Smoother.Reset(FScript().Location(), 0.f);
		const FJitter Now = Measure(HumanPace, Fps, [&Smoother](const FVector& P, float, float Dt) { return Smoother.Update(P, 0.f, Dt); });
		auto Row = [this, Fps](const TCHAR* Name, const FJitter& J)
		{
			AddInfo(FString::Printf(TEXT("JITTER %3.0f fps %-34s mean %6.1f cm/s, deviation %6.1f, worst frame-to-frame change %6.1f, frames standing still %4.1f%%"),
				Fps, Name, J.Mean, J.Deviation, J.WorstChange, J.Still * 100.));
		};
		Row(TEXT("pass 0: body glued, original speed"), Glued);
		Row(TEXT("pass 1: trailing follower"), RoundOne);
		Row(TEXT("pass 2 script pace, body glued"), GluedPaced);
		Row(TEXT("pass 2: human pace, smoothed"), Now);
		TestTrue(TEXT("she walks at her walking pace"), FMath::IsNearlyEqual(Now.Mean, 120., 4.));
		TestTrue(TEXT("steady scripted walking is shown as steady motion at every frame rate"), Now.Deviation < 3. && Now.WorstChange < 10. && Now.Still == 0.);
		TestTrue(TEXT("and far steadier than pass 1 or the glued body"), Now.Deviation < .1 * RoundOne.Deviation + 1. && Now.Deviation < .1 * GluedPaced.Deviation + 1.);
	}

	// Mother's opening walk with the human pace: the script now moves her 43 px (1.88 m) at 120 cm/s (continuous, 1.57 s).
	const float Dt = 1.f / 60.f;
	FDinkBodySmoother Mother;
	FVector Script = FVector::ZeroVector;
	Mother.Reset(Script, 90.f);
	FString Series; float Peak = 0.f, Arrived = -1.f, PeakLag = 0.f;
	for (int32 I = 1; I <= 240; ++I)
	{
		const float T = I * Dt;
		Script.Y = FMath::Min(188.1f, 120.f * T);
		Mother.Update(Script, 90.f, Dt);
		Peak = FMath::Max(Peak, Mother.GetSpeed()); PeakLag = FMath::Max(PeakLag, Mother.GetLag(Script));
		if (I % 12 == 0 && T <= 2.61f) Series += FString::Printf(TEXT("%.1fs:%.0f "), T, Mother.GetSpeed());
		if (Arrived < 0.f && T > 1.f && Mother.GetLag(Script) < 1.f) Arrived = T;
		if (T > .7f && T < 1.4f) TestTrue(TEXT("she holds a constant walking speed in the middle"), FMath::IsNearlyEqual(Mother.GetSpeed(), 120.f, 3.f));
	}
	AddInfo(FString::Printf(TEXT("OPENING WALK body speed cm/s: %s; peak %.0f, arrives after %.2f s, trails by at most %.0f cm"), *Series, Peak, Arrived, PeakLag));
	TestTrue(TEXT("she ramps up, never exceeds the script's pace and ramps down to a stop"), Peak <= 122.f && Arrived > 1.6f && Arrived < 2.6f && Mother.GetSpeed() < 1.f);
	TestTrue(TEXT("the body stays close behind the script"), PeakLag < 30.f);

	const FVector Held = Mother.GetLocation();
	Mother.Update(Script + FVector(0, 30, 0), 90.f, 0.f);
	TestTrue(TEXT("a paused frame moves nothing"), Mother.GetLocation().Equals(Held));
	Mother.Update(Script + FVector(5000, 0, 0), 90.f, Dt);
	TestTrue(TEXT("a warp snaps the body to the script"), Mother.GetLag(Script + FVector(5000, 0, 0)) < .01f);
	FDinkBodySmoother Turn; Turn.Reset(FVector::ZeroVector, 0.f);
	Turn.Update(FVector::ZeroVector, 180.f, Dt);
	TestTrue(TEXT("a new facing is approached at the turn rate"), FMath::Abs(Turn.GetYaw()) > 1.f && FMath::Abs(Turn.GetYaw()) < 10.f);
	for (int32 I = 0; I < 60; ++I) Turn.Update(FVector::ZeroVector, 180.f, Dt);
	TestTrue(TEXT("and reached"), FMath::IsNearlyEqual(FMath::Abs(Turn.GetYaw()), 180.f, .5f));
	FDinkBodySmoother Off; Off.SmoothTime = 0.f; Off.Reset(FVector::ZeroVector, 0.f);
	Off.Update(FVector(50, 0, 0), 30.f, Dt);
	TestTrue(TEXT("smoothing off: the body is glued to the script"), Off.GetLag(FVector(50, 0, 0)) < .01f && Off.GetYaw() == 30.f);
	return true;
}

#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"

namespace DinkAnimProbe
{
	/** Component-space transform of a skeleton bone at Time, straight from the sequence (no mesh needed). */
	FTransform BoneCS(const UAnimSequence* Seq, const FReferenceSkeleton& Ref, int32 Bone, double Time)
	{
		FTransform Out = FTransform::Identity;
		for (int32 B = Bone; B != INDEX_NONE; B = Ref.GetParentIndex(B))
		{
			FTransform Local;
			Seq->GetBoneTransform(Local, FSkeletonPoseBoneIndex(B), FAnimExtractContext(Time, false), false);
			Out = Out * Local;
		}
		return Out;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNaturalClipSurveyTest, "Dink.Animation.NaturalClipSurvey", DINK_TEST_FLAGS)
bool FDinkNaturalClipSurveyTest::RunTest(const FString&)
{
	// Measures the template's motion-capture clips the runtime plays: length, the ground speed their
	// planted feet imply (so the runtime can match stride to movement) and where the left heel lands.
	const TCHAR* Base = TEXT("/Game/Characters/Mannequins/Anims/Unarmed/");
	for (const TCHAR* Name : {TEXT("MM_Idle"), TEXT("Walk/MF_Unarmed_Walk_Fwd"), TEXT("Jog/MF_Unarmed_Jog_Fwd"), TEXT("Jump/MM_Jump"), TEXT("Jump/MM_Fall_Loop"),
		TEXT("Jump/MM_Land"), TEXT("Attack/MM_Attack_01"), TEXT("Attack/MM_Attack_02"), TEXT("Attack/MM_Attack_03"), TEXT("Attack/MM_ChargedAttack")})
	{
		const FString Leaf = FPaths::GetCleanFilename(Name);
		UAnimSequence* Seq = LoadObject<UAnimSequence>(nullptr, *(FString(Base) + Name + TEXT(".") + Leaf));
		if (!Seq) { AddInfo(FString::Printf(TEXT("NATURAL %s: not present"), Name)); continue; }
		const FReferenceSkeleton& Ref = Seq->GetSkeleton()->GetReferenceSkeleton();
		const int32 FootL = Ref.FindBoneIndex(TEXT("foot_l")), FootR = Ref.FindBoneIndex(TEXT("foot_r")), Root = Ref.FindBoneIndex(TEXT("root"));
		const int32 HandL = Ref.FindBoneIndex(TEXT("hand_l")), HandR = Ref.FindBoneIndex(TEXT("hand_r")), Pelvis = Ref.FindBoneIndex(TEXT("pelvis"));
		const double Length = Seq->GetPlayLength();
		const int32 N = FMath::Max(8, FMath::RoundToInt32(Length * 120.));
		double MinZ = 1e9;
		TArray<FVector> L, R;
		double RootTravel = 0, ReachL = -1e9, ReachR = -1e9, ReachLT = 0, ReachRT = 0;
		for (int32 I = 0; I <= N; ++I)
		{
			const double T = Length * I / N;
			const FVector RootAt = DinkAnimProbe::BoneCS(Seq, Ref, Root, T).GetLocation();
			L.Add(DinkAnimProbe::BoneCS(Seq, Ref, FootL, T).GetLocation() - RootAt);
			R.Add(DinkAnimProbe::BoneCS(Seq, Ref, FootR, T).GetLocation() - RootAt);
			MinZ = FMath::Min3(MinZ, L.Last().Z, R.Last().Z);
			RootTravel = FMath::Max(RootTravel, DinkAnimProbe::BoneCS(Seq, Ref, Root, T).GetLocation().Size());
			const FVector P = DinkAnimProbe::BoneCS(Seq, Ref, Pelvis, T).GetLocation();
			const double RL = DinkAnimProbe::BoneCS(Seq, Ref, HandL, T).GetLocation().Y - P.Y, RR = DinkAnimProbe::BoneCS(Seq, Ref, HandR, T).GetLocation().Y - P.Y;
			if (RL > ReachL) { ReachL = RL; ReachLT = T; }
			if (RR > ReachR) { ReachR = RR; ReachRT = T; }
		}
		// A foot is planted while its ankle is within 1.5 cm of the lowest ankle height of the clip.
		double Sum = 0; int32 Count = 0, Strikes = 0; double LeftStrike = -1;
		for (int32 I = 1; I <= N; ++I)
		{
			const double Dt = Length / N;
			for (const TArray<FVector>* Foot : {&L, &R})
				if ((*Foot)[I].Z < MinZ + 1.5 && (*Foot)[I - 1].Z < MinZ + 1.5) { Sum += -((*Foot)[I].Y - (*Foot)[I - 1].Y) / Dt; ++Count; }
			// A stride begins where the left foot passes the right one going forward.
			if ((L[I].Y - R[I].Y) > 0. && (L[I - 1].Y - R[I - 1].Y) <= 0.) { ++Strikes; if (LeftStrike < 0) LeftStrike = Length * I / N; }
		}
		const double Speed = Count ? Sum / Count : 0.;
		AddInfo(FString::Printf(TEXT("NATURAL %s: length %.4f s, planted-foot ground speed %.1f cm/s, stride %.1f cm, left heel strike at %.3f s (phase %.3f), left strides %d, root travel %.1f cm, root motion %d, hand reach L %.0f cm at %.2f s, R %.0f cm at %.2f s"),
			*Leaf, Length, Speed, Speed * Length, LeftStrike, LeftStrike >= 0 ? LeftStrike / Length : -1., Strikes, RootTravel, Seq->HasRootMotion() ? 1 : 0, ReachL, ReachLT, ReachR, ReachRT));
	}
	return true;
}
