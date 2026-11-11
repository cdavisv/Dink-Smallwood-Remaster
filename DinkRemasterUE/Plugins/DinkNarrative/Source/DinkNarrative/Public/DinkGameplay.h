#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "DinkOriginId.h"
#include "DinkRandom.h"
#include <vector>
#include <array>
#include "DinkGameplay.generated.h"

class APlayerController;
class UPrimitiveComponent;
class UDinkStorySubsystem;
struct FDinkRuntimeHardnessState;
struct FDinkHardnessProjection;
struct FDinkOriginalSlotHistory;
struct FDinkHardnessFitSet;
namespace DinkHardness { struct PhysicsOwner; struct Stamp; }
class UDinkDirector;
class FJsonObject;
struct FDinkSprite;

/** One frame of dink.ini (Content/Dink/Data/Gameplay/frames.csv). */
struct DINKNARRATIVE_API FDinkFrameInfo
{
	int32 DelayMs = 0;
	/** set_frame_special: the frame on which an attack animation hits (dink.cpp D:16971). */
	bool bSpecial = false;
	/** Hardbox relative to the sprite position (engine pixels). */
	int32 Left = 0;
	int32 Top = 0;
	int32 Right = 0;
	int32 Bottom = 0;
	/** SET_FRAME_FRAME <seq> <frame> -1: the animation wraps to frame 1 here (frame[] == -1, D:16996). */
	bool bLoop = false;
	/** A slot without a picture: the animation ends here (frame[] < 1, D:17010). */
	bool bEmpty = false;
	/** The picture's size (getpic()'s box: right = Width, bottom = Height). */
	int32 Width = 0;
	int32 Height = 0;
};

/**
 * One screen's hardness map as the engine builds it on load (g_hitmap: tile hardness, then the hardboxes of
 * placements with hard == 0 as 100 + placement index), from Content/Dink/Data/Gameplay/Hardness/SCR_nnn.txt.
 * Codes: 0 free, 1 solid, 2 low (missiles and flyers cross), 3 other, 100+n sprite hardbox of placement n.
 * The file's last block ("tiles", Vision TileLayerVision) is the tile layer alone (fill_whole_hard, D:654).
 */
struct DINKNARRATIVE_API FDinkHardnessMap
{
	static constexpr int32 Width = 600;
	static constexpr int32 Height = 400;
	/** Vision value of the "tiles" block: the tile layer without placements (fill_whole_hard, dink.cpp:654-681). */
	static constexpr int32 TileLayerVision = -1;
	int32 Screen = 0;
	int32 Vision = 0;
	TArray<uint8> Codes;

	/** Blocks a walker in the screen's solid collision (codes 1, 3 and every hardbox); 2 (low) and 0 do not. */
	static bool IsSolidCode(int32 Code) { return Code != 0 && Code != 2; }

	/** get_hard (D:527): map pixel (engine x - 20, y); 0 outside the 600x400 map. */
	int32 Get(int32 MapX, int32 MapY) const
	{
		return MapX < 0 || MapY < 0 || MapX >= Width || MapY >= Height || Codes.Num() != Width * Height ? 0 : Codes[MapY * Width + MapX];
	}
	void Set(int32 MapX, int32 MapY, uint8 Code)
	{
		if (Codes.Num() != Width * Height) { Codes.SetNumZeroed(Width * Height); }
		if (MapX >= 0 && MapY >= 0 && MapX < Width && MapY < Height) { Codes[MapY * Width + MapX] = Code; }
	}
	/** Parses one vision block of the text format (see Scripts/sync_gameplay_data.py). */
	static TMap<int32, TSharedPtr<FDinkHardnessMap>> ParseFile(int32 Screen, const FString& Text);
};

/**
 * The 3D adaptation layer over the Classic brains (REMASTER_PLAN section 2 "AI": short attack wind-ups,
 * at most two attackers at once). Numbers come from Content/Dink/Data/AI/adaptation.ini; play reads the
 * file (Enabled=1 there), parity tests switch it off. Off = the original's rules exactly.
 */
struct DINKNARRATIVE_API FDinkAdaptationSettings
{
	bool bEnabled = false;
	/** Telegraph: the attacker stops, faces its target and waits this long before its attack starts. */
	double WindUpMs = 450.0;
	/** Sprites that may be winding up or attacking the same target at once; the others hold position. */
	int32 MaxAttackers = 2;
	/** Hold behaviour of a capped attacker: 0 stand still facing the target, 1 also re-aim every HoldReaimMs. */
	double HoldReaimMs = 400.0;
	FString Source;
	/** Reads the ini (missing file: defaults, disabled). */
	bool Load(const FString& Path, FString* OutError = nullptr);
	static FString DefaultPath();
};

/** Physical reach for authored geometry; independent of each region's legacy pixel scale. */
struct DINKNARRATIVE_API FDinkAuthoredInteractionSettings
{
	double AttackReachCm = 85.0;
	double AttackHalfWidthCm = 18.0;
	double TalkReachCm = 150.0;
	double TalkHalfWidthCm = 50.0;
	double PickupReachCm = 30.0;
	double ElevatedPickupReachCm = 85.0;
	double ElevatedPickupMinHeightCm = 45.0;
	double PickupShoulderHeightCm = 140.0;
	double ContactReachCm = 5.0;
	static FString DefaultPath();
	void Load();
};

