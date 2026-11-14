#pragma once

#include "CoreMinimal.h"

class FJsonObject;

/**
 * Class-wide creature art: one row of `classes` in Content/Dink/Data/Art/creatures.json binds a sprite class
 * (tools/data/sprite_classes.csv `class_id`) to an animated mesh, so every placement of that class on every screen, and
 * every sprite a script creates with one of the row's sequences, is shown by the creature instead of a sprite card.
 *
 * Presentation only. The DinkC scripts and the sprite simulation keep driving position, facing, brain, speed, hits,
 * death and removal; the mesh follows the sprite. A class row adds no collision, no body boxes, no actor tag that
 * gameplay reads and never writes to a sprite. Origin rows (`placements`) and every other Data/Art manifest that names
 * an origin keep precedence. Mirrored by Scripts/art_coverage.py (creature_class_rows / "class-bound").
 */

/** One gait clip of a locomotion set and the ground speed it was authored for (its feet do not slide at that speed). */
struct DINKCORE_API FDinkCreatureGait
{
	FString Clip;
	float SpeedCmS = 0.f;
	/** Gait cycles the clip holds. */
	float Cycles = 1.f;
};

/**
 * Locomotion by measured speed (JSON `locomotion`: {"idle": clip, "gaits": [{"clip", "speed_cm_s", "cycles"}]}, gaits
 * slowest first). Clips are blended natively and the cycle advances by distance over the blended stride, so no blend
 * space asset is needed and the feet keep their ground at any speed.
 */
struct DINKCORE_API FDinkCreatureLocomotion
{
	FString Idle;
	TArray<FDinkCreatureGait> Gaits;
	bool IsSet() const { return !Idle.IsEmpty() && Gaits.Num() > 0; }
};

/** How one group of sprite sequences is shown (JSON `roles`, keyed by a free name). */
struct DINKCORE_API FDinkCreatureRole
{
	FName Name;
	/** Sprite sequences (dink.ini numbers) that mean this role: the walk facings, an attack, the headless run. */
	TArray<int32> Sequences;
	/** true (JSON "locomotion": true, or an object with the role's own set): idle and gaits by measured speed. Otherwise `Clip`. */
	bool bLocomotion = false;
	/** Animation sequence path played for the role (empty with bLocomotion). */
	FString Clip;
	/** Clip loops while the sprite stays in the role; false plays it once over the sprite sequence's own duration and holds the last pose. */
	bool bLoop = false;
	/** Optional skeletal mesh shown in this role instead of the row's mesh (same skeleton): the headless duck. */
	FString Mesh;
	/** The role's own locomotion set (with bLocomotion); unset = the row's. */
	FDinkCreatureLocomotion Locomotion;
};

/** What the original leaves where a sprite of the class is killed (add_kill_sprite, dink.cpp:12359). */
struct DINKCORE_API FDinkCreatureCorpse
{
	/** Death sequences (base_death + facing) the corpse stands for; the kill leaves it only when the sprite's own death sequence is one of them. */
	TArray<int32> Sequences;
	/** Static mesh path left on the ground until the player leaves the screen, as the original's corpse sprite. */
	FString Mesh;
	FVector OffsetCm = FVector::ZeroVector;
	double YawOffset = 0.0;
	double Scale = 1.0;
	/**
	 * Optional blood on the ground (JSON `decal`: {"material", "size_cm": [along, across], "depth_cm"}): a deferred decal
	 * projected straight down under the corpse, so the pool also stains the grass that would hide a flat mesh. The
	 * texture's right is the corpse's forward. The corpse mesh itself receives no decal.
	 */
	FString DecalMaterial;
	FVector2D DecalSizeCm = FVector2D::ZeroVector;
	double DecalDepthCm = 45.0;
};

/** One row of `classes`. */
struct DINKCORE_API FDinkCreatureClassBinding
{
	FName ClassId;
	FString Mesh;
	FDinkCreatureLocomotion Locomotion;
	TArray<FDinkCreatureRole> Roles;
	/** sequence -> index into Roles. */
	TMap<int32, int32> RoleBySequence;
	TArray<FDinkCreatureCorpse> Corpses;
	/** Material overrides by slot name (one mesh, several colours: the slimes). */
	TMap<FName, FString> Materials;
	FVector OffsetCm = FVector::ZeroVector;
	/** Pitch, yaw, roll added to the facing (degrees), as the origin rows' rotation_deg. */
	FVector RotationDeg = FVector::ZeroVector;
	double Scale = 1.0;
	/** Below this measured speed the creature stands (idle clip only), cm/s. */
	float StationarySpeedCmS = 5.f;
	/** Cross-fade between roles and between two plays of a clip, s. */
	float BlendTimeS = 0.12f;
	/** Averaging time of the shown position, s (the sprite moves in whole pixels on 60 Hz frames). 0 glues the mesh to the sprite. */
	float SmoothTimeS = 0.1f;
	float TurnRateDegS = 540.f;
	/** Beyond this distance from the camera the mesh is not drawn (and its pose not evaluated), cm. 0 = never culled. */
	float CullDistanceCm = 15000.f;
	FString Note;

