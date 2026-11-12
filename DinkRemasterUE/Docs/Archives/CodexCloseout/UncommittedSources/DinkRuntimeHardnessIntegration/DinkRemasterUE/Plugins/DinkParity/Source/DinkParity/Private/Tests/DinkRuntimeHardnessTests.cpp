#include "DinkTestHelpers.h"
#include "DinkGameplay.h"
#include "Hardness/DinkRuntimeHardnessSource.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Guid.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkRuntimeHardnessSourceContract,
    "Dink.Gameplay.Hardness.SourceContract", DINK_TEST_FLAGS)
bool FDinkRuntimeHardnessSourceContract::RunTest(const FString& Parameters)
{
    const FString Directory = FPaths::ProjectSavedDir() / TEXT("Automation/RuntimeHardness") / FGuid::NewGuid().ToString();
    IFileManager::Get().MakeDirectory(*Directory, true);
    ON_SCOPE_EXIT { IFileManager::Get().DeleteDirectory(*Directory, false, true); };
    const FString File = Directory / TEXT("source.json");
    TArray<FString> Rows;
    for (int32 Y = 0; Y < 400; ++Y) Rows.Add(TEXT("[[600,0]]"));
    TArray<FString> HardFlags;for(int32 I=1;I<=99;++I)HardFlags.Add(I==99?TEXT("-7"):TEXT("0"));
    const FString Valid = TEXT("{\"schema\":\"dinkex.runtime-hardness/2\",\"width\":600,\"height\":400,\"vision\":-1,")
        TEXT("\"skipped_tile_indices\":[],\"ordered_stamps\":[{\"owner\":13,\"code\":113,\"rect\":[379,291,416,312],\"warp\":false}],\"tile_base_rle\":[")
        + FString::Join(Rows, TEXT(",")) + TEXT("],\"editor_hard_flags\":[")+FString::Join(HardFlags,TEXT(","))+TEXT("]}");
    FDinkRuntimeHardnessSource Source;
    FString Error;
    if (!TestTrue(TEXT("write owned synthetic fixture"), FFileHelper::SaveStringToFile(Valid, *File))) return false;
    TestTrue(TEXT("strict source accepts complete base and signed vision"), FDinkRuntimeHardnessSource::Load(File, -1, Source, Error));
    TestEqual(TEXT("all explicit tile bytes"), static_cast<int32>(Source.TileBase.size()), 240000);
    TestEqual(TEXT("exact owner preserved"), Source.InitialStamps.empty() ? 0 : static_cast<int32>(Source.InitialStamps[0].Code), 113);
    TestFalse(TEXT("consumer vision mismatch refuses"), FDinkRuntimeHardnessSource::Load(File, 0, Source, Error));
    TestEqual(TEXT("inactive raw editor flag retained"),Source.EditorHard[99],-7);
    const TArray<TPair<FString,FString>> Faults = {
        {TEXT("\"editor_hard_flags\":"),TEXT("\"missing_editor_hard_flags\":")},
        {TEXT("-7]"),TEXT("true]")},
        {TEXT("-7]"),TEXT("2147483648]")},
        {TEXT(",0,-7]"),TEXT(",-7]")},
        {TEXT("\"width\":600"), TEXT("\"width\":true")},
        {TEXT("\"vision\":-1,"), TEXT("")},
        {TEXT("\"vision\":-1"), TEXT("\"vision\":true")},
        {TEXT("\"skipped_tile_indices\":[]"), TEXT("\"skipped_tile_indices\":[7]")},
        {TEXT("[[600,0]]"), TEXT("[[600,113]]")},
        {TEXT("[[600,0]]"), TEXT("[[599,0]]")},
        {TEXT("\"code\":113"), TEXT("\"code\":114")}
    };
    for (const auto& Fault : Faults)
    {
        const FString Bad = Valid.Replace(*Fault.Key, *Fault.Value);
        TestTrue(TEXT("write own fault fixture"), FFileHelper::SaveStringToFile(Bad, *File));
        TestFalse(*FString::Printf(TEXT("refuse %s"), *Fault.Key), FDinkRuntimeHardnessSource::Load(File, -1, Source, Error));
        TestEqual(TEXT("invalid load never replaces prior complete base"), static_cast<int32>(Source.TileBase.size()), 240000);
        TestEqual(TEXT("invalid load never replaces raw inactive flag"),Source.EditorHard[99],-7);
        TestEqual(TEXT("invalid load never replaces prior owner"), Source.InitialStamps.empty() ? 0 : static_cast<int32>(Source.InitialStamps[0].Code), 113);
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkRuntimeHardnessAdmissionRefusal,
    "Dink.Gameplay.Hardness.AdmissionRefusal", DINK_TEST_FLAGS)
bool FDinkRuntimeHardnessAdmissionRefusal::RunTest(const FString& Parameters)
{
    UDinkGameplay* Game = NewObject<UDinkGameplay>();
    FString Error;
    TestFalse(TEXT("no physical owner cannot activate transition maps"), Game->AdmitRuntimeHardness(209, 0, nullptr, Error));
    TestFalse(TEXT("missing target cannot redraw"), Game->RedrawRuntimeHardness(123456, Error));
    int32 Code = 9;
    TestFalse(TEXT("legacy map has no falsely activated runtime state"), Game->TryRuntimeHardnessCode(209, 0, 390, 300, Code));
    TestEqual(TEXT("refusal does not write output code"), Code, 9);
    const FDinkOriginId Barrel(209,13);
    TestEqual(TEXT("independent editor sequence setter"), Game->EditorHardnessPicture(Barrel, true, 173), 173);
    TestEqual(TEXT("independent editor frame setter"), Game->EditorHardnessPicture(Barrel, false, 6), 6);
    TestEqual(TEXT("frame does not overwrite sequence"), Game->EditorHardnessPicture(Barrel, true, -1), 173);
    TestEqual(TEXT("sequence does not overwrite frame"), Game->EditorHardnessPicture(Barrel, false, -1), 6);
    TestEqual(TEXT("invalid negative editor slot"), Game->EditorHardnessPicture(FDinkOriginId(209,-1), true, 1), -1);
    TestEqual(TEXT("invalid zero editor slot"), Game->EditorHardnessPicture(FDinkOriginId(209,0), true, 1), -1);
    TestEqual(TEXT("invalid high editor slot"), Game->EditorHardnessPicture(FDinkOriginId(209,100), true, 1), -1);
    TestEqual(TEXT("sequence wraps unsigned16"), Game->EditorHardnessPicture(Barrel, true, 65537), 1);
    TestEqual(TEXT("sequence signed wrap unsigned16"), Game->EditorHardnessPicture(Barrel, true, -2), 65534);
    TestEqual(TEXT("frame wraps unsigned8"), Game->EditorHardnessPicture(Barrel, false, 257), 1);
    TestEqual(TEXT("frame signed wrap unsigned8"), Game->EditorHardnessPicture(Barrel, false, -2), 254);
    TestEqual(TEXT("minus one remains getter"), Game->EditorHardnessPicture(Barrel, true, -1), 65534);
    return true;
}

#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "Hardness/DinkHardnessActivation.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Engine/Engine.h"
#include "Engine/World.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHardnessAdapterTransitions,
    "Dink.Gameplay.Hardness.AdapterTransitions", DINK_TEST_FLAGS)
