// The inventory screen's rules (the original's item screen, process_item, dink.cpp:16409-16636). Drawing is in
// DinkNarrativeOverlay.cpp; the keys are in DinkNarrativeInput.cpp. Arming goes through UDinkGameplay::ArmItemSlot /
// ArmMagicSlot, the same calls as the console's dink.Arm / dink.ArmMagic, so the scripts see exactly the same thing.

#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkFactSubsystem.h"
#include "DinkInventoryComponent.h"
#include "Engine/World.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"

void UDinkStorySubsystem::PlayInterfaceSound(int32 Sound, int32 Speed)
{
	// SoundPlayEffect(n, speed, 0, 0, 0): a plain cue, as playsound(n, speed, 0, 0, 0) would log it.
	if (Director)
	{
		Director->Audio.Cue(FString::Printf(TEXT("sound:%d speed=%d random=0 sprite=0 repeat=0"), Sound, Speed));
	}
}

bool UDinkStorySubsystem::CanOpenInventory() const
{
	if (!IsReady() || !Gameplay || !Director || bNewGamePending || GetActiveMenu())
	{
		return false;
	}
	if (Gameplay->IsHardnessLoading() || Director->GetDink().bFrozen || Gameplay->IsBowActive() || Gameplay->GetAttackGate().IsLocked(NowMs))
	{
		return false;
	}
	const UDinkFactSubsystem* F = Facts.Get();
	return !F || F->GetFact(TEXT("life")) > 0;
}

bool UDinkStorySubsystem::OpenInventory()
{
	if (InventoryScreen.bOpen)
	{
		return true;
	}
	if (!CanOpenInventory())
	{
		return false;
	}
	InventoryScreen.bOpen = true;
	InventoryScreen.ChangedAt = FPlatformTime::Seconds();
	if (InventoryScreen.Cursor < 1)
	{
		InventoryScreen.Cursor = 1; // dink.cpp:16453
	}
	// The original's main loop does nothing but the item screen while it is open (dink.cpp:17361): no brains, no scripts,
	// no magic charge (5937). Advance() returns at once while it is open; in a game the world is paused too (pawn, camera).
	UWorld* World = GetWorld();
	if (World && World->IsGameWorld() && !World->IsPaused())
	{
		bInventoryPausedWorld = UGameplayStatics::SetGamePaused(World, true);
	}
	PlayInterfaceSound(18, 22050); // dink.cpp:14958
	AddEvent(TEXT("inventory"), TEXT("open"));
	OnInventoryToggled.Broadcast(true); // the recordings pause with the game (UDinkAudioSubsystem)
	return true;
}

void UDinkStorySubsystem::CloseInventory(bool bSound)
{
	if (!InventoryScreen.bOpen)
	{
		return;
	}
	InventoryScreen.bOpen = false;
	InventoryScreen.ChangedAt = FPlatformTime::Seconds();
	if (bInventoryPausedWorld)
	{
		bInventoryPausedWorld = false;
		if (UWorld* World = GetWorld())
		{
			UGameplayStatics::SetGamePaused(World, false);
		}
	}
	if (bSound)
	{
		PlayInterfaceSound(17, 22050); // dink.cpp:16632
	}
	AddEvent(TEXT("inventory"), TEXT("close"));
	OnInventoryToggled.Broadcast(false);
}

void UDinkStorySubsystem::MoveInventoryCursor(int32 DX, int32 DY)
{
	if (!InventoryScreen.bOpen || (DX == 0 && DY == 0))
	{
		return;
	}
	int32& Cur = InventoryScreen.Cursor;
	// One direction per press, in the original's order (right, left, down, up: an else-if chain).
	if (!InventoryScreen.bMagic)
	{
		const int32 Hor = Cur - ((Cur - 1) / 4) * 4; // 1..4
		const int32 Virt = (Cur - 1) / 4;            // 0..3
		if (DX > 0)
		{
			if (Hor < 4) ++Cur;
		}
		else if (DX < 0)
		{
			if (Hor > 1)
			{
				--Cur;
			}
			else
			{
				InventoryScreen.bMagic = true; // to the magic panel's right column, same row
				Cur = Virt * 2 + 2;
			}
		}
		else if (DY > 0)
		{
			if (Virt < 3) Cur += 4;
		}
		else if (Virt > 0)
		{
			Cur -= 4;
		}
	}
	else
	{
		const int32 Hor = Cur - ((Cur - 1) / 2) * 2; // 1..2
		const int32 Virt = (Cur - 1) / 2;            // 0..3
		if (DX > 0)
		{
			if (Hor < 2)
			{
				++Cur;
			}
			else
			{
				InventoryScreen.bMagic = false; // to the item panel's first column, same row
				Cur = Virt * 4 + 1;
			}
		}
		else if (DX < 0)
		{
			if (Hor > 1) --Cur;
		}
		else if (DY > 0)
		{
			if (Virt < 3) Cur += 2;
		}
		else if (Virt > 0)
		{
			Cur -= 2;
		}
	}
	PlayInterfaceSound(11, 22050);
}

bool UDinkStorySubsystem::ArmInventorySelection()
{
	if (!InventoryScreen.bOpen || !Gameplay)
	{
		return false;
	}
	const bool bArmed = InventoryScreen.bMagic ? Gameplay->ArmMagicSlot(InventoryScreen.Cursor) : Gameplay->ArmItemSlot(InventoryScreen.Cursor);
	if (bArmed)
	{
		PlayInterfaceSound(18, 42050); // dink.cpp:16479, 16553; an empty slot: "can't arm nothing", no sound
		AddEvent(TEXT("inventory"), FString::Printf(TEXT("arm %s %d"), InventoryScreen.bMagic ? TEXT("magic") : TEXT("item"), InventoryScreen.Cursor));
	}
	return bArmed;
}

bool UDinkStorySubsystem::QuickArmItemSlot(int32 Slot)
{
	if (!Gameplay || Slot < 1 || Slot > FDinkInventoryState::NumItemSlots || !(InventoryScreen.bOpen || CanOpenInventory()))
	{
		return false;
	}
	if (InventoryScreen.bOpen)
	{
		InventoryScreen.bMagic = false;
		InventoryScreen.Cursor = Slot;
		return ArmInventorySelection();
	}
	if (!Gameplay->ArmItemSlot(Slot))
	{
		return false;
	}
	PlayInterfaceSound(18, 42050);
	AddEvent(TEXT("inventory"), FString::Printf(TEXT("quick-arm item %d"), Slot));
	return true;
}
