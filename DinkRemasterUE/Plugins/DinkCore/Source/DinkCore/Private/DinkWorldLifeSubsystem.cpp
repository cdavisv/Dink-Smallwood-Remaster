#include "DinkWorldLifeSubsystem.h"
#include "DinkLandforms.h"
#include "DinkCoreModule.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkEnvironmentSubsystem.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/WindDirectionalSourceComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Engine/WindDirectionalSource.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Scalability.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

static TAutoConsoleVariable<int32> CVarDinkWorldLife(TEXT("dink.World.Life"), 1,
	TEXT("World life (shared wind, walk-through bend, particles, ambient life): 1 on, 0 off. Presentation only."));
static TAutoConsoleVariable<float> CVarDinkWorldWind(TEXT("dink.World.Wind"), 1.f,
	TEXT("Multiplier of the regional wind of MPC_Dink_World and the wind source (0 = still air, 2 = double)."));
static TAutoConsoleVariable<float> CVarDinkWorldParticles(TEXT("dink.World.Particles"), 1.f,
	TEXT("Particle budget of the world life layer (0 = none; times sg.EffectsQuality: Low 0.25, Medium 0.6, High+ 1)."));
static TAutoConsoleVariable<int32> CVarDinkWorldStaticFoliageShadows(TEXT("dink.World.StaticFoliageShadows"), 1,
	TEXT("1: wind-swayed vegetation (M_Veg_Foliage / M_Veg_Bark) keeps cached rest-pose virtual shadow pages (Rigid invalidation); 0: Auto (re-rendered every frame)."));
static TAutoConsoleVariable<int32> CVarDinkWorldStats(TEXT("dink.World.Stats"), 0,
	TEXT("1: log DINK WORLD lines every 2 s (wind, particles, lights, CPU ms of the layer)."));

namespace
{
	const FName N_WindDir(TEXT("WindDir")), N_WindGust(TEXT("WindGust")), N_WorldLife(TEXT("WorldLife"));
	const FName N_Push[4] = { FName(TEXT("Push0")), FName(TEXT("Push1")), FName(TEXT("Push2")), FName(TEXT("Push3")) };
	const FName T_Creature(TEXT("DinkCreature")), T_Humanoid(TEXT("DinkHumanoid"));
	constexpr int32 CustomFloats = 6;   // r, g, b, opacity, shape, seed

	// motes are lit (pollen is dark at night, never a glowing speck); embers, sparks and glows are additive
	bool IsGlow(EDinkLifeParticle K) { return K == EDinkLifeParticle::Ember || K == EDinkLifeParticle::Spark || K == EDinkLifeParticle::Glow; }
	float ShapeOf(EDinkLifeParticle K)
	{
		switch (K)
		{
		case EDinkLifeParticle::Dust: return 0.f;
		case EDinkLifeParticle::Smoke: return 0.f;
		case EDinkLifeParticle::Debris: return 2.f;
		case EDinkLifeParticle::Ripple: return 1.f;
		case EDinkLifeParticle::Spark: return 1.f;
		default: return 0.f;
		}
	}
	float Num(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, float Default)
	{
		double V = Default;
		return O.IsValid() && O->TryGetNumberField(Key, V) ? float(V) : Default;
	}
	FDinkWindProfile ReadProfile(const TSharedPtr<FJsonObject>& O, const FDinkWindProfile& Base)
	{
		FDinkWindProfile P = Base;
		P.Strength = Num(O, TEXT("strength"), Base.Strength);
		P.Gustiness = Num(O, TEXT("gustiness"), Base.Gustiness);
		P.DirectionDeg = Num(O, TEXT("direction_deg"), Base.DirectionDeg);
		return P;
	}
	bool Finite(const FVector& V) { return FMath::IsFinite(V.X) && FMath::IsFinite(V.Y) && FMath::IsFinite(V.Z); }
}

// ------------------------------------------------------------------------------------------------ pure helpers

float DinkWorldLife::EffectiveStrength(float ProfileStrength, float CVarWind, bool bIndoor, int32 FoliageQuality)
{
	if (bIndoor || FoliageQuality <= 0) return 0.f;
	const float S = FMath::Max(ProfileStrength, 0.f) * FMath::Max(CVarWind, 0.f);
	return FMath::IsFinite(S) ? FMath::Min(S, 2.f) : 0.f;
}

float DinkWorldLife::GlobalGust(double TimeSeconds, float Gustiness)
{
	// three incommensurate slow waves: a lull every half minute or so, a gust building over 4-8 s
	const double T = FMath::IsFinite(TimeSeconds) ? FMath::Fmod(TimeSeconds, 100000.0) : 0.0;
	const double W = 0.55 * FMath::Sin(T * 0.21) + 0.30 * FMath::Sin(T * 0.53 + 1.7) + 0.15 * FMath::Sin(T * 1.31 + 4.1);
	const float G = 1.f + float(W) * 0.8f * FMath::Clamp(Gustiness, 0.f, 1.f);
	return FMath::Clamp(G, 0.3f, 1.8f);
}

FVector2D DinkWorldLife::DirectionOf(float DirectionDeg)
{
	const float R = FMath::DegreesToRadians(FMath::IsFinite(DirectionDeg) ? DirectionDeg : 37.f);
	return FVector2D(FMath::Cos(R), FMath::Sin(R));
}

FDinkWindProfile DinkWorldLife::EaseProfile(const FDinkWindProfile& From, const FDinkWindProfile& To, float Alpha)
{
	const float A = FMath::Clamp(Alpha, 0.f, 1.f);
	FDinkWindProfile P;
	P.Strength = FMath::Lerp(From.Strength, To.Strength, A);
	P.Gustiness = FMath::Lerp(From.Gustiness, To.Gustiness, A);
	const float Delta = FMath::FindDeltaAngleDegrees(From.DirectionDeg, To.DirectionDeg);
	P.DirectionDeg = FMath::UnwindDegrees(From.DirectionDeg + Delta * A);
	return P;
}

void DinkWorldLife::PickPushers(const FVector2D& Focus, const TArray<FVector4f>& Candidates, float Radius, int32 MaxSlots, TArray<FVector4f>& Out)
{
	Out.Reset();
	TArray<TPair<float, int32>, TInlineAllocator<32>> Near;
	for (int32 I = 0; I < Candidates.Num(); ++I)
	{
		const FVector4f& C = Candidates[I];
		if (C.W <= 0.f || !FMath::IsFinite(C.X) || !FMath::IsFinite(C.Y)) continue;
		const float D2 = FVector2f::DistSquared(FVector2f(C.X, C.Y), FVector2f(Focus));
		if (D2 <= Radius * Radius) Near.Add({ D2, I });
	}
	Near.Sort([](const TPair<float, int32>& A, const TPair<float, int32>& B) { return A.Key < B.Key || (A.Key == B.Key && A.Value < B.Value); });
	for (int32 I = 0; I < Near.Num() && Out.Num() < MaxSlots; ++I) Out.Add(Candidates[Near[I].Value]);
}

