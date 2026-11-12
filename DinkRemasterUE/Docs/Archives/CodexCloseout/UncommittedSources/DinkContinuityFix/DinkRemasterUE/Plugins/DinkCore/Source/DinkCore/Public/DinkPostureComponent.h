#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DinkPostureComponent.generated.h"
class UAnimInstance;
class USkeletalMeshComponent;

/** Owns only its optional post-process override, preserving the previous raw override and
 * respecting external changes. Art validation owns graph/skeleton compatibility. */
UCLASS()
class DINKCORE_API UDinkPostureComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    bool Configure(USkeletalMeshComponent* Mesh, TSubclassOf<UAnimInstance> Class);
    void Release();
    static bool ReadOverride(const USkeletalMeshComponent* Mesh, TSubclassOf<UAnimInstance>& Out);
protected:
    virtual void OnUnregister() override;
private:
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> Target;
    UPROPERTY(Transient) TSubclassOf<UAnimInstance> Previous;
    UPROPERTY(Transient) TSubclassOf<UAnimInstance> Managed;
    bool bExternallyReplaced = false;
};
