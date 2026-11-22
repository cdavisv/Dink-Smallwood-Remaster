// Landforms: the world heightfield of Scripts/export_landforms.py laid under the greybox (see DinkLandforms.h).

#include "DinkLandforms.h"
#include "DinkCollision.h"
#include "DinkCoreModule.h"
#include "DinkPlayerBlockers.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkWarpComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/ShapeComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "CoreGlobals.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "ProceduralMeshComponent.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

static TAutoConsoleVariable<int32> CVarDinkLandforms(TEXT("dink.Landforms"), 1,
	TEXT("Landforms (world heightfield, Content/Dink/Data/Environment/landforms.json): 1 on, 0 off (flat 1997 ground sheets). ")
	TEXT("Read at play start (or -DinkLandforms=0 on the command line); switching it during play is a review tool."));
static TAutoConsoleVariable<float> CVarDinkLandformsRadius(TEXT("dink.LandformsRadius"), 16000.f,
	TEXT("Landforms: the ground of screens within this many cm of the camera is drawn (beyond it the flat sheet stays)."));

const FName DinkLandforms::Tag(TEXT("DinkLandforms"));
const FName DinkLandforms::LiftedTag(TEXT("DinkLandformsLifted"));
const FName DinkLandforms::FlatTag(TEXT("DinkLandformsFlat"));

namespace
{
	/** The importer's water surface over a water fill (DinkGreyboxAssets.h WaterSurfaceHeightM). */
	constexpr double WaterSurfaceCm = 3.0;
	constexpr double CellCm = 5000.0;
	/** Mesh step in map pixels: near screens (around the player) and far ones. */
	constexpr int32 NearStepPx = 5;
	constexpr int32 FarStepPx = 10;

	float CatmullRom(float P0, float P1, float P2, float P3, float T)
	{
		const float T2 = T * T, T3 = T2 * T;
		return 0.5f * ((2.f * P1) + (-P0 + P2) * T + (2.f * P0 - 5.f * P1 + 4.f * P2 - P3) * T2 + (-P0 + 3.f * P1 - 3.f * P2 + P3) * T3);
	}

	bool IsShoreWater(const UMaterialInterface* Material)
	{
		const UMaterial* Base = Material ? Material->GetMaterial() : nullptr;
		return Base && Base->GetName() == TEXT("M_Env_WaterShore");
	}

	void MakeMovable(AActor* Actor)
	{
		TArray<USceneComponent*> Components;
		Actor->GetComponents<USceneComponent>(Components);
		for (USceneComponent* C : Components)
		{
			if (C->Mobility != EComponentMobility::Movable) C->SetMobility(EComponentMobility::Movable);
		}
	}
}

FString DinkLandforms::DefaultPath()
{
	return FPaths::ProjectContentDir() / TEXT("Dink/Data/Environment/landforms.json");
}

float DinkLandforms::SampleGrid(const TArray<float>& Grid, int32 W, int32 H, double GX, double GY)
{
	if (W < 2 || H < 2 || Grid.Num() < W * H) return 0.f;
	GX = FMath::Clamp(GX, 0.0, double(W - 1));
	GY = FMath::Clamp(GY, 0.0, double(H - 1));
	const int32 X1 = FMath::Min(int32(GX), W - 2), Y1 = FMath::Min(int32(GY), H - 2);
	const float TX = float(GX - X1), TY = float(GY - Y1);
	auto At = [&](int32 I, int32 J) { return Grid[FMath::Clamp(J, 0, H - 1) * W + FMath::Clamp(I, 0, W - 1)]; };
	float Rows[4];
	for (int32 K = 0; K < 4; ++K)
	{
		const int32 J = Y1 - 1 + K;
		Rows[K] = CatmullRom(At(X1 - 1, J), At(X1, J), At(X1 + 1, J), At(X1 + 2, J), TX);
	}
	return CatmullRom(Rows[0], Rows[1], Rows[2], Rows[3], TY);
}

void DinkLandforms::ConfigureGround(UPrimitiveComponent& Component)
{
	Component.SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Component.SetCollisionResponseToAllChannels(ECR_Ignore);
	Component.SetGenerateOverlapEvents(false);
}

bool DinkLandforms::IsActive(const UWorld* World)
{
	const UDinkLandformsSubsystem* Landforms = World ? World->GetSubsystem<UDinkLandformsSubsystem>() : nullptr;
	return Landforms && Landforms->IsActive();
}

bool DinkLandforms::IsPlayerPawn(const AActor* Actor)
{
	const APawn* Pawn = Cast<APawn>(Actor);
	return Pawn && Cast<APlayerController>(Pawn->GetController()) != nullptr;
}

float DinkLandforms::ActorLiftCm(const AActor* Actor)
{
	if (!Actor || !Actor->ActorHasTag(LiftedTag) || IsPlayerPawn(Actor)) return 0.f;
	return HeightCm(Actor->GetWorld(), FVector2D(Actor->GetActorLocation()), /*bBelowZero*/ false);
}

float DinkLandforms::GeometryLiftCm(const UPrimitiveComponent* Component)
{
	if (!Component || Component->ComponentHasTag(FlatTag)) return 0.f;
	return ActorLiftCm(Component->GetOwner());
}

