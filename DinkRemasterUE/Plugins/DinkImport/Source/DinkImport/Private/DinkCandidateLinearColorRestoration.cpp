#include "DinkMaterialArtLibrary.h"
#include "Engine/StaticMesh.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Misc/PackageName.h"

namespace
{
TSharedPtr<FJsonObject> ReadColorSnapshot(const FString& Text)
{
    TSharedPtr<FJsonObject> Result;
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Result);
    return Result;
}

// Detached JSON only. Compare every raw field, triangle and slot after removing
// precisely the four color columns that this correction is permitted to write.
FString NonColorSnapshot(const FString& Text)
{
    const TSharedPtr<FJsonObject> Root = ReadColorSnapshot(Text);
    if (!Root.IsValid() || !Root->GetBoolField(TEXT("valid"))) return FString();
    const TSharedPtr<FJsonObject> Raw = Root->GetObjectField(TEXT("raw"));
    TArray<TSharedPtr<FJsonValue>> Rows;
    for (const auto& Entry : Raw->GetArrayField(TEXT("instances")))
    {
        TArray<TSharedPtr<FJsonValue>> Values = Entry->AsArray();
        if (Values.Num() < 15) return FString();
        for (int32 Channel = 11; Channel < 15; ++Channel) Values[Channel] = MakeShared<FJsonValueNumber>(0.0);
        Rows.Add(MakeShared<FJsonValueArray>(Values));
    }
    Raw->SetArrayField(TEXT("instances"), Rows);
    Raw->RemoveField(TEXT("expected_built_color_rgba8")); // Derived solely from the permitted color columns.
    const TSharedRef<FJsonObject> Fields = MakeShared<FJsonObject>();
    Fields->SetObjectField(TEXT("raw"), Raw);
    Fields->SetArrayField(TEXT("slots"), Root->GetArrayField(TEXT("slots")));
    FString Result;
    FJsonSerializer::Serialize(Fields, TJsonWriterFactory<>::Create(&Result));
    return Result;
}
}

