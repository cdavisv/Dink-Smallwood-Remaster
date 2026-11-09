#include "DinkMaterialArtLibrary.h"
#include "Materials/Material.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSourceData.h"
#include "EditorFramework/AssetImportData.h"
#include "PhysicsEngine/BodySetup.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

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

FString UDinkMaterialArtLibrary::InspectStaticMeshMaterialBindings(UStaticMesh* Mesh, int32 LODIndex)
{
	TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetStringField(TEXT("schema"), TEXT("dink-static-mesh-material-bindings/1"));
	Root->SetBoolField(TEXT("valid"), false);
	Root->SetNumberField(TEXT("lod"), LODIndex);
	auto Finish = [&Root](const TCHAR* Error = nullptr)
	{
		if (Error) Root->SetStringField(TEXT("error"), Error);
		FString Result;
		FJsonSerializer::Serialize(Root, TJsonWriterFactory<>::Create(&Result));
		return Result;
	};
	if (!Mesh) return Finish(TEXT("null_mesh"));
	Root->SetStringField(TEXT("mesh"), Mesh->GetPathName());
	if (LODIndex < 0 || LODIndex >= Mesh->GetNumSourceModels()) return Finish(TEXT("invalid_lod"));
	const FMeshDescription* Description = Mesh->GetMeshDescription(LODIndex);
	if (!Description || Description->Triangles().Num() == 0) return Finish(TEXT("missing_geometry"));
	const FStaticMeshConstAttributes Attributes(*Description);
	const auto Names = Attributes.GetPolygonGroupMaterialSlotNames();
	if (!Names.IsValid()) return Finish(TEXT("missing_imported_slot_attribute"));

	TMap<FName, int32> ImportedToSlot;
	TArray<TSharedPtr<FJsonValue>> Slots;
	const TArray<FStaticMaterial>& Materials = Mesh->GetStaticMaterials();
	for (int32 Index = 0; Index < Materials.Num(); ++Index)
	{
		const FStaticMaterial& Material = Materials[Index];
		if (Material.ImportedMaterialSlotName.IsNone()) return Finish(TEXT("unnamed_imported_slot"));
		if (ImportedToSlot.Contains(Material.ImportedMaterialSlotName)) return Finish(TEXT("ambiguous_imported_slot"));
		ImportedToSlot.Add(Material.ImportedMaterialSlotName, Index);
		TSharedRef<FJsonObject> Slot = MakeShared<FJsonObject>();
		Slot->SetNumberField(TEXT("slot_index"), Index);
		Slot->SetStringField(TEXT("slot_name"), Material.MaterialSlotName.ToString());
		Slot->SetStringField(TEXT("imported_slot_name"), Material.ImportedMaterialSlotName.ToString());
		Slots.Add(MakeShared<FJsonValueObject>(Slot));
	}
	TMap<int32, int32> GroupToSlot;
	TArray<TSharedPtr<FJsonValue>> Groups;
	for (const FPolygonGroupID Group : Description->PolygonGroups().GetElementIDs())
	{
		const FName ImportedName = Names[Group];
		const int32* SlotIndex = ImportedToSlot.Find(ImportedName);
		if (ImportedName.IsNone() || !SlotIndex) return Finish(TEXT("unresolved_polygon_group_slot"));
		GroupToSlot.Add(Group.GetValue(), *SlotIndex);
		TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
		Row->SetNumberField(TEXT("polygon_group_id"), Group.GetValue());
		Row->SetStringField(TEXT("imported_slot_name"), ImportedName.ToString());
		Row->SetNumberField(TEXT("slot_index"), *SlotIndex);
		Groups.Add(MakeShared<FJsonValueObject>(Row));
	}
	TArray<TSharedPtr<FJsonValue>> Triangles;
	Triangles.Reserve(Description->Triangles().Num());
	for (const FTriangleID Triangle : Description->Triangles().GetElementIDs())
	{
		const FPolygonGroupID Group = Description->GetTrianglePolygonGroup(Triangle);
		const int32* SlotIndex = GroupToSlot.Find(Group.GetValue());
		if (!SlotIndex) return Finish(TEXT("unresolved_triangle_group"));
		TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
		Row->SetNumberField(TEXT("triangle_id"), Triangle.GetValue());
		Row->SetNumberField(TEXT("polygon_group_id"), Group.GetValue());
		Row->SetNumberField(TEXT("slot_index"), *SlotIndex);
		Triangles.Add(MakeShared<FJsonValueObject>(Row));
	}
	Root->SetArrayField(TEXT("slots"), Slots);
	Root->SetArrayField(TEXT("groups"), Groups);
	Root->SetArrayField(TEXT("triangles"), Triangles);
	Root->SetBoolField(TEXT("valid"), true);
	return Finish();
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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkMaterialSlotBindingInspectionTest,
	"Dink.Art.MaterialSlotBindingInspection", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FDinkMaterialSlotBindingInspectionTest::RunTest(const FString& Parameters)
{
	auto Parse = [this](const FString& Text)
	{
		TSharedPtr<FJsonObject> Result;
		TestTrue(TEXT("inspection returns JSON"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Result));
		return Result;
	};
	const auto NullResult = Parse(UDinkMaterialArtLibrary::InspectStaticMeshMaterialBindings(nullptr));
	if (!NullResult) return false;
	TestFalse(TEXT("null mesh is refused"), NullResult->GetBoolField(TEXT("valid")));
	UStaticMesh* Mesh = NewObject<UStaticMesh>();
	Mesh->AddSourceModel();
	Mesh->GetStaticMaterials().Add(FStaticMaterial(nullptr, TEXT("RenamedPublicA"), TEXT("ImportedA")));
	Mesh->GetStaticMaterials().Add(FStaticMaterial(nullptr, TEXT("RenamedPublicB"), TEXT("ImportedB")));
	FMeshDescription* Description = Mesh->CreateMeshDescription(0);
	if (!TestNotNull(TEXT("fixture description"), Description)) return false;
	FStaticMeshAttributes Attributes(*Description);
	Attributes.Register();
	const FPolygonGroupID First = Description->CreatePolygonGroup();
	const FPolygonGroupID Gap = Description->CreatePolygonGroup();
	const FPolygonGroupID Last = Description->CreatePolygonGroup();
	Description->DeletePolygonGroup(Gap);
	auto Names = Attributes.GetPolygonGroupMaterialSlotNames();
	Names[First] = TEXT("ImportedB");
	Names[Last] = TEXT("ImportedA");
	auto Positions = Attributes.GetVertexPositions();
	for (int32 Triangle = 0; Triangle < 2; ++Triangle)
	{
		TArray<FVertexInstanceID> Corners;
		for (int32 Corner = 0; Corner < 3; ++Corner)
		{
			const FVertexID Vertex = Description->CreateVertex();
			Positions[Vertex] = FVector3f(float(Triangle * 10 + (Corner == 1)), float(Corner == 2), 0);
			Corners.Add(Description->CreateVertexInstance(Vertex));
		}
		Description->CreateTriangle(Triangle == 0 ? First : Last, Corners);
	}
	const bool DirtyBefore = Mesh->GetOutermost()->IsDirty();
	const FString Before = UDinkMaterialArtLibrary::InspectStaticMeshMaterialBindings(Mesh);
	const auto Result = Parse(Before);
	if (!Result || !TestTrue(TEXT("named fixture is valid"), Result->GetBoolField(TEXT("valid")))) return false;
	const auto& Triangles = Result->GetArrayField(TEXT("triangles"));
	if (!TestEqual(TEXT("both triangles inspected"), Triangles.Num(), 2)) return false;
	TestEqual(TEXT("group zero resolves to slot one, not group index"),
		Triangles[0]->AsObject()->GetNumberField(TEXT("slot_index")), 1.0);
	TestEqual(TEXT("sparse group resolves to slot zero"),
		Triangles[1]->AsObject()->GetNumberField(TEXT("slot_index")), 0.0);
	TestEqual(TEXT("actual sparse group ID retained"),
		Triangles[1]->AsObject()->GetNumberField(TEXT("polygon_group_id")), double(Last.GetValue()));
	TestEqual(TEXT("source imported names unchanged"), Names[First], FName(TEXT("ImportedB")));
	Triangles[0]->AsObject()->SetNumberField(TEXT("slot_index"), 999);
	TestEqual(TEXT("detached JSON edits do not change the source"),
		UDinkMaterialArtLibrary::InspectStaticMeshMaterialBindings(Mesh), Before);
	TestEqual(TEXT("inspection preserves dirty state"), Mesh->GetOutermost()->IsDirty(), DirtyBefore);
	Names[First] = TEXT("NoSuchImportedSlot");
	const auto Unresolved = Parse(UDinkMaterialArtLibrary::InspectStaticMeshMaterialBindings(Mesh));
	if (!Unresolved) return false;
	TestFalse(TEXT("unknown name never falls back to a dense index"), Unresolved->GetBoolField(TEXT("valid")));
	Names[First] = TEXT("ImportedB");
	Mesh->GetStaticMaterials()[1].ImportedMaterialSlotName = TEXT("ImportedA");
	const auto Ambiguous = Parse(UDinkMaterialArtLibrary::InspectStaticMeshMaterialBindings(Mesh));
	if (!Ambiguous) return false;
	TestFalse(TEXT("ambiguous imported names are refused"), Ambiguous->GetBoolField(TEXT("valid")));
	Mesh->GetStaticMaterials()[1].ImportedMaterialSlotName = TEXT("ImportedB");
	Description->PolygonGroupAttributes().UnregisterAttribute(MeshAttribute::PolygonGroup::ImportedMaterialSlotName);
	const auto Missing = Parse(UDinkMaterialArtLibrary::InspectStaticMeshMaterialBindings(Mesh));
	if (!Missing) return false;
	TestFalse(TEXT("missing attribute is not created by inspection"), Missing->GetBoolField(TEXT("valid")));
	TestFalse(TEXT("inspection leaves the missing attribute absent"),
		FStaticMeshConstAttributes(*Description).GetPolygonGroupMaterialSlotNames().IsValid());
	const auto BadLOD = Parse(UDinkMaterialArtLibrary::InspectStaticMeshMaterialBindings(Mesh, 1));
	if (!BadLOD) return false;
	TestFalse(TEXT("invalid LOD is refused before description access"), BadLOD->GetBoolField(TEXT("valid")));
	return true;
}
#endif

FString UDinkMaterialArtLibrary::InspectStaticMeshSourceLods(UStaticMesh* Mesh)
{
    TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("schema"), TEXT("dink-static-mesh-source-lods/1"));
    Root->SetBoolField(TEXT("valid"), Mesh != nullptr);
    TArray<TSharedPtr<FJsonValue>> Rows;
    if (Mesh)
    {
        Root->SetStringField(TEXT("mesh"), Mesh->GetPathName());
        for (int32 Index = 0; Index < Mesh->GetNumSourceModels(); ++Index)
        {
            const FStaticMeshSourceModel& Source = Mesh->GetSourceModel(Index);
            TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
            Row->SetNumberField(TEXT("lod"), Index);
            Row->SetStringField(TEXT("stored_source"), Source.SourceImportFilename);
            Row->SetStringField(TEXT("resolved_source"), Source.SourceImportFilename.IsEmpty()
                ? FString() : UAssetImportData::ResolveImportFilename(Source.SourceImportFilename, Mesh->GetOutermost()));
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
    }
    Root->SetArrayField(TEXT("lods"), Rows);
    FString Result;
    FJsonSerializer::Serialize(Root, TJsonWriterFactory<>::Create(&Result));
    return Result;
}
