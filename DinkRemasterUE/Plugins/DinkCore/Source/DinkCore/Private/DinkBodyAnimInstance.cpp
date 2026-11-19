#include "DinkBodyAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AttributesRuntime.h"
#include "BonePose.h"
#include "DinkCollision.h"
#include "DinkSecondaryMotion.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"

namespace
{
TAutoConsoleVariable<int32> CVarDinkLegs(TEXT("dink.Anim.Legs"), 1,
	TEXT("Presentation only. 1: the native body animation places the feet (pinned while planted, pivot steps when turning on the spot, the stride and stance of each character's style, two-bone leg reach with a pelvis offset) and turns NPC heads; 0: the clips as they are (for comparison)."));
TAutoConsoleVariable<int32> CVarDinkFootLock(TEXT("dink.Anim.FootLock"), 1,
	TEXT("Presentation only. 1: a foot the animation sets down stays where it landed until the animation lifts it, and steps when the body turns or shifts on the spot; 0: the feet follow the pose."));
TAutoConsoleVariable<int32> CVarDinkGroundAdapt(TEXT("dink.Anim.GroundAdapt"), 1,
	TEXT("Presentation only. 1: each foot is put on the visible ground under it (traced), the pelvis lowered so the lower foot reaches; 0: the feet stay on the plane of the capsule's floor."));
TAutoConsoleVariable<int32> CVarDinkStyle(TEXT("dink.Anim.Style"), 1,
	TEXT("Presentation only, with dink.Anim.Legs 1. 1: each character's gait style (step length and cadence, stance width, uneven steps, pivot-step pace, chest swing; animation_natural.json `style`); 0: the clip's own."));
TAutoConsoleVariable<int32> CVarDinkLookAt(TEXT("dink.Anim.LookAt"), 1,
	TEXT("Presentation only. 1: NPC heads turn towards Dink when he is near and in front of them (limited angles); 0: off."));

	// Rotates one bone by a mesh-space rotation (the mesh faces +Y, +X is the character's left), worked out from the
	// posed chain so that no bone-axis convention is assumed.
	void RotateInMeshSpace(FCompactPose& Out, int32 Index, const FQuat& Delta)
	{
		if (Index == INDEX_NONE) return;
		FQuat ParentSpace = FQuat::Identity;
		for (FCompactPoseBoneIndex P = Out.GetParentBoneIndex(FCompactPoseBoneIndex(Index)); P.GetInt() != INDEX_NONE; P = Out.GetParentBoneIndex(P))
			ParentSpace = Out[P].GetRotation() * ParentSpace;
		FTransform& Bone = Out[FCompactPoseBoneIndex(Index)];
		Bone.SetRotation((ParentSpace.Inverse() * Delta * ParentSpace * Bone.GetRotation()).GetNormalized());
	}
	float YawOf(const FVector& V) { return FMath::RadiansToDegrees(FMath::Atan2(V.Y, V.X)); }
}

void FDinkGaitBlend::Solve(float Speed, TConstArrayView<float> GaitSpeeds, TConstArrayView<float> GaitStrides,
	float& OutIdle, TArray<float, TInlineAllocator<4>>& OutWeights, float& OutCyclesPerSecond, float CadencePower)
{
	const int32 N = FMath::Min(GaitSpeeds.Num(), GaitStrides.Num());
	OutWeights.Init(0.f, N);
	OutIdle = 1.f;
	OutCyclesPerSecond = 0.f;
	Speed = FMath::IsFinite(Speed) ? FMath::Max(0.f, Speed) : 0.f;
	if (N == 0 || Speed < 1.f) return;
	if (Speed <= GaitSpeeds[0])
	{
		// Slower than the slowest gait: mix in the standing pose, which shortens the step, and
		// lower the cadence a little, as a person walking slowly does. A pose mixed W parts
		// gait to 1 - W parts standing covers W^SlowStridePower of the gait's stride (measured
		// on the posed mesh, see Dink.Art.PlayerAction), so the cadence is set to whatever makes
		// cadence x covered stride equal the speed.
		const float Ratio = Speed / FMath::Max(GaitSpeeds[0], 1.f);
		const float W = FMath::Pow(Ratio, (1.f - FMath::Clamp(CadencePower, 0.f, 1.f)) / SlowStridePower);
		OutIdle = 1.f - W;
		OutWeights[0] = W;
		OutCyclesPerSecond = Speed / FMath::Max(FMath::Pow(W, SlowStridePower) * GaitStrides[0], 1.f);
		return;
	}
	OutIdle = 0.f;
	for (int32 i = 0; i + 1 < N; ++i)
	{
		if (Speed <= GaitSpeeds[i + 1])
		{
			const float W = (Speed - GaitSpeeds[i]) / FMath::Max(GaitSpeeds[i + 1] - GaitSpeeds[i], 1.f);
			OutWeights[i] = 1.f - W;
			OutWeights[i + 1] = W;
			OutCyclesPerSecond = Speed / FMath::Max(FMath::Lerp(GaitStrides[i], GaitStrides[i + 1], W), 1.f);
			return;
		}
	}
	// Faster than the fastest authored gait: same stride, quicker cadence.
	OutWeights[N - 1] = 1.f;
	OutCyclesPerSecond = Speed / FMath::Max(GaitStrides[N - 1], 1.f);
}

bool UDinkBodyAnimInstance::FindPair(const TMap<FName, FDinkBodyClip>& Library, FName Name, FDinkBodyClipPair& Out) const
{
	const FString Base = Name.ToString();
	const FDinkBodyClip* Timid = Library.Find(FName(*(Base + TEXT("_Timid"))));
	const FDinkBodyClip* Confident = Library.Find(FName(*(Base + TEXT("_Confident"))));
	const FDinkBodyClip* Plain = Library.Find(Name);
	if (!Timid) Timid = Confident ? Confident : Plain;
	if (!Confident) Confident = Timid;
	if (!Timid || !Timid->IsValid() || !Confident->IsValid()) return false;
	Out.Timid = *Timid;
	Out.Confident = *Confident;
	return true;
}

