#include "DinkInventoryComponent.h"

FDinkInventoryState::FDinkInventoryState()
{
	Items.Init(NAME_None, NumItemSlots);
	Magic.Init(NAME_None, NumMagicSlots);
}

bool FDinkInventoryState::Sanitize()
{
	bool bChanged = false;
	if (Items.Num() != NumItemSlots)
	{
		Items.SetNum(NumItemSlots);
		bChanged = true;
	}
	if (Magic.Num() != NumMagicSlots)
	{
		Magic.SetNum(NumMagicSlots);
		bChanged = true;
	}
	if (ArmedItemSlot != INDEX_NONE && (!Items.IsValidIndex(ArmedItemSlot) || Items[ArmedItemSlot].IsNone()))
	{
		ArmedItemSlot = INDEX_NONE;
		bChanged = true;
	}
	if (ArmedMagicSlot != INDEX_NONE && (!Magic.IsValidIndex(ArmedMagicSlot) || Magic[ArmedMagicSlot].IsNone()))
	{
		ArmedMagicSlot = INDEX_NONE;
		bChanged = true;
	}
	return bChanged;
}

UDinkInventoryComponent::UDinkInventoryComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

int32 UDinkInventoryComponent::AddTo(TArray<FName>& Slots, FName Id)
{
	if (Id.IsNone())
	{
		return INDEX_NONE;
	}
	for (int32 i = 0; i < Slots.Num(); ++i)
	{
		if (Slots[i].IsNone())
		{
			Slots[i] = Id;
			return i;
		}
	}
	return INDEX_NONE;
}

int32 UDinkInventoryComponent::Count(const TArray<FName>& Slots, FName Id)
{
	if (Id.IsNone())
	{
		return 0;
	}
	int32 N = 0;
	for (const FName& Slot : Slots)
	{
		N += (Slot == Id) ? 1 : 0;
	}
	return N;
}

int32 UDinkInventoryComponent::NumFree(const TArray<FName>& Slots)
{
	int32 N = 0;
	for (const FName& Slot : Slots)
	{
		N += Slot.IsNone() ? 1 : 0;
	}
	return N;
}

int32 UDinkInventoryComponent::AddItem(FName ItemId)
{
	const int32 Slot = AddTo(State.Items, ItemId);
	if (Slot != INDEX_NONE)
	{
		NotifyChanged();
	}
	return Slot;
}

bool UDinkInventoryComponent::RemoveItemAt(int32 Slot)
{
	if (!State.Items.IsValidIndex(Slot) || State.Items[Slot].IsNone())
	{
		return false;
	}
	State.Items[Slot] = NAME_None;
	if (State.ArmedItemSlot == Slot)
	{
		State.ArmedItemSlot = INDEX_NONE;
	}
	NotifyChanged();
	return true;
}

bool UDinkInventoryComponent::RemoveItem(FName ItemId)
{
	return !ItemId.IsNone() && RemoveItemAt(State.Items.IndexOfByKey(ItemId));
}

int32 UDinkInventoryComponent::CountItem(FName ItemId) const
{
	return Count(State.Items, ItemId);
}

FName UDinkInventoryComponent::GetItemAt(int32 Slot) const
{
	return State.Items.IsValidIndex(Slot) ? State.Items[Slot] : NAME_None;
}

int32 UDinkInventoryComponent::NumFreeItemSlots() const
{
	return NumFree(State.Items);
}

int32 UDinkInventoryComponent::AddMagic(FName SpellId)
{
	const int32 Slot = AddTo(State.Magic, SpellId);
	if (Slot != INDEX_NONE)
	{
		NotifyChanged();
	}
	return Slot;
}

bool UDinkInventoryComponent::RemoveMagicAt(int32 Slot)
{
	if (!State.Magic.IsValidIndex(Slot) || State.Magic[Slot].IsNone())
	{
		return false;
	}
	State.Magic[Slot] = NAME_None;
	if (State.ArmedMagicSlot == Slot)
	{
		State.ArmedMagicSlot = INDEX_NONE;
	}
	NotifyChanged();
	return true;
}

bool UDinkInventoryComponent::RemoveMagic(FName SpellId)
{
	return !SpellId.IsNone() && RemoveMagicAt(State.Magic.IndexOfByKey(SpellId));
}

int32 UDinkInventoryComponent::CountMagic(FName SpellId) const
{
	return Count(State.Magic, SpellId);
}

FName UDinkInventoryComponent::GetMagicAt(int32 Slot) const
{
	return State.Magic.IsValidIndex(Slot) ? State.Magic[Slot] : NAME_None;
}

int32 UDinkInventoryComponent::NumFreeMagicSlots() const
{
	return NumFree(State.Magic);
}

bool UDinkInventoryComponent::ArmItem(int32 Slot)
{
	if (!State.Items.IsValidIndex(Slot) || State.Items[Slot].IsNone())
	{
		return false;
	}
	if (State.ArmedItemSlot != Slot)
	{
		State.ArmedItemSlot = Slot;
		NotifyChanged();
	}
	return true;
}

void UDinkInventoryComponent::DisarmItem()
{
	if (State.ArmedItemSlot != INDEX_NONE)
	{
		State.ArmedItemSlot = INDEX_NONE;
		NotifyChanged();
	}
}

bool UDinkInventoryComponent::ArmMagic(int32 Slot)
{
	if (!State.Magic.IsValidIndex(Slot) || State.Magic[Slot].IsNone())
	{
		return false;
	}
	if (State.ArmedMagicSlot != Slot)
	{
		State.ArmedMagicSlot = Slot;
		NotifyChanged();
	}
	return true;
}

void UDinkInventoryComponent::DisarmMagic()
{
	if (State.ArmedMagicSlot != INDEX_NONE)
	{
		State.ArmedMagicSlot = INDEX_NONE;
		NotifyChanged();
	}
}

FName UDinkInventoryComponent::GetArmedItem() const
{
	return GetItemAt(State.ArmedItemSlot);
}

FName UDinkInventoryComponent::GetArmedMagic() const
{
	return GetMagicAt(State.ArmedMagicSlot);
}

void UDinkInventoryComponent::SetState(const FDinkInventoryState& NewState)
{
	State = NewState;
	State.Sanitize();
	NotifyChanged();
}

void UDinkInventoryComponent::NotifyChanged()
{
	OnInventoryChangedNative.Broadcast(this);
	OnInventoryChanged.Broadcast(this);
}
