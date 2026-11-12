#pragma once
#include <algorithm>
#include <array>
#include <map>
#include <optional>
#include <vector>

namespace DinkHardness
{
// Original add_sprite[_dumb] scans active slots1..299. UE script handles are
// deliberately not changed. Negative occupants reserve an initial editor birth.
class OriginalSlots
{
public:
    static constexpr int Limit=300;
    OriginalSlots() { Active[1]=1; Handles[1]=1; Last[1]=1; }
    bool Valid() const { return Good; }
    void Refuse() { Good=false; }
    std::optional<int> Slot(int Handle) const
    { auto I=Handles.find(Handle); return I==Handles.end()?std::nullopt:std::optional<int>(I->second); }
    bool Preserve(int Handle,int Index)
    {
        if(Handle<1||Index<1||Index>=Limit||Active[Index]||Handles.count(Handle)) return Reject();
        Active[Index]=Handle; Handles[Handle]=Index; Last[Handle]=Index; return true;
    }
    bool Birth(int Handle)
    {
        if(!Good||Handle<=1||Handles.count(Handle)) return Reject();
        int Index=Free(); if(!Index)return Reject();
        Active[Index]=Handle; Handles[Handle]=Index; Last[Handle]=Index; return true;
    }
    bool ReserveEditor(int Owner)
    {
        if(!Good||Owner<1||Owner>99||Editors.count(Owner))return Reject();
        int Index=Free();if(!Index)return Reject();Active[Index]=-Owner;Editors[Owner]=Index;return true;
    }
    bool BindEditor(int Owner,int Handle)
    {
        auto I=Editors.find(Owner);
        if(!Good||I==Editors.end()||Handle<=1)return Reject();
        int Index=I->second;
        if(Active[Index]==Handle)return Slot(Handle)==Index;
        if(Active[Index]!=-Owner||Handles.count(Handle))return Reject();
        Active[Index]=Handle;Handles[Handle]=Index;Last[Handle]=Index;return true;
    }
    bool HasEditor(int Owner) const { return Editors.count(Owner)!=0; }
    bool Bound() const
    { return std::none_of(Active.begin(),Active.end(),[](int H){return H<0;}); }
    bool Scratch() { return Good&&(Free()!=0||Reject()); }
    void Release(int Handle)
    {
        auto I=Handles.find(Handle);if(I==Handles.end()||Handle==1)return;
        Active[I->second]=0;Handles.erase(I);
    }
    bool Reactivate(int Handle)
    {
        if(Slot(Handle))return true;
        auto I=Last.find(Handle);
        // Reusing a UE handle after its original slot was reused has no exact
        // translation; refuse admission rather than silently inventing an order.
        if(!Good||I==Last.end()||Active[I->second])return Reject();
        Active[I->second]=Handle;Handles[Handle]=I->second;return true;
    }
private:
    bool Good=true;
    std::array<int,Limit> Active{};
    std::map<int,int> Handles,Last,Editors;
    int Free() const {for(int I=1;I<Limit;++I)if(!Active[I])return I;return 0;}
    bool Reject(){Good=false;return false;}
};
struct EditorFields { int Type,Hard,Seq,Frame;bool Removed,ClearScript; };
inline EditorFields ProjectEditorFields(int Type,int Hard,int Seq,int Frame,int Override,
                                       int SavedSeq,int SavedFrame,std::optional<int> RuntimeHard={})
{
    EditorFields Out{Type,RuntimeHard?*RuntimeHard:Hard,Seq,Frame,false,false};
    if(Override!=0){Out.Seq=SavedSeq;Out.Frame=SavedFrame;Out.ClearScript=true;}
    if(Override==1||Override==6||Override==7||Override==8)Out.Removed=true;
    if(Override==2||Override==4)Out.Type=1;
    if(Override==3||Override==5)Out.Type=0;
    if(Override==2||Override==3)Out.Hard=1;
    if(Override==4||Override==5)Out.Hard=0;
    return Out;
}
struct InitialPlacement
{
    int Owner,Type,Y,Que,Vision;
};
inline std::optional<std::vector<InitialPlacement>> MixedInitialOrder(
    std::vector<InitialPlacement> Placements,int Vision)
{
    std::array<bool,100> Seen{};
    for(const auto& P:Placements)
    {
        if(P.Owner<1||P.Owner>99||Seen[P.Owner]||P.Type<0||P.Type>2)return std::nullopt;
        Seen[P.Owner]=true;
    }
    std::sort(Placements.begin(),Placements.end(),[](const auto&A,const auto&B){
        int AY=A.Que?A.Que:A.Y,BY=B.Que?B.Que:B.Y;
        return AY!=BY?AY<BY:A.Owner<B.Owner;
    });
    Placements.erase(std::remove_if(Placements.begin(),Placements.end(),[Vision](const auto&P){
        return (P.Vision!=0&&P.Vision!=Vision)||(P.Que?P.Que:P.Y)>=20000;
    }),Placements.end());
    return Placements;
}
}
