#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "DinkOriginId.h"
#include "DinkNarrativeTypes.h"
#include "DinkDirector.generated.h"

class UDinkStorySubsystem;
class UDinkInventoryComponent;
class UDinkStatsComponent;
class ADinkScreenVolume;
class APlayerController;
class UCharacterMovementComponent;
struct FDinkScriptInstance;
struct FDinkScreenCorners;
class FDinkInkStory;

/** How far a director command is implemented (the generated status table). */
UENUM(BlueprintType)
enum class EDinkCommandStatus : uint8
{
	/** Acts on the greybox world / game state. */
	Implemented,
	/** Accepted and recorded (on the sprite as data, or logged) with a reason; never an error. */
	Recorded,
};

/**
 * One sprite handle of the scripts (the engine's spr[] index). 1 is Dink; others come from
 * sp(editor_num), create_sprite, the actor a script runs for, or text sprites. A handle may have no
 * actor (a "virtual" sprite: tests, the smoke run, background placements imported as instances, or
 * actors not loaded): its position and properties then live only here, and every command still works
 * on the record.
 */
struct DINKNARRATIVE_API FDinkSprite
{
	int32 Handle = 0;
	bool bActive = true;
	TWeakObjectPtr<AActor> Actor;
	/** Placement the sprite came from (invalid for spawned and text sprites). */
	FDinkOriginId Origin;
    // Transient original sp_index domain. Origin remains persistent source
    // identity; this index addresses the CURRENT screen's smallMap instead.
    int32 HardnessEditorIndex=0;
    bool bRetainedOriginalEditor=false;
    // Immutable original actor remains the provenance authority after a clone
    // deliberately loses its placement binding on a different/current screen.
    TWeakObjectPtr<AActor> HardnessSourceActor;
	/** Screen whose pixel space X/Y are in. */
	int32 Screen = 0;
	/** Script attached (sp_script / the placement's script); None after kill_this_task. */
	FName Script;
	/** Engine coordinates: x includes the 20 px status bar (map x = X - 20), y = map y. */
	double X = 0.0;
	double Y = 0.0;
	/** Numpad direction 1-9. */
	int32 Dir = 2;
	bool bFrozen = false;
	bool bSpawned = false;
	bool bText = false;
	/** Every sp_* value a script set, by property name without "sp_" (brain, seq, speed, ...). */
	TMap<FName, int32> Props;

	// Movement (move / move_stop)
	bool bMoving = false;
	/** move(.., nohard 1): the move ignores hardness, so it triggers no warp (D:15337 is reached from the hit test). */
	bool bMoveNoHard = false;
	int32 MoveDir = 0;
	int32 MoveStop = 0;
	double MoveElapsedMs = 0.0;
	/** Human pace (UDinkGameplay::PaceScale): the share of an engine frame's movement not yet taken. */
	double PaceCarry = 0.0;

	/** sp_kill(sprite, ms): removed at this time (0 = never). */
	double KillAtMs = 0.0;

	// Combat state of the engine's sprite (UDinkGameplay)
	/** hurt_thing's accumulated damage, applied by the sprite's brain on the next tick. */
	int32 Damage = 0;
	/** Sprite that dealt the last hit (add_exp pays only when this is 1). */
	int32 LastHit = 0;
	/** notouch / notouch_timer: no touch damage and no missile hits until the timer passes. */
	bool bNoTouch = false;
	double NoTouchUntilMs = 0.0;
	/** duck_brain: the duck lost its head (base 110); the next hit runs duckdie. */
	bool bHeadless = false;
	/**
	 * Set by the kill path of UDinkGameplay::ProcessDamage where the engine turns the sprite into the blood burst of
	 * sequence 164 (duck_brain's hit on a headless duck, D:12726-12740; pig_brain's kill, D:13370-13382). Presentation
	 * only (the class layer's burst reads it): never saved, never traced, and a sprite removed by sp_active 0 / sp_kill
	 * or a script's own handling does not have it, as the original shows no blood then.
	 */
	bool bBurstKill = false;

	// Brain state (UDinkGameplay::ThinkSprite; the engine's sprite fields of the same names). Script-visible
	// values (seq, frame, speed, timing, target, follow, distance, attack_wait, mx, my, base_*) live in Props.
	/** wait: next think when sp_timing > 0 (ThinkSprite's timer gate, D:16830). */
	double WaitMs = 0.0;
	/** move_wait: pill/people brains' next re-aim or wander decision. */
	double MoveWaitMs = 0.0;
	/** delay: when the animation shows its next frame. */
	double FrameDelayMs = 0.0;
	/** seq_orig: the sequence that last ended (walk cycles restart from it). */
	int32 SeqOrig = 0;
	/** people_brain's action: 0 decide, 1 sit and think, 2 walk (find_action, D:13046). */
	int32 Action = 0;
	/** 3D adaptation layer: telegraphed wind-up before an attack (UDinkGameplay::Adaptation). */
	bool bWindingUp = false;
	double WindUpUntilMs = 0.0;
	int32 WindUpDir = 0;

