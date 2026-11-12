// Dink.Narrative.*: the converted Ink story running on Inkpot's InkPlusPlus runtime, the story
// subsystem (script instances, fact mirroring, save/load) and the director.
//
// Expected texts are copied verbatim from the original scripts in the data repo
// (bin/dink/story/<script>.c, colour codes removed); when that repo is next to this project the
// tests also check every expected string really occurs in the original file.

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkInkStory.h"
#include "DinkNarrativeTypes.h"
#include "DinkSaveGame.h"
#include "DinkStatsComponent.h"
#include "DinkStorySubsystem.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Tests/AutomationEditorCommon.h"

namespace DinkNarrativeTest
{
	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* WorldState = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		bool IsValid() const { return Facts && WorldState && Story && Story->IsReady(); }
	};

	/** A story subsystem with its own fact and world-state subsystems, outside any world. */
	FEnv Make(FAutomationTestBase& Test)
	{
		FEnv Env;
		UGameInstance* GI = DinkTest::MakeOuterGameInstance();
		Env.Facts = NewObject<UDinkFactSubsystem>(GI);
		FString Error;
		Test.TestTrue(TEXT("facts table loads"), Env.Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
		Env.WorldState = NewObject<UDinkWorldStateSubsystem>(GI);
		Env.Story = NewObject<UDinkStorySubsystem>(GI);
		Test.TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), Env.Story->SetupStandalone(Env.Facts, Env.WorldState, &Error));
		Env.Story->StorySeed = 1997;
		Env.Story->ResetRuntime();
		return Env;
	}

	TArray<FDinkNarrativeEvent> Events(const UDinkStorySubsystem* S, const TCHAR* Kind, int32 From = 0)
	{
		TArray<FDinkNarrativeEvent> Out;
		const FName K(Kind);
		for (int32 i = From; i < S->Events.Num(); ++i)
		{
			if (S->Events[i].Kind == K)
			{
				Out.Add(S->Events[i]);
			}
		}
		return Out;
	}

	TArray<FString> Texts(const TArray<FDinkNarrativeEvent>& In)
	{
		TArray<FString> Out;
		for (const FDinkNarrativeEvent& E : In)
		{
			Out.Add(E.Text);
		}
		return Out;
	}

	TArray<FString> MenuTexts(const FDinkMenu* Menu)
	{
		TArray<FString> Out;
		if (Menu)
		{
			for (const FDinkStoryChoice& C : Menu->Choices)
			{
				Out.Add(C.Text);
			}
		}
		return Out;
	}

	void TestLines(FAutomationTestBase& Test, const FString& What, const TArray<FString>& Actual, const TArray<FString>& Expected)
	{
		Test.TestEqual(What + TEXT(": count"), Actual.Num(), Expected.Num());
		for (int32 i = 0; i < FMath::Min(Actual.Num(), Expected.Num()); ++i)
		{
			Test.TestEqual(FString::Printf(TEXT("%s [%d]"), *What, i), Actual[i], Expected[i]);
		}
	}

	/** When the data repo is next to the project: every expected string occurs verbatim in the original script. */
	void CheckOriginal(FAutomationTestBase& Test, const TCHAR* Script, const TArray<FString>& Strings)
	{
		// The data repo is the fork's root since 8 Nov 2026 (the project is DinkRemasterUE/ inside it); the old sibling layout is tried second.
		FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("../bin/dink/story") / (FString(Script) + TEXT(".c")));
		if (!IFileManager::Get().FileExists(*Path))
		{
			Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("../Dink-Smallwood-Remaster/bin/dink/story") / (FString(Script) + TEXT(".c")));
		}
		FString Source;
		if (!FFileHelper::LoadFileToString(Source, *Path))
		{
			Test.AddInfo(FString::Printf(TEXT("data repo not found (%s): verbatim check against the original skipped"), *Path));
			return;
		}
		for (const FString& S : Strings)
		{
			Test.TestTrue(FString::Printf(TEXT("\"%s\" occurs verbatim in %s.c"), *S, Script), Source.Contains(S, ESearchCase::CaseSensitive));
		}
	}

	FString DetailOf(const TArray<FDinkNarrativeEvent>& E, int32 I)
	{
		return E.IsValidIndex(I) ? E[I].Detail : FString();
	}
}

