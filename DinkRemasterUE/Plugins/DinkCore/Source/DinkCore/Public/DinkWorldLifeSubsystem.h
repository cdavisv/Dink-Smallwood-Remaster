#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkWorldLifeSubsystem.generated.h"

class AActor;
class UInstancedStaticMeshComponent;
class UMaterialParameterCollection;
class UPointLightComponent;
class UWindDirectionalSourceComponent;

/** Wind of one region (Content/Dink/Data/Environment/world_life.json `wind.regions`). */
struct FDinkWindProfile
{
	/** 0 still .. 1 the photoreal pass's tuned breeze .. 2 a gale. */
	float Strength = 1.f;
	/** 0 steady .. 1 the full travelling gust field. */
	float Gustiness = 1.f;
	/** Direction the wind blows TO, degrees in the Unreal XY plane (0 = +X east, 90 = +Y south). */
	float DirectionDeg = 37.f;
};

/** Kinds of the cheap CPU particles (instanced planes; Scripts/import_world_life.py builds their two materials). */
enum class EDinkLifeParticle : uint8
{
	Dust,     // lit soft puff that grows and fades (footsteps, pushes, landings), tinted by the ground
	Smoke,    // lit puff that rises and spreads (fire, chimneys, after an explosion)
	Debris,   // small lit chip that falls under gravity and settles (barrel staves, splinters, grit)
	Ripple,   // lit ring lying flat on a surface, grows and fades (fish rings, drips)
	Ember,    // additive glowing dot that rises and flickers out (fire)
	Spark,    // additive streak along its velocity (sword on stone, missile impacts)
	Glow,     // additive soft ball (fireball body, explosion flash, fireflies)
	Mote,     // additive tiny dot drifting on the wind (pollen in meadows, gnats by water)
	Count
};

/** One particle to emit (world cm, cm/s, seconds). */
struct FDinkLifeParticleSpec
{
	EDinkLifeParticle Kind = EDinkLifeParticle::Dust;
	FVector Location = FVector::ZeroVector;
	FVector Velocity = FVector::ZeroVector;
	float Life = 1.f;
	float SizeStart = 20.f;
	float SizeEnd = 60.f;
	FLinearColor Colour = FLinearColor::White;   // rgb; a = peak opacity (additive kinds: brightness)
	float Drag = 2.f;                             // 1/s velocity damping
	float Gravity = 0.f;                          // cm/s^2 downwards (negative rises)
	float WindFollow = 0.f;                       // 0..1: how much the particle drifts with the shared wind
	float FloorZ = -1e9f;                         // debris stops here (ground under it)
};

namespace DinkWorldLife
{
	/** Wind strength on Low foliage scalability, indoors and with dink.World.Wind 0 (pure, tested). */
	DINKCORE_API float EffectiveStrength(float ProfileStrength, float CVarWind, bool bIndoor, int32 FoliageQuality);
	/** Slow global gust multiplier 0.3..1.8 for a time and gustiness (smooth, deterministic, never NaN; tested). */
	DINKCORE_API float GlobalGust(double TimeSeconds, float Gustiness);
	/** Unit wind direction (XY) of a direction in degrees. */
	DINKCORE_API FVector2D DirectionOf(float DirectionDeg);
	/** Eases a profile towards a target (direction by the shortest turn). */
	DINKCORE_API FDinkWindProfile EaseProfile(const FDinkWindProfile& From, const FDinkWindProfile& To, float Alpha);
	/** Picks up to MaxSlots pushers nearest to Focus within Radius (by squared distance), nearest first. */
	DINKCORE_API void PickPushers(const FVector2D& Focus, const TArray<FVector4f>& Candidates, float Radius, int32 MaxSlots, TArray<FVector4f>& Out);
	/** Ground dust from a ground colour: 0 on green meadow and moss .. 1 on bare earth, sand, snow and stone. */
	DINKCORE_API float DustinessOfGround(const FLinearColor& Ground);
	/** True when the family art layer draws an effect on this actor (a placed sprite of an "effect_placed" row: its card
	 *  carries UDinkArtFamilySubsystem::FamilyTag; or a script sprite drawn by an effect row: ScriptEffectTag). The family
	 *  row owns that sprite's fire, smoke and light, so the world-life layer adds none of its own there (PR #166). */
	DINKCORE_API bool IsFamilyEffect(const AActor* Actor);
}

