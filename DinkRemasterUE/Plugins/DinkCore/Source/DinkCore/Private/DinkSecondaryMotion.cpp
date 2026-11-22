#include "DinkSecondaryMotion.h"

#include "Animation/AnimTypes.h"
#include "BonePose.h"
#include "Components/SkeletalMeshComponent.h"
#include "DinkBodyAnimInstance.h"
#include "DinkCreatureClassComponent.h"
#include "DinkStatsComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ScopeRWLock.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Misc/PackageName.h"
#include "Scalability.h"
#include "UObject/UObjectIterator.h"

DEFINE_LOG_CATEGORY_STATIC(LogDinkSecondary, Log, All);

static TAutoConsoleVariable<int32> CVarHairPhysics(TEXT("dink.Hair.Physics"), 1,
	TEXT("1 = character hair lags, swings and settles with head motion and wind (material offset from a spring); 0 = rigid hair."));
static TAutoConsoleVariable<int32> CVarGarmentPhysics(TEXT("dink.Garment.Physics"), 1,
	TEXT("1 = the Mother's skirt hangs from her hips as a bell, pushed out by her legs and swinging with her (no hem stretch); 0 = the skinned skirt."));
static TAutoConsoleVariable<int32> CVarHitPhysics(TEXT("dink.HitReaction.Physics"), 1,
	TEXT("1 = a hit jolts the upper body and head with a short spring (pose only, never the capsule); 0 = off."));
static TAutoConsoleVariable<int32> CVarLooseParts(TEXT("dink.LooseParts.Physics"), 1,
	TEXT("1 = creatures' loose parts with bones of their own (pillbug antennae and tail, pig ears and tail) lag and swing; 0 = as animated."));
static TAutoConsoleVariable<float> CVarHairWind(TEXT("dink.Hair.Wind"), 1.f,
	TEXT("Scales how far the wind leans the hair outdoors (world-alive's MPC_Dink_World wind, else the foliage's own breeze); 0 = no wind."));
static TAutoConsoleVariable<float> CVarSecondaryScale(TEXT("dink.Secondary.Scale"), 1.f,
	TEXT("Multiplies every secondary-motion amplitude (review aid; 1 = tuned)."));
static TAutoConsoleVariable<int32> CVarSecondaryQuality(TEXT("dink.Secondary.Quality"), -1,
	TEXT("-1 = follow effects scalability (Low off, Medium 30 Hz, High and up every frame); 0 off, 1 30 Hz, 2 every frame."));

namespace
{
	// Tuned at the play camera and close up (Docs/Verification/SecondaryMotion_15Nov2026). Short crops barely move:
	// a real crop's tips flex a few millimetres; the hero's longer fringe and nape locks about a centimetre at a sprint
	// start. The Mother's hair is drawn back into a bun: only her loose wisps and outline cards move.
	FDinkSecondaryProfile MakeProfile(FName Mesh, float HairHz, float HairMax, float YawMax, float Wind, bool bSkirt)
	{
		FDinkSecondaryProfile P;
		P.Mesh = Mesh;
		P.bHair = HairMax > 0.f;
		P.Hair = { HairHz, .22f, HairMax, 1.f };
		P.HairYaw = { HairHz * .8f, .25f, YawMax, 1.f };
		P.HairWindCm = Wind;
		P.bSkirt = bSkirt;
		P.Skirt = { 1.6f, .3f, 7.f, .85f };
		P.Jolt = { 3.2f, .38f, 14.f, 0.f };
		return P;
	}
	FDinkSecondaryProfile MakeCreature(FName Mesh, TArray<TArray<FName>> Chains, FDinkSpringParams Chain)
	{
		FDinkSecondaryProfile P = MakeProfile(Mesh, 3.f, 0.f, 0.f, 0.f, false);
		P.Chains = MoveTemp(Chains);
		P.Chain = Chain;
		return P;
	}
	const TArray<FDinkSecondaryProfile>& Profiles()
	{
		static const TArray<FDinkSecondaryProfile> Table = {
			MakeProfile(TEXT("SK_Dink_Photoreal"), 3.2f, 1.4f, .09f, .22f, false),
			MakeProfile(TEXT("SK_Mother_Photoreal"), 2.6f, .8f, .06f, .16f, true),
			MakeProfile(TEXT("SK_Milder_Photoreal"), 4.5f, .55f, .05f, .08f, false),
			// the older meshes have no secondary-motion materials: they keep only the hit jolt
			MakeProfile(TEXT("SK_Dink_Hands"), 3.2f, 0.f, 0.f, 0.f, false),
			MakeProfile(TEXT("SK_Dink"), 3.2f, 0.f, 0.f, 0.f, false),
			MakeProfile(TEXT("SK_Mother"), 2.6f, 0.f, 0.f, 0.f, false),
			MakeProfile(TEXT("SK_Milder"), 4.5f, 0.f, 0.f, 0.f, false),
			// creatures: loose parts with their own bones. Only bodies on a native Dink animation instance get them (the
			// placement pigs play a single-node blend space, which offers no place to add them).
			MakeCreature(TEXT("SK_Pillbug_Photoreal"), { { TEXT("antenna_01_l"), TEXT("antenna_02_l") }, { TEXT("antenna_01_r"), TEXT("antenna_02_r") }, { TEXT("tail") } }, { 4.f, .15f, 2.5f, 1.f }),
			MakeCreature(TEXT("SK_Pillbug"), { { TEXT("antenna_01_l"), TEXT("antenna_02_l") }, { TEXT("antenna_01_r"), TEXT("antenna_02_r") }, { TEXT("tail") } }, { 4.f, .15f, 2.5f, 1.f }),
			MakeCreature(TEXT("SK_Pig"), { { TEXT("ear_l") }, { TEXT("ear_r") }, { TEXT("tail_01"), TEXT("tail_02"), TEXT("tail_03") } }, { 3.f, .2f, 3.f, 1.f }),
		};
		return Table;
	}

