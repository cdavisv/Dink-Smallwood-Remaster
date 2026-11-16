#include "DinkBloodPresenter.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkStorySubsystem.h"
#include "Components/DecalComponent.h"
#include "Components/SceneComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInterface.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

static TAutoConsoleVariable<int32> CVarDinkHitBlood(TEXT("dink.HitBlood"), 1,
	TEXT("1 (default): a damaging hit leaves the original's blood on the ground until the screen changes (random_blood, dink.cpp:6675). 0: off."));

bool UDinkBloodPresenter::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId UDinkBloodPresenter::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkBloodPresenter, STATGROUP_Tickables);
}

void UDinkBloodPresenter::Deinitialize()
{
	Clear();
	Super::Deinitialize();
}

void UDinkBloodPresenter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (!FApp::CanEverRender() || CVarDinkHitBlood.GetValueOnGameThread() == 0) return;
	Present(DeltaTime);
}

int32 UDinkBloodPresenter::SpurtSequence(int32 BloodSeq, int32 BloodNum, uint32 Hash)
{
	if (BloodSeq > 0 && BloodNum > 0) return BloodSeq + int32(Hash % uint32(BloodNum));
	return 187 + int32(Hash % 3u);
}

double UDinkBloodPresenter::DecalSideCm(int32 WidthPx, int32 HeightPx, double InCmPerPx, double InMargin)
{
	return double(FMath::Max(WidthPx, HeightPx)) * InCmPerPx * FMath::Max(1.0, InMargin);
}

void UDinkBloodPresenter::LoadConfig()
{
	bConfigLoaded = true;
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Environment/environment.json")))
		|| !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid()) return;
	const TSharedPtr<FJsonObject>* Row = nullptr;
	if (!Root->TryGetObjectField(TEXT("hit_blood"), Row) || !Row) return;
	const TArray<TSharedPtr<FJsonValue>>* Paths = nullptr;
	if ((*Row)->TryGetArrayField(TEXT("materials"), Paths) && Paths)
	{
		for (const TSharedPtr<FJsonValue>& V : *Paths)
		{
			const FString Path = V->AsString();
			int32 Dot = INDEX_NONE;
			if (!Path.FindChar(TEXT('.'), Dot) || !FPackageName::DoesPackageExist(Path.Left(Dot))) continue;
			if (UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet)) Materials.Add(M);
		}
	}
	const TSharedPtr<FJsonObject>* Pictures = nullptr;
	if ((*Row)->TryGetObjectField(TEXT("last_frame_px"), Pictures) && Pictures)
	{
		for (const auto& Pair : (*Pictures)->Values)
		{
			const TArray<TSharedPtr<FJsonValue>>* Size = nullptr;
			if (Pair.Value->TryGetArray(Size) && Size && Size->Num() == 2)
				PictureSize.Add(FCString::Atoi(*FString(Pair.Key.ToView())), FIntPoint(int32((*Size)[0]->AsNumber()), int32((*Size)[1]->AsNumber())));
		}
	}
	(*Row)->TryGetNumberField(TEXT("cm_per_px"), CmPerPx);
	(*Row)->TryGetNumberField(TEXT("margin"), Margin);
	(*Row)->TryGetNumberField(TEXT("depth_cm"), DepthCm);
	(*Row)->TryGetNumberField(TEXT("spread_s"), SpreadS);
}

void UDinkBloodPresenter::Clear()
{
	for (UDecalComponent* C : Decals) if (C) C->DestroyComponent();
	Decals.Reset();
	Spreading.Reset();
}

