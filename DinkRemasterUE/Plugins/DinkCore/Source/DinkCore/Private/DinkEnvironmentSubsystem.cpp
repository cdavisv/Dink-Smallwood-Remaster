#include "DinkEnvironmentSubsystem.h"
#include "DinkCoreModule.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "DinkArtFamilySubsystem.h"
#include "Components/PostProcessComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/LocalFogVolumeComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/SkyLight.h"
#include "Components/SkyLightComponent.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkOriginComponent.h"
#include "UObject/UnrealType.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/DecalComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialParameterCollection.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "Misc/Base64.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Greybox/DinkWarpComponent.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/Texture.h"

static TAutoConsoleVariable<float> CVarDinkGrassDensity(TEXT("dink.GrassDensity"), 1.f,
	TEXT("Multiplier on the configured meadow grass scatter density (0 = no scatter)."));
static TAutoConsoleVariable<int32> CVarDinkInteriorExposure(TEXT("dink.InteriorExposure"), 1,
	TEXT("1 = open the exposure and lift shadows on indoor screens (presentation only)."));
static TAutoConsoleVariable<float> CVarDinkInteriorExposureBias(TEXT("dink.InteriorExposureBias"), -0.5f,
	TEXT("Exposure compensation (EV) on indoor screens while dink.InteriorExposure is on."));
static TAutoConsoleVariable<float> CVarDinkWind(TEXT("dink.Wind"), 1.f,
	TEXT("Foliage wind strength (0 = still). Drives the Wind scalar of MPC_Dink_Environment."));
static TAutoConsoleVariable<int32> CVarDinkIndoorEnv(TEXT("dink.IndoorEnv"), 1,
	TEXT("1 = indoor screens get the enclosing shell, black backdrop, interior lights and fixed exposure (presentation only)."));
static TAutoConsoleVariable<float> CVarDinkIndoorLight(TEXT("dink.IndoorLight"), 1.f,
	TEXT("Multiplier on every light of the indoor set (review). Applied when the set is built."));
static TAutoConsoleVariable<float> CVarDinkIndoorEV(TEXT("dink.IndoorEV"), 0.f,
	TEXT("Added to the configured fixed indoor exposure (EV, review)."));
static TAutoConsoleVariable<int32> CVarDinkTownHouses(TEXT("dink.TownHouses"), 1,
	TEXT("1 = town screens show the assembled house kit of town_houses.json instead of their sprite cards (visual only; read when a screen comes into range)."));
static TAutoConsoleVariable<int32> CVarDinkForest(TEXT("dink.Forest"), 1,
	TEXT("1 = trees stand on the unwalkable forest-canopy tiles (ground_classes.json `trees`; visual only; read when a screen comes into range)."));
static TAutoConsoleVariable<int32> CVarDinkRelief(TEXT("dink.Relief"), 1,
	TEXT("Rock standing on cliff, rock-mass and cave-wall tiles (ground_classes.json `relief`; visual only, no collision): 0 = off, 1 = only where the 1997 hardness blocks the ground (default), 2 = also in enclosed pockets no walking player can enter. Read when a screen comes into range."));
static TAutoConsoleVariable<int32> CVarDinkWaterTiles(TEXT("dink.WaterTiles"), 1,
	TEXT("1 = a water surface lies over the water tiles of screens whose collision has no water fill (ground_classes.json `water_tiles`; visual only; read when a screen comes into range)."));
static TAutoConsoleVariable<int32> CVarDinkIndoorLitCards(TEXT("dink.IndoorLitCards"), 1,
	TEXT("1 = sprite cards on indoor screens are lit by the scene lights instead of glowing unlit (read when the indoor set is built)."));
static TAutoConsoleVariable<int32> CVarDinkStateSwaps(TEXT("dink.StateSwaps"), 1,
	TEXT("1 = swapped-in meshes follow their screen's &vision (the burnt cottage). Read-only on the game state."));
static TAutoConsoleVariable<int32> CVarDinkBackdrop(TEXT("dink.Backdrop"), 1,
	TEXT("1 = the far terrain skirt and hill ring follow the camera."));

namespace
{
	uint32 Hash3(uint32 A, uint32 B, uint32 C)
	{
		uint32 H = A * 0x9E3779B1u ^ (B + 0x7F4A7C15u) * 0x85EBCA6Bu ^ (C + 0x165667B1u) * 0xC2B2AE35u;
		H ^= H >> 15; H *= 0x2C1B3C6Du; H ^= H >> 12; H *= 0x297A2D39u; H ^= H >> 15;
		return H;
	}
	float Unit(uint32 H) { return float(H & 0xFFFFFF) / float(0x1000000); }
}

bool UDinkEnvironmentSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId UDinkEnvironmentSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkEnvironmentSubsystem, STATGROUP_Tickables);
}

int32 UDinkEnvironmentSubsystem::GetGrassInstanceCount() const
{
	int32 Count = 0;
	for (const auto& Pair : GrassCells) for (const UInstancedStaticMeshComponent* C : Pair.Value.Components) if (C) Count += C->GetInstanceCount();
	return Count;
}

void UDinkEnvironmentSubsystem::LoadConfig()
{
	const FString Dir = FPaths::ProjectContentDir() / TEXT("Dink/Data/Environment/");
	FString Text;
	TSharedPtr<FJsonObject> Root;
	auto LoadMeshes = [](const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, TArray<TObjectPtr<UStaticMesh>>& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
		if (!Object->TryGetArrayField(Key, Rows) || !Rows) return;
		for (const TSharedPtr<FJsonValue>& V : *Rows)
		{
			const FString Path = V->AsString();
			if (!FPackageName::DoesPackageExist(Path.Left(Path.Find(TEXT("."))))) continue; // wired by name: used when it exists
			if (UStaticMesh* M = LoadObject<UStaticMesh>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet)) Out.Add(M);
		}
	};
	if (FFileHelper::LoadFileToString(Text, *(Dir + TEXT("environment.json")))
		&& FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) && Root.IsValid())
	{
		const TSharedPtr<FJsonObject>* Grass = nullptr;
		if (Root->TryGetObjectField(TEXT("grass"), Grass) && Grass)
		{
			double Number = 0.0;
			if ((*Grass)->TryGetNumberField(TEXT("density_per_m2"), Number)) GrassDensityPerM2 = float(Number);
			if ((*Grass)->TryGetNumberField(TEXT("accent_density_per_m2"), Number)) AccentDensityPerM2 = float(Number);
			if ((*Grass)->TryGetNumberField(TEXT("min_cover"), Number)) GrassMinCover = float(Number);
			if ((*Grass)->TryGetNumberField(TEXT("scale_min"), Number)) GrassScaleMin = float(Number);
			if ((*Grass)->TryGetNumberField(TEXT("scale_max"), Number)) GrassScaleMax = float(Number);
			if ((*Grass)->TryGetNumberField(TEXT("far_cm"), Number)) GrassFarCm = float(Number);
			if ((*Grass)->TryGetNumberField(TEXT("shadow_cm"), Number)) GrassShadowCm = float(Number);
			if ((*Grass)->TryGetNumberField(TEXT("lean_deg"), Number)) GrassLeanDeg = float(Number);
			if ((*Grass)->TryGetNumberField(TEXT("height_min"), Number)) GrassHeightMin = float(Number);
			if ((*Grass)->TryGetNumberField(TEXT("height_max"), Number)) GrassHeightMax = float(Number);
			// the dense patch meshes win when they are imported; the clump meshes are the fallback
			LoadMeshes(*Grass, TEXT("preferred_meshes"), GrassMeshes);
			if (GrassMeshes.IsEmpty()) LoadMeshes(*Grass, TEXT("meshes"), GrassMeshes);
			// the taller upright patches replace the stretched low ones as soon as they are imported (wired by name)
			if (GrassMeshes.ContainsByPredicate([](const UStaticMesh* M) { return M->GetName().Contains(TEXT("GrassPatch_Tall")); }))
			{
				GrassMeshes.RemoveAll([](const UStaticMesh* M) { return !M->GetName().Contains(TEXT("GrassPatch_Tall")); });
				if ((*Grass)->TryGetNumberField(TEXT("tall_height_min"), Number)) GrassHeightMin = float(Number); else GrassHeightMin = 0.9f;
				if ((*Grass)->TryGetNumberField(TEXT("tall_height_max"), Number)) GrassHeightMax = float(Number); else GrassHeightMax = 1.2f;
			}
			if ((*Grass)->TryGetNumberField(TEXT("field_variation"), Number)) GrassFieldVariation = float(Number);
				// roles, wired by name: short turf where the field is worn or grazed, dry drifts, rank tufts along things
				LoadMeshes(*Grass, TEXT("short_meshes"), GrassShortMeshes);
				LoadMeshes(*Grass, TEXT("dry_meshes"), GrassDryMeshes);
				LoadMeshes(*Grass, TEXT("rank_meshes"), GrassRankMeshes);
				if ((*Grass)->TryGetNumberField(TEXT("rank_density_per_m2"), Number)) RankDensityPerM2 = float(Number);
				if ((*Grass)->TryGetNumberField(TEXT("rank_reach_cm"), Number)) RankReachCm = float(Number);
				if ((*Grass)->TryGetNumberField(TEXT("wear_reach_cm"), Number)) WearReachCm = float(Number);
				if ((*Grass)->TryGetNumberField(TEXT("dry_share"), Number)) DryShare = float(Number);
				if ((*Grass)->TryGetNumberField(TEXT("accent_cluster"), Number)) AccentCluster = float(Number);
				if ((*Grass)->TryGetNumberField(TEXT("field_scale"), Number)) GrassFieldScale = float(Number);
				GrassFieldFootprint = GrassFieldScale;
				if ((*Grass)->TryGetNumberField(TEXT("field_footprint"), Number)) GrassFieldFootprint = float(Number);
				if ((*Grass)->TryGetNumberField(TEXT("rank_edge_share"), Number)) RankEdgeShare = float(Number);
				if ((*Grass)->TryGetNumberField(TEXT("short_reach_cm"), Number)) ShortReachCm = float(Number);
				if ((*Grass)->TryGetNumberField(TEXT("clear_max_height_cm"), Number)) ClearMaxHeightCm = float(Number);
				if ((*Grass)->TryGetNumberField(TEXT("clear_max_span_cm"), Number)) ClearMaxSpanCm = float(Number);
				if ((*Grass)->TryGetNumberField(TEXT("clear_reach_cm"), Number)) ClearReachCm = float(Number);
				if ((*Grass)->TryGetNumberField(TEXT("edge_feather"), Number)) EdgeFeather = FMath::Clamp(float(Number), 0.f, 1.f);
			LoadMeshes(*Grass, TEXT("accent_meshes"), AccentMeshes);
		}
	}
	if (Root.IsValid())
	{
		auto Colour = [](const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, FLinearColor& Out)
		{
			const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
			if (Object->TryGetArrayField(Key, Values) && Values && Values->Num() == 3)
				Out = FLinearColor(float((*Values)[0]->AsNumber()), float((*Values)[1]->AsNumber()), float((*Values)[2]->AsNumber()));
		};
		auto Number = [](const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, float& Out)
		{
			double V = 0.0;
			if (Object->TryGetNumberField(Key, V)) Out = float(V);
		};
		const TSharedPtr<FJsonObject>* Indoor = nullptr;
		if (Root->TryGetObjectField(TEXT("indoor"), Indoor) && Indoor)
		{
			Number(*Indoor, TEXT("ceiling_cm"), IndoorCeilingCm);
			Number(*Indoor, TEXT("margin_cm"), IndoorMarginCm);
			Number(*Indoor, TEXT("backdrop_height_cm"), IndoorBackdropCm);
			Number(*Indoor, TEXT("ceiling_tile_cm"), IndoorCeilingTileCm);
			const TArray<TSharedPtr<FJsonValue>>* Skip = nullptr;
			if ((*Indoor)->TryGetArrayField(TEXT("skip_screens"), Skip) && Skip) for (const auto& V : *Skip) IndoorSkipScreens.Add(int32(V->AsNumber()));
			FString BlackPath;
			if ((*Indoor)->TryGetStringField(TEXT("black_material"), BlackPath) && FPackageName::DoesPackageExist(BlackPath.Left(BlackPath.Find(TEXT(".")))))
				IndoorBlack = LoadObject<UMaterialInterface>(nullptr, *BlackPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
			auto Look = [&](const TCHAR* Key, FDinkIndoorLook& L)
			{
				const TSharedPtr<FJsonObject>* O = nullptr;
				if (!(*Indoor)->TryGetObjectField(Key, O) || !O) return;
				Number(*O, TEXT("exposure_ev"), L.ExposureEV);
				Number(*O, TEXT("ambient_intensity"), L.AmbientIntensity);
				Colour(*O, TEXT("ambient_colour"), L.AmbientColour);
				double Count = 0.0;
				if ((*O)->TryGetNumberField(TEXT("lamps_per_screen"), Count)) L.LampsPerScreen = int32(Count);
				Number(*O, TEXT("lamp_intensity"), L.LampIntensity);
				Number(*O, TEXT("lamp_radius_cm"), L.LampRadiusCm);
				Number(*O, TEXT("lamp_height_cm"), L.LampHeightCm);
				Colour(*O, TEXT("lamp_colour"), L.LampColour);
				(*O)->TryGetBoolField(TEXT("lamps_at_walls"), L.bLampsAtWalls);
				Number(*O, TEXT("fog_density"), L.FogDensity);
				Number(*O, TEXT("fill_intensity"), L.FillIntensity);
				Colour(*O, TEXT("fill_colour"), L.FillColour);
				Number(*O, TEXT("ceiling_cm"), L.CeilingCm);
				(*O)->TryGetStringField(TEXT("ceiling_material"), L.CeilingMaterial);
				(*O)->TryGetStringField(TEXT("ceiling_wall_class"), L.CeilingWallClass);
			};
			Look(TEXT("interior"), InteriorLook);
			Look(TEXT("dungeon"), DungeonLook);
			auto IndoorMaterial = [&](const TCHAR* Key) -> UMaterialInterface*
			{
				FString Path;
				if (!(*Indoor)->TryGetStringField(Key, Path) || !FPackageName::DoesPackageExist(Path.Left(Path.Find(TEXT("."))))) return nullptr;
				return LoadObject<UMaterialInterface>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
			};
			LitCardMaterial = IndoorMaterial(TEXT("lit_card_material"));
			FlameMaterial = IndoorMaterial(TEXT("flame_material"));
			const TSharedPtr<FJsonObject>* Props = nullptr;
			if ((*Indoor)->TryGetObjectField(TEXT("props"), Props) && Props)
			{
				for (const auto& Pair : (*Props)->Values)
				{
					const TSharedPtr<FJsonObject>* Row = nullptr;
					if (!Pair.Value->TryGetObject(Row) || !Row) continue;
					FDinkLightProp Prop;
					FString Path;
					// wired by name: the prop stands there once its mesh is imported, the flame burns either way
					if ((*Row)->TryGetStringField(TEXT("mesh"), Path) && FPackageName::DoesPackageExist(Path.Left(Path.Find(TEXT(".")))))
					{
						Prop.Mesh = LoadObject<UStaticMesh>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
						if (Prop.Mesh) LightPropMeshes.Add(Prop.Mesh);
					}
					const TArray<TSharedPtr<FJsonValue>>* V = nullptr;
					if ((*Row)->TryGetArrayField(TEXT("socket_cm"), V) && V && V->Num() == 3) Prop.SocketCm = FVector((*V)[0]->AsNumber(), (*V)[1]->AsNumber(), (*V)[2]->AsNumber());
					if ((*Row)->TryGetArrayField(TEXT("flame_cm"), V) && V && V->Num() == 2) Prop.FlameCm = FVector2D((*V)[0]->AsNumber(), (*V)[1]->AsNumber());
					Number(*Row, TEXT("mount_cm"), Prop.MountCm);
					LightProps.Add(FName(*FString(Pair.Key.ToView())), Prop);
				}
			}
			const TSharedPtr<FJsonObject>* Fire = nullptr;
			if ((*Indoor)->TryGetObjectField(TEXT("fire"), Fire) && Fire)
			{
				Number(*Fire, TEXT("intensity"), FireIntensity);
				Number(*Fire, TEXT("radius_cm"), FireRadiusCm);
				Colour(*Fire, TEXT("colour"), FireColour);
				const TArray<TSharedPtr<FJsonValue>>* Classes = nullptr;
				if ((*Fire)->TryGetArrayField(TEXT("classes"), Classes) && Classes) for (const auto& V : *Classes) FireClasses.Add(FName(*V->AsString()));
			}
		}
		const TSharedPtr<FJsonObject>* DecalsObject = nullptr;
		if (Root->TryGetObjectField(TEXT("decals"), DecalsObject) && DecalsObject)
		{
			for (const auto& Pair : (*DecalsObject)->Values)
			{
				const TSharedPtr<FJsonObject>* Row = nullptr;
				if (!Pair.Value->TryGetObject(Row) || !Row) continue;
				FDinkDecalClass Decal;
				double Size = 0.0;
				if ((*Row)->TryGetNumberField(TEXT("size_cm"), Size)) Decal.SizeCm = float(Size);
				const TArray<TSharedPtr<FJsonValue>>* Paths = nullptr;
				if ((*Row)->TryGetArrayField(TEXT("materials"), Paths) && Paths)
				{
					for (const auto& V : *Paths)
					{
						const FString Path = V->AsString();
						if (!FPackageName::DoesPackageExist(Path.Left(Path.Find(TEXT("."))))) continue;
						if (UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet)) { Decal.Materials.Add(M); DecalMaterials.Add(M); }
					}
				}
				if (!Decal.Materials.IsEmpty()) DecalClasses.Add(FName(*FString(Pair.Key.ToView())), MoveTemp(Decal));
			}
		}
		const TSharedPtr<FJsonObject>* SkyObject = nullptr;
		if (Root->TryGetObjectField(TEXT("sky"), SkyObject) && SkyObject)
		{
			const FLinearColor Before = SkyTint;
			Colour(*SkyObject, TEXT("tint"), SkyTint);
			bSkyTint = !SkyTint.Equals(Before);
		}
		const TSharedPtr<FJsonObject>* Burn = nullptr;
		if (Root->TryGetObjectField(TEXT("burnable"), Burn) && Burn)
		{
			FString Text2;
			if ((*Burn)->TryGetStringField(TEXT("class"), Text2)) BurnClass = FName(*Text2);
			double Seq = 0.0;
			if ((*Burn)->TryGetNumberField(TEXT("burn_sequence"), Seq)) BurnSequence = int32(Seq);
			const TArray<TSharedPtr<FJsonValue>>* Scripts = nullptr;
			if ((*Burn)->TryGetArrayField(TEXT("scripts"), Scripts) && Scripts) for (const auto& V : *Scripts) BurnScripts.Add(FName(*V->AsString()));
			auto Mesh = [&](const TCHAR* Key) -> UStaticMesh*
			{
				FString Path;
				if (!(*Burn)->TryGetStringField(Key, Path) || !FPackageName::DoesPackageExist(Path.Left(Path.Find(TEXT("."))))) return nullptr;
				return LoadObject<UStaticMesh>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
			};
			(*Burn)->TryGetBoolField(TEXT("show_card"), bBurnShowCard);
			BurnBeforeMesh = Mesh(TEXT("before_mesh"));
			BurnAfterMesh = Mesh(TEXT("burnt_mesh"));
		}
		const TArray<TSharedPtr<FJsonValue>>* Swaps = nullptr;
		if (Root->TryGetArrayField(TEXT("state_swaps"), Swaps) && Swaps)
		{
			for (const TSharedPtr<FJsonValue>& V : *Swaps)
			{
				const TSharedPtr<FJsonObject>* Row = nullptr;
				if (!V->TryGetObject(Row) || !Row) continue;
				FDinkStateSwap Swap;
				Swap.Screen = (*Row)->GetIntegerField(TEXT("screen"));
				Swap.Vision = (*Row)->GetIntegerField(TEXT("vision"));
				auto SwapMesh = [&](const TCHAR* Key) -> UStaticMesh*
				{
					FString Path;
					if (!(*Row)->TryGetStringField(Key, Path) || !FPackageName::DoesPackageExist(Path.Left(Path.Find(TEXT("."))))) return nullptr;
					return LoadObject<UStaticMesh>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
				};
				Swap.From = SwapMesh(TEXT("from"));
				Swap.To = SwapMesh(TEXT("to"));
				const TArray<TSharedPtr<FJsonValue>>* Classes = nullptr;
				if ((*Row)->TryGetArrayField(TEXT("hide_classes"), Classes) && Classes) for (const auto& C : *Classes) Swap.HideClasses.Add(FName(*C->AsString()));
				if (!Swap.From || !Swap.To) continue;
				StateSwapMeshes.Add(Swap.From); StateSwapMeshes.Add(Swap.To);
				StateSwaps.Add(MoveTemp(Swap));
			}
		}
	}
	Root.Reset();
	if (!GrassMeshes.IsEmpty() && FFileHelper::LoadFileToString(Text, *(Dir + TEXT("layer_cover.json")))
		&& FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) && Root.IsValid())
	{
		CoverW = Root->GetIntegerField(TEXT("w"));
		CoverH = Root->GetIntegerField(TEXT("h"));
		const TSharedPtr<FJsonObject>* Rows = nullptr;
		if (CoverW > 0 && CoverH > 0 && Root->TryGetObjectField(TEXT("screens"), Rows) && Rows)
		{
			for (const auto& Pair : (*Rows)->Values)
			{
				TArray<uint8> Bytes;
				if (FBase64::Decode(Pair.Value->AsString(), Bytes) && Bytes.Num() == CoverW * CoverH)
				{
					Cover.Add(FCString::Atoi(*FString(Pair.Key.ToView())), MoveTemp(Bytes));
				}
			}
		}
	}
	LoadTownHouses();
	LoadForest();
	UE_LOG(LogDink, Display, TEXT("DINK ENV: grass roles: %d short, %d dry, %d rank meshes; indoor: lit cards %s, flame %s, %d light props (%d meshes); %d state swaps; town houses on %d screens"),
		GrassShortMeshes.Num(), GrassDryMeshes.Num(), GrassRankMeshes.Num(), LitCardMaterial ? TEXT("yes") : TEXT("no"), FlameMaterial ? TEXT("yes") : TEXT("no"),
		LightProps.Num(), LightPropMeshes.Num(), StateSwaps.Num(), TownScreens.Num());
	UE_LOG(LogDink, Display, TEXT("DINK ENV: grass carpet %d meshes (%s first) at %.2f per m2, %d accent meshes at %.2f per m2, cover for %d screens"),
		GrassMeshes.Num(), GrassMeshes.IsEmpty() ? TEXT("none") : *GrassMeshes[0]->GetName(), GrassDensityPerM2, AccentMeshes.Num(), AccentDensityPerM2, Cover.Num());
}

