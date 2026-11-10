#include "DinkTestHelpers.h"
#include "DinkCameraHeadroom.h"
#include "DinkInteriorCameraComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Editor.h"
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "Misc/PackageName.h"
#include "SceneView.h"
#include "Tests/AutomationEditorCommon.h"
#include "UnrealClient.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkOutdoorHeadroomMath,"Dink.Art.Camera.OutdoorHeadroomGeometry",DINK_TEST_FLAGS)
bool FDinkOutdoorHeadroomMath::RunTest(const FString&)
{
    // Measured actual doorway arrival: 106.18594cm against the cottage, yaw89.4271/pitch-18.
    const FVector Pawn(97729.1303395717,37510.18435747431,98.3499956131);
    const FVector Eye(97728.12056988107,37409.20056726398,131.1632583712);
    const FRotator R(-18,89.4271,0); const FVector F=R.Vector(),U=R.RotateVector(FVector::UpVector);
    const FVector Top=Pawn+FVector(0,0,96); double Lift=0;
    const auto NDC=[&](double Z,double Scale) { const FVector D=Top-Eye-FVector(0,0,Z);return FVector::DotProduct(D,U)*Scale/FVector::DotProduct(D,F); };
    const double Y=1280./720.; // Actual horizontal90-degree FOV at16:9.
    TestTrue(TEXT("measured baseline clips capsule top"),NDC(0,Y)>1);
    TestTrue(TEXT("measured doorway has bounded analytic solution"),DinkCameraHeadroom::MinimumLift(Top,Eye,F,U,Y,0,.2,96,Lift));
    TestTrue(TEXT("lift is derived rather than a fixed80cm preset"),Lift>0 && Lift<80);
    TestTrue(TEXT("independent projection reaches requested headroom"),FMath::IsNearlyEqual(NDC(Lift,Y),.8,1.e-6));
    TestTrue(TEXT("smaller lift fails requested upper-frustum margin"),NDC(Lift-.01,Y)>.8);
    TestTrue(TEXT("clear outdoor400cm camera needs no lift"),DinkCameraHeadroom::MinimumLift(Top,Pawn-F*400,F,U,Y,0,.2,96,Lift) && Lift==0);
    TestFalse(TEXT("infeasible small height bound is not silently clamped"),DinkCameraHeadroom::MinimumLift(Top,Eye,F,U,Y,0,.2,10,Lift));
    TestEqual(TEXT("infeasible result clears prior lift"),Lift,0.);
    double Portrait=0,Wide=0;
    TestTrue(TEXT("vertical projection follows actual aspect/FOV"),DinkCameraHeadroom::MinimumLift(Top,Eye,F,U,1.,0,.2,96,Portrait) && DinkCameraHeadroom::MinimumLift(Top,Eye,F,U,2.,0,.2,96,Wide) && Wide>Portrait);
    TestFalse(TEXT("invalid projection fails closed"),DinkCameraHeadroom::MinimumLift(Top,Eye,F,U,0,0,.2,96,Lift));
    TestFalse(TEXT("nonfinite geometry fails closed"),DinkCameraHeadroom::MinimumLift(Top,FVector(std::numeric_limits<double>::infinity(),0,0),F,U,Y,0,.2,96,Lift));
    TestFalse(TEXT("point behind camera is not used as headroom solution"),DinkCameraHeadroom::MinimumLift(Eye-F*10,Eye,F,U,Y,0,.2,96,Lift));
    const FVector Impact(97735.00820751951,37399.37406384766,131.1559143066);
    const FVector Normal(-.02659731172,.99964570999,.00098703173);
    const double FaceClearance=FVector::DotProduct(Eye-Impact,Normal);
    TestTrue(TEXT("recorded valid12cm sphere edge contact has only10cm face clearance"),FaceClearance>9.9 && FaceClearance<10.1);
    TestTrue(TEXT("recordedcorner vertical lift stays exterior despite clearance below radius"),DinkCameraHeadroom::PreservesExteriorFace(Eye,Eye+FVector(0,0,60),Impact,Normal));
    TestFalse(TEXT("candidate crossing the original wall face is refused"),DinkCameraHeadroom::PreservesExteriorFace(Eye,Impact-Normal,Impact,Normal));
    TestFalse(TEXT("candidate materially losing baseline face clearance is refused"),DinkCameraHeadroom::PreservesExteriorFace(Eye,Eye-Normal*2,Impact,Normal));
    return true;
}

