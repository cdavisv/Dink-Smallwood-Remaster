#include "DinkTestHelpers.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkLayout.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Hardness/DinkHardnessFoundationSource.h"
#include "Hardness/DinkHardnessPrismComponent.h"
#include "Engine/OverlapResult.h"
#include "Hardness/DinkRuntimeHardnessWorldSubsystem.h"
#include "AssetCompilingManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "Engine/StaticMesh.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerController.h"
#include "GameMapsSettings.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
#include "DinkBarrelRolloutSourcePins.inl"
bool ReadRules(FAutomationTestBase& Test, TArray<FDinkFamilyCollisionFitRule>& Rules)
{
    FString Text, Error;
    if (!Test.TestTrue(TEXT("rollout source policy available"),
        FFileHelper::LoadFileToString(Text, *DinkArtFamily::DefaultFamiliesPath())) ||
        !Test.TestTrue(TEXT("rollout policy parses"), DinkFamilyCollisionFit::ParsePolicy(Text, Rules, Error)))
        return false;
    if (!Test.TestEqual(TEXT("whole rollout has exactly 85 rules"), Rules.Num(), 85)) return false;
    TSet<FString> ExpectedPins;
    for (const TCHAR* Pin : RolloutSourcePins) ExpectedPins.Add(Pin);
    int32 Backgrounds = 0, Anonymous = 0;
    TSet<FString> Origins;
    for (const auto& Rule : Rules)
    {
        Test.TestEqual(TEXT("rollout source hash pinned"), Rule.SourceHash.Len(), 40);
        Test.TestFalse(TEXT("each origin has one rule"), Origins.Contains(Rule.Origin.ToString()));
        Origins.Add(Rule.Origin.ToString());
        const FString Pin = FString::Printf(TEXT("%s|%s|%s|%d"), *Rule.Origin.ToString(),
            *Rule.SourceHash, Rule.SourceScript.IsNone() ? TEXT("") : *Rule.SourceScript.ToString(), Rule.SourceType);
        if (!Test.TestEqual(TEXT("exact frozen source identity present once: ") + Pin, ExpectedPins.Remove(Pin), 1))
            return false;
        Backgrounds += Rule.IsStaticBackground();
        Anonymous += !Rule.IsStaticBackground() && Rule.SourceScript.IsNone();
    }
    if (!Test.TestEqual(TEXT("all frozen source identities consumed"), ExpectedPins.Num(), 0)) return false;
    Test.TestEqual(TEXT("three original backgrounds"), Backgrounds, 3);
    Test.TestEqual(TEXT("eight anonymous original live barrels"), Anonymous, 8);
    for (const TCHAR* Control : {TEXT("S060_P08"), TEXT("S060_P09"), TEXT("S060_P10"), TEXT("S063_P06"),
        TEXT("S063_P07"), TEXT("S096_P06"), TEXT("S222_P06"), TEXT("S222_P07"), TEXT("S222_P08"),
        TEXT("S224_P07"), TEXT("S439_P06"), TEXT("S439_P22")})
        Test.TestFalse(TEXT("soft and authored controls excluded"), Origins.Contains(Control));
    return true;
}

UWorld* LoadRolloutWorld(FAutomationTestBase& Test)
{
    const FString File = FPackageName::LongPackageNameToFilename(
        UGameMapsSettings::GetGameDefaultMap(), FPackageName::GetMapPackageExtension());
    if (!Test.TestTrue(TEXT("ordinary generated world saved"), IFileManager::Get().FileExists(*File)))
        return nullptr;
    UWorld* World = UEditorLoadingAndSavingUtils::LoadMap(File);
    if (!Test.TestNotNull(TEXT("fresh ordinary generated world loads"), World)) return nullptr;
    FAssetCompilingManager::Get().FinishAllCompilation();
    return World;
}

ADinkPlaceholderActor* SourceActor(UWorld& World, const FDinkOriginId& Origin, FAutomationTestBase& Test)
{
    ADinkPlaceholderActor* Found = nullptr;
    for (TActorIterator<ADinkPlaceholderActor> It(&World); It; ++It)
    {
        if (!It->Origin || It->Origin->OriginId != Origin) continue;
        if (It->ActorHasTag(TEXT("DinkRetainedLiveSprite"))) continue;
        if (Found)
        {
            Test.AddError(TEXT("duplicate rollout source actor: ") + Origin.ToString());
            return nullptr;
        }
        Found = *It;
    }
    Test.TestNotNull(TEXT("actual rollout source actor: ") + Origin.ToString(), Found);
    return Found;
}

