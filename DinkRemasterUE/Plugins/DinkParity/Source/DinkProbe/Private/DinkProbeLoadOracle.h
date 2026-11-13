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

// Failure evidence only. Never normalizes the stored transforms or changes
// the existing FProperty::Identical predicate.
inline void AppendTransformDiagnostics(const FTransform& Saved,const FTransform& Actual,TArray<FString>& Errors)
{
    const FVector ST=Saved.GetTranslation(),AT=Actual.GetTranslation();
    const FQuat SQ=Saved.GetRotation(),AQ=Actual.GetRotation();
    const FVector SS=Saved.GetScale3D(),AS=Actual.GetScale3D();
    const double A[]{ST.X,ST.Y,ST.Z,SQ.X,SQ.Y,SQ.Z,SQ.W,SS.X,SS.Y,SS.Z};
    const double B[]{AT.X,AT.Y,AT.Z,AQ.X,AQ.Y,AQ.Z,AQ.W,AS.X,AS.Y,AS.Z};
    const TCHAR* Names[]{TEXT("translation.x"),TEXT("translation.y"),TEXT("translation.z"),
        TEXT("quaternion.x"),TEXT("quaternion.y"),TEXT("quaternion.z"),TEXT("quaternion.w"),
        TEXT("scale.x"),TEXT("scale.y"),TEXT("scale.z")};
    for(int32 Index=0;Index<10;++Index)
    {
        uint64 SavedBits=0,ActualBits=0;
        static_assert(sizeof(double)==sizeof(uint64));
        FMemory::Memcpy(&SavedBits,&A[Index],sizeof(double));
        FMemory::Memcpy(&ActualBits,&B[Index],sizeof(double));
        Errors.Add(FString::Printf(TEXT("PlayerTransform %s saved=%.17g bits=0x%016llx actual=%.17g bits=0x%016llx delta=%.17g"),
            Names[Index],A[Index],static_cast<unsigned long long>(SavedBits),B[Index],static_cast<unsigned long long>(ActualBits),B[Index]-A[Index]));
    }
    const bool AngularValid=!SQ.ContainsNaN()&&!AQ.ContainsNaN()&&FMath::IsFinite(SQ.SizeSquared())&&
        FMath::IsFinite(AQ.SizeSquared())&&SQ.SizeSquared()>0.0&&AQ.SizeSquared()>0.0;
    Errors.Add(FString::Printf(TEXT("PlayerTransform metrics savedIsNormalized=%d actualIsNormalized=%d savedQuatNorm2=%.17g actualQuatNorm2=%.17g translationDeltaCm=%.17g scaleDelta=%.17g angularValid=%d normalizedAngularDeltaRadians=%.17g"),
        int32(SQ.IsNormalized()),int32(AQ.IsNormalized()),double(SQ.SizeSquared()),double(AQ.SizeSquared()),
        double(FVector::Dist(ST,AT)),double((AS-SS).Size()),int32(AngularValid),
        AngularValid?double(SQ.GetNormalized().AngularDistance(AQ.GetNormalized())):-1.0));
}

inline TArray<FString> PersistentDifferences(const UDinkSaveGame& Saved,const UDinkSaveGame& Actual)
{
    TArray<FString> Errors;
    // Exact reflected values: includes all stat fields, slots/armed slots,
    // override timestamps/variants and exit times. No text rounding or ignore list.
    // Facts: every one but &vision. load_game's load_map sets *pvision = 0 (dink.cpp:1017, called at 1460) and the restarted
    // screen's base script sets it again (BuildScreenBackground, 1462), so a 1997 load keeps no saved &vision: when the screen
    // changed since Dink entered it (SCR_536 after the bombed rock: saved 1, its base script now says 2) the load shows the new one.
    {
        TSet<FName> Keys;Saved.Facts.GetKeys(Keys);for(const auto& P:Actual.Facts)Keys.Add(P.Key);
        bool bSame=true;TArray<FString> Moved;
        for(const FName& Key:Keys)
        {
            if(Key==FName(TEXT("vision")))continue;
            const int32* A=Saved.Facts.Find(Key);const int32* B=Actual.Facts.Find(Key);
            if(!A||!B||*A!=*B)
            {
                bSame=false;
                Moved.Add(FString::Printf(TEXT("persistent fact %s: saved %s, after the load %s"),*Key.ToString(),
                    A?*FString::FromInt(*A):TEXT("(none)"),B?*FString::FromInt(*B):TEXT("(none)")));
            }
        }
        if(!bSame){Errors.Add(TEXT("persistent Facts differs"));Errors.Append(Moved);}
    }
    for(const TCHAR* Name:{TEXT("PlayerStats"),TEXT("Inventory"),TEXT("Overrides"),
        TEXT("ScreenExitTimes"),TEXT("GameTimeMs"),TEXT("CurrentScreen"),TEXT("PlayerTransform")})
    {
        const FProperty* Field=FindFProperty<FProperty>(UDinkSaveGame::StaticClass(),Name);
        if(!Field||!Field->Identical_InContainer(&Saved,&Actual))
        {
            Errors.Add(FString::Printf(TEXT("persistent %s differs"),Name));
            if(FCString::Strcmp(Name,TEXT("PlayerTransform"))==0)
                AppendTransformDiagnostics(Saved.PlayerTransform,Actual.PlayerTransform,Errors);
        }
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