bool FDinkHardnessAdapterTransitions::RunTest(const FString& Parameters)
{
    UDinkFactSubsystem* Facts=DinkTest::MakeFacts(*this);
    auto* Story=NewObject<UDinkStorySubsystem>(DinkTest::MakeOuterGameInstance());
    FString Error;
    if(!TestTrue(TEXT("actual standalone story"),Story->SetupStandalone(Facts,DinkTest::MakeWorldState(),&Error)))return false;
    auto* D=Story->GetDirector();auto* G=Story->GetGameplay();
    const int32 Old=D->CreateVirtualSprite(1,230,177);
    FDinkScriptInstance Caller;
    Caller.Id=71;Caller.Sprite=Old;Caller.AttachedTo=Old;
    Caller.Vars.Add(TEXT("current_sprite"),Old);Caller.Vars.Add(TEXT("current_script"),71);
    Caller.Vars.Add(TEXT("v_return"),0);
    Story->GetStory().SetInt(TEXT("current_sprite"),Old);
    Story->GetStory().SetInt(TEXT("v_return"),1234);
    DinkHardness::PreserveForceVisionCaller(Caller,UDinkDirector::HandleNoSprite);
    Story->SwapOut(Caller);Story->SwapIn(Caller);
    TestEqual(TEXT("post-force cached special derives from caller sprite"),Caller.Vars.FindRef(TEXT("current_sprite")),1000);
    TestEqual(TEXT("post-force actual Ink argument derives from caller sprite"),Story->GetStory().GetInt(TEXT("current_sprite"),-1),1000);
    TestEqual(TEXT("ordinary caller continuation value survives"),Story->GetStory().GetInt(TEXT("v_return"),-1),1234);
    D->SpriteProperty(&Caller,TEXT("x"),Story->GetStory().GetInt(TEXT("current_sprite"),-1),999);
    TestEqual(TEXT("subsequent sp_x(current_sprite) cannot mutate old placement"),D->FindSprite(Old)->X,230.0);

    auto* Live=D->FindSprite(Old);Live->Props.Add(TEXT("live"),1);
    Live->Props.Add(TEXT("brain"),12);Live->Props.Add(TEXT("size"),100);
    Live->Props.Add(TEXT("brain_parm"),120);Live->Props.Add(TEXT("timing"),0);
    TestTrue(TEXT("actual dynamic live carry"),D->CarryOriginalLiveSprites(10,Error));
    D->GetDink().Screen=10;
    TestEqual(TEXT("live now belongs to current screen"),Live->Screen,10);
    TestEqual(TEXT("live engine X preserved"),Live->X,230.0);
    TestEqual(TEXT("live engine Y preserved"),Live->Y,177.0);
    G->TickBrains(34);
    TestTrue(TEXT("actual current-screen brain loop still thinks retained live sprite"),Live->GetProp(TEXT("size"))>100);
    Live->Origin=FDinkOriginId(1,13);
    TestTrue(TEXT("headless editor survivor carries without source-origin remap"),D->CarryOriginalLiveSprites(209,Error));
    TestEqual(TEXT("retained editor now uses current screen"),Live->Screen,209);
    const FDinkOriginId Owner=G->OriginalHardnessOwnerOrigin(*Live);
    TestEqual(TEXT("hardness owner domain follows current screen"),Owner.Screen,209);
    TestEqual(TEXT("original sp_index remains13"),Owner.Placement,13);
    TestEqual(TEXT("persistent editor source identity remains unchanged"),Live->Origin.Screen,1);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHardnessMarkedLoadAndVision,
    "Dink.Gameplay.Hardness.MarkedLoadAndLazyVision", DINK_TEST_FLAGS)
