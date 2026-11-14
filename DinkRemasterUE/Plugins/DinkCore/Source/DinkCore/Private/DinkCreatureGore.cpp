#include "DinkCreatureSubsystem.h"
#include "DinkCreatureClassComponent.h"
#include "DinkCoreModule.h"
#include "Components/DecalComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"

// Blood and thrown parts of the class-bound creatures. The 1997 game paints them into its sprites (the headless duck's
// fountain in sequences 111-119, the head that flies off in 121-129, the burst of sequence 164); the remaster's
// simulation draws none of it, so the presentation layer does. Nothing here touches a sprite or the simulation's
// random stream, and nothing collides.

namespace
{
	const FName GoreTag(TEXT("DinkCreatureCorpse"));
	constexpr float GravityCmS2 = 980.f;
}

USceneComponent* UDinkCreatureSubsystem::GoreRoot()
{
	UWorld* World = GetWorld();
	if (!CorpseHolder && World)
	{
		CorpseHolder = World->SpawnActor<AActor>();
		if (!CorpseHolder) return nullptr;
		USceneComponent* Root = NewObject<USceneComponent>(CorpseHolder, TEXT("Root"));
		Root->SetMobility(EComponentMobility::Movable);
		CorpseHolder->SetRootComponent(Root);
		Root->RegisterComponent();
	}
	return CorpseHolder ? CorpseHolder->GetRootComponent() : nullptr;
}

UStaticMeshComponent* UDinkCreatureSubsystem::AddGoreMesh(UStaticMesh* Mesh, const FTransform& Transform)
{
	USceneComponent* Root = GoreRoot();
	if (!Root || !Mesh) return nullptr;
	UStaticMeshComponent* Body = NewObject<UStaticMeshComponent>(CorpseHolder);
	Body->SetMobility(EComponentMobility::Movable);
	Body->SetupAttachment(Root);
	Body->SetStaticMesh(Mesh);
	Body->SetCollisionProfileName(TEXT("NoCollision"));
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Body->SetGenerateOverlapEvents(false);
	Body->SetCanEverAffectNavigation(false);
	Body->ComponentTags.Add(GoreTag);
	Body->bReceivesDecals = false;
	Body->RegisterComponent();
	Body->SetWorldTransform(Transform);
	return Body;
}

void UDinkCreatureSubsystem::EmitBlood(UStaticMesh* DropMesh, const FVector& From, const FVector& Direction, float SpeedCmS, float SpreadDeg, int32 Count,
	float SizeCm, float GroundZ, const FVector& Carry)
{
	USceneComponent* Root = GoreRoot();
	if (!Root || !DropMesh || Count <= 0) return;
	if (!DropInstances)
	{
		DropInstances = NewObject<UInstancedStaticMeshComponent>(CorpseHolder);
		DropInstances->SetMobility(EComponentMobility::Movable);
		DropInstances->SetupAttachment(Root);
		DropInstances->SetStaticMesh(DropMesh);
		DropInstances->SetCollisionProfileName(TEXT("NoCollision"));
		DropInstances->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		DropInstances->SetGenerateOverlapEvents(false);
		DropInstances->SetCanEverAffectNavigation(false);
		DropInstances->SetCastShadow(false);
		DropInstances->bReceivesDecals = false;
		DropInstances->ComponentTags.Add(GoreTag);
		DropInstances->RegisterComponent();
	}
	const FVector Axis = Direction.GetSafeNormal(UE_SMALL_NUMBER, FVector::UpVector);
	const float Cone = FMath::DegreesToRadians(FMath::Clamp(SpreadDeg, 0.f, 89.f));
	for (int32 Index = 0; Index < Count && BloodDrops.Num() < MaxBloodDrops; ++Index)
	{
		FBloodDrop Drop;
		Drop.Location = From + FMath::VRand() * (0.6f * SizeCm);
		Drop.Velocity = FMath::VRandCone(Axis, Cone) * SpeedCmS * FMath::FRandRange(0.55f, 1.f) + Carry;
		Drop.SizeCm = SizeCm * FMath::FRandRange(0.5f, 1.35f);
		Drop.GroundZ = GroundZ;
		BloodDrops.Add(Drop);
	}
}

