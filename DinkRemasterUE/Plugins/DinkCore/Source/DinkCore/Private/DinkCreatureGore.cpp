#include "DinkCreatureSubsystem.h"
#include "DinkCreatureClassComponent.h"
#include "DinkCoreModule.h"
#include "Components/DecalComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"

// Blood and thrown parts of the class-bound creatures. The 1997 game paints them into its sprites (the headless duck's
// fountain in sequences 111-119, the head that flies off in 121-129, the burst of sequence 164); the remaster's
// simulation draws none of it, so the presentation layer does. Nothing here touches a sprite or the simulation's
// random stream, and nothing collides.

static TAutoConsoleVariable<int32> CVarDinkCreatureGoreLog(TEXT("dink.CreatureGoreLog"), 0, TEXT("1 = log the blood drops, gobbets and feathers in the air a few times a second (review aid)."));
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

UInstancedStaticMeshComponent* UDinkCreatureSubsystem::GoreInstances(TObjectPtr<UInstancedStaticMeshComponent>& Slot, UStaticMesh* Mesh, bool bShadow)
{
	USceneComponent* Root = GoreRoot();
	if (!Root || !Mesh) return nullptr;
	if (!Slot)
	{
		Slot = NewObject<UInstancedStaticMeshComponent>(CorpseHolder);
		Slot->SetMobility(EComponentMobility::Movable);
		Slot->SetupAttachment(Root);
		Slot->SetStaticMesh(Mesh);
		Slot->SetCollisionProfileName(TEXT("NoCollision"));
		Slot->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Slot->SetGenerateOverlapEvents(false);
		Slot->SetCanEverAffectNavigation(false);
		Slot->SetCastShadow(bShadow);
		Slot->bReceivesDecals = false;
		Slot->ComponentTags.Add(GoreTag);
		Slot->RegisterComponent();
	}
	return Slot;
}

int32 UDinkCreatureSubsystem::GetLandedFeatherCount() const
{
	return LandedFeathers ? LandedFeathers->GetInstanceCount() : 0;
}

void UDinkCreatureSubsystem::EmitBlood(UStaticMesh* DropMesh, const FVector& From, const FVector& Direction, float SpeedCmS, float SpreadDeg, int32 Count,
	float SizeCm, float GroundZ, const FVector& Carry, int32 MaxInAir)
{
	USceneComponent* Root = GoreRoot();
	if (!Root || !DropMesh || Count <= 0) return;
	if (!GoreInstances(DropInstances, DropMesh, false)) return;
	const FVector Axis = Direction.GetSafeNormal(UE_SMALL_NUMBER, FVector::UpVector);
	const float Cone = FMath::DegreesToRadians(FMath::Clamp(SpreadDeg, 0.f, 89.f));
	for (int32 Index = 0; Index < Count && BloodDrops.Num() < FMath::Min(MaxInAir, MaxBloodDrops); ++Index)
	{
		FBloodDrop Drop;
		Drop.Location = From + FMath::VRand() * (0.6f * SizeCm);
		Drop.Velocity = FMath::VRandCone(Axis, Cone) * SpeedCmS * FMath::FRandRange(0.55f, 1.f) + Carry;
		Drop.SizeCm = SizeCm * (FMath::FRand() < 0.15f ? FMath::FRandRange(1.5f, 2.6f) : FMath::FRandRange(0.6f, 1.3f)); // mostly drops, some gobbets
		Drop.GroundZ = GroundZ;
		BloodDrops.Add(Drop);
	}
}

