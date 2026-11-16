// Dink.PhysAudit.*: the physical-mapping audit's mask comparison (DinkPhysicalAudit.h). A hardbox mask H and a drawn
// footprint mask F on one grid of map pixels: cover is how much of H has something drawn within the tolerance, overhang how
// much of F has no hardness within it, the offset is F's centroid minus H's.

#include "DinkTestHelpers.h"
#include "DinkPhysicalAudit.h"

namespace
{
	void PhysAuditFillRect(TArray<uint8>& M, const FIntPoint& Size, int32 L, int32 T, int32 R, int32 B)
	{
		for (int32 Y = T; Y <= B; ++Y)
			for (int32 X = L; X <= R; ++X)
				if (X >= 0 && Y >= 0 && X < Size.X && Y < Size.Y) M[Y * Size.X + X] = 1;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysAuditCompareTest, "Dink.PhysAudit.Compare", DINK_TEST_FLAGS)
bool FDinkPhysAuditCompareTest::RunTest(const FString& Parameters)
{
	const FIntPoint Size(100, 60);
	TArray<uint8> H, F;
	H.Init(0, Size.X * Size.Y);
	F.Init(0, Size.X * Size.Y);
	PhysAuditFillRect(H, Size, 20, 20, 39, 39);

	// the same rectangle drawn: full cover, no overhang, IoU 1, no offset
	PhysAuditFillRect(F, Size, 20, 20, 39, 39);
	DinkPhysicalAudit::FMaskCompare C = DinkPhysicalAudit::Compare(Size, H, F, 3.0);
	TestEqual(TEXT("same: cover"), C.Cover, 1.0);
	TestEqual(TEXT("same: overhang"), C.Overhang, 0.0);
	TestEqual(TEXT("same: IoU"), C.IoU, 1.0);
	TestTrue(TEXT("same: no offset"), C.Offset.IsNearlyZero(1e-6));

	// drawn 30 px to the east: the hardbox stands bare (an invisible wall), the mesh has no hardness (walk-through)
	F.Init(0, Size.X * Size.Y);
	PhysAuditFillRect(F, Size, 50, 20, 69, 39);
	C = DinkPhysicalAudit::Compare(Size, H, F, 3.0);
	TestTrue(TEXT("moved: little cover"), C.Cover < 0.2);
	TestTrue(TEXT("moved: mostly overhang"), C.Overhang > 0.8);
	TestEqual(TEXT("moved: IoU"), C.IoU, 0.0);
	TestTrue(TEXT("moved: offset +30 x"), FMath::IsNearlyEqual(C.Offset.X, 30.0, 1e-6) && FMath::IsNearlyZero(C.Offset.Y, 1e-6));
	TestTrue(TEXT("moved: farthest bare pixel ~30 px"), C.MaxBareDistance >= 29.0 && C.MaxBareDistance <= 31.0);

	// drawn as a thin card along the box's south edge: the tolerance decides the cover
	F.Init(0, Size.X * Size.Y);
	PhysAuditFillRect(F, Size, 20, 39, 39, 39);
	TestTrue(TEXT("card: small tolerance, low cover"), DinkPhysicalAudit::Compare(Size, H, F, 3.0).Cover < 0.3);
	TestEqual(TEXT("card: tolerance over the box depth, full cover"), DinkPhysicalAudit::Compare(Size, H, F, 25.0).Cover, 1.0);

	// nothing drawn: no cover, distances stay finite in the report (clamped), no offset
	F.Init(0, Size.X * Size.Y);
	C = DinkPhysicalAudit::Compare(Size, H, F, 3.0);
	TestEqual(TEXT("none: cover"), C.Cover, 0.0);
	TestEqual(TEXT("none: F cells"), C.FCells, 0);
	TestTrue(TEXT("none: max bare distance clamped"), C.MaxBareDistance <= 9999.0);
	return true;
}

