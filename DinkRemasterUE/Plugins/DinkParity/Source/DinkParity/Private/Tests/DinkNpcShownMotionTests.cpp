// Dink.Animation.NpcShownMotion: what is DRAWN of a walking humanoid NPC, frame by frame, in the real
// game loop. The scripts move an NPC's actor after its components have ticked, so a test of the
// smoothing maths alone (Dink.Animation.NpcSmoothPresentation) passed while the game showed Mother
// stepping forward with every scripted pixel and back on the next frame, and flipping to a new facing
// for one frame at every turn (owner, 13 Nov 2026: "the mother's stuttered walk"). This test reads the
// body's world transform at the end of every frame of a PIE session and holds it to: no backward
// frames and a steady speed during a steady walk, a turn rate within the limit, and no more walk-cycle
// starts and stops than the script's own. It also runs her wandering with the fix switched off
// (dink.Npc.LatePresent 0) and requires the measure to find the old defect there.
#include "DinkTestHelpers.h"
#include "DinkBodyAnimInstance.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkHumanoidComponent.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "AssetCompilingManager.h"
#include "Editor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
struct FDinkShownSample
{
    FVector Actor = FVector::ZeroVector, Body = FVector::ZeroVector;
    float BodyYaw = 0.f, AnimSpeed = 0.f, Dt = 0.f;
    int32 Dir = 0, Action = 0;
    bool bMoving = false;
};

struct FDinkShownStats
{
    int32 Frames = 0, Backward = 0;
    double Mean = 0, Deviation = 0, Min = 0, Max = 0;
};

/** Speed of the shown body along the direction the script travels, over samples [From, To). */
FDinkShownStats MeasureAlong(const TArray<FDinkShownSample>& S, int32 From, int32 To)
{
    FDinkShownStats R;
    if (To - From < 3) return R;
    const FVector Heading = (S[To - 1].Actor - S[From].Actor).GetSafeNormal2D();
    TArray<double> Speeds;
    for (int32 I = From + 1; I < To; ++I)
    {
        const double Along = FVector::DotProduct(S[I].Body - S[I - 1].Body, Heading);
        Speeds.Add(Along / FMath::Max(1e-4f, S[I].Dt));
        R.Backward += Along < -.02;
    }
    R.Frames = Speeds.Num();
    R.Min = FMath::Min(Speeds); R.Max = FMath::Max(Speeds);
    for (const double V : Speeds) R.Mean += V / Speeds.Num();
    for (const double V : Speeds) R.Deviation += FMath::Square(V - R.Mean) / Speeds.Num();
    R.Deviation = FMath::Sqrt(R.Deviation);
    return R;
}

/** Fastest change of the shown facing, degrees per second, over samples [From, To). */
double FastestTurn(const TArray<FDinkShownSample>& S, int32 From, int32 To)
{
    double Fastest = 0;
    for (int32 I = FMath::Max(1, From + 1); I < To; ++I)
        Fastest = FMath::Max(Fastest, double(FMath::Abs(FMath::FindDeltaAngleDegrees(S[I - 1].BodyYaw, S[I].BodyYaw)) / FMath::Max(1e-4f, S[I].Dt)));
    return Fastest;
}

class FDinkNpcShownMotionCheck : public IAutomationLatentCommand
{
public:
    explicit FDinkNpcShownMotionCheck(FAutomationTestBase* InTest) : Test(InTest) {}

    bool Update() override
    {
        if (!Began) Began = FPlatformTime::Seconds();
        UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
        APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
        ADinkGreyboxCharacter* Hero = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
        UDinkStorySubsystem* Story = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (FPlatformTime::Seconds() - Began > 400) { Test->AddError(TEXT("NPC shown motion: timed out")); return Finish(); }
        if (!Hero || !Story || Story->bNewGamePending) return false;
        UDinkDirector* D = Story->GetDirector();
        UDinkGameplay* Game = Story->GetGameplay();
        if (!D || !Game) return false;
        if (!Mother)
        {
            FAssetCompilingManager::Get().FinishAllCompilation();
            for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
                if (It->Origin && It->Origin->OriginId.ToString() == TEXT("S001_P26")) { MotherActor = *It; Mother = It->FindComponentByClass<UDinkHumanoidComponent>(); }
            for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites()) if (MotherActor.IsValid() && Pair.Value.Actor.Get() == MotherActor.Get()) Handle = Pair.Key;
            if (!Test->TestNotNull(TEXT("Mother has her authored body"), Mother) || !Test->TestTrue(TEXT("Mother's sprite found"), Handle != 0) ||
                !Test->TestTrue(TEXT("Mother uses the native body animation"), Mother->UsesBodyAnimation())) return Finish();
            PaceMode = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Npc.HumanPace"));
            LatePresent = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Npc.LatePresent"));
            TurnRate = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Npc.TurnRateDeg"));
            if (!Test->TestNotNull(TEXT("dink.Npc.HumanPace"), PaceMode) || !Test->TestNotNull(TEXT("dink.Npc.LatePresent"), LatePresent) || !Test->TestNotNull(TEXT("dink.Npc.TurnRateDeg"), TurnRate)) return Finish();
            PaceMode->Set(2); // the pace a person playing sees (automated runs default to the original speed)
            Game->bBrainsEnabled = true;
        }
        FDinkSprite* M = D->FindSprite(Handle);
        if (!M || !MotherActor.IsValid()) { Test->AddError(TEXT("Mother's sprite went away")); return Finish(); }
        ++Frame;
        // The opening talk: skip it, then take her out of the scene's hands.
        if (Stage == 0)
        {
            if (Frame % 10 == 0) Story->SkipDialogue();
            if (Frame < 150) return false;
            Next(1);
        }
        FDinkShownSample Now;
        Now.Actor = MotherActor->GetActorLocation();
        Now.Body = Mother->GetComponentLocation();
        Now.BodyYaw = float(Mother->GetComponentRotation().Yaw);
        Now.Dt = World->GetDeltaSeconds();
        Now.Dir = M->Dir; Now.Action = M->Action; Now.bMoving = M->bMoving;
        if (const UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(Mother->GetAnimInstance())) Now.AnimSpeed = Body->GetSpeed();
        Samples.Add(Now);
        const int32 N = Samples.Num();
        const float TurnLimit = TurnRate->GetFloat() * 1.05f + 10.f;

