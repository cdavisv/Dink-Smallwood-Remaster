// Dink.Gameplay.Controls.*: the player's keyboard and mouse as the game reads them (FDinkNarrativeInputProcessor), on the
// converted story without a world. The tests call the processor's Process* functions, which are exactly what its Slate
// handlers call once they have checked that a game world runs and the console is closed.

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkInventoryComponent.h"
#include "DinkNarrativeInput.h"
#include "DinkStorySubsystem.h"
#include "InputCoreTypes.h"
#include "HAL/PlatformTime.h"

namespace DinkPlaytestControlsTest
{
	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* G = nullptr;
		TSharedPtr<FDinkNarrativeInputProcessor> Input;
		bool IsValid() const { return Facts && World && Story && Story->IsReady() && G && G->HasData() && Input.IsValid(); }
	};

	/** Story, facts and world state outside any world, seeded; the input processor the game registers, without the click guard. */
	FEnv Make(FAutomationTestBase& Test, bool bInstant)
	{
		FEnv E;
		UGameInstance* GI = DinkTest::MakeOuterGameInstance();
		E.Facts = NewObject<UDinkFactSubsystem>(GI);
		FString Error;
		Test.TestTrue(TEXT("facts table loads"), E.Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
		E.World = NewObject<UDinkWorldStateSubsystem>(GI);
		E.Story = NewObject<UDinkStorySubsystem>(GI);
		Test.TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), E.Story->SetupStandalone(E.Facts, E.World, &Error));
		E.Story->StorySeed = 1997;
		E.Story->ResetRuntime();
		E.Story->bInstantMode = bInstant;
		E.D = E.Story->GetDirector();
		E.G = E.Story->GetGameplay();
		Test.TestTrue(TEXT("gameplay data loaded (Scripts/sync_gameplay_data.py)"), E.G && E.G->HasData());
		E.Input = MakeShared<FDinkNarrativeInputProcessor>(E.Story);
		E.Input->MouseConfirmGuardSeconds = 0.;
		return E;
	}

	void Settle(FEnv& E)
	{
		E.Story->RunUntilIdle();
		E.G->ProcessDamage();
		E.Story->RunUntilIdle();
	}

	void Frames(FEnv& E, int32 N)
	{
		for (int32 i = 0; i < N; ++i)
		{
			E.Story->Advance(1.0 / 60.0);
		}
	}

	int32 CountKind(const UDinkStorySubsystem* S, FName Kind, int32 From = 0)
	{
		int32 N = 0;
		for (int32 i = From; i < S->Events.Num(); ++i)
		{
			N += S->Events[i].Kind == Kind ? 1 : 0;
		}
		return N;
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

	int32 CountAttacks(const UDinkGameplay* G, int32 From = 0)
	{
		int32 N = 0;
		for (int32 i = From; i < G->Events.Num(); ++i)
		{
			N += G->Events[i].StartsWith(TEXT("attack with")) ? 1 : 0;
		}
		return N;
	}

	/** Dink west of the sprite's hardbox by Gap pixels, level with it, facing east. */
	void StandWestOf(FEnv& E, int32 Handle, int32 Gap = 20)
	{
		const FDinkSprite* T = E.D->FindSprite(Handle);
		int32 L = 0, Tp = 0, R = 0, B = 0;
		if (T && E.G->GetHardbox(*T, L, Tp, R, B))
		{
			FDinkSprite& Dink = E.D->GetDink();
			Dink.Screen = T->Screen;
			Dink.X = L - Gap;
			Dink.Y = T->Y;
			Dink.Dir = 6;
		}
	}
}

using namespace DinkPlaytestControlsTest;

