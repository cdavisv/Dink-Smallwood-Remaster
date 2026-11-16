#include "DinkBeatCapture.h"

#include "Containers/Ticker.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkStorySubsystem.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

DEFINE_LOG_CATEGORY_STATIC(LogDinkBeat, Log, All);

namespace DinkBeatCapture
{
namespace
{
	struct FPending
	{
		uint64 DueFrame = 0;
		FString Kind;
		FString Detail;
	};

	struct FState
	{
		FString Dir;
		int32 Counter = 0;
		TArray<FPending> Queue;
		TSet<int32> SeenScreens;
		int32 LastStory = INDEX_NONE;
		int32 LastScreen = INDEX_NONE;
		int32 LastLife = INDEX_NONE;
		bool bMenu = false;
		double LastWall = 0.0;
		double LastPeriodic = 0.0;
		// The last event processed (UDinkStorySubsystem::Events is a bounded list: find it again from the end).
		bool bHaveEvent = false;
		double EventTime = 0.0;
		FName EventKind;
		FString EventText;
		FTSTicker::FDelegateHandle Ticker;
	};

	FState& State()
	{
		static FState S;
		return S;
	}

	UWorld* GameWorld()
	{
		if (!GEngine) { return nullptr; }
		for (const FWorldContext& Context : GEngine->GetWorldContexts())
		{
			if ((Context.WorldType == EWorldType::Game || Context.WorldType == EWorldType::PIE) && Context.World())
			{
				return Context.World();
			}
		}
		return nullptr;
	}

	FString Clean(const FString& In)
	{
		FString Out;
		for (const TCHAR Ch : In)
		{
			Out.AppendChar(FChar::IsAlnum(Ch) ? Ch : TCHAR('_'));
			if (Out.Len() >= 40) { break; }
		}
		while (Out.ReplaceInline(TEXT("__"), TEXT("_"))) {}
		return Out;
	}

	void Shoot(UDinkStorySubsystem* Story, const FPending& P)
	{
		FState& S = State();
		UDinkFactSubsystem* F = Story ? Story->GetFacts() : nullptr;
		const int32 Screen = F ? F->GetFact(TEXT("player_map")) : 0;
		const FString File = S.Dir / FString::Printf(TEXT("%04d_%s_%s.png"), ++S.Counter, *Clean(P.Kind), *Clean(P.Detail));
		FScreenshotRequest::RequestScreenshot(File, true, false);
		UE_LOG(LogDinkBeat, Display, TEXT("DINK BEAT: %d %s %s screen=%d story=%d life=%d/%d gold=%d frozen=%d t=%.0f file=%s"), S.Counter, *P.Kind, *P.Detail,
			Screen, F ? F->GetFact(TEXT("story")) : 0, F ? F->GetFact(TEXT("life")) : 0, F ? F->GetFact(TEXT("lifemax")) : 0,
			F ? F->GetFact(TEXT("gold")) : 0, Story && Story->GetDirector() ? (Story->GetDirector()->GetDink().bFrozen ? 1 : 0) : 0,
			Story ? Story->GetNowMs() : 0.0, *FPaths::GetCleanFilename(File));
	}

	void ScanEvents(UDinkStorySubsystem* Story)
	{
		FState& S = State();
		const TArray<FDinkNarrativeEvent>& Events = Story->Events;
		int32 First = 0;
		if (S.bHaveEvent)
		{
			First = Events.Num();
			for (int32 i = Events.Num() - 1; i >= 0; --i)
			{
				const FDinkNarrativeEvent& E = Events[i];
				if (E.TimeMs == S.EventTime && E.Kind == S.EventKind && E.Text == S.EventText) { First = i + 1; break; }
				if (E.TimeMs < S.EventTime) { First = i + 1; break; }
			}
		}
		for (int32 i = First; i < Events.Num(); ++i)
		{
			const FDinkNarrativeEvent& E = Events[i];
			const FString Kind = E.Kind.ToString();
			if (Kind == TEXT("cmd") && (E.Text.StartsWith(TEXT("playsound")) || E.Text.StartsWith(TEXT("playmidi"))))
			{
				// Compared with the audio subsystem's "Playing approved sound/music" lines: a cue the script asked for and nothing played.
				UE_LOG(LogDinkBeat, Display, TEXT("DINK CUE: %s t=%.0f"), *E.Text, E.TimeMs);
			}
			if (Kind == TEXT("load")) { Request(TEXT("load"), E.Text, 45); }
			else if (Kind == TEXT("error")) { Request(TEXT("error"), E.Text); UE_LOG(LogDinkBeat, Warning, TEXT("DINK BEAT ERROR: %s %s"), *E.Text, *E.Detail); }
			else if (Kind == TEXT("game") && E.Text.StartsWith(TEXT("screenlock"))) { Request(TEXT("screenlock"), E.Text, 20); }
			else if (Kind == TEXT("game") && E.Text.StartsWith(TEXT("level-up"))) { Request(TEXT("levelup"), E.Text, 5); }
			else if (Kind == TEXT("cmd") && (E.Text.StartsWith(TEXT("save_game")) || E.Text.StartsWith(TEXT("load_game")) ||
				E.Text.StartsWith(TEXT("restart_game")) || E.Text.StartsWith(TEXT("kill_game")) || E.Text.StartsWith(TEXT("playmidi"))))
			{
				Request(E.Text.StartsWith(TEXT("playmidi")) ? TEXT("music") : TEXT("cmd"), E.Text, 10);
			}
		}
		if (Events.Num() > 0)
		{
			const FDinkNarrativeEvent& L = Events.Last();
			S.bHaveEvent = true;
			S.EventTime = L.TimeMs;
			S.EventKind = L.Kind;
			S.EventText = L.Text;
		}
	}

