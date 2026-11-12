#pragma once
#include "CoreMinimal.h"
#include "Components/ShapeComponent.h"
#include "Hardness/DinkCookedMeshIdentity.h"
#include "DinkHardnessPrismComponent.generated.h"
class UBodySetup;
namespace Chaos { class FTriangleMeshImplicitObject; }

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
    bool PrepareCookedMeshGeometry(UBodySetup& Source,const UPrimitiveComponent& PolicyReference);
    bool ValidateCookedMeshGeometry(const UBodySetup& Source) const;
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
    TWeakObjectPtr<UBodySetup> CookedSource;
    bool SourceRawCullBeforeRegistration=false;
    // Source cache raw cull may legitimately initialize under stock registration;
    // immutable geometry/GUID and phase-qualified owned cull remain strict.
    FGuid PreparedSourceGuid;
    bool PreparedSourceDoubleSided=false;
    const Chaos::FTriangleMeshImplicitObject* PreparedSourceImplicit=nullptr;
    const Chaos::FTriangleMeshImplicitObject* PreparedOwnedImplicit=nullptr;
    TWeakObjectPtr<UBodySetup> PreparedOwnedSetup;
    std::optional<DinkCookedMeshIdentity::Admission> PreparedIdentity;
};