/**
 * World life (stream world-alive, 15 Nov 2026): the shared wind and the small things that make the world move,
 * presentation only. Nothing here has collision, touches the simulation (hardness, sprite positions, hit and touch
 * boxes, script state), draws from the simulation's random stream or blocks the player; nothing is created when the
 * process cannot render (headless tests, the probe).
 *
 *  - Shared wind: one AWindDirectionalSource (cloth and anything that reads the scene wind) and the material parameter
 *    collection /Game/Dink/WorldLife/MPC_Dink_World, written every frame:
 *      WindDir  (x, y unit direction the wind blows to; z strength 0..2; w gustiness 0..1)
 *      WindGust (x slow global gust 0.3..1.8; y gust-field travel speed)
 *      Push0..3 (x, y world cm; z radius cm; w strength 0..1): Dink and the nearest moving creatures; grass, crops and
 *               bush tips bend away from them (Scripts/world_life_wind.py, M_Veg_Foliage / M_Veg_Bark)
 *      WorldLife (1 with the layer on)
 *    MPC_Dink_Environment.Wind (dink.Wind, UDinkEnvironmentSubsystem) stays the global multiplier on top.
 *    The profile comes per region from world_life.json, eased over a few seconds across screens; indoors it is 0.
 *    Hair and cloth read GetWindVelocityAt / GetWindDirection / GetWindStrength (C++), or the same MPC (materials).
 *  - Particles: a pool of instanced planes (puffs, chips, rings, glows, streaks) and a few flickering point lights,
 *    for UDinkWorldLifePresenter (DinkNarrative: fire, missiles, breaks, pushes) and the ambient layer here
 *    (footstep dust on bare ground, chimney smoke, pollen and gnats).
 *
 * Foliage shadows: every visible mesh near the player whose base material is M_Veg_Foliage or M_Veg_Bark and whose shadow
 * cache invalidation is still Auto gets Rigid (WPO sway no longer re-renders its virtual shadow pages every frame; the
 * shadow keeps the rest pose); dink.World.StaticFoliageShadows 0 or dink.World.Life 0 puts them back.
 *
 * Console: dink.World.Life 0 (everything here off: wind back to the material defaults, no particles), dink.World.Wind
 * <0..2> (multiplier of the regional wind; 0 = still), dink.World.Particles <0..2> (budget), dink.World.Stats 1 (log).
 */
