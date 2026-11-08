#include "DinkNarrativeTypes.h"

DEFINE_LOG_CATEGORY(LogDinkNarrative);
DEFINE_LOG_CATEGORY(LogDinkDirector);
DEFINE_LOG_CATEGORY(LogDinkAudio);

namespace
{
	constexpr TCHAR Nbsp = TCHAR(0x00A0);
}

FString DinkNarrative::ToDisplayText(const FString& InkText)
{
	FString Out = InkText;
	Out.ReplaceCharInline(Nbsp, TEXT(' '), ESearchCase::CaseSensitive);
	return Out;
}

TArray<FString> DinkNarrative::SplitCommandArgs(const FString& ArgText)
{
	TArray<FString> Out;
	const int32 Len = ArgText.Len();
	int32 i = 0;
	while (i < Len)
	{
		while (i < Len && ArgText[i] == TEXT(' '))
		{
			++i;
		}
		if (i >= Len)
		{
			break;
		}
		FString Token;
		if (ArgText[i] == TEXT('"'))
		{
			++i;
			while (i < Len && ArgText[i] != TEXT('"'))
			{
				Token.AppendChar(ArgText[i++]);
			}
			++i; // closing quote
		}
		else
		{
			while (i < Len && ArgText[i] != TEXT(' '))
			{
				Token.AppendChar(ArgText[i++]);
			}
		}
		Out.Add(ToDisplayText(Token));
	}
	return Out;
}

FString DinkNarrative::KnotForScript(const FString& ScriptName)
{
	return TEXT("d_") + ScriptName.ToLower().Replace(TEXT("-"), TEXT("_"));
}

FString DinkNarrative::EntryPath(const FString& ScriptName, const FString& Procedure)
{
	return KnotForScript(ScriptName) + TEXT(".on_") + Procedure.ToLower();
}

FLinearColor DinkNarrative::FontColor(int32 Index)
{
	// source/dink/dink.cpp init_font_colors (D:11709): index -> RGB.
	static const uint8 Table[16][3] = {
		{ 255, 255, 255 }, // 0: unused, white
		{ 255, 198, 255 }, { 131, 181, 74 }, { 99, 242, 247 }, { 255, 156, 74 }, { 222, 173, 255 },
		{ 244, 188, 73 }, { 173, 173, 173 }, { 85, 85, 85 }, { 148, 198, 255 }, { 0, 255, 0 },
		{ 255, 255, 2 }, { 255, 255, 2 }, { 255, 132, 132 }, { 255, 255, 2 }, { 255, 255, 255 },
	};
	const int32 I = (Index >= 1 && Index <= 15) ? Index : 15;
	return FLinearColor(FColor(Table[I][0], Table[I][1], Table[I][2]));
}

int32 DinkNarrative::TextDurationMs(int32 TextLength)
{
	// dink.h: text_timer = 77, text_min = 2700; say_text (D:4537).
	return FMath::Max(TextLength * 77, 2700);
}

bool FDinkStoryLine::IsBlockingSay() const
{
	static const FName SayStop(TEXT("say_stop")), SayStopXY(TEXT("say_stop_xy")), SayStopNpc(TEXT("say_stop_npc"));
	return Kind == EDinkLineKind::Spoken && (SayCall == SayStop || SayCall == SayStopXY || SayCall == SayStopNpc);
}

FString FDinkStoryLine::GetTagValue(const TCHAR* Key) const
{
	const FString Prefix = FString(Key) + TEXT(":");
	for (const FString& Tag : Tags)
	{
		if (Tag.StartsWith(Prefix, ESearchCase::CaseSensitive))
		{
			return Tag.Mid(Prefix.Len()).TrimStartAndEnd();
		}
	}
	return FString();
}

bool FDinkStoryLine::HasTag(const TCHAR* Key) const
{
	const FString Prefix = FString(Key) + TEXT(":");
	for (const FString& Tag : Tags)
	{
		if (Tag.Equals(Key, ESearchCase::CaseSensitive) || Tag.StartsWith(Prefix, ESearchCase::CaseSensitive))
		{
			return true;
		}
	}
	return false;
}

int32 FDinkStoryLine::ArgInt(int32 Index, int32 Default) const
{
	if (!Args.IsValidIndex(Index))
	{
		return Default;
	}
	const FString& A = Args[Index];
	if (A.IsNumeric())
	{
		return FCString::Atoi(*A);
	}
	return Default;
}

FDinkStoryLine FDinkStoryLine::Parse(const FString& RawLine, const TArray<FString>& InTags)
{
	FDinkStoryLine L;
	L.Raw = RawLine;
	while (L.Raw.EndsWith(TEXT("\n")))
	{
		L.Raw.LeftChopInline(1);
	}
	L.Tags.Reserve(InTags.Num());
	for (const FString& Tag : InTags)
	{
		L.Tags.Add(Tag.TrimStartAndEnd());
	}
	const FString Src = L.GetTagValue(TEXT("src"));
	L.SourceLine = Src.IsNumeric() ? FCString::Atoi(*Src) : 0;

	if (L.HasTag(TEXT("cmd")))
	{
		L.Kind = EDinkLineKind::Command;
		FString Body = L.Raw.TrimStartAndEnd();
		if (Body.StartsWith(TEXT(">>")))
		{
			Body.RightChopInline(2);
		}
		Body.TrimStartAndEndInline();
		L.Text = Body;
		FString Name, Rest;
		if (!Body.Split(TEXT(" "), &Name, &Rest))
		{
			Name = Body;
		}
		L.Command = FName(*Name);
		L.Args = DinkNarrative::SplitCommandArgs(Rest);
		return L;
	}

	L.Text = DinkNarrative::ToDisplayText(L.Raw);
	L.Id = L.GetTagValue(TEXT("id"));
	const FString Col = L.GetTagValue(TEXT("col"));
	if (Col.IsNumeric())
	{
		L.Color = FCString::Atoi(*Col);
	}
	L.bBlank = L.HasTag(TEXT("blank"));
	if (L.HasTag(TEXT("title")))
	{
		L.Kind = EDinkLineKind::Title;
		if (L.bBlank)
		{
			L.Text.TrimStartAndEndInline();
		}
		return L;
	}
	const FString Say = L.GetTagValue(TEXT("say"));
	if (!Say.IsEmpty())
	{
		L.Kind = EDinkLineKind::Spoken;
		L.SayCall = FName(*Say);
		L.Speaker = L.GetTagValue(TEXT("spk"));
		L.HandleVariable = L.GetTagValue(TEXT("handle"));
		const FString X = L.GetTagValue(TEXT("x"));
		const FString Y = L.GetTagValue(TEXT("y"));
		if (!X.IsEmpty() || !Y.IsEmpty())
		{
			L.bHasXY = true;
			L.X = FCString::Atoi(*X);
			L.Y = FCString::Atoi(*Y);
		}
		return L;
	}
	L.Kind = EDinkLineKind::Text;
	return L;
}