bool SourceMatches(FAutomationTestBase& Test, ADinkPlaceholderActor& Actor,
    const FDinkFamilyCollisionFitRule& Rule)
{
    return Test.TestTrue(TEXT("saved actor retains exact source identity: ") + Rule.Origin.ToString(),
        Actor.Origin && Actor.Origin->SourceHash == Rule.SourceHash &&
        Actor.Origin->ScriptName == Rule.SourceScript && Actor.Origin->PlacementType == Rule.SourceType &&
        Actor.Origin->Sequence == 173 && Actor.Origin->Frame == 1 && Actor.Origin->ClassId == TEXT("barrel") &&
        Actor.ScreenNumber == Rule.Origin.Screen && Actor.bHasHardness &&
        Actor.ActorHasTag(DinkFamilyCollisionFit::PromotedBackgroundTag) == Rule.IsStaticBackground());
}

FCollisionQueryParams OnlyBody(UWorld& World, UPrimitiveComponent& Body)
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DinkRolloutCardinal), true);
    for (TActorIterator<AActor> It(&World); It; ++It)
    {
        TArray<UPrimitiveComponent*> Components;
        It->GetComponents(Components);
        for (auto* Component : Components)
            if (Component != &Body) Query.AddIgnoredComponent(Component);
    }
    return Query;
}

void WriteRows(FAutomationTestBase& Test, const TArray<TSharedPtr<FJsonValue>>& Rows)
{
    auto Report = MakeShared<FJsonObject>();
    Report->SetArrayField(TEXT("origins"), Rows);
    FString Text;
    FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text));
    const FString Directory = FPaths::ProjectSavedDir() / TEXT("Automation");
    IFileManager::Get().MakeDirectory(*Directory, true);
    Test.TestTrue(TEXT("actual all-origin physics report saved"),
        FFileHelper::SaveStringToFile(Text, *(Directory / TEXT("BarrelRolloutBodies.json"))));
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkRolloutSavedInventory,
    "Dink.Gameplay.BarrelRollout.SavedInventory", DINK_TEST_FLAGS)
bool FDinkRolloutSavedInventory::RunTest(const FString&)
{
    TArray<FDinkFamilyCollisionFitRule> Rules;
    if (!ReadRules(*this, Rules)) return false;
    UWorld* World = LoadRolloutWorld(*this);
    if (!World) return false;
    TMap<int32, ADinkGreyboxScreen*> Hosts;
    TMap<int32, ADinkScreenVolume*> Volumes;
    TSet<int32> Screens;
    for (const auto& Rule : Rules) Screens.Add(Rule.Origin.Screen);
    TestEqual(TEXT("38 affected screens"), Screens.Num(), 38);
    for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It)
    {
        if (It->InstanceOrigins)
            for (const auto& Instance : It->InstanceOrigins->Origins)
                for (const auto& Rule : Rules)
                    TestTrue(TEXT("rollout source represented exactly once"), Instance.OriginId != Rule.Origin);
        if (!Screens.Contains(It->ScreenNumber)) continue;
        TestFalse(TEXT("unique marked foundation host"), Hosts.Contains(It->ScreenNumber));
        Hosts.Add(It->ScreenNumber, *It);
    }
    for (TActorIterator<ADinkScreenVolume> It(World); It; ++It)
    {
        if (!Screens.Contains(It->ScreenNumber)) continue;
        TestFalse(TEXT("unique saved screen volume"), Volumes.Contains(It->ScreenNumber));
        Volumes.Add(It->ScreenNumber, *It);
    }
    for (int32 Screen : Screens)
    {
        auto* Host = Hosts.FindRef(Screen);
        auto* Volume = Volumes.FindRef(Screen);
        if (!TestNotNull(TEXT("saved foundation host"), Host) || !TestNotNull(TEXT("saved screen volume"), Volume))
            return false;
        FDinkHardnessFoundationSource Source;
        FString Error;
        const FString Path = FPaths::ProjectContentDir() / FString::Printf(
            TEXT("Dink/Data/Gameplay/Hardness/Foundations/SCR_%03d.json"), Screen);
        if (!TestTrue(TEXT("foundation source loads"), FDinkHardnessFoundationSource::Load(Path, Screen, Source, Error)) ||
            !TestTrue(TEXT("foundation gameplay inputs match"), Source.VerifyGameplayInputs(Error)) ||
            !TestTrue(TEXT("fresh saved foundation geometry and profile match"),
                Source.VerifyInstances(*Volume, *Host, Error)))
        {
            AddError(Error);
            return false;
        }
    }
    for (const auto& Rule : Rules)
    {
        auto* Actor = SourceActor(*World, Rule.Origin, *this);
        if (!Actor || !SourceMatches(*this, *Actor, Rule)) return false;
        auto* Mesh = LoadObject<UStaticMesh>(nullptr, *Rule.Mesh);
        FDinkFamilyFittedGeometry Geometry;
        FString Error;
        if (!TestNotNull(TEXT("source kit mesh loads"), Mesh) ||
            !TestTrue(TEXT("exact cooked mesh readable"), DinkFamilyCollisionFit::ReadCookedGeometry(*Mesh, Geometry, Error)) ||
            !TestEqual(TEXT("actual canonical cooked surface hash"), Geometry.CanonicalSurfaceSha1, Rule.CanonicalSurfaceSha1))
        {
            AddError(Error);
            return false;
        }
    }
    return true;
}

