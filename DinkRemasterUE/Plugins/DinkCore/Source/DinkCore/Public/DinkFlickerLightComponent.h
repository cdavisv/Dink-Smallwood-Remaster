#pragma once

#include "CoreMinimal.h"
#include "Components/PointLightComponent.h"
#include "DinkFlickerLightComponent.generated.h"

/**
 * Firelight: a point light whose intensity wavers around its base value, as the light of an open fire does.
 * Presentation only (families.json "effect_light_flicker"); nothing in the simulation reads it.
 */
UCLASS(ClassGroup = (Dink), HideCategories = (Activation, Cooking, Collision))
class DINKCORE_API UDinkFlickerLightComponent : public UPointLightComponent
{
	GENERATED_BODY()

public:
	UDinkFlickerLightComponent();

	/** Base intensity (the light's own unit), the part of it that wavers (0 = steady) and a phase so two fires differ. */
	void SetFlicker(float InBaseIntensity, float InDepth, float InPhase);

	/** The factor at a time: three sines of unrelated periods, always within [1 - Depth, 1 + Depth]. */
	static float Factor(double TimeSeconds, float Depth, float Phase);

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	float BaseIntensity = 0.f;
	float Depth = 0.f;
	float Phase = 0.f;
};