void UDinkCreatureSubsystem::AddBloodDecal(UMaterialInterface* Material, const FVector& Ground, float YawDeg, float SizeCm)
{
	USceneComponent* Root = GoreRoot();
	if (!Root || !Material || SizeCm <= 0.f) return;
	if (BloodDecals.Num() >= MaxBloodDecals)
	{
		if (BloodDecals[0]) BloodDecals[0]->DestroyComponent(); // the oldest stain goes
		BloodDecals.RemoveAt(0);
	}
	UDecalComponent* Decal = NewObject<UDecalComponent>(CorpseHolder);
	Decal->SetupAttachment(Root);
	Decal->SetDecalMaterial(Material);
	Decal->DecalSize = FVector(45.0, SizeCm * 0.5, SizeCm * 0.5); // X is the projection depth: down, through the grass blades
	Decal->SetFadeScreenSize(0.f);
	Decal->ComponentTags.Add(GoreTag);
	Decal->RegisterComponent();
	// The box is sunk so that it reaches the grass tips and the soles of whoever stands in it, not up their legs.
	Decal->SetWorldLocationAndRotation(Ground - FVector(0.0, 0.0, UDinkCreatureSubsystem::DecalSinkCm), FRotator(-90.0, YawDeg, 0.0));
	BloodDecals.Add(Decal);
}

void UDinkCreatureSubsystem::ThrowPart(UStaticMesh* Flying, UStaticMesh* Landed, UMaterialInterface* LandedDecal, float DecalSizeCm, const FVector& From,
	const FVector& Velocity, float GroundZ, double Scale)
{
	UStaticMeshComponent* Body = AddGoreMesh(Flying, FTransform(FRotator(FMath::FRandRange(-40.f, 40.f), FMath::FRandRange(0.f, 360.f), 0.f), From, FVector(Scale)));
	if (!Body) return;
	FFlyingPart Part;
	Part.Velocity = Velocity;
	Part.Spin = FRotator(FMath::FRandRange(380.f, 720.f) * (FMath::RandBool() ? 1.f : -1.f), FMath::FRandRange(-200.f, 200.f), FMath::FRandRange(-260.f, 260.f));
	Part.GroundZ = GroundZ;
	Part.DecalSizeCm = DecalSizeCm;
	Part.Scale = Scale;
	Part.Landed = Landed;
	Part.LandedDecal = LandedDecal;
	FlyingParts.Add(Part);
	FlyingMeshes.Add(Body);
	UE_LOG(LogDink, Display, TEXT("DINK CREATURE CLASS: part thrown from %s at %.0f cm/s"), *From.ToCompactString(), Velocity.Size());
}

bool UDinkCreatureSubsystem::Burst(FName ClassId, int32 Sequence, int32 Brain, const FVector& Ground, int32 SizePercent)
{
	const int32 Index = ClassBindings.IndexOfByPredicate([ClassId](const FDinkCreatureClassBinding& B) { return B.ClassId == ClassId; });
	if (Index == INDEX_NONE || !LoadedClasses.IsValidIndex(Index) || !LoadedClasses[Index].IsValid()) return false;
	const FDinkCreatureClassBinding& Binding = ClassBindings[Index];
	const FDinkCreatureBurst* Row = Binding.BurstFor(Sequence, Brain);
	if (!Row) return false;
	const double Scale = Binding.Scale * FMath::Max(1, SizePercent) / 100.0;
	const int32 BurstIndex = int32(Row - Binding.Bursts.GetData());
	EmitBlood(LoadedClasses[Index]->BloodDrop, Ground + FVector(0.0, 0.0, 14.0 * Scale), FVector::UpVector, Row->DropSpeedCmS * FMath::Sqrt(float(Scale)), 78.f, Row->Drops,
		Row->DropSizeCm * Scale, Ground.Z);
	if (UMaterialInterface* Decal = LoadedClasses[Index]->BurstDecals[BurstIndex]) AddBloodDecal(Decal, Ground, FMath::FRandRange(0.f, 360.f), Row->DecalSizeCm * Scale);
	UE_LOG(LogDink, Display, TEXT("DINK CREATURE CLASS: %s burst at %s (sequence %d, brain %d, %d drops)"), *ClassId.ToString(), *Ground.ToCompactString(), Sequence, Brain, Row->Drops);
	return true;
}