void UDinkEnvironmentSubsystem::OnWorldBeginPlay(UWorld& World)
{
	Super::OnWorldBeginPlay(World);
	// Headless runs (automation, the gameplay probe) get nothing at all from this subsystem.
	if (!FApp::CanEverRender()) return;
	GatherScreens(World);
	if (Screens.IsEmpty()) return;
	for (TActorIterator<AActor> It(&World); It; ++It)
	{
		// the importer owns its actors' tags and identifies them by key
		if (It->ActorHasTag(TEXT("DinkKey=Env:Backdrop")) || It->ActorHasTag(TEXT("DinkEnvBackdrop"))) Backdrops.Add(*It);
	}
	LoadConfig();
	if (bSkyTint) SetSkyTint(SkyTint);
	WindCollection = LoadObject<UMaterialParameterCollection>(nullptr, TEXT("/Game/Dink/Photoreal/Vegetation/MPC_Dink_Environment.MPC_Dink_Environment"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	FActorSpawnParameters SP;
	SP.ObjectFlags |= RF_Transient;
	Holder = World.SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, SP);
	if (!Holder) return;
	USceneComponent* Root = NewObject<USceneComponent>(Holder, TEXT("EnvRoot"));
	Holder->SetRootComponent(Root);
	Root->RegisterComponent();
	InteriorExposure = NewObject<UPostProcessComponent>(Holder, TEXT("EnvInteriorExposure"));
	InteriorExposure->SetupAttachment(Root);
	InteriorExposure->bUnbound = true;
	InteriorExposure->bEnabled = false;
	InteriorExposure->Priority = 20.f; // above the authored ArtExposure volumes (10), which keep their values
	InteriorExposure->BlendWeight = 1.f;
	FPostProcessSettings& S = InteriorExposure->Settings;
	S.bOverride_AutoExposureBias = true;
	S.AutoExposureBias = CVarDinkInteriorExposureBias.GetValueOnGameThread();
	S.bOverride_AutoExposureMinBrightness = true;
	S.AutoExposureMinBrightness = -8.f;
	S.bOverride_LocalExposureShadowContrastScale = true;
	S.LocalExposureShadowContrastScale = 0.65f;
	S.bOverride_LocalExposureHighlightContrastScale = true;
	S.LocalExposureHighlightContrastScale = 0.8f;
	S.bOverride_LumenSkylightLeaking = true;
	S.LumenSkylightLeaking = 0.03f;
	InteriorExposure->RegisterComponent();
	bActive = true;
}

void UDinkEnvironmentSubsystem::SetSkyTint(const FLinearColor& Colour)
{
	// the sky light's colour multiplies the captured sky: a touch less blue warms everything the sun does not reach
	for (TActorIterator<ASkyLight> It(GetWorld()); It; ++It)
	{
		if (USkyLightComponent* C = It->GetLightComponent())
		{
			C->SetMobility(EComponentMobility::Movable);
			C->SetLightColor(Colour);
		}
	}
}

static FAutoConsoleCommandWithWorldAndArgs GDinkSkyTintCommand(
	TEXT("dink.SkyTint"), TEXT("dink.SkyTint <r> <g> <b>: colour of the sky light (review; the shipped value is environment.json sky.tint)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UDinkEnvironmentSubsystem* Env = World ? World->GetSubsystem<UDinkEnvironmentSubsystem>() : nullptr;
		if (Env && Args.Num() == 3) Env->SetSkyTint(FLinearColor(FCString::Atof(*Args[0]), FCString::Atof(*Args[1]), FCString::Atof(*Args[2])));
	}));

void UDinkEnvironmentSubsystem::GatherScreens(UWorld& World)
{
	if (!Screens.IsEmpty()) return;
	for (TActorIterator<ADinkScreenVolume> It(&World); It; ++It)
	{
		FScreenInfo Info;
		Info.Number = It->ScreenNumber;
		Info.Corners = It->Corners;
		Info.Centre = DinkLayout::MapPixelToUnreal(It->Corners, 300.0, 200.0);
		Info.bIndoor = It->bIndoor;
		Info.InteriorId = It->InteriorId;
		Info.bDungeon = It->Kind == TEXT("dungeon");
		Screens.Add(Info);
		FBox2D Bounds(ForceInit);
		for (const double X : {0.0, 600.0}) for (const double Y : {0.0, 400.0}) Bounds += FVector2D(DinkLayout::MapPixelToUnreal(It->Corners, X, Y));
		ScreenBounds.Add(Bounds);
	}
}

void UDinkEnvironmentSubsystem::LoadGroundColour()
{
	bGroundLoaded = true;
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Environment/ground_colour.json")))
		|| !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid()) return;
	GroundW = Root->GetIntegerField(TEXT("w"));
	GroundH = Root->GetIntegerField(TEXT("h"));
	const TSharedPtr<FJsonObject>* Rows = nullptr;
	if (GroundW <= 0 || GroundH <= 0 || !Root->TryGetObjectField(TEXT("screens"), Rows) || !Rows) return;
	for (const auto& Pair : (*Rows)->Values)
	{
		TArray<uint8> Bytes;
		if (FBase64::Decode(Pair.Value->AsString(), Bytes) && Bytes.Num() == GroundW * GroundH * 3) GroundColour.Add(FCString::Atoi(*FString(Pair.Key.ToView())), MoveTemp(Bytes));
	}
}

bool UDinkEnvironmentSubsystem::GroundColourAt(const FVector2D& WorldXY, FLinearColor& Out)
{
	if (!FApp::CanEverRender() || !GetWorld()) return false;
	if (!bGroundLoaded) LoadGroundColour();
	if (GroundColour.IsEmpty()) return false;
	GatherScreens(*GetWorld());
	for (int32 Index = 0; Index < Screens.Num(); ++Index)
	{
		if (!ScreenBounds[Index].IsInside(WorldXY)) continue;
		const FScreenInfo& Screen = Screens[Index];
		double MapX = 0.0, MapY = 0.0;
		if (!DinkLayout::MetresToMapPixel(Screen.Corners, DinkLayout::UnrealToMetres(FVector(WorldXY, 0.0)), MapX, MapY)) continue;
		if (MapX < 0.0 || MapX >= 600.0 || MapY < 0.0 || MapY >= 400.0) continue;
		const TArray<uint8>* Grid = GroundColour.Find(Screen.Number);
		if (!Grid || Screen.bIndoor) return false;
		const int32 CX = FMath::Clamp(int32(MapX / 600.0 * GroundW), 0, GroundW - 1);
		const int32 CY = FMath::Clamp(int32(MapY / 400.0 * GroundH), 0, GroundH - 1);
		const uint8* P = Grid->GetData() + (CY * GroundW + CX) * 3;
		Out = FLinearColor::FromSRGBColor(FColor(P[0], P[1], P[2]));
		return true;
	}
	return false;
}

// ---------------------------------------------------------------------------------------------------------------------
// Indoor set

void UDinkEnvironmentSubsystem::ClearIndoor()
{
	if (IndoorSet)
	{
		IndoorSet->Destroy();
		// the outdoor height fog comes back with the sky
		for (TActorIterator<AExponentialHeightFog> It(GetWorld()); It; ++It) if (It->GetComponent()) It->GetComponent()->SetVisibility(true);
	}
	for (const auto& Pair : IndoorCardRestore)
	{
		// only a card that still shows our lit copy: a script may have given it another picture meanwhile
		if (Pair.Key.IsValid() && Pair.Value.IsValid() && Cast<UMaterialInstanceDynamic>(Pair.Key->GetMaterial(0)) && Pair.Key->GetMaterial(0)->GetMaterial() == LitCardMaterial->GetMaterial())
			Pair.Key->SetMaterial(0, Pair.Value.Get());
	}
	IndoorCardRestore.Reset();
	for (const TWeakObjectPtr<UMeshComponent>& Card : IndoorFollowed)
	{
		UMeshComponent* C = Card.Get();
		const TObjectPtr<UMaterialInterface>* Source = C ? IndoorLitSource.Find(C->GetMaterial(0)) : nullptr;
		if (Source && *Source) C->SetMaterial(0, *Source);
	}
	IndoorFollowed.Reset();
	IndoorLitBySource.Reset();
	IndoorLitSource.Reset();
	IndoorSet = nullptr;
	IndoorFireLights.Reset();
	IndoorFireBase.Reset();
	IndoorScreen = -1;
}

