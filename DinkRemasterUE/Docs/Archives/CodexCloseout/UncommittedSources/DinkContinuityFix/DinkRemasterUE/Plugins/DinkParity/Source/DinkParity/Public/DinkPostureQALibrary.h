#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkPostureQALibrary.generated.h"
class UAnimSequence;
class UAnimBlueprint;
class USkeletalMesh;
/** Editor-module-only posture graph construction. Never edits production assets. */
UCLASS()
class DINKPARITY_API UDinkPostureQALibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Creates a new unsaved graph in /Game/DinkQA/Posture/. Refuses existing destinations. */
    UFUNCTION(BlueprintCallable, Category="Dink|QA")
    static UAnimBlueprint* CreatePostureGraph(USkeletalMesh* ReferenceMesh, UAnimSequence* Target, UAnimSequence* Reference, const FString& PackageName);
    UFUNCTION(BlueprintCallable, Category="Dink|QA")
    static bool VerifyPostureGraph(UAnimBlueprint* Blueprint, UAnimSequence* Target, UAnimSequence* Reference);
};