bool FDinkHardnessMarkedLoadAndVision::RunTest(const FString& Parameters)
{
    UGameInstance* GI=NewObject<UGameInstance>(GEngine);GI->InitializeStandalone();
    UWorld* World=GI->GetWorld();
    ON_SCOPE_EXIT {GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);};
    auto* Story=GI->GetSubsystem<UDinkStorySubsystem>();
    if(!TestNotNull(TEXT("actual initialized story"),Story)||!TestTrue(TEXT("actual story dataset ready"),Story->IsReady()&&Story->GetGameplay()->HasData()))return false;
    Story->bNewGamePending=false;Story->bRunScreenScripts=true;
    constexpr int32 MissingFoundationScreen=999999;
    auto* Host=World->SpawnActor<ADinkGreyboxScreen>();Host->ScreenNumber=MissingFoundationScreen;
    Host->Tags.Add(TEXT("DinkHardnessWorldV1"));
    auto* Card=World->SpawnActor<ADinkPlaceholderActor>();
    Card->ScreenNumber=MissingFoundationScreen;Card->Vision=2;Card->ApplyScreenVision(0);
    auto* D=Story->GetDirector();auto* G=Story->GetGameplay();D->GetDink().Screen=MissingFoundationScreen;
    Story->LastScreen=MissingFoundationScreen;
    Story->GetFacts()->SetFact(TEXT("player_map"),MissingFoundationScreen);
    auto* Greybox=World->GetSubsystem<UDinkGreyboxSubsystem>();
    if(!TestNotNull(TEXT("actual greybox vision registry"),Greybox))return false;
    Greybox->RegisterVisionPlaceholder(Card);
    TestTrue(TEXT("actual marker independent of sidecars"),G->RequiresOriginalHardnessScreen(MissingFoundationScreen));
    Story->GetFacts()->SetFact(TEXT("vision"),2);
    TestTrue(TEXT("ordinary marked live fact leaves placeholder visibility at published epoch"),Card->IsHidden());
    TestFalse(TEXT("ordinary marked live fact leaves actor collision at published epoch"),Card->GetActorEnableCollision());
    // A missing foundation must actively attempt/reject SAME-screen load, not
    // restore LastScreen and return success with a permanently stale map.
    AddExpectedError(TEXT("marked draw_hard_map refused"),EAutomationExpectedErrorFlags::Contains,1);
    G->DrawHardMap(MissingFoundationScreen);
    TestNull(TEXT("marked full redraw cannot allocate PR41 legacy map"),G->GetLiveHardness(MissingFoundationScreen));
    TestTrue(TEXT("unadmitted marked redraw holds capability gate"),G->IsHardnessLoading());
    const FString Saved=Story->SaveStateToJson();
    AddExpectedError(TEXT("hardness screen admission refused"),EAutomationExpectedErrorFlags::Contains,1);
    // ReportError normally logs this as an error as well.
    AddExpectedError(TEXT("marked-world saved screen admission failed"),EAutomationExpectedErrorFlags::Contains,1);
    TestFalse(TEXT("same-screen marked load without foundations fails admission"),Story->LoadStateFromJson(Saved));
    TestTrue(TEXT("failed marked load holds movement/script gate"),G->IsHardnessLoading());
    Host->Tags.Remove(TEXT("DinkHardnessWorldV1"));
    TestTrue(TEXT("unmarked legacy saved load keeps its supported resume behavior"),Story->LoadStateFromJson(Saved));
    TestFalse(TEXT("legacy load releases only old hardness gate"),G->IsHardnessLoading());
    Story->GetFacts()->SetFact(TEXT("vision"),0);
    Story->GetFacts()->SetFact(TEXT("vision"),2);
    TestFalse(TEXT("unmarked legacy positive control still applies registered placeholder vision"),Card->IsHidden());
    TestTrue(TEXT("unmarked legacy positive control still enables its actor collision"),Card->GetActorEnableCollision());
    return true;
}

#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"
#include "DinkOriginComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "Engine/StaticMesh.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkScriptSpriteComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHardnessEditorCarryActor,
    "Dink.Gameplay.Hardness.EditorCarryActorOwnership",DINK_TEST_FLAGS)