	int32 GetProp(FName Name, int32 Default = 0) const { const int32* V = Props.Find(Name); return V ? *V : Default; }
};

/** What a command asks of the script instance that ran it. */
struct DINKNARRATIVE_API FDinkCommandResult
{
	/** 0 = continue; otherwise an EDinkBlock value (see DinkStorySubsystem.h). */
	uint8 Block = 0;
	double BlockUntilMs = 0.0;
	int32 BlockRef = 0;
	/** kill_this_task and friends: end the instance. */
	bool bEndScript = false;
	/** The engine's "leave script" (process_line returning 2, e.g. kill_cur_item): the procedure stops, the instance stays. */
	bool bStopProcedure = false;
};

/** Arguments of one command line, plus who runs it. */
struct DINKNARRATIVE_API FDinkCommandContext
{
	FDinkScriptInstance& Instance;
	const FDinkStoryLine& Line;
	FName Name;

	int32 Int(int32 Index, int32 Default = 0) const { return Line.ArgInt(Index, Default); }
	FString Str(int32 Index) const { return Line.ArgString(Index); }
	int32 Num() const { return Line.Args.Num(); }
};

using FDinkCommandHandler = TFunction<FDinkCommandResult(FDinkCommandContext&)>;

struct DINKNARRATIVE_API FDinkCommandDef
{
	FName Name;
	EDinkCommandStatus Status = EDinkCommandStatus::Recorded;
	/** What it does here, or why it is only recorded. */
	FString Note;
	FDinkCommandHandler Handler;
};

/** Stand-in for the audio layer: logs and remembers every cue (there is no audio yet). */
struct DINKNARRATIVE_API FDinkAudioStub
{
	/** "music:5.mid", "music:stop", "sound:22", "sound:22 loop sprite 7", "cd:stop". */
	TArray<FString> Cues;
	FString CurrentMusic;
	TFunction<void(const FString&)> Playback;
	void Cue(const FString& Cue);
};

/**
 * Executes the story's director command lines (`>> name args #cmd`) against the world: the
 * command registry (every command of director_vocabulary.csv is either implemented or recorded with a
 * reason; an unknown name is a logged error), the sprite handle table, the EXTERNAL functions the story
 * calls, movement, fades and the audio stub. Owned by UDinkStorySubsystem.
 *
 * Coordinates: scripts use the original's screen pixels (x with the 20 px status bar). The director
 * converts them through the sprite's screen corners with DinkLayout (the transform the greybox
 * importer uses), so a `move_stop(&current_sprite, 2, 160, 1)` walks the placement actor south on its
 * screen until map y 160.
 */
UCLASS()
class DINKNARRATIVE_API UDinkDirector : public UObject
{
	GENERATED_BODY()

public:
	void Init(UDinkStorySubsystem* InStory);
	virtual UWorld* GetWorld() const override;

	/** Runs one command line for Instance. Unknown commands are logged as errors and skipped. */
	FDinkCommandResult Execute(FDinkScriptInstance& Instance, const FDinkStoryLine& Line);

	bool IsKnownCommand(FName Name) const { return Commands.Contains(Name); }
	const TMap<FName, FDinkCommandDef>& GetCommands() const { return Commands; }

	/** Binds the 27 EXTERNAL functions of _decls.ink to the story (lookaheadSafe = false). */
	void BindExternals(FDinkInkStory& Story);
	/** Names of the externals bound. */
	const TArray<FString>& GetExternalNames() const { return ExternalNames; }

	/**
	 * The command status table for every row of director_vocabulary.csv (command, category, usage,
	 * status, note) plus spoken lines, fact writes and externals. CSV text.
	 */
	FString BuildStatusTable(const FString& VocabularyCsv, int32* OutImplemented = nullptr, int32* OutRecorded = nullptr, int32* OutMissing = nullptr) const;

	// ---- Handle table ----

