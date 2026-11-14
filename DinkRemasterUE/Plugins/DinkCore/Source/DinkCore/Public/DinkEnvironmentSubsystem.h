#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkLayout.h"
#include "DinkEnvironmentSubsystem.generated.h"

class ADinkScreenVolume;
class ADinkPlaceholderActor;
class UPointLightComponent;
class UPostProcessComponent;
class UStaticMeshComponent;
class UStaticMesh;

/** One 8 m world cell of the grass carpet: an instanced component per mesh that has instances there. */
USTRUCT()
struct FDinkGrassCell
{
	GENERATED_BODY()
	UPROPERTY(Transient)
	TArray<TObjectPtr<class UInstancedStaticMeshComponent>> Components;
	bool bCastsShadow = false;
};

/** Look of one kind of indoor screen (environment.json `indoor.interior` / `indoor.dungeon`). */
struct FDinkIndoorLook
{
	float ExposureEV = 0.f;                 // fixed exposure while inside (the interior post-process component)
	float AmbientIntensity = 0.f;           // unshadowed cool fill, one per screen
	FLinearColor AmbientColour = FLinearColor(0.55f, 0.65f, 1.f);
	int32 LampsPerScreen = 0;               // warm shadowed lights without a sprite source (ceiling lamps / wall torches)
	float LampIntensity = 0.f, LampRadiusCm = 900.f, LampHeightCm = 240.f;
	FLinearColor LampColour = FLinearColor(1.f, 0.62f, 0.32f);
	bool bLampsAtWalls = false;             // dungeon: lamps stand off the wall placements instead of hanging in a row
	float FogDensity = 0.f;                 // local fog volume over the interior, 0 = none
	// round 6: an even, unshadowed fill (no inverse-square falloff) so wall tops and furniture read; a visible ceiling
	float FillIntensity = 0.f;
	FLinearColor FillColour = FLinearColor(1.f, 0.9f, 0.78f);
	float CeilingCm = 0.f;                  // 0 = no visible ceiling
	FString CeilingMaterial;                // tiled on one-sided planes facing down (ceiling_tile_cm each)
	FString CeilingWallClass;               // only interiors that carry placements of this class prefix get the ceiling
};

/** A scripted placement whose look follows its DinkC sprite state (burnable pines). */
USTRUCT()
struct FDinkBurnable
{
	GENERATED_BODY()
	UPROPERTY(Transient)
	TWeakObjectPtr<ADinkPlaceholderActor> Actor;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> Before;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> After;
	int32 State = 0; // 0 standing (dry), 1 burning or burnt, 2 the script replaced the picture: card only
};

/**
 * Presentation-only environment helpers of the photoreal pass. Nothing here has collision, input or
 * gameplay state, and nothing is created when the process cannot render (headless tests, probe).
 *
 *  - Backdrop: the importer's `Env:Backdrop` actor (far terrain skirt and hill ring)
 *    follow the camera in X/Y so no view ever sees the edge of the playable grid.
 *  - Interior exposure: on indoor screens an unbound post-process component (priority above the
 *    authored `ArtExposure` volumes, which stay untouched) opens the exposure and lifts shadows.
 *  - Grass carpet: instanced patches in 8 m world cells around the camera on ground the terrain mask
 *    marks as meadow (on authored screens: where a downward trace lands on a meadow-material mesh),
 *    thinned out by the material towards the far distance. Meshes and densities come from
 *    Content/Dink/Data/Environment/environment.json; coverage from layer_cover.json.
 *  - Family art on the screens around the current one, so the view never shows sprite cards next door.
 *  - Indoor set: while the player is on an indoor screen that no art manifest dresses, a hidden shadow-casting
 *    ceiling and wall shell over the whole interior (sun and sky stay out), black one-sided backdrop planes facing
 *    inward (no hills or neighbours in view; the camera looks through them from outside), warm shadowed lights at
 *    fire sprites, lamps or wall torches, a dim cool fill, a fixed exposure and, in dungeons, slight local fog.
 *    Built on entering, destroyed on leaving; nothing of it has collision. `dink.IndoorEnv 0` turns it off.
 *  - Burnable pines: the scripted pines listed in environment.json stand as the dry pine; once their DinkC script
 *    plays the burn sequence or swaps the picture (the secret stairs) the burnt pine stands there instead. The
 *    placement's own card stays hidden (it would still show the green pine: placement cards are not redrawn from
 *    the script state); `burnable.show_card` true shows it again from the burn on. Read-only on the script state.
 *  - Ground colour: the mean terrain colour under a point (ground_colour.json), for trunk feet.
 *  - Forest: trees on the unwalkable forest-canopy tiles of the screens in view (ground_classes.json `trees`).
 *
 * Console variables: dink.GrassDensity (multiplier, 0 = off), dink.InteriorExposure (0/1),
 * dink.InteriorExposureBias, dink.Backdrop (0/1), dink.Wind (foliage wind strength).
 */
