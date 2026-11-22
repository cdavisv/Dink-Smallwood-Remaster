#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Tickable.h"
#include "DinkHeroWeapon.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
class USkeletalMeshComponent;

/** One armed item's mesh in Dink's hand (Content/Dink/Data/Art/hero_weapons.json `items`). */
struct DINKNARRATIVE_API FDinkHeroWeaponRow
{
	FString Mesh;
	FName Bone;
	FVector Location = FVector::ZeroVector;
	FRotator Rotation = FRotator::ZeroRotator;
};

namespace DinkHeroWeapons
{
	/** The row of an item script (item-sw1 ...), nullptr when the item carries nothing in the hand (fists, bombs). */
	DINKNARRATIVE_API const FDinkHeroWeaponRow* Find(FName ItemScript);
	DINKNARRATIVE_API void Reload();
	/** The hero's drawn body: the visible skeletal mesh that has the bone, the pose leader first. */
	DINKNARRATIVE_API USkeletalMeshComponent* FindBody(AActor* Hero, FName Bone);
	/**
	 * Puts the item's mesh in the body's hand (or takes it away when Item has no row): one component per hero, tagged, made
	 * once and re-aimed on a change of item. Returns the component that holds the weapon, nullptr when the hand is empty.
	 */
	DINKNARRATIVE_API UStaticMeshComponent* Apply(AActor* Hero, FName ItemScript, bool bShow);
}

/**
 * The armed weapon in Dink's hand (bug A203). 1997 draws the armed weapon in every idle, walk and attack picture of Dink
 * (arming reloads those sequences: item-sw1.c, item-b1.c ...); the remaster attaches the weapon mesh to his hand for as long
 * as the item's script is the armed weapon (UDinkGameplay::GetWeaponInstance), and takes it away when nothing is armed,
 * the item is fists or a bomb, or Dink is dead. Presentation only: no collision, nothing of the simulation is read but the
 * armed item and &life. dink.Hero.Weapons 0: off.
 */
UCLASS()
class DINKNARRATIVE_API UDinkHeroWeaponSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkHeroWeaponSubsystem, STATGROUP_Tickables); }
	virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game || Type == EWorldType::PIE; }
	/** The item script shown in the hand last tick (NAME_None: empty). */
	FName GetShownItem() const { return Shown; }
private:
	FName Shown;
};
