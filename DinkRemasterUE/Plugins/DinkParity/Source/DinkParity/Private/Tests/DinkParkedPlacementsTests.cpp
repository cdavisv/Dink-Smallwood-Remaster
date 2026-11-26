// Bug A13 (SP-08, 25 Nov 2026): a placement 1997 parks outside the 600 x 400 playfield (the red knight S241_P03 at map y 564) is drawn
// by no render pass and collides with nothing, on its own screen and on the neighbour it stands on, until a script moves it in.
#include "DinkTestHelpers.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkOriginComponent.h"
#include "DinkPlayerBlockers.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Components/PrimitiveComponent.h"
#include "Components/ShapeComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkParkedPictureRectTest, "Dink.Gameplay.ParkedPlacements.PictureRect", DINK_TEST_FLAGS)
bool FDinkParkedPictureRectTest::RunTest(const FString&)
{
	// the red knight S241_P03: engine x 87 (map 67), y 564, picture 712/1 121 x 127 with its point at 92, 98: top at 466 > 400
	TestTrue(TEXT("the parked knight's picture lies below the field"), UDinkGameplay::PictureOutsideField(87, 564, 121, 127, 92, 98, 100));
	TestFalse(TEXT("the same knight at y 200 is inside"), UDinkGameplay::PictureOutsideField(87, 200, 121, 127, 92, 98, 100));
	// a counter at map y 437 whose picture still reaches up into the field (S001_P25's 156 x 77 picture) is drawn in 1997
	TestFalse(TEXT("a picture that reaches into the field is not parked"), UDinkGameplay::PictureOutsideField(325, 437, 156, 77, 78, 70, 100));
	TestTrue(TEXT("a picture wholly right of the field is parked"), UDinkGameplay::PictureOutsideField(20 + 700, 200, 50, 50, 25, 40, 100));
	TestFalse(TEXT("a picture over the right edge is not"), UDinkGameplay::PictureOutsideField(20 + 610, 200, 50, 50, 25, 40, 100));
	TestTrue(TEXT("size scales the picture: a 50% knight at y 450 starts below the field"), UDinkGameplay::PictureOutsideField(87, 450, 121, 127, 92, 98, 50));
	TestFalse(TEXT("a 200% knight at y 450 reaches back into the field"), UDinkGameplay::PictureOutsideField(87, 450, 121, 127, 92, 98, 200));
	TestTrue(TEXT("a picture of no size counts by its point"), UDinkGameplay::PictureOutsideField(0, 0, 0, 0, 0, 0, 100));
	return true;
}

