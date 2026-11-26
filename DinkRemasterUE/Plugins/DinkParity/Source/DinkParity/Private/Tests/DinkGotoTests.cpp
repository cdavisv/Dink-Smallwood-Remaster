// dink.Goto (A7, 25 Nov 2026): a teleport onto raised landforms puts Dink's drawn body and the camera ON the drawn ground
// (README of #224: Goto onto the bank splat S094_P06 left both under the surface), and a Goto from an outdoor screen into an
// interior (SCR_001, Terris 530) moves him there or says why it cannot (OPUS_HANDOFF task 6: it silently did nothing).
#include "DinkTestHelpers.h"
#include "DinkLandforms.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
class FDinkGotoPIE : public IAutomationLatentCommand
{
public:
	explicit FDinkGotoPIE(FAutomationTestBase* T) : Test(T) {}
	bool Update() override
	{
		if (!Began) Began = FPlatformTime::Seconds();
		if (FPlatformTime::Seconds() - Began > 300) { Test->AddError(TEXT("goto PIE timeout")); Cleanup(); return true; }
		UWorld* W = GEditor ? GEditor->PlayWorld.Get() : nullptr;
		APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
		ADinkGreyboxCharacter* H = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
		UDinkStorySubsystem* Story = W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		if (!H || !Story || Story->bNewGamePending) return false;
		World = W;
		UDinkGreyboxSubsystem* Grey = W->GetSubsystem<UDinkGreyboxSubsystem>();
		UDinkLandformsSubsystem* Land = W->GetSubsystem<UDinkLandformsSubsystem>();
		const double Now = W->GetTimeSeconds(), Since = Now - At;
		auto Next = [&](int32 P) { Phase = P; At = Now; };
		auto Report = [&](const TCHAR* What, int32 Screen, float X, float Y, bool bDryExpected)
		{
			ADinkScreenVolume* S = Grey->FindScreen(Screen);
			const FVector Flat = S ? S->MapPixelToWorld(X, Y) : FVector::ZeroVector;
			const FVector Pawn = H->GetActorLocation();
			const float Half = H->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
			const float Lift = Land->HeightCmAt(FVector2D(Pawn));
			const UCameraComponent* Cam = H->FindComponentByClass<UCameraComponent>();
			const FVector CamAt = Cam ? Cam->GetComponentLocation() : FVector::ZeroVector;
			const float CamGround = Land->HeightCmAt(FVector2D(CamAt));
			Test->AddInfo(FString::Printf(TEXT("%s SCR_%03d %.0f,%.0f: on screen %d, pawn %s (flat spot %s), capsule foot %.1f, ground lift %.1f, mesh %.1f, camera %s (ground under it %.1f + flat %.1f), boom %.1f"),
				What, Screen, X, Y, S && S->ContainsWorldLocation(Pawn) ? Screen : -1, *Pawn.ToCompactString(), *Flat.ToCompactString(), Pawn.Z - Half, Lift,
				H->GetMesh()->GetComponentLocation().Z, *CamAt.ToCompactString(), CamGround, Flat.Z, H->CameraBoom ? H->CameraBoom->TargetArmLength : 0.f));
			const FString W(What);
			// the drawn body stands on the drawn ground under the capsule (feet = capsule foot + lift)
			Test->TestEqual(W + TEXT(": the drawn body stands on the drawn ground"), H->GetMesh()->GetComponentLocation().Z - (Pawn.Z - Half), double(Lift), 3.0);
			// the camera is above the drawn ground under it and above the water surface (3 cm)
			Test->TestTrue(W + TEXT(": the camera is above the drawn ground and the water"), CamAt.Z > FMath::Max(CamGround, 3.f) + 20.0);
			if (bDryExpected) Test->TestTrue(W + TEXT(": Dink stands on dry ground, not on the water bed"), Lift >= 0.f);
			return S && S->ContainsWorldLocation(Pawn);
		};
		auto Goto = [&](int32 Screen, float X, float Y) { return Grey->GotoScreen(Screen, X, Y, false, /*bOntoDrawnGround, as dink.Goto*/ true); };
		switch (Phase)
		{
		case 0:
		{
			FDinkScriptInstance Caller;
			Story->ResetRuntime();
			Story->GetDirector()->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> unfreeze 1"), {TEXT("cmd")}));
			Story->GetGameplay()->bBrainsEnabled = false;
			// the real landforms (automation runs keep them off unless asked: load them as the game does)
			FDinkLandformsData Data;
			FString Json, Error; TArray<uint8> Png;
			const FString Path = DinkLandforms::DefaultPath();
			if (!Test->TestTrue(TEXT("landforms data"), FFileHelper::LoadFileToString(Json, *Path) && FFileHelper::LoadFileToArray(Png, *(FPaths::GetPath(Path) / TEXT("landforms.png")))
				&& Data.Load(Json, Png, Error))) { Cleanup(); return true; }
			Land->SetDataForTest(MoveTemp(Data), true);
			Test->AddInfo(FString::Printf(TEXT("ground at S094 406,145: %.1f cm; 379,61: %.1f cm"), Land->HeightCmAtPixel(94, 406, 145), Land->HeightCmAtPixel(94, 379, 61)));
			Grey->GotoScreen(93, 300, 200);
			Next(1); return false;
		}
		case 1:
			if (Since < 1.0) return false;
			Test->TestTrue(TEXT("Goto 94 406 145 (the bank splat S094_P06)"), Goto(94, 406, 145));
			Next(2); return false;
		case 2:
			if (Since < 2.0) return false;
			Report(TEXT("bank splat"), 94, 406, 145, true);
			Test->TestTrue(TEXT("Goto 94 379 61"), Goto(94, 379, 61));
			Next(3); return false;
		case 3:
			if (Since < 2.0) return false;
			Report(TEXT("bank 2"), 94, 379, 61, true);
			// the middle of SCR_094's lake: 1997 water, the drawn bed 91 cm down
			Test->TestTrue(TEXT("Goto 94 300 200 (1997 water)"), Goto(94, 300, 200));
			Next(4); return false;
		case 4:
			if (Since < 1.0) return false;
			Test->TestTrue(TEXT("Goto onto 1997 water lands on screen 94"), Report(TEXT("lake"), 94, 300, 200, true));
			Test->TestTrue(TEXT("Goto 1 (300,200) from outdoors"), Goto(1, 300, 200));
			Next(5); return false;
		case 5:
			if (Since < 1.5) return false;
			Test->TestTrue(TEXT("Goto 1 from outdoors puts Dink in his house"), Report(TEXT("interior 1"), 1, 300, 200, false));
			Goto(94, 406, 145);
			Next(6); return false;
		case 6:
			if (Since < 1.0) return false;
			Test->TestTrue(TEXT("Goto 530 (300,200) from outdoors"), Goto(530, 300, 200));
			Next(7); return false;
		case 7:
			if (Since < 1.5) return false;
			Test->TestTrue(TEXT("Goto 530 from outdoors puts Dink on SCR_530"), Report(TEXT("interior 530"), 530, 300, 200, false));
			Test->TestTrue(TEXT("Goto 1 314 161 (new-game spot)"), Goto(1, 314, 161));
			Next(8); return false;
		case 8:
			if (Since < 1.5) return false;
			Test->TestTrue(TEXT("on SCR_001"), Report(TEXT("interior 1 new-game spot"), 1, 314, 161, false));
			Cleanup();
			return true;
		default: return true;
		}
	}

private:
	void Cleanup()
	{
		if (UWorld* W = World.Get())
			if (UDinkLandformsSubsystem* L = W->GetSubsystem<UDinkLandformsSubsystem>()) L->SetDataForTest(FDinkLandformsData(), false);
	}
	FAutomationTestBase* Test;
	TWeakObjectPtr<UWorld> World;
	double Began = 0.0, At = 0.0;
	int32 Phase = 0;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGotoTest, "Dink.Movement.Goto", DINK_TEST_FLAGS)
bool FDinkGotoTest::RunTest(const FString&)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!TestNotNull(TEXT("real map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	AddCommand(new FStartPIECommand(false)); AddCommand(new FDinkGotoPIE(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