bool DinkWorldLife::IsFamilyEffect(const AActor* Actor)
{
	if (!Actor) return false;
	if (const ADinkPlaceholderActor* P = Cast<ADinkPlaceholderActor>(Actor))
	{
		if (P->Card && P->Card->IsVisible() && P->Card->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)) return true;
	}
	TInlineComponentArray<UPrimitiveComponent*> Parts(Actor);
	for (const UPrimitiveComponent* Part : Parts)
	{
		if (Part && Part->ComponentHasTag(UDinkArtFamilySubsystem::ScriptEffectTag)) return true;
	}
	return false;
}

float DinkWorldLife::DustinessOfGround(const FLinearColor& G)
{
	// green meadow: g clearly above r and b. Bare earth, sand, snow, stone: not.
	const float Green = G.G - 0.5f * (G.R + G.B);
	const float Bright = (G.R + G.G + G.B) / 3.f;
	if (!FMath::IsFinite(Green) || Bright <= 0.005f) return 0.f;
	const float Rel = Green / FMath::Max(Bright, 0.02f);
	return FMath::Clamp(1.f - (Rel - 0.05f) / 0.25f, 0.f, 1.f);
}

// ------------------------------------------------------------------------------------------------ subsystem

bool UDinkWorldLifeSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId UDinkWorldLifeSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkWorldLifeSubsystem, STATGROUP_Tickables);
}

float UDinkWorldLifeSubsystem::Frand()
{
	// own stream (xorshift): never the simulation's random numbers
	Rand ^= Rand << 13; Rand ^= Rand >> 17; Rand ^= Rand << 5;
	return float(Rand & 0xFFFFFF) / float(0x1000000);
}

void UDinkWorldLifeSubsystem::LoadConfig()
{
	DefaultWind = FDinkWindProfile();
	RegionWind.Reset();
	const FString Path = FPaths::ProjectContentDir() / TEXT("Dink/Data/Environment/world_life.json");
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!FFileHelper::LoadFileToString(Text, *Path) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid())
	{
		UE_LOG(LogDink, Warning, TEXT("world_life.json missing or unreadable (%s): default wind everywhere"), *Path);
		return;
	}
	const TSharedPtr<FJsonObject>* Wind = nullptr;
	if (Root->TryGetObjectField(TEXT("wind"), Wind) && Wind)
	{
		const TSharedPtr<FJsonObject>* Def = nullptr;
		if ((*Wind)->TryGetObjectField(TEXT("default"), Def) && Def) DefaultWind = ReadProfile(*Def, DefaultWind);
		WindEaseSeconds = FMath::Max(0.1f, Num(*Wind, TEXT("ease_s"), WindEaseSeconds));
		const TSharedPtr<FJsonObject>* Regions = nullptr;
		if ((*Wind)->TryGetObjectField(TEXT("regions"), Regions) && Regions)
		{
			for (const auto& Pair : (*Regions)->Values)
			{
				const TSharedPtr<FJsonObject>* O = nullptr;
				if (Pair.Value.IsValid() && Pair.Value->TryGetObject(O) && O) RegionWind.Add(FName(*Pair.Key), ReadProfile(*O, DefaultWind));
			}
		}
	}
	const TSharedPtr<FJsonObject>* Push = nullptr;
	if (Root->TryGetObjectField(TEXT("push"), Push) && Push)
	{
		PushRadiusCm = Num(*Push, TEXT("radius_cm"), PushRadiusCm);
		PushCreatureRadiusCm = Num(*Push, TEXT("creature_radius_cm"), PushCreatureRadiusCm);
		PushReachCm = Num(*Push, TEXT("reach_cm"), PushReachCm);
	}
	FireSeqs.Reset();
	FireClasses.Reset();
	const TSharedPtr<FJsonObject>* Fire = nullptr;
	if (Root->TryGetObjectField(TEXT("fire"), Fire) && Fire)
	{
		auto Read = [](const TSharedPtr<FJsonObject>& O) { return FVector2f(Num(O, TEXT("height_cm"), 100.f), Num(O, TEXT("scale"), 1.f)); };
		const TSharedPtr<FJsonObject>* Seqs = nullptr;
		if ((*Fire)->TryGetObjectField(TEXT("sequences"), Seqs) && Seqs)
		{
			for (const auto& Pair : (*Seqs)->Values)
			{
				const TSharedPtr<FJsonObject>* O = nullptr;
				if (Pair.Value.IsValid() && Pair.Value->TryGetObject(O) && O) FireSeqs.Add(FCString::Atoi(*Pair.Key), Read(*O));
			}
		}
		const TSharedPtr<FJsonObject>* Classes = nullptr;
		if ((*Fire)->TryGetObjectField(TEXT("classes"), Classes) && Classes)
		{
			for (const auto& Pair : (*Classes)->Values)
			{
				const TSharedPtr<FJsonObject>* O = nullptr;
				if (Pair.Value.IsValid() && Pair.Value->TryGetObject(O) && O) FireClasses.Add(FName(*Pair.Key), Read(*O));
			}
		}
	}
	const TSharedPtr<FJsonObject>* Parts = nullptr;
	if (Root->TryGetObjectField(TEXT("particles"), Parts) && Parts)
	{
		MaxParticles = FMath::Clamp(Num(*Parts, TEXT("max"), MaxParticles), 0.f, 4000.f);
		CullCm = Num(*Parts, TEXT("cull_cm"), CullCm);
		StrideCm = FMath::Max(10.f, Num(*Parts, TEXT("stride_cm"), StrideCm));
	}
}

void UDinkWorldLifeSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	if (!FApp::CanEverRender() || bActive) return;
	LoadConfig();
	WorldCollection = LoadObject<UMaterialParameterCollection>(nullptr, WorldCollectionPath(), nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!WorldCollection) UE_LOG(LogDink, Warning, TEXT("DINK WORLD: %s not found (run Scripts/import_world_life.sh): foliage keeps its default wind"), WorldCollectionPath());

	FActorSpawnParameters SP;
	SP.ObjectFlags |= RF_Transient;
	SP.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	// the scene wind (cloth, and any engine system that reads wind sources); directional, the whole world
	if (AWindDirectionalSource* W = InWorld.SpawnActor<AWindDirectionalSource>(AWindDirectionalSource::StaticClass(), FTransform::Identity, SP))
	{
		WindActor = W;
		WindSource = W->GetComponent();
	}
	Holder = InWorld.SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, SP);
	if (Holder)
	{
		USceneComponent* Root = NewObject<USceneComponent>(Holder, TEXT("Root"));
		Holder->SetRootComponent(Root);
		Root->RegisterComponent();
		Holder->AddInstanceComponent(Root);
		UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
		UMaterialInterface* Lit = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Dink/WorldLife/M_WorldLife_Lit.M_WorldLife_Lit"), nullptr, LOAD_NoWarn | LOAD_Quiet);
		UMaterialInterface* Glow = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Dink/WorldLife/M_WorldLife_Glow.M_WorldLife_Glow"), nullptr, LOAD_NoWarn | LOAD_Quiet);
		auto MakePool = [&](const TCHAR* Name, UMaterialInterface* Mat) -> UInstancedStaticMeshComponent*
		{
			if (!Plane || !Mat) return nullptr;
			UInstancedStaticMeshComponent* P = NewObject<UInstancedStaticMeshComponent>(Holder, Name);
			P->SetStaticMesh(Plane);
			P->SetMaterial(0, Mat);
			P->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			P->SetCollisionResponseToAllChannels(ECR_Ignore);
			P->SetGenerateOverlapEvents(false);
			P->SetCastShadow(false);
			P->bReceivesDecals = false;
			P->SetCanEverAffectNavigation(false);
			P->SetNumCustomDataFloats(CustomFloats);
			P->SetMobility(EComponentMobility::Movable);
			P->SetupAttachment(Root);
			P->RegisterComponent();
			Holder->AddInstanceComponent(P);
			return P;
		};
		LitPool = MakePool(TEXT("WorldLifeLit"), Lit);
		GlowPool = MakePool(TEXT("WorldLifeGlow"), Glow);
		if (!LitPool || !GlowPool) UE_LOG(LogDink, Warning, TEXT("DINK WORLD: particle materials missing under /Game/Dink/WorldLife (run Scripts/import_world_life.sh): no particles"));
	}
	Rand ^= uint32(FPlatformTime::Cycles());
	bActive = true;
	UE_LOG(LogDink, Display, TEXT("DINK WORLD: life layer on (%d wind regions, MPC %s, particles %s)"), RegionWind.Num(),
		WorldCollection ? TEXT("yes") : TEXT("no"), (LitPool && GlowPool) ? TEXT("yes") : TEXT("no"));
}

