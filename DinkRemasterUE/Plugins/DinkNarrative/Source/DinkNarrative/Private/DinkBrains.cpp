// The original engine's brains (source/dink/dink.cpp, "D:n" = line), ported onto the director's sprite
// records in the engine's screen pixels (x includes the 20 px status bar). Everything here runs the same
// for greybox actors (their position follows the sprite) and for virtual sprites in headless tests.
//
// Timing: the 1997 engine is locked at 60 frames a second (D:17300, base_timing 7, so every
// "speed * (base_timing / 4)" is just speed). Each frame every sprite runs ThinkSprite (D:16790): its brain
// thinks when sp_timing allows, then the move it made is checked against the screen's hardness and its
// animation advances. TickBrains turns game time into whole engine frames.
//
// Not ported: brain 1 (Dink is the player's pawn), 8 (texts: the story subsystem), 13 (mouse cursor) and
// 14 (buttons) of the title and menu screens, sp_reverse animations, the corpse/blood/damage-number
// sprites (draw_damage, random_blood, add_kill_sprite's picture), and smooth_follow (the base game never
// turns it on). Scripted move/move_stop belong to the director; a brain yields while one runs, as the
// engine's brains do (process_move first).

#include "DinkGameplay.h"
#include "DinkCombat.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkStorySubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "DrawDebugHelpers.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

namespace
{
	const FName B_Brain(TEXT("brain")), B_Seq(TEXT("seq")), B_Frame(TEXT("frame")), B_PSeq(TEXT("pseq")), B_PFrame(TEXT("pframe")),
		B_Speed(TEXT("speed")), B_Timing(TEXT("timing")), B_Mx(TEXT("mx")), B_My(TEXT("my")), B_BaseWalk(TEXT("base_walk")),
		B_BaseAttack(TEXT("base_attack")), B_Target(TEXT("target")), B_Follow(TEXT("follow")), B_Distance(TEXT("distance")),
		B_AttackWait(TEXT("attack_wait")), B_FrameDelay(TEXT("frame_delay")), B_PicFreeze(TEXT("picfreeze")), B_Flying(TEXT("flying")),
		B_MoveNoHard(TEXT("move_nohard")), B_BrainParm(TEXT("brain_parm")), B_BrainParm2(TEXT("brain_parm2")), B_Size(TEXT("size")),
		B_Range(TEXT("range")), B_Strength(TEXT("strength")), B_NoHit(TEXT("nohit")), B_Hitpoints(TEXT("hitpoints")),
		B_Defense(TEXT("defense")), B_Telegraph(TEXT("telegraph")), B_AttackHitSound(TEXT("attack_hit_sound")),
		B_AttackHitSoundSpeed(TEXT("attack_hit_sound_speed")), B_NoControl(TEXT("nocontrol"));
	const FName Proc_Attack(TEXT("attack")), Proc_Hit(TEXT("hit")), Proc_Damage(TEXT("damage"));

	constexpr int32 GameAreaY = 400;   // C_DINK_ORIGINAL_GAME_AREA_Y (dink.h:242)
	constexpr int32 RightBarX = 620;   // g_gameAreaRightBarStartX (dink.h:240)
	constexpr int32 ScreenSizeX = 640; // C_DINK_SCREENSIZE_X (misc_util.h:7)

	/** in_this_base (D:12197): the sequence's tens are the base. */
	bool InThisBase(int32 Seq, int32 Base)
	{
		return (Seq / 10) * 10 == Base;
	}

	bool Inside(int32 X, int32 Y, int32 L, int32 T, int32 R, int32 B)
	{
		return X >= L && X <= R && Y >= T && Y <= B;
	}

	int32 Px(double V)
	{
		return FMath::RoundToInt32(V);
	}
}

// ---------------------------------------------------------------------------------------------
// Frame loop

void UDinkGameplay::TickBrains(double DeltaMs)
{
	UDinkDirector* D = Director();
	if (!D || !Story)
	{
		return;
	}
	// The brain clock trails game time by the part of a frame not yet run.
	const double Expected = Story->GetNowMs() - DeltaMs - BrainCarryMs;
	if (FMath::Abs(Expected - BrainClockMs) > 1000.0)
	{
		BrainClockMs = Expected; // time was reset or loaded
	}
	BrainCarryMs += DeltaMs;
	int32 Frames = 0;
	while (BrainCarryMs >= EngineFrameMs - 1e-6 && Frames < 30)
	{
		BrainCarryMs -= EngineFrameMs;
		BrainClockMs += EngineFrameMs;
		++Frames;
		// Dink (sprite 1) thinks first in the engine's sprite loop (D:16858); his brain's only part here is the bow (process_bow, D:14761-14766).
		ProcessBow(BrainClockMs);
		TArray<int32> Handles;
		const int32 Screen = D->GetDink().Screen;
		for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
		{
			const FDinkSprite& S = Pair.Value;
			if (Pair.Key != 1 && Pair.Key != UDinkDirector::HandleNoSprite && S.bActive && !S.bText && (S.Screen == Screen || S.Screen <= 0))
			{
				Handles.Add(Pair.Key);
			}
		}
		Handles.Sort();
		for (const int32 H : Handles)
		{
			ThinkSprite(H, BrainClockMs);
		}
	}
	if (Frames >= 30)
	{
		BrainCarryMs = FMath::Min(BrainCarryMs, EngineFrameMs); // a long hitch: drop the backlog instead of fast-forwarding
	}
}

