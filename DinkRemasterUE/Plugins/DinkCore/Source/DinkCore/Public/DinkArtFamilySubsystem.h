#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Hardness/DinkFamilyCollisionFit.h"
#include "DinkFamilyAnchor.h"
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
	/** Optional frame of a sequence family (JSON "frame", 1-based): the row then binds that one picture and wins over class rows. 0 = every frame. */
	int32 Frame = 0;
	/** Class id from sprite_classes.csv, None for a sequence family. */
	FName ClassId;
	/** Object path of the static mesh, normalised to "/Game/...Pkg.Name". */
	FString Mesh;
	/** Optional further meshes of the same family (JSON "variants"); a placement picks one by a stable hash of its origin ID. */
	TArray<FString> Variants;
	EDinkFamilyFit Fit = EDinkFamilyFit::None;
	/** true: the mesh front faces the sprite's view (south, the original camera); false: a stable per-origin yaw. */
	bool bYawFromSprite = false;
	/** Added to the chosen yaw (degrees; JSON "yaw_offset"): for modules whose sprite shows them edge-on. */
	double YawOffset = 0.0;
	/**
	 * Multiplies the mesh's size after `fit` (JSON "scale", default 1, 0.05..20). For small things that the layout-scaled
	 * 1997 picture shows several times their real size (a shell, a starfish, a flask): at real size they cannot be seen
	 * from the play camera, at the card's size they are absurd close up; a row picks the largest size that is still believable.
	 */
	double Scale = 1.0;
	/** 0..1 (JSON "anchor_front"): moves the mesh back (north) by this share of half its depth, so at 1 its front edge, not its centre, stands on the sprite's bottom edge. For deep modules such as the curved wall. */
	double AnchorFront = 0.0;
	/** JSON "anchor": "card" (default), "hardbox" or "hardbox_inner" (DinkFamilyAnchor.h): stand the mesh on the 1997 hardbox, not the card. */
	EDinkFamilyAnchor Anchor = EDinkFamilyAnchor::Card;
	/** true: also dress placements that carry a DinkC script (default: scripted placements keep their card). */
	bool bScripted = false;
	/**
	 * JSON "offset_cm": {"S439_P05": [x, y, z]}: the mesh or effect card of single placements moves by this in world axes
	 * (cm; x east, y south, z up) after the anchor and every other rule. For the few placements whose 1997 point is not
	 * where the thing stands in the built world: the fires the picture paints on the cottage roof (their points lie on
	 * the ground north of the real-size cottage), flames and burn marks on a wall face, a flight of stairs against the
	 * drawn wall. Presentation only. An optional fourth number is a size factor for that placement (actor placements):
	 * the roof fires of screen 439 are 2.2 times their picture, as the cottage is real size on a layout four times the
	 * picture's.
	 */
	TMap<FName, FVector> OffsetCm;
	TMap<FName, double> OffsetScale;
	/**
	 * JSON "scripted_scripts": DinkC script names whose placements are dressed like unscripted ones although the row is not
	 * "scripted" (scripts read to never change, move or remove their own sprite's picture: a talking tree, a table that
	 * says "Ouch, splinters"). Other scripted placements of the row keep their card.
	 */
	TArray<FName> ScriptedScripts;
	/**
	 * JSON "span": "width" (1) or "height" (2, edge-on strips): the module is repeated along its own X axis until it fills
	 * that dimension of the layout-scaled card, each copy scaled along X only to close the run exactly (a 4.38 m interior
	 * wall sprite takes two 2.5 m modules at 0.876). "stretch" (3): one module scaled along X to the card's width.
	 * 0 (default): one module at its authored size.
	 */
	uint8 Span = 0;
	/** Optional JSON "span_fill": mesh of the further modules of a span; the main mesh then stands at JSON "span_end" ("left" -1, "right" +1). */
	FString SpanFill;
	int8 SpanEnd = 0;
	/**
	 * JSON "effect" instead of "mesh": object path of a material drawn on a camera-facing card of "effect_size_cm"
	 * (default 50) for pictures that are light, not things: the twinkle over a gold heap. Used for sprites that scripts
	 * create (DressScriptSprite); placed sprites of such a row keep their card.
	 *
	 * JSON "effect_placed": true (fire of the burning house): placed sprites of the row draw the effect too, also on
	 * screens an art manifest dresses (no manifest draws effects). Their own upright card stays where the importer put
	 * it (so it still faces the camera and follows the screen and vision rules of every card) but shows the effect
	 * material. "effect_fit": [w, h] is the part of the flipbook frame the 1997 picture corresponds to (the flames fill
	 * 0.73 of a frame that leaves room for their sway): the card grows by 1/w and 1/h about the middle of its bottom
	 * edge, then sinks by "effect_sink" (fraction of the new height: the margin under the flames in the frame).
	 * "effect_ground": true stands that bottom edge on the ground instead: a 1997 picture drawn above its sort point
	 * (the flames, 21 px up) is a thing standing further north, so the card moves north by the height it floated at;
	 * one drawn below it (the embers) moves south.
	 * "effect_light": [r, g, b, candela, radius_cm] adds a point light without shadows at "effect_light_height"
	 * (fraction of the new height, default 0.35), just in front of the card. "effect_light_flicker" (0 to 0.9,
	 * default 0) is the part of that intensity that wavers, as firelight does.
	 * "effect_plume": {"material": "/Game/...", "size_cm": [w, h], "origins": ["S439_P05", ...]} adds a second,
	 * camera-facing card over the named placements: the smoke column of a fire under the open sky (its foot in the
	 * upper flames). Only the named placements get it: under a roof the column would stand in the rafters.
	 */
	FString Effect;
	double EffectSizeCm = 50.0;
	bool bEffectPlaced = false;
	FVector2D EffectFit = FVector2D(1.0, 1.0);
	double EffectSink = 0.0;
	bool bEffectGround = false;
	FLinearColor EffectLight = FLinearColor::Black;
	double EffectLightCandela = 0.0;
	double EffectLightRadiusCm = 0.0;
	double EffectLightHeight = 0.35;
	double EffectLightFlicker = 0.0;
	FString EffectPlume;
	FVector2D EffectPlumeSizeCm = FVector2D(300.0, 600.0);
	TSet<FName> EffectPlumeOrigins;
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
	int32 Frame = 0;
	FName ClassId;
	bool bScripted = false;
	/** The placement's DinkC script (none when unscripted), matched against the row's ScriptedScripts. */
	FName ScriptName;
	bool bHardnessOnly = false;
};

