#pragma once

#include "CoreMinimal.h"
#include "DinkBodyDynamics.h"
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

/**
 * Walk-around character for the greybox: the engine's third-person template behaviour (camera
 * boom, orient to movement, Enhanced Input) with the mannequin, animation blueprint and input
 * assets copied from the engine's template content into /Game/Characters and /Game/Input
 * (Scripts/copy_template_content.sh). Runs at 6 m/s, walks at 2 m/s, with variable-height jump.
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

	/** Running speed, cm/s (6 m/s; the layout's travel-time figures assume it). */
	static constexpr float RunSpeed = 600.f;
	static constexpr float WalkSpeed = 200.f;
	virtual void Tick(float DeltaSeconds) override;
	virtual void Jump() override;
	virtual void Landed(const FHitResult& Hit) override;
	UPROPERTY(EditAnywhere, Category="Dink|Physicality", meta=(ClampMin="0", ClampMax="1"))
	float LandingStumbleChance = .45f;
	UFUNCTION(BlueprintPure, Category="Dink|Physicality")
	bool IsStumbling() const { return HeroPhysicality.IsStumbling(); }
	void SetWalking(bool bWalking);
	void ZoomCamera(float Steps);

private:
	void StartWalking() { SetWalking(true); }
	void StopWalking() { SetWalking(false); }
	void Zoom(const FInputActionValue& Value);
	UPROPERTY() TObjectPtr<UInputMappingContext> ThirdPersonMapping;
	UPROPERTY() TObjectPtr<UInputAction> WalkInputAction;
	UPROPERTY() TObjectPtr<UInputAction> JumpInputAction;
	UPROPERTY() TObjectPtr<UInputAction> ZoomInputAction;
	TWeakObjectPtr<UEnhancedInputLocalPlayerSubsystem> BoundInputSubsystem;
	bool bWalkingHeld = false;
	FDinkBodyDynamics BodyDynamics;
	FDinkHeroPhysicality HeroPhysicality;
	FVector PreviousBodyLocation = FVector::ZeroVector;
	FVector AppliedBodyOffset = FVector::ZeroVector;
	float AirSeconds = 0.f;
    float PreviousBodyYaw = 0.f;
	bool bBodyLocationReady = false;
	FQuat AppliedBodyRotation = FQuat::Identity;

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
