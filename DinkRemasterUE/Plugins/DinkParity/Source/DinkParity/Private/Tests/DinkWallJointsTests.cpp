// Dink.PhysicalPlay.WallJoints (26 Nov 2026, world scale follow-up, A71): on SCR_713 the dungeon walls P06 (drawn y 206-213) and P13 (drawn
// y 222-229) are staggered at the enlarged scale and their 1997 boxes (y 190-251) overlap at x 246-271. Trimming both to their drawn strips
// opened the slot between them, so #233's passage rule kept P06's whole box: a 6 m invisible wall north and south of the drawn one. The
// generator now trims P06 too with a joint (relaxed_hardboxes.json "joints": P06's drawn end over P13's box, P13's start over P06's, a plug
// across the slot where the modules meet). Checked in the real generated world (PIE), layer on: get_hard at the joint and the freed box,
// the walk-audit capsule mask (no free path from the south side of the wall to the north inside the two boxes), and a walk from the south
// that stops at P06's drawn face. Layer off: the 1997 boxes, unchanged.
#include "DinkTestHelpers.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkWalkAudit.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
TArray<bool> DecodeMask(const FString& Mask)
{
	TArray<bool> Out;
	int32 N = 0;
	for (const TCHAR C : Mask)
	{
		if (FChar::IsDigit(C)) { N = N * 10 + (C - TEXT('0')); continue; }
		for (int32 I = 0; I < N; ++I) Out.Add(C == TEXT('F'));
		N = 0;
	}
	return Out;
}

/** Free 3 px cells reachable from (Sx, Sy) inside the window [X0, X1] x [Y0, Y1] (map pixels); true if (Tx, Ty)'s cell is among them. */
bool ReachesInside(const TArray<bool>& Cells, int32 Sx, int32 Sy, int32 Tx, int32 Ty, int32 X0, int32 X1, int32 Y0, int32 Y1)
{
	const int32 GW = 200;
	const int32 C0 = X0 / 3, C1 = X1 / 3, R0 = Y0 / 3, R1 = Y1 / 3;
	TArray<bool> Seen; Seen.Init(false, Cells.Num());
	TArray<FIntPoint> Stack;
	const FIntPoint Start(Sx / 3, Sy / 3), Goal(Tx / 3, Ty / 3);
	if (!Cells.IsValidIndex(Start.Y * GW + Start.X) || !Cells[Start.Y * GW + Start.X]) return false;
	Stack.Add(Start); Seen[Start.Y * GW + Start.X] = true;
	while (Stack.Num())
	{
		const FIntPoint P = Stack.Pop();
		if (P == Goal) return true;
		for (const FIntPoint D : { FIntPoint(1, 0), FIntPoint(-1, 0), FIntPoint(0, 1), FIntPoint(0, -1) })
		{
			const FIntPoint Q = P + D;
			if (Q.X < C0 || Q.X > C1 || Q.Y < R0 || Q.Y > R1) continue;
			const int32 I = Q.Y * GW + Q.X;
			if (!Cells.IsValidIndex(I) || Seen[I] || !Cells[I]) continue;
			Seen[I] = true; Stack.Add(Q);
		}
	}
	return false;
}