void UDinkGameplay::ThinkSprite(int32 H, double Tick)
{
	UDinkDirector* D = Director();
	FDinkSprite* S = D ? D->FindSprite(H) : nullptr;
	if (!S || !S->bActive || S->bText || H == 1 || H == UDinkDirector::HandleNoSprite)
	{
		return;
	}
	const bool bScripted = S->bMoving;
	if (!bScripted)
	{
		S->X = Px(S->X);
		S->Y = Px(S->Y);
	}
	const double X0 = S->X, Y0 = S->Y;
	const int32 Size0 = S->GetProp(B_Size, 100);
	MovePath.Reset();
	MovePath.Add(FIntPoint(Px(S->X), Px(S->Y)));

	// The timer gate (D:16830): a sprite with sp_timing thinks once every timing ms; the animation runs every frame.
	bool bThink = true;
	const int32 Timing = S->GetProp(B_Timing);
	if (Timing > 0)
	{
		if (Tick > S->WaitMs)
		{
			S->WaitMs = Tick + Timing;
		}
		else
		{
			bThink = false;
		}
	}
	if (bThink)
	{
		switch (S->GetProp(B_Brain))
		{
		case 0: NoBrain(*S); break;
		case 2: BounceBrain(*S); break;
		case 3: DuckBrain(*S, Tick); break;
		case 4: PigBrain(*S, Tick); break;
		case 5: OneTimeBrain(*S, false); break;
		case 6: RepeatBrain(*S); break;
		case 7: OneTimeBrain(*S, true); break;
		case 9: PillBrain(*S, Tick); break;
		case 10: DragonBrain(*S, Tick); break;
		case 11: MissileBrain(*S, true); break;
		case 12: ScaleBrain(*S); break;
		case 15: ShadowBrain(*S); break;
		case 16: PeopleBrain(*S, Tick); break;
		case 17:
			MissileBrain(*S, false);
			if (FDinkSprite* M = D->FindSprite(H); M && M->bActive && M->GetProp(B_Seq) == 0)
			{
				D->DeactivateSprite(H, 0, /*bEndScripts*/ false); // missile_brain_expire (D:14426)
			}
			break;
		default: break; // 1 Dink, 8 text, 13 mouse, 14 button: not brains of world sprites here
		}
	}
	// Scripts the brain ran may have added sprites (the map may have moved) or removed this one.
	S = D->FindSprite(H);
	if (!S || !S->bActive)
	{
		return;
	}
	if (S->GetProp(B_Brain) != 13)
	{
		CheckIfMoveIsLegal(*S);
	}
	Animate(*S, Tick); // may run hit scripts: S is not used after this
	S = D->FindSprite(H);
	if (!S || !S->bActive)
	{
		return;
	}
	if (!S->bMoving && (S->X != X0 || S->Y != Y0))
	{
		AActor* Actor=S->Actor.Get();
		const bool bAuthoredBody=Actor && (Actor->ActorHasTag(TEXT("DinkCreature")) || Actor->ActorHasTag(TEXT("DinkHumanoid")));
		const FIntPoint Final(Px(S->X),Px(S->Y));
		FQuat ValidatedFacing = Actor ? Actor->GetActorQuat() : FQuat::Identity;
        if (bAuthoredBody) D->GetSpriteFacingRotation(*S, ValidatedFacing);
        if (bAuthoredBody && S->GetProp(B_MoveNoHard)!=1 && AuthoredActorMoveBlocked(*S,Final,Final,&ValidatedFacing))
		{
			S->X=X0; S->Y=Y0;
		}
		else
		{
			D->SyncActorToSprite(*S);
			if (bAuthoredBody) D->ApplyDir(*S, &ValidatedFacing);
		}
	}
	if (S->bSpawned && S->GetProp(B_Size, 100) != Size0)
	{
		if (AActor* Actor = S->Actor.Get())
		{
			Actor->SetActorScale3D(FVector(FMath::Max(1, S->GetProp(B_Size, 100)) / 100.0));
		}
	}
}

void UDinkGameplay::Animate(FDinkSprite& S, double Tick)
{
	// The forward animator of ThinkSprite (D:16956-17060); sp_reverse is not ported.
	const int32 Seq = S.GetProp(B_Seq);
	if (Seq <= 0 || S.GetProp(B_PicFreeze) != 0)
	{
		return;
	}
	int32 Frame = S.GetProp(B_Frame);
	const int32 FixedDelay = S.GetProp(B_FrameDelay);
	auto DelayOf = [this, Seq, FixedDelay](int32 F) { return FixedDelay != 0 ? FixedDelay : Data.FrameDelay(Seq, F); };
	if (Frame < 1)
	{
		// new animation
		S.Props.Add(B_PSeq, Seq);
		S.Props.Add(B_PFrame, 1);
		S.Props.Add(B_Frame, 1);
		S.FrameDelayMs = Tick + DelayOf(1);
		return;
	}
	if (Tick <= S.FrameDelayMs)
	{
		return;
	}
	++Frame;
	S.FrameDelayMs = Tick + DelayOf(Frame);
	S.Props.Add(B_PSeq, Seq);
	S.Props.Add(B_PFrame, Frame);
	S.Props.Add(B_Frame, Frame);
	int32 Code = Data.FrameCode(Seq, Frame);
	if (Code == -1)
	{
		Frame = 1;
		S.Props.Add(B_Frame, 1);
		S.Props.Add(B_PFrame, 1);
		S.FrameDelayMs = Tick + DelayOf(1);
		Code = Data.FrameCode(Seq, 1);
	}
	if (Code < 1)
	{
		// the animation is over: the last picture stays, seq_orig remembers it (walk cycles restart from it)
		S.Props.Add(B_PFrame, FMath::Max(1, Frame - 1));
		S.Props.Add(B_Frame, 0);
		S.SeqOrig = Seq;
		S.Props.Add(B_Seq, 0);
		S.Props.Add(B_NoControl, 0);
		return;
	}
	const FDinkFrameInfo* Info = Data.FindFrame(Seq, Frame);
	if (Info && Info->bSpecial)
	{
		// "this sprite can damage others right now!" (D:17050)
		RunThroughTagList(S.Handle);
	}
}

// ---------------------------------------------------------------------------------------------
// Movement helpers

