// The remaster's title screen (FDinkTitleScreen in DinkStorySubsystem.h): rules, camera and slots. Drawing is in
// DinkNarrativeOverlay.cpp (FTitlePainter), keys and mouse in DinkNarrativeInput.cpp.
//
// The 1997 title is start.c with the buttons start-1.c (new game: Dink at 334,161, fists armed), start-2.c (Continue: the
// ten `&savegameinfo` slots, load_game) and start-4.c (Quit: kill_game). The HD engine skips start.c in the base game
// (`if (&version > 108) if (is_base_game() == 1) kill_this_task()`) and shows its own main menu instead; this file is the
// remaster's equivalent of that menu. New Game leaves the existing newgame start (bNewGamePending, PollScreenChange) to
// run exactly as it did without a title, so the 1997 simulation and the probe traces do not change.

#include "DinkStorySubsystem.h"
#include "DinkAudioSubsystem.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkSaveGame.h"
#include "DinkSaveSubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "DinkLayout.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/App.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

DEFINE_LOG_CATEGORY_STATIC(LogDinkTitle, Log, All);

namespace
{
	TAutoConsoleVariable<int32> CVarTitleEnable(TEXT("dink.Title.Enable"), 1,
		TEXT("1: a real game shows the title screen when it starts (never under automation, the probe, capture scripts or -NoTitle). 0: start straight into a new game."));
	// Dink's house in Stonebrook (SCR_439: its door S439_P13 leads into SCR_001, where a new game starts), seen from the south.
	TAutoConsoleVariable<int32> CVarTitleScreen(TEXT("dink.Title.Screen"), 439,
		TEXT("Original screen the title camera looks at."));
	TAutoConsoleVariable<FString> CVarTitleShot(TEXT("dink.Title.Shot"), TEXT("320 220 2400 800 105 12 55"),
		TEXT("Title camera: mapX mapY distance_cm height_cm yaw_deg sway_deg hfov. The camera stands distance from the focus (map pixel on dink.Title.Screen, on the ground), height above it, at yaw (0 = east), and sways sway degrees either way."));

	constexpr int32 NumSlots = 10;
	/** A tool that carries the pawn further than this (dink.Goto) means a new game is wanted (old QA scripts know no title). */
	constexpr double ToolMoveCm = 300.0;

	FString SlotName(int32 Slot)
	{
		// Same names as the director's save_game / load_game (DinkDirector.cpp SaveSlotName).
		return FString::Printf(TEXT("dink_save%d"), Slot);
	}

	bool CommandLineAsksNoTitle()
	{
		const TCHAR* Cmd = FCommandLine::Get();
		// -DinkTitle shows it anyway (QA of the title itself in an -unattended private session).
		if (FParse::Param(Cmd, TEXT("DinkTitle")))
		{
			return false;
		}
		// QA launchers (Scripts/private_qa_session.py, run_capture.sh, run_packaged_tests.sh) pass -unattended and drive the
		// game with keys and console commands that expect it to start at once; a player's launch does not.
		if (FParse::Param(Cmd, TEXT("NoTitle")) || FParse::Param(Cmd, TEXT("DinkProbeHold")) || FApp::IsUnattended())
		{
			return true;
		}
		// Automation and capture runs drive the game from -ExecCmds and expect it to start at once.
		const FString Line(Cmd);
		return Line.Contains(TEXT("Automation RunTests"), ESearchCase::IgnoreCase) || Line.Contains(TEXT("dink.CaptureScript"), ESearchCase::IgnoreCase)
			|| Line.Contains(TEXT("RunTests"), ESearchCase::IgnoreCase);
	}

	FString PlayTime(int64 Ms)
	{
		const int64 Minutes = FMath::Max<int64>(0, Ms) / 60000;
		return FString::Printf(TEXT("%lld:%02lld"), Minutes / 60, Minutes % 60);
	}
}

bool UDinkStorySubsystem::ShouldShowTitle() const
{
	const UWorld* World = GetWorld();
	if (!World || !World->IsGameWorld() || GIsAutomationTesting || bInstantMode || IsRunningCommandlet() || CVarTitleEnable.GetValueOnGameThread() == 0)
	{
		return false;
	}
	return !CommandLineAsksNoTitle();
}