// The owner's playtest (14 Nov 2026): "left click should also hit". A left click goes down the same press/release path as F
// (the attack gate, so one attack per press, and the bow draws while it is held); a fast second click, which Slate delivers as a
// double-click, is a press too. With a menu up the click picks the highlighted option, and with a blocking line up it skips the
// line, exactly as Enter does; in neither case does Dink attack.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkControlsLeftClickTest, "Dink.Gameplay.Controls.LeftClickAttacks", DINK_TEST_FLAGS)
bool FDinkControlsLeftClickTest::RunTest(const FString& Parameters)
{
	FEnv E = Make(*this, /*bInstant*/ true);
	if (!E.IsValid())
	{
		return false;
	}
	E.G->StartNewGame();
	Settle(E);
	E.Story->OnScreenEntered(1);
	Settle(E);
	TestEqual(TEXT("new game: the fists are armed"), E.D->GetInventory()->GetArmedItem(), FName(TEXT("item-fst")));
	// s1-sack.c `hit`: "I hate you, sack of feed!" proves the fists' hit reached a target.
	const int32 Sack = E.D->HandleForPlacement(1, 52);
	TestTrue(TEXT("the sack S001_P52 is a sprite"), Sack > 1);
	StandWestOf(E, Sack);
	E.D->GetDink().bFrozen = false;

	int32 From = E.Story->Events.Num();
	int32 AttacksFrom = E.G->Events.Num();
	TestTrue(TEXT("left button down: used"), E.Input->ProcessMouseDown(EKeys::LeftMouseButton));
	TestEqual(TEXT("left button held as the attack input"), E.Input->GetAttackKeyDown(), EKeys::LeftMouseButton);
	TestTrue(TEXT("the attack gate holds the key"), E.G->GetAttackGate().IsHeld());
	Settle(E);
	TestEqual(TEXT("one attack with the fists"), CountAttacks(E.G, AttacksFrom), 1);
	TestTrue(TEXT("s1-sack hit: \"I hate you, sack of feed!\""), Said(E.Story, From).Contains(TEXT("I hate you, sack of feed!")));
	TestFalse(TEXT("a right click does nothing"), E.Input->ProcessMouseDown(EKeys::RightMouseButton));
	E.Input->ProcessMouseUp(EKeys::LeftMouseButton);
	TestFalse(TEXT("the release lets the key go at once"), E.G->GetAttackGate().IsHeld());
	TestFalse(TEXT("no attack input held"), E.Input->GetAttackKeyDown().IsValid());

	// A second click while F is held does not start a second attack (one attack input at a time), and F's own release still works.
	Frames(E, 60);
	AttacksFrom = E.G->Events.Num();
	E.Input->ProcessKeyDown(EKeys::F);
	E.Input->ProcessMouseDown(EKeys::LeftMouseButton);
	TestEqual(TEXT("F then a click: one attack"), CountAttacks(E.G, AttacksFrom), 1);
	E.Input->ProcessMouseUp(EKeys::LeftMouseButton);
	TestEqual(TEXT("the click's release does not let F go"), E.Input->GetAttackKeyDown(), EKeys::F);

	// Down, up, then the double-click event and up (what Slate sends for two quick clicks): two attacks, the second
	// remembered by the gate while the first still locks Dink and started when the lock ends.
	E.Input->ProcessKeyUp(EKeys::F);
	E.Input->UpdateRelease(FPlatformTime::Seconds() + 1.0, /*bAppActive*/ true); // the repeat guard has passed
	TestFalse(TEXT("F let go after the repeat guard"), E.Input->GetAttackKeyDown().IsValid());
	Frames(E, 60);
	E.D->GetDink().bFrozen = false;
	AttacksFrom = E.G->Events.Num();
	E.Input->ProcessMouseDown(EKeys::LeftMouseButton);
	E.Input->ProcessMouseUp(EKeys::LeftMouseButton);
	E.Input->ProcessMouseDown(EKeys::LeftMouseButton); // HandleMouseButtonDoubleClickEvent calls this
	E.Input->ProcessMouseUp(EKeys::LeftMouseButton);
	Frames(E, 60);
	Settle(E);
	TestEqual(TEXT("a double-click is two attacks"), CountAttacks(E.G, AttacksFrom), 2);

	// A menu: the click picks the highlighted option and is not an attack.
	FEnv M = Make(*this, /*bInstant*/ false);
	if (!M.IsValid())
	{
		return false;
	}
	M.G->StartNewGame();
	M.Story->bInstantMode = true;
	Settle(M);
	M.Story->bInstantMode = false;
	const int32 Mom = M.D->CreateVirtualSprite(1, 300, 200);
	M.Story->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), Mom);
	M.Story->RunUntilIdle();
	TestNotNull(TEXT("mother's talk menu is up"), M.Story->GetActiveMenu());
	M.Story->MoveMenuSelection(1); // "Ask about your father"
	AttacksFrom = M.G->Events.Num();
	From = M.Story->Events.Num();
	TestTrue(TEXT("a click on the menu is used"), M.Input->ProcessMouseDown(EKeys::LeftMouseButton));
	TestNull(TEXT("the menu is gone"), M.Story->GetActiveMenu());
	TestEqual(TEXT("&result 2: the highlighted option was picked"), M.Facts->GetFact(TEXT("result")), 2);
	TestEqual(TEXT("no attack from the menu click"), CountAttacks(M.G, AttacksFrom), 0);
	TestFalse(TEXT("the menu click holds no attack key"), M.Input->GetAttackKeyDown().IsValid());
	M.Input->ProcessMouseUp(EKeys::LeftMouseButton);

	// The answer is a say_stop: a blocking line. The click skips it (as Enter does) instead of attacking.
	M.Story->RunUntilIdle();
	bool bBlocking = false;
	for (const FDinkActiveText& T : M.Story->GetActiveTexts())
	{
		bBlocking |= T.bBlocking;
	}
	TestTrue(TEXT("Dink's question is a blocking line"), bBlocking);
	const int32 Skips = CountKind(M.Story, TEXT("skip"));
	AttacksFrom = M.G->Events.Num();
	TestTrue(TEXT("a click on a blocking line is used"), M.Input->ProcessMouseDown(EKeys::LeftMouseButton));
	TestEqual(TEXT("the line was skipped"), CountKind(M.Story, TEXT("skip")), Skips + 1);
	TestEqual(TEXT("no attack from the skip click"), CountAttacks(M.G, AttacksFrom), 0);
	M.Input->ProcessMouseUp(EKeys::LeftMouseButton);
	return true;
}
