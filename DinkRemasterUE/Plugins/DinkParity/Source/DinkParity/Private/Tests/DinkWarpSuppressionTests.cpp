#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"
#include "AssetCompilingManager.h"
#include "Editor.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
#include "UObject/UObjectIterator.h"

namespace
{
class FDinkRealWarpOverlapCheck : public IAutomationLatentCommand
{
public:
    explicit FDinkRealWarpOverlapCheck(FAutomationTestBase* InTest) : Test(InTest), Began(FPlatformTime::Seconds()) {}
    bool Update() override
    {
        UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
        APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
        ADinkGreyboxCharacter* Hero = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
        if (FPlatformTime::Seconds() - Began > 60)
        { Test->AddError(FString::Printf(TEXT("real warp overlap timed out: mode%d stage%d"), Mode, Stage)); return true; }
        if (!Hero) return false;
        UDinkStorySubsystem* Story = World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>();
        UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
        if (!Story || !Greybox || Story->bNewGamePending) return false;
        UDinkDirector* Director = Story->GetDirector();
        ADinkScreenVolume* Screen = Greybox->FindScreenAt(Hero->GetActorLocation());
        if (Stage == 0)
        {
            Story->SkipDialogue();
            if (PC->IsMoveInputIgnored() || World->GetTimeSeconds() < 2) return false;
            for (TObjectIterator<UDinkWarpComponent> It; It; ++It)
            {
                if (It->GetWorld() != World) continue;
                if (It->WarpId == TEXT("S001_P25")) Exit = *It;
                if (It->WarpId == TEXT("S439_P13")) Entrance = *It;
            }
            if (!Exit || !Entrance) { Test->AddError(TEXT("real house door pair absent")); return true; }
            OriginalEntrance = Entrance->GetComponentTransform();
            Test->TestTrue(TEXT("real pawn is player controlled"), Hero->IsPlayerControlled());
            Test->TestTrue(TEXT("production story bound warp suppression"), !!Greybox->WarpSuppressed);
            Story->bRunScreenScripts = false;
            Stage = 1;
        }
        if (Stage == 1)
        {
            // Fixture setup near the actual door. The separate StonebrookPlay test walks the full house route.
            Director->GetDink().bMoving = false;
            Hero->GetCharacterMovement()->StopMovementImmediately();
            FVector Approach = Exit->GetComponentLocation() - FVector(0, 300, 0);
            Approach.Z = 98;
            Hero->SetActorLocation(Approach, false, nullptr, ETeleportType::TeleportPhysics);
            Greybox->RefreshCurrentScreen();
            Director->GetDink().Screen = 1;
            Director->SyncSpriteFromActor(Director->GetDink());
            Director->GetDink().Props.Add(TEXT("speed"), 1);
            Hero->GetCharacterMovement()->MaxWalkSpeed = 150;
            Wait = World->GetTimeSeconds() + 1;
            Stage = 2;
            return false;
        }
        if (Stage == 2)
        {
            if (World->GetTimeSeconds() < Wait) return false;
            Test->TestFalse(TEXT("fixture starts outside real exit overlap"), Exit->IsOverlappingActor(Hero));
            if (Mode == 1)
            {
                // Force a real synchronous destination overlap; the in-progress guard must prevent bouncing.
                Entrance->SetWorldLocation(Exit->DestLocation + FVector(0, 0, 100));
            }
            if (Mode < 2) Director->StartMove(Director->GetDink(), 2, 600, Mode == 0 ? 1 : 0);
            Stage = 3;
        }
        if (Stage == 3)
        {
            if (Mode == 0)
            {
                if (!Exit->IsOverlappingActor(Hero)) return false;
                Test->TestTrue(TEXT("script nohard1 reaches actual door overlap while remaining inside"), Screen && Screen->ScreenNumber == 1);
                Test->TestTrue(TEXT("overlap occurred during production nohard1 move"), Director->IsDinkCarriedThroughHardness());
                Director->GetDink().bMoving = false;
                ++Mode; Stage = 1;
                return false;
            }
            if (!Screen || Screen->ScreenNumber != 439)
            {
                if (Mode == 2) Hero->AddMovementInput((Exit->GetComponentLocation() - Hero->GetActorLocation()).GetSafeNormal2D());
                return false;
            }
            Test->TestTrue(Mode == 1 ? TEXT("script nohard0 really warps") : TEXT("ordinary movement really warps"),
                FVector2D(Hero->GetActorLocation() - Exit->DestLocation).Size() < 100);
            if (Mode == 1)
            {
                Test->TestTrue(TEXT("destination return trigger overlaps without recursive bounce"), Entrance->IsOverlappingActor(Hero));
                Entrance->SetWorldTransform(OriginalEntrance);
            }
            Director->GetDink().bMoving = false;
            Hero->GetCharacterMovement()->StopMovementImmediately();
            Wait = World->GetTimeSeconds() + 1;
            Stage = 4;
            return false;
        }
        if (Stage == 4)
        {
            if (World->GetTimeSeconds() < Wait) return false;
            Test->TestTrue(TEXT("warp guard unwinds and normal cooldown expires"), Greybox->CanWarp(Hero));
            Stage = 5;
        }
        if (Stage == 5)
        {
            if (Screen && Screen->ScreenNumber == 1)
            {
                Test->TestTrue(TEXT("later actual entrance overlap reenters without bounce"),
                    FVector2D(Hero->GetActorLocation() - Entrance->DestLocation).Size() < 100);
                Hero->GetCharacterMovement()->StopMovementImmediately();
                if (++Mode == 3) return true;
                Stage = 1;
                return false;
            }
            Hero->AddMovementInput((Entrance->GetComponentLocation() - Hero->GetActorLocation()).GetSafeNormal2D());
        }
        return false;
    }
private:
    FAutomationTestBase* Test;
    double Began, Wait = 0;
    int32 Mode = 0, Stage = 0;
    UDinkWarpComponent* Exit = nullptr;
    UDinkWarpComponent* Entrance = nullptr;
    FTransform OriginalEntrance;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWarpSuppressionTest, "Dink.Import.Greybox.ScriptNoHardWarpOverlap", DINK_TEST_FLAGS)
bool FDinkWarpSuppressionTest::RunTest(const FString&)
{
    const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook"), FPackageName::GetMapPackageExtension());
    if (!IFileManager::Get().FileExists(*File)) { AddWarning(TEXT("skipped: generated Stonebrook map absent")); return true; }
    if (!TestNotNull(TEXT("real Stonebrook map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkRealWarpOverlapCheck(this));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
    return true;
}
