#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkCharacterArtLibrary.generated.h"

class USkeletalMesh;
class UMaterial;
class UMaterialExpression;
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
	/** Connects an expression output to one of the two custom-data pins of a material. The Hair shading
	 * model reads its back-light amount from the first; both are hidden from Python's property enum, so
	 * the importer cannot reach them through the material editing library. Slot 0 or 1; an empty output
	 * name takes the first output. False when the material, expression, slot or output is not valid. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Art")
	static bool ConnectMaterialCustomData(UMaterial* Material, UMaterialExpression* Expression, const FString& OutputName, int32 Slot);
};