namespace
{
class FOutdoorDoorHeadroomCheck : public IAutomationLatentCommand
{
public:
    explicit FOutdoorDoorHeadroomCheck(FAutomationTestBase* In):Test(In) {}
    bool Update() override
    {
        if (!Started) Started=FPlatformTime::Seconds();
        UWorld* W=GEditor ? GEditor->PlayWorld.Get() : nullptr;
        auto* PC=W ? W->GetFirstPlayerController() : nullptr;
        auto* H=PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
        auto* Story=W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        auto* G=W ? W->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
        if (FPlatformTime::Seconds()-Started>90) { Test->AddError(TEXT("outdoor headroom fixture readiness timed out"));if (bGuard && G && H) G->EndWarp(H);return true; }
        if (!H || !Story || Story->bNewGamePending || !G) return false;
        auto* C=H->FindComponentByClass<UDinkInteriorCameraComponent>();
        if (!Stage)
        {
            Story->SkipDialogue();if (PC->IsMoveInputIgnored()) return false;
            auto* Local=PC->GetLocalPlayer();auto* V=Local && Local->ViewportClient ? Local->ViewportClient->Viewport : nullptr;
            if (!Test->TestNotNull(TEXT("actual local viewport"),V) || !Test->TestNotNull(TEXT("actual headroom component"),C)) return true;
            if (V->GetSizeXY()==FIntPoint::ZeroValue) V->SetInitialSize(FIntPoint(1280,720));
            bGuard=G->BeginWarp(H);if (!Test->TestTrue(TEXT("scoped static camera inspection prevents fixture teleport firing a warp"),bGuard)) return true;
            CapsuleResponses=H->GetCapsuleComponent()->GetCollisionResponseToChannels();Input=H->InputComponent;
            H->GetCharacterMovement()->StopMovementImmediately();
            H->SetActorLocation(FVector(97729.1303395717,37510.18435747431,98.3499956131),false,nullptr,ETeleportType::TeleportPhysics);
            G->RefreshCurrentScreen();PC->SetControlRotation(FRotator(-18,89.4271,0));At=FPlatformTime::Seconds();Stage=1;return false;
        }
        if (FPlatformTime::Seconds()-At<.5) return false;
        USpringArmComponent* Arm=H->CameraBoom;UCameraComponent* Cam=H->FollowCamera;
        if (Stage==1)
        {
            Test->TestFalse(TEXT("actual doorway arrival is outdoors"),C->bInteriorMode);
            const FRotator R=Arm->GetTargetRotation();const FVector Base=Arm->GetComponentLocation();
            const FVector Desired=Base-R.Vector()*Arm->TargetArmLength+R.RotateVector(Arm->SocketOffset);
            FCollisionQueryParams Params(SCENE_QUERY_STAT(OutdoorDoorHeadroomTest),false,H);FHitResult Before,After;
            const auto Sphere=FCollisionShape::MakeSphere(Arm->ProbeSize);
            Test->TestTrue(TEXT("unadjusted actual cottage retracts camera"),W->SweepSingleByChannel(Before,Base,Desired,FQuat::Identity,Arm->ProbeChannel,Sphere,Params));
            auto* Blocker=Cast<UStaticMeshComponent>(Before.GetComponent());
            if (Test->TestNotNull(TEXT("baseline blocker is an actual static mesh"),Blocker))
                Test->TestTrue(TEXT("fixture reproduces actual cottage blocker"),Blocker->GetStaticMesh() && Blocker->GetStaticMesh()->GetName()==TEXT("SM_Cottage_Stonebrook_01"));
            Test->TestTrue(TEXT("fixture retains measured close-retraction regime"),Before.Distance>70 && Before.Distance<140);
            Test->TestTrue(TEXT("adaptive lift bounded by capsule height"),C->OutdoorHeadroomLift>0 && C->OutdoorHeadroomLift<=H->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
            Test->TestTrue(TEXT("no lateral offset workaround"),FMath::IsNearlyZero(Arm->TargetOffset.X) && FMath::IsNearlyZero(Arm->TargetOffset.Y));
            const FVector Lift(0,0,C->OutdoorHeadroomLift);
            Test->TestTrue(TEXT("raised camera still respects same wall"),W->SweepSingleByChannel(After,Base+Lift,Desired+Lift,FQuat::Identity,Arm->ProbeChannel,Sphere,Params) && After.GetComponent()==Before.GetComponent());
            Test->TestTrue(TEXT("actual camera equals collision sweep result"),Cam->GetComponentLocation().Equals(After.Location,1.));
            Test->TestTrue(TEXT("camera stays outside original wall face"),FVector::DotProduct(Cam->GetComponentLocation()-Before.ImpactPoint,Before.ImpactNormal)>0 && FVector::DotProduct(Cam->GetComponentLocation()-Before.ImpactPoint,Before.ImpactNormal)+.5>=FVector::DotProduct(Before.Location-Before.ImpactPoint,Before.ImpactNormal));
            FVector2D Pixel;Test->TestTrue(TEXT("actual capsule top projects"),PC->ProjectWorldLocationToScreen(H->GetCapsuleComponent()->GetComponentLocation()+FVector(0,0,H->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),Pixel));
            int32 Width=0,Height=0;PC->GetViewportSize(Width,Height);Test->TestTrue(TEXT("capsule top retains upper screen margin"),Pixel.Y>=Height*.09 && Pixel.Y<=Height);
            Test->TestTrue(TEXT("physical capsule policy unchanged"),H->GetCapsuleComponent()->GetCollisionResponseToChannels()==CapsuleResponses);
            Test->TestTrue(TEXT("input component unchanged"),H->InputComponent==Input);
            Test->TestFalse(TEXT("camera fix does not freeze movement"),PC->IsMoveInputIgnored());
            Test->TestEqual(TEXT("desired outdoor arm remains400"),Arm->TargetArmLength,400.f);
            PC->UnPossess();C->TickComponent(.1f,LEVELTICK_All,nullptr);
            Test->TestEqual(TEXT("ownership loss clears outdoor lift"),C->OutdoorHeadroomLift,0.f);
            Test->TestTrue(TEXT("ownership loss restores original pivot"),Arm->TargetOffset.IsNearlyZero());PC->Possess(H);
            H->GetCharacterMovement()->SetMovementMode(MOVE_Flying);H->SetActorLocation(H->GetActorLocation()+FVector(0,0,10000),false,nullptr,ETeleportType::TeleportPhysics);G->RefreshCurrentScreen();At=FPlatformTime::Seconds();Stage=2;return false;
        }
        Test->TestEqual(TEXT("unobstructed outdoor control clears lift"),C->OutdoorHeadroomLift,0.f);
        Test->TestTrue(TEXT("unobstructed outdoor pivot remains default"),Arm->TargetOffset.IsNearlyZero());
        Test->TestEqual(TEXT("unobstructed outdoor desired distance remains400"),Arm->TargetArmLength,400.f);
        G->EndWarp(H);return true;
    }
private:
    FAutomationTestBase* Test;double Started=0,At=0;int32 Stage=0;bool bGuard=false;
    UInputComponent* Input=nullptr;FCollisionResponseContainer CapsuleResponses;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkOutdoorDoorHeadroom,"Dink.Art.Camera.OutdoorDoorHeadroom",DINK_TEST_FLAGS)
bool FDinkOutdoorDoorHeadroom::RunTest(const FString&)
{
    const auto File=FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"),FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("actual world loads"),UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    AddCommand(new FStartPIECommand(false));AddCommand(new FOutdoorDoorHeadroomCheck(this));AddCommand(new FEndPlayMapCommand());return true;
}
