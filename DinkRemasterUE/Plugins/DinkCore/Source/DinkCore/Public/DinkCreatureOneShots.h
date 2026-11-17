#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Tickable.h"
#include "DinkCreatureOneShots.generated.h"

class FJsonObject;
class UAnimSequence;
class UDinkCreatureAnimInstance;
class UDinkCreatureClassComponent;
class USkeletalMeshComponent;
class UStaticMeshComponent;
struct FPoseContext;

/**
 * Event one-shots of class-bound creature bodies: a flinch when a hit costs life, a strike when the creature attacks
 * (the dragon's fire), short idle variations (the duck's peck and quack), and the death clip that ends in the corpse.
 * The 1997 game has no such sequences (a kill swaps the sprite for its corpse picture at once; the dragon spits fire
 * while it walks), so these are layered over what the sprite shows and never touch it. Presentation only: the sprite,
 * its hardness, its scripts, the corpse's time and place and the blood are the simulation's and stay exactly as they are.
 *
 * Data: `one_shots` inside a class row of Content/Dink/Data/Art/creatures.json:
 *   {"hit":    {"clip": path, "blend_in_s": .05, "blend_out_s": .2, "rate": 1, "mask": "spine_01"},
 *    "attack": {"clip": path, ..., "trigger": "missile" | "touch", "radius_cm": 400},
 *    "death":  {"clip": path, "blend_in_s": .08, "rate": 1},
 *    "burst_death": {"clip": path},
 *    "idle":   {"clips": [path, ...], "every_s": [5, 12]}}
 * `mask` names the bone from which down the clip shows (the dragon's neck over its walk); without it the whole body.
 */
struct FDinkCreatureOverlay
{
	const UAnimSequence* Sequence = nullptr;
	float Time = 0.f, Weight = 0.f;
	FName MaskRoot;
};

/** A frozen copy of a body's layer (clip, time, weight). */
struct FDinkCreatureLayerCopy
{
	const UAnimSequence* Sequence = nullptr;
	float Time = 0.f, Weight = 0.f;
};

enum class EDinkCreatureOneShot : uint8 { Hit, Attack, Idle };

struct DINKCORE_API FDinkCreatureOneShotSpec
{
	FString Clip;
	float BlendInS = .06f, BlendOutS = .2f, Rate = 1.f;
	FName MaskRoot;
	/**
	 * Death only. AlignCm: where the clip's last pose lies against the corpse mesh, in the corpse's own frame at scale 1
	 * (the art export's "death-last-frame minus corpse"): the corpse mesh is moved by it when the clip ends, so a corpse
	 * made from the last frame takes over without a jump (it stays inside its blood pool, which does not move).
	 * MaterialFromCorpse: the dying body wears the corpse's materials from the kill on (the blood of the 1997 remains
	 * is there at the kill frame; a corpse frozen from the same mesh shares its texture layout).
	 */
	FVector AlignCm = FVector::ZeroVector;
	bool bMaterialFromCorpse = false;
	bool IsSet() const { return !Clip.IsEmpty(); }
};

struct DINKCORE_API FDinkCreatureOneShotRow
{
	FDinkCreatureOneShotSpec Hit, Attack, Death;
	/** A kill the engine shows as the blood burst of sequence 164 (the headless duck's second hit): this clip plays first,
	 * the burst comes where it ends (UDinkCreatureDeathSubsystem::BeginBurstDeath). */
	FDinkCreatureOneShotSpec BurstDeath;
	TArray<FDinkCreatureOneShotSpec> Idle;
	float IdleEveryMinS = 5.f, IdleEveryMaxS = 12.f;
	/** "missile": a missile sprite (brain 11 or 17) appears within AttackRadiusCm; "touch": Dink loses life within it. */
	FName AttackTrigger;
	float AttackRadiusCm = 350.f;
};

namespace DinkCreatureOneShots
{
	/** The class's row, nullptr when creatures.json gives it none. Game thread. */
	DINKCORE_API const FDinkCreatureOneShotRow* Find(FName ClassId);
	/** Reads creatures.json again (tests, review). */
	DINKCORE_API void Reload();
	DINKCORE_API bool ParseRow(const FJsonObject& Row, FDinkCreatureOneShotRow& Out);
	/** The spec's clip, loaded once and kept alive; nullptr when missing. */
	DINKCORE_API UAnimSequence* Load(const FDinkCreatureOneShotSpec& Spec);
	/** Blends each overlay over the pose (worker thread), on the bones from its mask root down. */
	DINKCORE_API void ApplyOverlays(FPoseContext& Output, TConstArrayView<FDinkCreatureOverlay> Overlays);
	/** Envelope of a one-shot at Time into a clip of Length: eased in and out. */
	DINKCORE_API float Envelope(float Time, float Length, float BlendIn, float BlendOut);
}

