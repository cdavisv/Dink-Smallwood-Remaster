#include "DinkArtSubsystem.h"
#include "Misc/ScopeExit.h"
#include "DinkArtContextActor.h"
#include "DinkEarlyPostureAnimInstance.h"
#include "DinkPostureComponent.h"
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "DinkScreenExposureComponent.h"
#include "DinkCoreModule.h"
#include "DinkOriginComponent.h"
#include "DinkHumanoidComponent.h"
#include "DinkPlayerActionComponent.h"
#include "Animation/BlendSpace.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkWarpComponent.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/PointLight.h"
#include "Engine/RectLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Materials/MaterialInterface.h"
#include "Misc/PackageName.h"
#include "Misc/App.h"

// Photoreal pass: the dressed screens' ground and pond meshes keep their authored material slots;
// at runtime the flat-tiled meadow, earth and stream water are swapped for the world-aligned
// environment materials (Scripts/import_environment_materials.sh). Missing targets leave the
// authored material in place. `dink.EnvMaterials 0` before map load restores the authored look.
static TAutoConsoleVariable<int32> CVarDinkEnvMaterials(TEXT("dink.EnvMaterials"), 1,
	TEXT("1 = use the environment terrain/water materials on authored ground and pond meshes (read when art is applied)."));

// Photoreal pass: authored screens name the old stylised vegetation meshes in their manifests (origin and
// screen bindings win over family rows). Content/Dink/Data/Environment/environment.json "mesh_swaps" maps
// such a mesh package to photoreal meshes; the authored component stays as the collision proxy (hidden)
// and a visual-only component with the new mesh is attached to it. Rendering processes only, so the
// headless tests keep checking the manifests as written. dink.EnvMeshSwaps 0 (command line) turns it off.
static TAutoConsoleVariable<int32> CVarDinkEnvMeshSwaps(TEXT("dink.EnvMeshSwaps"), 1,
	TEXT("1 = swap the old stylised vegetation of authored screens for the photoreal meshes (visual only; read when art is applied)."));

static int32 DinkApplyEnvironmentMeshSwap(UStaticMeshComponent* Component)
{
	if (!Component || !Component->GetStaticMesh() || !FApp::CanEverRender() || CVarDinkEnvMeshSwaps.GetValueOnGameThread() == 0) return 0;
	static bool bLoaded = false;
	static TMap<FString, TArray<FString>> Table;
	static TMap<FString, FName> OnlyTag; // mesh_swap_only_tag: a swap limited to owners with this actor tag (one screen's art)
	if (!bLoaded)
	{
		bLoaded = true;
		FString Text;
		TSharedPtr<FJsonObject> Root;
		const TSharedPtr<FJsonObject>* Swaps = nullptr;
		if (FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Environment/environment.json")))
			&& FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) && Root.IsValid()
			&& Root->TryGetObjectField(TEXT("mesh_swaps"), Swaps) && Swaps)
		{
			for (const auto& Pair : (*Swaps)->Values)
			{
				TArray<FString>& Out = Table.Add(FString(Pair.Key.ToView()));
				for (const TSharedPtr<FJsonValue>& V : Pair.Value->AsArray()) Out.Add(V->AsString());
			}
			const TSharedPtr<FJsonObject>* Tags = nullptr;
			if (Root->TryGetObjectField(TEXT("mesh_swap_only_tag"), Tags) && Tags)
			{
				for (const auto& Pair : (*Tags)->Values) OnlyTag.Add(FString(Pair.Key.ToView()), FName(*Pair.Value->AsString()));
			}
		}
	}
	const TArray<FString>* Choices = Table.Find(Component->GetStaticMesh()->GetOutermost()->GetName());
	if (!Choices || Choices->IsEmpty()) return 0;
	if (const FName* Tag = OnlyTag.Find(Component->GetStaticMesh()->GetOutermost()->GetName()))
	{
		if (!Component->GetOwner() || !Component->GetOwner()->ActorHasTag(*Tag)) return 0;
	}
	const FVector At = Component->GetComponentLocation();
	const uint32 Pick = HashCombine(GetTypeHash(FMath::RoundToInt32(At.X)), GetTypeHash(FMath::RoundToInt32(At.Y))) % uint32(Choices->Num());
	const FString& Path = (*Choices)[Pick];
	if (!FPackageName::DoesPackageExist(Path.Left(Path.Find(TEXT("."))))) return 0;
	UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!Mesh) return 0;
	UStaticMeshComponent* Visual = NewObject<UStaticMeshComponent>(Component->GetOwner(), TEXT("EnvSwapVisual"));
	Visual->SetMobility(Component->Mobility);
	Visual->SetupAttachment(Component);
	Visual->SetStaticMesh(Mesh);
	Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Visual->SetGenerateOverlapEvents(false);
	Visual->SetCanEverAffectNavigation(false);
	// the new mesh stands on its own base centre; the old one may have been scaled to a sprite: keep world scale 1
	Visual->SetUsingAbsoluteScale(true);
	Visual->SetRelativeLocation(FVector::ZeroVector);
	Component->GetOwner()->AddInstanceComponent(Visual);
	Visual->RegisterComponent();
	// the authored component keeps its collision and is no longer drawn or lit
	Component->SetHiddenInGame(true);
	Component->SetCastShadow(false);
	Component->bAffectDistanceFieldLighting = false;
	Component->bAffectDynamicIndirectLighting = false;
	Component->MarkRenderStateDirty();
	return 1;
}

static TAutoConsoleVariable<int32> CVarDinkPhotorealNPCs(TEXT("dink.PhotorealNPCs"), 1,
	TEXT("1 = Mother and Milder use SK_<Name>_Photoreal when it is imported on the same skeleton and the process renders (read when their art is applied); 0 = the meshes of characters.json."));

/** Photoreal pass (round 6), visual only: same skeleton or the manifest's mesh stays; headless runs keep the manifest's mesh. */
static USkeletalMesh* DinkPhotorealNpcMesh(USkeletalMesh* Mesh)
{
	if (!Mesh || CVarDinkPhotorealNPCs.GetValueOnGameThread() == 0 || !FApp::CanEverRender()) return Mesh;
	const FString Name = Mesh->GetName();
	if (Name != TEXT("SK_Mother") && Name != TEXT("SK_Milder")) return Mesh;
	const FString Short = Name.RightChop(3);
	const FString Package = FString::Printf(TEXT("/Game/Dink/Photoreal/Characters/%s/SK_%s_Photoreal"), *Short, *Short);
	if (!FPackageName::DoesPackageExist(Package)) return Mesh;
	USkeletalMesh* Photoreal = LoadObject<USkeletalMesh>(nullptr, *FString::Printf(TEXT("%s.SK_%s_Photoreal"), *Package, *Short), nullptr, LOAD_NoWarn | LOAD_Quiet);
	return Photoreal && Photoreal->GetSkeleton() == Mesh->GetSkeleton() ? Photoreal : Mesh;
}

