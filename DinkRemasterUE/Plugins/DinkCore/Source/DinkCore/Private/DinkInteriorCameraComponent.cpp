#include "DinkInteriorCameraComponent.h"
#include "DinkPerfScope.h"
#include "UObject/StrongObjectPtr.h"
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
#include "GameFramework/Character.h"
#include "Components/SkeletalMeshComponent.h"
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
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/StaticMesh.h"
#include "HAL/IConsoleManager.h"
#include "Materials/Material.h"
#include "UObject/UObjectIterator.h"

namespace
{
const FName OpacityParameter(TEXT("DinkCameraOpacity"));
const FName FoliageProxyTag(TEXT("DinkCameraFoliageProxy"));
TAutoConsoleVariable<int32> CVarDinkCameraFoliageFade(TEXT("dink.CameraFoliageFade"), 1,
    TEXT("1: trees and tall bushes between the play camera and Dink fade (dithered, their shadows stay; DinkCameraFoliage.h). ")
    TEXT("0: off, the look before 15 Nov 2026 (the camera may stand in a pine crown). Presentation only."));
}

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
        const TSharedPtr<FJsonObject>* Foliage=nullptr;
        if (Schema==TEXT("dink-camera/1") && Config->TryGetObjectField(TEXT("foliage_variants"),Foliage))
        {
            for (const auto& Pair : (*Foliage)->Values)
            {
                FString Path; if (Pair.Value->TryGetString(Path)) FoliageVariants.Add(FString(*Pair.Key).ToLower(), Path);
            }
            // perf-stutter: the camera-fade variants loaded synchronously the first time a tree came between camera and Dink
            // (on screen entry, Dink.Perf.ScreenEntry.NoSyncLoads); load them here, at begin play, and keep them resident
            if (DinkPerf::FixesEnabled())
            {
                static TArray<TStrongObjectPtr<UMaterialInterface>> Resident;
                for (const TPair<FString, FString>& Pair : FoliageVariants)
                    if (UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, *Pair.Value, nullptr, LOAD_NoWarn | LOAD_Quiet))
                        Resident.Add(TStrongObjectPtr<UMaterialInterface>(M));
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
    ReleaseInteriorClearance();
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

void UDinkInteriorCameraComponent::SetHeroHidden(bool bHidden)
{
    if (bInteriorHeroHidden==bHidden) return;
    bInteriorHeroHidden=bHidden;
    const ACharacter* Hero=Cast<ACharacter>(GetOwner());
    USkeletalMeshComponent* Body=Hero ? Hero->GetMesh() : nullptr;
    if (!Body) return;
    // the body and everything drawn on it (hair, clothes, held items), for the owner's view only
    TArray<USceneComponent*> Parts; Body->GetChildrenComponents(true,Parts); Parts.Add(Body);
    for (USceneComponent* Part : Parts) if (UPrimitiveComponent* P=Cast<UPrimitiveComponent>(Part)) P->SetOwnerNoSee(bHidden);
}

void UDinkInteriorCameraComponent::ReleaseInteriorClearance()
{
    SetHeroHidden(false);
    if (!Arm) return;
    if (InteriorClearLift!=0.f && Arm->TargetOffset.Equals(InteriorClearAppliedOffset)) Arm->TargetOffset-=FVector(0,0,InteriorClearLift);
    if (!Arm->bUsePawnControlRotation) Arm->bUsePawnControlRotation=true;
    InteriorClearPitch=0.f; InteriorClearLift=0.f; InteriorClearArm=0.f;
}

void UDinkInteriorCameraComponent::UpdateInteriorClearance(float DeltaTime)
{
    // A62 (25 Nov 2026): see the header. The base pivot is what SelectScreen/UpdateFraming set this tick; this rule only adds to it.
    const APawn* Pawn=Cast<APawn>(GetOwner());
    const AController* Controller=Pawn ? Pawn->GetController() : nullptr;
    const UCapsuleComponent* Capsule=GetOwner()->FindComponentByClass<UCapsuleComponent>();
    // the base offset: what this rule added last tick comes off again, unless SelectScreen/UpdateFraming set the offset anew
    if (InteriorClearLift!=0.f && Arm->TargetOffset.Equals(InteriorClearAppliedOffset)) Arm->TargetOffset-=FVector(0,0,InteriorClearLift);
    if (!Controller || !Capsule || !Arm->bDoCollisionTest || Arm->TargetArmLength<=0 || Arm->bEnableCameraLag || Arm->bEnableCameraRotationLag)
    {
        ReleaseInteriorClearance(); return;
    }
    const FRotator Control=Controller->GetControlRotation();
    const double ControlPitch=FRotator::NormalizeAxis(Control.Pitch);
    const FVector Base=Arm->GetComponentLocation()+Arm->TargetOffset;
    const FCollisionShape Shape=FCollisionShape::MakeSphere(Arm->ProbeSize);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkInteriorClearance),false,GetOwner());
    const double Length=Arm->TargetArmLength;
    // the clear length of the arm from a pivot lifted by Lift along a pitch (0 when the pivot itself cannot be raised there)
    auto Clear=[&](double Pitch,double Lift)
    {
        const FVector Pivot=Base+FVector(0,0,Lift);
        FHitResult Hit;
        if (Lift>0 && GetWorld()->SweepSingleByChannel(Hit,Base,Pivot,FQuat::Identity,Arm->ProbeChannel,Shape,Params)) return 0.0;
        const FRotator R(Pitch,Control.Yaw,0.);
        const FVector Desired=Pivot-R.Vector()*Length+R.RotateVector(Arm->SocketOffset);
        if (!GetWorld()->SweepSingleByChannel(Hit,Pivot,Desired,FQuat::Identity,Arm->ProbeChannel,Shape,Params)) return FVector::Dist(Pivot,Desired);
        return Hit.bStartPenetrating ? 0.0 : Hit.Time*FVector::Dist(Pivot,Desired);
    };
    const ACharacter* Hero=Cast<ACharacter>(GetOwner());
    const USkeletalMeshComponent* Body=Hero ? Hero->GetMesh() : nullptr;
    const FVector Head=Body && Body->GetBoneIndex(TEXT("head"))!=INDEX_NONE ? Body->GetSocketLocation(TEXT("head")) : Capsule->GetComponentLocation()+FVector(0,0,Capsule->GetScaledCapsuleHalfHeight()*.7);
    // where the eye of a pitch / lift ends (the arm stops at its clear length) and how far that is from Dink's head
    auto EyeAt=[&](double Pitch,double Lift,double Reach)
    {
        const FRotator R(Pitch,Control.Yaw,0.);
        return Base+FVector(0,0,Lift)-R.Vector()*Reach+R.RotateVector(Arm->SocketOffset)*(Reach/FMath::Max(Length,1.));
    };
    const double Own=Clear(ControlPitch,0.);
    double BestPitch=ControlPitch,BestLift=0.,Best=Own;
    if (Own<InteriorMinimumClearArm)
    {
        // least change first (a steeper pitch, then a higher pivot) that clears the minimum arm; else the eye farthest from his head
        const double OwnHead=FVector::Dist(EyeAt(ControlPitch,0.,Own),Head);
        double BestHead=OwnHead;
        bool bFound=false;
        for (int32 Step=0; Step<=4 && !bFound; ++Step)
        {
            const double Lift=InteriorMaximumClearLift*Step/4.;
            for (double Pitch=FMath::Min(ControlPitch,0.)-5.; Pitch>=InteriorMaximumClearPitch-.01 && !bFound; Pitch-=5.)
            {
                const double Got=Clear(Pitch,Lift);
                if (Got>=InteriorMinimumClearArm) { Best=Got; BestPitch=Pitch; BestLift=Lift; bFound=true; break; }
                const double ToHead=FVector::Dist(EyeAt(Pitch,Lift,Got),Head);
                if (Got>0. && ToHead>BestHead) { BestHead=ToHead; Best=Got; BestPitch=Pitch; BestLift=Lift; }
            }
        }
        if (!bFound && BestHead<OwnHead+20.) { BestPitch=ControlPitch; BestLift=0.; Best=Own; }
    }
    // ease the pitch and the lift (no jump when Dink backs into a wall), snap when the rule lets go
    const float WantPitch=float(BestPitch-ControlPitch), WantLift=float(BestLift);
    InteriorClearPitch=FMath::FInterpTo(InteriorClearPitch,WantPitch,DeltaTime,8.f);
    const float Lift=FMath::FInterpTo(InteriorClearLift,WantLift,DeltaTime,8.f);
    if (FMath::Abs(InteriorClearPitch)<.05f && WantPitch==0.f) InteriorClearPitch=0.f;
    InteriorClearLift=(FMath::Abs(Lift)<.05f && WantLift==0.f) ? 0.f : Lift;
    InteriorClearArm=float(Best);
    Arm->TargetOffset+=FVector(0,0,InteriorClearLift);
    InteriorClearAppliedOffset=Arm->TargetOffset;
    if (InteriorClearPitch!=0.f)
    {
        Arm->bUsePawnControlRotation=false;
        Arm->SetWorldRotation(FRotator(ControlPitch+InteriorClearPitch,Control.Yaw,0.));
    }
    else if (!Arm->bUsePawnControlRotation) Arm->bUsePawnControlRotation=true;
    // never draw the frame from inside Dink's head: the eye this view will have, against his head
    const FRotator Final(ControlPitch+InteriorClearPitch,Control.Yaw,0.);
    const FVector Pivot=Base+FVector(0,0,InteriorClearLift);
    const double Reach=FMath::Min(double(Clear(Final.Pitch,InteriorClearLift)),Length);
    const FVector Eye=Pivot-Final.Vector()*Reach+Final.RotateVector(Arm->SocketOffset)*(Reach/FMath::Max(Length,1.));
    SetHeroHidden(FVector::Dist(Eye,Head)<InteriorHeadClearance);
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
	DINK_PERF_SCOPE(Dink_InteriorCamera_Tick);
    Super::TickComponent(DeltaTime,TickType,TickFunction);
    if (!Arm || !Camera) return;
    const APawn* Pawn=Cast<APawn>(GetOwner());
    if (!Pawn || !Pawn->IsLocallyControlled() || Pawn->GetController()!=GetWorld()->GetFirstPlayerController())
    {
        if (bInteriorMode || !Occluders.IsEmpty() || OutdoorHeadroomLift>0 || OutdoorPortalArmCap>0 || !bOutdoorPortalFramingFeasible) SelectScreen(nullptr);
        if (!FoliageFades.IsEmpty()) RestoreFoliage();
        return;
    }
    UDinkGreyboxSubsystem* Grey=GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>();
    ADinkScreenVolume* Screen=Grey ? Grey->GetCurrentScreen() : nullptr;
    if (!bSelectedScreen || Screen!=CurrentScreen.Get() || bAppliedCutaway!=bEnableWallCutaway) SelectScreen(Screen);
    const float PreviousNominal=OutdoorPortalArmCap>0 ? UncappedOutdoorArm : Arm->TargetArmLength;
    Arm->TargetArmLength = FMath::FInterpTo(PreviousNominal, GetDesiredArmLength(), DeltaTime, 10.f);
    UncappedOutdoorArm=Arm->TargetArmLength;
    if (bInteriorMode) { OutdoorHeadroomLift=0.f; UpdateFraming(DeltaTime); UpdateInteriorClearance(DeltaTime); }
    else { ReleaseInteriorClearance(); UpdateOutdoorHeadroom(); }
    UpdateFoliage(DeltaTime);
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
    RestoreOccluders(); RestoreCamera(); RestoreFoliage();
    if (Arm) Arm->RemoveTickPrerequisiteComponent(this);
    Super::EndPlay(Reason);
}

