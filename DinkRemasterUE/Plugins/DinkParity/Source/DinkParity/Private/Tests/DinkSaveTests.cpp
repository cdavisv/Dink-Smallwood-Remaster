#include "DinkTestHelpers.h"
#include "DinkSaveGame.h"
#include "DinkSaveSubsystem.h"
#include "DinkFactSubsystem.h"
#include "DinkInventoryComponent.h"
#include "DinkStatsComponent.h"
#include "DinkWorldStateSubsystem.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Components/SceneComponent.h"
#include "Kismet/GameplayStatics.h"

namespace
{
	struct FDinkTestGame
	{
		UDinkFactSubsystem* Facts = nullptr;
		UDinkWorldStateSubsystem* World = nullptr;
		UDinkStatsComponent* Stats = nullptr;
		UDinkInventoryComponent* Inventory = nullptr;

		FDinkSaveContext Context() const { return { Facts, World, Stats, Inventory }; }
	};

	FDinkTestGame MakeGame(FAutomationTestBase& Test)
	{
		FDinkTestGame Game;
		Game.Facts = DinkTest::MakeFacts(Test);
		Game.World = DinkTest::MakeWorldState();
		Game.Stats = NewObject<UDinkStatsComponent>(GetTransientPackage());
		Game.Inventory = NewObject<UDinkInventoryComponent>(GetTransientPackage());
		return Game;
	}

	/** Puts a game into a recognisable mid-story state. */
	void PlaySomeOfTheGame(FDinkTestGame& Game)
	{
		Game.Facts->SetFact(TEXT("story"), 5);
		Game.Facts->SetFact(TEXT("old_womans_duck"), 2);
		Game.Facts->SetFact(TEXT("s2-nad"), 1);
		Game.World->SetGameTimeMs(123456);
		Game.World->SetOverride(FDinkOriginId(37, 4), EDinkOverrideType::RemovedForever);
		Game.World->SetOverride(FDinkOriginId(412, 3), EDinkOverrideType::RemovedReturn3Min, TEXT("corpse"));
		Game.World->SetOverride(FDinkOriginId(412, 7), EDinkOverrideType::BackgroundHard);
		Game.World->NotifyScreenExited(412);
		Game.World->AdvanceGameTime(5000);

		FDinkStats Stats;
		Stats.Strength = 7;
		Stats.Defense = 4;
		Stats.Magic = 2;
		Stats.Life = 21;
		Stats.LifeMax = 25;
		Stats.Level = 6;
		Stats.Exp = 1234;
		Stats.Gold = 350;
		Stats.MagicLevel = 40;
		Stats.MagicCost = 100;
		Game.Stats->SetStats(Stats);

		Game.Inventory->AddItem(TEXT("item-fst"));
		Game.Inventory->AddItem(TEXT("item-eli"));
		Game.Inventory->AddItem(TEXT("item-sw1"));
		Game.Inventory->AddMagic(TEXT("item-fb"));
		Game.Inventory->ArmItem(2);
		Game.Inventory->ArmMagic(0);
	}