using namespace DinkNarrativeTest;

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeStoryLoadsTest, "Dink.Narrative.Story.Loads", DINK_TEST_FLAGS)
bool FDinkNarrativeStoryLoadsTest::RunTest(const FString& Parameters)
{
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	FDinkInkStory& Story = Env.Story->GetStory();
	TestEqual(TEXT("ink JSON format 21 (inklecate 1.2.1)"), Story.GetInkVersion(), 21);
	TestEqual(TEXT("377 script knots"), Story.Names().ScriptToKnot.Num(), 377);
	TestEqual(TEXT("930 entry points"), Story.Names().Entries.Num(), 930);
	TestEqual(TEXT("63 globals"), Story.Names().GlobalToInk.Num(), 63);

	// The source value forms include the three original-hardness accessors.
	const TArray<FString> Externals = {
		TEXT("buttoninfo"), TEXT("compare_sprite_script"), TEXT("compare_weapon"), TEXT("count_item"), TEXT("count_magic"),
		TEXT("create_sprite"), TEXT("editor_frame"), TEXT("editor_seq"), TEXT("free_items"), TEXT("free_magic"), TEXT("game_exist"), TEXT("get_burn"),
		TEXT("get_last_bow_power"), TEXT("get_rand_sprite_with_this_brain"), TEXT("get_sprite_with_this_brain"), TEXT("get_version"), TEXT("inside_box"),
		TEXT("is_base_game"), TEXT("is_script_attached"), TEXT("random"), TEXT("savegameinfo"), TEXT("scripts_used"), TEXT("sp"), TEXT("sp_brain"), TEXT("sp_dir"),
		TEXT("sp_editor_num"), TEXT("sp_hard"), TEXT("sp_hitpoints"), TEXT("sp_pframe"), TEXT("sp_pseq"), TEXT("sp_target"), TEXT("sp_x"), TEXT("sp_y") };
	const TArray<FString>& Bound = Env.Story->GetDirector()->GetExternalNames();
	TestEqual(TEXT("exact reviewed external vocabulary bound"), Bound.Num(), Externals.Num());
	TSet<FString> UniqueBound;
	for (const FString& Name : Bound)
	{
		TestTrue(TEXT("no unexpected external binding: ") + Name, Externals.Contains(Name));
		TestFalse(TEXT("no duplicate external binding: ") + Name, UniqueBound.Contains(Name));
		UniqueBound.Add(Name);
	}
	for (const FString& Name : Externals)
	{
		TestTrue(TEXT("external bound: ") + Name, Story.Ink().IsExternalFunctionBound(Name));
	}

	// Every fact has its Ink VAR, with the same initial value.
	for (const TPair<FName, FString>& Pair : Story.Names().GlobalToInk)
	{
		TestTrue(TEXT("VAR exists: ") + Pair.Value, Story.HasVariable(Pair.Value));
		TestEqual(TEXT("initial value of ") + Pair.Key.ToString(), Story.GetInt(Pair.Value, -12345), Env.Facts->GetFact(Pair.Key));
	}
	TestEqual(TEXT("&s2-nad is VAR s2_nad"), Story.Names().GlobalToInk.FindRef(TEXT("s2-nad")), FString(TEXT("s2_nad")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeKnotsResolveTest, "Dink.Narrative.Story.KnotsResolve", DINK_TEST_FLAGS)
bool FDinkNarrativeKnotsResolveTest::RunTest(const FString& Parameters)
{
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	const FDinkInkStory& Story = Env.Story->GetStory();
	int32 Knots = 0, Entries = 0, Bodies = 0;
	for (const TPair<FName, FString>& Pair : Story.Names().ScriptToKnot)
	{
		TestEqual(TEXT("knot name rule for ") + Pair.Key.ToString(), Pair.Value, DinkNarrative::KnotForScript(Pair.Key.ToString()));
		if (TestTrue(TEXT("knot resolves: ") + Pair.Value, Story.HasKnot(Pair.Value)))
		{
			++Knots;
		}
	}
	for (const FDinkStoryNames::FEntry& E : Story.Names().Entries)
	{
		Entries += Story.HasPath(E.Path) ? 1 : 0;
		TestTrue(TEXT("entry resolves: ") + E.Path, Story.HasPath(E.Path));
		const FString Body = DinkNarrative::KnotForScript(E.Script.ToString()) + TEXT(".p_") + E.Procedure.ToString();
		Bodies += Story.HasPath(Body) ? 1 : 0;
		TestTrue(TEXT("body resolves: ") + Body, Story.HasPath(Body));
	}
	TestEqual(TEXT("all 377 d_* knots resolve"), Knots, 377);
	TestEqual(TEXT("all 930 on_* entry stitches resolve"), Entries, 930);
	TestEqual(TEXT("all 930 p_* body stitches resolve"), Bodies, 930);
	TestFalse(TEXT("a made-up path does not resolve"), Story.HasPath(TEXT("d_s1_h1_m.on_nonsense")));
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeMomTalkTest, "Dink.Narrative.Talk.Mother", DINK_TEST_FLAGS)
bool FDinkNarrativeMomTalkTest::RunTest(const FString& Parameters)
{
	// s1-h1-m.c (Dink's mother), void talk, lines 83-150.
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	UDinkStorySubsystem* S = Env.Story;
	const int32 Mom = S->GetDirector()->CreateVirtualSprite(1, 300, 200);
	TestTrue(TEXT("talk starts"), S->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), Mom) != 0);
	S->RunUntilIdle();
	TestTrue(TEXT("freeze(1) froze Dink"), S->GetDirector()->GetDink().bFrozen);
	const TArray<FString> Menu0 = { TEXT("Ask about pig feeding"), TEXT("Ask about your father"), TEXT("Get info about the village"), TEXT("Get angry for no reason"), TEXT("Leave") };
	TestLines(*this, TEXT("menu while &pig_story == 0"), MenuTexts(S->GetActiveMenu()), Menu0);
	if (const FDinkMenu* M = S->GetActiveMenu())
	{
		TestEqual(TEXT("option ID keeps the original position"), M->Choices.Last().OptionId, FString(TEXT("s1-h1-m.talk.c1.6")));
	}

	TestTrue(TEXT("choose 'Ask about your father'"), S->Choose(1));
	S->bInstantMode = true;
	S->RunUntilIdle();
	const TArray<FDinkNarrativeEvent> Said = Events(S, TEXT("say"));
	const TArray<FString> Expected = {
		TEXT("What kind of a man was father?"),
		TEXT("He was a peasant like us."),
		TEXT("Was he good with the sword?"),
		TEXT("Of course not.  He was a wonderful farmer and husband."),
	};
	TestLines(*this, TEXT("spoken lines"), Texts(Said), Expected);
	TestTrue(TEXT("Dink speaks in colour 14"), DetailOf(Said, 0).StartsWith(TEXT("spk=1 col=14 id=s1-h1-m.talk.004")));
	TestTrue(TEXT("mother speaks as current_sprite in colour 13"), DetailOf(Said, 1).StartsWith(FString::Printf(TEXT("spk=%d col=13 id=s1-h1-m.talk.005"), Mom)));
	TestEqual(TEXT("&result written by the choice"), Env.Facts->GetFact(TEXT("result")), 2);
	TestFalse(TEXT("unfreeze(1) at the end"), S->GetDirector()->GetDink().bFrozen);
	CheckOriginal(*this, TEXT("s1-h1-m"), { TEXT("\"Ask about pig feeding\""), TEXT("\"Ask about your father\""), TEXT("\"Get info about the village\""),
		TEXT("\"Get angry for no reason\""), TEXT("\"Tell her you fed the pigs\""), TEXT("\"Leave\""), Expected[0], Expected[1], Expected[2], Expected[3] });

	// With &pig_story == 1 the conditional option appears (fact written through the fact store).
	S->bInstantMode = false;
	Env.Facts->SetFact(TEXT("pig_story"), 1);
	S->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), Mom);
	S->RunUntilIdle();
	TestLines(*this, TEXT("menu while &pig_story == 1"), MenuTexts(S->GetActiveMenu()),
		{ TEXT("Ask about pig feeding"), TEXT("Ask about your father"), TEXT("Get info about the village"), TEXT("Get angry for no reason"), TEXT("Tell her you fed the pigs"), TEXT("Leave") });
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeSmileSteinTalkTest, "Dink.Narrative.Talk.SmileStein", DINK_TEST_FLAGS)
bool FDinkNarrativeSmileSteinTalkTest::RunTest(const FString& Parameters)
{
	// s1-h3-of.c (farmer SmileStein), void talk: a nested menu whose first option starts the farm quest.
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	UDinkStorySubsystem* S = Env.Story;
	const int32 Farmer = S->GetDirector()->CreateVirtualSprite(1, 300, 200);
	S->StartProcedure(TEXT("s1-h3-of"), TEXT("talk"), Farmer);
	S->RunUntilIdle();
	TestLines(*this, TEXT("first menu (&farmer_quest == 0)"), MenuTexts(S->GetActiveMenu()),
		{ TEXT("Ask how the family's doing"), TEXT("Inquire about his farm"), TEXT("Ask to see Libby"), TEXT("Leave") });
	TestTrue(TEXT("choose 'Inquire about his farm'"), S->Choose(1));
	S->RunUntilIdle(); // runs into the nested menu (says block in real time, so advance)
	for (int32 i = 0; i < 100 && !S->GetActiveMenu(); ++i)
	{
		S->Advance(0.5);
	}
	TestLines(*this, TEXT("nested menu"), MenuTexts(S->GetActiveMenu()), { TEXT("Offer to take care of the problem"), TEXT("Ask what he plans to do") });
	TestEqual(TEXT("quest not started yet"), Env.Facts->GetFact(TEXT("farmer_quest")), 0);
	TestTrue(TEXT("choose 'Offer to take care of the problem'"), S->Choose(0));
	S->bInstantMode = true;
	S->RunUntilIdle();
	TestEqual(TEXT("&farmer_quest = 1 written as the original does"), Env.Facts->GetFact(TEXT("farmer_quest")), 1);
	TestEqual(TEXT("Ink sees it"), S->GetStory().GetInt(TEXT("farmer_quest")), 1);
	const TArray<FString> Expected = {
		TEXT("So how is your farm?  Growing much?"),
		TEXT("The farm... oh the farm!!  Those damn monsters,"),
		TEXT("they're really starting to bother me."),
		TEXT("They come in from the forest and tear up the fields!"),
		TEXT("I gotta do something about them soon ..."),
		TEXT("Don't worry Mr. SmileStein, I'll take care of the problem."),
		TEXT("Really Dink??  Oh thank you, thank you."),
		TEXT("Just come back and tell me when you've defeated them."),
		TEXT("No problem sir."),
	};
	TestLines(*this, TEXT("spoken lines"), Texts(Events(S, TEXT("say"))), Expected);
	CheckOriginal(*this, TEXT("s1-h3-of"), Expected);
	CheckOriginal(*this, TEXT("s1-h3-of"), { TEXT("\"Ask how the family's doing\""), TEXT("\"Inquire about his farm\""), TEXT("\"Offer to take care of the problem\"") });

	// Second talk: the quest option replaces the inquiry.
	S->bInstantMode = false;
	S->StartProcedure(TEXT("s1-h3-of"), TEXT("talk"), Farmer);
	S->RunUntilIdle();
	TestLines(*this, TEXT("menu with &farmer_quest == 1"), MenuTexts(S->GetActiveMenu()),
		{ TEXT("Ask how the family's doing"), TEXT("Ask to see Libby"), TEXT("Get info about the farm"), TEXT("Leave") });
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeTollBridgeTest, "Dink.Narrative.Talk.TollBridge", DINK_TEST_FLAGS)
bool FDinkNarrativeTollBridgeTest::RunTest(const FString& Parameters)
{
	// s1-brg2.c (the toll bridge keeper), void talk: a titled menu; paying writes &gold and &story.
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	UDinkStorySubsystem* S = Env.Story;
	// Dink's stats mirror the engine-bound facts both ways.
	UDinkStatsComponent* Stats = NewObject<UDinkStatsComponent>(GetTransientPackage());
	Stats->bMirrorToFacts = true;
	Stats->SetFactMirrorTarget(Env.Facts);
	Env.Facts->SetFact(TEXT("gold"), 150);
	TestEqual(TEXT("fact -> stats: gold 150"), Stats->Stats.Gold, 150);
	TestEqual(TEXT("fact -> Ink: gold 150"), S->GetStory().GetInt(TEXT("gold")), 150);

	const int32 Keeper = S->GetDirector()->CreateVirtualSprite(404, 300, 200);
	S->StartProcedure(TEXT("s1-brg2"), TEXT("talk"), Keeper);
	S->RunUntilIdle();
	const FDinkMenu* M = S->GetActiveMenu();
	TestNotNull(TEXT("menu"), M);
	if (M)
	{
		TestLines(*this, TEXT("title"), M->TitleLines, { TEXT("\"Hello good sir, the bridge toll is 100 gold.\"") });
		TestEqual(TEXT("title colour (set_title_color 3)"), M->TitleColor, 3);
	}
	TestLines(*this, TEXT("options"), MenuTexts(M), { TEXT("Pay the toll"), TEXT("Argue"), TEXT("Leave") });
	S->Choose(0);
	S->bInstantMode = true;
	S->RunUntilIdle();
	TestLines(*this, TEXT("spoken"), Texts(Events(S, TEXT("say"))), { TEXT("Thanks.  Have a nice day.") });
	TestEqual(TEXT("&gold -= 100 in the fact store"), Env.Facts->GetFact(TEXT("gold")), 50);
	TestEqual(TEXT("... in the player's stats"), Stats->Stats.Gold, 50);
	TestEqual(TEXT("&story = 7"), Env.Facts->GetFact(TEXT("story")), 7);
	TestNull(TEXT("kill_this_task ended the keeper's script"), S->FindInstanceForSprite(Keeper));
	if (const FDinkSprite* K = S->GetDirector()->FindSprite(Keeper))
	{
		TestEqual(TEXT("move_stop(&current_sprite, 4, -50, 1) walked him off to x -50"), (int32)FMath::RoundToInt(K->X), -50);
	}
	CheckOriginal(*this, TEXT("s1-brg2"), { TEXT("\"Hello good sir, the bridge toll is 100 gold.\""), TEXT("\"Pay the toll\""), TEXT("Thanks.  Have a nice day.") });

	// Not enough gold: the other branch, and nothing is taken.
	Env.Facts->SetFact(TEXT("gold"), 20);
	const int32 From = S->Events.Num();
	S->StartProcedure(TEXT("s1-brg2"), TEXT("talk"), S->GetDirector()->CreateVirtualSprite(404, 300, 200));
	S->RunUntilIdle(); // instant mode picks the first option
	TestLines(*this, TEXT("too poor"), Texts(Events(S, TEXT("say"), From)), { TEXT("You don't have enough gold, fool!") });
	TestEqual(TEXT("gold unchanged"), Env.Facts->GetFact(TEXT("gold")), 20);
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeFactMirrorTest, "Dink.Narrative.Facts.OneSourceOfTruth", DINK_TEST_FLAGS)
bool FDinkNarrativeFactMirrorTest::RunTest(const FString& Parameters)
{
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	FDinkInkStory& Ink = Env.Story->GetStory();
	Env.Facts->SetFact(TEXT("s2-nad"), 3);
	TestEqual(TEXT("FactSubsystem -> Ink (&s2-nad -> s2_nad)"), Ink.GetInt(TEXT("s2_nad")), 3);
	Ink.SetInt(TEXT("old_womans_duck"), 4);
	TestEqual(TEXT("Ink -> FactSubsystem"), Env.Facts->GetFact(TEXT("old_womans_duck")), 4);
	Env.Facts->AddToFact(TEXT("story"), 2);
	TestEqual(TEXT("AddToFact reaches Ink"), Ink.GetInt(TEXT("story")), 2);

	// A script assignment (s1-h1-m main, &story == 0 branch: &update_status = 1; &story = 1).
	const int32 Mom = Env.Story->GetDirector()->CreateVirtualSprite(1, 300, 200);
	Env.Facts->SetFact(TEXT("story"), 0);
	Env.Facts->SetFact(TEXT("old_womans_duck"), 0);
	Env.Story->bInstantMode = true;
	Env.Story->StartProcedure(TEXT("s1-h1-m"), TEXT("main"), Mom);
	Env.Story->RunUntilIdle();
	TestEqual(TEXT("script wrote &story = 1"), Env.Facts->GetFact(TEXT("story")), 1);
	TestEqual(TEXT("script wrote engine-bound &update_status = 1"), Env.Facts->GetFact(TEXT("update_status")), 1);
	TestEqual(TEXT("music cue from playmidi"), Env.Story->GetDirector()->Audio.CurrentMusic, FString(TEXT("5.mid")));

	// Reset (new game / load) pushes every fact again.
	Env.Facts->ResetToInitialValues();
	for (const TPair<FName, FString>& Pair : Ink.Names().GlobalToInk)
	{
		TestEqual(TEXT("after reset: ") + Pair.Key.ToString(), Ink.GetInt(Pair.Value), Env.Facts->GetFact(Pair.Key));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeBlockingTest, "Dink.Narrative.Director.BlockingOrder", DINK_TEST_FLAGS)
bool FDinkNarrativeBlockingTest::RunTest(const FString& Parameters)
{
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	UDinkStorySubsystem* S = Env.Story;
	const int32 Mom = S->GetDirector()->CreateVirtualSprite(1, 300, 200);
	const int32 Keeper = S->GetDirector()->CreateVirtualSprite(1, 400, 200);
	const int32 MomTalk = S->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), Mom);
	S->Advance(0.0);
	TestNotNull(TEXT("menu open"), S->GetActiveMenu());
	S->Choose(1); // 'Ask about your father': wait(200), then say_stop lines

	S->Advance(0.0);
	TestEqual(TEXT("wait(200) blocks: nothing said at t+0"), Events(S, TEXT("say")).Num(), 0);
	// A second instance runs while the first one waits (several scripts at once).
	const int32 KeeperHit = S->StartProcedure(TEXT("s1-brg2"), TEXT("hit"), Keeper);
	S->Advance(0.0);
	TArray<FDinkNarrativeEvent> Said = Events(S, TEXT("say"));
	TestLines(*this, TEXT("say (non-blocking) shows while the other script waits"), Texts(Said), { TEXT("Did something touch me?  A fly perhaps?") });
	const FDinkScriptInstance* Hit = S->FindInstance(KeeperHit);
	TestTrue(TEXT("say does not block: the hit procedure already ended"), Hit && Hit->State == EDinkInstanceState::Idle);
	TestEqual(TEXT("its text is still on screen"), S->GetActiveTexts().Num(), 1);

	S->Advance(0.15);
	TestEqual(TEXT("t+150 ms: mother's script still waiting"), Events(S, TEXT("say")).Num(), 1);
	S->Advance(0.06);
	Said = Events(S, TEXT("say"));
	TestEqual(TEXT("t+210 ms: the first say_stop line"), Said.Num(), 2);
	TestEqual(TEXT("it is Dink's question"), Said.Last().Text, FString(TEXT("What kind of a man was father?")));
	const FDinkScriptInstance* Talk = S->FindInstance(MomTalk);
	TestTrue(TEXT("say_stop blocks"), Talk && Talk->State == EDinkInstanceState::Blocked && Talk->Block == EDinkBlock::Say);
	// 30 characters * 77 ms = 2310 < 2700 ms minimum.
	S->Advance(2.6);
	TestEqual(TEXT("still on the line after 2.6 s"), Events(S, TEXT("say")).Num(), 2);
	S->Advance(0.15);
	S->Advance(0.25); // the wait(200) after it
	TestEqual(TEXT("after 2.7 s the line timed out; after wait(200) the answer"), Events(S, TEXT("say")).Last().Text, FString(TEXT("He was a peasant like us.")));
	TestTrue(TEXT("skip key ends a say_stop at once"), S->SkipDialogue());
	S->Advance(0.0);
	S->Advance(0.25);
	TestEqual(TEXT("after the skip and wait(200): next line"), Events(S, TEXT("say")).Last().Text, FString(TEXT("Was he good with the sword?")));

	// Command order inside one instance equals source order (#src).
	int32 LastSrc = 0;
	bool bOrdered = true;
	for (const FDinkNarrativeEvent& E : Events(S, TEXT("cmd")))
	{
		if (E.InstanceId == MomTalk)
		{
			const int32 Src = FCString::Atoi(*E.Detail.RightChop(4));
			bOrdered &= Src >= LastSrc;
			LastSrc = Src;
		}
	}
	TestTrue(TEXT("commands ran in source order"), bOrdered);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeNbspTest, "Dink.Narrative.Display.Nbsp", DINK_TEST_FLAGS)
