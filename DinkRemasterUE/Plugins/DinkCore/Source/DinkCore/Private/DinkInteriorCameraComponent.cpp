#include "DinkInteriorCameraComponent.h"
#include "DinkCoreModule.h"
#include "DinkArtSubsystem.h"
#include "DinkCameraFraming.h"
#include "DinkCameraHeadroom.h"
#include "DinkCameraOcclusion.h"
#include "Components/CapsuleComponent.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "SceneView.h"
#include "EngineUtils.h"
#include "GameFramework/SpringArmComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace { const FName OpacityParameter(TEXT("DinkCameraOpacity")); }

UDinkInteriorCameraComponent::UDinkInteriorCameraComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostPhysics;
}

void UDinkInteriorCameraComponent::BeginPlay()
{
    Super::BeginPlay();
    Arm = GetOwner()->FindComponentByClass<USpringArmComponent>();
    Camera = GetOwner()->FindComponentByClass<UCameraComponent>();
    if (!Arm || !Camera) { SetComponentTickEnabled(false); return; }
    OutdoorArm = Arm->TargetArmLength; UncappedOutdoorArm=OutdoorArm; OutdoorPivot = Arm->TargetOffset;
    OutdoorSocket = Arm->SocketOffset; OutdoorFOV = Camera->FieldOfView;
    Arm->AddTickPrerequisiteComponent(this);
    FString Text; TSharedPtr<FJsonObject> Config;
    if (FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir()/TEXT("Dink/Data/Art/camera_materials.json"))) &&
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Config) && Config.IsValid())
    {
        FString Schema; const TSharedPtr<FJsonObject>* Variants = nullptr;
        if (Config->TryGetStringField(TEXT("schema"), Schema) && Schema == TEXT("dink-camera/1") &&
            Config->TryGetObjectField(TEXT("material_variants"), Variants))
        {
            for (const auto& Pair : (*Variants)->Values)
            {
                FString Path; if (Pair.Value->TryGetString(Path)) MaterialVariants.Add(FString(*Pair.Key).ToLower(), Path);
            }
        }
        const TSharedPtr<FJsonObject>* Floors=nullptr;
        if (Schema==TEXT("dink-camera/1") && Config->TryGetObjectField(TEXT("floor_framing"),Floors))
        {
            for (const auto& Pair : (*Floors)->Values)
            {
                const FString Key(*Pair.Key);
                if (!Key.IsNumeric() || Pair.Value->Type!=EJson::Object) continue;
                const TSharedPtr<FJsonObject> Room=Pair.Value->AsObject();
                const TArray<TSharedPtr<FJsonValue>>* Points=nullptr;
                if (!Room->TryGetArrayField(TEXT("polygon_cm"),Points) || Points->Num()!=4) continue;
                TArray<FVector2D> Polygon;
                for (const auto& Point : *Points)
                {
                    const TArray<TSharedPtr<FJsonValue>>* XY=nullptr;
                    if (!Point->TryGetArray(XY) || XY->Num()!=2 || (*XY)[0]->Type!=EJson::Number || (*XY)[1]->Type!=EJson::Number) break;
                    Polygon.Add(FVector2D((*XY)[0]->AsNumber(),(*XY)[1]->AsNumber()));
                }
                double Height=0;
                if (Polygon.Num()==4 && Room->TryGetNumberField(TEXT("floor_z_cm"),Height) && FMath::IsFinite(Height))
                {
                    RoomFloors.Add(FCString::Atoi(*Key),MoveTemp(Polygon));
                    RoomFloorHeights.Add(FCString::Atoi(*Key),Height);
                }
            }
        }
    }
}

float UDinkInteriorCameraComponent::GetDesiredArmLength() const
{
    return FMath::Clamp((bInteriorMode ? InteriorArmLength : OutdoorArm) + ZoomOffset,
        MinimumArmLength, bInteriorMode ? MaximumInteriorArmLength : MaximumOutdoorArmLength);
}

