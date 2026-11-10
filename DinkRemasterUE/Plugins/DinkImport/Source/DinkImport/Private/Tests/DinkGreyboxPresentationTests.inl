// Included only by DinkGreyboxAssets.cpp: exercises the exact production mesh writer without asset saves.
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGreyboxPresentationSplitTest,
    "Dink.Import.Greybox.GroundWaterAndDebugMeshSplit",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDinkGreyboxPresentationSplitTest::RunTest(const FString&)
{
    using namespace DinkGreybox;
    FDinkBundleScreen Screen;
    Screen.Corners.NW={0,0}; Screen.Corners.NE={26.25,0};
    Screen.Corners.SW={0,17.5}; Screen.Corners.SE={26.25,17.5};
    FDinkBundleCollision Collision;
    // The actual SCR003 hero-containing hard rectangle, plus every presentation class and water.
    Collision.ByClass.Add(TEXT("sprite"),{FIntRect(293,262,453,305)});
    Collision.ByClass.Add(TEXT("solid"),{FIntRect(0,0,10,10)});
    Collision.ByClass.Add(TEXT("low"),{FIntRect(10,0,20,10)});
    Collision.ByClass.Add(TEXT("warp"),{FIntRect(20,0,30,10)});
    Collision.ByClass.Add(TEXT("fill_water"),{FIntRect(40,0,50,10)});
    Collision.ByClass.Add(TEXT("fill_solid"),{FIntRect(50,0,60,10)}); // physical-only, still not scenery
    const auto Before=Collision.ByClass;
    FMeshWriter Visual,Debug;
    WriteScreenPresentation(Screen,Collision,FVector::ZeroVector,Visual,Debug);
    TestEqual(TEXT("original textured ground keeps192 triangles plus water top2"),Visual.Triangles,194);
    TestEqual(TEXT("exact ground/water presentation groups"),Visual.GroupOrder.Num(),2);
    TestTrue(TEXT("ground and water retained"),Visual.Groups.Contains(TEXT("Ground"))&&Visual.Groups.Contains(TEXT("Water")));
    TestEqual(TEXT("four nonempty debug prisms keep40 triangles"),Debug.Triangles,40);
    TestEqual(TEXT("four debug class groups"),Debug.GroupOrder.Num(),4);
    for(const FName Slot:{FName(TEXT("Solid")),FName(TEXT("Low")),FName(TEXT("Sprite")),FName(TEXT("Warp"))})
    {
        TestFalse(TEXT("debug class absent from normal presentation"),Visual.Groups.Contains(Slot));
        TestTrue(TEXT("debug class preserved for explicit inspection"),Debug.Groups.Contains(Slot));
    }
    TestFalse(TEXT("water not duplicated into debug"),Debug.Groups.Contains(TEXT("Water")));
    float VisualMax=-FLT_MAX,DebugMax=-FLT_MAX;
    for(const FVertexID ID:Visual.Desc.Vertices().GetElementIDs())VisualMax=FMath::Max(VisualMax,Visual.Positions[ID].Z);
    for(const FVertexID ID:Debug.Desc.Vertices().GetElementIDs())DebugMax=FMath::Max(DebugMax,Debug.Positions[ID].Z);
    TestEqual(TEXT("only3cm water surface above normal ground"),VisualMax,3.f);
    TestEqual(TEXT("original100cm debug prism height retained"),DebugMax,100.f);
    FBox3f SpriteBox(ForceInit);
    const auto Group=Debug.Groups.FindChecked(TEXT("Sprite"));
    for(const FPolygonID P:Debug.Desc.GetPolygonGroupPolygons(Group))
        for(const FVertexInstanceID VI:Debug.Desc.GetPolygonVertexInstances(P))
            SpriteBox+=Debug.Positions[Debug.Desc.GetVertexInstanceVertex(VI)];
    TestEqual(TEXT("actual old oversized width preserved only in debug"),SpriteBox.GetSize().X,700.f);
    TestEqual(TEXT("actual old oversized depth preserved only in debug"),SpriteBox.GetSize().Y,188.125f);
    TestTrue(TEXT("source collision class membership unchanged"),Before.OrderIndependentCompareEqual(Collision.ByClass));
    FMeshWriter EmptyVisual,EmptyDebug;FDinkBundleCollision Empty;
    WriteScreenPresentation(Screen,Empty,FVector::ZeroVector,EmptyVisual,EmptyDebug);
    TestEqual(TEXT("empty-hardness screen still has original ground"),EmptyVisual.Triangles,192);
    TestEqual(TEXT("empty debug has no dummy geometry"),EmptyDebug.Triangles,0);
    const FString DebugPackage=TEXT("/Game/Dink/_Generated/Screens/SCR_003/SM_SCR_003_DebugBlockers");
    TestFalse(TEXT("nonempty debug asset retained"),ShouldPruneUnusedDebugMesh(DebugPackage,&Collision));
    TestTrue(TEXT("nonempty-to-empty debug asset is pruned"),ShouldPruneUnusedDebugMesh(DebugPackage,&Empty));
    FDinkBundleCollision WaterOnly;WaterOnly.ByClass.Add(TEXT("fill_water"),{FIntRect(0,0,10,10)});
    TestTrue(TEXT("water-only does not retain obsolete debug asset"),ShouldPruneUnusedDebugMesh(DebugPackage,&WaterOnly));
    TestFalse(TEXT("missing collision record never authorizes deletion"),ShouldPruneUnusedDebugMesh(DebugPackage,nullptr));
    for(const FString Suffix:{FString(TEXT("CollSolid")),FString(TEXT("CollLow")),FString(TEXT("Visual"))})
        TestFalse(TEXT("debug pruning cannot delete physical/normal assets"),ShouldPruneUnusedDebugMesh(TEXT("/Game/Dink/_Generated/Screens/SCR_003/SM_SCR_003_")+Suffix,&Empty));
    return true;
}