int32 UDinkGameplay::GetHard(int32 Screen, int32 X, int32 Y) const
{
	int32 X1 = X - 20;
	int32 Y1 = Y;
	if (IsScreenLocked())
	{
		// get_hard's screenlock fix (D:532), including its y test that reads x1.
		if (X1 < 0 && X1 > -5) { X1 = 0; }
		else if (X1 > 599 && X1 < 605) { X1 = 599; }
		if (Y1 < 0 && Y1 > -5) { Y1 = 0; }
		else if (Y1 > 399 && X1 < 405) { Y1 = 399; }
	}
	if (const FLiveHardness* Live = LiveHardness.Find(Screen))
	{
		// A script redrew the map in this screen visit (draw_hard_sprite / draw_hard_map): g_hitmap as they left it.
		return Live->Map->Get(X1, Y1);
	}
	const UDinkFactSubsystem* Facts = Story ? Story->GetFacts() : nullptr;
	const FDinkHardnessMap* Map = Data.GetHardness(Screen, Facts ? Facts->GetFact(TEXT("vision")) : 0);
	const int32 Code = Map ? Map->Get(X1, Y1) : 0;
	if (Code > 100)
	{
		// A placement's hardbox: gone if the placement was removed (the engine never stamps removed ones).
		const UDinkWorldStateSubsystem* World = Story ? Story->GetWorldState() : nullptr;
		if (World && World->IsPlacementRemoved(FDinkOriginId(Screen, Code - 100)))
		{
			return 0;
		}
	}
	return Code;
}

int32 UDinkGameplay::GetDistanceAndDir(int32 H, int32 H1, int32& OutDir) const
{
	UDinkDirector* D = Director();
	const FDinkSprite* A = D ? D->FindSprite(H) : nullptr;
	const FDinkSprite* B = D ? D->FindSprite(H1) : nullptr;
	if (!A || !B)
	{
		return 5000;
	}
	const int32 Ax = Px(A->X), Ay = Px(A->Y), Bx = Px(B->X), By = Px(B->Y);
	int32 DistX = 5000, DistY = 5000, DirX = OutDir, DirY = OutDir;
	if (Ax > Bx && Ax - Bx < DistX) { DistX = Ax - Bx; DirX = 4; }
	if (Ax <= Bx && Bx - Ax < DistX) { DistX = Bx - Ax; DirX = 6; }
	if (Ay > By && Ay - By < DistY) { DistY = Ay - By; DirY = 8; }
	if (Ay <= By && By - Ay < DistY) { DistY = By - Ay; DirY = 2; }
	if (DistX > DistY)
	{
		OutDir = DirX;
		return DistX;
	}
	OutDir = DirY;
	return DistY;
}

void UDinkGameplay::ChangeDir(FDinkSprite& S, int32 Dir1, int32 Base)
{
	// changedir (D:5596). For sprites other than Dink and brains 9/10 the speed is scaled by base_timing / 4,
	// which is 1 at the locked 60 fps, and capped at 49.
	int32 Speed = S.GetProp(B_Speed, 1);
	const int32 Brain = S.GetProp(B_Brain);
	if (S.Handle > 1 && Brain != 9 && Brain != 10)
	{
		Speed = FMath::Min(Speed, 49);
	}
	const int32 OldSeq = S.GetProp(B_Seq);
	int32 Seq = OldSeq;
	int32 Mx = S.GetProp(B_Mx), My = S.GetProp(B_My);
	auto Active = [this](int32 Q) { return Data.SeqExists(Q); };
	S.Dir = Dir1;
	switch (Dir1)
	{
	case 1:
		Mx = -Speed + Speed / 3; My = Speed - Speed / 3;
		if (Base != -1) { Seq = Base + 1; if (!Active(Seq)) { Seq = Base + 9; } }
		break;
	case 2:
		Mx = 0; My = Speed;
		if (Base != -1) { Seq = Base + 2; }
		if (!Active(Seq) && Active(Base + 3)) { Seq = Base + 3; }
		if (!Active(Seq) && Active(Base + 1)) { Seq = Base + 1; }
		break;
	case 3:
		Mx = Speed - Speed / 3; My = Speed - Speed / 3;
		if (Base != -1) { Seq = Base + 3; if (!Active(Seq)) { Seq = Base + 7; } }
		break;
	case 4:
		Mx = -Speed; My = 0;
		if (Base != -1) { Seq = Base + 4; }
		if (!Active(Seq) && Active(Base + 7)) { Seq = Base + 7; }
		if (!Active(Seq) && Active(Base + 1)) { Seq = Base + 1; }
		break;
	case 6:
		Mx = Speed; My = 0;
		if (Base != -1) { Seq = Base + 6; }
		if (!Active(Seq) && Active(Base + 3)) { Seq = Base + 3; }
		if (!Active(Seq) && Active(Base + 9)) { Seq = Base + 9; }
		break;
	case 7:
		Mx = -Speed + Speed / 3; My = -Speed + Speed / 3;
		if (Base != -1) { Seq = Base + 7; if (!Active(Seq)) { Seq = Base + 3; } }
		break;
	case 8:
		Mx = 0; My = -Speed;
		if (Base != -1) { Seq = Base + 8; }
		if (!Active(Seq) && Active(Base + 7)) { Seq = Base + 7; }
		if (!Active(Seq) && Active(Base + 9)) { Seq = Base + 9; }
		break;
	case 9:
		Mx = Speed - Speed / 3; My = -Speed + Speed / 3;
		if (Base != -1) { Seq = Base + 9; if (!Active(Seq)) { Seq = Base + 1; } }
		break;
	default:
		break;
	}
	if (OldSeq != Seq)
	{
		S.Props.Add(B_Frame, 0);
		S.FrameDelayMs = 0.0;
	}
	if (!Active(Seq))
	{
		Seq = OldSeq;
	}
	S.Props.Add(B_Seq, Seq);
	S.Props.Add(B_Mx, Mx);
	S.Props.Add(B_My, My);
}

void UDinkGameplay::AutoMove(FDinkSprite& S)
{
	// automove (D:12214) + move (D:13520): one pixel at a time, x for the first |mx| steps, y for the
	// first |my|; every pixel goes on the path that check_if_move_is_legal walks.
	const int32 Mx = S.GetProp(B_Mx), My = S.GetProp(B_My);
	const int32 Ax = FMath::Abs(Mx), Ay = FMath::Abs(My);
	const int32 Amount = FMath::Max(Ax, Ay);
	int32 X = Px(S.X), Y = Px(S.Y);
	if (MovePath.Num() == 0)
	{
		MovePath.Add(FIntPoint(X, Y));
	}
	for (int32 i = 1; i <= Amount; ++i)
	{
		if (i <= Ax) { X += Mx > 0 ? 1 : -1; }
		if (i <= Ay) { Y += My > 0 ? 1 : -1; }
		MovePath.Add(FIntPoint(X, Y));
	}
	S.X = X;
	S.Y = Y;
}

