#pragma once
#include "DinkHardnessLayers.h"
namespace DinkHardness
{
// getpic (dink.cpp443) uses displayed pseq/pframe ONLY. seq/frame do not enter
// this API. Animation may update the displayed fields on a later engine tick.
template<class Lookup>
std::optional<Rect> DisplayedBounds(int PSeq, int PFrame, int EngineX, int Y, Lookup&& FindRelative)
{
    const int X = EngineX - 20;
    if (PSeq == 0 || PFrame == 0) return Rect{X,Y,X,Y};
    const auto Relative = FindRelative(PSeq, PFrame);
    if (!Relative) return std::nullopt;
    return Rect{X+Relative->Left,Y+Relative->Top,X+Relative->Right,Y+Relative->Bottom};
}
}
