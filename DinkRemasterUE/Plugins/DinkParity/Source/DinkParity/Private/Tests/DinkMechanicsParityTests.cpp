#include "DinkTestHelpers.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "DinkFloatingNumbers.h"
#include "DinkFactSubsystem.h"
#include "Components/SceneComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"

/**
 * Mechanics QA (15 Nov 2026): the player's own keys measured against the 1997 human_brain (source/dink/dink.cpp).
 *
 * 1997 values (RTDink, locked at 60 Hz, dink.cpp:17304-17318: Dink's speed is 3 with dinkspeed 3):
 *  - straight walk 3 px per frame (move() with amount = speed, 15013-15036), diagonal 2 + 2 px (speed - speed / 3, 15044-15070):
 *    the diagonal is 2.83 / 3 = 0.943 of the straight speed (asserted for a key diagonal); no acceleration, no braking: the first
 *    and last frame of input already move or stop him (measured and reported: the remaster eases, an owner decision).
 *  - dir follows the keys on their frame (changedir after move, same lines); an attack (14812-14820) or a spell (14906-14941)
 *    reads that dir at once.
 *  - while sp_nocontrol is set (item-fst.c / item-fb.c after sp_seq) human_brain returns before the movement keys (14742) until
 *    the sequence has played (16958): Dink stands for the 400 ms of a punch.
 *  - with the bow drawn human_brain runs process_bow and returns (14761-14766): the keys turn him (14568-14598), he does not walk.
 * The remaster's walk/run speeds and their easing are owner decisions (UE AGENTS.md "Animation pass 2"); they are measured here
 * and reported, not asserted against pixels.
 */
