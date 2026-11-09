// Dink.Gameplay.Probe.Stonebrook: a scripted playthrough of Stonebrook in PIE on the generated greybox,
// from a new game, using only what a player can do: walk (teleport stands in for walking), talk (the E
// key's TryTalk), attack (the F key's PlayerAttack), touch (standing on a sprite), arm an item (the
// inventory screen's stand-in) and skip text. No fact is written by the probe. It advances &story as
// far as the wired systems allow and writes where and why it stopped to
// Saved/Narrative/stonebrook_probe.txt (and every event of the run, in game time, to stonebrook_probe_trace.txt).
// The stopping point is the result; the test fails only when it stops earlier than the last recorded run (a
// regression). Deterministic: the editor runs a fixed 60 Hz step during the probe and every probe timing (step
// timeouts, retries, punch cadence, walking) is game time, so seed 1997 plays the same game in every run.

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"
#include "UObject/Package.h"
#include "DinkFactSubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkInventoryComponent.h"
#include "DinkSaveSubsystem.h"
#include "DinkStatsComponent.h"
#include "DinkWorldStateSubsystem.h"
#include "Misc/SecureHash.h"
#include "Kismet/GameplayStatics.h"
#include "DinkStorySubsystem.h"
#include "DinkOriginComponent.h"
#include "EngineUtils.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"
#include "UObject/UObjectIterator.h"
#include "AssetCompilingManager.h"
#if WITH_EDITOR
#include "Editor.h"
#include "FileHelpers.h"
#endif
#include "GameFramework/Pawn.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/WorldSettings.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#if WITH_EDITOR
#include "Tests/AutomationEditorCommon.h"
#endif
#include "DinkProbeHold.h"

// The probe is its own module (DinkProbe) so it can be compiled into a Development game target and run in a packaged
// build (Plugins/DinkParity/Docs/packaged_probe.md). Same flags as DinkTestHelpers.h's, which stays in DinkParity (editor-only).
#ifndef DINK_TEST_FLAGS
#define DINK_TEST_FLAGS (EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter)
#endif

namespace DinkProbeTest
{
	// The whole world when imported (the toll bridge, SCR_404, belongs to Goodheart Castle, not to the
	// Stonebrook import), else Stonebrook.
	const TCHAR* WorldMap = TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World");
	const TCHAR* StonebrookMap = TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook");

	/**
	 * The world the probe plays in: the PIE world in the editor, the one game world of a packaged (or -game) process.
	 * A packaged process has a single GameInstance for its whole life, so there is no second PIE-like session: the
	 * chapters run one process each and hand over through their save slots (Scripts/run_packaged_tests.sh).
	 */
	inline UWorld* ProbeWorld()
	{
#if WITH_EDITOR
		if (GEditor)
		{
			return GEditor->PlayWorld.Get();
		}
#endif
		if (GEngine)
		{
			for (const FWorldContext& Context : GEngine->GetWorldContexts())
			{
				if (Context.WorldType == EWorldType::Game && Context.World())
				{
					return Context.World();
				}
			}
		}
		return nullptr;
	}

	/**
	 * The probe runs the editor with a fixed 60 Hz time step: every frame is 1/60 s of game time whatever the machine
	 * does, so script waits, the 100 ms status update, the brains' 60 Hz frames and the probe's own actions fall on the
	 * same frames in every run. (With the real-time step a frame's length was the wall clock's, and where a wait ended
	 * or a monster's step landed relative to the probe's punches and casts changed from run to run.)
	 */
	struct FTimeStepGuard
	{
		bool bSaved = false;
		bool bWasFixed = false;
		double WasDelta = 1.0 / 30.0;
	};
	inline FTimeStepGuard& TimeStep()
	{
		static FTimeStepGuard Guard;
		return Guard;
	}
	inline void UseFixedTimeStep()
	{
		FTimeStepGuard& G = TimeStep();
		if (!G.bSaved)
		{
			G.bSaved = true;
			G.bWasFixed = FApp::UseFixedTimeStep();
			G.WasDelta = FApp::GetFixedDeltaTime();
		}
		FApp::SetFixedDeltaTime(1.0 / 60.0);
		FApp::SetUseFixedTimeStep(true);
	}
	inline void RestoreTimeStep()
	{
		FTimeStepGuard& G = TimeStep();
		if (G.bSaved)
		{
			FApp::SetUseFixedTimeStep(G.bWasFixed);
			FApp::SetFixedDeltaTime(G.WasDelta);
			G.bSaved = false;
		}
	}

	/** What the player keeps between frames (the probe's own memory, not game state). */
	struct FProbeState
	{
		/** One punch per swing (game ms). */
		double NextPunchMs = 0.0;
		/** Game time of Dink's last walking step, and the end of the cast animation (sp_nocontrol). */
		double LastWalkMs = -1.0;
		double HoldUntilMs = 0.0;
		/** Walkable cells of the fight screen: Cell px apart, no hardness within WalkRadius px. */
		int32 GridScreen = 0;
		int32 GridVision = -1;
		TArray<uint8> Free;
		int32 Casts = 0;
		/** OrbitFight: the way round the track (+1 / -1), chosen when the fight begins; 0 = not chosen. */
		int32 OrbitDir = 0;
		double LastLogMs = -1000.0;
				/** A value a step noted when it began (gold, strength...), to compare with what it should become; -1 = none. */
				int32 Mark = -1;
						/** Game time (ms) of the last elixir the probe drank (the dragons' fight): the use is a script, the new life shows a frame later. */
						double LastDrinkMs = -100000.0;
						/** Game time (ms) a wait step ends; -1 = not waiting. */
						double WaitUntilMs = -1.0;
						/** A monster has died and left loot on the screen of the current sweep (so the sweep did something). */
						bool bSawDrop = false;
						/** Game time (ms) the loot of the current sweep began to lie there; -1 = none. */
						double LootSinceMs = -1.0;
	};

	/**
	 * Knobs of KiteFight beyond the cult's (the defaults are the cult's behaviour exactly, so chapter 2 plays as before).
	 * bNoStrike: keep away, never hit anything (two monsters that have targeted each other kill each other: en-bong.c main
	 * targets get_sprite_with_this_brain(9), so a player who stays out of it takes no part). StandDist: with every threat that
	 * far away he stands still. Pull: a neutral sprite he strikes first (a peaceful goblin: its `hit` makes only it hostile).
	 * Wanderers: peaceful brain-16 sprites with touch damage are kept away from. PaceFactor: chasers' pace for the safety
	 * test (a diagonal step moves x and y by the full speed, D:5640: 1.41 times a straight one). FireLeadSec: extra
	 * distance a strike needs, in seconds of the chaser's walking. Goto: walk to these pixels (a drop) when it is safe.
	 */
	struct FFightOpts
	{
		bool bNoStrike = false;
		double StandDist = 0.0;
		int32 Pull = 0;
		bool bWanderers = false;
		double PaceFactor = 1.0;
		double FireLeadSec = 0.0;
		/** Room to the screen edge a strike needs behind him (50: the chasers rush him after a hit). */
		double MinEdge = 50.0;
		/** Strikes only a target with at most this many hitpoints (the first fireball does 6 at least: a lone Bong with 6 left dies of it and cannot hunt him). */
		int32 StrikeMaxHp = MAX_int32;
		/** A chaser that has not targeted Dink hurts by touch only: keep this far (centre to centre) from it instead of its attack reach. 0 = off. */
		double WanderDist = 0.0;
		/** Extra standoff, in seconds of the threat's walking, on top of its attack reach (a wanderer closes 85 px in a second: a bare reach leaves him boxed in). */
		double PaceMarginSec = 0.0;
		/** With no safe cell at all he walks to the reachable cell farthest from the threats instead of standing (cornered, he was touched to death). */
		bool bFlee = false;
		/** Dink keeps inside this rectangle of engine pixels (cells outside it are walls for him), and prefers (OpenWeight) and strikes only from cells with room to run. */
		bool bArena = false;
		FIntRect Arena = FIntRect(0, 0, 640, 400);
		double OpenWeight = 0.0;
		bool bGoto = false;
		/** Go for the Goto spot even when the clock says a threat could reach it first (a wanderer that is not after him: the worst is a touch of 5). */
		bool bForceGoto = false;
		/** A cell the threat cannot walk to (another walled-off part of the screen: SCR_480's pen) has no time limit: he may stand and fire across the fence. */
		bool bWalkReach = false;
		FIntPoint GotoAt = FIntPoint(0, 0);
	};

	/** Knobs of FCtx::OrbitFight (the knights: three chasers that cannot be out-fought on foot). */
	struct FOrbitOpts
	{
		/** The track: an ellipse RadiusX wide and Radius high round (CentreX, CentreY). */
		double CentreX = 322.0, CentreY = 200.0, Radius = 178.0;
		/** Horizontal half-axis (the track is an ellipse Radius px high). */
		double RadiusX = 272.0;
		/** How far ahead on the track (px) Dink aims: he runs the circle at 180 px/s while the chasers, who steer at where he is, settle on a smaller circle inside it. */
		double LookPx = 70.0;
		/** A chaser closer than this (Chebyshev px) is in blow range: stop everything and run from it. */
		double Danger = 95.0;
		/** A charged fireball goes along a row or column through a chaser (px off the line). */
		double LineTol = 14.0;
		/** Seconds the cast animation holds him. */
		double CastHoldSec = 0.25;
		/** He fires only with every chaser at least this far (Chebyshev px): the cast holds him still and they close in meanwhile. */
		double FireClear = 108.0;
	};

	/** Knobs of FCtx::DuelFight (the melee duel). */
	struct FDuelOpts
	{
		/** Pixels kept from the touch box and the blow's box, on top of the capsule. */
		double Margin = 3.0;
		/** The other sprites that hurt by touch get this much more (a wanderer walks 85 px/s on a diagonal). */
		double WanderMargin = 12.0;
		/** The fist must hit with this much to spare (the target walks while the punch is in the air). */
		double FistMargin = 4.0;
		/**
		 * A monster's attack cannot begin before its attack_wait: a punch (the 0.4 s lock) plus the step out of the blow's box (0.2 s) plus
		 * 60 ms must fit between now and the blow, which lands (frames before the special one x frame delay) after the attack starts. 0 = from
		 * the monster's own animation: 660 ms less that delay (gs 385, gh 285, Mog 410).
		 */
		double GateMs = 0.0;
		/** Hit it at range with a charged fireball while it is farther than this (Chebyshev px); 0 = never. */
		double CastFrom = 0.0;
		/**
		 * The other sprites that hurt by touch (the goblins still walking about: a punch that reaches one makes it hostile too, and its
		 * touch is 8 a time; a goblin sitting down shows a picture whose hardbox is 124 px wide). Each is a chaser of pace speed x 1000 / timing
		 * (x1.42 on a diagonal): he only goes to, and strikes from, cells no such sprite reaches before he has walked there and stood for HoldSec
		 * (0.7 s: the punch locks him 0.4 s), prefers cells with time to spare, and with one that could reach him within FleeSec he walks to the
		 * nearest cell that is safe by that clock first.
		 */
		/** Pull a peaceful target with a fireball first (Pull in the step: brain 16). */
		bool bPull = true;
		/**
		 * The target never swings (the Joppa dragons, brain 10, cast `harm` from where they stand: en-drag.c `attack`): there is no blow's box to keep out
		 * of, so every cell is safe from it; only its touch box (touch_damage) and the other sprites remain. Off = the melee duel of chapter 7 exactly.
		 */
		bool bCaster = false;
		/**
		 * Do not strike, wait or cast within AvoidR px (Chebyshev) of this point: the last goblin's death starts Mog's scene (s3-mog.c: Dink
		 * frozen for ~5 s, Mog created at 317,301 with touch damage 8), and a Dink frozen next to him is touched every 0.4 s. 0 = off.
		 */
		double AvoidX = 0.0, AvoidY = 0.0, AvoidR = 0.0;
		double FleeSec = 1.3;
		/** Look-ahead (s) at the monster walking on along its heading when standing, and (HoldSec - 0.1) when striking. */
		double TouchSec = 0.35;
		double HoldSec = 0.9;
		/** Stand this far (Chebyshev px) from the monster while nothing can be hit (its attack starts inside sp_distance). */
		double StageCheb = 60.0;
		int32 Range = 0;
		/** Log the choice every this many ms. */
		double LogMs = 100.0;
	};

	/** Knobs of FCtx::SquadFight (several hostile monsters at once: the three knights of SCR_521). */
	struct FSquadOpts
	{
		/** Pixels kept from the touch boxes and the blows' boxes, on top of the capsule. */
		double Margin = 3.0;
		/** The fist must hit with this much to spare. */
		double FistMargin = 4.0;
		/** A monster whose attack_wait is this far ahead (ms) cannot attack within a punch and a step out: 0 = from its own animation (660 less the blow delay). */
		double GateMs = 0.0;
		/** Hit with a charged fireball along a clear row or column while every monster is farther than this (Chebyshev px); 0 = never. */
		double CastFrom = 0.0;
		/** Look-ahead (s) at a monster walking on along its heading when standing, and (HoldSec - 0.1) when striking. */
		double TouchSec = 0.35;
		double HoldSec = 0.9;
		/** Wait this far (Chebyshev px) from the nearest monster outside every blow's box: its attack starts inside sp_distance, so it swings (and the others around it are in its way). */
		double BaitCheb = 58.0;
		/** Strike at all (fists); false = only bait, dodge and cast. */
		bool bStrike = true;
		int32 Range = 0;
		/** Log the choice every this many ms. */
		double LogMs = 100.0;
	};

	struct FCtx
	{
		FProbeState* P = nullptr;
		UWorld* World = nullptr;
		APawn* Pawn = nullptr;
		UDinkStorySubsystem* S = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* G = nullptr;
		UDinkGreyboxSubsystem* GB = nullptr;
		UDinkFactSubsystem* F = nullptr;

		int32 Fact(const TCHAR* N) const { return F->GetFact(N); }
		bool Idle() const { return !D->GetDink().bFrozen && !S->GetActiveMenu(); }
		/** Time dilation (slomo): the story clock follows the world's. Only while nothing is fought. */
		void Dilate(float Factor) const { UGameplayStatics::SetGlobalTimeDilation(World, Factor); }
		bool Busy() const
		{
			for (const TUniquePtr<FDinkScriptInstance>& I : S->GetInstances())
			{
				if (I->State == EDinkInstanceState::Blocked && I->Block != EDinkBlock::Button)
				{
					return true;
				}
			}
			return false;
		}
		bool OnScreen(int32 Screen) const
		{
			const ADinkScreenVolume* V = GB->GetCurrentScreen();
			return V && V->ScreenNumber == Screen && Fact(TEXT("player_map")) == Screen;
		}
		/** Teleport (walking stand-in) to engine pixel X/Y (with the 20 px bar) on Screen, or the nearest free spot around it. */
		bool Goto(int32 Screen, double X, double Y) const
		{
			const ADinkScreenVolume* Destination = GB->FindScreen(Screen);
			const UCapsuleComponent* Capsule = Pawn ? Pawn->FindComponentByClass<UCapsuleComponent>() : nullptr;
			if (!Destination || !Capsule)
			{
				return false;
			}
			// A successful TeleportTo can synchronously overlap an exit and arrive on another
			// screen. Reject real trigger/capsule intersections before trying a candidate;
			// keep ordinary blocking collision and warp handling authoritative.
			TArray<const UDinkWarpComponent*> Exits;
			for (TObjectIterator<UDinkWarpComponent> It; It; ++It)
			{
				if (It->GetWorld() == World && It->SourceScreen == Screen && It->bTriggerEnabled &&
					It->IsQueryCollisionEnabled() && It->GetGenerateOverlapEvents())
				{
					Exits.Add(*It);
				}
			}
			const FCollisionShape Shape = FCollisionShape::MakeCapsule(
				Capsule->GetScaledCapsuleRadius() + 1.f, Capsule->GetScaledCapsuleHalfHeight() + 1.f);
			const auto TouchesExit = [&](const FVector& Position)
			{
				for (const UDinkWarpComponent* Exit : Exits)
				{
					if (Exit->OverlapComponent(Position, Capsule->GetComponentQuat(), Shape)) { return true; }
				}
				return false;
			};
			for (int32 Ring = 0; Ring <= 8; ++Ring)
			{
				for (int32 K = 0; K < (Ring == 0 ? 1 : 8); ++K)
				{
					const double A = K * PI / 4.0;
					const double Px = X + Ring * 12.0 * FMath::Cos(A);
					const double Py = Y + Ring * 12.0 * FMath::Sin(A);
					if (Px <= 25.0 || Px >= 615.0 || Py <= 5.0 || Py >= 395.0) { continue; }
					const FVector Target = Destination->MapPixelToWorld(Px - 20.0, Py) +
						FVector(0.0, 0.0, Capsule->GetScaledCapsuleHalfHeight() + 2.0);
					if (TouchesExit(Target) || !GB->GotoScreen(Screen, Px - 20.0, Py)) { continue; }
					// TeleportTo has processed overlaps now. Check the actual physical screen,
					// rather than the cached screen/facts which update on the next normal tick.
					const ADinkScreenVolume* Arrived = GB->FindScreenAt(Pawn->GetActorLocation());
					if (Arrived == Destination && !TouchesExit(Capsule->GetComponentLocation())) { return true; }
				}
			}
			return false;
		}
		void Face(int32 Screen, double X, double Y, int32 Dir) const
		{
			static const FIntPoint V[10] = { {0,0}, {-1,1}, {0,1}, {1,1}, {-1,0}, {0,0}, {1,0}, {-1,-1}, {0,-1}, {1,-1} };
			FVector A, B;
			if (D->PixelToWorld(Screen, X, Y, A) && D->PixelToWorld(Screen, X + V[Dir].X * 20.0, Y + V[Dir].Y * 20.0, B))
			{
				Pawn->SetActorRotation(FRotator(0.0, (B - A).Rotation().Yaw, 0.0));
			}
		}
		/** Stands Gap px west of the sprite's hardbox (or on it), facing east (6). */
		bool StandBy(int32 Handle, int32 Gap, bool bOnIt = false) const
		{
			const FDinkSprite* T = D->FindSprite(Handle);
			int32 L = 0, Tp = 0, R = 0, B = 0;
			if (!T)
			{
				return false;
			}
			const double X = bOnIt ? T->X : (G->GetHardbox(*T, L, Tp, R, B) ? L - Gap : T->X - Gap);
			const double Y = T->Y;
			Goto(T->Screen, X, Y);
			Face(T->Screen, X, Y, 6);
			return true;
		}
		int32 Placement(int32 Screen, int32 Index) const { return D->HandleForPlacement(Screen, Index); }
		/**
		 * A player's spacing in a fight: stand Gap px west (or east, if that spot is hard) of the sprite on its
		 * row, face it and punch. A Bonca attacks inside 50 px and its reach ends at 47; Dink's fist reaches 62.
		 */
		bool KiteAndPunch(int32 Handle, int32 Gap, bool bPunch = true) const
		{
			const FDinkSprite* T = D->FindSprite(Handle);
			if (!T || !T->bActive)
			{
				return false;
			}
			const int32 X = FMath::RoundToInt32(T->X), Y = FMath::RoundToInt32(T->Y);
			// West, east, then (cornered) the far side of the screen: never within its touch box.
			bool bPlaced = false;
			bool bWest = true;
			for (const int32 Side : { -1, 1 })
			{
				const double Px = X + Side * Gap;
				if (Px > 25.0 && Px < 615.0 && Clear(T->Screen, FMath::RoundToInt32(Px), Y) && GB->GotoScreen(T->Screen, Px - 20.0, Y))
				{
					G->SyncDinkFromActor();
					const FDinkSprite& Dk = D->GetDink();
					if (FMath::Abs(Dk.X - Px) < 6.0 && FMath::Abs(Dk.Y - Y) < 6.0)
					{
						bPlaced = true;
						bWest = Side < 0;
						Face(T->Screen, Px, Y, bWest ? 6 : 4);
						break;
					}
				}
			}
			if (!bPlaced)
			{
				// Back off to the farthest clear spot and let it come.
				const FIntPoint Spots[] = { {X < 320 ? 520 : 120, Y}, {X < 320 ? 520 : 120, Y < 200 ? 300 : 100}, {320, Y < 200 ? 300 : 100} };
				for (const FIntPoint& Spot : Spots)
				{
					if (Clear(T->Screen, Spot.X, Spot.Y) && GB->GotoScreen(T->Screen, Spot.X - 20.0, Spot.Y))
					{
						break;
					}
				}
				return true;
			}
			G->SyncDinkFromActor();
			S->AddEvent(TEXT("game"), FString::Printf(TEXT("probe: Dink %.0f,%.0f life %d; %d at %d,%d hp %d target %d seq %d"), D->GetDink().X, D->GetDink().Y,
				Fact(TEXT("life")), Handle, X, Y, T->GetProp(TEXT("hitpoints")), T->GetProp(TEXT("target")), T->GetProp(TEXT("seq"))));
			// One punch per swing: the original lets Dink attack again only when the punch animation is over.
			// (This was a function-level static that outlived the PIE session: leftover state between runs.)
			if (!bPunch)
			{
				return true;
			}
			if (S->GetNowMs() >= P->NextPunchMs && ArmFists())
			{
				G->PlayerAttack();
				P->NextPunchMs = S->GetNowMs() + 450.0;
			}
			return true;
		}

		// ---- A ranged fight on foot (Jack): walk at Dink's speed, keep clear of the chaser, cast along a clear line ----

		static constexpr int32 Cell = 6;
		static constexpr int32 Cols = 100; // engine x 20..619
		static constexpr int32 Rows = 67;  // y 0..401
		static constexpr int32 WalkRadius = 10;
		/** Dink walks dinkspeed 3 px per 60 Hz frame (dink.cpp D:17311-17318): 180 px/s. */
		static constexpr double WalkPxPerMs = 0.18;