// ---------------------------------------------------------------------------------------------------------------------
// Foliage between the camera and Dink (15 Nov 2026). Trees carry no collision, so the boom never shortens for them and
// the view stays steady; instead a crown in the way fades through its material's camera variant (camera_materials.json
// "foliage_variants": the same graph with DinkCameraOpacity on a dithered mask and the shadow pass left whole).

bool UDinkInteriorCameraComponent::FoliageSupported(UStaticMeshComponent& Component)
{
    if (!Component.GetStaticMesh() || Component.GetNumMaterials()==0 || Component.ComponentHasTag(FoliageProxyTag)) return false;
    for (int32 I=0; I<Component.GetNumMaterials(); ++I)
    {
        UMaterialInterface* Material=Component.GetMaterial(I);
        if (!Material) return false;
        if (const bool* Known=FoliageMaterialSupported.Find(Material)) { if (!*Known) return false; continue; }
        bool bSupported=false;
        if (UMaterial* Base=Material->GetMaterial())
        {
            if (const TObjectPtr<UMaterialInterface>* Variant=FoliageVariantByBase.Find(Base)) bSupported=*Variant!=nullptr;
            else if (const FString* Path=FoliageVariants.Find(Base->GetPathName().ToLower()))
            {
                UMaterialInterface* Loaded=LoadObject<UMaterialInterface>(nullptr,**Path,nullptr,LOAD_NoWarn|LOAD_Quiet);
                float Default=0.f;
                if (Loaded && (Loaded->GetBlendMode()!=BLEND_Masked ||
                    !Loaded->GetScalarParameterValue(FMaterialParameterInfo(OpacityParameter),Default) || !FMath::IsNearlyEqual(Default,1.f)))
                {
                    UE_LOG(LogDink,Warning,TEXT("Camera foliage fade: %s is not a masked variant with %s = 1; %s keeps blocking the view"),
                        **Path,*OpacityParameter.ToString(),*Base->GetName());
                    Loaded=nullptr;
                }
                FoliageVariantByBase.Add(Base,Loaded);
                bSupported=Loaded!=nullptr;
            }
        }
        FoliageMaterialSupported.Add(Material,bSupported);
        if (!bSupported) return false;
    }
    return true;
}

