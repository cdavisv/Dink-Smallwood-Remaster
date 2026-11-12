#include "DinkTestHelpers.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkStatsComponent.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"
#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
#include "UObject/UObjectIterator.h"

namespace
{
class FDoorRetryCheck : public IAutomationLatentCommand
{
public:
    explicit FDoorRetryCheck(FAutomationTestBase* T):Test(T),Start(FPlatformTime::Seconds()) {}
    bool Update() override
    {
        if (FPlatformTime::Seconds()-Start>100) { Test->AddError(TEXT("door retry fixture timed out")); return true; }
        UWorld* W=GEditor ? GEditor->PlayWorld.Get() : nullptr;
        auto* PC=W ? W->GetFirstPlayerController() : nullptr;
        auto* G=W ? W->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
        auto* Story=W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (!PC || !G || !Story || Story->bNewGamePending) return false;
        if (!Hero) Hero=Cast<ADinkGreyboxCharacter>(PC->GetPawn());
        if (!Hero) return false;
        auto* Move=Hero->GetCharacterMovement();
        const double Now=W->GetTimeSeconds();
        if (!Phase)
        {
            Story->SkipDialogue(); if (PC->IsMoveInputIgnored() || Now<2.) return false;
            Story->bRunScreenScripts=false;
            Story->GetDirector()->GetDink().bMoving=false;
            for (TObjectIterator<UDinkWarpComponent> It;It;++It)
                if (It->GetWorld()==W)
                { if (It->WarpId==TEXT("S001_P25")) Exit=*It; if (It->WarpId==TEXT("S439_P13")) Entry=*It; }
            if (!Exit || !Entry) { Test->AddError(TEXT("actual house door pair missing")); return true; }
            OriginalKind=Exit->Kind; OriginalMode=Exit->TriggerMode; OriginalSource=Exit->SourceScreen;
            OriginalEnabled=Exit->bTriggerEnabled;
            Test->TestTrue(TEXT("actual door/exit and walk_in metadata"),Exit->Kind==TEXT("exit") && Entry->Kind==TEXT("door") && Exit->TriggerMode==TEXT("walk_in"));
            // Fixture begins outdoors. The subsequent entry and final re-exit use ordinary movement.
            Hero->SetActorLocation(Exit->DestLocation+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics);
            Move->StopMovementImmediately(); G->RefreshCurrentScreen();
            Story->GetDirector()->GetDink().Screen=439;
            Story->GetDirector()->SyncSpriteFromActor(Story->GetDirector()->GetDink());
            End=Now+1.; Phase=1; return false;
        }
        if (Phase==1)
        {
            if (Now<End) return false;
            const auto* Physical=G->FindScreenAt(Hero->GetActorLocation());
            if (!Physical || Physical->ScreenNumber!=1)
            { Hero->AddMovementInput((Entry->GetComponentLocation()-Hero->GetActorLocation()).GetSafeNormal2D()); return false; }
            Move->StopMovementImmediately(); Hero->ConsumeMovementInputVector(); Arrival=Hero->GetActorLocation();
            Test->TestTrue(TEXT("real entry leaves capsule overlapping actual return trigger"),Exit->IsOverlappingActor(Hero));
            Approach=Exit->GetRetryApproachDirection(Hero);
            Test->TestTrue(TEXT("arrival approach direction exists"),!Approach.IsNearlyZero());
            OriginalLife=Hero->Stats->Stats.Life;
            SavedSuppression=MoveTemp(G->WarpSuppressed);
            G->WarpSuppressed=SavedSuppression;
            Case=-1; Phase=2;
        }
        if (Phase==2)
        {
            Restore(PC,G);
            // Reset only fixture state between negative cases; no fabricated BeginOverlap event.
            G->NotifyWarped(Hero,*Entry);
            Hero->SetActorLocation(Arrival,false,nullptr,ETeleportType::TeleportPhysics);
            Move->StopMovementImmediately(); Hero->ConsumeMovementInputVector(); G->RefreshCurrentScreen();
            if (++Case==11)
            {
                // Retained approach survives crossing the centre, unlike recomputing centre-minus-position.
                const FVector Remembered=Exit->GetRetryApproachDirection(Hero);
                FVector Past=Exit->GetComponentLocation()+Remembered*5.; Past.Z=Arrival.Z;
                Hero->SetActorLocation(Past,false,nullptr,ETeleportType::TeleportPhysics);
                Test->TestTrue(TEXT("past-centre fixture remains overlapping"),Exit->IsOverlappingActor(Hero));
                Test->TestTrue(TEXT("initial approach remains valid past trigger centre"),FVector::DotProduct(Remembered,Exit->GetRetryApproachDirection(Hero))>.99);
                Hero->SetActorLocation(Arrival,false,nullptr,ETeleportType::TeleportPhysics);
                Move->StopMovementImmediately(); Hero->ConsumeMovementInputVector();
                G->NotifyWarped(Hero,*Entry); End=Now+UDinkGreyboxSubsystem::WarpCooldownSeconds; Phase=4; return false;
            }
            if (Case==1) PC->SetIgnoreMoveInput(true);
            if (Case==2) G->WarpSuppressed=[](const APawn*){return true;};
            if (Case==3) Exit->bTriggerEnabled=false;
            if (Case==4) Exit->Kind=TEXT("hole");
            if (Case==5) Exit->TriggerMode=TEXT("touch_approx");
            if (Case==6) Exit->SourceScreen=439;
            if (Case==7) PC->UnPossess();
            if (Case==8) Hero->Stats->Stats.Life=0; // Private component fixture; no death/quest/fact broadcast.
            if (Case==9)
            {
                Exit->Kind=TEXT("hole"); // Prime a nonzero acceleration without allowing a warp.
                End=Now+.5; Phase=3; return false;
            }
            if (Case==10)
            {
                auto* CharacterNPC=W->SpawnActor<ACharacter>(); NPC=CharacterNPC;
                CharacterNPC->GetCharacterMovement()->DisableMovement();
                auto* Capsule=CharacterNPC->GetCapsuleComponent();
                Capsule->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
                Capsule->SetCollisionResponseToAllChannels(ECR_Overlap); Capsule->SetGenerateOverlapEvents(true);
                NPC->SetActorLocation(Exit->GetComponentLocation()); Capsule->UpdateOverlaps();
                NPCStart=NPC->GetActorLocation();
                Test->TestTrue(TEXT("nonplayer fixture really overlaps return trigger"),Exit->IsOverlappingActor(NPC));
            }
            End=Now+1.1; Phase=5;
        }
        if (Phase==3)
        {
            Hero->AddMovementInput(Approach,1,true);
            if (Now<End) return false;
            Test->TestTrue(TEXT("fixture primes actual current acceleration"),!Move->GetCurrentAcceleration().IsNearlyZero());
            Move->bUpdateOnlyIfRendered=true; Exit->Kind=OriginalKind;
            End=Now+1.1; Phase=5; return false;
        }
        if (Phase==5)
        {
            // Case0 releases input; case10 moves away. Others push even when blocked at zero velocity.
            if (Case!=0 && Case!=10) Hero->AddMovementInput(Approach,1,true);
            if (Case==10) Hero->AddMovementInput(-Approach);
            if (Now<End) return false;
            const auto* Physical=G->FindScreenAt(Hero->GetActorLocation());
            Test->TestTrue(*FString::Printf(TEXT("negative case%d stays on source screen"),Case),Physical && Physical->ScreenNumber==1);
            if (Case==0) Test->TestTrue(TEXT("idle after cooldown never bounces"),Exit->IsOverlappingActor(Hero));
            if (Case==9) Test->TestTrue(TEXT("stale acceleration cannot retry when movement updates skip"),Move->IsComponentTickEnabled() && !Move->GetCurrentAcceleration().IsNearlyZero());
            if (NPC) { Test->TestTrue(TEXT("uncontrolled pawn never warps"),NPC->GetActorLocation().Equals(NPCStart)); NPC->Destroy(); NPC=nullptr; }
            Phase=2; return false;
        }
        if (Phase==4)
        {
            Hero->AddMovementInput(Approach);
            const auto* Physical=G->FindScreenAt(Hero->GetActorLocation());
            if (Now<End-.05)
                Test->TestTrue(TEXT("held toward input respects full cooldown"),Physical && Physical->ScreenNumber==1);
            if (Physical && Physical->ScreenNumber==439)
            {
                Test->TestTrue(TEXT("deliberate re-exit succeeds without leaving overlap first"),Now>=End-.02);
                Move->StopMovementImmediately(); Hero->ConsumeMovementInputVector(); End=Now+1.; Phase=6;
            }
            return false;
        }
        if (Phase==6)
        {
            if (Now<End) return false;
            const auto* Physical=G->FindScreenAt(Hero->GetActorLocation());
            Test->TestTrue(TEXT("no recursive or later idle destination bounce"),Physical && Physical->ScreenNumber==439 && G->CanWarp(Hero));
            Restore(PC,G); return true;
        }
        return false;
    }
private:
    void Restore(APlayerController* PC,UDinkGreyboxSubsystem* G)
    {
        PC->ResetIgnoreMoveInput(); if (!PC->GetPawn()) PC->Possess(Hero);
        Exit->Kind=OriginalKind; Exit->TriggerMode=OriginalMode; Exit->SourceScreen=OriginalSource; Exit->bTriggerEnabled=OriginalEnabled;
        Hero->Stats->Stats.Life=OriginalLife; Hero->GetCharacterMovement()->bUpdateOnlyIfRendered=false;
        G->WarpSuppressed=SavedSuppression;
    }
    FAutomationTestBase* Test; double Start,End=0; int32 Phase=0,Case=0,OriginalLife=1,OriginalSource=0;
    ADinkGreyboxCharacter* Hero=nullptr; UDinkWarpComponent* Exit=nullptr; UDinkWarpComponent* Entry=nullptr; APawn* NPC=nullptr;
    FVector Arrival,Approach,NPCStart; FName OriginalKind,OriginalMode; bool OriginalEnabled=true;
    TFunction<bool(const APawn*)> SavedSuppression;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkDoorRetryTest,"Dink.Import.Greybox.DoorOverlapIntentRetry",DINK_TEST_FLAGS)
bool FDinkDoorRetryTest::RunTest(const FString&)
{
    const FString File=FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook"),FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("real Stonebrook loads"),UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    AddCommand(new FStartPIECommand(false)); AddCommand(new FDoorRetryCheck(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