void UDinkInteriorCameraComponent::AddZoomInput(float Steps)
{
    if (!FMath::IsFinite(Steps) || FMath::IsNearlyZero(Steps)) return;
    const float Base = bInteriorMode ? InteriorArmLength : OutdoorArm;
    // Clamp from the effective distance, so reversing at a limit responds immediately.
    ZoomOffset = FMath::Clamp(GetDesiredArmLength() - FMath::Clamp(Steps, -10.f, 10.f) * ZoomStep,
        MinimumArmLength, bInteriorMode ? MaximumInteriorArmLength : MaximumOutdoorArmLength) - Base;
}

void UDinkInteriorCameraComponent::RestoreCamera()
{
    OutdoorHeadroomLift=0.f; OutdoorPortalArmCap=0.f; bOutdoorPortalFramingFeasible=true; OutdoorPortalOwner.Reset(); OutdoorPortalMeshSHA.Reset(); UncappedOutdoorArm=OutdoorArm;
    FloorFramingShift=FVector::ZeroVector; bFloorFramingAvailable=false; bFloorFramingFeasible=true;
    if (Arm) { Arm->TargetArmLength=OutdoorArm; Arm->TargetOffset=OutdoorPivot; Arm->SocketOffset=OutdoorSocket; }
    if (Camera) Camera->SetFieldOfView(OutdoorFOV);
}

void UDinkInteriorCameraComponent::RestoreOccluders()
{
    for (FDinkCameraOccluder& Entry : Occluders)
    {
        if (!IsValid(Entry.Component)) continue;
        const bool bStillOwned=Entry.Component->OverrideMaterials==Entry.ManagedOverrides;
        if (bStillOwned)
        {
            Entry.Component->OverrideMaterials=Entry.OriginalOverrides;
            Entry.Component->MarkRenderStateDirty();
        }
        else
        {
            bool bRestoredSlot=false;
            for (int32 I=0; I<Entry.OriginalMaterials.Num(); ++I)
            {
                if (Entry.Component->GetMaterial(I)!=Entry.FadeMaterials[I] || !Entry.Component->OverrideMaterials.IsValidIndex(I)) continue;
                Entry.Component->OverrideMaterials[I]=Entry.OriginalOverrides.IsValidIndex(I) ? Entry.OriginalOverrides[I] : nullptr;
                bRestoredSlot=true;
            }
            if (bRestoredSlot) Entry.Component->MarkRenderStateDirty();
        }
        FCollisionResponseContainer Expected=Entry.CollisionResponses;
        Expected.SetResponse(ECC_Camera,ECR_Ignore);
        // A different named profile owns its complete policy, including Camera.
        if (Entry.Component->GetCollisionProfileName()==Entry.ManagedCollisionProfile)
        {
            const bool bPhysicalPolicyOwned=Entry.Component->GetCollisionEnabled()==Entry.CollisionEnabled &&
                Entry.Component->GetCollisionObjectType()==Entry.CollisionObjectType;
            if (bPhysicalPolicyOwned && Entry.Component->GetCollisionResponseToChannels()==Expected)
            {
                Entry.Component->SetCollisionProfileName(Entry.CollisionProfile);
                Entry.Component->SetCollisionResponseToChannel(ECC_Camera,Entry.CameraResponse);
            }
            else if (Entry.Component->GetCollisionResponseToChannel(ECC_Camera)==ECR_Ignore)
            {
                // Release only our channel; preserve external enabled/type/response changes.
                Entry.Component->SetCollisionResponseToChannel(ECC_Camera,Entry.CameraResponse);
            }
        }
    }
    Occluders.Reset(); FadingOccluderCount=0; ManagedOccluderCount=0;
}