        switch (Stage)
        {
        case 1: // a scripted move (move / move_stop): its position advances evenly, so it must be shown evenly
            if (N == 1)
            {
                LatePresent->Set(1);
                M->bFrozen = false;
                Game->bBrainsEnabled = false; // only the scripted move moves her
                D->StartMove(*M, 6, int32(M->X) + 70);
            }
            if (N > 400) { Test->AddError(TEXT("the scripted move did not end")); return Finish(); }
            if (M->bMoving || N < MoveEnd + 45) { if (M->bMoving) MoveEnd = N; return false; }
            {
                // Steady part: from 0.6 s after the start (the ramp up) to the script's last step.
                const FDinkShownStats Walk = MeasureAlong(Samples, 36, MoveEnd);
                Test->AddInfo(FString::Printf(TEXT("scripted move of 70 px: %d steady frames, shown speed mean %.1f cm/s, deviation %.1f, min %.1f, max %.1f; frames moving backwards %d"),
                    Walk.Frames, Walk.Mean, Walk.Deviation, Walk.Min, Walk.Max, Walk.Backward));
                Test->TestTrue(TEXT("a steady scripted walk has enough frames to judge"), Walk.Frames >= 30);
                Test->TestEqual(TEXT("a steady scripted walk never draws the body moving backwards"), Walk.Backward, 0);
                Test->TestTrue(TEXT("a steady scripted walk is drawn at a steady speed (deviation under 8 cm/s)"), Walk.Deviation < 8.);
                Test->TestTrue(TEXT("...at the human pace, not above it"), Walk.Mean > 90. && Walk.Max < 150.);
                Test->TestTrue(TEXT("the body ends on the scripted position"), FVector::Dist2D(Samples.Last().Body, Samples.Last().Actor) < 3.);
            }
            Next(2);
            return false;
        case 2: // a turn on the spot by the script (sp_dir)
            if (N == 1) D->SpriteProperty(nullptr, TEXT("dir"), Handle, 4);
            if (N < 90) return false;
            {
                const double Turn = FastestTurn(Samples, 0, N);
                Test->AddInfo(FString::Printf(TEXT("scripted about-turn: fastest shown turn %.0f deg/s (limit %.0f)"), Turn, TurnRate->GetFloat()));
                Test->TestTrue(TEXT("an about-turn is eased, never a flip"), Turn <= TurnLimit);
            }
            Next(3);
            return false;
        case 3: // her own wandering brain with the end-of-frame step off: the 13 Nov build. The measure must see its defect...
        case 4: // ...and as shipped it must be gone.
        {
            const bool bOff = Stage == 3;
            if (N == 1) { LatePresent->Set(bOff ? 0 : 1); Game->bBrainsEnabled = true; M->bFrozen = false; M->Action = 0; M->MoveWaitMs = 0.; }
            // Stretches of steady walking: the brain walks in one direction; skip the first 0.6 s (the ramp) of each.
            int32 Stretches = 0, WalkFrames = 0, Backward = 0, ScriptFlips = 0, ShownFlips = 0, ScriptTurns = 0;
            double WorstDeviation = 0, WorstMax = 0;
            if (N < 1500 || (N % 300) != 0) return false; // judged at 25 s, then every 5 s up to 60 s until she has walked and turned
            for (int32 I = 0; I < N;)
            {
                int32 J = I;
                while (J < N && Samples[J].Action == 2 && Samples[J].Dir == Samples[I].Dir && Samples[I].Action == 2) ++J;
                if (J - I > 80 && FVector::Dist2D(Samples[J - 1].Actor, Samples[I].Actor) > 40.)
                {
                    const FDinkShownStats Walk = MeasureAlong(Samples, I + 36, J);
                    ++Stretches; WalkFrames += Walk.Frames; Backward += Walk.Backward;
                    WorstDeviation = FMath::Max(WorstDeviation, Walk.Deviation); WorstMax = FMath::Max(WorstMax, Walk.Max);
                }
                I = FMath::Max(J, I + 1);
            }
            for (int32 I = 1; I < N; ++I)
            {
                ScriptFlips += (Samples[I].Action == 2) != (Samples[I - 1].Action == 2);
                ShownFlips += (Samples[I].AnimSpeed > 15.f) != (Samples[I - 1].AnimSpeed > 15.f);
                ScriptTurns += Samples[I].Dir != Samples[I - 1].Dir;
            }
            if ((Stretches < 2 || ScriptTurns < 1) && N < 3600) return false;
            const double Turn = FastestTurn(Samples, 0, N);
            Test->AddInfo(FString::Printf(TEXT("wandering for %.0f s, end-of-frame step %s: %d steady stretches, %d frames; frames moving backwards %d; worst deviation %.1f cm/s, fastest frame %.1f cm/s; %d script turns, fastest shown turn %.0f deg/s; walk cycle starts+stops %d against the brain's %d"),
                N / 60., bOff ? TEXT("OFF (the 13 Nov build)") : TEXT("on"), Stretches, WalkFrames, Backward, WorstDeviation, WorstMax, ScriptTurns, Turn, ShownFlips, ScriptFlips));
            Test->TestTrue(TEXT("she walked and turned (steady stretches to judge)"), Stretches >= 1 && WalkFrames >= 60 && ScriptTurns >= 1);
            if (bOff)
            {
                Test->TestTrue(TEXT("the measure sees the old defect: without the end-of-frame step the body is drawn moving backwards on some frames"), Backward > 0 && WorstDeviation > 40.);
                Test->TestTrue(TEXT("the measure sees the old defect: the body flips to a new facing within one frame"), Turn > 2000.);
                Next(4);
                return false;
            }
            Test->TestEqual(TEXT("wandering never draws the body moving backwards along its walk"), Backward, 0);
            Test->TestTrue(TEXT("wandering is drawn at a steady speed (deviation under 8 cm/s)"), WorstDeviation < 8.);
            Test->TestTrue(TEXT("...and never faster than a walk"), WorstMax < 150.);
            Test->TestTrue(TEXT("every turn of the wandering body is eased"), Turn <= TurnLimit);
            Test->TestTrue(TEXT("the walk cycle starts and stops no more often than her brain walks and stands"), ShownFlips <= ScriptFlips + 2);
            return Finish();
        }
        default:
            return Finish();
        }
    }

