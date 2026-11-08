#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkCharacterArtLibrary.generated.h"

class USkeletalMesh;
class UBlendSpace;
class UAnimSequence;

/** Validates Blender/Unreal rigs before assigning an existing animation skeleton. */
UCLASS()
class DINKIMPORT_API UDinkCharacterArtLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** JSON bone names, parents, local bind transforms, bounds and skeleton asset path. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Art")
	static FString InspectRig(USkeletalMesh* Mesh);
	/** Assigns only if all bone names, hierarchy and local bind transforms match. Never alters the reference. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Art")
	static bool AssignMatchingSkeleton(USkeletalMesh* Mesh, USkeletalMesh* Reference);
	/** Configure and rebuild a one-dimensional idle/walk blend space on its own compatible rig. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Art")
	static bool ConfigureCreatureLocomotion(UBlendSpace* Blend, UAnimSequence* Idle, UAnimSequence* Walk, float WalkSpeed, UAnimSequence* Run = nullptr, float RunSpeed = 400.f);
	/** Actual raw pose motion, root displacement and loop seam measurements. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Art")
	static FString InspectCreatureAnimation(UAnimSequence* Animation);
};
