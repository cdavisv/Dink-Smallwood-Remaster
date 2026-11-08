#include "DinkFactSubsystem.h"
#include "DinkCoreModule.h"
#include "Misc/DefaultValueHelper.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void UDinkFactSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	FString Error;
	const FString Path = GetDefaultInitialFactsPath();
	if (!LoadInitialFactsFromFile(Path, &Error))
	{
		UE_LOG(LogDink, Error, TEXT("UDinkFactSubsystem: could not load initial facts: %s"), *Error);
	}
}

FString UDinkFactSubsystem::GetDefaultInitialFactsPath()
{
	return FPaths::ConvertRelativePathToFull(FPaths::ProjectContentDir() / TEXT("Dink/Data/Facts/dink_globals.csv"));
}

bool UDinkFactSubsystem::LoadInitialFactsFromFile(const FString& Path, FString* OutError)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		if (OutError)
		{
			*OutError = FString::Printf(TEXT("cannot read '%s'"), *Path);
		}
		return false;
	}
	return LoadInitialFactsFromString(Text, OutError);
}

bool UDinkFactSubsystem::LoadInitialFactsFromString(const FString& CsvText, FString* OutError)
{
	auto Fail = [OutError](const FString& Message)
	{
		if (OutError)
		{
			*OutError = Message;
		}
		return false;
	};

	TArray<FString> Lines;
	CsvText.ParseIntoArrayLines(Lines, /*CullEmpty*/ false);

	TMap<FName, FDinkFactDefinition> NewDefinitions;
	bool bSeenHeader = false;
	for (int32 LineIndex = 0; LineIndex < Lines.Num(); ++LineIndex)
	{
		const FString Line = Lines[LineIndex].TrimStartAndEnd();
		if (Line.IsEmpty() || Line.StartsWith(TEXT("#")))
		{
			continue;
		}
		TArray<FString> Cells;
		Line.ParseIntoArray(Cells, TEXT(","), /*CullEmpty*/ false);
		for (FString& Cell : Cells)
		{
			Cell.TrimStartAndEndInline();
		}
		if (!bSeenHeader && Cells[0].Equals(TEXT("name"), ESearchCase::IgnoreCase))
		{
			bSeenHeader = true;
			continue;
		}
		if (Cells.Num() < 2)
		{
			return Fail(FString::Printf(TEXT("line %d: expected name,initial"), LineIndex + 1));
		}

		FDinkFactDefinition Def;
		Def.Name = DinkFacts::NormalizeName(Cells[0]);
		if (Def.Name.IsNone())
		{
			return Fail(FString::Printf(TEXT("line %d: empty or invalid fact name '%s'"), LineIndex + 1, *Cells[0]));
		}
		if (!FDefaultValueHelper::ParseInt(Cells[1], Def.InitialValue))
		{
			return Fail(FString::Printf(TEXT("line %d: '%s' is not an integer"), LineIndex + 1, *Cells[1]));
		}
		if (Cells.Num() >= 3 && !Cells[2].IsEmpty())
		{
			if (Cells[2].Equals(TEXT("engine"), ESearchCase::IgnoreCase))
			{
				Def.Kind = EDinkFactKind::Engine;
			}
			else if (Cells[2].Equals(TEXT("story"), ESearchCase::IgnoreCase))
			{
				Def.Kind = EDinkFactKind::Story;
			}
			else
			{
				return Fail(FString::Printf(TEXT("line %d: unknown kind '%s'"), LineIndex + 1, *Cells[2]));
			}
		}
		if (NewDefinitions.Contains(Def.Name))
		{
			return Fail(FString::Printf(TEXT("line %d: duplicate fact '%s'"), LineIndex + 1, *Def.Name.ToString()));
		}
		NewDefinitions.Add(Def.Name, Def);
	}

	if (NewDefinitions.IsEmpty())
	{
		return Fail(TEXT("no facts found"));
	}

	Definitions = MoveTemp(NewDefinitions);
	ResetToInitialValues();
	UE_LOG(LogDink, Log, TEXT("UDinkFactSubsystem: loaded %d initial facts"), Definitions.Num());
	return true;
}