UCLASS()
class DINKCORE_API UDinkEnvironmentSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void OnWorldBeginPlay(UWorld& World) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;

	/** Number of grass instances currently spawned (review/debug). */
	int32 GetGrassInstanceCount() const;

	/** Mean terrain base colour (linear) under a world point, from ground_colour.json. False off the terrain grid, on indoor screens and when the process cannot render. */
	bool GroundColourAt(const FVector2D& WorldXY, FLinearColor& Out);

private:
	struct FScreenInfo
	{
		int32 Number = 0;
		FDinkScreenCorners Corners;
		FVector Centre = FVector::ZeroVector;
		bool bIndoor = false;
		bool bDungeon = false;
		FName InteriorId;
	};

	void LoadConfig();
	void UpdateGrass(const FVector& Camera, float Density);
	void BuildGrassCell(const FIntPoint& Cell, float Density);
	void ClearGrass();
	bool IsScreenDressed(int32 ScreenNumber) const;
	bool GroundAt(const FVector2D& WorldXY, uint32 Hash, float& OutZ) const;
	void ApplyNeighbourFamilies(const FVector& Around);
	void GatherScreens(UWorld& World);
	void LoadGroundColour();
	void UpdateIndoor(const ADinkScreenVolume* Current, float DeltaTime);
	void BuildIndoor(const ADinkScreenVolume& Current);
	void ClearIndoor();
	void FindBurnables();
	void UpdateBurnables();

	bool bActive = false;
	TArray<FScreenInfo> Screens;
	TArray<FBox2D> ScreenBounds;
	TArray<TWeakObjectPtr<AActor>> Backdrops;

	UPROPERTY(Transient)
	TObjectPtr<AActor> Holder;
	UPROPERTY(Transient)
	TObjectPtr<UPostProcessComponent> InteriorExposure;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> GrassMeshes;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> AccentMeshes;
	UPROPERTY(Transient)
	TMap<FString, TObjectPtr<class UMaterialInterface>> ScatterMaterials;
	UPROPERTY(Transient)
	TMap<FIntPoint, FDinkGrassCell> GrassCells;
	UPROPERTY(Transient)
	TObjectPtr<class UMaterialParameterCollection> WindCollection;
	float LastWind = -1.f;

	// grass carpet config (environment.json)
	float GrassDensityPerM2 = 0.f;      // carpet meshes per square metre
	float AccentDensityPerM2 = 0.f;     // taller clumps, weeds, flowers
	float GrassMinCover = 0.55f;
	float GrassScaleMin = 0.6f, GrassScaleMax = 1.3f;
	float GrassFarCm = 3800.f, GrassCellCm = 800.f, GrassShadowCm = 800.f;
	int32 CoverW = 0, CoverH = 0;
	TMap<int32, TArray<uint8>> Cover;
	float LastGrassDensity = -1.f;
	FIntPoint LastGrassCell = FIntPoint(MAX_int32, MAX_int32);
	int32 LastFamilyScreen = -1;
	TSet<int32> DressedScreens;
	TArray<TWeakObjectPtr<class UStaticMeshComponent>> BareGround;
	double NextDressedCheck = 0.0;
	float GrassLeanDeg = 0.f;
	float GrassHeightMin = 1.f, GrassHeightMax = 1.f;
	float GrassFieldVariation = 0.f;                    // 0..1: how far world noise and path wear vary the carpet's height and density
	mutable float LastCover = 1.f;                      // meadow cover at the last GroundAt hit (1 away from paths)   // height scale of a carpet patch (absolute, not times the footprint scale)

	// ground colour grid (ground_colour.json), loaded on first use
	bool bGroundLoaded = false;
	int32 GroundW = 0, GroundH = 0;
	TMap<int32, TArray<uint8>> GroundColour;

	// indoor set
	UPROPERTY(Transient)
	TObjectPtr<AActor> IndoorSet;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UPointLightComponent>> IndoorFireLights;
	UPROPERTY(Transient)
	TObjectPtr<class UMaterialInterface> IndoorBlack;
	TArray<float> IndoorFireBase;
	int32 IndoorScreen = -1;
	bool bIndoorDungeon = false;
	TSet<int32> IndoorSkipScreens;
	float IndoorCeilingCm = 340.f, IndoorMarginCm = 120.f, IndoorBackdropCm = 2600.f;
	FDinkIndoorLook InteriorLook, DungeonLook;
	float FireIntensity = 0.f, FireRadiusCm = 900.f;
	FLinearColor FireColour = FLinearColor(1.f, 0.5f, 0.2f);
	TSet<FName> FireClasses;

	// burnable pines
	UPROPERTY(Transient)
	TArray<FDinkBurnable> Burnables;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> BurnBeforeMesh;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> BurnAfterMesh;
	TSet<FName> BurnScripts;
	FName BurnClass;
	int32 BurnSequence = 20;
	bool bBurnShowCard = false;
	double NextBurnCheck = 0.0;

	// --- grass roles and field structure (round 5) ---
	/** Something the carpet reacts to: rank growth along it (fence, wall, trunk, boulder, pond rim) or wear around it (door, path). */
	struct FGrassSource
	{
		FTransform WorldToLocal = FTransform::Identity;
		FBox LocalBox = FBox(ForceInit);
		FBox2D WorldBounds = FBox2D(ForceInit);   // already grown by the reach
		bool bWear = false;
		bool bShort = false;                      // round 6: short, closed turf along it (walls, fences, path rims), not thinned
		float ReachCm = 150.f;
	};
	/** A town house footprint the carpet stays out of (round 6). */
	struct FGrassBlock
	{
		FTransform WorldToLocal = FTransform::Identity;
		FBox2D LocalRect = FBox2D(ForceInit);
		FBox2D WorldBounds = FBox2D(ForceInit);
	};
	TArray<FGrassBlock> GrassBlocks;
	float GrassFieldScale = 1.f;            // height scale of the field patch (grass.field_scale): caps the general field's height
	float GrassFieldFootprint = 1.f;        // footprint scale of the field patch (grass.field_footprint): wider than tall keeps the ground covered
	float IndoorCeilingTileCm = 250.f;
	FLinearColor SkyTint = FLinearColor::White;   // environment.json sky.tint: colour of the sky light (warms shade)
	bool bSkyTint = false;
