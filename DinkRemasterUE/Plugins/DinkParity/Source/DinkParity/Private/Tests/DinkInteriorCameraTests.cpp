#include "DinkTestHelpers.h"
#include <limits>
#include "DinkInteriorCameraComponent.h"
#include "DinkCameraOcclusion.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "Engine/StaticMesh.h"
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "SceneView.h"
#include "UnrealClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
struct FMeshBefore
{
    UStaticMeshComponent* Mesh=nullptr;
    UStaticMesh* Asset=nullptr;
    FTransform Transform;
    FVector Extent, BoundsOrigin;
    ECollisionEnabled::Type Enabled=ECollisionEnabled::NoCollision;
    FName Profile;
    FCollisionResponseContainer Responses;
    ECollisionChannel ObjectType=ECC_WorldStatic;
    TArray<TObjectPtr<UMaterialInterface>> Materials, Overrides;
    explicit FMeshBefore(UStaticMeshComponent* M) : Mesh(M), Asset(M->GetStaticMesh()), Transform(M->GetComponentTransform()),
        Extent(M->Bounds.BoxExtent), BoundsOrigin(M->Bounds.Origin), Enabled(M->GetCollisionEnabled()),
        Profile(M->GetCollisionProfileName()), Responses(M->GetCollisionResponseToChannels()), ObjectType(M->GetCollisionObjectType()), Overrides(M->OverrideMaterials)
    { for (int32 I=0; I<M->GetNumMaterials(); ++I) Materials.Add(M->GetMaterial(I)); }
};
class FInteriorCameraPIE : public IAutomationLatentCommand
{
public:
    explicit FInteriorCameraPIE(FAutomationTestBase* T) : Test(T) {}
    bool Update() override
    {
        if (!Began) Began=FPlatformTime::Seconds();
        if (FPlatformTime::Seconds()-Began>90) { Test->AddError(FString::Printf(TEXT("interior camera PIE timed out phase%d"),Phase)); return true; }
        UWorld* W=GEditor ? GEditor->PlayWorld.Get() : nullptr;
        APlayerController* PC=W ? W->GetFirstPlayerController() : nullptr;
        ADinkGreyboxCharacter* Hero=PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
        UDinkStorySubsystem* Story=W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (!Hero || !Story || Story->bNewGamePending) return false;
        UDinkGreyboxSubsystem* Grey=W->GetSubsystem<UDinkGreyboxSubsystem>();
        UDinkInteriorCameraComponent* C=Hero->FindComponentByClass<UDinkInteriorCameraComponent>();
        if (Phase==0)
        {
            if (!ViewportReady)
            {
                ULocalPlayer* Local=PC->GetLocalPlayer(); FViewport* V=Local && Local->ViewportClient ? Local->ViewportClient->Viewport : nullptr;
                if (!Test->TestNotNull(TEXT("PIE has a real player viewport"),V)) return true;
                const FIntPoint Prior=V->GetSizeXY();
                // NullRHI PIE creates an unsized real viewport. Initialize the actual player
                // surface so both production framing and independent deprojection use real pixels.
                if (Prior==FIntPoint::ZeroValue) V->SetInitialSize(FIntPoint(1280,720));
                const FIntPoint Size=V->GetSizeXY();
                if (!Test->TestTrue(TEXT("actual PIE viewport initialized with positive pixel dimensions"),Size.X>0 && Size.Y>0)) return true;
                Test->AddInfo(FString::Printf(TEXT("Real PIE viewport prior%dx%d initialized%dx%d LocalPlayerSize%s"),Prior.X,Prior.Y,Size.X,Size.Y,*Local->Size.ToString()));
                ViewportReady=true; return false;
            }
            Story->SkipDialogue();
            if (Story->GetActiveMenu() || Story->GetDirector()->GetDink().bFrozen || PC->IsMoveInputIgnored()) return false;
            if (!Test->TestNotNull(TEXT("real character owns interior camera component"),C)) return true;
            Home=Grey->FindScreen(1); Yard=Grey->FindScreen(439);
            if (!Test->TestNotNull(TEXT("actual house volume exists"),Home) || !Test->TestNotNull(TEXT("actual outdoor439 volume exists"),Yard)) return true;
            ExpectedControl=FRotator(-18,225,0); PC->SetControlRotation(ExpectedControl); InputBefore=Hero->InputComponent;
            MoveIgnored=PC->IsMoveInputIgnored(); LookIgnored=PC->IsLookInputIgnored();
            CapsuleResponses=Hero->GetCapsuleComponent()->GetCollisionResponseToChannels(); CapsuleEnabled=Hero->GetCapsuleComponent()->GetCollisionEnabled();
            Move(Hero,Grey,Yard,300,200); Phase=1; At=FPlatformTime::Seconds(); return false;
        }
        if (FPlatformTime::Seconds()-At<.6) return false;
        if (Phase==1)
        {
            Test->TestEqual(TEXT("outdoor439 selected before capturing original wall state"),Grey->GetCurrentScreen(),Yard);
            CheckCamera(Hero,false); CheckInput(Hero,PC);
            Test->TestFalse(TEXT("outdoor camera mode"),C->bInteriorMode);
            // Exercise a nonempty override array with the same original material, as well as the
            // untouched empty/full arrays on every other real wall and ceiling.
            for (TActorIterator<AActor> It(W); It; ++It)
            {
                if (!It->ActorHasTag(TEXT("DinkArtScreen_1")) || !It->ActorHasTag(TEXT("DinkCameraOccluder"))) continue;
                TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
                for (UStaticMeshComponent* M : Meshes)
                {
                    if (!OverrideFixture && M->GetNumMaterials()>0)
                    {
                        OverrideFixture=M; FixtureOverrides=M->OverrideMaterials; M->SetMaterial(0,M->GetMaterial(0));
                    }
                    Before.Emplace(M);
                }
            }
            for (TActorIterator<AActor> It(W); It; ++It)
            {
                if (!It->ActorHasTag(TEXT("DinkArtScreen_1"))) continue;
                TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
                for (UStaticMeshComponent* M : Meshes)
                    if (M->GetStaticMesh() && M->GetStaticMesh()->GetName()==TEXT("SM_Floor_Oak_2m_01")) Floors.Add(M);
            }
            Test->TestEqual(TEXT("actual house floor union contains56 authored floor tiles"),Floors.Num(),56);
            Test->TestTrue(TEXT("real house has multiple tagged wall/ceiling meshes"),Before.Num()>2);
            bool Wall=false, Ceiling=false, Door=false;
            for (const FMeshBefore& B : Before) { Wall|=B.Asset && B.Asset->GetName().Contains(TEXT("Wall")); Ceiling|=B.Asset && B.Asset->GetName().Contains(TEXT("Ceiling")); Door|=B.Asset && B.Asset->GetName().Contains(TEXT("Doorway")); }
            Test->TestTrue(TEXT("fixture includes real walls"),Wall); Test->TestTrue(TEXT("fixture includes real ceiling"),Ceiling); Test->TestTrue(TEXT("returned-door lintel is explicitly tagged for camera management"),Door);
            UnknownActor=W->SpawnActor<AActor>(); Unknown=NewObject<UStaticMeshComponent>(UnknownActor,TEXT("UnknownCameraMaterial"));
            UnknownActor->SetRootComponent(Unknown); UnknownActor->AddInstanceComponent(Unknown);
            Unknown->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
            Unknown->SetMobility(EComponentMobility::Movable); Unknown->SetCollisionProfileName(TEXT("BlockAll")); Unknown->RegisterComponent();
            UnknownActor->SetActorLocation(Home->MapPixelToWorld(100,100)+FVector(0,0,5000));
            UnknownActor->Tags.Add(TEXT("DinkArtScreen_1")); UnknownActor->Tags.Add(TEXT("DinkCameraOccluder"));
            UnknownMaterial=Unknown->GetMaterial(0);
            ExpectedControl=FRotator(0,270,0); PC->SetControlRotation(ExpectedControl);
            Move(Hero,Grey,Home,303.5,345); Phase=5; At=FPlatformTime::Seconds(); return false;
        }
        if (Phase==5)
        {
            CheckCamera(Hero,true); CheckInput(Hero,PC);
            UStaticMeshComponent* Portal=nullptr;
            for (const FMeshBefore& B : Before) if (B.Asset && B.Asset->GetName().Contains(TEXT("Doorway"))) Portal=B.Mesh;
            if (!Test->TestNotNull(TEXT("clear-aperture fixture uses actual doorway mesh"),Portal)) return true;
            const FRotator R=Hero->CameraBoom->GetTargetRotation();
            const FVector Eye=Hero->CameraBoom->GetComponentLocation()+Hero->CameraBoom->TargetOffset-R.Vector()*Hero->CameraBoom->TargetArmLength+R.RotateVector(Hero->CameraBoom->SocketOffset);
            Test->TestTrue(TEXT("clear camera lies inside doorway's broad AABB"),Portal->Bounds.GetBox().IsInside(Eye));
            FHitResult Near; Test->TestFalse(TEXT("real doorway sphere probe clears the empty aperture"),Portal->SweepComponent(Near,Eye,Eye+FVector(.01,0,0),FQuat::Identity,FCollisionShape::MakeSphere(Hero->CameraBoom->ProbeSize+6.f),true));
            FCollisionQueryParams Q(TEXT("ClearPortalRegression"),true,Hero);
            const FVector Side=R.RotateVector(FVector(0,22,0));
            for (const FVector& Target : {Hero->GetActorLocation()+FVector(0,0,60),Hero->GetActorLocation(),Hero->GetActorLocation()-FVector(0,0,60),Hero->GetActorLocation()+Side,Hero->GetActorLocation()-Side})
            { FHitResult Hit; Test->TestFalse(TEXT("actual doorway body ray clears empty aperture"),Portal->LineTraceComponent(Hit,Eye,Target,Q)); }
            Test->TestEqual(TEXT("a clear aperture never fades the surrounding doorway/walls"),C->FadingOccluderCount,0);
            for (int32 I=0; I<Portal->GetNumMaterials(); ++I)
            {
                UMaterialInstanceDynamic* MID=Cast<UMaterialInstanceDynamic>(Portal->GetMaterial(I)); float Opacity=0;
                if (Test->TestNotNull(TEXT("clear portal still managed with fade variants"),MID))
                { Test->TestTrue(TEXT("portal fade parameter exists"),MID->GetScalarParameterValue(FMaterialParameterInfo(TEXT("DinkCameraOpacity")),Opacity)); Test->TestEqual(TEXT("clear aperture retains opaque frame"),Opacity,1.f); }
            }
            Test->AddInfo(FString::Printf(TEXT("Clear-aperture fixture pawn%s eye%s insideDoorBounds1 geometricSphereClear1 opacity1"),*Hero->GetActorLocation().ToCompactString(),*Eye.ToCompactString()));
            ExpectedControl=FRotator(-18,270,0); PC->SetControlRotation(ExpectedControl);
            // A static camera inspection at the live return pose overlaps the exit warp.
            // Hold only the existing reentrant-warp guard until this fixture is inspected.
            Test->TestTrue(TEXT("return camera fixture acquires scoped warp guard"),Grey->BeginWarp(Hero));
            Move(Hero,Grey,Home,302.956,386.332); Phase=8; At=FPlatformTime::Seconds(); return false;
        }
        if (Phase==8)
        {
            CheckInput(Hero,PC);
            Test->TestEqual(TEXT("static actual-return camera fixture stays in screen1"),Grey->GetCurrentScreen(),Home);
            CheckForegroundReturn(Hero,PC);
            Grey->EndWarp(Hero);
            ExpectedControl=FRotator(-18,225,0); PC->SetControlRotation(ExpectedControl);
            Move(Hero,Grey,Home,303.5,370); Phase=2; At=FPlatformTime::Seconds(); return false;
        }
        if (Phase==6 || Phase==7)
        {
            CheckInput(Hero,PC);
            Test->TestEqual(TEXT("adaptive fixture remains in actual house1"),Grey->GetCurrentScreen(),Home);
            const FVector Expected=Home->MapPixelToWorld(303.5,382);
            Test->TestTrue(TEXT("frustum solve never translates pawn XY"),FVector2D(Hero->GetActorLocation()-Expected).Size()<.05);
            Test->TestEqual(TEXT("adaptive framing retains240cm arm"),Hero->CameraBoom->TargetArmLength,240.f);
            Test->TestEqual(TEXT("adaptive framing retains70deg FOV"),Hero->FollowCamera->FieldOfView,70.f);
            Test->TestTrue(TEXT("adaptive framing retains52cm vertical pivot"),FMath::IsNearlyEqual(Hero->CameraBoom->TargetOffset.Z,52.,.01));
            const double Shoulder=Phase==7 ? -45. : 45.;
            Test->TestTrue(TEXT("315 chooses left shoulder;225 retains right shoulder"),Hero->CameraBoom->SocketOffset.Equals(FVector(0,Shoulder,0),.01));
            const FVector2D Pan(Hero->CameraBoom->TargetOffset.X,Hero->CameraBoom->TargetOffset.Y);
            Test->TestTrue(TEXT("actual returned-door pose receives a bounded inward camera-only pan"),Pan.Y<-1 && Pan.Size()>1 && Pan.Size()<=150.01);
            const FVector Eye=Hero->FollowCamera->GetComponentLocation();
            Test->TestTrue(TEXT("adaptive camera preserves readable180cm view depth"),FVector::DotProduct(Hero->GetActorLocation()-Eye,Hero->FollowCamera->GetForwardVector())>=179.9);
            Test->TestTrue(TEXT("adaptive camera remains over180cm from pawn"),FVector::Distance(Eye,Hero->GetActorLocation())>180);
            Test->TestEqual(TEXT("adaptive framing retains ownership of85 architectural surfaces"),C->ManagedOccluderCount,Before.Num());
            for (const FMeshBefore& B : Before)
            {
                CheckGeometry(B); FCollisionResponseContainer Responses=B.Responses; Responses.SetResponse(ECC_Camera,ECR_Ignore);
                Test->TestTrue(TEXT("adaptive framing preserves every nonCamera response"),B.Mesh->GetCollisionResponseToChannels()==Responses);
                for (int32 I=0; I<B.Materials.Num(); ++I) Test->TestNotNull(TEXT("adaptive wall still uses owned fade MID"),Cast<UMaterialInstanceDynamic>(B.Mesh->GetMaterial(I)));
            }
            Test->TestEqual(TEXT("adaptive solve does not mutate unknown material"),Unknown->GetMaterial(0),UnknownMaterial);
            Test->TestEqual(TEXT("adaptive solve retains unknown Camera blocker"),Unknown->GetCollisionResponseToChannel(ECC_Camera),ECR_Block);
            CheckBottomFloor(Hero,PC);
            Test->AddInfo(FString::Printf(TEXT("Adaptive382 yaw%.1f shoulder%.1f pan%s actualEye%s"),ExpectedControl.Yaw,Shoulder,*Pan.ToString(),*Eye.ToCompactString()));
            if (Phase==6)
            {
                ExpectedControl=FRotator(-18,315,0); PC->SetControlRotation(ExpectedControl); Phase=7; At=FPlatformTime::Seconds(); return false;
            }
            const FVector Pivot=Hero->CameraBoom->GetComponentLocation()+Hero->CameraBoom->TargetOffset;
            UnknownActor->SetActorLocation(FMath::Lerp(Pivot,Hero->CameraBoom->GetUnfixedCameraPosition(),.55));
            Phase=9;At=FPlatformTime::Seconds();return false;
        }
        if (Phase==9)
        {
            const FVector Pivot=Hero->CameraBoom->GetComponentLocation()+Hero->CameraBoom->TargetOffset;
            const FVector Unfixed=Hero->CameraBoom->GetUnfixedCameraPosition();
            FCollisionQueryParams Q(TEXT("UnsupportedBoomBlocker"),false,Hero);FHitResult Hit;
            const bool Blocked=W->SweepSingleByChannel(Hit,Pivot,Unfixed,FQuat::Identity,ECC_Camera,FCollisionShape::MakeSphere(Hero->CameraBoom->ProbeSize),Q);
            Test->TestTrue(TEXT("unsupported material provides actual camera sweep blocker"),Blocked && Hit.GetComponent()==Unknown);
            Test->TestTrue(TEXT("unsupported material retains actual spring-arm retraction"),Hero->CameraBoom->IsCollisionFixApplied());
            Test->TestTrue(TEXT("retained blocker shortens actual camera distance"),FVector::Dist(Pivot,Hero->FollowCamera->GetComponentLocation())+1<FVector::Dist(Pivot,Unfixed));
            Test->TestEqual(TEXT("unsupported blocker material remains original while retracting"),Unknown->GetMaterial(0),UnknownMaterial);
            Test->TestEqual(TEXT("unsupported blocker keeps camera response while retracting"),Unknown->GetCollisionResponseToChannel(ECC_Camera),ECR_Block);
            CheckInput(Hero,PC);
            UnknownActor->SetActorLocation(Home->MapPixelToWorld(100,100)+FVector(0,0,5000));
            Move(Hero,Grey,Yard,300,200);Phase=3;At=FPlatformTime::Seconds();return false;
        }
        if (Phase==2 || Phase==4)
        {
            Test->TestEqual(TEXT("indoor fixture selects actual screen1"),Grey->GetCurrentScreen(),Home);
            CheckCamera(Hero,true); CheckInput(Hero,PC);
            Test->TestTrue(TEXT("interior camera active"),C->bInteriorMode);
            Test->TestEqual(TEXT("all real tagged walls/ceiling managed, unsupported fixture excluded"),C->ManagedOccluderCount,Before.Num());
            Test->TestTrue(TEXT("real returned-door yaw225 fades an occluding surface"),C->FadingOccluderCount>0);
            Test->TestTrue(TEXT("actual camera remains over180cm from pawn at yaw225"),FVector::Distance(Hero->FollowCamera->GetComponentLocation(),Hero->GetActorLocation())>180.f);
            const FRotator R=Hero->CameraBoom->GetTargetRotation();
            const FVector Eye=Hero->CameraBoom->GetComponentLocation()+Hero->CameraBoom->TargetOffset-R.Vector()*Hero->CameraBoom->TargetArmLength+R.RotateVector(Hero->CameraBoom->SocketOffset);
            Test->AddInfo(FString::Printf(TEXT("Camera fixture phase%d pawn%s actualEye%s desiredEye%s rotation%s managed%d fading%d"),Phase,*Hero->GetActorLocation().ToCompactString(),*Hero->FollowCamera->GetComponentLocation().ToCompactString(),*Eye.ToCompactString(),*R.ToCompactString(),C->ManagedOccluderCount,C->FadingOccluderCount));
            int32 Transparent=0;
            for (const FMeshBefore& B : Before)
            {
                bool BoxHit=false, TraceHit=false; FCollisionQueryParams Query(TEXT("CameraRegressionDiagnosis"),true,Hero);
                const FVector Side=R.RotateVector(FVector(0,22,0));
                for (const FVector& Target : {Hero->GetActorLocation()+FVector(0,0,60),Hero->GetActorLocation(),Hero->GetActorLocation()-FVector(0,0,60),Hero->GetActorLocation()+Side,Hero->GetActorLocation()-Side})
                { BoxHit|=FMath::LineBoxIntersection(B.Mesh->Bounds.GetBox(),Eye,Target,Target-Eye); FHitResult Hit; TraceHit|=B.Mesh->LineTraceComponent(Hit,Eye,Target,Query); }
                if (BoxHit || TraceHit || B.Mesh->Bounds.GetBox().ExpandBy(12).IsInside(Eye)) Test->AddInfo(FString::Printf(TEXT("Occluder %s bounds%s extent%s containsEye%d boxRay%d actualTrace%d"),*B.Asset->GetName(),*B.Mesh->Bounds.Origin.ToCompactString(),*B.Mesh->Bounds.BoxExtent.ToCompactString(),B.Mesh->Bounds.GetBox().ExpandBy(12).IsInside(Eye),BoxHit,TraceHit));
                CheckGeometry(B); FCollisionResponseContainer Expected=B.Responses; Expected.SetResponse(ECC_Camera,ECR_Ignore);
                Test->TestTrue(TEXT("only Camera response changes; Pawn/visibility/other channels preserved"),B.Mesh->GetCollisionResponseToChannels()==Expected);
                for (int32 I=0; I<B.Materials.Num(); ++I)
                {
                    UMaterialInstanceDynamic* MID=Cast<UMaterialInstanceDynamic>(B.Mesh->GetMaterial(I));
                    if (Test->TestNotNull(TEXT("every managed material is a dynamic fade variant"),MID))
                    {
                        float Opacity=1; Test->TestTrue(TEXT("fade scalar exists"),MID->GetScalarParameterValue(FMaterialParameterInfo(TEXT("DinkCameraOpacity")),Opacity));
                        Test->TestTrue(TEXT("opacity remains valid"),Opacity>=0 && Opacity<=1); Transparent+=Opacity<.001f ? 1 : 0;
                    }
                }
            }
            Test->TestTrue(TEXT("fade reaches zero opacity after settling"),Transparent>0);
            Test->TestEqual(TEXT("unmapped material remains original"),Unknown->GetMaterial(0),UnknownMaterial);
            Test->TestEqual(TEXT("unmapped material keeps Camera blocker"),Unknown->GetCollisionResponseToChannel(ECC_Camera),ECR_Block);
            Test->TestEqual(TEXT("unmapped material keeps BlockAll profile"),Unknown->GetCollisionProfileName(),FName(TEXT("BlockAll")));
            if (Phase==2) { Move(Hero,Grey,Home,303.5,382); Phase=6; At=FPlatformTime::Seconds(); return false; }
            Test->TestTrue(TEXT("external ownership fixture has six supported meshes"),Before.Num()>=6);
            if (Before.Num()<6) return true;
            Before[0].Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Before[1].Mesh->SetCollisionObjectType(ECC_WorldDynamic);
            Before[2].Mesh->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
            const FName ExternalProfile=Before[2].Mesh->GetCollisionProfileName();
            const FCollisionResponseContainer ExternalResponses=Before[2].Mesh->GetCollisionResponseToChannels();
            const ECollisionEnabled::Type ExternalEnabled=Before[2].Mesh->GetCollisionEnabled();
            const ECollisionChannel ExternalObjectType=Before[2].Mesh->GetCollisionObjectType();
            Before[3].Mesh->SetCollisionResponseToChannel(ECC_Pawn,ECR_Overlap);
            Before[4].Mesh->SetCollisionResponseToChannel(ECC_Camera,ECR_Overlap);
            const int32 ExtraSlot=Before[5].Mesh->GetNumMaterials()+2;
            Before[5].Mesh->SetMaterial(ExtraSlot,UnknownMaterial);
            auto ExpectedOverrides=Before[5].Mesh->OverrideMaterials;
            for (int32 I=0;I<Before[5].Materials.Num();++I)
                ExpectedOverrides[I]=Before[5].Overrides.IsValidIndex(I) ? Before[5].Overrides[I] : nullptr;
            C->DestroyComponent();
            Test->TestEqual(TEXT("external NoCollision survives manager destruction"),Before[0].Mesh->GetCollisionEnabled(),ECollisionEnabled::NoCollision);
            Test->TestEqual(TEXT("external object type survives manager destruction"),Before[1].Mesh->GetCollisionObjectType(),ECC_WorldDynamic);
            Test->TestEqual(TEXT("external named profile survives manager destruction"),Before[2].Mesh->GetCollisionProfileName(),ExternalProfile);
            Test->TestTrue(TEXT("external named profile responses survive manager destruction"),Before[2].Mesh->GetCollisionResponseToChannels()==ExternalResponses);
            Test->TestEqual(TEXT("external named profile enabled state survives"),Before[2].Mesh->GetCollisionEnabled(),ExternalEnabled);
            Test->TestEqual(TEXT("external named profile object type survives"),Before[2].Mesh->GetCollisionObjectType(),ExternalObjectType);
            Test->TestEqual(TEXT("external Pawn response survives manager destruction"),Before[3].Mesh->GetCollisionResponseToChannel(ECC_Pawn),ECR_Overlap);
            Test->TestEqual(TEXT("owned Camera response restores beside external Pawn change"),Before[3].Mesh->GetCollisionResponseToChannel(ECC_Camera),Before[3].Responses.GetResponse(ECC_Camera));
            Test->TestEqual(TEXT("external Camera response survives manager destruction"),Before[4].Mesh->GetCollisionResponseToChannel(ECC_Camera),ECR_Overlap);
            Test->TestEqual(TEXT("foreign appended material survives manager destruction"),Before[5].Mesh->GetMaterial(ExtraSlot),UnknownMaterial);
            Test->TestTrue(TEXT("only owned material slots restore beside foreign appended override"),Before[5].Mesh->OverrideMaterials==ExpectedOverrides);
            // Restore the test's deliberate external changes before the original85-mesh invariants.
            for (int32 I=0;I<6;++I)
            {
                const FMeshBefore& B=Before[I]; B.Mesh->SetCollisionEnabled(B.Enabled);
                B.Mesh->SetCollisionObjectType(B.ObjectType);B.Mesh->SetCollisionResponseToChannels(B.Responses);B.Mesh->SetCollisionProfileName(B.Profile);
                B.Mesh->OverrideMaterials=B.Overrides;B.Mesh->MarkRenderStateDirty();
            }
            CheckRestored(); CheckCamera(Hero,false); CheckInput(Hero,PC);
            Test->TestEqual(TEXT("unsupported component remains blocking after destruction"),Unknown->GetCollisionResponseToChannel(ECC_Camera),ECR_Block);
            if (OverrideFixture) { OverrideFixture->OverrideMaterials=FixtureOverrides; OverrideFixture->MarkRenderStateDirty(); }
            UnknownActor->Destroy(); return true;
        }
        if (Phase==3)
        {
            Test->TestEqual(TEXT("exit selects outdoor439"),Grey->GetCurrentScreen(),Yard);
            Test->TestFalse(TEXT("exiting clears interior mode"),C->bInteriorMode);
            Test->TestEqual(TEXT("exiting releases occluder ownership"),C->ManagedOccluderCount,0);
            CheckRestored(); CheckCamera(Hero,false); CheckInput(Hero,PC);
            ExpectedControl=FRotator(-18,225,0); PC->SetControlRotation(ExpectedControl);
            Move(Hero,Grey,Home,303.5,370); Phase=4; At=FPlatformTime::Seconds(); return false;
        }
        return false;
    }
private:
    void Move(ADinkGreyboxCharacter* H,UDinkGreyboxSubsystem* G,ADinkScreenVolume* S,double X,double Y)
    { H->GetCharacterMovement()->StopMovementImmediately(); H->SetActorLocation(S->MapPixelToWorld(X,Y)+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics); G->RefreshCurrentScreen(); }
    void CheckGeometry(const FMeshBefore& B)
    {
        Test->TestEqual(TEXT("occluder mesh asset retained"),B.Mesh->GetStaticMesh().Get(),B.Asset);
        Test->TestEqual(TEXT("occluder collision enabled unchanged"),B.Mesh->GetCollisionEnabled(),B.Enabled);
        Test->TestTrue(TEXT("occluder transform unchanged"),B.Mesh->GetComponentTransform().Equals(B.Transform,.01));
        Test->TestTrue(TEXT("occluder extents unchanged"),B.Mesh->Bounds.BoxExtent.Equals(B.Extent,.01));
        Test->TestTrue(TEXT("occluder bounds origin unchanged"),B.Mesh->Bounds.Origin.Equals(B.BoundsOrigin,.01));
    }
    void CheckRestored()
    {
        for (const FMeshBefore& B : Before)
        {
            CheckGeometry(B); Test->TestEqual(TEXT("original collision profile restored"),B.Mesh->GetCollisionProfileName(),B.Profile);
            Test->TestTrue(TEXT("all original collision responses restored"),B.Mesh->GetCollisionResponseToChannels()==B.Responses);
            Test->TestTrue(TEXT("exact original override array restored"),B.Mesh->OverrideMaterials==B.Overrides);
            for (int32 I=0; I<B.Materials.Num(); ++I) Test->TestEqual(TEXT("original effective material restored"),B.Mesh->GetMaterial(I),B.Materials[I].Get());
        }
    }
    bool FloorContains(const FVector2D& Point,ADinkGreyboxCharacter* Hero,double FloorZ)
    {
        const FVector Start(Point.X,Point.Y,FloorZ+25),End(Point.X,Point.Y,FloorZ-25);
        FCollisionQueryParams Q(TEXT("CameraFloorGeometryRegression"),true,Hero);
        for (UStaticMeshComponent* Floor : Floors)
        {
            const FBox Box=Floor->Bounds.GetBox();
            if (Point.X<Box.Min.X || Point.X>Box.Max.X || Point.Y<Box.Min.Y || Point.Y>Box.Max.Y) continue;
            FHitResult Hit;
            if (Floor->LineTraceComponent(Hit,Start,End,Q)) return true;
            // The source has sub-centimetre plank seams. A0.5cm physical probe tolerates only
            // those gaps; the strict footprint test above never expands an exterior tile boundary.
            if (Floor->SweepComponent(Hit,Start,End,FQuat::Identity,FCollisionShape::MakeSphere(.5f),true)) return true;
        }
        return false;
    }
    void CheckBottomFloor(ADinkGreyboxCharacter* Hero,APlayerController* PC)
    {
        ULocalPlayer* Local=PC->GetLocalPlayer();
        FViewport* Viewport=Local && Local->ViewportClient ? Local->ViewportClient->Viewport : nullptr;
        if (!Test->TestNotNull(TEXT("real local player viewport available for independent frustum projection"),Viewport)) return;
        FSceneViewProjectionData Projection;
        if (!Test->TestTrue(TEXT("actual PC viewport projection is available"),Local->GetProjectionData(Viewport,Projection))) return;
        const FIntRect Rect=Projection.GetConstrainedViewRect();
        if (!Test->TestTrue(TEXT("actual constrained viewport has positive size"),Rect.Width()>0 && Rect.Height()>0)) return;
        double FloorZ=-DBL_MAX;
        for (UStaticMeshComponent* Floor : Floors) FloorZ=FMath::Max(FloorZ,Floor->Bounds.GetBox().Max.Z);
        Test->TestTrue(TEXT("source/rendered floor plane isZ0, independent of pawn floor clearance"),FMath::Abs(FloorZ)<.01);
        const FMatrix Inverse=Projection.ComputeViewProjectionMatrix().InverseFast();
        for (double Fraction : {0.,.5,1.})
        {
            const FVector2D Pixel(Rect.Min.X+Fraction*Rect.Width(),Rect.Max.Y);
            FVector Origin,Direction;
            FSceneView::DeprojectScreenToWorld(Pixel,Rect,Inverse,Origin,Direction);
            if (!Test->TestTrue(TEXT("actual bottom-frustum ray points down toward floor"),Direction.Z<-.000001)) continue;
            const double Distance=(FloorZ-Origin.Z)/Direction.Z;
            if (!Test->TestTrue(TEXT("bottom floor intersection is in front of actual camera"),Distance>0)) continue;
            const FVector Hit=Origin+Direction*Distance; bool Inside=true;
            for (const FVector2D& Offset : {FVector2D(0,0),FVector2D(3,0),FVector2D(-3,0),FVector2D(0,3),FVector2D(0,-3),FVector2D(2.12132,2.12132),FVector2D(-2.12132,2.12132),FVector2D(2.12132,-2.12132),FVector2D(-2.12132,-2.12132)})
                Inside &= FloorContains(FVector2D(Hit.X,Hit.Y)+Offset,Hero,FloorZ);
            Test->TestTrue(TEXT("projected bottom corner/center lies within actual floor geometry union with3cm margin"),Inside);
            Test->AddInfo(FString::Printf(TEXT("Floor-frustum yaw%.1f viewport%dx%d fraction%.1f floorHit%s insideUnionMargin3=%d"),ExpectedControl.Yaw,Rect.Width(),Rect.Height(),Fraction,*Hit.ToCompactString(),Inside));
        }
    }
    void CheckForegroundReturn(ADinkGreyboxCharacter* Hero,APlayerController* PC)
    {
        UStaticMeshComponent* Portal=nullptr;
        for (const FMeshBefore& B : Before) if (B.Asset && B.Asset->GetName().Contains(TEXT("Doorway"))) Portal=B.Mesh;
        if (!Test->TestNotNull(TEXT("foreground fixture uses actual authored doorway"),Portal)) return;
        const FVector Eye=Hero->FollowCamera->GetComponentLocation(), Body=Hero->GetActorLocation();
        const FRotator Rotation=Hero->FollowCamera->GetComponentRotation();
        const FVector Forward=Rotation.Vector(), Side=Rotation.RotateVector(FVector(0,22,0));
        const double EndDepth=FVector::DotProduct(Body-Eye,Forward)-Hero->GetCapsuleComponent()->GetScaledCapsuleRadius();
        FCollisionQueryParams Q(TEXT("IndependentForegroundRegression"),true,Hero);
        FHitResult Near;
        Test->TestFalse(TEXT("returned peripheral jamb misses legacy near-eye sphere"),Portal->SweepComponent(Near,Eye,Eye+FVector(.01,0,0),FQuat::Identity,FCollisionShape::MakeSphere(Hero->CameraBoom->ProbeSize+6.f),true));
        for (const FVector& Target : {Body+FVector(0,0,60),Body,Body-FVector(0,0,60),Body+Side,Body-Side})
        { FHitResult Hit; Test->TestFalse(TEXT("returned peripheral jamb misses all legacy body rays"),Portal->LineTraceComponent(Hit,Eye,Target,Q)); }
        ULocalPlayer* Local=PC->GetLocalPlayer();
        FViewport* Viewport=Local && Local->ViewportClient ? Local->ViewportClient->Viewport : nullptr;
        FSceneViewProjectionData Projection;
        if (!Test->TestTrue(TEXT("actual viewport projects peripheral foreground fixture"),Viewport && Local->GetProjectionData(Viewport,Projection))) return;
        const FIntRect Rect=Projection.GetConstrainedViewRect();
        const FMatrix Inverse=Projection.ComputeViewProjectionMatrix().InverseFast();
        int32 ActualForegroundHits=0;
        for (double X : {.75,.85,.95}) for (double Y : {.3,.5,.7})
        {
            FVector Origin,Direction;
            FSceneView::DeprojectScreenToWorld(FVector2D(Rect.Min.X+X*Rect.Width(),Rect.Min.Y+Y*Rect.Height()),Rect,Inverse,Origin,Direction);
            const double Rate=FVector::DotProduct(Direction,Forward);
            if (Rate<=0) continue;
            const double StartDepth=FVector::DotProduct(Origin-Eye,Forward);
            FHitResult Hit;
            if (Portal->LineTraceComponent(Hit,Origin,Origin+Direction*((EndDepth-StartDepth)/Rate),Q))
            {
                const double Depth=FVector::DotProduct(Hit.ImpactPoint-Eye,Forward);
                Test->TestTrue(TEXT("independently projected jamb hit is visible foreground before pawn"),Depth>0 && Depth<EndDepth);
                ++ActualForegroundHits;
            }
        }
        Test->TestTrue(TEXT("several independent right-third viewport rays hit actual foreground jamb"),ActualForegroundHits>=3);
        TArray<DinkCameraOcclusion::FSweep> Sweeps;
        FMinimalViewInfo View; Hero->FollowCamera->GetCameraView(0,View);
        Test->TestTrue(TEXT("actual-projection foreground sweeps build"),DinkCameraOcclusion::BuildForegroundSweeps(Eye,Rotation,Projection.ProjectionMatrix,View.GetFinalPerspectiveNearClipPlane(),EndDepth,Sweeps));
        Test->TestTrue(TEXT("inscribed component sweep detects genuine foreground jamb"),DinkCameraOcclusion::Intersects(Portal,Sweeps));
        for (int32 I=0; I<Portal->GetNumMaterials(); ++I)
        {
            UMaterialInstanceDynamic* MID=Cast<UMaterialInstanceDynamic>(Portal->GetMaterial(I)); float Opacity=1;
            if (Test->TestNotNull(TEXT("foreground jamb owns fade material"),MID))
            { Test->TestTrue(TEXT("foreground fade parameter exists"),MID->GetScalarParameterValue(FMaterialParameterInfo(TEXT("DinkCameraOpacity")),Opacity)); Test->TestEqual(TEXT("actual-return peripheral jamb fades despite clear body rays"),Opacity,0.f); }
        }
        // Real collision-backed negative controls using the same component query path.
        AActor* Fixture=Hero->GetWorld()->SpawnActor<AActor>();
        UStaticMeshComponent* Cube=NewObject<UStaticMeshComponent>(Fixture);
        Fixture->SetRootComponent(Cube); Fixture->AddInstanceComponent(Cube);
        Cube->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
        Cube->SetMobility(EComponentMobility::Movable); Cube->SetCollisionProfileName(TEXT("BlockAll"));
        Cube->SetWorldScale3D(FVector(.2)); Cube->RegisterComponent();
        const FVector Right=Rotation.RotateVector(FVector(0,1,0));
        Fixture->SetActorLocation(Eye+Forward*80+Right*30);
        Test->TestTrue(TEXT("solid off-axis foreground mesh intersects projection volume"),DinkCameraOcclusion::Intersects(Cube,Sweeps));
        Fixture->SetActorLocation(Eye-Forward*80);
        Test->TestFalse(TEXT("mesh behind eye never intersects foreground volume"),DinkCameraOcclusion::Intersects(Cube,Sweeps));
        Fixture->SetActorLocation(Eye+Forward*(EndDepth+150));
        Test->TestFalse(TEXT("mesh beyond pawn never intersects foreground volume"),DinkCameraOcclusion::Intersects(Cube,Sweeps));
        Fixture->SetActorLocation(Eye+Forward*80+Right*300);
        Test->TestFalse(TEXT("mesh outside projected view never intersects foreground volume"),DinkCameraOcclusion::Intersects(Cube,Sweeps));
        Fixture->Destroy();
        Test->AddInfo(FString::Printf(TEXT("Actual-return foreground pawn%s eye%s control%s independentPixelHits%d endDepth%.3f"),*Body.ToCompactString(),*Eye.ToCompactString(),*Rotation.ToCompactString(),ActualForegroundHits,EndDepth));
    }
    void CheckCamera(ADinkGreyboxCharacter* H,bool Indoors)
    {
        Test->TestEqual(TEXT("camera arm preset"),H->CameraBoom->TargetArmLength,Indoors ? 240.f : 400.f);
        Test->TestTrue(TEXT("camera pivot preset"),H->CameraBoom->TargetOffset.Equals(Indoors ? FVector(0,0,52) : FVector::ZeroVector));
        Test->TestTrue(TEXT("camera shoulder preset"),H->CameraBoom->SocketOffset.Equals(Indoors ? FVector(0,45,0) : FVector::ZeroVector));
        Test->TestEqual(TEXT("camera FOV preset"),H->FollowCamera->FieldOfView,Indoors ? 70.f : 90.f);
    }
    void CheckInput(ADinkGreyboxCharacter* H,APlayerController* PC)
    {
        Test->TestTrue(TEXT("requested gameplay control yaw/pitch unchanged"),PC->GetControlRotation().Equals(ExpectedControl,.01));
        Test->TestEqual(TEXT("movement input ignore unchanged"),PC->IsMoveInputIgnored(),MoveIgnored);
        Test->TestEqual(TEXT("look input ignore unchanged"),PC->IsLookInputIgnored(),LookIgnored);
        Test->TestEqual(TEXT("input component retained"),H->InputComponent.Get(),InputBefore);
        Test->TestTrue(TEXT("player capsule responses unchanged"),H->GetCapsuleComponent()->GetCollisionResponseToChannels()==CapsuleResponses);
        Test->TestEqual(TEXT("player capsule collision enabled unchanged"),H->GetCapsuleComponent()->GetCollisionEnabled(),CapsuleEnabled);
    }
    FAutomationTestBase* Test; int32 Phase=0; double Began=0,At=0;
    ADinkScreenVolume* Home=nullptr; ADinkScreenVolume* Yard=nullptr;
    TArray<FMeshBefore> Before; TArray<UStaticMeshComponent*> Floors; UInputComponent* InputBefore=nullptr;
    UStaticMeshComponent* OverrideFixture=nullptr; TArray<TObjectPtr<UMaterialInterface>> FixtureOverrides;
    AActor* UnknownActor=nullptr; UStaticMeshComponent* Unknown=nullptr; UMaterialInterface* UnknownMaterial=nullptr;
    FRotator ExpectedControl; bool ViewportReady=false,MoveIgnored=false,LookIgnored=false; FCollisionResponseContainer CapsuleResponses; ECollisionEnabled::Type CapsuleEnabled=ECollisionEnabled::NoCollision;
};
class FRestoreCameraArtSetting : public IAutomationLatentCommand
{
public: explicit FRestoreCameraArtSetting(int32 V):Value(V) {} bool Update() override { IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"))->Set(Value,ECVF_SetByCode); return true; }
private:int32 Value;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkInteriorCameraTest,"Dink.Art.InteriorCamera.FadesAndRestoresPhysicalHouse",DINK_TEST_FLAGS)
bool FDinkInteriorCameraTest::RunTest(const FString&)
{
    const FString File=FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"),FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("real gameplay world loads"),UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    IConsoleVariable* Art=IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled")); const int32 Prior=Art->GetInt(); Art->Set(1,ECVF_SetByCode);
    AddCommand(new FStartPIECommand(false)); AddCommand(new FInteriorCameraPIE(this)); AddCommand(new FEndPlayMapCommand()); AddCommand(new FRestoreCameraArtSetting(Prior)); return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkForegroundProjectionTest,"Dink.Art.InteriorCamera.ForegroundProjection",DINK_TEST_FLAGS)
