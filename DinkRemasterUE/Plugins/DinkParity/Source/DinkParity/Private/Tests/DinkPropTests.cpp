// Dink.Gameplay.Prop.*: the director command sp_prop, defined by owner decision OD1 (doc/remaster/verbatim_review.md, 9 Nov 2026).
//
// No 1997 command changes a placement's map `prop` flag; the two 1997 calls (s5-fguy.c:6 `sp_prop(&door, 0)` "kill door", s5-end.c:33
// `sp_prop(&door, 1)`, &door = sp(2) = S419_P02, seq 61, a warp to SCR_228) did nothing and sit behind fix switches that stay false. The remaster
// defines sp_prop(sprite, 0|1) as setting that flag until the screen loads again, with the engine's rules for it:
//  - get_hard (dink.cpp:569-575): a stamped hardbox (100 + n) of a placement whose prop is not 0 reads 0: walk-through.
//  - special_block (dink.cpp:15337-15341, called from the walk code at 16906-16909): Dink running into a placement with prop 1 warps.
//  - load_map reads map.dat anew: a screen load gives every placement map.dat's prop back.
// The greybox approximates a map.dat warp (prop 1) as a solid hardbox with a slightly larger trigger that fires on contact; with prop 0 it is a
// stamped hardbox, which is solid, so sp_prop(door, 0) switches only the trigger off. On a placement without a warp in map.dat a non-zero prop
// makes its hardbox walk-through and warps nowhere (only the 93 map.dat warps have a destination trigger).

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkNarrativeTypes.h"
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

