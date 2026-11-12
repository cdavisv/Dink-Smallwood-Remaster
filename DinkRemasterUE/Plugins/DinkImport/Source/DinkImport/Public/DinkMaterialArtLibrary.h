#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkMaterialArtLibrary.generated.h"

class UMaterial;
class UMaterialExpression;
class UTexture2D;
class UStaticMesh;
class UPrimitiveComponent;

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
	/** Detached source mip bytes and format. Does not edit, compress, save or read GPU pixels. */
	UFUNCTION(BlueprintPure, Category = "Dink|Art")
	static FString InspectTextureSourcePixels(UTexture2D* Texture);

	/** Unsaved candidate-only import correction. Requires exact current snapshot and complete unique color rows; never saves. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Art")
	static FString RestoreCandidateStaticMeshLinearColors(UStaticMesh* Mesh, const FString& ExpectedGeometry,
		const TArray<int32>& InstanceIDs, const TArray<FLinearColor>& LinearColors);

	/** Exact per-input source/output index; never uses first-source-match helpers or edits the graph. */
	UFUNCTION(BlueprintPure, Category = "Dink|Art")
	static FString InspectMaterialExpressionInputs(UMaterialExpression* Expression);

	/** Detached live responses for all64 serialized channels, including hidden enum values. No writes. */
	UFUNCTION(BlueprintPure, Category = "Dink|Art")
	static TArray<int32> InspectPrimitiveCollisionResponses(UPrimitiveComponent* Component);

	/** Detached JSON per-LOD import metadata via public source-model accessors. Never edits/cooks/saves. */
	UFUNCTION(BlueprintPure, Category = "Dink|Art")
	static FString InspectStaticMeshSourceLods(UStaticMesh* Mesh);

	/** Detached RAW MeshDescription and built LOD buffers: all UVs, Color0, signed TBN and named sections. Never builds or saves. */
	UFUNCTION(BlueprintPure, Category = "Dink|Art")
	static FString InspectStaticMeshGeometry(UStaticMesh* Mesh, int32 LODIndex = 0);

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
