#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DinkOriginId.h"
#include "DinkInstanceOriginsComponent.generated.h"

/** Origin of one instance of an instanced static mesh component (see UDinkInstanceOriginsComponent). */
USTRUCT(BlueprintType)
struct DINKCORE_API FDinkInstanceOrigin
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FDinkOriginId OriginId;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FName ScriptName;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	int32 Sequence = 0;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	int32 Frame = 0;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FName ClassId;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FName Category;

	/** Name of the instanced static mesh component on the same actor that holds the instance. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FName ComponentName;

	/** Index of the instance in that component. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	int32 InstanceIndex = INDEX_NONE;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FString SourceHash;
};

/**
 * Origin IDs of placements that were imported as instances rather than actors (the original's
 * background decoration, editor type 0, which the engine bakes into the screen and never touches
 * again). One per actor that owns instanced components; parity tests and coverage reports count
 * these together with UDinkOriginComponent so every original placement is accounted for once.
 */
UCLASS(ClassGroup = (Dink), meta = (BlueprintSpawnableComponent), HideCategories = (Activation, Cooking, Collision))
class DINKCORE_API UDinkInstanceOriginsComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UDinkInstanceOriginsComponent();

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	TArray<FDinkInstanceOrigin> Origins;
};