bool FDinkNarrativeNbspTest::RunTest(const FString& Parameters)
{
	const TCHAR Nbsp = TCHAR(0x00A0);
	TestEqual(TEXT("U+00A0 becomes a space"), DinkNarrative::ToDisplayText(FString::Printf(TEXT("a%cb%c%cc"), Nbsp, Nbsp, Nbsp)), FString(TEXT("a b  c")));
	const FDinkStoryLine Parsed = FDinkStoryLine::Parse(FString::Printf(TEXT("Megapotion!%c All stats\n"), Nbsp), { TEXT("id:x.y.001"), TEXT("say:say"), TEXT("spk:1"), TEXT("col:14"), TEXT("src:3") });
	TestEqual(TEXT("parsed line display text"), Parsed.Text, FString(TEXT("Megapotion!  All stats")));
	TestEqual(TEXT("raw keeps U+00A0"), Parsed.Raw, FString::Printf(TEXT("Megapotion!%c All stats"), Nbsp));

	// From the real story: s1-h1-m talk line 115 has a double space the Ink runtime would collapse.
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	FDinkInkStory& Ink = Env.Story->GetStory();
	Ink.SwitchFlow(TEXT("nbsp"));
	Ink.ChoosePath(TEXT("d_s1_h1_m.on_talk"));
	FDinkStoryLine Found;
	for (int32 i = 0; i < 200; ++i)
	{
		if (!Ink.CanContinue())
		{
			if (Ink.GetChoices().Num() == 0)
			{
				break;
			}
			Ink.Choose(Ink.GetChoices()[1].Index);
			continue;
		}
		const FDinkStoryLine L = Ink.ContinueLine();
		if (L.Id == TEXT("s1-h1-m.talk.007"))
		{
			Found = L;
			break;
		}
	}
	TestTrue(TEXT("runtime text carries U+00A0"), Found.Raw.Contains(FString(1, &Nbsp)));
	TestEqual(TEXT("display text equals the original"), Found.Text, FString(TEXT("Of course not.  He was a wonderful farmer and husband.")));
	TestEqual(TEXT("choice text: no U+00A0 left"), DinkNarrative::ToDisplayText(FString::Printf(TEXT("Yes%cplease"), Nbsp)), FString(TEXT("Yes please")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeSaveLoadTest, "Dink.Narrative.Save.MidConversation", DINK_TEST_FLAGS)
bool FDinkNarrativeSaveLoadTest::RunTest(const FString& Parameters)
{
	FEnv A = Make(*this);
	if (!A.IsValid())
	{
		return false;
	}
	A.Facts->SetFact(TEXT("pig_story"), 1);
	A.Facts->SetFact(TEXT("gold"), 33);
	const int32 Mom = A.Story->GetDirector()->CreateVirtualSprite(1, 300, 200);
	A.Story->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), Mom);
	A.Story->RunUntilIdle();
	TestEqual(TEXT("menu open before saving"), MenuTexts(A.Story->GetActiveMenu()).Num(), 6);

	UDinkSaveGame* Save = NewObject<UDinkSaveGame>(GetTransientPackage());
	FDinkSaveContext ContextA;
	ContextA.Facts = A.Facts;
	ContextA.WorldState = A.WorldState;
	Save->CaptureFrom(ContextA);
	A.Story->CaptureToSave(Save);
	TestTrue(TEXT("narrative state in the save"), Save->SubsystemState.Contains(TEXT("narrative")));
	TArray<uint8> Bytes;
	TestTrue(TEXT("serialise"), UDinkSaveGame::SaveToBytes(Save, Bytes));

	// A different session: load into fresh subsystems, then answer the menu.
	FEnv B = Make(*this);
	B.Facts->SetFact(TEXT("gold"), 999);
	UDinkSaveGame* Loaded = UDinkSaveGame::LoadFromBytes(Bytes);
	TestNotNull(TEXT("deserialise"), Loaded);
	if (!Loaded || !B.IsValid())
	{
		return false;
	}
	FDinkSaveContext ContextB;
	ContextB.Facts = B.Facts;
	ContextB.WorldState = B.WorldState;
	TestTrue(TEXT("apply"), Loaded->ApplyTo(ContextB));
	B.Story->RestoreFromSave(Loaded);
	TestLines(*this, TEXT("same menu after load"), MenuTexts(B.Story->GetActiveMenu()),
		{ TEXT("Ask about pig feeding"), TEXT("Ask about your father"), TEXT("Get info about the village"), TEXT("Get angry for no reason"), TEXT("Tell her you fed the pigs"), TEXT("Leave") });
	TestTrue(TEXT("Dink still frozen after load"), B.Story->GetDirector()->GetDink().bFrozen);
	// No drift: every fact equals its Ink VAR.
	for (const TPair<FName, FString>& Pair : B.Story->GetStory().Names().GlobalToInk)
	{
		TestEqual(TEXT("fact == VAR after load: ") + Pair.Key.ToString(), B.Story->GetStory().GetInt(Pair.Value), B.Facts->GetFact(Pair.Key));
	}
	TestEqual(TEXT("gold back to 33"), B.Facts->GetFact(TEXT("gold")), 33);

	TestTrue(TEXT("choose 'Tell her you fed the pigs'"), B.Story->Choose(4));
	B.Story->bInstantMode = true;
	B.Story->RunUntilIdle();
	TestLines(*this, TEXT("conversation continues after load"), Texts(Events(B.Story, TEXT("say"))),
		{ TEXT("I'm finished with my chores, mother."), TEXT("Good boy.  Go visit our neighbors while I prepare dinner.") });
	TestTrue(TEXT("speaker handle survived the load"), DetailOf(Events(B.Story, TEXT("say")), 1).StartsWith(FString::Printf(TEXT("spk=%d "), Mom)));
	TestEqual(TEXT("&result = 5 (original position of the option)"), B.Facts->GetFact(TEXT("result")), 5);
	TestFalse(TEXT("unfrozen at the end"), B.Story->GetDirector()->GetDink().bFrozen);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeUnknownCommandTest, "Dink.Narrative.Director.UnknownCommand", DINK_TEST_FLAGS)