bool UDinkBodyAnimInstance::Configure(const TMap<FName, FDinkBodyClip>& Library, FName Set)
{
	FDinkBodyClipPair NewIdle, NewFall;
	TArray<FDinkBodyClipPair> NewGaits;
	TArray<FName, TInlineAllocator<4>> GaitNames;
	FName IdleName, FallName;
	if (Set == TEXT("Hero")) { IdleName = TEXT("Idle"); FallName = TEXT("Fall"); GaitNames = {TEXT("Shuffle"), TEXT("Walk"), TEXT("Run")}; }
	else if (Set == TEXT("NpcF")) { IdleName = TEXT("NpcF_Idle"); GaitNames = {TEXT("NpcF_Walk"), TEXT("NpcF_Hurry")}; }
	else if (Set == TEXT("NpcM")) { IdleName = TEXT("NpcM_Idle"); GaitNames = {TEXT("NpcM_Walk"), TEXT("NpcM_Run")}; }
	else return false;
	if (!FindPair(Library, IdleName, NewIdle)) return false;
	for (const FName Name : GaitNames)
	{
		FDinkBodyClipPair Pair;
		if (FindPair(Library, Name, Pair) && Pair.Speed() > 1.f && Pair.Timid.StrideCm > 1.f && Pair.Confident.StrideCm > 1.f &&
			!NewGaits.ContainsByPredicate([&Pair](const FDinkBodyClipPair& G) { return FMath::IsNearlyEqual(G.Speed(), Pair.Speed(), 1.f); }))
			NewGaits.Add(Pair);
	}
	if (NewGaits.IsEmpty()) return false;
	NewGaits.Sort([](const FDinkBodyClipPair& A, const FDinkBodyClipPair& B) { return A.Speed() < B.Speed(); });
	const USkeleton* Skeleton = CurrentSkeleton;
	for (const FDinkBodyClipPair& Pair : NewGaits)
		if (Skeleton && (Pair.Timid.Sequence->GetSkeleton() != Skeleton || Pair.Confident.Sequence->GetSkeleton() != Skeleton)) return false;
	if (!FallName.IsNone()) FindPair(Library, FallName, NewFall);
	Idle = NewIdle; Fall = NewFall; Gaits = MoveTemp(NewGaits);
	SetName = Set;
	bLegsReady = false;
	bSnapStand = true;
	Clips.Reset();
	for (const auto& Pair : Library)
		if (Pair.Value.IsValid() && (!Skeleton || Pair.Value.Sequence->GetSkeleton() == Skeleton)) Clips.Add(Pair.Key, Pair.Value);
	StopActions();
	Phase = IdleTime = FallTime = AirAlpha = 0.f;
	return true;
}

void UDinkBodyAnimInstance::SetMotion(float SpeedCm, bool bInAirborne, float InConfidence, FVector2f LeanDegrees)
{
	Speed = FMath::IsFinite(SpeedCm) ? FMath::Max(0.f, SpeedCm) : 0.f;
	bAirborne = bInAirborne;
	Confidence = FMath::IsFinite(InConfidence) ? FMath::Clamp(InConfidence, 0.f, 1.f) : 0.f;
	Lean = FVector2f(FMath::Clamp(LeanDegrees.X, -12.f, 12.f), FMath::Clamp(LeanDegrees.Y, -10.f, 10.f));
}

bool UDinkBodyAnimInstance::HasClip(FName Name) const
{
	FDinkBodyClipPair Pair;
	return FindPair(Clips, Name, Pair);
}

bool UDinkBodyAnimInstance::PlayAction(FName Name, bool bFullBody, float Scale, float BlendIn, float BlendOut, bool bHoldLastFrame)
{
	FDinkBodyClipPair Pair;
	if (!IsConfigured() || !FindPair(Clips, Name, Pair)) return false;
	// The running action (if any) fades under the new one: a combo flows instead of popping.
	Slots[1] = Slots[0];
	Slots[1].bFading = Slots[1].bActive;
	FSlot& S = Slots[0];
	S = FSlot();
	S.Clips = Pair;
	S.BlendIn = FMath::Max(.001f, BlendIn);
	S.BlendOut = FMath::Max(.001f, BlendOut);
	S.Scale = FMath::Clamp(Scale, 0.f, 1.f);
	S.bFullBody = bFullBody;
	S.bHold = bHoldLastFrame;
	S.bActive = true;
	ActionName = Name;
	return true;
}

void UDinkBodyAnimInstance::StopActions()
{
	Slots[0] = FSlot(); Slots[1] = FSlot();
	ActionName = NAME_None;
}

bool UDinkBodyAnimInstance::IsActionActive() const { return Slots[0].bActive; }
float UDinkBodyAnimInstance::GetActionTime() const { return Slots[0].bActive ? Slots[0].Time : 0.f; }

void UDinkBodyAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
	Super::NativeUpdateAnimation(DeltaSeconds);
	Frame.Base.Reset();
	Frame.Actions.Reset();
	Frame.Lean = Lean;
	Frame.Posture = Posture;
	if (!IsConfigured()) { PublishFrame(); return; }
	const float Dt = FMath::IsFinite(DeltaSeconds) ? FMath::Clamp(DeltaSeconds, 0.f, .25f) : 0.f;
	{
		// The leg layer's state on the frame drawn last (its evaluation has finished by now).
		const FDinkBodyAnimProxy& Proxy = GetProxyOnGameThread<FDinkBodyAnimProxy>();
		const FDinkLegTelemetry Previous = LegTelemetry;
		LegTelemetry = Proxy.Telemetry;
		// A foot that has just been pinned is a footstep.
		const UWorld* World = GetWorld();
		const float Now = World ? float(World->GetTimeSeconds()) : 0.f;
		static const FName FootNames[2] = {TEXT("foot_l"), TEXT("foot_r")};
		for (int32 S = 0; S < 2; ++S)
		{
			if (LegTelemetry.bValid && Previous.bValid && LegTelemetry.Plants[S] > Previous.Plants[S] &&
				(LastPlant[S] < 0.f || Now - LastPlant[S] >= .18f || Now < LastPlant[S]))
			{
				LastPlant[S] = Now;
				OnFootPlant().Broadcast(GetOwningActor(), FootNames[S], LegTelemetry.FootWorld[S]);
			}
		}
	}
	const float C = Confidence;
	MoveAlpha = FMath::Clamp(Speed / 120.f, 0.f, 1.f);
	// The character's own step length (and so cadence: the speed is kept), applied with the legs' reach.
	const bool bLegs = CVarDinkLegs.GetValueOnGameThread() != 0;
	const FDinkGaitStyle Style = bLegs && CVarDinkStyle.GetValueOnGameThread() != 0 ? FDinkGaitStyle::For(SetName, C) : FDinkGaitStyle();
	// The style's step length is a walk's: nothing holds a run's feet (no warp, no new pins there), so a shorter run stride
	// would only skate; it fades out between 300 and 450 cm/s.
	const float RunFade = 1.f - FMath::Clamp((Speed - 300.f) / 150.f, 0.f, 1.f);
	const float StrideScale = FMath::Lerp(1.f, Style.Stride, MoveAlpha * RunFade);
	TArray<float, TInlineAllocator<4>> Speeds, Strides, Weights;
	for (const FDinkBodyClipPair& Gait : Gaits) { Speeds.Add(Gait.Speed()); Strides.Add(Gait.Stride(C) * StrideScale); }
	float IdleWeight = 1.f;
	FDinkGaitBlend::Solve(Speed, Speeds, Strides, IdleWeight, Weights, CyclesPerSecond, SlowCadence);
	if (bLegs)
	{
		// Standing <-> walking is a blend in time, not a switch by speed: the solver gives the standing pose all the
		// weight the moment the pawn stops (and a slow walk half of it at 5 cm/s), which snapped a striding leg into
		// the idle stance in one frame (a 56 cm jump of the foot on arrival, 13 Nov build). The phase freezes at a stop,
		// the stride fades into the stance over StandBlendSeconds and the pinned feet settle with a step if needed.
		float Sum = 0.f;
		for (const float W : Weights) Sum += W;
		if (Speed >= 1.f && Sum > 1.e-3f) { LastGait.Reset(); for (const float W : Weights) LastGait.Add(W / Sum); }
		// A freshly configured body (a spawn, a load) starts in the state it is in, not blending out of a stand.
		IdleShown = bSnapStand ? IdleWeight : FMath::FInterpConstantTo(IdleShown, IdleWeight, Dt, 1.f / StandBlendSeconds);
		bSnapStand = false;
		if (LastGait.Num() == Weights.Num())
			for (int32 i = 0; i < Weights.Num(); ++i) Weights[i] = LastGait[i] * (1.f - IdleShown);
		IdleWeight = IdleShown;
		// The cadence covers the speed with the stride that is shown (FDinkGaitBlend's slow-walk law).
		if (Speed >= 1.f && Speeds.Num() > 0 && Speed <= Speeds[0])
			CyclesPerSecond = FMath::Min(Speed / FMath::Max(FMath::Pow(1.f - IdleShown, FDinkGaitBlend::SlowStridePower) * Strides[0], 1.f), 2.4f);
	}
	else
	{
		IdleShown = IdleWeight;
		LastGait.Reset();
	}
	BlendedStride = CyclesPerSecond > 0.f ? Speed / CyclesPerSecond : 0.f;
	Phase = FMath::Fmod(Phase + CyclesPerSecond * Dt, 12.f); // whole cycles of clips holding 1, 2, 3 or 4
	IdleTime += Dt;
	Frame.Legs.Style = Style;
	// Like the stride, the uneven pair of steps is a walk's: at a run's 3.5 m cycle it pushed a foot 6 cm past the leg's reach.
	Frame.Legs.Style.Uneven *= RunFade;
	Frame.Legs.StrideScale = StrideScale;
	Frame.Legs.StepCycleCm = BlendedStride;
	const bool bFallReady = Fall.IsValid();
	AirAlpha = bFallReady ? FMath::FInterpConstantTo(AirAlpha, bAirborne ? 1.f : 0.f, Dt, bAirborne ? 9.f : 7.f) : 0.f;
	FallTime = AirAlpha > 0.f ? FallTime + Dt : 0.f;
	const float Ground = 1.f - AirAlpha;
	auto Add = [this](const FDinkBodyClip& Clip, float Time, float Weight)
	{
		if (Weight > .0005f) Frame.Base.Add({Clip.Sequence, Time, Weight});
	};
	auto AddPair = [&](const FDinkBodyClipPair& Pair, float Cycle, float Weight, bool bPhase)
	{
		// bPhase: Cycle counts gait cycles (phase-locked across clips); else seconds, wrapped.
		const bool bSame = Pair.Timid.Sequence == Pair.Confident.Sequence;
		Add(Pair.Timid, bPhase ? Pair.Timid.TimeAtPhase(Cycle) : FMath::Fmod(Cycle, Pair.Timid.Duration), bSame ? Weight : Weight * (1.f - C));
		if (!bSame) Add(Pair.Confident, bPhase ? Pair.Confident.TimeAtPhase(Cycle) : FMath::Fmod(Cycle, Pair.Confident.Duration), Weight * C);
	};
	AddPair(Idle, IdleTime, IdleWeight * Ground, false);
	for (int32 i = 0; i < Gaits.Num(); ++i) AddPair(Gaits[i], Phase, Weights[i] * Ground, true);
	if (bFallReady) AddPair(Fall, FallTime, AirAlpha, false);

	for (FSlot& S : Slots)
	{
		if (!S.bActive) continue;
		S.Time += Dt;
		if (S.bFading) S.Fade = FMath::Max(0.f, S.Fade - Dt / .09f);
		const float Length = S.Clips.Length();
		if (S.bHold) S.Time = FMath::Min(S.Time, Length - .001f); // waits on its last frame until replaced or stopped
		if (S.Time >= Length || S.Fade <= 0.f) { S = FSlot(); continue; }
		const float In = FMath::SmoothStep(0.f, 1.f, S.Time / S.BlendIn);
		const float Out = S.bHold ? 1.f : FMath::SmoothStep(0.f, 1.f, (Length - S.Time) / S.BlendOut);
		FDinkBodyActionFrame A;
		A.Timid = {S.Clips.Timid.Sequence, FMath::Min(S.Time, S.Clips.Timid.Duration), 1.f - C};
		A.Confident = {S.Clips.Confident.Sequence, FMath::Min(S.Time, S.Clips.Confident.Duration), C};
		A.Weight = FMath::Min(In, Out) * S.Scale * S.Fade;
		A.LowerBodyWeight = S.bFullBody ? 1.f : 1.f - MoveAlpha;
		if (A.Weight > .0005f) Frame.Actions.Add(A);
	}
	if (!Slots[0].bActive) ActionName = NAME_None;
	UpdateLegInput(Dt);
	PublishFrame();
}

void UDinkBodyAnimInstance::PublishFrame()
{
	// The engine copies the instance into its proxy (FDinkBodyAnimProxy::PreUpdate) BEFORE NativeUpdateAnimation runs
	// (UAnimInstance::UpdateAnimation), so without this the pose of every frame would be built from the previous
	// frame's speed, clips and, for the leg layer, the previous frame's component transform: pinned feet would be put a
	// frame of travel away from where they stand. The parallel update and evaluation start after this returns.
	GetProxyOnGameThread<FDinkBodyAnimProxy>().Frame = Frame;
}

