using UnrealBuildTool;

public class DinkImport : ModuleRules
{
	public DinkImport(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "DinkCore" });
		PrivateDependencyModuleNames.AddRange(new string[] {
			"UnrealEd", "Json", "ImageWrapper", "MaterialEditor", "MeshDescription", "StaticMeshDescription",
			"AssetRegistry", "LevelEditor", "RenderCore", "ImageCore", "RHI", "PhysicsCore", "Chaos", "DinkNarrative"
		});
	}
}
