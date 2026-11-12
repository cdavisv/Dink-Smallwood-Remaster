#pragma once

#include "CoreMinimal.h"

/** Bounded, damped secondary motion. Uses game time and observed motion, never the gameplay RNG.
 * The capsule/script root stays authoritative; the mesh pivots at its existing foot origin. */
struct FDinkBodyDynamics
{
    FRotator Update(const FVector& Location, const FQuat& Facing, float DeltaTime, bool bGrounded = true)
    {
        if (DeltaTime <= SMALL_NUMBER) return FRotator(Lean.X, 0, Lean.Y);
        if (!bReady || FVector::DistSquared(Location, PreviousLocation) >= FMath::Square(200.))
        {
            PreviousLocation = Location; PreviousVelocity = FVector::ZeroVector;
            Lean = LeanVelocity = FVector2D::ZeroVector; bReady = true; bWasGrounded = bGrounded;
            Phase = FMath::Fmod(FMath::Abs(Location.X * .017 + Location.Y * .031), 2. * PI);
            return FRotator::ZeroRotator;
        }
        const FVector Velocity = (Location - PreviousLocation) / DeltaTime;
        const FVector Acceleration = Facing.UnrotateVector((Velocity - PreviousVelocity) / DeltaTime);
        const float Speed = Velocity.Size2D();
        // A little forward posture at speed; spring response on starts, stops and corners.
        FVector2D Target(FMath::Clamp(-Speed * .003 - Acceleration.X * .001, -4., 3.),
                         FMath::Clamp(Acceleration.Y * .0015, -4., 4.));
        if (bGrounded && !bWasGrounded)
            LeanVelocity.X -= FMath::Clamp(FMath::Abs(PreviousVelocity.Z) * .035, 0., 25.);
        // Substeps keep the spring stable at low frame rates.
        float Remaining = FMath::Min(DeltaTime, .125f);
        while (Remaining > SMALL_NUMBER)
        {
            const float Step = FMath::Min(Remaining, 1.f / 120.f);
            LeanVelocity += ((Target - Lean) * 100. - LeanVelocity * 20.) * Step;
            Lean += LeanVelocity * Step;
            Remaining -= Step;
        }
        Lean.X = FMath::Clamp(Lean.X, -5., 5.); Lean.Y = FMath::Clamp(Lean.Y, -4., 4.);
        Phase = FMath::Fmod(Phase + DeltaTime * 1.8, 2. * PI);
        const double Idle = bGrounded ? FMath::Clamp(1. - Speed / 80., 0., 1.) : 0.;
        PreviousLocation = Location; PreviousVelocity = Velocity; bWasGrounded = bGrounded;
        return FRotator(Lean.X + FMath::Sin(Phase) * .18 * Idle, 0,
                        Lean.Y + FMath::Sin(Phase * .5) * .25 * Idle);
    }
    void Reset() { *this = FDinkBodyDynamics(); }
private:
    FVector PreviousLocation = FVector::ZeroVector, PreviousVelocity = FVector::ZeroVector;
    FVector2D Lean = FVector2D::ZeroVector, LeanVelocity = FVector2D::ZeroVector;
    double Phase = 0;
    bool bReady = false, bWasGrounded = true;
};
