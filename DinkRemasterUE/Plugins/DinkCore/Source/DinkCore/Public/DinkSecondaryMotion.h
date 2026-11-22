#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "UObject/ObjectKey.h"
#include "DinkSecondaryMotion.generated.h"

class USkeletalMeshComponent;
class UMaterialParameterCollection;
struct FCompactPose;

/**
 * Secondary motion of the characters (hair, Mother's skirt, a short hit jolt). Presentation only: nothing here
 * moves a capsule, a scripted position, hardness or any script-visible state.
 *
 * None of the character meshes has hair, skirt or cloth bones (all three use the 89 mannequin bones) and none carries
 * clothing data, so the motion is a damped spring per body part, run on the game thread, whose state reaches the
 * materials as custom primitive data (the hair and outfit materials of Scripts/import_photoreal_art.py turn it into
 * a world position offset). The hit jolt is a spring on spine_03, neck_01 and head, added after the body animation
 * (FDinkSecondaryMotion::ApplyToPose, called at the end of FDinkBodyAnimProxy::Evaluate).
 *
 * Custom primitive data layout (all in component space, mesh units):
 *   0..2  hair tip offset            3  hair yaw lag (radians about the component's up axis)
 *   4..6  head centre                7  hair weight (0 = off)
 *   8..11 pelvis-rigid rotation (quaternion x y z w; all zero = skirt off)   12..14 pelvis-rigid translation
 *   15..17 hip L   18..20 knee L   21..23 ankle L   24..26 hip R   27..29 knee R   30..32 ankle R
 *   33..35 skirt sway at the hem
 * where "pelvis-rigid" maps a bind-pose (pre-skinned) position to where it would be if it were bound to the pelvis.
 */
namespace DinkSecondaryCPD
{
	constexpr int32 HairOffset = 0, HairYaw = 3, HeadCentre = 4, HairWeight = 7;
	constexpr int32 PelvisRotation = 8, PelvisTranslation = 12;
	constexpr int32 HipL = 15, KneeL = 18, AnkleL = 21, HipR = 24, KneeR = 27, AnkleR = 30, SkirtSway = 33;
	constexpr int32 Count = 36;
}

/** Natural frequency, damping ratio and travel limit of one spring. */
struct DINKCORE_API FDinkSpringParams
{
	float FrequencyHz = 2.f;
	float Damping = .3f;
	/** The state never leaves this radius (cm, or radians / degrees for an angular spring). */
	float Max = 2.f;
	/** How much of the anchor's acceleration the free end feels (1 = a pendulum hung from it). */
	float InertiaGain = 1.f;
};

/** A damped spring in three dimensions: the lag of a free end hung from a moving anchor. */
struct DINKCORE_API FDinkSpring3
{
	FVector X = FVector::ZeroVector, V = FVector::ZeroVector;
	/** Advances by Dt (fixed sub-steps of at most 1/120 s). AnchorAccel is the anchor's acceleration (the end lags
	 * against it), Force an extra acceleration such as wind (cm/s^2). Non-finite input resets the spring. */
	void Step(float Dt, const FVector& AnchorAccel, const FVector& Force, const FDinkSpringParams& P);
	/** Adds a velocity (an impulse), bounded so that a stack of hits cannot fling the state. */
	void Kick(const FVector& DeltaV, const FDinkSpringParams& P);
	void Reset() { X = V = FVector::ZeroVector; }
	bool IsAtRest(float Tolerance = .01f) const { return X.SizeSquared() < Tolerance * Tolerance && V.SizeSquared() < Tolerance * Tolerance; }
};

/** Per character part tuning (cm, Hz). The table lives in DinkSecondaryMotion.cpp, keyed by mesh asset name. */
struct DINKCORE_API FDinkSecondaryProfile
{
	FName Mesh;
	FDinkSpringParams Hair, HairYaw, Skirt, Jolt;
	/** Hair tip deflection per metre per second of wind (cm). */
	float HairWindCm = 0.f;
	/** Loose parts with bones of their own (antennae, ears, tails), root to tip; each lags its root's acceleration. */
	TArray<TArray<FName>> Chains;
	FDinkSpringParams Chain;
	bool bHair = false, bSkirt = false, bJolt = true;
	static const FDinkSecondaryProfile* Find(FName MeshName);
};

/** State the game thread keeps per animated body. */
struct DINKCORE_API FDinkSecondaryBody
{
	TWeakObjectPtr<USkeletalMeshComponent> Mesh;
	/** The key its published pose state is filed under (still valid when the component is gone). */
	TObjectKey<USkeletalMeshComponent> Key;
	const FDinkSecondaryProfile* Profile = nullptr;
	TWeakObjectPtr<const UObject> MeshAsset;
	int32 Head = INDEX_NONE, Pelvis = INDEX_NONE, ThighL = INDEX_NONE, ThighR = INDEX_NONE, CalfL = INDEX_NONE, CalfR = INDEX_NONE, FootL = INDEX_NONE, FootR = INDEX_NONE;
	FTransform PelvisBind = FTransform::Identity;
	FDinkSpring3 Hair, HairYaw, Skirt, Jolt;
	/** Per loose-part chain: the spring (mesh space, cm at the tip) and its root's motion history (world). */
	TArray<FDinkSpring3, TInlineAllocator<4>> ChainSprings;
	TArray<FVector, TInlineAllocator<4>> ChainPrev, ChainPrevVel, ChainAccel;
	FVector PrevHead = FVector::ZeroVector, PrevHeadVel = FVector::ZeroVector, HeadAccel = FVector::ZeroVector;
	FVector PrevPelvis = FVector::ZeroVector, PrevPelvisVel = FVector::ZeroVector, PelvisAccel = FVector::ZeroVector;
	float PrevYaw = 0.f, PrevYawRate = 0.f, YawAccel = 0.f;
	int32 PrevLife = INDEX_NONE;
	int32 HistoryFrames = 0;
	double LastUpdate = 0.0;
	/** Spring time owed at Medium quality (the springs step at 30 Hz, the pose data every frame). */
	float SpringDebt = 0.f;
	bool bWritten = false;
	void ResetMotion();
};

