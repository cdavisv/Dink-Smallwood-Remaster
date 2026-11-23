// Dink.PhysicalPlay.RealScreens: the physical play layer ON in the real generated world (PIE), so CI covers play mode
// (review of PR #160). (1) SCR_215: walking west along y 78 at the pine S215_P05, whose 1997 box (right edge x 409) is relaxed,
// Dink stops at the box with the layer off and walks past its edge with it on. (2) SCR_438: a class pillbug (creature body,
// skinned) is hit by Dink's fist at drawn contact and not from 1.5 m in front of its body with the part Hits on, and its own box is
// the size of a pillbug, not of its world bounds. (3) With the default parts (Hits off, Bodies on), Dink walking into the pillbug
// is stopped by its body (part Bodies), and from there his blow lands at drawn contact (Hits on: owner decision 19 Nov 2026).
// (4) A class-bound creature (review of PR #160, finding 1): its player-only body box is made and stops Dink, and from there its
// touch reaches him (finding 4) and its drawn reach meets him (part CreatureReach).
#include "DinkTestHelpers.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkCreatureSubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "DinkPlayerBlockers.h"
#include "UObject/UObjectIterator.h"
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
		if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.CreatureClassArt"))) V->Set(1, ECVF_SetByConsole);
	}
	bool Update() override
	{
		if (!Began) Began = FPlatformTime::Seconds();
		if (FPlatformTime::Seconds() - Began > 420) { Test->AddError(TEXT("physical play PIE timeout")); return true; }
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
			// review finding 2: the 1997 hardness the simulation reads (get_hard) follows the same rule: the box only at the drawn trunk
			const int32 InBox = G->GetHard(215, 400 + 20, 78), AtTrunk = G->GetHard(215, 358 + 20, 78);
			Test->AddInfo(FString::Printf(TEXT("pine S215_P05, layer %s: get_hard in the box %d, at the trunk %d"), Phase == 2 ? TEXT("off") : TEXT("on"), InBox, AtTrunk));
			if (Phase == 2) Test->TestTrue(TEXT("layer off: get_hard reads the 1997 box"), InBox == 105 && AtTrunk == 105);
			else Test->TestTrue(TEXT("layer on: get_hard reads the box only at the drawn trunk"), InBox == 0 && AtTrunk == 105);
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
			// what its hits and touches use: its authored body boxes when it has them, else its skinned body
			if (!UDinkGameplay::CreatureDrawnBody(*D->FindSprite(Bug)->Actor, Body)) Body = UDinkGameplay::DrawnBodyBox(*Skin);
			const FVector World = Skin->Bounds.BoxExtent * 2.0;
			Test->AddInfo(FString::Printf(TEXT("pillbug body: own box %.0f x %.0f x %.0f cm, world bounds %.0f x %.0f x %.0f cm"),
				Body.Extent.X * 2, Body.Extent.Y * 2, Body.Extent.Z * 2, World.X, World.Y, World.Z));
			Test->TestTrue(TEXT("the pillbug's own box is pillbug-sized (under 3 m long)"), FMath::Max(Body.Extent.X, Body.Extent.Y) * 2 < 300.0);
			Next(22); return false;
		}
		if (Phase == 22 || Phase == 23)
		{
			Hits(1); // the part Hits: Dink's blow lands at drawn contact
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
		// ---- (3) the default parts: Hits on, Bodies on. Dink walks into the pillbug from 1.5 m: its body stops him, and from there his
		// fist at drawn contact lands (the body never keeps him out of his own reach).
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
			const int32 Before = G->Events.Num();
			G->RunThroughTagList(1);
			bool bHit = false;
			const FString Prefix = FString::Printf(TEXT("hit %d by 1"), Bug);
			for (int32 I = Before; I < G->Events.Num(); ++I) bHit |= G->Events[I].StartsWith(Prefix);
			Test->TestTrue(TEXT("default parts (Hits, Bodies on): stopped by the body, the fist at drawn contact lands"), bHit);
			Next(26); return false;
		}
		// ---- (4) a class-bound creature: a pillbug on SCR_278 (foes/pill, no creatures.json placement row)
		if (Phase == 26)
		{
			Grey->GotoScreen(278, 300, 200);
			Next(27); return false;
		}
		if (Phase == 27)
		{
			if (Since < 2.0) return false;
			ClassBug = 0;
			for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
			{
				const AActor* A = Pair.Value.Actor.Get();
				if (Pair.Key != 1 && Pair.Value.bActive && Pair.Value.Screen == 278 && A && !A->IsHidden() && !A->ActorHasTag(TEXT("DinkCreature")) &&
					UDinkGameplay::FindCreatureBodyBlocker(A)) { ClassBug = Pair.Key; break; }
			}
			if (!ClassBug)
			{
				for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
				{
					const AActor* A = Pair.Value.Actor.Get();
					if (Pair.Value.Screen != 278 || !A) continue;
					Test->AddInfo(FString::Printf(TEXT("SCR_278 sprite %d %s active %d hidden %d brain %d nohit %d creature-tag %d class-body %d blocker %d"), Pair.Key,
						*Pair.Value.Script.ToString(), Pair.Value.bActive, A->IsHidden(), Pair.Value.GetProp(TEXT("brain")), Pair.Value.GetProp(TEXT("nohit")),
						A->ActorHasTag(TEXT("DinkCreature")), UDinkCreatureSubsystem::FindClassBody(A) != nullptr, UDinkGameplay::FindCreatureBodyBlocker(A) != nullptr));
				}
			}
			if (!Test->TestTrue(TEXT("finding 1: a class-bound creature on SCR_278 carries a body box"), ClassBug > 1)) return true;
			// it stands still for the test with the brains off (not sp_freeze: a frozen body carries no blocker, review of 22 Nov finding 7)
			G->bBrainsEnabled = false;
			FDinkDrawnBody Own;
			UDinkGameplay::CreatureDrawnBody(*D->FindSprite(ClassBug)->Actor, Own);
			const FVector Away = -Own.Frame.GetRotation().GetAxisX().GetSafeNormal2D();
			const FVector Far = Own.Frame.GetLocation() + Away * (FMath::Abs(Own.Extent.X) + H->GetSimpleCollisionRadius() + 150.0);
			H->SetActorLocation(FVector(Far.X, Far.Y, H->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
			FHitResult Block;
			H->SetActorLocation(FVector(Own.Frame.GetLocation().X, Own.Frame.GetLocation().Y, H->GetActorLocation().Z), true, &Block);
			Test->TestTrue(TEXT("finding 1: walking at the class-bound creature, its body box stops Dink"), Block.bBlockingHit);
			Test->AddInfo(FString::Printf(TEXT("class creature sprite %d (%s): stopped %.0f cm from its centre (own half length %.0f cm)"), ClassBug,
				*D->FindSprite(ClassBug)->Script.ToString(), FVector::Dist2D(H->GetActorLocation(), Own.Frame.GetLocation()), FMath::Abs(Own.Extent.X)));
			Next(28); return false;
		}
		if (Phase == 28)
		{
			if (Since < 0.5) return false;
			FDinkSprite* Bug2 = D->FindSprite(ClassBug);
			if (!Bug2) return true;
			Test->TestTrue(TEXT("finding 4: stopped by its body box, Dink is within its touch (bitten by walking up)"), G->DrawnInteractionLands(ClassBug, false));
			// review of 22 Nov 2026, finding 6: DrawnInteractionLands is also true where the layer does not decide; the bite itself, by
			// the touch list, with the layer deciding (its drawn reach is known only to the layer)
			Test->TestTrue(TEXT("finding 6: the layer decides this creature (it has a drawn reach)"), G->CreatureReachRadiusCm(*Bug2) > 0.0);
			if (Bug2->GetProp(TEXT("touch_damage")) > 0)
			{
				Story->GetFacts()->SetFact(TEXT("life"), 99);
				D->GetDink().bNoTouch = false;
				const FString Bite = FString::Printf(TEXT("touch damage %d from %d"), Bug2->GetProp(TEXT("touch_damage")), ClassBug);
				const auto Bites = [&]() { int32 N = 0; for (const FString& E : G->Events) N += E.Contains(Bite) ? 1 : 0; return N; };
				const int32 Before = Bites();
				G->RunThroughTouchDamageList(1);
				const bool bBitten = Bites() > Before;
				Test->TestTrue(TEXT("finding 6: the touch list bites Dink at the body box"), bBitten);
			}
			else
			{
				Test->AddInfo(TEXT("the SCR_278 creature has no touch damage: the bite is not checked"));
			}
			int32 Dir = 0;
			const FVector To = H->GetActorLocation() - Bug2->Actor->GetActorLocation();
			Dir = FMath::Abs(To.X) > FMath::Abs(To.Y) ? (To.X > 0 ? 6 : 4) : (To.Y > 0 ? 2 : 8);
			const FDinkSprite& Me2 = D->GetDink();
			int32 PixelDir = 0;
			G->GetDistanceAndDir(ClassBug, 1, PixelDir);
			Test->TestTrue(TEXT("part CreatureReach: against its body Dink is in its drawn reach"), G->CreatureReachesDink(*Bug2, PixelDir));
			Test->AddInfo(FString::Printf(TEXT("Dink at (%.0f,%.0f), creature at (%.0f,%.0f), its facing to Dink %d (world %d)"), Me2.X, Me2.Y, Bug2->X, Bug2->Y, PixelDir, Dir));
			G->bBrainsEnabled = true;
			// review of 22 Nov 2026, finding 5: relaxed_hardboxes.json against the world as built. On the 16 screens with the most relaxed
			// boxes, every relaxed placement still has a player-only blocker (PR #129's hull of its drawn mesh) over its drawn footprint:
			// a box without one would let Dink walk through the drawn thing.
			TArray<TPair<int32, int32>> ByCount;
			for (const auto& R : G->GetPhysicalPlaySettings().Relaxed) ByCount.Add(TPair<int32, int32>(R.Key, R.Value.Num()));
			ByCount.Sort([](const TPair<int32, int32>& A, const TPair<int32, int32>& B) { return A.Value != B.Value ? A.Value > B.Value : A.Key < B.Key; });
			for (int32 I = 0; I < FMath::Min(16, ByCount.Num()); ++I) RelaxedScreens.Add(ByCount[I].Key);
			Next(30); return false;
		}
		if (Phase >= 30 && Phase < 30 + 2 * RelaxedScreens.Num())
		{
			const int32 Screen = RelaxedScreens[(Phase - 30) / 2];
			if ((Phase - 30) % 2 == 0) { Grey->GotoScreen(Screen, 300, 200); Next(Phase + 1); return false; }
			if (Since < 1.5) return false;
			const ADinkScreenVolume* V = Grey->FindScreen(Screen);
			if (D->GetDink().Screen != Screen)
			{
				// (SCR_134: relaxed boxes in the data, but the screen is not reached by a teleport into the generated world)
				Test->AddInfo(FString::Printf(TEXT("finding 5: SCR_%d not entered (Dink on %d, volume %s): skipped"), Screen, D->GetDink().Screen, V ? TEXT("yes") : TEXT("no")));
				Next(Phase + 1); return false;
			}
			TArray<FBox> Hulls;
			for (TObjectIterator<UPrimitiveComponent> It; It; ++It)
			{
				if (It->GetWorld() == W && It->IsRegistered() && It->ComponentHasTag(DinkPlayerBlockers::Tag) && It->IsCollisionEnabled()) Hulls.Add(It->Bounds.GetBox());
			}
			int32 Checked = 0, Missing = 0, Unsafe = 0, Walls = 0;
			FString Which;
			for (const int32 N : G->GetPhysicalPlaySettings().Relaxed.FindRef(Screen))
			{
				const FIntRect* Foot = G->GetPhysicalPlaySettings().Feet.Find(Screen * 1000 + N);
				if (!Foot || !V) continue;
				// A71: a trimmed wall has no hull; its box stays inside its drawn strip (measured on the wall mesh at entry)
				if (G->GetPhysicalPlaySettings().Trimmed.Contains(Screen * 1000 + N))
				{
					++Walls;
					if (G->PlayHardness(Screen, (Foot->Min.X + Foot->Max.X) / 2, (Foot->Min.Y + Foot->Max.Y) / 2, 100 + N) != 100 + N) { ++Unsafe; Which += FString::Printf(TEXT(" wall P%02d open at its strip"), N); }
					continue;
				}
				FBox Plan(ForceInit);
				for (const FIntPoint C : { Foot->Min, Foot->Max, FIntPoint(Foot->Min.X, Foot->Max.Y), FIntPoint(Foot->Max.X, Foot->Min.Y) }) Plan += V->MapPixelToWorld(C.X, C.Y);
				Plan = Plan.ExpandBy(FVector(15.0, 15.0, 1e6));
				++Checked;
				bool bHull = false;
				for (const FBox& Hb : Hulls) bHull |= Hb.Intersect(Plan);
				// beside the drawn footprint (inside the 1997 box of a relaxed placement): open where a blocker stands for the drawn
				// thing, the 1997 box where none does (the layer keeps it: nothing would stop Dink there)
				const int32 Code = 100 + N, AtSide = G->PlayHardness(Screen, Foot->Max.X + 2, (Foot->Min.Y + Foot->Max.Y) / 2, Code);
				if (!bHull)
				{
					++Missing; Which += FString::Printf(TEXT(" P%02d"), N);
					if (AtSide != Code) ++Unsafe;
				}
			}
			Test->AddInfo(FString::Printf(TEXT("finding 5: SCR_%d: %d relaxed placements, %d without a blocker over their footprint%s (kept as 1997 boxes); %d trimmed walls"), Screen, Checked, Missing, *Which, Walls));
			Test->TestEqual(FString::Printf(TEXT("finding 5: SCR_%d: a relaxed placement without its drawn blocker keeps its 1997 box"), Screen), Unsafe, 0);
			Next(Phase + 1); return false;
		}
		return true;
	}
	FAutomationTestBase* Test;
	double Began = 0, At = 0;
	int32 Phase = 0, Bug = 0, ClassBug = 0;
	TArray<int32> RelaxedScreens;
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
	// class-bound creatures are drawn by their animated bodies headless too (as in play), so part (4) has one to meet
	if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.CreatureClassArt"))) V->Set(2, ECVF_SetByConsole);
	AddCommand(new FStartPIECommand(false)); AddCommand(new FDinkPhysicalPlayWorldPIE(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
