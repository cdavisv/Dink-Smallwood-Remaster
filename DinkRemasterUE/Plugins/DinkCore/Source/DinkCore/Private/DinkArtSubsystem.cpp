#include "DinkArtSubsystem.h"
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
#include "Components/PostProcessComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/PointLight.h"
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

namespace
{
	TAutoConsoleVariable<int32> CVarDinkArtEnabled(TEXT("dink.ArtEnabled"), 1,
		TEXT("Apply authored Blender art at world startup (0: original greybox, 1: authored art)."));

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
}

bool UDinkArtSubsystem::DoesSupportWorldType(EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UDinkArtSubsystem::OnWorldBeginPlay(UWorld& World)
{
	Super::OnWorldBeginPlay(World);
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
	int32 Replaced = 0, Added = 0;
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
			// Per-triangle authored collision preserves openings and the visible prop footprint.
			Component->SetCollisionProfileName(TEXT("BlockAll"));
			bool bCollision = true;
			Row->TryGetBoolField(TEXT("collision"), bCollision);
			if (!bCollision) Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Component->SetGenerateOverlapEvents(false);
			if (Navigation.IsValid() && !bDisableNavigation) Component->SetCanEverAffectNavigation(true);
			Added++;
		}
	}
	if (Manifest->TryGetArrayField(TEXT("lights"), Rows))
	{
		for (const TSharedPtr<FJsonValue>& Value : *Rows)
		{
			const TSharedPtr<FJsonObject> Row = Value->AsObject();
			APointLight* Light = World.SpawnActor<APointLight>(VectorField(Row, TEXT("world_cm")), FRotator::ZeroRotator);
			if (!Light) continue;
			Light->Tags.Add(TEXT("DinkAuthoredArt"));
			UPointLightComponent* C = CastChecked<UPointLightComponent>(Light->GetLightComponent());
			C->SetMobility(EComponentMobility::Movable);
			C->SetIntensityUnits(ELightUnits::Lumens);
			C->SetIntensity(Row->GetNumberField(TEXT("lumens")));
			C->SetUseTemperature(true);
			C->SetTemperature(Row->GetNumberField(TEXT("kelvin")));
			C->SetAttenuationRadius(Row->GetNumberField(TEXT("radius_cm")));
			C->SetSourceRadius(18.f);
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
		USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *Row->GetStringField(TEXT("mesh")));
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
		Human->Configure(Mesh, Locomotion);
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
	Component.SetSkeletalMesh(Mesh);
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
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *(*Row)->GetStringField(TEXT("mesh")));
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
	Human->Configure(Mesh, Locomotion);
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


void UDinkArtSubsystem::ConfigurePlayerActions(USkeletalMeshComponent& Component)
{
    FString Text;
    TSharedPtr<FJsonObject> Manifest;
    if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/hero_actions.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest) return;
    FString Schema;
    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    if (!Manifest->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-hero-actions/1") ||
        !Manifest->TryGetArrayField(TEXT("actions"), Rows)) return;
    TMap<int32, UAnimSequence*> Approved;
    for (const auto& Value : *Rows)
    {
        const auto Row = Value->AsObject();
        FString Path; bool Loop = true; double Duration = 0, Impact = 0;
        const TArray<TSharedPtr<FJsonValue>>* Sequences = nullptr;
        if (!Row || !Row->TryGetStringField(TEXT("animation"), Path) || !Row->TryGetBoolField(TEXT("loop"), Loop) || Loop ||
            !Row->TryGetNumberField(TEXT("duration_s"), Duration) || !Row->TryGetNumberField(TEXT("impact_s"), Impact) ||
            !FMath::IsFinite(Duration) || !FMath::IsFinite(Impact) || !FMath::IsNearlyEqual(Duration, .4, .0001) ||
            !FMath::IsNearlyEqual(Impact, .175, .0001) ||
            Path != TEXT("/Game/Dink/Hero/Animations/AN_Dink_Fist.AN_Dink_Fist") ||
            !Row->TryGetArrayField(TEXT("sequences"), Sequences)) return;
        UAnimSequence* Clip = LoadObject<UAnimSequence>(nullptr, *Path);
        if (!Clip || !FMath::IsNearlyEqual(Clip->GetPlayLength(), Duration, .001)) return;
        for (const auto& Sequence : *Sequences)
        {
            double IdValue = 0;
            if (!Sequence->TryGetNumber(IdValue) || !FMath::IsFinite(IdValue) ||
                (IdValue != 102 && IdValue != 104 && IdValue != 106 && IdValue != 108)) return;
            const int32 Id = int32(IdValue);
            if (Approved.Contains(Id)) return;
            Approved.Add(Id, Clip);
        }
    }
    if (Approved.Num() != 4 || !Component.GetOwner()) return;
    UDinkPlayerActionComponent* Action = Component.GetOwner()->FindComponentByClass<UDinkPlayerActionComponent>();
    if (!Action)
    {
        Action = NewObject<UDinkPlayerActionComponent>(Component.GetOwner(), TEXT("PlayerCosmeticAction"));
        Component.GetOwner()->AddInstanceComponent(Action);
        Action->RegisterComponent();
    }
    if (!Action->Configure(&Component, Approved)) Action->DestroyComponent();
}

bool UDinkArtSubsystem::PlayPlayerSequence(AActor* Actor, int32 Sequence)
{
    if (!Actor || !CVarDinkArtEnabled.GetValueOnGameThread()) return false;
    UDinkPlayerActionComponent* Action = Actor->FindComponentByClass<UDinkPlayerActionComponent>();
    return Action && Action->PlaySequence(Sequence);
}