int32 UDinkBloodPresenter::Present(float DeltaTime)
{
	UWorld* World = GetWorld();
	const UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
	const UDinkStorySubsystem* Story = Instance ? Instance->GetSubsystem<UDinkStorySubsystem>() : nullptr;
	const UDinkDirector* Director = Story ? Story->GetDirector() : nullptr;
	const UDinkGameplay* Game = Story ? Story->GetGameplay() : nullptr;
	if (!Director || !Game) return 0;
	if (!bConfigLoaded) LoadConfig();
	if (Materials.IsEmpty()) return 0;

	const int32 Screen = Director->GetCurrentScreen();
	const int32 ResetSerial = Director->GetSpriteResetSerial();
	if (Screen != SeenScreen || ResetSerial != SeenResetSerial)
	{
		// the original redraws the background when a screen is drawn: its blood goes with it
		const bool bFirst = SeenScreen < 0;
		SeenScreen = Screen;
		SeenResetSerial = ResetSerial;
		Clear();
		// blood of the screen before the change is not drawn on the new one
		if (!bFirst) SeenSerial = Game->GetBloodSerial();
	}

	// spread the young decals (the spurt animation's frames before the last)
	for (int32 I = 0; I < Decals.Num(); ++I)
	{
		FVector2D& S = Spreading[I];
		if (S.Y >= SpreadS || !Decals[I]) continue;
		S.Y += DeltaTime;
		const double A = SpreadS > 0.0 ? FMath::Clamp(S.Y / SpreadS, 0.0, 1.0) : 1.0;
		const double Half = S.X * (0.45 + 0.55 * A);
		Decals[I]->DecalSize = FVector(DepthCm, Half, Half);
		Decals[I]->MarkRenderStateDirty();
	}

	int32 Made = 0;
	for (const FDinkBloodEvent& E : Game->GetBloodEvents())
	{
		if (E.Serial <= SeenSerial) continue;
		SeenSerial = E.Serial;
		if (E.Screen != Screen) continue;
		FVector At;
		const FDinkSprite* Sprite = Director->FindSprite(E.Sprite);
		const AActor* Actor = Sprite ? Sprite->Actor.Get() : nullptr;
		if (Actor) At = Actor->GetActorLocation();
		else if (!Director->PixelToWorld(E.Screen, E.X, E.Y, At)) continue;
		// the ground under the hit sprite (its blood fell from the wound at y - 40 to the ground at its feet)
		FHitResult Hit;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkHitBlood), false);
		if (Actor) Params.AddIgnoredActor(Actor);
		if (const APawn* Pawn = Instance->GetFirstLocalPlayerController() ? Instance->GetFirstLocalPlayerController()->GetPawn() : nullptr) Params.AddIgnoredActor(Pawn);
		// start just above the sprite's ground point (script sprites stand 60 cm up), so a tree's crown is not taken for it
		if (World->LineTraceSingleByObjectType(Hit, At + FVector(0, 0, 100), At - FVector(0, 0, 400), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
			At.Z = Hit.ImpactPoint.Z;
		const uint32 Hash = HashCombine(GetTypeHash(E.Serial), HashCombine(GetTypeHash(E.Sprite), GetTypeHash(FMath::RoundToInt(E.X * 7 + E.Y))));
		// the spurt the simulation drew, as 1997 (the hash only stands in for events without one)
		const int32 Seq = E.Seq > 0 ? E.Seq : SpurtSequence(E.BloodSeq, E.BloodNum, Hash);
		const FIntPoint* Px = PictureSize.Find(Seq);
		const double Half = 0.5 * DecalSideCm(Px ? Px->X : 39, Px ? Px->Y : 56, CmPerPx, Margin);
		if (!Holder)
		{
			FActorSpawnParameters SP;
			SP.ObjectFlags |= RF_Transient;
			Holder = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, SP);
			if (!Holder) return Made;
			USceneComponent* Root = NewObject<USceneComponent>(Holder, TEXT("Root"));
			Holder->SetRootComponent(Root);
			Root->RegisterComponent();
#if WITH_EDITOR
			Holder->SetActorLabel(TEXT("DinkHitBlood"));
#endif
		}
		if (Decals.Num() >= MaxDecals)
		{
			if (Decals[0]) Decals[0]->DestroyComponent();
			Decals.RemoveAt(0);
			Spreading.RemoveAt(0);
		}
		UDecalComponent* C = NewObject<UDecalComponent>(Holder);
		C->SetupAttachment(Holder->GetRootComponent());
		C->SetDecalMaterial(Materials[int32((Hash >> 8) % uint32(Materials.Num()))]);
		C->DecalSize = FVector(DepthCm, Half * (SpreadS > 0.0 ? 0.45 : 1.0), Half * (SpreadS > 0.0 ? 0.45 : 1.0));
		C->SortOrder = 2;
		C->SetWorldLocationAndRotation(At, FRotator(-90.0, double((Hash >> 16) % 360u), 0.0));
		C->RegisterComponent();
		Decals.Add(C);
		Spreading.Add(FVector2D(Half, SpreadS > 0.0 ? 0.0 : SpreadS));
		++Made;
		UE_LOG(LogTemp, Verbose, TEXT("DINK BLOOD: sprite %d screen %d seq %d side %.0f cm at %s"), E.Sprite, Screen, Seq, 2.0 * Half, *At.ToCompactString());
	}
	return Made;
}
