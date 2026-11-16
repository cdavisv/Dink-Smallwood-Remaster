using UnrealBuildTool;

public class DinkExpanded : ModuleRules
{
	public DinkExpanded(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "DinkCore", "DinkNarrative" });
		PrivateDependencyModuleNames.AddRange(new string[] { "Json", "Projects" });
		if (Target.bBuildEditor)
		{
			// Editor-only tests (PIE on the generated world).
			PrivateDependencyModuleNames.AddRange(new string[] { "UnrealEd" });
		}
	}
}
