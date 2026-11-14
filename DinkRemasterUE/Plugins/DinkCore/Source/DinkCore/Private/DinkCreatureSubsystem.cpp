#include "DinkCreatureSubsystem.h"
#include "DinkCreatureComponent.h"
#include "DinkCreatureClassComponent.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkCoreModule.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Animation/AnimSequence.h"
#include "Animation/BlendSpace.h"
#include "Materials/MaterialInterface.h"
#include "Components/BoxComponent.h"
#include "Components/DecalComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "Misc/PackageName.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
// Photoreal pass (round 6): visual only, same skeleton or refused; headless runs keep validating the manifest's mesh.
static TAutoConsoleVariable<int32> CVarDinkPhotorealPillbug(TEXT("dink.PhotorealPillbug"), 1,
	TEXT("1 = SK_Pillbug_Photoreal replaces the pillbug mesh of creatures.json while the process renders (same skeleton, clips, body boxes); read at begin play."));
static TAutoConsoleVariable<int32> CVarDinkCreatureClassArt(TEXT("dink.CreatureClassArt"), 1,
	TEXT("Class rows of creatures.json (every placement of a bound sprite class, and script-made sprites of its sequences, shown by the animated creature; presentation only). 0 = off, 1 = while the process renders, 2 = also headless (tests). Read at begin play."));
