using UnrealBuildTool;

// Primary game module. Deliberately thin: gameplay rules live in the DinkCore
// plugin so they can be tested and reused without the game module.
public class DinkRemaster : ModuleRules
{
	public DinkRemaster(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "DinkCore" });
	}
}