void UDinkInteriorCameraComponent::SelectScreen(ADinkScreenVolume* Screen)
{
    const bool SameMode = bSelectedScreen && bInteriorMode == bool(Screen && Screen->bIndoor);
    const float PreviousArm = OutdoorPortalArmCap>0 ? UncappedOutdoorArm : Arm->TargetArmLength;
    RestoreOccluders(); CurrentScreen=Screen; bSelectedScreen=true;
    bAppliedCutaway=bEnableWallCutaway;
    bInteriorMode = Screen && Screen->bIndoor;
    if (bInteriorMode)
    {
        Arm->TargetArmLength=GetDesiredArmLength(); Arm->TargetOffset=OutdoorPivot+InteriorPivotOffset;
        Arm->SocketOffset=OutdoorSocket+InteriorShoulderOffset; Camera->SetFieldOfView(InteriorFieldOfView);
        ShoulderTargetSign=1.f; CurrentShoulderY=InteriorShoulderOffset.Y; bSnapFraming=true;
    }
    else { RestoreCamera(); Arm->TargetArmLength=GetDesiredArmLength(); }
    // Adjacent screens must not restart an in-progress zoom or flash the unzoomed preset.
    if (SameMode) Arm->TargetArmLength=PreviousArm;
    UncappedOutdoorArm=Arm->TargetArmLength;
    // Outdoor meshes participate only through the same explicit tag and complete
    // authored material mapping. Their physical collision and outdoor camera stay intact.
    // Normal play retracts the camera against solid architecture instead of removing it.
    // This also prevents a single exterior-cottage component from fading the whole house.
    if (!Screen || !bEnableWallCutaway) return;
    const FName ScreenTag(*FString::Printf(TEXT("DinkArtScreen_%d"),Screen->ScreenNumber));
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        if (!It->ActorHasTag(ScreenTag) || !It->ActorHasTag(TEXT("DinkCameraOccluder"))) continue;
        TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
        for (UStaticMeshComponent* Mesh : Meshes)
        {
            if (!Mesh->IsRegistered() || Mesh->GetNumMaterials()==0) continue;
            TArray<UMaterialInterface*> Variants; bool bComplete=true;
            for (int32 I=0; I<Mesh->GetNumMaterials(); ++I)
            {
                UMaterialInterface* Original=Mesh->GetMaterial(I);
                const FString* Path=Original ? MaterialVariants.Find(Original->GetPathName().ToLower()) : nullptr;
                UMaterialInterface* Variant=Path ? LoadObject<UMaterialInterface>(nullptr,**Path) : nullptr;
                float DefaultOpacity=0;
                if (!Variant || Variant->GetBlendMode()!=BLEND_Masked ||
                    !Variant->GetScalarParameterValue(FMaterialParameterInfo(OpacityParameter),DefaultOpacity) ||
                    !FMath::IsNearlyEqual(DefaultOpacity,1.f)) { bComplete=false; break; }
                Variants.Add(Variant);
            }
            // Without a complete authored fade variant, retain the original camera blocker.
            if (!bComplete) continue;
            FDinkCameraOccluder Entry; Entry.Component=Mesh;
            Entry.CameraResponse=Mesh->GetCollisionResponseToChannel(ECC_Camera);
            Entry.CollisionProfile=Mesh->GetCollisionProfileName(); Entry.CollisionResponses=Mesh->GetCollisionResponseToChannels();
            Entry.CollisionEnabled=Mesh->GetCollisionEnabled(); Entry.CollisionObjectType=Mesh->GetCollisionObjectType();
            Entry.OriginalOverrides=Mesh->OverrideMaterials;
            for (int32 I=0; I<Variants.Num(); ++I)
            {
                Entry.OriginalMaterials.Add(Mesh->GetMaterial(I));
                UMaterialInstanceDynamic* MID=UMaterialInstanceDynamic::Create(Variants[I],this);
                MID->SetScalarParameterValue(OpacityParameter,1.f); Entry.FadeMaterials.Add(MID);
                Mesh->SetMaterial(I,MID);
            }
            // Only the camera probe ignores these walls. Pawn/projectile/visibility responses are unchanged.
            Mesh->SetCollisionResponseToChannel(ECC_Camera,ECR_Ignore);
            Entry.ManagedCollisionProfile=Mesh->GetCollisionProfileName(); Entry.ManagedOverrides=Mesh->OverrideMaterials;
            Occluders.Add(MoveTemp(Entry));
        }
    }
    ManagedOccluderCount=Occluders.Num();
}

