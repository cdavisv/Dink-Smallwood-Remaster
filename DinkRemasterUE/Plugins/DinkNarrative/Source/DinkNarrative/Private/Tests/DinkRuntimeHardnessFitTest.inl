// Included by the production adapter only in automation builds so this fixture
// can inspect its private published epoch without exposing an admission bypass.
#include "Misc/AutomationTest.h"
#include "Misc/ScopeExit.h"
#include "Misc/Guid.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Engine/GameInstance.h"
#include "Greybox/DinkScreenVolume.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/BodySetup.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "DinkCollision.h"
#include "Hardness/DinkHardnessPrismComponent.h"
#include "UObject/Package.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#endif

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHardnessFittedLifecycle,
    "Dink.Gameplay.Hardness.FittedLifecycle",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FDinkHardnessFittedLifecycle::RunTest(const FString& Parameters)
{
    auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    auto* Barrel=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Dink/Kits/Stonebrook/SM_Barrel_Oak_01.SM_Barrel_Oak_01"));
#if WITH_EDITOR
    FAssetCompilingManager::Get().FinishAllCompilation();
#endif
    if(!TestNotNull(TEXT("real native barrel required"),Barrel)||!TestNotNull(TEXT("engine cube"),Cube))return false;
    UGameInstance* GI=NewObject<UGameInstance>(GEngine);GI->InitializeStandalone();UWorld* W=GI->GetWorld();
    TWeakPtr<FDinkRegisteredHardnessOwner> ShutdownOwner;
    TWeakObjectPtr<AActor> ShutdownHost;
    ON_SCOPE_EXIT {
        TArray<TWeakObjectPtr<UDinkHardnessPrismComponent>> RegisteredBodies;
        if(auto* H=ShutdownHost.Get())
        {TArray<UDinkHardnessPrismComponent*> Bodies;H->GetComponents(Bodies);for(auto* B:Bodies)if(B->IsRegistered())RegisteredBodies.Add(B);}
        const bool HadOwner=ShutdownOwner.IsValid();
        GI->Shutdown();
        if(HadOwner)
        {
            TestTrue(TEXT("shutdown fixture had actual registered owned bodies"),RegisteredBodies.Num()>0);
            TestFalse(TEXT("actual GI shutdown releases retained physical owner before World GC"),ShutdownOwner.IsValid());
            for(const auto& Weak:RegisteredBodies)if(auto* B=Weak.Get())
                TestFalse(TEXT("actual GI shutdown retires owned component registration/physics before World GC"),B->IsRegistered()||B->IsPhysicsStateCreated());
        }
        GEngine->DestroyWorldContext(W);W->DestroyWorld(false);
        // The standalone fixture owns this entire game world. Match the engine
        // game-unload lifecycle so later real editor map loads can collect it.
        AddInfo(FString::Printf(TEXT("Owned scratch teardown %s rooted=%d flags=%u"),*W->GetPathName(),W->IsRooted(),uint32(W->GetFlags())));
        TestFalse(TEXT("owned scratch world released from root"),W->IsRooted());
        W->MarkObjectsPendingKill();
        TestTrue(TEXT("owned scratch world marked for collection"),W->HasAnyInternalFlags(EInternalObjectFlags::Garbage));};
    auto* Story=GI->GetSubsystem<UDinkStorySubsystem>();
    if(!TestTrue(TEXT("actual story dataset ready"),Story&&Story->IsReady()&&Story->GetGameplay()->HasData()))return false;
    Story->bRunScreenScripts=false;Story->bNewGamePending=false;
    auto* G=Story->GetGameplay();auto* D=Story->GetDirector();
    const FDinkOriginId Id(209,13);const auto* Placement=G->GetData().FindPlacement(Id);
    if(!TestNotNull(TEXT("audited food barrel source"),Placement))return false;
    auto* Volume=W->SpawnActor<ADinkScreenVolume>();Volume->ScreenNumber=209;
    Volume->Corners.NW={0,0};Volume->Corners.NE={41.25,0};Volume->Corners.SW={0,27.5};Volume->Corners.SE={41.25,27.5};
    auto* Host=W->SpawnActor<ADinkGreyboxScreen>();Host->ScreenNumber=209;auto* Root=Host->GetRootComponent();Root->SetMobility(EComponentMobility::Static);Host->Tags.Add(TEXT("DinkHardnessWorldV1"));
    auto Policy=[&](FName Profile){auto* C=NewObject<UStaticMeshComponent>(Host);C->SetupAttachment(Root);C->SetMobility(EComponentMobility::Static);C->SetCollisionProfileName(Profile);C->SetGenerateOverlapEvents(false);C->SetCanEverAffectNavigation(false);C->RegisterComponent();return C;};
    auto* Solid=Policy(DinkCollision::ProfileHardSolid);auto* Low=Policy(DinkCollision::ProfileHardLow);
    // This native fixture owns an UNSAVED floor derived from the actual engine
    // cube. Its source/transform/policy callback proves that exact scratch floor;
    // production world admission still requires its strict source descriptor.
    auto* Package=CreatePackage(*(TEXT("/Game/Dink/RuntimeHardnessV1/Fixtures/T_")+FGuid::NewGuid().ToString(EGuidFormats::Digits)));
    auto* Fixed=DuplicateObject<UStaticMesh>(Cube,Package,TEXT("SCR_209_FixedSolidV1"));
#if WITH_EDITOR
    // Duplication does not itself qualify a new unsaved mesh for registered
    // physics. Finish the owned scratch candidate just as a staged asset would.
    Fixed->Build(false);FAssetCompilingManager::Get().FinishAllCompilation();
#endif
    if(Fixed->GetBodySetup())Fixed->GetBodySetup()->CreatePhysicsMeshes();
    auto* Floor=NewObject<UStaticMeshComponent>(Host);Floor->SetupAttachment(Root);Floor->SetMobility(EComponentMobility::Static);Floor->SetCollisionProfileName(DinkCollision::ProfileHardSolid);Floor->SetGenerateOverlapEvents(false);Floor->SetCanEverAffectNavigation(false);Floor->SetStaticMesh(Fixed);Floor->ComponentTags.Add(TEXT("DinkHardnessFixedFloorFillV1"));
    Floor->SetRelativeLocation(FVector(2062.5,1375,-50));Floor->SetRelativeScale3D(FVector(41.25,27.5,1));Floor->RegisterComponent();
    const auto* FloorBody=Floor->GetBodyInstance();
    const bool FloorReady=W->GetPhysicsScene()!=nullptr&&Floor->IsRegistered()&&Floor->IsPhysicsStateCreated()&&FloorBody&&FloorBody->IsValidBodyInstance();
    const FString FloorState=FString::Printf(TEXT("scratch floor readiness scene=%d registered=%d physics=%d validBody=%d compiling=%d bodySetup=%d boxes=%d convexes=%d enabled=%d object=%d path=%s"),
        W->GetPhysicsScene()!=nullptr,Floor->IsRegistered(),Floor->IsPhysicsStateCreated(),FloorBody&&FloorBody->IsValidBodyInstance(),Fixed->IsCompiling(),Fixed->GetBodySetup()!=nullptr,
        Fixed->GetBodySetup()?Fixed->GetBodySetup()->AggGeom.BoxElems.Num():-1,Fixed->GetBodySetup()?Fixed->GetBodySetup()->AggGeom.ConvexElems.Num():-1,int32(Floor->GetCollisionEnabled()),int32(Floor->GetCollisionObjectType()),*Fixed->GetPathName());
    if(!TestTrue(FloorState,FloorReady))return false;
    const FTransform FloorTransform=Floor->GetComponentTransform();const auto FloorResponses=Floor->GetCollisionResponseToChannels();
    FDinkHardnessWorldDefinition Definition;Definition.Host=Host;Definition.Screen=Volume;Definition.SolidPolicy=Solid;Definition.LowPolicy=Low;Definition.ImmutableFloorFill.Add(Floor);Definition.Vision=0;
    Definition.IsAuthoredCollisionScreen=[](){return false;};Definition.VerifyImmutableFoundation=[=](FString& E){const bool Ok=Floor->GetStaticMesh()==Fixed&&Floor->GetComponentTransform().Equals(FloorTransform,0)&&Floor->GetCollisionResponseToChannels()==FloorResponses&&Fixed->GetBodySetup()!=nullptr;if(!Ok)E=TEXT("scratch immutable floor changed");return Ok;};
    FString Error;auto Owner=FDinkRegisteredHardnessOwner::Create(MoveTemp(Definition),Error);
    ShutdownOwner=Owner;ShutdownHost=Host;
    if(!TestTrue(FString(TEXT("actual registered owner: "))+Error,Owner.IsValid()))return false;
    const FVector Ground=DinkLayout::MapPixelToUnreal(Volume->Corners,Placement->X-20,Placement->Y);
    auto* Actor=W->SpawnActorDeferred<ADinkPlaceholderActor>(ADinkPlaceholderActor::StaticClass(),FTransform(Ground));
    Actor->ScreenNumber=209;Actor->Origin->OriginId=Id;Actor->Origin->Sequence=173;Actor->Origin->Frame=1;Actor->Origin->ScriptName=TEXT("bar-f1");Actor->Origin->ClassId=TEXT("barrel");Actor->Origin->SourceHash=FString::ChrN(40,TEXT('a'));
    Actor->GetRootComponent()->SetMobility(EComponentMobility::Movable);Actor->Card->SetMobility(EComponentMobility::Movable);Actor->FinishSpawning(FTransform(Ground));Actor->Tags.Add(UDinkArtFamilySubsystem::FamilyTag);
    Actor->Card->SetStaticMesh(Cube);Actor->Card->SetCollisionEnabled(ECollisionEnabled::NoCollision);Actor->Card->SetCanEverAffectNavigation(false);Actor->Card->SetGenerateOverlapEvents(false);Actor->Card->SetHiddenInGame(true);
    auto* FamilyMesh=NewObject<UStaticMeshComponent>(Actor);Actor->AddInstanceComponent(FamilyMesh);FamilyMesh->SetupAttachment(Actor->GetRootComponent());FamilyMesh->SetMobility(EComponentMobility::Movable);FamilyMesh->SetStaticMesh(Barrel);FamilyMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);FamilyMesh->SetCanEverAffectNavigation(false);FamilyMesh->SetGenerateOverlapEvents(false);FamilyMesh->ComponentTags.Add(UDinkArtFamilySubsystem::FamilyTag);FamilyMesh->SetRelativeLocation(FVector(89,0,0));FamilyMesh->RegisterComponent();
    auto* Families=W->GetSubsystem<UDinkArtFamilySubsystem>();if(!TestNotNull(TEXT("family subsystem"),Families))return false;
    FDinkFamilyFittedGeometry Geometry;if(!TestTrue(TEXT("actual cooked complex geometry"),DinkFamilyCollisionFit::ReadCookedGeometry(*Barrel,Geometry,Error)))return false;
    Families->bReady=true;Families->bCollisionFitPolicyError=false;Families->Precedence={};Families->Bindings.Reset();Families->CollisionFitRules.Reset();
    FDinkFamilyBinding Binding;Binding.Family=TEXT("barrel");Binding.ClassId=TEXT("barrel");Binding.Mesh=Barrel->GetPathName();Binding.Fit=EDinkFamilyFit::None;Binding.bScripted=true;Families->Bindings.Add(Binding);
    Families->CollisionFitRules.Add({Id,Barrel->GetPathName(),Geometry.CookedGeometrySha1});
    const int Handle=D->CreateVirtualSprite(209,Placement->X,Placement->Y);auto* S=D->FindSprite(Handle);S->Actor=Actor;S->Origin=Id;S->Script=TEXT("bar-f1");S->Props.Add(TEXT("live"),1);S->Props.Add(TEXT("pseq"),173);S->Props.Add(TEXT("pframe"),1);S->Props.Add(TEXT("hard"),0);
    // Feed the SAME strict production reader an owned saved source packet.
    // There is no public path override or missing-sidecar admission exemption.
    const FString SelectedDirectory=FPaths::ProjectSavedDir()/TEXT("Automation/FittedSource")/FGuid::NewGuid().ToString();
    IFileManager::Get().MakeDirectory(*SelectedDirectory,true);
    ON_SCOPE_EXIT {IFileManager::Get().DeleteDirectory(*SelectedDirectory,false,true);};
    const FString SelectedFile=SelectedDirectory/TEXT("SCR_209_layers.json");
    TArray<FString> SourceRows;for(int Y=0;Y<400;++Y)SourceRows.Add(TEXT("[[600,0]]"));
    TArray<FString> SourceFlags;for(int I=0;I<99;++I)SourceFlags.Add(TEXT("0"));
    const FString SelectedJson=TEXT("{\"schema\":\"dinkex.runtime-hardness/2\",\"width\":600,\"height\":400,\"vision\":0,\"skipped_tile_indices\":[],\"ordered_stamps\":[],\"tile_base_rle\":[")+
        FString::Join(SourceRows,TEXT(","))+TEXT("],\"editor_hard_flags\":[")+FString::Join(SourceFlags,TEXT(","))+TEXT("]}");
    if(!TestTrue(TEXT("write owned strict selected-source fixture"),FFileHelper::SaveStringToFile(SelectedJson,*SelectedFile)))return false;
    FDinkRuntimeHardnessSource SelectedSource;
    if(!TestTrue(TEXT("strict actual source parser accepts selected baseline"),FDinkRuntimeHardnessSource::Load(SelectedFile,0,SelectedSource,Error))){AddError(Error);return false;}
    auto Map=DinkHardness::Layers::Create(SelectedSource.TileBase,{});
    if(!TestTrue(TEXT("private complete scratch epoch"),Map.has_value()&&G->OriginalSlotHistory.IsValid()))return false;
    G->OriginalSlotHistory->SelectedProjection=true;G->OriginalSlotHistory->Screen=209;
    G->HardnessProjection=MakeShared<FDinkHardnessProjection>(std::move(*Map),SelectedSource.TileBase,209,G->OriginalSlotHistory);G->HardnessProjection->RawEditorHard=SelectedSource.EditorHard;G->HardnessProjection->Phase=EOriginalHardnessPhase::Live;
    FString CanonicalError;TestFalse(TEXT("public admission never exempts absent/drifted canonical baseline"),G->AdmitRuntimeHardness(209,0,Owner,CanonicalError));
    const bool Admitted=G->AdmitRuntimeHardnessFromSourceFile(209,0,Owner,SelectedFile,Error);
    if(!TestTrue(FString(TEXT("actual baseline scene transaction: "))+Error,Admitted))return false;
    const bool Redrawn=G->RedrawRuntimeHardnessMap(209,Error);
    if(!TestTrue(FString(TEXT("actual full fitted redraw: "))+Error,Redrawn))return false;
    auto* Primitive=G->FindHardnessFitPrimitive(*D->FindSprite(Handle));if(!TestNotNull(TEXT("same-owner admitted exact fitted primitive"),Primitive))return false;
    TestTrue(TEXT("fitted visual aligned to script ground"),FamilyMesh->Bounds.GetBox().GetCenter().Equals(Primitive->Bounds.GetBox().GetCenter(),.1));
    const auto FitCells=G->HardnessProjection->Fits->Candidates[0].LogicalCells;
    if(!TestTrue(TEXT("nonempty fitted mask"),FitCells.Num()>0))return false;
    const auto Cell=FitCells[FitCells.Num()/2];TestEqual(TEXT("GetHard uses fitted owner113"),G->GetHard(209,Cell.X+20,Cell.Y),113);
    FHitResult Hit;const FCollisionShape Capsule=FCollisionShape::MakeCapsule(10,30);
    TestTrue(TEXT("Pawn capsule hits actual barrel"),W->SweepSingleByChannel(Hit,Ground+FVector(0,0,170),Ground+FVector(0,0,30),FQuat::Identity,ECC_Pawn,Capsule)&&Hit.GetComponent()==Primitive);
    W->LineTraceSingleByChannel(Hit,Ground+FVector(-180,0,150),Ground+FVector(180,0,150),ECC_Pawn);
    TestTrue(TEXT("no old300cm barrel wall above physical mesh"),Hit.GetComponent()!=Primitive);
    G->SetPlacementProp(Id,1);Primitive=G->FindHardnessFitPrimitive(*D->FindSprite(Handle));
    TestEqual(TEXT("accepted prop reads through immediately"),G->GetHard(209,Cell.X+20,Cell.Y),0);
    TestNotNull(TEXT("walkthrough retains exact inert interaction geometry"),Primitive);
    W->SweepSingleByChannel(Hit,Ground+FVector(0,0,170),Ground+FVector(0,0,30),FQuat::Identity,ECC_Pawn,Capsule);TestTrue(TEXT("prop removes barrel world blocking"),Hit.GetComponent()!=Primitive);
    if(Primitive)TestTrue(TEXT("actual direct sweep still queries inert cooked body"),Primitive->SweepComponent(Hit,Ground+FVector(0,0,170),Ground+FVector(0,0,30),FQuat::Identity,Capsule,true));
    G->SetPlacementProp(Id,0);TestEqual(TEXT("prop restore uses same logical epoch"),G->GetHard(209,Cell.X+20,Cell.Y),113);
    S=D->FindSprite(Handle);S->Props.Add(TEXT("hard"),1);G->RecordEditorHardness(Id,1);
    if(!TestTrue(TEXT("soft intact redraw"),G->RedrawRuntimeHardness(Handle,Error)))return false;
    TestTrue(TEXT("softness alone retains intact visual"),FamilyMesh->IsVisible()&&!FamilyMesh->bHiddenInGame);TestEqual(TEXT("softness clears old logical mask"),G->GetHard(209,Cell.X+20,Cell.Y),0);
    S=D->FindSprite(Handle);S->Props.Add(TEXT("seq"),173);S->Props.Add(TEXT("brain"),5);S->Props.Add(TEXT("nohit"),1);
    if(!TestTrue(TEXT("actual bar-f1 break state releases fitted body"),G->RedrawRuntimeHardness(Handle,Error)))return false;
    TestNull(TEXT("broken barrel has no fitted physical instance"),G->FindHardnessFitPrimitive(*D->FindSprite(Handle)));
    TestTrue(TEXT("broken barrel hides intact family and exposes card"),FamilyMesh->bHiddenInGame&&!FamilyMesh->IsVisible()&&!Actor->Card->bHiddenInGame);
    TestTrue(TEXT("broken redraw is idempotent"),G->RedrawRuntimeHardnessMap(209,Error));
    Story->GetWorldState()->SetOverride(Id,EDinkOverrideType::BackgroundNoHardness);
    G->EditorHardnessPicture(Id,true,173);G->EditorHardnessPicture(Id,false,6);
    S=D->FindSprite(Handle);S->Props.Add(TEXT("pframe"),6);S->Props.Add(TEXT("seq"),0);S->Props.Add(TEXT("brain"),0);
    if(!TestTrue(TEXT("persisted broken173/6 source projection"),G->RedrawRuntimeHardnessMap(209,Error)))return false;
    TestTrue(TEXT("persisted broken background never restores intact family"),FamilyMesh->bHiddenInGame&&!FamilyMesh->IsVisible());
    TestEqual(TEXT("persisted broken background stays nonblocking"),G->GetHard(209,Cell.X+20,Cell.Y),0);
    TestTrue(TEXT("immutable floor unchanged"),Floor->GetComponentTransform().Equals(FloorTransform,0)&&Floor->GetCollisionResponseToChannels()==FloorResponses&&Floor->GetStaticMesh()==Fixed);
    TestTrue(TEXT("script/drop coordinates and original source identity preserved"),D->FindSprite(Handle)->X==Placement->X&&D->FindSprite(Handle)->Y==Placement->Y&&Actor->Origin->OriginId==Id);
    // Leave a real owned body active to exercise production shutdown, rather
    // than qualifying cleanup only after a final empty broken-barrel map.
    const int32 Extra=D->CreateVirtualSprite(209,Placement->X+70,Placement->Y);
    auto* ExtraSprite=D->FindSprite(Extra);ExtraSprite->Props.Add(TEXT("pseq"),173);ExtraSprite->Props.Add(TEXT("pframe"),1);ExtraSprite->Props.Add(TEXT("hard"),0);
    if(!TestTrue(TEXT("prepare controlled final registered body for shutdown lifetime proof"),G->RedrawRuntimeHardnessMap(209,Error))){AddError(Error);return false;}
    return true;
}
