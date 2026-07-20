// Copyright GASP_AUU58. All Rights Reserved.

using UnrealBuildTool;

public class AssetLoader : ModuleRules
{
	public AssetLoader(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				"CoreUObject",
				"Engine",
			}
		);

		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				// StreamableManager lives here
			}
		);
	}
}