private:
    void Next(int32 NewStage) { Stage = NewStage; Samples.Reset(); MoveEnd = 0; }
    bool Finish()
    {
        if (PaceMode) PaceMode->Set(1);
        if (LatePresent) LatePresent->Set(1);
        return true;
    }
    FAutomationTestBase* Test;
    TWeakObjectPtr<AActor> MotherActor;
    UDinkHumanoidComponent* Mother = nullptr;
    IConsoleVariable* PaceMode = nullptr;
    IConsoleVariable* LatePresent = nullptr;
    IConsoleVariable* TurnRate = nullptr;
    TArray<FDinkShownSample> Samples;
    double Began = 0;
    int32 Handle = 0, Frame = 0, Stage = 0, MoveEnd = 0;
};

/** The game loop of a person playing is not the automation default: 60 rendered frames a second, each one world tick. */
class FDinkFixedStepCommand : public IAutomationLatentCommand
{
public:
    explicit FDinkFixedStepCommand(bool bInOn) : bOn(bInOn) {}
    bool Update() override
    {
        static bool bWasFixed = false; static double WasDelta = 0;
        if (bOn) { bWasFixed = FApp::UseFixedTimeStep(); WasDelta = FApp::GetFixedDeltaTime(); FApp::SetFixedDeltaTime(1. / 60.); FApp::SetUseFixedTimeStep(true); }
        else { FApp::SetUseFixedTimeStep(bWasFixed); FApp::SetFixedDeltaTime(WasDelta); }
        return true;
    }
private:
    bool bOn;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNpcShownMotionTest, "Dink.Animation.NpcShownMotion", DINK_TEST_FLAGS)
bool FDinkNpcShownMotionTest::RunTest(const FString&)
{
    if (!IFileManager::Get().FileExists(*(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/animation_pass.json"))))
    { AddWarning(TEXT("skipped: animation pass manifest absent")); return true; }
    const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook"), FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("real player map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FDinkFixedStepCommand(true));
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkNpcShownMotionCheck(this));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
    ADD_LATENT_AUTOMATION_COMMAND(FDinkFixedStepCommand(false));
    return true;
}