/** One map.dat placement (Content/Dink/Data/Gameplay/placements.csv). */
struct DINKNARRATIVE_API FDinkPlacementInfo
{
	FDinkOriginId Origin;
	/** 0 background, 1 live sprite, 2 hardness only. Only type 1 becomes a sprite with a script (place_sprites_game). */
	int32 Type = 0;
	/** Engine x (map x + the 20 px status bar) and y. */
	int32 X = 0;
	int32 Y = 0;
	int32 Seq = 0;
	int32 Frame = 0;
	int32 Size = 100;
	int32 Vision = 0;
	int32 Brain = 0;
	FName Script;
	int32 Hitpoints = 0;
	int32 Strength = 0;
	int32 Defense = 0;
	int32 Exp = 0;
	int32 NoHit = 0;
	int32 TouchDamage = 0;
	int32 Speed = 0;
	int32 Timing = 0;
	int32 BaseWalk = -1;
	int32 BaseIdle = -1;
	int32 BaseAttack = -1;
	int32 BaseHit = 0;
	int32 BaseDie = -1;
	/** map.dat's hard flag, inverted: 0 = the hardbox is stamped into the hardness (D:6136), 1 = none. */
	int32 Hard = 0;
	int32 Sound = 0;
	int32 Que = 0;
	bool bHasQueSource = false;
	/**
	 * map.dat's prop flag (g_smallMap.sprite[n].prop): get_hard reads this placement's stamped hardbox as 0 when it is not 0 (walk-through,
	 * dink.cpp:569-575) and special_block warps Dink to WarpMap when it is 1 (D:15337-15341). 1 on the 93 sprite warps, 0 elsewhere.
	 */
	int32 Prop = 0;
	/** map.dat's warp_map: the screen special_block sends Dink to (process_warp_man D:15718); 0 for none. */
	int32 WarpMap = 0;
};

/** The original's per-frame and per-placement data (Scripts/sync_gameplay_data.py; never hand-edited). */
class DINKNARRATIVE_API FDinkGameplayData
{
public:
	/** Loads frames.csv and placements.csv from Content/Dink/Data/Gameplay. */
	bool Load(FString* OutError = nullptr);
	bool IsLoaded() const { return Frames.Num() > 0 && Placements.Num() > 0; }
	static FString GetDataPath(const TCHAR* File);

	const FDinkFrameInfo* FindFrame(int32 Seq, int32 Frame) const;
	/** g_seq[Seq].active: dink.ini defines the sequence. */
	bool SeqExists(int32 Seq) const { return Seq > 0 && FrameCounts.Contains(Seq); }
	/** g_seq[Seq].frame[Frame] as the animator reads it: 1 a picture, 0 end of the animation, -1 wrap to frame 1. */
	int32 FrameCode(int32 Seq, int32 Frame) const;
	/** Delay of a frame (dink.ini set_frame_delay or the sequence default), ms. */
	int32 FrameDelay(int32 Seq, int32 Frame) const;
	/** The screen's hardness for a &vision value (falls back to vision 0); null if the screen has no data. Loaded on first use. */
	const FDinkHardnessMap* GetHardness(int32 Screen, int32 Vision) const;
	/** Tests: replace a screen's hardness (all visions). Null removes the override. */
	void SetHardnessOverride(int32 Screen, TSharedPtr<FDinkHardnessMap> Map);
	/** The screen's tile layer (get_hard_map, D:582: what fill_hardxy and fill_whole_hard copy back); null without data or with a test override. */
	const FDinkHardnessMap* GetTileHardness(int32 Screen) const;
    const std::array<int,100>* GetEditorHardFlags(int32 Screen) const;
	/**
	 * A sequence a script's init("load_sequence_now ...") defines that dink.ini does not (s7-mil.c:13: Seth's pose 580): its hardbox, for every
	 * frame (figure_out, dink.cpp:2335-2344: a sequence not yet active is read from the line, ReadFromLoadSequenceString 2216-2226, and every
	 * frame gets the line's hardbox, LoadSpriteSingleFrame 1899-1922). Only the hardbox is known here (no pictures, no frame count).
	 */
	void AddInitSequence(int32 Seq, const FDinkFrameInfo& Box) { InitSequences.Add(Seq, Box); }
	const FDinkFrameInfo* FindInitSequence(int32 Seq) const { return InitSequences.Find(Seq); }
	/** Time from the start of Seq until its first special (hit) frame shows; INDEX_NONE if it has none. */
	int32 HitFrameDelayMs(int32 Seq) const;
	const FDinkPlacementInfo* FindPlacement(const FDinkOriginId& Origin) const;
	/** Placements of a screen in placement order. */
	TArray<const FDinkPlacementInfo*> GetPlacementsOnScreen(int32 Screen) const;
	/** The screen's base script (map.dat), None if it has none. */
	FName GetBaseScript(int32 Screen) const { return BaseScripts.FindRef(Screen); }

