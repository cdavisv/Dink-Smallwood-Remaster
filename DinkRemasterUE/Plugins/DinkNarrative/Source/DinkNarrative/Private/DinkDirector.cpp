#include "DinkDirector.h"
#include "DinkAudioSubsystem.h"
#include "DinkCreatureSubsystem.h"
#include "DinkArtSubsystem.h"
#include "DinkStorySubsystem.h"
#include "DinkScriptSpriteComponent.h"
#include "DinkFactSubsystem.h"
#include "DinkGameplay.h"
#include "DinkInventoryComponent.h"
#include "DinkLayout.h"
#include "DinkOriginComponent.h"
#include "DinkSaveSubsystem.h"
#include "DinkStatsComponent.h"
#include "DinkWorldStateSubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

namespace
{
	/** Pixels per second per point of sp_speed. ASSUMED (not measured in the original): speed 1 = 60 px/s. */
	constexpr double PixelsPerSecondPerSpeed = 60.0;
	/** A move that has not reached its stop coordinate after this long is ended (the original can stall on hardness forever). */
	constexpr double MaxMoveMs = 30000.0;
	/** get_version(): C_DINK_VERSION of the Dink Smallwood HD engine this data comes from (dink.h:196). */
	constexpr int32 DinkVersion = 114;

	FIntPoint DirVector(int32 Dir)
	{
		switch (Dir)
		{
		case 1: return FIntPoint(-1, 1);
		case 2: return FIntPoint(0, 1);
		case 3: return FIntPoint(1, 1);
		case 4: return FIntPoint(-1, 0);
		case 6: return FIntPoint(1, 0);
		case 7: return FIntPoint(-1, -1);
		case 8: return FIntPoint(0, -1);
		case 9: return FIntPoint(1, -1);
		default: return FIntPoint(0, 0);
		}
	}

	/** Screen-space angle of a numpad direction, degrees from east towards south (+y). */
	double DirAngle(int32 Dir)
	{
		switch (Dir)
		{
		case 6: return 0.0;
		case 3: return 45.0;
		case 2: return 90.0;
		case 1: return 135.0;
		case 4: return 180.0;
		case 7: return -135.0;
		case 8: return -90.0;
		case 9: return -45.0;
		default: return 90.0;
		}
	}

	FString SaveSlotName(int32 Slot)
	{
		return FString::Printf(TEXT("dink_save%d"), Slot);
	}

	TSharedPtr<Ink::FValueType> IntResult(int32 V) { return MakeShared<Ink::FValueType>(V); }

	/** Generated placeholders are Static; a script that moves one makes it Movable (at run time only). */
	void MakeMovable(AActor* Actor)
	{
		USceneComponent* Root = Actor ? Actor->GetRootComponent() : nullptr;
		if (!Root || Root->Mobility == EComponentMobility::Movable)
		{
			return;
		}
		TArray<USceneComponent*> Components;
		Actor->GetComponents<USceneComponent>(Components);
		for (USceneComponent* C : Components)
		{
			C->SetMobility(EComponentMobility::Movable);
		}
	}
	TSharedPtr<Ink::FValueType> StringResult(const FString& S) { return MakeShared<Ink::FValueType>(S); }
}

void FDinkAudioStub::Cue(const FString& InCue)
{
	Cues.Add(InCue);
	if (Cues.Num() > 512)
	{
		Cues.RemoveAt(0, Cues.Num() - 512);
	}
	UE_LOG(LogDinkAudio, Log, TEXT("audio cue %s"), *InCue);
	if (Playback) Playback(InCue);
}

void UDinkDirector::Init(UDinkStorySubsystem* InStory)
{
	Story = InStory;
	Audio.Playback = [this](const FString& Cue) { if (UWorld* World = GetWorld()) if (UDinkAudioSubsystem* Local = World->GetSubsystem<UDinkAudioSubsystem>()) Local->HandleCue(Cue, this); };
	RegisterCommands();
}

UDinkInventoryComponent* UDinkDirector::GetInventory()
{
	if (AActor* Dink = GetActor(1))
	{
		if (UDinkInventoryComponent* Inv = Dink->FindComponentByClass<UDinkInventoryComponent>())
		{
			return Inv;
		}
	}
	if (!FallbackInventory)
	{
		FallbackInventory = NewObject<UDinkInventoryComponent>(this, TEXT("FallbackInventory"));
	}
	return FallbackInventory;
}

UDinkStatsComponent* UDinkDirector::GetPlayerStats() const
{
	const AActor* Dink = GetActor(1);
	return Dink ? Dink->FindComponentByClass<UDinkStatsComponent>() : nullptr;
}

// ---------------------------------------------------------------------------------------------
// Command table

void UDinkDirector::Register(const TCHAR* Name, EDinkCommandStatus Status, const TCHAR* Note, FDinkCommandHandler Handler)
{
	FDinkCommandDef Def;
	Def.Name = FName(Name);
	Def.Status = Status;
	Def.Note = Note;
	Def.Handler = MoveTemp(Handler);
	Commands.Add(Def.Name, MoveTemp(Def));
}

FDinkCommandResult UDinkDirector::RecordOnly(FDinkCommandContext& Ctx)
{
	UE_LOG(LogDinkDirector, Verbose, TEXT("recorded %s %s"), *Ctx.Name.ToString(), *FString::Join(Ctx.Line.Args, TEXT(" ")));
	return FDinkCommandResult();
}

void UDinkDirector::RegisterRecordedProp(const TCHAR* Prop, const TCHAR* Note)
{
	const FName PropName(Prop);
	Register(*FString::Printf(TEXT("sp_%s"), Prop), EDinkCommandStatus::Recorded, Note, [this, PropName](FDinkCommandContext& Ctx)
	{
		SpriteProperty(&Ctx.Instance, PropName, Ctx.Int(0), Ctx.Int(1, -1));
		return FDinkCommandResult();
	});
}

