#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "DinkEarlyPostureAnimInstance.generated.h"

/** Parent of the optional post-process graph. The graph applies a local-space additive
 * authored on Dink's unchanged rig; ordinary locomotion and action poses are its input. */
UCLASS(Transient, Blueprintable)
class DINKCORE_API UDinkEarlyPostureAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="Dink|Posture")
    float PostureWeight = 0.f;
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    static float TargetWeight(int32 Story, bool bAllowed, bool bAttacking, bool bAirborne, float Confidence = 0.f);
private:
    FVector PreviousLocation = FVector::ZeroVector;
    bool bHasPreviousLocation = false;
};