int32 UDinkGameplay::CheckIfMoveIsLegal(FDinkSprite& S)
{
	if (S.GetProp(B_MoveNoHard) == 1)
	{
		return 0;
	}
	const bool bFlying = S.GetProp(B_Flying) != 0;
	for (int32 i = 1; i < MovePath.Num(); ++i)
	{
		int32 Hard = GetHard(S.Screen, MovePath[i].X, MovePath[i].Y);
		if (Hard == 0 && AuthoredActorMoveBlocked(S, MovePath[i - 1], MovePath[i])) { Hard = 1; }
		if (Hard == 2 && bFlying)
		{
			// a flyer over low hardness: the rest of the path is not looked at (D:13428)
			MovePath.SetNum(1);
			return 0;
		}
		if (Hard > 0)
		{
			S.X = MovePath[i - 1].X;
			S.Y = MovePath[i - 1].Y;
			MovePath.SetNum(1);
			MovePath[0] = FIntPoint(Px(S.X), Px(S.Y));
			return Hard;
		}
	}
	return 0;
}

int32 UDinkGameplay::AutoReverse(FDinkSprite& S)
{
	const int32 R = RandomModulo(2) + 1;
	const int32 Dir = S.Dir;
	if (Dir == 1 || Dir == 2) { return R == 1 ? 8 : 6; }
	if (Dir == 3 || Dir == 6) { return R == 1 ? 2 : 4; }
	if (Dir == 9 || Dir == 8) { return R == 1 ? 2 : 6; }
	if (Dir == 7 || Dir == 4) { return R == 1 ? 8 : 6; }
	return 0;
}

int32 UDinkGameplay::AutoReverseDiag(FDinkSprite& S)
{
	if (S.Dir == 0)
	{
		S.Dir = 7;
	}
	const int32 R = RandomModulo(2) + 1;
	const int32 Dir = S.Dir;
	if (Dir == 1 || Dir == 3) { return R == 1 ? 9 : 7; }
	if (Dir == 3 || Dir == 6) { return R == 1 ? 7 : 1; }
	if (Dir == 9 || Dir == 8) { return R == 1 ? 1 : 7; }
	if (Dir == 7 || Dir == 4) { return R == 1 ? 3 : 9; }
	return 0;
}

bool UDinkGameplay::ProcessFollow(FDinkSprite& S)
{
	// process_follow (D:12560): walk towards the followed sprite until within 40 px.
	UDinkDirector* D = Director();
	const int32 Follow = S.GetProp(B_Follow);
	const FDinkSprite* F = D->FindSprite(Follow);
	if (!F || !F->bActive)
	{
		S.Props.Add(B_Follow, 0);
		return false;
	}
	int32 Dir = S.Dir;
	if (GetDistanceAndDir(S.Handle, Follow, Dir) < 40)
	{
		return true;
	}
	ChangeDir(S, Dir, S.GetProp(B_BaseWalk, -1));
	AutoMove(S);
	return true;
}

void UDinkGameplay::ProcessTarget(FDinkSprite& S)
{
	// process_target (D:12588): one step towards the target unless within sp_distance.
	UDinkDirector* D = Director();
	const int32 Target = S.GetProp(B_Target);
	const FDinkSprite* T = D->FindSprite(Target);
	if (!T || !T->bActive)
	{
		S.Props.Add(B_Target, 0);
		return;
	}
	int32 Dir = S.Dir;
	if (GetDistanceAndDir(S.Handle, Target, Dir) < S.GetProp(B_Distance))
	{
		return;
	}
	ChangeDir(S, Dir, S.GetProp(B_BaseWalk, -1));
	AutoMove(S);
}

// ---------------------------------------------------------------------------------------------
// The 3D adaptation layer

int32 UDinkGameplay::CountAttackers(int32 Target, int32 Except) const
{
	int32 N = 0;
	if (const UDinkDirector* D = Director())
	{
		for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
		{
			const FDinkSprite& S = Pair.Value;
			if (Pair.Key == Except || !S.bActive || S.GetProp(B_Target) != Target)
			{
				continue;
			}
			const int32 BaseAttack = S.GetProp(B_BaseAttack, -1);
			if (S.bWindingUp || (BaseAttack != -1 && S.GetProp(B_Seq) > 0 && InThisBase(S.GetProp(B_Seq), BaseAttack)))
			{
				++N;
			}
		}
	}
	return N;
}

bool UDinkGameplay::AdaptationAllowsAttack(FDinkSprite& S, int32 Target, int32& InOutDir, double Tick)
{
	if (!Adaptation.bEnabled)
	{
		return true;
	}
	if (S.bWindingUp)
	{
		if (Tick < S.WindUpUntilMs)
		{
			return false;
		}
		// the telegraphed attack goes where it was aimed, so a player who moved away can dodge it
		S.bWindingUp = false;
		S.Props.Add(B_Telegraph, 0);
		InOutDir = S.WindUpDir;
		return true;
	}
	if (CountAttackers(Target, S.Handle) >= Adaptation.MaxAttackers)
	{
		// capped: hold position facing the target and look again shortly
		S.Props.Add(B_Mx, 0);
		S.Props.Add(B_My, 0);
		S.Dir = InOutDir;
		S.MoveWaitMs = Tick + Adaptation.HoldReaimMs;
		return false;
	}
	if (Adaptation.WindUpMs <= 0.0)
	{
		return true;
	}
	S.bWindingUp = true;
	S.WindUpUntilMs = Tick + Adaptation.WindUpMs;
	S.WindUpDir = InOutDir;
	S.Dir = InOutDir;
	S.Props.Add(B_Telegraph, 1);
	S.Props.Add(B_Mx, 0);
	S.Props.Add(B_My, 0);
	S.Props.Add(B_Seq, 0);
	Note(FString::Printf(TEXT("wind-up %d at %d (%.0f ms)"), S.Handle, Target, Adaptation.WindUpMs));
	if (const AActor* Actor = S.Actor.Get())
	{
		if (UWorld* World = Actor->GetWorld())
		{
			// Greybox telegraph placeholder: a red marker over the attacker for the wind-up.
			DrawDebugSphere(World, Actor->GetActorLocation() + FVector(0, 0, 150), 25.f, 8, FColor::Red, false, static_cast<float>(Adaptation.WindUpMs / 1000.0), 0, 3.f);
		}
	}
	return false;
}