void UDinkDirector::RegisterCommands()
{
	using S = EDinkCommandStatus;
	auto Block = [](EDinkBlock Kind, double Until = 0.0, int32 Ref = 0)
	{
		FDinkCommandResult R;
		R.Block = static_cast<uint8>(Kind);
		R.BlockUntilMs = Until;
		R.BlockRef = Ref;
		return R;
	};

	// ---- Timing and control ----
	Register(TEXT("wait"), S::Implemented, TEXT("suspends this script instance for ms of game time (others keep running)"), [this, Block](FDinkCommandContext& Ctx)
	{
		return Block(EDinkBlock::Time, Story->GetNowMs() + FMath::Max(0, Ctx.Int(0)));
	});
	Register(TEXT("freeze"), S::Implemented, TEXT("sprite frozen; for Dink (1) player movement input is ignored"), [this](FDinkCommandContext& Ctx)
	{
		SetFrozen(Ctx.Int(0), true);
		return FDinkCommandResult();
	});
	Register(TEXT("unfreeze"), S::Implemented, TEXT("undoes freeze"), [this](FDinkCommandContext& Ctx)
	{
		SetFrozen(Ctx.Int(0), false);
		return FDinkCommandResult();
	});
	Register(TEXT("wait_for_button"), S::Implemented, TEXT("blocks until the skip/confirm key"), [Block](FDinkCommandContext&)
	{
		return Block(EDinkBlock::Button);
	});
	Register(TEXT("kill_this_task"), S::Implemented, TEXT("ends this script instance; the sprite keeps no script"), [this](FDinkCommandContext& Ctx)
	{
		if (FDinkSprite* Sprite = FindSprite(Ctx.Instance.Sprite))
		{
			if (Sprite->Script == Ctx.Instance.Script)
			{
				Sprite->Script = NAME_None;
			}
		}
		FDinkCommandResult R;
		R.bEndScript = true;
		return R;
	});
	Register(TEXT("script_attach"), S::Implemented, TEXT("re-owns the instance (1000 = survives screen changes)"), [](FDinkCommandContext& Ctx)
	{
		Ctx.Instance.AttachedTo = Ctx.Int(0);
		return FDinkCommandResult();
	});
	Register(TEXT("external"), S::Implemented, TEXT("runs another script's procedure in a new instance for the same sprite and waits for it"), [this, Block](FDinkCommandContext& Ctx)
	{
		TArray<int32> Args;
		for (int32 A = 2; A < Ctx.Num(); ++A)
		{
			Args.Add(Ctx.Int(A));
		}
		const FName Script(*Ctx.Str(0));
		const FName Proc(*Ctx.Str(1));
		const int32 Child = Story->StartProcedure(Script, Proc, Ctx.Instance.Sprite, Args, Ctx.Instance.Screen, /*bNewInstance*/ true);
		if (Child == 0)
		{
			UE_LOG(LogDinkDirector, Log, TEXT("external %s.%s: not in the converted story (the original has no such script or procedure); nothing to run"), *Script.ToString(), *Proc.ToString());
			Story->MissingTargets.FindOrAdd(FString::Printf(TEXT("external %s.%s"), *Script.ToString().ToLower(), *Proc.ToString().ToLower()))++;
			return FDinkCommandResult();
		}
		FDinkScriptInstance* ChildInstance = Story->FindInstance(Child);
		ChildInstance->ParentId = Ctx.Instance.Id;
		ChildInstance->bEndWithProcedure = true;
		return Block(EDinkBlock::Child, 0.0, Child);
	});
	Register(TEXT("spawn"), S::Implemented, TEXT("starts another script's main in a new instance owned by 1000"), [this](FDinkCommandContext& Ctx)
	{
		const int32 Child = Story->StartProcedure(FName(*Ctx.Str(0)), TEXT("main"), HandleNoSprite, {}, Ctx.Instance.Screen, /*bNewInstance*/ true);
		if (Child == 0)
		{
			Story->MissingTargets.FindOrAdd(FString::Printf(TEXT("spawn %s.main"), *Ctx.Str(0).ToLower()))++;
		}
		if (FDinkScriptInstance* ChildInstance = Story->FindInstance(Child))
		{
			ChildInstance->AttachedTo = HandleNoSprite;
		}
		return FDinkCommandResult();
	});
	Register(TEXT("set_callback_random"), S::Implemented, TEXT("repeating timer that runs a procedure of this instance when it is idle"), [this](FDinkCommandContext& Ctx)
	{
		Ctx.Instance.CallbackProc = FName(*Ctx.Str(0));
		Ctx.Instance.CallbackMinMs = Ctx.Int(1);
		Ctx.Instance.CallbackRandomMs = Ctx.Int(2);
		Ctx.Instance.NextCallbackMs = Story->GetNowMs() + Ctx.Int(1) + (Ctx.Int(2) > 0 ? Story->GetGameplay()->RandomModulo(Ctx.Int(2)) : 0);
		return FDinkCommandResult();
	});
	Register(TEXT("choice_start"), S::Implemented, TEXT("menu arguments (set_y, title colour); the options are the Ink choices that follow"), [](FDinkCommandContext& Ctx)
	{
		Ctx.Instance.MenuSetY = Ctx.Int(0);
		Ctx.Instance.MenuTitleColor = Ctx.Int(1);
		Ctx.Instance.MenuTitle.Reset();
		return FDinkCommandResult();
	});

	// ---- Movement ----
	Register(TEXT("move"), S::Implemented, TEXT("walks the sprite in a numpad direction until it passes the stop coordinate; does not wait"), [this](FDinkCommandContext& Ctx)
	{
		if (FDinkSprite* Sprite = FindSprite(Ctx.Int(0)))
		{
			StartMove(*Sprite, Ctx.Int(1), Ctx.Int(2), Ctx.Int(3));
		}
		return FDinkCommandResult();
	});
	Register(TEXT("move_stop"), S::Implemented, TEXT("as move, and the script waits until the sprite arrives"), [this, Block](FDinkCommandContext& Ctx)
	{
		FDinkSprite* Sprite = FindSprite(Ctx.Int(0));
		if (!Sprite)
		{
			return FDinkCommandResult();
		}
		StartMove(*Sprite, Ctx.Int(1), Ctx.Int(2), Ctx.Int(3));
		return Sprite->bMoving ? Block(EDinkBlock::Move, 0.0, Sprite->Handle) : FDinkCommandResult();
	});

	// ---- Sprites ----
	const TCHAR* PropNote = TEXT("sprite property: moves/turns the actor through the screen-to-world transform");
	for (const TCHAR* Prop : { TEXT("x"), TEXT("y"), TEXT("dir") })
	{
		const FName PropName(Prop);
		Register(*FString::Printf(TEXT("sp_%s"), Prop), S::Implemented, PropNote, [this, PropName](FDinkCommandContext& Ctx)
		{
			SpriteProperty(&Ctx.Instance, PropName, Ctx.Int(0), Ctx.Int(1, -1));
			return FDinkCommandResult();
		});
	}
	struct FPropDef { const TCHAR* Prop; S Status; const TCHAR* Note; };
	const FPropDef Props[] = {
		{ TEXT("speed"), S::Implemented, TEXT("pixels per think for brains (changedir, D:5596, sets a new mx/my at once) and move/move_stop (60 px/s per point = speed px per 60 Hz frame at timing 0)") },
		{ TEXT("hitpoints"), S::Implemented, TEXT("life of the actor's UDinkStatsComponent (recorded when it has none)") },
		{ TEXT("strength"), S::Implemented, TEXT("strength of the actor's UDinkStatsComponent (recorded when it has none)") },
		{ TEXT("defense"), S::Implemented, TEXT("defense of the actor's UDinkStatsComponent (recorded when it has none)") },
		{ TEXT("touch_damage"), S::Implemented, TEXT("touch damage of the actor's UDinkStatsComponent (recorded when it has none)") },
		{ TEXT("nodraw"), S::Implemented, TEXT("hides / shows the actor") },
		{ TEXT("size"), S::Implemented, TEXT("actor scale = size / 100") },
		{ TEXT("kill"), S::Implemented, TEXT("removes the sprite after ms (sp_kill timer)") },
		{ TEXT("brain"), S::Implemented, TEXT("the sprite's brain, run every 60 Hz engine frame (DinkBrains.cpp): 0 none/follow, 2 bounce, 3 duck, 4 pig, 5/6/7 play once/repeat/play and vanish, 9 monster (wander, chase, melee), 10 dragon (script ATTACK), 11/17 missile (hardness), 12 scale and vanish, 15 shadow, 16 people; 13/14 (title mouse/buttons) are recorded only") },
		{ TEXT("brain_parm"), S::Implemented, TEXT("brain parameter: target size of brain 12 (pickup vanish), the sprite a missile must not hit; other uses recorded for the AI layer") },
		{ TEXT("brain_parm2"), S::Implemented, TEXT("second sprite a missile must not hit (missile_brain D:14318); other uses recorded") },
		{ TEXT("timing"), S::Implemented, TEXT("think interval: the brain runs at most once per timing ms (ThinkSprite's timer, D:16830); the animation runs every frame") },
		{ TEXT("seq"), S::Implemented, TEXT("animation sequence: the frame stepper (dink.ini delays, loops, ends -> seq_orig) drives every sprite but Dink and lands a melee hit on a special frame; Dink's attack lands at the hit frame's time; nothing is drawn yet") },
		{ TEXT("pseq"), S::Implemented, TEXT("picture sequence: its hardbox is the sprite's box for hit/touch/talk/missile tests (getpic); nothing is drawn yet") },
		{ TEXT("pframe"), S::Implemented, TEXT("picture frame: its hardbox is the sprite's box (getpic); nothing is drawn yet") },
		{ TEXT("frame"), S::Implemented, TEXT("animation frame of the frame stepper (0 restarts the sequence)") },
		{ TEXT("frame_delay"), S::Implemented, TEXT("fixed delay per frame for the frame stepper instead of dink.ini's") },
		{ TEXT("base_walk"), S::Implemented, TEXT("walk sequence base: changedir picks base+dir (with the engine fallbacks); 110 marks a headless duck") },
		{ TEXT("base_attack"), S::Implemented, TEXT("attack sequence base: a brain-9 monster attacks with base_attack+dir; -1 = never melees; also decides whether a hit makes it target the attacker") },
		{ TEXT("base_death"), S::Recorded, TEXT("2D death sequence base, recorded for the animation layer") },
		{ TEXT("base_idle"), S::Recorded, TEXT("2D idle sequence base, recorded for the animation layer") },
		{ TEXT("reverse"), S::Recorded, TEXT("2D animation reversed, recorded for the animation layer") },
		{ TEXT("que"), S::Recorded, TEXT("2D draw order, recorded (no meaning for depth-sorted 3D)") },
		{ TEXT("noclip"), S::Recorded, TEXT("2D screen clipping, recorded (no meaning in 3D)") },
		{ TEXT("hard"), S::Recorded, TEXT("hardbox in the hardness map, recorded (greybox collision is baked per screen)") },
		{ TEXT("nohit"), S::Implemented, TEXT("no hit damage: melee only runs `hit` (if scripted), missiles pass (D:15467, 14316)") },
		{ TEXT("notouch"), S::Implemented, TEXT("touch/missile immunity flag; as in the engine it clears on the next tick unless a hit set its timer") },
		{ TEXT("nocontrol"), S::Recorded, TEXT("player control lock while moving, recorded") },
		{ TEXT("exp"), S::Implemented, TEXT("experience the player gets when he dealt the killing blow (add_exp in add_kill_sprite, D:12359)") },
		{ TEXT("target"), S::Implemented, TEXT("sprite a brain-9 monster chases and attacks, a brain-10 one casts at (process_target, D:12588)") },
		{ TEXT("follow"), S::Implemented, TEXT("sprite to walk after until within 40 px (process_follow, D:12560)") },
		{ TEXT("distance"), S::Implemented, TEXT("a monster attacks (and stops closing in) when its target is nearer than this on the larger axis (5 if 0)") },
		{ TEXT("range"), S::Implemented, TEXT("melee reach of the sprite's attack (sword: 40 px instead of 28) and a missile's hit margin (D:15476, 14322)") },
		{ TEXT("attack_wait"), S::Implemented, TEXT("no attack before game time + ms (D:9335)") },
		{ TEXT("kill_wait"), S::Recorded, TEXT("AI delay, recorded for the AI layer") },
		{ TEXT("flying"), S::Implemented, TEXT("crosses low hardness (2): missiles fly over water and fences, walls still stop them (check_if_move_is_legal, D:13428)") },
		{ TEXT("sound"), S::Recorded, TEXT("looping sprite sound, recorded for the audio layer") },
		{ TEXT("disabled"), S::Recorded, TEXT("sprite disabled flag, recorded") },
		{ TEXT("editor_num"), S::Recorded, TEXT("read-only in practice (placement number); a write is recorded") },
		{ TEXT("prop"), S::Recorded, TEXT("not a DinkC built-in (the engine ignores it); only behind a fix switch") },
		{ TEXT("mx"), S::Implemented, TEXT("x pixels per think of the sprite's brain movement (missiles, bounce; changedir sets it from speed and dir)") },
		{ TEXT("my"), S::Implemented, TEXT("y pixels per think of the sprite's brain movement (missiles, bounce; changedir sets it from speed and dir)") },
		{ TEXT("attack_hit_sound"), S::Recorded, TEXT("sound of the sprite's hits, recorded for the audio layer (the audio stub logs a hit cue)") },
		{ TEXT("attack_hit_sound_speed"), S::Recorded, TEXT("speed of that sound, recorded for the audio layer") },
	};
	for (const FPropDef& P : Props)
	{
		if (P.Status == S::Recorded)
		{
			RegisterRecordedProp(P.Prop, P.Note);
		}
		else
		{
			const FName PropName(P.Prop);
			Register(*FString::Printf(TEXT("sp_%s"), P.Prop), P.Status, P.Note, [this, PropName](FDinkCommandContext& Ctx)
			{
				SpriteProperty(&Ctx.Instance, PropName, Ctx.Int(0), Ctx.Int(1, -1));
				return FDinkCommandResult();
			});
		}
	}
	Register(TEXT("sp_active"), S::Implemented, TEXT("0 removes the sprite: actor hidden (spawned ones destroyed), its scripts end"), [this](FDinkCommandContext& Ctx)
	{
		const int32 Handle = Ctx.Int(0);
		if (Ctx.Int(1, -1) == 0)
		{
			DeactivateSprite(Handle, Ctx.Instance.Id);
		}
		else if (Ctx.Int(1, -1) == 1)
		{
			if (FDinkSprite* Sprite = FindSprite(Handle))
			{
				Sprite->bActive = true;
				if (AActor* Actor = Sprite->Actor.Get())
				{
					Actor->SetActorHiddenInGame(false);
				}
			}
		}
		return FDinkCommandResult();
	});
	Register(TEXT("sp_script"), S::Implemented, TEXT("attaches a script to the sprite (ending its old one) and runs its main at once (dink.cpp:8155-8175)"), [this](FDinkCommandContext& Ctx)
	{
		const int32 Handle = Ctx.Int(0);
		const FName Script(*Ctx.Str(1).ToLower());
		FDinkSprite* Sprite = FindSprite(Handle);
		if (!Sprite)
		{
			return FDinkCommandResult();
		}
		for (const TUniquePtr<FDinkScriptInstance>& I : Story->Instances)
		{
			if (I->IsAlive() && I->Sprite == Handle && I->ParentId == 0)
			{
				if (I->Id == Ctx.Instance.Id)
				{
					I->bKillPending = true;
				}
				else
				{
					Story->FinishInstance(*I, TEXT("sp_script replaced it"));
				}
			}
		}
		Sprite->Script = Script;
		if (UDinkScriptSpriteComponent* Comp = UDinkScriptSpriteComponent::FindOrAdd(Sprite->Actor.Get()))
		{
			Comp->Script = Script;
		}
		if (AActor* Actor = Sprite->Actor.Get())
			if (UDinkArtSubsystem* Art = Actor->GetWorld()->GetSubsystem<UDinkArtSubsystem>())
				Art->ApplyScriptCharacter(Actor, Script, Sprite->GetProp(TEXT("size"), 100) > 0 ? Sprite->GetProp(TEXT("size"), 100) / 100.f : 1.f);
		// dink.cpp:8155-8175: kill_scripts_owned_by, load_script, then `locate(script, "MAIN"); run_script(script)` ON THE SPOT, in the
		// caller's turn, unless no_running_main is set (a screen's base script during the screen build, dink.cpp:6812: the main runs
		// later, from init_scripts). run_script runs until the script blocks, then control returns to the caller; RunNow does the same
		// (a main that waits or say_stops stays Running/Blocked and the story tick continues it). So `sp_script(&s, "B"); sp_hitpoints(&s, 40);`
		// leaves 40 here as in the original: B's main set its stats first. (Before 7 Nov 2026 only StartProcedure ran, so main ran after
		// the caller yielded and B's 100 hit points overwrote the caller's 40: pitfall 53.)
		// `Sprite` can be invalidated by the main (it may create sprites): not used after this call.
		const int32 MainId = Script.IsNone() ? 0 : Story->StartProcedure(Script, TEXT("main"), Handle, {}, Sprite->Screen > 0 ? Sprite->Screen : Ctx.Instance.Screen, /*bNewInstance*/ true);
		if (MainId)
		{
			if (!Story->bNoRunningMain)
			{
				Story->RunNow(MainId);
			}
		}
		else if (!Script.IsNone())
		{
			// The engine attaches the script and runs main only if it has one (dam-bomn has only `damage`).
			if (!Story->GetStory().Names().ScriptToKnot.Contains(Script))
			{
				UE_LOG(LogDinkDirector, Log, TEXT("sp_script %d %s: the original has no such script; attached as a name only"), Handle, *Script.ToString());
				Story->MissingTargets.FindOrAdd(FString::Printf(TEXT("sp_script %s"), *Script.ToString()))++;
			}
		}
		return FDinkCommandResult();
	});
	Register(TEXT("create_sprite"), S::Implemented, TEXT("spawns a marker actor at the screen pixel (statement form; the value form is the EXTERNAL)"), [this](FDinkCommandContext& Ctx)
	{
		const int32 Handle = CreateVirtualSprite(InstanceScreen(Ctx.Instance), Ctx.Int(0), Ctx.Int(1));
		FDinkSprite& Sprite = Sprites[Handle];
		InitCreatedSprite(Sprite);
		Sprite.Props.Add(TEXT("brain"), Ctx.Int(2));
		Sprite.Props.Add(TEXT("pseq"), Ctx.Int(3));
		Sprite.Props.Add(TEXT("pframe"), Ctx.Int(4));
		SpawnSpriteActor(Sprite);
		return FDinkCommandResult();
	});
	Register(TEXT("hurt"), S::Implemented, TEXT("hurt_thing (defense rule; the target's brain applies it next tick, a death runs `die`), then the target's `hit` unless nohit, with &enemy_sprite/&missle_source = the caller's sprite (D:9937)"), [this](FDinkCommandContext& Ctx)
	{
		const int32 Handle = Ctx.Int(0);
		const int32 Damage = Ctx.Int(1);
		if (!FindSprite(Handle) || Damage < 0)
		{
			return FDinkCommandResult();
		}
		Story->GetGameplay()->HurtThing(Handle, Damage);
		const FDinkSprite* Target = FindSprite(Handle);
		if (Target && Target->GetProp(TEXT("nohit")) != 1 && !Target->Script.IsNone() && Story->HasProcedure(Target->Script, TEXT("hit")))
		{
			if (Ctx.Instance.Sprite != HandleNoSprite)
			{
				if (UDinkFactSubsystem* Facts = Story->GetFacts())
				{
					Facts->SetFact(TEXT("enemy_sprite"), Ctx.Instance.Sprite);
					Facts->SetFact(TEXT("missle_source"), Ctx.Instance.Sprite);
				}
			}
			const int32 Id = Story->StartProcedure(Target->Script, TEXT("hit"), Handle, {}, Target->Screen > 0 ? Target->Screen : INDEX_NONE);
			if (Id && Id != Ctx.Instance.Id)
			{
				Story->RunNow(Id);
			}
		}
		return FDinkCommandResult();
	});
	Register(TEXT("kill_shadow"), S::Implemented, TEXT("removes the brain-15 shadow sprites whose brain_parm is the sprite (D:9020)"), [this](FDinkCommandContext& Ctx)
	{
		TArray<int32> Shadows;
		for (const TPair<int32, FDinkSprite>& Pair : Sprites)
		{
			if (Pair.Value.bActive && Pair.Value.GetProp(TEXT("brain")) == 15 && Pair.Value.GetProp(TEXT("brain_parm")) == Ctx.Int(0))
			{
				Shadows.Add(Pair.Key);
			}
		}
		for (const int32 H : Shadows)
		{
			DeactivateSprite(H, Ctx.Instance.Id, false);
		}
		return FDinkCommandResult();
	});
	Register(TEXT("run_script_by_number"), S::Implemented, TEXT("runs a procedure of the script instance with that number (&current_script), relocating it like run_script (D:8204)"), [this](FDinkCommandContext& Ctx)
	{
		const int32 Id = Ctx.Int(0);
		if (Id != Ctx.Instance.Id && Story->FindInstance(Id) && Story->StartProcedureIn(Id, FName(*Ctx.Str(1).ToLower())))
		{
			Story->RunNow(Id);
		}
		return FDinkCommandResult();
	});

	// ---- World state ----
	auto OriginFor = [this](FDinkCommandContext& Ctx, int32 Placement) { return FDinkOriginId(InstanceScreen(Ctx.Instance), Placement); };
	Register(TEXT("editor_type"), S::Implemented, TEXT("persistent per-placement override in UDinkWorldStateSubsystem (types 1-8, the original's spmap)"), [this, OriginFor](FDinkCommandContext& Ctx)
	{
		const FDinkOriginId Origin = OriginFor(Ctx, Ctx.Int(0));
		const int32 Type = Ctx.Int(1);
		if (UDinkWorldStateSubsystem* World = Story->GetWorldState(); World && Origin.IsValid() && Type >= 0 && Type <= 8)
		{
			FDinkWorldOverride Existing;
			const FName Variant = World->TryGetOverride(Origin, Existing) ? Existing.Variant : NAME_None;
			World->SetOverride(Origin, static_cast<EDinkOverrideType>(Type), Variant);
		}
		return FDinkCommandResult();
	});
	auto EditorVariant = [this, OriginFor](FDinkCommandContext& Ctx, const TCHAR* Part)
	{
		const FDinkOriginId Origin = OriginFor(Ctx, Ctx.Int(0));
		UDinkWorldStateSubsystem* World = Story->GetWorldState();
		FDinkWorldOverride Existing;
		if (World && Origin.IsValid() && World->TryGetOverride(Origin, Existing))
		{
			World->SetOverride(Origin, Existing.Type, FName(*FString::Printf(TEXT("%s%d"), Part, Ctx.Int(1))));
		}
		return FDinkCommandResult();
	};
	Register(TEXT("editor_seq"), S::Implemented, TEXT("stored as the override's Variant (\"seq<N>\") when the placement has an override"), [EditorVariant](FDinkCommandContext& Ctx) { return EditorVariant(Ctx, TEXT("seq")); });
	Register(TEXT("editor_frame"), S::Implemented, TEXT("stored as the override's Variant (\"frame<N>\") when the placement has an override"), [EditorVariant](FDinkCommandContext& Ctx) { return EditorVariant(Ctx, TEXT("frame")); });
	Register(TEXT("force_vision"), S::Implemented, TEXT("sets &vision; the greybox shows that vision's placements"), [this](FDinkCommandContext& Ctx)
	{
		if (UDinkFactSubsystem* Facts = Story->GetFacts())
		{
			Facts->SetFact(TEXT("vision"), Ctx.Int(0));
		}
		return FDinkCommandResult();
	});
	Register(TEXT("load_screen"), S::Implemented, TEXT("warps Dink to &player_map (greybox dink.Goto) keeping his screen pixel"), [this](FDinkCommandContext& Ctx)
	{
		const int32 Target = Story->GetFacts() ? Story->GetFacts()->GetFact(TEXT("player_map")) : 0;
		FDinkSprite& Dink = GetDink();
		Dink.Screen = Target;
		if (UWorld* World = GetWorld())
		{
			if (UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>())
			{
				Greybox->GotoScreen(Target, Dink.X - 20.0, Dink.Y);
			}
		}
		return FDinkCommandResult();
	});
	Register(TEXT("draw_screen"), S::Implemented, TEXT("yields one frame (the screen is already drawn in 3D)"), [this, Block](FDinkCommandContext&)
	{
		return Block(EDinkBlock::Frame, Story->GetNowMs());
	});
	Register(TEXT("screenlock"), S::Implemented, TEXT("locked fight (D:10083): Dink cannot leave the screen; the greybox raises a barrier on the screen's open edges until screenlock(0) or the next screen load (load_map clears it, D:1016); sprite warps are not refused, as in the original"), [this](FDinkCommandContext& Ctx)
	{
		const int32 Value = Ctx.Int(0, 1);
		if (Value == 0 || Value == 1)
		{
			Story->GetGameplay()->SetScreenLock(Value != 0);
		}
		return FDinkCommandResult();
	});
	Register(TEXT("dink_can_walk_off_screen"), S::Recorded, TEXT("flag kept; screen edges are not walls in 3D"), [this](FDinkCommandContext& Ctx)
	{
		bDinkCanWalkOffScreen = Ctx.Int(0) != 0;
		return FDinkCommandResult();
	});
	Register(TEXT("draw_hard_map"), S::Recorded, TEXT("collision is baked into the screen meshes; nothing to rebuild"), [this](FDinkCommandContext& Ctx) { return RecordOnly(Ctx); });
	Register(TEXT("draw_hard_sprite"), S::Recorded, TEXT("collision is baked into the screen meshes; nothing to rebuild"), [this](FDinkCommandContext& Ctx) { return RecordOnly(Ctx); });

	// ---- Screen ----
	Register(TEXT("fade_down"), S::Implemented, TEXT("fades the view to black and waits (600 ms, assumed)"), [this, Block](FDinkCommandContext&)
	{
		FadeTarget = 1.f;
		return Block(EDinkBlock::Time, Story->GetNowMs() + FadeDurationMs);
	});
	Register(TEXT("fade_up"), S::Implemented, TEXT("fades back in and waits (600 ms, assumed)"), [this, Block](FDinkCommandContext&)
	{
		FadeTarget = 0.f;
		return Block(EDinkBlock::Time, Story->GetNowMs() + FadeDurationMs);
	});
	Register(TEXT("fill_screen"), S::Recorded, TEXT("palette fill of the 2D back buffer; the 3D view has nothing to fill"), [this](FDinkCommandContext& Ctx) { return RecordOnly(Ctx); });
	Register(TEXT("show_bmp"), S::Recorded, TEXT("full-screen picture: not shown yet; waits for the skip key like the original"), [Block](FDinkCommandContext&)
	{
		return Block(EDinkBlock::Button);
	});
	Register(TEXT("show_popup"), S::Recorded, TEXT("HD-engine mobile quick-tip image; not part of the remaster UI"), [this](FDinkCommandContext& Ctx) { return RecordOnly(Ctx); });
	Register(TEXT("draw_status"), S::Recorded, TEXT("status bar redraw; no status UI yet (stats are facts)"), [this](FDinkCommandContext& Ctx) { return RecordOnly(Ctx); });

	// ---- Audio (stub) ----
	Register(TEXT("playmidi"), S::Implemented, TEXT("audio stub: logs the music cue"), [this](FDinkCommandContext& Ctx)
	{
		Audio.CurrentMusic = Ctx.Str(0);
		Audio.Cue(TEXT("music:") + Ctx.Str(0));
		return FDinkCommandResult();
	});
	Register(TEXT("stopmidi"), S::Implemented, TEXT("audio stub: logs the music stop"), [this](FDinkCommandContext&)
	{
		Audio.CurrentMusic.Reset();
		Audio.Cue(TEXT("music:stop"));
		return FDinkCommandResult();
	});
	Register(TEXT("stopcd"), S::Implemented, TEXT("audio stub: logs the (legacy CD) music stop"), [this](FDinkCommandContext&)
	{
		Audio.Cue(TEXT("cd:stop"));
		return FDinkCommandResult();
	});
	Register(TEXT("playsound"), S::Implemented, TEXT("audio stub: logs the sound cue (number, speed, sprite, repeat)"), [this](FDinkCommandContext& Ctx)
	{
		Audio.Cue(FString::Printf(TEXT("sound:%s speed=%d random=%d sprite=%d repeat=%d"), *Ctx.Str(0), Ctx.Int(1), Ctx.Int(2), Ctx.Int(3), Ctx.Int(4)));
		return FDinkCommandResult();
	});

	// ---- Inventory and stats ----
	Register(TEXT("add_item"), S::Implemented, TEXT("UDinkInventoryComponent::AddItem(script name), then the item script's `pickup` in a new instance (D:6915)"), [this](FDinkCommandContext& Ctx)
	{
		Story->GetGameplay()->AddItem(FName(*Ctx.Str(0)), false);
		return FDinkCommandResult();
	});
	Register(TEXT("add_magic"), S::Implemented, TEXT("UDinkInventoryComponent::AddMagic(script name), then the spell script's `pickup` (D:6940)"), [this](FDinkCommandContext& Ctx)
	{
		Story->GetGameplay()->AddItem(FName(*Ctx.Str(0)), true);
		return FDinkCommandResult();
	});
	Register(TEXT("kill_this_item"), S::Implemented, TEXT("removes that item: `holdingdrop` and `disarm` if armed, then `drop` (kill_cur_item_script, D:1505)"), [this](FDinkCommandContext& Ctx)
	{
		Story->GetGameplay()->KillThisItem(FName(*Ctx.Str(0)));
		return FDinkCommandResult();
	});
	Register(TEXT("kill_cur_item"), S::Implemented, TEXT("removes the armed item: its `disarm`, then `holdingdrop` and `drop`; the calling script stops (D:1480, D:7801)"), [this](FDinkCommandContext& Ctx)
	{
		UDinkGameplay* Game = Story->GetGameplay();
		const bool bSelf = Game->GetWeaponInstance() == Ctx.Instance.Id;
		Game->KillCurItem();
		FDinkCommandResult R;
		// Called from the armed item's own `use` (item-nut): the original runs that script's `disarm`
		// (kill_this_task) inside the call; here the instance ends.
		R.bEndScript = bSelf;
		R.bStopProcedure = !bSelf;
		return R;
	});
	Register(TEXT("arm_weapon"), S::Implemented, TEXT("`disarm` of the armed item, then `arm` of the item in slot &cur_weapon (1-based) in a new instance (D:7850)"), [this](FDinkCommandContext&)
	{
		Story->GetGameplay()->ArmWeapon();
		return FDinkCommandResult();
	});
	Register(TEXT("add_exp"), S::Implemented, TEXT("experience for the player whoever dealt the last hit (add_exp(num, sprite, true), D:615), capped at 99,999"), [this](FDinkCommandContext& Ctx)
	{
		Story->GetGameplay()->AddExp(Ctx.Int(0), Ctx.Int(1), /*bAlways*/ true);
		return FDinkCommandResult();
	});

	// ---- System ----
	Register(TEXT("save_game"), S::Implemented, TEXT("UDinkSaveSubsystem::SaveToSlot(\"dink_save<N>\") when a game instance and player exist"), [this](FDinkCommandContext& Ctx)
	{
		UWorld* World = GetWorld();
		UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
		if (UDinkSaveSubsystem* Saves = GI ? GI->GetSubsystem<UDinkSaveSubsystem>() : nullptr)
		{
			Saves->SaveToSlot(SaveSlotName(Ctx.Int(0)), GetActor(1), GetCurrentScreen());
		}
		return FDinkCommandResult();
	});
	Register(TEXT("load_game"), S::Implemented, TEXT("UDinkSaveSubsystem::LoadFromSlot(\"dink_save<N>\"); ends the script"), [this](FDinkCommandContext& Ctx)
	{
		UWorld* World = GetWorld();
		UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
		const int32 Slot = Ctx.Int(0);
		FDinkCommandResult R;
		R.bEndScript = true;
		if (UDinkSaveSubsystem* Saves = GI ? GI->GetSubsystem<UDinkSaveSubsystem>() : nullptr)
		{
			if (UGameplayStatics::DoesSaveGameExist(SaveSlotName(Slot), 0))
			{
				// Deferred: loading replaces every script instance, including this one.
				TWeakObjectPtr<UDinkSaveSubsystem> WeakSaves = Saves;
				TWeakObjectPtr<AActor> Player = GetActor(1);
				World->GetTimerManager().SetTimerForNextTick([WeakSaves, Player, Slot]()
				{
					if (UDinkSaveSubsystem* S = WeakSaves.Get())
					{
						S->LoadFromSlot(SaveSlotName(Slot), Player.Get());
					}
				});
			}
		}
		return R;
	});
	Register(TEXT("kill_game"), S::Recorded, TEXT("quits the game in the original; logged and the script ends (not wired to quitting)"), [](FDinkCommandContext&)
	{
		UE_LOG(LogDinkDirector, Log, TEXT("kill_game: the original quits here"));
		FDinkCommandResult R;
		R.bEndScript = true;
		return R;
	});
	Register(TEXT("restart_game"), S::Implemented, TEXT("deferred fresh-game world reload; initial facts, placements and scripts restored; ends the script"), [this](FDinkCommandContext&)
	{
		// Resetting now would invalidate this executing script. The story applies
		// the request at its next Advance boundary, then waits for the new world.
		Story->RequestRestartGame();
		FDinkCommandResult R;
		R.bEndScript = true;
		return R;
	});
	Register(TEXT("activate_bow"), S::Recorded, TEXT("bow charge (combat layer not built): yields one frame"), [this, Block](FDinkCommandContext&)
	{
		return Block(EDinkBlock::Frame, Story->GetNowMs());
	});
	Register(TEXT("init"), S::Recorded, TEXT("dink.ini line that redefines a 2D sequence: recorded for the animation layer"), [this](FDinkCommandContext& Ctx)
	{
		InitLines.AddUnique(Ctx.Str(0));
		UE_LOG(LogDinkDirector, Verbose, TEXT("init \"%s\" recorded"), *Ctx.Str(0));
		return FDinkCommandResult();
	});
	for (const TCHAR* Name : { TEXT("set_mode"), TEXT("stop_entire_game"), TEXT("reset_timer"), TEXT("set_button") })
	{
		Register(Name, S::Recorded, TEXT("engine/menu mode switch of the 2D title and escape screens; no equivalent yet"), [this](FDinkCommandContext& Ctx) { return RecordOnly(Ctx); });
	}
	Register(TEXT("set_dink_speed"), S::Recorded, TEXT("Dink's 2D walk speed (main.c sets 3); the greybox character walks at a fixed 6 m/s; recorded on Dink's sprite"), [this](FDinkCommandContext& Ctx)
	{
		if (Ctx.Int(0) != 0)
		{
			GetDink().Props.Add(TEXT("dinkspeed"), Ctx.Int(0));
		}
		return FDinkCommandResult();
	});
	for (const TCHAR* Name : { TEXT("debug"), TEXT("preload_seq"), TEXT("load_sound"), TEXT("make_global_int") })
	{
		Register(Name, S::Recorded, TEXT("engine no-op (dev log / asset preload); the converter writes it as an Ink comment, so it never arrives"), [this](FDinkCommandContext& Ctx) { return RecordOnly(Ctx); });
	}
	for (const TCHAR* Name : { TEXT("freeeze"), TEXT("unfreeeze") })
	{
		Register(Name, S::Recorded, TEXT("misspelling the engine ignores; only reachable behind a fix switch that stays false"), [this](FDinkCommandContext& Ctx) { return RecordOnly(Ctx); });
	}
}

