#pragma once

#include "CoreMinimal.h"

class UWorld;

/**
 * Review tool (takeover A5, 25 Nov 2026): which skeletal LOD the play camera shows the townsfolk. The photoreal people's LOD1
 * to LOD3 are hair-heavy (art-people-5, 23 Nov) and their LOD screen sizes were never read: `lod_info` is not exposed to the
 * editor's Python. This lists, for every people mesh of creatures.json (class rows of /Game/Dink/Photoreal/Characters/NPC/),
 * every mesh of characters.json and the hero, each LOD's screen size, hysteresis and triangles, and the LOD the engine's rule
 * picks (FSkeletalMeshObject::UpdateMinDesiredLODLevel: the worst LOD whose (ScreenSize / 2)^2 exceeds the bounds' screen
 * radius squared, r.SkeletalMeshLODRadiusScale applied) for the play camera at a list of distances. The camera is the hero's
 * follow camera (90 degrees horizontal, a 16:9 view, the boom's 400 cm) unless a player camera is live, whose FOV and aspect
 * are used. With a world, the class figures standing in it are listed too with their distance to the camera and, in a
 * rendered game, the LOD the renderer chose (GetPredictedLODLevel; always 0 without a renderer).
 * Console: dink.LodDump [distance_cm ...]. Writes Saved/Art/lod_screen_sizes.txt and returns the text.
 */
namespace DinkLodDump
{
	/** Bounds' screen radius squared as the engine computes it (ComputeBoundsScreenRadiusSquared) for a camera of HorizontalFovDeg and Aspect. */
	DINKCORE_API float ScreenRadiusSquared(float SphereRadiusCm, float DistanceCm, float HorizontalFovDeg, float Aspect);
	/** The LOD UpdateMinDesiredLODLevel picks from those screen sizes (no hysteresis: a body coming into view). */
	DINKCORE_API int32 PickLod(const TArray<float>& ScreenSizes, float ScreenRadiusSq);
	DINKCORE_API FString Write(UWorld* World, const TArray<float>& DistancesCm);
}
