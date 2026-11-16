#pragma once

#include "Engine/EngineTypes.h"
#include "CollisionQueryParams.h"

/**
 * Collision channels and profiles for the original's hardness codes. Defined in
 * Config/DefaultEngine.ini ([/Script/Engine.CollisionProfile]); keep the two in step.
 *
 *   hardness 1, 3 (tile), 100 (sprite hardbox), 200 (warp hardbox) -> profile DinkHardSolid
 *   hardness 2 "low" (water edges, fences: projectiles and flyers cross) -> profile DinkHardLow
 *
 * Both block pawns. DinkHardLow ignores the DinkProjectile trace channel (and Visibility/Camera),
 * which is the difference the original makes between the two codes.
 */
namespace DinkCollision
{
	/** Trace channel for projectiles (fireballs, arrows, thrown things). */
	inline constexpr ECollisionChannel Projectile = ECC_GameTraceChannel1;
	/** Object channel of solid hardness blockers. */
	inline constexpr ECollisionChannel HardSolid = ECC_GameTraceChannel2;
	/** Object channel of low hardness blockers. */
	inline constexpr ECollisionChannel HardLow = ECC_GameTraceChannel3;
	/**
	 * Object channel of player-only blockers: drawn solid things (a boulder, a trunk) larger than their 1997 hardness.
	 * No component responds to it by default and its profile ignores every channel but Pawn (projectiles, sight and the
	 * camera pass); the player capsule blocks it. Pawn-channel queries made for anything else (NPC and creature moves) must
	 * pass IgnorePlayerBlockers(): a query's own default responses block every object type, this one included.
	 */
	inline constexpr ECollisionChannel PlayerBlock = ECC_GameTraceChannel4;

	/**
	 * Query responses for a body that is not the player (an NPC, a creature) or for a query that must see the world as it
	 * was before the player-only blockers: every channel blocks, as a query without response params does, except
	 * DinkPlayerBlock. A query without response params blocks against every object type, and the blocker profile blocks Pawn,
	 * so a Pawn-channel query on simple collision without these stops at the drawn outline of a boulder or trunk. (A complex
	 * query misses the blocker anyway: it is a convex-only procedural mesh with no complex geometry. The NPC moves trace
	 * complex today; the responses keep them right if that ever changes.)
	 */
	inline FCollisionResponseParams IgnorePlayerBlockers()
	{
		FCollisionResponseParams Responses(ECR_Block);
		Responses.CollisionResponse.SetResponse(PlayerBlock, ECR_Ignore);
		return Responses;
	}

	inline const FName ProfileHardSolid(TEXT("DinkHardSolid"));
	inline const FName ProfileHardLow(TEXT("DinkHardLow"));
	inline const FName ProfilePlayerBlock(TEXT("DinkPlayerBlock"));
	inline const FName ProfileWarpTrigger(TEXT("DinkWarpTrigger"));
	inline const FName ProfileScreenVolume(TEXT("DinkScreenVolume"));
}