	int32 NumFrames() const { return Frames.Num(); }
	int32 NumPlacements() const { return Placements.Num(); }

private:
    friend class FDinkHardnessRetainedLegacyOwner;
    mutable TMap<int32,std::array<int,100>> EditorHardFlags;
	static int64 Key(int32 Seq, int32 Frame) { return static_cast<int64>(Seq) * 1000 + Frame; }
	TMap<int64, FDinkFrameInfo> Frames;
	TMap<int32, int32> FrameCounts;
	TMap<FDinkOriginId, FDinkPlacementInfo> Placements;
	TMap<int32, TArray<FDinkOriginId>> ByScreen;
	TMap<int32, FName> BaseScripts;
	TMap<int32, FDinkFrameInfo> InitSequences;
	/** Screen -> vision -> map (lazy; the files are ~9 KB each). */
	mutable TMap<int32, TMap<int32, TSharedPtr<FDinkHardnessMap>>> Hardness;
	TMap<int32, TSharedPtr<FDinkHardnessMap>> HardnessOverrides;
};

/** A melee hit waiting for its attack animation's special frame. */
struct DINKNARRATIVE_API FDinkPendingHit
{
	int32 Sprite = 0;
	int32 Seq = 0;
	double AtMs = 0.0;
};

/**
 * The bow being drawn: the engine's attackinfo_struct g_dglos.g_bowStatus (dink.h:367-376), set by the DinkC command
 * activate_bow (dink.cpp:9397-9408), charged and released by process_bow (dink.cpp:14564-14621) from Dink's brain while it is
 * active (dink.cpp:14761-14766), `hitme` set by the 100 ms status timer (dink.cpp:17339-17344).
 */
struct DINKNARRATIVE_API FDinkBowStatus
{
	/** g_bowStatus.active: the bow is drawn; Dink's brain does nothing else (no walking, attack, magic or talk keys). */
	bool bActive = false;
	/** g_bowStatus.script: the script instance blocked in activate_bow (the item's `use`), run on at the release. */
	int32 Instance = 0;
	/** g_bowStatus.hitme: false until the first 100 ms status tick after activate_bow; the pull adds nothing before it. */
	bool bHitMe = false;
	/** g_bowStatus.time: the draw, 0..500 (7 per pull tick). */
	int32 Time = 0;
	/** g_bowStatus.last_power: the draw at the last release (get_last_bow_power). */
	int32 LastPower = 0;
	/** g_bowStatus.pull_wait: engine ms of the next pull (every 10 ms, i.e. every 60 Hz frame). */
	double PullWaitMs = 0.0;
};

/**
 * The original engine's gameplay rules that decide WHEN a script procedure runs, ported from
 * source/dink/dink.cpp onto the director's sprite records (engine pixel space, so they work the same
 * for greybox actors and for virtual sprites in headless tests):
 *
 *  - hit:   run_through_tag_list (D:15460-15596), when an attack animation reaches its special frame;
 *           every live sprite whose hardbox (+5/+5/+5/+10) holds the attacker's position after the
 *           28 px (or sp_range) forward reach; melee damage = DinkRules::ResolveMeleeHit; sets
 *           &missle_source, &enemy_sprite, last_hit and runs `hit`.
 *  - touch: run_through_touch_damage_list (D:15629-15680) for Dink every tick: touch_damage -1 only
 *           runs `touch` (again every tick until the script clears it), > 0 hurts Dink (defense rule)
 *           with 400 ms immunity and runs `touch`.
 *  - push:  walking into hardness in a cardinal direction for 600 ms (D:13526, 14768), then `push`
 *           of scripted sprites whose hardbox +2 holds Dink (run_through_tag_list_push, D:15600).
 *  - damage and death: hurt_thing (D:6656) accumulates damage; each tick the sprite's brain applies it
 *           (pill_brain 9, dragon_brain 10, people_brain 16: hitpoints, `die`, corpse, exp through
 *           add_exp only when Dink dealt the last hit; duck_brain 3: `die` then `duckdie`;
 *           pig_brain 4); Dink loses &life.
 *  - status (every 100 ms while &update_status is 1, D:5836-5963): spell charge, level-up (lraise
 *           `raise`), Dink's death (dinfo `die`).
 *  - items and magic: arm_weapon / add_item / kill_cur_item ... run the item scripts' arm, disarm,
 *           pickup, use, holdingdrop and drop procedures (D:1480-1600, 6915-6955, 7850-7870, 14819, 14941).
 *  - brains (ThinkSprite, D:16790-16880, in DinkBrains.cpp): every non-Dink sprite thinks at the engine's
 *           60 Hz step, gated by sp_timing, and runs its brain: 0 none (follow), 2 bounce, 3 duck, 4 pig,
 *           5/6/7 play once / repeat / play once and vanish, 9 monster (diagonal wander, chase sp_target,
 *           melee with base_attack), 10 dragon (cardinal wander, script ATTACK), 11/17 missile (hardness:
 *           walls stop it, low hardness 2 lets flyers pass, sprite hardboxes run `hit`/`damage`),
 *           12 scale and vanish, 15 shadow, 16 people (sit / walk). Movement is in screen pixels against
 *           the screen's hardness map; the animator advances seq/frame from dink.ini and lands a melee hit on
 *           a special frame (run_through_tag_list). Scripted move/move_stop (the director) take priority.
 *  - the 3D adaptation layer (Adaptation, off unless enabled): telegraphed wind-up, attacker cap.
 *
 * One seedable random source stands in for the C library's rand(): DinkC random(), the combat rolls and
 * set_callback_random draw from it in call order.
 */
UCLASS()
class DINKNARRATIVE_API UDinkGameplay : public UObject
{
	GENERATED_BODY()

public:
	void Init(UDinkStorySubsystem* InStory);
	const FDinkGameplayData& GetData() const { return Data; }
	bool HasData() const { return Data.IsLoaded(); }

