#include "DinkCreatureClass.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

namespace
{
	FVector ClassVector(const FJsonObject& Row, const TCHAR* Key, const FVector& Default)
	{
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		return Row.TryGetArrayField(Key, Values) && Values->Num() == 3
			? FVector((*Values)[0]->AsNumber(), (*Values)[1]->AsNumber(), (*Values)[2]->AsNumber()) : Default;
	}

	double ClassNumber(const FJsonObject& Row, const TCHAR* Key, double Default)
	{
		double Number = 0.0;
		return Row.TryGetNumberField(Key, Number) ? Number : Default;
	}

	bool ClassSequences(const FJsonObject& Row, TArray<int32>& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		if (!Row.TryGetArrayField(TEXT("sequences"), Values)) return false;
		for (const TSharedPtr<FJsonValue>& Value : *Values)
		{
			double Number = 0.0;
			if (!Value.IsValid() || !Value->TryGetNumber(Number) || Number < 1.0) return false;
			Out.AddUnique(int32(Number));
		}
		return Out.Num() > 0;
	}

	bool ClassLocomotion(const FJsonObject& Row, FDinkCreatureLocomotion& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* Gaits = nullptr;
		if (!Row.TryGetStringField(TEXT("idle"), Out.Idle) || !Out.Idle.StartsWith(TEXT("/Game/")) || !Row.TryGetArrayField(TEXT("gaits"), Gaits)) return false;
		float Last = 0.f;
		for (const TSharedPtr<FJsonValue>& Value : *Gaits)
		{
			const TSharedPtr<FJsonObject> GaitRow = Value.IsValid() ? Value->AsObject() : nullptr;
			FDinkCreatureGait Gait;
			if (!GaitRow || !GaitRow->TryGetStringField(TEXT("clip"), Gait.Clip) || !Gait.Clip.StartsWith(TEXT("/Game/"))) return false;
			Gait.SpeedCmS = float(ClassNumber(*GaitRow, TEXT("speed_cm_s"), 0.0));
			Gait.Cycles = float(ClassNumber(*GaitRow, TEXT("cycles"), 1.0));
			if (Gait.SpeedCmS <= Last || Gait.Cycles <= 0.f) return false; // slowest first, strictly rising
			Last = Gait.SpeedCmS;
			Out.Gaits.Add(MoveTemp(Gait));
		}
		return Out.Gaits.Num() > 0;
	}

	/** The engine's other facing when a death sequence does not exist (dink.cpp:12392-12404). */
	int32 MirrorDir(int32 Dir)
	{
		switch (Dir)
		{
		case 1: return 9;
		case 3: return 7;
		case 7: return 3;
		case 9: return 1;
		case 4: return 6;
		case 6: return 4;
		case 8: return 2;
		case 2: return 8;
		default: return Dir;
		}
	}
}

const FDinkCreatureCorpse* FDinkCreatureClassBinding::CorpseFor(int32 BaseDeath, int32 Dir) const
{
	if (BaseDeath < 0) return nullptr; // base_die -1: base_walk + 5 or the generic puff, never one of these (dink.cpp:12371-12389)
	if (Dir < 1 || Dir > 9) Dir = 3;   // dink.cpp:12361-12365
	for (const int32 Candidate : { BaseDeath + Dir, BaseDeath + MirrorDir(Dir) })
	{
		for (const FDinkCreatureCorpse& Corpse : Corpses)
		{
			if (Corpse.Sequences.Contains(Candidate)) return &Corpse;
		}
	}
	return nullptr;
}

