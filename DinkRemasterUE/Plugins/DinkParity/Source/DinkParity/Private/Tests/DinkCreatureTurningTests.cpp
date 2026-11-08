#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Components/BoxComponent.h"
#include "Editor.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
class FDinkPillbugPondTurnCheck : public IAutomationLatentCommand
{
public:
    explicit FDinkPillbugPondTurnCheck(FAutomationTestBase* InTest) : Test(InTest) {}
    bool Update() override
    {
        if (!Began) Began = FPlatformTime::Seconds();
        if (FPlatformTime::Seconds() - Began > 90) { Test->AddError(TEXT("pond turn real PIE readiness timed out")); return true; }
        UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
        APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
        APawn* Hero = PC ? PC->GetPawn() : nullptr;
        UDinkStorySubsystem* Story = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (!Hero || !Story || Story->bNewGamePending) return false;
        FAssetCompilingManager::Get().FinishAllCompilation();
        UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
        ADinkScreenVolume* Screen = Greybox->FindScreen(438);
        ADinkPlaceholderActor* Bug = nullptr;
        for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It) if (It->Origin->OriginId == FDinkOriginId(438, 3)) Bug = *It;
        if (!Test->TestNotNull(TEXT("actual SCR438 volume loaded"), Screen) || !Test->TestNotNull(TEXT("actual S438_P03 loaded"), Bug)) return true;
        TInlineComponentArray<UBoxComponent*> Components(Bug);
        TArray<UBoxComponent*> Bodies;
        for (UBoxComponent* Body : Components) if (Body->ComponentHasTag(TEXT("DinkAuthoredInteraction"))) Bodies.Add(Body);
        if (!Test->TestTrue(TEXT("actual imported compound body available"), Bodies.Num() >= 2)) return true;
        Story->bRunScreenScripts = false;
        UDinkDirector* D = Story->GetDirector();
        UDinkGameplay* Game = Story->GetGameplay();
        const int32 Handle = D->HandleForActor(Bug);
        Hero->SetActorLocation(Screen->MapPixelToWorld(300, 110) + FVector(0, 0, 98), false, nullptr, ETeleportType::TeleportPhysics);
        D->GetDink().Screen = 438; D->SyncSpriteFromActor(D->GetDink());
        const FCollisionQueryParams Params(TEXT("PillbugActualCommittedBody"), true, Bug);
        auto Overlap = [&]()
        {
            for (UBoxComponent* Body : Bodies)
                if (World->OverlapBlockingTestByChannel(Body->GetComponentLocation(), Body->GetComponentQuat(), ECC_Pawn,
                    FCollisionShape::MakeBox(Body->GetScaledBoxExtent()), Params)) return true;
            return false;
        };
        FQuat OldFacing;
        auto Reset = [&](int32 Dir, int32 Mx, int32 My, double Y = 202)
        {
            FDinkSprite* S = D->FindSprite(Handle);
            S->Actor = Bug; S->Screen = 438; S->X = 369; S->Y = Y;
            S->bActive = true; S->bMoving = false; S->bFrozen = false;
            S->bWindingUp = false; S->MoveWaitMs = 1000000000.;
            S->Props.Add(TEXT("brain"), 9); S->Props.Add(TEXT("speed"), 1);
            S->Props.Add(TEXT("timing"), 0); S->Props.Add(TEXT("target"), 1);
            S->Props.Add(TEXT("base_walk"), 130); S->Props.Add(TEXT("base_attack"), -1);
            S->Props.Add(TEXT("move_nohard"), 0);
            S->Dir = 3; D->GetSpriteFacingRotation(*S, OldFacing);
            Bug->SetActorLocation(Screen->MapPixelToWorld(349, Y));
            Bug->SetActorRotation(OldFacing);
            // A pending original walk_normal step between target re-aims; logical direction
            // may already differ from the safe physical facing after a blocked turn.
            S->Dir = Dir; S->Props.Add(TEXT("mx"), Mx); S->Props.Add(TEXT("my"), My);
            S->Props.Add(TEXT("seq"), 130 + Dir); S->Props.Add(TEXT("frame"), 1);
            S->FrameDelayMs = 1000000000.;
        };
        Reset(7, -1, -1);
        Test->TestFalse(TEXT("measured P03 startpose clear of pond bank"), Overlap());
        Game->ThinkSprite(Handle, 1000.);
        Test->TestEqual(TEXT("first actual NW step preserves original X movement"), D->FindSprite(Handle)->X, 368.);
        Test->TestEqual(TEXT("first actual NW step preserves original Y movement"), D->FindSprite(Handle)->Y, 201.);
        Test->TestTrue(TEXT("first NW step defers unsafe turn at physical body"), Bug->GetActorQuat().AngularDistance(OldFacing) < .001);
        Test->TestFalse(TEXT("first NW committed actual body does not penetrate"), Overlap());
        Test->TestEqual(TEXT("first step retains original logical NW direction"), D->FindSprite(Handle)->Dir, 7);
        Test->TestEqual(TEXT("first step retains actual hero target"), D->FindSprite(Handle)->GetProp(TEXT("target")), 1);
        const FVector DeferredPosition = Bug->GetActorLocation();
        const TSharedPtr<FJsonObject> DeferredSaved = D->SaveState();
        Bug->SetActorLocation(Screen->MapPixelToWorld(360, 190));
        Bug->SetActorRotation(FRotator(0, -134.43, 0));
        D->LoadState(DeferredSaved);
        Test->TestTrue(TEXT("save restores exact first-deferred-step physical XY"), Bug->GetActorLocation().Equals(DeferredPosition, .01));
        Test->TestTrue(TEXT("save restores safe old physical facing not logical NW"), Bug->GetActorQuat().AngularDistance(OldFacing) < .001);
        Test->TestFalse(TEXT("restored deferred body has no new bank penetration"), Overlap());
        Test->TestEqual(TEXT("save preserves deferred logical NW direction"), D->FindSprite(Handle)->Dir, 7);
        Test->TestEqual(TEXT("save preserves actual hero target"), D->FindSprite(Handle)->GetProp(TEXT("target")), 1);
        // Old module JSON has no presentation quaternion. It must remain accepted without
        // forcing a deferred logical direction into the already safe physical body.
        for (const auto& Value : DeferredSaved->GetArrayField(TEXT("sprites")))
            Value->AsObject()->RemoveField(TEXT("authoredFacing"));
        D->LoadState(DeferredSaved);
        Test->TestTrue(TEXT("legacy JSON without optional facing retains safe current pose"), Bug->GetActorQuat().AngularDistance(OldFacing) < .001 && !Overlap());
        Test->TestEqual(TEXT("legacy JSON retains logical NW metadata"), D->FindSprite(Handle)->Dir, 7);
        Game->ThinkSprite(Handle, 1017.);
        Test->TestEqual(TEXT("second NW step advances original X"), D->FindSprite(Handle)->X, 367.);
        Test->TestEqual(TEXT("second NW step advances original Y"), D->FindSprite(Handle)->Y, 200.);
        FQuat Wanted; D->GetSpriteFacingRotation(*D->FindSprite(Handle), Wanted);
        Test->TestTrue(TEXT("second NW step commits desired facing after clearance"), Bug->GetActorQuat().AngularDistance(Wanted) < .001);
        Test->TestFalse(TEXT("second NW actual body does not penetrate"), Overlap());

