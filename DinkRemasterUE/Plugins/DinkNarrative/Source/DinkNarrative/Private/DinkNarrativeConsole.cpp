// Console commands of the narrative layer (style of dink.Goto in DinkCore) and the whole-story smoke run.

#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkGameplay.h"
#include "DinkInventoryComponent.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/OutputDevice.h"
#include "Misc/Paths.h"

namespace
{
	UDinkStorySubsystem* GetStory(UWorld* World)
	{
		UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
		UDinkStorySubsystem* S = GI ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		if (!S || !S->IsReady())
		{
			UE_LOG(LogDinkNarrative, Warning, TEXT("no story: run this in PIE or the game (and Scripts/sync_story.py once)"));
			return nullptr;
		}
		return S;
	}

	/** Collects InkPlusPlus' own error/warning log lines (its runtime logs some errors instead of reporting them). */
	class FInkLogCapture : public FOutputDevice
	{
	public:
		TArray<FString> Lines;
		virtual void Serialize(const TCHAR* V, ELogVerbosity::Type Verbosity, const FName& Category) override
		{
			static const FName InkCategory(TEXT("InkPlusPlus"));
			if (Category == InkCategory && Verbosity <= ELogVerbosity::Warning)
			{
				Lines.Add(V);
			}
		}
		virtual bool CanBeUsedOnAnyThread() const override { return true; }
	};
}