namespace
{
	/** One row of `classes`; false with the first reason in OutProblem. */
	bool ParseClassRow(const TSharedPtr<FJsonObject>& Row, const TArray<FDinkCreatureClassBinding>& Earlier, FDinkCreatureClassBinding& B, FString& OutProblem)
	{
		auto Problem = [&OutProblem](const FString& Text) { if (OutProblem.IsEmpty()) OutProblem = Text; };
		if (!Row) { Problem(TEXT("classes: a row is not an object")); return false; }
		FString ClassId;
		if (!Row->TryGetStringField(TEXT("class"), ClassId) || ClassId.IsEmpty()) { Problem(TEXT("classes: row without class")); return false; }
		B.ClassId = FName(*ClassId);
		if (Earlier.ContainsByPredicate([&B](const FDinkCreatureClassBinding& Other) { return Other.ClassId == B.ClassId; }))
		{
			Problem(FString::Printf(TEXT("classes: %s bound twice, second row skipped"), *ClassId));
			return false;
		}
		if (!Row->TryGetStringField(TEXT("mesh"), B.Mesh) || !B.Mesh.StartsWith(TEXT("/Game/")))
		{
			Problem(FString::Printf(TEXT("classes: %s has no /Game/ mesh"), *ClassId));
			return false;
		}
		const TSharedPtr<FJsonObject>* Locomotion = nullptr;
		bool bValid = true;
		if (Row->TryGetObjectField(TEXT("locomotion"), Locomotion) && Locomotion && !ClassLocomotion(**Locomotion, B.Locomotion))
		{
			Problem(FString::Printf(TEXT("classes: %s locomotion needs a /Game/ idle and gaits with rising speed_cm_s"), *ClassId));
			bValid = false;
		}
		Row->TryGetStringField(TEXT("note"), B.Note);
		B.OffsetCm = ClassVector(*Row, TEXT("offset_cm"), FVector::ZeroVector);
		B.RotationDeg = ClassVector(*Row, TEXT("rotation_deg"), FVector::ZeroVector);
		B.Scale = ClassNumber(*Row, TEXT("scale"), 1.0);
		B.StationarySpeedCmS = float(ClassNumber(*Row, TEXT("stationary_speed_cm_s"), 5.0));
		B.BlendTimeS = float(ClassNumber(*Row, TEXT("blend_time_s"), 0.12));
		B.SmoothTimeS = float(ClassNumber(*Row, TEXT("smooth_time_s"), 0.1));
		B.TurnRateDegS = float(ClassNumber(*Row, TEXT("turn_rate_deg_s"), 540.0));
		B.CullDistanceCm = float(ClassNumber(*Row, TEXT("cull_distance_cm"), 15000.0));
		if (B.Scale <= 0.0)
		{
			Problem(FString::Printf(TEXT("classes: %s scale is not positive"), *ClassId));
			bValid = false;
		}

		const TSharedPtr<FJsonObject>* Roles = nullptr;
		bool bLocomotion = false;
		if (Row->TryGetObjectField(TEXT("roles"), Roles) && Roles)
		{
			TArray<FString> Names;
			for (const auto& Pair : (*Roles)->Values) Names.Add(FString(*Pair.Key));
			Names.Sort(); // JSON object order is not kept by the engine's reader: a stable order for both runtimes
			for (const FString& Name : Names)
			{
				const TSharedPtr<FJsonObject>* RoleRow = nullptr;
				FDinkCreatureRole Role;
				Role.Name = FName(*Name);
				if (!(*Roles)->TryGetObjectField(Name, RoleRow) || !RoleRow || !ClassSequences(**RoleRow, Role.Sequences))
				{
					Problem(FString::Printf(TEXT("classes: %s role %s has no sequences"), *ClassId, *Name));
					bValid = false;
					continue;
				}
				const TSharedPtr<FJsonObject>* Own = nullptr;
				if ((*RoleRow)->TryGetObjectField(TEXT("locomotion"), Own) && Own)
				{
					Role.bLocomotion = ClassLocomotion(**Own, Role.Locomotion);
					if (!Role.bLocomotion)
					{
						Problem(FString::Printf(TEXT("classes: %s role %s locomotion needs a /Game/ idle and gaits with rising speed_cm_s"), *ClassId, *Name));
						bValid = false;
						continue;
					}
				}
				else
				{
					(*RoleRow)->TryGetBoolField(TEXT("locomotion"), Role.bLocomotion);
				}
				(*RoleRow)->TryGetStringField(TEXT("clip"), Role.Clip);
				(*RoleRow)->TryGetBoolField(TEXT("loop"), Role.bLoop);
				(*RoleRow)->TryGetStringField(TEXT("mesh"), Role.Mesh);
				if (!Role.bLocomotion && !Role.Clip.StartsWith(TEXT("/Game/")))
				{
					Problem(FString::Printf(TEXT("classes: %s role %s is neither locomotion nor a /Game/ clip"), *ClassId, *Name));
					bValid = false;
					continue;
				}
				if (Role.bLocomotion && !Role.Locomotion.IsSet() && !B.Locomotion.IsSet())
				{
					Problem(FString::Printf(TEXT("classes: %s role %s is locomotion but the row has no locomotion set"), *ClassId, *Name));
					bValid = false;
					continue;
				}
				for (const int32 Sequence : Role.Sequences)
				{
					if (B.RoleBySequence.Contains(Sequence))
					{
						Problem(FString::Printf(TEXT("classes: %s sequence %d is in two roles"), *ClassId, Sequence));
						bValid = false;
					}
					else
					{
						B.RoleBySequence.Add(Sequence, B.Roles.Num());
					}
				}
				bLocomotion |= Role.bLocomotion;
				B.Roles.Add(MoveTemp(Role));
			}
		}
		if (!bLocomotion)
		{
			Problem(FString::Printf(TEXT("classes: %s has no locomotion role"), *ClassId));
			bValid = false;
		}
		const TArray<TSharedPtr<FJsonValue>>* Corpses = nullptr;
		if (Row->TryGetArrayField(TEXT("corpses"), Corpses))
		{
			for (const TSharedPtr<FJsonValue>& CorpseValue : *Corpses)
			{
				const TSharedPtr<FJsonObject> CorpseRow = CorpseValue.IsValid() ? CorpseValue->AsObject() : nullptr;
				FDinkCreatureCorpse Corpse;
				if (!CorpseRow || !ClassSequences(*CorpseRow, Corpse.Sequences) || !CorpseRow->TryGetStringField(TEXT("mesh"), Corpse.Mesh) ||
					!Corpse.Mesh.StartsWith(TEXT("/Game/")))
				{
					Problem(FString::Printf(TEXT("classes: %s has a corpse without sequences or a /Game/ mesh"), *ClassId));
					bValid = false;
					continue;
				}
				Corpse.OffsetCm = ClassVector(*CorpseRow, TEXT("offset_cm"), FVector::ZeroVector);
				Corpse.YawOffset = ClassNumber(*CorpseRow, TEXT("yaw_offset"), 0.0);
				Corpse.Scale = ClassNumber(*CorpseRow, TEXT("scale"), 1.0);
				const TSharedPtr<FJsonObject>* Decal = nullptr;
				if (CorpseRow->TryGetObjectField(TEXT("decal"), Decal) && Decal)
				{
					const TArray<TSharedPtr<FJsonValue>>* Size = nullptr;
					if (!(*Decal)->TryGetStringField(TEXT("material"), Corpse.DecalMaterial) || !Corpse.DecalMaterial.StartsWith(TEXT("/Game/")) ||
						!(*Decal)->TryGetArrayField(TEXT("size_cm"), Size) || Size->Num() != 2 || (*Size)[0]->AsNumber() <= 0.0 || (*Size)[1]->AsNumber() <= 0.0)
					{
						Problem(FString::Printf(TEXT("classes: %s has a corpse decal without a /Game/ material or a positive size_cm pair"), *ClassId));
						bValid = false;
						continue;
					}
					Corpse.DecalSizeCm = FVector2D((*Size)[0]->AsNumber(), (*Size)[1]->AsNumber());
					Corpse.DecalDepthCm = FMath::Max(1.0, ClassNumber(**Decal, TEXT("depth_cm"), 45.0));
				}
				B.Corpses.Add(MoveTemp(Corpse));
			}
		}
		const TSharedPtr<FJsonObject>* Materials = nullptr;
		if (Row->TryGetObjectField(TEXT("materials"), Materials) && Materials)
		{
			for (const auto& Pair : (*Materials)->Values)
			{
				const FString Slot(*Pair.Key);
				FString Path;
				if (Pair.Value.IsValid() && Pair.Value->TryGetString(Path) && Path.StartsWith(TEXT("/Game/"))) B.Materials.Add(FName(*Slot), Path);
				else { Problem(FString::Printf(TEXT("classes: %s material %s is not a /Game/ path"), *ClassId, *Slot)); bValid = false; }
			}
		}
		return bValid;
	}
}

