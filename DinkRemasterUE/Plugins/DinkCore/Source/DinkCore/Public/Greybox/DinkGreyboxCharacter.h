#pragma once

#include "CoreMinimal.h"
#include "DinkHeroPhysicality.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameModeBase.h"
#include "DinkGreyboxCharacter.generated.h"

class UCameraComponent;
class UEnhancedInputLocalPlayerSubsystem;
class UDinkInventoryComponent;
class UDinkStatsComponent;
class UInputAction;
class UInputMappingContext;
class USpringArmComponent;
struct FInputActionValue;

/** What the original's human_brain lets the player's direction keys do right now (set by the narrative layer every frame). */
enum class EDinkPlayerHold : uint8
{
	/** Normal play: the keys move Dink. */
	None,
	/** sp_nocontrol during an attack or spell sequence (dink.cpp:14742, cleared at the sequence's end 16958): the keys do nothing. */
	Rooted,
	/** The bow is drawn (process_bow, dink.cpp:14568-14598, 14761-14766): the keys turn Dink, he does not walk. */
	TurnOnly,
};

/**
 * Walk-around character for the greybox: the engine's third-person template behaviour (camera
 * boom, orient to movement, Enhanced Input) with the mannequin, animation blueprint and input
 * assets copied from the engine's template content into /Game/Characters and /Game/Input
 * (Scripts/copy_template_content.sh). Under the player's control walks at 1.7 m/s and runs at 6 m/s while the run key is held; variable-height jump.
 *
 * Carries Dink's stats (mirrored both ways with the engine-kind facts, so a script's `&gold -= 100`
 * reaches them) and inventory, so the narrative layer's add_item/count_item work in the greybox.
 */
