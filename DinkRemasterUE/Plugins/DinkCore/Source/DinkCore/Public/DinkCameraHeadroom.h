#pragma once
#include "CoreMinimal.h"

namespace DinkCameraHeadroom
{
/** Retain the original exterior side without mistaking an edge contact's face normal
 * for the swept sphere's contact normal. Baseline face clearance can be below ProbeSize.
 */
inline bool PreservesExteriorFace(const FVector& BaseEye,const FVector& CandidateEye,
    const FVector& ImpactPoint,const FVector& ImpactNormal)
{
    if (BaseEye.ContainsNaN() || CandidateEye.ContainsNaN() || ImpactPoint.ContainsNaN() ||
        ImpactNormal.ContainsNaN() || ImpactNormal.IsNearlyZero()) return false;
    const double Before=FVector::DotProduct(BaseEye-ImpactPoint,ImpactNormal);
    const double After=FVector::DotProduct(CandidateEye-ImpactPoint,ImpactNormal);
    return Before>0 && After>0 && After+.5>=Before;
}

/** Minimum world-Z eye translation that puts the capsule top below the upper NDC margin.
 * ProjectionY and OffsetY are the actual perspective projection M[1][1] and M[2][1].
 * No world/input state; a non-visible point, invalid projection or infeasible bound fails closed.
 */
inline bool MinimumLift(const FVector& Top, const FVector& Eye, const FVector& Forward,
    const FVector& Up, double ProjectionY, double OffsetY, double MarginNDC,
    double MaxLift, double& OutLift)
{
    OutLift=0;
    if (Top.ContainsNaN() || Eye.ContainsNaN() || Forward.ContainsNaN() || Up.ContainsNaN() ||
        !FMath::IsFinite(ProjectionY) || ProjectionY<=0 || !FMath::IsFinite(OffsetY) ||
        !FMath::IsFinite(MarginNDC) || MarginNDC<0 || MarginNDC>=1 ||
        !FMath::IsFinite(MaxLift) || MaxLift<0 ||
        !FMath::IsNearlyEqual(Forward.SizeSquared(),1.,1.e-5) ||
        !FMath::IsNearlyEqual(Up.SizeSquared(),1.,1.e-5) ||
        FMath::Abs(FVector::DotProduct(Forward,Up))>1.e-5) return false;
    const FVector Delta=Top-Eye;
    const double Depth=FVector::DotProduct(Delta,Forward);
    if (Depth<=1.e-4) return false;
    const double Slope=(1.-MarginNDC-OffsetY)/ProjectionY;
    const double Excess=FVector::DotProduct(Delta,Up)-Slope*Depth;
    if (Excess<=1.e-6) return true;
    const double Improvement=Up.Z-Slope*Forward.Z;
    if (Improvement<=1.e-6) return false;
    const double Lift=Excess/Improvement;
    if (!FMath::IsFinite(Lift) || Lift>MaxLift) return false;
    OutLift=Lift;
    return true;
}
}
