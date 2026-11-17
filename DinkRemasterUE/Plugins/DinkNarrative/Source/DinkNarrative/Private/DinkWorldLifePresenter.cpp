#include "DinkWorldLifePresenter.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkScriptSpriteComponent.h"
#include "DinkStorySubsystem.h"
#include "DinkWorldLifeSubsystem.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkCoreModule.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "HAL/IConsoleManager.h"

namespace
{
	const FName C_Seq(TEXT("seq")), C_PSeq(TEXT("pseq")), C_Brain(TEXT("brain"));
	bool Finite(const FVector& V) { return FMath::IsFinite(V.X) && FMath::IsFinite(V.Y) && FMath::IsFinite(V.Z); }
}

DinkWorldLifeRoles::FTables DinkWorldLifeRoles::Defaults()
{
	FTables T;
	// dink.ini: 20 burning tree, 86 fireplace fire, 155-157 small fires (154 is the burn mark), 425 island torch, 427 fire loop
	T.Fire = { 20, 86, 155, 156, 157, 425, 427 };
	// item-fb.c / item-sfb.c (comets 502-508, fireballs 512-518) and item-ice.c (163)
	T.Fireball = { 502, 504, 506, 508, 512, 514, 516, 518, 163 };
	// dam-fire.c 70 (explo), dam-sfb.c 167 (shock), 161 atomic, 171 fire-mountain blast. NOT 164: the creature layer
	// draws a 164 kill as the duck/pig blood burst (gore at the 1997 level); never fire over it
	T.Bursts = { 70, 161, 167, 171 };
	// bar-*.c hit(): sp_seq 173 (barel-) with brain 5
	T.BarrelBreak = { 173 };
	// dink.cpp: brain 11 repeating missile, 17 missile that ends with its animation (D:16874/16880)
	T.MissileBrains = { 11, 17 };
	// dink.ini 409-412: Dink's push sequences
	T.PushSeqs = { 312, 314, 316, 318 };
	return T;
}

EDinkLifeSpriteRole DinkWorldLifeRoles::RoleOf(const FTables& T, int32 Seq, int32 PSeq, int32 Brain)
{
	if (Seq > 0 && T.Bursts.Contains(Seq)) return EDinkLifeSpriteRole::Burst;
	if (T.MissileBrains.Contains(Brain))
	{
		const int32 S = Seq > 0 ? Seq : PSeq;
		return T.Fireball.Contains(S) ? EDinkLifeSpriteRole::Fireball : EDinkLifeSpriteRole::Missile;
	}
	if (Seq > 0 && T.BarrelBreak.Contains(Seq)) return EDinkLifeSpriteRole::Barrel;
	if (Seq > 0 && T.Fire.Contains(Seq)) return EDinkLifeSpriteRole::Fire;
	return EDinkLifeSpriteRole::None;
}

bool UDinkWorldLifePresenter::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void FDinkWorldLifePresentTickFunction::ExecuteTick(float DeltaTime, ELevelTick TickType, ENamedThreads::Type CurrentThread, const FGraphEventRef& MyCompletionGraphEvent)
{
	if (IsValid(Target) && TickType != LEVELTICK_ViewportsOnly) Target->Present(DeltaTime);
}

void UDinkWorldLifePresenter::LoadTables()
{
	Tables = DinkWorldLifeRoles::Defaults();
	const FString Path = FPaths::ProjectContentDir() / TEXT("Dink/Data/Environment/world_life.json");
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!FFileHelper::LoadFileToString(Text, *Path) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid()) return;
	const TSharedPtr<FJsonObject>* Roles = nullptr;
	if (!Root->TryGetObjectField(TEXT("sprite_roles"), Roles) || !Roles) return;
	auto Extend = [&](const TCHAR* Key, TSet<int32>& Into)
	{
		const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
		if ((*Roles)->TryGetArrayField(Key, List) && List) for (const TSharedPtr<FJsonValue>& V : *List) if (V.IsValid()) Into.Add(int32(V->AsNumber()));
	};
	Extend(TEXT("fire"), Tables.Fire);
	Extend(TEXT("fireball"), Tables.Fireball);
	Extend(TEXT("bursts"), Tables.Bursts);
	Extend(TEXT("barrel_break"), Tables.BarrelBreak);
	Extend(TEXT("push"), Tables.PushSeqs);
}

