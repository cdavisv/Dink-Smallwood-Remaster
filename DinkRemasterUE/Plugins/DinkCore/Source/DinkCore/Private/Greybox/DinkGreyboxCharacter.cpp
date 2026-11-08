#include "Greybox/DinkGreyboxCharacter.h"
#include "DinkCoreModule.h"
#include "DinkArtSubsystem.h"
#include "DinkInteriorCameraComponent.h"
#include "DinkInventoryComponent.h"
#include "DinkStatsComponent.h"
#include "Animation/AnimInstance.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputAction.h"
#include "InputActionValue.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "InputTriggers.h"

ADinkGreyboxCharacter::ADinkGreyboxCharacter()
{
	// A 56 cm shoulder width fits the original house's 61 cm diagonal clearance between
	// the round table and bed. The template's 84 cm capsule seals that passage.
	GetCapsuleComponent()->InitCapsuleSize(28.f, 96.f);
	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->bOrientRotationToMovement = true;
	Move->RotationRate = FRotator(0.f, 420.f, 0.f);
	Move->MaxAcceleration = 1400.f;
	Move->GroundFriction = 6.f;
	Move->MaxWalkSpeed = RunSpeed;
	Move->MinAnalogWalkSpeed = 20.f;
	Move->BrakingDecelerationWalking = 1200.f;
	Move->JumpZVelocity = 420.f;
	Move->GravityScale = 1.35f;
	Move->AirControl = .3f;
	Move->BrakingDecelerationFalling = 150.f;
	Move->MaxStepHeight = 35.f;
	Move->GetNavAgentPropertiesRef().bCanJump = true;
	JumpMaxHoldTime = .16f;
	JumpMaxCount = 1;

	ThirdPersonMapping = CreateDefaultSubobject<UInputMappingContext>(TEXT("ThirdPersonControls"));
	WalkInputAction = CreateDefaultSubobject<UInputAction>(TEXT("WalkAction"));
	JumpInputAction = CreateDefaultSubobject<UInputAction>(TEXT("JumpAction"));
	ZoomInputAction = CreateDefaultSubobject<UInputAction>(TEXT("ZoomAction"));
	WalkInputAction->ValueType = EInputActionValueType::Boolean;
	JumpInputAction->ValueType = EInputActionValueType::Boolean;
	ZoomInputAction->ValueType = EInputActionValueType::Axis1D;
	ThirdPersonMapping->MapKey(WalkInputAction, EKeys::LeftShift);
	ThirdPersonMapping->MapKey(WalkInputAction, EKeys::Gamepad_LeftShoulder);
	ThirdPersonMapping->MapKey(JumpInputAction, EKeys::SpaceBar);
	ThirdPersonMapping->MapKey(JumpInputAction, EKeys::Gamepad_FaceButton_Bottom);
	ThirdPersonMapping->MapKey(ZoomInputAction, EKeys::MouseWheelAxis);
	ThirdPersonMapping->MapKey(ZoomInputAction, EKeys::Gamepad_DPad_Up).Triggers.Add(CreateDefaultSubobject<UInputTriggerPressed>(TEXT("ZoomInPress")));
	FEnhancedActionKeyMapping& ZoomOut = ThirdPersonMapping->MapKey(ZoomInputAction, EKeys::Gamepad_DPad_Down);
	ZoomOut.Triggers.Add(CreateDefaultSubobject<UInputTriggerPressed>(TEXT("ZoomOutPress")));
	ZoomOut.Modifiers.Add(CreateDefaultSubobject<UInputModifierNegate>(TEXT("ZoomOutDirection")));

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	CameraBoom->TargetArmLength = 400.f;
	CameraBoom->bUsePawnControlRotation = true;

	FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
	FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	FollowCamera->bUsePawnControlRotation = false;
	CreateDefaultSubobject<UDinkInteriorCameraComponent>(TEXT("InteriorCamera"));

	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -96.f), FRotator(0.f, -90.f, 0.f));

	Stats = CreateDefaultSubobject<UDinkStatsComponent>(TEXT("Stats"));
	Stats->bMirrorToFacts = true;
	Inventory = CreateDefaultSubobject<UDinkInventoryComponent>(TEXT("Inventory"));

	MeshAsset = TSoftObjectPtr<USkeletalMesh>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple")));
	AnimClass = TSoftClassPtr<UAnimInstance>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed_C")));
	MappingContexts.Add(TSoftObjectPtr<UInputMappingContext>(FSoftObjectPath(TEXT("/Game/Input/IMC_Default.IMC_Default"))));
	MappingContexts.Add(TSoftObjectPtr<UInputMappingContext>(FSoftObjectPath(TEXT("/Game/Input/IMC_MouseLook.IMC_MouseLook"))));
	MoveAction = TSoftObjectPtr<UInputAction>(FSoftObjectPath(TEXT("/Game/Input/Actions/IA_Move.IA_Move")));
	LookAction = TSoftObjectPtr<UInputAction>(FSoftObjectPath(TEXT("/Game/Input/Actions/IA_Look.IA_Look")));
	MouseLookAction = TSoftObjectPtr<UInputAction>(FSoftObjectPath(TEXT("/Game/Input/Actions/IA_MouseLook.IA_MouseLook")));
}

