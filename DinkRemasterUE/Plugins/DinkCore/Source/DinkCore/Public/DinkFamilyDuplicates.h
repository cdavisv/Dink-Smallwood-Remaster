#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkFamilyDuplicates.generated.h"

struct FDinkFamilyBinding;
struct FDinkFamilyPrecedence;
class ADinkPlaceholderActor;
class UDinkArtFamilySubsystem;
class USceneComponent;

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
 *
 * Copies are one object only while they show the same picture (review R5/R6 of #192). A copy's picture changes when the
 * save gives it its editor_seq/editor_frame (update_play_changes, dink.cpp:5829-5830: dam-fire.c burns an unscripted
 * pine to 20/29 with editor_type 4) or its animation reaches a picture with its own family row
 * (UDinkArtFamilySubsystem::SetPlacementPicture). 1997 draws only the copy of the screen Dink is on, so the copy that
 * draws a group (its "drawer") is:
 *   - the kept copy, while every copy shows the kept copy's picture and that picture has a family mesh (one mesh,
 *     never a different variant or yaw when Dink crosses the seam);
 *   - else (pictures differ, or the shared picture is drawn by a card, which renders only on the current screen:
 *     dink.LegacyCardsCurrentScreen) the copy on the screen Dink is on, with ITS OWN picture (its family mesh if that
 *     picture has one, else its card); on any other screen the kept copy.
 * Every other copy of the group is hidden (card and family parts hidden in game, never destroyed) and given back exactly
 * when it draws again, so two copies never draw at once. The drawer is decided anew on every picture change and every
 * screen change; pictures equal again join the copies again. A group with a background instance keeps its kept copy
 * (instances never change picture, and one instance cannot be hidden alone); no such group has a scripted or burnable
 * copy in the 1997 maps.
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
	/** Tag on a placement actor whose object another copy draws now (it also carries the family tag). */
	static const FName DroppedTag;

	/** Hook at the end of UDinkArtFamilySubsystem::BuildIndex (the first ApplyScreen: the start screen at play start). */
	static void Build(UDinkArtFamilySubsystem& Families);
	/** Hook of DressActor: true when another copy draws the actor's object now (its card is hidden and it is tagged; dress nothing). */
	static bool DropActor(UDinkArtFamilySubsystem& Families, ADinkPlaceholderActor& Actor, const FString& Origin);
	/** Hook of DressInstances: true when the background instance is a dropped copy (add no family instance for it). */
	static bool IsDroppedInstance(UDinkArtFamilySubsystem& Families, const FString& Origin);
	/** Hook of SetPlacementPicture before it undresses the actor: what this rule hid on it is shown again (not dressed). */
	static void Restore(UDinkArtFamilySubsystem& Families, ADinkPlaceholderActor& Actor);
	/** Hook of SetPlacementPicture after the new picture is registered: the copies of the actor's object pick their drawer anew. */
	static void PictureChanged(UDinkArtFamilySubsystem& Families, ADinkPlaceholderActor& Actor);
	/** Hook of the family layer's screen change (after ApplyScreen): every group picks its drawer anew. */
	static void ScreenChanged(UDinkArtFamilySubsystem& Families);

	/** Dropped origin -> kept origin (empty until the first query). The static decision; GetDrawer says who draws now. */
	const TMap<FString, FString>& GetDropped() const { return Dropped; }
	/** The copy that draws Origin's object now; Origin itself when it is no copy. */
	FString GetDrawer(const FString& Origin) const;
	int32 GetCopyCount() const { return Copies; }
	/** Builds the decision now if it was not built yet (Build normally did; a query before it builds it then). */
	void EnsureBuilt(UDinkArtFamilySubsystem& Families);
	/** Time the one build took (ms). */
	double GetBuildMs() const { return BuildMs; }

protected:
	virtual bool DoesSupportWorldType(EWorldType::Type WorldType) const override;

private:
	static UDinkFamilyDuplicatesSubsystem* For(UDinkArtFamilySubsystem& Families);
	/** The copies of one object: the kept copy first, then the dropped ones (by origin). */
	struct FGroup
	{
		TArray<FString> Members;
		/** A member is a background instance: the kept copy always draws. */
		bool bHasInstance = false;
		/** The member that draws the object now. */
		FString Drawer;
	};
	/** What Suppress hid on one copy, to give back exactly that. */
	struct FHidden
	{
		TArray<TWeakObjectPtr<USceneComponent>> Components;
		/** The family tag was added by this rule (the copy was not dressed). */
		bool bTagged = false;
	};
	FString PickDrawer(UDinkArtFamilySubsystem& Families, const FGroup& Group) const;
	void Refresh(UDinkArtFamilySubsystem& Families, FGroup& Group);
	void Suppress(ADinkPlaceholderActor& Actor, const FString& Origin);
	void Unsuppress(UDinkArtFamilySubsystem& Families, ADinkPlaceholderActor& Actor, const FString& Origin, bool bDress);
	TMap<FString, FString> Dropped;
	TArray<FGroup> Groups;
	/** Every copy's origin -> its group (index into Groups). */
	TMap<FString, int32> GroupOf;
	/** Copies that are placement actors (the others are background instances). */
	TMap<FString, TWeakObjectPtr<ADinkPlaceholderActor>> MemberActors;
	TMap<FString, FHidden> Hidden;
	int32 Copies = 0;
	double BuildMs = 0.0;
	bool bBuilt = false;
};