FDinkFootPlant& UDinkBodyAnimInstance::OnFootPlant()
{
	static FDinkFootPlant Event;
	return Event;
}

void UDinkBodyAnimInstance::UpdateLegInput(float Dt)
{
	FDinkLegInput& L = Frame.Legs;
	USkeletalMeshComponent* Mesh = GetSkelMeshComponent();
	UWorld* World = Mesh ? Mesh->GetWorld() : nullptr;
	L.bEnabled = CVarDinkLegs.GetValueOnGameThread() != 0 && Mesh != nullptr && World != nullptr && Dt > 0.f;
	Frame.Look = FDinkLookInput();
	if (!Mesh) return;
	const FTransform C2W = Mesh->GetComponentTransform();
	const FVector Location = C2W.GetLocation();
	L.bTeleport = !bLegsReady || FVector::DistSquared(Location, LastComponentLocation) > FMath::Square(150.);
	L.Velocity = !L.bTeleport && Dt > 0.f ? (Location - LastComponentLocation) / Dt : FVector::ZeroVector;
	LastComponentLocation = Location;
	bLegsReady = true;
	L.ComponentToWorld = C2W;
	L.DeltaTime = Dt;
	L.MoveAlpha = MoveAlpha;
	L.bStanding = Speed < 15.f;
	L.bAirborne = bAirborne || AirAlpha > .5f;
	// A landing sinks the hips into the knees for a moment, deeper the longer the fall (the Land clip carries the
	// standing crouch; moving, the legs keep running and only this absorbs it).
	if (bAirborne) AirTime += Dt;
	if (bWasAirborne && !bAirborne)
	{
		LandAmplitude = FMath::Clamp((AirTime - .2f) / .6f, 0.f, 1.f) * 8.f * FMath::Lerp(.35f, 1.f, MoveAlpha) * FMath::Lerp(1.2f, .85f, Confidence);
		LandTime = 0.f;
	}
	if (!bAirborne && !bWasAirborne) AirTime = 0.f;
	bWasAirborne = bAirborne;
	LandTime += Dt;
	L.LandingDip = LandTime < .07f ? LandAmplitude * FMath::SmoothStep(0.f, 1.f, LandTime / .07f) : LandAmplitude * FMath::Exp(-(LandTime - .07f) / .16f);
	// The visible ground under each foot, where it was drawn last frame.
	// Off screen or hidden, nobody sees the feet: keep the last ground and spend no traces.
	const bool bSeen = Mesh->WasRecentlyRendered(.25f) && !(Mesh->GetOwner() && Mesh->GetOwner()->IsHidden());
	const bool bGround = L.bEnabled && !L.bAirborne && CVarDinkGroundAdapt.GetValueOnGameThread() != 0;
	if (bGround && !bSeen && !L.bTeleport)
	{
		for (int32 S = 0; S < 2; ++S) L.GroundOffset[S] = GroundSmoothed[S];
	}
	else for (int32 S = 0; S < 2; ++S)
	{
		float Target = 0.f;
		L.bGround[S] = false;
		L.GroundNormal[S] = FVector::UpVector;
		if (bGround)
		{
			const FVector At = LegTelemetry.bValid && !L.bTeleport ? LegTelemetry.FootWorld[S] : C2W.TransformPosition(FVector(S == 0 ? 12.f : -12.f, 0.f, 0.f));
			float Z = 0.f;
			FVector N = FVector::UpVector;
			if (FDinkFootGround::Trace(World, At, float(Location.Z), Mesh->GetOwner(), Z, N) && FMath::Abs(Z - Location.Z) < 30.f)
			{
				Target = Z - float(Location.Z);
				L.bGround[S] = true;
				L.GroundNormal[S] = C2W.InverseTransformVectorNoScale(N).GetSafeNormal();
			}
		}
		GroundSmoothed[S] = L.bTeleport ? Target : FMath::FInterpTo(GroundSmoothed[S], Target, Dt, 18.f);
		L.GroundOffset[S] = GroundSmoothed[S];
	}
	// The head turns towards whatever the owner asked to be looked at.
	if (L.bEnabled && LookWeight > .001f && CVarDinkLookAt.GetValueOnGameThread() != 0)
	{
		Frame.Look.Target = C2W.InverseTransformPosition(LookWorld);
		Frame.Look.Weight = LookWeight;
	}
}

void FDinkBodyAnimProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	if (const UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(InAnimInstance)) Frame = Body->Frame;
}

namespace
{
	void Sample(const FDinkBodyLayer& Layer, FPoseContext& Context, FCompactPose& Pose)
	{
		Pose.SetBoneContainer(&Context.Pose.GetBoneContainer());
		FBlendedCurve Curve;
		Curve.InitFrom(Context.Curve);
		UE::Anim::FStackAttributeContainer Attributes;
		FAnimationPoseData Data(Pose, Curve, Attributes);
		Layer.Sequence->GetAnimationPose(Data, FAnimExtractContext(double(Layer.Time), false));
	}
}