	void ExpectSameGame(FAutomationTestBase& Test, const FDinkTestGame& A, const FDinkTestGame& B)
	{
		Test.TestTrue(TEXT("facts equal"), A.Facts->GetAllFacts().OrderIndependentCompareEqual(B.Facts->GetAllFacts()));
		Test.TestEqual(TEXT("story"), B.Facts->GetFact(TEXT("story")), 5);
		Test.TestEqual(TEXT("s2-nad"), B.Facts->GetFact(TEXT("s2-nad")), 1);
		Test.TestTrue(TEXT("overrides equal"), A.World->ExportOverrides() == B.World->ExportOverrides());
		Test.TestEqual(TEXT("override count"), B.World->NumOverrides(), 3);
		Test.TestEqual(TEXT("game clock"), B.World->GetGameTimeMs(), int64(128456));
		Test.TestEqual(TEXT("screen exit time"), B.World->GetScreenExitTimeMs(412), int64(123456));
		Test.TestTrue(TEXT("stats equal"), A.Stats->Stats == B.Stats->Stats);
		Test.TestTrue(TEXT("inventory equal"), A.Inventory->GetState() == B.Inventory->GetState());
		Test.TestEqual(TEXT("armed sword"), B.Inventory->GetArmedItem(), FName(TEXT("item-sw1")));
		Test.TestEqual(TEXT("armed fireball"), B.Inventory->GetArmedMagic(), FName(TEXT("item-fb")));
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkSaveRoundTripTest, "Dink.Core.Save.RoundTrip", DINK_TEST_FLAGS)
bool FDinkSaveRoundTripTest::RunTest(const FString& Parameters)
{
	FDinkTestGame Original = MakeGame(*this);
	PlaySomeOfTheGame(Original);

	UDinkSaveGame* Save = NewObject<UDinkSaveGame>(GetTransientPackage());
	Save->CaptureFrom(Original.Context());
	Save->CurrentScreen = 412;
	Save->PlayerTransform = FTransform(FRotator(0, 90, 0), FVector(100, -250, 30));

	TArray<uint8> Bytes;
	TestTrue(TEXT("serialise"), UDinkSaveGame::SaveToBytes(Save, Bytes));
	TestTrue(TEXT("bytes written"), Bytes.Num() > 0);

	TArray<FString> Log;
	UDinkSaveGame* Loaded = UDinkSaveGame::LoadFromBytes(Bytes, &Log);
	TestNotNull(TEXT("deserialise"), Loaded);
	if (!Loaded)
	{
		return false;
	}
	TestEqual(TEXT("version"), Loaded->SaveVersion, UDinkSaveGame::CurrentVersion);
	TestEqual(TEXT("no migration needed"), Log.Num(), 0);
	TestEqual(TEXT("screen"), Loaded->CurrentScreen, 412);
	TestEqual(TEXT("transform"), Loaded->PlayerTransform, Save->PlayerTransform);
	TestTrue(TEXT("timestamp kept"), Loaded->SavedAtUtc == Save->SavedAtUtc);

	// Apply into a fresh game that has moved on, as a load does.
	FDinkTestGame Restored = MakeGame(*this);
	Restored.Facts->SetFact(TEXT("story"), 13);
	Restored.World->SetOverride(FDinkOriginId(1, 1), EDinkOverrideType::RemovedForever);
	Restored.Inventory->AddItem(TEXT("item-junk"));
	TestTrue(TEXT("apply"), Loaded->ApplyTo(Restored.Context()));
	ExpectSameGame(*this, Original, Restored);
	TestFalse(TEXT("state from after the save is gone"), Restored.World->IsPlacementRemoved(FDinkOriginId(1, 1)));

	// A default (new-game) save also survives: values equal to defaults may be skipped on write.
	FDinkTestGame Fresh = MakeGame(*this);
	UDinkSaveGame* FreshSave = NewObject<UDinkSaveGame>(GetTransientPackage());
	FreshSave->CaptureFrom(Fresh.Context());
	TArray<uint8> FreshBytes;
	UDinkSaveGame::SaveToBytes(FreshSave, FreshBytes);
	UDinkSaveGame* FreshLoaded = UDinkSaveGame::LoadFromBytes(FreshBytes);
	TestNotNull(TEXT("fresh save loads"), FreshLoaded);
	if (FreshLoaded)
	{
		TestEqual(TEXT("fresh version"), FreshLoaded->SaveVersion, UDinkSaveGame::CurrentVersion);
		TestTrue(TEXT("fresh stats"), FreshLoaded->PlayerStats == FDinkStats());
		TestEqual(TEXT("fresh inventory slots"), FreshLoaded->Inventory.Items.Num(), 16);
		TestEqual(TEXT("fresh facts"), FreshLoaded->Facts.Num(), 63);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkSaveMigrationTest, "Dink.Core.Save.Migration", DINK_TEST_FLAGS)
bool FDinkSaveMigrationTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("class default is not a real version"), GetDefault<UDinkSaveGame>()->SaveVersion, int32(INDEX_NONE));
	TestEqual(TEXT("new saves are current"), NewObject<UDinkSaveGame>(GetTransientPackage())->SaveVersion, UDinkSaveGame::CurrentVersion);

	// A version-0 save: fact keys still carry the DinkC '&'.
	UDinkSaveGame* V0 = NewObject<UDinkSaveGame>(GetTransientPackage());
	V0->SaveVersion = 0;
	V0->Facts.Add(TEXT("&story"), 7);
	V0->Facts.Add(TEXT("&s2-nad"), 1);
	V0->Facts.Add(TEXT("gold"), 30);
	V0->CurrentScreen = 37;

