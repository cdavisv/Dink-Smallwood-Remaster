// Dink.WalkAudit.*: the walk-through audit's footprint raster (DinkWalkAudit.h). A closed vertical shell (a trunk, a boulder's
// sides) slices to a ring, which the hole fill turns into the solid cross-section; the inside distance measures how deep a
// cell lies; the band ignores what is above head height or below the ankle.

#include "DinkTestHelpers.h"
#include "DinkWalkAudit.h"

namespace
{
	// an open-ended vertical prism (N sides, radius R, Z0..Z1) around (CX, CY): walls only, like a trunk's bark
	void Prism(TArray<FVector>& V, TArray<uint32>& I, double CX, double CY, double R, double Z0, double Z1, int32 N = 24)
	{
		const uint32 Base = V.Num();
		for (int32 K = 0; K < N; ++K)
		{
			const double A = 2.0 * PI * K / N;
			V.Add(FVector(CX + R * FMath::Cos(A), CY + R * FMath::Sin(A), Z0));
			V.Add(FVector(CX + R * FMath::Cos(A), CY + R * FMath::Sin(A), Z1));
		}
		for (int32 K = 0; K < N; ++K)
		{
			const uint32 A0 = Base + 2 * K, A1 = A0 + 1, B0 = Base + 2 * ((K + 1) % N), B1 = B0 + 1;
			I.Append({ A0, B0, A1, A1, B0, B1 });
		}
	}
	int32 Count(const TArray<uint8>& C) { int32 N = 0; for (uint8 X : C) N += X; return N; }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWalkAuditRasterTest, "Dink.WalkAudit.FootprintRaster", DINK_TEST_FLAGS)
bool FDinkWalkAuditRasterTest::RunTest(const FString& Parameters)
{
	const FVector2D Origin(-100.0, -100.0);
	const FIntPoint Size(40, 40); // 5 cm cells over 2 m
	TArray<FVector> V;
	TArray<uint32> I;
	Prism(V, I, 0.0, 0.0, 50.0, 0.0, 200.0);
	TArray<uint8> Cells;
	DinkWalkAudit::RasterSlice(V, I, 15.0, 120.0, Origin, 5.0, Size, Cells);
	const int32 Ring = Count(Cells);
	TestTrue(TEXT("a vertical shell slices to a thin ring"), Ring > 40 && Ring < 200);
	DinkWalkAudit::FillHoles(Size, Cells);
	const double Area = Count(Cells) * 25.0;
	TestTrue(FString::Printf(TEXT("hole fill gives the 50 cm disc (%.0f cm2, disc %.0f)"), Area, PI * 2500.0), FMath::Abs(Area - PI * 2500.0) < 0.2 * PI * 2500.0);
	TArray<float> Depth;
	DinkWalkAudit::InsideDistance(Size, 5.0, Cells, Depth);
	const float Centre = Depth[20 * Size.X + 20];
	TestTrue(FString::Printf(TEXT("centre lies ~50 cm inside (%.1f)"), Centre), Centre > 40.f && Centre < 60.f);

	// a canopy (above the band) and a pebble (under it) leave nothing
	TArray<FVector> V2;
	TArray<uint32> I2;
	Prism(V2, I2, 0.0, 0.0, 80.0, 200.0, 400.0);
	Prism(V2, I2, 30.0, 30.0, 10.0, 0.0, 10.0);
	DinkWalkAudit::RasterSlice(V2, I2, 15.0, 120.0, Origin, 5.0, Size, Cells);
	TestEqual(TEXT("canopy and pebble are outside the body band"), Count(Cells), 0);

	// a sloped triangle (a rock's flank) fills its projection
	TArray<FVector> V3 = { FVector(-50, -50, 20), FVector(50, -50, 20), FVector(-50, 50, 100) };
	TArray<uint32> I3 = { 0, 1, 2 };
	DinkWalkAudit::RasterSlice(V3, I3, 15.0, 120.0, Origin, 5.0, Size, Cells);
	const double TriArea = Count(Cells) * 25.0;
	TestTrue(FString::Printf(TEXT("sloped triangle fills its projection (%.0f cm2 of 5000)"), TriArea), TriArea > 4000.0 && TriArea < 6500.0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWalkAuditHullTest, "Dink.WalkAudit.ConvexHull", DINK_TEST_FLAGS)
bool FDinkWalkAuditHullTest::RunTest(const FString& Parameters)
{
	TArray<FVector2D> P;
	for (int32 K = 0; K < 64; ++K) P.Add(FVector2D(FMath::Cos(K * PI / 32.0) * 50.0, FMath::Sin(K * PI / 32.0) * 30.0));
	P.Add(FVector2D(0, 0)); P.Add(FVector2D(10, 5));
	const TArray<FVector2D> H = DinkWalkAudit::ConvexHull(P, 16);
	TestEqual(TEXT("reduced to 16 points"), H.Num(), 16);
	double Area = 0.0;
	for (int32 I = 0; I < H.Num(); ++I) Area += FVector2D::CrossProduct(H[I], H[(I + 1) % H.Num()]) * 0.5;
	TestTrue(FString::Printf(TEXT("counter-clockwise, close to the ellipse's area (%.0f of %.0f)"), Area, PI * 1500.0), Area > 0.9 * PI * 1500.0 && Area <= PI * 1500.0 + 1.0);
	return true;
}
