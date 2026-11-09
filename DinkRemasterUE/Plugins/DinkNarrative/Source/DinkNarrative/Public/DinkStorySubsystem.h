#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "DinkInkStory.h"
#include "DinkStorySubsystem.generated.h"

class UDinkDirector;
class UDinkGameplay;
class UDinkFactSubsystem;
class UDinkWorldStateSubsystem;
class UDinkSaveGame;
class APawn;
class FDinkNarrativeInputProcessor;
class AHUD;
class UCanvas;

/** Life cycle of one script instance. */
enum class EDinkInstanceState : uint8
{
	/** Alive, no procedure running (DinkC instances outlive their procedures: main sets locals, talk reads them). */
	Idle,
	/** Has a procedure to step. */
	Running,
	/** Waiting for a blocking command or a say_stop to finish. */
	Blocked,
	/** Waiting for the player to pick a menu option. */
	Choosing,
	/** Ended (kill_this_task, its sprite removed, screen change, external finished). Removed after the tick. */
	Finished,
};

/** What a blocked instance waits for. */
enum class EDinkBlock : uint8
{
	None,
	/** wait(ms), fades: until NowMs >= BlockUntilMs. */
	Time,
	/** say_stop*: until text BlockRef is gone (timed out or skipped). */
	Say,
	/** move_stop: until sprite BlockRef stops moving. */
	Move,
	/** external(): until instance BlockRef has finished. */
	Child,
	/** draw_screen: one tick. */
	Frame,
	/** wait_for_button / show_bmp: until the player presses the skip key. */
	Button,
	/** activate_bow: until the attack key is let go (UDinkGameplay::ProcessBow runs the script on, dink.cpp:14615-14620). */
	Bow,
};

/**
 * One running DinkC script instance (the engine's rinfo[] entry): a script attached to a sprite,
 * with its own Ink flow (call stack, output, choices) and its own copy of the script's local
 * variables. Several are alive at once, as in the original.
 */
struct DINKNARRATIVE_API FDinkScriptInstance
{
	int32 Id = 0;
	/** Original script name ("s1-h1-m"). */
	FName Script;
	/** Procedure last started ("talk"). */
	FName Procedure;
	/** &current_sprite: the sprite handle the script belongs to (0 = none, e.g. a screen's base script). */
	int32 Sprite = 0;
	/** Owner for screen changes (script_attach): the sprite by default, 1000 = survives screen changes. */
	int32 AttachedTo = 0;
	/** Original screen the instance runs on (coordinates and sp() refer to it). */
	int32 Screen = 0;
	EDinkInstanceState State = EDinkInstanceState::Idle;
	EDinkBlock Block = EDinkBlock::None;
	double BlockUntilMs = 0.0;
	int32 BlockRef = 0;
	/** Instance that called this one with external() and waits for it (0 = none). Ends with its procedure. */
	int32 ParentId = 0;
	bool bEndWithProcedure = false;
	/** sp_active(own sprite, 0) / kill requested: ends at its next stop. */
	bool bKillPending = false;
	/** Ink VAR values that belong to this instance: the script's locals and the pseudo-variables. */
	TMap<FString, int32> Vars;
	/** Title lines and arguments of the menu being built (choice_start / title_start). */
	TArray<FDinkStoryLine> MenuTitle;
	int32 MenuSetY = 0;
	int32 MenuTitleColor = 0;
	/** set_callback_random: procedure, minimum and random part (ms), next firing time. */
	FName CallbackProc;
	int32 CallbackMinMs = 0;
	int32 CallbackRandomMs = 0;
	double NextCallbackMs = 0.0;
	/** Lines executed in total (smoke-run statistics and loop detection). */
	int64 LinesRun = 0;

	FString FlowName() const { return FString::Printf(TEXT("i%d"), Id); }
	bool IsAlive() const { return State != EDinkInstanceState::Finished; }
};