	const FDinkCreatureRole* RoleFor(int32 Sequence) const
	{
		const int32* Index = RoleBySequence.Find(Sequence);
		return Index ? &Roles[*Index] : nullptr;
	}
	/** Corpse for a kill: the sprite's death sequence with the engine's mirrored-facing fallback (dink.cpp:12392-12404). */
	const FDinkCreatureCorpse* CorpseFor(int32 BaseDeath, int32 Dir) const;
};

/** Why a placement is or is not shown by its class row. */
enum class EDinkCreatureClassDecision : uint8
{
	Bound,
	NoRow,
	/** A creatures/characters/replacement/hide row of any Data/Art manifest names this origin. */
	OriginPrecedence,
	/** Type 2 hardness proxy or a placement without a picture. */
	NoPicture,
};

namespace DinkCreatureClass
{
	/** The sprite a role and a corpse are decided from, as the simulation holds it. Plain data: no world needed. */
	struct FSpriteView
	{
		/** Animating sequence (sp_seq), 0 when the picture stands still. */
		int32 Seq = 0;
		/** Picture sequence (sp_pseq): what a still sprite shows. */
		int32 PSeq = 0;
		int32 BaseWalk = -1;
	};

	/**
	 * Reads `classes` of a parsed creatures.json. Rows that lack a class, a mesh, a locomotion role or name a sequence
	 * twice are skipped and reported; a class listed twice keeps its first row. Returns the rows kept.
	 */
	DINKCORE_API int32 ParseBindings(const FJsonObject& Manifest, TArray<FDinkCreatureClassBinding>& Out, TArray<FString>* Problems = nullptr);

	/** Class row of a placement, by its class id; origins a manifest already binds are never taken. */
	DINKCORE_API EDinkCreatureClassDecision Decide(const TArray<FDinkCreatureClassBinding>& Bindings, FName ClassId, const FString& Origin,
		const TSet<FString>& PrecedenceOrigins, bool bHasPicture, const FDinkCreatureClassBinding*& OutBinding);

	/** Class row of a script-made sprite: the first row one of whose sequences is the sprite's picture, else one of its walk base's facings. */
	DINKCORE_API const FDinkCreatureClassBinding* FindBySprite(const TArray<FDinkCreatureClassBinding>& Bindings, const FSpriteView& Sprite);

	/** Role shown for the sprite: its animating sequence, else its still picture, else the first locomotion role. */
	DINKCORE_API const FDinkCreatureRole* RoleForSprite(const FDinkCreatureClassBinding& Binding, const FSpriteView& Sprite);

	/**
	 * The direction a killed sprite's corpse is made for. pill_brain and people_brain turn a missing direction into 3 and a
	 * cardinal one into its diagonal first (change_dir_to_diag, dink.cpp:12877-12885, called at 12908-12909 and 13106-13108);
	 * dragon_brain passes the direction as it is (dink.cpp:13254).
	 */
	DINKCORE_API int32 KillDir(int32 Brain, int32 Dir);

	/** Numpad direction of a walk sequence (131 -> 1), 0 when the last digit is not a direction. */
	DINKCORE_API int32 DirOfSequence(int32 Sequence);

	/** Screen-space angle of a numpad direction, degrees from east towards south (the director's DirAngle). */
	DINKCORE_API double DirYawDegrees(int32 Dir);

	/**
	 * Weights of idle and of each gait (slowest first) and the cycles per second at which the blended stride covers
	 * exactly Speed. Strides are the ground one cycle of each gait covers (speed x duration / cycles). Below Stationary the
	 * creature stands. Pure maths.
	 */
	DINKCORE_API void SolveGaits(float Speed, float Stationary, TConstArrayView<float> GaitSpeeds, TConstArrayView<float> GaitStrides,
		float& OutIdle, TArray<float, TInlineAllocator<4>>& OutWeights, float& OutCyclesPerSecond);
}
