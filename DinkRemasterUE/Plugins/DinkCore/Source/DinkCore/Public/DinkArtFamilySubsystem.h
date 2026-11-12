#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Hardness/DinkFamilyCollisionFit.h"
#include "DinkArtFamilySubsystem.generated.h"

class ADinkGreyboxScreen;
class ADinkPlaceholderActor;
class ADinkScreenVolume;
class FJsonObject;
class UStaticMesh;

/**
 * How a family mesh is sized (families.json `fit`). The default is None: the mesh's real size, like the player and the
 * dressed screens; the greybox cards are layout-scaled (settlements x4), so the card-fitting modes are opt-in only.
 */
enum class EDinkFamilyFit : uint8
{
	/** Opt-in: uniform scale so the mesh fits inside the layout-scaled card, its width (east-west) and its height. */
	Footprint,
	/** Opt-in: uniform scale so the mesh is as tall as the layout-scaled card. */
	Height,
	/** Default: the mesh's authored real size (scale 1), standing at the card's ground point. */
	None,
};

/** One row of Content/Dink/Data/Art/families.json. */
struct DINKCORE_API FDinkFamilyBinding
{
	/** As written: a sequence ("173 bonuses/barrels/barel-": the leading number counts) or a class id ("barrel"). */
	FString Family;
	/** Leading number of a sequence family, INDEX_NONE for a class family. */
	int32 Sequence = INDEX_NONE;
	/** Class id from sprite_classes.csv, None for a sequence family. */
	FName ClassId;
	/** Object path of the static mesh, normalised to "/Game/...Pkg.Name". */
	FString Mesh;
	EDinkFamilyFit Fit = EDinkFamilyFit::None;
	/** true: the mesh front faces the sprite's view (south, the original camera); false: a stable per-origin yaw. */
	bool bYawFromSprite = false;
	/** true: also dress placements that carry a DinkC script (default: scripted placements keep their card). */
	bool bScripted = false;
	FString Note;
};

/** Origin IDs and screens the authored-art manifests (Codex's DinkArtSubsystem, creatures, characters) already handle. */
struct DINKCORE_API FDinkFamilyPrecedence
{
	TSet<FString> Origins;
	TSet<int32> Screens;

	/** Adds one parsed Data/Art manifest; schemas other than dink-art/creatures/characters add nothing. */
	void AddManifest(const FJsonObject& Manifest);
	/** Every *.json in Directory except SkipFile (families.json itself). */
	static FDinkFamilyPrecedence LoadDirectory(const FString& Directory, const FString& SkipFile);
};

/** Why a placement is or is not dressed by its family. */
enum class EDinkFamilyDecision : uint8
{
	Bound,
	HardnessOnly,
	ScreenDressed,
	OriginHandled,
	NoBinding,
	Scripted,
};

/** What the resolver needs to know about one placement. */
struct DINKCORE_API FDinkFamilyPlacement
{
	FString Origin;
	int32 Screen = 0;
	int32 Sequence = 0;
	FName ClassId;
	bool bScripted = false;
	bool bHardnessOnly = false;
};

namespace DinkArtFamily
{
	/** "Dink/Data/Art/families.json" under the project content directory. */
	DINKCORE_API FString DefaultFamiliesPath();

	/** Parses families.json text (schema dink-art-families/1). Rows with errors are left out and reported. */
	DINKCORE_API bool ParseFamilies(const FString& Json, TArray<FDinkFamilyBinding>& Out, TArray<FString>& Errors);

	/** The binding for a placement: a class row wins over a sequence row. */
	DINKCORE_API const FDinkFamilyBinding* Resolve(const TArray<FDinkFamilyBinding>& Bindings, int32 Sequence, FName ClassId);

	/** Precedence, in order: hardness-only proxy, dressed screen, origin-bound, no binding, scripted (unless the row allows). */
	DINKCORE_API EDinkFamilyDecision Decide(const FDinkFamilyPlacement& Placement, const FDinkFamilyPrecedence& Precedence,
		const TArray<FDinkFamilyBinding>& Bindings, const FDinkFamilyBinding*& OutBinding);

	/**
	 * Uniform scale for a mesh of MeshSizeCm (bounding box) replacing a card of SpriteWidthCm x SpriteHeightCm. The width
	 * compared is the mesh's X extent when its yaw comes from the sprite, else its larger horizontal extent. Clamped to
	 * [MinScale, MaxScale]; 1 when a size is missing.
	 */
	DINKCORE_API float FitScale(EDinkFamilyFit Fit, double SpriteWidthCm, double SpriteHeightCm, const FVector& MeshSizeCm, bool bYawFromSprite);
	constexpr float MinScale = 0.05f;
	constexpr float MaxScale = 20.f;

	/** Places a mesh whose local bounds are MeshBounds so that its horizontal centre and its bottom land on Ground. */
	DINKCORE_API FTransform MeshTransform(const FBox& MeshBounds, const FVector& Ground, double YawDegrees, float Scale);

	/** Deterministic yaw in [0, 360) from the origin ID (no random stream is touched). */
	DINKCORE_API double StableYaw(const FString& Origin);

	DINKCORE_API const TCHAR* DecisionName(EDinkFamilyDecision Decision);
}

