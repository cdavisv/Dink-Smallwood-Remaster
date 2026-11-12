#include "DinkEarlyPostureAnimInstance.h"
#include "DinkFactSubsystem.h"
#include "DinkPlayerActionComponent.h"
#include "DinkStatsComponent.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"

float UDinkEarlyPostureAnimInstance::TargetWeight(int32 Story, bool bAllowed, bool bAttacking, bool bAirborne)
{
    if (!bAllowed) return 0.f;
    // Timid in Stonebrook; later progress relaxes the pose without changing quest facts.
    const float Mood = Story <= 2 ? 1.f : (Story < 7 ? .7f : .3f);
    return Mood * (bAttacking ? .35f : (bAirborne ? .5f : 1.f));
}

void UDinkEarlyPostureAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    if (DeltaSeconds <= SMALL_NUMBER) return;
    const ACharacter* Hero = Cast<ACharacter>(TryGetPawnOwner());
    if (!Hero) { PostureWeight=0.f; bHasPreviousLocation=false; return; }
    const FVector Position=Hero->GetActorLocation();
    const bool Teleported=!bHasPreviousLocation || FVector::DistSquared(Position,PreviousLocation)>FMath::Square(200.);
    PreviousLocation=Position; bHasPreviousLocation=true;
    const AController* Controller=Hero->GetController();
    const UDinkStatsComponent* Stats=Hero->FindComponentByClass<UDinkStatsComponent>();
    const UDinkPlayerActionComponent* Action=Hero->FindComponentByClass<UDinkPlayerActionComponent>();
    const UGameInstance* GI=Hero->GetGameInstance();
    const UDinkFactSubsystem* Facts=GI ? GI->GetSubsystem<UDinkFactSubsystem>() : nullptr;
    const bool Allowed=Controller && !Controller->IsMoveInputIgnored() && (!Stats || !Stats->IsDead());
    const float Target=TargetWeight(Facts ? Facts->GetFact(TEXT("story")) : 0,Allowed,
        Action && Action->IsActionActive(),Hero->GetCharacterMovement()->IsFalling());
    // A cutscene/death or observed warp drops the transient pose immediately.
    PostureWeight=(!Allowed || Teleported) ? 0.f : FMath::FInterpTo(PostureWeight,Target,DeltaSeconds,5.f);
}
