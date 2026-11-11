#pragma once
// Probe-only oracle: persistence is not a snapshot of the restarted script VM.
#include "DinkSaveGame.h"
#include "DinkNarrativeTypes.h"
#include "Hardness/DinkHardnessSlots.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

namespace DinkProbeLoadOracle
{
inline TSharedPtr<FJsonObject> Narrative(const UDinkSaveGame& Save)
{
    const FString* Text=Save.SubsystemState.Find(TEXT("narrative"));
    TSharedPtr<FJsonObject> Result;
    if(Text) FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Text),Result);
    return Result;
}
inline bool OriginalMode(const FJsonObject& NarrativeState,bool Required)
{
    bool Selected=false;
    const TSharedPtr<FJsonObject>* Gameplay=nullptr;
    if(NarrativeState.TryGetObjectField(TEXT("gameplay"),Gameplay)&&Gameplay&&Gameplay->IsValid())
        (*Gameplay)->TryGetBoolField(TEXT("originalHardnessVisitV1"),Selected);
    return Required||Selected;
}
inline bool LegacyLinesEqual(const FString& Expected,const FString& Actual)
{
    TArray<FString> A,B;Expected.ParseIntoArrayLines(A,false);Actual.ParseIntoArrayLines(B,false);
    return A==B;
}

inline TArray<FString> PersistentDifferences(const UDinkSaveGame& Saved,const UDinkSaveGame& Actual)
{
    TArray<FString> Errors;
    // Exact reflected values: includes all stat fields, slots/armed slots,
    // override timestamps/variants and exit times. No text rounding or ignore list.
    for(const TCHAR* Name:{TEXT("Facts"),TEXT("PlayerStats"),TEXT("Inventory"),TEXT("Overrides"),
        TEXT("ScreenExitTimes"),TEXT("GameTimeMs"),TEXT("CurrentScreen"),TEXT("PlayerTransform")})
    {
        const FProperty* Field=FindFProperty<FProperty>(UDinkSaveGame::StaticClass(),Name);
        if(!Field||!Field->Identical_InContainer(&Saved,&Actual))Errors.Add(FString::Printf(TEXT("persistent %s differs"),Name));
    }
    const auto Before=Narrative(Saved),After=Narrative(Actual);
    if(!Before||!After){Errors.Add(TEXT("missing actual narrative JSON"));return Errors;}
    for(const TCHAR* Name:{TEXT("nowMs"),TEXT("lastScreen")})
    {
        const auto A=Before->TryGetField(Name),B=After->TryGetField(Name);
        if(!A||!B||!FJsonValue::CompareEqual(*A,*B))Errors.Add(FString::Printf(TEXT("persistent narrative.%s differs"),Name));
    }
    const TSharedPtr<FJsonObject>* BeforeGameplay=nullptr;
    const TSharedPtr<FJsonObject>* AfterGameplay=nullptr;
    if(!Before->TryGetObjectField(TEXT("gameplay"),BeforeGameplay)||!BeforeGameplay||!BeforeGameplay->IsValid()||
       !After->TryGetObjectField(TEXT("gameplay"),AfterGameplay)||!AfterGameplay||!AfterGameplay->IsValid())
    {Errors.Add(TEXT("missing original-load gameplay object"));return Errors;}
    for(const TCHAR* Name:{TEXT("originalHardnessVisitV1"),TEXT("hardnessEditorPicturesV1")})
    {
        const auto A=(*BeforeGameplay)->TryGetField(Name);
        const auto B=(*AfterGameplay)->TryGetField(Name);
        if(!A||!B||!FJsonValue::CompareEqual(*A,*B))Errors.Add(FString::Printf(TEXT("persistent gameplay.%s differs"),Name));
    }
    return Errors;
}
struct FBirthExpectation
{
    int32 Type=0,Hard=0,Seq=0,Frame=0;bool Removed=false;FName Script;
};
inline FBirthExpectation BirthExpectation(int32 Type,int32 Hard,int32 Seq,int32 Frame,FName Script,
    int32 Override,int32 SavedSeq,int32 SavedFrame)
{
    const auto Fields=DinkHardness::ProjectEditorFields(Type,Hard,Seq,Frame,Override,SavedSeq,SavedFrame);
    return {Fields.Type,Fields.Hard,Fields.Seq,Fields.Frame,Fields.Removed,Fields.ClearScript?NAME_None:Script};
}
struct FProcedureStart { int32 Id=0,Sprite=0,Index=0;FString Path; };
struct FProcedureCall { int32 Caller=0,Index=0;FName Command;TArray<FString> Args; };
inline TSet<int32> QualifySourceCalls(TSet<int32> Roots,const TArray<FProcedureStart>& Starts,
    const TArray<FProcedureCall>& Calls,int32 SavedNext,int32 DetachedSprite)
{
    for(int32 Pass=0;Pass<Starts.Num();++Pass)
    {
        bool Changed=false;
        for(const auto& Start:Starts)if(Start.Id>=SavedNext&&!Roots.Contains(Start.Id))
        {
            // A native creation command emits start synchronously. Use its last
            // preceding command, not any historical matching script string.
            const FProcedureCall* Creator=nullptr;
            for(const auto& Call:Calls)if(Call.Index<Start.Index&&(!Creator||Call.Index>Creator->Index))Creator=&Call;
            if(!Creator||!Roots.Contains(Creator->Caller))continue;
            int32 Arg=-1;FName Procedure(TEXT("main"));bool SpriteMatches=false;
            if(Creator->Command==TEXT("spawn")){Arg=0;SpriteMatches=Start.Sprite==DetachedSprite;}
            else if(Creator->Command==TEXT("external")&&Creator->Args.Num()>1)
            {
                Arg=0;Procedure=FName(*Creator->Args[1]);
                for(const auto& Caller:Starts)if(Caller.Id==Creator->Caller)SpriteMatches=Start.Sprite==Caller.Sprite;
            }
            else if(Creator->Command==TEXT("sp_script")&&Creator->Args.Num()>1)
            {Arg=1;SpriteMatches=Creator->Args[0].IsNumeric()&&FCString::Atoi(*Creator->Args[0])==Start.Sprite;}
            if(Arg>=0&&Creator->Args.IsValidIndex(Arg)&&SpriteMatches&&
                Start.Path==DinkNarrative::EntryPath(Creator->Args[Arg],Procedure.ToString()))
            {Roots.Add(Start.Id);Changed=true;}
        }
        if(!Changed)break;
    }
    return Roots;
}
inline bool HasExactStart(const TArray<FProcedureStart>& Starts,int32 Id,int32 Sprite,const FString& Path)
{
    return Starts.ContainsByPredicate([&](const auto& Start){return Start.Id==Id&&Start.Sprite==Sprite&&Start.Path==Path;});
}
struct FFreshIdentity
{
    int32 Id=0,Screen=0;
    bool SourceQualified=false;
};
inline bool FreshIdentities(const TSet<int32>& OldAlive,int32 SavedNext,int32 Screen,
    const TArray<FFreshIdentity>& Fresh,FString& Error)
{
    if(SavedNext<1){Error=TEXT("invalid saved next instance ID");return false;}
    TSet<int32> Seen;
    for(const auto& I:Fresh)
    {
        if(I.Id<SavedNext||OldAlive.Contains(I.Id)||Seen.Contains(I.Id)||I.Screen!=Screen||!I.SourceQualified)
        {Error=TEXT("old, duplicate, wrong-screen or unqualified restarted instance");return false;}
        Seen.Add(I.Id);
    }
    return true;
}
}
