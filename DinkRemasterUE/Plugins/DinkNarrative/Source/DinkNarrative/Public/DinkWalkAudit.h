#pragma once

#include "CoreMinimal.h"

class UWorld;

/**
 * Walk-through audit (alpha QA, 14 Nov 2026; the owner's "you can walk through rocks"). For every visible static mesh of a
 * screen it compares the mesh's footprint at body height (a slice of its triangles between ground + BandLowCm and ground +
 * BandHighCm, holes filled) with where the player's capsule may stand (an overlap test with the pawn's own capsule shape,
 * channel and responses at each footprint cell, the capsule's foot above the step height). A placement whose footprint
 * holds cells where the capsule centre is allowed is one Dink can walk into; DepthCm says how far (distance from the
 * footprint's edge). The other direction: every stamped sprite hardbox (hardness code 100 + n) is compared with the union of
 * all footprints; hardbox pixels far from anything drawn are an invisible wall. Read-only: nothing in the world changes.
 */
struct DINKNARRATIVE_API FDinkWalkAuditRow
{
	int32 Screen = 0;
	FString Actor;
	FString Component;
	FString Origin;
	FString Mesh;
	/** family, family_instance, authored, environment, card, interior, other. */
	FString Kind;
	int32 Instance = INDEX_NONE;
	FVector Centre = FVector::ZeroVector;
	FVector2D CentrePx = FVector2D::ZeroVector;
	double GroundZ = 0.0;
	double CellCm = 5.0;
	int32 FootprintCells = 0;
	double FootprintM2 = 0.0;
	FVector2D SizeCm = FVector2D::ZeroVector;
	double HeightCm = 0.0;
	int32 TestedCells = 0;
	int32 AllowedCells = 0;
	/** Deepest footprint cell where the capsule centre may stand, cm from the footprint's edge (0 when none). */
	double DepthCm = 0.0;
	FVector DeepestAt = FVector::ZeroVector;
	FVector2D DeepestPx = FVector2D::ZeroVector;
	/** get_hard at the deepest allowed cell and at the footprint centre. */
	int32 HardAtDeepest = 0;
	int32 HardAtCentre = 0;
	/** Convex hull of the body-band slice in the mesh's own space (cm, before scale), and that band's local Z (player_blockers.json). */
	TArray<FVector2D> LocalHull;
	double LocalZLow = 0.0, LocalZHigh = 0.0;
	/** Material sections left out as soft (foliage: needles, leaves, moss). */
	int32 SoftSections = 0;
	/** Footprint from the mesh's bounds only (no CPU triangles). */
	bool bBoundsOnly = false;
};

/** One stamped sprite hardbox (code 100 + n) and how much of it lies away from anything drawn. */
struct DINKNARRATIVE_API FDinkWalkAuditWall
{
	int32 Screen = 0;
	int32 Placement = 0;
	int32 Pixels = 0;
	/** Hardbox pixels farther than the wall tolerance from every footprint. */
	int32 BarePixels = 0;
	double MaxDistanceCm = 0.0;
	FVector2D CentrePx = FVector2D::ZeroVector;
	FVector2D MinPx = FVector2D::ZeroVector, MaxPx = FVector2D::ZeroVector;
};

namespace DinkWalkAudit
{
	constexpr double BandLowCm = 15.0;
	constexpr double BandHighCm = 120.0;
	/** Trees (trunks) are sliced up to here: below the lowest limbs of the big pines and willows. */
	constexpr double TrunkBandHighCm = 60.0;
	/** Bare hardbox pixels: farther than this from every footprint. */
	constexpr double WallToleranceCm = 40.0;

	/** Audits one screen of the loaded world (its art must be applied: visit it first). Returns false without a screen or pawn. */
	DINKNARRATIVE_API bool AuditScreen(UWorld& World, int32 Screen, TArray<FDinkWalkAuditRow>& OutRows, TArray<FDinkWalkAuditWall>& OutWalls, TArray<FString>& OutBlockers);

	/** Run-length mask of where the capsule centre may stand without the player-only blockers (Step x Step map pixels per cell). */
	DINKNARRATIVE_API FString WalkMask(UWorld& World, int32 ScreenNumber, int32 Step);
	/** walk_mask.csv header: screen, step (map pixels per cell), mask (WalkMask). Written fresh at the start of each run. */
	DINKNARRATIVE_API FString MaskCsvHeader();
	DINKNARRATIVE_API FString RowCsvHeader();
	DINKNARRATIVE_API FString RowCsv(const FDinkWalkAuditRow& Row);
	DINKNARRATIVE_API FString WallCsvHeader();
	DINKNARRATIVE_API FString HullCsvHeader();
	DINKNARRATIVE_API FString HullCsv(const FDinkWalkAuditRow& Row);
	DINKNARRATIVE_API FString WallCsv(const FDinkWalkAuditWall& Wall);

	/**
	 * Footprint of a triangle soup (world space) in the band [ZLow, ZHigh], on a grid of CellCm cells with origin Origin and
	 * Size cells; holes enclosed by the slice are filled. Exposed for the unit test.
	 */
	DINKNARRATIVE_API void RasterSlice(const TArray<FVector>& Vertices, const TArray<uint32>& Indices, double ZLow, double ZHigh,
		const FVector2D& Origin, double CellCm, const FIntPoint& Size, TArray<uint8>& InOutCells);
	/** Convex hull (counter-clockwise, Andrew's monotone chain), reduced to at most MaxPoints by dropping the least-area vertices. */
	DINKNARRATIVE_API TArray<FVector2D> ConvexHull(TArray<FVector2D> Points, int32 MaxPoints = 16);
	DINKNARRATIVE_API void FillHoles(const FIntPoint& Size, TArray<uint8>& InOutCells);
	/** Chamfer distance (cm) of every set cell to the nearest unset cell or the grid's edge. */
	DINKNARRATIVE_API void InsideDistance(const FIntPoint& Size, double CellCm, const TArray<uint8>& Cells, TArray<float>& OutCm);
}