void UDinkWorldLifePresenter::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	if (!FApp::CanEverRender() || !InWorld.PersistentLevel || PresentTick.IsTickFunctionRegistered()) return;
	LoadTables();
	Rand ^= uint32(FPlatformTime::Cycles());
	PresentTick.Target = this;
	PresentTick.TickGroup = TG_PostUpdateWork;
	PresentTick.bCanEverTick = true;
	PresentTick.bStartWithTickEnabled = true;
	PresentTick.RegisterTickFunction(InWorld.PersistentLevel);
}

void UDinkWorldLifePresenter::Deinitialize()
{
	for (TPair<int32, FFollow>& P : Followed) RestoreMarker(P.Value);
	Followed.Reset();
	if (PresentTick.IsTickFunctionRegistered()) PresentTick.UnRegisterTickFunction();
	Super::Deinitialize();
}

float UDinkWorldLifePresenter::Frand()
{
	Rand ^= Rand << 13; Rand ^= Rand >> 17; Rand ^= Rand << 5;
	return float(Rand & 0xFFFFFF) / float(0x1000000);
}

void UDinkWorldLifePresenter::RestoreMarker(FFollow& F)
{
	if (!F.bMarkerHidden) return;
	F.bMarkerHidden = false;
	if (ADinkScriptSpriteActor* A = Cast<ADinkScriptSpriteActor>(F.Actor.Get()); A && A->Marker) A->Marker->SetVisibility(true, false);
}

void UDinkWorldLifePresenter::Burst(const FVector& At, bool bBig)
{
	UDinkWorldLifeSubsystem* Life = GetWorld()->GetSubsystem<UDinkWorldLifeSubsystem>();
	if (!Life || !Life->IsActive()) return;
	const float K = bBig ? 2.f : 1.f;
	const float FloorZ = Life->GroundZ(At, float(At.Z) - 60.f);
	FDinkLifeParticleSpec S;
	S.Kind = EDinkLifeParticle::Glow;
	S.Location = At;
	S.Life = 0.35f;
	S.SizeStart = 90.f * K; S.SizeEnd = 220.f * K;
	S.Colour = FLinearColor(1.f, 0.48f, 0.14f, 1.6f);
	S.Drag = 0.f;
	Life->Emit(S);
	for (int32 I = 0; I < int32(16 * K); ++I)
	{
		FDinkLifeParticleSpec P;
		P.Kind = EDinkLifeParticle::Spark;
		P.Location = At;
		const FVector Dir = FVector(Frand() - 0.5f, Frand() - 0.5f, 0.15f + 0.7f * Frand()).GetSafeNormal();
		P.Velocity = Dir * (300.f + 450.f * Frand()) * FMath::Sqrt(K);
		P.Life = 0.35f + 0.35f * Frand();
		P.SizeStart = 7.f; P.SizeEnd = 3.f;
		P.Colour = FLinearColor(1.f, 0.55f + 0.3f * Frand(), 0.15f, 5.f);
		P.Drag = 1.5f; P.Gravity = 650.f;
		Life->Emit(P);
	}
	for (int32 I = 0; I < int32(6 * K); ++I)
	{
		FDinkLifeParticleSpec P;
		P.Kind = EDinkLifeParticle::Smoke;
		P.Location = At + FVector((Frand() - 0.5f) * 50.f * K, (Frand() - 0.5f) * 50.f * K, (Frand() - 0.3f) * 40.f);
		P.Velocity = FVector((Frand() - 0.5f) * 80.f, (Frand() - 0.5f) * 80.f, 40.f + 50.f * Frand());
		P.Life = 2.f + 1.5f * Frand();
		P.SizeStart = 50.f * K; P.SizeEnd = (190.f + 80.f * Frand()) * K;
		const float G = 0.12f + 0.1f * Frand();
		P.Colour = FLinearColor(G, G * 0.95f, G * 0.9f, 0.45f);
		P.Drag = 1.2f; P.Gravity = -10.f; P.WindFollow = 0.6f;
		Life->Emit(P);
	}
	for (int32 I = 0; I < int32(6 * K); ++I)
	{
		FDinkLifeParticleSpec P;
		P.Kind = EDinkLifeParticle::Debris;
		P.Location = At;
		P.Velocity = FVector((Frand() - 0.5f) * 400.f, (Frand() - 0.5f) * 400.f, 200.f + 250.f * Frand());
		P.Life = 2.5f + Frand();
		P.SizeStart = P.SizeEnd = 4.f + 4.f * Frand();
		P.Colour = FLinearColor(0.08f, 0.07f, 0.06f, 1.f);
		P.Drag = 0.6f; P.Gravity = 900.f; P.FloorZ = FloorZ;
		Life->Emit(P);
	}
	Life->Flash(At + FVector(0, 0, 40), FLinearColor(1.f, 0.55f, 0.25f), 220.f * K, 1500.f * K, 0.5f);
}

