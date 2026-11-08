using UnrealBuildTool;

public class DinkRemasterEditorTarget : TargetRules
{
	public DinkRemasterEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		bUseUnityBuild = false;
		bUseAdaptiveUnityBuild = false;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("DinkRemaster");
	}
}
