#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Tickable.h"
#include "DinkHeroBow.generated.h"

class UStaticMeshComponent;

/** How one bow bends (Content/Dink/Data/Art/hero_weapons.json `bows.items.<item>.draw`; centimetres in the bow mesh's own axes: X up the upper limb, +Y from the grip to the string). */
struct DINKNARRATIVE_API FDinkHeroBowDraw
{
	/** Where the segments of the upper limb begin, on the stave's centre line at rest; the lower limb is the mirror in X. */
	TArray<FVector2D> Joints;
	/** Each joint's share of the bend. */
	TArray<double> Weights;
	/** Where the string is tied to the upper limb, at rest. */
	FVector2D StringEnd = FVector2D::ZeroVector;
	/** The arrow's height on the stave: the string is pulled there. */
	double NockUp = 0.0;
	/** The furthest the string comes back from its place at rest. */
	double MaxDraw = 0.0;
};

/** The bow at one draw: every part's place in the bow mesh's axes. */
struct DINKNARRATIVE_API FDinkHeroBowPose
{
	/** Radians of bend summed over a limb's joints. */
	double Bend = 0.0;
	/** Per segment of the upper limb: X, Y of its joint and its turn in degrees (Z); the lower limb is the mirror (-X, Y, -turn). */
	TArray<FVector> Segments;
	/** The upper limb's string end, and the point the string is pulled to. */
	FVector2D Tip = FVector2D::ZeroVector;
	FVector2D Apex = FVector2D::ZeroVector;
};

/** One bow item's row: the part meshes (`%s` = Grip, LimbU1.., LimbL1.., StringU, StringL) and its draw. */
struct DINKNARRATIVE_API FDinkHeroBowRow
{
	FString Parts;
	FDinkHeroBowDraw Draw;
};

namespace DinkHeroBow
{
	/** The bend at which the string, tied to both limb tips and pulled DrawCm back at the arrow's height, keeps its length. */
	DINKNARRATIVE_API FDinkHeroBowPose Solve(const FDinkHeroBowDraw& Draw, double DrawCm);
	/** The row of a bow item (item-b1 ...), nullptr for anything else. */
	DINKNARRATIVE_API const FDinkHeroBowRow* Find(FName ItemScript);
	DINKNARRATIVE_API void Reload();
	/**
	 * Dresses the hero's held bow (the component DinkHeroWeapons::Apply made) for a draw: limb segments turned, the two string halves
	 * stretched from the tips to the pull point, the arrow on the string (bArrow), the quiver on his back. Hides all of it when no
	 * bow is shown. Returns true while a bow is dressed.
	 */
	DINKNARRATIVE_API bool Apply(AActor* Hero, FName ItemScript, double DrawCm, bool bArrow);
	/** How far the string hand has pulled the string (cm), from where the body's string fingers are; 0 when they are not at the string. */
	DINKNARRATIVE_API double DrawFromHand(AActor* Hero, FName ItemScript);
	/** A dressed part by its key (LimbU1, StringU, Arrow, Quiver ...), nullptr if it does not exist. */
	DINKNARRATIVE_API UStaticMeshComponent* FindPart(AActor* Hero, FName Key);
}

/**
 * The bow that bends (art row AN-05). 1997 draws the armed bow with an arrow across it and a quiver of red-fletched arrows on
 * Dink's back (graphics/dink/bow/idle, walk), and in the draw the bow bending as the string comes back (bow/hit, six pictures a
 * direction; the draw is g_bowStatus.time, dink.cpp:14564-14621). The remaster's bow mesh is cut into rigid parts (art kit
 * HeroWeapons, tools/build_bow_parts.py); while UDinkGameplay::IsBowActive the string follows the body's string fingers, the
 * limbs bend so that the string keeps its length, and the arrow rides on the string; at the release the string goes back and the
 * arrow is gone for a moment (it is the missile now). Presentation only: reads the armed item, the bow status and bone places.
 * dink.Hero.BowDraw <cm> forces a draw for review (-2: follow the hand even when the bow is not drawn).
 */
UCLASS()
class DINKNARRATIVE_API UDinkHeroBowSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkHeroBowSubsystem, STATGROUP_Tickables); }
	virtual bool DoesSupportWorldType(EWorldType::Type Type) const override { return Type == EWorldType::Game || Type == EWorldType::PIE; }
	/** The draw shown last tick, cm. */
	double GetDrawCm() const { return DrawCm; }
private:
	double DrawCm = 0.0;
	double ArrowBackAt = 0.0;
	bool bWasActive = false;
};