void UDinkWorldLifePresenter::BarrelBreak(const FVector& At)
{
	UDinkWorldLifeSubsystem* Life = GetWorld()->GetSubsystem<UDinkWorldLifeSubsystem>();
	if (!Life || !Life->IsActive()) return;
	const float FloorZ = Life->GroundZ(At, float(At.Z));
	for (int32 I = 0; I < 16; ++I)
	{
		FDinkLifeParticleSpec P;
		P.Kind = EDinkLifeParticle::Debris;
		P.Location = FVector(At.X, At.Y, FloorZ + 30.f + 40.f * Frand());
		P.Velocity = FVector((Frand() - 0.5f) * 380.f, (Frand() - 0.5f) * 380.f, 150.f + 260.f * Frand());
		P.Life = 6.f + 3.f * Frand();
		P.SizeStart = P.SizeEnd = 8.f + 14.f * Frand();
		const float W = 0.75f + 0.5f * Frand();
		P.Colour = FLinearColor(0.34f * W, 0.22f * W, 0.12f * W, 1.f);
		P.Drag = 0.4f; P.Gravity = 950.f; P.FloorZ = FloorZ;
		Life->Emit(P);
	}
	for (int32 I = 0; I < 5; ++I)
	{
		FDinkLifeParticleSpec P;
		P.Kind = EDinkLifeParticle::Dust;
		P.Location = FVector(At.X + (Frand() - 0.5f) * 40.f, At.Y + (Frand() - 0.5f) * 40.f, FloorZ + 20.f);
		P.Velocity = FVector((Frand() - 0.5f) * 120.f, (Frand() - 0.5f) * 120.f, 30.f + 30.f * Frand());
		P.Life = 1.4f + 0.6f * Frand();
		P.SizeStart = 30.f; P.SizeEnd = 120.f;
		P.Colour = FLinearColor(0.5f, 0.42f, 0.32f, 0.35f);
		P.Drag = 2.f; P.Gravity = -5.f; P.WindFollow = 0.3f;
		Life->Emit(P);
	}
}

