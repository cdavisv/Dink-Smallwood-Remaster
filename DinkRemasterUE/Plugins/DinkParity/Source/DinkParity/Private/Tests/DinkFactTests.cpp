#include "DinkTestHelpers.h"
#include "DinkFactSubsystem.h"
#include "DinkFactTypes.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFactTableTest, "Dink.Core.Facts.ShippedTable", DINK_TEST_FLAGS)
bool FDinkFactTableTest::RunTest(const FString& Parameters)
{
	UDinkFactSubsystem* Facts = DinkTest::MakeFacts(*this);

	// story/main.c declares 63 globals, 22 of them used by the engine itself (tools/dinkc facts.csv).
	TestEqual(TEXT("63 globals"), Facts->GetDefinitions().Num(), 63);
	int32 EngineCount = 0;
	for (const TPair<FName, FDinkFactDefinition>& Pair : Facts->GetDefinitions())
	{
		EngineCount += Pair.Value.Kind == EDinkFactKind::Engine ? 1 : 0;
	}
	TestEqual(TEXT("22 engine-bound globals"), EngineCount, 22);

	// New-game values from main.c.
	TestEqual(TEXT("story starts at 0"), Facts->GetFact(TEXT("story")), 0);
	TestEqual(TEXT("strength starts at 3"), Facts->GetFact(TEXT("strength")), 3);
	TestEqual(TEXT("life starts at 10"), Facts->GetFact(TEXT("life")), 10);
	TestEqual(TEXT("lifemax starts at 10"), Facts->GetFact(TEXT("lifemax")), 10);
	TestEqual(TEXT("level starts at 1"), Facts->GetFact(TEXT("level")), 1);
	TestEqual(TEXT("speed starts at 1"), Facts->GetFact(TEXT("speed")), 1);
	TestEqual(TEXT("player_map starts at 1"), Facts->GetFact(TEXT("player_map")), 1);
	TestTrue(TEXT("s2-nad exists (names with '-')"), Facts->HasFact(TEXT("s2-nad")));
	TestTrue(TEXT("old_womans_duck exists"), Facts->HasFact(TEXT("old_womans_duck")));
	TestTrue(TEXT("missle_source keeps the original spelling"), Facts->HasFact(TEXT("missle_source")));
	TestEqual(TEXT("story is a story fact"), Facts->GetFactKind(TEXT("story")), EDinkFactKind::Story);
	TestEqual(TEXT("strength is an engine fact"), Facts->GetFactKind(TEXT("strength")), EDinkFactKind::Engine);
	TestEqual(TEXT("unknown is undeclared"), Facts->GetFactKind(TEXT("no_such_fact")), EDinkFactKind::Undeclared);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFactGetSetTest, "Dink.Core.Facts.GetSetAdd", DINK_TEST_FLAGS)
bool FDinkFactGetSetTest::RunTest(const FString& Parameters)
{
	UDinkFactSubsystem* Facts = DinkTest::MakeFacts(*this);

	TestEqual(TEXT("unknown fact reads 0"), Facts->GetFact(TEXT("no_such_fact")), 0);
	int32 Value = -1;
	TestFalse(TEXT("TryGetFact on unknown"), Facts->TryGetFact(TEXT("no_such_fact"), Value));

	Facts->SetFact(TEXT("story"), 5);
	TestEqual(TEXT("set story"), Facts->GetFact(TEXT("story")), 5);
	TestEqual(TEXT("'&story' names the same fact"), Facts->GetFact(TEXT("&story")), 5);
	TestEqual(TEXT("case-insensitive"), Facts->GetFact(TEXT("STORY")), 5);

	TestEqual(TEXT("AddToFact returns new value"), Facts->AddToFact(TEXT("&story"), 2), 7);
	TestEqual(TEXT("AddToFact negative"), Facts->AddToFact(TEXT("story"), -10), -3);

	AddExpectedMessage(TEXT("creating undeclared fact"), EAutomationExpectedErrorFlags::Contains, 1);
	Facts->SetFact(TEXT("dx_new_fact"), 4);
	TestEqual(TEXT("undeclared fact created"), Facts->GetFact(TEXT("dx_new_fact")), 4);
	TestEqual(TEXT("undeclared kind"), Facts->GetFactKind(TEXT("dx_new_fact")), EDinkFactKind::Undeclared);

	Facts->ResetToInitialValues();
	TestEqual(TEXT("reset story"), Facts->GetFact(TEXT("story")), 0);
	TestFalse(TEXT("reset drops undeclared facts"), Facts->HasFact(TEXT("dx_new_fact")));
	TestEqual(TEXT("reset keeps 63"), Facts->GetAllFacts().Num(), 63);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFactDelegateTest, "Dink.Core.Facts.Delegates", DINK_TEST_FLAGS)
