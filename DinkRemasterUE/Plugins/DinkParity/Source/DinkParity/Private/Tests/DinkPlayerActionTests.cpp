#include "DinkTestHelpers.h"
#include "DinkArtSubsystem.h"
#include "DinkPlayerActionComponent.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkSaveGame.h"
#include "DinkSaveSubsystem.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/BlendSpace.h"
#include "AnimationRuntime.h"
#include "DinkBodyAnimInstance.h"
#include "DinkHumanoidComponent.h"
#include "Engine/SkeletalMesh.h"
#include "EngineUtils.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "DinkOriginComponent.h"
#include "AssetCompilingManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/FileManager.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
/** Planted-foot drift of a posed mesh that travels along its facing (+Y in mesh space) at Speed. */
struct FDinkSlideProbe
{
    struct FPoint { int32 Bone; FVector Local; FVector Previous; bool bPrevious = false; };
    TArray<FPoint> Points;
    double Max = 0, Sum = 0, Signed = 0; int32 Samples = 0;
    void Init(USkeletalMeshComponent* Mesh)
    {
        const FReferenceSkeleton& Ref = Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
        for (const TCHAR* Side : {TEXT("l"), TEXT("r")})
        {
            const int32 Foot = Ref.FindBoneIndex(FName(*FString::Printf(TEXT("foot_%s"), Side)));
            if (Foot == INDEX_NONE) continue;
            const FTransform Rest = FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, Foot);
            const FVector Ankle = Rest.GetLocation();
            // Heel: 7.8 cm behind the ankle; ball: 14.9 cm ahead; both on the sole (the same points the source build measures).
            Points.Add({Foot, Rest.InverseTransformPosition(FVector(Ankle.X, Ankle.Y - 7.8, 0.))});
            Points.Add({Foot, Rest.InverseTransformPosition(FVector(Ankle.X, Ankle.Y + 14.9, 0.))});
        }
    }
    void Sample(USkeletalMeshComponent* Mesh, double Travelled)
    {
        // A foot counts as planted while it is flat: heel and ball both on the ground in two
        // consecutive frames. (A motion-capture swing foot skims the ground with one of them.)
        const TArray<FTransform>& Pose = Mesh->GetComponentSpaceTransforms();
        for (int32 Foot = 0; Foot + 1 < Points.Num(); Foot += 2)
        {
            FPoint& Heel = Points[Foot]; FPoint& Ball = Points[Foot + 1];
            if (!Pose.IsValidIndex(Heel.Bone)) continue;
            FVector H = Pose[Heel.Bone].TransformPosition(Heel.Local), B = Pose[Ball.Bone].TransformPosition(Ball.Local);
            H.Y += Travelled; B.Y += Travelled;
            const bool bFlat = H.Z < 1.5 && B.Z < 1.5, bWasFlat = Heel.bPrevious && Heel.Previous.Z < 1.5 && Ball.Previous.Z < 1.5;
            if (bFlat && bWasFlat)
                for (const TPair<FVector, FVector>& P : {TPair<FVector, FVector>(H, Heel.Previous), TPair<FVector, FVector>(B, Ball.Previous)})
                {
                    const double Drift = FVector::Dist2D(P.Key, P.Value);
                    Max = FMath::Max(Max, Drift); Sum += Drift; Signed += P.Key.Y - P.Value.Y; ++Samples; All.Add(Drift);
                }
            Heel.Previous = H; Ball.Previous = B; Heel.bPrevious = Ball.bPrevious = true;
        }
    }
    double Mean() const { return Samples ? Sum / Samples : 0.; }
    /** Typical drift: robust against a swing foot that skims the ground flat for a frame or two. */
    double Median() { All.Sort(); return All.Num() ? All[All.Num() / 2] : 0.; }
    TArray<double> All;
};