namespace
{
	/** Invisible collision of a lifted actor: what the simulation and the player's capsule meet, never what is drawn. */
	bool StaysFlat(const UPrimitiveComponent& P)
	{
		if (P.ComponentHasTag(DinkLandforms::FlatTag)) return true;
		if (P.GetCollisionEnabled() == ECollisionEnabled::NoCollision) return false;
		return P.IsA<UShapeComponent>() || P.ComponentHasTag(DinkPlayerBlockers::Tag) || P.bHiddenInGame || !P.IsVisible();
	}
}

void DinkLandforms::KeepCollisionFlat(AActor& Actor, float BeforeCm, float AfterCm)
{
	TInlineComponentArray<UPrimitiveComponent*> Prims(&Actor);
	const USceneComponent* Root = Actor.GetRootComponent();
	TArray<UPrimitiveComponent*, TInlineAllocator<8>> Held;
	for (UPrimitiveComponent* P : Prims)
	{
		if (P && P != Root && StaysFlat(*P)) Held.Add(P);
	}
	for (UPrimitiveComponent* P : Held)
	{
		// a primitive under another held one moves with it
		bool bUnderHeld = false;
		for (const USceneComponent* Up = P->GetAttachParent(); Up && Up != Root && !bUnderHeld; Up = Up->GetAttachParent())
			bUnderHeld = Held.Contains(Up);
		if (bUnderHeld) continue;
		const bool bNew = !P->ComponentHasTag(FlatTag);
		const float Offset = bNew ? -AfterCm : BeforeCm - AfterCm;
		if (bNew) P->ComponentTags.Add(FlatTag);
		if (FMath::Abs(Offset) < 1e-4f) continue;
		if (P->Mobility != EComponentMobility::Movable) P->SetMobility(EComponentMobility::Movable);
		P->AddWorldOffset(FVector(0.0, 0.0, Offset), false, nullptr, ETeleportType::TeleportPhysics);
	}
}

bool DinkLandforms::GroundAt(const UWorld* World, const FVector2D& WorldXY, float& OutCm, FVector& OutNormal, bool bBelowZero)
{
	const UDinkLandformsSubsystem* Landforms = World ? World->GetSubsystem<UDinkLandformsSubsystem>() : nullptr;
	if (!Landforms || !Landforms->IsActive() || !Landforms->HasDataAt(WorldXY)) return false;
	auto H = [&](const FVector2D& P) { const float Z = Landforms->HeightCmAt(P); return bBelowZero ? Z : FMath::Max(Z, 0.f); };
	OutCm = H(WorldXY);
	constexpr double D = 10.0;
	const float DX = H(WorldXY + FVector2D(D, 0.0)) - H(WorldXY - FVector2D(D, 0.0));
	const float DY = H(WorldXY + FVector2D(0.0, D)) - H(WorldXY - FVector2D(0.0, D));
	OutNormal = FVector(-DX, -DY, 2.0 * D).GetSafeNormal();
	return true;
}

float DinkLandforms::HeightCm(const UWorld* World, const FVector2D& WorldXY, bool bBelowZero)
{
	const UDinkLandformsSubsystem* Landforms = World ? World->GetSubsystem<UDinkLandformsSubsystem>() : nullptr;
	const float H = Landforms ? Landforms->HeightCmAt(WorldXY) : 0.f;
	return bBelowZero ? H : FMath::Max(H, 0.f);
}

bool FDinkLandformsData::Load(const FString& Json, const TArray<uint8>& AtlasPng, FString& OutError)
{
	Screens.Reset();
	TSharedPtr<FJsonObject> Root;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid())
	{
		OutError = TEXT("landforms.json is not JSON");
		return false;
	}
	if (Root->GetStringField(TEXT("schema")) != TEXT("dink-landforms/1"))
	{
		OutError = TEXT("landforms.json: unknown schema");
		return false;
	}
	GridPx = int32(Root->GetNumberField(TEXT("grid_px")));
	const TArray<TSharedPtr<FJsonValue>>& Grid = Root->GetArrayField(TEXT("grid"));
	if (Grid.Num() != 2 || GridPx <= 0)
	{
		OutError = TEXT("landforms.json: bad grid");
		return false;
	}
	GridW = int32(Grid[0]->AsNumber());
	GridH = int32(Grid[1]->AsNumber());
	IImageWrapperModule& Module = FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
	TSharedPtr<IImageWrapper> Png = Module.CreateImageWrapper(EImageFormat::PNG);
	TArray64<uint8> Raw;
	if (!Png.IsValid() || !Png->SetCompressed(AtlasPng.GetData(), AtlasPng.Num()) || !Png->GetRaw(ERGBFormat::Gray, 16, Raw))
	{
		OutError = TEXT("landforms.png cannot be decoded as 16-bit greyscale");
		return false;
	}
	const int32 AW = int32(Png->GetWidth()), AH = int32(Png->GetHeight());
	if (Raw.Num() < int64(AW) * AH * 2)
	{
		OutError = TEXT("landforms.png is short");
		return false;
	}
	const uint16* Pixels = reinterpret_cast<const uint16*>(Raw.GetData());
	for (const TSharedPtr<FJsonValue>& Value : Root->GetArrayField(TEXT("screens")))
	{
		const TSharedPtr<FJsonObject> Row = Value->AsObject();
		FDinkLandformsScreen S;
		S.Screen = int32(Row->GetNumberField(TEXT("screen")));
		Row->TryGetStringField(TEXT("flat"), S.Flat);
		Row->TryGetBoolField(TEXT("wade"), S.bWade);
		const TArray<TSharedPtr<FJsonValue>>& Atlas = Row->GetArrayField(TEXT("atlas"));
		const TArray<TSharedPtr<FJsonValue>>& Corners = Row->GetArrayField(TEXT("corners"));
		if (Atlas.Num() != 2 || Corners.Num() != 4)
		{
			OutError = FString::Printf(TEXT("landforms.json: screen %d has no atlas cell or corners"), S.Screen);
			return false;
		}
		auto Corner = [&](int32 I)
		{
			const TArray<TSharedPtr<FJsonValue>>& P = Corners[I]->AsArray();
			return FVector2D(P[0]->AsNumber(), P[1]->AsNumber());
		};
		S.Corners.NW = Corner(0); S.Corners.NE = Corner(1); S.Corners.SW = Corner(2); S.Corners.SE = Corner(3);
		const int32 AX = int32(Atlas[0]->AsNumber()), AY = int32(Atlas[1]->AsNumber());
		if (AX < 0 || AY < 0 || AX + GridW > AW || AY + GridH > AH)
		{
			OutError = FString::Printf(TEXT("landforms.json: screen %d lies outside the atlas"), S.Screen);
			return false;
		}
		S.HeightsM.SetNumUninitialized(GridW * GridH);
		for (int32 J = 0; J < GridH; ++J)
			for (int32 I = 0; I < GridW; ++I)
				S.HeightsM[J * GridW + I] = float(int32(Pixels[(AY + J) * AW + AX + I]) - 32768) / 1000.f;
		for (const FVector2D& P : {S.Corners.NW, S.Corners.NE, S.Corners.SW, S.Corners.SE})
		{
			S.BoundsCm += P * DinkLayout::CentimetresPerMetre;
		}
		Screens.Add(S.Screen, MoveTemp(S));
	}
	return true;
}

