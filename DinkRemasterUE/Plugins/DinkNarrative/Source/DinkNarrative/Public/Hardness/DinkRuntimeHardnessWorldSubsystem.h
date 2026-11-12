#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkRuntimeHardnessWorldSubsystem.generated.h"
namespace DinkHardness { struct PhysicsOwner; }

/** Explicit new-world capability and retained physical owners. Sidecars alone
 * never opt a legacy world into different script/placement semantics. */
UCLASS()
class DINKNARRATIVE_API UDinkRuntimeHardnessWorldSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    bool RequiresScreenCapability(int32 Screen) const;
    bool IsAuthoredCollisionScreen(int32 Screen) const;
    TSharedPtr<DinkHardness::PhysicsOwner> AcquireOrRearm(int32 Screen, int32 Vision, FString& Error);
    virtual void Deinitialize() override;
protected:
    virtual bool DoesSupportWorldType(EWorldType::Type WorldType) const override;
private:
    struct FEntry;
    TMap<int32,TSharedPtr<FEntry>> Owners;
};