namespace DinkPropTest
{
	constexpr int32 Screen = 419;
	constexpr int32 DoorIndex = 2;    // S419_P02: seq 61/1 at engine 425,234, map.dat prop 1, warp_map 228; hardbox map 381-411 x 225-248 (code 102)
	constexpr int32 BarrelIndex = 11; // S419_P11 bar-sh: a live barrel, hard 0 (stamped, code 111), prop 0, at engine 72,360

	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* G = nullptr;
		bool IsValid() const { return Story && Story->IsReady() && G && G->HasData() && G->GetData().FindPlacement(FDinkOriginId(Screen, DoorIndex)); }
	};

	/** A standalone story (no world), instant mode, a new game, on SCR_419 with its real map.dat and hardness data; screen scripts off. */
	FEnv Make(FAutomationTestBase& Test)
	{
		FEnv E;
		FString Error;
		UGameInstance* GI = DinkTest::MakeOuterGameInstance();
		E.Facts = NewObject<UDinkFactSubsystem>(GI);
		Test.TestTrue(TEXT("facts table loads"), E.Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
		E.World = NewObject<UDinkWorldStateSubsystem>(GI);
		E.Story = NewObject<UDinkStorySubsystem>(GI);
		Test.TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), E.Story->SetupStandalone(E.Facts, E.World, &Error));
		E.Story->StorySeed = 1997;
		E.Story->ResetRuntime();
		E.Story->bInstantMode = true;
		E.D = E.Story->GetDirector();
		E.G = E.Story->GetGameplay();
		Test.TestTrue(TEXT("gameplay data with SCR_419 (Scripts/sync_gameplay_data.py, prop column)"), E.IsValid());
		if (!E.IsValid())
		{
			return E;
		}
		E.G->Adaptation.bEnabled = false;
		E.Story->bRunScreenScripts = false;
		E.Story->OnScreenEntered(Screen);
		return E;
	}

	/** Runs DinkC command lines (as the converted story emits them: `>> sp_prop {s5_fguy__door} 0`) for a script instance of Sprite on SCR_419. */
	void Run(FEnv& E, int32 Sprite, const TArray<FString>& Commands)
	{
		FDinkScriptInstance Instance;
		Instance.Sprite = Sprite;
		Instance.Screen = Screen;
		for (const FString& C : Commands)
		{
			E.D->Execute(Instance, FDinkStoryLine::Parse(TEXT(">> ") + C, { TEXT("cmd"), TEXT("src:1") }));
		}
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPropFlagTest, "Dink.Gameplay.Prop.FlagFollowsTheMapRules", DINK_TEST_FLAGS)
bool FDinkPropFlagTest::RunTest(const FString& Parameters)
{
	using namespace DinkPropTest;
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	const FDinkOriginId Door(Screen, DoorIndex), Barrel(Screen, BarrelIndex);
	const FDinkPlacementInfo* DoorInfo = E.G->GetData().FindPlacement(Door);
	const FDinkPlacementInfo* BarrelInfo = E.G->GetData().FindPlacement(Barrel);
	if (!TestNotNull(TEXT("S419_P11 in placements.csv"), BarrelInfo))
	{
		return false;
	}
	TestEqual(TEXT("S419_P02 is a map.dat warp (prop 1)"), DoorInfo->Prop, 1);
	TestEqual(TEXT("to SCR_228 (warp_map)"), DoorInfo->WarpMap, 228);
	TestEqual(TEXT("its hardbox is stamped (hard 0)"), DoorInfo->Hard, 0);
	TestEqual(TEXT("S419_P11 (bar-sh) has prop 0"), BarrelInfo->Prop, 0);
	TestEqual(TEXT("and a stamped hardbox"), BarrelInfo->Hard, 0);
	TestEqual(TEXT("the door's flag is map.dat's"), E.G->GetPlacementProp(Door), 1);

	// The door: engine pixel 415,236 is inside its hardbox (map 395,236).
	const int32 DoorHard = E.G->GetHard(Screen, 415, 236);
	TestEqual(TEXT("the door's hardbox is in the loaded map as 100 + its index"), DoorHard, 102);
	const int32 DoorHandle = E.D->HandleForPlacement(Screen, DoorIndex);
	TestTrue(TEXT("sp(2) on SCR_419 is a sprite"), DoorHandle > 1);

	// s5-fguy.c:6 with its switch on: sp_prop(&door, 0).
	Run(E, DoorHandle, { FString::Printf(TEXT("sp_prop %d 0"), DoorHandle) });
	TestEqual(TEXT("sp_prop(door, 0): prop 0"), E.G->GetPlacementProp(Door), 0);
	TestEqual(TEXT("recorded on the sprite too"), E.D->FindSprite(DoorHandle)->GetProp(TEXT("prop"), -1), 0);
	TestEqual(TEXT("prop 0 with a stamped hardbox: hard (get_hard D:569 keeps 100 + n)"), E.G->GetHard(Screen, 415, 236), 102);
	TestTrue(TEXT("the change is a gameplay event"), E.G->Events.Contains(TEXT("prop S419_P02 0")));

	// s5-end.c:33 with its switch on: sp_prop(&door, 1).
	Run(E, DoorHandle, { FString::Printf(TEXT("sp_prop %d 1"), DoorHandle) });
	TestEqual(TEXT("sp_prop(door, 1): map.dat's value again"), E.G->GetPlacementProp(Door), 1);
	TestEqual(TEXT("the hardness unchanged"), E.G->GetHard(Screen, 415, 236), 102);

	// A screen load gives map.dat's flag back (load_map reads map.dat; no 1997 command writes prop).
	Run(E, DoorHandle, { FString::Printf(TEXT("sp_prop %d 0"), DoorHandle) });
	TestEqual(TEXT("off again"), E.G->GetPlacementProp(Door), 0);
	E.Story->OnScreenEntered(Screen - 1);
	E.Story->OnScreenEntered(Screen);
	TestEqual(TEXT("a screen load restores map.dat's prop 1"), E.G->GetPlacementProp(Door), 1);

	// A placement that is no warp: prop 1 makes its stamped hardbox walk-through (get_hard D:569) and warps nowhere (no destination trigger).
	const int32 BarrelCode = E.G->GetHard(Screen, BarrelInfo->X, BarrelInfo->Y - 2);
	TestEqual(TEXT("the barrel's hardbox is hard (100 + 11)"), BarrelCode, 111);
	const int32 BarrelHandle = E.D->HandleForPlacement(Screen, BarrelIndex);
	Run(E, BarrelHandle, { FString::Printf(TEXT("sp_prop %d 1"), BarrelHandle) });
	TestEqual(TEXT("sp_prop(barrel, 1): prop 1"), E.G->GetPlacementProp(Barrel), 1);
	TestEqual(TEXT("its hardbox now reads 0: walk-through"), E.G->GetHard(Screen, BarrelInfo->X, BarrelInfo->Y - 2), 0);
	TestEqual(TEXT("the door is untouched"), E.G->GetHard(Screen, 415, 236), 102);
	// draw_hard_map stamps the barrel again (fill_hard_sprites does not read prop), and get_hard still reads it as 0.
	Run(E, BarrelHandle, { TEXT("draw_hard_map") });
	TestEqual(TEXT("stamped again by draw_hard_map"), E.G->GetLiveHardness(Screen) ? E.G->GetLiveHardness(Screen)->Get(BarrelInfo->X - 20, BarrelInfo->Y - 2) : 0, 111);
	TestEqual(TEXT("and still walk-through"), E.G->GetHard(Screen, BarrelInfo->X, BarrelInfo->Y - 2), 0);
	Run(E, BarrelHandle, { FString::Printf(TEXT("sp_prop %d 0"), BarrelHandle) });
	TestEqual(TEXT("sp_prop(barrel, 0): hard again"), E.G->GetHard(Screen, BarrelInfo->X, BarrelInfo->Y - 2), 111);
	Run(E, BarrelHandle, { FString::Printf(TEXT("sp_prop %d 1"), BarrelHandle) });
	E.Story->OnScreenEntered(Screen - 1);
	E.Story->OnScreenEntered(Screen);
	TestEqual(TEXT("a screen load: the barrel's prop is map.dat's 0"), E.G->GetPlacementProp(Barrel), 0);
	TestEqual(TEXT("and its hardbox hard"), E.G->GetHard(Screen, BarrelInfo->X, BarrelInfo->Y - 2), 111);

	// A sprite that is no placement has no map flag: sp_prop only records it.
	const int32 Made = E.D->CreateVirtualSprite(Screen, 300, 200);
	Run(E, Made, { FString::Printf(TEXT("sp_prop %d 1"), Made) });
	TestEqual(TEXT("a created sprite: recorded"), E.D->FindSprite(Made)->GetProp(TEXT("prop"), -1), 1);
	TestEqual(TEXT("nothing else changes"), E.G->GetPlacementProp(Door), 1);
	return true;
}