void UDinkWorldLifeSubsystem::Deinitialize()
{
	ClearAll();
	Super::Deinitialize();
}

void UDinkWorldLifeSubsystem::ClearAll()
{
	RestoreFoliageShadows();
	Particles.Reset();
	if (IsValid(LitPool)) LitPool->ClearInstances();
	if (IsValid(GlowPool)) GlowPool->ClearInstances();
	for (FLight& L : Lights)
	{
		if (IsValid(L.Comp)) L.Comp->SetVisibility(false);
		L.Key = 0;
		L.Until = 0.f;
	}
}

UInstancedStaticMeshComponent* UDinkWorldLifeSubsystem::PoolFor(EDinkLifeParticle Kind) const
{
	return IsGlow(Kind) ? GlowPool.Get() : LitPool.Get();
}

void UDinkWorldLifeSubsystem::Emit(const FDinkLifeParticleSpec& Spec)
{
	if (!IsActive() || Budget <= 0.f || !PoolFor(Spec.Kind)) return;
	if (Particles.Num() >= int32(MaxParticles * FMath::Min(Budget, 2.f))) return;
	if (!Finite(Spec.Location) || !Finite(Spec.Velocity) || !(Spec.Life > 0.f)) { ++NonFinite; return; }
	if (FVector::DistSquared(Spec.Location, Camera) > FMath::Square(CullCm)) return;
	FParticle& P = Particles.AddDefaulted_GetRef();
	P.S = Spec;
	P.S.Life = FMath::Clamp(Spec.Life, 0.02f, 30.f);
	P.P = Spec.Location;
	P.V = Spec.Velocity;
	P.Seed = Frand();
	++EmittedTotal;
}

UPointLightComponent* UDinkWorldLifeSubsystem::AcquireLight()
{
	const float Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.f;
	for (FLight& L : Lights)
	{
		if (L.Comp && Now > L.Until) return L.Comp;
	}
	if (!Holder || Lights.Num() >= 8) return nullptr;
	UPointLightComponent* C = NewObject<UPointLightComponent>(Holder);
	C->SetCastShadows(false);
	C->SetMobility(EComponentMobility::Movable);
	C->bUseInverseSquaredFalloff = true;
	C->SetIntensityUnits(ELightUnits::Candelas);
	C->SetSpecularScale(0.5f);
	C->SetSourceRadius(25.f);
	C->SetIntensity(0.f);   // the engine default is 5000: never draw a frame at it
	C->SetVisibility(false);
	C->SetupAttachment(Holder->GetRootComponent());
	C->RegisterComponent();
	Holder->AddInstanceComponent(C);
	FLight& L = Lights.AddDefaulted_GetRef();
	L.Comp = C;
	L.Seed = Frand() * 100.f;
	return C;
}

void UDinkWorldLifeSubsystem::Flash(const FVector& At, const FLinearColor& Colour, float Intensity, float RadiusCm, float Seconds)
{
	if (!IsActive() || Budget <= 0.f || !Finite(At)) return;
	UPointLightComponent* C = AcquireLight();
	if (!C) return;
	const float Now = GetWorld()->GetTimeSeconds();
	for (FLight& L : Lights)
	{
		if (L.Comp != C) continue;
		L.Key = 0; L.Base = Intensity; L.Flicker = 0.25f; L.Start = Now; L.Until = Now + FMath::Max(Seconds, 0.05f);
	}
	C->SetWorldLocation(At);
	C->SetLightColor(Colour);
	C->SetAttenuationRadius(RadiusCm);
	C->SetIntensity(Intensity);
	C->SetVisibility(true);
}

void UDinkWorldLifeSubsystem::KeepLight(uint64 Key, const FVector& At, const FLinearColor& Colour, float Intensity, float RadiusCm, float Flicker)
{
	if (!IsActive() || Key == 0 || !Finite(At)) return;
	const float Now = GetWorld()->GetTimeSeconds();
	FLight* Found = Lights.FindByPredicate([Key](const FLight& L) { return L.Key == Key && L.Comp; });
	if (!Found)
	{
		UPointLightComponent* C = AcquireLight();
		if (!C) return;
		Found = Lights.FindByPredicate([C](const FLight& L) { return L.Comp == C; });
		Found->Key = Key;
		Found->Start = Now;
		C->SetLightColor(Colour);
		C->SetAttenuationRadius(RadiusCm);
		C->SetIntensity(Intensity);
		C->SetWorldLocation(At);
		C->SetVisibility(true);
	}
	Found->Base = Intensity;
	Found->Flicker = Flicker;
	Found->Until = Now + 0.15f;
	Found->Comp->SetWorldLocation(At);
}

int32 UDinkWorldLifeSubsystem::GetLiveLights() const
{
	const float Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.f;
	int32 N = 0;
	for (const FLight& L : Lights) N += (L.Comp && Now <= L.Until) ? 1 : 0;
	return N;
}

