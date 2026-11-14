#include "DinkCreatureClassComponent.h"
#include "DinkCreatureSubsystem.h"
#include "Engine/World.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AttributesRuntime.h"
#include "BonePose.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"

// ---------------------------------------------------------------------------------------------
// Animation: a weighted blend of clip layers, evaluated on the worker thread

void UDinkCreatureAnimInstance::SetLayers(TConstArrayView<FDinkCreaturePoseLayer> InLayers)
{
	Layers.Reset();
	Layers.Append(InLayers.GetData(), InLayers.Num());
}

void FDinkCreatureAnimProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	if (const UDinkCreatureAnimInstance* Creature = Cast<UDinkCreatureAnimInstance>(InAnimInstance)) Layers = Creature->Layers;
}

bool FDinkCreatureAnimProxy::Evaluate(FPoseContext& Output)
{
	float Total = 0.f;
	for (const FDinkCreaturePoseLayer& Layer : Layers) if (Layer.Sequence) Total += Layer.Weight;
	if (Total <= KINDA_SMALL_NUMBER)
	{
		Output.ResetToRefPose();
		return true;
	}
	FCompactPose& Out = Output.Pose;
	const int32 NumBones = Out.GetNumBones();
	bool bFirst = true;
	for (const FDinkCreaturePoseLayer& Layer : Layers)
	{
		if (!Layer.Sequence || Layer.Weight <= 0.f) continue;
		FCompactPose Pose;
		Pose.SetBoneContainer(&Out.GetBoneContainer());
		FBlendedCurve Curve;
		Curve.InitFrom(Output.Curve);
		UE::Anim::FStackAttributeContainer Attributes;
		FAnimationPoseData Data(Pose, Curve, Attributes);
		Layer.Sequence->GetAnimationPose(Data, FAnimExtractContext(double(Layer.Time), false));
		const ScalarRegister W(Layer.Weight / Total);
		for (FCompactPoseBoneIndex Bone(0); Bone.GetInt() < NumBones; ++Bone)
		{
			if (bFirst) Out[Bone] = Pose[Bone] * W;
			else Out[Bone].AccumulateWithShortestRotation(Pose[Bone], W);
		}
		bFirst = false;
	}
	if (bFirst)
	{
		Output.ResetToRefPose();
		return true;
	}
	for (FCompactPoseBoneIndex Bone(0); Bone.GetInt() < NumBones; ++Bone) Out[Bone].NormalizeRotation();
	return true;
}

// ---------------------------------------------------------------------------------------------
// Component

UDinkCreatureClassComponent::UDinkCreatureClassComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	// After the tickable objects: the story moves and hides the sprite's actor there (see the class comment).
	PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
	SetMobility(EComponentMobility::Movable);
	SetCollisionProfileName(TEXT("NoCollision"));
	SetCollisionEnabled(ECollisionEnabled::NoCollision);
	SetGenerateOverlapEvents(false);
	SetCanEverAffectNavigation(false);
	// The actor may be turned (script sprites) or scaled (sp_size) by the director; the body shows its own facing and size.
	SetUsingAbsoluteLocation(true);
	SetUsingAbsoluteRotation(true);
	SetUsingAbsoluteScale(true);
	// Hundreds of these exist in the world at once: only the ones in view pay for a pose.
	VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
	ComponentTags.Add(TEXT("DinkCreatureClass"));
}

