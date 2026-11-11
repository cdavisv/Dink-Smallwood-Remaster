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
    auto* RefusedBody=NewObject<UDinkHardnessPrismComponent>(Host);
    Policy->SetGenerateOverlapEvents(true);
    TestFalse(TEXT("failed initial preparation refuses"),RefusedBody->PrepareCookedMeshGeometry(*Source,*Policy));
    TestFalse(TEXT("failed initial preparation cannot validate later"),RefusedBody->ValidateCookedMeshGeometry(*Source));
    Policy->SetGenerateOverlapEvents(false);
    auto* Body=NewObject<UDinkHardnessPrismComponent>(Host);
    Body->SetupAttachment(Root);
    const FVector Center=Mesh->GetBoundingBox().GetCenter();
    Body->SetRelativeLocation(FVector(-Center.X,-Center.Y,0));
    if(!TestTrue(TEXT("prepare exact readonly cooked geometry"),Body->PrepareCookedMeshGeometry(*Source,*Policy)))return false;
    // Test-owned unregistered copy only: every mutation is restored before registration.
    auto* PreparedSetup=Body->GetBodySetup();auto& PreparedMesh=*PreparedSetup->TriMeshGeometries[0];
    auto& MutableParticles=const_cast<Chaos::FTriangleMeshImplicitObject::ParticlesType&>(PreparedMesh.Particles());
    const auto OriginalPoint=MutableParticles.GetX(0);auto ShiftedPoint=OriginalPoint;ShiftedPoint[0]+=.25f;
    MutableParticles.SetX(0,ShiftedPoint);
    TestFalse(TEXT("post-prepare owned particle mutation refuses"),Body->ValidateCookedMeshGeometry(*Source));
    MutableParticles.SetX(0,OriginalPoint);
    auto ChangeCycle=[&](const auto& Elements)
    {
        auto Original=Elements;auto Changed=Original;
        const auto First=Changed[0][0];Changed[0][0]=Changed[0][1];Changed[0][1]=Changed[0][2];Changed[0][2]=First;
        auto& MutableElements=const_cast<Chaos::FTrimeshIndexBuffer&>(PreparedMesh.Elements());
        MutableElements.Reinitialize(MoveTemp(Changed));
        TestFalse(TEXT("even semantically identical cyclic reorder AFTER own freeze refuses"),Body->ValidateCookedMeshGeometry(*Source));
        MutableElements.Reinitialize(MoveTemp(Original));
    };
    if(PreparedMesh.Elements().RequiresLargeIndices())ChangeCycle(PreparedMesh.Elements().GetLargeIndexBuffer());
    else ChangeCycle(PreparedMesh.Elements().GetSmallIndexBuffer());
    const bool BeforeCull=PreparedMesh.GetCullsBackFaceRaycast();PreparedMesh.SetCullsBackFaceRaycast(!BeforeCull);
    TestFalse(TEXT("wrong owned inert cull refuses"),Body->ValidateCookedMeshGeometry(*Source));PreparedMesh.SetCullsBackFaceRaycast(BeforeCull);
    TestTrue(TEXT("exact restored owned epoch remains valid"),Body->ValidateCookedMeshGeometry(*Source));
    Host->AddInstanceComponent(Body);Body->RegisterComponent();
    if(!TestTrue(TEXT("registered inert profile preparation"),Body->FinalizeRegisteredPreparation(*Policy)))return false;
    TestTrue(TEXT("registered actual triangle body remains query+simulation inert"),Body->ValidateRegisteredInert());
    auto* Own=Body->GetBodySetup();
    TestTrue(TEXT("own transient setup never aliases source setup"),Own!=Source);
    TestTrue(TEXT("owned exact deep-copy implicit never aliases source"),
        Own&&Own->TriMeshGeometries.Num()==1&&Own->TriMeshGeometries[0]!=Source->TriMeshGeometries[0]);
    TestTrue(TEXT("all particles/elements/materials/external faces exact; owned active cull derived"),Body->ValidateCookedMeshGeometry(*Source));
    Own->TriMeshGeometries[0]->SetCullsBackFaceRaycast(Source->bDoubleSidedGeometry);
    TestFalse(TEXT("wrong registered owned cull refuses"),Body->ValidateCookedMeshGeometry(*Source));
    Own->TriMeshGeometries[0]->SetCullsBackFaceRaycast(!Source->bDoubleSidedGeometry);
    TestTrue(TEXT("correct registered owned cull restores validation"),Body->ValidateCookedMeshGeometry(*Source));
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