void UDinkWorldLifePresenter::Present(float DeltaTime)
{
	UWorld* World = GetWorld();
	UDinkWorldLifeSubsystem* Life = World ? World->GetSubsystem<UDinkWorldLifeSubsystem>() : nullptr;
	const UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
	const UDinkStorySubsystem* Story = Instance ? Instance->GetSubsystem<UDinkStorySubsystem>() : nullptr;
	const UDinkDirector* Director = Story ? Story->GetDirector() : nullptr;
	const UDinkGameplay* Game = Story ? Story->GetGameplay() : nullptr;
	if (!Life || !Director || !Game) return;
	if (!Life->IsActive())
	{
		for (TPair<int32, FFollow>& P : Followed) RestoreMarker(P.Value);
		Followed.Reset();
		return;
	}
	DeltaTime = FMath::Clamp(DeltaTime, 0.f, 0.1f);
	TickDemos(DeltaTime);
	const int32 Screen = Director->GetCurrentScreen();
	const int32 Serial = Director->GetSpriteResetSerial();
	if (Screen != SeenScreen || Serial != SeenResetSerial)
	{
		// a new screen (or a restored save): nothing seen there yet starts a burst or a break
		SeenScreen = Screen;
		SeenResetSerial = Serial;
		for (TPair<int32, FFollow>& P : Followed) RestoreMarker(P.Value);
		Followed.Reset();
	}
	const UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
	const ADinkScreenVolume* Volume = Grey ? Grey->GetCurrentScreen() : nullptr;
	const bool bIndoor = Volume && Volume->bIndoor;
	const FDinkGameplayData& Data = Game->GetData();

	TSet<int32, DefaultKeyFuncs<int32>, TInlineSetAllocator<64>> Alive;
	for (const TPair<int32, FDinkSprite>& Pair : Director->GetSprites())
	{
		const FDinkSprite& Sprite = Pair.Value;
		if (Pair.Key == 1 || Sprite.bText || !Sprite.bActive || (Sprite.Screen > 0 && Sprite.Screen != Screen)) continue;
		const int32 Seq = Sprite.GetProp(C_Seq), PSeq = Sprite.GetProp(C_PSeq), Brain = Sprite.GetProp(C_Brain);
		EDinkLifeSpriteRole Role = DinkWorldLifeRoles::RoleOf(Tables, Seq, PSeq, Brain);
		if (Role == EDinkLifeSpriteRole::Fire && Sprite.Origin.IsValid())
		{
			// a placement drawn as fire from the start is the core layer's (it finds placed fires by class/sequence)
			const FDinkPlacementInfo* P = Data.FindPlacement(Sprite.Origin);
			if (P && Tables.Fire.Contains(P->Seq) && P->Seq == Seq) Role = EDinkLifeSpriteRole::None;
		}
		FFollow* Known = Followed.Find(Pair.Key);
		if (Role == EDinkLifeSpriteRole::None)
		{
			if (Known) { RestoreMarker(*Known); Followed.Remove(Pair.Key); }
			continue;
		}
		AActor* Actor = Sprite.Actor.Get();
		// a family effect row draws this sprite (fire walls, embers, script effects of PR #166): its fire, smoke and light are
		// that layer's; adding ours would double them
		if (DinkWorldLife::IsFamilyEffect(Actor))
		{
			if (Known) { RestoreMarker(*Known); Followed.Remove(Pair.Key); }
			continue;
		}
		FVector At;
		if (Actor) At = Actor->GetActorLocation();
		else if (!Director->PixelToWorld(Sprite.Screen > 0 ? Sprite.Screen : Screen, Sprite.X, Sprite.Y, At)) continue;
		if (!Finite(At)) continue;
		Alive.Add(Pair.Key);
		// a reused handle (create_sprite makes a new actor) is a new sprite: its burst plays, no trail runs from the old one
		const bool bNew = !Known || Known->Role != Role || Known->Seq != Seq || Known->Actor.Get() != Actor;
		FFollow& F = Followed.FindOrAdd(Pair.Key);
		if (bNew)
		{
			RestoreMarker(F);
			F = FFollow();
			F.Role = Role;
			F.Seq = Seq;
			F.Last = At;
			F.Actor = Actor;
		}
		// the grey create_sprite marker is all a fireball or a blast shows without family art: draw it ourselves, but only
		// while particles really draw (budget, materials); otherwise the marker stays, so a missile is never invisible
		if (!Life->CanDrawParticles()) RestoreMarker(F);
		else if ((Role == EDinkLifeSpriteRole::Fireball || Role == EDinkLifeSpriteRole::Burst) && !F.bMarkerHidden)
		{
			ADinkScriptSpriteActor* SA = Cast<ADinkScriptSpriteActor>(Actor);
			if (SA && SA->Marker && SA->Marker->IsVisible() && !SA->FindComponentByTag<UStaticMeshComponent>(UDinkArtFamilySubsystem::ScriptSpriteTag)
				&& !SA->FindComponentByTag<UStaticMeshComponent>(UDinkArtFamilySubsystem::ScriptEffectTag))
			{
				SA->Marker->SetVisibility(false, false);
				F.bMarkerHidden = true;
			}
		}
		const uint64 Key = (uint64(uint32(Pair.Key)) << 8) | uint64(uint8(Role)) << 1;
		switch (Role)
		{
		case EDinkLifeSpriteRole::Fire:
		{
			float H = 120.f, K = 1.f;
			Life->FireOfSequence(Seq, H, K);
			const float Ground = Life->GroundZ(At, float(At.Z));
			Life->EmitFire(Key | 1ull, FVector(At.X, At.Y, Ground), H, K, bIndoor, DeltaTime);
			break;
		}
		case EDinkLifeSpriteRole::Fireball:
		{
			const bool bIce = Seq == 163 || PSeq == 163;
			const FLinearColor Hot = bIce ? FLinearColor(0.5f, 0.75f, 1.f, 1.f) : FLinearColor(1.f, 0.42f, 0.1f, 1.f);
			FDinkLifeParticleSpec Core;
			Core.Kind = EDinkLifeParticle::Glow;
			Core.Location = At;
			Core.Life = FMath::Max(2.5f * DeltaTime, 0.03f);
			Core.SizeStart = Core.SizeEnd = 42.f;
			Core.Colour = FLinearColor(Hot.R, Hot.G, Hot.B, 1.8f);
			Core.Drag = 0.f;
			Life->Emit(Core);
			Core.SizeStart = Core.SizeEnd = 13.f;
			Core.Colour = FLinearColor(1.f, 0.85f, 0.6f, 2.2f);
			Life->Emit(Core);
			const float Step = float(FVector::Dist(At, F.Last));
			F.Trail = Step > 300.f ? 0.f : F.Trail + Step;   // a jump (teleport, reuse) never draws a trail
			const FVector From = F.Last;
			while (F.Trail >= 14.f)
			{
				F.Trail -= 14.f;
				const float U = Frand();
				FDinkLifeParticleSpec P;
				P.Kind = EDinkLifeParticle::Ember;
				P.Location = FMath::Lerp(From, At, U) + FVector((Frand() - 0.5f) * 10.f, (Frand() - 0.5f) * 10.f, (Frand() - 0.5f) * 10.f);
				P.Velocity = FVector((Frand() - 0.5f) * 30.f, (Frand() - 0.5f) * 30.f, 20.f + 30.f * Frand());
				P.Life = 0.3f + 0.4f * Frand();
				P.SizeStart = 9.f; P.SizeEnd = 2.f;
				P.Colour = FLinearColor(Hot.R, Hot.G * 0.9f, Hot.B, 3.f);
				P.Drag = 2.f; P.Gravity = -20.f;
				Life->Emit(P);
				if (!bIce && Frand() < 0.35f)
				{
					FDinkLifeParticleSpec Sm;
					Sm.Kind = EDinkLifeParticle::Smoke;
					Sm.Location = P.Location;
					Sm.Velocity = FVector(0, 0, 25.f);
					Sm.Life = 1.f + 0.6f * Frand();
					Sm.SizeStart = 14.f; Sm.SizeEnd = 60.f;
					Sm.Colour = FLinearColor(0.2f, 0.19f, 0.18f, 0.25f);
					Sm.Drag = 1.f; Sm.WindFollow = 0.4f;
					Life->Emit(Sm);
				}
			}
			Life->KeepLight(Key | 1ull, At, Hot, 140.f, 800.f, 0.2f);
			break;
		}
		case EDinkLifeSpriteRole::Missile:
		{
			// arrows and axes keep their own picture; a faint air streak behind them reads the speed
			const float Step = float(FVector::Dist(At, F.Last));
			F.Trail = Step > 300.f ? 0.f : F.Trail + Step;
			if (F.Trail >= 40.f)
			{
				F.Trail = 0.f;
				FDinkLifeParticleSpec P;
				P.Kind = EDinkLifeParticle::Spark;
				P.Location = At;
				P.Velocity = (At - F.Last).GetSafeNormal() * 400.f;
				P.Life = 0.18f;
				P.SizeStart = 5.f; P.SizeEnd = 2.f;
				P.Colour = FLinearColor(0.9f, 0.9f, 0.85f, 0.35f);
				P.Drag = 8.f;
				Life->Emit(P);
			}
			break;
		}
		case EDinkLifeSpriteRole::Burst:
			if (bNew) Burst(At, Seq == 161 || Seq == 171);
			break;
		case EDinkLifeSpriteRole::Barrel:
			// the break starts now (its first frames), not a barrel met mid-sequence on entering the screen
			if (bNew && Sprite.GetProp(TEXT("frame")) <= 2) BarrelBreak(At);
			break;
		default:
			break;
		}
		F.Last = At;
	}
	for (auto It = Followed.CreateIterator(); It; ++It)
	{
		if (!Alive.Contains(It.Key())) { RestoreMarker(It.Value()); It.RemoveCurrent(); }
	}

	// pushing: dust and grit at Dink's hands while he leans on something, more at the foot of a rock that slides
	const FDinkSprite* Dink = Director->GetSprites().Find(1);
	const APlayerController* PC = World->GetFirstPlayerController();
	const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (Dink && Pawn && Tables.PushSeqs.Contains(Dink->GetProp(C_Seq)))
	{
		PushTimer += DeltaTime;
		if (PushTimer >= 0.22f)
		{
			PushTimer = 0.f;
			const FVector P = Pawn->GetActorLocation();
			const FVector Fwd = Pawn->GetActorForwardVector().GetSafeNormal2D();
			// the thing pushed: the nearest script sprite in front of him that is moving
			FVector Foot = P + Fwd * 55.f;
			bool bSliding = false;
			for (const TPair<int32, FDinkSprite>& Pair : Director->GetSprites())
			{
				const FDinkSprite& S = Pair.Value;
				const AActor* A = S.Actor.Get();
				if (Pair.Key == 1 || !A || !S.bMoving || (S.Screen > 0 && S.Screen != Screen)) continue;
				const FVector L = A->GetActorLocation();
				if (FVector::DistSquared2D(L, P) < FMath::Square(220.0) && FVector::DotProduct((L - P).GetSafeNormal2D(), Fwd) > 0.3)
				{
					Foot = L;
					bSliding = true;
					break;
				}
			}
			const float Z = Life->GroundZ(Foot, float(P.Z) - 90.f);
			for (int32 I = 0; I < (bSliding ? 3 : 1); ++I)
			{
				FDinkLifeParticleSpec S;
				S.Kind = EDinkLifeParticle::Dust;
				S.Location = FVector(Foot.X + (Frand() - 0.5f) * 60.f, Foot.Y + (Frand() - 0.5f) * 60.f, Z + 5.f);
				S.Velocity = FVector((Frand() - 0.5f) * 60.f, (Frand() - 0.5f) * 60.f, 15.f + 20.f * Frand()) - FVector(Fwd * 25.f);
				S.Life = 1.2f + 0.6f * Frand();
				S.SizeStart = 20.f; S.SizeEnd = bSliding ? 110.f : 60.f;
				S.Colour = FLinearColor(0.5f, 0.45f, 0.38f, bSliding ? 0.38f : 0.2f);
				S.Drag = 2.f; S.Gravity = -4.f; S.WindFollow = 0.3f;
				Life->Emit(S);
				if (bSliding)
				{
					FDinkLifeParticleSpec G;
					G.Kind = EDinkLifeParticle::Debris;
					G.Location = FVector(Foot.X, Foot.Y, Z + 8.f);
					G.Velocity = FVector((Frand() - 0.5f) * 120.f, (Frand() - 0.5f) * 120.f, 80.f + 80.f * Frand());
					G.Life = 2.f + Frand();
					G.SizeStart = G.SizeEnd = 2.5f + 2.5f * Frand();
					G.Colour = FLinearColor(0.32f, 0.3f, 0.27f, 1.f);
					G.Drag = 0.5f; G.Gravity = 900.f; G.FloorZ = Z;
					Life->Emit(G);
				}
			}
		}
	}
	else
	{
		PushTimer = 0.f;
	}
}

