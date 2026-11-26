// A62 (25 Nov 2026): the play camera in Dink's house (SCR_001). (1) Measurement: what the spring arm's own probe meets at six spots.
// (2) Dink with his back to a wall (a 20 cm BlockAll wall 40 cm behind him on the camera's side, as the house's east wall in the
// rendered frames): the camera does not sit in his hair: it clears InteriorMinimumClearArm along a steeper pitch / higher pivot, or
// his body is not drawn for that view; the player's control rotation is untouched; without the wall the rule lets go.
#include "DinkTestHelpers.h"
#include "DinkInteriorCameraComponent.h"
#include "DinkStorySubsystem.h"
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
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"

namespace
{
struct FHouseSpot { int32 Screen; float X, Y, Pitch, Yaw; const TCHAR* Name; };
const FHouseSpot GHouseSpots[] = {
	{1, 300, 260, -15, 270, TEXT("SCR_1 mid-room, facing north")},
	{1, 300, 260, -15, 90, TEXT("SCR_1 mid-room, facing south")},
	{1, 300, 260, -15, 0, TEXT("SCR_1 mid-room, facing east")},
	{1, 500, 110, -15, 315, TEXT("SCR_1 NE corner by the sack")},
	{1, 440, 150, -15, 270, TEXT("SCR_1 440,150")},
	{1, 314, 161, -15, 180, TEXT("SCR_1 new-game spot")},
};

class FHouseCameraMeasure : public IAutomationLatentCommand
{
public:
	explicit FHouseCameraMeasure(FAutomationTestBase* T) : Test(T) {}
	bool Update() override
	{
		if (!Start) Start = FPlatformTime::Seconds();
		if (FPlatformTime::Seconds() - Start > 180) { Test->AddError(TEXT("house camera timed out")); return true; }
		UWorld* W = GEditor ? GEditor->PlayWorld.Get() : nullptr;
		APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
		ADinkGreyboxCharacter* H = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
		UDinkStorySubsystem* S = W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		if (!H || !S || S->bNewGamePending) return false;
		if (Stage == 0) { S->SkipDialogue(); if (PC->IsMoveInputIgnored()) return false; }
		UDinkGreyboxSubsystem* G = W->GetSubsystem<UDinkGreyboxSubsystem>();
		const double Now = W->GetTimeSeconds();
		const int32 Index = Stage / 2;
		if (Index >= UE_ARRAY_COUNT(GHouseSpots)) return BackToTheWall(W, PC, H, G);
		const FHouseSpot& Spot = GHouseSpots[Index];
		ADinkScreenVolume* Screen = G->FindScreen(Spot.Screen);
		if (!Test->TestNotNull(TEXT("screen"), Screen)) return true;
		if (Stage % 2 == 0)
		{
			H->GetCharacterMovement()->StopMovementImmediately();
			H->SetActorLocation(Screen->MapPixelToWorld(Spot.X, Spot.Y) + FVector(0, 0, 98), false, nullptr, ETeleportType::TeleportPhysics);
			G->RefreshCurrentScreen();
			PC->SetControlRotation(FRotator(Spot.Pitch, Spot.Yaw, 0));
			At = Now; ++Stage; return false;
		}
		if (Now - At < 1.5) return false;
		USpringArmComponent* Arm = H->CameraBoom;
		const FVector Base = Arm->GetComponentLocation();
		const FVector Pivot = Base + Arm->TargetOffset;
		const FVector Wanted = Arm->GetUnfixedCameraPosition();
		const FVector Eye = H->FollowCamera->GetComponentLocation();
		const FVector Head = H->GetMesh()->GetBoneIndex(TEXT("head")) != INDEX_NONE ? H->GetMesh()->GetSocketLocation(TEXT("head")) : H->GetActorLocation() + FVector(0, 0, 70);
		Test->AddInfo(FString::Printf(TEXT("%s: target arm %.0f, base %s, pivot %s (pivot - base %s), eye %s, eye to pivot %.1f, eye to head %.1f, eye to capsule axis %.1f, wanted eye %s, control %s"),
			Spot.Name, Arm->TargetArmLength, *Base.ToCompactString(), *Pivot.ToCompactString(), *(Pivot - Base).ToCompactString(), *Eye.ToCompactString(),
			FVector::Dist(Eye, Pivot), FVector::Dist(Eye, Head), FVector::Dist2D(Eye, H->GetActorLocation()), *Wanted.ToCompactString(), *PC->GetControlRotation().ToCompactString()));
		// the arm's own probe line, as USpringArmComponent::UpdateDesiredArmLocation sweeps it (from the arm origin to the desired eye)
		TArray<FHitResult> Hits;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkHouseCameraMeasure), false, H);
		W->SweepMultiByChannel(Hits, Pivot, Wanted, FQuat::Identity, Arm->ProbeChannel, FCollisionShape::MakeSphere(Arm->ProbeSize), Params);
		for (const FHitResult& Hit : Hits)
		{
			Test->AddInfo(FString::Printf(TEXT("  probe hit %s / %s (%s) at %.1f cm, normal %s, start-penetrating %d, blocking %d"),
				Hit.GetActor() ? *Hit.GetActor()->GetName() : TEXT("-"), Hit.GetComponent() ? *Hit.GetComponent()->GetName() : TEXT("-"),
				Hit.GetComponent() ? *Hit.GetComponent()->GetCollisionProfileName().ToString() : TEXT("-"), Hit.Distance, *Hit.ImpactNormal.ToCompactString(),
				Hit.bStartPenetrating ? 1 : 0, Hit.bBlockingHit ? 1 : 0));
		}
		if (!Hits.Num()) Test->AddInfo(TEXT("  probe: no hit"));
		++Stage; return false;
	}