int32 DinkCreatureClass::ParseBindings(const FJsonObject& Manifest, TArray<FDinkCreatureClassBinding>& Out, TArray<FString>* Problems)
{
	const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
	if (!Manifest.TryGetArrayField(TEXT("classes"), Rows)) return 0;
	int32 Kept = 0;
	for (const TSharedPtr<FJsonValue>& Value : *Rows)
	{
		FDinkCreatureClassBinding B;
		FString Problem;
		if (!ParseClassRow(Value.IsValid() ? Value->AsObject() : nullptr, Out, B, Problem))
		{
			// one line per refused row: its first reason
			if (Problems) Problems->Add(Problem.IsEmpty() ? FString(TEXT("classes: a row is invalid")) : Problem);
			continue;
		}
		Out.Add(MoveTemp(B));
		++Kept;
	}
	return Kept;
}

EDinkCreatureClassDecision DinkCreatureClass::Decide(const TArray<FDinkCreatureClassBinding>& Bindings, FName ClassId, const FString& Origin,
	const TSet<FString>& PrecedenceOrigins, bool bHasPicture, const FDinkCreatureClassBinding*& OutBinding)
{
	OutBinding = nullptr;
	if (ClassId.IsNone()) return EDinkCreatureClassDecision::NoRow;
	const FDinkCreatureClassBinding* Found = Bindings.FindByPredicate([ClassId](const FDinkCreatureClassBinding& B) { return B.ClassId == ClassId; });
	if (!Found) return EDinkCreatureClassDecision::NoRow;
	if (PrecedenceOrigins.Contains(Origin)) return EDinkCreatureClassDecision::OriginPrecedence;
	if (!bHasPicture) return EDinkCreatureClassDecision::NoPicture;
	OutBinding = Found;
	return EDinkCreatureClassDecision::Bound;
}