	TArray<uint8> Bytes;
	TestTrue(TEXT("serialise v0"), UDinkSaveGame::SaveToBytes(V0, Bytes));
	TArray<FString> Log;
	UDinkSaveGame* Migrated = UDinkSaveGame::LoadFromBytes(Bytes, &Log);
	TestNotNull(TEXT("v0 loads"), Migrated);
	if (!Migrated)
	{
		return false;
	}
	TestEqual(TEXT("now current"), Migrated->SaveVersion, UDinkSaveGame::CurrentVersion);
	TestEqual(TEXT("one step logged per version"), Log.Num(), UDinkSaveGame::CurrentVersion);
	if (Log.Num() >= 1)
	{
		TestEqual(TEXT("step text"), Log[0], FString(TEXT("migrated save v0 -> v1")));
	}
	TestEqual(TEXT("&story -> story"), Migrated->Facts.FindRef(TEXT("story")), 7);
	TestEqual(TEXT("&s2-nad -> s2-nad"), Migrated->Facts.FindRef(TEXT("s2-nad")), 1);
	TestEqual(TEXT("plain key kept"), Migrated->Facts.FindRef(TEXT("gold")), 30);
	TestFalse(TEXT("no '&' keys left"), Migrated->Facts.Contains(TEXT("&story")));
	TestEqual(TEXT("other fields untouched"), Migrated->CurrentScreen, 37);

	// The migrated save applies; an unmigrated one is refused.
	UDinkFactSubsystem* Facts = DinkTest::MakeFacts(*this);
	FDinkSaveContext Context;
	Context.Facts = Facts;
	TestTrue(TEXT("migrated save applies"), Migrated->ApplyTo(Context));
	TestEqual(TEXT("story restored"), Facts->GetFact(TEXT("story")), 7);

	UDinkSaveGame* Stale = NewObject<UDinkSaveGame>(GetTransientPackage());
	Stale->SaveVersion = 0;
	AddExpectedMessage(TEXT("migrate first"), EAutomationExpectedErrorFlags::Contains, 1);
	TestFalse(TEXT("unmigrated save refused"), Stale->ApplyTo(Context));

	// Saves from a newer build are refused, not guessed at.
	UDinkSaveGame* Future = NewObject<UDinkSaveGame>(GetTransientPackage());
	Future->SaveVersion = UDinkSaveGame::CurrentVersion + 1;
	TArray<uint8> FutureBytes;
	UDinkSaveGame::SaveToBytes(Future, FutureBytes);
	AddExpectedMessage(TEXT("cannot migrate save version"), EAutomationExpectedErrorFlags::Contains, 1);
	TestNull(TEXT("future save refused"), UDinkSaveGame::LoadFromBytes(FutureBytes));

	// The engine warns when the header names no class; that is the expected outcome here.
	AddExpectedMessage(TEXT("Failed to find object"), EAutomationExpectedErrorFlags::Contains, 1);
	TestNull(TEXT("garbage refused"), UDinkSaveGame::LoadFromBytes(TArray<uint8>{ 1, 2, 3 }));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkGameInstanceIntegrationTest, "Dink.Core.Save.GameInstanceSlotRoundTrip", DINK_TEST_FLAGS)