static TAutoConsoleVariable<int32> CVarDinkPhotorealHero(TEXT("dink.PhotorealHero"), 1,
	TEXT("1 = the player uses SK_Dink_Photoreal when it is imported (read when the player's art is applied); 0 = the manifest's hero."));

static void DinkApplyEnvironmentMaterials(UStaticMeshComponent* Component)
{
	if (!Component || CVarDinkEnvMaterials.GetValueOnGameThread() == 0) return;
	// Camera occluders are faded through a reviewed per-material mapping (camera_materials.json): leave them alone.
	if (const AActor* Owner = Component->GetOwner(); Owner && Owner->ActorHasTag(TEXT("DinkCameraOccluder"))) return;
	static const TPair<const TCHAR*, const TCHAR*> Table[] = {
		{TEXT("/Game/Dink/Materials/Stonebrook/MI_Stonebrook_Meadow"), TEXT("/Game/Dink/Materials/Environment/MI_Env_Terrain_MeadowTurf")},
		{TEXT("/Game/Dink/Materials/StonebrookFields/MI_Stonebrook_Meadow"), TEXT("/Game/Dink/Materials/Environment/MI_Env_Terrain_MeadowTurf")},
		{TEXT("/Game/Dink/Materials/Stonebrook/MI_Stonebrook_Earth"), TEXT("/Game/Dink/Materials/Environment/MI_Env_Terrain_EarthWorn")},
		{TEXT("/Game/Dink/Materials/StonebrookFields/MI_Stonebrook_Earth"), TEXT("/Game/Dink/Materials/Environment/MI_Env_Terrain_EarthWorn")},
		{TEXT("/Game/Dink/Materials/StonebrookFields/MI_Fields_StreamWater"), TEXT("/Game/Dink/Materials/Environment/M_Env_Water")},
	};
	static TMap<FString, TWeakObjectPtr<UMaterialInterface>> Cache;
	for (int32 Slot = 0; Slot < Component->GetNumMaterials(); ++Slot)
	{
		const UMaterialInterface* Current = Component->GetMaterial(Slot);
		if (!Current) continue;
		const FString Package = Current->GetOutermost()->GetName();
		for (const TPair<const TCHAR*, const TCHAR*>& Row : Table)
		{
			if (Package != Row.Key) continue;
			TWeakObjectPtr<UMaterialInterface>& Cached = Cache.FindOrAdd(Row.Value);
			if (!Cached.IsValid() && FPackageName::DoesPackageExist(Row.Value))
			{
				Cached = LoadObject<UMaterialInterface>(nullptr, *(FString(Row.Value) + TEXT(".") + FPackageName::GetShortName(FString(Row.Value))));
			}
			// The pig pen is trodden mud: plain earth there, without the grass patches of the worn-earth instance.
			const AActor* EarthOwner = Component->GetOwner();
			const bool bPlainEarth = FCString::Strstr(Row.Value, TEXT("EarthWorn")) && EarthOwner && EarthOwner->ActorHasTag(TEXT("DinkArtScreen_407"));
			if (bPlainEarth)
			{
				static TWeakObjectPtr<UMaterialInterface> Plain;
				if (!Plain.IsValid()) Plain = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Dink/Materials/Environment/MI_Env_Terrain_EarthPath.MI_Env_Terrain_EarthPath"));
				if (Plain.IsValid()) Component->SetMaterial(Slot, Plain.Get());
			}
			else if (Cached.IsValid())
			{
				Component->SetMaterial(Slot, Cached.Get());
				// Single-layer water is not a Nanite shading model; draw the pond surface as a regular mesh.
				if (FCString::Strstr(Row.Value, TEXT("M_Env_Water"))) { Component->bDisallowNanite = true; Component->MarkRenderStateDirty(); }
			}
			break;
		}
	}
}

namespace
{
	TAutoConsoleVariable<int32> CVarDinkBodyAnimation(TEXT("dink.BodyAnimation"), 1,
		TEXT("1: hero and humanoid NPCs use the animation pass's native body animation; 0: template blueprint and blend space."));
	TAutoConsoleVariable<int32> CVarDinkArtEnabled(TEXT("dink.ArtEnabled"), 1,
		TEXT("Apply authored Blender art at world startup (0: original greybox, 1: authored art)."));

	FName AnimationSetOf(const TSharedPtr<FJsonObject>& Row)
	{
		FString Set;
		return Row && Row->TryGetStringField(TEXT("animation_set"), Set) ? FName(*Set) : FName();
	}

	FVector VectorField(const TSharedPtr<FJsonObject>& Row, const TCHAR* Key, FVector Default = FVector::ZeroVector)
	{
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		if (Row->TryGetArrayField(Key, Values) && Values->Num() == 3)
		{
			return FVector((*Values)[0]->AsNumber(), (*Values)[1]->AsNumber(), (*Values)[2]->AsNumber());
		}
		return Default;
	}

	FTransform RowTransform(const TSharedPtr<FJsonObject>& Row, const TCHAR* LocationKey)
	{
		const FVector R = VectorField(Row, TEXT("rotation_deg"));
		return FTransform(FRotator(R.X, R.Y, R.Z), VectorField(Row, LocationKey), VectorField(Row, TEXT("scale"), FVector::OneVector));
	}

    struct FAuthoredLight
    {
        bool bRect = false;
        FVector Position = FVector::ZeroVector;
        FRotator Rotation = FRotator::ZeroRotator;
        float Lumens = 0, Kelvin = 0, Radius = 0, Width = 0, Height = 0;
    };

    bool LightNumber(const TSharedPtr<FJsonObject>& Row, const TCHAR* Key, float& Out)
    {
        const auto Value = Row->TryGetField(Key);
        if (!Value.IsValid() || Value->Type != EJson::Number) return false;
        const double Number = Value->AsNumber();
        if (!FMath::IsFinite(Number) || Number > double(MAX_flt) || Number < -double(MAX_flt)) return false;
        Out = static_cast<float>(Number);
        return FMath::IsFinite(Out);
    }

    bool LightVector(const TSharedPtr<FJsonObject>& Row, const TCHAR* Key, FVector& Out)
    {
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (!Row->TryGetArrayField(Key, Values) || Values->Num() != 3) return false;
        for (int32 Index = 0; Index != 3; ++Index)
        {
            const auto& Value = (*Values)[Index];
            if (!Value.IsValid() || Value->Type != EJson::Number || !FMath::IsFinite(Value->AsNumber())) return false;
            Out[Index] = Value->AsNumber();
        }
        return true;
    }

