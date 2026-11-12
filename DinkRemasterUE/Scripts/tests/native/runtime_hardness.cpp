#include "Hardness/DinkHardnessLayers.h"
#include <cassert>
#include <iostream>
using namespace DinkHardness;
int main()
{
    Layers::Pixels Base(600 * 400, 0);
    Base[300 * 600 + 390] = 2; // low water/fence hidden beneath barrel
    Base[300 * 600 + 391] = 1; // wall hidden beneath barrel
    Base[310 * 600 + 500] = 3; // unrelated geometry must survive
    Stamp Barrel{{379,291,416,312},113}; // actual S209_P13 footprint
    Stamp Behind{{400,300,430,320},114};
    auto Created = Layers::Create(Base, {Behind, Barrel});
    assert(Created);
    auto& Map = *Created;
    assert(Map.Get(390,300) == 113 && Map.Get(405,305) == 113);
    // sp_hard 1 only changes eligibility in the caller, never clears pixels.
    const std::vector<Stamp> SoftBarrel{Behind};
    assert(Map.Get(390,300) == 113);
    assert(Map.Redraw(Barrel.Bounds, SoftBarrel));
    assert(Map.Get(390,300) == 2 && Map.Get(391,300) == 1);
    assert(Map.Get(405,305) == 114 && Map.Get(500,310) == 3);
    // Restoration, including which owner wins the overlap.
    assert(Map.Redraw(Barrel.Bounds, {Behind,Barrel}));
    assert(Map.Get(390,300) == 113 && Map.Get(405,305) == 113);
    assert(Map.Redraw(Barrel.Bounds, {Barrel,Behind}));
    assert(Map.Get(405,305) == 114);
    // Original clear uses current pseq/pframe, not the previous or animation box:
    // only clearing the small stump preserves old pixels outside that rectangle.
    Stamp Tree{{200,200,294,236},115}, Stump{{234,209,264,230},115};
    auto TreeMap = Layers::Create(Base,{Tree});
    assert(TreeMap && TreeMap->Redraw(Tree.Bounds, {})); // dam-fire first makes tree soft
    assert(TreeMap->Get(201,201) == 0);
    assert(TreeMap->Redraw(Stump.Bounds,{Stump})); // then hard0 restores HARD stump
    assert(TreeMap->Get(240,215) == 115 && TreeMap->Get(201,201) == 0);
    auto Residual = Layers::Create(Base,{Tree});
    assert(Residual && Residual->Redraw(Stump.Bounds,{}));
    assert(Residual->Get(201,201) == 115 && Residual->Get(240,215) == 0);
    // Restamps are global, not clipped to the clear box (original fills all).
    assert(Residual->Redraw({0,0,1,1},{{{550,350,560,360},1}}));
    assert(Residual->Get(551,351) == 1);
    // Owner-partition collision plan must rasterize exactly, including low2.
    Layers::Pixels Raster(600*400,0);
    for (const auto& R : Map.CollisionRects())
        for (int Y=R.Bounds.Top; Y<R.Bounds.Bottom; ++Y)
            for (int X=R.Bounds.Left; X<R.Bounds.Right; ++X)
            { assert(!Raster[Y*600+X]); Raster[Y*600+X]=R.Code; }
    assert(Raster == Map.GetPixels());
    // Clipping and strict refusal leave prior state intact.
    assert(Map.Redraw({-20,-20,2,2},{{{-30,-30,1,1},199}}));
    assert(Map.Get(0,0)==199 && Map.Get(-1,0)==0 && Map.Get(600,400)==0);
    const auto Before=Map.GetPixels();
    assert(!Map.Redraw(Barrel.Bounds,{{Barrel.Bounds,200}}));
    assert(Map.GetPixels()==Before);
    assert(!Layers::Create({},{}));
    Base[0]=100; assert(!Layers::Create(Base,{})); // never accept composed owner bytes as base
    std::cout << "PASS removal/restoration/overlap/tile-low/unrelated/current-picture/stump/global-restamp/owner-partition/clipping/refusal\n";
}