bool FDinkHardnessEditorCarryActor::RunTest(const FString& Parameters)
{
    UGameInstance* GI=NewObject<UGameInstance>(GEngine);GI->InitializeStandalone();
    UWorld* World=GI->GetWorld();
    ON_SCOPE_EXIT {GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);};
    auto* Story=GI->GetSubsystem<UDinkStorySubsystem>();if(!TestNotNull(TEXT("story"),Story)||!TestTrue(TEXT("story dataset ready"),Story->IsReady()&&Story->GetGameplay()->HasData()))return false;
    Story->bRunScreenScripts=false;Story->bNewGamePending=false;
    auto* D=Story->GetDirector();auto* G=Story->GetGameplay();
    const auto* Eligible=G->GetData().FindPlacement(FDinkOriginId(209,13));
    if(!TestNotNull(TEXT("actual eligible editor source"),Eligible))return false;
    TestEqual(TEXT("source remains an eligible live record"),Eligible->Type,1);
    auto* Before=World->SpawnActor<ADinkScreenVolume>();Before->ScreenNumber=209;
    Before->Corners.NW={0,0};Before->Corners.NE={6,0};Before->Corners.SW={0,4};Before->Corners.SE={6,4};
    auto* After=World->SpawnActor<ADinkScreenVolume>();After->ScreenNumber=10;
    After->Corners.NW={20,30};After->Corners.NE={26,30};After->Corners.SW={20,34};After->Corners.SE={26,34};
    auto* Source=World->SpawnActor<ADinkWarpPlaceholderActor>();
    Source->Origin->OriginId=FDinkOriginId(209,13);Source->ScreenNumber=209;
    Source->Vision=7;Source->ApplyScreenVision(7);
    Source->Card->SetMobility(EComponentMobility::Movable);
    Source->SetActorLocation(FVector(Eligible->X-20,Eligible->Y,45));
    Source->SetActorScale3D(FVector(1.2,0.8,1.1));
    Source->Card->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Source->Card->SetCollisionResponseToAllChannels(ECR_Ignore);
    Source->Card->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);
    Source->Warp->bTriggerEnabled=true;
    // Exact PR40 construction pattern: runtime instance child, root attachment,
    // NoCollision/navfalse/overlapfalse, hidden old card, FamilyArt tag.
    auto* Family=NewObject<UStaticMeshComponent>(Source,TEXT("FamilyArt"));
    Family->SetMobility(EComponentMobility::Movable);Family->SetupAttachment(Source->GetRootComponent());
    auto* FamilyMesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Dink/Kits/Stonebrook/SM_Barrel_Oak_01.SM_Barrel_Oak_01"));
    if(!TestNotNull(TEXT("actual PR40 barrel family mesh fixture"),FamilyMesh))return false;
    Family->SetStaticMesh(FamilyMesh);
    Family->SetCollisionEnabled(ECollisionEnabled::NoCollision);Family->SetCanEverAffectNavigation(false);
    Family->SetGenerateOverlapEvents(false);Family->ComponentTags.Add(TEXT("DinkFamilyArt"));
    const FTransform FamilyTransform=DinkArtFamily::MeshTransform(FamilyMesh->GetBoundingBox(),FVector(34,-12,0),17,1.0f);
    Family->SetRelativeTransform(FamilyTransform);Source->AddInstanceComponent(Family);Family->RegisterComponent();
    Source->Tags.Add(TEXT("DinkFamilyArt"));Source->Card->SetHiddenInGame(true);
    UMaterialInterface* Parent=FamilyMesh->GetMaterial(0);if(!Parent)Parent=UMaterial::GetDefaultMaterial(MD_Surface);
    auto* SourceMID=UMaterialInstanceDynamic::Create(Parent,Family);
    FScalarParameterValue Parameter;Parameter.ParameterInfo=FMaterialParameterInfo(TEXT("DinkCarryFrame"));Parameter.ParameterValue=17;
    SourceMID->ScalarParameterValues.Add(Parameter);Family->SetMaterial(0,SourceMID);
    const FTransform SourceTransform=Source->GetActorTransform();
    const FCollisionResponseContainer Responses=Source->Card->GetCollisionResponseToChannels();
    const int32 Handle=D->HandleForActor(Source);auto* S=D->FindSprite(Handle);
    if(!TestNotNull(TEXT("editor source sprite"),S))return false;
    S->X=Eligible->X;S->Y=Eligible->Y;S->Props.Add(TEXT("live"),1);S->Props.Add(TEXT("hard"),0);
    D->SpriteProperty(nullptr,TEXT("pseq"),Handle,32);D->SpriteProperty(nullptr,TEXT("pframe"),Handle,1);
    auto* SourceScript=Source->FindComponentByClass<UDinkScriptSpriteComponent>();
    const int32 SurvivorSlot=G->InspectOriginalShadowSlot(Handle);
    FString Error;TestTrue(*FString::Printf(TEXT("same-screen full-rebuild carry prelude: %s"),*Error),D->CarryOriginalLiveSprites(209,Error));
    auto* Copy=Cast<ADinkWarpPlaceholderActor>(S->Actor.Get());
    if(!TestNotNull(TEXT("runtime native template retains actor class"),Copy))return false;
    TestTrue(TEXT("source and runtime actors independent"),Copy!=Source);
    UStaticMeshComponent* CopyFamily=nullptr;
    TInlineComponentArray<UStaticMeshComponent*> Children(Copy);
    for(auto* C:Children)if(C->GetFName()==TEXT("FamilyArt"))CopyFamily=C;
    if(!TestNotNull(TEXT("actual PR40 runtime FamilyArt child was duplicated"),CopyFamily))return false;
    TestTrue(TEXT("family child independent owner and outer"),CopyFamily!=Family&&CopyFamily->GetOwner()==Copy&&CopyFamily->GetOuter()==Copy);
    TestTrue(TEXT("family child attaches to clone root"),CopyFamily->GetAttachParent()==Copy->GetRootComponent());
    TestTrue(TEXT("family relative transform retained"),CopyFamily->GetRelativeTransform().Equals(FamilyTransform));
    TestTrue(TEXT("family actual mesh retained"),CopyFamily->GetStaticMesh()==Family->GetStaticMesh());
    TestTrue(TEXT("actual family child follows new screen frame"),(CopyFamily->GetComponentLocation()-Family->GetComponentLocation()).Equals(FVector::ZeroVector,0.01));
    TestTrue(TEXT("old card remains hidden while family remains visible"),Copy->Card->bHiddenInGame&&!CopyFamily->bHiddenInGame);
    TestTrue(TEXT("source old card/family visibility unchanged"),Source->Card->bHiddenInGame&&!Family->bHiddenInGame);
    auto* CopyMID=Cast<UMaterialInstanceDynamic>(CopyFamily->GetMaterial(0));
    if(!TestNotNull(TEXT("family material instance retained"),CopyMID))return false;
    TestTrue(TEXT("material override instance detached from source"),CopyMID!=SourceMID&&CopyMID->GetOuter()==Copy);
    TestEqual(TEXT("family material slot count retained"),CopyFamily->GetNumMaterials(),Family->GetNumMaterials());
    for(int32 I=1;I<Family->GetNumMaterials();++I)TestTrue(TEXT("family immutable material slot retained"),CopyFamily->GetMaterial(I)==Family->GetMaterial(I));
    TestEqual(TEXT("actual MID override count retained"),CopyMID->ScalarParameterValues.Num(),1);
    if(CopyMID->ScalarParameterValues.Num()!=1)return false;
    TestEqual(TEXT("actual MID override retained"),CopyMID->ScalarParameterValues[0].ParameterValue,17.0f);
    CopyMID->ScalarParameterValues[0].ParameterValue=91;
    TestEqual(TEXT("runtime material mutation cannot change source MID"),SourceMID->ScalarParameterValues[0].ParameterValue,17.0f);
    D->SpriteProperty(nullptr,TEXT("pseq"),Handle,173);
    auto* CopyScript=Copy->FindComponentByClass<UDinkScriptSpriteComponent>();
    if(!TestNotNull(TEXT("runtime script binding retained"),CopyScript)||!TestNotNull(TEXT("source script snapshot"),SourceScript))return false;
    TestEqual(TEXT("runtime pseq mutation reaches clone only"),CopyScript->Props.FindRef(TEXT("pseq")),173);
    TestEqual(TEXT("source pseq snapshot unchanged"),SourceScript->Props.FindRef(TEXT("pseq")),32);
    TestEqual(TEXT("source stale runtime handle explicitly detached"),SourceScript->Handle,0);
    TestTrue(TEXT("source FamilyArt transform unchanged"),Family->GetRelativeTransform().Equals(FamilyTransform));
    TestTrue(TEXT("persistent source transform untouched"),Source->GetActorTransform().Equals(SourceTransform));
    TestTrue(TEXT("runtime actor uses new map frame and floor-relative height"),Copy->GetActorLocation().Equals(SourceTransform.GetLocation(),0.01));
    TestTrue(TEXT("template scale retained"),Copy->GetActorScale3D().Equals(SourceTransform.GetScale3D(),0.001));
    TestTrue(TEXT("actual render mesh retained"),Copy->Card->GetStaticMesh()==Source->Card->GetStaticMesh());
    TestEqual(TEXT("material slot count retained"),Copy->Card->GetNumMaterials(),Source->Card->GetNumMaterials());
    for(int32 I=0;I<Source->Card->GetNumMaterials();++I)TestTrue(TEXT("actual material retained"),Copy->Card->GetMaterial(I)==Source->Card->GetMaterial(I));
    TestTrue(TEXT("source warp binding untouched"),Source->Warp->bTriggerEnabled);
    TestTrue(TEXT("all64 actor collision responses retained"),Copy->Card->GetCollisionResponseToChannels()==Responses);
    TestEqual(TEXT("actual collision enabled retained"),Copy->Card->GetCollisionEnabled(),Source->Card->GetCollisionEnabled());
    TestTrue(TEXT("source origin unchanged"),Source->Origin->OriginId==FDinkOriginId(209,13));
    TestFalse(TEXT("runtime copy has no persistent placement origin"),Copy->Origin->OriginId.IsValid());
    TestTrue(TEXT("sprite retains original script/source origin"),S->Origin==FDinkOriginId(209,13));
    TestTrue(TEXT("source-index copy excluded"),Copy->ActorHasTag(TEXT("DinkRetainedLiveSprite")));
    TestEqual(TEXT("live copy is not gated by old placement vision"),Copy->Vision,0);
    TestFalse(TEXT("old source warp not duplicated into new map"),Copy->Warp->bTriggerEnabled);
    TestEqual(TEXT("old source warp collision disabled"),Copy->Warp->GetCollisionEnabled(),ECollisionEnabled::NoCollision);
    const FDinkOriginId Owner=G->OriginalHardnessOwnerOrigin(*S);
    TestTrue(TEXT("hardness owner current-map domain"),Owner==FDinkOriginId(209,13));
    // The actual full rebuild uses this private reservation helper before it
    // binds the same persistent actor to a NEW eligible placement birth.
    G->BeginOriginalIdentityScreen(209);G->PrepareLegacyOriginalIdentity(209);
    const int32 Fresh=D->HandleForPlacement(209,13);
    S=D->FindSprite(Handle); // TMap growth may relocate records
    TestTrue(TEXT("source placement can bind fresh handle without stealing survivor"),Fresh!=Handle&&Fresh>1);
    TestTrue(TEXT("fresh source handle binds original actor"),D->GetActor(Fresh)==Source);
    TestTrue(TEXT("same-screen survivor and rebirth have distinct ordered shadow slots"),G->InspectOriginalShadowSlot(Handle)==SurvivorSlot&&G->InspectOriginalShadowSlot(Fresh)>SurvivorSlot);
    TestTrue(TEXT("rebirth does not steal survivor actor"),D->GetActor(Handle)==Copy);
    TestTrue(TEXT("both original source identities coexist"),D->FindSprite(Fresh)->Origin==S->Origin&&S->Origin==FDinkOriginId(209,13));
    TestTrue(TEXT("both current owner domains remain editor113"),G->OriginalHardnessOwnerOrigin(*D->FindSprite(Fresh))==FDinkOriginId(209,13)&&G->OriginalHardnessOwnerOrigin(*S)==FDinkOriginId(209,13));
    TestTrue(TEXT("new birth still uses independent original MID"),Family->GetMaterial(0)==SourceMID&&CopyFamily->GetMaterial(0)==CopyMID&&CopyMID!=SourceMID);
    TestTrue(TEXT("survivor can subsequently cross to another screen"),D->CarryOriginalLiveSprites(10,Error));
    TestTrue(TEXT("cross-screen retained family body follows target frame"),(CopyFamily->GetComponentLocation()-Family->GetComponentLocation()).Equals(FVector(2000,3000,0),0.01));
    TestTrue(TEXT("persistent source actor stays anchored after cross"),Source->GetActorTransform().Equals(SourceTransform));
    TestTrue(TEXT("cross-screen current owner changes without changing source"),G->OriginalHardnessOwnerOrigin(*S)==FDinkOriginId(10,13)&&S->Origin==FDinkOriginId(209,13));
    D->DeactivateSprite(Handle,0,false);
    TestTrue(TEXT("destroying transient survivor preserves source actor"),IsValid(Source));
    TestTrue(TEXT("fresh source binding still independent"),D->GetActor(Fresh)==Source);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHardnessShadowRoundTrip,
    "Dink.Gameplay.Hardness.ShadowAcrossProjectionSelection",DINK_TEST_FLAGS)