void UDinkStorySubsystem::DecideTitle()
{
	UWorld* World = GetWorld();
	APlayerController* PC = World && World->IsGameWorld() ? World->GetFirstPlayerController() : nullptr;
	if (!PC || !PC->GetPawn() || !World->HasBegunPlay())
	{
		return; // not yet: decide in the first tick that has a player
	}
	bTitleDecisionPending = false;
	if (ShouldShowTitle())
	{
		OpenTitle();
	}
}

void UDinkStorySubsystem::RefreshTitleSlots()
{
	TitleScreen.Slots.Reset();
	const UWorld* World = GetWorld();
	const UDinkGreyboxSubsystem* Greybox = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
	for (int32 Slot = 1; Slot <= NumSlots; ++Slot)
	{
		FDinkTitleSlot& Info = TitleScreen.Slots.AddDefaulted_GetRef();
		Info.Slot = Slot;
		if (!UGameplayStatics::DoesSaveGameExist(SlotName(Slot), 0))
		{
			continue;
		}
		const UDinkSaveGame* Save = Cast<UDinkSaveGame>(UGameplayStatics::LoadGameFromSlot(SlotName(Slot), 0));
		if (!Save)
		{
			continue; // unreadable: shown as empty, as the original's game_exist would not show it either
		}
		Info.bExists = true;
		auto Fact = [Save](const TCHAR* Name) { const int32* V = Save->Facts.Find(FName(Name)); return V ? *V : 0; };
		Info.Level = Fact(TEXT("level"));
		Info.Life = Fact(TEXT("life"));
		Info.LifeMax = Fact(TEXT("lifemax"));
		Info.Gold = Fact(TEXT("gold"));
		Info.PlayMs = Save->GameTimeMs;
		Info.SavedAtUtc = Save->SavedAtUtc;
		if (const ADinkScreenVolume* Screen = Greybox ? Greybox->FindScreen(Save->CurrentScreen) : nullptr)
		{
			Info.Area = !Screen->AreaName.IsEmpty() ? Screen->AreaName : Screen->RegionName;
		}
	}
}

bool UDinkStorySubsystem::OpenTitle()
{
	UWorld* World = GetWorld();
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!IsReady() || TitleScreen.bOpen)
	{
		return TitleScreen.bOpen;
	}
	CloseInventory(/*bSound*/ false);
	TitleScreen.bOpen = true;
	TitleScreen.OpenedAt = TitleScreen.PageChangedAt = FPlatformTime::Seconds();
	TitleScreen.ClosedAt = -1.0;
	TitleScreen.Page = EDinkTitlePage::Main;
	RefreshTitleSlots();
	TitleScreen.Selected = TitleScreen.AnySave() ? 1 : 0; // Continue when there is a save, else New Game
	bTitleMusicStarted = false;
	AddEvent(TEXT("title"), TEXT("open"));
	UE_LOG(LogDinkTitle, Display, TEXT("Title screen open (%d saved games)"), TitleScreen.Slots.FilterByPredicate([](const FDinkTitleSlot& S) { return S.bExists; }).Num());
	if (!Pawn)
	{
		return true; // no world (tests): the rules only
	}
	TitlePawnStart = Pawn->GetActorLocation();

	// Dink stands still and the camera looks at the countryside; the cursor is shown for the mouse.
	PC->SetIgnoreMoveInput(true);
	PC->SetIgnoreLookInput(true);
	bTitleSavedCursor = PC->bShowMouseCursor;
	PC->bShowMouseCursor = true;
	// Leave the launch-time permanent mouse capture (DefaultInput.ini: CapturePermanently, high-precision relative mouse),
	// or the OS cursor stays hidden and frozen and the rows cannot be pointed at.
	PC->SetInputMode(FInputModeGameAndUI().SetHideCursorDuringCapture(false).SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock));
	if (!TitleCamera.IsValid())
	{
		FActorSpawnParameters SP;
		SP.ObjectFlags |= RF_Transient;
		ACameraActor* Camera = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), FTransform::Identity, SP);
		if (Camera)
		{
			Camera->GetCameraComponent()->bConstrainAspectRatio = false;
			TitleCamera = Camera;
		}
	}
	TitleFocus = Pawn->GetActorLocation();
	const UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
	TArray<FString> Shot;
	CVarTitleShot.GetValueOnGameThread().ParseIntoArrayWS(Shot);
	if (const ADinkScreenVolume* Screen = Greybox ? Greybox->FindScreen(CVarTitleScreen.GetValueOnGameThread()) : nullptr; Screen && Shot.Num() >= 2)
	{
		TitleFocus = DinkLayout::MapPixelToUnreal(Screen->Corners, FCString::Atod(*Shot[0]), FCString::Atod(*Shot[1]));
		FHitResult Hit;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkTitleGround), false, Pawn);
		if (World->LineTraceSingleByChannel(Hit, TitleFocus + FVector(0, 0, 20000.0), TitleFocus - FVector(0, 0, 20000.0), ECC_Visibility, Params))
		{
			TitleFocus = Hit.ImpactPoint;
		}
	}
	if (ACameraActor* Camera = Cast<ACameraActor>(TitleCamera.Get()))
	{
		PlaceTitleCamera(0.0);
		PC->SetViewTarget(Camera);
	}
	return true;
}

