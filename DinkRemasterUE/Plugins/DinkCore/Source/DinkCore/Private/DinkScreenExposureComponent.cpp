#include "DinkScreenExposureComponent.h"
#include "Components/PostProcessComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "TimerManager.h"

UDinkScreenExposureComponent::UDinkScreenExposureComponent()
{
    PrimaryComponentTick.bCanEverTick=false;
}
void UDinkScreenExposureComponent::DisableProvider()
{
    if (UPostProcessComponent* Exposure=Provider.Get())
    { Exposure->bEnabled=false; Exposure->bUnbound=false; }
}
void UDinkScreenExposureComponent::ConfigureExposure(UPostProcessComponent* Exposure,int32 ScreenNumber)
{
    if (bEndingPlay) return;
    DisableProvider();
    // Never claim another actor's postprocess provider.
    Provider=IsValid(Exposure) && Exposure->GetOwner()==GetOwner() ? Exposure : nullptr;
    OwnerScreenNumber=FMath::Max(ScreenNumber,0);
    DisableProvider();
    if (HasBegunPlay()) { RefreshOwnership(); StartRefreshTimer(); }
}
void UDinkScreenExposureComponent::BeginPlay()
{
    Super::BeginPlay();
    RefreshOwnership();
    StartRefreshTimer();
}
void UDinkScreenExposureComponent::StartRefreshTimer()
{
    if (bEndingPlay || !Provider.IsValid() || !Provider->IsRegistered()) return;
    if (UWorld* World=GetWorld())
        if (!World->GetTimerManager().IsTimerActive(OwnershipRefresh))
            // One provider-level refresh observes controller replacement without a
            // screen event. The bound is100ms of game time, not instantaneous.
            World->GetTimerManager().SetTimer(OwnershipRefresh,this,
                &UDinkScreenExposureComponent::RefreshOwnership,.1f,true);
}
bool UDinkScreenExposureComponent::HasOwnershipRefreshTimer() const
{
    const UWorld* World=GetWorld();
    return World && World->GetTimerManager().IsTimerActive(OwnershipRefresh);
}
void UDinkScreenExposureComponent::ScreenChanged(ADinkScreenVolume*) { RefreshOwnership(); }
void UDinkScreenExposureComponent::PawnChanged(APawn*) { RefreshOwnership(); }
void UDinkScreenExposureComponent::RefreshOwnership()
{
    if (bEndingPlay) return;
    if (!Provider.IsValid() || !Provider->IsRegistered())
    { DisableProvider(); ClearBindings(); return; }
    UWorld* World=GetWorld();
    UDinkGreyboxSubsystem* CurrentGrey=World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
    if (CurrentGrey!=Greybox.Get())
    {
        if (Greybox.IsValid()) Greybox->OnScreenChanged.Remove(ScreenHandle);
        ScreenHandle.Reset(); Greybox=CurrentGrey;
        if (CurrentGrey) ScreenHandle=CurrentGrey->OnScreenChanged.AddUObject(this,&UDinkScreenExposureComponent::ScreenChanged);
    }
    APlayerController* PC=World ? World->GetFirstPlayerController() : nullptr;
    if (PC!=BoundController.Get())
    {
        if (BoundController.IsValid()) BoundController->GetOnNewPawnNotifier().Remove(PawnHandle);
        PawnHandle.Reset(); BoundController=PC;
        if (PC) PawnHandle=PC->GetOnNewPawnNotifier().AddUObject(this,&UDinkScreenExposureComponent::PawnChanged);
    }
    const APawn* Pawn=IsValid(PC) && PC->IsLocalController() ? PC->GetPawn() : nullptr;
    const ADinkScreenVolume* Screen=CurrentGrey ? CurrentGrey->GetCurrentScreen() : nullptr;
    const bool Active=World && World->IsGameWorld() && OwnerScreenNumber>0 && IsValid(Pawn) &&
        IsValid(Screen) && Screen->bIndoor && Screen->ScreenNumber==OwnerScreenNumber &&
        CurrentGrey->FindScreenAt(Pawn->GetActorLocation())==Screen;
    Provider->bEnabled=Active;
    Provider->bUnbound=Active;
}
void UDinkScreenExposureComponent::ClearBindings()
{
    if (UWorld* World=GetWorld()) World->GetTimerManager().ClearTimer(OwnershipRefresh);
    if (Greybox.IsValid()) Greybox->OnScreenChanged.Remove(ScreenHandle);
    if (BoundController.IsValid()) BoundController->GetOnNewPawnNotifier().Remove(PawnHandle);
    ScreenHandle.Reset(); PawnHandle.Reset(); Greybox.Reset(); BoundController.Reset();
}
void UDinkScreenExposureComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    bEndingPlay=true;
    DisableProvider(); ClearBindings();
    Super::EndPlay(Reason);
}
