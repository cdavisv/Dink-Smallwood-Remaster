#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DinkInventoryComponent.generated.h"

/**
 * Inventory contents: 16 item slots and 8 magic slots (dink.cpp lines 18-19; the save's
 * g_itemData[17] / g_MagicData[9], 1-based in the original), plus the armed item and spell.
 *
 * Slots hold item IDs: the original item script name (item-fst, item-sw1, item-fb, ...), which
 * is the identity add_item()/add_magic() use. They will map 1:1 to PrimaryAssetIds of the
 * future UDinkItemDefinition / UDinkMagicDefinition data assets. NAME_None is an empty slot.
 *
 * Slot indices are 0-based here. The original's &cur_weapon / &cur_magic are 1-based
 * (slot + 1); convert at the scripting boundary.
 */
USTRUCT(BlueprintType)
struct DINKCORE_API FDinkInventoryState
{
	GENERATED_BODY()

	static constexpr int32 NumItemSlots = 16;
	static constexpr int32 NumMagicSlots = 8;

	FDinkInventoryState();

	/** Always NumItemSlots entries; NAME_None = empty. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Inventory")
	TArray<FName> Items;

	/** Always NumMagicSlots entries; NAME_None = empty. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Inventory")
	TArray<FName> Magic;

	/** Armed item (weapon) slot, INDEX_NONE if none. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Inventory")
	int32 ArmedItemSlot = INDEX_NONE;

	/** Armed spell slot, INDEX_NONE if none. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, SaveGame, Category = "Dink|Inventory")
	int32 ArmedMagicSlot = INDEX_NONE;

	/**
	 * Repairs a state read from a save or from data: resizes the arrays to the slot counts
	 * (dropping extra entries) and disarms slots that are out of range or empty.
	 * Returns true if anything had to change.
	 */
	bool Sanitize();

	bool operator==(const FDinkInventoryState& Other) const
	{
		return Items == Other.Items && Magic == Other.Magic && ArmedItemSlot == Other.ArmedItemSlot && ArmedMagicSlot == Other.ArmedMagicSlot;
	}
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDinkInventoryChangedSignature, UDinkInventoryComponent*, Component);
DECLARE_MULTICAST_DELEGATE_OneParam(FDinkInventoryChangedNative, UDinkInventoryComponent*);

/**
 * The player's items and spells. Adding goes to the first empty slot and fails when full;
 * duplicates are allowed (the original counts them with count_item). Removing the armed slot
 * disarms it. Arming an empty slot fails. Running the item's arm/disarm behaviour is the job of
 * the item definition (later), not of this component.
 */
UCLASS(ClassGroup = (Dink), meta = (BlueprintSpawnableComponent))
class DINKCORE_API UDinkInventoryComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UDinkInventoryComponent();

	// ---- Items ----

	/** Puts ItemId in the first empty item slot; returns the slot or INDEX_NONE if full / invalid. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Inventory")
	int32 AddItem(FName ItemId);

	/** Empties Slot; returns false if it was already empty or out of range. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Inventory")
	bool RemoveItemAt(int32 Slot);

	/** Removes the first slot holding ItemId (kill_this_item); returns false if none. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Inventory")
	bool RemoveItem(FName ItemId);

	UFUNCTION(BlueprintPure, Category = "Dink|Inventory")
	int32 CountItem(FName ItemId) const;

	UFUNCTION(BlueprintPure, Category = "Dink|Inventory")
	FName GetItemAt(int32 Slot) const;

	UFUNCTION(BlueprintPure, Category = "Dink|Inventory")
	int32 NumFreeItemSlots() const;

	// ---- Magic ----

	UFUNCTION(BlueprintCallable, Category = "Dink|Inventory")
	int32 AddMagic(FName SpellId);

	UFUNCTION(BlueprintCallable, Category = "Dink|Inventory")
	bool RemoveMagicAt(int32 Slot);

	UFUNCTION(BlueprintCallable, Category = "Dink|Inventory")
	bool RemoveMagic(FName SpellId);

	UFUNCTION(BlueprintPure, Category = "Dink|Inventory")
	int32 CountMagic(FName SpellId) const;

	UFUNCTION(BlueprintPure, Category = "Dink|Inventory")
	FName GetMagicAt(int32 Slot) const;

	UFUNCTION(BlueprintPure, Category = "Dink|Inventory")
	int32 NumFreeMagicSlots() const;

	// ---- Arming ----

	/** Arms the item in Slot (replacing any armed item). False if the slot is empty or invalid. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Inventory")
	bool ArmItem(int32 Slot);

	UFUNCTION(BlueprintCallable, Category = "Dink|Inventory")
	void DisarmItem();

	UFUNCTION(BlueprintCallable, Category = "Dink|Inventory")
	bool ArmMagic(int32 Slot);

	UFUNCTION(BlueprintCallable, Category = "Dink|Inventory")
	void DisarmMagic();

	/** Armed item ID, or None. */
	UFUNCTION(BlueprintPure, Category = "Dink|Inventory")
	FName GetArmedItem() const;

	/** Armed spell ID, or None. */
	UFUNCTION(BlueprintPure, Category = "Dink|Inventory")
	FName GetArmedMagic() const;

	UFUNCTION(BlueprintPure, Category = "Dink|Inventory")
	int32 GetArmedItemSlot() const { return State.ArmedItemSlot; }

	UFUNCTION(BlueprintPure, Category = "Dink|Inventory")
	int32 GetArmedMagicSlot() const { return State.ArmedMagicSlot; }

	// ---- Save ----

	const FDinkInventoryState& GetState() const { return State; }

	/** Replaces the whole state (load path); the state is sanitised first. */
	void SetState(const FDinkInventoryState& NewState);

	UPROPERTY(BlueprintAssignable, Category = "Dink|Inventory")
	FDinkInventoryChangedSignature OnInventoryChanged;

	FDinkInventoryChangedNative OnInventoryChangedNative;

private:
	static int32 AddTo(TArray<FName>& Slots, FName Id);
	static int32 Count(const TArray<FName>& Slots, FName Id);
	static int32 NumFree(const TArray<FName>& Slots);
	void NotifyChanged();

	UPROPERTY(EditAnywhere, SaveGame, Category = "Dink|Inventory")
	FDinkInventoryState State;
};
