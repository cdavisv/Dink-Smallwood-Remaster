#include "DinkMaterialArtLibrary.h"
#include "EditorFramework/AssetImportData.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSourceData.h"
#include "Dom/JsonObject.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/Package.h"
#include "UObject/UnrealType.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkSourceLodInspectionTest,
    "Dink.Import.Inspection.SourceLODRecords",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDinkSourceLodInspectionTest::RunTest(const FString&)
{
    const auto Decode = [this](const FString& Json)
    {
        TSharedPtr<FJsonObject> Object;
        TestTrue(TEXT("inspection returns a JSON object"),
            FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Object) && Object.IsValid());
        return Object;
    };
    const TSharedPtr<FJsonObject> Null = Decode(UDinkMaterialArtLibrary::InspectStaticMeshSourceLods(nullptr));
    if (!Null.IsValid()) return false;
    TestEqual(TEXT("null schema"), Null->GetStringField(TEXT("schema")), FString(TEXT("dink-static-mesh-source-lods/1")));
    TestFalse(TEXT("null mesh is explicitly invalid"), Null->GetBoolField(TEXT("valid")));
    TestEqual(TEXT("null mesh has no source rows"), Null->GetArrayField(TEXT("lods")).Num(), 0);

    UPackage* Package = CreatePackage(TEXT("/Game/DinkQA/TransientSourceLodInspection"));
    UStaticMesh* Mesh = NewObject<UStaticMesh>(Package, NAME_None, RF_Transient);
    const bool bDirtyBeforeEmptyInspection = Package->IsDirty();
    const TSharedPtr<FJsonObject> Empty = Decode(UDinkMaterialArtLibrary::InspectStaticMeshSourceLods(Mesh));
    if (!Empty.IsValid()) return false;
    TestTrue(TEXT("an empty but existing mesh is valid"), Empty->GetBoolField(TEXT("valid")));
    TestEqual(TEXT("empty mesh has no invented source rows"), Empty->GetArrayField(TEXT("lods")).Num(), 0);
    TestEqual(TEXT("empty inspection preserves dirty state"), Package->IsDirty(), bDirtyBeforeEmptyInspection);

    Mesh->SetNumSourceModels(3);
    const TArray<FString> Stored = {
        FString(),
        TEXT("../../SourceAssets/Inspection/LOD1.fbx"),
        FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("BridgeProof/MetadataOnly/LOD2.fbx"))
    };
    for (int32 Index = 0; Index < Stored.Num(); ++Index)
        Mesh->GetSourceModel(Index).SourceImportFilename = Stored[Index];
    const bool bDirtyBeforeInspection = Package->IsDirty();
    const FString Json = UDinkMaterialArtLibrary::InspectStaticMeshSourceLods(Mesh);
    const TSharedPtr<FJsonObject> Record = Decode(Json);
    if (!Record.IsValid()) return false;
    TestEqual(TEXT("record identifies the actual mesh"), Record->GetStringField(TEXT("mesh")), Mesh->GetPathName());
    const TArray<TSharedPtr<FJsonValue>>& Rows = Record->GetArrayField(TEXT("lods"));
    if (!TestEqual(TEXT("all three source models are represented"), Rows.Num(), 3)) return false;
    for (int32 Index = 0; Index < Rows.Num(); ++Index)
    {
        const TSharedPtr<FJsonObject> Row = Rows[Index]->AsObject();
        if (!TestTrue(TEXT("source row object"), Row.IsValid())) return false;
        TestEqual(TEXT("row keeps the original LOD index"), Row->GetIntegerField(TEXT("lod")), Index);
        TestEqual(TEXT("stored source text remains exact"), Row->GetStringField(TEXT("stored_source")), Stored[Index]);
        const FString Expected = Stored[Index].IsEmpty() ? FString()
            : UAssetImportData::ResolveImportFilename(Stored[Index], Package);
        const FString Resolved = Row->GetStringField(TEXT("resolved_source"));
        TestEqual(TEXT("filename uses native package-relative import resolution"), Resolved, Expected);
        if (Index > 0) TestFalse(TEXT("nonempty source is resolved absolute"), FPaths::IsRelative(Resolved));
        TestEqual(TEXT("inspection does not alter source metadata"), Mesh->GetSourceModel(Index).SourceImportFilename, Stored[Index]);
    }
    TestEqual(TEXT("inspection does not alter source count"), Mesh->GetNumSourceModels(), 3);
    TestEqual(TEXT("inspection does not change package dirty state"), Package->IsDirty(), bDirtyBeforeInspection);
    TestEqual(TEXT("repeated inspection is deterministic"), UDinkMaterialArtLibrary::InspectStaticMeshSourceLods(Mesh), Json);
    // Mutating the detached result cannot mutate the native source-model metadata.
    Record->GetArrayField(TEXT("lods"))[1]->AsObject()->SetStringField(TEXT("stored_source"), TEXT("changed detached JSON"));
    TestEqual(TEXT("detached JSON is not writable native metadata"), Mesh->GetSourceModel(1).SourceImportFilename, Stored[1]);
    const UFunction* Function = UDinkMaterialArtLibrary::StaticClass()->FindFunctionByName(TEXT("InspectStaticMeshSourceLods"));
    TestTrue(TEXT("getter is reflected BlueprintPure for Python/editor inspection"),
        Function && Function->HasAnyFunctionFlags(FUNC_BlueprintPure));
    // This test creates no assets or FBX files and performs no save/build/import.
    return true;
}
#endif
