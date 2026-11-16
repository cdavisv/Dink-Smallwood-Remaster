// Dink.Art.Family.Anchor: families.json "anchor" (DinkFamilyAnchor.h) puts a family mesh on the 1997 hardbox instead of
// the card's ground point; hardbox_inner puts a thin wall module against the hardbox face towards the screen's middle.

#include "DinkTestHelpers.h"
#include "DinkFamilyAnchor.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkArtFamilyAnchorTest, "Dink.Art.Family.Anchor", DINK_TEST_FLAGS)
bool FDinkArtFamilyAnchorTest::RunTest(const FString& Parameters)
{
	EDinkFamilyAnchor Mode = EDinkFamilyAnchor::Card;
	TestTrue(TEXT("parse hardbox"), DinkFamilyAnchor::Parse(TEXT("hardbox"), Mode) && Mode == EDinkFamilyAnchor::Hardbox);
	TestTrue(TEXT("parse hardbox_inner"), DinkFamilyAnchor::Parse(TEXT("hardbox_inner"), Mode) && Mode == EDinkFamilyAnchor::HardboxInner);
	TestFalse(TEXT("unknown anchor refused"), DinkFamilyAnchor::Parse(TEXT("middle"), Mode));

	FVector2D Px;
	// a tree whose hardbox lies left of its sprite point: the mesh goes to the box centre
	TestTrue(TEXT("hardbox: target"), DinkFamilyAnchor::TargetPixel(EDinkFamilyAnchor::Hardbox, FVector2D(300, 200), FIntRect(-40, -10, 0, 10), FVector2D(5, 5), Px));
	TestTrue(TEXT("hardbox: centre of the box"), Px.Equals(FVector2D(280, 200)));
	TestFalse(TEXT("card: no target"), DinkFamilyAnchor::TargetPixel(EDinkFamilyAnchor::Card, FVector2D(300, 200), FIntRect(-40, -10, 0, 10), FVector2D(5, 5), Px));
	TestFalse(TEXT("empty box: no target"), DinkFamilyAnchor::TargetPixel(EDinkFamilyAnchor::Hardbox, FVector2D(300, 200), FIntRect(0, 0, 0, 0), FVector2D(5, 5), Px));

	// a west wall (tall, 48 px thick hardbox at x 85..133, left of the middle): a 5 px thick module stands against x 133
	TestTrue(TEXT("inner west"), DinkFamilyAnchor::TargetPixel(EDinkFamilyAnchor::HardboxInner, FVector2D(109, 150), FIntRect(-24, -50, 24, 50), FVector2D(2.5, 50), Px));
	TestTrue(TEXT("inner west: inner face"), FMath::IsNearlyEqual(Px.X, 130.5) && FMath::IsNearlyEqual(Px.Y, 150.0));
	// an east wall: against its west face
	DinkFamilyAnchor::TargetPixel(EDinkFamilyAnchor::HardboxInner, FVector2D(491, 150), FIntRect(-24, -50, 24, 50), FVector2D(2.5, 50), Px);
	TestTrue(TEXT("inner east: inner face"), FMath::IsNearlyEqual(Px.X, 469.5));
	// a north wall (wide box above the middle): against its south face
	DinkFamilyAnchor::TargetPixel(EDinkFamilyAnchor::HardboxInner, FVector2D(250, 80), FIntRect(-50, -27, 50, 27), FVector2D(50, 2.5), Px);
	TestTrue(TEXT("inner north: south face"), FMath::IsNearlyEqual(Px.Y, 104.5) && FMath::IsNearlyEqual(Px.X, 250.0));
	// a module thicker than the box stays centred
	DinkFamilyAnchor::TargetPixel(EDinkFamilyAnchor::HardboxInner, FVector2D(109, 150), FIntRect(-24, -50, 24, 50), FVector2D(30, 50), Px);
	TestTrue(TEXT("thick module: centred"), FMath::IsNearlyEqual(Px.X, 109.0));

	// frames.csv rows (the game's file, the test's text)
	const int32 Rows = DinkFamilyAnchor::LoadFramesCsv(TEXT("seq,frame,delay_ms,special,left,top,right,bottom,loop,empty,width,height,origin_x,origin_y,sha\n32,1,0,0,-30,-8,12,8,0,0,120,160,70,150,x\n"));
	TestEqual(TEXT("one frame row"), Rows, 1);
	FIntRect Box;
	int32 Width = 0, OriginX = 0;
	TestTrue(TEXT("frame hardbox"), DinkFamilyAnchor::FrameHardbox(32, 1, Box, Width, OriginX) && Box == FIntRect(-30, -8, 12, 8) && Width == 120 && OriginX == 70);
	TestFalse(TEXT("unknown frame"), DinkFamilyAnchor::FrameHardbox(32, 2, Box, Width, OriginX));
	// put the real table back for the rest of the run
	FString Text;
	if (FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Gameplay/frames.csv")))) DinkFamilyAnchor::LoadFramesCsv(Text);
	return true;
}