void UDinkCreatureSubsystem::AddBloodDecal(UMaterialInterface* Material, const FVector& Ground, float YawDeg, float SizeCm)
{
	USceneComponent* Root = GoreRoot();
	if (!Root || !Material || SizeCm <= 0.f) return;
	// At the cap the oldest stain is moved, not destroyed and made again: a running headless duck lays one every few
	// tens of centimetres, and creating and destroying decal components that often churns the renderer's decal pass
	// (bug list A13 is a crash there).
	BloodDecals.RemoveAll([](const TObjectPtr<UDecalComponent>& Decal) { return !IsValid(Decal); });
	UDecalComponent* Decal = nullptr;
	if (BloodDecals.Num() >= MaxBloodDecals)
	{
		Decal = BloodDecals[0];
		BloodDecals.RemoveAt(0);
		if (Decal->GetDecalMaterial() != Material) Decal->SetDecalMaterial(Material);
		Decal->DecalSize = FVector(45.0, SizeCm * 0.5, SizeCm * 0.5);
		Decal->MarkRenderStateDirty();
	}
	else
	{
		Decal = NewObject<UDecalComponent>(CorpseHolder);
		Decal->SetupAttachment(Root);
		Decal->SetDecalMaterial(Material);
		Decal->DecalSize = FVector(45.0, SizeCm * 0.5, SizeCm * 0.5); // X is the projection depth: down, through the grass blades
		Decal->SetFadeScreenSize(0.f);
		Decal->ComponentTags.Add(GoreTag);
		Decal->RegisterComponent();
		++BloodDecalsMade;
	}
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
	// The core: sequence 164 is a ball of fine blood drops that starts small and dense where the animal stood, grows to
	// radius_cm (83 px across beside a 31 px duck) within the sequence and thins as its drops fall. Each droplet is sent
	// to its own place in that ball and slowed by the air, so the ball is filled, not a shell.
	const float Radius = Row->RadiusCm * float(Scale);
	const FVector Middle = Ground + FVector(0.0, 0.0, Radius * 0.85); // nearly the whole ball above the ground: a droplet that reaches it is gone
	if (Row->Blobs > 0 && GoreInstances(BlobInstances, LoadedClasses[Index]->BloodBlob, false))
	{
		constexpr float CoreDrag = 2.4f;
		const float Reach = (1.f - FMath::Exp(-CoreDrag * FMath::Max(0.2f, Row->DurationS) * 0.7f)) / CoreDrag; // distance per unit of starting speed
		for (int32 Blob = 0; Blob < Row->Blobs && BloodDrops.Num() < MaxBloodDrops; ++Blob)
		{
			FBloodDrop Drop;
			const FVector Out = FMath::VRand();
			const float Target = Radius * FMath::Pow(FMath::FRand(), 0.42f); // a little denser toward the rim, as the picture
			Drop.Kind = 1;
			Drop.Location = Middle + Out * Target * 0.1f;
			Drop.Velocity = Out * (Target * 0.9f / Reach);
			Drop.Rotation = FRotator(FMath::FRandRange(0.f, 360.f), FMath::FRandRange(0.f, 360.f), FMath::FRandRange(0.f, 360.f));
			Drop.SizeCm = Row->BlobSizeCm * Scale * (FMath::FRand() < 0.12f ? FMath::FRandRange(1.6f, 2.6f) : FMath::FRandRange(0.5f, 1.3f));
			Drop.GroundZ = Ground.Z;
			Drop.Life = Row->DurationS * FMath::FRandRange(0.7f, 1.35f);
			Drop.Gravity = 0.3f;
			Drop.Drag = CoreDrag;
			BloodDrops.Add(Drop);
		}
	}
	if (Row->Feathers > 0 && GoreInstances(FeatherInstances, LoadedClasses[Index]->Feather, false))
	{
		GoreInstances(LandedFeathers, LoadedClasses[Index]->Feather, false);
		for (int32 Feather = 0; Feather < Row->Feathers && BloodDrops.Num() < MaxBloodDrops; ++Feather)
		{
			FBloodDrop Drop;
			Drop.Kind = 2;
			Drop.Location = Middle + FMath::VRand() * 0.3 * Radius;
			Drop.Velocity = FMath::VRandCone(FVector::UpVector, FMath::DegreesToRadians(75.f)) * FMath::FRandRange(120.f, 420.f) * FMath::Sqrt(float(Scale));
			Drop.Rotation = FRotator(FMath::FRandRange(0.f, 360.f), FMath::FRandRange(0.f, 360.f), FMath::FRandRange(0.f, 360.f));
			Drop.Spin = FRotator(FMath::FRandRange(-500.f, 500.f), FMath::FRandRange(-300.f, 300.f), FMath::FRandRange(-500.f, 500.f));
			Drop.SizeCm = 7.f * Scale * FMath::FRandRange(0.6f, 1.4f);
			Drop.GroundZ = Ground.Z;
			Drop.Gravity = 0.22f;
			Drop.Drag = 2.6f;
			BloodDrops.Add(Drop);
		}
	}
	if (UMaterialInterface* Decal = LoadedClasses[Index]->BurstDecals[BurstIndex]) AddBloodDecal(Decal, Ground, FMath::FRandRange(0.f, 360.f), Row->DecalSizeCm * Scale);
	++BurstCount;
	UE_LOG(LogDink, Display, TEXT("DINK CREATURE CLASS: %s burst at %s (sequence %d, brain %d, %d drops, %d gobbets, %d feathers; %d particles now in the air)"), *ClassId.ToString(),
		*Ground.ToString(), Sequence, Brain, Row->Drops, Row->Blobs, Row->Feathers, BloodDrops.Num());
	return true;
}

