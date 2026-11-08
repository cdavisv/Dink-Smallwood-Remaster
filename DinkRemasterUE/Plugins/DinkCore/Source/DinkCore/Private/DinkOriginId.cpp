#include "DinkOriginId.h"

FString FDinkOriginId::ToString() const
{
	if (!IsValid())
	{
		return TEXT("None");
	}
	return FString::Printf(TEXT("S%03d_P%02d"), Screen, Placement);
}

namespace DinkOriginIdPrivate
{
	/** Reads 1-3 decimal digits starting at Index; advances Index. */
	static bool ReadNumber(const FString& Text, int32& Index, int32& OutValue)
	{
		int32 Digits = 0;
		int32 Value = 0;
		while (Index < Text.Len() && FChar::IsDigit(Text[Index]))
		{
			if (++Digits > 3)
			{
				return false;
			}
			Value = Value * 10 + (Text[Index] - TEXT('0'));
			++Index;
		}
		OutValue = Value;
		return Digits > 0;
	}
}

bool FDinkOriginId::Parse(const FString& Text, FDinkOriginId& Out)
{
	using namespace DinkOriginIdPrivate;

	int32 Index = 0;
	if (Text.Len() < 5 || FChar::ToUpper(Text[Index]) != TEXT('S'))
	{
		return false;
	}
	++Index;

	int32 ScreenValue = 0;
	if (!ReadNumber(Text, Index, ScreenValue))
	{
		return false;
	}
	if (Index + 1 >= Text.Len() || Text[Index] != TEXT('_') || FChar::ToUpper(Text[Index + 1]) != TEXT('P'))
	{
		return false;
	}
	Index += 2;

	int32 PlacementValue = 0;
	if (!ReadNumber(Text, Index, PlacementValue) || Index != Text.Len())
	{
		return false;
	}

	const FDinkOriginId Parsed(ScreenValue, PlacementValue);
	if (!Parsed.IsValid())
	{
		return false;
	}
	Out = Parsed;
	return true;
}
