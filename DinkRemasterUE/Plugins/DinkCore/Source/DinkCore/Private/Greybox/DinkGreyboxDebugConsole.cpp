// Small, observable controls for manual/desktop playtesting. Movement still comes from normal input.
#include "DinkCoreModule.h"
#include "DinkLayout.h"
#include "DinkOriginComponent.h"
#include "EngineUtils.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"

static FAutoConsoleCommandWithWorld GDinkPlayerCommand(
	TEXT("dink.Player"), TEXT("Print the player's world/map position, physical radius, and camera angles for a reproducible playtest."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		APawn* Pawn = PC ? PC->GetPawn() : nullptr;
		UDinkGreyboxSubsystem* Grey = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
		if (!Pawn || !Grey)
		{
			UE_LOG(LogDink, Display, TEXT("DINK PLAYER: no player"));
			return;
		}
		const FVector Position = Pawn->GetActorLocation();
		const ADinkScreenVolume* Screen = Grey->FindScreenAt(Position);
		double MapX = 0.0, MapY = 0.0;
		if (Screen)
		{
			DinkLayout::MetresToMapPixel(Screen->Corners, DinkLayout::UnrealToMetres(Position), MapX, MapY);
		}
		const UCapsuleComponent* Capsule = Pawn->FindComponentByClass<UCapsuleComponent>();
		const FRotator View = PC->GetControlRotation();
		UE_LOG(LogDink, Display, TEXT("DINK PLAYER: screen=%d map=%.3f,%.3f world=%.3f,%.3f,%.3f yaw=%.3f pitch=%.3f radius=%.1f move_ignored=%d"),
			Screen ? Screen->ScreenNumber : 0, MapX, MapY, Position.X, Position.Y, Position.Z,
			View.Yaw, FRotator::NormalizeAxis(View.Pitch), Capsule ? Capsule->GetScaledCapsuleRadius() : 0.f,
			PC->IsMoveInputIgnored() ? 1 : 0);
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkViewCommand(
	TEXT("dink.View"), TEXT("dink.View <yaw> <pitch>: set the normal third-person camera orientation in degrees; does not move the player."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		if (!PC || Args.Num() != 2 || !Args[0].IsNumeric() || !Args[1].IsNumeric())
		{
			UE_LOG(LogDink, Display, TEXT("usage: dink.View <yaw> <pitch>"));
			return;
		}
		PC->SetControlRotation(FRotator(FMath::Clamp(FCString::Atod(*Args[1]), -80.0, 60.0), FCString::Atod(*Args[0]), 0.0));
	}));


static FAutoConsoleCommandWithWorldAndArgs GDinkOriginCommand(
	TEXT("dink.Origin"), TEXT("dink.Origin <S001_P26>: print an original placement's live world/map position for interaction debugging."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		FDinkOriginId Id;
		if (!World || Args.Num() != 1 || !FDinkOriginId::Parse(Args[0], Id))
		{
			UE_LOG(LogDink, Display, TEXT("usage: dink.Origin <S001_P26>"));
			return;
		}
		UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			const UDinkOriginComponent* Origin = UDinkOriginComponent::FindOnActor(*It);
			if (!Origin || !(Origin->OriginId == Id)) continue;
			const FVector Position = It->GetActorLocation();
			const ADinkScreenVolume* Screen = Grey ? Grey->FindScreenAt(Position) : nullptr;
			double MapX = 0.0, MapY = 0.0;
			if (Screen) DinkLayout::MetresToMapPixel(Screen->Corners, DinkLayout::UnrealToMetres(Position), MapX, MapY);
			UE_LOG(LogDink, Display, TEXT("DINK ORIGIN: %s screen=%d map=%.3f,%.3f world=%.3f,%.3f,%.3f hidden=%d"),
				*Id.ToString(), Screen ? Screen->ScreenNumber : 0, MapX, MapY, Position.X, Position.Y, Position.Z, It->IsHidden() ? 1 : 0);
			return;
		}
		UE_LOG(LogDink, Display, TEXT("DINK ORIGIN: %s not found in this map"), *Id.ToString());
	}));