bool FDinkFactDelegateTest::RunTest(const FString& Parameters)
{
	UDinkFactSubsystem* Facts = DinkTest::MakeFacts(*this);

	struct FCall { FName Fact; int32 Old; int32 New; };
	TArray<FCall> AnyCalls;
	TArray<FCall> StoryCalls;
	int32 ResetCalls = 0;
	Facts->OnAnyFactChangedNative.AddLambda([&AnyCalls](FName Fact, int32 Old, int32 New) { AnyCalls.Add({ Fact, Old, New }); });
	Facts->OnFactChangedNative(TEXT("&story")).AddLambda([&StoryCalls](FName Fact, int32 Old, int32 New) { StoryCalls.Add({ Fact, Old, New }); });
	Facts->OnFactsResetNative.AddLambda([&ResetCalls]() { ++ResetCalls; });

	Facts->SetFact(TEXT("story"), 3);
	Facts->SetFact(TEXT("story"), 3); // unchanged: no event
	Facts->SetFact(TEXT("gossip"), 1);
	Facts->AddToFact(TEXT("story"), 1);

	TestEqual(TEXT("any-fact events"), AnyCalls.Num(), 3);
	TestEqual(TEXT("story events"), StoryCalls.Num(), 2);
	if (StoryCalls.Num() == 2)
	{
		TestEqual(TEXT("first story event old"), StoryCalls[0].Old, 0);
		TestEqual(TEXT("first story event new"), StoryCalls[0].New, 3);
		TestEqual(TEXT("second story event old"), StoryCalls[1].Old, 3);
		TestEqual(TEXT("second story event new"), StoryCalls[1].New, 4);
		TestEqual(TEXT("event carries the bare name"), StoryCalls[0].Fact, FName(TEXT("story")));
	}
	if (AnyCalls.Num() == 3)
	{
		TestEqual(TEXT("gossip event"), AnyCalls[1].Fact, FName(TEXT("gossip")));
	}

	// A listener that subscribes to more facts while being notified must not break dispatch.
	Facts->OnFactChangedNative(TEXT("mayor")).AddLambda([Facts](FName, int32, int32)
	{
		for (int32 i = 0; i < 64; ++i)
		{
			Facts->OnFactChangedNative(FName(*FString::Printf(TEXT("dx_listener_%d"), i)));
		}
	});
	Facts->SetFact(TEXT("mayor"), 1);
	TestEqual(TEXT("mayor set"), Facts->GetFact(TEXT("mayor")), 1);

	Facts->ResetToInitialValues();
	TestEqual(TEXT("reset event"), ResetCalls, 1);
	TestEqual(TEXT("reset fires no per-fact events"), StoryCalls.Num(), 2);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFactConditionTest, "Dink.Core.Facts.Conditions", DINK_TEST_FLAGS)