namespace
{
FVector CreatureVector(const TSharedPtr<FJsonObject>& Row, const TCHAR* Key, FVector Default = FVector::ZeroVector)
{
	const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
	return Row->TryGetArrayField(Key, Values) && Values->Num() == 3
			   ? FVector((*Values)[0]->AsNumber(), (*Values)[1]->AsNumber(), (*Values)[2]->AsNumber())
			   : Default;
}
float CreatureNumber(const TSharedPtr<FJsonObject>& Row, const TCHAR* Key, float Default)
{
	double Number;
	return Row->TryGetNumberField(Key, Number) ? float(Number) : Default;
}
} // namespace
bool UDinkCreatureSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{
	return Type == EWorldType::Game || Type == EWorldType::PIE;
}
void UDinkCreatureSubsystem::OnWorldBeginPlay(UWorld& World)
{
	Super::OnWorldBeginPlay(World);
	const IConsoleVariable* Enabled = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));
	if (Enabled && !Enabled->GetInt())
		return;
	FString Text;
	TSharedPtr<FJsonObject> Manifest;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/creatures.json"))) ||
		!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest)
		return;
	FString Schema;
	if (!Manifest->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-creatures/1"))
		return;
	AttachOriginRows(World, *Manifest);
	BindClasses(World, *Manifest);
}
void UDinkCreatureSubsystem::AttachOriginRows(UWorld& World, const FJsonObject& Manifest)
{
	const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
	if (!Manifest.TryGetArrayField(TEXT("placements"), Rows))
		return;
	TMap<FString, ADinkPlaceholderActor*> Actors;
	for (TActorIterator<ADinkPlaceholderActor> It(&World); It; ++It)
		Actors.Add(It->Origin->OriginId.ToString(), *It);
	int32 Count = 0;
	for (const TSharedPtr<FJsonValue>& Value : *Rows)
	{
		const TSharedPtr<FJsonObject> Row = Value->AsObject();
		if (!Row)
			continue;
		ADinkPlaceholderActor* Actor = Actors.FindRef(Row->GetStringField(TEXT("origin")));
		if (!Actor || Actor->FindComponentByClass<UDinkCreatureComponent>())
			continue;
		USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *Row->GetStringField(TEXT("mesh")));
		if (Mesh && Mesh->GetName() == TEXT("SK_Pillbug") && CVarDinkPhotorealPillbug.GetValueOnGameThread() != 0 && FApp::CanEverRender())
		{
			static const TCHAR* PhotorealPillbug = TEXT("/Game/Dink/Photoreal/Creatures/Pillbug/SK_Pillbug_Photoreal");
			USkeletalMesh* Photoreal = FPackageName::DoesPackageExist(PhotorealPillbug)
				? LoadObject<USkeletalMesh>(nullptr, *(FString(PhotorealPillbug) + TEXT(".SK_Pillbug_Photoreal")), nullptr, LOAD_NoWarn | LOAD_Quiet) : nullptr;
			if (Photoreal && Photoreal->GetSkeleton() == Mesh->GetSkeleton()) Mesh = Photoreal;
		}
		UBlendSpace* Locomotion = LoadObject<UBlendSpace>(nullptr, *Row->GetStringField(TEXT("locomotion")));
		FString FeedPath;
		Row->TryGetStringField(TEXT("feed_animation"), FeedPath);
		UAnimSequence* Feed = FeedPath.IsEmpty() ? nullptr : LoadObject<UAnimSequence>(nullptr, *FeedPath);
		const TArray<TSharedPtr<FJsonValue>>* Boxes = nullptr;
		if (!Mesh || !Locomotion || !Mesh->GetSkeleton() || Mesh->GetSkeleton() != Locomotion->GetSkeleton() ||
			(!FeedPath.IsEmpty() && (!Feed || Feed->GetSkeleton() != Mesh->GetSkeleton())) ||
			!Row->TryGetArrayField(TEXT("body_boxes"), Boxes) || Boxes->IsEmpty())
		{
			UE_LOG(LogDink, Warning, TEXT("Creature art incompatible/incomplete for %s; retaining sprite"),
				   *Actor->Origin->OriginId.ToString());
			continue;
		}
		bool bValid = true;
		for (const auto& BoxValue : *Boxes)
		{
			const auto Box = BoxValue->AsObject();
			const FVector Extent = Box ? CreatureVector(Box, TEXT("extent_cm")) : FVector::ZeroVector;
			bValid &= Extent.GetMin() > 2.f;
		}
		if (!bValid)
		{
			UE_LOG(LogDink, Warning, TEXT("Creature art invalid collision for %s; retaining sprite"),
				   *Actor->Origin->OriginId.ToString());
			continue;
		}
		Actor->GetRootComponent()->SetMobility(EComponentMobility::Movable);
		UDinkCreatureComponent* Creature = NewObject<UDinkCreatureComponent>(Actor, TEXT("AuthoredCreature"));
		Creature->SetupAttachment(Actor->GetRootComponent());
		Actor->AddInstanceComponent(Creature);
		const FVector Rotation = CreatureVector(Row, TEXT("rotation_deg"));
		Creature->SetRelativeTransform(FTransform(FRotator(Rotation.X, Rotation.Y, Rotation.Z),
												  CreatureVector(Row, TEXT("offset_cm")),
												  CreatureVector(Row, TEXT("scale"), FVector::OneVector)));
		Creature->RegisterComponent();
		FDinkCreaturePresentation Settings;
		FString Bone;
		if (Row->TryGetStringField(TEXT("food_bone"), Bone))
			Settings.FoodBone = FName(*Bone);
		Settings.FoodRadiusCm = CreatureNumber(Row, TEXT("food_radius_cm"), 70.f);
		Settings.FoodForwardDot = CreatureNumber(Row, TEXT("food_forward_dot"), .5f);
		Settings.StationarySpeedCmS = CreatureNumber(Row, TEXT("stationary_speed_cm_s"), 5.f);
		Settings.NominalWalkSpeedCmS = CreatureNumber(Row, TEXT("nominal_walk_speed_cm_s"), 80.f);
		Settings.NominalRunSpeedCmS = CreatureNumber(Row, TEXT("nominal_run_speed_cm_s"), 0.f);
		if (!Creature->Configure(Mesh, Locomotion, Feed, Settings))
		{
			Creature->DestroyComponent();
			continue;
		}
		for (const auto& BoxValue : *Boxes)
		{
			const auto Box = BoxValue->AsObject();
			UBoxComponent* Body = NewObject<UBoxComponent>(Actor);
			Body->SetupAttachment(Actor->GetRootComponent());
			Body->SetMobility(EComponentMobility::Movable);
			Body->SetBoxExtent(CreatureVector(Box, TEXT("extent_cm")));
			Body->SetRelativeLocation(CreatureVector(Box, TEXT("offset_cm")));
			const FVector R = CreatureVector(Box, TEXT("rotation_deg"));
			Body->SetRelativeRotation(FRotator(R.X, R.Y, R.Z));
			Body->SetCollisionProfileName(TEXT("Pawn"));
			Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
			Body->SetGenerateOverlapEvents(false);
			Body->CanCharacterStepUpOn = ECB_No; // Living creatures are not walkable floor.
			Body->SetHiddenInGame(true);
			Body->ComponentTags.Add(TEXT("DinkAuthoredInteraction"));
			Actor->AddInstanceComponent(Body);
			Body->RegisterComponent();
		}
		Actor->Card->SetHiddenInGame(true);
		Actor->Card->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Actor->Tags.AddUnique(TEXT("DinkAuthoredArt"));
		Actor->Tags.AddUnique(TEXT("DinkCreature"));
		++Count;
		const TArray<TSharedPtr<FJsonValue>>* Sequences = nullptr;
		if (Row->TryGetArrayField(TEXT("food_sequences"), Sequences))
			for (const auto& Sequence : *Sequences)
				FoodSequences.Add(int32(Sequence->AsNumber()));
		FString Path;
		if (Row->TryGetStringField(TEXT("food_mesh"), Path) && !Path.IsEmpty())
		{
			FoodMesh = LoadObject<UStaticMesh>(nullptr, *Path);
			FoodMeshOffset = CreatureVector(Row, TEXT("food_mesh_offset_cm"), FVector(0, 0, -60));
		}
	}
	UE_LOG(LogDink, Display, TEXT("DINK CREATURE ART OK: %d original actors animated"), Count);
}
void UDinkCreatureSubsystem::NotifyScriptSprite(AActor* Actor, int32 Sequence)
{
	if (!Actor)
		return;
	if (!FoodSequences.Contains(Sequence))
	{
		FoodActors.Remove(Actor);
		return;
	}
	FoodActors.RemoveAll([](const TWeakObjectPtr<AActor>& Food) { return !Food.IsValid() || Food->IsHidden(); });
	FoodActors.AddUnique(Actor);
	if (!FoodMesh || Actor->FindComponentByTag<UStaticMeshComponent>(TEXT("DinkAuthoredFood")))
		return;
	TInlineComponentArray<UStaticMeshComponent*> Markers(Actor);
	for (UStaticMeshComponent* Marker : Markers)
		Marker->SetHiddenInGame(true);
	UStaticMeshComponent* Visual = NewObject<UStaticMeshComponent>(Actor, TEXT("AuthoredFood"));
	Actor->AddInstanceComponent(Visual);
	Visual->SetStaticMesh(FoodMesh);
	Visual->SetMobility(EComponentMobility::Movable);
	Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Visual->ComponentTags.Add(TEXT("DinkAuthoredFood"));
	Visual->SetupAttachment(Actor->GetRootComponent());
	Visual->RegisterComponent();
	Visual->SetWorldTransform(
		FTransform(Actor->GetActorRotation(), Actor->GetActorLocation() + FoodMeshOffset, FVector::OneVector));
}