FDinkCommandResult UDinkDirector::Execute(FDinkScriptInstance& Instance, const FDinkStoryLine& Line)
{
	++CommandsRun;
	CommandCounts.FindOrAdd(Line.Command)++;
	const FDinkCommandDef* Def = Commands.Find(Line.Command);
	if (!Def)
	{
		Story->ReportError(FString::Printf(TEXT("unknown director command '%s' in %s.%s (source line %d): \"%s\""),
			*Line.Command.ToString(), *Instance.Script.ToString(), *Instance.Procedure.ToString(), Line.SourceLine, *Line.Text));
		return FDinkCommandResult();
	}
	FDinkCommandContext Ctx{ Instance, Line, Line.Command };
	FDinkCommandResult Result = Def->Handler(Ctx);
	if (Story->bInstantMode && Result.Block != 0)
	{
		if (static_cast<EDinkBlock>(Result.Block) == EDinkBlock::Move)
		{
			FinishAllMoves();
		}
	}
	return Result;
}

// ---------------------------------------------------------------------------------------------
// Externals

void UDinkDirector::BindExternals(FDinkInkStory& InkStory)
{
	ExternalNames.Reset();
	auto Bind = [this, &InkStory](const TCHAR* Name, FDinkInkStory::FExternal Function)
	{
		ExternalNames.Add(Name);
		InkStory.BindExternal(Name, MoveTemp(Function));
	};
	auto Arg = [](const TArray<Ink::FValueType>& Args, int32 I) { return Args.IsValidIndex(I) ? FDinkInkStory::ArgToInt(Args[I]) : 0; };
	auto ArgS = [](const TArray<Ink::FValueType>& Args, int32 I) { return Args.IsValidIndex(I) ? FDinkInkStory::ArgToString(Args[I]) : FString(); };

	Bind(TEXT("buttoninfo"), [](const TArray<Ink::FValueType>& Args)
	{
		// The original fills &buttoninfo with the key bound to button N (escape menu); no key-binding UI yet.
		return StringResult(FString::Printf(TEXT("Button %d"), Args.Num() > 0 ? FDinkInkStory::ArgToInt(Args[0]) : 0));
	});
	Bind(TEXT("savegameinfo"), [Arg](const TArray<Ink::FValueType>& Args)
	{
		const int32 Slot = Arg(Args, 0);
		const bool bExists = UGameplayStatics::DoesSaveGameExist(SaveSlotName(Slot), 0);
		return StringResult(bExists ? FString::Printf(TEXT("Slot %d - Saved game"), Slot) : FString::Printf(TEXT("Slot %d - Empty"), Slot));
	});
	Bind(TEXT("game_exist"), [Arg](const TArray<Ink::FValueType>& Args)
	{
		return IntResult(UGameplayStatics::DoesSaveGameExist(SaveSlotName(Arg(Args, 0)), 0) ? 1 : 0);
	});
	Bind(TEXT("compare_sprite_script"), [this, Arg, ArgS](const TArray<Ink::FValueType>& Args)
	{
		const FDinkSprite* Sprite = FindSprite(Arg(Args, 0));
		return IntResult(Sprite && Sprite->Script.ToString().Equals(ArgS(Args, 1), ESearchCase::IgnoreCase) ? 1 : 0);
	});
	Bind(TEXT("compare_weapon"), [this, ArgS](const TArray<Ink::FValueType>& Args)
	{
		return IntResult(GetInventory()->GetArmedItem().ToString().Equals(ArgS(Args, 0), ESearchCase::IgnoreCase) ? 1 : 0);
	});
	Bind(TEXT("count_item"), [this, ArgS](const TArray<Ink::FValueType>& Args)
	{
		return IntResult(GetInventory()->CountItem(FName(*ArgS(Args, 0).ToLower())));
	});
	Bind(TEXT("count_magic"), [this, ArgS](const TArray<Ink::FValueType>& Args)
	{
		return IntResult(GetInventory()->CountMagic(FName(*ArgS(Args, 0).ToLower())));
	});
	Bind(TEXT("free_items"), [this](const TArray<Ink::FValueType>&) { return IntResult(GetInventory()->NumFreeItemSlots()); });
	Bind(TEXT("free_magic"), [this](const TArray<Ink::FValueType>&) { return IntResult(GetInventory()->NumFreeMagicSlots()); });
	Bind(TEXT("create_sprite"), [this, Arg](const TArray<Ink::FValueType>& Args)
	{
		FDinkScriptInstance* Instance = Story->GetCurrentInstance();
		const int32 Screen = Instance ? InstanceScreen(*Instance) : GetCurrentScreen();
		const int32 Handle = CreateVirtualSprite(Screen, Arg(Args, 0), Arg(Args, 1));
		FDinkSprite& Sprite = Sprites[Handle];
		InitCreatedSprite(Sprite);
		Sprite.Props.Add(TEXT("brain"), Arg(Args, 2));
		Sprite.Props.Add(TEXT("pseq"), Arg(Args, 3));
		Sprite.Props.Add(TEXT("pframe"), Arg(Args, 4));
		SpawnSpriteActor(Sprite);
		return IntResult(Handle);
	});
	Bind(TEXT("get_burn"), [](const TArray<Ink::FValueType>&) { return IntResult(0); }); // the engine returns 0 (D:8974)
	Bind(TEXT("get_last_bow_power"), [](const TArray<Ink::FValueType>&) { return IntResult(0); }); // no bow yet
	Bind(TEXT("get_version"), [](const TArray<Ink::FValueType>&) { return IntResult(DinkVersion); });
	Bind(TEXT("is_base_game"), [](const TArray<Ink::FValueType>&) { return IntResult(1); });
	Bind(TEXT("scripts_used"), [this](const TArray<Ink::FValueType>&)
	{
		int32 Alive = 0;
		for (const TUniquePtr<FDinkScriptInstance>& I : Story->Instances)
		{
			Alive += I->IsAlive() ? 1 : 0;
		}
		return IntResult(Alive);
	});
	Bind(TEXT("get_sprite_with_this_brain"), [this, Arg](const TArray<Ink::FValueType>& Args)
	{
		const int32 Brain = Arg(Args, 0);
		const int32 Except = Arg(Args, 1);
		TArray<int32> Handles;
		Sprites.GetKeys(Handles);
		Handles.Sort();
		for (const int32 H : Handles)
		{
			const FDinkSprite& S = Sprites[H];
			if (H != Except && S.bActive && !S.bText && S.GetProp(TEXT("brain"), INDEX_NONE) == Brain)
			{
				return IntResult(H);
			}
		}
		return IntResult(0);
	});
	Bind(TEXT("random"), [this, Arg](const TArray<Ink::FValueType>& Args)
	{
		// (rand() % range) + base from the gameplay layer's one seedable rand() source (dink.cpp "random").
		return IntResult(Story->GetGameplay()->Random(Arg(Args, 0), Arg(Args, 1)));
	});
	Bind(TEXT("get_rand_sprite_with_this_brain"), [this, Arg](const TArray<Ink::FValueType>& Args)
	{
		const int32 Brain = Arg(Args, 0);
		const int32 Except = Arg(Args, 1);
		TArray<int32> Handles;
		for (const TPair<int32, FDinkSprite>& Pair : Sprites)
		{
			if (Pair.Key != Except && Pair.Value.bActive && !Pair.Value.bText && Pair.Value.GetProp(TEXT("brain"), INDEX_NONE) == Brain)
			{
				Handles.Add(Pair.Key);
			}
		}
		if (Handles.Num() == 0)
		{
			return IntResult(0);
		}
		Handles.Sort();
		return IntResult(Handles[Story->GetGameplay()->RandomModulo(Handles.Num())]); // the (rand() % count + 1)-th (D:9277)
	});
	Bind(TEXT("is_script_attached"), [this, Arg](const TArray<Ink::FValueType>& Args)
	{
		const FDinkScriptInstance* I = Story->FindInstanceForSprite(Arg(Args, 0));
		return IntResult(I ? I->Id : 0);
	});
	Bind(TEXT("inside_box"), [Arg](const TArray<Ink::FValueType>& Args)
	{
		const int32 X = Arg(Args, 0), Y = Arg(Args, 1), L = Arg(Args, 2), T = Arg(Args, 3), R = Arg(Args, 4), B = Arg(Args, 5);
		return IntResult(X >= L && X <= R && Y >= T && Y <= B ? 1 : 0);
	});
	Bind(TEXT("sp"), [this, Arg](const TArray<Ink::FValueType>& Args)
	{
		FDinkScriptInstance* Instance = Story->GetCurrentInstance();
		const int32 Screen = Instance ? InstanceScreen(*Instance) : GetCurrentScreen();
		return IntResult(HandleForPlacement(Screen, Arg(Args, 0)));
	});
	Bind(TEXT("sp_editor_num"), [this, Arg](const TArray<Ink::FValueType>& Args)
	{
		const FDinkSprite* Sprite = FindSprite(Arg(Args, 0));
		return IntResult(Sprite && Sprite->Origin.IsValid() ? Sprite->Origin.Placement : 0);
	});
	for (const TCHAR* Prop : { TEXT("brain"), TEXT("dir"), TEXT("hitpoints"), TEXT("pframe"), TEXT("pseq"), TEXT("target"), TEXT("x"), TEXT("y") })
	{
		const FName PropName(Prop);
		Bind(*FString::Printf(TEXT("sp_%s"), Prop), [this, Arg, PropName](const TArray<Ink::FValueType>& Args)
		{
			return IntResult(SpriteProperty(Story->GetCurrentInstance(), PropName, Arg(Args, 0), Args.Num() > 1 ? Arg(Args, 1) : -1));
		});
	}
}