void UDinkCreatureSubsystem::StepGore(float DeltaTime)
{
	const float Dt = FMath::Clamp(DeltaTime, 0.f, 0.05f);
	if (Dt <= 0.f) return;
	for (int32 Index = FlyingParts.Num() - 1; Index >= 0; --Index)
	{
		FFlyingPart& Part = FlyingParts[Index];
		UStaticMeshComponent* Body = FlyingMeshes[Index];
		if (!Body)
		{
			FlyingParts.RemoveAt(Index);
			FlyingMeshes.RemoveAt(Index);
			continue;
		}
		Part.Velocity.Z -= GravityCmS2 * Dt;
		FVector Location = Body->GetComponentLocation() + Part.Velocity * Dt;
		if (Location.Z <= Part.GroundZ && Part.Velocity.Z < 0.f)
		{
			// It lands: the part lying in its pool, as the last frame of the original's sequence, until the screen is left.
			Location.Z = Part.GroundZ;
			const float Yaw = FMath::FRandRange(0.f, 360.f);
			if (UStaticMeshComponent* Landed = AddGoreMesh(Part.Landed, FTransform(FRotator(0.0, Yaw, 0.0), Location, FVector(Part.Scale)))) Corpses.Add(Landed);
			if (Part.LandedDecal) AddBloodDecal(Part.LandedDecal, Location, Yaw, Part.DecalSizeCm);
			UE_LOG(LogDink, Display, TEXT("DINK CREATURE CLASS: part landed at %s"), *Location.ToCompactString());
			Body->DestroyComponent();
			FlyingParts.RemoveAt(Index);
			FlyingMeshes.RemoveAt(Index);
			continue;
		}
		Body->SetWorldLocationAndRotation(Location, Body->GetComponentRotation() + Part.Spin * Dt);
	}
	if (!DropInstances) return;
	TArray<FTransform> Transforms;
	Transforms.Reserve(BloodDrops.Num());
	for (int32 Index = BloodDrops.Num() - 1; Index >= 0; --Index)
	{
		FBloodDrop& Drop = BloodDrops[Index];
		Drop.Velocity.Z -= GravityCmS2 * Dt;
		Drop.Velocity *= 1.f - 0.6f * Dt; // air
		Drop.Location += Drop.Velocity * Dt;
		if (Drop.Location.Z <= Drop.GroundZ)
		{
			BloodDrops.RemoveAtSwap(Index);
			continue;
		}
		// The mesh is 1 cm long along +X: it points along its flight and draws out with its speed.
		const float Stretch = 1.f + FMath::Min(2.5f, float(Drop.Velocity.Size()) / 260.f);
		Transforms.Emplace(Drop.Velocity.ToOrientationQuat(), Drop.Location, FVector(Drop.SizeCm * Stretch, Drop.SizeCm, Drop.SizeCm));
	}
	if (DropInstances->GetInstanceCount() > 0) DropInstances->ClearInstances();
	if (Transforms.Num() > 0) DropInstances->AddInstances(Transforms, /*bShouldReturnIndices*/ false, /*bWorldSpace*/ true);
}

void UDinkCreatureSubsystem::ClearGore()
{
	BloodDrops.Reset();
	FlyingParts.Reset();
	for (UStaticMeshComponent* Body : FlyingMeshes) if (Body) Body->DestroyComponent();
	FlyingMeshes.Reset();
	if (DropInstances) DropInstances->ClearInstances();
	for (UDecalComponent* Decal : BloodDecals) if (Decal) Decal->DestroyComponent();
	BloodDecals.Reset();
}
