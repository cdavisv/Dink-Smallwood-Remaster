#pragma once

#include "CoreMinimal.h"

class UWorld;

/**
 * Physical-mapping audit (alpha QA, 15 Nov 2026; the owner's "make sure that the physical aspects of the game are mapped to
 * the actual objects"). Read-only. The simulation is the 1997 engine's: hardness in map pixels, the sprite hardbox of the
 * picture a sprite shows (dink.ini), hit and touch tests against that hardbox (dink.cpp run_through_tag_list /
 * run_through_touch_damage_list, ported in UDinkGameplay::RunThroughTagList / RunThroughTouchDamageList). This audit puts
 * the drawn 3D world into the same map-pixel space and compares, per placement and per live sprite:
 *  - the hardbox rectangle (what blocks, what a sword or missile hits, what a pickup or warp is touched by) with the
 *    footprint of the meshes that draw that placement (a slice of their triangles at body height, holes filled; skeletal
 *    bodies by their bounds), and with the footprint of everything drawn on the screen;
 *  - warp trigger boxes with the drawn door/exit;
 *  - where each live sprite stands with what is drawn there (NPCs and creatures inside walls or furniture);
 *  - solid and low tile hardness (code 1/3, 2) that nothing drawn covers (invisible walls that are not sprite hardboxes).
 * Rows are written by dink.PhysAudit; Scripts/summarise_phys_audit.py classifies and ranks them.
 */
namespace DinkPhysicalAudit
{
	/** Distance (px) within which a drawn footprint counts as covering a hardbox pixel and the other way round. */
	constexpr double ToleranceCm = 40.0;

	/** Overlap figures of a hardbox mask H and a footprint mask F on the same grid (cells are map pixels). */
	struct FMaskCompare
	{
		int32 HCells = 0;
		int32 FCells = 0;
		/** H cells within TolPx of an F cell / HCells: how much of the hardbox has something drawn on or next to it. */
		double Cover = 0.0;
		/** F cells farther than TolPx from every H cell / FCells: drawn body with no hardness under it. */
		double Overhang = 0.0;
		/** F cells inside H / |H union F|. */
		double IoU = 0.0;
		/** Centroid of F minus centroid of H (cells). */
		FVector2D Offset = FVector2D::ZeroVector;
		/** Largest distance (cells) of an H cell from every F cell. */
		double MaxBareDistance = 0.0;
	};

	/** Compares two masks of Size cells (row major, 0/1). Exposed for the unit test. */
	DINKNARRATIVE_API FMaskCompare Compare(const FIntPoint& Size, const TArray<uint8>& H, const TArray<uint8>& F, double TolPx);

	/** Distance (cells, 3-4 chamfer) of every cell to the nearest set cell of Mask; Big where the mask is empty. */
	DINKNARRATIVE_API void DistanceToSet(const FIntPoint& Size, const TArray<uint8>& Mask, TArray<float>& Out);

	/** Header and rows of the four files (phys_origins.csv, phys_warps.csv, phys_tiles.csv, phys_screens.csv). */
	DINKNARRATIVE_API FString OriginCsvHeader();
	DINKNARRATIVE_API FString WarpCsvHeader();
	DINKNARRATIVE_API FString TileCsvHeader();
	DINKNARRATIVE_API FString ScreenCsvHeader();

	/** Audits one screen of the loaded world (visit it first so its art is applied); appends CSV lines. False without screen or pawn. */
	DINKNARRATIVE_API bool AuditScreen(UWorld& World, int32 Screen, TArray<FString>& OutOrigins, TArray<FString>& OutWarps,
		TArray<FString>& OutTiles, FString& OutScreen, FString* OutOccupancy = nullptr);
}
