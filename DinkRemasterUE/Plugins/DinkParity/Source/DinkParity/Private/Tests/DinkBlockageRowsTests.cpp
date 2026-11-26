// Dink.PhysicalPlay.BlockageRows (23 Nov 2026): the invisible-blockage rows of doc/remaster/ALPHA_BUG_LIST.md and the 20 Nov playtest,
// walked in the real generated world (PIE). A71: interior and dungeon walls whose drawn strip stands inside a thick 1997 wall box
// (relaxed_hardboxes.json "trimmed"): with part Collision on Dink walks up to the drawn wall. A92: painted low rocks with nothing drawn
// (audit tiles opened by Scripts/make_relaxed_hardboxes.py). A20: a teleport onto SCR_471's authored pond lands on the meadow beside it instead
// of falling without end. P8: walking at the seated King of the ending, Dink's capsule stays out of his drawn body (layer on).
// A62, A61: the camera measured and logged (Info lines "A62", "A61"). A93 and A94 are measured offline (Docs/Verification/Blockages_23Nov2026).
#include "DinkTestHelpers.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkFactSubsystem.h"
#include "DinkCreatureSubsystem.h"
#include "DinkCreatureClassComponent.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
// One walk: teleport to (Fx, Fy) on Screen with the layer in Mode (0 off, 2 on), walk towards (Tx, Ty) for Seconds, then Check.
enum class EWalkCheck : uint8 { WallFace, PassX, ShoreY, None };
struct FBlockWalk
{
	const TCHAR* Row; int32 Screen; double Fx, Fy, Tx, Ty; int32 Mode; double Seconds; EWalkCheck Check;
	double Edge; // WallFace / ShoreY: the drawn edge's map y; PassX: the x Dink must pass
	int32 Sign;  // WallFace / ShoreY: +1 the edge is south of Dink (he walks south), -1 north
	double MaxGapCm;
	int32 Placement = 0; // screen * 1000 + placement of a trimmed wall
};
const FBlockWalk Walks[] = {
	// A71 (relaxed_hardboxes.json "trimmed"; box and drawn strip from the dink.PhysAudit run of 15 Nov 2026, SCR_713 from the 25 Nov run at the enlarged scale)
	{ TEXT("A71 S003_P01 plaster corner post, box y 152-207, drawn y 202-206, from the north"), 3, 350, 140, 350, 230, 0, 4.0, EWalkCheck::WallFace, 202, 1, 0, 3001 },
	{ TEXT("A71 S003_P01 plaster corner post, box y 152-207, drawn y 202-206, from the north"), 3, 350, 140, 350, 230, 2, 4.0, EWalkCheck::WallFace, 202, 1, 40, 3001 },
	{ TEXT("A71 S003_P19 plaster door jamb, box y 152-207, drawn y 177-181, from the south"), 3, 423, 216, 423, 150, 0, 4.0, EWalkCheck::WallFace, 181, -1, 0, 3019 },
	{ TEXT("A71 S003_P19 plaster door jamb, box y 152-207, drawn y 177-181, from the south"), 3, 423, 216, 423, 150, 2, 4.0, EWalkCheck::WallFace, 181, -1, 40, 3019 },
	{ TEXT("A71 S577_P09 dungeon wall, box y 33-94, drawn y 78-93, from the north"), 577, 341, 22, 341, 110, 0, 4.0, EWalkCheck::WallFace, 78, 1, 0, 577009 },
	{ TEXT("A71 S577_P09 dungeon wall, box y 33-94, drawn y 78-93, from the north"), 577, 341, 22, 341, 110, 2, 4.0, EWalkCheck::WallFace, 78, 1, 0, 577009 },
	// SCR_713 (world scale on, 25 Nov 2026): P06's drawn strip (y 206-213) and P13's (y 222-229) are staggered; since 26 Nov P06 is trimmed
	// too, with a joint closing the slot between them (Dink.PhysicalPlay.WallJoints); P07 beside it is trimmed
	{ TEXT("A71 S713_P07 dungeon wall, box y 190-251, drawn y 205-212, from the south"), 713, 108, 258, 108, 170, 0, 5.0, EWalkCheck::WallFace, 212, -1, 0, 713007 },
	{ TEXT("A71 S713_P07 dungeon wall, box y 190-251, drawn y 205-212, from the south"), 713, 108, 258, 108, 170, 2, 5.0, EWalkCheck::WallFace, 212, -1, 40, 713007 },
	// A92 (painted low rocks, nothing drawn: audit tiles opened)
	{ TEXT("A92 SCR_126 low rock x 365-426 at y 253, walked east"), 126, 325, 253, 480, 253, 0, 4.0, EWalkCheck::PassX, 426, 0, 0 },
	{ TEXT("A92 SCR_126 low rock x 365-426 at y 253, walked east"), 126, 325, 253, 480, 253, 2, 4.0, EWalkCheck::PassX, 426, 0, 0 },
	// P8 (the seated King of the ending, S070_P03 at (333,192), 1997 box x 279-388, y 156-203), walked at from the south
	{ TEXT("P8 SCR_070 the King, from the south"), 70, 333, 280, 333, 150, 0, 4.0, EWalkCheck::None, 0, 0, 0 },
	{ TEXT("P8 SCR_070 the King, from the south"), 70, 333, 280, 333, 150, 2, 4.0, EWalkCheck::None, 0, 0, 0 },
	// A62 (camera in the north-east corner of Dink's house, by the feed sack)
	{ TEXT("A62 SCR_001 north-east corner by the sack"), 1, 440, 150, 520, 90, 2, 3.0, EWalkCheck::None, 0, 0, 0 },
	{ TEXT("A62 SCR_001 room centre (comparison)"), 1, 300, 260, 300, 250, 2, 1.0, EWalkCheck::None, 0, 0, 0 },
};