bool FDinkBodyAnimProxy::Evaluate(FPoseContext& Output)
{
	float Total = 0.f;
	for (const FDinkBodyLayer& Layer : Frame.Base) if (Layer.Sequence) Total += Layer.Weight;
	if (Total <= KINDA_SMALL_NUMBER)
	{
		Output.ResetToRefPose();
		return true;
	}
	FCompactPose& Out = Output.Pose;
	const int32 NumBones = Out.GetNumBones();
	bool bFirst = true;
	for (const FDinkBodyLayer& Layer : Frame.Base)
	{
		if (!Layer.Sequence) continue;
		FCompactPose Pose;
		Sample(Layer, Output, Pose);
		const ScalarRegister W(Layer.Weight / Total);
		for (FCompactPoseBoneIndex Bone(0); Bone.GetInt() < NumBones; ++Bone)
		{
			if (bFirst) Out[Bone] = Pose[Bone] * W;
			else Out[Bone].AccumulateWithShortestRotation(Pose[Bone], W);
		}
		bFirst = false;
	}
	for (FCompactPoseBoneIndex Bone(0); Bone.GetInt() < NumBones; ++Bone) Out[Bone].NormalizeRotation();

	const FBoneContainer& Bones = Out.GetBoneContainer();
	if (!bMaskReady || MaskSerial != Bones.GetSerialNumber() || LowerBody.Num() != NumBones)
	{
		LowerBody.Init(false, NumBones);
		LeanBones.Reset();
		ChestBone = HeadBone = ClavicleL = ClavicleR = UpperArmL = UpperArmR = INDEX_NONE;
		PelvisBone = NeckBone = Spine3Bone = INDEX_NONE;
		for (int32 S = 0; S < 2; ++S) Thigh[S] = Calf[S] = Foot[S] = INDEX_NONE;
		const FReferenceSkeleton& Reference = Bones.GetReferenceSkeleton();
		for (FCompactPoseBoneIndex Bone(0); Bone.GetInt() < NumBones; ++Bone)
		{
			const FString Name = Reference.GetBoneName(Bones.MakeMeshPoseIndex(Bone).GetInt()).ToString();
			LowerBody[Bone.GetInt()] = Name == TEXT("root") || Name == TEXT("pelvis") || Name.StartsWith(TEXT("thigh")) ||
				Name.StartsWith(TEXT("calf")) || Name.StartsWith(TEXT("foot")) || Name.StartsWith(TEXT("ball")) || Name.StartsWith(TEXT("ik_foot"));
			if (Name == TEXT("spine_01") || Name == TEXT("spine_03")) LeanBones.Add(Bone.GetInt());
			if (Name == TEXT("spine_04")) ChestBone = Bone.GetInt();
			if (Name == TEXT("head")) HeadBone = Bone.GetInt();
			if (Name == TEXT("clavicle_l")) ClavicleL = Bone.GetInt();
			if (Name == TEXT("clavicle_r")) ClavicleR = Bone.GetInt();
			if (Name == TEXT("upperarm_l")) UpperArmL = Bone.GetInt();
			if (Name == TEXT("upperarm_r")) UpperArmR = Bone.GetInt();
			if (Name == TEXT("pelvis")) PelvisBone = Bone.GetInt();
			if (Name == TEXT("neck_01")) NeckBone = Bone.GetInt();
			if (Name == TEXT("spine_03")) Spine3Bone = Bone.GetInt();
			for (int32 S = 0; S < 2; ++S)
			{
				const TCHAR* Side = S == 0 ? TEXT("_l") : TEXT("_r");
				if (Name == FString(TEXT("thigh")) + Side) Thigh[S] = Bone.GetInt();
				if (Name == FString(TEXT("calf")) + Side) Calf[S] = Bone.GetInt();
				if (Name == FString(TEXT("foot")) + Side) Foot[S] = Bone.GetInt();
			}
		}
		// The leg layer needs pelvis -> thigh -> calf -> foot as direct parents; any other rig keeps the clips as they are.
		for (int32 S = 0; S < 2; ++S)
		{
			const bool bChain = PelvisBone != INDEX_NONE && Thigh[S] != INDEX_NONE && Calf[S] != INDEX_NONE && Foot[S] != INDEX_NONE &&
				Out.GetParentBoneIndex(FCompactPoseBoneIndex(Thigh[S])).GetInt() == PelvisBone &&
				Out.GetParentBoneIndex(FCompactPoseBoneIndex(Calf[S])).GetInt() == Thigh[S] &&
				Out.GetParentBoneIndex(FCompactPoseBoneIndex(Foot[S])).GetInt() == Calf[S];
			if (!bChain) { PelvisBone = INDEX_NONE; break; }
			// Planted height of the ankle: the reference pose stands on the ground.
			FTransform Ref = FTransform::Identity;
			for (FCompactPoseBoneIndex B(Foot[S]); B.GetInt() != INDEX_NONE; B = Out.GetParentBoneIndex(B)) Ref = Ref * Bones.GetRefPoseTransform(B);
			PlantedFootZ[S] = float(Ref.GetLocation().Z);
			// The foot's own axis that points forward when it stands in the reference pose: its yaw on the ground.
			FootForward[S] = Ref.GetRotation().UnrotateVector(FVector::YAxisVector);
		}
		// The pins are world space and per side: a level-of-detail switch keeps them; only the pose's velocities restart.
		bPrevDesired = false;
		MaskSerial = Bones.GetSerialNumber();
		bMaskReady = true;
	}
	for (const FDinkBodyActionFrame& Action : Frame.Actions)
	{
		if (!Action.Timid.Sequence || !Action.Confident.Sequence) continue;
		FCompactPose Timid, Confident;
		const bool bBoth = Action.Timid.Sequence != Action.Confident.Sequence && Action.Timid.Weight > .001f && Action.Confident.Weight > .001f;
		Sample(Action.Timid.Weight >= Action.Confident.Weight || bBoth ? Action.Timid : Action.Confident, Output, Timid);
		if (bBoth) Sample(Action.Confident, Output, Confident);
		for (FCompactPoseBoneIndex Bone(0); Bone.GetInt() < NumBones; ++Bone)
		{
			const float W = Action.Weight * (LowerBody[Bone.GetInt()] ? Action.LowerBodyWeight : 1.f);
			if (W <= .0005f) continue;
			FTransform Pose = Timid[Bone];
			if (bBoth) { Pose.Blend(Timid[Bone], Confident[Bone], Action.Confident.Weight); }
			FTransform Base = Out[Bone];
			Out[Bone].Blend(Base, Pose, W);
		}
	}
	// The pose never carries the clip's travel: the capsule owns where the character is.
	if (NumBones > 0) Out[FCompactPoseBoneIndex(0)] = Bones.GetRefPoseTransform(FCompactPoseBoneIndex(0));
	auto Tilt = [](const FVector& From, float ForwardDeg, float SideDeg, const FVector& Forward, const FVector& Side)
	{
		const FVector To = (From + Forward * FMath::Tan(FMath::DegreesToRadians(ForwardDeg)) + Side * FMath::Tan(FMath::DegreesToRadians(SideDeg))).GetSafeNormal();
		return FQuat::FindBetweenNormals(From, To);
	};
	if (!Frame.Posture.IsNearlyZero3(.01f) || FMath::Abs(Frame.Posture.W) > .01f)
	{
		// The upper arms come in towards the body (a narrower carriage than the captured mannequin's).
		RotateInMeshSpace(Out, UpperArmL, Tilt(-FVector::UpVector, Frame.Posture.W, 0.f, -FVector::XAxisVector, FVector::YAxisVector));
		RotateInMeshSpace(Out, UpperArmR, Tilt(-FVector::UpVector, Frame.Posture.W, 0.f, FVector::XAxisVector, FVector::YAxisVector));
		// Chest rounds forward; the head then drops a little further; each shoulder comes forward.
		RotateInMeshSpace(Out, ChestBone, Tilt(FVector::UpVector, Frame.Posture.X, 0.f, FVector::YAxisVector, FVector::XAxisVector));
		RotateInMeshSpace(Out, HeadBone, Tilt(FVector::YAxisVector, Frame.Posture.Y, 0.f, -FVector::UpVector, FVector::XAxisVector));
		RotateInMeshSpace(Out, ClavicleL, Tilt(FVector::XAxisVector, Frame.Posture.Z, 0.f, FVector::YAxisVector, FVector::UpVector));
		RotateInMeshSpace(Out, ClavicleR, Tilt(-FVector::XAxisVector, Frame.Posture.Z, 0.f, FVector::YAxisVector, FVector::UpVector));
	}
	if (!Frame.Lean.IsNearlyZero(.01f) && LeanBones.Num() > 0)
	{
		for (const int32 Index : LeanBones)
			RotateInMeshSpace(Out, Index, Tilt(FVector::UpVector, Frame.Lean.X / LeanBones.Num(), Frame.Lean.Y / LeanBones.Num(), FVector::YAxisVector, FVector::XAxisVector));
	}
	if (Frame.Legs.bEnabled)
	{
		ApplyChestSwing(Out);
		ApplyLegs(Out);
		ApplyLook(Out);
	}
	else
	{
		Telemetry = FDinkLegTelemetry();
		for (FDinkFootLock& Lock : Locks) Lock.Reset();
		bPrevDesired = false;
		PelvisOffset = PelvisVelocity = 0.f;
	}
	FDinkSecondaryMotion::ApplyToPose(GetSkelMeshComponent(), Out);
	return true;
}

