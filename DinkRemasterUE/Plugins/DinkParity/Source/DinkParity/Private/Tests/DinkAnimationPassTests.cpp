#include "DinkTestHelpers.h"
#include "DinkBodyAnimInstance.h"
#include "DinkGameplay.h"
#include "DinkHumanoidComponent.h"
#include "DinkPlayerActionComponent.h"

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
		for (int32 I = 0; I < W.Num(); ++I) { Sum += W[I]; Stride += W[I] * Strides[I]; TestTrue(TEXT("weights are 0..1"), W[I] >= 0.f && W[I] <= 1.f); }
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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNpcFollowerTest, "Dink.Animation.NpcFollower", DINK_TEST_FLAGS)
bool FDinkNpcFollowerTest::RunTest(const FString&)
{
	const float Dt = 1.f / 60.f;
	// Mother's opening walk: the script moves her 43 px (1.88 m) at sp_speed 1 = 262.5 cm/s in her 4.375 cm/px house.
	FDinkVisualFollower Mother;
	Mother.ComfortSpeed = 125.f; Mother.MaxLag = 180.f;
	FVector Script(0, 0, 0);
	Mother.Reset(Script, 90.f);
	float Peak = 0.f, PeakLag = 0.f, Arrived = -1.f, PeakStep = 0.f;
	FVector Previous = Script;
	for (int32 I = 0; I < 360; ++I)
	{
		const float T = I * Dt;
		const float ScriptSpeed = T < .7167f ? 262.5f : 0.f;
		Script.Y = FMath::Min(188.1f, 262.5f * T);
		const FVector Body = Mother.Update(Script, 90.f, ScriptSpeed, Dt);
		Peak = FMath::Max(Peak, Mother.GetSpeed());
		PeakLag = FMath::Max(PeakLag, Mother.GetLag(Script));
		PeakStep = FMath::Max(PeakStep, float(FVector::Dist(Body, Previous)) / Dt);
		Previous = Body;
		if (Arrived < 0.f && Mother.GetLag(Script) < 1.f && T > .5f) Arrived = T;
	}
	AddInfo(FString::Printf(TEXT("Mother's 1.88 m: script 0.72 s at 262.5 cm/s; body peak %.0f cm/s, arrives after %.2f s, peak lag %.0f cm"), Peak, Arrived, PeakLag));
	TestTrue(TEXT("her body walks at her own pace, not the script's sprint"), Peak <= 126.f && PeakStep <= 127.f);
	TestTrue(TEXT("she starts and stops gradually and arrives"), Arrived > 1.4f && Arrived < 2.6f && Mother.GetSpeed() < 1.f);
	TestTrue(TEXT("she never trails by more than the limit"), PeakLag <= 181.f);

	// A long scripted walk: the gap is capped, so she hurries to keep up (the trade-off of a presentation-only fix).
	FDinkVisualFollower Long;
	Long.ComfortSpeed = 125.f; Long.MaxLag = 180.f;
	Script = FVector::ZeroVector; Long.Reset(Script, 0.f);
	float LongLag = 0.f;
	for (int32 I = 0; I < 300; ++I) { Script.X += 262.5f * Dt; Long.Update(Script, 0.f, 262.5f, Dt); LongLag = FMath::Max(LongLag, Long.GetLag(Script)); }
	AddInfo(FString::Printf(TEXT("long scripted walk at 262.5 cm/s: peak lag %.0f cm, final lag %.0f cm, body speed %.0f cm/s"), LongLag, Long.GetLag(Script), Long.GetSpeed()));
	TestTrue(TEXT("on a long walk the lag stays near the limit"), LongLag < 190.f && Long.GetLag(Script) < 185.f);
	TestTrue(TEXT("and she ends up matching the script's speed"), FMath::IsNearlyEqual(Long.GetSpeed(), 262.5f, 20.f));
	const FVector Held = Long.GetLocation();
	Long.Update(Script, 0.f, 262.5f, 0.f);
	TestTrue(TEXT("a paused frame moves nothing"), Long.GetLocation().Equals(Held));
	Long.Update(Script + FVector(5000, 0, 0), 0.f, 0.f, Dt);
	TestTrue(TEXT("a warp snaps the body to the script"), Long.GetLag(Script + FVector(5000, 0, 0)) < .01f);

	// Turning: the facing eases instead of snapping.
	FDinkVisualFollower Turn; Turn.Reset(FVector::ZeroVector, 0.f);
	Turn.Update(FVector::ZeroVector, 180.f, 0.f, Dt);
	TestTrue(TEXT("a new facing is approached at the turn rate"), FMath::Abs(Turn.GetYaw()) > 1.f && FMath::Abs(Turn.GetYaw()) < 10.f);
	for (int32 I = 0; I < 60; ++I) Turn.Update(FVector::ZeroVector, 180.f, 0.f, Dt);
	TestTrue(TEXT("and reached"), FMath::IsNearlyEqual(FMath::Abs(Turn.GetYaw()), 180.f, .5f));

	FDinkVisualFollower Off; Off.MaxLag = 0.f; Off.Reset(FVector::ZeroVector, 0.f);
	Off.Update(FVector(50, 0, 0), 30.f, 262.5f, Dt);
	TestTrue(TEXT("easing off: the body is glued to the script"), Off.GetLag(FVector(50, 0, 0)) < .01f && Off.GetYaw() == 30.f);
	return true;
}