static FAutoConsoleCommandWithWorldAndArgs GDinkRunCommand(
	TEXT("dink.Run"),
	TEXT("dink.Run <script> <procedure> [S001_P26 | handle]: runs a DinkC procedure from the converted story. Default target: the nearest actor carrying that script, else no sprite."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UDinkStorySubsystem* S = GetStory(World);
		if (!S || Args.Num() < 2)
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("usage: dink.Run <script> <procedure> [origin id | handle]"));
			return;
		}
		const FName Script(*Args[0].ToLower());
		const FName Proc(*Args[1].ToLower());
		int32 Handle = 0;
		int32 Screen = INDEX_NONE;
		FDinkOriginId Origin;
		if (Args.Num() > 2 && FDinkOriginId::Parse(Args[2], Origin))
		{
			Handle = S->GetDirector()->HandleForPlacement(Origin.Screen, Origin.Placement);
			Screen = Origin.Screen;
		}
		else if (Args.Num() > 2 && Args[2].IsNumeric())
		{
			Handle = FCString::Atoi(*Args[2]);
		}
		else
		{
			const APlayerController* PC = World->GetFirstPlayerController();
			const FVector From = PC && PC->GetPawn() ? PC->GetPawn()->GetActorLocation() : FVector::ZeroVector;
			double Best = TNumericLimits<double>::Max();
			AActor* BestActor = nullptr;
			for (TActorIterator<AActor> It(World); It; ++It)
			{
				const UDinkOriginComponent* O = UDinkOriginComponent::FindOnActor(*It);
				if (O && O->ScriptName == Script)
				{
					const double D = FVector::DistSquared(From, It->GetActorLocation());
					if (D < Best)
					{
						Best = D;
						BestActor = *It;
					}
				}
			}
			if (BestActor)
			{
				Handle = S->GetDirector()->HandleForActor(BestActor);
				Screen = UDinkOriginComponent::FindOnActor(BestActor)->OriginId.Screen;
			}
		}
		const int32 Id = S->StartProcedure(Script, Proc, Handle, {}, Screen);
		UE_LOG(LogDinkNarrative, Display, TEXT("dink.Run %s.%s sprite %d: %s"), *Script.ToString(), *Proc.ToString(), Handle,
			Id ? *FString::Printf(TEXT("instance %d started"), Id) : TEXT("no such entry point in the converted story"));
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkSayCommand(
	TEXT("dink.Say"),
	TEXT("dink.Say <text>: Dink says the text (non-blocking, like DinkC say)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (UDinkStorySubsystem* S = GetStory(World))
		{
			FDinkStoryLine Line;
			Line.Kind = EDinkLineKind::Spoken;
			Line.SayCall = TEXT("say");
			Line.Text = FString::Join(Args, TEXT(" "));
			Line.Speaker = TEXT("1");
			S->ShowText(Line, 1, 0);
		}
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkFactCommand(
	TEXT("dink.Fact"),
	TEXT("dink.Fact <name> [value]: prints or sets a fact (original DinkC name without &, e.g. story, s2-nad, gold). The Ink story sees it at once."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
		UDinkFactSubsystem* Facts = GI ? GI->GetSubsystem<UDinkFactSubsystem>() : nullptr;
		if (!Facts || Args.Num() < 1)
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("usage: dink.Fact <name> [value]"));
			return;
		}
		const FName Name(*Args[0]);
		if (Args.Num() > 1)
		{
			Facts->SetFact(Name, FCString::Atoi(*Args[1]));
		}
		UE_LOG(LogDinkNarrative, Display, TEXT("%s = %d"), *Name.ToString(), Facts->GetFact(Name));
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkChooseCommand(
	TEXT("dink.Choose"),
	TEXT("dink.Choose <n>: picks option n (1-based) of the menu on screen."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (UDinkStorySubsystem* S = GetStory(World))
		{
			const bool bOk = Args.Num() > 0 && S->Choose(FCString::Atoi(*Args[0]) - 1);
			UE_LOG(LogDinkNarrative, Display, TEXT("dink.Choose: %s"), bOk ? TEXT("ok") : TEXT("no menu or no such option"));
		}
	}));

static FAutoConsoleCommandWithWorld GDinkSkipCommand(
	TEXT("dink.Skip"),
	TEXT("dink.Skip: skips the text being waited on (like the skip key)."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		if (UDinkStorySubsystem* S = GetStory(World))
		{
			S->SkipDialogue();
		}
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkScreenScriptsCommand(
	TEXT("dink.ScreenScripts"),
	TEXT("dink.ScreenScripts 0|1: run the screen's and its placements' main procedures when the player enters a screen (default 1)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (UDinkStorySubsystem* S = GetStory(World))
		{
			if (Args.Num() > 0)
			{
				S->bRunScreenScripts = FCString::Atoi(*Args[0]) != 0;
			}
			UE_LOG(LogDinkNarrative, Display, TEXT("dink.ScreenScripts %d"), S->bRunScreenScripts ? 1 : 0);
		}
	}));

static FAutoConsoleCommandWithWorld GDinkStoryCommand(
	TEXT("dink.Story"),
	TEXT("dink.Story: lists the running script instances, texts, menu, audio cues and recent errors."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		UDinkStorySubsystem* S = GetStory(World);
		if (!S)
		{
			return;
		}
		UE_LOG(LogDinkNarrative, Display, TEXT("time %.0f ms, %d instances"), S->GetNowMs(), S->GetInstances().Num());
		for (const TUniquePtr<FDinkScriptInstance>& I : S->GetInstances())
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("  #%d %s.%s sprite %d screen %d state %d block %d lines %lld"), I->Id, *I->Script.ToString(),
				*I->Procedure.ToString(), I->Sprite, I->Screen, static_cast<int32>(I->State), static_cast<int32>(I->Block), I->LinesRun);
		}
		for (const FDinkActiveText& T : S->GetActiveTexts())
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("  text %d by %d: %s"), T.Handle, T.Owner, *T.Text);
		}
		if (const FDinkMenu* M = S->GetActiveMenu())
		{
			for (int32 i = 0; i < M->Choices.Num(); ++i)
			{
				UE_LOG(LogDinkNarrative, Display, TEXT("  menu %d. %s"), i + 1, *M->Choices[i].Text);
			}
		}
		const FDinkAudioStub& Audio = S->GetDirector()->Audio;
		for (int32 i = FMath::Max(0, Audio.Cues.Num() - 5); i < Audio.Cues.Num(); ++i)
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("  audio %s"), *Audio.Cues[i]);
		}
		for (int32 i = FMath::Max(0, S->ErrorLog.Num() - 5); i < S->ErrorLog.Num(); ++i)
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("  error %s"), *S->ErrorLog[i]);
		}
	}));

