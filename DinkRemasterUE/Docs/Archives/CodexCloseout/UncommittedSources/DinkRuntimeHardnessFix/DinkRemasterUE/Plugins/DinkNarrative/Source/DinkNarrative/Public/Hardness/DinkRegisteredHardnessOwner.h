#pragma once
#include "CoreMinimal.h"
#include "DinkHardnessSession.h"
class AActor;
class ADinkScreenVolume;
class UPrimitiveComponent;

/** Only a separately reviewed new world generation may supply this definition.
 * Callback proofs are required native checks, not permission to reuse/disable an
 * aggregate legacy mesh. No production caller/automatic admission exists yet. */
struct DINKNARRATIVE_API FDinkHardnessWorldDefinition
{
    TWeakObjectPtr<AActor> Host;
    TWeakObjectPtr<ADinkScreenVolume> Screen;
    TWeakObjectPtr<UPrimitiveComponent> SolidPolicy;
    TWeakObjectPtr<UPrimitiveComponent> LowPolicy;
    TArray<TWeakObjectPtr<UPrimitiveComponent>> ImmutableFloorFill;
    float HeightCm = 300.f;
    int32 Vision = 0;
    TFunction<bool()> IsAuthoredCollisionScreen;
    TFunction<bool(FString&)> VerifyImmutableFoundation;
};

/** Actual registered-body candidate backend; native proof/build still pending. */
class DINKNARRATIVE_API FDinkRegisteredHardnessOwner final
    : public DinkHardness::PhysicsOwner, public TSharedFromThis<FDinkRegisteredHardnessOwner>
{
public:
    static TSharedPtr<FDinkRegisteredHardnessOwner> Create(FDinkHardnessWorldDefinition Definition, FString& Error);
    virtual ~FDinkRegisteredHardnessOwner();
    virtual int Version() const noexcept override { return 1; }
    virtual int GetScreen() const noexcept override;
    virtual int GetVision() const noexcept override;
    virtual bool IsAuthoredScreen() const noexcept override;
    virtual std::uintptr_t GetWorldCookie() const noexcept override;
    virtual bool HasAdmittedBaseline() const noexcept override;
    virtual void InvalidateForScreenRebuild() noexcept override;
    bool RearmForScreenBuild(int32 Vision, FString& Error);
    virtual std::unique_ptr<DinkHardness::PreparedPhysics> Prepare(const std::vector<DinkHardness::OwnedRect>& Candidate) override;
private:
    explicit FDinkRegisteredHardnessOwner(FDinkHardnessWorldDefinition Definition);
    struct FImpl;
    TUniquePtr<FImpl> Impl;
};
