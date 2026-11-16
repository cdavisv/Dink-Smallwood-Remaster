#pragma once

#include "CoreMinimal.h"

class UWorld;
class ADinkScreenVolume;

/**
 * Where a family mesh stands (families.json "anchor"; physical mapping, 15 Nov 2026). Presentation only: the 1997 hardness,
 * hit and touch boxes stay where the engine puts them; the mesh moves to them.
 *  - Card (default): the card's ground point (picture centre east-west, the placement's depth), as before.
 *  - Hardbox: the centre of the placement's 1997 hardbox (dink.ini, frames.csv), so a tree's trunk stands where the 1997
 *    trunk blocks instead of at the middle of its picture.
 *  - HardboxInner: a thin module (an interior wall) against the hardbox's inner face, the one towards the screen's middle
 *    (the room), so Dink stops at the drawn wall instead of short of a wall drawn in the middle of a thick 1997 wall top.
 */
enum class EDinkFamilyAnchor : uint8
{
	Card,
	Hardbox,
	HardboxInner,
};

namespace DinkFamilyAnchor
{
	/** Parses "card" / "hardbox" / "hardbox_inner" (false for anything else). */
	DINKCORE_API bool Parse(const FString& Text, EDinkFamilyAnchor& Out);

	/** Hardbox of a picture relative to the sprite point (engine pixels), and the picture's width and origin x; false when unknown or empty. */
	DINKCORE_API bool FrameHardbox(int32 Sequence, int32 Frame, FIntRect& OutBox, int32& OutWidth, int32& OutOriginX);

	/**
	 * Map pixel (x, y) where the mesh centre goes for a placement whose sprite point is at PlacementPx, with hardbox Box (relative)
	 * and a mesh footprint of HalfPx (half width, half depth in map pixels). False: keep the card anchor.
	 */
	DINKCORE_API bool TargetPixel(EDinkFamilyAnchor Mode, const FVector2D& PlacementPx, const FIntRect& Box, const FVector2D& HalfPx, FVector2D& OutPx);

	/**
	 * World point (ground, XY) for the mesh centre: the placement's sprite point is recovered from the card's world location
	 * (the card centre is (width / 2 - origin x) scaled picture pixels east of it, export_import_bundle.py), the hardbox is
	 * frames.csv's, MeshSizeCm the mesh's bounds after scale, Yaw its yaw relative to the screen's east (degrees).
	 */
	DINKCORE_API bool AnchorWorld(const ADinkScreenVolume& Volume, EDinkFamilyAnchor Mode, int32 Sequence, int32 Frame, const FVector& CardWorld,
		double CardWidthCm, double Yaw, const FVector& MeshSizeCm, FVector& OutWorld);

	/** Parses frames.csv text into the table FrameHardbox reads (tests; the game loads Content/Dink/Data/Gameplay/frames.csv once). */
	DINKCORE_API int32 LoadFramesCsv(const FString& Text);
}