void UDinkInteriorCameraComponent::GatherFoliage()
{
    FoliageCandidates.Reset();
    UWorld* World=GetWorld();
    if (!World || !GetOwner()) return;
    const double Start=FPlatformTime::Seconds();
    const FVector Here=GetOwner()->GetActorLocation();
    constexpr double Range=3000.0;
    const FBox Around(Here-FVector(Range,Range,Range),Here+FVector(Range,Range,Range));
    for (TObjectIterator<UStaticMeshComponent> It; It; ++It)
    {
        UStaticMeshComponent* Component=*It;
        if (!IsValid(Component) || Component->GetWorld()!=World || !Component->IsRegistered() || !Component->IsVisible() ||
            Component->bHiddenInGame || Component->ComponentHasTag(FoliageProxyTag)) continue;
        UStaticMesh* Mesh=Component->GetStaticMesh();
        if (!Mesh || !Component->Bounds.GetBox().Intersect(Around)) continue;
        if (const AActor* Owner=Component->GetOwner(); Owner && Owner->IsHidden()) continue;
        const FBox Local=Mesh->GetBoundingBox();
        UInstancedStaticMeshComponent* Instanced=Cast<UInstancedStaticMeshComponent>(Component);
        // Instances scale about 0.85-1.2 (forest): a mesh far too low even at 1.5 x is grass or fern.
        if (Local.GetSize().Z*Component->GetComponentScale().GetAbsMax()*(Instanced ? 1.5 : 1.0)<DinkCameraFoliage::MinimumHeightCm) continue;
        if (!FoliageSupported(*Component)) continue;
        if (Instanced)
        {
            for (int32 Index=0; Index<Instanced->GetInstanceCount(); ++Index)
            {
                FTransform Transform;
                if (!Instanced->GetInstanceTransform(Index,Transform,true)) continue;
                // A fading instance is shrunk to nothing: its crown is where it stood.
                for (const FDinkFoliageFade& Fade : FoliageFades) if (Fade.Source==Component && Fade.Instance==Index) Transform=Fade.InstanceTransform;
                if (FVector::DistSquaredXY(Transform.GetLocation(),Here)>Range*Range) continue;
                DinkCameraFoliage::FCrown Crown;
                if (DinkCameraFoliage::CrownFromBounds(Local,Transform,Crown)) FoliageCandidates.Add({Component,Index,Crown});
            }
        }
        else
        {
            DinkCameraFoliage::FCrown Crown;
            if (DinkCameraFoliage::CrownFromBounds(Local,Component->GetComponentTransform(),Crown)) FoliageCandidates.Add({Component,INDEX_NONE,Crown});
        }
    }
    FoliageCandidateCount=FoliageCandidates.Num();
    const double Ms=(FPlatformTime::Seconds()-Start)*1000.0;
    UE_LOG(LogDink,Verbose,TEXT("Camera foliage: %d crowns near Dink (%.1f ms)"),FoliageCandidateCount,Ms);
}