class FDinkRolloutRuntimeCheck : public IAutomationLatentCommand
{
public:
    FDinkRolloutRuntimeCheck(FAutomationTestBase* InTest, TArray<FDinkFamilyCollisionFitRule> InRules)
        : Test(InTest), Rules(MoveTemp(InRules)), Began(FPlatformTime::Seconds())
    {
        for (const auto& Rule : Rules) Screens.AddUnique(Rule.Origin.Screen);
        Screens.Sort();
    }

    bool Update() override
    {
        if (FPlatformTime::Seconds() - Began > 600)
        {
            Test->AddError(TEXT("whole rollout runtime screen traversal timed out"));
            return true;
        }
        UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
        auto* PC = World ? World->GetFirstPlayerController() : nullptr;
        auto* Hero = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
        auto* Story = World && World->GetGameInstance()
            ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        auto* Greybox = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
        if (!Hero || !Story || !Story->IsReady() || !Greybox) return false;
        auto* Gameplay = Story->GetGameplay();
        auto* Director = Story->GetDirector();
        const double Now = World->GetTimeSeconds();
        if (Now < Until) return false;
        if (ScreenIndex == Screens.Num())
        {
            Test->TestEqual(TEXT("every exact origin has an actual registered body record"), Rows.Num(), Rules.Num());
            WriteRows(*Test, Rows);
            return true;
        }
        const int32 Screen = Screens[ScreenIndex];
        if (!Entered)
        {
            Story->bNewGamePending = false;
            Story->bInstantMode = true;
            if (!Test->TestTrue(TEXT("ordinary entry into rollout screen"), Greybox->GotoScreen(Screen, 300, 200)))
                return true;
            Entered = true;
            Until = Now + .25;
            return false;
        }
        if (!Test->TestEqual(TEXT("requested source screen became current"), Director->GetDink().Screen, Screen) ||
            !Test->TestFalse(TEXT("all-origin initial projection released loading gate"), Gameplay->IsHardnessLoading()))
            return true;
        const auto OriginalOrder = Gameplay->OriginalHardnessPlacementOrder(Screen);
        for (const auto& Rule : Rules)
        {
            if (Rule.Origin.Screen != Screen) continue;
            auto* Actor = SourceActor(*World, Rule.Origin, *Test);
            if (!Actor || !SourceMatches(*Test, *Actor, Rule)) return true;
            const FDinkSprite* ExistingLive=nullptr;int32 ExistingHandle=0;
            for(const auto& Pair:Director->GetSprites())
                if(Pair.Value.bActive&&Pair.Value.Origin==Rule.Origin&&Pair.Value.Actor.Get()==Actor)
                {ExistingLive=&Pair.Value;ExistingHandle=Pair.Key;break;}
            const auto* OriginalPlacement=Gameplay->GetData().FindPlacement(Rule.Origin);
            FString OrderText;for(int32 Index:OriginalOrder)OrderText+=FString::Printf(TEXT("%d,"),Index);
            Test->AddInfo(FString::Printf(TEXT("ORIGINAL_BIRTH origin=%s sourceType=%d static=%d effectiveType=%d override=%d projected=%d capability=%d liveHandle=%d order=[%s]"),
                *Rule.Origin.ToString(),Rule.SourceType,Rule.IsStaticBackground(),
                OriginalPlacement?Gameplay->EffectiveHardnessPlacementType(*OriginalPlacement):-1,
                int32(Story->GetWorldState()->GetOverrideType(Rule.Origin)),Gameplay->UsesOriginalHardnessProjection(Screen),
                World->GetSubsystem<UDinkRuntimeHardnessWorldSubsystem>()->RequiresScreenCapability(Screen),
                ExistingHandle,*OrderText));
            if (!Test->TestEqual(TEXT("original live birth order matches exact source type: ")+Rule.Origin.ToString(),
                OriginalOrder.Contains(Rule.Origin.Placement), !Rule.IsStaticBackground()))
                return true;
            if (!Rule.IsStaticBackground())
            {
                if (!Test->TestTrue(TEXT("original live birth keeps source script identity"),
                    ExistingLive && ExistingLive->bActive && ExistingLive->Actor.Get() == Actor && ExistingLive->Script == Rule.SourceScript))
                    return true;
            }
            FDinkSprite QueryActor;
            QueryActor.Actor = Actor;
            QueryActor.Screen = Screen;
            FString Error;
            auto* Body = Gameplay->FindHardnessFitPrimitive(QueryActor, &Error);
            if (!Test->TestNotNull(TEXT("published actual fitted body for ") + Rule.Origin.ToString(), Body))
            {
                Test->AddError(Error);
                return true;
            }
            UStaticMeshComponent* Family = nullptr;
            TInlineComponentArray<UStaticMeshComponent*> Components(Actor);
            for (auto* Component : Components)
                if (Component->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)) Family = Component;
            if (!Test->TestNotNull(TEXT("actual family component"), Family) ||
                !Test->TestNotNull(TEXT("actual family static mesh"), Family->GetStaticMesh().Get()) ||
                !Test->TestTrue(TEXT("family visible and original card hidden"),
                    Family->IsVisible() && !Family->bHiddenInGame && Actor->Card && Actor->Card->bHiddenInGame))
                return true;
            FDinkFamilyFittedGeometry Geometry;
            if (!Test->TestTrue(TEXT("runtime exact cooked mesh readable"),
                DinkFamilyCollisionFit::ReadCookedGeometry(*Family->GetStaticMesh(), Geometry, Error)))
            {
                Test->AddError(Error);
                return true;
            }
            FBox Expected(ForceInit);
            for (const auto& Vertex : Geometry.Vertices)
                Expected += Family->GetComponentTransform().TransformPosition(FVector(Vertex));
            if (!Test->TestTrue(TEXT("actual fitted extent equals the transformed cooked mesh"),
                Body->Bounds.Origin.Equals(Expected.GetCenter(), .05) &&
                Body->Bounds.BoxExtent.Equals(Expected.GetExtent(), .05)))
                return true;
            const auto* Placement = Gameplay->GetData().FindPlacement(Rule.Origin);
            if (!Test->TestNotNull(TEXT("original gameplay placement"), Placement)) return true;
            const auto* Volume = Greybox->FindScreen(Screen);
            if (!Test->TestNotNull(TEXT("runtime screen volume"), Volume)) return true;
            const FVector Ground = Volume->MapPixelToWorld(float(Placement->X - 20), float(Placement->Y));
            const auto Query = OnlyBody(*World, *Body);
            const auto Capsule = FCollisionShape::MakeCapsule(
                Hero->GetCapsuleComponent()->GetScaledCapsuleRadius(),
                Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
            auto* Host = Cast<ADinkGreyboxScreen>(Body->GetOwner());
            if (!Test->TestTrue(TEXT("actual fitted owner binds the current source screen"),
                Host && Host->ScreenNumber == Screen)) return true;
            int32 MatchingBodies = 0;
            TInlineComponentArray<UDinkHardnessPrismComponent*> OwnedBodies(Host);
            for (auto* Owned : OwnedBodies)
                if (Owned->IsRegistered() && Owned->IsQueryCollisionEnabled() &&
                    Owned->HardnessCode == 100 + Rule.Origin.Placement)
                {
                    ++MatchingBodies;
                    if (!Test->TestTrue(TEXT("no active same-screen legacy prism retains fitted owner code"), Owned == Body))
                        return true;
                }
            if (!Test->TestEqual(TEXT("one active body owns fitted source code"), MatchingBodies, 1)) return true;
            // Scan actual original hardbox cells against the published fitted logical owner.
            FDinkSprite SourceSprite;
            SourceSprite.Origin = Rule.Origin;
            SourceSprite.Screen = Screen;
            SourceSprite.X = Placement->X;
            SourceSprite.Y = Placement->Y;
            SourceSprite.Props.Add(TEXT("pseq"), 173);
            SourceSprite.Props.Add(TEXT("pframe"), 1);
            int32 Left, Top, Right, Bottom;
            bool OwnedCell = false, GapCell = false;
            if (!Test->TestTrue(TEXT("original source hardbox readable"),
                Gameplay->GetHardbox(SourceSprite, Left, Top, Right, Bottom))) return true;
            for (int32 Y = Top + 1; Y < Bottom; ++Y)
                for (int32 X = Left + 1; X < Right; ++X)
                {
                    const int32 Code = Gameplay->GetHard(Screen, X, Y);
                    OwnedCell |= Code == 100 + Rule.Origin.Placement;
                    const FVector Point = Volume->MapPixelToWorld(float(X - 20), float(Y)) + FVector(0,0,90);
                    if (!GapCell && Expected.ComputeSquaredDistanceToPoint(Point) >
                        FMath::Square(Capsule.GetCapsuleRadius() + 2))
                    {
                        if (!Test->TestNotEqual(TEXT("old hardbox gap loses this barrel's logical owner"),
                            Code, 100 + Rule.Origin.Placement)) return true;
                        if (!Test->TestFalse(TEXT("capsule gap clears the actual barrel body"),
                            World->OverlapBlockingTestByChannel(Point, FQuat::Identity, ECC_Pawn, Capsule, Query))) return true;
                        // Unfiltered query retains unrelated valid blockers; report them without claiming global clearance.
                        TArray<FOverlapResult> Hits;
                        World->OverlapMultiByChannel(Hits, Point, FQuat::Identity, ECC_Pawn, Capsule);
                        for (const auto& Hit : Hits)
                        {
                            const auto* Prism = Cast<UDinkHardnessPrismComponent>(Hit.GetComponent());
                            if (!Test->TestFalse(TEXT("unfiltered gap has no same-screen barrel owner overlap"),
                                Prism && Prism->GetOwner() == Host && Prism->HardnessCode == 100 + Rule.Origin.Placement))
                                return true;
                        }
                        Test->AddInfo(FString::Printf(TEXT("%s old-hardbox gap unfiltered overlaps=%d; unrelated blockers retained"),
                            *Rule.Origin.ToString(), Hits.Num()));
                        GapCell = true;
                    }
                }
            if (!Test->TestTrue(TEXT("fitted logical footprint owns an actual original hardbox cell"), OwnedCell) ||
                !Test->TestTrue(TEXT("original hardbox has a capsule-sized released gap"), GapCell)) return true;
            for (const FVector Direction : {FVector(1,0,0), FVector(-1,0,0), FVector(0,1,0), FVector(0,-1,0)})
            {
                FHitResult Hit;
                if (!Test->TestTrue(TEXT("actual Pawn query blocks on fitted mesh from each side"),
                    World->SweepSingleByChannel(Hit, Ground + Direction * 200 + FVector(0,0,90),
                        Ground + FVector(0,0,90), FQuat::Identity, ECC_Pawn, Capsule, Query) &&
                    Hit.GetComponent() == Body))
                    return true;
            }
            auto Row = MakeShared<FJsonObject>();
            Row->SetStringField(TEXT("origin"), Rule.Origin.ToString());
            Row->SetStringField(TEXT("source_hash"), Rule.SourceHash);
            Row->SetStringField(TEXT("script"), Rule.SourceScript.ToString());
            Row->SetBoolField(TEXT("background"), Rule.IsStaticBackground());
            Row->SetStringField(TEXT("body"), Body->GetPathName());
            Row->SetStringField(TEXT("geometry_sha1"), Geometry.CookedGeometrySha1);
            Row->SetStringField(TEXT("surface_sha1"), Geometry.CanonicalSurfaceSha1);
            Row->SetStringField(TEXT("extent_cm"), Body->Bounds.BoxExtent.ToString());
            Row->SetBoolField(TEXT("four_pawn_sweeps"), true);
            Row->SetBoolField(TEXT("logical_owned_cell"), OwnedCell);
            Row->SetBoolField(TEXT("released_old_hardbox_gap"), GapCell);
            Row->SetNumberField(TEXT("active_same_code_prisms"), MatchingBodies);
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
        ++ScreenIndex;
        Entered = false;
        return false;
    }

private:
    FAutomationTestBase* Test;
    TArray<FDinkFamilyCollisionFitRule> Rules;
    TArray<int32> Screens;
    TArray<TSharedPtr<FJsonValue>> Rows;
    double Began;
    double Until = 0;
    int32 ScreenIndex = 0;
    bool Entered = false;
};

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkRolloutRuntimeBodies,
    "Dink.Gameplay.BarrelRollout.AllOriginBodies", DINK_TEST_FLAGS)
