// Dink.PhysicalPlay.SealedGaps (26 Nov 2026, world scale follow-up): 1997 walkable ground inside a hardness outline that Dink's capsule
// could not enter at the reference scale and fits at the enlarged scale (Content/Dink/Data/Play/sealed_gaps.json). SCR_189/190: an 8 px
// slit between two low rock lines (y 246-253), closed on every side (the thorn S189_P03 in the west, a low stub at x 200 of SCR_190 in the
// east): with the world scale on the 28 cm capsule fits it (9.0 cm/px) and the probe's chapter 17 teleport landed in it. Measured on the
// real generated world (PIE) with the walk audit's own capsule mask (DinkWalkAudit::WalkMask, 3 px cells): with part Collision on no cell
// of the slit is free and the open floor beside it is; get_hard is the 1997 code in both modes (the simulation does not change).
// Then every other sealed screen (the closed pockets of Scripts/check_capsule_gaps.py), layer on: no free capsule cell inside a sealed rect.
#include "DinkTestHelpers.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkWalkAudit.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
/** WalkMask's run-length text (<count><F|B>, 200 cells a row of 3 px) as one bool per cell, true = the capsule centre may stand. */
TArray<bool> DecodeWalkMask(const FString& Mask)
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

struct FSealCheck
{
	int32 Screen;
	int32 X0, X1;      // the slit's map x (inclusive)
	int32 OpenX, OpenY; // open floor near it (free in both modes)
	int32 EntryX, EntryY;
};
const FSealCheck Checks[] = {
	{ 190, 0, 199, 60, 280, 60, 280 },
	{ 189, 242, 599, 400, 280, 400, 280 },
};
constexpr int32 SlitY0 = 246, SlitY1 = 253;