namespace
{
	/**
	 * PIE on the generated world: Dink by the SCR_419 door (S419_P02, the house's warp to SCR_228). With sp_prop(door, 0) he walks into the
	 * door and stays on SCR_419; after sp_prop(door, 1) the same walk warps him to SCR_228; a screen load with the door switched off gives the
	 * warp back.
	 */
	class FDinkPropDoorCheck : public IAutomationLatentCommand
	{
	public:
		explicit FDinkPropDoorCheck(FAutomationTestBase* InTest) : Test(InTest), Began(FPlatformTime::Seconds()) {}

		virtual bool Update() override
		{
			if (FPlatformTime::Seconds() - Began > 120.0)
			{
				Test->AddError(FString::Printf(TEXT("SCR_419 door check timed out at stage %d"), Stage));
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
			UDinkDirector* Director = Story->GetDirector();
			UDinkGameplay* Game = Story->GetGameplay();
			const double Now = World->GetTimeSeconds();
			const FDinkOriginId DoorOrigin(DinkPropTest::Screen, DinkPropTest::DoorIndex);
			auto PlayerMap = [Story]() { return Story->GetFacts()->GetFact(TEXT("player_map")); };
			auto PhysicalScreen = [Greybox, Hero]()
			{
				const ADinkScreenVolume* S = Greybox->FindScreenAt(Hero->GetActorLocation());
				return S ? S->ScreenNumber : 0;
			};
			auto SpProp = [Director](int32 Value)
			{
				const int32 Handle = Director->HandleForPlacement(DinkPropTest::Screen, DinkPropTest::DoorIndex);
				FDinkScriptInstance Stand;
				Director->Execute(Stand, FDinkStoryLine::Parse(FString::Printf(TEXT(">> sp_prop %d %d"), Handle, Value), { TEXT("cmd"), TEXT("src:6") }));
				return Handle;
			};
			auto Push = [this, Hero]() { Hero->AddMovementInput((Door->GetComponentLocation() - Hero->GetActorLocation()).GetSafeNormal2D(), 1.f, true); };
			auto Place = [Hero, Greybox](const FVector& At)
			{
				Hero->SetActorLocation(At + FVector(0, 0, 98), false, nullptr, ETeleportType::TeleportPhysics);
				Hero->GetCharacterMovement()->StopMovementImmediately();
				Greybox->RefreshCurrentScreen();
			};

            // Marked screens need their normal Story entry, even for a prop-only test.
            if ((Stage==1||Stage==5) && Now>=At && Game->RequiresOriginalHardnessScreen(DinkPropTest::Screen) &&
                (Director->GetDink().Screen!=DinkPropTest::Screen || !Game->UsesOriginalHardnessProjection(DinkPropTest::Screen) || Game->IsHardnessLoading()))
            {
                if(FPlatformTime::Seconds()<AdmissionDeadline)return false;
                Test->AddError(FString::Printf(TEXT("SCR419 prop entry refused/timed out: director=%d projected=%d loading=%d screenScripts=%d"),Director->GetDink().Screen,int32(Game->UsesOriginalHardnessProjection(DinkPropTest::Screen)),int32(Game->IsHardnessLoading()),int32(Story->bRunScreenScripts)));
                return true;
            }

			switch (Stage)
			{
			case 0:
				// Skip dialogue normally; keep Story entry enabled so marked physical/logical admission completes.
				Story->SkipDialogue();
				if (Story->GetActiveMenu() || Director->GetDink().bFrozen || PC->IsMoveInputIgnored() || Now < 2.0)
				{
					return false;
				}
				if(!Test->TestTrue(TEXT("normal screen entry remains enabled"),Story->bRunScreenScripts))return true;
				for (TObjectIterator<UDinkWarpComponent> It; It; ++It)
				{
					if (It->GetWorld() == World && It->WarpId == TEXT("S419_P02")) { Door = *It; }
					if (It->GetWorld() == World && It->WarpId == TEXT("S228_P20")) { Back = *It; }
				}
				if (!Test->TestNotNull(TEXT("the SCR_419 door's warp S419_P02"), Door) || !Test->TestNotNull(TEXT("its return warp S228_P20"), Back))
				{
					return true;
				}
				Test->TestTrue(TEXT("the door warps to SCR_228 on walking in"), Door->bTriggerEnabled && Door->DestScreen == 228 && Door->TriggerMode == TEXT("walk_in"));
				// Where the house's exit puts Dink: on SCR_419 in front of the door.
				Arrival = Back->DestLocation;
				Place(Arrival);
                AdmissionDeadline=FPlatformTime::Seconds()+5;
				At = Now + 1.0;
				Stage = 1;
				return false;
			case 1:
				if (Now < At) { return false; }
				if (!Test->TestEqual(TEXT("Dink stands on SCR_419 in front of the door"), PhysicalScreen(), DinkPropTest::Screen) || PlayerMap() != DinkPropTest::Screen)
				{
					Test->AddError(FString::Printf(TEXT("player_map %d"), PlayerMap()));
					return true;
				}
				// s5-fguy.c:6 ("kill door") with its switch on.
				SpProp(0);
				Test->TestEqual(TEXT("sp_prop(door, 0): the placement's prop is 0"), Game->GetPlacementProp(DoorOrigin), 0);
				Test->TestFalse(TEXT("its warp is switched off"), Greybox->IsSpriteWarpOn(TEXT("S419_P02")));
				At = Now + 3.0;
				Stage = 2;
				return false;
			case 2:
				Push();
				bTouched |= Door->IsOverlappingActor(Hero);
				if (PhysicalScreen() != DinkPropTest::Screen)
				{
					Test->AddError(FString::Printf(TEXT("with prop 0 the door warped Dink to SCR_%03d"), PhysicalScreen()));
					return true;
				}
				if (Now < At) { return false; }
				Test->TestTrue(TEXT("Dink walked into the door"), bTouched);
				Test->TestTrue(TEXT("and still touches it"), Door->IsOverlappingActor(Hero));
				Test->TestEqual(TEXT("prop 0: no warp, Dink stays on SCR_419 (special_block runs only for prop 1, dink.cpp:15339)"), PhysicalScreen(), DinkPropTest::Screen);
				// s5-end.c:33 with its switch on.
				SpProp(1);
				Test->TestEqual(TEXT("sp_prop(door, 1): prop 1"), Game->GetPlacementProp(DoorOrigin), 1);
				Test->TestTrue(TEXT("its warp is on again"), Greybox->IsSpriteWarpOn(TEXT("S419_P02")));
				At = Now + 4.0;
				Stage = 3;
				return false;
			case 3:
				if (PhysicalScreen() != 228)
				{
					if (Now < At)
					{
						Push();
						return false;
					}
					Test->AddError(TEXT("with prop 1 again the door did not warp Dink to SCR_228"));
					return true;
				}
				Hero->GetCharacterMovement()->StopMovementImmediately();
				Hero->ConsumeMovementInputVector();
				Test->TestTrue(TEXT("prop 1: walking into the door warps Dink to SCR_228"), true);
				At = Now + 1.0;
				Stage = 4;
				return false;
			case 4:
				if (Now < At) { return false; }
				// Back on SCR_419, the door switched off for this visit, then a screen load.
				Place(Arrival);
                AdmissionDeadline=FPlatformTime::Seconds()+5;
				At = Now + 1.0;
				Stage = 5;
				return false;
			case 5:
				if (Now < At) { return false; }
				if (!Test->TestEqual(TEXT("back on SCR_419"), PlayerMap(), DinkPropTest::Screen))
				{
					return true;
				}
				SpProp(0);
				Test->TestFalse(TEXT("switched off on the new visit"), Greybox->IsSpriteWarpOn(TEXT("S419_P02")));
				Greybox->GotoScreen(1, 314.f, 161.f);
				Greybox->RefreshCurrentScreen();
				At = Now + 1.0;
				Stage = 6;
				return false;
			case 6:
				if (Now < At) { return false; }
				Test->TestEqual(TEXT("a screen load (SCR_001)"), PlayerMap(), 1);
				Test->TestTrue(TEXT("gives the door its warp back"), Greybox->IsSpriteWarpOn(TEXT("S419_P02")));
				Test->TestEqual(TEXT("and map.dat's prop 1"), Game->GetPlacementProp(DoorOrigin), 1);
				return true;
			default:
				return true;
			}
		}

	private:
		FAutomationTestBase* Test;
		double Began;
		double At = 0.0;
        double AdmissionDeadline = 0.0;
		int32 Stage = 0;
		bool bTouched = false;
		UDinkWarpComponent* Door = nullptr;
		UDinkWarpComponent* Back = nullptr;
		FVector Arrival = FVector::ZeroVector;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPropDoorTest, "Dink.Gameplay.Prop.Scr419DoorWarpFollowsProp", DINK_TEST_FLAGS)
bool FDinkPropDoorTest::RunTest(const FString& Parameters)
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
	ADD_LATENT_AUTOMATION_COMMAND(FDinkPropDoorCheck(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

namespace DinkPropTest
{
	/** A brain-0 sprite at engine (X, FromY) follows Dink at (X, DinkY) for 200 engine frames (move_legal on every step). Its final y. */
	int32 FollowWalk(FEnv& E, int32 X, int32 FromY, int32 DinkY)
	{
		FDinkSprite& Dink = E.D->GetDink();
		Dink.Screen = Screen;
		Dink.X = X;
		Dink.Y = DinkY;
		const int32 H = E.D->CreateVirtualSprite(Screen, X, FromY);
		FDinkSprite& W = *E.D->FindSprite(H);
		UDinkDirector::InitCreatedSprite(W);
		W.Props.Add(TEXT("brain"), 0);
		W.Props.Add(TEXT("follow"), 1);
		W.Props.Add(TEXT("speed"), 1);
		W.Props.Add(TEXT("timing"), 0);
		W.Props.Add(TEXT("base_walk"), -1);
		for (int32 Frame = 0; Frame < 200; ++Frame)
		{
			E.G->ThinkSprite(H, Frame * UDinkGameplay::EngineFrameMs);
		}
		const int32 Y = FMath::RoundToInt32(E.D->FindSprite(H)->Y);
		E.D->DeactivateSprite(H, 0);
		return Y;
	}
}

// get_hard (dink.cpp:569-575) reads a stamped hardbox of a placement whose prop is not 0 as 0, for every sprite that moves: monsters, people and
// missiles walk and fly through a map.dat warp's hardbox (a door). Only Dink warps there (special_block from the walk code, D:16906-16911).
// The remaster used to stop every sprite at a door's hardbox (alpha bug list: "monsters and missiles treat a warp's hardbox as solid").
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPropSpritesCrossWarpTest, "Dink.Gameplay.Prop.SpritesCrossMapWarpHardbox", DINK_TEST_FLAGS)
bool FDinkPropSpritesCrossWarpTest::RunTest(const FString& Parameters)
{
	using namespace DinkPropTest;
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	const FDinkOriginId Door(Screen, DoorIndex);
	// Engine x 415 crosses the door's hardbox (code 102); south of it the column is free down to y 275.
	TestEqual(TEXT("the door's hardbox reads 102 in the map (GetHard keeps it for the pawn's warp box and the probe)"), E.G->GetHard(Screen, 415, 240), 102);
	int32 Edge = 275;
	while (Edge > 200 && E.G->GetHard(Screen, 415, Edge - 1) == 0)
	{
		--Edge;
	}
	if (!TestEqual(TEXT("precondition: going north from engine 415,275 the first hard pixel is the door's (102)"), E.G->GetHard(Screen, 415, Edge - 1), 102) ||
		!TestTrue(TEXT("precondition: at least 20 free pixels south of it"), Edge <= 255))
	{
		return false;
	}
	const int32 Through = FollowWalk(E, 415, 275, 200);
	TestTrue(FString::Printf(TEXT("a walker from the south walks into the door's hardbox (prop 1: get_hard reads 0), past its edge at y %d (got %d)"), Edge, Through), Through < Edge - 1);

	// With sp_prop(door, 0) (owner decision OD1) the flag is 0: the stamped hardbox is solid for sprites, as for any prop-0 placement.
	const int32 DoorHandle = E.D->HandleForPlacement(Screen, DoorIndex);
	Run(E, DoorHandle, { FString::Printf(TEXT("sp_prop %d 0"), DoorHandle) });
	TestEqual(TEXT("sp_prop(door, 0)"), E.G->GetPlacementProp(Door), 0);
	TestEqual(TEXT("then the walker stops at the hardbox's south edge"), FollowWalk(E, 415, 275, 200), Edge);
	Run(E, DoorHandle, { FString::Printf(TEXT("sp_prop %d 1"), DoorHandle) });
	TestTrue(TEXT("map.dat's prop 1 again: walk-through again"), FollowWalk(E, 415, 275, 200) < Edge - 1);
	return true;
}