void UDinkCreatureSubsystem::SetGoreInstances(UInstancedStaticMeshComponent& Instances, const TArray<FTransform>& Transforms)
{
	// The instances are moved in place every frame; only the difference in count is added or removed (from the end, so
	// no index moves), and the whole set is cleared only when nothing of it is left in the air.
	const int32 Have = Instances.GetInstanceCount(), Want = Transforms.Num();
	if (Want == 0)
	{
		if (Have > 0) Instances.ClearInstances();
		return;
	}
	if (Have > Want)
	{
		TArray<int32> Tail;
		Tail.Reserve(Have - Want);
		for (int32 Index = Have - 1; Index >= Want; --Index) Tail.Add(Index);
		Instances.RemoveInstances(Tail, /*bInstanceArrayAlreadySortedInReverseOrder*/ true);
	}
	const int32 Kept = FMath::Min(Have, Want);
	if (Kept > 0) Instances.BatchUpdateInstancesTransforms(0, TArrayView<const FTransform>(Transforms.GetData(), Kept), /*bWorldSpace*/ true, /*bMarkRenderStateDirty*/ true, /*bTeleport*/ true);
	if (Want > Have) Instances.AddInstances(TArray<FTransform>(Transforms.GetData() + Have, Want - Have), /*bShouldReturnIndices*/ false, /*bWorldSpace*/ true, /*bUpdateNavigation*/ false);
}