	bool Tick(float)
	{
		FState& S = State();
		const double Wall = FPlatformTime::Seconds();
		const double Dt = S.LastWall > 0.0 ? Wall - S.LastWall : 0.0;
		S.LastWall = Wall;
		if (S.Dir.IsEmpty()) { return true; }
		UWorld* World = GameWorld();
		UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
		UDinkStorySubsystem* Story = GI ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		if (!Story || !Story->IsReady() || !Story->GetFacts()) { return true; }
		UDinkFactSubsystem* F = Story->GetFacts();
		const int32 Screen = F->GetFact(TEXT("player_map"));
		if (Dt > 0.2)
		{
			UE_LOG(LogDinkBeat, Display, TEXT("DINK HITCH: %.0f ms screen=%d t=%.0f"), Dt * 1000.0, Screen, Story->GetNowMs());
		}
		const int32 StoryFact = F->GetFact(TEXT("story"));
		if (StoryFact != S.LastStory)
		{
			if (S.LastStory != INDEX_NONE) { Request(TEXT("story"), FString::Printf(TEXT("%d_to_%d"), S.LastStory, StoryFact), 10); }
			S.LastStory = StoryFact;
		}
		if (Screen != S.LastScreen)
		{
			if (Screen > 0 && !S.SeenScreens.Contains(Screen))
			{
				S.SeenScreens.Add(Screen);
				Request(TEXT("screen"), FString::Printf(TEXT("%d_from_%d"), Screen, S.LastScreen), 30);
			}
			S.LastScreen = Screen;
		}
		const int32 Life = F->GetFact(TEXT("life"));
		if (Life <= 0 && S.LastLife > 0) { Request(TEXT("death"), FString::Printf(TEXT("life_%d"), Life), 30); }
		S.LastLife = Life;
		const bool bMenu = Story->GetActiveMenu() != nullptr;
		if (bMenu && !S.bMenu)
		{
			const FDinkMenu* M = Story->GetActiveMenu();
			Request(TEXT("menu"), M->Choices.Num() > 0 ? M->Choices[0].Text : FString());
		}
		S.bMenu = bMenu;
		ScanEvents(Story);
		if (Wall - S.LastPeriodic > 60.0)
		{
			if (S.LastPeriodic > 0.0) { Request(TEXT("periodic"), FString::Printf(TEXT("%d"), Screen)); }
			S.LastPeriodic = Wall;
		}
		// One screenshot per frame; the rest wait their turn.
		if (!FScreenshotRequest::IsScreenshotRequested())
		{
			for (int32 i = 0; i < S.Queue.Num(); ++i)
			{
				if (S.Queue[i].DueFrame <= GFrameCounter)
				{
					const FPending P = S.Queue[i];
					S.Queue.RemoveAt(i);
					Shoot(Story, P);
					break;
				}
			}
		}
		return true;
	}

	void SetDir(const FString& Dir)
	{
		FState& S = State();
		S.Dir = Dir;
		S.Queue.Reset();
		if (!Dir.IsEmpty())
		{
			IFileManager::Get().MakeDirectory(*Dir, true);
			UE_LOG(LogDinkBeat, Display, TEXT("DINK BEAT: on, shots into %s"), *Dir);
		}
	}

	// dink.Sprites: the live sprites of Dink's screen (QA driving: where to stand to talk, fight or push).
	FAutoConsoleCommand GSpritesCommand(
		TEXT("dink.Sprites"),
		TEXT("dink.Sprites: list the live sprites on Dink's screen (handle, script, brain, map x/y, hitpoints, origin)."),
		FConsoleCommandDelegate::CreateLambda([]()
		{
			UWorld* World = GameWorld();
			UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
			UDinkStorySubsystem* Story = GI ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
			UDinkDirector* D = Story ? Story->GetDirector() : nullptr;
			if (!D) { return; }
			const int32 Screen = D->GetDink().Screen;
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				const FDinkSprite& Sp = Pair.Value;
				if (!Sp.bActive || Sp.bText || Sp.Screen != Screen) { continue; }
				UE_LOG(LogDinkBeat, Display, TEXT("DINK SPRITE: %d script=%s brain=%d map=%.0f,%.0f hp=%d origin=%s"), Pair.Key,
					Sp.Script.IsNone() ? TEXT("-") : *Sp.Script.ToString(), Sp.GetProp(TEXT("brain")), Sp.X - 20.0, Sp.Y,
					Sp.GetProp(TEXT("hitpoints")), *Sp.Origin.ToString());
			}
		}));

	FAutoConsoleCommand GBeatShotsCommand(
		TEXT("dink.BeatShots"),
		TEXT("dink.BeatShots <dir>|off: screenshot (with UI) every story beat into <dir> and log DINK BEAT / DINK HITCH lines (playthrough QA)."),
		FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args)
		{
			SetDir(Args.Num() == 1 && Args[0] != TEXT("off") ? Args[0] : FString());
		}));
}

void Request(const FString& Kind, const FString& Detail, int32 DelayFrames)
{
	FState& S = State();
	if (S.Dir.IsEmpty()) { return; }
	S.Queue.Add({ GFrameCounter + uint64(FMath::Max(0, DelayFrames)), Kind, Detail });
}

bool IsOn() { return !State().Dir.IsEmpty(); }

void Startup()
{
	FString Dir;
	if (FParse::Value(FCommandLine::Get(), TEXT("DinkBeatShots="), Dir) && !Dir.IsEmpty())
	{
		SetDir(Dir);
	}
	State().Ticker = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateStatic(&Tick));
}

void Shutdown()
{
	FTSTicker::GetCoreTicker().RemoveTicker(State().Ticker);
}
}