private:
	bool BackToTheWall(UWorld* W, APlayerController* PC, ADinkGreyboxCharacter* H, UDinkGreyboxSubsystem* G)
	{
		UDinkInteriorCameraComponent* C = H->FindComponentByClass<UDinkInteriorCameraComponent>();
		if (!Test->TestNotNull(TEXT("interior camera"), C)) return true;
		const double Now = W->GetTimeSeconds();
		const FRotator Control(-15.0, 270.0, 0.0);
		auto Eye = [&]() { return H->FollowCamera->GetComponentLocation(); };
		auto Head = [&]() { return H->GetMesh()->GetBoneIndex(TEXT("head")) != INDEX_NONE ? H->GetMesh()->GetSocketLocation(TEXT("head")) : H->GetActorLocation() + FVector(0, 0, 70); };
		switch (WallStage)
		{
		case 0:
		{
			ADinkScreenVolume* Screen = G->FindScreen(1);
			H->GetCharacterMovement()->StopMovementImmediately();
			H->SetActorLocation(Screen->MapPixelToWorld(300, 260) + FVector(0, 0, 98), false, nullptr, ETeleportType::TeleportPhysics);
			G->RefreshCurrentScreen();
			PC->SetControlRotation(Control);
			// the wall on the camera's side, 40 cm from Dink's axis, across his back
			const FVector Back = -FRotator(0.0, Control.Yaw, 0.0).Vector();
			FActorSpawnParameters SP; SP.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Wall = W->SpawnActor<AStaticMeshActor>(H->GetActorLocation() + Back * 50.0 + FVector(0, 0, 50), FRotator(0.0, Control.Yaw, 0.0), SP);
			UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
			if (!Test->TestNotNull(TEXT("wall"), Wall.Get()) || !Test->TestNotNull(TEXT("cube mesh"), Cube)) return true;
			Wall->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
			Wall->GetStaticMeshComponent()->SetStaticMesh(Cube);
			Wall->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
			Wall->SetActorScale3D(FVector(0.2, 4.0, 4.0)); // 20 cm thick along the camera's line, 4 m wide and high
			At = Now; WallStage = 1; return false;
		}
		case 1:
		{
			if (Now - At < 1.5) return false;
			const double EyeToHead = FVector::Dist(Eye(), Head());
			Test->AddInfo(FString::Printf(TEXT("back to the wall: clear arm %.1f, pitch %.1f below the player's, pivot lift %.1f, eye %.1f cm from the head, body hidden %d, eye to pivot %.1f"),
				C->InteriorClearArm, C->InteriorClearPitch, C->InteriorClearLift, EyeToHead, C->bInteriorHeroHidden ? 1 : 0,
				FVector::Dist(Eye(), H->CameraBoom->GetComponentLocation() + H->CameraBoom->TargetOffset)));
			{
				// the probe along a few pitches and lifts, as the rule sweeps them (diagnosis)
				USpringArmComponent* Arm = H->CameraBoom;
				FCollisionQueryParams P(SCENE_QUERY_STAT(DinkHouseWallDiag), false, H);
				for (const double Lift : {0.0, 40.0})
					for (const double Pitch : {-15.0, -30.0, -45.0, -60.0})
					{
						const FVector Pivot = Arm->GetComponentLocation() + Arm->TargetOffset - FVector(0, 0, C->InteriorClearLift) + FVector(0, 0, Lift);
						const FRotator R(Pitch, Control.Yaw, 0.0);
						const FVector Desired = Pivot - R.Vector() * Arm->TargetArmLength + R.RotateVector(Arm->SocketOffset);
						FHitResult Hit;
						const bool bHit = W->SweepSingleByChannel(Hit, Pivot, Desired, FQuat::Identity, Arm->ProbeChannel, FCollisionShape::MakeSphere(Arm->ProbeSize), P);
						Test->AddInfo(FString::Printf(TEXT("  lift %.0f pitch %.0f: %s %.1f cm (%s, start %d), socket %s"), Lift, Pitch, bHit ? TEXT("hit") : TEXT("clear"),
							bHit ? Hit.Time * FVector::Dist(Pivot, Desired) : FVector::Dist(Pivot, Desired), Hit.GetActor() ? *Hit.GetActor()->GetName() : TEXT("-"),
							Hit.bStartPenetrating ? 1 : 0, *Arm->SocketOffset.ToCompactString()));
					}
			}
			Test->TestTrue(TEXT("the camera is not inside Dink's head: it clears his head or his body is not drawn for this view"),
				EyeToHead >= C->InteriorHeadClearance - 1.0 || C->bInteriorHeroHidden);
			Test->TestTrue(TEXT("the rule looks down more steeply or from higher (it does not just close in)"), C->InteriorClearPitch < -1.f || C->InteriorClearLift > 1.f);
			Test->TestTrue(TEXT("the pitch stays within the bound"), FRotator::NormalizeAxis(PC->GetControlRotation().Pitch) + C->InteriorClearPitch >= C->InteriorMaximumClearPitch - 0.5);
			Test->TestTrue(TEXT("the player's control rotation is unchanged"), PC->GetControlRotation().GetNormalized().Equals(Control.GetNormalized(), 0.01));
			Wall->Destroy();
			At = Now; WallStage = 2; return false;
		}
		case 2:
		{
			if (Now - At < 1.5) return false;
			Test->AddInfo(FString::Printf(TEXT("wall gone: pitch %.2f, lift %.2f, arm %.1f, hidden %d, eye %.1f from the head"), C->InteriorClearPitch, C->InteriorClearLift,
				H->CameraBoom->TargetArmLength, C->bInteriorHeroHidden ? 1 : 0, FVector::Dist(Eye(), Head())));
			Test->TestEqual(TEXT("without the wall the rule lets go (pitch)"), C->InteriorClearPitch, 0.f, 0.5f);
			Test->TestEqual(TEXT("(lift)"), C->InteriorClearLift, 0.f, 0.5f);
			Test->TestFalse(TEXT("(body drawn)"), C->bInteriorHeroHidden);
			Test->TestTrue(TEXT("(the arm follows the player's rotation again)"), H->CameraBoom->bUsePawnControlRotation);
			Test->TestTrue(TEXT("the camera stands back the interior arm again"), FVector::Dist(Eye(), Head()) > 180.0);
			return true;
		}
		default: return true;
		}
	}
	FAutomationTestBase* Test;
	double Start = 0, At = 0;
	int32 Stage = 0, WallStage = 0;
	TWeakObjectPtr<AStaticMeshActor> Wall;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHouseCameraMeasureTest, "Dink.Art.InteriorCamera.BackToTheWall", DINK_TEST_FLAGS)
bool FDinkHouseCameraMeasureTest::RunTest(const FString&)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!TestNotNull(TEXT("actual world loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	AddCommand(new FStartPIECommand(false)); AddCommand(new FHouseCameraMeasure(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
