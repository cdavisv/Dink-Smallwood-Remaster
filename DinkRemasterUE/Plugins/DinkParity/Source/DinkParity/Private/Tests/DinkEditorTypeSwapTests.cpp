// Dink.Gameplay.EditorTypeSwap.*: the save's editor_type 2-5 swap a placement between live sprite and background on legacy (untagged)
// screens, as update_play_changes (dink.cpp:5773-5832) rewrites the screen's sprite table before place_sprites_game reads it (5974):
//
//  - 2 -> type 1, hard 1 (5787-5791); 3 -> type 0, hard 1 (5792-5798); 4 -> type 1, hard 0 (5801-5805); 5 -> type 0, hard 0 (5807-5811);
//    for every nonzero type seq and frame come from the save and the script is cleared (5829-5831).
//  - place_sprites_game then draws type 0 (and 2) placements into the background, stamping a hard one's box as 100 + its index
//    (6036-6054), and makes type 1 placements live sprites with the rewritten hard flag and picture (6083-6132).
//  - draw_hard_sprite and draw_hard_map run update_play_changes first (8096, 8228), so a draw during the visit reads the same rewritten table:
//    fill_back_sprites (6832-6895) stamps background placements, fill_hard_sprites (6972-7031) live ones.
//
// Headless (no world, so every screen takes the legacy path): SCR_662's P2 (type 0 in map.dat, seq 179/1, hard 0, engine 404,259) and
// SCR_031's barrel P03 (type 1, bar-gh, seq 173/1, hard 0, engine 320,316). The save is written by the DinkC commands themselves.

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkStorySubsystem.h"
#include "DinkWorldStateSubsystem.h"

