#include "DinkSaveSubsystem.h"
#include "DinkCoreModule.h"
#include "DinkFactSubsystem.h"
#include "DinkInventoryComponent.h"
#include "DinkStatsComponent.h"
#include "DinkWorldStateSubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"

FDinkSaveContext UDinkSaveSubsystem::MakeContext(AActor* Player) const
{
	FDinkSaveContext Context;
	if (const UGameInstance* GameInstance = GetGameInstance())
	{
		Context.Facts = GameInstance->GetSubsystem<UDinkFactSubsystem>();
		Context.WorldState = GameInstance->GetSubsystem<UDinkWorldStateSubsystem>();
	}
	if (Player)
	{
		Context.PlayerStats = Player->FindComponentByClass<UDinkStatsComponent>();
		Context.PlayerInventory = Player->FindComponentByClass<UDinkInventoryComponent>();
	}
	return Context;
}

UDinkSaveGame* UDinkSaveSubsystem::CaptureSnapshot(AActor* Player, int32 CurrentScreen)
{
	UDinkSaveGame* Save = NewObject<UDinkSaveGame>(this);
	Save->CaptureFrom(MakeContext(Player));
	Save->CurrentScreen = CurrentScreen;
	if (Player)
	{
		Save->PlayerTransform = Player->GetActorTransform();
	}
	OnSnapshotCaptured.Broadcast(Save);
	return Save;
}

bool UDinkSaveSubsystem::ApplySnapshot(UDinkSaveGame* Save, AActor* Player)
{
	if (!Save || !Save->ApplyTo(MakeContext(Player)))
	{
		return false;
	}
	if (Player)
	{
		Player->SetActorTransform(Save->PlayerTransform, /*bSweep*/ false, nullptr, ETeleportType::TeleportPhysics);
		// Restore the physical screen before narrative subscribers rebind to the snapshot.
		// Refresh only changes the cached volume/native audio notification, never exit timers or scripts.
		if (UWorld* World = Player->GetWorld())
			if (UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>()) Greybox->RefreshCurrentScreen();
	}
	OnSnapshotApplied.Broadcast(Save);
	return true;
}

bool UDinkSaveSubsystem::SaveToSlot(const FString& SlotName, AActor* Player, int32 CurrentScreen)
{
	UDinkSaveGame* Save = CaptureSnapshot(Player, CurrentScreen);
	TArray<uint8> Bytes;
	return UDinkSaveGame::SaveToBytes(Save, Bytes) && UGameplayStatics::SaveDataToSlot(Bytes, SlotName, 0);
}

UDinkSaveGame* UDinkSaveSubsystem::LoadFromSlot(const FString& SlotName, AActor* Player)
{
	TArray<uint8> Bytes;
	if (!UGameplayStatics::LoadDataFromSlot(Bytes, SlotName, 0))
	{
		UE_LOG(LogDink, Warning, TEXT("UDinkSaveSubsystem: no save in slot '%s'"), *SlotName);
		return nullptr;
	}
	TArray<FString> Log;
	UDinkSaveGame* Save = UDinkSaveGame::LoadFromBytes(Bytes, &Log);
	if (!Save || !ApplySnapshot(Save, Player))
	{
		UE_LOG(LogDink, Error, TEXT("UDinkSaveSubsystem: could not load slot '%s': %s"), *SlotName, *FString::Join(Log, TEXT("; ")));
		return nullptr;
	}
	return Save;
}
