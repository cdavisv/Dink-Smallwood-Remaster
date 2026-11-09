#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DinkInteriorCameraComponent.generated.h"

class USpringArmComponent;
class UCameraComponent;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class ADinkScreenVolume;

USTRUCT()
struct FDinkCameraOccluder
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Component;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> OriginalMaterials;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> OriginalOverrides;
    FName CollisionProfile;
    FName ManagedCollisionProfile;
    FCollisionResponseContainer CollisionResponses;
    ECollisionEnabled::Type CollisionEnabled = ECollisionEnabled::NoCollision;
    ECollisionChannel CollisionObjectType = ECC_WorldStatic;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> ManagedOverrides;
    UPROPERTY() TArray<TObjectPtr<UMaterialInstanceDynamic>> FadeMaterials;
    ECollisionResponse CameraResponse = ECR_Block;
    float Opacity = 1.f;
};

/** Interior presentation only. Original controller input, Pawn collision and warp rules stay authoritative. */
UCLASS(ClassGroup=(Dink), meta=(BlueprintSpawnableComponent))
class DINKCORE_API UDinkInteriorCameraComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UDinkInteriorCameraComponent();
    /** Historical cutaway mode for comparison fixtures only. Normal play keeps architecture opaque. */
    UPROPERTY(Transient) bool bEnableWallCutaway = false;
    /** Positive steps move closer. Kept separate from interior/outdoor base distances. */
    void AddZoomInput(float Steps);
    float GetZoomOffset() const { return ZoomOffset; }
    float GetDesiredArmLength() const;
    UPROPERTY(EditAnywhere, Category="Dink|Camera") float ZoomStep = 35.f;
    UPROPERTY(EditAnywhere, Category="Dink|Camera") float MinimumArmLength = 180.f;
    UPROPERTY(EditAnywhere, Category="Dink|Camera") float MaximumOutdoorArmLength = 650.f;
    UPROPERTY(EditAnywhere, Category="Dink|Camera") float MaximumInteriorArmLength = 320.f;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
    UPROPERTY(EditAnywhere, Category="Dink|Camera") float InteriorArmLength = 240.f;
    UPROPERTY(EditAnywhere, Category="Dink|Camera") FVector InteriorPivotOffset = FVector(0,0,52);
    UPROPERTY(EditAnywhere, Category="Dink|Camera") FVector InteriorShoulderOffset = FVector(0,45,0);
    UPROPERTY(EditAnywhere, Category="Dink|Camera") float InteriorFieldOfView = 70.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") bool bInteriorMode = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") int32 FadingOccluderCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") int32 ManagedOccluderCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") FVector FloorFramingShift = FVector::ZeroVector;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") bool bFloorFramingAvailable = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") bool bFloorFramingFeasible = true;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void SelectScreen(ADinkScreenVolume* Screen);
    void RestoreOccluders();
    void RestoreCamera();
    void UpdateFraming(float DeltaTime);
    bool CalculateFraming(float ShoulderY, const FMatrix& Projection, FVector2D& Shift) const;
    UPROPERTY() TObjectPtr<USpringArmComponent> Arm;
    UPROPERTY() TObjectPtr<UCameraComponent> Camera;
    UPROPERTY() TArray<FDinkCameraOccluder> Occluders;
    TWeakObjectPtr<ADinkScreenVolume> CurrentScreen;
    TMap<FString,FString> MaterialVariants;
    TMap<int32,TArray<FVector2D>> RoomFloors;
    TMap<int32,double> RoomFloorHeights;
    FVector PreviousPawnLocation = FVector::ZeroVector;
    float ShoulderTargetSign = 1.f;
    float CurrentShoulderY = 45.f;
    bool bSnapFraming = true;
    float OutdoorArm = 400.f;
    float OutdoorFOV = 90.f;
    FVector OutdoorPivot = FVector::ZeroVector;
    FVector OutdoorSocket = FVector::ZeroVector;
    bool bSelectedScreen = false;
    bool bAppliedCutaway = false;
    float ZoomOffset = 0.f;
};