	FDinkSprite* FindSprite(int32 Handle);
	const FDinkSprite* FindSprite(int32 Handle) const;
	/** Handle of an actor (allocated on first use; actors with an origin keep one handle per origin). */
	int32 HandleForActor(AActor* Actor);
	/** sp(editor_num): handle of placement Placement on Screen; 0 if it was removed (editor_type). */
	int32 HandleForPlacement(int32 Screen, int32 Placement);
	/** add_sprite's defaults on a script-made sprite (speed 1, timing 33, size 100, base_* 0, dir 0). */
	static void InitCreatedSprite(FDinkSprite& Sprite);
	/** add_sprite_dumb's defaults (D:3089-3135), which create_sprite uses (D:9041-9051): speed 0, timing 0, size 100, hard 1, base_* -1, dir 0. */
	static void InitDumbSprite(FDinkSprite& Sprite);
	/** set_dink_speed's walk speed (D:17311-17321) over main.c's default 3: 4 for 1, 2 for 2, 1 for 3, 1/3 above, 0 for <= 0. */
	static float DinkSpeedScale(int32 DinkSpeed);
	/** A new virtual sprite (no actor) at engine pixel X/Y on Screen. */
	int32 CreateVirtualSprite(int32 Screen, double X, double Y);
	/** Smallest free handle >= 2 (the engine's add_sprite picks the first free slot). */
	int32 AllocateHandle();
	AActor* GetActor(int32 Handle) const;
	/** Dink (handle 1): binds the first local player's pawn when there is one. */
	FDinkSprite& GetDink();
	/**
	 * Removes the sprite (sp_active 0): hides its actor (destroys spawned ones) and ends its scripts.
	 * bEndScripts false is the engine's `active = false` of a dying or vanishing sprite (its running
	 * die/touch script carries on).
	 */
	void DeactivateSprite(int32 Handle, int32 ExceptInstanceId, bool bEndScripts = true);
	/** Frees handles of sprites that belong to another screen (screen change). Dink, 1000-attached and spawned sprites of live instances stay. */
	void ReleaseScreenSprites(int32 KeepScreen, const TSet<int32>& KeepHandles);
    bool CarryOriginalLiveSprites(int32 Screen,FString& Error);
	const TMap<int32, FDinkSprite>& GetSprites() const { return Sprites; }
	void ResetSprites();
	/** Counts ResetSprites calls: presentation layers that remember sprites by handle (a restored save reuses the handles on the same screen) drop what they hold when it moves. Not simulation state. */
	int32 GetSpriteResetSerial() const { return SpriteResetSerial; }

	/** Generic sp_<prop>(sprite, value): value -1 reads only. Returns the current value. */
	int32 SpriteProperty(FDinkScriptInstance* Instance, FName Prop, int32 Handle, int32 Value);

	// ---- Movement and time ----

	/** Advances movement, sp_kill timers and fades. */
	/** bGameStopped (stop_entire_game): kill timers still run (D:16811-16833, before the get_frame branch), moves do not (they run in the brain). */
	void Tick(double DeltaMs, double NowMs, bool bGameStopped = false);
	bool IsMoving(int32 Handle) const;
	/** move / move_stop: walks the sprite in numpad direction Dir until x (or y for 2/8) passes Stop. */
	void StartMove(FDinkSprite& Sprite, int32 Dir, int32 Stop, int32 NoHard = 0);
	/** Optional scale (0..1] on a sprite's scripted move speed; set by the gameplay layer (human pace of NPCs). */
	TFunction<double(const FDinkSprite&)> MovePaceScale;
	/** kill_game: when set, called instead of quitting the application (tests). */
	TFunction<void()> OnKillGame;
	/** True while a script carries Dink with a move that ignores hardness (warps must not fire then). */
	bool IsDinkCarriedThroughHardness() const { const FDinkSprite* D = Sprites.Find(1); return D && D->bMoving && D->bMoveNoHard; }
	/**
	 * A script is putting Dink somewhere (load_screen): the warps his new place overlaps must not fire. The original warps only from the walk code's
	 * hardness hit (special_block, dink.cpp:15337); sp_x / sp_y / load_screen never run it (s3-sec1.c:40-42 puts Dink at 515,383 of SCR_227, inside
	 * the hut's exit, and he stays). True only during that placement.
	 */
	bool IsDinkPlacedByScript() const { return bPlacingDink; }
	/** Instant mode: finish every move now. */
	void FinishAllMoves();
	/**
	 * The player controller's move input (SetIgnoreMoveInput is a counter) is held by this layer in ONE place, for two reasons: Dink is
	 * frozen (freeze(1)), or the hardness loading gate is closed (UDinkGameplay::IsHardnessLoading). This recomputes the hold from those
	 * reasons now: it takes one count when a reason holds and none is taken, gives it back when no reason holds any more, and moves it when
	 * the controller changed. The controller it was taken on is remembered, so a reset, a load or a lost pawn link can never strand it.
	 */
	void UpdatePlayerMoveHold();
	/** Whether UpdatePlayerMoveHold currently holds a controller's move input. */
	bool HoldsPlayerMoveInput() const { return MoveHoldController.IsValid(); }
	/**
	 * 1997 load_map clears Dink's freeze on every screen load (dink.cpp:1013-1015): walking off an edge (14071-14151), a warp (15724) and
	 * a script's load_screen (7874-7878). load_screen does it at once (the script may freeze him again before the screen is entered);
	 * this tells OnScreenEntered that the screen it enters was loaded that way, so it does not clear a freeze the script took afterwards.
	 */
	bool ConsumeScriptLoadedScreen(int32 Screen) { const bool b = ScriptLoadedScreen == Screen; ScriptLoadedScreen = INDEX_NONE; return b; }
	/**
	 * What load_map does to Dink (dink.cpp:1013-1015): his scripted move stops (move_active, move_nohard false; a move_stop waiting
	 * on it goes on) and his freeze is cleared. Returns true if anything changed.
	 */
	bool ApplyLoadMapToDink(int32 FreezeSerialLimit = MAX_int32, int32 MoveSerialLimit = MAX_int32);
	/**
	 * Grow by one with every new freeze of Dink and every scripted move of Dink. The greybox notices a new screen up to about 0.25 s
	 * after the pawn crossed into it; a freeze or move started after the crossing (escape.c's freeze(1) on Esc, the death script, a
	 * spell) is not one load_map would have cleared, so the screen entry passes the serials seen at the crossing as limits.
	 */
	int32 GetDinkFreezeSerial() const { return DinkFreezeSerial; }
	int32 GetDinkMoveSerial() const { return DinkMoveSerial; }

