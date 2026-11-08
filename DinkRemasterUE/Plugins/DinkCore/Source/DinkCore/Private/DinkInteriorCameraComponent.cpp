#include "DinkInteriorCameraComponent.h"
#include "DinkCoreModule.h"
#include "DinkCameraFraming.h"
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
    OutdoorArm = Arm->TargetArmLength; OutdoorPivot = Arm->TargetOffset;
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

void UDinkInteriorCameraComponent::RestoreCamera()
{
    FloorFramingShift=FVector::ZeroVector; bFloorFramingAvailable=false; bFloorFramingFeasible=true;
    if (Arm) { Arm->TargetArmLength=OutdoorArm; Arm->TargetOffset=OutdoorPivot; Arm->SocketOffset=OutdoorSocket; }
    if (Camera) Camera->SetFieldOfView(OutdoorFOV);
}

void UDinkInteriorCameraComponent::RestoreOccluders()
{
    for (FDinkCameraOccluder& Entry : Occluders)
    {
        if (!IsValid(Entry.Component)) continue;
        bool bStillOwned=true;
        for (int32 I=0; I<Entry.OriginalMaterials.Num(); ++I)
            bStillOwned &= Entry.Component->GetMaterial(I)==Entry.FadeMaterials[I];
        if (bStillOwned)
        {
            Entry.Component->OverrideMaterials=Entry.OriginalOverrides;
            Entry.Component->MarkRenderStateDirty();
        }
        else for (int32 I=0; I<Entry.OriginalMaterials.Num(); ++I)
        {
            if (Entry.Component->GetMaterial(I)==Entry.FadeMaterials[I]) Entry.Component->SetMaterial(I,Entry.OriginalMaterials[I]);
        }
        FCollisionResponseContainer Expected=Entry.CollisionResponses;
        Expected.SetResponse(ECC_Camera,ECR_Ignore);
        if (Entry.Component->GetCollisionResponseToChannels()==Expected)
            Entry.Component->SetCollisionProfileName(Entry.CollisionProfile);
        Entry.Component->SetCollisionResponseToChannel(ECC_Camera,Entry.CameraResponse);
    }
    Occluders.Reset(); FadingOccluderCount=0; ManagedOccluderCount=0;
}

void UDinkInteriorCameraComponent::SelectScreen(ADinkScreenVolume* Screen)
{
    RestoreOccluders(); CurrentScreen=Screen; bSelectedScreen=true;
    bInteriorMode = Screen && Screen->bIndoor;
    if (!bInteriorMode) { RestoreCamera(); return; }
    Arm->TargetArmLength=InteriorArmLength; Arm->TargetOffset=OutdoorPivot+InteriorPivotOffset;
    Arm->SocketOffset=OutdoorSocket+InteriorShoulderOffset; Camera->SetFieldOfView(InteriorFieldOfView);
    ShoulderTargetSign=1.f; CurrentShoulderY=InteriorShoulderOffset.Y; bSnapFraming=true;
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

void UDinkInteriorCameraComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(DeltaTime,TickType,TickFunction);
    if (!Arm || !Camera) return;
    const APawn* Pawn=Cast<APawn>(GetOwner());
    if (!Pawn || !Pawn->IsLocallyControlled() || Pawn->GetController()!=GetWorld()->GetFirstPlayerController())
    {
        if (bInteriorMode) SelectScreen(nullptr);
        return;
    }
    UDinkGreyboxSubsystem* Grey=GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>();
    ADinkScreenVolume* Screen=Grey ? Grey->GetCurrentScreen() : nullptr;
    if (!bSelectedScreen || Screen!=CurrentScreen.Get()) SelectScreen(Screen);
    if (!bInteriorMode) return;
    UpdateFraming(DeltaTime);
    const FRotator Rotation=Arm->GetTargetRotation();
    const FVector Pivot=Arm->GetComponentLocation()+Arm->TargetOffset;
    const FVector Eye=Pivot-Rotation.Vector()*Arm->TargetArmLength+Rotation.RotateVector(Arm->SocketOffset);
    const FVector Body=GetOwner()->GetActorLocation();
    const FVector Side=Rotation.RotateVector(FVector(0,22,0));
    const FVector Targets[]={Body+FVector(0,0,60),Body,Body-FVector(0,0,60),Body+Side,Body-Side};
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
