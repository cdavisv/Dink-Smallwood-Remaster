#pragma once
#include "CoreMinimal.h"

/**
 * Player-only body language state. Never moves the capsule, never locks input and never
 * consumes story/combat RNG.
 *
 * Dink starts as an unsure, scrawny farm lad and grows into a hero: confidence (0 = new game,
 * 1 = late game, see ConfidenceFor) is earned through levels and stats. The animation layer
 * (UDinkBodyAnimInstance) turns it into posture and gait by mixing authored timid and confident
 * clips; nothing here rocks, bounces or tips the mesh any more. What remains procedural is what
 * a clip cannot know: a small trunk lean into accelerations and corners, the rare stumble of an
 * untrained runner and how hard a landing was. A stumble is a catch-step he recovers from, not
 * a pratfall.
 */
struct FDinkHeroPhysicality
{
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

    /** A landing. True when it was a clumsy one that needs a catch-step (IsStumbling follows). */
    bool Land(float ImpactSpeed, float AirSeconds, float Chance)
    {
        LandImpact = FMath::Clamp((ImpactSpeed - 150.f) / 450.f, 0.f, 1.f);
        bLanded = AirSeconds >= .12f;
        if (ImpactSpeed < 220.f || AirSeconds < .18f || Cooldown > 0.f) return false;
        if (Random.FRand() >= FMath::Clamp(Chance, 0.f, 1.f)) return false;
        Recovery = StumbleDuration;
        Cooldown = 1.8f;
        bStumbleStarted = true;
        return true;
    }

    /** A running stumble: a toe catches and he recovers in two quick steps. */
    bool Trip()
    {
        if (Cooldown > 0.f || Recovery > 0.f) return false;
        Recovery = StumbleDuration;
        Cooldown = 12.f;
        bStumbleStarted = true;
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
        // Leaving the ground ends a catch-step: the airborne pose takes over.
        Recovery = Grounded ? FMath::Max(0.f, Recovery - DeltaTime) : 0.f;
        const float SpeedChange = bReady ? (Speed - PreviousSpeed) / DeltaTime : 0.f;
        PreviousSpeed = Speed; bReady = true;
        if (Grounded && TripsPerRunSecond > 0.f && Speed > 490.f && Timid > .05f &&
            Random.FRand() < TripsPerRunSecond * Timid * DeltaTime) Trip();
        // Trunk lean, degrees: into the acceleration, back against braking, into a corner.
        // An unsure runner brakes later and harder, so his stops rock him a little more.
        const float Run = FMath::Clamp(Speed / 600.f, 0.f, 1.f);
        FVector2f Target = FVector2f::ZeroVector;
        if (Grounded)
        {
            Target.X = SpeedChange >= 0.f ? FMath::Clamp(SpeedChange / 2048.f, 0.f, 1.f) * MaxStartLean
                : -FMath::Clamp(-SpeedChange / 2048.f, 0.f, 1.f) * MaxStopLean * FMath::Lerp(1.f, 1.3f, Timid);
            Target.Y = -FMath::Clamp(TurnRate / 360.f, -1.f, 1.f) * Run * MaxTurnLean;
        }
        float Remaining = FMath::Min(DeltaTime, .125f);
        while (Remaining > SMALL_NUMBER)
        {
            // Critically damped spring in substeps, so the lean is the same at every frame rate.
            const float Step = FMath::Min(Remaining, 1.f / 120.f);
            LeanVelocity += ((Target - Lean) * 90.f - LeanVelocity * 19.f) * Step;
            Lean += LeanVelocity * Step;
            Remaining -= Step;
        }
    }
    bool IsStumbling() const { return Recovery > 0.f; }
    /** True once after a stumble began (the caller plays the catch-step). */
    bool ConsumeStumbleStart() { const bool B = bStumbleStarted; bStumbleStarted = false; return B; }
    /** True once after a landing; OutImpact is 0 (a hop) to 1 (a hard drop). */
    bool ConsumeLanding(float& OutImpact) { const bool B = bLanded; bLanded = false; OutImpact = LandImpact; return B; }
    /** Trunk lean in degrees: X forward, Y to the character's left. */
    FVector2f GetLean() const { return Lean; }
    /** Drops every transient motion. Confidence is earned, so it survives teleports/cutscenes. */
    void Cancel()
    {
        Recovery = Cooldown = PreviousSpeed = LandImpact = 0.f;
        Lean = LeanVelocity = FVector2f::ZeroVector;
        bReady = bStumbleStarted = bLanded = false;
    }
    static constexpr float StumbleDuration = .85f;
    static constexpr float MaxStartLean = 4.f, MaxStopLean = 3.f, MaxTurnLean = 5.f;
private:
    FRandomStream Random{1997};
    FVector2f Lean = FVector2f::ZeroVector, LeanVelocity = FVector2f::ZeroVector;
    float Recovery = 0.f, Cooldown = 0.f, PreviousSpeed = 0.f, LandImpact = 0.f;
    float Confidence = 0.f, TargetConfidence = 0.f;
    bool bReady = false, bStumbleStarted = false, bLanded = false;
};