bool FDinkFactConditionTest::RunTest(const FString& Parameters)
{
	UDinkFactSubsystem* Facts = DinkTest::MakeFacts(*this);
	Facts->SetFact(TEXT("story"), 5);

	struct FCase { EDinkCompareOp Op; int32 Value; bool bExpected; };
	const FCase Cases[] = {
		{ EDinkCompareOp::Equal, 5, true },          { EDinkCompareOp::Equal, 4, false },
		{ EDinkCompareOp::NotEqual, 4, true },       { EDinkCompareOp::NotEqual, 5, false },
		{ EDinkCompareOp::Less, 6, true },           { EDinkCompareOp::Less, 5, false },
		{ EDinkCompareOp::LessOrEqual, 5, true },    { EDinkCompareOp::LessOrEqual, 4, false },
		{ EDinkCompareOp::Greater, 4, true },        { EDinkCompareOp::Greater, 5, false },
		{ EDinkCompareOp::GreaterOrEqual, 5, true }, { EDinkCompareOp::GreaterOrEqual, 6, false },
	};
	for (const FCase& Case : Cases)
	{
		const FDinkFactCondition Condition(TEXT("story"), Case.Op, Case.Value);
		TestEqual(FString::Printf(TEXT("story(5) %s"), *Condition.ToString()), Facts->EvaluateCondition(Condition), Case.bExpected);
	}

	TestTrue(TEXT("unknown fact compares as 0"), Facts->EvaluateCondition(FDinkFactCondition(TEXT("no_such_fact"), EDinkCompareOp::Equal, 0)));
	TestTrue(TEXT("empty list is true"), Facts->EvaluateAll({}));
	TestTrue(TEXT("all true"), Facts->EvaluateAll({
		FDinkFactCondition(TEXT("story"), EDinkCompareOp::GreaterOrEqual, 5),
		FDinkFactCondition(TEXT("strength"), EDinkCompareOp::Equal, 3) }));
	TestFalse(TEXT("one false"), Facts->EvaluateAll({
		FDinkFactCondition(TEXT("story"), EDinkCompareOp::GreaterOrEqual, 5),
		FDinkFactCondition(TEXT("strength"), EDinkCompareOp::Greater, 3) }));

	// Text form.
	FDinkFactCondition Parsed;
	TestTrue(TEXT("parse 's2-nad>=2'"), FDinkFactCondition::Parse(TEXT("s2-nad>=2"), Parsed));
	TestEqual(TEXT("name with '-'"), Parsed.Fact, FName(TEXT("s2-nad")));
	TestEqual(TEXT(">= op"), Parsed.Op, EDinkCompareOp::GreaterOrEqual);
	TestEqual(TEXT("value 2"), Parsed.Value, 2);

	TestTrue(TEXT("parse '&story == 5'"), FDinkFactCondition::Parse(TEXT("  &story == 5 "), Parsed));
	TestEqual(TEXT("& stripped"), Parsed.Fact, FName(TEXT("story")));
	TestEqual(TEXT("== op"), Parsed.Op, EDinkCompareOp::Equal);

	TestTrue(TEXT("parse 'gold<-3'"), FDinkFactCondition::Parse(TEXT("gold<-3"), Parsed));
	TestEqual(TEXT("< op"), Parsed.Op, EDinkCompareOp::Less);
	TestEqual(TEXT("negative value"), Parsed.Value, -3);

	TestTrue(TEXT("parse 'x != 0'"), FDinkFactCondition::Parse(TEXT("x != 0"), Parsed));
	TestEqual(TEXT("!= op"), Parsed.Op, EDinkCompareOp::NotEqual);
	TestTrue(TEXT("parse 'x > 1'"), FDinkFactCondition::Parse(TEXT("x > 1"), Parsed));
	TestEqual(TEXT("> op"), Parsed.Op, EDinkCompareOp::Greater);
	TestTrue(TEXT("parse 'x <= 1'"), FDinkFactCondition::Parse(TEXT("x <= 1"), Parsed));
	TestEqual(TEXT("<= op"), Parsed.Op, EDinkCompareOp::LessOrEqual);
	TestTrue(TEXT("single '=' accepted as =="), FDinkFactCondition::Parse(TEXT("x = 1"), Parsed));
	TestEqual(TEXT("= op"), Parsed.Op, EDinkCompareOp::Equal);

	TestTrue(TEXT("ToString/Parse round trip"), FDinkFactCondition::Parse(FDinkFactCondition(TEXT("s2-nad"), EDinkCompareOp::LessOrEqual, -7).ToString(), Parsed)
		&& Parsed.Fact == FName(TEXT("s2-nad")) && Parsed.Op == EDinkCompareOp::LessOrEqual && Parsed.Value == -7);

	for (const TCHAR* Bad : { TEXT("story"), TEXT("story >"), TEXT("== 5"), TEXT("story >= x"), TEXT("story => 5"),
		TEXT("story ! 5"), TEXT("two words == 1"), TEXT("") })
	{
		TestFalse(FString::Printf(TEXT("rejects '%s'"), Bad), FDinkFactCondition::Parse(Bad, Parsed));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFactLoadTest, "Dink.Core.Facts.LoadAndRestore", DINK_TEST_FLAGS)
bool FDinkFactLoadTest::RunTest(const FString& Parameters)
{
	UDinkFactSubsystem* Facts = NewObject<UDinkFactSubsystem>(DinkTest::MakeOuterGameInstance());
	FString Error;
	TestTrue(TEXT("load CSV text"), Facts->LoadInitialFactsFromString(
		TEXT("# comment\nname,initial,kind\n&story,2,story\nstrength,3,engine\n\nnokind,9\n"), &Error));
	TestEqual(TEXT("3 facts"), Facts->GetAllFacts().Num(), 3);
	TestEqual(TEXT("'&' stripped on load"), Facts->GetFact(TEXT("story")), 2);
	TestEqual(TEXT("kind defaults to story"), Facts->GetFactKind(TEXT("nokind")), EDinkFactKind::Story);

	TestFalse(TEXT("duplicate rejected"), Facts->LoadInitialFactsFromString(TEXT("a,1\na,2\n"), &Error));
	TestTrue(TEXT("error names the duplicate"), Error.Contains(TEXT("duplicate")));
	TestFalse(TEXT("non-integer rejected"), Facts->LoadInitialFactsFromString(TEXT("a,x\n"), &Error));
	TestFalse(TEXT("unknown kind rejected"), Facts->LoadInitialFactsFromString(TEXT("a,1,weird\n"), &Error));
	TestFalse(TEXT("empty rejected"), Facts->LoadInitialFactsFromString(TEXT("# nothing\n"), &Error));
	TestFalse(TEXT("missing file rejected"), Facts->LoadInitialFactsFromFile(TEXT("/nonexistent/dink_globals.csv"), &Error));
	TestEqual(TEXT("failed loads keep the previous table"), Facts->GetAllFacts().Num(), 3);

	Facts->SetFact(TEXT("story"), 9);
	TMap<FName, int32> Saved;
	Saved.Add(TEXT("story"), 11);
	Saved.Add(TEXT("&dx_saved_only"), 4);
	Facts->RestoreFacts(Saved);
	TestEqual(TEXT("restored story"), Facts->GetFact(TEXT("story")), 11);
	TestEqual(TEXT("unsaved facts back to initial"), Facts->GetFact(TEXT("nokind")), 9);
	TestEqual(TEXT("save-only fact kept, name normalised"), Facts->GetFact(TEXT("dx_saved_only")), 4);
	return true;
}