namespace DinkArtFamily
{
	/** "Dink/Data/Art/families.json" under the project content directory. */
	DINKCORE_API FString DefaultFamiliesPath();

	/** Parses families.json text (schema dink-art-families/1). Rows with errors are left out and reported. */
	DINKCORE_API bool ParseFamilies(const FString& Json, TArray<FDinkFamilyBinding>& Out, TArray<FString>& Errors);

	/** The binding for a placement: a sequence-and-frame row wins over a class row, which wins over a plain sequence row. */
	DINKCORE_API const FDinkFamilyBinding* Resolve(const TArray<FDinkFamilyBinding>& Bindings, int32 Sequence, FName ClassId, int32 Frame = 0);
	/** The binding for a sprite a script created. As Resolve, but an "effect_placed" row (a fire sized from a placed
	 *  sprite's own card) never takes it: the picture's own sequence row is tried instead, and nullptr when that is a
	 *  placed-effect row too (the sprite then shows its 1997 picture). */
	DINKCORE_API const FDinkFamilyBinding* ResolveScriptSprite(const TArray<FDinkFamilyBinding>& Bindings, int32 Sequence, FName ClassId, int32 Frame = 0);

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

	/** One module of a span: which mesh, where along the run (cm from its middle, along the module's X) and how long (0 = authored length). */
	struct FSpanPiece
	{
		bool bFill = false;
		double OffsetCm = 0.0;
		double LengthCm = 0.0;
	};
	/** The modules that fill SpanCm with modules of ModuleCm (one unscaled piece when the binding has no span). */
	DINKCORE_API void SpanPieces(const FDinkFamilyBinding& Binding, double SpanCm, double ModuleCm, TArray<FSpanPiece>& Out);
	/** MeshTransform for one span piece: moved along the yawed X axis and scaled along X only. */
	DINKCORE_API FTransform SpanTransform(const FBox& MeshBounds, const FVector& Ground, double YawDegrees, float Scale, const FSpanPiece& Piece);

