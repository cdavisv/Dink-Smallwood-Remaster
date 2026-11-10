#pragma once
#include "CoreMinimal.h"

/**
 * Player-only, distance-driven body language. Never moves the capsule, never locks input and
 * never consumes story/combat RNG.
 *
 * Dink starts scrawny, timid and uncoordinated: a hunched, head-down stance, a lopsided goofy
 * run, shoulders that lag every corner, frequent landing catch-steps and the occasional flail on
 * takeoff that ends in a pratfall. Confidence (0 = new game, 1 = late-game hero, see
 * ConfidenceFor) is earned through levels and stats and gradually straightens his back, evens
 * his stride, steadies his landings and fills out his frame.
 */
struct FDinkHeroPhysicality
{
    /** Timid (confidence 0) baseline lean. Authored bone-level posture may replace it. */
    static constexpr float BaselinePitch = -3.6f;
    /** Upright, chin-up baseline of a confident Dink (confidence 1). */
    static constexpr float ConfidentPitch = .4f;

    /** 0..1 from the player's stats: mostly level, partly raw strength and defense. */
    static float ConfidenceFor(int32 Level, int32 Strength, int32 Defense)
    {
        const float Levels = FMath::Clamp((Level - 1) / 11.f, 0.f, 1.f);
        const float Power = FMath::Clamp((Strength + Defense - 3) / 25.f, 0.f, 1.f);
        const float Raw = .7f * Levels + .3f * Power;
        return Raw * Raw * (3.f - 2.f * Raw); // slow start, visible mid-game growth, plateau
    }

    /** The confidence the body eases towards (a level-up straightens him over ~3 s). */
    void SetTargetConfidence(float Value, bool bSnap = false)
    {
        TargetConfidence = FMath::IsFinite(Value) ? FMath::Clamp(Value, 0.f, 1.f) : 0.f;
        if (bSnap) Confidence = TargetConfidence;
    }
    float GetConfidence() const { return Confidence; }
    float GetBaselinePitch() const { return FMath::Lerp(BaselinePitch, ConfidentPitch, Confidence); }
    /** The timid part of the baseline: what an authored bone-level slouch replaces. */
    float GetHunchPitch() const { return BaselinePitch * (1.f - Confidence); }

    /** Scrawny shoulders/chest that fill out with confidence; X/Y width, Z height. */
    FVector GetPhysiqueScale() const
    {
        const float Width = FMath::Lerp(.86f, 1.f, Confidence);
        return FVector(Width, Width, FMath::Lerp(.985f, 1.f, Confidence));
    }

    /** Scale for a gameplay chance: unchanged when timid, MinScale when fully confident. */
    float ScaleChance(float Chance, float MinScale) const
    {
        return FMath::Clamp(Chance, 0.f, 1.f) * FMath::Lerp(1.f, MinScale, Confidence);
    }

    /** An actual jump left the ground. A clumsy takeoff flails and guarantees a hard landing. */
    bool TakeOff(float FlailChance)
    {
        if (Recovery > 0.f) BeginRecoveryBlend();
        Recovery = 0.f; bPratfall = false;
        bFlailing = Random.FRand() < FMath::Clamp(FlailChance, 0.f, 1.f);
        FlailTime = 0.f;
        if (bFlailing) StumbleSide = Random.FRand() < .5f ? -1.f : 1.f;
        return bFlailing;
    }

    bool Land(float ImpactSpeed, float AirSeconds, float Chance)
    {
        const bool Flailed = bFlailing;
        bFlailing = false;
        if (ImpactSpeed < 220.f || AirSeconds < .18f || Cooldown > 0.f) return false;
        if (!Flailed && Random.FRand() >= FMath::Clamp(Chance, 0.f, 1.f)) return false;
        bPratfall = Flailed;
        RecoveryDuration = bPratfall ? PratfallDuration : StumbleDuration;
        Recovery = RecoveryDuration;
        Cooldown = 1.8f;
        if (!Flailed) StumbleSide = Random.FRand() < .5f ? -1.f : 1.f;
        return true;
    }