float UDinkWorldLifeSubsystem::GroundZ(const FVector& At, float Fallback) const
{
	UWorld* World = GetWorld();
	if (!World || !Finite(At)) return Fallback;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(DinkWorldLifeGround), false);
	if (Holder) Q.AddIgnoredActor(Holder);
	if (const APlayerController* PC = World->GetFirstPlayerController(); PC && PC->GetPawn()) Q.AddIgnoredActor(PC->GetPawn());
	// the hidden 1997 hardness prisms and player blockers block Visibility too: the first visible surface is the ground
	static const FName P_HardSolid(TEXT("DinkHardSolid")), P_HardLow(TEXT("DinkHardLow")), P_PlayerBlock(TEXT("DinkPlayerBlock"));
	// landforms are drawn only (no collision): their surface is the ground unless something drawn stands higher on it
	float Land = 0.f;
	FVector LandNormal;
	const bool bLand = DinkLandforms::GroundAt(World, FVector2D(At), Land, LandNormal);
	for (int32 Try = 0; Try < 6; ++Try)
	{
		FHitResult Hit;
		if (!World->LineTraceSingleByChannel(Hit, At + FVector(0, 0, 150), At - FVector(0, 0, 1500), ECC_Visibility, Q)) break;
		const UPrimitiveComponent* C = Hit.GetComponent();
		const FName Profile = C ? C->GetCollisionProfileName() : NAME_None;
		if (C && C->IsVisible() && !C->bHiddenInGame && Profile != P_HardSolid && Profile != P_HardLow && Profile != P_PlayerBlock)
			return bLand ? FMath::Max(Land, float(Hit.ImpactPoint.Z)) : float(Hit.ImpactPoint.Z);
		if (!C) break;
		Q.AddIgnoredComponent(C);
	}
	return bLand ? Land : Fallback;
}

FVector UDinkWorldLifeSubsystem::GetWindVelocityAt(const FVector& At) const
{
	(void)At;   // one directional wind for now; local shelter (forest, walls) is a later refinement
	const float Speed = 350.f * WindStrength * WindGustNow;
	return FVector(WindDir.X * Speed, WindDir.Y * Speed, 0.0);
}

void UDinkWorldLifeSubsystem::UpdateWind(float DeltaTime, const ADinkScreenVolume* Current)
{
	UWorld* World = GetWorld();
	const FDinkWindProfile* Region = Current ? RegionWind.Find(Current->Region) : nullptr;
	FDinkWindProfile Target = Region ? *Region : DefaultWind;
	const bool bIndoor = Current && Current->bIndoor;
	const int32 Foliage = Scalability::GetQualityLevels().FoliageQuality;
	if (!bWindSeeded) { WindNow = Target; bWindSeeded = true; }
	WindNow = DinkWorldLife::EaseProfile(WindNow, Target, FMath::Clamp(DeltaTime / WindEaseSeconds, 0.f, 1.f));
	const float Raw = DinkWorldLife::EffectiveStrength(WindNow.Strength, CVarDinkWorldWind.GetValueOnGameThread(), bIndoor, Foliage);
	// ease indoors/outdoors too, so a door does not snap the trees still
	WindStrength = FMath::FInterpTo(WindStrength, Raw, DeltaTime, 1.5f);
	if (FMath::Abs(WindStrength - Raw) < 0.002f) WindStrength = Raw;
	WindDir = DinkWorldLife::DirectionOf(WindNow.DirectionDeg);
	WindGustNow = DinkWorldLife::GlobalGust(World->GetTimeSeconds(), WindNow.Gustiness);
	// the gust field's travel is integrated here: the material never multiplies absolute time by a changing speed
	const float Speed = 0.6f + 0.6f * WindStrength;
	GustTravel += WindDir * double(DeltaTime * Speed);
	if (FMath::Abs(GustTravel.X) > 8000.0 || FMath::Abs(GustTravel.Y) > 8000.0) GustTravel = FVector2D::ZeroVector;   // float precision; one jump every ~2 h of wind

	if (WorldCollection)
	{
		if (UMaterialParameterCollectionInstance* MPC = World->GetParameterCollectionInstance(WorldCollection))
		{
			MPC->SetVectorParameterValue(N_WindDir, FLinearColor(WindDir.X, WindDir.Y, WindStrength, WindNow.Gustiness));
			MPC->SetVectorParameterValue(N_WindGust, FLinearColor(WindGustNow, Speed, float(GustTravel.X), float(GustTravel.Y)));
			MPC->SetScalarParameterValue(N_WorldLife, 1.f);
		}
	}
	if (WindActor && WindSource)
	{
		WindActor->SetActorRotation(FRotator(0.0, FMath::RadiansToDegrees(FMath::Atan2(WindDir.Y, WindDir.X)), 0.0));
		// Speed carries the magnitude (m/s, as GetWindVelocityAt), Strength only switches it on
		WindSource->SetStrength(WindStrength > 0.f ? 1.f : 0.f);
		WindSource->SetSpeed(3.5f * WindStrength * WindGustNow);
		WindSource->SetMinimumGustAmount(0.1f * WindNow.Gustiness);
		WindSource->SetMaximumGustAmount(0.5f * WindNow.Gustiness);
	}
}

void UDinkWorldLifeSubsystem::UpdatePushers(float DeltaTime)
{
	UWorld* World = GetWorld();
	const APlayerController* PC = World->GetFirstPlayerController();
	APawn* Player = PC ? PC->GetPawn() : nullptr;
	const double Now = World->GetTimeSeconds();
	const UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
	const ADinkScreenVolume* Screen = Grey ? Grey->GetCurrentScreen() : nullptr;
	const int32 ScreenNumber = Screen ? Screen->ScreenNumber : -1;
	if (Now >= NextPusherScan || ScreenNumber != PusherScreen)
	{
		NextPusherScan = Now + 3.0;
		PusherScreen = ScreenNumber;
		PusherCandidates.Reset();
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			AActor* A = *It;
			if (!A || A == Player || A->IsHidden() || (!A->ActorHasTag(T_Creature) && !A->ActorHasTag(T_Humanoid))) continue;
			if (FVector::DistSquared2D(A->GetActorLocation(), Camera) > FMath::Square(PushReachCm)) continue;
			PusherCandidates.Add(A);
		}
		for (auto It = LastPos.CreateIterator(); It; ++It) if (!It.Key().IsValid()) It.RemoveCurrent();
		for (auto It = Motion.CreateIterator(); It; ++It) if (!It.Key().IsValid()) It.RemoveCurrent();
	}
	TArray<FVector4f> Cands;
	auto Note = [&](AActor* A, float Radius, float Standing)
	{
		if (!A) return;
		const FVector P = A->GetActorLocation();
		FVector* Last = LastPos.Find(A);
		const float Speed = (Last && DeltaTime > 0.f) ? float(FVector::Dist2D(P, *Last) / DeltaTime) : 0.f;
		LastPos.Add(A, P);
		float& M = Motion.FindOrAdd(A);
		const float Want = Speed > 15.f && Speed < 3000.f ? 1.f : 0.f;   // a teleport is not a walk
		M = FMath::FInterpTo(M, Want, DeltaTime, Want > M ? 6.f : 1.2f);
		const float W = Standing + (1.f - Standing) * M;
		if (W > 0.01f) Cands.Add(FVector4f(float(P.X), float(P.Y), Radius, W));
	};
	if (Player) Note(Player, PushRadiusCm, 0.45f);
	for (const TWeakObjectPtr<AActor>& W : PusherCandidates) Note(W.Get(), PushCreatureRadiusCm, 0.f);
	TArray<FVector4f> Slots;
	const FVector Focus = Player ? Player->GetActorLocation() : Camera;
	DinkWorldLife::PickPushers(FVector2D(Focus), Cands, PushReachCm, 4, Slots);
	if (WorldCollection)
	{
		if (UMaterialParameterCollectionInstance* MPC = World->GetParameterCollectionInstance(WorldCollection))
		{
			for (int32 I = 0; I < 4; ++I)
			{
				const FVector4f S = I < Slots.Num() ? Slots[I] : FVector4f(0.f, 0.f, 1.f, 0.f);
				MPC->SetVectorParameterValue(N_Push[I], FLinearColor(S.X, S.Y, S.Z, S.W));
			}
		}
	}
}