void UDinkEnvironmentSubsystem::BuildIndoor(const ADinkScreenVolume& Current)
{
	UWorld* World = GetWorld();
	ClearIndoor();
	IndoorScreen = Current.ScreenNumber;
	bIndoorDungeon = Current.Kind == TEXT("dungeon");
	const FDinkIndoorLook& Look = bIndoorDungeon ? DungeonLook : InteriorLook;
	const FVector Here = DinkLayout::MapPixelToUnreal(Current.Corners, 300.0, 200.0);
	// the whole interior (every screen of the same set) is one enclosure; lights only near the player
	FBox2D Bounds(ForceInit);
	TArray<int32> Lit;
	for (int32 Index = 0; Index < Screens.Num(); ++Index)
	{
		const FScreenInfo& S = Screens[Index];
		const bool bSame = S.Number == Current.ScreenNumber || (S.bIndoor && !Current.InteriorId.IsNone() && S.InteriorId == Current.InteriorId);
		if (!bSame) continue;
		Bounds += ScreenBounds[Index];
		if (FVector::DistSquared2D(S.Centre, Here) < FMath::Square(4500.0)) Lit.Add(Index);
	}
	if (!Bounds.bIsValid) return;
	FActorSpawnParameters SP;
	SP.ObjectFlags |= RF_Transient;
	IndoorSet = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, SP);
	if (!IndoorSet) return;
	USceneComponent* Root = NewObject<USceneComponent>(IndoorSet, TEXT("IndoorRoot"));
	IndoorSet->SetRootComponent(Root);
	Root->RegisterComponent();
	// the outdoor height fog would paint its sky-blue inscatter over the black backdrop: off while inside
	for (TActorIterator<AExponentialHeightFog> It(World); It; ++It) if (It->GetComponent()) It->GetComponent()->SetVisibility(false);
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	const FVector2D Min = Bounds.Min - FVector2D(IndoorMarginCm), Max = Bounds.Max + FVector2D(IndoorMarginCm);
	const FVector2D Mid = (Min + Max) * 0.5, Size = Max - Min;
	auto Mesh = [&](UStaticMesh* Asset, const FTransform& At, bool bOccluder)
	{
		if (!Asset) return;
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(IndoorSet);
		C->SetMobility(EComponentMobility::Movable);
		C->SetupAttachment(Root);
		C->SetStaticMesh(Asset);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetGenerateOverlapEvents(false);
		C->SetCanEverAffectNavigation(false);
		C->SetWorldTransform(At);
		if (IndoorBlack) C->SetMaterial(0, IndoorBlack);
		if (bOccluder)
		{
			// never drawn, but in the shadow maps and in the Lumen scene: the sun and the sky stay outside
			C->SetHiddenInGame(true);
			C->SetCastShadow(true);
			C->bCastHiddenShadow = true;
			C->bAffectIndirectLightingWhileHidden = true;
			C->bCastShadowAsTwoSided = true;
		}
		else
		{
			C->SetCastShadow(false);
			C->bAffectDistanceFieldLighting = false;
			C->bAffectDynamicIndirectLighting = false;
		}
		C->RegisterComponent();
	};
	const double Top = IndoorCeilingCm, Thick = 80.0, Out = 300.0;
	Mesh(Cube, FTransform(FQuat::Identity, FVector(Mid, Top + Thick * 0.5), FVector((Size.X + 2 * Out) / 100.0, (Size.Y + 2 * Out) / 100.0, Thick / 100.0)), true);
	const double WallH = Top + Thick + 100.0, WallZ = (Top + Thick - 100.0) * 0.5;
	Mesh(Cube, FTransform(FQuat::Identity, FVector(Min.X - Thick * 0.5, Mid.Y, WallZ), FVector(Thick / 100.0, (Size.Y + 2 * Thick) / 100.0, WallH / 100.0)), true);
	Mesh(Cube, FTransform(FQuat::Identity, FVector(Max.X + Thick * 0.5, Mid.Y, WallZ), FVector(Thick / 100.0, (Size.Y + 2 * Thick) / 100.0, WallH / 100.0)), true);
	Mesh(Cube, FTransform(FQuat::Identity, FVector(Mid.X, Min.Y - Thick * 0.5, WallZ), FVector((Size.X + 2 * Thick) / 100.0, Thick / 100.0, WallH / 100.0)), true);
	Mesh(Cube, FTransform(FQuat::Identity, FVector(Mid.X, Max.Y + Thick * 0.5, WallZ), FVector((Size.X + 2 * Thick) / 100.0, Thick / 100.0, WallH / 100.0)), true);
	if (IndoorBlack)
	{
		// black planes facing inward: seen from inside they hide everything beyond the room, from outside they are culled
		const double Big = (FMath::Max3(Size.X, Size.Y, double(IndoorBackdropCm)) + 600.0) / 100.0;
		const double ZMid = IndoorBackdropCm * 0.5 - 100.0;
		auto Facing = [&](const FVector& At, const FVector& Normal)
		{
			Mesh(Plane, FTransform(FRotationMatrix::MakeFromZ(Normal).ToQuat(), At, FVector(Big, Big, 1.0)), false);
		};
		Facing(FVector(Min.X, Mid.Y, ZMid), FVector(1, 0, 0));
		Facing(FVector(Max.X, Mid.Y, ZMid), FVector(-1, 0, 0));
		Facing(FVector(Mid.X, Min.Y, ZMid), FVector(0, 1, 0));
		Facing(FVector(Mid.X, Max.Y, ZMid), FVector(0, -1, 0));
		Facing(FVector(Mid, IndoorBackdropCm), FVector(0, 0, -1));
	}
	const float Gain = FMath::Max(CVarDinkIndoorLight.GetValueOnGameThread(), 0.f);
	auto Light = [&](const FVector& At, float Intensity, const FLinearColor& Colour, float Radius, bool bShadow, bool bFire)
	{
		if (Intensity <= 0.f) return;
		UPointLightComponent* L = NewObject<UPointLightComponent>(IndoorSet);
		L->SetMobility(EComponentMobility::Movable);
		L->SetupAttachment(Root);
		L->SetWorldLocation(At);
		L->SetIntensityUnits(ELightUnits::Candelas);
		L->SetIntensity(Intensity * Gain);
		L->SetLightColor(Colour);
		L->SetAttenuationRadius(Radius);
		L->SetSourceRadius(bShadow ? 6.f : 60.f);
		L->SetCastShadows(bShadow);
		if (!bShadow) L->SetSpecularScale(0.f);
		L->RegisterComponent();
		if (bFire) { IndoorFireLights.Add(L); IndoorFireBase.Add(Intensity * Gain); }
	};
	auto Prop = [&](UStaticMesh* Asset, const FTransform& At)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(IndoorSet);
		C->SetMobility(EComponentMobility::Movable);
		C->SetupAttachment(Root);
		C->SetStaticMesh(Asset);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetGenerateOverlapEvents(false);
		C->SetCanEverAffectNavigation(false);
		C->SetCastShadow(false);   // its own flame sits inside or on it: no shadow cage around the light
		C->SetWorldTransform(At);
		C->RegisterComponent();
	};
	auto Fill = [&](const FVector& At, float Intensity, const FLinearColor& Colour)
	{
		if (Intensity <= 0.f) return;
		// an even fill: no inverse-square falloff, so it has no hot spot on the floor under it or the ceiling over it
		UPointLightComponent* L = NewObject<UPointLightComponent>(IndoorSet);
		L->SetMobility(EComponentMobility::Movable);
		L->SetupAttachment(Root);
		L->SetWorldLocation(At);
		L->bUseInverseSquaredFalloff = false;
		L->SetLightFalloffExponent(1.2f);
		L->SetIntensity(Intensity * Gain);
		L->SetLightColor(Colour);
		L->SetAttenuationRadius(4500.f);
		L->SetSourceRadius(80.f);
		L->SetCastShadows(false);
		L->SetSpecularScale(0.f);
		L->RegisterComponent();
	};
	TSet<int32> LitNumbers;
	TMap<int32, FVector> Centres;
	for (const int32 Index : Lit) LitNumbers.Add(Screens[Index].Number);
	// a visible ceiling over rooms whose walls are the kit that stops at that height (one-sided planes facing down)
	// the ceiling goes by the walls that stand there, not by the screen's kind (a house interior built of dungeon blocks gets the stone one)
	const FDinkIndoorLook* const CeilingCandidates[] = {&Look, bIndoorDungeon ? &InteriorLook : &DungeonLook};
	for (const FDinkIndoorLook* Candidate : CeilingCandidates)
	{
		const FDinkIndoorLook& CeilingLook = *Candidate;
		if (CeilingLook.CeilingCm <= 0.f || CeilingLook.CeilingMaterial.IsEmpty() || !Plane) continue;
		bool bWalled = CeilingLook.CeilingWallClass.IsEmpty();
		for (TActorIterator<ADinkPlaceholderActor> It(World); It && !bWalled; ++It)
			bWalled = LitNumbers.Contains(It->ScreenNumber) && It->Origin && It->Origin->ClassId.ToString().StartsWith(CeilingLook.CeilingWallClass);
		for (TActorIterator<ADinkGreyboxScreen> It(World); It && !bWalled; ++It)
		{
			if (!LitNumbers.Contains(It->ScreenNumber) || !It->InstanceOrigins) continue;
			for (const FDinkInstanceOrigin& O : It->InstanceOrigins->Origins) if (O.ClassId.ToString().StartsWith(CeilingLook.CeilingWallClass)) { bWalled = true; break; }
		}
		UMaterialInterface* CeilingMaterial = bWalled && FPackageName::DoesPackageExist(CeilingLook.CeilingMaterial.Left(CeilingLook.CeilingMaterial.Find(TEXT("."))))
			? LoadObject<UMaterialInterface>(nullptr, *CeilingLook.CeilingMaterial, nullptr, LOAD_NoWarn | LOAD_Quiet) : nullptr;
		if (CeilingMaterial)
		{
			UInstancedStaticMeshComponent* Ceiling = NewObject<UInstancedStaticMeshComponent>(IndoorSet);
			Ceiling->SetMobility(EComponentMobility::Movable);
			Ceiling->SetupAttachment(Root);
			Ceiling->SetStaticMesh(Plane);
			Ceiling->SetMaterial(0, CeilingMaterial);
			Ceiling->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Ceiling->SetGenerateOverlapEvents(false);
			Ceiling->SetCanEverAffectNavigation(false);
			Ceiling->SetCastShadow(false);
			Ceiling->RegisterComponent();
			const double Tile = FMath::Max(double(IndoorCeilingTileCm), 50.0);
			const int32 NX = FMath::CeilToInt32(Size.X / Tile), NY = FMath::CeilToInt32(Size.Y / Tile);
			TArray<FTransform> Tiles;
			for (int32 Y = 0; Y < NY; ++Y)
				for (int32 X = 0; X < NX; ++X)
					Tiles.Emplace(FRotator(0.0, (Hash3(uint32(X), uint32(Y), 7u) & 1u) ? 180.0 : 0.0, 180.0), FVector(Min.X + (X + 0.5) * Tile, Min.Y + (Y + 0.5) * Tile, CeilingLook.CeilingCm), FVector(Tile / 100.0, Tile / 100.0, 1.0));
			Ceiling->AddInstances(Tiles, false, true);
			break;
		}
	}
	for (const int32 Index : Lit)
	{
		const FScreenInfo& S = Screens[Index];
		Centres.Add(S.Number, S.Centre);
		const double LightTop = Look.CeilingCm > 0.f ? FMath::Min(double(IndoorCeilingCm) - 40.0, double(Look.CeilingCm) - 60.0) : IndoorCeilingCm - 40.0;
		Light(S.Centre + FVector(0, 0, LightTop), Look.AmbientIntensity, Look.AmbientColour, 3000.f, false, false);
		Fill(S.Centre + FVector(0, 0, 165.0), Look.FillIntensity, Look.FillColour);
		if (!Look.bLampsAtWalls)
		{
			for (int32 I = 0; I < Look.LampsPerScreen; ++I)
			{
				const FVector At = DinkLayout::MapPixelToUnreal(S.Corners, 600.0 * (I + 0.5) / Look.LampsPerScreen, 215.0);
				const FVector Flame(At.X, At.Y, Look.LampHeightCm);
				Light(Flame, Look.LampIntensity, Look.LampColour, Look.LampRadiusCm, true, true);
				// a hanging lantern carries the lamp (pivot = its ceiling plate; the flame socket hangs below it)
				const FDinkLightProp* Lantern = LightProps.Find(TEXT("hanging_lantern"));
				if (Lantern && Lantern->Mesh) Prop(Lantern->Mesh, FTransform(FRotator(0.0, 37.0 * I, 0.0), Flame - Lantern->SocketCm));
				SpawnFlame(Flame - FVector(0.0, 0.0, 3.0), Lantern ? Lantern->FlameCm : FVector2D(5.0, 9.0));
			}
		}
	}
	// fire sprites (hearths, flames) light their surroundings; dungeon lamps stand off the wall placements
	auto FromPlacement = [&](FName ClassId, const FString& Origin, const FVector& At, const FVector& Centre, const FBox* Dressed = nullptr)
	{
		const FVector Inward = (FVector(Centre.X, Centre.Y, 0.0) - FVector(At.X, At.Y, 0.0)).GetSafeNormal();
		if (FireClasses.Contains(ClassId))
		{
			Light(FVector(At.X, At.Y, 90.0) + Inward * 45.0, FireIntensity, FireColour, FireRadiusCm, true, true);
		}
		else if (Look.bLampsAtWalls && Look.LampsPerScreen > 0 && ClassId.ToString().StartsWith(TEXT("dungeon_wall_stone")))
		{
			// a stable share of the wall segments carries a torch pool
			if (FCrc::StrCrc32(*Origin) % uint32(FMath::Max(Look.LampsPerScreen, 1)) == 0u)
			{
				// a wall torch: the bracket on the wall face, the stave leaning into the room (mesh +Y), the flame on its head
				const FVector Axis = FMath::Abs(Inward.X) > FMath::Abs(Inward.Y) ? FVector(FMath::Sign(Inward.X), 0.0, 0.0) : FVector(0.0, FMath::Sign(Inward.Y), 0.0);
				const FDinkLightProp* Torch = LightProps.Find(TEXT("wall_torch"));
				const FRotator Facing(0.0, Axis.Rotation().Yaw - 90.0, 0.0);
				// out of the wall: to the face of the mesh that dresses the placement when there is one (dungeon blocks are over a metre deep)
				double Out = 125.0;
				if (Dressed && Dressed->IsValid) Out = (Axis.X > 0.5 ? Dressed->Max.X - At.X : Axis.X < -0.5 ? At.X - Dressed->Min.X : Axis.Y > 0.5 ? Dressed->Max.Y - At.Y : At.Y - Dressed->Min.Y) + 2.0;
				const FVector Pivot = FVector(At.X, At.Y, Torch ? Torch->MountCm : Look.LampHeightCm - 77.0) + Axis * FMath::Clamp(Out, 5.0, 400.0);
				const FVector Flame = Pivot + Facing.RotateVector(Torch ? Torch->SocketCm : FVector(0.0, 33.0, 77.0));
				if (Torch && Torch->Mesh) Prop(Torch->Mesh, FTransform(Facing, Pivot));
				Light(Flame + Axis * 18.0 + FVector(0.0, 0.0, 12.0), Look.LampIntensity, Look.LampColour, Look.LampRadiusCm, true, true);
				SpawnFlame(Flame, Torch ? Torch->FlameCm : FVector2D(14.0, 30.0));
			}
		}
	};
	for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
	{
		if (!LitNumbers.Contains(It->ScreenNumber) || !It->Origin || !It->Card || It->PlacementKind == TEXT("hardness_only")) continue;
		FBox Dressed(ForceInit);
		TInlineComponentArray<UStaticMeshComponent*> Parts(*It);
		for (const UStaticMeshComponent* Part : Parts) if (Part != It->Card && Part->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)) Dressed += Part->Bounds.GetBox();
		FromPlacement(It->Origin->ClassId, It->Origin->OriginId.ToString(), It->Card->GetComponentLocation(), Centres[It->ScreenNumber], &Dressed);
	}
	for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It)
	{
		if (!LitNumbers.Contains(It->ScreenNumber) || !It->InstanceOrigins) continue;
		TInlineComponentArray<UInstancedStaticMeshComponent*> Components(*It);
		for (const FDinkInstanceOrigin& O : It->InstanceOrigins->Origins)
		{
			for (UInstancedStaticMeshComponent* C : Components)
			{
				FTransform T;
				if (C->GetFName() == O.ComponentName && C->GetInstanceTransform(O.InstanceIndex, T, /*bWorldSpace*/ true))
					FromPlacement(O.ClassId, O.OriginId.ToString(), T.GetLocation(), Centres[It->ScreenNumber]);
			}
		}
	}
	RelightIndoorCards(LitNumbers);
	if (Look.FogDensity > 0.f)
	{
		ULocalFogVolumeComponent* Fog = NewObject<ULocalFogVolumeComponent>(IndoorSet);
		Fog->SetMobility(EComponentMobility::Movable);
		Fog->SetupAttachment(Root);
		// the volume is a unit sphere of 5 m radius: scale it over the interior
		const double Radius = FMath::Max(Size.X, Size.Y) * 0.75;
		Fog->SetWorldTransform(FTransform(FQuat::Identity, FVector(Mid, 100.0), FVector(Radius / 500.0)));
		Fog->SetRadialFogExtinction(Look.FogDensity);
		Fog->SetHeightFogExtinction(Look.FogDensity);
		Fog->SetHeightFogFalloff(200.f);
		Fog->SetFogAlbedo(FLinearColor(0.75f, 0.8f, 0.9f));
		Fog->RegisterComponent();
	}
	UE_LOG(LogDink, Display, TEXT("DINK ENV: indoor set for screen %d (%s, interior %s): %.0f x %.0f m, %d fire and lamp lights, %d screens lit"),
		Current.ScreenNumber, bIndoorDungeon ? TEXT("dungeon") : TEXT("interior"), *Current.InteriorId.ToString(), Size.X / 100.0, Size.Y / 100.0, IndoorFireLights.Num(), Lit.Num());
}