FTransform FDinkBodyAnimProxy::ComponentSpace(const FCompactPose& Pose, int32 Index) const
{
	FTransform T = FTransform::Identity;
	for (FCompactPoseBoneIndex B(Index); B.GetInt() != INDEX_NONE; B = Pose.GetParentBoneIndex(B)) T = T * Pose[B];
	return T;
}

void FDinkBodyAnimProxy::ApplyChestSwing(FCompactPose& Out)
{
	// A swagger is the chest swinging further against the hips than the capture does (a burly man's shoulders);
	// the head is turned back by as much so that he still looks where he goes.
	const FDinkLegInput& L = Frame.Legs;
	const float Gain = (L.Style.ChestSwing - 1.f) * L.MoveAlpha;
	if (FMath::Abs(Gain) < .01f || Spine3Bone == INDEX_NONE || NeckBone == INDEX_NONE || UpperArmL == INDEX_NONE || UpperArmR == INDEX_NONE || PelvisBone == INDEX_NONE) return;
	const FVector Hips = ComponentSpace(Out, Thigh[0]).GetLocation() - ComponentSpace(Out, Thigh[1]).GetLocation();
	const FVector Shoulders = ComponentSpace(Out, UpperArmL).GetLocation() - ComponentSpace(Out, UpperArmR).GetLocation();
	const float Twist = FMath::Clamp(FMath::FindDeltaAngleDegrees(YawOf(Hips), YawOf(Shoulders)), -25.f, 25.f);
	const float Extra = FMath::Clamp(Twist * Gain, -12.f, 12.f);
	RotateInMeshSpace(Out, Spine3Bone, FQuat(FVector::UpVector, FMath::DegreesToRadians(Extra)));
	RotateInMeshSpace(Out, NeckBone, FQuat(FVector::UpVector, FMath::DegreesToRadians(-Extra)));
}