namespace
{
FAutoConsoleCommandWithWorld CreatureStatus(TEXT("dink.Creatures"), TEXT("Read authored creature motion, head pose and feeding state."), FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
{
 if (!World) return;
 for (TActorIterator<AActor> It(World);It;++It)
  if (const UDinkCreatureComponent* Creature=It->FindComponentByClass<UDinkCreatureComponent>())
  {
   const UDinkOriginComponent* Origin=UDinkOriginComponent::FindOnActor(*It);
   UE_LOG(LogDink,Log,TEXT("Creature %s speed=%.2f yaw=%.2f head=%s feeding=%d hidden=%d"),Origin ? *Origin->OriginId.ToString() : *It->GetName(),Creature->GetLocomotionSpeed(),It->GetActorRotation().Yaw,*Creature->GetSocketLocation(Creature->GetFoodBone()).ToCompactString(),Creature->IsFeeding(),It->IsHidden());
  }
}));
}

// ---------------------------------------------------------------------------------------------
// Class rows: presentation only (DinkCreatureClass.h)

namespace
{
	/** "/Game/Folder/Asset" or "/Game/Folder/Asset.Asset" -> the loaded object, nullptr without a warning when the package is absent. */
	template <typename T>
	T* LoadClassAsset(const FString& Path)
	{
		if (Path.IsEmpty()) return nullptr;
		FString Package = Path, Name;
		if (!Path.Split(TEXT("."), &Package, &Name)) Name = FPackageName::GetShortName(Path);
		if (!FPackageName::DoesPackageExist(Package)) return nullptr;
		return LoadObject<T>(nullptr, *(Package + TEXT(".") + Name), nullptr, LOAD_NoWarn | LOAD_Quiet);
	}

