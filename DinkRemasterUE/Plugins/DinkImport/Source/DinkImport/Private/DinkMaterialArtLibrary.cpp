#include "DinkMaterialArtLibrary.h"
#include "Materials/Material.h"
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/BodySetup.h"

TArray<int32> UDinkMaterialArtLibrary::GetConnectedMaterialProperties(UMaterial* Material)
{
	TArray<int32> Connected;
	if (!Material) return Connected;
	for (int32 Index = 0; Index < MP_MAX; ++Index)
	{
		const FExpressionInput* Input = Material->GetExpressionInputForProperty(static_cast<EMaterialProperty>(Index));
		if (Input && Input->Expression) Connected.Add(Index);
	}
	return Connected;
}

TArray<FDinkConvexArtSnapshot> UDinkMaterialArtLibrary::InspectStaticMeshConvexCollision(UStaticMesh* Mesh)
{
	TArray<FDinkConvexArtSnapshot> Result;
	const UBodySetup* Body = Mesh ? Mesh->GetBodySetup() : nullptr;
	if (!Body) return Result;
	Result.Reserve(Body->AggGeom.ConvexElems.Num());
	for (const FKConvexElem& Hull : Body->AggGeom.ConvexElems)
	{
		FDinkConvexArtSnapshot Snapshot;
		Snapshot.LocalToMesh = Hull.GetTransform();
		Snapshot.LocalVertices = Hull.VertexData;
		Snapshot.Indices = Hull.IndexData;
		Snapshot.MeshVertices.Reserve(Hull.VertexData.Num());
		for (const FVector& Vertex : Hull.VertexData)
		{
			Snapshot.MeshVertices.Add(Snapshot.LocalToMesh.TransformPosition(Vertex));
		}
		Result.Add(MoveTemp(Snapshot));
	}
	return Result;
}

#if WITH_DEV_AUTOMATION_TESTS
#include "Materials/MaterialExpressionConstant3Vector.h"
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkMaterialPropertyInspectionTest,
	"Dink.Art.MaterialPropertyInspection", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FDinkMaterialPropertyInspectionTest::RunTest(const FString& Parameters)
{
	UMaterial* Material = NewObject<UMaterial>();
	UMaterialExpressionConstant3Vector* Node = NewObject<UMaterialExpressionConstant3Vector>(Material);
	TestTrue(TEXT("empty graph has no connected properties"),
		UDinkMaterialArtLibrary::GetConnectedMaterialProperties(Material).IsEmpty());
	const TArray<EMaterialProperty> Properties = {MP_BaseColor, MP_EmissiveColor, MP_WorldPositionOffset,
		MP_CustomizedUVs0, MP_CustomizedUVs7, MP_Displacement, MP_PixelDepthOffset};
	TArray<int32> Expected;
	for (EMaterialProperty Property : Properties)
	{
		FExpressionInput* Input = Material->GetExpressionInputForProperty(Property);
		if (!TestNotNull(TEXT("supported material input exists"), Input)) return false;
		Input->Expression = Node;
		Input->OutputIndex = 0;
		Expected.Add(static_cast<int32>(Property));
	}
	Expected.Sort();
	TestTrue(TEXT("includes reused nodes on displacement and hidden UV pins"),
		UDinkMaterialArtLibrary::GetConnectedMaterialProperties(Material) == Expected);
	for (EMaterialProperty Property : Properties)
	{
		FExpressionInput* Input = Material->GetExpressionInputForProperty(Property);
		TestTrue(TEXT("inspection preserves the original connection"), Input->Expression == Node && Input->OutputIndex == 0);
	}
	TestTrue(TEXT("null material is handled without a dereference"),
		UDinkMaterialArtLibrary::GetConnectedMaterialProperties(nullptr).IsEmpty());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkConvexArtInspectionTest,
	"Dink.Art.ConvexTransformInspection", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FDinkConvexArtInspectionTest::RunTest(const FString& Parameters)
{
	TestTrue(TEXT("null mesh returns no snapshots"),
		UDinkMaterialArtLibrary::InspectStaticMeshConvexCollision(nullptr).IsEmpty());
	UStaticMesh* Mesh = NewObject<UStaticMesh>();
	TestTrue(TEXT("bodyless mesh returns no snapshots"),
		UDinkMaterialArtLibrary::InspectStaticMeshConvexCollision(Mesh).IsEmpty());
	TestNull(TEXT("inspection never creates a body"), Mesh->GetBodySetup());
	Mesh->CreateBodySetup();
	UBodySetup* Body = Mesh->GetBodySetup();
	FKConvexElem Hull;
	Hull.VertexData = {FVector(0, 0, 0), FVector(2, 0, 0), FVector(0, 3, 0), FVector(0, 0, 4)};
	Hull.IndexData = {0, 2, 1, 0, 1, 3, 0, 3, 2, 1, 2, 3};
	const FTransform Transform(FRotator(19, 37, -11), FVector(23, -17, 41), FVector(1.5, .7, 2.1));
	Hull.SetTransform(Transform);
	Body->AggGeom.ConvexElems.Add(Hull);
	const bool bMeshDirty = Mesh->GetOutermost()->IsDirty();
	const bool bBodyDirty = Body->GetOutermost()->IsDirty();
	TArray<FDinkConvexArtSnapshot> Snapshots = UDinkMaterialArtLibrary::InspectStaticMeshConvexCollision(Mesh);
	if (!TestEqual(TEXT("one snapshot per authored hull"), Snapshots.Num(), 1)) return false;
	TestTrue(TEXT("actual nonidentity transform retained"), Snapshots[0].LocalToMesh.Equals(Transform));
	TestTrue(TEXT("local vertices retained"), Snapshots[0].LocalVertices == Hull.VertexData);
	TestTrue(TEXT("actual face indices retained"), Snapshots[0].Indices == Hull.IndexData);
	for (int32 Index = 0; Index < Hull.VertexData.Num(); ++Index)
	{
		TestTrue(TEXT("mesh-space vertex includes translation rotation and nonuniform scale"),
			Snapshots[0].MeshVertices[Index].Equals(Transform.TransformPosition(Hull.VertexData[Index]), 1.e-6));
	}
	Snapshots[0].LocalVertices[0] = FVector(999);
	Snapshots[0].Indices.Reset();
	const FKConvexElem& After = Body->AggGeom.ConvexElems[0];
	TestTrue(TEXT("snapshot mutation never changes body vertices"), After.VertexData == Hull.VertexData);
	TestTrue(TEXT("snapshot mutation never changes body indices"), After.IndexData == Hull.IndexData);
	TestTrue(TEXT("inspection never changes body transform"), After.GetTransform().Equals(Transform));
	TestEqual(TEXT("mesh dirty state preserved"), Mesh->GetOutermost()->IsDirty(), bMeshDirty);
	TestEqual(TEXT("body dirty state preserved"), Body->GetOutermost()->IsDirty(), bBodyDirty);
	return true;
}
#endif
