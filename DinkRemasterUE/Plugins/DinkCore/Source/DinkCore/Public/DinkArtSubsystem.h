#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkArtSubsystem.generated.h"

/** Applies authored Blender assets without modifying the regenerable greybox maps.
 * Original actors keep their origins, scripts, vision gates and save identities.
 * The manifest is produced by Scripts/import_stonebrook_art.py.
 */
UCLASS()
class DINKCORE_API UDinkArtSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	/** Applies an optional authored player mesh after the pawn has loaded its animation rig. */
	bool ApplyPlayer(class USkeletalMeshComponent& Component);
    /** Cosmetic only: original script sequence and175ms damage scheduling remain authoritative. */
    bool PlayPlayerSequence(AActor* Actor, int32 Sequence);
	/** Present dynamically scripted actors (such as Milder) without replacing their gameplay identity. */
	bool ApplyScriptCharacter(AActor* Actor, FName Script, float SpriteScale = 1.f);
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
protected:
	virtual bool DoesSupportWorldType(EWorldType::Type WorldType) const override;
private:
	void ApplyManifest(UWorld& World, const FString& ManifestFile);
	void ApplyCharacters(UWorld& World);
    void ConfigurePlayerActions(class USkeletalMeshComponent& Component);
};