static FAutoConsoleCommandWithWorld GDinkAttackCommand(
	TEXT("dink.Attack"),
	TEXT("dink.Attack: the attack key (F / Left Ctrl): runs the armed item's use; the hit lands on its animation's hit frame."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		if (UDinkStorySubsystem* S = GetStory(World))
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("dink.Attack: %s"), S->GetGameplay()->PlayerAttack() ? TEXT("used the armed item") : TEXT("nothing armed, or Dink is frozen"));
		}
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkHurtCommand(
	TEXT("dink.Hurt"),
	TEXT("dink.Hurt <S001_P26> <damage>: review only: hurt_thing on a placement's sprite of the current screen, as a player's blow would (its brain applies it next tick). For captures of deaths and what they leave."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UDinkStorySubsystem* S = GetStory(World);
		FDinkOriginId Origin;
		if (!S || Args.Num() < 2 || !FDinkOriginId::Parse(Args[0], Origin))
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("usage: dink.Hurt <origin id> <damage>"));
			return;
		}
		int32 Handle = S->GetDirector()->HandleForPlacement(Origin.Screen, Origin.Placement);
		if (Handle <= 0)
		{
			// A placement its `die` script has marked killed (editor_type) is no longer found by number: its actor still carries the sprite.
			for (TActorIterator<AActor> It(World); It && Handle <= 0; ++It)
			{
				const UDinkOriginComponent* O = UDinkOriginComponent::FindOnActor(*It);
				if (O && O->OriginId == Origin) Handle = S->GetDirector()->HandleForActor(*It);
			}
		}
		const int32 Dealt = Handle > 0 ? S->GetGameplay()->HurtThing(Handle, FCString::Atoi(*Args[1])) : 0;
		UE_LOG(LogDinkNarrative, Display, TEXT("dink.Hurt: %s handle %d, %d dealt"), *Args[0], Handle, Dealt);
	}));

static FAutoConsoleCommandWithWorld GDinkMagicCommand(
	TEXT("dink.Magic"),
	TEXT("dink.Magic: the magic key (Q): casts the armed spell if &magic_level >= &magic_cost."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		if (UDinkStorySubsystem* S = GetStory(World))
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("dink.Magic: %s (magic_level %d / magic_cost %d)"), S->GetGameplay()->PlayerCastMagic() ? TEXT("cast") : TEXT("not cast"),
				S->GetFacts()->GetFact(TEXT("magic_level")), S->GetFacts()->GetFact(TEXT("magic_cost")));
		}
	}));

namespace
{
	/** "3" (1-based slot) or an item script name ("item-sw1") -> 1-based slot, 0 if not held. */
	int32 ParseSlot(const FString& Arg, bool bMagic, UDinkInventoryComponent* Inv)
	{
		if (Arg.IsNumeric())
		{
			return FCString::Atoi(*Arg);
		}
		const int32 Count = bMagic ? FDinkInventoryState::NumMagicSlots : FDinkInventoryState::NumItemSlots;
		for (int32 i = 0; i < Count; ++i)
		{
			if ((bMagic ? Inv->GetMagicAt(i) : Inv->GetItemAt(i)) == FName(*Arg.ToLower()))
			{
				return i + 1;
			}
		}
		return 0;
	}
}

