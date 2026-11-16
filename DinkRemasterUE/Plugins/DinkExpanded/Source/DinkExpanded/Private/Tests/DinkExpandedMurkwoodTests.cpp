#include "DinkExpanded.h"

#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkGameplay.h"
#include "DinkInkStory.h"
#include "DinkSaveGame.h"
#include "DinkStorySubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "Engine/GameInstance.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

/**
 * Pack 3's first slice (Murkwood Deep, doc/remaster/EXPANDED_CONTENT.md section 6) through the real runtime: the merged story the
 * build wrote to Plugins/DinkExpanded/Content/Data, the 1997 director and fact store. The lines are DRAFTS (owner to approve).
 */
namespace DinkExpandedMurkwood
{
	struct FGuard
	{
		bool bWas = DinkExpanded::IsEnabled();
		FDinkExpandedRegistry Was = DinkExpanded::GetRegistry();
		FString Story = FDinkInkStory::StoryDataOverrideDir();
		TArray<FString> Extra = FDinkGameplayData::ExtraDataDirs();
		~FGuard()
		{
			DinkExpanded::ApplySwitch(false);
			if (bWas)
			{
				DinkExpanded::ApplyForTest(Was, Story, Extra.Num() ? Extra.Last() : FString());
			}
			FDinkInkStory::StoryDataOverrideDir() = Story;
			FDinkGameplayData::ExtraDataDirs() = Extra;
		}
	};

	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* WorldState = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		bool IsValid() const { return Facts && WorldState && Story && Story->IsReady(); }
	};

	FEnv Make(FAutomationTestBase& Test)
	{
		FEnv Env;
		UGameInstance* GI = NewObject<UGameInstance>(GetTransientPackage());
		Env.Facts = NewObject<UDinkFactSubsystem>(GI);
		FString Error;
		Test.TestTrue(TEXT("facts table loads"), Env.Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
		Env.WorldState = NewObject<UDinkWorldStateSubsystem>(GI);
		Env.Story = NewObject<UDinkStorySubsystem>(GI);
		Test.TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), Env.Story->SetupStandalone(Env.Facts, Env.WorldState, &Error));
		return Env;
	}

	/** Switch on with the built packs (as -DinkExpanded=1 does at start). */
	bool On(FAutomationTestBase& Test, FDinkExpandedRegistry& Out)
	{
		const FString Dir = DinkExpanded::GetDataDir();
		FString Error;
		if (!Test.TestTrue(FString::Printf(TEXT("packs.json loads (%s)"), *Error), Out.LoadFromFile(Dir / TEXT("packs.json"), Error)))
		{
			return false;
		}
		DinkExpanded::ApplyForTest(Out, Dir / TEXT("Story"), Dir / TEXT("Gameplay"));
		return true;
	}

	TArray<FString> Said(const UDinkStorySubsystem* S, int32 From)
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

	int32 FindSpriteWithScript(const UDinkStorySubsystem* S, FName Script)
	{
		for (const TPair<int32, FDinkSprite>& Pair : S->GetDirector()->GetSprites())
		{
			if (Pair.Value.bActive && Pair.Value.Script == Script)
			{
				return Pair.Key;
			}
		}
		return 0;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkExpandedMurkwoodDataTest, "Dink.Expanded.Murkwood.Data",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter)
bool FDinkExpandedMurkwoodDataTest::RunTest(const FString& Parameters)
{
	using namespace DinkExpandedMurkwood;
	FGuard Guard;
	FDinkExpandedRegistry R;
	if (!On(*this, R))
	{
		return false;
	}
	const FDinkPack* Pack = R.FindPack(TEXT("murkwood"));
	if (!TestNotNull(TEXT("pack murkwood built"), Pack))
	{
		return false;
	}
	TestEqual(TEXT("namespace x3"), Pack->Number, 3);
	TestEqual(TEXT("six greybox screens"), Pack->Screens.Num(), 6);
	TestEqual(TEXT("one join"), Pack->Joins.Num(), 1);
	TestEqual(TEXT("joined at the Murkwood clearing, SCR_301"), Pack->Joins[0].FromScreen, 301);
	TestFalse(TEXT("the slice's text is owner-approved (16 Nov 2026), not a draft"), Pack->bDraft);

	// The gameplay tables: the 1997 rows, then the pack's (the hooks are what the switch sets).
	FDinkGameplayData WithPack;
	FString Error;
	TestTrue(FString::Printf(TEXT("tables load with the pack (%s)"), *Error), WithPack.Load(&Error));
	const FDinkPlacementInfo* Burt = WithPack.FindPlacement(FDinkOriginId(331, 1));
	TestTrue(TEXT("S331_P01 is Old Burt's placement"), Burt && Burt->Script == FName(TEXT("x3-burt")));
	TestTrue(TEXT("pack screen base script"), WithPack.GetBaseScript(332) == FName(TEXT("x3-thin")));
	TestNotNull(TEXT("pack screen hardness from the pack's data"), WithPack.GetHardness(332, 0));
	const int32 OnRows = WithPack.GetPlacementsOnScreen(366).Num();

	DinkExpanded::ApplySwitch(false);
	FDinkGameplayData Off;
	TestTrue(TEXT("tables load without the pack"), Off.Load(&Error));
	TestNull(TEXT("off: no pack placement"), Off.FindPlacement(FDinkOriginId(331, 1)));
	TestNull(TEXT("off: no pack hardness"), Off.GetHardness(332, 0));
	TestEqual(TEXT("the 1997 screen of the sealed gate has the same placements on and off"), Off.GetPlacementsOnScreen(366).Num(), OnRows);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkExpandedMurkwoodQuestTest, "Dink.Expanded.Murkwood.Quest",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter)
