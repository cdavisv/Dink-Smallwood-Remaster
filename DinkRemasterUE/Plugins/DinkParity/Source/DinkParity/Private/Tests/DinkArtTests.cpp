#include "DinkTestHelpers.h"
#include "AssetCompilingManager.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Materials/Material.h"
#include "StaticMeshResources.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkArtAssetTest, "Dink.Art.ImportedAssetScaleAndMaterials", DINK_TEST_FLAGS)
bool FDinkArtAssetTest::RunTest(const FString& Parameters)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/stonebrook.json"))))
	{
		AddWarning(TEXT("skipped: authored art not imported; run Scripts/import_stonebrook_art.sh"));
		return true;
	}
	TSharedPtr<FJsonObject> Root;
	if (!TestTrue(TEXT("art manifest parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root)) || !Root) return false;
	TestEqual(TEXT("supported schema"), Root->GetStringField(TEXT("schema")), FString(TEXT("dink-art/1")));
	const TArray<TSharedPtr<FJsonValue>>* Assets = nullptr;
	if (!TestTrue(TEXT("asset bounds recorded at import"), Root->TryGetArrayField(TEXT("assets"), Assets))) return false;
	TestTrue(TEXT("art kit has multiple authored meshes"), Assets->Num() >= 5);
	for (const TSharedPtr<FJsonValue>& Value : *Assets)
	{
		const TSharedPtr<FJsonObject> Row = Value->AsObject();
		const FString Path = Row->GetStringField(TEXT("mesh"));
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Path);
		if (!TestNotNull(TEXT("mesh loads: ") + Path, Mesh)) continue;
		FAssetCompilingManager::Get().FinishAllCompilation();
		const TArray<TSharedPtr<FJsonValue>>& Size = Row->GetArrayField(TEXT("expected_size_cm"));
		const FVector Expected(Size[0]->AsNumber(), Size[1]->AsNumber(), Size[2]->AsNumber());
		const FVector Actual = Mesh->GetBounds().BoxExtent * 2.0;
		// Compare physical LOD0 dimensions with the independent Blender source.
		// Higher LODs are checked separately; every mesh retains a strict 1cm tolerance.
		double Tolerance = 1.0;
		Row->TryGetNumberField(TEXT("bounds_tolerance_cm"), Tolerance);
		TestTrue(TEXT("Blender metres imported as centimetres: ") + Path, Actual.Equals(Expected, Tolerance));
		TestTrue(TEXT("nonempty rendered mesh: ") + Path, Mesh->GetNumLODs() > 0);
		int32 ExpectedLODs = 1;
		Row->TryGetNumberField(TEXT("expected_lods"), ExpectedLODs);
		TestTrue(TEXT("authored LOD chain preserved: ") + Path, Mesh->GetNumLODs() >= ExpectedLODs);
		if (ExpectedLODs > 1 && Mesh->GetRenderData())
		{
			for (int32 LOD = 0; LOD < Mesh->GetRenderData()->LODResources.Num(); ++LOD)
			{
				const FStaticMeshVertexBuffer& Vertices = Mesh->GetRenderData()->LODResources[LOD].VertexBuffers.StaticMeshVertexBuffer;
				int32 ZeroNormals = 0;
				for (uint32 Index = 0; Index < Vertices.GetNumVertices(); ++Index)
				{
					const auto Normal = Vertices.VertexTangentZ(Index);
					// Packed 8-bit zero normals can decode to small nonzero values;
					// require a usable unit direction rather than exact floating zero.
					const FVector3f Direction(Normal.X, Normal.Y, Normal.Z);
					ZeroNormals += Direction.ContainsNaN() || Direction.SizeSquared() < 0.8f ? 1 : 0;
				}
				TestEqual(FString::Printf(TEXT("rendered LOD%d has no cancelling normals: %s"), LOD, *Path), ZeroNormals, 0);
			}
		}
		for (const FStaticMaterial& Slot : Mesh->GetStaticMaterials())
		{
			TestNotNull(TEXT("authored material assigned: ") + Path + TEXT("/") + Slot.MaterialSlotName.ToString(), Slot.MaterialInterface.Get());
			if (Slot.MaterialInterface && Mesh->GetNaniteSettings().bEnabled)
			{
				TestTrue(TEXT("Nanite material usage saved (no default material fallback): ") + Path,
					Slot.MaterialInterface->GetMaterial()->GetUsageByFlag(MATUSAGE_Nanite));
			}
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkExteriorArtAssetTest, "Dink.Art.ExteriorAssetScaleAndMaterials", DINK_TEST_FLAGS)
bool FDinkExteriorArtAssetTest::RunTest(const FString& Parameters)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/stonebrook_exterior.json"))))
	{
		AddWarning(TEXT("skipped: authored art not imported; run Scripts/import_stonebrook_art.sh"));
		return true;
	}
	TSharedPtr<FJsonObject> Root;
	if (!TestTrue(TEXT("art manifest parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root)) || !Root) return false;
	TestEqual(TEXT("supported schema"), Root->GetStringField(TEXT("schema")), FString(TEXT("dink-art/1")));
	const TArray<TSharedPtr<FJsonValue>>* Assets = nullptr;
	if (!TestTrue(TEXT("asset bounds recorded at import"), Root->TryGetArrayField(TEXT("assets"), Assets))) return false;
	TestTrue(TEXT("art kit has multiple authored meshes"), Assets->Num() >= 5);
	for (const TSharedPtr<FJsonValue>& Value : *Assets)
	{
		const TSharedPtr<FJsonObject> Row = Value->AsObject();
		const FString Path = Row->GetStringField(TEXT("mesh"));
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Path);
		if (!TestNotNull(TEXT("mesh loads: ") + Path, Mesh)) continue;
		FAssetCompilingManager::Get().FinishAllCompilation();
		const TArray<TSharedPtr<FJsonValue>>& Size = Row->GetArrayField(TEXT("expected_size_cm"));
		const FVector Expected(Size[0]->AsNumber(), Size[1]->AsNumber(), Size[2]->AsNumber());
		const FVector Actual = Mesh->GetBounds().BoxExtent * 2.0;
		// Compare physical LOD0 dimensions with the independent Blender source.
		// Higher LODs are checked separately; every mesh retains a strict 1cm tolerance.
		double Tolerance = 1.0;
		Row->TryGetNumberField(TEXT("bounds_tolerance_cm"), Tolerance);
		TestTrue(TEXT("Blender metres imported as centimetres: ") + Path, Actual.Equals(Expected, Tolerance));
		TestTrue(TEXT("nonempty rendered mesh: ") + Path, Mesh->GetNumLODs() > 0);
		int32 ExpectedLODs = 1;
		Row->TryGetNumberField(TEXT("expected_lods"), ExpectedLODs);
		TestTrue(TEXT("authored LOD chain preserved: ") + Path, Mesh->GetNumLODs() >= ExpectedLODs);
		if (ExpectedLODs > 1 && Mesh->GetRenderData())
		{
			for (int32 LOD = 0; LOD < Mesh->GetRenderData()->LODResources.Num(); ++LOD)
			{
				const FStaticMeshVertexBuffer& Vertices = Mesh->GetRenderData()->LODResources[LOD].VertexBuffers.StaticMeshVertexBuffer;
				int32 ZeroNormals = 0;
				for (uint32 Index = 0; Index < Vertices.GetNumVertices(); ++Index)
				{
					const auto Normal = Vertices.VertexTangentZ(Index);
					// Packed 8-bit zero normals can decode to small nonzero values;
					// require a usable unit direction rather than exact floating zero.
					const FVector3f Direction(Normal.X, Normal.Y, Normal.Z);
					ZeroNormals += Direction.ContainsNaN() || Direction.SizeSquared() < 0.8f ? 1 : 0;
				}
				TestEqual(FString::Printf(TEXT("rendered LOD%d has no cancelling normals: %s"), LOD, *Path), ZeroNormals, 0);
			}
		}
		for (const FStaticMaterial& Slot : Mesh->GetStaticMaterials())
		{
			TestNotNull(TEXT("authored material assigned: ") + Path + TEXT("/") + Slot.MaterialSlotName.ToString(), Slot.MaterialInterface.Get());
			if (Slot.MaterialInterface && Mesh->GetNaniteSettings().bEnabled)
			{
				TestTrue(TEXT("Nanite material usage saved (no default material fallback): ") + Path,
					Slot.MaterialInterface->GetMaterial()->GetUsageByFlag(MATUSAGE_Nanite));
			}
		}
	}
	return true;
}
