#pragma once

#include "CoreMinimal.h"
#include "DinkLayout.h"

DINKEXPANDED_API DECLARE_LOG_CATEGORY_EXTERN(LogDinkExpanded, Log, All);

/**
 * DinkExpanded: the remaster's additive content (REMASTER_PLAN section 11, rule 5: "Base game is sacred, expanded content is
 * additive and lives in a separate plugin that can be switched off"). Design: doc/remaster/EXPANDED_CONTENT.md.
 *
 * A content pack is data (Plugins/DinkExpanded/Packs/<pack>/pack.toml) plus DinkC scripts (the .c files in Packs/<pack>/story), built by
 * tools/expanded into Plugins/DinkExpanded/Content/Data: packs.json (this registry), Gameplay/ (placements.csv and screens.csv rows
 * of the pack's screens, their hardness) and Story/ (the 1997 story with the packs' knots and VARs added; every 1997 knot is
 * byte-identical, checked by the build).
 *
 * The switch is off by default. Off, this module sets nothing: the 1997 story, tables and world load exactly as without the plugin.
 */

/** A rectangle in original map pixels of one screen (half-open: X0 <= x < X1, Y0 <= y < Y1). */
struct DINKEXPANDED_API FDinkPackRect
{
	int32 X0 = 0;
	int32 Y0 = 0;
	int32 X1 = 0;
	int32 Y1 = 0;
	bool IsValid() const { return X0 < X1 && Y0 < Y1 && X0 >= 0 && Y0 >= 0 && X1 <= 600 && Y1 <= 400; }
	FVector2D Centre() const { return FVector2D((X0 + X1) * 0.5, (Y0 + Y1) * 0.5); }
};

/** A pack sheet: the pack's screens laid out as one rectangle grid, placed beyond everything the world already holds. */
struct DINKEXPANDED_API FDinkPackSheet
{
	FName Id;
	/** Size of one screen: the median size of the loaded world's 1997 screens of this kind (settlement, wilderness, dungeon, interior). */
	FName Kind;
	/** Unit direction (x east, y south) the sheet is pushed away from what is already placed. */
	FVector2D Direction = FVector2D(-1.0, 0.0);
	/** Gap to everything placed before, metres (the same rule as tools/analyse min_gap_m: past the fog horizon). */
	double GapM = 1500.0;
};

/** One screen a pack owns. Its number is an unused 1997 map slot (no map record, no script mentions it); see the doc. */
struct DINKEXPANDED_API FDinkPackScreen
{
	int32 Screen = 0;
	/** Column and row on its sheet. */
	FIntPoint Grid = FIntPoint::ZeroValue;
	FName Sheet;
	FString Name;
	FName Kind;
	FName Region;
	FName BaseScript;
	int32 MusicRaw = 0;
	bool bIndoor = false;
	/** Hardness-1 rectangles (trees, rocks, walls of the greybox). */
	TArray<FDinkPackRect> Solids;
};

/** A placement on a pack screen (also a row of Gameplay/placements.csv with origin S<screen>_P<index>). */
struct DINKEXPANDED_API FDinkPackPlacement
{
	int32 Screen = 0;
	int32 Index = 0;
	int32 X = 0;
	int32 Y = 0;
	int32 Seq = 0;
	int32 Frame = 0;
	int32 Brain = 0;
	int32 Size = 100;
	FName Script;
	/** npc, creature, item, prop: the greybox shape. */
	FName Kind;
	FString Name;
	bool bHard = false;
};

/**
 * A designed join: how a pack's screens attach to the 1997 world without changing it. The 1997 side is an overlay trigger only:
 * no 1997 tile, hardness pixel, placement or script changes, and nothing at all exists there while the switch is off.
 */
struct DINKEXPANDED_API FDinkPackJoin
{
	FString Id;
	/** 1997 screen and trigger rectangle (map pixels) Dink walks into. */
	int32 FromScreen = 0;
	FDinkPackRect FromRect;
	/** Pack screen and point Dink arrives at. */
	int32 ToScreen = 0;
	FVector2D ToPoint = FVector2D::ZeroVector;
	/** Pack-side trigger back. */
	int32 BackScreen = 0;
	FDinkPackRect BackRect;
	/** 1997 screen and point Dink comes back to (also where a save made inside the pack puts him when packs are off). */
	int32 ReturnScreen = 0;
	FVector2D ReturnPoint = FVector2D::ZeroVector;
	/** Optional condition on a pack fact (empty = always open). */
	FName RequiresFact;
	int32 RequiresAtLeast = 0;
};