float FDinkLandformsData::HeightMAtPixel(int32 Screen, double MapX, double MapY) const
{
	const FDinkLandformsScreen* S = Screens.Find(Screen);
	return S ? DinkLandforms::SampleGrid(S->HeightsM, GridW, GridH, MapX / GridPx, MapY / GridPx) : 0.f;
}

// ------------------------------------------------------------------------------------------------------- subsystem
bool UDinkLandformsSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UDinkLandformsSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	LoadData();
}

void UDinkLandformsSubsystem::Deinitialize()
{
	Built.Reset();
	Super::Deinitialize();
}

TStatId UDinkLandformsSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkLandformsSubsystem, STATGROUP_Tickables);
}

void UDinkLandformsSubsystem::LoadData()
{
	int32 Switch = CVarDinkLandforms.GetValueOnGameThread();
	const bool bExplicit = FParse::Value(FCommandLine::Get(), TEXT("DinkLandforms="), Switch);
	// Parity runs (automation tests, the packaged probe) keep the flat 1997 ground unless the command line asks for it:
	// the simulation must not depend on the presentation's ground.
	if (!bExplicit && (GIsAutomationTesting || FParse::Param(FCommandLine::Get(), TEXT("DinkProbeHold"))))
	{
		UE_LOG(LogDink, Display, TEXT("DINK LANDFORMS: off for an automation/parity run (-DinkLandforms=1 turns it on): flat ground sheets"));
		return;
	}
	if (Switch == 0)
	{
		UE_LOG(LogDink, Display, TEXT("DINK LANDFORMS: off (dink.Landforms 0 / -DinkLandforms=0): flat ground sheets"));
		return;
	}
	const FString Path = DinkLandforms::DefaultPath();
	FString Json, Error;
	TArray<uint8> Png;
	if (!FFileHelper::LoadFileToString(Json, *Path) || !FFileHelper::LoadFileToArray(Png, *(FPaths::GetPath(Path) / TEXT("landforms.png"))))
	{
		UE_LOG(LogDink, Display, TEXT("DINK LANDFORMS: no data at %s: flat ground sheets"), *Path);
		return;
	}
	if (!Data.Load(Json, Png, Error))
	{
		UE_LOG(LogDink, Warning, TEXT("DINK LANDFORMS: %s: flat ground sheets"), *Error);
		Data.Screens.Reset();
		return;
	}
	Cells.Reset();
	for (const TPair<int32, FDinkLandformsScreen>& Pair : Data.Screens)
	{
		const FBox2D& B = Pair.Value.BoundsCm;
		for (int32 X = FMath::FloorToInt32(B.Min.X / CellCm); X <= FMath::FloorToInt32(B.Max.X / CellCm); ++X)
			for (int32 Y = FMath::FloorToInt32(B.Min.Y / CellCm); Y <= FMath::FloorToInt32(B.Max.Y / CellCm); ++Y)
				Cells.FindOrAdd(FIntPoint(X, Y)).Add(Pair.Key);
	}
	bLoaded = true;
	bActive = true;
	UE_LOG(LogDink, Display, TEXT("DINK LANDFORMS: %d screens with height (%d x %d grid at %d px)"), Data.Screens.Num(), Data.GridW, Data.GridH, Data.GridPx);
}

