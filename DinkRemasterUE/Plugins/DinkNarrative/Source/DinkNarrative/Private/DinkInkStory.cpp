#include "DinkInkStory.h"
#include "Ink/Choice.h"
#include "Ink/Container.h"
#include "Ink/Path.h"
#include "Ink/SearchResult.h"
#include "Ink/StoryState.h"
#include "Ink/VariableState.h"
#include "Dom/JsonObject.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

// ---------------------------------------------------------------------------------------------
// Names table

bool FDinkStoryNames::LoadFromCsv(const FString& CsvText, FString* OutError)
{
	*this = FDinkStoryNames();
	TArray<FString> Lines;
	CsvText.ParseIntoArrayLines(Lines);
	if (Lines.Num() < 2 || !Lines[0].StartsWith(TEXT("kind,original,ink,scope,script")))
	{
		if (OutError)
		{
			*OutError = TEXT("names.csv: unexpected header");
		}
		return false;
	}
	for (int32 i = 1; i < Lines.Num(); ++i)
	{
		TArray<FString> F;
		Lines[i].ParseIntoArray(F, TEXT(","), /*CullEmpty*/ false);
		if (F.Num() < 5)
		{
			continue;
		}
		const FString& Kind = F[0];
		const FString& Original = F[1];
		const FString& InkName = F[2];
		const FName Script(*F[4]);
		if (Kind == TEXT("global"))
		{
			FString Fact = Original;
			Fact.RemoveFromStart(TEXT("&"));
			GlobalToInk.Add(FName(*Fact), InkName);
			InkToGlobal.Add(InkName, FName(*Fact));
		}
		else if (Kind == TEXT("local"))
		{
			ScriptLocals.FindOrAdd(Script).Add(InkName);
		}
		else if (Kind == TEXT("knot"))
		{
			ScriptToKnot.Add(FName(*Original), InkName);
		}
		else if (Kind == TEXT("entry"))
		{
			FString ScriptPart, Proc;
			Original.Split(TEXT(":"), &ScriptPart, &Proc);
			EntryPaths.Add(InkName);
			Entries.Add({ InkName, FName(*ScriptPart), FName(*Proc) });
		}
		else if (Kind == TEXT("pseudo"))
		{
			PseudoVariables.Add(InkName);
		}
	}
	return true;
}

bool FDinkStoryNames::HasEntry(FName Script, FName Procedure) const
{
	return EntryPaths.Contains(DinkNarrative::EntryPath(Script.ToString(), Procedure.ToString()));
}

// ---------------------------------------------------------------------------------------------

FDinkInkStory::FDinkInkStory() = default;

FDinkInkStory::~FDinkInkStory()
{
	if (TSharedPtr<Ink::FVariableState> State = HookedState.Pin())
	{
		State->VariableChanged.Remove(VariableHandle);
	}
}

FString FDinkInkStory::GetDataPath(const TCHAR* File)
{
	return FPaths::ProjectContentDir() / TEXT("Dink/Data/Story") / File;
}

bool FDinkInkStory::Load(const FString& StoryJson, const FString& NamesCsv, FString* OutError)
{
	// Check the format version before handing the text to the runtime (it asserts on garbage).
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(StoryJson);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid() || !Root->HasField(TEXT("root")))
	{
		if (OutError)
		{
			*OutError = TEXT("story JSON does not parse or has no root");
		}
		return false;
	}
	InkVersion = static_cast<int32>(Root->GetNumberField(TEXT("inkVersion")));
	if (InkVersion < 18 || InkVersion > 21)
	{
		if (OutError)
		{
			*OutError = FString::Printf(TEXT("ink JSON version %d not supported by InkPlusPlus (18..21)"), InkVersion);
		}
		return false;
	}
	Root.Reset();

	if (!NamesTable.LoadFromCsv(NamesCsv, OutError))
	{
		return false;
	}
	Story = MakeShared<Ink::FStory>(StoryJson);
	Story->OnError().AddLambda([this](const FString& Message, Ink::EErrorType Type)
	{
		PendingErrors.Add(FString::Printf(TEXT("%s: %s"), Type == Ink::EErrorType::Warning ? TEXT("warning") : TEXT("error"), *Message));
	});
	HookState();
	return true;
}

