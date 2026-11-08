#include "DinkTestHelpers.h"
#include "DinkInteriorCameraComponent.h"
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
    TArray<TObjectPtr<UMaterialInterface>> Materials, Overrides;
    explicit FMeshBefore(UStaticMeshComponent* M) : Mesh(M), Asset(M->GetStaticMesh()), Transform(M->GetComponentTransform()),
        Extent(M->Bounds.BoxExtent), BoundsOrigin(M->Bounds.Origin), Enabled(M->GetCollisionEnabled()),
        Profile(M->GetCollisionProfileName()), Responses(M->GetCollisionResponseToChannels()), Overrides(M->OverrideMaterials)
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
            Move(Hero,Grey,Yard,300,200); Phase=3; At=FPlatformTime::Seconds(); return false;
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
            C->DestroyComponent();
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
