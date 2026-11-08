#pragma once

#include "CoreMinimal.h"

/** Options of one greybox import run (Scripts/import_greybox.sh). */
struct FDinkGreyboxImportOptions
{
	/** Region key from the bundle (stonebrook, terris, ...) or "all". */
	FString Region = TEXT("stonebrook");
	/** Bundle directory; empty = <project>/ImportData. */
	FString BundleDir;
	/** Report drift only: build nothing, save nothing. */
	bool bDryRun = false;
};

/** Result counters of one run (also written to Saved/Import/import_<region>.json). */
struct FDinkGreyboxImportResult
{
	bool bOk = false;
	FString Error;
	FString MapPackage;
	int32 Screens = 0;
	int32 PlacementActors = 0;
	int32 PlacementInstances = 0;
	int32 Warps = 0;
	int32 ActorsCreated = 0;
	int32 ActorsUpdated = 0;
	int32 ActorsDeleted = 0;
	int32 ActorsUnchanged = 0;
	int32 ActorsMovedByHand = 0;
	int32 ForeignActors = 0;
	int32 AssetsCreated = 0;
	int32 AssetsUpdated = 0;
	int32 AssetsDeleted = 0;
	int32 AssetsUnchanged = 0;
	int32 LevelsSaved = 0;
	double Seconds = 0.0;

	int32 Drift() const
	{
		return ActorsCreated + ActorsUpdated + ActorsDeleted + AssetsCreated + AssetsUpdated + AssetsDeleted;
	}
};

/**
 * Pipeline stage 6: turns the import bundle (ImportData/, written by
 * Scripts/export_import_bundle.py) into a walkable greybox under /Game/Dink/_Generated.
 *
 * Idempotent: generated assets carry content hashes (Content/Dink/_Generated/import_manifest.json)
 * and generated actors carry tags DinkGenerated / DinkKey=<id> / DinkHash=<hash>. A re-run
 * rebuilds only what changed, deletes generated actors whose origin left the import, leaves
 * untagged ("foreign") actors alone, saves only changed packages, and reports the drift.
 */
class DINKIMPORT_API FDinkGreyboxImporter
{
public:
	static FDinkGreyboxImportResult Run(const FDinkGreyboxImportOptions& Options);

	/** /Game/Dink/_Generated/Maps/L_Greybox_<Region> ("World" for all). */
	static FString MapPackageFor(const FString& Region);
	/** Sublevel package of a layout group (mainland, joppa, darklands, snow_isle, fragments, interiors). */
	static FString SublevelPackageFor(const FString& Region, const FString& Group);
	static FString PascalCase(const FString& Key);
};
