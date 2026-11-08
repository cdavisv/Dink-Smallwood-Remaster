#include "DinkProbeHold.h"
#include "DinkStorySubsystem.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Tickable.h"

DEFINE_LOG_CATEGORY_STATIC(LogDinkProbeHold, Log, All);

namespace DinkProbeHold
{
	enum class EState : uint8 { Off, Held, Released, Done };
	static EState State = EState::Off;

	static UWorld* GameWorld()
	{
		if (GEngine)
		{
			for (const FWorldContext& Context : GEngine->GetWorldContexts())
			{
				if (Context.WorldType == EWorldType::Game && Context.World())
				{
					return Context.World();
				}
			}
		}
		return nullptr;
	}

	void Engage()
	{
#if !WITH_EDITOR
		if (!FParse::Param(FCommandLine::Get(), TEXT("DinkProbeHold")))
		{
			return;
		}
		UWorld* World = GameWorld();
		if (!World || !World->GetFirstPlayerController())
		{
			UE_LOG(LogDinkProbeHold, Warning, TEXT("-DinkProbeHold: no world or no player controller at the end of engine start-up; the probe's start will not match PIE"));
			return;
		}
		UGameplayStatics::SetGamePaused(World, true);
		State = EState::Held;
		UE_LOG(LogDinkProbeHold, Display, TEXT("-DinkProbeHold: world paused until the probe starts"));
#endif
	}

	bool IsEngaged()
	{
		return State != EState::Off;
	}

	bool Process(UWorld* World)
	{
		if (!World || State == EState::Off || State == EState::Done)
		{
			return false;
		}
		if (State == EState::Held)
		{
			// Every tickable that was waiting in the pending list has been merged into the engine's list by now (the paused world
			// still calls TickObjects each frame). Take the story and the greybox out and put them back, the story first.
			UDinkStorySubsystem* Story = World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
			UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
			if (Story && Greybox)
			{
				FTickableGameObject* StoryTick = static_cast<FTickableGameObject*>(Story);
				FTickableGameObject* GreyboxTick = static_cast<FTickableGameObject*>(Greybox);
				const ETickableTickType StoryType = StoryTick->GetTickableTickType();
				const ETickableTickType GreyboxType = GreyboxTick->GetTickableTickType();
				StoryTick->SetTickableTickType(ETickableTickType::Never);
				GreyboxTick->SetTickableTickType(ETickableTickType::Never);
				StoryTick->SetTickableTickType(StoryType);
				GreyboxTick->SetTickableTickType(GreyboxType);
			}
			else
			{
				UE_LOG(LogDinkProbeHold, Warning, TEXT("-DinkProbeHold: no story or greybox subsystem; the tick order was not aligned with PIE"));
			}
			UGameplayStatics::SetGamePaused(World, false);
			State = EState::Released;
			return true; // one world frame runs before the next Update: the story clock reaches 16.667 ms, as in PIE
		}
		State = EState::Done;
		return false;
	}
}
