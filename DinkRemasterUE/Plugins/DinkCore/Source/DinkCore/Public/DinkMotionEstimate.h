#pragma once

#include "CoreMinimal.h"

/** Observed root motion over100ms of game time, independent of render-frame/60Hz brain alignment.
 * This is presentation data only; no desired speed, AI properties or movement is inferred. */
struct FDinkMotionEstimate
{
    void Reset()
    {
        HasPrevious = false;
        Time = Path = 0;
        Speed = ImmediateSpeed = 0;
        Samples.Reset();
    }
    float Update(const FVector& Location, float DeltaTime)
    {
        const double Distance = HasPrevious ? FVector::DistXY(Location, Previous) : 0;
        if (!HasPrevious || DeltaTime <= SMALL_NUMBER || FVector::DistSquared(Location, Previous) >= FMath::Square(200.))
        {
            Reset(); HasPrevious = true; Previous = Location;
            Samples.Add({0, 0});
            return 0;
        }
        Previous = Location;
        ImmediateSpeed = float(Distance / DeltaTime);
        Time += DeltaTime; Path += Distance;
        Samples.Add({Time, Path});
        const double Cutoff = FMath::Max(Samples[0].Time, Time - .1);
        while (Samples.Num() > 2 && Samples[1].Time <= Cutoff)
            Samples.RemoveAt(0, 1, EAllowShrinking::No);
        const FSample& A = Samples[0];
        const FSample& B = Samples[1];
        const double Alpha = B.Time > A.Time ? FMath::Clamp((Cutoff - A.Time) / (B.Time - A.Time), 0., 1.) : 0.;
        const double Base = FMath::Lerp(A.Path, B.Path, Alpha);
        Speed = Time > Cutoff ? float(FMath::Max(0., Path - Base) / (Time - Cutoff)) : 0.f;
        if (Speed < .001f) Speed = 0;
        return Speed;
    }
    float GetImmediateSpeed() const { return ImmediateSpeed; }
private:
    struct FSample { double Time, Path; };
    TArray<FSample, TInlineAllocator<32>> Samples;
    FVector Previous = FVector::ZeroVector;
    double Time = 0, Path = 0;
    float Speed = 0, ImmediateSpeed = 0;
    bool HasPrevious = false;
};