class FDinkWallJointsPIE : public IAutomationLatentCommand
{
public:
	explicit FDinkWallJointsPIE(FAutomationTestBase* T) : Test(T) {}
	~FDinkWallJointsPIE()
	{
		if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.PhysicalPlay"))) V->Set(-1, ECVF_SetByConsole);
	}
	static void SetLayer(int32 Mode)
	{
		if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.PhysicalPlay"))) V->Set(Mode, ECVF_SetByConsole);
	}
	bool Update() override
	{
		if (!Began) Began = FPlatformTime::Seconds();
		if (FPlatformTime::Seconds() - Began > 300) { Test->AddError(TEXT("wall joints PIE timeout")); return true; }
		UWorld* W = GEditor ? GEditor->PlayWorld.Get() : nullptr;
		APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
		ADinkGreyboxCharacter* H = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
		UDinkStorySubsystem* Story = W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		if (!H || !Story || Story->bNewGamePending) return false;
		UDinkGreyboxSubsystem* Grey = W->GetSubsystem<UDinkGreyboxSubsystem>();
		UDinkDirector* D = Story->GetDirector();
		UDinkGameplay* G = Story->GetGameplay();
		const double Now = W->GetTimeSeconds();
		const double Since = Now - At;
		const FDinkSprite& Me = D->GetDink();
		auto Unfreeze = [&]() { FDinkScriptInstance Caller; D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> unfreeze 1"), {TEXT("cmd")})); };
		if (Phase == 0)
		{
			Story->ResetRuntime();
			Unfreeze();
			G->bBrainsEnabled = false;
			const FDinkPhysicalPlaySettings& S = G->GetPhysicalPlaySettings();
			Test->TestTrue(TEXT("the game's relaxed list trims S713_P06 (A71) and has joints on SCR_713"),
				S.Trimmed.Contains(713006) && S.Joints.Contains(713) && S.Joints[713].Num() >= 1);
			FDinkPhysicalPlaySettings P;
			Test->TestTrue(TEXT("joints parse"), P.ParseRelaxed(TEXT("{\"screens\": {\"5\": [2]}, \"joints\": {\"5\": [[1, 2, 3, 4], [5, 6, 7, 8]]}}")));
			Test->TestTrue(TEXT("joint rects read inclusive"), P.Joints.Contains(5) && P.Joints[5].Num() == 2 && P.Joints[5][1] == FIntRect(5, 6, 7, 8));
			At = Now; Phase = 1; return false;
		}
		// layer off (Mode 0), then on (Mode 2): enter SCR_713 by way of SCR_407 (the layer's collision is applied at a screen entry)
		if (Phase == 1 || Phase == 10) { SetLayer(Phase == 1 ? 0 : 2); Grey->GotoScreen(407, 300, 200); At = Now; ++Phase; return false; }
		if (Phase == 2 || Phase == 11) { if (Since < 1.0) return false; Grey->GotoScreen(713, 200, 262); At = Now; ++Phase; return false; }
		if (Phase == 3 || Phase == 12)
		{
			if (Since < 1.5) return false;
			const bool bOn = Phase == 12;
			const TCHAR* Layer = bOn ? TEXT("on") : TEXT("off");
			// get_hard (engine x = map x + 20): P06's strip, P06's box south of it, the slot's west part, the plug, P13's box north of its strip
			struct FProbe { int32 X, Y; bool bSolidOn; const TCHAR* What; };
			const FProbe Probes[] = {
				{ 200, 210, true, TEXT("P06's drawn strip") }, { 200, 240, false, TEXT("P06's box south of its strip") },
				{ 200, 195, false, TEXT("P06's box north of its strip") }, { 250, 210, true, TEXT("P06's drawn end over P13's box (joint)") },
				{ 258, 217, true, TEXT("the plug across the slot (joint)") }, { 250, 217, false, TEXT("the slot's west part") },
				{ 300, 225, true, TEXT("P13's drawn strip") }, { 300, 200, false, TEXT("P13's box north of its strip") },
			};
			for (const FProbe& P : Probes)
			{
				const int32 Hard = G->GetHard(713, P.X + 20, P.Y);
				const bool bWant = !bOn || P.bSolidOn;
				Test->TestEqual(FString::Printf(TEXT("SCR_713 (layer %s) get_hard at %d,%d (%s) is %s"), Layer, P.X, P.Y, P.What, bWant ? TEXT("solid") : TEXT("0")), Hard != 0, bWant);
			}
			// the capsule: nothing joins the wall's south side to its north side inside the two boxes (x 145-370, y 190-251)
			const TArray<bool> Cells = DecodeMask(DinkWalkAudit::WalkMask(*W, 713, 3));
			if (Test->TestTrue(FString::Printf(TEXT("SCR_713 (layer %s): walk mask whole"), Layer), Cells.Num() >= 200 * 133))
			{
				const bool bSouthFree = Cells[(240 / 3) * 200 + 200 / 3], bNorthFree = Cells[(196 / 3) * 200 + 300 / 3];
				const bool bJoined = ReachesInside(Cells, 200, 240, 300, 196, 145, 370, 190, 251);
				Test->AddInfo(FString::Printf(TEXT("SCR_713 (layer %s): south of P06 (200,240) %s, north of P13 (300,196) %s, joined inside the boxes: %s"),
					Layer, bSouthFree ? TEXT("free") : TEXT("blocked"), bNorthFree ? TEXT("free") : TEXT("blocked"), bJoined ? TEXT("YES") : TEXT("no")));
				Test->TestFalse(FString::Printf(TEXT("SCR_713 (layer %s): no capsule path through the walls' boxes from the south side to the north"), Layer), bJoined);
				if (bOn) Test->TestTrue(TEXT("SCR_713 (layer on): Dink may stand in P06's box south of its drawn strip and in P13's north of its own"), bSouthFree && bNorthFree);
			}
			Unfreeze();
			At = Now; ++Phase; return false;
		}
		if (Phase == 4 || Phase == 13)
		{
			// a walk from the south at x 200 towards the north: the layer on stops him at P06's drawn face (y 213), off at the box (y 251)
			if (const ADinkScreenVolume* V = Grey->FindScreen(713)) H->AddMovementInput((V->MapPixelToWorld(200, 170) - V->MapPixelToWorld(200, 262)).GetSafeNormal2D());
			if (Since < 5.0) return false;
			const bool bOn = Phase == 13;
			const ADinkScreenVolume* V = Grey->FindScreen(713);
			const double Cm = V ? FVector::Dist2D(V->MapPixelToWorld(300, 200), V->MapPixelToWorld(400, 200)) / 100.0 : 0.0;
			const double RadiusPx = Cm > 0 ? H->GetCapsuleComponent()->GetScaledCapsuleRadius() / Cm : 0.0;
			double Face = 213;
			if (const FIntRect* F = G->GetPhysicalPlaySettings().Feet.Find(713006); bOn && F)
			{
				// the strip the layer measured on P06's own wall modules at entry (not P13's, whose box overlaps P06's)
				Test->AddInfo(FString::Printf(TEXT("SCR_713 P06 strip measured at entry: y %d-%d (audit 206-213)"), F->Min.Y, F->Max.Y));
				Test->TestTrue(TEXT("SCR_713 P06 (layer on): the measured strip is P06's drawn wall, not both walls"), F->Max.Y <= 217 && F->Min.Y >= 202);
				if (const FIntRect* F13 = G->GetPhysicalPlaySettings().Feet.Find(713013))
				{
					Test->AddInfo(FString::Printf(TEXT("SCR_713 P13 strip measured at entry: y %d-%d (audit 222-229)"), F13->Min.Y, F13->Max.Y));
					Test->TestTrue(TEXT("SCR_713 P13 (layer on): the measured strip is P13's drawn wall"), F13->Min.Y >= 218 && F13->Max.Y <= 233);
				}
				Face = F->Max.Y;
			}
			const double GapCm = (Me.Y - Face - RadiusPx) * Cm;
			Test->AddInfo(FString::Printf(TEXT("SCR_713 P06 from the south (layer %s): stopped at screen %d (%.0f,%.0f), body front %.0f cm from the drawn face (y %.0f)"),
				bOn ? TEXT("on") : TEXT("off"), Me.Screen, Me.X - 20, Me.Y, GapCm, Face));
			if (bOn)
			{
				Test->TestTrue(FString::Printf(TEXT("SCR_713 P06 (layer on): Dink walks up to the drawn wall (gap %.0f cm <= 40)"), GapCm), Me.Screen == 713 && GapCm <= 40.0);
				Test->TestTrue(FString::Printf(TEXT("SCR_713 P06 (layer on): and not through it (gap %.0f cm >= -40)"), GapCm), GapCm >= -40.0);
			}
			else Test->TestTrue(TEXT("SCR_713 P06 (layer off): the 1997 box stops him south of it (y > 251)"), Me.Screen == 713 && Me.Y > 251.0);
			At = Now; Phase = bOn ? 99 : 10; return false;
		}
		SetLayer(-1);
		return true;
	}
	FAutomationTestBase* Test;
	double Began = 0, At = 0;
	int32 Phase = 0;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWallJointsTest, "Dink.PhysicalPlay.WallJoints", DINK_TEST_FLAGS)
bool FDinkWallJointsTest::RunTest(const FString&)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!TestNotNull(TEXT("real map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	AddCommand(new FStartPIECommand(false)); AddCommand(new FDinkWallJointsPIE(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
