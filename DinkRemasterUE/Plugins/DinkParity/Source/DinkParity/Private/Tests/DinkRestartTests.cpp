#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkInventoryComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
class FRestartFromDeath : public IAutomationLatentCommand
{
public:
    explicit FRestartFromDeath(FAutomationTestBase* InTest) : Test(InTest) {}
    bool Update() override
    {
        if (!Began) Began = FPlatformTime::Seconds();
        if (FPlatformTime::Seconds() - Began > 90) { Test->AddError(FString::Printf(TEXT("death restart timed out at phase%d cycle%d"), Phase, Cycle)); return true; }
        if (!GI.IsValid() && GEditor && GEditor->PlayWorld) GI = GEditor->PlayWorld->GetGameInstance();
        UWorld* World = GI.IsValid() ? GI->GetWorld() : nullptr;
        ADinkGreyboxCharacter* Hero = World && World->GetFirstPlayerController() ? Cast<ADinkGreyboxCharacter>(World->GetFirstPlayerController()->GetPawn()) : nullptr;
        UDinkStorySubsystem* Story = GI.IsValid() ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (!Hero || !Story || Story->bNewGamePending) return false;
        UDinkDirector* Director = Story->GetDirector();
        UDinkFactSubsystem* Facts = Story->GetFacts();
        UDinkWorldStateSubsystem* State = GI->GetSubsystem<UDinkWorldStateSubsystem>();
        UDinkInventoryComponent* Inventory = Hero->FindComponentByClass<UDinkInventoryComponent>();
        if (Phase == 0 || Phase == 3)
        {
            // Ordinary Space behavior clears opening dialogue; never change freeze or life directly.
            Story->SkipDialogue();
            if (Story->GetActiveMenu() || Director->GetDink().bFrozen || World->GetFirstPlayerController()->IsMoveInputIgnored()) return false;
            if (Phase == 3)
            {
                Test->TestTrue(TEXT("restart replaces the UWorld"), World != OldWorld.Get());
                Test->TestTrue(TEXT("restart replaces the player pawn"), Hero != OldPawn.Get());
                Test->TestEqual(TEXT("new player has initial life"), Facts->GetFact(TEXT("life")), 10);
                Test->TestEqual(TEXT("original opening restores fresh starting story"), Facts->GetFact(TEXT("story")), InitialStory);
                Test->TestEqual(TEXT("gold reset"), Facts->GetFact(TEXT("gold")), 0);
                Test->TestEqual(TEXT("normal status/death processing restored"), Facts->GetFact(TEXT("update_status")), 1);
                Test->TestEqual(TEXT("old placement overrides removed"), State->NumOverrides(), 0);
                Test->TestTrue(TEXT("old screen visit clock removed"), State->ExportScreenExitTimes().IsEmpty());
                Test->TestEqual(TEXT("newgame adds fists exactly once"), Inventory->CountItem(TEXT("item-fst")), 1);
                Test->TestEqual(TEXT("newgame arms fists"), Inventory->GetArmedItem(), FName(TEXT("item-fst")));
                Test->TestEqual(TEXT("previous inventory discarded"), Inventory->CountItem(TEXT("restart-test-item")), 0);
                Test->TestTrue(TEXT("fresh game has no pending attack hits"), Story->GetGameplay()->SaveState()->GetArrayField(TEXT("pendingHits")).IsEmpty());
                Test->TestEqual(TEXT("old death instance cleared"), Story->GetGameplay()->SaveState()->GetIntegerField(TEXT("death")), 0);
                Test->TestTrue(TEXT("new world starts at house"), World->GetSubsystem<UDinkGreyboxSubsystem>()->GetCurrentScreen() && World->GetSubsystem<UDinkGreyboxSubsystem>()->GetCurrentScreen()->ScreenNumber == 1);
                Test->TestTrue(TEXT("new player uses original start position"), FVector2D(Hero->GetActorLocation()-InitialPosition).Size() < 20);
                Test->TestFalse(TEXT("new player is unfrozen after dialogue"), Director->GetDink().bFrozen);
                Test->TestFalse(TEXT("new controller accepts movement"), World->GetFirstPlayerController()->IsMoveInputIgnored());
                ++Cycle;
                if (Cycle == 2) return true;
            }
            else
            {
                InitialPosition = Hero->GetActorLocation();
                // Original s1-h1-m.c:70 advances story0 to1 after the opening.
                // Compare the same post-dialogue point on a genuinely fresh world.
                InitialStory = Facts->GetFact(TEXT("story"));
            }
            // Before dying, enter a screen whose hardness is a registered original-hardness world (DinkHardnessWorldV1): the
            // story keeps its physics owner per screen, and an owner of the old world left behind by the restart refused the
            // new world's owner on the next visit ("another retained body owner exists"), which held the loading gate and
            // froze Dink for good (CPP_STABILITY_AUDIT.md R1).
            Test->TestTrue(TEXT("SCR_417 is a registered original-hardness screen"), Story->GetGameplay()->RequiresOriginalHardnessScreen(HardnessScreen));
            World->GetSubsystem<UDinkGreyboxSubsystem>()->GotoScreen(HardnessScreen, 300.f, 200.f);
            Phase = 5; PhaseAt = FPlatformTime::Seconds(); return false;
        }
        if (Phase == 4)
        {
            // Dirty persistent state and inventory before actual lethal combat damage.
            Facts->SetFact(TEXT("story"), 17); Facts->SetFact(TEXT("gold"), 777);
            State->SetOverride(FDinkOriginId(438, 3), EDinkOverrideType::RemovedForever);
            State->NotifyScreenExited(438);
            Inventory->AddItem(TEXT("restart-test-item"));
            Test->TestTrue(TEXT("actual damage reaches player brain"), Story->GetGameplay()->HurtThing(1, 1000) > 0);
            Phase = 1; PhaseAt = FPlatformTime::Seconds(); return false;
        }
        if (Phase == 5)
        {
            // OnScreenEntered sets player_map and admits the screen's hardness in the same call.
            if (Facts->GetFact(TEXT("player_map")) != HardnessScreen || FPlatformTime::Seconds() - PhaseAt < 1.0)
            {
                if (FPlatformTime::Seconds() - PhaseAt > 15) { Test->AddError(FString::Printf(TEXT("cycle%d: SCR_%d was never entered"), Cycle, HardnessScreen)); return true; }
                return false;
            }
            Test->TestFalse(FString::Printf(TEXT("cycle%d: the registered hardness screen is admitted (no loading gate)"), Cycle), Story->GetGameplay()->IsHardnessLoading());
            Test->TestTrue(FString::Printf(TEXT("cycle%d: the registered hardness screen is projected"), Cycle), Story->GetGameplay()->UsesOriginalHardnessProjection(HardnessScreen));
            Test->TestFalse(FString::Printf(TEXT("cycle%d: Dink can move on the registered hardness screen"), Cycle), World->GetFirstPlayerController()->IsMoveInputIgnored());
            if (Story->GetGameplay()->IsHardnessLoading()) return true; // frozen for good: no death menu can follow
            Phase = 4; return false;
        }
        if (Phase == 1)
        {
            const FDinkMenu* Menu = Story->GetActiveMenu();
            if (!Menu) return false;
            Test->TestTrue(TEXT("original death menu contains Restart"), Menu->Choices.IsValidIndex(1) && Menu->Choices[1].Text.Contains(TEXT("Restart game")));
            Test->TestTrue(TEXT("real lethal damage left player dead"), Facts->GetFact(TEXT("life")) <= 0);
            Test->TestTrue(TEXT("original death script froze player"), Director->GetDink().bFrozen);
            OldWorld = World; OldPawn = Hero;
            Test->TestTrue(TEXT("choose original Restart option"), Story->Choose(1));
            Phase = 2; PhaseAt = FPlatformTime::Seconds(); return false;
        }
        if (Phase == 2)
        {
            if (World == OldWorld.Get())
            {
                if (FPlatformTime::Seconds() - PhaseAt > 10)
                {
                    Test->AddError(FString::Printf(TEXT("Restart choice did not replace world: life%d frozen%d (the old handler only logged)"), Facts->GetFact(TEXT("life")), Director->GetDink().bFrozen));
                    return true;
                }
                return false;
            }
            Phase = 3;
        }
        return false;
    }
private:
    FAutomationTestBase* Test;
    TWeakObjectPtr<UGameInstance> GI;
    TWeakObjectPtr<UWorld> OldWorld;
    TWeakObjectPtr<AActor> OldPawn;
    FVector InitialPosition = FVector::ZeroVector;
    double Began = 0, PhaseAt = 0;
    int32 Phase = 0, Cycle = 0, InitialStory = 0;
    static constexpr int32 HardnessScreen = 417;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkDeathRestartTest, "Dink.Gameplay.Restart.DeathMenuCreatesFreshPlayableWorldTwice", DINK_TEST_FLAGS)
bool FDinkDeathRestartTest::RunTest(const FString&)
{
    const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("real world map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FRestartFromDeath(this));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
    return true;
}
