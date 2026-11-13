#include "DinkBodyAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AttributesRuntime.h"
#include "BonePose.h"

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
	if (!IsConfigured()) return;
	const float Dt = FMath::IsFinite(DeltaSeconds) ? FMath::Clamp(DeltaSeconds, 0.f, .25f) : 0.f;
	const float C = Confidence;
	TArray<float, TInlineAllocator<4>> Speeds, Strides, Weights;
	for (const FDinkBodyClipPair& Gait : Gaits) { Speeds.Add(Gait.Speed()); Strides.Add(Gait.Stride(C)); }
	float IdleWeight = 1.f;
	FDinkGaitBlend::Solve(Speed, Speeds, Strides, IdleWeight, Weights, CyclesPerSecond, SlowCadence);
	BlendedStride = CyclesPerSecond > 0.f ? Speed / CyclesPerSecond : 0.f;
	Phase = FMath::Fmod(Phase + CyclesPerSecond * Dt, 12.f); // whole cycles of clips holding 1, 2, 3 or 4
	IdleTime += Dt;
	MoveAlpha = FMath::Clamp(Speed / 120.f, 0.f, 1.f);
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
		}
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
	// Rotates one bone by a mesh-space rotation (the mesh faces +Y, +X is the character's left),
	// worked out from the posed chain so that no bone-axis convention is assumed.
	auto RotateInMeshSpace = [&Out](int32 Index, const FQuat& Delta)
	{
		if (Index == INDEX_NONE) return;
		FQuat ParentSpace = FQuat::Identity;
		for (FCompactPoseBoneIndex P = Out.GetParentBoneIndex(FCompactPoseBoneIndex(Index)); P.GetInt() != INDEX_NONE; P = Out.GetParentBoneIndex(P))
			ParentSpace = Out[P].GetRotation() * ParentSpace;
		FTransform& Bone = Out[FCompactPoseBoneIndex(Index)];
		Bone.SetRotation((ParentSpace.Inverse() * Delta * ParentSpace * Bone.GetRotation()).GetNormalized());
	};
	auto Tilt = [](const FVector& From, float ForwardDeg, float SideDeg, const FVector& Forward, const FVector& Side)
	{
		const FVector To = (From + Forward * FMath::Tan(FMath::DegreesToRadians(ForwardDeg)) + Side * FMath::Tan(FMath::DegreesToRadians(SideDeg))).GetSafeNormal();
		return FQuat::FindBetweenNormals(From, To);
	};
	if (!Frame.Posture.IsNearlyZero3(.01f) || FMath::Abs(Frame.Posture.W) > .01f)
	{
		// The upper arms come in towards the body (a narrower carriage than the captured mannequin's).
		RotateInMeshSpace(UpperArmL, Tilt(-FVector::UpVector, Frame.Posture.W, 0.f, -FVector::XAxisVector, FVector::YAxisVector));
		RotateInMeshSpace(UpperArmR, Tilt(-FVector::UpVector, Frame.Posture.W, 0.f, FVector::XAxisVector, FVector::YAxisVector));
		// Chest rounds forward; the head then drops a little further; each shoulder comes forward.
		RotateInMeshSpace(ChestBone, Tilt(FVector::UpVector, Frame.Posture.X, 0.f, FVector::YAxisVector, FVector::XAxisVector));
		RotateInMeshSpace(HeadBone, Tilt(FVector::YAxisVector, Frame.Posture.Y, 0.f, -FVector::UpVector, FVector::XAxisVector));
		RotateInMeshSpace(ClavicleL, Tilt(FVector::XAxisVector, Frame.Posture.Z, 0.f, FVector::YAxisVector, FVector::UpVector));
		RotateInMeshSpace(ClavicleR, Tilt(-FVector::XAxisVector, Frame.Posture.Z, 0.f, FVector::YAxisVector, FVector::UpVector));
	}
	if (!Frame.Lean.IsNearlyZero(.01f) && LeanBones.Num() > 0)
	{
		for (const int32 Index : LeanBones)
			RotateInMeshSpace(Index, Tilt(FVector::UpVector, Frame.Lean.X / LeanBones.Num(), Frame.Lean.Y / LeanBones.Num(), FVector::YAxisVector, FVector::XAxisVector));
	}
	return true;
}
