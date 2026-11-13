#include "DinkProbeLoadOracle.h"
#include "DinkProbeLoadTransformDiagnostic.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "UObject/Package.h"

#if WITH_DEV_AUTOMATION_TESTS
namespace
{
UDinkSaveGame* OracleSave(bool Original)
{
    auto* Save=NewObject<UDinkSaveGame>();
    Save->Facts.Add(TEXT("story"),4);
    Save->PlayerStats.Life=17;
    Save->Inventory.Items[0]=TEXT("item-fst");Save->Inventory.ArmedItemSlot=0;
    Save->SubsystemState.Add(TEXT("narrative"),FString::Printf(TEXT("{\"nowMs\":123,\"lastScreen\":1,\"nextInstanceId\":10,\"instances\":[],\"gameplay\":{\"originalHardnessVisitV1\":%s,\"hardnessEditorPicturesV1\":[]}}"),Original?TEXT("true"):TEXT("false")));
    return Save;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkProbePersistentLoadOracle,
    "Dink.Gameplay.ProbeLoadOracle.PersistentDomains",EAutomationTestFlags_ApplicationContextMask|EAutomationTestFlags::ProductFilter)
bool FDinkProbePersistentLoadOracle::RunTest(const FString& Parameters)
{
    auto* Saved=OracleSave(true);
    TestTrue(TEXT("identical persistent state passes"),DinkProbeLoadOracle::PersistentDifferences(*Saved,*Saved).IsEmpty());
    for(int32 Domain=0;Domain<10;++Domain)
    {
        auto* Actual=DuplicateObject<UDinkSaveGame>(Saved,GetTransientPackage());
        switch(Domain)
        {
        case 0:Actual->Facts.Add(TEXT("story"),5);break;
        case 1:Actual->PlayerStats.Life++;break;
        case 2:Actual->Inventory.Items[0]=TEXT("item-sw1");break;
        case 3:Actual->Inventory.ArmedItemSlot=INDEX_NONE;break;
        case 4:Actual->Overrides.AddDefaulted();break;
        case 5:Actual->ScreenExitTimes.AddDefaulted();break;
        case 6:Actual->GameTimeMs++;break;
        case 7:Actual->CurrentScreen++;break;
        case 8:Actual->PlayerTransform.SetLocation(FVector(1,0,0));break;
        case 9:Actual->SubsystemState[TEXT("narrative")].ReplaceInline(TEXT("\"hardnessEditorPicturesV1\":[]"),TEXT("\"hardnessEditorPicturesV1\":[{\"origin\":\"S031_P03\",\"seq\":173,\"frame\":6}]"));break;
        }
        TestFalse(FString::Printf(TEXT("changed persistent domain %d refuses"),Domain),DinkProbeLoadOracle::PersistentDifferences(*Saved,*Actual).IsEmpty());
    }
    auto* FreshRuntime=DuplicateObject<UDinkSaveGame>(Saved,GetTransientPackage());
    FreshRuntime->SubsystemState[TEXT("narrative")].ReplaceInline(TEXT("\"instances\":[]"),TEXT("\"instances\":[{\"id\":10}]"));
    TestTrue(TEXT("fresh VM IDs are not falsely persistent"),DinkProbeLoadOracle::PersistentDifferences(*Saved,*FreshRuntime).IsEmpty());
    // load_game's load_map resets &vision (dink.cpp:1017) and the restarted screen's base script sets it again (1462).
    auto* Vision=DuplicateObject<UDinkSaveGame>(Saved,GetTransientPackage());
    Saved->Facts.Add(TEXT("vision"),1);Vision->Facts.Add(TEXT("vision"),2);
    TestTrue(TEXT("&vision set again by the restarted screen is not a persistent difference"),DinkProbeLoadOracle::PersistentDifferences(*Saved,*Vision).IsEmpty());
    Vision->Facts.Remove(TEXT("story"));
    TestFalse(TEXT("a missing fact still refuses"),DinkProbeLoadOracle::PersistentDifferences(*Saved,*Vision).IsEmpty());
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkProbeSavedBirthOracle,
    "Dink.Gameplay.ProbeLoadOracle.SavedBirthAndArm",EAutomationTestFlags_ApplicationContextMask|EAutomationTestFlags::ProductFilter)
bool FDinkProbeSavedBirthOracle::RunTest(const FString& Parameters)
{
    const auto Plain=DinkProbeLoadOracle::BirthExpectation(1,0,173,1,TEXT("bar-gh"),0,0,0);
    TestTrue(TEXT("authored live birth retains source script and picture"),Plain.Type==1&&Plain.Script==TEXT("bar-gh")&&Plain.Seq==173&&Plain.Frame==1);
    for(int32 Override:{2,3,4,5})
    {
        const auto Birth=DinkProbeLoadOracle::BirthExpectation(1,0,173,1,TEXT("bar-gh"),Override,173,6);
        TestTrue(FString::Printf(TEXT("override %d clears birth main and selects persisted picture/type"),Override),
            Birth.Script.IsNone()&&Birth.Seq==173&&Birth.Frame==6&&!Birth.Removed&&Birth.Type==((Override==2||Override==4)?1:0)&&Birth.Hard==((Override==2||Override==3)?1:0));
    }
    const FString Arm=DinkNarrative::EntryPath(TEXT("item-fst"),TEXT("arm"));
    const TArray<DinkProbeLoadOracle::FProcedureStart> Starts{{10,1000,0,Arm}};
    TestTrue(TEXT("actual arm invocation on same fresh detached ID qualifies"),DinkProbeLoadOracle::HasExactStart(Starts,10,1000,Arm));
    TestFalse(TEXT("missing arm invocation refuses"),DinkProbeLoadOracle::HasExactStart({},10,1000,Arm));
    TestFalse(TEXT("arm on another ID refuses"),DinkProbeLoadOracle::HasExactStart(Starts,11,1000,Arm));
    TestFalse(TEXT("arm on wrong item script refuses"),DinkProbeLoadOracle::HasExactStart(Starts,10,1000,DinkNarrative::EntryPath(TEXT("item-sw1"),TEXT("arm"))));
    auto* Saved=OracleSave(true);auto* Missing=DuplicateObject<UDinkSaveGame>(Saved,GetTransientPackage());
    Missing->SubsystemState[TEXT("narrative")]=TEXT("{\"nowMs\":123,\"lastScreen\":1}");
    TestFalse(TEXT("missing actual gameplay object refuses without dereference"),DinkProbeLoadOracle::PersistentDifferences(*Saved,*Missing).IsEmpty());
    TestFalse(TEXT("missing saved gameplay object refuses without dereference"),DinkProbeLoadOracle::PersistentDifferences(*Missing,*Saved).IsEmpty());
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkProbeFreshLoadOracle,
    "Dink.Gameplay.ProbeLoadOracle.FreshIdentities",EAutomationTestFlags_ApplicationContextMask|EAutomationTestFlags::ProductFilter)
bool FDinkProbeFreshLoadOracle::RunTest(const FString& Parameters)
{
    const TSet<int32> Old{2,8};FString Error;
    const TArray<DinkProbeLoadOracle::FFreshIdentity> Valid{{10,31,true},{11,31,true}};
    TestTrue(TEXT("source-qualified fresh current-screen IDs pass"),DinkProbeLoadOracle::FreshIdentities(Old,10,31,Valid,Error));
    for(int32 Defect=0;Defect<5;++Defect)
    {
        auto Bad=Valid;
        switch(Defect){case 0:Bad[0].Id=8;break;case 1:Bad[0].Id=9;break;case 2:Bad[0].Screen=209;break;case 3:Bad[0].SourceQualified=false;break;case 4:Bad[1].Id=10;break;}
        TestFalse(FString::Printf(TEXT("identity defect %d refuses"),Defect),DinkProbeLoadOracle::FreshIdentities(Old,10,31,Bad,Error));
    }
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkProbeSourceCallOracle,
    "Dink.Gameplay.ProbeLoadOracle.SourceCalls",EAutomationTestFlags_ApplicationContextMask|EAutomationTestFlags::ProductFilter)
bool FDinkProbeSourceCallOracle::RunTest(const FString& Parameters)
{
    // A placement main detaches a spawned global; that global calls a DIFFERENT
    // script via external. Neither child is required to equal a sprite script.
    const TArray<DinkProbeLoadOracle::FProcedureStart> Starts{
        {10,2,0,DinkNarrative::EntryPath(TEXT("source"),TEXT("main"))},
        {11,1000,2,DinkNarrative::EntryPath(TEXT("global"),TEXT("main"))},
        {12,1000,4,DinkNarrative::EntryPath(TEXT("helper"),TEXT("talk"))}};
    const TArray<DinkProbeLoadOracle::FProcedureCall> Calls{
        {10,1,TEXT("spawn"),{TEXT("global")}},
        {11,3,TEXT("external"),{TEXT("helper"),TEXT("talk")}}};
    auto Qualified=DinkProbeLoadOracle::QualifySourceCalls({10},Starts,Calls,10,1000);
    TestTrue(TEXT("literal source spawn/external chain qualifies detached globals"),Qualified.Contains(11)&&Qualified.Contains(12));
    for(int32 Defect=0;Defect<3;++Defect)
    {
        auto BadStarts=Starts;auto BadCalls=Calls;
        if(Defect==0)BadCalls[0].Caller=99;
        else if(Defect==1)BadCalls[0].Args[0]=TEXT("wrong-source");
        else BadStarts[1].Sprite=2;
        Qualified=DinkProbeLoadOracle::QualifySourceCalls({10},BadStarts,BadCalls,10,1000);
        TestFalse(FString::Printf(TEXT("unqualified creation chain %d refuses"),Defect),Qualified.Contains(11)||Qualified.Contains(12));
    }
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkProbeLoadModeOracle,
    "Dink.Gameplay.ProbeLoadOracle.ModeContract",EAutomationTestFlags_ApplicationContextMask|EAutomationTestFlags::ProductFilter)
bool FDinkProbeLoadModeOracle::RunTest(const FString& Parameters)
{
    const auto Original=DinkProbeLoadOracle::Narrative(*OracleSave(true));
    const auto Legacy=DinkProbeLoadOracle::Narrative(*OracleSave(false));
    TestTrue(TEXT("actual saved selected flag chooses restart on unmarked screen"),DinkProbeLoadOracle::OriginalMode(*Original,false));
    TestTrue(TEXT("marked screen chooses restart even for old unselected save"),DinkProbeLoadOracle::OriginalMode(*Legacy,true));
    TestFalse(TEXT("unselected unmarked save retains exact legacy dump comparison"),DinkProbeLoadOracle::OriginalMode(*Legacy,false));
    TestTrue(TEXT("legacy exact positive preserves VM snapshot"),DinkProbeLoadOracle::LegacyLinesEqual(TEXT("fact story=4\ninstance old state0"),TEXT("fact story=4\ninstance old state0")));
    TestFalse(TEXT("legacy runtime state difference still refuses"),DinkProbeLoadOracle::LegacyLinesEqual(TEXT("fact story=4\ninstance old state0"),TEXT("fact story=4\ninstance new state1")));
    TestFalse(TEXT("legacy persistent difference still refuses"),DinkProbeLoadOracle::LegacyLinesEqual(TEXT("fact story=4"),TEXT("fact story=5")));
    return true;
}
#endif

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkProbeStockProjectionOracle,
    "Dink.Gameplay.ProbeLoadOracle.StockProjection",EAutomationTestFlags_ApplicationContextMask|EAutomationTestFlags::ProductFilter)