UCLASS()
class DINKCORE_API ADinkGreyboxCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	ADinkGreyboxCharacter();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<USpringArmComponent> CameraBoom;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera")
	TObjectPtr<UCameraComponent> FollowCamera;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink")
	TObjectPtr<UDinkStatsComponent> Stats;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dink")
	TObjectPtr<UDinkInventoryComponent> Inventory;

	UPROPERTY(EditAnywhere, Category = "Dink|Assets")
	TSoftObjectPtr<USkeletalMesh> MeshAsset;

	UPROPERTY(EditAnywhere, Category = "Dink|Assets")
	TSoftClassPtr<UAnimInstance> AnimClass;

	UPROPERTY(EditAnywhere, Category = "Dink|Input")
	TArray<TSoftObjectPtr<UInputMappingContext>> MappingContexts;

	UPROPERTY(EditAnywhere, Category = "Dink|Input")
	TSoftObjectPtr<UInputAction> MoveAction;

	UPROPERTY(EditAnywhere, Category = "Dink|Input")
	TSoftObjectPtr<UInputAction> LookAction;

	UPROPERTY(EditAnywhere, Category = "Dink|Input")
	TSoftObjectPtr<UInputAction> MouseLookAction;

	/** Running speed, cm/s (6 m/s; the layout's travel-time figures, the bot and the debug
	 * commands assume it: it is the top speed whenever no person is steering). */
	static constexpr float RunSpeed = 600.f;
	/** Walking speed, cm/s: what the player's stick or keys give unless the run key is held. */
	static constexpr float WalkSpeed = 170.f;
	/** A person's last movement input counts as steering for this long, s. */
	static constexpr float HumanSteerGraceSeconds = .25f;
	virtual void Tick(float DeltaSeconds) override;
	virtual void Jump() override;
	virtual void Landed(const FHitResult& Hit) override;
	virtual void OnJumped_Implementation() override;
	/** New-game chance that a real jump ends in a botched landing: a stagger, or (two in five
	 * of them at level 1) flat on his face. It falls with confidence to nothing for the hero
	 * (FDinkHeroPhysicality::BotchChance). Cosmetic: the capsule and the controls are untouched. */
	UPROPERTY(EditAnywhere, Category="Dink|Physicality", meta=(ClampMin="0", ClampMax="1"))
	float LandingStumbleChance = .3f;
	/** Level-1 rate of catching a toe while running flat out (about once in two minutes of
	 * running; fades with confidence). A catch-step he recovers from, never a fall. */
	UPROPERTY(EditAnywhere, Category="Dink|Physicality", meta=(ClampMin="0", ClampMax="1"))
	float RunTripsPerSecond = .008f;
	/** The same at a walk (about once in three minutes of walking at level 1). */
	UPROPERTY(EditAnywhere, Category="Dink|Physicality", meta=(ClampMin="0", ClampMax="1"))
	float WalkTripsPerSecond = .006f;
	/** Review tool behind dink.Hero.Mannerism: plays one of the clumsy moments now, whatever the dice say. */
	bool ForceMannerism(FName Kind);
	/** Launch speed and air control of a timid (level 1) and a fully confident Dink. */
	static constexpr float TimidJumpZ = 280.f, ConfidentJumpZ = 340.f;
	static constexpr float TimidAirControl = .2f, ConfidentAirControl = .35f;
	UFUNCTION(BlueprintPure, Category="Dink|Physicality")
	bool IsStumbling() const { return HeroPhysicality.IsStumbling(); }
	/** 0 = scrawny, timid new-game Dink; 1 = the late-game hero (see FDinkHeroPhysicality). */
	UFUNCTION(BlueprintPure, Category="Dink|Physicality")
	float GetConfidence() const { return HeroPhysicality.GetConfidence(); }
	/** Names of the build shapes (morph targets) a hero mesh may carry; see FDinkHeroPhysicality::GetBuild. */
	static const FName ScrawnyShape, BrawnyShape;
	/** True while the shown hero mesh carries both build shapes and they are being driven. */
	UFUNCTION(BlueprintPure, Category="Dink|Physicality")
	bool HasBuildShapes() const { return bBuildShapes; }
	/** Build shown now: X = scrawny, Y = brawny, each 0..1 (zero when the mesh has no build shapes). */
	UFUNCTION(BlueprintPure, Category="Dink|Physicality")
	FVector2D GetShownBuild() const { return bBuildShapes ? FVector2D(AppliedBuild) : FVector2D::ZeroVector; }
	/** The run key (Left Shift, left shoulder button): run while held, or walk if dink.Hero.RunByDefault is 1. */
	void SetRunKeyHeld(bool bHeld);
	bool IsRunKeyHeld() const { return bRunKeyHeld; }
	/** True while movement input from the player's own controls arrived within the grace time. */
	bool IsHumanSteering() const;
	/** Top ground speed wanted now: WalkSpeed or RunSpeed, times DinkSpeedScale. */
	float DesiredTopSpeed() const;
	/**
	 * set_dink_speed (dink.cpp:7563-7575, read every frame at D:17311-17321): Dink's walk speed in 2D pixels per frame is 12 for
	 * dinkspeed 1, 6 for 2, 3 for 3 (main.c's default) and 1 above that. The scale is that speed over the default 3 (item-bt.c's boots
	 * arm with set_dink_speed(2): twice as fast). Set by the director's set_dink_speed.
	 */
	float DinkSpeedScale = 1.f;
	/** Movement from the player's own controls (stick or keys; X right, Y forward, relative to the camera). */
	void PlayerMoveInput(FVector2D Axis);
	/**
	 * 1997 input rules for the player's own keys (alpha mechanics QA, 15 Nov 2026). Entering Rooted or TurnOnly while a person
	 * steers stops the walk at once, as the original's Dink stands for the attack. Movement fed directly (the bot, scripted
	 * moves, tests) never passes through PlayerMoveInput and is not affected, so probe traces cannot change.
	 */
	void SetPlayerHold(EDinkPlayerHold Hold);
	EDinkPlayerHold GetPlayerHold() const { return PlayerHold; }
	/**
	 * The direction (world, unit, horizontal) of the player's last own movement input, while it is still Dink's facing: the
	 * original's changedir sets dir on the frame of the key (dink.cpp:15013-15070) and the attack, spell and bow read it at once
	 * (14812-14820, item-fst.c / item-fb.c sp_dir(1, -1)), whereas the pawn turns at RotationRate. Cleared when a script sets
	 * Dink's dir or something other than the player's keys moves the pawn.
	 */
	bool GetPlayerFacing(FVector& OutDirection) const;
	void ClearPlayerFacing() { bPlayerFacing = false; }
	/** True when the player's own movement keys gave input on this frame or the last (the original's sjoy direction bits). */
	bool HasPlayerKeysThisFrame() const;
	/** Turns the pawn to Direction at once (the attack plays where it hits). */
	void FaceDirectionNow(const FVector& Direction);
	void ZoomCamera(float Steps);

	/**
	 * Player-only wall clearance (mesh only; the capsule and its movement are untouched). The
	 * hunch, lean and gait sway carry the head and shoulders past the 28 cm capsule, so walking
	 * into a wall pushed them into it. Each frame short sphere sweeps run from the capsule axis
	 * to the head and shoulder points of the posed mesh; when one is blocked the applied body
	 * lean is eased off and the mesh pulled back along the facing by the overlap (clamped to
	 * MaxWallPullback, applied at once so nothing shows through, released smoothly when clear).
	 */
	UPROPERTY(EditAnywhere, Category="Dink|Physicality")
	bool bWallClearance = true;
	/** Largest pull-back of the mesh, cm. */
	UPROPERTY(EditAnywhere, Category="Dink|Physicality", meta=(ClampMin="0"))
	float MaxWallPullback = 35.f;
	/** Mesh pull-back currently applied along -facing, cm (0 when no wall is in reach). */
	UFUNCTION(BlueprintPure, Category="Dink|Physicality")
	float GetWallPullback() const { return WallPullback; }
	/** 0..1: how much of the body lean is being held back by a wall. */
	UFUNCTION(BlueprintPure, Category="Dink|Physicality")
	float GetWallLeanDamping() const { return WallLeanDamping; }
	/** World position of the forward-most head point the clearance protects, as the mesh stands now. */
	UFUNCTION(BlueprintPure, Category="Dink|Physicality")
	FVector GetHeadReachPoint() const;
	/** Forward reach of the protected points beyond their bones, cm (face/nose, shoulder front). */
	static constexpr float HeadReach = 13.f, HeadLift = 5.f, ShoulderReach = 9.f, WallProbeRadius = 3.f;

