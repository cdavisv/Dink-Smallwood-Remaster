#include "DinkStorySubsystem.h"
#include "Hardness/DinkFamilyCollisionFit.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "Hardness/DinkHardnessActivation.h"
#include "DinkNarrativeInput.h"
#include "DinkFactSubsystem.h"
#include "DinkOriginComponent.h"
#include "DinkSaveGame.h"
#include "DinkSaveSubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/HUD.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
	const FName NAME_Narrative(TEXT("narrative"));
	const FName NAME_Talk(TEXT("talk"));
	const FName NAME_Main(TEXT("main"));
	const FName NAME_Vision(TEXT("vision"));
	const FName NAME_PlayerMap(TEXT("player_map"));
}

UDinkStorySubsystem::UDinkStorySubsystem()
{
}

void UDinkStorySubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	Collection.InitializeDependency<UDinkFactSubsystem>();
	Collection.InitializeDependency<UDinkWorldStateSubsystem>();
	Collection.InitializeDependency<UDinkSaveSubsystem>();

	UGameInstance* GameInstance = GetGameInstance();
	FString Error;
	if (!SetupStandalone(GameInstance->GetSubsystem<UDinkFactSubsystem>(), GameInstance->GetSubsystem<UDinkWorldStateSubsystem>(), &Error))
	{
		UE_LOG(LogDinkNarrative, Error, TEXT("story not loaded: %s (run Scripts/sync_story.py)"), *Error);
		return;
	}
	if (UDinkSaveSubsystem* Saves = GameInstance->GetSubsystem<UDinkSaveSubsystem>())
	{
		SaveCapturedHandle = Saves->OnSnapshotCaptured.AddUObject(this, &UDinkStorySubsystem::CaptureToSave);
		SaveAppliedHandle = Saves->OnSnapshotApplied.AddUObject(this, &UDinkStorySubsystem::RestoreFromSave);
	}
	bNewGamePending = true;
	if (!IsRunningCommandlet())
	{
		bAutoTick = true;
		HudHandle = AHUD::OnHUDPostRender.AddUObject(this, &UDinkStorySubsystem::DrawHUD);
		if (FSlateApplication::IsInitialized())
		{
			InputProcessor = MakeShared<FDinkNarrativeInputProcessor>(this);
			FSlateApplication::Get().RegisterInputPreProcessor(InputProcessor);
		}
	}
}

void UDinkStorySubsystem::Deinitialize()
{
	if (Gameplay) Gameplay->ShutdownRuntimeHardness();
	bAutoTick = false;
	AHUD::OnHUDPostRender.Remove(HudHandle);
	if (InputProcessor.IsValid() && FSlateApplication::IsInitialized())
	{
		FSlateApplication::Get().UnregisterInputPreProcessor(InputProcessor);
	}
	InputProcessor.Reset();
	if (UGameInstance* GameInstance = GetGameInstance())
	{
		if (UDinkSaveSubsystem* Saves = GameInstance->GetSubsystem<UDinkSaveSubsystem>())
		{
			Saves->OnSnapshotCaptured.Remove(SaveCapturedHandle);
			Saves->OnSnapshotApplied.Remove(SaveAppliedHandle);
		}
	}
	if (UDinkFactSubsystem* F = Facts.Get())
	{
		F->OnAnyFactChangedNative.Remove(FactChangedHandle);
		F->OnFactsResetNative.Remove(FactsResetHandle);
	}
	Super::Deinitialize();
}

bool UDinkStorySubsystem::SetupStandalone(UDinkFactSubsystem* InFacts, UDinkWorldStateSubsystem* InWorldState, FString* OutError)
{
	Facts = InFacts;
	WorldState = InWorldState;
	if (!Gameplay)
	{
		Gameplay = NewObject<UDinkGameplay>(this, TEXT("Gameplay"));
		Gameplay->Init(this);
	}
	if (!Director)
	{
		Director = NewObject<UDinkDirector>(this, TEXT("Director"));
		Director->Init(this);
	}
	if (!LoadStory(OutError))
	{
		return false;
	}
	BindFacts();
	PushAllFactsToInk();
	return true;
}

UWorld* UDinkStorySubsystem::GetWorld() const
{
	const UGameInstance* GameInstance = Cast<UGameInstance>(GetOuter());
	return GameInstance ? GameInstance->GetWorld() : nullptr;
}

bool UDinkStorySubsystem::LoadStory(FString* OutError)
{
	FString Json, Names;
	const FString JsonPath = FDinkInkStory::GetDataPath(TEXT("dink.json"));
	const FString NamesPath = FDinkInkStory::GetDataPath(TEXT("names.csv"));
	if (!FFileHelper::LoadFileToString(Json, *JsonPath) || !FFileHelper::LoadFileToString(Names, *NamesPath))
	{
		if (OutError)
		{
			*OutError = FString::Printf(TEXT("cannot read %s or %s"), *JsonPath, *NamesPath);
		}
		return false;
	}
	const double Start = FPlatformTime::Seconds();
	if (!Story.Load(Json, Names, OutError))
	{
		return false;
	}
	Director->BindExternals(Story);
	Story.OnIntVariableChanged = [this](const FString& Name, int32 Value) { HandleInkVariableChanged(Name, Value); };
	Story.ResetState(StorySeed); // never the C library's unseeded rand(): same seed, same story
	UE_LOG(LogDinkNarrative, Log, TEXT("story loaded: ink v%d, %d knots, %d entry points, %d globals in %.0f ms"),
		Story.GetInkVersion(), Story.Names().ScriptToKnot.Num(), Story.Names().Entries.Num(), Story.Names().GlobalToInk.Num(),
		(FPlatformTime::Seconds() - Start) * 1000.0);
	return true;
}

// ---------------------------------------------------------------------------------------------
// Facts <-> Ink

void UDinkStorySubsystem::BindFacts()
{
	UDinkFactSubsystem* F = Facts.Get();
	if (!F || FactChangedHandle.IsValid())
	{
		return;
	}
	FactChangedHandle = F->OnAnyFactChangedNative.AddUObject(this, &UDinkStorySubsystem::HandleFactChanged);
	FactsResetHandle = F->OnFactsResetNative.AddUObject(this, &UDinkStorySubsystem::HandleFactsReset);
}

void UDinkStorySubsystem::PushAllFactsToInk()
{
	UDinkFactSubsystem* F = Facts.Get();
	if (!F || !Story.IsLoaded())
	{
		return;
	}
	TGuardValue<bool> Guard(bSyncingFacts, true);
	for (const TPair<FName, FString>& Pair : Story.Names().GlobalToInk)
	{
		Story.SetInt(Pair.Value, F->GetFact(Pair.Key));
	}
}

void UDinkStorySubsystem::HandleFactChanged(FName Fact, int32 OldValue, int32 NewValue)
{
	// Side effects of engine-bound facts, whoever wrote them.
	if (Fact == NAME_Vision)
	{
        if (Gameplay) Gameplay->OriginalHardnessVisionChanged(NewValue);
		if (UWorld* World = GetWorld();World&&DinkHardness::ApplyFactVisionImmediately(Gameplay&&Gameplay->RequiresOriginalHardnessScreen(Director->GetCurrentScreen())))
		{
			if (UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>())
			{
				Greybox->SetScreenVision(Director->GetCurrentScreen(), NewValue);
			}
		}
	}
	if (bSyncingFacts || !Story.IsLoaded())
	{
		return;
	}
	if (const FString* InkName = Story.Names().GlobalToInk.Find(Fact))
	{
		TGuardValue<bool> Guard(bSyncingFacts, true);
		Story.SetInt(*InkName, NewValue);
	}
}

void UDinkStorySubsystem::HandleFactsReset()
{
	PushAllFactsToInk();
}

void UDinkStorySubsystem::HandleInkVariableChanged(const FString& Name, int32 Value)
{
	if (bSyncingFacts)
	{
		return;
	}
	if (const FName* Fact = Story.Names().InkToGlobal.Find(Name))
	{
		if (UDinkFactSubsystem* F = Facts.Get())
		{
			TGuardValue<bool> Guard(bSyncingFacts, true);
			F->SetFact(*Fact, Value);
		}
	}
}

// ---------------------------------------------------------------------------------------------
// Instances

bool UDinkStorySubsystem::HasProcedure(FName Script, FName Procedure) const
{
	return Story.IsLoaded() && Story.Names().HasEntry(Script, Procedure);
}

FDinkScriptInstance* UDinkStorySubsystem::FindInstance(int32 InstanceId)
{
	if (InstanceId == 0)
	{
		return nullptr;
	}
	for (const TUniquePtr<FDinkScriptInstance>& I : Instances)
	{
		if (I->Id == InstanceId)
		{
			return I.Get();
		}
	}
	return nullptr;
}

FDinkScriptInstance* UDinkStorySubsystem::FindInstanceForSprite(int32 Sprite, FName Script)
{
	for (const TUniquePtr<FDinkScriptInstance>& I : Instances)
	{
		if (I->IsAlive() && I->Sprite == Sprite && I->ParentId == 0 && !I->bEndWithProcedure && (Script.IsNone() || I->Script == Script))
		{
			return I.Get();
		}
	}
	return nullptr;
}