void FDinkBodyAnimProxy::ApplyLegs(FCompactPose& Out)
{
	const FDinkLegInput& L = Frame.Legs;
	if (PelvisBone == INDEX_NONE) { Telemetry = FDinkLegTelemetry(); return; }
	const float Dt = FMath::Clamp(L.DeltaTime, 0.f, .1f);
	if (L.bTeleport)
	{
		StrideWarp = 1.f;
		for (FDinkFootLock& Lock : Locks) Lock.Reset();
		bPrevDesired = false;
		PelvisOffset = PelvisVelocity = 0.f;
	}
	const FTransform& C2W = L.ComponentToWorld;
	const float Scale = FMath::Max(.05f, float(C2W.GetScale3D().Z));
	const FTransform PelvisParent = ComponentSpace(Out, Out.GetParentBoneIndex(FCompactPoseBoneIndex(PelvisBone)).GetInt());
	FTransform PelvisCS = Out[FCompactPoseBoneIndex(PelvisBone)] * PelvisParent;
	FTransform ThighCS[2], CalfCS[2], FootCS[2];
	FVector Desired[2], Target[2];
	FDinkFootLock::FOutput Res[2];
	float DesiredYaw[2];
	for (int32 S = 0; S < 2; ++S)
	{
		ThighCS[S] = Out[FCompactPoseBoneIndex(Thigh[S])] * PelvisCS;
		CalfCS[S] = Out[FCompactPoseBoneIndex(Calf[S])] * ThighCS[S];
		FootCS[S] = Out[FCompactPoseBoneIndex(Foot[S])] * CalfCS[S];
	}
	// Stride warp (with the style; dink.Anim.Style 0 shows the clip's own stride): measured on the foot the clip has down
	// (the lower one, near its planted height) while walking, how fast it travels back under the body against how fast the
	// body goes; the step length is scaled by the ratio, so a planted foot stays where it is set down instead of skating.
	{
		const float BodySpeed = float(L.Velocity.Size2D());
		const int32 Low = FootCS[0].GetLocation().Z <= FootCS[1].GetLocation().Z ? 0 : 1;
		const float StepY = float(FootCS[Low].GetLocation().Y) * L.StrideScale;
		const float NearPlanted = (float(FootCS[Low].GetLocation().Z) - FMath::Min(LowZ[Low], PlantedFootZ[Low] + 6.f / Scale)) * Scale;
		float WarpTarget = 1.f;
		bool bMeasure = false;
		if (CVarDinkStyle.GetValueOnAnyThread() != 0 && bPrevDesired && Dt > 0.f && !L.bStanding && !L.bAirborne && BodySpeed > 30.f && BodySpeed < 320.f && NearPlanted < 2.f)
		{
			const float Back = -(StepY - PrevStepY[Low]) * Scale / Dt; // cm/s backwards in the body (+Y is forward)
			if (Back > 20.f) { WarpTarget = FMath::Clamp(BodySpeed / Back, .6f, 1.6f); bMeasure = true; }
		}
		// Walking only: warping a run (its stance short, its feet often both off the ground) made its slide twice as bad.
		if (bMeasure || L.bStanding || BodySpeed <= 30.f || BodySpeed >= 320.f)
			StrideWarp = FMath::FInterpTo(StrideWarp, WarpTarget, Dt, bMeasure ? 4.f : 6.f);
		for (int32 S = 0; S < 2; ++S) PrevStepY[S] = float(FootCS[S].GetLocation().Y) * L.StrideScale;
	}
	for (int32 S = 0; S < 2; ++S)
	{
		// The style's foot placement: the stride about the body's centre (the cadence was set to match it) times the
		// warp, an uneven pair of steps, the stance width. +X is the character's left.
		const float Side = S == 0 ? 1.f : -1.f;
		FVector F = FootCS[S].GetLocation();
		F.Y = F.Y * L.StrideScale * StrideWarp + Side * L.Style.Uneven * L.StepCycleCm * .25f * L.MoveAlpha / Scale;
		F.X += Side * L.Style.WidthCm / Scale;
		Desired[S] = F;
		DesiredYaw[S] = YawOf(C2W.TransformVectorNoScale(FootCS[S].GetRotation().RotateVector(FootForward[S])));
	}
	const bool bLock = CVarDinkFootLock.GetValueOnAnyThread() != 0;
	FDinkFootLockSettings Settings;
	for (int32 S = 0; S < 2; ++S)
	{
		FDinkFootLock::FInput In;
		In.Desired = C2W.TransformPosition(Desired[S]);
		In.DesiredYaw = DesiredYaw[S];
		// Over the ground: the foot's motion in the body plus the body's travel (its turning is left out, so a body
		// turning on the spot does not drag its planted feet round).
		const FVector LocalVelocity = bPrevDesired && Dt > 0.f ? (Desired[S] - PrevDesired[S]) / Dt : FVector::ZeroVector;
		// Without last frame's pose (a warp, a level-of-detail switch) the speed is unknown: nothing new pins this frame,
		// and a pinned foot stays pinned (one fast frame never lets go).
		In.GroundSpeed = bPrevDesired ? float((C2W.TransformVector(LocalVelocity) + L.Velocity).Size2D()) : 1.e4f;
		// Planted height: the lowest the pose has put this ankle lately (creeping up 3 cm/s), never above the
		// reference stance by more than 6 cm. A clip's stance need not match the reference pose's ankle height.
		const float AnkleZ = float(FootCS[S].GetLocation().Z);
		LowZ[S] = bPrevDesired ? FMath::Min(LowZ[S] + 3.f / Scale * Dt, AnkleZ) : AnkleZ;
		In.Height = (AnkleZ - FMath::Min(LowZ[S], PlantedFootZ[S] + 6.f / Scale)) * Scale;
		In.bStanding = L.bStanding;
		In.bAllowed = bLock && !L.bAirborne;
		In.bNewPins = L.bStanding || L.Velocity.Size2D() < 320.f;
		In.bOtherPinned = Locks[1 - S].IsPinned();
		In.StepTimeScale = L.Style.StepTime;
		Res[S] = Locks[S].Update(In, Dt, Settings);
		PrevDesired[S] = Desired[S];
	}
	bPrevDesired = true;
	// Targets in component space, on the visible ground.
	float Ground[2];
	for (int32 S = 0; S < 2; ++S)
	{
		Ground[S] = L.bGround[S] && !L.bAirborne ? L.GroundOffset[S] / Scale : 0.f;
		Target[S] = C2W.InverseTransformPosition(Res[S].Position);
		Target[S].Z = Desired[S].Z + Ground[S] + Res[S].Lift / Scale;
	}
	// The pelvis goes down for the lower foot's ground, for a target a straight leg could not reach, and for a landing.
	// Both feet on visible ground above the capsule's floor (an NPC whose actor height is fixed): the body rises onto it.
	const bool bBothGround = L.bGround[0] && L.bGround[1] && !L.bAirborne;
	float Want = (bBothGround ? FMath::Min(Ground[0], Ground[1]) : FMath::Min(0.f, FMath::Min(Ground[0], Ground[1]))) - L.LandingDip / Scale;
	for (int32 S = 0; S < 2; ++S)
	{
		// Usable reach: most of the chain, or what the clip itself already reaches (a straight stance leg is the clip's,
		// not a reason to sink the hips).
		const float Leg = FMath::Max(float(FVector::Dist(ThighCS[S].GetLocation(), CalfCS[S].GetLocation()) + FVector::Dist(CalfCS[S].GetLocation(), FootCS[S].GetLocation())) * .975f,
			float(FVector::Dist(ThighCS[S].GetLocation(), FootCS[S].GetLocation())) + .01f);
		const FVector Hip = ThighCS[S].GetLocation() + FVector(0, 0, Want);
		const float R = float(FVector::Dist2D(Hip, Target[S]));
		const float Down = float(Hip.Z - Target[S].Z);
		if (R < Leg && Down > 0.f)
		{
			const float Reach = FMath::Sqrt(FMath::Max(0.f, Leg * Leg - R * R));
			if (Down > Reach) Want -= FMath::Min(Down - Reach, 12.f / Scale);
		}
	}
	// A shorter step (the stride warp, a style's stride) brings the stance foot in under the hips; at the clip's pelvis height
	// that folds the knee 10 degrees deeper than the clip has it (a crouched shuffle, 16 Nov strips). The hips rise by as much
	// as keeps the stance leg as straight as the clip's, at most 2.8 cm, on level ground only (nothing else asked to sink them).
	if (!L.bAirborne && !L.bStanding && Want > -.5f / Scale)
	{
		const int32 St = Target[0].Z <= Target[1].Z ? 0 : 1;
		const FVector Hip = ThighCS[St].GetLocation() + FVector(0, 0, Want);
		const float Clip = float(FVector::Dist(ThighCS[St].GetLocation(), FootCS[St].GetLocation()));
		const float R = float(FVector::Dist2D(Hip, Target[St]));
		const float Down = float(Hip.Z - Target[St].Z);
		if (R < Clip && Down > 0.f)
			Want += FMath::Clamp(FMath::Sqrt(Clip * Clip - R * R) - Down, 0.f, 2.8f / Scale);
	}
	Want = FMath::Clamp(Want, -30.f / Scale, 20.f / Scale);
	if (L.bTeleport || Dt <= 0.f) { PelvisOffset = Want; PelvisVelocity = 0.f; }
	else
	{
		float Remaining = Dt;
		const float Omega = 26.f;
		while (Remaining > SMALL_NUMBER)
		{
			const float Step = FMath::Min(Remaining, 1.f / 240.f);
			PelvisVelocity += ((Want - PelvisOffset) * Omega * Omega - PelvisVelocity * 2.f * Omega) * Step;
			PelvisOffset += PelvisVelocity * Step;
			Remaining -= Step;
		}
	}
	const FVector Drop(0, 0, PelvisOffset);
	PelvisCS.AddToTranslation(Drop);
	Out[FCompactPoseBoneIndex(PelvisBone)] = PelvisCS.GetRelativeTransform(PelvisParent);
	for (int32 S = 0; S < 2; ++S)
	{
		const FVector Hip = ThighCS[S].GetLocation() + Drop, Knee = CalfCS[S].GetLocation() + Drop, Ankle = FootCS[S].GetLocation() + Drop;
		FVector Pole = Knee - (Hip + Ankle) * .5;
		Pole = Pole.SizeSquared() > 1. ? Pole.GetSafeNormal() : FVector::YAxisVector;
		// A knee may face forward or outward, never backward (a clip's own knee plane is kept otherwise).
		if (FVector::DotProduct(Pole, FVector::YAxisVector) < -.3) Pole = (Pole + 1.5 * FVector::YAxisVector).GetSafeNormal();
		FVector NewKnee, NewAnkle;
		FDinkTwoBoneIK::Solve(Hip, Knee, Ankle, Target[S], Pole, NewKnee, NewAnkle, .04f, float(FVector::Dist(Hip, Ankle)));
		const FQuat Q1 = FQuat::FindBetweenVectors(Knee - Hip, NewKnee - Hip);
		FTransform NewThigh = ThighCS[S];
		NewThigh.SetLocation(Hip);
		NewThigh.SetRotation((Q1 * ThighCS[S].GetRotation()).GetNormalized());
		const FQuat Q2 = FQuat::FindBetweenVectors(Q1.RotateVector(Ankle - Knee), NewAnkle - NewKnee);
		FTransform NewCalf = CalfCS[S];
		NewCalf.SetLocation(NewKnee);
		NewCalf.SetRotation((Q2 * Q1 * CalfCS[S].GetRotation()).GetNormalized());
		// The foot keeps the pose's orientation, turned to its pin's yaw and laid on the ground's slope.
		FQuat FootRot = FootCS[S].GetRotation();
		const float YawDelta = FMath::FindDeltaAngleDegrees(DesiredYaw[S], Res[S].Yaw);
		if (FMath::Abs(YawDelta) > .01f) FootRot = FQuat(FVector::UpVector, FMath::DegreesToRadians(YawDelta)) * FootRot;
		if (L.bGround[S])
		{
			FVector N = L.GroundNormal[S];
			const float Tilt = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(float(N.Z), -1.f, 1.f)));
			const float Planted = FMath::Clamp(1.f - (Desired[S].Z - LowZ[S]) * Scale / 12.f, 0.f, 1.f) * (1.f - FMath::Clamp(Res[S].Lift / 4.f, 0.f, 1.f));
			if (Tilt > .5f && Planted > 0.f)
			{
				const FQuat Slope = FQuat::FindBetweenNormals(FVector::UpVector, N);
				FootRot = FQuat::Slerp(FQuat::Identity, Slope, Planted * FMath::Min(1.f, 25.f / Tilt)) * FootRot;
			}
		}
		FTransform NewFoot = FootCS[S];
		NewFoot.SetLocation(NewAnkle);
		NewFoot.SetRotation(FootRot.GetNormalized());
		Out[FCompactPoseBoneIndex(Thigh[S])] = NewThigh.GetRelativeTransform(PelvisCS);
		Out[FCompactPoseBoneIndex(Calf[S])] = NewCalf.GetRelativeTransform(NewThigh);
		Out[FCompactPoseBoneIndex(Foot[S])] = NewFoot.GetRelativeTransform(NewCalf);
		Telemetry.State[S] = uint8(Locks[S].GetState());
		Telemetry.LockWeight[S] = Res[S].Weight;
		Telemetry.KneeFlexDeg[S] = FDinkTwoBoneIK::Flexion(Hip, NewKnee, NewAnkle, FVector::YAxisVector);
		Telemetry.Steps[S] = Locks[S].GetSteps();
		Telemetry.Plants[S] = Locks[S].GetPlants();
		if (S == 0) for (int32 R = 0; R < 3; ++R) Telemetry.Releases[R] = Locks[0].GetReleases(R) + Locks[1].GetReleases(R);
		Telemetry.FootWorld[S] = C2W.TransformPosition(NewAnkle);
	}
	Telemetry.PelvisOffsetCm = PelvisOffset * Scale;
	Telemetry.bValid = true;
}

