#include "DinkScreenIndex.h"
#include "DinkPerfScope.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"

void UDinkScreenIndexSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	if (UWorld* World = GetWorld())
	{
		SpawnHandle = World->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateUObject(this, &UDinkScreenIndexSubsystem::OnActorSpawned));
	}
	LevelHandle = FWorldDelegates::LevelAddedToWorld.AddUObject(this, &UDinkScreenIndexSubsystem::OnLevelAdded);
}

void UDinkScreenIndexSubsystem::Deinitialize()
{
	if (UWorld* World = GetWorld()) World->RemoveOnActorSpawnedHandler(SpawnHandle);
	FWorldDelegates::LevelAddedToWorld.Remove(LevelHandle);
	Super::Deinitialize();
}

UDinkScreenIndexSubsystem* UDinkScreenIndexSubsystem::Get(const UWorld* World)
{
	return World ? World->GetSubsystem<UDinkScreenIndexSubsystem>() : nullptr;
}

void UDinkScreenIndexSubsystem::OnActorSpawned(AActor* Actor)
{
	if (bBuilt && (Cast<ADinkPlaceholderActor>(Actor) || Cast<ADinkGreyboxScreen>(Actor))) bBuilt = false;
}

void UDinkScreenIndexSubsystem::OnLevelAdded(ULevel* Level, UWorld* World)
{
	if (World == GetWorld()) bBuilt = false;
}

void UDinkScreenIndexSubsystem::Build()
{
	DINK_PERF_SCOPE(Dink_ScreenIndex_Build);
	PlaceholdersByScreen.Reset();
	GreyboxByScreen.Reset();
	Placeholders.Reset();
	if (UWorld* World = GetWorld())
	{
		for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
		{
			Placeholders.Add(*It);
			PlaceholdersByScreen.FindOrAdd(It->ScreenNumber).Add(*It);
		}
		for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It) GreyboxByScreen.FindOrAdd(It->ScreenNumber).Add(*It);
	}
	bBuilt = true;
	++Builds;
}

const TArray<TWeakObjectPtr<ADinkPlaceholderActor>>& UDinkScreenIndexSubsystem::PlaceholdersOn(int32 ScreenNumber)
{
	static const TArray<TWeakObjectPtr<ADinkPlaceholderActor>> None;
	if (!bBuilt) Build();
	const TArray<TWeakObjectPtr<ADinkPlaceholderActor>>* Found = PlaceholdersByScreen.Find(ScreenNumber);
	return Found ? *Found : None;
}

const TArray<TWeakObjectPtr<ADinkGreyboxScreen>>& UDinkScreenIndexSubsystem::GreyboxOn(int32 ScreenNumber)
{
	static const TArray<TWeakObjectPtr<ADinkGreyboxScreen>> None;
	if (!bBuilt) Build();
	const TArray<TWeakObjectPtr<ADinkGreyboxScreen>>* Found = GreyboxByScreen.Find(ScreenNumber);
	return Found ? *Found : None;
}

const TArray<TWeakObjectPtr<ADinkPlaceholderActor>>& UDinkScreenIndexSubsystem::AllPlaceholders()
{
	if (!bBuilt) Build();
	return Placeholders;
}

TArray<ADinkPlaceholderActor*> DinkScreenIndex::Placeholders(UWorld* World, int32 ScreenNumber)
{
	TArray<ADinkPlaceholderActor*> Out;
	if (!World) return Out;
	if (UDinkScreenIndexSubsystem* Index = DinkPerf::FixesEnabled() ? UDinkScreenIndexSubsystem::Get(World) : nullptr)
	{
		for (const TWeakObjectPtr<ADinkPlaceholderActor>& Weak : Index->PlaceholdersOn(ScreenNumber))
			if (ADinkPlaceholderActor* Actor = Weak.Get(); IsValid(Actor) && Actor->ScreenNumber == ScreenNumber) Out.Add(Actor);
		return Out;
	}
	for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It) if (It->ScreenNumber == ScreenNumber) Out.Add(*It);
	return Out;
}

TArray<ADinkGreyboxScreen*> DinkScreenIndex::Greybox(UWorld* World, int32 ScreenNumber)
{
	TArray<ADinkGreyboxScreen*> Out;
	if (!World) return Out;
	if (UDinkScreenIndexSubsystem* Index = DinkPerf::FixesEnabled() ? UDinkScreenIndexSubsystem::Get(World) : nullptr)
	{
		for (const TWeakObjectPtr<ADinkGreyboxScreen>& Weak : Index->GreyboxOn(ScreenNumber))
			if (ADinkGreyboxScreen* Actor = Weak.Get(); IsValid(Actor) && Actor->ScreenNumber == ScreenNumber) Out.Add(Actor);
		return Out;
	}
	for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It) if (It->ScreenNumber == ScreenNumber) Out.Add(*It);
	return Out;
}
