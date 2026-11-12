using UnrealBuildTool;

public class DinkNarrative : ModuleRules
{
	public DinkNarrative(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "DinkCore", "InkPlusPlus" });
		PrivateDependencyModuleNames.AddRange(new string[] { "Json", "Slate", "SlateCore", "InputCore", "PhysicsCore", "Chaos" });
	}
}