	/** Moves the actor of a sprite to its X/Y (keeps the actor's height). */
	void SyncActorToSprite(FDinkSprite& Sprite);
	/** Reads the sprite's X/Y from its actor. */
	void SyncSpriteFromActor(FDinkSprite& Sprite);
	/** Corners of an original screen in the loaded world, if that screen volume exists. */
	bool GetScreenCorners(int32 Screen, FDinkScreenCorners& OutCorners) const;
	/** Same next-facing rotation for presentation and authored body collision queries. */
	bool GetSpriteFacingRotation(const FDinkSprite& Sprite, FQuat& OutRotation) const;
	/** World location (cm) of engine pixel X/Y on Screen, if the screen is loaded. */
	bool PixelToWorld(int32 Screen, double X, double Y, FVector& OutWorld) const;
	/** Screen the player stands on (greybox), else &player_map. */
	int32 GetCurrentScreen() const;
	/** Screen volume containing a world location (the greybox's current screen lags a teleport); else GetCurrentScreen(). */
	int32 ScreenAt(const FVector& Location) const;
	/** Numpad direction (1-9) on Screen's pixel grid of a world-space direction at Location; 0 if unknown. */
	int32 DirFromWorld(int32 Screen, const FVector& Location, const FVector& Direction) const;
	/** Numpad direction of a pixel-space vector (y grows south). 0 for a zero vector. */
	static int32 DirFromPixelDelta(double Dx, double Dy);
	/**
	 * The original's &savegameinfo line for a save slot (dink.cpp:4093-4106): "Slot N - H:MM - <save info>" for a used slot, where H:MM is
	 * the play time the save holds (g_playerInfo.minutes, dink.cpp:1054) and the base game's save info is "Level &level" (dink.cpp:17729,
	 * deciphered when saved, 1066-1069); "Slot N - Empty" when Save is null. Play time here is the story clock the save carries.
	 */
	static FString SaveGameInfo(int32 Slot, const class UDinkSaveGame* Save);

	// ---- Fade ----
	/** 0 = clear, 1 = black. */
	float FadeAlpha = 0.f;
	float FadeTarget = 0.f;
	/** Duration of fade_down / fade_up. Assumed, not measured from the original. */
	static constexpr double FadeDurationMs = 600.0;

	// ---- Other state the world layers will read ----
	/** screenlock (UDinkGameplay::SetScreenLock keeps it and the greybox barriers in step). */
	bool bScreenLocked = false;
	/** dink.ini lines scripts ran with init() (sequence redefinitions), in order, for the animation layer. */
	TArray<FString> InitLines;
	bool bDinkCanWalkOffScreen = false;
	/** stop_entire_game(1) (D:10099-10108): no sprite thinks or animates while a menu is up; cleared on the first frame without one (D:17431-17440). */
	bool bStopEntireGame = false;
	/** load_screen is moving the pawn (IsDinkPlacedByScript). */
	bool bPlacingDink = false;
	FDinkAudioStub Audio;

