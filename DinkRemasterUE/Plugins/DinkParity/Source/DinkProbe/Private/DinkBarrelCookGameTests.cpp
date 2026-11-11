#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/BodySetup.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Hardness/DinkCanonicalSurface.h"
#include "HAL/PlatformProperties.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "UObject/Package.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#endif

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBarrelCookGameSurface,
    "Dink.Art.Family.BarrelCookedGameSurface",
    EAutomationTestFlags_ApplicationContextMask|EAutomationTestFlags::ProductFilter)
bool FDinkBarrelCookGameSurface::RunTest(const FString&)
{
    constexpr const TCHAR* MeshPath=TEXT("/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.SM_Barrel_Oak_01");
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,MeshPath);
    if(!TestNotNull(TEXT("approved photoreal mesh loads from actual target data"),Mesh))return false;
#if WITH_EDITOR
    FAssetCompilingManager::Get().FinishAllCompilation();
#endif
    auto* Body=Mesh->GetBodySetup();
    if(!TestNotNull(TEXT("actual saved photoreal collision setup"),Body))return false;
    // BodySetup.cpp IsRuntime chooses runtime cooking only for an owning
    // object's game world. This saved asset has no such owner.
    if(!TestTrue(TEXT("saved asset ownership excludes runtime world cooking"),
        Body->GetOuter()==Mesh&&Mesh->GetWorld()==nullptr))return false;
    const bool CreatedBefore=Body->bCreatedPhysicsMeshes;
    const bool RequiresCooked=FPlatformProperties::RequiresCookedData();
    if(RequiresCooked)
    {
        if(!TestTrue(TEXT("Game target reads a cooked package"),Mesh->GetPackage()->HasAnyPackageFlags(PKG_Cooked))||
           !TestTrue(TEXT("Game target has serialized cooked collision data"),Body->bHasCookedCollisionData))return false;
    }
    // Test capability initialization. In Game the guards above require a cooked
    // package and serialized collision, with no invalidation or recook request.
    Body->CreatePhysicsMeshes();
    if(!TestTrue(TEXT("actual complex cooked collision is initialized"),
        Body->bCreatedPhysicsMeshes&&!Body->bFailedToCreatePhysicsMeshes&&
        Body->CollisionTraceFlag==CTF_UseComplexAsSimple&&!Body->bDoubleSidedGeometry&&
        Body->TriMeshGeometries.Num()==1&&Body->TriMeshGeometries[0]))return false;
    const auto& Cooked=*Body->TriMeshGeometries[0];
    if(!TestEqual(TEXT("actual cooked full photoreal triangle count"),Cooked.Elements().GetNumTriangles(),16648))return false;
    std::vector<DinkCanonicalSurface::Triangle> Triangles;
    Triangles.reserve(16648);
    bool Finite=true,MaterialValid=true;
    auto Read=[&](const auto& Rows)
    {
        int32 Index=0;
        for(const auto& Row:Rows)
        {
            DinkCanonicalSurface::Triangle Triangle;
            for(int32 Corner=0;Corner<3;++Corner)
            {
                const FVector3f Position(Cooked.Particles().GetX(Row[Corner]));
                Finite&=FMath::IsFinite(Position.X)&&FMath::IsFinite(Position.Y)&&FMath::IsFinite(Position.Z);
                Triangle.Points[Corner]={Position.X,Position.Y,Position.Z};
            }
            Triangle.Material=Cooked.GetMaterialIndex(Index++);
            MaterialValid&=Triangle.Material==0;
            Triangles.push_back(Triangle);
        }
    };
    if(Cooked.Elements().RequiresLargeIndices())Read(Cooked.Elements().GetLargeIndexBuffer());
    else Read(Cooked.Elements().GetSmallIndexBuffer());
    if(!TestTrue(TEXT("all actual collision vertices finite"),Finite)||
       !TestTrue(TEXT("all actual collision materials match authored group0"),MaterialValid))return false;
    const auto Bytes=DinkCanonicalSurface::Bytes(Triangles,!Body->bDoubleSidedGeometry);
    uint8 Hash[FSHA1::DigestSize];FSHA1::HashBuffer(Bytes.data(),Bytes.size(),Hash);
    const FString Digest=BytesToHex(Hash,FSHA1::DigestSize).ToLower();
    TestEqual(TEXT("actual cooked oriented surface matches editor-proven authored source"),
        Digest,FString(TEXT("de0f514e0172077e7bbd9dc0b30c75f5c40939e6")));
    const FString Directory=FPaths::ProjectSavedDir()/TEXT("Automation");
    IFileManager::Get().MakeDirectory(*Directory,true);
    const FString SurfacePath=Directory/TEXT("BarrelCookGame.surface.bin");
    const FString FactsPath=Directory/TEXT("BarrelCookGame.txt");
    if(!TestFalse(TEXT("preserve prior target surface capture"),IFileManager::Get().FileExists(*SurfacePath))||
       !TestFalse(TEXT("preserve prior target facts"),IFileManager::Get().FileExists(*FactsPath)))return false;
    TArray<uint8> Surface;Surface.Append(Bytes.data(),int32(Bytes.size()));
    TestTrue(TEXT("actual target canonical surface captured"),FFileHelper::SaveArrayToFile(Surface,*SurfacePath));
    const FString Facts=FString::Printf(TEXT("mesh=%s\nrequires_cooked=%d\npackage_cooked=%d\nserialized_collision=%d\ninitialized_before=%d\ntriangles=%d\neffective_cull=%d\nraw_cull=%d\nbody_guid=%s\ncanonical_sha1=%s\n"),
        *Mesh->GetPathName(),RequiresCooked,Mesh->GetPackage()->HasAnyPackageFlags(PKG_Cooked),
        Body->bHasCookedCollisionData,CreatedBefore,Cooked.Elements().GetNumTriangles(),!Body->bDoubleSidedGeometry,
        Cooked.GetCullsBackFaceRaycast(),*Body->BodySetupGuid.ToString(),*Digest);
    TestTrue(TEXT("actual target capability facts captured"),FFileHelper::SaveStringToFile(Facts,*FactsPath));
    AddInfo(Facts);return true;
}
