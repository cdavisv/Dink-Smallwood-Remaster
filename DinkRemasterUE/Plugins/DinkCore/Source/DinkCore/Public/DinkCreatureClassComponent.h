#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "Components/SkeletalMeshComponent.h"
#include "DinkCreatureClass.h"
#include "DinkHumanoidComponent.h"
#include "DinkCreatureClassComponent.generated.h"

class UAnimSequence;
class UMaterialInterface;
class USkeletalMesh;
class UStaticMesh;

/** One clip at one time with one weight: what the worker thread blends. */
struct FDinkCreaturePoseLayer
{
	const UAnimSequence* Sequence = nullptr;
	float Time = 0.f;
	float Weight = 0.f;
};

struct DINKCORE_API FDinkCreatureAnimProxy : public FAnimInstanceProxy
{
	FDinkCreatureAnimProxy() = default;
	explicit FDinkCreatureAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;
	TArray<FDinkCreaturePoseLayer, TInlineAllocator<8>> Layers;
};

/** Stateless native animation of a class-bound creature: blends the layers its component computed this frame. No blueprint. */
UCLASS(Transient, NotBlueprintable)
class DINKCORE_API UDinkCreatureAnimInstance : public UAnimInstance
{
	GENERATED_BODY()
public:
	void SetLayers(TConstArrayView<FDinkCreaturePoseLayer> InLayers);
	const TArray<FDinkCreaturePoseLayer, TInlineAllocator<8>>& GetLayers() const { return Layers; }
protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FDinkCreatureAnimProxy(this); }
private:
	TArray<FDinkCreaturePoseLayer, TInlineAllocator<8>> Layers;
	friend struct FDinkCreatureAnimProxy;
};

/** A locomotion set with its clips loaded. */
struct DINKCORE_API FDinkCreatureLoadedLocomotion
{
	const UAnimSequence* Idle = nullptr;
	TArray<const UAnimSequence*, TInlineAllocator<4>> Gaits;
	TArray<float, TInlineAllocator<4>> Speeds, Strides, Cycles;
	bool IsValid() const { return Idle != nullptr && Gaits.Num() > 0; }
};

struct DINKCORE_API FDinkCreatureLoadedRole
{
	/** nullptr: the row's mesh. */
	USkeletalMesh* Mesh = nullptr;
	const UAnimSequence* Clip = nullptr;
	FDinkCreatureLoadedLocomotion Locomotion;
};

/** A class row with every asset it names loaded and checked against the mesh's skeleton. Owned by UDinkCreatureSubsystem, which keeps the assets alive. */
struct DINKCORE_API FDinkCreatureLoadedClass
{
	FDinkCreatureClassBinding Binding;
	USkeletalMesh* Mesh = nullptr;
	TArray<FDinkCreatureLoadedRole> Roles;
	TArray<UStaticMesh*> CorpseMeshes;
	/** One per corpse row, nullptr where the row has no decal. */
	TArray<UMaterialInterface*> CorpseDecals;
	TMap<FName, UMaterialInterface*> Materials;
	int32 DefaultRole = INDEX_NONE;
};

/** The sprite as the simulation holds it this frame. Written by the presenter (DinkNarrative), read here; nothing flows back. */
struct DINKCORE_API FDinkCreatureSpriteState
{
	/** Animating sequence (sp_seq), 0 when the picture stands still. */
	int32 Seq = 0;
	/** Picture sequence (sp_pseq). */
	int32 PSeq = 0;
	/** Animation frame of Seq (sp_frame), 0 before its first frame. */
	int32 Frame = 0;
	/** Numpad direction 1-9. */
	int32 Dir = 0;
	/** World yaw of that direction on the sprite's screen (the director's facing); false: unknown. */
	bool bHasFacing = false;
	float FacingYawDeg = 0.f;
	/** sp_size, percent. */
	int32 SizePercent = 100;
	/** Seconds the sprite's current sequence takes from first to last frame (its frame delays); 0 unknown. */
	float SequenceDurationS = 0.f;
};

