#include "DinkTestHelpers.h"
#include "Hardness/DinkHardnessPrismComponent.h"
#include "Hardness/DinkFamilyCollisionFit.h"
#include "AssetCompilingManager.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Components/BoxComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DinkCollision.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Misc/ScopeExit.h"
#include "PhysicsEngine/BodySetup.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFamilyFitExactInertBody,
    "Dink.Art.Family.CollisionFitExactInertBody",DINK_TEST_FLAGS)
bool FDinkFamilyFitExactInertBody::RunTest(const FString& Parameters)
{
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.SM_Barrel_Oak_01"));
    FAssetCompilingManager::Get().FinishAllCompilation();
    if(!TestNotNull(TEXT("actual selected barrel mesh"),Mesh))return false;
    auto* Source=Mesh->GetBodySetup();if(!TestNotNull(TEXT("source body setup"),Source))return false;
    Source->CreatePhysicsMeshes(); // test-only readiness, production never cooks
    FDinkFamilyFittedGeometry Before;FString Error;
    if(!TestTrue(TEXT("read actual source cooked geometry"),DinkFamilyCollisionFit::ReadCookedGeometry(*Mesh,Before,Error)))
    {AddError(Error);return false;}
    auto* World=UWorld::CreateWorld(EWorldType::Game,false);
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT{GEngine->DestroyWorldContext(World);World->DestroyWorld(false);};
    auto* Host=World->SpawnActor<AActor>();
    auto* Root=NewObject<USceneComponent>(Host);Root->SetMobility(EComponentMobility::Static);
    Host->SetRootComponent(Root);Root->RegisterComponent();
    // Policy reference is deliberately unregistered: it creates no test box.
    auto* Policy=NewObject<UBoxComponent>(Host);
    Policy->SetCollisionProfileName(DinkCollision::ProfileHardSolid);
    Policy->SetGenerateOverlapEvents(false);Policy->SetCanEverAffectNavigation(false);
    auto* Body=NewObject<UDinkHardnessPrismComponent>(Host);
    Body->SetupAttachment(Root);
    const FVector Center=Mesh->GetBoundingBox().GetCenter();
    Body->SetRelativeLocation(FVector(-Center.X,-Center.Y,0));
    if(!TestTrue(TEXT("prepare exact readonly cooked geometry"),Body->PrepareCookedMeshGeometry(*Source,*Policy)))return false;
    Host->AddInstanceComponent(Body);Body->RegisterComponent();
    if(!TestTrue(TEXT("registered inert profile preparation"),Body->FinalizeRegisteredPreparation(*Policy)))return false;
    TestTrue(TEXT("registered actual triangle body remains query+simulation inert"),Body->ValidateRegisteredInert());
    auto* Own=Body->GetBodySetup();
    TestTrue(TEXT("own transient setup never aliases source setup"),Own!=Source);
    TestTrue(TEXT("owned exact deep-copy implicit never aliases source"),
        Own&&Own->TriMeshGeometries.Num()==1&&Own->TriMeshGeometries[0]!=Source->TriMeshGeometries[0]);
    TestTrue(TEXT("all particles/elements/materials/external faces exact; owned active cull derived"),Body->ValidateCookedMeshGeometry(*Source));
    TestEqual(TEXT("source raw cache cull unchanged by own registration"),Source->TriMeshGeometries[0]->GetCullsBackFaceRaycast(),Before.bSourceCullsBackFaceRaycast);
    TestEqual(TEXT("owned active cull follows stock double-sided policy"),Own->TriMeshGeometries[0]->GetCullsBackFaceRaycast(),!Source->bDoubleSidedGeometry);
    TestEqual(TEXT("source GUID unchanged"),Source->BodySetupGuid,Before.BodySetupGuid);
    const FVector Directions[]={FVector(1,0,0),FVector(-1,0,0),FVector(0,1,0),FVector(0,-1,0)};
    for(const FVector& Direction:Directions)
    {
        FHitResult Hit;
        const bool Contact=Body->SweepComponent(Hit,Direction*200+FVector(0,0,96),FVector(0,0,96),
            FQuat::Identity,FCollisionShape::MakeCapsule(28,96),true);
        TestTrue(TEXT("four cardinal player capsules contact exact inert query geometry"),Contact);
        if(Contact)TestTrue(TEXT("contact is near actual84cm barrel, not old254/319cm box"),
            Hit.Location.Size2D()>28 && Hit.Location.Size2D()<90);
        FHitResult High;
        TestFalse(TEXT("capsule above actual101cm mesh has no300cm proxy wall"),
            Body->SweepComponent(High,Direction*200+FVector(0,0,250),FVector(0,0,250),
                FQuat::Identity,FCollisionShape::MakeCapsule(28,96),true));
    }
    FHitResult WorldHit;
    TestFalse(TEXT("inert body does not block world pawn sweep"),World->SweepSingleByChannel(WorldHit,
        FVector(200,0,96),FVector(0,0,96),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(28,96)));
    FDinkFamilyFittedGeometry After;
    TestTrue(TEXT("source remains readable"),DinkFamilyCollisionFit::ReadCookedGeometry(*Mesh,After,Error));
    TestEqual(TEXT("actual source triangle+material+effective-policy digest unchanged"),After.CookedGeometrySha1,Before.CookedGeometrySha1);
    TestEqual(TEXT("source raw cache cull still unchanged after direct queries"),After.bSourceCullsBackFaceRaycast,Before.bSourceCullsBackFaceRaycast);
    // An unrelated ordinary component may legitimately initialize the shared
    // source cache. Exercise the ACTUAL engine registration path, not a setter.
    auto* Ordinary=NewObject<UStaticMeshComponent>(Host);
    Ordinary->SetupAttachment(Root);Ordinary->SetRelativeLocation(FVector(10000,0,0));
    Ordinary->SetStaticMesh(Mesh);Ordinary->SetCollisionProfileName(DinkCollision::ProfileHardSolid);
    Host->AddInstanceComponent(Ordinary);Ordinary->RegisterComponent();
    FDinkFamilyFittedGeometry Initialized;
    const bool InitializedRead=DinkFamilyCollisionFit::ReadCookedGeometry(*Mesh,Initialized,Error);
    TestTrue(TEXT("ordinary source-component initialization remains readable"),InitializedRead);
    TestEqual(TEXT("ordinary component derives source cache cull by stock policy"),Source->TriMeshGeometries[0]->GetCullsBackFaceRaycast(),!Source->bDoubleSidedGeometry);
    if(InitializedRead)TestEqual(TEXT("policy SHA independent of ordinary source cache initialization"),Initialized.CanonicalSurfaceSha1,Before.CanonicalSurfaceSha1);
    TestTrue(TEXT("owned exact geometry remains current across ordinary source cache initialization"),Body->ValidateCookedMeshGeometry(*Source));
    TestTrue(TEXT("body remains inert after direct interaction queries"),Body->ValidateRegisteredInert());
    return true;
}