private:
	void StartWalking() { SetRunKeyHeld(true); }
	void StopWalking() { SetRunKeyHeld(false); }
	void UpdateGait(float DeltaSeconds);
	double LastHumanMoveSeconds = -1.e9;
	EDinkPlayerHold PlayerHold = EDinkPlayerHold::None;
	FVector PlayerFacing = FVector::ForwardVector;
	bool bPlayerFacing = false;
	void Zoom(const FInputActionValue& Value);
	UPROPERTY() TObjectPtr<UInputMappingContext> ThirdPersonMapping;
	UPROPERTY() TObjectPtr<UInputAction> WalkInputAction;
	UPROPERTY() TObjectPtr<UInputAction> JumpInputAction;
	UPROPERTY() TObjectPtr<UInputAction> ZoomInputAction;
	TWeakObjectPtr<UEnhancedInputLocalPlayerSubsystem> BoundInputSubsystem;
	bool bRunKeyHeld = false;
	FDinkHeroPhysicality HeroPhysicality;
	FVector PreviousBodyLocation = FVector::ZeroVector;
	FVector AppliedBodyOffset = FVector::ZeroVector;
	/** Landforms: how far the drawn body and the camera boom stand above the capsule's flat floor now (visual only). */
	float AppliedGroundLift = 0.f;
	FVector AppliedPhysique = FVector::OneVector;
	FVector2f AppliedBuild = FVector2f(-1.f, -1.f);
	TWeakObjectPtr<class USkeletalMesh> BuildMesh;
	bool bBuildShapes = false;
	float AppliedJumpConfidence = -1.f;
	float AirSeconds = 0.f;
    float PreviousBodyYaw = 0.f;
	bool bBodyLocationReady = false;
	void UpdateConfidence(bool bSnap);
	/** Shows what the physicality decided this frame on the body: catch-steps, botched landings,
	 * fidgets, the after-swing wobble. Cosmetic. */
	void UpdateMannerisms(class UDinkBodyAnimInstance& Body, bool bAllowed, bool bTeleported, bool bGrounded);
	void PlayBotch(UDinkBodyAnimInstance& Body, FDinkHeroPhysicality::EBotch Kind);
	int32 PreviousLife = 0;
	float PreviousAttackTime = 0.f;
	FName FidgetClip;
	bool bReviewJump = false;
	float WallPullback = 0.f;
	float WallLeanDamping = 0.f;
	bool ShouldClearWalls() const;
	/** Probe points (head, shoulders) in mesh component space, from the live pose when there is one. */
	void GetWallProbePoints(TArray<FVector, TInlineAllocator<3>>& Out) const;
	/** Pull-back (cm along -facing) the mesh needs at this relative transform to keep its probes out of walls. */
	float MeasureWallOverlap(const FTransform& MeshRelative) const;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	virtual void NotifyControllerChanged() override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

	void Move(const FInputActionValue& Value);
	void Look(const FInputActionValue& Value);
};

/** Game mode of the generated greybox maps: spawns ADinkGreyboxCharacter at the map's player start. */
UCLASS()
class DINKCORE_API ADinkGreyboxGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ADinkGreyboxGameMode();
};
