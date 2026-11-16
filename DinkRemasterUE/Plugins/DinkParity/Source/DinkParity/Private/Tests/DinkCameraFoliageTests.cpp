// Foliage between the play camera and Dink (15 Nov 2026): the crown model and the fade variants the camera uses.
#include "DinkTestHelpers.h"
#include "DinkCameraFoliage.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCameraFoliageGeometryTest, "Dink.Art.CameraFoliage.Geometry", DINK_TEST_FLAGS)
bool FDinkCameraFoliageGeometryTest::RunTest(const FString&)
{
    using namespace DinkCameraFoliage;
    // A pine of 8 x 8 x 18 m standing at (1000, 0) on the ground, its pivot at the foot of the trunk.
    const FBox Pine(FVector(-400, -400, 0), FVector(400, 400, 1800));
    FCrown Crown;
    TestTrue(TEXT("a tree has a crown"), CrownFromBounds(Pine, FTransform(FVector(1000, 0, 0)), Crown));
    TestTrue(TEXT("crown axis at the trunk"), Crown.Axis.Equals(FVector2D(1000, 0), 1.e-6));
    TestEqual(TEXT("crown radius is the share of the half extent"), Crown.Radius, 400.0 * RadiusShare, 1.e-6);
    TestEqual(TEXT("crown from the ground"), Crown.Bottom, 0.0, 1.e-6);
    TestEqual(TEXT("crown to the top"), Crown.Top, 1800.0, 1.e-6);
    FCrown Scaled;
    TestTrue(TEXT("instance scale counts"), CrownFromBounds(Pine, FTransform(FQuat::Identity, FVector(0, 0, 0), FVector(1.2)), Scaled));
    TestEqual(TEXT("scaled radius"), Scaled.Radius, 480.0 * RadiusShare, 1.e-6);
    FCrown Grass;
    TestFalse(TEXT("grass and ferns never fade"), CrownFromBounds(FBox(FVector(-50, -50, 0), FVector(50, 50, 90)), FTransform::Identity, Grass));

    const FVector Body(1000 + 600, 0, 96);   // Dink 6 m east of the trunk, beyond the crown (radius 3.2 m)
    const FVector Targets[] = {Body + FVector(0, 0, 60), Body, Body - FVector(0, 0, 85)};
    // the play camera 4 m behind Dink, inside the crown
    TestTrue(TEXT("camera standing in the crown"), Blocks(Crown, FVector(1000 + 200, 0, 180), Targets, 0.0));
    // the camera beyond the crown on the other side: the lines to Dink pass through it
    TestTrue(TEXT("crown between camera and Dink"), Blocks(Crown, FVector(1000 - 600, 0, 180), Targets, 0.0));
    // camera and Dink both east of the tree, the crown beside the line
    TestFalse(TEXT("crown beside the line stays"), Blocks(Crown, FVector(1000 + 1000, 0, 180), Targets, 0.0));
    const TArray<FVector> SideTarget = {Body + FVector(0, 700, 0)};
    TestFalse(TEXT("crown off to the side stays"), Blocks(Crown, FVector(1000 - 600, 700, 180), SideTarget, 0.0));
    // a crown passed just outside its radius fades only while it is already fading (hold margin)
    const FVector Edge(1000 + 330, -500, 180);
    const TArray<FVector> EdgeTarget = {FVector(1000 + 330, 500, 180)};
    TestFalse(TEXT("just outside the radius: no fade"), Blocks(Crown, Edge, EdgeTarget, 0.0));
    TestTrue(TEXT("just outside the radius: a fading crown stays faded"), Blocks(Crown, Edge, EdgeTarget, HoldMarginCm));
    // a crown that starts above the line (a raised crown) or ends below it does not block
    FCrown High = Crown; High.Bottom = 400.0;
    TestFalse(TEXT("line under a raised crown"), Blocks(High, FVector(1000 - 600, 0, 180), Targets, 0.0));
    FCrown Low = Crown; Low.Top = 50.0;
    const TArray<FVector> Head = {Body + FVector(0, 0, 60)};
    TestFalse(TEXT("line over a low bush"), Blocks(Low, FVector(1000 - 600, 0, 180), Head, 0.0));
    // a line that climbs over the trunk: inside the crown's height range only far from the axis
    FCrown Thin = Crown; Thin.Bottom = 110.0; Thin.Top = 120.0;
    TestTrue(TEXT("a full crown is crossed"), SegmentCrosses(Crown, FVector(0, 0, 100), FVector(2000, 0, 300), 0.0));
    TestFalse(TEXT("height range clips the segment before the XY test"), SegmentCrosses(Thin, FVector(0, 0, 100), FVector(2000, 0, 300), 0.0));
    TestTrue(TEXT("near test for the candidate filter"), Near(Crown, FVector(1000 - 600, 0, 180), Body, 200.0));
    TestFalse(TEXT("near test rejects far crowns"), Near(Crown, FVector(5000, 5000, 180), FVector(5400, 5000, 96), 200.0));

    // The fade: out within a quarter second, held, back in within half a second; never past 0 or 1.
    float Opacity = 1.f;
    for (int32 I = 0; I < 15; ++I) Opacity = StepOpacity(Opacity, true, 1.f / 60.f);
    TestEqual(TEXT("fades out in 0.25 s"), Opacity, FadedOpacity, 1.e-4f);
    Opacity = StepOpacity(Opacity, true, 1.f);
    TestEqual(TEXT("stays faded"), Opacity, FadedOpacity, 1.e-4f);
    for (int32 I = 0; I < 12; ++I) Opacity = StepOpacity(Opacity, false, 1.f / 60.f);
    TestTrue(TEXT("comes back gradually"), Opacity > 0.4f && Opacity < 0.6f);
    for (int32 I = 0; I < 30; ++I) Opacity = StepOpacity(Opacity, false, 1.f / 60.f);
    TestEqual(TEXT("back to opaque"), Opacity, 1.f, 1.e-4f);
    TestEqual(TEXT("a negative frame time changes nothing"), StepOpacity(.5f, true, -1.f), .5f, 1.e-6f);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCameraFoliageVariantsTest, "Dink.Art.CameraFoliage.Variants", DINK_TEST_FLAGS)
