#include "DinkTestHelpers.h"
#include "DinkArtSubsystem.h"
#include "DinkInteriorCameraComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "Engine/LocalPlayer.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Misc/ScopeExit.h"
#include "Dom/JsonObject.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
#include "UnrealClient.h"

struct FDinkExteriorPortalTestAccess
{
    static TArray<FDinkExteriorCameraRule>& Rules(UDinkArtSubsystem& Art){return Art.ExteriorCameraRules;}
    static void Register(UDinkArtSubsystem& Art,const FString& File,const TSharedPtr<FJsonObject>& Row,int32 Screen,UStaticMeshComponent* Mesh)
    {Art.RegisterExteriorCameraRule(File,Row,Screen,Mesh);}
    static const FDinkExteriorCameraRule* Actual(UDinkArtSubsystem& Art)
    {
        const FDinkExteriorCameraRule* Result=nullptr;
        for(const auto& R:Art.ExteriorCameraRules)
            if(R.Manifest==TEXT("stonebrook_exterior.json")&&R.Element==TEXT("DinksCottage")&&R.Screen==439&&R.Component.IsValid())
            {if(Result)return nullptr;Result=&R;}
        return Result;
    }
};
namespace
{
class FOutdoorPortalCheck : public IAutomationLatentCommand
{
public:
    explicit FOutdoorPortalCheck(FAutomationTestBase* In):Test(In){}
    bool Update() override
    {
        if(!Started)Started=FPlatformTime::Seconds();
        UWorld* W=GEditor?GEditor->PlayWorld.Get():nullptr;
        auto* PC=W?W->GetFirstPlayerController():nullptr;
        auto* H=PC?Cast<ADinkGreyboxCharacter>(PC->GetPawn()):nullptr;
        auto* Story=W&&W->GetGameInstance()?W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>():nullptr;
        auto* Grey=W?W->GetSubsystem<UDinkGreyboxSubsystem>():nullptr;
        if(FPlatformTime::Seconds()-Started>90)
        {Test->AddError(TEXT("portal fixture readiness timed out"));if(Guard&&Grey&&H)Grey->EndWarp(H);return true;}
        if(!H||!Story||Story->bNewGamePending||!Grey)return false;
        auto* C=H->FindComponentByClass<UDinkInteriorCameraComponent>();
        auto* Art=W->GetSubsystem<UDinkArtSubsystem>();
        const auto* Rule=Art?FDinkExteriorPortalTestAccess::Actual(*Art):nullptr;
        if(!Stage)
        {
            Story->SkipDialogue();if(PC->IsMoveInputIgnored())return false;
            if(!Test->TestNotNull(TEXT("actual bound cottage source rule"),Rule)||!Test->TestNotNull(TEXT("camera component"),C))return true;
            auto* Local=PC->GetLocalPlayer();auto* Viewport=Local&&Local->ViewportClient?Local->ViewportClient->Viewport:nullptr;
            if(!Test->TestNotNull(TEXT("actual viewport"),Viewport))return true;
            if(Viewport->GetSizeXY()==FIntPoint::ZeroValue)Viewport->SetInitialSize(FIntPoint(1280,720));
            Guard=Grey->BeginWarp(H);if(!Test->TestTrue(TEXT("scoped camera fixture guard"),Guard))return true;
            Mesh=Rule->Component;Profile=Mesh->GetCollisionProfileName();Responses=Mesh->GetCollisionResponseToChannels();
            Enabled=Mesh->GetCollisionEnabled();ObjectType=Mesh->GetCollisionObjectType();Transform=Mesh->GetComponentTransform();
            Overrides=Mesh->OverrideMaterials;Visible=Mesh->IsVisible();Hidden=Mesh->bHiddenInGame;
            CapsuleResponses=H->GetCapsuleComponent()->GetCollisionResponseToChannels();Input=H->InputComponent;
            H->GetCharacterMovement()->StopMovementImmediately();
            H->SetActorLocation(FVector(97729.63625545749,37512.61084546293,98.34999561309814),false,nullptr,ETeleportType::TeleportPhysics);
            Grey->RefreshCurrentScreen();PC->SetControlRotation(FRotator(-18,86.1711,0));At=FPlatformTime::Seconds();Stage=1;return false;
        }
        if(!C||!Rule||!Mesh.IsValid())
        {Test->AddError(TEXT("actual portal fixture lost its owned component"));if(Guard)Grey->EndWarp(H);return true;}
        if(FPlatformTime::Seconds()-At<.5)return false;
        auto* Arm=H->CameraBoom;auto* Camera=H->FollowCamera;
        if(Stage==1)
        {
            Test->TestFalse(TEXT("recorded bad frame is outdoor"),C->bInteriorMode);
            Test->TestEqual(TEXT("explicit actual source owner"),C->OutdoorPortalOwner,FString(TEXT("stonebrook_exterior.json:DinksCottage")));
            Test->TestEqual(TEXT("source native package authority retained"),C->OutdoorPortalMeshSHA,Rule->NativeMeshSHA);
            Test->TestTrue(TEXT("portal headroom solution feasible"),C->bOutdoorPortalFramingFeasible);
            Test->TestTrue(TEXT("presentation cap applies below requested zoom minimum like physical retraction"),C->OutdoorPortalArmCap>90&&C->OutdoorPortalArmCap<125);
            Test->TestEqual(TEXT("requested user zoom still400"),C->GetDesiredArmLength(),400.f);
            const FVector Base=Arm->GetComponentLocation();const FRotator Rotation=Arm->GetTargetRotation();
            const FVector Uncapped=Base-Rotation.Vector()*400+Rotation.RotateVector(Arm->SocketOffset);
            FCollisionQueryParams Params(SCENE_QUERY_STAT(OutdoorPortalTest),false,H);FHitResult Original,Actual;
            const auto Shape=FCollisionShape::MakeSphere(Arm->ProbeSize);
            Test->TestFalse(TEXT("recorded baseline really is clear door NOHIT"),W->SweepSingleByChannel(Original,Base,Uncapped,FQuat::Identity,Arm->ProbeChannel,Shape,Params));
            DinkCameraPortal::FLimit Bound;
            Test->TestTrue(TEXT("actual registered component supplies portal plane"),DinkCameraPortal::Limit(Rule->Definition,Mesh->GetComponentTransform(),Base,Uncapped,Arm->ProbeSize,Bound));
            Test->TestTrue(TEXT("actual native camera remains outside portal lip"),Bound.Outside(Camera->GetComponentLocation()));
            Test->TestFalse(TEXT("actual camera no longer lies in hollow cottage"),Rule->Definition.Inside(Mesh->GetComponentTransform().InverseTransformPosition(Camera->GetComponentLocation())));
            const FVector Raised=Base+Arm->TargetOffset,End=Raised-Rotation.Vector()*Arm->TargetArmLength+Rotation.RotateVector(Arm->SocketOffset);
            const bool Hit=W->SweepSingleByChannel(Actual,Raised,End,FQuat::Identity,Arm->ProbeChannel,Shape,Params);
            Test->TestTrue(TEXT("native camera equals real physical sweep or its clear capped endpoint"),Camera->GetComponentLocation().Equals(Hit?Actual.Location:End,1.));
            FVector2D Pixel;const FVector Top=H->GetCapsuleComponent()->GetComponentLocation()+FVector(0,0,H->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
            Test->TestTrue(TEXT("actual capsule top projects"),PC->ProjectWorldLocationToScreen(Top,Pixel));
            int32 Width=0,Height=0;PC->GetViewportSize(Width,Height);Test->TestTrue(TEXT("actual top inside upper90percent"),Pixel.Y>=Height*.09&&Pixel.Y<Height);
            FMinimalViewInfo View;Camera->GetCameraView(0,View);
            Test->TestTrue(TEXT("top beyond actual near clip"),FVector::DotProduct(Top-Camera->GetComponentLocation(),Camera->GetForwardVector())>View.GetFinalPerspectiveNearClipPlane());
            CheckPreserved(H,PC);
            C->AddZoomInput(1);Test->TestEqual(TEXT("capped camera zoom requests365, not106"),C->GetDesiredArmLength(),365.f);
            C->AddZoomInput(-1);Test->TestEqual(TEXT("reverse zoom immediately returns400"),C->GetDesiredArmLength(),400.f);
            PC->UnPossess();C->TickComponent(.1f,LEVELTICK_All,nullptr);
            Test->TestEqual(TEXT("unpossess clears cap"),C->OutdoorPortalArmCap,0.f);Test->TestEqual(TEXT("unpossess clears lift"),C->OutdoorHeadroomLift,0.f);
            Test->TestTrue(TEXT("unpossess clears owner/pivot"),C->OutdoorPortalOwner.IsEmpty()&&Arm->TargetOffset.IsNearlyZero());PC->Possess(H);
            H->GetCharacterMovement()->SetMovementMode(MOVE_Flying);H->SetActorLocation(H->GetActorLocation()+FVector(0,0,10000),false,nullptr,ETeleportType::TeleportPhysics);
            Grey->RefreshCurrentScreen();At=FPlatformTime::Seconds();Stage=2;return false;
        }
        if(Stage==2)
        {
            Test->TestEqual(TEXT("free outdoor400 restored without cap poisoning zoom"),Arm->TargetArmLength,400.f);
            Test->TestEqual(TEXT("free outdoor has no cap"),C->OutdoorPortalArmCap,0.f);Test->TestEqual(TEXT("free outdoor has no lift"),C->OutdoorHeadroomLift,0.f);
            H->SetActorLocation(FVector(-183760.16,392550.355,98.15),false,nullptr,ETeleportType::TeleportPhysics);Grey->RefreshCurrentScreen();At=FPlatformTime::Seconds();Stage=3;return false;
        }
        Test->TestTrue(TEXT("actual indoor mode retained"),C->bInteriorMode);Test->TestEqual(TEXT("indoor desired arm stays240"),C->GetDesiredArmLength(),240.f);
        Test->TestEqual(TEXT("indoor cap cleared"),C->OutdoorPortalArmCap,0.f);Test->TestEqual(TEXT("indoor outdoor-lift cleared"),C->OutdoorHeadroomLift,0.f);
        CheckPreserved(H,PC);C->DestroyComponent();Test->TestEqual(TEXT("real EndPlay restores outdoor arm"),Arm->TargetArmLength,400.f);
        Test->TestTrue(TEXT("real EndPlay restores pivot"),Arm->TargetOffset.IsNearlyZero());Grey->EndWarp(H);return true;
    }
private:
    void CheckPreserved(ADinkGreyboxCharacter* H,APlayerController* PC)
    {
        Test->TestTrue(TEXT("complete physical policy unchanged"),Mesh->GetCollisionProfileName()==Profile&&Mesh->GetCollisionResponseToChannels()==Responses&&Mesh->GetCollisionEnabled()==Enabled&&Mesh->GetCollisionObjectType()==ObjectType);
        Test->TestTrue(TEXT("architecture pose/material/visibility unchanged"),Mesh->GetComponentTransform().Equals(Transform,0)&&Mesh->OverrideMaterials==Overrides&&Mesh->IsVisible()==Visible&&Mesh->bHiddenInGame==Hidden);
        Test->TestTrue(TEXT("pawn collision and input identity unchanged"),H->GetCapsuleComponent()->GetCollisionResponseToChannels()==CapsuleResponses&&H->InputComponent==Input&&!PC->IsMoveInputIgnored());
    }
    FAutomationTestBase* Test;double Started=0,At=0;int32 Stage=0;bool Guard=false;
    TWeakObjectPtr<UStaticMeshComponent> Mesh;FName Profile;FCollisionResponseContainer Responses,CapsuleResponses;
    ECollisionEnabled::Type Enabled=ECollisionEnabled::NoCollision;ECollisionChannel ObjectType=ECC_WorldStatic;FTransform Transform;
    TArray<TObjectPtr<UMaterialInterface>> Overrides;bool Visible=false,Hidden=false;UInputComponent* Input=nullptr;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkOutdoorPortalCamera,"Dink.Art.Camera.OutdoorPortalCamera",DINK_TEST_FLAGS)
bool FDinkOutdoorPortalCamera::RunTest(const FString&)
{
    const auto File=FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"),FPackageName::GetMapPackageExtension());
    if(!TestNotNull(TEXT("actual current full world loads"),UEditorLoadingAndSavingUtils::LoadMap(File)))return false;
    AddCommand(new FStartPIECommand(false));AddCommand(new FOutdoorPortalCheck(this));AddCommand(new FEndPlayMapCommand());return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPortalOwnership,"Dink.Art.Camera.ExteriorPortalOwnership",DINK_TEST_FLAGS)
bool FDinkPortalOwnership::RunTest(const FString&)
{
    UWorld* W=UWorld::CreateWorld(EWorldType::Game,false);
    if(!TestNotNull(TEXT("scratch ownership world"),W))return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(W);
    ON_SCOPE_EXIT{GEngine->DestroyWorldContext(W);W->DestroyWorld(false);W->MarkObjectsPendingKill();};
    auto* Art=W->GetSubsystem<UDinkArtSubsystem>();
    auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
    if(!TestNotNull(TEXT("actual subsystem"),Art)||!TestNotNull(TEXT("actual engine mesh"),Cube))return false;
    auto* A=W->SpawnActor<AStaticMeshActor>();auto* B=W->SpawnActor<AStaticMeshActor>();
    auto* C=A->GetStaticMeshComponent();auto* Other=B->GetStaticMeshComponent();C->SetStaticMesh(Cube);Other->SetStaticMesh(Cube);
    FDinkExteriorCameraRule R;R.Manifest=TEXT("fixture.json");R.Element=TEXT("OwnedBuilding");R.Screen=439;R.Mesh=Cube->GetPathName();R.NativeMeshSHA=FString::ChrN(64,'a');
    const FBox Box=Cube->GetBounds().GetBox();R.NativeBoundsMin=Box.Min;R.NativeBoundsMax=Box.Max;
    R.Definition.Point=FVector(0,60,0);R.Definition.Normal=FVector(0,1,0);R.Definition.Tangent=FVector(1,0,0);
    R.Definition.Minimum=FVector2D(-30,-30);R.Definition.Maximum=FVector2D(30,30);R.Definition.InteriorPoint=FVector::ZeroVector;
    R.Definition.InteriorPlanes={FPlane(1,0,0,50),FPlane(-1,0,0,50),FPlane(0,1,0,50),FPlane(0,-1,0,50),FPlane(0,0,1,50),FPlane(0,0,-1,50)};
    FDinkExteriorPortalTestAccess::Rules(*Art).Add(R);
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("name"),TEXT("OwnedBuilding"));
    const auto Profile=C->GetCollisionProfileName();const auto Responses=C->GetCollisionResponseToChannels();const auto Materials=C->OverrideMaterials;const auto Transform=C->GetComponentTransform();
    FDinkExteriorPortalTestAccess::Register(*Art,TEXT("decorative-context.json"),Row,439,C);
    TestFalse(TEXT("same mesh/context does not guess owner"),FDinkExteriorPortalTestAccess::Rules(*Art)[0].Component.IsValid());
    FDinkExteriorPortalTestAccess::Register(*Art,TEXT("fixture.json"),Row,1,C);
    TestFalse(TEXT("wrong source screen cannot register"),FDinkExteriorPortalTestAccess::Rules(*Art)[0].Component.IsValid());
    FDinkExteriorPortalTestAccess::Register(*Art,TEXT("fixture.json"),Row,439,C);
    TestTrue(TEXT("exact actual source instance registers"),FDinkExteriorPortalTestAccess::Rules(*Art)[0].Component.Get()==C);
    TestTrue(TEXT("registration does not change physics/materials/pose"),C->GetCollisionProfileName()==Profile&&C->GetCollisionResponseToChannels()==Responses&&C->OverrideMaterials==Materials&&C->GetComponentTransform().Equals(Transform,0));
    FDinkExteriorPortalTestAccess::Register(*Art,TEXT("fixture.json"),Row,439,Other);
    TestFalse(TEXT("duplicate owner invalidates instead of selecting another actor"),FDinkExteriorPortalTestAccess::Rules(*Art)[0].Component.IsValid());
    return true;
}