	bool Finite(const FVector& V) { return FMath::IsFinite(V.X) && FMath::IsFinite(V.Y) && FMath::IsFinite(V.Z); }

	/** Bone transform in component space of the reference (bind) pose. */
	FTransform RefComponentSpace(const FReferenceSkeleton& Ref, int32 Bone)
	{
		FTransform T = FTransform::Identity;
		for (int32 B = Bone; B != INDEX_NONE; B = Ref.GetParentIndex(B)) T = T * Ref.GetRefBonePose()[B];
		return T;
	}

	/** Head centre in the head bone's frame: about 9 cm above and 2 cm in front of the joint (the mannequin's head bone
	 * sits at the top of the neck). Worked out from the bind pose so that no bone-axis convention is assumed. */
	FVector HeadCentreLocal(const FReferenceSkeleton& Ref, int32 Head)
	{
		const FTransform Bind = RefComponentSpace(Ref, Head);
		return Bind.InverseTransformPosition(Bind.GetLocation() + FVector(0.f, 2.f, 9.f));
	}

	struct FPublished
	{
		FVector3f Jolt = FVector3f::ZeroVector;
		const FDinkSecondaryProfile* Profile = nullptr;
		TArray<FVector3f, TInlineAllocator<4>> Lags;
	};
	FRWLock JoltLock;
	TMap<TObjectKey<USkeletalMeshComponent>, FPublished> JoltByMesh;
}

const FDinkSecondaryProfile* FDinkSecondaryProfile::Find(FName MeshName)
{
	for (const FDinkSecondaryProfile& P : Profiles()) if (P.Mesh == MeshName) return &P;
	return nullptr;
}

void FDinkSpring3::Step(float Dt, const FVector& AnchorAccel, const FVector& Force, const FDinkSpringParams& P)
{
	if (!FMath::IsFinite(Dt) || Dt <= 0.f || !Finite(AnchorAccel) || !Finite(Force) || !Finite(X) || !Finite(V)) { Reset(); return; }
	Dt = FMath::Min(Dt, .1f);
	const float W = 2.f * PI * FMath::Max(P.FrequencyHz, .05f);
	const float C = 2.f * FMath::Clamp(P.Damping, 0.f, 4.f) * W;
	const FVector External = Force - AnchorAccel * P.InertiaGain;
	const int32 Steps = FMath::Clamp(FMath::CeilToInt(Dt * 120.f), 1, 16);
	const float H = Dt / Steps;
	const float Max = FMath::Max(P.Max, 0.f);
	for (int32 i = 0; i < Steps; ++i)
	{
		// semi-implicit Euler: stable for W*H < 2 (W = 2 pi 5 Hz, H = 1/120 s gives .26)
		V += (External - X * (W * W) - V * C) * H;
		X += V * H;
		const float Len = X.Size();
		if (Len > Max)
		{
			// the end reaches its stop (the scalp, the hem's reach): keep it there and drop the outward speed
			const FVector N = X / Len;
			X = N * Max;
			const float Out = FVector::DotProduct(V, N);
			if (Out > 0.f) V -= N * Out;
		}
	}
	if (!Finite(X) || !Finite(V)) Reset();
}

void FDinkSpring3::Kick(const FVector& DeltaV, const FDinkSpringParams& P)
{
	if (!Finite(DeltaV)) return;
	const float Cap = FMath::Max(P.Max, 0.f) * 2.f * PI * FMath::Max(P.FrequencyHz, .05f) * 1.5f;
	V = (V + DeltaV).GetClampedToMaxSize(Cap);
}

void FDinkSecondaryBody::ResetMotion()
{
	Hair.Reset(); HairYaw.Reset(); Skirt.Reset(); Jolt.Reset();
	for (FDinkSpring3& S : ChainSprings) S.Reset();
	for (FVector& V : ChainPrevVel) V = FVector::ZeroVector;
	for (FVector& V : ChainAccel) V = FVector::ZeroVector;
	HeadAccel = PelvisAccel = PrevHeadVel = PrevPelvisVel = FVector::ZeroVector;
	YawAccel = PrevYawRate = 0.f;
	HistoryFrames = 0;
}

float FDinkSecondaryMotion::FoliageGust(const FVector2D& P, float T, const FVector2D& WindDir, float Travel, float Gustiness)
{
	// the foliage material's field (world_life_wind.py WIND_HLSL): value noise of about 14 m and 5 m cells travelling
	// down the wind
	auto Hash = [](const FVector2D& C) { const double S = FMath::Sin(C.X * 127.1 + C.Y * 311.7) * 43758.5453; return S - FMath::Floor(S); };
	auto Noise = [&Hash](const FVector2D& Q)
	{
		const FVector2D I(FMath::Floor(Q.X), FMath::Floor(Q.Y));
		FVector2D F = Q - I; F = F * F * (FVector2D(3.0) - 2.0 * F);
		const double A = FMath::Lerp(Hash(I), Hash(I + FVector2D(1, 0)), F.X), B = FMath::Lerp(Hash(I + FVector2D(0, 1)), Hash(I + FVector2D(1, 1)), F.X);
		return FMath::Lerp(A, B, F.Y);
	};
	const FVector2D Wd = WindDir.GetSafeNormal().IsNearlyZero() ? FVector2D(.92, .39) : WindDir.GetSafeNormal();
	const double G1 = Noise(P / 1400.0 - Wd * T * .11 * Travel);
	const double G2 = Noise(P / 520.0 - Wd * T * .23 * Travel);
	const float Field = float(.45 + 1.5 * FMath::SmoothStep(.35, .85, .65 * G1 + .35 * G2));
	return FMath::Lerp(1.f, Field, FMath::Clamp(Gustiness, 0.f, 1.f));
}

