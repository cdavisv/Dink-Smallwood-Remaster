#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkWarpComponent.h"
#include "DinkCollision.h"
#include "DinkOriginComponent.h"
#include "DinkInstanceOriginsComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "UObject/UObjectIterator.h"

namespace
{
TAutoConsoleVariable<int32> CVarDinkGreyboxBlockers(TEXT("dink.GreyboxBlockers"), 0,
	TEXT("Show generated hardness presentation prisms (0 default off, 1 debug only); never changes collision."));
FAutoConsoleVariableSink DebugBlockerSink(FConsoleCommandDelegate::CreateLambda([]
{
	static int32 Previous = 0;
	const int32 Value = CVarDinkGreyboxBlockers.GetValueOnGameThread();
	if (Value == Previous) return;
	Previous = Value;
	for (TObjectIterator<ADinkGreyboxScreen> It; It; ++It)
		if (IsValid(*It) && It->GetWorld() && It->GetWorld()->IsGameWorld()) It->RefreshDebugBlockers();
}));
}

ADinkPlaceholderActor::ADinkPlaceholderActor()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent->SetMobility(EComponentMobility::Static);
	Card = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Card"));
	Card->SetupAttachment(RootComponent);
	Card->SetMobility(EComponentMobility::Static);
	Card->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Card->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
	Card->SetCanEverAffectNavigation(false);
	Card->SetGenerateOverlapEvents(false);
	Origin = CreateDefaultSubobject<UDinkOriginComponent>(TEXT("Origin"));
}

void ADinkPlaceholderActor::BeginPlay()
{
	Super::BeginPlay();
	if (Vision != 0)
	{
		if (UDinkGreyboxSubsystem* Greybox = GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>())
		{
			Greybox->RegisterVisionPlaceholder(this);
		}
	}
	// The original loads every screen with &vision = 0 until a script changes it.
	ApplyScreenVision(0);
}

void ADinkPlaceholderActor::ApplyScreenVision(int32 ScreenVision)
{
	const bool bPresent = Vision == 0 || Vision == ScreenVision;
	SetActorHiddenInGame(!bPresent);
	SetActorEnableCollision(bPresent);
}

ADinkWarpPlaceholderActor::ADinkWarpPlaceholderActor()
{
	Warp = CreateDefaultSubobject<UDinkWarpComponent>(TEXT("Warp"));
	Warp->SetupAttachment(RootComponent);
	Warp->SetMobility(EComponentMobility::Static);
}

ADinkScriptWarpActor::ADinkScriptWarpActor()
{
	PrimaryActorTick.bCanEverTick = false;
	Warp = CreateDefaultSubobject<UDinkWarpComponent>(TEXT("Warp"));
	Warp->SetMobility(EComponentMobility::Static);
	RootComponent = Warp;
}

ADinkGreyboxScreen::ADinkGreyboxScreen()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent->SetMobility(EComponentMobility::Static);

	Visual = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Visual"));
	Visual->SetupAttachment(RootComponent);
	Visual->SetMobility(EComponentMobility::Static);
	Visual->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
	Visual->SetCanEverAffectNavigation(false);
	Visual->SetGenerateOverlapEvents(false);

	DebugBlockers = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DebugBlockers"));
	DebugBlockers->SetupAttachment(RootComponent);
	DebugBlockers->SetMobility(EComponentMobility::Static);
	DebugBlockers->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
	DebugBlockers->SetCanEverAffectNavigation(false);
	DebugBlockers->SetGenerateOverlapEvents(false);
	DebugBlockers->SetHiddenInGame(true);
	DebugBlockers->SetCastShadow(false);
	DebugBlockers->SetCastHiddenShadow(false);

	CollisionSolid = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("CollisionSolid"));
	CollisionSolid->SetupAttachment(RootComponent);
	CollisionSolid->SetMobility(EComponentMobility::Static);
	CollisionSolid->SetCollisionProfileName(DinkCollision::ProfileHardSolid);
	CollisionSolid->SetHiddenInGame(true);
	CollisionSolid->SetVisibility(false);
	CollisionSolid->SetCastShadow(false);
	CollisionSolid->SetGenerateOverlapEvents(false);

	CollisionLow = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("CollisionLow"));
	CollisionLow->SetupAttachment(RootComponent);
	CollisionLow->SetMobility(EComponentMobility::Static);
	CollisionLow->SetCollisionProfileName(DinkCollision::ProfileHardLow);
	CollisionLow->SetHiddenInGame(true);
	CollisionLow->SetVisibility(false);
	CollisionLow->SetCastShadow(false);
	CollisionLow->SetGenerateOverlapEvents(false);

	InstanceOrigins = CreateDefaultSubobject<UDinkInstanceOriginsComponent>(TEXT("InstanceOrigins"));
}

void ADinkGreyboxScreen::BeginPlay()
{
	Super::BeginPlay();
	RefreshDebugBlockers();
}

void ADinkGreyboxScreen::RefreshDebugBlockers()
{
	DebugBlockers->SetHiddenInGame(CVarDinkGreyboxBlockers.GetValueOnGameThread() == 0);
}