// ---------------------------------------------------------------------------------------------
// Handle table

FDinkSprite* UDinkDirector::FindSprite(int32 Handle)
{
	if (Handle == 1)
	{
		return &GetDink();
	}
	return Sprites.Find(Handle);
}

const FDinkSprite* UDinkDirector::FindSprite(int32 Handle) const
{
	return Sprites.Find(Handle);
}

FDinkSprite& UDinkDirector::GetDink()
{
	FDinkSprite* Dink = Sprites.Find(1);
	if (!Dink)
	{
		Dink = &Sprites.Add(1);
		Dink->Handle = 1;
		Dink->Screen = GetCurrentScreen();
		Dink->X = 334; // start-1.c: sp_x(1, 334), sp_y(1, 161)
		Dink->Y = 161;
		Dink->Dir = 4;
		Dink->Props.Add(TEXT("speed"), 3);
		Dink->Props.Add(TEXT("brain"), 1);
	}
	if (!Dink->Actor.IsValid())
	{
		if (UWorld* World = GetWorld())
		{
			if (APlayerController* PC = World->GetFirstPlayerController())
			{
				if (APawn* Pawn = PC->GetPawn())
				{
					Dink->Actor = Pawn;
					HandleByActor.Add(Pawn, 1);
					Dink->Screen = GetCurrentScreen();
					SyncSpriteFromActor(*Dink);
					if (UDinkScriptSpriteComponent* Comp = UDinkScriptSpriteComponent::FindOrAdd(Pawn))
					{
						Comp->Handle = 1;
					}
				}
			}
		}
	}
	return *Dink;
}