		static FIntPoint CellCentre(int32 I) { return FIntPoint(20 + Cell / 2 + (I % Cols) * Cell, Cell / 2 + (I / Cols) * Cell); }
		static int32 CellAt(double X, double Y)
		{
			const int32 Cx = FMath::Clamp(FMath::FloorToInt32((X - 20.0) / Cell), 0, Cols - 1);
			const int32 Cy = FMath::Clamp(FMath::FloorToInt32(Y / Cell), 0, Rows - 1);
			return Cy * Cols + Cx;
		}
		void BuildGrid(int32 Screen) const
		{
			const int32 Vision = Fact(TEXT("vision"));
			if (P->GridScreen == Screen && P->GridVision == Vision && P->Free.Num() == Cols * Rows)
			{
				return;
			}
			P->GridScreen = Screen;
			P->GridVision = Vision;
			P->Free.Init(0, Cols * Rows);
			TArray<FBox> Triggers;
			for (TObjectIterator<UDinkWarpComponent> It; It; ++It)
			{
				if (It->GetWorld() == World && It->SourceScreen == Screen && It->bTriggerEnabled)
				{
					Triggers.Add(It->Bounds.GetBox().ExpandBy(FVector(Pawn->GetSimpleCollisionRadius() + 20.0, Pawn->GetSimpleCollisionRadius() + 20.0, 0.0)));
				}
			}
			for (int32 I = 0; I < Cols * Rows; ++I)
			{
				const FIntPoint C = CellCentre(I);
				if (C.X < 20 + WalkRadius || C.X > 619 - WalkRadius || C.Y < WalkRadius || C.Y > 399 - WalkRadius)
				{
					continue;
				}
				bool bFree = true;
				for (int32 Dy = -WalkRadius; Dy <= WalkRadius && bFree; Dy += 4)
				{
					for (int32 Dx = -WalkRadius; Dx <= WalkRadius && bFree; Dx += 4)
					{
						bFree = G->GetHard(Screen, C.X + Dx, C.Y + Dy) == 0;
					}
				}
				// Walking into a warp trigger (the door, the stairs) leaves the screen, and with it the fight; the
				// trigger reaches past its hardbox, so ask the world for the real boxes (plus the capsule).
				if (bFree)
				{
					FVector At;
					if (D->PixelToWorld(Screen, C.X, C.Y, At))
					{
						for (const FBox& Box : Triggers)
						{
							bFree = bFree && !(At.X >= Box.Min.X && At.X <= Box.Max.X && At.Y >= Box.Min.Y && At.Y <= Box.Max.Y);
						}
					}
				}
				P->Free[I] = bFree ? 1 : 0;
			}
		}
		/** Walking distance (px) from Start over free cells, 8 neighbours; Dist < 0 = unreachable. Parent for paths. */
		void WalkDistances(int32 Start, double StartCost, TArray<double>& Dist, TArray<int32>* Parent) const
		{
			Dist.Init(-1.0, Cols * Rows);
			if (Parent)
			{
				Parent->Init(INDEX_NONE, Cols * Rows);
			}
			// Start from the nearest free cell (the sprite may stand closer to a wall than WalkRadius).
			if (!P->Free[Start])
			{
				int32 Best = INDEX_NONE;
				double BestD = 0.0;
				const FIntPoint S0 = CellCentre(Start);
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (P->Free[I])
					{
						const double Dd = FVector2D::Distance(FVector2D(CellCentre(I)), FVector2D(S0));
						if (Best == INDEX_NONE || Dd < BestD)
						{
							Best = I;
							BestD = Dd;
						}
					}
				}
				if (Best == INDEX_NONE)
				{
					return;
				}
				StartCost += BestD;
				Start = Best;
			}
			typedef TPair<double, int32> FNode;
			TArray<FNode> Heap;
			Dist[Start] = StartCost;
			Heap.HeapPush(FNode(StartCost, Start), [](const FNode& A, const FNode& B) { return A.Key < B.Key; });
			while (Heap.Num() > 0)
			{
				FNode N;
				Heap.HeapPop(N, [](const FNode& A, const FNode& B) { return A.Key < B.Key; });
				if (N.Key > Dist[N.Value] + 1e-9)
				{
					continue;
				}
				const int32 Cx = N.Value % Cols, Cy = N.Value / Cols;
				for (int32 Dy = -1; Dy <= 1; ++Dy)
				{
					for (int32 Dx = -1; Dx <= 1; ++Dx)
					{
						const int32 Nx = Cx + Dx, Ny = Cy + Dy;
						if ((Dx == 0 && Dy == 0) || Nx < 0 || Ny < 0 || Nx >= Cols || Ny >= Rows)
						{
							continue;
						}
						const int32 J = Ny * Cols + Nx;
						// Diagonal steps only between free orthogonal neighbours (no cutting wall corners).
						if (!P->Free[J] || (Dx != 0 && Dy != 0 && (!P->Free[Cy * Cols + Nx] || !P->Free[Ny * Cols + Cx])))
						{
							continue;
						}
						const double D2 = N.Key + (Dx != 0 && Dy != 0 ? Cell * UE_SQRT_2 : Cell);
						if (Dist[J] < 0.0 || D2 < Dist[J] - 1e-9)
						{
							Dist[J] = D2;
							if (Parent)
							{
								(*Parent)[J] = N.Value;
							}
							Heap.HeapPush(FNode(D2, J), [](const FNode& A, const FNode& B) { return A.Key < B.Key; });
						}
					}
				}
			}
		}
		/** Hardboxes (inflated by a missile's range, 10) of every live sprite on Screen but Dink and the target. */
		TArray<FIntRect> MissileObstacles(int32 Screen, int32 Target) const
		{
			TArray<FIntRect> Out;
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				const FDinkSprite& O = Pair.Value;
				int32 L, Tp, R, B;
				if (Pair.Key == 1 || Pair.Key == Target || !O.bActive || O.bText || O.Screen != Screen || O.GetProp(TEXT("nohit")) == 1 || O.bNoTouch
					|| !G->GetHardbox(O, L, Tp, R, B))
				{
					continue;
				}
				Out.Add(FIntRect(L - 10, Tp - 10, R + 10, B + 10));
			}
			return Out;
		}
		/**
		 * Would a fireball thrown from (X, Y) towards Dir (2, 4, 6, 8) reach the target's hardbox? item-fb.c starts it 30 px
		 * ahead of Dink for 4 and 6, at Dink for 2 and 8, 6 px a frame; missile_brain (D:14240) ends it on any hardness but
		 * low (2) and on the first live sprite whose hardbox, inflated by its range (10), holds it.
		 */
		bool LineClear(int32 Screen, int32 X, int32 Y, int32 Dir, int32 Target, const TArray<FIntRect>& Obstacles) const
		{
			const FDinkSprite* T = D->FindSprite(Target);
			int32 TL = 0, TT = 0, TR = 0, TB = 0;
			if (!T || !G->GetHardbox(*T, TL, TT, TR, TB))
			{
				return false;
			}
			const FIntRect Box(TL - 10, TT - 10, TR + 10, TB + 10);
			const FIntPoint Step = Dir == 6 ? FIntPoint(6, 0) : Dir == 4 ? FIntPoint(-6, 0) : Dir == 2 ? FIntPoint(0, 6) : FIntPoint(0, -6);
			FIntPoint M(X + (Dir == 6 ? 30 : Dir == 4 ? -30 : 0), Y);
			for (int32 N = 0; N < 120 && M.X > 0 && M.X < 640 && M.Y > -20 && M.Y < 420; ++N, M += Step)
			{
				if (M.X >= Box.Min.X && M.X <= Box.Max.X && M.Y >= Box.Min.Y && M.Y <= Box.Max.Y)
				{
					return true;
				}
				const int32 Hard = G->GetHard(Screen, M.X, M.Y);
				if (Hard != 0 && Hard != 2)
				{
					return false;
				}
				for (const FIntRect& R : Obstacles)
				{
					if (M.X >= R.Min.X && M.X <= R.Max.X && M.Y >= R.Min.Y && M.Y <= R.Max.Y)
					{
						return false;
					}
				}
			}
			return false;
		}
		/** No hardness on the straight way from A to B, 8 px either side (a walker of Jack's width). */
		bool StraightClear(int32 Screen, double Ax, double Ay, double Bx, double By) const
		{
			const FVector2D A(Ax, Ay), B(Bx, By);
			const double Len = FVector2D::Distance(A, B);
			if (Len < 1.0)
			{
				return true;
			}
			const FVector2D Dir = (B - A) / Len;
			const FVector2D Side(-Dir.Y, Dir.X);
			for (double Tt = 0.0; Tt <= Len; Tt += 3.0)
			{
				for (const double Off : { -8.0, 0.0, 8.0 })
				{
					const FVector2D Q = A + Dir * Tt + Side * Off;
					if (G->GetHard(Screen, FMath::RoundToInt32(Q.X), FMath::RoundToInt32(Q.Y)) != 0)
					{
						return false;
					}
				}
			}
			return true;
		}
		/** The pawn's capsule radius in this screen's pixels: the touch box gets it added in 3D (CapsuleMarginPixels). */
		double CapsulePx(int32 Screen, double X, double Y) const
		{
			FVector A, B;
			if (!D->PixelToWorld(Screen, X, Y, A) || !D->PixelToWorld(Screen, X + 10.0, Y, B))
			{
				return 0.0;
			}
			const double CmPerPixel = FVector::Dist2D(A, B) / 10.0;
			return CmPerPixel > KINDA_SMALL_NUMBER ? Pawn->GetSimpleCollisionRadius() / CmPerPixel : 0.0;
		}
		/**
		 * The Jack fight as a player plays it. Dink walks (at most 180 px/s, over walkable pixels) and never comes nearer
		 * the chaser than his touch box plus a margin, choosing spots he reaches well before Jack. With the spell charged
		 * he walks to the nearest such spot level with Jack (row or column) that has a clear line, faces him and casts;
		 * after a cast he stands for the cast animation (item-fb.c sp_nocontrol). While Jack has not been hit yet (he
		 * sits and strolls, brain 16, harmless) and no line is clear, Dink walks up and punches him once to start the fight.
		 */
		/** For every cell the share of free cells within 12 cells (72 px): 1 = open ground, small = a dead end, a corridor, a pocket. */
		void OpennessMap(TArray<float>& Out) const
		{
			TArray<int32> Sum;
			Sum.Init(0, (Cols + 1) * (Rows + 1));
			for (int32 Y = 0; Y < Rows; ++Y)
			{
				for (int32 X = 0; X < Cols; ++X)
				{
					Sum[(Y + 1) * (Cols + 1) + X + 1] = P->Free[Y * Cols + X] + Sum[Y * (Cols + 1) + X + 1] + Sum[(Y + 1) * (Cols + 1) + X] - Sum[Y * (Cols + 1) + X];
				}
			}
			Out.SetNumUninitialized(Cols * Rows);
			for (int32 I = 0; I < Cols * Rows; ++I)
			{
				const int32 Cx = I % Cols, Cy = I / Cols;
				const int32 X0 = FMath::Max(Cx - 12, 0), X1 = FMath::Min(Cx + 13, Cols), Y0 = FMath::Max(Cy - 12, 0), Y1 = FMath::Min(Cy + 13, Rows);
				Out[I] = float(Sum[Y1 * (Cols + 1) + X1] - Sum[Y0 * (Cols + 1) + X1] - Sum[Y1 * (Cols + 1) + X0] + Sum[Y0 * (Cols + 1) + X0]) / 625.0f;
			}
		}
		void KiteAndCast(int32 Handle) const
		{
			const FDinkSprite* T = D->FindSprite(Handle);
			if (!T || !T->bActive)
			{
				return;
			}
			G->SyncDinkFromActor();
			const FDinkSprite& Dk = D->GetDink();
			const int32 Screen = T->Screen;
			const double Now = S->GetNowMs();
			const double Dt = P->LastWalkMs < 0.0 ? 17.0 : FMath::Clamp(Now - P->LastWalkMs, 0.0, 100.0);
			P->LastWalkMs = Now;
			if (Now < P->HoldUntilMs)
			{
				return;
			}
			BuildGrid(Screen);
			TArray<float> Open;
			OpennessMap(Open);
			int32 HL = 0, HT = 0, HR = 0, HB = 0;
			G->GetHardbox(*T, HL, HT, HR, HB);
			const bool bChasing = T->GetProp(TEXT("brain")) == 9;
			// A chaser made by create_sprite has base_attack 0, and pill_brain (D:12933) treats seq 0 as "still attacking":
			// when his walk cycle ends he stands still until a script changes his sequence again (his `hit` does). The
			// original's behaviour, kept; a player can walk past him then.
			const bool bStalled = bChasing && T->GetProp(TEXT("seq")) == 0 && T->GetProp(TEXT("base_attack"), -1) == 0;
			// Touch: Jack's hardbox + 2 px + the capsule radius holds Dink (RunThroughTouchDamageList); keep 20 px more
			// (6 while he stands still).
			const double TouchPx = 2.0 + CapsulePx(Screen, Dk.X, Dk.Y);
			const double Reach = TouchPx + (bStalled ? 6.0 : 20.0);
			auto Clearance = [&](double X, double Y)
			{
				const double Dx = FMath::Max3(HL - X, 0.0, X - HR);
				const double Dy = FMath::Max3(HT - Y, 0.0, Y - HB);
				return FMath::Max(Dx, Dy);
			};
			// Jack walks speed 2 per think at timing 33 (create_sprite's default): about 60 px/s, a third of Dink's pace.
			const double SpeedRatio = 3.0;
			TArray<double> DistJack, DistDink;
			TArray<int32> Parent;
			WalkDistances(CellAt(T->X, T->Y), 0.0, DistJack, nullptr);
			const int32 DinkCell = CellAt(Dk.X, Dk.Y);
			{
				// Dink's paths never pass through Jack's reach (cells too near him are walls for this search).
				const TArray<uint8> Walkable = P->Free;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					const FIntPoint C = CellCentre(I);
					if (P->Free[I] && I != DinkCell && Clearance(C.X, C.Y) < Reach)
					{
						P->Free[I] = 0;
					}
				}
				WalkDistances(DinkCell, 0.0, DistDink, &Parent);
				P->Free = Walkable;
			}
			auto Safe = [&](int32 I)
			{
				const FIntPoint C = CellCentre(I);
				return P->Free[I] && DistDink[I] >= 0.0 && Clearance(C.X, C.Y) >= Reach
					&& (!bChasing || bStalled || DistJack[I] < 0.0 || DistDink[I] / SpeedRatio + 30.0 < DistJack[I]);
			};
			const bool bCharged = Fact(TEXT("magic_cost")) > 0 && Fact(TEXT("magic_level")) >= Fact(TEXT("magic_cost"));
			int32 Goal = INDEX_NONE;
			int32 FireDir = 0;
			const TArray<FIntRect> Obstacles = MissileObstacles(Screen, Handle);
			if (bCharged)
			{
				double Best = 0.0;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (!Safe(I) || Open[I] < 0.4f)
					{
						continue;
					}
					const FIntPoint C = CellCentre(I);
					const double Dx = T->X - C.X, Dy = T->Y - C.Y;
					int32 Dir = 0;
					if (FMath::Abs(Dy) <= 6.0 && FMath::Abs(Dx) <= 260.0)
					{
						Dir = Dx > 0 ? 6 : 4;
					}
					else if (FMath::Abs(Dx) <= 6.0 && FMath::Abs(Dy) <= 260.0)
					{
						Dir = Dy > 0 ? 2 : 8;
					}
					// The fireball makes him a chaser (or wakes him, or sets a stalled one walking again for a cycle): fire from
					// far enough away to walk off before he arrives (70 px past his touch box; 40 when he stands stalled, who
					// covers a walk cycle at a third of Dink's pace).
					if (Dir == 0 || Clearance(C.X, C.Y) < TouchPx + (bStalled ? 40.0 : 70.0) || !LineClear(Screen, C.X, C.Y, Dir, Handle, Obstacles))
					{
						continue;
					}
					if (Goal == INDEX_NONE || DistDink[I] < Best)
					{
						Goal = I;
						Best = DistDink[I];
						FireDir = Dir;
					}
				}
			}
			bool bPunch = false;
			if (Goal == INDEX_NONE && !bChasing && bCharged)
			{
				// Start the fight with the fists: level with him, 26 px off his hardbox (the fist reaches 28 px + 5).
				double Best = 0.0;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					const FIntPoint C = CellCentre(I);
					const bool bWest = FMath::Abs(C.X - (HL - 26)) <= 3, bEast = FMath::Abs(C.X - (HR + 26)) <= 3;
					if (!P->Free[I] || DistDink[I] < 0.0 || FMath::Abs(C.Y - T->Y) > 4.0 || !(bWest || bEast))
					{
						continue;
					}
					if (Goal == INDEX_NONE || DistDink[I] < Best)
					{
						Goal = I;
						Best = DistDink[I];
						FireDir = bWest ? 6 : 4;
						bPunch = true;
					}
				}
			}
			// A walking chaser stalls when his walk cycle ends with his direction unchanged (bStalled): standing still,
			// or walking straight away from him, keeps his direction, so he stops short of Dink.
			const int32 JackDir = UDinkDirector::DirFromPixelDelta(Dk.X - T->X, Dk.Y - T->Y);
			if (Goal == INDEX_NONE && bChasing && !bStalled)
			{
				const double StillToWalk = (11 - FMath::Clamp(T->GetProp(TEXT("frame")), 0, 10)) * 6.0 + 6.0;
				if (Clearance(Dk.X, Dk.Y) - TouchPx > StillToWalk + 8.0)
				{
					return; // stand: he stops before he gets here
				}
			}
			if (Goal == INDEX_NONE)
			{
				// Keep away: the spot Dink reaches first that is farthest (by walking) from the chaser, up to 200 px.
				double Best = -1e9;
				FireDir = 0;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (!Safe(I))
					{
						continue;
					}
					// Out of his way, not across the house: far enough (up to 120 px of walking), as near as possible, and
					// in the direction he is already walking (so his direction holds and he stalls).
					const FIntPoint C = CellCentre(I);
					const double Away = DistJack[I] < 0.0 ? 250.0 : FMath::Min(DistJack[I], 250.0);
					const bool bSameWay = UDinkDirector::DirFromPixelDelta(C.X - T->X, C.Y - T->Y) == JackDir;
					const double Score = Away - 0.3 * DistDink[I] + (bChasing && bSameWay ? 60.0 : 0.0) + 300.0 * Open[I]; // not into a pocket: a dead end is where he was cornered
					if (Score > Best)
					{
						Best = Score;
						Goal = I;
					}
				}
			}
			if (Goal == INDEX_NONE)
			{
				// Nothing is safe by the clock: the reachable cell farthest from him by walking (the walk graph without his zone).
				TArray<double> DistAll;
				WalkDistances(DinkCell, 0.0, DistAll, &Parent);
				double BestFar = -1e9;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (DistAll[I] >= 0.0 && DistJack[I] >= 0.0)
					{
						const double Far = FMath::Min(DistJack[I], 250.0) - 0.1 * DistAll[I] + 300.0 * Open[I];
						if (Far > BestFar)
						{
							BestFar = Far;
							Goal = I;
						}
					}
				}
			}
			if (Goal == INDEX_NONE)
			{
				return; // cornered: stand
			}
			// Walk towards the goal along the path, as far as Dink walks in Dt.
			TArray<int32> Path;
			for (int32 I = Goal; I != INDEX_NONE && I != DinkCell; I = Parent[I])
			{
				Path.Insert(I, 0);
				if (Path.Num() > Cols * Rows)
				{
					break;
				}
			}
			if (Path.Num() == 0)
			{
				Path.Add(Goal); // already in the goal's cell: step onto its centre
			}
			double Budget = WalkPxPerMs * Dt;
			double X = Dk.X, Y = Dk.Y;
			for (const int32 I : Path)
			{
				const FIntPoint C = CellCentre(I);
				const double Seg = FVector2D::Distance(FVector2D(X, Y), FVector2D(C));
				if (Seg <= Budget)
				{
					X = C.X;
					Y = C.Y;
					Budget -= Seg;
				}
				else
				{
					const double A = Budget / FMath::Max(Seg, 1e-6);
					X += (C.X - X) * A;
					Y += (C.Y - Y) * A;
					break;
				}
			}
			const FIntPoint GoalC = CellCentre(Goal);
			if (FMath::Abs(X - Dk.X) > 0.01 || FMath::Abs(Y - Dk.Y) > 0.01)
			{
				GB->GotoScreen(Screen, X - 20.0, Y);
				G->SyncDinkFromActor();
				if (FMath::Abs(D->GetDink().X - X) > 3.0 || FMath::Abs(D->GetDink().Y - Y) > 3.0)
				{
					// The capsule did not fit there (the 3D collision is a little wider than the hardness): not walkable.
					P->Free[CellAt(X, Y)] = 0;
				}
			}
			const FDinkSprite& Dk2 = D->GetDink();
			S->AddEvent(TEXT("game"), FString::Printf(TEXT("probe: Dink %.0f,%.0f life %d charge %d; %d at %.0f,%.0f hp %d brain %d target %d; goal %d,%d%s"), Dk2.X, Dk2.Y,
				Fact(TEXT("life")), Fact(TEXT("magic_level")), Handle, T->X, T->Y, T->GetProp(TEXT("hitpoints")), T->GetProp(TEXT("brain")), T->GetProp(TEXT("target")),
				GoalC.X, GoalC.Y, bPunch ? TEXT(" (to punch)") : FireDir ? TEXT(" (to fire)") : TEXT("")));
			if (FireDir == 0 || FMath::Abs(Dk2.X - GoalC.X) > 4.0 || FMath::Abs(Dk2.Y - GoalC.Y) > 4.0)
			{
				return;
			}
			Face(Screen, Dk2.X, Dk2.Y, FireDir);
			if (bPunch)
			{
				if (Now >= P->NextPunchMs && ArmFists())
				{
					G->PlayerAttack();
					P->NextPunchMs = Now + 450.0;
					P->HoldUntilMs = Now + 175.0; // until the punch lands (fists: hit frame at 175 ms)
				}
			}
			else if (LineClear(Screen, FMath::RoundToInt32(Dk2.X), FMath::RoundToInt32(Dk2.Y), FireDir, Handle, Obstacles) && G->PlayerCastMagic())
			{
				++P->Casts;
				// The cast animation (seq 32x: 5 frames of 30 ms, dink.ini) holds Dink: item-fb.c sp_nocontrol(1, 1).
				P->HoldUntilMs = Now + 150.0;
			}
		}
			/** The most hitpoints a live monster on Screen has. */
		int32 MostHp(int32 Screen) const
		{
			int32 Most = 0;
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				const FDinkSprite& O = Pair.Value;
				const int32 Brain = O.GetProp(TEXT("brain"));
				if (Pair.Key != 1 && O.bActive && !O.bText && O.Screen == Screen && (Brain == 9 || Brain == 10))
				{
					Most = FMath::Max(Most, O.GetProp(TEXT("hitpoints")));
				}
			}
			return Most;
		}
	/** Live monsters (brain 9 or 10 with hitpoints) on Screen. */
		int32 Hostiles(int32 Screen) const
		{
			int32 N = 0;
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				const FDinkSprite& O = Pair.Value;
				const int32 Brain = O.GetProp(TEXT("brain"));
				N += (Pair.Key != 1 && O.bActive && !O.bText && O.Screen == Screen && (Brain == 9 || Brain == 10) && O.GetProp(TEXT("hitpoints")) > 0) ? 1 : 0;
			}
			return N;
		}
		/**
		 * A fight against several chasers at once (the cult girls, then Bishop Nelson; later the goblins and knights). The
		 * player never comes nearer a chaser than its touch box plus its attack reach plus a margin, and walks at 180 px/s
		 * (the chasers: speed x 1000 / timing px/s, 15-60). Each frame he takes the cheapest walk to a spot that is safe
		 * from every chaser and, from the nearest one's side, lets him strike: a clear fireball line when the spell is
		 * charged, else 54 px level with it (his fist reaches 62, a chaser's bite 47: the cave Bonca's spacing). With no such
		 * spot he keeps away: the safe spot farthest from them all. Friends on the screen (Mary, Nelson before he turns)
		  * are never in the line of fire or the fist's reach: a hit on Mary ends the game (s2-culg.c:110). A sprite running
		  * FutureHostile (Nelson's s2-cman: he turns into a slayer when the last girl dies, at the spot where he stands) is
		  * kept away from as if he were one already, FutureDistance being the attack distance his script will set.
		  */
		void KiteFight(FName FutureHostile = NAME_None, int32 FutureDistance = 70, const FFightOpts& Opt = FFightOpts()) const
		{
			G->SyncDinkFromActor();
			const FDinkSprite& Dk = D->GetDink();
			const int32 Screen = Dk.Screen;
			const double Now = S->GetNowMs();
			const double Dt = P->LastWalkMs < 0.0 ? 17.0 : FMath::Clamp(Now - P->LastWalkMs, 0.0, 100.0);
			P->LastWalkMs = Now;
			if (Now < P->HoldUntilMs)
			{
				return;
			}
			BuildGrid(Screen);
			// The arena and openness (opt-in): the walk graph the whole function sees, put back on every way out.
			struct FMaskGuard { TArray<uint8>* Free; TArray<uint8> Saved; ~FMaskGuard() { if (Saved.Num() > 0) { *Free = Saved; } } };
			FMaskGuard MaskGuard{ &P->Free, TArray<uint8>() };
			if (Opt.bArena)
			{
				MaskGuard.Saved = P->Free;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					const FIntPoint C = CellCentre(I);
					if (C.X < Opt.Arena.Min.X || C.X > Opt.Arena.Max.X || C.Y < Opt.Arena.Min.Y || C.Y > Opt.Arena.Max.Y)
					{
						P->Free[I] = 0;
					}
				}
			}
			TArray<int32> FreeSum;
			if (Opt.OpenWeight > 0.0)
			{
				FreeSum.Init(0, (Cols + 1) * (Rows + 1));
				for (int32 Y = 0; Y < Rows; ++Y)
				{
					for (int32 X = 0; X < Cols; ++X)
					{
						FreeSum[(Y + 1) * (Cols + 1) + X + 1] = P->Free[Y * Cols + X] + FreeSum[Y * (Cols + 1) + X + 1] + FreeSum[(Y + 1) * (Cols + 1) + X] - FreeSum[Y * (Cols + 1) + X];
					}
				}
			}
			/** The share of free cells within 12 cells (72 px) of cell I: 1 = open ground, small = a dead end or a corridor. */
			auto Openness = [&FreeSum](int32 I)
			{
				const int32 Cx = I % Cols, Cy = I / Cols;
				const int32 X0 = FMath::Max(Cx - 12, 0), X1 = FMath::Min(Cx + 13, Cols), Y0 = FMath::Max(Cy - 12, 0), Y1 = FMath::Min(Cy + 13, Rows);
				const int32 N = FreeSum[Y1 * (Cols + 1) + X1] - FreeSum[Y0 * (Cols + 1) + X1] - FreeSum[Y1 * (Cols + 1) + X0] + FreeSum[Y0 * (Cols + 1) + X0];
				return double(N) / 625.0;
			};
			const double TouchPx = 2.0 + CapsulePx(Screen, Dk.X, Dk.Y);
			struct FThreat { int32 Handle; int32 L, T, R, B; double X, Y, Pace, Reach, Dist, StrikeDist; bool bFuture = false; bool bNeutral = false; };
			TArray<FThreat> Th, Future;
			TArray<FIntPoint> Friends;
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				const FDinkSprite& O = Pair.Value;
				int32 L, Tp, R, B;
				if (Pair.Key == 1 || !O.bActive || O.bText || O.Screen != Screen || !G->GetHardbox(O, L, Tp, R, B))
				{
					continue;
				}
				const int32 Brain = O.GetProp(TEXT("brain"));
				if ((Brain == 9 || Brain == 10) && O.GetProp(TEXT("hitpoints")) > 0)
				{
					FThreat T;
					T.Handle = Pair.Key;
					T.L = L; T.T = Tp; T.R = R; T.B = B;
					T.X = O.X; T.Y = O.Y;
					T.Pace = O.GetProp(TEXT("speed"), 1) * 1000.0 / FMath::Max(O.GetProp(TEXT("timing"), 33), 17) * Opt.PaceFactor;
					// Out of its touch box (+ capsule + 6) and out of its attack distance: pill_brain starts an attack only when the target is
					// nearer than sp_distance (centre to centre), and the blow lands 330 ms later only where Dink still is.
					T.Reach = TouchPx + 6.0;
					// A blow lands 47 px from the attacker's centre with the default range (the cave Bonca: reach 47, attacks inside 50), more with a longer
					// sp_range (Nelson's 60 reaches 79).
					T.StrikeDist = FMath::Max<double>(FMath::Max(O.GetProp(TEXT("distance"), 50), 40), 47 + FMath::Max(O.GetProp(TEXT("range")) - 28, 0)) + 4.0 + T.Pace * Opt.FireLeadSec;
					// Passing and waiting keep 10 px more (it walks towards him and his steps are 3 px): only the one he strikes at is closer.
					T.Dist = T.StrikeDist + 10.0 + T.Pace * Opt.PaceMarginSec;
					if (Opt.WanderDist > 0.0 && O.GetProp(TEXT("target")) != 1)
					{
						T.StrikeDist = T.Dist = Opt.WanderDist;
					}
					Th.Add(T);
				}
				else if (!FutureHostile.IsNone() && O.Script == FutureHostile)
				{
					FThreat T;
					T.Handle = Pair.Key;
					T.L = L; T.T = Tp; T.R = R; T.B = B;
					T.X = O.X; T.Y = O.Y;
					T.Pace = 1000.0 / 66.0; // speed 1 at timing 66 (s2-cslay.c:39-42)
					T.Reach = TouchPx + 6.0;
					T.StrikeDist = FutureDistance + 4.0;
				T.Dist = T.StrikeDist + 10.0;
					T.bFuture = true;
					Future.Add(T);
					Friends.Add(FIntPoint(FMath::RoundToInt32(O.X), FMath::RoundToInt32(O.Y)));
				}
				else if (O.GetProp(TEXT("nohit")) != 1 && O.Script != NAME_None && (O.GetProp(TEXT("hitpoints")) > 0 || Brain == 16))
				{
					if ((Opt.bWanderers && Brain == 16 && O.GetProp(TEXT("touch_damage")) != 0 && O.GetProp(TEXT("hitpoints")) > 0) || Pair.Key == Opt.Pull)
					{
						// A peaceful wanderer (people_brain, D:13087): it hurts by touch only, but it walks where it likes.
						FThreat T;
						T.Handle = Pair.Key;
						T.L = L; T.T = Tp; T.R = R; T.B = B;
						T.X = O.X; T.Y = O.Y;
						T.Pace = O.GetProp(TEXT("speed"), 1) * 1000.0 / FMath::Max(O.GetProp(TEXT("timing"), 33), 17) * Opt.PaceFactor;
						T.Reach = TouchPx + 6.0;
						T.StrikeDist = FMath::Max<double>(FMath::Max(O.GetProp(TEXT("distance"), 50), 40), 47 + FMath::Max(O.GetProp(TEXT("range")) - 28, 0)) + 4.0 + T.Pace * Opt.FireLeadSec;
						T.Dist = T.StrikeDist + 10.0 + T.Pace * Opt.PaceMarginSec;
						T.bNeutral = true;
						Th.Add(T);
					}
					if (Pair.Key != Opt.Pull)
					{
						Friends.Add(FIntPoint(FMath::RoundToInt32(O.X), FMath::RoundToInt32(O.Y)));
					}
				}
			}
			int32 NumChasers = 0;
			bool bPullHere = false;
			for (const FThreat& T : Th)
			{
				NumChasers += T.bNeutral ? 0 : 1;
				bPullHere = bPullHere || (T.bNeutral && T.Handle == Opt.Pull);
			}
			if (NumChasers == 0 && !bPullHere)
			{
				return;
			}
			// He only becomes dangerous when the last chaser dies (his script runs then, where he stands, and holds Dink for the whole
			// scene): until then he is a friend to keep out of the fire; with one chaser left he is kept away from like the rest.
			if (NumChasers <= 1)
			{
				Th.Append(Future);
			}
			auto Clearance = [](const FThreat& T, double X, double Y)
			{
				return FMath::Max(FMath::Max3(T.L - X, 0.0, X - T.R), FMath::Max3(T.T - Y, 0.0, Y - T.B));
			};
			int32 TargetHandle = 0;
			auto TooNear = [&Clearance, &TargetHandle](const FThreat& T, double X, double Y)
			{
				return Clearance(T, X, Y) < T.Reach || FVector2D::Distance(FVector2D(T.X, T.Y), FVector2D(X, Y)) < (T.Handle == TargetHandle ? T.StrikeDist : T.Dist);
			};
			// The nearest chaser is the target: the ones behind it are farther from Dink than it is.
			int32 Target = INDEX_NONE;
			auto DistToDink = [&Dk](const FThreat& T) { return FVector2D::Distance(FVector2D(T.X, T.Y), FVector2D(Dk.X, Dk.Y)); };
			for (int32 I = 0; I < Th.Num(); ++I)
			{
				if (!Th[I].bFuture && !Th[I].bNeutral && (Target == INDEX_NONE || DistToDink(Th[I]) < DistToDink(Th[Target]) - 1e-6))
				{
					Target = I;
				}
			}
			if (Target == INDEX_NONE)
			{
				for (int32 I = 0; I < Th.Num(); ++I)
				{
					if (Th[I].Handle == Opt.Pull)
					{
						Target = I;
					}
				}
			}
			if (Target == INDEX_NONE)
			{
				return;
			}
			if (Opt.bNoStrike && !Opt.bGoto && Opt.StandDist > 0.0)
			{
				bool bFar = true;
				for (const FThreat& T : Th)
				{
					bFar = bFar && DistToDink(T) >= Opt.StandDist;
				}
				if (bFar)
				{
					return; // nothing near him: stand
				}
			}
			const FThreat Tg = Th[Target];
			TargetHandle = Tg.Handle;
			const int32 DinkCell = CellAt(Dk.X, Dk.Y);
			TArray<double> DistDink;
			TArray<int32> Parent;
			{
				const TArray<uint8> Walkable = P->Free;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (!P->Free[I] || I == DinkCell)
					{
						continue;
					}
					const FIntPoint C = CellCentre(I);
					for (const FThreat& T : Th)
					{
						if (TooNear(T, C.X, C.Y))
						{
							P->Free[I] = 0;
							break;
						}
					}
				}
				WalkDistances(DinkCell, 0.0, DistDink, &Parent);
				P->Free = Walkable;
			}
			TArray<TArray<double>> ThreatReach;
			if (Opt.bWalkReach)
			{
				ThreatReach.SetNum(Th.Num());
				for (int32 K = 0; K < Th.Num(); ++K)
				{
					WalkDistances(CellAt(Th[K].X, Th[K].Y), 0.0, ThreatReach[K], nullptr);
				}
			}
			auto Safe = [&](int32 I)
			{
				if (!P->Free[I] || DistDink[I] < 0.0)
				{
					return false;
				}
				const FIntPoint C = CellCentre(I);
				for (int32 K = 0; K < Th.Num(); ++K)
				{
					const FThreat& T = Th[K];
					const double Far = FVector2D::Distance(FVector2D(T.X, T.Y), FVector2D(C)) - (T.Handle == TargetHandle ? T.StrikeDist : T.Dist);
					if (TooNear(T, C.X, C.Y) || (!(Opt.bWalkReach && ThreatReach[K][I] < 0.0) && DistDink[I] / (WalkPxPerMs * 1000.0) + 0.15 >= Far / FMath::Max(T.Pace, 1.0)))
					{
						return false;
					}
				}
				return true;
			};
			const bool bCharged = Fact(TEXT("magic_cost")) > 0 && Fact(TEXT("magic_level")) >= Fact(TEXT("magic_cost"));
			const TArray<FIntRect> Obstacles = MissileObstacles(Screen, Tg.Handle);
			int32 Goal = INDEX_NONE;
			int32 StrikeDir = 0;
			bool bFist = false;
			double Best = 0.0;
			const FDinkSprite* TgSprite = D->FindSprite(Tg.Handle);
			const bool bMayStrike = !Opt.bNoStrike && TgSprite && TgSprite->GetProp(TEXT("hitpoints")) <= Opt.StrikeMaxHp;
			for (int32 I = 0; I < Cols * Rows && bMayStrike; ++I)
			{
				if (!Safe(I))
				{
					continue;
				}
				const FIntPoint C = CellCentre(I);
				const double Dx = Tg.X - C.X, Dy = Tg.Y - C.Y;
				int32 Dir = 0;
				bool bByFist = false;
				if (Opt.OpenWeight > 0.0 && Openness(I) < 0.45)
				{
					continue; // a strike from a dead end is the last one
				}
				// Never strike from against a wall: the chaser answers a hit by rushing him, and he needs room to walk away (a cast from
				// x 605 left him pinned on the east edge, with the capsule not fitting the 3D wall: bitten for 9).
				if (FMath::Min(FMath::Min(C.X - 20.0, 619.0 - C.X), FMath::Min<double>(C.Y, 399.0 - C.Y)) < Opt.MinEdge)
				{
					continue;
				}
				if (bCharged && FMath::Abs(Dy) <= 6.0 && FMath::Abs(Dx) <= 260.0 && FMath::Abs(Dx) >= 40.0)
				{
					Dir = Dx > 0 ? 6 : 4;
				}
				else if (bCharged && FMath::Abs(Dx) <= 6.0 && FMath::Abs(Dy) <= 260.0 && FMath::Abs(Dy) >= 40.0)
				{
					Dir = Dy > 0 ? 2 : 8;
				}
				if (Dir != 0 && !LineClear(Screen, C.X, C.Y, Dir, Tg.Handle, Obstacles))
				{
					Dir = 0;
				}
				if (Dir == 0 && FMath::Abs(Dy) <= 4.0 && FMath::Abs(Dx) >= 54.0 && FMath::Abs(Dx) <= 60.0)
				{
					Dir = Dx > 0 ? 6 : 4;
					bByFist = true;
				}
				if (Dir == 0)
				{
					continue;
				}
				// A friend near the fist or the line ruins it (Mary dying ends the run).
				bool bFriendNear = false;
				for (const FIntPoint& FriendPoint : Friends)
				{
					bFriendNear = bFriendNear || FVector2D::Distance(FVector2D(FriendPoint), FVector2D(C)) < (bByFist ? 90.0 : 40.0);
				}
				if (bFriendNear)
				{
					continue;
				}
				if (Goal == INDEX_NONE || DistDink[I] < Best)
				{
					Goal = I;
					Best = DistDink[I];
					StrikeDir = Dir;
					bFist = bByFist;
				}
			}
			if (Goal == INDEX_NONE && Opt.bGoto && Safe(CellAt(Opt.GotoAt.X, Opt.GotoAt.Y)))
			{
				Goal = CellAt(Opt.GotoAt.X, Opt.GotoAt.Y); // a drop he can reach before anything can reach him
			}
			if (Goal == INDEX_NONE && Opt.bGoto && Opt.bForceGoto)
			{
				TArray<double> DistAll;
				WalkDistances(DinkCell, 0.0, DistAll, &Parent); // the walk graph without the threats' zones
				double Nearest = 1e9; // the loot may lie within a walk radius of a wall: the nearest cell he can stand on
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					const double Gap = FVector2D::Distance(FVector2D(CellCentre(I)), FVector2D(Opt.GotoAt));
					if (DistAll[I] >= 0.0 && Gap < Nearest)
					{
						Nearest = Gap;
						Goal = I;
					}
				}
			}
			if (Goal == INDEX_NONE)
			{
				// Keep away: the safe spot the farthest from every chaser (and not far to walk to).
				Best = -1e9;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (!Safe(I))
					{
						continue;
					}
					const FIntPoint C = CellCentre(I);
					double Away = 250.0;
					for (const FThreat& T : Th)
					{
						Away = FMath::Min(Away, FVector2D::Distance(FVector2D(T.X, T.Y), FVector2D(C)) - T.Dist);
					}
					// Not the corner: the farthest cell from a crowd is always a corner, and the crowd follows him into it. A comfortable ring
					// round them (130 px past their attack distance), the nearest cell on it, and room to run on every side.
					const double EdgeRoom = FMath::Min(FMath::Min(C.X - 20.0, 619.0 - C.X), FMath::Min<double>(C.Y, 399.0 - C.Y));
					const double Score = FMath::Min(Away, 130.0) - 0.25 * DistDink[I] + 0.3 * FMath::Min(EdgeRoom, 60.0) + (Opt.OpenWeight > 0.0 ? Opt.OpenWeight * Openness(I) : 0.0);
					if (Score > Best)
					{
						Best = Score;
						Goal = I;
					}
				}
			}
			if (Goal == INDEX_NONE && Opt.bFlee)
			{
				// Nothing is safe by the clock: the reachable cell with the most room round it (the walk graph without the threats' zones).
				TArray<double> DistAll;
				WalkDistances(DinkCell, 0.0, DistAll, &Parent);
				Best = -1e9;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (DistAll[I] < 0.0)
					{
						continue;
					}
					const FIntPoint C = CellCentre(I);
					double Room = 1e9;
					for (const FThreat& T : Th)
					{
						Room = FMath::Min(Room, FVector2D::Distance(FVector2D(T.X, T.Y), FVector2D(C)) - T.Dist);
					}
					const double Score = FMath::Min(Room, 300.0) - 0.1 * DistAll[I];
					if (Score > Best)
					{
						Best = Score;
						Goal = I;
					}
				}
			}
			if (Goal == INDEX_NONE)
			{
				return; // cornered: stand
			}
			TArray<int32> Path;
			for (int32 I = Goal; I != INDEX_NONE && I != DinkCell; I = Parent[I])
			{
				Path.Insert(I, 0);
				if (Path.Num() > Cols * Rows)
				{
					break;
				}
			}
			if (Path.Num() == 0)
			{
				Path.Add(Goal);
			}
			double Budget = WalkPxPerMs * Dt;
			double X = Dk.X, Y = Dk.Y;
			for (const int32 I : Path)
			{
				const FIntPoint C = CellCentre(I);
				const double Seg = FVector2D::Distance(FVector2D(X, Y), FVector2D(C));
				if (Seg <= Budget)
				{
					X = C.X;
					Y = C.Y;
					Budget -= Seg;
				}
				else
				{
					const double A = Budget / FMath::Max(Seg, 1e-6);
					X += (C.X - X) * A;
					Y += (C.Y - Y) * A;
					break;
				}
			}
			if (FMath::Abs(X - Dk.X) > 0.01 || FMath::Abs(Y - Dk.Y) > 0.01)
			{
				GB->GotoScreen(Screen, X - 20.0, Y);
				G->SyncDinkFromActor();
				if (FMath::Abs(D->GetDink().X - X) > 3.0 || FMath::Abs(D->GetDink().Y - Y) > 3.0)
				{
					P->Free[CellAt(X, Y)] = 0; // the capsule did not fit: not walkable
				}
			}
			const FDinkSprite& Dk2 = D->GetDink();
			const FIntPoint GoalC = CellCentre(Goal);
			if (Now - P->LastLogMs >= 100.0)
			{
				P->LastLogMs = Now;
				const FDinkSprite* TgNow = D->FindSprite(Tg.Handle);
				S->AddEvent(TEXT("game"), FString::Printf(TEXT("probe: Dink %.0f,%.0f life %d charge %d; %d chasers, target %d at %.0f,%.0f hp %d; goal %d,%d%s"), Dk2.X, Dk2.Y, Fact(TEXT("life")),
					Fact(TEXT("magic_level")), Th.Num(), Tg.Handle, Tg.X, Tg.Y, TgNow ? TgNow->GetProp(TEXT("hitpoints")) : 0, GoalC.X, GoalC.Y,
					StrikeDir == 0 ? TEXT("") : bFist ? TEXT(" (to punch)") : TEXT(" (to fire)")));
			}
			if (StrikeDir == 0 || FMath::Abs(Dk2.X - GoalC.X) > 4.0 || FMath::Abs(Dk2.Y - GoalC.Y) > 4.0)
			{
				return;
			}
			Face(Screen, Dk2.X, Dk2.Y, StrikeDir);
			if (bFist)
			{
				if (Now >= P->NextPunchMs && ArmFists())
				{
					G->PlayerAttack();
					P->NextPunchMs = Now + 450.0;
					P->HoldUntilMs = Now + 175.0;
				}
			}
			else if (G->PlayerCastMagic())
			{
				++P->Casts;
				P->HoldUntilMs = Now + 150.0; // the cast animation holds him (item-fb.c sp_nocontrol)
			}
		}
		// ---- The melee duel (the goblins of SCR_680, Mog, the knights): one hostile monster, fists, a dance of reach boxes ----

		struct FReach
		{
			double L = 0, T = 0, R = 0, B = 0;
			bool Has(double X, double Y) const { return X >= L && X <= R && Y >= T && Y <= B; }
		};
		/**
		 * run_through_tag_list's test box (D:15460-15540): the victim's hardbox +5/+5/+5/+10, widened along the ATTACKER's dir by its
		 * range (28 by default, 36 up and down) and 10 px on both sides across it. The attacker's point (x, y) must lie inside.
		 */
		static FReach ReachBox(double L, double T, double R, double B, int32 Dir, int32 Range)
		{
			const int32 Amount = Range == 0 ? 28 : Range;
			const int32 AmountY = Range == 0 ? 36 : Range + Range / 6;
			const int32 RangeAmount = Range / 8;
			FReach Bx{ L - 5, T - 5, R + 5, B + 10 };
			switch (Dir)
			{
			case 6: Bx.T -= 10 + (Range != 0 ? RangeAmount : 0); Bx.B += 10 + (Range != 0 ? RangeAmount : 0); Bx.L -= Amount; break;
			case 4: Bx.T -= 10 + (Range != 0 ? RangeAmount : 0); Bx.B += 10 + (Range != 0 ? RangeAmount : 0); Bx.R += Amount; break;
			case 2: Bx.R += 10 + (Range != 0 ? RangeAmount : 0); Bx.L -= 10 + (Range != 0 ? RangeAmount : 0); Bx.T -= AmountY; break;
			case 8: Bx.R += 10; Bx.L -= 10; Bx.B += AmountY; break; // the engine's right edge widens and narrows by the same amount (D:15521)
			default: break;
			}
			return Bx;
		}
		/**
		 * A duel on foot with one hostile monster (brain 9, chasing Dink). Its blow lands where Dink is when its animation reaches the special
		 * frame (D:17050), by the boxes above, 5 frames after it starts; the monster stands still meanwhile, and an attack starts only when it
		 * is within sp_distance (Chebyshev) and sp_attack_wait has passed (D:12935). A fist (reach box from the victim's picture, 0.175 s after
		 * the swing begins, Dink locked for 0.4 s) hits where the blow cannot: below the target (his box ends 10 px lower for a fist than for
		 * the monster's own blow), or ahead of an attack whose time has not come. So each frame: a cell where the fist hits and the expected blow
		 * does not (or cannot start yet: attack_wait ahead by GateMs), reached by a walk that never touches a touch box (the monster's, or
		 * any other sprite that hurts by touch); with none, the nearest cell out of the blow's box; and the blow already under way is dodged
		 * by the shortest walk out of its box. Walks at 180 px/s on a 6 px grid like KiteFight.
		 */
		void DuelFight(int32 Handle, const FDuelOpts& Opt = FDuelOpts()) const
		{
			G->SyncDinkFromActor();
			const FDinkSprite& Dk = D->GetDink();
			const int32 Screen = Dk.Screen;
			const double Now = S->GetNowMs();
			const double Dt = P->LastWalkMs < 0.0 ? 17.0 : FMath::Clamp(Now - P->LastWalkMs, 0.0, 100.0);
			P->LastWalkMs = Now;
			if (Now < P->HoldUntilMs)
			{
				return;
			}
			const FDinkSprite* T = D->FindSprite(Handle);
			int32 TL = 0, TT = 0, TR = 0, TB = 0;
			if (!T || !T->bActive || !G->GetHardbox(*T, TL, TT, TR, TB))
			{
				return;
			}
			BuildGrid(Screen);
			const double Cap = CapsulePx(Screen, Dk.X, Dk.Y);
			const double TouchM = 2.0 + Cap + Opt.Margin;
			const double Tx = FMath::RoundToDouble(T->X), Ty = FMath::RoundToDouble(T->Y);
			const int32 TRange = T->GetProp(TEXT("range"));
			const int32 TDistance = T->GetProp(TEXT("distance"), 50);
			const int32 Seq = T->GetProp(TEXT("seq"));
			const int32 BaseAttack = T->GetProp(TEXT("base_attack"), -1);
			const bool bAttacking = BaseAttack > 0 && Seq > 0 && (Seq / 10) * 10 == BaseAttack;
			double BlowInMs = -1.0; // ms until its blow lands; < 0 = not attacking or already landed
			if (bAttacking)
			{
				const int32 Frame = T->GetProp(TEXT("frame"));
				int32 Special = 0;
				for (int32 Fr = 1; Fr <= 30; ++Fr)
				{
					const FDinkFrameInfo* Fi = G->GetData().FindFrame(Seq, Fr);
					if (!Fi) { break; }
					if (Fi->bSpecial) { Special = Fr; break; }
				}
				if (Special > 0 && Frame < Special)
				{
					const int32 Fixed = T->GetProp(TEXT("frame_delay"));
					const double Fd = Fixed != 0 ? Fixed : G->GetData().FrameDelay(Seq, FMath::Max(Frame, 1));
					BlowInMs = Frame < 1 ? Special * Fd : FMath::Max(0.0, T->FrameDelayMs - G->GetBrainClockMs()) + (Special - Frame - 1) * Fd;
				}
			}
			const double WaitAhead = T->GetProp(TEXT("attack_wait")) - Now; // > 0: no attack can start for that long
			double BlowDelayMs = 275.0; // from the start of its attack animation to its special frame
			if (BaseAttack > 0)
			{
				for (int32 Fr = 1; Fr <= 30; ++Fr)
				{
					const FDinkFrameInfo* Fi = G->GetData().FindFrame(BaseAttack + 6, Fr);
					if (!Fi) { break; }
					if (Fi->bSpecial)
					{
						const int32 Fixed = T->GetProp(TEXT("frame_delay"));
						BlowDelayMs = (Fr - 1) * (Fixed != 0 ? double(Fixed) : double(G->GetData().FrameDelay(BaseAttack + 6, 1)));
						break;
					}
				}
			}
			const double GateMs = Opt.GateMs > 0.0 ? Opt.GateMs : 660.0 - BlowDelayMs;
			const bool bGate = !bAttacking && WaitAhead >= GateMs;
			// Touch boxes (Dink's point + capsule inside the hardbox + 2): the monster's, and every other sprite that hurts by touch.
			TArray<FReach> Touch;
			TArray<FReach> Others;
			TArray<double> OtherPace; // px/s a wanderer can close in (diagonal steps move x and y at full speed)
			TArray<FReach> OtherBoxes; // everything else a fist could land on (a peaceful sprite turns hostile when hit)
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				const FDinkSprite& O = Pair.Value;
				int32 L, Tp, R, B;
				if (Pair.Key == 1 || !O.bActive || O.bText || O.Screen != Screen || !G->GetHardbox(O, L, Tp, R, B))
				{
					continue;
				}
				if (Pair.Key != Handle && O.GetProp(TEXT("nohit")) != 1 && (O.GetProp(TEXT("hitpoints")) > 0 || O.Script != NAME_None))
				{
					// (The family of Joppa walks about: against a caster the boxes get 10 px more, the sword's blow lands 0.2 s after the swing starts.)
					const double Mg = Opt.bCaster ? 10.0 : 0.0;
					OtherBoxes.Add(FReach{ L - Mg, Tp - Mg, R + Mg, B + Mg });
				}
				if (O.GetProp(TEXT("touch_damage")) == 0 || O.GetProp(TEXT("hitpoints")) <= 0)
				{
					continue;
				}
				if (Pair.Key != Handle)
				{
					Others.Add(FReach{ double(L), double(Tp), double(R), double(B) });
					OtherPace.Add(1.42 * O.GetProp(TEXT("speed"), 1) * 1000.0 / FMath::Max(O.GetProp(TEXT("timing"), 33), 17));
				}
				const double M = TouchM + (Pair.Key == Handle ? 0.0 : Opt.WanderMargin);
				Touch.Add(FReach{ L - M, Tp - M, R + M, B + M });
			}
			/** Seconds before the nearest other sprite that hurts by touch could reach q (its touch box, plus the capsule). */
			auto OtherTime = [&Others, &OtherPace, TouchM](double X, double Y)
			{
				double Best = 999.0;
				for (int32 K = 0; K < Others.Num(); ++K)
				{
					const FReach& O = Others[K];
					const double Clear = FMath::Max(FMath::Max(FMath::Max3(O.L - X, 0.0, X - O.R), FMath::Max3(O.T - Y, 0.0, Y - O.B)) - TouchM, 0.0);
					Best = FMath::Min(Best, Clear / FMath::Max(OtherPace[K], 1.0));
				}
				return Best;
			};
			auto InTouch = [&Touch](double X, double Y) { for (const FReach& B : Touch) { if (B.Has(X, Y)) { return true; } } return false; };
			auto InAvoid = [&Opt](double Qx, double Qy) { return Opt.AvoidR > 0.0 && FMath::Max(FMath::Abs(Qx - Opt.AvoidX), FMath::Abs(Qy - Opt.AvoidY)) < Opt.AvoidR; };
			// Where the monster walks: its heading (mx, my px per think; every frame at timing 0) goes on after an attack or a wander turn,
			// and it re-aims at Dink every 200 ms. Still while it swings (to its blow and the animation's end).
			const double ThinkMs = FMath::Max<double>(T->GetProp(TEXT("timing")), 1000.0 / 60.0);
			const double Vx = T->GetProp(TEXT("mx")) * 1000.0 / ThinkMs, Vy = T->GetProp(TEXT("my")) * 1000.0 / ThinkMs;
			const double StillMs = bAttacking ? (BlowInMs >= 0.0 ? BlowInMs + 80.0 : 80.0) : 0.0;
			const double TouchTM = TouchM; // capsule + 2 + margin: the touch box of the monster
			// Would the monster, walking on, touch q within Sec seconds? (its hardbox now, moved along its heading)
			auto TouchSoon = [&](double Qx, double Qy, double Sec, double Extra = 0.0)
			{
				for (double Tau = 0.0; Tau <= Sec + 1e-6; Tau += 0.033)
				{
					const double Run = FMath::Max(0.0, Tau * 1000.0 - StillMs) / 1000.0;
					const double Mx = Vx * Run, My = Vy * Run;
					if (Qx >= TL + Mx - TouchTM - Extra && Qx <= TR + Mx + TouchTM + Extra && Qy >= TT + My - TouchTM - Extra && Qy <= TB + My + TouchTM + Extra) { return true; }
				}
				return false;
			};
			// The monster's dir when it attacks from q: the larger axis towards q (get_distance_and_dir, smooth_follow off).
			auto AttackDirFrom = [&](double Qx, double Qy)
			{
				const double Dx = FMath::Abs(Tx - Qx), Dy = FMath::Abs(Ty - Qy);
				return Dx > Dy ? (Tx > Qx ? 4 : 6) : (Ty > Qy ? 8 : 2);
			};
			const int32 CommittedDir = T->Dir;
			// Would its blow land on Dink at q? (his picture while punching: -19..19 x -10..10, plus the margin)
			auto BlowHits = [&](double Qx, double Qy)
			{
				if (Opt.bCaster) { return false; }
				const int32 Dir = bAttacking ? CommittedDir : AttackDirFrom(Qx, Qy);
				const double M = Opt.Margin;
				return ReachBox(Qx - 19 - M, Qy - 10 - M, Qx + 19 + M, Qy + 10 + M, Dir, TRange).Has(Tx, Ty);
			};
			auto FaceDirTo = [&](double Qx, double Qy)
			{
				const double Dx = Tx - Qx, Dy = Ty - Qy;
				return FMath::Abs(Dx) >= FMath::Abs(Dy) ? (Dx > 0 ? 6 : 4) : (Dy > 0 ? 2 : 8);
			};
			auto FistHits = [&](double Qx, double Qy)
			{
				FReach Bx = ReachBox(TL, TT, TR, TB, FaceDirTo(Qx, Qy), Opt.Range);
				const double M = Opt.FistMargin;
				return Qx >= Bx.L + M && Qx <= Bx.R - M && Qy >= Bx.T + M && Qy <= Bx.B - M;
			};
			// Walks: the grid without the touch boxes.
			const int32 DinkCell = CellAt(Dk.X, Dk.Y);
			TArray<float> Open;
			OpennessMap(Open); // 1 = open ground, small = a dead end or a corridor: the fight is drawn to open ground
			TArray<double> DistDink;
			TArray<int32> Parent;
			{
				const TArray<uint8> Walkable = P->Free;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (P->Free[I] && I != DinkCell)
					{
						const FIntPoint C = CellCentre(I);
						if (InTouch(C.X, C.Y)) { P->Free[I] = 0; }
					}
				}
				WalkDistances(DinkCell, 0.0, DistDink, &Parent);
				P->Free = Walkable;
			}
			const double Cheb0 = FMath::Max(FMath::Abs(Tx - Dk.X), FMath::Abs(Ty - Dk.Y));
			// A charged fireball at range, along a clear row or column (the monster walks up to him meanwhile).
			if (Opt.CastFrom > 0.0 && T->GetProp(TEXT("brain")) == 9 && !bAttacking && !InAvoid(Dk.X, Dk.Y) && Cheb0 >= Opt.CastFrom && Fact(TEXT("magic_cost")) > 0 && Fact(TEXT("magic_level")) >= Fact(TEXT("magic_cost")))
			{
				int32 Dir = 0;
				const double Dx = Tx - Dk.X, Dy = Ty - Dk.Y;
				if (FMath::Abs(Dy) <= 6.0 && FMath::Abs(Dx) >= 40.0 && FMath::Abs(Dx) <= 260.0) { Dir = Dx > 0 ? 6 : 4; }
				else if (FMath::Abs(Dx) <= 6.0 && FMath::Abs(Dy) >= 40.0 && FMath::Abs(Dy) <= 260.0) { Dir = Dy > 0 ? 2 : 8; }
				if (Dir != 0 && LineClear(Screen, FMath::RoundToInt32(Dk.X), FMath::RoundToInt32(Dk.Y), Dir, Handle, MissileObstacles(Screen, Handle)))
				{
					Face(Screen, Dk.X, Dk.Y, Dir);
					if (G->PlayerCastMagic())
					{
						++P->Casts;
						P->HoldUntilMs = Now + 150.0;
						return;
					}
				}
			}
			// The goal.
			auto Safe = [&](double Qx, double Qy) { return bGate || !BlowHits(Qx, Qy); };
			// A punch from q that would also reach another sprite (it turns hostile) is no strike.
			auto HitsOthers = [&](double Qx, double Qy)
			{
				const int32 Dir = FaceDirTo(Qx, Qy);
				for (const FReach& Ob : OtherBoxes)
				{
					const FReach Bx = ReachBox(Ob.L, Ob.T, Ob.R, Ob.B, Dir, Opt.Range);
					if (Bx.Has(Qx, Qy)) { return true; }
				}
				return false;
			};
			int32 Goal = INDEX_NONE;
			const TCHAR* Mode = TEXT("stand");
			const bool bNowInBlow = BlowHits(Dk.X, Dk.Y);
			const double OtherNow = OtherTime(Dk.X, Dk.Y);
			const double WalkSecPerPx = 1.0 / (WalkPxPerMs * 1000.0);
			const auto NoExtra = [](int32, const FIntPoint&) { return 0.0; };
			// The cheapest (walk + Extra) cell Ok accepts, INDEX_NONE if none.
			auto Nearest = [&](TFunctionRef<bool(int32, const FIntPoint&)> Ok, TFunctionRef<double(int32, const FIntPoint&)> Extra)
			{
				int32 Pick = INDEX_NONE;
				double Best = 1e9;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (DistDink[I] < 0.0) { continue; }
					const FIntPoint C = CellCentre(I);
					if (!Ok(I, C)) { continue; }
					const double Cost = DistDink[I] + Extra(I, C);
					if (Cost < Best) { Best = Cost; Pick = I; }
				}
				return Pick;
			};
			// A cell no other wanderer reaches before Dink has walked there and stood for HoldSec.
			auto OthersLate = [&](int32 I, const FIntPoint& C, double HoldSec) { return OtherTime(C.X, C.Y) >= DistDink[I] * WalkSecPerPx + HoldSec; };
			auto Isolation = [&](int32 I, const FIntPoint& C) { return 120.0 * FMath::Max(0.0, 2.5 - OtherTime(C.X, C.Y)) + 200.0 * FMath::Max(0.0, 0.6 - double(Open[I])); };
			// A peaceful target (brain 16: a goblin walking about) is pulled first: a charged fireball from a cell level with it, 100-230 px off,
			// with a clear line, where no other goblin reaches him first and there is room to run. Its `hit` then makes only it hostile.
			if (T->GetProp(TEXT("brain")) != 9 && Opt.bPull)
			{
				const TArray<FIntRect> Obstacles = MissileObstacles(Screen, Handle);
				const bool bCharged = Fact(TEXT("magic_cost")) > 0 && Fact(TEXT("magic_level")) >= Fact(TEXT("magic_cost"));
				auto LineDir = [&](double Qx, double Qy)
				{
					const double Dx = Tx - Qx, Dy = Ty - Qy;
					if (FMath::Abs(Dy) <= 3.0 && FMath::Abs(Dx) >= 100.0 && FMath::Abs(Dx) <= 230.0) { return Dx > 0 ? 6 : 4; }
					if (FMath::Abs(Dx) <= 3.0 && FMath::Abs(Dy) >= 100.0 && FMath::Abs(Dy) <= 230.0) { return Dy > 0 ? 2 : 8; }
					return 0;
				};
				const int32 PullGoal = Nearest([&](int32 I, const FIntPoint& C)
				{
					const int32 Dir = LineDir(C.X, C.Y);
					return Dir != 0 && Open[I] >= 0.5f && OthersLate(I, C, 1.5) && LineClear(Screen, C.X, C.Y, Dir, Handle, Obstacles);
				}, Isolation);
				if (PullGoal != INDEX_NONE)
				{
					const FIntPoint GC = CellCentre(PullGoal);
					TArray<int32> PullPath;
					for (int32 I = PullGoal; I != INDEX_NONE && I != DinkCell; I = Parent[I])
					{
						PullPath.Insert(I, 0);
						if (PullPath.Num() > Cols * Rows) { break; }
					}
					double Budget = WalkPxPerMs * Dt;
					double X = Dk.X, Y = Dk.Y;
					for (const int32 I : PullPath)
					{
						const FIntPoint C = CellCentre(I);
						const double Seg = FVector2D::Distance(FVector2D(X, Y), FVector2D(C));
						if (Seg <= Budget) { X = C.X; Y = C.Y; Budget -= Seg; }
						else { const double A = Budget / FMath::Max(Seg, 1e-6); X += (C.X - X) * A; Y += (C.Y - Y) * A; break; }
					}
					if (FMath::Abs(X - Dk.X) > 0.01 || FMath::Abs(Y - Dk.Y) > 0.01)
					{
						GB->GotoScreen(Screen, X - 20.0, Y);
						G->SyncDinkFromActor();
					}
					const FDinkSprite& DkP = D->GetDink();
					if (Now - P->LastLogMs >= Opt.LogMs)
					{
						P->LastLogMs = Now;
						S->AddEvent(TEXT("game"), FString::Printf(TEXT("probe: duel pull Dink %.0f,%.0f life %d; %d at %.0f,%.0f hp %d charge %d goal %d,%d other %.2f"), DkP.X, DkP.Y, Fact(TEXT("life")), Handle, T->X, T->Y,
							T->GetProp(TEXT("hitpoints")), Fact(TEXT("magic_level")), GC.X, GC.Y, OtherNow));
					}
					if (bCharged && FMath::Abs(DkP.X - GC.X) <= 3.5 && FMath::Abs(DkP.Y - GC.Y) <= 3.5)
					{
						const int32 Dir = LineDir(DkP.X, DkP.Y);
						if (Dir != 0)
						{
							Face(Screen, DkP.X, DkP.Y, Dir);
							if (G->PlayerCastMagic()) { ++P->Casts; P->HoldUntilMs = Now + 150.0; }
						}
					}
					return;
				}
			}
			if (bAttacking && BlowInMs >= 0.0 && bNowInBlow)
			{
				Mode = TEXT("dodge"); // the nearest cell out of the blow's box (the time is whatever is left)
				Goal = Nearest([&](int32, const FIntPoint& C) { return !BlowHits(C.X, C.Y); }, Isolation);
			}
			else if (OtherNow < Opt.FleeSec)
			{
				Mode = TEXT("flee"); // another goblin is coming: draw the fight away from it
				Goal = Nearest([&](int32 I, const FIntPoint& C) { return !BlowHits(C.X, C.Y) && OthersLate(I, C, 1.0); }, NoExtra);
				if (Goal == INDEX_NONE)
				{
					// None is safe by the clock: the cell with the most time before anything reaches it.
					double Best = -1e9;
					for (int32 I = 0; I < Cols * Rows; ++I)
					{
						if (DistDink[I] < 0.0) { continue; }
						const FIntPoint C = CellCentre(I);
						if (BlowHits(C.X, C.Y)) { continue; }
						const double Score = OtherTime(C.X, C.Y) - DistDink[I] * WalkSecPerPx;
						if (Score > Best) { Best = Score; Goal = I; }
					}
				}
			}
			if (Goal == INDEX_NONE && TouchSoon(Dk.X, Dk.Y, Opt.TouchSec))
			{
				Mode = TEXT("sidestep"); // it is walking into him: out of its way (across its heading), not away along it
				Goal = Nearest([&](int32 I, const FIntPoint& C) { return !TouchSoon(C.X, C.Y, Opt.TouchSec + 0.3, 10.0) && Safe(C.X, C.Y) && OthersLate(I, C, 0.3); }, Isolation);
				if (Goal == INDEX_NONE)
				{
					Goal = Nearest([&](int32, const FIntPoint& C) { return !TouchSoon(C.X, C.Y, Opt.TouchSec, 4.0); }, Isolation);
				}
			}
			if (Goal == INDEX_NONE)
			{
				Mode = TEXT("strike");
				Goal = Nearest([&](int32 I, const FIntPoint& C) { return !InAvoid(C.X, C.Y) && Safe(C.X, C.Y) && FistHits(C.X, C.Y) && OthersLate(I, C, Opt.HoldSec) && !HitsOthers(C.X, C.Y) && !TouchSoon(C.X, C.Y, Opt.HoldSec - 0.1, 6.0); },
					[&](int32 I, const FIntPoint& C)
					{
						return Isolation(I, C) + (FMath::Min(FMath::Min(C.X - 20.0, 619.0 - C.X), FMath::Min<double>(C.Y, 399.0 - C.Y)) < 14.0 ? 40.0 : 0.0);
					});
			}
			if (Goal == INDEX_NONE)
			{
				// Nothing to hit from safely: wait where he is if that is out of its reach (it comes to him), else the nearest cell that is
				// (Chebyshev StageCheb from it: its attack starts inside sp_distance).
				const bool bStayOk = !InAvoid(Dk.X, Dk.Y) && !BlowHits(Dk.X, Dk.Y) && Cheb0 >= Opt.StageCheb - 6.0 && !TouchSoon(Dk.X, Dk.Y, Opt.TouchSec);
				if (bStayOk)
				{
					Mode = TEXT("wait");
					Goal = DinkCell;
				}
				else
				{
					Mode = TEXT("stage");
					Goal = Nearest([&](int32 I, const FIntPoint& C) { return !InAvoid(C.X, C.Y) && !BlowHits(C.X, C.Y) && OthersLate(I, C, 0.3) && !TouchSoon(C.X, C.Y, Opt.TouchSec, 8.0) && FMath::Max(FMath::Abs(Tx - C.X), FMath::Abs(Ty - C.Y)) >= Opt.StageCheb; }, Isolation);
					if (Goal == INDEX_NONE)
					{
						Mode = TEXT("evade");
						Goal = Nearest([&](int32, const FIntPoint& C) { return !BlowHits(C.X, C.Y); }, Isolation);
					}
				}
			}
			if (Goal == INDEX_NONE)
			{
				Goal = DinkCell;
			}
			TArray<int32> Path;
			for (int32 I = Goal; I != INDEX_NONE && I != DinkCell; I = Parent[I])
			{
				Path.Insert(I, 0);
				if (Path.Num() > Cols * Rows) { break; }
			}
			double Budget = WalkPxPerMs * Dt;
			double X = Dk.X, Y = Dk.Y;
			for (const int32 I : Path)
			{
				const FIntPoint C = CellCentre(I);
				const double Seg = FVector2D::Distance(FVector2D(X, Y), FVector2D(C));
				if (Seg <= Budget) { X = C.X; Y = C.Y; Budget -= Seg; }
				else { const double A = Budget / FMath::Max(Seg, 1e-6); X += (C.X - X) * A; Y += (C.Y - Y) * A; break; }
			}
			if (FMath::Abs(X - Dk.X) > 0.01 || FMath::Abs(Y - Dk.Y) > 0.01)
			{
				GB->GotoScreen(Screen, X - 20.0, Y);
				G->SyncDinkFromActor();
				if (FMath::Abs(D->GetDink().X - X) > 3.0 || FMath::Abs(D->GetDink().Y - Y) > 3.0)
				{
					P->Free[CellAt(X, Y)] = 0; // the capsule did not fit: not walkable
				}
			}
			const FDinkSprite& Dk2 = D->GetDink();
			const FIntPoint GoalC = CellCentre(Goal);
			if (Now - P->LastLogMs >= Opt.LogMs)
			{
				P->LastLogMs = Now;
				S->AddEvent(TEXT("game"), FString::Printf(TEXT("probe: duel %s Dink %.0f,%.0f life %d; %d at %.0f,%.0f hp %d dir %d seq %d frame %d attack in %.0f blow in %.0f touch %d other %.2f; goal %d,%d step %.1f,%.1f v %.0f,%.0f hold %d"),
					Mode, Dk2.X, Dk2.Y, Fact(TEXT("life")), Handle, T->X, T->Y, T->GetProp(TEXT("hitpoints")), T->Dir, Seq, T->GetProp(TEXT("frame")),
					WaitAhead, BlowInMs, Touch.Num(), OtherNow, GoalC.X, GoalC.Y, X, Y, Vx, Vy, int32(P->HoldUntilMs - Now)));
			}
			if (FCString::Strcmp(Mode, TEXT("strike")) != 0 || FMath::Abs(Dk2.X - GoalC.X) > 3.5 || FMath::Abs(Dk2.Y - GoalC.Y) > 3.5)
			{
				return;
			}
			// At the strike cell: face the target and swing (one punch per animation: 0.4 s, Dink cannot move meanwhile: sp_nocontrol).
			// Against a caster the family wanders into the swing: hold it while the blow would reach one of them (or the other dragon).
			if (Opt.bCaster && HitsOthers(Dk2.X, Dk2.Y)) { return; }
			const int32 FaceDir = FaceDirTo(Dk2.X, Dk2.Y);
			Face(Screen, Dk2.X, Dk2.Y, FaceDir);
			if (Now >= P->NextPunchMs && ArmFists())
			{
				G->PlayerAttack();
				P->NextPunchMs = Now + 450.0;
				P->HoldUntilMs = Now + 400.0;
			}
		}
		/**
		 * Several hostile monsters at once (brain 9, chasing Dink): the three knights of SCR_521 (40 hp, defense 6, strength 12, range 50, distance 62, 60 px/s).
		 * DuelFight's model for each of them: a blow already under way lands where Dink stands when its animation reaches the special frame (the monster
		 * stands still meanwhile); one that is not attacking and whose attack_wait has passed (or is near) could start a blow at any cell within sp_distance
		 * of it. Their blows hit every sprite in the box (the melee rule), each other included, so a Dink who is never in a box, and who stands where the
		 * monsters come together to swing at him, lets them kill each other (traced: a dead Dink standing still saw two of three dead in 150 s). Each frame,
		 * in order: (1) dodge a pending blow, by the shortest walk out of every pending box; (2) a monster walking into him: sidestep; (3) a cell in the
		 * potential box of one that could attack: leave it; (4) a charged fireball along a clear row or column when every monster is far; (5) a punch from a
		 * cell where the fist reaches one and no pending or potential blow reaches him; (6) wait outside every box, about BaitCheb from the nearest monster.
		 */
		void SquadFight(const FSquadOpts& Opt = FSquadOpts()) const
		{
			G->SyncDinkFromActor();
			const FDinkSprite& Dk = D->GetDink();
			const int32 Screen = Dk.Screen;
			const double Now = S->GetNowMs();
			const double Dt = P->LastWalkMs < 0.0 ? 17.0 : FMath::Clamp(Now - P->LastWalkMs, 0.0, 100.0);
			P->LastWalkMs = Now;
			if (Now < P->HoldUntilMs)
			{
				return;
			}
			struct FFoe
			{
				int32 H = 0;
				const FDinkSprite* T = nullptr;
				int32 L = 0, Tp = 0, R = 0, B = 0;
				double X = 0.0, Y = 0.0;
				int32 Range = 0, Distance = 62, Hp = 0, Dir = 0;
				bool bAttacking = false, bGate = false;
				double BlowInMs = -1.0, WaitAhead = 0.0, Vx = 0.0, Vy = 0.0, StillMs = 0.0, Pace = 85.0;
			};
			TArray<FFoe> Foes;
			TArray<FReach> Touch;
			const double CapPx = CapsulePx(Screen, Dk.X, Dk.Y);
			const double TouchM = 2.0 + CapPx + Opt.Margin;
			TArray<int32> Handles;
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				const FDinkSprite& O = Pair.Value;
				if (Pair.Key != 1 && O.bActive && !O.bText && O.Screen == Screen && O.GetProp(TEXT("hitpoints")) > 0 && O.GetProp(TEXT("brain")) == 9)
				{
					Handles.Add(Pair.Key);
				}
			}
			Handles.Sort();
			for (const int32 H : Handles)
			{
				FFoe Fo;
				Fo.H = H;
				Fo.T = D->FindSprite(H);
				if (!Fo.T || !G->GetHardbox(*Fo.T, Fo.L, Fo.Tp, Fo.R, Fo.B))
				{
					continue;
				}
				const FDinkSprite& T = *Fo.T;
				Fo.X = FMath::RoundToDouble(T.X);
				Fo.Y = FMath::RoundToDouble(T.Y);
				Fo.Range = T.GetProp(TEXT("range"));
				Fo.Distance = T.GetProp(TEXT("distance"), 50);
				Fo.Hp = T.GetProp(TEXT("hitpoints"));
				Fo.Dir = T.Dir;
				const int32 Seq = T.GetProp(TEXT("seq"));
				const int32 BaseAttack = T.GetProp(TEXT("base_attack"), -1);
				Fo.bAttacking = BaseAttack > 0 && Seq > 0 && (Seq / 10) * 10 == BaseAttack;
				if (Fo.bAttacking)
				{
					const int32 Frame = T.GetProp(TEXT("frame"));
					int32 Special = 0;
					for (int32 Fr = 1; Fr <= 30; ++Fr)
					{
						const FDinkFrameInfo* Fi = G->GetData().FindFrame(Seq, Fr);
						if (!Fi) { break; }
						if (Fi->bSpecial) { Special = Fr; break; }
					}
					if (Special > 0 && Frame < Special)
					{
						const int32 Fixed = T.GetProp(TEXT("frame_delay"));
						const double Fd = Fixed != 0 ? Fixed : G->GetData().FrameDelay(Seq, FMath::Max(Frame, 1));
						Fo.BlowInMs = Frame < 1 ? Special * Fd : FMath::Max(0.0, T.FrameDelayMs - G->GetBrainClockMs()) + (Special - Frame - 1) * Fd;
					}
				}
				Fo.WaitAhead = T.GetProp(TEXT("attack_wait")) - Now;
				double BlowDelayMs = 275.0;
				if (BaseAttack > 0)
				{
					for (int32 Fr = 1; Fr <= 30; ++Fr)
					{
						const FDinkFrameInfo* Fi = G->GetData().FindFrame(BaseAttack + 6, Fr);
						if (!Fi) { break; }
						if (Fi->bSpecial)
						{
							const int32 Fixed = T.GetProp(TEXT("frame_delay"));
							BlowDelayMs = (Fr - 1) * (Fixed != 0 ? double(Fixed) : double(G->GetData().FrameDelay(BaseAttack + 6, 1)));
							break;
						}
					}
				}
				const double GateMs = Opt.GateMs > 0.0 ? Opt.GateMs : 660.0 - BlowDelayMs;
				Fo.bGate = !Fo.bAttacking && Fo.WaitAhead >= GateMs;
				const double ThinkMs = FMath::Max<double>(T.GetProp(TEXT("timing")), 1000.0 / 60.0);
				Fo.Vx = T.GetProp(TEXT("mx")) * 1000.0 / ThinkMs;
				Fo.Vy = T.GetProp(TEXT("my")) * 1000.0 / ThinkMs;
				Fo.StillMs = Fo.bAttacking ? (Fo.BlowInMs >= 0.0 ? Fo.BlowInMs + 80.0 : 80.0) : 0.0;
				Fo.Pace = 1.42 * T.GetProp(TEXT("speed"), 1) * 1000.0 / FMath::Max(T.GetProp(TEXT("timing"), 33), 17);
				Touch.Add(FReach{ double(Fo.L) - TouchM, double(Fo.Tp) - TouchM, double(Fo.R) + TouchM, double(Fo.B) + TouchM });
				Foes.Add(Fo);
			}
			if (Foes.IsEmpty())
			{
				return;
			}
			BuildGrid(Screen);
			// Dink's picture while punching or standing: -19..19 x -10..10 (plus the margin).
			auto HitBy = [&](const FFoe& Fo, int32 FoeDir, double Qx, double Qy)
			{
				const double M = Opt.Margin;
				return ReachBox(Qx - 19 - M, Qy - 10 - M, Qx + 19 + M, Qy + 10 + M, FoeDir, Fo.Range).Has(Fo.X, Fo.Y);
			};
			auto AttackDirFrom = [&](const FFoe& Fo, double Qx, double Qy)
			{
				const double Dx = FMath::Abs(Fo.X - Qx), Dy = FMath::Abs(Fo.Y - Qy);
				return Dx > Dy ? (Fo.X > Qx ? 4 : 6) : (Fo.Y > Qy ? 8 : 2);
			};
			// A blow under way that has not landed yet and would hit q.
			auto Pending = [&](double Qx, double Qy)
			{
				for (const FFoe& Fo : Foes) { if (Fo.bAttacking && Fo.BlowInMs >= 0.0 && HitBy(Fo, Fo.Dir, Qx, Qy)) { return true; } }
				return false;
			};
			// A monster that could begin a blow at q (inside its sp_distance, attack_wait passed or near) and whose blow would hit q.
			auto Potential = [&](double Qx, double Qy)
			{
				for (const FFoe& Fo : Foes)
				{
					if (Fo.bAttacking || Fo.bGate) { continue; }
					if (FMath::Max(FMath::Abs(Fo.X - Qx), FMath::Abs(Fo.Y - Qy)) >= Fo.Distance + 8.0) { continue; }
					if (HitBy(Fo, AttackDirFrom(Fo, Qx, Qy), Qx, Qy)) { return true; }
				}
				return false;
			};
			auto InTouch = [&Touch](double X, double Y) { for (const FReach& Bx : Touch) { if (Bx.Has(X, Y)) { return true; } } return false; };
			// Would a monster, walking on along its heading, touch q within Sec seconds?
			auto TouchSoon = [&](double Qx, double Qy, double Sec, double Extra = 0.0)
			{
				for (const FFoe& Fo : Foes)
				{
					for (double Tau = 0.0; Tau <= Sec + 1e-6; Tau += 0.033)
					{
						const double Run = FMath::Max(0.0, Tau * 1000.0 - Fo.StillMs) / 1000.0;
						const double Mx = Fo.Vx * Run, My = Fo.Vy * Run;
						if (Qx >= Fo.L + Mx - TouchM - Extra && Qx <= Fo.R + Mx + TouchM + Extra && Qy >= Fo.Tp + My - TouchM - Extra && Qy <= Fo.B + My + TouchM + Extra) { return true; }
					}
				}
				return false;
			};
			auto FaceDirTo = [&](const FFoe& Fo, double Qx, double Qy)
			{
				const double Dx = Fo.X - Qx, Dy = Fo.Y - Qy;
				return FMath::Abs(Dx) >= FMath::Abs(Dy) ? (Dx > 0 ? 6 : 4) : (Dy > 0 ? 2 : 8);
			};
			auto FistHits = [&](const FFoe& Fo, double Qx, double Qy)
			{
				const FReach Bx = ReachBox(Fo.L, Fo.Tp, Fo.R, Fo.B, FaceDirTo(Fo, Qx, Qy), Opt.Range);
				const double M = Opt.FistMargin;
				return Qx >= Bx.L + M && Qx <= Bx.R - M && Qy >= Bx.T + M && Qy <= Bx.B - M;
			};
			/** Seconds before the nearest monster could reach q's touch box. */
			auto FoeTime = [&](double X, double Y)
			{
				double Best = 999.0;
				for (const FFoe& Fo : Foes)
				{
					const double Clear = FMath::Max(FMath::Max(FMath::Max3(Fo.L - X, 0.0, X - Fo.R), FMath::Max3(Fo.Tp - Y, 0.0, Y - Fo.B)) - TouchM, 0.0);
					Best = FMath::Min(Best, Clear / FMath::Max(Fo.Pace, 1.0));
				}
				return Best;
			};
			auto NearestCheb = [&](double X, double Y)
			{
				double Best = 1e9;
				for (const FFoe& Fo : Foes) { Best = FMath::Min(Best, FMath::Max(FMath::Abs(Fo.X - X), FMath::Abs(Fo.Y - Y))); }
				return Best;
			};
			const int32 DinkCell = CellAt(Dk.X, Dk.Y);
			TArray<float> Open;
			OpennessMap(Open);
			TArray<double> DistDink;
			TArray<int32> Parent;
			{
				const TArray<uint8> Walkable = P->Free;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (P->Free[I] && I != DinkCell)
					{
						const FIntPoint C = CellCentre(I);
						if (InTouch(C.X, C.Y)) { P->Free[I] = 0; }
					}
				}
				WalkDistances(DinkCell, 0.0, DistDink, &Parent);
				P->Free = Walkable;
			}
			const double WalkSecPerPx = 1.0 / (WalkPxPerMs * 1000.0);
			// A charged fireball along a clear row or column at the nearest monster that has one, when no monster is close.
			double MinCheb = NearestCheb(Dk.X, Dk.Y);
			if (Opt.CastFrom > 0.0 && MinCheb >= Opt.CastFrom && !Pending(Dk.X, Dk.Y) && Fact(TEXT("magic_cost")) > 0 && Fact(TEXT("magic_level")) >= Fact(TEXT("magic_cost")))
			{
				for (const FFoe& Fo : Foes)
				{
					int32 Dir = 0;
					const double Dx = Fo.X - Dk.X, Dy = Fo.Y - Dk.Y;
					if (FMath::Abs(Dy) <= 6.0 && FMath::Abs(Dx) >= 40.0 && FMath::Abs(Dx) <= 260.0) { Dir = Dx > 0 ? 6 : 4; }
					else if (FMath::Abs(Dx) <= 6.0 && FMath::Abs(Dy) >= 40.0 && FMath::Abs(Dy) <= 260.0) { Dir = Dy > 0 ? 2 : 8; }
					if (Dir != 0 && LineClear(Screen, FMath::RoundToInt32(Dk.X), FMath::RoundToInt32(Dk.Y), Dir, Fo.H, MissileObstacles(Screen, Fo.H)))
					{
						Face(Screen, Dk.X, Dk.Y, Dir);
						if (G->PlayerCastMagic())
						{
							++P->Casts;
							P->HoldUntilMs = Now + 150.0;
							return;
						}
					}
				}
			}
			auto Isolation = [&](int32 I, const FIntPoint& C) { return 120.0 * FMath::Max(0.0, 1.0 - FoeTime(C.X, C.Y)) + 200.0 * FMath::Max(0.0, 0.6 - double(Open[I])); };
			const auto NoExtra = [](int32, const FIntPoint&) { return 0.0; };
			auto Nearest = [&](TFunctionRef<bool(int32, const FIntPoint&)> Ok, TFunctionRef<double(int32, const FIntPoint&)> Extra)
			{
				int32 Pick = INDEX_NONE;
				double Best = 1e9;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (DistDink[I] < 0.0) { continue; }
					const FIntPoint C = CellCentre(I);
					if (!Ok(I, C)) { continue; }
					const double Cost = DistDink[I] + Extra(I, C);
					if (Cost < Best) { Best = Cost; Pick = I; }
				}
				return Pick;
			};
			int32 Goal = INDEX_NONE;
			const TCHAR* Mode = TEXT("stand");
			if (Pending(Dk.X, Dk.Y))
			{
				Mode = TEXT("dodge");
				Goal = Nearest([&](int32, const FIntPoint& C) { return !Pending(C.X, C.Y) && !Potential(C.X, C.Y); }, Isolation);
				if (Goal == INDEX_NONE)
				{
					Goal = Nearest([&](int32, const FIntPoint& C) { return !Pending(C.X, C.Y); }, Isolation);
				}
			}
			if (Goal == INDEX_NONE && TouchSoon(Dk.X, Dk.Y, Opt.TouchSec))
			{
				Mode = TEXT("sidestep");
				Goal = Nearest([&](int32, const FIntPoint& C) { return !TouchSoon(C.X, C.Y, Opt.TouchSec + 0.3, 10.0) && !Pending(C.X, C.Y) && !Potential(C.X, C.Y); }, Isolation);
				if (Goal == INDEX_NONE)
				{
					Goal = Nearest([&](int32, const FIntPoint& C) { return !TouchSoon(C.X, C.Y, Opt.TouchSec, 4.0) && !Pending(C.X, C.Y); }, Isolation);
				}
			}
			if (Goal == INDEX_NONE && Potential(Dk.X, Dk.Y))
			{
				Mode = TEXT("leave");
				Goal = Nearest([&](int32, const FIntPoint& C) { return !Pending(C.X, C.Y) && !Potential(C.X, C.Y) && !TouchSoon(C.X, C.Y, Opt.TouchSec, 6.0); }, Isolation);
			}
			int32 StrikeFoe = INDEX_NONE;
			if (Goal == INDEX_NONE && Opt.bStrike)
			{
				Mode = TEXT("strike");
				Goal = Nearest([&](int32, const FIntPoint& C)
				{
					bool bReach = false;
					for (const FFoe& Fo : Foes) { bReach = bReach || FistHits(Fo, C.X, C.Y); }
					return bReach && !Pending(C.X, C.Y) && !Potential(C.X, C.Y) && !TouchSoon(C.X, C.Y, Opt.HoldSec - 0.1, 6.0);
				}, Isolation);
			}
			if (Goal == INDEX_NONE)
			{
				const bool bStayOk = !Pending(Dk.X, Dk.Y) && !Potential(Dk.X, Dk.Y) && !TouchSoon(Dk.X, Dk.Y, Opt.TouchSec) && MinCheb >= Opt.BaitCheb - 6.0;
				if (bStayOk)
				{
					Mode = TEXT("wait");
					Goal = DinkCell;
				}
				else
				{
					Mode = TEXT("bait");
					Goal = Nearest([&](int32, const FIntPoint& C) { return !Pending(C.X, C.Y) && !Potential(C.X, C.Y) && !TouchSoon(C.X, C.Y, Opt.TouchSec, 8.0) && NearestCheb(C.X, C.Y) >= Opt.BaitCheb; }, Isolation);
					if (Goal == INDEX_NONE)
					{
						Mode = TEXT("evade");
						Goal = Nearest([&](int32, const FIntPoint& C) { return !Pending(C.X, C.Y); }, Isolation);
					}
				}
			}
			if (Goal == INDEX_NONE)
			{
				Goal = DinkCell;
			}
			TArray<int32> Path;
			for (int32 I = Goal; I != INDEX_NONE && I != DinkCell; I = Parent[I])
			{
				Path.Insert(I, 0);
				if (Path.Num() > Cols * Rows) { break; }
			}
			double Budget = WalkPxPerMs * Dt;
			double X = Dk.X, Y = Dk.Y;
			for (const int32 I : Path)
			{
				const FIntPoint C = CellCentre(I);
				const double Seg = FVector2D::Distance(FVector2D(X, Y), FVector2D(C));
				if (Seg <= Budget) { X = C.X; Y = C.Y; Budget -= Seg; }
				else { const double A = Budget / FMath::Max(Seg, 1e-6); X += (C.X - X) * A; Y += (C.Y - Y) * A; break; }
			}
			if (FMath::Abs(X - Dk.X) > 0.01 || FMath::Abs(Y - Dk.Y) > 0.01)
			{
				GB->GotoScreen(Screen, X - 20.0, Y);
				G->SyncDinkFromActor();
				if (FMath::Abs(D->GetDink().X - X) > 3.0 || FMath::Abs(D->GetDink().Y - Y) > 3.0)
				{
					P->Free[CellAt(X, Y)] = 0; // the capsule did not fit: not walkable
				}
			}
			const FDinkSprite& Dk2 = D->GetDink();
			const FIntPoint GoalC = CellCentre(Goal);
			if (Now - P->LastLogMs >= Opt.LogMs)
			{
				P->LastLogMs = Now;
				FString FoeText;
				for (const FFoe& Fo : Foes)
				{
					FoeText += FString::Printf(TEXT(" [%d %.0f,%.0f hp %d %s wait %.0f blow %.0f]"), Fo.H, Fo.X, Fo.Y, Fo.Hp, Fo.bAttacking ? TEXT("atk") : (Fo.bGate ? TEXT("gate") : TEXT("rdy")), Fo.WaitAhead, Fo.BlowInMs);
				}
				S->AddEvent(TEXT("game"), FString::Printf(TEXT("probe: squad %s Dink %.0f,%.0f life %d;%s goal %d,%d step %.1f,%.1f hold %d"),
					Mode, Dk2.X, Dk2.Y, Fact(TEXT("life")), *FoeText, GoalC.X, GoalC.Y, X, Y, int32(P->HoldUntilMs - Now)));
			}
			if (FCString::Strcmp(Mode, TEXT("strike")) != 0 || FMath::Abs(Dk2.X - GoalC.X) > 3.5 || FMath::Abs(Dk2.Y - GoalC.Y) > 3.5)
			{
				return;
			}
			// At the strike cell: face the monster whose fist box holds the cell (the lowest hit points first) and swing.
			for (int32 K = 0; K < Foes.Num(); ++K)
			{
				if (FistHits(Foes[K], Dk2.X, Dk2.Y) && (StrikeFoe == INDEX_NONE || Foes[K].Hp < Foes[StrikeFoe].Hp)) { StrikeFoe = K; }
			}
			if (StrikeFoe == INDEX_NONE)
			{
				return;
			}
			Face(Screen, Dk2.X, Dk2.Y, FaceDirTo(Foes[StrikeFoe], Dk2.X, Dk2.Y));
			if (Now >= P->NextPunchMs && ArmFists())
			{
				G->PlayerAttack();
				P->NextPunchMs = Now + 450.0;
				P->HoldUntilMs = Now + 400.0;
			}
		}
		/**
		 * Running circles (the three knights of SCR_521: 100 hit points each as the remake runs s3-camps.c, defense 6, 60 px/s straight, and a
		 * fireball does 2-3). Dink walks 180 px/s, the chasers steer at where he is (pure pursuit at 85 px/s at best): on a circle of radius R
		 * they settle on a smaller one inside, and stay at least about 0.7 R from him (simulated). So he runs the track, never stopping except
		 * to fire: the moment a charged fireball has a clear row or column through a chaser (40-260 px) he turns and casts, else he runs on.
		 * A chaser inside Danger sends him to the free cell farthest from all of them. The walk goes over the same 6 px grid as the others.
		 */
		void OrbitFight(const FOrbitOpts& Opt = FOrbitOpts()) const
		{
			G->SyncDinkFromActor();
			const FDinkSprite& Dk = D->GetDink();
			const int32 Screen = Dk.Screen;
			const double Now = S->GetNowMs();
			const double Dt = P->LastWalkMs < 0.0 ? 17.0 : FMath::Clamp(Now - P->LastWalkMs, 0.0, 100.0);
			P->LastWalkMs = Now;
			if (Now < P->HoldUntilMs)
			{
				return;
			}
			BuildGrid(Screen);
			struct FChaser { int32 Handle; double X, Y; };
			TArray<FChaser> Ks;
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				const FDinkSprite& O = Pair.Value;
				const int32 Brain = O.GetProp(TEXT("brain"));
				if (Pair.Key != 1 && O.bActive && !O.bText && O.Screen == Screen && (Brain == 9 || Brain == 10) && O.GetProp(TEXT("hitpoints")) > 0)
				{
					Ks.Add(FChaser{ Pair.Key, O.X, O.Y });
				}
			}
			if (Ks.Num() == 0)
			{
				return;
			}
			auto Cheb = [](double Ax, double Ay, double Bx, double By) { return FMath::Max(FMath::Abs(Ax - Bx), FMath::Abs(Ay - By)); };
			auto Nearest = [&Ks, &Cheb](double X, double Y)
			{
				double Best = 1e9;
				for (const FChaser& K : Ks) { Best = FMath::Min(Best, Cheb(K.X, K.Y, X, Y)); }
				return Best;
			};
			const double R = Opt.Radius;
			const double Ang = FMath::Atan2((Dk.Y - Opt.CentreY) / R, (Dk.X - Opt.CentreX) / Opt.RadiusX); // the ellipse's parameter
			/** The parameter's step for Px px along the track at the current parameter. */
			auto Step = [&Opt, R](double A, double Px) { return Px / FMath::Max(FMath::Sqrt(FMath::Square(Opt.RadiusX * FMath::Sin(A)) + FMath::Square(R * FMath::Cos(A))), 1.0); };
			auto OnTrack = [&Opt, R](double A) { return FVector2D(Opt.CentreX + Opt.RadiusX * FMath::Cos(A), Opt.CentreY + R * FMath::Sin(A)); };
			if (P->OrbitDir == 0)
			{
				// The way round that keeps him farthest from the chasers over the next 2 s (they close in on where he started at 85 px/s).
				double BestMin = -1.0;
				for (const int32 Way : { 1, -1 })
				{
					double Min = 1e9;
					for (double Tau = 0.0; Tau <= 2.0; Tau += 0.1)
					{
						const FVector2D Q = OnTrack(Ang + Way * Step(Ang, 180.0 * Tau));
						for (const FChaser& K : Ks)
						{
							const double Dx = Dk.X - K.X, Dy = Dk.Y - K.Y;
							const double L = FMath::Max(FMath::Sqrt(Dx * Dx + Dy * Dy), 1.0);
							const double Moved = FMath::Min(85.0 * Tau, L);
							Min = FMath::Min(Min, FVector2D::Distance(Q, FVector2D(K.X + Dx / L * Moved, K.Y + Dy / L * Moved)));
						}
					}
					if (Min > BestMin) { BestMin = Min; P->OrbitDir = Way; }
				}
			}
			const double Near = Nearest(Dk.X, Dk.Y);
			const bool bCharged = Fact(TEXT("magic_cost")) > 0 && Fact(TEXT("magic_level")) >= Fact(TEXT("magic_cost"));
			if (bCharged && Near >= Opt.FireClear)
			{
				int32 Pick = 0, Dir = 0;
				double Gap = 1e9;
				for (const FChaser& K : Ks)
				{
					const double Dx = K.X - Dk.X, Dy = K.Y - Dk.Y;
					int32 D1 = 0;
					if (FMath::Abs(Dy) <= Opt.LineTol && FMath::Abs(Dx) >= 40.0 && FMath::Abs(Dx) <= 260.0) { D1 = Dx > 0 ? 6 : 4; }
					else if (FMath::Abs(Dx) <= Opt.LineTol && FMath::Abs(Dy) >= 40.0 && FMath::Abs(Dy) <= 260.0) { D1 = Dy > 0 ? 2 : 8; }
					if (D1 != 0 && FMath::Max(FMath::Abs(Dx), FMath::Abs(Dy)) < Gap
						&& LineClear(Screen, FMath::RoundToInt32(Dk.X), FMath::RoundToInt32(Dk.Y), D1, K.Handle, MissileObstacles(Screen, K.Handle)))
					{
						Pick = K.Handle;
						Dir = D1;
						Gap = FMath::Max(FMath::Abs(Dx), FMath::Abs(Dy));
					}
				}
				if (Pick != 0)
				{
					Face(Screen, Dk.X, Dk.Y, Dir);
					if (G->PlayerCastMagic())
					{
						++P->Casts;
						P->HoldUntilMs = Now + Opt.CastHoldSec * 1000.0;
						S->AddEvent(TEXT("game"), FString::Printf(TEXT("probe: orbit fire Dink %.0f,%.0f dir %d at %d (%.0f px)"), Dk.X, Dk.Y, Dir, Pick, Gap));
						return;
					}
				}
			}
			// Where to: the point on the track ahead of him, as near as a free cell gets; in blow range, the free cell farthest from every chaser.
			const int32 DinkCell = CellAt(Dk.X, Dk.Y);
			TArray<double> DistDink;
			TArray<int32> Parent;
			WalkDistances(DinkCell, 0.0, DistDink, &Parent);
			const FVector2D Aim = OnTrack(Ang + P->OrbitDir * Step(Ang, Opt.LookPx));
			int32 Goal = INDEX_NONE;
			const TCHAR* Mode = TEXT("run");
			double Best = 1e9;
			if (Near < Opt.Danger)
			{
				Mode = TEXT("flee");
				Best = -1e9;
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (DistDink[I] < 0.0 || DistDink[I] > 160.0) { continue; }
					const FIntPoint C = CellCentre(I);
					// Not the corner (the farthest cell from three chasers always is one, and they follow him in): room on every side counts.
					const double Edge = FMath::Min(FMath::Min(C.X - 20.0, 619.0 - C.X), FMath::Min<double>(C.Y, 399.0 - C.Y));
					const double Score = FMath::Min(Nearest(C.X, C.Y), 200.0) + 0.8 * FMath::Min(Edge, 70.0) - 0.15 * DistDink[I];
					if (Score > Best) { Best = Score; Goal = I; }
				}
			}
			else
			{
				for (int32 I = 0; I < Cols * Rows; ++I)
				{
					if (DistDink[I] < 0.0) { continue; }
					const FIntPoint C = CellCentre(I);
					const double Gap = FVector2D::Distance(FVector2D(C), Aim) + (Nearest(C.X, C.Y) < Opt.Danger + 10.0 ? 400.0 : 0.0);
					if (Gap < Best) { Best = Gap; Goal = I; }
				}
			}
			if (Goal == INDEX_NONE)
			{
				return;
			}
			TArray<int32> Path;
			for (int32 I = Goal; I != INDEX_NONE && I != DinkCell; I = Parent[I])
			{
				Path.Insert(I, 0);
				if (Path.Num() > Cols * Rows) { break; }
			}
			double Budget = WalkPxPerMs * Dt;
			double X = Dk.X, Y = Dk.Y;
			for (const int32 I : Path)
			{
				const FIntPoint C = CellCentre(I);
				const double Seg = FVector2D::Distance(FVector2D(X, Y), FVector2D(C));
				if (Seg <= Budget) { X = C.X; Y = C.Y; Budget -= Seg; }
				else { const double A = Budget / FMath::Max(Seg, 1e-6); X += (C.X - X) * A; Y += (C.Y - Y) * A; break; }
			}
			if (FMath::Abs(X - Dk.X) > 0.01 || FMath::Abs(Y - Dk.Y) > 0.01)
			{
				GB->GotoScreen(Screen, X - 20.0, Y);
				G->SyncDinkFromActor();
				if (FMath::Abs(D->GetDink().X - X) > 3.0 || FMath::Abs(D->GetDink().Y - Y) > 3.0)
				{
					P->Free[CellAt(X, Y)] = 0; // the capsule did not fit: not walkable
				}
			}
			if (Now - P->LastLogMs >= 100.0)
			{
				P->LastLogMs = Now;
				const FIntPoint GC = CellCentre(Goal);
				S->AddEvent(TEXT("game"), FString::Printf(TEXT("probe: orbit %s Dink %.0f,%.0f life %d charge %d; %d chasers, nearest %.0f; aim %.0f,%.0f goal %d,%d"), Mode, D->GetDink().X, D->GetDink().Y,
					Fact(TEXT("life")), Fact(TEXT("magic_level")), Ks.Num(), Near, Aim.X, Aim.Y, GC.X, GC.Y));
			}
		}
		/** No hardness within 24 px: not in a wall and clear of warp hardboxes, whose triggers reach past them. */
		bool Clear(int32 Screen, int32 X, int32 Y) const
		{
			for (int32 Dy = -24; Dy <= 24; Dy += 4)
			{
				for (int32 Dx = -24; Dx <= 24; Dx += 4)
				{
					if (G->GetHard(Screen, X + Dx, Y + Dy) != 0)
					{
						return false;
					}
				}
			}
			return true;
		}
		bool ArmFists() const
		{
			// A sword (chapter 11 buys and arms the longsword) is the melee weapon from then on: the fists are only armed over anything else (a bomb, the bow).
			const FName Armed = D->GetInventory()->GetArmedItem();
			if (Armed == TEXT("item-sw1") || Armed == TEXT("item-sw2") || Armed == TEXT("item-sw3"))
			{
				return true;
			}
			if (Armed != TEXT("item-fst"))
			{
				const int32 FistSlot = Slot(TEXT("item-fst"));
				return FistSlot != 0 && G->ArmItemSlot(FistSlot);
			}
			return true;
		}
		int32 SpriteWithScript(const TCHAR* Script) const
		{
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				if (Pair.Value.bActive && Pair.Value.Script == FName(Script))
				{
					return Pair.Key;
				}
			}
			return 0;
		}
		bool Said(const TCHAR* Text) const
		{
			return S->Events.ContainsByPredicate([Text](const FDinkNarrativeEvent& E) { return E.Kind == TEXT("say") && E.Text == Text; });
		}
		/**
		 * The harm casts of the dragons (en-drag.c, s7-drag.c `attack`) hurt for their strength - defense wherever Dink stands: no range, no dodge. He drinks an
		 * elixir (item-eli, life +20, Terris 25 gold) as soon as one more cast would kill him (life <= Damage), and takes up the sword again afterwards.
		 * Returns true when this frame was spent on the elixir.
		 */
		bool DrinkAndKeepSword(int32 CastStrength) const
		{
			const double NowMs = S->GetNowMs();
			const int32 Damage = FMath::Max(1, CastStrength - Fact(TEXT("defense")));
			if (Fact(TEXT("life")) > 0 && Fact(TEXT("life")) <= Damage && NowMs - P->LastDrinkMs > 500.0)
			{
				if (const int32 Eli = Slot(TEXT("item-eli")))
				{
					G->ArmItemSlot(Eli);
					if (G->PlayerAttack()) { P->LastDrinkMs = NowMs; }
					return true;
				}
			}
			if (D->GetInventory()->GetArmedItem() != TEXT("item-sw1") && NowMs - P->LastDrinkMs > 200.0)
			{
				if (const int32 Sword = Slot(TEXT("item-sw1"))) { G->ArmItemSlot(Sword); }
			}
			return false;
		}
		int32 CountItem(FName Item) const
		{
			int32 N = 0;
			for (int32 i = 0; i < FDinkInventoryState::NumItemSlots; ++i)
			{
				N += D->GetInventory()->GetItemAt(i) == Item ? 1 : 0;
			}
			return N;
		}
		int32 Slot(FName Item) const
		{
			for (int32 i = 0; i < FDinkInventoryState::NumItemSlots; ++i)
			{
				if (D->GetInventory()->GetItemAt(i) == Item)
				{
					return i + 1;
				}
			}
			return 0;
		}
		/**
		 * Everything a save must bring back, as sorted text lines: screen, pawn position, every fact, the stats component,
		 * both inventories and what is armed, every world override, the world clock, the live script instances. A chapter
		 * writes it when it ends and the next chapter compares it with the same dump taken right after loading the slot.
		 */
		FString StateDump() const
		{
			TArray<FString> L;
			const ADinkScreenVolume* V = GB->GetCurrentScreen();
			L.Add(FString::Printf(TEXT("screen player_map %d greybox %d"), Fact(TEXT("player_map")), V ? V->ScreenNumber : 0));
			const FVector At = Pawn->GetActorLocation();
			L.Add(FString::Printf(TEXT("pawn %.1f %.1f %.1f yaw %.1f"), At.X, At.Y, At.Z, Pawn->GetActorRotation().Yaw));
			TArray<FName> Names;
			F->GetAllFacts().GetKeys(Names);
			Names.Sort([](const FName& A, const FName& B) { return A.LexicalLess(B); });
			for (const FName& N : Names)
			{
				L.Add(FString::Printf(TEXT("fact %s=%d"), *N.ToString(), F->GetFact(N)));
			}
			if (const UDinkStatsComponent* St = Pawn->FindComponentByClass<UDinkStatsComponent>())
			{
				const FDinkStats& K = St->Stats;
				L.Add(FString::Printf(TEXT("stats str %d def %d magic %d life %d/%d level %d exp %d gold %d charge %d/%d"), K.Strength, K.Defense, K.Magic, K.Life, K.LifeMax, K.Level, K.Exp, K.Gold, K.MagicLevel, K.MagicCost));
			}
			const UDinkInventoryComponent* Inv = D->GetInventory();
			for (int32 i = 0; i < FDinkInventoryState::NumItemSlots; ++i)
			{
				L.Add(FString::Printf(TEXT("item %d %s"), i + 1, *Inv->GetItemAt(i).ToString()));
			}
			for (int32 i = 0; i < FDinkInventoryState::NumMagicSlots; ++i)
			{
				L.Add(FString::Printf(TEXT("magic %d %s"), i + 1, *Inv->GetMagicAt(i).ToString()));
			}
			L.Add(FString::Printf(TEXT("armed %s slot %d, spell %s slot %d"), *Inv->GetArmedItem().ToString(), Inv->GetArmedItemSlot(), *Inv->GetArmedMagic().ToString(), Inv->GetArmedMagicSlot()));
			if (const UDinkWorldStateSubsystem* W = World->GetGameInstance()->GetSubsystem<UDinkWorldStateSubsystem>())
			{
				L.Add(FString::Printf(TEXT("world clock %lld ms, %d overrides"), W->GetGameTimeMs(), W->NumOverrides()));
				for (const FDinkWorldOverride& O : W->ExportOverrides())
				{
					L.Add(FString::Printf(TEXT("override %s type %d at %lld variant %s"), *O.Origin.ToString(), static_cast<int32>(O.Type), O.SetAtMs, *O.Variant.ToString()));
				}
				for (const FDinkScreenExitTime& E : W->ExportScreenExitTimes())
				{
					L.Add(FString::Printf(TEXT("exit screen %d at %lld"), E.Screen, E.ExitedAtMs));
				}
			}
			TArray<FString> Live;
			for (const TUniquePtr<FDinkScriptInstance>& I : S->GetInstances())
			{
				if (I->IsAlive())
				{
					Live.Add(FString::Printf(TEXT("instance %s attached %d screen %d state %d"), *I->Script.ToString(), I->AttachedTo, I->Screen, static_cast<int32>(I->State)));
				}
			}
			Live.Sort();
			L.Append(Live);
			return FString::Join(L, TEXT("\n"));
		}
		FString State() const
		{
			const ADinkScreenVolume* V = GB->GetCurrentScreen();
			FString Out = FString::Printf(TEXT("greybox screen %d, Dink sprite screen %d, pawn at %s; "), V ? V->ScreenNumber : 0, D->GetDink().Screen, *Pawn->GetActorLocation().ToCompactString());
			Out += FString::Printf(TEXT("wizard_see %d, wizard_again %d, s2-aunt %d, caveguy %d, strength %d, defense %d, magic %d, level %d, spell charge %d/%d, "), Fact(TEXT("wizard_see")), Fact(TEXT("wizard_again")),
				Fact(TEXT("s2-aunt")), Fact(TEXT("caveguy")), Fact(TEXT("strength")), Fact(TEXT("defense")), Fact(TEXT("magic")), Fact(TEXT("level")), Fact(TEXT("magic_level")), Fact(TEXT("magic_cost")));
			Out += FString::Printf(TEXT("story %d, pig_story %d, old_womans_duck %d, nuttree %d, letter %d, gold %d, life %d/%d, exp %d, player_map %d, vision %d, Dink %s at %.0f,%.0f, menu %s; scripts:"),
				Fact(TEXT("story")), Fact(TEXT("pig_story")), Fact(TEXT("old_womans_duck")), Fact(TEXT("nuttree")), Fact(TEXT("letter")), Fact(TEXT("gold")),
				Fact(TEXT("life")), Fact(TEXT("lifemax")), Fact(TEXT("exp")), Fact(TEXT("player_map")), Fact(TEXT("vision")),
				D->GetDink().bFrozen ? TEXT("frozen") : TEXT("free"), D->GetDink().X, D->GetDink().Y, S->GetActiveMenu() ? TEXT("open") : TEXT("none"));
			for (const TUniquePtr<FDinkScriptInstance>& I : S->GetInstances())
			{
				if (I->State != EDinkInstanceState::Idle)
				{
					Out += FString::Printf(TEXT(" %s.%s(state %d block %d"), *I->Script.ToString(), *I->Procedure.ToString(), static_cast<int32>(I->State), static_cast<int32>(I->Block));
					Out += I->State == EDinkInstanceState::Blocked && I->Block == EDinkBlock::Time ? FString::Printf(TEXT(" until %.0f)"), I->BlockUntilMs) : FString(TEXT(")"));
				}
			}
			Out += FString::Printf(TEXT("; game time %.0f ms, update_status %d, status ticks %lld"), S->GetNowMs(), Fact(TEXT("update_status")), G->StatusTicks);
			if (const int32 Jack = SpriteWithScript(TEXT("s2-jack")))
			{
				const FDinkSprite* J = D->FindSprite(Jack);
				Out += FString::Printf(TEXT("; Jack (%d) at %.0f,%.0f hp %d brain %d target %d touch %d"), Jack, J->X, J->Y, J->GetProp(TEXT("hitpoints")), J->GetProp(TEXT("brain")),
					J->GetProp(TEXT("target")), J->GetProp(TEXT("touch_damage")));
			}
			TArray<FString> Last;
			for (int32 i = S->Events.Num() - 1; i >= 0 && Last.Num() < 4; --i)
			{
				if (S->Events[i].Kind == TEXT("say"))
				{
					Last.Insert(TEXT("\"") + S->Events[i].Text + TEXT("\""), 0);
				}
			}
			Out += TEXT("; last lines: ") + FString::Join(Last, TEXT(" / "));
			TArray<FString> Game;
			for (int32 i = S->Events.Num() - 1; i >= 0 && Game.Num() < 40; --i)
			{
				if (S->Events[i].Kind == TEXT("game"))
				{
					Game.Insert(FString::Printf(TEXT("%.0f %s"), S->Events[i].TimeMs, *S->Events[i].Text), 0);
				}
			}
			Out += TEXT("\n  last gameplay events: ") + FString::Join(Game, TEXT(" | "));
			return Out;
		}
	};

	/** One step: Act runs once when it starts (and again every Retry seconds if set); Done ends it. */
	struct FStep
	{
		FString Name;
		TFunction<void(FCtx&)> Act;
		TFunction<bool(FCtx&)> Done;
		double Timeout = 30.0;
		double Retry = 0.0;
		/** A fight: the player keeps acting while other scripts wait (a spell's explosion, a hit line), only not while Dink is frozen or a menu is open. */
		bool bFight = false;
		/** Menu answers by option text, in order. */
		TArray<FString> Answers;
	};

	/** One chapter of the play-through: where it starts (a new game, or the slot the previous chapter wrote), where it saves. */
	struct FChapterSpec
	{
		int32 Number = 1;
		FString Title;
		FString LoadSlot;
		FString SaveSlot;
		/** Report file stem under Saved/Narrative. */
		FString Stem;
	};
	inline FChapterSpec MakeChapter(int32 Number, const TCHAR* Title)
	{
		FChapterSpec C;
		C.Number = Number;
		C.Title = Title;
		C.LoadSlot = Number > 1 ? FString::Printf(TEXT("probe_ch%d"), Number - 1) : FString();
		C.SaveSlot = FString::Printf(TEXT("probe_ch%d"), Number);
		C.Stem = Number == 1 ? FString(TEXT("stonebrook_probe")) : FString::Printf(TEXT("probe_ch%d"), Number);
		return C;
	}

	class FProbeCommand : public IAutomationLatentCommand
	{
	public:
		/**
		 * StopAfterSteps: end the run (successfully) once that many steps are done; TraceOut: keep the trace in memory
		 * instead of writing the report and trace files (the repeatability test compares two runs).
		 */
		FProbeCommand(FAutomationTestBase* InTest, const FChapterSpec& InSpec, int32 InExpectedSteps, int32 InStopAfterSteps = INDEX_NONE, FString* InTraceOut = nullptr)
			: Test(InTest), Spec(InSpec), ExpectedSteps(InExpectedSteps), StopAfterSteps(InStopAfterSteps), TraceOut(InTraceOut), Began(FPlatformTime::Seconds())
		{
			BuildSteps();
		}

		int32 NumSteps() const { return Steps.Num(); }

		virtual bool Update() override
		{
			const double Wall = FPlatformTime::Seconds();
			if (!bWallBegun)
			{
				// The wall-clock start-up limits count from the first frame of this command, not from its construction: a test that queues two
				// runs builds both up front, and the second run's limit was spent by the first (RepeatableChapter failed so on a loaded machine).
				bWallBegun = true;
				Began = Wall;
			}
			FCtx C;
			C.P = &Probe;
			C.World = ProbeWorld();
#if !WITH_EDITOR
			// A packaged game started with -DinkProbeHold waits here, paused, until the probe starts (see DinkProbeHold.h).
			if (DinkProbeHold::Process(C.World))
			{
				return false;
			}
#endif
			APlayerController* PC = C.World ? C.World->GetFirstPlayerController() : nullptr;
			C.Pawn = PC ? PC->GetPawn() : nullptr;
			C.S = C.World && C.World->GetGameInstance() ? C.World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
			if (!C.Pawn || !C.S || !C.S->IsReady())
			{
				if (Wall - Began > 60.0)
				{
					RestoreTimeStep();
					Test->AddError(TEXT("PIE did not start"));
					return true;
				}
				return false;
			}
			C.D = C.S->GetDirector();
			C.G = C.S->GetGameplay();
			C.GB = C.World->GetSubsystem<UDinkGreyboxSubsystem>();
			C.F = C.S->GetFacts();
			// Every time below is game time (the story clock, which follows the world's), never the wall clock: the
			// editor runs with a fixed 60 Hz step (see RunTest), so the same seed plays the same game every run.
			const double Now = C.S->GetNowMs() / 1000.0;
			if (!Spec.LoadSlot.IsEmpty() && !bLoaded)
			{
				// A chapter after the first starts from the slot the previous chapter wrote. The editor starts a new game
				// first (newgame.c, the mother's scene): let that begin, then load over it, as a player would from the title.
				// (&story 1: the mother's opening scene has begun, so newgame.c has run: a load before that was undone by the new game starting
				// after it, in the second PIE session of one editor. A story clock past 10 s is the previous session's world still
				// being torn down: PlayWorld pointed at it for a few frames and the save was loaded into a world that then vanished.)
				if (C.S->bNewGamePending || !C.GB->GetCurrentScreen() || C.Fact(TEXT("story")) < 1
					|| C.S->GetNowMs() > 10000.0)
				{
					if (Wall - Began > 60.0)
					{
						RestoreTimeStep();
						Test->AddError(TEXT("the new game did not start"));
						return true;
					}
					return false;
				}
				UDinkSaveSubsystem* Saves = C.World->GetGameInstance()->GetSubsystem<UDinkSaveSubsystem>();
				UDinkSaveGame* Loaded = Saves ? Saves->LoadFromSlot(Spec.LoadSlot, C.Pawn) : nullptr;
				if (!Loaded)
				{
					RestoreTimeStep();
					Test->AddError(FString::Printf(TEXT("save slot '%s' is missing or does not load: run chapter %d first (its test writes it)"), *Spec.LoadSlot, Spec.Number - 1));
					return true;
				}
				bLoaded = true;
				LoadedScreen = Loaded->CurrentScreen;
				// What was loaded must be what was saved: the same state dump, taken before a frame runs.
				const FString Before = FPaths::ProjectSavedDir() / FString::Printf(TEXT("Narrative/probe_ch%d_state.txt"), Spec.Number - 1);
				FString Expected;
				if (FFileHelper::LoadFileToString(Expected, *Before))
				{
					const FString RestoredDump = C.StateDump();
					TArray<FString> A, B;
					Expected.ParseIntoArrayLines(A, false);
					RestoredDump.ParseIntoArrayLines(B, false);
					int32 Bad = 0;
					for (int32 i = 0; i < FMath::Max(A.Num(), B.Num()); ++i)
					{
						const FString& X = A.IsValidIndex(i) ? A[i] : FString(TEXT("(missing)"));
						const FString& Y = B.IsValidIndex(i) ? B[i] : FString(TEXT("(missing)"));
						if (X != Y && Bad++ < 8)
						{
							Test->AddError(FString::Printf(TEXT("loading '%s' did not restore the saved game: saved \"%s\", loaded \"%s\""), *Spec.LoadSlot, *X, *Y));
						}
					}
					Test->AddInfo(FString::Printf(TEXT("loaded slot '%s': %d state lines compared with chapter %d's end, %d differ"), *Spec.LoadSlot, A.Num(), Spec.Number - 1, Bad));
				}
				else
				{
					Test->AddWarning(FString::Printf(TEXT("no %s: the loaded game was not compared with the saved one"), *Before));
				}
				Test->TestEqual(TEXT("the greybox is on the saved screen right after the load"), C.GB->GetCurrentScreen() ? C.GB->GetCurrentScreen()->ScreenNumber : 0, LoadedScreen);
				// The trace of a loaded chapter starts at the load: what the new game played in the frames before it (the mother's scene, a
				// number of frames that depends on how long PIE took to start) is not part of this chapter's game.
				C.S->Events.Reset();
				return false;
			}
			if (!bStarted)
			{
				bStarted = true;
				// Where in the game's life the probe began: the same in PIE and in a packaged process (the parity check needs it).
				Test->AddInfo(FString::Printf(TEXT("probe begins at story clock %.4f ms, world time %.6f s"), C.S->GetNowMs(), C.World->GetTimeSeconds()));
				C.G->Adaptation.bEnabled = false; // the probe plays the original's rules (Classic) from a fixed seed
				if (Spec.LoadSlot.IsEmpty())
				{
					C.G->SetRandomSeed(1997); // a loaded chapter continues the saved stream (the save holds the generator's state)
				}
				C.S->MaxEvents = 2000000; // keep every event for the trace
				StepStart = Now;
				StartedWall = Wall;
			}
			// The player skips text and answers menus the step asks for.
			C.S->SkipDialogue();
			if (const FDinkMenu* Menu = C.S->GetActiveMenu(); Menu && Steps.IsValidIndex(Current))
			{
				TArray<FString>& Answers = Steps[Current].Answers;
				int32 Pick = INDEX_NONE;
				for (int32 a = 0; a < Answers.Num() && Pick == INDEX_NONE; ++a)
				{
					for (int32 i = 0; i < Menu->Choices.Num(); ++i)
					{
						if (Menu->Choices[i].Text == Answers[a])
						{
							Pick = i;
							Answers.RemoveAt(a);
							break;
						}
					}
				}
				C.S->Choose(Pick == INDEX_NONE ? Menu->Choices.Num() - 1 : Pick);
			}
			if (!Steps.IsValidIndex(Current))
			{
				return Finish(C, TEXT("every step done"));
			}
			FStep& Step = Steps[Current];
			const double Elapsed = Now - StepStart;
			if (!bActed || (Step.Retry > 0.0 && Now - LastAct >= Step.Retry && C.Idle() && (Step.bFight || !C.Busy())))
			{
				if (Step.Act && (C.Idle() || !bActed))
				{
					Step.Act(C);
				}
				bActed = true;
				LastAct = Now;
				if (!Step.bFight)
				{
					return false;
				}
				// A fight acts every frame: it must still finish and time out (the old loop never reached the
				// checks below while a fight's retry was due on every frame).
			}
			if (Step.Done(C))
			{
				Log.Add(FString::Printf(TEXT("OK   %2d %s (%.1f s game time, done at %.3f s)"), Current + 1, *Step.Name, Elapsed, Now));
				++Current;
				bActed = false;
				StepStart = Now;
				if (StopAfterSteps != INDEX_NONE && Current >= StopAfterSteps)
				{
					return Finish(C, FString::Printf(TEXT("stopped after %d steps"), StopAfterSteps));
				}
				return false;
			}
			if (Elapsed > Step.Timeout)
			{
				return Finish(C, FString::Printf(TEXT("step %d \"%s\" did not complete in %.0f s of game time. %s"), Current + 1, *Step.Name, Step.Timeout, *C.State()));
			}
			return false;
		}

	private:
		bool Finish(FCtx& C, const FString& Why)
		{
			RestoreTimeStep();
			C.Dilate(1.0f);
			Log.Add(Current >= Steps.Num() ? TEXT("DONE ") + Why : TEXT("STOP ") + Why);
			// The whole run, event by event in game time: two runs with the same seed must give the same lines
			// (diff two copies to find where runs part).
			TArray<FString> Trace;
			Trace.Reserve(C.S->Events.Num() + 1);
			Trace.Add(FString::Printf(TEXT("# Dink.Gameplay.Probe.%s trace: %d of %d steps; %d events"), Spec.Number == 1 ? TEXT("Stonebrook") : *FString::Printf(TEXT("Ch%d"), Spec.Number), Current, Steps.Num(), C.S->Events.Num()));
			for (const FDinkNarrativeEvent& E : C.S->Events)
			{
				// (Kind is an FName: lower case, as the editor shows it; a cooked game shows the engine's own "Game", "Start", "Cmd".)
				Trace.Add(FString::Printf(TEXT("%.3f %d %s %s %s"), E.TimeMs, E.InstanceId, *E.Kind.ToString().ToLower(), *E.Text, *E.Detail));
			}
			C.S->MaxEvents = 4096;
			if (TraceOut)
			{
				*TraceOut = FString::Join(Trace, TEXT("\n"));
				Test->AddInfo(FString::Printf(TEXT("repeat run ended: %s"), *Why.Left(900)));
				Test->TestTrue(FString::Printf(TEXT("the run reaches step %d (reached %d)"), StopAfterSteps, Current), Current >= StopAfterSteps);
				return true;
			}
			const FString Dir = FPaths::ProjectSavedDir() / TEXT("Narrative/");
			const FString TraceFile = Dir + Spec.Stem + TEXT("_trace.txt");
			FFileHelper::SaveStringArrayToFile(Trace, *TraceFile);
			const FString Md5 = LexToString(FMD5Hash::HashFile(*TraceFile)).Left(10);
			const FString Text = FString::Printf(TEXT("Dink.Gameplay.Probe chapter %d (%s): %d of %d steps in %.1f s of game time (%.1f s wall); trace md5 %s, %d events; final %s\n\n"), Spec.Number, *Spec.Title,
				Current, Steps.Num(), C.S->GetNowMs() / 1000.0, FPlatformTime::Seconds() - StartedWall, *Md5, C.S->Events.Num(), *C.State()) + FString::Join(Log, TEXT("\n")) + TEXT("\n");
			FFileHelper::SaveStringToFile(Text, *(Dir + Spec.Stem + TEXT(".txt")));
			Test->AddInfo(FString::Printf(TEXT("chapter %d: %d of %d steps, trace md5 %s (%d events)"), Spec.Number, Current, Steps.Num(), *Md5, C.S->Events.Num()));
			// A scripted walk past the map's edge (s2-culg.c: Dink at y 480) used to drop the pawn out of the world (no ground there, gravity on).
			Test->TestTrue(FString::Printf(TEXT("the pawn is still on the ground at the end of chapter %d (Z %.0f)"), Spec.Number, C.Pawn->GetActorLocation().Z), C.Pawn->GetActorLocation().Z > -1000.0);
			if (Current >= ExpectedSteps)
			{
				// The next chapter starts from this save, and compares what it loads with this dump.
				UDinkSaveSubsystem* Saves = C.World->GetGameInstance()->GetSubsystem<UDinkSaveSubsystem>();
				const bool bSaved = Saves && Saves->SaveToSlot(Spec.SaveSlot, C.Pawn, C.Fact(TEXT("player_map")));
				Test->TestTrue(FString::Printf(TEXT("the end of chapter %d is saved to slot '%s'"), Spec.Number, *Spec.SaveSlot), bSaved);
				FFileHelper::SaveStringToFile(C.StateDump(), *(Dir + FString::Printf(TEXT("probe_ch%d_state.txt"), Spec.Number)));
			}
			else
			{
				// A failed chapter must not leave a slot for the next one to load: that chapter then fails with "run chapter N first".
				UGameplayStatics::DeleteGameInSlot(Spec.SaveSlot, 0);
				IFileManager::Get().Delete(*(Dir + FString::Printf(TEXT("probe_ch%d_state.txt"), Spec.Number)));
			}
			for (const FString& L : Log)
			{
				Test->AddInfo(L);
			}
			Test->TestTrue(FString::Printf(TEXT("the probe gets at least as far as before (%d steps; reached %d)"), ExpectedSteps, Current), Current >= ExpectedSteps);
			return true;
		}

		void BuildSteps()
		{
			switch (Spec.Number)
			{
			case 1: BuildChapter1(); break;
			case 2: BuildChapter2(); break;
			case 3: BuildChapter3(); break;
			case 4: BuildChapter4(); break;
			case 5: BuildChapter5(); break;
			case 6: BuildChapter6(); break;
			case 7: BuildChapter7(); break;
			case 8: BuildChapter8(); break;
			case 9: BuildChapter9(); break;
			case 10: BuildChapter10(); break;
			case 11: BuildChapter11(); break;
			case 12: BuildChapter12(); break;
			case 13: BuildChapter13(); break;
			case 14: BuildChapter14(); break;
			case 15: BuildChapter15(); break;
			case 16: BuildChapter16(); break;
			case 17: BuildChapter17(); break;
			case 18: BuildChapter18(); break;
			default: break;
			}
		}

		void Add(const TCHAR* Name, TFunction<void(FCtx&)> Act, TFunction<bool(FCtx&)> Done, double Timeout = 30.0, TArray<FString> Answers = {}, double Retry = 0.0, bool bFight = false)
		{
			FStep S;
			S.Name = Name;
			S.Act = MoveTemp(Act);
			S.Done = MoveTemp(Done);
			S.Timeout = Timeout;
			S.Answers = MoveTemp(Answers);
			S.Retry = Retry;
			S.bFight = bFight;
			Steps.Add(MoveTemp(S));
		}

		// ---- Chapter 1: Stonebrook, Martridge's trial, the toll, Jack, the prisoner's cave (new game -> SCR_625) ----
		void BuildChapter1()
		{
			Add(TEXT("new game: fists armed, mother's opening scene on SCR_001 (&story 1)"), nullptr,
				[](FCtx& C) { return C.Fact(TEXT("story")) >= 1 && C.Idle() && !C.Busy() && C.D->GetInventory()->GetArmedItem() == TEXT("item-fst"); }, 60.0);
			Add(TEXT("touch the sack of pig feed (S001_P52, s1-sack touch)"),
				[](FCtx& C) { C.StandBy(C.Placement(1, 52), 0, true); },
				[](FCtx& C) { return C.Slot(TEXT("item-pig")) != 0 && C.Idle(); }, 20.0, {}, 3.0);
			Add(TEXT("the sack's actor is gone (brain 12 vanish) and stays gone (editor_type 1)"), nullptr,
				[](FCtx& C)
				{
					for (TActorIterator<AActor> It(C.World); It; ++It)
					{
						const UDinkOriginComponent* O = UDinkOriginComponent::FindOnActor(*It);
						if (O && O->OriginId == FDinkOriginId(1, 52))
						{
							return It->IsHidden() && C.D->HandleForPlacement(1, 52) == 0;
						}
					}
					return false;
				}, 10.0);
			Add(TEXT("arm the feed (inventory)"),
				[](FCtx& C) { C.G->ArmItemSlot(C.Slot(TEXT("item-pig"))); },
				[](FCtx& C) { return C.D->GetInventory()->GetArmedItem() == TEXT("item-pig"); }, 10.0);
			Add(TEXT("walk to the pig pen (SCR_407)"),
				[](FCtx& C) { C.Goto(407, 300, 250); },
				[](FCtx& C) { return C.OnScreen(407) && C.Idle() && !C.Busy(); }, 20.0);
			Add(TEXT("throw feed in the pen (item-pig use) -> the bully's scene (&pig_story 1)"),
				[](FCtx& C) { C.Goto(407, 300, 250); C.Face(407, 300, 250, 2); C.G->PlayerAttack(); },
				[](FCtx& C) { return C.Fact(TEXT("pig_story")) == 1 && C.Idle() && !C.Busy(); }, 60.0, {}, 8.0);
			Add(TEXT("walk to Ethel's house (SCR_002)"),
				[](FCtx& C) { C.Goto(2, 330, 200); },
				[](FCtx& C) { return C.OnScreen(2) && C.Idle() && !C.Busy(); }, 20.0);
			Add(TEXT("talk to Ethel: ask after her pet, agree (&old_womans_duck 1)"),
				[](FCtx& C) { C.StandBy(C.Placement(2, 23), 25); C.S->TryTalk(C.Pawn); },
				[](FCtx& C) { return C.Fact(TEXT("old_womans_duck")) == 1 && C.Idle() && !C.Busy(); }, 40.0,
				{ TEXT("Ask after her pet"), TEXT("Agree whole heartedly") }, 6.0);
			Add(TEXT("search the woods for the duck (SCR_440/441, findduck: one visit in four)"),
				[this](FCtx& C) { const int32 Next = (++Searches % 2) ? 440 : 441; C.Goto(Next, 300, 250); },
				[](FCtx& C) { return (C.OnScreen(440) || C.OnScreen(441)) && C.Fact(TEXT("vision")) == 2; }, 120.0, {}, 2.0);
			Add(TEXT("talk to the duck: yell at it (s1-oldd, &old_womans_duck 2)"),
				[](FCtx& C) { const int32 Screen = C.Fact(TEXT("player_map")); C.StandBy(C.Placement(Screen, Screen == 440 ? 2 : 11), 25); C.S->TryTalk(C.Pawn); },
				[](FCtx& C) { return C.Fact(TEXT("old_womans_duck")) == 2 && C.Idle() && !C.Busy(); }, 40.0, { TEXT("Yell at it") }, 6.0);
			Add(TEXT("back to Ethel's: the duck is home (&old_womans_duck 4)"),
				[](FCtx& C) { C.Goto(2, 330, 200); },
				[](FCtx& C) { return C.Fact(TEXT("old_womans_duck")) == 4 && C.Idle() && !C.Busy(); }, 30.0);
			Add(TEXT("home: mother asks for AlkTree nuts (s1-h1-m main, &story 2)"),
				[](FCtx& C) { C.Goto(1, 334, 161); },
				[](FCtx& C) { return C.Fact(TEXT("story")) >= 2 && C.Idle() && !C.Busy(); }, 40.0);
			Add(TEXT("arm the fists (inventory)"),
				[](FCtx& C) { C.G->ArmItemSlot(C.Slot(TEXT("item-fst"))); },
				[](FCtx& C) { return C.D->GetInventory()->GetArmedItem() == TEXT("item-fst"); }, 10.0);
			Add(TEXT("walk to the AlkTree (SCR_474)"),
				[](FCtx& C) { C.Goto(474, 300, 200); },
				[](FCtx& C) { return C.OnScreen(474) && C.Idle() && !C.Busy(); }, 20.0);
			Add(TEXT("hit the AlkTree (S474_P01, s1-ntree hit) until a nut falls"),
				[](FCtx& C) { C.StandBy(C.Placement(474, 1), 12); C.G->PlayerAttack(); },
				[](FCtx& C) { const int32 Nut = C.SpriteWithScript(TEXT("s1-nut")); return Nut != 0 && !C.D->IsMoving(Nut); }, 40.0, {}, 2.0);
			Add(TEXT("pick up the nut (s1-nut touch: &story 3)"),
				[](FCtx& C) { C.StandBy(C.SpriteWithScript(TEXT("s1-nut")), 0, true); },
				[](FCtx& C) { return C.Fact(TEXT("story")) >= 3 && C.Idle(); }, 20.0, {}, 3.0);
			Add(TEXT("outside the house: it burns (SCR_439, s1-h1-o main)"),
				[](FCtx& C) { C.Goto(439, 600, 250); },
				[](FCtx& C) { return C.Said(TEXT("She's still in there!!")) && C.Idle() && !C.Busy(); }, 40.0);
			Add(TEXT("into the burning house (SCR_001, s1-h1-s main: &story 4)"),
				[](FCtx& C) { C.Goto(1, 334, 161); },
				[](FCtx& C) { return C.Fact(TEXT("story")) >= 4 && C.Idle() && !C.Busy(); }, 60.0);
			Add(TEXT("outside: the villagers (SCR_439, s1-h1-o main: &story 5)"),
				[](FCtx& C) { if (C.Fact(TEXT("story")) < 5) { C.Goto(439, 600, 250); } },
				[](FCtx& C) { return C.Fact(TEXT("story")) >= 5 && C.Idle() && !C.Busy(); }, 60.0);
			Add(TEXT("walk to the gravedigger (SCR_408)"),
				[](FCtx& C) { C.Goto(408, 400, 200); },
				[](FCtx& C) { return C.OnScreen(408) && C.Idle() && !C.Busy(); }, 20.0);
			Add(TEXT("talk to him: a letter came (s1-gg talk: &letter 1)"),
				[](FCtx& C) { C.StandBy(C.Placement(408, 4), 25); C.S->TryTalk(C.Pawn); },
				[](FCtx& C) { return C.Fact(TEXT("letter")) == 1 && C.Idle() && !C.Busy(); }, 40.0, {}, 6.0);
			Add(TEXT("home: read the letter (s1-h1-s, s1-ltr: &story 6)"),
				[](FCtx& C) { C.Goto(1, 334, 161); },
				[](FCtx& C) { return C.Fact(TEXT("story")) >= 6 && C.Idle() && !C.Busy(); }, 60.0);
			// Martridge's trial (s1-magic, s1-wiz, s1-mh-m, s1-cavem, s1-mh-s, s1-mh-f): where Stonebrook's gold comes from.
			Add(TEXT("walk into the apparition's clearing (SCR_376, s1-magic/s1-wiz scene: &wizard_again 1)"),
				[](FCtx& C) { C.Goto(376, 320, 380); },
				[](FCtx& C) { return C.Fact(TEXT("wizard_again")) == 1 && C.SpriteWithScript(TEXT("s1-wiz")) == 0 && C.Idle() && !C.Busy(); }, 90.0);
			Add(TEXT("walk to Martridge's hidden cabin (SCR_006)"),
				[](FCtx& C) { C.Goto(6, 330, 300); },
				[](FCtx& C) { return C.OnScreen(6) && C.Idle() && !C.Busy(); }, 20.0);
			Add(TEXT("talk to Martridge: tell him you're worthy (s1-mh-m talk: red potion, &wizard_see 2)"),
				[](FCtx& C) { C.StandBy(C.Placement(6, 23), 25); C.S->TryTalk(C.Pawn); },
				[](FCtx& C) { return C.Fact(TEXT("wizard_see")) == 2 && C.Idle() && !C.Busy(); }, 90.0, { TEXT("Tell him you're worthy") }, 6.0);
			Add(TEXT("drink the red potion (rpotion touch: &strength + 1)"),
				[](FCtx& C) { C.StandBy(C.SpriteWithScript(TEXT("rpotion")), 0, true); },
				[](FCtx& C) { return C.Fact(TEXT("strength")) >= 4 && C.Idle(); }, 20.0, {}, 3.0);
			Add(TEXT("walk into the Bonca's cave west of the hills (SCR_100, s1-cavem main)"),
				[](FCtx& C) { C.Goto(100, 150, 230); },
				[](FCtx& C) { return C.OnScreen(100) && C.SpriteWithScript(TEXT("s1-cavem")) != 0 && C.Idle() && !C.Busy(); }, 30.0);
			Add(TEXT("kill the Bonca with the fists, keeping its distance (s1-cavem die: &wizard_see 3)"),
				[](FCtx& C) { C.KiteAndPunch(C.SpriteWithScript(TEXT("s1-cavem")), 54); },
				[](FCtx& C) { return C.Fact(TEXT("wizard_see")) == 3 && C.Idle() && !C.Busy(); }, 180.0, {}, 0.05, true);
			Add(TEXT("back to the cabin: Martridge is gone, his scroll lies there (s1-mh-s main: &vision 1)"),
				[](FCtx& C) { C.Goto(6, 330, 300); },
				[](FCtx& C) { return C.OnScreen(6) && C.Fact(TEXT("vision")) == 1 && C.Idle() && !C.Busy(); }, 30.0);
			Add(TEXT("read the scroll (s1-mh-f talk: 200 gold, +1 magic, fireball, &wizard_see 4)"),
				[](FCtx& C) { C.StandBy(C.Placement(6, 24), 25); C.S->TryTalk(C.Pawn); },
				[](FCtx& C) { return C.Fact(TEXT("wizard_see")) == 4 && C.Fact(TEXT("gold")) >= 200 && C.Idle() && !C.Busy(); }, 90.0, {}, 6.0);
			Add(TEXT("walk to the toll bridge (SCR_404)"),
				[](FCtx& C) { C.Goto(404, 300, 200); },
				[](FCtx& C) { return C.OnScreen(404) && C.Idle() && !C.Busy(); }, 20.0);
			Add(TEXT("pay the toll (s1-brg2 talk, 100 gold: &story 7)"),
				[](FCtx& C) { const int32 Guard = C.SpriteWithScript(TEXT("s1-brg2")); if (Guard) { C.StandBy(Guard, 25); } C.S->TryTalk(C.Pawn); },
				[](FCtx& C) { return C.Fact(TEXT("story")) >= 7 && C.Idle(); }, 40.0, { TEXT("Pay the toll") }, 6.0);
			// Terris (s2-aunt, s2-auntp, s2-h2-s, s2-jack).
			Add(TEXT("over the bridge to Terris: Aunt Maria's house, Jack and Maria (SCR_036, s2-auntp main: &s2-aunt 1)"),
				[](FCtx& C) { C.Goto(36, 300, 230); /* inside, clear of the door warp S036_P18 */ },
				[](FCtx& C) { return C.Fact(TEXT("s2-aunt")) >= 1 && C.Idle() && !C.Busy(); }, 90.0, {}, 4.0);
			Add(TEXT("upstairs to the room she prepared (SCR_037, s2-h2-s main: &s2-aunt 2)"),
				[](FCtx& C) { C.Goto(37, 250, 280); /* clear of the stairs warp S037_P13 */ },
				[](FCtx& C) { return C.Fact(TEXT("s2-aunt")) >= 2 && C.Idle() && !C.Busy(); }, 40.0, {}, 4.0);
			Add(TEXT("back down: Jack beats Maria (s2-auntp main: &s2-aunt 3)"),
				[](FCtx& C) { C.Goto(36, 300, 230); /* inside, clear of the door warp S036_P18 */ },
				[](FCtx& C) { return C.Fact(TEXT("s2-aunt")) >= 3 && C.Idle() && !C.Busy(); }, 120.0, {}, 4.0);
			Add(TEXT("arm the fireball (inventory: magic slot 1)"),
				[](FCtx& C) { C.G->ArmMagicSlot(1); },
				[](FCtx& C) { return C.D->GetInventory()->GetArmedMagic() == TEXT("item-fb"); }, 10.0);
			Add(TEXT("kill Jack with fireballs from a distance (s2-jack: 50 hp; his hit makes him a brain-9 chaser with touch damage 10; die: &s2-aunt 4, +100 exp)"),
			// Jack's touch (10) kills a 10-life Dink at once. The player keeps away on foot (Dink walks three times Jack's
			// pace), and with the spell charged (5 s at magic 2) steps level with him where the line is clear (no wall,
			// no Maria or furniture in between) and throws a fireball.
			[](FCtx& C) { C.KiteAndCast(C.SpriteWithScript(TEXT("s2-jack"))); },
			[](FCtx& C) { return C.Fact(TEXT("s2-aunt")) >= 4 && C.Idle() && !C.Busy(); }, 300.0, {}, 0.001, true);
		Add(TEXT("the prisoner's cave (SCR_579, s2-cave main: &caveguy 1)"),
				[](FCtx& C) { C.Goto(579, 300, 300); },
				[](FCtx& C) { return C.Fact(TEXT("caveguy")) >= 1 && C.Idle() && !C.Busy(); }, 60.0, {}, 4.0);
			Add(TEXT("the bar in Terris (SCR_034, s2-bar main: the cave cult scene, &caveguy 2)"),
				[](FCtx& C) { C.Goto(34, 300, 300); },
				[](FCtx& C) { return C.Fact(TEXT("caveguy")) >= 2 && C.Idle() && !C.Busy(); }, 120.0, {}, 4.0);
			Add(TEXT("the magic teacher (S038_P22, s2-mh-m talk: &caveguy 3, or 4 with Acid Rain at &magic 5)"),
				[](FCtx& C) { C.Goto(38, 300, 260); C.StandBy(C.Placement(38, 22), 25); C.S->TryTalk(C.Pawn); },
				[](FCtx& C) { return C.Fact(TEXT("caveguy")) >= 3 && C.Idle() && !C.Busy(); }, 60.0, {}, 6.0);
			// The teacher wants &magic > 4 and Dink has 2: each ppotion (ppotion.c: &magic += 1) is a pickup the probe walks
			// onto. The three nearest Terris: the fields east of the castle (SCR_273), the southern dam country (SCR_597),
			// the cobbler's meadows (SCR_352).
			auto TouchPotion = [](FCtx& C, int32 Screen, double X, double Y)
			{
				const int32 Potion = C.OnScreen(Screen) ? C.SpriteWithScript(TEXT("ppotion")) : 0;
				if (Potion)
				{
					C.StandBy(Potion, 0, true);
				}
				else
				{
					C.Goto(Screen, X, Y);
				}
			};
			Add(TEXT("a potion of magic in the fields near Terris (SCR_273, ppotion touch: &magic 3)"),
				[TouchPotion](FCtx& C) { TouchPotion(C, 273, 300, 300); },
				[](FCtx& C) { return C.Fact(TEXT("magic")) >= 3 && C.Idle(); }, 30.0, {}, 3.0);
			Add(TEXT("a potion of magic in the southern dam country (SCR_597, ppotion touch: &magic 4)"),
				[TouchPotion](FCtx& C) { TouchPotion(C, 597, 300, 280); },
				[](FCtx& C) { return C.Fact(TEXT("magic")) >= 4 && C.Idle(); }, 30.0, {}, 3.0);
			Add(TEXT("a potion of magic in the cobbler's meadows (SCR_352, ppotion touch: &magic 5)"),
				[TouchPotion](FCtx& C) { TouchPotion(C, 352, 300, 300); },
				[](FCtx& C) { return C.Fact(TEXT("magic")) >= 5 && C.Idle(); }, 30.0, {}, 3.0);
			Add(TEXT("learn Acid Rain from him (s2-mh-m talk needs &magic > 4: &caveguy 4)"),
				[](FCtx& C) { C.Goto(38, 300, 260); C.StandBy(C.Placement(38, 22), 25); C.S->TryTalk(C.Pawn); },
				[](FCtx& C) { return C.Fact(TEXT("caveguy")) >= 4 && C.Idle() && !C.Busy(); }, 30.0, {}, 6.0);
			Add(TEXT("arm Acid Rain (inventory: magic slot 2, item-ice: cost 1000)"),
				[](FCtx& C) { C.G->ArmMagicSlot(2); },
				[](FCtx& C) { return C.D->GetInventory()->GetArmedMagic() == TEXT("item-ice"); }, 10.0);
			Add(TEXT("free the prisoner: cast Acid Rain at the idol in his cave (SCR_579, item-ice -> dam-ice -> dam-icee: &caveguy 5)"),
				// 1000 at &magic 5 charges in 200 status steps (20 s). The spell flies east from Dink and bursts on the
				// idol's hardbox (it starts at x 336), inside dam-icee's box 300,195-388,244. The burst has touch damage 4:
				// Dink stands 100 px back (from 290 it killed him: "you shall burn and kill yourself with it").
				[](FCtx& C)
				{
					C.Goto(579, 230, 218);
					C.Face(579, 230, 218, 6);
					if (C.Fact(TEXT("magic_cost")) > 0 && C.Fact(TEXT("magic_level")) >= C.Fact(TEXT("magic_cost")))
					{
						C.G->PlayerCastMagic();
					}
				},
				[](FCtx& C) { return C.Fact(TEXT("caveguy")) >= 5 && C.Idle() && !C.Busy(); }, 90.0, {}, 0.5);
			Add(TEXT("on into the next room (SCR_578, s2-cave2 main: the cult's ambush, the Mordavia scroll: &caveguy 6)"),
				// Not again once the scene has run: its scripted warp (&player_map = 625; load_screen()) put Dink on SCR_625, and a retry
				// of the walk would drag him back into the cave (the old run did that on its last frame, so its save would have been in the cave).
				[](FCtx& C) { if (C.Fact(TEXT("caveguy")) < 6) { C.Goto(578, 300, 300); } },
				[](FCtx& C) { return C.Fact(TEXT("caveguy")) >= 6 && C.OnScreen(625) && C.Idle() && !C.Busy(); }, 90.0, {}, 4.0);
		}

		// ---- Chapter 4: gold for the bow (Act B step 15's missing 227): monsters that kill each other, collected after 5-minute waits ----
		/** The loot a monster leaves (emake: mgold, lgold, gold200, sgold, 1gold, small heart, full heart, food) lying on the screen, or 0. A food drop (1 in 20 of a large one) pays nothing, but a sweep that waited for gold that never came stood in a corner for 130 s (chapter 11). */
		static int32 Drops(FCtx& C)
		{
			for (const TCHAR* Script : { TEXT("mgold"), TEXT("lgold"), TEXT("gold200"), TEXT("sgold"), TEXT("1gold"), TEXT("sheart"), TEXT("heart"), TEXT("sfood") })
			{
				if (const int32 Drop = C.SpriteWithScript(Script)) { return Drop; }
			}
			return 0;
		}

		/**
		 * One sweep of a monster screen for its loot (Feud: see BuildChapter4's comment), until gold reaches GoldTarget. Shared by chapters 4 and 11.
		 * Level-up menus that open during it are answered LevelUps.
		 */
		void AddFeud(const TCHAR* Name, int32 Screen, double X, double Y, int32 Expected, bool bPen, int32 GoldTarget, const TArray<FString>& LevelUps)
		{
			Add(Name,
				[Screen, X, Y, Expected, bPen, GoldTarget](FCtx& C)
				{
					if (C.Fact(TEXT("gold")) >= GoldTarget) { return; }
					if (!C.OnScreen(Screen)) { C.P->Mark = -1; C.P->bSawDrop = false; C.P->LootSinceMs = -1.0; C.Goto(Screen, X, Y); return; }
					const int32 Alive = C.Hostiles(Screen);
					if (C.P->Mark < 0 && Alive >= Expected) { C.P->Mark = Alive; } // all of them have run their main
					FFightOpts O;
					// Two of them: let them fight (they walk 170 px/s on diagonals, as fast as he does: nothing could be kited). The
					// survivor wanders (nobody has targeted Dink) and is shot only when the first fireball kills it (6 damage at least), else left.
					O.bNoStrike = Alive >= 2 && !bPen;
					O.StrikeMaxHp = bPen ? MAX_int32 : 6; // fenced in (low hardness, SCR_480): they cannot come out, he shoots them across the fence
					O.bWalkReach = bPen;
					O.WanderDist = Alive >= 2 ? 0.0 : 42.0;
					O.StandDist = 170.0;
					O.PaceFactor = Alive >= 2 ? 1.42 : 0.5; // a wanderer walks where it likes: it is not coming for him
					O.MinEdge = 14.0; // the survivor sits in a corner: the only lines at it start at a wall
					if (const int32 Drop = Drops(C))
					{
						C.P->bSawDrop = true;
						if (C.P->LootSinceMs < 0.0) { C.P->LootSinceMs = C.S->GetNowMs(); }
						O.bForceGoto = C.S->GetNowMs() - C.P->LootSinceMs > 10000.0; // 10 s of waiting for the survivor to wander off is enough
						const FDinkSprite* Loot = C.D->FindSprite(Drop);
						O.bGoto = Loot != nullptr;
						if (Loot)
						{
							O.GotoAt = FIntPoint(FMath::RoundToInt32(Loot->X), FMath::RoundToInt32(Loot->Y));
							if (FVector2D::Distance(FVector2D(Loot->X, Loot->Y), FVector2D(C.D->GetDink().X, C.D->GetDink().Y)) < 30.0) { C.StandBy(Drop, 0, true); return; } // the last steps
						}
					}
					if (Alive == 0)
					{
						if (const int32 Drop = Drops(C)) { C.StandBy(Drop, 0, true); } // nothing left to fear: he walks onto it (a teleport stands in)
						return;
					}
					C.KiteFight(NAME_None, 70, O);
				},
				[Screen, bPen, GoldTarget](FCtx& C)
				{
					const bool bGold = C.Fact(TEXT("gold")) >= GoldTarget;
					const bool bDone = bGold || (C.OnScreen(Screen) && C.P->Mark >= 0 && C.P->bSawDrop && C.Hostiles(Screen) < C.P->Mark && Drops(C) == 0 && (C.Hostiles(Screen) == 0 || (!bPen && C.MostHp(Screen) > 6)));
					if (bDone && C.Idle() && !C.Busy()) { C.P->Mark = -1; return true; }
					return false;
				}, 150.0, LevelUps, 0.001, true);
		}

		// Waits in Arturous's shop (nothing there to hurt him) at 8x time dilation: game time is what the respawn clock counts, and
		// nothing is fought meanwhile.
		void AddShopWait(const TCHAR* Name, double Seconds, int32 GoldTarget)
		{
			Add(Name,
				[Seconds, GoldTarget](FCtx& C)
				{
					if (C.Fact(TEXT("gold")) >= GoldTarget) { return; }
					if (C.P->WaitUntilMs < 0.0) { C.P->WaitUntilMs = C.S->GetNowMs() + Seconds * 1000.0; }
					if (!C.OnScreen(97)) { C.Goto(97, 300, 230); } // inside, clear of the door's warp
					C.Dilate(8.0f);
				},
				[GoldTarget](FCtx& C)
				{
					if (C.Fact(TEXT("gold")) >= GoldTarget || C.S->GetNowMs() >= C.P->WaitUntilMs)
					{
						C.P->WaitUntilMs = -1.0;
						C.Dilate(1.0f);
						return true;
					}
					return false;
				}, Seconds + 30.0);
		}

		void BuildChapter4()
		{
			// 1000 for the bow (s3-st2p.c:45) and 60 for the healer before the goblins (1 gold per missing life, s2-healp.c:132).
			const int32 GoldTarget = 1060;
			// Dink is stronger now (strength 8) and the level-up menu is answered "Increase Attack" (probe_route.md 2.4).
			const TArray<FString> LevelUps = { TEXT("Increase Attack"), TEXT("Increase Attack"), TEXT("Increase Attack"), TEXT("Increase Attack") };
			// en-bong.c and en-boncd.c main: each targets get_sprite_with_this_brain(9), the other monster of the screen, so the pair fights
			// itself from the first second (the old run saw the Bong hit the Boncd for 6 and 5) and nobody hunts Dink until he hits one of
			// them (`hit` re-targets the attacker). A player who stays out of it lets them fight, and a monster killed by another still runs
			// its `die` and drops its loot (en-bong.c:89 emake large). The screen's monsters come back 5 minutes after Dink leaves it.
			auto Feud = [this, LevelUps, GoldTarget](const TCHAR* Name, int32 Screen, double X, double Y, int32 Expected, bool bPen = false)
			{
				AddFeud(Name, Screen, X, Y, Expected, bPen, GoldTarget, LevelUps);
			};
			auto Wait = [this, GoldTarget](const TCHAR* Name, double Seconds)
			{
				AddShopWait(Name, Seconds, GoldTarget);
			};
			for (int32 Round = 1; Round <= 3; ++Round)
			{
				if (Round > 1)
				{
					Wait(*FString::Printf(TEXT("round %d: wait 5 minutes in the shop (8x), the screens' monsters come back (editor_type 6)"), Round), 302.0);
				}
				Feud(*FString::Printf(TEXT("round %d: SCR_583, Bong and Boncd fight, he waits, then takes the loot"), Round), 583, 570, 60, 2);
				Feud(*FString::Printf(TEXT("round %d: SCR_480, two Bongs"), Round), 480, 570, 60, 2, true);
				Feud(*FString::Printf(TEXT("round %d: SCR_632, two Bongs"), Round), 632, 60, 380, 2);
			}
			Add(TEXT("to Arturous's shop (SCR_097), gold counted"),
				[](FCtx& C) { if (!C.OnScreen(97)) { C.Goto(97, 300, 230); } },
				[GoldTarget](FCtx& C) { return C.OnScreen(97) && C.Idle() && !C.Busy() && C.Fact(TEXT("gold")) >= GoldTarget; }, 10.0, {}, 1.0);
		}

		// ---- Chapter 5: the bow (Act B steps 15, 16, 20): Arturous, arm it, the goblin gate guard ----
		void BuildChapter5()
		{
			Add(TEXT("buy the bow from Arturous (SCR_097, s3-st2p talk: \"Buy a Bow and some arrows for $1000\": gold >= 1000, a free slot)"),
				[](FCtx& C)
				{
					if (C.P->Mark < 0) { C.P->Mark = C.Fact(TEXT("gold")); }
					if (!C.OnScreen(97)) { C.Goto(97, 300, 230); return; }
					if (const int32 Seller = C.SpriteWithScript(TEXT("s3-st2p"))) { C.StandBy(Seller, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.Slot(TEXT("item-b1")) != 0 && C.P->Mark >= 1000 && C.Fact(TEXT("gold")) == C.P->Mark - 1000 && C.Idle() && !C.Busy(); }, 60.0, { TEXT("Buy a Bow and some arrows for $1000") }, 4.0);
			Add(TEXT("arm the bow (inventory: item-b1; the guard checks the armed weapon, s3-gobg.c:80)"),
				[](FCtx& C) { C.G->ArmItemSlot(C.Slot(TEXT("item-b1"))); },
				[](FCtx& C) { return C.D->GetInventory()->GetArmedItem() == TEXT("item-b1"); }, 10.0);
			Add(TEXT("the goblin gate guard (SCR_712, s3-gobg talk: \"Ask the Goblin guard to let you in\": armed bow, &mayor 3, &gobpass 1)"),
				[](FCtx& C)
				{
					if (!C.OnScreen(712)) { C.Goto(712, 250, 380); return; }
					if (const int32 Guard = C.SpriteWithScript(TEXT("s3-gobg"))) { C.StandBy(Guard, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.Fact(TEXT("gobpass")) == 1 && C.Idle() && !C.Busy(); }, 60.0, { TEXT("Ask the Goblin guard to let you in") }, 4.0);
		}

		// ---- Chapter 6: the goblin sanctuary (Act B steps 21, 22): four goblins one at a time, then Mog ----
		void BuildChapter6()
		{
			const TArray<FString> LevelUps = { TEXT("Increase Magic"), TEXT("Increase Magic"), TEXT("Increase Magic") };
			Add(TEXT("the healer in Terris (SCR_033, s2-healp talk: \"Get healed\": 1 gold per missing life)"),
				[](FCtx& C)
				{
					if (C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax"))) { return; }
					if (!C.OnScreen(33)) { C.Goto(33, 300, 250); return; }
					if (const int32 Healer = C.Placement(33, 19)) { C.StandBy(Healer, 25); C.S->TryTalk(C.Pawn); } // the bench the script is attached to
				},
				[](FCtx& C) { return C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax")) && C.Idle(); }, 60.0, { TEXT("Get healed") }, 0.5, true); // the healer's main loops on wait(500) for ever: Busy() is always true there
			// A goblin is pulled by one fireball (its `hit` makes only it hostile, s3-gh.c:32); the others walk about (brain 16) and hurt by touch.
			auto Pull = [this, LevelUps](const TCHAR* Name, int32 Index)
			{
				Add(Name,
					[Index](FCtx& C)
					{
						if (!C.OnScreen(680)) { C.Goto(680, 600, 385); return; } // the bottom strip, from the south gate (the west lane x 20-70 is a walled-off dead end)
						FFightOpts O;
						O.Pull = C.Placement(680, Index);
						O.bWanderers = true;
						O.PaceFactor = 1.42;
						O.FireLeadSec = 0.4;
						O.MinEdge = 20.0;
						O.PaceMarginSec = 0.5;
						O.bFlee = true;
						C.KiteFight(NAME_None, 70, O);
						},
						[Index](FCtx& C) { return C.OnScreen(680) && C.Placement(680, Index) == 0 && C.Idle() && !C.Busy(); }, 150.0, LevelUps, 0.001, true);
			};
			Pull(TEXT("goblin S680_P13 (s3-gh, 40 hp, 15 px/s): pulled by a fireball from the east end of the strip, killed (+150 exp, editor_type 6)"), 13);
			Add(TEXT("out of the sanctuary to the south gate (SCR_712): the other three goblins are still walking about"),
				[](FCtx& C) { if (!C.OnScreen(712)) { C.Goto(712, 250, 380); } },
				[](FCtx& C) { return C.OnScreen(712) && C.Idle() && !C.Busy(); }, 20.0, {}, 1.0);
			// The other three goblins and Mog are chapter 7 (BuildChapter7): the goblins cannot be kited in this corridor, they are fought with
			// `DuelFight` (reach boxes, healer trips between the fights).
		}

		// ---- Chapter 7: the other three goblins of the sanctuary one at a time in melee (Act B step 21), Mog (22), the Cast camp (23); the ambush (24) is the stop ----
		void BuildChapter7()
		{
			const TArray<FString> LevelUps = { TEXT("Increase Attack"), TEXT("Increase Attack"), TEXT("Increase Attack") };
			auto Heal = [this](const TCHAR* Name)
			{
				Add(Name,
					[](FCtx& C)
					{
						if (C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax"))) { return; }
						if (!C.OnScreen(33)) { C.Goto(33, 300, 250); return; }
						if (const int32 Healer = C.Placement(33, 19)) { C.StandBy(Healer, 25); C.S->TryTalk(C.Pawn); }
					},
					[](FCtx& C) { return C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax")) && C.Idle(); }, 60.0, { TEXT("Get healed") }, 0.5, true);
			};
			auto Goblin = [this, LevelUps](const TCHAR* Name, int32 Index, bool bLast = false)
			{
				Add(Name,
					[Index, bLast](FCtx& C)
					{
						if (!C.OnScreen(680)) { C.Goto(680, 600, 385); return; }
						const int32 H = C.Placement(680, Index);
						const FDinkSprite* T = H ? C.D->FindSprite(H) : nullptr;
						if (!T) { return; }
						FDuelOpts O;
						O.CastFrom = 90.0;
						if (bLast) { O.AvoidX = 317.0; O.AvoidY = 301.0; O.AvoidR = 110.0; } // Mog appears there when this one dies (s3-mog.c:10)
						C.DuelFight(H, O);
					},
					[Index](FCtx& C) { return C.OnScreen(680) && C.Placement(680, Index) == 0 && C.Idle() && !C.Busy(); }, 150.0, LevelUps, 0.001, true);
			};
			Goblin(TEXT("goblin S680_P14 (s3-gh, 40 hp)"), 14);
			Heal(TEXT("the healer in Terris (1 gold per missing life)"));
			Goblin(TEXT("goblin S680_P11 (s3-gs, 60 hp)"), 11);
			Heal(TEXT("the healer in Terris (1 gold per missing life)"));
			Goblin(TEXT("goblin S680_P12 (s3-gs, 60 hp): the last, its death starts Mog (s3-gs.c:71)"), 12, true);
			Add(TEXT("Mog (s3-mog.c scene, en-gmog.c: 50 hp, defense 4, range 45, screenlock): the duel; his death is the warp to SCR_489 (&gobpass 5)"),
				[](FCtx& C)
				{
					if (C.OnScreen(489)) { return; }
					if (const int32 Mog = C.SpriteWithScript(TEXT("en-gmog")))
					{
						FDuelOpts O;
						O.CastFrom = 90.0;
						C.DuelFight(Mog, O);
					}
				},
				[](FCtx& C) { return C.Fact(TEXT("gobpass")) == 5 && C.OnScreen(489); }, 150.0, { TEXT("Increase Attack") }, 0.001, true);
			Add(TEXT("the Cast camp (SCR_489, s3-camp.c: Dink frozen, scripted walk and fade_down; the move over the screen's edge to SCR_521)"), nullptr,
				[](FCtx& C) { return C.OnScreen(521); }, 120.0);
			Add(TEXT("the ambush begins (SCR_521, s3-camps.c: fade_up, the scripted walk, dialogue, screenlock, three knights s3-dorks, &mayor 3 -> 4): played to the first blow, then the stop below"),
				nullptr,
				[](FCtx& C)
				{
					const int32 Knight = C.SpriteWithScript(TEXT("s3-dorks"));
					const FDinkSprite* K = Knight ? C.D->FindSprite(Knight) : nullptr;
					return C.OnScreen(521) && C.Fact(TEXT("mayor")) == 4 && C.D->bScreenLocked && K && K->GetProp(TEXT("hitpoints")) > 0 && C.Idle();
				}, 120.0);
			// The ambush fight itself is chapter 8 (BuildChapter8), the Mayor and the parade too: this chapter ends when the scene has made its first blow possible.
			// (Before the sp_script fix of 7 Nov 2026 the knights had 100 hit points here, not the original's 40: AGENTS.md pitfall 53.)
		}

		// ---- Chapter 8: the ambush of the three Cast knights (Act B step 24), the Mayor's scroll and the parade (25, &story 10) ----
		void BuildChapter8()
		{
			// The knights have the original's 40 hit points since sp_script runs main at once (pitfall 53). Their blows hit every sprite in the box, each other
			// too: `SquadFight` never stands in a blow's box (dodging those under way, keeping out of the potential box of any that could start one) and waits
			// where they come together to swing, so they kill each other (and a punch or fireball from a safe cell finishes what is left).
			Add(TEXT("the three knights (s3-dorks: 40 hp, defense 6, strength 12, touch 5): SquadFight"),
				[](FCtx& C)
				{
					FSquadOpts O;
					O.CastFrom = 90.0;
					C.SquadFight(O);
				},
				[](FCtx& C) { return C.SpriteWithScript(TEXT("s3-dorks")) == 0 && !C.D->bScreenLocked && C.Idle(); }, 150.0, { TEXT("Increase Attack"), TEXT("Increase Attack"), TEXT("Increase Attack") }, 0.001, true);
			Add(TEXT("the knights' loot (emake.large: gold lying where each fell; the screen is unlocked)"),
				[](FCtx& C) { if (const int32 Drop = Drops(C)) { C.StandBy(Drop, 0, true); } },
				[](FCtx& C) { return Drops(C) == 0 && C.Idle() && !C.Busy(); }, 30.0, {}, 0.5);
			Add(TEXT("the Mayor in Hiram's Bookstore (SCR_067, s3-mayor talk at &mayor 4: \"Show him the scroll with the plans\": &mayor 5, the parade on SCR_586 (s3-tc.c): &story 10, &mayor 6)"),
				[](FCtx& C)
				{
					if (!C.OnScreen(67) && C.Fact(TEXT("mayor")) == 4) { C.Goto(67, 360, 250); return; }
					if (const int32 Mayor = C.SpriteWithScript(TEXT("s3-mayor"))) { C.StandBy(Mayor, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.Fact(TEXT("story")) == 10 && C.Fact(TEXT("mayor")) == 6 && C.Idle() && !C.Busy(); }, 150.0, { TEXT("Show him the scroll with the plans") }, 4.0);
		}

		// ---- Chapter 9: Windemere (Act C of Docs/probe_route.md, steps 26-30): Pete's bomb, the two all-potion chests, the cracked rock ----
		void BuildChapter9()
		{
			Add(TEXT("Blistering Pete's (SCR_196, s4-st3p talk: \"See what's for sale\", \"Bomb - $20\": gold - 20, item-bom)"),
				[](FCtx& C)
				{
					if (C.P->Mark < 0) { C.P->Mark = C.Fact(TEXT("gold")); }
					if (!C.OnScreen(196)) { C.Goto(196, 300, 250); return; }
					if (const int32 Pete = C.SpriteWithScript(TEXT("s4-st3p"))) { C.StandBy(Pete, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { const bool bOk = C.Slot(TEXT("item-bom")) != 0 && C.P->Mark >= 20 && C.Fact(TEXT("gold")) == C.P->Mark - 20 && C.Idle() && !C.Busy(); if (bOk) { C.P->Mark = -1; } return bOk; }, 60.0, { TEXT("See what's for sale"), TEXT("Bomb - $20") }, 4.0);
			// A chest of the enclosure (SCR_536): the fists' hit makes the potion (ch1-ap hit: make.apotion), standing on it raises magic, strength and defense by one.
			auto Chest = [this](int32 Index, double X, double Y)
			{
				Add(*FString::Printf(TEXT("the all-potion chest S536_P%02d (ch-ap hit: apotion appears; touch: magic, strength and defense +1)"), Index),
					[Index, X, Y](FCtx& C)
					{
						if (C.P->Mark < 0) { C.P->Mark = C.Fact(TEXT("strength")); }
						if (!C.OnScreen(536)) { C.Goto(536, X, Y); return; }
						if (const int32 Potion = C.SpriteWithScript(TEXT("apotion"))) { C.StandBy(Potion, 0, true); return; }
						if (C.Placement(536, Index)) { C.StandBy(C.Placement(536, Index), 12); C.G->PlayerAttack(); }
					},
					[](FCtx& C) { const bool bOk = C.P->Mark >= 0 && C.Fact(TEXT("strength")) >= C.P->Mark + 1 && C.Idle() && !C.SpriteWithScript(TEXT("apotion")); if (bOk) { C.P->Mark = -1; } return bOk; }, 40.0, {}, 1.0);
			};
			Chest(31, 179, 200);
			Chest(29, 433, 200);
			Add(TEXT("plant the bomb by the cracked rock (SCR_536 S536_P15 s4-rock, vision 1): arm item-bom, attack: dam-bom is spawned and the bomb leaves the inventory"),
				[](FCtx& C)
				{
					if (C.Slot(TEXT("item-bom")) == 0) { return; }
					if (!C.OnScreen(536)) { C.Goto(536, 413, 120); return; }
					const int32 Rock = C.SpriteWithScript(TEXT("s4-rock"));
					if (!Rock) { return; }
					if (C.D->GetInventory()->GetArmedItem() != TEXT("item-bom")) { C.G->ArmItemSlot(C.Slot(TEXT("item-bom"))); }
					C.StandBy(Rock, 20);
					C.G->PlayerAttack();
				},
				[](FCtx& C) { return C.Slot(TEXT("item-bom")) == 0 && C.Idle(); }, 30.0, {}, 1.0);
			Add(TEXT("walk away from the fuse (3 s): the explosion hits the rock (s4-rock hit, &missle_source dam-bomn): &s4-duck 1"),
				[](FCtx& C)
				{
					if (C.Fact(TEXT("s4-duck")) == 1) { return; }
					const int32 Rock = C.SpriteWithScript(TEXT("s4-rock"));
					const FDinkSprite* R = Rock ? C.D->FindSprite(Rock) : nullptr;
					if (R && FMath::Max(FMath::Abs(R->X - C.D->GetDink().X), FMath::Abs(R->Y - C.D->GetDink().Y)) < 90.0) { C.Goto(536, 413, 300); }
				},
				[](FCtx& C) { return C.Fact(TEXT("s4-duck")) == 1 && C.Idle(); }, 30.0, {}, 0.5);
			// Act C step 31: the 27 ducks (brain 3, s4-duck, 5 hp). The first hit makes `die` (the head flies off, the body runs on headless), the second `duckdie`:
			// external("make", "foodduck") (a food sprite), and when no brain-3 sprite is left spawn("s4-end"): &s4-duck 2, &story 11, the scene of Kelly and the guard
			// (s4-end.c, Dink frozen, about 25 s). Needs `external`/`spawn` to run their script at once (pitfall 56, fixed 7 Nov 2026 night): until then the last
			// `duckdie` was cut short by the removal of the duck's sprite and the scene never started.
			Add(TEXT("the 27 ducks of the enclosure (SCR_536, s4-duck: die, then duckdie each; the last one's duckdie reaches spawn(\"s4-end\")): &s4-duck 2, &story 11"),
				[](FCtx& C)
				{
					if (!C.OnScreen(536)) { C.Goto(536, 413, 300); return; }
					if (!C.Idle()) { return; }
					int32 Target = 0;
					double Best = 1e18;
					const FDinkSprite& Dk = C.D->GetDink();
					for (const TPair<int32, FDinkSprite>& Pair : C.D->GetSprites())
					{
						const FDinkSprite& O = Pair.Value;
						if (Pair.Key != 1 && O.bActive && !O.bText && O.Screen == 536 && O.GetProp(TEXT("brain")) == 3)
						{
							const double Dist = FMath::Square(O.X - Dk.X) + FMath::Square(O.Y - Dk.Y);
							if (Dist < Best) { Best = Dist; Target = Pair.Key; }
						}
					}
					if (Target) { C.KiteAndPunch(Target, 30); }
				},
				[](FCtx& C) { return C.Fact(TEXT("s4-duck")) == 2 && C.Fact(TEXT("story")) == 11 && C.Idle() && !C.Busy(); }, 400.0, {}, 0.001, true);
		}

		/** A permanent pickup (potion, heart) touched by standing on it, or a chest opened by a punch whose potion is then touched: Fact must rise by one. */
		void AddPickup(const TCHAR* Name, int32 Screen, double X, double Y, const TCHAR* Script, const TCHAR* Fact, int32 ChestIndex)
		{
			Add(Name,
				[=](FCtx& C)
				{
					if (C.P->Mark < 0) { C.P->Mark = C.Fact(Fact); }
					if (!C.OnScreen(Screen)) { C.Goto(Screen, X, Y); return; }
					if (const int32 Potion = C.SpriteWithScript(Script)) { C.StandBy(Potion, 0, true); return; }
					if (ChestIndex && C.Placement(Screen, ChestIndex)) { C.StandBy(C.Placement(Screen, ChestIndex), 12); C.G->PlayerAttack(); }
				},
				[=](FCtx& C) { const bool bOk = C.P->Mark >= 0 && C.Fact(Fact) >= C.P->Mark + 1 && C.Idle() && !C.SpriteWithScript(Script); if (bOk) { C.P->Mark = -1; } return bOk; }, 30.0, {}, 0.5);
		}

		// ---- Chapter 10 (test `ChAJoppa`, see the name rule in AGENTS.md): the rest of Windemere's errands and Joppa Isle (Acts C-D of Docs/probe_route.md, steps 28, 32-35) ----
		void BuildChapter10()
		{
			// Step 28: the healer of Windemere (SCR_195, s4-healp: "Get healed", 1 gold per missing life). Dink left the ducks at 15/29.
			Add(TEXT("the healer in Windemere (SCR_195 s4-healp, 1 gold per missing life)"),
				[](FCtx& C)
				{
					if (C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax"))) { return; }
					if (!C.OnScreen(195)) { C.Goto(195, 300, 250); return; }
					if (const int32 Healer = C.Placement(195, 19)) { C.StandBy(Healer, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax")) && C.Idle(); }, 60.0, { TEXT("Get healed") }, 0.5, true);
			// Step 32 (optional): the three permanent pickups of the wilds and the sanctuary village: +1 strength (SCR_663 rpotion), +1 defense (SCR_603 bpotion),
			// +1 strength (SCR_742 chest box2-sp, whose potion is make.spotion = rpotion). A pickup is touched by standing on it; the chest is opened by a punch.
			auto Pickup = [this](const TCHAR* Name, int32 Screen, double X, double Y, const TCHAR* Script, const TCHAR* Fact, int32 ChestIndex)
			{
				AddPickup(Name, Screen, X, Y, Script, Fact, ChestIndex);
			};
			Pickup(TEXT("the strength potion of the Windemere wilds (SCR_663 S663_P06 rpotion: strength +1)"), 663, 352, 100, TEXT("rpotion"), TEXT("strength"), 0);
			Pickup(TEXT("the defense potion of the marshes (SCR_603 S603_P02 bpotion: defense +1)"), 603, 80, 300, TEXT("bpotion"), TEXT("defense"), 0);
			Pickup(TEXT("the chest of the sanctuary village (SCR_742 S742_P16 box2-sp: a punch, then the potion it makes: strength +1)"), 742, 460, 190, TEXT("rpotion"), TEXT("strength"), 16);
			// Step 33: Joppa. The route walks the tunnel (SCR_537 door -> 163 -> 259 -> 258 -> 257 -> 483 -> 451 -> 419); the probe teleports to SCR_419, whose base
			// script `s5-jops` says "Weird.  This town looks deserted." (&s5-jop 0 -> 1) after 900 ms. Needs &story > 10 (the stairs of SCR_163 only exist then).
			Add(TEXT("Joppa (SCR_419, s5-jops: &s5-jop 0 -> 1, \"Weird.  This town looks deserted.\")"),
				[](FCtx& C) { if (!C.OnScreen(419)) { C.Goto(419, 300, 300); } },
				[](FCtx& C) { return C.OnScreen(419) && C.Fact(TEXT("s5-jop")) == 1 && C.Idle(); }, 30.0, {}, 0.5);
			// Step 34: the basement (door S419_P02 -> SCR_228 -> stairs S228_P23 -> SCR_229, base `s5-base`: the hiding parents, `s5-guy` main, 12 s, Dink frozen): &s5-jop 2.
			Add(TEXT("the basement (SCR_229, s5-base creates s5-guy and s5-mom, the scene of the hiding parents): &s5-jop 1 -> 2"),
				[](FCtx& C) { if (!C.OnScreen(229) && C.Fact(TEXT("s5-jop")) == 1) { C.Goto(229, 466, 160); } },
				[](FCtx& C) { return C.OnScreen(229) && C.Fact(TEXT("s5-jop")) == 2 && C.Idle() && !C.Busy(); }, 90.0, {}, 0.5);
			// Step 35 (back up to SCR_419: s5-jops makes the family, s5-fguy's scene, the two dragons) is the first step of chapter 12 (BuildChapter12): once the
			// scene has run the dragons are alive and casting, so a chapter that ended there left no time for anything else. s5-jops does it again on every entry
			// while &s5-jop is 2. Chapter 11 (BuildChapter11) is the kit the dragons need: the fourth level-up on Attack, two all-potions, the longsword.
		}

		// ---- Chapter 11 (test `ChBKit`): the kit for the Joppa dragons (probe_route.md 2.4/2.5): gold, two all-potions, Pete's longsword ----
		void BuildChapter11()
		{
			// Strength at the dragons is 13 + 1 (the level-up of chapter 8, now Attack) + 2 (the two all-potions below) + 4 (the longsword armed, item-sw1.c:44).
			// 400 gold for the sword (s4-st3p.c:36-49); this run has 205. One round of chapter 4's Feud pays about 200, a second (after the 5-minute wait) the rest.
			const int32 GoldTarget = 480; // 400 + 3 elixirs of 25 + a little
			const TArray<FString> LevelUps = { TEXT("Increase Attack"), TEXT("Increase Attack"), TEXT("Increase Attack") };
			for (int32 Round = 1; Round <= 3; ++Round)
			{
				if (Round > 1)
				{
					AddShopWait(*FString::Printf(TEXT("round %d: wait 5 minutes in Arturous's shop (8x), the screens' monsters come back (editor_type 6)"), Round), 302.0, GoldTarget);
				}
				AddFeud(*FString::Printf(TEXT("round %d: SCR_583, Bong and Boncd fight, he waits, then takes the loot"), Round), 583, 570, 60, 2, false, GoldTarget, LevelUps);
				AddFeud(*FString::Printf(TEXT("round %d: SCR_480, two Bongs"), Round), 480, 570, 60, 2, true, GoldTarget, LevelUps);
				AddFeud(*FString::Printf(TEXT("round %d: SCR_632, two Bongs"), Round), 632, 60, 380, 2, false, GoldTarget, LevelUps);
			}
			// Route step 6/38 (probe_route.md 2.3): the all-potion chest of Murkwood (SCR_395 S395_P03 ch1-ap, with a flying pill bug beside it: touch 4) and the potion on the
			// south coast (SCR_750 S750_P02): +1 strength, defense and magic each.
			AddPickup(TEXT("the all-potion chest of Murkwood (SCR_395 S395_P03 ch1-ap: a punch, then the potion: strength, defense, magic +1)"), 395, 339, 262, TEXT("apotion"), TEXT("strength"), 3);
			AddPickup(TEXT("the all-potion of the south coast (SCR_750 S750_P02: strength, defense, magic +1)"), 750, 174, 250, TEXT("apotion"), TEXT("strength"), 0);
			Add(TEXT("Pete's (SCR_196, s4-st3p talk: \"See what's for sale\", \"Longsword - $400\": gold - 400, item-sw1)"),
				[](FCtx& C)
				{
					if (C.P->Mark < 0) { C.P->Mark = C.Fact(TEXT("gold")); }
					if (!C.OnScreen(196)) { C.Goto(196, 300, 250); return; }
					if (const int32 Pete = C.SpriteWithScript(TEXT("s4-st3p"))) { C.StandBy(Pete, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { const bool bOk = C.Slot(TEXT("item-sw1")) != 0 && C.P->Mark >= 400 && C.Fact(TEXT("gold")) == C.P->Mark - 400 && C.Idle() && !C.Busy(); if (bOk) { C.P->Mark = -1; } return bOk; }, 60.0, { TEXT("See what's for sale"), TEXT("Longsword - $400") }, 4.0);
			// The dragons' harm cannot be dodged (20 - defense 5 = 15 a cast, 29 life): elixirs (Terris healer SCR_033, "Buy a bottle of elixer for $25", life +20) drunk in the fight.
			Add(TEXT("three elixirs from the Terris healer (SCR_033 s2-healp: \"Buy a bottle of elixer for $25\" x3)"),
				[](FCtx& C)
				{
					if (C.CountItem(TEXT("item-eli")) >= 3) { return; }
					if (!C.OnScreen(33)) { C.Goto(33, 300, 250); return; }
					if (const int32 Healer = C.Placement(33, 19)) { C.StandBy(Healer, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.CountItem(TEXT("item-eli")) >= 3 && C.Idle(); }, 60.0, { TEXT("Buy a bottle of elixer for $25"), TEXT("Buy a bottle of elixer for $25"), TEXT("Buy a bottle of elixer for $25") }, 0.5, true); // the healer's main loops on wait(500): Busy() is always true there
			Add(TEXT("arm the longsword (item-sw1 arm: strength +4, sp_distance 50, sp_range 40)"),
				[](FCtx& C) { if (C.P->Mark < 0) { C.P->Mark = C.Fact(TEXT("strength")); } C.G->ArmItemSlot(C.Slot(TEXT("item-sw1"))); },
				[](FCtx& C) { const bool bOk = C.D->GetInventory()->GetArmedItem() == TEXT("item-sw1") && C.P->Mark >= 0 && C.Fact(TEXT("strength")) == C.P->Mark + 4 && C.Idle(); if (bOk) { C.P->Mark = -1; } return bOk; }, 10.0);
		}

		// ---- Chapter 12 (test `ChCDragons`): the two dragons of Joppa (Act D step 36) and the epilogue (37, &story 12) ----
		void BuildChapter12()
		{
			Add(TEXT("the healer in Windemere (SCR_195 s4-healp, 1 gold per missing life)"),
				[](FCtx& C)
				{
					if (C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax"))) { return; }
					if (!C.OnScreen(195)) { C.Goto(195, 300, 250); return; }
					if (const int32 Healer = C.Placement(195, 19)) { C.StandBy(Healer, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax")) && C.Idle(); }, 60.0, { TEXT("Get healed") }, 0.5, true);
			Add(TEXT("back to Joppa (SCR_419, s5-jops with &s5-jop 2: s5-fguy's scene, two dragons en-drag, screenlock): the fight can begin"),
				[](FCtx& C) { if (!C.OnScreen(419)) { C.Goto(419, 422, 264); } },
				[](FCtx& C)
				{
					int32 Dragons = 0;
					for (const TPair<int32, FDinkSprite>& Pair : C.D->GetSprites()) { Dragons += (Pair.Value.bActive && Pair.Value.Script == FName(TEXT("en-drag"))) ? 1 : 0; }
					return C.OnScreen(419) && Dragons == 2 && C.D->bScreenLocked && C.Idle(); }, 120.0, {}, 0.5);
			Add(TEXT("the two dragons (en-drag: 80 hp, defense 8, touch 10, harm 20 by cast): DuelFight with the sword, family alive; the last death spawns s5-end: &story 12"),
				[](FCtx& C)
				{
					// The dragon in front of him until it is dead, then the other.
					int32 Target = C.P->Mark;
					const FDinkSprite* T = Target > 0 ? C.D->FindSprite(Target) : nullptr;
					if (!T || !T->bActive || T->GetProp(TEXT("hitpoints")) <= 0)
					{
						Target = 0;
						double Best = 1e18;
						const FDinkSprite& Dk = C.D->GetDink();
						for (const TPair<int32, FDinkSprite>& Pair : C.D->GetSprites())
						{
							const FDinkSprite& O = Pair.Value;
							if (O.bActive && O.Script == FName(TEXT("en-drag")) && O.GetProp(TEXT("hitpoints")) > 0)
							{
								const double Dist = FMath::Square(O.X - Dk.X) + FMath::Square(O.Y - Dk.Y);
								if (Dist < Best) { Best = Dist; Target = Pair.Key; }
							}
						}
						C.P->Mark = Target;
					}
					if (!Target) { return; }
					// The harm cast (en-drag.c `attack`) hurts for 20 - defense wherever Dink stands (no range, no dodge), a dragon's first one the moment he first hits it
					// (`hit` targets him and its attack_wait is long past) and then every 3-8 s while he keeps hitting it (the target callback, 0.5-2 s, re-rolls 1 in 9 for
					// Dink): he drinks an elixir when one more cast would kill him (FCtx::DrinkAndKeepSword).
					if (C.DrinkAndKeepSword(20)) { return; }
					FDuelOpts O;
					O.bCaster = true;
					O.bPull = false;
					O.Range = C.D->GetInventory()->GetArmedItem() == TEXT("item-sw1") ? 40 : 0;
					O.StageCheb = 40.0;
					C.DuelFight(Target, O);
				},
				[](FCtx& C) { const bool bOk = C.Fact(TEXT("story")) == 12 && C.Fact(TEXT("life")) > 0 && C.Idle() && !C.Busy(); if (bOk) { C.P->Mark = -1; } return bOk; }, 150.0, { TEXT("Increase Attack"), TEXT("I saved all of you, actually.") }, 0.001, true);
		}

		// ---- Chapter 13 (test `ChDCastle`): after the dragons: their loot, the level-up, the castle guard, the King (&story 12 -> 13 -> 14), the dungeon's potions (Act D end, Act E steps 39-41) ----
		void BuildChapter13()
		{
			// The two dragons' death spots hold emake.xlarge (gold200 and the like); the second kill's 400 exp reach 1600 (100 * 4 * 4): level 5, the menu "YOU ARE NOW LEVEL 5".
			Add(TEXT("the dragons' loot (emake.xlarge), and the level-up of the second 400 exp (level 5: Attack)"),
				[](FCtx& C) { if (const int32 Drop = Drops(C)) { C.StandBy(Drop, 0, true); } },
				[](FCtx& C) { return Drops(C) == 0 && C.Fact(TEXT("level")) >= 5 && C.Idle() && !C.Busy(); }, 40.0, { TEXT("Increase Attack") }, 0.5);
			Add(TEXT("the castle gate (SCR_402, s2-ca-g talk at &story 12: \"Request an audience with King Daniel\": enter() -> SCR_102)"),
				[](FCtx& C)
				{
					if (!C.OnScreen(402)) { C.Goto(402, 321, 300); return; }
					if (const int32 Guard = C.Placement(402, 5)) { C.StandBy(Guard, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.OnScreen(102) && C.Idle() && !C.Busy(); }, 60.0, { TEXT("Request an audience with King Daniel") }, 4.0);
			Add(TEXT("the King (SCR_070, king.c talk at &story 12: the greeting sets 13, the menu: \"Offer to help Milder\": &story 14)"),
				[](FCtx& C)
				{
					if (!C.OnScreen(70)) { C.Goto(70, 300, 260); return; }
					if (const int32 King = C.Placement(70, 3)) { C.StandBy(King, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.Fact(TEXT("story")) == 14 && C.Idle() && !C.Busy(); }, 90.0, { TEXT("Offer to help Milder") }, 4.0);
			AddPickup(TEXT("the defense potion of the King's hall (SCR_070 S070_P22 bpotion: defense +1)"), 70, 110, 240, TEXT("bpotion"), TEXT("defense"), 0);
			AddPickup(TEXT("the magic chest of the castle's back rooms (SCR_069 S069_P02 ch1-mp: a punch, then the potion: magic +1)"), 69, 323, 255, TEXT("ppotion"), TEXT("magic"), 2);
			AddPickup(TEXT("the gold-heart chest (SCR_101 S101_P02 ch1-gh: a punch, then the heart: lifemax +10)"), 101, 320, 255, TEXT("gheart"), TEXT("lifemax"), 2);
		}

		// ---- Chapter 14 (test `ChEEdge`): the Edge of the World and the ancients' machine to the Darklands (Act E steps 42-45) ----
		void BuildChapter14()
		{
			AddPickup(TEXT("the defense potion at the Edge's entrance (SCR_243 S243_P01 bpotion: defense +1)"), 243, 330, 160, TEXT("bpotion"), TEXT("defense"), 0);
			AddPickup(TEXT("the strength potion on the way to the machine (SCR_248 S248_P03 rpotion: strength +1)"), 248, 250, 140, TEXT("rpotion"), TEXT("strength"), 0);
			Add(TEXT("the pit (SCR_243 S243_P13 s6-hole, there at &story > 13: touch: Dink falls, fade_down, &player_map = 182, load_screen)"),
				[](FCtx& C)
				{
					if (!C.OnScreen(243)) { C.Goto(243, 470, 360); return; }
					// The pit's hardbox is 457-487 x 293-317 and its hardness stamp is solid (a wall of its own): touch -1 runs the script when Dink's point is within the
					// box plus 2 + the capsule's margin (4) = 323 from the south. A ring search (`Goto`) stood at 326 and never touched it; asking for the exact pixel does
					// (316 and 317 are refused, the capsule overlaps the stamp; 318 gets in and touches). UNVERIFIED: whether a walking Dink gets that close.
					if (C.SpriteWithScript(TEXT("s6-hole")))
					{
						const int32 Attempt = FMath::Max(C.P->Mark, 0);
						C.P->Mark = Attempt + 1;
						C.GB->GotoScreen(243, 472.0 - 20.0, 318.0 + (Attempt % 5));
						C.G->SyncDinkFromActor();
					}
				},
				[](FCtx& C) { const bool bOk = C.OnScreen(182) && C.Idle() && !C.Busy(); if (bOk) { C.P->Mark = -1; } return bOk; }, 30.0, {}, 0.5);
			Add(TEXT("the machine (SCR_253 s6-warp talk: \"Press the red button\": the spinner, fade_down, &player_map = 154, load_screen): the Darklands"),
				[](FCtx& C)
				{
					if (C.Fact(TEXT("player_map")) == 154) { return; } // arrived (the retry fires on the frame the scene ends)
					if (!C.OnScreen(253)) { C.Goto(253, 263, 395); return; }
					if (const int32 Machine = C.Placement(253, 6)) { C.StandBy(Machine, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.OnScreen(154) && C.D->GetDink().Screen == 154 && C.Idle() && !C.Busy() && C.Fact(TEXT("story")) == 14; }, 90.0, { TEXT("Press the red button") }, 4.0); // (player_map turns 154 before the script moves Dink and freezes him)
		}

		// ---- Chapter 15 (test `ChFDarklands`): the first Darklands room, SCR_156: the Bong, the Slayer and the Dragon (Act F step 47) ----
		void BuildChapter15()
		{
			Add(TEXT("the healer in Windemere (SCR_195 s4-healp, 1 gold per missing life)"),
				[](FCtx& C)
				{
					if (C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax"))) { return; }
					if (!C.OnScreen(195)) { C.Goto(195, 300, 250); return; }
					if (const int32 Healer = C.Placement(195, 19)) { C.StandBy(Healer, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax")) && C.Idle(); }, 60.0, { TEXT("Get healed") }, 0.5, true);
			Add(TEXT("SCR_156 (s7-bong 40 hp, s7-slay 100 hp, s7-drag 80 hp with harm 30; screenlock): the dragon first (it casts at him half the time), then the slayer and the bong"),
				[](FCtx& C)
				{
					if (!C.OnScreen(156)) { C.Goto(156, 60, 250); return; }
					if (C.DrinkAndKeepSword(30)) { return; }
					int32 Target = 0;
					for (const TCHAR* Script : { TEXT("s7-drag"), TEXT("s7-slay"), TEXT("s7-bong") })
					{
						const int32 H = C.SpriteWithScript(Script);
						const FDinkSprite* T = H ? C.D->FindSprite(H) : nullptr;
						if (T && T->GetProp(TEXT("hitpoints")) > 0) { Target = H; break; }
					}
					if (!Target) { return; }
					FDuelOpts O;
					O.bCaster = C.D->FindSprite(Target)->GetProp(TEXT("brain")) == 10;
					O.bPull = false;
					O.Range = C.D->GetInventory()->GetArmedItem() == TEXT("item-sw1") ? 40 : 0;
					O.StageCheb = 60.0;
					C.DuelFight(Target, O);
				},
				[](FCtx& C) { return C.OnScreen(156) && C.SpriteWithScript(TEXT("s7-slay")) == 0 && C.SpriteWithScript(TEXT("s7-bong")) == 0 && !C.D->bScreenLocked && C.Fact(TEXT("life")) > 0 && C.Idle(); }, 150.0, { TEXT("Increase Attack") }, 0.001, true);
		}

		// ---- Chapter 16 (test `ChGSlayers`): SCR_157, the four Slayers and the gold heart (Act F step 48) ----
		void BuildChapter16()
		{
			Add(TEXT("the healer in Windemere (SCR_195 s4-healp, 1 gold per missing life)"),
				[](FCtx& C)
				{
					if (C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax"))) { return; }
					if (!C.OnScreen(195)) { C.Goto(195, 300, 250); return; }
					if (const int32 Healer = C.Placement(195, 19)) { C.StandBy(Healer, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax")) && C.Idle(); }, 60.0, { TEXT("Get healed") }, 0.5, true);
			Add(TEXT("SCR_157: the four slayers (s7-slay 100 hp, defense 5, strength 20, range 45; screenlock): SquadFight with the sword"),
				[](FCtx& C)
				{
					if (!C.OnScreen(157)) { C.Goto(157, 60, 250); return; }
					if (C.DrinkAndKeepSword(27)) { return; }
					FSquadOpts O;
					O.Range = C.D->GetInventory()->GetArmedItem() == TEXT("item-sw1") ? 40 : 0;
					C.SquadFight(O);
				},
				[](FCtx& C) { return C.OnScreen(157) && C.SpriteWithScript(TEXT("s7-slay")) == 0 && !C.D->bScreenLocked && C.Fact(TEXT("life")) > 0 && C.Idle(); }, 200.0, { TEXT("Increase Attack") }, 0.001, true);
		}

		// ---- Chapter 17 (test `ChHDucks`): the slayers' loot and gold heart, SCR_190's three duck-bugs and the full heart (Act F steps 48-49) ----
		void BuildChapter17()
		{
			Add(TEXT("the slayers' loot (emake.xlarge x4) lying on SCR_157"),
				[](FCtx& C) { if (const int32 Drop = Drops(C)) { C.StandBy(Drop, 0, true); } },
				[](FCtx& C) { return Drops(C) == 0 && C.Idle() && !C.Busy(); }, 40.0, {}, 0.5);
			AddPickup(TEXT("the gold heart of the locked room (SCR_157 S157_P09 gheart: lifemax +10)"), 157, 267, 215, TEXT("gheart"), TEXT("lifemax"), 0);
			Add(TEXT("the healer in Windemere (SCR_195 s4-healp, 1 gold per missing life)"),
				[](FCtx& C)
				{
					if (C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax"))) { return; }
					if (!C.OnScreen(195)) { C.Goto(195, 300, 250); return; }
					if (const int32 Healer = C.Placement(195, 19)) { C.StandBy(Healer, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax")) && C.Idle(); }, 60.0, { TEXT("Get healed") }, 0.5, true);
			Add(TEXT("SCR_190: the three duck-bugs (s7-duck 50 hp, no defense, touch 25; screenlock): SquadFight with the sword"),
				[](FCtx& C)
				{
					if (!C.OnScreen(190)) { C.Goto(190, 60, 250); return; }
					if (C.DrinkAndKeepSword(27)) { return; }
					FSquadOpts O;
					O.Range = C.D->GetInventory()->GetArmedItem() == TEXT("item-sw1") ? 40 : 0;
					C.SquadFight(O);
				},
				[](FCtx& C) { return C.OnScreen(190) && C.Hostiles(190) == 0 && !C.D->bScreenLocked && C.Fact(TEXT("life")) > 0 && C.Idle(); }, 200.0, { TEXT("Increase Attack") }, 0.001, true);
			Add(TEXT("the ducks' loot and the full heart (SCR_190 S190_P10 heart: life = lifemax)"),
				[](FCtx& C) { if (const int32 Drop = Drops(C)) { C.StandBy(Drop, 0, true); } },
				[](FCtx& C) { return Drops(C) == 0 && C.Idle() && !C.Busy(); }, 40.0, {}, 0.5);
		}

		// ---- Chapter 18 (test `ChISeth`): Milder and the start of the Seth fight (Act F steps 51-52; the fight is the stop, step 53) ----
		void BuildChapter18()
		{
			Add(TEXT("the healer in Windemere (SCR_195 s4-healp, 1 gold per missing life)"),
				[](FCtx& C)
				{
					if (C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax"))) { return; }
					if (!C.OnScreen(195)) { C.Goto(195, 300, 250); return; }
					if (const int32 Healer = C.Placement(195, 19)) { C.StandBy(Healer, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.Fact(TEXT("life")) >= C.Fact(TEXT("lifemax")) && C.Idle(); }, 60.0, { TEXT("Get healed") }, 0.5, true);
			// The route goes SCR_222 (barrels), SCR_254 (save machine, the hole S254_P04) -> SCR_085 -> east to SCR_086; the probe teleports to SCR_086.
			Add(TEXT("Milder (SCR_086 s7-mil talk at &story 14: \"Take his advice\", the dialogue, the explosion, Seth appears and gets s7-boss): the fight begins"),
				[](FCtx& C)
				{
					if (C.SpriteWithScript(TEXT("s7-boss"))) { return; } // Seth is there: a second talk would only say "Milder, wake up!"
					if (!C.OnScreen(86)) { C.Goto(86, 250, 300); return; }
					if (const int32 Milder = C.SpriteWithScript(TEXT("s7-mil"))) { C.StandBy(Milder, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.OnScreen(86) && C.SpriteWithScript(TEXT("s7-boss")) != 0 && C.Idle() && !C.Busy(); }, 120.0, { TEXT("Take his advice") }, 4.0);
			// NEXT (design-level stop, 8 Nov 2026): Act F step 53, Seth (s7-boss: 300 hp, defense 25, touch 30; every 2-6 s a bomb (strength 25) or "greater harm" 30 unless random(40,1) <= magic).
			// Dink here: see the chapter's report line (strength 22 with the longsword, defense 7, magic 10, life 52, level 5, 1 elixir). Sword hits on defense 25 do 0.5 net (a pity point
			// half the time): about 600 swings for 300 hp. The route needs the bow (b1 + bow lore 1500 gold, strength about 25, no hold-the-key action in the probe yet: `activate_bow`).
		}

		// ---- Chapter 3: preparation (Act B/C of Docs/probe_route.md): gold, strength and hearts on the roads, then the Mayor's errand ----
		void BuildChapter3()
		{
			// A fact the step must raise by Amount from where it began (the step notes it in Act, which runs first).
			auto Raise = [](FCtx& C, const TCHAR* Fact, int32 Amount) { if (C.P->Mark < 0) { C.P->Mark = C.Fact(Fact); return false; } return C.Fact(Fact) >= C.P->Mark + Amount; };
			auto Reached = [](FCtx& C, bool bOk) { if (bOk) { C.P->Mark = -1; } return bOk; };
			auto Pickup = [](FCtx& C, int32 Screen, double X, double Y, const TCHAR* Script)
			{
				const int32 Item = C.OnScreen(Screen) ? C.SpriteWithScript(Script) : 0;
				if (Item) { C.StandBy(Item, 0, true); } else if (!C.OnScreen(Screen)) { C.Goto(Screen, X, Y); }
			};
			Add(TEXT("the road to KernSin: a gold heart (SCR_524, S524_P04 gheart touch: &lifemax + 10)"),
				[Pickup](FCtx& C) { Pickup(C, 524, 250, 250, TEXT("gheart")); },
				[Raise, Reached](FCtx& C) { return Reached(C, Raise(C, TEXT("lifemax"), 10) && C.Idle()); }, 30.0, {}, 3.0);
			auto Chest = [Pickup, Raise, Reached](int32 Screen, int32 Index, double X, double Y, FProbeCommand* Self)
			{
				// Hit the chest (the fists' hit makes the coins: ch1-pap.hit, make.papgold), then stand on them (papgold.touch: &gold + 200).
				Self->Add(*FString::Printf(TEXT("open the chest S%03d_P%02d with a punch (ch1-pap hit: the coins appear)"), Screen, Index),
					[Screen, Index, X, Y](FCtx& C)
					{
						if (C.P->Mark < 0) { C.P->Mark = C.Fact(TEXT("gold")); } // the coins fall at Dink's feet: he may have them before the next step
						if (!C.OnScreen(Screen)) { C.Goto(Screen, X, Y); return; }
						if (!C.SpriteWithScript(TEXT("papgold"))) { C.StandBy(C.Placement(Screen, Index), 12); C.G->PlayerAttack(); }
					},
					[Screen](FCtx& C) { return C.OnScreen(Screen) && C.P->Mark >= 0 && (C.SpriteWithScript(TEXT("papgold")) != 0 || C.Fact(TEXT("gold")) >= C.P->Mark + 200) && C.Idle(); }, 30.0, {}, 1.0);
				Self->Add(*FString::Printf(TEXT("take the coins (papgold touch: &gold + 200)")),
					[Pickup, Screen](FCtx& C) { Pickup(C, Screen, 300, 250, TEXT("papgold")); },
					[Raise, Reached](FCtx& C) { return Reached(C, Raise(C, TEXT("gold"), 200) && C.Idle()); }, 20.0, {}, 2.0);
			};
			Chest(5, 28, 400, 230, this);
			Chest(557, 5, 300, 230, this);
			Chest(747, 1, 300, 230, this);
			Add(TEXT("four strength potions beside the goblin camp (SCR_681, S681_P14-17 rpotion touch: &strength + 4)"),
				[Pickup](FCtx& C) { Pickup(C, 681, 380, 300, TEXT("rpotion")); },
				[Raise, Reached](FCtx& C) { return Reached(C, Raise(C, TEXT("strength"), 4) && C.Idle()); }, 60.0, {}, 3.0);
				// The Mayor's errand (Act B steps 17-19): Christina in the fountain square, the girl who leads him to the bookstore, the Mayor.
				Add(TEXT("Christina at the fountain (SCR_586, s3-chick talk: tell her about the planned assault, &mayor 1)"),
					[](FCtx& C)
					{
						if (!C.OnScreen(586)) { C.Goto(586, 300, 250); return; }
						if (const int32 Christina = C.SpriteWithScript(TEXT("s3-chick"))) { C.StandBy(Christina, 25); C.S->TryTalk(C.Pawn); }
					},
					[](FCtx& C) { return C.Fact(TEXT("mayor")) == 1 && C.Idle() && !C.Busy(); }, 60.0, { TEXT("Tell her about the planned assault") }, 3.0);
				Add(TEXT("into the bookstore street: the girl leads him on (SCR_587, s3-st1o main: &mayor 2)"),
					[](FCtx& C) { if (!C.OnScreen(587)) { C.Goto(587, 80, 300); } },
					[](FCtx& C) { return C.Fact(TEXT("mayor")) == 2 && C.Idle() && !C.Busy(); }, 90.0, {}, 4.0);
				Add(TEXT("the Mayor in Hiram's Bookstore (SCR_067, s3-mayor talk: tell him about the planned assault, &mayor 3)"),
					[](FCtx& C)
					{
						if (!C.OnScreen(67)) { C.Goto(67, 360, 250); return; } // inside, clear of the exit door's warp S067_P15 (a spot by the door sent him straight back out)
						if (const int32 Mayor = C.SpriteWithScript(TEXT("s3-mayor"))) { C.StandBy(Mayor, 25); C.S->TryTalk(C.Pawn); }
					},
					[](FCtx& C) { return C.Fact(TEXT("mayor")) == 3 && C.Idle() && !C.Busy(); }, 60.0, { TEXT("Tell him about the planned assault") }, 3.0);
				}

		// ---- Chapter 2: Terris, Nadine, the cult, Mary (&story 7 -> 8) ----
		void BuildChapter2()
		{
			// Act A of Docs/probe_route.md, steps 9-12. Chapter 1 left Dink on SCR_625 with &story 7, fists armed, magic 5.
			Add(TEXT("talk to Nadine: ask why her house is such a mess (SCR_066, s2-nadp talk: &s2-nad 1)"),
				[](FCtx& C)
				{
					if (!C.OnScreen(66)) { C.Goto(66, 340, 330); return; }
					if (const int32 Nadine = C.SpriteWithScript(TEXT("s2-nadp"))) { C.StandBy(Nadine, 25); C.S->TryTalk(C.Pawn); }
				},
				[](FCtx& C) { return C.Fact(TEXT("s2-nad")) == 1 && C.Idle() && !C.Busy(); }, 60.0, { TEXT("Ask Nadine why her house is such a mess") }, 3.0);
			Add(TEXT("talk to Nadine again: offer to find her girl (&s2-nad 2)"),
				[](FCtx& C) { if (const int32 Nadine = C.SpriteWithScript(TEXT("s2-nadp"))) { C.StandBy(Nadine, 25); C.S->TryTalk(C.Pawn); } },
				[](FCtx& C) { return C.Fact(TEXT("s2-nad")) == 2 && C.Idle() && !C.Busy(); }, 60.0, { TEXT("Offer to find Nadine's girl") }, 3.0);
			Add(TEXT("arm the fireball (inventory: magic slot 1, cost 100: 2 s of charge at magic 5)"),
				[](FCtx& C) { C.G->ArmMagicSlot(1); },
				[](FCtx& C) { return C.D->GetInventory()->GetArmedMagic() == TEXT("item-fb"); }, 10.0);
			Add(TEXT("the cult's backyard (SCR_238, s2-cult main: four girls, Bishop Nelson, Mary; screenlock)"),
				// Never "Use brains and stay hidden": it loops forever (s2-cult.c:133-143).
				[](FCtx& C) { if (!C.OnScreen(238)) { C.Goto(238, 600, 300); } },
				[](FCtx& C) { return C.D->bScreenLocked && C.Idle(); }, 120.0, { TEXT("Say something to the effect that you are going to save her") }, 3.0);
			Add(TEXT("kill the four girls and Bishop Nelson, keeping clear of all of them (s2-cbon, s2-cslay die: screenlock(0))"),
				[](FCtx& C)
				{
					// Never cornered: with nothing safe by the clock he runs to the open ground (the first version stood in a corner and was touched to death
					// once the shipped game's stray sprites stopped vanishing, see AGENTS.md pitfall 42).
					FFightOpts O;
					O.bFlee = true;
					O.OpenWeight = 60.0;
					O.PaceMarginSec = 0.3;
					C.KiteFight(TEXT("s2-cman"), 79, O);
				},
				[](FCtx& C) { return !C.D->bScreenLocked && C.Idle() && !C.Busy(); }, 300.0, {}, 0.001, true);
			Add(TEXT("talk to Mary: rescue complete (s2-culg talk: scripted walk home to SCR_066, &s2-nad 3, &story 8)"),
				[](FCtx& C) { if (const int32 Mary = C.SpriteWithScript(TEXT("s2-culg"))) { C.StandBy(Mary, 25); C.S->TryTalk(C.Pawn); } },
				// Dink walked up through the exit door's warp during the scene (S066_P16 at y 439) and was sent outside to SCR_497: the scene must
								// end in Nadine's house (a script that holds Dink never triggers a warp, D:15337).
								[](FCtx& C) { return C.Fact(TEXT("story")) >= 8 && C.OnScreen(66) && C.Idle() && !C.Busy(); }, 120.0, { TEXT("A friend of the land.") }, 4.0);
		}

		FAutomationTestBase* Test;
		FChapterSpec Spec;
		bool bLoaded = false;
		bool bLoadChecked = false;
		int32 LoadedScreen = 0;
		double LoadWall = 0.0;
		int32 ExpectedSteps;
		int32 StopAfterSteps = INDEX_NONE;
		FString* TraceOut = nullptr;
		double Began;
		bool bWallBegun = false;
		double StartedWall = 0.0;
		bool bStarted = false;
		FProbeState Probe;

		TArray<FStep> Steps;
		int32 Current = 0;
		bool bActed = false;
		double StepStart = 0.0;
		double LastAct = 0.0;
		int32 Searches = 0;
		TArray<FString> Log;
	};
}

namespace DinkProbeTest
{
	/**
	 * Runs one chapter of the play-through in PIE on the generated world. The tests are named Ch1..ChN so the automation
	 * runner (alphabetical by path) plays them in order; each starts from the slot the previous one saved. Floor = steps the
	 * chapter completed in the last recorded run (raise it when the game gets further). Every run is deterministic (fixed
	 * 60 Hz step, seed 1997 in chapter 1, the generator's state travels in the save), so the floor is exact.
	 */
	inline bool RunChapterTest(FAutomationTestBase& T, const FChapterSpec& Spec, int32 WorldFloor, int32 StonebrookFloor)
	{
#if !WITH_EDITOR
		// Packaged game (Development): the engine has already loaded GameDefaultMap (L_Greybox_World) and its game has been
		// running since process start; there is no PIE to start and no editor world to load a map into. Only the world
		// map is cooked, and a package that lacks it is an error, never a skip (a skipped probe passes, which would be a
		// false pass). A cooked map is not a loose .umap on disk (IoStore), so ask the package store, not the file system.
		(void)StonebrookFloor;
		if (!FPackageName::DoesPackageExist(WorldMap))
		{
			T.AddError(FString::Printf(TEXT("%s is not in this build (the cook did not include the generated greybox)"), WorldMap));
			return true;
		}
		const UWorld* Running = ProbeWorld();
		if (Running && Running->GetOutermost()->GetName() != WorldMap)
		{
			T.AddError(FString::Printf(TEXT("the packaged game started on %s, not on %s (GameDefaultMap)"), *Running->GetOutermost()->GetName(), WorldMap));
			return true;
		}
		T.AddInfo(FString::Printf(TEXT("chapter %d (%s) on %s, packaged game process"), Spec.Number, *Spec.Title, WorldMap));
		UseFixedTimeStep();
		ADD_LATENT_AUTOMATION_COMMAND(FProbeCommand(&T, Spec, WorldFloor));
		ADD_LATENT_AUTOMATION_COMMAND(FDelayedFunctionLatentCommand([]() { RestoreTimeStep(); }, 0.0f));
		return true;
#else
		const TCHAR* ProbeMap = WorldMap;
		FString File = FPackageName::LongPackageNameToFilename(ProbeMap, FPackageName::GetMapPackageExtension());
		if (!IFileManager::Get().FileExists(*File))
		{
			ProbeMap = StonebrookMap;
			File = FPackageName::LongPackageNameToFilename(ProbeMap, FPackageName::GetMapPackageExtension());
			T.AddInfo(TEXT("L_Greybox_World not generated: probing L_Greybox_Stonebrook (the toll bridge is outside it)"));
		}
		if (!IFileManager::Get().FileExists(*File))
		{
			T.AddWarning(TEXT("skipped: no greybox is generated (run Scripts/import_greybox.sh --region stonebrook or all)"));
			return true;
		}
		if (Spec.Number > 1 && ProbeMap != WorldMap)
		{
			T.AddWarning(TEXT("skipped: this chapter needs L_Greybox_World (Scripts/import_greybox.sh --region all)"));
			return true;
		}
		T.AddInfo(FString::Printf(TEXT("chapter %d (%s) on %s"), Spec.Number, *Spec.Title, ProbeMap));
		// The engine's internet check during PIE start-up times out on this offline machine; not ours.
		T.AddExpectedMessage(TEXT("HTTP request timed out"), EAutomationExpectedMessageFlags::Contains, -1, false);
		UWorld* Current = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
		if (!Current || Current->GetOutermost()->GetName() != ProbeMap)
		{
			T.TestNotNull(TEXT("map loads"), UEditorLoadingAndSavingUtils::LoadMap(File));
			FAssetCompilingManager::Get().FinishAllCompilation();
		}
		// Fixed 60 Hz game frames from before PIE starts (the new-game scene included) until the chapter ends.
		UseFixedTimeStep();
		ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
		ADD_LATENT_AUTOMATION_COMMAND(FProbeCommand(&T, Spec, ProbeMap == WorldMap ? WorldFloor : StonebrookFloor));
		ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
		ADD_LATENT_AUTOMATION_COMMAND(FDelayedFunctionLatentCommand([]() { RestoreTimeStep(); }, 0.0f));
		return true;
#endif
	}
}

// 6 Nov 2026: on L_Greybox_World chapter 1 plays all 47 steps, through the cult's ambush in the prisoner's cave
// (&caveguy 6); the scripted warp that ends it puts Dink on SCR_625. Stonebrook alone ends before the toll bridge (22).
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh1Test, "Dink.Gameplay.Probe.Ch1Stonebrook", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh1Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(1, TEXT("Stonebrook, Martridge, the toll, Jack, the prisoner's cave")), 47, 22);
}

// Chapter 2 (Terris: Nadine, the cult, Mary) starts from chapter 1's slot, chapter 3 from chapter 2's.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh2Test, "Dink.Gameplay.Probe.Ch2Terris", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh2Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(2, TEXT("Terris: Nadine, the cult of the Dead Dragon Carcass, Mary")), 6, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh3Test, "Dink.Gameplay.Probe.Ch3Roads", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh3Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(3, TEXT("The roads: gold heart, three chests, strength potions, the Mayor")), 11, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh5Test, "Dink.Gameplay.Probe.Ch5Bow", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh5Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(5, TEXT("The bow: Arturous, arm it, the goblin gate guard")), 3, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh6Test, "Dink.Gameplay.Probe.Ch6Goblins", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh6Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(6, TEXT("The goblin sanctuary: healer and first goblin (the other three are chapter 7)")), 3, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh7Test, "Dink.Gameplay.Probe.Ch7Sanctuary", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh7Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(7, TEXT("The goblin sanctuary: the other goblins and Mog, the Cast camp, the ambush")), 8, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh8Test, "Dink.Gameplay.Probe.Ch8Knights", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh8Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(8, TEXT("The ambush: the three Cast knights, the Mayor and the parade")), 3, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh9Test, "Dink.Gameplay.Probe.Ch9Windemere", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh9Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(9, TEXT("Windemere: Pete's bomb, the two all-potion chests, the cracked rock, the 27 ducks")), 6, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh10Test, "Dink.Gameplay.Probe.ChAJoppa", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh10Test::RunTest(const FString& Parameters)
{
	// Named ChA..: the runner sorts by path, so a chapter 10 called Ch10 would run before Ch2 (AGENTS.md pitfall 33). Chapters 11-18 are ChBKit, ChCDragons, ChDCastle, ChEEdge, ChFDarklands, ChGSlayers, ChHDucks, ChISeth
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(10, TEXT("Windemere's errands and Joppa: the healer, three pickups, Joppa, the basement scene")), 6, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh11Test, "Dink.Gameplay.Probe.ChBKit", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh11Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(11, TEXT("The kit for the dragons: gold from the Bongs, two all-potions, Pete's longsword")), 16, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh12Test, "Dink.Gameplay.Probe.ChCDragons", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh12Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(12, TEXT("The two dragons of Joppa and the epilogue (&story 12)")), 3, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh13Test, "Dink.Gameplay.Probe.ChDCastle", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh13Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(13, TEXT("After the dragons: their loot, the castle, the King (&story 14), the back rooms' potions")), 6, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh14Test, "Dink.Gameplay.Probe.ChEEdge", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh14Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(14, TEXT("The Edge of the World: the pit, the machine to the Darklands")), 4, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh15Test, "Dink.Gameplay.Probe.ChFDarklands", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh15Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(15, TEXT("The Darklands: the first room, SCR_156")), 2, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh16Test, "Dink.Gameplay.Probe.ChGSlayers", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh16Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(16, TEXT("The Darklands: the four slayers of SCR_157")), 2, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh17Test, "Dink.Gameplay.Probe.ChHDucks", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh17Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(17, TEXT("The Darklands: the slayers' gold heart and the three duck-bugs of SCR_190")), 5, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh18Test, "Dink.Gameplay.Probe.ChISeth", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh18Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(18, TEXT("The Darklands: Milder and the beginning of the Seth fight")), 2, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeCh4Test, "Dink.Gameplay.Probe.Ch4Gold", DINK_TEST_FLAGS)
bool FDinkGameplayProbeCh4Test::RunTest(const FString& Parameters)
{
	using namespace DinkProbeTest;
	return RunChapterTest(*this, MakeChapter(4, TEXT("Gold for the bow: monsters that kill each other, waits for their return")), 10, 0);
}

#if WITH_EDITOR
// The two repeat tests run two PIE sessions (two fresh GameInstances) in one process, which a packaged game cannot:
// there the same check is two process runs of a chapter and a comparison of their trace md5s (Scripts/run_packaged_tests.sh).
namespace DinkProbeTest
{
	/** Compares the two traces the repeat test collected: same seed, same fixed step, same game. */
	class FCompareTracesCommand : public IAutomationLatentCommand
	{
	public:
		FCompareTracesCommand(FAutomationTestBase* InTest, TSharedRef<FString> InA, TSharedRef<FString> InB) : Test(InTest), A(InA), B(InB) {}
		virtual bool Update() override
		{
			TArray<FString> LinesA, LinesB;
			A->ParseIntoArrayLines(LinesA, false);
			B->ParseIntoArrayLines(LinesB, false);
			int32 First = INDEX_NONE;
			for (int32 i = 1; i < FMath::Min(LinesA.Num(), LinesB.Num()); ++i) // line 0 is the header (counts)
			{
				if (LinesA[i] != LinesB[i])
				{
					First = i;
					break;
				}
			}
			if (First != INDEX_NONE)
			{
				Test->AddError(FString::Printf(TEXT("the runs part at event %d: \"%s\" / \"%s\""), First, *LinesA[First], *LinesB[First]));
			}
			Test->TestEqual(TEXT("both runs have the same number of events"), LinesA.Num(), LinesB.Num());
			Test->TestTrue(TEXT("the trace is not empty"), LinesA.Num() > 1000);
			Test->AddInfo(FString::Printf(TEXT("two runs, %d events each, %s"), LinesA.Num(), First == INDEX_NONE ? TEXT("identical") : TEXT("different")));
			return true;
		}
	private:
		FAutomationTestBase* Test;
		TSharedRef<FString> A, B;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeRepeatTest, "Dink.Gameplay.Probe.Repeatable", DINK_TEST_FLAGS)
bool FDinkGameplayProbeRepeatTest::RunTest(const FString& Parameters)
{
	// The project rule: gameplay is deterministic under a fixed seed. The probe plays the first stretch of the story
	// (through the cave Bonca, the first real fight: where real-time runs used to part) twice in two PIE sessions of
	// this editor, from a new game each, and the two event traces must be identical, line by line, in game time.
	// Fails if anything in gameplay reads the wall clock or the frame time, keeps state across sessions (a static, a
	// leftover in a subsystem) or depends on container order. It plays the same code as the full probe.
	using namespace DinkProbeTest;
	FString File = FPackageName::LongPackageNameToFilename(WorldMap, FPackageName::GetMapPackageExtension());
	const TCHAR* ProbeMap = WorldMap;
	if (!IFileManager::Get().FileExists(*File))
	{
		ProbeMap = StonebrookMap;
		File = FPackageName::LongPackageNameToFilename(ProbeMap, FPackageName::GetMapPackageExtension());
	}
	if (!IFileManager::Get().FileExists(*File))
	{
		AddWarning(TEXT("skipped: no greybox is generated (run Scripts/import_greybox.sh --region stonebrook or all)"));
		return true;
	}
	AddExpectedMessage(TEXT("HTTP request timed out"), EAutomationExpectedMessageFlags::Contains, -1, false);
	UWorld* Current = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!Current || Current->GetOutermost()->GetName() != ProbeMap)
	{
		TestNotNull(TEXT("map loads"), UEditorLoadingAndSavingUtils::LoadMap(File));
		FAssetCompilingManager::Get().FinishAllCompilation();
	}
	// Step 28 is the cave Bonca (SCR_100) on the world map; the Stonebrook-only map has the same story up to step 22.
	const int32 Steps = ProbeMap == WorldMap ? 28 : 22;
	TSharedRef<FString> A = MakeShared<FString>(), B = MakeShared<FString>();
	UseFixedTimeStep();
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FProbeCommand(this, MakeChapter(1, TEXT("repeat")), Steps, Steps, &A.Get()));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	ADD_LATENT_AUTOMATION_COMMAND(FDelayedFunctionLatentCommand([]() { UseFixedTimeStep(); }, 0.0f));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FProbeCommand(this, MakeChapter(1, TEXT("repeat")), Steps, Steps, &B.Get()));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	ADD_LATENT_AUTOMATION_COMMAND(FDelayedFunctionLatentCommand([]() { RestoreTimeStep(); }, 0.0f));
	ADD_LATENT_AUTOMATION_COMMAND(FCompareTracesCommand(this, A, B));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayProbeRepeatChapterTest, "Dink.Gameplay.Probe.RepeatableChapter", DINK_TEST_FLAGS)
bool FDinkGameplayProbeRepeatChapterTest::RunTest(const FString& Parameters)
{
	// Chapter 2 (the cult fight: four chasers, a boss, one shared rand() stream, the save slot's generator state) played twice from
	// chapter 1's slot in two PIE sessions: the event traces must be identical line by line. Cheap (about 25 s a run) and it covers
	// what chapter 1's repeat does not: loading a save, and a fight with several brains. Needs the slot Ch1Stonebrook writes.
	using namespace DinkProbeTest;
	FString File = FPackageName::LongPackageNameToFilename(WorldMap, FPackageName::GetMapPackageExtension());
	if (!IFileManager::Get().FileExists(*File))
	{
		AddWarning(TEXT("skipped: needs L_Greybox_World (Scripts/import_greybox.sh --region all)"));
		return true;
	}
	AddExpectedMessage(TEXT("HTTP request timed out"), EAutomationExpectedMessageFlags::Contains, -1, false);
	UWorld* Current = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!Current || Current->GetOutermost()->GetName() != WorldMap)
	{
		TestNotNull(TEXT("map loads"), UEditorLoadingAndSavingUtils::LoadMap(File));
		FAssetCompilingManager::Get().FinishAllCompilation();
	}
	const FChapterSpec Spec = MakeChapter(2, TEXT("repeat"));
	const int32 Steps = FProbeCommand(this, Spec, 0).NumSteps(); // only to count the chapter's steps
	TSharedRef<FString> A = MakeShared<FString>(), B = MakeShared<FString>();
	UseFixedTimeStep();
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FProbeCommand(this, Spec, Steps, Steps, &A.Get()));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	ADD_LATENT_AUTOMATION_COMMAND(FDelayedFunctionLatentCommand([]() { UseFixedTimeStep(); }, 0.0f));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FProbeCommand(this, Spec, Steps, Steps, &B.Get()));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	ADD_LATENT_AUTOMATION_COMMAND(FDelayedFunctionLatentCommand([]() { RestoreTimeStep(); }, 0.0f));
	ADD_LATENT_AUTOMATION_COMMAND(FCompareTracesCommand(this, A, B));
	return true;
}
#endif // WITH_EDITOR
