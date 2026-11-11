#include "Greybox/DinkGreyboxCharacter.h"
#include "DinkCoreModule.h"
#include "DinkArtSubsystem.h"
#include "DinkEarlyPostureAnimInstance.h"
#include "DinkInteriorCameraComponent.h"
#include "DinkInventoryComponent.h"
#include "DinkStatsComponent.h"
#include "Animation/AnimInstance.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "CollisionQueryParams.h"
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
	Move->RotationRate = FRotator(0.f, 300.f, 0.f);
	Move->MaxAcceleration = 900.f;
	Move->GroundFriction = 6.f;
	Move->MaxWalkSpeed = RunSpeed;
	Move->MinAnalogWalkSpeed = 20.f;
	Move->BrakingDecelerationWalking = 850.f;
	Move->JumpZVelocity = 280.f;
	Move->GravityScale = 1.45f;
	Move->AirControl = .2f;
	Move->BrakingDecelerationFalling = 150.f;
	Move->MaxStepHeight = 35.f;
	Move->GetNavAgentPropertiesRef().bCanJump = true;
	JumpMaxHoldTime = .08f;
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

void ADinkGreyboxCharacter::Landed(const FHitResult& Hit)
{
	const bool Allowed = Controller && !Controller->IsMoveInputIgnored() && !Stats->IsDead();
	// Clumsy landings become rare as Dink grows into a hero; a flailing takeoff always lands badly.
	if (Allowed) HeroPhysicality.Land(FMath::Max(0.f, -GetVelocity().Z), AirSeconds,
		HeroPhysicality.ScaleChance(LandingStumbleChance, .08f));
	AirSeconds = 0.f;
	Super::Landed(Hit);
}

void ADinkGreyboxCharacter::OnJumped_Implementation()
{
	Super::OnJumped_Implementation();
	if (Controller && !Controller->IsMoveInputIgnored() && !Stats->IsDead())
		HeroPhysicality.TakeOff(HeroPhysicality.ScaleChance(TakeoffFlailChance, 0.f));
}

void ADinkGreyboxCharacter::UpdateConfidence(bool bSnap)
{
	const FDinkStats& S = Stats->Stats;
	HeroPhysicality.SetTargetConfidence(FDinkHeroPhysicality::ConfidenceFor(S.Level, S.Strength, S.Defense), bSnap);
	// Player-only jump (the original has none): a stronger Dink hops higher and steers in the air.
	const float C = HeroPhysicality.GetConfidence();
	if (C != AppliedJumpConfidence || bSnap)
	{
		UCharacterMovementComponent* Move = GetCharacterMovement();
		Move->JumpZVelocity = FMath::Lerp(TimidJumpZ, ConfidentJumpZ, C);
		Move->AirControl = FMath::Lerp(TimidAirControl, ConfidentAirControl, C);
		AppliedJumpConfidence = C;
	}
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
	const FVector Location = GetActorLocation();
	const bool Teleported = !bBodyLocationReady || FVector::DistSquared(Location, PreviousBodyLocation) >= FMath::Square(200.);
	if (Teleported) { HeroPhysicality.Cancel(); AirSeconds = 0.f; }
	// Loads and warps show the earned build at once; a level-up straightens him over a few seconds.
	UpdateConfidence(Teleported);
	const bool Grounded = GetCharacterMovement()->IsMovingOnGround();
	const bool Allowed = Controller && !Controller->IsMoveInputIgnored() && !Stats->IsDead();
	if (!Allowed) AirSeconds = 0.f;
	else if (!Grounded) AirSeconds += DeltaSeconds;
	else AirSeconds = 0.f;
	const float TurnRate = !Teleported && DeltaSeconds > SMALL_NUMBER
        ? FMath::FindDeltaAngleDegrees(PreviousBodyYaw, GetActorRotation().Yaw) / DeltaSeconds : 0.f;
    HeroPhysicality.Update(DeltaSeconds, GetVelocity().Size2D(), Grounded, Allowed && !Teleported, TurnRate,
        RunTripsPerSecond);
    PreviousBodyYaw = GetActorRotation().Yaw;
	PreviousBodyLocation = Location; bBodyLocationReady = true;
	const FQuat Base = AppliedBodyRotation.Inverse() * GetMesh()->GetRelativeRotation().Quaternion();
	AppliedBodyRotation = BodyDynamics.Update(GetActorLocation(), GetActorQuat(), DeltaSeconds,
		Grounded).Quaternion() * HeroPhysicality.GetRotation().Quaternion();
    if (Allowed && !Teleported && DeltaSeconds>SMALL_NUMBER &&
        Cast<UDinkEarlyPostureAnimInstance>(GetMesh()->GetPostProcessInstance()))
    {
        // Bone-level authored slouch owns the timid hunch; keep shuffle/stumble and the upright
        // lean confidence earns.
        AppliedBodyRotation = AppliedBodyRotation * FRotator(-HeroPhysicality.GetHunchPitch(),0,0).Quaternion();
    }
	// A wall the clearance found last frame holds back part of the lean (eased, cosmetic).
	if (WallLeanDamping > 0.f)
		AppliedBodyRotation = FQuat::Slerp(AppliedBodyRotation, FQuat::Identity, .8f * WallLeanDamping);
	GetMesh()->SetRelativeRotation(AppliedBodyRotation * Base);
	const FVector BaseLocation = GetMesh()->GetRelativeLocation() - AppliedBodyOffset;
	// Scrawny frame that fills out with confidence; composed on whatever scale art authored.
	const FVector BaseScale = GetMesh()->GetRelativeScale3D() / AppliedPhysique;
	AppliedPhysique = HeroPhysicality.GetPhysiqueScale();
	// Wall clearance composes with the physicality offset: measure the mesh where the body
	// layer puts it, then pull it back along the facing (actor-local -X) by the overlap. It
	// rises at once (nothing shows through the wall) and releases over a few tenths of a second.
	const FVector BodyOffset = HeroPhysicality.GetOffset();
	const float WallNeeded = ShouldClearWalls() ? MeasureWallOverlap(FTransform(GetMesh()->GetRelativeRotation().Quaternion(),
		BaseLocation + BodyOffset, BaseScale * AppliedPhysique)) : 0.f;
	WallPullback = (Teleported || WallNeeded >= WallPullback) ? WallNeeded
		: FMath::FInterpTo(WallPullback, WallNeeded, DeltaSeconds, 6.f);
	const float LeanTarget = FMath::Clamp(WallNeeded / 8.f, 0.f, 1.f);
	WallLeanDamping = Teleported ? LeanTarget : FMath::FInterpTo(WallLeanDamping, LeanTarget, DeltaSeconds, 8.f);
	if (WallLeanDamping < KINDA_SMALL_NUMBER) WallLeanDamping = 0.f;
	AppliedBodyOffset = BodyOffset - FVector(WallPullback, 0.f, 0.f);
	GetMesh()->SetRelativeLocation(BaseLocation + AppliedBodyOffset);
	GetMesh()->SetRelativeScale3D(BaseScale * AppliedPhysique);
}

