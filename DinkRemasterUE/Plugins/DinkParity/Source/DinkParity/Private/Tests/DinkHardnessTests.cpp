// Dink.Gameplay.Hardness.*: sp_hard, draw_hard_sprite and draw_hard_map as the 1997 engine runs them (AGENTS.md pitfall 77).
//
//  - sp_hard (dink.cpp:9979-9998): the sprite's hard flag (inverted: 0 = hard); for a placement's sprite also g_smallMap.sprite[sp_index].hard.
//  - draw_hard_sprite (dink.cpp:8089-8104): update_play_changes, fill_hardxy of the sprite's hardbox (the tile layer comes back there,
//    597-614), fill_back_sprites (6832-6895), fill_hard_sprites (6972-7031).
//  - draw_hard_map (dink.cpp:8224-8232): update_play_changes, fill_whole_hard (654-681), fill_hard_sprites, fill_back_sprites.
//  - add_hardness (dink.cpp:487-501) stamps 100 + the placement's index, or 1 for a sprite that is not a placement.
//
// Headless on SCR_031 (no base script; the barrel S031_P03 bar-gh, hard; the pig S031_P04 pdie, not hard), with the screen's real hardness
// and tile layer (Content/Dink/Data/Gameplay/Hardness/SCR_031.txt). A walker (brain 0 following Dink: process_follow, then
// check_if_move_is_legal, the test Dink's own walk uses in the engine) shows where a body can go. The last test runs the same commands in a
// physics world and checks the greybox's solid collision.

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkLayout.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

namespace DinkHardnessTest
{
	constexpr int32 Screen = 31;
	constexpr int32 BarrelIndex = 3; // S031_P03 bar-gh, engine 320,316, seq 173/1: hardbox map x 283-319, y 301-321 (code 103)
	constexpr int32 PigIndex = 4;    // S031_P04 pdie, engine 321,107, seq 41/1, hard 1 in map.dat: box map x 275-320, y 83-110

	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* G = nullptr;
		bool IsValid() const { return Story && Story->IsReady() && G && G->HasData() && G->GetData().GetTileHardness(Screen); }
	};

	/** A standalone story (no world unless the caller's GI has one), instant mode, a new game, on SCR_031. */
	FEnv Make(FAutomationTestBase& Test, UGameInstance* GI = nullptr)
	{
		FEnv E;
		FString Error;
		if (GI)
		{
			E.Story = GI->GetSubsystem<UDinkStorySubsystem>();
			E.Facts = GI->GetSubsystem<UDinkFactSubsystem>();
			E.World = GI->GetSubsystem<UDinkWorldStateSubsystem>();
		}
		else
		{
			GI = DinkTest::MakeOuterGameInstance();
			E.Facts = NewObject<UDinkFactSubsystem>(GI);
			Test.TestTrue(TEXT("facts table loads"), E.Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
			E.World = NewObject<UDinkWorldStateSubsystem>(GI);
			E.Story = NewObject<UDinkStorySubsystem>(GI);
			Test.TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), E.Story->SetupStandalone(E.Facts, E.World, &Error));
		}
		if (!E.Story)
		{
			return E;
		}
		E.Story->StorySeed = 1997;
		E.Story->ResetRuntime();
		E.Story->bInstantMode = true;
		E.D = E.Story->GetDirector();
		E.G = E.Story->GetGameplay();
		Test.TestTrue(TEXT("gameplay data with SCR_031's tile layer (Scripts/sync_gameplay_data.py)"), E.IsValid());
		if (!E.IsValid())
		{
			return E;
		}
		E.G->Adaptation.bEnabled = false;
		E.G->StartNewGame();
		E.Story->RunUntilIdle();
		E.Story->OnScreenEntered(Screen);
		E.Story->RunUntilIdle();
		return E;
	}

	/** Runs DinkC command lines (as the converted story emits them) for a script instance of Sprite on OnScreen. */
	void Run(FEnv& E, int32 Sprite, const TArray<FString>& Commands, int32 OnScreen = Screen)
	{
		const int32 Id = E.Story->StartProcedure(TEXT("pdie"), TEXT("main"), Sprite, {}, OnScreen, /*bNewInstance*/ true);
		FDinkScriptInstance* Instance = E.Story->FindInstance(Id);
		if (!Instance)
		{
			return;
		}
		for (const FString& C : Commands)
		{
			E.D->Execute(*Instance, FDinkStoryLine::Parse(TEXT(">> ") + C, { TEXT("cmd"), TEXT("src:1") }));
		}
		E.Story->RunUntilIdle();
	}

	/**
	 * Dink at engine (X, DinkY), a walker (brain 0, follow 1, speed 1, timing 0) at (X, FromY) walking towards him one pixel a frame until
	 * within 40 px (it stops at DinkY - 39) or stopped by hardness (check_if_move_is_legal). Returns the walker's final y.
	 */
	int32 Walk(FEnv& E, int32 X, int32 FromY, int32 DinkY)
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

	/** Pixels of the map with Code. */
	int32 Count(const FDinkHardnessMap& Map, int32 Code)
	{
		int32 N = 0;
		for (const uint8 C : Map.Codes)
		{
			N += C == Code;
		}
		return N;
	}

	/** Pixels of the map box [L, R) x [T, B) (map coordinates) with Code. */
	int32 CountIn(const FDinkHardnessMap& Map, int32 L, int32 T, int32 R, int32 B, int32 Code)
	{
		int32 N = 0;
		for (int32 Y = T; Y < B; ++Y)
		{
			for (int32 X = L; X < R; ++X)
			{
				N += Map.Get(X, Y) == Code;
			}
		}
		return N;
	}

	/** Pixels where two maps differ (and the first one, for the message). */
	int32 Differ(const FDinkHardnessMap& A, const FDinkHardnessMap& B, FString& First)
	{
		int32 N = 0;
		for (int32 i = 0; i < FMath::Min(A.Codes.Num(), B.Codes.Num()); ++i)
		{
			if (A.Codes[i] != B.Codes[i])
			{
				if (N++ == 0)
				{
					First = FString::Printf(TEXT("map %d,%d: %d vs %d"), i % FDinkHardnessMap::Width, i / FDinkHardnessMap::Width, A.Codes[i], B.Codes[i]);
				}
			}
		}
		return N;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHardnessDrawHardMapRebuildsTest, "Dink.Gameplay.Hardness.DrawHardMapRebuildsTheLoadedMap", DINK_TEST_FLAGS)
