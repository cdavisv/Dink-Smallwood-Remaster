#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkCreatureEvents.generated.h"

class UDinkDirector;
class UDinkCreatureClassComponent;

/**
 * Reads the simulation for the creature one-shots (DinkCreatureOneShots.h) and tells the bodies; never writes to it.
 * - a hit that costs a living class sprite life: its body flinches (the hit points dropped and stay above 0);
 * - an attack, by the row's trigger:
 *   "cast": the body's own sprite starts its ATTACK procedure, seen as its attack_wait jumping forward (the 1997 dragons,
 *     en-drag.c/s7-drag.c/sc-drag.c attack(), set sp_attack_wait first and cast harm with a brain-7 spark: they never fire
 *     a missile);
 *   "missile": a missile sprite (brain 11 or 17) appears near the body and was not fired by Dink (brain_parm 1: item-fb.c,
 *     item-b1..b3, the axe, bombs): the nearest such body strikes;
 *   "touch": Dink loses life to that body's touch damage (Dink's last_hit is its sprite, set by the touch damage list,
 *     dink.cpp:15639-15660): that body bites.
 * UDinkCreaturePresenter calls Observe once a frame, before the bodies present.
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
	/** attack_wait of the "cast" attackers on the screen, by sprite handle, last frame. */
	TMap<int32, int32> LastAttackWait;
	int32 LastLife = -1, LastScreen = -1, Attacks = 0;
	UDinkCreatureClassComponent* NearestAttacker(const UDinkDirector& Director, const FVector& At, FName Trigger) const;
};
