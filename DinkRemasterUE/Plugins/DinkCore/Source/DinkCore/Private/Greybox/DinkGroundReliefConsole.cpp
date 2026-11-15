// Ground relief review switch: M_Env_Terrain marches the view ray through its layers' height maps (parallax
// occlusion, Scripts/import_environment_materials.py) and scales the depth by MPC_Env_Ground.ReliefScale.
// Visual only: nothing here touches collision, hardness or placements.
#include "DinkCoreModule.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialParameterCollection.h"

static FAutoConsoleCommandWithWorldAndArgs GDinkGroundReliefCommand(
	TEXT("dink.GroundRelief"), TEXT("dink.GroundRelief <scale>: scale of the ground's parallax relief in this world (1 = as authored, 0 = flat sheet, no march)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UMaterialParameterCollection* Collection = LoadObject<UMaterialParameterCollection>(nullptr,
			TEXT("/Game/Dink/Materials/Environment/MPC_Env_Ground.MPC_Env_Ground"), nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (!World || !Collection || Args.Num() != 1 || !Args[0].IsNumeric())
		{
			UE_LOG(LogDink, Display, TEXT("usage: dink.GroundRelief <scale> (needs MPC_Env_Ground: run Scripts/import_environment_materials.sh)"));
			return;
		}
		const float Scale = FMath::Clamp(FCString::Atof(*Args[0]), 0.f, 4.f);
		UKismetMaterialLibrary::SetScalarParameterValue(World, Collection, TEXT("ReliefScale"), Scale);
		UE_LOG(LogDink, Display, TEXT("DINK GROUND RELIEF: scale %.2f"), Scale);
	}));