	/** Places a mesh whose local bounds are MeshBounds so that its horizontal centre and its bottom land on Ground. */
	DINKCORE_API FTransform MeshTransform(const FBox& MeshBounds, const FVector& Ground, double YawDegrees, float Scale);

	/** Deterministic yaw in [0, 360) from the origin ID (no random stream is touched). */
	DINKCORE_API double StableYaw(const FString& Origin);

	/** Deterministic variant index in [0, Count) from the origin ID; independent of StableYaw. */
	DINKCORE_API int32 StableVariant(const FString& Origin, int32 Count);

	/** Depth (the sprite's view axis) in cm of a mesh of MeshSizeCm turned by YawDegrees about Z and scaled. */
	DINKCORE_API double DepthAfterYaw(const FVector& MeshSizeCm, double YawDegrees, float Scale);

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

	/** Tag on the family mesh that stands for a sprite a script created (create_sprite). */
	static const FName ScriptSpriteTag;
	/** Tag on the camera-facing effect card of a script-created sprite (rows with "effect"). */
	static const FName ScriptEffectTag;
	/** Tag on the card that shows a script-created sprite's 1997 picture when its picture has no family mesh. */
	static const FName ScriptPictureTag;

	/** The picture cards made by DressScriptSprite; UDinkGreyboxSubsystem turns them to face the camera each frame. */
	static TArray<TWeakObjectPtr<class UStaticMeshComponent>>& ScriptPictureCards();
	/** Pixel width, height and origin (x, y) of a 1997 picture "<seq>_<frame:02d>" from Data/Art/sprite_pictures.json. */
	static bool PictureInfo(int32 Sequence, int32 Frame, FIntVector4& Out);
	/** The same for a picture key ("<seq>_<frame:02d>" or "init_<file>_<frame:02d>"). */
	static bool PictureInfoForKey(const FString& Key, FIntVector4& Out);
	/**
	 * A script's init("load_sequence_now <file> <seq> ...") line loads <file>'s frames into <seq>, replacing what dink.ini put
	 * there (figure_out, dink.cpp:2335-2366: FreeSequence + ReloadSequence for an active sequence): Seth's pose 580 and walks
	 * 581/583/587/589 (s7-mil.c:9-13) over the green gnome. Picture cards of that sequence then show "init_<file>_<frame>"
	 * (sprite_pictures.json, imported by the bundle) and no family mesh of the old picture. Hero sequences
	 * (graphics\dink\...) are skipped: the hero is drawn by his own mesh. Presentation only. False if the line defines nothing.
	 */
	static bool RegisterInitSequencePicture(const FString& Line);
	/** Forgets every init picture (a loaded game registers its own lines again). */
	static void ClearInitSequencePictures();
	/** "init_<file>" for a sequence an init line replaced, else empty. */
	static FString InitSequencePicture(int32 Sequence);

	/**
	 * Presentation of a sprite a script created (create_sprite: pickups, dropped gold and hearts). Such a sprite has no
	 * origin ID and no card; it is a small marker actor. When the picture it shows (sequence and frame) belongs to a
	 * family with a mesh in families.json, the actor gets that mesh as a child without collision, standing at
	 * Actor location + GroundOffset at Size times its real size, and the marker (the actor's root mesh) is hidden.
	 * Call again when the picture or the size changes: the mesh follows, and a picture without a family row gets the
	 * marker back. Actors that another layer presents (script characters, creatures, food) are left alone.
	 * Visual only: touch, hit and talk keep the sprite's pixel box. Returns true when a family mesh is shown.
	 * A picture without a family mesh (script people, Seth, effects) is drawn as the 1997 picture on a camera-facing card
	 * (MI_Sprite_<seq>_<frame> of the import, real size from sprite_pictures.json, its origin on the ground point) and the
	 * grey marker is hidden; true is returned then too. bAllowPictureCard false leaves that out (a twinkle riding a heap).
	 * The marker stays only when the picture was never imported.
	 */
	bool DressScriptSprite(AActor* Actor, int32 Sequence, int32 Frame, const FVector& GroundOffset, float Size = 1.f, bool bAllowPictureCard = true);