// Review only (captures): the presenter's effects ahead of Dink, without any sprite. Nothing in the simulation changes.
static FAutoConsoleCommandWithWorldAndArgs GDinkWorldDemo(
	TEXT("dink.World.Demo"),
	TEXT("dink.World.Demo <burst|bigburst|barrel|fire|bigfire|fireball|dust> [cm ahead=180]: review-only world-life effect ahead of Dink (captures)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UDinkWorldLifePresenter* Presenter = World ? World->GetSubsystem<UDinkWorldLifePresenter>() : nullptr;
		UDinkWorldLifeSubsystem* Life = World ? World->GetSubsystem<UDinkWorldLifeSubsystem>() : nullptr;
		const APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
		if (!Presenter || !Life || !Life->IsActive() || !Pawn || Args.Num() < 1)
		{
			UE_LOG(LogDink, Display, TEXT("dink.World.Demo: needs a rendering game with dink.World.Life 1, a player and a kind"));
			return;
		}
		const float Ahead = Args.Num() > 1 ? FCString::Atof(*Args[1]) : 180.f;
		const FVector P = Pawn->GetActorLocation() + Pawn->GetActorForwardVector().GetSafeNormal2D() * Ahead;
		Presenter->Demo(Args[0], FVector(P.X, P.Y, Life->GroundZ(P, float(P.Z) - 90.f)));
		UE_LOG(LogDink, Display, TEXT("dink.World.Demo %s at %s"), *Args[0], *P.ToCompactString());
	}));