void UDinkEnvironmentSubsystem::UpdateIndoor(const ADinkScreenVolume* Current, float DeltaTime)
{
	bool bWanted = Current && Current->bIndoor && CVarDinkIndoorEnv.GetValueOnGameThread() != 0 && !IndoorSkipScreens.Contains(Current->ScreenNumber);
	if (bWanted)
	{
		// a screen an art manifest dresses keeps its own authored lighting
		const UDinkArtFamilySubsystem* Families = GetWorld()->GetSubsystem<UDinkArtFamilySubsystem>();
		if (Families && Families->GetPrecedence().Screens.Contains(Current->ScreenNumber)) bWanted = false;
	}
	if (!bWanted)
	{
		if (IndoorSet || IndoorScreen != -1) ClearIndoor();
	}
	else if (IndoorScreen != Current->ScreenNumber)
	{
		BuildIndoor(*Current);
	}
	if (InteriorExposure)
	{
		FPostProcessSettings& S = InteriorExposure->Settings;
		const bool bSet = IndoorSet != nullptr;
		const float EV = (bIndoorDungeon ? DungeonLook.ExposureEV : InteriorLook.ExposureEV) + CVarDinkIndoorEV.GetValueOnGameThread();
		// inside the set the exposure is fixed: an eye adapted to the room, so dark corners stay dark
		S.bOverride_AutoExposureMaxBrightness = bSet;
		S.AutoExposureMinBrightness = bSet ? EV : -8.f;
		S.AutoExposureMaxBrightness = EV;
		S.AutoExposureBias = bSet ? 0.f : CVarDinkInteriorExposureBias.GetValueOnGameThread();
	}
	// animated sprite cards (creatures, people, scripted things): whenever one shows an unlit sprite frame, give it the lit copy of that frame
	if (IndoorSet && LitCardMaterial)
	{
		for (const TWeakObjectPtr<UMeshComponent>& Card : IndoorFollowed)
		{
			UMeshComponent* C = Card.Get();
			UMaterialInterface* M = C && C->GetNumMaterials() > 0 ? C->GetMaterial(0) : nullptr;
			if (!M || IndoorLitSource.Contains(M) || Cast<UMaterialInstanceDynamic>(M)) continue;
			const UMaterial* Base = M->GetMaterial();
			if (!Base || Base->GetName() != TEXT("M_DinkSprite")) continue;
			TObjectPtr<UMaterialInterface>& Lit = IndoorLitBySource.FindOrAdd(M);
			if (!Lit)
			{
				UTexture* Tex = nullptr;
				if (!M->GetTextureParameterValue(FHashedMaterialParameterInfo(TEXT("Tex")), Tex) || !Tex) continue;
				UMaterialInstanceDynamic* D = UMaterialInstanceDynamic::Create(LitCardMaterial, IndoorSet);
				D->SetTextureParameterValue(TEXT("Tex"), Tex);
				Lit = D;
				IndoorLitSource.Add(D, M);
			}
			C->SetMaterial(0, Lit);
		}
	}
	// fire light: slow breathing plus a quick shimmer, per light
	const double Now = GetWorld()->GetTimeSeconds();
	for (int32 Index = 0; Index < IndoorFireLights.Num(); ++Index)
	{
		if (UPointLightComponent* L = IndoorFireLights[Index])
		{
			const double Ph = Index * 1.7;
			L->SetIntensity(IndoorFireBase[Index] * float(0.9 + 0.06 * FMath::Sin(Now * 2.3 + Ph) + 0.04 * FMath::Sin(Now * 11.0 + Ph * 3.0)));
		}
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Burnable pines (read-only on the DinkC sprite state)

namespace
{
	/** A value of the script layer's sprite property map (UDinkScriptSpriteComponent::Props, another module), by reflection. */
	bool ReadScriptProp(const AActor& Actor, FName Key, int32& Out)
	{
		for (const UActorComponent* C : Actor.GetComponents())
		{
			if (!C || C->GetClass()->GetFName() != TEXT("DinkScriptSpriteComponent")) continue;
			const FMapProperty* Map = CastField<FMapProperty>(C->GetClass()->FindPropertyByName(TEXT("Props")));
			if (!Map || !CastField<FNameProperty>(Map->KeyProp) || !CastField<FIntProperty>(Map->ValueProp)) return false;
			FScriptMapHelper Helper(Map, Map->ContainerPtrToValuePtr<void>(C));
			if (const uint8* Value = Helper.FindValueFromHash(&Key))
			{
				Out = *reinterpret_cast<const int32*>(Value);
				return true;
			}
			return false;
		}
		return false;
	}
}

void UDinkEnvironmentSubsystem::FindBurnables()
{
	if (BurnClass.IsNone() || !BurnBeforeMesh || !BurnAfterMesh) return;
	for (TActorIterator<ADinkPlaceholderActor> It(GetWorld()); It; ++It)
	{
		ADinkPlaceholderActor* Actor = *It;
		if (!Actor->Origin || !Actor->Card || !Actor->GetRootComponent() || Actor->Origin->ClassId != BurnClass || !BurnScripts.Contains(Actor->Origin->ScriptName)) continue;
		if (Burnables.ContainsByPredicate([Actor](const FDinkBurnable& B) { return B.Actor == Actor; })) continue;
		if (Actor->ActorHasTag(UDinkArtFamilySubsystem::FamilyTag) || Actor->ActorHasTag(TEXT("DinkAuthoredArt"))) continue;
		FDinkBurnable B;
		B.Actor = Actor;
		const FVector CardLocation = Actor->Card->GetRelativeLocation();
		const double Yaw = DinkArtFamily::StableYaw(Actor->Origin->OriginId.ToString());
		auto Make = [&](UStaticMesh* Mesh, const TCHAR* Name)
		{
			UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(Actor, Name);
			C->SetMobility(EComponentMobility::Movable);
			C->SetupAttachment(Actor->GetRootComponent());
			C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			C->SetGenerateOverlapEvents(false);
			C->SetCanEverAffectNavigation(false);
			C->SetStaticMesh(Mesh);
			C->SetRelativeTransform(DinkArtFamily::MeshTransform(Mesh->GetBoundingBox(), FVector(CardLocation.X, CardLocation.Y, 0.0), Yaw, 1.f));
			C->SetHiddenInGame(true);
			C->RegisterComponent();
			return C;
		};
		B.Before = Make(BurnBeforeMesh, TEXT("BurnableBefore"));
		B.After = Make(BurnAfterMesh, TEXT("BurnableAfter"));
		B.State = -1;
		Burnables.Add(B);
	}
}

void UDinkEnvironmentSubsystem::UpdateBurnables()
{
	for (FDinkBurnable& B : Burnables)
	{
		ADinkPlaceholderActor* Actor = B.Actor.Get();
		if (!Actor || !Actor->Origin || !Actor->Card || !B.Before || !B.After || B.State == 3) continue;
		int32 Seq = 0, PSeq = 0;
		ReadScriptProp(*Actor, TEXT("seq"), Seq);
		const bool bPicture = ReadScriptProp(*Actor, TEXT("pseq"), PSeq) && PSeq != 0 && PSeq != Actor->Origin->Sequence;
		int32 State = B.State < 0 ? 0 : B.State;
		if (bPicture) State = 2;                                  // the script put another picture there (the stairs)
		else if (Seq == BurnSequence && State < 1) State = 1;     // the burn animation started
		if (State == B.State) continue;
		// a card something else hid (vision, a kill) stays that way: this hook leaves such a placement alone
		if (B.State < 0 && Actor->Card->bHiddenInGame) { B.State = 3; continue; }
		B.State = State;
		// The placement's card keeps the pine picture whatever the script sets (the presentation layer does not
		// redraw placement cards), so it stays hidden unless burnable.show_card says the cards follow the script:
		// then the fire card plays over the burnt pine and the swapped picture stands alone.
		B.Before->SetHiddenInGame(State != 0);
		B.After->SetHiddenInGame(!(State == 1 || (State == 2 && !bBurnShowCard)));
		Actor->Card->SetHiddenInGame(State == 0 || !bBurnShowCard);
		UE_LOG(LogDink, Display, TEXT("DINK ENV: burnable %s state %d (seq %d, pseq %d)"), *Actor->Origin->OriginId.ToString(), State, Seq, PSeq);
	}
}


// ---------------------------------------------------------------------------------------------------------------------
// Indoor: flames, light props, lit sprite cards

void UDinkEnvironmentSubsystem::SpawnFlame(const FVector& At, const FVector2D& SizeCm)
{
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	if (!IndoorSet || !FlameMaterial || !Plane) return;
	// two crossed upright cards (the plane's local X stands up); additive, unlit, no shadow
	for (const double Yaw : {20.0, 110.0})
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(IndoorSet);
		C->SetMobility(EComponentMobility::Movable);
		C->SetupAttachment(IndoorSet->GetRootComponent());
		C->SetStaticMesh(Plane);
		C->SetMaterial(0, FlameMaterial);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetGenerateOverlapEvents(false);
		C->SetCanEverAffectNavigation(false);
		C->SetCastShadow(false);
		C->bAffectDistanceFieldLighting = false;
		C->bAffectDynamicIndirectLighting = false;
		C->SetWorldTransform(FTransform(FRotator(90.0, Yaw, 0.0), At + FVector(0.0, 0.0, SizeCm.Y * 0.42), FVector(SizeCm.Y / 100.0, SizeCm.X / 100.0, 1.0)));
		C->RegisterComponent();
	}
}

void UDinkEnvironmentSubsystem::RelightIndoorCards(const TSet<int32>& ScreenNumbers)
{
	if (!LitCardMaterial || !IndoorSet || CVarDinkIndoorLitCards.GetValueOnGameThread() == 0) return;
	TMap<FName, int32> Kept, Skipped;
	int32 Count = 0;
	auto Relight = [&](UMeshComponent* C, FName ClassId)
	{
		if (!C || C->bHiddenInGame || C->GetNumMaterials() < 1) return;
		UMaterialInterface* M = C->GetMaterial(0);
		const UMaterial* Base = M ? M->GetMaterial() : nullptr;
		// only the importer's unlit sprite material; fire sprites stay what they are: light sources
		if (!Base || Base->GetName() != TEXT("M_DinkSprite") || FireClasses.Contains(ClassId)) return;
		UTexture* Tex = nullptr;
		if (!M->GetTextureParameterValue(FHashedMaterialParameterInfo(TEXT("Tex")), Tex) || !Tex || Tex->GetName() == TEXT("DefaultTexture")) return;
		// a card whose material is already dynamic is being animated by someone else (creatures, effects): leave it
		if (Cast<UMaterialInstanceDynamic>(M)) return;
		UMaterialInstanceDynamic* Lit = UMaterialInstanceDynamic::Create(LitCardMaterial, IndoorSet);
		Lit->SetTextureParameterValue(TEXT("Tex"), Tex);
		IndoorCardRestore.Emplace(C, M);
		C->SetMaterial(0, Lit);
		Kept.FindOrAdd(ClassId)++;
		++Count;
	};
	for (TActorIterator<ADinkPlaceholderActor> It(GetWorld()); It; ++It)
	{
		if (!ScreenNumbers.Contains(It->ScreenNumber) || !It->Origin || !It->Card || It->IsHidden()) continue;
		// things that move, animate or get replaced by a script keep the importer's material (their frames are swapped under us otherwise)
		if (It->Brain != 0 || !It->Origin->ScriptName.IsNone() || It->ActorHasTag(TEXT("DinkCreature")) || It->ActorHasTag(TEXT("DinkHumanoid")))
		{
			// something animates or replaces this card's picture: it is followed frame by frame (FollowIndoorCards) instead
			Skipped.FindOrAdd(It->Origin->ClassId)++;
			if (!FireClasses.Contains(It->Origin->ClassId)) IndoorFollowed.Add(It->Card);
			continue;
		}
		Relight(It->Card, It->Origin->ClassId);
	}
	for (TActorIterator<ADinkGreyboxScreen> It(GetWorld()); It; ++It)
	{
		if (!ScreenNumbers.Contains(It->ScreenNumber) || !It->InstanceOrigins) continue;
		TInlineComponentArray<UInstancedStaticMeshComponent*> Components(*It);
		for (UInstancedStaticMeshComponent* C : Components)
		{
			FName ClassId;
			for (const FDinkInstanceOrigin& O : It->InstanceOrigins->Origins) if (O.ComponentName == C->GetFName()) { ClassId = O.ClassId; break; }
			Relight(C, ClassId);
		}
	}
	// which sprite cards are still cards on this interior (no family mesh yet): the art backlog, by class
	FString List;
	Kept.ValueSort([](int32 A, int32 B) { return A > B; });
	for (const auto& Pair : Kept) List += FString::Printf(TEXT("%s x%d, "), *Pair.Key.ToString(), Pair.Value);
	FString Left;
	for (const auto& Pair : Skipped) Left += FString::Printf(TEXT("%s x%d, "), *Pair.Key.ToString(), Pair.Value);
	UE_LOG(LogDink, Display, TEXT("DINK ENV: indoor screen %d: %d sprite cards lit by the scene (still cards: %s); left unlit because animated or scripted: %s"), IndoorScreen, Count, *List, *Left);
}

// ---------------------------------------------------------------------------------------------------------------------
// State swaps (the burnt cottage): read-only on the screen's &vision as the placements show it

void UDinkEnvironmentSubsystem::UpdateStateSwaps()
{
	if (StateSwaps.IsEmpty() || CVarDinkStateSwaps.GetValueOnGameThread() == 0) return;
	UWorld* World = GetWorld();
	for (FDinkStateSwap& S : StateSwaps)
	{
		// the state is on when a placement gated by that vision value is shown (SetScreenVision un-hides its actor)
		bool bOn = false;
		for (TActorIterator<ADinkPlaceholderActor> It(World); It && !bOn; ++It) bOn = It->ScreenNumber == S.Screen && It->Vision == S.Vision && !It->IsHidden();
		if (int32(bOn) == S.State) continue;
		const FName ScreenTag(*FString::Printf(TEXT("DinkArtScreen_%d"), S.Screen));
		int32 Changed = 0;
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			if (!It->ActorHasTag(ScreenTag)) continue;
			TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
			for (UStaticMeshComponent* M : Meshes)
			{
				if (M->GetFName() != TEXT("EnvSwapVisual") || M->GetStaticMesh() != (bOn ? S.From : S.To)) continue;
				// the swap visual took the authored component's Static mobility: a static component refuses a new mesh
				M->SetMobility(EComponentMobility::Movable);
				if (!M->SetStaticMesh(bOn ? S.To : S.From)) continue;
				++Changed;
			}
		}
		// the swap visual may not exist yet (art is applied after begin play): try again until it does
		if (Changed == 0 && S.State < 0 && !bOn) { S.State = 0; continue; }
		if (Changed == 0 && bOn) continue;
		S.State = int32(bOn);
		int32 Hidden = 0;
		if (bOn)
		{
			// the burn holes and floor holes the original paints over the intact house are modelled in the burnt mesh
			for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
			{
				if (It->ScreenNumber != S.Screen || It->Vision != S.Vision || !It->Origin || !It->Card || !S.HideClasses.Contains(It->Origin->ClassId)) continue;
				It->Card->SetHiddenInGame(true);
				++Hidden;
			}
		}
		UE_LOG(LogDink, Display, TEXT("DINK ENV: state swap screen %d vision %d %s: %d visuals now %s, %d decal cards hidden"), S.Screen, S.Vision, bOn ? TEXT("on") : TEXT("off"),
			Changed, *(bOn ? S.To : S.From)->GetName(), Hidden);
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Town houses (Content/Dink/Data/Art/town_houses.json, written by Scripts/assemble_town_houses.py)

void UDinkEnvironmentSubsystem::LoadTownHouses()
{
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/town_houses.json")))
		|| !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid()) return;
	const TSharedPtr<FJsonObject>* ScreensObject = nullptr;
	if (!Root->TryGetObjectField(TEXT("screens"), ScreensObject) || !ScreensObject) return;
	for (const auto& Pair : (*ScreensObject)->Values)
	{
		const TSharedPtr<FJsonObject>* Row = nullptr;
		if (!Pair.Value->TryGetObject(Row) || !Row) continue;
		FDinkTownScreen& Screen = TownScreens.Add(FCString::Atoi(*FString(Pair.Key.ToView())));
		const TArray<TSharedPtr<FJsonValue>>* Prints = nullptr;
		if ((*Row)->TryGetArrayField(TEXT("footprints"), Prints) && Prints)
		{
			for (const TSharedPtr<FJsonValue>& FV : *Prints)
			{
				const TSharedPtr<FJsonObject>* F = nullptr;
				if (!FV->TryGetObject(F) || !F) continue;
				FDinkTownScreen::FFootprint Print;
				const TArray<TSharedPtr<FJsonValue>>* V = nullptr;
				if ((*F)->TryGetArrayField(TEXT("px"), V) && V && V->Num() == 2) Print.Px = FVector2D((*V)[0]->AsNumber(), (*V)[1]->AsNumber());
				if ((*F)->TryGetArrayField(TEXT("rect_cm"), V) && V && V->Num() == 4)
					Print.RectCm = FBox2D(FVector2D((*V)[0]->AsNumber(), (*V)[1]->AsNumber()), FVector2D((*V)[2]->AsNumber(), (*V)[3]->AsNumber()));
				double PrintYaw = 0.0;
				if ((*F)->TryGetNumberField(TEXT("yaw"), PrintYaw)) Print.Yaw = float(PrintYaw);
				if (Print.RectCm.bIsValid) Screen.Footprints.Add(Print);
			}
		}
		const TArray<TSharedPtr<FJsonValue>>* Houses = nullptr;
		if (!(*Row)->TryGetArrayField(TEXT("houses"), Houses) || !Houses) continue;
		for (const TSharedPtr<FJsonValue>& HV : *Houses)
		{
			const TSharedPtr<FJsonObject>* House = nullptr;
			if (!HV->TryGetObject(House) || !House) continue;
			const TArray<TSharedPtr<FJsonValue>>* Hide = nullptr;
			if ((*House)->TryGetArrayField(TEXT("hide"), Hide) && Hide) for (const auto& V : *Hide) Screen.Hide.Add(V->AsString());
			const TArray<TSharedPtr<FJsonValue>>* Modules = nullptr;
			if (!(*House)->TryGetArrayField(TEXT("modules"), Modules) || !Modules) continue;
			for (const TSharedPtr<FJsonValue>& MV : *Modules)
			{
				const TSharedPtr<FJsonObject>* M = nullptr;
				if (!MV->TryGetObject(M) || !M) continue;
				FDinkTownModule Module;
				Module.Mesh = (*M)->GetStringField(TEXT("mesh"));
				const TArray<TSharedPtr<FJsonValue>>* V = nullptr;
				if ((*M)->TryGetArrayField(TEXT("px"), V) && V && V->Num() == 2) Module.Px = FVector2D((*V)[0]->AsNumber(), (*V)[1]->AsNumber());
				if ((*M)->TryGetArrayField(TEXT("offset_cm"), V) && V && V->Num() == 3) Module.OffsetCm = FVector((*V)[0]->AsNumber(), (*V)[1]->AsNumber(), (*V)[2]->AsNumber());
				if ((*M)->TryGetArrayField(TEXT("scale"), V) && V && V->Num() == 3) Module.Scale = FVector((*V)[0]->AsNumber(), (*V)[1]->AsNumber(), (*V)[2]->AsNumber());
				double Yaw = 0.0;
				if ((*M)->TryGetNumberField(TEXT("yaw"), Yaw)) Module.Yaw = float(Yaw);
				Screen.Modules.Add(MoveTemp(Module));
			}
		}
	}
}

void UDinkEnvironmentSubsystem::ApplyTownHouses(int32 ScreenNumber, const FDinkScreenCorners& Corners)
{
	const FDinkTownScreen* Town = TownScreens.Find(ScreenNumber);
	if (!Town || TownApplied.Contains(ScreenNumber) || CVarDinkTownHouses.GetValueOnGameThread() == 0) return;
	TownApplied.Add(ScreenNumber);
	UWorld* World = GetWorld();
	FActorSpawnParameters SP;
	SP.ObjectFlags |= RF_Transient;
	AActor* Actor = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, SP);
	if (!Actor) return;
	USceneComponent* Root = NewObject<USceneComponent>(Actor, TEXT("TownRoot"));
	Actor->SetRootComponent(Root);
	Root->RegisterComponent();
	TownActors.Add(Actor);
	TMap<FString, UInstancedStaticMeshComponent*> ByMesh;
	int32 Placed = 0, Missing = 0;
	for (const FDinkTownModule& M : Town->Modules)
	{
		UInstancedStaticMeshComponent*& Component = ByMesh.FindOrAdd(M.Mesh);
		if (!Component)
		{
			const FString Package = M.Mesh.StartsWith(TEXT("/")) ? M.Mesh : TEXT("/Game/Dink/Photoreal/TownExteriors/") + M.Mesh;
			UStaticMesh* Mesh = FPackageName::DoesPackageExist(Package) ? LoadObject<UStaticMesh>(nullptr, *(Package + TEXT(".") + FPackageName::GetShortName(Package)), nullptr, LOAD_NoWarn | LOAD_Quiet) : nullptr;
			if (!Mesh) { ++Missing; ByMesh.Remove(M.Mesh); continue; }
			Component = NewObject<UInstancedStaticMeshComponent>(Actor);
			Component->SetMobility(EComponentMobility::Movable);
			Component->SetupAttachment(Root);
			Component->SetStaticMesh(Mesh);
			Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Component->SetGenerateOverlapEvents(false);
			Component->SetCanEverAffectNavigation(false);
			Component->RegisterComponent();
		}
		const FVector At = DinkLayout::MapPixelToUnreal(Corners, M.Px.X, M.Px.Y) + M.OffsetCm;
		Component->AddInstance(FTransform(FRotator(0.0, M.Yaw, 0.0), At, M.Scale), /*bWorldSpace*/ true);
		++Placed;
	}
	if (Placed == 0 && !Town->Modules.IsEmpty()) return; // kit not imported: the sprite cards stay
	// the carpet stays out of the houses and wears short in front of them
	for (const FDinkTownScreen::FFootprint& Print : Town->Footprints)
	{
		const FTransform LocalToWorld(FRotator(0.0, Print.Yaw, 0.0), DinkLayout::MapPixelToUnreal(Corners, Print.Px.X, Print.Px.Y));
		FGrassBlock Block;
		Block.WorldToLocal = LocalToWorld.Inverse();
		Block.LocalRect = Print.RectCm;
		for (const double X : {Print.RectCm.Min.X, Print.RectCm.Max.X}) for (const double Y : {Print.RectCm.Min.Y, Print.RectCm.Max.Y})
			Block.WorldBounds += FVector2D(LocalToWorld.TransformPosition(FVector(X, Y, 0.0)));
		GrassBlocks.Add(Block);
	}
	if (!Town->Footprints.IsEmpty()) bGrassSourcesStale = true;
	// the sprite cards the modules stand for (cards only: hardness, warps and scripts are other components and stay)
	int32 Hidden = 0;
	for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
	{
		if (It->ScreenNumber != ScreenNumber || !It->Origin || !It->Card || !Town->Hide.Contains(It->Origin->OriginId.ToString())) continue;
		It->Card->SetHiddenInGame(true);
		++Hidden;
	}
	for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It)
	{
		if (It->ScreenNumber != ScreenNumber || !It->InstanceOrigins) continue;
		TInlineComponentArray<UInstancedStaticMeshComponent*> Components(*It);
		for (const FDinkInstanceOrigin& O : It->InstanceOrigins->Origins)
		{
			if (!Town->Hide.Contains(O.OriginId.ToString())) continue;
			for (UInstancedStaticMeshComponent* C : Components)
			{
				FTransform T;
				if (C->GetFName() != O.ComponentName || !C->GetInstanceTransform(O.InstanceIndex, T, /*bWorldSpace*/ false)) continue;
				// a decor component draws many placements: this one instance shrinks to nothing below the ground (visual only)
				T.SetScale3D(FVector(0.0001));
				T.AddToTranslation(FVector(0.0, 0.0, -2000.0));
				C->UpdateInstanceTransform(O.InstanceIndex, T, /*bWorldSpace*/ false, /*bMarkRenderStateDirty*/ true);
				++Hidden;
			}
		}
	}
	UE_LOG(LogDink, Display, TEXT("DINK ENV: town houses on screen %d: %d modules placed (%d of unknown mesh), %d sprite cards hidden"), ScreenNumber, Placed, Missing, Hidden);
}