bool FDinkForegroundProjectionTest::RunTest(const FString&)
{
    const FVector Eye(1234,-5678,224); const FRotator Rotation(-18,315,0);
    const FVector Forward=Rotation.Vector(),Right=Rotation.RotateVector(FVector(0,1,0)),Up=Rotation.RotateVector(FVector(0,0,1));
    TArray<DinkCameraOcclusion::FSweep> Sweeps;
    for (const FVector4& Values : {FVector4(1.428148,2.53893,0,0),FVector4(2.,1.,.3,-.2)})
    {
        FMatrix Projection=FMatrix::Identity;
        Projection.M[0][0]=Values.X; Projection.M[1][1]=Values.Y;
        Projection.M[2][0]=Values.Z; Projection.M[2][1]=Values.W;
        Projection.M[2][3]=1.; Projection.M[3][3]=0.;
        TestTrue(TEXT("perspective and off-axis portrait projections build foreground volumes"),DinkCameraOcclusion::BuildForegroundSweeps(Eye,Rotation,Projection,10,212,Sweeps));
        TestEqual(TEXT("bounded twelve-sweep foreground approximation"),Sweeps.Num(),12);
        for (const DinkCameraOcclusion::FSweep& Sweep : Sweeps)
            for (const FVector& Centre : {Sweep.Start,Sweep.End})
                for (double X : {-1.,1.}) for (double Y : {-1.,1.}) for (double Z : {-1.,1.})
                {
                    const FVector Corner=Centre+Rotation.RotateVector(Sweep.HalfExtent*FVector(X,Y,Z))-Eye;
                    const double Depth=FVector::DotProduct(Corner,Forward);
                    const double NDCX=FVector::DotProduct(Corner,Right)*Values.X/Depth+Values.Z;
                    const double NDCY=FVector::DotProduct(Corner,Up)*Values.Y/Depth+Values.W;
                    const bool Inside=FMath::Abs(NDCX)<=1.000001 && FMath::Abs(NDCY)<=1.000001 && Depth>=9.9999 && Depth<=212.0001;
                    if (!Inside) AddError(FString::Printf(TEXT("swept corner escapes projection: NDC %.12f %.12f depth%.12f slopes%s local%s"),NDCX,NDCY,Depth,*Values.ToString(),*(Sweep.HalfExtent*FVector(X,Y,Z)).ToString()));
                }
    }
    TestFalse(TEXT("orthographic matrices are rejected rather than treated as perspective"),DinkCameraOcclusion::BuildForegroundSweeps(Eye,Rotation,FMatrix::Identity,10,212,Sweeps));
    TestTrue(TEXT("invalid projection clears prior sweep output"),Sweeps.IsEmpty());
    FMatrix Projection=FMatrix::Identity; Projection.M[2][3]=1; Projection.M[3][3]=0;
    TestFalse(TEXT("foreground ending before near plane is rejected"),DinkCameraOcclusion::BuildForegroundSweeps(Eye,Rotation,Projection,10,5,Sweeps));
    TestFalse(TEXT("nonfinite far depth is rejected"),DinkCameraOcclusion::BuildForegroundSweeps(Eye,Rotation,Projection,10,std::numeric_limits<double>::infinity(),Sweeps));
    return true;
}
