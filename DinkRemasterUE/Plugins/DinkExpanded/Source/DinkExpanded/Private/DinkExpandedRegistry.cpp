#include "DinkExpanded.h"

#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	bool ReadRect(const TSharedPtr<FJsonObject>& O, const TCHAR* Field, FDinkPackRect& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (!O.IsValid() || !O->TryGetArrayField(Field, A) || A->Num() != 4)
		{
			return false;
		}
		Out.X0 = static_cast<int32>((*A)[0]->AsNumber());
		Out.Y0 = static_cast<int32>((*A)[1]->AsNumber());
		Out.X1 = static_cast<int32>((*A)[2]->AsNumber());
		Out.Y1 = static_cast<int32>((*A)[3]->AsNumber());
		return true;
	}

	bool ReadRectValue(const TSharedPtr<FJsonValue>& V, FDinkPackRect& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (!V.IsValid() || !V->TryGetArray(A) || A->Num() != 4)
		{
			return false;
		}
		Out.X0 = static_cast<int32>((*A)[0]->AsNumber());
		Out.Y0 = static_cast<int32>((*A)[1]->AsNumber());
		Out.X1 = static_cast<int32>((*A)[2]->AsNumber());
		Out.Y1 = static_cast<int32>((*A)[3]->AsNumber());
		return true;
	}

	bool ReadPoint(const TSharedPtr<FJsonObject>& O, const TCHAR* Field, FVector2D& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (!O.IsValid() || !O->TryGetArrayField(Field, A) || A->Num() != 2)
		{
			return false;
		}
		Out = FVector2D((*A)[0]->AsNumber(), (*A)[1]->AsNumber());
		return true;
	}

	FName NameField(const TSharedPtr<FJsonObject>& O, const TCHAR* Field)
	{
		FString S;
		return O->TryGetStringField(Field, S) && !S.IsEmpty() ? FName(*S.ToLower()) : NAME_None;
	}
}

const FDinkPackSheet* FDinkPack::FindSheet(FName SheetId) const
{
	return Sheets.FindByPredicate([SheetId](const FDinkPackSheet& S) { return S.Id == SheetId; });
}

bool FDinkExpandedRegistry::LoadFromFile(const FString& Path, FString& OutError)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		OutError = FString::Printf(TEXT("cannot read %s (run python3 -m expanded build in tools/expanded)"), *Path);
		return false;
	}
	return LoadFromJson(Text, OutError);
}