int32 UDinkLandformsSubsystem::ScreenAt(const FVector2D& WorldXY, double& OutMapX, double& OutMapY) const
{
	const TArray<int32>* Candidates = Cells.Find(FIntPoint(FMath::FloorToInt32(WorldXY.X / CellCm), FMath::FloorToInt32(WorldXY.Y / CellCm)));
	if (!Candidates) return 0;
	const FVector2D Metres = WorldXY / DinkLayout::CentimetresPerMetre;
	for (const int32 Screen : *Candidates)
	{
		const FDinkLandformsScreen& S = Data.Screens.FindChecked(Screen);
		if (!S.BoundsCm.ExpandBy(1.0).IsInside(WorldXY)) continue;
		double X = 0.0, Y = 0.0;
		if (!DinkLayout::MetresToMapPixel(S.Corners, Metres, X, Y)) continue;
		if (X < -0.01 || X > 600.01 || Y < -0.01 || Y > 400.01) continue;
		OutMapX = X;
		OutMapY = Y;
		return Screen;
	}
	return 0;
}

float UDinkLandformsSubsystem::HeightCmAt(const FVector2D& WorldXY) const
{
	if (!bActive) return 0.f;
	double X = 0.0, Y = 0.0;
	const int32 Screen = ScreenAt(WorldXY, X, Y);
	return Screen ? Data.HeightMAtPixel(Screen, X, Y) * 100.f : 0.f;
}

bool UDinkLandformsSubsystem::HasDataAt(const FVector2D& WorldXY) const
{
	double X = 0.0, Y = 0.0;
	return bActive && ScreenAt(WorldXY, X, Y) != 0;
}

void UDinkLandformsSubsystem::SetDataForTest(FDinkLandformsData&& InData, bool bActivate)
{
	if (bActive) SetActive(false);
	Data = MoveTemp(InData);
	Cells.Reset();
	for (const TPair<int32, FDinkLandformsScreen>& Pair : Data.Screens)
	{
		const FBox2D& B = Pair.Value.BoundsCm;
		for (int32 X = FMath::FloorToInt32(B.Min.X / CellCm); X <= FMath::FloorToInt32(B.Max.X / CellCm); ++X)
			for (int32 Y = FMath::FloorToInt32(B.Min.Y / CellCm); Y <= FMath::FloorToInt32(B.Max.Y / CellCm); ++Y)
				Cells.FindOrAdd(FIntPoint(X, Y)).Add(Pair.Key);
	}
	bLoaded = Data.Screens.Num() > 0;
	if (bActivate && bLoaded) SetActive(true);
}

float UDinkLandformsSubsystem::HeightCmAtPixel(int32 Screen, double MapX, double MapY) const
{
	return bActive ? Data.HeightMAtPixel(Screen, MapX, MapY) * 100.f : 0.f;
}

ADinkGreyboxScreen* UDinkLandformsSubsystem::FindGreybox(int32 Screen) const
{
	if (const TWeakObjectPtr<ADinkGreyboxScreen>* Found = GreyboxByScreen.Find(Screen))
	{
		return Found->Get();
	}
	return nullptr;
}

void UDinkLandformsSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	GreyboxByScreen.Reset();
	for (TActorIterator<ADinkGreyboxScreen> It(&InWorld); It; ++It)
	{
		GreyboxByScreen.Add(It->ScreenNumber, *It);
	}
	if (bActive)
	{
		SnapPlacedActors(true);
	}
}

void UDinkLandformsSubsystem::SnapPlacedActors(bool bOn)
{
	UWorld* World = GetWorld();
	if (!World) return;
	if (!bOn)
	{
		for (const TPair<TWeakObjectPtr<AActor>, float>& Pair : ActorLift)
		{
			AActor* A = Pair.Key.Get();
			if (!A) continue;
			A->AddActorWorldOffset(FVector(0.0, 0.0, -Pair.Value), false, nullptr, ETeleportType::TeleportPhysics);
			DinkLandforms::KeepCollisionFlat(*A, Pair.Value, 0.f);
			A->Tags.Remove(DinkLandforms::LiftedTag);
		}
		for (const auto& Pair : DecorLift)
		{
			UInstancedStaticMeshComponent* ISM = Pair.Key.Get();
			if (!ISM) continue;
			for (int32 I = 0; I < Pair.Value.Num() && I < ISM->GetInstanceCount(); ++I)
			{
				FTransform T;
				ISM->GetInstanceTransform(I, T, true);
				T.AddToTranslation(FVector(0.0, 0.0, -Pair.Value[I]));
				ISM->UpdateInstanceTransform(I, T, true, false, true);
			}
			ISM->MarkRenderStateDirty();
		}
		ActorLift.Reset();
		DecorLift.Reset();
		bSnapped = false;
		return;
	}
	if (bSnapped) return;
	bSnapped = true;
	const double T0 = FPlatformTime::Seconds();
	int32 Actors = 0, Instances = 0;
	auto Lift = [&](AActor* A)
	{
		if (!A || ActorLift.Contains(A)) return;
		const FVector L = A->GetActorLocation();
		// as the director's sprites (DinkLandforms::ActorLiftCm): never below 0, only the player's drawn body wades
		const float H = FMath::Max(HeightCmAt(FVector2D(L)), 0.f);
		if (FMath::Abs(H) < 0.05f) return;
		MakeMovable(A);
		A->AddActorWorldOffset(FVector(0.0, 0.0, H), false, nullptr, ETeleportType::TeleportPhysics);
		// what the simulation and the player's capsule meet stays where it was: warp boxes, blockers, body shapes
		DinkLandforms::KeepCollisionFlat(*A, 0.f, H);
		A->Tags.AddUnique(DinkLandforms::LiftedTag);
		ActorLift.Add(A, H);
		++Actors;
	};
	// placements (props, NPCs, creatures, pickups, sprite warps) are drawn on the ground; script warp triggers are invisible
	// collision and stay where the 1997 sweeps meet them
	for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
	{
		if (Data.Screens.Contains(It->ScreenNumber)) Lift(*It);
	}
	// background decoration drawn as instances of the screen's greybox actor
	for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It)
	{
		if (!Data.Screens.Contains(It->ScreenNumber)) continue;
		Instances += LiftScreenDecor(**It);
	}
	UE_LOG(LogDink, Display, TEXT("DINK LANDFORMS: %d placement actors and %d decor instances set on the ground (%.0f ms)"), Actors, Instances,
		(FPlatformTime::Seconds() - T0) * 1000.0);
}

