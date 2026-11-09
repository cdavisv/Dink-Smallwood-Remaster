#pragma once

#include "CoreMinimal.h"
#include "DinkMotionEstimate.h"
#include "DinkBodyDynamics.h"
#include "Components/SkeletalMeshComponent.h"
#include "DinkHumanoidComponent.generated.h"

class UBlendSpace;

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
	void Configure(USkeletalMesh* Mesh, UBlendSpace* Locomotion);
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	float GetLocomotionSpeed() const { return LocomotionSpeed; }
private:
	FDinkMotionEstimate Motion;
	FDinkBodyDynamics BodyDynamics;
	FQuat AppliedBodyRotation = FQuat::Identity;
	FQuat LastBodyRotation = FQuat::Identity;
	bool bBodyRotationApplied = false;
	float LocomotionSpeed = 0.f;
	UPROPERTY(Transient)
	TObjectPtr<UBlendSpace> LocomotionAsset;
};