bool FDinkExpandedRegistry::LoadFromJson(const FString& Text, FString& OutError)
{
	Packs.Reset();
	TSharedPtr<FJsonObject> Root;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid())
	{
		OutError = TEXT("packs.json does not parse");
		return false;
	}
	FString Schema;
	if (!Root->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-expanded/1"))
	{
		OutError = FString::Printf(TEXT("packs.json schema '%s', expected dink-expanded/1"), *Schema);
		return false;
	}
	const TArray<TSharedPtr<FJsonValue>>* PackValues = nullptr;
	if (!Root->TryGetArrayField(TEXT("packs"), PackValues))
	{
		OutError = TEXT("packs.json has no packs array");
		return false;
	}
	for (const TSharedPtr<FJsonValue>& PV : *PackValues)
	{
		const TSharedPtr<FJsonObject> P = PV->AsObject();
		if (!P.IsValid())
		{
			OutError = TEXT("pack entry is not an object");
			return false;
		}
		FDinkPack& Pack = Packs.AddDefaulted_GetRef();
		Pack.Id = NameField(P, TEXT("id"));
		Pack.Number = P->GetIntegerField(TEXT("number"));
		P->TryGetStringField(TEXT("name"), Pack.Name);
		P->TryGetStringField(TEXT("wave"), Pack.Wave);
		P->TryGetStringField(TEXT("status"), Pack.Status);
		P->TryGetBoolField(TEXT("draft"), Pack.bDraft);
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		if (P->TryGetArrayField(TEXT("sheets"), Values))
		{
			for (const TSharedPtr<FJsonValue>& V : *Values)
			{
				const TSharedPtr<FJsonObject> O = V->AsObject();
				FDinkPackSheet& S = Pack.Sheets.AddDefaulted_GetRef();
				S.Id = NameField(O, TEXT("id"));
				S.Kind = NameField(O, TEXT("kind"));
				FVector2D Dir;
				if (ReadPoint(O, TEXT("direction"), Dir) && !Dir.IsNearlyZero())
				{
					S.Direction = Dir.GetSafeNormal();
				}
				O->TryGetNumberField(TEXT("gap_m"), S.GapM);
			}
		}
		if (P->TryGetArrayField(TEXT("screens"), Values))
		{
			for (const TSharedPtr<FJsonValue>& V : *Values)
			{
				const TSharedPtr<FJsonObject> O = V->AsObject();
				FDinkPackScreen& S = Pack.Screens.AddDefaulted_GetRef();
				S.Screen = O->GetIntegerField(TEXT("screen"));
				FVector2D Grid;
				ReadPoint(O, TEXT("grid"), Grid);
				S.Grid = FIntPoint(static_cast<int32>(Grid.X), static_cast<int32>(Grid.Y));
				S.Sheet = NameField(O, TEXT("sheet"));
				O->TryGetStringField(TEXT("name"), S.Name);
				S.Kind = NameField(O, TEXT("kind"));
				S.Region = NameField(O, TEXT("region"));
				S.BaseScript = NameField(O, TEXT("base_script"));
				O->TryGetNumberField(TEXT("music"), S.MusicRaw);
				O->TryGetBoolField(TEXT("indoor"), S.bIndoor);
				const TArray<TSharedPtr<FJsonValue>>* Solids = nullptr;
				if (O->TryGetArrayField(TEXT("solids"), Solids))
				{
					for (const TSharedPtr<FJsonValue>& R : *Solids)
					{
						FDinkPackRect Rect;
						if (!ReadRectValue(R, Rect))
						{
							OutError = FString::Printf(TEXT("pack %s screen %d: a solid is not [x0, y0, x1, y1]"), *Pack.Id.ToString(), S.Screen);
							return false;
						}
						S.Solids.Add(Rect);
					}
				}
			}
		}
		if (P->TryGetArrayField(TEXT("placements"), Values))
		{
			for (const TSharedPtr<FJsonValue>& V : *Values)
			{
				const TSharedPtr<FJsonObject> O = V->AsObject();
				FDinkPackPlacement& Pl = Pack.Placements.AddDefaulted_GetRef();
				Pl.Screen = O->GetIntegerField(TEXT("screen"));
				Pl.Index = O->GetIntegerField(TEXT("index"));
				Pl.X = O->GetIntegerField(TEXT("x"));
				Pl.Y = O->GetIntegerField(TEXT("y"));
				Pl.Seq = O->GetIntegerField(TEXT("seq"));
				Pl.Frame = O->GetIntegerField(TEXT("frame"));
				Pl.Brain = O->GetIntegerField(TEXT("brain"));
				O->TryGetNumberField(TEXT("size"), Pl.Size);
				Pl.Script = NameField(O, TEXT("script"));
				Pl.Kind = NameField(O, TEXT("kind"));
				O->TryGetStringField(TEXT("name"), Pl.Name);
				O->TryGetBoolField(TEXT("hard"), Pl.bHard);
			}
		}
		if (P->TryGetArrayField(TEXT("joins"), Values))
		{
			for (const TSharedPtr<FJsonValue>& V : *Values)
			{
				const TSharedPtr<FJsonObject> O = V->AsObject();
				FDinkPackJoin& J = Pack.Joins.AddDefaulted_GetRef();
				O->TryGetStringField(TEXT("id"), J.Id);
				const TSharedPtr<FJsonObject>* From = nullptr;
				const TSharedPtr<FJsonObject>* To = nullptr;
				const TSharedPtr<FJsonObject>* Back = nullptr;
				const TSharedPtr<FJsonObject>* Return = nullptr;
				if (!O->TryGetObjectField(TEXT("from"), From) || !O->TryGetObjectField(TEXT("to"), To) ||
					!O->TryGetObjectField(TEXT("back"), Back) || !O->TryGetObjectField(TEXT("return"), Return) ||
					!ReadRect(*From, TEXT("rect"), J.FromRect) || !ReadPoint(*To, TEXT("point"), J.ToPoint) ||
					!ReadRect(*Back, TEXT("rect"), J.BackRect) || !ReadPoint(*Return, TEXT("point"), J.ReturnPoint))
				{
					OutError = FString::Printf(TEXT("pack %s join '%s': from/to/back/return incomplete"), *Pack.Id.ToString(), *J.Id);
					return false;
				}
				J.FromScreen = (*From)->GetIntegerField(TEXT("screen"));
				J.ToScreen = (*To)->GetIntegerField(TEXT("screen"));
				J.BackScreen = (*Back)->GetIntegerField(TEXT("screen"));
				J.ReturnScreen = (*Return)->GetIntegerField(TEXT("screen"));
				const TSharedPtr<FJsonObject>* Requires = nullptr;
				if (O->TryGetObjectField(TEXT("requires"), Requires) && Requires->IsValid())
				{
					J.RequiresFact = NameField(*Requires, TEXT("fact"));
					(*Requires)->TryGetNumberField(TEXT("at_least"), J.RequiresAtLeast);
				}
			}
		}
	}
	const TArray<FString> Problems = Validate();
	if (Problems.Num() > 0)
	{
		OutError = FString::Join(Problems, TEXT("; "));
		Packs.Reset();
		return false;
	}
	return true;
}

void FDinkExpandedRegistry::FilterPacks(const TArray<FName>& Keep)
{
	if (Keep.Num() > 0)
	{
		Packs.RemoveAll([&Keep](const FDinkPack& P) { return !Keep.Contains(P.Id); });
	}
}