void ADinkGreyboxCharacter::BeginPlay()
{
	Super::BeginPlay();
	if (USkeletalMesh* Mesh = MeshAsset.LoadSynchronous())
	{
		GetMesh()->SetSkeletalMesh(Mesh);
		if (UClass* Anim = AnimClass.LoadSynchronous())
		{
			GetMesh()->SetAnimInstanceClass(Anim);
		}
		if (UDinkArtSubsystem* Art = GetWorld()->GetSubsystem<UDinkArtSubsystem>()) Art->ApplyPlayer(*GetMesh());
	}
	else
	{
		UE_LOG(LogDink, Warning, TEXT("Greybox character: %s missing; run Scripts/copy_template_content.sh"), *MeshAsset.ToString());
	}
}

void ADinkGreyboxCharacter::EndPlay(const EEndPlayReason::Type Reason)
{
	if (UEnhancedInputLocalPlayerSubsystem* Input = BoundInputSubsystem.Get())
		Input->RemoveMappingContext(ThirdPersonMapping);
	BoundInputSubsystem.Reset();
	Super::EndPlay(Reason);
}

void ADinkGreyboxCharacter::NotifyControllerChanged()
{
	if (UEnhancedInputLocalPlayerSubsystem* Input = BoundInputSubsystem.Get())
		Input->RemoveMappingContext(ThirdPersonMapping);
	BoundInputSubsystem.Reset();
	StopJumping();
	Super::NotifyControllerChanged();
	if (APlayerController* PC = Cast<APlayerController>(Controller))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Input = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			BoundInputSubsystem = Input;
			Input->AddMappingContext(ThirdPersonMapping, 1);
			for (const TSoftObjectPtr<UInputMappingContext>& Soft : MappingContexts)
			{
				if (UInputMappingContext* Context = Soft.LoadSynchronous())
				{
					Input->AddMappingContext(Context, 0);
				}
				else
				{
					UE_LOG(LogDink, Warning, TEXT("Greybox character: input mapping %s missing"), *Soft.ToString());
				}
			}
		}
	}
}

void ADinkGreyboxCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (!Input)
	{
		UE_LOG(LogDink, Error, TEXT("Greybox character needs the Enhanced Input component (Config/DefaultInput.ini)"));
		return;
	}
	if (UInputAction* A = MoveAction.LoadSynchronous())
	{
		Input->BindAction(A, ETriggerEvent::Triggered, this, &ADinkGreyboxCharacter::Move);
	}
	if (UInputAction* A = LookAction.LoadSynchronous())
	{
		Input->BindAction(A, ETriggerEvent::Triggered, this, &ADinkGreyboxCharacter::Look);
	}
	if (UInputAction* A = MouseLookAction.LoadSynchronous())
	{
		Input->BindAction(A, ETriggerEvent::Triggered, this, &ADinkGreyboxCharacter::Look);
	}
	// Dialogue's Slate handler consumes Space before Enhanced Input sees it.
	Input->BindAction(WalkInputAction, ETriggerEvent::Started, this, &ADinkGreyboxCharacter::StartWalking);
	Input->BindAction(WalkInputAction, ETriggerEvent::Completed, this, &ADinkGreyboxCharacter::StopWalking);
	Input->BindAction(WalkInputAction, ETriggerEvent::Canceled, this, &ADinkGreyboxCharacter::StopWalking);
	Input->BindAction(JumpInputAction, ETriggerEvent::Started, this, &ADinkGreyboxCharacter::Jump);
	Input->BindAction(JumpInputAction, ETriggerEvent::Completed, this, &ADinkGreyboxCharacter::StopJumping);
	Input->BindAction(JumpInputAction, ETriggerEvent::Canceled, this, &ADinkGreyboxCharacter::StopJumping);
	Input->BindAction(ZoomInputAction, ETriggerEvent::Triggered, this, &ADinkGreyboxCharacter::Zoom);
}

void ADinkGreyboxCharacter::SetWalking(bool bWalking)
{
	bWalkingHeld = bWalking;
	GetCharacterMovement()->MaxWalkSpeed = bWalking ? WalkSpeed : RunSpeed;
}

void ADinkGreyboxCharacter::Jump()
{
	if (Controller && !Controller->IsMoveInputIgnored() && !Stats->IsDead()) Super::Jump();
}

void ADinkGreyboxCharacter::Zoom(const FInputActionValue& Value)
{
	ZoomCamera(Value.Get<float>());
}

void ADinkGreyboxCharacter::ZoomCamera(float Steps)
{
	if (UDinkInteriorCameraComponent* Camera = FindComponentByClass<UDinkInteriorCameraComponent>())
		Camera->AddZoomInput(Steps);
}

void ADinkGreyboxCharacter::Tick(float DeltaSeconds)
{
	if (APlayerController* PC = Cast<APlayerController>(Controller); PC && IsLocallyControlled())
	{
		// Poll held controls too: losing focus or a consumed menu key-up must never stick a gait/jump.
		const bool Held = PC->IsInputKeyDown(EKeys::LeftShift) || PC->IsInputKeyDown(EKeys::Gamepad_LeftShoulder);
		if (Held != bWalkingHeld) SetWalking(Held);
		if (PC->IsMoveInputIgnored() || Stats->IsDead() ||
			(!PC->IsInputKeyDown(EKeys::SpaceBar) && !PC->IsInputKeyDown(EKeys::Gamepad_FaceButton_Bottom))) StopJumping();
	}
	Super::Tick(DeltaSeconds);
	const FQuat Base = AppliedBodyRotation.Inverse() * GetMesh()->GetRelativeRotation().Quaternion();
	AppliedBodyRotation = BodyDynamics.Update(GetActorLocation(), GetActorQuat(), DeltaSeconds,
		GetCharacterMovement()->IsMovingOnGround()).Quaternion();
	GetMesh()->SetRelativeRotation(AppliedBodyRotation * Base);
}

void ADinkGreyboxCharacter::Move(const FInputActionValue& Value)
{
	const FVector2D Axis = Value.Get<FVector2D>();
	if (Controller)
	{
		const FRotator Yaw(0.f, Controller->GetControlRotation().Yaw, 0.f);
		AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::X), Axis.Y);
		AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::Y), Axis.X);
	}
}

void ADinkGreyboxCharacter::Look(const FInputActionValue& Value)
{
	const FVector2D Axis = Value.Get<FVector2D>();
	AddControllerYawInput(Axis.X);
	AddControllerPitchInput(Axis.Y);
}

ADinkGreyboxGameMode::ADinkGreyboxGameMode()
{
	DefaultPawnClass = ADinkGreyboxCharacter::StaticClass();
}
