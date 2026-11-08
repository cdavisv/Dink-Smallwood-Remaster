#pragma once

#include "CoreMinimal.h"
#include "DinkNarrativeTypes.generated.h"

DINKNARRATIVE_API DECLARE_LOG_CATEGORY_EXTERN(LogDinkNarrative, Log, All);
DINKNARRATIVE_API DECLARE_LOG_CATEGORY_EXTERN(LogDinkDirector, Log, All);
DINKNARRATIVE_API DECLARE_LOG_CATEGORY_EXTERN(LogDinkAudio, Log, All);

/** What one output line of the converted story is (tools/dinkink DESIGN.md sections 3, 4 and 7). */
UENUM(BlueprintType)
enum class EDinkLineKind : uint8
{
	/** Plain text without a known tag (the converted story has none; logged). */
	Text,
	/** A say / say_stop / say_xy / say_stop_xy / say_stop_npc line (tags #id #say #spk #col #src). */
	Spoken,
	/** A director command line ">> name args" tagged #cmd. */
	Command,
	/** A title_start line shown above the next menu (#title). */
	Title,
};

/** One output line of the story, classified and with its tags parsed. */
struct DINKNARRATIVE_API FDinkStoryLine
{
	EDinkLineKind Kind = EDinkLineKind::Text;

	/** The line exactly as the Ink runtime returned it, without the trailing newline. */
	FString Raw;

	/** Display text: Raw with U+00A0 turned into ordinary spaces (DESIGN.md 3). For commands: everything after ">> ". */
	FString Text;

	/** All tags as the runtime returned them ("id:s1-h1-m.talk.001", "cmd", ...). */
	TArray<FString> Tags;

	// ---- Spoken / title lines ----

	/** #id: stable line ID (script.procedure.nnn). */
	FString Id;
	/** #say: say, say_stop, say_xy, say_stop_xy, say_stop_npc. */
	FName SayCall;
	/** #spk: an integer handle or the name of an Ink variable that holds the handle; empty for _xy lines. */
	FString Speaker;
	/** #col: colour index 1..15 (14 when the original had no colour code). */
	int32 Color = 14;
	/** #x / #y for _xy lines (original screen pixels). */
	bool bHasXY = false;
	int32 X = 0;
	int32 Y = 0;
	/** #handle: Ink variable that receives the text sprite's handle. */
	FString HandleVariable;
	/** #blank: an empty title line. */
	bool bBlank = false;

	// ---- Command lines ----

	/** Command name (lower case as written: "move_stop"). */
	FName Command;
	/** Arguments: integers as text, strings without their quotes (U+00A0 turned into spaces). */
	TArray<FString> Args;

	/** #src: line in the original .c file (0 if absent). */
	int32 SourceLine = 0;

	/** say_stop, say_stop_xy and say_stop_npc block the script until the text is gone. */
	bool IsBlockingSay() const;

	/** Value of the first tag "Key:value", or empty. */
	FString GetTagValue(const TCHAR* Key) const;
	bool HasTag(const TCHAR* Key) const;

	/** Integer argument I (0 if missing or not a number). */
	int32 ArgInt(int32 Index, int32 Default = 0) const;
	FString ArgString(int32 Index) const { return Args.IsValidIndex(Index) ? Args[Index] : FString(); }

	/** Classifies a runtime line by its tags (never by its text, DESIGN.md 7). */
	static FDinkStoryLine Parse(const FString& RawLine, const TArray<FString>& Tags);
};

/** One visible option of a menu. */
struct DINKNARRATIVE_API FDinkStoryChoice
{
	/** Index into the runtime's current choices (what ChooseChoiceIndex takes). */
	int32 Index = 0;
	/** Display text (U+00A0 turned into spaces). */
	FString Text;
	/** #opt tag: script.procedure.c<menu>.<original position>. */
	FString OptionId;
};

namespace DinkNarrative
{
	/** The one display transform of DESIGN.md 3: U+00A0 back to an ordinary space. */
	DINKNARRATIVE_API FString ToDisplayText(const FString& InkText);

	/** Splits command arguments: space separated, double-quoted strings may contain spaces. */
	DINKNARRATIVE_API TArray<FString> SplitCommandArgs(const FString& ArgText);

	/** "s1-h1-m" -> "d_s1_h1_m" (DESIGN.md 1). */
	DINKNARRATIVE_API FString KnotForScript(const FString& ScriptName);

	/** ("s1-h1-m", "talk") -> "d_s1_h1_m.on_talk". */
	DINKNARRATIVE_API FString EntryPath(const FString& ScriptName, const FString& Procedure);

	/** The original's font colour table (dink.cpp init_font_colors); index 1..15, others white. */
	DINKNARRATIVE_API FLinearColor FontColor(int32 Index);

	/** Original say_text duration: strlen * 77 ms, at least 2700 ms (dink.h text_timer, text_min). */
	DINKNARRATIVE_API int32 TextDurationMs(int32 TextLength);
}