namespace
{
class FDinkParkedPIE : public IAutomationLatentCommand
{
public:
	explicit FDinkParkedPIE(FAutomationTestBase* T) : Test(T) {}
	bool Update() override
	{
		if (!Began) Began = FPlatformTime::Seconds();
		if (FPlatformTime::Seconds() - Began > 240) { Test->AddError(TEXT("parked placements PIE timeout")); return true; }
		UWorld* W = GEditor ? GEditor->PlayWorld.Get() : nullptr;
		APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
		ADinkGreyboxCharacter* H = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
		UDinkStorySubsystem* Story = W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		if (!H || !Story || Story->bNewGamePending) return false;
		UDinkGreyboxSubsystem* Grey = W->GetSubsystem<UDinkGreyboxSubsystem>();
		UDinkDirector* D = Story->GetDirector();
		const double Now = W->GetTimeSeconds(), Since = Now - At;
		auto Next = [&](int32 P) { Phase = P; At = Now; };
		auto Find = [&](const TCHAR* Origin) -> ADinkPlaceholderActor*
		{
			for (TActorIterator<ADinkPlaceholderActor> It(W); It; ++It)
				if (It->Origin && It->Origin->OriginId.ToString() == Origin) return *It;
			return nullptr;
		};
		// drawn: some drawn component in the main pass; colliding: some body shape that collides
		auto Drawn = [](const AActor& A, int32& OutDrawn, int32& OutHidden, int32& OutShapesOn, int32& OutShapesOff)
		{
			OutDrawn = OutHidden = OutShapesOn = OutShapesOff = 0;
			TInlineComponentArray<UPrimitiveComponent*> Cs(&A);
			for (const UPrimitiveComponent* C : Cs)
			{
				if (C->ComponentHasTag(DinkPlayerBlockers::Tag)) continue;
				if (Cast<UShapeComponent>(C)) { (C->GetCollisionEnabled() != ECollisionEnabled::NoCollision ? OutShapesOn : OutShapesOff)++; continue; }
				(C->bRenderInMainPass ? OutDrawn : OutHidden)++;
			}
		};
		int32 Dr = 0, Hi = 0, On = 0, Off = 0;
		switch (Phase)
		{
		case 0:
		{
			FDinkScriptInstance Caller;
			Story->ResetRuntime();
			D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> unfreeze 1"), {TEXT("cmd")}));
			Story->GetGameplay()->bBrainsEnabled = false;
			Grey->GotoScreen(273, 300, 200); // the screen south of 241, where the knight's map point stands
			Next(1); return false;
		}
		case 1:
		{
			if (Since < 1.5) return false;
			ADinkPlaceholderActor* Knight = Find(TEXT("S241_P03"));
			if (!Test->TestNotNull(TEXT("the red knight S241_P03 is in the world"), Knight)) return true;
			Drawn(*Knight, Dr, Hi, On, Off);
			Test->AddInfo(FString::Printf(TEXT("from SCR_273: knight parked %d, drawn parts %d, out of the passes %d, shapes colliding %d, off %d"),
				UDinkGameplay::IsParked(Knight) ? 1 : 0, Dr, Hi, On, Off));
			Test->TestTrue(TEXT("seen from the neighbour, the parked knight is parked"), UDinkGameplay::IsParked(Knight));
			Test->TestEqual(TEXT("no part of it is drawn"), Dr, 0);
			Test->TestEqual(TEXT("no body shape of it collides"), On, 0);
			Grey->GotoScreen(241, 300, 200);
			Next(2); return false;
		}
		case 2:
		{
			if (Since < 1.5) return false;
			ADinkPlaceholderActor* Knight = Find(TEXT("S241_P03"));
			Test->TestTrue(TEXT("on its own screen it stays parked (1997 never draws it)"), UDinkGameplay::IsParked(Knight));
			int32 InField = 0, ParkedInField = 0;
			for (TActorIterator<ADinkPlaceholderActor> It(W); It; ++It)
				if (It->ScreenNumber == 241 && *It != Knight) { ++InField; ParkedInField += UDinkGameplay::IsParked(*It) ? 1 : 0; }
			Test->TestTrue(TEXT("SCR_241 has other placements"), InField > 0);
			Test->TestEqual(TEXT("none of SCR_241's placements inside the field is parked"), ParkedInField, 0);
			// a script moves the knight into the field: he is drawn again and his body collides again
			Handle = 0;
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites()) if (Pair.Value.Actor.Get() == Knight) Handle = Pair.Key;
			if (!Test->TestTrue(TEXT("the knight is a live sprite on SCR_241"), Handle > 0)) return true;
			FDinkScriptInstance Caller;
			D->Execute(Caller, FDinkStoryLine::Parse(FString::Printf(TEXT(">> sp_y %d 250"), Handle), {TEXT("cmd")}));
			Next(3); return false;
		}
		case 3:
		{
			if (Since < 0.5) return false;
			ADinkPlaceholderActor* Knight = Find(TEXT("S241_P03"));
			Drawn(*Knight, Dr, Hi, On, Off);
			Test->AddInfo(FString::Printf(TEXT("moved in: parked %d, drawn parts %d, out of the passes %d, shapes colliding %d, off %d"),
				UDinkGameplay::IsParked(Knight) ? 1 : 0, Dr, Hi, On, Off));
			Test->TestFalse(TEXT("moved into the field by a script, the knight is not parked"), UDinkGameplay::IsParked(Knight));
			Test->TestEqual(TEXT("every part the rule took out is back in the passes"), Hi, HiddenBefore);
			Test->TestEqual(TEXT("its body shapes collide again"), Off, 0);
			FDinkScriptInstance Caller;
			D->Execute(Caller, FDinkStoryLine::Parse(FString::Printf(TEXT(">> sp_y %d 564"), Handle), {TEXT("cmd")}));
			Next(4); return false;
		}
		case 4:
		{
			if (Since < 0.5) return false;
			ADinkPlaceholderActor* Knight = Find(TEXT("S241_P03"));
			Drawn(*Knight, Dr, Hi, On, Off);
			Test->TestTrue(TEXT("moved out again, parked again"), UDinkGameplay::IsParked(Knight));
			Test->TestEqual(TEXT("and not drawn"), Dr, 0);
			// review switch: off = the look before (drawn on the neighbour)
			if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ParkedPlacements"))) V->Set(0, ECVF_SetByConsole);
			Next(5); return false;
		}
		case 5:
		{
			if (Since < 0.5) return false;
			ADinkPlaceholderActor* Knight = Find(TEXT("S241_P03"));
			Test->TestFalse(TEXT("dink.ParkedPlacements 0: not parked"), UDinkGameplay::IsParked(Knight));
			if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ParkedPlacements"))) V->Set(1, ECVF_SetByConsole);
			return true;
		}
		default: return true;
		}
	}
private:
	FAutomationTestBase* Test;
	double Began = 0.0, At = 0.0;
	int32 Phase = 0, Handle = 0, HiddenBefore = 0;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkParkedPlacementsTest, "Dink.Gameplay.ParkedPlacements.RedKnight", DINK_TEST_FLAGS)
bool FDinkParkedPlacementsTest::RunTest(const FString&)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!TestNotNull(TEXT("real map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	AddCommand(new FStartPIECommand(false)); AddCommand(new FDinkParkedPIE(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