FDinkScriptInstance& UDinkStorySubsystem::CreateInstance(FName Script, int32 Sprite, int32 Screen)
{
	TUniquePtr<FDinkScriptInstance> New = MakeUnique<FDinkScriptInstance>();
	FDinkScriptInstance& I = *New;
	I.Id = NextInstanceId++;
	I.Script = Script;
	I.Sprite = Sprite;
	I.AttachedTo = Sprite;
	I.Screen = Screen;
	if (const TArray<FString>* Locals = Story.Names().ScriptLocals.Find(Script))
	{
		for (const FString& Local : *Locals)
		{
			I.Vars.Add(Local, 0);
		}
	}
	I.Vars.Add(TEXT("current_sprite"), Sprite);
	I.Vars.Add(TEXT("current_script"), I.Id);
	for (int32 A = 1; A <= 9; ++A)
	{
		I.Vars.Add(FString::Printf(TEXT("arg%d"), A), 0);
	}
	I.Vars.Add(TEXT("v_return"), 0);
	Instances.Add(MoveTemp(New));
	return I;
}

int32 UDinkStorySubsystem::StartProcedure(FName Script, FName Procedure, int32 Sprite, const TArray<int32>& Args, int32 Screen, bool bNewInstance)
{
	if (!Story.IsLoaded())
	{
		return 0;
	}
	Script = FName(*Script.ToString().ToLower());
	Procedure = FName(*Procedure.ToString().ToLower());
	const FString Path = DinkNarrative::EntryPath(Script.ToString(), Procedure.ToString());
	if (!Story.Names().EntryPaths.Contains(Path))
	{
		UE_LOG(LogDinkNarrative, Verbose, TEXT("no entry %s (script %s has no procedure %s in the converted story)"), *Path, *Script.ToString(), *Procedure.ToString());
		return 0;
	}
	FDinkScriptInstance* I = bNewInstance ? nullptr : FindInstanceForSprite(Sprite, Script);
	if (!I)
	{
		int32 InstanceScreen = Screen;
		if (InstanceScreen == INDEX_NONE)
		{
			const FDinkSprite* S = Director->FindSprite(Sprite);
			InstanceScreen = (S && S->Screen > 0) ? S->Screen : Director->GetCurrentScreen();
		}
		I = &CreateInstance(Script, Sprite, InstanceScreen);
	}
	BeginProcedure(*I, Procedure, Path, Args);
	return I->Id;
}

void UDinkStorySubsystem::BeginProcedure(FDinkScriptInstance& I, FName Procedure, const FString& Path, const TArray<int32>& Args)
{
	for (int32 A = 1; A <= 9; ++A)
	{
		I.Vars.Add(FString::Printf(TEXT("arg%d"), A), Args.IsValidIndex(A - 1) ? Args[A - 1] : 0);
	}
	if (Menu.InstanceId == I.Id)
	{
		Menu = FDinkMenu();
	}
	I.MenuTitle.Reset();
	I.Procedure = Procedure;
	I.State = EDinkInstanceState::Running;
	I.Block = EDinkBlock::None;
	I.BlockRef = 0;
	Story.SwitchFlow(I.FlowName());
	Story.ChoosePath(Path);
	AddEvent(TEXT("start"), Path, FString::Printf(TEXT("sprite=%d instance=%d"), I.Sprite, I.Id));
}

bool UDinkStorySubsystem::StartProcedureIn(int32 InstanceId, FName Procedure, const TArray<int32>& Args)
{
	FDinkScriptInstance* I = FindInstance(InstanceId);
	if (!I || !I->IsAlive() || !Story.IsLoaded())
	{
		return false;
	}
	Procedure = FName(*Procedure.ToString().ToLower());
	const FString Path = DinkNarrative::EntryPath(I->Script.ToString(), Procedure.ToString());
	if (!Story.Names().EntryPaths.Contains(Path))
	{
		return false;
	}
	BeginProcedure(*I, Procedure, Path, Args);
	return true;
}

int32 UDinkStorySubsystem::RunNow(int32 InstanceId)
{
	FDinkScriptInstance* Target = FindInstance(InstanceId);
	if (!Target || Target->State != EDinkInstanceState::Running || InstanceId == CurrentInstanceId)
	{
		return 0;
	}
	// run_script inside another script's command: that script's locals leave the story while the
	// other runs, and come back after (instances are TUniquePtr, so the pointer stays valid).
	FDinkScriptInstance* Outer = FindInstance(CurrentInstanceId);
	if (Outer)
	{
		SwapOut(*Outer);
	}
	const int32 Lines = StepInstance(InstanceId, MaxLinesPerStep);
	if (Outer && Outer->IsAlive())
	{
		Story.SwitchFlow(Outer->FlowName());
		SwapIn(*Outer);
	}
	return Lines;
}

int32 UDinkStorySubsystem::CreateDetachedInstance(FName Script, int32 Sprite)
{
	Script = FName(*Script.ToString().ToLower());
	if (!Story.IsLoaded() || !Story.Names().ScriptToKnot.Contains(Script))
	{
		return 0;
	}
	FDinkScriptInstance& I = CreateInstance(Script, Sprite, Director ? Director->GetCurrentScreen() : 0);
	I.AttachedTo = Sprite == UDinkDirector::HandleNoSprite ? UDinkDirector::HandleNoSprite : Sprite;
	I.State = EDinkInstanceState::Idle;
	return I.Id;
}

int32 UDinkStorySubsystem::RunForActor(AActor* Actor, FName Procedure)
{
	const UDinkOriginComponent* Origin = UDinkOriginComponent::FindOnActor(Actor);
	if (!Origin || !Director)
	{
		return 0;
	}
	const int32 Handle = Director->HandleForActor(Actor);
	const FDinkSprite* Sprite = Director->FindSprite(Handle);
	const FName Script = (Sprite && !Sprite->Script.IsNone()) ? Sprite->Script : Origin->ScriptName;
	if (Script.IsNone())
	{
		return 0;
	}
	return StartProcedure(Script, Procedure, Handle, {}, Origin->OriginId.Screen);
}

void UDinkStorySubsystem::KillInstance(int32 InstanceId, const TCHAR* Reason)
{
	if (FDinkScriptInstance* I = FindInstance(InstanceId))
	{
		FinishInstance(*I, Reason);
	}
}

void UDinkStorySubsystem::FinishInstance(FDinkScriptInstance& I, const TCHAR* Reason)
{
	if (!I.IsAlive())
	{
		return;
	}
	I.State = EDinkInstanceState::Finished;
	I.Block = EDinkBlock::None;
	if (Menu.InstanceId == I.Id)
	{
		Menu = FDinkMenu();
	}
	if (Story.IsLoaded())
	{
		Story.RemoveFlow(I.FlowName());
	}
	// Event texts are lower case whatever the FName display case: a cooked game has no case-preserving names (WITH_CASE_PRESERVING_NAME is
	// editor-only), so "main" displays as the engine's own "Main" there and a trace would differ from the editor's (AGENTS.md, Linux problems 47).
	AddEvent(TEXT("end"), FString::Printf(TEXT("%s.%s"), *I.Script.ToString().ToLower(), *I.Procedure.ToString().ToLower()), Reason);
}

void UDinkStorySubsystem::RemoveFinishedInstances()
{
	Instances.RemoveAll([](const TUniquePtr<FDinkScriptInstance>& I) { return !I->IsAlive(); });
}

void UDinkStorySubsystem::SwapIn(FDinkScriptInstance& I)
{
    I.Vars.Add(TEXT("current_sprite"),I.Sprite);
    I.Vars.Add(TEXT("current_script"),I.Id);
	TGuardValue<bool> Guard(bSyncingFacts, true);
	for (const TPair<FString, int32>& Var : I.Vars)
	{
		Story.SetInt(Var.Key, Var.Value);
	}
}

void UDinkStorySubsystem::SwapOut(FDinkScriptInstance& I)
{
	for (TPair<FString, int32>& Var : I.Vars)
	{
		Var.Value = Story.GetInt(Var.Key, Var.Value);
	}
    // Original decipher/var_equals resolves these from the live instance,
    // not a cached local that predates force_vision's sprite1000 reassignment.
    I.Vars.Add(TEXT("current_sprite"),I.Sprite);
    I.Vars.Add(TEXT("current_script"),I.Id);
    Story.SetInt(TEXT("current_sprite"),I.Sprite);
    Story.SetInt(TEXT("current_script"),I.Id);
}

void UDinkStorySubsystem::TakeInkErrors(const FDinkScriptInstance* I)
{
	for (const FString& E : Story.TakeErrors())
	{
		ReportError(FString::Printf(TEXT("ink runtime (%s.%s): %s"), I ? *I->Script.ToString() : TEXT("?"), I ? *I->Procedure.ToString() : TEXT("?"), *E));
	}
}

