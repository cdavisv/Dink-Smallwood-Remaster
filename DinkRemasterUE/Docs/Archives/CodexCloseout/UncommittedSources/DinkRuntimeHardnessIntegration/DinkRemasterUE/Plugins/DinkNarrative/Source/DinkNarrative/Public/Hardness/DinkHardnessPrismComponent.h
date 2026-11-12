#pragma once
#include "CoreMinimal.h"
#include "Components/ShapeComponent.h"
#include "DinkHardnessPrismComponent.generated.h"

/** Transient original open-bottom triangle shells for one hardness-code mask. Preparation creates
 * actual registered bodies with per-shape collision disabled, not an active
 * temporary proxy. No use is admitted until native staged-world proof. */
UCLASS(Transient, NotBlueprintable)
class DINKNARRATIVE_API UDinkHardnessPrismComponent : public UShapeComponent
{
    GENERATED_BODY()
public:
    UDinkHardnessPrismComponent(const FObjectInitializer& ObjectInitializer);
    bool PrepareGeometry(const TArray<TArray<FVector>>& LocalPrisms, const UPrimitiveComponent& PolicyReference);
    bool FinalizeRegisteredPreparation(const UPrimitiveComponent& PolicyReference);
    bool ValidateRegisteredInert() const;
    UPROPERTY(VisibleInstanceOnly, Category="Dink|Hardness")
    int32 HardnessCode = 0;
    bool DesiredNavigation() const { return bDesiredNavigation; }
    virtual void UpdateBodySetup() override;
    virtual FPrimitiveSceneProxy* CreateSceneProxy() override { return nullptr; }
    virtual FBoxSphereBounds CalcBounds(const FTransform& LocalToWorld) const override;
private:
    FBox LocalGeometryBounds = FBox(ForceInit);
    bool bDesiredNavigation = false;
};