bool FDinkExpandedMurkwoodQuestTest::RunTest(const FString& Parameters)
{
	using namespace DinkExpandedMurkwood;
	FGuard Guard;
	FDinkExpandedRegistry R;
	if (!On(*this, R))
	{
		return false;
	}
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	UDinkStorySubsystem* S = Env.Story;
	const FDinkStoryNames& Names = S->GetStory().Names();
	TestTrue(TEXT("merged story holds the pack's scripts"), Names.ScriptToKnot.Contains(TEXT("x3-burt")));
	TestTrue(TEXT("merged story still holds the 1997 scripts"), Names.ScriptToKnot.Contains(TEXT("s1-h1-m")) && Names.ScriptToKnot.Contains(TEXT("s2-signe")));
	TestTrue(TEXT("pack globals are facts"), Names.GlobalToInk.Contains(TEXT("x3_burt")));

	// Every 1997 story fact before the quest (the pack may change engine stats such as gold, never story state).
	TMap<FName, int32> Before;
	for (const TPair<FName, int32>& F : Env.Facts->GetAllFacts())
	{
		if (Env.Facts->GetFactKind(F.Key) == EDinkFactKind::Story)
		{
			Before.Add(F.Key, F.Value);
		}
	}
	S->bInstantMode = true;
	FString Wanted;
	S->AutoChooser = [&Wanted](const FDinkMenu& Menu)
	{
		for (int32 i = 0; i < Menu.Choices.Num(); ++i)
		{
			if (Menu.Choices[i].Text == Wanted)
			{
				return i;
			}
		}
		return Menu.Choices.Num() - 1;
	};
	UDinkDirector* D = S->GetDirector();

	// 1. Old Burt asks for his leg.
	const int32 Burt = D->CreateVirtualSprite(331, 320, 180);
	int32 Mark = S->Events.Num();
	S->StartProcedure(TEXT("x3-burt"), TEXT("talk"), Burt, {}, 331);
	S->RunUntilIdle();
	TestEqual(TEXT("Burt asked: &x3_burt = 1"), Env.Facts->GetFact(TEXT("x3_burt")), 1);
	TestTrue(TEXT("he says what ate it"), Said(S, Mark).Contains(TEXT("Boar ate it. Big ugly thing, up in the wallow north of the trail.")));
	TestFalse(TEXT("Dink unfrozen after the talk"), D->GetDink().bFrozen);

	// 2. The Murk boar dies and drops the leg.
	const int32 Boar = D->CreateVirtualSprite(267, 320, 200);
	S->StartProcedure(TEXT("x3-boar"), TEXT("die"), Boar, {}, 267);
	S->RunUntilIdle();
	TestEqual(TEXT("boar dead: &x3_boar = 1"), Env.Facts->GetFact(TEXT("x3_boar")), 1);
	const int32 Leg = FindSpriteWithScript(S, TEXT("x3-leg"));
	if (!TestTrue(TEXT("the boar dropped a sprite running x3-leg"), Leg > 1))
	{
		return false;
	}

	// 3. Dink picks it up.
	Mark = S->Events.Num();
	S->StartProcedure(TEXT("x3-leg"), TEXT("touch"), Leg, {}, 267);
	S->RunUntilIdle();
	TestEqual(TEXT("carrying the leg: &x3_leg = 1"), Env.Facts->GetFact(TEXT("x3_leg")), 1);
	TestTrue(TEXT("Dink's line"), Said(S, Mark).Contains(TEXT("Burt's leg. Still warm. I'm not thinking about why.")));

	// 4. Back at the camp: give it to him.
	const int32 Gold = Env.Facts->GetFact(TEXT("gold"));
	Wanted = TEXT("Give Burt his leg");
	Mark = S->Events.Num();
	S->StartProcedure(TEXT("x3-burt"), TEXT("talk"), Burt, {}, 331);
	S->RunUntilIdle();
	TestEqual(TEXT("quest done: &x3_burt = 2"), Env.Facts->GetFact(TEXT("x3_burt")), 2);
	TestEqual(TEXT("leg handed over: &x3_leg = 2"), Env.Facts->GetFact(TEXT("x3_leg")), 2);
	TestEqual(TEXT("reward: 150 gold"), Env.Facts->GetFact(TEXT("gold")), Gold + 150);
	TestTrue(TEXT("he is having it stuffed"), Said(S, Mark).Contains(TEXT("Don't be daft, boy. I'm having it stuffed. Over the fireplace.")));

	// 5. Afterwards.
	Mark = S->Events.Num();
	S->StartProcedure(TEXT("x3-burt"), TEXT("talk"), Burt, {}, 331);
	S->RunUntilIdle();
	TestTrue(TEXT("after the quest"), Said(S, Mark).Contains(TEXT("It's a leg, Burt.")));
	TestFalse(TEXT("Dink unfrozen at the end"), D->GetDink().bFrozen);

	for (const TPair<FName, int32>& F : Before)
	{
		TestEqual(FString::Printf(TEXT("1997 story fact %s untouched by the pack"), *F.Key.ToString()), Env.Facts->GetFact(F.Key), F.Value);
	}
	TestEqual(TEXT("no runtime errors"), S->ErrorLog.Num(), 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkExpandedMurkwoodSaveTest, "Dink.Expanded.Murkwood.SaveLoadsWithPacksOff",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter)
bool FDinkExpandedMurkwoodSaveTest::RunTest(const FString& Parameters)
{
	using namespace DinkExpandedMurkwood;
	FGuard Guard;
	FDinkExpandedRegistry R;
	if (!On(*this, R))
	{
		return false;
	}
	// A save made mid-conversation with Old Burt (his instance is alive, blocked on a line).
	FEnv A = Make(*this);
	if (!A.IsValid())
	{
		return false;
	}
	A.Facts->SetFact(TEXT("gold"), 77);
	A.Facts->SetFact(TEXT("story"), 5);
	const int32 Burt = A.Story->GetDirector()->CreateVirtualSprite(331, 320, 180);
	A.Story->StartProcedure(TEXT("x3-burt"), TEXT("talk"), Burt, {}, 331);
	A.Story->RunUntilIdle();
	TestTrue(TEXT("Burt's instance alive in the save"), A.Story->FindInstanceForSprite(Burt, TEXT("x3-burt")) != nullptr);
	UDinkSaveGame* Save = NewObject<UDinkSaveGame>(GetTransientPackage());
	FDinkSaveContext CA;
	CA.Facts = A.Facts;
	CA.WorldState = A.WorldState;
	Save->CaptureFrom(CA);
	A.Story->CaptureToSave(Save);
	TArray<uint8> Bytes;
	TestTrue(TEXT("serialise"), UDinkSaveGame::SaveToBytes(Save, Bytes));

	// Load it with the packs OFF: the 1997 story, no pack knots.
	DinkExpanded::ApplySwitch(false);
	FEnv B = Make(*this);
	if (!B.IsValid())
	{
		return false;
	}
	TestFalse(TEXT("base story has no pack scripts"), B.Story->GetStory().Names().ScriptToKnot.Contains(TEXT("x3-burt")));
	UDinkSaveGame* Loaded = UDinkSaveGame::LoadFromBytes(Bytes);
	if (!TestNotNull(TEXT("deserialise"), Loaded))
	{
		return false;
	}
	FDinkSaveContext CB;
	CB.Facts = B.Facts;
	CB.WorldState = B.WorldState;
	TestTrue(TEXT("apply"), Loaded->ApplyTo(CB));
	B.Story->RestoreFromSave(Loaded);
	bool bPackInstance = false;
	for (const TUniquePtr<FDinkScriptInstance>& I : B.Story->GetInstances())
	{
		bPackInstance |= I->IsAlive() && I->Script.ToString().StartsWith(TEXT("x3-"));
	}
	TestFalse(TEXT("the pack's instance is left out"), bPackInstance);
	TestEqual(TEXT("1997 state loads: gold"), B.Facts->GetFact(TEXT("gold")), 77);
	TestEqual(TEXT("1997 state loads: story"), B.Facts->GetFact(TEXT("story")), 5);
	TestEqual(TEXT("no errors loading"), B.Story->ErrorLog.Num(), 0);
	// The game goes on: a 1997 script runs on the loaded state.
	B.Story->bInstantMode = true;
	const int32 Mom = B.Story->GetDirector()->CreateVirtualSprite(1, 300, 200);
	TestTrue(TEXT("1997 scripts still start"), B.Story->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), Mom) != 0);
	B.Story->RunUntilIdle();
	TestEqual(TEXT("no errors running"), B.Story->ErrorLog.Num(), 0);
	return true;
}

#endif
