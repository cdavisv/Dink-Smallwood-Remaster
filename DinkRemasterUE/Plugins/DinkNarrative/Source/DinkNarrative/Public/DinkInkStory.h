#pragma once

#include "CoreMinimal.h"
#include "DinkNarrativeTypes.h"
#include "Ink/Story.h"
#include "Ink/Value.h"

/** One row group of names.csv (tools/dinkink): how DinkC names map to Ink names. */
struct DINKNARRATIVE_API FDinkStoryNames
{
	/** Fact name (original global without '&', e.g. "s2-nad") -> Ink VAR ("s2_nad"). 63 rows. */
	TMap<FName, FString> GlobalToInk;
	/** Ink VAR -> fact name. */
	TMap<FString, FName> InkToGlobal;
	/** Script name -> knot ("s1-h1-m" -> "d_s1_h1_m"). */
	TMap<FName, FString> ScriptToKnot;
	/** Script name -> its local Ink VARs ("s1_h1_m__whob"). */
	TMap<FName, TArray<FString>> ScriptLocals;
	/** Every entry path ("d_s1_h1_m.on_talk"). */
	TSet<FString> EntryPaths;
	/** Entry paths in names.csv order with their script and procedure. */
	struct FEntry { FString Path; FName Script; FName Procedure; };
	TArray<FEntry> Entries;
	/** Engine pseudo-variables (current_sprite, arg1..9, v_return, ...). */
	TArray<FString> PseudoVariables;

	bool LoadFromCsv(const FString& CsvText, FString* OutError = nullptr);
	bool HasEntry(FName Script, FName Procedure) const;
};

/**
 * Thin wrapper over Inkpot's InkPlusPlus runtime (Ink::FStory) for the converted Dink story:
 * load the compiled JSON, run flows, read and write integer VARs, classify output lines and
 * collect the runtime's errors. No Unreal objects; the story subsystem owns one of these.
 */
class DINKNARRATIVE_API FDinkInkStory
{
public:
	FDinkInkStory();
	~FDinkInkStory();

	/** Loads the compiled story (ink JSON format 21) and the names table. */
	bool Load(const FString& StoryJson, const FString& NamesCsv, FString* OutError = nullptr);

	/** Content/Dink/Data/Story/<File>. */
	static FString GetDataPath(const TCHAR* File);

	bool IsLoaded() const { return Story.IsValid(); }
	Ink::FStory& Ink() const { return *Story; }
	const FDinkStoryNames& Names() const { return NamesTable; }

	/** Ink format version the file declared. */
	int32 GetInkVersion() const { return InkVersion; }

	/** True if Path ("knot" or "knot.stitch") resolves to content exactly. */
	bool HasPath(const FString& Path) const;
	/** True if the knot exists in the story's top level. */
	bool HasKnot(const FString& Knot) const;

	// ---- Variables ----
	bool HasVariable(const FString& Name) const;
	int32 GetInt(const FString& Name, int32 Default = 0) const;
	FString GetString(const FString& Name) const;
	/** Sets an Ink global (int). Returns false if the VAR does not exist. */
	bool SetInt(const FString& Name, int32 Value);

	// ---- State ----
	/** New story state (all flows gone, globals at their declared values); seed for RANDOM. */
	void ResetState(int32 Seed);
	FString SaveStateJson() const;
	bool LoadStateJson(const FString& Json);

	// ---- Flows ----
	void SwitchFlow(const FString& Flow);
	void RemoveFlow(const FString& Flow);
	TArray<FString> AliveFlows() const;

	/** ChoosePathString with a reset call stack (DinkC: starting a procedure abandons the old one). */
	void ChoosePath(const FString& Path);
	bool CanContinue() const;
	/** One line of output, classified. */
	FDinkStoryLine ContinueLine();
	TArray<FDinkStoryChoice> GetChoices() const;
	void Choose(int32 ChoiceIndex);

	/** Errors and warnings the runtime reported since the last call (and clears them). */
	TArray<FString> TakeErrors();

	/** External function: args as the runtime passes them; return an int, a string or nothing. */
	using FExternal = TFunction<TSharedPtr<Ink::FValueType>(const TArray<Ink::FValueType>&)>;
	/** Binds with lookaheadSafe = false (DESIGN.md 5). Replaces an existing binding. */
	void BindExternal(const FString& Name, FExternal Function);

	/** Variable-change observer: (name, new int value). Fires for every global the runtime assigns. */
	TFunction<void(const FString&, int32)> OnIntVariableChanged;

	static int32 ArgToInt(const Ink::FValueType& Value);
	static FString ArgToString(const Ink::FValueType& Value);

private:
    friend class FDinkHardnessRetainedLegacyOwner;
	void HookState();
	void HandleVariableChanged(const FString& Name, TSharedPtr<Ink::FObject> Value);

	TSharedPtr<Ink::FStory> Story;
	FDinkStoryNames NamesTable;
	TArray<FString> PendingErrors;
	TMap<FString, TSharedPtr<FStoryExternalFunction>> Externals;
	int32 InkVersion = 0;
	FDelegateHandle VariableHandle;
	/** The variable state the observer is bound to (rebound after ResetState). */
	TWeakPtr<Ink::FVariableState> HookedState;
};