int32 UDinkStorySubsystem::StepInstance(int32 InstanceId, int32 MaxLines)
{
	FDinkScriptInstance* I = FindInstance(InstanceId);
	if (!I || I->State != EDinkInstanceState::Running)
	{
		return 0;
	}
	TGuardValue<int32> Current(CurrentInstanceId, InstanceId);
	SwapIn(*I);
	int32 Lines = 0;
	while (Lines < MaxLines && I->State == EDinkInstanceState::Running && (!Gameplay||!Gameplay->IsHardnessLoading()))
	{
		Story.SwitchFlow(I->FlowName());
		if (!Story.CanContinue())
		{
			TArray<FDinkStoryChoice> Choices = Story.GetChoices();
			if (Choices.Num() > 0)
			{
				I->State = EDinkInstanceState::Choosing;
				OpenMenu(*I);
			}
			else if (I->bEndWithProcedure)
			{
				FinishInstance(*I, TEXT("external returned"));
			}
			else
			{
				I->State = EDinkInstanceState::Idle;
				AddEvent(TEXT("idle"), FString::Printf(TEXT("%s.%s"), *I->Script.ToString().ToLower(), *I->Procedure.ToString().ToLower()));
			}
			break;
		}
		const FDinkStoryLine Line = Story.ContinueLine();
		++Lines;
		++I->LinesRun;
		TakeInkErrors(I);
		switch (Line.Kind)
		{
		case EDinkLineKind::Command:
		{
			++StatCommands;
			AddEvent(TEXT("cmd"), Line.Text, FString::Printf(TEXT("src=%d"), Line.SourceLine));
			const FDinkCommandResult Result = Director->Execute(*I, Line);
			if (Result.bEndScript)
			{
				FinishInstance(*I, *Line.Command.ToString());
			}
			else if (Result.bStopProcedure)
			{
				if (I->bEndWithProcedure)
				{
					FinishInstance(*I, *Line.Command.ToString());
				}
				else if (I->State == EDinkInstanceState::Running)
				{
					I->State = EDinkInstanceState::Idle;
					AddEvent(TEXT("idle"), FString::Printf(TEXT("%s.%s"), *I->Script.ToString().ToLower(), *I->Procedure.ToString().ToLower()), *Line.Command.ToString().ToLower());
				}
			}
			else if (Result.Block != 0)
			{
				++StatBlocks;
				I->State = EDinkInstanceState::Blocked;
				I->Block = static_cast<EDinkBlock>(Result.Block);
				I->BlockUntilMs = Result.BlockUntilMs;
				I->BlockRef = Result.BlockRef;
			}
			break;
		}
		case EDinkLineKind::Spoken:
			++StatSpoken;
			HandleSpokenLine(*I, Line);
			break;
		case EDinkLineKind::Title:
			I->MenuTitle.Add(Line);
			AddEvent(TEXT("title"), Line.Text);
			break;
		default:
			if (!Line.Raw.TrimStartAndEnd().IsEmpty())
			{
				AddEvent(TEXT("text"), Line.Text);
				UE_LOG(LogDinkNarrative, Warning, TEXT("untagged story line in %s.%s: \"%s\""), *I->Script.ToString(), *I->Procedure.ToString(), *Line.Text);
			}
			break;
		}
	}
	if (I->IsAlive())
	{
		SwapOut(*I);
		// sp_active(own sprite, 0) / sp_script on itself: the engine lets the script run on until it yields.
		if (I->bKillPending && I->State != EDinkInstanceState::Running)
		{
			FinishInstance(*I, TEXT("its sprite was removed"));
		}
	}
	return Lines;
}

int32 UDinkStorySubsystem::ResolveSpeaker(const FString& SpeakerTag) const
{
	if (SpeakerTag.IsEmpty())
	{
		return 0;
	}
	if (SpeakerTag.IsNumeric())
	{
		return FCString::Atoi(*SpeakerTag);
	}
	return Story.GetInt(SpeakerTag, 0);
}

void UDinkStorySubsystem::HandleSpokenLine(FDinkScriptInstance& I, const FDinkStoryLine& Line)
{
	static const FName SayStop(TEXT("say_stop")), SayStopNpc(TEXT("say_stop_npc"));
	const int32 Speaker = Line.bHasXY ? UDinkDirector::HandleNoSprite : ResolveSpeaker(Line.Speaker);
	if (Speaker == 0)
	{
		// dink.cpp say/say_stop: "Sprite 0 can talk? Yeah, didn't think so." - the engine shows nothing and does not wait.
		++StatSaySkipped;
		AddEvent(TEXT("say-skipped"), Line.Text, TEXT("speaker 0"));
		return;
	}
	if (Line.SayCall == SayStopNpc)
	{
		for (const FDinkActiveText& T : ActiveTexts)
		{
			if (T.Owner == Speaker)
			{
				++StatSaySkipped;
				AddEvent(TEXT("say-skipped"), Line.Text, TEXT("say_stop_npc: speaker already talking"));
				return;
			}
		}
	}
	if (Line.SayCall == SayStop)
	{
		// kill_text_owned_by(speaker) and kill_text_owned_by(1) (D:7914).
		ActiveTexts.RemoveAll([this, Speaker](const FDinkActiveText& T)
		{
			const bool bKill = T.Owner == Speaker || T.Owner == 1;
			if (bKill)
			{
				RemoveTextSprite(T.Handle);
			}
			return bKill;
		});
	}
	else if (!Line.bHasXY)
	{
		// say: kill_text_owned_by(speaker) unless 1000 (D:7756).
		ActiveTexts.RemoveAll([this, Speaker](const FDinkActiveText& T)
		{
			const bool bKill = T.Owner == Speaker;
			if (bKill)
			{
				RemoveTextSprite(T.Handle);
			}
			return bKill;
		});
	}
	const int32 TextHandle = ShowText(Line, Speaker, I.Id);
	if (!Line.HandleVariable.IsEmpty())
	{
		Story.SetInt(Line.HandleVariable, TextHandle);
	}
	AddEvent(TEXT("say"), Line.Text, FString::Printf(TEXT("spk=%d col=%d id=%s %s"), Speaker, Line.Color, *Line.Id, *Line.SayCall.ToString().ToLower()));
	if (Line.IsBlockingSay())
	{
		++StatBlocks;
		I.State = EDinkInstanceState::Blocked;
		I.Block = EDinkBlock::Say;
		I.BlockRef = TextHandle;
	}
}

int32 UDinkStorySubsystem::ShowText(const FDinkStoryLine& Line, int32 Speaker, int32 InstanceId)
{
	FDinkActiveText T;
	T.Handle = Director->AllocateHandle();
	FDinkSprite& S = Director->Sprites.Add(T.Handle);
	S.Handle = T.Handle;
	S.bText = true;
	if (const FDinkSprite* Owner = Director->FindSprite(Speaker))
	{
		S.X = Owner->X;
		S.Y = Owner->Y;
		S.Screen = Owner->Screen;
	}
	T.Owner = Speaker;
	T.InstanceId = InstanceId;
	T.Text = Line.Text;
	T.LineId = Line.Id;
	T.Color = Line.Color;
	T.bBlocking = Line.IsBlockingSay();
	T.bXY = Line.bHasXY;
	T.X = Line.X;
	T.Y = Line.Y;
	// strlen of the original string, which still had its 2-character colour code when it had a colour.
	const int32 Length = Line.Text.Len() + (Line.Color != 14 ? 2 : 0);
	T.ExpireMs = NowMs + DinkNarrative::TextDurationMs(Length);
    if(Gameplay)Gameplay->RecordOriginalHardnessBirth(T.Handle);
	ActiveTexts.Add(T);
	return T.Handle;
}

FDinkActiveText* UDinkStorySubsystem::FindText(int32 Handle)
{
	return ActiveTexts.FindByPredicate([Handle](const FDinkActiveText& T) { return T.Handle == Handle; });
}

/**
 * A text is a sprite slot with its own kill timer in the engine (dink.cpp D:16811-16823: the timer deactivates the slot it belongs to).
 * Here the active text list outlives a screen change, which releases every sprite but Dink and the survivors, and the handle is then
 * given to the next create_sprite or placement: removing "the text's handle" at its expiry deleted whatever lived there (a Bong,
 * silently, 2.7 s after its screen was entered).
 */
void UDinkStorySubsystem::RemoveTextSprite(int32 Handle)
{
	if (Director)
	{
		if (const FDinkSprite* Sprite = Director->FindSprite(Handle); Sprite && Sprite->bText)
		{
            if(Gameplay)Gameplay->RecordOriginalHardnessRelease(Handle);
			Director->Sprites.Remove(Handle);
		}
	}
}

void UDinkStorySubsystem::RemoveText(int32 Handle)
{
	ActiveTexts.RemoveAll([Handle](const FDinkActiveText& T) { return T.Handle == Handle; });
	if (Director)
	{
		if (const FDinkSprite* S = Director->FindSprite(Handle); S && S->bText)
		{
            if(Gameplay)Gameplay->RecordOriginalHardnessRelease(Handle);
			Director->Sprites.Remove(Handle);
		}
	}
}

void UDinkStorySubsystem::OpenMenu(FDinkScriptInstance& I)
{
	if (Menu.InstanceId != 0 && Menu.InstanceId != I.Id)
	{
		return; // another menu is showing; this one opens when it closes
	}
	Story.SwitchFlow(I.FlowName());
	Menu = FDinkMenu();
	Menu.InstanceId = I.Id;
	Menu.TitleColor = I.MenuTitleColor;
	for (const FDinkStoryLine& T : I.MenuTitle)
	{
		Menu.TitleLines.Add(T.bBlank ? FString() : T.Text);
	}
	Menu.Choices = Story.GetChoices();
	++StatMenus;
	TArray<FString> Texts;
	for (const FDinkStoryChoice& C : Menu.Choices)
	{
		Texts.Add(C.Text);
	}
	AddEvent(TEXT("menu"), FString::Join(Texts, TEXT(" | ")), FString::Printf(TEXT("instance=%d"), I.Id));
}

