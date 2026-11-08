#include "DinkSaveGame.h"
#include "DinkCoreModule.h"
#include "DinkFactSubsystem.h"
#include "DinkInventoryComponent.h"
#include "DinkStatsComponent.h"
#include "DinkWorldStateSubsystem.h"
#include "Kismet/GameplayStatics.h"

UDinkSaveGame::UDinkSaveGame()
{
	if (!HasAnyFlags(RF_ClassDefaultObject | RF_ArchetypeObject))
	{
		SaveVersion = CurrentVersion;
	}
}

void UDinkSaveGame::CaptureFrom(const FDinkSaveContext& Context)
{
	SaveVersion = CurrentVersion;
	SavedAtUtc = FDateTime::UtcNow();

	if (Context.Facts)
	{
		Facts = Context.Facts->GetAllFacts();
	}
	if (Context.WorldState)
	{
		Overrides = Context.WorldState->ExportOverrides();
		ScreenExitTimes = Context.WorldState->ExportScreenExitTimes();
		GameTimeMs = Context.WorldState->GetGameTimeMs();
	}
	if (Context.PlayerStats)
	{
		PlayerStats = Context.PlayerStats->Stats;
	}
	if (Context.PlayerInventory)
	{
		Inventory = Context.PlayerInventory->GetState();
	}
}

bool UDinkSaveGame::ApplyTo(const FDinkSaveContext& Context) const
{
	if (SaveVersion != CurrentVersion)
	{
		UE_LOG(LogDink, Error, TEXT("UDinkSaveGame::ApplyTo: save is version %d, expected %d; migrate first"), SaveVersion, CurrentVersion);
		return false;
	}
	if (Context.Facts)
	{
		Context.Facts->RestoreFacts(Facts);
	}
	if (Context.WorldState)
	{
		Context.WorldState->ImportState(Overrides, ScreenExitTimes, GameTimeMs);
	}
	if (Context.PlayerStats)
	{
		Context.PlayerStats->SetStats(PlayerStats);
	}
	if (Context.PlayerInventory)
	{
		Context.PlayerInventory->SetState(Inventory);
	}
	return true;
}

bool UDinkSaveGame::MigrateToCurrentVersion(TArray<FString>* OutLog)
{
	if (SaveVersion < 0 || SaveVersion > CurrentVersion)
	{
		const FString Message = FString::Printf(TEXT("cannot migrate save version %d (this build understands 0..%d)"), SaveVersion, CurrentVersion);
		UE_LOG(LogDink, Error, TEXT("UDinkSaveGame: %s"), *Message);
		if (OutLog)
		{
			OutLog->Add(Message);
		}
		return false;
	}

	while (SaveVersion < CurrentVersion)
	{
		const int32 From = SaveVersion;
		switch (From)
		{
		case 0: MigrateV0ToV1(); break;
		case 1: MigrateV1ToV2(); break;
		default:
			checkf(false, TEXT("UDinkSaveGame: no migration step from version %d"), From);
			return false;
		}
		SaveVersion = From + 1;
		const FString Message = FString::Printf(TEXT("migrated save v%d -> v%d"), From, SaveVersion);
		UE_LOG(LogDink, Log, TEXT("UDinkSaveGame: %s"), *Message);
		if (OutLog)
		{
			OutLog->Add(Message);
		}
	}
	return true;
}

void UDinkSaveGame::MigrateV0ToV1()
{
	TMap<FName, int32> Renamed;
	Renamed.Reserve(Facts.Num());
	for (const TPair<FName, int32>& Pair : Facts)
	{
		const FName Name = DinkFacts::NormalizeName(Pair.Key);
		if (!Name.IsNone())
		{
			Renamed.Add(Name, Pair.Value);
		}
	}
	Facts = MoveTemp(Renamed);
}

void UDinkSaveGame::MigrateV1ToV2()
{
	// Version 1 had no SubsystemState. A v1 file deserialises with the map empty, which is exactly
	// "no module state": the narrative layer then starts with no running scripts, as the original
	// does after loading a save.
	SubsystemState.Reset();
}

bool UDinkSaveGame::SaveToBytes(UDinkSaveGame* Save, TArray<uint8>& OutBytes)
{
	OutBytes.Reset();
	return Save && UGameplayStatics::SaveGameToMemory(Save, OutBytes);
}

UDinkSaveGame* UDinkSaveGame::LoadFromBytes(const TArray<uint8>& Bytes, TArray<FString>* OutLog)
{
	UDinkSaveGame* Save = Cast<UDinkSaveGame>(UGameplayStatics::LoadGameFromMemory(Bytes));
	if (!Save)
	{
		if (OutLog)
		{
			OutLog->Add(TEXT("bytes are not a UDinkSaveGame"));
		}
		return nullptr;
	}
	if (!Save->MigrateToCurrentVersion(OutLog))
	{
		return nullptr;
	}
	Save->Inventory.Sanitize();
	return Save;
}