bool UDinkCreatureClassComponent::Configure(TSharedRef<const FDinkCreatureLoadedClass> InClass, float GroundOffsetCm, float InitialYawDeg, int32 InSizePercent)
{
	if (!InClass->Mesh || !InClass->Roles.IsValidIndex(InClass->DefaultRole) || InClass->Roles.Num() != InClass->Binding.Roles.Num()) return false;
	Class = InClass;
	HeldAssets.Reset();
	auto Hold = [this](const UObject* Asset) { if (Asset) HeldAssets.AddUnique(const_cast<UObject*>(Asset)); };
	Hold(InClass->Mesh);
	for (const FDinkCreatureLoadedRole& Role : InClass->Roles)
	{
		Hold(Role.Mesh);
		Hold(Role.Clip);
		Hold(Role.Locomotion.Idle);
		for (const UAnimSequence* Gait : Role.Locomotion.Gaits) Hold(Gait);
	}
	for (const auto& Pair : InClass->Materials) Hold(Pair.Value);
	GroundOffset = GroundOffsetCm;
	TargetYaw = InitialYawDeg;
	Smoother = FDinkBodySmoother();
	// The smoother measures the speed the gaits are chosen by, so it is never switched off entirely.
	Smoother.SmoothTime = FMath::Max(InClass->Binding.SmoothTimeS, 0.02f);
	Smoother.TurnRateDeg = InClass->Binding.TurnRateDegS;
	SizePercent = FMath::Max(1, InSizePercent);
	Sprite = FDinkCreatureSpriteState();
	bHasSprite = bFollowDir = bPlaced = false;
	FirstDir = LastSeq = LastFrame = 0;
	Phase = IdleTime = CyclesPerSecond = 0.f;
	Tracks.Reset();
	Layers.Reset();
	SetAnimationMode(EAnimationMode::AnimationBlueprint);
	SetAnimInstanceClass(UDinkCreatureAnimInstance::StaticClass());
	if (InClass->Binding.CullDistanceCm > 0.f) SetCullDistance(InClass->Binding.CullDistanceCm);
	StartRole(InClass->DefaultRole, true);
	Present(0.f);
	return true;
}

void UDinkCreatureClassComponent::ShowMesh(USkeletalMesh* Mesh)
{
	if (!Mesh || GetSkeletalMeshAsset() == Mesh) return;
	SetSkeletalMeshAsset(Mesh);
	for (const auto& Pair : Class->Materials) SetMaterialByName(Pair.Key, Pair.Value);
}

void UDinkCreatureClassComponent::StartRole(int32 Role, bool bRestart)
{
	if (!Class.IsValid() || !Class->Roles.IsValidIndex(Role)) return;
	if (!bRestart && Tracks.Num() > 0 && Tracks.Last().Role == Role && !Tracks.Last().bFadingOut) return;
	for (FTrack& Track : Tracks) Track.bFadingOut = true;
	FTrack Track;
	Track.Role = Role;
	Track.Weight = Tracks.Num() == 0 ? 1.f : 0.f;
	const FDinkCreatureRole& Row = Class->Binding.Roles[Role];
	const FDinkCreatureLoadedRole& Loaded = Class->Roles[Role];
	if (!Row.bLocomotion && !Row.bLoop && Loaded.Clip && Sprite.SequenceDurationS > 0.05f)
	{
		// A one-shot spans the sprite sequence it stands for: the attack lands when the original's hit frame does.
		Track.Rate = FMath::Clamp(Loaded.Clip->GetPlayLength() / Sprite.SequenceDurationS, 0.25f, 4.f);
	}
	// The sprite came into this role from another one: what the original throws at that moment (the duck's head). The
	// bones are still where the last role left them.
	const bool bFromAnotherRole = Tracks.Num() > 0 && Tracks.Last().Role != Role;
	if (bFromAnotherRole && Row.Gore.HasSevered() && Loaded.FlyingMesh && Loaded.LandedMesh && bPlaced)
	{
		if (UDinkCreatureSubsystem* Creatures = GetWorld() ? GetWorld()->GetSubsystem<UDinkCreatureSubsystem>() : nullptr)
		{
			const FVector From = GetBoneIndex(Row.Gore.Bone) != INDEX_NONE ? GetSocketLocation(Row.Gore.Bone) : Shown + FVector(0.0, 0.0, 30.0);
			const FVector Forward = FRotator(0.0, Smoother.GetYaw(), 0.0).Vector();
			const double Scale = Class->Binding.Scale * SizePercent / 100.0;
			const FVector Velocity = (Forward * FMath::FRandRange(0.45f, 0.8f) + FVector(0.0, 0.0, 1.0)) * Row.Gore.ThrowSpeedCmS + Forward * Smoother.GetSpeed();
			Creatures->ThrowPart(Loaded.FlyingMesh, Loaded.LandedMesh, Loaded.LandedDecal, Row.Gore.LandedDecalSizeCm * Scale, From, Velocity, Shown.Z, Scale);
			if (Row.Gore.SeveredDrops > 0 && Class->BloodDrop)
			{
				Creatures->EmitBlood(Class->BloodDrop, From, FVector(0.0, 0.0, 1.0), Row.Gore.DropSpeedCmS * 1.3f, 55.f, Row.Gore.SeveredDrops, Row.Gore.DropSizeCm * Scale, Shown.Z);
			}
		}
	}
	if (bFromAnotherRole)
	{
		DropDebt = GoreTime = TrailDistance = 0.f;
		bHasGorePoint = false;
	}
	if (Tracks.Num() >= 4) Tracks.RemoveAt(0);
	Tracks.Add(Track);
	ShowMesh(Loaded.Mesh ? Loaded.Mesh : Class->Mesh);
}

