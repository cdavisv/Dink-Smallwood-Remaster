#pragma once
#include <utility>
#include <array>
#include <optional>
namespace DinkHardness
{
enum class Activation { Legacy, Refuse, Projected };
// A data update cannot migrate an old generated collision world. Only its
// explicit physical-world capability can demand the new pipeline.
constexpr Activation SelectActivation(bool MarkedWorld,bool SourceReady)
{return !MarkedWorld?Activation::Legacy:SourceReady?Activation::Projected:Activation::Refuse;}
enum class VisionTransition { PreservePublished, RebindBase, RebuildScreen };
constexpr VisionTransition SelectVisionTransition(bool BaseMain,bool Forced)
{return Forced?VisionTransition::RebuildScreen:BaseMain?VisionTransition::RebindBase:VisionTransition::PreservePublished;}
template<class Instance> void PreserveForceVisionCaller(Instance& Caller,int NoSprite)
{Caller.Sprite=NoSprite;Caller.AttachedTo=NoSprite;}
constexpr bool ShouldApplyOriginalVision(bool BackgroundOnly,int EffectiveType){return !BackgroundOnly||EffectiveType==0;}
inline std::optional<int> CurrentEditorHardFlag(const std::array<int,100>& Raw,int Index,int Override,std::optional<int> Runtime={})
{
    if(Index<1||Index>99||Override<0||Override>8)return std::nullopt;
    int Hard=Runtime?*Runtime:Raw[Index];
    if(Override==2||Override==3)Hard=1;
    if(Override==4||Override==5)Hard=0;
    return Hard;
}
constexpr bool ApplyFactVisionImmediately(bool MarkedWorld){return !MarkedWorld;}
constexpr bool RestartOriginalScreenOnLoad(bool MarkedWorld){return MarkedWorld;}
template<class Sprite> void CarryLiveScreenIdentity(Sprite& Live,int Screen){Live.Screen=Screen;}
template<class Stamps> Stamps OriginalDrawPasses(Stamps Background,Stamps Live,bool WholeMap)
{
    auto& First=WholeMap?Live:Background;
    auto& Second=WholeMap?Background:Live;
    First.insert(First.end(),Second.begin(),Second.end());
    return std::move(First);
}
}
