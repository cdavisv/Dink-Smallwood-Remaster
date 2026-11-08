#pragma once
#include "CoreMinimal.h"
#include "DinkMotionEstimate.h"
#include "Components/SkeletalMeshComponent.h"
#include "DinkCreatureComponent.generated.h"
class UBlendSpace;
class UAnimSequence;
struct DINKCORE_API FDinkCreaturePresentation
{
	FName FoodBone = TEXT("head");
	float FoodRadiusCm = 70.f;
	float FoodForwardDot = .5f;
	float StationarySpeedCmS = 5.f;
	float NominalWalkSpeedCmS = 80.f;
	float NominalRunSpeedCmS = 0.f;
};
/** Own-rig animated creature attached to an original actor; presentation never writes script state. */
UCLASS(ClassGroup = Dink, meta = (BlueprintSpawnableComponent))
class DINKCORE_API UDinkCreatureComponent : public USkeletalMeshComponent
{
	GENERATED_BODY()
  public:
	UDinkCreatureComponent();
	bool Configure(USkeletalMesh* Mesh, UBlendSpace* Locomotion, UAnimSequence* Feed,
				   const FDinkCreaturePresentation& Settings);
	virtual void TickComponent(float DeltaTime, ELevelTick TickType,
							   FActorComponentTickFunction* ThisTickFunction) override;
	bool CanFeedAt(const FVector& Food) const;
	bool TryFeed(AActor* Food);
	float GetLocomotionSpeed() const
	{
		return SpeedCmS;
	}
	FName GetFoodBone() const { return Settings.FoodBone; }
	bool IsFeeding() const
	{
		return bFeeding;
	}

  private:
	void ResumeLocomotion();
	FDinkCreaturePresentation Settings;
	FDinkMotionEstimate Motion;
	bool bFeeding = false;
	float SpeedCmS = 0.f;
	TSet<TWeakObjectPtr<AActor>> ConsumedFood;
	UPROPERTY(Transient) TObjectPtr<UBlendSpace> Locomotion;
	UPROPERTY(Transient) TObjectPtr<UAnimSequence> Feed;
};