/** A text on screen (the engine's brain-8 text sprite). */
struct DINKNARRATIVE_API FDinkActiveText
{
	/** Text sprite handle (what `int &t = say_xy(...)` receives). */
	int32 Handle = 0;
	/** Speaker handle, 1000 for _xy texts. */
	int32 Owner = 0;
	int32 InstanceId = 0;
	FString Text;
	FString LineId;
	int32 Color = 14;
	double ExpireMs = 0.0;
	bool bBlocking = false;
	bool bXY = false;
	int32 X = 0;
	int32 Y = 0;
};

/** The menu currently shown (one at a time, like the original's talk menu). */
struct DINKNARRATIVE_API FDinkMenu
{
	int32 InstanceId = 0;
	TArray<FString> TitleLines;
	int32 TitleColor = 0;
	TArray<FDinkStoryChoice> Choices;
	int32 Selected = 0;
};

/** One thing that happened, in order (tests, the smoke run, dink.Story). */
struct DINKNARRATIVE_API FDinkNarrativeEvent
{
	double TimeMs = 0.0;
	int32 InstanceId = 0;
	/** say, cmd, title, menu, choose, end, kill, error. */
	FName Kind;
	FString Text;
	FString Detail;
};

/** Statistics of a smoke run of every entry point. */
struct DINKNARRATIVE_API FDinkSmokeReport
{
	int32 EntryPoints = 0;
	int32 Completed = 0;
	int32 HitStepCap = 0;
	/** Ran out of things to do while an instance still waited (should be 0 in stub mode). */
	int32 Stalled = 0;
	/** Of those that hit the cap: still looping through a blocking command (wait, move_stop...: the original's idle loops, which take real time). */
	int32 CapInIdleLoop = 0;
	int32 WithErrors = 0;
	int64 TotalLines = 0;
	int32 SpokenLines = 0;
	int32 Commands = 0;
	int32 Menus = 0;
	TMap<FName, int32> CommandCounts;
	/** "entry: message" for every runtime/director error. */
	TArray<FString> Errors;
	TArray<FString> CappedEntries;
	TArray<FString> StalledEntries;
	int32 SaySkipped = 0;
	TMap<FString, int32> MissingTargets;
	FString ToText() const;
};

/**
 * Owns the one converted Ink story (Content/Dink/Data/Story/dink.json, Inkpot's InkPlusPlus runtime)
 * and runs DinkC script instances on it:
 *
 *  - StartProcedure("s1-h1-m", "talk", Sprite) enters `d_s1_h1_m.on_talk` in that sprite's instance.
 *  - Each instance runs in its own Ink flow (ink 1.1 multi-flow), so an NPC's idle loop, a cutscene
 *    and the player's conversation are alive at the same time. One story = one set of globals, as in
 *    DinkC; script locals are swapped in and out per instance (DESIGN.md 5).
 *  - Every output line is classified: spoken lines go to the presentation (floating text), command
 *    lines to UDinkDirector, menus become choices. Blocking commands suspend only their instance.
 *  - Ink VARs and UDinkFactSubsystem are one source of truth: fact changes are pushed into the story,
 *    story assignments are written into the facts (and from there into the player's stats).
 *  - Save/load: the Ink state (all flows), the instances, the sprite handle table and the texts on
 *    screen go into UDinkSaveGame::SubsystemState["narrative"].
 *
 * Console: dink.Run, dink.Say, dink.Fact, dink.Choose, dink.Skip, dink.Story, dink.ScreenScripts.
 */
UCLASS()
class DINKNARRATIVE_API UDinkStorySubsystem : public UGameInstanceSubsystem, public FTickableGameObject
{
	GENERATED_BODY()

public:
	UDinkStorySubsystem();

	// USubsystem
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** For tests: set up without a running game instance, using these fact/world-state objects. */
	bool SetupStandalone(UDinkFactSubsystem* InFacts, UDinkWorldStateSubsystem* InWorldState, FString* OutError = nullptr);

	bool IsReady() const { return Story.IsLoaded(); }
	FDinkInkStory& GetStory() { return Story; }
	UDinkDirector* GetDirector() const { return Director; }
	/** The engine's gameplay rules (hit, touch, push, damage and death, items, status update). */
	UDinkGameplay* GetGameplay() const { return Gameplay; }
	UDinkFactSubsystem* GetFacts() const { return Facts.Get(); }
	UDinkWorldStateSubsystem* GetWorldState() const { return WorldState.Get(); }
	virtual UWorld* GetWorld() const override;

