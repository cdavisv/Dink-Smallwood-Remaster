#include "DinkTestHelpers.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/BoxComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Misc/ScopeExit.h"
#include "Serialization/ObjectWriter.h"

namespace
{
TArray<UStaticMeshComponent*> GeneratedWalls(ADinkScreenVolume& Volume)
{
    TArray<UStaticMeshComponent*> Result;
    TInlineComponentArray<UStaticMeshComponent*> Components(&Volume);
    for (auto* Component : Components)
        if (Component->GetName().StartsWith(TEXT("InteriorWall_"))) Result.Add(Component);
    return Result;
}
struct FWallPhysics
{
    UPrimitiveComponent* Component;
    FTransform Transform;
    FCollisionResponseContainer Responses;
    ECollisionEnabled::Type Collision;
    FName Profile;
    bool Overlaps, Visible;
    AActor* Owner;
    USceneComponent* Parent;
    UStaticMesh* Mesh;
    TArray<UMaterialInterface*> Materials;
    explicit FWallPhysics(UPrimitiveComponent* C) : Component(C), Transform(C->GetComponentTransform()),
        Responses(C->GetCollisionResponseToChannels()), Collision(C->GetCollisionEnabled()),
        Profile(C->GetCollisionProfileName()), Overlaps(C->GetGenerateOverlapEvents()), Visible(C->GetVisibleFlag()),
        Owner(C->GetOwner()), Parent(C->GetAttachParent()), Mesh(nullptr)
    {if(auto* Static=Cast<UStaticMeshComponent>(C)){Mesh=Static->GetStaticMesh();for(int I=0;I<Static->GetNumMaterials();++I)Materials.Add(Static->GetMaterial(I));}}
    void Check(FAutomationTestBase& Test) const
    {
        FTransform Now=Component->GetComponentTransform(), Before=Transform;
        TArray<uint8> A,B;FObjectWriter WA(A),WB(B);WA<<Before;WB<<Now;
        Test.TestTrue(TEXT("wall transform bytes unchanged"),A==B);
        Test.TestTrue(TEXT("wall collision responses unchanged"),Responses==Component->GetCollisionResponseToChannels());
        Test.TestEqual(TEXT("wall collision enabled unchanged"),int32(Component->GetCollisionEnabled()),int32(Collision));
        Test.TestEqual(TEXT("wall collision profile unchanged"),Component->GetCollisionProfileName(),Profile);
        Test.TestEqual(TEXT("wall overlap generation unchanged"),Component->GetGenerateOverlapEvents(),Overlaps);
        Test.TestEqual(TEXT("wall visible flag unchanged"),Component->GetVisibleFlag(),Visible);
        Test.TestTrue(TEXT("wall ownership and attachment unchanged"),Component->GetOwner()==Owner&&Component->GetAttachParent()==Parent);
        if(auto* Static=Cast<UStaticMeshComponent>(Component))
        {Test.TestTrue(TEXT("generated wall mesh unchanged"),Static->GetStaticMesh()==Mesh);Test.TestEqual(TEXT("wall material count unchanged"),Static->GetNumMaterials(),Materials.Num());
         for(int I=0;I<Materials.Num();++I)Test.TestTrue(TEXT("wall material unchanged"),Static->GetMaterial(I)==Materials[I]);}
    }
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkInteriorWallOwnershipTest,
    "Dink.Art.GeneratedInteriorWalls.OwnerAndJoinedRooms",DINK_TEST_FLAGS)
bool FDinkInteriorWallOwnershipTest::RunTest(const FString&)
{
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
    if(!TestNotNull(TEXT("owned scratch game world"),World))return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT{GEngine->DestroyWorldContext(World);World->DestroyWorld(false);World->MarkObjectsPendingKill();};
    auto* Greybox=World->GetSubsystem<UDinkGreyboxSubsystem>();
    if(!TestNotNull(TEXT("real screen subsystem"),Greybox)||!TestNotNull(TEXT("real physics scene"),World->GetPhysicsScene()))return false;
    auto* PC=World->SpawnActor<APlayerController>();auto* Pawn=World->SpawnActor<APawn>();
    auto* Root=NewObject<USceneComponent>(Pawn);Root->SetMobility(EComponentMobility::Movable);Pawn->SetRootComponent(Root);Root->RegisterComponent();PC->Possess(Pawn);
    if(!TestTrue(TEXT("actual first controller possesses scratch pawn"),World->GetFirstPlayerController()==PC&&PC->GetPawn()==Pawn))return false;
    auto Make=[&](int32 Number,double X,bool Indoor,FName Interior,FName Sheet)
    {
        auto* V=World->SpawnActor<ADinkScreenVolume>();V->ScreenNumber=Number;V->bIndoor=Indoor;V->InteriorId=Interior;V->Sheet=Sheet;
        V->Corners.NW={X,0};V->Corners.NE={X+12,0};V->Corners.SW={X,8};V->Corners.SE={X+12,8};
        V->SetActorLocation(FVector((X+6)*100,400,100));V->Bounds->SetBoxExtent(FVector(600,400,200));
        const FVector2D Mid[4]={{300,0},{600,200},{300,400},{0,200}};
        for(int E=0;E<4;++E)
        {auto* Wall=V->EdgeWalls[E];Wall->SetCollisionProfileName(TEXT("BlockAll"));Wall->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
         Wall->SetBoxExtent(E%2?FVector(10,400,100):FVector(600,10,100));Wall->SetWorldLocation(V->MapPixelToWorld(Mid[E].X,Mid[E].Y)+FVector(0,0,100));}
        return V;
    };
    auto* Home=Make(1,0,true,TEXT("INT_001"),TEXT("interior:INT_001"));Home->SetInteriorWallVisualsHidden(true);
    auto* Other=Make(2,30,true,TEXT("INT_002"),TEXT("interior:INT_002"));
    auto* JoinedA=Make(3,60,true,TEXT("INT_003"),TEXT("interior:INT_003"));
    auto* JoinedB=Make(4,72,true,TEXT("INT_003"),TEXT("interior:INT_003"));
    auto* Yard=Make(439,110,false,NAME_None,TEXT("mainland"));
    auto* BoothW=Make(289,150,true,TEXT("INT_289"),TEXT("interior:INT_289"));
    auto* BoothE=Make(290,162,true,TEXT("INT_289"),TEXT("interior:INT_289"));
    JoinedA->EdgeWalls[1]->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    JoinedB->EdgeWalls[3]->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    BoothW->EdgeWalls[1]->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    BoothE->EdgeWalls[3]->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    for(auto* V:{Home,Other,JoinedA,Yard,BoothW,BoothE})V->DispatchBeginPlay(); // joined B intentionally begins later
    TestEqual(TEXT("unconverted room creates its four original wall cubes"),GeneratedWalls(*Other).Num(),4);
    TestEqual(TEXT("joined A creates exactly three closed-edge visuals"),GeneratedWalls(*JoinedA).Num(),3);
    TestEqual(TEXT("real booth west group creates three closed-edge visuals"),GeneratedWalls(*BoothW).Num(),3);
    TestEqual(TEXT("real booth east group creates three closed-edge visuals"),GeneratedWalls(*BoothE).Num(),3);
    TArray<FWallPhysics> Physics;
    for(auto* V:{Home,Other,JoinedA,JoinedB,Yard,BoothW,BoothE}){Physics.Emplace(V->Bounds);for(auto* Wall:V->EdgeWalls)Physics.Emplace(Wall);for(auto* Visual:GeneratedWalls(*V))Physics.Emplace(Visual);}
    auto* Ordinary=World->SpawnActor<AStaticMeshActor>();auto* OrdinaryMesh=Ordinary->GetStaticMeshComponent();
    OrdinaryMesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));OrdinaryMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    const FTransform OrdinaryPose=Ordinary->GetActorTransform();
    auto Visible=[&](ADinkScreenVolume* V,bool Expected,const TCHAR* Label)
    {for(auto* Wall:GeneratedWalls(*V)){TestEqual(Label,!Wall->bHiddenInGame,Expected);TestTrue(TEXT("component visible flag retained"),Wall->GetVisibleFlag());TestEqual(TEXT("presentation cubes stay noncolliding"),int32(Wall->GetCollisionEnabled()),int32(ECollisionEnabled::NoCollision));}};
    const FVector North=Other->EdgeWalls[0]->GetComponentLocation();
    auto CheckPhysics=[&]()
    {for(const auto& Before:Physics)Before.Check(*this);FHitResult Hit;
     TestTrue(TEXT("same physical north wall blocks while its cube is hidden or shown"),World->LineTraceSingleByChannel(Hit,North-FVector(0,50,0),North+FVector(0,50,0),ECC_Pawn));
     TestTrue(TEXT("trace still hits exact original edge box"),Hit.GetComponent()==Other->EdgeWalls[0]);
     TestTrue(TEXT("ordinary outdoor/unconverted mesh remains visible"),OrdinaryMesh->GetVisibleFlag()&&!OrdinaryMesh->bHiddenInGame&&!Ordinary->IsHidden());
     TestTrue(TEXT("ordinary outdoor mesh pose unchanged"),OrdinaryPose.Equals(Ordinary->GetActorTransform(),0));};
    auto Move=[&](ADinkScreenVolume* V){Pawn->SetActorLocation(V->MapPixelToWorld(300,200)+FVector(0,0,100));Greybox->RefreshCurrentScreen();};
    Move(Home);Visible(Home,false,TEXT("authored home hide remains authoritative"));Visible(Other,false,TEXT("other interior hidden from home"));CheckPhysics();
    Home->SetInteriorWallVisualsHidden(false);Visible(Home,true,TEXT("unhidden own room visible"));Home->SetInteriorWallVisualsHidden(true);
    Move(Yard);for(auto* V:{Home,Other,JoinedA})Visible(V,false,TEXT("all generated interior walls hidden outdoors"));
    Home->SetInteriorWallVisualsHidden(false);Visible(Home,false,TEXT("clearing authored hide cannot expose offscreen room"));Home->SetInteriorWallVisualsHidden(true);CheckPhysics();
    Move(Other);Visible(Other,true,TEXT("unconverted room visible in its own screen"));Visible(Home,false,TEXT("authored home still hidden"));Visible(JoinedA,false,TEXT("unrelated joined group hidden"));CheckPhysics();
    Move(JoinedA);JoinedB->DispatchBeginPlay();
    TestEqual(TEXT("late-born joined B creates exactly three closed-edge visuals"),GeneratedWalls(*JoinedB).Num(),3);
    for(auto* Visual:GeneratedWalls(*JoinedB))Physics.Emplace(Visual);
    Visible(JoinedA,true,TEXT("joined source room visible"));Visible(JoinedB,true,TEXT("late-born joined room visible immediately"));Visible(Other,false,TEXT("other room hidden from joined group"));
    Move(JoinedB);Visible(JoinedA,true,TEXT("joined A retained on crossing into row4"));Visible(JoinedB,true,TEXT("joined B visible on row4"));CheckPhysics();
    JoinedB->Sheet=TEXT("interior:OTHER");Greybox->RefreshCurrentScreen();Visible(JoinedA,false,TEXT("same interior ID with different sheet is not joined"));JoinedB->Sheet=JoinedA->Sheet;
    JoinedB->SetInteriorWallVisualsHidden(true);Greybox->RefreshCurrentScreen();Visible(JoinedB,false,TEXT("authored group member hide remains authoritative"));JoinedB->SetInteriorWallVisualsHidden(false);
    Move(BoothW);Visible(BoothW,true,TEXT("actual booth west owner visible"));Visible(BoothE,true,TEXT("actual booth east joined room visible"));Visible(JoinedA,false,TEXT("separate joined house group remains hidden"));
    Move(BoothE);Visible(BoothW,true,TEXT("booth crossing retains west room"));Visible(BoothE,true,TEXT("booth crossing retains east room"));CheckPhysics();
    auto Callback=Greybox->OnScreenChanged.AddLambda([&](ADinkScreenVolume* Entered){if(Entered==Other)Pawn->SetActorLocation(Yard->MapPixelToWorld(300,200));});
    Move(Other);for(auto* V:{Home,Other,JoinedA,JoinedB,BoothW,BoothE})Visible(V,false,TEXT("synchronous entry relocation uses physical outdoor screen"));Greybox->OnScreenChanged.Remove(Callback);
    PC->UnPossess();Greybox->RefreshCurrentScreen();for(auto* V:{Home,Other,JoinedA,JoinedB,BoothW,BoothE})Visible(V,false,TEXT("no possessed pawn hides all generated rooms"));
    PC->Possess(Pawn);Move(Other);Visible(Other,true,TEXT("possession restores current unconverted room"));CheckPhysics();
    return true;
}