	/** Inventory for scripts when the player has no UDinkInventoryComponent (tests, smoke run). */
	UDinkInventoryComponent* GetInventory();
	UDinkStatsComponent* GetPlayerStats() const;

	/** JSON object of the handle table and director state (save). */
	TSharedPtr<class FJsonObject> SaveState() const;
	void LoadState(const TSharedPtr<class FJsonObject>& State);

	/** Monotonic counter for sp_* writes etc. (tests). */
	int32 CommandsRun = 0;
	TMap<FName, int32> CommandCounts;

	/** Engine sprite numbers above this are the engine's "1000 = no sprite / screen" conventions. */
	static constexpr int32 HandleNoSprite = 1000;

private:
	friend class UDinkStorySubsystem;
	friend class UDinkGameplay;
	friend class FDinkFreezeReleaseTest; // Dink.Input.FreezeReleasedByReset drives SetFrozen with a real controller
	friend class FDinkMoveHoldTest; // Dink.Input.MoveHoldFollowsItsReasons
	friend class FDinkFreezeFallbackGravityTest; // Dink.Input.ResetRestoresGravityWithoutPawnLink
	friend class FDinkScreenLoadUnfreezeTest; // Dink.Input.ScreenLoadClearsFreeze
	friend class FDinkScriptlessEntryOpensGateTest; // Dink.Input.ScriptlessScreenEntryOpensHardnessGate
	void RegisterCommands();
	void Register(const TCHAR* Name, EDinkCommandStatus Status, const TCHAR* Note, FDinkCommandHandler Handler);
	/** Registers sp_<Prop> as a recorded property (stored on the sprite for the animation/AI layers). */
	void RegisterRecordedProp(const TCHAR* Prop, const TCHAR* Note);
	FDinkCommandResult RecordOnly(FDinkCommandContext& Ctx);
	bool StepMove(FDinkSprite& Sprite, double DeltaMs);
	void ApplyDir(FDinkSprite& Sprite, const FQuat* ValidatedAuthoredFacing = nullptr);
	void SetFrozen(int32 Handle, bool bFrozen);
	AActor* SpawnSpriteActor(FDinkSprite& Sprite);
	AActor* FindPlacementActor(const FDinkOriginId& Origin);
	void BuildOriginIndex();
	int32 InstanceScreen(const FDinkScriptInstance& Instance) const;
	ADinkScreenVolume* FindScreenVolume(int32 Screen) const;

	UPROPERTY()
	TObjectPtr<UDinkStorySubsystem> Story;

	UPROPERTY()
	TObjectPtr<UDinkInventoryComponent> FallbackInventory;

	TMap<FName, FDinkCommandDef> Commands;
	TArray<FString> ExternalNames;
	TMap<int32, FDinkSprite> Sprites;
	/** Per created sprite, the picture (seq, pseq, pframe, size, brain, brain_parm) its presentation was last made for:
	 * Tick presents it again when walking (changedir), a brain or a script changed the picture by any path. */
	TMap<int32, uint32> PresentedPicture;
	TMap<FDinkOriginId, int32> HandleByOrigin;
	TMap<TWeakObjectPtr<AActor>, int32> HandleByActor;
	TMap<FDinkOriginId, TWeakObjectPtr<AActor>> OriginIndex;
	TWeakObjectPtr<UWorld> OriginIndexWorld;
	/** The controller whose move input UpdatePlayerMoveHold holds (one count), null when none is held. */
	TWeakObjectPtr<APlayerController> MoveHoldController;
	/** The movement component whose gravity a freeze took away (see SetFrozen), and its scale before; null when none is taken. */
	TWeakObjectPtr<UCharacterMovementComponent> GravityHeldMovement;
	float DinkGravityScale = 1.f;
	/** The screen a script's load_screen loaded (see ConsumeScriptLoadedScreen). */
	int32 ScriptLoadedScreen = INDEX_NONE;
	/** Dink's controller: his pawn's, else the world's first local player's. */
	APlayerController* FindPlayerController() const;
	/** Gives back the gravity a freeze took (on the component it was taken from, even when Dink's record or pawn link is gone). */
	void RestoreDinkGravity();
	/** Gravity follows the hold: taken from Dink's current pawn while he is frozen and his controller is held, else given back. */
	void SyncDinkGravity();
	int32 DinkFreezeSerial = 0;
	int32 DinkMoveSerial = 0;

public:
	/** See GetSpriteResetSerial. */
	int32 SpriteResetSerial = 0;
};
