#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkLayout.h"
#include "DinkLandforms.generated.h"

class AActor;
class ADinkGreyboxScreen;
class UInstancedStaticMeshComponent;
class UProceduralMeshComponent;
class UPrimitiveComponent;

/**
 * Landforms (owner direction of 15 Nov 2026: "real shape to the landscape"): a world heightfield made from the 1997 map by
 * Scripts/export_landforms.py (Content/Dink/Data/Environment/landforms.json + landforms.png). Banks slope into the water,
 * open ground undulates gently, rock and forest that nobody reaches rise, chasms drop; interiors, settlements, authored
 * screens and building facades stay flat. Every screen shares its edge heights with its neighbours.
 *
 * A VISUAL height layer only (coordinator decision of 16 Nov 2026): the 1997 simulation (2D positions, hardness, scripted
 * moves, timing, every collision result) is the same with the layer on and off. The ground mesh has no collision at all; the
 * player's capsule keeps walking on the importer's flat floor against the unchanged collision and only his drawn body and the
 * camera rise by the height under him (ADinkGreyboxCharacter). Other actors are drawn on the ground, but every invisible
 * collision primitive they carry (warp boxes, player-only blockers, NPC body shapes, fitted hardness) is held at its flat
 * height (FlatTag); queries between a flat body and lifted visible geometry are made in the lifted frame (GeometryLiftCm).
 */
struct DINKCORE_API FDinkLandformsScreen
{
	int32 Screen = 0;
	FDinkScreenCorners Corners;
	/** GridW x GridH heights in metres, row-major, at map pixel (i * GridPx, j * GridPx). */
	TArray<float> HeightsM;
	FBox2D BoundsCm = FBox2D(ForceInit);
	FString Flat;
	/** Walkable 1997 water (a ford, shallows) lies below 0 here: Dink's drawn body wades (his capsule stays on the floor). */
	bool bWade = false;
};

struct DINKCORE_API FDinkLandformsData
{
	int32 GridPx = 10;
	int32 GridW = 61;
	int32 GridH = 41;
	TMap<int32, FDinkLandformsScreen> Screens;

	/** Parses landforms.json and its 16-bit atlas (PNG bytes). */
	bool Load(const FString& Json, const TArray<uint8>& AtlasPng, FString& OutError);
	/** Height (m) at a map pixel of a screen with data (Catmull-Rom on the grid; exact at the vertices); 0 without data. */
	float HeightMAtPixel(int32 Screen, double MapX, double MapY) const;
};

namespace DinkLandforms
{
	/** "Dink/Data/Environment/landforms.json" under the project content directory. */
	DINKCORE_API FString DefaultPath();
	/** Catmull-Rom sample of a W x H grid at grid coordinates (GX, GY), clamped at the rim (exact at the vertices). */
	DINKCORE_API float SampleGrid(const TArray<float>& Grid, int32 W, int32 H, double GX, double GY);
	/**
	 * The landforms ground height (cm) at a world point, or 0 (no subsystem, switched off, no data there). bBelowZero false
	 * clamps fords to 0 (script sprites: NPC and creature bodies keep the 1997 sweeps' floor; only the player wades).
	 */
	DINKCORE_API float HeightCm(const UWorld* World, const FVector2D& WorldXY, bool bBelowZero = true);
	/** The ground mesh is drawn only: no collision on any channel (the simulation and the player's capsule never see it). */
	DINKCORE_API void ConfigureGround(UPrimitiveComponent& Component);
	/** Tag on the ground actors. */
	DINKCORE_API extern const FName Tag;
	/** Tag on an actor whose root stands on the landforms ground (its Z = flat Z + HeightCm(XY, false)). */
	DINKCORE_API extern const FName LiftedTag;
	/** Tag on a collision primitive of a lifted actor that is held at its flat (1997 floor) height. */
	DINKCORE_API extern const FName FlatTag;
	/** True while the layer is drawn in this world. */
	DINKCORE_API bool IsActive(const UWorld* World);
	/** The player's pawn: its capsule is never lifted (only its drawn body, see ADinkGreyboxCharacter). */
	DINKCORE_API bool IsPlayerPawn(const AActor* Actor);
	/** How far the landforms lift this actor's root now (0: player, flat actors, layer off). */
	DINKCORE_API float ActorLiftCm(const AActor* Actor);
	/** How far the landforms lift this primitive now (0 for a primitive held flat or on an unlifted actor). */
	DINKCORE_API float GeometryLiftCm(const UPrimitiveComponent* Component);
	/**
	 * After an actor's root lift changed from BeforeCm to AfterCm: its invisible collision primitives (shapes, hidden meshes,
	 * player-only blockers, warp boxes) go back to their flat height; ones seen for the first time are tagged FlatTag.
	 * The root itself is never held (a collision root is not lifted: script warp triggers).
	 */
	DINKCORE_API void KeepCollisionFlat(AActor& Actor, float BeforeCm, float AfterCm);
	/** The drawn ground at a world point (cm) and its normal; false off the layer (no data there or switched off). */
	DINKCORE_API bool GroundAt(const UWorld* World, const FVector2D& WorldXY, float& OutCm, FVector& OutNormal, bool bBelowZero = true);
}