	// ---- Running scripts ----

	/** True if the converted story has an entry point for this script procedure. */
	bool HasProcedure(FName Script, FName Procedure) const;

	/**
	 * Starts Procedure of Script for Sprite (a handle, see UDinkDirector). Reuses the instance already
	 * attached to that sprite with that script (its locals survive; the running procedure is abandoned,
	 * as run_script does), otherwise creates one. Args become &arg1..&arg9. Returns the instance ID, 0 if
	 * the story has no such entry (logged).
	 */
	int32 StartProcedure(FName Script, FName Procedure, int32 Sprite, const TArray<int32>& Args = {}, int32 Screen = INDEX_NONE, bool bNewInstance = false);

	/** Runs Procedure of the script on the actor's origin component, for that actor's handle. */
	int32 RunForActor(AActor* Actor, FName Procedure);

	/** Relocates an existing instance to Procedure (run_script on a known instance). False if it has no such entry. */
	bool StartProcedureIn(int32 InstanceId, FName Procedure, const TArray<int32>& Args = {});
	/**
	 * The engine's run_script: steps a Running instance now, until it blocks or ends. Safe inside another
	 * instance's command (that instance's locals are swapped out and back). Does nothing for the instance
	 * being stepped. Returns the lines run.
	 */
	int32 RunNow(int32 InstanceId);
	/** load_script(Script, Sprite): a new idle instance without a procedure; Sprite 1000 survives screen changes. 0 if the story lacks the script. */
	int32 CreateDetachedInstance(FName Script, int32 Sprite);

	/** Ends an instance (removes its flow). */
	void KillInstance(int32 InstanceId, const TCHAR* Reason);

	FDinkScriptInstance* FindInstance(int32 InstanceId);
	const TArray<TUniquePtr<FDinkScriptInstance>>& GetInstances() const { return Instances; }
	/** The instance currently attached to Sprite with Script (any script if None). */
	FDinkScriptInstance* FindInstanceForSprite(int32 Sprite, FName Script = NAME_None);
	/** The instance being stepped right now (commands and externals act for it), or null. */
	FDinkScriptInstance* GetCurrentInstance() { return FindInstance(CurrentInstanceId); }

	/** Advances time and steps every runnable instance (what Tick does). */
	void Advance(double DeltaSeconds);

	/**
	 * Steps until no instance can make progress without time passing or input, or MaxLines lines ran.
	 * In instant mode blocking commands complete at once and menus are answered by AutoChooser.
	 * Returns the number of lines executed.
	 */
	int64 RunUntilIdle(int64 MaxLines = 100000);

	double GetNowMs() const { return NowMs; }

	// ---- Presentation state ----
	const TArray<FDinkActiveText>& GetActiveTexts() const { return ActiveTexts; }
	const FDinkMenu* GetActiveMenu() const { return Menu.InstanceId != 0 ? &Menu : nullptr; }
	/** Picks visible option VisibleIndex (0-based) of the active menu. */
	bool Choose(int32 VisibleIndex);
	/** Keyboard menu: move the highlight / pick the highlighted option. */
	void MoveMenuSelection(int32 Delta);
	bool ChooseSelected() { return Choose(Menu.Selected); }
	/** The original's skip: ends the blocking texts (and button waits). Returns true if something was skipped. */
	bool SkipDialogue();
	/** Text sprite handle -> text. */
	FDinkActiveText* FindText(int32 Handle);
	void RemoveText(int32 Handle);
	/** Takes a text's sprite out of the sprite table, but only while that handle still is a text sprite (a released handle may belong to a monster by now). */
	void RemoveTextSprite(int32 Handle);
	/** Shows a line for Speaker (handle) the way the director shows spoken lines. Returns the text handle. */
	int32 ShowText(const FDinkStoryLine& Line, int32 Speaker, int32 InstanceId);

	/** Black-screen amount 0..1 (fade_down/fade_up). */
	float GetFadeAlpha() const;