class FDinkPlayerActionCheck : public IAutomationLatentCommand
{
public:
    explicit FDinkPlayerActionCheck(FAutomationTestBase* InTest) : Test(InTest) {}
    bool Update() override
    {
        if (!Began) Began = FPlatformTime::Seconds();
        UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
        APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
        ADinkGreyboxCharacter* Hero = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
        UDinkStorySubsystem* Story = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (FPlatformTime::Seconds() - Began > 90) { Test->AddError(TEXT("player action PIE readiness timed out")); return true; }
        if (!Hero || !Story || Story->bNewGamePending) return false;
        FAssetCompilingManager::Get().FinishAllCompilation();
        USkeletalMeshComponent* Mesh = Hero->GetMesh();
        UDinkPlayerActionComponent* Action = Hero->FindComponentByClass<UDinkPlayerActionComponent>();
        UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(Mesh->GetAnimInstance());
        if (!Test->TestNotNull(TEXT("the hero runs the native body animation"), Body) ||
            !Test->TestNotNull(TEXT("cosmetic player action configured at startup"), Action)) return true;
        UDinkArtSubsystem* Art = World->GetSubsystem<UDinkArtSubsystem>();
        UDinkDirector* D = Story->GetDirector();
        UDinkGameplay* Game = Story->GetGameplay();
        const FName Fists(TEXT("item-fst"));

        // --- Which clip shows an attack: jab, cross, swing inside the combo window; never a mode switch.
        const FTransform ActorBefore = Hero->GetActorTransform();
        const float RadiusBefore = Hero->GetCapsuleComponent()->GetScaledCapsuleRadius();
        const bool FrozenBefore = D->GetDink().bFrozen;
        Test->TestTrue(TEXT("a reviewed sequence starts the cosmetic action"), Art->PlayPlayerSequence(Hero, 104, Fists));
        Test->TestEqual(TEXT("first attack is the jab"), Action->GetActiveClip(), FName(TEXT("Fist_Jab")));
        Test->TestTrue(TEXT("second attack inside the window is the cross"), Art->PlayPlayerSequence(Hero, 104, Fists) && Action->GetActiveClip() == TEXT("Fist_Cross"));
        Test->TestTrue(TEXT("third is the heavier swing"), Art->PlayPlayerSequence(Hero, 106, Fists) && Action->GetActiveClip() == TEXT("Fist_Swing"));
        Test->TestTrue(TEXT("the combo wraps to the jab"), Art->PlayPlayerSequence(Hero, 108, Fists) && Action->GetActiveClip() == TEXT("Fist_Jab"));
        Test->TestEqual(TEXT("the original sequence is retained"), Action->GetActiveSequence(), 108);
        Test->TestTrue(TEXT("the animation instance is never swapped for a clip"), Mesh->GetAnimInstance() == Body && Mesh->GetAnimationMode() == EAnimationMode::AnimationBlueprint);
        Test->TestFalse(TEXT("an unreviewed sequence plays nothing"), Art->PlayPlayerSequence(Hero, 112, Fists));
        Test->TestTrue(TEXT("a spell cast shows the cast gesture, not a punch"), Art->PlayPlayerSequence(Hero, 104, TEXT("magic")) && Action->GetActiveClip() == TEXT("Cast"));
        Test->TestTrue(TEXT("the bow's draw is held until the release"), Art->PlayPlayerClip(Hero, TEXT("Bow_Draw"), true) && Action->GetActiveClip() == TEXT("Bow_Draw"));
        Test->TestTrue(TEXT("the release follows"), Art->PlayPlayerClip(Hero, TEXT("Bow_Release")) && Action->GetActiveClip() == TEXT("Bow_Release"));
        Test->TestFalse(TEXT("the bow is not shown as a punch"), Art->PlayPlayerSequence(Hero, 104, TEXT("item-b1")));
        Test->TestTrue(TEXT("a sword plays a sword cut when imported"), Art->PlayPlayerSequence(Hero, 104, TEXT("item-sw1")) &&
            (Action->GetActiveClip() == TEXT("Sword_Slash_1") || !Body->HasClip(TEXT("Sword_Slash_1"))));
        Action->Cancel();
        Test->TestFalse(TEXT("cancel ends the cosmetic action"), Action->IsActionActive());
        Test->TestTrue(TEXT("cosmetic playback never changes actor transform"), Hero->GetActorTransform().Equals(ActorBefore, .001));
        Test->TestEqual(TEXT("cosmetic playback never changes capsule"), Hero->GetCapsuleComponent()->GetScaledCapsuleRadius(), RadiusBefore);
        Test->TestEqual(TEXT("cosmetic playback never writes frozen state"), D->GetDink().bFrozen, FrozenBefore);

        // --- The original pending-hit scheduler owns the 175 ms damage, across save/load.
        Story->bRunScreenScripts = false;
        Game->bBrainsEnabled = false;
        Game->SetRandomSeed(1997);
        Story->GetFacts()->SetFact(TEXT("strength"), 4);
        ADinkScreenVolume* Home = World->GetSubsystem<UDinkGreyboxSubsystem>()->FindScreen(1);
        Hero->SetActorLocation(Home->MapPixelToWorld(370, 161) + FVector(0, 0, 98), false, nullptr, ETeleportType::TeleportPhysics);
        Hero->SetActorRotation(FRotator::ZeroRotator);
        D->GetDink().Screen = 1; D->SyncSpriteFromActor(D->GetDink()); D->GetDink().Dir = 6;
        const int32 TargetHandle = D->CreateVirtualSprite(1, D->GetDink().X + 20, D->GetDink().Y);
        FDinkSprite* Target = D->FindSprite(TargetHandle);
        Target->Props.Add(TEXT("brain"), 9); Target->Props.Add(TEXT("hitpoints"), 10000);
        Target->Props.Add(TEXT("defense"), 0); Target->Props.Add(TEXT("touch_damage"), 0);
        Target->Props.Add(TEXT("pseq"), 131); Target->Props.Add(TEXT("pframe"), 1);
        auto HP = [&]() { return D->FindSprite(TargetHandle)->GetProp(TEXT("hitpoints")); };
        UDinkSaveSubsystem* Saves = World->GetGameInstance()->GetSubsystem<UDinkSaveSubsystem>();
        Test->TestEqual(TEXT("authoritative fist hit delay remains 175 ms"), Game->GetData().HitFrameDelayMs(106), 175);
        Test->TestEqual(TEXT("the original locks Dink for the sequence's 400 ms"), Game->SequenceDurationMs(106), 400);
        D->SpriteProperty(nullptr, TEXT("seq"), 1, 106);
        Test->TestTrue(TEXT("original sequence assignment triggers the visual"), Action->IsActionActive() && Action->GetActiveSequence() == 106);
        Story->Tick(.174f);
        Test->TestEqual(TEXT("no damage before the original 175 ms"), HP(), 10000);
        UDinkSaveGame* MidSave = Saves->CaptureSnapshot(Hero, 1);
        Story->Tick(.05f);
        const int32 DamagedHP = HP();
        Test->TestTrue(TEXT("the original scheduler applies one pending hit"), DamagedHP < 10000);
        Test->TestTrue(TEXT("mid-action snapshot applies"), Saves->ApplySnapshot(MidSave, Hero));
        Test->TestEqual(TEXT("authoritative target restores before hit"), HP(), 10000);
        Test->TestEqual(TEXT("restore keeps exactly the one pending hit"), Game->SaveState()->GetArrayField(TEXT("pendingHits")).Num(), 1);
        Story->Tick(.0005f);
        Test->TestEqual(TEXT("restored hit still waits until 175 ms"), HP(), 10000);
        Story->Tick(.0006f);
        Test->TestEqual(TEXT("restored original hit lands once at 175 ms"), HP(), DamagedHP);
        Story->Tick(.5f);
        Test->TestEqual(TEXT("the long cosmetic recovery cannot create another hit"), HP(), DamagedHP);

        // --- The attack key: one attack per press, no repeat on hold, a buffered press chains at the lock's end.
        D->GetDink().bFrozen = false;
        Target = D->FindSprite(TargetHandle); Target->Props.Add(TEXT("hitpoints"), 10000);
        auto CountHits = [&](int32 Before) { return Before == HP() ? 0 : 1; };
        Game->InputAttackReleased();
        Story->Tick(1.f);
        int32 Last = HP();
        const bool bStarted = Game->InputAttackPressed();
        if (Test->TestTrue(TEXT("a press starts an attack (fists armed, Dink free)"), bStarted))
        {
            int32 Hits = 0; double FirstHitAt = -1;
            for (int32 I = 0; I < 300; ++I) // the key stays down for three seconds
            {
                Story->Tick(.01f);
                if (HP() != Last) { ++Hits; Last = HP(); if (FirstHitAt < 0) FirstHitAt = (I + 1) * .01; }
                if (I % 7 == 0) Game->InputAttackPressed(); // what an OS auto-repeat would send
            }
            Test->TestEqual(TEXT("holding the key for three seconds lands exactly one hit"), Hits, 1);
            Test->TestTrue(TEXT("that hit lands at the original 175 ms"), FirstHitAt > .17 && FirstHitAt <= .19);
            Game->InputAttackReleased();
            Story->Tick(.5f); Last = HP();
            // Mash: press and release every 100 ms for two seconds.
            Hits = 0; TArray<double> HitTimes;
            for (int32 I = 0; I < 240; ++I)
            {
                if (I < 200 && I % 10 == 0) Game->InputAttackPressed();
                if (I < 200 && I % 10 == 5) Game->InputAttackReleased();
                Story->Tick(.01f);
                if (HP() != Last) { ++Hits; Last = HP(); HitTimes.Add((I + 1) * .01); }
            }
            FString Times; for (const double T : HitTimes) Times += FString::Printf(TEXT("%.2f "), T);
            Test->AddInfo(FString::Printf(TEXT("mashing every 100 ms for 2 s: %d hits at %s"), Hits, *Times));
            Test->TestTrue(TEXT("mashing attacks once per 400 ms lock, as the original does"), Hits >= 5 && Hits <= 6);
            for (int32 I = 1; I < HitTimes.Num(); ++I)
                Test->TestTrue(TEXT("mashed hits are a full attack apart"), HitTimes[I] - HitTimes[I - 1] >= .39);
            // The bot's and the console's path is not gated: it restarts the attack at once, as before.
            Game->InputAttackReleased(); Story->Tick(1.f);
            Test->TestTrue(TEXT("PlayerAttack is ungated"), Game->PlayerAttack() && Game->PlayerAttack());
        }

        // --- NPC speed mapping: the script side is untouched (sp_speed 1 = 60 px/s)...
        const int32 Walker = D->CreateVirtualSprite(1, 300, 200);
        FDinkSprite* W = D->FindSprite(Walker);
        W->Props.Add(TEXT("speed"), 1);
        D->StartMove(*W, 6, 400);
        D->Tick(1000., Story->GetNowMs());
        Test->TestTrue(TEXT("sp_speed 1 still moves a sprite 60 px a second"), FMath::IsNearlyEqual(D->FindSprite(Walker)->X, 360., .01));
        const double CmPerPx = FVector::Dist(Home->MapPixelToWorld(300, 200), Home->MapPixelToWorld(301, 200));
        Test->AddInfo(FString::Printf(TEXT("Dink's house: %.2f cm per pixel, so sp_speed 1 is %.0f cm/s in the world"), CmPerPx, CmPerPx * 60.));
        // Human pace (npc_pace.json): off in automated runs by default, so recorded timings keep the original speed...
        IConsoleVariable* PaceMode = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Npc.HumanPace"));
        Test->TestFalse(TEXT("automated runs use the original NPC speed by default"), Game->IsHumanPaceActive());
        FDinkSprite Townsperson; Townsperson.Handle = 77; Townsperson.Screen = 1; Townsperson.Props.Add(TEXT("brain"), 16); Townsperson.Props.Add(TEXT("speed"), 1);
        Test->TestEqual(TEXT("so a townsperson keeps full speed there"), Game->PaceScale(Townsperson), 1.);
        // ...and on (2 forces it): a townsperson walks at 120 cm/s whatever the screen's scale, a move still ends at its pixel, only later.
        PaceMode->Set(2);
        Test->TestTrue(TEXT("forced on"), Game->IsHumanPaceActive());
        Test->TestTrue(TEXT("townsfolk walk at 120 cm/s"), FMath::IsNearlyEqual(Game->PaceSpeedCm(16, NAME_None, 1), 120., .01));
        Test->TestTrue(TEXT("a faster sp_speed is capped for humans"), FMath::IsNearlyEqual(Game->PaceSpeedCm(16, NAME_None, 3), 170., .01));
        Test->TestTrue(TEXT("Milder has his own pace"), FMath::IsNearlyEqual(Game->PaceSpeedCm(0, TEXT("s1-bul"), 1), 135., .01));
        Test->TestEqual(TEXT("a pig is not a person"), Game->PaceSpeedCm(4, NAME_None, 1), 0.);
        const double Indoor = Game->PaceScale(Townsperson);
        Test->TestTrue(FString::Printf(TEXT("in Dink's house the scale is 120 / %.1f = %.3f"), CmPerPx * 60., Indoor), FMath::IsNearlyEqual(Indoor, 120. / (CmPerPx * 60.), .005));
        FDinkSprite Outdoor = Townsperson; Outdoor.Screen = 438;
        const double OutdoorCm = FVector::Dist(World->GetSubsystem<UDinkGreyboxSubsystem>()->FindScreen(438)->MapPixelToWorld(300, 200), World->GetSubsystem<UDinkGreyboxSubsystem>()->FindScreen(438)->MapPixelToWorld(301, 200));
        Test->TestTrue(FString::Printf(TEXT("outdoors (%.1f cm per pixel) the world pace is the same 120 cm/s"), OutdoorCm), FMath::IsNearlyEqual(Game->PaceScale(Outdoor) * 60. * OutdoorCm, 120., 1.));
        FDinkSprite Hero1 = Townsperson; Hero1.Handle = 1;
        Test->TestEqual(TEXT("Dink's own scripted moves keep their speed"), Game->PaceScale(Hero1), 1.);
        const int32 Paced = D->CreateVirtualSprite(1, 300, 157);
        FDinkSprite* PS = D->FindSprite(Paced);
        PS->Props.Add(TEXT("speed"), 1); PS->Props.Add(TEXT("brain"), 16);
        D->StartMove(*PS, 2, 200);
        double Took = 0;
        for (int32 I = 0; I < 600 && D->IsMoving(Paced); ++I) { D->Tick(10., Story->GetNowMs()); Took += .01; }
        Test->TestTrue(FString::Printf(TEXT("a paced move_stop of 43 px completes at its stop pixel, after %.2f s instead of 0.72 s"), Took),
            !D->IsMoving(Paced) && D->FindSprite(Paced)->Y == 200. && FMath::IsNearlyEqual(Took, 43. * CmPerPx / 120., .05));
        // Her wandering brain at the human pace: never more than the paced share of a pixel a frame (diagonals 1.41 times that).
        {
            AActor* MotherActor = nullptr;
            for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
                if (It->Origin && It->Origin->OriginId.ToString() == TEXT("S001_P26")) MotherActor = *It;
            int32 MotherHandle = 0;
            for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites()) if (Pair.Value.Actor.Get() == MotherActor && MotherActor) MotherHandle = Pair.Key;
            if (Test->TestTrue(TEXT("Mother's sprite found"), MotherHandle != 0))
            {
                Game->bBrainsEnabled = true;
                D->FindSprite(MotherHandle)->bFrozen = false;
                TArray<FVector2D> Track;
                for (int32 I = 0; I < 1200; ++I) { Story->Tick(1.f / 60.f); const FDinkSprite* M = D->FindSprite(MotherHandle); Track.Add(FVector2D(M->X, M->Y)); }
                double Fastest = 0, Total = 0;
                for (int32 I = 60; I < Track.Num(); ++I) Fastest = FMath::Max(Fastest, FVector2D::Distance(Track[I], Track[I - 60]));
                for (int32 I = 1; I < Track.Num(); ++I) Total += FVector2D::Distance(Track[I], Track[I - 1]);
                Test->AddInfo(FString::Printf(TEXT("Mother wandering for 20 s at the human pace (brain %d): %.0f px in all, fastest second %.1f px = %.0f cm/s (original: 60 px = %.0f cm/s)"),
                    D->FindSprite(MotherHandle)->GetProp(TEXT("brain")), Total, Fastest, Fastest * CmPerPx, 60. * CmPerPx));
                Test->TestTrue(TEXT("she wanders, at a walking pace"), Total > 20. && Fastest <= Indoor * 60. * 1.1 + 2.);
                Game->bBrainsEnabled = false;
            }
        }
        PaceMode->Set(1);
        // ...and Mother's body is shown smoothed with the motion-capture clips.
        UDinkHumanoidComponent* Mother = nullptr;
        for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
            if (It->Origin && It->Origin->OriginId.ToString() == TEXT("S001_P26")) Mother = It->FindComponentByClass<UDinkHumanoidComponent>();
        if (Test->TestNotNull(TEXT("Mother has her authored body"), Mother))
            Test->TestTrue(TEXT("Mother uses the native body animation and the position smoother"), Mother->UsesBodyAnimation() && Mother->GetSmoother().SmoothTime > 0.f);