bool FDinkNarrativeUnknownCommandTest::RunTest(const FString& Parameters)
{
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	UDinkStorySubsystem* S = Env.Story;
	const int32 Id = S->StartProcedure(TEXT("s1-brg2"), TEXT("hit"), S->GetDirector()->CreateVirtualSprite(1, 300, 200));
	FDinkScriptInstance* I = S->FindInstance(Id);
	const FDinkStoryLine Line = FDinkStoryLine::Parse(TEXT(">> frobnicate 1 \"two words\""), { TEXT("cmd"), TEXT("src:7") });
	TestEqual(TEXT("parsed as a command"), Line.Kind, EDinkLineKind::Command);
	TestEqual(TEXT("name"), Line.Command, FName(TEXT("frobnicate")));
	TestLines(*this, TEXT("args"), Line.Args, { TEXT("1"), TEXT("two words") });
	AddExpectedError(TEXT("unknown director command 'frobnicate'"), EAutomationExpectedErrorFlags::Contains, 1);
	const FDinkCommandResult R = S->GetDirector()->Execute(*I, Line);
	TestEqual(TEXT("does not block"), R.Block, uint8(0));
	TestFalse(TEXT("does not end the script"), R.bEndScript);
	TestEqual(TEXT("logged once"), S->ErrorLog.Num(), 1);
	S->RunUntilIdle();
	TestEqual(TEXT("the script still runs to its end"), Events(S, TEXT("say")).Num(), 1);

	// A text line that starts with ">>" but has no #cmd tag is spoken text, not a command.
	const FDinkStoryLine Spoken = FDinkStoryLine::Parse(TEXT(">> not a command"), { TEXT("say:say"), TEXT("spk:1") });
	TestEqual(TEXT("classified by tag, not by text"), Spoken.Kind, EDinkLineKind::Spoken);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeVocabularyTest, "Dink.Narrative.Director.Vocabulary", DINK_TEST_FLAGS)
bool FDinkNarrativeVocabularyTest::RunTest(const FString& Parameters)
{
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	FString Vocabulary;
	TestTrue(TEXT("director_vocabulary.csv synced"), FFileHelper::LoadFileToString(Vocabulary, *FDinkInkStory::GetDataPath(TEXT("director_vocabulary.csv"))));
	int32 Implemented = 0, Recorded = 0, Missing = 0;
	const FString Table = Env.Story->GetDirector()->BuildStatusTable(Vocabulary, &Implemented, &Recorded, &Missing);
	TestEqual(TEXT("every vocabulary row is implemented or recorded"), Missing, 0);
	TArray<FString> Rows;
	Vocabulary.ParseIntoArrayLines(Rows);
	TestEqual(TEXT("one status row per vocabulary row"), Implemented + Recorded, Rows.Num() - 1);
	AddInfo(FString::Printf(TEXT("director status: %d implemented, %d recorded, %d not done"), Implemented, Recorded, Missing));

	const FString Generated = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("Narrative/director_status.csv"));
	FFileHelper::SaveStringToFile(Table, *Generated);
	const FString Committed = FPaths::ConvertRelativePathToFull(FPaths::ProjectPluginsDir() / TEXT("DinkNarrative/Docs/director_status.csv"));
	FString Existing;
	FFileHelper::LoadFileToString(Existing, *Committed);
	TestTrue(FString::Printf(TEXT("Plugins/DinkNarrative/Docs/director_status.csv is current (regenerate: cp %s %s)"), *Generated, *Committed),
		Existing.Replace(TEXT("\r"), TEXT("")) == Table);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeSpritesTest, "Dink.Narrative.Director.SpritesAndWorldState", DINK_TEST_FLAGS)