void UDinkGameplay::RunAttackScript(FDinkSprite& S)
{
	const int32 H = S.Handle;
	if (!S.Script.IsNone() && Story->HasProcedure(S.Script, Proc_Attack))
	{
		Note(FString::Printf(TEXT("attack %d (%s)"), H, *S.Script.ToString()));
		RunProc(H, Proc_Attack); // S may be stale after this
	}
}

// ---------------------------------------------------------------------------------------------
// Brains

void UDinkGameplay::NoBrain(FDinkSprite& S)
{
	// no_brain (D:13200)
	if (S.bMoving || S.bFrozen)
	{
		return;
	}
	if (S.GetProp(B_Follow) > 0)
	{
		ProcessFollow(S);
	}
}

void UDinkGameplay::BounceBrain(FDinkSprite& S)
{
	// bounce_brain (D:13616): flies, bouncing off the screen's edges (picture box), no hardness.
	const FDinkFrameInfo* Pic = Data.FindFrame(S.GetProp(B_PSeq), FMath::Max(1, S.GetProp(B_PFrame, 1)));
	const int32 W = Pic ? Pic->Width : 0, Hgt = Pic ? Pic->Height : 0;
	int32 Mx = S.GetProp(B_Mx), My = S.GetProp(B_My);
	if (S.Y > GameAreaY - Hgt) { My = -My; }
	if (S.X > ScreenSizeX - W) { Mx = -Mx; }
	if (S.Y < 0) { My = -My; }
	if (S.X < 0) { Mx = -Mx; }
	S.Props.Add(B_Mx, Mx);
	S.Props.Add(B_My, My);
	S.X += Mx;
	S.Y += My;
}

void UDinkGameplay::DuckBrain(FDinkSprite& S, double Tick)
{
	// duck_brain (D:12723); its damage half (head flies off, duckdie) is in ProcessDamage.
	if (S.bMoving || S.bFrozen)
	{
		return;
	}
	if (S.GetProp(B_Follow) > 0)
	{
		ProcessFollow(S);
		return;
	}
	const int32 Base = S.GetProp(B_BaseWalk, -1);
	bool bWalk = false;
	if (Base == 110)
	{
		RandomModulo(100); // random_blood's roll (the blood is not drawn)
		bWalk = true;
	}
	if (!bWalk && S.GetProp(B_Seq) == 0)
	{
		if (RandomModulo(12) + 1 == 1)
		{
			const int32 Hold = RandomModulo(9) + 1;
			if (Hold != 2 && Hold != 8 && Hold != 5)
			{
				ChangeDir(S, Hold, Base);
			}
			else
			{
				// quack: sound 1, pitch by size; the duck stops for a moment
				const int32 Size = S.GetProp(B_Size, 100);
				const int32 Pitch = Size >= 100 ? 18000 - Size * 50 : 16000 + Size * 100;
				Director()->Audio.Cue(FString::Printf(TEXT("sound:1 speed=%d sprite %d (duck)"), Pitch, S.Handle));
				S.Props.Add(B_Mx, 0);
				S.Props.Add(B_My, 0);
				S.WaitMs = Tick + RandomModulo(300) + 200;
			}
			return;
		}
		if (S.GetProp(B_Mx) != 0 || S.GetProp(B_My) != 0)
		{
			S.Props.Add(B_Seq, S.SeqOrig);
		}
	}
	if (S.Y > GameAreaY) { ChangeDir(S, 9, Base); }
	if (S.X > RightBarX - 30) { ChangeDir(S, 7, Base); }
	if (S.Y < 10) { ChangeDir(S, 1, Base); }
	if (S.X < 30) { ChangeDir(S, 3, Base); }
	AutoMove(S);
	if (CheckIfMoveIsLegal(S) != 0 && S.Dir != 0)
	{
		ChangeDir(S, AutoReverseDiag(S), Base);
	}
}

void UDinkGameplay::PigBrain(FDinkSprite& S, double Tick)
{
	// pig_brain (D:13356); its damage half is in ProcessDamage.
	if (S.bMoving || S.bFrozen)
	{
		return;
	}
	const int32 Base = S.GetProp(B_BaseWalk, -1);
	if (S.GetProp(B_Seq) == 0)
	{
		if (RandomModulo(12) + 1 == 1)
		{
			int32 Hold = RandomModulo(9) + 1;
			if (Hold != 4 && Hold != 6 && Hold != 2 && Hold != 8 && Hold != 5)
			{
				ChangeDir(S, Hold, Base);
			}
			else
			{
				const int32 Size = S.GetProp(B_Size, 100);
				const int32 Pitch = Size >= 100 ? 18000 - Size * 50 : 16000 + Size * 100;
				Hold = RandomModulo(4) + 1;
				Director()->Audio.Cue(FString::Printf(TEXT("sound:%d speed=%d sprite %d (pig)"), Hold + 1, Pitch, S.Handle));
				S.Props.Add(B_Mx, 0);
				S.Props.Add(B_My, 0);
				S.WaitMs = Tick + RandomModulo(300) + 200;
			}
		}
		else if (S.GetProp(B_Mx) != 0 || S.GetProp(B_My) != 0)
		{
			S.Props.Add(B_Seq, S.SeqOrig);
		}
	}
	const FDinkFrameInfo* Pic = Data.FindFrame(S.GetProp(B_PSeq), FMath::Max(1, S.GetProp(B_PFrame, 1)));
	const int32 W = Pic ? Pic->Width : 0, Hgt = Pic ? Pic->Height : 0;
	if (S.Y > GameAreaY - Hgt / 4) { ChangeDir(S, 9, Base); }
	if (S.X > ScreenSizeX - W - 10) { ChangeDir(S, 1, Base); }
	if (S.Y < 10) { ChangeDir(S, 1, Base); }
	if (S.X < 10) { ChangeDir(S, 3, Base); }
	AutoMove(S);
	if (CheckIfMoveIsLegal(S) != 0)
	{
		ChangeDir(S, AutoReverseDiag(S), Base);
	}
}