void UDinkWorldLifeSubsystem::GatherChimneys()
{
	Chimneys.Reset();
	RigidShadows.RemoveAll([](const TWeakObjectPtr<UPrimitiveComponent>& W) { return !W.IsValid(); });
	UWorld* World = GetWorld();
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (FVector::DistSquared2D(It->GetActorLocation(), Camera) > FMath::Square(9000.0)) continue;
		TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
		for (UStaticMeshComponent* M : Meshes)
		{
			const UStaticMesh* Mesh = M ? M->GetStaticMesh() : nullptr;
			if (!Mesh || !M->IsVisible()) continue;
			ApplyFoliageShadowPolicy(M);
			bool* Known = ChimneyMesh.Find(Mesh);
			if (!Known) Known = &ChimneyMesh.Add(Mesh, Mesh->GetName().Contains(TEXT("Chimney")));
			if (!*Known) continue;
			const FBoxSphereBounds MeshBounds = Mesh->GetBounds();
			auto Add = [&](const FTransform& T)
			{
				const FBox B = MeshBounds.GetBox().TransformBy(T);
				const FVector Top(B.GetCenter().X, B.GetCenter().Y, B.Max.Z);
				// not every hearth is lit: a stable two in three by position
				const uint32 H = HashCombine(GetTypeHash(int32(Top.X / 50.0)), GetTypeHash(int32(Top.Y / 50.0)));
				if (H % 3 != 0 && Finite(Top)) Chimneys.Add(Top);
			};
			if (UInstancedStaticMeshComponent* ISM = Cast<UInstancedStaticMeshComponent>(M))
			{
				for (int32 I = 0; I < ISM->GetInstanceCount() && I < 64; ++I)
				{
					FTransform T;
					if (ISM->GetInstanceTransform(I, T, true)) Add(T);
				}
			}
			else
			{
				Add(M->GetComponentTransform());
			}
		}
	}
}


bool UDinkWorldLifeSubsystem::FireOfSequence(int32 Seq, float& OutHeightCm, float& OutScale) const
{
	const FVector2f* F = Seq > 0 ? FireSeqs.Find(Seq) : nullptr;
	if (!F) return false;
	OutHeightCm = F->X;
	OutScale = F->Y;
	return true;
}

void UDinkWorldLifeSubsystem::EmitFire(uint64 Key, const FVector& Base, float HeightCm, float Scale, bool bIndoor, float DeltaTime)
{
	if (!IsActive() || !Finite(Base) || Key == 0) return;
	if (FVector::DistSquared2D(Base, Camera) > FMath::Square(CullCm)) return;
	Scale = FMath::Clamp(Scale, 0.2f, 5.f);
	HeightCm = FMath::Clamp(HeightCm, 10.f, 1500.f);
	const float Now = GetWorld()->GetTimeSeconds();
	FVector4f& T = FireTimers.FindOrAdd(Key, FVector4f(0.f, 0.f, 0.f, Now));
	T.W = Now;
	const float B = FMath::Max(Budget, 0.f);
	T.X += DeltaTime * (bIndoor ? 0.f : 3.f * Scale) * B;     // smoke (indoors the hearth draws up its chimney)
	T.Y += DeltaTime * 5.f * Scale * B;                       // embers
	T.Z += DeltaTime * 12.f;                                  // flame glow
	const FVector Top = Base + FVector(0, 0, HeightCm);
	const float Spread = 18.f * Scale;
	while (T.X >= 1.f)
	{
		T.X -= 1.f;
		FDinkLifeParticleSpec S;
		S.Kind = EDinkLifeParticle::Smoke;
		S.Location = Top + FVector((Frand() - 0.5f) * Spread, (Frand() - 0.5f) * Spread, 0.f);
		S.Velocity = FVector(0, 0, 70.f + 40.f * Frand());
		S.Life = 3.5f + 2.f * Frand();
		S.SizeStart = 35.f * Scale; S.SizeEnd = (160.f + 90.f * Frand()) * Scale;
		const float Grey = 0.16f + 0.12f * Frand();
		S.Colour = FLinearColor(Grey, Grey * 0.97f, Grey * 0.95f, 0.5f);
		S.Drag = 0.6f; S.Gravity = -12.f; S.WindFollow = 0.45f;   // rises first, then leans down the wind
		Emit(S);
	}
	while (T.Y >= 1.f)
	{
		T.Y -= 1.f;
		FDinkLifeParticleSpec S;
		S.Kind = EDinkLifeParticle::Ember;
		S.Location = Base + FVector((Frand() - 0.5f) * Spread * 1.4f, (Frand() - 0.5f) * Spread * 1.4f, HeightCm * (0.3f + 0.5f * Frand()));
		S.Velocity = FVector((Frand() - 0.5f) * 40.f, (Frand() - 0.5f) * 40.f, 90.f + 90.f * Frand());
		S.Life = 0.8f + 1.2f * Frand();
		S.SizeStart = 6.f; S.SizeEnd = 2.f;
		S.Colour = FLinearColor(1.f, 0.38f + 0.2f * Frand(), 0.06f, 3.5f);
		S.Drag = 1.2f; S.Gravity = -25.f; S.WindFollow = 0.5f;
		Emit(S);
	}
	while (T.Z >= 1.f)
	{
		T.Z -= 1.f;
		FDinkLifeParticleSpec S;
		S.Kind = EDinkLifeParticle::Glow;
		// a flickering flame core: overlapping warm glows of random size just above the fire's base
		S.Location = Base + FVector((Frand() - 0.5f) * Spread, (Frand() - 0.5f) * Spread, HeightCm * (0.2f + 0.3f * Frand()));
		S.Velocity = FVector(0, 0, 60.f);
		S.Life = 0.25f + 0.15f * Frand();
		S.SizeStart = (35.f + 25.f * Frand()) * Scale; S.SizeEnd = 15.f * Scale;
		S.Colour = FLinearColor(1.f, 0.4f + 0.15f * Frand(), 0.08f, 0.9f);
		S.Drag = 0.f;
		Emit(S);
	}
	if (!bIndoor) KeepLight(Key, Base + FVector(0, 0, HeightCm * 0.6f), FLinearColor(1.f, 0.5f, 0.2f), 160.f * Scale, 900.f * FMath::Sqrt(Scale), 0.35f);
}

void UDinkWorldLifeSubsystem::ApplyFoliageShadowPolicy(UStaticMeshComponent* M)
{
	if (!M || CVarDinkWorldStaticFoliageShadows.GetValueOnGameThread() == 0 || !M->CastShadow) return;
	if (M->ShadowCacheInvalidationBehavior != EShadowCacheInvalidationBehavior::Auto) return;   // perf-stutter's Static forests, or set by its owner
	UMaterialInterface* Mat = M->GetNumMaterials() > 0 ? M->GetMaterial(0) : nullptr;
	if (!Mat) return;
	bool* Known = FoliageMaterial.Find(Mat);
	if (!Known)
	{
		const UMaterial* Base = Mat->GetBaseMaterial();
		const FName N = Base ? Base->GetFName() : NAME_None;
		Known = &FoliageMaterial.Add(Mat, N == FName(TEXT("M_Veg_Foliage")) || N == FName(TEXT("M_Veg_Bark")));
	}
	if (!*Known) return;
	M->ShadowCacheInvalidationBehavior = EShadowCacheInvalidationBehavior::Rigid;
	M->MarkRenderStateDirty();
	RigidShadows.Add(M);
}