bool FDinkRolloutRuntimeBodies::RunTest(const FString&)
{
    TArray<FDinkFamilyCollisionFitRule> Rules;
    if (!ReadRules(*this, Rules) || !LoadRolloutWorld(*this)) return false;
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkRolloutRuntimeCheck(this, MoveTemp(Rules)));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
    return true;
}


class FDinkRolloutBackgroundCheck : public IAutomationLatentCommand
{
public:
    FDinkRolloutBackgroundCheck(FAutomationTestBase* InTest, FDinkFamilyCollisionFitRule InRule)
        : Test(InTest), Rule(MoveTemp(InRule)), Began(FPlatformTime::Seconds()) {}

    bool Update() override
    {
        if (FPlatformTime::Seconds() - Began > 120)
        {
            Test->AddError(TEXT("background lifecycle timed out: ") + Rule.Origin.ToString());
            return true;
        }
        UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
        auto* Story = World && World->GetGameInstance()
            ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        auto* Greybox = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
        if (!Story || !Story->IsReady() || !Greybox) return false;
        const double Now = World->GetTimeSeconds();
        if (Now < Until) return false;
        Story->bNewGamePending = false;
        Story->bInstantMode = true;
        if (Phase == 0)
        {
            if (!Enter(*Greybox)) return true;
            Phase = 1;
            Until = Now + .5;
            return false;
        }
        if (!Check(*World, *Story)) return true;
        if (Phase == 1)
        {
            Overrides = Story->GetWorldState()->ExportOverrides();
            ExitTimes = Story->GetWorldState()->ExportScreenExitTimes();
            GameTimeMs = Story->GetWorldState()->GetGameTimeMs();
            Narrative = Story->SaveStateToJson();
            if (!Test->TestFalse(TEXT("background intact save captured"), Narrative.IsEmpty())) return true;
            if (!Test->TestTrue(TEXT("ordinary background leave"),
                Greybox->GotoScreen(Rule.Origin.Screen == 31 ? 209 : 31)))
                return true;
            Phase = 2;
            Until = Now + .5;
            return false;
        }
        if (Phase == 2)
        {
            if (!Enter(*Greybox)) return true;
            Phase = 3;
            Until = Now + .5;
            return false;
        }
        if (Phase == 3)
        {
            Story->GetWorldState()->ImportState(Overrides, ExitTimes, GameTimeMs);
            if (!Test->TestTrue(TEXT("ordinary background same-screen save restore"),
                Story->LoadStateFromJson(Narrative)))
                return true;
            Phase = 4;
            Until = Now + .5;
            return false;
        }
        return true;
    }

private:
    bool Enter(UDinkGreyboxSubsystem& Greybox)
    {
        return Test->TestTrue(TEXT("ordinary background screen entry"),
            Greybox.GotoScreen(Rule.Origin.Screen, 300, 200));
    }