bool UDinkInteriorCameraComponent::CalculateFraming(float ShoulderY,const FMatrix& Projection,FVector2D& Shift) const
{
    Shift=FVector2D::ZeroVector;
    const ADinkScreenVolume* Screen=CurrentScreen.Get();
    const TArray<FVector2D>* Polygon=Screen ? RoomFloors.Find(Screen->ScreenNumber) : nullptr;
    const double* FloorZ=Screen ? RoomFloorHeights.Find(Screen->ScreenNumber) : nullptr;
    if (!Polygon || !FloorZ || Polygon->Num()!=4) return false;
    const FRotator Rotation=Arm->GetTargetRotation();
    const FRotationMatrix Basis(Rotation);
    const FVector Forward=Basis.GetUnitAxis(EAxis::X),Right=Basis.GetUnitAxis(EAxis::Y),Up=Basis.GetUnitAxis(EAxis::Z);
    FVector Socket=OutdoorSocket+InteriorShoulderOffset; Socket.Y=OutdoorSocket.Y+ShoulderY;
    const FVector Eye=Arm->GetComponentLocation()+OutdoorPivot+InteriorPivotOffset-
        Forward*Arm->TargetArmLength+Rotation.RotateVector(Socket);
    if (Eye.Z<=*FloorZ+Arm->ProbeSize) return false;
    if (FMath::Abs(Projection.M[0][0])<1.e-8 || FMath::Abs(Projection.M[1][1])<1.e-8) return false;
    TArray<FVector2D> Hits;
    for (const double Side : {-1.,0.,1.})
    {
        const double X=(Side-Projection.M[2][0])/Projection.M[0][0];
        const double Y=(-1.-Projection.M[2][1])/Projection.M[1][1];
        const FVector Ray=Forward+Right*X+Up*Y;
        // Looking above the floor is legitimate; there is no bottom-edge floor ray to constrain.
        if (Ray.Z>=-1.e-7) return true;
        const FVector Hit=Eye+Ray*((*FloorZ-Eye.Z)/Ray.Z);
        Hits.Add(FVector2D(Hit.X,Hit.Y));
    }
    double Area=0;
    const FVector2D Origin=(*Polygon)[0];
    for (int32 I=1; I<3; ++I) Area+=FVector2D::CrossProduct((*Polygon)[I]-Origin,(*Polygon)[I+1]-Origin);
    if (!FMath::IsFinite(Area) || FMath::Abs(Area)<1.e-6) return false;
    const double Sign=Area>0 ? 1. : -1.;
    TArray<DinkCameraFraming::FPlane> Planes;
    const FVector2D EyeXY(Eye.X,Eye.Y);
    for (int32 I=0; I<4; ++I)
    {
        const FVector2D A=(*Polygon)[I],B=(*Polygon)[(I+1)%4],C=(*Polygon)[(I+2)%4];
        const FVector2D Edge=B-A;
        const double Length=Edge.Size();
        if (!FMath::IsFinite(Length) || Length<1.e-6 || FVector2D::CrossProduct(Edge,C-B)*Sign<=1.e-6) return false;
        const FVector2D Inward(-Sign*Edge.Y/Length,Sign*Edge.X/Length);
        // Forward walls already stop farther floor rays. Constrain only edges at/behind
        // the camera, where a faded near wall could expose the floating room's underside.
        if (FVector2D::DotProduct(Inward,EyeXY-A)>=5.) continue;
        double Need=-TNumericLimits<double>::Max();
        for (const FVector2D& Hit : Hits) Need=FMath::Max(Need,5.-FVector2D::DotProduct(Inward,Hit-A));
        Planes.Add({Inward,Need});
    }
    if (Planes.IsEmpty()) return true;
    // A room-edge adjustment must never solve the floor gap by pushing the camera into Dink.
    const double Depth=FVector::DotProduct(GetOwner()->GetActorLocation()-Eye,Forward);
    Planes.Add({FVector2D(-Forward.X,-Forward.Y),180.-Depth});
    return DinkCameraFraming::FindMinimumTranslation(Planes,150.,Shift);
}

