// Dink.Save.SlotInfoAsOriginal: the save machine's and the load menus' slot lines (&savegameinfo). The original writes
// "Slot N - H:MM - Level L" for a used slot (dink.cpp:4093-4106: the save's play minutes, g_playerInfo.minutes, and its save info,
// "Level &level" in the base game, dink.cpp:17729 and 1066-1069) and "Slot N - Empty" for a free one. The remaster said
// "Slot N - Saved game" for every used slot, so a player could not tell ten saves apart (playthrough QA, 15 Nov 2026).

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkSaveGame.h"
#include "DinkStorySubsystem.h"
#include "DinkWorldStateSubsystem.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkSaveSlotInfoTest, "Dink.Save.SlotInfoAsOriginal", DINK_TEST_FLAGS)
bool FDinkSaveSlotInfoTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("a free slot"), UDinkDirector::SaveGameInfo(4, nullptr), FString(TEXT("Slot 4 - Empty")));

	UGameInstance* GI = DinkTest::MakeOuterGameInstance();
	UDinkFactSubsystem* Facts = NewObject<UDinkFactSubsystem>(GI);
	FString Error;
	TestTrue(TEXT("facts load"), Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error));
	UDinkStorySubsystem* Story = NewObject<UDinkStorySubsystem>(GI);
	if (!TestTrue(TEXT("story loads"), Story->SetupStandalone(Facts, NewObject<UDinkWorldStateSubsystem>(GI), &Error))) return false;

	// The story's own save state (the key the slot line reads): 90 s of story clock, level 4.
	Story->Advance(90.0);
	UDinkSaveGame* Save = NewObject<UDinkSaveGame>(GI);
	Story->CaptureToSave(Save);
	Save->Facts.Add(TEXT("level"), 4);
	TestEqual(TEXT("a used slot: play time and level"), UDinkDirector::SaveGameInfo(3, Save), FString(TEXT("Slot 3 - 0:01 - Level 4")));

	// 1 h 12 min 30 s; the Ink state is a string inside the JSON, so an escaped "nowMs" in it is not the clock.
	UDinkSaveGame* Long = NewObject<UDinkSaveGame>(GI);
	Long->SubsystemState.Add(TEXT("narrative"), TEXT("{\"version\":1,\"ink\":\"{\\\"nowMs\\\":5}\",\"nowMs\": 4350000.5}"));
	Long->Facts.Add(TEXT("level"), 7);
	TestEqual(TEXT("hours and minutes"), UDinkDirector::SaveGameInfo(1, Long), FString(TEXT("Slot 1 - 1:12 - Level 7")));

	// A save with no story state (an old or foreign file) still reads as used, at 0:00.
	UDinkSaveGame* Bare = NewObject<UDinkSaveGame>(GI);
	Bare->Facts.Add(TEXT("level"), 2);
	TestEqual(TEXT("no clock"), UDinkDirector::SaveGameInfo(10, Bare), FString(TEXT("Slot 10 - 0:00 - Level 2")));
	return true;
}
