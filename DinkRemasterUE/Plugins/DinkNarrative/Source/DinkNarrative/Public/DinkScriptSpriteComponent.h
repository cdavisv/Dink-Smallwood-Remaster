#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/Actor.h"
#include "DinkScriptSpriteComponent.generated.h"

class UStaticMeshComponent;

/**
 * Added by the director to every actor a script addresses through a sprite handle. Holds what the
 * scripts set on the sprite that the 3D world does not act on yet (sp_seq, sp_pseq, sp_pframe,
 * sp_base_walk, sp_brain, sp_timing, init lines...), so the future animation and AI layers read the
 * same data the original engine had. Written only by UDinkDirector.
 */
UCLASS(ClassGroup = (Dink), meta = (BlueprintSpawnableComponent))
class DINKNARRATIVE_API UDinkScriptSpriteComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	/** The sprite handle scripts use for this actor (1 = Dink). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Script")
	int32 Handle = 0;

	/** Every sp_<prop> value set by a script, by property name without "sp_" (seq, pframe, brain, speed, ...). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Script")
	TMap<FName, int32> Props;

	/** Numpad direction the scripts last gave (sp_dir / movement). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Script")
	int32 Dir = 2;

	/** Script attached to the sprite (sp_script), None if none. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Script")
	FName Script;

	/** freeze/unfreeze. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Script")
	bool bFrozen = false;

	/** Finds or creates the component on Actor. */
	static UDinkScriptSpriteComponent* FindOrAdd(AActor* Actor);
};

/** An actor made by create_sprite: a small marker so a person can see it in the greybox. */
UCLASS()
class DINKNARRATIVE_API ADinkScriptSpriteActor : public AActor
{
	GENERATED_BODY()

public:
	ADinkScriptSpriteActor();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Script")
	TObjectPtr<UStaticMeshComponent> Marker;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink|Script")
	TObjectPtr<UDinkScriptSpriteComponent> Sprite;
};