int32 UDinkLandformsSubsystem::LiftScreenDecor(ADinkGreyboxScreen& Screen)
{
	int32 Instances = 0;
	TInlineComponentArray<UInstancedStaticMeshComponent*> ISMs(&Screen);
	for (UInstancedStaticMeshComponent* ISM : ISMs)
	{
		if (!ISM || ISM->GetInstanceCount() == 0) continue;
		if (DecorLift.ContainsByPredicate([ISM](const auto& Pair) { return Pair.Key.Get() == ISM; })) continue;   // lifted before
		TArray<float> Lifts;
		Lifts.SetNumZeroed(ISM->GetInstanceCount());
		bool bAny = false;
		for (int32 I = 0; I < ISM->GetInstanceCount(); ++I)
		{
			FTransform T;
			ISM->GetInstanceTransform(I, T, true);
			// a card's base is its placement point: the card's own lift (offset_z) rides on the ground under its centre
			const float H = HeightCmAt(FVector2D(T.GetLocation()));
			if (FMath::Abs(H) < 0.05f) continue;
			if (!bAny && ISM->Mobility != EComponentMobility::Movable) ISM->SetMobility(EComponentMobility::Movable);
			bAny = true;
			T.AddToTranslation(FVector(0.0, 0.0, H));
			ISM->UpdateInstanceTransform(I, T, true, false, true);
			Lifts[I] = H;
			++Instances;
		}
		if (bAny)
		{
			ISM->MarkRenderStateDirty();
			DecorLift.Emplace(ISM, MoveTemp(Lifts));
		}
	}
	// the player-only blockers standing for decor instances are collision, not drawing: they stay on the flat floor
	return Instances;
}

int32 UDinkLandformsSubsystem::SnapScreenDecor(ADinkGreyboxScreen& Screen)
{
	// before the first snap SnapPlacedActors takes the whole world (this decor included)
	if (!bActive || !bSnapped || !Data.Screens.Contains(Screen.ScreenNumber)) return 0;
	const int32 Instances = LiftScreenDecor(Screen);
	// placements dressed now (family art parts and their player-only blockers made on a lifted actor): blockers back to flat
	for (const TPair<TWeakObjectPtr<AActor>, float>& Pair : ActorLift)
	{
		const ADinkPlaceholderActor* P = Cast<ADinkPlaceholderActor>(Pair.Key.Get());
		if (P && P->ScreenNumber == Screen.ScreenNumber) DinkLandforms::KeepCollisionFlat(*Pair.Key.Get(), Pair.Value, Pair.Value);
	}
	if (Instances > 0) UE_LOG(LogDink, Verbose, TEXT("DINK LANDFORMS: %d decor instances made later on SCR_%03d set on the ground"), Instances, Screen.ScreenNumber);
	return Instances;
}