int32 UDinkDirector::AllocateHandle()
{
	int32 H = 2;
	while (Sprites.Contains(H) || H == HandleNoSprite)
	{
		++H;
	}
	return H;
}

AActor* UDinkDirector::GetActor(int32 Handle) const
{
	if (Handle == 1)
	{
		const_cast<UDinkDirector*>(this)->GetDink();
	}
	const FDinkSprite* Sprite = Sprites.Find(Handle);
	return Sprite ? Sprite->Actor.Get() : nullptr;
}

int32 UDinkDirector::HandleForActor(AActor* Actor)
{
	if (!Actor)
	{
		return 0;
	}
	if (const int32* Existing = HandleByActor.Find(Actor))
	{
		if (Sprites.Contains(*Existing))
		{
			return *Existing;
		}
	}
	if (const UWorld* World = Actor->GetWorld())
	{
		if (const APlayerController* PC = World->GetFirstPlayerController(); PC && PC->GetPawn() == Actor)
		{
			GetDink();
			return 1;
		}
	}
	const UDinkOriginComponent* Origin = UDinkOriginComponent::FindOnActor(Actor);
	int32 Handle = 0;
	if (Origin && Origin->OriginId.IsValid())
	{
		if (const int32* ByOrigin = HandleByOrigin.Find(Origin->OriginId); ByOrigin && Sprites.Contains(*ByOrigin))
		{
			Handle = *ByOrigin;
		}
	}
	if (Handle == 0)
	{
		Handle = AllocateHandle();
		FDinkSprite& New = Sprites.Add(Handle);
		New.Handle = Handle;
		if (Origin)
		{
			New.Origin = Origin->OriginId;
			New.Screen = Origin->OriginId.Screen;
			New.Script = Origin->ScriptName;
			if (UDinkGameplay* Game = Story->GetGameplay())
			{
				Game->InitPlacementSprite(New);
			}
		}
		else
		{
			New.Screen = GetCurrentScreen();
		}
		if (const ADinkPlaceholderActor* Placeholder = Cast<ADinkPlaceholderActor>(Actor))
		{
			New.Props.Add(TEXT("brain"), Placeholder->Brain);
		}
	}
	FDinkSprite& Sprite = Sprites[Handle];
	Sprite.Actor = Actor;
	HandleByActor.Add(Actor, Handle);
	if (Sprite.Origin.IsValid())
	{
		HandleByOrigin.Add(Sprite.Origin, Handle);
	}
	SyncSpriteFromActor(Sprite);
	if (UDinkScriptSpriteComponent* Comp = UDinkScriptSpriteComponent::FindOrAdd(Actor))
	{
		Comp->Handle = Handle;
		Comp->Script = Sprite.Script;
		Comp->Props = Sprite.Props; // map.dat's brain, hitpoints, touch damage... for the AI/animation layers
	}
	return Handle;
}

int32 UDinkDirector::HandleForPlacement(int32 Screen, int32 Placement)
{
	const FDinkOriginId Origin(Screen, Placement);
	if (!Origin.IsValid())
	{
		return 0;
	}
	if (const UDinkWorldStateSubsystem* World = Story->GetWorldState(); World && World->IsPlacementRemoved(Origin))
	{
		return 0;
	}
	if (const int32* Existing = HandleByOrigin.Find(Origin); Existing && Sprites.Contains(*Existing))
	{
		return *Existing;
	}
	if (AActor* Actor = FindPlacementActor(Origin))
	{
		return HandleForActor(Actor);
	}
	// Not an actor in this world (instanced background placement, other map, tests): a virtual sprite.
	const int32 Handle = AllocateHandle();
	FDinkSprite& Sprite = Sprites.Add(Handle);
	Sprite.Handle = Handle;
	Sprite.Origin = Origin;
	Sprite.Screen = Screen;
	if (UDinkGameplay* Game = Story->GetGameplay())
	{
		Game->InitPlacementSprite(Sprite);
	}
	HandleByOrigin.Add(Origin, Handle);
	return Handle;
}

void UDinkDirector::InitCreatedSprite(FDinkSprite& Sprite)
{
	// add_sprite (D:4299): a zeroed sprite with speed 1, timer 33, size 100, hard 1 (so base_walk etc. are 0, dir 0).
	Sprite.Dir = 0;
	Sprite.Props.Add(TEXT("speed"), 1);
	Sprite.Props.Add(TEXT("timing"), 33);
	Sprite.Props.Add(TEXT("size"), 100);
	Sprite.Props.Add(TEXT("hard"), 1);
	for (const TCHAR* Base : { TEXT("base_walk"), TEXT("base_idle"), TEXT("base_attack"), TEXT("base_death"), TEXT("base_hit") })
	{
		Sprite.Props.Add(Base, 0);
	}
}

int32 UDinkDirector::CreateVirtualSprite(int32 Screen, double X, double Y)
{
	const int32 Handle = AllocateHandle();
	FDinkSprite& Sprite = Sprites.Add(Handle);
	Sprite.Handle = Handle;
	Sprite.Screen = Screen;
	Sprite.X = X;
	Sprite.Y = Y;
	Sprite.bSpawned = true;
	return Handle;
}

void UDinkDirector::DeactivateSprite(int32 Handle, int32 ExceptInstanceId, bool bEndScripts)
{
	FDinkSprite* Sprite = FindSprite(Handle);
	if (!Sprite || Handle == 1)
	{
		if (Handle == 1)
		{
			UE_LOG(LogDinkDirector, Log, TEXT("sp_active(1, 0): Dink is not removed"));
		}
		return;
	}
	Sprite->bActive = false;
	Sprite->bMoving = false;
	if (AActor* Actor = Sprite->Actor.Get())
	{
		if (Sprite->bSpawned)
		{
			Actor->Destroy();
		}
		else
		{
			Actor->SetActorHiddenInGame(true);
			Actor->SetActorEnableCollision(false);
		}
	}
	if (Sprite->bText)
	{
		Story->RemoveText(Handle);
	}
	if (!bEndScripts)
	{
		return;
	}
	for (const TUniquePtr<FDinkScriptInstance>& I : Story->Instances)
	{
		if (I->IsAlive() && I->Sprite == Handle && I->AttachedTo != HandleNoSprite)
		{
			if (I->Id == ExceptInstanceId)
			{
				I->bKillPending = true;
			}
			else
			{
				Story->FinishInstance(*I, TEXT("its sprite was removed"));
			}
		}
	}
}

