#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkHeroInspectionLibrary.generated.h"

class USkeleton;
class USkeletalMesh;
class UTexture2D;

/** Detached editor readback only. Never imports, builds, assigns, dirties or saves assets. */
UCLASS()
class DINKIMPORT_API UDinkHeroInspectionLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintPure, Category="Dink|Art|Inspection")
    static FString InspectSkeletonReference(USkeleton* Skeleton);

    /** Full-stream hashes/statistics plus at most64 explicit vertex samples per representation. */
    UFUNCTION(BlueprintPure, Category="Dink|Art|Inspection")
    static FString InspectSkeletalMeshLod(USkeletalMesh* Mesh, int32 LODIndex, const TArray<int32>& SampleVertices);

    /** Source and saved platform mip metadata/hashes; at most64 pixels, explicit unsupported formats. */
    UFUNCTION(BlueprintPure, Category="Dink|Art|Inspection")
    static FString InspectTexturePixels(UTexture2D* Texture, const TArray<FIntPoint>& Pixels);
};