        Reset(8, 0, -1);
        Game->ThinkSprite(Handle, 1100.);
        Test->TestEqual(TEXT("north-only step escapes in one original pixel"), D->FindSprite(Handle)->Y, 201.);
        D->GetSpriteFacingRotation(*D->FindSprite(Handle), Wanted);
        Test->TestTrue(TEXT("north step turns at its clear endpoint"), Bug->GetActorQuat().AngularDistance(Wanted) < .001);
        Test->TestFalse(TEXT("north actual final body is clear"), Overlap());

        Reset(3, 1, 1);
        const FVector Before = Bug->GetActorLocation();
        Game->ThinkSprite(Handle, 1200.);
        Test->TestTrue(TEXT("current-facing bank collision still rejects movement"), Bug->GetActorLocation().Equals(Before, .01));
        Test->TestFalse(TEXT("rejected bank step leaves actual body clear"), Overlap());

        Reset(3, 1, 1);
        D->FindSprite(Handle)->Props.Add(TEXT("move_nohard"), 1);
        Game->ThinkSprite(Handle, 1300.);
        Test->TestEqual(TEXT("explicit nohard retains original movement override"), D->FindSprite(Handle)->Y, 203.);

        Reset(3, 1, 1);
        D->FindSprite(Handle)->Actor.Reset();
        Game->ThinkSprite(Handle, 1400.);
        Test->TestEqual(TEXT("virtual classic sprite still follows free center pixel"), D->FindSprite(Handle)->Y, 203.);

        Reset(8, 0, -1, 203);
        Test->TestTrue(TEXT("old-save escape fixture genuinely starts overlapping"), Overlap());
        for (int32 Step = 0; Step < 3; ++Step) Game->ThinkSprite(Handle, 1500. + Step * 17.);
        Test->TestTrue(TEXT("separate old-save escape still moves away from bank"), D->FindSprite(Handle)->Y < 203);
        Test->TestFalse(TEXT("old-save escape reaches clear actual body"), Overlap());
        return true;
    }
private:
    FAutomationTestBase* Test;
    double Began = 0;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPillbugPondTurnTest,
    "Dink.Gameplay.AuthoredGeometry.PillbugEscapesPondTurnAtActualPose", DINK_TEST_FLAGS)
bool FDinkPillbugPondTurnTest::RunTest(const FString&)
{
    const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
    if (!IFileManager::Get().FileExists(*File)) { AddWarning(TEXT("skipped: generated world absent")); return true; }
    if (!TestNotNull(TEXT("actual field world loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkPillbugPondTurnCheck(this));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
    return true;
}
