#pragma once

#include "CoreMinimal.h"

/**
 * Foliage between the play camera and Dink (15 Nov 2026). Tree and bush meshes carry no collision (family art, the
 * forest on the canopy tiles), so the spring arm runs straight into a pine crown and the view is needles. A crown is
 * modelled as an upright cylinder from its mesh bounds; one that the camera stands in, or that the lines from the camera
 * to Dink's head, chest and feet pass through, fades (dithered, shadows kept). Presentation only: the boom length never
 * changes for foliage, so the view does not pump while Dink walks through a wood.
 */
namespace DinkCameraFoliage
{
/** An upright cylinder standing for a crown: its axis in world XY, its height range and its radius (cm). */
struct FCrown
{
    FVector2D Axis = FVector2D::ZeroVector;
    double Bottom = 0.0;
    double Top = 0.0;
    double Radius = 0.0;
};

/** Share of the mesh's mean horizontal half extent taken as the crown radius (a crown's bounding box holds its tips). */
constexpr double RadiusShare = 0.8;
/** Meshes lower than this (cm, after scale) never fade: grass, ferns and small shrubs do not hide Dink. */
constexpr double MinimumHeightCm = 150.0;
/** Extra radius (cm) while a crown is already fading, so it does not flicker on its edge. */
constexpr double HoldMarginCm = 40.0;
/** Seconds a crown stays faded after the last frame it was in the way (walking along a crown's edge). */
constexpr double HoldSeconds = 0.35;
/** Opacity change per second: out quickly, back in a little slower. */
constexpr float FadeOutPerSecond = 4.f;
constexpr float FadeInPerSecond = 2.5f;
/** Opacity of a fully faded crown: a trace of it stays, so a wood does not vanish around Dink. */
constexpr float FadedOpacity = 0.f;

/** The crown of a mesh whose local bounding box is LocalBounds, placed by Transform. False for a mesh too low to matter. */
inline bool CrownFromBounds(const FBox& LocalBounds, const FTransform& Transform, FCrown& Out)
{
    if (!LocalBounds.IsValid) return false;
    const FVector Scale = Transform.GetScale3D().GetAbs();
    const FVector Size = LocalBounds.GetSize() * Scale;
    if (!FMath::IsFinite(Size.X) || !FMath::IsFinite(Size.Y) || !FMath::IsFinite(Size.Z) || Size.Z < MinimumHeightCm) return false;
    const FVector Centre = Transform.TransformPosition(LocalBounds.GetCenter());
    Out.Axis = FVector2D(Centre.X, Centre.Y);
    Out.Bottom = Centre.Z - Size.Z * 0.5;
    Out.Top = Centre.Z + Size.Z * 0.5;
    Out.Radius = RadiusShare * 0.25 * (Size.X + Size.Y);
    return Out.Radius > 1.0;
}

/** Whether the segment A-B passes within Radius + Margin of the crown's axis while inside its height range. */
inline bool SegmentCrosses(const FCrown& Crown, const FVector& A, const FVector& B, double Margin)
{
    double T0 = 0.0, T1 = 1.0;
    const double DZ = B.Z - A.Z;
    if (FMath::Abs(DZ) < 1.e-6)
    {
        if (A.Z < Crown.Bottom || A.Z > Crown.Top) return false;
    }
    else
    {
        double Ta = (Crown.Bottom - A.Z) / DZ, Tb = (Crown.Top - A.Z) / DZ;
        if (Ta > Tb) Swap(Ta, Tb);
        T0 = FMath::Max(T0, Ta);
        T1 = FMath::Min(T1, Tb);
        if (T0 > T1) return false;
    }
    const FVector2D P0 = FVector2D(A) + (FVector2D(B) - FVector2D(A)) * T0;
    const FVector2D P1 = FVector2D(A) + (FVector2D(B) - FVector2D(A)) * T1;
    const FVector2D D = P1 - P0;
    const double Length2 = D.SizeSquared();
    const double T = Length2 > 1.e-9 ? FMath::Clamp(FVector2D::DotProduct(Crown.Axis - P0, D) / Length2, 0.0, 1.0) : 0.0;
    const double Reach = Crown.Radius + Margin;
    return FVector2D::DistSquared(P0 + D * T, Crown.Axis) <= Reach * Reach;
}

/** Whether the crown hides Dink: the camera stands in it, or a line from the camera to one of the targets crosses it. */
inline bool Blocks(const FCrown& Crown, const FVector& Eye, TArrayView<const FVector> Targets, double Margin)
{
    for (const FVector& Target : Targets)
    {
        if (SegmentCrosses(Crown, Eye, Target, Margin)) return true;
    }
    return false;
}

/** Whether the crown can matter at all this frame (a cheap XY test before Blocks): within Reach of the eye-to-body segment. */
inline bool Near(const FCrown& Crown, const FVector& Eye, const FVector& Body, double Reach)
{
    FCrown Wide = Crown;
    Wide.Bottom = -TNumericLimits<double>::Max();
    Wide.Top = TNumericLimits<double>::Max();
    return SegmentCrosses(Wide, Eye, Body, Reach);
}

/** One frame of a crown's fade: towards FadedOpacity while it is in the way (or held), back to 1 otherwise. */
inline float StepOpacity(float Opacity, bool bInTheWay, float DeltaSeconds)
{
    const float Target = bInTheWay ? FadedOpacity : 1.f;
    const float Rate = bInTheWay ? FadeOutPerSecond : FadeInPerSecond;
    return FMath::FInterpConstantTo(Opacity, Target, FMath::Max(0.f, DeltaSeconds), Rate);
}
}