namespace DinkEditorTypeSwapTest
{
	constexpr int32 BackScreen = 662;
	constexpr int32 BackIndex = 2;   // S662_P02: type 0, seq 179 frame 1, hard 0, engine 404,259
	constexpr int32 LiveScreen = 31;
	constexpr int32 LiveIndex = 3;   // S031_P03: type 1, bar-gh, seq 173 frame 1, hard 0, engine 320,316

	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* G = nullptr;
		bool IsValid() const
		{
			return Story && Story->IsReady() && G && G->HasData() && G->GetData().GetTileHardness(BackScreen) && G->GetData().GetTileHardness(LiveScreen);
		}
	};

	FEnv Make(FAutomationTestBase& Test, int32 Screen)
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
		Test.TestTrue(TEXT("gameplay data with the tile layers of SCR_662 and SCR_031 (Scripts/sync_gameplay_data.py)"), E.IsValid());
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

	/** Runs DinkC command lines (as the converted story emits them) in a script instance on Screen. */
	void Run(FEnv& E, int32 Screen, const TArray<FString>& Commands)
	{
		const int32 Id = E.Story->StartProcedure(TEXT("pdie"), TEXT("main"), 1, {}, Screen, /*bNewInstance*/ true);
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

	/** Leaves Screen and comes back: load_map and place_sprites_game again. */
	void Revisit(FEnv& E, int32 Screen)
	{
		E.Story->OnScreenEntered(Screen == LiveScreen ? BackScreen : LiveScreen);
		E.Story->RunUntilIdle();
		E.Story->OnScreenEntered(Screen);
		E.Story->RunUntilIdle();
	}

	/** The active sprite born from the placement, or null. */
	const FDinkSprite* SpriteFor(const FEnv& E, const FDinkOriginId& Origin)
	{
		for (const TPair<int32, FDinkSprite>& Pair : E.D->GetSprites())
		{
			if (Pair.Value.bActive && Pair.Value.Origin == Origin)
			{
				return &Pair.Value;
			}
		}
		return nullptr;
	}

	/** The screen's map as GetHard reads it now (the redrawn or play-changed map if there is one, else the loaded one). */
	TArray<uint8> MapNow(const FEnv& E, int32 Screen)
	{
		if (const FDinkHardnessMap* Live = E.G->GetLiveHardness(Screen))
		{
			return Live->Codes;
		}
		const FDinkHardnessMap* Loaded = E.G->GetData().GetHardness(Screen, E.Facts->GetFact(TEXT("vision")));
		return Loaded ? Loaded->Codes : TArray<uint8>();
	}

	int32 Count(const TArray<uint8>& Codes, int32 Code)
	{
		int32 N = 0;
		for (const uint8 C : Codes)
		{
			N += C == Code;
		}
		return N;
	}

	int32 Differ(const TArray<uint8>& A, const TArray<uint8>& B, FString& First)
	{
		int32 N = A.Num() == B.Num() ? 0 : 1;
		for (int32 i = 0; i < FMath::Min(A.Num(), B.Num()); ++i)
		{
			if (A[i] != B[i] && N++ == 0)
			{
				First = FString::Printf(TEXT("map %d,%d: %d vs %d"), i % FDinkHardnessMap::Width, i / FDinkHardnessMap::Width, A[i], B[i]);
			}
		}
		return N;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkEditorTypeSwap4Test, "Dink.Gameplay.EditorTypeSwap.Type4MakesBackgroundLive", DINK_TEST_FLAGS)
bool FDinkEditorTypeSwap4Test::RunTest(const FString& Parameters)
{
	using namespace DinkEditorTypeSwapTest;
	FEnv E = Make(*this, BackScreen);
	if (!E.IsValid())
	{
		return false;
	}
	const FDinkOriginId Origin(BackScreen, BackIndex);
	TestNull(TEXT("map.dat's type 0 placement is background: no sprite"), SpriteFor(E, Origin));
	TestEqual(TEXT("its hardbox is stamped on load (hard 0: 102)"), E.G->GetHard(BackScreen, 404, 259), 102);

	// editor_type 4 with the picture 179/2 (box -47..46 x -20..14 instead of 179/1's -64..58 x -25..12).
	Run(E, BackScreen, { FString::Printf(TEXT("editor_type %d 4"), BackIndex), FString::Printf(TEXT("editor_seq %d 179"), BackIndex),
		FString::Printf(TEXT("editor_frame %d 2"), BackIndex) });
	Revisit(E, BackScreen);

	// update_play_changes D:5801-5805 (type 1, hard 0) and 5829-5830 (seq, frame), then place_sprites_game D:6083: a live sprite.
	const FDinkSprite* S = SpriteFor(E, Origin);
	if (TestNotNull(TEXT("saved editor_type 4 makes the background placement a live sprite on the next visit (dink.cpp:5801-5805, 6083)"), S))
	{
		TestEqual(TEXT("born with the rewritten hard flag 0 (D:5804, 6097)"), S->GetProp(TEXT("hard"), 1), 0);
		TestEqual(TEXT("and the saved picture: pseq 179 (D:5829)"), S->GetProp(TEXT("pseq")), 179);
		TestEqual(TEXT("pframe 2 (D:5830)"), S->GetProp(TEXT("pframe")), 2);
		TestEqual(TEXT("its script is cleared (D:5831)"), S->Script, FName());
	}
	TestEqual(TEXT("its hardbox is stamped at load (D:6129-6132): 102 at its centre"), E.G->GetHard(BackScreen, 404, 259), 102);
	TestEqual(TEXT("179/1's box is gone where 179/2's is not (engine 345,259: map x 325)"), E.G->GetHard(BackScreen, 345, 259) == 102, false);
	const TArray<uint8> AtLoad = MapNow(E, BackScreen);

	// draw_hard_map (D:8224-8232): update_play_changes, the tile layer, fill_hard_sprites (the live sprite, its map flag 0) and fill_back_sprites
	// (which skips it: type 1 now). The rebuilt map is the one the screen loaded with.
	Run(E, BackScreen, { TEXT("draw_hard_map") });
	FString First;
	const TArray<uint8> AfterDraw = MapNow(E, BackScreen);
	TestEqual(TEXT("draw_hard_map keeps the live placement's box (102 at its centre)"), E.G->GetHard(BackScreen, 404, 259), 102);
	const int32 Changed = Differ(AfterDraw, AtLoad, First);
	TestEqual(FString::Printf(TEXT("draw_hard_map rebuilds the map the screen loaded with (%s)"), *First), Changed, 0);
	TestTrue(TEXT("the box is stamped (some pixels of 102)"), Count(AfterDraw, 102) > 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkEditorTypeSwap2Test, "Dink.Gameplay.EditorTypeSwap.Type2MakesBackgroundLiveSoft", DINK_TEST_FLAGS)
bool FDinkEditorTypeSwap2Test::RunTest(const FString& Parameters)
{
	using namespace DinkEditorTypeSwapTest;
	FEnv E = Make(*this, BackScreen);
	if (!E.IsValid())
	{
		return false;
	}
	const FDinkOriginId Origin(BackScreen, BackIndex);
	Run(E, BackScreen, { FString::Printf(TEXT("editor_type %d 2"), BackIndex), FString::Printf(TEXT("editor_seq %d 179"), BackIndex),
		FString::Printf(TEXT("editor_frame %d 1"), BackIndex) });
	Revisit(E, BackScreen);

	// update_play_changes D:5787-5791: type 1, hard 1. A live sprite without hardness.
	const FDinkSprite* S = SpriteFor(E, Origin);
	if (TestNotNull(TEXT("saved editor_type 2 makes the background placement a live sprite on the next visit (dink.cpp:5787-5791, 6083)"), S))
	{
		TestEqual(TEXT("born with the rewritten hard flag 1 (D:5790)"), S->GetProp(TEXT("hard"), 0), 1);
		TestEqual(TEXT("pseq 179 (D:5829)"), S->GetProp(TEXT("pseq")), 179);
		TestEqual(TEXT("pframe 1 (D:5830)"), S->GetProp(TEXT("pframe")), 1);
	}
	TestEqual(TEXT("its box is not stamped at load: no 102 anywhere"), Count(MapNow(E, BackScreen), 102), 0);
	Run(E, BackScreen, { TEXT("draw_hard_map") });
	TestEqual(TEXT("nor after draw_hard_map (fill_hard_sprites: flag 1; fill_back_sprites: type 1)"), Count(MapNow(E, BackScreen), 102), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkEditorTypeSwap3Test, "Dink.Gameplay.EditorTypeSwap.Type3DrawsLiveIntoBackground", DINK_TEST_FLAGS)
bool FDinkEditorTypeSwap3Test::RunTest(const FString& Parameters)
{
	using namespace DinkEditorTypeSwapTest;
	FEnv E = Make(*this, LiveScreen);
	if (!E.IsValid())
	{
		return false;
	}
	const FDinkOriginId Origin(LiveScreen, LiveIndex);
	TestNotNull(TEXT("map.dat's barrel (type 1) is a live sprite"), SpriteFor(E, Origin));
	TestEqual(TEXT("its hardbox is stamped on load (103)"), E.G->GetHard(LiveScreen, 320, 316), 103);

	// bar-gh.c `hit`: editor_type 3, editor_seq 173, editor_frame 6 (the flat barrel).
	Run(E, LiveScreen, { FString::Printf(TEXT("editor_type %d 3"), LiveIndex), FString::Printf(TEXT("editor_seq %d 173"), LiveIndex),
		FString::Printf(TEXT("editor_frame %d 6"), LiveIndex) });
	Revisit(E, LiveScreen);

	// update_play_changes D:5792-5798 (type 0, hard 1), place_sprites_game D:6036-6054: drawn into the background, never a sprite.
	TestNull(TEXT("saved editor_type 3 draws the live barrel into the background on the next visit: no sprite (dink.cpp:5792-5798, 6036)"), SpriteFor(E, Origin));
	int32 BarGh = 0;
	for (const TUniquePtr<FDinkScriptInstance>& I : E.Story->GetInstances())
	{
		BarGh += I->IsAlive() && I->Script == FName(TEXT("bar-gh")) ? 1 : 0;
	}
	TestEqual(TEXT("so no bar-gh instance runs"), BarGh, 0);
	TestEqual(TEXT("hard 1: its box is not stamped at load"), E.G->GetHard(LiveScreen, 320, 316), 0);
	TestEqual(TEXT("no pixel of 103 at load"), Count(MapNow(E, LiveScreen), 103), 0);
	Run(E, LiveScreen, { TEXT("draw_hard_map") });
	TestEqual(TEXT("nor after draw_hard_map (fill_back_sprites: flag 1)"), Count(MapNow(E, LiveScreen), 103), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkEditorTypeSwap5Test, "Dink.Gameplay.EditorTypeSwap.Type5DrawsLiveIntoBackgroundHard", DINK_TEST_FLAGS)
bool FDinkEditorTypeSwap5Test::RunTest(const FString& Parameters)
{
	using namespace DinkEditorTypeSwapTest;
	FEnv E = Make(*this, LiveScreen);
	if (!E.IsValid())
	{
		return false;
	}
	const FDinkOriginId Origin(LiveScreen, LiveIndex);
	// editor_type 5 with the picture 443/7 (box -26..33 x -16..6; the barrel's 173/1 is -17..20 x -15..6). The override's Variant keeps only
	// the last command ("frame7"); the save keeps both, and update_play_changes takes both (D:5829-5830).
	Run(E, LiveScreen, { FString::Printf(TEXT("editor_type %d 5"), LiveIndex), FString::Printf(TEXT("editor_seq %d 443"), LiveIndex),
		FString::Printf(TEXT("editor_frame %d 7"), LiveIndex) });
	Revisit(E, LiveScreen);

	// update_play_changes D:5807-5811 (type 0, hard 0), place_sprites_game D:6036-6054: background, its box stamped as 103.
	TestNull(TEXT("saved editor_type 5 draws the live barrel into the background on the next visit: no sprite (dink.cpp:5807-5811, 6036)"), SpriteFor(E, Origin));
	TestEqual(TEXT("hard 0: its box is stamped at load (D:6050-6054)"), E.G->GetHard(LiveScreen, 320, 316), 103);
	TestEqual(TEXT("with the saved picture's box: 443/7 reaches engine x 352 (173/1 ends at 340)"), E.G->GetHard(LiveScreen, 350, 316), 103);
	const TArray<uint8> AtLoad = MapNow(E, LiveScreen);

	// draw_hard_map (D:8224-8232) runs update_play_changes first: fill_back_sprites stamps the background barrel with the save's seq and
	// frame (443/7), not map.dat's seq with the Variant's frame.
	Run(E, LiveScreen, { TEXT("draw_hard_map") });
	FString First;
	const int32 Changed = Differ(MapNow(E, LiveScreen), AtLoad, First);
	TestEqual(FString::Printf(TEXT("draw_hard_map rebuilds the map the screen loaded with (%s)"), *First), Changed, 0);
	TestEqual(TEXT("the background barrel's box is still 443/7's after the draw"), E.G->GetHard(LiveScreen, 350, 316), 103);
	return true;
}