void FDinkInkStory::HookState()
{
	TSharedPtr<Ink::FVariableState> State = Story->GetVariablesState();
	if (HookedState.Pin() == State)
	{
		return;
	}
	if (TSharedPtr<Ink::FVariableState> Old = HookedState.Pin())
	{
		Old->VariableChanged.Remove(VariableHandle);
	}
	VariableHandle = State->VariableChanged.AddRaw(this, &FDinkInkStory::HandleVariableChanged);
	HookedState = State;
}

void FDinkInkStory::HandleVariableChanged(const FString& Name, TSharedPtr<Ink::FObject> Value)
{
	if (!OnIntVariableChanged)
	{
		return;
	}
	if (TSharedPtr<Ink::FValueInt> Int = Ink::FObject::DynamicCastTo<Ink::FValueInt>(Value))
	{
		OnIntVariableChanged(Name, Int->GetValue());
	}
	else if (TSharedPtr<Ink::FValueBool> Bool = Ink::FObject::DynamicCastTo<Ink::FValueBool>(Value))
	{
		OnIntVariableChanged(Name, Bool->GetValue() ? 1 : 0);
	}
	else if (TSharedPtr<Ink::FValueFloat> Float = Ink::FObject::DynamicCastTo<Ink::FValueFloat>(Value))
	{
		OnIntVariableChanged(Name, static_cast<int32>(Float->GetValue()));
	}
}

bool FDinkInkStory::HasPath(const FString& Path) const
{
	if (!Story.IsValid() || Path.IsEmpty())
	{
		return false;
	}
	const Ink::FSearchResult Result = Story->ContentAtPath(MakeShared<Ink::FPath>(Path));
	return Result.GetObject().IsValid() && !Result.GetIsApproximate();
}

bool FDinkInkStory::HasKnot(const FString& Knot) const
{
	return Story.IsValid() && Story->KnotContainerWithName(Knot).IsValid();
}

bool FDinkInkStory::HasVariable(const FString& Name) const
{
	return Story.IsValid() && Story->GetVariablesState()->GlobalVariableExistsWithName(Name);
}

int32 FDinkInkStory::GetInt(const FString& Name, int32 Default) const
{
	if (!HasVariable(Name))
	{
		return Default;
	}
	const TSharedPtr<Ink::FObject> Obj = Story->GetVariablesState()->GetVariable(Name);
	if (TSharedPtr<Ink::FValueInt> Int = Ink::FObject::DynamicCastTo<Ink::FValueInt>(Obj))
	{
		return Int->GetValue();
	}
	if (TSharedPtr<Ink::FValueBool> Bool = Ink::FObject::DynamicCastTo<Ink::FValueBool>(Obj))
	{
		return Bool->GetValue() ? 1 : 0;
	}
	if (TSharedPtr<Ink::FValueFloat> Float = Ink::FObject::DynamicCastTo<Ink::FValueFloat>(Obj))
	{
		return static_cast<int32>(Float->GetValue());
	}
	return Default;
}

FString FDinkInkStory::GetString(const FString& Name) const
{
	if (!HasVariable(Name))
	{
		return FString();
	}
	const TSharedPtr<Ink::FObject> Obj = Story->GetVariablesState()->GetVariable(Name);
	if (TSharedPtr<Ink::FValueString> Str = Ink::FObject::DynamicCastTo<Ink::FValueString>(Obj))
	{
		return Str->GetValue();
	}
	return FString::FromInt(GetInt(Name));
}

bool FDinkInkStory::SetInt(const FString& Name, int32 Value)
{
	if (!HasVariable(Name))
	{
		return false;
	}
	if (GetInt(Name, Value + 1) == Value)
	{
		return true; // unchanged: no observer echo
	}
	Story->GetVariablesState()->SetVariable(Name, MakeShared<Ink::FValueInt>(Value));
	return true;
}

void FDinkInkStory::ResetState(int32 Seed)
{
	Story->ResetState();
	Story->GetStoryState()->SetStorySeed(Seed);
	HookState();
	PendingErrors.Reset();
}

FString FDinkInkStory::SaveStateJson() const
{
	return Story->GetStoryState()->ToJson();
}