bool FDinkHardnessShadowRoundTrip::RunTest(const FString& Parameters)
{
    UGameInstance* GI=NewObject<UGameInstance>(GEngine);GI->InitializeStandalone();
    UWorld* World=GI->GetWorld();
    ON_SCOPE_EXIT {GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);};
    auto* Story=GI->GetSubsystem<UDinkStorySubsystem>();if(!TestNotNull(TEXT("actual story"),Story)||!TestTrue(TEXT("actual dataset ready"),Story->IsReady()&&Story->GetGameplay()->HasData()))return false;
    Story->bRunScreenScripts=true;Story->bNewGamePending=false;
    auto* D=Story->GetDirector();auto* G=Story->GetGameplay();
    auto* First=World->SpawnActor<ADinkGreyboxScreen>();First->ScreenNumber=1;First->Tags.Add(TEXT("DinkHardnessWorldV1"));
    auto* Last=World->SpawnActor<ADinkGreyboxScreen>();Last->ScreenNumber=209;Last->Tags.Add(TEXT("DinkHardnessWorldV1"));
    const int32 Survivor=D->CreateVirtualSprite(1,230,177);
    D->FindSprite(Survivor)->Props.Add(TEXT("live"),1);
    D->FindSprite(Survivor)->Props.Add(TEXT("brain"),12);
    D->FindSprite(Survivor)->Props.Add(TEXT("size"),100);
    D->FindSprite(Survivor)->Props.Add(TEXT("brain_parm"),140);
    D->FindSprite(Survivor)->Props.Add(TEXT("timing"),0);
    const int32 SurvivorSlot=G->InspectOriginalShadowSlot(Survivor);
    TestTrue(TEXT("all director births observed before map admission"),SurvivorSlot>1);
    // These deliberately incomplete tagged hosts must reject physical admission.
    // The fixture tests the ACTUAL bookkeeping/legacy round trip independently;
    // it does not claim a registered-body or successful map-admission pass.
    AddExpectedError(TEXT("hardness screen admission refused"),EAutomationExpectedErrorFlags::Contains,2);
    Story->OnScreenEntered(1);
    TestTrue(TEXT("incomplete marked host holds physical gate"),G->IsHardnessLoading());
    TestEqual(TEXT("map admission failure does not erase live lifetime"),G->InspectOriginalShadowSlot(Survivor),SurvivorSlot);
    Story->OnScreenEntered(10); // shipped empty screen, unmarked PR41 route
    TestFalse(TEXT("unmarked execution remains available without V2 admission"),G->IsHardnessLoading());
    TestEqual(TEXT("SelectLegacy retains actual survivor slot"),G->InspectOriginalShadowSlot(Survivor),SurvivorSlot);
    TestEqual(TEXT("actual carried sprite now thinks on legacy screen"),D->FindSprite(Survivor)->Screen,10);
    G->TickBrains(34);
    TestTrue(TEXT("actual legacy brain loop continues survivor"),D->FindSprite(Survivor)->GetProp(TEXT("size"))>100);
    const int32 Temporary=D->CreateVirtualSprite(10,250,170);
    const int32 ReleasedSlot=G->InspectOriginalShadowSlot(Temporary);
    D->DeactivateSprite(Temporary,0,false);
    const int32 NewLive=D->CreateVirtualSprite(10,260,180);D->FindSprite(NewLive)->Props.Add(TEXT("live"),1);
    TestEqual(TEXT("legacy release and new birth reuse free shadow slot"),G->InspectOriginalShadowSlot(NewLive),ReleasedSlot);
    TestTrue(TEXT("UE handles remain unchanged and independent"),NewLive!=Temporary&&NewLive!=Survivor);
    Story->OnScreenEntered(209);
    TestEqual(TEXT("marked reselection retains carried slot across legacy"),G->InspectOriginalShadowSlot(Survivor),SurvivorSlot);
    TestEqual(TEXT("marked reselection retains legacy-born live slot"),G->InspectOriginalShadowSlot(NewLive),ReleasedSlot);
    TestEqual(TEXT("actual survivor screen follows reselection"),D->FindSprite(Survivor)->Screen,209);
    return true;
}