bool FDinkProbeStockProjectionOracle::RunTest(const FString& Parameters)
{
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
    if(!TestNotNull(TEXT("owned stock-only world"),World))return false;
    ON_SCOPE_EXIT {World->DestroyWorld(false);};
    // CreateWorld already initializes WorldSettings and the persistent level.
    ACharacter* Pawn=World->SpawnActor<ACharacter>();
    if(!TestNotNull(TEXT("owned same-root pawn"),Pawn))return false;
    const FTransform Initial(FRotator(0,180,0),FVector(-183760.15999999997,392550.35499999998,98.149998664855957));
    Pawn->SetActorTransform(Initial,false,nullptr,ETeleportType::TeleportPhysics);
    DinkProbeLoadDiagnostic::FBoundary Before;Before.PawnClass=Pawn->GetClass();Before.Actor=Pawn->GetActorTransform();
    auto* Root=Pawn->GetRootComponent();Before.RootClass=Root->GetClass();Before.Registered=Root->IsRegistered();Before.RelativeRotation=Root->GetRelativeRotation();
    Before.AbsoluteLocation=Root->IsUsingAbsoluteLocation();Before.AbsoluteRotation=Root->IsUsingAbsoluteRotation();Before.AbsoluteScale=Root->IsUsingAbsoluteScale();
    auto* Saved=OracleSave(true);Saved->PlayerTransform=FTransform(FRotator(0,-90,0),FVector(65133.07178933332,56192.182237999979,98));
    TArray<uint8> SavedBytesBefore,SavedBytesAfter;TestTrue(TEXT("serialize raw saved bytes"),UGameplayStatics::SaveGameToMemory(Saved,SavedBytesBefore));
    FTransform Applied;FString Reason;
    if(!TestTrue(TEXT("actual stock reference qualifies"),DinkProbeLoadDiagnostic::StockProjection(*Pawn,Before,Saved->PlayerTransform,Applied,Reason)))
    {AddError(Reason);return false;}
    auto* Expected=DuplicateObject<UDinkSaveGame>(Saved,GetTransientPackage());Expected->PlayerTransform=Applied;
    TestTrue(TEXT("actual independent pawn applies saved transform"),Pawn->SetActorTransform(Saved->PlayerTransform,false,nullptr,ETeleportType::TeleportPhysics));
    auto* Actual=DuplicateObject<UDinkSaveGame>(Saved,GetTransientPackage());Actual->PlayerTransform=Pawn->GetActorTransform();
    TestTrue(TEXT("independent actual pawn matches qualified stock reference exactly"),Actual->PlayerTransform.Equals(Applied,0));
    TestTrue(TEXT("qualified exact projection passes"),DinkProbeLoadOracle::PersistentDifferences(*Expected,*Actual).IsEmpty());
    for(int32 Channel=0;Channel<3;++Channel)
    {
        Actual->PlayerTransform=Applied;
        if(Channel==0)Actual->PlayerTransform.AddToTranslation(FVector(1,0,0));
        if(Channel==1)Actual->PlayerTransform.SetRotation(FRotator(0,3,0).Quaternion()*Applied.GetRotation());
        if(Channel==2)Actual->PlayerTransform.SetScale3D(FVector(1.1,1,1));
        TestFalse(FString::Printf(TEXT("projection rejects changed transform channel %d"),Channel),DinkProbeLoadOracle::PersistentDifferences(*Expected,*Actual).IsEmpty());
    }
    auto Bad=Before;Bad.RelativeRotation.Yaw+=7;
    TestFalse(TEXT("inconsistent preload cache rejects reference"),DinkProbeLoadDiagnostic::StockProjection(*Pawn,Bad,Saved->PlayerTransform,Applied,Reason));
    Bad=Before;Bad.Parent=true;
    TestFalse(TEXT("attached preload rejects reference"),DinkProbeLoadDiagnostic::StockProjection(*Pawn,Bad,Saved->PlayerTransform,Applied,Reason));
    Bad=Before;Bad.Registered=false;
    TestFalse(TEXT("unregistered preload rejects reference"),DinkProbeLoadDiagnostic::StockProjection(*Pawn,Bad,Saved->PlayerTransform,Applied,Reason));
    Actual->PlayerTransform=Saved->PlayerTransform;Actual->PlayerTransform.AddToTranslation(FVector(1,0,0));
    TestFalse(TEXT("default oracle remains raw exact"),DinkProbeLoadOracle::PersistentDifferences(*Saved,*Actual).IsEmpty());
    TestTrue(TEXT("serialize saved after projection"),UGameplayStatics::SaveGameToMemory(Saved,SavedBytesAfter));
    TestTrue(TEXT("raw saved bytes unchanged"),SavedBytesBefore==SavedBytesAfter);
    return true;
}
#endif
