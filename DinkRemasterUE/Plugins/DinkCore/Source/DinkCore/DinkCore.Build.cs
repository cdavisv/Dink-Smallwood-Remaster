using UnrealBuildTool;

public class DinkCore : ModuleRules
{
	public DinkCore(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "GameplayTags", "ProceduralMeshComponent" });
		// ProceduralMeshComponent (public: UDinkPlayerBlockerComponent): PR41 runtime screen collision. PhysicsCore/Chaos:
		// read-only cooked family-fit descriptors; no second physical authority.
		// RenderCore/RHI: frame timings (game, render, GPU ms) of dink.CaptureScript `fps` lines (review only).
		PrivateDependencyModuleNames.AddRange(new string[] { "Json", "EnhancedInput", "InputCore", "PhysicsCore", "Chaos", "RenderCore", "RHI" });
	}
}
