using UnrealBuildTool;

public class DinkRemasterTarget : TargetRules
{
	public DinkRemasterTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		// As in DinkRemasterEditor.Target.cs: no unity bundles. Adaptive unity decides from the git working set which files are compiled alone, so a commit changes
		// which files share a translation unit, and DinkNarrative's file-local helpers collide (Inside in DinkBrains.cpp/DinkGameplay.cpp, NAME_Main in DinkGameplay.cpp/DinkStorySubsystem.cpp).
		bUseUnityBuild = false;
		bUseAdaptiveUnityBuild = false;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("DinkRemaster");
	}
}
