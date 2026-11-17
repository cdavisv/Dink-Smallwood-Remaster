#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkCreatureEvents.generated.h"

class UDinkDirector;
class UDinkCreatureClassComponent;

/**
 * Reads the simulation for the creature one-shots (DinkCreatureOneShots.h) and tells the bodies; never writes to it.
 * - a hit that costs a living class sprite life: its body flinches (the hit points dropped and stay above 0);
 * - an attack: a missile sprite (brain 11 or 17) appears near a body whose row attacks by "missile" (the dragon's fire),
 *   or Dink loses life near a body whose row attacks by "touch" (a slime's bite): the nearest such body strikes.
 * UDinkCreaturePresenter calls Observe once a frame, before the bodies present.
 */
UCLASS()
class DINKNARRATIVE_API UDinkCreatureEventSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual bool DoesSupportWorldType(EWorldType::Type Type) const override;
	void Observe(const UDinkDirector& Director);
	/** The hit points the sprite had last frame, for the presenter's flinch check. */
	static bool CostsLife(int32 Before, int32 Now) { return Now >= 1 && Before > Now; }
	int32 GetAttacksStarted() const { return Attacks; }
private:
	TSet<int32> SeenMissiles;
	int32 LastLife = -1, LastScreen = -1, Attacks = 0;
	UDinkCreatureClassComponent* NearestAttacker(const UDinkDirector& Director, const FVector& At, FName Trigger) const;
};
