#pragma once
#include "CoreMinimal.h"
#include "DinkLayout.h"
class ADinkGreyboxScreen;
class ADinkScreenVolume;

/** Runtime-staged authority for immutable ground/fill only. This descriptor is
 * additive generated Data; producer writes only explicitly requested output. */
struct DINKNARRATIVE_API FDinkHardnessFoundationSource
{
    int32 Screen = 0;
    FDinkScreenCorners Corners;
    float HeightCm = 300.f;
    FString SourceTextSha1, CollisionSourceHash, SolidMesh, LowMesh;
    TArray<FIntRect> SolidFill, WaterFill;
    TMap<FString,FString> GameplaySha1;
    static bool Load(const FString& File,int32 ExpectedScreen,FDinkHardnessFoundationSource& Out,FString& Error);
    bool VerifyGameplayInputs(FString& Error) const;
    bool VerifyInstances(ADinkScreenVolume& Volume,ADinkGreyboxScreen& Host,FString& Error,bool RequireMarker=true) const;
};
