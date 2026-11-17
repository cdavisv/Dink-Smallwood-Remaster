#include "DinkFlickerLightComponent.h"
#include "Engine/World.h"

UDinkFlickerLightComponent::UDinkFlickerLightComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = false;
}

void UDinkFlickerLightComponent::SetFlicker(float InBaseIntensity, float InDepth, float InPhase)
{
	BaseIntensity = FMath::Max(InBaseIntensity, 0.f);
	Depth = FMath::Clamp(InDepth, 0.f, 0.9f);
	Phase = InPhase;
	SetComponentTickEnabled(Depth > 0.f && BaseIntensity > 0.f);
}

float UDinkFlickerLightComponent::Factor(double TimeSeconds, float Depth, float Phase)
{
	// a slow breath, a quicker waver and a fast shimmer; the weights sum to one
	const double T = TimeSeconds + double(Phase);
	const double Wave = 0.5 * FMath::Sin(T * 2.3) + 0.3 * FMath::Sin(T * 6.1 + 1.7) + 0.2 * FMath::Sin(T * 13.7 + 0.4);
	return float(1.0 + double(FMath::Clamp(Depth, 0.f, 0.9f)) * Wave);
}

void UDinkFlickerLightComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (const UWorld* World = GetWorld()) SetIntensity(BaseIntensity * Factor(World->GetTimeSeconds(), Depth, Phase));
}