bool UDinkInteriorCameraComponent::BeginFoliageFade(FDinkFoliageFade& Entry)
{
    UStaticMeshComponent* Target=Entry.Source;
    UInstancedStaticMeshComponent* Instanced=Cast<UInstancedStaticMeshComponent>(Entry.Source.Get());
    if (!IsValid(Target)) return false;
    if (Entry.Instance!=INDEX_NONE)
    {
        AActor* Owner=Instanced ? Instanced->GetOwner() : nullptr;
        if (!Owner || !Instanced->IsValidInstance(Entry.Instance) || !Instanced->GetInstanceTransform(Entry.Instance,Entry.InstanceTransform,true)) return false;
        // The instance is drawn by a stand-in at its place while it fades (one instance cannot take its own material).
        UStaticMeshComponent* Proxy=NewObject<UStaticMeshComponent>(Owner,NAME_None,RF_Transient);
        Proxy->SetMobility(EComponentMobility::Movable);
        Proxy->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
        Proxy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Proxy->SetGenerateOverlapEvents(false);
        Proxy->SetCanEverAffectNavigation(false);
        Proxy->ComponentTags.Add(FoliageProxyTag);
        Proxy->SetStaticMesh(Instanced->GetStaticMesh());
        Proxy->CastShadow=Instanced->CastShadow;
        Proxy->bCastDynamicShadow=Instanced->bCastDynamicShadow;
        Proxy->LightingChannels=Instanced->LightingChannels;
        Proxy->SetUsingAbsoluteLocation(true); Proxy->SetUsingAbsoluteRotation(true); Proxy->SetUsingAbsoluteScale(true);
        Proxy->SetWorldTransform(Entry.InstanceTransform);
        for (int32 I=0; I<Instanced->GetNumMaterials(); ++I) Proxy->SetMaterial(I,Instanced->GetMaterial(I));
        Proxy->RegisterComponent();
        const TArray<float>& Data=Instanced->GetCustomPrimitiveData().Data;
        for (int32 K=0; K<Data.Num(); ++K) Proxy->SetCustomPrimitiveDataFloat(K,Data[K]);
        Entry.Proxy=Proxy;
        Target=Proxy;
    }
    Entry.OriginalOverrides=Target->OverrideMaterials;
    for (int32 I=0; I<Target->GetNumMaterials(); ++I)
    {
        UMaterialInterface* Original=Target->GetMaterial(I);
        UMaterial* Base=Original ? Original->GetMaterial() : nullptr;
        const TObjectPtr<UMaterialInterface>* Variant=Base ? FoliageVariantByBase.Find(Base) : nullptr;
        if (!Variant || !*Variant)
        {
            if (Entry.Proxy) { Entry.Proxy->DestroyComponent(); Entry.Proxy=nullptr; }
            Entry.FadeMaterials.Reset();
            return false;
        }
        UMaterialInstanceDynamic* MID=UMaterialInstanceDynamic::Create(*Variant,this);
        MID->CopyMaterialUniformParameters(Original);
        MID->SetScalarParameterValue(OpacityParameter,1.f);
        Entry.FadeMaterials.Add(MID);
    }
    for (int32 I=0; I<Entry.FadeMaterials.Num(); ++I) Target->SetMaterial(I,Entry.FadeMaterials[I]);
    if (Entry.Proxy)
    {
        FTransform Gone=Entry.InstanceTransform;
        Gone.SetScale3D(FVector(1.e-4));
        Instanced->UpdateInstanceTransform(Entry.Instance,Gone,true,true,true);
    }
    Entry.Opacity=1.f;
    return true;
}