bool UDinkStorySubsystem::Choose(int32 VisibleIndex)
{
	FDinkScriptInstance* I = FindInstance(Menu.InstanceId);
	if (!I || !Menu.Choices.IsValidIndex(VisibleIndex) || I->State != EDinkInstanceState::Choosing)
	{
		return false;
	}
	const FDinkStoryChoice Picked = Menu.Choices[VisibleIndex];
	Story.SwitchFlow(I->FlowName());
	Story.Choose(Picked.Index);
	I->MenuTitle.Reset();
	I->State = EDinkInstanceState::Running;
	Menu = FDinkMenu();
	AddEvent(TEXT("choose"), Picked.Text, Picked.OptionId);
	return true;
}

void UDinkStorySubsystem::MoveMenuSelection(int32 Delta)
{
	if (Menu.InstanceId != 0 && Menu.Choices.Num() > 0)
	{
		Menu.Selected = (Menu.Selected + Delta + Menu.Choices.Num()) % Menu.Choices.Num();
	}
}

bool UDinkStorySubsystem::SkipDialogue()
{
	bool bSkipped = false;
	ActiveTexts.RemoveAll([this, &bSkipped](const FDinkActiveText& T)
	{
		if (T.bBlocking)
		{
			bSkipped = true;
			RemoveTextSprite(T.Handle);
			return true;
		}
		return false;
	});
	for (const TUniquePtr<FDinkScriptInstance>& I : Instances)
	{
		if (I->State == EDinkInstanceState::Blocked && I->Block == EDinkBlock::Button)
		{
			I->State = EDinkInstanceState::Running;
			I->Block = EDinkBlock::None;
			bSkipped = true;
		}
	}
	if (bSkipped)
	{
		AddEvent(TEXT("skip"), FString());
	}
	return bSkipped;
}

float UDinkStorySubsystem::GetFadeAlpha() const
{
	return Director ? Director->FadeAlpha : 0.f;
}

// ---------------------------------------------------------------------------------------------
// Time

bool UDinkStorySubsystem::UpdateBlocks()
{
	bool bChanged = false;
	for (const TUniquePtr<FDinkScriptInstance>& Ptr : Instances)
	{
		FDinkScriptInstance& I = *Ptr;
		if (I.State != EDinkInstanceState::Blocked)
		{
			continue;
		}
		bool bDone = false;
		switch (I.Block)
		{
		case EDinkBlock::Time: bDone = bInstantMode || NowMs >= I.BlockUntilMs; break;
		case EDinkBlock::Say: bDone = FindText(I.BlockRef) == nullptr; break;
		case EDinkBlock::Move: bDone = !Director->IsMoving(I.BlockRef); break;
		case EDinkBlock::Child:
		{
			const FDinkScriptInstance* Child = FindInstance(I.BlockRef);
			bDone = !Child || !Child->IsAlive();
			break;
		}
		case EDinkBlock::Frame: bDone = bInstantMode || NowMs > I.BlockUntilMs; break;
		case EDinkBlock::Button: bDone = bInstantMode; break;
		case EDinkBlock::Bow:
			// The release runs the script on itself (UDinkGameplay::ProcessBow). Instant mode (tests, smoke run) has no held key: the draw ends at
			// once with the power it has (0). A bow that is no longer drawn for this instance (load, reset) lets it go on too.
			bDone = bInstantMode || !Gameplay || Gameplay->GetBowInstance() != I.Id;
			if (bDone && Gameplay)
			{
				Gameplay->EndBowBlock(I.Id);
			}
			break;
		default: bDone = true; break;
		}
		if (bDone)
		{
			I.State = EDinkInstanceState::Running;
			I.Block = EDinkBlock::None;
			bChanged = true;
		}
	}
	return bChanged;
}

void UDinkStorySubsystem::Tick(float DeltaTime)
{
	Advance(DeltaTime);
}

TStatId UDinkStorySubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkStorySubsystem, STATGROUP_Tickables);
}

void UDinkStorySubsystem::Advance(double DeltaSeconds)
{
	if (HandlePendingRestart()) return;
	if (!IsReady())
	{
		return;
	}
    // Keep screen/load entry available while a previous capability is gated;
    // stop simulation only after giving the new screen its admission boundary.
    if(Gameplay&&Gameplay->IsHardnessLoading())
    {PollScreenChange();if(Gameplay->IsHardnessLoading())return;}
	const double DeltaMs = FMath::Max(0.0, DeltaSeconds * 1000.0);
	NowMs += DeltaMs;
	// The world-state clock (respawn timers) is game time too.
	if (UDinkWorldStateSubsystem* World = WorldState.Get())
	{
		ClockCarryMs += DeltaMs;
		const int64 Whole = FMath::FloorToInt64(ClockCarryMs);
		ClockCarryMs -= static_cast<double>(Whole);
		World->AdvanceGameTime(Whole);
	}
	PollScreenChange();
    if(Gameplay&&Gameplay->IsHardnessLoading())return;
	Director->Tick(DeltaMs, NowMs);
	UpdatePlayerPush();
	Gameplay->Tick(DeltaMs, NowMs);

	// Texts time out.
	for (int32 T = ActiveTexts.Num() - 1; T >= 0; --T)
	{
		if (ActiveTexts[T].ExpireMs <= NowMs)
		{
			RemoveTextSprite(ActiveTexts[T].Handle);
			ActiveTexts.RemoveAt(T);
		}
	}

	// set_callback_random: fires into an idle instance (D:11639).
	for (const TUniquePtr<FDinkScriptInstance>& I : Instances)
	{
		if (!I->CallbackProc.IsNone() && I->State == EDinkInstanceState::Idle && NowMs >= I->NextCallbackMs)
		{
			I->NextCallbackMs = NowMs + I->CallbackMinMs + (I->CallbackRandomMs > 0 ? Gameplay->RandomModulo(I->CallbackRandomMs) : 0);
			StartProcedure(I->Script, I->CallbackProc, I->Sprite);
		}
	}

	for (int32 Pass = 0; Pass < 8; ++Pass)
	{
		bool bProgress = UpdateBlocks();
		TArray<int32> Ids;
		for (const TUniquePtr<FDinkScriptInstance>& I : Instances)
		{
			if (I->State == EDinkInstanceState::Running)
			{
				Ids.Add(I->Id);
			}
		}
		for (const int32 Id : Ids)
		{
			const int32 Lines = StepInstance(Id, MaxLinesPerStep);
			bProgress |= Lines > 0;
			if (Lines >= MaxLinesPerStep)
			{
				UE_LOG(LogDinkNarrative, Warning, TEXT("instance %d ran %d lines in one tick without waiting; suspended to the next tick"), Id, Lines);
			}
		}
		RemoveFinishedInstances();
		if (Menu.InstanceId == 0)
		{
			for (const TUniquePtr<FDinkScriptInstance>& I : Instances)
			{
				if (I->State == EDinkInstanceState::Choosing)
				{
					OpenMenu(*I);
					break;
				}
			}
		}
		if (!bProgress)
		{
			break;
		}
	}
}

int64 UDinkStorySubsystem::RunUntilIdle(int64 MaxLines)
{
	int64 Total = 0;
	for (;;)
	{
		bool bProgress = false;
		if (bInstantMode)
		{
			Director->FinishAllMoves();
			for (int32 T = ActiveTexts.Num() - 1; T >= 0; --T)
			{
				RemoveTextSprite(ActiveTexts[T].Handle);
			}
			ActiveTexts.Reset();
			Director->FadeAlpha = Director->FadeTarget;
		}
		bProgress |= UpdateBlocks();
		if (bInstantMode && Menu.InstanceId != 0)
		{
			const int32 Pick = AutoChooser ? AutoChooser(Menu) : 0;
			bProgress |= Choose(FMath::Clamp(Pick, 0, FMath::Max(0, Menu.Choices.Num() - 1)));
		}
		TArray<int32> Ids;
		for (const TUniquePtr<FDinkScriptInstance>& I : Instances)
		{
			if (I->State == EDinkInstanceState::Running)
			{
				Ids.Add(I->Id);
			}
		}
		for (const int32 Id : Ids)
		{
			const int64 Budget = FMath::Min<int64>(MaxLinesPerStep, MaxLines - Total);
			if (Budget <= 0)
			{
				break;
			}
			const int32 Lines = StepInstance(Id, static_cast<int32>(Budget));
			Total += Lines;
			bProgress |= Lines > 0;
		}
		RemoveFinishedInstances();
		if (Menu.InstanceId == 0)
		{
			for (const TUniquePtr<FDinkScriptInstance>& I : Instances)
			{
				if (I->State == EDinkInstanceState::Choosing)
				{
					OpenMenu(*I);
					bProgress = true;
					break;
				}
			}
		}
		if (!bProgress || Total >= MaxLines)
		{
			break;
		}
	}
	return Total;
}

// ---------------------------------------------------------------------------------------------
// Screens and talking

void UDinkStorySubsystem::PollScreenChange()
{
	UWorld* World = GetWorld();
	if (!World || !World->IsGameWorld())
	{
		return;
	}
	UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
	if (Greybox && !Greybox->WarpSuppressed)
	{
		// A script that carries Dink through hardness (nohard 1), or puts him somewhere (load_screen), triggers no warp, as in the original (see
		// UDinkWarpComponent and UDinkDirector::IsDinkPlacedByScript).
		Greybox->WarpSuppressed = [Weak = TWeakObjectPtr<UDinkDirector>(Director)](const APawn* Pawn)
		{
			return Weak.IsValid() && (Weak->IsDinkCarriedThroughHardness() || Weak->IsDinkPlacedByScript());
		};
	}
	const ADinkScreenVolume* Screen = Greybox ? Greybox->GetCurrentScreen() : nullptr;
	if (Screen && Screen->ScreenNumber != LastScreen)
	{
		if (bNewGamePending && bRunScreenScripts)
		{
			// The start button's start-1.c / the HD engine's newgame.c: fists added and armed.
			bNewGamePending = false;
			Gameplay->StartNewGame();
		}
		OnScreenEntered(Screen->ScreenNumber);
	}
}

