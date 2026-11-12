#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkRoofSourceMetadataLibrary.generated.h"

/** Exact roof-source metadata operations; no asset import, mesh build, cook or save. */
UCLASS()
class DINKIMPORT_API UDinkRoofSourceMetadataLibrary : public UBlueprintFunctionLibrary
{
 GENERATED_BODY()
public:
 /** Detached raw+resolved AssetImportData and all explicit mesh LOD filenames. Never mutates. */
 UFUNCTION(BlueprintPure, Category="Dink|Art|Roof")
 static FString InspectRoofSourceFilenames(UObject* Asset);
 /** Only exact canonical roof mesh/texture identity and existing canonical source files.
  * Validates every path before mutation. Changes filenames only, preserves timestamp/MD5,
  * refuses already-saved canonical packages; marks the new owned package dirty but never saves/builds/reimports. Caller enforces exact50/SHA. */
 UFUNCTION(BlueprintCallable, Category="Dink|Art|Roof")
 static bool SetRoofSourceFilenamesRelative(UObject* Asset, const TArray<FString>& ExpectedAbsoluteFiles);
private:
 // Internal transaction seam: no reflection/public namespace override. Only the
 // uniquely named scratch-fixture automation class may exercise this core.
 friend class FDinkRoofSourceMetadataTest;
 static bool ApplyFilenameTransaction(UObject* Asset, const TArray<FString>& ExpectedAbsoluteFiles);
};