// ---------------------------------------------------------------------------------------------------------------------
// Forest (environment.json `forest`, ground_classes.json `trees`)

void UDinkEnvironmentSubsystem::LoadForest()
{
	const FString Dir = FPaths::ProjectContentDir() / TEXT("Dink/Data/Environment/");
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!FFileHelper::LoadFileToString(Text, *(Dir + TEXT("environment.json")))
		|| !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid()) return;
	const TSharedPtr<FJsonObject>* Forest = nullptr;
	if (!Root->TryGetObjectField(TEXT("forest"), Forest) || !Forest) return;
	auto LoadMeshes = [&](const TCHAR* Key, TArray<TObjectPtr<UStaticMesh>>& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
		if (!(*Forest)->TryGetArrayField(Key, Rows) || !Rows) return;
		for (const TSharedPtr<FJsonValue>& V : *Rows)
		{
			const FString Path = V->AsString();
			if (!FPackageName::DoesPackageExist(Path.Left(Path.Find(TEXT("."))))) continue; // wired by name: used when it exists
			if (UStaticMesh* M = LoadObject<UStaticMesh>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet)) Out.Add(M);
		}
	};
	LoadMeshes(TEXT("meshes"), ForestMeshes);
	LoadMeshes(TEXT("understory_meshes"), ForestUnderMeshes);
	double Number = 0.0;
	if ((*Forest)->TryGetNumberField(TEXT("interior_fill"), Number)) ForestInteriorFill = float(Number);
	if ((*Forest)->TryGetNumberField(TEXT("scale_min"), Number)) ForestScaleMin = float(Number);
	if ((*Forest)->TryGetNumberField(TEXT("scale_max"), Number)) ForestScaleMax = float(Number);
	if ((*Forest)->TryGetNumberField(TEXT("understory_share"), Number)) ForestUnderShare = float(Number);
	if ((*Forest)->TryGetNumberField(TEXT("cull_cm"), Number)) ForestCullCm = float(Number);
	// relief and water tiles (same data file, same life cycle as the forest)
	const TSharedPtr<FJsonObject>* Relief = nullptr;
	if (Root->TryGetObjectField(TEXT("relief"), Relief) && Relief)
	{
		const TArray<TSharedPtr<FJsonValue>>* Paths = nullptr;
		if ((*Relief)->TryGetArrayField(TEXT("meshes"), Paths) && Paths)
		{
			for (const TSharedPtr<FJsonValue>& V : *Paths)
			{
				const FString Path = V->AsString();
				if (!FPackageName::DoesPackageExist(Path.Left(Path.Find(TEXT("."))))) continue;
				if (UStaticMesh* M = LoadObject<UStaticMesh>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet)) ReliefMeshes.Add(M);
			}
		}
		if ((*Relief)->TryGetNumberField(TEXT("fill"), Number)) ReliefFill = float(Number);
		if ((*Relief)->TryGetNumberField(TEXT("sink"), Number)) ReliefSink = float(Number);
		if ((*Relief)->TryGetNumberField(TEXT("cull_cm"), Number)) ReliefCullCm = float(Number);
	}
	const TSharedPtr<FJsonObject>* WaterTiles = nullptr;
	if (Root->TryGetObjectField(TEXT("water_tiles"), WaterTiles) && WaterTiles)
	{
		FString Path;
		if ((*WaterTiles)->TryGetStringField(TEXT("material"), Path) && FPackageName::DoesPackageExist(Path.Left(Path.Find(TEXT(".")))))
			WaterTileMaterial = LoadObject<UMaterialInterface>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
		if ((*WaterTiles)->TryGetNumberField(TEXT("height_cm"), Number)) WaterTileHeightCm = float(Number);
	}
	if (ForestMeshes.IsEmpty() && ReliefMeshes.IsEmpty() && !WaterTileMaterial) return;
	Root.Reset();
	if (!FFileHelper::LoadFileToString(Text, *(Dir + TEXT("ground_classes.json")))
		|| !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid()) return;
	const TSharedPtr<FJsonObject>* Rows = nullptr;
	if (!Root->TryGetObjectField(TEXT("screens"), Rows) || !Rows) return;
	int32 Count = 0, ReliefCount = 0;
	for (const auto& Pair : (*Rows)->Values)
	{
		const TSharedPtr<FJsonObject>* Row = nullptr;
		const TArray<TSharedPtr<FJsonValue>>* Trees = nullptr;
		if (!Pair.Value->TryGetObject(Row) || !Row) continue;
		const int32 ScreenNumber = FCString::Atoi(*FString(Pair.Key.ToView()));
		const TArray<TSharedPtr<FJsonValue>>* Rocks = nullptr;
		if (!ReliefMeshes.IsEmpty() && (*Row)->TryGetArrayField(TEXT("relief"), Rocks) && Rocks)
		{
			TArray<FDinkReliefRock>& OutRocks = ReliefRocks.Add(ScreenNumber);
			for (const TSharedPtr<FJsonValue>& V : *Rocks)
			{
				const TArray<TSharedPtr<FJsonValue>>* P = nullptr;
				if (!V->TryGetArray(P) || !P || P->Num() < 4) continue;
				FDinkReliefRock Rock;
				Rock.Px = FVector2D((*P)[0]->AsNumber(), (*P)[1]->AsNumber());
				Rock.ClearPx = float((*P)[2]->AsNumber());
				Rock.Tier = int32((*P)[3]->AsNumber());
				OutRocks.Add(Rock);
				++ReliefCount;
			}
		}
		const TArray<TSharedPtr<FJsonValue>>* Rects = nullptr;
		if (WaterTileMaterial && (*Row)->TryGetArrayField(TEXT("water_tiles"), Rects) && Rects)
		{
			TArray<FBox2D>& OutRects = WaterTileRects.Add(ScreenNumber);
			for (const TSharedPtr<FJsonValue>& V : *Rects)
			{
				const TArray<TSharedPtr<FJsonValue>>* P = nullptr;
				if (!V->TryGetArray(P) || !P || P->Num() < 4) continue;
				OutRects.Add(FBox2D(FVector2D((*P)[0]->AsNumber(), (*P)[1]->AsNumber()), FVector2D((*P)[2]->AsNumber(), (*P)[3]->AsNumber())));
			}
		}
		if (ForestMeshes.IsEmpty() || !(*Row)->TryGetArrayField(TEXT("trees"), Trees) || !Trees) continue;
		TArray<FDinkForestTree>& Out = ForestTrees.Add(ScreenNumber);
		for (const TSharedPtr<FJsonValue>& V : *Trees)
		{
			const TArray<TSharedPtr<FJsonValue>>* P = nullptr;
			if (!V->TryGetArray(P) || !P || P->Num() < 2) continue;
			FDinkForestTree Tree;
			Tree.Px = FVector2D((*P)[0]->AsNumber(), (*P)[1]->AsNumber());
			Tree.bEdge = P->Num() > 2 && (*P)[2]->AsNumber() > 0.5;
			Out.Add(Tree);
			++Count;
		}
	}
	UE_LOG(LogDink, Display, TEXT("DINK ENV: forest: %d tree points on %d screens, %d tree meshes, %d understory meshes"), Count, ForestTrees.Num(), ForestMeshes.Num(), ForestUnderMeshes.Num());
	UE_LOG(LogDink, Display, TEXT("DINK ENV: relief: %d rock points on %d screens, %d rock meshes; water tiles on %d screens"), ReliefCount, ReliefRocks.Num(), ReliefMeshes.Num(), WaterTileRects.Num());
}

void UDinkEnvironmentSubsystem::ApplyRelief(int32 ScreenNumber, const FDinkScreenCorners& Corners)
{
	const TArray<FDinkReliefRock>* Rocks = ReliefRocks.Find(ScreenNumber);
	const TArray<FBox2D>* Water = WaterTileRects.Find(ScreenNumber);
	if ((!Rocks && !Water) || ReliefApplied.Contains(ScreenNumber)) return;
	ReliefApplied.Add(ScreenNumber);
	const int32 MaxTier = CVarDinkRelief.GetValueOnGameThread();
	const bool bWater = Water && WaterTileMaterial && CVarDinkWaterTiles.GetValueOnGameThread() != 0;
	const bool bRocks = Rocks && !ReliefMeshes.IsEmpty() && MaxTier > 0;
	if (!bWater && !bRocks) return;
	// a screen an art manifest dresses keeps its own ground
	const UDinkArtFamilySubsystem* Families = GetWorld()->GetSubsystem<UDinkArtFamilySubsystem>();
	if (Families && Families->GetPrecedence().Screens.Contains(ScreenNumber)) return;
	FActorSpawnParameters SP;
	SP.ObjectFlags |= RF_Transient;
	AActor* Actor = GetWorld()->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, SP);
	if (!Actor) return;
	USceneComponent* Root = NewObject<USceneComponent>(Actor, TEXT("ReliefRoot"));
	Actor->SetRootComponent(Root);
	Root->RegisterComponent();
	ForestActors.Add(Actor);
	auto Quiet = [&](UStaticMeshComponent* C)
	{
		C->SetMobility(EComponentMobility::Movable);
		C->SetupAttachment(Root);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetGenerateOverlapEvents(false);
		C->SetCanEverAffectNavigation(false);
	};
	int32 Placed = 0, Sheets = 0;
	if (bRocks)
	{
		// centimetres per map pixel on this screen (the settlement layout stretches screens: measure, do not assume)
		const double CmPerPx = FVector::Dist2D(DinkLayout::MapPixelToUnreal(Corners, 250.0, 200.0), DinkLayout::MapPixelToUnreal(Corners, 350.0, 200.0)) / 100.0;
		TMap<UStaticMesh*, UInstancedStaticMeshComponent*> ByMesh;
		for (int32 I = 0; I < Rocks->Num(); ++I)
		{
			const FDinkReliefRock& Rock = (*Rocks)[I];
			if (Rock.Tier > MaxTier) continue;
			const uint32 H = Hash3(uint32(ScreenNumber), uint32(I), 0x20C4u);
			UStaticMesh* Mesh = ReliefMeshes[int32(H % uint32(ReliefMeshes.Num()))];
			const FBox Box = Mesh->GetBoundingBox();
			const double Half = FMath::Max(FVector2D(Box.GetExtent()).Size(), 1.0);       // the footprint's corner: no yaw can push it past the disc
			const float Scale = float(ReliefFill * Rock.ClearPx * CmPerPx / Half);
			UInstancedStaticMeshComponent*& Component = ByMesh.FindOrAdd(Mesh);
			if (!Component)
			{
				Component = NewObject<UInstancedStaticMeshComponent>(Actor);
				Quiet(Component);
				Component->SetStaticMesh(Mesh);
				Component->SetCullDistances(0, int32(ReliefCullCm));
				Component->RegisterComponent();
			}
			FVector At = DinkLayout::MapPixelToUnreal(Corners, Rock.Px.X, Rock.Px.Y);
			// the mesh's pivot may sit anywhere: stand its base on the ground, sunk a little so no edge floats
			At.Z += -Box.Min.Z * Scale - ReliefSink * Box.GetSize().Z * Scale;
			Component->AddInstance(FTransform(FRotator(0.0, Unit(Hash3(H, 3u, 4u)) * 360.f, 0.0), At, FVector(Scale)), /*bWorldSpace*/ true);
			++Placed;
		}
	}
	if (bWater)
	{
		UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
		for (const FBox2D& R : *Water)
		{
			if (!Plane) break;
			const FVector A = DinkLayout::MapPixelToUnreal(Corners, R.Min.X, R.Min.Y), B = DinkLayout::MapPixelToUnreal(Corners, R.Max.X, R.Min.Y);
			const FVector C = DinkLayout::MapPixelToUnreal(Corners, R.Min.X, R.Max.Y), D = DinkLayout::MapPixelToUnreal(Corners, R.Max.X, R.Max.Y);
			UStaticMeshComponent* Sheet = NewObject<UStaticMeshComponent>(Actor);
			Quiet(Sheet);
			Sheet->SetStaticMesh(Plane);
			Sheet->SetMaterial(0, WaterTileMaterial);
			Sheet->SetCastShadow(false);
			const FVector Mid = (A + B + C + D) * 0.25 + FVector(0.0, 0.0, WaterTileHeightCm);
			const FVector AxisX = (B - A), AxisY = (C - A);
			Sheet->SetWorldTransform(FTransform(FRotationMatrix::MakeFromXY(AxisX, AxisY).Rotator(), Mid, FVector(AxisX.Size() / 100.0, AxisY.Size() / 100.0, 1.0)));
			Sheet->RegisterComponent();
			++Sheets;
		}
	}
	UE_LOG(LogDink, Display, TEXT("DINK ENV: relief on screen %d: %d rocks of %d points (tier <= %d), %d water sheets"), ScreenNumber, Placed, Rocks ? Rocks->Num() : 0, MaxTier, Sheets);
}

void UDinkEnvironmentSubsystem::ApplyForest(int32 ScreenNumber, const FDinkScreenCorners& Corners)
{
	const TArray<FDinkForestTree>* Trees = ForestTrees.Find(ScreenNumber);
	if (!Trees || ForestMeshes.IsEmpty() || ForestApplied.Contains(ScreenNumber) || CVarDinkForest.GetValueOnGameThread() == 0) return;
	ForestApplied.Add(ScreenNumber);
	// a screen an art manifest dresses keeps its own vegetation
	const UDinkArtFamilySubsystem* Families = GetWorld()->GetSubsystem<UDinkArtFamilySubsystem>();
	if (Families && Families->GetPrecedence().Screens.Contains(ScreenNumber)) return;
	FActorSpawnParameters SP;
	SP.ObjectFlags |= RF_Transient;
	AActor* Actor = GetWorld()->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, SP);
	if (!Actor) return;
	USceneComponent* Root = NewObject<USceneComponent>(Actor, TEXT("ForestRoot"));
	Actor->SetRootComponent(Root);
	Root->RegisterComponent();
	ForestActors.Add(Actor);
	TMap<UStaticMesh*, UInstancedStaticMeshComponent*> ByMesh;
	auto Place = [&](UStaticMesh* Mesh, const FVector& At, float Yaw, float Scale)
	{
		UInstancedStaticMeshComponent*& Component = ByMesh.FindOrAdd(Mesh);
		if (!Component)
		{
			Component = NewObject<UInstancedStaticMeshComponent>(Actor);
			Component->SetMobility(EComponentMobility::Movable);
			Component->SetupAttachment(Root);
			Component->SetStaticMesh(Mesh);
			Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Component->SetGenerateOverlapEvents(false);
			Component->SetCanEverAffectNavigation(false);
			Component->SetCullDistances(0, int32(ForestCullCm));
			Component->RegisterComponent();
		}
		Component->AddInstance(FTransform(FRotator(0.0, Yaw, 0.0), At, FVector(Scale)), /*bWorldSpace*/ true);
	};
	int32 Placed = 0, Under = 0;
	for (int32 I = 0; I < Trees->Num(); ++I)
	{
		const FDinkForestTree& Tree = (*Trees)[I];
		const uint32 H = Hash3(uint32(ScreenNumber), uint32(I), 0x7F0E57u);
		// the rows a player can see carry every tree; deeper in, where only a camera above the crowns would look, fewer
		if (!Tree.bEdge && Unit(Hash3(H, 1u, 2u)) > ForestInteriorFill) continue;
		const FVector At = DinkLayout::MapPixelToUnreal(Corners, Tree.Px.X, Tree.Px.Y);
		Place(ForestMeshes[int32(H % uint32(ForestMeshes.Num()))], At, Unit(Hash3(H, 3u, 4u)) * 360.f,
			FMath::Lerp(ForestScaleMin, ForestScaleMax, Unit(Hash3(H, 5u, 6u))));
		++Placed;
		if (Tree.bEdge && !ForestUnderMeshes.IsEmpty() && Unit(Hash3(H, 7u, 8u)) < ForestUnderShare)
		{
			// ferns and bushes at the feet of the edge trees, within the tree's own unwalkable 8 px
			const float Angle = Unit(Hash3(H, 9u, 10u)) * 2.f * PI;
			const float Reach = 25.f + 35.f * Unit(Hash3(H, 11u, 12u));
			Place(ForestUnderMeshes[int32(Hash3(H, 13u, 14u) % uint32(ForestUnderMeshes.Num()))], At + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0.f) * Reach,
				Unit(Hash3(H, 15u, 16u)) * 360.f, FMath::Lerp(0.8f, 1.25f, Unit(Hash3(H, 17u, 18u))));
			++Under;
		}
	}
	UE_LOG(LogDink, Display, TEXT("DINK ENV: forest on screen %d: %d trees of %d points, %d understory plants"), ScreenNumber, Placed, Trees->Num(), Under);
}