void UDinkCreatureClassComponent::PresentGore(float DeltaTime)
{
	if (Tracks.Num() == 0 || !Class->Roles.IsValidIndex(Tracks.Last().Role) || DeltaTime <= 0.f) return;
	const FDinkCreatureGore& Gore = Class->Binding.Roles[Tracks.Last().Role].Gore;
	const FDinkCreatureLoadedRole& Loaded = Class->Roles[Tracks.Last().Role];
	if (!Gore.HasFountain() && !Loaded.TrailDecal) return;
	UDinkCreatureSubsystem* Creatures = GetWorld() ? GetWorld()->GetSubsystem<UDinkCreatureSubsystem>() : nullptr;
	if (!Creatures) return;
	const double Scale = Class->Binding.Scale * SizePercent / 100.0;
	GoreTime += DeltaTime;
	if (Gore.HasFountain() && Class->BloodDrop)
	{
		// A cut artery spurts with the heart: about four beats a second in a running bird, never quite dry between them.
		const float Beat = 0.35f + 0.65f * FMath::Square(FMath::Max(0.f, FMath::Sin(GoreTime * 2.f * PI * 4.f)));
		DropDebt += Gore.DropsPerSecond * Beat * 1.5f * DeltaTime;
		const int32 Count = FMath::Min(24, FMath::FloorToInt32(DropDebt));
		if (Count > 0)
		{
			DropDebt -= Count;
			const FVector From = GetBoneIndex(Gore.Bone) != INDEX_NONE ? GetSocketLocation(Gore.Bone) : Shown + FVector(0.0, 0.0, 30.0 * Scale);
			// Up and a little ahead: the stump points forward and up, and the body runs on under the falling drops.
			const FVector Direction = (FVector(0.0, 0.0, 1.0) + FRotator(0.0, Smoother.GetYaw(), 0.0).Vector() * 0.25).GetSafeNormal();
			Creatures->EmitBlood(Class->BloodDrop, From, Direction, Gore.DropSpeedCmS * (0.55f + 0.45f * Beat) * FMath::Sqrt(float(Scale)), Gore.SpreadDeg, Count,
				Gore.DropSizeCm * Scale, Shown.Z, FRotator(0.0, Smoother.GetYaw(), 0.0).Vector() * Smoother.GetSpeed()); // the drops leave a running body with its speed
		}
	}
	if (Loaded.TrailDecal)
	{
		if (bHasGorePoint) TrailDistance += float(FVector::Dist2D(Shown, LastGorePoint));
		LastGorePoint = Shown;
		if (!bHasGorePoint || TrailDistance >= Gore.TrailEveryCm)
		{
			TrailDistance = 0.f;
			Creatures->AddBloodDecal(Loaded.TrailDecal, Shown, FMath::FRandRange(0.f, 360.f), Gore.TrailSizeCm * Scale * FMath::FRandRange(0.7f, 1.2f));
		}
		bHasGorePoint = true;
	}
}

