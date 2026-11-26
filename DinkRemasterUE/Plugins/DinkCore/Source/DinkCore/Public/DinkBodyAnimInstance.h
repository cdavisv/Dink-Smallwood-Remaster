#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "BonePose.h"
#include "DinkFootPlacement.h"
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
	/** An action that leaves the standing posture for a while (he is flat on the ground): the
	 * additive posture layer is faded out between these two times, seconds; 0, 0 = never. */
	float PostureOffS = 0.f, PostureOnS = 0.f;
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

/** What the leg layer gets from the game thread each frame (see DinkFootPlacement.h). */
struct FDinkLegInput
{
	bool bEnabled = false, bTeleport = false, bAirborne = false;
	FTransform ComponentToWorld = FTransform::Identity;
	/** World velocity of the mesh component (its travel, smoothed lag included), cm/s. */
	FVector Velocity = FVector::ZeroVector;
	float DeltaTime = 0.f;
	/** 0 standing still .. 1 walking (120 cm/s and up). */
	float MoveAlpha = 0.f;
	bool bStanding = true;
	/** Visible ground under each foot (0 left, 1 right), as a height offset from the mesh origin's plane, cm (world), and its normal. */
	bool bGround[2] = {false, false};
	float GroundOffset[2] = {0.f, 0.f};
	FVector GroundNormal[2] = {FVector::UpVector, FVector::UpVector};
	/** Extra pelvis drop (cm, world) of a landing. */
	float LandingDip = 0.f;
	/** Stride factor of the style, as applied to the gait solver this frame (MoveAlpha already mixed in). */
	float StrideScale = 1.f;
	FDinkGaitStyle Style;
	float StepCycleCm = 0.f;
	/** The cadence factor the game thread applied this frame (FDinkLegTelemetry::CadenceWarp of the last evaluation). */
	float CadenceWarp = 1.f;
};

/** Head turned towards a point (component space), with a weight. */
struct FDinkLookInput
{
	FVector Target = FVector::ZeroVector;
	float Weight = 0.f;
};

/** What the leg layer did on the last evaluated frame, for tests and the motion trace. */
struct FDinkLegTelemetry
{
	uint8 State[2] = {0, 0};
	float LockWeight[2] = {0.f, 0.f};
	float KneeFlexDeg[2] = {0.f, 0.f};
	float PelvisOffsetCm = 0.f;
	float LookYawDeg = 0.f, LookPitchDeg = 0.f;
	int32 Steps[2] = {0, 0}, Plants[2] = {0, 0};
	/** Pins let go (both feet): lifted, ran off, too far from the pose. */
	int32 Releases[3] = {0, 0, 0};
	FVector FootWorld[2] = {FVector::ZeroVector, FVector::ZeroVector};
	/** The cadence factor the stride warp asks the game thread for (the style's cadence share of the correction), 1: none. */
	float CadenceWarp = 1.f;
	/** How much of the leg layer was laid on the pose: 1 standing on the feet, less while the pose lies or kneels (FDinkBodyAnimProxy::LyingLegShare). */
	float LegShare = 1.f;
	bool bValid = false;
};

/**
 * The hero's mannerism layer: how his confidence shows in the bones, on top of whatever clips
 * are playing. Posture is a pair of additive poses (Posture_Timid, Posture_Confident: bone
 * rotations away from the reference pose, applied in each bone's own frame) mixed by
 * confidence. The gait part belongs to the unsure lad only and fades to nothing with
 * confidence: arms that hang instead of swinging (one more than the other), a trunk that
 * rocks unevenly over the steps, a head that bobs, elbows that stick out when he runs. None of
 * it touches the pelvis or the legs' timing, so the feet stay where the gait put them.
 */
struct FDinkBodyMannerFrame
{
	const UAnimSequence* PostureTimid = nullptr;
	const UAnimSequence* PostureConfident = nullptr;
	const UAnimSequence* RunArms = nullptr;
	/** Standing pose the arms are pulled towards while he walks (their swing is damped). */
	FDinkBodyLayer ArmRest;
	float Confidence = 0.f;
	/** 0..1: share of the posture layer shown (an action authored with its own posture lowers it). */
	float PostureWeight = 0.f;
	/** Gait cycles (as FDinkBodyClip::TimeAtPhase counts them), 0..1 moving, 0..1 running. */
	float Phase = 0.f, MoveAlpha = 0.f, RunAlpha = 0.f;
	/** 0..1 after the actions' share is taken out: how much of the timid gait layer shows. */
	float Gait = 0.f;
	bool IsActive() const { return PostureTimid && PostureConfident; }
};

