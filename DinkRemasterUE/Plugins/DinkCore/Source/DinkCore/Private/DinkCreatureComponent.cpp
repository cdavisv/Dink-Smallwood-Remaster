#include "DinkCreatureComponent.h"
#include "DinkCreatureSubsystem.h"
#include "DinkCoreModule.h"
#include "DinkOriginComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/BlendSpace.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

UDinkCreatureComponent::UDinkCreatureComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	// The scripts and brains move the actor from the story subsystem, a tickable object that runs after the actor tick
	// groups: in the default group this component measured last frame's position (QA item A6).
	PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
	SetMobility(EComponentMobility::Movable);
	SetCollisionProfileName(TEXT("NoCollision"));
	SetGenerateOverlapEvents(false);
	SetCanEverAffectNavigation(false);
	VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
}
bool UDinkCreatureComponent::Configure(USkeletalMesh* Mesh, UBlendSpace* InLocomotion, UAnimSequence* InFeed,
									   const FDinkCreaturePresentation& InSettings)
{
	if (!Mesh || !InLocomotion || !Mesh->GetSkeleton() || Mesh->GetSkeleton() != InLocomotion->GetSkeleton() ||
		(InFeed && (InFeed->GetSkeleton() != Mesh->GetSkeleton() ||
					Mesh->GetRefSkeleton().FindBoneIndex(InSettings.FoodBone) == INDEX_NONE)) ||
		InSettings.FoodRadiusCm <= 0.f || InSettings.NominalWalkSpeedCmS <= 0.f)
		return false;
	Settings = InSettings;
	SetSkeletalMesh(Mesh);
	Locomotion = InLocomotion;
	Feed = InFeed;
	Motion.Reset();
	SpeedCmS = ShownSpeedCmS = 0.f;
	ConsumedFood.Reset();
	ResumeLocomotion();
	return true;
}
void UDinkCreatureComponent::ResumeLocomotion()
{
	bFeeding = false;
	SetAnimationMode(EAnimationMode::AnimationSingleNode);
	if (Locomotion)
		PlayAnimation(Locomotion, true);
}
bool UDinkCreatureComponent::CanFeedAt(const FVector& Food) const
{
	const AActor* Owner = GetOwner();
	if (!Feed || !Owner || Owner->IsHidden() || SpeedCmS > Settings.StationarySpeedCmS || Motion.GetImmediateSpeed() > Settings.StationarySpeedCmS ||
		GetBoneIndex(Settings.FoodBone) == INDEX_NONE)
		return false;
	const FVector Head = GetSocketLocation(Settings.FoodBone);
	const FVector Delta = Food - Head;
	return Delta.SizeSquared2D() <= FMath::Square(Settings.FoodRadiusCm) &&
		   (Delta.SizeSquared2D() < KINDA_SMALL_NUMBER ||
			FVector::DotProduct(Owner->GetActorForwardVector().GetSafeNormal2D(), Delta.GetSafeNormal2D()) >=
				Settings.FoodForwardDot);
}
bool UDinkCreatureComponent::TryFeed(AActor* FoodActor)
{
	if (!IsValid(FoodActor) || FoodActor->IsHidden() || bFeeding || ConsumedFood.Contains(FoodActor))
		return false;
	FVector Target = FoodActor->GetActorLocation();
	if (const UStaticMeshComponent* Visual =
			FoodActor->FindComponentByTag<UStaticMeshComponent>(TEXT("DinkAuthoredFood")))
	{
		if (!Visual->GetStaticMesh() || !Visual->GetVisibleFlag() || Visual->bHiddenInGame)
			return false;
		// Original script markers retain a root at ground+60. Reach and occlusion must
		// use the delivered visible kernels, not that invisible legacy actor origin.
		Target = Visual->Bounds.Origin;
	}
	if (!CanFeedAt(Target))
		return false;
	FHitResult Hit;
	FCollisionQueryParams Params(TEXT("DinkCreatureFood"), true, GetOwner());
	Params.AddIgnoredActor(FoodActor);
	if (GetWorld()->LineTraceSingleByChannel(Hit, GetSocketLocation(Settings.FoodBone), Target, ECC_Visibility, Params))
		return false;
	const UDinkOriginComponent* Origin = UDinkOriginComponent::FindOnActor(GetOwner());
	UE_LOG(LogDink, Log, TEXT("Creature feed %s food=%s target=%s"),
		   Origin ? *Origin->OriginId.ToString() : *GetOwner()->GetName(), *FoodActor->GetName(),
		   *Target.ToCompactString());
	ConsumedFood.Add(FoodActor);
	bFeeding = true;
	PlayAnimation(Feed, false);
	if (UAnimSingleNodeInstance* Animation = GetSingleNodeInstance())
		Animation->SetPlayRate(1.f);
	return true;
}
void UDinkCreatureComponent::TickComponent(float DeltaTime, ELevelTick TickType,
										   FActorComponentTickFunction* ThisTickFunction)
{
	if (AActor* Owner = GetOwner())
	{
		const FVector At = Owner->GetActorLocation();
		SpeedCmS = Motion.Update(At, DeltaTime);
		// The sprite moves in whole pixels (6.9 cm) on 60 Hz steps, so the speed over 100 ms steps by a pixel's worth from
		// frame to frame. The animation is driven by a quarter-second average of it; a stop is followed at once.
		const float Follow = SpeedCmS <= Settings.StationarySpeedCmS ? 1.f : 1.f - FMath::Exp(-FMath::Max(DeltaTime, 0.f) / 0.25f);
		ShownSpeedCmS = ShownSpeedCmS <= Settings.StationarySpeedCmS ? SpeedCmS : FMath::Lerp(ShownSpeedCmS, SpeedCmS, Follow);
		if (bFeeding && (Motion.GetImmediateSpeed() > Settings.StationarySpeedCmS || SpeedCmS > Settings.StationarySpeedCmS || !GetSingleNodeInstance() ||
						 !GetSingleNodeInstance()->IsPlaying()))
			ResumeLocomotion();
		if (!bFeeding)
		{
			if (UAnimSingleNodeInstance* Animation = GetSingleNodeInstance(); Animation && Locomotion)
			{
				FVector Position = FVector::ZeroVector;
				for (int32 Axis = 0; Axis < 3; ++Axis)
				{
					const FBlendParameter& Parameter = Locomotion->GetBlendParameter(Axis);
					if (Parameter.DisplayName.Contains(TEXT("Speed")))
						Position[Axis] = FMath::Clamp(ShownSpeedCmS, Parameter.Min, Parameter.Max);
				}
				Animation->SetBlendSpacePosition(Position);
				const float HighestNominal = FMath::Max(Settings.NominalWalkSpeedCmS, Settings.NominalRunSpeedCmS);
				Animation->SetPlayRate(FMath::Clamp(ShownSpeedCmS / FMath::Max(HighestNominal, 1.f), 1.f, 3.f));
			}
			if (const UDinkCreatureSubsystem* Creatures = GetWorld()->GetSubsystem<UDinkCreatureSubsystem>())
				for (const TWeakObjectPtr<AActor>& Food : Creatures->GetFoodActors())
					if (TryFeed(Food.Get()))
						break;
		}
		for (auto It = ConsumedFood.CreateIterator(); It; ++It)
			if (!It->IsValid())
				It.RemoveCurrent();
	}
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
}