/** Static entry points: the pose hook (worker-thread safe) and pure helpers the tests use. */
struct DINKCORE_API FDinkSecondaryMotion
{
	/** Adds the current hit jolt of this mesh to a finished local-space pose. No-op when there is none. Never touches
	 * root, pelvis or the legs. Safe on the animation worker thread. */
	static void ApplyToPose(const USkeletalMeshComponent* Mesh, FCompactPose& Pose);
	/** The jolt (degrees: X forward tilt, Y tilt to the character's left, Z twist) last published for Mesh. */
	static FVector3f GetPublishedJolt(const USkeletalMeshComponent* Mesh);
	static void PublishJolt(const USkeletalMeshComponent* Mesh, const FVector3f& Degrees);
	/** Publishes the jolt and the loose-part lags (mesh space, cm at each chain's tip, in Profile->Chains order). */
	static void Publish(const USkeletalMeshComponent* Mesh, const FVector3f& Degrees, const FDinkSecondaryProfile* Profile, TConstArrayView<FVector3f> ChainLags);
	static void ForgetMesh(const USkeletalMeshComponent* Mesh);
	static void ForgetKey(TObjectKey<USkeletalMeshComponent> Key);
	/** The foliage's wind gust field at a world position and game time, as the foliage material computes it (world-alive's
	 * WIND_HLSL, Scripts/world_life_wind.py): value noise of about 14 m and 5 m cells travelling along WindDir at Travel,
	 * 0.45 calm to 1.95 at a crest, blended towards 1 by (1 - Gustiness). The defaults are master's foliage breeze. */
	static float FoliageGust(const FVector2D& WorldXY, float TimeSeconds, const FVector2D& WindDir = FVector2D(.92, .39), float Travel = 1.f, float Gustiness = 1.f);
};

/**
 * Finds the animated character bodies in the world (every 0.5 s), advances their springs every frame and writes the
 * custom primitive data their materials read. Console: dink.Hair.Physics, dink.Garment.Physics, dink.HitReaction.Physics
 * dink.LooseParts.Physics (0 = off), dink.Secondary.Scale, dink.Secondary.Report. Scalability: off at effects quality Low, 30 Hz at Medium.
 */
UCLASS()
class DINKCORE_API UDinkSecondaryMotionSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual bool IsTickableInEditor() const override { return false; }

	/** A hit on Actor from WorldDirection (the direction the blow travels; zero = from the front), Strength 0..1. */
	void NotifyHit(AActor* Actor, const FVector& WorldDirection, float Strength = 1.f);
	/** Starts tracking Mesh now (tests; the scan finds bodies by itself). False when its mesh has no profile. */
	bool Track(USkeletalMeshComponent* Mesh);
	const FDinkSecondaryBody* FindBody(const USkeletalMeshComponent* Mesh) const;
	int32 NumBodies() const { return Bodies.Num(); }
	/** Mean game-thread cost of one body's update over the last report window, microseconds. */
	double GetMeanBodyMicros() const { return MeanMicros; }
	/** Advances every body by DeltaTime regardless of pause or the update rate (tests). */
	void StepForTest(float DeltaTime) { bIgnoreVisibility = true; Advance(DeltaTime, true); }
	FString Report() const;

private:
	void Scan();
	void Advance(float DeltaTime, bool bForce);
	/** DeltaTime moves the anchors' history and the custom primitive data (every frame); SpringDt advances the springs
	 * (0 between the 30 Hz steps at Medium). False when the body was skipped (off screen, no pose). */
	bool UpdateBody(FDinkSecondaryBody& Body, float DeltaTime, float SpringDt);
	void WriteOff(FDinkSecondaryBody& Body);
	void RebuildIndex();
	/** Wind for the hair at a world position (cm/s-scaled force direction and speed in m/s), with the gust. */
	bool HairWind(const FVector& At, FVector& OutDir, float& OutSpeed) const;
	FVector HitDirection(const USkeletalMeshComponent* Mesh) const;
	TArray<FDinkSecondaryBody> Bodies;
	TMap<TObjectKey<USkeletalMeshComponent>, int32> Index;
	/** World-alive's MPC_Dink_World when the build carries it (retried at every scan until found). */
	UPROPERTY(Transient) TObjectPtr<UMaterialParameterCollection> WindMpc;
	bool bOff = false;
	double NextScan = 0.0, Accumulated = 0.0, CostMicros = 0.0, MeanMicros = 0.0;
	int32 CostSamples = 0;
	/** Tests step bodies that never render. */
	bool bIgnoreVisibility = false;
};
