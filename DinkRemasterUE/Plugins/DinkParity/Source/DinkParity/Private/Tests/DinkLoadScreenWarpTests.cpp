// Dink.Import.Greybox.LoadScreenPlacementDoesNotWarp: a script's load_screen puts Dink on a pixel inside a warp trigger, and he stays there.
//
// The original warps Dink only from the walk code's hardness hit (special_block, dink.cpp:15337); sp_x, sp_y and load_screen never run it.
// s3-sec1.c:39-43 (the stump of SCR_710's secret tree) does `&player_map = 227; sp_x(1, 515); sp_y(1, 383); load_screen(227)`, and 515,383 is
// inside the hut's exit S227_P01 (499,409, back to SCR_710): before the fix the greybox trigger fired on the teleport's overlap and the
// probe's chapter 19 never reached the bow-lore man. Here the same thing on the generated Stonebrook map: Dink put by load_screen into
// the trigger of Dink's house door (S001_P25) stays on SCR_001.

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkNarrativeTypes.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"
#include "AssetCompilingManager.h"
#include "Editor.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
#include "UObject/UObjectIterator.h"

namespace
{
	class FDinkLoadScreenWarpCheck : public IAutomationLatentCommand
	{
	public:
		explicit FDinkLoadScreenWarpCheck(FAutomationTestBase* InTest) : Test(InTest), Began(FPlatformTime::Seconds()) {}

		virtual bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
			APawn* Hero = PC ? PC->GetPawn() : nullptr;
			if (FPlatformTime::Seconds() - Began > 60.0)
			{
				Test->AddError(FString::Printf(TEXT("load_screen warp check timed out at stage %d"), Stage));
				return true;
			}
			if (!Hero)
			{
				return false;
			}
			UDinkStorySubsystem* Story = World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>();
			UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
			if (!Story || !Greybox || !Story->IsReady() || Story->bNewGamePending || World->GetTimeSeconds() < 2.0)
			{
				return false;
			}
			UDinkDirector* Director = Story->GetDirector();
			if (Stage == 0)
			{
				Story->SkipDialogue();
				Story->bRunScreenScripts = false;
				for (TObjectIterator<UDinkWarpComponent> It; It; ++It)
				{
					if (It->GetWorld() == World && It->WarpId == TEXT("S001_P25"))
					{
						Exit = *It;
					}
				}
				const ADinkScreenVolume* House = Greybox->FindScreen(1);
				if (!Test->TestNotNull(TEXT("the house door's warp S001_P25"), Exit) || !Test->TestNotNull(TEXT("SCR_001"), House))
				{
					return true;
				}
				Test->TestTrue(TEXT("the story bound the warp suppression"), !!Greybox->WarpSuppressed);
				// A pixel of SCR_001 whose world point lies inside the door's trigger box.
				const FBox Box = Exit->Bounds.GetBox();
				for (int32 Y = 399; Y >= 300 && Pixel.X == 0; --Y)
				{
					for (int32 X = 280; X <= 370; ++X)
					{
						const FVector At = House->MapPixelToWorld(X - 20.0, Y);
						if (At.X > Box.Min.X + 5.0 && At.X < Box.Max.X - 5.0 && At.Y > Box.Min.Y + 5.0 && At.Y < Box.Max.Y - 5.0)
						{
							Pixel = FIntPoint(X, Y);
							break;
						}
					}
				}
				if (!Test->TestTrue(TEXT("a pixel of SCR_001 inside the door's trigger"), Pixel.X != 0))
				{
					return true;
				}
				// What s3-sec1.c:39-42 does: &player_map, sp_x, sp_y, load_screen.
				Story->GetFacts()->SetFact(TEXT("player_map"), 1);
				FDinkSprite& Dink = Director->GetDink();
				Dink.X = Pixel.X;
				Dink.Y = Pixel.Y;
				FDinkScriptInstance* Instance = Story->GetInstances().Num() > 0 ? Story->GetInstances()[0].Get() : nullptr;
				FDinkScriptInstance Stand;
				Director->Execute(Instance ? *Instance : Stand, FDinkStoryLine::Parse(TEXT(">> load_screen"), { TEXT("cmd"), TEXT("src:1") }));
				Test->TestTrue(TEXT("the pawn overlaps the door's trigger after load_screen"), Exit->IsOverlappingActor(Hero));
				Wait = World->GetTimeSeconds() + 1.0;
				Stage = 1;
				return false;
			}
			if (World->GetTimeSeconds() < Wait)
			{
				return false;
			}
			Greybox->RefreshCurrentScreen();
			const ADinkScreenVolume* Now = Greybox->FindScreenAt(Hero->GetActorLocation());
			Test->TestEqual(TEXT("load_screen into a warp's trigger: Dink stays on SCR_001 (no warp, as in the original)"), Now ? Now->ScreenNumber : 0, 1);
			Test->TestTrue(TEXT("and not at the warp's destination"), FVector2D(Hero->GetActorLocation() - Exit->DestLocation).Size() > 200.0);
			Test->AddInfo(FString::Printf(TEXT("placed at pixel %d,%d of SCR_001"), Pixel.X, Pixel.Y));
			return true;
		}

	private:
		FAutomationTestBase* Test;
		double Began;
		double Wait = 0.0;
		int32 Stage = 0;
		UDinkWarpComponent* Exit = nullptr;
		FIntPoint Pixel = FIntPoint(0, 0);
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkLoadScreenWarpTest, "Dink.Import.Greybox.LoadScreenPlacementDoesNotWarp", DINK_TEST_FLAGS)
bool FDinkLoadScreenWarpTest::RunTest(const FString&)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook"), FPackageName::GetMapPackageExtension());
	if (!IFileManager::Get().FileExists(*File))
	{
		AddWarning(TEXT("skipped: generated Stonebrook map absent"));
		return true;
	}
	if (!TestNotNull(TEXT("the Stonebrook map loads"), UEditorLoadingAndSavingUtils::LoadMap(File)))
	{
		return false;
	}
	FAssetCompilingManager::Get().FinishAllCompilation();
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FDinkLoadScreenWarpCheck(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