static FAutoConsoleCommandWithWorldAndArgs GDinkArmCommand(
	TEXT("dink.Arm"),
	TEXT("dink.Arm <slot 1-16 | item script>: what choosing an item on the inventory screen does (&cur_weapon, disarm/arm)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (UDinkStorySubsystem* S = GetStory(World); S && Args.Num() > 0)
		{
			const int32 Slot = ParseSlot(Args[0], false, S->GetDirector()->GetInventory());
			UE_LOG(LogDinkNarrative, Display, TEXT("dink.Arm %s: %s"), *Args[0], S->GetGameplay()->ArmItemSlot(Slot) ? TEXT("armed") : TEXT("no such item"));
		}
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkArmMagicCommand(
	TEXT("dink.ArmMagic"),
	TEXT("dink.ArmMagic <slot 1-8 | spell script>: what choosing a spell on the inventory screen does (&cur_magic, disarm/arm)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (UDinkStorySubsystem* S = GetStory(World); S && Args.Num() > 0)
		{
			const int32 Slot = ParseSlot(Args[0], true, S->GetDirector()->GetInventory());
			UE_LOG(LogDinkNarrative, Display, TEXT("dink.ArmMagic %s: %s"), *Args[0], S->GetGameplay()->ArmMagicSlot(Slot) ? TEXT("armed") : TEXT("no such spell"));
		}
	}));

static FAutoConsoleCommandWithWorld GDinkInventoryCommand(
	TEXT("dink.Inventory"),
	TEXT("dink.Inventory: lists items and spells (the inventory screen is not built yet), the armed ones and Dink's stats."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		if (UDinkStorySubsystem* S = GetStory(World))
		{
			UDinkInventoryComponent* Inv = S->GetDirector()->GetInventory();
			for (int32 i = 0; i < FDinkInventoryState::NumItemSlots; ++i)
			{
				if (!Inv->GetItemAt(i).IsNone())
				{
					UE_LOG(LogDinkNarrative, Display, TEXT("  item %d: %s%s"), i + 1, *Inv->GetItemAt(i).ToString(), Inv->GetArmedItemSlot() == i ? TEXT(" (armed)") : TEXT(""));
				}
			}
			for (int32 i = 0; i < FDinkInventoryState::NumMagicSlots; ++i)
			{
				if (!Inv->GetMagicAt(i).IsNone())
				{
					UE_LOG(LogDinkNarrative, Display, TEXT("  magic %d: %s%s"), i + 1, *Inv->GetMagicAt(i).ToString(), Inv->GetArmedMagicSlot() == i ? TEXT(" (armed)") : TEXT(""));
				}
			}
			const UDinkFactSubsystem* F = S->GetFacts();
			UE_LOG(LogDinkNarrative, Display, TEXT("  life %d/%d strength %d defense %d magic %d exp %d level %d gold %d magic_level %d/%d"),
				F->GetFact(TEXT("life")), F->GetFact(TEXT("lifemax")), F->GetFact(TEXT("strength")), F->GetFact(TEXT("defense")), F->GetFact(TEXT("magic")),
				F->GetFact(TEXT("exp")), F->GetFact(TEXT("level")), F->GetFact(TEXT("gold")), F->GetFact(TEXT("magic_level")), F->GetFact(TEXT("magic_cost")));
		}
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkSeedCommand(
	TEXT("dink.Seed"),
	TEXT("dink.Seed <n>: reseeds the gameplay random source (DinkC random(), combat rolls, callback timers)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (UDinkStorySubsystem* S = GetStory(World); S && Args.Num() > 0)
		{
			S->GetGameplay()->SetRandomSeed(FCString::Atoi(*Args[0]));
		}
	}));

// ---------------------------------------------------------------------------------------------
// Smoke run

FDinkSmokeReport UDinkStorySubsystem::RunSmoke(int32 Seed, int32 StepCap, const TArray<FString>* OnlyEntries)
{
	FDinkSmokeReport Report;
	if (!IsReady())
	{
		return Report;
	}
	TGuardValue<bool> Instant(bInstantMode, true);
	TGuardValue<bool> Quiet(bQuietErrors, true);
	TGuardValue<bool> NoEvents(bRecordEvents, false);
	TGuardValue<bool> NoScreens(bRunScreenScripts, false);
	const TFunction<int32(const FDinkMenu&)> OldChooser = AutoChooser;
	FRandomStream Rng(Seed);
	AutoChooser = [&Rng](const FDinkMenu& Menu) { return Menu.Choices.Num() > 0 ? Rng.RandHelper(Menu.Choices.Num()) : 0; };

	FInkLogCapture Capture;
	GLog->AddOutputDevice(&Capture);
	Director->CommandCounts.Reset();
	const int64 Spoken0 = StatSpoken, Commands0 = StatCommands, Menus0 = StatMenus, Skipped0 = StatSaySkipped;
	MissingTargets.Reset();

	for (const FDinkStoryNames::FEntry& Entry : Story.Names().Entries)
	{
		if (OnlyEntries && !OnlyEntries->Contains(Entry.Path))
		{
			continue;
		}
		++Report.EntryPoints;
		if (UDinkFactSubsystem* F = Facts.Get())
		{
			F->ResetToInitialValues();
		}
		StorySeed = Seed;
		ResetRuntime();
		ErrorLog.Reset();
		Capture.Lines.Reset();
		GetDirector()->GetInventory()->SetState(FDinkInventoryState());
		const int64 Blocks0 = StatBlocks;

		const int32 Sprite = Director->CreateVirtualSprite(1, 320, 200);
		Director->Sprites[Sprite].Script = Entry.Script;
		Director->Sprites[Sprite].bSpawned = false;
		const int32 Id = StartProcedure(Entry.Script, Entry.Procedure, Sprite, {}, 1);
		if (Id == 0)
		{
			Report.Errors.Add(Entry.Path + TEXT(": entry point did not start"));
			++Report.WithErrors;
			continue;
		}
		const int64 Lines = RunUntilIdle(StepCap);
		Report.TotalLines += Lines;
		bool bWaiting = false;
		for (const TUniquePtr<FDinkScriptInstance>& I : Instances)
		{
			bWaiting |= I->State == EDinkInstanceState::Running || I->State == EDinkInstanceState::Blocked || I->State == EDinkInstanceState::Choosing;
		}
		if (Lines >= StepCap)
		{
			++Report.HitStepCap;
			const bool bIdleLoop = StatBlocks > Blocks0;
			Report.CapInIdleLoop += bIdleLoop ? 1 : 0;
			Report.CappedEntries.Add(FString::Printf(TEXT("%s (%s)"), *Entry.Path, bIdleLoop ? TEXT("loops through blocking commands: an endless loop of the original") : TEXT("loops without ever blocking: would hang the original")));
		}
		else if (bWaiting)
		{
			++Report.Stalled;
			Report.StalledEntries.Add(Entry.Path);
		}
		else
		{
			++Report.Completed;
		}
		TSet<FString> Seen;
		for (const FString& E : ErrorLog)
		{
			if (!Seen.Contains(E)) { Seen.Add(E); Report.Errors.Add(Entry.Path + TEXT(": ") + E); }
		}
		for (const FString& E : Capture.Lines)
		{
			const FString Msg = TEXT("InkPlusPlus log: ") + E;
			if (!Seen.Contains(Msg)) { Seen.Add(Msg); Report.Errors.Add(Entry.Path + TEXT(": ") + Msg); }
		}
		Report.WithErrors += Seen.Num() > 0 ? 1 : 0;
	}
	GLog->RemoveOutputDevice(&Capture);
	Report.SpokenLines = static_cast<int32>(StatSpoken - Spoken0);
	Report.Commands = static_cast<int32>(StatCommands - Commands0);
	Report.Menus = static_cast<int32>(StatMenus - Menus0);
	Report.SaySkipped = static_cast<int32>(StatSaySkipped - Skipped0);
	Report.MissingTargets = MissingTargets;
	Report.CommandCounts = Director->CommandCounts;
	AutoChooser = OldChooser;
	if (UDinkFactSubsystem* F = Facts.Get())
	{
		F->ResetToInitialValues();
	}
	StorySeed = 1997;
	ResetRuntime();
	ErrorLog.Reset();
	return Report;
}

static FAutoConsoleCommandWithWorldAndArgs GDinkSmokeCommand(
	TEXT("dink.SmokeRun"),
	TEXT("dink.SmokeRun [seed] [step cap]: runs every entry point of the story with stubbed commands; report in Saved/Narrative/smoke_report.txt."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (UDinkStorySubsystem* S = GetStory(World))
		{
			const int32 Seed = Args.Num() > 0 ? FCString::Atoi(*Args[0]) : 1997;
			const int32 Cap = Args.Num() > 1 ? FCString::Atoi(*Args[1]) : 5000;
			const FDinkSmokeReport Report = S->RunSmoke(Seed, Cap);
			const FString Path = FPaths::ProjectSavedDir() / TEXT("Narrative/smoke_report.txt");
			FFileHelper::SaveStringToFile(Report.ToText(), *Path);
			UE_LOG(LogDinkNarrative, Display, TEXT("smoke run: %d entry points, %d completed, %d hit the cap, %d stalled, %d with errors; %s"),
				Report.EntryPoints, Report.Completed, Report.HitStepCap, Report.Stalled, Report.WithErrors, *Path);
		}
	}));

// dink.Npc.Trace <seconds> [file] [frame folder]: one CSV row per rendered frame and per humanoid NPC body on Dink's
// screen: what the script says (sprite pixel, direction, brain action, sequence) next to what is shown
// (the body's position, facing, speed and gait phase). With a frame folder every traced frame is also
// saved as <folder>/f_<frame>.png (run the game with -benchmark -fps=60 so that each rendered frame is
// one sixtieth of a second however long the picture takes to save). Diagnostic only; nothing is changed.
#include "DinkHumanoidComponent.h"
#include "Containers/Ticker.h"
#include "UnrealClient.h"

namespace
{
	struct FDinkNpcTrace
	{
		TWeakObjectPtr<UWorld> World;
		FString Path, FrameFolder;
		TArray<FString> Rows;
		double EndTime = 0.0;
		uint64 Frame = 0;
	};

	bool TickNpcTrace(TSharedRef<FDinkNpcTrace> T, float RealDelta)
	{
		UWorld* World = T->World.Get();
		UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
		UDinkStorySubsystem* S = GI ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		UDinkDirector* D = S ? S->GetDirector() : nullptr;
		const double Now = World ? World->GetTimeSeconds() : 0.0;
		if (!D || Now >= T->EndTime)
		{
			FFileHelper::SaveStringToFile(FString::Join(T->Rows, TEXT("\n")) + TEXT("\n"), *T->Path);
			UE_LOG(LogDinkNarrative, Display, TEXT("DINK NPC TRACE: %d rows -> %s"), T->Rows.Num() - 1, *T->Path);
			return false;
		}
		++T->Frame;
		if (!T->FrameFolder.IsEmpty())
		{
			FScreenshotRequest::RequestScreenshot(T->FrameFolder / FString::Printf(TEXT("f_%05llu.png"), T->Frame), false, false);
		}
		const int32 Screen = D->GetDink().Screen;
		for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
		{
			const FDinkSprite& Sp = Pair.Value;
			AActor* A = Sp.Actor.Get();
			if (!A || !Sp.bActive || Pair.Key == 1 || Sp.Screen != Screen || !A->ActorHasTag(TEXT("DinkHumanoid")))
			{
				continue;
			}
			const UDinkHumanoidComponent* H = A->FindComponentByClass<UDinkHumanoidComponent>();
			const UDinkBodyAnimInstance* B = H ? Cast<UDinkBodyAnimInstance>(H->GetAnimInstance()) : nullptr;
			const FVector AL = A->GetActorLocation();
			const FVector BL = H ? H->GetComponentLocation() : AL;
			T->Rows.Add(FString::Printf(TEXT("%llu,%.4f,%.5f,%.5f,%d,%s,%.2f,%.2f,%d,%d,%d,%d,%d,%d,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.4f,%.3f,%.2f,%.2f,%s"),
				T->Frame, Now, World->GetDeltaSeconds(), RealDelta, Pair.Key, *Sp.Script.ToString(), Sp.X, Sp.Y, Sp.Dir, Sp.Action,
				Sp.GetProp(TEXT("seq")), Sp.GetProp(TEXT("pframe")), Sp.bMoving ? 1 : 0, Sp.bFrozen ? 1 : 0,
				AL.X, AL.Y, A->GetActorRotation().Yaw, BL.X, BL.Y, H ? H->GetComponentRotation().Yaw : 0.,
				H ? H->GetLocomotionSpeed() : 0.f, H ? H->GetScriptedSpeed() : 0.f,
				B ? B->GetPhase() : 0.f, B ? B->GetCyclesPerSecond() : 0.f, B ? B->GetBlendedStrideCm() : 0.f, B ? B->GetSpeed() : 0.f,
				H && H->GetSkeletalMeshAsset() ? *H->GetSkeletalMeshAsset()->GetName() : TEXT("-")));
		}
		return true;
	}
}

static FAutoConsoleCommandWithWorldAndArgs GDinkNpcTraceCommand(
	TEXT("dink.Npc.Trace"),
	TEXT("dink.Npc.Trace <seconds> [file] [frame folder]: per rendered frame, the scripted and the shown state of every humanoid NPC on Dink's screen, as CSV (default Saved/Narrative/npc_trace.csv); with a folder, a picture of every traced frame too."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || !GetStory(World))
		{
			return;
		}
		TSharedRef<FDinkNpcTrace> T = MakeShared<FDinkNpcTrace>();
		T->World = World;
		T->EndTime = World->GetTimeSeconds() + (Args.Num() > 0 ? FMath::Max(.1f, FCString::Atof(*Args[0])) : 10.f);
		T->Path = Args.Num() > 1 ? Args[1] : FPaths::ProjectSavedDir() / TEXT("Narrative/npc_trace.csv");
		if (Args.Num() > 2) T->FrameFolder = Args[2];
		T->Rows.Add(TEXT("frame,time,dt,real_dt,handle,script,sprite_x,sprite_y,dir,action,seq,pframe,moving,frozen,actor_x,actor_y,actor_yaw,body_x,body_y,body_yaw,body_speed,script_speed,phase,cycles_per_s,stride_cm,anim_speed,mesh"));
		FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([T](float Delta) { return TickNpcTrace(T, Delta); }));
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkNpcHoldCommand(
	TEXT("dink.Npc.Hold"),
	TEXT("dink.Npc.Hold 0|1: review only. 1 stops every sprite brain (townsfolk stand where they are, for portraits); 0 lets them think again."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UDinkStorySubsystem* S = GetStory(World);
		if (S && S->GetGameplay() && Args.Num() > 0)
		{
			S->GetGameplay()->bBrainsEnabled = FCString::Atoi(*Args[0]) == 0;
			UE_LOG(LogDinkNarrative, Display, TEXT("dink.Npc.Hold %d"), S->GetGameplay()->bBrainsEnabled ? 0 : 1);
		}
	}));
