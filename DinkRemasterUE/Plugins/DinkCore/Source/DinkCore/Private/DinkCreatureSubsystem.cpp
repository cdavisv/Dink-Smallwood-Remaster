#include "DinkCreatureSubsystem.h"
#include "DinkCreatureComponent.h"
#include "DinkCoreModule.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Animation/AnimSequence.h"
#include "Animation/BlendSpace.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
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
	const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
	if (!Manifest->TryGetStringField(TEXT("schema"), Schema) || Schema != TEXT("dink-creatures/1") ||
		!Manifest->TryGetArrayField(TEXT("placements"), Rows))
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
