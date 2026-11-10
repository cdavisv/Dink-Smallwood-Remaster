#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkHardnessFoundationLibrary.generated.h"
class AActor;
class UWorld;
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
    /** Bounded actual-world candidate; copies all loaded controls except the
     * two old aggregate hosts. Creates fresh marked031/209 hosts, never clears
     * or clones their legacy collision. Saves only absent owned candidates. */
    UFUNCTION(BlueprintCallable,Category="Dink|Hardness")
    static FString StageTwoBarrelWorldV1(UWorld* SourceWorld,const FString& BundleDir,
        const FString& DescriptorDir,const FString& TargetWorldPackage,const TArray<FString>& ArtManifestFiles);
    UFUNCTION(BlueprintCallable,Category="Dink|Hardness")
    static FString VerifyFoundationInstanceV1(const FString& BundleDir,AActor* Host);
};
