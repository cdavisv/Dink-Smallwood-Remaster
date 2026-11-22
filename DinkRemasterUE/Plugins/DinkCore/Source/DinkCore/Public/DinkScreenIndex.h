// Per-screen lookup of the generated world's placement actors and greybox screens (stream perf-stutter, 15 Nov 2026).
//
// The whole 644-screen world is loaded at once (always-loaded sublevels), about 5,800 placement actors. Screen-entry
// dressing used to walk every one of them for each screen it dressed (decals, town houses, indoor cards, state
// swaps): tens of thousands of actor visits in the frame the player crossed a screen edge. This index is built once
// (lazily, on the first query) and rebuilt when a level is added to the world or a placement/greybox actor spawns.
// Read-only: it never changes an actor; the order inside a screen is the TActorIterator order, as before.
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkScreenIndex.generated.h"

class ADinkPlaceholderActor;
class ADinkGreyboxScreen;

namespace DinkScreenIndex
{
	/** The placement actors of one screen: from the index under dink.Perf.Fixes, else by walking the world (master). */
	DINKCORE_API TArray<ADinkPlaceholderActor*> Placeholders(UWorld* World, int32 ScreenNumber);
	/** The greybox screen actors of one screen, the same way. */
	DINKCORE_API TArray<ADinkGreyboxScreen*> Greybox(UWorld* World, int32 ScreenNumber);
}

UCLASS()
class DINKCORE_API UDinkScreenIndexSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** Placement actors of one original screen (valid pointers at the time of the build; callers check IsValid). */
	const TArray<TWeakObjectPtr<ADinkPlaceholderActor>>& PlaceholdersOn(int32 ScreenNumber);
	/** Greybox screen actors (ground, decor instances) of one original screen. */
	const TArray<TWeakObjectPtr<ADinkGreyboxScreen>>& GreyboxOn(int32 ScreenNumber);
	/** Every placement actor of the world, in iterator order. */
	const TArray<TWeakObjectPtr<ADinkPlaceholderActor>>& AllPlaceholders();

	/** Forget the index: the next query rebuilds it. */
	void Invalidate() { bBuilt = false; }
	int32 GetBuildCount() const { return Builds; }

	static UDinkScreenIndexSubsystem* Get(const UWorld* World);

private:
	void Build();
	void OnActorSpawned(AActor* Actor);
	void OnLevelAdded(ULevel* Level, UWorld* World);

	TMap<int32, TArray<TWeakObjectPtr<ADinkPlaceholderActor>>> PlaceholdersByScreen;
	TMap<int32, TArray<TWeakObjectPtr<ADinkGreyboxScreen>>> GreyboxByScreen;
	TArray<TWeakObjectPtr<ADinkPlaceholderActor>> Placeholders;
	bool bBuilt = false;
	int32 Builds = 0;
	FDelegateHandle SpawnHandle, LevelHandle;
};
