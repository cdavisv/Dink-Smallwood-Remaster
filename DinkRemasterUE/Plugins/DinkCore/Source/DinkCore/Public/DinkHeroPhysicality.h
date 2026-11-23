#pragma once
#include "CoreMinimal.h"

/**
 * Player-only body language state. Never moves the capsule, never locks input and never
 * consumes story/combat RNG.
 *
 * Dink starts as an unsure, scrawny farm lad and grows into a hero: confidence (0 = new game,
 * 1 = late game, see ConfidenceFor) is earned through levels and stats. His build follows it
 * (GetBuild: scrawny, then a farmhand, then brawny). The animation layer
 * (UDinkBodyAnimInstance) turns it into posture and gait by mixing authored timid and confident
 * clips; nothing here rocks, bounces or tips the mesh any more. What remains procedural is what
 * a clip cannot know: a small trunk lean into accelerations and corners, when a toe catches,
 * whether a landing is botched (a stagger, or now and then flat on his face), when he fidgets
 * and how he rocks after over-swinging. Every one of those is a chance or a rate that falls
 * with confidence and is zero for the finished hero; all are drawn from a private stream and
 * none starts in or just after a fight.
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

    /**
     * The build his body shows, for a hero mesh that carries the two build shapes (morph targets
     * Physique_Scrawny and Physique_Brawny, authored by SourceAssets/Art/PhotorealPass/Characters/
     * Tools/physique.py): X = how much of the scrawny shape, Y = how much of the brawny one. The
     * mesh as exported is the build in between, a working farmhand, reached at BuildMidpoint.
     * Only the trunk, neck, arms and legs change; head, hands and feet stay his own.
     */
    static constexpr float BuildMidpoint = .45f;
    static FVector2f BuildFor(float InConfidence)
    {
        const float C = FMath::IsFinite(InConfidence) ? FMath::Clamp(InConfidence, 0.f, 1.f) : 0.f;
        return FVector2f(FMath::Clamp(1.f - C / BuildMidpoint, 0.f, 1.f),
            FMath::Clamp((C - BuildMidpoint) / (1.f - BuildMidpoint), 0.f, 1.f));
    }
    FVector2f GetBuild() const { return BuildFor(Confidence); }
    /** Overall size that goes with the build shapes: the lad is a touch smaller all over, in
     * proportion (nothing is squeezed, unlike GetPhysiqueScale). */
    FVector GetBuildScale() const { return FVector(FMath::Lerp(.975f, 1.f, Confidence)); }

    /** Fallback for a hero mesh WITHOUT the build shapes: a narrower frame that fills out with
     * confidence; X/Y width, Z height. It narrows the head and hands too, which is why the
     * photoreal hero uses GetBuild and GetBuildScale instead. */
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

    /** How clumsy he still is, for a chance or a rate: 1 at new game, falling all the way to 0
     * for the finished hero, and never rising on the way (the mannerism arc is monotone). */
    static float Clumsiness(float InConfidence)
    {
        const float Timid = 1.f - (FMath::IsFinite(InConfidence) ? FMath::Clamp(InConfidence, 0.f, 1.f) : 0.f);
        return Timid * FMath::Sqrt(Timid);
    }
    /** Toe catches per second of travel at this speed: none standing or creeping, the walking
     * rate at a walk, the running rate flat out. */
    static float TripsPerSecond(float Speed, float InConfidence, float RunRate, float WalkRate)
    {
        const float Rate = Speed > RunTripSpeed ? RunRate : Speed > WalkTripSpeed ? WalkRate : 0.f;
        return FMath::Max(0.f, Rate) * Clumsiness(InConfidence);
    }
    /** Chance that a real jump ends in a botched landing (Base is the new-game chance). */
    static float BotchChance(float InConfidence, float Base) { return FMath::Clamp(Base, 0.f, 1.f) * Clumsiness(InConfidence); }
    /** Share of botched landings that put him flat on his face instead of a stagger. */
    static float FaceplantShare(float InConfidence) { return .4f * Clumsiness(InConfidence); }
    /** Seconds of standing about before the next fidget; U is a 0..1 draw. The lad fidgets
     * every few seconds, the hero stands planted for most of a minute. */
    static float FidgetGap(float InConfidence, float U)
    {
        const float C = FMath::IsFinite(InConfidence) ? FMath::Clamp(InConfidence, 0.f, 1.f) : 0.f;
        return FMath::Lerp(FMath::Lerp(5.f, 11.f, U), FMath::Lerp(18.f, 36.f, U), C);
    }

    enum class EBotch : uint8 { None, Stagger, Faceplant };

    /** A landing. True when it was a clumsy one (IsStumbling follows; ConsumeBotch says which
     * kind). Never in or just after a fight: see NotifyCombat. */
    bool Land(float ImpactSpeed, float AirSeconds, float Chance)
    {
        LandImpact = FMath::Clamp((ImpactSpeed - 150.f) / 450.f, 0.f, 1.f);
        bLanded = AirSeconds >= .12f;
        const int32 Forced = ForcedLanding;
        ForcedLanding = -1;
        if (Forced == int32(EBotch::None)) return false;
        if (Forced < 0)
        {
            if (ImpactSpeed < 220.f || AirSeconds < .18f || Cooldown > 0.f || CombatQuiet > 0.f) return false;
            if (Random.FRand() >= FMath::Clamp(Chance, 0.f, 1.f)) return false;
        }
        Botch = Forced >= 0 ? EBotch(Forced) : Random.FRand() < FaceplantShare(Confidence) ? EBotch::Faceplant : EBotch::Stagger;
        Recovery = Botch == EBotch::Faceplant ? FaceplantDuration : StumbleDuration;
        Cooldown = Recovery + 1.f;
        bStumbleStarted = true;
        return true;
    }

    /** A toe catches while walking or running and he recovers in two quick steps. Never in or
     * just after a fight. */
    bool Trip()
    {
        if (Cooldown > 0.f || Recovery > 0.f || CombatQuiet > 0.f) return false;
        Recovery = StumbleDuration;
        Cooldown = TripCooldown;
        Botch = EBotch::None;
        bStumbleStarted = true;
        return true;
    }

    /** Review tool: the next qualifying landing is this kind whatever the dice say (None = a clean one). */
    void ForceNextLanding(EBotch Kind) { ForcedLanding = int32(Kind); }

    /** He attacked or was hurt: for the next few seconds nothing clumsy starts, so a pratfall
     * can never hide a fight from the player. (Nothing here ever moved the capsule or locked
     * input; this keeps the picture readable too.) */
    void NotifyCombat() { CombatQuiet = CombatQuietSeconds; IdleSeconds = 0.f; }
    bool IsCombatQuiet() const { return CombatQuiet > 0.f; }

    /** The end of a swing: an unsure Dink has put too much of himself into it and rocks on his
     * feet for a second (degrees per second of trunk sway; nothing for the hero). Side is +1 or
     * -1: the way the swing carried him. */
    void KickWobble(float Side)
    {
        const float Timid = 1.f - Confidence;
        WobbleVelocity += FVector2f(70.f, 55.f * (Side < 0.f ? -1.f : 1.f)) * Timid;
    }

    void Update(float DeltaTime, float Speed, bool Grounded, bool Allowed, float TurnRate = 0.f,
        float TripsPerRunSecond = 0.f, float TripsPerWalkSecond = 0.f)
    {
        if (!Allowed) { Cancel(); return; }
        if (DeltaTime <= SMALL_NUMBER || !FMath::IsFinite(DeltaTime)) return;
        Speed = FMath::IsFinite(Speed) ? FMath::Max(0.f, Speed) : 0.f;
        TurnRate = FMath::IsFinite(TurnRate) ? TurnRate : 0.f;
        Confidence = FMath::FInterpConstantTo(Confidence, TargetConfidence, DeltaTime, .35f);
        const float Timid = 1.f - Confidence;
        Cooldown = FMath::Max(0.f, Cooldown - DeltaTime);
        CombatQuiet = FMath::Max(0.f, CombatQuiet - DeltaTime);
        // Leaving the ground ends a catch-step: the airborne pose takes over.
        Recovery = Grounded ? FMath::Max(0.f, Recovery - DeltaTime) : 0.f;
        const float SpeedChange = bReady ? (Speed - PreviousSpeed) / DeltaTime : 0.f;
        PreviousSpeed = Speed; bReady = true;
        if (const float Rate = TripsPerSecond(Speed, Confidence, TripsPerRunSecond, TripsPerWalkSecond);
            Grounded && Rate > 0.f && Timid > .05f && Random.FRand() < Rate * DeltaTime) Trip();
        // Standing about: the next fidget comes due sooner the less sure of himself he is.
        if (Grounded && Speed < 5.f && Recovery <= 0.f && CombatQuiet <= 0.f)
        {
            IdleSeconds += DeltaTime;
            if (IdleSeconds >= NextFidget)
            {
                IdleSeconds = 0.f;
                FidgetRoll = FVector2f(Random.FRand(), Random.FRand());
                NextFidget = FidgetGap(Confidence, Random.FRand());
                bFidget = true;
            }
        }
        else IdleSeconds = 0.f;
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
            // The after-swing wobble: a loose, underdamped rock that dies away in about a second.
            WobbleVelocity += (Wobble * -WobbleStiffness - WobbleVelocity * WobbleDamping) * Step;
            Wobble += WobbleVelocity * Step;
            Remaining -= Step;
        }
    }
    bool IsStumbling() const { return Recovery > 0.f; }
    /** True once after a stumble began (the caller plays the catch-step). */
    bool ConsumeStumbleStart() { const bool B = bStumbleStarted; bStumbleStarted = false; return B; }
    /** True once after a landing; OutImpact is 0 (a hop) to 1 (a hard drop). */
    bool ConsumeLanding(float& OutImpact) { const bool B = bLanded; bLanded = false; OutImpact = LandImpact; return B; }
    /** Which botched landing began (once, with ConsumeStumbleStart); None for a toe catch. */
    EBotch GetBotch() const { return Botch; }
    /** True once when a fidget comes due; OutRoll holds two 0..1 draws for choosing it. */
    bool ConsumeFidget(FVector2f& OutRoll) { const bool B = bFidget; bFidget = false; OutRoll = FidgetRoll; return B; }
    /** Trunk lean in degrees: X forward, Y to the character's left (the after-swing wobble included). */
    FVector2f GetLean() const { return Lean + Wobble; }
    FVector2f GetWobble() const { return Wobble; }
    /** Drops every transient motion. Confidence is earned, so it survives teleports/cutscenes. */
    void Cancel()
    {
        Recovery = Cooldown = PreviousSpeed = LandImpact = IdleSeconds = CombatQuiet = 0.f;
        Lean = LeanVelocity = Wobble = WobbleVelocity = FVector2f::ZeroVector;
        bReady = bStumbleStarted = bLanded = bFidget = false;
        Botch = EBotch::None;
    }
    static constexpr float StumbleDuration = .85f, FaceplantDuration = 3.f, TripCooldown = 14.f;
    static constexpr float RunTripSpeed = 490.f, WalkTripSpeed = 110.f, CombatQuietSeconds = 6.f;
    static constexpr float WobbleStiffness = 230.f, WobbleDamping = 6.5f;
    static constexpr float MaxStartLean = 4.f, MaxStopLean = 3.f, MaxTurnLean = 5.f;
private:
    FRandomStream Random{1997};
    FVector2f Lean = FVector2f::ZeroVector, LeanVelocity = FVector2f::ZeroVector;
    FVector2f Wobble = FVector2f::ZeroVector, WobbleVelocity = FVector2f::ZeroVector, FidgetRoll = FVector2f::ZeroVector;
    float Recovery = 0.f, Cooldown = 0.f, PreviousSpeed = 0.f, LandImpact = 0.f;
    float Confidence = 0.f, TargetConfidence = 0.f;
    float CombatQuiet = 0.f, IdleSeconds = 0.f, NextFidget = 4.f;
    EBotch Botch = EBotch::None;
    int32 ForcedLanding = -1;
    bool bReady = false, bStumbleStarted = false, bLanded = false, bFidget = false;
};