bool ADinkGreyboxCharacter::ShouldClearWalls() const
{
	// The player only: the probe bot drives this pawn through a player controller too, which
	// is fine because only the mesh moves; NPCs and unpossessed copies never run it.
	return bWallClearance && GetMesh() && GetWorld() && Cast<APlayerController>(Controller) != nullptr;
}

void ADinkGreyboxCharacter::GetWallProbePoints(TArray<FVector, TInlineAllocator<3>>& Out) const
{
	// Mesh component space of the 89-bone rig: feet at the origin, facing +Y, centimetres.
	// The live pose (walk, posture clip, head-down) is used when the mesh has one; the
	// fallbacks are Dink's bind-pose bones.
	struct FProbe { const TCHAR* Bone; FVector BindPose; FVector Reach; };
	const FProbe Probes[] = {
		{TEXT("head"), FVector(0., .7, 162.6), FVector(0., HeadReach, HeadLift)},
		{TEXT("upperarm_l"), FVector(19., -2.6, 143.6), FVector(0., ShoulderReach, 0.)},
		{TEXT("upperarm_r"), FVector(-19., -2.6, 143.6), FVector(0., ShoulderReach, 0.)}};
	const USkeletalMeshComponent* Body = GetMesh();
	const bool bLive = Body && Body->GetSkeletalMeshAsset() && Body->GetNumComponentSpaceTransforms() > 0;
	for (const FProbe& Probe : Probes)
	{
		FVector Bone = Probe.BindPose;
		if (bLive)
		{
			const int32 Index = Body->GetBoneIndex(FName(Probe.Bone));
			const FVector Live = Index != INDEX_NONE ? Body->GetBoneTransform(Index, FTransform::Identity).GetLocation() : FVector::ZeroVector;
			if (Index != INDEX_NONE && Live.Z > 60. && Live.Z < 240.) Bone = Live;
		}
		Out.Add(Bone + Probe.Reach);
	}
}

FVector ADinkGreyboxCharacter::GetHeadReachPoint() const
{
	TArray<FVector, TInlineAllocator<3>> Points;
	GetWallProbePoints(Points);
	return GetMesh() ? GetMesh()->GetComponentTransform().TransformPosition(Points[0]) : GetActorLocation();
}

float ADinkGreyboxCharacter::MeasureWallOverlap(const FTransform& MeshRelative) const
{
	const UWorld* World = GetWorld();
	const UCapsuleComponent* Capsule = GetCapsuleComponent();
	if (!World || !Capsule) return 0.f;
	TArray<FVector, TInlineAllocator<3>> Points;
	GetWallProbePoints(Points);
	const FTransform Actor = GetActorTransform();
	const FVector Axis = GetActorLocation(), Up = GetActorUpVector();
	const FVector Facing = GetActorForwardVector().GetSafeNormal2D();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkWallClearance), false, this);
	// Whatever stops the capsule stops the head; other bodies (NPCs, ragdolls) do not.
	FCollisionResponseParams Responses(Capsule->GetCollisionResponseToChannels());
	Responses.CollisionResponse.SetResponse(ECC_Pawn, ECR_Ignore);
	Responses.CollisionResponse.SetResponse(ECC_PhysicsBody, ECR_Ignore);
	float Needed = 0.f;
	for (const FVector& Local : Points)
	{
		const FVector Point = Actor.TransformPosition(MeshRelative.TransformPosition(Local));
		// Short sweep from the capsule axis at the point's height out to the point.
		const FVector Start = Axis + Up * FVector::DotProduct(Point - Axis, Up);
		if (FVector::DistSquared(Start, Point) < 1.) continue;
		FHitResult Hit;
		if (!World->SweepSingleByChannel(Hit, Start, Point, FQuat::Identity, Capsule->GetCollisionObjectType(),
			FCollisionShape::MakeSphere(WallProbeRadius), Params, Responses) || Hit.bStartPenetrating) continue;
		const double Depth = FVector::DotProduct(Hit.Location - Point, Hit.Normal);
		const double Along = FVector::DotProduct(-Facing, Hit.Normal); // what a pull-back gains per cm
		if (Depth <= 0. || Along < .2) continue; // side walls: pulling back would not help
		Needed = FMath::Max(Needed, float(Depth / Along));
	}
	return FMath::Min(Needed, MaxWallPullback);
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
