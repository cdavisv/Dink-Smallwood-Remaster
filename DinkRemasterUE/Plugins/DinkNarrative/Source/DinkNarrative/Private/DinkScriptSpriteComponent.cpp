#include "DinkScriptSpriteComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

UDinkScriptSpriteComponent* UDinkScriptSpriteComponent::FindOrAdd(AActor* Actor)
{
	if (!Actor)
	{
		return nullptr;
	}
	if (UDinkScriptSpriteComponent* Existing = Actor->FindComponentByClass<UDinkScriptSpriteComponent>())
	{
		return Existing;
	}
	UDinkScriptSpriteComponent* Comp = NewObject<UDinkScriptSpriteComponent>(Actor, TEXT("DinkScriptSprite"));
	Actor->AddInstanceComponent(Comp);
	Comp->RegisterComponent();
	return Comp;
}

ADinkScriptSpriteActor::ADinkScriptSpriteActor()
{
	PrimaryActorTick.bCanEverTick = false;
	Marker = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Marker"));
	RootComponent = Marker;
	Marker->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Marker->SetRelativeScale3D(FVector(0.3f, 0.3f, 0.6f));
	// A hard reference, so the engine's basic cylinder is cooked with the game.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (Cylinder.Succeeded())
	{
		Marker->SetStaticMesh(Cylinder.Object);
	}
	Sprite = CreateDefaultSubobject<UDinkScriptSpriteComponent>(TEXT("DinkScriptSprite"));
}
