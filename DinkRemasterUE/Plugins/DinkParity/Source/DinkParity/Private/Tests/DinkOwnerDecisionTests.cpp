// Dink.Narrative.OwnerDecisions.*: the fix switches the owner turned on for the shipped build (OD2 of doc/remaster/verbatim_review.md,
// 9 Nov 2026; tools/dinkink/dinkink/overrides.py OWNER_DECISIONS). Four typos made the 1997 engine drop written lines; with the switches on
// the converted story speaks them. Every other fix switch stays false (the engine's behaviour), checked by Scripts/sync_story.py.
//
//  - s2-jack.c:171  say_stop('I guess I just killed your husband.", 1);  one double quote: get_parms returns early with the speaker 0
//                   (dink.cpp:4164, 4206-4225), say_stop rejects sprite 0 (7908-7913).
//  - s4-sign3.c:17  say_stop("`%Long live the ducks.", &current_sprite;  no `)`: the speaker reads 0 (4141-4186), rejected (7908-7913).
//  - s3-chick.c:42  say_stop("`9Hello Dink, I'm Christina." &current_sprite);  no comma: get_parms returns early (4206-4225), rejected.
//  - s1-h3-8.c:13   `{` for `}`: the == 2 and == 3 tests nest inside the == 1 block (7289-7360), so two of the three bed lines never run.
//
// Expected texts are verbatim from bin/dink/story (colour codes removed); checked against the files when the data repo is next to the project.

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkNarrativeTypes.h"
#include "DinkStorySubsystem.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace DinkOwnerDecisionTest
{
	struct FEnv
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		bool IsValid() const { return Facts && Story && Story->IsReady(); }
	};

	FEnv Make(FAutomationTestBase& Test)
	{
		FEnv E;
		UGameInstance* GI = DinkTest::MakeOuterGameInstance();
		E.Facts = NewObject<UDinkFactSubsystem>(GI);
		FString Error;
		Test.TestTrue(TEXT("facts table loads"), E.Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
		UDinkWorldStateSubsystem* World = NewObject<UDinkWorldStateSubsystem>(GI);
		E.Story = NewObject<UDinkStorySubsystem>(GI);
		Test.TestTrue(FString::Printf(TEXT("story loads (%s)"), *Error), E.Story->SetupStandalone(E.Facts, World, &Error));
		E.Story->StorySeed = 1997;
		E.Story->ResetRuntime();
		E.Story->bInstantMode = true;
		return E;
	}

	/** Spoken lines (text, detail "spk=.. col=.. id=..") since event From. */
	TArray<TPair<FString, FString>> Said(const UDinkStorySubsystem* S, int32 From)
	{
		TArray<TPair<FString, FString>> Out;
		static const FName Say(TEXT("say"));
		for (int32 i = From; i < S->Events.Num(); ++i)
		{
			if (S->Events[i].Kind == Say)
			{
				Out.Emplace(S->Events[i].Text, S->Events[i].Detail);
			}
		}
		return Out;
	}

	void TestLines(FAutomationTestBase& Test, const FString& What, const TArray<TPair<FString, FString>>& Actual, const TArray<FString>& Expected)
	{
		Test.TestEqual(What + TEXT(": count"), Actual.Num(), Expected.Num());
		for (int32 i = 0; i < FMath::Min(Actual.Num(), Expected.Num()); ++i)
		{
			Test.TestEqual(FString::Printf(TEXT("%s [%d]"), *What, i), Actual[i].Key, Expected[i]);
		}
	}

	/** The written line occurs in the original script, with the typo the switch works around (when the data repo is next to the project). */
	void CheckOriginal(FAutomationTestBase& Test, const TCHAR* Script, const FString& Written)
	{
		FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("../bin/dink/story") / (FString(Script) + TEXT(".c")));
		if (!IFileManager::Get().FileExists(*Path))
		{
			Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("../Dink-Smallwood-Remaster/bin/dink/story") / (FString(Script) + TEXT(".c")));
		}
		FString Source;
		if (!FFileHelper::LoadFileToString(Source, *Path))
		{
			Test.AddInfo(FString::Printf(TEXT("data repo not found (%s): check against the original skipped"), *Path));
			return;
		}
		Test.TestTrue(FString::Printf(TEXT("%s.c has `%s`"), Script, *Written), Source.Contains(Written, ESearchCase::CaseSensitive));
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkOwnerDecisionTypoLinesTest, "Dink.Narrative.OwnerDecisions.TypoLinesSpoken", DINK_TEST_FLAGS)
bool FDinkOwnerDecisionTypoLinesTest::RunTest(const FString& Parameters)
{
	using namespace DinkOwnerDecisionTest;
	FEnv E = Make(*this);
	if (!E.IsValid())
	{
		return false;
	}
	UDinkStorySubsystem* S = E.Story;
	UDinkDirector* D = S->GetDirector();

	// s2-jack die (Jack killed; &temp2hold is Maria, set by s2-auntp): fix_s2_jack_l171.
	{
		const int32 Jack = D->CreateVirtualSprite(36, 160, 150);
		const int32 Maria = D->CreateVirtualSprite(36, 300, 200);
		E.Facts->SetFact(TEXT("temp2hold"), Maria);
		const int32 From = S->Events.Num();
		TestTrue(TEXT("s2-jack die starts"), S->StartProcedure(TEXT("s2-jack"), TEXT("die"), Jack) != 0);
		S->RunUntilIdle();
		const TArray<TPair<FString, FString>> Lines = Said(S, From);
		TestLines(*this, TEXT("s2-jack die"), Lines, {
			TEXT("Dink!  What have you done!"),
			TEXT("I guess I just killed your husband."),
			TEXT("Jack wasn't always like that.  He used to be.. <bursts into tears>"),
			TEXT("I know.  It's ok, I'm here now.") });
		TestTrue(TEXT("s2-jack.c:171 is Dink's line (spk 1, colour 14, its own ID)"), Lines.IsValidIndex(1) && Lines[1].Value.StartsWith(TEXT("spk=1 col=14 id=s2-jack.die.002")));
		CheckOriginal(*this, TEXT("s2-jack"), TEXT("say_stop('I guess I just killed your husband.\", 1);"));
	}

	// s4-sign3 talk (&story 0: the duck tax notice): fix_s4_sign3_l17.
	{
		const int32 Sign = D->CreateVirtualSprite(200, 300, 200);
		const int32 From = S->Events.Num();
		TestTrue(TEXT("s4-sign3 talk starts"), S->StartProcedure(TEXT("s4-sign3"), TEXT("talk"), Sign) != 0);
		S->RunUntilIdle();
		const TArray<TPair<FString, FString>> Lines = Said(S, From);
		TestLines(*this, TEXT("s4-sign3 talk"), Lines, {
			TEXT("Hear ye, hear ye ..."),
			TEXT("By order of our great ducks the monthly tax shall be doubled."),
			TEXT("This also applies to food donations."),
			TEXT("Long live the ducks.") });
		TestTrue(TEXT("s4-sign3.c:17 is the sign's (current_sprite, colour 15)"), Lines.IsValidIndex(3) && Lines[3].Value.StartsWith(FString::Printf(TEXT("spk=%d col=15 id=s4-sign3.talk.005"), Sign)));
		TestFalse(TEXT("unfreeze(1) still runs after it"), D->GetDink().bFrozen);
		CheckOriginal(*this, TEXT("s4-sign3"), TEXT("say_stop(\"`%Long live the ducks.\", &current_sprite;"));
	}

	// s3-chick talk, "Say hi" (&result 1): fix_s3_chick_l42.
	{
		S->bInstantMode = false;
		const int32 Christina = D->CreateVirtualSprite(586, 300, 200);
		TestTrue(TEXT("s3-chick talk starts"), S->StartProcedure(TEXT("s3-chick"), TEXT("talk"), Christina) != 0);
		S->RunUntilIdle();
		const FDinkMenu* Menu = S->GetActiveMenu();
		TestTrue(TEXT("her menu opens with \"Say hi\" first"), Menu && Menu->Choices.Num() > 0 && Menu->Choices[0].Text == TEXT("Say hi"));
		const int32 From = S->Events.Num();
		TestTrue(TEXT("choose \"Say hi\""), S->Choose(0));
		S->bInstantMode = true;
		S->RunUntilIdle();
		const TArray<TPair<FString, FString>> Lines = Said(S, From);
		TestLines(*this, TEXT("s3-chick talk, Say hi"), Lines, {
			TEXT("Hey, how's it going?"),
			TEXT("Oh hi, pretty good."),
			TEXT("My name's Dink, pleasure to meet you."),
			TEXT("Hello Dink, I'm Christina."),
			TEXT("Just having a stroll around town?"),
			TEXT("I was just taking a look at the town square."),
			TEXT("What for?"),
			TEXT("For the big parade happening soon, what else silly?"),
			TEXT("Ahh, yes.. I've ... heard of that parade.") });
		TestTrue(TEXT("s3-chick.c:42 is Christina's (current_sprite, colour 9)"), Lines.IsValidIndex(3) && Lines[3].Value.StartsWith(FString::Printf(TEXT("spk=%d col=9 id=s3-chick.talk.005"), Christina)));
		CheckOriginal(*this, TEXT("s3-chick"), TEXT("say_stop(\"`9Hello Dink, I'm Christina.\" &current_sprite);"));
	}

	// s1-h3-8 talk (Libby's bed): fix_s1_h3_8_l13, one of three lines at random.
	{
		const int32 Bed = D->CreateVirtualSprite(4, 300, 200);
		TSet<FString> Heard;
		int32 Talks = 0;
		for (; Talks < 60 && Heard.Num() < 3; ++Talks)
		{
			const int32 From = S->Events.Num();
			S->StartProcedure(TEXT("s1-h3-8"), TEXT("talk"), Bed);
			S->RunUntilIdle();
			const TArray<TPair<FString, FString>> Lines = Said(S, From);
			TestEqual(TEXT("each talk says exactly one bed line"), Lines.Num(), 1);
			for (const TPair<FString, FString>& L : Lines)
			{
				Heard.Add(L.Key);
			}
		}
		TestTrue(TEXT("Libby's bed, ahh yeah."), Heard.Contains(TEXT("Libby's bed, ahh yeah.")));
		TestTrue(TEXT("Libby's bed, to dream the impossible dream... (s1-h3-8.c:16)"), Heard.Contains(TEXT("Libby's bed, to dream the impossible dream...")));
		TestTrue(TEXT("Libby's bed, looks lonely. (s1-h3-8.c:20)"), Heard.Contains(TEXT("Libby's bed, looks lonely.")));
		AddInfo(FString::Printf(TEXT("all three bed lines within %d talks"), Talks));
	}
	return true;
}