void FDinkBodyAnimProxy::ApplyLook(FCompactPose& Out)
{
	const FDinkLookInput& Look = Frame.Look;
	Telemetry.LookYawDeg = Telemetry.LookPitchDeg = 0.f;
	if (Look.Weight < .001f || HeadBone == INDEX_NONE || NeckBone == INDEX_NONE) return;
	const FVector Head = ComponentSpace(Out, HeadBone).GetLocation();
	const FVector D = Look.Target - Head;
	if (D.SizeSquared() < 100.) return;
	// Mesh space: forward +Y, left +X. A person turns the head about 70 degrees each way and tips it 30 down, 20 up.
	const float Yaw = FMath::Clamp(FMath::RadiansToDegrees(FMath::Atan2(float(D.X), float(D.Y))), -70.f, 70.f);
	const float Pitch = FMath::Clamp(FMath::RadiansToDegrees(FMath::Atan2(float(D.Z), float(FVector(D.X, D.Y, 0).Size()))), -30.f, 20.f);
	const FQuat QYaw(FVector::UpVector, FMath::DegreesToRadians(-Yaw));
	const FQuat QPitch(QYaw.RotateVector(FVector::XAxisVector), FMath::DegreesToRadians(Pitch));
	const FQuat Q = QPitch * QYaw;
	RotateInMeshSpace(Out, NeckBone, FQuat::Slerp(FQuat::Identity, Q, .4f * Look.Weight));
	RotateInMeshSpace(Out, HeadBone, FQuat::Slerp(FQuat::Identity, Q, .6f * Look.Weight));
	Telemetry.LookYawDeg = Yaw * Look.Weight;
	Telemetry.LookPitchDeg = Pitch * Look.Weight;
}
