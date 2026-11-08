#include "DinkHumanoidComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/BlendSpace.h"
#include "GameFramework/Actor.h"

UDinkHumanoidComponent::UDinkHumanoidComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	SetMobility(EComponentMobility::Movable);
	SetCollisionProfileName(TEXT("NoCollision"));
	SetGenerateOverlapEvents(false);
	SetCanEverAffectNavigation(false);
	VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
}

void UDinkHumanoidComponent::Configure(USkeletalMesh* Mesh, UBlendSpace* Locomotion)
{
	// A script size/profile reapply may already have supplied a fresh authored transform.
	// Strip our last lean only if that exact pose is still ours; never remove it from a new base.
	const FQuat Current = GetRelativeRotation().Quaternion();
	if (bBodyRotationApplied && Current.Equals(LastBodyRotation, .00001f))
		SetRelativeRotation(AppliedBodyRotation.Inverse() * Current);
	AppliedBodyRotation = FQuat::Identity;
	bBodyRotationApplied = false;
	SetSkeletalMesh(Mesh);
	LocomotionAsset = Locomotion;
	if (Locomotion)
	{
		SetAnimationMode(EAnimationMode::AnimationSingleNode);
		PlayAnimation(Locomotion, true);
		if (UAnimSingleNodeInstance* Animation=GetSingleNodeInstance()) Animation->SetPlayRate(1.f);
	}
	Motion.Reset();
	BodyDynamics.Reset();
	LocomotionSpeed = 0.f;
}

void UDinkHumanoidComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	if (AActor* Owner = GetOwner())
	{
		const FVector Location = Owner->GetActorLocation();
		const FQuat Current = GetRelativeRotation().Quaternion();
		const FQuat Base = bBodyRotationApplied && Current.Equals(LastBodyRotation, .00001f)
			? AppliedBodyRotation.Inverse() * Current : Current;
		AppliedBodyRotation = BodyDynamics.Update(Location, Owner->GetActorQuat(), DeltaTime).Quaternion();
		LastBodyRotation = AppliedBodyRotation * Base;
		SetRelativeRotation(LastBodyRotation);
		bBodyRotationApplied = true;
		LocomotionSpeed = Motion.Update(Location, DeltaTime);
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