void UDinkStorySubsystem::PlaceTitleCamera(double Seconds)
{
	ACameraActor* Camera = Cast<ACameraActor>(TitleCamera.Get());
	if (!Camera)
	{
		return;
	}
	TArray<FString> Shot;
	CVarTitleShot.GetValueOnGameThread().ParseIntoArrayWS(Shot);
	auto At = [&Shot](int32 I, double Default) { return Shot.IsValidIndex(I) ? FCString::Atod(*Shot[I]) : Default; };
	const double Distance = At(2, 2600.0), Height = At(3, 900.0), Yaw = At(4, 200.0), Sway = At(5, 14.0), Fov = At(6, 50.0);
	// A slow sway (90 s a cycle) rather than a full orbit, so the shot never turns to the world's edge.
	const double YawNow = Yaw + Sway * FMath::Sin(Seconds * 2.0 * PI / 90.0);
	const FVector Dir = FRotator(0.0, YawNow, 0.0).Vector();
	const FVector From = TitleFocus + Dir * Distance + FVector(0, 0, Height);
	const FVector To = TitleFocus + FVector(0, 0, 150.0);
	Camera->SetActorLocationAndRotation(From, (To - From).Rotation());
	Camera->GetCameraComponent()->SetFieldOfView(static_cast<float>(Fov));
}

void UDinkStorySubsystem::UpdateTitle(float DeltaSeconds)
{
	UWorld* World = GetWorld();
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!Pawn)
	{
		return;
	}
	const double Since = FPlatformTime::Seconds() - TitleScreen.OpenedAt;
	PlaceTitleCamera(Since);
	// The title's music (start.c: playmidi("1003.mid")), once the screen's own music has had its first say.
	if (!bTitleMusicStarted && Since > 0.4 && Director)
	{
		bTitleMusicStarted = true;
		Director->Audio.Cue(TEXT("music:1003.mid"));
	}
	// A tool teleported the player (dink.Goto typed in the console): it wants the game, not the title. Keep the order a game
	// without a title has: the newgame start and the start screen's entry first (on the start screen), then the tool's move.
	if (FVector::Dist(Pawn->GetActorLocation(), TitlePawnStart) > ToolMoveCm)
	{
		UE_LOG(LogDinkTitle, Display, TEXT("Title screen closed: the player was moved by a tool; starting a new game first"));
		const FVector Moved = Pawn->GetActorLocation();
		const FRotator MovedRot = Pawn->GetActorRotation();
		UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
		Pawn->SetActorLocation(TitlePawnStart, false, nullptr, ETeleportType::TeleportPhysics);
		if (Greybox)
		{
			Greybox->RefreshCurrentScreen();
		}
		CloseTitle(/*bNewGame*/ true);
		PollScreenChange(); // bNewGamePending: newgame.c, then the start screen's scripts, as on a title-less first frame
		Pawn->TeleportTo(Moved, MovedRot);
		if (Greybox)
		{
			Greybox->RefreshCurrentScreen(); // the next poll enters the tool's screen normally
		}
	}
}