void UDinkWorldLifeSubsystem::RestoreFoliageShadows()
{
	for (const TWeakObjectPtr<UPrimitiveComponent>& W : RigidShadows)
	{
		UPrimitiveComponent* C = W.Get();
		if (!C || C->ShadowCacheInvalidationBehavior != EShadowCacheInvalidationBehavior::Rigid) continue;
		C->ShadowCacheInvalidationBehavior = EShadowCacheInvalidationBehavior::Auto;
		C->MarkRenderStateDirty();
	}
	RigidShadows.Reset();
}

void UDinkWorldLifeSubsystem::GatherPlacedFires()
{
	PlacedFires.Reset();
	if (FireSeqs.IsEmpty() && FireClasses.IsEmpty()) return;
	UWorld* World = GetWorld();
	auto Fire = [&](int32 Seq, FName ClassId, FVector2f& Out) -> bool
	{
		if (const FVector2f* C = FireClasses.Find(ClassId)) { Out = *C; return true; }
		if (const FVector2f* S = FireSeqs.Find(Seq)) { Out = *S; return true; }
		return false;
	};
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* A = *It;
		if (!A || A->IsHidden() || FVector::DistSquared2D(A->GetActorLocation(), Camera) > FMath::Square(9000.0)) continue;
		if (DinkWorldLife::IsFamilyEffect(A)) continue;   // the family row draws this fire (and its light)
		if (const UDinkOriginComponent* O = UDinkOriginComponent::FindOnActor(A))
		{
			FVector2f F;
			if (Fire(O->Sequence, O->ClassId, F))
			{
				FPlacedFire& P = PlacedFires.AddDefaulted_GetRef();
				P.Key = (uint64(GetTypeHash(O->OriginId.ToString())) << 1) | 1ull;
				P.Base = A->GetActorLocation();
				P.Base.Z = GroundZ(P.Base, float(P.Base.Z));
				P.Height = F.X; P.Scale = F.Y; P.Actor = A;
			}
		}
		if (const UDinkInstanceOriginsComponent* IO = A->FindComponentByClass<UDinkInstanceOriginsComponent>())
		{
			for (const FDinkInstanceOrigin& Inst : IO->Origins)
			{
				FVector2f F;
				if (!Fire(Inst.Sequence, Inst.ClassId, F)) continue;
				TInlineComponentArray<UInstancedStaticMeshComponent*> ISMs(A);
				for (UInstancedStaticMeshComponent* ISM : ISMs)
				{
					FTransform T;
					if (!ISM || ISM->GetFName() != Inst.ComponentName || !ISM->IsVisible() || !ISM->GetInstanceTransform(Inst.InstanceIndex, T, true)) continue;
					FPlacedFire& P = PlacedFires.AddDefaulted_GetRef();
					P.Key = (uint64(GetTypeHash(Inst.OriginId.ToString())) << 1) | 1ull;
					P.Base = T.GetLocation();
					P.Height = F.X; P.Scale = F.Y; P.Actor = A;
				}
			}
		}
	}
}