bool FDinkNarrativeSpritesTest::RunTest(const FString& Parameters)
{
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	UDinkStorySubsystem* S = Env.Story;
	UDinkDirector* D = S->GetDirector();
	const int32 Npc = D->CreateVirtualSprite(12, 300, 200);
	const int32 Id = S->StartProcedure(TEXT("s1-brg2"), TEXT("hit"), Npc, {}, 12);
	FDinkScriptInstance* I = S->FindInstance(Id);
	auto Run = [&](const TCHAR* Text)
	{
		const FDinkStoryLine L = FDinkStoryLine::Parse(FString(TEXT(">> ")) + Text, { TEXT("cmd"), TEXT("src:1") });
		return D->Execute(*I, L);
	};
	// Numpad 2 = south: y grows until it passes the stop y; x unchanged.
	Run(*FString::Printf(TEXT("sp_speed %d 2"), Npc));
	FDinkCommandResult R = Run(*FString::Printf(TEXT("move_stop %d 2 260 1"), Npc));
	TestEqual(TEXT("move_stop blocks on the sprite"), R.Block, uint8(EDinkBlock::Move));
	D->Tick(250.0, 250.0); // 2 x 60 px/s x 0.25 s = 30 px
	TestEqual(TEXT("moving south: y 230 after 0.25 s"), (int32)FMath::RoundToInt(D->FindSprite(Npc)->Y), 230);
	TestTrue(TEXT("still moving"), D->IsMoving(Npc));
	D->Tick(1000.0, 1250.0);
	TestFalse(TEXT("arrived"), D->IsMoving(Npc));
	TestEqual(TEXT("stopped exactly at y 260"), (int32)FMath::RoundToInt(D->FindSprite(Npc)->Y), 260);
	TestEqual(TEXT("x untouched"), (int32)FMath::RoundToInt(D->FindSprite(Npc)->X), 300);
	// Numpad 4 = west, stop coordinate is x; already past it -> done at once (engine behaviour).
	R = Run(*FString::Printf(TEXT("move_stop %d 4 400 1"), Npc));
	TestEqual(TEXT("west with stop x 400 from x 300: already past, no wait"), R.Block, uint8(0));
	// Diagonal 7 = north-west, stop is x.
	Run(*FString::Printf(TEXT("move %d 7 290 0"), Npc));
	D->Tick(100.0, 1350.0);
	TestEqual(TEXT("diagonal reaches x 290"), (int32)FMath::RoundToInt(D->FindSprite(Npc)->X), 290);
	TestEqual(TEXT("... moving up as much"), (int32)FMath::RoundToInt(D->FindSprite(Npc)->Y), 250);

	Run(*FString::Printf(TEXT("sp_x %d 123"), Npc));
	TestEqual(TEXT("sp_x sets"), D->SpriteProperty(I, TEXT("x"), Npc, -1), 123);
	Run(*FString::Printf(TEXT("sp_seq %d 371"), Npc));
	Run(*FString::Printf(TEXT("sp_base_walk %d 370"), Npc));
	TestEqual(TEXT("sp_seq recorded"), D->FindSprite(Npc)->GetProp(TEXT("seq")), 371);
	TestEqual(TEXT("sp_base_walk recorded"), D->FindSprite(Npc)->GetProp(TEXT("base_walk")), 370);
	Run(TEXT("init \"load_sequence_now graphics\\dink\\walk\\ds-w9- 79 43 38 72 -14 -9 14 9\""));
	TestEqual(TEXT("init line recorded for the animation layer"), D->InitLines.Last(), FString(TEXT("load_sequence_now graphics\\dink\\walk\\ds-w9- 79 43 38 72 -14 -9 14 9")));

	// sp(editor) and editor_type use the instance's screen.
	const int32 Placed = D->HandleForPlacement(12, 7);
	TestTrue(TEXT("sp(7) gives a handle"), Placed > 1);
	TestEqual(TEXT("sp_editor_num"), D->SpriteProperty(I, TEXT("editor_num"), Placed, -1), 7);
	Run(TEXT("editor_type 7 1"));
	TestEqual(TEXT("editor_type(7, 1) -> override on S012_P07"), Env.WorldState->GetOverrideType(FDinkOriginId(12, 7)), EDinkOverrideType::RemovedForever);
	Env.WorldState->SetOverride(FDinkOriginId(12, 9), EDinkOverrideType::RemovedForever);
	TestEqual(TEXT("sp() of a removed placement is 0"), D->HandleForPlacement(12, 9), 0);

	// sp_active 0 ends the sprite's script; wait blocks for its time.
	const int32 Other = D->CreateVirtualSprite(12, 100, 100);
	const int32 OtherId = S->StartProcedure(TEXT("s1-h1-m"), TEXT("talk"), Other);
	S->RunUntilIdle();
	Run(*FString::Printf(TEXT("sp_active %d 0"), Other));
	TestNull(TEXT("sp_active(sprite, 0) ended that sprite's script"), S->FindInstance(OtherId) && S->FindInstance(OtherId)->IsAlive() ? S->FindInstance(OtherId) : nullptr);
	R = Run(TEXT("wait 300"));
	TestEqual(TEXT("wait blocks on time"), R.Block, uint8(EDinkBlock::Time));
	TestEqual(TEXT("until now + 300 ms"), R.BlockUntilMs, S->GetNowMs() + 300.0);

	// Audio cues go to the stub.
	Run(TEXT("playsound 22 22050 0 0 0"));
	Run(TEXT("playmidi \"5.mid\""));
	TestTrue(TEXT("sound cue logged"), D->Audio.Cues.ContainsByPredicate([](const FString& C) { return C.StartsWith(TEXT("sound:22")); }));
	TestEqual(TEXT("music cue"), D->Audio.CurrentMusic, FString(TEXT("5.mid")));

	// create_sprite (value form through the EXTERNAL) gives a fresh handle with the brain recorded.
	FDinkInkStory& Ink = S->GetStory();
	TestTrue(TEXT("external create_sprite is bound"), Ink.Ink().IsExternalFunctionBound(TEXT("create_sprite")));
	const int32 Before = D->GetSprites().Num();
	R = Run(TEXT("create_sprite 340 200 7 167 1"));
	TestEqual(TEXT("create_sprite statement adds a sprite"), D->GetSprites().Num(), Before + 1);
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeSmokeTest, "Dink.Narrative.Smoke.AllEntryPoints", DINK_TEST_FLAGS)
bool FDinkNarrativeSmokeTest::RunTest(const FString& Parameters)
{
	// Every entry point once, all commands stubbed (instant), random menu choices from seed 1997,
	// 5000 lines per entry point. The report is written to Saved/Narrative/smoke_report.txt.
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	// The InkPlusPlus runtime logs some story errors itself at Error level; they belong in the report.
	AddExpectedError(TEXT("RUNTIME ERROR"), EAutomationExpectedErrorFlags::Contains, -1);
	AddExpectedMessage(TEXT("LogInkPlusPlus"), EAutomationExpectedErrorFlags::Contains, -1);
	const double Start = FPlatformTime::Seconds();
	const FDinkSmokeReport Report = Env.Story->RunSmoke(1997, 5000);
	const double Seconds = FPlatformTime::Seconds() - Start;
	const FString Path = FPaths::ProjectSavedDir() / TEXT("Narrative/smoke_report.txt");
	FFileHelper::SaveStringToFile(FString::Printf(TEXT("Dink.Narrative.Smoke.AllEntryPoints, seed 1997, cap 5000 lines, %.1f s\n\n"), Seconds) + Report.ToText(), *Path);
	AddInfo(FString::Printf(TEXT("smoke run: %d entry points, %d completed, %d hit the step cap (%d idle loops), %d stalled, %d with errors; %lld lines, %d spoken, %d commands, %d menus in %.1f s; report %s"),
		Report.EntryPoints, Report.Completed, Report.HitStepCap, Report.CapInIdleLoop, Report.Stalled, Report.WithErrors, Report.TotalLines,
		Report.SpokenLines, Report.Commands, Report.Menus, Seconds, *Path));
	TestEqual(TEXT("every entry point ran"), Report.EntryPoints, 930);
	TestEqual(TEXT("every entry point is accounted for"), Report.Completed + Report.HitStepCap + Report.Stalled, Report.EntryPoints);
	TestEqual(TEXT("nothing stalls with stubbed commands"), Report.Stalled, 0);
	TestFalse(TEXT("no unknown director command in the whole story"), Report.Errors.ContainsByPredicate([](const FString& E) { return E.Contains(TEXT("unknown director command")); }));
	// Every call target is in the story except ranstuff (called only by the dead s1-slim; the original has no ranstuff.c).
	TArray<FString> Missing;
	Report.MissingTargets.GetKeys(Missing);
	for (const FString& M : Missing)
	{
		TestTrue(TEXT("only targets the original lacks are missing: ") + M, M == TEXT("external ranstuff.small"));
	}
	TestEqual(TEXT("no runtime errors"), Report.WithErrors, 0);
	return true;
}

// ---------------------------------------------------------------------------------------------
// In the generated greybox (PIE): the new-game cutscene of Dink's mother, talking to her, the
// screen-to-world mapping of sprite coordinates, and the console commands.

namespace DinkNarrativeTest
{
	const TCHAR* NarrativeStonebrookMap = TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook");

	class FIntroCommand : public IAutomationLatentCommand
	{
	public:
		explicit FIntroCommand(FAutomationTestBase* InTest) : Test(InTest), Began(FPlatformTime::Seconds()) {}

