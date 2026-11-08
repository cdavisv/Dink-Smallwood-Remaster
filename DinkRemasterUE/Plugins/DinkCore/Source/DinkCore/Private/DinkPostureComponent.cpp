#include "DinkPostureComponent.h"
#include "Animation/AnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "UObject/UnrealType.h"

bool UDinkPostureComponent::ReadOverride(const USkeletalMeshComponent* Mesh, TSubclassOf<UAnimInstance>& Out)
{
    // The public getter resolves the mesh asset fallback; restoration needs the exact raw
    // override, including null. Read reflection only; all changes use the native setter.
    const FClassProperty* Property=FindFProperty<FClassProperty>(USkeletalMeshComponent::StaticClass(),TEXT("OverridePostProcessAnimBP"));
    if (!Mesh || !Property) return false;
    Out=Cast<UClass>(Property->GetObjectPropertyValue_InContainer(Mesh));
    return true;
}

bool UDinkPostureComponent::Configure(USkeletalMeshComponent* Mesh, TSubclassOf<UAnimInstance> Class)
{
    if (!Mesh || !Class) { Release(); return false; }
    if (Target && Target!=Mesh) Release();
    TSubclassOf<UAnimInstance> Current;
    if (!ReadOverride(Mesh,Current)) return false;
    if (Target==Mesh && (bExternallyReplaced || (Managed && Current!=Managed)))
    {
        bExternallyReplaced=true; return false;
    }
    if (!Target) { Target=Mesh; Previous=Current; }
    if (Current!=Class) Mesh->SetOverridePostProcessAnimBP(Class);
    Managed=Class;
    return true;
}

void UDinkPostureComponent::Release()
{
    TSubclassOf<UAnimInstance> Current;
    if (!bExternallyReplaced && Managed && ReadOverride(Target,Current) && Current==Managed)
        Target->SetOverridePostProcessAnimBP(Previous);
    Target=nullptr; Previous=nullptr; Managed=nullptr; bExternallyReplaced=false;
}

void UDinkPostureComponent::OnUnregister()
{
    Release();
    Super::OnUnregister();
}
