#include "DinkExpanded.h"
#include "DinkExpandedWorldSubsystem.h"

#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS

#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkGameplay.h"
#include "DinkInkStory.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"
#include "AssetCompilingManager.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/AutomationTest.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

/**
 * Dink.Expanded.Murkwood.Play: the slice in PIE on the generated 1997 world with the switch on. Dink walks into the join's 1997 side on
 * SCR_301, arrives on The Thin Place (its base script runs), walks west into Burt's Camp across the seamless pack edge, back east and out
 * through the pack-side trigger to the return point on SCR_301. The switch state of the process is restored at the end.
 */
namespace
{
	struct FSavedSwitch
	{
		bool bWas = false;
		FDinkExpandedRegistry Registry;
		FString Story;
		TArray<FString> Extra;
	};

	class FDinkExpandedPlayCheck : public IAutomationLatentCommand
	{
	public:
		FDinkExpandedPlayCheck(FAutomationTestBase* InTest, TSharedRef<FSavedSwitch> InSaved) : Test(InTest), Saved(InSaved), Began(FPlatformTime::Seconds()) {}

		virtual bool Update() override
		{
			if (FPlatformTime::Seconds() - Began > 150.0)
			{
				Test->AddError(FString::Printf(TEXT("Murkwood play check timed out at stage %d"), Stage));
				return Finish();
			}
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
			ACharacter* Hero = PC ? Cast<ACharacter>(PC->GetPawn()) : nullptr;
			if (!Hero)
			{
				return false;
			}
			UDinkStorySubsystem* Story = World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>();
			UDinkFactSubsystem* Facts = World->GetGameInstance()->GetSubsystem<UDinkFactSubsystem>();
			UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
			UDinkExpandedWorldSubsystem* Packs = World->GetSubsystem<UDinkExpandedWorldSubsystem>();
			if (!Story || !Facts || !Greybox || Story->bNewGamePending)
			{
				return false;
			}
			Story->SkipDialogue();
			const ADinkScreenVolume* Screen = Greybox->FindScreenAt(Hero->GetActorLocation());
			const int32 Here = Screen ? Screen->ScreenNumber : 0;
			auto WalkTo = [&](const FVector& Target)
			{
				Hero->AddMovementInput((Target - Hero->GetActorLocation()).GetSafeNormal2D());
			};
			if (Stage == 0)
			{
				if (World->GetTimeSeconds() < 2.0 || PC->IsMoveInputIgnored())
				{
					return false;
				}
				if (!Test->TestNotNull(TEXT("pack world subsystem exists with the switch on"), Packs))
				{
					return Finish();
				}
				In = Packs->FindJoin(TEXT("murkwood_thin_place"), TEXT("in"));
				Out = Packs->FindJoin(TEXT("murkwood_thin_place"), TEXT("out"));
				if (!Test->TestNotNull(TEXT("join on SCR_301 built"), In) || !Test->TestNotNull(TEXT("pack-side trigger built"), Out) ||
					!Test->TestNotNull(TEXT("pack screen 332 registered"), Greybox->FindScreen(332)) || !Test->TestNotNull(TEXT("SCR_301 in this world"), Greybox->FindScreen(301)))
				{
					return Finish();
				}
				double MinX = TNumericLimits<double>::Max();
				for (TActorIterator<ADinkScreenVolume> It(World); It; ++It)
				{
					if (!DinkExpanded::GetRegistry().IsPackScreen(It->ScreenNumber))
					{
						MinX = FMath::Min(MinX, FMath::Min(It->Corners.NW.X, It->Corners.SW.X));
					}
				}
				Test->TestTrue(TEXT("the pack sheet stands at least 1.5 km beyond the loaded 1997 world"), Greybox->FindScreen(332)->Corners.NE.X <= MinX - 1499.0);
				// Start a few metres east of the trigger on SCR_301 (map 330, 345) and walk into it.
				const FVector Start = Greybox->FindScreen(301)->MapPixelToWorld(340.f, 345.f) + FVector(0, 0, 98.0);
				Hero->SetActorLocation(Start, false, nullptr, ETeleportType::TeleportPhysics);
				Hero->GetCharacterMovement()->StopMovementImmediately();
				Greybox->RefreshCurrentScreen();
				Wait = World->GetTimeSeconds() + 1.0;
				Stage = 1;
				return false;
			}
			if (Stage == 1)
			{
				// SCR_301's 1997 pillbugs lock the screen (en-pill1: screenlock(1)); a locked fight closes the join like every other exit.
				if (Greybox->GetLockedScreen() == 301)
				{
					if (World->GetTimeSeconds() < Wait)
					{
						return false;
					}
					if (!bSawLocked)
					{
						bSawLocked = true;
						Test->TestFalse(TEXT("the join is closed while SCR_301's fight is locked"), In->Warp->bTriggerEnabled);
					}
					// The fight won (the pillbugs' die runs screenlock(0)).
					Story->GetGameplay()->SetScreenLock(false);
					Wait = World->GetTimeSeconds() + 0.5;
					return false;
				}
				if (World->GetTimeSeconds() < Wait)
				{
					return false;
				}
				if (Here != 332)
				{
					WalkTo(In->Warp->GetComponentLocation());
					return false;
				}
				Test->TestTrue(TEXT("arrived at The Thin Place's arrival point"), FVector::Dist2D(Hero->GetActorLocation(), In->Warp->DestLocation) < 300.0);
				Wait = World->GetTimeSeconds() + 1.5;
				Stage = 2;
				return false;
			}
			if (Stage == 2)
			{
				if (World->GetTimeSeconds() < Wait || Facts->GetFact(TEXT("x3_thin")) == 0)
				{
					return false;
				}
				Test->TestEqual(TEXT("the Thin Place's base script ran: &x3_thin = 1"), Facts->GetFact(TEXT("x3_thin")), 1);
				Test->TestEqual(TEXT("&player_map is the pack screen"), Facts->GetFact(TEXT("player_map")), 332);
				Stage = 3;
				return false;
			}
			if (Stage == 3)
			{
				// West across the seamless edge into Burt's Camp (both pack screens on one sheet).
				if (Here != 331)
				{
					if (!PC->IsMoveInputIgnored() && !Story->GetDirector()->GetDink().bFrozen)
					{
						WalkTo(Greybox->FindScreen(331)->MapPixelToWorld(450.f, 200.f));
					}
					return false;
				}
				// The story notices the new screen on its next screen check (every 0.25 s).
				if (Facts->GetFact(TEXT("player_map")) != 331)
				{
					return false;
				}
				Test->TestEqual(TEXT("walked into Burt's Camp: &player_map 331"), Facts->GetFact(TEXT("player_map")), 331);
				Stage = 4;
				return false;
			}
			if (Stage == 4)
			{
				// Back east, through The Thin Place and out by the pack-side trigger.
				if (Here != 301)
				{
					WalkTo(Here == 331 ? Greybox->FindScreen(332)->MapPixelToWorld(300.f, 200.f) : Out->Warp->GetComponentLocation());
					return false;
				}
				if (Facts->GetFact(TEXT("player_map")) != 301)
				{
					return false;
				}
				Test->TestTrue(TEXT("back at the 1997 return point on SCR_301"), FVector::Dist2D(Hero->GetActorLocation(), Out->Warp->DestLocation) < 300.0);
				Test->TestEqual(TEXT("&player_map 301"), Facts->GetFact(TEXT("player_map")), 301);
				return Finish();
			}
			return false;
		}