		virtual bool Update() override
		{
			const double Now = FPlatformTime::Seconds();
			if (Now - Began > 90.0)
			{
				Test->AddError(FString::Printf(TEXT("PIE narrative check timed out at stage %d"), Stage));
				return true;
			}
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
			APawn* Pawn = PC ? PC->GetPawn() : nullptr;
			UDinkStorySubsystem* S = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
			if (!Pawn || !S || !S->IsReady())
			{
				return false;
			}
			UDinkDirector* D = S->GetDirector();
			auto FindMom = [World]() -> AActor*
			{
				for (TActorIterator<AActor> It(World); It; ++It)
				{
					const UDinkOriginComponent* O = UDinkOriginComponent::FindOnActor(*It);
					if (O && O->ScriptName == TEXT("s1-h1-m") && O->OriginId.Screen == 1)
					{
						return *It;
					}
				}
				return nullptr;
			};
			switch (Stage)
			{
			case 0: // the cutscene started when the player appeared on SCR_001 (&story == 0)
			{
				const FDinkScriptInstance* Main = nullptr;
				for (const TUniquePtr<FDinkScriptInstance>& I : S->GetInstances())
				{
					if (I->Script == TEXT("s1-h1-m") && I->Procedure == TEXT("main"))
					{
						Main = I.Get();
					}
				}
				if (!Main)
				{
					return false;
				}
				Mom = FindMom();
				Test->TestNotNull(TEXT("mother's placement actor on SCR_001"), Mom);
				MomHandle = Main->Sprite;
				Test->TestTrue(TEXT("her main runs for her actor's handle"), Mom && D->GetActor(MomHandle) == Mom);
				Test->TestEqual(TEXT("music cue 5.mid"), D->Audio.CurrentMusic, FString(TEXT("5.mid")));
				Test->TestTrue(TEXT("freeze(1): Dink frozen"), D->GetDink().bFrozen);
				Test->TestTrue(TEXT("... the player's move input is held"), PC->IsMoveInputIgnored());
				Stage = 1;
				return false;
			}
			case 1: // her first line appears over her after wait(1000)
			{
				const FDinkActiveText* Text = S->GetActiveTexts().FindByPredicate([this](const FDinkActiveText& T) { return T.Owner == MomHandle; });
				if (!Text)
				{
					return false;
				}
				Test->TestEqual(TEXT("first line of the new game"), Text->Text, FString(TEXT("Dink, would you go feed the pigs?")));
				Test->TestEqual(TEXT("in her colour (13)"), Text->Color, 13);
				Stage = 2;
				return false;
			}
			case 2: // skip through the cutscene
			{
				S->SkipDialogue();
				const FDinkScriptInstance* Main = S->FindInstanceForSprite(MomHandle, TEXT("s1-h1-m"));
				if (Main && Main->State != EDinkInstanceState::Idle)
				{
					return false;
				}
				Test->TestFalse(TEXT("unfreeze(1) at the end of the cutscene"), D->GetDink().bFrozen);
				Test->TestFalse(TEXT("... move input released"), PC->IsMoveInputIgnored());
				Test->TestEqual(TEXT("&story = 1"), S->GetFacts()->GetFact(TEXT("story")), 1);
				TArray<FString> Said;
				for (const FDinkNarrativeEvent& E : S->Events)
				{
					if (E.Kind == TEXT("say"))
					{
						Said.Add(E.Text);
					}
				}
				TestLines(*Test, TEXT("the cutscene's lines"), Said, { TEXT("Dink, would you go feed the pigs?"), TEXT("What, now?"), TEXT("YES, NOW.") });

				// Screen-to-world: a sprite pixel lands where the screen volume maps it.
				const ADinkScreenVolume* Screen = World->GetSubsystem<UDinkGreyboxSubsystem>()->FindScreen(1);
				const FDinkSprite* Sprite = D->FindSprite(MomHandle);
				if (Screen && Sprite && Mom)
				{
					const int32 NewX = FMath::RoundToInt(Sprite->X) + 40;
					D->SpriteProperty(nullptr, TEXT("x"), MomHandle, NewX);
					const FVector Expected = Screen->MapPixelToWorld(NewX - 20, Sprite->Y);
					const double Off = FVector2D(Mom->GetActorLocation() - Expected).Size();
					Test->TestTrue(FString::Printf(TEXT("sp_x moves her through DinkLayout (%.2f cm off)"), Off), Off < 1.0);
				}
				// Stand next to her, facing her, and talk (what the E key does).
				if (Mom)
				{
					const FVector To = Mom->GetActorLocation();
					const FVector At = To + FVector(0, 150, 0);
					Pawn->SetActorLocation(FVector(At.X, At.Y, Pawn->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
					Pawn->SetActorRotation((To - At).Rotation());
					Test->TestTrue(TEXT("talk key finds her"), S->TryTalk(Pawn));
				}
				Stage = 3;
				return false;
			}
			case 3:
			{
				const FDinkMenu* Menu = S->GetActiveMenu();
				if (!Menu)
				{
					return false;
				}
				TestLines(*Test, TEXT("her talk menu"), MenuTexts(Menu), { TEXT("Ask about pig feeding"), TEXT("Ask about your father"), TEXT("Get info about the village"), TEXT("Get angry for no reason"), TEXT("Leave") });
				Test->TestTrue(TEXT("Dink frozen while talking"), D->GetDink().bFrozen);
				S->Choose(4);
				Stage = 4;
				return false;
			}
			case 4:
			{
				if (D->GetDink().bFrozen)
				{
					return false;
				}
				// Console commands.
				GEngine->Exec(World, TEXT("dink.Fact story 3"));
				Test->TestEqual(TEXT("dink.Fact sets the fact"), S->GetFacts()->GetFact(TEXT("story")), 3);
				Test->TestEqual(TEXT("... and Ink sees it"), S->GetStory().GetInt(TEXT("story")), 3);
				GEngine->Exec(World, TEXT("dink.Say Hello from the console"));
				Test->TestTrue(TEXT("dink.Say shows Dink's text"), S->GetActiveTexts().ContainsByPredicate([](const FDinkActiveText& T) { return T.Owner == 1 && T.Text == TEXT("Hello from the console"); }));
				GEngine->Exec(World, TEXT("dink.Run s1-h1-m hit"));
				Stage = 5;
				return false;
			}
			case 5:
			{
				const bool bOuch = S->GetActiveTexts().ContainsByPredicate([this](const FDinkActiveText& T) { return T.Owner == MomHandle && T.Text == TEXT("Ouch!  Stop it!"); });
				if (!bOuch)
				{
					return false;
				}
				Test->TestTrue(TEXT("dink.Run s1-h1-m hit runs her hit procedure"), bOuch);
				return true;
			}
			default:
				return true;
			}
		}

	private:
		FAutomationTestBase* Test;
		double Began;
		int32 Stage = 0;
		AActor* Mom = nullptr;
		int32 MomHandle = 0;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeGreyboxTest, "Dink.Narrative.Greybox.IntroAndTalk", DINK_TEST_FLAGS)
bool FDinkNarrativeGreyboxTest::RunTest(const FString& Parameters)
{
	const FString File = FPackageName::LongPackageNameToFilename(NarrativeStonebrookMap, FPackageName::GetMapPackageExtension());
	if (!IFileManager::Get().FileExists(*File))
	{
		AddWarning(TEXT("skipped: the Stonebrook greybox is not generated (run Scripts/import_greybox.sh --region stonebrook)"));
		return true;
	}
	UWorld* Current = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
	if (!Current || Current->GetOutermost()->GetName() != NarrativeStonebrookMap)
	{
		TestNotNull(TEXT("map loads"), UEditorLoadingAndSavingUtils::LoadMap(File));
		FAssetCompilingManager::Get().FinishAllCompilation();
	}
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FIntroCommand(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeClockTest, "Dink.Narrative.Clock.FollowsWorldTime", DINK_TEST_FLAGS)
bool FDinkNarrativeClockTest::RunTest(const FString& Parameters)
{
	// The story's game clock (waits, texts, the 100 ms status update, the brains' 60 Hz frames) is the game
	// world's time: it ticks inside UWorld::Tick, so time dilation applies and a paused world stops it. Until
	// the fix the subsystem was a world-less tickable: the engine ticked it outside the world with its own
	// undilated delta, so `slomo 4` in the PIE probe sped up the pawn and the greybox but not the scripts, and
	// a paused game would have let scripts and monsters run on. Here a real game instance and its world tick by hand.
	if (!TestNotNull(TEXT("GEngine"), GEngine))
	{
		return false;
	}
	UGameInstance* GameInstance = NewObject<UGameInstance>(GEngine);
	GameInstance->InitializeStandalone();
	UWorld* World = GameInstance->GetWorld();
	UDinkStorySubsystem* S = GameInstance->GetSubsystem<UDinkStorySubsystem>();
	if (TestNotNull(TEXT("world"), World) && TestNotNull(TEXT("story subsystem"), S) && TestTrue(TEXT("story loaded"), S->IsReady()))
	{
		TestTrue(TEXT("the story ticks with its game world"), S->GetTickableGameObjectWorld() == World);
		const double T0 = S->GetNowMs();
		World->Tick(LEVELTICK_All, 0.1f);
		TestEqual(TEXT("one world tick of 100 ms: the story clock moves 100 ms"), S->GetNowMs() - T0, 100.0, 0.01);

		World->GetWorldSettings()->SetTimeDilation(4.f);
		const double T1 = S->GetNowMs();
		World->Tick(LEVELTICK_All, 0.1f);
		TestEqual(TEXT("time dilation 4 (slomo 4): 100 ms of real time is 400 ms of story time"), S->GetNowMs() - T1, 400.0, 0.01);
		World->GetWorldSettings()->SetTimeDilation(1.f);

		APlayerState* Pauser = World->SpawnActor<APlayerState>();
		World->GetWorldSettings()->SetPauserPlayerState(Pauser);
		TestTrue(TEXT("the world is paused"), World->IsPaused());
		const double T2 = S->GetNowMs();
		World->Tick(LEVELTICK_All, 0.1f);
		TestEqual(TEXT("paused: the story clock stands still"), S->GetNowMs() - T2, 0.0, 0.01);
		World->GetWorldSettings()->SetPauserPlayerState(nullptr);
		World->Tick(LEVELTICK_All, 0.1f);
		TestEqual(TEXT("unpaused: it runs again"), S->GetNowMs() - T2, 100.0, 0.01);
		if (Pauser)
		{
			Pauser->Destroy();
		}
	}
	GameInstance->Shutdown();
	if (World)
	{
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
	}
	return true;
}

// ---------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeSpScriptRunsMainTest, "Dink.Narrative.Director.SpScriptRunsMainAtOnce", DINK_TEST_FLAGS)
bool FDinkNarrativeSpScriptRunsMainTest::RunTest(const FString& Parameters)
{
	// dink.cpp:8155-8175: sp_script is kill_scripts_owned_by + load_script + `locate(script, "MAIN"); run_script(script)` on the spot, in the
	// caller's turn (unless no_running_main, dink.cpp:6812: the screen's base script during the screen build). s3-camps.c:108-113 depends on
	// it: it attaches s3-dorks (main: sp_hitpoints 100, defense 6, strength 12, touch damage 5) and then sets the knights' hit points to 40,
	// so the original's knights have 40. The remake used to start main only (it ran after the caller yielded: 100). Pitfall 53.
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	UDinkStorySubsystem* S = Env.Story;
	UDinkDirector* D = S->GetDirector();
	const int32 Caller = D->CreateVirtualSprite(12, 100, 100);
	const int32 CallerId = S->StartProcedure(TEXT("s1-brg2"), TEXT("hit"), Caller, {}, 12);
	S->RunUntilIdle();
	FDinkScriptInstance* A = S->FindInstance(CallerId);
	if (!TestNotNull(TEXT("the caller's instance (a stand-in for script A's main)"), A))
	{
		return false;
	}
	auto Run = [&](const FString& Text)
	{
		const FDinkStoryLine L = FDinkStoryLine::Parse(FString(TEXT(">> ")) + Text, { TEXT("cmd"), TEXT("src:1") });
		return D->Execute(*A, L);
	};
	// Not SpriteProperty(.., -1): reading touch_damage that way writes -1 (the engine's change_sprite_noreturn, see UDinkDirector::SpriteProperty).
	auto Read = [&](const TCHAR* Prop, int32 Handle) { return D->FindSprite(Handle)->GetProp(FName(Prop)); };

	// 1. A's main: sp_script(&s, "s3-dorks"); sp_hitpoints(&s, 40). B's main set 100 first; A's 40 comes last.
	const int32 Knight = D->CreateVirtualSprite(12, 300, 200);
	Run(FString::Printf(TEXT("sp_hitpoints %d 7"), Knight));
	Run(FString::Printf(TEXT("sp_script %d \"s3-dorks\""), Knight));
	TestEqual(TEXT("right after sp_script, B's main has already run: hit points 100 (not A's earlier 7)"), Read(TEXT("hitpoints"), Knight), 100);
	TestEqual(TEXT("... defense 6"), Read(TEXT("defense"), Knight), 6);
	TestEqual(TEXT("... strength 12"), Read(TEXT("strength"), Knight), 12);
	TestEqual(TEXT("... touch damage 5"), Read(TEXT("touch_damage"), Knight), 5);
	TestEqual(TEXT("the script is attached"), D->FindSprite(Knight)->Script, FName(TEXT("s3-dorks")));
	Run(FString::Printf(TEXT("sp_hitpoints %d 40"), Knight));
	TestEqual(TEXT("A's sp_hitpoints(&s, 40) after sp_script is what stays: 40, as in the original"), Read(TEXT("hitpoints"), Knight), 40);
	S->RunUntilIdle();
	S->Advance(0.5);
	TestEqual(TEXT("and nothing runs main again later (the old deferred main made it 100)"), Read(TEXT("hitpoints"), Knight), 40);
	const FDinkScriptInstance* B = S->FindInstanceForSprite(Knight, TEXT("s3-dorks"));
	TestTrue(TEXT("B's instance exists on the sprite and its main has returned (Idle)"), B && B->State == EDinkInstanceState::Idle);
	const FString DorksMain = DinkNarrative::EntryPath(TEXT("s3-dorks"), TEXT("main"));
	TestEqual(TEXT("B's main started exactly once"), Events(S, TEXT("start")).FilterByPredicate([&DorksMain](const FDinkNarrativeEvent& E) { return E.Text == DorksMain; }).Num(), 1);

	// 2. A main that blocks: run_script runs it until it waits, then control returns to the caller; the tick continues it.
	// s1-bul.c main: sp_speed 2 ... freeze(1); wait(200); say_stop(...) (&pig_story is 0 at the start).
	const int32 Bully = D->CreateVirtualSprite(12, 400, 200);
	const int32 SaysBefore = Events(S, TEXT("say")).Num();
	Run(FString::Printf(TEXT("sp_script %d \"s1-bul\""), Bully));
	TestEqual(TEXT("the blocking main ran up to its wait: sp_speed(2) is set when sp_script returns"), Read(TEXT("speed"), Bully), 2);
	const FDinkScriptInstance* Bul = S->FindInstanceForSprite(Bully, TEXT("s1-bul"));
	TestTrue(TEXT("its main is Blocked on the wait, not finished"), Bul && Bul->State == EDinkInstanceState::Blocked && Bul->Block == EDinkBlock::Time);
	TestEqual(TEXT("it has not said its first line yet"), Events(S, TEXT("say")).Num(), SaysBefore);
	Run(FString::Printf(TEXT("sp_speed %d 9"), Bully)); // the caller goes on in the same turn
	TestEqual(TEXT("the caller's next line ran after the main's first segment"), Read(TEXT("speed"), Bully), 9);
	S->Advance(0.25);
	Bul = S->FindInstanceForSprite(Bully, TEXT("s1-bul"));
	TestTrue(TEXT("after the wait the tick continues the main: it is on its first say_stop"), Bul && Bul->State == EDinkInstanceState::Blocked && Bul->Block == EDinkBlock::Say);
	TestEqual(TEXT("its first line"), Events(S, TEXT("say")).Last().Text, FString(TEXT("Here, piggie piggies.")));

	// 3. no_running_main (a screen's base script during the screen build): attached, main deferred, not run on the spot.
	const int32 Late = D->CreateVirtualSprite(12, 500, 200);
	{
		TGuardValue<bool> NoRunning(S->bNoRunningMain, true);
		Run(FString::Printf(TEXT("sp_script %d \"s3-dorks\""), Late));
	}
	TestEqual(TEXT("no_running_main: the script is attached"), D->FindSprite(Late)->Script, FName(TEXT("s3-dorks")));
	TestEqual(TEXT("no_running_main: main has not run on the spot"), Read(TEXT("hitpoints"), Late), 0);
	S->Advance(0.0);
	TestEqual(TEXT("no_running_main: it runs later (init_scripts)"), Read(TEXT("hitpoints"), Late), 100);

	// 4. Replacing: the old script's instance on the sprite ends (kill_scripts_owned_by), the new one runs.
	Run(FString::Printf(TEXT("sp_script %d \"s3-dorks\""), Knight));
	int32 Alive = 0;
	for (const TUniquePtr<FDinkScriptInstance>& I : S->GetInstances())
	{
		Alive += (I->IsAlive() && I->Sprite == Knight && I->ParentId == 0) ? 1 : 0;
	}
	TestEqual(TEXT("re-attaching leaves exactly one live script on the sprite (the old one was replaced)"), Alive, 1);
	TestEqual(TEXT("and its main ran at once again: 100"), Read(TEXT("hitpoints"), Knight), 100);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkNarrativeExternalSpawnRunAtOnceTest, "Dink.Narrative.Director.ExternalAndSpawnRunAtOnce", DINK_TEST_FLAGS)
bool FDinkNarrativeExternalSpawnRunAtOnceTest::RunTest(const FString& Parameters)
{
	// dink.cpp:11326-11360 (`external`: load_script, locate(child, proc), proc_return = script, run_script(child)) and dink.cpp:8181-8203
	// (`spawn`: load_script(name, 1000), locate(.., "MAIN"), run_script) run the child ON THE SPOT, in the caller's turn. The remake used to
	// start it and let it run on the next story step; the duck brain's `duckdie` (s4-duck.c: external("make", "foodduck"), then
	// `if (get_sprite_with_this_brain(3, ..) == 0) spawn("s4-end")`) then removed the sprite, ending parent and child before the child ran a
	// line, so the 27th duck of Windemere never ended the enclosure (&story 11). Pitfall 56.
	FEnv Env = Make(*this);
	if (!Env.IsValid())
	{
		return false;
	}
	UDinkStorySubsystem* S = Env.Story;
	UDinkDirector* D = S->GetDirector();
	const int32 Caller = D->CreateVirtualSprite(12, 100, 100);
	const int32 CallerId = S->StartProcedure(TEXT("s1-brg2"), TEXT("hit"), Caller, {}, 12);
	S->RunUntilIdle();
	FDinkScriptInstance* A = S->FindInstance(CallerId);
	if (!TestNotNull(TEXT("the caller's instance (a stand-in for the parent script)"), A))
	{
		return false;
	}
	auto Run = [&](const FString& Text)
	{
		const FDinkStoryLine L = FDinkStoryLine::Parse(FString(TEXT(">> ")) + Text, { TEXT("cmd"), TEXT("src:1") });
		return D->Execute(*A, L);
	};
	auto Fact = [&](const TCHAR* Name) { return Env.Facts->GetFact(FName(Name)); };
	auto Count = [&](int32 Brain, int32 PSeq)
	{
		int32 N = 0;
		for (const TPair<int32, FDinkSprite>& P : D->GetSprites())
		{
			N += (P.Value.bActive && P.Value.GetProp(TEXT("brain")) == Brain && P.Value.GetProp(TEXT("pseq")) == PSeq) ? 1 : 0;
		}
		return N;
	};
	auto EndedCount = [&](const FString& Entry)
	{
		return Events(S, TEXT("end")).FilterByPredicate([&Entry](const FDinkNarrativeEvent& E) { return E.Text == Entry; }).Num();
	};

	// 1. external, a child that ends without blocking: its effect is there when the command returns, the caller is not blocked and its
	// next line comes AFTER the child's (make.c sheart: `&save_y += 1; create_sprite(..); sp_script(&crap, "sheart")`).
	Env.Facts->SetFact(TEXT("save_x"), 200);
	Env.Facts->SetFact(TEXT("save_y"), 100);
	const FDinkCommandResult R1 = Run(TEXT("external \"make\" \"sheart\""));
	TestEqual(TEXT("external: the child ran in the caller's turn (&save_y += 1)"), Fact(TEXT("save_y")), 101);
	TestEqual(TEXT("external: the child's sprite exists (create_sprite + sp_script ran: brain 6, seq 54)"), Count(6, 54), 1);
	TestEqual(TEXT("external: the child ended without blocking, so the caller is not blocked"), static_cast<int32>(R1.Block), 0);
	TestEqual(TEXT("external: the child ended (\"external returned\")"), EndedCount(TEXT("make.sheart")), 1);
	Env.Facts->SetFact(TEXT("save_y"), 55); // the caller's own next line
	S->RunUntilIdle();
	S->Advance(0.5);
	TestEqual(TEXT("external: the caller's value stays (the old deferred child ran later and made it 56)"), Fact(TEXT("save_y")), 55);
	TestEqual(TEXT("external: the child ran once"), Events(S, TEXT("start")).FilterByPredicate([](const FDinkNarrativeEvent& E) { return E.Text == DinkNarrative::EntryPath(TEXT("make"), TEXT("sheart")); }).Num(), 1);

	// 2. spawn: the spawned main has run when the command returns (s4-end main: &s4-duck = 2; &story = 11; freeze(1); ...), owned by 1000,
	// and runs until it blocks (it walks a man in with move_stop).
	Env.Facts->SetFact(TEXT("story"), 10);
	Env.Facts->SetFact(TEXT("s4-duck"), 1);
	Run(TEXT("spawn \"s4-end\""));
	TestEqual(TEXT("spawn: the caller's next line sees the spawned main's &s4-duck = 2"), Fact(TEXT("s4-duck")), 2);
	TestEqual(TEXT("spawn: ... and &story = 11"), Fact(TEXT("story")), 11);
	const FDinkScriptInstance* Spawned = nullptr;
	for (const TUniquePtr<FDinkScriptInstance>& I : S->GetInstances())
	{
		if (I->IsAlive() && I->Script == TEXT("s4-end"))
		{
			Spawned = I.Get();
		}
	}
	TestTrue(TEXT("spawn: the new instance is owned by 1000 and Blocked at its first move_stop (it ran up to there)"),
		Spawned && Spawned->AttachedTo == UDinkDirector::HandleNoSprite && Spawned->State == EDinkInstanceState::Blocked && Spawned->Block == EDinkBlock::Move);
	TestEqual(TEXT("spawn: main started once"), Events(S, TEXT("start")).FilterByPredicate([](const FDinkNarrativeEvent& E) { return E.Text == DinkNarrative::EntryPath(TEXT("s4-end"), TEXT("main")); }).Num(), 1);

	// 3. The duck case, through the duck brain (UDinkGameplay::ProcessDamage: RunProc(duckdie), then the sprite is removed): two headless
	// ducks of s4-duck. The first one's death runs external("make", "foodduck") (a food sprite, seq 421) and finds the second alive; the second
	// one's death does the same and then spawn("s4-end"). Both children must have run although the duck's sprite and instances are removed
	// right after duckdie returns.
	Env.Facts->SetFact(TEXT("story"), 10);
	Env.Facts->SetFact(TEXT("s4-duck"), 1);
	const int32 FoodBefore = Count(6, 421);
	TArray<int32> Ducks;
	for (int32 K = 0; K < 2; ++K)
	{
		const int32 Duck = D->CreateVirtualSprite(536, 300 + 40 * K, 300);
		Ducks.Add(Duck);
		FDinkSprite* Sprite = D->FindSprite(Duck);
		Sprite->Props.Add(TEXT("brain"), 3);
		Sprite->bHeadless = true; // the body that runs on after the head flew off: its death is `duckdie`
		Run(FString::Printf(TEXT("sp_script %d \"s4-duck\""), Duck)); // main: sp_hitpoints 5
	}
	auto Kill = [&](int32 Duck)
	{
		D->FindSprite(Duck)->Damage = 5;
		S->GetGameplay()->ProcessDamage();
	};
	const int32 SpawnsBefore = Events(S, TEXT("start")).FilterByPredicate([](const FDinkNarrativeEvent& E) { return E.Text == DinkNarrative::EntryPath(TEXT("s4-end"), TEXT("main")); }).Num();
	const int32 FoodEndsBefore = EndedCount(TEXT("make.foodduck"));
	Kill(Ducks[0]);
	TestFalse(TEXT("duck 1: the body is removed"), D->FindSprite(Ducks[0]) && D->FindSprite(Ducks[0])->bActive);
	TestEqual(TEXT("duck 1: external(\"make\", \"foodduck\") ran although the sprite was removed right after (a food sprite exists)"), Count(6, 421), FoodBefore + 1);
	TestEqual(TEXT("duck 1: the child ended before its parent's next line"), EndedCount(TEXT("make.foodduck")), FoodEndsBefore + 1);
	TestEqual(TEXT("duck 1: another duck is alive, so no spawn(\"s4-end\"): &s4-duck stays 1"), Fact(TEXT("s4-duck")), 1);
	Kill(Ducks[1]);
	TestFalse(TEXT("duck 2: the body is removed"), D->FindSprite(Ducks[1]) && D->FindSprite(Ducks[1])->bActive);
	TestEqual(TEXT("duck 2: its food sprite exists too"), Count(6, 421), FoodBefore + 2);
	TestEqual(TEXT("duck 2: the last duck's duckdie reached its last line: spawn(\"s4-end\") ran (&s4-duck 2)"), Fact(TEXT("s4-duck")), 2);
	TestEqual(TEXT("duck 2: ... &story 11"), Fact(TEXT("story")), 11);
	TestEqual(TEXT("duck 2: s4-end's main started exactly once more"),
		Events(S, TEXT("start")).FilterByPredicate([](const FDinkNarrativeEvent& E) { return E.Text == DinkNarrative::EntryPath(TEXT("s4-end"), TEXT("main")); }).Num(), SpawnsBefore + 1);

	// 4. external, a child that blocks: the parent must wait for it (run_script returns at the child's first block and `external` leaves the
	// parent's script); it goes on when the child ends. s4-end main stands in for a child that blocks (move_stop).
	Env.Facts->SetFact(TEXT("story"), 10);
	Env.Facts->SetFact(TEXT("s4-duck"), 1);
	const FDinkCommandResult R4 = Run(TEXT("external \"s4-end\" \"main\""));
	TestEqual(TEXT("blocking child: it ran up to its first block in the caller's turn (&story 11)"), Fact(TEXT("story")), 11);
	TestEqual(TEXT("blocking child: the caller is blocked on the child"), static_cast<int32>(R4.Block), static_cast<int32>(EDinkBlock::Child));
	const FDinkScriptInstance* Child = S->FindInstance(R4.BlockRef);
	TestTrue(TEXT("blocking child: it is alive, Blocked, and the caller's child"), Child && Child->IsAlive() && Child->State == EDinkInstanceState::Blocked && Child->ParentId == A->Id && Child->bEndWithProcedure);
	A->State = EDinkInstanceState::Blocked; // what StepInstance does with the result
	A->Block = EDinkBlock::Child;
	A->BlockRef = R4.BlockRef;
	S->Advance(0.1);
	TestEqual(TEXT("blocking child: the caller still waits while the child lives"), static_cast<int32>(A->State), static_cast<int32>(EDinkInstanceState::Blocked));
	S->bInstantMode = true; // the moves and says finish at once
	S->RunUntilIdle();
	TestTrue(TEXT("blocking child: the child ended (end of the procedure: \"external returned\")"), !S->FindInstance(R4.BlockRef) || !S->FindInstance(R4.BlockRef)->IsAlive());
	TestTrue(TEXT("blocking child: the caller went on when it ended"), A->State != EDinkInstanceState::Blocked);
	return true;
}