/** Snapshot the worker thread evaluates. */
struct FDinkBodyFrame
{
	FDinkLegInput Legs;
	FDinkLookInput Look;
	TArray<FDinkBodyLayer, TInlineAllocator<12>> Base;
	TArray<FDinkBodyActionFrame, TInlineAllocator<2>> Actions;
	/** Upper-body lean in mesh space, degrees: X forward, Y to the character's left. */
	FVector2f Lean = FVector2f::ZeroVector;
	/** Light posture layer over the motion-capture clips, degrees: chest rounded forward, head
	 * lowered, shoulders drawn forward, upper arms brought in (W). Zero is the clip as captured. */
	FVector4f Posture = FVector4f(0, 0, 0, 0);
	/** The hand that holds a weapon (0 left, 1 right): the grip pose (Grip_L / Grip_R, its held last frame) and how far
	 * the fingers of that hand have closed into it, 0..1. */
	FDinkBodyLayer Grip[2];
	/** 1: that arm also takes the grip pose (the weapon carried on guard) while no action plays; 0: the fingers only. */
	float Carry = 1.f;
	FDinkBodyMannerFrame Manner;
};

/** Pure numbers of the mannerism layer, shared by the runtime and its tests. */
struct DINKCORE_API FDinkMannerMaths
{
	/** Trunk roll of the timid gait, degrees, to the character's left: he rocks over each
	 * step, and further over one foot than the other. Zero when standing and for the hero. */
	static float GaitRoll(float Phase, float Timid, float MoveAlpha, float RunAlpha);
	/** Share of the arm swing taken away (X left arm, Y right arm): 0 = the clip's swing. */
	static FVector2f ArmSwingDamping(float Timid, float MoveAlpha, float RunAlpha);
	/** Cadence multiplier during a toe catch that began Seconds ago: the foot hangs, then two
	 * quick steps make the lost ground up. Its integral over CatchSeconds is CatchSeconds. */
	static float CatchCadence(float Seconds);
	static constexpr float CatchHang = .14f, CatchSeconds = .36f, CatchHangRate = .15f;
	/** How a walk slower than the walk clip is taken (FDinkGaitBlend's cadence power): the lad
	 * shuffles in short quick steps, the hero strides. Base is the body's own setting. */
	static float CadencePower(float Base, float Confidence) { return FMath::Clamp(Base + FMath::Lerp(-.3f, .15f, FMath::Clamp(Confidence, 0.f, 1.f)), 0.f, 1.f); }
	/** Share of the posture layer kept under an action clip of this name (older clips were
	 * authored with their own hunched stand). */
	static float PostureShareFor(FName Action);
};

struct DINKCORE_API FDinkBodyAnimProxy : public FAnimInstanceProxy
{
	FDinkBodyAnimProxy() = default;
	explicit FDinkBodyAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}
	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;
	FDinkBodyFrame Frame;
	FDinkLegTelemetry Telemetry;