	/**
	 * Class id of a sprite picture, learnt from the placements of the loaded world (sprite_classes.csv is import-time
	 * data). Frame 0 asks for the sequence as a whole: the class when every placed frame of it has the same one.
	 */
	FName ClassOfPicture(int32 Sequence, int32 Frame) const;

	/**
	 * The picture a placement shows instead of its imported one: the save's editor_seq / editor_frame, which update_play_changes
	 * (dink.cpp:5773-5832) gives a placement with a saved editor_type 2-5 on every screen load, its script cleared (5831). The
	 * family row is then looked up from that picture (a row with its sequence and frame, else its class, else its sequence; a
	 * scripted-only restriction reads bScripted) and a placement this layer dressed already is dressed again from it. Sequence <= 0
	 * forgets the picture: the imported one again. Placements with a fitted collision body are left to that layer. Visual only.
	 * Returns true when a family mesh shows for the placement.
	 */
	bool SetPlacementPicture(ADinkPlaceholderActor& Actor, int32 Sequence, int32 Frame, bool bScripted);

	/**
	 * During a visit: the placement's sprite now shows Sequence/Frame (its animation). When families.json has a row for that very
	 * picture (sequence and frame) and it is not the mesh the placement shows already, the placement is dressed from that picture
	 * (SetPlacementPicture). Any other picture changes nothing. Returns true when the mesh changed.
	 */
	bool FollowPlacementPicture(ADinkPlaceholderActor& Actor, int32 Sequence, int32 Frame);

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
	/** The binding's mesh or one of its variants for this origin; falls back to the main mesh when a variant is missing. */
	UStaticMesh* MeshFor(const FDinkFamilyBinding& Binding, const FString& Origin);
	UStaticMesh* LoadFamilyMesh(const FString& Path, const FString& Family);
	bool DressActor(ADinkPlaceholderActor& Actor);
	/** A placed sprite of an "effect_placed" row: its card shows the effect material (and carries the row's light). */
	bool DressPlacedEffect(ADinkPlaceholderActor& Actor, const FDinkFamilyBinding& Binding);
	int32 DressInstances(ADinkGreyboxScreen& Screen);

	TArray<FDinkFamilyBinding> Bindings;
    TArray<FDinkFamilyCollisionFitRule> CollisionFitRules;
    FDinkReleasedFamilyVisualBinding ReleasedVisualBinding;
    bool bCollisionFitPolicyError=true; // unavailable until the mandatory file has been read and parsed
	FDinkFamilyPrecedence Precedence;
	UPROPERTY(Transient)
	TMap<FString, TObjectPtr<UStaticMesh>> Meshes;
	TSet<FString> MissingMeshes;
	UPROPERTY(Transient)
	TMap<FString, TObjectPtr<class UMaterialInterface>> Effects;
	TMap<int32, TArray<TWeakObjectPtr<ADinkPlaceholderActor>>> ActorsByScreen;
	TMap<int32, TArray<TWeakObjectPtr<ADinkGreyboxScreen>>> GreyboxByScreen;
	/** SetPlacementPicture: the picture DressActor looks the family row up from, per placement (the imported one when absent). */
	struct FPlacementPicture { int32 Sequence = 0; int32 Frame = 0; bool bScripted = false; };
	TMap<TWeakObjectPtr<ADinkPlaceholderActor>, FPlacementPicture> PlacementPictures;
	/** (sequence << 16 | frame) -> class id, from every placement; frame 0 holds the sequence's class when it is unique (None otherwise). */
	TMap<int32, FName> ClassByPicture;
	TSet<int32> AppliedScreens;
	TMap<EDinkFamilyDecision, int32> DecisionCounts;
	FDelegateHandle ScreenHandle;
	TWeakObjectPtr<class UDinkGreyboxSubsystem> Greybox;
	int32 Dressed = 0;
	bool bReady = false;
	bool bIndexed = false;
};
