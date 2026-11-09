#include "Greybox/DinkWarpComponent.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "DinkCollision.h"
#include "DinkCoreModule.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Misc/ScopeExit.h"

UDinkWarpComponent::UDinkWarpComponent()
{
	SetCollisionProfileName(DinkCollision::ProfileWarpTrigger);
	SetGenerateOverlapEvents(true);
	SetCanEverAffectNavigation(false);
	ShapeColor = FColor(255, 0, 255);
	bHiddenInGame = true;
	SetLineThickness(2.f);
}

void UDinkWarpComponent::BeginPlay()
{
	Super::BeginPlay();
	OnComponentBeginOverlap.AddDynamic(this, &UDinkWarpComponent::HandleBeginOverlap);
    OnComponentEndOverlap.AddDynamic(this, &UDinkWarpComponent::HandleEndOverlap);
}

void UDinkWarpComponent::HandleBeginOverlap(UPrimitiveComponent*, AActor* OtherActor, UPrimitiveComponent*, int32, bool, const FHitResult&)
{
	APawn* Pawn = Cast<APawn>(OtherActor);
	if (Pawn && Pawn->IsPlayerControlled())
	{
		// The original warps Dink only when his own walking (or a script move that does not skip hardness) pushes into the warp's
		// hardness (special_block, dink.cpp D:15337). `move(1, dir, stop, 1)` ignores hardness and never triggers one: s2-culg.c puts
		// Dink at y 480 and walks him up with nohard 1 through the exit door's warp (S066_P16 at y 439) to y 353. A move with nohard 0
		// does (s1-h1-s.c walks him out of the burning house into the door that way).
		const UDinkGreyboxSubsystem* Greybox = GetWorld() ? GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
		if (Greybox && Greybox->WarpSuppressed && Greybox->WarpSuppressed(Pawn))
		{
			return;
		}
        // Arrival can overlap the return door during the warp guard/cooldown. Keep
        // the initial approach direction so deliberate movement past the centre is
        // not mistaken for moving away. Nohard1 never arms this retry state.
        if (bTriggerEnabled && TriggerMode==TEXT("walk_in") && (Kind==TEXT("door") || Kind==TEXT("exit")))
        {
            for (auto It=RetryApproachDirections.CreateIterator();It;++It)
                if (!It.Key().IsValid()) It.RemoveCurrent();
            RetryApproachDirections.Add(Pawn,(GetComponentLocation()-Pawn->GetActorLocation()).GetSafeNormal2D());
        }
		TryWarp(Pawn);
	}
}

void UDinkWarpComponent::HandleEndOverlap(UPrimitiveComponent*,AActor* OtherActor,UPrimitiveComponent*,int32)
{
    if (APawn* Pawn=Cast<APawn>(OtherActor)) RetryApproachDirections.Remove(Pawn);
}

FVector UDinkWarpComponent::GetRetryApproachDirection(const APawn* Pawn) const
{
    if (!Pawn) return FVector::ZeroVector;
    if (const FVector* Direction=RetryApproachDirections.Find(Pawn)) return *Direction;
    return (GetComponentLocation()-Pawn->GetActorLocation()).GetSafeNormal2D();
}

bool UDinkWarpComponent::TryWarp(APawn* Pawn)
{
	if (!Pawn || !bTriggerEnabled)
	{
		return false;
	}
	UWorld* World = GetWorld();
	UDinkGreyboxSubsystem* Greybox = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
	if (Greybox && !Greybox->BeginWarp(Pawn))
	{
		return false;
	}
	// TeleportTo updates overlaps synchronously. Guard the pawn before moving it so the
	// destination's return trigger cannot warp it back before NotifyWarped records cooldown.
	ON_SCOPE_EXIT { if (Greybox) { Greybox->EndWarp(Pawn); } };
	float HalfHeight = 0.f;
	if (const UCapsuleComponent* Capsule = Pawn->FindComponentByClass<UCapsuleComponent>())
	{
		HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
	}
	const FVector Target = DestLocation + FVector(0.0, 0.0, HalfHeight + 2.0);
	const bool bMoved = Pawn->TeleportTo(Target, FRotator(0.0, Pawn->GetActorRotation().Yaw, 0.0));
	UE_LOG(LogDink, Log, TEXT("Warp %s (%s) SCR_%03d -> SCR_%03d (%.0f, %.0f): %s"), *WarpId, *Kind.ToString(), SourceScreen,
		DestScreen, DestMapPixel.X, DestMapPixel.Y, bMoved ? TEXT("moved") : TEXT("blocked at destination"));
	if (bMoved && Greybox)
	{
		Greybox->NotifyWarped(Pawn, *this);
	}
	return bMoved;
}