	TMap<FString, int32> LoadPlacementSizes()
	{
		// The sprite's size before its screen is entered (sp_size; the simulation holds it once the sprite exists).
		TMap<FString, int32> Sizes;
		TArray<FString> Lines;
		if (!FFileHelper::LoadFileToStringArray(Lines, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Gameplay/placements.csv"))) || Lines.Num() < 2) return Sizes;
		TArray<FString> Header;
		Lines[0].ParseIntoArray(Header, TEXT(","), false);
		const int32 OriginColumn = Header.IndexOfByKey(TEXT("origin")), SizeColumn = Header.IndexOfByKey(TEXT("size"));
		if (OriginColumn == INDEX_NONE || SizeColumn == INDEX_NONE) return Sizes;
		for (int32 Line = 1; Line < Lines.Num(); ++Line)
		{
			TArray<FString> Fields;
			Lines[Line].ParseIntoArray(Fields, TEXT(","), false);
			if (Fields.IsValidIndex(OriginColumn) && Fields.IsValidIndex(SizeColumn)) Sizes.Add(Fields[OriginColumn], FCString::Atoi(*Fields[SizeColumn]));
		}
		return Sizes;
	}
}

bool UDinkCreatureSubsystem::IsClassArtAllowed()
{
	const int32 Mode = CVarDinkCreatureClassArt.GetValueOnGameThread();
	// Headless runs (the automated tests, the probe) show nothing: they keep the cards, as they keep the stylised pillbug.
	return Mode >= 2 || (Mode == 1 && FApp::CanEverRender());
}

UDinkCreatureClassComponent* UDinkCreatureSubsystem::FindClassBody(const AActor* Actor)
{
	return Actor ? Actor->FindComponentByClass<UDinkCreatureClassComponent>() : nullptr;
}

TSharedPtr<const FDinkCreatureLoadedClass> UDinkCreatureSubsystem::LoadClass(const FDinkCreatureClassBinding& Binding)
{
	const FString ClassName = Binding.ClassId.ToString();
	auto Refuse = [&ClassName](const TCHAR* Why, const FString& What) -> TSharedPtr<const FDinkCreatureLoadedClass>
	{
		UE_LOG(LogDink, Warning, TEXT("Creature class %s not bound: %s %s; its sprites keep their cards"), *ClassName, Why, *What);
		return nullptr;
	};
	TSharedRef<FDinkCreatureLoadedClass> Loaded = MakeShared<FDinkCreatureLoadedClass>();
	Loaded->Binding = Binding;
	Loaded->Mesh = LoadClassAsset<USkeletalMesh>(Binding.Mesh);
	if (!Loaded->Mesh || !Loaded->Mesh->GetSkeleton()) return Refuse(TEXT("mesh missing or without skeleton"), Binding.Mesh);
	const USkeleton* Skeleton = Loaded->Mesh->GetSkeleton();
	TArray<UObject*> Assets;
	Assets.Add(Loaded->Mesh);
	FString Problem;
	auto LoadClip = [&](const FString& Path) -> const UAnimSequence*
	{
		UAnimSequence* Clip = LoadClassAsset<UAnimSequence>(Path);
		if (!Clip || Clip->GetSkeleton() != Skeleton || Clip->GetPlayLength() <= 0.f)
		{
			if (Problem.IsEmpty()) Problem = Path;
			return nullptr;
		}
		Assets.Add(Clip);
		return Clip;
	};
	auto LoadSet = [&](const FDinkCreatureLocomotion& Set, FDinkCreatureLoadedLocomotion& Out)
	{
		Out.Idle = LoadClip(Set.Idle);
		for (const FDinkCreatureGait& Gait : Set.Gaits)
		{
			const UAnimSequence* Clip = LoadClip(Gait.Clip);
			if (!Clip) continue;
			Out.Gaits.Add(Clip);
			Out.Speeds.Add(Gait.SpeedCmS);
			Out.Cycles.Add(Gait.Cycles);
			Out.Strides.Add(Gait.SpeedCmS * Clip->GetPlayLength() / Gait.Cycles); // ground one cycle covers at the speed it was made for
		}
	};
	FDinkCreatureLoadedLocomotion RowSet;
	if (Binding.Locomotion.IsSet()) LoadSet(Binding.Locomotion, RowSet);
	for (const FDinkCreatureRole& Role : Binding.Roles)
	{
		FDinkCreatureLoadedRole Out;
		if (!Role.Mesh.IsEmpty())
		{
			Out.Mesh = LoadClassAsset<USkeletalMesh>(Role.Mesh);
			if (!Out.Mesh || Out.Mesh->GetSkeleton() != Skeleton) return Refuse(TEXT("role mesh missing or on another skeleton"), Role.Mesh);
			Assets.Add(Out.Mesh);
		}
		if (Role.bLocomotion)
		{
			if (Role.Locomotion.IsSet()) LoadSet(Role.Locomotion, Out.Locomotion);
			else Out.Locomotion = RowSet;
			if (!Out.Locomotion.IsValid() && Problem.IsEmpty()) Problem = TEXT("(locomotion set)");
			if (Loaded->DefaultRole == INDEX_NONE) Loaded->DefaultRole = Loaded->Roles.Num();
		}
		else
		{
			Out.Clip = LoadClip(Role.Clip);
		}
		Loaded->Roles.Add(MoveTemp(Out));
	}
	if (!Problem.IsEmpty()) return Refuse(TEXT("clip missing, empty or on another skeleton"), Problem);
	if (Loaded->DefaultRole == INDEX_NONE) return Refuse(TEXT("no locomotion role"), FString());
	for (const FDinkCreatureCorpse& Corpse : Binding.Corpses)
	{
		UStaticMesh* Mesh = LoadClassAsset<UStaticMesh>(Corpse.Mesh);
		if (!Mesh) return Refuse(TEXT("corpse mesh missing"), Corpse.Mesh);
		Loaded->CorpseMeshes.Add(Mesh);
		Assets.Add(Mesh);
		UMaterialInterface* Decal = nullptr;
		if (!Corpse.DecalMaterial.IsEmpty())
		{
			Decal = LoadClassAsset<UMaterialInterface>(Corpse.DecalMaterial);
			if (!Decal) return Refuse(TEXT("corpse decal material missing"), Corpse.DecalMaterial);
			Assets.Add(Decal);
		}
		Loaded->CorpseDecals.Add(Decal);
	}
	for (const auto& Pair : Binding.Materials)
	{
		UMaterialInterface* Material = LoadClassAsset<UMaterialInterface>(Pair.Value);
		if (!Material) return Refuse(TEXT("material missing"), Pair.Value);
		Loaded->Materials.Add(Pair.Key, Material);
		Assets.Add(Material);
	}
	for (UObject* Asset : Assets) ClassAssets.AddUnique(Asset);
	return Loaded;
}

UDinkCreatureClassComponent* UDinkCreatureSubsystem::AttachClassBody(AActor& Actor, const TSharedRef<const FDinkCreatureLoadedClass>& Class,
	float GroundOffsetCm, float YawDeg, int32 SizePercent)
{
	if (!Actor.GetRootComponent()) return nullptr;
	UDinkCreatureClassComponent* Body = NewObject<UDinkCreatureClassComponent>(&Actor, TEXT("ClassCreature"));
	Body->SetupAttachment(Actor.GetRootComponent());
	Actor.AddInstanceComponent(Body);
	Body->RegisterComponent();
	if (!Body->Configure(Class, GroundOffsetCm, YawDeg, SizePercent))
	{
		Body->DestroyComponent();
		return nullptr;
	}
	return Body;
}

void UDinkCreatureSubsystem::BindClasses(UWorld& World, const FJsonObject& Manifest)
{
	ClassBindings.Reset();
	LoadedClasses.Reset();
	ClassAssets.Reset();
	ClassPlacements = 0;
	if (!IsClassArtAllowed()) return;
	TArray<FDinkCreatureClassBinding> Parsed;
	TArray<FString> Problems;
	DinkCreatureClass::ParseBindings(Manifest, Parsed, &Problems);
	for (const FString& Problem : Problems) UE_LOG(LogDink, Warning, TEXT("creatures.json %s"), *Problem);
	for (const FDinkCreatureClassBinding& Binding : Parsed)
	{
		if (TSharedPtr<const FDinkCreatureLoadedClass> Loaded = LoadClass(Binding))
		{
			ClassBindings.Add(Binding);
			LoadedClasses.Add(Loaded);
		}
	}
	if (ClassBindings.IsEmpty()) return;
	// Whatever another manifest names by origin stays its own: creature and character rows, replacements, hidden origins.
	const FDinkFamilyPrecedence Precedence = FDinkFamilyPrecedence::LoadDirectory(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art"), TEXT("families.json"));
	const TMap<FString, int32> Sizes = LoadPlacementSizes();
	TMap<FName, int32> PerClass;
	for (TActorIterator<ADinkPlaceholderActor> It(&World); It; ++It)
	{
		ADinkPlaceholderActor* Actor = *It;
		if (!Actor->Origin || !Actor->Card || !Actor->GetRootComponent() || FindClassBody(Actor)) continue;
		if (Actor->ActorHasTag(TEXT("DinkCreature")) || Actor->ActorHasTag(TEXT("DinkHumanoid")) || Actor->ActorHasTag(TEXT("DinkAuthoredArt")) ||
			Actor->ActorHasTag(UDinkArtFamilySubsystem::FamilyTag))
		{
			continue;
		}
		const FString Origin = Actor->Origin->OriginId.ToString();
		const bool bHasPicture = Actor->PlacementKind != TEXT("hardness_only") && Actor->Card->GetStaticMesh() != nullptr && !Actor->Card->bHiddenInGame;
		const FDinkCreatureClassBinding* Binding = nullptr;
		if (DinkCreatureClass::Decide(ClassBindings, Actor->Origin->ClassId, Origin, Precedence.Origins, bHasPicture, Binding) != EDinkCreatureClassDecision::Bound) continue;
		const int32 Index = int32(Binding - ClassBindings.GetData());
		const int32* Size = Sizes.Find(Origin);
		// The placement's picture is one facing of its walk (131 faces south-west): the body stands so until the sprite turns.
		const float Yaw = float(DinkCreatureClass::DirYawDegrees(DinkCreatureClass::DirOfSequence(Actor->Origin->Sequence)));
		if (!AttachClassBody(*Actor, LoadedClasses[Index].ToSharedRef(), 0.f, Yaw, Size && *Size > 0 ? *Size : 100)) continue;
		// Only the picture goes. The card's collision, the actor's tags and everything the scripts and brains read stay.
		Actor->Card->SetHiddenInGame(true);
		++ClassPlacements;
		PerClass.FindOrAdd(Binding->ClassId)++;
	}
	FString Summary;
	for (const auto& Pair : PerClass) Summary += FString::Printf(TEXT("%s%s %d"), Summary.IsEmpty() ? TEXT("") : TEXT(", "), *Pair.Key.ToString(), Pair.Value);
	UE_LOG(LogDink, Display, TEXT("DINK CREATURE CLASS ART OK: %d placements of %d classes shown by their creature (%s)"), ClassPlacements, ClassBindings.Num(), *Summary);
}

UDinkCreatureClassComponent* UDinkCreatureSubsystem::PresentScriptSprite(AActor* Actor, const DinkCreatureClass::FSpriteView& Sprite,
	float GroundOffsetCm, float YawDeg, int32 SizePercent)
{
	if (!Actor || ClassBindings.IsEmpty() || FindClassBody(Actor)) return nullptr;
	// A script character, an origin-bound creature or the pig's feed already dress this actor.
	if (Actor->ActorHasTag(TEXT("DinkCreature")) || Actor->ActorHasTag(TEXT("DinkHumanoid")) || Actor->ActorHasTag(TEXT("DinkAuthoredArt")) ||
		Actor->FindComponentByTag<UStaticMeshComponent>(TEXT("DinkAuthoredFood")))
	{
		return nullptr;
	}
	const FDinkCreatureClassBinding* Binding = DinkCreatureClass::FindBySprite(ClassBindings, Sprite);
	if (!Binding) return nullptr;
	const int32 Index = int32(Binding - ClassBindings.GetData());
	TInlineComponentArray<UStaticMeshComponent*> Markers(Actor);
	UDinkCreatureClassComponent* Body = AttachClassBody(*Actor, LoadedClasses[Index].ToSharedRef(), GroundOffsetCm, YawDeg, SizePercent);
	if (!Body) return nullptr;
	for (UStaticMeshComponent* Marker : Markers) Marker->SetHiddenInGame(true); // the greybox cylinder of a script-made sprite
	return Body;
}

bool UDinkCreatureSubsystem::LeaveCorpse(FName ClassId, int32 BaseDeath, int32 Dir, const FVector& Ground, float YawDeg, int32 SizePercent)
{
	UWorld* World = GetWorld();
	const int32 Index = ClassBindings.IndexOfByPredicate([ClassId](const FDinkCreatureClassBinding& B) { return B.ClassId == ClassId; });
	if (!World || Index == INDEX_NONE) return false;
	const FDinkCreatureClassBinding& Binding = ClassBindings[Index];
	const FDinkCreatureCorpse* Corpse = Binding.CorpseFor(BaseDeath, Dir);
	if (!Corpse) return false;
	const int32 CorpseIndex = int32(Corpse - Binding.Corpses.GetData());
	UStaticMesh* Mesh = LoadedClasses[Index]->CorpseMeshes[CorpseIndex];
	if (!CorpseHolder)
	{
		CorpseHolder = World->SpawnActor<AActor>();
		if (!CorpseHolder) return false;
		USceneComponent* Root = NewObject<USceneComponent>(CorpseHolder, TEXT("Root"));
		Root->SetMobility(EComponentMobility::Movable);
		CorpseHolder->SetRootComponent(Root);
		Root->RegisterComponent();
	}
	UStaticMeshComponent* Body = NewObject<UStaticMeshComponent>(CorpseHolder);
	Body->SetMobility(EComponentMobility::Movable);
	Body->SetupAttachment(CorpseHolder->GetRootComponent());
	Body->SetStaticMesh(Mesh);
	Body->SetCollisionProfileName(TEXT("NoCollision"));
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Body->SetGenerateOverlapEvents(false);
	Body->SetCanEverAffectNavigation(false);
	Body->ComponentTags.Add(TEXT("DinkCreatureCorpse"));
	Body->bReceivesDecals = false; // its blood is in its own textures; the pool decal below is for the ground and the grass
	const double Scale = Corpse->Scale * FMath::Max(1, SizePercent) / 100.0; // the corpse keeps the sprite's size (dink.cpp:12382, 12416)
	const FRotator Facing(0.0, YawDeg + Corpse->YawOffset, 0.0);
	Body->RegisterComponent();
	Body->SetWorldTransform(FTransform(Facing, Ground + Facing.RotateVector(Corpse->OffsetCm * Scale), FVector(Scale)));
	Corpses.Add(Body);
	if (UMaterialInterface* DecalMaterial = LoadedClasses[Index]->CorpseDecals[CorpseIndex])
	{
		UDecalComponent* Decal = NewObject<UDecalComponent>(CorpseHolder);
		Decal->SetupAttachment(CorpseHolder->GetRootComponent());
		Decal->SetDecalMaterial(DecalMaterial);
		// The decal box: X is the projection depth (down), Y and Z the footprint. Pitched down, its Z is the corpse's
		// forward and its Y the corpse's right, which is how the texture was drawn (right = forward, up = left).
		Decal->DecalSize = FVector(Corpse->DecalDepthCm, Corpse->DecalSizeCm.Y * 0.5 * Scale, Corpse->DecalSizeCm.X * 0.5 * Scale);
		Decal->SetFadeScreenSize(0.f);
		Decal->ComponentTags.Add(TEXT("DinkCreatureCorpse"));
		Decal->RegisterComponent();
		Decal->SetWorldLocationAndRotation(Ground, FRotator(-90.0, YawDeg + Corpse->YawOffset, 0.0));
		CorpseDecals.Add(Decal);
	}
	UE_LOG(LogDink, Display, TEXT("DINK CREATURE CLASS: %s corpse at %s (death sequence base %d, dir %d)"), *ClassId.ToString(), *Ground.ToCompactString(), BaseDeath, Dir);
	return true;
}

void UDinkCreatureSubsystem::ClearCorpses()
{
	for (UStaticMeshComponent* Corpse : Corpses) if (Corpse) Corpse->DestroyComponent();
	Corpses.Reset();
	for (UDecalComponent* Decal : CorpseDecals) if (Decal) Decal->DestroyComponent();
	CorpseDecals.Reset();
}

namespace
{
FAutoConsoleCommandWithWorld CreatureClassStatus(TEXT("dink.CreatureClasses"), TEXT("Log the class-bound creatures that follow a sprite: role, shown speed, cadence, yaw."), FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
{
	if (!World) return;
	int32 Bodies = 0;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		const UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(*It);
		if (!Body) continue;
		++Bodies;
		if (!Body->HasSpriteState() || It->IsHidden()) continue;
		const UDinkOriginComponent* Origin = UDinkOriginComponent::FindOnActor(*It);
		UE_LOG(LogDink, Log, TEXT("Class creature %s %s role=%s seq=%d pseq=%d dir=%d speed=%.1f cycles/s=%.2f yaw=%.1f size=%d at %s"), *Body->GetClassId().ToString(),
			Origin ? *Origin->OriginId.ToString() : *It->GetName(), *Body->GetRoleName().ToString(), Body->GetSpriteState().Seq, Body->GetSpriteState().PSeq,
			Body->GetSpriteState().Dir, Body->GetShownSpeed(), Body->GetCyclesPerSecond(), Body->GetShownYaw(), Body->GetSizePercent(), *Body->GetShownLocation().ToCompactString());
	}
	const UDinkCreatureSubsystem* Creatures = World->GetSubsystem<UDinkCreatureSubsystem>();
	UE_LOG(LogDink, Log, TEXT("Class creatures: %d bodies, %d corpses, %d classes bound"), Bodies, Creatures ? Creatures->GetCorpseCount() : 0, Creatures ? Creatures->GetClassBindings().Num() : 0);
}));
}