bool FDinkCameraFoliageVariantsTest::RunTest(const FString&)
{
    FString Text;
    TSharedPtr<FJsonObject> Config;
    if (!TestTrue(TEXT("camera_materials.json reads"), FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/camera_materials.json"))) &&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Config) && Config.IsValid())) return false;
    const TSharedPtr<FJsonObject>* Variants = nullptr;
    if (!TestTrue(TEXT("foliage_variants listed"), Config->TryGetObjectField(TEXT("foliage_variants"), Variants))) return false;
    TMap<FString, UMaterialInterface*> ByBase;
    for (const auto& Pair : (*Variants)->Values)
    {
        const FString Path = Pair.Value->AsString();
        UMaterialInterface* Variant = LoadObject<UMaterialInterface>(nullptr, *Path);
        if (!TestNotNull(*FString::Printf(TEXT("variant %s loads"), *Path), Variant)) continue;
        TestEqual(*FString::Printf(TEXT("%s is masked"), *Path), int32(Variant->GetBlendMode()), int32(BLEND_Masked));
        float Default = 0.f;
        TestTrue(*FString::Printf(TEXT("%s has DinkCameraOpacity = 1"), *Path),
            Variant->GetScalarParameterValue(FMaterialParameterInfo(TEXT("DinkCameraOpacity")), Default) && FMath::IsNearlyEqual(Default, 1.f));
        TestTrue(*FString::Printf(TEXT("%s dithers its mask"), *Path), Variant->GetMaterial() && Variant->GetMaterial()->DitherOpacityMask);
        ByBase.Add(FString(*Pair.Key).ToLower(), Variant);
    }
    // Every material of the forest's and the family pines' meshes has a variant: the camera can fade them.
    for (const TCHAR* MeshPath : {TEXT("/Game/Dink/Photoreal/Vegetation/SM_Veg_Pine_Large_01.SM_Veg_Pine_Large_01"),
             TEXT("/Game/Dink/Photoreal/Vegetation/SM_Veg_Pine_Medium_01.SM_Veg_Pine_Medium_01"),
             TEXT("/Game/Dink/Photoreal/Vegetation/SM_Veg_Pine_Storm_01.SM_Veg_Pine_Storm_01"),
             TEXT("/Game/Dink/Photoreal/Vegetation/SM_Veg_Oak_Large_01.SM_Veg_Oak_Large_01")})
    {
        UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, MeshPath);
        if (!TestNotNull(*FString::Printf(TEXT("%s loads"), MeshPath), Mesh)) continue;
        for (int32 I = 0; I < Mesh->GetStaticMaterials().Num(); ++I)
        {
            UMaterialInterface* M = Mesh->GetMaterial(I);
            const UMaterial* Base = M ? M->GetMaterial() : nullptr;
            TestTrue(*FString::Printf(TEXT("%s slot %d (%s) has a camera fade variant"), MeshPath, I, Base ? *Base->GetName() : TEXT("none")),
                Base && ByBase.Contains(Base->GetPathName().ToLower()));
        }
    }
    return true;
}