const FDinkCreatureClassBinding* DinkCreatureClass::FindBySprite(const TArray<FDinkCreatureClassBinding>& Bindings, const FSpriteView& Sprite)
{
	// The picture first (what the card would show), then the walk base's facings: a script may create the sprite with
	// any picture and give it the creature's base_walk a line later.
	for (const int32 Sequence : { Sprite.Seq, Sprite.PSeq })
	{
		if (Sequence <= 0) continue;
		for (const FDinkCreatureClassBinding& B : Bindings)
		{
			if (B.RoleBySequence.Contains(Sequence)) return &B;
		}
	}
	if (Sprite.BaseWalk > 0)
	{
		for (const FDinkCreatureClassBinding& B : Bindings)
		{
			for (int32 Dir = 1; Dir <= 9; ++Dir)
			{
				const FDinkCreatureRole* Role = Dir == 5 ? nullptr : B.RoleFor(Sprite.BaseWalk + Dir);
				if (Role && Role->bLocomotion) return &B;
			}
		}
	}
	return nullptr;
}

const FDinkCreatureRole* DinkCreatureClass::RoleForSprite(const FDinkCreatureClassBinding& Binding, const FSpriteView& Sprite)
{
	if (const FDinkCreatureRole* Role = Sprite.Seq > 0 ? Binding.RoleFor(Sprite.Seq) : nullptr) return Role;
	if (const FDinkCreatureRole* Role = Sprite.PSeq > 0 ? Binding.RoleFor(Sprite.PSeq) : nullptr) return Role;
	// A picture the row does not know (a script changed it): the creature keeps standing in its first locomotion role.
	return Binding.Roles.FindByPredicate([](const FDinkCreatureRole& Role) { return Role.bLocomotion; });
}

int32 DinkCreatureClass::KillDir(int32 Brain, int32 Dir)
{
	if (Brain != 9 && Brain != 16) return Dir;
	if (Dir == 0) Dir = 3;
	switch (Dir)
	{
	case 8: return 7;
	case 4: return 1;
	case 2: return 3;
	case 6: return 9;
	default: return Dir;
	}
}

int32 DinkCreatureClass::DirOfSequence(int32 Sequence)
{
	const int32 Dir = Sequence > 0 ? Sequence % 10 : 0;
	return Dir == 5 ? 0 : Dir;
}

double DinkCreatureClass::DirYawDegrees(int32 Dir)
{
	switch (Dir)
	{
	case 6: return 0.0;
	case 3: return 45.0;
	case 2: return 90.0;
	case 1: return 135.0;
	case 4: return 180.0;
	case 7: return -135.0;
	case 8: return -90.0;
	case 9: return -45.0;
	default: return 90.0;
	}
}

void DinkCreatureClass::SolveGaits(float Speed, float Stationary, TConstArrayView<float> GaitSpeeds, TConstArrayView<float> GaitStrides,
	float& OutIdle, TArray<float, TInlineAllocator<4>>& OutWeights, float& OutCyclesPerSecond)
{
	const int32 Num = FMath::Min(GaitSpeeds.Num(), GaitStrides.Num());
	OutWeights.Init(0.f, Num);
	OutIdle = 1.f;
	OutCyclesPerSecond = 0.f;
	if (Num == 0 || Speed <= Stationary) return;
	float Stride = GaitStrides[Num - 1];
	if (Speed <= GaitSpeeds[0])
	{
		// Slower than the slowest gait: that gait fades into standing and its steps shorten with it, so the cadence
		// falls more slowly than the speed (a quarter-speed creature takes half-length steps at half the pace).
		const float Share = Speed / GaitSpeeds[0];
		OutWeights[0] = Share;
		OutIdle = 1.f - Share;
		Stride = GaitStrides[0] * FMath::Sqrt(Share);
	}
	else if (Speed >= GaitSpeeds[Num - 1])
	{
		OutWeights[Num - 1] = 1.f;
		OutIdle = 0.f;
	}
	else
	{
		OutIdle = 0.f;
		for (int32 Index = 0; Index + 1 < Num; ++Index)
		{
			if (Speed > GaitSpeeds[Index + 1]) continue;
			const float T = (Speed - GaitSpeeds[Index]) / (GaitSpeeds[Index + 1] - GaitSpeeds[Index]);
			OutWeights[Index] = 1.f - T;
			OutWeights[Index + 1] = T;
			Stride = FMath::Lerp(GaitStrides[Index], GaitStrides[Index + 1], T);
			break;
		}
	}
	OutCyclesPerSecond = Stride > KINDA_SMALL_NUMBER ? Speed / Stride : 0.f;
}
