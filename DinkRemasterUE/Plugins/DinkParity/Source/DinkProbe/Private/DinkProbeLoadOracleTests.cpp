#include "DinkProbeLoadOracle.h"
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
