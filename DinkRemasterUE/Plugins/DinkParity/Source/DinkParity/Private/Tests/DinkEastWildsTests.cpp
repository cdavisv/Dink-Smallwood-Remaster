// Dink.Gameplay.EastWilds.*: the cobbler's booth doorway, owner decision of 9 Nov 2026 (tools/analyse regions.toml [[join]]
// cobbler_booth_doorway; root AGENTS.md "Map connectivity facts").
//
// The 1997 data gives the East Wilds no designed entrance: its only door, S289_P19 (SCR_289, the booth's west room, warp to SCR_350 at engine
// 371,241), sits in a room nothing leads to. The remaster joins SCR_289 and SCR_290 (the booth's Koka room, entered by S734_P31 at engine 315,310)
// into one interior: the void tiles SCR_289 (11, 1-3) and (9-11, 4) and SCR_290 (0, 1-4) become floor, and the analysis cuts the passage into the
// hardness its greybox collision is baked from: map y 176-214 below the door on SCR_289 (the wall hardboxes S289_P11/P12 cut), y 125-214 of
// SCR_290's west wall (S290_P10 and the top of S290_P14 cut), 2 px jambs against the void (Scripts/export_import_bundle.py applies connectivity.json `designed_joins`). The parity layer's
// hardness (Content/Dink/Data/Gameplay/Hardness, hard.dat and map.dat) is the 1997 game's and keeps the walls: NPC brains still meet them.
//
// PIE on the generated world, movement input along waypoints, the ordinary walk a player makes: from the Koka door's arrival point on SCR_290 west
// along the passage (map y 200, the middle of its band clear of the door's trigger, the hardbox plus 30 cm: y 189-208 for the 28 cm capsule) into
// SCR_289 without touching S289_P19, north into the door alcove and east into the door, which warps him to SCR_350; then the return trip from
// S350_P09's arrival point in SCR_289 east along the passage back into the Koka room, again without touching the door. Line traces check the
// baked collision: the doorway is free, the void around the rooms is not.

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkLayout.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"
#include "AssetCompilingManager.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
#include "UObject/UObjectIterator.h"

namespace DinkEastWildsTest
{
	constexpr int32 West = 289;  // the booth's west room, door S289_P19 to the East Wilds
	constexpr int32 East = 290;  // the booth's Koka room, door S290_P19 to SCR_734
	constexpr int32 Meadow = 350;

	struct FWaypoint
	{
		int32 Screen;
		double X, Y;  // map pixels
	};

	// Planned on ImportData/collision.json with the capsule (28 cm = 6.4 px at the interior scale, 4.375 cm a pixel; every leg keeps at least
	// 7.6 px from a blocker) and the door's trigger (S289_P19's hardbox 521-600 x 125-176 plus 30 cm) kept clear.
	const FWaypoint Path[] = {
		{East, 295, 288}, {East, 240, 288}, {East, 236, 225}, {East, 140, 225}, {East, 136, 172},   // across the Koka room
		{East, 45, 160}, {East, 45, 200},                                                           // into the opening, down to the passage
		{West, 560, 200}, {West, 497, 200},                                                         // west along the passage, under the door
		{West, 497, 150},                                                                           // north into the door alcove
	};
	// The return: from S350_P09's arrival point (SCR_289 map 496,151) back to the middle of the Koka room.
	const FWaypoint Back[] = {
		{West, 497, 200}, {East, 45, 200}, {East, 45, 160}, {East, 136, 172}, {East, 236, 225},
	};
}

namespace
{
	class FDinkEastWildsCheck : public IAutomationLatentCommand
	{
	public:
		explicit FDinkEastWildsCheck(FAutomationTestBase* InTest) : Test(InTest), Began(FPlatformTime::Seconds()) {}