bool UDinkStorySubsystem::ForceOriginalHardnessVision(FDinkScriptInstance& Caller,int32 Vision)
{
    if(!Gameplay||!Gameplay->UsesOriginalHardnessProjection(Caller.Screen))return false;
    // Original force_vision moves the caller to sprite1000 before kill_all_scripts.
    DinkHardness::PreserveForceVisionCaller(Caller,UDinkDirector::HandleNoSprite);
    if(Facts.IsValid())Facts->SetFact(NAME_Vision,Vision);
    // This is nested script execution just like RunNow: save caller locals
    // before base/placement mains and restore its Ink flow afterwards.
    SwapOut(Caller);
    OnScreenEntered(Caller.Screen,true,Vision);
    if(Caller.IsAlive()){Story.SwitchFlow(Caller.FlowName());SwapIn(Caller);}
    return true;
}

void UDinkStorySubsystem::OnScreenEntered(int32 Screen,bool bForceVisionRebuild,int32 InitialVision,bool bRestartSavedRuntime)
{
	if (Screen == LastScreen && !bForceVisionRebuild)
	{
		return;
	}
    const bool OriginalTransition=Gameplay&&(Gameplay->RequiresOriginalHardnessScreen(Screen)||Gameplay->RequiresOriginalHardnessScreen(LastScreen)||Gameplay->HasSelectedOriginalHardness());
    if (Gameplay)
    {
        Gameplay->InvalidateRuntimeHardnessForScreenLoad(!bForceVisionRebuild);
        if(Gameplay->RequiresOriginalHardnessScreen(Screen))Gameplay->GateOriginalHardnessTransition();
    }
	const int32 Previous = LastScreen;
	LastScreen = Screen;
	AddEvent(TEXT("screen"), FString::FromInt(Screen), FString::Printf(TEXT("from %d"), Previous));
	// load_map builds the hardness anew (D:5966): what draw_hard_sprite / draw_hard_map changed on the last screen is gone.
	if (Gameplay)
	{
		Gameplay->OnScreenLoaded();
	}
	// Respawn clock: leaving a screen stamps its time (update_screen_time, D:1602); entering one clears
	// the timed overrides (editor_type 6/7/8) whose time is up (fix_dead_sprites, D:917).
	if (UDinkWorldStateSubsystem* World = bForceVisionRebuild?nullptr:WorldState.Get())
	{
		if (Previous > 0)
		{
			World->NotifyScreenExited(Previous);
		}
		for (const FDinkOriginId& Back : World->ProcessRespawns(Screen))
		{
			AddEvent(TEXT("respawn"), Back.ToString());
		}
	}
	if (UDinkFactSubsystem* F = Facts.Get())
	{
		F->SetFact(NAME_PlayerMap, Screen);
	}
	if (!bRunScreenScripts)
	{
		return;
	}

	// The engine kills every script not attached to 1000 when a screen loads (kill_all_scripts).
	TSet<int32> Keep;
	bool bSurvivorRuns = false;
	for (const TUniquePtr<FDinkScriptInstance>& I : Instances)
	{
		if (!I->IsAlive())
		{
			continue;
		}
		if (I->AttachedTo != UDinkDirector::HandleNoSprite)
		{
			FinishInstance(*I, TEXT("screen change"));
		}
		else
		{
			Keep.Add(I->Sprite);
			bSurvivorRuns |= I->State != EDinkInstanceState::Idle;
			// The engine has one current map and every sprite lives on it: a survivor (an armed item's script, the death
			// script, a cutscene that attached itself to 1000) now acts on the new screen. Its create_sprite and sp()
			// resolve against InstanceScreen; left on the screen it was created on, a spell armed in one room put its
			// missile on that room when cast in the next, where no brain thinks for it.
			I->Screen = Screen;
		}
	}
	RemoveFinishedInstances();
    // kill_last_sprite preserves every live sprite, independently of whether
    // its old script survives kill_all_scripts.
    if(OriginalTransition)for(const auto& Pair:Director->GetSprites())if(Pair.Value.bActive&&Pair.Value.GetProp(TEXT("live")))Keep.Add(Pair.Key);
    FString HardnessError;
    if(OriginalTransition&&
        ((Gameplay->RequiresOriginalHardnessScreen(Screen)&&!Gameplay->ValidateOriginalEditorCarry(Screen,InitialVision,HardnessError))||!Director->CarryOriginalLiveSprites(Screen,HardnessError)))
    {Gameplay->GateOriginalHardnessTransition();UE_LOG(LogDinkNarrative,Error,TEXT("original live carry refused: %s"),*HardnessError);return;}
	Director->ReleaseScreenSprites(Screen, Keep);
    Gameplay->BeginOriginalIdentityScreen(Screen);
    if(!Gameplay->BeginOriginalHardnessScreen(Screen,HardnessError,InitialVision))
    {UE_LOG(LogDinkNarrative,Error,TEXT("hardness screen admission refused: %s"),*HardnessError);return;}
    if(bRestartSavedRuntime){Gameplay->ArmWeapon();Gameplay->ArmMagic();}
	Gameplay->SyncDinkFromActor();
	// Remaster safety rule: the original cannot change screens while Dink is frozen, but a warp or
	// dink.Goto can. If no surviving script is running (one that could unfreeze him), do it here.
	if (Director->GetDink().bFrozen && !bSurvivorRuns)
	{
		UE_LOG(LogDinkNarrative, Log, TEXT("screen change ended the script that froze Dink; unfreezing him"));
		Director->SetFrozen(1, false);
	}

	// load_map clears screenlock (D:1016): a lock never outlives its screen.
	if (!bForceVisionRebuild && Director->bScreenLocked)
	{
		Gameplay->SetScreenLock(false);
	}
	// &vision is 0 when a screen loads; the base script may change it in main.
	if (UDinkFactSubsystem* F = Facts.Get())
	{
		F->SetFact(NAME_Vision, InitialVision);
	}
	// The screen's base script (map.dat): from its screen volume, or from the data table when headless.
	const ADinkScreenVolume* Volume = GetWorld() ? Director->FindScreenVolume(Screen) : nullptr;
	const FName BaseScript = Volume ? Volume->BaseScript : Gameplay->GetData().GetBaseScript(Screen);
	if (!BaseScript.IsNone() && HasProcedure(BaseScript, NAME_Main))
	{
		const int32 Id = StartProcedure(BaseScript, NAME_Main, 0, {}, Screen, /*bNewInstance*/ true);
		// dink.cpp:6805-6814: the base script's main runs with no_running_main set (only for this first run, up to its first block).
		TGuardValue<bool> NoRunningMain(bNoRunningMain, true);
		StepInstance(Id, MaxLinesPerStep);
	}
	EnterScreenPlacements(Screen);
	UE_LOG(LogTemp,Display,TEXT("HARDNESS_ENTRY_COMPLETE screen=%d required=%d projected=%d loading=%d"),Screen,int32(Gameplay->RequiresOriginalHardnessScreen(Screen)),int32(Gameplay->UsesOriginalHardnessProjection(Screen)),int32(Gameplay->IsHardnessLoading()));
}

