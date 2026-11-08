#pragma once

#include "CoreMinimal.h"
#include "Commandlets/Commandlet.h"
#include "DinkImportGreyboxCommandlet.generated.h"

/**
 * Headless entry point of the greybox importer (wrapped by Scripts/import_greybox.sh):
 *
 *   UnrealEditor-Cmd <project> -run=DinkImportGreybox -Region=stonebrook|all [-Bundle=<dir>] [-DryRun]
 *
 * Prints one "DINK IMPORT OK ..." or "DINK IMPORT FAILED ..." line; returns 0 on success.
 */
UCLASS()
class UDinkImportGreyboxCommandlet : public UCommandlet
{
	GENERATED_BODY()

public:
	UDinkImportGreyboxCommandlet();
	virtual int32 Main(const FString& Params) override;
};