#include "AssetCompilingManager.h"
#include "DinkLayout.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHardnessRetainedLegacyOwner,
    "Dink.Gameplay.Hardness.RetainedLegacyCurrentOwner",DINK_TEST_FLAGS)
bool FDinkHardnessRetainedLegacyOwner::RunTest(const FString& Parameters)
{
    UStaticMesh* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    FAssetCompilingManager::Get().FinishAllCompilation();
    if(!TestNotNull(TEXT("engine cube"),Cube))return false;
    UGameInstance* GI=NewObject<UGameInstance>(GEngine);GI->InitializeStandalone();
    UWorld* World=GI->GetWorld();
    ON_SCOPE_EXIT {GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);};
    auto* Story=GI->GetSubsystem<UDinkStorySubsystem>();
    if(!TestNotNull(TEXT("story"),Story)||!TestTrue(TEXT("actual dataset"),Story->IsReady()&&Story->GetGameplay()->HasData()))return false;
    Story->bRunScreenScripts=false;Story->bNewGamePending=false;
    auto* G=Story->GetGameplay();auto* D=Story->GetDirector();
    constexpr int32 Current=10;
    TestNull(TEXT("current editor13 is inactive/absent from active placements"),G->GetData().FindPlacement(FDinkOriginId(Current,13)));
    TArray<FString> Flags;for(int32 I=1;I<=99;++I)Flags.Add(I==13?TEXT("200"):TEXT("0"));
    const FString Json=TEXT("{\"schema\":\"dinkex.editor-hard/1\",\"screen\":10,\"map_record\":1,\"editor_hard_flags\":[")+FString::Join(Flags,TEXT(","))+TEXT("]}");
    FDinkEditorHardSource Raw;FString Error;
    if(!TestTrue(TEXT("strict independent current-map flags parse"),FDinkEditorHardSource::Parse(Json,Current,Raw,Error)))return false;
    auto& Data=const_cast<FDinkGameplayData&>(G->GetData());Data.EditorHardFlags.Add(Current,Raw.EditorHard);
    FDinkEditorHardSource Preserved=Raw;
    TestFalse(TEXT("bool raw flag rejects"),FDinkEditorHardSource::Parse(Json.Replace(TEXT("200"),TEXT("true")),Current,Preserved,Error));
    TestEqual(TEXT("failed flag read preserves current inactive200"),Preserved.EditorHard[13],200);
    TestFalse(TEXT("wrong current screen rejects"),FDinkEditorHardSource::Parse(Json,11,Preserved,Error));
    auto Map=MakeShared<FDinkHardnessMap>();Map->Screen=Current;Map->Codes.SetNumZeroed(600*400);Data.SetHardnessOverride(Current,Map);
    auto* Greybox=World->GetSubsystem<UDinkGreyboxSubsystem>();
    auto* Volume=World->SpawnActor<ADinkScreenVolume>();Volume->ScreenNumber=Current;
    Volume->Corners.NW={0,0};Volume->Corners.NE={6,0};Volume->Corners.SW={0,4};Volume->Corners.SE={6,4};Greybox->RegisterScreen(Volume);
    ON_SCOPE_EXIT {Greybox->UnregisterScreen(Volume);};
    auto* Host=World->SpawnActorDeferred<ADinkGreyboxScreen>(ADinkGreyboxScreen::StaticClass(),FTransform(FVector(300,200,-50)));
    Host->ScreenNumber=Current;Host->CollisionSolid->SetStaticMesh(Cube);Host->CollisionSolid->SetRelativeScale3D(FVector(6,4,1));
    Host->FinishSpawning(FTransform(FVector(300,200,-50))); // floor only, no baked obstacle
    TestFalse(TEXT("legacy destination has no marked-map authority"),G->RequiresOriginalHardnessScreen(Current));
    const int32 Retained=D->CreateVirtualSprite(209,230,177);
    auto* S=D->FindSprite(Retained);S->Origin=FDinkOriginId(209,13);S->HardnessEditorIndex=13;
    S->Props.Add(TEXT("live"),1);S->Props.Add(TEXT("hard"),0);S->Props.Add(TEXT("pseq"),173);S->Props.Add(TEXT("pframe"),1);
    TestTrue(TEXT("actual virtual editor carry"),D->CarryOriginalLiveSprites(Current,Error));
    Story->GetFacts()->SetFact(TEXT("player_map"),Current);D->GetDink().Screen=Current;
    FDinkScriptInstance Caller;Caller.Id=6001;Caller.Sprite=Retained;Caller.Screen=Current;
    auto Cmd=[&](const FString& Text){D->Execute(Caller,FDinkStoryLine::Parse(TEXT(">> ")+Text,{TEXT("cmd"),TEXT("src:1")}));};
    auto Blocked=[&](){FHitResult Hit;return World->LineTraceSingleByChannel(Hit,FVector(180,177,150),FVector(245,177,150),ECC_Pawn);};
    Cmd(TEXT("draw_hard_map"));
    TestEqual(TEXT("inactive current raw200 is soft despite survivor own hard0"),G->GetHard(Current,230,177),0);
    TestFalse(TEXT("no legacy prism for soft current editor flag"),Blocked());
    Cmd(FString::Printf(TEXT("sp_hard %d 0"),Retained));Cmd(TEXT("draw_hard_map"));
    TestEqual(TEXT("retained editor stamps113, never dynamic1"),G->GetHard(Current,230,177),113);
    TestTrue(TEXT("sp_hard writes current-map visit flag"),G->VisitPlacementHard.Contains(FDinkOriginId(Current,13))&&G->VisitPlacementHard.FindRef(FDinkOriginId(Current,13))==0);
    TestFalse(TEXT("old persistent source flag was not written"),G->VisitPlacementHard.Contains(FDinkOriginId(209,13)));
    TestTrue(TEXT("actual legacy physical route blocks new current-owner stamp"),Blocked());
    TestNotNull(TEXT("one PR41 runtime proxy owns legacy result"),Greybox->GetRuntimeSolidCollision(Current));
    Cmd(FString::Printf(TEXT("sp_hard %d 1"),Retained));Cmd(FString::Printf(TEXT("draw_hard_sprite %d"),Retained));
    TestEqual(TEXT("current-owner softness clears113"),G->GetHard(Current,230,177),0);
    TestFalse(TEXT("actual legacy physical route clears obstacle"),Blocked());
    FHitResult Floor;
    TestTrue(TEXT("unrelated floor remains"),World->LineTraceSingleByChannel(Floor,FVector(100,100,200),FVector(100,100,-200),ECC_Pawn));
    TestTrue(TEXT("persistent source identity never remapped"),D->FindSprite(Retained)->Origin==FDinkOriginId(209,13));
    TestFalse(TEXT("raw flag bridge did not activate marked projection"),G->UsesOriginalHardnessProjection(Current));
    // Ordinary cross-origin PR41 sprites retain their prior dynamic-code route;
    // the current-editor branch is limited to explicitly retained editors.
    D->FindSprite(Retained)->bRetainedOriginalEditor=false;
    D->SpriteProperty(&Caller,TEXT("hard"),Retained,0);Cmd(TEXT("draw_hard_map"));
    TestEqual(TEXT("ordinary PR41 cross-origin sprite still stamps dynamic1"),G->GetHard(Current,230,177),1);
    return true;
}