        // --- In-engine foot sliding: the posed mesh at every blend weight, against the old blend space.
        AActor* Stage = World->SpawnActor<AActor>();
        USkeletalMeshComponent* Dummy = NewObject<USkeletalMeshComponent>(Stage);
        Stage->SetRootComponent(Dummy);
        Dummy->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Dummy->SetSkeletalMesh(Mesh->GetSkeletalMeshAsset());
        Dummy->RegisterComponent();
        Dummy->SetComponentTickEnabled(false);
        const float Dt = 1.f / 60.f;
        double WorstMean = 0, WorstMax = 0;
        Dummy->SetAnimInstanceClass(UDinkBodyAnimInstance::StaticClass());
        UDinkBodyAnimInstance* Walk = Cast<UDinkBodyAnimInstance>(Dummy->GetAnimInstance());
        if (Test->TestTrue(TEXT("bare mesh takes the hero clip set"), Walk && Walk->Configure(Art->GetAnimationLibrary(), TEXT("Hero"))))
        {
            for (const float Confidence : {0.f, .5f, 1.f})
                for (const float Speed : {45.f, 90.f, 120.f, 170.f, 200.f, 300.f, 450.f, 600.f})
                {
                    FDinkSlideProbe Probe; Probe.Init(Dummy);
                    for (int32 I = 0; I < 150; ++I)
                    {
                        Walk->SetMotion(Speed, false, Confidence);
                        Dummy->TickAnimation(Dt, false);
                        Dummy->RefreshBoneTransforms();
                        if (I >= 30) Probe.Sample(Dummy, Speed * Dt * I);
                    }
                    Test->AddInfo(FString::Printf(TEXT("SLIDE new hero speed %.0f confidence %.1f: planted drift median %.3f mean %.3f max %.3f cm/frame (%d samples), stride %.1f cm, net %.3f"),
                        Speed, Confidence, Probe.Median(), Probe.Mean(), Probe.Max, Probe.Samples, Walk->GetBlendedStrideCm(), Probe.Samples ? Probe.Signed / Probe.Samples : 0.));
                    Test->TestTrue(TEXT("the planted foot has no net slide: the stride matches the speed"), FMath::Abs(Probe.Samples ? Probe.Signed / Probe.Samples : 0.) < .35);
                    Test->TestTrue(TEXT("cadence times stride equals the speed at every blend weight"),
                        FMath::IsNearlyEqual(Walk->GetCyclesPerSecond() * Walk->GetBlendedStrideCm(), Speed, .5f));
                    if (Speed == 120.f || Speed == 170.f) { WorstMean = FMath::Max(WorstMean, Probe.Median()); WorstMax = FMath::Max(WorstMax, Probe.Max); }
                    // The old blend space measured 1.0 to 2.6 cm/frame with the same probe.
                    Test->TestTrue(TEXT("no blend weight slides like the old blend space did at a walk"), Probe.Mean() < 1.7);
                    if (Speed == 600.f) Test->TestTrue(TEXT("the run's planted foot holds (height-only contact test, 60 Hz samples of a 30 fps clip)"), Probe.Mean() < 1.4);
                }
            Test->TestTrue(TEXT("walking does not slide more than the motion-capture clip itself does"), WorstMean < 1.4);
        }
        if (UBlendSpace* Old = LoadObject<UBlendSpace>(nullptr, TEXT("/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run.BS_Idle_Walk_Run")))
        {
            for (const float Speed : {200.f, 262.5f, 600.f})
            {
                Dummy->SetAnimationMode(EAnimationMode::AnimationSingleNode);
                Dummy->PlayAnimation(Old, true);
                UAnimSingleNodeInstance* Node = Dummy->GetSingleNodeInstance();
                FVector Position = FVector::ZeroVector; float MaxSpeed = 0;
                for (int32 Axis = 0; Axis < 3; ++Axis)
                    if (Old->GetBlendParameter(Axis).DisplayName.Contains(TEXT("Speed")))
                    { Position[Axis] = FMath::Clamp(Speed, Old->GetBlendParameter(Axis).Min, Old->GetBlendParameter(Axis).Max); MaxSpeed = Old->GetBlendParameter(Axis).Max; }
                Node->SetBlendSpacePosition(Position);
                Node->SetPlayRate(MaxSpeed > 0 ? FMath::Clamp(Speed / MaxSpeed, 1.f, 3.f) : 1.f);
                FDinkSlideProbe Probe; Probe.Init(Dummy);
                for (int32 I = 0; I < 150; ++I)
                {
                    Dummy->TickAnimation(Dt, false);
                    Dummy->RefreshBoneTransforms();
                    if (I >= 30) Probe.Sample(Dummy, Speed * Dt * I);
                }
                Test->AddInfo(FString::Printf(TEXT("SLIDE old blend space speed %.1f: planted drift median %.3f mean %.3f max %.3f cm/frame (%d samples), net %.3f"), Speed, Probe.Median(), Probe.Mean(), Probe.Max, Probe.Samples, Probe.Samples ? Probe.Signed / Probe.Samples : 0.));
            }
        }
        Stage->Destroy();
        return true;
    }
private:
    FAutomationTestBase* Test;
    double Began = 0;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPlayerActionTest,
    "Dink.Art.PlayerAction.ComboHitTimingInputAndFootSlide", DINK_TEST_FLAGS)
bool FDinkPlayerActionTest::RunTest(const FString&)
{
    if (!IFileManager::Get().FileExists(*(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/animation_pass.json"))))
    { AddWarning(TEXT("skipped: animation pass manifest absent")); return true; }
    const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook"), FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("real player map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkPlayerActionCheck(this));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
    return true;
}
