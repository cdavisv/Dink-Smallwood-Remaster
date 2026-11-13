#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "DinkBodyAnimInstance.generated.h"

class UAnimSequence;

/** One authored clip of the animation pass (Content/Dink/Data/Art/animation_pass.json). */
USTRUCT()
struct DINKCORE_API FDinkBodyClip
{
	GENERATED_BODY()
	UPROPERTY() TObjectPtr<UAnimSequence> Sequence;
	float Duration = 0.f;
	/** Travel speed the cycle was authored for and ground covered by one full cycle, cm. */
	float SpeedCm = 0.f, StrideCm = 0.f;
	/** Documentary only: the hit and input-lock times the clip was built around. */
	float HitS = 0.f, LockS = 0.f;
	/** Gait cycles (left + right step) the clip holds, and the time of its first left-foot lead. */
	float Cycles = 1.f, PhaseStart = 0.f;
	bool bLoop = false;
	/** Seconds into the clip for a gait phase counted in cycles. */
	float TimeAtPhase(float Phase) const
	{
		return FMath::Fmod(PhaseStart + FMath::Fmod(Phase, FMath::Max(Cycles, 1.f)) * Duration / FMath::Max(Cycles, 1.f), Duration);
	}
	/** Ground covered by one gait cycle, cm. */
	float CycleStride() const { return StrideCm / FMath::Max(Cycles, 1.f); }
	bool IsValid() const { return Sequence != nullptr && Duration > 0.f; }
};

/** A timid/confident pair of the same move; either may stand in for the other. */
USTRUCT()
struct DINKCORE_API FDinkBodyClipPair
{
	GENERATED_BODY()
	UPROPERTY() FDinkBodyClip Timid;
	UPROPERTY() FDinkBodyClip Confident;
	bool IsValid() const { return Timid.IsValid() && Confident.IsValid(); }
	float Stride(float C) const { return FMath::Lerp(Timid.CycleStride(), Confident.CycleStride(), C); }
	float Speed() const { return Confident.SpeedCm; }
	float Length() const { return FMath::Max(Timid.Duration, Confident.Duration); }
};

/** Pure locomotion blend maths, shared by the runtime and its tests. */
struct DINKCORE_API FDinkGaitBlend
{
	/** Weights of idle and of each gait (same order as the speeds) and the cycles per second
	 * that make the blended stride cover exactly Speed: the feet do not slide at any weight.
	 * Below the slowest gait both the step length and the cadence shrink, as a person's do
	 * when walking slowly. */
	static void Solve(float Speed, TConstArrayView<float> GaitSpeeds, TConstArrayView<float> GaitStrides,
		float& OutIdle, TArray<float, TInlineAllocator<4>>& OutWeights, float& OutCyclesPerSecond, float CadencePower = SlowCadencePower);
	/** Below the slowest gait: stride covered by a gait/standing mix of weight W is W^SlowStridePower
	 * of the gait's, and the cadence falls with speed^SlowCadencePower. */
	static constexpr float SlowStridePower = 2.2f, SlowCadencePower = .7f;
};

struct FDinkBodyLayer
{
	const UAnimSequence* Sequence = nullptr;
	float Time = 0.f, Weight = 0.f;
};

struct FDinkBodyActionFrame
{
	FDinkBodyLayer Timid, Confident;
	float Weight = 0.f, LowerBodyWeight = 0.f;
};

/** Snapshot the worker thread evaluates. */
struct FDinkBodyFrame
{
	TArray<FDinkBodyLayer, TInlineAllocator<12>> Base;
	TArray<FDinkBodyActionFrame, TInlineAllocator<2>> Actions;
	/** Upper-body lean in mesh space, degrees: X forward, Y to the character's left. */
	FVector2f Lean = FVector2f::ZeroVector;
	/** Light posture layer over the motion-capture clips, degrees: chest rounded forward, head
	 * lowered, shoulders drawn forward, upper arms brought in (W). Zero is the clip as captured. */
	FVector4f Posture = FVector4f(0, 0, 0, 0);
};