void UDinkInteriorCameraComponent::UpdateFraming(float DeltaTime)
{
    const ADinkScreenVolume* Screen=CurrentScreen.Get();
    bFloorFramingAvailable=ManagedOccluderCount>0 && Screen && RoomFloors.Contains(Screen->ScreenNumber);
    bFloorFramingFeasible=true; FloorFramingShift=FVector::ZeroVector;
    if (!bFloorFramingAvailable) return;
    APlayerController* PC=Cast<APlayerController>(Cast<APawn>(GetOwner())->GetController());
    int32 Width=0,Height=0; if (PC) PC->GetViewportSize(Width,Height);
    if (Width<=0 || Height<=0) { bFloorFramingFeasible=false; Arm->TargetOffset=OutdoorPivot+InteriorPivotOffset; Arm->SocketOffset=OutdoorSocket+InteriorShoulderOffset; return; }
    FMinimalViewInfo View; Camera->GetCameraView(0.f,View);
    FSceneViewProjectionData Data; const FIntRect Rect(0,0,Width,Height); Data.SetViewRectangle(Rect);
    TEnumAsByte<EAspectRatioAxisConstraint> Axis=AspectRatio_MaintainXFOV;
    if (PC && PC->GetLocalPlayer()) Axis=PC->GetLocalPlayer()->AspectRatioAxisConstraint;
    if (Camera->bOverrideAspectRatioAxisConstraint) Axis=Camera->AspectRatioAxisConstraint;
    FMinimalViewInfo::CalculateProjectionMatrixGivenViewRectangle(View,Axis,Rect,Data);
    FVector2D Plus,Minus;
    const float Magnitude=FMath::Abs(InteriorShoulderOffset.Y);
    const bool PlusOK=CalculateFraming(Magnitude,Data.ProjectionMatrix,Plus);
    const bool MinusOK=CalculateFraming(-Magnitude,Data.ProjectionMatrix,Minus);
    if (!PlusOK && !MinusOK) { bFloorFramingFeasible=false; Arm->TargetOffset=OutdoorPivot+InteriorPivotOffset; Arm->SocketOffset=OutdoorSocket+InteriorShoulderOffset; return; }
    const double PlusScore=PlusOK ? Plus.SizeSquared()+(ShoulderTargetSign<0 ? 144. : 0.) : TNumericLimits<double>::Max();
    const double MinusScore=MinusOK ? Minus.SizeSquared()+(ShoulderTargetSign>0 ? 144. : 0.) : TNumericLimits<double>::Max();
    ShoulderTargetSign=MinusScore<PlusScore ? -1.f : 1.f;
    const FVector Position=GetOwner()->GetActorLocation();
    const bool Teleported=bSnapFraming || FVector::DistSquared(Position,PreviousPawnLocation)>FMath::Square(500.);
    CurrentShoulderY=Teleported ? ShoulderTargetSign*Magnitude :
        FMath::FInterpConstantTo(CurrentShoulderY,ShoulderTargetSign*Magnitude,DeltaTime,600.f);
    FVector2D Shift;
    if (!CalculateFraming(CurrentShoulderY,Data.ProjectionMatrix,Shift))
    {
        // If an intermediate shoulder position cannot satisfy both visibility and
        // readable distance, use the validated endpoint instead of an unsafe close view.
        CurrentShoulderY=ShoulderTargetSign*Magnitude; Shift=ShoulderTargetSign>0 ? Plus : Minus;
    }
    FloorFramingShift=FVector(Shift.X,Shift.Y,0);
    Arm->TargetOffset=OutdoorPivot+InteriorPivotOffset+FloorFramingShift;
    Arm->SocketOffset=OutdoorSocket+InteriorShoulderOffset; Arm->SocketOffset.Y=OutdoorSocket.Y+CurrentShoulderY;
    PreviousPawnLocation=Position; bSnapFraming=false;
}

