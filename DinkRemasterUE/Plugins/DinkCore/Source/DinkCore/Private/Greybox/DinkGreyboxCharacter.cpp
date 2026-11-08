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
	Move->RotationRate = FRotator(0.f, 500.f, 0.f);
	Move->MaxWalkSpeed = RunSpeed;
	Move->MinAnalogWalkSpeed = 20.f;
	Move->BrakingDecelerationWalking = 2000.f;
	Move->JumpZVelocity = 0.f;
	Move->GetNavAgentPropertiesRef().bCanJump = false;

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

void ADinkGreyboxCharacter::NotifyControllerChanged()
{
	Super::NotifyControllerChanged();
	if (APlayerController* PC = Cast<APlayerController>(Controller))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Input = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
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