bool UDinkLandformsSubsystem::BuildScreen(int32 Screen, bool bNear)
{
	const FDinkLandformsScreen* S = Data.Screens.Find(Screen);
	ADinkGreyboxScreen* Greybox = FindGreybox(Screen);
	UWorld* World = GetWorld();
	if (!S || !Greybox || !World || !Greybox->Visual || Skipped.Contains(Screen)) return false;
	// a screen an authored art manifest dresses hides its greybox ground and keeps its own (and stays flat in the data)
	if (Greybox->Visual->bHiddenInGame) { Skipped.Add(Screen); return false; }
	UStaticMeshComponent* Visual = Greybox->Visual;
	const int32 GroundSlot = FMath::Max(0, Visual->GetMaterialIndex(TEXT("Ground")));
	const int32 WaterSlot = Visual->GetMaterialIndex(TEXT("Water"));
	UMaterialInterface* Ground = Visual->GetMaterial(GroundSlot);
	UMaterialInterface* Water = WaterSlot != INDEX_NONE ? Visual->GetMaterial(WaterSlot) : nullptr;
	if (WaterSlot != INDEX_NONE && !IsShoreWater(Water))
	{
		// the flat sheet's water quads use a material that does not end on the shoreline by itself: keep the flat sheet
		UE_LOG(LogDink, Warning, TEXT("DINK LANDFORMS: screen %d keeps its flat ground: its water (%s) is not the shore water material"),
			Screen, *GetNameSafe(Water));
		Skipped.Add(Screen);
		return false;
	}

	FBuilt* Existing = Built.Find(Screen);
	const int32 Step = bNear ? NearStepPx : FarStepPx;
	if (Existing && Existing->Mesh.IsValid() && Existing->Step <= Step) return true;
	const double T0 = FPlatformTime::Seconds();

	AActor* Actor = Existing ? Existing->Actor.Get() : nullptr;
	const FVector Pivot = DinkLayout::MapPixelToUnreal(S->Corners, 300.0, 200.0);
	if (!Actor)
	{
		FActorSpawnParameters SP;
		SP.ObjectFlags |= RF_Transient;
		Actor = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform(Pivot), SP);
		if (!Actor) return false;
		Actor->Tags.Add(DinkLandforms::Tag);
		USceneComponent* Root = NewObject<USceneComponent>(Actor, TEXT("LandformsRoot"));
		Actor->SetRootComponent(Root);
		Root->RegisterComponent();
		Actor->SetActorLocation(Pivot);
	}
	UProceduralMeshComponent* Mesh = Existing ? Existing->Mesh.Get() : nullptr;
	if (!Mesh)
	{
		Mesh = NewObject<UProceduralMeshComponent>(Actor, TEXT("LandformsGround"));
		Mesh->SetupAttachment(Actor->GetRootComponent());
		Mesh->bUseAsyncCooking = false;
		Mesh->SetCanEverAffectNavigation(false);
		Mesh->SetGenerateOverlapEvents(false);
		Mesh->SetCastShadow(true);
		// drawn only: nothing collides with it, the player's capsule included (a visual height layer)
		DinkLandforms::ConfigureGround(*Mesh);
		Mesh->ComponentTags.Add(DinkLandforms::Tag);
		Mesh->RegisterComponent();
		Actor->AddInstanceComponent(Mesh);
	}

	const int32 NX = 600 / Step + 1, NY = 400 / Step + 1;
	TArray<FVector> Vertices;
	TArray<FVector2D> UVs;
	TArray<FVector> Normals;
	TArray<FProcMeshTangent> Tangents;
	TArray<int32> Triangles;
	Vertices.SetNumUninitialized(NX * NY);
	UVs.SetNumUninitialized(NX * NY);
	for (int32 J = 0; J < NY; ++J)
		for (int32 I = 0; I < NX; ++I)
		{
			const double X = I * Step, Y = J * Step;
			FVector P = DinkLayout::MapPixelToUnreal(S->Corners, X, Y) - Pivot;
			P.Z = Data.HeightMAtPixel(Screen, X, Y) * 100.0;
			Vertices[J * NX + I] = P;
			UVs[J * NX + I] = FVector2D(X / 600.0, Y / 400.0);
		}
	Normals.SetNumUninitialized(NX * NY);
	Tangents.SetNumUninitialized(NX * NY);
	for (int32 J = 0; J < NY; ++J)
		for (int32 I = 0; I < NX; ++I)
		{
			const FVector DX = Vertices[J * NX + FMath::Min(I + 1, NX - 1)] - Vertices[J * NX + FMath::Max(I - 1, 0)];
			const FVector DY = Vertices[FMath::Min(J + 1, NY - 1) * NX + I] - Vertices[FMath::Max(J - 1, 0) * NX + I];
			FVector N = FVector::CrossProduct(DX, DY).GetSafeNormal();
			if (N.Z < 0.0) N = -N;
			Normals[J * NX + I] = N;
			Tangents[J * NX + I] = FProcMeshTangent(DX.GetSafeNormal(), false);
		}
	Triangles.Reserve((NX - 1) * (NY - 1) * 6);
	for (int32 J = 0; J + 1 < NY; ++J)
		for (int32 I = 0; I + 1 < NX; ++I)
		{
			const int32 A = J * NX + I, B = A + 1, C = A + NX + 1, D = A + NX;
			// FMeshWriter::Quad of the importer: P0..P3 with cross(P1 - P0, P3 - P0) up -> (0, 2, 1), (0, 3, 2)
			if (FVector::CrossProduct(Vertices[B] - Vertices[A], Vertices[D] - Vertices[A]).Z >= 0.0)
				Triangles.Append({A, C, B, A, D, C});
			else
				Triangles.Append({A, B, C, A, C, D});
		}
	Mesh->ClearAllMeshSections();
	Mesh->CreateMeshSection_LinearColor(0, Vertices, Triangles, Normals, UVs, TArray<FLinearColor>(), Tangents, /*bCreateCollision*/ false);
	Mesh->SetMaterial(0, Ground);
	if (Water)
	{
		// the flat sheet's water: one quad at the importer's water height with the screen's shore material, which draws
		// water only where the terrain mask's alpha says so; the bed under it is now real ground below the surface
		TArray<FVector> WV;
		TArray<FVector2D> WU;
		const double Px[4][2] = {{0, 0}, {600, 0}, {600, 400}, {0, 400}};
		for (int32 K = 0; K < 4; ++K)
		{
			WV.Add(DinkLayout::MapPixelToUnreal(S->Corners, Px[K][0], Px[K][1], WaterSurfaceCm / 100.0) - Pivot);
			WU.Add(FVector2D(Px[K][0] / 600.0, Px[K][1] / 400.0));
		}
		TArray<int32> WT;
		if (FVector::CrossProduct(WV[1] - WV[0], WV[3] - WV[0]).Z >= 0.0) WT = {0, 2, 1, 0, 3, 2};
		else WT = {0, 1, 2, 0, 2, 3};
		const TArray<FVector> WN = {FVector::UpVector, FVector::UpVector, FVector::UpVector, FVector::UpVector};
		Mesh->CreateMeshSection_LinearColor(1, WV, WT, WN, WU, TArray<FLinearColor>(), TArray<FProcMeshTangent>(), false);
		Mesh->SetMaterial(1, Water);
	}
	Visual->SetVisibility(false);
	FBuilt& Record = Built.FindOrAdd(Screen);
	Record.Actor = Actor;
	Record.Mesh = Mesh;
	Record.Greybox = Greybox;
	Record.Step = Step;
	UE_LOG(LogDink, Verbose, TEXT("DINK LANDFORMS: screen %d ground %dx%d%s in %.1f ms"), Screen, NX, NY, bNear ? TEXT(" (near)") : TEXT(""),
		(FPlatformTime::Seconds() - T0) * 1000.0);
	return true;
}