/** The one-shots of one body: stepped by its component every presentation step. */
struct DINKCORE_API FDinkCreatureOneShotPlayer
{
	/** Starts the class's clip of that kind (a hit restarts a running hit). False when the class has none. */
	bool Play(FName ClassId, EDinkCreatureOneShot Kind);
	/** Advances time, starts an idle variation now and then while the body stands, and writes this step's overlays. */
	void Step(FName ClassId, float DeltaTime, bool bStanding, TArray<FDinkCreatureOverlay, TInlineAllocator<2>>& Out);
	bool IsPlaying() const { return Active.Num() > 0; }
	int32 GetPlayed() const { return Played; }
private:
	struct FShot
	{
		const UAnimSequence* Clip = nullptr;
		FDinkCreatureOneShotSpec Spec;
		EDinkCreatureOneShot Kind = EDinkCreatureOneShot::Hit;
		float Time = 0.f;
	};
	TArray<FShot, TInlineAllocator<2>> Active;
	float NextIdle = -1.f, StandTime = 0.f;
	int32 Played = 0;
	/** Its own numbers: nothing of the simulation's random stream is read or advanced. */
	FRandomStream Random{1997};
};

/**
 * Death clips of killed class bodies. The kill swaps the sprite for its corpse at once (add_kill_sprite, dink.cpp:12359):
 * the corpse, its blood pool and the blood of the hit appear at that moment as before. What changes is only how the body
 * goes: a copy of it stays where it stood and plays the class's death clip from its last pose, and the corpse mesh (built
 * as that clip's last frame) is shown when the clip ends; until then it is there but not drawn. A screen change or a load
 * clears corpses (UDinkCreatureSubsystem::ClearCorpses) and these with them. dink.Creature.DeathClips 0: off.
 */
UCLASS()
class DINKCORE_API UDinkCreatureDeathSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()
public:
	/** The body was killed and its corpse (may be null: then nothing plays and the body goes as before) was just left. */
	bool BeginDeath(const UDinkCreatureClassComponent& Body, UStaticMeshComponent* Corpse);
	/**
	 * The body was killed by a blood-burst kill (duck_brain's second hit, dink.cpp:12728-12740): a copy plays the class's
	 * burst_death clip where the body stood and AtEnd(ground) makes the 1997 burst when the clip ends, so the burst, its
	 * drops, stain and feathers are the same as before, only after the fall. False (and nothing started: make the burst
	 * at once) when the class has no such clip or one-shots are off. A screen change or load (ClearCorpses) drops it.
	 */
	bool BeginBurstDeath(const UDinkCreatureClassComponent& Body, TFunction<void(const FVector& Ground)> AtEnd);
	/** Review only (dink.Creature.ShowDeath): a copy of Body plays its death (or burst death) clip beside it; nothing follows. */
	bool ShowDeath(const UDinkCreatureClassComponent& Body, bool bBurst, const FVector& Offset);
	int32 GetPlayingCount() const { return Deaths.Num(); }
	int32 GetStarted() const { return Started; }
	/** Seconds into the death clip of the newest death, -1 when none plays. */
	float GetNewestTime() const { return Deaths.Num() ? Deaths.Last().Time : -1.f; }
	void StepDeaths(float DeltaTime);
	virtual void Tick(float DeltaTime) override { StepDeaths(DeltaTime); }
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkCreatureDeathSubsystem, STATGROUP_Tickables); }
	virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
	virtual void Deinitialize() override;
private:
	struct FDeath
	{
		TWeakObjectPtr<USkeletalMeshComponent> Body;
		TWeakObjectPtr<UStaticMeshComponent> Corpse;
		const UAnimSequence* Clip = nullptr;
		/** The body's layers when it was killed: faded out under the clip. */
		TArray<FDinkCreatureLayerCopy> From;
		float Time = 0.f, Rate = 1.f, BlendIn = .08f;
		FVector AlignCm = FVector::ZeroVector;
		/** Burst deaths and review copies have no corpse; a burst is made by AtEnd. */
		bool bNoCorpse = false;
		TFunction<void(const FVector&)> AtEnd;
		FVector Ground = FVector::ZeroVector;
		int32 Epoch = 0;
	};
	USkeletalMeshComponent* SpawnDying(const UDinkCreatureClassComponent& Body, const FDinkCreatureOneShotSpec& Spec, UStaticMeshComponent* BloodFrom);
	UPROPERTY(Transient) TObjectPtr<AActor> Holder;
	UPROPERTY(Transient) TArray<TObjectPtr<USkeletalMeshComponent>> Bodies;
	TArray<FDeath> Deaths;
	int32 Started = 0;
	void Finish(int32 Index, bool bComplete);
	int32 CurrentEpoch() const;
};
