#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkLayout.generated.h"

/**
 * World position of one original screen: the four corners of its 600x400 map in world metres
 * (x east, y south), as solved by the data repo's tools/analyse (out/world_layout.json, the
 * "lattice rubber sheet"). Screens are convex quads, not rectangles: neighbours on one sheet share
 * corners, so the bilinear map below is continuous across their common edge.
 */
USTRUCT(BlueprintType)
struct DINKCORE_API FDinkScreenCorners
{
	GENERATED_BODY()

	/** North-west corner = map pixel (0, 0). Metres, x east, y south. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dink|Layout")
	FVector2D NW = FVector2D::ZeroVector;

	/** North-east corner = map pixel (600, 0). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dink|Layout")
	FVector2D NE = FVector2D::ZeroVector;

	/** South-west corner = map pixel (0, 400). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dink|Layout")
	FVector2D SW = FVector2D::ZeroVector;

	/** South-east corner = map pixel (600, 400). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dink|Layout")
	FVector2D SE = FVector2D::ZeroVector;

	bool operator==(const FDinkScreenCorners& O) const { return NW == O.NW && NE == O.NE && SW == O.SW && SE == O.SE; }
};

/**
 * The one place that converts original coordinates to Unreal coordinates.
 *
 *   map pixel (x, y)  ->  world metres (x east, y south)  ->  Unreal centimetres
 *
 * Map pixels: x = placement x minus the 20 px status bar (dinkex `map_x`), y as stored; one
 * screen is 600 x 400. Metres: bilinear blend of the screen's corners with u = x/600, v = y/400
 * (identical to tools/analyse/analyse/layout.py). Unreal: X = 100 * east, Y = 100 * south,
 * Z = 100 * height. Unreal is left-handed with Z up; east x south = up, so this mapping is a
 * proper rotation-free scaling, not a mirror: the original's "north is up the screen" becomes
 * -Y in Unreal, and a top-down view of the level with +X to the right reads like the original
 * map.
 */
namespace DinkLayout
{
	inline constexpr double ScreenWidthPx = 600.0;
	inline constexpr double ScreenHeightPx = 400.0;
	inline constexpr double CentimetresPerMetre = 100.0;

	/** Bilinear map of a map pixel to world metres (x east, y south). Extrapolates outside 0..600/0..400. */
	DINKCORE_API FVector2D MapPixelToMetres(const FDinkScreenCorners& Corners, double MapX, double MapY);

	/** World metres (x east, y south) plus height in metres to Unreal centimetres. */
	DINKCORE_API FVector MetresToUnreal(const FVector2D& Metres, double HeightMetres = 0.0);

	/** Inverse of MetresToUnreal for the ground plane (drops Z). */
	DINKCORE_API FVector2D UnrealToMetres(const FVector& Unreal);

	/** MapPixelToMetres followed by MetresToUnreal. */
	DINKCORE_API FVector MapPixelToUnreal(const FDinkScreenCorners& Corners, double MapX, double MapY, double HeightMetres = 0.0);

	/** Yaw (degrees, Unreal convention) of the screen's local +x (east) axis at a map pixel. */
	DINKCORE_API double LocalEastYawDegrees(const FDinkScreenCorners& Corners, double MapX, double MapY);

	/**
	 * Inverse map: world metres -> map pixel of this screen (Newton iterations on the bilinear map).
	 * Returns false if it did not converge. The result may lie outside 0..600/0..400.
	 */
	DINKCORE_API bool MetresToMapPixel(const FDinkScreenCorners& Corners, const FVector2D& Metres, double& OutMapX, double& OutMapY);

	/** True if the world point (metres) lies inside the screen quad (inclusive of the edges, with a small tolerance in pixels). */
	DINKCORE_API bool ContainsMetres(const FDinkScreenCorners& Corners, const FVector2D& Metres, double TolerancePx = 1e-6);
}

/** Blueprint access to the layout transform. */
UCLASS()
class DINKCORE_API UDinkLayoutLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Original map pixel (x without the 20 px bar, y) on a screen to an Unreal world location (cm). */
	UFUNCTION(BlueprintPure, Category = "Dink|Layout")
	static FVector MapPixelToWorld(const FDinkScreenCorners& Corners, float MapX, float MapY)
	{
		return DinkLayout::MapPixelToUnreal(Corners, MapX, MapY);
	}
};