class FDinkSealedGapsPIE : public IAutomationLatentCommand
{
public:
	explicit FDinkSealedGapsPIE(FAutomationTestBase* T) : Test(T) {}
	~FDinkSealedGapsPIE()
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
		if (FPlatformTime::Seconds() - Began > 900) { Test->AddError(TEXT("sealed gaps PIE timeout")); return true; }
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
		if (Phase == 0)
		{
			Story->ResetRuntime();
			G->bBrainsEnabled = false;
			const TArray<FIntRect>* R190 = G->GetPhysicalPlaySettings().Sealed.Find(190);
			const TArray<FIntRect>* R189 = G->GetPhysicalPlaySettings().Sealed.Find(189);
			Test->TestTrue(TEXT("the game's sealed_gaps.json loads with the SCR_189/190 slit"), R190 && R189 && R190->Num() > 0 && R189->Num() > 0);
			FDinkPhysicalPlaySettings S;
			Test->TestTrue(TEXT("sealed list parses"), S.ParseSealed(TEXT("{\"screens\": {\"7\": [{\"rect\": [1, 2, 3, 4], \"why\": \"x\"}], \"8\": []}}")));
			Test->TestTrue(TEXT("sealed rect read inclusive"), S.Sealed.Contains(7) && S.Sealed[7].Num() == 1 && S.Sealed[7][0] == FIntRect(1, 2, 3, 4));
			Test->TestFalse(TEXT("bad sealed json refused"), S.ParseSealed(TEXT("{")));
			At = Now; Phase = 1; return false;
		}
		// two modes (layer off, then on) x two screens; each entered by way of SCR_407 (the layer's collision is applied at a screen entry)
		const int32 Step = Phase - 1;
		if (Step < 4 * 3)
		{
			const int32 Mode = Step / 6 == 0 ? 0 : 2;
			const FSealCheck& C = Checks[(Step / 3) % 2];
			const int32 Part = Step % 3;
			if (Part == 0) { SetLayer(Mode); Grey->GotoScreen(407, 300, 200); At = Now; ++Phase; return false; }
			if (Part == 1) { if (Since < 1.0) return false; Grey->GotoScreen(C.Screen, C.EntryX, C.EntryY); At = Now; ++Phase; return false; }
			if (Since < 1.5) return false;
			const TCHAR* Layer = Mode ? TEXT("on") : TEXT("off");
			const TArray<bool> Cells = DecodeWalkMask(DinkWalkAudit::WalkMask(*W, C.Screen, 3));
			if (!Test->TestTrue(FString::Printf(TEXT("SCR_%03d (layer %s): Dink is on the screen and the walk mask is whole"), C.Screen, Layer),
				D->GetDink().Screen == C.Screen && Cells.Num() >= 200 * 133)) { ++Phase; return false; }
			int32 Free = 0, Tested = 0;
			for (int32 Cy = SlitY0 / 3; Cy <= SlitY1 / 3; ++Cy)
				for (int32 Cx = C.X0 / 3; Cx <= C.X1 / 3; ++Cx)
				{
					// cells whose centre lies inside the slit
					const double Px = Cx * 3 + 1.5, Py = Cy * 3 + 1.5;
					if (Px < C.X0 || Px > C.X1 + 1 || Py < SlitY0 || Py > SlitY1 + 1) continue;
					++Tested;
					Free += Cells[Cy * 200 + Cx];
				}
			const bool bOpen = Cells[(C.OpenY / 3) * 200 + C.OpenX / 3];
			const int32 Hard = G->GetHard(C.Screen, (C.X0 + C.X1) / 2 + 20, 249);
			Test->AddInfo(FString::Printf(TEXT("SCR_%03d (layer %s): %d of %d slit cells free for the capsule; open floor at %d,%d %s; get_hard in the slit %d"),
				C.Screen, Layer, Free, Tested, C.OpenX, C.OpenY, bOpen ? TEXT("free") : TEXT("blocked"), Hard));
			Test->TestTrue(FString::Printf(TEXT("SCR_%03d (layer %s): the open floor beside the slit stays free"), C.Screen, Layer), bOpen);
			Test->TestEqual(FString::Printf(TEXT("SCR_%03d (layer %s): get_hard in the slit is the 1997 code (0)"), C.Screen, Layer), Hard, 0);
			if (Mode) Test->TestEqual(FString::Printf(TEXT("SCR_%03d (layer on): no cell of the sealed slit is free for Dink's capsule"), C.Screen), Free, 0);
			else if (Free == 0) Test->AddInfo(FString::Printf(TEXT("SCR_%03d (layer off): the slit does not fit the capsule (reference-scale world?)"), C.Screen));
			++Phase; return false;
		}
		// a teleport into the slit with the layer on (the probe's chapter 17 spot): Dink does not stay inside the sealed gap
		if (Phase == 13) { SetLayer(2); Grey->GotoScreen(407, 300, 200); At = Now; ++Phase; return false; }
		if (Phase == 14) { if (Since < 1.0) return false; Grey->GotoScreen(190, 60, 250, /*bEvenIntoWalls*/ true); At = Now; ++Phase; return false; }
		if (Phase == 15)
		{
			if (Since < 2.0) return false;
			const FDinkSprite& Me = D->GetDink();
			Test->AddInfo(FString::Printf(TEXT("teleport to SCR_190 60,250 with the layer on: Dink at screen %d (%.0f,%.0f)"), Me.Screen, Me.X - 20, Me.Y));
			Test->TestFalse(TEXT("SCR_190 (layer on): a teleport into the sealed slit does not leave Dink in it"), Me.Screen == 190 && Me.Y >= 246 && Me.Y <= 253 && Me.X - 20 <= 199);
			++Phase; return false;
		}
		// ---- every sealed screen, layer on
		if (Others.IsEmpty() && !bOthersListed)
		{
			bOthersListed = true;
			for (const TPair<int32, TArray<FIntRect>>& Pair : G->GetPhysicalPlaySettings().Sealed) if (Pair.Key != 189 && Pair.Key != 190) Others.Add(Pair.Key);
			Others.Sort();
			Test->AddInfo(FString::Printf(TEXT("%d other sealed screens"), Others.Num()));
		}
		if (Other < Others.Num())
		{
			const int32 Screen = Others[Other];
			if (Sub == 0) { SetLayer(2); Grey->GotoScreen(Screen == 407 ? 408 : 407, 300, 200); At = Now; Sub = 1; return false; }
			if (Sub == 1)
			{
				if (Since < 1.0) return false;
				// any free spot of the screen (the teleport refuses a blocked one)
				static const FIntPoint Spots[] = { {300, 200}, {150, 100}, {450, 100}, {150, 300}, {450, 300}, {300, 60}, {300, 340}, {60, 200}, {540, 200}, {100, 380}, {500, 380}, {100, 20}, {500, 20} };
				bool bIn = false;
				for (const FIntPoint& P : Spots) if (Grey->GotoScreen(Screen, P.X, P.Y)) { bIn = true; break; }
				if (!bIn) bIn = Grey->GotoScreen(Screen, 300, 200, /*bEvenIntoWalls*/ true);
				if (!Test->TestTrue(FString::Printf(TEXT("SCR_%03d: Dink is set down on the screen"), Screen), bIn)) { ++Other; Sub = 0; return false; }
				At = Now; Sub = 2; return false;
			}
			if (Since < 1.5) return false;
			const TArray<bool> Cells = DecodeWalkMask(DinkWalkAudit::WalkMask(*W, Screen, 3));
			int32 Free = 0, Tested = 0;
			if (Cells.Num() >= 200 * 133)
				for (const FIntRect& R : G->GetPhysicalPlaySettings().Sealed[Screen])
					for (int32 Cy = R.Min.Y / 3; Cy <= R.Max.Y / 3; ++Cy)
						for (int32 Cx = R.Min.X / 3; Cx <= R.Max.X / 3; ++Cx)
						{
							const double Px = Cx * 3 + 1.5, Py = Cy * 3 + 1.5;
							if (Px < R.Min.X || Px > R.Max.X + 1 || Py < R.Min.Y || Py > R.Max.Y + 1) continue;
							++Tested;
							Free += Cells[Cy * 200 + Cx];
						}
			Test->AddInfo(FString::Printf(TEXT("SCR_%03d (layer on): %d of %d sealed cells free (Dink on screen %d)"), Screen, Free, Tested, D->GetDink().Screen));
			Test->TestEqual(FString::Printf(TEXT("SCR_%03d (layer on): no sealed cell is free for Dink's capsule"), Screen), Free, 0);
			++Other; Sub = 0; return false;
		}
		SetLayer(-1);
		return true;
	}
	FAutomationTestBase* Test;
	double Began = 0, At = 0;
	int32 Phase = 0, Other = 0, Sub = 0;
	bool bOthersListed = false;
	TArray<int32> Others;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkSealedGapsTest, "Dink.PhysicalPlay.SealedGaps", DINK_TEST_FLAGS)
bool FDinkSealedGapsTest::RunTest(const FString&)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!TestNotNull(TEXT("real map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	AddCommand(new FStartPIECommand(false)); AddCommand(new FDinkSealedGapsPIE(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