void UDinkInteriorCameraComponent::EndFoliageFade(FDinkFoliageFade& Entry)
{
    if (Entry.Proxy)
    {
        if (UInstancedStaticMeshComponent* Instanced=Cast<UInstancedStaticMeshComponent>(Entry.Source.Get()); IsValid(Instanced) && Instanced->IsValidInstance(Entry.Instance))
            Instanced->UpdateInstanceTransform(Entry.Instance,Entry.InstanceTransform,true,true,true);
        Entry.Proxy->DestroyComponent();
        Entry.Proxy=nullptr;
    }
    else if (IsValid(Entry.Source))
    {
        bool bChanged=false;
        for (int32 I=0; I<Entry.FadeMaterials.Num(); ++I)
        {
            // Give back only the slots that still show this fade (another layer may have set its own material since).
            if (!Entry.Source->OverrideMaterials.IsValidIndex(I) || Entry.Source->OverrideMaterials[I]!=Entry.FadeMaterials[I]) continue;
            Entry.Source->OverrideMaterials[I]=Entry.OriginalOverrides.IsValidIndex(I) ? Entry.OriginalOverrides[I] : nullptr;
            bChanged=true;
        }
        if (bChanged) Entry.Source->MarkRenderStateDirty();
    }
    Entry.FadeMaterials.Reset();
}

