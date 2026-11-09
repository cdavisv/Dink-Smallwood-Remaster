#pragma once
#include "CoreMinimal.h"

/** Player-only, distance-driven clumsiness. Never moves the capsule or consumes story/combat RNG. */
struct FDinkHeroPhysicality
{
    // Authored bone-level posture may replace this baseline while retaining the moving layer.
    static constexpr float BaselinePitch = -2.4f;

    bool Land(float ImpactSpeed, float AirSeconds, float Chance)
    {
        if (ImpactSpeed < 220.f || AirSeconds < .18f || Cooldown > 0.f) return false;
        if (Random.FRand() >= FMath::Clamp(Chance, 0.f, 1.f)) return false;
        Recovery = RecoveryDuration;
        Cooldown = 1.8f;
        StumbleSide = Random.FRand() < .5f ? -1.f : 1.f;
        return true;
    }
    void Update(float DeltaTime, float Speed, bool Grounded, bool Allowed, float TurnRate = 0.f)
    {
        if (!Allowed) { Cancel(); return; }
        if (DeltaTime <= SMALL_NUMBER || !FMath::IsFinite(DeltaTime)) return;
        Speed = FMath::IsFinite(Speed) ? FMath::Max(0.f, Speed) : 0.f;
        TurnRate = FMath::IsFinite(TurnRate) ? TurnRate : 0.f;
        Cooldown = FMath::Max(0.f, Cooldown - DeltaTime);
        // A fresh takeoff cancels a previous landing's catch-step, without rearming its cooldown.
        Recovery = Grounded ? FMath::Max(0.f, Recovery - DeltaTime) : 0.f;
        const float DistanceSpeed = bReady ? .5f * (Speed + PreviousSpeed) : Speed;
        const float SpeedChange = bReady ? (Speed - PreviousSpeed) / DeltaTime : 0.f;
        PreviousSpeed = Speed; bReady = true;
        const float Start = FMath::Clamp(SpeedChange / 1100.f, 0.f, 1.f);
        const float Stop = FMath::Clamp(-SpeedChange / 1100.f, 0.f, 1.f);
        const float TargetLurch = Grounded ? -2.1f * Start - 4.2f * Stop : 0.f;
        Lurch = FMath::Lerp(Lurch, TargetLurch, 1.f - FMath::Exp(-DeltaTime * (TargetLurch < Lurch ? 12.f : 4.f)));
        Turn = FMath::Lerp(Turn, Grounded ? FMath::Clamp(TurnRate / 300.f, -1.f, 1.f) : 0.f,
            1.f - FMath::Exp(-DeltaTime * 6.f));
        const float WeightTarget = Grounded ? FMath::Clamp(Speed / 180.f, 0.f, 1.f) : 0.f;
        Weight = FMath::Lerp(Weight, WeightTarget, 1.f - FMath::Exp(-DeltaTime * 9.f));
        const double Stride = FMath::Lerp(135., 215., FMath::Clamp((Speed - 200.) / 400., 0., 1.));
        if (Grounded) Phase = FMath::Fmod(Phase + DistanceSpeed * DeltaTime * 2. * PI / Stride, 2. * PI);
        IdlePhase = FMath::Fmod(IdlePhase + DeltaTime * 1.3, 2. * PI);
        // Unequal left/right beats, a drooping stance, and shoulders which lag a corner.
        const double Gait = Phase + .22 * FMath::Sin(Phase);
        const float Idle = Grounded ? 1.f - Weight : 0.f;
        Rotation = FRotator(BaselinePitch - Weight * (1.6 + .9 * FMath::Sin(Gait * 2. + .3))
                + Lurch + Idle * .3 * FMath::Sin(IdlePhase),
            Weight * 2.2 * FMath::Sin(Gait + .4) - Turn * 4.,
            Weight * (3.2 * FMath::Sin(Gait) + .6 * FMath::Sin(Gait * 2. + .6))
                - Turn * 2. + Idle * .35 * FMath::Sin(IdlePhase * .5));
        Offset = FVector(Weight * .8 * FMath::Sin(Gait * 2.) - Lurch * .65,
            Weight * 1.35 * FMath::Sin(Gait) + Turn * .8,
            -Weight * (1.1 * FMath::Abs(FMath::Sin(Gait)) + .4 * FMath::Abs(FMath::Sin(Gait * 2.))));
        if (IsStumbling())
        {
            const double T = 1. - Recovery / RecoveryDuration;
            const double Envelope = FMath::Sin(PI * T);
            // Dip, two uncoordinated corrections, then settle. Input and root motion stay free.
            Rotation.Pitch += Envelope * (-12.5 + 3.5 * FMath::Sin(3. * PI * T));
            Rotation.Roll += StumbleSide * 7. * FMath::Sin(2. * PI * T) * Envelope;
            Rotation.Yaw += StumbleSide * 5.5 * Envelope;
            Offset += FVector(7. * Envelope, StumbleSide * 3. * Envelope,
                -3. * Envelope * FMath::Abs(FMath::Sin(3. * PI * T)));
        }
        Rotation.Pitch = FMath::Clamp(Rotation.Pitch, -20., 6.);
        Rotation.Roll = FMath::Clamp(Rotation.Roll, -9., 9.);
        Rotation.Yaw = FMath::Clamp(Rotation.Yaw, -8., 8.);
        Offset = Offset.GetClampedToMaxSize(12.);
    }
    bool IsStumbling() const { return Recovery > 0.f; }
    const FRotator& GetRotation() const { return Rotation; }
    const FVector& GetOffset() const { return Offset; }
    void Cancel()
    {
        Recovery = Cooldown = Weight = Lurch = Turn = PreviousSpeed = 0.f;
        Phase = IdlePhase = 0.; bReady = false;
        Rotation = FRotator::ZeroRotator; Offset = FVector::ZeroVector;
    }
private:
    static constexpr float RecoveryDuration = .85f;
    FRandomStream Random{1997};
    FRotator Rotation = FRotator::ZeroRotator;
    FVector Offset = FVector::ZeroVector;
    double Phase = 0., IdlePhase = 0.;
    float Recovery = 0.f, Cooldown = 0.f, Weight = 0.f, StumbleSide = 1.f;
    float PreviousSpeed = 0.f, Lurch = 0.f, Turn = 0.f;
    bool bReady = false;
};