void UDinkDirector::ReleaseScreenSprites(int32 KeepScreen, const TSet<int32>& KeepHandles)
{
	TArray<int32> Remove;
	for (const TPair<int32, FDinkSprite>& Pair : Sprites)
	{
		if (Pair.Key == 1 || KeepHandles.Contains(Pair.Key))
		{
			continue;
		}
		Remove.Add(Pair.Key);
	}
	for (const int32 H : Remove)
	{
		FDinkSprite& Sprite = Sprites[H];
		if (Sprite.bSpawned)
		{
			if (AActor* Actor = Sprite.Actor.Get())
			{
				Actor->Destroy();
			}
		}
		HandleByOrigin.Remove(Sprite.Origin);
		HandleByActor.Remove(Sprite.Actor);
		Sprites.Remove(H);
	}
	GetDink().Screen = KeepScreen;
}

void UDinkDirector::ResetSprites()
{
	for (TPair<int32, FDinkSprite>& Pair : Sprites)
	{
		if (Pair.Value.bSpawned)
		{
			if (AActor* Actor = Pair.Value.Actor.Get())
			{
				Actor->Destroy();
			}
		}
	}
	Sprites.Reset();
	HandleByOrigin.Reset();
	HandleByActor.Reset();
	OriginIndex.Reset();
	OriginIndexWorld.Reset();
	bDinkInputBlocked = false;
}

int32 UDinkDirector::SpriteProperty(FDinkScriptInstance* Instance, FName Prop, int32 Handle, int32 Value)
{
	static const FName X(TEXT("x")), Y(TEXT("y")), Dir(TEXT("dir")), EditorNum(TEXT("editor_num")), Hitpoints(TEXT("hitpoints")),
		Strength(TEXT("strength")), Defense(TEXT("defense")), TouchDamage(TEXT("touch_damage")), NoDraw(TEXT("nodraw")),
		Size(TEXT("size")), Kill(TEXT("kill")), NoTouch(TEXT("notouch")), Seq(TEXT("seq")), Speed(TEXT("speed")), AttackWait(TEXT("attack_wait"));
	FDinkSprite* Sprite = FindSprite(Handle);
	if (!Sprite)
	{
		UE_LOG(LogDinkDirector, Verbose, TEXT("sp_%s(%d, %d): no such sprite"), *Prop.ToString(), Handle, Value);
		return 0;
	}
	AActor* Actor = Sprite->Actor.Get();
	UDinkStatsComponent* Stats = Actor ? Actor->FindComponentByClass<UDinkStatsComponent>() : nullptr;
	// -1 means "read only" except for the setters the engine implements with change_sprite_noreturn
	// (dink.cpp D:5471), which store -1 as a value: touch damage -1 is "touch runs the script",
	// base_walk -1 is "no walk sequence".
	static const TSet<FName> AlwaysWrite = { FName(TEXT("touch_damage")), FName(TEXT("base_walk")), FName(TEXT("base_idle")),
		FName(TEXT("base_attack")), FName(TEXT("base_death")), FName(TEXT("base_hit")), FName(TEXT("mx")), FName(TEXT("my")) };
	if (Value != -1 || AlwaysWrite.Contains(Prop))
	{
		if (Prop == X)
		{
			Sprite->X = Value;
			Sprite->bMoving = false;
			SyncActorToSprite(*Sprite);
		}
		else if (Prop == Y)
		{
			Sprite->Y = Value;
			Sprite->bMoving = false;
			SyncActorToSprite(*Sprite);
		}
		else if (Prop == Dir)
		{
			Sprite->Dir = Value;
			if (UDinkGameplay* Game = Story->GetGameplay(); Game && Handle != 1)
			{
				// sp_dir runs changedir (D:7505): new mx/my and the walk sequence for that direction.
				Game->ChangeDir(*Sprite, Value, Sprite->GetProp(TEXT("base_walk"), -1));
			}
			ApplyDir(*Sprite);
		}
		else if (Prop == AttackWait)
		{
			// sp_attack_wait stores game time + ms (D:9335)
			Sprite->Props.Add(Prop, static_cast<int32>(FMath::Min<double>(Story->GetNowMs() + Value, MAX_int32)));
		}
		else
		{
			Sprite->Props.Add(Prop, Value);
			if (Stats && (Prop == Hitpoints || Prop == Strength || Prop == Defense || Prop == TouchDamage))
			{
				FDinkStats NewStats = Stats->Stats;
				if (Prop == Hitpoints) { NewStats.Life = Value; }
				else if (Prop == Strength) { NewStats.Strength = Value; }
				else if (Prop == Defense) { NewStats.Defense = Value; }
				else { NewStats.TouchDamage = Value; }
				Stats->SetStats(NewStats);
			}
			else if (Prop == NoDraw && Actor && !Sprite->bText)
			{
				Actor->SetActorHiddenInGame(Value != 0);
			}
			else if (Prop == Size && Actor && Value > 0 && Sprite->bSpawned)
			{
				MakeMovable(Actor);
				Actor->SetActorScale3D(FVector(Value / 100.0));
				if (Actor->ActorHasTag(TEXT("DinkScriptHumanoid")))
					if (UDinkArtSubsystem* Art = Actor->GetWorld()->GetSubsystem<UDinkArtSubsystem>()) Art->ApplyScriptCharacter(Actor, Sprite->Script, Value / 100.f);
			}
			else if (Prop == Kill && Value > 0)
			{
				Sprite->KillAtMs = Story->GetNowMs() + Value;
			}
			else if (Prop == NoTouch)
			{
				Sprite->bNoTouch = Value != 0;
			}
			else if (Prop == Seq)
			{
				if (UDinkGameplay* Game = Story->GetGameplay())
				{
					Game->OnSequenceSet(Handle, Value);
					if (Actor && Actor->GetWorld()) if (UDinkCreatureSubsystem* Creatures=Actor->GetWorld()->GetSubsystem<UDinkCreatureSubsystem>()) Creatures->NotifyScriptSprite(Actor,Value);
				}
			}
			else if (Prop == Speed && Handle != 1)
			{
				if (UDinkGameplay* Game = Story->GetGameplay())
				{
					Game->ChangeDir(*Sprite, Sprite->Dir, Sprite->GetProp(TEXT("base_walk"), -1)); // sp_speed runs changedir (D:9118)
				}
			}
		}
		if (UDinkScriptSpriteComponent* Comp = Actor ? UDinkScriptSpriteComponent::FindOrAdd(Actor) : nullptr)
		{
			Comp->Props = Sprite->Props;
			Comp->Dir = Sprite->Dir;
		}
	}
	if (Prop == X)
	{
		return FMath::RoundToInt(Sprite->X);
	}
	if (Prop == Y)
	{
		return FMath::RoundToInt(Sprite->Y);
	}
	if (Prop == Dir)
	{
		return Sprite->Dir;
	}
	if (Prop == EditorNum)
	{
		return Sprite->Origin.IsValid() ? Sprite->Origin.Placement : 0;
	}
	if (Prop == Hitpoints && Stats)
	{
		return Stats->Stats.Life;
	}
	return Sprite->GetProp(Prop);
}

void UDinkDirector::SetFrozen(int32 Handle, bool bFrozen)
{
	FDinkSprite* Sprite = FindSprite(Handle);
	if (!Sprite)
	{
		return;
	}
	Sprite->bFrozen = bFrozen;
	if (UDinkScriptSpriteComponent* Comp = Sprite->Actor.IsValid() ? UDinkScriptSpriteComponent::FindOrAdd(Sprite->Actor.Get()) : nullptr)
	{
		Comp->bFrozen = bFrozen;
	}
	if (Handle == 1)
	{
		APawn* Pawn = Cast<APawn>(Sprite->Actor.Get());
		APlayerController* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
		if (PC && bDinkInputBlocked != bFrozen)
		{
			PC->SetIgnoreMoveInput(bFrozen);
			bDinkInputBlocked = bFrozen;
			// A frozen Dink is carried by script in screen pixels, and the original's pixels reach past the map (a cutscene puts him
			// at y 480 to walk in from below, s2-culg.c:47, `dink_can_walk_off_screen`); there is no ground there, so the pawn would fall
			// out of the world and stay there. No gravity while a script holds him.
			if (const ACharacter* Character = Cast<ACharacter>(Pawn))
			{
				if (UCharacterMovementComponent* Movement = Character->GetCharacterMovement())
				{
					if (bFrozen)
					{
						DinkGravityScale = Movement->GravityScale;
						Movement->GravityScale = 0.f;
						Movement->StopMovementImmediately();
					}
					else
					{
						Movement->GravityScale = DinkGravityScale;
					}
				}
			}
		}
	}
}

// ---------------------------------------------------------------------------------------------
// Movement and coordinates

ADinkScreenVolume* UDinkDirector::FindScreenVolume(int32 Screen) const
{
	UWorld* World = GetWorld();
	const UDinkGreyboxSubsystem* Greybox = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
	return Greybox ? Greybox->FindScreen(Screen) : nullptr;
}

bool UDinkDirector::GetScreenCorners(int32 Screen, FDinkScreenCorners& OutCorners) const
{
	if (const ADinkScreenVolume* Volume = FindScreenVolume(Screen))
	{
		OutCorners = Volume->Corners;
		return true;
	}
	return false;
}

bool UDinkDirector::PixelToWorld(int32 Screen, double X, double Y, FVector& OutWorld) const
{
	FDinkScreenCorners Corners;
	if (!GetScreenCorners(Screen, Corners))
	{
		return false;
	}
	OutWorld = DinkLayout::MapPixelToUnreal(Corners, X - 20.0, Y);
	return true;
}

int32 UDinkDirector::GetCurrentScreen() const
{
	if (UWorld* World = GetWorld())
	{
		if (const UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>())
		{
			if (const ADinkScreenVolume* Screen = Greybox->GetCurrentScreen())
			{
				return Screen->ScreenNumber;
			}
		}
	}
	const UDinkFactSubsystem* Facts = Story ? Story->GetFacts() : nullptr;
	return Facts ? Facts->GetFact(TEXT("player_map")) : 1;
}

int32 UDinkDirector::ScreenAt(const FVector& Location) const
{
	if (UWorld* World = GetWorld())
	{
		if (const UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>())
		{
			if (const ADinkScreenVolume* Screen = Greybox->FindScreenAt(Location))
			{
				return Screen->ScreenNumber;
			}
		}
	}
	return GetCurrentScreen();
}

int32 UDinkDirector::DirFromPixelDelta(double Dx, double Dy)
{
	if (FMath::IsNearlyZero(Dx) && FMath::IsNearlyZero(Dy))
	{
		return 0;
	}
	// 45-degree sectors around east (6), south-east (3), south (2) ...; y grows south.
	const double Angle = FMath::RadiansToDegrees(FMath::Atan2(Dy, Dx));
	const int32 Sector = (FMath::RoundToInt32(Angle / 45.0) + 8) % 8;
	static const int32 Dirs[8] = { 6, 3, 2, 1, 4, 7, 8, 9 };
	return Dirs[Sector];
}

int32 UDinkDirector::DirFromWorld(int32 Screen, const FVector& Location, const FVector& Direction) const
{
	FDinkScreenCorners Corners;
	if (!GetScreenCorners(Screen, Corners))
	{
		return 0;
	}
	double X0 = 0.0, Y0 = 0.0, X1 = 0.0, Y1 = 0.0;
	const FVector Ahead = Location + Direction.GetSafeNormal2D() * 100.0;
	if (!DinkLayout::MetresToMapPixel(Corners, DinkLayout::UnrealToMetres(Location), X0, Y0)
		|| !DinkLayout::MetresToMapPixel(Corners, DinkLayout::UnrealToMetres(Ahead), X1, Y1))
	{
		return 0;
	}
	return DirFromPixelDelta(X1 - X0, Y1 - Y0);
}

int32 UDinkDirector::InstanceScreen(const FDinkScriptInstance& Instance) const
{
	return Instance.Screen > 0 ? Instance.Screen : GetCurrentScreen();
}

void UDinkDirector::SyncActorToSprite(FDinkSprite& Sprite)
{
	AActor* Actor = Sprite.Actor.Get();
	FVector World;
	if (!Actor || !PixelToWorld(Sprite.Screen, Sprite.X, Sprite.Y, World))
	{
		return;
	}
	World.Z = Actor->GetActorLocation().Z;
	MakeMovable(Actor);
	Actor->SetActorLocation(World, /*bSweep*/ false, nullptr, ETeleportType::TeleportPhysics);
}

