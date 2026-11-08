#include "DinkFactTypes.h"
#include "Misc/DefaultValueHelper.h"

bool FDinkFactCondition::Evaluate(int32 FactValue) const
{
	switch (Op)
	{
	case EDinkCompareOp::Equal:          return FactValue == Value;
	case EDinkCompareOp::NotEqual:       return FactValue != Value;
	case EDinkCompareOp::Less:           return FactValue < Value;
	case EDinkCompareOp::LessOrEqual:    return FactValue <= Value;
	case EDinkCompareOp::Greater:        return FactValue > Value;
	case EDinkCompareOp::GreaterOrEqual: return FactValue >= Value;
	}
	return false;
}

const TCHAR* FDinkFactCondition::OpToString(EDinkCompareOp InOp)
{
	switch (InOp)
	{
	case EDinkCompareOp::Equal:          return TEXT("==");
	case EDinkCompareOp::NotEqual:       return TEXT("!=");
	case EDinkCompareOp::Less:           return TEXT("<");
	case EDinkCompareOp::LessOrEqual:    return TEXT("<=");
	case EDinkCompareOp::Greater:        return TEXT(">");
	case EDinkCompareOp::GreaterOrEqual: return TEXT(">=");
	}
	return TEXT("?");
}

FString FDinkFactCondition::ToString() const
{
	return FString::Printf(TEXT("%s %s %d"), *Fact.ToString(), OpToString(Op), Value);
}

bool FDinkFactCondition::Parse(const FString& Text, FDinkFactCondition& Out)
{
	// Find the operator: the first of = ! < >. Fact names may contain '-' and digits
	// (s2-nad) but never these characters.
	int32 OpStart = INDEX_NONE;
	for (int32 i = 0; i < Text.Len(); ++i)
	{
		const TCHAR C = Text[i];
		if (C == TEXT('=') || C == TEXT('!') || C == TEXT('<') || C == TEXT('>'))
		{
			OpStart = i;
			break;
		}
	}
	if (OpStart == INDEX_NONE)
	{
		return false;
	}

	const TCHAR First = Text[OpStart];
	const bool bHasEquals = OpStart + 1 < Text.Len() && Text[OpStart + 1] == TEXT('=');
	EDinkCompareOp ParsedOp;
	switch (First)
	{
	case TEXT('='): ParsedOp = EDinkCompareOp::Equal; break;
	case TEXT('!'):
		if (!bHasEquals) { return false; }
		ParsedOp = EDinkCompareOp::NotEqual; break;
	case TEXT('<'): ParsedOp = bHasEquals ? EDinkCompareOp::LessOrEqual : EDinkCompareOp::Less; break;
	default:        ParsedOp = bHasEquals ? EDinkCompareOp::GreaterOrEqual : EDinkCompareOp::Greater; break;
	}
	const int32 OpLen = bHasEquals ? 2 : 1;

	const FString NamePart = Text.Left(OpStart).TrimStartAndEnd();
	const FString ValuePart = Text.Mid(OpStart + OpLen).TrimStartAndEnd();
	const FName Name = DinkFacts::NormalizeName(NamePart);
	if (Name.IsNone())
	{
		return false;
	}
	int32 ParsedValue = 0;
	if (ValuePart.IsEmpty() || !FDefaultValueHelper::ParseInt(ValuePart, ParsedValue))
	{
		return false;
	}

	Out = FDinkFactCondition(Name, ParsedOp, ParsedValue);
	return true;
}

FName DinkFacts::NormalizeName(const FString& Name)
{
	FString Trimmed = Name.TrimStartAndEnd();
	if (Trimmed.StartsWith(TEXT("&")))
	{
		Trimmed.RightChopInline(1);
	}
	for (const TCHAR C : Trimmed)
	{
		if (FChar::IsWhitespace(C))
		{
			return NAME_None;
		}
	}
	return Trimmed.IsEmpty() ? NAME_None : FName(*Trimmed);
}

FName DinkFacts::NormalizeName(FName Name)
{
	if (Name.IsNone())
	{
		return Name;
	}
	// Fast path: most callers already pass normalized names.
	const FString AsString = Name.ToString();
	if (!AsString.StartsWith(TEXT("&")) && AsString.TrimStartAndEnd().Len() == AsString.Len())
	{
		return Name;
	}
	return NormalizeName(AsString);
}
