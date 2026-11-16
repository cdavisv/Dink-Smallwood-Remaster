#include "DinkExpanded.h"

#include "DinkGameplay.h"
#include "DinkInkStory.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMisc.h"
#include "Interfaces/IPluginManager.h"
#include "Misc/CommandLine.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"

DEFINE_LOG_CATEGORY(LogDinkExpanded);

namespace
{
	const TCHAR* ConfigSection = TEXT("DinkExpanded");

	struct FState
	{
		bool bEnabled = false;
		FDinkExpandedRegistry Registry;
		FString StoryDir;
		FString GameplayDir;
	};

	FState& State()
	{
		static FState S;
		return S;
	}

	void SetHooks(const FString& StoryDir, const FString& GameplayDir)
	{
		FDinkInkStory::StoryDataOverrideDir() = StoryDir;
		TArray<FString>& Extra = FDinkGameplayData::ExtraDataDirs();
		Extra.Remove(State().GameplayDir);
		if (!GameplayDir.IsEmpty())
		{
			Extra.AddUnique(GameplayDir);
		}
		State().StoryDir = StoryDir;
		State().GameplayDir = GameplayDir;
	}

	TArray<FName> ParsePackList(const FString& Text)
	{
		TArray<FString> Parts;
		Text.ParseIntoArray(Parts, TEXT(","));
		TArray<FName> Out;
		for (FString& P : Parts)
		{
			P.TrimStartAndEndInline();
			if (!P.IsEmpty())
			{
				Out.Add(FName(*P.ToLower()));
			}
		}
		return Out;
	}

	FString DescribeState()
	{
		const FState& S = State();
		if (!S.bEnabled)
		{
			return TEXT("DinkExpanded: OFF (the 1997 game only). Turn on with -DinkExpanded=1, DINK_EXPANDED=1 or [DinkExpanded] Enabled=True in Game.ini; restart to apply.");
		}
		FString Out = FString::Printf(TEXT("DinkExpanded: ON, %d pack(s), %d pack screen(s); story %s; tables + %s"), S.Registry.Packs.Num(),
			S.Registry.NumScreens(), *S.StoryDir, *S.GameplayDir);
		for (const FDinkPack& P : S.Registry.Packs)
		{
			Out += FString::Printf(TEXT("\n  %s (%s, x%d): %s, %d screens, %d placements, %d joins%s"), *P.Id.ToString(), *P.Wave, P.Number, *P.Status,
				P.Screens.Num(), P.Placements.Num(), P.Joins.Num(), P.bDraft ? TEXT(", DRAFT text (owner to approve)") : TEXT(""));
		}
		return Out;
	}

	FAutoConsoleCommand CmdExpanded(
		TEXT("dink.Expanded"),
		TEXT("dink.Expanded            print the DinkExpanded switch and the active content packs\n")
		TEXT("dink.Expanded 0|1 [packs] write the switch (and optional comma-separated pack list) to the user Game.ini; applies at the next start"),
		FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
		{
			if (Args.Num() >= 1)
			{
				const bool bOn = Args[0] == TEXT("1") || Args[0].Equals(TEXT("on"), ESearchCase::IgnoreCase) || Args[0].Equals(TEXT("true"), ESearchCase::IgnoreCase);
				GConfig->SetBool(ConfigSection, TEXT("Enabled"), bOn, GGameIni);
				GConfig->SetString(ConfigSection, TEXT("Packs"), Args.Num() >= 2 ? *Args[1] : TEXT(""), GGameIni);
				GConfig->Flush(false, GGameIni);
				UE_LOG(LogDinkExpanded, Display, TEXT("DinkExpanded switch saved: %s%s. It applies when the game starts again (the story and tables load at start)."),
					bOn ? TEXT("ON") : TEXT("OFF"), Args.Num() >= 2 ? *(TEXT(", packs ") + Args[1]) : TEXT(""));
			}
			UE_LOG(LogDinkExpanded, Display, TEXT("%s"), *DescribeState());
		}));
}

namespace DinkExpanded
{
	FString GetDataDir()
	{
		const TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(TEXT("DinkExpanded"));
		const FString Content = Plugin.IsValid() ? Plugin->GetContentDir() : FPaths::ProjectPluginsDir() / TEXT("DinkExpanded/Content");
		return FPaths::ConvertRelativePathToFull(Content / TEXT("Data"));
	}

	bool ReadSwitchSetting(TArray<FName>* OutPacks)
	{
		bool bOn = false;
		FString Packs;
		if (GConfig)
		{
			GConfig->GetBool(ConfigSection, TEXT("Enabled"), bOn, GGameIni);
			GConfig->GetString(ConfigSection, TEXT("Packs"), Packs, GGameIni);
		}
		const FString Env = FPlatformMisc::GetEnvironmentVariable(TEXT("DINK_EXPANDED"));
		if (!Env.IsEmpty())
		{
			bOn = Env != TEXT("0");
		}
		FString Cmd;
		if (FParse::Value(FCommandLine::Get(), TEXT("DinkExpanded="), Cmd))
		{
			bOn = Cmd != TEXT("0");
		}
		FString CmdPacks;
		if (FParse::Value(FCommandLine::Get(), TEXT("DinkExpandedPacks="), CmdPacks))
		{
			Packs = CmdPacks;
		}
		if (OutPacks)
		{
			*OutPacks = ParsePackList(Packs);
		}
		return bOn;
	}

	bool IsEnabled()
	{
		return State().bEnabled;
	}

	const FDinkExpandedRegistry& GetRegistry()
	{
		return State().Registry;
	}

	bool ApplySwitch(bool bOn, const TArray<FName>& Packs, FString* OutError)
	{
		FState& S = State();
		if (!bOn)
		{
			SetHooks(FString(), FString());
			S.Registry = FDinkExpandedRegistry();
			S.bEnabled = false;
			return true;
		}
		const FString Dir = GetDataDir();
		FDinkExpandedRegistry Registry;
		FString Error;
		if (!Registry.LoadFromFile(Dir / TEXT("packs.json"), Error))
		{
			UE_LOG(LogDinkExpanded, Error, TEXT("DinkExpanded switch is on but the packs do not load (%s): staying OFF, the 1997 game only"), *Error);
			if (OutError)
			{
				*OutError = Error;
			}
			ApplySwitch(false);
			return false;
		}
		Registry.FilterPacks(Packs);
		S.Registry = MoveTemp(Registry);
		S.bEnabled = true;
		SetHooks(Dir / TEXT("Story"), Dir / TEXT("Gameplay"));
		UE_LOG(LogDinkExpanded, Display, TEXT("%s"), *DescribeState());
		return true;
	}

	void ApplyForTest(const FDinkExpandedRegistry& Registry, const FString& StoryDir, const FString& GameplayDir)
	{
		FState& S = State();
		S.Registry = Registry;
		S.bEnabled = true;
		SetHooks(StoryDir, GameplayDir);
	}
}

class FDinkExpandedModule : public IModuleInterface
{
public:
	virtual void StartupModule() override
	{
		TArray<FName> Packs;
		if (DinkExpanded::ReadSwitchSetting(&Packs))
		{
			DinkExpanded::ApplySwitch(true, Packs);
		}
		else
		{
			UE_LOG(LogDinkExpanded, Log, TEXT("DinkExpanded is OFF (default): nothing is hooked, the 1997 game loads unchanged"));
		}
	}

	virtual void ShutdownModule() override
	{
		DinkExpanded::ApplySwitch(false);
	}
};

IMPLEMENT_MODULE(FDinkExpandedModule, DinkExpanded)
