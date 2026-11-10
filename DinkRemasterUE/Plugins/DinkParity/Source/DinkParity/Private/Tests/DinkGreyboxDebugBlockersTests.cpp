#include "DinkTestHelpers.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkOriginComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ScopeExit.h"
#include "Serialization/ObjectWriter.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGreyboxDebugBlockersTest,
    "Dink.Art.Greybox.DebugBlockersStayPresentationOnly",DINK_TEST_FLAGS)
bool FDinkGreyboxDebugBlockersTest::RunTest(const FString&)
{
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
    if(!TestNotNull(TEXT("scratch world"),World))return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT{GEngine->DestroyWorldContext(World);World->DestroyWorld(false);World->MarkObjectsPendingKill();};
    if(!TestNotNull(TEXT("actual physics scene"),World->GetPhysicsScene()))return false;
    auto* Setting=IConsoleManager::Get().FindConsoleVariable(TEXT("dink.GreyboxBlockers"));
    if(!TestNotNull(TEXT("explicit debug setting exists"),Setting))return false;
    const int32 Original=Setting->GetInt();
    ON_SCOPE_EXIT{Setting->Set(Original,ECVF_SetByConsole);IConsoleManager::Get().CallAllConsoleVariableSinks();};
    Setting->Set(0,ECVF_SetByConsole);IConsoleManager::Get().CallAllConsoleVariableSinks();
    auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    auto* Plane=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane.Plane"));
    if(!TestNotNull(TEXT("actual engine solid mesh"),Cube)||!TestNotNull(TEXT("actual ground visual mesh"),Plane))return false;
    auto* Screen=World->SpawnActor<ADinkGreyboxScreen>();Screen->ScreenNumber=3;
    Screen->Visual->SetStaticMesh(Plane);
    Screen->DebugBlockers->SetStaticMesh(Cube);
    Screen->CollisionSolid->SetStaticMesh(Cube);
    Screen->CollisionSolid->SetRelativeLocation(FVector(0,0,-50));
    Screen->CollisionLow->SetStaticMesh(Cube);
    Screen->CollisionLow->SetRelativeLocation(FVector(300,0,-50));
    // Retain real card/decor/source identity beside the presentation toggle.
    auto* Card=World->SpawnActor<ADinkPlaceholderActor>();Card->ScreenNumber=3;
    Card->Card->SetStaticMesh(Plane);Card->Origin->OriginId=FDinkOriginId(3,12);Card->Origin->ScriptName=TEXT("bar-f1");Card->Origin->SourceHash=TEXT("unchanged-original-source");
    auto* Decor=NewObject<UInstancedStaticMeshComponent>(Screen,TEXT("Decor_Control"));
    Decor->SetMobility(EComponentMobility::Static);Decor->SetupAttachment(Screen->GetRootComponent());
    Decor->SetStaticMesh(Cube);Decor->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Screen->AddInstanceComponent(Decor);Decor->RegisterComponent();Decor->AddInstance(FTransform(FVector(500,0,0)));
    FDinkInstanceOrigin Origin;Origin.OriginId=FDinkOriginId(3,5);Origin.ScriptName=TEXT("s1-h3-s");Origin.ComponentName=Decor->GetFName();Origin.InstanceIndex=0;Origin.SourceHash=TEXT("original-decor");
    Screen->InstanceOrigins->Origins.Add(Origin);
    Screen->DispatchBeginPlay();
    TestTrue(TEXT("nonempty debug mesh hidden by default"),Screen->DebugBlockers->GetStaticMesh()==Cube&&Screen->DebugBlockers->bHiddenInGame);
    TestFalse(TEXT("debug never casts visible shadows"),Screen->DebugBlockers->CastShadow);
    TestFalse(TEXT("debug never casts hidden shadows"),Screen->DebugBlockers->bCastHiddenShadow);
    TArray<uint8> BeforeOrigins,BeforeCard;
    FObjectWriter WO(Screen->InstanceOrigins,BeforeOrigins),WC(Card->Origin,BeforeCard);
    FTransform DecorBefore;Decor->GetInstanceTransform(0,DecorBefore);
    const FTransform CardBefore=Card->Card->GetComponentTransform(),FloorBefore=Screen->Visual->GetComponentTransform(),DebugBefore=Screen->DebugBlockers->GetComponentTransform();
    struct FPhysical { UStaticMeshComponent* C; UStaticMesh* Mesh; FTransform T; FName Profile;
        FCollisionResponseContainer Responses; ECollisionEnabled::Type Enabled; bool Overlaps; FBodyInstance* Body;
    };
    TArray<FPhysical> Physical;
    for(UStaticMeshComponent* C:{Screen->CollisionSolid.Get(),Screen->CollisionLow.Get()})
        Physical.Add({C,C->GetStaticMesh(),C->GetComponentTransform(),C->GetCollisionProfileName(),C->GetCollisionResponseToChannels(),C->GetCollisionEnabled(),C->GetGenerateOverlapEvents(),C->GetBodyInstance()});
    auto CheckContacts=[&]
    {
        FHitResult Hit;
        TestTrue(TEXT("original solid ground still blocks capsule channel"),World->LineTraceSingleByChannel(Hit,FVector(0,0,100),FVector(0,0,-100),ECC_Pawn));
        TestTrue(TEXT("solid hit still belongs original physical component"),Hit.GetComponent()==Screen->CollisionSolid);
    };
    CheckContacts();
    for(const int32 Mode:{1,0,1,0})
    {
        Setting->Set(Mode,ECVF_SetByConsole);IConsoleManager::Get().CallAllConsoleVariableSinks();
        TestEqual(TEXT("explicit setting controls only debug hidden flag"),bool(Screen->DebugBlockers->bHiddenInGame),Mode==0);
        TestFalse(TEXT("original textured floor remains visible"),Screen->Visual->bHiddenInGame);
        TestTrue(TEXT("all render geometry transforms unchanged"),Card->Card->GetComponentTransform().Equals(CardBefore,0)&&Screen->Visual->GetComponentTransform().Equals(FloorBefore,0)&&Screen->DebugBlockers->GetComponentTransform().Equals(DebugBefore,0));
        TestFalse(TEXT("original sprite card remains visible"),Card->Card->bHiddenInGame);
        TestFalse(TEXT("original instanced decor remains visible"),Decor->bHiddenInGame);
        TestEqual(TEXT("debug never admits physical collision"),int32(Screen->DebugBlockers->GetCollisionEnabled()),int32(ECollisionEnabled::NoCollision));
        for(const auto& P:Physical)
        {
            TestTrue(TEXT("same original physics mesh and body"),P.C->GetStaticMesh()==P.Mesh&&P.C->GetBodyInstance()==P.Body);
            TestTrue(TEXT("physical transforms exact"),P.C->GetComponentTransform().Equals(P.T,0));
            TestTrue(TEXT("physical collision policy unchanged"),P.C->GetCollisionProfileName()==P.Profile&&P.C->GetCollisionResponseToChannels()==P.Responses&&P.C->GetCollisionEnabled()==P.Enabled&&P.C->GetGenerateOverlapEvents()==P.Overlaps);
        }
        FTransform DecorNow;Decor->GetInstanceTransform(0,DecorNow);TestTrue(TEXT("original decor instance unchanged"),DecorBefore.Equals(DecorNow,0));
        TArray<uint8> NowOrigins,NowCard;FObjectWriter NO(Screen->InstanceOrigins,NowOrigins),NC(Card->Origin,NowCard);
        TestTrue(TEXT("original placement/script identity bytes unchanged"),BeforeOrigins==NowOrigins&&BeforeCard==NowCard);
        CheckContacts();
    }
    Setting->Set(1,ECVF_SetByConsole);IConsoleManager::Get().CallAllConsoleVariableSinks();
    auto* Late=World->SpawnActor<ADinkGreyboxScreen>();Late->DispatchBeginPlay();
    TestFalse(TEXT("late screen inherits explicit debug setting"),Late->DebugBlockers->bHiddenInGame);
    return true;
}
