#pragma once
#include "DinkArtSubsystem.h"

#if WITH_DEV_AUTOMATION_TESTS
// Shared single definition for editor tests and runtime-capable dev diagnostics.
struct FDinkExteriorPortalTestAccess
{
    static TArray<FDinkExteriorCameraRule>& Rules(UDinkArtSubsystem& Art){return Art.ExteriorCameraRules;}
    static void Register(UDinkArtSubsystem& Art,const FString& File,const TSharedPtr<FJsonObject>& Row,int32 Screen,UStaticMeshComponent* Mesh)
    {Art.RegisterExteriorCameraRule(File,Row,Screen,Mesh);}
    static const FDinkExteriorCameraRule* Actual(UDinkArtSubsystem& Art)
    {
        const FDinkExteriorCameraRule* Result=nullptr;
        for(const auto& R:Art.ExteriorCameraRules)
            if(R.Manifest==TEXT("stonebrook_exterior.json")&&R.Element==TEXT("DinksCottage")&&R.Screen==439&&R.Component.IsValid())
            {if(Result)return nullptr;Result=&R;}
        return Result;
    }
};
#endif
