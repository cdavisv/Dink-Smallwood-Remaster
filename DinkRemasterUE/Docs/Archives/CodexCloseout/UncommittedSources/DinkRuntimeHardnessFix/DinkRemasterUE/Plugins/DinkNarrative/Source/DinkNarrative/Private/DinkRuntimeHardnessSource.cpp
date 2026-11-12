#include "Hardness/DinkRuntimeHardnessSource.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
bool Integer(const TSharedPtr<FJsonValue>& V, int32& Out)
{
    if (!V.IsValid() || V->Type != EJson::Number) return false;
    const double N = V->AsNumber();
    if (!FMath::IsFinite(N) || N < MIN_int32 || N > MAX_int32 || FMath::FloorToDouble(N) != N) return false;
    Out = static_cast<int32>(N);
    return true;
}
bool Field(const TSharedPtr<FJsonObject>& O, const TCHAR* Name, int32& Out)
{
    return O.IsValid() && Integer(O->TryGetField(Name), Out);
}
}

bool FDinkRuntimeHardnessSource::Load(const FString& File, int32 ExpectedVision,
                                     FDinkRuntimeHardnessSource& Out, FString& Error)
{
    auto Fail = [&Error](const TCHAR* Why) { Error = Why; return false; };
    FString Text;
    TSharedPtr<FJsonObject> Object;
    if (!FFileHelper::LoadFileToString(Text, *File) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Object) || !Object.IsValid())
        return Fail(TEXT("runtime hardness sidecar missing or invalid; legacy world requires migration"));
    FString Schema;
    int32 Width = 0, Height = 0, Vision = 0;
    if (!Object->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dinkex.runtime-hardness/1") ||
        !Field(Object, TEXT("width"), Width) || Width != 600 ||
        !Field(Object, TEXT("height"), Height) || Height != 400 ||
        !Field(Object, TEXT("vision"), Vision) || Vision != ExpectedVision)
        return Fail(TEXT("runtime hardness schema/dimensions/vision mismatch"));
    const TArray<TSharedPtr<FJsonValue>>* Skipped = nullptr;
    if (!Object->TryGetArrayField(TEXT("skipped_tile_indices"), Skipped) || Skipped->Num() != 0)
        return Fail(TEXT("invalid tile cells require explicit previous-screen state"));
    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    if (!Object->TryGetArrayField(TEXT("tile_base_rle"), Rows) || Rows->Num() != 400)
        return Fail(TEXT("explicit complete tile base required"));
    FDinkRuntimeHardnessSource Candidate;
    Candidate.TileBase.reserve(600 * 400);
    for (const auto& Row : *Rows)
    {
        if (!Row.IsValid() || Row->Type != EJson::Array) return Fail(TEXT("invalid tile row"));
        int32 WidthSoFar = 0;
        for (const auto& Run : Row->AsArray())
        {
            if (!Run.IsValid() || Run->Type != EJson::Array || Run->AsArray().Num() != 2)
                return Fail(TEXT("invalid tile run"));
            int32 Count = 0, Code = 0;
            if (!Integer(Run->AsArray()[0], Count) || Count < 1 || Count > 600 ||
                !Integer(Run->AsArray()[1], Code) || Code < 0 || Code > 3 || WidthSoFar + Count > 600)
                return Fail(TEXT("tile run length/code invalid"));
            Candidate.TileBase.insert(Candidate.TileBase.end(), Count, static_cast<std::uint8_t>(Code));
            WidthSoFar += Count;
        }
        if (WidthSoFar != 600) return Fail(TEXT("incomplete tile row"));
    }
    const TArray<TSharedPtr<FJsonValue>>* Stamps = nullptr;
    if (!Object->TryGetArrayField(TEXT("ordered_stamps"), Stamps)) return Fail(TEXT("ordered stamps required"));
    TSet<int32> Owners;
    for (const auto& Value : *Stamps)
    {
        if (!Value.IsValid() || Value->Type != EJson::Object) return Fail(TEXT("invalid stamp"));
        const auto Stamp = Value->AsObject();
        int32 Owner = 0, Code = 0; bool Warp = false;
        const TArray<TSharedPtr<FJsonValue>>* Box = nullptr;
        if (!Field(Stamp, TEXT("owner"), Owner) || Owner < 1 || Owner > 99 || Owners.Contains(Owner) ||
            !Field(Stamp, TEXT("code"), Code) || Code != 100 + Owner ||
            !Stamp->TryGetBoolField(TEXT("warp"), Warp) ||
            !Stamp->TryGetArrayField(TEXT("rect"), Box) || Box->Num() != 4)
            return Fail(TEXT("stamp owner/code/warp/rect invalid"));
        int32 L = 0, T = 0, R = 0, B = 0;
        if (!Integer((*Box)[0], L) || !Integer((*Box)[1], T) || !Integer((*Box)[2], R) || !Integer((*Box)[3], B) ||
            L < 0 || L >= R || R > 600 || T < 0 || T >= B || B > 400)
            return Fail(TEXT("stamp bounds invalid"));
        Owners.Add(Owner);
        Candidate.InitialStamps.push_back({{L, T, R, B}, static_cast<std::uint8_t>(Code)});
    }
    Out = MoveTemp(Candidate); // only publish validated source; preserve Out on failure
    Error.Reset();
    return true;
}
