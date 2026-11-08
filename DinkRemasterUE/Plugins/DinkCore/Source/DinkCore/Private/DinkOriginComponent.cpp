#include "DinkOriginComponent.h"
#include "GameFramework/Actor.h"

UDinkOriginComponent::UDinkOriginComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
	bWantsInitializeComponent = false;
}

UDinkOriginComponent* UDinkOriginComponent::FindOnActor(const AActor* Actor)
{
	return Actor ? Actor->FindComponentByClass<UDinkOriginComponent>() : nullptr;
}
