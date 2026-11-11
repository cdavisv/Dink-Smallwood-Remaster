// Included by the production adapter only in automation builds so this fixture
// can inspect its private published epoch without exposing an admission bypass.
#include "Misc/AutomationTest.h"
#include <cmath>
#include <limits>
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
#include "Materials/Material.h"
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
    const int Handle=D->CreateVirtualSprite(209,Placement->X,Placement->Y);auto* S=D->FindSprite(Handle);S->Actor=Actor;S->Origin=Id;S->Script=TEXT("bar-f1");G->InitPlacementSprite(*S);S->Props.Add(TEXT("live"),1);S->Props.Add(TEXT("pseq"),173);S->Props.Add(TEXT("pframe"),1);S->Props.Add(TEXT("hard"),0);
    TestTrue(TEXT("ordinary source initializer preserves audited stationary placement semantics"),S->X==Placement->X&&S->Y==Placement->Y&&S->Dir==0&&
        S->Props.Contains(TEXT("speed"))&&S->GetProp(TEXT("speed"))==Placement->Speed&&Placement->Speed==0);
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
    const auto& PublishedRelease=G->HardnessProjection->Fits->Releases.Last();
    const FTransform RequestedWorld=PublishedRelease.ReleaseCardRelative*Actor->GetRootComponent()->GetComponentTransform();
    TestTrue(TEXT("large parent fixture exercises local roundtrip while world request stays exact"),
        Actor->GetRootComponent()->GetComponentLocation().X==2722.5&&PublishedRelease.ReleaseCardRelative.GetLocation().X==1.0000000000000018&&Actor->Card->GetRelativeLocation().X==1.0&&Actor->Card->GetComponentTransform().Equals(RequestedWorld,0));
    TestTrue(TEXT("published epoch freezes actual observed relative rather than ideal request"),Actor->PublishedLegacyCardRelative.Equals(Actor->Card->GetRelativeTransform(),0));
    const auto ReleasedBefore=Actor->Card->GetRelativeTransform();
    const auto ReleaseState=G->HardnessProjection->Fits->ReleaseStates.Last();
    auto EpochULP=Actor->PublishedLegacyCardRelative;auto ULPLocation=EpochULP.GetLocation();ULPLocation.X=std::nextafter(ULPLocation.X,std::numeric_limits<double>::infinity());EpochULP.SetTranslation(ULPLocation);
    Actor->PublishedLegacyCardRelative=EpochULP;
    TestFalse(TEXT("one ULP tamper of frozen actual relative epoch still refuses"),Families->PrepareCollisionFitReleaseCandidate(Id,ReleaseState,PreparedPicture,Error));
    Actor->PublishedLegacyCardRelative=ReleasedBefore;
    Actor->Card->AddWorldOffset(FVector(1,0,0));
    TestFalse(TEXT("true world displacement refuses future release"),Families->PrepareCollisionFitReleaseCandidate(Id,ReleaseState,PreparedPicture,Error));
    Actor->Card->SetRelativeTransform(ReleasedBefore);
    auto* RootParent=Actor->GetRootComponent();auto* OtherParent=NewObject<USceneComponent>(Actor);Actor->AddInstanceComponent(OtherParent);OtherParent->SetupAttachment(RootParent);OtherParent->SetMobility(EComponentMobility::Movable);OtherParent->RegisterComponent();
    TestTrue(TEXT("owned alternative parent attaches for rejection control"),Actor->Card->AttachToComponent(OtherParent,FAttachmentTransformRules::KeepWorldTransform));
    TestFalse(TEXT("changed parent refuses even with same world frame"),Families->PrepareCollisionFitReleaseCandidate(Id,ReleaseState,PreparedPicture,Error));
    Actor->Card->AttachToComponent(RootParent,FAttachmentTransformRules::KeepWorldTransform);OtherParent->DestroyComponent();Actor->Card->SetRelativeTransform(ReleasedBefore);
    Actor->Card->AttachToComponent(RootParent,FAttachmentTransformRules::KeepWorldTransform,TEXT("UnsupportedSocket"));
    TestFalse(TEXT("nonempty attachment socket refuses supported publication"),Families->PrepareCollisionFitReleaseCandidate(Id,ReleaseState,PreparedPicture,Error));
    Actor->Card->AttachToComponent(RootParent,FAttachmentTransformRules::KeepWorldTransform,NAME_None);Actor->Card->SetRelativeTransform(ReleasedBefore);
    Actor->Card->SetAbsolute(true,false,false);
    TestFalse(TEXT("absolute location refuses relative-to-world publication contract"),Families->PrepareCollisionFitReleaseCandidate(Id,ReleaseState,PreparedPicture,Error));
    Actor->Card->SetAbsolute(false,false,false);Actor->Card->SetRelativeTransform(ReleasedBefore);
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
    auto IntactState=ReleaseState;IntactState.bPrebirth=false;IntactState.RuntimeHandle=Handle;IntactState.bActive=true;IntactState.DisplayedSequence=173;IntactState.DisplayedFrame=1;
    IntactState.DisplayedPicture=IntactState.SourcePicture;IntactState.AnimationSequence=0;IntactState.Brain=0;IntactState.NoHit=0;
    FDinkFamilyCollisionFitCandidate RestoreCandidate;
    const auto RetainedWitness=Actor->PublishedLegacyReleaseWitness;
    if(!TestTrue(TEXT("successful publication retains lean nonrecursive picture witness"),RetainedWitness.IsValid()&&RetainedWitness->Geometry.Vertices.IsEmpty()&&RetainedWitness->LogicalCells.IsEmpty()&&!RetainedWitness->RestoreReleaseWitness))return false;
    Actor->PublishedLegacyReleaseWitness.Reset();
    TestFalse(TEXT("intact restore cannot infer missing publication witness"),Families->PrepareCollisionFit(Id,IntactState,RestoreCandidate,Error));
    Actor->bHasPublishedLegacyPicture=false;
    TestFalse(TEXT("unwitnessed visible card and hidden family cannot admit intact restore"),Families->PrepareCollisionFit(Id,IntactState,RestoreCandidate,Error));
    Actor->PublishedLegacyReleaseWitness=RetainedWitness;
    Actor->bHasPublishedLegacyPicture=false;
    TestFalse(TEXT("cleared flag cannot bypass retained publication witness"),Families->PrepareCollisionFit(Id,IntactState,RestoreCandidate,Error));
    Actor->bHasPublishedLegacyPicture=true;
    UStaticMesh* RetainedMesh=Actor->Card->GetStaticMesh();Actor->Card->SetStaticMesh(nullptr);
    TestFalse(TEXT("intact restore refuses swapped published card mesh"),Families->PrepareCollisionFit(Id,IntactState,RestoreCandidate,Error));
    Actor->Card->SetStaticMesh(RetainedMesh);
    const auto SourceSha=Actor->PublishedSourcePictureSha1;Actor->PublishedSourcePictureSha1=TEXT("tampered");
    TestFalse(TEXT("intact restore refuses changed source descriptor witness"),Families->PrepareCollisionFit(Id,IntactState,RestoreCandidate,Error));
    Actor->PublishedSourcePictureSha1=SourceSha;
    auto BadIntactDescriptor=IntactState;BadIntactDescriptor.SourcePicture.OriginX++;
    TestFalse(TEXT("intact restore rejects changed canonical pivot retaining old descriptor SHA"),Families->PrepareCollisionFit(Id,BadIntactDescriptor,RestoreCandidate,Error));
    if(!TestTrue(TEXT("known published broken card qualifies genuine intact request"),Families->PrepareCollisionFit(Id,IntactState,RestoreCandidate,Error))){AddError(Error);return false;}
    Actor->PublishedLegacyReleaseWitness.Reset();
    TestFalse(TEXT("prepare-to-apply witness removal refuses"),Families->ValidateCollisionFit(RestoreCandidate,IntactState,Error));
    Actor->PublishedLegacyReleaseWitness=RetainedWitness;
    const auto BaselineBefore=Actor->ImportedCardRelativeTransform;Actor->ImportedCardRelativeTransform.AddToTranslation(FVector(1,0,0));
    TestFalse(TEXT("intact restore refuses immutable baseline tamper"),Families->PrepareCollisionFit(Id,IntactState,RestoreCandidate,Error));
    Actor->ImportedCardRelativeTransform=BaselineBefore;
    Actor->PublishedLegacyCardRelative=EpochULP;
    TestFalse(TEXT("intact restore refuses one ULP published epoch tamper"),Families->PrepareCollisionFit(Id,IntactState,RestoreCandidate,Error));
    Actor->PublishedLegacyCardRelative=ReleasedBefore;
    Actor->Card->SetAbsolute(true,false,false);
    TestFalse(TEXT("intact restore refuses unsupported parent-relative authority"),Families->PrepareCollisionFit(Id,IntactState,RestoreCandidate,Error));
    Actor->Card->SetAbsolute(false,false,false);Actor->Card->SetRelativeTransform(ReleasedBefore);
    Actor->Card->SetMaterial(0,RetainedWitness->SourcePictureMaterial->Get());
    TestFalse(TEXT("intact restore refuses changed published card material"),Families->PrepareCollisionFit(Id,IntactState,RestoreCandidate,Error));
    Actor->Card->SetMaterial(0,RetainedWitness->ReleaseMaterial->Get());
    #if WITH_EDITOR
    if(auto* PublishedMI=Cast<UMaterialInstanceConstant>(RetainedWitness->ReleaseMaterial->Get()))
    {
        const bool WasDirty=PublishedMI->GetOutermost()->IsDirty();UTexture* ExactTex=RetainedWitness->ReleaseTexture->Get();
        ON_SCOPE_EXIT {PublishedMI->SetTextureParameterValueEditorOnly(FMaterialParameterInfo(TEXT("Tex")),ExactTex);PublishedMI->GetOutermost()->SetDirtyFlag(WasDirty);};
        PublishedMI->SetTextureParameterValueEditorOnly(FMaterialParameterInfo(TEXT("Tex")),RetainedWitness->SourcePictureTexture->Get());
        TestFalse(TEXT("intact restore refuses prior published MI Tex mutation"),Families->PrepareCollisionFit(Id,IntactState,RestoreCandidate,Error));
        TestFalse(TEXT("prepared restore revalidates prior published MI Tex epoch"),Families->ValidateCollisionFit(RestoreCandidate,IntactState,Error));
        PublishedMI->SetTextureParameterValueEditorOnly(FMaterialParameterInfo(TEXT("Tex")),ExactTex);
    }
    else AddError(TEXT("expected published ordinary MI for intact restore texture control"));
    #endif
    const bool RestoredIntact=G->RedrawRuntimeHardnessMap(209,Error);
    if(!TestTrue(TEXT("intact source restore after repeated broken presentation"),RestoredIntact)){RedrawFailure(TEXT("intact source restore after repeated broken presentation"),Error);return false;}
    TestNotNull(TEXT("intact restore reintroduces actual fitted body"),G->FindHardnessFitPrimitive(*D->FindSprite(Handle)));
    TestTrue(TEXT("intact restore hides legacy card and shows family"),Actor->Card->bHiddenInGame&&FamilyMesh->IsVisible()&&!FamilyMesh->bHiddenInGame);
    TestEqual(TEXT("intact restore retains immutable source picture identity"),Actor->Origin->Frame,1);
    // Keep a registered generic mask body for shutdown coverage. The natural
    // completion case below retires the source barrel's fitted body explicitly.
    const int32 Extra=D->CreateVirtualSprite(209,Placement->X+70,Placement->Y);
    auto* ExtraSprite=D->FindSprite(Extra);ExtraSprite->Props.Add(TEXT("pseq"),173);ExtraSprite->Props.Add(TEXT("pframe"),1);ExtraSprite->Props.Add(TEXT("hard"),0);
    const bool ShutdownRedrawn=G->RedrawRuntimeHardnessMap(209,Error);
    if(!TestTrue(TEXT("prepare controlled final registered body for shutdown lifetime proof"),ShutdownRedrawn)){RedrawFailure(TEXT("prepare controlled final registered body for shutdown lifetime proof"),Error);return false;}
    // Detached fixture evidence only: never synchronize or repair the measured row.
    TArray<TSharedPtr<FJsonValue>> CoordinateRows;int32 FirstCoordinateDivergence=INDEX_NONE;
    const FString CoordinateDir=FPaths::ProjectSavedDir()/TEXT("Automation/ReleasedCoordinateDiagnostic");
    const FString CoordinateFile=CoordinateDir/(FGuid::NewGuid().ToString(EGuidFormats::Digits)+TEXT(".json"));
    const auto CoordinateSnapshot=[&](const TCHAR* Phase,double Tick)
    {
        const auto* Row=D->FindSprite(Handle);auto Facts=MakeShared<FJsonObject>();
        Facts->SetStringField(TEXT("phase"),Phase);Facts->SetNumberField(TEXT("tick"),Tick);Facts->SetBoolField(TEXT("row_present"),Row!=nullptr);
        if(Row)
        {
            const FVector Actual=Actor->GetActorLocation();const FVector Mapped=DinkLayout::MapPixelToUnreal(Volume->Corners,Row->X-20,Row->Y);
            double InverseX=0,InverseY=0;const bool InverseOk=DinkLayout::MetresToMapPixel(Volume->Corners,DinkLayout::UnrealToMetres(Actual),InverseX,InverseY);
            const bool Agrees=FVector2D(Actual.X,Actual.Y).Equals(FVector2D(Mapped.X,Mapped.Y),.05);
            if(!Agrees&&FirstCoordinateDivergence==INDEX_NONE)FirstCoordinateDivergence=CoordinateRows.Num();
            Facts->SetBoolField(TEXT("strict_ground_agrees"),Agrees);Facts->SetBoolField(TEXT("inverse_ok"),InverseOk);
            const auto Exact=[&](const TCHAR* Name,double Value){uint64 Bits=0;FMemory::Memcpy(&Bits,&Value,sizeof(Bits));Facts->SetStringField(Name,FString::Printf(TEXT("%.17g/0x%016llx"),Value,static_cast<unsigned long long>(Bits)));};
            Exact(TEXT("row_x"),Row->X);Exact(TEXT("row_y"),Row->Y);Exact(TEXT("placement_x"),Placement->X);Exact(TEXT("placement_y"),Placement->Y);
            Exact(TEXT("actor_x"),Actual.X);Exact(TEXT("actor_y"),Actual.Y);Exact(TEXT("actor_z"),Actual.Z);Exact(TEXT("mapped_x"),Mapped.X);Exact(TEXT("mapped_y"),Mapped.Y);
            const FQuat ActualQ=Actor->GetActorQuat();const FVector ActualScale=Actor->GetActorScale3D();
            Exact(TEXT("actor_qx"),ActualQ.X);Exact(TEXT("actor_qy"),ActualQ.Y);Exact(TEXT("actor_qz"),ActualQ.Z);Exact(TEXT("actor_qw"),ActualQ.W);
            Exact(TEXT("actor_sx"),ActualScale.X);Exact(TEXT("actor_sy"),ActualScale.Y);Exact(TEXT("actor_sz"),ActualScale.Z);
            Exact(TEXT("delta_x"),Actual.X-Mapped.X);Exact(TEXT("delta_y"),Actual.Y-Mapped.Y);Exact(TEXT("inverse_engine_x"),InverseX+20);Exact(TEXT("inverse_y"),InverseY);
            Exact(TEXT("corner_nw_x"),Volume->Corners.NW.X);Exact(TEXT("corner_nw_y"),Volume->Corners.NW.Y);Exact(TEXT("corner_ne_x"),Volume->Corners.NE.X);Exact(TEXT("corner_ne_y"),Volume->Corners.NE.Y);
            Exact(TEXT("corner_sw_x"),Volume->Corners.SW.X);Exact(TEXT("corner_sw_y"),Volume->Corners.SW.Y);Exact(TEXT("corner_se_x"),Volume->Corners.SE.X);Exact(TEXT("corner_se_y"),Volume->Corners.SE.Y);
            Facts->SetStringField(TEXT("actor"),GetPathNameSafe(Row->Actor.Get()));Facts->SetStringField(TEXT("source"),GetPathNameSafe(Actor));Facts->SetStringField(TEXT("origin"),Row->Origin.ToString());
            Facts->SetNumberField(TEXT("screen"),Row->Screen);Facts->SetNumberField(TEXT("handle"),Handle);Facts->SetNumberField(TEXT("dir"),Row->Dir);
            Facts->SetBoolField(TEXT("active"),Row->bActive);Facts->SetBoolField(TEXT("moving"),Row->bMoving);Facts->SetBoolField(TEXT("spawned"),Row->bSpawned);Facts->SetBoolField(TEXT("retained"),Row->bRetainedOriginalEditor);
            Facts->SetBoolField(TEXT("slot"),G->HardnessProjection&&G->HardnessProjection->Identity->Slots.Slot(Handle).has_value());Facts->SetBoolField(TEXT("explicit_speed"),Row->Props.Contains(TEXT("speed")));
            for(const TCHAR* Key:{TEXT("mx"),TEXT("my"),TEXT("seq"),TEXT("frame"),TEXT("pseq"),TEXT("pframe"),TEXT("brain"),TEXT("nohit")})Facts->SetNumberField(Key,Row->GetProp(Key));
            Facts->SetNumberField(TEXT("speed_default1"),Row->GetProp(TEXT("speed"),1));
        }
        CoordinateRows.Add(MakeShared<FJsonValueObject>(Facts));
    };
    const auto SaveCoordinates=[&]()
    {
        auto Facts=MakeShared<FJsonObject>();Facts->SetArrayField(TEXT("rows"),CoordinateRows);Facts->SetNumberField(TEXT("first_divergence"),FirstCoordinateDivergence);
        FString Text;IFileManager::Get().MakeDirectory(*CoordinateDir,true);
        const bool Written=FJsonSerializer::Serialize(Facts,TJsonWriterFactory<>::Create(&Text))&&FFileHelper::SaveStringToFile(Text,*CoordinateFile);
        AddInfo(FString::Printf(TEXT("released coordinate diagnostic rows=%d firstDivergence=%d written=%d path=%s"),CoordinateRows.Num(),FirstCoordinateDivergence,Written,*CoordinateFile));
    };
    ON_SCOPE_EXIT { SaveCoordinates(); };
    TestTrue(TEXT("natural source begins with unchanged placement speed and dumb-sprite direction"),D->FindSprite(Handle)->GetProp(TEXT("speed"))==Placement->Speed&&D->FindSprite(Handle)->Dir==0);
    CoordinateSnapshot(TEXT("before_first_natural_hit"),Story->GetNowMs());
    // Natural production path: original hit procedure, then ThinkSprite's real
    // Animate -> OneTimeBrain5 completion. No manual final pframe or final redraw.
    S=D->FindSprite(Handle);S->bSpawned=false; // this actor is the fixture's ordinary source placement
    S->Script=Placement->Script;
    const int32 HitInstance=Story->StartProcedure(Placement->Script,TEXT("hit"),Handle,{},209,true);
    if(!TestTrue(TEXT("actual source hit procedure starts"),HitInstance>0))return false;
    Story->RunNow(HitInstance);
    S=D->FindSprite(Handle);
    if(!TestTrue(TEXT("actual hit script initializes natural brain5 and persisted background"),
        S&&S->bActive&&S->GetProp(TEXT("brain"))==5&&S->GetProp(TEXT("seq"))==173&&
        Story->GetWorldState()->GetOverrideType(Id)==EDinkOverrideType::BackgroundNoHardness&&!G->IsHardnessLoading()))return false;
    const double NaturalStart=Story->GetNowMs();int32 NaturalFrames=0;TSet<int32> AnimatedFrames;
    for(;NaturalFrames<180&&D->FindSprite(Handle)->bActive;++NaturalFrames)
    {
        CoordinateSnapshot(TEXT("before_existing_think"),NaturalStart+NaturalFrames*(1000.0/60.0));
        G->ThinkSprite(Handle,NaturalStart+NaturalFrames*(1000.0/60.0));
        CoordinateSnapshot(TEXT("after_existing_think"),NaturalStart+NaturalFrames*(1000.0/60.0));
        AnimatedFrames.Add(D->FindSprite(Handle)->GetProp(TEXT("pframe")));
    }
    CoordinateSnapshot(TEXT("after_natural_deactivation"),Story->GetNowMs());
    TestTrue(TEXT("natural animator actually visited intermediate and final frames"),AnimatedFrames.Contains(2)&&AnimatedFrames.Contains(3)&&AnimatedFrames.Contains(4)&&AnimatedFrames.Contains(5)&&AnimatedFrames.Contains(6));
    S=D->FindSprite(Handle);
    if(!TestTrue(TEXT("natural Animate reaches final1736 then brain5 deactivates"),S&&!S->bActive&&
        S->GetProp(TEXT("pseq"))==173&&S->GetProp(TEXT("pframe"))==6&&S->GetProp(TEXT("seq"))==0&&S->GetProp(TEXT("frame"))==0&&NaturalFrames<180))return false;
    TestTrue(TEXT("original kill_this_task ends attached script naturally"),S->Script.IsNone());
    TestTrue(TEXT("natural final background is actually visible without reactivating logical sprite"),
        !Actor->IsHidden()&&Actor->Card->IsVisible()&&!Actor->Card->bHiddenInGame&&FamilyMesh->bHiddenInGame&&!FamilyMesh->IsVisible()&&!G->IsHardnessLoading());
    TestEqual(TEXT("natural final background uses actual1736 material"),Actor->Card->GetMaterial(0)->GetPathName(),FString(TEXT("/Game/Dink/_Generated/Sprites/MI_Sprite_173_06.MI_Sprite_173_06")));
    UTexture* NaturalTex=nullptr;
    TestTrue(TEXT("natural final background actual Tex is1736"),Actor->Card->GetMaterial(0)->GetTextureParameterValue(FMaterialParameterInfo(TEXT("Tex")),NaturalTex)&&NaturalTex&&NaturalTex->GetPathName()==TEXT("/Game/Dink/_Generated/Sprites/T_Sprite_173_06.T_Sprite_173_06"));
    TestTrue(TEXT("natural final background preserves canonical source pivot projection"),Actor->Card->GetRelativeTransform().Equals(FirstBrokenPose,0));
    TestNull(TEXT("natural inactive background has no fitted body"),G->FindHardnessFitPrimitive(*S));
    // Generic/spawned behavior and brain7 remain distinct from source-backed brain5.
    for(const int32 Case:{0,1,2})
    {
        const int32 Brain=Case==2?7:5;const bool Spawned=Case==0;
        auto* Other=W->SpawnActor<AActor>();const int32 H=D->CreateVirtualSprite(209,Placement->X+100,Placement->Y);
        auto* OtherSprite=D->FindSprite(H);OtherSprite->Actor=Other;OtherSprite->bSpawned=Spawned;
        OtherSprite->Props.Add(TEXT("brain"),Brain);OtherSprite->Props.Add(TEXT("seq"),173);
        for(int32 F=0;F<180&&D->FindSprite(H)->bActive;++F)G->ThinkSprite(H,NaturalStart+F*(1000.0/60.0));
        TestFalse(TEXT("paired generic one-time sprite deactivates"),D->FindSprite(H)->bActive);
        TestTrue(TEXT("brain7 stays hidden; generic spawnedbrain5 stays destroyed, no background publication"),
            Spawned?Other->IsActorBeingDestroyed():Other->IsHidden());
        TestTrue(TEXT("unrelated one-time completion cannot alter admitted source background"),!Actor->IsHidden()&&Actor->Card->GetMaterial(0)==FirstBrokenMaterial);
    }
    // A requested source without an admitted projection must retain the loading
    // guard and must not forcibly expose an actor. Restore via normal redraw only.
    const auto AdmittedFinalBackgroundProjection=G->HardnessProjection;Actor->SetActorHiddenInGame(true);G->HardnessProjection.Reset();
    TestFalse(TEXT("natural final background refuses absent screen admission"),G->CommitFittedBrain5Background(Handle,Error));
    TestTrue(TEXT("unadmitted refusal holds gate and never forces visibility"),G->IsHardnessLoading()&&Actor->IsHidden());
    G->HardnessProjection=AdmittedFinalBackgroundProjection;G->SetHardnessLoading(false);
    if(!TestTrue(TEXT("restored admission republishes through existing guarded background path"),G->RedrawRuntimeHardnessMap(209,Error))){AddError(Error);return false;}
    S=D->FindSprite(Handle); // Generic sprite insertions above may invalidate earlier TMap value pointers.
    if(!TestNotNull(TEXT("final background source record remains bound"),S))return false;
    AddInfo(FString::Printf(TEXT("final background factors ActorHidden=%d currentActive=%d materialSame=%d actualMaterial=%s expectedMaterial=%s"),
        Actor->IsHidden(),S->bActive,Actor->Card->GetMaterial(0)==FirstBrokenMaterial,*GetPathNameSafe(Actor->Card->GetMaterial(0)),*GetPathNameSafe(FirstBrokenMaterial)));
    TestTrue(TEXT("normal guarded redraw restores correct inactive background"),!Actor->IsHidden()&&!S->bActive&&Actor->Card->GetMaterial(0)==FirstBrokenMaterial);
    TestTrue(TEXT("default absent final-mesh option leaves all existing legacy controls exact"),!Families->ReleasedVisualBinding.bRequested&&!Actor->ReleasedFamilyArt);
