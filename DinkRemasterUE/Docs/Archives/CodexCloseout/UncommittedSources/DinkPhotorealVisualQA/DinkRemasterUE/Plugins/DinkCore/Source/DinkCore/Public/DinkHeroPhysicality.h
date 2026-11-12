#pragma once
#include "CoreMinimal.h"

/** Dink's awkward secondary animation, layered over locomotion without moving the gameplay root.
 * Landing rolls have a private seeded stream: cosmetic luck never consumes combat/story randomness. */
struct FDinkHeroPhysicality
{
    bool Land(float ImpactSpeed, float AirSeconds, float Chance)
    {
        if (ImpactSpeed < 220.f || AirSeconds < .18f || Cooldown > 0.f) return false;
        if (Random.FRand() >= FMath::Clamp(Chance, 0.f, 1.f)) return false;
        Recovery = RecoveryDuration;
        Cooldown = 1.6f;
        StumbleSide = Random.FRand() < .5f ? -1.f : 1.f;
        return true;
    }
    void Update(float DeltaTime, float Speed, bool Grounded, bool Allowed)
    {
        if (DeltaTime <= SMALL_NUMBER) return;
        if (!Allowed) { Cancel(); return; }
        Cooldown = FMath::Max(0.f, Cooldown - DeltaTime);
        Recovery = FMath::Max(0.f, Recovery - DeltaTime);
        const float WeightTarget = Grounded ? FMath::Clamp(Speed / 180.f, 0.f, 1.f) : 0.f;
        Weight = FMath::FInterpTo(Weight, WeightTarget, DeltaTime, 9.f);
        const double Stride = FMath::Lerp(145., 230., FMath::Clamp((Speed-200.) / 400., 0., 1.));
        if (Grounded) Phase = FMath::Fmod(Phase + Speed * DeltaTime * 2. * PI / Stride, 2. * PI);
        // An uneven shuffle, a slight hunch, and shoulders that lag his feet.
        Rotation = FRotator(-1.2 - Weight * (1.1 + .55 * FMath::Sin(Phase * 2.)),
            Weight * 1.4 * FMath::Sin(Phase + .4),
            Weight * (1.5 * FMath::Sin(Phase) + .4 * FMath::Sin(Phase * 2. + .6)));
        Offset = FVector(0, Weight * .8 * FMath::Sin(Phase), -Weight * 1.2 * FMath::Abs(FMath::Sin(Phase)));
        if (IsStumbling())
        {
            const double T = 1. - Recovery / RecoveryDuration;
            const double Envelope = FMath::Sin(PI * T);
            Rotation.Pitch += Envelope * (-8. + 3. * FMath::Sin(3. * PI * T));
            Rotation.Roll += StumbleSide * 5. * FMath::Sin(2. * PI * T) * Envelope;
            Rotation.Yaw += StumbleSide * 4. * Envelope;
            Offset += FVector(5. * Envelope, StumbleSide * 2. * Envelope,
                -2. * Envelope * FMath::Abs(FMath::Sin(3. * PI * T)));
        }
    }
    bool IsStumbling() const { return Recovery > 0.f; }
    const FRotator& GetRotation() const { return Rotation; }
    const FVector& GetOffset() const { return Offset; }
    void Cancel()
    {
        Recovery = Cooldown = Weight = 0.f;
        Phase = 0.; Rotation = FRotator::ZeroRotator; Offset = FVector::ZeroVector;
    }
private:
    static constexpr float RecoveryDuration = .7f;
    FRandomStream Random{1997};
    FRotator Rotation = FRotator::ZeroRotator;
    FVector Offset = FVector::ZeroVector;
    double Phase = 0.;
    float Recovery = 0.f, Cooldown = 0.f, Weight = 0.f, StumbleSide = 1.f;
};