void UDinkDirector::SyncSpriteFromActor(FDinkSprite& Sprite)
{
	const AActor* Actor = Sprite.Actor.Get();
	if (!Actor)
	{
		return;
	}
	if (Sprite.Screen <= 0)
	{
		Sprite.Screen = GetCurrentScreen();
	}
	FDinkScreenCorners Corners;
	if (!GetScreenCorners(Sprite.Screen, Corners))
	{
		return;
	}
	double MapX = 0.0, MapY = 0.0;
	if (DinkLayout::MetresToMapPixel(Corners, DinkLayout::UnrealToMetres(Actor->GetActorLocation()), MapX, MapY))
	{
		Sprite.X = MapX + 20.0;
		Sprite.Y = MapY;
	}
}

bool UDinkDirector::GetSpriteFacingRotation(const FDinkSprite& Sprite, FQuat& OutRotation) const
{
	FDinkScreenCorners Corners;
	if (!GetScreenCorners(Sprite.Screen, Corners)) { return false; }
	const double Yaw = DinkLayout::LocalEastYawDegrees(Corners, Sprite.X - 20.0, Sprite.Y) + DirAngle(Sprite.Dir);
	OutRotation = FRotator(0.0, Yaw, 0.0).Quaternion();
	return true;
}

void UDinkDirector::ApplyDir(FDinkSprite& Sprite, const FQuat* ValidatedAuthoredFacing)
{
	AActor* Actor = Sprite.Actor.Get();
	if (UDinkScriptSpriteComponent* Comp = Actor ? UDinkScriptSpriteComponent::FindOrAdd(Actor) : nullptr)
	{
		Comp->Dir = Sprite.Dir;
	}
	// Sprite cards and authored furniture retain their presentation orientation. Authored
	// humanoids keep the placeholder origin/script actor but turn with the original brain.
	if (!Actor || (Cast<ADinkPlaceholderActor>(Actor) && !Actor->ActorHasTag(TEXT("DinkHumanoid")) && !Actor->ActorHasTag(TEXT("DinkCreature"))))
	{
		return;
	}
	FQuat Facing;
    if (ValidatedAuthoredFacing) Facing = *ValidatedAuthoredFacing;
    else if (!GetSpriteFacingRotation(Sprite, Facing)) return;
	MakeMovable(Actor);
	Actor->SetActorRotation(Facing);
}

void UDinkDirector::StartMove(FDinkSprite& Sprite, int32 Dir, int32 Stop, int32 NoHard)
{
	Sprite.bMoveNoHard = NoHard == 1;
	const FIntPoint V = DirVector(Dir);
	if (V == FIntPoint(0, 0))
	{
		UE_LOG(LogDinkDirector, Log, TEXT("move of sprite %d: direction %d is not a numpad direction; ignored"), Sprite.Handle, Dir);
		return;
	}
	Sprite.Dir = Dir;
	ApplyDir(Sprite);
	Sprite.MoveDir = Dir;
	Sprite.MoveStop = Stop;
	Sprite.MoveElapsedMs = 0.0;
	Sprite.bMoving = true;
	StepMove(Sprite, 0.0); // already past the stop coordinate: done at once, as the engine does
}

bool UDinkDirector::StepMove(FDinkSprite& Sprite, double DeltaMs)
{
	if (!Sprite.bMoving)
	{
		return false;
	}
	const FIntPoint V = DirVector(Sprite.MoveDir);
	const double Speed = FMath::Max(1, Sprite.GetProp(TEXT("speed"), 1)) * PixelsPerSecondPerSpeed;
	Sprite.X += V.X * Speed * DeltaMs / 1000.0;
	Sprite.Y += V.Y * Speed * DeltaMs / 1000.0;
	Sprite.MoveElapsedMs += DeltaMs;
	// The stop coordinate is x for the horizontal and diagonal directions, y for 2 and 8.
	const bool bAlongX = V.X != 0;
	double& Coord = bAlongX ? Sprite.X : Sprite.Y;
	const int32 Sign = bAlongX ? V.X : V.Y;
	if ((Sign > 0 && Coord >= Sprite.MoveStop) || (Sign < 0 && Coord <= Sprite.MoveStop))
	{
		if (DeltaMs > 0.0)
		{
			// Clamp to the stop coordinate; a diagonal walk gives back the same overshoot on the other axis.
			const double Over = Coord - Sprite.MoveStop;
			Coord = Sprite.MoveStop;
			if (bAlongX && V.Y != 0)
			{
				Sprite.Y -= Over * V.Y / V.X;
			}
		}
		Sprite.bMoving = false;
	}
	else if (Sprite.MoveElapsedMs > MaxMoveMs)
	{
		UE_LOG(LogDinkDirector, Log, TEXT("move of sprite %d did not reach %d in %.0f s; stopped"), Sprite.Handle, Sprite.MoveStop, MaxMoveMs / 1000.0);
		Sprite.bMoving = false;
	}
	SyncActorToSprite(Sprite);
	return Sprite.bMoving;
}

bool UDinkDirector::IsMoving(int32 Handle) const
{
	const FDinkSprite* Sprite = Sprites.Find(Handle);
	return Sprite && Sprite->bMoving;
}

void UDinkDirector::FinishAllMoves()
{
	for (TPair<int32, FDinkSprite>& Pair : Sprites)
	{
		FDinkSprite& S = Pair.Value;
		if (S.bMoving)
		{
			const FIntPoint V = DirVector(S.MoveDir);
			const bool bAlongX = V.X != 0;
			const double Delta = (bAlongX ? S.MoveStop - S.X : S.MoveStop - S.Y);
			if (bAlongX)
			{
				S.X = S.MoveStop;
				if (V.Y != 0)
				{
					S.Y += FMath::Abs(Delta) * V.Y; // diagonal: same distance on both axes
				}
			}
			else
			{
				S.Y = S.MoveStop;
			}
			S.bMoving = false;
			SyncActorToSprite(S);
		}
	}
}

void UDinkDirector::Tick(double DeltaMs, double NowMs)
{
	TArray<int32> ToKill;
	for (TPair<int32, FDinkSprite>& Pair : Sprites)
	{
		StepMove(Pair.Value, DeltaMs);
		if (Pair.Value.KillAtMs > 0.0 && NowMs >= Pair.Value.KillAtMs)
		{
			Pair.Value.KillAtMs = 0.0;
			ToKill.Add(Pair.Key);
		}
	}
	for (const int32 H : ToKill)
	{
		DeactivateSprite(H, 0);
	}
	const float Step = static_cast<float>(DeltaMs / FadeDurationMs);
	FadeAlpha = FadeAlpha < FadeTarget ? FMath::Min(FadeTarget, FadeAlpha + Step) : FMath::Max(FadeTarget, FadeAlpha - Step);
}

AActor* UDinkDirector::SpawnSpriteActor(FDinkSprite& Sprite)
{
	UWorld* World = GetWorld();
	FVector Location;
	if (!World || !World->IsGameWorld() || !PixelToWorld(Sprite.Screen, Sprite.X, Sprite.Y, Location))
	{
		return nullptr;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ADinkScriptSpriteActor* Actor = World->SpawnActor<ADinkScriptSpriteActor>(Location + FVector(0, 0, 60), FRotator::ZeroRotator, Params);
	if (Actor)
	{
		Sprite.Actor = Actor;
		HandleByActor.Add(Actor, Sprite.Handle);
		Actor->Sprite->Handle = Sprite.Handle;
		Actor->Sprite->Props = Sprite.Props;
		Actor->Sprite->Script = Sprite.Script;
		Actor->Sprite->Dir = Sprite.Dir;
		if (UDinkArtSubsystem* Art = World->GetSubsystem<UDinkArtSubsystem>())
			Art->ApplyScriptCharacter(Actor, Sprite.Script, Sprite.GetProp(TEXT("size"), 100) > 0 ? Sprite.GetProp(TEXT("size"), 100) / 100.f : 1.f);
		if (Actor->ActorHasTag(TEXT("DinkHumanoid"))) ApplyDir(Sprite);
		if (UDinkCreatureSubsystem* Creatures=World->GetSubsystem<UDinkCreatureSubsystem>()) Creatures->NotifyScriptSprite(Actor,Sprite.GetProp(TEXT("seq")) > 0 ? Sprite.GetProp(TEXT("seq")) : Sprite.GetProp(TEXT("pseq")));
	}
	return Actor;
}

void UDinkDirector::BuildOriginIndex()
{
	UWorld* World = GetWorld();
	if (OriginIndexWorld.Get() == World && OriginIndex.Num() > 0)
	{
		return;
	}
	OriginIndex.Reset();
	OriginIndexWorld = World;
	if (!World)
	{
		return;
	}
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (const UDinkOriginComponent* Origin = UDinkOriginComponent::FindOnActor(*It))
		{
			OriginIndex.Add(Origin->OriginId, *It);
		}
	}
}

AActor* UDinkDirector::FindPlacementActor(const FDinkOriginId& Origin)
{
	BuildOriginIndex();
	const TWeakObjectPtr<AActor>* Found = OriginIndex.Find(Origin);
	return Found ? Found->Get() : nullptr;
}

// ---------------------------------------------------------------------------------------------
// Save

TSharedPtr<FJsonObject> UDinkDirector::SaveState() const
{
	TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetNumberField(TEXT("fadeAlpha"), FadeAlpha);
	Root->SetNumberField(TEXT("fadeTarget"), FadeTarget);
	Root->SetBoolField(TEXT("screenLocked"), bScreenLocked);
	Root->SetStringField(TEXT("music"), Audio.CurrentMusic);
	{
		TArray<TSharedPtr<FJsonValue>> Inits;
		for (const FString& L : InitLines)
		{
			Inits.Add(MakeShared<FJsonValueString>(L));
		}
		Root->SetArrayField(TEXT("init"), Inits);
	}
	TArray<TSharedPtr<FJsonValue>> Array;
	for (const TPair<int32, FDinkSprite>& Pair : Sprites)
	{
		const FDinkSprite& S = Pair.Value;
		TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
		O->SetNumberField(TEXT("handle"), S.Handle);
		O->SetBoolField(TEXT("active"), S.bActive);
		O->SetStringField(TEXT("origin"), S.Origin.IsValid() ? S.Origin.ToString() : FString());
		O->SetNumberField(TEXT("screen"), S.Screen);
		O->SetStringField(TEXT("script"), S.Script.IsNone() ? FString() : S.Script.ToString());
		O->SetNumberField(TEXT("x"), S.X);
		O->SetNumberField(TEXT("y"), S.Y);
		O->SetNumberField(TEXT("dir"), S.Dir);
        if (const AActor* Actor = S.Actor.Get(); Actor && (Actor->ActorHasTag(TEXT("DinkCreature")) || Actor->ActorHasTag(TEXT("DinkHumanoid"))))
        {
            // Logical Dir can lead the safe physical facing by a step near a tight obstacle.
            // Optional presentation metadata leaves classic/virtual and older saves unchanged.
            const FQuat Facing = Actor->GetActorQuat();
            O->SetArrayField(TEXT("authoredFacing"), {
                MakeShared<FJsonValueNumber>(Facing.X), MakeShared<FJsonValueNumber>(Facing.Y),
                MakeShared<FJsonValueNumber>(Facing.Z), MakeShared<FJsonValueNumber>(Facing.W)});
        }
		O->SetBoolField(TEXT("frozen"), S.bFrozen);
		O->SetBoolField(TEXT("spawned"), S.bSpawned);
		O->SetBoolField(TEXT("text"), S.bText);
		O->SetBoolField(TEXT("moving"), S.bMoving);
		O->SetNumberField(TEXT("moveDir"), S.MoveDir);
		O->SetNumberField(TEXT("moveStop"), S.MoveStop);
		O->SetNumberField(TEXT("killAtMs"), S.KillAtMs);
		O->SetNumberField(TEXT("damage"), S.Damage);
		O->SetNumberField(TEXT("lastHit"), S.LastHit);
		O->SetBoolField(TEXT("notouch"), S.bNoTouch);
		O->SetNumberField(TEXT("notouchUntilMs"), S.NoTouchUntilMs);
		O->SetBoolField(TEXT("headless"), S.bHeadless);
		O->SetNumberField(TEXT("waitMs"), S.WaitMs);
		O->SetNumberField(TEXT("moveWaitMs"), S.MoveWaitMs);
		O->SetNumberField(TEXT("frameDelayMs"), S.FrameDelayMs);
		O->SetNumberField(TEXT("seqOrig"), S.SeqOrig);
		O->SetNumberField(TEXT("action"), S.Action);
		O->SetBoolField(TEXT("windingUp"), S.bWindingUp);
		O->SetNumberField(TEXT("windUpUntilMs"), S.WindUpUntilMs);
		O->SetNumberField(TEXT("windUpDir"), S.WindUpDir);
		TSharedRef<FJsonObject> P = MakeShared<FJsonObject>();
		for (const TPair<FName, int32>& Prop : S.Props)
		{
			P->SetNumberField(Prop.Key.ToString(), Prop.Value);
		}
		O->SetObjectField(TEXT("props"), P);
		Array.Add(MakeShared<FJsonValueObject>(O));
	}
	Root->SetArrayField(TEXT("sprites"), Array);
	return Root;
}

