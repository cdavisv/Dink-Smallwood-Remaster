#include "DinkTestHelpers.h"
#include "DinkBodyDynamics.h"
#include "DinkHeroPhysicality.h"
#include "DinkStatsComponent.h"
#include "DinkEarlyPostureAnimInstance.h"
#include "DinkHumanoidComponent.h"
#include "Animation/BlendSpace.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "DinkInteriorCameraComponent.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputKeyEventArgs.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBodyDynamicsTest, "Dink.Movement.SecondaryMotion", DINK_TEST_FLAGS)
bool FDinkBodyDynamicsTest::RunTest(const FString&)
{
    for (const float Dt : {1.f/120.f, 1.f/30.f, .125f})
    {
        FDinkBodyDynamics Motion;
        FVector Position = FVector::ZeroVector;
        Motion.Update(Position, FQuat::Identity, Dt);
        FRotator Pose;
        for (int32 I=0; I<120; ++I)
        {
            Position += FVector(400 * Dt, (I%2 ? 1 : -1)*200*Dt, 0);
            Pose = Motion.Update(Position, FQuat::Identity, Dt);
            TestTrue(TEXT("starts and abrupt turns keep a finite bounded pose"), !Pose.ContainsNaN() && FMath::Abs(Pose.Pitch)<=5.2 && FMath::Abs(Pose.Roll)<=4.3);
        }
        TestTrue(TEXT("sustained locomotion produces forward weight"), Pose.Pitch < -.5);
        const FRotator Paused = Motion.Update(Position, FQuat::Identity, 0);
        TestTrue(TEXT("zero game time does not integrate spring"), FMath::Abs(Paused.Pitch-Pose.Pitch)<.2);
        TestTrue(TEXT("warp resets motion rather than causing a lurch"), Motion.Update(Position+FVector(3000,0,0), FQuat::Identity, Dt).IsNearlyZero());
        Position += FVector(3000,0,0);
        for (int32 I=0; I<120; ++I) Pose=Motion.Update(Position,FQuat::Identity,Dt);
        TestTrue(TEXT("standing settles to small idle mannerisms"), FMath::Abs(Pose.Pitch)<.2 && FMath::Abs(Pose.Roll)<.3);
    }
    FDinkBodyDynamics Falling, Grounded;
    Falling.Update(FVector(0,0,100),FQuat::Identity,.05f,false);
    Grounded.Update(FVector(0,0,100),FQuat::Identity,.05f,true);
    Falling.Update(FVector(0,0,60),FQuat::Identity,.05f,false);
    Grounded.Update(FVector(0,0,60),FQuat::Identity,.05f,true);
    const FRotator Land=Falling.Update(FVector::ZeroVector,FQuat::Identity,.05f,true);
    const FRotator Stand=Grounded.Update(FVector::ZeroVector,FQuat::Identity,.05f,true);
    TestTrue(TEXT("landing gives a damped weight response"), Land.Pitch<Stand.Pitch-.1);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkClumsyHeroTest,"Dink.Movement.ClumsyHero",DINK_TEST_FLAGS)
