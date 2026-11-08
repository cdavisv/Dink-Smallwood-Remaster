#pragma once

#include "Engine/EngineTypes.h"

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

	inline const FName ProfileHardSolid(TEXT("DinkHardSolid"));
	inline const FName ProfileHardLow(TEXT("DinkHardLow"));
	inline const FName ProfileWarpTrigger(TEXT("DinkWarpTrigger"));
	inline const FName ProfileScreenVolume(TEXT("DinkScreenVolume"));
}