void UDinkFactSubsystem::ResetToInitialValues()
{
	Values.Reset();
	for (const TPair<FName, FDinkFactDefinition>& Pair : Definitions)
	{
		Values.Add(Pair.Key, Pair.Value.InitialValue);
	}
	BroadcastReset();
}

int32 UDinkFactSubsystem::GetFact(FName Fact) const
{
	const int32* Found = Values.Find(DinkFacts::NormalizeName(Fact));
	return Found ? *Found : 0;
}

bool UDinkFactSubsystem::TryGetFact(FName Fact, int32& OutValue) const
{
	if (const int32* Found = Values.Find(DinkFacts::NormalizeName(Fact)))
	{
		OutValue = *Found;
		return true;
	}
	return false;
}

bool UDinkFactSubsystem::HasFact(FName Fact) const
{
	return Values.Contains(DinkFacts::NormalizeName(Fact));
}

void UDinkFactSubsystem::SetFact(FName Fact, int32 Value)
{
	const FName Name = DinkFacts::NormalizeName(Fact);
	if (Name.IsNone())
	{
		UE_LOG(LogDink, Warning, TEXT("UDinkFactSubsystem::SetFact called with no name"));
		return;
	}

	int32* Existing = Values.Find(Name);
	if (!Existing)
	{
		UE_LOG(LogDink, Warning, TEXT("UDinkFactSubsystem: creating undeclared fact '%s'"), *Name.ToString());
		Existing = &Values.Add(Name, 0);
	}
	const int32 OldValue = *Existing;
	if (OldValue == Value)
	{
		return;
	}
	*Existing = Value;

	if (const FDinkFactChangedNative* PerFact = PerFactDelegates.Find(Name))
	{
		// Copy first: a listener may subscribe to another fact and rehash the map.
		const FDinkFactChangedNative PerFactCopy = *PerFact;
		PerFactCopy.Broadcast(Name, OldValue, Value);
	}
	OnAnyFactChangedNative.Broadcast(Name, OldValue, Value);
	OnFactChanged.Broadcast(Name, OldValue, Value);
}

int32 UDinkFactSubsystem::AddToFact(FName Fact, int32 Delta)
{
	const int32 NewValue = GetFact(Fact) + Delta;
	SetFact(Fact, NewValue);
	return NewValue;
}

bool UDinkFactSubsystem::EvaluateCondition(const FDinkFactCondition& Condition) const
{
	return Condition.Evaluate(GetFact(Condition.Fact));
}

bool UDinkFactSubsystem::EvaluateAll(const TArray<FDinkFactCondition>& Conditions) const
{
	for (const FDinkFactCondition& Condition : Conditions)
	{
		if (!EvaluateCondition(Condition))
		{
			return false;
		}
	}
	return true;
}

EDinkFactKind UDinkFactSubsystem::GetFactKind(FName Fact) const
{
	const FDinkFactDefinition* Def = Definitions.Find(DinkFacts::NormalizeName(Fact));
	return Def ? Def->Kind : EDinkFactKind::Undeclared;
}

void UDinkFactSubsystem::RestoreFacts(const TMap<FName, int32>& Saved)
{
	Values.Reset();
	for (const TPair<FName, FDinkFactDefinition>& Pair : Definitions)
	{
		Values.Add(Pair.Key, Pair.Value.InitialValue);
	}
	for (const TPair<FName, int32>& Pair : Saved)
	{
		const FName Name = DinkFacts::NormalizeName(Pair.Key);
		if (!Name.IsNone())
		{
			Values.Add(Name, Pair.Value);
		}
	}
	BroadcastReset();
}

FDinkFactChangedNative& UDinkFactSubsystem::OnFactChangedNative(FName Fact)
{
	return PerFactDelegates.FindOrAdd(DinkFacts::NormalizeName(Fact));
}

void UDinkFactSubsystem::BroadcastReset()
{
	OnFactsResetNative.Broadcast();
	OnFactsReset.Broadcast();
}
