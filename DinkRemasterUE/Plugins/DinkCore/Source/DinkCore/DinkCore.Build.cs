using UnrealBuildTool;

public class DinkCore : ModuleRules
{
	public DinkCore(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "GameplayTags" });
		// ProceduralMeshComponent: the runtime solid collision of a screen whose hardness a script redraws (Greybox/DinkGreyboxHardness.cpp).
		PrivateDependencyModuleNames.AddRange(new string[] { "Json", "EnhancedInput", "InputCore", "ProceduralMeshComponent" });
	}
}
