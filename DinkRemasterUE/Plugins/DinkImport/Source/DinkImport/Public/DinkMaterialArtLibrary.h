#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkMaterialArtLibrary.generated.h"

class UMaterial;
class UStaticMesh;

/** Detached read-only snapshot; modifying this value cannot mutate its source body. */
USTRUCT(BlueprintType)
struct DINKIMPORT_API FDinkConvexArtSnapshot
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Dink|Art")
	FTransform LocalToMesh = FTransform::Identity;
	UPROPERTY(BlueprintReadOnly, Category = "Dink|Art")
	TArray<FVector> LocalVertices;
	UPROPERTY(BlueprintReadOnly, Category = "Dink|Art")
	TArray<FVector> MeshVertices;
	UPROPERTY(BlueprintReadOnly, Category = "Dink|Art")
	TArray<int32> Indices;
};

/** Read-only editor inspection for reviewed material recipes and authored hulls. */
UCLASS()
class DINKIMPORT_API UDinkMaterialArtLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** All connected property IDs, including pins hidden from Python's enum. Never edits the graph. */
	UFUNCTION(BlueprintPure, Category = "Dink|Art")
	static TArray<int32> GetConnectedMaterialProperties(UMaterial* Material);

	/** Uses public GetTransform; never cooks, rebuilds, saves or modifies the mesh/body. */
	UFUNCTION(BlueprintPure, Category = "Dink|Art")
	static TArray<FDinkConvexArtSnapshot> InspectStaticMeshConvexCollision(UStaticMesh* Mesh);

	/** JSON triangle/group bindings resolved by actual imported slot names. No index-order assumptions or writes. */
	UFUNCTION(BlueprintPure, Category = "Dink|Art")
	static FString InspectStaticMeshMaterialBindings(UStaticMesh* Mesh, int32 LODIndex = 0);
};