FVector3f FDinkSecondaryMotion::GetPublishedJolt(const USkeletalMeshComponent* Mesh)
{
	FReadScopeLock Lock(JoltLock);
	const FPublished* Found = JoltByMesh.Find(Mesh);
	return Found ? Found->Jolt : FVector3f::ZeroVector;
}

void FDinkSecondaryMotion::PublishJolt(const USkeletalMeshComponent* Mesh, const FVector3f& Degrees)
{
	Publish(Mesh, Degrees, nullptr, {});
}

void FDinkSecondaryMotion::Publish(const USkeletalMeshComponent* Mesh, const FVector3f& Degrees, const FDinkSecondaryProfile* Profile, TConstArrayView<FVector3f> ChainLags)
{
	bool bAny = !Degrees.IsNearlyZero(.01f);
	for (const FVector3f& L : ChainLags) bAny |= !L.IsNearlyZero(.01f);
	FWriteScopeLock Lock(JoltLock);
	if (!bAny) { JoltByMesh.Remove(Mesh); return; }
	FPublished& P = JoltByMesh.FindOrAdd(Mesh);
	P.Jolt = Degrees;
	P.Profile = Profile && Profile->Chains.Num() == ChainLags.Num() ? Profile : nullptr;
	P.Lags = ChainLags;
}

void FDinkSecondaryMotion::ForgetMesh(const USkeletalMeshComponent* Mesh)
{
	FWriteScopeLock Lock(JoltLock);
	JoltByMesh.Remove(Mesh);
}

void FDinkSecondaryMotion::ForgetKey(TObjectKey<USkeletalMeshComponent> Key)
{
	FWriteScopeLock Lock(JoltLock);
	JoltByMesh.Remove(Key);
}

void FDinkSecondaryMotion::ApplyToPose(const USkeletalMeshComponent* Mesh, FCompactPose& Pose)
{
	if (!Mesh) return;
	FPublished Snapshot;
	{
		FReadScopeLock Lock(JoltLock);
		const FPublished* Found = JoltByMesh.Find(Mesh);
		if (!Found) return;
		Snapshot = *Found;
	}
	const FVector3f Deg = Snapshot.Jolt;
	const FBoneContainer& Bones = Pose.GetBoneContainer();
	const FReferenceSkeleton& Ref = Bones.GetReferenceSkeleton();
	auto Compact = [&](const TCHAR* Name)
	{
		const int32 MeshIndex = Ref.FindBoneIndex(FName(Name));
		if (MeshIndex == INDEX_NONE) return FCompactPoseBoneIndex(INDEX_NONE);
		return Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(MeshIndex));
	};
	// mesh space: the mesh faces +Y, +X is the character's left, +Z up (same convention as the body animation)
	auto Rotate = [&Pose](FCompactPoseBoneIndex Index, const FQuat& Delta)
	{
		if (Index.GetInt() == INDEX_NONE || Index.GetInt() >= Pose.GetNumBones()) return;
		FQuat ParentSpace = FQuat::Identity;
		for (FCompactPoseBoneIndex P = Pose.GetParentBoneIndex(Index); P.GetInt() != INDEX_NONE; P = Pose.GetParentBoneIndex(P))
			ParentSpace = Pose[P].GetRotation() * ParentSpace;
		FTransform& Bone = Pose[Index];
		Bone.SetRotation((ParentSpace.Inverse() * Delta * ParentSpace * Bone.GetRotation()).GetNormalized());
	};
	auto Tilt = [](float ForwardDeg, float SideDeg, float TwistDeg)
	{
		const FVector Up = FVector::UpVector;
		const FVector To = (Up + FVector::YAxisVector * FMath::Tan(FMath::DegreesToRadians(ForwardDeg)) + FVector::XAxisVector * FMath::Tan(FMath::DegreesToRadians(SideDeg))).GetSafeNormal();
		return FQuat(Up, FMath::DegreesToRadians(TwistDeg)) * FQuat::FindBetweenNormals(Up, To);
	};
	// a blow bends the chest most, the neck and head follow; parents first so each share adds to the one below
	struct FShare { const TCHAR* Bone; float Share; };
	static const FShare Shares[] = { { TEXT("spine_03"), .4f }, { TEXT("neck_01"), .3f }, { TEXT("head"), .3f } };
	if (!Deg.IsNearlyZero(.01f))
		for (const FShare& S : Shares)
			Rotate(Compact(S.Bone), Tilt(Deg.X * S.Share, Deg.Y * S.Share, Deg.Z * S.Share));
	// loose parts: each bone of a chain turns so that the chain's tip trails by its share of the lag
	if (!Snapshot.Profile) return;
	auto MeshSpace = [&Pose](FCompactPoseBoneIndex Index)
	{
		FTransform T = Pose[Index];
		for (FCompactPoseBoneIndex P = Pose.GetParentBoneIndex(Index); P.GetInt() != INDEX_NONE; P = Pose.GetParentBoneIndex(P)) T = T * Pose[P];
		return T;
	};
	for (int32 C = 0; C < Snapshot.Profile->Chains.Num() && C < Snapshot.Lags.Num(); ++C)
	{
		const FVector Lag(Snapshot.Lags[C]);
		if (Lag.IsNearlyZero(.01)) continue;
		const TArray<FName>& Chain = Snapshot.Profile->Chains[C];
		const int32 N = Chain.Num();
		for (int32 i = 0; i < N; ++i)
		{
			const int32 MeshIndex = Ref.FindBoneIndex(Chain[i]);
			if (MeshIndex == INDEX_NONE) break;
			const FCompactPoseBoneIndex Index = Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(MeshIndex));
			if (Index.GetInt() == INDEX_NONE || Index.GetInt() >= Pose.GetNumBones()) break;
			// the bone's direction: towards the next bone of the chain, or for the last one along its parent's
			const FTransform Here = MeshSpace(Index);
			FVector Dir, Base = Here.GetLocation();
			const int32 NextMesh = i + 1 < N ? Ref.FindBoneIndex(Chain[i + 1]) : INDEX_NONE;
			const FCompactPoseBoneIndex Next = NextMesh != INDEX_NONE ? Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(NextMesh)) : FCompactPoseBoneIndex(INDEX_NONE);
			if (Next.GetInt() != INDEX_NONE && Next.GetInt() < Pose.GetNumBones()) Dir = MeshSpace(Next).GetLocation() - Base;
			else if (Pose.GetParentBoneIndex(Index).GetInt() != INDEX_NONE) Dir = Base - MeshSpace(Pose.GetParentBoneIndex(Index)).GetLocation();
			else continue;
			const double Len = Dir.Size();
			if (Len < .5) continue;
			// each bone takes an equal share of the tip's lag, measured over the remaining length
			Rotate(Index, FQuat::FindBetweenVectors(Dir, Dir + Lag / double(N)));
		}
	}
}

bool UDinkSecondaryMotionSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	const UWorld* World = Cast<UWorld>(Outer);
	return World && (World->WorldType == EWorldType::Game || World->WorldType == EWorldType::PIE);
}

void UDinkSecondaryMotionSubsystem::Deinitialize()
{
	for (const FDinkSecondaryBody& B : Bodies) FDinkSecondaryMotion::ForgetKey(B.Key);
	Bodies.Reset();
	Index.Reset();
	Super::Deinitialize();
}

TStatId UDinkSecondaryMotionSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkSecondaryMotionSubsystem, STATGROUP_Tickables);
}

const FDinkSecondaryBody* UDinkSecondaryMotionSubsystem::FindBody(const USkeletalMeshComponent* Mesh) const
{
	const int32* At = Index.Find(Mesh);
	return At && Bodies.IsValidIndex(*At) ? &Bodies[*At] : nullptr;
}

bool UDinkSecondaryMotionSubsystem::Track(USkeletalMeshComponent* Mesh)
{
	if (!Mesh || Mesh->GetWorld() != GetWorld()) return false;
	const USkeletalMesh* Asset = Mesh->GetSkeletalMeshAsset();
	if (!Asset) return false;
	const FDinkSecondaryProfile* Profile = FDinkSecondaryProfile::Find(Asset->GetFName());
	FDinkSecondaryBody* Body = const_cast<FDinkSecondaryBody*>(FindBody(Mesh));
	if (!Profile)
	{
		// swapped to a mesh without secondary motion: clear what was shown and let the next scan drop it
		if (Body) { WriteOff(*Body); Body->Profile = nullptr; Body->MeshAsset = nullptr; }
		return false;
	}
	if (Body && Body->MeshAsset.Get() == Asset) return true;
	if (!Body)
	{
		Index.Add(Mesh, Bodies.Num());
		Body = &Bodies.AddDefaulted_GetRef();
		Body->Mesh = Mesh;
		Body->Key = Mesh;
	}
	Body->Profile = Profile;
	Body->MeshAsset = Asset;
	Body->ResetMotion();
	Body->bWritten = false;
	const FReferenceSkeleton& Ref = Asset->GetRefSkeleton();
	Body->Head = Ref.FindBoneIndex(TEXT("head"));
	Body->Pelvis = Ref.FindBoneIndex(TEXT("pelvis"));
	Body->ThighL = Ref.FindBoneIndex(TEXT("thigh_l")); Body->ThighR = Ref.FindBoneIndex(TEXT("thigh_r"));
	Body->CalfL = Ref.FindBoneIndex(TEXT("calf_l")); Body->CalfR = Ref.FindBoneIndex(TEXT("calf_r"));
	Body->FootL = Ref.FindBoneIndex(TEXT("foot_l")); Body->FootR = Ref.FindBoneIndex(TEXT("foot_r"));
	Body->PelvisBind = Body->Pelvis != INDEX_NONE ? RefComponentSpace(Ref, Body->Pelvis) : FTransform::Identity;
	const int32 NumChains = Profile->Chains.Num();
	Body->ChainSprings.SetNum(NumChains); Body->ChainPrev.Init(FVector::ZeroVector, NumChains);
	Body->ChainPrevVel.Init(FVector::ZeroVector, NumChains); Body->ChainAccel.Init(FVector::ZeroVector, NumChains);
	if (const UDinkStatsComponent* Stats = Mesh->GetOwner() ? Mesh->GetOwner()->FindComponentByClass<UDinkStatsComponent>() : nullptr)
		Body->PrevLife = Stats->Stats.Life;
	return true;
}