void UDinkStorySubsystem::EnterScreenPlacements(int32 Screen)
{
    if(Gameplay&&Gameplay->IsHardnessLoading())return;
	const int32 Vision = Facts.IsValid() ? Facts->GetFact(NAME_Vision) : 0;
	UWorld* World = GetWorld();
	TMap<int32, AActor*> Actors;
	if (World)
	{
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			const UDinkOriginComponent* Origin = UDinkOriginComponent::FindOnActor(*It);
			if (Origin && Origin->OriginId.Screen == Screen)
			{
				Actors.Add(Origin->OriginId.Placement, *It);
			}
		}
	}
	// Removed placements stay hidden (editor_type 1, or 6/7/8 not yet due).
	for (const TPair<int32, AActor*>& Pair : Actors)
	{
		if (WorldState.IsValid() && WorldState->IsPlacementRemoved(FDinkOriginId(Screen, Pair.Key)))
		{
			Pair.Value->SetActorHiddenInGame(true);
			Pair.Value->SetActorEnableCollision(false);
		}
	}
	if (!Gameplay->HasData())
	{
		// No map.dat table (Scripts/sync_gameplay_data.py not run): the actors' scripts only.
		TArray<int32> Keys;
		Actors.GetKeys(Keys);
		Keys.Sort();
		for (const int32 Key : Keys)
		{
			AActor* Actor = Actors[Key];
			const UDinkOriginComponent* Origin = UDinkOriginComponent::FindOnActor(Actor);
			const ADinkPlaceholderActor* Placeholder = Cast<ADinkPlaceholderActor>(Actor);
			if ((WorldState.IsValid() && WorldState->IsPlacementRemoved(Origin->OriginId)) || (Placeholder && Placeholder->Vision != 0 && Placeholder->Vision != Vision))
			{
				continue;
			}
			if (!Actor->ActorHasTag(DinkFamilyCollisionFit::PromotedBackgroundTag) &&
				!Origin->ScriptName.IsNone() && HasProcedure(Origin->ScriptName, NAME_Main))
			{
				RunForActor(Actor, NAME_Main);
			}
		}
		return;
	}
	// place_sprites_game (D:6040-6140): every active live placement (type 1) of the current vision becomes
	// a sprite with map.dat's fields, and its script is loaded; then every script's main runs.
	// Placements without an actor in this world (headless tests, other maps) become virtual sprites.
    // Only migrated layered sources enter the original mixed-placement phase.
    // Legacy data/UE script handles retain their existing path.
    const bool Projected=Gameplay->UsesOriginalHardnessProjection(Screen);
    if(!Projected)Gameplay->PrepareLegacyOriginalIdentity(Screen);
    FString ProjectionError;
    if(Projected&&!Gameplay->PrepareOriginalHardnessPlacements(Screen,ProjectionError))
    {UE_LOG(LogDinkNarrative,Error,TEXT("original hardness placement phase refused: %s"),*ProjectionError);return;}
    // Allocate/reuse actual UE handles in the existing data order. The separate
    // original-slot plan controls hardness ties and original main dispatch only.
    const auto Placements=Gameplay->GetData().GetPlacementsOnScreen(Screen);
    const auto OriginalOrder=Projected?Gameplay->OriginalHardnessPlacementOrder(Screen):TArray<int32>();
    TMap<int32,int32> OriginalMains;
	TArray<int32> Mains;
	for (const FDinkPlacementInfo* P : Placements)
	{
        const int32 Type=Projected?Gameplay->EffectiveHardnessPlacementType(*P):P->Type;
		if (Type != 1 || (P->Vision != 0 && P->Vision != Vision) || (Projected&&!OriginalOrder.Contains(P->Origin.Placement)))
		{
			continue;
		}
		if (WorldState.IsValid() && WorldState->IsPlacementRemoved(P->Origin))
		{
			continue;
		}
		AActor* Actor = Actors.FindRef(P->Origin.Placement);
		const int32 Handle = Actor ? Director->HandleForActor(Actor) : Director->HandleForPlacement(Screen, P->Origin.Placement);
		if (Handle <= 1)
		{
			continue;
		}
		if (Actor)
		{
			Actor->SetActorHiddenInGame(false);
			Actor->SetActorEnableCollision(true);
		}
        if(Projected){Gameplay->BindOriginalHardnessPlacement(P->Origin,Handle);OriginalMains.Add(P->Origin.Placement,Handle);}
        else Gameplay->BindLegacyOriginalIdentity(P->Origin,Handle);
		Mains.Add(Handle);
	}
    if(Projected){Mains.Reset();for(int32 Owner:OriginalOrder)if(const auto* H=OriginalMains.Find(Owner))Mains.Add(*H);}
    if(Projected&&!Gameplay->FinishOriginalHardnessPlacements(Screen,ProjectionError))
    {UE_LOG(LogDinkNarrative,Error,TEXT("original hardness bindings refused: %s"),*ProjectionError);return;}
	for (const int32 Handle : Mains)
	{
		const FDinkSprite* S = Director->FindSprite(Handle);
		if (S && !S->Script.IsNone() && HasProcedure(S->Script, NAME_Main))
		{
			StartProcedure(S->Script, NAME_Main, Handle, {}, Screen);
		}
	}
}

void UDinkStorySubsystem::UpdatePlayerPush()
{
	const APawn* Pawn = Cast<APawn>(Director->GetDink().Actor.Get());
	if (!Pawn)
	{
		return;
	}
	// Pushing (D:13526): Dink keeps walking into hardness. Here: movement input but (almost) no movement.
	const FVector Input = Pawn->GetLastMovementInputVector();
	const bool bWalking = Input.Size2D() > 0.1;
	const bool bStuck = Pawn->GetVelocity().Size2D() < 30.0;
	const int32 Dir = bWalking ? Director->DirFromWorld(Director->GetDink().Screen, Pawn->GetActorLocation(), Input) : 0;
	Gameplay->UpdatePush(bWalking && bStuck, Dir, NowMs);
}

bool UDinkStorySubsystem::TryTalk(APawn* Pawn)
{
	if (!Pawn || !Director || Menu.InstanceId != 0)
	{
		return false;
	}
	// Frozen, or drawing the bow (Dink's brain runs process_bow and returns before the talk key, dink.cpp:14761-14766).
	if (Director->GetDink().bFrozen || (Gameplay && Gameplay->IsBowActive()))
	{
		return false;
	}
	// The original's rule first (run_through_tag_list_talk, in the screen's pixels); then, for the
	// greybox's sake, the nearest scripted actor within 3.5 m in front of the player.
	if (const int32 Target = Gameplay->FindTalkTarget(1))
	{
		const FDinkSprite* Sprite = Director->FindSprite(Target);
		UE_LOG(LogDinkNarrative, Log, TEXT("talk: sprite %d (%s, %s) from Dink at %.0f,%.0f dir %d on screen %d"), Target, Sprite ? *Sprite->Script.ToString() : TEXT("?"),
			Sprite ? *Sprite->Origin.ToString() : TEXT("-"), Director->GetDink().X, Director->GetDink().Y, Director->GetDink().Dir, Director->GetDink().Screen);
		return Sprite && StartProcedure(Sprite->Script, NAME_Talk, Target, {}, Sprite->Screen) != 0;
	}
	UE_LOG(LogDinkNarrative, Log, TEXT("talk: no sprite by the original rule from Dink at %.0f,%.0f dir %d on screen %d; nearest actor in front"),
		Director->GetDink().X, Director->GetDink().Y, Director->GetDink().Dir, Director->GetDink().Screen);
	UWorld* World = Pawn->GetWorld();
	const FVector From = Pawn->GetActorLocation();
	const FVector Forward = Pawn->GetActorForwardVector();
	constexpr double MaxDistance = 350.0;
	AActor* Best = nullptr;
	double BestDistance = MaxDistance;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* Actor = *It;
		const UDinkOriginComponent* Origin = UDinkOriginComponent::FindOnActor(Actor);
		// Placements, and sprites scripts created (create_sprite + sp_script: the letter, the bridge guard...).
		// Authored targets already used physical geometry above; the legacy 3.5 m
		// fallback must not reopen their old origin-based interaction range.
		if ((!Origin && !Director->HandleByActor.Contains(Actor)) || Actor->IsHidden() || Actor == Pawn || Actor->ActorHasTag(TEXT("DinkAuthoredArt")))
		{
			continue;
		}
		const FVector Delta = (Actor->GetActorLocation() - From) * FVector(1, 1, 0);
		const double Distance = Delta.Size();
		if (Distance >= BestDistance || FVector::DotProduct(Delta.GetSafeNormal(), Forward) < -0.2)
		{
			continue;
		}
		const int32* Handle = Director->HandleByActor.Find(Actor);
		const FDinkSprite* Sprite = Handle ? Director->FindSprite(*Handle) : nullptr;
		if (Sprite && !Sprite->bActive)
		{
			continue;
		}
		const FName Script = Sprite ? Sprite->Script : Origin->ScriptName;
		if (Script.IsNone() || !HasProcedure(Script, NAME_Talk))
		{
			continue;
		}
		Best = Actor;
		BestDistance = Distance;
	}
	if (!Best)
	{
		return false;
	}
	if (!UDinkOriginComponent::FindOnActor(Best))
	{
		const int32 Handle = Director->HandleByActor.FindRef(Best);
		const FDinkSprite* Sprite = Director->FindSprite(Handle);
		return Sprite && StartProcedure(Sprite->Script, NAME_Talk, Handle, {}, Sprite->Screen) != 0;
	}
	return RunForActor(Best, NAME_Talk) != 0;
}

// ---------------------------------------------------------------------------------------------
// Diagnostics

void UDinkStorySubsystem::ReportError(const FString& Message, bool bLogAsError)
{
	ErrorLog.Add(Message);
	if (ErrorLog.Num() > 2000)
	{
		ErrorLog.RemoveAt(0, ErrorLog.Num() - 2000);
	}
	AddEvent(TEXT("error"), Message);
	if (bQuietErrors)
	{
		UE_LOG(LogDinkNarrative, Log, TEXT("%s"), *Message);
	}
	else if (bLogAsError)
	{
		UE_LOG(LogDinkNarrative, Error, TEXT("%s"), *Message);
	}
	else
	{
		UE_LOG(LogDinkNarrative, Warning, TEXT("%s"), *Message);
	}
}

void UDinkStorySubsystem::AddEvent(FName Kind, const FString& Text, const FString& Detail)
{
	if (!bRecordEvents)
	{
		return;
	}
	FDinkNarrativeEvent E;
	E.TimeMs = NowMs;
	E.InstanceId = CurrentInstanceId;
	E.Kind = Kind;
	E.Text = Text;
	E.Detail = Detail;
	Events.Add(MoveTemp(E));
	if (Events.Num() > MaxEvents)
	{
		Events.RemoveAt(0, Events.Num() - MaxEvents);
	}
}

// ---------------------------------------------------------------------------------------------
// Save / load

bool UDinkStorySubsystem::RequestRestartGame()
{
    UWorld* World = GetWorld();
    if (!World || !World->IsGameWorld() || bInstantMode) return false;
    if (bRestartRequested || bRestartAwaitingWorld) return true;
    RestartMapName = UGameplayStatics::GetCurrentLevelName(World, true);
    if (RestartMapName.IsEmpty()) return false;
    bRestartRequested = true;
    return true;
}

