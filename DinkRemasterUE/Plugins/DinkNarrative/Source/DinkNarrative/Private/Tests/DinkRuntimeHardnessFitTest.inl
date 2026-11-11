// Included by the production adapter only in automation builds so this fixture
// can inspect its private published epoch without exposing an admission bypass.
#include "Misc/AutomationTest.h"
#include "Misc/App.h"
#include "Misc/ScopeExit.h"
#include "Misc/Guid.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Engine/GameInstance.h"
#include "Greybox/DinkScreenVolume.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "Engine/Texture2D.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceConstant.h"
#include "UObject/Package.h"
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
    auto* Barrel=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.SM_Barrel_Oak_01"));
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
    Actor->ScreenNumber=209;Actor->Origin->PlacementType=Placement->Type;Actor->Origin->OriginId=Id;Actor->Origin->Sequence=173;Actor->Origin->Frame=1;Actor->Origin->ScriptName=TEXT("bar-f1");Actor->Origin->ClassId=TEXT("barrel");Actor->Origin->SourceHash=FString::ChrN(40,TEXT('a'));
    Actor->GetRootComponent()->SetMobility(EComponentMobility::Movable);Actor->Card->SetMobility(EComponentMobility::Movable);Actor->FinishSpawning(FTransform(Ground));Actor->Tags.Add(UDinkArtFamilySubsystem::FamilyTag);
    auto* CardMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Dink/_Generated/Shared/SM_DinkCard.SM_DinkCard"));
    auto* IntactMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Dink/_Generated/Sprites/MI_Sprite_173_01.MI_Sprite_173_01"));
    if(!TestNotNull(TEXT("ordinary imported source card mesh"),CardMesh)||!TestNotNull(TEXT("ordinary imported source picture"),IntactMaterial))return false;
    Actor->ImportedCardRelativeTransform=FTransform(FQuat::Identity,FVector(-13,0,-11),FVector(.56,1,.55));Actor->bHasImportedCardBaseline=true;
    Actor->Card->SetRelativeTransform(Actor->ImportedCardRelativeTransform);Actor->Card->SetMaterial(0,IntactMaterial);
    Actor->Card->SetStaticMesh(CardMesh);Actor->Card->SetCollisionEnabled(ECollisionEnabled::NoCollision);Actor->Card->SetCanEverAffectNavigation(false);Actor->Card->SetGenerateOverlapEvents(false);Actor->Card->SetHiddenInGame(true);
    auto* FamilyMesh=NewObject<UStaticMeshComponent>(Actor);Actor->AddInstanceComponent(FamilyMesh);FamilyMesh->SetupAttachment(Actor->GetRootComponent());FamilyMesh->SetMobility(EComponentMobility::Movable);FamilyMesh->SetStaticMesh(Barrel);FamilyMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);FamilyMesh->SetCanEverAffectNavigation(false);FamilyMesh->SetGenerateOverlapEvents(false);FamilyMesh->ComponentTags.Add(UDinkArtFamilySubsystem::FamilyTag);FamilyMesh->SetRelativeLocation(FVector(89,0,0));FamilyMesh->RegisterComponent();
    auto* Families=W->GetSubsystem<UDinkArtFamilySubsystem>();if(!TestNotNull(TEXT("family subsystem"),Families))return false;
    // Exercise the same native loader used before visual CVar gates, using
    // only this fixture's private temporary files (never rename shipped Data).
    const FString PolicyDir=FPaths::ProjectSavedDir()/TEXT("Automation/FamilyPolicyLoad")/FGuid::NewGuid().ToString(EGuidFormats::Digits);
    IFileManager::Get().MakeDirectory(*PolicyDir,true);
    ON_SCOPE_EXIT {IFileManager::Get().DeleteDirectory(*PolicyDir,false,true);};
    FString PolicyText,PolicyError;
    Families->CollisionFitRules.AddDefaulted(); // failed reload must clear stale rows
    if(!TestFalse(TEXT("missing mandatory policy file refuses native load"),Families->LoadCollisionFitPolicy(PolicyDir/TEXT("missing.json"),PolicyText,PolicyError))||
       !TestTrue(TEXT("missing policy records unavailable authority"),Families->HasCollisionFitPolicyError())||
       !TestTrue(TEXT("failed load clears previous fit requests"),Families->GetCollisionFitRules().IsEmpty()))return false;
    FDinkSprite PolicySprite;PolicySprite.Screen=209;PolicySprite.Origin=Id;
    FDinkHardnessFitSet PolicyFits;std::vector<DinkHardness::Stamp> PolicyRuns;bool PolicyReplaced=false;
    if(!TestFalse(TEXT("runtime prepare refuses missing policy instead of taking nonfit fallback"),G->PrepareHardnessFit(PolicySprite,101,true,PolicyFits,PolicyRuns,PolicyReplaced,PolicyError))||
       !TestTrue(TEXT("policy refusal publishes no fitted bodies"),PolicyFits.Bodies.empty()))return false;
    const FString LegacyFile=PolicyDir/TEXT("present_legacy.json");
    if(!TestTrue(TEXT("write owned valid no-policy legacy control"),FFileHelper::SaveStringToFile(TEXT(R"({"schema":"dink-art-families/1","families":[]})"),*LegacyFile)))return false;
    if(!TestTrue(TEXT("present valid file with absent optional policy remains legacy"),Families->LoadCollisionFitPolicy(LegacyFile,PolicyText,PolicyError))||
       !TestTrue(TEXT("successful legacy reload clears prior failure diagnostic"),PolicyError.IsEmpty())||
       !TestFalse(TEXT("loaded legacy policy is not unavailable"),Families->HasCollisionFitPolicyError())||
       !TestTrue(TEXT("loaded legacy policy activates no fits"),Families->GetCollisionFitRules().IsEmpty())||
       !TestTrue(TEXT("loaded legacy policy permits ordinary nonfit prepare"),G->PrepareHardnessFit(PolicySprite,101,true,PolicyFits,PolicyRuns,PolicyReplaced,PolicyError))||
       !TestFalse(TEXT("legacy control did not replace source geometry"),PolicyReplaced))return false;
    {
        IConsoleVariable* Visual=IConsoleManager::Get().FindConsoleVariable(TEXT("dink.FamilyArt"));
        if(!TestNotNull(TEXT("family visual toggle exists"),Visual))return false;
        const int32 Previous=Visual->GetInt();
        ON_SCOPE_EXIT {Visual->SetWithCurrentPriority(Previous);};
        Visual->SetWithCurrentPriority(0);
        if(!TestEqual(TEXT("visual toggle is actually off for loader control"),Visual->GetInt(),0))return false;
        Families->OnWorldBeginPlay(*W);
        if(!TestFalse(TEXT("disabled optional graphics still loads collision policy"),Families->HasCollisionFitPolicyError())||
           !TestTrue(TEXT("disabled graphics cannot erase requested fits"),Families->IsCollisionFitRequested(Id)))return false;
    }
    FDinkFamilyFittedGeometry Geometry;if(!TestTrue(TEXT("actual cooked complex geometry"),DinkFamilyCollisionFit::ReadCookedGeometry(*Barrel,Geometry,Error)))return false;
    Families->bReady=true;Families->bCollisionFitPolicyError=false;Families->Precedence={};Families->Bindings.Reset();Families->CollisionFitRules.Reset();
    FDinkFamilyBinding Binding;Binding.Family=TEXT("barrel");Binding.ClassId=TEXT("barrel");Binding.Mesh=Barrel->GetPathName();Binding.Fit=EDinkFamilyFit::None;Binding.bScripted=true;Families->Bindings.Add(Binding);
    FDinkFamilyCollisionFitRule ActiveRule;
    ActiveRule.Origin=Id;ActiveRule.Mesh=Barrel->GetPathName();
    ActiveRule.CanonicalSurfaceSha1=Geometry.CanonicalSurfaceSha1;
    ActiveRule.SourceHash=Actor->Origin->SourceHash;ActiveRule.SourceScript=TEXT("bar-f1");
    Families->CollisionFitRules.Add(ActiveRule);
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
    auto RedrawFailure=[&](const TCHAR* Phase,const FString& Failure)
    {
        // Failure-only readback AFTER the unchanged redraw. No query/admission/slot allocation.
        const FString Reason=Failure;AddError(Reason.IsEmpty()?TEXT("Redraw returned false with no Error"):Reason);
        auto O=MakeShared<FJsonObject>();O->SetStringField(TEXT("phase"),Phase);O->SetStringField(TEXT("error"),Reason);O->SetBoolField(TEXT("hardness_loading"),G->IsHardnessLoading());
        auto V=[](const FVector& P){return FString::Printf(TEXT("%.17g,%.17g,%.17g"),P.X,P.Y,P.Z);};
        auto Pose=[&](const FTransform& T){auto R=MakeShared<FJsonObject>();const auto Q=T.GetRotation();R->SetStringField(TEXT("translation_xyz"),V(T.GetTranslation()));R->SetStringField(TEXT("scale_xyz"),V(T.GetScale3D()));R->SetStringField(TEXT("quaternion_xyzw"),FString::Printf(TEXT("%.17g,%.17g,%.17g,%.17g"),Q.X,Q.Y,Q.Z,Q.W));return R;};
        O->SetNumberField(TEXT("effective_source_type"),G->EffectiveHardnessPlacementType(*Placement));
        O->SetObjectField(TEXT("actor_world"),Pose(Actor->GetActorTransform()));O->SetObjectField(TEXT("imported_baseline"),Pose(Actor->ImportedCardRelativeTransform));
        O->SetObjectField(TEXT("card_relative"),Pose(Actor->Card->GetRelativeTransform()));O->SetBoolField(TEXT("card_visible"),Actor->Card->IsVisible());O->SetBoolField(TEXT("card_hidden"),Actor->Card->bHiddenInGame);O->SetStringField(TEXT("card_material"),GetPathNameSafe(Actor->Card->GetMaterial(0)));
        TArray<TSharedPtr<FJsonValue>> Sprites,Releases;int32 Active=0,Inactive=0;
        for(const auto& Pair:D->GetSprites())if(Pair.Value.Origin==Id)
        {
            const auto& Sprite=Pair.Value;if(Sprite.bActive)++Active;else++Inactive;auto R=MakeShared<FJsonObject>();
            R->SetNumberField(TEXT("handle"),Sprite.Handle);R->SetBoolField(TEXT("active"),Sprite.bActive);R->SetNumberField(TEXT("seq"),Sprite.GetProp(TEXT("seq")));R->SetNumberField(TEXT("brain"),Sprite.GetProp(TEXT("brain")));R->SetNumberField(TEXT("nohit"),Sprite.GetProp(TEXT("nohit")));R->SetNumberField(TEXT("pseq"),Sprite.GetProp(TEXT("pseq")));R->SetNumberField(TEXT("pframe"),Sprite.GetProp(TEXT("pframe")));R->SetStringField(TEXT("script"),Sprite.Script.ToString());Sprites.Add(MakeShared<FJsonValueObject>(R));
        }
        O->SetNumberField(TEXT("origin_active_sprites"),Active);O->SetNumberField(TEXT("origin_inactive_sprites"),Inactive);O->SetArrayField(TEXT("sprites"),Sprites);
        if(G->HardnessProjection&&G->HardnessProjection->Fits)
        {
            const auto& Fits=*G->HardnessProjection->Fits;O->SetNumberField(TEXT("candidate_count"),Fits.Candidates.Num());O->SetNumberField(TEXT("release_count"),Fits.Releases.Num());O->SetNumberField(TEXT("body_count"),Fits.Bodies.size());
            for(int32 I=0;I<Fits.Releases.Num();++I)
            {
                const auto& C=Fits.Releases[I];auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("origin"),C.Origin.ToString());R->SetBoolField(TEXT("prepared"),C.bReleasePicturePrepared);R->SetObjectField(TEXT("expected_relative"),Pose(C.ReleaseCardRelative));R->SetStringField(TEXT("expected_material"),C.ReleaseMaterial?GetPathNameSafe(C.ReleaseMaterial->Get()):FString());
                if(C.Card.IsValid())
                {
                    const auto* Card=C.Card.Get();const auto Actual=Card->GetRelativeTransform();const auto ActualWorld=Card->GetComponentTransform();
                    R->SetObjectField(TEXT("actual_relative"),Pose(Actual));R->SetObjectField(TEXT("actual_card_world"),Pose(ActualWorld));
                    R->SetBoolField(TEXT("relative_exact"),Actual.Equals(C.ReleaseCardRelative,0));R->SetBoolField(TEXT("translation_exact"),Actual.GetTranslation().Equals(C.ReleaseCardRelative.GetTranslation(),0));R->SetBoolField(TEXT("rotation_exact"),Actual.GetRotation().Equals(C.ReleaseCardRelative.GetRotation(),0));R->SetBoolField(TEXT("scale_exact"),Actual.GetScale3D().Equals(C.ReleaseCardRelative.GetScale3D(),0));
                    const auto* Parent=Card->GetAttachParent();const auto* Root=Actor->GetRootComponent();
                    R->SetStringField(TEXT("attach_parent"),GetPathNameSafe(Parent));R->SetStringField(TEXT("attach_socket"),Card->GetAttachSocketName().ToString());R->SetStringField(TEXT("actor_root"),GetPathNameSafe(Root));
                    R->SetBoolField(TEXT("parent_is_actor_root"),Parent&&Parent==Root);R->SetBoolField(TEXT("absolute_location"),Card->IsUsingAbsoluteLocation());R->SetBoolField(TEXT("absolute_rotation"),Card->IsUsingAbsoluteRotation());R->SetBoolField(TEXT("absolute_scale"),Card->IsUsingAbsoluteScale());
                    const bool RelativeCompositionApplies=!Card->IsUsingAbsoluteLocation()&&!Card->IsUsingAbsoluteRotation()&&!Card->IsUsingAbsoluteScale();
                    R->SetBoolField(TEXT("relative_composition_applies"),RelativeCompositionApplies);
                    if(Root){const auto RootWorld=Root->GetComponentTransform();const auto Requested=C.ReleaseCardRelative*RootWorld;R->SetObjectField(TEXT("actor_root_world"),Pose(RootWorld));R->SetObjectField(TEXT("requested_world_via_actor_root"),Pose(Requested));R->SetBoolField(TEXT("world_exact_via_actor_root"),RelativeCompositionApplies&&Parent==Root&&Card->GetAttachSocketName().IsNone()&&ActualWorld.Equals(Requested,0));}
                    if(Parent){const auto ParentWorld=Parent->GetComponentTransform();const auto ParentSocketWorld=Parent->GetSocketTransform(Card->GetAttachSocketName(),RTS_World);const auto Requested=C.ReleaseCardRelative*ParentWorld;const auto SocketRequested=C.ReleaseCardRelative*ParentSocketWorld;R->SetObjectField(TEXT("attach_parent_world"),Pose(ParentWorld));R->SetObjectField(TEXT("attach_parent_socket_world"),Pose(ParentSocketWorld));R->SetObjectField(TEXT("requested_world_via_actual_parent"),Pose(Requested));R->SetObjectField(TEXT("requested_world_via_parent_socket"),Pose(SocketRequested));R->SetBoolField(TEXT("world_exact_via_actual_parent"),RelativeCompositionApplies&&Card->GetAttachSocketName().IsNone()&&ActualWorld.Equals(Requested,0));R->SetBoolField(TEXT("world_exact_via_parent_socket"),RelativeCompositionApplies&&ActualWorld.Equals(SocketRequested,0));}
                }
                if(Fits.ReleaseStates.IsValidIndex(I)){const auto& State=Fits.ReleaseStates[I];R->SetBoolField(TEXT("prebirth"),State.bPrebirth);R->SetBoolField(TEXT("active"),State.bActive);R->SetNumberField(TEXT("runtime_handle"),State.RuntimeHandle);R->SetNumberField(TEXT("frame"),State.DisplayedFrame);}
                Releases.Add(MakeShared<FJsonValueObject>(R));
            }
        }
        O->SetArrayField(TEXT("releases"),Releases);FString Text;const FString Dir=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Automation/ReleasedPictureRedraw"));IFileManager::Get().MakeDirectory(*Dir,true);const FString File=Dir/(FGuid::NewGuid().ToString(EGuidFormats::Digits)+TEXT(".json"));
        const bool Written=FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Text))&&FFileHelper::SaveStringToFile(Text,*File,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_NoReplaceExisting);
        AddInfo(FString::Printf(TEXT("redraw diagnostic receipt=%s written=%d payload=%s"),*File,Written,*Text));
    };
    const bool Redrawn=G->RedrawRuntimeHardnessMap(209,Error);
    if(!TestTrue(FString(TEXT("actual full fitted redraw: "))+Error,Redrawn)){RedrawFailure(TEXT("actual full fitted redraw"),Error);return false;}
    auto* Primitive=G->FindHardnessFitPrimitive(*D->FindSprite(Handle));if(!TestNotNull(TEXT("same-owner admitted exact fitted primitive"),Primitive))return false;
    TestTrue(TEXT("fitted visual aligned to script ground"),FamilyMesh->Bounds.GetBox().GetCenter().Equals(Primitive->Bounds.GetBox().GetCenter(),.1));
    const auto FrozenCard=Actor->Card->GetRelativeTransform();Actor->Card->AddLocalOffset(FVector(1,0,0));
    TestNull(TEXT("explicit intact card pose tamper still refuses fit"),G->FindHardnessFitPrimitive(*D->FindSprite(Handle)));
    Actor->Card->SetRelativeTransform(FrozenCard);
    TestNotNull(TEXT("restoring exact card epoch requalifies fit"),G->FindHardnessFitPrimitive(*D->FindSprite(Handle)));
    const auto FrozenBaseline=Actor->ImportedCardRelativeTransform;Actor->ImportedCardRelativeTransform.AddToTranslation(FVector(1,0,0));
    TestNull(TEXT("immutable imported baseline tamper still refuses admitted fit"),G->FindHardnessFitPrimitive(*D->FindSprite(Handle)));
    Actor->ImportedCardRelativeTransform=FrozenBaseline;
    TestNotNull(TEXT("restored source baseline requalifies admitted fit"),G->FindHardnessFitPrimitive(*D->FindSprite(Handle)));
    auto BrokenPictureState=G->HardnessProjection->Fits->Candidates[0].Sprite;
    BrokenPictureState.DisplayedFrame=6;BrokenPictureState.DisplayedPicture.Frame=6;
    if(const auto* F=G->Data.FindFrame(173,6))
    {auto& P=BrokenPictureState.DisplayedPicture;P.Width=F->Width;P.Height=F->Height;P.OriginX=F->OriginX;P.OriginY=F->OriginY;P.Sha1=F->PictureDescriptorSha1;}
    FDinkFamilyCollisionFitCandidate PreparedPicture;
    const bool PicturePrepared=Families->PrepareCollisionFitReleaseCandidate(Id,BrokenPictureState,PreparedPicture,Error);
    if(PicturePrepared)
    {
        // Characterize real fixture assets AFTER the unchanged prepare; surface availability is not an admission condition.
        for(UTexture* T:{PreparedPicture.SourcePictureTexture->Get(),PreparedPicture.ReleaseTexture->Get()})
        {
            const auto* Texture2D=Cast<UTexture2D>(T);const FIntPoint Imported=Texture2D?Texture2D->GetImportedSize():FIntPoint::ZeroValue;
            AddInfo(FString::Printf(TEXT("release picture asset=%s class=%s imported=%d,%d platformSurface=%.17g,%.17g canEverRender=%d"),
                *GetPathNameSafe(T),T?*T->GetClass()->GetPathName():TEXT("None"),Imported.X,Imported.Y,T?double(T->GetSurfaceWidth()):0,T?double(T->GetSurfaceHeight()):0,FApp::CanEverRender()));
        }
    }
    if(!PicturePrepared)
    {
        // Failure-only observation AFTER the real unchanged prepare path. Never finish async compilation here.
        auto Facts=MakeShared<FJsonObject>();Facts->SetStringField(TEXT("prepare_error"),Error);Facts->SetStringField(TEXT("actor"),Actor->GetPathName());
        Facts->SetBoolField(TEXT("baseline_present"),Actor->bHasImportedCardBaseline);
        auto Pose=[](const FTransform& T){auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("translation"),T.GetTranslation().ToString());R->SetStringField(TEXT("rotation"),T.GetRotation().ToString());R->SetStringField(TEXT("scale"),T.GetScale3D().ToString());return R;};
        Facts->SetObjectField(TEXT("imported_baseline"),Pose(Actor->ImportedCardRelativeTransform));Facts->SetObjectField(TEXT("card_relative"),Pose(Actor->Card->GetRelativeTransform()));
        Facts->SetObjectField(TEXT("card_world"),Pose(Actor->Card->GetComponentTransform()));Facts->SetBoolField(TEXT("card_world_upright"),Actor->Card->GetComponentQuat().GetUpVector().Equals(FVector::UpVector,0));
        Facts->SetStringField(TEXT("origin"),Actor->Origin->OriginId.ToString());Facts->SetStringField(TEXT("source_hash"),Actor->Origin->SourceHash);Facts->SetNumberField(TEXT("source_seq"),Actor->Origin->Sequence);Facts->SetNumberField(TEXT("source_frame"),Actor->Origin->Frame);
        auto Picture=[](const FDinkLegacyPictureDescriptor& P)
        {
            auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("sequence"),P.Sequence);R->SetNumberField(TEXT("frame"),P.Frame);R->SetNumberField(TEXT("width"),P.Width);R->SetNumberField(TEXT("height"),P.Height);
            R->SetNumberField(TEXT("origin_x"),P.OriginX);R->SetNumberField(TEXT("origin_y"),P.OriginY);R->SetStringField(TEXT("descriptor_sha1"),P.Sha1);R->SetBoolField(TEXT("descriptor_valid"),DinkFamilyCollisionFit::ValidatePictureDescriptor(P));
            const FString Key=FString::Printf(TEXT("%d_%02d"),P.Sequence,P.Frame);const FString ExpectedMI=FString::Printf(TEXT("/Game/Dink/_Generated/Sprites/MI_Sprite_%s.MI_Sprite_%s"),*Key,*Key);
            const FString ExpectedTex=FString::Printf(TEXT("/Game/Dink/_Generated/Sprites/T_Sprite_%s.T_Sprite_%s"),*Key,*Key);
            R->SetStringField(TEXT("expected_material"),ExpectedMI);R->SetStringField(TEXT("expected_texture"),ExpectedTex);auto* MI=LoadObject<UMaterialInterface>(nullptr,*ExpectedMI);UTexture* Tex=nullptr;
            R->SetStringField(TEXT("actual_material"),GetPathNameSafe(MI));R->SetStringField(TEXT("material_class"),MI?MI->GetClass()->GetPathName():FString());
            R->SetBoolField(TEXT("tex_parameter_found"),MI&&MI->GetTextureParameterValue(FMaterialParameterInfo(TEXT("Tex")),Tex));R->SetStringField(TEXT("actual_texture"),GetPathNameSafe(Tex));R->SetStringField(TEXT("texture_class"),Tex?Tex->GetClass()->GetPathName():FString());
            if(const auto* Texture2D=Cast<UTexture2D>(Tex))
            {const FIntPoint Imported=Texture2D->GetImportedSize();R->SetNumberField(TEXT("imported_width"),Imported.X);R->SetNumberField(TEXT("imported_height"),Imported.Y);}
            if(Tex)
            {
                #if WITH_EDITOR
                R->SetBoolField(TEXT("is_compiling_before_dimensions"),Tex->IsCompiling());
                #endif
                R->SetNumberField(TEXT("surface_width"),Tex->GetSurfaceWidth());R->SetNumberField(TEXT("surface_height"),Tex->GetSurfaceHeight());
                R->SetNumberField(TEXT("expected_resampled_width"),FMath::Min(1024u,FMath::RoundUpToPowerOfTwo(uint32(P.Width))));R->SetNumberField(TEXT("expected_resampled_height"),FMath::Min(1024u,FMath::RoundUpToPowerOfTwo(uint32(P.Height))));
                #if WITH_EDITOR
                R->SetBoolField(TEXT("is_compiling_after_dimensions"),Tex->IsCompiling());
                #endif
                #if WITH_EDITORONLY_DATA
                if(const auto* T2D=Cast<UTexture2D>(Tex)){R->SetNumberField(TEXT("source_width"),T2D->Source.GetSizeX());R->SetNumberField(TEXT("source_height"),T2D->Source.GetSizeY());}
                #endif
            }
            return R;
        };
        Facts->SetObjectField(TEXT("source_picture"),Picture(BrokenPictureState.SourcePicture));Facts->SetObjectField(TEXT("displayed_picture"),Picture(BrokenPictureState.DisplayedPicture));
        const FString Dir=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Automation/ReleasedPicturePreflight"));IFileManager::Get().MakeDirectory(*Dir,true);
        const FString File=Dir/(FGuid::NewGuid().ToString(EGuidFormats::Digits)+TEXT(".json"));FString Text;
        const bool Written=FJsonSerializer::Serialize(Facts,TJsonWriterFactory<>::Create(&Text))&&FFileHelper::SaveStringToFile(Text,*File,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_NoReplaceExisting);
        AddInfo(FString::Printf(TEXT("release preflight diagnostic receipt=%s written=%d payload=%s"),*File,Written,*Text));
    }
    if(!TestTrue(FString(TEXT("actual source173/6 release picture preflights before mutation: "))+Error,PicturePrepared))return false;
    #if WITH_EDITOR
    if(auto* TargetMI=Cast<UMaterialInstanceConstant>(PreparedPicture.ReleaseMaterial->Get()))
    {
        UTexture* OriginalTex=PreparedPicture.ReleaseTexture->Get();const bool WasDirty=TargetMI->GetOutermost()->IsDirty();
        ON_SCOPE_EXIT {TargetMI->SetTextureParameterValueEditorOnly(FMaterialParameterInfo(TEXT("Tex")),OriginalTex);TargetMI->GetOutermost()->SetDirtyFlag(WasDirty);};
        const auto BeforeRejected=Actor->Card->GetRelativeTransform();auto* BeforeMaterial=Actor->Card->GetMaterial(0);
        TargetMI->SetTextureParameterValueEditorOnly(FMaterialParameterInfo(TEXT("Tex")),PreparedPicture.SourcePictureTexture->Get());
        TestFalse(TEXT("postprepare target Tex mutation refuses actual publication validator"),DinkFamilyCollisionFit::ValidateReleasedPictureAssets(PreparedPicture,Error));
        TestTrue(TEXT("rejected target Tex mutation leaves card untouched"),Actor->Card->GetRelativeTransform().Equals(BeforeRejected,0)&&Actor->Card->GetMaterial(0)==BeforeMaterial&&Actor->Card->bHiddenInGame);
        TargetMI->SetTextureParameterValueEditorOnly(FMaterialParameterInfo(TEXT("Tex")),OriginalTex);
        TestTrue(TEXT("restored exact target Tex requalifies"),DinkFamilyCollisionFit::ValidateReleasedPictureAssets(PreparedPicture,Error));
    }
    else AddError(TEXT("expected ordinary target material instance for Tex mutation control"));
    #endif
    Actor->bHasImportedCardBaseline=false;
    TestFalse(TEXT("old missing importer baseline refuses broken publication"),Families->PrepareCollisionFitReleaseCandidate(Id,BrokenPictureState,PreparedPicture,Error));
    Actor->bHasImportedCardBaseline=true;
    auto BadPicture=BrokenPictureState;BadPicture.DisplayedPicture.OriginX++;
    TestFalse(TEXT("tampered canonical frame pivot refuses before mutation"),Families->PrepareCollisionFitReleaseCandidate(Id,BadPicture,PreparedPicture,Error));
    BadPicture=BrokenPictureState;BadPicture.DisplayedPicture.Frame=1;
    TestFalse(TEXT("wrong frame descriptor never exposes intact173/1 fallback"),Families->PrepareCollisionFitReleaseCandidate(Id,BadPicture,PreparedPicture,Error));
    TestTrue(TEXT("negative picture preparation left card hidden and exact"),Actor->Card->GetRelativeTransform().Equals(FrozenCard,0)&&Actor->Card->bHiddenInGame);
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
    const bool SoftRedrawn=G->RedrawRuntimeHardness(Handle,Error);
    if(!TestTrue(TEXT("soft intact redraw"),SoftRedrawn)){RedrawFailure(TEXT("soft intact redraw"),Error);return false;}
    TestTrue(TEXT("softness alone retains intact visual"),FamilyMesh->IsVisible()&&!FamilyMesh->bHiddenInGame);TestEqual(TEXT("softness clears old logical mask"),G->GetHard(209,Cell.X+20,Cell.Y),0);
    Actor->Card->SetMobility(EComponentMobility::Static);
    TestTrue(TEXT("release starts with a registered static imported card"),Actor->Card->IsRegistered()&&Actor->Card->Mobility==EComponentMobility::Static);
    S=D->FindSprite(Handle);S->Props.Add(TEXT("seq"),173);S->Props.Add(TEXT("brain"),5);S->Props.Add(TEXT("nohit"),1);
    const bool BreakRedrawn=G->RedrawRuntimeHardness(Handle,Error);
    if(!TestTrue(TEXT("actual bar-f1 break state releases fitted body"),BreakRedrawn)){RedrawFailure(TEXT("actual bar-f1 break state releases fitted body"),Error);return false;}
    TestNull(TEXT("broken barrel has no fitted physical instance"),G->FindHardnessFitPrimitive(*D->FindSprite(Handle)));
    TestTrue(TEXT("broken barrel hides intact family and exposes card"),FamilyMesh->bHiddenInGame&&!FamilyMesh->IsVisible()&&!Actor->Card->bHiddenInGame);
    TestTrue(TEXT("actual release makes only noncolliding card movable for projection"),Actor->Card->Mobility==EComponentMobility::Movable&&Actor->Card->GetCollisionEnabled()==ECollisionEnabled::NoCollision&&!Actor->Card->CanEverAffectNavigation()&&!Actor->Card->GetGenerateOverlapEvents());
    const bool FirstBrokenRepeat=G->RedrawRuntimeHardnessMap(209,Error);
    if(!TestTrue(TEXT("broken redraw is idempotent"),FirstBrokenRepeat)){RedrawFailure(TEXT("broken redraw is idempotent"),Error);}
    Story->GetWorldState()->SetOverride(Id,EDinkOverrideType::BackgroundNoHardness);
    G->EditorHardnessPicture(Id,true,173);G->EditorHardnessPicture(Id,false,6);
    S=D->FindSprite(Handle);S->Props.Add(TEXT("pframe"),6);S->Props.Add(TEXT("seq"),0);S->Props.Add(TEXT("brain"),0);
    const bool PersistedBroken=G->RedrawRuntimeHardnessMap(209,Error);
    if(!TestTrue(TEXT("persisted broken173/6 source projection"),PersistedBroken)){RedrawFailure(TEXT("persisted broken173/6 source projection"),Error);return false;}
    TestTrue(TEXT("persisted broken background never restores intact family"),FamilyMesh->bHiddenInGame&&!FamilyMesh->IsVisible());
    TestEqual(TEXT("persisted broken picture projects actual173/6 material"),Actor->Card->GetMaterial(0)->GetPathName(),FString(TEXT("/Game/Dink/_Generated/Sprites/MI_Sprite_173_06.MI_Sprite_173_06")));
    TestTrue(TEXT("persisted broken picture uses source dimensions/pivot"),Actor->Card->GetRelativeTransform().Equals(FTransform(FQuat::Identity,FVector(1,0,-20),FVector(.84,1,.64)),1.e-12));
    const auto FirstBrokenPose=Actor->Card->GetRelativeTransform();auto* FirstBrokenMaterial=Actor->Card->GetMaterial(0);
    const bool RepeatedBroken=G->RedrawRuntimeHardnessMap(209,Error);
    if(!TestTrue(TEXT("repeated broken-load source redraw succeeds"),RepeatedBroken)){RedrawFailure(TEXT("repeated broken-load source redraw succeeds"),Error);}
    TestTrue(TEXT("repeated broken picture geometry/material never compound"),Actor->Card->GetRelativeTransform().Equals(FirstBrokenPose,0)&&Actor->Card->GetMaterial(0)==FirstBrokenMaterial);
    const auto ReleasedBefore=Actor->Card->GetRelativeTransform();
    const auto ReleaseState=G->HardnessProjection->Fits->ReleaseStates.Last();
    Actor->Card->AddLocalOffset(FVector(1,0,0));
    TestFalse(TEXT("published broken card position tamper refuses next release"),Families->PrepareCollisionFitReleaseCandidate(Id,ReleaseState,PreparedPicture,Error));
    Actor->Card->SetRelativeTransform(ReleasedBefore);
    Actor->Card->SetRelativeRotation(FRotator(10,0,0));
    TestFalse(TEXT("released non-yaw card rotation refuses rather than being legitimized"),Families->PrepareCollisionFitReleaseCandidate(Id,ReleaseState,PreparedPicture,Error));
    Actor->Card->SetRelativeTransform(ReleasedBefore);
    Actor->ImportedCardRelativeTransform.AddToTranslation(FVector(1,0,0));
    TestFalse(TEXT("released immutable source baseline tamper refuses"),Families->PrepareCollisionFitReleaseCandidate(Id,ReleaseState,PreparedPicture,Error));
    Actor->ImportedCardRelativeTransform=FrozenBaseline;
    Actor->Card->SetMaterial(0,IntactMaterial);
    TestFalse(TEXT("published broken card wrong material refuses next release"),Families->PrepareCollisionFitReleaseCandidate(Id,ReleaseState,PreparedPicture,Error));
    Actor->Card->SetMaterial(0,Actor->PublishedLegacyCardMaterial);
    TestTrue(TEXT("restored released epoch requalifies exact picture"),Families->PrepareCollisionFitReleaseCandidate(Id,ReleaseState,PreparedPicture,Error));
    TestEqual(TEXT("persisted broken background stays nonblocking"),G->GetHard(209,Cell.X+20,Cell.Y),0);
    TestTrue(TEXT("immutable floor unchanged"),Floor->GetComponentTransform().Equals(FloorTransform,0)&&Floor->GetCollisionResponseToChannels()==FloorResponses&&Floor->GetStaticMesh()==Fixed);
    TestTrue(TEXT("script/drop coordinates and original source identity preserved"),D->FindSprite(Handle)->X==Placement->X&&D->FindSprite(Handle)->Y==Placement->Y&&Actor->Origin->OriginId==Id);
    // Model the strict persisted restore boundary using the actual source override/picture APIs.
    Story->GetWorldState()->ClearOverride(Id);G->EditorHardnessPicture(Id,true,173);G->EditorHardnessPicture(Id,false,1);
    S=D->FindSprite(Handle);S->Props.Add(TEXT("pframe"),1);S->Props.Add(TEXT("hard"),0);S->Props.Add(TEXT("nohit"),0);
    G->RecordEditorHardness(Id,0);
    const bool RestoredIntact=G->RedrawRuntimeHardnessMap(209,Error);
    if(!TestTrue(TEXT("intact source restore after repeated broken presentation"),RestoredIntact)){RedrawFailure(TEXT("intact source restore after repeated broken presentation"),Error);return false;}
    TestNotNull(TEXT("intact restore reintroduces actual fitted body"),G->FindHardnessFitPrimitive(*D->FindSprite(Handle)));
    TestTrue(TEXT("intact restore hides legacy card and shows family"),Actor->Card->bHiddenInGame&&FamilyMesh->IsVisible()&&!FamilyMesh->bHiddenInGame);
    TestEqual(TEXT("intact restore retains immutable source picture identity"),Actor->Origin->Frame,1);
    // Leave a real owned body active to exercise production shutdown, rather
    // than qualifying cleanup only after a final empty broken-barrel map.
    const int32 Extra=D->CreateVirtualSprite(209,Placement->X+70,Placement->Y);
    auto* ExtraSprite=D->FindSprite(Extra);ExtraSprite->Props.Add(TEXT("pseq"),173);ExtraSprite->Props.Add(TEXT("pframe"),1);ExtraSprite->Props.Add(TEXT("hard"),0);
    const bool ShutdownRedrawn=G->RedrawRuntimeHardnessMap(209,Error);
    if(!TestTrue(TEXT("prepare controlled final registered body for shutdown lifetime proof"),ShutdownRedrawn)){RedrawFailure(TEXT("prepare controlled final registered body for shutdown lifetime proof"),Error);return false;}
    return true;
}