void UDinkLandformsSubsystem::FreeScreen(int32 Screen)
{
	FBuilt Record;
	if (!Built.RemoveAndCopyValue(Screen, Record)) return;
	if (AActor* A = Record.Actor.Get()) A->Destroy();
	if (ADinkGreyboxScreen* G = Record.Greybox.Get())
	{
		if (G->Visual) G->Visual->SetVisibility(true);
	}
}

void UDinkLandformsSubsystem::EnsureAround(const FVector& WorldLocation)
{
	if (!bActive) return;
	double X = 0.0, Y = 0.0;
	const FVector2D At(WorldLocation);
	// the screen under the point and its eight neighbours (in world space: probe a ring a little wider than a screen)
	TSet<int32> Near;
	if (const int32 S = ScreenAt(At, X, Y)) Near.Add(S);
	for (int32 K = 0; K < 16; ++K)
	{
		const double A = K * UE_PI / 8.0;
		for (const double R : {1500.0, 3200.0})
		{
			if (const int32 S = ScreenAt(At + FVector2D(FMath::Cos(A), FMath::Sin(A)) * R, X, Y)) Near.Add(S);
		}
	}
	for (const int32 S : Near) BuildScreen(S, true);
}

void UDinkLandformsSubsystem::SetActive(bool bOn)
{
	if (!bLoaded || bOn == bActive) return;
	if (!bOn)
	{
		TArray<int32> Screens;
		Built.GetKeys(Screens);
		for (const int32 S : Screens) FreeScreen(S);
		SnapPlacedActors(false);
		bActive = false;
	}
	else
	{
		bActive = true;
		SnapPlacedActors(true);
	}
	UE_LOG(LogDink, Display, TEXT("DINK LANDFORMS: %s"), bActive ? TEXT("on") : TEXT("off"));
}

void UDinkLandformsSubsystem::Tick(float DeltaTime)
{
	UWorld* World = GetWorld();
	if (!World || !bLoaded) return;
	const bool bWant = CVarDinkLandforms.GetValueOnGameThread() != 0;
	if (bWant != bActive) SetActive(bWant);
	if (!bActive) return;
	APlayerController* PC = World->GetFirstPlayerController();
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	FVector Camera = Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector;
	if (PC && PC->PlayerCameraManager)
	{
		Camera = PC->PlayerCameraManager->GetCameraLocation();
	}
	const FVector Player = Pawn ? Pawn->GetActorLocation() : Camera;
	// the player's own screen and its neighbours at once (the capsule never stands on it: ADinkGreyboxCharacter draws him on it)
	EnsureAround(Player);
	// farther screens: drawn only, a few per frame, nearest first
	const double Radius = CVarDinkLandformsRadius.GetValueOnGameThread();
	TArray<TPair<double, int32>> Want;
	for (const TPair<int32, FDinkLandformsScreen>& Pair : Data.Screens)
	{
		const double D = FMath::Sqrt(Pair.Value.BoundsCm.ComputeSquaredDistanceToPoint(FVector2D(Camera)));
		if (D <= Radius && !Built.Contains(Pair.Key) && !Skipped.Contains(Pair.Key)) Want.Emplace(D, Pair.Key);
	}
	Want.Sort([](const TPair<double, int32>& A, const TPair<double, int32>& B) { return A.Key < B.Key; });
	for (int32 K = 0; K < Want.Num() && K < 3; ++K) BuildScreen(Want[K].Value, false);
	// the ground keeps the flat sheet's current materials (the environment tints the meadow once per world, maybe after we built)
	for (const TPair<int32, FBuilt>& Pair : Built)
	{
		UProceduralMeshComponent* Mesh = Pair.Value.Mesh.Get();
		const ADinkGreyboxScreen* G = Pair.Value.Greybox.Get();
		if (!Mesh || !G || !G->Visual) continue;
		UMaterialInterface* Ground = G->Visual->GetMaterial(FMath::Max(0, G->Visual->GetMaterialIndex(TEXT("Ground"))));
		if (Ground && Mesh->GetMaterial(0) != Ground) Mesh->SetMaterial(0, Ground);
	}
	// free what is far behind
	TArray<int32> Far;
	for (const TPair<int32, FBuilt>& Pair : Built)
	{
		const FDinkLandformsScreen* S = Data.Screens.Find(Pair.Key);
		if (S && FMath::Sqrt(S->BoundsCm.ComputeSquaredDistanceToPoint(FVector2D(Camera))) > Radius * 1.5 &&
			FMath::Sqrt(S->BoundsCm.ComputeSquaredDistanceToPoint(FVector2D(Player))) > 6000.0)
			Far.Add(Pair.Key);
	}
	for (const int32 S : Far) FreeScreen(S);
}

