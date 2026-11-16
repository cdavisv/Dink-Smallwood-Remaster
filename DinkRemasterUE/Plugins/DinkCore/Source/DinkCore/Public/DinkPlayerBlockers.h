#pragma once

#include "CoreMinimal.h"
#include "ProceduralMeshComponent.h"
#include "DinkPlayerBlockers.generated.h"

class AActor;
class USceneComponent;
class UStaticMesh;
class UPrimitiveComponent;

/**
 * Player-only blockers (alpha QA, 14 Nov 2026; owner decision of 14 Nov: anything that looks solid at body height stops Dink).
 * Content/Dink/Data/Art/player_blockers.json lists meshes whose drawn body (a boulder, a trunk, a statue) is larger than the 1997
 * hardbox of the placements that show them, so the capsule could walk into them. Each row is the mesh's body-height cross-section
 * as a convex hull in the mesh's own space (cm, before the component's scale), measured by `dink.WalkAudit`'s slice. A component
 * that draws such a mesh gets a collision-only procedural prism of that hull with profile DinkPlayerBlock, which blocks the player
 * capsule and nothing else: NPC and creature moves, missiles, sight, the camera and the 1997 hardness (GetHard) are unchanged.
 */
struct DINKCORE_API FDinkPlayerBlockerShape
{
	FString Mesh;
	TArray<FVector2D> HullCm;
	double ZLowCm = 0.0;
	double ZHighCm = 0.0;
};

namespace DinkPlayerBlockers
{
	/** "Dink/Data/Art/player_blockers.json" under the project content directory. */
	DINKCORE_API FString DefaultPath();
	/** Parses the table (schema dink-player-blockers/1). Rows with errors are left out and reported. */
	DINKCORE_API bool Parse(const FString& Json, TMap<FString, FDinkPlayerBlockerShape>& Out, TArray<FString>& Errors, TSet<FString>* OutSkip = nullptr);
	/** The loaded table (read once from DefaultPath; `dink.PlayerBlockers 0` before play turns the layer off). */
	DINKCORE_API const TMap<FString, FDinkPlayerBlockerShape>& Table();
	DINKCORE_API const FDinkPlayerBlockerShape* Find(const UStaticMesh* Mesh);
	/**
	 * Adds the blocker of Mesh (if the table has one) to Owner, attached to AttachTo at RelativeToAttach (the drawn mesh's
	 * transform relative to AttachTo). Returns the new component, or null.
	 */
	DINKCORE_API UPrimitiveComponent* Add(AActor& Owner, USceneComponent& AttachTo, const FTransform& RelativeToAttach, const UStaticMesh* Mesh,
		const FString& Origin = FString());
	/** The same blocker from a given shape (no table lookup, no skip list): what Add builds; tests use it directly. */
	DINKCORE_API UPrimitiveComponent* AddShape(AActor& Owner, USceneComponent& AttachTo, const FTransform& RelativeToAttach,
		const FDinkPlayerBlockerShape& Shape, const UStaticMesh* Mesh = nullptr);
	/** Placements (origin IDs) the table leaves without a blocker (JSON "skip_origins": the blocker would cut off something to reach). */
	DINKCORE_API const TSet<FString>& SkipOrigins();
	/** Tag on every blocker component. */
	DINKCORE_API extern const FName Tag;
}

/**
 * The blocker: a collision-only convex prism (DinkPlayerBlock profile). It blocks only while the mesh it stands for is drawn
 * (visible, not hidden in game, its actor not hidden), so a placement a script hides or kills stops blocking at once.
 */
UCLASS(ClassGroup = Dink)
class DINKCORE_API UDinkPlayerBlockerComponent : public UProceduralMeshComponent
{
	GENERATED_BODY()
public:
	UDinkPlayerBlockerComponent(const FObjectInitializer& ObjectInitializer);
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
	/** Whether the drawn mesh is shown (and so whether this blocks). */
	bool IsDrawnShown() const;
	TWeakObjectPtr<USceneComponent> Drawn;
	/** The mesh it stands for (its hull is in player_blockers.json). */
	TWeakObjectPtr<const UStaticMesh> Mesh;
};
