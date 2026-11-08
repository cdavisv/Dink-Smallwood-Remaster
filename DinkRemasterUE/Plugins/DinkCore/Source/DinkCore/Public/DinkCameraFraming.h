#pragma once
#include "CoreMinimal.h"

namespace DinkCameraFraming
{
/** A camera-only translation must satisfy Dot(Normal, Translation) >= Minimum. */
struct FPlane
{
    FVector2D Normal;
    double Minimum=0;
};

namespace Detail
{
inline double Length(const FVector2D& V)
{
    const double Scale=FMath::Max(FMath::Abs(V.X),FMath::Abs(V.Y));
    if (Scale==0) return 0;
    return Scale*FMath::Sqrt(FMath::Square(V.X/Scale)+FMath::Square(V.Y/Scale));
}
}

/** Nearest feasible point to the origin, bounded by MaxDistance. No pawn, input or world state.
 * In2D a convex closest point is the origin, a projection onto one boundary, or a two-boundary
 * intersection. Enumerating those candidates avoids an iterative solver or order-dependent clamps.
 * Failure clears Out. Zero-normal tautologies are ignored; a positive zero-normal plane is invalid.
 */
inline bool FindMinimumTranslation(const TArray<FPlane>& Planes,double MaxDistance,FVector2D& Out)
{
    Out=FVector2D::ZeroVector;
    if (!FMath::IsFinite(MaxDistance) || MaxDistance<0) return false;
    const double Tolerance=1.e-7+1.e-10*MaxDistance;
    TArray<FPlane> UnitPlanes;
    UnitPlanes.Reserve(Planes.Num());
    for (const FPlane& P : Planes)
    {
        if (!FMath::IsFinite(P.Normal.X) || !FMath::IsFinite(P.Normal.Y) || !FMath::IsFinite(P.Minimum)) return false;
        const double Scale=FMath::Max(FMath::Abs(P.Normal.X),FMath::Abs(P.Normal.Y));
        if (Scale==0)
        {
            if (P.Minimum>0) return false;
            continue;
        }
        // Divide before taking a length, so very large/small finite normal scales remain valid.
        FVector2D Normal=P.Normal/Scale;
        const double Length=Detail::Length(Normal);
        Normal/=Length;
        const double Minimum=(P.Minimum/Scale)/Length;
        if (!FMath::IsFinite(Minimum))
        {
            // A finite negative minimum whose normalization exceeds the numeric range is redundant
            // within any finite distance bound. The corresponding positive constraint is impossible.
            if (Minimum<0) continue;
            return false;
        }
        if (Minimum>MaxDistance+Tolerance) return false;
        if (Minimum < -MaxDistance-Tolerance) continue;
        UnitPlanes.Add({Normal,Minimum});
    }
    const auto Feasible=[&](const FVector2D& Point)
    {
        for (const FPlane& P : UnitPlanes)
            if (FVector2D::DotProduct(P.Normal,Point)<P.Minimum-Tolerance) return false;
        return true;
    };
    if (Feasible(FVector2D::ZeroVector)) return true;
    bool Found=false;
    double BestDistance=0;
    FVector2D Best=FVector2D::ZeroVector;
    const auto Consider=[&](const FVector2D& Point)
    {
        if (!FMath::IsFinite(Point.X) || !FMath::IsFinite(Point.Y)) return;
        const double Distance=Detail::Length(Point);
        if (!FMath::IsFinite(Distance) || Distance>MaxDistance+Tolerance || !Feasible(Point)) return;
        if (!Found || Distance<BestDistance) { Found=true; BestDistance=Distance; Best=Point; }
    };
    for (const FPlane& P : UnitPlanes) Consider(P.Normal*P.Minimum);
    for (int32 I=0; I<UnitPlanes.Num(); ++I)
    {
        const FPlane& A=UnitPlanes[I];
        for (int32 J=I+1; J<UnitPlanes.Num(); ++J)
        {
            const FPlane& B=UnitPlanes[J];
            const double Determinant=A.Normal.X*B.Normal.Y-A.Normal.Y*B.Normal.X;
            if (Determinant==0) continue;
            Consider(FVector2D((A.Minimum*B.Normal.Y-A.Normal.Y*B.Minimum)/Determinant,
                              (A.Normal.X*B.Minimum-A.Minimum*B.Normal.X)/Determinant));
        }
    }
    if (Found) Out=Best;
    return Found;
}
}
