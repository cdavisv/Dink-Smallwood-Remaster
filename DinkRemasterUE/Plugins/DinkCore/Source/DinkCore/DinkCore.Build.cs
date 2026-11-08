using UnrealBuildTool;

public class DinkCore : ModuleRules
{
	public DinkCore(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "GameplayTags" });
		PrivateDependencyModuleNames.AddRange(new string[] { "Json", "EnhancedInput", "InputCore" });
	}
}