void UDinkWorldLifeSubsystem::UpdateAmbient(float DeltaTime, const ADinkScreenVolume* Current)
{
	UWorld* World = GetWorld();
	if (Budget <= 0.f) return;
	const APlayerController* PC = World->GetFirstPlayerController();
	const APawn* Player = PC ? PC->GetPawn() : nullptr;
	const bool bIndoor = Current && Current->bIndoor;

	// footstep dust: one small puff per stride on bare ground (earth, sand, snow, paths), tinted by the ground
	if (Player && !bIndoor)
	{
		const FVector P = Player->GetActorLocation();
		const float Step = float(FVector::Dist2D(P, LastFoot));
		LastFoot = P;
		if (Step < 200.f) FootTravel += Step; else FootTravel = 0.f;   // a teleport or screen warp is not a stride
		if (FootTravel >= StrideCm)
		{
			FootTravel = 0.f;
			FLinearColor Ground(0.4f, 0.36f, 0.3f);
			UDinkEnvironmentSubsystem* Env = World->GetSubsystem<UDinkEnvironmentSubsystem>();
			const bool bHasGround = Env && Env->GroundColourAt(FVector2D(P), Ground);
			const float Dusty = bHasGround ? DinkWorldLife::DustinessOfGround(Ground) : 0.f;
			if (Dusty > 0.05f)
			{
				const float Z = GroundZ(P, float(P.Z) - 90.f);
				const FVector Back = -Player->GetVelocity().GetSafeNormal2D();
				for (int32 I = 0; I < 3; ++I)
				{
					FDinkLifeParticleSpec S;
					S.Kind = EDinkLifeParticle::Dust;
					S.Location = FVector(P.X + (Frand() - 0.5f) * 30.f, P.Y + (Frand() - 0.5f) * 30.f, Z + 4.f);
					S.Velocity = Back * (20.f + 30.f * Frand()) + FVector(0, 0, 18.f + 14.f * Frand());
					S.Life = 0.9f + 0.6f * Frand();
					S.SizeStart = 16.f; S.SizeEnd = 70.f + 30.f * Frand();
					// a touch darker and warmer than the ground it rises from, so it reads on pale earth too (16 Nov: 0.32 x ground x 1.25 was invisible on 408)
					const FLinearColor Tint = (Ground * FLinearColor(0.95f, 0.88f, 0.78f)).GetClamped(0.f, 1.f);
					S.Colour = FLinearColor(Tint.R, Tint.G, Tint.B, 0.55f * Dusty);
					S.Drag = 2.5f; S.Gravity = -4.f; S.WindFollow = 0.25f;
					Emit(S);
				}
			}
		}
	}

	// chimney smoke on the screens in view
	const double Now = World->GetTimeSeconds();
	const int32 Screen = Current ? Current->ScreenNumber : -1;
	// chimneys and placed fires: on a screen change and once more 3 s later (neighbour art dresses late); no periodic scans
	if (Screen != ChimneyScreen && Now > 2.0)
	{
		ChimneyScreen = Screen;
		NextChimneyScan = Now + 3.0;
		const double ScanStart = FPlatformTime::Seconds();
		GatherChimneys();
		GatherPlacedFires();
		// whole-world actor walk (no per-screen index on master yet): its cost is logged, it is the layer's entry hitch
		UE_LOG(LogDink, Display, TEXT("DINK WORLD: scan screen %d: %d chimneys, %d fires, %d rigid shadows in %.2f ms"), Screen, Chimneys.Num(), PlacedFires.Num(), RigidShadows.Num(),
			(FPlatformTime::Seconds() - ScanStart) * 1000.0);
	}
	else if (NextChimneyScan > 0.0 && Now >= NextChimneyScan)
	{
		NextChimneyScan = 0.0;
		const double ScanStart = FPlatformTime::Seconds();
		GatherChimneys();
		GatherPlacedFires();
		// whole-world actor walk (no per-screen index on master yet): its cost is logged, it is the layer's entry hitch
		UE_LOG(LogDink, Display, TEXT("DINK WORLD: scan screen %d: %d chimneys, %d fires, %d rigid shadows in %.2f ms"), Screen, Chimneys.Num(), PlacedFires.Num(), RigidShadows.Num(),
			(FPlatformTime::Seconds() - ScanStart) * 1000.0);
	}
	for (const FPlacedFire& F : PlacedFires)
	{
		const AActor* A = F.Actor.Get();
		if (!A || A->IsHidden() || DinkWorldLife::IsFamilyEffect(A)) continue;   // dressed by a family effect row after the scan
		EmitFire(F.Key, F.Base, F.Height, F.Scale, bIndoor, DeltaTime);
	}
	for (auto It = FireTimers.CreateIterator(); It; ++It) if (Now - It.Value().W > 2.0) It.RemoveCurrent();
	ChimneyTimer += DeltaTime;
	if (!bIndoor && ChimneyTimer >= 0.45f / FMath::Max(Budget, 0.25f))
	{
		ChimneyTimer = 0.f;
		for (const FVector& Top : Chimneys)
		{
			if (FVector::DistSquared2D(Top, Camera) > FMath::Square(5000.0)) continue;
			FDinkLifeParticleSpec S;
			S.Kind = EDinkLifeParticle::Smoke;
			S.Location = Top + FVector((Frand() - 0.5f) * 20.f, (Frand() - 0.5f) * 20.f, 10.f);
			S.Velocity = FVector(0, 0, 55.f + 25.f * Frand());
			S.Life = 5.f + 2.5f * Frand();
			S.SizeStart = 35.f; S.SizeEnd = 260.f + 120.f * Frand();
			S.Colour = FLinearColor(0.62f, 0.6f, 0.58f, 0.35f);
			S.Drag = 0.35f; S.Gravity = -6.f; S.WindFollow = 0.9f;
			Emit(S);
		}
	}

	// pollen and seed fluff drifting on the wind over meadows (a few at a time, near the player)
	MoteTimer += DeltaTime;
	if (Player && !bIndoor && WindStrength > 0.05f && MoteTimer >= 0.35f / Budget)
	{
		MoteTimer = 0.f;
		const FVector P = Player->GetActorLocation();
		const FVector At(P.X + (Frand() - 0.5f) * 1600.f, P.Y + (Frand() - 0.5f) * 1100.f, P.Z);
		FLinearColor Ground;
		UDinkEnvironmentSubsystem* Env = World->GetSubsystem<UDinkEnvironmentSubsystem>();
		if (Env && Env->GroundColourAt(FVector2D(At), Ground) && DinkWorldLife::DustinessOfGround(Ground) < 0.3f)
		{
			FDinkLifeParticleSpec S;
			S.Kind = EDinkLifeParticle::Mote;
			S.Location = FVector(At.X, At.Y, GroundZ(At, float(P.Z) - 90.f) + 40.f + 120.f * Frand());
			S.Velocity = FVector(0, 0, 4.f * (Frand() - 0.3f));
			S.Life = 5.f + 4.f * Frand();
			S.SizeStart = S.SizeEnd = 2.2f + 1.6f * Frand();
			S.Colour = FLinearColor(0.95f, 0.9f, 0.72f, 0.7f);
			S.Drag = 0.8f; S.WindFollow = 0.6f;
			Emit(S);
		}
	}
}

void UDinkWorldLifeSubsystem::UpdateParticles(float DeltaTime)
{
	const FVector WindV = GetWindVelocityAt(Camera);
	const float Now = GetWorld()->GetTimeSeconds();
	for (int32 I = Particles.Num() - 1; I >= 0; --I)
	{
		FParticle& P = Particles[I];
		P.Age += DeltaTime;
		if (P.Age >= P.S.Life) { Particles.RemoveAtSwap(I, EAllowShrinking::No); continue; }
		if (!P.bSettled)
		{
			const FVector Drift = WindV * P.S.WindFollow;
			P.V += ((Drift - P.V) * FMath::Min(P.S.Drag * DeltaTime, 1.f));
			P.V.Z -= P.S.Gravity * DeltaTime;
			P.P += P.V * DeltaTime;
			if (P.S.Kind == EDinkLifeParticle::Debris && P.P.Z <= P.S.FloorZ)
			{
				P.P.Z = P.S.FloorZ + 1.f;
				P.V = FVector::ZeroVector;
				P.bSettled = true;
			}
		}
		if (!Finite(P.P) || !Finite(P.V)) { ++NonFinite; Particles.RemoveAtSwap(I, EAllowShrinking::No); }
	}
	// translucent puffs draw in the order of their instances: far ones first, so dense smoke does not pop
	Order.Reset();
	for (int32 I = 0; I < Particles.Num(); ++I) Order.Add(I);
	const FVector Cam = Camera;
	Order.Sort([this, &Cam](int32 A, int32 B) { return FVector::DistSquared(Particles[A].P, Cam) > FVector::DistSquared(Particles[B].P, Cam); });
	LitT.Reset(); GlowT.Reset(); LitD.Reset(); GlowD.Reset();
	for (const int32 Index : Order)
	{
		const FParticle& P = Particles[Index];
		const float T = P.Age / P.S.Life;
		const float Size = FMath::Lerp(P.S.SizeStart, P.S.SizeEnd, 1.f - FMath::Square(1.f - T));
		// fade in over the first 12%, out over the last 45% (debris holds, then fades)
		float A = FMath::Min(T / 0.12f, 1.f) * FMath::Min((1.f - T) / 0.45f, 1.f);
		if (P.S.Kind == EDinkLifeParticle::Debris) A = FMath::Min((1.f - T) / 0.2f, 1.f);
		if (P.S.Kind == EDinkLifeParticle::Ember) A *= 0.6f + 0.4f * FMath::Sin(Now * 23.f + P.Seed * 40.f);
		A *= P.S.Colour.A;
		const FVector ToCam = (Camera - P.P).GetSafeNormal();
		FQuat Rot;
		FVector Scale(Size / 100.f);
		switch (P.S.Kind)
		{
		case EDinkLifeParticle::Ripple:
			Rot = FQuat::Identity;
			break;
		case EDinkLifeParticle::Debris:
			Rot = FQuat(FVector(P.Seed, 1.f - P.Seed, 0.4f).GetSafeNormal(), P.bSettled ? P.Seed * 6.f : (P.Age * 9.f + P.Seed * 6.f));
			Scale = FVector(Size / 100.f, Size / 100.f * (0.35f + 0.4f * P.Seed), 1.f);
			break;
		case EDinkLifeParticle::Spark:
		{
			const FVector Along = P.V.GetSafeNormal();
			Rot = (Along.IsNearlyZero() ? FRotationMatrix::MakeFromZ(ToCam) : FRotationMatrix::MakeFromZX(ToCam, Along)).ToQuat();
			Scale = FVector(FMath::Clamp(float(P.V.Size()) * 0.0009f, Size / 100.f, 0.6f), Size / 100.f * 0.25f, 1.f);
			break;
		}
		default:
			Rot = FRotationMatrix::MakeFromZ(ToCam).ToQuat() * FQuat(FVector::UpVector, P.Seed * 6.283f + (P.S.Kind == EDinkLifeParticle::Smoke ? P.Age * 0.3f : 0.f));
			break;
		}
		const bool bGlow = IsGlow(P.S.Kind);
		(bGlow ? GlowT : LitT).Add(FTransform(Rot, P.P, Scale));
		TArray<float>& D = bGlow ? GlowD : LitD;
		D.Add(P.S.Colour.R); D.Add(P.S.Colour.G); D.Add(P.S.Colour.B); D.Add(FMath::Max(A, 0.f)); D.Add(ShapeOf(P.S.Kind)); D.Add(P.Seed);
	}
	PushPool(LitPool, LitT, LitD, bLitParked);
	PushPool(GlowPool, GlowT, GlowD, bGlowParked);
}