TArray<FString> FDinkExpandedRegistry::Validate() const
{
	TArray<FString> Out;
	TSet<int32> Numbers;
	TSet<int32> Screens;
	TSet<FName> Ids;
	for (const FDinkPack& P : Packs)
	{
		const FString Tag = P.Id.ToString();
		if (P.Id.IsNone() || Ids.Contains(P.Id))
		{
			Out.Add(FString::Printf(TEXT("pack id '%s' empty or repeated"), *Tag));
		}
		Ids.Add(P.Id);
		if (P.Number < 1 || P.Number > 9 || Numbers.Contains(P.Number))
		{
			Out.Add(FString::Printf(TEXT("pack %s: number %d must be 1-9 and unique (it names the namespace x<n>)"), *Tag, P.Number));
		}
		Numbers.Add(P.Number);
		TSet<FString> Cells;
		for (const FDinkPackScreen& S : P.Screens)
		{
			// The numbers no 1997 map record uses (tools/expanded checks map.dat; the runtime keeps the range rule).
			if (S.Screen < 1 || S.Screen > 768 || Screens.Contains(S.Screen))
			{
				Out.Add(FString::Printf(TEXT("pack %s: screen %d outside 1..768 or owned twice"), *Tag, S.Screen));
			}
			Screens.Add(S.Screen);
			if (!P.FindSheet(S.Sheet))
			{
				Out.Add(FString::Printf(TEXT("pack %s: screen %d names no sheet of the pack ('%s')"), *Tag, S.Screen, *S.Sheet.ToString()));
			}
			const FString Key = FString::Printf(TEXT("%s:%d:%d"), *S.Sheet.ToString(), S.Grid.X, S.Grid.Y);
			if (S.Grid.X < 0 || S.Grid.Y < 0 || Cells.Contains(Key))
			{
				Out.Add(FString::Printf(TEXT("pack %s: screen %d grid cell (%d, %d) negative or taken"), *Tag, S.Screen, S.Grid.X, S.Grid.Y));
			}
			Cells.Add(Key);
			if (!S.BaseScript.IsNone() && !S.BaseScript.ToString().StartsWith(P.ScriptPrefix()))
			{
				Out.Add(FString::Printf(TEXT("pack %s: base script %s is outside the namespace %s"), *Tag, *S.BaseScript.ToString(), *P.ScriptPrefix()));
			}
			for (const FDinkPackRect& R : S.Solids)
			{
				if (!R.IsValid())
				{
					Out.Add(FString::Printf(TEXT("pack %s: screen %d has a solid outside 600 x 400"), *Tag, S.Screen));
				}
			}
		}
		auto OwnScreen = [&P](int32 N) { return P.Screens.ContainsByPredicate([N](const FDinkPackScreen& S) { return S.Screen == N; }); };
		for (const FDinkPackPlacement& Pl : P.Placements)
		{
			if (!OwnScreen(Pl.Screen))
			{
				Out.Add(FString::Printf(TEXT("pack %s: placement on screen %d, which the pack does not own"), *Tag, Pl.Screen));
			}
			if (Pl.Index < 1 || Pl.Index > 99)
			{
				Out.Add(FString::Printf(TEXT("pack %s: placement index %d outside 1..99"), *Tag, Pl.Index));
			}
		}
		for (const FDinkPackJoin& J : P.Joins)
		{
			if (OwnScreen(J.FromScreen) || OwnScreen(J.ReturnScreen) || !OwnScreen(J.ToScreen) || !OwnScreen(J.BackScreen))
			{
				Out.Add(FString::Printf(TEXT("pack %s join %s: from/return must be 1997 screens, to/back the pack's"), *Tag, *J.Id));
			}
			if (!J.FromRect.IsValid() || !J.BackRect.IsValid())
			{
				Out.Add(FString::Printf(TEXT("pack %s join %s: a trigger rectangle is outside 600 x 400"), *Tag, *J.Id));
			}
			if (!J.RequiresFact.IsNone() && !J.RequiresFact.ToString().StartsWith(P.GlobalPrefix()))
			{
				Out.Add(FString::Printf(TEXT("pack %s join %s: condition fact %s is outside the namespace %s"), *Tag, *J.Id, *J.RequiresFact.ToString(), *P.GlobalPrefix()));
			}
		}
	}
	return Out;
}

const FDinkPack* FDinkExpandedRegistry::FindPack(FName Id) const
{
	return Packs.FindByPredicate([Id](const FDinkPack& P) { return P.Id == Id; });
}

const FDinkPackScreen* FDinkExpandedRegistry::FindScreen(int32 Screen, const FDinkPack** OutPack) const
{
	for (const FDinkPack& P : Packs)
	{
		for (const FDinkPackScreen& S : P.Screens)
		{
			if (S.Screen == Screen)
			{
				if (OutPack)
				{
					*OutPack = &P;
				}
				return &S;
			}
		}
	}
	return nullptr;
}

bool FDinkExpandedRegistry::IsPackScript(FName Script) const
{
	const FString S = Script.ToString();
	return Packs.ContainsByPredicate([&S](const FDinkPack& P) { return S.StartsWith(P.ScriptPrefix()); });
}

int32 FDinkExpandedRegistry::NumScreens() const
{
	int32 N = 0;
	for (const FDinkPack& P : Packs)
	{
		N += P.Screens.Num();
	}
	return N;
}