UCLASS()
class DINKCORE_API UDinkWorldLifeSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	/** True while the layer runs (a rendering game world with dink.World.Life 1). */
	bool IsActive() const { return bActive && bEnabled; }
	/** True while particles can actually be drawn (layer on, a budget above 0, both particle materials loaded). Callers
	 *  that hide something because a particle replaces it (the presenter's fireball markers) check this every frame. */
	bool CanDrawParticles() const { return IsActive() && Budget > 0.f && LitPool && GlowPool; }

	// ---- shared wind (hair, cloth, anything) -------------------------------------------------------------
	/** Unit XY direction the wind blows to. */
	FVector2D GetWindDirection() const { return WindDir; }
	/** Effective strength 0..2 (region, indoors, dink.World.Wind, scalability). */
	float GetWindStrength() const { return WindStrength; }
	/** Gust multiplier now (0.3..1.8; 1 on average). */
	float GetWindGust() const { return WindGustNow; }
	/** Wind velocity at a point, cm/s (about 350 cm/s at strength 1 on an average gust); zero indoors. */
	FVector GetWindVelocityAt(const FVector& At) const;
	static const TCHAR* WorldCollectionPath() { return TEXT("/Game/Dink/WorldLife/MPC_Dink_World.MPC_Dink_World"); }

	// ---- particles ---------------------------------------------------------------------------------------
	/** Emits one particle (dropped silently over budget, far from the camera or with the layer off). */
	void Emit(const FDinkLifeParticleSpec& Spec);
	/** A brief flickering light (explosions, sparks): intensity in candela-ish units of UPointLightComponent. */
	void Flash(const FVector& At, const FLinearColor& Colour, float Intensity, float RadiusCm, float Seconds);
	/** A light kept alive while Keep is called every frame with the same key (fires, fireballs); flickers. */
	void KeepLight(uint64 Key, const FVector& At, const FLinearColor& Colour, float Intensity, float RadiusCm, float Flicker);
	/**
	 * One frame of a fire at Base (ground of the flame) whose flames reach HeightCm: smoke from the top, embers, a soft
	 * heat glow and a flickering light (outdoors; indoor screens already light their hearths). Scale 1 = a hearth or
	 * torch fire, 3 = a burning tree or house. Key keeps the light and the emission timers of one fire across frames.
	 */
	void EmitFire(uint64 Key, const FVector& Base, float HeightCm, float Scale, bool bIndoor, float DeltaTime);
	/** Fire sources of placements on the screens in view (class or 1997 sequence of world_life.json `fire`), re-scanned on screen change. */
	int32 GetPlacedFireCount() const { return PlacedFires.Num(); }
	/** Sequences world_life.json `fire.sequences` lists as fire, with their flame height in cm and scale. */
	bool FireOfSequence(int32 Seq, float& OutHeightCm, float& OutScale) const;
	/** Ground Z under a point (first blocking hit of a downward trace), else Fallback. */
	float GroundZ(const FVector& At, float Fallback) const;
	/** Camera location of the first player (zero if none). */
	FVector GetCamera() const { return Camera; }
	/** Particle budget multiplier now (dink.World.Particles x sg.EffectsQuality). 0 = none. */
	float GetBudget() const { return Budget; }
	int32 GetLiveParticles() const { return Particles.Num(); }
	int32 GetLiveLights() const;
	/** Particles emitted since the world began (review/tests). */
	int64 GetEmittedTotal() const { return EmittedTotal; }
	int64 GetNonFiniteCount() const { return NonFinite; }