	// ---- Facts ----

	/** Pushes every fact into its Ink VAR (story load, fact reset, load game). */
	void PushAllFactsToInk();

	// ---- Save / load ----

	/** Everything needed to resume mid-conversation, as JSON text. */
	FString SaveStateToJson();
	bool LoadStateFromJson(const FString& Json);
	void CaptureToSave(UDinkSaveGame* Save);
	void RestoreFromSave(const UDinkSaveGame* Save);
	/** Defer restart until outside the active script; replaces the world and starts a fresh game.
	 * Returns false in standalone/instant story tests, which have no playable world to reload. */
	bool RequestRestartGame();

	/** All instances and texts gone; Ink state reset; facts pushed again. */
	void ResetRuntime();

	// ---- Interaction ----

	/** The talk key: runs `talk` of the nearest scripted actor in front of Pawn. True if one started. */
	bool TryTalk(APawn* Pawn);
	/** Screen load (the engine's load_screen + draw_screen): kills scripts of the old screen, runs `main` of the new one. */
	void OnScreenEntered(int32 Screen);
	/** Run screen and placement `main` procedures when the player enters a screen (dink.ScreenScripts). */
	bool bRunScreenScripts = true;
	/** A new game (no save loaded): newgame.c `main` runs before the first screen's scripts. Set in Initialize. */
	bool bNewGamePending = false;

	// ---- Modes and diagnostics ----

	/** Stub mode: every blocking command completes at once (smoke run, tests). */
	bool bInstantMode = false;
	/** In instant mode: picks a visible option for a menu (0-based); default the first. */
	TFunction<int32(const FDinkMenu&)> AutoChooser;
	/** Lines one instance may run in one step before it is suspended to the next tick (runaway loops). */
	int32 MaxLinesPerStep = 5000;
	/** Record FDinkNarrativeEvent entries (tests and dink.Story). Bounded to the last MaxEvents. */
	bool bRecordEvents = true;
	int32 MaxEvents = 4096;
	TArray<FDinkNarrativeEvent> Events;
	/** Errors reported (Ink runtime, unknown commands...). */
	TArray<FString> ErrorLog;
	/** Log reported errors at Log verbosity instead of Error (smoke run: they go into the report). */
	bool bQuietErrors = false;
	/**
	 * The original's g_dglos.no_running_main (dink.cpp:6812-6814): true only while a screen's base script runs its main during a
	 * screen build (EnterScreen). sp_script then attaches the script but does not run its main on the spot (dink.cpp:8163, 8169):
	 * init_scripts (dink.cpp:11690) runs it once the screen is built, which here is the deferred StartProcedure.
	 */
	bool bNoRunningMain = false;
	/** Seed of the Ink RANDOM state after ResetRuntime. */
	int32 StorySeed = 1997;
	/** Counters since load (smoke-run statistics). */
	int64 StatSpoken = 0;
	int64 StatCommands = 0;
	int64 StatMenus = 0;
	/** Times an instance blocked (wait, move_stop, say_stop, fades, external...). */
	int64 StatBlocks = 0;
	/** Spoken lines the engine would not show (speaker 0, say_stop_npc while the speaker talks). */
	int64 StatSaySkipped = 0;
	/** Things the story asked for that it does not contain ("external emake.medium", "sp_script en-drag"), with counts. */
	TMap<FString, int32> MissingTargets;
	void ReportError(const FString& Message, bool bLogAsError = true);
	void AddEvent(FName Kind, const FString& Text, const FString& Detail = FString());

	/**
	 * Runs every entry point once (all commands stubbed, random choices from Seed, StepCap lines each),
	 * on a fresh story state each, and reports. Resets the runtime afterwards.
	 */
	FDinkSmokeReport RunSmoke(int32 Seed, int32 StepCap, const TArray<FString>* OnlyEntries = nullptr);