private:
	void ApplyLegs(FCompactPose& Out);
	void ApplyChestSwing(FCompactPose& Out);
	void ApplyLook(FCompactPose& Out);
	FTransform ComponentSpace(const FCompactPose& Pose, int32 Index) const;
	TArray<bool> LowerBody;
	int32 PelvisBone = INDEX_NONE, NeckBone = INDEX_NONE, Spine3Bone = INDEX_NONE;
	int32 Thigh[2] = {INDEX_NONE, INDEX_NONE}, Calf[2] = {INDEX_NONE, INDEX_NONE}, Foot[2] = {INDEX_NONE, INDEX_NONE};
	float PlantedFootZ[2] = {0.f, 0.f}, LowZ[2] = {0.f, 0.f};
	/** The pelvis' height in the reference pose (component space): what standing on the feet is measured against. */
	float PelvisRefZ = 0.f;
	/**
	 * The leg layer's share of a pose (takeover A2, 25 Nov 2026): a pose whose pelvis is low (Botch_Faceplant lying, a kneel)
	 * does not stand on its feet, so foot pins, two-bone reach and pelvis offset fade out with it: 1 at 70 % of the reference
	 * pelvis height and above, 0 at 45 % and below (dink.Anim.LegsOffLying 0: always 1). On 23 Nov the layer pulled the
	 * lying hero's feet to the pins they had when he stood: knees folded, shins in the air, the trunk propped on the fists.
	 */
	float LyingLegShare(const FCompactPose& Pose) const;
	FVector FootForward[2] = {FVector::YAxisVector, FVector::YAxisVector};
	FDinkFootLock Locks[2];
	FVector PrevDesired[2] = {FVector::ZeroVector, FVector::ZeroVector};
	bool bPrevDesired = false;
	/** Stride warp: the planted foot's step length scaled so it travels back under the body exactly at the body's speed
	 * (the slow-walk cadence law and the clip's own stride leave it 15-20% off, which was the slide). Smoothed, 0.6-1.6. */
	float StrideWarp = 1.f, CadenceWarp = 1.f;
	float PrevStepY[2] = {0.f, 0.f};
	float PelvisOffset = 0.f, PelvisVelocity = 0.f;
	TArray<int32, TInlineAllocator<2>> LeanBones;
	int32 ChestBone = INDEX_NONE, HeadBone = INDEX_NONE, ClavicleL = INDEX_NONE, ClavicleR = INDEX_NONE, UpperArmL = INDEX_NONE, UpperArmR = INDEX_NONE;
	/** The finger bones below each hand (0 left, 1 right): what the grip pose replaces. */
	TArray<int32, TInlineAllocator<16>> GripBones[2];
	/** The arm of each side (upper arm, forearm, hand and their twist bones): what carries the weapon on guard. */
	TArray<int32, TInlineAllocator<8>> CarryBones[2];
	uint16 MaskSerial = 0;
	bool bMaskReady = false;
	/** Additive rotations of the mannerism poses, cached per bone container. */
	struct FAdditive { int32 Bone; FQuat Timid, Confident, RunArms; };
	TArray<FAdditive> Additives;
	TArray<int32, TInlineAllocator<6>> ArmBonesL, ArmBonesR;
	const UAnimSequence* CachedTimid = nullptr;
	const UAnimSequence* CachedConfident = nullptr;
	const UAnimSequence* CachedRunArms = nullptr;
	uint16 AdditiveSerial = 0;
	void BuildAdditives(FPoseContext& Output);
};