void UDinkGameplay::OneTimeBrain(FDinkSprite& S, bool bForReal)
{
	// one_time_brain (5, D:15741: plays once, then the last frame is drawn into the background) and
	// one_time_brain_for_real (7, D:15772: plays once, then gone). Both end the sprite when the animation ends.
	if (S.bMoving && !bForReal)
	{
		return;
	}
	if (S.GetProp(B_Follow) > 0)
	{
		ProcessFollow(S);
	}
	if (S.GetProp(B_Seq) == 0)
	{
		Director()->DeactivateSprite(S.Handle, 0, /*bEndScripts*/ false);
		return;
	}
	if (S.bMoving)
	{
		return; // the director moves it (process_move); a second step on top would double its speed
	}
	if (!bForReal || S.Dir > 0)
	{
		ChangeDir(S, S.Dir, -1);
		AutoMove(S);
	}
}

void UDinkGameplay::RepeatBrain(FDinkSprite& S)
{
	// repeat_brain (D:15832): loops its sequence; a placement starts from its map.dat picture.
	if (S.SeqOrig == 0 && S.Origin.IsValid())
	{
		if (const FDinkPlacementInfo* P = Data.FindPlacement(S.Origin))
		{
			S.SeqOrig = P->Seq;
			S.Props.Add(B_Frame, P->Frame);
			S.WaitMs = 0.0;
		}
	}
	if (S.GetProp(B_Seq) == 0)
	{
		S.Props.Add(B_Seq, S.SeqOrig);
	}
}

void UDinkGameplay::ScaleBrain(FDinkSprite& S)
{
	// scale_brain (D:15798): size moves 5 (= 5 * base_timing / 4) per think towards brain_parm, then gone.
	const int32 Target = S.GetProp(B_BrainParm);
	int32 Size = S.GetProp(B_Size, 100);
	if (Size == Target)
	{
		Note(FString::Printf(TEXT("vanished %d"), S.Handle));
		Director()->DeactivateSprite(S.Handle, 0, /*bEndScripts*/ false);
		return;
	}
	int32 Num = 5;
	if (Size > Target)
	{
		if (Size - Num < Target) { Num = Size - Target; }
		Size -= Num;
	}
	if (Size < Target)
	{
		if (Size + Num > Target) { Num = Target - Size; }
		Size += Num;
	}
	S.Props.Add(B_Size, Size);
	if (S.bMoving)
	{
		return;
	}
	if (S.Dir > 0)
	{
		ChangeDir(S, S.Dir, -1);
		AutoMove(S);
	}
}

void UDinkGameplay::ShadowBrain(FDinkSprite& S)
{
	// shadow_brain (D:13218): sits under the sprite in brain_parm, gone with it.
	const FDinkSprite* Owner = Director()->FindSprite(S.GetProp(B_BrainParm));
	if (!Owner || !Owner->bActive)
	{
		Director()->DeactivateSprite(S.Handle, 0, /*bEndScripts*/ false);
		return;
	}
	S.X = Owner->X;
	S.Y = Owner->Y;
	S.Props.Add(B_Size, Owner->GetProp(B_Size, 100));
	if (S.GetProp(B_Seq) == 0 && S.SeqOrig != 0)
	{
		S.Props.Add(B_Seq, S.SeqOrig);
	}
}

void UDinkGameplay::PillBrain(FDinkSprite& S, double Tick)
{
	// pill_brain (D:12887): the monster. Its damage half (hitpoints, die, corpse, exp) is in ProcessDamage.
	if (S.bMoving || S.bFrozen)
	{
		return;
	}
	if (S.GetProp(B_Follow) > 0)
	{
		ProcessFollow(S);
	}
	const int32 Base = S.GetProp(B_BaseWalk, -1);
	const int32 BaseAttack = S.GetProp(B_BaseAttack, -1);
	const int32 Target = S.GetProp(B_Target);
	bool bWalkNormal = true;
	if (Target != 0)
	{
		if (InThisBase(S.GetProp(B_Seq), BaseAttack))
		{
			return; // still attacking (as in the engine, seq 0 with base_attack 0 counts too: such a sprite waits)
		}
		if (S.bWindingUp)
		{
			// adaptation layer: the telegraph is committed; it attacks when it ends, wherever the target went
			int32 Dir = S.WindUpDir;
			if (AdaptationAllowsAttack(S, Target, Dir, Tick))
			{
				S.Dir = Dir;
				S.Props.Add(B_Seq, BaseAttack + Dir);
				S.Props.Add(B_Frame, 0);
				if (!S.Script.IsNone()) { RunAttackScript(S); }
				else { S.MoveWaitMs = Tick + RandomModulo(300) + 10; }
			}
			return;
		}
		if (S.GetProp(B_Distance) == 0)
		{
			S.Props.Add(B_Distance, 5);
		}
		int32 Dir = S.Dir;
		const int32 Distance = GetDistanceAndDir(S.Handle, Target, Dir);
		if (Distance < S.GetProp(B_Distance) && S.GetProp(B_AttackWait) < Tick && BaseAttack != -1)
		{
			int32 AttackDir = Dir; // get_distance_and_dir with smooth_follow off: the same cardinal direction
			if (!AdaptationAllowsAttack(S, Target, AttackDir, Tick))
			{
				return;
			}
			S.Dir = AttackDir;
			S.Props.Add(B_Seq, BaseAttack + AttackDir);
			S.Props.Add(B_Frame, 0);
			if (!S.Script.IsNone())
			{
				RunAttackScript(S); // the script sets sp_attack_wait (en-bonc: random 0..4 s)
			}
			else
			{
				S.MoveWaitMs = Tick + RandomModulo(300) + 10;
			}
			return;
		}
		if (S.MoveWaitMs < Tick)
		{
			ProcessTarget(S);
			S.MoveWaitMs = Tick + 200;
			return;
		}
		// between re-aims it walks on like a wanderer (goto walk_normal)
	}
	if (bWalkNormal)
	{
		const bool bRecal = (Base != -1 && S.GetProp(B_Seq) == 0) || (S.GetProp(B_Seq) == 0 && S.MoveWaitMs < Tick);
		if (bRecal)
		{
			// recal: 1 in 12 a new diagonal direction, else keep walking the last walk cycle (D:12985)
			for (int32 Guard = 0; Guard < 1000; ++Guard)
			{
				if (RandomModulo(12) + 1 == 1)
				{
					const int32 Hold = RandomModulo(9) + 1;
					if (Hold != 4 && Hold != 6 && Hold != 2 && Hold != 8 && Hold != 5)
					{
						ChangeDir(S, Hold, Base);
						S.MoveWaitMs = Tick + RandomModulo(2000) + 200;
					}
					break;
				}
				if (InThisBase(S.SeqOrig, BaseAttack))
				{
					continue;
				}
				S.Props.Add(B_Seq, S.SeqOrig);
				if (S.SeqOrig == 0)
				{
					continue;
				}
				break;
			}
		}
	}
	// It stays on its screen: near an edge it turns back in (D:13006).
	if (S.Y > GameAreaY - 15) { ChangeDir(S, 9, Base); }
	if (S.X > RightBarX - 15) { ChangeDir(S, 1, Base); }
	if (S.Y < 18) { ChangeDir(S, 1, Base); }
	if (S.X < 18) { ChangeDir(S, 3, Base); }
	AutoMove(S);
	if (CheckIfMoveIsLegal(S) != 0)
	{
		S.MoveWaitMs = Tick + 400;
		ChangeDir(S, AutoReverseDiag(S), Base);
	}
}