private:
	struct FParticle
	{
		FDinkLifeParticleSpec S;
		FVector P = FVector::ZeroVector;
		FVector V = FVector::ZeroVector;
		float Age = 0.f;
		float Seed = 0.f;
		bool bSettled = false;
	};
	struct FLight
	{
		TObjectPtr<UPointLightComponent> Comp;
		uint64 Key = 0;          // 0 = flash
		float Base = 0.f;
		float Flicker = 0.f;
		float Until = 0.f;       // flashes: world time it ends; kept lights: the last frame it was kept + a grace
		float Start = 0.f;
		float Seed = 0.f;
	};

	void LoadConfig();
	void UpdateWind(float DeltaTime, const class ADinkScreenVolume* Current);
	void UpdatePushers(float DeltaTime);
	void UpdateAmbient(float DeltaTime, const class ADinkScreenVolume* Current);
	void UpdateParticles(float DeltaTime);
	void PushPool(UInstancedStaticMeshComponent* Pool, const TArray<FTransform>& T, const TArray<float>& D, bool& bParked);
	void UpdateLights(float DeltaTime);
	void GatherChimneys();
	void GatherPlacedFires();
	struct FPlacedFire { uint64 Key = 0; FVector Base = FVector::ZeroVector; float Height = 100.f; float Scale = 1.f; TWeakObjectPtr<AActor> Actor; };
	TArray<FPlacedFire> PlacedFires;
	TMap<int32, FVector2f> FireSeqs;          // sequence -> (height cm, scale)
	TMap<FName, FVector2f> FireClasses;       // class id -> (height cm, scale)
	TMap<uint64, FVector4f> FireTimers;       // key -> smoke, ember, glow accumulators, last frame seen
	void ClearAll();
	UPointLightComponent* AcquireLight();
	UInstancedStaticMeshComponent* PoolFor(EDinkLifeParticle Kind) const;

	bool bActive = false;     // world can render and the config loaded
	bool bEnabled = true;     // dink.World.Life
	UPROPERTY(Transient)
	TObjectPtr<AActor> Holder;
	UPROPERTY(Transient)
	TObjectPtr<AActor> WindActor;
	UPROPERTY(Transient)
	TObjectPtr<UWindDirectionalSourceComponent> WindSource;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialParameterCollection> WorldCollection;
	UPROPERTY(Transient)
	TObjectPtr<UInstancedStaticMeshComponent> LitPool;      // Dust, Smoke, Debris, Ripple
	UPROPERTY(Transient)
	TObjectPtr<UInstancedStaticMeshComponent> GlowPool;     // Ember, Spark, Glow, Mote
	TArray<FLight> Lights;   // components are owned by Holder (instance components)

	TArray<FParticle> Particles;
	// per-frame scratch kept between frames (no allocation per frame)
	TArray<FTransform> LitT, GlowT, AllT;
	TArray<float> LitD, GlowD, AllD;
	TArray<int32> Order;
	bool bLitParked = true, bGlowParked = true;
	FVector2D GustTravel = FVector2D::ZeroVector;
	TMap<TObjectPtr<const UStaticMesh>, bool> ChimneyMesh;
	// foliage shadow policy: wind-swayed vegetation keeps cached (rest-pose) virtual shadow pages (Rigid), as perf-stutter's
	// dink.Perf.StaticForestShadows does for the forest ISMs; restored when the layer goes off
	TMap<TObjectPtr<const class UMaterialInterface>, bool> FoliageMaterial;
	TArray<TWeakObjectPtr<class UPrimitiveComponent>> RigidShadows;
	void ApplyFoliageShadowPolicy(class UStaticMeshComponent* M);
	void RestoreFoliageShadows();
	int64 EmittedTotal = 0;
	int64 NonFinite = 0;      // emissions refused or particles dropped for a NaN/inf position or velocity (soak evidence: stays 0)
	uint32 Rand = 0x9E3779B9u;
	float Frand();

	// wind
	TMap<FName, FDinkWindProfile> RegionWind;
	FDinkWindProfile DefaultWind;
	FDinkWindProfile WindNow;
	bool bWindSeeded = false;
	FVector2D WindDir = FVector2D(0.8, 0.6);
	float WindStrength = 1.f;
	float WindGustNow = 1.f;
	float WindEaseSeconds = 4.f;

	// pushers
	float PushRadiusCm = 95.f;
	float PushCreatureRadiusCm = 70.f;
	float PushReachCm = 2500.f;
	TMap<TWeakObjectPtr<AActor>, FVector> LastPos;
	TMap<TWeakObjectPtr<AActor>, float> Motion;   // 0..1 eased "is moving"
	double NextPusherScan = 0.0;
	int32 PusherScreen = -1;
	TArray<TWeakObjectPtr<AActor>> PusherCandidates;

	// ambient
	FVector LastFoot = FVector::ZeroVector;
	float FootTravel = 0.f;
	float StrideCm = 62.f;
	TArray<FVector> Chimneys;
	int32 ChimneyScreen = -1;
	double NextChimneyScan = 0.0;
	float ChimneyTimer = 0.f;
	float MoteTimer = 0.f;

	FVector Camera = FVector::ZeroVector;
	float Budget = 1.f;
	float MaxParticles = 600.f;
	float CullCm = 6000.f;
	double NextStats = 0.0;
};
