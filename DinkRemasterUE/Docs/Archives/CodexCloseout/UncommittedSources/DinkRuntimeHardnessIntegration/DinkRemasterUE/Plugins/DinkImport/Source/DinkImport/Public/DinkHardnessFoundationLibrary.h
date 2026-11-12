#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkHardnessFoundationLibrary.generated.h"
class AActor;
/** Explicit review/staging tools. No automatic generation, save, world edit or
 * canonical overwrite; caller must use an approved isolated project. */
UCLASS()
class DINKIMPORT_API UDinkHardnessFoundationLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable,Category="Dink|Hardness")
    static FString PrepareFoundationV1(const FString& BundleDir,int32 Screen);
    /** Only an empty host in /Game/Dink/RuntimeHardnessV1/Worlds/. Complete
     * explicit art manifest list required; authored screens remain unmarked. */
    UFUNCTION(BlueprintCallable,Category="Dink|Hardness")
    static FString StageFoundationHostV1(const FString& BundleDir,const FString& DescriptorFile,
        AActor* Host,AActor* Volume,const TArray<FString>& ArtManifestFiles);
    UFUNCTION(BlueprintCallable,Category="Dink|Hardness")
    static FString VerifyFoundationInstanceV1(const FString& BundleDir,AActor* Host);
};
