// Dink.Gameplay.*: the original engine's rules that run script procedures from play (hit, touch, push,
// damage and death, drops, pickups, items and magic, the 100 ms status update), on the converted story.
//
// Headless: screens are entered without a world, so map.dat's live placements become virtual sprites
// (Content/Dink/Data/Gameplay, Scripts/sync_gameplay_data.py) and their scripts run as in the game.
// Expected texts are verbatim from bin/dink/story/<script>.c and are checked against those files when
// the data repo is next to the project.

#include "DinkTestHelpers.h"
#include "DinkCombat.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkInventoryComponent.h"
#include "DinkRandom.h"
#include "DinkSaveGame.h"
#include "DinkStorySubsystem.h"
#include "DinkLayout.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace DinkGameplayTest
{
	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* G = nullptr;
		bool IsValid() const { return Facts && World && Story && Story->IsReady() && G && G->HasData(); }
	};

	/** Story, facts and world state outside any world, instant mode (blocks complete at once), seeded. */
	FEnv Make(FAutomationTestBase& Test, int32 Seed = 1997)
	{
		FEnv E;
		UGameInstance* GI = DinkTest::MakeOuterGameInstance();
		E.Facts = NewObject<UDinkFactSubsystem>(GI);
		FString Error;
		Test.TestTrue(TEXT("facts table loads"), E.Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
		E.World = NewObject<UDinkWorldStateSubsystem>(GI);
		E.Story = NewObject<UDinkStorySubsystem>(GI);
		Test.TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), E.Story->SetupStandalone(E.Facts, E.World, &Error));
		E.Story->StorySeed = Seed;
		E.Story->ResetRuntime();
		E.Story->bInstantMode = true;
		E.D = E.Story->GetDirector();
		E.G = E.Story->GetGameplay();
		Test.TestTrue(TEXT("gameplay data loaded (Scripts/sync_gameplay_data.py)"), E.G && E.G->HasData());
		return E;
	}

	/** Game time in 60 Hz engine frames (the brains think per frame). */
	void RunFor(FEnv& E, double Seconds)
	{
		const int32 Frames = FMath::CeilToInt32(Seconds * 60.0 - 1e-6);
		for (int32 i = 0; i < Frames; ++i)
		{
			E.Story->Advance(1.0 / 60.0);
		}
	}

	void Settle(FEnv& E)
	{
		E.Story->RunUntilIdle();
		E.G->ProcessDamage();
		E.Story->RunUntilIdle();
	}

	void NewGame(FEnv& E)
	{
		E.G->StartNewGame();
		Settle(E);
	}

	void Enter(FEnv& E, int32 Screen)
	{
		E.Story->OnScreenEntered(Screen);
		Settle(E);
	}

	/** Dink west of the sprite's hardbox by Gap pixels, level with it, facing Dir. */
	void StandWestOf(FEnv& E, int32 Handle, int32 Gap = 20, int32 Dir = 6)
	{
		const FDinkSprite* T = E.D->FindSprite(Handle);
		int32 L = 0, Tp = 0, R = 0, B = 0;
		if (T && E.G->GetHardbox(*T, L, Tp, R, B))
		{
			FDinkSprite& Dink = E.D->GetDink();
			Dink.Screen = T->Screen;
			Dink.X = L - Gap;
			Dink.Y = T->Y;
			Dink.Dir = Dir;
		}
	}

	void StandOn(FEnv& E, int32 Handle)
	{
		const FDinkSprite* T = E.D->FindSprite(Handle);
		FDinkSprite& Dink = E.D->GetDink();
		if (T)
		{
			Dink.Screen = T->Screen;
			Dink.X = T->X;
			Dink.Y = T->Y;
		}
	}

	void Attack(FEnv& E)
	{
		E.G->PlayerAttack();
		Settle(E);
	}

	TArray<FString> Said(const UDinkStorySubsystem* S, int32 From = 0)
	{
		TArray<FString> Out;
		for (int32 i = From; i < S->Events.Num(); ++i)
		{
			if (S->Events[i].Kind == TEXT("say"))
			{
				Out.Add(S->Events[i].Text);
			}
		}
		return Out;
	}

	int32 FindByScript(const FEnv& E, const TCHAR* Script, bool bActiveOnly = true)
	{
		for (const TPair<int32, FDinkSprite>& Pair : E.D->GetSprites())
		{
			if (Pair.Value.Script == FName(Script) && (!bActiveOnly || Pair.Value.bActive))
			{
				return Pair.Key;
			}
		}
		return 0;
	}

	int32 CountByScript(const FEnv& E, const TCHAR* Script)
	{
		int32 N = 0;
		for (const TPair<int32, FDinkSprite>& Pair : E.D->GetSprites())
		{
			N += Pair.Value.Script == FName(Script) && Pair.Value.bActive && Pair.Value.bSpawned ? 1 : 0;
		}
		return N;
	}

	void CheckOriginal(FAutomationTestBase& Test, const TCHAR* Script, const TArray<FString>& Strings)
	{
		const FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("../Dink-Smallwood-Remaster/bin/dink/story") / (FString(Script) + TEXT(".c")));
		FString Source;
		if (!FFileHelper::LoadFileToString(Source, *Path))
		{
			Test.AddInfo(FString::Printf(TEXT("data repo not found (%s): verbatim check skipped"), *Path));
			return;
		}
		for (const FString& S : Strings)
		{
			Test.TestTrue(FString::Printf(TEXT("\"%s\" occurs verbatim in %s.c"), *S, Script), Source.Contains(S, ESearchCase::CaseSensitive));
		}
	}

	/** Answers menus by option text (instant mode). */
	void ChooseByText(FEnv& E, TArray<FString> Answers)
	{
		E.Story->AutoChooser = [Answers](const FDinkMenu& Menu) mutable
		{
			for (int32 a = 0; a < Answers.Num(); ++a)
			{
				for (int32 i = 0; i < Menu.Choices.Num(); ++i)
				{
					if (Menu.Choices[i].Text == Answers[a])
					{
						Answers.RemoveAt(a);
						return i;
					}
				}
			}
			return Menu.Choices.Num() - 1;
		};
	}
}