		virtual bool Update() override
		{
			using namespace DinkEastWildsTest;
			if (FPlatformTime::Seconds() - Began > 240.0)
			{
				Test->AddError(FString::Printf(TEXT("booth walk timed out at stage %d, waypoint %d"), Stage, Next));
				return true;
			}
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
			ADinkGreyboxCharacter* Hero = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
			UDinkStorySubsystem* Story = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
			UDinkGreyboxSubsystem* Greybox = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
			if (!Hero || !Story || !Greybox || !Story->IsReady() || Story->bNewGamePending)
			{
				return false;
			}
			const double Now = World->GetTimeSeconds();
			auto PlayerMap = [Story]() { return Story->GetFacts()->GetFact(TEXT("player_map")); };
			auto PhysicalScreen = [Greybox, Hero]()
			{
				const ADinkScreenVolume* S = Greybox->FindScreenAt(Hero->GetActorLocation());
				return S ? S->ScreenNumber : 0;
			};
			auto At = [Greybox](int32 Screen, double X, double Y, double Z = 0.0)
			{
				const ADinkScreenVolume* S = Greybox->FindScreen(Screen);
				return S ? DinkLayout::MapPixelToUnreal(S->Corners, X, Y, Z) : FVector::ZeroVector;
			};
			// Baked collision at a map pixel: a trace down from 5 m that stops on a prism (3 m tall) rather than the ground (0).
			auto Solid = [World, At](int32 Screen, double X, double Y)
			{
				FHitResult Hit;
				const FVector P = At(Screen, X, Y);
				return World->LineTraceSingleByChannel(Hit, P + FVector(0, 0, 500), P - FVector(0, 0, 50), ECC_Pawn) && Hit.ImpactPoint.Z - P.Z > 100.0;
			};
			auto Across = [World, At](int32 SA, double XA, double YA, int32 SB, double XB, double YB)
			{
				FHitResult Hit;
				return World->LineTraceSingleByChannel(Hit, At(SA, XA, YA, 1.5), At(SB, XB, YB, 1.5), ECC_Pawn);
			};

			switch (Stage)
			{
			case 0:
			{
				Story->SkipDialogue();
				if (Story->GetActiveMenu() || Story->GetDirector()->GetDink().bFrozen || PC->IsMoveInputIgnored() || Now < 2.0)
				{
					return false;
				}
				Story->bRunScreenScripts = false;
				for (TObjectIterator<UDinkWarpComponent> It; It; ++It)
				{
					if (It->GetWorld() != World) { continue; }
					if (It->WarpId == TEXT("S289_P19")) { Door = *It; }
					if (It->WarpId == TEXT("S734_P31")) { KokaDoor = *It; }
					if (It->WarpId == TEXT("S350_P09")) { MeadowDoor = *It; }
				}
				if (!Test->TestNotNull(TEXT("the East Wilds door S289_P19"), Door) || !Test->TestNotNull(TEXT("Koka's booth door S734_P31"), KokaDoor) ||
					!Test->TestNotNull(TEXT("the meadow's door back into the booth S350_P09"), MeadowDoor))
				{
					return true;
				}
				Test->TestTrue(TEXT("S289_P19 warps to SCR_350 at map 351,241 (engine 371,241) on walking in"),
					Door->bTriggerEnabled && Door->DestScreen == Meadow && Door->TriggerMode == TEXT("walk_in") && Door->DestMapPixel.Equals(FVector2D(351, 241)));
				Test->TestTrue(TEXT("S734_P31 warps into SCR_290 at map 295,310 (engine 315,310)"),
					KokaDoor->DestScreen == East && KokaDoor->DestMapPixel.Equals(FVector2D(295, 310)));
				Test->TestTrue(TEXT("S350_P09 warps into SCR_289 at map 496,151 (engine 516,151)"),
					MeadowDoor->DestScreen == West && MeadowDoor->DestMapPixel.Equals(FVector2D(496, 151)));
				const ADinkScreenVolume* VW = Greybox->FindScreen(West);
				const ADinkScreenVolume* VE = Greybox->FindScreen(East);
				if (!Test->TestNotNull(TEXT("SCR_289's screen volume"), VW) || !Test->TestNotNull(TEXT("SCR_290's"), VE))
				{
					return true;
				}
				Test->TestTrue(FString::Printf(TEXT("one interior: SCR_289 and SCR_290 on the same sheet (%s, %s)"), *VW->Sheet.ToString(), *VE->Sheet.ToString()), VW->Sheet == VE->Sheet);
				Test->TestTrue(TEXT("side by side: SCR_289's east edge is SCR_290's west edge"),
					FVector2D::Distance(VW->Corners.NE, VE->Corners.NW) < 0.01 && FVector2D::Distance(VW->Corners.SE, VE->Corners.SW) < 0.01);

				// The baked collision.
				Test->TestFalse(TEXT("the doorway is free: SCR_289 map 505,200 -> SCR_290 map 60,200"), Across(West, 505, 200, East, 60, 200));
				Test->TestFalse(TEXT("and along its lower edge: SCR_289 map 490,210 -> SCR_290 map 60,210"), Across(West, 490, 210, East, 60, 210));
				Test->TestFalse(TEXT("SCR_290's opening is free facing the door: map 90,150 -> 3,150"), Across(East, 90, 150, East, 3, 150));
				for (const FWaypoint& P : { FWaypoint{West, 590, 187}, FWaypoint{West, 530, 207}, FWaypoint{West, 490, 180}, FWaypoint{West, 580, 211},
						 FWaypoint{East, 10, 187}, FWaypoint{East, 10, 210}, FWaypoint{East, 10, 150}, FWaypoint{East, 60, 140}, FWaypoint{East, 60, 210} })
				{
					Test->TestFalse(FString::Printf(TEXT("doorway SCR_%03d map %.0f,%.0f is not solid"), P.Screen, P.X, P.Y), Solid(P.Screen, P.X, P.Y));
				}
				for (const FWaypoint& P : { FWaypoint{West, 580, 90}, FWaypoint{West, 580, 230}, FWaypoint{West, 580, 215}, FWaypoint{West, 470, 230}, FWaypoint{West, 30, 200},
						 FWaypoint{West, 300, 30}, FWaypoint{East, 20, 90}, FWaypoint{East, 20, 124}, FWaypoint{East, 20, 215}, FWaypoint{East, 20, 260},
						 FWaypoint{East, 300, 30}, FWaypoint{West, 550, 150} })
				{
					Test->TestTrue(FString::Printf(TEXT("void, jamb or door SCR_%03d map %.0f,%.0f is solid"), P.Screen, P.X, P.Y), Solid(P.Screen, P.X, P.Y));
				}
				// The parity layer keeps the 1997 walls (hard.dat + map.dat stamps; engine x = map x + 20).
				UDinkGameplay* Game = Story->GetGameplay();
				Test->TestTrue(TEXT("engine hardness: S290_P10's hardbox still at SCR_290 map 60,200"), Game->GetHard(East, 80, 200) >= 100);
				Test->TestTrue(TEXT("engine hardness: SCR_289's east wall still at map 500,200"), Game->GetHard(West, 520, 200) >= 100);

				Place(Hero, Greybox, KokaDoor->DestLocation);
				At0 = Now + 1.0;
				Stage = 1;
				return false;
			}
			case 1:
				if (Now < At0) { return false; }
				if (!Test->TestEqual(TEXT("Dink stands on SCR_290 at the Koka door's arrival point"), PhysicalScreen(), East) ||
					!Test->TestEqual(TEXT("player_map 290"), PlayerMap(), East))
				{
					return true;
				}
				Next = 0;
				Leg = Now;
				Stage = 2;
				return false;
			case 2:
			{
				const int32 Here = PhysicalScreen();
				if (Here == Meadow)
				{
					Test->AddError(FString::Printf(TEXT("the door warped Dink before the last waypoint (waypoint %d)"), Next));
					return true;
				}
				bSawWest |= Here == West && PlayerMap() == West;
				bTouched |= Door->IsOverlappingActor(Hero);
				const FWaypoint& P = Path[Next];
				const FVector Target = At(P.Screen, P.X, P.Y);
				const FVector D = Target - Hero->GetActorLocation();
				if (D.Size2D() < 6.0)
				{
					if (++Next == UE_ARRAY_COUNT(Path))
					{
						Hero->GetCharacterMovement()->StopMovementImmediately();
						Hero->ConsumeMovementInputVector();
						Test->TestTrue(TEXT("Dink walked into SCR_289 through the doorway (physical screen and player_map 289)"), bSawWest);
						Test->TestFalse(TEXT("without touching the door S289_P19's trigger on the way"), bTouched);
						Test->TestEqual(TEXT("and stands in its door alcove"), PhysicalScreen(), West);
						Leg = Now;
						Stage = 3;
					}
					else
					{
						Leg = Now;
					}
					return false;
				}
				if (Now - Leg > 12.0)
				{
					Test->AddError(FString::Printf(TEXT("stuck before waypoint %d (SCR_%03d map %.1f,%.1f), %.0f cm away, on SCR_%03d"), Next, P.Screen, P.X, P.Y,
						D.Size2D(), Here));
					return true;
				}
				// Slow near the waypoint so the walk does not overshoot into a wall or the door's trigger.
				Hero->AddMovementInput(D.GetSafeNormal2D(), D.Size2D() < 60.0 ? 0.35f : 1.f, true);
				return false;
			}
			case 3:
				if (PhysicalScreen() != Meadow)
				{
					if (Now - Leg > 8.0)
					{
						Test->AddError(FString::Printf(TEXT("walking east into S289_P19 did not warp Dink to SCR_350 (on SCR_%03d)"), PhysicalScreen()));
						return true;
					}
					Hero->AddMovementInput(FVector(At(West, 560, 150) - Hero->GetActorLocation()).GetSafeNormal2D(), 1.f, true);
					return false;
				}
				Hero->GetCharacterMovement()->StopMovementImmediately();
				Hero->ConsumeMovementInputVector();
				At0 = Now + 1.0;
				Stage = 4;
				return false;
			case 4:
				if (Now < At0) { return false; }
				Test->TestEqual(TEXT("S289_P19 warped Dink to SCR_350 (player_map)"), PlayerMap(), Meadow);
				Test->TestEqual(TEXT("he stands on SCR_350"), PhysicalScreen(), Meadow);
				Test->TestTrue(FString::Printf(TEXT("at the door's arrival point, map 351,241 (%.0f cm away)"), FVector::Dist2D(Hero->GetActorLocation(), Door->DestLocation)),
					FVector::Dist2D(Hero->GetActorLocation(), Door->DestLocation) < 150.0);
				// The return trip starts where the meadow's door S350_P09 puts Dink: the west room, in front of S289_P19.
				Place(Hero, Greybox, MeadowDoor->DestLocation);
				At0 = Now + 1.0;
				Stage = 5;
				return false;
			case 5:
				if (Now < At0) { return false; }
				if (!Test->TestEqual(TEXT("back in the west room at S350_P09's arrival point"), PhysicalScreen(), West) ||
					!Test->TestEqual(TEXT("player_map 289"), PlayerMap(), West))
				{
					return true;
				}
				Test->TestFalse(TEXT("the arrival point does not touch the door's trigger"), Door->IsOverlappingActor(Hero));
				bTouched = false;
				Next = 0;
				Leg = Now;
				Stage = 6;
				return false;
			case 6:
			{
				const int32 Here = PhysicalScreen();
				if (Here == Meadow)
				{
					Test->AddError(FString::Printf(TEXT("the return trip was pulled through the door to SCR_350 (waypoint %d)"), Next));
					return true;
				}
				bTouched |= Door->IsOverlappingActor(Hero);
				const FWaypoint& P = Back[Next];
				const FVector D = At(P.Screen, P.X, P.Y) - Hero->GetActorLocation();
				if (D.Size2D() < 6.0)
				{
					Leg = Now;
					if (++Next == UE_ARRAY_COUNT(Back))
					{
						Hero->GetCharacterMovement()->StopMovementImmediately();
						Hero->ConsumeMovementInputVector();
						Test->TestFalse(TEXT("the return trip never touched the door S289_P19's trigger"), bTouched);
						Test->TestEqual(TEXT("Dink is back in the Koka room (physical screen)"), Here, East);
						Test->TestEqual(TEXT("player_map 290"), PlayerMap(), East);
						return true;
					}
					return false;
				}
				if (Now - Leg > 12.0)
				{
					Test->AddError(FString::Printf(TEXT("return trip stuck before waypoint %d (SCR_%03d map %.1f,%.1f), %.0f cm away, on SCR_%03d"), Next, P.Screen,
						P.X, P.Y, D.Size2D(), Here));
					return true;
				}
				Hero->AddMovementInput(D.GetSafeNormal2D(), D.Size2D() < 60.0 ? 0.35f : 1.f, true);
				return false;
			}
			default:
				return true;
			}
		}

