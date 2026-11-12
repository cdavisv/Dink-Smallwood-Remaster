#pragma once
#include "CoreMinimal.h"
struct FDinkBundle;
class UStaticMesh;
class UStaticMeshComponent;

/** New generation only. Returns UNSAVED candidate assets; never loads/replaces
 * old CollSolid/CollLow or changes the existing importer/manifest/world. */
struct DINKIMPORT_API FDinkHardnessFoundationCandidate
{
    int32 Screen = 0;
    FVector Pivot = FVector::ZeroVector;
    UStaticMesh* FixedSolid = nullptr; // ground + fill_solid only
    UStaticMesh* FixedLow = nullptr;   // fill_water only; null when absent
    FString CollisionSourceHash;
};
namespace DinkGreybox
{
    DINKIMPORT_API bool VerifyRuntimeHardnessFoundationSourceV1(const FDinkBundle& Bundle,
        const FDinkHardnessFoundationCandidate& Candidate, FString& Error);
    /** Actual registered immutable instance: source triangles, cooked shape
     * triangles/winding, transform, full profile responses, overlap/nav/domain. */
    DINKIMPORT_API bool VerifyRuntimeHardnessFoundationInstanceV1(const FDinkBundle& Bundle,
        const FDinkHardnessFoundationCandidate& Candidate, UStaticMeshComponent& Solid,
        UStaticMeshComponent* Low, FString& Error);
    DINKIMPORT_API bool BuildRuntimeHardnessFoundationV1(const FDinkBundle& Bundle, int32 Screen,
        FDinkHardnessFoundationCandidate& Out, FString& Error);
}
