#pragma once

#include "CoreMinimal.h"
#include "DinkMotionEstimate.h"
#include "DinkBodyDynamics.h"
#include "DinkBodyAnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "DinkHumanoidComponent.generated.h"

class UBlendSpace;

/**
 * Presents a scripted NPC's movement as continuous motion. The original engine moves a sprite in
 * whole pixels on 60 Hz frames (one pixel is 4.4 cm in Dink's house, 10 cm outdoors), so the
 * scripted position arrives as small jumps that do not line up with rendered frames. The body is
 * shown at a critically damped average of that position: steady scripted movement becomes steady
 * motion, starts and stops become short ramps, and the body trails the script by speed x
 * SmoothTime (about 20 cm at a walk). There is no catch-up logic: the body never moves faster
 * than the script does. The scripted position, its timing and its collision are not touched.
 * Pure maths, testable without a world.
 */
struct DINKCORE_API FDinkBodySmoother
{
	/** Averaging time, s. 0 glues the body to the scripted position. */
	float SmoothTime = .18f;
	float TurnRateDeg = 300.f;
	/** A jump of the scripted position beyond this is a warp, not a walk, cm. */
	float WarpDistance = 200.f;

	void Reset(const FVector& Location, float YawDeg) { Position = Location; Velocity = FVector::ZeroVector; Yaw = YawDeg; bReady = true; }
	/** Advances towards Target (the scripted position) and returns where to show the body. */
	FVector Update(const FVector& Target, float TargetYawDeg, float DeltaTime);
	bool IsReady() const { return bReady; }
	float GetSpeed() const { return float(Velocity.Size2D()); }
	float GetYaw() const { return Yaw; }
	float GetLag(const FVector& Target) const { return float(FVector::Dist2D(Target, Position)); }
	const FVector& GetLocation() const { return Position; }
private:
	FVector Position = FVector::ZeroVector, Velocity = FVector::ZeroVector;
	float Yaw = 0.f;
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
	/** Library + Set select the native body animation (stride-matched gaits, smoothed position
	 * and facing); without them the blend space drives the mesh as before. */
	void Configure(USkeletalMesh* Mesh, UBlendSpace* Locomotion, const TMap<FName, FDinkBodyClip>* Library = nullptr, FName Set = NAME_None);
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	/** Speed the body is shown moving at, cm/s. */
	float GetLocomotionSpeed() const { return LocomotionSpeed; }
	/** Speed of the scripted position, cm/s. */
	float GetScriptedSpeed() const { return ScriptedSpeed; }
	bool UsesBodyAnimation() const { return bBodyAnimation; }
	const FDinkBodySmoother& GetSmoother() const { return Smoother; }
	/** Posture layer in degrees (chest, head, shoulders) shown on this body. */
	void SetPosture(FVector4f Degrees) { Posture = Degrees; }
	void SetSlowCadencePower(float Power);
private:
	FDinkMotionEstimate Motion;
	FDinkBodyDynamics BodyDynamics;
	FDinkBodySmoother Smoother;
	FVector4f Posture = FVector4f(0, 0, 0, 0);
	FQuat AppliedBodyRotation = FQuat::Identity;
	FQuat LastBodyRotation = FQuat::Identity;
	FVector AppliedLag = FVector::ZeroVector, LastLocation = FVector::ZeroVector;
	bool bBodyRotationApplied = false, bLagApplied = false, bBodyAnimation = false;
	float LocomotionSpeed = 0.f, ScriptedSpeed = 0.f;
	UPROPERTY(Transient)
	TObjectPtr<UBlendSpace> LocomotionAsset;
};