bool FDinkHardnessDrawHardMapRebuildsTest::RunTest(const FString& Parameters)
{
	using namespace DinkHardnessTest;
	// The tile layer is the loaded map wherever no hardbox is stamped, and draw_hard_map on a screen nobody touched rebuilds exactly the map
	// the engine built on load (the port of fill_whole_hard, fill_hard_sprites, fill_back_sprites and their ranks against tools/dinkex's maps).
	for (const int32 S : { 31, 209, 712, 710, 536, 156 })
	{
		FEnv E = Make(*this);
		if (!E.IsValid())
		{
			return false;
		}
		if (S != Screen)
		{
			E.Story->OnScreenEntered(S);
			E.Story->RunUntilIdle();
		}
		const FDinkHardnessMap* Loaded = E.G->GetData().GetHardness(S, E.Facts->GetFact(TEXT("vision")));
		const FDinkHardnessMap* Tiles = E.G->GetData().GetTileHardness(S);
		if (!TestNotNull(FString::Printf(TEXT("SCR_%03d has its hardness and tile layer"), S), Loaded) || !TestNotNull(TEXT("tile layer"), Tiles))
		{
			continue;
		}
		int32 Mismatch = 0;
		for (int32 i = 0; i < Loaded->Codes.Num(); ++i)
		{
			Mismatch += Loaded->Codes[i] < 100 && Loaded->Codes[i] != Tiles->Codes[i];
		}
		TestEqual(FString::Printf(TEXT("SCR_%03d: tile layer = loaded map outside the hardboxes"), S), Mismatch, 0);
		TestNull(TEXT("no redrawn map before a draw"), E.G->GetLiveHardness(S));
		Run(E, 1, { TEXT("draw_hard_map") }, S);
		const FDinkHardnessMap* Live = E.G->GetLiveHardness(S);
		if (TestNotNull(TEXT("draw_hard_map leaves a redrawn map"), Live))
		{
			FString First;
			TestEqual(FString::Printf(TEXT("SCR_%03d: draw_hard_map rebuilds the loaded map (%s)"), S, *First), Differ(*Live, *Loaded, First), 0);
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHardnessSoftSpriteTest, "Dink.Gameplay.Hardness.SoftSpriteLetsDinkThrough", DINK_TEST_FLAGS)
bool FDinkHardnessSoftSpriteTest::RunTest(const FString& Parameters)
{
	using namespace DinkHardnessTest;
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	const int32 Barrel = E.D->HandleForPlacement(Screen, BarrelIndex);
	TestTrue(TEXT("the barrel is a sprite with bar-gh"), Barrel > 1 && E.D->FindSprite(Barrel)->Script == FName(TEXT("bar-gh")));
	TestEqual(TEXT("its hardbox is stamped (103) on load"), E.G->GetHard(Screen, 320, 316), 103);
	TestEqual(TEXT("a walker coming from the north stops at the barrel's top edge (map y 301)"), Walk(E, 320, 260, 345), 300);

	// bar-gh.c `hit`, verbatim: editor_type 3 (flat for good), sp_hard(&current_sprite, 1), draw_hard_sprite(&current_sprite).
	E.Story->StartProcedure(TEXT("bar-gh"), TEXT("hit"), Barrel, {}, Screen);
	E.Story->RunUntilIdle();
	TestEqual(TEXT("bar-gh made the barrel background without hardness (editor_type 3)"), static_cast<int32>(E.World->GetOverrideType(FDinkOriginId(Screen, BarrelIndex))), 3);
	TestEqual(TEXT("its sprite's hard flag is 1"), E.D->FindSprite(Barrel)->GetProp(TEXT("hard")), 1);
	const FDinkHardnessMap* Live = E.G->GetLiveHardness(Screen);
	if (!TestNotNull(TEXT("draw_hard_sprite redrew the map"), Live))
	{
		return false;
	}
	TestEqual(TEXT("no pixel of the barrel's hardbox is left"), Count(*Live, 103), 0);
	TestEqual(TEXT("the tile layer is back under it (0 there)"), E.G->GetHard(Screen, 320, 316), 0);
	TestEqual(TEXT("the tree's and the thorn's hardboxes are stamped again"), Count(*Live, 101) + Count(*Live, 102), 1378 + 4080);
	TestEqual(TEXT("the walker now walks through where the barrel was, to 40 px from Dink"), Walk(E, 320, 260, 345), 345 - 39);

	// A screen load builds the hardness anew (load_map), and place_sprites_game runs update_play_changes first (D:5974, 5792-5798): the save's
	// editor_type 3 clears the barrel's hard flag, so its box is not stamped on the next visit either (pitfall 77, fixed 14 Nov 2026).
	E.Story->OnScreenEntered(Screen + 1);
	E.Story->OnScreenEntered(Screen);
	E.Story->RunUntilIdle();
	const FDinkHardnessMap* Reloaded = E.G->GetLiveHardness(Screen);
	TestTrue(TEXT("the reloaded map has no pixel of the barrel's hardbox"), !Reloaded || Count(*Reloaded, 103) == 0);
	TestEqual(TEXT("the barrel made flat for good stays walk-through on the next visit"), E.G->GetHard(Screen, 320, 316), 0);
	TestEqual(TEXT("the tree's and the thorn's hardboxes are still there"), Reloaded ? Count(*Reloaded, 101) + Count(*Reloaded, 102) : -1, 1378 + 4080);
	TestEqual(TEXT("the walker walks through where the barrel was"), Walk(E, 320, 260, 345), 345 - 39);
	// editor_type 5 (background, hard) stamps it again on the next load, with the picture the save holds (here the intact barrel's again).
	const FDinkPlacementInfo* BarrelInfo = E.G->GetData().FindPlacement(FDinkOriginId(Screen, BarrelIndex));
	E.World->SetOverride(FDinkOriginId(Screen, BarrelIndex), EDinkOverrideType::BackgroundHard);
	if (BarrelInfo)
	{
		Run(E, E.D->HandleForPlacement(Screen, BarrelIndex), { FString::Printf(TEXT("editor_seq %d %d"), BarrelIndex, BarrelInfo->Seq),
			FString::Printf(TEXT("editor_frame %d %d"), BarrelIndex, BarrelInfo->Frame) });
	}
	E.Story->OnScreenEntered(Screen + 1);
	E.Story->OnScreenEntered(Screen);
	E.Story->RunUntilIdle();
	TestTrue(TEXT("editor_type 5: the barrel's box is stamped on load (100 + its index)"), E.G->GetHard(Screen, 320, 316) == 103);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHardnessHardSpriteTest, "Dink.Gameplay.Hardness.HardSpriteBlocks", DINK_TEST_FLAGS)
bool FDinkHardnessHardSpriteTest::RunTest(const FString& Parameters)
{
	using namespace DinkHardnessTest;
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	const int32 Pig = E.D->HandleForPlacement(Screen, PigIndex);
	TestTrue(TEXT("the pig is a sprite"), Pig > 1);
	TestEqual(TEXT("map.dat's pig has no hardbox (hard 1)"), E.G->GetHard(Screen, 321, 100), 0);
	// (A line of low hardness crosses map y 54-55 above it: the walker starts below.)
	TestEqual(TEXT("a walker from the north passes where the pig stands"), Walk(E, 320, 60, 160), 160 - 39);

	// sp_hard(pig, 0) alone changes nothing on the map; draw_hard_sprite stamps it (fill_hard_sprites: the map's flag of S031_P04 is 0 now).
	Run(E, Pig, { FString::Printf(TEXT("sp_hard %d 0"), Pig) });
	TestEqual(TEXT("sp_hard sets the sprite's flag"), E.D->FindSprite(Pig)->GetProp(TEXT("hard")), 0);
	TestEqual(TEXT("sp_hard alone does not touch the map"), E.G->GetHard(Screen, 321, 100), 0);
	Run(E, Pig, { FString::Printf(TEXT("draw_hard_sprite %d"), Pig) });
	TestEqual(TEXT("draw_hard_sprite stamps the pig's hardbox as 100 + its index"), E.G->GetHard(Screen, 321, 100), 104);
	TestEqual(TEXT("its whole box: 46 x 28 px"), Count(*E.G->GetLiveHardness(Screen), 104), 46 * 28);
	TestEqual(TEXT("the walker stops at the pig's top edge (map y 83)"), Walk(E, 320, 60, 160), 82);

	// A sprite that is not a placement stamps 1 (D:7024-7029).
	const int32 Made = E.D->CreateVirtualSprite(Screen, 160, 250);
	FDinkSprite& M = *E.D->FindSprite(Made);
	UDinkDirector::InitCreatedSprite(M);
	M.Props.Add(TEXT("pseq"), 173);
	M.Props.Add(TEXT("pframe"), 1);
	Run(E, Made, { FString::Printf(TEXT("draw_hard_sprite %d"), Made) });
	TestEqual(TEXT("a created sprite is not hard (add_sprite: hard 1)"), E.G->GetHard(Screen, 160, 250), 0);
	Run(E, Made, { FString::Printf(TEXT("sp_hard %d 0"), Made), FString::Printf(TEXT("draw_hard_sprite %d"), Made) });
	TestEqual(TEXT("made hard, it stamps code 1"), E.G->GetHard(Screen, 160, 250), 1);
	TestEqual(TEXT("over its whole box (seq 173/1: -17..20 x -15..6, map 123-159 x 235-255)"), CountIn(*E.G->GetLiveHardness(Screen), 123, 235, 160, 256, 1), 37 * 21);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHardnessDrawHardMapRestoresTest, "Dink.Gameplay.Hardness.DrawHardMapRestores", DINK_TEST_FLAGS)
bool FDinkHardnessDrawHardMapRestoresTest::RunTest(const FString& Parameters)
{
	using namespace DinkHardnessTest;
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	const FDinkHardnessMap& Loaded = *E.G->GetData().GetHardness(Screen, 0);
	const int32 Barrel = E.D->HandleForPlacement(Screen, BarrelIndex);
	const int32 Pig = E.D->HandleForPlacement(Screen, PigIndex);
	// The barrel soft and the pig hard (sp_hard + draw_hard_sprite each, no editor_type), then both flags back and one draw_hard_map.
	Run(E, Barrel, { FString::Printf(TEXT("sp_hard %d 1"), Barrel), FString::Printf(TEXT("draw_hard_sprite %d"), Barrel),
		FString::Printf(TEXT("sp_hard %d 0"), Pig), FString::Printf(TEXT("draw_hard_sprite %d"), Pig) });
	TestEqual(TEXT("barrel soft"), E.G->GetHard(Screen, 320, 316), 0);
	TestEqual(TEXT("pig hard"), E.G->GetHard(Screen, 321, 100), 104);
	TestEqual(TEXT("walker through the barrel"), Walk(E, 320, 260, 345), 345 - 39);
	Run(E, Barrel, { FString::Printf(TEXT("sp_hard %d 0"), Barrel), FString::Printf(TEXT("sp_hard %d 1"), Pig) });
	TestEqual(TEXT("sp_hard alone: the barrel still soft"), E.G->GetHard(Screen, 320, 316), 0);
	Run(E, Barrel, { TEXT("draw_hard_map") });
	FString First;
	TestEqual(FString::Printf(TEXT("draw_hard_map restores the loaded map (%s)"), *First), Differ(*E.G->GetLiveHardness(Screen), Loaded, First), 0);
	TestEqual(TEXT("barrel hard again"), E.G->GetHard(Screen, 320, 316), 103);
	TestEqual(TEXT("pig soft again"), E.G->GetHard(Screen, 321, 100), 0);
	TestEqual(TEXT("the walker stops at the barrel again"), Walk(E, 320, 260, 345), 300);
	// sp_active(sprite, 0) and draw_hard_map (s1-h1-4.c, s4-rock.c): an inactive sprite is not stamped (fill_hard_sprites skips it).
	Run(E, Barrel, { FString::Printf(TEXT("sp_active %d 0"), Barrel), TEXT("draw_hard_map") });
	TestEqual(TEXT("a deactivated placement's hardbox is gone after draw_hard_map"), E.G->GetHard(Screen, 320, 316), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHardnessGreyboxCollisionTest, "Dink.Gameplay.Hardness.GreyboxCollisionFollows", DINK_TEST_FLAGS)
bool FDinkHardnessGreyboxCollisionTest::RunTest(const FString& Parameters)
{
	using namespace DinkHardnessTest;
	// A physics world with SCR_031's screen volume (an axis-aligned 600 x 400 px screen, 4.375 cm a pixel) and a greybox screen whose baked
	// CollisionSolid is one box over the barrel's hardbox (map 283-320 x 301-322), as the importer's prism there.
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	FAssetCompilingManager::Get().FinishAllCompilation();
	if (!TestNotNull(TEXT("engine cube"), Cube))
	{
		return false;
	}
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
	ADinkScreenVolume* Volume = World->SpawnActor<ADinkScreenVolume>();
	Volume->ScreenNumber = Screen;
	Volume->Corners.NW = FVector2D(0, 0);
	Volume->Corners.NE = FVector2D(26.25, 0);
	Volume->Corners.SW = FVector2D(0, 17.5);
	Volume->Corners.SE = FVector2D(26.25, 17.5);
	Greybox->RegisterScreen(Volume);
	auto At = [Volume](double X, double Y, double Z = 0.0) { return DinkLayout::MapPixelToUnreal(Volume->Corners, X, Y, Z); };
	const FVector BoxMin = At(283, 301), BoxMax = At(320, 322);
	const FVector Centre = (BoxMin + BoxMax) * 0.5;
	ADinkGreyboxScreen* GreyScreen = World->SpawnActorDeferred<ADinkGreyboxScreen>(ADinkGreyboxScreen::StaticClass(), FTransform(FVector(Centre.X, Centre.Y, 150.0)));
	GreyScreen->ScreenNumber = Screen;
	GreyScreen->CollisionSolid->SetStaticMesh(Cube);
	GreyScreen->CollisionSolid->SetRelativeScale3D(FVector(FMath::Abs(BoxMax.X - BoxMin.X) / 100.0, FMath::Abs(BoxMax.Y - BoxMin.Y) / 100.0, 3.0));
	GreyScreen->FinishSpawning(FTransform(FVector(Centre.X, Centre.Y, 150.0)));

	FEnv E = Make(*this, GI);
	if (!E.IsValid())
	{
		GI->Shutdown();
		return false;
	}
	E.Story->bRunScreenScripts = true;
	// A horizontal trace at 1.5 m through the middle of a hardbox, west to east (the pawn's own walk is a capsule sweep against the same mesh).
	auto Blocked = [World](const FVector& From, const FVector& To)
	{
		FHitResult Hit;
		return World->LineTraceSingleByChannel(Hit, From + FVector(0, 0, 150), To + FVector(0, 0, 150), ECC_Pawn);
	};
	const FVector BarrelWest = At(270, 311), BarrelEast = At(335, 311);
	const FVector PigWest = At(265, 97), PigEast = At(330, 97);
	TestTrue(TEXT("the baked collision blocks across the barrel"), Blocked(BarrelWest, BarrelEast));
	TestFalse(TEXT("nothing blocks across the pig"), Blocked(PigWest, PigEast));

	const int32 Barrel = E.D->HandleForPlacement(Screen, BarrelIndex);
	E.Story->StartProcedure(TEXT("bar-gh"), TEXT("hit"), Barrel, {}, Screen);
	E.Story->RunUntilIdle();
	UPrimitiveComponent* Runtime = Greybox->GetRuntimeSolidCollision(Screen);
	TestNotNull(TEXT("draw_hard_sprite gave the screen a runtime solid collision"), Runtime);
	TestEqual(TEXT("the baked one is off"), static_cast<int32>(GreyScreen->CollisionSolid->GetCollisionEnabled()), static_cast<int32>(ECollisionEnabled::NoCollision));
	TestFalse(TEXT("the barrel made soft: nothing blocks across it any more"), Blocked(BarrelWest, BarrelEast));
	FHitResult Ground;
	TestTrue(TEXT("the runtime mesh has the ground"), World->LineTraceSingleByChannel(Ground, At(100, 100, 2.0), At(100, 100, -2.0), ECC_Pawn) && Ground.GetComponent() == Runtime);

	const int32 Pig = E.D->HandleForPlacement(Screen, PigIndex);
	Run(E, Pig, { FString::Printf(TEXT("sp_hard %d 0"), Pig), FString::Printf(TEXT("draw_hard_sprite %d"), Pig) });
	TestTrue(TEXT("the pig made hard: its prism blocks"), Blocked(PigWest, PigEast));
	TestFalse(TEXT("the barrel stays soft"), Blocked(BarrelWest, BarrelEast));

	E.Story->OnScreenEntered(Screen + 1);
	TestNull(TEXT("a screen load removes the runtime collision"), Greybox->GetRuntimeSolidCollision(Screen));
	TestTrue(TEXT("and gives the baked one back"), Blocked(BarrelWest, BarrelEast));
	TestFalse(TEXT("the pig is soft again"), Blocked(PigWest, PigEast));

	// Back on the screen: bar-gh saved editor_type 3 for the barrel, so place_sprites_game does not stamp it (update_play_changes, D:5974,
	// 5792-5798) and the pawn walks through where it stood, as in the original (pitfall 77, fixed 14 Nov 2026).
	E.Story->OnScreenEntered(Screen);
	E.Story->RunUntilIdle();
	TestFalse(TEXT("the next visit: the flattened barrel does not block the pawn"), Blocked(BarrelWest, BarrelEast));
	TestNotNull(TEXT("through a runtime collision built from the loaded map"), Greybox->GetRuntimeSolidCollision(Screen));
	TestFalse(TEXT("the pig (map.dat hard 1) stays soft"), Blocked(PigWest, PigEast));
	// A placement removed for good (editor_type 1) is never stamped (D:5784, 5974): its baked box leaves the pawn's collision on load too.
	E.World->SetOverride(FDinkOriginId(Screen, BarrelIndex), EDinkOverrideType::RemovedForever);
	E.Story->OnScreenEntered(Screen + 1);
	E.Story->OnScreenEntered(Screen);
	E.Story->RunUntilIdle();
	TestFalse(TEXT("a removed barrel does not block the pawn"), Blocked(BarrelWest, BarrelEast));
	E.World->SetOverride(FDinkOriginId(Screen, BarrelIndex), EDinkOverrideType::None);
	E.Story->OnScreenEntered(Screen + 1);
	E.Story->OnScreenEntered(Screen);
	E.Story->RunUntilIdle();
	TestTrue(TEXT("without play changes the baked collision is back"), Blocked(BarrelWest, BarrelEast));
	TestNull(TEXT("and no runtime collision is built"), Greybox->GetRuntimeSolidCollision(Screen));

	Greybox->UnregisterScreen(Volume);
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}