    // Explicit staged-world admission only; legacy aggregate collision is never toggled here.
    // Observes original birth/rank phases without changing UE script handles.
    void ResetOriginalSlotHistory();
    void BeginOriginalIdentityScreen(int32 Screen);
    void PrepareLegacyOriginalIdentity(int32 Screen);
    void BindLegacyOriginalIdentity(const FDinkOriginId& Origin,int32 Handle);
    void RebuildOriginalIdentityFromActualSprites();
    bool HasSelectedOriginalHardness() const;
    bool HasOriginalIdentityOnScreen(int32 Screen) const;
    bool BeginOriginalHardnessScreen(int32 Screen, FString& Error, int32 InitialVision=0);
    void RestartOriginalSavedRuntime();
    void FinishLegacyHardnessLoad(int32 Screen) { if(!RequiresOriginalHardnessScreen(Screen))SetHardnessLoading(false); }
    void GateOriginalHardnessTransition() { SetHardnessLoading(true); }
    bool IsHardnessLoading() const { return bHardnessLoading; }
    bool UsesOriginalHardnessProjection(int32 Screen) const;
    bool RequiresOriginalHardnessScreen(int32 Screen) const;
    FDinkOriginId OriginalHardnessOwnerOrigin(const FDinkSprite& Sprite) const;
    bool ValidateOriginalEditorCarry(int32 Screen,int32 Vision,FString& Error) const;
    bool OriginalEditorHardFlag(int32 Screen,int32 Index,int32& Hard) const;
    void ApplyOriginalHardnessVision(int32 Screen,int32 Vision,bool bBackgroundOnly);
    bool PrepareOriginalHardnessPlacements(int32 Screen, FString& Error);
    TArray<int32> OriginalHardnessPlacementOrder(int32 Screen) const;
    void BindOriginalHardnessPlacement(const FDinkOriginId& Origin, int32 Handle);
    bool FinishOriginalHardnessPlacements(int32 Screen, FString& Error);
    int32 EffectiveHardnessPlacementType(const FDinkPlacementInfo& Placement) const;
    void RecordOriginalHardnessBirth(int32 Handle);
    void RecordOriginalHardnessRelease(int32 Handle);
    void RecordOriginalHardnessReactivation(int32 Handle);
    void OriginalHardnessVisionChanged(int32 Vision);
    bool AdmitRuntimeHardness(int32 Screen, int32 Vision, TSharedPtr<DinkHardness::PhysicsOwner> Owner, FString& Error);
    bool GetDisplayedHardnessBox(const FDinkSprite& Sprite, int32& L, int32& T, int32& R, int32& B) const;
    bool RedrawRuntimeHardness(int32 Handle, FString& Error);
    bool RedrawRuntimeHardnessMap(int32 Screen,FString& Error);
    void InvalidateRuntimeHardnessForScreenLoad(bool bResetTransientEditorHard=true);
    /** Release owned world bodies/caches on GI shutdown; never rebuild or admit. */
    void ShutdownRuntimeHardness();
    void RecordEditorHardness(const FDinkOriginId& Origin, int32 Value);
    int32 EditorHardnessPicture(const FDinkOriginId& Origin, bool bSequence, int32 Value);
    bool TryRuntimeHardnessCode(int32 Screen, int32 Vision, int32 MapX, int32 MapY, int32& Code) const;


	// ---- Random ----

	/** Reseeds the default stream (and drops an injected source). */
	void SetRandomSeed(int32 Seed);
	/** Injects a source (tests: FDinkScriptedRandomSource); null restores the seeded stream. */
	void SetRandomSource(TSharedPtr<IDinkRandomSource> Source);
	IDinkRandomSource& Rng();
	/** DinkC random(range, base): (rand() % range) + base; base when range is 0 (dink.cpp "random"). */
	int32 Random(int32 Range, int32 Base);
	/** rand() % N for engine-internal draws (set_callback_random timers). */
	int32 RandomModulo(int32 N) { return N > 0 ? Rng().RandomModulo(N) : 0; }

	// ---- Sprite data ----

	/** Copies map.dat's live-sprite fields onto a placement sprite (place_sprites_game, D:6080-6110). */
	void InitPlacementSprite(FDinkSprite& Sprite) const;
	/**
	 * The DinkC init("load_sequence_now <file> <seq> <speed> <x> <y> <left> <top> <right> <bottom>") line, for a sequence the base data (dink.ini)
	 * does not define: from now on its frames have that hardbox (FDinkGameplayData::AddInitSequence). False if the line defines nothing new.
	 */
	bool ApplyInitLine(const FString& Line);
	/** Absolute hardbox of a sprite (getpic(): its current sequence/frame); false if no picture data. */
	bool GetHardbox(const FDinkSprite& Sprite, int32& L, int32& T, int32& R, int32& B) const;
	/** Script set sp_seq: a sequence with a hit frame schedules that sprite's melee test. */
	void OnSequenceSet(int32 Handle, int32 Seq);

	// ---- Player actions (keys, console, tests) ----