    // Parse the entire light list before replacing/hiding/spawning any scene actor.
    // An omitted kind remains the original isotropic point-light path.
    bool ReadAuthoredLights(const TSharedPtr<FJsonObject>& Manifest, TArray<FAuthoredLight>& Out)
    {
        const auto Field = Manifest->TryGetField(TEXT("lights"));
        if (!Field.IsValid()) return true;
        if (Field->Type != EJson::Array) return false;
        for (const auto& Value : Field->AsArray())
        {
            if (!Value.IsValid() || Value->Type != EJson::Object) return false;
            const auto Row = Value->AsObject();
            FString Kind = TEXT("point");
            if (Row->HasField(TEXT("kind")) && !Row->TryGetStringField(TEXT("kind"), Kind)) return false;
            if (Kind != TEXT("point") && Kind != TEXT("rect")) return false;
            FAuthoredLight Light;
            Light.bRect = Kind == TEXT("rect");
            if (!LightVector(Row, TEXT("world_cm"), Light.Position) ||
                !LightNumber(Row, TEXT("lumens"), Light.Lumens) || Light.Lumens < 0 ||
                !LightNumber(Row, TEXT("kelvin"), Light.Kelvin) || Light.Kelvin <= 0 ||
                !LightNumber(Row, TEXT("radius_cm"), Light.Radius) || Light.Radius <= 0) return false;
            if (Light.bRect)
            {
                FVector Rotation;
                if (!LightVector(Row, TEXT("rotation_deg"), Rotation) ||
                    !LightNumber(Row, TEXT("source_width_cm"), Light.Width) || Light.Width <= 0 ||
                    !LightNumber(Row, TEXT("source_height_cm"), Light.Height) || Light.Height <= 0) return false;
                Light.Rotation = FRotator(Rotation.X, Rotation.Y, Rotation.Z);
            }
            else if (Row->HasField(TEXT("source_width_cm")) || Row->HasField(TEXT("source_height_cm"))) return false;
            Out.Add(Light);
        }
        return true;
    }
}