void UDinkGameplay::DragonBrain(FDinkSprite& S, double Tick)
{
	// dragon_brain (D:13234): cardinal wanderer; with a target it runs its script's ATTACK whenever
	// sp_attack_wait has passed (the dragon's fireballs, Seth's spells). Its damage half is in ProcessDamage.
	if (S.bMoving || S.bFrozen)
	{
		return;
	}
	if (S.GetProp(B_Follow) > 0)
	{
		ProcessFollow(S);
		return;
	}
	const int32 H = S.Handle;
	const int32 Target = S.GetProp(B_Target);
	if (Target != 0 && (S.bWindingUp || S.GetProp(B_AttackWait) < Tick) && !S.Script.IsNone() && Story->HasProcedure(S.Script, Proc_Attack))
	{
		int32 Dir = S.bWindingUp ? S.WindUpDir : S.Dir;
		if (!S.bWindingUp)
		{
			GetDistanceAndDir(H, Target, Dir);
		}
		if (!AdaptationAllowsAttack(S, Target, Dir, Tick))
		{
			return;
		}
		RunAttackScript(S);
		FDinkSprite* After = Director()->FindSprite(H);
		if (!After || !After->bActive || After != &S)
		{
			return; // the script changed the sprite table; think again next frame
		}
	}
	const int32 Base = S.GetProp(B_BaseWalk, -1);
	if (S.GetProp(B_Seq) == 0)
	{
		for (int32 Guard = 0; Guard < 1000; ++Guard)
		{
			if (RandomModulo(12) + 1 == 1)
			{
				const int32 Hold = RandomModulo(9) + 1;
				if (Hold != 1 && Hold != 3 && Hold != 7 && Hold != 9 && Hold != 5)
				{
					ChangeDir(S, Hold, Base);
				}
				break;
			}
			S.Props.Add(B_Seq, S.SeqOrig);
			if (S.SeqOrig != 0)
			{
				break;
			}
		}
	}
	if (S.Y > GameAreaY) { ChangeDir(S, 8, Base); }
	if (S.X > ScreenSizeX) { ChangeDir(S, 4, Base); }
	if (S.Y < 0) { ChangeDir(S, 2, Base); }
	if (S.X < 0) { ChangeDir(S, 6, Base); }
	AutoMove(S);
	if (CheckIfMoveIsLegal(S) != 0)
	{
		ChangeDir(S, AutoReverse(S), Base);
	}
}

void UDinkGameplay::FindAction(FDinkSprite& S, double Tick)
{
	// find_action (D:13046): sit and think (face a random diagonal) or walk a random diagonal.
	S.Action = RandomModulo(2) + 1;
	const int32 Base = S.GetProp(B_BaseWalk, -1);
	static const int32 Diagonals[5] = { 0, 1, 3, 7, 9 };
	if (S.Action == 1)
	{
		S.MoveWaitMs = Tick + RandomModulo(3000) + 400;
		if (Base != -1)
		{
			const int32 Dir = RandomModulo(4) + 1;
			S.Props.Add(B_PFrame, 1);
			S.Props.Add(B_PSeq, Base + Diagonals[Dir]);
		}
		return;
	}
	S.MoveWaitMs = Tick + RandomModulo(3000) + 500;
	const int32 Dir = RandomModulo(4) + 1;
	S.Props.Add(B_PFrame, 1);
	ChangeDir(S, Diagonals[Dir], Base);
}

void UDinkGameplay::PeopleBrain(FDinkSprite& S, double Tick)
{
	// people_brain (D:13087): townsfolk sit and walk in turn. Its damage half is in ProcessDamage.
	if (S.bMoving || S.bFrozen)
	{
		return;
	}
	if (S.GetProp(B_Follow) > 0)
	{
		ProcessFollow(S);
		return;
	}
	if (S.MoveWaitMs < Tick && S.GetProp(B_Seq) == 0)
	{
		S.Action = 0;
	}
	if (S.Action == 0)
	{
		FindAction(S, Tick);
	}
	if (S.Action != 2)
	{
		S.Props.Add(B_Seq, 0);
		return;
	}
	if (S.SeqOrig != 0 && S.GetProp(B_Seq) == 0)
	{
		S.Props.Add(B_Seq, S.SeqOrig);
	}
	const int32 Base = S.GetProp(B_BaseWalk, -1);
	if (S.Y > GameAreaY) { ChangeDir(S, RandomModulo(2) + 1 == 1 ? 9 : 7, Base); }
	if (S.X > RightBarX) { ChangeDir(S, RandomModulo(2) + 1 == 1 ? 1 : 7, Base); }
	if (S.Y < 20) { ChangeDir(S, RandomModulo(2) + 1 == 1 ? 1 : 3, Base); }
	if (S.X < 30) { ChangeDir(S, RandomModulo(2) + 1 == 1 ? 3 : 9, Base); }
	AutoMove(S);
	if (CheckIfMoveIsLegal(S) != 0)
	{
		if (RandomModulo(3) == 2)
		{
			ChangeDir(S, AutoReverseDiag(S), Base);
		}
		else
		{
			S.MoveWaitMs = 0.0;
			S.Props.Add(B_PFrame, 1);
			S.Props.Add(B_Seq, 0);
		}
	}
}

