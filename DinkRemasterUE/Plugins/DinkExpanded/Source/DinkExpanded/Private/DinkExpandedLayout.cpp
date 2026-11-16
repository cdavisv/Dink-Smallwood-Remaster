#include "DinkExpanded.h"

namespace
{
	/** Plan defaults (REMASTER_PLAN section 3 and tools/analyse regions.toml at 0.025 m/px), used only when no screen of the kind is loaded. */
	FVector2D DefaultSize(FName Kind)
	{
		const double Base = 0.025;
		double K = 2.75;
		if (Kind == TEXT("settlement"))
		{
			K = 4.0;
		}
		else if (Kind == TEXT("dungeon"))
		{
			K = 2.25;
		}
		else if (Kind == TEXT("interior"))
		{
			K = 1.75;
		}
		return FVector2D(600.0 * Base * K, 400.0 * Base * K);
	}

	double Median(TArray<double>& V)
	{
		V.Sort();
		const int32 N = V.Num();
		return N % 2 ? V[N / 2] : 0.5 * (V[N / 2 - 1] + V[N / 2]);
	}

	void Extend(FBox2D& Box, const FDinkScreenCorners& C)
	{
		Box += C.NW;
		Box += C.NE;
		Box += C.SW;
		Box += C.SE;
	}
}

namespace DinkExpanded
{
	FVector2D MedianScreenSize(const TArray<FBaseScreen>& Base, FName Kind)
	{
		TArray<double> W;
		TArray<double> H;
		for (const FBaseScreen& S : Base)
		{
			if (S.Kind == Kind)
			{
				W.Add(0.5 * (FVector2D::Distance(S.Corners.NW, S.Corners.NE) + FVector2D::Distance(S.Corners.SW, S.Corners.SE)));
				H.Add(0.5 * (FVector2D::Distance(S.Corners.NW, S.Corners.SW) + FVector2D::Distance(S.Corners.NE, S.Corners.SE)));
			}
		}
		return W.Num() > 0 ? FVector2D(Median(W), Median(H)) : DefaultSize(Kind);
	}

	TMap<int32, FDinkScreenCorners> LayoutPackScreens(const TArray<FBaseScreen>& Base, const FDinkExpandedRegistry& Registry)
	{
		TMap<int32, FDinkScreenCorners> Out;
		FBox2D Occupied(ForceInit);
		for (const FBaseScreen& S : Base)
		{
			Extend(Occupied, S.Corners);
		}
		if (!Occupied.bIsValid)
		{
			Occupied = FBox2D(FVector2D::ZeroVector, FVector2D::ZeroVector);
		}
		for (const FDinkPack& Pack : Registry.Packs)
		{
			for (const FDinkPackSheet& Sheet : Pack.Sheets)
			{
				const FVector2D Cell = MedianScreenSize(Base, Sheet.Kind);
				FIntPoint Extent(0, 0);
				for (const FDinkPackScreen& S : Pack.Screens)
				{
					if (S.Sheet == Sheet.Id)
					{
						Extent.X = FMath::Max(Extent.X, S.Grid.X + 1);
						Extent.Y = FMath::Max(Extent.Y, S.Grid.Y + 1);
					}
				}
				if (Extent.X == 0)
				{
					continue;
				}
				const FVector2D Size(Extent.X * Cell.X, Extent.Y * Cell.Y);
				// Push the sheet's box from the centre of everything placed so far along its direction until it is GapM clear of it.
				const FVector2D Dir = Sheet.Direction.IsNearlyZero() ? FVector2D(-1.0, 0.0) : Sheet.Direction.GetSafeNormal();
				const FBox2D Keep = Occupied.ExpandBy(Sheet.GapM);
				const FVector2D Start = Occupied.GetCenter();
				double Lo = 0.0;
				double Hi = 1.0;
				auto Clear = [&](double T)
				{
					const FVector2D C = Start + Dir * T;
					return !FBox2D(C - Size * 0.5, C + Size * 0.5).Intersect(Keep);
				};
				while (!Clear(Hi))
				{
					Hi *= 2.0;
				}
				for (int32 i = 0; i < 60; ++i)
				{
					const double Mid = 0.5 * (Lo + Hi);
					(Clear(Mid) ? Hi : Lo) = Mid;
				}
				const FVector2D NW = Start + Dir * Hi - Size * 0.5;
				for (const FDinkPackScreen& S : Pack.Screens)
				{
					if (S.Sheet != Sheet.Id)
					{
						continue;
					}
					FDinkScreenCorners C;
					C.NW = NW + FVector2D(S.Grid.X * Cell.X, S.Grid.Y * Cell.Y);
					C.NE = C.NW + FVector2D(Cell.X, 0.0);
					C.SW = C.NW + FVector2D(0.0, Cell.Y);
					C.SE = C.NW + Cell;
					Out.Add(S.Screen, C);
				}
				Occupied += FBox2D(NW, NW + Size);
			}
		}
		return Out;
	}
}
