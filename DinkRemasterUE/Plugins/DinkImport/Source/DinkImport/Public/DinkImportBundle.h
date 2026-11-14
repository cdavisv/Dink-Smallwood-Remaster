#pragma once

#include "CoreMinimal.h"
#include "DinkLayout.h"

/**
 * In-memory form of the import bundle written by Scripts/export_import_bundle.py (ImportData/).
 * Field meanings are documented in that script; this is a straight read of its JSON.
 */
/** One layer of the master terrain material chosen for a screen (photoreal pass). */
struct FDinkBundleGroundLayer
{
	FString Name;            // catalogue name, textures are T_Env_<Name>_{BC,N,ORM,H,Macro}
	double TileCm = 400.0;
	double NormalStrength = 1.0;
	double Backlight = 0.0;   // foliage transmission when viewed against the sun
	double Emissive = 0.0;    // strength of the layer's emissive mask (T_Env_<Name>_E), 0 = none
	double Structured = 0.0;  // 1 = a laid pattern (boards, flagstones): no UV warp, no variant or far lookup
	double Drift = 1.0;       // 0 = no field-scale value drift or dry patches on this layer (floors, snow)
};

struct FDinkBundleScreen
{
	FString Id;              // SCR_412
	int32 Screen = 0;
	int32 Col = 0;
	int32 Row = 0;
	FString Region, RegionName, Name, Kind, Sheet, Group;
	bool bIndoor = false;
	int32 MusicRaw = 0;
	FString MusicAction, MusicFile, BaseScript;
	bool bScreenlock = false;
	bool bLocking = false;
	TArray<FString> EncounterScripts;
	FString InteriorId, InteriorName;
	TArray<int32> VisionValues;
	TMap<int32, TArray<FString>> VisionRules;
	FDinkScreenCorners Corners;   // metres
	FString GroundImage, GroundHash, CollisionHash, Hash;
	/** Terrain layers A, B, C and their RGB weight mask; empty when the screen keeps its painted ground. */
	TArray<FDinkBundleGroundLayer> GroundLayers;
	FString GroundMask, GroundMaskHash;
	/** Non-empty when the exporter left the screen out (reason), e.g. a layout overlap. */
	FString Excluded;
};

struct FDinkBundleCard
{
	FString Sprite;          // sprite key "32_01"
	FString ScaleMode;       // layout | base
	double WidthM = 0, HeightM = 0, OffsetXM = 0, OffsetZM = 0;
};

struct FDinkBundlePlacement
{
	FString Id;              // S412_P03
	int32 Screen = 0, Index = 0;
	double MapX = 0, MapY = 0;
	FVector2D World = FVector2D::ZeroVector;   // metres (tools/analyse world_layout.json)
	double MPerPx = 0, ScaleX = 0, ScaleY = 0, RotDeg = 0;
	int32 Seq = 0, Frame = 0, Type = 0, SizePercent = 100, Brain = 0, Vision = 0;
	FString Kind, Script, ScriptKind, ClassId, Category, Name, Treatment, Representation, Group, Region, Hash;
	TArray<FString> VisionRule;
	bool bHasCard = false;
	FDinkBundleCard Card;
	bool bHasHardness = false;
	FIntRect HardRect;       // map pixels [x0,y0,x1,y1)
	bool bIsWarp = false;
};

struct FDinkBundleWarp
{
	FString Id, Source, Placement, TriggerMode, Kind, Script, Note, Hash;
	int32 SrcScreen = 0, DstScreen = 0;
	double DstX = 0, DstY = 0;
	bool bDstValid = false;
	FVector2D DstWorld = FVector2D::ZeroVector;  // metres
	bool bHasQuad = false;
	FVector2D Quad[4];       // metres: (x0,y0) (x1,y0) (x1,y1) (x0,y1)
	int32 AnimSeq = 0, Vision = 0;
	TArray<FString> ReturnWarps;
	bool bOneWay = false;
};

struct FDinkBundleSprite
{
	FString Key, File, Hash;
	int32 Width = 0, Height = 0, TexWidth = 0, TexHeight = 0;
};

/** Merged hardness rectangles of one screen, per collision class (solid, low, sprite, warp, fill_water, fill_solid). */
struct FDinkBundleCollision
{
	TMap<FString, TArray<FIntRect>> ByClass;
};

struct FDinkBundle
{
	FString Dir;
	FString Schema;
	FString SourceCommit;
	double BaseMetresPerPixel = 0.025;
	int32 StartScreen = 1;
	double StartX = 0, StartY = 0;
	int32 StartDir = 4;
	FVector2D StartWorld = FVector2D::ZeroVector;
	FString StartNote;
	TArray<FString> Regions;
	TArray<FString> Problems;
	/** Hash of the bundle's data files (bundle.json "files"): changes whenever any input changes. */
	FString FilesHash;

	TArray<FDinkBundleScreen> Screens;
	TArray<FDinkBundlePlacement> Placements;
	TArray<FDinkBundleWarp> Warps;
	TMap<FString, FDinkBundleSprite> Sprites;
	TMap<FString, FDinkBundleCollision> Collision;  // by screen id

	TMap<int32, int32> ScreenIndex;  // screen number -> index in Screens

	const FDinkBundleScreen* FindScreen(int32 Number) const
	{
		const int32* I = ScreenIndex.Find(Number);
		return I ? &Screens[*I] : nullptr;
	}

	/** Reads every JSON of the bundle. Returns false with a message on any missing file or schema mismatch. */
	bool Load(const FString& InDir, FString& OutError);

	/** Project-relative default location: <project>/ImportData. */
	static FString DefaultDir();
};