using namespace DinkGameplayTest;

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayHitSceneryTest, "Dink.Gameplay.Hit.SceneryLines", DINK_TEST_FLAGS)
bool FDinkGameplayHitSceneryTest::RunTest(const FString& Parameters)
{
	// Fists (newgame.c), then the attack key next to Stonebrook furniture with a `hit` procedure.
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	NewGame(E);
	TestEqual(TEXT("newgame: fists in slot 1"), E.D->GetInventory()->GetItemAt(0), FName(TEXT("item-fst")));
	TestEqual(TEXT("newgame: fists armed"), E.D->GetInventory()->GetArmedItem(), FName(TEXT("item-fst")));
	TestTrue(TEXT("weapon script instance alive"), E.G->GetWeaponInstance() != 0);

	// SCR_002, Ethel's house: S002_P21 (s1-h2-1.c, a smelly thing) and SCR_003 S003_P16 (s1-h3-1.c, a table).
	Enter(E, 2);
	const int32 Smelly = E.D->HandleForPlacement(2, 21);
	TestEqual(TEXT("S002_P21 carries s1-h2-1"), E.D->FindSprite(Smelly) ? E.D->FindSprite(Smelly)->Script : NAME_None, FName(TEXT("s1-h2-1")));

	// Facing away (west) from 20 px west of it: the reach is on the wrong side, nothing happens.
	StandWestOf(E, Smelly, 20, 4);
	int32 From = E.Story->Events.Num();
	Attack(E);
	TestFalse(TEXT("facing away: no hit line"), Said(E.Story, From).Contains(TEXT("You smell, therefore you die!!!")));

	// Facing it (east): within 28 px + 5 of its hardbox.
	StandWestOf(E, Smelly, 20, 6);
	From = E.Story->Events.Num();
	Attack(E);
	TestTrue(TEXT("hit: s1-h2-1 `hit` says its line"), Said(E.Story, From).Contains(TEXT("You smell, therefore you die!!!")));
	TestEqual(TEXT("&missle_source = Dink"), E.Facts->GetFact(TEXT("missle_source")), 1);
	TestEqual(TEXT("&enemy_sprite = Dink"), E.Facts->GetFact(TEXT("enemy_sprite")), 1);

	// Out of reach (40 px away: fists reach 28 + 5).
	StandWestOf(E, Smelly, 40, 6);
	From = E.Story->Events.Num();
	Attack(E);
	TestFalse(TEXT("40 px away: out of the fists' reach"), Said(E.Story, From).Contains(TEXT("You smell, therefore you die!!!")));

	Enter(E, 3);
	const int32 Table = E.D->HandleForPlacement(3, 16);
	StandWestOf(E, Table, 10, 6);
	From = E.Story->Events.Num();
	Attack(E);
	TestTrue(TEXT("hit: s1-h3-1 `hit` says its line"), Said(E.Story, From).Contains(TEXT("Stupid table!")));
	CheckOriginal(*this, TEXT("s1-h2-1"), { TEXT("You smell, therefore you die!!!") });
	CheckOriginal(*this, TEXT("s1-h3-1"), { TEXT("Stupid table!") });
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayPillbugTest, "Dink.Gameplay.Combat.PillbugDiesAndDrops", DINK_TEST_FLAGS)
bool FDinkGameplayPillbugTest::RunTest(const FString& Parameters)
{
	// en-pill.c: main sets brain 9, 8 hitpoints, touch damage 1, exp 5; die sets editor_type 6 and runs
	// emake.small (random(3,1) == 1: a small heart, otherwise nothing).
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	NewGame(E);
	Enter(E, 278);
	const FDinkOriginId Origin(278, 4);
	int32 Bug = E.D->HandleForPlacement(278, 4);
	const FDinkSprite* S = E.D->FindSprite(Bug);
	if (!TestNotNull(TEXT("pillbug S278_P04"), S))
	{
		return false;
	}
	TestEqual(TEXT("en-pill main: brain 9"), S->GetProp(TEXT("brain")), 9);
	TestEqual(TEXT("en-pill main: 8 hitpoints"), S->GetProp(TEXT("hitpoints")), 8);
	TestEqual(TEXT("en-pill main: exp 5"), S->GetProp(TEXT("exp")), 5);
	TestEqual(TEXT("en-pill main: touch damage 1"), S->GetProp(TEXT("touch_damage")), 1);
	const int32 BugX = FMath::RoundToInt32(S->X), BugY = FMath::RoundToInt32(S->Y);

	int32 Attacks = 0;
	while (Attacks < 12 && E.D->FindSprite(Bug) && E.D->FindSprite(Bug)->bActive)
	{
		StandWestOf(E, Bug);
		Attack(E);
		++Attacks;
	}
	TestTrue(FString::Printf(TEXT("dead after %d fist hits (2-3 each at strength 3)"), Attacks), Attacks >= 3 && Attacks <= 4);
	TestEqual(TEXT("exp 5 for the kill (add_exp: Dink dealt the last hit)"), E.Facts->GetFact(TEXT("exp")), 5);
	TestEqual(TEXT("die: editor_type(4, 6) -> S278_P04 back in 5 minutes"), E.World->GetOverrideType(Origin), EDinkOverrideType::RemovedReturn5Min);
	TestEqual(TEXT("die: &save_x = its x"), E.Facts->GetFact(TEXT("save_x")), BugX);
	TestEqual(TEXT("die: &save_y = its y"), E.Facts->GetFact(TEXT("save_y")), BugY);
	TestTrue(TEXT("die ran"), E.G->Events.ContainsByPredicate([](const FString& Ev) { return Ev.StartsWith(TEXT("die ")) && Ev.Contains(TEXT("en-pill")); }));

	// Many seeded kills: emake.small gives a small heart one time in three, nothing else.
	int32 Hearts = 0, Others = 0;
	const int32 Kills = 300;
	for (int32 k = 0; k < Kills; ++k)
	{
		E.World->ClearOverride(Origin);
		Enter(E, 279);
		E.G->SetRandomSeed(static_cast<int32>(GetTypeHash(FString::Printf(TEXT("pillbug kill %d"), k))));
		Enter(E, 278);
		Bug = E.D->HandleForPlacement(278, 4);
		for (int32 a = 0; a < 12 && E.D->FindSprite(Bug) && E.D->FindSprite(Bug)->bActive; ++a)
		{
			StandWestOf(E, Bug);
			Attack(E);
		}
		const int32 Heart = FindByScript(E, TEXT("sheart"));
		Hearts += Heart != 0 ? 1 : 0;
		for (const TPair<int32, FDinkSprite>& Pair : E.D->GetSprites())
		{
			Others += (Pair.Value.bSpawned && Pair.Value.bActive && !Pair.Value.bText && Pair.Value.Script != FName(TEXT("sheart")) && !Pair.Value.Script.IsNone()) ? 1 : 0;
		}
		if (Heart && k == 0)
		{
			const FDinkSprite* H = E.D->FindSprite(Heart);
			TestEqual(TEXT("the heart lies where the bug died (x)"), FMath::RoundToInt32(H->X), E.Facts->GetFact(TEXT("save_x")));
		}
	}
	AddInfo(FString::Printf(TEXT("emake.small over %d seeded kills: %d small hearts (expected 1/3 = %d)"), Kills, Hearts, Kills / 3));
	TestTrue(TEXT("small hearts within 1/3 +- 4 sigma (100 +- 33)"), Hearts >= 67 && Hearts <= 133);
	TestEqual(TEXT("no other drop from emake.small"), Others, 0);
	CheckOriginal(*this, TEXT("en-pill"), { TEXT("sp_exp(&current_sprite, 5);"), TEXT("editor_type(&hold, 6);"), TEXT("external(\"emake\",\"small\");") });
	CheckOriginal(*this, TEXT("emake"), { TEXT("int &mcrap = random(3,1);") });
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayDropTableTest, "Dink.Gameplay.Combat.DropTableOdds", DINK_TEST_FLAGS)
bool FDinkGameplayDropTableTest::RunTest(const FString& Parameters)
{
	// emake.medium: random(20,1): 1 small heart, 2 heart, 3 food (random(3,1): frames 1, 2, 7; the
	// frame-8 branch needs 4 and never runs), 4-20 mgold. 2000 seeded runs.
	FEnv E = Make(*this, 77);
	if (!E.IsValid())
	{
		return false;
	}
	E.Facts->SetFact(TEXT("save_x"), 300);
	E.Facts->SetFact(TEXT("save_y"), 200);
	TMap<FString, int32> Count;
	TSet<int32> FoodFrames;
	const int32 Runs = 2000;
	for (int32 k = 0; k < Runs; ++k)
	{
		const int32 Host = E.D->CreateVirtualSprite(1, 300, 200);
		E.Story->StartProcedure(TEXT("emake"), TEXT("medium"), Host, {}, 1, true);
		E.Story->RunUntilIdle();
		for (const TPair<int32, FDinkSprite>& Pair : E.D->GetSprites())
		{
			if (Pair.Value.bSpawned && !Pair.Value.Script.IsNone() && Pair.Value.Props.Contains(TEXT("pseq")) && Pair.Value.GetProp(TEXT("brain")) == 6)
			{
				Count.FindOrAdd(Pair.Value.Script.ToString())++;
				if (Pair.Value.Script == FName(TEXT("sfood")))
				{
					FoodFrames.Add(Pair.Value.GetProp(TEXT("pframe")));
				}
			}
		}
		E.Story->ResetRuntime();
		E.G->SetRandomSeed(static_cast<int32>(GetTypeHash(FString::Printf(TEXT("emake medium %d"), k))));
	}
	const int32 Small = Count.FindRef(TEXT("sheart")), Big = Count.FindRef(TEXT("heart")), Food = Count.FindRef(TEXT("sfood")), Gold = Count.FindRef(TEXT("mgold"));
	AddInfo(FString::Printf(TEXT("emake.medium x%d: sheart %d, heart %d, sfood %d, mgold %d"), Runs, Small, Big, Food, Gold));
	TestEqual(TEXT("one drop per run"), Small + Big + Food + Gold, Runs);
	// 1/20 of 2000 = 100 (sigma 9.7); 17/20 = 1700 (sigma 16).
	TestTrue(TEXT("small heart ~ 1/20"), Small >= 61 && Small <= 139);
	TestTrue(TEXT("heart ~ 1/20"), Big >= 61 && Big <= 139);
	TestTrue(TEXT("food ~ 1/20"), Food >= 61 && Food <= 139);
	TestTrue(TEXT("gold ~ 17/20"), Gold >= 1636 && Gold <= 1764);
	TestFalse(TEXT("food type 4 (frame 8) never drops: random(3,1) cannot be 4"), FoodFrames.Contains(8));
	TestTrue(TEXT("food types 1-3 (frames 1, 2, 7) seen"), FoodFrames.Contains(1) && FoodFrames.Contains(2) && FoodFrames.Contains(7));

	// random(range, base) is (rand() % range) + base; range 0 gives the base.
	TestEqual(TEXT("random(0, 7) = 7"), E.G->Random(0, 7), 7);
	E.G->SetRandomSource(MakeShared<FDinkScriptedRandomSource>(TArray<int32>{ 45 }));
	TestEqual(TEXT("random(20, 1) with rand() = 45 -> 6"), E.G->Random(20, 1), 6);
	E.G->SetRandomSource(nullptr);
	E.G->SetRandomSeed(123);
	const int32 A = E.G->Random(1000, 0);
	E.G->SetRandomSeed(123);
	TestEqual(TEXT("seeded: same seed, same roll"), E.G->Random(1000, 0), A);
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayPickupTest, "Dink.Gameplay.Touch.GoldAndHeart", DINK_TEST_FLAGS)
bool FDinkGameplayPickupTest::RunTest(const FString& Parameters)
{
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	E.Facts->SetFact(TEXT("save_x"), 300);
	E.Facts->SetFact(TEXT("save_y"), 200);
	E.D->GetDink().Screen = 1;

	// emake.medium with rand() = 5 -> random(20,1) = 6: gold (mgold). mgold main: random(5,1) twice;
	// touch: random(30,5) with rand() = 10 -> 15 gold.
	E.G->SetRandomSource(MakeShared<FDinkScriptedRandomSource>(TArray<int32>{ 5, 0, 0, 10 }));
	const int32 Host = E.D->CreateVirtualSprite(1, 300, 200);
	E.Story->StartProcedure(TEXT("emake"), TEXT("medium"), Host, {}, 1, true);
	E.Story->RunUntilIdle();
	const int32 Gold = FindByScript(E, TEXT("mgold"));
	if (!TestTrue(TEXT("emake.medium dropped mgold"), Gold != 0))
	{
		return false;
	}
	TestEqual(TEXT("mgold main: touch damage -1 (touch runs the script)"), E.D->FindSprite(Gold)->GetProp(TEXT("touch_damage")), -1);
	const int32 GoldBefore = E.Facts->GetFact(TEXT("gold"));
	StandOn(E, Gold);
	int32 From = E.Story->Events.Num();
	E.Story->Advance(0.016);
	E.Story->RunUntilIdle();
	TestEqual(TEXT("touch: &gold += random(30,5) = 15"), E.Facts->GetFact(TEXT("gold")), GoldBefore + 15);
	TestTrue(TEXT("touch: Dink says the amount"), Said(E.Story, From).Contains(TEXT("I found 15 gold.")));
	TestEqual(TEXT("touch damage 0: does not trigger again"), E.D->FindSprite(Gold)->GetProp(TEXT("touch_damage")), 0);
	E.Story->Advance(0.016);
	E.Story->Advance(0.016);
	E.Story->RunUntilIdle();
	TestEqual(TEXT("touched once only"), E.Facts->GetFact(TEXT("gold")), GoldBefore + 15);
	// scale_brain (D:15798): 5 size points per think (base_timing 7 / 4 = 1) from 100 to brain_parm 10, timing 0:
	// 18 frames of shrinking, gone on the 19th.
	TestTrue(TEXT("brain 12: the gold is still shrinking two frames later"), E.D->FindSprite(Gold)->bActive && E.D->FindSprite(Gold)->GetProp(TEXT("size"), 100) < 100);
	RunFor(E, 0.35);
	TestFalse(TEXT("brain 12: the gold shrinks and is gone"), E.D->FindSprite(Gold)->bActive);

	// emake.medium with rand() = 1 -> random(20,1) = 2: a heart. touch: &life = &lifemax.
	E.G->SetRandomSource(MakeShared<FDinkScriptedRandomSource>(TArray<int32>{ 1 }));
	E.Facts->SetFact(TEXT("lifemax"), 10);
	E.Facts->SetFact(TEXT("life"), 3);
	E.Story->StartProcedure(TEXT("emake"), TEXT("medium"), Host, {}, 1, true);
	E.Story->RunUntilIdle();
	const int32 Heart = FindByScript(E, TEXT("heart"));
	if (!TestTrue(TEXT("emake.medium dropped a heart"), Heart != 0))
	{
		return false;
	}
	StandOn(E, Heart);
	E.Story->Advance(0.016);
	E.Story->RunUntilIdle();
	TestEqual(TEXT("heart touch: &life = &lifemax"), E.Facts->GetFact(TEXT("life")), 10);
	RunFor(E, 0.35);
	TestFalse(TEXT("the heart is gone"), E.D->FindSprite(Heart)->bActive);
	CheckOriginal(*this, TEXT("mgold"), { TEXT("int &mcrap = random(30,5);"), TEXT("say(\"I found &mcrap gold.\",1);") });
	CheckOriginal(*this, TEXT("heart"), { TEXT("&life = &lifemax;") });
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayTouchDamageTest, "Dink.Gameplay.Touch.DamageHurtsDink", DINK_TEST_FLAGS)
bool FDinkGameplayTouchDamageTest::RunTest(const FString& Parameters)
{
	// run_through_touch_damage_list: a pillbug (touch damage 1) hurts Dink through his defense, then
	// 400 ms of immunity (dink.cpp D:15660-15668).
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	NewGame(E);
	Enter(E, 278);
	const int32 Bug = E.D->HandleForPlacement(278, 4);
	E.Facts->SetFact(TEXT("life"), 10);
	StandOn(E, Bug);
	E.Story->Advance(0.010);
	TestEqual(TEXT("touch: life 10 -> 9"), E.Facts->GetFact(TEXT("life")), 9);
	E.Story->Advance(0.200);
	TestEqual(TEXT("immune for 400 ms"), E.Facts->GetFact(TEXT("life")), 9);
	E.Story->Advance(0.250);
	TestEqual(TEXT("after 400 ms: hurt again"), E.Facts->GetFact(TEXT("life")), 8);
	// Defense 1 against touch 1: 0, or 1 on the pity roll; never more.
	E.Facts->SetFact(TEXT("defense"), 1);
	int32 Lost = 0;
	for (int32 i = 0; i < 40; ++i)
	{
		E.Facts->SetFact(TEXT("life"), 8);
		E.Story->Advance(0.401);
		Lost += 8 - E.Facts->GetFact(TEXT("life"));
		TestTrue(TEXT("defense 1: at most 1 lost"), 8 - E.Facts->GetFact(TEXT("life")) <= 1);
	}
	TestTrue(FString::Printf(TEXT("pity point about half the time (%d of 40)"), Lost), Lost >= 8 && Lost <= 32);
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayPersistenceTest, "Dink.Gameplay.World.EditorTypePersistence", DINK_TEST_FLAGS)
bool FDinkGameplayPersistenceTest::RunTest(const FString& Parameters)
{
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	NewGame(E);
	// A pig on SCR_407 (brain 4, 10 hitpoints, die.c: editor_type 1 = gone for good).
	Enter(E, 407);
	const FDinkOriginId Pig(407, 2);
	int32 H = E.D->HandleForPlacement(407, 2);
	TestEqual(TEXT("S407_P02 is a pig (brain 4) with die.c"), E.D->FindSprite(H) ? E.D->FindSprite(H)->GetProp(TEXT("brain")) : -1, 4);
	for (int32 a = 0; a < 12 && E.D->FindSprite(H) && E.D->FindSprite(H)->bActive; ++a)
	{
		StandWestOf(E, H);
		Attack(E);
	}
	TestEqual(TEXT("killed pig: editor_type 1"), E.World->GetOverrideType(Pig), EDinkOverrideType::RemovedForever);
	Enter(E, 408);
	Enter(E, 407);
	TestEqual(TEXT("after leaving and coming back: still gone (sp() = 0)"), E.D->HandleForPlacement(407, 2), 0);
	bool bSpritePresent = false;
	for (const TPair<int32, FDinkSprite>& Pair : E.D->GetSprites())
	{
		bSpritePresent |= Pair.Value.Origin == Pig;
	}
	TestFalse(TEXT("no sprite of S407_P02 on re-entry"), bSpritePresent);
	TestTrue(TEXT("its neighbour S407_P05 is back as a sprite"), E.D->HandleForPlacement(407, 5) > 1);

	// Save and load into a fresh session: still gone.
	UDinkSaveGame* Save = NewObject<UDinkSaveGame>(GetTransientPackage());
	FDinkSaveContext Ctx;
	Ctx.Facts = E.Facts;
	Ctx.WorldState = E.World;
	Save->CaptureFrom(Ctx);
	E.Story->CaptureToSave(Save);
	TArray<uint8> Bytes;
	TestTrue(TEXT("save serialises"), UDinkSaveGame::SaveToBytes(Save, Bytes));
	FEnv F = Make(*this);
	UDinkSaveGame* Loaded = UDinkSaveGame::LoadFromBytes(Bytes);
	FDinkSaveContext CtxB;
	CtxB.Facts = F.Facts;
	CtxB.WorldState = F.World;
	TestTrue(TEXT("save applies"), Loaded && Loaded->ApplyTo(CtxB));
	F.Story->RestoreFromSave(Loaded);
	Enter(F, 406);
	Enter(F, 407);
	TestEqual(TEXT("after load: the pig is still gone"), F.D->HandleForPlacement(407, 2), 0);

	// Respawning types: the timer starts when the player leaves the screen (fix_dead_sprites, D:917-959).
	struct FCase { FDinkOriginId Origin; int32 Type; int64 DelayMs; };
	const FCase Cases[] = { { FDinkOriginId(278, 4), 6, 300000 }, { FDinkOriginId(278, 5), 7, 180000 }, { FDinkOriginId(279, 5), 8, 60000 } };
	for (const FCase& C : Cases)
	{
		FEnv R = Make(*this);
		NewGame(R);
		R.World->SetGameTimeMs(10000);
		Enter(R, C.Origin.Screen);
		const int32 Sprite = R.D->HandleForPlacement(C.Origin.Screen, C.Origin.Placement);
		if (C.Type == 6)
		{
			// The real path: kill it (en-pill.c die: editor_type 6).
			for (int32 a = 0; a < 12 && R.D->FindSprite(Sprite) && R.D->FindSprite(Sprite)->bActive; ++a)
			{
				StandWestOf(R, Sprite);
				Attack(R);
			}
		}
		else
		{
			// A script's editor_type(N, type) on that screen.
			const int32 Id = R.Story->StartProcedure(TEXT("en-pill"), TEXT("hit"), Sprite, {}, C.Origin.Screen);
			const FDinkStoryLine L = FDinkStoryLine::Parse(FString::Printf(TEXT(">> editor_type %d %d"), C.Origin.Placement, C.Type), { TEXT("cmd"), TEXT("src:1") });
			R.D->Execute(*R.Story->FindInstance(Id), L);
		}
		const FString What = FString::Printf(TEXT("%s type %d"), *C.Origin.ToString(), C.Type);
		TestEqual(What + TEXT(": override set"), static_cast<int32>(R.World->GetOverrideType(C.Origin)), C.Type);
		R.World->SetGameTimeMs(20000);
		Enter(R, C.Origin.Screen == 278 ? 279 : 278); // leave: exit time 20000
		R.World->SetGameTimeMs(20000 + C.DelayMs);
		Enter(R, C.Origin.Screen);
		TestEqual(What + TEXT(": not back at exactly the delay"), R.D->HandleForPlacement(C.Origin.Screen, C.Origin.Placement), 0);
		R.World->SetGameTimeMs(20000 + C.DelayMs + 5);
		Enter(R, C.Origin.Screen == 278 ? 279 : 278); // leave again: the timer restarts at this exit
		R.World->SetGameTimeMs(20000 + C.DelayMs + 5 + C.DelayMs + 1);
		Enter(R, C.Origin.Screen);
		const int32 Back = R.D->HandleForPlacement(C.Origin.Screen, C.Origin.Placement);
		TestTrue(What + TEXT(": back 1 ms after the delay since the last exit"), Back > 1);
		TestEqual(What + TEXT(": override cleared"), R.World->GetOverrideType(C.Origin), EDinkOverrideType::None);
		TestEqual(What + TEXT(": its main ran again (8 hitpoints)"), R.D->FindSprite(Back) ? R.D->FindSprite(Back)->GetProp(TEXT("hitpoints")) : -1, 8);
	}
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplaySwordTest, "Dink.Gameplay.Items.SwordChangesDamage", DINK_TEST_FLAGS)
bool FDinkGameplaySwordTest::RunTest(const FString& Parameters)
{
	// item-sw1.c arm: &strength += 4, sp_range(1, 40); disarm undoes it. Melee damage
	// strength / 2 + rand() % ((strength + 1) / 2) + 1 (D:15567), with rand() = 0: 2 at strength 3, 4 at 7.
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	NewGame(E);
	E.G->SetRandomSource(MakeShared<FDinkScriptedRandomSource>(TArray<int32>{ 0 }));
	E.D->GetDink().Screen = 1;
	const int32 Target = E.D->CreateVirtualSprite(1, 300, 200);
	FDinkSprite& T = *E.D->FindSprite(Target);
	T.bSpawned = false;
	T.Props.Add(TEXT("brain"), 9);
	T.Props.Add(TEXT("hitpoints"), 100);
	T.Props.Add(TEXT("pseq"), 131);
	T.Props.Add(TEXT("pframe"), 1);
	auto Hp = [&E, Target]() { return E.D->FindSprite(Target)->GetProp(TEXT("hitpoints")); };
	TestEqual(TEXT("new game strength 3"), E.Facts->GetFact(TEXT("strength")), 3);

	StandWestOf(E, Target, 20);
	Attack(E);
	TestEqual(TEXT("fists: 2 damage"), Hp(), 98);
	StandWestOf(E, Target, 38);
	Attack(E);
	TestEqual(TEXT("fists from 38 px: out of reach (28 + 5)"), Hp(), 98);

	// Picking up the sword (add_item: its pickup runs) and arming it on the inventory screen.
	const int32 Slot = E.G->AddItem(TEXT("item-sw1"), false);
	Settle(E);
	TestEqual(TEXT("sword in slot 2"), Slot, 1);
	TestTrue(TEXT("arm slot 2"), E.G->ArmItemSlot(2));
	Settle(E);
	TestEqual(TEXT("item-sw1 arm: &strength 3 + 4 = 7"), E.Facts->GetFact(TEXT("strength")), 7);
	TestEqual(TEXT("item-sw1 arm: sp_range(1, 40)"), E.D->GetDink().GetProp(TEXT("range")), 40);
	TestEqual(TEXT("&cur_weapon = 2"), E.Facts->GetFact(TEXT("cur_weapon")), 2);
	Attack(E);
	TestEqual(TEXT("sword from 38 px: in reach (40 + 5), 4 damage"), Hp(), 94);
	StandWestOf(E, Target, 20);
	Attack(E);
	TestEqual(TEXT("sword: 4 damage"), Hp(), 90);

	// Back to the fists: the sword's disarm takes the 4 strength back.
	TestTrue(TEXT("arm slot 1"), E.G->ArmItemSlot(1));
	Settle(E);
	TestEqual(TEXT("item-sw1 disarm: &strength back to 3"), E.Facts->GetFact(TEXT("strength")), 3);
	Attack(E);
	TestEqual(TEXT("fists again: 2 damage"), Hp(), 88);
	CheckOriginal(*this, TEXT("item-sw1"), { TEXT("&strength += 4;"), TEXT("&strength -= 4;"), TEXT("sp_range(1, 40);") });
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayMagicTest, "Dink.Gameplay.Magic.RechargeSteps", DINK_TEST_FLAGS)
bool FDinkGameplayMagicTest::RunTest(const FString& Parameters)
{
	// item-fb.c arm: &magic_cost = 100; use: &magic_level = 0 and a fireball (create_sprite brain 11,
	// sp_script dam-fire). The 100 ms status update adds &magic until the cost (D:5935).
	for (const int32 Magic : { 3, 7, 1 })
	{
		FEnv E = Make(*this);
		if (!E.IsValid())
		{
			return false;
		}
		NewGame(E);
		E.Facts->SetFact(TEXT("update_status"), 1);
		E.Facts->SetFact(TEXT("magic"), Magic);
		E.D->GetDink().Screen = 1;
		E.G->AddItem(TEXT("item-fb"), true);
		Settle(E);
		TestTrue(TEXT("arm spell slot 1"), E.G->ArmMagicSlot(1));
		Settle(E);
		TestEqual(TEXT("item-fb arm: &magic_cost 100"), E.Facts->GetFact(TEXT("magic_cost")), 100);
		E.Facts->SetFact(TEXT("magic_level"), 100);
		TestTrue(TEXT("charged: cast"), E.G->PlayerCastMagic());
		Settle(E);
		TestEqual(TEXT("item-fb use: &magic_level 0"), E.Facts->GetFact(TEXT("magic_level")), 0);
		const int32 Fireball = FindByScript(E, TEXT("dam-fire"));
		TestTrue(TEXT("a fireball (PLACEHOLDER missile, brain 11, dam-fire) exists"), Fireball != 0 && E.D->FindSprite(Fireball)->GetProp(TEXT("brain")) == 11);
		TestFalse(TEXT("not charged: no cast"), E.G->PlayerCastMagic());
		const int64 Ticks0 = E.G->StatusTicks;
		int32 Steps = 0;
		while (E.Facts->GetFact(TEXT("magic_level")) < 100 && Steps < 1000)
		{
			E.Story->Advance(0.100);
			++Steps;
		}
		const int32 Expected = DinkRules::MagicRechargeSteps(100, Magic);
		TestEqual(FString::Printf(TEXT("magic %d: recharged in ceil(100 / %d) = %d steps of 100 ms"), Magic, Magic, Expected), Steps, Expected);
		TestEqual(TEXT("one status update per 100 ms"), static_cast<int32>(E.G->StatusTicks - Ticks0), Steps);
		TestTrue(TEXT("charged again: cast"), E.G->PlayerCastMagic());
	}
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplaySpellScreenTest, "Dink.Gameplay.Magic.SpellFliesOnTheCurrentScreen", DINK_TEST_FLAGS)
bool FDinkGameplaySpellScreenTest::RunTest(const FString& Parameters)
{
	// An item script instance (the armed spell) outlives screen changes (script_attach 1000), as in the original,
	// where every sprite lives on the one current map. Its instance used to keep the screen it was created on, so a
	// spell armed on one screen and cast on the next put its missile on the old screen: the brains only think for
	// sprites of Dink's screen, so the missile never flew (the probe's Acid Rain in the prisoner's cave stood still
	// at its spawn point for 90 s; it had been armed at the teacher's, SCR_038).
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	E.G->Adaptation.bEnabled = false;
	NewGame(E);
	E.Facts->SetFact(TEXT("update_status"), 1);
	E.Facts->SetFact(TEXT("magic"), 2);
	Enter(E, 38);
	E.D->GetDink().Screen = 38;
	E.G->AddItem(TEXT("item-fb"), true);
	Settle(E);
	TestTrue(TEXT("arm the fireball on screen 38"), E.G->ArmMagicSlot(1));
	Settle(E);
	Enter(E, 579);
	FDinkSprite& Dink = E.D->GetDink();
	Dink.Screen = 579;
	Dink.X = 290;
	Dink.Y = 218;
	Dink.Dir = 6;
	E.Facts->SetFact(TEXT("magic_level"), 100);
	TestTrue(TEXT("cast on screen 579"), E.G->PlayerCastMagic());
	Settle(E);
	const int32 Fireball = FindByScript(E, TEXT("dam-fire"));
	const FDinkSprite* M = E.D->FindSprite(Fireball);
	if (TestNotNull(TEXT("a fireball exists"), M))
	{
		TestEqual(TEXT("the fireball is on the screen Dink is on, not the one the spell was armed on"), M->Screen, 579);
		const double X0 = M->X;
		E.Story->bInstantMode = false;
		RunFor(E, 2.0 / 60.0); // two engine frames
		const FDinkSprite* After = E.D->FindSprite(Fireball);
		TestTrue(TEXT("and it flies: its brain thinks for it (6 px east a frame, until it bursts on something)"), After && After->X > X0);
	}
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayDuckTest, "Dink.Gameplay.Stonebrook.DuckQuestAndKill", DINK_TEST_FLAGS)
bool FDinkGameplayDuckTest::RunTest(const FString& Parameters)
{
	// Ethel's duck: s1-h2-o talk -> &old_womans_duck 1; findduck (SCR_440 base script) finds him one time
	// in four; s1-oldd talk "Yell at it" -> 2, he goes home; back at Ethel's (s1-h2-s: vision 1) he is in
	// the house (s1-h2-dk). One hit kills a duck (duck_brain): his die runs.
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	NewGame(E);
	Enter(E, 2);
	const int32 Ethel = E.D->HandleForPlacement(2, 23);
	ChooseByText(E, { TEXT("Ask after her pet"), TEXT("Agree whole heartedly") });
	E.Story->StartProcedure(TEXT("s1-h2-o"), TEXT("talk"), Ethel, {}, 2);
	Settle(E);
	TestEqual(TEXT("Ethel's talk: &old_womans_duck = 1"), E.Facts->GetFact(TEXT("old_womans_duck")), 1);

	// findduck: random(4,1) == 1 shows him (vision 2). rand() = 0 makes it 1.
	E.G->SetRandomSource(MakeShared<FDinkScriptedRandomSource>(TArray<int32>{ 0 }));
	int32 From = E.Story->Events.Num();
	Enter(E, 440);
	E.G->SetRandomSource(nullptr);
	TestEqual(TEXT("findduck: &vision 2"), E.Facts->GetFact(TEXT("vision")), 2);
	TestTrue(TEXT("findduck: \"There's that duck!!\""), Said(E.Story, From).Contains(TEXT("There's that duck!!")));
	const int32 Stray = E.D->HandleForPlacement(440, 2);
	TestTrue(TEXT("the duck S440_P02 (vision 2) is a sprite"), Stray > 1 && E.D->FindSprite(Stray)->bActive);
	ChooseByText(E, { TEXT("Yell at it") });
	E.Story->StartProcedure(TEXT("s1-oldd"), TEXT("talk"), Stray, {}, 440);
	Settle(E);
	TestEqual(TEXT("yelled at: &old_womans_duck = 2"), E.Facts->GetFact(TEXT("old_womans_duck")), 2);

	From = E.Story->Events.Num();
	Enter(E, 2);
	TestEqual(TEXT("s1-h2-s: vision 1 (the duck is home)"), E.Facts->GetFact(TEXT("vision")), 1);
	TestEqual(TEXT("Ethel's main: &old_womans_duck = 4"), E.Facts->GetFact(TEXT("old_womans_duck")), 4);
	const int32 Duck = E.D->HandleForPlacement(2, 24);
	TestTrue(TEXT("the duck S002_P24 (vision 1, s1-h2-dk) is a sprite"), Duck > 1 && E.D->FindSprite(Duck)->bActive);
	StandWestOf(E, Duck);
	From = E.Story->Events.Num();
	Attack(E);
	TestEqual(TEXT("s1-h2-dk die: &old_womans_duck = 5"), E.Facts->GetFact(TEXT("old_womans_duck")), 5);
	const TArray<FString> Lines = Said(E.Story, From);
	for (const TCHAR* Line : { TEXT("Dink, noooooooo!!!"), TEXT("You little bastard!!"), TEXT("Get out!!"), TEXT("Uh, sorry.") })
	{
		TestTrue(FString::Printf(TEXT("die: \"%s\""), Line), Lines.Contains(Line));
	}
	TestTrue(TEXT("duck_brain: the body runs on headless"), E.D->FindSprite(Duck)->bHeadless && E.D->FindSprite(Duck)->bActive);
	StandWestOf(E, Duck);
	Attack(E);
	TestFalse(TEXT("second hit: duckdie, the body is gone"), E.D->FindSprite(Duck) && E.D->FindSprite(Duck)->bActive);
	CheckOriginal(*this, TEXT("s1-h2-dk"), { TEXT("Dink, noooooooo!!!"), TEXT("You little bastard!!"), TEXT("Get out!!"), TEXT("Uh, sorry.") });
	CheckOriginal(*this, TEXT("findduck"), { TEXT("There's that duck!!") });
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayPigFeedTest, "Dink.Gameplay.Stonebrook.PigFeeding", DINK_TEST_FLAGS)
bool FDinkGameplayPigFeedTest::RunTest(const FString& Parameters)
{
	// The first quest: touch the sack of feed in Dink's house (s1-sack touch: add_item item-pig), arm it,
	// use it in the pig pen on SCR_407 (item-pig use: inside_box 200,180-400,306) -> the bully's scene
	// (s1-bul) -> &pig_story 1; mother's talk offers "Tell her you fed the pigs".
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	NewGame(E);
	Enter(E, 1);
	TestEqual(TEXT("mother's scene: &story 1"), E.Facts->GetFact(TEXT("story")), 1);
	TestEqual(TEXT("mother's scene: &update_status 1"), E.Facts->GetFact(TEXT("update_status")), 1);
	const int32 Sack = E.D->HandleForPlacement(1, 52);
	StandOn(E, Sack);
	int32 From = E.Story->Events.Num();
	E.Story->Advance(0.016);
	Settle(E);
	TestEqual(TEXT("touch the sack: item-pig in slot 2"), E.D->GetInventory()->GetItemAt(1), FName(TEXT("item-pig")));
	TestTrue(TEXT("\"I now have a sack of pig feed.\""), Said(E.Story, From).Contains(TEXT("I now have a sack of pig feed.")));
	TestEqual(TEXT("the sack: editor_type 1"), E.World->GetOverrideType(FDinkOriginId(1, 52)), EDinkOverrideType::RemovedForever);
	RunFor(E, 0.4);
	TestFalse(TEXT("the sack is gone"), E.D->FindSprite(Sack) && E.D->FindSprite(Sack)->bActive);

	TestTrue(TEXT("arm the feed"), E.G->ArmItemSlot(2));
	Settle(E);
	Enter(E, 407);
	FDinkSprite& Dink = E.D->GetDink();
	Dink.X = 300;
	Dink.Y = 250;
	Dink.Dir = 2;
	From = E.Story->Events.Num();
	Attack(E);
	TestTrue(TEXT("\"Come on pigs, eat!\""), Said(E.Story, From).Contains(TEXT("Come on pigs, eat!")));
	TestEqual(TEXT("the bully's scene: &pig_story 1"), E.Facts->GetFact(TEXT("pig_story")), 1);
	TestTrue(TEXT("the bully says his line"), Said(E.Story, From).Contains(TEXT("Well, lookie what we got here.")));

	// Mother's talk now offers the option; &story only moves on in her main once Ethel's duck is
	// settled too (s1-h1-m.c main: &old_womans_duck > 2 and &pig_story != 0 -> &story = 2).
	Enter(E, 1);
	ChooseByText(E, { TEXT("Tell her you fed the pigs") });
	From = E.Story->Events.Num();
	E.Story->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), E.D->HandleForPlacement(1, 26), {}, 1);
	Settle(E);
	TestTrue(TEXT("told mother"), Said(E.Story, From).Contains(TEXT("I'm finished with my chores, mother.")));
	TestEqual(TEXT("&story still 1 while the duck quest is open"), E.Facts->GetFact(TEXT("story")), 1);
	CheckOriginal(*this, TEXT("s1-sack"), { TEXT("I now have a sack of pig feed.") });
	CheckOriginal(*this, TEXT("item-pig"), { TEXT("Come on pigs, eat!") });
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayStatusTest, "Dink.Gameplay.Status.LevelUpAndDeath", DINK_TEST_FLAGS)
bool FDinkGameplayStatusTest::RunTest(const FString& Parameters)
{
	// Status update (D:5856-5963): exp at the next level's threshold runs lraise `raise` (its menu picks
	// the stat); life below 1 runs dinfo `die` once (it sets &update_status 0).
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	NewGame(E);
	E.Facts->SetFact(TEXT("update_status"), 1);
	E.Facts->SetFact(TEXT("exp"), 120);
	ChooseByText(E, { TEXT("Increase Defense") });
	E.Story->Advance(0.100);
	Settle(E);
	TestEqual(TEXT("level 2"), E.Facts->GetFact(TEXT("level")), 2);
	TestEqual(TEXT("exp 120 - 100 = 20"), E.Facts->GetFact(TEXT("exp")), 20);
	TestEqual(TEXT("defense +1"), E.Facts->GetFact(TEXT("defense")), 1);
	TestEqual(TEXT("lifemax +3"), E.Facts->GetFact(TEXT("lifemax")), 13);

	E.Story->AutoChooser = [](const FDinkMenu&) { return 1; };
	E.Facts->SetFact(TEXT("life"), 0);
	E.Story->bInstantMode = false;
	E.Story->Advance(0.100);
	TestEqual(TEXT("dinfo die: &update_status 0"), E.Facts->GetFact(TEXT("update_status")), 0);
	TestTrue(TEXT("dinfo die: Dink frozen"), E.D->GetDink().bFrozen);
	const int32 Instances = E.Story->GetInstances().Num();
	E.Story->Advance(0.100);
	E.Story->Advance(0.100);
	TestEqual(TEXT("dinfo runs once"), E.Story->GetInstances().Num(), Instances);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayPushTest, "Dink.Gameplay.Push.Rock", DINK_TEST_FLAGS)
