#pragma once
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
constexpr bool ApplyFactVisionImmediately(bool MarkedWorld){return !MarkedWorld;}
constexpr bool RestartOriginalScreenOnLoad(bool MarkedWorld){return MarkedWorld;}
template<class Sprite> void CarryLiveScreenIdentity(Sprite& Live,int Screen){Live.Screen=Screen;}
}
