#pragma once

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"
#include "UObject/Package.h"
#include "DinkFactSubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "Engine/GameInstance.h"

/** Flags for every Dink test: run in any application context (editor, commandlet), product filter. */
#define DINK_TEST_FLAGS (EAutomationTestFlags_ApplicationContextMask | EAutomationTestFlags::ProductFilter)

namespace DinkTest
{
	/**
	 * Game-instance subsystems are ClassWithin UGameInstance, so even standalone test copies need
	 * a game instance as their outer. This one is never initialised (no world, no subsystems of its
	 * own); tests call the subsystem methods directly.
	 */
	inline UGameInstance* MakeOuterGameInstance()
	{
		return NewObject<UGameInstance>(GetTransientPackage());
	}

	/**
	 * A fact subsystem created outside a game instance (no Initialize call), loaded with the
	 * shipped table. Fails the test if the table cannot be read.
	 */
	inline UDinkFactSubsystem* MakeFacts(FAutomationTestBase& Test)
	{
		UDinkFactSubsystem* Facts = NewObject<UDinkFactSubsystem>(MakeOuterGameInstance());
		FString Error;
		const bool bLoaded = Facts->LoadInitialFactsFromFile(UDinkFactSubsystem::GetDefaultInitialFactsPath(), &Error);
		Test.TestTrue(FString::Printf(TEXT("shipped facts table loads (%s)"), *Error), bLoaded);
		return Facts;
	}

	inline UDinkWorldStateSubsystem* MakeWorldState()
	{
		return NewObject<UDinkWorldStateSubsystem>(MakeOuterGameInstance());
	}
}