static FAutoConsoleCommandWithWorldAndArgs GDinkPillbugCarcassCommand(
	TEXT("dink.PillbugCarcass"), TEXT("Review only: lays a carcass beside every photoreal pillbug of the current screen (nothing is killed)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&, UWorld* World)
	{
		if (UDinkEnvironmentSubsystem* Env = World ? World->GetSubsystem<UDinkEnvironmentSubsystem>() : nullptr) Env->ReviewCarcasses();
	}));

void UDinkEnvironmentSubsystem::ApplyDecals(int32 ScreenNumber)
{
	if (DecalClasses.IsEmpty() || DecalScreens.Contains(ScreenNumber)) return;
	DecalScreens.Add(ScreenNumber);
	// screens and origins the authored-art manifests handle keep their own treatment
	const UDinkArtFamilySubsystem* Families = GetWorld()->GetSubsystem<UDinkArtFamilySubsystem>();
	if (Families && Families->GetPrecedence().Screens.Contains(ScreenNumber)) return;
	int32 Count = 0;
	for (TActorIterator<ADinkPlaceholderActor> It(GetWorld()); It; ++It)
	{
		if (It->ScreenNumber != ScreenNumber || !It->Origin || !It->Card || !It->GetRootComponent()) continue;
		const FDinkDecalClass* Decal = DecalClasses.Find(It->Origin->ClassId);
		// scripted, animated or already dressed placements keep what they have
		// a class a state swap models in its mesh (the burn holes of the burnt cottage) is that swap's business
		if (Decal && StateSwaps.ContainsByPredicate([&](const FDinkStateSwap& S) { return S.Screen == ScreenNumber && S.HideClasses.Contains(It->Origin->ClassId); })) continue;
		if (!Decal || !It->Origin->ScriptName.IsNone() || It->Brain != 0 || It->Card->bHiddenInGame
			|| It->ActorHasTag(UDinkArtFamilySubsystem::FamilyTag) || It->ActorHasTag(TEXT("DinkAuthoredArt"))) continue;
		const FString Origin = It->Origin->OriginId.ToString();
		if (Families && Families->GetPrecedence().Origins.Contains(Origin)) continue;
		UDecalComponent* C = NewObject<UDecalComponent>(*It, TEXT("EnvDecal"));
		C->SetupAttachment(It->GetRootComponent());
		C->SetDecalMaterial(Decal->Materials[int32(FCrc::StrCrc32(*Origin) % uint32(Decal->Materials.Num()))]);
		// the decal box: X is the projection depth (down), Y and Z the footprint
		C->DecalSize = FVector(40.0, Decal->SizeCm * 0.5, Decal->SizeCm * 0.5);
		const FVector Card = It->Card->GetComponentLocation();
		C->SetWorldLocationAndRotation(FVector(Card.X, Card.Y, It->GetActorLocation().Z), FRotator(-90.0, DinkArtFamily::StableYaw(Origin), 0.0));
		It->AddInstanceComponent(C);
		C->RegisterComponent();
		It->Card->SetHiddenInGame(true);
		++Count;
	}
	if (Count > 0) UE_LOG(LogDink, Display, TEXT("DINK ENV: %d ground decals on screen %d"), Count, ScreenNumber);
}

void UDinkEnvironmentSubsystem::UpdateCorpses(int32 CurrentScreen)
{
	if (!bCorpsesGathered)
	{
		bCorpsesGathered = true;
		static const TCHAR* Path = TEXT("/Game/Dink/Photoreal/Creatures/Pillbug/SM_Pillbug_Corpse_PR");
		if (FPackageName::DoesPackageExist(Path)) CorpseMesh = LoadObject<UStaticMesh>(nullptr, *(FString(Path) + TEXT(".SM_Pillbug_Corpse_PR")), nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (!CorpseMesh) return;
		for (TActorIterator<ADinkPlaceholderActor> It(GetWorld()); It; ++It)
		{
			if (!It->ActorHasTag(TEXT("DinkCreature"))) continue;
			USkeletalMeshComponent* Body = It->FindComponentByClass<USkeletalMeshComponent>();
			if (!Body || !Body->GetSkeletalMeshAsset() || Body->GetSkeletalMeshAsset()->GetName() != TEXT("SK_Pillbug_Photoreal")) continue;
			FDinkCorpseWatch Watch;
			Watch.Actor = *It;
			Watch.Body = Body;
			Watch.Screen = It->ScreenNumber;
			CorpseWatches.Add(Watch);
		}
		UE_LOG(LogDink, Display, TEXT("DINK ENV: %d photoreal pillbugs watched for their carcass"), CorpseWatches.Num());
	}
	if (!CorpseMesh || !Holder) return;
	if (CurrentScreen != CorpseScreen)
	{
		// the original drops its corpses with the screen
		CorpseScreen = CurrentScreen;
		for (UStaticMeshComponent* C : Corpses) if (C) C->DestroyComponent();
		Corpses.Reset();
		for (FDinkCorpseWatch& W : CorpseWatches) { W.bSeen = false; W.bDone = false; }
	}
	for (FDinkCorpseWatch& W : CorpseWatches)
	{
		if (W.Screen != CurrentScreen) continue;
		const AActor* Actor = W.Actor.Get();
		const USkeletalMeshComponent* Body = W.Body.Get();
		if (Actor && Body && !Actor->IsHidden())
		{
			W.bSeen = true;
			W.bDone = false;
			W.Last = Body->GetComponentLocation();
			W.Yaw = Body->GetComponentRotation().Yaw;
			if (!bCorpseReview) continue;
		}
		if ((!W.bSeen || W.bDone) && !bCorpseReview) continue;
		if (bCorpseReview) { if (!Actor) continue; W.Last = Actor->GetActorLocation() + FVector(260.0, 0.0, 0.0); W.Last.Z = Body ? Body->GetComponentLocation().Z : W.Last.Z; }
		W.bDone = true;
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(Holder);
		C->SetMobility(EComponentMobility::Movable);
		C->SetupAttachment(Holder->GetRootComponent());
		C->SetStaticMesh(CorpseMesh);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetGenerateOverlapEvents(false);
		C->SetCanEverAffectNavigation(false);
		C->SetWorldTransform(FTransform(FRotator(0.0, W.Yaw, 0.0), W.Last));
		C->RegisterComponent();
		Corpses.Add(C);
		UE_LOG(LogDink, Display, TEXT("DINK ENV: pillbug carcass at %s (screen %d)"), *W.Last.ToCompactString(), CurrentScreen);
	}
	bCorpseReview = false;
}

bool UDinkEnvironmentSubsystem::IsScreenDressed(int32 ScreenNumber) const
{
	return DressedScreens.Contains(ScreenNumber);
}

void UDinkEnvironmentSubsystem::ClearGrass()
{
	for (auto& Pair : GrassCells) for (UInstancedStaticMeshComponent* C : Pair.Value.Components) if (C) C->DestroyComponent();
	GrassCells.Reset();
}

bool UDinkEnvironmentSubsystem::GroundAt(const FVector2D& WorldXY, uint32 Hash, float& OutZ) const
{
	for (int32 Index = 0; Index < Screens.Num(); ++Index)
	{
		if (!ScreenBounds[Index].IsInside(WorldXY)) continue;
		const FScreenInfo& Screen = Screens[Index];
		double MapX = 0.0, MapY = 0.0;
		if (!DinkLayout::MetresToMapPixel(Screen.Corners, DinkLayout::UnrealToMetres(FVector(WorldXY, 0.0)), MapX, MapY)) continue;
		if (MapX < 0.0 || MapX >= 600.0 || MapY < 0.0 || MapY >= 400.0) continue;
		if (Screen.bIndoor) return false;
		for (const FGrassBlock& Block : GrassBlocks)
		{
			if (!Block.WorldBounds.IsInside(WorldXY)) continue;
			const FVector L = Block.WorldToLocal.TransformPosition(FVector(WorldXY, 0.0));
			if (Block.LocalRect.IsInside(FVector2D(L))) return false;
		}
		if (IsScreenDressed(Screen.Number))
		{
			// Authored screen: the tile mask knows nothing of its paths, ponds and buildings. Grass grows only
			// where a downward trace lands on a mesh that carries the meadow terrain material.
			// authored paths, pens and pond rims lie on top of the meadow, often without collision: stay off their footprints
			for (const TWeakObjectPtr<UStaticMeshComponent>& Bare : BareGround)
			{
				const UStaticMeshComponent* Component = Bare.Get();
				if (!Component || !Component->GetStaticMesh()) continue;
				const FVector Local = Component->GetComponentTransform().InverseTransformPosition(FVector(WorldXY, Component->GetComponentLocation().Z));
				const FBox Box = Component->GetStaticMesh()->GetBoundingBox();
				if (Local.X >= Box.Min.X && Local.X <= Box.Max.X && Local.Y >= Box.Min.Y && Local.Y <= Box.Max.Y) return false;
			}
			FHitResult Hit;
			FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkGrass), /*bTraceComplex*/ true);
			if (!GetWorld()->LineTraceSingleByChannel(Hit, FVector(WorldXY, 400.0), FVector(WorldXY, -200.0), ECC_Visibility, Params)) return false;
			const UPrimitiveComponent* Component = Hit.GetComponent();
			const UMaterialInterface* Material = Component ? Component->GetMaterial(0) : nullptr;
			if (!Material || !Material->GetName().Contains(TEXT("MeadowTurf"))) return false;
			OutZ = Hit.ImpactPoint.Z;
			LastCover = 1.f;
			return true;
		}
		const TArray<uint8>* Mask = Cover.Find(Screen.Number);
		if (!Mask) return false;
		// noisy edge: the threshold wanders per point, so the carpet ends in a ragged line, not on the mask grid
		OutZ = 0.f;
		LastCover = CoverAt(*Mask, MapX, MapY);
		return LastCover > GrassMinCover + (Unit(Hash3(Hash, 77u, 5u)) - 0.5f) * 0.5f;
	}
	return false;
}

float UDinkEnvironmentSubsystem::MaskCoverAt(const FVector2D& WorldXY) const
{
	// meadow cover of the tile mask under a point, 0..1; -1 where there is no mask (authored or indoor screens, off the grid)
	for (int32 Index = 0; Index < Screens.Num(); ++Index)
	{
		if (!ScreenBounds[Index].IsInside(WorldXY)) continue;
		const FScreenInfo& Screen = Screens[Index];
		double MapX = 0.0, MapY = 0.0;
		if (!DinkLayout::MetresToMapPixel(Screen.Corners, DinkLayout::UnrealToMetres(FVector(WorldXY, 0.0)), MapX, MapY)) continue;
		if (MapX < 0.0 || MapX >= 600.0 || MapY < 0.0 || MapY >= 400.0) continue;
		if (Screen.bIndoor || IsScreenDressed(Screen.Number)) return -1.f;
		const TArray<uint8>* Mask = Cover.Find(Screen.Number);
		if (!Mask) return -1.f;
		return CoverAt(*Mask, MapX, MapY);
	}
	return -1.f;
}

float UDinkEnvironmentSubsystem::CoverAt(const TArray<uint8>& Mask, double MapX, double MapY) const
{
	// bilinear between the cell centres of the cover grid (clamped at the screen's rim): the carpet's edge follows the
	// terrain mask's soft edge instead of stepping along grid cells (round 7: the steps read as a hard card line)
	const double X = FMath::Clamp(MapX / 600.0 * CoverW - 0.5, 0.0, double(CoverW - 1));
	const double Y = FMath::Clamp(MapY / 400.0 * CoverH - 0.5, 0.0, double(CoverH - 1));
	const int32 X0 = FMath::FloorToInt32(X), Y0 = FMath::FloorToInt32(Y);
	const int32 X1 = FMath::Min(X0 + 1, CoverW - 1), Y1 = FMath::Min(Y0 + 1, CoverH - 1);
	const float FX = float(X - X0), FY = float(Y - Y0);
	auto At = [&](int32 CX, int32 CY) { return Mask[CY * CoverW + CX] / 255.f; };
	return FMath::Lerp(FMath::Lerp(At(X0, Y0), At(X1, Y0), FX), FMath::Lerp(At(X0, Y1), At(X1, Y1), FX), FY);
}

void UDinkEnvironmentSubsystem::GatherGrassClears()
{
	// Low things the carpet would bury: family props (tools, pebbles, mushrooms, bones, corpses), small authored props and
	// ground decals. Each gets a clearing over its footprint with a soft rim; the lower the thing, the wider the rim.
	// Tall or long things (trees, barrels above the grass, fence runs, walls) stand in the grass as before.
	UWorld* World = GetWorld();
	if (!World) return;
	TArray<FGrassClear> Found;
	TSet<uint64> Keys;
	TArray<FBox2D> Fresh;
	auto Add = [&](const FTransform& LocalToWorld, const FBox& LocalBox, float ReachCm)
	{
		FGrassClear C;
		C.WorldToLocal = LocalToWorld.Inverse();
		C.LocalBox = LocalBox;
		C.ReachCm = ReachCm;
		for (const double X : {LocalBox.Min.X, LocalBox.Max.X}) for (const double Y : {LocalBox.Min.Y, LocalBox.Max.Y})
			C.WorldBounds += FVector2D(LocalToWorld.TransformPosition(FVector(X, Y, 0.0)));
		C.WorldBounds = C.WorldBounds.ExpandBy(ReachCm);
		const FVector2D Mid = C.WorldBounds.GetCenter(), Size = C.WorldBounds.GetSize();
		const uint64 Key = (uint64(Hash3(uint32(FMath::RoundToInt32(Mid.X)), uint32(FMath::RoundToInt32(Mid.Y)), 11u)) << 32)
			| uint64(Hash3(uint32(FMath::RoundToInt32(Size.X)), uint32(FMath::RoundToInt32(Size.Y)), 13u));
		Keys.Add(Key);
		if (!GrassClearKeys.Contains(Key)) Fresh.Add(C.WorldBounds);
		Found.Add(MoveTemp(C));
	};
	auto FromMesh = [&](const FTransform& LocalToWorld, const FBox& LocalBox)
	{
		const FVector Scale = LocalToWorld.GetScale3D().GetAbs();
		const FVector Size = LocalBox.GetSize() * Scale;
		if (Size.Z > ClearMaxHeightCm || FMath::Max(Size.X, Size.Y) > ClearMaxSpanCm || FMath::Max(Size.X, Size.Y) < 1.0) return;
		// 25 cm and lower: the full rim; toward the height limit the rim closes to a third (grass stands against a crate)
		const float Low = 1.f - FMath::Clamp((float(Size.Z) - 25.f) / FMath::Max(ClearMaxHeightCm - 25.f, 1.f), 0.f, 1.f);
		Add(LocalToWorld, LocalBox, ClearReachCm * FMath::Lerp(0.35f, 1.f, Low));
	};
	if (ClearMaxHeightCm > 0.f)
	{
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			const bool bFamily = It->ActorHasTag(UDinkArtFamilySubsystem::FamilyTag);
			const bool bAuthored = !bFamily && It->ActorHasTag(TEXT("DinkAuthoredArt"));
			if ((!bFamily && !bAuthored) || It->IsHidden()) continue;
			TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
			for (UStaticMeshComponent* M : Meshes)
			{
				if (!M->GetStaticMesh() || !M->IsVisible()) continue;
				if (bFamily && !M->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)) continue;
				const FBox Box = M->GetStaticMesh()->GetBoundingBox();
				{
					// props only: never the ground, the water or vegetation (weeds, ferns, flowers and bushes are family meshes too
					// and grow in the grass)
					const UMaterialInterface* Material = M->GetNumMaterials() > 0 ? M->GetMaterial(0) : nullptr;
					const FString MaterialName = Material ? Material->GetName() : FString();
					const FString Name = M->GetStaticMesh()->GetName();
					if (M->GetFName() == TEXT("EnvSwapVisual") || MaterialName.Contains(TEXT("Terrain")) || MaterialName.Contains(TEXT("Meadow")) || MaterialName.Contains(TEXT("Earth"))
						|| MaterialName.Contains(TEXT("Water")) || MaterialName.Contains(TEXT("Veg")) || Name.Contains(TEXT("Grass")) || Name.Contains(TEXT("Veg_"))
						|| Name.Contains(TEXT("Weed")) || Name.Contains(TEXT("Fern")) || Name.Contains(TEXT("Flower")) || Name.Contains(TEXT("Reed")) || Name.Contains(TEXT("Bush"))
						|| Name.Contains(TEXT("Thorn")) || Name.Contains(TEXT("Vine")) || Name.Contains(TEXT("Stump")) || Name.Contains(TEXT("Tree"))) continue;
				}
				if (const UInstancedStaticMeshComponent* Instanced = Cast<UInstancedStaticMeshComponent>(M))
				{
					for (int32 Index = 0; Index < Instanced->GetInstanceCount(); ++Index)
					{
						FTransform T;
						if (Instanced->GetInstanceTransform(Index, T, /*bWorldSpace*/ true)) FromMesh(T, Box);
					}
				}
				else FromMesh(M->GetComponentTransform(), Box);
			}
			// a ground decal (blood splat, burn hole) lies flat: the carpet opens over the middle of its sheet
			TInlineComponentArray<UDecalComponent*> Decals(*It);
			for (const UDecalComponent* D : Decals)
			{
				if (D->GetFName() != TEXT("EnvDecal")) continue;
				const double Half = FMath::Max(D->DecalSize.Y, D->DecalSize.Z) * 0.7;
				Add(FTransform(D->GetComponentLocation()), FBox(FVector(-Half, -Half, -1.0), FVector(Half, Half, 1.0)), ClearReachCm);
			}
		}
		for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
		{
			if (It->ActorHasTag(UDinkArtFamilySubsystem::FamilyTag) || It->ActorHasTag(TEXT("DinkAuthoredArt"))) continue;   // seen above
			TInlineComponentArray<UDecalComponent*> Decals(*It);
			for (const UDecalComponent* D : Decals)
			{
				if (D->GetFName() != TEXT("EnvDecal")) continue;
				const double Half = FMath::Max(D->DecalSize.Y, D->DecalSize.Z) * 0.7;
				Add(FTransform(D->GetComponentLocation()), FBox(FVector(-Half, -Half, -1.0), FVector(Half, Half, 1.0)), ClearReachCm);
			}
		}
	}
	// cells that were built before a clearing arrived (a screen dressed while its neighbour is in view) grow again without it
	if (!Fresh.IsEmpty())
	{
		for (auto It = GrassCells.CreateIterator(); It; ++It)
		{
			const FVector2D Origin(It.Key().X * GrassCellCm, It.Key().Y * GrassCellCm);
			const FBox2D CellBox(Origin, Origin + FVector2D(GrassCellCm));
			if (!Fresh.ContainsByPredicate([&](const FBox2D& B) { return B.Intersect(CellBox); })) continue;
			for (UInstancedStaticMeshComponent* C : It.Value().Components) if (C) C->DestroyComponent();
			It.RemoveCurrent();
		}
	}
	const int32 Before = GrassClears.Num();
	GrassClears = MoveTemp(Found);
	GrassClearKeys = MoveTemp(Keys);
	if (GrassClears.Num() != Before) UE_LOG(LogDink, Display, TEXT("DINK ENV: %d grass clearings (low props and decals), %d new"), GrassClears.Num(), Fresh.Num());
}

