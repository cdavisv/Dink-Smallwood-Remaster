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
    const FString Valid = TEXT("{\"schema\":\"dinkex.runtime-hardness/1\",\"width\":600,\"height\":400,\"vision\":-1,")
        TEXT("\"skipped_tile_indices\":[],\"ordered_stamps\":[{\"owner\":13,\"code\":113,\"rect\":[379,291,416,312],\"warp\":false}],\"tile_base_rle\":[")
        + FString::Join(Rows, TEXT(",")) + TEXT("]}");
    FDinkRuntimeHardnessSource Source;
    FString Error;
    if (!TestTrue(TEXT("write owned synthetic fixture"), FFileHelper::SaveStringToFile(Valid, *File))) return false;
    TestTrue(TEXT("strict source accepts complete base and signed vision"), FDinkRuntimeHardnessSource::Load(File, -1, Source, Error));
    TestEqual(TEXT("all explicit tile bytes"), static_cast<int32>(Source.TileBase.size()), 240000);
    TestEqual(TEXT("exact owner preserved"), Source.InitialStamps.empty() ? 0 : static_cast<int32>(Source.InitialStamps[0].Code), 113);
    TestFalse(TEXT("consumer vision mismatch refuses"), FDinkRuntimeHardnessSource::Load(File, 0, Source, Error));
    const TArray<TPair<FString,FString>> Faults = {
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
    TestFalse(TEXT("editor carry refuses before corrupting persistent origin"),D->CarryOriginalLiveSprites(209,Error));
    TestEqual(TEXT("refused editor actor keeps source screen"),Live->Screen,10);
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
    if(!TestNotNull(TEXT("actual initialized story"),Story))return false;
    Story->bNewGamePending=false;Story->bRunScreenScripts=true;
    constexpr int32 MissingFoundationScreen=999999;
    auto* Host=World->SpawnActor<ADinkGreyboxScreen>();Host->ScreenNumber=MissingFoundationScreen;
    Host->Tags.Add(TEXT("DinkHardnessWorldV1"));
    auto* Card=World->SpawnActor<ADinkPlaceholderActor>();
    Card->ScreenNumber=MissingFoundationScreen;Card->Vision=2;Card->ApplyScreenVision(0);
    auto* D=Story->GetDirector();auto* G=Story->GetGameplay();D->GetDink().Screen=MissingFoundationScreen;
    Story->LastScreen=MissingFoundationScreen;
    TestTrue(TEXT("actual marker independent of sidecars"),G->RequiresOriginalHardnessScreen(MissingFoundationScreen));
    Story->GetFacts()->SetFact(TEXT("vision"),2);
    TestTrue(TEXT("ordinary marked live fact leaves placeholder visibility at published epoch"),Card->IsHidden());
    TestFalse(TEXT("ordinary marked live fact leaves actor collision at published epoch"),Card->GetActorEnableCollision());
    // A missing foundation must actively attempt/reject SAME-screen load, not
    // restore LastScreen and return success with a permanently stale map.
    const FString Saved=Story->SaveStateToJson();
    AddExpectedError(TEXT("hardness screen admission refused"),EAutomationExpectedErrorFlags::Contains,1);
    // ReportError normally logs this as an error as well.
    AddExpectedError(TEXT("marked-world saved screen admission failed"),EAutomationExpectedErrorFlags::Contains,1);
    TestFalse(TEXT("same-screen marked load without foundations fails admission"),Story->LoadStateFromJson(Saved));
    TestTrue(TEXT("failed marked load holds movement/script gate"),G->IsHardnessLoading());
    Host->Tags.Remove(TEXT("DinkHardnessWorldV1"));
    TestTrue(TEXT("unmarked legacy saved load keeps its supported resume behavior"),Story->LoadStateFromJson(Saved));
    TestFalse(TEXT("legacy load releases only old hardness gate"),G->IsHardnessLoading());
    return true;
}
