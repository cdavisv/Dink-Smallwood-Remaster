#pragma once
#include "CoreMinimal.h"
#include <array>
#include "DinkHardnessSession.h"

/** Strict additive data consumer. No fallback to erasing top-owner map bytes. */
struct DINKNARRATIVE_API FDinkRuntimeHardnessSource
{
    std::array<int,100> EditorHard{}; // index0 unused; explicit raw slots1..99
    DinkHardness::Layers::Pixels TileBase;
    std::vector<DinkHardness::Stamp> InitialStamps;
    static bool Load(const FString& File, int32 ExpectedVision,
                     FDinkRuntimeHardnessSource& Out, FString& Error);
};

/** Raw current-smallMap flags only; selecting this data does not admit a map/body. */
struct DINKNARRATIVE_API FDinkEditorHardSource
{
    std::array<int,100> EditorHard{};
    static bool Parse(const FString& Text,int32 Screen,FDinkEditorHardSource& Out,FString& Error);
    static bool Load(const FString& File,int32 Screen,FDinkEditorHardSource& Out,FString& Error);
};