	/**
	 * Attack key, pressed and let go at once (a tap): the armed weapon's `use` (D:14819); the hit lands on the animation's hit frame.
	 * False if nothing ran (also while the bow is drawn: Dink's brain only processes the bow then, D:14761-14766).
	 */
	bool PlayerAttack();
	/**
	 * Attack key down (the original's button 1, sjoy.joybit[1]): runs the armed weapon's `use` as PlayerAttack does and keeps the key held.
	 * With the bow armed (item-b1/b2/b3 `use`: activate_bow) the draw grows while the key is held and the arrow leaves on
	 * PlayerAttackRelease (process_bow, D:14564-14621). The input layer binds the key's press and release to these two.
	 */
	bool PlayerAttackPress();
	/** Attack key up (sjoy.letgo[1], D:12091): a drawn bow is released at its next engine frame. */
	void PlayerAttackRelease();
	bool IsAttackHeld() const { return bAttackHeld; }

	// ---- The bow (D:9397-9420, 14564-14621, 17344) ----

	/** Most power a draw reaches (D:14604). */
	static constexpr int32 BowMaxPower = 500;
	/** Power per pull tick once `hitme` is set (D:14603). */
	static constexpr int32 BowPullPerTick = 7;
	/** A pull tick every 10 ms of engine time (D:14602): at the engine's 60 Hz, once a frame. */
	static constexpr double BowPullTickMs = 10.0;
	/** activate_bow (D:9397-9408), from the director: Dink stops (seq 0, pseq 100 + dir, pframe 1) and the bow is drawn for InstanceId. */
	void ActivateBow(int32 InstanceId);
	/** process_bow (D:14564-14621) for one engine frame at TickMs: aim, pull, and the release when the attack key is up. TickBrains calls it first in each frame. */
	void ProcessBow(double TickMs);
	/** The bow block of InstanceId ended without a release (instant mode): the draw so far becomes the last power, the bow is put down. */
	void EndBowBlock(int32 InstanceId);
	bool IsBowActive() const { return Bow.bActive; }
	/** The instance waiting in activate_bow, 0 if the bow is not drawn. */
	int32 GetBowInstance() const { return Bow.bActive ? Bow.Instance : 0; }
	/** The current draw (0..500). */
	int32 GetBowPower() const { return Bow.Time; }
	/** get_last_bow_power (D:9410-9414). */
	int32 GetLastBowPower() const { return Bow.LastPower; }
	const FDinkBowStatus& GetBowStatus() const { return Bow; }
	/** Magic key: the armed spell's `use` when &magic_level >= &magic_cost (D:14941). */
	bool PlayerCastMagic();
	/** Inventory screen stand-in: arm item slot N (1-based, &cur_weapon) as arm_weapon does. */
	bool ArmItemSlot(int32 Slot);
	/** Inventory screen stand-in: arm spell slot N (1-based, &cur_magic) as arm_magic does. */
	bool ArmMagicSlot(int32 Slot);
	/** Per frame from the player controller: Dink walks into hardness (not low hardness) in a numpad direction. */
	void UpdatePush(bool bBlockedByHardness, int32 Dir, double NowMs);
	/** New game: runs newgame.c `main` (fists added and armed, as the start button's start-1.c does). */
	void StartNewGame();
	/** Dink's pixel position and screen from the player pawn (PIE); nothing for a virtual Dink. */
	void SyncDinkFromActor();
	/**
	 * SyncDinkFromActor plus Dink's dir from the pawn's facing (the original's dir is where Dink faces). The attack,
	 * magic and talk keys call it before their scripts read sp_dir(1, -1); nothing for a virtual Dink.
	 */
	void SyncDinkFacingFromActor();

	// ---- Engine ports ----

	void RunThroughTagList(int32 Attacker);
	void RunThroughTouchDamageList(int32 H);
	void RunThroughTagListPush(int32 H);
	/**
	 * run_through_tag_list_talk (D:14171): the first sprite (handle order) whose hardbox + 10 px, plus 50 px
	 * (35 up/down) in Dink's facing direction, holds Dink and whose script has `talk`. 0 if none.
	 */
	int32 FindTalkTarget(int32 H);
	/** hurt_thing: defense rule, adds to the sprite's pending damage. Returns the damage added. */
	int32 HurtThing(int32 Target, int32 Damage);
	/** add_exp: only when Dink dealt the last hit unless bAlways (the add_exp command). */
	void AddExp(int32 Amount, int32 Sprite, bool bAlways = false);
	/** Applies pending damage the way each sprite's brain does on its next think. */
	void ProcessDamage();
	/** One 100 ms status update (D:5836): magic charge, level-up, Dink's death. */
	void StatusTick();

	// ---- Item scripts (commands) ----

	/** add_item / add_magic: inventory slot, then the item script's `pickup` (D:6915-6955). */
	int32 AddItem(FName Script, bool bMagic);
	/** arm_weapon / arm_magic: `disarm` of the old script, `arm` of the slot's script (D:7850-7870). */
	void ArmWeapon();
	void ArmMagic();
	/** kill_cur_item (D:1480): disarm, then holdingdrop and drop of the item. */
	void KillCurItem();
	/** kill_this_item (D:1505): drop of that item (holdingdrop and disarm first if armed). */
	void KillThisItem(FName Script);
	int32 GetWeaponInstance() const { return WeaponInstance; }
	int32 GetMagicInstance() const { return MagicInstance; }

	// ---- Brains (DinkBrains.cpp) ----

