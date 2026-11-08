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
        if (FPlatformTime::Seconds() - Began > 90)
        {
            if (PC) PC->SetPause(false);
            if (World && Stage) World->GetWorldSettings()->SetTimeDilation(OriginalDilation);
            Test->AddError(TEXT("player action PIE readiness timed out")); return true;
        }
        if (!Hero || !Story || Story->bNewGamePending) return false;
        FAssetCompilingManager::Get().FinishAllCompilation();
        USkeletalMeshComponent* Mesh = Hero->GetMesh();
        UDinkPlayerActionComponent* Action = Hero->FindComponentByClass<UDinkPlayerActionComponent>();
        if (!Test->TestNotNull(TEXT("reviewed optional player action configured at startup"), Action)) return true;
        UDinkArtSubsystem* Art = World->GetSubsystem<UDinkArtSubsystem>();
        if (Stage == 0)
        {
            OriginalDilation = World->GetWorldSettings()->TimeDilation;
            Test->TestTrue(TEXT("real reviewed sequence starts cosmetic action"), Art->PlayPlayerSequence(Hero, 104));
            WorldStart = World->GetTimeSeconds();
            World->GetWorldSettings()->SetTimeDilation(.25f);
            Stage = 1; return false;
        }
        if (Stage == 1)
        {
            Test->TestTrue(TEXT("action elapsed follows actual dilated game time"), FMath::IsNearlyEqual(Action->GetElapsedSeconds(), World->GetTimeSeconds() - WorldStart, .001));
            PausedElapsed = Action->GetElapsedSeconds();
            Test->TestTrue(TEXT("real PIE pause accepted"), PC->SetPause(true));
            Stage = 2; return false;
        }
        PC->SetPause(false);
        World->GetWorldSettings()->SetTimeDilation(OriginalDilation);
        Test->TestTrue(TEXT("real paused world cannot advance cosmetic action"), FMath::IsNearlyEqual(Action->GetElapsedSeconds(), PausedElapsed, .00001));
        Action->Cancel();
        UClass* BaseClass = Mesh->GetAnimClass();
        const FTransform ActorBefore = Hero->GetActorTransform();
        const float RadiusBefore = Hero->GetCapsuleComponent()->GetScaledCapsuleRadius();
        UDinkDirector* D = Story->GetDirector();
        const bool FrozenBefore = D->GetDink().bFrozen;
        for (const int32 Seq : {102, 104, 106, 108})
        {
            Test->TestTrue(TEXT("each reviewed original sequence is whitelisted"), Art->PlayPlayerSequence(Hero, Seq));
            Test->TestTrue(TEXT("temporary SingleNode displays imported fist"), Mesh->GetAnimationMode() == EAnimationMode::AnimationSingleNode && Mesh->GetSingleNodeInstance());
            Test->TestEqual(TEXT("correct reviewed sequence retained"), Action->GetActiveSequence(), Seq);
            Action->TickComponent(.1f, LEVELTICK_All, nullptr);
            Test->TestTrue(TEXT("SingleNode pose and one game clock agree"), FMath::IsNearlyEqual(Mesh->GetSingleNodeInstance()->GetCurrentTime(), .1f, .0001f));
            Test->TestTrue(TEXT("same original seq can restart reviewed action"), Art->PlayPlayerSequence(Hero, Seq));
            Test->TestEqual(TEXT("same-sequence restart starts at zero elapsed"), Action->GetElapsedSeconds(), 0.);
            Action->TickComponent(.401f, LEVELTICK_All, nullptr);
            Test->TestFalse(TEXT("one shot ends at reviewed duration"), Action->IsActionActive());
            Test->TestTrue(TEXT("completion restores original locomotion AnimBP class"), Mesh->GetAnimationMode() == EAnimationMode::AnimationBlueprint && Mesh->GetAnimClass() == BaseClass);
        }
        Art->PlayPlayerSequence(Hero, 106);
        Test->TestFalse(TEXT("unreviewed sword sequence cannot play fist"), Art->PlayPlayerSequence(Hero, 112));
        Test->TestTrue(TEXT("replacement cancels overlay and restores locomotion"), !Action->IsActionActive() && Mesh->GetAnimClass() == BaseClass);
        Art->PlayPlayerSequence(Hero, 104);
        Mesh->SetAnimInstanceClass(BaseClass);
        Action->TickComponent(.01f, LEVELTICK_All, nullptr);
        Test->TestTrue(TEXT("external replacement remains intact"), !Action->IsActionActive() && Mesh->GetAnimationMode() == EAnimationMode::AnimationBlueprint && Mesh->GetAnimClass() == BaseClass);
        Art->PlayPlayerSequence(Hero, 106);
        Hero->AddActorWorldOffset(FVector(0, 0, 250));
        Action->TickComponent(.01f, LEVELTICK_All, nullptr);
        Test->TestFalse(TEXT("teleport cancels transient cosmetic action"), Action->IsActionActive());
        Hero->SetActorTransform(ActorBefore, false, nullptr, ETeleportType::TeleportPhysics);
        Test->TestTrue(TEXT("cosmetic playback never changes actor transform"), Hero->GetActorTransform().Equals(ActorBefore, .001));
        Test->TestEqual(TEXT("cosmetic playback never changes capsule"), Hero->GetCapsuleComponent()->GetScaledCapsuleRadius(), RadiusBefore);
        Test->TestEqual(TEXT("cosmetic playback never writes frozen state"), D->GetDink().bFrozen, FrozenBefore);

        // The real original pending-hit scheduler owns175ms damage across save/load.
        Story->bRunScreenScripts = false;
        UDinkGameplay* Game = Story->GetGameplay();
        Game->bBrainsEnabled = false;
        Game->SetRandomSeed(1997);
        Story->GetFacts()->SetFact(TEXT("strength"), 4);
        ADinkScreenVolume* Home = World->GetSubsystem<UDinkGreyboxSubsystem>()->FindScreen(1);
        Hero->SetActorLocation(Home->MapPixelToWorld(370, 161) + FVector(0, 0, 98), false, nullptr, ETeleportType::TeleportPhysics);
        Hero->SetActorRotation(FRotator::ZeroRotator);
        D->GetDink().Screen = 1; D->SyncSpriteFromActor(D->GetDink()); D->GetDink().Dir = 6;
        const int32 TargetHandle = D->CreateVirtualSprite(1, D->GetDink().X + 20, D->GetDink().Y);
        FDinkSprite* Target = D->FindSprite(TargetHandle);
        Target->Props.Add(TEXT("brain"), 9); Target->Props.Add(TEXT("hitpoints"), 100);
        Target->Props.Add(TEXT("defense"), 0); Target->Props.Add(TEXT("touch_damage"), 0);
        Target->Props.Add(TEXT("pseq"), 131); Target->Props.Add(TEXT("pframe"), 1);
        UDinkSaveSubsystem* Saves = World->GetGameInstance()->GetSubsystem<UDinkSaveSubsystem>();
        UDinkSaveGame* IdleSave = Saves->CaptureSnapshot(Hero, 1);
        Test->TestEqual(TEXT("authoritative reviewed fist hit delay remains175ms"), Game->GetData().HitFrameDelayMs(106), 175);
        D->SpriteProperty(nullptr, TEXT("seq"), 1, 106);
        Test->TestTrue(TEXT("original sequence assignment triggers reviewed visual"), Action->IsActionActive() && Action->GetActiveSequence() == 106);
        Story->Tick(.174f); Action->TickComponent(.174f, LEVELTICK_All, nullptr);
        Test->TestEqual(TEXT("no damage before original175ms"), D->FindSprite(TargetHandle)->GetProp(TEXT("hitpoints")), 100);
        const double BeforeCapture = Story->GetNowMs();
        UDinkSaveGame* MidSave = Saves->CaptureSnapshot(Hero, 1);
        Test->TestEqual(TEXT("save capture cannot advance authoritative time"), Story->GetNowMs(), BeforeCapture);
        Test->TestTrue(TEXT("optional save captures transient cosmetic progress"), MidSave->SubsystemState.Contains(TEXT("player_action")));
        Story->Tick(.05f); Action->TickComponent(.05f, LEVELTICK_All, nullptr);
        const int32 DamagedHP = D->FindSprite(TargetHandle)->GetProp(TEXT("hitpoints"));
        Test->TestTrue(TEXT("real original scheduler applies one pending hit"), DamagedHP < 100);
        Test->TestTrue(TEXT("mid-action snapshot applies"), Saves->ApplySnapshot(MidSave, Hero));
        Test->TestEqual(TEXT("authoritative target restores before hit"), D->FindSprite(TargetHandle)->GetProp(TEXT("hitpoints")), 100);
        Test->TestTrue(TEXT("cosmetic restore resumes saved174ms directly"), Action->IsActionActive() && FMath::IsNearlyEqual(Action->GetElapsedSeconds(), .174, .0001));
        Test->TestEqual(TEXT("cosmetic restore never reschedules pending hit"), Game->SaveState()->GetArrayField(TEXT("pendingHits")).Num(), 1);
        Story->Tick(.0005f); Action->TickComponent(.0005f, LEVELTICK_All, nullptr);
        Test->TestEqual(TEXT("restored hit still waits until175ms"), D->FindSprite(TargetHandle)->GetProp(TEXT("hitpoints")), 100);
        Story->Tick(.0006f); Action->TickComponent(.0006f, LEVELTICK_All, nullptr);
        Test->TestEqual(TEXT("restored original hit lands once at175ms"), D->FindSprite(TargetHandle)->GetProp(TEXT("hitpoints")), DamagedHP);
        Story->Tick(.01f); Action->TickComponent(.225f, LEVELTICK_All, nullptr);
        Test->TestEqual(TEXT("cosmetic completion cannot create another hit"), D->FindSprite(TargetHandle)->GetProp(TEXT("hitpoints")), DamagedHP);
        Test->TestTrue(TEXT("loaded action completion restores original AnimBP"), !Action->IsActionActive() && Mesh->GetAnimClass() == BaseClass);
        Art->PlayPlayerSequence(Hero, 106);
        Test->TestTrue(TEXT("legacy idle save applies"), Saves->ApplySnapshot(IdleSave, Hero));
        Test->TestTrue(TEXT("load without action state cancels discarded overlay"), !Action->IsActionActive() && Mesh->GetAnimationMode() == EAnimationMode::AnimationBlueprint && Mesh->GetAnimClass() == BaseClass);
        return true;
    }
private:
    FAutomationTestBase* Test;
    double Began = 0, WorldStart = 0, PausedElapsed = 0;
    float OriginalDilation = 1;
    int32 Stage = 0;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPlayerActionTest,
    "Dink.Art.PlayerAction.ApprovedFistTimingSaveAndLocomotion", DINK_TEST_FLAGS)
bool FDinkPlayerActionTest::RunTest(const FString&)
{
    if (!IFileManager::Get().FileExists(*(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/hero_actions.json"))))
    { AddWarning(TEXT("skipped: reviewed hero action manifest absent")); return true; }
    const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook"), FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("real player map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkPlayerActionCheck(this));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
    return true;
}