bool FDinkInkStory::LoadStateJson(const FString& Json)
{
	TSharedPtr<FJsonObject> Obj;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Json);
	if (!FJsonSerializer::Deserialize(Reader, Obj) || !Obj.IsValid() || !Obj->HasField(TEXT("inkSaveVersion")))
	{
		return false;
	}
	Story->GetStoryState()->LoadJSONObj(*Obj);
	HookState();
	return true;
}

void FDinkInkStory::SwitchFlow(const FString& Flow)
{
	Story->SwitchFlow(Flow);
}

void FDinkInkStory::RemoveFlow(const FString& Flow)
{
	// An instance created by load_script but never started has no flow (and the runtime's flow map may not exist yet).
	if (Story->AliveFlowNames().Contains(Flow))
	{
		Story->RemoveFlow(Flow);
	}
}

TArray<FString> FDinkInkStory::AliveFlows() const
{
	return Story->AliveFlowNames();
}

void FDinkInkStory::ChoosePath(const FString& Path)
{
	Story->ChoosePathString(Path, /*resetCallstack*/ true, {});
}

bool FDinkInkStory::CanContinue() const
{
	return Story->CanContinue();
}

FDinkStoryLine FDinkInkStory::ContinueLine()
{
	const FString Raw = Story->Continue();
	return FDinkStoryLine::Parse(Raw, Story->GetCurrentTags());
}

TArray<FDinkStoryChoice> FDinkInkStory::GetChoices() const
{
	TArray<FDinkStoryChoice> Out;
	for (const TSharedPtr<Ink::FChoice>& C : Story->GetCurrentChoices())
	{
		FDinkStoryChoice Choice;
		Choice.Index = C->GetIndex();
		Choice.Text = DinkNarrative::ToDisplayText(C->GetText()).TrimStartAndEnd();
		for (const FString& Tag : C->GetTags())
		{
			const FString T = Tag.TrimStartAndEnd();
			if (T.StartsWith(TEXT("opt:")))
			{
				Choice.OptionId = T.Mid(4);
			}
		}
		Out.Add(MoveTemp(Choice));
	}
	return Out;
}

void FDinkInkStory::Choose(int32 ChoiceIndex)
{
	Story->ChooseChoiceIndex(ChoiceIndex);
}

TArray<FString> FDinkInkStory::TakeErrors()
{
	TArray<FString> Out = MoveTemp(PendingErrors);
	PendingErrors.Reset();
	// Errors the runtime keeps in its state (when no OnError handler fired) are reported too.
	if (Story.IsValid() && (Story->HasError() || Story->HasWarning()))
	{
		for (const FString& E : Story->GetCurrentErrors())
		{
			Out.Add(TEXT("error: ") + E);
		}
		for (const FString& W : Story->GetCurrentWarnings())
		{
			Out.Add(TEXT("warning: ") + W);
		}
		Story->ResetErrors();
	}
	return Out;
}

void FDinkInkStory::BindExternal(const FString& Name, FExternal Function)
{
	if (Story->IsExternalFunctionBound(Name))
	{
		Story->UnbindExternalFunction(Name);
	}
	TSharedPtr<FStoryExternalFunction> Delegate = MakeShared<FStoryExternalFunction>();
	Delegate->BindLambda([Function = MoveTemp(Function)](const TArray<Ink::FValueType>& Args) -> TSharedPtr<Ink::FValueType>
	{
		return Function(Args);
	});
	Externals.Add(Name, Delegate);
	Story->BindExternalFunctionGeneral(Name, Delegate, /*lookaheadSafe*/ false);
}

int32 FDinkInkStory::ArgToInt(const Ink::FValueType& Value)
{
	if (Value.HasSubtype<int32>())
	{
		return Value.GetSubtype<int32>();
	}
	if (Value.HasSubtype<float>())
	{
		return static_cast<int32>(Value.GetSubtype<float>());
	}
	if (Value.HasSubtype<bool>())
	{
		return Value.GetSubtype<bool>() ? 1 : 0;
	}
	if (Value.HasSubtype<FString>())
	{
		return FCString::Atoi(*Value.GetSubtype<FString>());
	}
	return 0;
}

FString FDinkInkStory::ArgToString(const Ink::FValueType& Value)
{
	if (Value.HasSubtype<FString>())
	{
		return DinkNarrative::ToDisplayText(Value.GetSubtype<FString>());
	}
	return FString::FromInt(ArgToInt(Value));
}
