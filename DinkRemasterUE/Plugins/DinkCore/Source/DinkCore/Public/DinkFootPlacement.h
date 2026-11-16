#pragma once

#include "CoreMinimal.h"

/**
 * Presentation-only leg placement for the native body animation (UDinkBodyAnimInstance): where each foot is put
 * on the ground and how the leg reaches it. Nothing here moves the capsule, the scripted sprite or any gameplay
 * state; it only bends the drawn legs. Pure maths (no world), shared by the runtime and the Dink.Animation tests.
 *
 * - FDinkTwoBoneIK: hip-knee-ankle reach with a soft limit near full extension (no knee pop, no hyperextension:
 *   the knee bends in the plane of the animated knee, never backwards).
 * - FDinkFootLock: one foot's contact. A foot the animation sets down (low and still over the ground in the body's
 *   travelling frame) is pinned where it landed, so it does not slide or spin with the body; it is let go, with a
 *   short blend, when the animation lifts it. When the body turns or shifts on the spot and a pinned foot ends up
 *   too far from where the pose wants it, the foot takes a step there (one foot at a time, lifted on an arc) instead
 *   of the body spinning on planted feet.
 * - FDinkGaitStyle: per character, how their walk differs from the shared motion capture (step length, and so
 *   cadence; stance width; how quick their pivot steps are; how much the chest swings against the hips).
 */
struct DINKCORE_API FDinkTwoBoneIK
{
	/**
	 * Hip, Knee, Ankle: the animated chain. Target: where the ankle should go. Pole: a point the knee should face
	 * (normally the animated knee pushed forward). Writes the new knee and ankle; the bone lengths are kept.
	 * SoftShare: the last share of the reach over which the leg straightens smoothly instead of snapping straight.
	 * SoftStart: the soft zone never begins before this hip-to-ankle distance (pass the animated one, so a pose the
	 * clip already reaches is returned unchanged). Returns how far the ankle stayed short of the target (0 when reached).
	 */
	static float Solve(const FVector& Hip, const FVector& Knee, const FVector& Ankle, const FVector& Target, const FVector& PoleDirection,
		FVector& OutKnee, FVector& OutAnkle, float SoftShare = .04f, float SoftStart = 0.f);
	/** Knee flexion in degrees: 0 straight, positive bent with the knee towards PoleDirection, negative hyperextended. */
	static float Flexion(const FVector& Hip, const FVector& Knee, const FVector& Ankle, const FVector& PoleDirection);
};

struct DINKCORE_API FDinkFootLockSettings
{
	/** A foot locks when it is this close to its planted height and moving slower than LockSpeed over the ground. */
	float LockHeight = 3.f, LockSpeed = 45.f;
	/** Moving (walking, running): a pin follows the pose's foot once it is further than this from it, cm (the stride warp keeps the
	 * pose's planted foot close to the ground speed, so this only takes up what is left over a stance), so the clip's
	 * own drift is taken up a little at a time instead of stretching the leg. */
	float PinSlack = 16.f;
	/** Standing: a pinned foot this far (cm) or this turned (degrees) from where the pose wants it takes a step. */
	float StepDistance = 11.f, StepYaw = 32.f;
	/** Step timing (s, scaled by distance between Min and Max) and the lift at its middle (cm, for a 20 cm step). */
	float StepTimeMin = .17f, StepTimeMax = .3f, StepLift = 6.f;
	/** Let-go blend once the animation lifts the foot, s; a pinned foot further than this from the pose is let go. */
	float ReleaseTime = .12f, MaxError = 24.f;
	/** Yaw a pinned foot may keep against the leg before it must step, degrees. */
	float MaxPinnedYaw = 40.f;
};

