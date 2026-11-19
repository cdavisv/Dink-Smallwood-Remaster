#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkPhysicsAssetLibrary.generated.h"

class UPhysicsAsset;

/** Editor helpers for the characters' physics assets (constraint limits). Python cannot reach the constraint setup. */
UCLASS()
class DINKIMPORT_API UDinkPhysicsAssetLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** One line per constraint: bones, swing1/swing2/twist motion and limit (degrees). */
	UFUNCTION(BlueprintCallable, Category = "Dink|Physics")
	static FString DescribeConstraints(UPhysicsAsset* Asset);
	/** Brings every constraint of a humanoid (mannequin bone names) within human joint ranges: a free axis becomes
	 * limited, a limit wider than the range is narrowed to it, a tighter one is kept. Linear motion is locked. Returns the
	 * number of constraints changed; marks the asset dirty (the caller saves it). */
	UFUNCTION(BlueprintCallable, Category = "Dink|Physics")
	static int32 ClampHumanJointLimits(UPhysicsAsset* Asset);
};
