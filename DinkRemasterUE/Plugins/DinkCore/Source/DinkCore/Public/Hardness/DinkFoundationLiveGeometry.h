#pragma once

#include "CoreMinimal.h"

struct FBodyInstance;

namespace DinkFoundationLiveGeometry
{
    DINKCORE_API FString TriangleSignature(const FVector3f& A, const FVector3f& B, const FVector3f& C);

    // Reads the registered body's single query/simulation triangle shape under
    // the physics lock. The optional pose is the runtime verifier's body check.
    DINKCORE_API bool ReadTriangleSignatures(const FBodyInstance& Body, const FTransform* ExpectedBodyPose,
        TArray<FString>& Out, FString& Error);
}
