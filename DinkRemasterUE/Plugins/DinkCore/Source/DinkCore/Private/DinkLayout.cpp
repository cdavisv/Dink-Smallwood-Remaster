#include "DinkLayout.h"

namespace DinkLayout
{
	FVector2D MapPixelToMetres(const FDinkScreenCorners& C, double MapX, double MapY)
	{
		// tools/analyse/analyse/layout.py: P = (1-u)(1-v)nw + u(1-v)ne + (1-u)v sw + uv se
		const double U = MapX / ScreenWidthPx;
		const double V = MapY / ScreenHeightPx;
		return C.NW * ((1.0 - U) * (1.0 - V)) + C.NE * (U * (1.0 - V)) + C.SW * ((1.0 - U) * V) + C.SE * (U * V);
	}

	FVector MetresToUnreal(const FVector2D& Metres, double HeightMetres)
	{
		return FVector(Metres.X * CentimetresPerMetre, Metres.Y * CentimetresPerMetre, HeightMetres * CentimetresPerMetre);
	}

	FVector2D UnrealToMetres(const FVector& Unreal)
	{
		return FVector2D(Unreal.X / CentimetresPerMetre, Unreal.Y / CentimetresPerMetre);
	}

	FVector MapPixelToUnreal(const FDinkScreenCorners& Corners, double MapX, double MapY, double HeightMetres)
	{
		return MetresToUnreal(MapPixelToMetres(Corners, MapX, MapY), HeightMetres);
	}

	/** d P / d x and d P / d y (metres per map pixel) at a map pixel. */
	static void Jacobian(const FDinkScreenCorners& C, double MapX, double MapY, FVector2D& DX, FVector2D& DY)
	{
		const double U = MapX / ScreenWidthPx;
		const double V = MapY / ScreenHeightPx;
		DX = ((C.NE - C.NW) * (1.0 - V) + (C.SE - C.SW) * V) / ScreenWidthPx;
		DY = ((C.SW - C.NW) * (1.0 - U) + (C.SE - C.NE) * U) / ScreenHeightPx;
	}

	double LocalEastYawDegrees(const FDinkScreenCorners& Corners, double MapX, double MapY)
	{
		FVector2D DX, DY;
		Jacobian(Corners, MapX, MapY, DX, DY);
		// metres x east / y south map straight onto Unreal X / Y, so the Unreal yaw is atan2(y, x)
		return FMath::RadiansToDegrees(FMath::Atan2(DX.Y, DX.X));
	}

	bool MetresToMapPixel(const FDinkScreenCorners& Corners, const FVector2D& Metres, double& OutMapX, double& OutMapY)
	{
		double X = ScreenWidthPx * 0.5;
		double Y = ScreenHeightPx * 0.5;
		for (int32 Iter = 0; Iter < 50; ++Iter)
		{
			const FVector2D R = MapPixelToMetres(Corners, X, Y) - Metres;
			if (R.SizeSquared() < 1e-18)
			{
				break;
			}
			FVector2D DX, DY;
			Jacobian(Corners, X, Y, DX, DY);
			const double Det = DX.X * DY.Y - DX.Y * DY.X;
			if (FMath::Abs(Det) < 1e-18)
			{
				return false;
			}
			// solve J * d = R
			X -= (R.X * DY.Y - R.Y * DY.X) / Det;
			Y -= (DX.X * R.Y - DX.Y * R.X) / Det;
		}
		OutMapX = X;
		OutMapY = Y;
		return (MapPixelToMetres(Corners, X, Y) - Metres).Size() < 1e-6;
	}

	bool ContainsMetres(const FDinkScreenCorners& Corners, const FVector2D& Metres, double TolerancePx)
	{
		double X = 0.0, Y = 0.0;
		if (!MetresToMapPixel(Corners, Metres, X, Y))
		{
			return false;
		}
		return X >= -TolerancePx && X <= ScreenWidthPx + TolerancePx && Y >= -TolerancePx && Y <= ScreenHeightPx + TolerancePx;
	}
}