void UDinkInteriorCameraComponent::UpdateOutdoorHeadroom()
{
    OutdoorHeadroomLift=0.f; OutdoorPortalArmCap=0.f; bOutdoorPortalFramingFeasible=true; OutdoorPortalOwner.Reset(); OutdoorPortalMeshSHA.Reset();
    Arm->TargetOffset=OutdoorPivot;
    // Match the native spring-arm sweep rather than extending through a blocker.
    // Lag/custom camera-local offsets need a different trajectory; leave their policy alone.
    if (!Arm->bDoCollisionTest || Arm->TargetArmLength<=0 || Arm->ProbeSize<=0 ||
        Arm->ProbeChannel!=ECC_Camera || Arm->bEnableCameraLag || Arm->bEnableCameraRotationLag ||
        !Camera->GetRelativeLocation().IsNearlyZero()) return;
    const UCapsuleComponent* Capsule=GetOwner()->FindComponentByClass<UCapsuleComponent>();
    const APawn* Pawn=Cast<APawn>(GetOwner());
    APlayerController* PC=Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
    int32 Width=0,Height=0; if (PC) PC->GetViewportSize(Width,Height);
    if (!Capsule || Width<=0 || Height<=0) return;
    const FRotator Rotation=Arm->GetTargetRotation();
    const FVector Pivot=Arm->GetComponentLocation()+OutdoorPivot;
    FVector Desired=Pivot-Rotation.Vector()*Arm->TargetArmLength+Rotation.RotateVector(Arm->SocketOffset);
    const FCollisionShape Shape=FCollisionShape::MakeSphere(Arm->ProbeSize);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkOutdoorHeadroom),false,GetOwner());
    FMinimalViewInfo View; Camera->GetCameraView(0.f,View);
    if (View.ProjectionMode!=ECameraProjectionMode::Perspective) return;
    const FIntRect Rect(0,0,Width,Height);
    FSceneViewProjectionData Projection; Projection.SetViewRectangle(Rect);
    TEnumAsByte<EAspectRatioAxisConstraint> Axis=AspectRatio_MaintainXFOV;
    if (PC->GetLocalPlayer()) Axis=PC->GetLocalPlayer()->AspectRatioAxisConstraint;
    if (Camera->bOverrideAspectRatioAxisConstraint) Axis=Camera->AspectRatioAxisConstraint;
    FMinimalViewInfo::CalculateProjectionMatrixGivenViewRectangle(View,Axis,Rect,Projection);
    const FQuat ViewRotation=Rotation.Quaternion()*Camera->GetRelativeRotation().Quaternion();
    const FVector Forward=ViewRotation.GetForwardVector(),Up=ViewRotation.GetUpVector();
    const FVector Top=Capsule->GetComponentLocation()+FVector(0,0,Capsule->GetScaledCapsuleHalfHeight());
    const double Maximum=Capsule->GetScaledCapsuleHalfHeight();
    constexpr double MarginNDC=.2; // Keep the capsule top within the upper90% of screen height.
    // A clear physical door aperture can put an outdoor camera in the hollow shell.
    // This is an authored presentation boundary, never a fabricated collision hit.
    DinkCameraPortal::FLimit Portal;
    bool PortalActive=false;
    const ADinkScreenVolume* Screen=CurrentScreen.Get();
    UDinkArtSubsystem* Art=GetWorld()->GetSubsystem<UDinkArtSubsystem>();
    const double Near=View.GetFinalPerspectiveNearClipPlane();
    const double PX=Projection.ProjectionMatrix.M[0][0],PY=Projection.ProjectionMatrix.M[1][1];
    if(!bEnableWallCutaway&&Screen&&Art&&Arm->SocketOffset.IsNearlyZero()&&Camera->GetRelativeRotation().IsNearlyZero()&&PX>0&&PY>0&&Near>0)
    {
        const double Corner=Near*FMath::Sqrt(FMath::Square((1.+FMath::Abs(Projection.ProjectionMatrix.M[2][0]))/PX)+
                                           FMath::Square((1.+FMath::Abs(Projection.ProjectionMatrix.M[2][1]))/PY));
        const double Clearance=FMath::Max(double(Arm->ProbeSize),Corner);
        const bool Registered=Art->ExteriorCameraLimit(*Screen,Pivot,Desired,Arm->ProbeSize,Clearance,Portal);
        PortalActive=Registered&&!Portal.bInfeasible;
        if(Registered&&Portal.bInfeasible){OutdoorPortalOwner=Portal.Owner; OutdoorPortalMeshSHA=Portal.MeshSourceSHA;bOutdoorPortalFramingFeasible=false;}
        if(PortalActive)
        {
            OutdoorPortalOwner=Portal.Owner; OutdoorPortalMeshSHA=Portal.MeshSourceSHA;
            Arm->TargetArmLength*=Portal.Fraction;OutdoorPortalArmCap=Arm->TargetArmLength;
            Desired=Pivot-Rotation.Vector()*Arm->TargetArmLength+Rotation.RotateVector(Arm->SocketOffset);
        }
    }
    FHitResult BaseHit;
    const bool PhysicalHit=GetWorld()->SweepSingleByChannel(BaseHit,Pivot,Desired,FQuat::Identity,Arm->ProbeChannel,Shape,Params)&&BaseHit.Time<1.f;
    if(PhysicalHit&&BaseHit.bStartPenetrating){if(PortalActive)bOutdoorPortalFramingFeasible=false;return;}
    if(!PhysicalHit&&!PortalActive)return;
    FVector Eye=PhysicalHit ? BaseHit.Location : Desired;
    double Lift=0;
    for (int32 Attempt=0; Attempt<3; ++Attempt)
    {
        double More=0;
        if (!DinkCameraHeadroom::MinimumLift(Top,Eye,Forward,Up,Projection.ProjectionMatrix.M[1][1],
            Projection.ProjectionMatrix.M[2][1],MarginNDC,Maximum-Lift,More)) { if(PortalActive)bOutdoorPortalFramingFeasible=false; return; }
        if (More<=1.e-5)
        {
            const bool Readable=FVector::DotProduct(Top-Eye,Forward)>Near+1.e-4;
            if(PortalActive&&(!Portal.Outside(Eye)||!Readable)){bOutdoorPortalFramingFeasible=false;return;}
            if (Lift>0) { OutdoorHeadroomLift=Lift; Arm->TargetOffset=OutdoorPivot+FVector(0,0,Lift); }
            return;
        }
        Lift+=More+.25; // Numerical clearance, still inside the capsule-derived bound.
        if (Lift>Maximum) { if(PortalActive)bOutdoorPortalFramingFeasible=false; return; }
        const FVector Offset(0,0,Lift);
        FHitResult PivotHit,Candidate;
        if (GetWorld()->SweepSingleByChannel(PivotHit,Pivot,Pivot+Offset,FQuat::Identity,Arm->ProbeChannel,Shape,Params)) { if(PortalActive)bOutdoorPortalFramingFeasible=false; return; }
        const bool CandidateHit=GetWorld()->SweepSingleByChannel(Candidate,Pivot+Offset,Desired+Offset,FQuat::Identity,Arm->ProbeChannel,Shape,Params)&&Candidate.Time<1.f;
        if(CandidateHit&&Candidate.bStartPenetrating){if(PortalActive)bOutdoorPortalFramingFeasible=false;return;}
        if(PhysicalHit&&(!CandidateHit||Candidate.GetComponent()!=BaseHit.GetComponent()||
           FVector::DotProduct(Candidate.ImpactNormal,BaseHit.ImpactNormal)<.5||
           !DinkCameraHeadroom::PreservesExteriorFace(BaseHit.Location,Candidate.Location,BaseHit.ImpactPoint,BaseHit.ImpactNormal)))
        {if(PortalActive)bOutdoorPortalFramingFeasible=false;return;}
        Eye=CandidateHit ? Candidate.Location : Desired+Offset;
        if(PortalActive&&!Portal.Outside(Eye)){bOutdoorPortalFramingFeasible=false;return;}
    }
    if(PortalActive)bOutdoorPortalFramingFeasible=false;
}

void UDinkInteriorCameraComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(DeltaTime,TickType,TickFunction);
    if (!Arm || !Camera) return;
    const APawn* Pawn=Cast<APawn>(GetOwner());
    if (!Pawn || !Pawn->IsLocallyControlled() || Pawn->GetController()!=GetWorld()->GetFirstPlayerController())
    {
        if (bInteriorMode || !Occluders.IsEmpty() || OutdoorHeadroomLift>0 || OutdoorPortalArmCap>0 || !bOutdoorPortalFramingFeasible) SelectScreen(nullptr);
        return;
    }
    UDinkGreyboxSubsystem* Grey=GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>();
    ADinkScreenVolume* Screen=Grey ? Grey->GetCurrentScreen() : nullptr;
    if (!bSelectedScreen || Screen!=CurrentScreen.Get() || bAppliedCutaway!=bEnableWallCutaway) SelectScreen(Screen);
    const float PreviousNominal=OutdoorPortalArmCap>0 ? UncappedOutdoorArm : Arm->TargetArmLength;
    Arm->TargetArmLength = FMath::FInterpTo(PreviousNominal, GetDesiredArmLength(), DeltaTime, 10.f);
    UncappedOutdoorArm=Arm->TargetArmLength;
    if (bInteriorMode) { OutdoorHeadroomLift=0.f; UpdateFraming(DeltaTime); }
    else UpdateOutdoorHeadroom();
    if (Occluders.IsEmpty()) return;
    const FRotator Rotation=Arm->GetTargetRotation();
    const FVector Pivot=Arm->GetComponentLocation()+Arm->TargetOffset;
    const FVector Eye=Pivot-Rotation.Vector()*Arm->TargetArmLength+Rotation.RotateVector(Arm->SocketOffset);
    const FVector Body=GetOwner()->GetActorLocation();
    const FVector Side=Rotation.RotateVector(FVector(0,22,0));
    const FVector Targets[]={Body+FVector(0,0,60),Body,Body-FVector(0,0,60),Body+Side,Body-Side};
    // Cover foreground geometry off the body silhouette using the actual player
    // projection. Inscribed complex-component sweeps leave real apertures clear.
    TArray<DinkCameraOcclusion::FSweep> ForegroundSweeps;
    APlayerController* PC=Cast<APlayerController>(Pawn->GetController());
    int32 Width=0,Height=0; if (PC) PC->GetViewportSize(Width,Height);
    const UCapsuleComponent* Capsule=GetOwner()->FindComponentByClass<UCapsuleComponent>();
    if (Width>0 && Height>0 && Capsule)
    {
        FMinimalViewInfo View; Camera->GetCameraView(0.f,View);
        View.Location=Eye; View.Rotation=Rotation;
        const FIntRect Rect(0,0,Width,Height);
        FSceneViewProjectionData Projection; Projection.SetViewRectangle(Rect);
        TEnumAsByte<EAspectRatioAxisConstraint> Axis=AspectRatio_MaintainXFOV;
        if (PC->GetLocalPlayer()) Axis=PC->GetLocalPlayer()->AspectRatioAxisConstraint;
        if (Camera->bOverrideAspectRatioAxisConstraint) Axis=Camera->AspectRatioAxisConstraint;
        FMinimalViewInfo::CalculateProjectionMatrixGivenViewRectangle(View,Axis,Rect,Projection);
        const double FarDepth=FVector::DotProduct(Body-Eye,Rotation.Vector())-Capsule->GetScaledCapsuleRadius();
        DinkCameraOcclusion::BuildForegroundSweeps(Eye,Rotation,Projection.ProjectionMatrix,
            View.GetFinalPerspectiveNearClipPlane(),FarDepth,ForegroundSweeps);
    }
    FCollisionQueryParams Params(TEXT("DinkCameraOcclusion"),true,GetOwner());
    FadingOccluderCount=0;
    for (FDinkCameraOccluder& Entry : Occluders)
    {
        if (!IsValid(Entry.Component)) continue;
        const FBox Box=Entry.Component->Bounds.GetBox();
        bool bBlocks=false;
        const float Clearance=Arm->ProbeSize+6.f;
        if (Box.ExpandBy(Clearance).IsInside(Eye))
        {
            // Bounds alone include empty doorway/window apertures. Test the actual
            // near-camera sphere against this component before fading its surfaces.
            FHitResult NearHit;
            bBlocks=Entry.Component->SweepComponent(NearHit,Eye,Eye+FVector(.01,0,0),
                FQuat::Identity,FCollisionShape::MakeSphere(Clearance),true);
        }
        for (const FVector& Target : Targets)
        {
            if (bBlocks) break;
            if (!FMath::LineBoxIntersection(Box,Eye,Target,Target-Eye)) continue;
            FHitResult Hit;
            bBlocks=Entry.Component->LineTraceComponent(Hit,Eye,Target,Params);
        }
        if (!bBlocks) bBlocks=DinkCameraOcclusion::Intersects(Entry.Component,ForegroundSweeps);
        Entry.Opacity=FMath::FInterpConstantTo(Entry.Opacity,bBlocks ? 0.f : 1.f,DeltaTime,bBlocks ? 5.f : 3.f);
        if (Entry.Opacity<.999f) ++FadingOccluderCount;
        for (UMaterialInstanceDynamic* MID : Entry.FadeMaterials) if (MID) MID->SetScalarParameterValue(OpacityParameter,Entry.Opacity);
    }
}

void UDinkInteriorCameraComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    RestoreOccluders(); RestoreCamera();
    if (Arm) Arm->RemoveTickPrerequisiteComponent(this);
    Super::EndPlay(Reason);
}