class FDinkBlockageRowsPIE : public IAutomationLatentCommand
{
public:
	explicit FDinkBlockageRowsPIE(FAutomationTestBase* T) : Test(T) {}
	~FDinkBlockageRowsPIE()
	{
		if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.PhysicalPlay"))) V->Set(-1, ECVF_SetByConsole);
		if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.CreatureClassArt")); V && ClassArt != INDEX_NONE) V->Set(ClassArt, ECVF_SetByConsole);
	}
	static void SetLayer(int32 Mode)
	{
		if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.PhysicalPlay"))) V->Set(Mode, ECVF_SetByConsole);
	}
	FString CameraReport(UWorld* W, ADinkGreyboxCharacter* H) const
	{
		const FVector Cam = H->FollowCamera ? H->FollowCamera->GetComponentLocation() : FVector::ZeroVector;
		const FVector Head = H->GetActorLocation() + FVector(0, 0, 60);
		FHitResult Hit;
		FCollisionQueryParams P(SCENE_QUERY_STAT(DinkBlockRowsCam), true, H);
		const bool bHit = W->LineTraceSingleByChannel(Hit, Cam, Head, ECC_Camera, P);
		return FString::Printf(TEXT("camera %.0f cm from Dink's head (arm %.0f of %.0f), sight to his head %s"), FVector::Dist(Cam, Head),
			H->CameraBoom ? FVector::Dist(H->CameraBoom->GetComponentLocation(), Cam) : -1.0, H->CameraBoom ? H->CameraBoom->TargetArmLength : -1.f,
			bHit && Hit.GetComponent() ? *FString::Printf(TEXT("blocked %.0f cm from the camera by %s of %s"), Hit.Distance, *Hit.GetComponent()->GetName(), *GetNameSafe(Hit.GetActor())) : TEXT("clear"));
	}
	bool Update() override
	{
		if (!Began) Began = FPlatformTime::Seconds();
		if (FPlatformTime::Seconds() - Began > 600) { Test->AddError(TEXT("blockage rows PIE timeout")); return true; }
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
		auto Next = [&](int32 P) { Phase = P; At = Now; };
		const FDinkSprite& Me = D->GetDink();
		auto CmPerPx = [&](int32 Screen) { const ADinkScreenVolume* V = Grey->FindScreen(Screen); return V ? FVector::Dist2D(V->MapPixelToWorld(300, 200), V->MapPixelToWorld(400, 200)) / 100.0 : 0.0; };
		auto Unfreeze = [&]() { FDinkScriptInstance Caller; D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> unfreeze 1"), {TEXT("cmd")})); };
		if (Phase == 0)
		{
			Story->ResetRuntime();
			Unfreeze();
			G->bBrainsEnabled = false;
			// A20: a teleport onto SCR_471's pond (no floor under map pixel 300,200)
			Grey->GotoScreen(471, 300, 200);
			Next(1); return false;
		}
		if (Phase == 1)
		{
			if (Since < 2.0) return false;
			const ADinkScreenVolume* V = Grey->FindScreen(471);
			const double Level = V ? V->MapPixelToWorld(300, 200).Z : 0.0;
			const double Z = H->GetActorLocation().Z - H->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
			Test->AddInfo(FString::Printf(TEXT("A20: after dink.Goto 471 300 200 Dink stands at screen %d (%.0f,%.0f), feet %.0f cm from the screen's level"), Me.Screen, Me.X - 20, Me.Y, Z - Level));
			Test->TestTrue(TEXT("A20: a teleport onto SCR_471's pond does not fall: Dink stands on SCR_471 within 2 m of its level"), Me.Screen == 471 && FMath::Abs(Z - Level) < 200.0);
			Next(10); return false;
		}
		// ---- the walks
		const int32 NumWalks = UE_ARRAY_COUNT(Walks);
		if (Phase >= 10 && Phase < 10 + 2 * NumWalks)
		{
			const FBlockWalk& Wk = Walks[(Phase - 10) / 2];
			if ((Phase - 10) % 2 == 0)
			{
				// by way of another screen: the layer's collision is applied at a screen entry
				if (Hop == 0) { Hop = 1; SetLayer(Wk.Mode); Grey->GotoScreen(Wk.Screen == 407 ? 408 : 407, 300, 200); At = Now; return false; }
				if (Hop == 1) { if (Since < 1.0) return false; Hop = 2; Grey->GotoScreen(Wk.Screen, Wk.Fx, Wk.Fy); MaxX = -1; At = Now; return false; }
				if (Since < 1.5) return false;
				Hop = 0;
				// foes are taken away (brains are off): only the walk is tested
				for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
					if (Pair.Key != 1 && Pair.Value.bActive && Pair.Value.Screen == Wk.Screen && Pair.Value.GetProp(TEXT("hitpoints")) > 0 && Pair.Value.GetProp(TEXT("brain")) != 0) D->DeactivateSprite(Pair.Key, 0, false);
				Unfreeze();
				Test->AddInfo(FString::Printf(TEXT("%s (layer %s): start screen %d (%.0f,%.0f)"), Wk.Row, Wk.Mode ? TEXT("on") : TEXT("off"), Me.Screen, Me.X - 20, Me.Y));
				Next(Phase + 1); return false;
			}
			if (const ADinkScreenVolume* V = Grey->FindScreen(Wk.Screen)) H->AddMovementInput((V->MapPixelToWorld(Wk.Tx, Wk.Ty) - V->MapPixelToWorld(Wk.Fx, Wk.Fy)).GetSafeNormal2D());
			if (Me.Screen == Wk.Screen && FMath::Abs(Me.Y - Wk.Fy) <= 8.0) MaxX = FMath::Max(MaxX, Me.X - 20);
			if (Since < Wk.Seconds) return false;
			const double Cm = CmPerPx(Wk.Screen);
			const double RadiusPx = Cm > 0 ? H->GetCapsuleComponent()->GetScaledCapsuleRadius() / Cm : 0;
			const TCHAR* Layer = Wk.Mode ? TEXT("on") : TEXT("off");
			if (Wk.Check == EWalkCheck::WallFace || Wk.Check == EWalkCheck::ShoreY)
			{
				// gap between Dink's body front and the drawn edge (cm); negative: his body is past it. Layer on: the strip the layer
				// measured on the wall mesh at entry (MeasureWallStrip), else the 15 Nov audit's
				double Edge = Wk.Edge;
				if (Wk.Mode && Wk.Placement)
					if (const FIntRect* F = G->GetPhysicalPlaySettings().Feet.Find(Wk.Placement)) Edge = Wk.Sign > 0 ? F->Min.Y : F->Max.Y;
				const double GapCm = (Wk.Sign * (Edge - Me.Y) - RadiusPx) * Cm;
				if (Edge != Wk.Edge) Test->AddInfo(FString::Printf(TEXT("%s: the wall strip measured at entry faces Dink at y %.0f (audit %.0f)"), Wk.Row, Edge, Wk.Edge));
				Test->AddInfo(FString::Printf(TEXT("%s (layer %s): stopped at screen %d (%.0f,%.0f); body front %.0f cm from the drawn edge"), Wk.Row, Layer, Me.Screen, Me.X - 20, Me.Y, GapCm));
				if (Wk.MaxGapCm > 0)
				{
					Test->TestTrue(FString::Printf(TEXT("%s (layer %s): Dink walks up to the drawn edge (gap %.0f cm <= %.0f)"), Wk.Row, Layer, GapCm, Wk.MaxGapCm), Me.Screen == Wk.Screen && GapCm <= Wk.MaxGapCm);
					Test->TestTrue(FString::Printf(TEXT("%s (layer %s): and not through it (gap %.0f cm >= -40)"), Wk.Row, Layer, GapCm), GapCm >= -40.0);
				}
			}
			else if (Wk.Check == EWalkCheck::PassX)
			{
				Test->AddInfo(FString::Printf(TEXT("%s (layer %s): farthest x on its line %.0f (rock ends at %.0f), now screen %d (%.0f,%.0f)"), Wk.Row, Layer, MaxX, Wk.Edge, Me.Screen, Me.X - 20, Me.Y));
				if (Wk.Mode) Test->TestTrue(FString::Printf(TEXT("%s (layer on): Dink walks across the painted rock"), Wk.Row), MaxX > Wk.Edge);
			}
			else
			{
				FString Extra;
				if (Wk.Screen == 70)
				{
					for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
						if (Pair.Value.Origin.IsValid() && Pair.Value.Origin.Screen == 70 && Pair.Value.Origin.Placement == 3 && Pair.Value.Actor.IsValid())
						{
							const AActor* King = Pair.Value.Actor.Get();
							// his drawn body: the class-bound skinned King and throne (dink.CreatureClassArt 2 headless)
							const UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(King);
							const FBox KB = Body ? Body->Bounds.GetBox() : FBox(ForceInit);
							const FVector E = KB.IsValid ? KB.GetExtent() : FVector::ZeroVector;
							const FVector O = KB.IsValid ? KB.GetCenter() : FVector::ZeroVector;
							Extra = FString::Printf(TEXT("; King actor %.0f cm away, his drawn bounds %.0f x %.0f cm, Dink's capsule %s them (%.0f cm from the box)"),
								FVector::Dist2D(King->GetActorLocation(), H->GetActorLocation()), E.X * 2, E.Y * 2,
								KB.IsValid && KB.ExpandBy(H->GetCapsuleComponent()->GetScaledCapsuleRadius()).IsInsideXY(H->GetActorLocation()) ? TEXT("inside") : TEXT("outside"),
								KB.IsValid ? FMath::Sqrt(KB.ComputeSquaredDistanceToPoint(FVector(H->GetActorLocation().X, H->GetActorLocation().Y, O.Z))) : -1.0);
							Extra += TEXT("; ") + CameraReport(W, H);
							if (Wk.Mode) Test->TestFalse(TEXT("P8 (layer on): walking at the seated King Dink's capsule stays out of his drawn body"),
								KB.IsValid && KB.ExpandBy(H->GetCapsuleComponent()->GetScaledCapsuleRadius() - 5.0).IsInsideXY(H->GetActorLocation()));
							if (Wk.Mode) Test->TestTrue(TEXT("P8: the King is drawn by his class-bound body"), KB.IsValid != 0);
						}
				}
				else Extra = TEXT("; ") + CameraReport(W, H);
				Test->AddInfo(FString::Printf(TEXT("%s (layer %s): stopped at screen %d (%.0f,%.0f)%s"), Wk.Row, Layer, Me.Screen, Me.X - 20, Me.Y, *Extra));
			}
			Next(Phase + 1); return false;
		}
		// ---- A61: entering Ethel's house (SCR_409's door S409_P16 -> SCR_002 at 292,373): the camera's first frames
		const int32 P61 = 10 + 2 * NumWalks;
		if (Phase == P61) { SetLayer(2); Grey->GotoScreen(409, 368, 345); Next(P61 + 1); return false; }
		if (Phase == P61 + 1)
		{
			if (Since < 1.5) return false;
			Unfreeze();
			if (const ADinkScreenVolume* V = Grey->FindScreen(409)) H->AddMovementInput((V->MapPixelToWorld(368, 290) - V->MapPixelToWorld(368, 345)).GetSafeNormal2D());
			if (Me.Screen != 2 && Since < 5.0) return false;
			Test->AddInfo(FString::Printf(TEXT("A61: walking into Ethel's door: screen %d (%.0f,%.0f)"), Me.Screen, Me.X - 20, Me.Y));
			Next(P61 + 2); return false;
		}
		if (Phase == P61 + 2)
		{
			for (const double T : { 0.2, 0.6, 1.2, 2.5 })
				if (Since >= T && LastCam < T) { LastCam = T; Test->AddInfo(FString::Printf(TEXT("A61: %.1f s after the warp, screen %d (%.0f,%.0f): %s"), T, Me.Screen, Me.X - 20, Me.Y, *CameraReport(W, H))); }
			if (Since < 2.6) return false;
			Next(P61 + 3); return false;
		}
		// ---- the end: the console variables back
		if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.CreatureClassArt")); V && ClassArt != INDEX_NONE) V->Set(ClassArt, ECVF_SetByConsole);
		SetLayer(-1);
		return true;
	}
	FAutomationTestBase* Test;
	double Began = 0, At = 0, MaxX = -1, LastCam = -1;
	int32 Phase = 0, ClassArt = INDEX_NONE;
	int32 Hop = 0;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBlockageRowsTest, "Dink.PhysicalPlay.BlockageRows", DINK_TEST_FLAGS)
bool FDinkBlockageRowsTest::RunTest(const FString&)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!TestNotNull(TEXT("real map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	// class-bound bodies (the seated King of P8) drawn headless too, as in play; set before the play world starts (put back at the end)
	FDinkBlockageRowsPIE* Cmd = new FDinkBlockageRowsPIE(this);
	if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.CreatureClassArt"))) { Cmd->ClassArt = V->GetInt(); V->Set(2, ECVF_SetByConsole); }
	AddCommand(new FStartPIECommand(false)); AddCommand(Cmd); AddCommand(new FEndPlayMapCommand()); return true;
}