void UDinkGameplay::MissileBrain(FDinkSprite& S, bool bRepeat)
{
	// missile_brain (D:14240): flies its mx/my; a wall (any hardness but low, which flyers cross) ends it
	// through its `damage` procedure (&missile_target 0) or silently; a placement's hardbox runs that
	// sprite's `hit` and the missile's `damage` (&missile_target = it); then every sprite it overlaps
	// (hardbox + sp_range) takes missile damage and runs `hit`.
	UDinkDirector* D = Director();
	const int32 H = S.Handle;
	AutoMove(S);
	SetFact(TEXT("missle_source"), H);
	const int32 Hard = CheckIfMoveIsLegal(S);
	if (bRepeat && S.GetProp(B_Seq) == 0)
	{
		S.Props.Add(B_Seq, S.SeqOrig);
	}
	auto HitSound = [D](const FDinkSprite& M)
	{
		const int32 Sound = M.GetProp(B_AttackHitSound);
		D->Audio.Cue(Sound == 0 ? FString(TEXT("sound:9 speed=22050 hit")) : FString::Printf(TEXT("sound:%d speed=%d hit"), Sound, M.GetProp(B_AttackHitSoundSpeed)));
	};
	if (Hard > 0 && Hard != 2)
	{
		if (Hard > 100)
		{
			// a placement's hardbox: find its sprite (sp_index == hard - 100)
			int32 Owner = 0;
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				if (Pair.Value.Origin.IsValid() && Pair.Value.Screen == S.Screen && Pair.Value.Origin.Placement == Hard - 100)
				{
					Owner = Pair.Key;
					break;
				}
			}
			if (Owner != 0)
			{
				Note(FString::Printf(TEXT("missile %d hits the hardbox of %d"), H, Owner));
				if (const FDinkSprite* O = D->FindSprite(Owner); O && !O->Script.IsNone())
				{
					SetFact(TEXT("missile_target"), 1);
					SetFact(TEXT("enemy_sprite"), 1);
					RunProc(Owner, Proc_Hit);
				}
				const FDinkSprite* M = D->FindSprite(H);
				if (M && !M->Script.IsNone())
				{
					SetFact(TEXT("missile_target"), Owner);
					SetFact(TEXT("enemy_sprite"), 1);
					RunProc(H, Proc_Damage);
				}
				else if (M)
				{
					HitSound(*M);
					D->DeactivateSprite(H, 0, /*bEndScripts*/ false);
				}
				return;
			}
		}
		Note(FString::Printf(TEXT("missile %d hits a wall (hardness %d)"), H, Hard));
		if (!S.Script.IsNone())
		{
			SetFact(TEXT("missile_target"), 0);
			RunProc(H, Proc_Damage);
		}
		else
		{
			HitSound(S);
			D->DeactivateSprite(H, 0, /*bEndScripts*/ false);
			return;
		}
	}
	FDinkSprite* M = D->FindSprite(H);
	if (!M)
	{
		return;
	}
	if (M->X > 1000 || M->Y > 700 || M->Y < -500 || M->X < -500)
	{
		D->DeactivateSprite(H, 0, /*bEndScripts*/ false);
	}
	const int32 Screen = M->Screen;
	for (const int32 J : LiveSprites(Screen))
	{
		M = D->FindSprite(H);
		FDinkSprite* T = D->FindSprite(J);
		if (!M || J == H || !T || !T->bActive || T->GetProp(B_NoHit) == 1 || T->bNoTouch || J == M->GetProp(B_BrainParm) || J == M->GetProp(B_BrainParm2))
		{
			continue;
		}
		int32 L, Tp, R, B;
		const int32 Range = M->GetProp(B_Range);
		if (!GetHardbox(*T, L, Tp, R, B) || !Inside(Px(M->X), Px(M->Y), L - Range, Tp - Range, R + Range, B + Range))
		{
			continue;
		}
		T->bNoTouch = true;
		T->NoTouchUntilMs = NowMs + DinkRules::MissileImmunityMs;
		T->Props.Add(B_Target, 1);
		SetFact(TEXT("enemy_sprite"), 1);
		Note(FString::Printf(TEXT("missile %d hits %d"), H, J));
		const int32 Strength = M->GetProp(B_Strength);
		if (!M->Script.IsNone())
		{
			SetFact(TEXT("missile_target"), J);
			RunProc(H, Proc_Damage);
		}
		else
		{
			HitSound(*M);
		}
		T = D->FindSprite(J);
		const int32 TargetHp = J == 1 ? GetFact(TEXT("life")) : (T ? T->GetProp(B_Hitpoints) : 0);
		if (T && TargetHp > 0 && Strength != 0)
		{
			const int32 Defense = J == 1 ? GetFact(TEXT("defense")) : T->GetProp(B_Defense);
			T->Damage += DinkRules::ResolveMissileHit(Strength, Defense, Rng());
			T->LastHit = 1;
		}
		if (T && !T->Script.IsNone())
		{
			SetFact(TEXT("missile_target"), 1);
			RunProc(J, Proc_Hit);
		}
	}
}

// ---------------------------------------------------------------------------------------------
// screenlock

void UDinkGameplay::SetScreenLock(bool bLocked)
{
	UDinkDirector* D = Director();
	if (!D)
	{
		return;
	}
	const bool bWas = D->bScreenLocked;
	D->bScreenLocked = bLocked;
	if (bWas != bLocked)
	{
		Note(FString::Printf(TEXT("screenlock %d"), bLocked ? 1 : 0));
	}
	if (UWorld* World = D->GetWorld())
	{
		if (UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>())
		{
			Greybox->SetScreenLocked(bLocked ? D->GetDink().Screen : 0, bLocked);
		}
	}
}

bool UDinkGameplay::IsScreenLocked() const
{
	const UDinkDirector* D = Director();
	return D && D->bScreenLocked;
}