void UDinkWorldLifeSubsystem::PushPool(UInstancedStaticMeshComponent* Pool, const TArray<FTransform>& T, const TArray<float>& D, bool& bParked)
{
	if (!Pool) return;
	const int32 Have = Pool->GetInstanceCount();
	if (T.Num() == 0)
	{
		// nothing alive: an idle pool is not touched again (no upload, no render-state churn)
		if (Have > 0 && !bParked) { Pool->ClearInstances(); }
		bParked = true;
		return;
	}
	bParked = false;
	// unused slots park zero-sized at the first live particle (not at the world origin, which would stretch the bounds)
	const FTransform Parked(FQuat::Identity, T[0].GetLocation(), FVector::ZeroVector);
	if (Have < T.Num())
	{
		AllT.Reset();
		AllT.Init(Parked, T.Num() - Have);
		Pool->AddInstances(AllT, false, true, false);
	}
	else if (Have > T.Num() + 64)
	{
		Pool->ClearInstances();
		Pool->AddInstances(T, false, true, false);
	}
	const int32 Count = Pool->GetInstanceCount();
	AllT.Reset();
	AllT.Append(T);
	while (AllT.Num() < Count) AllT.Add(Parked);
	AllD.Reset();
	AllD.Append(D);
	AllD.SetNumZeroed(Count * CustomFloats);
	Pool->SetCustomData(0, Count - 1, AllD, false);
	// the instance data manager pushes the changed instances itself: no MarkRenderStateDirty per frame
	Pool->BatchUpdateInstancesTransforms(0, AllT, true, false, true);
}

void UDinkWorldLifeSubsystem::UpdateLights(float DeltaTime)
{
	(void)DeltaTime;
	const float Now = GetWorld()->GetTimeSeconds();
	for (FLight& L : Lights)
	{
		if (!L.Comp) continue;
		if (Now > L.Until)
		{
			if (L.Comp->IsVisible()) L.Comp->SetVisibility(false);
			L.Key = 0;
			continue;
		}
		float I = L.Base;
		if (L.Key == 0)
		{
			// a flash: up at once, then down along a short tail
			const float T = FMath::Clamp((Now - L.Start) / FMath::Max(L.Until - L.Start, 0.01f), 0.f, 1.f);
			I *= FMath::Square(1.f - T);
		}
		const float F = 1.f + L.Flicker * (0.55f * FMath::Sin(Now * 9.1f + L.Seed) + 0.3f * FMath::Sin(Now * 23.7f + L.Seed * 2.f) + 0.15f * FMath::Sin(Now * 3.3f + L.Seed * 5.f));
		L.Comp->SetIntensity(FMath::Max(I * F, 0.f));
	}
}

void UDinkWorldLifeSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	UWorld* World = GetWorld();
	if (!bActive || !World) return;
	const double Start = FPlatformTime::Seconds();
	const bool bWant = CVarDinkWorldLife.GetValueOnGameThread() != 0;
	if (bWant != bEnabled)
	{
		bEnabled = bWant;
		ChimneyScreen = -2;   // back on: chimneys, fires and the foliage shadow policy are gathered again at once
		if (!bEnabled)
		{
			ClearAll();
			// back to the material defaults: the foliage sways as it did before this layer
			if (WorldCollection)
			{
				if (UMaterialParameterCollectionInstance* MPC = World->GetParameterCollectionInstance(WorldCollection))
				{
					MPC->SetVectorParameterValue(N_WindDir, FLinearColor(0.8f, 0.6f, 1.f, 1.f));
					MPC->SetVectorParameterValue(N_WindGust, FLinearColor(1.f, 1.f, 0.f, 0.f));
					for (const FName& N : N_Push) MPC->SetVectorParameterValue(N, FLinearColor(0.f, 0.f, 1.f, 0.f));
					MPC->SetScalarParameterValue(N_WorldLife, 0.f);
				}
			}
			if (WindSource) WindSource->SetStrength(0.f);
		}
	}
	if (!bEnabled) return;
	if (CVarDinkWorldStaticFoliageShadows.GetValueOnGameThread() == 0 && !RigidShadows.IsEmpty()) RestoreFoliageShadows();
	DeltaTime = FMath::Clamp(DeltaTime, 0.f, 0.1f);
	const APlayerController* PC = World->GetFirstPlayerController();
	if (PC && PC->PlayerCameraManager) Camera = PC->PlayerCameraManager->GetCameraLocation();
	const int32 Effects = Scalability::GetQualityLevels().EffectsQuality;
	Budget = FMath::Clamp(CVarDinkWorldParticles.GetValueOnGameThread(), 0.f, 2.f) * (Effects <= 0 ? 0.25f : Effects == 1 ? 0.6f : 1.f);

	const UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
	const ADinkScreenVolume* Current = Grey ? Grey->GetCurrentScreen() : nullptr;
	UpdateWind(DeltaTime, Current);
	UpdatePushers(DeltaTime);
	UpdateAmbient(DeltaTime, Current);
	UpdateParticles(DeltaTime);
	UpdateLights(DeltaTime);

	const double Ms = (FPlatformTime::Seconds() - Start) * 1000.0;
	if (CVarDinkWorldStats.GetValueOnGameThread() != 0 && World->GetTimeSeconds() >= NextStats)
	{
		NextStats = World->GetTimeSeconds() + 2.0;
		UE_LOG(LogDink, Display, TEXT("DINK WORLD: screen %d region %s wind %.2f dir %.0f gust %.2f | particles %d lights %d emitted %lld nonfinite %lld chimneys %d fires %d rigidshadows %d | actors %d | tick %.3f ms"),
			Current ? Current->ScreenNumber : -1, Current ? *Current->Region.ToString() : TEXT("-"), WindStrength,
			FMath::RadiansToDegrees(FMath::Atan2(WindDir.Y, WindDir.X)), WindGustNow, Particles.Num(), GetLiveLights(), EmittedTotal, NonFinite, Chimneys.Num(), PlacedFires.Num(), RigidShadows.Num(), World->GetActorCount(), Ms);
	}
}