bool UDinkStorySubsystem::HandlePendingRestart()
{
    UWorld* World = GetWorld();
    if (bRestartAwaitingWorld)
    {
        // OpenLevel queues travel. A further tick on the old world must not run
        // newgame or death again before the engine has replaced its actors.
        if (!World || World == RestartSourceWorld.Get() || !World->HasBegunPlay() ||
            !World->GetFirstPlayerController() || !World->GetFirstPlayerController()->GetPawn()) return true;
        bRestartAwaitingWorld = false;
        RestartSourceWorld.Reset();
        RestartMapName.Reset();
        bNewGamePending = true;
        UE_LOG(LogDinkNarrative, Display, TEXT("restart_game: fresh world ready; normal newgame startup pending"));
        return false;
    }
    if (!bRestartRequested) return false;
    if (!World || !World->IsGameWorld()) return true;
    bRestartRequested = false;
    bRestartAwaitingWorld = true;
    RestartSourceWorld = World;
    // These subsystems belong to the game instance, so level travel alone would
    // keep the dead player's facts, placement removals and running scripts.
    if (UDinkFactSubsystem* F = Facts.Get()) F->ResetToInitialValues();
    if (UDinkWorldStateSubsystem* State = WorldState.Get()) State->ResetState();
    NowMs = 0;
    ClockCarryMs = 0;
    NextInstanceId = 1;
    ResetRuntime();
    bNewGamePending = false;
    bRunScreenScripts = true;
    UE_LOG(LogDinkNarrative, Display, TEXT("restart_game: replacing world %s with fresh initial state"), *RestartMapName);
    UGameplayStatics::OpenLevel(World, FName(*RestartMapName), true);
    return true;
}

void UDinkStorySubsystem::ResetRuntime()
{
	Instances.Reset();
	ActiveTexts.Reset();
	Menu = FDinkMenu();
	CurrentInstanceId = 0;
	LastScreen = 0;
	if (Gameplay)
	{
		Gameplay->Reset();
		Gameplay->SetRandomSeed(StorySeed);
	}
	if (Director)
	{
		Director->ResetSprites();
		Director->FadeAlpha = Director->FadeTarget = 0.f;
	}
	if (Story.IsLoaded())
	{
		Story.ResetState(StorySeed);
		PushAllFactsToInk();
	}
}

FString UDinkStorySubsystem::SaveStateToJson()
{
	TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetNumberField(TEXT("version"), 1);
	Root->SetStringField(TEXT("ink"), Story.SaveStateJson());
	Root->SetNumberField(TEXT("nowMs"), NowMs);
	Root->SetNumberField(TEXT("nextInstanceId"), NextInstanceId);
	Root->SetNumberField(TEXT("lastScreen"), LastScreen);
	Root->SetNumberField(TEXT("menuInstance"), Menu.InstanceId);
	Root->SetNumberField(TEXT("menuSelected"), Menu.Selected);
	{
		TArray<TSharedPtr<FJsonValue>> Titles;
		for (const FString& T : Menu.TitleLines)
		{
			Titles.Add(MakeShared<FJsonValueString>(T));
		}
		Root->SetArrayField(TEXT("menuTitles"), Titles);
		Root->SetNumberField(TEXT("menuTitleColor"), Menu.TitleColor);
	}
	TArray<TSharedPtr<FJsonValue>> InstanceArray;
	for (const TUniquePtr<FDinkScriptInstance>& Ptr : Instances)
	{
		const FDinkScriptInstance& I = *Ptr;
		if (!I.IsAlive())
		{
			continue;
		}
		TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
		O->SetNumberField(TEXT("id"), I.Id);
		O->SetStringField(TEXT("script"), I.Script.ToString());
		O->SetStringField(TEXT("procedure"), I.Procedure.ToString());
		O->SetNumberField(TEXT("sprite"), I.Sprite);
		O->SetNumberField(TEXT("attachedTo"), I.AttachedTo);
		O->SetNumberField(TEXT("screen"), I.Screen);
		O->SetNumberField(TEXT("state"), static_cast<int32>(I.State));
		O->SetNumberField(TEXT("block"), static_cast<int32>(I.Block));
		O->SetNumberField(TEXT("blockUntilMs"), I.BlockUntilMs);
		O->SetNumberField(TEXT("blockRef"), I.BlockRef);
		O->SetNumberField(TEXT("parent"), I.ParentId);
		O->SetBoolField(TEXT("endWithProcedure"), I.bEndWithProcedure);
		O->SetStringField(TEXT("callbackProc"), I.CallbackProc.IsNone() ? FString() : I.CallbackProc.ToString());
		O->SetNumberField(TEXT("callbackMinMs"), I.CallbackMinMs);
		O->SetNumberField(TEXT("callbackRandomMs"), I.CallbackRandomMs);
		O->SetNumberField(TEXT("nextCallbackMs"), I.NextCallbackMs);
		O->SetNumberField(TEXT("menuSetY"), I.MenuSetY);
		O->SetNumberField(TEXT("menuTitleColor"), I.MenuTitleColor);
		TSharedRef<FJsonObject> Vars = MakeShared<FJsonObject>();
		for (const TPair<FString, int32>& V : I.Vars)
		{
			Vars->SetNumberField(V.Key, V.Value);
		}
		O->SetObjectField(TEXT("vars"), Vars);
		TArray<TSharedPtr<FJsonValue>> Titles;
		for (const FDinkStoryLine& T : I.MenuTitle)
		{
			TSharedRef<FJsonObject> TO = MakeShared<FJsonObject>();
			TO->SetStringField(TEXT("raw"), T.Raw);
			TO->SetStringField(TEXT("tags"), FString::Join(T.Tags, TEXT("\x1f")));
			Titles.Add(MakeShared<FJsonValueObject>(TO));
		}
		O->SetArrayField(TEXT("menuTitle"), Titles);
		InstanceArray.Add(MakeShared<FJsonValueObject>(O));
	}
	Root->SetArrayField(TEXT("instances"), InstanceArray);
	TArray<TSharedPtr<FJsonValue>> TextArray;
	for (const FDinkActiveText& T : ActiveTexts)
	{
		TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
		O->SetNumberField(TEXT("handle"), T.Handle);
		O->SetNumberField(TEXT("owner"), T.Owner);
		O->SetNumberField(TEXT("instance"), T.InstanceId);
		O->SetStringField(TEXT("text"), T.Text);
		O->SetStringField(TEXT("lineId"), T.LineId);
		O->SetNumberField(TEXT("color"), T.Color);
		O->SetNumberField(TEXT("expireMs"), T.ExpireMs);
		O->SetBoolField(TEXT("blocking"), T.bBlocking);
		O->SetBoolField(TEXT("xy"), T.bXY);
		O->SetNumberField(TEXT("x"), T.X);
		O->SetNumberField(TEXT("y"), T.Y);
		TextArray.Add(MakeShared<FJsonValueObject>(O));
	}
	Root->SetArrayField(TEXT("texts"), TextArray);
	Root->SetObjectField(TEXT("director"), Director->SaveState());
	Root->SetObjectField(TEXT("gameplay"), Gameplay->SaveState());

	FString Out;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Out);
	FJsonSerializer::Serialize(Root, Writer);
	return Out;
}

