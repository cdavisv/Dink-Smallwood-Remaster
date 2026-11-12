#pragma once
#include "CoreMinimal.h"
#include "DinkHardnessSession.h"

/** Strict additive data consumer. No fallback to erasing top-owner map bytes. */
struct DINKNARRATIVE_API FDinkRuntimeHardnessSource
{
    DinkHardness::Layers::Pixels TileBase;
    std::vector<DinkHardness::Stamp> InitialStamps;
    static bool Load(const FString& File, int32 ExpectedVision,
                     FDinkRuntimeHardnessSource& Out, FString& Error);
};
