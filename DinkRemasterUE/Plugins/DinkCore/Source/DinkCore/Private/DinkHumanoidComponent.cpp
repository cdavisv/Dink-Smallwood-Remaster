#include "DinkHumanoidComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/BlendSpace.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"

namespace
{
TAutoConsoleVariable<float> CVarNpcSmoothTime(TEXT("dink.Npc.SmoothTime"), .18f,
	TEXT("Averaging time of an NPC body's position, s: turns the script's pixel steps into continuous motion (0: the body is glued to the scripted position)."));
TAutoConsoleVariable<float> CVarNpcTurnRate(TEXT("dink.Npc.TurnRateDeg"), 300.f,
	TEXT("How fast an NPC body turns to a new facing, degrees per second."));
}

FVector FDinkBodySmoother::Update(const FVector& Target, float TargetYawDeg, float DeltaTime)
{
	if (!bReady || SmoothTime <= 0.f || FVector::DistSquared2D(Target, Position) > FMath::Square(WarpDistance))
	{
		// First frame, a warp, or smoothing switched off: the body is where the script is.
		Reset(Target, TargetYawDeg);
		return Position;
	}
	if (DeltaTime <= SMALL_NUMBER || !FMath::IsFinite(DeltaTime)) return Position; // paused
	Position.Z = Target.Z;
	// Critically damped spring towards the scripted position, in fixed substeps so that the
	// result does not depend on the frame rate.
	const float Omega = 2.f / SmoothTime;
	float Remaining = FMath::Min(DeltaTime, .25f);
	while (Remaining > SMALL_NUMBER)
	{
		const float Step = FMath::Min(Remaining, 1.f / 240.f);
		FVector To = Target - Position;
		To.Z = 0.;
		Velocity += (To * double(Omega * Omega) - Velocity * double(2.f * Omega)) * double(Step);
		Velocity.Z = 0.;
		Position += Velocity * double(Step);
		Remaining -= Step;
	}
	if (FVector::DistSquared2D(Target, Position) < .0004 && Velocity.SizeSquared2D() < .01) { Position.X = Target.X; Position.Y = Target.Y; Velocity = FVector::ZeroVector; }
	// Face along the motion while moving, the scripted facing once there.
	const float WantYaw = Velocity.SizeSquared2D() > FMath::Square(25.) ? float(FMath::RadiansToDegrees(FMath::Atan2(Velocity.Y, Velocity.X))) : TargetYawDeg;
	const float Turn = TurnRateDeg * DeltaTime;
	Yaw = FRotator::NormalizeAxis(Yaw + FMath::Clamp(FMath::FindDeltaAngleDegrees(Yaw, WantYaw), -Turn, Turn));
	return Position;
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
	}
	if (!bBodyAnimation && Locomotion)
	{
		SetAnimationMode(EAnimationMode::AnimationSingleNode);
		PlayAnimation(Locomotion, true);
		if (UAnimSingleNodeInstance* Animation=GetSingleNodeInstance()) Animation->SetPlayRate(1.f);
	}
	Motion.Reset();
	BodyDynamics.Reset();
	Smoother = FDinkBodySmoother();
	LocomotionSpeed = ScriptedSpeed = 0.f;
}

void UDinkHumanoidComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	AActor* Owner = GetOwner();
	if (Owner && bBodyAnimation)
	{
		const FVector Location = Owner->GetActorLocation();
		ScriptedSpeed = Motion.Update(Location, DeltaTime);
		Smoother.SmoothTime = CVarNpcSmoothTime.GetValueOnGameThread();
		Smoother.TurnRateDeg = CVarNpcTurnRate.GetValueOnGameThread();
		const float ActorYaw = float(Owner->GetActorRotation().Yaw);
		const FVector Visual = Smoother.Update(Location, ActorYaw, DeltaTime);
		LocomotionSpeed = Smoother.GetSpeed();
		// The lag and the eased facing are applied on top of whatever transform art authored;
		// if someone replaced that transform since last frame, start from theirs.
		const FTransform Parent = GetAttachParent() ? GetAttachParent()->GetComponentTransform() : FTransform::Identity;
		const FVector BaseLocation = bLagApplied && GetRelativeLocation().Equals(LastLocation, .001) ? GetRelativeLocation() - AppliedLag : GetRelativeLocation();
		const FQuat Current = GetRelativeRotation().Quaternion();
		const FQuat BaseRotation = bBodyRotationApplied && Current.Equals(LastBodyRotation, .00001f) ? AppliedBodyRotation.Inverse() * Current : Current;
		AppliedLag = Parent.InverseTransformVector(Visual - Location);
		LastLocation = BaseLocation + AppliedLag;
		AppliedBodyRotation = FQuat(FVector::UpVector, FMath::DegreesToRadians(FMath::FindDeltaAngleDegrees(ActorYaw, Smoother.GetYaw())));
		LastBodyRotation = AppliedBodyRotation * BaseRotation;
		SetRelativeLocationAndRotation(LastLocation, LastBodyRotation);
		bLagApplied = bBodyRotationApplied = true;
		if (UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(GetAnimInstance()))
		{
			// The clips are the mannequin's size: a smaller body covers less ground per step.
			Body->SetMotion(LocomotionSpeed / FMath::Max(.1f, float(GetComponentScale().Z)), false, 1.f);
			Body->SetPosture(Posture);
		}
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

void UDinkHumanoidComponent::SetSlowCadencePower(float Power)
{
	if (UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(GetAnimInstance())) Body->SetSlowCadencePower(Power);
}
