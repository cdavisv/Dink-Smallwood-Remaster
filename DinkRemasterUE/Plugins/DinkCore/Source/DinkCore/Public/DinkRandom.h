#pragma once

#include "CoreMinimal.h"
#include "Math/RandomStream.h"

/**
 * Injectable random source for the combat rules.
 *
 * The original engine draws with the C library's rand() and always reduces it with
 * "rand() % n" (dink.cpp). The rules in DinkCombat.h call RandomModulo(n) at exactly the
 * places the original calls rand() % n, in the same order, so a scripted source can pin
 * every roll in tests and a seeded stream gives reproducible fights.
 */
class DINKCORE_API IDinkRandomSource
{
public:
	virtual ~IDinkRandomSource() = default;

	/** Equivalent of rand() % Modulus. Modulus must be > 0; returns a value in [0, Modulus). */
	virtual int32 RandomModulo(int32 Modulus) = 0;
};

/** Production source: an FRandomStream (seedable, so replays are deterministic). */
class DINKCORE_API FDinkStreamRandomSource : public IDinkRandomSource
{
public:
	explicit FDinkStreamRandomSource(int32 Seed) : Stream(Seed) {}
	explicit FDinkStreamRandomSource(const FRandomStream& InStream) : Stream(InStream) {}

	virtual int32 RandomModulo(int32 Modulus) override
	{
		return Modulus > 0 ? Stream.RandRange(0, Modulus - 1) : 0;
	}

	FRandomStream& GetStream() { return Stream; }

private:
	FRandomStream Stream;
};

/**
 * Test source: replays a fixed list of raw "rand()" values (each reduced by % Modulus, as the
 * original does) and records every modulus requested so tests can check that a rule rolled
 * the right range. Running past the end of the list repeats the last value (0 if empty) and
 * counts an overrun, which tests should assert is zero.
 */
class DINKCORE_API FDinkScriptedRandomSource : public IDinkRandomSource
{
public:
	FDinkScriptedRandomSource() = default;
	explicit FDinkScriptedRandomSource(TArray<int32> InValues) : Values(MoveTemp(InValues)) {}

	virtual int32 RandomModulo(int32 Modulus) override
	{
		RequestedModuli.Add(Modulus);
		int32 Raw = 0;
		if (Values.IsValidIndex(NextIndex))
		{
			Raw = Values[NextIndex++];
		}
		else
		{
			++Overruns;
			Raw = Values.Num() > 0 ? Values.Last() : 0;
		}
		return Modulus > 0 ? ((Raw % Modulus) + Modulus) % Modulus : 0;
	}

	/** Every modulus passed to RandomModulo, in call order. */
	TArray<int32> RequestedModuli;
	/** Draws made after the scripted values ran out. */
	int32 Overruns = 0;
	/** Number of scripted values consumed. */
	int32 Consumed() const { return NextIndex; }

private:
	TArray<int32> Values;
	int32 NextIndex = 0;
};