/**
 * The animated mesh of a class-bound creature, attached to the sprite's own actor (a placement's placeholder or a
 * script-made sprite actor). It shows the sprite's position as continuous motion (the engine moves sprites in whole
 * pixels on 60 Hz frames; FDinkBodySmoother, the humanoid bodies' averaging), faces along that motion and otherwise
 * the sprite's direction, and plays the role its picture stands for. It uses an absolute transform, so nothing that
 * turns or scales the actor shows; it has no collision, generates no overlaps, and never writes to the actor or the
 * sprite. Hidden with its actor.
 *
 * It ticks in TG_PostUpdateWork: the scripts and brains move the actor from UDinkStorySubsystem, a tickable object that
 * runs after the actor tick groups, so a body placed in the default group would show last frame's scripted position.
 */
UCLASS(ClassGroup = Dink)
class DINKCORE_API UDinkCreatureClassComponent : public USkeletalMeshComponent
{
	GENERATED_BODY()
public:
	UDinkCreatureClassComponent();
	/** GroundOffsetCm: the ground under the actor's origin (script-made sprite actors float 60 cm up). InitialYawDeg: world yaw shown until the sprite turns. */
	bool Configure(TSharedRef<const FDinkCreatureLoadedClass> InClass, float GroundOffsetCm, float InitialYawDeg, int32 SizePercent);
	void ApplySpriteState(const FDinkCreatureSpriteState& State);
	/** One presentation step; TickComponent calls it. Public for tests that drive time themselves. */
	void Present(float DeltaTime);
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	FName GetClassId() const { return Class.IsValid() ? Class->Binding.ClassId : NAME_None; }
	const FDinkCreatureClassBinding* GetBinding() const { return Class.IsValid() ? &Class->Binding : nullptr; }
	/** Role shown now (the newest track). */
	FName GetRoleName() const;
	float GetShownSpeed() const { return Smoother.GetSpeed(); }
	float GetShownYaw() const { return Smoother.GetYaw(); }
	const FVector& GetShownLocation() const { return Shown; }
	float GetCyclesPerSecond() const { return CyclesPerSecond; }
	int32 GetSizePercent() const { return SizePercent; }
	const FDinkCreatureSpriteState& GetSpriteState() const { return Sprite; }
	bool HasSpriteState() const { return bHasSprite; }
	/** Layers handed to the animation this frame (clip, time, weight; weights sum to 1). */
	const TArray<FDinkCreaturePoseLayer, TInlineAllocator<8>>& GetLayers() const { return Layers; }
	/** Seconds into the newest track's clip, -1 for a locomotion track. */
	float GetClipTime() const;

private:
	struct FTrack
	{
		int32 Role = INDEX_NONE;
		float Time = 0.f, Rate = 1.f, Weight = 0.f;
		bool bFadingOut = false;
	};
	void StartRole(int32 Role, bool bRestart);
	void ShowMesh(USkeletalMesh* Mesh);
	void BuildLayers(float DeltaTime);

	TSharedPtr<const FDinkCreatureLoadedClass> Class;
	/** Keeps the clips and meshes of the row alive for as long as this component shows them. */
	UPROPERTY(Transient) TArray<TObjectPtr<UObject>> HeldAssets;
	FDinkCreatureSpriteState Sprite;
	TArray<FTrack, TInlineAllocator<4>> Tracks;
	TArray<FDinkCreaturePoseLayer, TInlineAllocator<8>> Layers;
	FDinkBodySmoother Smoother;
	FVector Shown = FVector::ZeroVector;
	float GroundOffset = 0.f, TargetYaw = 0.f, Phase = 0.f, IdleTime = 0.f, CyclesPerSecond = 0.f;
	int32 SizePercent = 100, FirstDir = 0, LastSeq = 0, LastFrame = 0;
	bool bHasSprite = false, bFollowDir = false, bPlaced = false;
};