public:
	/** Review only (dink.PillbugCarcass): a carcass beside every photoreal pillbug of the current screen at the next check. */
	void ReviewCarcasses() { bCorpseReview = true; }
	/** Live sky light colour (review; dink.SkyTint r g b). */
	void SetSkyTint(const FLinearColor& Colour);
private:
	// --- round 7: clearings round low family props, authored props and ground decals; feathered carpet edge ---
	struct FGrassClear
	{
		FTransform WorldToLocal = FTransform::Identity;
		FBox LocalBox = FBox(ForceInit);
		FBox2D WorldBounds = FBox2D(ForceInit);   // already grown by the reach
		float ReachCm = 40.f;
	};
	TArray<FGrassClear> GrassClears;
	TSet<uint64> GrassClearKeys;
	float ClearMaxHeightCm = 110.f;         // grass.clear_max_height_cm: things taller than this stand in the grass (0 = no clearings)
	float ClearMaxSpanCm = 320.f;           // grass.clear_max_span_cm: longer things (fence runs, walls) are not props
	float ClearReachCm = 40.f;              // grass.clear_reach_cm: soft rim round the footprint of the lowest things
	float EdgeFeather = 1.f;                // grass.edge_feather 0..1: the carpet thins and shortens toward the end of the meadow mask
	void GatherGrassClears();
	float GrassClearAt(const FVector2D& At, const TArray<int32>& Candidates) const;
	float CoverAt(const TArray<uint8>& Mask, double MapX, double MapY) const;
	float RankEdgeShare = 0.35f;            // share of the taller rank growth kept along walls and fences (grass.rank_edge_share); trunks and pond rims keep all
	float ShortReachCm = 150.f;             // short turf within this of walls, fences, paths and doors (grass.short_reach_cm)
	void GatherGrassSources();
	float MaskCoverAt(const FVector2D& WorldXY) const;
	void GrassInfluence(const FVector2D& At, const TArray<int32>& Candidates, float& OutRank, float& OutWear, float& OutShort) const;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> GrassShortMeshes;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> GrassDryMeshes;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> GrassRankMeshes;
	TArray<FGrassSource> GrassSources;
	bool bGrassSourcesStale = true;
	float RankDensityPerM2 = 2.5f, RankReachCm = 130.f, WearReachCm = 260.f, DryShare = 0.12f, AccentCluster = 0.6f;

	// --- indoor: lit sprite cards, flames and light props ---
	struct FDinkLightProp
	{
		TObjectPtr<UStaticMesh> Mesh;
		FVector SocketCm = FVector::ZeroVector;   // flame point in Unreal mesh space
		float MountCm = 0.f;                      // pivot height above the floor
		FVector2D FlameCm = FVector2D(12.0, 26.0);  // flame card width, height
	};
	void SpawnFlame(const FVector& At, const FVector2D& SizeCm);
	void RelightIndoorCards(const TSet<int32>& ScreenNumbers);
	UPROPERTY(Transient)
	TObjectPtr<class UMaterialInterface> LitCardMaterial;
	UPROPERTY(Transient)
	TObjectPtr<class UMaterialInterface> FlameMaterial;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> LightPropMeshes;   // keeps the meshes of the prop table alive
	TMap<FName, FDinkLightProp> LightProps;            // wall_torch, hanging_lantern, brazier, candle
	TArray<TPair<TWeakObjectPtr<class UMeshComponent>, TWeakObjectPtr<class UMaterialInterface>>> IndoorCardRestore;
	TArray<TWeakObjectPtr<class UMeshComponent>> IndoorFollowed;                     // animated or scripted cards, relit frame by frame
	UPROPERTY(Transient)
	TMap<TObjectPtr<class UMaterialInterface>, TObjectPtr<class UMaterialInterface>> IndoorLitBySource;   // unlit sprite frame -> its lit copy
	UPROPERTY(Transient)
	TMap<TObjectPtr<class UMaterialInterface>, TObjectPtr<class UMaterialInterface>> IndoorLitSource;     // lit copy -> the frame it stands for

	// --- state swaps: a swapped-in mesh that follows a screen's &vision (the burnt cottage), read-only ---
	struct FDinkStateSwap
	{
		int32 Screen = 0, Vision = 0;
		FString FromName;
		TObjectPtr<UStaticMesh> From, To;
		TSet<FName> HideClasses;
		int32 State = -1;
	};
	void UpdateStateSwaps();
	TArray<FDinkStateSwap> StateSwaps;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> StateSwapMeshes;
	double NextStateCheck = 0.0;

	// --- town houses: kit modules assembled per screen by Scripts/assemble_town_houses.py (visual only) ---
	struct FDinkTownModule
	{
		FString Mesh;
		FVector2D Px = FVector2D::ZeroVector;
		FVector OffsetCm = FVector::ZeroVector;
		float Yaw = 0.f;
		FVector Scale = FVector::OneVector;
	};
	struct FDinkTownScreen
	{
		TArray<FDinkTownModule> Modules;
		TSet<FString> Hide;
		struct FFootprint { FVector2D Px = FVector2D::ZeroVector; float Yaw = 0.f; FBox2D RectCm = FBox2D(ForceInit); };
		TArray<FFootprint> Footprints;
	};
	void LoadTownHouses();
	void ApplyTownHouses(int32 ScreenNumber, const FDinkScreenCorners& Corners);

	// --- forest (13 Nov 2026, visual only): the 1997 tiles paint a closed pine forest where nobody can walk and the
	// terrain layer under it is bare leaf litter. Trees of environment.json `forest` stand on the points
	// ground_classes.json lists per screen (`trees`: map x, map y, 1 on the forest's edge; written by the world
	// export, never on ground a player can reach). No collision; `dink.Forest 0` turns it off. ---
	struct FDinkForestTree { FVector2D Px = FVector2D::ZeroVector; bool bEdge = false; };
	void LoadForest();
	void ApplyForest(int32 ScreenNumber, const FDinkScreenCorners& Corners);
	TMap<int32, TArray<FDinkForestTree>> ForestTrees;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> ForestMeshes;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> ForestUnderMeshes;
	float ForestInteriorFill = 0.55f, ForestScaleMin = 0.85f, ForestScaleMax = 1.2f, ForestUnderShare = 0.4f, ForestCullCm = 26000.f;
	TSet<int32> ForestApplied;
	UPROPERTY(Transient)
	TArray<TObjectPtr<AActor>> ForestActors;

	// --- relief and water tiles (13 Nov 2026, visual only, no collision): rock of environment.json `relief` on the
	// cliff-face, rock-mass and cave-wall points of ground_classes.json `relief` where nobody can stand (dink.Relief:
	// 0 off, 1 tier 1 = the 1997 hardness blocks the disc, 2 also enclosed pockets), and a water sheet over the
	// `water_tiles` of screens whose collision has no water fill (dink.WaterTiles). ---
	struct FDinkReliefRock { FVector2D Px = FVector2D::ZeroVector; float ClearPx = 0.f; int32 Tier = 1; };
	void ApplyRelief(int32 ScreenNumber, const FDinkScreenCorners& Corners);
	TMap<int32, TArray<FDinkReliefRock>> ReliefRocks;
	TMap<int32, TArray<FBox2D>> WaterTileRects;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMesh>> ReliefMeshes;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> WaterTileMaterial;
	float ReliefFill = 0.95f, ReliefSink = 0.12f, ReliefCullCm = 26000.f, WaterTileHeightCm = 3.f;
	TSet<int32> ReliefApplied;

	// --- pillbug carcass (round 6, visual only): where a photoreal pillbug of the current screen is killed (its actor is
	// hidden), SM_Pillbug_Corpse_PR lies until the player leaves the screen. Reads actor visibility; writes nothing.
	struct FDinkCorpseWatch
	{
		TWeakObjectPtr<AActor> Actor;
		TWeakObjectPtr<class USkeletalMeshComponent> Body;
		int32 Screen = -1;
		FVector Last = FVector::ZeroVector;
		float Yaw = 0.f;
		bool bSeen = false, bDone = false;
	};
	void UpdateCorpses(int32 CurrentScreen);

	// --- ground decals for sprite classes (round 6, environment.json `decals`): blood splats, burn holes. Visual only:
	// the placement's card is hidden and a deferred decal lies at its ground point, attached to the placement actor.
	struct FDinkDecalClass
	{
		TArray<TObjectPtr<class UMaterialInterface>> Materials;
		float SizeCm = 100.f;
	};
	void ApplyDecals(int32 ScreenNumber);
	TMap<FName, FDinkDecalClass> DecalClasses;
	UPROPERTY(Transient)
	TArray<TObjectPtr<class UMaterialInterface>> DecalMaterials;
	TSet<int32> DecalScreens;
	TArray<FDinkCorpseWatch> CorpseWatches;
	UPROPERTY(Transient)
	TArray<TObjectPtr<class UStaticMeshComponent>> Corpses;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> CorpseMesh;
	int32 CorpseScreen = -1;
	bool bCorpsesGathered = false;
	bool bCorpseReview = false;
	TMap<int32, FDinkTownScreen> TownScreens;
	TSet<int32> TownApplied;
	UPROPERTY(Transient)
	TArray<TObjectPtr<AActor>> TownActors;
};