FString UDinkLandformsSubsystem::Audit(int32 MaxRows) const
{
	UWorld* World = GetWorld();
	if (!World || !bActive) return TEXT("DINK LANDFORMS AUDIT: landforms off");
	struct FRow { float Diff; FString Text; };
	TArray<FRow> Rows;
	int32 Checked = 0, Off = 0, Instances = 0, InstOff = 0;
	auto Check = [&](const FString& Name, int32 Screen, const FVector& Base, float ExpectLift)
	{
		const float Ground = FMath::Max(HeightCmAt(FVector2D(Base)), 0.f);   // actors are never drawn below 0
		const float Diff = float(Base.Z - ExpectLift) - Ground;
		return TPair<float, FString>(Diff, FString::Printf(TEXT("%s SCR_%03d base %.1f ground %.1f diff %+.1f cm"), *Name, Screen, Base.Z - ExpectLift, Ground, Diff));
	};
	// actors: their imported base was 0 above the flat sheet, so their base now must equal the ground under them; their
	// invisible collision must not have moved (visual layer: what the simulation meets stays on the 1997 floor)
	int32 Held = 0, Lifted = 0;
	for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
	{
		if (!Data.Screens.Contains(It->ScreenNumber)) continue;
		++Checked;
		TInlineComponentArray<UPrimitiveComponent*> Prims(*It);
		for (const UPrimitiveComponent* P : Prims)
		{
			if (!P || P->GetCollisionEnabled() == ECollisionEnabled::NoCollision) continue;
			if (P->ComponentHasTag(DinkLandforms::FlatTag)) ++Held; else if (StaysFlat(*P) == false && It->ActorHasTag(DinkLandforms::LiftedTag)) ++Lifted;
		}
		const TPair<float, FString> R = Check(It->GetName(), It->ScreenNumber, It->GetActorLocation(), 0.f);
		if (FMath::Abs(R.Key) > 2.f) { ++Off; Rows.Add({R.Key, R.Value}); }
	}
	for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It)
	{
		if (!Data.Screens.Contains(It->ScreenNumber)) continue;
		TInlineComponentArray<UInstancedStaticMeshComponent*> ISMs(*It);
		for (UInstancedStaticMeshComponent* ISM : ISMs)
		{
			for (int32 I = 0; ISM && I < ISM->GetInstanceCount(); ++I)
			{
				FTransform T;
				ISM->GetInstanceTransform(I, T, true);
				++Instances;
				// a card's centre sits offset_z above its placement point; compare the lift the ground asks for
				const float* Lift = nullptr;
				for (const auto& Pair : DecorLift) if (Pair.Key.Get() == ISM && Pair.Value.IsValidIndex(I)) Lift = &Pair.Value[I];
				const float Ground = HeightCmAt(FVector2D(T.GetLocation()));
				const float Diff = (Lift ? *Lift : 0.f) - Ground;
				if (FMath::Abs(Diff) > 2.f)
				{
					++InstOff;
					Rows.Add({Diff, FString::Printf(TEXT("%s instance %d SCR_%03d lift %.1f ground %.1f diff %+.1f cm"), *ISM->GetName(), I, It->ScreenNumber, Lift ? *Lift : 0.f, Ground, Diff)});
				}
			}
		}
	}
	Rows.Sort([](const FRow& A, const FRow& B) { return FMath::Abs(A.Diff) > FMath::Abs(B.Diff); });
	FString Out = FString::Printf(TEXT("DINK LANDFORMS AUDIT: %d placement actors on %d landforms screens, %d off the ground by more than 2 cm; %d decor instances, %d off; %d screens built; collision held flat %d, visible colliding geometry lifted %d"),
		Checked, Data.Screens.Num(), Off, Instances, InstOff, Built.Num(), Held, Lifted);
	for (int32 I = 0; I < Rows.Num() && I < MaxRows; ++I) Out += TEXT("\nDINK LANDFORMS AUDIT ROW: ") + Rows[I].Text;
	return Out;
}

static FAutoConsoleCommandWithWorldAndArgs GDinkLandformsAuditCommand(
	TEXT("dink.LandformsAudit"),
	TEXT("Landforms review: placement actors and decor instances of every landforms screen against the ground under them; the probe's height at the player."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		const UDinkLandformsSubsystem* L = World ? World->GetSubsystem<UDinkLandformsSubsystem>() : nullptr;
		if (!L) return;
		UE_LOG(LogDink, Display, TEXT("%s"), *L->Audit(Args.Num() > 0 ? FCString::Atoi(*Args[0]) : 40));
		if (const APlayerController* PC = World->GetFirstPlayerController())
		{
			if (const APawn* Pawn = PC->GetPawn())
			{
				const FVector P = Pawn->GetActorLocation();
				UE_LOG(LogDink, Display, TEXT("DINK LANDFORMS AUDIT: player at (%.0f, %.0f, %.1f), ground %.1f cm"), P.X, P.Y, P.Z, L->HeightCmAt(FVector2D(P)));
			}
		}
	}));
