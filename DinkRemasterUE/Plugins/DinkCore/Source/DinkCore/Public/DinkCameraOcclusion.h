#pragma once

#include "CoreMinimal.h"
#include "Components/StaticMeshComponent.h"

// An inscribed approximation, not an exact arbitrary-frustum collision query.
namespace DinkCameraOcclusion
{
struct FSweep
{
    FVector Start, End, HalfExtent;
    FQuat Rotation;
};
inline bool BuildForegroundSweeps(const FVector& Eye, const FRotator& ViewRotation,
    const FMatrix& Projection, double NearDepth, double FarDepth, TArray<FSweep>& Out)
{
    Out.Reset();
    const double SX=Projection.M[0][0], SY=Projection.M[1][1];
    const double OX=Projection.M[2][0], OY=Projection.M[2][1];
    if (Eye.ContainsNaN() || ViewRotation.ContainsNaN() || !FMath::IsFinite(NearDepth) ||
        !FMath::IsFinite(FarDepth) || NearDepth<=0 || FarDepth<=NearDepth ||
        !FMath::IsFinite(SX) || !FMath::IsFinite(SY) || !FMath::IsFinite(OX) || !FMath::IsFinite(OY) ||
        SX<=1.e-8 || SY<=1.e-8 || !FMath::IsNearlyZero(Projection.M[3][3]) ||
        !FMath::IsNearlyEqual(Projection.M[2][3],1.)) return false;
    const FRotationMatrix Basis(ViewRotation);
    const FVector Forward=Basis.GetUnitAxis(EAxis::X), Right=Basis.GetUnitAxis(EAxis::Y), Up=Basis.GetUnitAxis(EAxis::Z);
    const FVector CentreRay=Forward-Right*(OX/SX)-Up*(OY/SY);
    constexpr double Thickness=.01;
    for (int32 I=0; I<12; ++I)
    {
        const double A=FMath::Lerp(NearDepth,FarDepth,I/12.);
        const double B=FMath::Lerp(NearDepth,FarDepth,(I+1)/12.);
        if (B-A<=2*Thickness) continue;
        // Inset for box thickness and an off-axis projection's moving centreline.
        const double Width=(A-Thickness*FMath::Abs(OX))/SX;
        const double Height=(A-Thickness*FMath::Abs(OY))/SY;
        if (Width<=0 || Height<=0 || !FMath::IsFinite(Width) || !FMath::IsFinite(Height)) return false;
        Out.Add({Eye+CentreRay*(A+Thickness),Eye+CentreRay*(B-Thickness),
            FVector(Thickness,Width,Height),ViewRotation.Quaternion()});
    }
    return !Out.IsEmpty();
}
inline bool Intersects(UStaticMeshComponent* Component,const TArray<FSweep>& Sweeps)
{
    if (!IsValid(Component)) return false;
    const FBox ComponentBox=Component->Bounds.GetBox();
    for (const FSweep& Sweep : Sweeps)
    {
        const FBox LocalBox(-Sweep.HalfExtent,Sweep.HalfExtent);
        FBox Bounds=LocalBox.TransformBy(FTransform(Sweep.Rotation,Sweep.Start));
        Bounds+=LocalBox.TransformBy(FTransform(Sweep.Rotation,Sweep.End));
        if (!Bounds.Intersect(ComponentBox)) continue;
        FHitResult Hit;
        // Actual complex geometry is authoritative; an empty aperture inside bounds stays clear.
        if (Component->SweepComponent(Hit,Sweep.Start,Sweep.End,Sweep.Rotation,
            FCollisionShape::MakeBox(Sweep.HalfExtent),true)) return true;
    }
    return false;
}
}