bool UDinkStorySubsystem::LoadStateFromJson(const FString& Json)
{
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid() || Root->GetIntegerField(TEXT("version")) != 1)
	{
		ReportError(TEXT("narrative save state does not parse (version 1 expected)"));
		return false;
	}
    if(Gameplay&&Gameplay->RequiresOriginalHardnessScreen(Root->GetIntegerField(TEXT("lastScreen"))))Gameplay->GateOriginalHardnessTransition();
	ResetRuntime();
	if (!Story.LoadStateJson(Root->GetStringField(TEXT("ink"))))
	{
		ReportError(TEXT("narrative save: Ink state does not load"));
		return false;
	}
	NowMs = Root->GetNumberField(TEXT("nowMs"));
	NextInstanceId = Root->GetIntegerField(TEXT("nextInstanceId"));
	LastScreen = Root->GetIntegerField(TEXT("lastScreen"));
    bool SavedOriginal=false;
    const TSharedPtr<FJsonObject>* SavedGameplayPtr=nullptr;
    const auto SavedGameplay=Root->TryGetObjectField(TEXT("gameplay"),SavedGameplayPtr)?*SavedGameplayPtr:TSharedPtr<FJsonObject>();
    if(SavedGameplay.IsValid())
    {
        const auto Policy=SavedGameplay->TryGetField(TEXT("originalHardnessVisitV1"));
        if(Policy.IsValid()&&Policy->Type!=EJson::Boolean)
        {Gameplay->GateOriginalHardnessTransition();ReportError(TEXT("original hardness visit policy must be bool"));return false;}
        SavedGameplay->TryGetBoolField(TEXT("originalHardnessVisitV1"),SavedOriginal);
    }
    const bool RestartOriginalLoad=Gameplay->RequiresOriginalHardnessScreen(LastScreen)||SavedOriginal;
    if(RestartOriginalLoad)
    {
        auto DirectorState=MakeShared<FJsonObject>(*Root->GetObjectField(TEXT("director")));
        TArray<TSharedPtr<FJsonValue>> DinkOnly;
        for(const auto& V:DirectorState->GetArrayField(TEXT("sprites")))
            if(V->AsObject()->GetIntegerField(TEXT("handle"))==1)DinkOnly.Add(V);
        DirectorState->SetArrayField(TEXT("sprites"),DinkOnly);Director->LoadState(DirectorState);
    }
    else Director->LoadState(Root->GetObjectField(TEXT("director")));
	const TSharedPtr<FJsonObject>* GameplayState = nullptr;
	Gameplay->LoadState(Root->TryGetObjectField(TEXT("gameplay"), GameplayState) ? *GameplayState : nullptr);
	for (const TSharedPtr<FJsonValue>& V : Root->GetArrayField(TEXT("instances")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		TUniquePtr<FDinkScriptInstance> New = MakeUnique<FDinkScriptInstance>();
		FDinkScriptInstance& I = *New;
		I.Id = O->GetIntegerField(TEXT("id"));
		I.Script = FName(*O->GetStringField(TEXT("script")));
		I.Procedure = FName(*O->GetStringField(TEXT("procedure")));
		I.Sprite = O->GetIntegerField(TEXT("sprite"));
		I.AttachedTo = O->GetIntegerField(TEXT("attachedTo"));
		I.Screen = O->GetIntegerField(TEXT("screen"));
		I.State = static_cast<EDinkInstanceState>(O->GetIntegerField(TEXT("state")));
		I.Block = static_cast<EDinkBlock>(O->GetIntegerField(TEXT("block")));
		I.BlockUntilMs = O->GetNumberField(TEXT("blockUntilMs"));
		I.BlockRef = O->GetIntegerField(TEXT("blockRef"));
		I.ParentId = O->GetIntegerField(TEXT("parent"));
		I.bEndWithProcedure = O->GetBoolField(TEXT("endWithProcedure"));
		const FString Callback = O->GetStringField(TEXT("callbackProc"));
		I.CallbackProc = Callback.IsEmpty() ? NAME_None : FName(*Callback);
		I.CallbackMinMs = O->GetIntegerField(TEXT("callbackMinMs"));
		I.CallbackRandomMs = O->GetIntegerField(TEXT("callbackRandomMs"));
		I.NextCallbackMs = O->GetNumberField(TEXT("nextCallbackMs"));
		I.MenuSetY = O->GetIntegerField(TEXT("menuSetY"));
		I.MenuTitleColor = O->GetIntegerField(TEXT("menuTitleColor"));
		for (const auto& Var : O->GetObjectField(TEXT("vars"))->Values)
		{
			I.Vars.Add(FString(*Var.Key), static_cast<int32>(Var.Value->AsNumber()));
		}
		for (const TSharedPtr<FJsonValue>& TV : O->GetArrayField(TEXT("menuTitle")))
		{
			TArray<FString> Tags;
			TV->AsObject()->GetStringField(TEXT("tags")).ParseIntoArray(Tags, TEXT("\x1f"));
			I.MenuTitle.Add(FDinkStoryLine::Parse(TV->AsObject()->GetStringField(TEXT("raw")), Tags));
		}
		Instances.Add(MoveTemp(New));
	}
	for (const TSharedPtr<FJsonValue>& V : Root->GetArrayField(TEXT("texts")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		FDinkActiveText T;
		T.Handle = O->GetIntegerField(TEXT("handle"));
		T.Owner = O->GetIntegerField(TEXT("owner"));
		T.InstanceId = O->GetIntegerField(TEXT("instance"));
		T.Text = O->GetStringField(TEXT("text"));
		T.LineId = O->GetStringField(TEXT("lineId"));
		T.Color = O->GetIntegerField(TEXT("color"));
		T.ExpireMs = O->GetNumberField(TEXT("expireMs"));
		T.bBlocking = O->GetBoolField(TEXT("blocking"));
		T.bXY = O->GetBoolField(TEXT("xy"));
		T.X = O->GetIntegerField(TEXT("x"));
		T.Y = O->GetIntegerField(TEXT("y"));
		ActiveTexts.Add(T);
	}
	const int32 MenuInstance = Root->GetIntegerField(TEXT("menuInstance"));
	if (FDinkScriptInstance* I = FindInstance(MenuInstance))
	{
		Story.SwitchFlow(I->FlowName());
		Menu = FDinkMenu();
		Menu.InstanceId = MenuInstance;
		Menu.Selected = Root->GetIntegerField(TEXT("menuSelected"));
		Menu.TitleColor = Root->GetIntegerField(TEXT("menuTitleColor"));
		for (const TSharedPtr<FJsonValue>& T : Root->GetArrayField(TEXT("menuTitles")))
		{
			Menu.TitleLines.Add(T->AsString());
		}
		Menu.Choices = Story.GetChoices();
	}
	// The fact store is the source of truth: whatever the Ink state held, facts win.
	PushAllFactsToInk();
    Gameplay->RebuildOriginalIdentityFromActualSprites();
    if(DinkHardness::RestartOriginalScreenOnLoad(RestartOriginalLoad))
    {
        const int32 LoadedScreen=LastScreen;
        for(const auto& Instance:Instances)if(Instance->IsAlive())FinishInstance(*Instance,TEXT("original marked-world load rebuild"));
        RemoveFinishedInstances();
        for(const auto& Text:ActiveTexts)RemoveTextSprite(Text.Handle);
        ActiveTexts.Reset();Menu=FDinkMenu();
        // Original load_game kills all runtime sprites, reloads smallMap and
        // restarts the screen. Saved editor overrides/pictures remain loaded.
        Director->ReleaseScreenSprites(LoadedScreen,{});
        Gameplay->RestartOriginalSavedRuntime();
        OnScreenEntered(LoadedScreen,true,0,true);
        if(Gameplay->IsHardnessLoading())
        {ReportError(TEXT("marked-world saved screen admission failed; gameplay remains gated"));return false;}
    }
    else Gameplay->FinishLegacyHardnessLoad(LastScreen);
	AddEvent(TEXT("load"), FString::Printf(TEXT("%d instances, %d texts"), Instances.Num(), ActiveTexts.Num()));
	return true;
}

void UDinkStorySubsystem::CaptureToSave(UDinkSaveGame* Save)
{
	if (Save && IsReady())
	{
		Save->SubsystemState.Add(NAME_Narrative, SaveStateToJson());
	}
}

void UDinkStorySubsystem::RestoreFromSave(const UDinkSaveGame* Save)
{
	if (!Save || !IsReady())
	{
		return;
	}
	bNewGamePending = false;
	if (const FString* State = Save->SubsystemState.Find(NAME_Narrative))
	{
		LoadStateFromJson(*State);
	}
	else
	{
		ResetRuntime();
	}
	// The save moved the pawn in one step: have the greybox find the saved screen now. Left to its 0.25 s check, PollScreenChange
	// saw the screen the pawn had left, entered it (its scripts, its sprites, its exit time) and only then the saved one.
	if (UWorld* World = GetWorld(); World && World->IsGameWorld())
	{
		if (UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>())
		{
			Greybox->RefreshCurrentScreen();
		}
	}
}

FString FDinkSmokeReport::ToText() const
{
	FString Out;
	Out += FString::Printf(TEXT("entry points: %d\ncompleted: %d\nhit step cap: %d (of which looping through a blocking command - wait, move_stop... - i.e. the original's endless idle loops: %d)\nstalled: %d\nwith runtime errors: %d\n"),
		EntryPoints, Completed, HitStepCap, CapInIdleLoop, Stalled, WithErrors);
	Out += FString::Printf(TEXT("lines run: %lld; spoken lines: %d (of which not shown, as in the engine - speaker 0 or say_stop_npc while talking: %d); commands: %d; menus: %d\n"), TotalLines, SpokenLines, SaySkipped, Commands, Menus);
	Out += FString::Printf(TEXT("\ntargets the story calls but does not contain (scripts or procedures absent from the original game; count):\n"));
	TArray<FString> Missing;
	MissingTargets.GetKeys(Missing);
	Missing.Sort();
	for (const FString& M : Missing)
	{
		Out += FString::Printf(TEXT("  %s %d\n"), *M, MissingTargets[M]);
	}
	Out += TEXT("\ncommands executed (name count):\n");
	TArray<TPair<FName, int32>> Sorted;
	for (const TPair<FName, int32>& C : CommandCounts)
	{
		Sorted.Add(C);
	}
	Sorted.Sort([](const TPair<FName, int32>& A, const TPair<FName, int32>& B) { return A.Value != B.Value ? A.Value > B.Value : A.Key.LexicalLess(B.Key); });
	for (const TPair<FName, int32>& C : Sorted)
	{
		Out += FString::Printf(TEXT("  %s %d\n"), *C.Key.ToString(), C.Value);
	}
	Out += FString::Printf(TEXT("\nentry points that hit the step cap (%d):\n"), CappedEntries.Num());
	for (const FString& E : CappedEntries)
	{
		Out += TEXT("  ") + E + TEXT("\n");
	}
	Out += FString::Printf(TEXT("\nentry points that stalled (%d):\n"), StalledEntries.Num());
	for (const FString& E : StalledEntries)
	{
		Out += TEXT("  ") + E + TEXT("\n");
	}
	Out += FString::Printf(TEXT("\nerrors (%d):\n"), Errors.Num());
	for (const FString& E : Errors)
	{
		Out += TEXT("  ") + E + TEXT("\n");
	}
	return Out;
}
