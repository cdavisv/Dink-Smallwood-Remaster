// Included by the ordinary importer: test its actual pure preflight using shipped
// source descriptors, with no private map, generated native asset or bundle fixture.
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFittedGenerationPreflightTest,
    "Dink.Import.Greybox.FittedFoundationPreflight", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDinkFittedGenerationPreflightTest::RunTest(const FString&)
{
    FString Text, Error;
    TArray<FDinkFamilyCollisionFitRule> Rules;
    if (!TestTrue(TEXT("shipped full policy readable"), FFileHelper::LoadFileToString(Text, *DinkArtFamily::DefaultFamiliesPath())) ||
        !TestTrue(TEXT("shipped full policy parses"), DinkFamilyCollisionFit::ParsePolicy(Text, Rules, Error)) ||
        !TestEqual(TEXT("explicit source fixture has85 identities"), Rules.Num(), 85)) return false;
    FDinkBundle Bundle;
    TSet<int32> Selected;
    for (const auto& Rule : Rules)
    {
        if (!Selected.Contains(Rule.Origin.Screen))
        {
            FDinkHardnessFoundationSource Source;
            if (!TestTrue(TEXT("shipped source descriptor loads"), FDinkHardnessFoundationSource::Load(
                FPaths::ProjectContentDir() / FString::Printf(TEXT("Dink/Data/Gameplay/Hardness/Foundations/SCR_%03d.json"), Rule.Origin.Screen),
                Rule.Origin.Screen, Source, Error))) return false;
            FDinkBundleScreen Screen; Screen.Screen = Rule.Origin.Screen;
            Screen.Id = FString::Printf(TEXT("SCR_%03d"), Screen.Screen);
            Screen.Corners = Source.Corners; Screen.CollisionHash = Source.CollisionSourceHash;
            Bundle.ScreenIndex.Add(Screen.Screen, Bundle.Screens.Num());
            Bundle.Screens.Add(Screen);
            FDinkBundleCollision Collision;
            Collision.ByClass.Add(TEXT("fill_solid"), Source.SolidFill);
            Collision.ByClass.Add(TEXT("fill_water"), Source.WaterFill);
            Bundle.Collision.Add(Screen.Id, Collision);
            Selected.Add(Screen.Screen);
        }
        FDinkBundlePlacement Placement;
        Placement.Id = Rule.Origin.ToString(); Placement.Screen = Rule.Origin.Screen;
        Placement.Index = Rule.Origin.Placement; Placement.Hash = Rule.SourceHash;
        Placement.Type = Rule.SourceType; Placement.Script = Rule.SourceScript.IsNone() ? FString() : Rule.SourceScript.ToString();
        Placement.Representation = Rule.IsStaticBackground() ? TEXT("instance") : TEXT("actor");
        Placement.ClassId = TEXT("barrel"); Placement.Seq = 173; Placement.Frame = 1;
        Placement.bHasCard = true; Placement.bHasHardness = true;
        Bundle.Placements.Add(Placement);
    }
    TMap<int32, FFittedScreen> Plan;
    TMap<FString, const FDinkBundlePlacement*> Promoted;
    if (!TestTrue(TEXT("fresh-clone planning needs no generated foundations"),
        PrepareFittedGeneration(Bundle, Selected, Plan, Promoted, Error))) { AddError(Error); return false; }
    TestEqual(TEXT("all38 source screens planned"), Plan.Num(), 38);
    TestEqual(TEXT("three source background promotions planned"), Promoted.Num(), 3);
    for (const auto& Pair : Plan)
        TestTrue(TEXT("pure planning never loads/builds native foundations"),
            Pair.Value.Candidate.FixedSolid == nullptr && Pair.Value.Candidate.FixedLow == nullptr);
    const FString OriginalHash = Bundle.Placements.Last().Hash;
    Bundle.Placements.Last().Hash = FString::ChrN(40, TEXT('0'));
    Plan.Reset(); Promoted.Reset();
    TestFalse(TEXT("a late85th source mismatch rejects before any native work"),
        PrepareFittedGeneration(Bundle, Selected, Plan, Promoted, Error));
    TestTrue(TEXT("late-source failure is explicit"), Error.Contains(TEXT("source placement mismatch")));
    for (const auto& Pair : Plan)
        TestTrue(TEXT("late rejection still owns zero native assets"), !Pair.Value.Candidate.FixedSolid && !Pair.Value.Candidate.FixedLow);
    Bundle.Placements.Last().Hash = OriginalHash;
    const int32 LastScreen = Bundle.Screens.Last().Screen;
    Bundle.Screens.Last().CollisionHash = TEXT("invalid-last-source");
    TSet<int32> Partial; Partial.Add(34);
    Plan.Reset(); Promoted.Reset();
    TestFalse(TEXT("partial import also validates unselected late source descriptor"),
        PrepareFittedGeneration(Bundle, Partial, Plan, Promoted, Error));
    TestTrue(TEXT("late descriptor identity refusal is explicit"), Error.Contains(TEXT("descriptor differs from bundle source")));
    TestTrue(TEXT("late source lies outside partial selection"), !Partial.Contains(LastScreen));
    return true;
}