bool FDinkGameInstanceIntegrationTest::RunTest(const FString& Parameters)
{
	// Real game instance: subsystems are created by the engine and the fact table is loaded in
	// Initialize. Then a full SaveToSlot / LoadFromSlot through UDinkSaveSubsystem with a player actor.
	if (!TestNotNull(TEXT("GEngine"), GEngine))
	{
		return false;
	}
	UGameInstance* GameInstance = NewObject<UGameInstance>(GEngine);
	GameInstance->InitializeStandalone();
	UWorld* World = GameInstance->GetWorld();

	UDinkFactSubsystem* Facts = GameInstance->GetSubsystem<UDinkFactSubsystem>();
	UDinkWorldStateSubsystem* WorldState = GameInstance->GetSubsystem<UDinkWorldStateSubsystem>();
	UDinkSaveSubsystem* Saves = GameInstance->GetSubsystem<UDinkSaveSubsystem>();
	TestNotNull(TEXT("fact subsystem"), Facts);
	TestNotNull(TEXT("world state subsystem"), WorldState);
	TestNotNull(TEXT("save subsystem"), Saves);
	TestNotNull(TEXT("world"), World);

	if (Facts && WorldState && Saves && World)
	{
		TestEqual(TEXT("Initialize loaded 63 facts"), Facts->GetAllFacts().Num(), 63);
		TestEqual(TEXT("strength 3 from table"), Facts->GetFact(TEXT("strength")), 3);

		AActor* Player = World->SpawnActor<AActor>();
		USceneComponent* Root = NewObject<USceneComponent>(Player, TEXT("Root"));
		Player->SetRootComponent(Root);
		Root->RegisterComponent();
		UDinkStatsComponent* Stats = NewObject<UDinkStatsComponent>(Player, TEXT("Stats"));
		Stats->RegisterComponent();
		UDinkInventoryComponent* Inventory = NewObject<UDinkInventoryComponent>(Player, TEXT("Inventory"));
		Inventory->RegisterComponent();

		// The stats component finds the fact subsystem through its world when mirroring.
		Stats->bMirrorToFacts = true;
		Stats->AddGold(77);
		TestEqual(TEXT("mirror through the world's game instance"), Facts->GetFact(TEXT("gold")), 77);

		Facts->SetFact(TEXT("story"), 9);
		WorldState->SetOverride(FDinkOriginId(254, 2), EDinkOverrideType::RemovedForever);
		Inventory->AddItem(TEXT("item-fst"));
		Inventory->ArmItem(0);
		const FTransform SavedTransform(FRotator(0, 45, 0), FVector(1200, 340, 80));
		Player->SetActorTransform(SavedTransform);

		const FString Slot = TEXT("DinkParity_TestSlot");
		TestTrue(TEXT("save to slot"), Saves->SaveToSlot(Slot, Player, 254));

		// Change everything, then load.
		Facts->SetFact(TEXT("story"), 1);
		WorldState->ResetState();
		Stats->AddGold(1000);
		Inventory->DisarmItem();
		Player->SetActorTransform(FTransform::Identity);

		UDinkSaveGame* Loaded = Saves->LoadFromSlot(Slot, Player);
		TestNotNull(TEXT("load from slot"), Loaded);
		if (Loaded)
		{
			TestEqual(TEXT("screen"), Loaded->CurrentScreen, 254);
		}
		TestEqual(TEXT("story back to 9"), Facts->GetFact(TEXT("story")), 9);
		TestTrue(TEXT("override back"), WorldState->IsPlacementRemoved(FDinkOriginId(254, 2)));
		TestEqual(TEXT("gold back to 77"), Stats->Stats.Gold, 77);
		TestEqual(TEXT("weapon re-armed"), Inventory->GetArmedItem(), FName(TEXT("item-fst")));
		TestTrue(TEXT("player moved back"), Player->GetActorTransform().Equals(SavedTransform, 0.01));

		UGameplayStatics::DeleteGameInSlot(Slot, 0);
		AddExpectedMessage(TEXT("no save in slot"), EAutomationExpectedErrorFlags::Contains, 1);
		AddExpectedMessage(TEXT("Failed to read file"), EAutomationExpectedErrorFlags::Contains, 1);
		TestNull(TEXT("missing slot"), Saves->LoadFromSlot(TEXT("DinkParity_NoSuchSlot"), Player));
		Player->Destroy();
	}

	GameInstance->Shutdown();
	if (World)
	{
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkSaveMigrationV1Test, "Dink.Core.Save.MigrationV1ToV2", DINK_TEST_FLAGS)
bool FDinkSaveMigrationV1Test::RunTest(const FString& Parameters)
{
	// Version 2 added SubsystemState (module text blobs such as the narrative runtime's Ink state).
	UDinkSaveGame* V1 = NewObject<UDinkSaveGame>(GetTransientPackage());
	V1->SaveVersion = 1;
	V1->Facts.Add(TEXT("story"), 4);
	TArray<uint8> Bytes;
	TestTrue(TEXT("serialise v1"), UDinkSaveGame::SaveToBytes(V1, Bytes));
	TArray<FString> Log;
	UDinkSaveGame* Migrated = UDinkSaveGame::LoadFromBytes(Bytes, &Log);
	if (!TestNotNull(TEXT("v1 loads"), Migrated))
	{
		return false;
	}
	TestEqual(TEXT("now v2"), Migrated->SaveVersion, 2);
	TestEqual(TEXT("one step"), Log.Num(), 1);
	if (Log.Num() == 1)
	{
		TestEqual(TEXT("step text"), Log[0], FString(TEXT("migrated save v1 -> v2")));
	}
	TestEqual(TEXT("no module state in a v1 save"), Migrated->SubsystemState.Num(), 0);
	TestEqual(TEXT("facts untouched"), Migrated->Facts.FindRef(TEXT("story")), 4);

	// A v2 save keeps its module state through bytes.
	UDinkSaveGame* V2 = NewObject<UDinkSaveGame>(GetTransientPackage());
	V2->SubsystemState.Add(TEXT("narrative"), TEXT("{\"version\":1}"));
	TestTrue(TEXT("serialise v2"), UDinkSaveGame::SaveToBytes(V2, Bytes));
	UDinkSaveGame* Back = UDinkSaveGame::LoadFromBytes(Bytes);
	TestTrue(TEXT("module state round-trips"), Back && Back->SubsystemState.FindRef(TEXT("narrative")) == TEXT("{\"version\":1}"));
	return true;
}
