#include "DinkTestHelpers.h"
#include "DinkInventoryComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkInventoryLimitsTest, "Dink.Core.Inventory.Limits", DINK_TEST_FLAGS)
bool FDinkInventoryLimitsTest::RunTest(const FString& Parameters)
{
	UDinkInventoryComponent* Inv = NewObject<UDinkInventoryComponent>(GetTransientPackage());
	TestEqual(TEXT("16 free item slots"), Inv->NumFreeItemSlots(), 16);
	TestEqual(TEXT("8 free magic slots"), Inv->NumFreeMagicSlots(), 8);

	TestEqual(TEXT("None is not an item"), Inv->AddItem(NAME_None), int32(INDEX_NONE));
	for (int32 i = 0; i < 16; ++i)
	{
		TestEqual(FString::Printf(TEXT("item %d goes to slot %d"), i, i), Inv->AddItem(i % 2 ? FName(TEXT("item-eli")) : FName(*FString::Printf(TEXT("item-%02d"), i))), i);
	}
	TestEqual(TEXT("17th item fails"), Inv->AddItem(TEXT("item-fst")), int32(INDEX_NONE));
	TestEqual(TEXT("full"), Inv->NumFreeItemSlots(), 0);
	TestEqual(TEXT("duplicates allowed and counted"), Inv->CountItem(TEXT("item-eli")), 8);

	for (int32 i = 0; i < 8; ++i)
	{
		TestEqual(FString::Printf(TEXT("spell %d"), i), Inv->AddMagic(FName(*FString::Printf(TEXT("item-m%d"), i))), i);
	}
	TestEqual(TEXT("9th spell fails"), Inv->AddMagic(TEXT("item-fb")), int32(INDEX_NONE));

	// Removing frees the slot, and the next add reuses the first free slot.
	TestTrue(TEXT("remove first elixir"), Inv->RemoveItem(TEXT("item-eli")));
	TestEqual(TEXT("first elixir was slot 1"), Inv->GetItemAt(1), FName());
	TestEqual(TEXT("seven elixirs left"), Inv->CountItem(TEXT("item-eli")), 7);
	TestEqual(TEXT("add reuses slot 1"), Inv->AddItem(TEXT("item-fst")), 1);
	TestFalse(TEXT("remove missing item"), Inv->RemoveItem(TEXT("item-nothere")));
	TestFalse(TEXT("remove out of range"), Inv->RemoveItemAt(16));
	TestFalse(TEXT("remove negative"), Inv->RemoveItemAt(-1));
	TestEqual(TEXT("out of range read"), Inv->GetItemAt(99), FName());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkInventoryArmTest, "Dink.Core.Inventory.ArmDisarm", DINK_TEST_FLAGS)
bool FDinkInventoryArmTest::RunTest(const FString& Parameters)
{
	UDinkInventoryComponent* Inv = NewObject<UDinkInventoryComponent>(GetTransientPackage());
	int32 Changes = 0;
	Inv->OnInventoryChangedNative.AddLambda([&Changes](UDinkInventoryComponent*) { ++Changes; });

	const int32 Fists = Inv->AddItem(TEXT("item-fst"));
	const int32 Sword = Inv->AddItem(TEXT("item-sw1"));
	const int32 Fireball = Inv->AddMagic(TEXT("item-fb"));
	TestEqual(TEXT("nothing armed"), Inv->GetArmedItem(), FName());

	TestFalse(TEXT("cannot arm an empty slot"), Inv->ArmItem(5));
	TestFalse(TEXT("cannot arm out of range"), Inv->ArmItem(16));
	TestTrue(TEXT("arm fists"), Inv->ArmItem(Fists));
	TestEqual(TEXT("fists armed"), Inv->GetArmedItem(), FName(TEXT("item-fst")));
	TestTrue(TEXT("arm sword replaces fists"), Inv->ArmItem(Sword));
	TestEqual(TEXT("one weapon at a time"), Inv->GetArmedItem(), FName(TEXT("item-sw1")));
	TestEqual(TEXT("armed slot"), Inv->GetArmedItemSlot(), Sword);

	TestFalse(TEXT("cannot arm an empty magic slot"), Inv->ArmMagic(3));
	TestTrue(TEXT("arm fireball"), Inv->ArmMagic(Fireball));
	TestEqual(TEXT("fireball armed"), Inv->GetArmedMagic(), FName(TEXT("item-fb")));

	Inv->DisarmItem();
	TestEqual(TEXT("disarmed item"), Inv->GetArmedItemSlot(), int32(INDEX_NONE));
	Inv->DisarmMagic();
	TestEqual(TEXT("disarmed magic"), Inv->GetArmedMagic(), FName());

	// Removing the armed item or spell disarms it.
	Inv->ArmItem(Sword);
	Inv->ArmMagic(Fireball);
	TestTrue(TEXT("remove sword"), Inv->RemoveItem(TEXT("item-sw1")));
	TestEqual(TEXT("removing armed item disarms"), Inv->GetArmedItemSlot(), int32(INDEX_NONE));
	TestTrue(TEXT("remove fireball"), Inv->RemoveMagicAt(Fireball));
	TestEqual(TEXT("removing armed spell disarms"), Inv->GetArmedMagicSlot(), int32(INDEX_NONE));

	// Removing a different slot keeps the armed one.
	Inv->ArmItem(Fists);
	Inv->AddItem(TEXT("item-eli"));
	Inv->RemoveItem(TEXT("item-eli"));
	TestEqual(TEXT("unrelated removal keeps weapon"), Inv->GetArmedItem(), FName(TEXT("item-fst")));
	TestTrue(TEXT("change events fired"), Changes > 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkInventorySanitizeTest, "Dink.Core.Inventory.SanitizeLoadedState", DINK_TEST_FLAGS)
bool FDinkInventorySanitizeTest::RunTest(const FString& Parameters)
{
	FDinkInventoryState Corrupt;
	Corrupt.Items.SetNum(20);
	Corrupt.Items[0] = TEXT("item-fst");
	Corrupt.Items[18] = TEXT("item-lost");
	Corrupt.Magic.SetNum(3);
	Corrupt.ArmedItemSlot = 18;
	Corrupt.ArmedMagicSlot = 2; // empty

	UDinkInventoryComponent* Inv = NewObject<UDinkInventoryComponent>(GetTransientPackage());
	Inv->SetState(Corrupt);
	TestEqual(TEXT("items trimmed to 16"), Inv->GetState().Items.Num(), 16);
	TestEqual(TEXT("magic padded to 8"), Inv->GetState().Magic.Num(), 8);
	TestEqual(TEXT("out-of-range armed item cleared"), Inv->GetArmedItemSlot(), int32(INDEX_NONE));
	TestEqual(TEXT("armed empty spell cleared"), Inv->GetArmedMagicSlot(), int32(INDEX_NONE));
	TestEqual(TEXT("valid content kept"), Inv->GetItemAt(0), FName(TEXT("item-fst")));

	FDinkInventoryState Clean;
	TestFalse(TEXT("default state needs no repair"), Clean.Sanitize());
	return true;
}