    /** Running stumble over his own feet; rare, and gone entirely once confident. */
    bool Trip()
    {
        if (Cooldown > 0.f || Recovery > 0.f) return false;
        bPratfall = false;
        RecoveryDuration = StumbleDuration;
        Recovery = RecoveryDuration;
        Cooldown = 4.f;
        StumbleSide = Random.FRand() < .5f ? -1.f : 1.f;
        return true;
    }

    void Update(float DeltaTime, float Speed, bool Grounded, bool Allowed, float TurnRate = 0.f,
        float TripsPerRunSecond = 0.f)
    {
        if (!Allowed) { Cancel(); return; }
        if (DeltaTime <= SMALL_NUMBER || !FMath::IsFinite(DeltaTime)) return;
        Speed = FMath::IsFinite(Speed) ? FMath::Max(0.f, Speed) : 0.f;
        TurnRate = FMath::IsFinite(TurnRate) ? TurnRate : 0.f;
        Confidence = FMath::FInterpConstantTo(Confidence, TargetConfidence, DeltaTime, .35f);
        const float Timid = 1.f - Confidence;
        Cooldown = FMath::Max(0.f, Cooldown - DeltaTime);
        // A fresh takeoff cancels a previous landing's catch-step, without rearming its cooldown;
        // the pose eases out of it rather than snapping upright in one frame.
        if (!Grounded && Recovery > 0.f) BeginRecoveryBlend();
        Recovery = Grounded ? FMath::Max(0.f, Recovery - DeltaTime) : 0.f;
        BlendLeft = FMath::Max(0.f, BlendLeft - DeltaTime);
        if (Grounded) bFlailing = false; else if (bFlailing) FlailTime += DeltaTime;
        const float DistanceSpeed = bReady ? .5f * (Speed + PreviousSpeed) : Speed;
        const float SpeedChange = bReady ? (Speed - PreviousSpeed) / DeltaTime : 0.f;
        PreviousSpeed = Speed; bReady = true;
        const float Start = FMath::Clamp(SpeedChange / 1100.f, 0.f, 1.f);
        const float Stop = FMath::Clamp(-SpeedChange / 1100.f, 0.f, 1.f);
        const float LurchScale = FMath::Lerp(.35f, 1.f, Timid);
        const float TargetLurch = Grounded ? LurchScale * (-2.1f * Start - 4.2f * Stop) : 0.f;
        Lurch = FMath::Lerp(Lurch, TargetLurch, 1.f - FMath::Exp(-DeltaTime * (TargetLurch < Lurch ? 12.f : 4.f)));
        Turn = FMath::Lerp(Turn, Grounded ? FMath::Clamp(TurnRate / 300.f, -1.f, 1.f) : 0.f,
            1.f - FMath::Exp(-DeltaTime * FMath::Lerp(10.f, 6.f, Timid)));
        const float WeightTarget = Grounded ? FMath::Clamp(Speed / 180.f, 0.f, 1.f) : 0.f;
        Weight = FMath::Lerp(Weight, WeightTarget, 1.f - FMath::Exp(-DeltaTime * 9.f));
        // Running (above walking pace) is where the goofiness shows most.
        const float RunTarget = Grounded ? FMath::Clamp((Speed - 250.f) / 300.f, 0.f, 1.f) : 0.f;
        Run = FMath::Lerp(Run, RunTarget, 1.f - FMath::Exp(-DeltaTime * 6.f));
        const double Stride = FMath::Lerp(135., 215., FMath::Clamp((Speed - 200.) / 400., 0., 1.));
        if (Grounded) Phase = FMath::Fmod(Phase + DistanceSpeed * DeltaTime * 2. * PI / Stride, 2. * PI);
        IdlePhase = FMath::Fmod(IdlePhase + DeltaTime * 1.3, 2. * PI);
        MopePhase = FMath::Fmod(MopePhase + DeltaTime * .37, 2. * PI);
        if (Grounded && TripsPerRunSecond > 0.f && Run > .8f && Timid > .05f &&
            Random.FRand() < TripsPerRunSecond * Timid * DeltaTime) Trip();

        // Unequal left/right beats, a drooping stance and shoulders which lag a corner. A timid
        // Dink limps on one beat and flops on the other; a confident one keeps an even cadence.
        const double Gait = Phase + FMath::Lerp(.04, .3, Timid) * FMath::Sin(Phase);
        const float Idle = Grounded ? 1.f - Weight : 0.f;
        const float Sway = FMath::Lerp(1.1f, 3.4f, Timid);
        const float Flop = Run * Timid; // knock-kneed, arms-everywhere run
        // A sad little sigh: every few seconds a timid idle Dink sags and stares at his feet.
        const float Mope = Idle * Timid * FMath::Max(0.f, (float)FMath::Sin(MopePhase)) *
            FMath::Max(0.f, (float)FMath::Sin(MopePhase * 3.));
        Rotation = FRotator(GetBaselinePitch() - Weight * FMath::Lerp(.6, 1.7, Timid) * (1. + .55 * FMath::Sin(Gait * 2. + .3))
                + Lurch + Idle * FMath::Lerp(.15, .35, Timid) * FMath::Sin(IdlePhase) - 2.2f * Mope
                - Flop * (1.2 + 1.4 * FMath::Abs(FMath::Sin(Gait))),
            Weight * FMath::Lerp(.8, 2.4, Timid) * FMath::Sin(Gait + .4) - Turn * FMath::Lerp(1.4, 4.4, Timid)
                + Flop * 2.6 * FMath::Sin(Gait * 2. + 1.1),
            Weight * (Sway * FMath::Sin(Gait) + .6 * Timid * FMath::Sin(Gait * 2. + .6))
                + Flop * 2.4 * FMath::Sin(Gait + .9)
                - Turn * FMath::Lerp(.8, 2.2, Timid) + Idle * .35 * Timid * FMath::Sin(IdlePhase * .5));
        Offset = FVector(Weight * .8 * FMath::Sin(Gait * 2.) - Lurch * .65,
            Weight * FMath::Lerp(.5, 1.4, Timid) * FMath::Sin(Gait) + Turn * .8 * Timid,
            -Weight * FMath::Lerp(.5, 1.1, Timid) * FMath::Abs(FMath::Sin(Gait))
                - .4 * Weight * FMath::Abs(FMath::Sin(Gait * 2.))
                + Flop * 2.2 * (FMath::Abs(FMath::Sin(Gait)) - .5)); // bouncy, boing-boing run
        if (bFlailing)
        {
            // Pinwheeling in mid-air: rocks back, then wobbles side to side looking for balance.
            const double W = FMath::Min(1., FlailTime / .12);
            Rotation.Pitch += W * (4.5 + 3. * FMath::Sin(FlailTime * 23.));
            Rotation.Roll += W * StumbleSide * 7. * FMath::Sin(FlailTime * 17.);
            Rotation.Yaw += W * StumbleSide * 4. * FMath::Sin(FlailTime * 11. + .7);
        }
        if (IsStumbling())
        {
            const double T = 1. - Recovery / RecoveryDuration;
            if (bPratfall)
            {
                // Faceplant: pitch over fast, lie there a moment, then sheepishly push back up.
                const double Down = T < .18 ? FMath::InterpEaseOut(0., 1., T / .18, 2.)
                    : (T < .55 ? 1. : FMath::InterpEaseInOut(1., 0., (T - .55) / .45, 2.));
                const double Shake = T > .55 ? FMath::Sin(4. * PI * (T - .55) / .45) * (1. - T) : 0.;
                Rotation.Pitch += -34. * Down + 4. * Shake;
                Rotation.Roll += StumbleSide * (6. * Down + 3. * Shake);
                Rotation.Yaw += StumbleSide * 6. * Down;
                Offset += FVector(18. * Down, StumbleSide * 4. * Down, -8. * Down);
            }
            else
            {
                const double Envelope = FMath::Sin(PI * T);
                // Dip, two uncoordinated corrections, then settle. Input and root motion stay free.
                Rotation.Pitch += Envelope * (-12.5 + 3.5 * FMath::Sin(3. * PI * T));
                Rotation.Roll += StumbleSide * 7. * FMath::Sin(2. * PI * T) * Envelope;
                Rotation.Yaw += StumbleSide * 5.5 * Envelope;
                Offset += FVector(7. * Envelope, StumbleSide * 3. * Envelope,
                    -3. * Envelope * FMath::Abs(FMath::Sin(3. * PI * T)));
            }
        }
        if (BlendLeft > 0.f)
        {
            // Ease from the interrupted stumble/pratfall pose into the newly computed one.
            const float Alpha = FMath::InterpEaseInOut(0.f, 1.f, 1.f - BlendLeft / RecoveryBlendTime, 2.f);
            Rotation = FMath::Lerp(BlendFromRotation, Rotation, Alpha);
            Offset = FMath::Lerp(BlendFromOffset, Offset, Alpha);
        }
        const bool Fall = (IsStumbling() && bPratfall) || BlendLeft > 0.f;
        Rotation.Pitch = FMath::Clamp(Rotation.Pitch, Fall ? -40. : -20., 6.);
        Rotation.Roll = FMath::Clamp(Rotation.Roll, -9., 9.);
        Rotation.Yaw = FMath::Clamp(Rotation.Yaw, -8., 8.);
        Offset = Offset.GetClampedToMaxSize(Fall ? 24. : 12.);
    }
    bool IsStumbling() const { return Recovery > 0.f; }
    bool IsPratfall() const { return Recovery > 0.f && bPratfall; }
    bool IsFlailing() const { return bFlailing; }
    const FRotator& GetRotation() const { return Rotation; }
    const FVector& GetOffset() const { return Offset; }
    /** Drops every transient motion. Confidence is earned, so it survives teleports/cutscenes. */
    void Cancel()
    {
        Recovery = Cooldown = Weight = Lurch = Turn = Run = PreviousSpeed = FlailTime = BlendLeft = 0.f;
        Phase = IdlePhase = MopePhase = 0.; bReady = bFlailing = bPratfall = false;
        Rotation = FRotator::ZeroRotator; Offset = FVector::ZeroVector;
    }
private:
    void BeginRecoveryBlend()
    {
        BlendFromRotation = Rotation; BlendFromOffset = Offset; BlendLeft = RecoveryBlendTime;
    }
    static constexpr float RecoveryBlendTime = .22f;
    static constexpr float StumbleDuration = .85f;
    static constexpr float PratfallDuration = 1.6f;
    FRandomStream Random{1997};
    FRotator Rotation = FRotator::ZeroRotator;
    FVector Offset = FVector::ZeroVector;
    FRotator BlendFromRotation = FRotator::ZeroRotator;
    FVector BlendFromOffset = FVector::ZeroVector;
    float BlendLeft = 0.f;
    double Phase = 0., IdlePhase = 0., MopePhase = 0.;
    float Recovery = 0.f, RecoveryDuration = StumbleDuration, Cooldown = 0.f, Weight = 0.f, StumbleSide = 1.f;
    float PreviousSpeed = 0.f, Lurch = 0.f, Turn = 0.f, Run = 0.f, FlailTime = 0.f;
    float Confidence = 0.f, TargetConfidence = 0.f;
    bool bReady = false, bFlailing = false, bPratfall = false;
};
