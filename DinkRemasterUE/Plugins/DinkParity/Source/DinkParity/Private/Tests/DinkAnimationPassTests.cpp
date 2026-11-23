#include "DinkTestHelpers.h"
#include "DinkBodyAnimInstance.h"
#include "DinkGameplay.h"
#include "DinkHumanoidComponent.h"
#include "DinkHeroPhysicality.h"
#include "Greybox/DinkGreyboxCharacter.h"
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

// The growth arc as numbers: every clumsy chance and rate falls with confidence and is nothing for the
// finished hero; nothing clumsy starts in a fight; the layers that touch the gait add up to no net motion.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHeroMannerismsTest, "Dink.Animation.HeroMannerisms", DINK_TEST_FLAGS)
bool FDinkHeroMannerismsTest::RunTest(const FString&)
{
	using P = FDinkHeroPhysicality;
	const ADinkGreyboxCharacter* Defaults = GetDefault<ADinkGreyboxCharacter>();
	const float RunRate = Defaults->RunTripsPerSecond, WalkRate = Defaults->WalkTripsPerSecond, Botch = Defaults->LandingStumbleChance;
	TestTrue(TEXT("the shipped rates are rare events, not a tic"), RunRate > 0.f && RunRate <= .02f && WalkRate > 0.f && WalkRate <= .01f && Botch >= .15f && Botch <= .4f);
	float Previous[6] = {2.f, 2.f, 2.f, 2.f, 2.f, -1.f};
	for (int32 I = 0; I <= 100; ++I)
	{
		const float C = I / 100.f;
		const float Now[6] = {P::Clumsiness(C), P::TripsPerSecond(600.f, C, RunRate, WalkRate), P::TripsPerSecond(170.f, C, RunRate, WalkRate),
			P::BotchChance(C, Botch), P::FaceplantShare(C), P::FidgetGap(C, .5f)};
		for (int32 K = 0; K < 5; ++K)
			TestTrue(FString::Printf(TEXT("clumsiness %d never rises with confidence (at %.2f)"), K, C), Now[K] <= Previous[K] && Now[K] >= 0.f);
		TestTrue(TEXT("the surer he is the longer he stands still between fidgets"), Now[5] >= Previous[5]);
		FMemory::Memcpy(Previous, Now, sizeof(Now));
	}
	TestEqual(TEXT("new-game Dink is fully clumsy"), P::Clumsiness(0.f), 1.f);
	TestEqual(TEXT("the finished hero never trips running"), P::TripsPerSecond(600.f, 1.f, RunRate, WalkRate), 0.f);
	TestEqual(TEXT("the finished hero never trips walking"), P::TripsPerSecond(170.f, 1.f, RunRate, WalkRate), 0.f);
	TestEqual(TEXT("the finished hero never botches a landing"), P::BotchChance(1.f, 1.f), 0.f);
	TestEqual(TEXT("nobody trips standing still"), P::TripsPerSecond(0.f, 0.f, 1.f, 1.f), 0.f);
	TestTrue(TEXT("the lad trips at a walk and at a run"), P::TripsPerSecond(170.f, 0.f, RunRate, WalkRate) == WalkRate && P::TripsPerSecond(600.f, 0.f, RunRate, WalkRate) == RunRate);
	TestTrue(TEXT("bad input counts as the lad, not as a crash"), P::Clumsiness(NAN) == 1.f && P::BotchChance(NAN, .3f) == .3f);
	TestTrue(TEXT("half-way he is already much steadier"), P::Clumsiness(.5f) < .4f && P::Clumsiness(.5f) > .2f);

	// Simulated walking: an hour at each confidence, at an exaggerated rate so the counts mean something.
	int32 LastTrips = MAX_int32;
	for (const float C : {0.f, .25f, .5f, .75f, 1.f})
	{
		P Walker; Walker.SetTargetConfidence(C, true);
		int32 Trips = 0; float Gap = 1.e9f, SinceLast = 1.e9f;
		for (int32 I = 0; I < 60 * 3600; ++I)
		{
			const bool Was = Walker.IsStumbling();
			Walker.Update(1.f / 60.f, 170.f, true, true, 0.f, .05f, .05f);
			SinceLast += 1.f / 60.f;
			if (!Was && Walker.IsStumbling()) { ++Trips; Gap = FMath::Min(Gap, SinceLast); SinceLast = 0.f; }
		}
		AddInfo(FString::Printf(TEXT("confidence %.2f: %d toe catches in an hour of walking at ten times the shipped rate"), C, Trips));
		TestTrue(TEXT("fewer toe catches at every stage"), Trips <= LastTrips);
		if (Trips > 1) TestTrue(TEXT("never two in quick succession"), Gap >= P::TripCooldown);
		if (C == 0.f) TestTrue(TEXT("the lad does catch a toe walking"), Trips > 20);
		if (C == 1.f) TestEqual(TEXT("the hero never does"), Trips, 0);
		LastTrips = Trips;
	}
	// In a fight: an attack or a blow every few seconds keeps every clumsy moment away.
	{
		P Fighter;
		int32 Trips = 0, Botches = 0, Fidgets = 0;
		FVector2f Roll;
		for (int32 I = 0; I < 60 * 600; ++I)
		{
			if (I % 240 == 0) Fighter.NotifyCombat();
			Fighter.Update(1.f / 60.f, I % 1200 < 600 ? 600.f : 0.f, true, true, 0.f, 1.f, 1.f);
			Trips += Fighter.ConsumeStumbleStart();
			if (I % 90 == 0) Botches += Fighter.Land(400.f, .4f, 1.f);
			Fidgets += Fighter.ConsumeFidget(Roll);
		}
		TestEqual(TEXT("no toe catch during a fight, whatever the rate"), Trips, 0);
		TestEqual(TEXT("no botched landing during a fight, whatever the chance"), Botches, 0);
		TestEqual(TEXT("no fidget during a fight"), Fidgets, 0);
		for (int32 I = 0; I < 60 * 7; ++I) Fighter.Update(1.f / 60.f, 0.f, true, true);
		TestFalse(TEXT("the quiet ends a few seconds after the fight"), Fighter.IsCombatQuiet());
	}
	// Landings: 2000 jumps at each confidence.
	int32 LastBotches = MAX_int32, LastFlat = MAX_int32 - 16;
	for (const float C : {0.f, .25f, .5f, .75f, 1.f})
	{
		P Jumper; Jumper.SetTargetConfidence(C, true);
		int32 Botches = 0, Flat = 0;
		for (int32 I = 0; I < 2000; ++I)
		{
			if (Jumper.Land(400.f, .4f, P::BotchChance(C, Botch))) { ++Botches; Flat += Jumper.GetBotch() == P::EBotch::Faceplant; }
			Jumper.Update(6.f, 0.f, true, true);
		}
		AddInfo(FString::Printf(TEXT("confidence %.2f: %d of 2000 landings botched, %d of them flat on his face"), C, Botches, Flat));
		TestTrue(TEXT("fewer botched landings at every stage"), Botches <= LastBotches && Flat <= LastFlat + 5);
		if (C == 0.f) TestTrue(TEXT("the lad botches some landings, and most of those are staggers"), Botches > 400 && Botches < 800 && Flat > 100 && Flat < Botches / 2 + 40);
		if (C == 1.f) TestEqual(TEXT("the hero lands clean every time"), Botches, 0);
		LastBotches = Botches; LastFlat = Flat;
	}
	// Fidgets: a minute and a half of standing about.
	int32 LadFidgets = 0, HeroFidgets = 0, MovingFidgets = 0;
	{
		P Lad, Hero, Walker; Hero.SetTargetConfidence(1.f, true);
		FVector2f Roll;
		for (int32 I = 0; I < 60 * 90; ++I)
		{
			Lad.Update(1.f / 60.f, 0.f, true, true); Hero.Update(1.f / 60.f, 0.f, true, true); Walker.Update(1.f / 60.f, 170.f, true, true);
			LadFidgets += Lad.ConsumeFidget(Roll); HeroFidgets += Hero.ConsumeFidget(Roll); MovingFidgets += Walker.ConsumeFidget(Roll);
			TestTrue(TEXT("fidget draws are 0..1"), Roll.X >= 0.f && Roll.X <= 1.f && Roll.Y >= 0.f && Roll.Y <= 1.f);
		}
	}
	AddInfo(FString::Printf(TEXT("90 s standing: the lad fidgets %d times, the hero %d"), LadFidgets, HeroFidgets));
	TestTrue(TEXT("the lad cannot stand still"), LadFidgets >= 7 && LadFidgets <= 19);
	TestTrue(TEXT("the hero stands planted"), HeroFidgets >= 1 && HeroFidgets <= 5);
	TestEqual(TEXT("nobody fidgets while walking"), MovingFidgets, 0);
	// The after-swing wobble.
	{
		P Lad, Hero; Hero.SetTargetConfidence(1.f, true);
		Lad.Update(1.f / 60.f, 0.f, true, true); Hero.Update(1.f / 60.f, 0.f, true, true);
		Lad.KickWobble(1.f); Hero.KickWobble(1.f);
		float Peak = 0.f, HeroPeak = 0.f; int32 Swings = 0; float LastSign = 0.f;
		for (int32 I = 0; I < 150; ++I)
		{
			Lad.Update(1.f / 60.f, 0.f, true, true); Hero.Update(1.f / 60.f, 0.f, true, true);
			Peak = FMath::Max(Peak, Lad.GetWobble().Size()); HeroPeak = FMath::Max(HeroPeak, Hero.GetWobble().Size());
			const float Sign = FMath::Sign(Lad.GetWobble().X);
			if (Sign != 0.f && Sign != LastSign) { ++Swings; LastSign = Sign; }
		}
		AddInfo(FString::Printf(TEXT("after-swing wobble of the lad: peak %.1f degrees, %d swings, %.2f degrees left after 2.5 s"), Peak, Swings, Lad.GetWobble().Size()));
		TestTrue(TEXT("the lad rocks visibly but not wildly after a swing"), Peak > 2.5f && Peak < 8.f && Swings >= 3);
		TestTrue(TEXT("and has settled within a few seconds"), Lad.GetWobble().Size() < .15f);
		TestEqual(TEXT("the hero does not rock at all"), HeroPeak, 0.f);
	}
	// The gait layer: no net change of the step, nothing for the hero, nothing standing.
	double Covered = 0.;
	for (int32 I = 0; I < 3600; ++I) Covered += FDinkMannerMaths::CatchCadence((I + .5f) / 3600.f) / 3600.;
	TestTrue(FString::Printf(TEXT("a toe catch loses no ground in the end (%.4f of a second of cadence in one second)"), Covered), FMath::IsNearlyEqual(Covered, 1., 1e-3));
	TestTrue(TEXT("the foot hangs first, then hurries"), FDinkMannerMaths::CatchCadence(.05f) < .3f && FDinkMannerMaths::CatchCadence(.25f) > 1.3f && FDinkMannerMaths::CatchCadence(1.f) == 1.f);
	float Left = 0.f, Right = 0.f, Mean = 0.f;
	for (int32 I = 0; I < 360; ++I)
	{
		const float Roll = FDinkMannerMaths::GaitRoll(I / 360.f, 1.f, 1.f, 0.f);
		Left = FMath::Max(Left, Roll); Right = FMath::Max(Right, -Roll); Mean += Roll / 360.f;
		TestEqual(TEXT("the hero's trunk does not rock"), FDinkMannerMaths::GaitRoll(I / 360.f, 0.f, 1.f, 1.f), 0.f);
		TestEqual(TEXT("nor does anyone's standing still"), FDinkMannerMaths::GaitRoll(I / 360.f, 1.f, 0.f, 0.f), 0.f);
	}
	AddInfo(FString::Printf(TEXT("timid walk trunk rock: %.1f degrees one way, %.1f the other"), Left, Right));
	TestTrue(TEXT("the lad rocks further over one foot than the other, a few degrees"), Left > 1.5f && Right > 1.5f && Left < 5.f && Right < 5.f && FMath::Abs(Left - Right) > .8f && FMath::Abs(Mean) < .01f);
	TestTrue(TEXT("his arms hang, the left more than the right, less so at a run; the hero's swing"),
		FDinkMannerMaths::ArmSwingDamping(1.f, 1.f, 0.f).X > FDinkMannerMaths::ArmSwingDamping(1.f, 1.f, 0.f).Y &&
		FDinkMannerMaths::ArmSwingDamping(1.f, 1.f, 1.f).X < FDinkMannerMaths::ArmSwingDamping(1.f, 1.f, 0.f).X &&
		FDinkMannerMaths::ArmSwingDamping(0.f, 1.f, 0.f).IsNearlyZero() && FDinkMannerMaths::ArmSwingDamping(1.f, 1.f, 0.f).X <= .7f);
	TestTrue(TEXT("the lad takes shorter, quicker steps at a walk than the hero"),
		FDinkMannerMaths::CadencePower(.7f, 0.f) < FDinkMannerMaths::CadencePower(.7f, .5f) && FDinkMannerMaths::CadencePower(.7f, .5f) < FDinkMannerMaths::CadencePower(.7f, 1.f));
	{
		// The same walk, 170 cm/s, taken by the lad and by the hero: stride times cadence is the speed for both.
		const float Speeds[] = {273.f}, Strides[] = {204.75f};
		float Stride[2];
		for (int32 K = 0; K < 2; ++K)
		{
			float Idle = 0.f, Cycles = 0.f; TArray<float, TInlineAllocator<4>> W;
			FDinkGaitBlend::Solve(170.f, Speeds, Strides, Idle, W, Cycles, FDinkMannerMaths::CadencePower(.7f, float(K)));
			Stride[K] = FMath::Pow(W[0], FDinkGaitBlend::SlowStridePower) * Strides[0];
			TestTrue(TEXT("no sliding at either end of the arc"), FMath::IsNearlyEqual(Stride[K] * Cycles, 170.f, .5f));
		}
		AddInfo(FString::Printf(TEXT("walking at 170 cm/s: the lad's gait cycle covers %.0f cm, the hero's %.0f cm"), Stride[0], Stride[1]));
		TestTrue(TEXT("the lad's step is clearly shorter"), Stride[0] < Stride[1] - 12.f);
	}
	TestTrue(TEXT("older action clips keep only part of the posture layer, new ones all of it"),
		FDinkMannerMaths::PostureShareFor(TEXT("Fist_Jab")) < 1.f && FDinkMannerMaths::PostureShareFor(TEXT("Sword_Chop")) < 1.f &&
		FDinkMannerMaths::PostureShareFor(TEXT("Fidget_Scuff")) == 1.f && FDinkMannerMaths::PostureShareFor(TEXT("Botch_Stagger")) == 1.f);
	return true;
}