void UDinkStorySubsystem::CloseTitle(bool bNewGame)
{
	if (!TitleScreen.bOpen)
	{
		return;
	}
	TitleScreen.bOpen = false;
	TitleScreen.ClosedAt = FPlatformTime::Seconds();
	UWorld* World = GetWorld();
	if (APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr)
	{
		PC->SetIgnoreMoveInput(false);
		PC->SetIgnoreLookInput(false);
		PC->bShowMouseCursor = bTitleSavedCursor;
		PC->SetInputMode(FInputModeGameOnly()); // the game's mouse look capture again
		if (APawn* Pawn = PC->GetPawn())
		{
			PC->SetViewTarget(Pawn);
		}
	}
	if (AActor* Camera = TitleCamera.Get())
	{
		Camera->Destroy();
	}
	TitleCamera.Reset();
	// The title's music gives way to the screen's (the audio subsystem plays a screen's music when it is entered).
	if (Director && bTitleMusicStarted)
	{
		Director->Audio.Cue(TEXT("music:stop"));
		if (UDinkAudioSubsystem* Audio = World ? World->GetSubsystem<UDinkAudioSubsystem>() : nullptr)
		{
			Audio->ReplayScreenMusic();
		}
	}
	AddEvent(TEXT("title"), bNewGame ? TEXT("new game") : TEXT("continue"));
}

void UDinkStorySubsystem::SetTitlePage(EDinkTitlePage Page)
{
	TitleScreen.Page = Page;
	TitleScreen.PageChangedAt = FPlatformTime::Seconds();
	TitleScreen.Selected = 0;
	if (Page == EDinkTitlePage::Continue)
	{
		RefreshTitleSlots();
		// Start on the newest save.
		FDateTime Newest = FDateTime::MinValue();
		for (int32 i = 0; i < TitleScreen.Slots.Num(); ++i)
		{
			if (TitleScreen.Slots[i].bExists && TitleScreen.Slots[i].SavedAtUtc > Newest)
			{
				Newest = TitleScreen.Slots[i].SavedAtUtc;
				TitleScreen.Selected = i;
			}
		}
	}
	else if (Page == EDinkTitlePage::Controls)
	{
		TitleScreen.Selected = 0; // the one "Back" row
	}
}

TArray<FString> UDinkStorySubsystem::GetTitleRows() const
{
	TArray<FString> Rows;
	switch (TitleScreen.Page)
	{
	case EDinkTitlePage::Main:
		Rows = { TEXT("New Game"), TEXT("Continue"), TEXT("Controls"), TEXT("Quit") };
		break;
	case EDinkTitlePage::Continue:
		for (const FDinkTitleSlot& S : TitleScreen.Slots)
		{
			if (!S.bExists)
			{
				Rows.Add(FString::Printf(TEXT("Slot %d - Empty"), S.Slot));
				continue;
			}
			// The 1997 slot line is "Slot N - H:MM - Level L" (savegameinfo); the area and the date are the remaster's.
			FString Line = FString::Printf(TEXT("Slot %d - %s - Level %d"), S.Slot, *PlayTime(S.PlayMs), S.Level);
			if (!S.Area.IsEmpty())
			{
				Line += TEXT(" - ") + S.Area;
			}
			Rows.Add(Line);
		}
		Rows.Add(TEXT("Back"));
		break;
	case EDinkTitlePage::Controls:
		Rows.Add(TEXT("Back"));
		break;
	}
	return Rows;
}

bool UDinkStorySubsystem::IsTitleRowEnabled(int32 Row) const
{
	switch (TitleScreen.Page)
	{
	case EDinkTitlePage::Main:
		return Row != 1 || TitleScreen.AnySave();
	case EDinkTitlePage::Continue:
		return !TitleScreen.Slots.IsValidIndex(Row) ? Row == TitleScreen.Slots.Num() : TitleScreen.Slots[Row].bExists;
	default:
		return Row == 0;
	}
}

void UDinkStorySubsystem::MoveTitleSelection(int32 Delta)
{
	const int32 Num = GetTitleRows().Num();
	if (!TitleScreen.bOpen || Num == 0 || Delta == 0)
	{
		return;
	}
	// Skip the rows that do nothing (Continue without a save, empty slots), wrapping like the original's menus.
	int32 Row = TitleScreen.Selected;
	for (int32 Tries = 0; Tries < Num; ++Tries)
	{
		Row = (Row + (Delta > 0 ? 1 : -1) + Num) % Num;
		if (IsTitleRowEnabled(Row))
		{
			break;
		}
	}
	if (Row != TitleScreen.Selected)
	{
		TitleScreen.Selected = Row;
		PlayInterfaceSound(11, 22050); // SELECT.WAV, the menus' move sound
	}
}