float UDinkEnvironmentSubsystem::GrassClearAt(const FVector2D& At, const TArray<int32>& Candidates) const
{
	// 1 over the footprint, falling to 0 across the rim
	float Clear = 0.f;
	for (const int32 Index : Candidates)
	{
		const FGrassClear& C = GrassClears[Index];
		if (!C.WorldBounds.IsInside(At)) continue;
		const FVector L = C.WorldToLocal.TransformPosition(FVector(At, 0.0));
		const FVector Scale = C.WorldToLocal.GetScale3D().GetAbs();
		const double DX = FMath::Max3(C.LocalBox.Min.X - L.X, 0.0, L.X - C.LocalBox.Max.X) / FMath::Max(Scale.X, 1e-4);
		const double DY = FMath::Max3(C.LocalBox.Min.Y - L.Y, 0.0, L.Y - C.LocalBox.Max.Y) / FMath::Max(Scale.Y, 1e-4);
		Clear = FMath::Max(Clear, FMath::Clamp(1.f - float(FMath::Sqrt(DX * DX + DY * DY)) / FMath::Max(C.ReachCm, 1.f), 0.f, 1.f));
	}
	return Clear;
}

void UDinkEnvironmentSubsystem::GatherGrassSources()
{
	GrassSources.Reset();
	UWorld* World = GetWorld();
	if (!World) return;
	auto Add = [&](const FTransform& LocalToWorld, const FBox& LocalBox, bool bWear, float Reach, bool bShort = false)
	{
		FGrassSource S;
		S.WorldToLocal = LocalToWorld.Inverse();
		S.LocalBox = LocalBox;
		S.bWear = bWear;
		S.bShort = bShort;
		S.ReachCm = Reach;
		for (const double X : {LocalBox.Min.X, LocalBox.Max.X}) for (const double Y : {LocalBox.Min.Y, LocalBox.Max.Y})
			S.WorldBounds += FVector2D(LocalToWorld.TransformPosition(FVector(X, Y, 0.0)));
		S.WorldBounds = S.WorldBounds.ExpandBy(Reach);
		GrassSources.Add(S);
	};
	auto AroundPoint = [&](const FVector& At, double HalfX, double HalfY, bool bWear, float Reach, bool bShort = false)
	{
		Add(FTransform(FVector(At.X, At.Y, 0.0)), FBox(FVector(-HalfX, -HalfY, -1.0), FVector(HalfX, HalfY, 1.0)), bWear, Reach, bShort);
	};
	// town house fronts: short turf along the wall (the footprint itself carries no grass)
	for (const FGrassBlock& Block : GrassBlocks)
	{
		Add(Block.WorldToLocal.Inverse(), FBox(FVector(Block.LocalRect.Min, -1.0), FVector(Block.LocalRect.Max, 1.0)), false, ShortReachCm, true);
	}
	// what a placement's class says about the ground around it (greybox screens; authored screens speak through their meshes)
	auto FromClass = [&](const FString& Class, const FVector& At, double WidthCm, double HeightCm)
	{
		if (Class.StartsWith(TEXT("door_")) || Class.EndsWith(TEXT("_door"))) { AroundPoint(At, FMath::Max(60.0, WidthCm * 0.3), 60.0, true, WearReachCm); return; }
		if (Class.StartsWith(TEXT("fence_")))
		{
			// a rail drawn north-south runs up the picture; east-west along it
			if (Class.Contains(TEXT("_ns"))) AroundPoint(At - FVector(0.0, HeightCm * 0.25, 0.0), 25.0, HeightCm * 0.3, false, ShortReachCm, true);
			else if (Class.Contains(TEXT("_ew"))) AroundPoint(At, WidthCm * 0.5, 25.0, false, ShortReachCm, true);
			else AroundPoint(At, WidthCm * 0.35, WidthCm * 0.35, false, ShortReachCm * 0.7f, true);
			return;
		}
		if (Class.StartsWith(TEXT("tree_")) || Class.StartsWith(TEXT("stump")) || Class.StartsWith(TEXT("sign")) || Class.StartsWith(TEXT("well"))) { AroundPoint(At, 45.0, 45.0, false, RankReachCm * 1.3f); return; }
		if (Class.StartsWith(TEXT("rock")) || Class.StartsWith(TEXT("boulder")) || Class.Contains(TEXT("gravestone"))) { AroundPoint(At, WidthCm * 0.4, 40.0, false, RankReachCm); return; }
		if (Class.StartsWith(TEXT("town_wall")) || Class.StartsWith(TEXT("cottage")) || Class.StartsWith(TEXT("wall_"))) { AroundPoint(At, WidthCm * 0.5, 40.0, false, ShortReachCm, true); return; }
	};
	for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
	{
		if (!It->Origin || !It->Card || It->IsHidden() || IsScreenDressed(It->ScreenNumber)) continue;
		const FVector Scale = It->Card->GetComponentScale();
		FromClass(It->Origin->ClassId.ToString(), It->Card->GetComponentLocation(), Scale.X * 100.0, Scale.Z * 100.0);
	}
	for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It)
	{
		if (!It->InstanceOrigins || IsScreenDressed(It->ScreenNumber)) continue;
		TInlineComponentArray<UInstancedStaticMeshComponent*> Components(*It);
		for (const FDinkInstanceOrigin& O : It->InstanceOrigins->Origins)
		{
			for (UInstancedStaticMeshComponent* C : Components)
			{
				FTransform T;
				if (C->GetFName() == O.ComponentName && C->GetInstanceTransform(O.InstanceIndex, T, /*bWorldSpace*/ true))
					FromClass(O.ClassId.ToString(), T.GetLocation(), T.GetScale3D().X * 100.0, T.GetScale3D().Z * 100.0);
			}
		}
	}
	// doors: every warp trigger wears the turf in front of it
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (const UDinkWarpComponent* Warp = It->FindComponentByClass<UDinkWarpComponent>())
		{
			const FVector Extent = Warp->GetScaledBoxExtent();
			AroundPoint(Warp->GetComponentLocation(), FMath::Max(Extent.X, 50.0), FMath::Max(Extent.Y, 50.0), true, WearReachCm);
			AroundPoint(Warp->GetComponentLocation(), FMath::Max(Extent.X, 50.0), FMath::Max(Extent.Y, 50.0), false, WearReachCm + ShortReachCm, true);
		}
		if (!It->ActorHasTag(TEXT("DinkAuthoredArt"))) continue;
		TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
		for (UStaticMeshComponent* M : Meshes)
		{
			if (!M->GetStaticMesh() || M->GetFName() == TEXT("EnvSwapVisual") || Cast<UInstancedStaticMeshComponent>(M)) continue;
			const UMaterialInterface* Material = M->GetNumMaterials() > 0 ? M->GetMaterial(0) : nullptr;
			const FString MaterialName = Material ? Material->GetName() : FString();
			const FString Name = M->GetStaticMesh()->GetName();
			const FBox Box = M->GetStaticMesh()->GetBoundingBox();
			if (MaterialName.Contains(TEXT("Terrain_Earth")))
			{
				Add(M->GetComponentTransform(), Box, true, WearReachCm * 0.3f);              // paths and yards: thin at the very rim
				Add(M->GetComponentTransform(), Box, false, ShortReachCm, true);             // and short turf beside them
			}
			else if (MaterialName.Contains(TEXT("M_Env_Water"))) Add(M->GetComponentTransform(), Box, false, RankReachCm * 1.4f);          // pond and stream rims
			else if (Name.Contains(TEXT("Oak")) || Name.Contains(TEXT("Pine")) || Name.Contains(TEXT("Willow")) || Name.Contains(TEXT("Stump")))
				AroundPoint(M->GetComponentLocation(), 45.0, 45.0, false, RankReachCm * 1.3f);
			else if (Name.Contains(TEXT("Boulder")) || Name.Contains(TEXT("Well")) || Name.Contains(TEXT("Trough")))
				Add(M->GetComponentTransform(), Box, false, RankReachCm);
			else if (Name.Contains(TEXT("Fence")) || Name.Contains(TEXT("Wall")) || Name.Contains(TEXT("Cottage")) || Name.Contains(TEXT("Gate")) || Name.Contains(TEXT("Barn")) || Name.Contains(TEXT("Chimney")))
				Add(M->GetComponentTransform(), Box, false, ShortReachCm, true);                // walls and fence lines: short turf
		}
	}
	UE_LOG(LogDink, Display, TEXT("DINK ENV: %d grass sources (rank growth and wear)"), GrassSources.Num());
}

void UDinkEnvironmentSubsystem::GrassInfluence(const FVector2D& At, const TArray<int32>& Candidates, float& OutRank, float& OutWear, float& OutShort) const
{
	OutRank = 0.f; OutWear = 0.f; OutShort = 0.f;
	for (const int32 Index : Candidates)
	{
		const FGrassSource& S = GrassSources[Index];
		if (!S.WorldBounds.IsInside(At)) continue;
		const FVector L = S.WorldToLocal.TransformPosition(FVector(At, 0.0));
		const double DX = FMath::Max3(S.LocalBox.Min.X - L.X, 0.0, L.X - S.LocalBox.Max.X);
		const double DY = FMath::Max3(S.LocalBox.Min.Y - L.Y, 0.0, L.Y - S.LocalBox.Max.Y);
		const double Distance = FMath::Sqrt(DX * DX + DY * DY) / FMath::Max(double(S.WorldToLocal.GetScale3D().X), 1e-4);
		const float F = FMath::Clamp(1.f - float(Distance) / FMath::Max(S.ReachCm, 1.f), 0.f, 1.f);
		if (S.bWear) OutWear = FMath::Max(OutWear, F); else if (S.bShort) OutShort = FMath::Max(OutShort, F); else OutRank = FMath::Max(OutRank, F);
	}
}