bool FDinkGameplayPushTest::RunTest(const FString& Parameters)
{
	// Walking into hardness in a cardinal direction for more than 600 ms runs `push` of the scripted
	// sprites whose hardbox + 2 px holds Dink (D:13526, 14768, 15600). s1-roc (S277_P03): too heavy below
	// strength 4; at 4 it rolls east to x 350 and &rock_placement becomes 1.
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	NewGame(E);
	Enter(E, 277);
	const int32 Rock = E.D->HandleForPlacement(277, 3);
	const FDinkSprite* R = E.D->FindSprite(Rock);
	int32 L = 0, T = 0, Rt = 0, B = 0;
	if (!TestTrue(TEXT("rock S277_P03 with a hardbox"), R && E.G->GetHardbox(*R, L, T, Rt, B)))
	{
		return false;
	}
	FDinkSprite& Dink = E.D->GetDink();
	Dink.X = L - 1;
	Dink.Y = (T + B) / 2;
	int32 From = E.Story->Events.Num();
	E.G->UpdatePush(true, 6, 1000.0);
	E.G->UpdatePush(true, 6, 1500.0);
	Settle(E);
	TestEqual(TEXT("not before 600 ms"), Said(E.Story, From).Num(), 0);
	E.G->UpdatePush(true, 6, 1601.0);
	Settle(E);
	TestTrue(TEXT("strength 3: too heavy"), Said(E.Story, From).Contains(TEXT("It's too heavy for me.  If I was a little stronger...")));
	E.G->UpdatePush(false, 0, 1700.0);
	E.Facts->SetFact(TEXT("strength"), 4);
	From = E.Story->Events.Num();
	E.G->UpdatePush(true, 6, 2000.0);
	E.G->UpdatePush(true, 6, 2601.0);
	Settle(E);
	TestTrue(TEXT("strength 4, pushing east: it moves"), Said(E.Story, From).Contains(TEXT("It's .. it's moving...")));
	TestEqual(TEXT("&rock_placement = 1"), E.Facts->GetFact(TEXT("rock_placement")), 1);
	TestEqual(TEXT("the rock rolled to x 350"), FMath::RoundToInt32(E.D->FindSprite(Rock)->X), 350);
	CheckOriginal(*this, TEXT("s1-roc"), { TEXT("It's too heavy for me.  If I was a little stronger..."), TEXT("It's .. it's moving...") });
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayNutTest, "Dink.Gameplay.Items.EatNutKillCurItem", DINK_TEST_FLAGS)
bool FDinkGameplayNutTest::RunTest(const FString& Parameters)
{
	// item-nut.c use: &life += 2 (up to lifemax), "Yum, tasted good.", kill_cur_item(): the armed item
	// leaves the inventory, &cur_weapon 0, its drop runs (D:1480); the calling script stops.
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	NewGame(E);
	E.Facts->SetFact(TEXT("lifemax"), 10);
	E.Facts->SetFact(TEXT("life"), 5);
	const int32 Slot = E.G->AddItem(TEXT("item-nut"), false);
	Settle(E);
	TestTrue(TEXT("arm the nut"), E.G->ArmItemSlot(Slot + 1));
	Settle(E);
	const int32 From = E.Story->Events.Num();
	TestTrue(TEXT("use (attack key)"), E.G->PlayerAttack());
	Settle(E);
	TestEqual(TEXT("life 5 + 2"), E.Facts->GetFact(TEXT("life")), 7);
	TestTrue(TEXT("\"Yum, tasted good.\""), Said(E.Story, From).Contains(TEXT("Yum, tasted good.")));
	TestTrue(TEXT("the nut left the inventory"), E.D->GetInventory()->GetItemAt(Slot).IsNone());
	TestEqual(TEXT("&cur_weapon 0"), E.Facts->GetFact(TEXT("cur_weapon")), 0);
	TestEqual(TEXT("nothing armed"), E.G->GetWeaponInstance(), 0);
	TestTrue(TEXT("kill_cur_item ran its drop"), E.G->Events.ContainsByPredicate([](const FString& Ev) { return Ev == TEXT("kill_cur_item item-nut"); }));
	CheckOriginal(*this, TEXT("item-nut"), { TEXT("Yum, tasted good."), TEXT("kill_cur_item();") });
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayCastFacingTest, "Dink.Gameplay.Magic.CastFacesThePawn", DINK_TEST_FLAGS)
bool FDinkGameplayCastFacingTest::RunTest(const FString& Parameters)
{
	// The magic key casts where Dink faces: item-fb.c's use reads sp_dir(1, -1) and throws the fireball 30 px
	// that way (seq 504 west, 506 east). Dink's dir must come from the pawn's facing, as for the attack key.
	// Until the fix PlayerCastMagic left the dir as the last script or attack had set it (s2-auntp sets
	// sp_dir(1, 1) in Jack's scene, so every fireball in the probe's Jack fight flew west whatever Dink faced).
	// A real game instance with one screen volume and a stand-in pawn actor.
	if (!TestNotNull(TEXT("GEngine"), GEngine))
	{
		return false;
	}
	UGameInstance* GameInstance = NewObject<UGameInstance>(GEngine);
	GameInstance->InitializeStandalone();
	UWorld* World = GameInstance->GetWorld();
	UDinkStorySubsystem* S = GameInstance->GetSubsystem<UDinkStorySubsystem>();
	UDinkGreyboxSubsystem* Greybox = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
	if (TestNotNull(TEXT("story subsystem"), S) && TestTrue(TEXT("story loaded"), S && S->IsReady()) && TestNotNull(TEXT("greybox subsystem"), Greybox))
	{
		UDinkFactSubsystem* F = S->GetFacts();
		UDinkDirector* D = S->GetDirector();
		UDinkGameplay* G = S->GetGameplay();
		S->bRunScreenScripts = false;
		S->ResetRuntime();
		S->bInstantMode = true;
		G->Adaptation.bEnabled = false;
		ADinkScreenVolume* Volume = World->SpawnActor<ADinkScreenVolume>();
		Volume->ScreenNumber = 36;
		Volume->Corners.NW = FVector2D(0, 0);
		Volume->Corners.NE = FVector2D(60, 0);
		Volume->Corners.SW = FVector2D(0, 40);
		Volume->Corners.SE = FVector2D(60, 40);
		Greybox->RegisterScreen(Volume);
		F->SetFact(TEXT("player_map"), 36);
		AActor* Pawn = World->SpawnActor<AActor>();
		USceneComponent* Root = NewObject<USceneComponent>(Pawn, TEXT("Root"));
		Pawn->SetRootComponent(Root);
		Root->RegisterComponent();
		const FVector At = DinkLayout::MapPixelToUnreal(Volume->Corners, 300, 200);
		Pawn->SetActorLocation(At);
		G->StartNewGame();
		S->RunUntilIdle();
		FDinkSprite& Dink = D->GetDink();
		Dink.Actor = Pawn;
		Dink.Screen = 36;
		F->SetFact(TEXT("update_status"), 1);
		F->SetFact(TEXT("magic"), 2);
		G->AddItem(TEXT("item-fb"), true);
		S->RunUntilIdle();
		TestTrue(TEXT("arm the fireball"), G->ArmMagicSlot(1));
		S->RunUntilIdle();
		for (const int32 Facing : { 6, 4, 6 })
		{
			// The pawn faces east (6) or west (4) in map pixels; the stale dir is always the other way.
			const FVector Ahead = DinkLayout::MapPixelToUnreal(Volume->Corners, Facing == 6 ? 320 : 280, 200);
			Pawn->SetActorRotation(FRotator(0.0, (Ahead - At).Rotation().Yaw, 0.0));
			D->GetDink().Dir = Facing == 6 ? 4 : 6;
			F->SetFact(TEXT("magic_level"), 100);
			TArray<int32> Old;
			D->GetSprites().GetKeys(Old);
			TestTrue(FString::Printf(TEXT("cast facing %d"), Facing), G->PlayerCastMagic());
			S->RunUntilIdle();
			TestEqual(FString::Printf(TEXT("facing %d: Dink's dir is the pawn's facing"), Facing), D->GetDink().Dir, Facing);
			int32 Fireball = 0;
			for (const TPair<int32, FDinkSprite>& P : D->GetSprites())
			{
				if (!Old.Contains(P.Key) && P.Value.Script == FName(TEXT("dam-fire")))
				{
					Fireball = P.Key;
				}
			}
			const FDinkSprite* M = D->FindSprite(Fireball);
			if (TestNotNull(FString::Printf(TEXT("facing %d: a fireball (dam-fire)"), Facing), M))
			{
				TestEqual(FString::Printf(TEXT("facing %d: its sequence (item-fb.c: 506 east, 504 west)"), Facing), M->GetProp(TEXT("seq")), Facing == 6 ? 506 : 504);
				TestTrue(FString::Printf(TEXT("facing %d: it starts on Dink's %s side"), Facing, Facing == 6 ? TEXT("east") : TEXT("west")), Facing == 6 ? M->X > D->GetDink().X : M->X < D->GetDink().X);
				D->DeactivateSprite(Fireball, 0, /*bEndScripts*/ true);
			}
		}
		CheckOriginal(*this, TEXT("item-fb"), { TEXT("&mydir = sp_dir(1, -1);"), TEXT("sp_seq(&junk, 506);"), TEXT("sp_seq(&junk, 504);") });
		Pawn->Destroy();
		Greybox->UnregisterScreen(Volume);
		Volume->Destroy();
	}
	GameInstance->Shutdown();
	if (World)
	{
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
	}
	return true;
}

