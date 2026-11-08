#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DinkPlayerActionComponent.generated.h"

class UAnimInstance;
class UAnimSequence;
class USkeletalMesh;
class USkeletalMeshComponent;
class UDinkSaveGame;
class UDinkSaveSubsystem;

/** Cosmetic player action only. Original script sequence/hit timing remains authoritative. */
UCLASS(ClassGroup = Dink, meta = (BlueprintSpawnableComponent))
class DINKCORE_API UDinkPlayerActionComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UDinkPlayerActionComponent();
    bool Configure(USkeletalMeshComponent* Mesh, const TMap<int32, UAnimSequence*>& ApprovedActions);
    bool PlaySequence(int32 Sequence);
    void Cancel();
    static bool IsReviewedSequence(int32 Sequence);
    bool IsActionActive() const { return ActiveSequence != 0; }
    int32 GetActiveSequence() const { return ActiveSequence; }
    double GetElapsedSeconds() const { return ElapsedSeconds; }
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;
protected:
    virtual void OnUnregister() override;
private:
    void ResetAction(bool RestoreAnimation);
    void CaptureSave(UDinkSaveGame* Save);
    void RestoreSave(const UDinkSaveGame* Save);
    void BindSave();
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> Target;
    UPROPERTY(Transient) TMap<int32, TObjectPtr<UAnimSequence>> Actions;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ActiveClip;
    UPROPERTY(Transient) TObjectPtr<USkeletalMesh> PlayedMesh;
    UPROPERTY(Transient) TSubclassOf<UAnimInstance> OriginalAnimClass;
    TWeakObjectPtr<UDinkSaveSubsystem> Saves;
    FDelegateHandle CaptureHandle, RestoreHandle;
    FVector PreviousLocation = FVector::ZeroVector;
    int32 ActiveSequence = 0;
    double ElapsedSeconds = 0;
};
