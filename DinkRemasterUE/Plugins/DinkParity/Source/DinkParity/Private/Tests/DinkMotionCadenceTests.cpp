#include "DinkTestHelpers.h"
#include "DinkCreatureComponent.h"
#include "DinkHumanoidComponent.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/BlendSpace.h"
#include "AssetCompilingManager.h"
#include "Components/SceneComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkMotionCadenceTest,
    "Dink.Art.MotionEstimate.ClassicBrainAcrossRenderCadences", DINK_TEST_FLAGS)
bool FDinkMotionCadenceTest::RunTest(const FString&)
{
    USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
    UBlendSpace* BS = LoadObject<UBlendSpace>(nullptr, TEXT("/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run.BS_Idle_Walk_Run"));
    if (!Mesh || !BS) { AddWarning(TEXT("skipped: template motion rig absent")); return true; }
    FAssetCompilingManager::Get().FinishAllCompilation();
    UAnimSequence* Feed = BS->GetBlendSamples().Num() ? Cast<UAnimSequence>(BS->GetBlendSample(0).Animation) : nullptr;
    if (!TestNotNull(TEXT("compatible food fixture clip"), Feed)) return false;
    FVector2D BaselineXY = FVector2D::ZeroVector;
    for (const int32 Rate : {30, 60, 120, 144, 240})
    {
        UGameInstance* GI = NewObject<UGameInstance>(GEngine); GI->InitializeStandalone();
        UWorld* World = GI->GetWorld();
        ON_SCOPE_EXIT { GI->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
        UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
        Story->bRunScreenScripts = false; Story->bNewGamePending = false;
        Story->GetFacts()->SetFact(TEXT("life"), 100); Story->GetFacts()->SetFact(TEXT("lifemax"), 100);
        Story->GetFacts()->SetFact(TEXT("update_status"), 0);
        UDinkDirector* D = Story->GetDirector(); UDinkGameplay* Game = Story->GetGameplay();
        Game->Adaptation.bEnabled = false; Game->SetRandomSeed(1997);
        UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
        // A deliberately empty synthetic room isolates original brain cadence from path obstacles.
        // No original placement/origin is invented or modified by this fixture.
        ADinkScreenVolume* Room = World->SpawnActor<ADinkScreenVolume>(); Room->ScreenNumber = 999;
        Room->Corners.NW = FVector2D(0, 0); Room->Corners.NE = FVector2D(60, 0);
        Room->Corners.SW = FVector2D(0, 40); Room->Corners.SE = FVector2D(60, 40);
        Room->Bounds->SetMobility(EComponentMobility::Movable);
        Room->SetActorLocation(FVector(3000, 2000, 0));
        Room->Bounds->SetBoxExtent(FVector(3000, 2000, 1000)); Room->Bounds->UpdateBounds();
        Greybox->RegisterScreen(Room);
        ON_SCOPE_EXIT { Greybox->UnregisterScreen(Room); };
        auto Actor = [&]()
        {
            AActor* A = World->SpawnActor<AActor>(); USceneComponent* Root = NewObject<USceneComponent>(A);
            A->SetRootComponent(Root); Root->RegisterComponent(); return A;
        };
        AActor* Goal = Actor(); Goal->SetActorLocation(Room->MapPixelToWorld(480, 100));
        D->GetDink().Actor = Goal; D->GetDink().Screen = 999; D->GetDink().X = 500; D->GetDink().Y = 100;
        AActor* Owner = Actor(); Owner->Tags.Add(TEXT("DinkCreature"));
        Owner->SetActorLocation(Room->MapPixelToWorld(80, 100));
        const int32 Handle = D->CreateVirtualSprite(999, 100, 100);
        FDinkSprite* S = D->FindSprite(Handle); S->Actor = Owner;
        S->Props.Add(TEXT("brain"), 9); S->Props.Add(TEXT("speed"), 1); S->Props.Add(TEXT("timing"), 0);
        S->Props.Add(TEXT("base_walk"), 130); S->Props.Add(TEXT("base_attack"), -1); S->Props.Add(TEXT("target"), 1);
        S->Props.Add(TEXT("seq"), 133); S->SeqOrig = 133;
        UDinkHumanoidComponent* Human = NewObject<UDinkHumanoidComponent>(Owner); Human->SetupAttachment(Owner->GetRootComponent()); Human->RegisterComponent(); Human->Configure(Mesh, BS);
        UDinkCreatureComponent* Creature = NewObject<UDinkCreatureComponent>(Owner); Creature->SetupAttachment(Owner->GetRootComponent()); Creature->RegisterComponent();
        FDinkCreaturePresentation Settings; Settings.NominalRunSpeedCmS = 400;
        if (!TestTrue(TEXT("generic creature motion rig configures"), Creature->Configure(Mesh, BS, Feed, Settings))) return false;
        const float Dt = 1.f / Rate;
        Human->TickComponent(Dt, LEVELTICK_All, nullptr); Creature->TickComponent(Dt, LEVELTICK_All, nullptr);
        double Time = 0, ObservedPath = 0, Integral = 0, Duration = 0;
        int32 FalseIdle = 0, IntermittentFrames = 0, PhantomFood = 0, FalseCadence = 0;
        for (int32 Frame = 0; Frame < Rate * 3; ++Frame)
        {
            const FVector Before = Owner->GetActorLocation();
            Story->Tick(Dt);
            Human->TickComponent(Dt, LEVELTICK_All, nullptr); Creature->TickComponent(Dt, LEVELTICK_All, nullptr);
            Time += Dt;
            if (Time < .25) continue;
            const double Distance = FVector::DistXY(Before, Owner->GetActorLocation());
            ObservedPath += Distance; Duration += Dt;
            Integral += Creature->GetLocomotionSpeed() * Dt;
            FalseIdle += Creature->GetLocomotionSpeed() <= 1 || Human->GetLocomotionSpeed() <= 1;
            IntermittentFrames += Distance < .001;
            FalseCadence += Creature->GetSingleNodeInstance()->GetPlayRate() <= 1.01f || Human->GetSingleNodeInstance()->GetPlayRate() <= 1.01f;
            PhantomFood += Creature->CanFeedAt(Creature->GetSocketLocation(TEXT("head")) + Owner->GetActorForwardVector() * 40);
            TestTrue(TEXT("humanoid and creature observe identical physical motion"), FMath::IsNearlyEqual(Human->GetLocomotionSpeed(), Creature->GetLocomotionSpeed(), .01f));
        }
        const FString Label = FString::Printf(TEXT("%dHz"), Rate);
        const double ActualMean = ObservedPath / Duration, PresentedMean = Integral / Duration;
        AddInfo(FString::Printf(TEXT("%s actual%.2f presented%.2f intermittent%d falseidle%d"), *Label, ActualMean, PresentedMean, IntermittentFrames, FalseIdle));
        TestTrue(Label + TEXT(" real original brain moves continuously"), ActualMean > 300);
        TestEqual(Label + TEXT(" moving brain never presents false idle"), FalseIdle, 0);
        TestEqual(Label + TEXT(" zero render displacement never permits running feed"), PhantomFood, 0);
        TestTrue(Label + TEXT(" presented world speed matches actual path mean"), FMath::Abs(PresentedMean - ActualMean) < ActualMean * .05);
        if (Rate >= 120) TestTrue(Label + TEXT(" fixture genuinely has between-brain render frames"), IntermittentFrames > Rate / 4);
        const FVector2D Final(D->FindSprite(Handle)->X, D->FindSprite(Handle)->Y);
        if (Rate == 30) BaselineXY = Final;
        else TestTrue(Label + TEXT(" original brain finalXY independent of presentation cadence"), Final.Equals(BaselineXY, .001));
        TestEqual(Label + TEXT(" original target retained"), D->FindSprite(Handle)->GetProp(TEXT("target")), 1);
        TestEqual(Label + TEXT(" original logical speed retained"), D->FindSprite(Handle)->GetProp(TEXT("speed")), 1);
        D->FindSprite(Handle)->bFrozen = true;
        for (int32 Frame = 0; Frame < FMath::CeilToInt(Rate * .2); ++Frame)
        {
            Story->Tick(Dt); Human->TickComponent(Dt, LEVELTICK_All, nullptr); Creature->TickComponent(Dt, LEVELTICK_All, nullptr);
        }
        TestEqual(Label + TEXT(" real stop returns creature to idle promptly"), Creature->GetLocomotionSpeed(), 0.f);
        TestEqual(Label + TEXT(" real stop returns humanoid to idle promptly"), Human->GetLocomotionSpeed(), 0.f);
        AActor* Food = Actor(); Food->SetActorLocation(Creature->GetSocketLocation(TEXT("head")) + Owner->GetActorForwardVector() * 40);
        TestTrue(Label + TEXT(" genuinely stopped creature can feed"), Creature->TryFeed(Food));
        Owner->AddActorWorldOffset(FVector(.1, 0, 0));
        Creature->TickComponent(.005f, LEVELTICK_All, nullptr);
        TestFalse(Label + TEXT(" immediate physical motion interrupts feed before smoothing catches up"), Creature->IsFeeding());
        Owner->AddActorWorldOffset(FVector(1000, 0, 0));
        Human->TickComponent(Dt, LEVELTICK_All, nullptr); Creature->TickComponent(Dt, LEVELTICK_All, nullptr);
        TestEqual(Label + TEXT(" teleport immediately resets creature estimate"), Creature->GetLocomotionSpeed(), 0.f);
        TestEqual(Label + TEXT(" teleport immediately resets humanoid estimate"), Human->GetLocomotionSpeed(), 0.f);
    }
    return true;
}
