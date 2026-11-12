using UnrealBuildTool;

// Developer-only module: automation tests that check DinkCore against the
// documented rules of the 1997 game. Never shipped.
public class DinkParity : ModuleRules
{
	public DinkParity(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PrivateDependencyModuleNames.AddRange(new string[] {
			"Core", "CoreUObject", "Engine", "InputCore", "DinkCore", "DinkNarrative", "InkPlusPlus", "Json", "UnrealEd", "MeshDescription", "StaticMeshDescription", "Chaos", "EngineSettings"
		});
	}
}