/** One foot's contact state, in world space. */
struct DINKCORE_API FDinkFootLock
{
	enum class EState : uint8 { Free, Locked, Stepping };
	struct FInput
	{
		/** Where the pose (after the style) wants the foot this frame, and its yaw, world. */
		FVector Desired = FVector::ZeroVector;
		float DesiredYaw = 0.f;
		/** Speed of the desired foot over the ground (the body's travel included, its turning not), cm/s. */
		float GroundSpeed = 0.f;
		/** Height of the animated foot above its planted height, cm. */
		float Height = 0.f;
		/** The body is standing (not walking or running): pinned feet may step instead of sliding. */
		bool bStanding = true;
		/** Locks are allowed (on the ground, nothing switched off). */
		bool bAllowed = true;
		/** New pins may be made (false when running: the run's capture already holds its short stance, and pins there only
		 * stretched the legs and dropped the pelvis; a pin already held is let go when the pose lifts the foot, as ever). */
		bool bNewPins = true;
		/** The other foot is pinned, so this one may lift for a step. */
		bool bOtherPinned = true;
		/** Pivot-step time scale (personality: a timid lad shuffles round more slowly). */
		float StepTimeScale = 1.f;
	};
	struct FOutput
	{
		/** Where to put the foot, world (Z: the desired height plus any step lift; the ground is added later). */
		FVector Position = FVector::ZeroVector;
		float Yaw = 0.f;
		/** How much of the pin is in Position (0: the pose's own foot). */
		float Weight = 0.f;
		float Lift = 0.f;
	};
	FOutput Update(const FInput& In, float DeltaTime, const FDinkFootLockSettings& S);
	/** Back to the pose's own foot at once (a warp). The plant count is kept; the next pin after a reset is not a plant. */
	void Reset() { State = EState::Free; Weight = 0.f; StepT = 0.f; bWantsStep = false; bLifted = false; FastFrames = 0; }
	/** Feet set down so far: a pin after the pose lifted the foot, or the end of a pivot step (footsteps). */
	int32 GetPlants() const { return Plants; }
	/** Why pins were let go so far: the pose lifted the foot, it ran off over the ground, it was too far from the pose. */
	int32 GetReleases(int32 Reason) const { return Releases[FMath::Clamp(Reason, 0, 2)]; }
	EState GetState() const { return State; }
	bool IsPinned() const { return State == EState::Locked && Weight > .99f; }
	bool WantsStep() const { return bWantsStep; }
	const FVector& GetPin() const { return Pin; }
	int32 GetSteps() const { return Steps; }
private:
	EState State = EState::Free;
	FVector Pin = FVector::ZeroVector, StepFrom = FVector::ZeroVector;
	float PinYaw = 0.f, StepFromYaw = 0.f, Weight = 0.f, StepT = 0.f, StepTime = .2f, StepDist = 0.f;
	bool bWantsStep = false, bLifted = false;
	int32 Steps = 0, Plants = 0, FastFrames = 0;
	int32 Releases[3] = {0, 0, 0};
};

/** How one character's legs and trunk differ from the shared motion capture; mixed by confidence for the hero. */
struct DINKCORE_API FDinkGaitStyle
{
	/** Step length against the clip's (cadence rises by the inverse: speed is kept). */
	float Stride = 1.f;
	/** Each foot set this much further out (+) or in (-) from the clip's line, cm. */
	float WidthCm = 0.f;
	/** One leg's step longer than the other's by this share (an uneven, untrained gait). */
	float Uneven = 0.f;
	/** Pivot steps take this much longer (>1) or shorter. */
	float StepTime = 1.f;
	/** Gain on the chest's turn against the hips while walking (1: as captured; >1 a swagger). */
	float ChestSwing = 1.f;
	static FDinkGaitStyle Lerp(const FDinkGaitStyle& A, const FDinkGaitStyle& B, float T);
	/** Style of an animation set ("Hero", "NpcF", "NpcM") at a confidence, from animation_natural.json `style`; neutral when absent. */
	static FDinkGaitStyle For(FName Set, float Confidence);
	/** Re-read the json (tests). */
	static void Reload();
};

class AActor;
class UWorld;
/** The visible ground under a point, as the leg layer and dink.Motion.Trace see it: the first hit on a visible, non-character
 * surface between 45 cm above and 50 cm below FloorZ. The 1997 hardness prisms and the player-only blockers are never
 * ground, nor is a hit that starts inside a surface. Game thread. */
struct DINKCORE_API FDinkFootGround
{
	static bool Trace(UWorld* World, const FVector& At, float FloorZ, const AActor* Ignore, float& OutZ, FVector& OutNormal, FString* OutWhat = nullptr);
};
