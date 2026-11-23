// Dink.PhysicalPlay.Blockages: invisible blockages of the 20 Nov 2026 playtest (~/Repos/Dink-Smallwood/Playtest_20Nov2026), in the
// real generated world (PIE), layer on. P1: the painted boulders of the grass_rocky tiles keep a 1997 hardness outline where the
// remaster draws open ground; on SCR_408 Dink stopped dead in open ground near (208,239), and walking east into SCR_409 at y 289 put
// him inside a closed invisible ring (x 4-62, y 280-334). With part Collision on (open tiles of relaxed_hardboxes.json) neither
// stops him. P2 / A54: the room dressing's WickerBasket stood 70 cm south of the feed sack; walking north from (448,200) now takes
// the sack. A66: the mother is talked to from in front of her.
#include "DinkTestHelpers.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkFactSubsystem.h"
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
class FDinkPhysicalPlayBlockagesPIE : public IAutomationLatentCommand
{
public:
	explicit FDinkPhysicalPlayBlockagesPIE(FAutomationTestBase* T) : Test(T) {}
	~FDinkPhysicalPlayBlockagesPIE()
	{
		if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.PhysicalPlay"))) V->Set(-1, ECVF_SetByConsole);
	}
	bool Update() override
	{
		if (!Began) Began = FPlatformTime::Seconds();
		if (FPlatformTime::Seconds() - Began > 420) { Test->AddError(TEXT("blockages PIE timeout")); return true; }
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
		auto Walk = [&](int32 Screen, double Fx, double Fy, double Tx, double Ty)
		{
			if (const ADinkScreenVolume* V = Grey->FindScreen(Screen)) H->AddMovementInput((V->MapPixelToWorld(Tx, Ty) - V->MapPixelToWorld(Fx, Fy)).GetSafeNormal2D());
		};
		const FDinkSprite& Me = D->GetDink();
		if (Phase == 0)
		{
			FDinkScriptInstance Caller;
			Story->ResetRuntime();
			D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> unfreeze 1"), {TEXT("cmd")}));
			if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.PhysicalPlay"))) V->Set(2, ECVF_SetByConsole);
			G->bBrainsEnabled = false;
			Test->AddInfo(FString::Printf(TEXT("hardness with the layer on: SCR_408 (208,239) %d, SCR_409 (30,289) %d"),
				G->GetHard(408, 208 + 20, 239), G->GetHard(409, 30 + 20, 289)));
			Grey->GotoScreen(407, 300, 200);
			Next(1); return false;
		}
		// ---- P1, SCR_408: walk east along y 239 from x 150 (through the spot where Dink stopped dead in open ground)
		if (Phase == 1) { if (Since < 1.0) return false; Grey->GotoScreen(408, 150, 239); Next(2); return false; }
		if (Phase == 2) { if (Since < 1.5) return false; Next(3); return false; }
		if (Phase == 3)
		{
			Walk(408, 150, 239, 300, 239);
			if (Me.Screen == 408) MaxX408 = FMath::Max(MaxX408, Me.X - 20);
			if (Since < 3.0) return false;
			Test->AddInfo(FString::Printf(TEXT("P1 SCR_408: walked east from x 150 to x %.0f (y %.0f), screen %d, farthest on SCR_408 x %.0f"), Me.X - 20, Me.Y, Me.Screen, MaxX408));
			// (review of 22 Nov 2026, finding 6: on SCR_408 itself, not "anywhere but SCR_408")
			Test->TestTrue(TEXT("P1: on SCR_408 Dink walks past (208,239) (no invisible wall in open ground)"), MaxX408 > 240);
			Grey->GotoScreen(408, 540, 289);
			Next(4); return false;
		}
		// ---- P1, SCR_408 -> SCR_409 at y 289: across the screen edge and on east, out of the old invisible ring (x 4-62)
		if (Phase == 4) { if (Since < 1.5) return false; Next(5); return false; }
		if (Phase == 5)
		{
			Walk(Me.Screen, 0, Me.Y, 600, Me.Y);
			if (Since < 6.0) return false;
			Test->AddInfo(FString::Printf(TEXT("P1 408 -> 409: Dink at screen %d x %.0f y %.0f"), Me.Screen, Me.X - 20, Me.Y));
			Test->TestTrue(TEXT("P1: walking east from SCR_408 at y 289 Dink crosses into SCR_409 and past the old ring (x > 70)"), Me.Screen == 409 && Me.X - 20 > 70);
			// after the new game's first scene (&story 1: feed the pigs), so the house holds no cut-scene
			Story->GetFacts()->SetFact(TEXT("story"), 1);
			G->bBrainsEnabled = true; // Dink's touches run with the brains
			Grey->GotoScreen(1, 448, 200);
			Next(6); return false;
		}
		// ---- P2 / A54, SCR_001: north from (448,200) to the feed sack (448,130)
		if (Phase == 6)
		{
			if (Since < 1.5) return false;
			FDinkScriptInstance Caller;
			D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> unfreeze 1"), {TEXT("cmd")}));
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				if (Pair.Value.Origin.IsValid() && Pair.Value.Origin.Screen == 1 && Pair.Value.Origin.Placement == 52) Sack = Pair.Key;
				if (Pair.Value.Origin.IsValid() && Pair.Value.Origin.Screen == 1 && Pair.Value.Origin.Placement == 26) Mother = Pair.Key;
			}
			Test->AddInfo(FString::Printf(TEXT("SCR_001: feed sack sprite %d, mother sprite %d"), Sack, Mother));
			Next(7); return false;
		}
		if (Phase == 7)
		{
			Walk(1, 448, 200, 448, 100);
			const FDinkSprite* S = Sack ? D->FindSprite(Sack) : nullptr;
			// s1-sack's touch: sp_touch_damage 0, brain 12 (it shrinks away), the feed in Dink's items
			const bool bTaken = Sack != 0 && (!S || !S->bActive || S->GetProp(TEXT("touch_damage")) != -1);
			if (!bTaken && Since < 4.0) return false;
			Test->AddInfo(FString::Printf(TEXT("P2: walking north from (448,200): Dink at (%.0f,%.0f), sack %s"), Me.X - 20, Me.Y, bTaken ? TEXT("taken") : TEXT("still there")));
			Test->TestTrue(TEXT("P2 / A54: walking north from (448,200) Dink takes the feed sack"), bTaken);
			G->bBrainsEnabled = false; // the mother (brain 16) stands still to be talked to
			const FDinkSprite* M0 = Mother ? D->FindSprite(Mother) : nullptr;
			MotherX = M0 ? M0->X - 20 : 183; MotherY = M0 ? M0->Y : 240;
			Grey->GotoScreen(1, 300, 200);
			Next(8); return false;
		}
		// ---- A66, SCR_001: the mother, from the east, facing her (walking up to her)
		if (Phase == 8)
		{
			if (Since < 1.5) return false;
			FDinkScriptInstance Caller;
			D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> unfreeze 1"), {TEXT("cmd")}));
			const FDinkSprite* M0 = Mother ? D->FindSprite(Mother) : nullptr;
			if (M0 && M0->Actor.IsValid())
			{
				const FVector East = (Grey->FindScreen(1)->MapPixelToWorld(300, 200) - Grey->FindScreen(1)->MapPixelToWorld(200, 200)).GetSafeNormal2D();
				MotherAt = M0->Actor->GetActorLocation();
				const FVector From = MotherAt + East * 160.0;
				H->SetActorLocation(FVector(From.X, From.Y, H->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
				H->SetActorRotation(FRotator(0, (-East).Rotation().Yaw, 0));
			}
			Next(9); return false;
		}
		if (Phase == 9)
		{
			H->AddMovementInput((MotherAt - H->GetActorLocation()).GetSafeNormal2D());
			if (Since < 2.0) return false;
			const FDinkSprite* M = Mother ? D->FindSprite(Mother) : nullptr;
			FHitResult Block;
			const FVector West = (Grey->FindScreen(1)->MapPixelToWorld(150, 240) - Grey->FindScreen(1)->MapPixelToWorld(240, 240)).GetSafeNormal2D();
			const UCapsuleComponent* Capsule = H->GetCapsuleComponent();
			FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkA66), false, H);
			W->SweepSingleByChannel(Block, H->GetActorLocation(), H->GetActorLocation() + West * 30.0, H->GetActorQuat(), ECC_Pawn, Capsule->GetCollisionShape(), Params);
			const FString What = Block.bBlockingHit && Block.GetComponent() ? FString::Printf(TEXT("%s of %s"), *Block.GetComponent()->GetName(), *GetNameSafe(Block.GetActor())) : FString(TEXT("nothing"));
			Test->AddInfo(FString::Printf(TEXT("A66: Dink stopped at (%.0f,%.0f) facing west, %.0f cm from her actor; mother at (%.0f,%.0f); what stops him: %s"),
				Me.X - 20, Me.Y, FVector::Dist2D(H->GetActorLocation(), MotherAt), M ? M->X - 20 : -1.0, M ? M->Y : -1.0, *What));
			const int32 Target = G->FindTalkTarget(1);
			const FDinkSprite* Found = Target ? D->FindSprite(Target) : nullptr;
			Test->AddInfo(FString::Printf(TEXT("A66: the talk rule finds sprite %d (%s %s)"), Target, Found ? *Found->Script.ToString() : TEXT("-"), Found ? *Found->Origin.ToString() : TEXT("-")));
			Test->TestTrue(TEXT("A66: facing the mother from in front of her, Dink talks to her"), Mother != 0 && Target == Mother);
			Test->TestTrue(TEXT("A66: the talk key starts her talk"), Story->TryTalk(H));
			Next(10); return false;
		}
		// ---- Review of PR #160, 22 Nov 2026, finding 1: pickups the layer-on bot could not reach. Each is walked at from two sides
		// (map pixels); it must be collected (its touch ran: gone, or its touch_damage no longer -1).
		struct FPickup { int32 Screen, Placement; double Fx, Fy, Tx, Ty, Gx, Gy, Hx, Hy; const TCHAR* Name; };
		static const FPickup Pickups[] = {
			{ 166, 23, 300, 197, 350, 197, 350, 250, 350, 197, TEXT("bpotion S166_P23 (7 px from the decoration S166_P17)") },
			{ 157, 9, 197, 161, 247, 161, 247, 215, 247, 161, TEXT("gheart S157_P09 (beside S157_P04)") },
		};
		if (Phase >= 10 && Phase < 10 + 4 * int32(UE_ARRAY_COUNT(Pickups)))
		{
			const FPickup& Pk = Pickups[(Phase - 10) / 4];
			const int32 Sub = (Phase - 10) % 4; // 0 go to side 1, 1 walk, 2 go to side 2, 3 walk
			const auto Find = [&]() { for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites()) if (Pair.Value.Origin.IsValid() && Pair.Value.Origin.Screen == Pk.Screen && Pair.Value.Origin.Placement == Pk.Placement) return Pair.Key; return 0; };
			if (Sub == 0 || Sub == 2)
			{
				if (!bWent)
				{
					bWent = true;
					G->bBrainsEnabled = true; // Dink's touches run with the brains
					Grey->GotoScreen(Pk.Screen, Sub == 0 ? Pk.Fx : Pk.Gx, Sub == 0 ? Pk.Fy : Pk.Gy);
					return false;
				}
				if (Since < 1.5) return false;
				bWent = false;
				// the foes of the room (SCR_157's slayers) are taken away: only the walk to the pickup is tested
				for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
					if (Pair.Key != 1 && Pair.Value.bActive && Pair.Value.Screen == Pk.Screen && Pair.Value.GetProp(TEXT("hitpoints")) > 0) D->DeactivateSprite(Pair.Key, 0, false);
				FDinkScriptInstance Caller;
				D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> unfreeze 1"), {TEXT("cmd")}));
				PickupSprite = Find();
				const FDinkSprite* P0 = PickupSprite ? D->FindSprite(PickupSprite) : nullptr;
				Test->AddInfo(FString::Printf(TEXT("%s: sprite %d active %d at (%.0f,%.0f) touch %d"), Pk.Name, PickupSprite, P0 && P0->bActive, P0 ? P0->X : 0.0, P0 ? P0->Y : 0.0, P0 ? P0->GetProp(TEXT("touch_damage")) : 0));
				Next(Phase + 1); return false;
			}
			const FDinkSprite* P = PickupSprite ? D->FindSprite(PickupSprite) : nullptr;
			const bool bTaken = PickupSprite != 0 && (!P || !P->bActive || P->GetProp(TEXT("touch_damage")) != -1);
			if (Sub == 1) Walk(Pk.Screen, Pk.Fx, Pk.Fy, Pk.Tx, Pk.Ty); else Walk(Pk.Screen, Pk.Gx, Pk.Gy, Pk.Hx, Pk.Hy);
			if (!bTaken && Since < 4.0) return false;
			Test->AddInfo(FString::Printf(TEXT("%s, side %d: Dink at (%.0f,%.0f) screen %d, %s"), Pk.Name, Sub == 1 ? 1 : 2, Me.X - 20, Me.Y, Me.Screen, bTaken ? TEXT("collected") : TEXT("still there")));
			if (bTaken) { Test->TestTrue(FString::Printf(TEXT("finding 1: walking at %s, Dink collects it"), Pk.Name), true); Next((Phase - 10) / 4 * 4 + 14); return false; }
			if (Sub == 3) Test->TestTrue(FString::Printf(TEXT("finding 1: walking at %s, Dink collects it"), Pk.Name), false);
			Next(Phase + 1); return false;
		}
		return true;
	}
	FAutomationTestBase* Test;
	double Began = 0, At = 0;
	int32 Phase = 0, Sack = 0, Mother = 0, PickupSprite = 0;
	double MaxX408 = -1.0;
	bool bWent = false;
	double MotherX = 0, MotherY = 0;
	FVector MotherAt = FVector::ZeroVector;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicalPlayBlockagesTest, "Dink.PhysicalPlay.Blockages", DINK_TEST_FLAGS)
bool FDinkPhysicalPlayBlockagesTest::RunTest(const FString&)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!TestNotNull(TEXT("real map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	AddCommand(new FStartPIECommand(false)); AddCommand(new FDinkPhysicalPlayBlockagesPIE(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
