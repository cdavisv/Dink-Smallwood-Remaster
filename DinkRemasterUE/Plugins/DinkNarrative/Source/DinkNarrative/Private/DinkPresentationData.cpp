#include "DinkPresentationData.h"
#include "DinkNarrativeTypes.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/Csv/CsvParser.h"

namespace
{
	/** Rows after the header, every cell trimmed; rows shorter than MinCells are dropped. */
	TArray<TArray<FString>> ReadCsv(const FString& Text, int32 MinCells)
	{
		TArray<TArray<FString>> Out;
		const FCsvParser Parser(Text);
		const FCsvParser::FRows& Rows = Parser.GetRows();
		for (int32 r = 1; r < Rows.Num(); ++r)
		{
			if (Rows[r].Num() < MinCells)
			{
				continue;
			}
			TArray<FString>& Row = Out.AddDefaulted_GetRef();
			for (const TCHAR* Cell : Rows[r])
			{
				Row.Add(FString(Cell).TrimStartAndEnd());
			}
		}
		return Out;
	}
}

FString FDinkPresentationData::GetDataDir()
{
	return FPaths::ProjectContentDir() / TEXT("Dink/Data/Presentation");
}

const FDinkPresentationData& FDinkPresentationData::Get()
{
	static const FDinkPresentationData Data = []()
	{
		FDinkPresentationData D;
		FString Text;
		if (FFileHelper::LoadFileToString(Text, *(GetDataDir() / TEXT("items.csv"))))
		{
			D.LoadItems(Text);
		}
		else
		{
			UE_LOG(LogDinkNarrative, Warning, TEXT("presentation: %s missing, item names are derived from their scripts"), *(GetDataDir() / TEXT("items.csv")));
		}
		if (FFileHelper::LoadFileToString(Text, *(GetDataDir() / TEXT("speakers.csv"))))
		{
			D.LoadSpeakers(Text);
		}
		else
		{
			UE_LOG(LogDinkNarrative, Warning, TEXT("presentation: %s missing, no speaker name plates (Scripts/export_presentation_data.py)"), *(GetDataDir() / TEXT("speakers.csv")));
		}
		return D;
	}();
	return Data;
}

bool FDinkPresentationData::LoadItems(const FString& CsvText)
{
	for (const TArray<FString>& Row : ReadCsv(CsvText, 2))
	{
		if (Row[0].IsEmpty() || Row[1].IsEmpty())
		{
			continue;
		}
		FItem& Item = Items.FindOrAdd(FName(*Row[0].ToLower()));
		Item.Name = Row[1];
		Item.Icon = Row.Num() > 2 && !Row[2].IsEmpty() ? FSoftObjectPath(Row[2]) : FSoftObjectPath();
	}
	return Items.Num() > 0;
}

bool FDinkPresentationData::LoadSpeakers(const FString& CsvText)
{
	for (const TArray<FString>& Row : ReadCsv(CsvText, 2))
	{
		if (!Row[0].IsEmpty() && !Row[1].IsEmpty())
		{
			Speakers.Add(Row[0], Row[1]);
		}
	}
	return Speakers.Num() > 0;
}

FString FDinkPresentationData::DeriveItemName(FName Script)
{
	FString Name = Script.ToString();
	Name.RemoveFromStart(TEXT("item-"), ESearchCase::IgnoreCase);
	Name.ReplaceInline(TEXT("-"), TEXT(" "));
	Name.ReplaceInline(TEXT("_"), TEXT(" "));
	if (!Name.IsEmpty())
	{
		Name[0] = FChar::ToUpper(Name[0]);
	}
	return Name;
}

FString FDinkPresentationData::ItemName(FName Script) const
{
	if (const FItem* Item = Items.Find(FName(*Script.ToString().ToLower())))
	{
		return Item->Name;
	}
	return DeriveItemName(Script);
}

FSoftObjectPath FDinkPresentationData::ItemIcon(FName Script) const
{
	const FItem* Item = Items.Find(FName(*Script.ToString().ToLower()));
	return Item ? Item->Icon : FSoftObjectPath();
}

FString FDinkPresentationData::SpeakerName(const FString& LineId, int32 Speaker) const
{
	if (const FString* Name = LineId.IsEmpty() ? nullptr : Speakers.Find(LineId))
	{
		return *Name;
	}
	return Speaker == 1 ? FString(TEXT("Dink")) : FString();
}