	private:
		bool Finish()
		{
			DinkExpanded::ApplySwitch(false);
			if (Saved->bWas)
			{
				DinkExpanded::ApplyForTest(Saved->Registry, Saved->Story, Saved->Extra.Num() ? Saved->Extra.Last() : FString());
			}
			FDinkInkStory::StoryDataOverrideDir() = Saved->Story;
			FDinkGameplayData::ExtraDataDirs() = Saved->Extra;
			return true;
		}

		FAutomationTestBase* Test;
		TSharedRef<FSavedSwitch> Saved;
		double Began;
		double Wait = 0.0;
		int32 Stage = 0;
		bool bSawLocked = false;
		ADinkExpandedJoinActor* In = nullptr;
		ADinkExpandedJoinActor* Out = nullptr;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkExpandedPlayTest, "Dink.Expanded.Murkwood.Play",
	EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter)
bool FDinkExpandedPlayTest::RunTest(const FString& Parameters)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!IFileManager::Get().FileExists(*File))
	{
		AddWarning(TEXT("skipped: generated world map absent"));
		return true;
	}
	TSharedRef<FSavedSwitch> Saved = MakeShared<FSavedSwitch>();
	Saved->bWas = DinkExpanded::IsEnabled();
	Saved->Registry = DinkExpanded::GetRegistry();
	Saved->Story = FDinkInkStory::StoryDataOverrideDir();
	Saved->Extra = FDinkGameplayData::ExtraDataDirs();
	// The switch on with the built packs, before PIE creates its game instance and world (as -DinkExpanded=1 does at start).
	FString Error;
	if (!TestTrue(TEXT("packs on"), DinkExpanded::ApplySwitch(true, {}, &Error)) || !DinkExpanded::GetRegistry().FindPack(TEXT("murkwood")))
	{
		AddError(FString::Printf(TEXT("Murkwood pack not available: %s"), *Error));
		DinkExpanded::ApplySwitch(false);
		if (Saved->bWas)
		{
			DinkExpanded::ApplyForTest(Saved->Registry, Saved->Story, Saved->Extra.Num() ? Saved->Extra.Last() : FString());
		}
		return false;
	}
	if (!TestNotNull(TEXT("generated world loads"), UEditorLoadingAndSavingUtils::LoadMap(File)))
	{
		return false;
	}
	FAssetCompilingManager::Get().FinishAllCompilation();
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FDinkExpandedPlayCheck(this, Saved));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

#endif