	private:
		static void Place(ADinkGreyboxCharacter* Hero, UDinkGreyboxSubsystem* Greybox, const FVector& Where)
		{
			Hero->SetActorLocation(Where + FVector(0, 0, 98), false, nullptr, ETeleportType::TeleportPhysics);
			Hero->GetCharacterMovement()->StopMovementImmediately();
			Greybox->RefreshCurrentScreen();
		}

		FAutomationTestBase* Test;
		double Began;
		double At0 = 0.0;
		double Leg = 0.0;
		int32 Stage = 0;
		int32 Next = 0;
		bool bSawWest = false;
		bool bTouched = false;
		UDinkWarpComponent* Door = nullptr;
		UDinkWarpComponent* KokaDoor = nullptr;
		UDinkWarpComponent* MeadowDoor = nullptr;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkEastWildsBoothTest, "Dink.Gameplay.EastWilds.BoothDoorwayLeadsToTheEastWilds", DINK_TEST_FLAGS)
bool FDinkEastWildsBoothTest::RunTest(const FString& Parameters)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!IFileManager::Get().FileExists(*File))
	{
		AddWarning(TEXT("skipped: generated world map absent (Scripts/import_greybox.sh --region all)"));
		return true;
	}
	if (!TestNotNull(TEXT("the world map loads"), UEditorLoadingAndSavingUtils::LoadMap(File)))
	{
		return false;
	}
	FAssetCompilingManager::Get().FinishAllCompilation();
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FDinkEastWildsCheck(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