// A text is a sprite slot with its own kill timer in the engine (dink.cpp D:16811-16823: the timer deactivates the slot it belongs to).
// Here the list of active texts outlives a screen change (which releases every sprite but Dink and the survivors), the handle is given
// to the next sprite, and the text's expiry then removed that sprite: a Bong of SCR_480 vanished silently 2.7 s after Dink came from the
// screen where he had picked up gold ("I found 34 gold."), and the probe's gold loop never ended.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameplayStaleTextTest, "Dink.Gameplay.Texts.ExpiredTextKeepsARecycledHandle", DINK_TEST_FLAGS)
bool FDinkGameplayStaleTextTest::RunTest(const FString& Parameters)
{
	using namespace DinkGameplayTest;
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	E.Story->bInstantMode = false; // texts last their time
	FDinkStoryLine Line;
	Line.Text = TEXT("I found 34 gold.");
	const int32 TextHandle = E.Story->ShowText(Line, 1, 0);
	const FDinkSprite* Text = E.D->FindSprite(TextHandle);
	TestTrue(TEXT("the text is a sprite"), Text && Text->bText);
	// SCR_583: en-bong and en-boncd, the first live placements, take the smallest free handles (2 and 3).
	E.Story->OnScreenEntered(583);
	const FDinkSprite* Reused = E.D->FindSprite(TextHandle);
	if (!TestTrue(TEXT("set-up: the screen change released the text's sprite and a monster took its handle"), Reused && !Reused->bText && Reused->Script == FName(TEXT("en-bong"))))
	{
		return false;
	}
	RunFor(E, 5.0); // the text's time (strlen x 77 ms, at least 2.7 s) is over
	TestEqual(TEXT("no text is left"), E.Story->GetActiveTexts().Num(), 0);
	Reused = E.D->FindSprite(TextHandle);
	TestTrue(TEXT("the Bong that has the handle now is still there"), Reused && Reused->bActive && Reused->Script == FName(TEXT("en-bong")));
	return true;
}