void UDinkDirector::LoadState(const TSharedPtr<FJsonObject>& State)
{
	ResetSprites();
	if (!State.IsValid())
	{
		return;
	}
	FadeAlpha = static_cast<float>(State->GetNumberField(TEXT("fadeAlpha")));
	FadeTarget = static_cast<float>(State->GetNumberField(TEXT("fadeTarget")));
	bScreenLocked = State->GetBoolField(TEXT("screenLocked"));
	Audio.CurrentMusic = State->GetStringField(TEXT("music"));
	// Resume a saved explicit track without adding a new classic script cue.
	if (!Audio.CurrentMusic.IsEmpty() && Audio.Playback) Audio.Playback(TEXT("music:") + Audio.CurrentMusic);
	InitLines.Reset();
	const TArray<TSharedPtr<FJsonValue>>* Inits = nullptr;
	if (State->TryGetArrayField(TEXT("init"), Inits))
	{
		for (const TSharedPtr<FJsonValue>& V : *Inits)
		{
			InitLines.Add(V->AsString());
		}
	}
	for (const TSharedPtr<FJsonValue>& V : State->GetArrayField(TEXT("sprites")))
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		FDinkSprite S;
		S.Handle = O->GetIntegerField(TEXT("handle"));
		S.bActive = O->GetBoolField(TEXT("active"));
		FDinkOriginId::Parse(O->GetStringField(TEXT("origin")), S.Origin);
		S.Screen = O->GetIntegerField(TEXT("screen"));
		const FString Script = O->GetStringField(TEXT("script"));
		S.Script = Script.IsEmpty() ? NAME_None : FName(*Script);
		S.X = O->GetNumberField(TEXT("x"));
		S.Y = O->GetNumberField(TEXT("y"));
		S.Dir = O->GetIntegerField(TEXT("dir"));
		S.bFrozen = O->GetBoolField(TEXT("frozen"));
		S.bSpawned = O->GetBoolField(TEXT("spawned"));
		S.bText = O->GetBoolField(TEXT("text"));
		S.bMoving = O->GetBoolField(TEXT("moving"));
		S.MoveDir = O->GetIntegerField(TEXT("moveDir"));
		S.MoveStop = O->GetIntegerField(TEXT("moveStop"));
		S.KillAtMs = O->GetNumberField(TEXT("killAtMs"));
		O->TryGetNumberField(TEXT("damage"), S.Damage);
		O->TryGetNumberField(TEXT("lastHit"), S.LastHit);
		O->TryGetBoolField(TEXT("notouch"), S.bNoTouch);
		O->TryGetNumberField(TEXT("notouchUntilMs"), S.NoTouchUntilMs);
		O->TryGetBoolField(TEXT("headless"), S.bHeadless);
		O->TryGetNumberField(TEXT("waitMs"), S.WaitMs);
		O->TryGetNumberField(TEXT("moveWaitMs"), S.MoveWaitMs);
		O->TryGetNumberField(TEXT("frameDelayMs"), S.FrameDelayMs);
		O->TryGetNumberField(TEXT("seqOrig"), S.SeqOrig);
		O->TryGetNumberField(TEXT("action"), S.Action);
		O->TryGetBoolField(TEXT("windingUp"), S.bWindingUp);
		O->TryGetNumberField(TEXT("windUpUntilMs"), S.WindUpUntilMs);
		O->TryGetNumberField(TEXT("windUpDir"), S.WindUpDir);
		for (const auto& Prop : O->GetObjectField(TEXT("props"))->Values)
		{
			S.Props.Add(FName(*FString(*Prop.Key)), static_cast<int32>(Prop.Value->AsNumber()));
		}
		// Rebind actors: placements by origin, Dink to the player pawn, spawned markers anew.
		if (S.Origin.IsValid())
		{
			HandleByOrigin.Add(S.Origin, S.Handle);
			if (AActor* Actor = FindPlacementActor(S.Origin))
			{
				S.Actor = Actor;
				HandleByActor.Add(Actor, S.Handle);
				bool bPresent = S.bActive;
				if (const ADinkPlaceholderActor* Placement = Cast<ADinkPlaceholderActor>(Actor); Placement && Placement->Vision != 0)
				{
					bPresent &= Story && Story->GetFacts() && Placement->Vision == Story->GetFacts()->GetFact(TEXT("vision"));
				}
				// Restoring a consumed pickup or dead NPC must not leave its newly authored
				// collision as an invisible blocker. nodraw intentionally only hides the art.
				Actor->SetActorHiddenInGame(!bPresent || S.GetProp(TEXT("nodraw")) != 0);
				Actor->SetActorEnableCollision(bPresent);
                const TArray<TSharedPtr<FJsonValue>>* Facing = nullptr;
                if ((Actor->ActorHasTag(TEXT("DinkCreature")) || Actor->ActorHasTag(TEXT("DinkHumanoid"))) &&
                    O->TryGetArrayField(TEXT("authoredFacing"), Facing) && Facing->Num() == 4)
                {
                    FQuat Rotation((*Facing)[0]->AsNumber(), (*Facing)[1]->AsNumber(), (*Facing)[2]->AsNumber(), (*Facing)[3]->AsNumber());
                    if (!Rotation.ContainsNaN() && Rotation.SizeSquared() > UE_SMALL_NUMBER)
                    {
                        Rotation.Normalize();
                        FVector Location = Actor->GetActorLocation(), PixelLocation;
                        if (PixelToWorld(S.Screen, S.X, S.Y, PixelLocation))
                        { Location.X = PixelLocation.X; Location.Y = PixelLocation.Y; }
                        MakeMovable(Actor);
                        Actor->SetActorTransform(FTransform(Rotation, Location, Actor->GetActorScale3D()), false, nullptr, ETeleportType::TeleportPhysics);
                        if (UDinkScriptSpriteComponent* Comp = UDinkScriptSpriteComponent::FindOrAdd(Actor)) Comp->Dir = S.Dir;
                    }
                }
			}
		}
		const int32 Handle = S.Handle;
		const bool bSpawned = S.bSpawned && S.bActive && !S.bText;
		Sprites.Add(Handle, MoveTemp(S));
		if (bSpawned)
		{
			SpawnSpriteActor(Sprites[Handle]);
		}
	}
	FDinkSprite& Dink = GetDink();
	SetFrozen(1, Dink.bFrozen);
}

UWorld* UDinkDirector::GetWorld() const
{
	return Story ? Story->GetWorld() : nullptr;
}

// ---------------------------------------------------------------------------------------------
// Status table

FString UDinkDirector::BuildStatusTable(const FString& VocabularyCsv, int32* OutImplemented, int32* OutRecorded, int32* OutMissing) const
{
	int32 Implemented = 0, Recorded = 0, Missing = 0;
	TArray<FString> Lines;
	VocabularyCsv.ParseIntoArrayLines(Lines);
	FString Out = TEXT("command,category,uses,form,status,note\n");
	auto Csv = [](const FString& S) { return S.Contains(TEXT(",")) || S.Contains(TEXT("\"")) ? TEXT("\"") + S.Replace(TEXT("\""), TEXT("\"\"")) + TEXT("\"") : S; };
	// Columns: command,category,args,blocking,lines,external_calls,comments,fix_intent,var_writes,scripts,note (the args and note may be quoted).
	auto SplitCsv = [](const FString& Line)
	{
		TArray<FString> F;
		FString Cur;
		bool bQuoted = false;
		for (int32 i = 0; i < Line.Len(); ++i)
		{
			const TCHAR C = Line[i];
			if (C == TEXT('"'))
			{
				if (bQuoted && i + 1 < Line.Len() && Line[i + 1] == TEXT('"')) { Cur.AppendChar(C); ++i; }
				else { bQuoted = !bQuoted; }
			}
			else if (C == TEXT(',') && !bQuoted) { F.Add(Cur); Cur.Reset(); }
			else { Cur.AppendChar(C); }
		}
		F.Add(Cur);
		return F;
	};
	for (int32 i = 1; i < Lines.Num(); ++i)
	{
		const TArray<FString> F = SplitCsv(Lines[i]);
		if (F.Num() < 10)
		{
			continue;
		}
		const FString& Command = F[0];
		const FString& Category = F[1];
		const int32 Uses = FCString::Atoi(*F[4]) + FCString::Atoi(*F[5]) + FCString::Atoi(*F[6]) + FCString::Atoi(*F[7]) + FCString::Atoi(*F[8]);
		FString Form, Status, Note;
		if (Command.StartsWith(TEXT("(line) ")))
		{
			Form = TEXT("spoken line");
			Status = TEXT("implemented");
			Note = Command.Contains(TEXT("stop")) ? TEXT("floating text over the speaker in its colour; blocks until timed out (strlen x 77 ms, min 2700) or skipped")
				: TEXT("floating text over the speaker in its colour; does not block");
		}
		else if (Command.StartsWith(TEXT("=")))
		{
			Form = TEXT("fact write");
			Status = TEXT("implemented");
			Note = TEXT("Ink VAR mirrored into UDinkFactSubsystem (and from there into the player's UDinkStatsComponent for stats)");
		}
		else if (FCString::Atoi(*F[4]) == 0 && FCString::Atoi(*F[5]) > 0 && ExternalNames.Contains(Command))
		{
			Form = TEXT("external");
			Status = TEXT("implemented");
			Note = TEXT("EXTERNAL function bound with lookaheadSafe = false");
		}
		else if (const FDinkCommandDef* Def = Commands.Find(FName(*Command)))
		{
			Form = FCString::Atoi(*F[4]) > 0 ? TEXT("command") : (FCString::Atoi(*F[6]) > 0 ? TEXT("comment (engine no-op)") : TEXT("fix intent only"));
			Status = Def->Status == EDinkCommandStatus::Implemented ? TEXT("implemented") : TEXT("recorded");
			Note = Def->Note;
			if (ExternalNames.Contains(Command))
			{
				Note += TEXT("; also bound as EXTERNAL (value form)");
			}
		}
		else
		{
			Form = TEXT("?");
			Status = TEXT("not done");
			Note = TEXT("no handler: an occurrence at run time is logged as an unknown-command error");
		}
		if (Status == TEXT("implemented")) { ++Implemented; }
		else if (Status == TEXT("recorded")) { ++Recorded; }
		else { ++Missing; }
		Out += FString::Printf(TEXT("%s,%s,%d,%s,%s,%s\n"), *Csv(Command), *Csv(Category), Uses, *Csv(Form), *Status, *Csv(Note));
	}
	if (OutImplemented) { *OutImplemented = Implemented; }
	if (OutRecorded) { *OutRecorded = Recorded; }
	if (OutMissing) { *OutMissing = Missing; }
	return Out;
}
