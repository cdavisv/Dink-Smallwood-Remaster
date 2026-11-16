#include "DinkFloatingNumbers.h"
#include "Components/TextRenderComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "HAL/IConsoleManager.h"

namespace
{
	TAutoConsoleVariable<int32> CVarFloatingNumbers(TEXT("dink.FloatingNumbers"), 1,
		TEXT("1: hits on monsters show the damage and kills the experience as rising numbers, as the original did (draw_damage, add_exp); 0: off."));
	TAutoConsoleVariable<float> CVarFloatingNumberSize(TEXT("dink.FloatingNumbers.SizeCm"), 34.f,
		TEXT("World height of a floating number's glyphs, cm."));

	FVector CameraLocation(const UWorld* World, const FVector& Fallback)
	{
		const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		return PC && PC->PlayerCameraManager ? PC->PlayerCameraManager->GetCameraLocation() : Fallback + FVector(-500, 0, 300);
	}
}

bool UDinkFloatingNumbers::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId UDinkFloatingNumbers::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkFloatingNumbers, STATGROUP_Tickables);
}

void UDinkFloatingNumbers::Show(const FVector& At, int32 Value, EDinkFloatingNumber Kind)
{
	UWorld* World = GetWorld();
	if (!World || Value <= 0 || CVarFloatingNumbers.GetValueOnGameThread() == 0)
	{
		return;
	}
	FActorSpawnParameters Params;
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	const FVector Start = At + FVector(0, 0, Kind == EDinkFloatingNumber::Experience ? ExperienceLiftCm : 0.f);
	AActor* Actor = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform(Start), Params);
	if (!Actor)
	{
		return;
	}
	const float Size = FMath::Max(4.f, CVarFloatingNumberSize.GetValueOnGameThread());
	auto MakeText = [&](const TCHAR* Name, const FColor& Colour, bool bRoot) -> UTextRenderComponent*
	{
		UTextRenderComponent* T = NewObject<UTextRenderComponent>(Actor, Name);
		T->SetMobility(EComponentMobility::Movable);
		T->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		T->SetCastShadow(false);
		T->SetHorizontalAlignment(EHTA_Center);
		T->SetVerticalAlignment(EVRTA_TextCenter);
		T->SetWorldSize(Size);
		T->SetTextRenderColor(Colour);
		T->SetText(FText::AsNumber(Value));
		if (bRoot) Actor->SetRootComponent(T);
		else T->SetupAttachment(Actor->GetRootComponent());
		T->RegisterComponent();
		Actor->AddInstanceComponent(T);
		return T;
	};
	// 1997: white damage (font colour 15), yellow experience (14: 255, 255, 2), over a half-black box (bgColor 0,0,0,150).
	UTextRenderComponent* Text = MakeText(TEXT("Number"), Kind == EDinkFloatingNumber::Experience ? FColor(255, 255, 2) : FColor(255, 255, 255), true);
	UTextRenderComponent* Shadow = MakeText(TEXT("Shadow"), FColor(0, 0, 0), false);
	// The shadow sits a little behind and below the number, as seen from the camera (set each tick with the facing).
	FLive L;
	L.Actor = Actor; L.Text = Text; L.Shadow = Shadow; L.Start = Start;
	Live.Add(L);
	Tick(0.f);
}

FString UDinkFloatingNumbers::NewestText() const
{
	const UTextRenderComponent* T = Live.Num() ? Live.Last().Text.Get() : nullptr;
	return T ? T->Text.ToString() : FString();
}

void UDinkFloatingNumbers::Tick(float DeltaTime)
{
	UWorld* World = GetWorld();
	for (int32 I = Live.Num() - 1; I >= 0; --I)
	{
		FLive& L = Live[I];
		L.Age += DeltaTime;
		AActor* Actor = L.Actor.Get();
		if (!Actor || L.Age >= LifeSeconds)
		{
			if (Actor) Actor->Destroy();
			Live.RemoveAt(I);
			continue;
		}
		// speed 1, my -1: a steady rise for the whole second.
		const FVector At = L.Start + FVector(0, 0, RiseCm * (L.Age / LifeSeconds));
		const FVector ToCamera = (CameraLocation(World, At) - At).GetSafeNormal();
		const FRotator Facing = ToCamera.Rotation();
		Actor->SetActorLocationAndRotation(At, Facing);
		if (UTextRenderComponent* Shadow = L.Shadow.Get())
			Shadow->SetRelativeLocation(FVector(-1.5f, 1.5f, -1.5f) * (Shadow->WorldSize / 34.f) * 2.f);
	}
}

void UDinkFloatingNumbers::Deinitialize()
{
	for (FLive& L : Live)
		if (AActor* Actor = L.Actor.Get()) Actor->Destroy();
	Live.Reset();
	Super::Deinitialize();
}
