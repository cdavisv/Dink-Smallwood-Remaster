// Dink.PhysicalPlay.RealScreens: the physical play layer ON in the real generated world (PIE), so CI covers play mode
// (review of PR #160). (1) SCR_215: walking west along y 78 at the pine S215_P05, whose 1997 box (right edge x 409) is relaxed,
// Dink stops at the box with the layer off and walks past its edge with it on. (2) SCR_438: a class pillbug (creature body,
// skinned) is hit by Dink's fist at drawn contact and not from 1.5 m in front of its body with the part Hits on, and its own box is
// the size of a pillbug, not of its world bounds. (3) With the default parts (Hits off, Bodies on), Dink walking into the pillbug
// is stopped by its body box, and from there his blow is the 1997 box test and lands.
#include "DinkTestHelpers.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/SkinnedMeshComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
class FDinkPhysicalPlayWorldPIE : public IAutomationLatentCommand
{
public:
	explicit FDinkPhysicalPlayWorldPIE(FAutomationTestBase* T) : Test(T) {}
	~FDinkPhysicalPlayWorldPIE()
	{
		for (const TCHAR* Name : { TEXT("dink.PhysicalPlay"), TEXT("dink.PhysicalPlay.Hits") })
			if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(Name)) V->Set(-1, ECVF_SetByConsole);
	}
	bool Update() override
	{
		if (!Began) Began = FPlatformTime::Seconds();
		if (FPlatformTime::Seconds() - Began > 240) { Test->AddError(TEXT("physical play PIE timeout")); return true; }
		UWorld* W = GEditor ? GEditor->PlayWorld.Get() : nullptr;
		APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
		ADinkGreyboxCharacter* H = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
		UDinkStorySubsystem* Story = W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		if (!H || !Story || Story->bNewGamePending) return false;
		UDinkGreyboxSubsystem* Grey = W->GetSubsystem<UDinkGreyboxSubsystem>();
		UDinkDirector* D = Story->GetDirector();
		UDinkGameplay* G = Story->GetGameplay();
		const double Now = W->GetTimeSeconds();
		const double Since = Now - At;
		auto Next = [&](int32 P) { Phase = P; At = Now; };
		auto Mode = [](int32 M) { if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.PhysicalPlay"))) V->Set(M, ECVF_SetByConsole); };
		auto Hits = [](int32 M) { if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.PhysicalPlay.Hits"))) V->Set(M, ECVF_SetByConsole); };
		ADinkScreenVolume* S215 = Grey->FindScreen(215);
		if (!Test->TestNotNull(TEXT("SCR_215 in the world"), S215)) return true;
		const double BoxEdgeX = S215->MapPixelToWorld(409, 78).X; // the pine's 1997 box, right edge (map x grows with world X here)
		// ---- (1) the relaxed pine, layer off then on
		if (Phase == 0)
		{
			// the new game's intro freezes Dink: start from a reset runtime, unfrozen (as Dink.Mechanics.HeroInputParity)
			FDinkScriptInstance Caller;
			Story->ResetRuntime();
			D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> unfreeze 1"), {TEXT("cmd")}));
		}
		if (Phase == 0 || Phase == 10)
		{
			// enter SCR_215 from its neighbour, so the screen's entry (ApplyPhysicalPlayCollision) runs under this mode
			Mode(Phase == 0 ? 0 : 2);
			G->bBrainsEnabled = false;
			Grey->GotoScreen(216, 300, 200);
			Next(Phase + 3); return false;
		}
		if (Phase == 3 || Phase == 13)
		{
			if (Since < 1.0) return false;
			Grey->GotoScreen(215, 450, 78);
			Next(Phase - 2); return false;
		}
		if (Phase == 1 || Phase == 11)
		{
			if (Since < 1.5) return false;
			Start = H->GetActorLocation();
			Next(Phase + 1); return false;
		}
		if (Phase == 2 || Phase == 12)
		{
			const FVector West = (S215->MapPixelToWorld(330, 78) - S215->MapPixelToWorld(450, 78)).GetSafeNormal2D();
			H->AddMovementInput(West);
			if (Since < 3.0) return false;
			const double X = H->GetActorLocation().X;
			Test->AddInfo(FString::Printf(TEXT("pine S215_P05, layer %s: walked from %.0f to %.0f cm (1997 box edge at %.0f)"), Phase == 2 ? TEXT("off") : TEXT("on"), Start.X, X, BoxEdgeX));
			if (Phase == 2) Test->TestTrue(TEXT("layer off: the 1997 box stops Dink at its edge"), X > BoxEdgeX - 30.0);
			else Test->TestTrue(TEXT("layer on: Dink walks past the 1997 box's edge (the relaxed box)"), X < BoxEdgeX - 100.0);
			Next(Phase == 2 ? 10 : 20); return false;
		}
		// ---- (2) a class pillbug on SCR_438, layer on
		if (Phase == 20)
		{
			Mode(2);
			Grey->GotoScreen(438, 165, 300);
			Next(21); return false;
		}
		if (Phase == 21)
		{
			if (Since < 2.0) return false;
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				const AActor* A = Pair.Value.Actor.Get();
				if (Pair.Value.Script == FName(TEXT("en-pill")) && A && !A->IsHidden() && A->FindComponentByClass<USkinnedMeshComponent>()) { Bug = Pair.Key; break; }
			}
			if (!Test->TestTrue(TEXT("a pillbug drawn by its creature body"), Bug > 1)) return true;
			FDinkScriptInstance Caller;
			D->Execute(Caller, FDinkStoryLine::Parse(FString::Printf(TEXT(">> freeze %d"), Bug), {TEXT("cmd")})); // it stands still for the blows
			const USkinnedMeshComponent* Skin = D->FindSprite(Bug)->Actor->FindComponentByClass<USkinnedMeshComponent>();
			Body = UDinkGameplay::DrawnBodyBox(*Skin);
			const FVector World = Skin->Bounds.BoxExtent * 2.0;
			Test->AddInfo(FString::Printf(TEXT("pillbug body: own box %.0f x %.0f x %.0f cm, world bounds %.0f x %.0f x %.0f cm"),
				Body.Extent.X * 2, Body.Extent.Y * 2, Body.Extent.Z * 2, World.X, World.Y, World.Z));
			Test->TestTrue(TEXT("the pillbug's own box is pillbug-sized (under 3 m long)"), FMath::Max(Body.Extent.X, Body.Extent.Y) * 2 < 300.0);
			Next(22); return false;
		}
		if (Phase == 22 || Phase == 23)
		{
			Hits(1); // the part Hits (off by default): Dink's blow lands at drawn contact
			// Dink faces the bug's centre from the -X side of its box, his capsule's front Gap cm from it.
			const double Gap = Phase == 22 ? 15.0 : 150.0;
			const FVector Axis = Body.Frame.GetRotation().GetAxisX();
			const FVector Away = -Axis.GetSafeNormal2D();
			const double Half = FMath::Abs(Body.Extent.X);
			const FVector At2 = Body.Frame.GetLocation() + Away * (Half + H->GetSimpleCollisionRadius() + Gap);
			H->SetActorLocation(FVector(At2.X, At2.Y, H->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
			H->SetActorRotation(FRotator(0, (-Away).Rotation().Yaw, 0));
			D->GetDink().Dir = FMath::Abs(Away.X) > FMath::Abs(Away.Y) ? (Away.X > 0 ? 4 : 6) : (Away.Y > 0 ? 8 : 2);
			const int32 Before = G->Events.Num();
			G->RunThroughTagList(1);
			bool bHit = false;
			const FString Prefix = FString::Printf(TEXT("hit %d by 1"), Bug);
			for (int32 I = Before; I < G->Events.Num(); ++I) bHit |= G->Events[I].StartsWith(Prefix);
			if (Phase == 22) Test->TestTrue(TEXT("layer on: the fist at drawn contact hits the pillbug"), bHit);
			else Test->TestFalse(TEXT("layer on: from 1.5 m in front of its body the fist misses"), bHit);
			if (Phase == 22) { Next(23); return false; }
			Next(24); return false;
		}
		// ---- (3) the default parts: Hits off, Bodies on. Dink walks into the pillbug from 1.5 m: its body box stops him, and from
		// there the 1997 fist box reaches it (the body never keeps him out of the 1997 reach), and the blow equals the 1997 box test.
		if (Phase == 24)
		{
			Hits(-1);
			const FVector Axis = Body.Frame.GetRotation().GetAxisX();
			const FVector Away = -Axis.GetSafeNormal2D();
			const double Half = FMath::Abs(Body.Extent.X);
			const FVector Far = Body.Frame.GetLocation() + Away * (Half + H->GetSimpleCollisionRadius() + 150.0);
			H->SetActorLocation(FVector(Far.X, Far.Y, H->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
			H->SetActorRotation(FRotator(0, (-Away).Rotation().Yaw, 0));
			FHitResult Block;
			const FVector Centre = Body.Frame.GetLocation();
			H->SetActorLocation(FVector(Centre.X, Centre.Y, H->GetActorLocation().Z), true, &Block);
			Test->TestTrue(TEXT("Bodies on: walking at the pillbug, its body box stops Dink"), Block.bBlockingHit);
			Test->TestTrue(TEXT("Bodies on: Dink stands outside the pillbug's drawn body"),
				FVector::Dist2D(H->GetActorLocation(), Centre) > Half + H->GetSimpleCollisionRadius() - 10.0);
			Test->AddInfo(FString::Printf(TEXT("stopped %.0f cm from the pillbug's centre (own half length %.0f cm)"), FVector::Dist2D(H->GetActorLocation(), Centre), Half));
			BodyAway = Away;
			Next(25); return false;
		}
		if (Phase == 25)
		{
			if (Since < 0.5) return false; // Dink's 1997 pixel follows the pawn on the next ticks
			FDinkSprite& Me = D->GetDink();
			Me.Dir = FMath::Abs(BodyAway.X) > FMath::Abs(BodyAway.Y) ? (BodyAway.X > 0 ? 4 : 6) : (BodyAway.Y > 0 ? 8 : 2);
			const FDinkSprite* BugSprite = D->FindSprite(Bug);
			const bool bLegacy = BugSprite && G->LegacyHitBoxContains(*BugSprite, FMath::RoundToInt32(Me.X), FMath::RoundToInt32(Me.Y), Me.Dir, Me.GetProp(TEXT("range")));
			const int32 Before = G->Events.Num();
			G->RunThroughTagList(1);
			bool bHit = false;
			const FString Prefix = FString::Printf(TEXT("hit %d by 1"), Bug);
			for (int32 I = Before; I < G->Events.Num(); ++I) bHit |= G->Events[I].StartsWith(Prefix);
			Test->TestEqual(TEXT("Hits off: the blow is the 1997 box test"), bHit, bLegacy);
			Test->TestTrue(TEXT("Hits off, Bodies on: stopped by the body, the 1997 fist box reaches the pillbug"), bHit);
			return true;
		}
		return true;
	}
	FAutomationTestBase* Test;
	double Began = 0, At = 0;
	int32 Phase = 0, Bug = 0;
	FVector Start = FVector::ZeroVector;
	FDinkDrawnBody Body;
	FVector BodyAway = FVector::ZeroVector;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPhysicalPlayRealScreensTest, "Dink.PhysicalPlay.RealScreens", DINK_TEST_FLAGS)
bool FDinkPhysicalPlayRealScreensTest::RunTest(const FString&)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!TestNotNull(TEXT("real map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	AddCommand(new FStartPIECommand(false)); AddCommand(new FDinkPhysicalPlayWorldPIE(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