bool FDinkClumsyHeroTest::RunTest(const FString&)
{
    FDinkHeroPhysicality A,B;
    int32 Stumbles=0;
    for (int32 I=0; I<100; ++I)
    {
        const bool DidStumble=A.Land(300.f,.4f,.3f);
        TestEqual(TEXT("cosmetic landing stream is repeatable"),DidStumble,B.Land(300.f,.4f,.3f));
        Stumbles+=DidStumble ? 1 : 0;
        A.Update(2.f,0,true,true); B.Update(2.f,0,true,true);
    }
    TestTrue(TEXT("normal landing chance produces occasional rather than constant stumbles"),Stumbles>10 && Stumbles<50);
    TestFalse(TEXT("small steps do not cause stumbles"),A.Land(100,.4f,1));
    TestFalse(TEXT("spawn-height falls do not cause stumbles"),A.Land(300,.05f,1));
    float Impact=-1.f;
    TestFalse(TEXT("a spawn-height drop is not even a landing"),A.ConsumeLanding(Impact));
    TestTrue(TEXT("qualifying fall can stumble"),A.Land(300,.4f,1));
    TestTrue(TEXT("a landing is reported once, with how hard it was"),A.ConsumeLanding(Impact) && Impact>.2f && Impact<.5f && !A.ConsumeLanding(Impact));
    TestTrue(TEXT("the catch-step is announced once for the animation layer"),A.ConsumeStumbleStart() && !A.ConsumeStumbleStart());
    A.Update(.2f,200,true,true);
    TestTrue(TEXT("he is recovering"),A.IsStumbling());
    A.Update(0,200,true,true);
    TestTrue(TEXT("paused game time cannot advance the recovery"),A.IsStumbling());
    TestFalse(TEXT("bounce contacts cannot retrigger a stumble"),A.Land(300,.4f,1));
    A.Update(.8f,0,true,true); TestFalse(TEXT("Dink recovers within one second"),A.IsStumbling());
    A.Update(2,0,true,true); A.Land(300,.4f,1); A.Update(.1f,200,true,false);
    TestFalse(TEXT("cutscene freeze cancels recovery"),A.IsStumbling());
    TestTrue(TEXT("freeze removes the lean"),A.GetLean().IsNearlyZero());
    for (int32 I=0;I<240;++I)
    {
        A.Update(1.f/60.f,200,true,true);
        if (I>60) TestTrue(TEXT("a steady walk carries no procedural wobble at all: the gait is in the clips"),A.GetLean().IsNearlyZero(.02f));
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkClumsierResponseTest,"Dink.Movement.ClumsyTransitions",DINK_TEST_FLAGS)
bool FDinkClumsierResponseTest::RunTest(const FString&)
{
    FDinkHeroPhysicality Starting, Stopping, Left, Right;
    float Forward=0.f;
    for (int32 I=0; I<18; ++I)
    {
        // CharacterMovement's 2048 cm/s2: 0 to 600 in about 0.3 s.
        Starting.Update(1.f/60.f,FMath::Min(600.f,(I+1)*34.f),true,true);
        Forward=FMath::Max(Forward,Starting.GetLean().X);
    }
    TestTrue(TEXT("he leans into an acceleration, by a few degrees and no more"),Forward>1.5f && Forward<=FDinkHeroPhysicality::MaxStartLean+.5f);
    for (int32 I=0; I<120; ++I) { Starting.Update(1.f/60.f,600,true,true); Stopping.Update(1.f/60.f,600,true,true); }
    TestTrue(TEXT("at a steady run the lean has settled"),Starting.GetLean().IsNearlyZero(.05f));
    float Back=0.f;
    for (int32 I=0; I<18; ++I) { Stopping.Update(1.f/60.f,FMath::Max(0.f,600.f-(I+1)*34.f),true,true); Back=FMath::Min(Back,Stopping.GetLean().X); }
    TestTrue(TEXT("braking rocks him back against the stop"),Back<-1.f && Back>=-FDinkHeroPhysicality::MaxStopLean*1.3f-.5f);
    for (int32 I=0; I<120; ++I) Stopping.Update(1.f/60.f,0,true,true);
    TestTrue(TEXT("the stop settles upright"),Stopping.GetLean().IsNearlyZero(.05f));
    for (int32 I=0; I<60; ++I)
    {
        Left.Update(1.f/60.f,600,true,true,-300);
        Right.Update(1.f/60.f,600,true,true,300);
    }
    TestTrue(TEXT("he leans into a corner, opposite ways for opposite turns"),Left.GetLean().Y>2.f && Right.GetLean().Y<-2.f);
    Left.Land(300,.4f,1); Left.Update(.1f,200,true,true,-300);
    Left.Update(0,200,true,false);
    TestTrue(TEXT("freeze cancels the lean even if game time is paused"),Left.GetLean().IsNearlyZero());
    FDinkHeroPhysicality Jump;
    TestTrue(TEXT("landing fixture stumbles"),Jump.Land(300,.4f,1));
    Jump.Update(.1f,200,true,true);
    Jump.Update(1.f/60.f,200,false,true);
    TestFalse(TEXT("jumping out of recovery removes the grounded catch-step"),Jump.IsStumbling());
    TestFalse(TEXT("takeoff does not clear landing debounce"),Jump.Land(300,.4f,1));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkClumsyFrameRatesTest,"Dink.Movement.ClumsyFrameRates",DINK_TEST_FLAGS)
bool FDinkClumsyFrameRatesTest::RunTest(const FString&)
{
    for (const float Dt : {1.f/120.f,1.f/30.f,.125f})
    {
        FDinkHeroPhysicality Motion;
        for (int32 I=0; I<240; ++I)
        {
            if (I%40==0) Motion.Land(300,.4f,1);
            Motion.Update(Dt,I%60<30 ? 600.f : 0.f,true,true,I%2 ? 300.f : -300.f);
            const FVector2f Lean=Motion.GetLean();
            TestTrue(TEXT("hitches, starts, stops, turns and catches keep a small finite lean"),
                FMath::IsFinite(Lean.X) && FMath::IsFinite(Lean.Y) && FMath::Abs(Lean.X)<=6.f && FMath::Abs(Lean.Y)<=6.f);
        }
        Motion.Cancel(); Motion.Update(Dt,0,true,true);
        TestTrue(TEXT("reset discards previous speed/turn impulses"),Motion.GetLean().IsNearlyZero(.001f));
    }
    FDinkHeroPhysicality Fine, Coarse;
    for (int32 I=0;I<240;++I) Fine.Update(1.f/120.f,600,true,true,150);
    for (int32 I=0;I<60;++I) Coarse.Update(1.f/30.f,600,true,true,150);
    TestTrue(TEXT("constant motion is stable across common frame rates"),Fine.GetLean().Equals(Coarse.GetLean(),.02f));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHeroGrowthTest,"Dink.Movement.HeroGrowth",DINK_TEST_FLAGS)
bool FDinkHeroGrowthTest::RunTest(const FString&)
{
    TestEqual(TEXT("new-game Dink has no confidence"),FDinkHeroPhysicality::ConfidenceFor(1,3,0),0.f);
    float Previous=0.f;
    for (int32 Level=2; Level<=14; ++Level)
    {
        const float C=FDinkHeroPhysicality::ConfidenceFor(Level,3+Level,Level/2);
        TestTrue(TEXT("confidence never drops as Dink levels"),C>=Previous && C<=1.f);
        Previous=C;
    }
    TestTrue(TEXT("a late-game hero is fully confident"),FDinkHeroPhysicality::ConfidenceFor(12,20,8)>.99f);
    TestTrue(TEXT("mid-game Dink is visibly part-way"),
        FMath::IsWithin(FDinkHeroPhysicality::ConfidenceFor(6,8,3),.25f,.75f));

    FDinkHeroPhysicality Timid, Hero;
    Hero.SetTargetConfidence(1.f,true);
    TestTrue(TEXT("scrawny frame fills out"),Timid.GetPhysiqueScale().X<.9 && Hero.GetPhysiqueScale().Equals(FVector::OneVector));
    TestTrue(TEXT("landing stumbles become rare"),FMath::IsNearlyEqual(Hero.ScaleChance(.45f,.08f),.036f,1e-4f)
        && FMath::IsNearlyEqual(Timid.ScaleChance(.45f,.08f),.45f));

    FDinkHeroPhysicality Easing;
    Easing.SetTargetConfidence(1.f);
    Easing.Update(1.f,0,true,true);
    TestTrue(TEXT("a level-up straightens him gradually, not in one frame"),FMath::IsWithin(Easing.GetConfidence(),.2f,.5f));
    Easing.Cancel();
    TestTrue(TEXT("teleports and cutscenes keep the confidence he earned"),Easing.GetConfidence()>.2f);
    for (int32 I=0;I<8;++I) Easing.Update(.5f,0,true,true);
    TestEqual(TEXT("confidence settles at its target"),Easing.GetConfidence(),1.f);

    FDinkHeroPhysicality Runner, Veteran;
    Veteran.SetTargetConfidence(1.f,true);
    int32 Trips=0, VeteranTrips=0;
    for (int32 I=0;I<7200;++I)
    {
        const bool Was=Runner.IsStumbling(), VeteranWas=Veteran.IsStumbling();
        Runner.Update(1.f/60.f,600,true,true,0,.2f); Veteran.Update(1.f/60.f,600,true,true,0,.2f);
        Trips+=!Was && Runner.IsStumbling(); VeteranTrips+=!VeteranWas && Veteran.IsStumbling();
    }
    AddInfo(FString::Printf(TEXT("timid runner at an exaggerated test rate: %d stumbles in two minutes"),Trips));
    TestTrue(TEXT("an untrained Dink catches a toe now and then, never in quick succession"),Trips>=2 && Trips<=10);
    TestEqual(TEXT("the hero never trips running"),VeteranTrips,0);
    FDinkHeroPhysicality Walker;
    for (int32 I=0;I<3600;++I) { Walker.Update(1.f/60.f,200,true,true,0,.2f); TestFalse(TEXT("walking never trips"),Walker.IsStumbling()); if (Walker.IsStumbling()) break; }
    FDinkHeroPhysicality Default;
    int32 DefaultTrips=0;
    for (int32 I=0;I<60*600;++I) { const bool Was=Default.IsStumbling(); Default.Update(1.f/60.f,600,true,true,0,ADinkGreyboxCharacter::StaticClass()->GetDefaultObject<ADinkGreyboxCharacter>()->RunTripsPerSecond); DefaultTrips+=!Was && Default.IsStumbling(); }
    AddInfo(FString::Printf(TEXT("default rate: %d stumbles in ten minutes of flat-out level-1 running"),DefaultTrips));
    TestTrue(TEXT("at the shipped rate a stumble is rare"),DefaultTrips<=12);

    TestTrue(TEXT("earned confidence relaxes the authored slouch too"),
        FMath::IsNearlyEqual(UDinkEarlyPostureAnimInstance::TargetWeight(0,true,false,false,1.f),.15f,1e-4f));
    TestEqual(TEXT("story-only relaxation is unchanged"),UDinkEarlyPostureAnimInstance::TargetWeight(7,true,false,false,0.f),.3f);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkZoomLimitsTest, "Dink.Movement.ZoomLimits", DINK_TEST_FLAGS)
bool FDinkZoomLimitsTest::RunTest(const FString&)
{
    UDinkInteriorCameraComponent* Camera=NewObject<UDinkInteriorCameraComponent>();
    TestEqual(TEXT("default outdoor framing"),Camera->GetDesiredArmLength(),400.f);
    for (int32 I=0; I<30; ++I) Camera->AddZoomInput(1);
    TestEqual(TEXT("close zoom stays behind the player"),Camera->GetDesiredArmLength(),180.f);
    Camera->AddZoomInput(-1);
    TestEqual(TEXT("reverse responds at limit without dead scroll"),Camera->GetDesiredArmLength(),215.f);
    for (int32 I=0; I<30; ++I) Camera->AddZoomInput(-1);
    TestEqual(TEXT("outdoor zoom capped"),Camera->GetDesiredArmLength(),650.f);
    Camera->bInteriorMode=true;
    TestTrue(TEXT("entering room clamps zoom to room limit"),Camera->GetDesiredArmLength()<=320.f);
    Camera->AddZoomInput(1);
    TestEqual(TEXT("indoor zoom reverses immediately too"),Camera->GetDesiredArmLength(),285.f);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBodyReconfigureTest, "Dink.Movement.HumanoidReconfigure", DINK_TEST_FLAGS)
bool FDinkBodyReconfigureTest::RunTest(const FString&)
{
    UWorld* W=UWorld::CreateWorld(EWorldType::Game,false);
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(W);
    AActor* Actor=W->SpawnActor<AActor>();
    USceneComponent* Root=NewObject<USceneComponent>(Actor);
    Actor->SetRootComponent(Root); Root->RegisterComponent();
    UDinkHumanoidComponent* Human=NewObject<UDinkHumanoidComponent>(Actor);
    Human->SetupAttachment(Root); Human->RegisterComponent();
    USkeletalMesh* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
    UBlendSpace* Gait=LoadObject<UBlendSpace>(nullptr,TEXT("/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run.BS_Idle_Walk_Run"));
    TestNotNull(TEXT("real humanoid mesh"),Mesh); TestNotNull(TEXT("real humanoid gait"),Gait);
    Human->Configure(Mesh,Gait);
    Human->TickComponent(.016f,LEVELTICK_All,nullptr);
    Actor->AddActorWorldOffset(FVector(10,0,0));
    const FTransform RootBefore=Actor->GetActorTransform();
    Human->TickComponent(.016f,LEVELTICK_All,nullptr);
    TestFalse(TEXT("fixture develops nonzero secondary lean"),Human->GetRelativeRotation().IsNearlyZero(.001));
    TestTrue(TEXT("body motion keeps script root fixed"),Actor->GetActorTransform().Equals(RootBefore));
    const FTransform Presentation(FRotator(0,-90,0),FVector(3,4,-60),FVector(.8));
    // ApplyScriptCharacter/sp_size replaces the authored transform before Configure.
    for (int32 I=0; I<3; ++I)
    {
        Human->SetRelativeTransform(Presentation); Human->Configure(Mesh,Gait);
        Human->TickComponent(.016f,LEVELTICK_All,nullptr);
        TestTrue(TEXT("reconfiguration starts from the new authored pose without inverse stale lean"),Human->GetRelativeTransform().Equals(Presentation,.0001));
        Actor->AddActorWorldOffset(FVector(10,0,0)); Human->TickComponent(.016f,LEVELTICK_All,nullptr);
    }
    Human->Configure(Mesh,Gait); Human->TickComponent(.016f,LEVELTICK_All,nullptr);
    TestTrue(TEXT("reconfigure without a new transform also removes owned lean"),Human->GetRelativeTransform().Equals(Presentation,.0001));
    GEngine->DestroyWorldContext(W); W->DestroyWorld(false);
    return true;
}

namespace
{
class FDinkMovementPIE : public IAutomationLatentCommand
{
public:
    explicit FDinkMovementPIE(FAutomationTestBase* T):Test(T) {}
    bool Update() override
    {
        if (!Began) Began=FPlatformTime::Seconds();
        UWorld* W=GEditor ? GEditor->PlayWorld.Get() : nullptr;
        APlayerController* PC=W ? W->GetFirstPlayerController() : nullptr;
        ADinkGreyboxCharacter* H=PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
        UDinkStorySubsystem* Story=W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (FPlatformTime::Seconds()-Began>60) { Test->AddError(TEXT("movement PIE timeout")); return true; }
        if (!H || !Story || Story->bNewGamePending) return false;
        UCharacterMovementComponent* Move=H->GetCharacterMovement();
        auto Freeze=[Story](bool Frozen)
        {
            FDinkScriptInstance Caller;
            Story->GetDirector()->Execute(Caller,FDinkStoryLine::Parse(Frozen ? TEXT(">> freeze 1") : TEXT(">> unfreeze 1"),{TEXT("cmd")}));
        };
        auto Key=[PC](FKey K,EInputEvent E) { PC->InputKey(FInputKeyEventArgs(nullptr,INPUTDEVICEID_NONE,K,E,FPlatformTime::Cycles64())); };
        if (Phase==0)
        {
            Story->bRunScreenScripts=false;
            Freeze(false); // release the opening scene before discarding its director state
            Story->ResetRuntime(); Story->GetGameplay()->bBrainsEnabled=false;
            Freeze(false);
            ADinkScreenVolume* Yard=W->GetSubsystem<UDinkGreyboxSubsystem>()->FindScreen(439);
            if (!Test->TestNotNull(TEXT("yard fixture"),Yard)) return true;
            H->SetActorLocation(Yard->MapPixelToWorld(300,280)+FVector(0,0,100),false,nullptr,ETeleportType::TeleportPhysics);
            Move->StopMovementImmediately();
            Phase=1; At=W->GetTimeSeconds(); return false;
        }
        if (Phase==1)
        {
            if (!Move->IsMovingOnGround()) return false;
            StartZ=H->GetActorLocation().Z;
            Key(EKeys::LeftShift,IE_Pressed);
            At=W->GetTimeSeconds(); Phase=2; return false;
        }
        if (Phase==2)
        {
            if (W->GetTimeSeconds()-At<.1) return false;
            Test->TestEqual(TEXT("actual Shift input selects walk speed"),Move->MaxWalkSpeed,200.f);
            H->AddMovementInput(FVector(1,0,0));
            if (W->GetTimeSeconds()-At<.7) return false;
            Test->TestTrue(FString::Printf(TEXT("walk measured %.1f cm/s ignore=%d"),Move->Velocity.Size2D(),PC->IsMoveInputIgnored()),Move->Velocity.Size2D()>170 && Move->Velocity.Size2D()<=201);
            Key(EKeys::LeftShift,IE_Released);
            At=W->GetTimeSeconds(); Phase=3; return false;
        }
        if (Phase==3)
        {
            H->AddMovementInput(FVector(1,0,0));
            if (W->GetTimeSeconds()-At<.5) return false;
            Test->TestEqual(TEXT("releasing Shift restores run"),Move->MaxWalkSpeed,600.f);
            Test->TestTrue(FString::Printf(TEXT("run measured %.1f cm/s"),Move->Velocity.Size2D()),Move->Velocity.Size2D()>450);
            Move->StopMovementImmediately();
            Freeze(true);
            H->Jump();
            Test->TestFalse(TEXT("cutscene freeze rejects jumping"),H->bPressedJump);
            Freeze(false);
            StartZ=H->GetActorLocation().Z;
            H->LandingStumbleChance=1.f; // exercise the actual Landed callback deterministically
            Key(EKeys::SpaceBar,IE_Pressed);
            At=W->GetTimeSeconds(); Phase=4; return false;
        }
        if (Phase==4)
        {
            Peak=FMath::Max(Peak,H->GetActorLocation().Z-StartZ);
            if (W->GetTimeSeconds()-At<.12) return false;
            Test->TestTrue(FString::Printf(TEXT("Space launch: mode=%d vertical=%.1f height=%.1f"),int32(Move->MovementMode),Move->Velocity.Z,Peak),Move->IsFalling() && Move->Velocity.Z>0 && Peak>20);
            Key(EKeys::SpaceBar,IE_Released);
            H->Jump(); H->CheckJumpInput(.016f); H->StopJumping();
            Test->TestTrue(TEXT("midair press cannot double jump"),H->JumpCurrentCount<=1);
            Phase=5; return false;
        }
        if (Phase==5)
        {
            Peak=FMath::Max(Peak,H->GetActorLocation().Z-StartZ);
            if (!Move->IsMovingOnGround() || W->GetTimeSeconds()-At<.3) return false;
            Test->TestTrue(TEXT("jump lands on physical ground"),FMath::Abs(H->GetActorLocation().Z-StartZ)<5);
            Test->TestTrue(TEXT("Dink has a low, unathletic hop"),Peak>20 && Peak<65);
            Test->AddInfo(FString::Printf(TEXT("Measured Dink hop height %.2f cm; previous jump measured107.6cm"),Peak));
            Test->TestTrue(TEXT("eligible actual landing can trigger Dink stumble"),H->IsStumbling());
            Test->TestEqual(TEXT("walking and jumping retain narrow house capsule"),H->GetCapsuleComponent()->GetUnscaledCapsuleRadius(),28.f);
            RecoveryStart=H->GetActorLocation(); At=W->GetTimeSeconds(); Phase=9; return false;
        }
        if (Phase==9)
        {
            if (W->GetTimeSeconds()-At<.12) return false;
            Test->TestTrue(TEXT("idle catch-step never displaces the gameplay capsule"),FVector::Dist(H->GetActorLocation(),RecoveryStart)<.1);
            Test->TestTrue(TEXT("recovery is still active before immediate player jump"),H->IsStumbling());
            Key(EKeys::SpaceBar,IE_Pressed); At=W->GetTimeSeconds(); Phase=10; return false;
        }
        if (Phase==10)
        {
            if (W->GetTimeSeconds()-At<.1) return false;
            Test->TestTrue(TEXT("player can jump immediately during a catch-step"),Move->IsFalling() && Move->Velocity.Z>0);
            Test->TestFalse(TEXT("fresh jump cancels grounded stumble animation"),H->IsStumbling());
            Key(EKeys::SpaceBar,IE_Released); Phase=11; return false;
        }
        if (Phase==11)
        {
            if (!Move->IsMovingOnGround() || W->GetTimeSeconds()-At<.3) return false;
            UDinkInteriorCameraComponent* Camera=H->FindComponentByClass<UDinkInteriorCameraComponent>();
            Camera->AddZoomInput(2);
            TargetArm=Camera->GetDesiredArmLength(); At=W->GetTimeSeconds(); Phase=6; return false;
        }
        if (Phase==6)
        {
            if (W->GetTimeSeconds()-At<1) return false;
            Test->TestTrue(TEXT("camera tick honors zoom instead of resetting to screen preset"),FMath::Abs(H->CameraBoom->TargetArmLength-TargetArm)<1);
            UDinkGreyboxSubsystem* Grey=W->GetSubsystem<UDinkGreyboxSubsystem>();
            UDinkInteriorCameraComponent* Camera=H->FindComponentByClass<UDinkInteriorCameraComponent>();
            const FTransform Before=H->GetActorTransform();
            Camera->AddZoomInput(1); Camera->TickComponent(.016f,LEVELTICK_All,nullptr);
            TargetArm=Camera->GetDesiredArmLength();
            const float BeforeArm=H->CameraBoom->TargetArmLength;
            Test->TestTrue(TEXT("transition fixture has an ongoing smooth zoom"),FMath::Abs(BeforeArm-TargetArm)>1.f);
            const float ExpectedArm=FMath::FInterpTo(BeforeArm,TargetArm,.016f,10.f);
            ADinkScreenVolume* Neighbor=Grey->FindScreen(471);
            ADinkScreenVolume* Home=Grey->FindScreen(1);
            if (!Test->TestNotNull(TEXT("neighbor transition fixture"),Neighbor) || !Test->TestNotNull(TEXT("interior transition fixture"),Home)) return true;
            H->SetActorLocation(Neighbor->MapPixelToWorld(300,280)+FVector(0,0,100),false,nullptr,ETeleportType::TeleportPhysics);
            Grey->RefreshCurrentScreen(); Camera->TickComponent(.016f,LEVELTICK_All,nullptr);
            Test->TestTrue(TEXT("zoom continues smoothly without preset flash on an outdoor screen transition"),FMath::IsNearlyEqual(H->CameraBoom->TargetArmLength,ExpectedArm,.001f));
            H->SetActorLocation(Home->MapPixelToWorld(370,161)+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics);
            Grey->RefreshCurrentScreen(); Camera->TickComponent(.016f,LEVELTICK_All,nullptr);
            Test->TestTrue(TEXT("room transition immediately uses the selected bounded zoom"),FMath::IsNearlyEqual(H->CameraBoom->TargetArmLength,Camera->GetDesiredArmLength(),.001f));
            H->SetActorTransform(Before,false,nullptr,ETeleportType::TeleportPhysics);
            Grey->RefreshCurrentScreen(); Camera->TickComponent(.016f,LEVELTICK_All,nullptr);
            Test->TestTrue(TEXT("return outdoors retains chosen zoom without preset flash"),FMath::IsNearlyEqual(H->CameraBoom->TargetArmLength,TargetArm,.001f));
            Move->StopMovementImmediately();
            PC->UnPossess(); PC->Possess(H);
            At=W->GetTimeSeconds(); Phase=7; return false;
        }
        if (Phase==7)
        {
            if (W->GetTimeSeconds()-At<.1) return false;
            Key(EKeys::SpaceBar,IE_Pressed);
            At=W->GetTimeSeconds(); Phase=8; return false;
        }
        if (Phase==8)
        {
            if (W->GetTimeSeconds()-At<.1) return false;
            Key(EKeys::SpaceBar,IE_Released);
            Test->TestTrue(TEXT("repossession restores usable jump mapping"),Move->IsFalling() && Move->Velocity.Z>0);
            At=W->GetTimeSeconds(); Phase=12; return false;
        }
        if (Phase==12)
        {
            if (!Move->IsMovingOnGround() || W->GetTimeSeconds()-At<.3) return false;
            Test->TestEqual(TEXT("new-game Dink has the timid hop"),Move->JumpZVelocity,ADinkGreyboxCharacter::TimidJumpZ);
            Test->TestEqual(TEXT("new-game Dink has no confidence"),H->GetConfidence(),0.f);
            TimidWidth=H->GetMesh()->GetRelativeScale3D().X;
            // Level him up to a late-game hero; the body should grow into it over a few seconds.
            H->Stats->Stats.Level=12; H->Stats->Stats.Strength=20; H->Stats->Stats.Defense=8;
            At=W->GetTimeSeconds(); Phase=13; return false;
        }
        if (Phase==13)
        {
            if (W->GetTimeSeconds()-At<1.)
            {
                Test->TestTrue(TEXT("growth is gradual, not a one-frame snap"),H->GetConfidence()<.5f);
                return false;
            }
            if (W->GetTimeSeconds()-At<3.5) return false;
            Test->TestEqual(TEXT("levelled Dink is fully confident"),H->GetConfidence(),1.f);
            Test->TestEqual(TEXT("levelled Dink hops higher"),Move->JumpZVelocity,ADinkGreyboxCharacter::ConfidentJumpZ);
            const double Growth=H->GetMesh()->GetRelativeScale3D().X/TimidWidth;
            Test->AddInfo(FString::Printf(TEXT("Mesh width grew by %.3f"),Growth));
            Test->TestTrue(TEXT("scrawny frame fills out on the real mesh"),FMath::IsNearlyEqual(Growth,1./.86,.005));
            return true;
        }
        return false;
    }
private:
    FAutomationTestBase* Test;
    double Began=0,At=0,StartZ=0,Peak=0;
    float TargetArm=0;
    double TimidWidth=1;
    FVector RecoveryStart=FVector::ZeroVector;
    int32 Phase=0;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkMovementIntegrationTest,"Dink.Movement.PlayableControls",DINK_TEST_FLAGS)
bool FDinkMovementIntegrationTest::RunTest(const FString&)
{
    const FString File=FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook"),FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("real map loads"),UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    AddCommand(new FStartPIECommand(false)); AddCommand(new FDinkMovementPIE(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