void UDinkCreatureClassComponent::ApplySpriteState(const FDinkCreatureSpriteState& State)
{
	if (!Class.IsValid()) return;
	if (!bHasSprite)
	{
		bHasSprite = true;
		FirstDir = State.Dir;
	}
	Sprite = State;
	SizePercent = FMath::Max(1, State.SizePercent);
	DinkCreatureClass::FSpriteView View;
	View.Seq = State.Seq;
	View.PSeq = State.PSeq;
	const FDinkCreatureRole* Role = DinkCreatureClass::RoleForSprite(Class->Binding, View);
	if (Role)
	{
		const int32 Index = int32(Role - Class->Binding.Roles.GetData());
		// The same sequence set again, or wrapped to its first frame: the one-shot plays again.
		const bool bRestart = !Role->bLocomotion && !Role->bLoop && State.Seq > 0 && Class->Binding.RoleFor(State.Seq) == Role &&
			(State.Seq != LastSeq || State.Frame < LastFrame);
		StartRole(Index, bRestart);
	}
	LastSeq = State.Seq;
	LastFrame = State.Frame;
	// A sprite's direction is 2 until its brain first turns it, whatever its placement's picture faces: the body keeps the
	// picture's facing until the sprite turns or walks.
	if (State.Dir != FirstDir) bFollowDir = true;
	if (bFollowDir && State.bHasFacing) TargetYaw = State.FacingYawDeg;
}

FName UDinkCreatureClassComponent::GetRoleName() const
{
	return Class.IsValid() && Tracks.Num() > 0 ? Class->Binding.Roles[Tracks.Last().Role].Name : NAME_None;
}

float UDinkCreatureClassComponent::GetClipTime() const
{
	if (!Class.IsValid() || Tracks.Num() == 0 || Class->Binding.Roles[Tracks.Last().Role].bLocomotion) return -1.f;
	return Tracks.Last().Time;
}