bool UDinkArtSubsystem::DoesSupportWorldType(EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UDinkArtSubsystem::OnWorldBeginPlay(UWorld& World)
{
    bInitialApplicationComplete = false;
    AuthoredCollisionScreens.Reset();
    ON_SCOPE_EXIT { bInitialApplicationComplete = true; };
	Super::OnWorldBeginPlay(World);
    LoadExteriorCameraRules();
	if (!CVarDinkArtEnabled.GetValueOnGameThread()) return;
	TArray<FString> DressingFiles;
	IFileManager::Get().FindFiles(DressingFiles, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/*.json")), true, false);
	DressingFiles.Sort();
	for (const FString& File : DressingFiles) ApplyManifest(World, File);
	ApplyCharacters(World);
}

void UDinkArtSubsystem::ApplyManifest(UWorld& World, const FString& ManifestFile)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art") / ManifestFile))) return;
	TSharedPtr<FJsonObject> Manifest;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest.IsValid())
	{
		UE_LOG(LogDink, Warning, TEXT("Art: invalid manifest; retaining greybox"));
		return;
	}
	ApplyManifest(World, Manifest, ManifestFile);
}

void UDinkArtSubsystem::ApplyManifest(UWorld& World, const TSharedPtr<FJsonObject>& Manifest, const FString& ManifestFile)
{
	FString Schema;
	if (!Manifest->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-art/1")) return;

	// Do not dress unrelated maps or test worlds: each manifest names its source screen.
	int32 TargetScreen = 1;
	Manifest->TryGetNumberField(TEXT("screen"), TargetScreen);
	bool bHasScreen = false;
	for (TActorIterator<ADinkGreyboxScreen> It(&World); It; ++It) bHasScreen |= It->ScreenNumber == TargetScreen;
	if (!bHasScreen) return;

    TArray<FAuthoredLight> Lights;
    if (!ReadAuthoredLights(Manifest, Lights))
    {
        UE_LOG(LogDink, Warning, TEXT("Art: invalid lights; retaining scene (%s)"), *ManifestFile);
        return;
    }

	// Validate all referenced assets before hiding anything: an incomplete checkout stays playable.
	TMap<FString, UStaticMesh*> Meshes;
	for (const TCHAR* Field : {TEXT("replacements"), TEXT("elements")})
	{
		const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
		if (!Manifest->TryGetArrayField(Field, Rows)) continue;
		for (const TSharedPtr<FJsonValue>& Value : *Rows)
		{
			const TSharedPtr<FJsonObject> Row = Value->AsObject();
			FString Path;
			if (!Row.IsValid() || !Row->TryGetStringField(TEXT("mesh"), Path)) return;
			// This optional policy belongs only to physical elements. Validate the entire
			// manifest before replacements, hiding, or spawning can change the scene.
			if (!Manifest->HasField(TEXT("context")) && FCString::Strcmp(Field, TEXT("elements")) == 0 &&
				Row->HasField(TEXT("can_affect_navigation")))
			{
				const TSharedPtr<FJsonValue> Navigation = Row->TryGetField(TEXT("can_affect_navigation"));
				if (!Navigation.IsValid() || Navigation->Type != EJson::Boolean)
				{
					UE_LOG(LogDink, Warning, TEXT("Art: can_affect_navigation must be a boolean; retaining scene (%s)"), *ManifestFile);
					return;
				}
			}
			if (!Meshes.Contains(Path))
			{
				UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Path);
				if (!Mesh)
				{
					UE_LOG(LogDink, Warning, TEXT("Art: missing %s; retaining greybox. Run Scripts/import_stonebrook_art.sh"), *Path);
					return;
				}
				Meshes.Add(Path, Mesh);
			}
		}
	}

    if (Manifest->HasField(TEXT("context")))
    {
        if (ADinkArtContextActor* Context=ADinkArtContextActor::CreateFromManifest(World,Manifest,Meshes,TargetScreen))
            Context->Tags.Add(FName(*FString::Printf(TEXT("DinkArtManifest_%s"),*ManifestFile)));
        else UE_LOG(LogDink,Warning,TEXT("Art: invalid render-only context %s; skipped without changing scene"),*ManifestFile);
        return;
    }

	TMap<FString, ADinkPlaceholderActor*> Placements;
	for (TActorIterator<ADinkPlaceholderActor> It(&World); It; ++It) Placements.Add(It->Origin->OriginId.ToString(), *It);
	int32 Replaced = 0, Added = 0, MeshSwaps = 0;
	const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
	if (Manifest->TryGetArrayField(TEXT("replacements"), Rows))
	{
		for (const TSharedPtr<FJsonValue>& Value : *Rows)
		{
			const TSharedPtr<FJsonObject> Row = Value->AsObject();
			ADinkPlaceholderActor* A = Placements.FindRef(Row->GetStringField(TEXT("origin")));
			if (!A) continue;
			A->Tags.Add(TEXT("DinkAuthoredArt"));
			A->Card->SetMobility(EComponentMobility::Movable);
			A->Card->EmptyOverrideMaterials();
			A->Card->SetStaticMesh(Meshes.FindChecked(Row->GetStringField(TEXT("mesh"))));
			A->Card->SetRelativeTransform(RowTransform(Row, TEXT("offset_cm")));
			A->Card->SetCollisionProfileName(TEXT("BlockAll"));
			A->Card->SetGenerateOverlapEvents(false);
			Replaced++;
		}
	}
	if (Manifest->TryGetArrayField(TEXT("warp_overrides"), Rows))
	{
		for (const TSharedPtr<FJsonValue>& Value : *Rows)
		{
			const TSharedPtr<FJsonObject> Row = Value->AsObject();
			if (ADinkWarpPlaceholderActor* A = Cast<ADinkWarpPlaceholderActor>(Placements.FindRef(Row->GetStringField(TEXT("origin")))))
			{
				A->Warp->SetMobility(EComponentMobility::Movable);
				A->Warp->SetWorldLocation(VectorField(Row, TEXT("world_cm")));
				A->Warp->SetBoxExtent(VectorField(Row, TEXT("extent_cm")));
			}
		}
	}
	if (Manifest->TryGetArrayField(TEXT("hide_origins"), Rows))
	{
		for (const TSharedPtr<FJsonValue>& Value : *Rows)
		{
			if (ADinkPlaceholderActor* A = Placements.FindRef(Value->AsString())) A->Card->SetHiddenInGame(true);
		}
	}
	if (Manifest->TryGetArrayField(TEXT("hide_screen_visuals"), Rows))
	{
		TSet<int32> Screens;
		for (const TSharedPtr<FJsonValue>& Value : *Rows) Screens.Add(int32(Value->AsNumber()));
		for (TActorIterator<ADinkGreyboxScreen> It(&World); It; ++It)
		{
			if (!Screens.Contains(It->ScreenNumber)) continue;
			It->Visual->SetHiddenInGame(true);
			TArray<UInstancedStaticMeshComponent*> Decor;
			It->GetComponents(Decor);
			for (UInstancedStaticMeshComponent* Component : Decor) Component->SetHiddenInGame(true);
		}
		// Screen volumes create their presentation cubes in BeginPlay, which can run
		// after this subsystem. Record the choice and hide any cubes already present.
		for (TActorIterator<ADinkScreenVolume> It(&World); It; ++It)
		{
			if (Screens.Contains(It->ScreenNumber)) It->SetInteriorWallVisualsHidden(true);
		}
	}
	if (Manifest->TryGetArrayField(TEXT("authored_collision_screens"), Rows))
	{
		TSet<int32> Screens, PreserveLow;
		for (const TSharedPtr<FJsonValue>& Value : *Rows) Screens.Add(int32(Value->AsNumber()));
        for (int32 Screen : Screens) AuthoredCollisionScreens.Add(Screen);
		const TArray<TSharedPtr<FJsonValue>>* LowScreens = nullptr;
		if (Manifest->TryGetArrayField(TEXT("preserve_low_collision_screens"), LowScreens))
			for (const TSharedPtr<FJsonValue>& Value : *LowScreens) PreserveLow.Add(int32(Value->AsNumber()));
		for (TActorIterator<ADinkGreyboxScreen> It(&World); It; ++It)
		{
			if (!Screens.Contains(It->ScreenNumber)) continue;
			It->CollisionSolid->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			// Fitted land replaces the ground/solid prisms. Water/low boundaries may
			// retain their separate walker-blocking, projectile-passing channel.
			if (!PreserveLow.Contains(It->ScreenNumber))
				It->CollisionLow->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		}
	}
	if (Manifest->TryGetArrayField(TEXT("elements"), Rows))
	{
		for (const TSharedPtr<FJsonValue>& Value : *Rows)
		{
			const TSharedPtr<FJsonObject> Row = Value->AsObject();
			const TSharedPtr<FJsonValue> Navigation = Row->TryGetField(TEXT("can_affect_navigation"));
			const bool bDisableNavigation = Navigation.IsValid() && !Navigation->AsBool();
			const FTransform Transform = RowTransform(Row, TEXT("world_cm"));
			AStaticMeshActor* A = bDisableNavigation
				? World.SpawnActorDeferred<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FTransform::Identity)
				: World.SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), Transform);
			if (!A) continue;
			A->Tags.Add(TEXT("DinkAuthoredArt"));
			A->Tags.Add(FName(*FString::Printf(TEXT("DinkArtScreen_%d"), TargetScreen)));
			bool bCameraOccluder=false;
			if (Row->TryGetBoolField(TEXT("camera_occluder"), bCameraOccluder) && bCameraOccluder) A->Tags.Add(TEXT("DinkCameraOccluder"));
			UStaticMeshComponent* Component = A->GetStaticMeshComponent();
			if (bDisableNavigation)
			{
				Component->SetCanEverAffectNavigation(false);
				A->FinishSpawning(Transform);
			}
			Component->SetStaticMesh(Meshes.FindChecked(Row->GetStringField(TEXT("mesh"))));
			DinkApplyEnvironmentMaterials(Component);
			// Per-triangle authored collision preserves openings and the visible prop footprint.
			Component->SetCollisionProfileName(TEXT("BlockAll"));
			bool bCollision = true;
			Row->TryGetBoolField(TEXT("collision"), bCollision);
			if (!bCollision) Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Component->SetGenerateOverlapEvents(false);
			if (Navigation.IsValid() && !bDisableNavigation) Component->SetCanEverAffectNavigation(true);
			RegisterExteriorCameraRule(ManifestFile,Row,TargetScreen,Component);
			MeshSwaps += DinkApplyEnvironmentMeshSwap(Component);
			Added++;
		}
	}
    for (const FAuthoredLight& Row : Lights)
	{
        ALight* Light = Row.bRect
            ? static_cast<ALight*>(World.SpawnActor<ARectLight>(Row.Position, Row.Rotation))
            : static_cast<ALight*>(World.SpawnActor<APointLight>(Row.Position, FRotator::ZeroRotator));
        if (!Light) continue;
        Light->Tags.Add(TEXT("DinkAuthoredArt"));
        ULocalLightComponent* C = CastChecked<ULocalLightComponent>(Light->GetLightComponent());
        C->SetMobility(EComponentMobility::Movable);
        C->SetIntensityUnits(ELightUnits::Lumens);
        C->SetIntensity(Row.Lumens);
        C->SetUseTemperature(true);
        C->SetTemperature(Row.Kelvin);
        C->SetAttenuationRadius(Row.Radius);
        if (Row.bRect)
        {
            URectLightComponent* Rect = CastChecked<URectLightComponent>(C);
            Rect->SetSourceWidth(Row.Width);
            Rect->SetSourceHeight(Row.Height);
            // Installed setter clamps even a zero request to0.1cm.
            Rect->SetBarnDoorLength(0.1f);
        }
        else
        {
            CastChecked<UPointLightComponent>(C)->SetSourceRadius(18.f);
            // Photoreal pass: firelight flickers (a light-function material; authored lumens and colour unchanged).
            if (Row.Kelvin <= 2200.f && CVarDinkEnvMaterials.GetValueOnGameThread() != 0)
            {
                static const TCHAR* Flicker = TEXT("/Game/Dink/Materials/Environment/M_Env_FireFlicker");
                if (FPackageName::DoesPackageExist(Flicker))
                {
                    C->SetLightFunctionMaterial(LoadObject<UMaterialInterface>(nullptr, *(FString(Flicker) + TEXT(".M_Env_FireFlicker"))));
                }
            }
        }
	}
	if (Manifest->TryGetArrayField(TEXT("postprocess"), Rows))
	{
		for (const TSharedPtr<FJsonValue>& Value : *Rows)
		{
			const TSharedPtr<FJsonObject> Row = Value->AsObject();
			AActor* A = World.SpawnActor<AActor>();
			if (!A) continue;
			A->Tags.Add(TEXT("DinkAuthoredArt"));
			UBoxComponent* Bounds = NewObject<UBoxComponent>(A, TEXT("ArtExposureBounds"));
			A->SetRootComponent(Bounds);
			Bounds->SetBoxExtent(VectorField(Row, TEXT("extent_cm")));
			// Postprocess volume containment uses the parent's physics shape. Keep
			// a query shape without any blocking or overlap responses.
			Bounds->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
			Bounds->SetCollisionResponseToAllChannels(ECR_Ignore);
			Bounds->SetGenerateOverlapEvents(false);
			Bounds->SetWorldLocation(VectorField(Row, TEXT("world_cm")));
			A->AddInstanceComponent(Bounds);
			Bounds->RegisterComponent();
			UPostProcessComponent* PP = NewObject<UPostProcessComponent>(A, TEXT("ArtExposure"));
			PP->SetupAttachment(Bounds);
			PP->bEnabled = false;
			PP->bUnbound = false;
			PP->BlendRadius = 100.f;
			PP->BlendWeight = 1.f;
			PP->Priority = 10.f;
			PP->Settings.bOverride_AutoExposureBias = true;
			PP->Settings.AutoExposureBias = Row->GetNumberField(TEXT("exposure_bias"));
			PP->Settings.bOverride_BloomIntensity = true;
			PP->Settings.BloomIntensity = 0.15f;
			A->AddInstanceComponent(PP);
			PP->RegisterComponent();
            UDinkScreenExposureComponent* Ownership=NewObject<UDinkScreenExposureComponent>(A,TEXT("ArtExposureOwner"));
            Ownership->ConfigureExposure(PP,TargetScreen);
            A->AddInstanceComponent(Ownership);
            Ownership->RegisterComponent();
			float Distance = 0.f;
			UE_LOG(LogDink, Display, TEXT("Art exposure: bias %.1f, bounds contain centre %s"),
				PP->Settings.AutoExposureBias, PP->EncompassesPoint(VectorField(Row, TEXT("world_cm")), 0.f, &Distance) ? TEXT("yes") : TEXT("no"));
		}
	}
	if (MeshSwaps > 0) UE_LOG(LogDink, Display, TEXT("DINK ART: %d authored vegetation elements show photoreal meshes (dink.EnvMeshSwaps)"), MeshSwaps);
	UE_LOG(LogDink, Display, TEXT("DINK ART OK: %d placements replaced, %d authored elements; original scripts retained, authored collision active"), Replaced, Added);
}

void UDinkArtSubsystem::ApplyCharacters(UWorld& World)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/characters.json")))) return;
	TSharedPtr<FJsonObject> Manifest;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest) return;
	FString Schema;
	if (!Manifest->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-characters/1")) return;
	const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
	if (!Manifest->TryGetArrayField(TEXT("placements"), Rows)) return;
	TMap<FString, ADinkPlaceholderActor*> Placements;
	for (TActorIterator<ADinkPlaceholderActor> It(&World); It; ++It) Placements.Add(It->Origin->OriginId.ToString(), *It);
	int32 Applied = 0;
	for (const TSharedPtr<FJsonValue>& Value : *Rows)
	{
		const TSharedPtr<FJsonObject> Row = Value->AsObject();
		if (!Row) continue;
		ADinkPlaceholderActor* A = Placements.FindRef(Row->GetStringField(TEXT("origin")));
		if (!A) continue;
		USkeletalMesh* Mesh = DinkPhotorealNpcMesh(LoadObject<USkeletalMesh>(nullptr, *Row->GetStringField(TEXT("mesh"))));
		UBlendSpace* Locomotion = LoadObject<UBlendSpace>(nullptr, *Row->GetStringField(TEXT("locomotion")));
		if (!Mesh || !Locomotion || Mesh->GetSkeleton() != Locomotion->GetSkeleton())
		{
			UE_LOG(LogDink, Warning, TEXT("Character art: missing or incompatible rig for %s; retaining sprite"), *Row->GetStringField(TEXT("origin")));
			continue;
		}
		A->GetRootComponent()->SetMobility(EComponentMobility::Movable);
		UDinkHumanoidComponent* Human = NewObject<UDinkHumanoidComponent>(A, TEXT("AuthoredHumanoid"));
		Human->SetupAttachment(A->GetRootComponent());
		Human->SetRelativeTransform(RowTransform(Row, TEXT("offset_cm")));
		A->AddInstanceComponent(Human);
		Human->RegisterComponent();
		Human->Configure(Mesh, Locomotion, CVarDinkBodyAnimation.GetValueOnGameThread() != 0 ? &GetAnimationLibrary() : nullptr, AnimationSetOf(Row));
		UCapsuleComponent* Body = NewObject<UCapsuleComponent>(A, TEXT("AuthoredBody"));
		Body->SetupAttachment(A->GetRootComponent());
		Body->SetMobility(EComponentMobility::Movable);
		const float Radius = Row->GetNumberField(TEXT("capsule_radius_cm"));
		const float HalfHeight = Row->GetNumberField(TEXT("capsule_halfheight_cm"));
		Body->InitCapsuleSize(Radius, HalfHeight);
		Body->SetRelativeLocation(FVector(0, 0, HalfHeight));
		Body->SetCollisionProfileName(TEXT("Pawn"));
		Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
		Body->SetGenerateOverlapEvents(false);
		Body->ComponentTags.Add(TEXT("DinkAuthoredInteraction"));
		A->AddInstanceComponent(Body);
		Body->RegisterComponent();
		A->Card->SetHiddenInGame(true);
		A->Card->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		A->Tags.Add(TEXT("DinkAuthoredArt"));
		A->Tags.Add(TEXT("DinkHumanoid"));
		Applied++;
	}
	UE_LOG(LogDink, Display, TEXT("DINK CHARACTER ART OK: %d animated original actors"), Applied);
}


bool UDinkArtSubsystem::ApplyPlayer(USkeletalMeshComponent& Component)
{
	if (!CVarDinkArtEnabled.GetValueOnGameThread()) return false;
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/characters.json")))) return false;
	TSharedPtr<FJsonObject> Manifest;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest) return false;
	FString Schema;
	if (!Manifest->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-characters/1")) return false;
	const TSharedPtr<FJsonObject>* Row = nullptr;
	if (!Manifest->TryGetObjectField(TEXT("player"), Row) || !Row || !Row->IsValid()) return false;
	FString Path;
	if (!(*Row)->TryGetStringField(TEXT("mesh"), Path)) return false;
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *Path);
	USkeletalMesh* Reference = Component.GetSkeletalMeshAsset();
	if (!Mesh || !Reference || Mesh->GetSkeleton() != Reference->GetSkeleton())
	{
		UE_LOG(LogDink, Warning, TEXT("Player art: missing or incompatible mesh %s; retaining current character"), *Path);
		return false;
	}
	// Photoreal pass: the photoreal hero replaces the manifest's mesh behind dink.PhotorealHero when the
	// process renders (headless tests keep validating the manifest's mesh). Same skeleton or it is refused;
	// capsule, sockets, animation blueprint and clips are untouched.
	if (CVarDinkPhotorealHero.GetValueOnGameThread() != 0 && FApp::CanEverRender())
	{
		static const TCHAR* PhotorealHero = TEXT("/Game/Dink/Photoreal/Characters/Dink/SK_Dink_Photoreal");
		if (FPackageName::DoesPackageExist(PhotorealHero))
		{
			USkeletalMesh* Photoreal = LoadObject<USkeletalMesh>(nullptr, *(FString(PhotorealHero) + TEXT(".SK_Dink_Photoreal")));
			if (Photoreal && Photoreal->GetSkeleton() == Reference->GetSkeleton())
			{
				Mesh = Photoreal;
				UE_LOG(LogDink, Display, TEXT("DINK PLAYER ART: photoreal hero active (dink.PhotorealHero 0 restores %s)"), *Path);
			}
			else UE_LOG(LogDink, Warning, TEXT("Player art: photoreal hero missing or on another skeleton; keeping %s"), *Path);
		}
	}
	Component.SetSkeletalMesh(Mesh);
	// Animation pass: the native body instance replaces the template animation blueprint when
	// its clips are imported and fit this skeleton; otherwise the blueprint stays.
	if (CVarDinkBodyAnimation.GetValueOnGameThread() != 0 && !GetAnimationLibrary().IsEmpty())
	{
		UClass* Previous = Component.GetAnimClass();
		Component.SetAnimInstanceClass(UDinkBodyAnimInstance::StaticClass());
		UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(Component.GetAnimInstance());
		if (Body && Body->Configure(GetAnimationLibrary(), TEXT("Hero")))
		{
			UE_LOG(LogDink, Display, TEXT("DINK PLAYER ANIMATION OK: native body animation, %d clips"), GetAnimationLibrary().Num());
		}
		else
		{
			UE_LOG(LogDink, Warning, TEXT("Player animation: hero clip set incomplete; keeping the animation blueprint"));
			Component.SetAnimInstanceClass(Previous);
		}
	}
    ConfigurePlayerActions(Component);
    FString PosturePath;
    UClass* PostureClass=nullptr;
    if ((*Row)->TryGetStringField(TEXT("posture_class"),PosturePath))
    {
        UClass* Candidate=LoadClass<UDinkEarlyPostureAnimInstance>(nullptr,*PosturePath);
        const UAnimBlueprintGeneratedClass* Graph=Cast<UAnimBlueprintGeneratedClass>(Candidate);
        if (Graph && Graph->GetTargetSkeleton()==Mesh->GetSkeleton()) PostureClass=Candidate;
        else UE_LOG(LogDink,Warning,TEXT("Player posture class missing or incompatible: %s"),*PosturePath);
    }
    if (AActor* Owner=Component.GetOwner())
    {
        UDinkPostureComponent* Posture=Owner->FindComponentByClass<UDinkPostureComponent>();
        if (!Posture && PostureClass)
        {
            Posture=NewObject<UDinkPostureComponent>(Owner,TEXT("PlayerPosture"));
            Owner->AddInstanceComponent(Posture); Posture->RegisterComponent();
        }
        if (Posture) Posture->Configure(&Component,PostureClass);
    }
	UE_LOG(LogDink, Display, TEXT("DINK PLAYER ART OK: %s; existing locomotion and collision retained"), *Path);
	return true;
}


bool UDinkArtSubsystem::ApplyScriptCharacter(AActor* Actor, FName Script, float SpriteScale)
{
	if (!Actor || Script.IsNone() || !CVarDinkArtEnabled.GetValueOnGameThread()) return false;
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/characters.json")))) return false;
	TSharedPtr<FJsonObject> Manifest;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest) return false;
	FString Schema;
	if (!Manifest->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-characters/1")) return false;
	const TSharedPtr<FJsonObject>* Profiles = nullptr;
	const TSharedPtr<FJsonObject>* Row = nullptr;
	if (!Manifest->TryGetObjectField(TEXT("script_profiles"), Profiles) || !Profiles || !Profiles->IsValid() ||
		!(*Profiles)->TryGetObjectField(Script.ToString().ToLower(), Row) || !Row || !Row->IsValid()) return false;
	USkeletalMesh* Mesh = DinkPhotorealNpcMesh(LoadObject<USkeletalMesh>(nullptr, *(*Row)->GetStringField(TEXT("mesh"))));
	UBlendSpace* Locomotion = LoadObject<UBlendSpace>(nullptr, *(*Row)->GetStringField(TEXT("locomotion")));
	if (!Mesh || !Locomotion || Mesh->GetSkeleton() != Locomotion->GetSkeleton()) return false;
	if (!Actor->GetRootComponent()) return false;
	Actor->GetRootComponent()->SetMobility(EComponentMobility::Movable);
	// The generic marker constructor uses a nonuniform root scale. Replace it with
	// the actual script size before attaching anatomical art and collision.
	const float LogicalScale = FMath::Max(SpriteScale, .001f);
	Actor->SetActorScale3D(FVector(LogicalScale));
	UDinkHumanoidComponent* Human = FindObject<UDinkHumanoidComponent>(Actor, TEXT("ScriptHumanoid"));
	if (!Human)
	{
		Human = NewObject<UDinkHumanoidComponent>(Actor, TEXT("ScriptHumanoid"));
		Human->SetupAttachment(Actor->GetRootComponent());
		Actor->AddInstanceComponent(Human);
		Human->RegisterComponent();
	}
	FTransform Presentation = RowTransform(*Row, TEXT("offset_cm"));
	// The marker root is at world ground+60 regardless of sp_size; retain world offset.
	Presentation.SetLocation(Presentation.GetLocation() / LogicalScale);
	Human->SetRelativeTransform(Presentation);
	Human->Configure(Mesh, Locomotion, CVarDinkBodyAnimation.GetValueOnGameThread() != 0 ? &GetAnimationLibrary() : nullptr, AnimationSetOf(*Row));
	UCapsuleComponent* Body = FindObject<UCapsuleComponent>(Actor, TEXT("ScriptHumanoidBody"));
	if (!Body)
	{
		Body = NewObject<UCapsuleComponent>(Actor, TEXT("ScriptHumanoidBody"));
		Body->SetupAttachment(Actor->GetRootComponent());
		Body->SetMobility(EComponentMobility::Movable);
		Body->ComponentTags.Add(TEXT("DinkAuthoredInteraction"));
		Body->SetCanEverAffectNavigation(false);
		Actor->AddInstanceComponent(Body);
	}
	const float Radius = (*Row)->GetNumberField(TEXT("capsule_radius_cm"));
	const float HalfHeight = (*Row)->GetNumberField(TEXT("capsule_halfheight_cm"));
	Body->InitCapsuleSize(Radius, HalfHeight);
	const FVector Offset = VectorField(*Row, TEXT("offset_cm"));
	Body->SetRelativeLocation(Offset / LogicalScale + FVector(0, 0, HalfHeight));
	Body->SetCollisionProfileName(TEXT("Pawn"));
	Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Body->SetGenerateOverlapEvents(false);
	if (!Body->IsRegistered()) Body->RegisterComponent();
	TInlineComponentArray<UStaticMeshComponent*> Markers(Actor);
	for (UStaticMeshComponent* Marker : Markers)
	{
		Marker->SetHiddenInGame(true);
		Marker->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	}
	Actor->Tags.AddUnique(TEXT("DinkAuthoredArt"));
	Actor->Tags.AddUnique(TEXT("DinkHumanoid"));
	Actor->Tags.AddUnique(TEXT("DinkScriptHumanoid"));
	UE_LOG(LogDink, Display, TEXT("DINK SCRIPT CHARACTER ART OK: %s %s"), *Script.ToString(), *Mesh->GetPathName());
	return true;
}


const TMap<FName, FDinkBodyClip>& UDinkArtSubsystem::GetAnimationLibrary()
{
    if (bAnimationLibraryLoaded) return AnimationLibrary;
    bAnimationLibraryLoaded = true;
    FString Text;
    TSharedPtr<FJsonObject> Manifest;
    if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/animation_pass.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest) return AnimationLibrary;
    FString Schema;
    const TSharedPtr<FJsonObject>* Rows = nullptr;
    if (!Manifest->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-animation-pass/1") ||
        !Manifest->TryGetObjectField(TEXT("clips"), Rows) || !Rows) return AnimationLibrary;
    for (const auto& Pair : (*Rows)->Values)
    {
        const TSharedPtr<FJsonObject>* Row = nullptr;
        FString Path;
        if (!Pair.Value->TryGetObject(Row) || !Row || !(*Row)->TryGetStringField(TEXT("asset"), Path) || !FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(Path))) continue;
        FDinkBodyClip Clip;
        Clip.Sequence = LoadObject<UAnimSequence>(nullptr, *Path);
        if (!Clip.Sequence || Clip.Sequence->HasRootMotion()) continue;
        Clip.Duration = Clip.Sequence->GetPlayLength();
        double Number = 0;
        if ((*Row)->TryGetNumberField(TEXT("speed_cm_s"), Number)) Clip.SpeedCm = float(Number);
        if ((*Row)->TryGetNumberField(TEXT("stride_cm"), Number)) Clip.StrideCm = float(Number);
        if ((*Row)->TryGetNumberField(TEXT("hit_s"), Number)) Clip.HitS = float(Number);
        if ((*Row)->TryGetNumberField(TEXT("lock_s"), Number)) Clip.LockS = float(Number);
        (*Row)->TryGetBoolField(TEXT("loop"), Clip.bLoop);
        if (Clip.IsValid()) AnimationLibrary.Add(FName(*Pair.Key), Clip);
    }
    return AnimationLibrary;
}

void UDinkArtSubsystem::ConfigurePlayerActions(USkeletalMeshComponent& Component)
{
    if (!Component.GetOwner()) return;
    UDinkPlayerActionComponent* Action = Component.GetOwner()->FindComponentByClass<UDinkPlayerActionComponent>();
    if (!Action)
    {
        Action = NewObject<UDinkPlayerActionComponent>(Component.GetOwner(), TEXT("PlayerCosmeticAction"));
        Component.GetOwner()->AddInstanceComponent(Action);
        Action->RegisterComponent();
    }
    if (!Action->Configure(&Component)) Action->DestroyComponent();
}

bool UDinkArtSubsystem::PlayPlayerSequence(AActor* Actor, int32 Sequence, FName Weapon)
{
    if (!Actor || !CVarDinkArtEnabled.GetValueOnGameThread()) return false;
    UDinkPlayerActionComponent* Action = Actor->FindComponentByClass<UDinkPlayerActionComponent>();
    return Action && Action->PlaySequence(Sequence, Weapon);
}

void UDinkArtSubsystem::LoadExteriorCameraRules()
{
    ExteriorCameraRules.Reset();
    FString Text;TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("Dink/Data/Art/camera_exteriors.json")))||
       !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Config)||!Config)return;
    FString Schema;const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
    if(!Config->TryGetStringField(TEXT("schema"),Schema)||Schema!=TEXT("dink-camera-exteriors/1")||!Config->TryGetArrayField(TEXT("rules"),Rows))return;
    TArray<FDinkExteriorCameraRule> Parsed;TSet<FString> Keys;
    auto Numbers=[](const TSharedPtr<FJsonObject>& O,const TCHAR* Name,int32 Count,TArray<double>& Values)
    {
        const TArray<TSharedPtr<FJsonValue>>* A=nullptr;Values.Reset();
        if(!O->TryGetArrayField(Name,A)||A->Num()!=Count)return false;
        for(const auto& V:*A){double N=0;if(!V->TryGetNumber(N)||!FMath::IsFinite(N))return false;Values.Add(N);}return true;
    };
    for(const auto& Value:*Rows)
    {
        if(Value->Type!=EJson::Object)return;const auto Row=Value->AsObject();if(!Row)return;
        FDinkExteriorCameraRule R;double Screen=0;
        if(!Row->TryGetStringField(TEXT("owner_manifest"),R.Manifest)||R.Manifest.IsEmpty()||FPaths::GetCleanFilename(R.Manifest)!=R.Manifest||
           !Row->TryGetStringField(TEXT("owner_element"),R.Element)||R.Element.IsEmpty()||
           !Row->TryGetStringField(TEXT("expected_mesh"),R.Mesh)||!R.Mesh.StartsWith(TEXT("/Game/"))||
           !Row->TryGetNumberField(TEXT("owner_screen"),Screen)||Screen<1||Screen>768||Screen!=FMath::FloorToDouble(Screen))return;
        R.Screen=int32(Screen);const FString Key=R.Manifest+TEXT(":")+R.Element;
        if(Keys.Contains(Key))return;Keys.Add(Key);
        TArray<double> V;
        if(!Row->TryGetStringField(TEXT("native_mesh_package_sha256"),R.NativeMeshSHA)||R.NativeMeshSHA.Len()!=64)return;
        for(const TCHAR Ch:R.NativeMeshSHA)if(!FChar::IsHexDigit(Ch))return;
        if(!Numbers(Row,TEXT("native_bounds_min_cm"),3,V))return;R.NativeBoundsMin=FVector(V[0],V[1],V[2]);
        if(!Numbers(Row,TEXT("native_bounds_max_cm"),3,V))return;R.NativeBoundsMax=FVector(V[0],V[1],V[2]);
        if(!Numbers(Row,TEXT("portal_point_cm"),3,V))return;R.Definition.Point=FVector(V[0],V[1],V[2]);
        if(!Numbers(Row,TEXT("outward_normal"),3,V))return;R.Definition.Normal=FVector(V[0],V[1],V[2]);
        if(!Numbers(Row,TEXT("tangent"),3,V))return;R.Definition.Tangent=FVector(V[0],V[1],V[2]);
        if(!Numbers(Row,TEXT("aperture_min_cm"),2,V))return;R.Definition.Minimum=FVector2D(V[0],V[1]);
        if(!Numbers(Row,TEXT("aperture_max_cm"),2,V))return;R.Definition.Maximum=FVector2D(V[0],V[1]);
        if(!Numbers(Row,TEXT("interior_point_cm"),3,V))return;R.Definition.InteriorPoint=FVector(V[0],V[1],V[2]);
        const TArray<TSharedPtr<FJsonValue>>* Planes=nullptr;if(!Row->TryGetArrayField(TEXT("interior_planes"),Planes))return;
        for(const auto& Plane:*Planes)
        {
            const TArray<TSharedPtr<FJsonValue>>* A=nullptr;if(!Plane->TryGetArray(A)||A->Num()!=4)return;
            V.Reset();for(const auto& N:*A){double Number=0;if(!N->TryGetNumber(Number)||!FMath::IsFinite(Number))return;V.Add(Number);}
            R.Definition.InteriorPlanes.Add(FPlane(V[0],V[1],V[2],V[3]));
        }
        if(!R.Definition.IsValid())return;Parsed.Add(MoveTemp(R));
    }
    ExteriorCameraRules=MoveTemp(Parsed);
}

void UDinkArtSubsystem::RegisterExteriorCameraRule(const FString& Manifest,const TSharedPtr<FJsonObject>& Row,
                                                int32 Screen,UStaticMeshComponent* Component)
{
    FString Name;if(!Row->TryGetStringField(TEXT("name"),Name))return;
    for(FDinkExteriorCameraRule& R:ExteriorCameraRules)
    {
        if(R.Manifest!=FPaths::GetCleanFilename(Manifest)||R.Element!=Name||R.Screen!=Screen)continue;
        // Bind only this actual authored element. Duplicate matches invalidate the rule, never pick an arbitrary actor.
        if(R.Component.IsValid()){R.Definition.InteriorPlanes.Reset();R.Component.Reset();continue;}
        if(Component&&Component->GetStaticMesh()&&Component->GetStaticMesh()->GetPathName()==R.Mesh&&R.Definition.IsValid())
        {
            // Bounds are an explicit source-version sanity check only, never the framing authority.
            // Native package SHA is verified against the source/LFS inventory before build/cook.
            const FBox Box=Component->GetStaticMesh()->GetBounds().GetBox();
            if(Box.Min.Equals(R.NativeBoundsMin,1.)&&Box.Max.Equals(R.NativeBoundsMax,1.))R.Component=Component;
        }
    }
}

bool UDinkArtSubsystem::ExteriorCameraLimit(const ADinkScreenVolume& Screen,const FVector& Pivot,const FVector& Desired,
                                         double ProbeRadius,double FrustumClearance,DinkCameraPortal::FLimit& Out) const
{
    bool Found=false;Out=DinkCameraPortal::FLimit();
    if(Screen.bIndoor||Screen.GetWorld()!=GetWorld()||!Screen.ContainsWorldLocation(Pivot))return false;
    for(const FDinkExteriorCameraRule& R:ExteriorCameraRules)
    {
        const UStaticMeshComponent* C=R.Component.Get();
        if(R.Screen!=Screen.ScreenNumber||!C||!C->IsRegistered()||C->GetWorld()!=GetWorld()||!C->GetStaticMesh()||C->GetStaticMesh()->GetPathName()!=R.Mesh)continue;
        DinkCameraPortal::FLimit Candidate;
        const bool Limited=DinkCameraPortal::Limit(R.Definition,C->GetComponentTransform(),Pivot,Desired,ProbeRadius,Candidate,FrustumClearance);
        if((Limited||Candidate.bInfeasible)&&Candidate.Fraction<Out.Fraction)
        {Candidate.Owner=R.Manifest+TEXT(":")+R.Element;Candidate.MeshSourceSHA=R.NativeMeshSHA;Out=Candidate;Found=true;}
    }
    return Found;
}
