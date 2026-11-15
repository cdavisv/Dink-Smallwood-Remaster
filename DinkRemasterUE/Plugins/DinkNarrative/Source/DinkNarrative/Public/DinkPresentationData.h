#pragma once

#include "CoreMinimal.h"
#include "UObject/SoftObjectPath.h"

/**
 * Display data for the player-facing UI, read at run time from Content/Dink/Data/Presentation (staged with the rest of
 * Content/Dink/Data). Presentation only: nothing here changes what a script does or when.
 *
 *  - items.csv (script,name,icon): the readable name of an item or spell script for the inventory screen ("item-pig" ->
 *    "Pig Feed"), and an optional icon texture (a soft object path, e.g. /Game/Dink/UI/Items/T_Item_Pig.T_Item_Pig).
 *    Icons are an art follow-up: an empty icon draws the name's monogram. A script missing from the table gets a name
 *    derived from it ("item-xyz" -> "Xyz").
 *  - speakers.csv (line_id,name): who says a line, by the Ink line id ("s1-h1-m.talk.005" -> "Mother"); written by
 *    Scripts/export_presentation_data.py from SourceAssets/Audio/Voice/voice_lines.csv. Lines without an entry show no
 *    name plate, except Dink's own (speaker 1).
 */
class DINKNARRATIVE_API FDinkPresentationData
{
public:
	struct FItem
	{
		FString Name;
		FSoftObjectPath Icon;
	};

	/** The shared table, loaded on first use. */
	static const FDinkPresentationData& Get();
	static FString GetDataDir();

	bool LoadItems(const FString& CsvText);
	bool LoadSpeakers(const FString& CsvText);

	/** Readable item/spell name; never empty for a non-empty script. */
	FString ItemName(FName Script) const;
	/** Icon texture path, invalid when the table has none (draw the monogram). */
	FSoftObjectPath ItemIcon(FName Script) const;
	/** Speaker name for a line: the table's, else "Dink" for speaker 1, else empty (no name plate). */
	FString SpeakerName(const FString& LineId, int32 Speaker) const;

	int32 NumItems() const { return Items.Num(); }
	int32 NumSpeakers() const { return Speakers.Num(); }

	/** "item-pig" -> "Pig", "item-sw1" -> "Sw1": the fallback when the table has no row. */
	static FString DeriveItemName(FName Script);

private:
	TMap<FName, FItem> Items;
	TMap<FString, FString> Speakers;
};