struct DINKEXPANDED_API FDinkPack
{
	FName Id;
	/** Wave number: scripts are named x<Number>-*, globals &x<Number>_* (the pack's namespace). */
	int32 Number = 0;
	FString Name;
	FString Wave;
	FString Status;
	/** Every line is a draft for the owner's approval. */
	bool bDraft = true;
	TArray<FDinkPackSheet> Sheets;
	TArray<FDinkPackScreen> Screens;
	TArray<FDinkPackPlacement> Placements;
	TArray<FDinkPackJoin> Joins;
	FString ScriptPrefix() const { return FString::Printf(TEXT("x%d-"), Number); }
	FString GlobalPrefix() const { return FString::Printf(TEXT("x%d_"), Number); }
	const FDinkPackSheet* FindSheet(FName SheetId) const;
};

/** Content/Data/packs.json, the packs the build exported. */
struct DINKEXPANDED_API FDinkExpandedRegistry
{
	TArray<FDinkPack> Packs;

	bool LoadFromJson(const FString& Text, FString& OutError);
	bool LoadFromFile(const FString& Path, FString& OutError);
	/** Keeps only the named packs (empty list = keep all). */
	void FilterPacks(const TArray<FName>& Keep);
	/** Namespace and shape rules (the runtime repeats the build's checks it can make alone). Empty = valid. */
	TArray<FString> Validate() const;

	const FDinkPack* FindPack(FName Id) const;
	const FDinkPackScreen* FindScreen(int32 Screen, const FDinkPack** OutPack = nullptr) const;
	bool IsPackScreen(int32 Screen) const { return FindScreen(Screen) != nullptr; }
	/** True for a script in some pack's namespace (x<n>-...). */
	bool IsPackScript(FName Script) const;
	int32 NumScreens() const;
};

namespace DinkExpanded
{
	/** Plugins/DinkExpanded/Content/Data (the build's output). */
	DINKEXPANDED_API FString GetDataDir();

	/**
	 * The switch, read once at module start: command line -DinkExpanded=0|1, else environment DINK_EXPANDED=0|1, else Game ini
	 * [DinkExpanded] Enabled=True|False (default False). [DinkExpanded] Packs=a,b limits the packs (default: all built packs).
	 */
	DINKEXPANDED_API bool ReadSwitchSetting(TArray<FName>* OutPacks = nullptr);

	/** True while the switch is applied (hooks set, registry loaded). */
	DINKEXPANDED_API bool IsEnabled();

	/** The active packs (empty while off). */
	DINKEXPANDED_API const FDinkExpandedRegistry& GetRegistry();

	/**
	 * Applies the switch. On: loads DataDir/packs.json (filtered to Packs), points the story at DataDir/Story and adds
	 * DataDir/Gameplay to the gameplay tables. Off: clears both hooks and the registry. The story and tables read the hooks when they
	 * load (game instance start), so a change applies to the next game instance, not the running one.
	 */
	DINKEXPANDED_API bool ApplySwitch(bool bOn, const TArray<FName>& Packs = {}, FString* OutError = nullptr);

	/** Tests: apply a registry already in memory with these data directories (empty strings = do not set that hook). */
	DINKEXPANDED_API void ApplyForTest(const FDinkExpandedRegistry& Registry, const FString& StoryDir, const FString& GameplayDir);

	/** One 1997 screen of the loaded world, as the layout sees it. */
	struct FBaseScreen
	{
		int32 Screen = 0;
		FName Kind;
		FDinkScreenCorners Corners;
	};

	/**
	 * World corners of every pack screen. Scale-agnostic by construction: a pack screen takes the median size of the loaded world's
	 * screens of its sheet's kind, and each sheet is pushed along its direction until it is GapM clear of the bounding box of
	 * everything placed before it (the whole 1997 world as loaded, then earlier pack sheets). Nothing here knows the 1997 map's
	 * size or the region scales: whatever tools/analyse and regions.toml produce, the packs sit beyond it.
	 */
	DINKEXPANDED_API TMap<int32, FDinkScreenCorners> LayoutPackScreens(const TArray<FBaseScreen>& Base, const FDinkExpandedRegistry& Registry);

	/** Screen size (metres, width x height) of a kind in the loaded world: the median, or the plan's defaults when none is loaded. */
	DINKEXPANDED_API FVector2D MedianScreenSize(const TArray<FBaseScreen>& Base, FName Kind);
}