/** A foot set down (the leg layer pinned it): owner actor, foot bone (foot_l / foot_r), where, world. Game thread. */
DECLARE_MULTICAST_DELEGATE_ThreeParams(FDinkFootPlant, AActor* /*Owner*/, FName /*Foot*/, FVector /*WorldLocation*/);

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
	/**
	 * How much of the posture's W (upper arms brought in) gives way while an action clip plays (X, times its weight)
	 * and while the body runs (Y, times the run gaits' share of the base pose): W x (1 - X a) x (1 - Y r). The run and
	 * the wind-ups already carry the hands in front of the belly; at full W they lay both hands on it (A102, 23 Nov).
	 * Default (1, 0.7); posture.<set>.arm_fade in animation_natural.json overrides it, [0, 0] keeps W in every state.
	 */
	void SetArmFade(FVector2f Fade) { ArmFade = FVector2f(FMath::Clamp(Fade.X, 0.f, 1.f), FMath::Clamp(Fade.Y, 0.f, 1.f)); }
	FVector2f GetArmFade() const { return ArmFade; }
	static constexpr float DefaultArmFadeAction = 1.f, DefaultArmFadeRun = .7f;
	/** W's factor for an action weight and a run share, both 0..1 (see SetArmFade). */
	static float ArmPostureScale(float ActionWeight, float RunShare, FVector2f Fade);
	/** The factor the last update applied to W (1 when nothing faded it). */
	float GetArmPostureScale() const { return LastArmScale; }
	/** How this body walks slower than its walk clip (see FDinkGaitBlend): 1 long slow steps, 0 short quick ones. */
	void SetSlowCadencePower(float Power) { SlowCadence = FMath::Clamp(Power, 0.f, 1.f); }
	void StopActions();
	/**
	 * The hand that holds an item (hand_r, hand_l; NAME_None: neither), art row AN-05. While it is set the finger bones
	 * of that hand take the last frame of the pose clip Grip_R / Grip_L, eased in and out over GripBlendSeconds, under
	 * every clip the body plays. While no action plays that arm takes the pose too: the weapon is carried on guard, as
	 * the armed Dink's 1997 idle and walk pictures show it (dink.Anim.WeaponCarry 0: fingers only); an action has its
	 * own arm and wrist back for as long as it is blended in. Nothing happens when the library has no such clip.
	 * Presentation only.
	 */
	void SetGrip(FName HandBone) { GripHand = HandBone; }
	FName GetGrip() const { return GripHand; }
	/** Turns the head towards a world point (NPCs looking at Dink), Weight 0..1; limited to what a neck can turn. */
	void SetLookAt(const FVector& WorldTarget, float Weight) { LookWorld = WorldTarget; LookWeight = FMath::Clamp(Weight, 0.f, 1.f); }
	/** The leg layer's state on the last evaluated frame (game thread). */
	const FDinkLegTelemetry& GetLegTelemetry() const { return LegTelemetry; }
	FName GetSet() const { return SetName; }
	/** Every body running this animation: broadcast once each time a foot is set down (a gait step, a pivot step, a
	 * landing), at most once per 0.18 s per foot; nothing while dink.Anim.Legs or dink.Anim.FootLock is 0. For footsteps. */
	static FDinkFootPlant& OnFootPlant();
	/** Lets the current action go over Seconds (he starts walking in the middle of a fidget). */
	void FadeOutAction(float Seconds = .2f);
	/** The current action plays Rate times faster while the body is moving (a pratfall he
	 * scrambles out of instead of sliding along the ground). */
	void SetActionRushWhenMoving(float Rate) { Slots[0].RushRate = FMath::Max(1.f, Rate); }
	/** A toe catches: the step hangs and two quick ones follow (see FDinkMannerMaths::CatchCadence). */
	void TriggerCatchStep() { CatchTime = 0.f; }
	/** True when the hero's additive posture clips are loaded: the bone-level mannerism layer is on. */
	bool HasMannerisms() const { return bMannerisms; }
	/** 0..1 scale of the mannerism layer (a wall in front of him takes most of the slump away). */
	void SetMannerScale(float Scale) { MannerScale = FMath::Clamp(Scale, 0.f, 1.f); }
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
		float Time = 0.f, BlendIn = .07f, BlendOut = .2f, Scale = 1.f, Fade = 1.f, FadeSeconds = .09f, RushRate = 1.f, PostureShare = 1.f;
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
	FVector2f ArmFade = FVector2f(DefaultArmFadeAction, DefaultArmFadeRun);
	float LastArmScale = 1.f;
	float SlowCadence = FDinkGaitBlend::SlowCadencePower;
	bool bAirborne = false, bWasAirborne = false, bLegsReady = false;
	FName SetName;
	FVector LookWorld = FVector::ZeroVector;
	float LookWeight = 0.f, AirTime = 0.f, LandTime = 10.f, LandAmplitude = 0.f;
	float GroundSmoothed[2] = {0.f, 0.f};
	FVector LastComponentLocation = FVector::ZeroVector;
	FDinkLegTelemetry LegTelemetry;
	float LastPlant[2] = {-1.f, -1.f};
	/** Standing weight as shown (eased towards the solver's) and the gait mix last seen while moving. */
	float IdleShown = 1.f;
	bool bSnapStand = true;
	TArray<float, TInlineAllocator<4>> LastGait;
	static constexpr float StandBlendSeconds = .22f;
	FName GripHand;
	float GripShown[2] = {0.f, 0.f};
	static constexpr float GripBlendSeconds = .12f;
	void UpdateLegInput(float Dt);
	void PublishFrame();
	float CatchTime = 1.e9f, MannerScale = 1.f;
	UPROPERTY(Transient) FDinkBodyClip PostureTimid;
	UPROPERTY(Transient) FDinkBodyClip PostureConfident;
	UPROPERTY(Transient) FDinkBodyClip RunArms;
	bool bMannerisms = false;
	friend struct FDinkBodyAnimProxy;
};