void UDinkStorySubsystem::HighlightTitleRow(int32 Row)
{
	if (TitleScreen.bOpen && Row != TitleScreen.Selected && GetTitleRows().IsValidIndex(Row) && IsTitleRowEnabled(Row))
	{
		TitleScreen.Selected = Row;
		PlayInterfaceSound(11, 22050);
	}
}

bool UDinkStorySubsystem::ChooseTitleRow(int32 Row)
{
	if (!TitleScreen.bOpen || !GetTitleRows().IsValidIndex(Row))
	{
		return false;
	}
	TitleScreen.Selected = Row;
	if (!IsTitleRowEnabled(Row))
	{
		PlayInterfaceSound(19, 22050); // NONO.WAV
		return false;
	}
	PlayInterfaceSound(17, 22050); // SEL1.WAV
	switch (TitleScreen.Page)
	{
	case EDinkTitlePage::Main:
		if (Row == 0)
		{
			// start-1.c: a new game. The existing newgame start runs at the first screen poll, as with no title.
			UE_LOG(LogDinkTitle, Display, TEXT("Title screen: New Game"));
			CloseTitle(/*bNewGame*/ true);
		}
		else if (Row == 1)
		{
			SetTitlePage(EDinkTitlePage::Continue);
		}
		else if (Row == 2)
		{
			SetTitlePage(EDinkTitlePage::Controls);
		}
		else
		{
			// start-4.c: kill_game.
			UE_LOG(LogDinkTitle, Display, TEXT("Title screen: Quit"));
			if (OnTitleQuit)
			{
				OnTitleQuit();
			}
			else if (UWorld* World = GetWorld(); World && !GIsAutomationTesting)
			{
				if (APlayerController* PC = World->GetFirstPlayerController())
				{
					PC->ConsoleCommand(TEXT("quit"));
				}
			}
		}
		return true;
	case EDinkTitlePage::Continue:
	{
		if (Row == TitleScreen.Slots.Num())
		{
			return TitleBack();
		}
		// start-2.c: load_game(&result). The load replaces the narrative state; the pending newgame start is cleared by
		// RestoreFromSave, as for any load.
		const int32 Slot = TitleScreen.Slots[Row].Slot;
		UWorld* World = GetWorld();
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
		UDinkSaveSubsystem* Saves = GI ? GI->GetSubsystem<UDinkSaveSubsystem>() : nullptr;
		if (!Saves || !PC || !PC->GetPawn())
		{
			return false;
		}
		UE_LOG(LogDinkTitle, Display, TEXT("Title screen: Continue from slot %d"), Slot);
		CloseTitle(/*bNewGame*/ false);
		if (!Saves->LoadFromSlot(SlotName(Slot), PC->GetPawn()))
		{
			UE_LOG(LogDinkTitle, Warning, TEXT("Slot %d did not load; back to the title"), Slot);
			OpenTitle();
			return false;
		}
		return true;
	}
	case EDinkTitlePage::Controls:
		return TitleBack();
	}
	return false;
}

bool UDinkStorySubsystem::TitleBack()
{
	if (!TitleScreen.bOpen || TitleScreen.Page == EDinkTitlePage::Main)
	{
		return false;
	}
	const EDinkTitlePage From = TitleScreen.Page;
	SetTitlePage(EDinkTitlePage::Main);
	TitleScreen.Selected = From == EDinkTitlePage::Continue ? 1 : 2;
	PlayInterfaceSound(17, 22050);
	return true;
}

static FAutoConsoleCommandWithWorldAndArgs GDinkTitleCommand(
	TEXT("dink.Title"), TEXT("dink.Title [0|1]: open the title screen (1, default) or close it into a new game (0)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
		UDinkStorySubsystem* Story = GI ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		if (!Story)
		{
			return;
		}
		if (Args.Num() > 0 && Args[0] == TEXT("0"))
		{
			if (Story->IsTitleOpen())
			{
				Story->ChooseTitleRow(0);
			}
		}
		else
		{
			Story->OpenTitle();
		}
	}));
