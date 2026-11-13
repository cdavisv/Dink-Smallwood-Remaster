#include "DinkHumanoidComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/BlendSpace.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"

namespace
{
TAutoConsoleVariable<float> CVarNpcMaxLag(TEXT("dink.Npc.MaxVisualLagCm"), 180.f,
	TEXT("Furthest an NPC body may trail its scripted position before it hurries, cm (0: no easing, the body is glued to the script)."));
TAutoConsoleVariable<float> CVarNpcComfort(TEXT("dink.Npc.ComfortSpeedScale"), 1.f,
	TEXT("Scale on the NPC walking pace (the authored walk clip's speed)."));
TAutoConsoleVariable<float> CVarNpcTurnRate(TEXT("dink.Npc.TurnRateDeg"), 300.f,
	TEXT("How fast an NPC body turns to a new facing, degrees per second."));
}

FVector FDinkVisualFollower::Update(const FVector& Target, float TargetYawDeg, float TargetSpeed, float DeltaTime)
{
	if (!bReady || FVector::DistSquared2D(Target, Visual) > FMath::Square(FMath::Max(300.f, MaxLag * 3.f)) || MaxLag <= 0.f)
	{
		// First frame, a warp, or easing switched off: the body is where the script is.
		Reset(Target, TargetYawDeg);
		return Visual;
	}
	if (DeltaTime <= SMALL_NUMBER || !FMath::IsFinite(DeltaTime)) return Visual; // paused
	FVector To = Target - Visual;
	Visual.Z = Target.Z;
	To.Z = 0.;
	const float Distance = float(To.Size());
	TargetSpeed = FMath::IsFinite(TargetSpeed) ? FMath::Max(0.f, TargetSpeed) : 0.f;
	// Walk at her own pace; brake so that she arrives instead of stopping dead; and never let
	// the gap grow past MaxLag: beyond it she matches the script's speed and closes the excess.
	float Desired = Distance > .5f ? ComfortSpeed : 0.f;
	Desired = FMath::Min(Desired, FMath::Sqrt(2.f * Deceleration * Distance));
	// (She starts to hurry over the last 30% of the allowance, so the limit is approached, not overshot.)
	const float Hurry = FMath::SmoothStep(MaxLag * .7f, MaxLag, Distance);
	Desired = FMath::Max(Desired, FMath::Lerp(Desired, TargetSpeed, Hurry) + FMath::Max(0.f, Distance - MaxLag) * 3.f);
	Speed = FMath::FInterpConstantTo(Speed, Desired, DeltaTime, Desired > Speed ? Acceleration : Deceleration);
	const float Step = FMath::Min(Speed * DeltaTime, Distance);
	if (Distance > KINDA_SMALL_NUMBER) Visual += To / Distance * Step;
	if (Distance <= .5f) Speed = FMath::Min(Speed, Desired);
	// Face where she is going while she has ground to cover, the scripted facing once there.
	const float WantYaw = Distance > 6.f && Speed > 15.f ? float(FMath::RadiansToDegrees(FMath::Atan2(To.Y, To.X))) : TargetYawDeg;
	const float Turn = TurnRateDeg * DeltaTime;
	Yaw = FRotator::NormalizeAxis(Yaw + FMath::Clamp(FMath::FindDeltaAngleDegrees(Yaw, WantYaw), -Turn, Turn));
	return Visual;
}

UDinkHumanoidComponent::UDinkHumanoidComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	SetMobility(EComponentMobility::Movable);
	SetCollisionProfileName(TEXT("NoCollision"));
	SetGenerateOverlapEvents(false);
	SetCanEverAffectNavigation(false);
	VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
}

void UDinkHumanoidComponent::Configure(USkeletalMesh* Mesh, UBlendSpace* Locomotion, const TMap<FName, FDinkBodyClip>* Library, FName Set)
{
	// A script size/profile reapply may already have supplied a fresh authored transform.
	// Strip our last lean/lag only if that exact pose is still ours; never remove it from a new base.
	const FQuat Current = GetRelativeRotation().Quaternion();
	if (bBodyRotationApplied && Current.Equals(LastBodyRotation, .00001f))
		SetRelativeRotation(AppliedBodyRotation.Inverse() * Current);
	if (bLagApplied && GetRelativeLocation().Equals(LastLocation, .001))
		SetRelativeLocation(GetRelativeLocation() - AppliedLag);
	AppliedBodyRotation = FQuat::Identity;
	AppliedLag = FVector::ZeroVector;
	bBodyRotationApplied = bLagApplied = false;
	SetSkeletalMesh(Mesh);
	LocomotionAsset = Locomotion;
	bBodyAnimation = false;
	if (Mesh && Library && !Set.IsNone() && !Library->IsEmpty())
	{
		SetAnimationMode(EAnimationMode::AnimationBlueprint);
		SetAnimInstanceClass(UDinkBodyAnimInstance::StaticClass());
		UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(GetAnimInstance());
		bBodyAnimation = Body && Body->Configure(*Library, Set);
		if (bBodyAnimation)
		{
			// The slowest authored gait is the pace she walks at.
			float Slowest = 0.f;
			for (const auto& Pair : *Library)
				if (Pair.Key.ToString().StartsWith(Set.ToString() + TEXT("_")) && Pair.Value.SpeedCm > 1.f && (Slowest <= 0.f || Pair.Value.SpeedCm < Slowest)) Slowest = Pair.Value.SpeedCm;
			if (Slowest > 0.f) Follower.ComfortSpeed = Slowest;
		}
	}
	if (!bBodyAnimation && Locomotion)
	{
		SetAnimationMode(EAnimationMode::AnimationSingleNode);
		PlayAnimation(Locomotion, true);
		if (UAnimSingleNodeInstance* Animation=GetSingleNodeInstance()) Animation->SetPlayRate(1.f);
	}
	Motion.Reset();
	BodyDynamics.Reset();
	const float Comfort = Follower.ComfortSpeed;
	Follower = FDinkVisualFollower();
	Follower.ComfortSpeed = Comfort;
	LocomotionSpeed = ScriptedSpeed = 0.f;
}

void UDinkHumanoidComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	AActor* Owner = GetOwner();
	if (Owner && bBodyAnimation)
	{
		const FVector Location = Owner->GetActorLocation();
		ScriptedSpeed = Motion.Update(Location, DeltaTime);
		Follower.MaxLag = CVarNpcMaxLag.GetValueOnGameThread();
		Follower.TurnRateDeg = CVarNpcTurnRate.GetValueOnGameThread();
		const float BaseComfort = Follower.ComfortSpeed;
		Follower.ComfortSpeed = BaseComfort * FMath::Max(.1f, CVarNpcComfort.GetValueOnGameThread());
		const float ActorYaw = float(Owner->GetActorRotation().Yaw);
		const FVector Visual = Follower.Update(Location, ActorYaw, ScriptedSpeed, DeltaTime);
		Follower.ComfortSpeed = BaseComfort;
		LocomotionSpeed = Follower.GetSpeed();
		// The lag and the eased facing are applied on top of whatever transform art authored;
		// if someone replaced that transform since last frame, start from theirs.
		const FTransform Parent = GetAttachParent() ? GetAttachParent()->GetComponentTransform() : FTransform::Identity;
		const FVector BaseLocation = bLagApplied && GetRelativeLocation().Equals(LastLocation, .001) ? GetRelativeLocation() - AppliedLag : GetRelativeLocation();
		const FQuat Current = GetRelativeRotation().Quaternion();
		const FQuat BaseRotation = bBodyRotationApplied && Current.Equals(LastBodyRotation, .00001f) ? AppliedBodyRotation.Inverse() * Current : Current;
		AppliedLag = Parent.InverseTransformVector(Visual - Location);
		LastLocation = BaseLocation + AppliedLag;
		AppliedBodyRotation = FQuat(FVector::UpVector, FMath::DegreesToRadians(FMath::FindDeltaAngleDegrees(ActorYaw, Follower.GetYaw())));
		LastBodyRotation = AppliedBodyRotation * BaseRotation;
		SetRelativeLocationAndRotation(LastLocation, LastBodyRotation);
		bLagApplied = bBodyRotationApplied = true;
		if (UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(GetAnimInstance())) Body->SetMotion(LocomotionSpeed, false, 1.f);
	}
	else if (Owner)
	{
		const FVector Location = Owner->GetActorLocation();
		const FQuat Current = GetRelativeRotation().Quaternion();
		const FQuat Base = bBodyRotationApplied && Current.Equals(LastBodyRotation, .00001f)
			? AppliedBodyRotation.Inverse() * Current : Current;
		AppliedBodyRotation = BodyDynamics.Update(Location, Owner->GetActorQuat(), DeltaTime).Quaternion();
		LastBodyRotation = AppliedBodyRotation * Base;
		SetRelativeRotation(LastBodyRotation);
		bBodyRotationApplied = true;
		LocomotionSpeed = ScriptedSpeed = Motion.Update(Location, DeltaTime);
		if (UAnimSingleNodeInstance* Animation = GetSingleNodeInstance(); Animation && LocomotionAsset)
		{
			FVector Position = FVector::ZeroVector;
			float MaxSpeed=0.f;
			for (int32 Axis = 0; Axis < 3; ++Axis)
			{
				const FBlendParameter& Parameter = LocomotionAsset->GetBlendParameter(Axis);
				if (Parameter.DisplayName.Contains(TEXT("Speed")))
				{
					Position[Axis] = FMath::Clamp(LocomotionSpeed, Parameter.Min, Parameter.Max);
					MaxSpeed=Parameter.Max;
				}
			}
			Animation->SetBlendSpacePosition(Position);
			Animation->SetPlayRate(MaxSpeed>0.f ? FMath::Clamp(LocomotionSpeed/MaxSpeed,1.f,3.f) : 1.f);
		}
	}
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
}