UCLASS()
class DINKCORE_API UDinkLandformsSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	/** True while the landforms are on (dink.Landforms, -DinkLandforms=0 on the command line) and data was loaded. */
	bool IsActive() const { return bActive; }
	/** Ground height (cm) at a world point; 0 where there are no landforms. */
	float HeightCmAt(const FVector2D& WorldXY) const;
	/** True where the layer is on and has data. */
	bool HasDataAt(const FVector2D& WorldXY) const;
	/** Ground height (cm) at a map pixel of a screen; 0 where there are no landforms. */
	float HeightCmAtPixel(int32 Screen, double MapX, double MapY) const;
	/** Builds the drawn ground of the screens around a world point at once (teleports, warps, loads). */
	void EnsureAround(const FVector& WorldLocation);
	const FDinkLandformsData& GetData() const { return Data; }
	int32 NumBuilt() const { return Built.Num(); }

	/** What the layer added to the height of a decor instance (LiftScreenDecor); 0 for an instance it has not lifted. */
	float DecorLiftCm(const UInstancedStaticMeshComponent* Component, int32 InstanceIndex) const;
	/** Tests: replaces the loaded data (switches the layer on with it when bActivate). */
	void SetDataForTest(FDinkLandformsData&& InData, bool bActivate);
	/** Review: every placement actor, warp and decor instance on a landforms screen against the surface (console dink.LandformsAudit). */
	FString Audit(int32 MaxRows = 40) const;
	/** Switches the layer on or off at run time (review; a clean comparison starts the game with -DinkLandforms=0). */
	void SetActive(bool bOn);
	/** Puts decor that was made on a greybox screen after the layer snapped (family art dresses a screen on its first
	 *  visit: new instanced meshes and their player-only blockers at the flat ground) on the ground. Only what was not
	 *  lifted yet moves. -> instances lifted. */
	int32 SnapScreenDecor(ADinkGreyboxScreen& Screen);

private:
	struct FBuilt
	{
		TWeakObjectPtr<AActor> Actor;
		TWeakObjectPtr<UProceduralMeshComponent> Mesh;
		TWeakObjectPtr<ADinkGreyboxScreen> Greybox;
		int32 Step = 0;
	};

	void LoadData();
	int32 ScreenAt(const FVector2D& WorldXY, double& OutMapX, double& OutMapY) const;
	bool BuildScreen(int32 Screen, bool bNear);
	void FreeScreen(int32 Screen);
	void SnapPlacedActors(bool bOn);
	int32 LiftScreenDecor(ADinkGreyboxScreen& Screen);
	ADinkGreyboxScreen* FindGreybox(int32 Screen) const;

	FDinkLandformsData Data;
	bool bLoaded = false;
	bool bActive = false;
	bool bSnapped = false;
	/** Coarse 5000 cm cells -> screens whose bounds touch them. */
	TMap<FIntPoint, TArray<int32>> Cells;
	TMap<int32, FBuilt> Built;
	TMap<int32, TWeakObjectPtr<ADinkGreyboxScreen>> GreyboxByScreen;
	/** Screens whose ground could not be replaced (no shore water material on the water slot): they keep the flat ground. */
	TSet<int32> Skipped;
	/** What SnapPlacedActors added to each actor and decor instance (so switching off puts them back). */
	TMap<TWeakObjectPtr<AActor>, float> ActorLift;
	TArray<TPair<TWeakObjectPtr<UInstancedStaticMeshComponent>, TArray<float>>> DecorLift;
	FVector LastCentre = FVector(FLT_MAX);
	double LastBuildTime = 0.0;
};
