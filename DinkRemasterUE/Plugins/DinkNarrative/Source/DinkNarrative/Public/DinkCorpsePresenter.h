#pragma once

#include "CoreMinimal.h"
#include "Engine/EngineTypes.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkCorpsePresenter.generated.h"

class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UTexture2D;
class UDecalComponent;
class USkeletalMeshComponent;
class UDinkDirector;

/**
 * The 1997 corpse of a killed sprite that no creature class draws (doc/remaster/GORE_STORY_PARITY.md G4), and Dink's own
 * death (G16).
 *
 * Corpses: in 1997 a monster (brain 9), dragon (10) or person (16) killed by damage leaves its death picture, sequence
 * base_death + direction (or base_walk + 5), played once and drawn into the background until the screen is drawn again
 * (add_kill_sprite, dink.cpp:12359-12420); a sprite with neither shows the explosion 164 once (brain 7, 12384-12385, 12416).
 * The remaster's bound creatures leave a mesh corpse (UDinkCreaturePresenter); every other kill used to leave nothing. This
 * layer leaves that very picture on a camera-facing card at its 1997 size until the screen changes or the director
 * recreates its sprites, and plays the explosion's frames on a card once. Whether a creature draws the corpse itself is
 * decided while the sprite is alive (a script-made sprite's actor is gone by the time the kill is seen).
 * Pictures: Content/Dink/Data/Sprites/Death (Scripts/export_death_pictures.py). dink.CorpseCards 0: off.
 *
 * Dink's death: while his sprite shows the 1997 death picture 436 (dinfo.c `die`), the hero's mesh falls as a ragdoll from
 * its physics asset (only the world holds it: creatures, bodies and missiles pass), a 190 cm blood pool spreads under him,
 * and a body thrown far or sunk is laid down face first at his feet; when a load or restart gives the sprite another
 * picture the mesh is attached to the capsule again at its old place. Capsule and sprite are untouched. dink.DeathFall 0: off.
 *
 * Strictly one way: reads the director, never writes to a sprite, draws nothing from the random stream. Nothing runs in a
 * process that cannot render.
 */
UCLASS()
class DINKNARRATIVE_API UDinkCorpsePresenter : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual void Deinitialize() override;

	/** One pass: follow living sprites, leave cards for the killed, play explosions. Returns cards made. Tests call it. */
	int32 Present(float DeltaTime = 0.f);
	/** dink.CorpseCards 0: removes every card and forgets the living sprites. Tick calls it while the switch is off. */
	void Suppress();
	/**
	 * The screen pixel the card of a picture stands on: the middle of the picture's bottom row once its registration point
	 * (OriginX, OriginY: dink.ini's offsets) is on the sprite's point (X, Y), all scaled by the sprite's size.
	 */
	static FVector2D CardFootPx(double X, double Y, int32 WidthPx, int32 HeightPx, int32 OriginX, int32 OriginY, int32 SizePercent);
	/** One pass of Dink's death fall. Tests call it. */
	void UpdateDinkDeath();
	int32 GetCardCount() const { return Cards.Num(); }
	const TArray<TObjectPtr<UStaticMeshComponent>>& GetCards() const { return Cards; }
	int32 GetPlayingCount() const { return Playing.Num(); }
	bool IsDinkFallen() const { return bDinkFallen; }
	bool HasDeathPool() const { return DeathPool != nullptr; }

	/** The explosion add_kill_sprite falls back to (seq 164, brain 7). */
	static constexpr int32 Explosion = 164;

	/**
	 * The death sequence add_kill_sprite shows (D:12359-12410): base_death + dir, with the engine's mirrored direction when
	 * that sequence has no picture; with no base_death, base_walk + 5 if it has one, else the explosion 164; 0 when the
	 * engine shows nothing (a death base of 0, or no picture in either direction). HasPicture says whether a sequence exists.
	 */
	static int32 DeathSequence(int32 BaseDeath, int32 BaseWalk, int32 Dir, TFunctionRef<bool(int32)> HasPicture);

	/** Dink's death (dinfo.c `die`: sp_seq(1, 436), 16 frames of falling, then he lies until the menu's choice). */
	static bool IsDinkDeathPicture(int32 Seq, int32 PSeq) { return Seq == 436 || PSeq == 436; }

	/** Card size (cm) of a picture: its 1997 pixels at the greybox's base scale (2.5 cm a pixel) times the sprite's size. */
	static FVector2D CardSizeCm(int32 WidthPx, int32 HeightPx, int32 SizePercent);

	/** Dink's blood pool (sequence 436 ends in a pool about twice his width) and how far a limp body may drift. */
	static constexpr float DeathPoolSizeCm = 190.f;
	static constexpr double DeathBodyMaxDriftCm = 220.0;

private:
	struct FPicture
	{
		int32 Width = 0, Height = 0, OriginX = 0, OriginY = 0;
		TObjectPtr<UTexture2D> Texture;
	};
	struct FFrame
	{
		int32 Width = 0, Height = 0, DelayMs = 50;
		TObjectPtr<UTexture2D> Texture;
	};
	struct FSeen
	{
		int32 Brain = 0;
		int32 Hitpoints = 0;
		/** A creature class or origin row draws this sprite's corpse (decided while it lives). */
		bool bCreatureDraws = false;
	};
	struct FPlay
	{
		TWeakObjectPtr<UStaticMeshComponent> Card;
		TWeakObjectPtr<UMaterialInstanceDynamic> Material;
		int32 Sequence = 0;
		int32 SizePercent = 100;
		double AgeS = 0.0;
	};

	void LoadPictures();
	UTexture2D* LoadTexture(const FString& File);
	UTexture2D* TextureFor(int32 Sequence);
	void Clear();
	UStaticMeshComponent* LeaveCard(UTexture2D* Texture, FVector2D SizeCm, int32 Screen, double X, double Y, const AActor* Ignore,
		UMaterialInstanceDynamic** OutMaterial = nullptr);
	bool CreatureDrawsCorpse(const AActor* Actor, int32 BaseDeath, int32 KillDir) const;
	void LayDownKinematic(USkeletalMeshComponent& Mesh, class UCapsuleComponent& Capsule);
	void EnsureHolder();

	bool bLoaded = false;
	TMap<int32, FPicture> Pictures;
	TMap<int32, TArray<FFrame>> Animations;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UTexture2D>> Textures;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> CardMesh;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> CardMaterial;
	UPROPERTY(Transient)
	TObjectPtr<AActor> Holder;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Cards;
	TArray<FPlay> Playing;
	TMap<int32, FSeen> Seen;
	int32 SeenScreen = -1;
	int32 SeenResetSerial = -1;

	bool bDinkFallen = false;
	bool bDinkKinematic = false;
	TWeakObjectPtr<USkeletalMeshComponent> FallenMesh;
	FTransform LivingMeshRelative;
	FName LivingMeshProfile;
	ECollisionResponse LivingCapsulePhysicsResponse = ECR_Block;
	UPROPERTY(Transient)
	TObjectPtr<UDecalComponent> DeathPool;
};
