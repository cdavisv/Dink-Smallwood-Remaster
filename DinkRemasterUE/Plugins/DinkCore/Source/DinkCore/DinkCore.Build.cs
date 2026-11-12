using UnrealBuildTool;

public class DinkCore : ModuleRules
{
	public DinkCore(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "GameplayTags" });
		// ProceduralMeshComponent: PR41 runtime screen collision. PhysicsCore/Chaos:
		// read-only cooked family-fit descriptors; no second physical authority.
		PrivateDependencyModuleNames.AddRange(new string[] { "Json", "EnhancedInput", "InputCore", "ProceduralMeshComponent", "PhysicsCore", "Chaos" });
	}
}
