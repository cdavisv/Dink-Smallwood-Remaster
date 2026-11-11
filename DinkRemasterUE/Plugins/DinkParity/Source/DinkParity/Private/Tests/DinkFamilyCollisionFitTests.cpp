#include "DinkTestHelpers.h"
#include "Hardness/DinkFamilyCollisionFit.h"
#include "Hardness/DinkFamilyFitMath.h"
#include "StaticMeshResources.h"
#include "Interfaces/Interface_CollisionDataProvider.h"
#include "AssetCompilingManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "UObject/UObjectGlobals.h"
#include "PhysicsEngine/BodySetup.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFamilyFitPolicyTest,"Dink.Art.Family.CollisionFitPolicy",DINK_TEST_FLAGS)
bool FDinkFamilyFitPolicyTest::RunTest(const FString&)
{
    TArray<FDinkFamilyCollisionFitRule> Rules;FString Error,Shipped;
    if(!TestTrue(TEXT("actual families available"),FFileHelper::LoadFileToString(Shipped,*(FPaths::ProjectContentDir()/TEXT("Dink/Data/Art/families.json")))))return false;
    TestTrue(TEXT("absent optional policy preserves defaults"),DinkFamilyCollisionFit::ParsePolicy(TEXT(R"({"schema":"dink-art-families/1","families":[]})"),Rules,Error));TestEqual(TEXT("absent policy activates zero origins"),Rules.Num(),0);
    TestTrue(TEXT("actual shipped policy parses"),DinkFamilyCollisionFit::ParsePolicy(Shipped,Rules,Error));const bool SourcePinned = Shipped.Contains(TEXT("dink-family-collision-fit/2")) || Shipped.Contains(TEXT("dink-family-collision-fit/3"));
    TestEqual(TEXT("expected shipped collision fit scope"), Rules.Num(), SourcePinned ? 85 : 2);
    TSet<FString> ActualOrigins;
    for(const auto& Rule:Rules)
    {
        ActualOrigins.Add(Rule.Origin.ToString());
        TestEqual(TEXT("approved active photoreal barrel mesh"),Rule.Mesh,FString(TEXT("/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.SM_Barrel_Oak_01")));
        TestEqual(TEXT("stable canonical photoreal surface SHA"),Rule.CanonicalSurfaceSha1,FString(TEXT("de0f514e0172077e7bbd9dc0b30c75f5c40939e6")));
        TestTrue(TEXT("v3 has no legacy ordered policy digest"),Rule.GeometrySha1.IsEmpty());
    }
    TestTrue(TEXT("exact reviewed pair retained with unique origins"),
        ActualOrigins.Num() == Rules.Num() && ActualOrigins.Contains(TEXT("S031_P03")) &&
        ActualOrigins.Contains(TEXT("S209_P13")));
    const FString Row=TEXT(R"({"origin":"S031_P03","family":"barrel","mesh":"/Game/Dink/Kits/Stonebrook/SM_Barrel_Oak_01.SM_Barrel_Oak_01","geometry_sha1":"0000000000000000000000000000000000000000","anchor":"sprite_ground","geometry":"cooked_complex","raster":"cell_center"})");
    auto Packet=[](const FString& Rows){return TEXT("{\"schema\":\"dink-art-families/1\",\"families\":[],\"collision_fit\":{\"schema\":\"dink-family-collision-fit/1\",\"origins\":[")+Rows+TEXT("]}}");};
    TestTrue(TEXT("complete narrow explicit rule parses, digest still requires native match"),DinkFamilyCollisionFit::ParsePolicy(Packet(Row),Rules,Error));TestEqual(TEXT("one prepared rule"),Rules.Num(),1);
    for(const FString& Bad:{Row+TEXT(",")+Row,Row.Replace(TEXT("S031_P03"),TEXT("S001_P03")),Row.Replace(TEXT("sprite_ground"),TEXT("card_center")),Row.Replace(TEXT("cooked_complex"),TEXT("box")),Row.Replace(TEXT("cell_center"),TEXT("unknown")),Row.Replace(TEXT("\"barrel\""),TEXT("true")),Row.Replace(TEXT("0000000000000000000000000000000000000000"),TEXT("not-reviewed"))})
    {TestFalse(TEXT("duplicate/foreign origin, wrong anchor/geometry/raster/type/digest refuse whole policy"),DinkFamilyCollisionFit::ParsePolicy(Packet(Bad),Rules,Error));TestEqual(TEXT("no partial policy survives refusal"),Rules.Num(),0);}
    const TArray<FString> InvalidDocuments = {
        TEXT("{"),
        TEXT(R"({"schema":"dink-art-families/1","families":[],"collision_fit":null})"),
        TEXT(R"({"schema":"dink-art-families/1","families":[],"collision_fit":{"origins":[]}})"),
        Packet(Row).Replace(TEXT("dink-family-collision-fit/1"), TEXT("dink-family-collision-fit/3")),
    };
    for (const auto& Invalid : InvalidDocuments)
    {
        TestFalse(TEXT("invalid explicit policy is rejected before generation"),
            DinkFamilyCollisionFit::ParsePolicy(Invalid, Rules, Error));
        TestTrue(TEXT("invalid policy reports an error and publishes no rows"),
            !Error.IsEmpty() && Rules.IsEmpty());
    }
    auto SourcePacket = [&Packet](const FString& Rows)
    {
        return Packet(Rows).Replace(TEXT("dink-family-collision-fit/1"), TEXT("dink-family-collision-fit/2"));
    };
    auto SourceRow = [&Row](const TCHAR* Id, const TCHAR* SourceFields)
    {
        return Row.LeftChop(1).Replace(TEXT("S031_P03"), Id) + SourceFields + TEXT("}");
    };
    const FString Anonymous = SourceRow(TEXT("S469_P13"), TEXT(R"(,"source_hash":"97c24d11722e25cf339fcbf0ee818f6b70e88f8d","source_script":"","source_type":1,"source_representation":"actor")"));
    const FString Background = SourceRow(TEXT("S469_P16"), TEXT(R"(,"source_hash":"7de7ec648bed4f586c30e43c3fc6ac53503e2758","source_script":"bar-sh","source_type":0,"source_representation":"instance")"));
    if (TestTrue(TEXT("explicit source rules cover anonymous live and scripted background"),
        DinkFamilyCollisionFit::ParsePolicy(SourcePacket(Anonymous + TEXT(",") + Background), Rules, Error)) &&
        TestEqual(TEXT("both source rules retained"), Rules.Num(), 2))
    {
        TestTrue(TEXT("anonymous source stays live"), Rules[0].SourceScript.IsNone() &&
            !Rules[0].IsStaticBackground());
        TestTrue(TEXT("type 0 source stays background with its original script name"),
            Rules[1].IsStaticBackground() && Rules[1].SourceScript == FName(TEXT("bar-sh")));
    }
    for (const auto& Bad : {Row, Background.Replace(TEXT("\"instance\""), TEXT("\"actor\"")),
            Background.Replace(TEXT("\"source_type\":0"), TEXT("\"source_type\":false")),
            Background.Replace(TEXT("bar-sh"), TEXT("bar-f1"))})
    {
        TestFalse(TEXT("source rule rejects missing metadata or incompatible background lifecycle"),
            DinkFamilyCollisionFit::ParsePolicy(SourcePacket(Bad), Rules, Error));
        TestEqual(TEXT("invalid source policy publishes no rows"), Rules.Num(), 0);
    }
    const FString PhotoRow = Anonymous.Replace(
        TEXT("/Game/Dink/Kits/Stonebrook/SM_Barrel_Oak_01.SM_Barrel_Oak_01"),
        TEXT("/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.SM_Barrel_Oak_01")).Replace(
        TEXT("\"geometry_sha1\":\"0000000000000000000000000000000000000000\""),
        TEXT("\"surface_algorithm\":\"DinkOrientedTrianglesF32LEMaterialU16LE/1\",\"surface_sha1\":\"de0f514e0172077e7bbd9dc0b30c75f5c40939e6\""));
    auto PhotoPacket = [&SourcePacket](const FString& Rows)
    { return SourcePacket(Rows).Replace(TEXT("dink-family-collision-fit/2"),TEXT("dink-family-collision-fit/3")); };
    TestTrue(TEXT("reviewed canonical photoreal source rule parses"),DinkFamilyCollisionFit::ParsePolicy(PhotoPacket(PhotoRow),Rules,Error));
    if(TestEqual(TEXT("one explicit canonical rule"),Rules.Num(),1))
        TestTrue(TEXT("canonical rule cannot fall back to legacy digest"),Rules[0].GeometrySha1.IsEmpty()&&!Rules[0].CanonicalSurfaceSha1.IsEmpty());
    for(const auto& Bad:{PhotoRow.Replace(TEXT("F32LE"),TEXT("F32BE")),
        PhotoRow.Replace(TEXT("de0f514e0172077e7bbd9dc0b30c75f5c40939e6"),TEXT("0000000000000000000000000000000000000000")),
        PhotoRow.Replace(TEXT("/Props/Stonebrook/PhotorealBarrelV1/"),TEXT("/Kits/Stonebrook/")),
        PhotoRow.LeftChop(1)+TEXT(",\"geometry_sha1\":\"0000000000000000000000000000000000000000\"}"),
        Anonymous})
    {
        TestFalse(TEXT("v3 rejects foreign algorithm/digest/mesh, mixed or legacy policy"),DinkFamilyCollisionFit::ParsePolicy(PhotoPacket(Bad),Rules,Error));
        TestTrue(TEXT("v3 failure leaves no partial rows"),Rules.IsEmpty());
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFamilyFitGeometryTest,"Dink.Art.Family.CollisionFitCookedGeometry",DINK_TEST_FLAGS)
bool FDinkFamilyFitGeometryTest::RunTest(const FString&)
{
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.SM_Barrel_Oak_01"));
    if(!TestNotNull(TEXT("actual family kit barrel"),Mesh))return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    if(!TestNotNull(TEXT("actual barrel body setup"),Mesh->GetBodySetup()))return false;
    // Test owns capability initialization only; production producer itself
    // refuses unavailable cooked geometry and never initiates a cook/save.
    Mesh->GetBodySetup()->CreatePhysicsMeshes();
    FDinkFamilyFittedGeometry G;FString Error;
    if(!TestTrue(TEXT("read actual reviewed cooked triangles"),DinkFamilyCollisionFit::ReadCookedGeometry(*Mesh,G,Error))){AddError(Error);return false;}
    TestEqual(TEXT("actual stable canonical photoreal surface"),G.CanonicalSurfaceSha1,FString(TEXT("de0f514e0172077e7bbd9dc0b30c75f5c40939e6")));
    TestEqual(TEXT("actual full source photoreal surface retained"),G.Triangles.Num(),16648);
    AddInfo(FString::Printf(TEXT("ACTUAL ordered cooked identity SHA1=%s"),*G.CookedGeometrySha1));
    FBox CookedBounds(ForceInit);for(const auto& V:G.Vertices)CookedBounds+=FVector(V);
    FTriMeshCollisionData Selected;const bool SelectedReady=Mesh->GetPhysicsTriMeshData(&Selected,Mesh->GetBodySetup()->bMeshCollideAll);
    FBox SelectedBounds(ForceInit);for(const auto& V:Selected.Vertices)SelectedBounds+=FVector(V);
    const auto* Render=Mesh->GetRenderData();
    const int32 SelectedLOD=Mesh->GetBodySetup()->bMeshCollideAll?0:FMath::Clamp(Mesh->LODForCollision,0,Render?Render->LODResources.Num()-1:0);
    AddInfo(FString::Printf(TEXT("ACTUAL collision LODForCollision=%d selectedLOD=%d bMeshCollideAll=%d NaniteEnabled=%d cookedReferencedVertices=%d cookedTriangles=%d cookedBounds=%s renderSourceBounds=%s selectedDataReady=%d selectedVertices=%d selectedTriangles=%d selectedBounds=%s cookedMinZ=%.17g cookedMaxZ=%.17g envelopeCm=%.17g"),
        Mesh->LODForCollision,SelectedLOD,int32(Mesh->GetBodySetup()->bMeshCollideAll),int32(Mesh->GetNaniteSettings().bEnabled),
        G.Vertices.Num(),G.Triangles.Num(),*CookedBounds.ToString(),*G.RenderBounds.ToString(),int32(SelectedReady),
        Selected.Vertices.Num(),Selected.Indices.Num(),*SelectedBounds.ToString(),CookedBounds.Min.Z,CookedBounds.Max.Z,DinkFamilyFit::CookedRenderEnvelopeCm));
    TestTrue(TEXT("actual selected collision LOD readable (test only, no cook/save)"),SelectedReady);
    if(SelectedReady)TestTrue(TEXT("actual cooked bounds match selected collision data (not source bound equality)"),CookedBounds.Equals(SelectedBounds,.0001));
    const auto Center=G.RenderBounds.GetCenter();
    TestFalse(TEXT("more than measured0.02cm budget must refuse"),DinkFamilyFit::WithinCookedRenderEnvelope(
        {Center.X,Center.Y,G.RenderBounds.Min.Z-.020001},
        {G.RenderBounds.Min.X,G.RenderBounds.Min.Y,G.RenderBounds.Min.Z},{G.RenderBounds.Max.X,G.RenderBounds.Max.Y,G.RenderBounds.Max.Z}));
    TestTrue(TEXT("actual triangles rather than one UCX box"),G.Triangles.Num()>1000);TestEqual(TEXT("UCX separately retained provenance"),G.AuthoredUCXVertices.Num(),8);
    FDinkScreenCorners Corners;Corners.NW=FVector2D(0,0);Corners.NE=FVector2D(41.25,0);Corners.SW=FVector2D(0,27.5);Corners.SE=FVector2D(41.25,27.5);
    const FVector Ground=DinkLayout::MapPixelToUnreal(Corners,300,316);const FTransform Proposed(FRotator(0,32,0),Ground,FVector::OneVector);
    TArray<FVector2D> Polygon;TArray<FIntPoint> Cells;double Low=0,High=0,Boundary=0;
    if(!TestTrue(TEXT("actual mesh projected through original screen"),DinkFamilyCollisionFit::BuildFootprint(G,Proposed,Corners,Polygon,Cells,Low,High,Boundary,Error)))return false;
    TestTrue(TEXT("fitted barrel logical area is smaller than original777pixels"),Cells.Num()>40&&Cells.Num()<250);
    double ExpectedLow=TNumericLimits<double>::Max(),ExpectedHigh=TNumericLimits<double>::Lowest();
    for(const auto& V:G.Vertices){const double Z=Proposed.TransformPosition(FVector(V)).Z;ExpectedLow=FMath::Min(ExpectedLow,Z);ExpectedHigh=FMath::Max(ExpectedHigh,Z);}
    TestTrue(TEXT("reported height equals exact transformed cooked vertices"),FMath::IsNearlyEqual(Low,ExpectedLow,1.e-6)&&FMath::IsNearlyEqual(High,ExpectedHigh,1.e-6));
    TestTrue(TEXT("actual physical height remains about101cm, not300cm"),High-Low>100&&High-Low<102);
    TestTrue(TEXT("raster boundary quantization explicitly measured"),Boundary>4&&Boundary<5);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkLegacyPictureProjection,"Dink.Art.Family.ReleasedPictureProjection",DINK_TEST_FLAGS)
bool FDinkLegacyPictureProjection::RunTest(const FString&)
{
    FDinkLegacyPictureDescriptor Source;Source.Sequence=173;Source.Frame=1;Source.Width=56;Source.Height=55;Source.OriginX=41;Source.OriginY=44;
    Source.Sha1=TEXT("b89b9bd0f6829a4c377345a7a3fe79793660dbfc");
    auto Broken=Source;Broken.Frame=6;Broken.Width=84;Broken.Height=64;Broken.Sha1=TEXT("31f8a48f1ae2bafe331f21acd5b8da64a4fa6ad9");
    const FTransform Baseline(FQuat::Identity,FVector(-13,0,-11),FVector(.56,1,.55));FTransform Projected;FString Error;
    TestTrue(TEXT("canonical source173/6 projects"),DinkFamilyCollisionFit::ProjectLegacyCard(Source,Broken,Baseline,Projected,Error));
    TestTrue(TEXT("source pixel geometry and pivot determine broken dimensions/anchor"),Projected.Equals(FTransform(FQuat::Identity,FVector(1,0,-20),FVector(.84,1,.64)),1.e-12));
    FTransform Again;TestTrue(TEXT("repeat uses immutable baseline without compounding"),DinkFamilyCollisionFit::ProjectLegacyCard(Source,Broken,Baseline,Again,Error)&&Again.Equals(Projected,0));
    TestTrue(TEXT("intact restore derives original baseline"),DinkFamilyCollisionFit::ProjectLegacyCard(Source,Source,Baseline,Again,Error)&&Again.Equals(Baseline,0));
    for(int32 Kind=0;Kind<5;++Kind)
    {
        auto Bad=Broken;if(Kind==0)Bad.Sha1.Reset();if(Kind==1)++Bad.Frame;if(Kind==2)++Bad.OriginX;if(Kind==3)++Bad.Width;if(Kind==4)Bad.Height=0;
        const FTransform Before=Again;
        TestFalse(TEXT("missing/wrong picture identity/pivot/size refuses"),DinkFamilyCollisionFit::ProjectLegacyCard(Source,Bad,Baseline,Again,Error));
        TestTrue(TEXT("rejected picture never mutates publication output"),Again.Equals(Before,0));
    }
    TestFalse(TEXT("missing importer scale refuses"),DinkFamilyCollisionFit::ProjectLegacyCard(Source,Broken,FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector),Again,Error));
    return true;
}


IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkLegacyPictureImportedSize,"Dink.Art.Family.ReleasedPictureImportedSize",DINK_TEST_FLAGS)
bool FDinkLegacyPictureImportedSize::RunTest(const FString&)
{
#if WITH_EDITORONLY_DATA
    FDinkLegacyPictureDescriptor P;P.Sequence=173;P.Frame=1;P.Width=56;P.Height=55;P.OriginX=41;P.OriginY=44;
    P.Sha1=TEXT("b89b9bd0f6829a4c377345a7a3fe79793660dbfc");
    TStrongObjectPtr<UTexture2D> Texture(NewObject<UTexture2D>(GetTransientPackage()));
    TArray<uint8> Pixels;Pixels.SetNumZeroed(64*64*4);Texture->Source.Init(64,64,1,1,TSF_BGRA8,Pixels.GetData());
    FIntPoint Observed;
    TestEqual(TEXT("owned unrendered texture has no platform surface width"),Texture->GetSurfaceWidth(),0.f);
    TestEqual(TEXT("owned unrendered texture has no platform surface height"),Texture->GetSurfaceHeight(),0.f);
    TestTrue(TEXT("actual imported authoring dimensions qualify without platform resource"),DinkFamilyCollisionFit::MatchesLegacyPictureImportedSize(P,*Texture,&Observed)&&Observed==FIntPoint(64,64));
    TArray<uint8> WrongPixels;WrongPixels.SetNumZeroed(32*64*4);Texture->Source.Init(32,64,1,1,TSF_BGRA8,WrongPixels.GetData());
    TestFalse(TEXT("actual mismatched imported width refuses despite valid descriptor"),DinkFamilyCollisionFit::MatchesLegacyPictureImportedSize(P,*Texture,&Observed));
    TestEqual(TEXT("rejection reports actual imported dimensions"),Observed,FIntPoint(32,64));
    Pixels.SetNumZeroed(64*32*4);Texture->Source.Init(64,32,1,1,TSF_BGRA8,Pixels.GetData());
    TestFalse(TEXT("actual mismatched imported height refuses"),DinkFamilyCollisionFit::MatchesLegacyPictureImportedSize(P,*Texture,&Observed));
#endif
    return true;
}
