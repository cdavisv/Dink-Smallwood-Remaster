#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Engine/TimerHandle.h"
#include "DinkArtContextActor.generated.h"

class ADinkScreenVolume;
class UDinkGreyboxSubsystem;
class APlayerController;
class APawn;
class UStaticMesh;
class UStaticMeshComponent;
class FJsonObject;

/** Optional render-only dressing context. Never owns/reparents original gameplay actors. */
UCLASS(NotBlueprintable)
class DINKCORE_API ADinkArtContextActor : public AActor
{
    GENERATED_BODY()
  public:
    ADinkArtContextActor();
    static ADinkArtContextActor *CreateFromManifest(UWorld &World, const TSharedPtr<FJsonObject> &Manifest,
                                                    const TMap<FString, UStaticMesh *> &Meshes, int32 OwnerScreen);
    /** Call after all components are prepared, so an incomplete manifest remains hidden. */
    void ConfigureOwnerScreen(int32 ScreenNumber);
    UStaticMeshComponent *AddRenderOnlyMesh(UStaticMesh *Mesh, const FTransform &WorldTransform);
    int32 GetOwnerScreenNumber() const
    {
        return OwnerScreenNumber;
    }

  protected:
    void BeginPlay() override;
    void EndPlay(const EEndPlayReason::Type Reason) override;

  private:
    void UpdateVisibility();
    void ScreenChanged(ADinkScreenVolume *Screen);
    void PawnChanged(APawn *Pawn);
    int32 OwnerScreenNumber = 0;
    TWeakObjectPtr<UDinkGreyboxSubsystem> Greybox;
    TWeakObjectPtr<APlayerController> BoundController;
    FDelegateHandle ScreenHandle, PawnHandle;
    FTimerHandle ControllerRefreshTimer;
};
