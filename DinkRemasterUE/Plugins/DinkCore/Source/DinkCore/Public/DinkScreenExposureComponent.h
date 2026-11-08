#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/TimerHandle.h"
#include "DinkScreenExposureComponent.generated.h"

class ADinkScreenVolume;
class UDinkGreyboxSubsystem;
class APlayerController;
class APawn;
class UPostProcessComponent;

/** Owns only one authored room's plain postprocess provider. Camera orbits can leave
 * its architectural bounds; activation follows the first local pawn's selected
 * AND physical indoor room. No camera, lighting or gameplay settings are changed.
 */
UCLASS(NotBlueprintable, ClassGroup=(Dink))
class DINKCORE_API UDinkScreenExposureComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UDinkScreenExposureComponent();
    UFUNCTION(BlueprintCallable, Category="Dink|Art")
    void ConfigureExposure(UPostProcessComponent* Exposure, int32 ScreenNumber);
    UFUNCTION(BlueprintPure, Category="Dink|Art")
    bool HasOwnershipRefreshTimer() const;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void RefreshOwnership();
    void StartRefreshTimer();
    void DisableProvider();
    void ScreenChanged(ADinkScreenVolume* Screen);
    void PawnChanged(APawn* Pawn);
    void ClearBindings();
    UPROPERTY(Transient)
    TWeakObjectPtr<UPostProcessComponent> Provider;
    UPROPERTY(VisibleAnywhere, Transient, Category="Dink|Art")
    int32 OwnerScreenNumber=0;
    bool bEndingPlay=false;
    TWeakObjectPtr<UDinkGreyboxSubsystem> Greybox;
    TWeakObjectPtr<APlayerController> BoundController;
    FDelegateHandle ScreenHandle, PawnHandle;
    FTimerHandle OwnershipRefresh;
};