void UDinkCreatureClassComponent::BuildLayers(float DeltaTime)
{
	const FDinkCreatureClassBinding& Binding = Class->Binding;
	const float Step = DeltaTime / FMath::Max(Binding.BlendTimeS, 0.001f);
	for (int32 Index = Tracks.Num() - 1; Index >= 0; --Index)
	{
		FTrack& Track = Tracks[Index];
		Track.Weight = FMath::Clamp(Track.Weight + (Track.bFadingOut ? -Step : Step), 0.f, 1.f);
		if (Track.bFadingOut && Track.Weight <= 0.f && Tracks.Num() > 1) Tracks.RemoveAt(Index);
	}
	const float Speed = Smoother.GetSpeed();
	IdleTime += DeltaTime;
	Layers.Reset();
	bool bPhaseAdvanced = false;
	float Total = 0.f;
	for (FTrack& Track : Tracks)
	{
		const FDinkCreatureRole& Row = Binding.Roles[Track.Role];
		const FDinkCreatureLoadedRole& Loaded = Class->Roles[Track.Role];
		// Eased weights: a linear cross-fade of two poses shows its start and end as a kink.
		const float W = FMath::SmoothStep(0.f, 1.f, Track.Weight);
		if (W <= 0.f) continue;
		if (Row.bLocomotion)
		{
			const FDinkCreatureLoadedLocomotion& Set = Loaded.Locomotion;
			float Idle = 1.f, Cycles = 0.f;
			TArray<float, TInlineAllocator<4>> Weights;
			DinkCreatureClass::SolveGaits(Speed, Binding.StationarySpeedCmS, Set.Speeds, Set.Strides, Idle, Weights, Cycles);
			if (!bPhaseAdvanced && !Track.bFadingOut)
			{
				// Distance over stride: the cycle advances exactly as far as the ground passed under the body.
				bPhaseAdvanced = true;
				CyclesPerSecond = Cycles;
				Phase = FMath::Fmod(Phase + Cycles * DeltaTime, 12.f);
			}
			if (Idle > 0.f && Set.Idle)
			{
				Layers.Add({ Set.Idle, FMath::Fmod(IdleTime, FMath::Max(Set.Idle->GetPlayLength(), 0.01f)), W * Idle });
				Total += W * Idle;
			}
			for (int32 Gait = 0; Gait < Set.Gaits.Num(); ++Gait)
			{
				if (Weights[Gait] <= 0.f) continue;
				const float Held = FMath::Max(Set.Cycles[Gait], 1.f);
				Layers.Add({ Set.Gaits[Gait], FMath::Fmod(Phase, Held) / Held * Set.Gaits[Gait]->GetPlayLength(), W * Weights[Gait] });
				Total += W * Weights[Gait];
			}
		}
		else if (Loaded.Clip)
		{
			const float Length = FMath::Max(Loaded.Clip->GetPlayLength(), 0.01f);
			Track.Time += DeltaTime * Track.Rate;
			Track.Time = Row.bLoop ? FMath::Fmod(Track.Time, Length) : FMath::Min(Track.Time, Length - 0.001f);
			Layers.Add({ Loaded.Clip, Track.Time, W });
			Total += W;
		}
	}
	if (!bPhaseAdvanced) CyclesPerSecond = 0.f;
	if (Total > KINDA_SMALL_NUMBER) for (FDinkCreaturePoseLayer& Layer : Layers) Layer.Weight /= Total;
	if (UDinkCreatureAnimInstance* Animation = Cast<UDinkCreatureAnimInstance>(GetAnimInstance())) Animation->SetLayers(Layers);
}

void UDinkCreatureClassComponent::Present(float DeltaTime)
{
	const AActor* Owner = GetOwner();
	if (!Class.IsValid() || !Owner) return;
	const FDinkCreatureClassBinding& Binding = Class->Binding;
	if (Owner->IsHidden())
	{
		bPlaced = false; // an inactive sprite: when it comes back it stands where it is, without a slide from its old place
		return;
	}
	const FVector Target = Owner->GetActorLocation() + FVector(0.0, 0.0, GroundOffset);
	if (!bPlaced)
	{
		bPlaced = true;
		Smoother.Reset(Target, TargetYaw);
	}
	// A sprite that walks has turned, whatever its direction number says.
	if (bHasSprite && !bFollowDir && Smoother.GetSpeed() > Binding.StationarySpeedCmS)
	{
		bFollowDir = true;
		if (Sprite.bHasFacing) TargetYaw = Sprite.FacingYawDeg;
	}
	// Steady pixel steps become steady motion, starts and stops short ramps; the body trails the sprite by speed x
	// smooth time and never moves faster than the sprite does. A jump beyond the warp distance takes the body along.
	Shown = Smoother.Update(Target, TargetYaw, DeltaTime);
	const float Yaw = Smoother.GetYaw();
	const double Scale = Binding.Scale * SizePercent / 100.0;
	const FVector Location = Shown + FRotator(0.0, Yaw, 0.0).RotateVector(Binding.OffsetCm * Scale);
	SetWorldLocationAndRotation(Location, FRotator(Binding.RotationDeg.X, Yaw + Binding.RotationDeg.Y, Binding.RotationDeg.Z));
	SetWorldScale3D(FVector(Scale));
	BuildLayers(DeltaTime);
	PresentGore(DeltaTime);
}

void UDinkCreatureClassComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Present(DeltaTime);
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
}
