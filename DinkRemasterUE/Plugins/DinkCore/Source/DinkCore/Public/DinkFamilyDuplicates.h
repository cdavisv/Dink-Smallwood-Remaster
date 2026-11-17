#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkFamilyDuplicates.generated.h"

struct FDinkFamilyBinding;
struct FDinkFamilyPrecedence;
class ADinkPlaceholderActor;
class UDinkArtFamilySubsystem;

/**
 * Bug A208: 1997 maps often place the same object on two (or four) neighbouring screens, one copy inside its screen and
 * the others past their own screen's edge only to draw the part that overlaps. 1997 shows one screen at a time; the
 * remaster shows the neighbours together, and the family layer gives every copy its own mesh with its own variant and
 * yaw, so the player saw two trees in one spot. This rule dresses ONE copy of such a group.
 *
 * A copy is one placement (actor or background instance) the family layer would dress (families.json row bound, same
 * gates as UDinkArtFamilySubsystem::DressActor / DressInstances). Two copies are the same object when all hold:
 *   - same families.json row, same sprite picture (sequence and frame), on different screens;
 *   - their ground points (where the mesh stands) are at most MaxWorldCm apart in the world;
 *   - their 1997 map points are at most MaxMapPx apart on the 1997 screen grid (screen column * 600 + x, row * 400 + y);
 *   - their cards are the same size in 1997 pixels (card width / local metres per pixel, within SizeTolerance).
 * Kept: the best by (distance in 1997 pixels from its ground point to its own screen's 600 x 400 interior, 0 inside;
 * then the lower screen number; then the lower origin ID). Greedy in that order over the whole world: a copy with an
 * already kept partner is dropped, so the result depends on the placement data only, never on which screen is dressed
 * first or on the frame budget of neighbour dressing.
 *
 * Dropped copies get no family mesh and their card stays hidden (the kept copy draws the object: its card until its
 * screen is dressed, then its mesh). A dropped placement actor's card is hidden as soon as the decision is built (in
 * the family layer's BuildIndex, at the first screen dressed: the start screen at play start); a dropped background
 * instance's card when its decor component is dressed. Presentation only: hardness, collision, scripts, warps and
 * origin IDs are untouched. Placements under a collision-fit rule (barrels) and placements gated by &vision (which
 * copy shows depends on story state) are never copies. `dink.FamilyDuplicates 0` before play = master behaviour.
 */
struct DINKCORE_API FDinkFamilyCopy
{
	FString Origin;
	int32 Screen = 0;
	/** The families.json row (rows are compared by identity). */
	const FDinkFamilyBinding* Binding = nullptr;
	int32 Sequence = 0;
	int32 Frame = 0;
	/** World XY (cm) where the family mesh stands: the card's centre along the placement's east axis, the placement's y. */
	FVector2D GroundCm = FVector2D::ZeroVector;
	/** The same point in its own screen's map pixels (inside: 0 <= x < 600, 0 <= y < 400). */
	FVector2D MapPx = FVector2D::ZeroVector;
	/** Card width in 1997 pixels (sprite width times sp size), independent of the layout scale of the region. */
	double SizePx = 0.0;
};

namespace DinkFamilyDuplicates
{
	/** The rubber-sheet layout moves copies of one 1997 pixel up to ~1 m apart at screen seams (S177_P04 / S209_P08: 82 cm). */
	constexpr double MaxWorldCm = 100.0;
	/** 385 of the 392 same-class cross-screen pairs within 1 m are 0-4 px apart in 1997; the other 7 are 5-15 px (kept as two). */
	constexpr double MaxMapPx = 4.0;
	constexpr double SizeTolerance = 0.05;

	/** 1997-pixel distance from a map point to the screen's 600 x 400 interior (0 inside). */
	DINKCORE_API double OutsidePx(const FVector2D& MapPx);
	/** The point on the 1997 world grid (32 screens a row, 600 x 400 px each). */
	DINKCORE_API FVector2D GridPx(int32 Screen, const FVector2D& MapPx);
	/** A and B stand for the same object (see the class comment). */
	DINKCORE_API bool SameObject(const FDinkFamilyCopy& A, const FDinkFamilyCopy& B);
	/** A is preferred to B: nearer its own screen's interior, then lower screen number, then lower origin ID. */
	DINKCORE_API bool Before(const FDinkFamilyCopy& A, const FDinkFamilyCopy& B);
	/** Dropped origin -> the kept origin that draws it. Independent of the order of Copies. */
	DINKCORE_API void Resolve(const TArray<FDinkFamilyCopy>& Copies, TMap<FString, FString>& OutDropped);
	/**
	 * Every copy of a world: placement actors and background instances that pass the family layer's static gates
	 * (Decide == Bound with a mesh row; not authored, humanoid or creature art; &vision 0; not under a collision-fit rule
	 * (IsFitted)). Card visibility is NOT read: it changes at run time, the decision must not.
	 */
	DINKCORE_API void Gather(UWorld& World, const TArray<FDinkFamilyBinding>& Bindings, const FDinkFamilyPrecedence& Precedence,
		TFunctionRef<bool(const ADinkPlaceholderActor&)> IsFitted, TArray<FDinkFamilyCopy>& Out);
}

/** Holds the A208 decision for one game world; built once, when the family layer indexes the world (BuildIndex). */
UCLASS()
class DINKCORE_API UDinkFamilyDuplicatesSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	/** Tag on a placement actor whose object another copy draws (it also carries the family tag). */
	static const FName DroppedTag;

	/** Hook at the end of UDinkArtFamilySubsystem::BuildIndex (the first ApplyScreen: the start screen at play start). */
	static void Build(UDinkArtFamilySubsystem& Families);
	/** Hook of DressActor: true when the actor is a dropped copy (its card is hidden and it is tagged; dress nothing). */
	static bool DropActor(UDinkArtFamilySubsystem& Families, ADinkPlaceholderActor& Actor, const FString& Origin);
	/** Hook of DressInstances: true when the background instance is a dropped copy (add no family instance for it). */
	static bool IsDroppedInstance(UDinkArtFamilySubsystem& Families, const FString& Origin);

	/** Dropped origin -> kept origin (empty until the first query). */
	const TMap<FString, FString>& GetDropped() const { return Dropped; }
	int32 GetCopyCount() const { return Copies; }
	/** Builds the decision now if it was not built yet (Build normally did; a query before it builds it then). */
	void EnsureBuilt(UDinkArtFamilySubsystem& Families);
	/** Time the one build took (ms). */
	double GetBuildMs() const { return BuildMs; }

protected:
	virtual bool DoesSupportWorldType(EWorldType::Type WorldType) const override;

private:
	static UDinkFamilyDuplicatesSubsystem* For(UDinkArtFamilySubsystem& Families);
	TMap<FString, FString> Dropped;
	int32 Copies = 0;
	double BuildMs = 0.0;
	bool bBuilt = false;
};
