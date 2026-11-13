#pragma once

#include "CoreMinimal.h"
#include "DinkMotionEstimate.h"
#include "DinkBodyDynamics.h"
#include "DinkBodyAnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "DinkHumanoidComponent.generated.h"

class UBlendSpace;

/**
 * Where an NPC's body is shown relative to where the original script has it. The script moves
 * sprites in screen pixels at the original's pace, which the remaster's larger rooms turn into
 * a sprint (Mother crosses her kitchen at 2.6 m/s). The body follows the scripted position at a
 * comfortable walking pace with eased starts, stops and turns, and only hurries when it would
 * fall further behind than MaxLag. The scripted position, its timing and its collision are not
 * touched: this is presentation only. Pure maths, testable without a world.
 */
struct DINKCORE_API FDinkVisualFollower
{
	/** Pace she walks at when nothing forces her to hurry, cm/s. */
	float ComfortSpeed = 125.f;
	/** Furthest the body may trail the scripted position, cm. */
	float MaxLag = 180.f;
	float Acceleration = 420.f, Deceleration = 380.f, TurnRateDeg = 300.f;

	void Reset(const FVector& Location, float YawDeg) { Visual = Location; Yaw = YawDeg; Speed = 0.f; bReady = true; }
	/** Advances the body towards Target (the scripted position, moving at TargetSpeed) and returns where to show it. */
	FVector Update(const FVector& Target, float TargetYawDeg, float TargetSpeed, float DeltaTime);
	bool IsReady() const { return bReady; }
	float GetSpeed() const { return Speed; }
	float GetYaw() const { return Yaw; }
	float GetLag(const FVector& Target) const { return float(FVector::Dist2D(Target, Visual)); }
	const FVector& GetLocation() const { return Visual; }
private:
	FVector Visual = FVector::ZeroVector;
	float Speed = 0.f, Yaw = 0.f;
	bool bReady = false;
};

/** Animated authored NPC surface attached to an original script actor.
 * Reads actual world displacement, so story moves and classic brains share locomotion.
 * Does not depend on an APawn owner or change the original movement/gameplay rules.
 */
UCLASS(ClassGroup = Dink, meta = (BlueprintSpawnableComponent))
class DINKCORE_API UDinkHumanoidComponent : public USkeletalMeshComponent
{
	GENERATED_BODY()
public:
	UDinkHumanoidComponent();
	/** Library + Set select the animation pass's native body animation (stride-matched gaits and
	 * the eased follower); without them the blend space drives the mesh as before. */
	void Configure(USkeletalMesh* Mesh, UBlendSpace* Locomotion, const TMap<FName, FDinkBodyClip>* Library = nullptr, FName Set = NAME_None);
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	/** Speed the body is shown moving at, cm/s. */
	float GetLocomotionSpeed() const { return LocomotionSpeed; }
	/** Speed of the scripted position, cm/s. */
	float GetScriptedSpeed() const { return ScriptedSpeed; }
	bool UsesBodyAnimation() const { return bBodyAnimation; }
	const FDinkVisualFollower& GetFollower() const { return Follower; }
private:
	FDinkMotionEstimate Motion;
	FDinkBodyDynamics BodyDynamics;
	FDinkVisualFollower Follower;
	FQuat AppliedBodyRotation = FQuat::Identity;
	FQuat LastBodyRotation = FQuat::Identity;
	FVector AppliedLag = FVector::ZeroVector, LastLocation = FVector::ZeroVector;
	bool bBodyRotationApplied = false, bLagApplied = false, bBodyAnimation = false;
	float LocomotionSpeed = 0.f, ScriptedSpeed = 0.f;
	UPROPERTY(Transient)
	TObjectPtr<UBlendSpace> LocomotionAsset;
};
