#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkCameraPortal.h"
#include "DinkArtSubsystem.generated.h"

/** Applies authored Blender assets without modifying the regenerable greybox maps.
 * Original actors keep their origins, scripts, vision gates and save identities.
 * The manifest is produced by Scripts/import_stonebrook_art.py.
 */
struct FDinkExteriorCameraRule
{
    FString Manifest,Element,Mesh,NativeMeshSHA;
    FVector NativeBoundsMin=FVector::ZeroVector,NativeBoundsMax=FVector::ZeroVector;
    int32 Screen=0;
    DinkCameraPortal::FDefinition Definition;
    TWeakObjectPtr<class UStaticMeshComponent> Component;
};

UCLASS()
class DINKCORE_API UDinkArtSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
public:
    /** Hardness migration waits for the actual art application and excludes
     * screens whose legacy collision this subsystem replaced. Read-only state. */
    bool HasCompletedInitialApplication() const { return bInitialApplicationComplete; }
    bool UsesAuthoredCollision(int32 Screen) const { return AuthoredCollisionScreens.Contains(Screen); }
	/** Applies an optional authored player mesh after the pawn has loaded its animation rig. */
	bool ApplyPlayer(class USkeletalMeshComponent& Component);
    /** Cosmetic only: original script sequence and175ms damage scheduling remain authoritative. */
    bool PlayPlayerSequence(AActor* Actor, int32 Sequence);
	/** Present dynamically scripted actors (such as Milder) without replacing their gameplay identity. */
	bool ApplyScriptCharacter(AActor* Actor, FName Script, float SpriteScale = 1.f);
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
    bool ExteriorCameraLimit(const class ADinkScreenVolume& Screen,const FVector& Pivot,const FVector& Desired,
                             double ProbeRadius,double FrustumClearance,DinkCameraPortal::FLimit& Out) const;
protected:
	virtual bool DoesSupportWorldType(EWorldType::Type WorldType) const override;
private:
	friend struct FDinkArtNavigationTestAccess;
    bool bInitialApplicationComplete = false;
    TSet<int32> AuthoredCollisionScreens;
    friend struct FDinkArtLightTestAccess;
    friend struct FDinkExteriorPortalTestAccess;
    void LoadExteriorCameraRules();
    void RegisterExteriorCameraRule(const FString& Manifest,const TSharedPtr<class FJsonObject>& Row,
                                    int32 Screen,class UStaticMeshComponent* Component);
    TArray<FDinkExteriorCameraRule> ExteriorCameraRules;
	void ApplyManifest(UWorld& World, const FString& ManifestFile);
	void ApplyManifest(UWorld& World, const TSharedPtr<class FJsonObject>& Manifest, const FString& ManifestFile);
	void ApplyCharacters(UWorld& World);
    void ConfigurePlayerActions(class USkeletalMeshComponent& Component);
};
