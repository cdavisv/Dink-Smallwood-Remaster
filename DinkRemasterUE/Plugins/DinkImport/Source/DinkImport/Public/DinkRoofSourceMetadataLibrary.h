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
 /** Read-only capability for the exact shared8roof/9texture source contracts. */
 UFUNCTION(BlueprintPure, Category="Dink|Art|Roof")
 static bool SupportsSharedRoofSourceFilenames();
 /** Only exact canonical roof or shared8roof/9texture identity and existing canonical source files.
  * Validates every path before mutation. Changes filenames only, preserves timestamp/MD5,
  * refuses already-saved canonical packages; marks the new owned package dirty but never saves/builds/reimports. Caller enforces exact50 legacy or exact23 shared trial/SHA. */
 UFUNCTION(BlueprintCallable, Category="Dink|Art|Roof")
 static bool SetRoofSourceFilenamesRelative(UObject* Asset, const TArray<FString>& ExpectedAbsoluteFiles);
 /** Capability for exactly four unsaved InteriorGableRecessV1 meshes; no namespace override. */
 UFUNCTION(BlueprintPure, Category="Dink|Art|Roof")
 static bool SupportsInteriorGableRecessSourceFilenames();
 /** One canonical existing FBX and one source LOD only. Metadata-only transaction;
  * refuses saved/foreign assets, preserves source MD5/timestamp and never imports/builds/saves. */
 UFUNCTION(BlueprintCallable, Category="Dink|Art|Roof")
 static bool SetInteriorGableRecessSourceFilenamesRelative(UObject* Asset, const TArray<FString>& ExpectedAbsoluteFiles);
 /** Read-only capability for exact House439 fresh1mesh/30texture source metadata. */
 UFUNCTION(BlueprintPure, Category="Dink|Art|House439")
 static bool SupportsHouse439SharedSourceFilenames();
 /** Exact House439 trial packages only; filename metadata, no save/build/reimport. */
 UFUNCTION(BlueprintCallable, Category="Dink|Art|House439")
 static bool SetHouse439SourceFilenamesRelative(UObject* Asset, const TArray<FString>& ExpectedAbsoluteFiles);
 /** Read-only capability for exact fresh4fireplace meshes/24textures; no production edits. */
 UFUNCTION(BlueprintPure, Category="Dink|Art|Fireplace")
 static bool SupportsFireplaceFiredClayV4SourceFilenames();
 /** Exact fresh fireplace trial filenames only; validates all scope before mutation; no save/build/reimport. */
 UFUNCTION(BlueprintCallable, Category="Dink|Art|Fireplace")
 static bool SetFireplaceFiredClayV4SourceFilenamesRelative(UObject* Asset, const TArray<FString>& ExpectedAbsoluteFiles);
private:
 // Internal transaction seam: no reflection/public namespace override. Only the
 // uniquely named scratch-fixture automation class may exercise this core.
 friend class FDinkRoofSourceMetadataTest;
 static bool ApplyFilenameTransaction(UObject* Asset, const TArray<FString>& ExpectedAbsoluteFiles);
};