#if WITH_EDITOR
    // Own unsaved synthetic assets; never mutate the engine cube or activate production Data.
    const FString PackageName=TEXT("/Game/DinkQA/ReleasedVisual_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    auto* VisualPackage=CreatePackage(*PackageName);auto* VisualMesh=DuplicateObject<UStaticMesh>(Cube,VisualPackage,TEXT("SM_SyntheticReleased"));
    if(!TestNotNull(TEXT("owned synthetic visual mesh"),VisualMesh)||
       !TestTrue(TEXT("owned body setup is not shared with engine source"),VisualMesh->GetBodySetup()&&VisualMesh->GetBodySetup()!=Cube->GetBodySetup()))return false;
    FAssetCompilingManager::Get().FinishAllCompilation(); // owned synthetic asset setup only, before any gameplay mutation
    VisualMesh->GetBodySetup()->AggGeom.EmptyElements();VisualMesh->MarkAsNotHavingNavigationData();VisualMesh->GetStaticMaterials().Reset();
    TArray<UMaterialInterface*> VisualMaterials;
    for(int32 I=0;I<3;++I)
    {
        auto* M=NewObject<UMaterial>(VisualPackage,*FString::Printf(TEXT("M_Synthetic_%d"),I),RF_Public|RF_Standalone);
        VisualMaterials.Add(M);VisualMesh->GetStaticMaterials().Add(FStaticMaterial(M));
    }
    // Characterize the supported unit-parent yaw path using actual stock components.
    // FamilyWorld comes from the first real child, not a hand-computed quaternion oracle.
    // No epsilon/force-update/cache flush: the final exact-world gate remains the production contract.
    auto TransformWords=[](const FTransform& T)
    {
        const FVector V=T.GetTranslation(),Z=T.GetScale3D();const FQuat Q=T.GetRotation();
        const double Values[]={V.X,V.Y,V.Z,Q.X,Q.Y,Q.Z,Q.W,Z.X,Z.Y,Z.Z};
        TArray<TSharedPtr<FJsonValue>> Out;
        for(const double Value:Values)
        {
            uint64 Word=0;FMemory::Memcpy(&Word,&Value,sizeof(Word));
            Out.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("%.17g/0x%016llx"),Value,static_cast<unsigned long long>(Word))));
        }
        return Out;
    };
    for(const double ParentYaw:{45.0,90.0})
    {
        auto* ParentActor=W->SpawnActor<AActor>();auto* Parent=NewObject<USceneComponent>(ParentActor);
        ParentActor->AddInstanceComponent(Parent);ParentActor->SetRootComponent(Parent);Parent->SetMobility(EComponentMobility::Movable);Parent->RegisterComponent();
        ParentActor->SetActorTransform(FTransform(FRotator(0,ParentYaw,0),FVector(221487.36,-157285.60,0),FVector::OneVector));
        auto* StockFamily=NewObject<USceneComponent>(ParentActor);ParentActor->AddInstanceComponent(StockFamily);StockFamily->SetupAttachment(Parent);StockFamily->SetMobility(EComponentMobility::Movable);
        StockFamily->SetRelativeTransform(FTransform(FRotator(0,DinkArtFamily::StableYaw(Id.ToString()),0),FVector::ZeroVector,FVector::OneVector));StockFamily->RegisterComponent();
        const FTransform ParentBefore=Parent->GetComponentTransform();
        const FQuat QualifiedYaw=StockFamily->GetComponentQuat();const FVector NonzeroAnchor(3.25,-7.125,-2.5);
        const FTransform Requested(QualifiedYaw,ParentActor->GetActorLocation()-QualifiedYaw.RotateVector(NonzeroAnchor),FVector::OneVector);
        const FTransform Relative=Requested.GetRelativeTransform(ParentBefore);
        auto* StockReleased=NewObject<USceneComponent>(ParentActor);ParentActor->AddInstanceComponent(StockReleased);StockReleased->SetupAttachment(Parent);StockReleased->SetMobility(EComponentMobility::Movable);StockReleased->RegisterComponent();
        StockReleased->SetRelativeTransform(Relative,false,nullptr,ETeleportType::TeleportPhysics);
        const FTransform Actual=StockReleased->GetComponentTransform();const bool Exact=Actual.Equals(Requested,0);
        auto Facts=MakeShared<FJsonObject>();Facts->SetNumberField(TEXT("nominal_parent_yaw_degrees"),ParentYaw);Facts->SetBoolField(TEXT("actual_world_exact_requested"),Exact);
        Facts->SetArrayField(TEXT("parent_actual_t_q_s_words"),TransformWords(ParentBefore));Facts->SetArrayField(TEXT("qualified_family_world_t_q_s_words"),TransformWords(StockFamily->GetComponentTransform()));
        Facts->SetArrayField(TEXT("requested_world_t_q_s_words"),TransformWords(Requested));Facts->SetArrayField(TEXT("requested_relative_t_q_s_words"),TransformWords(Relative));
        Facts->SetArrayField(TEXT("actual_world_t_q_s_words"),TransformWords(Actual));Facts->SetArrayField(TEXT("actual_relative_t_q_s_words"),TransformWords(StockReleased->GetRelativeTransform()));
        const FString Dir=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Automation/ReleasedParentYaw"));IFileManager::Get().MakeDirectory(*Dir,true);
        const FString File=Dir/(FGuid::NewGuid().ToString(EGuidFormats::Digits)+TEXT(".json"));FString Text;
        const bool Written=FJsonSerializer::Serialize(Facts,TJsonWriterFactory<>::Create(&Text))&&FFileHelper::SaveStringToFile(Text,*File,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_NoReplaceExisting);
        AddInfo(FString::Printf(TEXT("stock released parent yaw %.0f exact=%d receipt=%s written=%d payload=%s"),ParentYaw,Exact,*File,Written,*Text));
        TestTrue(TEXT("stock parent remains unit-scale and unchanged"),ParentBefore.GetScale3D().Equals(FVector::OneVector,0)&&Parent->GetComponentTransform().Equals(ParentBefore,0));
        TestTrue(FString::Printf(TEXT("stock supported parent yaw %.0f preserves exact requested world"),ParentYaw),Exact);
        TestTrue(TEXT("stock parent characterization receipt retained before equality assertion"),Written);
        ParentActor->Destroy();
    }
    FString Option=FString::Printf(TEXT("{\"schema\":\"dink-art-families/1\",\"released_barrel_visual\":{\"sequence\":173,\"frame\":6,\"mesh\":\"%s\",\"materials\":[\"%s\",\"%s\",\"%s\"]}}"),
        *VisualMesh->GetPathName(),*VisualMaterials[0]->GetPathName(),*VisualMaterials[1]->GetPathName(),*VisualMaterials[2]->GetPathName());
    FDinkReleasedFamilyVisualBinding Parsed;
    TestTrue(TEXT("optional released binding absent remains off"),DinkFamilyCollisionFit::ParseReleasedVisual(TEXT("{\"schema\":\"dink-art-families/1\"}"),Parsed,Error)&&!Parsed.bRequested);
    TestFalse(TEXT("wrong final frame refuses instead of ignoring request"),DinkFamilyCollisionFit::ParseReleasedVisual(Option.Replace(TEXT("\"frame\":6"),TEXT("\"frame\":1")),Parsed,Error));
    TestFalse(TEXT("unknown option field refuses"),DinkFamilyCollisionFit::ParseReleasedVisual(Option.Replace(TEXT("\"frame\":6"),TEXT("\"frame\":6,\"extra\":true")),Parsed,Error));
    if(!TestTrue(TEXT("explicit synthetic final1736 mapping parses"),DinkFamilyCollisionFit::ParseReleasedVisual(Option,Parsed,Error)))return false;
    Families->ReleasedVisualBinding=Parsed;
    const auto FinalLegacyState=G->HardnessProjection->Fits->ReleaseStates.Last();FDinkFamilyCollisionFitCandidate MissingVisual;
    Families->ReleasedVisualBinding.Mesh=PackageName+TEXT("/Missing.Missing");
    TestFalse(TEXT("explicit missing final mesh refuses before any card/child mutation"),Families->PrepareCollisionFitReleaseCandidate(Id,FinalLegacyState,MissingVisual,Error));
    TestTrue(TEXT("missing requested mesh leaves prior card and actor child untouched"),!Actor->ReleasedFamilyArt&&Actor->Card->GetRelativeTransform().Equals(FirstBrokenPose,0)&&Actor->Card->GetMaterial(0)==FirstBrokenMaterial);
    Families->ReleasedVisualBinding=Parsed;
    CoordinateSnapshot(TEXT("before_restore_props"),Story->GetNowMs());
    // Restore intact through the SAME coordinator before a second real hit/Animate/brain5 cycle.
    Story->GetWorldState()->ClearOverride(Id);G->EditorHardnessPicture(Id,true,173);G->EditorHardnessPicture(Id,false,1);G->RecordEditorHardness(Id,0);
    S=D->FindSprite(Handle);S->Script=Placement->Script;S->Props.Add(TEXT("pseq"),173);S->Props.Add(TEXT("pframe"),1);S->Props.Add(TEXT("seq"),0);S->Props.Add(TEXT("frame"),0);S->Props.Add(TEXT("brain"),0);S->Props.Add(TEXT("nohit"),0);S->Props.Add(TEXT("hard"),0);
    TestFalse(TEXT("natural deactivation released the original live slot"),G->HardnessProjection->Identity->Slots.Slot(Handle).has_value());
    FDinkScriptInstance ReactivationContext;ReactivationContext.Script=Placement->Script;ReactivationContext.Sprite=Handle;ReactivationContext.Screen=209;
    FDinkStoryLine ReactivationLine;ReactivationLine.Kind=EDinkLineKind::Command;ReactivationLine.Command=TEXT("sp_active");ReactivationLine.Args={FString::FromInt(Handle),TEXT("1")};
    CoordinateSnapshot(TEXT("before_sp_active"),Story->GetNowMs());
    D->Execute(ReactivationContext,ReactivationLine);
    CoordinateSnapshot(TEXT("after_sp_active"),Story->GetNowMs());
    TestTrue(TEXT("registered sp_active command restores actual live slot"),G->HardnessProjection->Identity->Slots.Slot(Handle).has_value()&&D->FindSprite(Handle)->bActive);
    CoordinateSnapshot(TEXT("before_intact_redraw"),Story->GetNowMs());
    const bool FeatureIntactRedrawn=G->RedrawRuntimeHardnessMap(209,Error);
    CoordinateSnapshot(TEXT("after_intact_redraw"),Story->GetNowMs());
    if(!TestTrue(TEXT("opt-in feature preserves actual intact restore/body"),FeatureIntactRedrawn)){AddError(Error);return false;}
    FString IntactBodyError;const auto* IntactBeforeHit=D->FindSprite(Handle);
    auto* IntactBeforeHitBody=G->FindHardnessFitPrimitive(*IntactBeforeHit,&IntactBodyError);
    TestNotNull(TEXT("intact fitted body present before natural feature hit"),IntactBeforeHitBody);
    if(!IntactBeforeHitBody)
    {
        AddInfo(FString::Printf(TEXT("feature intact prehit lookup: handle=%d actor=%s source=%s rowScreen=%d projectionScreen=%d vision=%d loading=%d reason=%s"),
            Handle,*GetPathNameSafe(IntactBeforeHit->Actor.Get()),*GetPathNameSafe(Actor),IntactBeforeHit->Screen,
            G->HardnessProjection?G->HardnessProjection->Screen:0,G->HardnessProjection?G->HardnessProjection->Vision:0,G->IsHardnessLoading(),*IntactBodyError));
        if(G->HardnessProjection&&G->HardnessProjection->Fits)
            for(const auto& Fit:G->HardnessProjection->Fits->Candidates)
                AddInfo(FString::Printf(TEXT("feature intact admitted candidate: actor=%s source=%s family=%s familyRegistered=%d"),
                    *GetPathNameSafe(Fit.Actor.Get()),*GetPathNameSafe(Fit.SourceActor.Get()),*GetPathNameSafe(Fit.FamilyComponent.Get()),Fit.FamilyComponent.IsValid()&&Fit.FamilyComponent->IsRegistered()));
    }
    const int32 MeshHit=Story->StartProcedure(Placement->Script,TEXT("hit"),Handle,{},209,true);
    if(!TestTrue(TEXT("second source hit really starts"),MeshHit>0))return false;Story->RunNow(MeshHit);
    for(int32 F=0;F<180&&D->FindSprite(Handle)->bActive;++F)G->ThinkSprite(Handle,NaturalStart+4000+F*(1000.0/60.0));
    S=D->FindSprite(Handle);auto* Released=Actor->ReleasedFamilyArt.Get();
    if(!TestNotNull(TEXT("natural final1736 publishes dedicated mesh child"),Released))return false;
    TestTrue(TEXT("natural released mesh preserves inactive/scriptend/type3/no-body domains"),!S->bActive&&S->Script.IsNone()&&S->GetProp(TEXT("pframe"))==6&&Story->GetWorldState()->GetOverrideType(Id)==EDinkOverrideType::BackgroundNoHardness&&!G->FindHardnessFitPrimitive(*S)&&!G->IsHardnessLoading());
    TestTrue(TEXT("real-size released child replaces visible giant card, not collision source"),Released->IsVisible()&&!Released->bHiddenInGame&&Released->GetStaticMesh()==VisualMesh&&Released->GetComponentScale().Equals(FVector::OneVector,0)&&Actor->Card->bHiddenInGame&&!Actor->Card->IsVisible()&&FamilyMesh->bHiddenInGame&&FamilyMesh->GetStaticMesh()==Barrel);
    TestTrue(TEXT("released child is visual only without authored/family interaction tags"),Released->GetCollisionEnabled()==ECollisionEnabled::NoCollision&&!Released->CanEverAffectNavigation()&&!Released->GetGenerateOverlapEvents()&&!Released->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)&&!Actor->ActorHasTag(TEXT("DinkAuthoredArt")));
    TestTrue(TEXT("hidden canonical card still holds exact1736 source witness"),Actor->Card->GetMaterial(0)==FirstBrokenMaterial&&Actor->Card->GetRelativeTransform().Equals(FirstBrokenPose,0));
    auto* Brain7Actor=W->SpawnActor<AActor>();const int32 Brain7Handle=D->CreateVirtualSprite(209,Placement->X+100,Placement->Y);
    auto* Brain7Sprite=D->FindSprite(Brain7Handle);Brain7Sprite->Actor=Brain7Actor;Brain7Sprite->bSpawned=false;Brain7Sprite->Props.Add(TEXT("brain"),7);Brain7Sprite->Props.Add(TEXT("seq"),173);
    for(int32 F=0;F<180&&D->FindSprite(Brain7Handle)->bActive;++F)G->ThinkSprite(Brain7Handle,NaturalStart+8000+F*(1000.0/60.0));
    TestTrue(TEXT("enabled final-mesh option keeps paired brain7 hidden without background publication"),Brain7Actor->IsHidden()&&!D->FindSprite(Brain7Handle)->bActive&&Actor->ReleasedFamilyArt==Released&&Released->IsVisible());
    const auto MeshWitness=Actor->PublishedLegacyReleaseWitness;const auto ChildPose=Released->GetRelativeTransform();
    const FName ChildProfile=Released->GetCollisionProfileName();const auto ChildCollision=Released->GetCollisionEnabled();
    const auto ChildObjectType=Released->GetCollisionObjectType();const auto ChildResponses=Released->GetCollisionResponseToChannels();
    auto FeatureState=G->HardnessProjection->Fits->ReleaseStates.Last();FDinkFamilyCollisionFitCandidate FeaturePrepared;
    const auto Refuses=[&](const TCHAR* What){TestFalse(What,Families->PrepareCollisionFitReleaseCandidate(Id,FeatureState,FeaturePrepared,Error));};
    Released->SetRelativeLocation(ChildPose.GetLocation()+FVector(1,0,0));Refuses(TEXT("released child pose tamper refuses"));Released->SetRelativeTransform(ChildPose);
    Released->SetMaterial(0,IntactMaterial);Refuses(TEXT("released child material tamper refuses"));Released->SetMaterial(0,VisualMaterials[0]);
    Released->SetStaticMesh(Cube);Refuses(TEXT("released child mesh identity tamper refuses"));Released->SetStaticMesh(VisualMesh);
    Released->SetCanEverAffectNavigation(true);Refuses(TEXT("released child navigation tamper refuses"));Released->SetCanEverAffectNavigation(false);
    Released->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Refuses(TEXT("released child query collision tamper refuses"));
    // SetCollisionEnabled invalidates the named profile; restore the captured full epoch.
    Released->SetCollisionProfileName(ChildProfile);
    TestTrue(TEXT("restored child collision profile and enabled/object/responses are exact"),Released->GetCollisionProfileName()==ChildProfile&&
        Released->GetCollisionEnabled()==ChildCollision&&Released->GetCollisionObjectType()==ChildObjectType&&Released->GetCollisionResponseToChannels()==ChildResponses);
    auto* Duplicate=NewObject<UStaticMeshComponent>(Actor);Duplicate->ComponentTags.Add(TEXT("DinkReleasedFamilyVisual"));Duplicate->RegisterComponent();
    Refuses(TEXT("duplicate dedicated-tag child refuses, even outside actor pointer"));Duplicate->DestroyComponent();
    Actor->PublishedLegacyReleaseWitness.Reset();Refuses(TEXT("visible released child cannot infer missing source witness"));Actor->PublishedLegacyReleaseWitness=MeshWitness;
    if(!TestTrue(TEXT("restored exact released epoch requalifies"),G->RedrawRuntimeHardnessMap(209,Error))){AddError(Error);return false;}
    // Actual source-backed type3 load boundary: remove Director rows, do not manufacture a legacy sprite.
    D->ReleaseScreenSprites(209,{});bool AnySourceRow=false;for(const auto& Pair:D->GetSprites())AnySourceRow|=Pair.Value.Origin==Id;
    TestFalse(TEXT("persisted background load has zero Director rows for origin"),AnySourceRow);
    if(!TestTrue(TEXT("zero-row type3 redraw uses original prebirth admission"),G->RedrawRuntimeHardnessMap(209,Error))){AddError(Error);return false;}
    TestTrue(TEXT("zero-row type3 retains same visible3D child and canonical hidden card"),Actor->ReleasedFamilyArt==Released&&Released->IsVisible()&&Actor->Card->bHiddenInGame&&!G->IsHardnessLoading());
    if(!TestTrue(TEXT("repeat zero-row load is idempotent"),G->RedrawRuntimeHardnessMap(209,Error))){AddError(Error);return false;}
    TestTrue(TEXT("repeat child geometry never compounds"),Released->GetRelativeTransform().Equals(ChildPose,0));
    // Recreate only the legitimate intact live source row; broken-load checks above had none.
    Story->GetWorldState()->ClearOverride(Id);G->EditorHardnessPicture(Id,false,1);G->RecordEditorHardness(Id,0);
    const int32 IntactHandle=D->CreateVirtualSprite(209,Placement->X,Placement->Y);auto* IntactSprite=D->FindSprite(IntactHandle);
    IntactSprite->Actor=Actor;IntactSprite->Origin=Id;IntactSprite->Script=Placement->Script;IntactSprite->bSpawned=false;IntactSprite->Props.Add(TEXT("pseq"),173);IntactSprite->Props.Add(TEXT("pframe"),1);IntactSprite->Props.Add(TEXT("hard"),0);
    if(!TestTrue(TEXT("mesh release witness permits genuine intact restore"),G->RedrawRuntimeHardnessMap(209,Error))){AddError(Error);return false;}
    TestTrue(TEXT("intact restores real body/family and hides mesh/card"),G->FindHardnessFitPrimitive(*D->FindSprite(IntactHandle))&&FamilyMesh->IsVisible()&&!FamilyMesh->bHiddenInGame&&!Released->IsVisible()&&Released->bHiddenInGame&&Actor->Card->bHiddenInGame);
#endif
    return true;
}
