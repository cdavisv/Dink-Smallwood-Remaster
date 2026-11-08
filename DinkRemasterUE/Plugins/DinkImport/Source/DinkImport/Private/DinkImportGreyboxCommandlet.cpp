#include "DinkImportGreyboxCommandlet.h"
#include "DinkGreyboxImporter.h"
#include "DinkImportLog.h"

UDinkImportGreyboxCommandlet::UDinkImportGreyboxCommandlet()
{
	IsClient = false;
	IsEditor = true;
	IsServer = false;
	LogToConsole = true;
}

int32 UDinkImportGreyboxCommandlet::Main(const FString& Params)
{
	FDinkGreyboxImportOptions Options;
	FParse::Value(*Params, TEXT("Region="), Options.Region);
	FParse::Value(*Params, TEXT("Bundle="), Options.BundleDir);
	Options.bDryRun = FParse::Param(*Params, TEXT("DryRun"));

	const FDinkGreyboxImportResult R = FDinkGreyboxImporter::Run(Options);
	if (!R.bOk)
	{
		UE_LOG(LogDinkImport, Display, TEXT("DINK IMPORT FAILED: %s"), *R.Error);
		return 1;
	}
	UE_LOG(LogDinkImport, Display,
		TEXT("DINK IMPORT OK: region %s -> %s: %d screens, %d placement actors, %d placement instances, %d warps; "
			 "actors %d created / %d updated / %d deleted / %d unchanged (%d moved by hand, %d foreign kept); "
			 "assets %d created / %d updated / %d deleted / %d unchanged; %d levels saved; drift %d; %.1f s"),
		*Options.Region, *R.MapPackage, R.Screens, R.PlacementActors, R.PlacementInstances, R.Warps, R.ActorsCreated, R.ActorsUpdated,
		R.ActorsDeleted, R.ActorsUnchanged, R.ActorsMovedByHand, R.ForeignActors, R.AssetsCreated, R.AssetsUpdated, R.AssetsDeleted,
		R.AssetsUnchanged, R.LevelsSaved, R.Drift(), R.Seconds);
	return 0;
}