void UDinkWorldLifePresenter::Demo(const FString& Kind, const FVector& Ground)
{
	UDinkWorldLifeSubsystem* Life = GetWorld() ? GetWorld()->GetSubsystem<UDinkWorldLifeSubsystem>() : nullptr;
	if (!Life) return;
	if (Kind == TEXT("burst") || Kind == TEXT("bigburst")) Burst(Ground + FVector(0, 0, 60), Kind == TEXT("bigburst"));
	else if (Kind == TEXT("barrel")) BarrelBreak(Ground);
	else if (Kind == TEXT("fire") || Kind == TEXT("bigfire"))
	{
		const bool bBig = Kind == TEXT("bigfire");
		DemoFire.Add(FDemoFire{ Ground, bBig ? 420.f : 90.f, bBig ? 2.6f : 1.f, float(GetWorld()->GetTimeSeconds()) + 12.f });
	}
	else if (Kind == TEXT("fireball"))
	{
		DemoBall = FDemoBall{ Ground + FVector(-300, 0, 60), Ground + FVector(300, 0, 60), float(GetWorld()->GetTimeSeconds()), 1.2f };
		bDemoBall = true;
	}
	else if (Kind == TEXT("dust"))
	{
		for (int32 I = 0; I < 6; ++I)
		{
			FDinkLifeParticleSpec S;
			S.Kind = EDinkLifeParticle::Dust;
			S.Location = Ground + FVector((Frand() - 0.5f) * 60.f, (Frand() - 0.5f) * 60.f, 5.f);
			S.Velocity = FVector((Frand() - 0.5f) * 60.f, (Frand() - 0.5f) * 60.f, 25.f);
			S.Life = 1.4f; S.SizeStart = 20.f; S.SizeEnd = 90.f;
			S.Colour = FLinearColor(0.5f, 0.44f, 0.36f, 0.35f);
			S.Drag = 2.f; S.WindFollow = 0.3f;
			Life->Emit(S);
		}
	}
}