void UDinkEnvironmentSubsystem::BuildGrassCell(const FIntPoint& Cell, float Density)
{
	FDinkGrassCell& Entry = GrassCells.Add(Cell);
	if (!Holder || GrassMeshes.IsEmpty()) return;
	const FVector2D Origin(Cell.X * GrassCellCm, Cell.Y * GrassCellCm);
	// mesh table: field carpet | short turf | dry drifts | rank tufts | accents (weeds, flowers, clumps)
	TArray<UStaticMesh*> Table;
	for (UStaticMesh* M : GrassMeshes) Table.Add(M);
	const int32 FirstShort = Table.Num();
	for (UStaticMesh* M : GrassShortMeshes) Table.Add(M);
	const int32 FirstDry = Table.Num();
	for (UStaticMesh* M : GrassDryMeshes) Table.Add(M);
	const int32 FirstRank = Table.Num();
	for (UStaticMesh* M : GrassRankMeshes) Table.Add(M);
	const int32 FirstAccent = Table.Num();
	for (UStaticMesh* M : AccentMeshes) Table.Add(M);
	TArray<TArray<FTransform>> Instances;
	Instances.SetNum(Table.Num());
	const FBox2D CellBox(Origin, Origin + FVector2D(GrassCellCm));
	TArray<int32> Near;
	bool bAnyRank = false;
	for (int32 Index = 0; Index < GrassSources.Num(); ++Index)
	{
		if (!GrassSources[Index].WorldBounds.Intersect(CellBox)) continue;
		Near.Add(Index);
		bAnyRank |= !GrassSources[Index].bWear;
	}
	TArray<int32> NearClears;
	for (int32 Index = 0; Index < GrassClears.Num(); ++Index)
	{
		if (GrassClears[Index].WorldBounds.Intersect(CellBox)) NearClears.Add(Index);
	}
	auto Value = [](const FVector2D& P, double Cm, uint32 Seed)
	{
		const double X = P.X / Cm, Y = P.Y / Cm;
		const int32 IX = FMath::FloorToInt32(X), IY = FMath::FloorToInt32(Y);
		const float FX = FMath::SmoothStep(0.f, 1.f, float(X - IX)), FY = FMath::SmoothStep(0.f, 1.f, float(Y - IY));
		auto Corner = [Seed](int32 A, int32 B) { return Unit(Hash3(uint32(A), uint32(B), Seed)); };
		return FMath::Lerp(FMath::Lerp(Corner(IX, IY), Corner(IX + 1, IY), FX), FMath::Lerp(Corner(IX, IY + 1), Corner(IX + 1, IY + 1), FX), FY);
	};
	const double Lean = GrassLeanDeg;
	auto Place = [&](int32 MeshIndex, uint32 H, const FVector2D& At, float Z, float Footprint, float Height, double LeanDeg)
	{
		Instances[MeshIndex].Emplace(
			FRotator((Unit(Hash3(H, 29u, 17u)) - 0.5) * 2.0 * LeanDeg, Unit(Hash3(H, 23u, 7u)) * 360.0, (Unit(Hash3(H, 31u, 19u)) - 0.5) * 2.0 * LeanDeg),
			FVector(At, Z), FVector(Footprint, Footprint, Height));
	};
	auto Grid = [&](float PerM2, uint32 Salt, TFunctionRef<void(uint32, const FVector2D&, float)> Each)
	{
		if (PerM2 <= 0.f) return;
		const float StepCm = 100.f / FMath::Sqrt(PerM2);
		const int32 N = FMath::Max(1, FMath::RoundToInt(GrassCellCm / StepCm));
		const float Step = GrassCellCm / N;
		for (int32 Y = 0; Y < N; ++Y)
			for (int32 X = 0; X < N; ++X)
			{
				const uint32 H = Hash3(uint32(Cell.X * 73856093) ^ Salt, uint32(Cell.Y * 19349663), uint32(Y * N + X));
				const FVector2D At = Origin + FVector2D((X + Unit(H)) * Step, (Y + Unit(Hash3(H, 3u, 9u))) * Step);
				float Z = 0.f;
				if (GroundAt(At, H, Z)) Each(H, At, Z);
			}
	};
	const float V = FMath::Clamp(GrassFieldVariation, 0.f, 1.f);
	const float Share = Density / FMath::Max(GrassDensityPerM2, 0.001f);
	// --- the field: tall where it is left alone, short where it is walked, grazed or thin, dry in drifts
	Grid(Density, 0u, [&](uint32 H, const FVector2D& At, float Z)
	{
		float Rank = 0.f, Wear = 0.f, Short = 0.f;
		GrassInfluence(At, Near, Rank, Wear, Short);
		// a clearing over a low prop or a decal: nothing on the footprint, a ragged thinning rim, shorter blades toward it
		const float Clear = NearClears.IsEmpty() ? 0.f : GrassClearAt(At, NearClears);
		if (Clear > 0.f && Clear + (Unit(Hash3(H, 67u, 41u)) - 0.5f) * 0.4f > 0.5f) return;
		// the end of the meadow (path, bare earth, shore): over the mask's soft edge the carpet thins out and steps down in
		// height with noise, so it does not end as a wall of full-height cards
		const float EdgeT = FMath::SmoothStep(GrassMinCover - 0.1f, GrassMinCover + 0.4f, LastCover);
		if (Unit(Hash3(H, 71u, 43u)) < (1.f - EdgeT) * 0.55f * EdgeFeather) return;
		const float Taper = FMath::Lerp(1.f, FMath::Lerp(0.4f, 1.f, EdgeT * (0.75f + 0.25f * Unit(Hash3(H, 73u, 47u)))), EdgeFeather)
			* (1.f - 0.55f * FMath::SmoothStep(0.f, 0.5f, Clear)) * FMath::Lerp(1.f, 1.f - 0.45f * Wear, EdgeFeather);
		const float Noise = 0.65f * Value(At, 1100.0, 91u) + 0.35f * Value(At, 300.0, 57u);
		const float EdgeWear = 1.f - FMath::SmoothStep(GrassMinCover, 0.98f, LastCover);     // the tile mask's path rims
		// the carpet's own edge: where the meadow mask ends within 0.8 m, the grass steps down to short, thin turf before bare ground
		float Brink = 0.f;
		if (!IsScreenDressed(-1))
		{
			for (const FVector2D& Off : {FVector2D(80.0, 0.0), FVector2D(-80.0, 0.0), FVector2D(0.0, 80.0), FVector2D(0.0, -80.0), FVector2D(160.0, 0.0), FVector2D(-160.0, 0.0), FVector2D(0.0, 160.0), FVector2D(0.0, -160.0)})
			{
				const float C = MaskCoverAt(At + Off);
				if (C >= 0.f && C < GrassMinCover) Brink += Off.SizeSquared() < 10000.0 ? 0.25f : 0.125f;
			}
		}
		Brink = FMath::Min(Brink * 1.4f, 1.f);
		const float Worn = FMath::Max3(Wear, EdgeWear * 0.8f, Brink) * V;
		const float Grazed = (1.f - FMath::SmoothStep(0.22f, 0.42f, Noise)) * V * (1.f - Rank);
		// a door step and a path rim are thin as well as short; the apron right at a door is trodden bare
		if (Unit(Hash3(H, 43u, 23u)) < FMath::Max(Worn * Worn * 0.7f, FMath::SmoothStep(0.55f, 0.8f, Wear))) return;
		// short turf along walls, fence lines, paths and round doors: closed within about two thirds of the reach, ragged beyond
		const float Along = FMath::SmoothStep(0.f, 0.35f, Short) * V;
		const bool bShort = Unit(Hash3(H, 47u, 3u)) < FMath::Max3(Worn, Grazed * 0.5f, Along);   // grazed stretches keep half their tall grass: mixed, not mown
		const float Pick = Unit(Hash3(H, 37u, 21u));
		float Footprint = FMath::Lerp(GrassScaleMin, GrassScaleMax, Unit(Hash3(H, 5u, 11u)));
		if (bShort && !GrassShortMeshes.IsEmpty() && Wear > 0.3f)
		{
			// trodden: lower still toward the door
			Place(FirstShort + int32(Hash3(H, 41u, 13u) % uint32(GrassShortMeshes.Num())), H, At, Z, Footprint * 1.2f, Footprint * FMath::Lerp(0.6f, 0.9f, Pick) * FMath::Max(Taper, 0.6f), Lean * 0.4);
			return;
		}
		if (bShort)
		{
			if (!GrassShortMeshes.IsEmpty())
			{
				Place(FirstShort + int32(Hash3(H, 41u, 13u) % uint32(GrassShortMeshes.Num())), H, At, Z, Footprint * 1.3f, Footprint * FMath::Lerp(1.0f, 1.3f, Pick) * FMath::Max(Taper, 0.6f), Lean * 0.6);   // wider than the tall patch: turf closes
			}
			else
			{
				// no short mesh yet: the field patch shrunk as a whole (never squashed flat), so the turf shows between
				Footprint *= FMath::Lerp(0.5f, 0.68f, Pick);
				Place(int32(Hash3(H, 41u, 13u) % uint32(GrassMeshes.Num())), H, At, Z, Footprint, Footprint * FMath::Lerp(GrassHeightMin, GrassHeightMax, Pick), Lean * 0.6);
			}
			return;
		}
		const float DryNoise = 0.7f * Value(At, 900.0, 133u) + 0.3f * Value(At, 240.0, 71u);
		// the general field is a uniformly scaled patch (field_scale caps its height); it stands taller only where rank growth is left
		Footprint *= GrassFieldFootprint;
		const float Tall = Taper * GrassFieldScale * FMath::Lerp(GrassHeightMin, GrassHeightMax, Pick) * FMath::Lerp(1.f, FMath::Lerp(0.85f, 1.15f, FMath::SmoothStep(0.3f, 0.8f, Noise)), V) * (1.f + 0.6f * Rank);
		if (!GrassDryMeshes.IsEmpty() && DryNoise > 0.78f - DryShare && Unit(Hash3(H, 53u, 29u)) < 0.8f)
		{
			Place(FirstDry + int32(Hash3(H, 41u, 13u) % uint32(GrassDryMeshes.Num())), H, At, Z, Footprint, Tall, Lean);
			return;
		}
		Place(int32(Hash3(H, 41u, 13u) % uint32(GrassMeshes.Num())), H, At, Z, Footprint, Tall, Lean);
	});
	// --- rank tufts: nobody mows along a fence, against a wall, round a trunk or on a pond's rim
	if (bAnyRank && !GrassRankMeshes.IsEmpty())
	{
		Grid(RankDensityPerM2 * Share, 0x51EDu, [&](uint32 H, const FVector2D& At, float Z)
		{
			float Rank = 0.f, Wear = 0.f, Short = 0.f;
			GrassInfluence(At, Near, Rank, Wear, Short);
			// right against a wall or under a fence rail a few tufts escape the scythe: a thin fringe, not a hedge
			if (Short > 0.8f && Unit(Hash3(H, 61u, 37u)) < RankEdgeShare) Rank = FMath::Max(Rank, Short);
			if (Rank <= 0.f || Wear > 0.35f || Unit(Hash3(H, 59u, 31u)) > Rank * Rank * 1.2f) return;
			if (!NearClears.IsEmpty() && GrassClearAt(At, NearClears) > 0.1f) return;
			const float Footprint = FMath::Lerp(0.85f, 1.25f, Unit(Hash3(H, 5u, 11u)));
			Place(FirstRank + int32(Hash3(H, 41u, 13u) % uint32(GrassRankMeshes.Num())), H, At, Z, Footprint, Footprint * FMath::Lerp(1.05f, 1.5f, Unit(Hash3(H, 37u, 21u))), Lean * 1.3);
		});
	}
	// --- accents in drifts: each kind grows where its own slow noise is high, so clover, weeds and flowers stand in clusters
	if (!AccentMeshes.IsEmpty())
	{
		const float Boost = 1.f / FMath::Max(1.f - AccentCluster, 0.15f);
		Grid(AccentDensityPerM2 * Share * Boost, 0x9E37u, [&](uint32 H, const FVector2D& At, float Z)
		{
			const int32 Kind = int32(Hash3(H, 41u, 13u) % uint32(AccentMeshes.Num()));
			const float Drift = 0.75f * Value(At, 620.0, 200u + uint32(Kind)) + 0.25f * Value(At, 170.0, 300u + uint32(Kind));
			if (Drift < AccentCluster) return;
			float Rank = 0.f, Wear = 0.f, Short = 0.f;
			GrassInfluence(At, Near, Rank, Wear, Short);
			if (Wear > 0.5f || Short > 0.5f) return;
			if (!NearClears.IsEmpty() && GrassClearAt(At, NearClears) > 0.1f) return;
			const float Scale = FMath::Lerp(0.8f, 1.2f, Unit(Hash3(H, 5u, 11u)));
			Place(FirstAccent + Kind, H, At, Z, Scale, Scale * FMath::Lerp(0.9f, 1.15f, Unit(Hash3(H, 37u, 21u))), Lean);
		});
	}
	for (int32 Index = 0; Index < Instances.Num(); ++Index)
	{
		if (Instances[Index].IsEmpty()) continue;
		UInstancedStaticMeshComponent* Component = NewObject<UInstancedStaticMeshComponent>(Holder);
		Component->SetupAttachment(Holder->GetRootComponent());
		Component->SetStaticMesh(Table[Index]);
		// each slot takes the "_Scatter" twin of its material when one is imported (ground-matched colour,
		// distance thinning); a material without a twin is left as authored
		for (int32 Slot = 0; Slot < Component->GetNumMaterials(); ++Slot)
		{
			const UMaterialInterface* Authored = Component->GetMaterial(Slot);
			if (!Authored) continue;
			const FString Twin = Authored->GetOutermost()->GetName() + TEXT("_Scatter");
			TObjectPtr<UMaterialInterface>& Cached = ScatterMaterials.FindOrAdd(Twin);
			if (!Cached && FPackageName::DoesPackageExist(Twin))
			{
				Cached = LoadObject<UMaterialInterface>(nullptr, *(Twin + TEXT(".") + FPackageName::GetShortName(Twin)));
			}
			if (Cached) Component->SetMaterial(Slot, Cached);
		}
		Component->SetMobility(EComponentMobility::Movable);
		Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Component->SetGenerateOverlapEvents(false);
		Component->SetCanEverAffectNavigation(false);
		Component->SetCastShadow(false);
		Component->bCastContactShadow = false;
		Component->bAffectDistanceFieldLighting = false;
		Component->bAffectDynamicIndirectLighting = false;
		Component->SetCullDistance(GrassFarCm + GrassCellCm);
		Component->NumCustomDataFloats = 0;
		Component->RegisterComponent();
		Component->AddInstances(Instances[Index], false, true);
		Entry.Components.Add(Component);
	}
}

void UDinkEnvironmentSubsystem::UpdateGrass(const FVector& Camera, float Density)
{
	if (!FMath::IsNearlyEqual(Density, LastGrassDensity))
	{
		ClearGrass();
		LastGrassDensity = Density;
	}
	if (Density <= 0.f || GrassMeshes.IsEmpty()) { ClearGrass(); return; }
	const FIntPoint Centre(FMath::FloorToInt32(Camera.X / GrassCellCm), FMath::FloorToInt32(Camera.Y / GrassCellCm));
	const int32 Radius = FMath::CeilToInt32(GrassFarCm / GrassCellCm);
	// drop cells that left the range, then build missing ones nearest first, a few per frame
	for (auto It = GrassCells.CreateIterator(); It; ++It)
	{
		if (FMath::Abs(It.Key().X - Centre.X) <= Radius + 1 && FMath::Abs(It.Key().Y - Centre.Y) <= Radius + 1) continue;
		for (UInstancedStaticMeshComponent* C : It.Value().Components) if (C) C->DestroyComponent();
		It.RemoveCurrent();
	}
	int32 Budget = 6;
	for (int32 Ring = 0; Ring <= Radius && Budget > 0; ++Ring)
		for (int32 DY = -Ring; DY <= Ring && Budget > 0; ++DY)
			for (int32 DX = -Ring; DX <= Ring && Budget > 0; ++DX)
			{
				if (FMath::Max(FMath::Abs(DX), FMath::Abs(DY)) != Ring) continue;
				const FIntPoint Cell(Centre.X + DX, Centre.Y + DY);
				const FVector2D Mid((Cell.X + 0.5f) * GrassCellCm, (Cell.Y + 0.5f) * GrassCellCm);
				if (FVector2D::Distance(Mid, FVector2D(Camera)) > GrassFarCm + GrassCellCm * 0.75f || GrassCells.Contains(Cell)) continue;
				BuildGrassCell(Cell, Density);
				--Budget;
			}
	// only the cells around the camera cast shadows; no contact shadows anywhere (ambient occlusion grounds the rest)
	for (auto& Pair : GrassCells)
	{
		const FVector2D Mid((Pair.Key.X + 0.5f) * GrassCellCm, (Pair.Key.Y + 0.5f) * GrassCellCm);
		const bool bShadow = FVector2D::Distance(Mid, FVector2D(Camera)) < GrassShadowCm + GrassCellCm * 0.5f;
		if (bShadow == Pair.Value.bCastsShadow) continue;
		Pair.Value.bCastsShadow = bShadow;
		for (UInstancedStaticMeshComponent* C : Pair.Value.Components) if (C) C->SetCastShadow(bShadow);
	}
}

void UDinkEnvironmentSubsystem::ApplyNeighbourFamilies(const FVector& Around)
{
	// The family layer dresses a screen when the player enters it; the screens in view would still show their
	// sprite cards. Dress everything within sight of the current screen as well (idempotent per screen).
	for (const FScreenInfo& Screen : Screens)
	{
		if (!TownScreens.IsEmpty() && FVector::DistSquared2D(Screen.Centre, Around) < FMath::Square(16000.0)) ApplyTownHouses(Screen.Number, Screen.Corners);
		if (!ForestTrees.IsEmpty() && FVector::DistSquared2D(Screen.Centre, Around) < FMath::Square(22000.0)) ApplyForest(Screen.Number, Screen.Corners);
		if ((!ReliefRocks.IsEmpty() || !WaterTileRects.IsEmpty()) && FVector::DistSquared2D(Screen.Centre, Around) < FMath::Square(22000.0)) ApplyRelief(Screen.Number, Screen.Corners);
		if (!DecalClasses.IsEmpty() && FVector::DistSquared2D(Screen.Centre, Around) < FMath::Square(16000.0)) ApplyDecals(Screen.Number);
	}
	UDinkArtFamilySubsystem* Families = GetWorld()->GetSubsystem<UDinkArtFamilySubsystem>();
	if (!Families || !Families->IsReady()) return;
	for (const FScreenInfo& Screen : Screens)
	{
		if (FVector::DistSquared2D(Screen.Centre, Around) < FMath::Square(16000.0) && !Families->IsScreenApplied(Screen.Number))
		{
			Families->ApplyScreen(Screen.Number);
		}
	}
}

void UDinkEnvironmentSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	UWorld* World = GetWorld();
	if (!bActive || !World) return;
	const APlayerController* PC = World->GetFirstPlayerController();
	if (!PC || !PC->PlayerCameraManager) return;
	const FVector Camera = PC->PlayerCameraManager->GetCameraLocation();

	const float Wind = FMath::Max(CVarDinkWind.GetValueOnGameThread(), 0.f);
	if (WindCollection && !FMath::IsNearlyEqual(Wind, LastWind))
	{
		LastWind = Wind;
		UKismetMaterialLibrary::SetScalarParameterValue(World, WindCollection, TEXT("Wind"), Wind);
	}

	const bool bFollow = CVarDinkBackdrop.GetValueOnGameThread() != 0;
	for (const TWeakObjectPtr<AActor>& Backdrop : Backdrops)
	{
		AActor* Actor = Backdrop.Get();
		if (!Actor) continue;
		Actor->SetActorHiddenInGame(!bFollow);
		if (bFollow) Actor->SetActorLocation(FVector(Camera.X, Camera.Y, Actor->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
	}

	const UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
	const ADinkScreenVolume* Current = Grey ? Grey->GetCurrentScreen() : nullptr;
	if (InteriorExposure)
	{
		InteriorExposure->bEnabled = Current && Current->bIndoor && CVarDinkInteriorExposure.GetValueOnGameThread() != 0;
	}
	UpdateIndoor(Current, DeltaTime);

	// Authored screens hide their greybox ground: the carpet asks the meadow meshes there instead of the tile mask.
	const double Now = World->GetTimeSeconds();
	if (Now >= NextDressedCheck)
	{
		NextDressedCheck = Now + 2.0;
		TSet<int32> Dressed;
		for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It)
		{
			if (It->Visual && It->Visual->bHiddenInGame) Dressed.Add(It->ScreenNumber);
		}
		if (Dressed.Num() != DressedScreens.Num())
		{
			DressedScreens = MoveTemp(Dressed);
				bGrassSourcesStale = true;
			BareGround.Reset();
			for (TActorIterator<AActor> It(World); It; ++It)
			{
				if (!It->ActorHasTag(TEXT("DinkAuthoredArt"))) continue;
				TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
				for (UStaticMeshComponent* M : Meshes)
				{
					const UMaterialInterface* Material = M->GetNumMaterials() > 0 ? M->GetMaterial(0) : nullptr;
					const FString Name = Material ? Material->GetName() : FString();
					if (Name.Contains(TEXT("Terrain_Earth")) || Name.Contains(TEXT("M_Env_Water"))) BareGround.Add(M);
				}
			}
			ClearGrass();
		}
	}
	const int32 ScreenNumber = Current ? Current->ScreenNumber : -1;
	if (ScreenNumber != LastFamilyScreen && Current)
	{
		LastFamilyScreen = ScreenNumber;
		ApplyNeighbourFamilies(DinkLayout::MapPixelToUnreal(Current->Corners, 300.0, 200.0));
		FindBurnables();
		if (!bGrassSourcesStale) GatherGrassClears();   // the screens dressed just now bring their low props
	}
	if (Now >= NextBurnCheck)
	{
		NextBurnCheck = Now + 0.1;
		if (!Burnables.IsEmpty()) UpdateBurnables();
		if (Now > 1.0) UpdateCorpses(ScreenNumber);
	}
	if (Now >= NextStateCheck)
	{
		NextStateCheck = Now + 0.5;
		UpdateStateSwaps();
	}
	if (bGrassSourcesStale && Now > 3.0)
	{
		// after the art layers have run (authored meshes, swaps): what the carpet grows along and wears around
		bGrassSourcesStale = false;
		GatherGrassSources();
		GatherGrassClears();
		ClearGrass();
	}
	const float Density = Current && Current->bIndoor ? 0.f : GrassDensityPerM2 * FMath::Max(CVarDinkGrassDensity.GetValueOnGameThread(), 0.f);
	UpdateGrass(Camera, Density);
}