	/** Run the brains at all (on by default; tests of other rules may switch them off). */
	bool bBrainsEnabled = true;
	/** The 3D adaptation layer (loaded from Content/Dink/Data/AI/adaptation.ini by Init). */
	FDinkAdaptationSettings Adaptation;
	/** One engine frame (the original is locked at 60 fps, D:17300). */
	static constexpr double EngineFrameMs = 1000.0 / 60.0;
	/** Advances the brains by whole engine frames (60 Hz) of game time. */
	void TickBrains(double DeltaMs);
	/**
	 * ThinkSprite (D:16790) for one sprite at engine time TickMs: the sp_timing gate, its brain, the hardness
	 * check of the move it made and its animation (with the special-frame hit). Public so a State Tree task can
	 * drive one sprite; the brains are plain C++ on the director's sprite records.
	 */
	void ThinkSprite(int32 Handle, double TickMs);
	/**
	 * get_hard on Screen for engine pixel X (with the 20 px bar), Y. The map a draw_hard_sprite / draw_hard_map of this screen visit
	 * left (GetLiveHardness) if there is one; else the loaded map, where removed placements' hardboxes read as 0.
	 */
	int32 GetHard(int32 Screen, int32 X, int32 Y) const;
	/** get_distance_and_dir (D:12405, smooth_follow off as in the base game): the larger axis distance; cardinal dir. */
	int32 GetDistanceAndDir(int32 H, int32 H1, int32& OutDir) const;
	/** changedir (D:5596): mx/my from speed and dir, the walk sequence base+dir with the engine's fallbacks. */
	void ChangeDir(FDinkSprite& S, int32 Dir, int32 Base);
	/** automove + move (D:12214, 13520): steps mx/my one pixel at a time, recording the path. */
	void AutoMove(FDinkSprite& S);
	/** check_if_move_is_legal (D:13416): the first hard pixel on the path stops the sprite before it; returns its code. */
	int32 CheckIfMoveIsLegal(FDinkSprite& S);
	/** Sprites (other than Except) winding up or in an attack animation against Target. */
	int32 CountAttackers(int32 Target, int32 Except) const;
	// ---- Hardness the scripts change (sp_hard, draw_hard_sprite, draw_hard_map) ----

	/**
	 * sp_hard on a placement's sprite also sets the placement's flag in the loaded map (dink.cpp:9979-9998: g_smallMap.sprite[sp_index].hard
	 * = the sprite's new value), which draw_hard_* read (fill_hard_sprites D:7016). It lasts until the screen loads again (load_map reads
	 * map.dat). Hard is the inverted engine flag: 0 = hard.
	 */
	void SetPlacementHard(const FDinkOriginId& Origin, int32 Hard);
	/**
	 * draw_hard_sprite (dink.cpp:8089-8104): update_play_changes, then the tile hardness back under the sprite's hardbox (its picture's box at
	 * its position, fill_hardxy D:597-614), then the hardboxes of the background placements (fill_back_sprites D:6832-6895) and of every active
	 * sprite (fill_hard_sprites D:6972-7031) stamped again over the whole map. Also gives the greybox's solid collision the new hardness.
	 */
	void DrawHardSprite(int32 Handle);
	/** draw_hard_map (dink.cpp:8224-8232): update_play_changes, the whole tile layer (fill_whole_hard D:654), fill_hard_sprites, fill_back_sprites. */
	void DrawHardMap(int32 Screen);
	/** The map a draw_hard_* left on Screen in this screen visit (what GetHard reads); null if no script redrew it since the screen loaded. */
	const FDinkHardnessMap* GetLiveHardness(int32 Screen) const;
	/** A screen load (load_map + place_sprites_game build g_hitmap anew, D:5966): drops the redrawn maps and the visit's sp_hard and sp_prop flags. */
	void OnScreenLoaded();

	// ---- The placement's prop flag (sp_prop, owner decision OD1 of 9 Nov 2026) ----

	/**
	 * sp_prop on a placement's sprite: g_smallMap.sprite[n].prop = Prop until the screen loads again (load_map reads map.dat anew). No 1997
	 * command writes prop; the remaster's director defines sp_prop to (doc/remaster/verbatim_review.md OD1). What the engine does with the flag:
	 * get_hard reads a stamped hardbox (100 + n) of a placement with prop != 0 as 0, so it is walk-through (dink.cpp:569-575), and special_block
	 * warps Dink when the walk code runs into one with prop == 1 (D:15337-15341, called from D:16906-16909). Here: on a sprite warp (map.dat
	 * prop 1) 0 switches its greybox trigger off (its hardbox stays solid, as a prop-0 placement's stamped hardbox is) and 1 back on; on any other
	 * placement a non-zero prop makes its stamped hardbox walk-through (GetHard, the greybox's solid collision) and warps nowhere: only the 93
	 * map.dat warps have a trigger (the engine would also warp on prop 1 to the placement's warp_map, 0 for most). A value equal to map.dat's
	 * drops the change. Not saved: a load is a screen load.
	 */
	void SetPlacementProp(const FDinkOriginId& Origin, int32 Prop);
	/** The placement's prop now: what sp_prop set in this screen visit, else map.dat's (0 for an unknown placement). */
	int32 GetPlacementProp(const FDinkOriginId& Origin) const;