struct DINKCORE_API FDinkBodyAnimProxy : public FAnimInstanceProxy
{
	FDinkBodyAnimProxy() = default;
	explicit FDinkBodyAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;
	FDinkBodyFrame Frame;
private:
	TArray<bool> LowerBody;
	TArray<int32, TInlineAllocator<2>> LeanBones;
	int32 ChestBone = INDEX_NONE, HeadBone = INDEX_NONE, ClavicleL = INDEX_NONE, ClavicleR = INDEX_NONE, UpperArmL = INDEX_NONE, UpperArmR = INDEX_NONE;
	uint16 MaskSerial = 0;
	bool bMaskReady = false;
};

/**
 * Native animation of the hero and the humanoid NPCs: no animation blueprint. Locomotion is a
 * phase-locked blend of idle and authored gaits whose cadence follows the distance covered, so
 * stride length matches movement speed at every blend weight; timid and confident variants of
 * each clip are mixed by the hero's confidence; one-shot actions (attacks, hurt, stumble, land)
 * are layered on top, on the whole body when standing and on the upper body when moving.
 * Presentation only: it reads speed and state, never moves the capsule and owns no gameplay.
 */
UCLASS(Transient, NotBlueprintable)
class DINKCORE_API UDinkBodyAnimInstance : public UAnimInstance
{
	GENERATED_BODY()
public:
	/** Set is "Hero", "NpcF" or "NpcM". False (and nothing changes) when the set lacks an idle or a gait. */
	bool Configure(const TMap<FName, FDinkBodyClip>& Library, FName Set);
	bool IsConfigured() const { return Idle.IsValid() && Gaits.Num() > 0; }
	/** Called by the owner every frame before the mesh ticks. */
	void SetMotion(float SpeedCm, bool bAirborne, float Confidence, FVector2f LeanDegrees = FVector2f::ZeroVector);
	/** Plays Name_Timid/Name_Confident (or plain Name) once. bFullBody keeps the legs even while moving. */
	bool PlayAction(FName Name, bool bFullBody = false, float Scale = 1.f, float BlendIn = .07f, float BlendOut = .2f, bool bHoldLastFrame = false);
	/** Chest slouch, head drop and shoulder rounding in degrees (see FDinkBodyFrame::Posture). */
	void SetPosture(FVector4f Degrees) { Posture = Degrees; }
	/** How this body walks slower than its walk clip (see FDinkGaitBlend): 1 long slow steps, 0 short quick ones. */
	void SetSlowCadencePower(float Power) { SlowCadence = FMath::Clamp(Power, 0.f, 1.f); }
	void StopActions();
	bool HasClip(FName Name) const;
	bool IsActionActive() const;
	FName GetActionName() const { return ActionName; }
	float GetActionTime() const;
	float GetPhase() const { return Phase; }
	float GetCyclesPerSecond() const { return CyclesPerSecond; }
	float GetBlendedStrideCm() const { return BlendedStride; }
	float GetSpeed() const { return Speed; }
	const FDinkBodyFrame& GetFrame() const { return Frame; }
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;
protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FDinkBodyAnimProxy(this); }
private:
	struct FSlot
	{
		FDinkBodyClipPair Clips;
		float Time = 0.f, BlendIn = .07f, BlendOut = .2f, Scale = 1.f, Fade = 1.f;
		bool bFullBody = false, bActive = false, bFading = false, bHold = false;
	};
	bool FindPair(const TMap<FName, FDinkBodyClip>& Library, FName Name, FDinkBodyClipPair& Out) const;
	UPROPERTY(Transient) TMap<FName, FDinkBodyClip> Clips;
	UPROPERTY(Transient) FDinkBodyClipPair Idle;
	UPROPERTY(Transient) FDinkBodyClipPair Fall;
	UPROPERTY(Transient) TArray<FDinkBodyClipPair> Gaits;
	FSlot Slots[2];
	FName ActionName;
	FDinkBodyFrame Frame;
	float Speed = 0.f, Confidence = 0.f, Phase = 0.f, IdleTime = 0.f, FallTime = 0.f, AirAlpha = 0.f;
	float CyclesPerSecond = 0.f, BlendedStride = 0.f, MoveAlpha = 0.f;
	FVector2f Lean = FVector2f::ZeroVector;
	FVector4f Posture = FVector4f(0, 0, 0, 0);
	float SlowCadence = FDinkGaitBlend::SlowCadencePower;
	bool bAirborne = false;
	friend struct FDinkBodyAnimProxy;
};