	// FTickableGameObject
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual bool IsTickable() const override { return bAutoTick && IsReady(); }
	virtual ETickableTickType GetTickableTickType() const override { return ETickableTickType::Conditional; }
	virtual bool IsTickableWhenPaused() const override { return false; }
	virtual bool IsTickableInEditor() const override { return false; }
	/**
	 * The game world: the story ticks inside UWorld::Tick with the world's game time (time dilation applied,
	 * nothing while the world is paused), in step with the pawn and the greybox. Without a world (headless
	 * tests) the engine ticks it with its own delta. (It used to return no world, so in PIE it ran on the
	 * editor's undilated real time: `slomo` sped the world up but not the scripts and brains.)
	 */
	virtual UWorld* GetTickableGameObjectWorld() const override { return GetWorld(); }

	/** Draws texts, menu and fade (bound to AHUD::OnHUDPostRender). */
	void DrawHUD(AHUD* HUD, UCanvas* Canvas);

private:
	friend class UDinkDirector;
	friend class UDinkGameplay;

	bool LoadStory(FString* OutError);
	void BindFacts();
	void HandleFactChanged(FName Fact, int32 OldValue, int32 NewValue);
	void HandleFactsReset();
	void HandleInkVariableChanged(const FString& Name, int32 Value);

	FDinkScriptInstance& CreateInstance(FName Script, int32 Sprite, int32 Screen);
	void BeginProcedure(FDinkScriptInstance& Instance, FName Procedure, const FString& Path, const TArray<int32>& Args);
	/** Registers the screen's live placements as sprites (map.dat type 1, not removed, current vision) and runs their `main`. */
	void EnterScreenPlacements(int32 Screen);
	/** PIE: tells the gameplay layer whether the player walks into something (push). */
	void UpdatePlayerPush();
	/** Swap the instance's locals and pseudo-variables into the story / back out. */
	void SwapIn(FDinkScriptInstance& Instance);
	void SwapOut(FDinkScriptInstance& Instance);
	/** Runs lines of one instance until it blocks, chooses, ends or hits MaxLines. Returns lines run. */
	int32 StepInstance(int32 InstanceId, int32 MaxLines);
	void HandleSpokenLine(FDinkScriptInstance& Instance, const FDinkStoryLine& Line);
	/** Unblocks instances whose wait is over. Returns true if any changed. */
	bool UpdateBlocks();
	void FinishInstance(FDinkScriptInstance& Instance, const TCHAR* Reason);
	void RemoveFinishedInstances();
	void OpenMenu(FDinkScriptInstance& Instance);
	void TakeInkErrors(const FDinkScriptInstance* Instance);
	int32 ResolveSpeaker(const FString& SpeakerTag) const;
	void PollScreenChange();

	FDinkInkStory Story;

	UPROPERTY()
	TObjectPtr<UDinkDirector> Director;

	UPROPERTY()
	TObjectPtr<UDinkGameplay> Gameplay;

	/** Fraction of a millisecond not yet passed on to the world-state clock. */
	double ClockCarryMs = 0.0;

	TWeakObjectPtr<UDinkFactSubsystem> Facts;
	TWeakObjectPtr<UDinkWorldStateSubsystem> WorldState;
	FDelegateHandle FactChangedHandle;
	FDelegateHandle FactsResetHandle;
	FDelegateHandle SaveCapturedHandle;
	FDelegateHandle SaveAppliedHandle;
	FDelegateHandle HudHandle;
	TSharedPtr<FDinkNarrativeInputProcessor> InputProcessor;

	/** Stable addresses: instances are only removed between steps (RemoveFinishedInstances). */
	TArray<TUniquePtr<FDinkScriptInstance>> Instances;
	TArray<FDinkActiveText> ActiveTexts;
	FDinkMenu Menu;
	/** Travel is asynchronous; never run startup scripts on the dying world. */
	bool HandlePendingRestart();
	bool bRestartRequested = false;
	bool bRestartAwaitingWorld = false;
	TWeakObjectPtr<UWorld> RestartSourceWorld;
	FString RestartMapName;

	int32 NextInstanceId = 1;
	int32 CurrentInstanceId = 0;
	double NowMs = 0.0;
	/** Guards against echoing a value back to where it came from. */
	bool bSyncingFacts = false;
	bool bAutoTick = false;
	int32 LastScreen = 0;
};