    bool Check(UWorld& World, UDinkStorySubsystem& Story)
    {
        // The leave phase validates after returning to the source screen.
        if (Phase == 2) return true;
        auto* Gameplay = Story.GetGameplay();
        auto* Actor = SourceActor(World, Rule.Origin, *Test);
        if (!Actor || !SourceMatches(*Test, *Actor, Rule)) return false;
        if (!Test->TestEqual(TEXT("background lifecycle remains on its current source screen"),
            Story.GetDirector()->GetDink().Screen, Rule.Origin.Screen) ||
            !Test->TestFalse(TEXT("background is absent from actual original live birth dispatch"),
                Gameplay->OriginalHardnessPlacementOrder(Rule.Origin.Screen).Contains(Rule.Origin.Placement)) ||
            !Test->TestFalse(TEXT("background body publication releases loading gate"), Gameplay->IsHardnessLoading()))
            return false;
        FDinkSprite QueryActor;
        QueryActor.Actor = Actor;
        QueryActor.Screen = Rule.Origin.Screen;
        FString Error;
        auto* Body = Gameplay->FindHardnessFitPrimitive(QueryActor, &Error);
        if (!Test->TestNotNull(TEXT("background actual body survives entry/reentry/save load"), Body))
        {
            Test->AddError(Error);
            return false;
        }
        auto* Controller = World.GetFirstPlayerController();
        UStaticMeshComponent* Family = nullptr;
        TArray<UStaticMeshComponent*> Components;
        Actor->GetComponents(Components);
        for (auto* Component : Components)
            if (Component->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)) Family = Component;
        return Test->TestNotNull(TEXT("background controller exists"), Controller) &&
            Test->TestFalse(TEXT("background publication releases controller movement"), Controller->IsMoveInputIgnored()) &&
            Test->TestFalse(TEXT("background publication releases Dink"), Story.GetDirector()->GetDink().bFrozen) &&
            Test->TestNotNull(TEXT("background published family component exists"), Family) &&
            Test->TestNotNull(TEXT("background published family mesh exists"), Family->GetStaticMesh().Get()) &&
            Test->TestTrue(TEXT("background retains its visible family and hides its legacy card"),
                Actor->ActorHasTag(UDinkArtFamilySubsystem::FamilyTag) && !Actor->IsHidden() &&
                Family->IsVisible() && !Family->bHiddenInGame && Actor->Card && Actor->Card->bHiddenInGame);
    }

    FAutomationTestBase* Test;
    FDinkFamilyCollisionFitRule Rule;
    double Began;
    double Until = 0;
    int32 Phase = 0;
    FString Narrative;
    TArray<FDinkWorldOverride> Overrides;
    TArray<FDinkScreenExitTime> ExitTimes;
    int64 GameTimeMs = 0;
};

IMPLEMENT_COMPLEX_AUTOMATION_TEST(FDinkRolloutBackgroundLifecycle,
    "Dink.Gameplay.BarrelRollout.BackgroundLifecycle", DINK_TEST_FLAGS)
void FDinkRolloutBackgroundLifecycle::GetTests(TArray<FString>& Names, TArray<FString>& Commands) const
{
    for (const TCHAR* Origin : {TEXT("S034_P49"), TEXT("S034_P50"), TEXT("S469_P16")})
    {
        Names.Add(Origin);
        Commands.Add(Origin);
    }
}
bool FDinkRolloutBackgroundLifecycle::RunTest(const FString& Parameters)
{
    TArray<FDinkFamilyCollisionFitRule> Rules;
    if (!ReadRules(*this, Rules)) return false;
    const auto* Rule = Rules.FindByPredicate([&](const auto& Row)
        { return Row.Origin.ToString() == Parameters; });
    if (!TestTrue(TEXT("promoted background has an exact static rule"), Rule && Rule->IsStaticBackground()) ||
        !LoadRolloutWorld(*this))
        return false;
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkRolloutBackgroundCheck(this, *Rule));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
    return true;
}
