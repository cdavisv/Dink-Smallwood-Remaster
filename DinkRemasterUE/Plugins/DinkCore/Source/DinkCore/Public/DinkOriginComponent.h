#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DinkOriginId.h"
#include "DinkOriginComponent.generated.h"

/**
 * Marks an actor as converted from a sprite placement of the original game.
 *
 * Written by the importer (DinkImport) on every generated actor and never hand-edited.
 * World state (UDinkWorldStateSubsystem), coverage reports and parity tests find actors by
 * this ID. Hand-made actors with no original counterpart simply do not have the component.
 */
UCLASS(ClassGroup = (Dink), meta = (BlueprintSpawnableComponent), HideCategories = (Activation, Cooking, Collision))
class DINKCORE_API UDinkOriginComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UDinkOriginComponent();

	/** Screen + placement index in the original map.dat. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FDinkOriginId OriginId;

	/** Name of the DinkC script attached to the placement in map.dat (without .c), or None. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FName ScriptName;

	/** Hash of the importer's source record, so re-imports can tell whether the original data changed. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FString SourceHash;

	/** Original sprite sequence (dink.ini) of the placement. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	int32 Sequence = 0;

	/** Original frame within Sequence (1-based). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	int32 Frame = 0;

	/** Editor placement type: 0 background, 1 live sprite, 2 hardness only. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	int32 PlacementType = 0;

	/** Stable class of the picture, from the data repo's tools/data/sprite_classes.csv (e.g. tree_pine_large). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FName ClassId;

	/** Category from sprite_classes.csv (structure, flora_tree, npc, enemy, ...). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FName Category;

	/** What the attached script is, from tools/dinkc script_kinds.csv (npc, enemy, warp, sign, ...), or None. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Origin")
	FName ScriptKind;

	/** "S412_P03". */
	UFUNCTION(BlueprintPure, Category = "Dink|Origin")
	FString GetOriginString() const { return OriginId.ToString(); }

	/** Returns the origin component on Actor, or nullptr. */
	static UDinkOriginComponent* FindOnActor(const AActor* Actor);
};