void UDinkInteriorCameraComponent::RestoreFoliage()
{
    for (FDinkFoliageFade& Entry : FoliageFades) EndFoliageFade(Entry);
    FoliageFades.Reset();
    FadingFoliageCount=0;
}

void UDinkInteriorCameraComponent::UpdateFoliage(float DeltaTime)
{
    FadingFoliageCount=0;
    UWorld* World=GetWorld();
    if (!World || !Camera || CVarDinkCameraFoliageFade.GetValueOnGameThread()==0 || FoliageVariants.IsEmpty())
    {
        if (!FoliageFades.IsEmpty()) RestoreFoliage();
        return;
    }
    const double Now=World->GetTimeSeconds();
    const FVector Body=GetOwner()->GetActorLocation();
    constexpr double RefreshSeconds=5.0;
    if (CurrentScreen.Get()!=FoliageGatherScreen.Get())
    {
        // Family art dresses a screen as it activates: gather again a moment after Dink changes screen.
        FoliageGatherScreen=CurrentScreen;
        FoliageGatherTime=FMath::Min(FoliageGatherTime,Now-RefreshSeconds+.3);
    }
    if (FoliageGatherTime<0 || Now-FoliageGatherTime>=RefreshSeconds || FVector::DistSquaredXY(Body,FoliageGatherOrigin)>FMath::Square(1000.))
    {
        GatherFoliage();
        FoliageGatherTime=Now;
        FoliageGatherOrigin=Body;
    }
    const UCapsuleComponent* Capsule=GetOwner()->FindComponentByClass<UCapsuleComponent>();
    const double Half=Capsule ? Capsule->GetScaledCapsuleHalfHeight() : 90.0;
    const FVector Eye=Camera->GetComponentLocation();
    const FVector Side=FRotator(0.0,Camera->GetComponentRotation().Yaw,0.0).RotateVector(FVector(0,22,0));
    const FVector Targets[]={Body+FVector(0,0,Half*.7),Body,Body-FVector(0,0,Half*.9),Body+Side,Body-Side};
    for (const FFoliageCandidate& Candidate : FoliageCandidates)
    {
        UStaticMeshComponent* Component=Candidate.Component.Get();
        if (!Component || !DinkCameraFoliage::Near(Candidate.Crown,Eye,Body,Candidate.Crown.Radius+200.0)) continue;
        int32 Found=FoliageFades.IndexOfByPredicate([&](const FDinkFoliageFade& F){ return F.Source==Component && F.Instance==Candidate.Instance; });
        if (!DinkCameraFoliage::Blocks(Candidate.Crown,Eye,Targets,Found!=INDEX_NONE ? DinkCameraFoliage::HoldMarginCm : 0.0)) continue;
        if (Found==INDEX_NONE)
        {
            FDinkFoliageFade Entry;
            Entry.Source=Component;
            Entry.Instance=Candidate.Instance;
            if (!BeginFoliageFade(Entry)) continue;
            Found=FoliageFades.Add(MoveTemp(Entry));
        }
        FoliageFades[Found].bInTheWay=true;
        FoliageFades[Found].HoldUntil=Now+DinkCameraFoliage::HoldSeconds;
    }
    for (int32 Index=FoliageFades.Num()-1; Index>=0; --Index)
    {
        FDinkFoliageFade& Entry=FoliageFades[Index];
        if (!IsValid(Entry.Source) || (Entry.Instance!=INDEX_NONE && !IsValid(Entry.Proxy)))
        {
            EndFoliageFade(Entry);
            FoliageFades.RemoveAt(Index);
            continue;
        }
        const bool bInTheWay=Entry.bInTheWay || Now<Entry.HoldUntil;
        Entry.bInTheWay=false;
        Entry.Opacity=DinkCameraFoliage::StepOpacity(Entry.Opacity,bInTheWay,DeltaTime);
        for (UMaterialInstanceDynamic* MID : Entry.FadeMaterials) if (MID) MID->SetScalarParameterValue(OpacityParameter,Entry.Opacity);
        if (!bInTheWay && Entry.Opacity>=1.f)
        {
            EndFoliageFade(Entry);
            FoliageFades.RemoveAt(Index);
            continue;
        }
        ++FadingFoliageCount;
    }
}