void UDinkSecondaryMotionSubsystem::Scan()
{
	const int32 Before = Bodies.Num();
	Bodies.RemoveAll([](const FDinkSecondaryBody& B)
	{
		if (B.Profile && B.Mesh.IsValid() && B.Mesh->IsRegistered()) return false;
		FDinkSecondaryMotion::ForgetKey(B.Key);
		return true;
	});
	if (Bodies.Num() != Before) RebuildIndex();
	UWorld* World = GetWorld();
	for (TObjectIterator<USkeletalMeshComponent> It(RF_ClassDefaultObject, true, EInternalObjectFlags::Garbage); It; ++It)
	{
		USkeletalMeshComponent* Mesh = *It;
		if (Mesh->GetWorld() != World || !Mesh->IsRegistered()) continue;
		Track(Mesh);
	}
	// world-alive's wind collection: found when its build and assets are present (soft, no compile dependency)
	if (!WindMpc)
	{
		static const TCHAR* Package = TEXT("/Game/Dink/WorldLife/MPC_Dink_World");
		if (FPackageName::DoesPackageExist(Package))
			WindMpc = LoadObject<UMaterialParameterCollection>(nullptr, TEXT("/Game/Dink/WorldLife/MPC_Dink_World.MPC_Dink_World"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	}
}

void UDinkSecondaryMotionSubsystem::RebuildIndex()
{
	Index.Reset();
	for (int32 i = 0; i < Bodies.Num(); ++i) Index.Add(Bodies[i].Key, i);
}

void UDinkSecondaryMotionSubsystem::NotifyHit(AActor* Actor, const FVector& WorldDirection, float Strength)
{
	if (!Actor || CVarHitPhysics.GetValueOnGameThread() == 0) return;
	for (FDinkSecondaryBody& B : Bodies)
	{
		USkeletalMeshComponent* Mesh = B.Mesh.Get();
		if (!Mesh || Mesh->GetOwner() != Actor || !B.Profile || !B.Profile->bJolt) continue;
		// the blow travels along WorldDirection: the chest gives way along it (mesh space: +Y forward, +X left)
		FVector Dir = WorldDirection.IsNearlyZero() ? HitDirection(Mesh) : WorldDirection;
		Dir = Mesh->GetComponentTransform().InverseTransformVectorNoScale(Dir.GetSafeNormal2D());
		const float S = FMath::Clamp(Strength, .2f, 1.f);
		// degrees per second: the head gives about 7 degrees at full strength (chest, neck and head shares summed), plus a
		// little twist away from the blow
		const float Peak = 10.f * S * CVarSecondaryScale.GetValueOnGameThread();
		const float Rate = Peak * 2.f * PI * B.Profile->Jolt.FrequencyHz;
		B.Jolt.Kick(FVector(Dir.Y * Rate, Dir.X * Rate, -Dir.X * Rate * .35f), B.Profile->Jolt);
	}
}

FVector UDinkSecondaryMotionSubsystem::HitDirection(const USkeletalMeshComponent* Mesh) const
{
	// the hero's damage reaches presentation as a life change only: the blow is taken to come from the nearest other
	// animated body within 4 m (a creature or a person), else from straight ahead
	const FVector At = Mesh->GetComponentLocation();
	const AActor* Self = Mesh->GetOwner();
	double Best = FMath::Square(400.0);
	FVector From = At + Mesh->GetComponentTransform().TransformVectorNoScale(FVector::YAxisVector) * 100.0;
	for (TObjectIterator<USkeletalMeshComponent> It(RF_ClassDefaultObject, true, EInternalObjectFlags::Garbage); It; ++It)
	{
		const USkeletalMeshComponent* Other = *It;
		if (Other->GetWorld() != GetWorld() || Other->GetOwner() == Self || !Other->IsRegistered() || !Other->IsVisible()) continue;
		const double D = FVector::DistSquared2D(Other->GetComponentLocation(), At);
		if (D < Best) { Best = D; From = Other->GetComponentLocation(); }
	}
	return (At - From).GetSafeNormal2D();
}

bool UDinkSecondaryMotionSubsystem::HairWind(const FVector& At, FVector& OutDir, float& OutSpeed) const
{
	const float T = float(GetWorld()->GetTimeSeconds());
	static IConsoleVariable* FoliageWind = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Wind"));
	const float Foliage = FoliageWind ? FMath::Max(FoliageWind->GetFloat(), 0.f) : 1.f;
	// world-alive's shared wind (MPC_Dink_World: WindDir xy = where it blows to, z = strength 0..2, already 0 indoors, at
	// Low and with dink.World.Wind 0, w = gustiness; WindGust x = the global gust, y = how fast the gust field travels)
	if (WindMpc)
		if (const UMaterialParameterCollectionInstance* Inst = GetWorld()->GetParameterCollectionInstance(WindMpc))
		{
			FLinearColor WindDir, WindGust(1, 1, 0, 0);
			if (Inst->GetVectorParameterValue(TEXT("WindDir"), WindDir))
			{
				Inst->GetVectorParameterValue(TEXT("WindGust"), WindGust);
				const FVector2D D2(WindDir.R, WindDir.G);
				OutDir = D2.IsNearlyZero() ? FVector(.8, .6, 0.0) : FVector(D2.GetSafeNormal(), 0.0);
				const float Gust = FDinkSecondaryMotion::FoliageGust(FVector2D(At), T, D2, WindGust.G, WindDir.A);
				OutSpeed = 3.5f * FMath::Max(WindDir.B, 0.f) * FMath::Clamp(WindGust.R, 0.f, 3.f) * Gust * Foliage;
				return OutSpeed > 0.f;
			}
		}
	// master: the foliage's own breeze (about 3 m/s along (0.8, 0.6), gusts travelling along (0.92, 0.39)), still indoors
	const UDinkGreyboxSubsystem* Greybox = GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>();
	const ADinkScreenVolume* Screen = Greybox ? Greybox->GetCurrentScreen() : nullptr;
	if (Screen && Screen->bIndoor) return false;
	OutDir = FVector(.8, .6, 0.0);
	OutSpeed = 3.f * FDinkSecondaryMotion::FoliageGust(FVector2D(At), T) * Foliage;
	return OutSpeed > 0.f;
}

void UDinkSecondaryMotionSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	Advance(DeltaTime, false);
}

void UDinkSecondaryMotionSubsystem::Advance(float DeltaTime, bool bForce)
{
	UWorld* World = GetWorld();
	if (!World) return;
	int32 Quality = CVarSecondaryQuality.GetValueOnGameThread();
	if (Quality < 0)
	{
		const int32 Effects = Scalability::GetQualityLevels().EffectsQuality;
		Quality = Effects <= 0 ? 0 : Effects == 1 ? 1 : 2;
	}
	if (bForce) Quality = 2;
	if (Quality == 0)
	{
		// Low: everything rests once (plain skinning, animated pose); no scan and no per-body work while off
		if (!bOff) { for (FDinkSecondaryBody& B : Bodies) WriteOff(B); bOff = true; }
		return;
	}
	bOff = false;
	const double Now = World->GetTimeSeconds();
	if (bForce || Now >= NextScan) { Scan(); NextScan = Now + .5; }
	for (FDinkSecondaryBody& B : Bodies)
	{
		// Medium: the springs step at 30 Hz (they sub-step inside), the pose data goes out every frame
		float SpringDt = DeltaTime;
		if (Quality == 1)
		{
			B.SpringDebt += DeltaTime;
			SpringDt = B.SpringDebt >= 1.f / 30.f ? B.SpringDebt : 0.f;
			if (SpringDt > 0.f) B.SpringDebt = 0.f;
		}
		const uint64 Start = FPlatformTime::Cycles64();
		if (UpdateBody(B, DeltaTime, SpringDt))
		{
			CostMicros += FPlatformTime::ToMilliseconds64(FPlatformTime::Cycles64() - Start) * 1000.0;
			++CostSamples;
		}
	}
	Accumulated += DeltaTime;
	if (Accumulated > 2.0 && CostSamples > 0) { MeanMicros = CostMicros / CostSamples; CostMicros = 0.0; CostSamples = 0; Accumulated = 0.0; }
}

void UDinkSecondaryMotionSubsystem::WriteOff(FDinkSecondaryBody& B)
{
	USkeletalMeshComponent* Mesh = B.Mesh.Get();
	if (!Mesh) return;
	static const TArray<float> Zero = [] { TArray<float> Z; Z.Init(0.f, DinkSecondaryCPD::Count); return Z; }();
	if (Mesh->GetCustomPrimitiveData().Data != Zero) Mesh->SetCustomPrimitiveDataFloatArray(0, Zero);
	B.bWritten = true;
	FDinkSecondaryMotion::PublishJolt(Mesh, FVector3f::ZeroVector);
	B.ResetMotion();
}

bool UDinkSecondaryMotionSubsystem::UpdateBody(FDinkSecondaryBody& B, float Dt, float SpringDt)
{
	USkeletalMeshComponent* Mesh = B.Mesh.Get();
	if (!Mesh || !B.Profile || Mesh->GetSkeletalMeshAsset() != B.MeshAsset.Get()) { if (Mesh) Track(Mesh); return false; }
	const FDinkSecondaryProfile& P = *B.Profile;
	// creature loose parts reach a pose only through a native Dink animation instance (the placement pigs play a
	// single-node blend space): elsewhere there is nothing to do
	const bool bNativePose = Cast<UDinkCreatureAnimInstance>(Mesh->GetAnimInstance()) || Cast<UDinkBodyAnimInstance>(Mesh->GetAnimInstance());
	const bool bMaterials = P.bHair || P.bSkirt;
	if (!bMaterials && !bNativePose) return false;
	// off screen (hundreds of creature bodies exist at once): creatures rest and start again when seen; the few people
	// with hair or skirt materials keep their data current so the first frame back in view is right
	if (!bMaterials && !bIgnoreVisibility && !Mesh->WasRecentlyRendered(.3f))
	{
		if (B.HistoryFrames > 0) { B.ResetMotion(); FDinkSecondaryMotion::PublishJolt(Mesh, FVector3f::ZeroVector); }
		return false;
	}
	const TArray<FTransform>& CS = Mesh->GetComponentSpaceTransforms();
	auto Valid = [&CS](int32 I) { return I != INDEX_NONE && CS.IsValidIndex(I); };
	if (!Valid(B.Head) || Dt <= 0.f) return false;
	const FTransform& Comp = Mesh->GetComponentTransform();
	const float Scale = FMath::Max(CVarSecondaryScale.GetValueOnGameThread(), 0.f);

	// anchor motion, world space: the head (hair) and the pelvis (skirt)
	const FVector HeadWorld = Comp.TransformPosition(CS[B.Head].GetLocation());
	const FVector PelvisWorld = Valid(B.Pelvis) ? Comp.TransformPosition(CS[B.Pelvis].GetLocation()) : HeadWorld;
	const FReferenceSkeleton& Ref = Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
	const FVector FaceDir = Comp.TransformVectorNoScale(CS[B.Head].GetRotation() * (RefComponentSpace(Ref, B.Head).GetRotation().Inverse() * FVector::YAxisVector));
	const float Yaw = FMath::Atan2(FaceDir.Y, FaceDir.X);
	// a teleport (screen change, load, warp, death restart) or a long hitch starts the springs again from rest
	const bool bJump = B.HistoryFrames > 0 && (FVector::DistSquared(HeadWorld, B.PrevHead) > FMath::Square(150.f) || Dt > .25f);
	if (bJump) B.ResetMotion();
	if (B.HistoryFrames > 0)
	{
		const FVector HeadVel = (HeadWorld - B.PrevHead) / Dt, PelvisVel = (PelvisWorld - B.PrevPelvis) / Dt;
		const float YawRate = FMath::FindDeltaAngleRadians(B.PrevYaw, Yaw) / Dt;
		if (B.HistoryFrames > 1)
		{
			// light low-pass (about 30 ms): the scripted bodies arrive in steps of whole frames
			const float A = 1.f - FMath::Exp(-Dt / .03f);
			B.HeadAccel = FMath::Lerp(B.HeadAccel, ((HeadVel - B.PrevHeadVel) / Dt).GetClampedToMaxSize(6000.f), A);
			B.PelvisAccel = FMath::Lerp(B.PelvisAccel, ((PelvisVel - B.PrevPelvisVel) / Dt).GetClampedToMaxSize(6000.f), A);
			B.YawAccel = FMath::Lerp(B.YawAccel, FMath::Clamp((YawRate - B.PrevYawRate) / Dt, -400.f, 400.f), A);
		}
		B.PrevHeadVel = HeadVel; B.PrevPelvisVel = PelvisVel; B.PrevYawRate = YawRate;
	}
	B.PrevHead = HeadWorld; B.PrevPelvis = PelvisWorld; B.PrevYaw = Yaw;
	B.HistoryFrames = FMath::Min(B.HistoryFrames + 1, 3);
	const bool bMotion = B.HistoryFrames > 2;

	TArray<float, TInlineAllocator<DinkSecondaryCPD::Count>> D;
	D.Init(0.f, DinkSecondaryCPD::Count);
	auto Put = [&D](int32 At, const FVector& V) { D[At] = float(V.X); D[At + 1] = float(V.Y); D[At + 2] = float(V.Z); };

	// hair: tips lag the head's acceleration, swing back and settle; wind leans them with the foliage's gusts
	if (P.bHair && CVarHairPhysics.GetValueOnGameThread() != 0)
	{
		FVector Wind = FVector::ZeroVector;
		const float WindScale = FMath::Max(CVarHairWind.GetValueOnGameThread(), 0.f);
		FVector Dir; float Speed = 0.f;
		if (P.HairWindCm > 0.f && WindScale > 0.f && HairWind(HeadWorld, Dir, Speed))
		{
			const float W = 2.f * PI * P.Hair.FrequencyHz;
			Wind = Dir.GetSafeNormal2D() * (P.HairWindCm * Speed * W * W * WindScale);
			// and a light flutter across the wind, a few times a second, that grows with it
			const float T = float(GetWorld()->GetTimeSeconds());
			const FVector Across = FVector::CrossProduct(FVector::UpVector, Dir.GetSafeNormal2D());
			Wind += (Across * FMath::Sin(T * 2.f * PI * 3.7f) + FVector::UpVector * .5f * FMath::Sin(T * 2.f * PI * 5.3f + 1.3f)) * (.18f * Wind.Size());
		}
		if (bMotion && SpringDt > 0.f)
		{
			B.Hair.Step(SpringDt, B.HeadAccel, Wind, P.Hair);
			B.HairYaw.Step(SpringDt, FVector(B.YawAccel, 0.f, 0.f), FVector::ZeroVector, P.HairYaw);
		}
		const FVector Tip = Comp.InverseTransformVector(B.Hair.X) * Scale;
		Put(DinkSecondaryCPD::HairOffset, Tip);
		D[DinkSecondaryCPD::HairYaw] = float(B.HairYaw.X.X * Scale);
		Put(DinkSecondaryCPD::HeadCentre, CS[B.Head].TransformPosition(HeadCentreLocal(Ref, B.Head)));
		D[DinkSecondaryCPD::HairWeight] = 1.f;
	}

	// skirt: a bell hung from the pelvis, pushed out by the legs, swinging behind the hips
	if (P.bSkirt && CVarGarmentPhysics.GetValueOnGameThread() != 0 && Valid(B.Pelvis) && Valid(B.ThighL) && Valid(B.ThighR)
		&& Valid(B.CalfL) && Valid(B.CalfR) && Valid(B.FootL) && Valid(B.FootR))
	{
		if (bMotion && SpringDt > 0.f) B.Skirt.Step(SpringDt, B.PelvisAccel, FVector::ZeroVector, P.Skirt);
		const FTransform Rigid = B.PelvisBind.Inverse() * CS[B.Pelvis];
		const FQuat Q = Rigid.GetRotation().GetNormalized();
		D[DinkSecondaryCPD::PelvisRotation] = float(Q.X); D[DinkSecondaryCPD::PelvisRotation + 1] = float(Q.Y);
		D[DinkSecondaryCPD::PelvisRotation + 2] = float(Q.Z); D[DinkSecondaryCPD::PelvisRotation + 3] = float(Q.W);
		Put(DinkSecondaryCPD::PelvisTranslation, Rigid.GetTranslation());
		Put(DinkSecondaryCPD::HipL, CS[B.ThighL].GetLocation()); Put(DinkSecondaryCPD::KneeL, CS[B.CalfL].GetLocation()); Put(DinkSecondaryCPD::AnkleL, CS[B.FootL].GetLocation());
		Put(DinkSecondaryCPD::HipR, CS[B.ThighR].GetLocation()); Put(DinkSecondaryCPD::KneeR, CS[B.CalfR].GetLocation()); Put(DinkSecondaryCPD::AnkleR, CS[B.FootR].GetLocation());
		Put(DinkSecondaryCPD::SkirtSway, Comp.InverseTransformVector(B.Skirt.X) * Scale);
	}

	// hit jolt: the hero's life falling is a hit (Stats is the authority); others are told through NotifyHit
	if (P.bJolt && CVarHitPhysics.GetValueOnGameThread() != 0)
	{
		if (const UDinkStatsComponent* Stats = Mesh->GetOwner() ? Mesh->GetOwner()->FindComponentByClass<UDinkStatsComponent>() : nullptr)
		{
			const int32 Life = Stats->Stats.Life;
			if (B.PrevLife != INDEX_NONE && Life < B.PrevLife && !bJump)
			{
				const float Lost = float(B.PrevLife - Life) / FMath::Max(1, Stats->Stats.LifeMax);
				NotifyHit(Mesh->GetOwner(), FVector::ZeroVector, FMath::Clamp(.35f + Lost * 4.f, .35f, 1.f));
			}
			B.PrevLife = Life;
		}
		if (SpringDt > 0.f && !B.Jolt.IsAtRest(.001f)) B.Jolt.Step(SpringDt, FVector::ZeroVector, FVector::ZeroVector, P.Jolt);
	}
	else B.Jolt.Reset();

	// loose parts (antennae, ears, tails): each chain lags its root's acceleration (world), shown in mesh space
	TArray<FVector3f, TInlineAllocator<4>> Lags;
	const bool bChains = bNativePose && P.Chains.Num() > 0 && B.ChainSprings.Num() == P.Chains.Num() && CVarLooseParts.GetValueOnGameThread() != 0;
	for (int32 C = 0; bChains && C < P.Chains.Num(); ++C)
	{
		const int32 RootBone = P.Chains[C].Num() > 0 ? Ref.FindBoneIndex(P.Chains[C][0]) : INDEX_NONE;
		if (!Valid(RootBone)) { Lags.Add(FVector3f::ZeroVector); continue; }
		const FVector Root = Comp.TransformPosition(CS[RootBone].GetLocation());
		if (B.HistoryFrames > 1)
		{
			const FVector Vel = (Root - B.ChainPrev[C]) / Dt;
			const float A = 1.f - FMath::Exp(-Dt / .03f);
			if (B.HistoryFrames > 2) B.ChainAccel[C] = FMath::Lerp(B.ChainAccel[C], ((Vel - B.ChainPrevVel[C]) / Dt).GetClampedToMaxSize(6000.f), A);
			B.ChainPrevVel[C] = Vel;
		}
		B.ChainPrev[C] = Root;
		if (bMotion && SpringDt > 0.f) B.ChainSprings[C].Step(SpringDt, B.ChainAccel[C], FVector::ZeroVector, P.Chain);
		Lags.Add(FVector3f(Comp.InverseTransformVector(B.ChainSprings[C].X) * Scale));
	}
	if (!bChains) for (FDinkSpring3& S : B.ChainSprings) S.Reset();
	FDinkSecondaryMotion::Publish(Mesh, FVector3f(B.Jolt.X), bChains ? &P : nullptr, bChains ? TConstArrayView<FVector3f>(Lags) : TConstArrayView<FVector3f>());

	if (Mesh->GetCustomPrimitiveData().Data.Num() != D.Num() || FMemory::Memcmp(Mesh->GetCustomPrimitiveData().Data.GetData(), D.GetData(), D.Num() * sizeof(float)) != 0)
		Mesh->SetCustomPrimitiveDataFloatArray(0, TConstArrayView<float>(D));
	B.bWritten = true;
	B.LastUpdate = GetWorld()->GetTimeSeconds();
	return true;
}

FString UDinkSecondaryMotionSubsystem::Report() const
{
	FString Out = FString::Printf(TEXT("secondary motion: %d bodies, mean %.1f us per body update (hair %d, garment %d, hit %d)\n"), Bodies.Num(), MeanMicros,
		CVarHairPhysics.GetValueOnGameThread(), CVarGarmentPhysics.GetValueOnGameThread(), CVarHitPhysics.GetValueOnGameThread());
	for (const FDinkSecondaryBody& B : Bodies)
	{
		const USkeletalMeshComponent* Mesh = B.Mesh.Get();
		Out += FString::Printf(TEXT("  %s on %s: hair tip %.2f cm, yaw lag %.3f rad, skirt %.2f cm, jolt %.2f deg\n"),
			B.Profile ? *B.Profile->Mesh.ToString() : TEXT("?"), Mesh && Mesh->GetOwner() ? *Mesh->GetOwner()->GetName() : TEXT("?"),
			B.Hair.X.Size(), B.HairYaw.X.X, B.Skirt.X.Size(), B.Jolt.X.Size());
	}
	return Out;
}

static FAutoConsoleCommandWithWorld GDinkSecondaryReport(TEXT("dink.Secondary.Report"), TEXT("Logs the tracked bodies, their spring states and the mean cost per body."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		if (const UDinkSecondaryMotionSubsystem* S = World ? World->GetSubsystem<UDinkSecondaryMotionSubsystem>() : nullptr)
			UE_LOG(LogDinkSecondary, Display, TEXT("%s"), *S->Report());
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkSecondaryHit(TEXT("dink.Secondary.Hit"), TEXT("dink.Secondary.Hit [strength]: jolts the player's body as a blow from the nearest body, else from the front (review aid)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UDinkSecondaryMotionSubsystem* S = World ? World->GetSubsystem<UDinkSecondaryMotionSubsystem>() : nullptr;
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		if (S && PC && PC->GetPawn()) S->NotifyHit(PC->GetPawn(), FVector::ZeroVector, Args.Num() > 0 ? FCString::Atof(*Args[0]) : 1.f);
	}));