	/** screenlock(n) (D:10083): the flag, the greybox barriers of Dink's screen; a screen load clears it (D:1016). */
	void SetScreenLock(bool bLocked);
	bool IsScreenLocked() const;
	/** did_player_cross_screen (D:14049): false while the screen is locked (Dink is clamped at the edge). */
	bool CanDinkLeaveScreen() const { return !IsScreenLocked(); }
	/** Engine time of the last brain frame. */
	double GetBrainClockMs() const { return BrainClockMs; }

	// ---- Time ----

	/** Called by the story subsystem every tick before scripts step. */
	void Tick(double DeltaMs, double NowMs);
	/** Lands every pending hit now (instant mode). */
	void FlushPendingHits();

	// ---- Save ----
	TSharedPtr<FJsonObject> SaveState() const;
	void LoadState(const TSharedPtr<FJsonObject>& State);
	void Reset();

	/** Status updates done (tests). */
	int64 StatusTicks = 0;
	/** Gameplay events in order ("hit S002_P21 by 1", "die 7", "drop 9 heart", ...), for tests and dink.Story. */
	TArray<FString> Events;


private:
	UDinkDirector* Director() const;
	TArray<int32> LiveSprites(int32 Screen) const;
	void RunProc(int32 Handle, FName Proc);
	void RunInstanceProc(int32 InstanceId, FName Proc);
	int32 NewItemInstance(FName Script);
	void Die(int32 Handle);
	void AddKillSprite(int32 Handle);
	// Brains (DinkBrains.cpp)
	void Animate(FDinkSprite& S, double TickMs);
	void NoBrain(FDinkSprite& S);
	void BounceBrain(FDinkSprite& S);
	void DuckBrain(FDinkSprite& S, double TickMs);
	void PigBrain(FDinkSprite& S, double TickMs);
	void OneTimeBrain(FDinkSprite& S, bool bForReal);
	void RepeatBrain(FDinkSprite& S);
	void PillBrain(FDinkSprite& S, double TickMs);
	void DragonBrain(FDinkSprite& S, double TickMs);
	void MissileBrain(FDinkSprite& S, bool bRepeat);
	void ScaleBrain(FDinkSprite& S);
	void ShadowBrain(FDinkSprite& S);
	void PeopleBrain(FDinkSprite& S, double TickMs);
	void FindAction(FDinkSprite& S, double TickMs);
	bool ProcessFollow(FDinkSprite& S);
	void ProcessTarget(FDinkSprite& S);
	int32 AutoReverse(FDinkSprite& S);
	int32 AutoReverseDiag(FDinkSprite& S);
	/** Adaptation layer: may this sprite start its attack now? Handles the wind-up and the attacker cap. */
	bool AdaptationAllowsAttack(FDinkSprite& S, int32 Target, int32& InOutDir, double TickMs);
	void RunAttackScript(FDinkSprite& S);
	enum class EAuthoredInteraction { Hit, Talk, Touch, Push };
	bool UsesAuthoredGeometry(const FDinkSprite& Attacker, const FDinkSprite& Target) const;
	bool AuthoredActorMoveBlocked(const FDinkSprite& Sprite, const FIntPoint& From, const FIntPoint& To, FQuat* OutFacing = nullptr) const;
	bool AuthoredGeometryMatches(const FDinkSprite& Attacker, const FDinkSprite& Target, EAuthoredInteraction Kind, double* OutDistanceCm = nullptr) const;
	FDinkAuthoredInteractionSettings AuthoredInteraction;
	int32 CapsuleMarginPixels(const FDinkSprite& Dink) const;
	void Note(const FString& E);
	// Hardness redrawing (DinkGameplay.cpp, "Hardness the scripts change")
	struct FLiveHardness
	{
		/** g_hitmap of the screen after the draws so far. */
		TSharedPtr<FDinkHardnessMap> Map;
		/** The map before the first draw (the loaded map, removed placements' boxes as tile hardness): what the greybox's baked collision shows. */
		TArray<uint8> Base;
	};
	FDinkHardnessMap& EnsureLiveHardness(int32 Screen);
	/** The engine's map placement j after update_play_changes (D:5773-5832): active, type, hard flag, picture. False if it does not exist. */
	bool MapPlacement(const FDinkPlacementInfo& P, bool& bActive, int32& Type, int32& Hard, int32& Seq, int32& Frame) const;
	/** add_hardness (D:487-501): the absolute hardbox [L, R) x [T, B) (engine pixels: map x + 20) set to Code, clipped to the map. */
	static void AddHardness(FDinkHardnessMap& Map, int32 L, int32 T, int32 R, int32 B, uint8 Code);
	void FillBackSprites(FDinkHardnessMap& Map, int32 Screen) const;
	void FillHardSprites(FDinkHardnessMap& Map, int32 Screen) const;
	/** The greybox's solid collision of Screen follows the live map (UDinkGreyboxSubsystem::ApplyScreenSolidChanges); no-op without a world. */
	void SyncGreyboxHardness(int32 Screen);
	void RestoreGreyboxHardness();
	TMap<int32, FLiveHardness> LiveHardness;
	/** sp_hard on placement sprites in this screen visit: g_smallMap.sprite[n].hard (D:9997). */
	TMap<FDinkOriginId, int32> VisitPlacementHard;
	/** sp_prop on placement sprites in this screen visit, only where it differs from map.dat: g_smallMap.sprite[n].prop. */
	TMap<FDinkOriginId, int32> VisitPlacementProp;
	/** A stamped hardbox code (100 + n) of Screen that an sp_prop of this visit made walk-through (prop != 0 where map.dat has 0, D:569). */
	bool IsWalkThroughByProp(int32 Screen, int32 Code) const;
	/** The loaded map of Screen as the engine holds it (removed placements' boxes show the tile layer); false without data. */
	bool BuildLoadedCodes(int32 Screen, TArray<uint8>& OutCodes, int32& OutVision) const;

