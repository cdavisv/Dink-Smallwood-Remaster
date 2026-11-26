#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DinkCameraFoliage.h"
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

/** One crown faded because it stands between the camera and Dink (DinkCameraFoliage). */
USTRUCT()
struct FDinkFoliageFade
{
    GENERATED_BODY()
    /** The tree's own component: a plain mesh, or the instanced component one of whose instances it is. */
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Source;
    /** Instance index in Source, or INDEX_NONE for a plain mesh component. */
    int32 Instance = INDEX_NONE;
    /** An instance fades through a stand-in mesh at its place while the instance itself is shrunk to nothing. */
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Proxy;
    FTransform InstanceTransform;
    UPROPERTY() TArray<TObjectPtr<UMaterialInterface>> OriginalOverrides;
    UPROPERTY() TArray<TObjectPtr<UMaterialInstanceDynamic>> FadeMaterials;
    float Opacity = 1.f;
    double HoldUntil = 0.0;
    bool bInTheWay = false;
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
    /** Collision-validated outdoor lift for a real blocker or authored portal; zero in interiors/free views. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") float OutdoorHeadroomLift = 0.f;
    /** Presentation-only portal cap; requested user zoom remains separate. Zero means no authored cap. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") float OutdoorPortalArmCap = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") bool bOutdoorPortalFramingFeasible = true;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") FString OutdoorPortalOwner;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") FString OutdoorPortalMeshSHA;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") bool bInteriorMode = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") int32 FadingOccluderCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") int32 ManagedOccluderCount = 0;
    /** Crowns (trees, tall bushes) faded this frame because they stand between the camera and Dink. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") int32 FadingFoliageCount = 0;
    /** Crown candidates near Dink, from the last gather. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") int32 FoliageCandidateCount = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") FVector FloorFramingShift = FVector::ZeroVector;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") bool bFloorFramingAvailable = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") bool bFloorFramingFeasible = true;
    /**
     * A62 (25 Nov 2026): indoors, when the arm's probe would stop within InteriorMinimumClearArm of the pivot (Dink with his back to a
     * wall: the camera sat in his hair), the camera looks down from higher instead: a steeper pitch (at most InteriorMaximumClearPitch)
     * from a pivot raised by up to InteriorMaximumClearLift (swept for the ceiling): the least change that clears the minimum arm, else
     * the one that puts the eye farthest from his head. The player's control rotation is not changed. If the eye still ends nearer than InteriorHeadClearance to Dink's head, his body is not drawn for this
     * view (owner-no-see) rather than filling the frame from inside his hair. Play camera only.
     */
    UPROPERTY(EditAnywhere, Category="Dink|Camera") float InteriorMinimumClearArm = 120.f;
    UPROPERTY(EditAnywhere, Category="Dink|Camera") float InteriorMaximumClearPitch = -75.f;
    UPROPERTY(EditAnywhere, Category="Dink|Camera") float InteriorMaximumClearLift = 100.f;
    UPROPERTY(EditAnywhere, Category="Dink|Camera") float InteriorHeadClearance = 58.f;
    /** What the clearance rule applies now: pitch (degrees below the player's, <= 0), pivot lift (cm), the clear arm it found (cm). */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") float InteriorClearPitch = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") float InteriorClearLift = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") float InteriorClearArm = 0.f;
    /** Dink's body is not drawn for the play camera (its eye is inside InteriorHeadClearance of his head). */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Dink|Camera") bool bInteriorHeroHidden = false;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void SelectScreen(ADinkScreenVolume* Screen);
    void RestoreOccluders();
    void RestoreCamera();
    void UpdateFraming(float DeltaTime);
    void UpdateOutdoorHeadroom();
    void UpdateInteriorClearance(float DeltaTime);
    void SetHeroHidden(bool bHidden);
    void ReleaseInteriorClearance();
    bool CalculateFraming(float ShoulderY, const FMatrix& Projection, FVector2D& Shift) const;
    /** Fades the crowns between the camera and Dink (see DinkCameraFoliage.h); restores them when they are clear. */
    void UpdateFoliage(float DeltaTime);
    void GatherFoliage();
    bool FoliageSupported(UStaticMeshComponent& Component);
    bool BeginFoliageFade(FDinkFoliageFade& Entry);
    void EndFoliageFade(FDinkFoliageFade& Entry);
    void RestoreFoliage();
    UPROPERTY() TObjectPtr<USpringArmComponent> Arm;
    UPROPERTY() TObjectPtr<UCameraComponent> Camera;
    UPROPERTY() TArray<FDinkCameraOccluder> Occluders;
    UPROPERTY() TArray<FDinkFoliageFade> FoliageFades;
    struct FFoliageCandidate { TWeakObjectPtr<UStaticMeshComponent> Component; int32 Instance = INDEX_NONE; DinkCameraFoliage::FCrown Crown; };
    TArray<FFoliageCandidate> FoliageCandidates;
    /** Base material path (lower case) -> its camera fade variant (camera_materials.json "foliage_variants"). */
    TMap<FString,FString> FoliageVariants;
    UPROPERTY() TMap<TObjectPtr<UMaterialInterface>,TObjectPtr<UMaterialInterface>> FoliageVariantByBase;
    TMap<TWeakObjectPtr<UMaterialInterface>,bool> FoliageMaterialSupported;
    FVector FoliageGatherOrigin = FVector(TNumericLimits<double>::Max());
    double FoliageGatherTime = -1.0;
    TWeakObjectPtr<ADinkScreenVolume> FoliageGatherScreen;
    TWeakObjectPtr<ADinkScreenVolume> CurrentScreen;
    TMap<FString,FString> MaterialVariants;
    TMap<int32,TArray<FVector2D>> RoomFloors;
    TMap<int32,double> RoomFloorHeights;
    FVector PreviousPawnLocation = FVector::ZeroVector;
    float ShoulderTargetSign = 1.f;
    float CurrentShoulderY = 45.f;
    bool bSnapFraming = true;
    FVector InteriorClearAppliedOffset = FVector::ZeroVector;
    float OutdoorArm = 400.f;
    float UncappedOutdoorArm = 400.f;
    float OutdoorFOV = 90.f;
    FVector OutdoorPivot = FVector::ZeroVector;
    FVector OutdoorSocket = FVector::ZeroVector;
    bool bSelectedScreen = false;
    bool bAppliedCutaway = false;
    float ZoomOffset = 0.f;
};
