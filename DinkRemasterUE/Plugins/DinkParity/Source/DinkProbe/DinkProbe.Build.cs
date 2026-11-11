using UnrealBuildTool;

// The automation-test play-through ("probe", Dink.Gameplay.Probe.*). Its own module, separate from DinkParity, so that
// it can be compiled into a Development GAME target (and so run in a packaged build): DinkParity depends on UnrealEd
// and is Editor-only. DeveloperTool = built whenever bBuildDeveloperTools is true (Editor, and Game in Development /
// DebugGame; never Shipping or Test, where WITH_DEV_AUTOMATION_TESTS is 0 anyway). See Docs/packaged_probe.md.
public class DinkProbe : ModuleRules
{
	public DinkProbe(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PrivateDependencyModuleNames.AddRange(new string[] {
			"Core", "CoreUObject", "Engine", "DinkCore", "DinkNarrative", "InkPlusPlus", "Chaos"
		});
		if (Target.bBuildEditor)
		{
			// PIE start/stop, loading the greybox map into the editor world (all behind WITH_EDITOR in the sources).
			PrivateDependencyModuleNames.Add("UnrealEd");
		}
	}
}
