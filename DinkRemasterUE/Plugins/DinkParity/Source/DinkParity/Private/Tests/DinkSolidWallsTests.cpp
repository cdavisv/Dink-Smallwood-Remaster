#include "DinkTestHelpers.h"
#include "DinkEarlyPostureAnimInstance.h"
#include "DinkPostureComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "DinkInteriorCameraComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/StaticMeshComponent.h"
#include "Editor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
namespace
{
class FSolidWallsCheck : public IAutomationLatentCommand
{
public:
    explicit FSolidWallsCheck(FAutomationTestBase* T):Test(T) {}
    bool Update() override
    {
        if (!Start) Start=FPlatformTime::Seconds();
        if (FPlatformTime::Seconds()-Start>90) { Test->AddError(TEXT("solid-wall fixture readiness timed out"));return true; }
        UWorld* W=GEditor ? GEditor->PlayWorld.Get() : nullptr;
        auto* PC=W ? W->GetFirstPlayerController() : nullptr;
        auto* H=PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
        auto* S=W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (!H || !S || S->bNewGamePending) return false;
        auto* C=H->FindComponentByClass<UDinkInteriorCameraComponent>();
        auto* G=W->GetSubsystem<UDinkGreyboxSubsystem>();
        if (!Stage)
        {
            S->SkipDialogue(); if (PC->IsMoveInputIgnored()) return false;
            Test->TestFalse(TEXT("normal play never enables whole-wall cutaway"),C->bEnableWallCutaway);
            // Exercise the native policy with the actual pawn/controller/world, without claiming
            // that a not-yet-imported additive graph has evaluated any bones.
            auto* Posture=NewObject<UDinkEarlyPostureAnimInstance>(H->GetMesh());
            Posture->NativeUpdateAnimation(.2f); Posture->NativeUpdateAnimation(.2f);
            Test->TestTrue(TEXT("real early-game pawn builds the timid pose weight"),Posture->PostureWeight>.9f);
            const float BeforePause=Posture->PostureWeight; Posture->NativeUpdateAnimation(0);
            Test->TestEqual(TEXT("zero game delta cannot advance native posture"),Posture->PostureWeight,BeforePause);
            PC->SetIgnoreMoveInput(true); Posture->NativeUpdateAnimation(.2f);
            Test->TestEqual(TEXT("actual controller freeze cancels native posture"),Posture->PostureWeight,0.f);
            PC->SetIgnoreMoveInput(false); Posture->NativeUpdateAnimation(.2f);
            const FTransform BeforeWarp=H->GetActorTransform();
            H->AddActorWorldOffset(FVector(500,0,0),false,nullptr,ETeleportType::TeleportPhysics);
            Posture->NativeUpdateAnimation(.2f);
            Test->TestEqual(TEXT("observed real pawn warp resets native posture"),Posture->PostureWeight,0.f);
            H->SetActorTransform(BeforeWarp,false,nullptr,ETeleportType::TeleportPhysics);
            PC->UnPossess(); Posture->NativeUpdateAnimation(.2f);
            Test->TestEqual(TEXT("unpossessed pawn cannot retain native posture"),Posture->PostureWeight,0.f);
            PC->Possess(H);

            for (TActorIterator<AActor> A(W);A;++A)
            {
                if (!A->ActorHasTag(TEXT("DinkCameraOccluder"))) continue;
                TInlineComponentArray<UStaticMeshComponent*> Components(*A);
                for (auto* M:Components)
                {
                    FBefore B; B.Mesh=M; B.Responses=M->GetCollisionResponseToChannels(); B.Overrides=M->OverrideMaterials;
                    Before.Add(B);
                }
            }
            Test->TestTrue(TEXT("actual architecture fixtures exist"),Before.Num()>10);
            ++Stage;
        }
        // Exercise interior and exterior walls with the camera pointed back through architecture.
        const int32 Screens[]={1,439}; const double Xs[]={370,339}; const double Ys[]={161,320};
        const int32 Index=(Stage-1)/4;
        if (Index>=2) return true;
        auto* Screen=G->FindScreen(Screens[Index]);
        if (!Test->TestNotNull(TEXT("fixture screen exists"),Screen)) return true;
        H->GetCharacterMovement()->StopMovementImmediately();
        H->SetActorLocation(Screen->MapPixelToWorld(Xs[Index],Ys[Index])+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics);
        G->RefreshCurrentScreen(); PC->SetControlRotation(FRotator(-12,(Stage-1)%4*90,0));
        C->TickComponent(.25f,LEVELTICK_All,nullptr);
        Test->TestEqual(TEXT("no architecture managed for disappearance"),C->ManagedOccluderCount,0);
        Test->TestEqual(TEXT("no wall or house becomes transparent"),C->FadingOccluderCount,0);
        Test->TestTrue(TEXT("camera retains physical collision probe"),H->CameraBoom->bDoCollisionTest);
        for (const auto& B:Before)
        {
            Test->TestTrue(TEXT("wall material overrides stay exactly authored"),B.Mesh->OverrideMaterials==B.Overrides);
            Test->TestTrue(TEXT("wall camera/physical collision policy stays authored"),B.Mesh->GetCollisionResponseToChannels()==B.Responses);
            Test->TestFalse(TEXT("wall actor is never hidden"),B.Mesh->GetOwner()->IsHidden());
        }
        ++Stage; return false;
    }
private:
    struct FBefore { UStaticMeshComponent* Mesh=nullptr; FCollisionResponseContainer Responses; TArray<TObjectPtr<UMaterialInterface>> Overrides; };
    TArray<FBefore> Before;
    FAutomationTestBase* Test;
    double Start=0;
    int32 Stage=0;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkSolidWallsTest,"Dink.Art.Camera.WallsRemainSolid",DINK_TEST_FLAGS)
bool FDinkSolidWallsTest::RunTest(const FString&)
{
    const FString File=FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"),FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("actual world loads"),UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    AddCommand(new FStartPIECommand(false)); AddCommand(new FSolidWallsCheck(this)); AddCommand(new FEndPlayMapCommand()); return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkEarlyPostureWeightTest,"Dink.Art.Posture.EarlyMoodWeight",DINK_TEST_FLAGS)
bool FDinkEarlyPostureWeightTest::RunTest(const FString&)
{
    TestEqual(TEXT("early Dink gets full authored timid pose"),UDinkEarlyPostureAnimInstance::TargetWeight(0,true,false,false),1.f);
    TestEqual(TEXT("later progression relaxes the posture"),UDinkEarlyPostureAnimInstance::TargetWeight(7,true,false,false),.3f);
    TestEqual(TEXT("attack reduces head/shoulder additive"),UDinkEarlyPostureAnimInstance::TargetWeight(0,true,true,false),.35f);
    TestEqual(TEXT("airborne additive is reduced"),UDinkEarlyPostureAnimInstance::TargetWeight(0,true,false,true),.5f);
    TestEqual(TEXT("frozen or dead Dink cannot retain transient posture"),UDinkEarlyPostureAnimInstance::TargetWeight(0,false,false,false),0.f);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPostureOwnershipTest,"Dink.Art.Posture.OverrideOwnership",DINK_TEST_FLAGS)
bool FDinkPostureOwnershipTest::RunTest(const FString&)
{
    USkeletalMeshComponent* Mesh=NewObject<USkeletalMeshComponent>();
    UDinkPostureComponent* Owner=NewObject<UDinkPostureComponent>();
    TSubclassOf<UAnimInstance> Current;
    const auto PoseClass=UDinkEarlyPostureAnimInstance::StaticClass();
    const auto PriorClass=UAnimSingleNodeInstance::StaticClass();
    const auto ForeignClass=UAnimInstance::StaticClass();
    Mesh->SetOverridePostProcessAnimBP(PriorClass);
    TestTrue(TEXT("managed pose can replace a previous override"),Owner->Configure(Mesh,PoseClass));
    Owner->Release(); UDinkPostureComponent::ReadOverride(Mesh,Current);
    TestTrue(TEXT("removing optional pose restores exact previous raw override"),Current==PriorClass);
    Mesh->SetOverridePostProcessAnimBP(nullptr); Owner->Configure(Mesh,PoseClass);
    Owner->Configure(Mesh,nullptr); UDinkPostureComponent::ReadOverride(Mesh,Current);
    TestTrue(TEXT("missing or invalid pose restores null raw override"),!Current);
    Owner->Configure(Mesh,PoseClass); Mesh->SetOverridePostProcessAnimBP(ForeignClass);
    TestFalse(TEXT("reapplying owned pose cannot overwrite a foreign replacement"),Owner->Configure(Mesh,PoseClass));
    Owner->Release(); UDinkPostureComponent::ReadOverride(Mesh,Current);
    TestTrue(TEXT("release preserves foreign replacement"),Current==ForeignClass);
    Owner->Configure(Mesh,PoseClass); Mesh->SetOverridePostProcessAnimBP(ForeignClass);
    Owner->Configure(Mesh,PoseClass); // observe ownership loss
    Mesh->SetOverridePostProcessAnimBP(PoseClass); // another system deliberately selects the same class
    Owner->Release(); UDinkPostureComponent::ReadOverride(Mesh,Current);
    TestTrue(TEXT("observed ownership loss stays released even if external code selects the old managed class"),Current==PoseClass);
    Mesh->SetOverridePostProcessAnimBP(ForeignClass);
    Owner->Configure(Mesh,PoseClass);
    USkeletalMeshComponent* Other=NewObject<USkeletalMeshComponent>();
    Owner->Configure(Other,PoseClass); UDinkPostureComponent::ReadOverride(Mesh,Current);
    TestTrue(TEXT("retargeting restores the previous mesh independently"),Current==ForeignClass);
    Owner->Release(); UDinkPostureComponent::ReadOverride(Other,Current);
    TestTrue(TEXT("retargeted mesh restores its own original override"),!Current);
    return true;
}
