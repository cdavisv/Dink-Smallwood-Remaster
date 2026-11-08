#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkCreatureSubsystem.generated.h"
/** Optional creature overlay on original placements. No actor, origin, script or brain replacement. */
UCLASS()
class DINKCORE_API UDinkCreatureSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
  public:
	virtual void OnWorldBeginPlay(UWorld& World) override;
	virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
	/** Called only for real script-created sprite actors, including restored ones. */
	void NotifyScriptSprite(AActor* Actor, int32 Sequence);
	const TArray<TWeakObjectPtr<AActor>>& GetFoodActors() const
	{
		return FoodActors;
	}

  private:
	TArray<TWeakObjectPtr<AActor>> FoodActors;
	TSet<int32> FoodSequences;
	UPROPERTY(Transient) TObjectPtr<class UStaticMesh> FoodMesh;
	FVector FoodMeshOffset = FVector(0, 0, -60);
};