FString UDinkMaterialArtLibrary::RestoreCandidateStaticMeshLinearColors(UStaticMesh* Mesh,
    const FString& ExpectedGeometry, const TArray<int32>& InstanceIDs, const TArray<FLinearColor>& LinearColors)
{
    bool Mutated = false;
    auto Fail = [&Mutated](const TCHAR* Message)
    {
        const TSharedRef<FJsonObject> Error = MakeShared<FJsonObject>();
        Error->SetBoolField(TEXT("valid"), false);
        Error->SetStringField(TEXT("error"), Message);
        Error->SetBoolField(TEXT("mutated"), Mutated);
        Error->SetBoolField(TEXT("saved"), false);
        FString Text;
        FJsonSerializer::Serialize(Error, TJsonWriterFactory<>::Create(&Text));
        return Text;
    };
    if (!Mesh) return Fail(TEXT("null_mesh"));
    if (!Mesh->GetOutermost()->GetName().StartsWith(TEXT("/Game/Dink/Refinements/House439ClosedEavesV1/Meshes/")))
        return Fail(TEXT("outside_candidate_namespace"));
    if (Mesh->HasAnyFlags(RF_WasLoaded) || FPackageName::DoesPackageExist(Mesh->GetOutermost()->GetName()))
        return Fail(TEXT("existing_saved_candidate_refused"));
    if (Mesh->GetNumSourceModels() != 1) return Fail(TEXT("expected_one_source_lod"));
    const FString Before = InspectStaticMeshGeometry(Mesh, 0);
    if (ExpectedGeometry != Before || NonColorSnapshot(Before).IsEmpty()) return Fail(TEXT("stale_or_invalid_snapshot"));
    FMeshDescription* Description = Mesh->GetMeshDescription(0);
    if (!Description || InstanceIDs.Num() != LinearColors.Num() || InstanceIDs.Num() != Description->VertexInstances().Num())
        return Fail(TEXT("incomplete_color_rows"));
    auto Colors = FStaticMeshAttributes(*Description).GetVertexInstanceColors();
    if (!Colors.IsValid()) return Fail(TEXT("missing_color_attribute"));
    TSet<int32> Seen;
    for (int32 Index = 0; Index < InstanceIDs.Num(); ++Index)
    {
        if (Seen.Contains(InstanceIDs[Index]) || !Description->IsVertexInstanceValid(FVertexInstanceID(InstanceIDs[Index])))
            return Fail(TEXT("invalid_or_duplicate_instance"));
        Seen.Add(InstanceIDs[Index]);
        const FLinearColor& Color = LinearColors[Index];
        for (const float Value : {Color.R, Color.G, Color.B, Color.A})
            if (!FMath::IsFinite(Value) || Value < 0.f || Value > 1.f) return Fail(TEXT("invalid_linear_color"));
    }
    const auto HullsBefore = InspectStaticMeshConvexCollision(Mesh);
    Mesh->Modify();
    Mutated = true;
    for (int32 Index = 0; Index < InstanceIDs.Num(); ++Index)
    {
        const FLinearColor& Color = LinearColors[Index];
        Colors[FVertexInstanceID(InstanceIDs[Index])] = FVector4f(Color.R, Color.G, Color.B, Color.A);
    }
    Mesh->CommitMeshDescription(0);
    TArray<FText> BuildErrors;
    Mesh->Build(true, &BuildErrors);
    if (!BuildErrors.IsEmpty()) return Fail(TEXT("rebuild_failed_discard_trial"));
    const FString After = InspectStaticMeshGeometry(Mesh, 0);
    if (NonColorSnapshot(Before) != NonColorSnapshot(After)) return Fail(TEXT("noncolor_raw_field_changed_discard_trial"));
    const FMeshDescription* AfterDescription = Mesh->GetMeshDescription(0);
    if (!AfterDescription) return Fail(TEXT("missing_postbuild_description_discard_trial"));
    const auto AfterColors = FStaticMeshConstAttributes(*AfterDescription).GetVertexInstanceColors();
    for (int32 Index = 0; Index < InstanceIDs.Num(); ++Index)
    {
        const FLinearColor& Color = LinearColors[Index];
        if (AfterColors[FVertexInstanceID(InstanceIDs[Index])] != FVector4f(Color.R, Color.G, Color.B, Color.A))
            return Fail(TEXT("linear_color_postflight_differs_discard_trial"));
    }
    const auto HullsAfter = InspectStaticMeshConvexCollision(Mesh);
    if (HullsBefore.Num() != HullsAfter.Num()) return Fail(TEXT("convex_count_changed_discard_trial"));
    for (int32 Index = 0; Index < HullsBefore.Num(); ++Index)
    {
        const auto& A = HullsBefore[Index]; const auto& B = HullsAfter[Index];
        if (A.LocalVertices != B.LocalVertices || A.MeshVertices != B.MeshVertices || A.Indices != B.Indices || !A.LocalToMesh.Equals(B.LocalToMesh, 0.0))
            return Fail(TEXT("convex_shape_changed_discard_trial"));
    }
    return After; // Actual raw+built readback, not an acceptance or save signal.
}

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "UObject/Package.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCandidateLinearColorRestorationTest,
    "Dink.Art.CandidateLinearColorRestoration",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FDinkCandidateLinearColorRestorationTest::RunTest(const FString& Parameters)
{
    const auto Null = ReadColorSnapshot(UDinkMaterialArtLibrary::RestoreCandidateStaticMeshLinearColors(nullptr, FString(), {}, {}));
    if (!TestTrue(TEXT("Null refused before mutation"), Null.IsValid() && !Null->GetBoolField(TEXT("mutated")))) return false;
    const FString Name = TEXT("/Game/Dink/Refinements/House439ClosedEavesV1/Meshes/ColorFixture_") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    UStaticMesh* Mesh = NewObject<UStaticMesh>(CreatePackage(*Name), TEXT("SM_ColorFixture"), RF_Transient);
    Mesh->AddSourceModel(); Mesh->bAllowCPUAccess = true;
    Mesh->GetStaticMaterials().Add(FStaticMaterial(nullptr, TEXT("Fixture"), TEXT("Fixture")));
    FMeshDescription Description;
    FStaticMeshAttributes Attributes(Description); Attributes.Register();
    auto UV = Attributes.GetVertexInstanceUVs(); UV.SetNumChannels(2);
    const auto Group = Description.CreatePolygonGroup();
    Attributes.GetPolygonGroupMaterialSlotNames()[Group] = TEXT("Fixture");
    TArray<FVertexInstanceID> Corners;
    TArray<int32> IDs;
    for (int32 Index = 0; Index < 3; ++Index)
    {
        const auto Vertex = Description.CreateVertex();
        Attributes.GetVertexPositions()[Vertex] = FVector3f(Index == 1 ? 10.f : 0.f, Index == 2 ? 10.f : 0.f, 0.f);
        const auto Instance = Description.CreateVertexInstance(Vertex); Corners.Add(Instance); IDs.Add(Instance.GetValue());
        Attributes.GetVertexInstanceNormals()[Instance] = FVector3f(0,0,1);
        Attributes.GetVertexInstanceTangents()[Instance] = FVector3f(1,0,0);
        Attributes.GetVertexInstanceBinormalSigns()[Instance] = 1.f;
        Attributes.GetVertexInstanceColors()[Instance] = FVector4f(.033f,.133f,.319f,.8f);
        UV.Set(Instance,0,FVector2f(Index == 1 ? 1.f : 0.f,Index == 2 ? 1.f : 0.f));
        UV.Set(Instance,1,FVector2f(.3f,.7f));
    }
    Description.CreateTriangle(Group,Corners);
    // Match the ordinary imported-mesh build path and preserve semantic UV1.
    FMeshBuildSettings& Settings = Mesh->GetSourceModel(0).BuildSettings;
    Settings.bGenerateLightmapUVs=false; Settings.bRecomputeNormals=false; Settings.bRecomputeTangents=false;
    UStaticMesh::FBuildMeshDescriptionsParams Build; Build.bFastBuild=false; Build.bAllowCpuAccess=true; Build.bCommitMeshDescription=true; Build.bMarkPackageDirty=false;
    if (!TestTrue(TEXT("Ordinary color fixture build succeeds"), Mesh->BuildFromMeshDescriptions({&Description},Build))) return false;
    const FString Before = UDinkMaterialArtLibrary::InspectStaticMeshGeometry(Mesh,0);
    const auto Initial = ReadColorSnapshot(Before);
    if (!TestTrue(TEXT("Initial color fixture snapshot valid"), Initial.IsValid() && Initial->GetBoolField(TEXT("valid"))))
    {
        AddError(TEXT("Initial color fixture snapshot: ") + Before);
        return false;
    }
    const TArray<FLinearColor> Colors{FLinearColor(.2f,.4f,.6f,.8f),FLinearColor(.2f,.4f,.6f,.8f),FLinearColor(.2f,.4f,.6f,.8f)};
    const auto Stale = ReadColorSnapshot(UDinkMaterialArtLibrary::RestoreCandidateStaticMeshLinearColors(Mesh,TEXT("stale"),IDs,Colors));
    TestTrue(TEXT("Stale snapshot refused before writes"), Stale.IsValid() && !Stale->GetBoolField(TEXT("mutated")));
    const TArray<int32> Duplicate{IDs[0],IDs[0],IDs[2]};
    const auto BadIDs = ReadColorSnapshot(UDinkMaterialArtLibrary::RestoreCandidateStaticMeshLinearColors(Mesh,Before,Duplicate,Colors));
    TestTrue(TEXT("Duplicate IDs refused before writes"), BadIDs.IsValid() && !BadIDs->GetBoolField(TEXT("mutated")));
    TArray<FLinearColor> InvalidColors = Colors; InvalidColors[0].A = 1.1f;
    const auto BadColor = ReadColorSnapshot(UDinkMaterialArtLibrary::RestoreCandidateStaticMeshLinearColors(Mesh,Before,IDs,InvalidColors));
    TestTrue(TEXT("Out of range color refused before writes"), BadColor.IsValid() && !BadColor->GetBoolField(TEXT("mutated")));
    TestEqual(TEXT("Negative cases preserve complete raw+built snapshot"), UDinkMaterialArtLibrary::InspectStaticMeshGeometry(Mesh,0), Before);
    const FString After = UDinkMaterialArtLibrary::RestoreCandidateStaticMeshLinearColors(Mesh,Before,IDs,Colors);
    const auto Result = ReadColorSnapshot(After);
    if (!TestTrue(TEXT("Actual rebuilt correction valid"), Result.IsValid() && Result->GetBoolField(TEXT("valid"))))
    {
        AddError(TEXT("Actual correction response: ") + After);
        AddInfo(TEXT("Noncolor raw before: ") + NonColorSnapshot(Before));
        AddInfo(TEXT("Noncolor raw after: ") + NonColorSnapshot(UDinkMaterialArtLibrary::InspectStaticMeshGeometry(Mesh,0)));
        return false;
    }
    TestEqual(TEXT("All noncolor raw fields preserved"), NonColorSnapshot(After), NonColorSnapshot(Before));
    const auto& Row = Result->GetObjectField(TEXT("raw"))->GetArrayField(TEXT("instances"))[0]->AsArray();
    TestTrue(TEXT("Linear red restored without sRGB decode"), FMath::Abs(Row[11]->AsNumber() - .2) < 1.e-6);
    TestTrue(TEXT("Scratch mesh remains transient"), Mesh->HasAnyFlags(RF_Transient));
    return true;
}
#endif
