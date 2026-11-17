#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkCreatureClass.h"
#include "DinkCreatureSubsystem.generated.h"
class ADinkPlaceholderActor;
class UDinkCreatureClassComponent;
class UMaterialInterface;
class UStaticMesh;
class UStaticMeshComponent;
struct FDinkCreatureLoadedClass;
/**
 * Optional creature overlay on original placements. No actor, origin, script or brain replacement.
 *
 * Two layers read from Content/Dink/Data/Art/creatures.json:
 * - `placements` (origin rows): the first creatures, with their own body boxes and the authored-interaction rules;
 * - `classes` (class rows, DinkCreatureClass.h): every other placement of a bound sprite class and every script-made
 *   sprite of its sequences, presentation only. `dink.CreatureClassArt` 0 turns the layer off, 1 (default) shows it
 *   while the process renders, 2 also in headless runs (the tests).
 */
UCLASS()
class DINKCORE_API UDinkCreatureSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
  public:
	virtual void OnWorldBeginPlay(UWorld& World) override;
	virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
	/** Called only for real script-created sprite actors, including restored ones. */
	void NotifyScriptSprite(AActor* Actor, int32 Sequence);
	const TArray<TWeakObjectPtr<AActor>>& GetFoodActors() const
	{
		return FoodActors;
	}

	// --- class rows ---------------------------------------------------------------------------------------------
	/** dink.CreatureClassArt allows the layer in this process (1 needs a renderer, 2 does not). */
	static bool IsClassArtAllowed();
	/** Rows of `classes` whose assets loaded and fit their mesh's skeleton. */
	const TArray<FDinkCreatureClassBinding>& GetClassBindings() const { return ClassBindings; }
	/** Placements a class row presents (begin play). */
	int32 GetClassPlacementCount() const { return ClassPlacements; }
	/** The class body on an actor, nullptr if none. */
	static UDinkCreatureClassComponent* FindClassBody(const AActor* Actor);
	/**
	 * Gives a script-made sprite actor the body of the class its picture or walk base belongs to, and hides its greybox
	 * marker. nullptr when no row takes the sprite or the actor is already dressed. GroundOffsetCm as Configure's.
	 */
	UDinkCreatureClassComponent* PresentScriptSprite(AActor* Actor, const DinkCreatureClass::FSpriteView& Sprite, float GroundOffsetCm, float YawDeg, int32 SizePercent);
	/**
	 * add_kill_sprite's picture (dink.cpp:12359): the class's corpse where a sprite was killed, until ClearCorpses. False
	 * when the row has no corpse for the sprite's death sequence (base_death + facing).
	 */
	bool LeaveCorpse(FName ClassId, int32 BaseDeath, int32 Dir, const FVector& Ground, float YawDeg, int32 SizePercent, int32 BaseWalk = 0);
	/** The original drops its corpse sprites with the screen. */
	void ClearCorpses();
	/** Counts ClearCorpses calls: a death clip begun before the last one belongs to a screen that is gone. */
	int32 GetClearCount() const { return ClearCount; }
	int32 GetCorpseCount() const { return Corpses.Num(); }
	/** The corpse LeaveCorpse made last (its death clip hands over to it, DinkCreatureOneShots.h). */
	UStaticMeshComponent* GetNewestCorpse() const { return Corpses.Num() ? Corpses.Last().Get() : nullptr; }
	/** Blood decals lying under the corpses. */
	int32 GetCorpseDecalCount() const { return CorpseDecals.Num(); }

	/**
	 * Gore of the class layer (DinkCreatureGore.cpp): drops of blood in flight, stains on the ground and thrown parts.
	 * Presentation only: no collision, no simulation state, its own random numbers. Everything goes with ClearCorpses.
	 */
	void EmitBlood(UStaticMesh* DropMesh, const FVector& From, const FVector& Direction, float SpeedCmS, float SpreadDeg, int32 Count, float SizeCm, float GroundZ,
		const FVector& Carry = FVector::ZeroVector, int32 MaxInAir = MaxBloodDrops);
	void AddBloodDecal(UMaterialInterface* Material, const FVector& Ground, float YawDeg, float SizeCm);
	/** A part that flies, spins and lands: Flying is shown in the air, Landed (with its decal) where it comes down. */
	void ThrowPart(UStaticMesh* Flying, UStaticMesh* Landed, UMaterialInterface* LandedDecal, float DecalSizeCm, const FVector& From, const FVector& Velocity, float GroundZ, double Scale);
	/** The class's burst for a sprite removed while it showed Sequence with Brain (the dead duck's sequence 164). False when the row has none. */
	bool Burst(FName ClassId, int32 Sequence, int32 Brain, const FVector& Ground, int32 SizePercent);
	/** Moves the drops and the flying parts; the presenter calls it once a frame. */
	void StepGore(float DeltaTime);
	int32 GetBloodDropCount() const { return BloodDrops.Num(); }
	int32 GetLandedFeatherCount() const;
	int32 GetFlyingPartCount() const { return FlyingParts.Num(); }
	int32 GetBloodDecalCount() const { return BloodDecals.Num(); }
	/** Decal components made since the world began: at MaxBloodDecals the oldest stain is moved instead of a new one made. */
	int32 GetBloodDecalsMade() const { return BloodDecalsMade; }
	/** Bursts shown since the world began (review aid and tests). */
	int32 GetBurstCount() const { return BurstCount; }
	static constexpr int32 MaxBloodDrops = 3000;
	/** The fountains of all bodies together stop here, so a burst always finds room. */
	static constexpr int32 MaxFountainDrops = 500;
	static constexpr int32 MaxBloodDecals = 96;
	/** Ground decals are projected from this far below the ground point: with a 45 cm half depth they reach 20 cm above it. */
	static constexpr double DecalSinkCm = 25.0;

  private:
	TArray<TWeakObjectPtr<AActor>> FoodActors;
	TSet<int32> FoodSequences;
	UPROPERTY(Transient) TObjectPtr<class UStaticMesh> FoodMesh;
	FVector FoodMeshOffset = FVector(0, 0, -60);

	void AttachOriginRows(UWorld& World, const class FJsonObject& Manifest);
	void BindClasses(UWorld& World, const class FJsonObject& Manifest);
	TSharedPtr<const FDinkCreatureLoadedClass> LoadClass(const FDinkCreatureClassBinding& Binding);
	UDinkCreatureClassComponent* AttachClassBody(AActor& Actor, const TSharedRef<const FDinkCreatureLoadedClass>& Class, float GroundOffsetCm, float YawDeg, int32 SizePercent);
	TArray<FDinkCreatureClassBinding> ClassBindings;
	TArray<TSharedPtr<const FDinkCreatureLoadedClass>> LoadedClasses;
	/** Every asset a class row uses: the loaded rows hold raw pointers. */
	UPROPERTY(Transient) TArray<TObjectPtr<UObject>> ClassAssets;
	UPROPERTY(Transient) TObjectPtr<AActor> CorpseHolder;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Corpses;
	int32 ClearCount = 0;
	UPROPERTY(Transient) TArray<TObjectPtr<class UDecalComponent>> CorpseDecals;
	int32 ClassPlacements = 0;

	/** 0 a drop in flight, 1 a gobbet of the burst's core, 2 a feather. */
	struct FBloodDrop
	{
		FVector Location = FVector::ZeroVector, Velocity = FVector::ZeroVector;
		FRotator Rotation = FRotator::ZeroRotator, Spin = FRotator::ZeroRotator;
		float SizeCm = 1.f, GroundZ = 0.f;
		/** Seconds lived and allowed (0 = until it reaches the ground). */
		float Age = 0.f, Life = 0.f;
		float Gravity = 1.f, Drag = 0.6f;
		uint8 Kind = 0;
	};
	class UInstancedStaticMeshComponent* GoreInstances(TObjectPtr<class UInstancedStaticMeshComponent>& Slot, UStaticMesh* Mesh, bool bShadow);
	/** Shows exactly these instances: the ones there are moved in place, only the difference is added or removed. */
	static void SetGoreInstances(class UInstancedStaticMeshComponent& Instances, const TArray<FTransform>& Transforms);
	int32 BloodDecalsMade = 0, BurstCount = 0;
	struct FFlyingPart
	{
		FVector Velocity = FVector::ZeroVector;
		FRotator Spin = FRotator::ZeroRotator;
		float GroundZ = 0.f, DecalSizeCm = 0.f;
		double Scale = 1.0;
		/** Kept alive by ClassAssets. */
		UStaticMesh* Landed = nullptr;
		UMaterialInterface* LandedDecal = nullptr;
	};
	class USceneComponent* GoreRoot();
	class UStaticMeshComponent* AddGoreMesh(UStaticMesh* Mesh, const FTransform& Transform);
	void ClearGore();
	TArray<FBloodDrop> BloodDrops;
	TArray<FFlyingPart> FlyingParts;
	/** Parallel to FlyingParts. */
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> FlyingMeshes;
	UPROPERTY(Transient) TObjectPtr<class UInstancedStaticMeshComponent> DropInstances;
	UPROPERTY(Transient) TObjectPtr<class UInstancedStaticMeshComponent> BlobInstances;
	UPROPERTY(Transient) TObjectPtr<class UInstancedStaticMeshComponent> FeatherInstances;
	/** Feathers that have come down: they lie there until ClearCorpses. */
	UPROPERTY(Transient) TObjectPtr<class UInstancedStaticMeshComponent> LandedFeathers;
	UPROPERTY(Transient) TArray<TObjectPtr<class UDecalComponent>> BloodDecals;
};