	void SetFact(const TCHAR* Name, int32 Value);
	int32 GetFact(const TCHAR* Name) const;
	bool IsFrozenDink() const;

	UPROPERTY()
	TObjectPtr<UDinkStorySubsystem> Story;

    void SaveEditorPictures(TSharedRef<FJsonObject> State) const;
    void LoadEditorPictures(const TSharedPtr<FJsonObject>& State);
    void RefuseOriginalHardnessProjection();
    bool AdmitRuntimeHardnessFromSourceFile(int32 Screen,int32 Vision,TSharedPtr<DinkHardness::PhysicsOwner> Owner,const FString& SourceFile,FString& Error);
    int32 EffectiveHardnessFlag(const FDinkPlacementInfo& Placement) const;
    void EffectiveHardnessPicture(const FDinkPlacementInfo& Placement, int32& Seq, int32& Frame) const;
    bool BuildHardnessDrawStamps(int32 Screen, int32 Vision, std::vector<DinkHardness::Stamp>& Out, FString& Error, bool bWholeMap=false, FDinkHardnessFitSet* Fits=nullptr) const;
    bool PrepareHardnessFit(const FDinkSprite& Sprite, uint8 Code, bool bPrebirth, FDinkHardnessFitSet& Fits, std::vector<DinkHardness::Stamp>& Runs, bool& Replaced, FString& Error) const;
    bool RefreshOriginalHardnessProp(int32 Screen,FString& Error);
    bool PublishHardnessFitVisuals(const TSharedPtr<FDinkHardnessFitSet>& Before, FString& Error);
    bool FittedMissileMatches(const FDinkSprite& Missile,const FDinkSprite& Target,int32 Range) const;
    bool HasHardnessFitInstance(const FDinkSprite& Sprite) const;
    UPrimitiveComponent* FindHardnessFitPrimitive(const FDinkSprite& Sprite, FString* Error=nullptr) const;
    friend class FDinkHardnessShadowRoundTrip;
    friend class FDinkHardnessRetainedLegacyOwner;
    friend class FDinkHardnessEditorCarryActor;
    friend class FDinkHardnessFittedLifecycle;
    // Read-only access for real-map acceptance; no admission/path override.
    friend class FDinkRealBarrelCheck;
#if WITH_DEV_AUTOMATION_TESTS
    friend class FDinkBarrelAttackNativeDiagnostic; // read-only developer metrology; no gameplay seam
#endif
    friend class FDinkRolloutRuntimeCheck;
    friend class FDinkRolloutBackgroundCheck;
    bool ValidateRetainedLegacyEditorFlags(int32 Screen,FString& Error) const;
    int32 InspectOriginalShadowSlot(int32 Handle) const;
    bool ReserveOriginalEditorSlot(int32 Owner);
    TSharedPtr<FDinkOriginalSlotHistory> OriginalSlotHistory;
    void SetHardnessLoading(bool Loading);
    bool bHardnessLoading=false;
    TWeakObjectPtr<APlayerController> HardnessBlockedController;
    TSharedPtr<FDinkHardnessProjection> HardnessProjection;
    // Retain registered physical bodies independently of transient map/session lifetime.
    TMap<int32, TSharedPtr<DinkHardness::PhysicsOwner>> HardnessOwners;
    struct FEditorHardnessState { int32 Hard = 0, Seq = 0, Frame = 0; bool bHardSet = false; };
    TMap<FDinkOriginId, FEditorHardnessState> EditorHardness;
    TMap<int64, TSharedPtr<FDinkRuntimeHardnessState>> RuntimeHardness;
    static int64 RuntimeHardnessKey(int32 Screen, int32 Vision)
    { return (static_cast<int64>(Screen) << 32) | static_cast<uint32>(Vision); }
	FDinkGameplayData Data;
	TSharedPtr<IDinkRandomSource> RandomSource;
	/** The seeded stream (RandomSource points at it unless a test injected another source). */
	TSharedPtr<FDinkStreamRandomSource> StreamSource;
	int32 Seed = 1997;
	int32 WeaponInstance = 0;
	int32 MagicInstance = 0;
	int32 DeathInstance = 0;
	TArray<FDinkPendingHit> PendingHits;
	FDinkBowStatus Bow;
	/** The attack key is held (PlayerAttackPress .. PlayerAttackRelease): the original's sjoy.joybit[1]. */
	bool bAttackHeld = false;
	double NowMs = 0.0;
	double NextStatusMs = 100.0;
	bool bPushActive = false;
	int32 PushDir = 0;
	double PushStartMs = 0.0;
	/** Brain clock: engine frames run at BrainClockMs, BrainCarryMs of game time not yet used. */
	double BrainClockMs = 0.0;
	double BrainCarryMs = 0.0;
	/** moveman / lpx / lpy of the sprite thinking now: the pixels its last automove passed (index 0 = start). */
	TArray<FIntPoint> MovePath;
};
