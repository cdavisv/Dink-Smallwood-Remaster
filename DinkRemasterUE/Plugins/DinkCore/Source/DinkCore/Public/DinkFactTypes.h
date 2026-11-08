#pragma once

#include "CoreMinimal.h"
#include "DinkFactTypes.generated.h"

/** Comparison used by FDinkFactCondition. */
UENUM(BlueprintType)
enum class EDinkCompareOp : uint8
{
	Equal          UMETA(DisplayName = "=="),
	NotEqual       UMETA(DisplayName = "!="),
	Less           UMETA(DisplayName = "<"),
	LessOrEqual    UMETA(DisplayName = "<="),
	Greater        UMETA(DisplayName = ">"),
	GreaterOrEqual UMETA(DisplayName = ">="),
};

/** How a fact is used by the original game (column "kind" of dink_globals.csv). */
UENUM(BlueprintType)
enum class EDinkFactKind : uint8
{
	/** Script-only quest/story state (story, old_womans_duck, s2-nad, ...). */
	Story,
	/** Also read or written by the original engine (strength, life, player_map, ...). */
	Engine,
	/** Not in the original globals table: added at run time or by expanded content. */
	Undeclared,
};

/**
 * A test of one integer fact, e.g. {story, GreaterOrEqual, 5}.
 *
 * Shared by everything that gates on quest state: dialogue (Ink tags), State Trees, spawn
 * rules, world-variant volumes. The fact name is the original DinkC global name without '&'.
 * Text form "story >= 5" (see Parse) so conditions can live in text data.
 */
USTRUCT(BlueprintType)
struct DINKCORE_API FDinkFactCondition
{
	GENERATED_BODY()

	/** Original global name without '&' (e.g. story, old_womans_duck, s2-nad). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dink|Facts")
	FName Fact;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dink|Facts")
	EDinkCompareOp Op = EDinkCompareOp::Equal;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dink|Facts")
	int32 Value = 0;

	FDinkFactCondition() = default;
	FDinkFactCondition(FName InFact, EDinkCompareOp InOp, int32 InValue) : Fact(InFact), Op(InOp), Value(InValue) {}

	/** Applies Op to (FactValue, Value). */
	bool Evaluate(int32 FactValue) const;

	/** "story >= 5". */
	FString ToString() const;

	/**
	 * Parses "story >= 5", "&s2-nad==1", "gold < -3". Operators: == = != < <= > >=.
	 * A leading '&' on the name is dropped. Returns false on malformed input.
	 */
	static bool Parse(const FString& Text, FDinkFactCondition& Out);

	static const TCHAR* OpToString(EDinkCompareOp Op);
};

namespace DinkFacts
{
	/** Strips whitespace and a leading '&' so "&story" and "story" name the same fact. */
	DINKCORE_API FName NormalizeName(FName Name);
	DINKCORE_API FName NormalizeName(const FString& Name);
}