void UDinkWorldLifePresenter::TickDemos(float DeltaTime)
{
	UDinkWorldLifeSubsystem* Life = GetWorld()->GetSubsystem<UDinkWorldLifeSubsystem>();
	const float Now = GetWorld()->GetTimeSeconds();
	for (int32 I = DemoFire.Num() - 1; I >= 0; --I)
	{
		if (Now > DemoFire[I].Until) { DemoFire.RemoveAtSwap(I); continue; }
		Life->EmitFire(0xD3D0000ull + uint64(I) * 2ull + 1ull, DemoFire[I].Base, DemoFire[I].Height, DemoFire[I].Scale, false, DeltaTime);
	}
	if (bDemoBall)
	{
		const float T = (Now - DemoBall.Start) / DemoBall.Seconds;
		if (T >= 1.f) { bDemoBall = false; Burst(DemoBall.To, false); return; }
		const FVector At = FMath::Lerp(DemoBall.From, DemoBall.To, T);
		FDinkLifeParticleSpec Core;
		Core.Kind = EDinkLifeParticle::Glow;
		Core.Location = At; Core.Life = FMath::Max(2.5f * DeltaTime, 0.03f);
		Core.SizeStart = Core.SizeEnd = 42.f; Core.Colour = FLinearColor(1.f, 0.42f, 0.1f, 1.8f); Core.Drag = 0.f;
		Life->Emit(Core);
		for (int32 K = 0; K < 3; ++K)
		{
			FDinkLifeParticleSpec P;
			P.Kind = EDinkLifeParticle::Ember;
			P.Location = At - (DemoBall.To - DemoBall.From).GetSafeNormal() * (Frand() * 30.f);
			P.Velocity = FVector((Frand() - 0.5f) * 30.f, (Frand() - 0.5f) * 30.f, 30.f);
			P.Life = 0.5f; P.SizeStart = 9.f; P.SizeEnd = 2.f; P.Colour = FLinearColor(1.f, 0.45f, 0.12f, 3.f); P.Drag = 2.f; P.Gravity = -20.f;
			Life->Emit(P);
		}
		Life->KeepLight(0xD3D1001ull, At, FLinearColor(1.f, 0.5f, 0.15f), 140.f, 800.f, 0.2f);
	}
}
