#include "DinkTestHelpers.h"
#include "Hardness/DinkFamilyCollisionFit.h"
#include "AssetCompilingManager.h"
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/BodySetup.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFamilyFitPolicyTest,"Dink.Art.Family.CollisionFitPolicy",DINK_TEST_FLAGS)
bool FDinkFamilyFitPolicyTest::RunTest(const FString&)
{
    TArray<FDinkFamilyCollisionFitRule> Rules;FString Error,Shipped;
    if(!TestTrue(TEXT("actual families available"),FFileHelper::LoadFileToString(Shipped,*(FPaths::ProjectContentDir()/TEXT("Dink/Data/Art/families.json")))))return false;
    TestTrue(TEXT("absent optional policy preserves current defaults"),DinkFamilyCollisionFit::ParsePolicy(Shipped,Rules,Error));TestEqual(TEXT("zero activated origins"),Rules.Num(),0);
    const FString Row=TEXT(R"({"origin":"S031_P03","family":"barrel","mesh":"/Game/Dink/Kits/Stonebrook/SM_Barrel_Oak_01.SM_Barrel_Oak_01","geometry_sha1":"0000000000000000000000000000000000000000","anchor":"sprite_ground","geometry":"cooked_complex","raster":"cell_center"})");
    auto Packet=[](const FString& Rows){return TEXT("{\"schema\":\"dink-art-families/1\",\"families\":[],\"collision_fit\":{\"schema\":\"dink-family-collision-fit/1\",\"origins\":[")+Rows+TEXT("]}}");};
    TestTrue(TEXT("complete narrow explicit rule parses, digest still requires native match"),DinkFamilyCollisionFit::ParsePolicy(Packet(Row),Rules,Error));TestEqual(TEXT("one prepared rule"),Rules.Num(),1);
    for(const FString& Bad:{Row+TEXT(",")+Row,Row.Replace(TEXT("S031_P03"),TEXT("S001_P03")),Row.Replace(TEXT("sprite_ground"),TEXT("card_center")),Row.Replace(TEXT("cooked_complex"),TEXT("box")),Row.Replace(TEXT("cell_center"),TEXT("unknown")),Row.Replace(TEXT("\"barrel\""),TEXT("true")),Row.Replace(TEXT("0000000000000000000000000000000000000000"),TEXT("not-reviewed"))})
    {TestFalse(TEXT("duplicate/foreign origin, wrong anchor/geometry/raster/type/digest refuse whole policy"),DinkFamilyCollisionFit::ParsePolicy(Packet(Bad),Rules,Error));TestEqual(TEXT("no partial policy survives refusal"),Rules.Num(),0);}
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFamilyFitGeometryTest,"Dink.Art.Family.CollisionFitCookedGeometry",DINK_TEST_FLAGS)
bool FDinkFamilyFitGeometryTest::RunTest(const FString&)
{
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Dink/Kits/Stonebrook/SM_Barrel_Oak_01.SM_Barrel_Oak_01"));
    if(!TestNotNull(TEXT("actual family kit barrel"),Mesh))return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    if(!TestNotNull(TEXT("actual barrel body setup"),Mesh->GetBodySetup()))return false;
    // Test owns capability initialization only; production producer itself
    // refuses unavailable cooked geometry and never initiates a cook/save.
    Mesh->GetBodySetup()->CreatePhysicsMeshes();
    FDinkFamilyFittedGeometry G;FString Error;
    if(!TestTrue(TEXT("read actual reviewed cooked triangles"),DinkFamilyCollisionFit::ReadCookedGeometry(*Mesh,G,Error))){AddError(Error);return false;}
    TestTrue(TEXT("actual triangles rather than one UCX box"),G.Triangles.Num()>1000);TestEqual(TEXT("UCX separately retained provenance"),G.AuthoredUCXVertices.Num(),8);
    FDinkScreenCorners Corners;Corners.NW=FVector2D(0,0);Corners.NE=FVector2D(41.25,0);Corners.SW=FVector2D(0,27.5);Corners.SE=FVector2D(41.25,27.5);
    const FVector Ground=DinkLayout::MapPixelToUnreal(Corners,300,316);const FTransform Proposed(FRotator(0,32,0),Ground,FVector::OneVector);
    TArray<FVector2D> Polygon;TArray<FIntPoint> Cells;double Low=0,High=0,Boundary=0;
    if(!TestTrue(TEXT("actual mesh projected through original screen"),DinkFamilyCollisionFit::BuildFootprint(G,Proposed,Corners,Polygon,Cells,Low,High,Boundary,Error)))return false;
    TestTrue(TEXT("fitted barrel logical area is smaller than original777pixels"),Cells.Num()>40&&Cells.Num()<250);
    TestTrue(TEXT("actual physical height is about101cm, not300cm"),FMath::Abs((High-Low)-100.750007629)<.01);
    TestTrue(TEXT("raster boundary quantization explicitly measured"),Boundary>4&&Boundary<5);
    return true;
}