void UDinkCreatureSubsystem::StepGore(float DeltaTime)
{
	const UWorld* GoreWorld = GetWorld();
	const float WorldDt = GoreWorld ? GoreWorld->GetDeltaSeconds() : 0.f;
	const float Dt = FMath::Clamp(WorldDt > 0.f ? WorldDt : DeltaTime, 0.f, 0.05f); // the world's own step, slowed with the game (a world that has not ticked: the caller's)
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
	TArray<FTransform> Kinds[3];
	TArray<FTransform> Landed;
	for (int32 Index = BloodDrops.Num() - 1; Index >= 0; --Index)
	{
		FBloodDrop& Drop = BloodDrops[Index];
		Drop.Age += Dt;
		Drop.Velocity.Z -= GravityCmS2 * Drop.Gravity * Dt;
		Drop.Velocity *= FMath::Max(0.f, 1.f - Drop.Drag * Dt); // air
		Drop.Location += Drop.Velocity * Dt;
		Drop.Rotation += Drop.Spin * Dt;
		const bool bDown = Drop.Location.Z <= Drop.GroundZ;
		if (bDown || (Drop.Life > 0.f && Drop.Age >= Drop.Life))
		{
			// A feather lies where it came down, flat, until the screen is left.
			if (Drop.Kind == 2 && bDown) Landed.Emplace(FRotator(0.0, Drop.Rotation.Yaw, FMath::FRandRange(-12.f, 12.f)), FVector(Drop.Location.X, Drop.Location.Y, Drop.GroundZ + 1.5), FVector(Drop.SizeCm));
			BloodDrops.RemoveAtSwap(Index);
			continue;
		}
		if (Drop.Kind == 0)
		{
			// The mesh is 1 cm long along +X: it points along its flight and draws out with its speed.
			const float Stretch = 1.f + FMath::Min(2.5f, float(Drop.Velocity.Size()) / 260.f);
			Kinds[0].Emplace(Drop.Velocity.ToOrientationQuat(), Drop.Location, FVector(Drop.SizeCm * Stretch, Drop.SizeCm, Drop.SizeCm));
		}
		else if (Drop.Kind == 1)
		{
			// A droplet of the core: full size at once, gone in the last fifth of its time if it has not landed.
			const float T = Drop.Life > 0.f ? Drop.Age / Drop.Life : 0.f;
			const float Size = Drop.SizeCm * (T > 0.8f ? FMath::Max(0.05f, (1.f - T) / 0.2f) : 1.f);
			Kinds[1].Emplace(Drop.Rotation, Drop.Location, FVector(Size, Size * 0.85f, Size * 0.8f));
		}
		else
		{
			Kinds[2].Emplace(Drop.Rotation, Drop.Location, FVector(Drop.SizeCm));
		}
	}
	int32 Kind = 0;
	for (UInstancedStaticMeshComponent* Instances : { DropInstances.Get(), BlobInstances.Get(), FeatherInstances.Get() })
	{
		if (Instances) SetGoreInstances(*Instances, Kinds[Kind]);
		++Kind;
	}
	if (LandedFeathers && Landed.Num() > 0 && LandedFeathers->GetInstanceCount() < 400) LandedFeathers->AddInstances(Landed, false, true);
	// Review aid (dink.CreatureGoreLog 1): what is in the air, a few times a second.
	static int32 Calls = 0;
	if (CVarDinkCreatureGoreLog.GetValueOnGameThread() != 0 && (Kinds[0].Num() + Kinds[1].Num() + Kinds[2].Num()) > 0 && (++Calls % 20) == 0)
	{
		UE_LOG(LogDink, Display, TEXT("DINK GORE: dt %.4f; %d drops, %d gobbets, %d feathers in the air; instances %d / %d / %d, landed feathers %d, stains %d%s"), Dt,
			Kinds[0].Num(), Kinds[1].Num(), Kinds[2].Num(), DropInstances ? DropInstances->GetInstanceCount() : -1, BlobInstances ? BlobInstances->GetInstanceCount() : -1,
			FeatherInstances ? FeatherInstances->GetInstanceCount() : -1, GetLandedFeatherCount(), BloodDecals.Num(),
			Kinds[1].Num() > 0 ? *FString::Printf(TEXT("; first gobbet at %s scale %s"), *Kinds[1][0].GetLocation().ToString(), *Kinds[1][0].GetScale3D().ToString()) : TEXT(""));
	}
}

void UDinkCreatureSubsystem::ClearGore()
{
	BloodDrops.Reset();
	FlyingParts.Reset();
	for (UStaticMeshComponent* Body : FlyingMeshes) if (Body) Body->DestroyComponent();
	FlyingMeshes.Reset();
	for (UInstancedStaticMeshComponent* Instances : { DropInstances.Get(), BlobInstances.Get(), FeatherInstances.Get(), LandedFeathers.Get() })
		if (Instances) Instances->ClearInstances();
	for (UDecalComponent* Decal : BloodDecals) if (Decal) Decal->DestroyComponent();
	BloodDecals.Reset();
}