/**
 * Sprite-family art binding (visual only). At screen activation, every greybox placement of that screen whose sprite
 * family (sequence or sprite_classes.csv class) has a mesh in Content/Dink/Data/Art/families.json gets that mesh as a
 * child component, at real size (default) standing at the card's ground point, and the card is hidden. Placements and screens that the authored
 * art manifests already handle (replacements, hide_origins, hide_origins_by_vision, warp_overrides, hide_screen_visuals,
 * authored collision, creature and character bindings) are left alone. Collision, hardness, origin IDs, scripts and
 * gameplay never change: the new components have no collision and the placement actor keeps everything it had.
 * `dink.FamilyArt 0` (before play) or `dink.ArtEnabled 0` leaves the greybox as it is.
 */
UCLASS()
class DINKCORE_API UDinkArtFamilySubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	/** Tag on every family component and on the actors that carry one. Never DinkAuthoredArt: gameplay keeps pixel rules. */
	static const FName FamilyTag;

	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;

	/** Dresses one screen (idempotent; called on screen activation). Returns the placements dressed by this call. */
	int32 ApplyScreen(int32 ScreenNumber);
	bool IsScreenApplied(int32 ScreenNumber) const { return AppliedScreens.Contains(ScreenNumber); }
	bool IsReady() const { return bReady; }
	const TArray<FDinkFamilyBinding>& GetBindings() const { return Bindings; }
    /** Typed producer for the single marked-world authority.
     * Absence of policy preserves PR40/41. */
    bool PrepareCollisionFit(const FDinkOriginId& Origin,const FDinkFamilyFitSpriteState& Sprite,
        FDinkFamilyCollisionFitCandidate& Out,FString& Error) const;
    bool ValidateCollisionFit(const FDinkFamilyCollisionFitCandidate& Candidate,
        const FDinkFamilyFitSpriteState& Current,FString& Error) const;
    bool ApplyCollisionFitVisual(FDinkFamilyCollisionFitCandidate& Candidate,
        const FDinkFamilyFitSpriteState& Current,const IDinkFamilyFitVisualAuthority& Authority,FString& Error);
    bool IsCollisionFitRequested(const FDinkOriginId& Origin) const;
    bool PrepareCollisionFitReleaseCandidate(const FDinkOriginId& Origin,const FDinkFamilyFitSpriteState& Current,
        FDinkFamilyCollisionFitCandidate& Out,FString& Error) const;
    bool ReleaseCollisionFitVisual(const FDinkFamilyCollisionFitCandidate& Candidate,
        const FDinkFamilyFitSpriteState& Current,const IDinkFamilyFitVisualAuthority& Authority,FString& Error);
    const TArray<FDinkFamilyCollisionFitRule>& GetCollisionFitRules() const { return CollisionFitRules; }
    bool HasCollisionFitPolicyError() const { return bCollisionFitPolicyError; }
	const FDinkFamilyPrecedence& GetPrecedence() const { return Precedence; }
	/** Placements dressed so far, and skip counts by decision. */
	int32 GetDressedCount() const { return Dressed; }
	const TMap<EDinkFamilyDecision, int32>& GetDecisionCounts() const { return DecisionCounts; }

protected:
	virtual bool DoesSupportWorldType(EWorldType::Type WorldType) const override;

private:
    friend class FDinkHardnessFittedLifecycle; // native scratch-policy fixture; no public bypass
    static UStaticMeshComponent* MakeUnpublishedReleasedVisual(ADinkPlaceholderActor& Actor,UStaticMesh& Mesh);
    bool LoadCollisionFitPolicy(const FString& File,FString& Text,FString& Error);
    bool PrepareCollisionFitImpl(const FDinkOriginId& Origin,const FDinkFamilyFitSpriteState& Sprite,
        FDinkFamilyCollisionFitCandidate& Out,FString& Error,bool Release) const;
	void ScreenChanged(ADinkScreenVolume* Screen);
	void BuildIndex(UWorld& World);
	UStaticMesh* MeshFor(const FDinkFamilyBinding& Binding);
	bool DressActor(ADinkPlaceholderActor& Actor);
	int32 DressInstances(ADinkGreyboxScreen& Screen);

	TArray<FDinkFamilyBinding> Bindings;
    TArray<FDinkFamilyCollisionFitRule> CollisionFitRules;
    FDinkReleasedFamilyVisualBinding ReleasedVisualBinding;
    bool bCollisionFitPolicyError=true; // unavailable until the mandatory file has been read and parsed
	FDinkFamilyPrecedence Precedence;
	UPROPERTY(Transient)
	TMap<FString, TObjectPtr<UStaticMesh>> Meshes;
	TSet<FString> MissingMeshes;
	TMap<int32, TArray<TWeakObjectPtr<ADinkPlaceholderActor>>> ActorsByScreen;
	TMap<int32, TArray<TWeakObjectPtr<ADinkGreyboxScreen>>> GreyboxByScreen;
	TSet<int32> AppliedScreens;
	TMap<EDinkFamilyDecision, int32> DecisionCounts;
	FDelegateHandle ScreenHandle;
	TWeakObjectPtr<class UDinkGreyboxSubsystem> Greybox;
	int32 Dressed = 0;
	bool bReady = false;
	bool bIndexed = false;
};