namespace
{
class FDinkMechanicsHeroPIE : public IAutomationLatentCommand
{
public:
    explicit FDinkMechanicsHeroPIE(FAutomationTestBase* T) : Test(T) {}
    bool Update() override
    {
        if (!Began) Began = FPlatformTime::Seconds();
        UWorld* W = GEditor ? GEditor->PlayWorld.Get() : nullptr;
        APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
        ADinkGreyboxCharacter* H = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
        UDinkStorySubsystem* Story = W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (FPlatformTime::Seconds() - Began > 120) { Test->AddError(TEXT("mechanics PIE timeout")); return true; }
        if (!H || !Story || Story->bNewGamePending) return false;
        UCharacterMovementComponent* Move = H->GetCharacterMovement();
        UDinkDirector* D = Story->GetDirector();
        UDinkGameplay* G = Story->GetGameplay();
        const double Now = W->GetTimeSeconds();
        const double Since = Now - At;
        const FRotator Yaw(0.f, PC->GetControlRotation().Yaw, 0.f);
        auto WorldOf = [&](FVector2D Axis) { return FVector(FRotationMatrix(Yaw).GetUnitAxis(EAxis::X) * Axis.Y + FRotationMatrix(Yaw).GetUnitAxis(EAxis::Y) * Axis.X).GetSafeNormal2D(); };
        auto Next = [&](int32 P) { Phase = P; At = Now; Samples.Reset(); bMark = false; Mark = 0; };
        // The run key is polled from the controller every frame (ADinkGreyboxCharacter::Tick): press it as a key.
        auto Key = [PC](FKey K, EInputEvent E) { PC->InputKey(FInputKeyEventArgs(nullptr, INPUTDEVICEID_NONE, K, E, FPlatformTime::Cycles64())); };
        const double Speed = Move->Velocity.Size2D();
        if (Phase == 0)
        {
            Story->bRunScreenScripts = false;
            FDinkScriptInstance Caller;
            Story->GetDirector()->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> unfreeze 1"), {TEXT("cmd")}));
            Story->ResetRuntime(); G->bBrainsEnabled = false;
            Story->GetDirector()->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> unfreeze 1"), {TEXT("cmd")}));
            ADinkScreenVolume* Yard = W->GetSubsystem<UDinkGreyboxSubsystem>()->FindScreen(439);
            if (!Test->TestNotNull(TEXT("yard fixture"), Yard)) return true;
            H->SetActorLocation(Yard->MapPixelToWorld(300, 280) + FVector(0, 0, 100), false, nullptr, ETeleportType::TeleportPhysics);
            Move->StopMovementImmediately();
            FistSlot = G->AddItem(TEXT("item-fst"), false) + 1;
            BowSlot = G->AddItem(TEXT("item-b1"), false) + 1;
            Test->TestTrue(TEXT("fists armed"), FistSlot > 0 && G->ArmItemSlot(FistSlot));
            Next(1); return false;
        }
        if (Phase == 1)
        {
            if (!Move->IsMovingOnGround() || Since < .3) return false;
            Next(10); Start = H->GetActorLocation(); return false;
        }
        // ---- M1: walk from a standstill and stop (the player's keys walk by default).
        if (Phase == 10)
        {
            H->PlayerMoveInput(FVector2D(0, 1));
            if (!bMark && Speed >= .95 * ADinkGreyboxCharacter::WalkSpeed) { bMark = true; Mark = Since; }
            if (Since < 1.2) return false;
            WalkTopSpeed = Speed; WalkReach95 = bMark ? Mark : -1;
            Next(11); Start = H->GetActorLocation(); return false;
        }
        if (Phase == 11)
        {
            if (!bMark && Speed < 1.) { bMark = true; Mark = Since; WalkStopCm = FVector::Dist2D(Start, H->GetActorLocation()); }
            if (Since < .6) return false;
            Test->AddInfo(FString::Printf(TEXT("M1 walk: top %.1f cm/s, 95%% after %.3f s, stops in %.3f s over %.1f cm (1997: 180 px/s from the first frame, stops on the frame)"),
                WalkTopSpeed, WalkReach95, bMark ? Mark : -1., WalkStopCm));
            Test->TestTrue(TEXT("walk reaches its top speed"), WalkReach95 >= 0 && WalkReach95 < .5);
            Key(EKeys::LeftShift, IE_Pressed);
            MaxSpeed = 0;
            Next(12); return false;
        }
        // ---- M2: run from a standstill (run key held) and stop.
        if (Phase == 12)
        {
            H->PlayerMoveInput(FVector2D(0, 1));
            MaxSpeed = FMath::Max(MaxSpeed, Speed);
            if (!bMark && Speed >= .95 * ADinkGreyboxCharacter::RunSpeed) { bMark = true; Mark = Since; }
            // Long enough to reach the top speed, short enough (about 5 m) not to run into the yard's fence.
            if (Since < 1.1 && !(bMark && Since > Mark + .15)) return false;
            RunTopSpeed = MaxSpeed; RunReach95 = bMark ? Mark : -1;
            Test->TestTrue(FString::Printf(TEXT("the run key runs (top %.1f cm/s)"), MaxSpeed), MaxSpeed > 550.);
            Key(EKeys::LeftShift, IE_Released);
            Next(13); Start = H->GetActorLocation(); return false;
        }
        if (Phase == 13)
        {
            if (!bMark && Speed < 1.) { bMark = true; Mark = Since; RunStopCm = FVector::Dist2D(Start, H->GetActorLocation()); }
            if (Since < .8) return false;
            Test->AddInfo(FString::Printf(TEXT("M2 run: top %.1f cm/s, 95%% after %.3f s, stops in %.3f s over %.1f cm"), RunTopSpeed, RunReach95, bMark ? Mark : -1., RunStopCm));
            Next(14); return false;
        }
        // ---- M3: a digital diagonal against the straight walk.
        if (Phase == 14)
        {
            H->PlayerMoveInput(FVector2D(1, 1));
            if (Since < 1.2) return false;
            Test->AddInfo(FString::Printf(TEXT("M3 diagonal walk %.1f cm/s = %.3f of the straight walk (1997: 2+2 px against 3 px a frame = 0.943)"), Speed, Speed / FMath::Max(WalkTopSpeed, 1.)));
            Test->TestTrue(TEXT("a key diagonal is the original's 0.943 of the straight walk"), FMath::Abs(Speed / FMath::Max(WalkTopSpeed, 1.) - .943) < .02);
            Next(15); return false;
        }
        if (Phase == 15)
        {
            if (Since < .6) return false;
            Next(20); return false;
        }
        // ---- M4: walk one way, reverse and attack on the same frame: the punch goes the new way, Dink stands for it.
        if (Phase == 20)
        {
            H->PlayerMoveInput(FVector2D(1, 0));
            if (Since < .8) return false;
            Test->TestEqual(TEXT("the player's keys turn the pawn faster than fed movement"), double(Move->RotationRate.Yaw), 900.0);
            // A choice menu or freeze (move input ignored): the original skips the keys (goto freeze, D:14744-14757).
            const FVector Right = WorldOf(FVector2D(1, 0));
            PC->SetIgnoreMoveInput(true);
            H->PlayerMoveInput(FVector2D(-1, 0));
            FVector Keys = FVector::ZeroVector;
            Test->TestTrue(TEXT("keys while input is ignored record no facing"), H->GetPlayerFacing(Keys) && FVector::DotProduct(Keys, Right) > .99);
            Test->TestTrue(TEXT("and do not turn him"), FVector::DotProduct(H->GetActorForwardVector(), Right) > .95);
            PC->SetIgnoreMoveInput(false);
            // The reversal key's frame (no attack yet).
            H->PlayerMoveInput(FVector2D(-1, 0));
            Next(23); return false;
        }
        if (Phase == 23)
        {
            // Next frame: the attack key is read before that frame's direction keys (D:14812 before 15013), so it takes the
            // dir the keys set on the previous frame, here the reversal, although the pawn has only begun to turn.
            const FVector Back = WorldOf(FVector2D(-1, 0));
            const double ForwardDot = FVector::DotProduct(H->GetActorForwardVector(), Back);
            const bool bStarted = G->InputAttackPressed();
            H->PlayerMoveInput(FVector2D(-1, 0));
            Test->TestTrue(TEXT("the press starts a punch"), bStarted);
            int32 Want = D->DirFromWorld(D->GetDink().Screen, H->GetActorLocation(), Back);
            if (Want == 1 || Want == 3) Want = 2; if (Want == 7 || Want == 9) Want = 8; // item-fst.c: no diagonal punches
            Test->TestEqual(FString::Printf(TEXT("the punch takes the last keys' dir at once (pawn forward . keys was %.2f)"), ForwardDot), D->GetDink().Dir, Want);
            Test->TestTrue(TEXT("Dink is held by the punch's sp_nocontrol"), G->IsDinkHeldBySequence());
            Test->TestTrue(TEXT("and the pawn's keys are rooted"), H->GetPlayerHold() == EDinkPlayerHold::Rooted);
            Test->TestTrue(FString::Printf(TEXT("the walk stops on the press (%.1f cm/s)"), Move->Velocity.Size2D()), Move->Velocity.Size2D() < 1.);
            G->InputAttackReleased(); // the key comes up again (a second press without a release is an OS repeat: FDinkAttackGate)
            Start = H->GetActorLocation(); MaxSpeed = 0;
            Next(21); return false;
        }
        if (Phase == 21)
        {
            H->PlayerMoveInput(FVector2D(-1, 0)); // the key stays down through the punch
            if (Since < .3) { MaxSpeed = FMath::Max(MaxSpeed, Speed); return false; }
            const double Drift = FVector::Dist2D(Start, H->GetActorLocation());
            Test->AddInfo(FString::Printf(TEXT("M4 during the punch: drift %.1f cm, top %.1f cm/s"), Drift, MaxSpeed));
            Test->TestTrue(TEXT("Dink stands for the punch (1997: nocontrol for the 400 ms sequence)"), Drift < 3. && MaxSpeed < 5.);
            Next(22); return false;
        }
        if (Phase == 22)
        {
            H->PlayerMoveInput(FVector2D(-1, 0));
            if (Since < .5) return false;
            Test->TestTrue(TEXT("the punch's hold has ended"), H->GetPlayerHold() == EDinkPlayerHold::None);
            Test->TestTrue(FString::Printf(TEXT("and the keys walk again (%.1f cm/s)"), Speed), Speed > 100.);
            // An attack and a new direction key on the same frame: the attack still takes the old dir (D:14812 before 15013).
            const FVector Back = WorldOf(FVector2D(-1, 0));
            Test->TestTrue(TEXT("a press on the key's own frame starts a punch"), G->InputAttackPressed());
            H->PlayerMoveInput(FVector2D(1, 0));
            int32 Want = D->DirFromWorld(D->GetDink().Screen, H->GetActorLocation(), Back);
            if (Want == 1 || Want == 3) Want = 2; if (Want == 7 || Want == 9) Want = 8;
            Test->TestEqual(TEXT("and goes the way of the previous frame's keys"), D->GetDink().Dir, Want);
            G->InputAttackReleased();
            Next(30); return false;
        }
        // ---- M5: the bow: drawn, the keys turn Dink and do not move him; the arrow flies the way he faces.
        if (Phase == 30)
        {
            if (Since < .6) return false;
            G->bBrainsEnabled = true; // process_bow runs on the brain clock (DinkBrains.cpp TickBrains)
            Test->TestTrue(TEXT("bow armed"), BowSlot > 0 && G->ArmItemSlot(BowSlot));
            Test->TestTrue(TEXT("the press draws the bow"), G->InputAttackPressed() && G->IsBowActive());
            Start = H->GetActorLocation(); MaxSpeed = 0;
            Next(31); return false;
        }
        if (Phase == 31)
        {
            H->PlayerMoveInput(FVector2D(0, -1));
            MaxSpeed = FMath::Max(MaxSpeed, Speed);
            if (Since < .5) return false;
            const FVector Want = WorldOf(FVector2D(0, -1));
            Test->TestTrue(TEXT("drawn, the keys hold Dink to turning"), H->GetPlayerHold() == EDinkPlayerHold::TurnOnly);
            Test->TestTrue(FString::Printf(TEXT("drawn, the keys do not walk him (drift %.1f cm, top %.1f cm/s)"), FVector::Dist2D(Start, H->GetActorLocation()), MaxSpeed),
                FVector::Dist2D(Start, H->GetActorLocation()) < 3. && MaxSpeed < 5.);
            Test->TestTrue(TEXT("drawn, the keys turn him"), FVector::DotProduct(H->GetActorForwardVector(), Want) > .99);
            Test->TestEqual(TEXT("and his dir follows"), D->GetDink().Dir, D->DirFromWorld(D->GetDink().Screen, H->GetActorLocation(), Want));
            Next(33); return false;
        }
        // ---- M5b: process_bow's diagonal hold (D:14566-14596): a diagonal sets a 100 ms wait; a single key turns him only after it.
        if (Phase == 33)
        {
            H->PlayerMoveInput(FVector2D(1, 1));
            if (Since < .25) return false;
            DiagDir = D->GetDink().Dir;
            Next(34); return false;
        }
        if (Phase == 34)
        {
            H->PlayerMoveInput(FVector2D(1, 0)); // Up let go a frame before Right
            const int32 Straight = D->DirFromWorld(D->GetDink().Screen, H->GetActorLocation(), WorldOf(FVector2D(1, 0)));
            const bool bMeaningful = (DiagDir == 1 || DiagDir == 3 || DiagDir == 7 || DiagDir == 9) && Straight % 2 == 0;
            if (!bMeaningful) { Test->AddInfo(TEXT("M5b skipped: the camera does not map the keys to a screen diagonal")); G->InputAttackReleased(); Next(32); return false; }
            if (Since < .05) { Test->TestEqual(TEXT("within 100 ms of the diagonal a single key keeps the diagonal aim"), D->GetDink().Dir, DiagDir); return false; }
            if (Since < .25) return false;
            Test->TestEqual(TEXT("after the 100 ms the single key turns him"), D->GetDink().Dir, Straight);
            DiagDir = Straight;
            Next(35); return false;
        }
        if (Phase == 35)
        {
            if (Since < .2) { Test->TestEqual(TEXT("no key, no turn while drawn"), D->GetDink().Dir, DiagDir); return false; }
            G->InputAttackReleased();
            Next(32); return false;
        }
        if (Phase == 32)
        {
            if (Since < .3) return false;
            Test->TestFalse(TEXT("released, the bow is down"), G->IsBowActive());
            Test->TestTrue(TEXT("and the keys are free"), H->GetPlayerHold() == EDinkPlayerHold::None);
            Test->TestTrue(TEXT("fists again"), G->ArmItemSlot(FistSlot));
            G->bBrainsEnabled = false;
            Next(40); return false;
        }
        // ---- M6: movement fed directly (the bot, scripts) keeps the old turn rate and the pawn's forward vector for the attack.
        if (Phase == 40)
        {
            if (Since < .6) return false;
            H->AddMovementInput(WorldOf(FVector2D(1, 0)));
            if (Since < 1.4) return false;
            Test->TestFalse(TEXT("fed movement is not a person steering"), H->IsHumanSteering());
            Test->TestEqual(TEXT("fed movement turns at the old 300 deg/s"), double(Move->RotationRate.Yaw), 300.0);
            FVector Unused;
            Test->TestFalse(TEXT("fed movement clears the keys' facing"), H->GetPlayerFacing(Unused));
            const int32 Fwd = D->DirFromWorld(D->GetDink().Screen, H->GetActorLocation(), H->GetActorForwardVector());
            Test->TestTrue(TEXT("the ungated attack still works"), G->PlayerAttack());
            int32 Want = Fwd; if (Want == 1 || Want == 3) Want = 2; if (Want == 7 || Want == 9) Want = 8;
            Test->TestEqual(TEXT("and faces the pawn's forward vector"), D->GetDink().Dir, Want);
            Test->TestTrue(TEXT("fed movement is never rooted by the hold (only the player's keys are)"), FVector::Dist2D(Move->Velocity, FVector::ZeroVector) > 50.);
            Next(50); return false;
        }
        // ---- M7: draw_damage / add_exp: a hit on a monster shows the damage over it for one second (presentation only).
        if (Phase == 50)
        {
            if (Since < .5) return false;
            AActor* Body = W->SpawnActor<AActor>(AActor::StaticClass(), FTransform(H->GetActorLocation() + FVector(200, 0, 0)));
            USceneComponent* Root = NewObject<USceneComponent>(Body, TEXT("Root"));
            Body->SetRootComponent(Root); Root->RegisterComponent();
            const int32 T = D->CreateVirtualSprite(D->GetDink().Screen, D->GetDink().X + 40, D->GetDink().Y);
            FDinkSprite* S = D->FindSprite(T);
            S->Actor = Body;
            S->Props.Add(TEXT("brain"), 9); S->Props.Add(TEXT("hitpoints"), 10);
            S->Damage = 4;
            Monster = T;
            Next(51); return false;
        }
        if (Phase == 51)
        {
            UDinkFloatingNumbers* Numbers = W->GetSubsystem<UDinkFloatingNumbers>();
            if (!Test->TestNotNull(TEXT("floating numbers in the game world"), Numbers)) return true;
            if (Since < .05) return false;
            Test->TestEqual(TEXT("the hit took 4 of 10 hitpoints"), D->FindSprite(Monster)->GetProp(TEXT("hitpoints")), 6);
            Test->TestEqual(TEXT("one number is shown"), Numbers->Num(), 1);
            Test->TestEqual(TEXT("it is the damage"), Numbers->NewestText(), FString(TEXT("4")));
            Story->GetFacts()->SetFact(TEXT("lifemax"), 100); Story->GetFacts()->SetFact(TEXT("life"), 100);
            D->GetDink().Damage = 3; // human_brain draws Dink's damage too (D:14699)
            Next(53); return false;
        }
        if (Phase == 53)
        {
            UDinkFloatingNumbers* Numbers = W->GetSubsystem<UDinkFloatingNumbers>();
            if (Since < .05) return false;
            Test->TestEqual(TEXT("Dink's own damage shows its number"), Numbers->NewestText(), FString(TEXT("3")));
            Next(52); return false;
        }
        if (Phase == 52)
        {
            if (Since < 1.1) return false;
            Test->TestEqual(TEXT("after a second they are gone (kill 1000)"), W->GetSubsystem<UDinkFloatingNumbers>()->Num(), 0);
            return true;
        }
        return true;
    }
    FAutomationTestBase* Test;
    double Began = 0, At = 0, Mark = 0;
    bool bMark = false;
    int32 Phase = 0, FistSlot = 0, BowSlot = 0, Monster = 0, DiagDir = 0;
    FVector Start = FVector::ZeroVector;
    double WalkTopSpeed = 0, WalkReach95 = 0, WalkStopCm = 0, RunTopSpeed = 0, RunReach95 = 0, RunStopCm = 0, MaxSpeed = 0;
    TArray<double> Samples;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkMechanicsHeroInputTest, "Dink.Mechanics.HeroInputParity", DINK_TEST_FLAGS)
bool FDinkMechanicsHeroInputTest::RunTest(const FString&)
{
    const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook"), FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("real map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    AddCommand(new FStartPIECommand(false)); AddCommand(new FDinkMechanicsHeroPIE(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
