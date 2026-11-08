#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkMaterialArtLibrary.generated.h"

class UMaterial;

/** Read-only editor inspection for reviewed art material recipes. */
UCLASS()
class DINKIMPORT_API UDinkMaterialArtLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** All connected property IDs, including pins hidden from Python's enum. Never edits the graph. */
	UFUNCTION(BlueprintPure, Category = "Dink|Art")
	static TArray<int32> GetConnectedMaterialProperties(UMaterial* Material);
};
