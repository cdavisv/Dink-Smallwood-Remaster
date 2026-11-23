#include "DinkCorpsePresenter.h"
#include "DinkEnvironmentSubsystem.h"
#include "DinkCollision.h"
#include "DinkCreatureClass.h"
#include "DinkCreatureClassComponent.h"
#include "DinkCreatureComponent.h"
#include "DinkCreatureSubsystem.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "ImageUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

static TAutoConsoleVariable<int32> CVarCorpseExplosionCards(TEXT("dink.CorpseExplosionCards"), 0,
	TEXT("1: the corpse presenter also lays its own card for a kill burst (164). 0 (default): the simulation's brain-7 burst sprite is drawn by the placed-effect layer (add_kill_sprite, dink.cpp:12385-12419)."));
static TAutoConsoleVariable<int32> CVarDinkCorpseCards(TEXT("dink.CorpseCards"), 1,
	TEXT("1 (default): a killed sprite that no creature class draws leaves its 1997 death picture on a card until the screen changes, or plays the explosion 164 (add_kill_sprite, dink.cpp:12359). 0: off."));
static TAutoConsoleVariable<int32> CVarDinkDeathFall(TEXT("dink.DeathFall"), 1,
	TEXT("1 (default): when Dink dies (dinfo.c sp_seq(1, 436)) his body falls as a ragdoll in a blood pool and lies until a load or restart. 0: he stands, as before."));

namespace
{
	const FName K_Seq(TEXT("seq")), K_PSeq(TEXT("pseq"));
	const FName K_BaseDeath(TEXT("base_death")), K_BaseWalk(TEXT("base_walk")), K_Hitpoints(TEXT("hitpoints")), K_Brain(TEXT("brain")),
		K_Size(TEXT("size"));
	const TCHAR* CardMeshPath = TEXT("/Game/Dink/_Generated/Shared/SM_DinkCard.SM_DinkCard");
	const TCHAR* CardMaterialPath = TEXT("/Game/Dink/_Generated/Shared/M_DinkSprite.M_DinkSprite");
	const TCHAR* DeathPoolMaterialPath = TEXT("/Game/Dink/Photoreal/Props/MI_Decal_BloodSplat_0.MI_Decal_BloodSplat_0");
	FString PictureDir() { return FPaths::ProjectContentDir() / TEXT("Dink/Data/Sprites/Death"); }

	template <typename T>
	T* LoadIfPresent(const TCHAR* Path)
	{
		const FString P(Path);
		return FPackageName::DoesPackageExist(P.Left(P.Find(TEXT(".")))) ? LoadObject<T>(nullptr, Path, nullptr, LOAD_NoWarn | LOAD_Quiet) : nullptr;
	}
}

bool UDinkCorpsePresenter::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

TStatId UDinkCorpsePresenter::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UDinkCorpsePresenter, STATGROUP_Tickables);
}

void UDinkCorpsePresenter::Deinitialize()
{
	Clear();
	Super::Deinitialize();
}

void UDinkCorpsePresenter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (!FApp::CanEverRender()) return;
	// two switches: the fall does not depend on the corpse cards
	UpdateDinkDeath();
	if (CVarDinkCorpseCards.GetValueOnGameThread() != 0) Present(DeltaTime);
	else Suppress();
}

void UDinkCorpsePresenter::Suppress()
{
	// the off switch: every card goes (explosions too); what was seen alive is forgotten, so a kill made while it is off
	// leaves nothing when the switch comes back
	Clear();
	Seen.Reset();
}

FVector2D UDinkCorpsePresenter::CardFootPx(double X, double Y, int32 WidthPx, int32 HeightPx, int32 OriginX, int32 OriginY, int32 SizePercent)
{
	// 1997 draws the picture with its registration point (dink.ini xoffset/yoffset) on the sprite's point, scaled with the sprite's
	// size (get_box, D:3164-3260); the card stands on the middle of the picture's bottom row
	const double S = double(SizePercent > 0 ? SizePercent : 100) / 100.0;
	return FVector2D(X + (0.5 * WidthPx - OriginX) * S, Y + (double(HeightPx) - OriginY) * S);
}

int32 UDinkCorpsePresenter::DeathSequence(int32 BaseDeath, int32 BaseWalk, int32 Dir, TFunctionRef<bool(int32)> HasPicture)
{
	int32 Base = BaseDeath;
	if (Base == -1)
	{
		// no death base: base_walk + 5 if that sequence exists, else the explosion 164 (D:12369-12385)
		return BaseWalk > 0 && HasPicture(BaseWalk + 5) ? BaseWalk + 5 : Explosion;
	}
	if (Base <= 0) return 0;
	if (Dir < 1 || Dir > 9) Dir = 3; // D:12361-12365
	if (!HasPicture(Base + Dir))
	{
		// the engine's mirrored facing (D:12392-12404)
		static const int32 Mirror[10] = {0, 9, 8, 7, 6, 5, 4, 3, 2, 1};
		Dir = Mirror[Dir];
	}
	return HasPicture(Base + Dir) ? Base + Dir : 0;
}

FVector2D UDinkCorpsePresenter::CardSizeCm(int32 WidthPx, int32 HeightPx, int32 SizePercent)
{
	const double S = 2.5 * double(SizePercent > 0 ? SizePercent : 100) / 100.0;
	return FVector2D(WidthPx * S, HeightPx * S);
}

void UDinkCorpsePresenter::LoadPictures()
{
	bLoaded = true;
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!FFileHelper::LoadFileToString(Text, *(PictureDir() / TEXT("death_pictures.json")))
		|| !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid()) return;
	const TSharedPtr<FJsonObject>* Table = nullptr;
	if (Root->TryGetObjectField(TEXT("pictures"), Table) && Table)
	{
		for (const auto& Pair : (*Table)->Values)
		{
			const TSharedPtr<FJsonObject>* Row = nullptr;
			if (!Pair.Value->TryGetObject(Row) || !Row) continue;
			FPicture P;
			P.Width = (*Row)->GetIntegerField(TEXT("width"));
			P.Height = (*Row)->GetIntegerField(TEXT("height"));
			P.OriginX = (*Row)->GetIntegerField(TEXT("origin_x"));
			P.OriginY = (*Row)->GetIntegerField(TEXT("origin_y"));
			Pictures.Add(FCString::Atoi(*FString(Pair.Key.ToView())), P);
		}
	}
	const TSharedPtr<FJsonObject>* Anims = nullptr;
	if (Root->TryGetObjectField(TEXT("animations"), Anims) && Anims)
	{
		for (const auto& Pair : (*Anims)->Values)
		{
			const TSharedPtr<FJsonObject>* Row = nullptr;
			const TArray<TSharedPtr<FJsonValue>>* Frames = nullptr;
			if (!Pair.Value->TryGetObject(Row) || !Row || !(*Row)->TryGetArrayField(TEXT("frames"), Frames) || !Frames) continue;
			const FString Key(Pair.Key.ToView());
			TArray<FFrame>& Out = Animations.Add(FCString::Atoi(*Key));
			for (const TSharedPtr<FJsonValue>& V : *Frames)
			{
				const TSharedPtr<FJsonObject>* F = nullptr;
				if (!V->TryGetObject(F) || !F) continue;
				FFrame Frame;
				Frame.Width = (*F)->GetIntegerField(TEXT("width"));
				Frame.Height = (*F)->GetIntegerField(TEXT("height"));
				Frame.DelayMs = FMath::Max(1, (int32)(*F)->GetIntegerField(TEXT("delay_ms")));
				Frame.Texture = LoadTexture(PictureDir() / FString::Printf(TEXT("%s_%02d.png"), *Key, (int32)(*F)->GetIntegerField(TEXT("frame"))));
				if (Frame.Texture) Out.Add(Frame);
			}
			if (Out.IsEmpty()) Animations.Remove(FCString::Atoi(*Key));
		}
	}
	CardMesh = LoadIfPresent<UStaticMesh>(CardMeshPath);
	CardMaterial = LoadIfPresent<UMaterialInterface>(CardMaterialPath);
}

UTexture2D* UDinkCorpsePresenter::LoadTexture(const FString& File)
{
	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *File)) return nullptr;
	UTexture2D* T = FImageUtils::ImportBufferAsTexture2D(Bytes);
	if (!T) return nullptr;
	T->Filter = TF_Nearest; // the 1997 pixels, as the greybox's sprite cards
	T->UpdateResource();
	Textures.Add(T);
	return T;
}

UTexture2D* UDinkCorpsePresenter::TextureFor(int32 Sequence)
{
	FPicture* P = Pictures.Find(Sequence);
	if (!P) return nullptr;
	if (!P->Texture) P->Texture = LoadTexture(PictureDir() / FString::Printf(TEXT("%d.png"), Sequence));
	return P->Texture;
}

void UDinkCorpsePresenter::Clear()
{
	for (UStaticMeshComponent* C : Cards) if (C) C->DestroyComponent();
	Cards.Reset();
	Playing.Reset();
}

void UDinkCorpsePresenter::EnsureHolder()
{
	if (Holder) return;
	UWorld* World = GetWorld();
	if (!World) return;
	FActorSpawnParameters SP;
	SP.ObjectFlags |= RF_Transient;
	Holder = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, SP);
	if (!Holder) return;
	USceneComponent* Root = NewObject<USceneComponent>(Holder, TEXT("Root"));
	Holder->SetRootComponent(Root);
	Root->RegisterComponent();
}

UStaticMeshComponent* UDinkCorpsePresenter::LeaveCard(UTexture2D* Texture, FVector2D SizeCm, int32 Screen, double X, double Y, const AActor* Ignore,
	UMaterialInstanceDynamic** OutMaterial)
{
	UWorld* World = GetWorld();
	const UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
	const UDinkStorySubsystem* Story = Instance ? Instance->GetSubsystem<UDinkStorySubsystem>() : nullptr;
	const UDinkDirector* Director = Story ? Story->GetDirector() : nullptr;
	FVector At;
	if (!Director || !Texture || !CardMesh || !CardMaterial || !Director->PixelToWorld(Screen, X, Y, At)) return nullptr;
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkCorpseCard), false);
	if (Ignore) Params.AddIgnoredActor(Ignore);
	if (const APlayerController* PC = Instance->GetFirstLocalPlayerController()) if (const APawn* Pawn = PC->GetPawn()) Params.AddIgnoredActor(Pawn);
	// the ground under the screen point: start just above it, so a tree's crown overhead is not taken for the ground
	if (World->LineTraceSingleByObjectType(Hit, At + FVector(0, 0, 100), At - FVector(0, 0, 400), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
		At.Z = Hit.ImpactPoint.Z;
	EnsureHolder();
	if (!Holder) return nullptr;
	UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(CardMaterial, Holder);
	M->SetTextureParameterValue(TEXT("Tex"), Texture);
	UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(Holder);
	C->SetupAttachment(Holder->GetRootComponent());
	C->SetStaticMesh(CardMesh);
	C->SetMaterial(0, M);
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	C->SetGenerateOverlapEvents(false);
	C->SetCanEverAffectNavigation(false);
	C->SetCastShadow(false);
	// the quad is 100 x 100 cm, bottom edge on its pivot: the card stands on the sprite's ground point with its foot on the
	// ground, so no part of the body sinks out of sight (the caller puts that point under the middle of the picture's bottom row)
	C->SetWorldScale3D(FVector(SizeCm.X / 100.0, 1.0, SizeCm.Y / 100.0));
	C->SetWorldLocation(At);
	C->RegisterComponent();
	Cards.Add(C);
	if (OutMaterial) *OutMaterial = M;
	return C;
}

bool UDinkCorpsePresenter::CreatureDrawsCorpse(const AActor* Actor, int32 BaseDeath, int32 KillDir, int32 BaseWalk) const
{
	// an origin row draws its creature's death itself; a creature class draws the corpses it has art for (its corpse rows)
	// (the same lookup as UDinkCreaturePresenter's LeaveCorpse: with base_death -1 the row of base_walk + 5, e.g. the slayer's 645)
	if (!Actor) return false;
	if (Actor->FindComponentByClass<UDinkCreatureComponent>()) return true;
	const UDinkCreatureClassComponent* Body = Actor->FindComponentByClass<UDinkCreatureClassComponent>();
	if (!Body) return false;
	const UDinkCreatureSubsystem* Creatures = GetWorld() ? GetWorld()->GetSubsystem<UDinkCreatureSubsystem>() : nullptr;
	const FDinkCreatureClassBinding* Binding = Creatures ? Creatures->GetClassBindings().FindByPredicate(
		[Body](const FDinkCreatureClassBinding& B) { return B.ClassId == Body->GetClassId(); }) : nullptr;
	return Binding && Binding->CorpseFor(BaseDeath, KillDir, BaseWalk);
}

int32 UDinkCorpsePresenter::Present(float DeltaTime)
{
	UWorld* World = GetWorld();
	const UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
	const UDinkStorySubsystem* Story = Instance ? Instance->GetSubsystem<UDinkStorySubsystem>() : nullptr;
	const UDinkDirector* Director = Story ? Story->GetDirector() : nullptr;
	if (!Director) return 0;
	if (!bLoaded) LoadPictures();
	if (Pictures.IsEmpty()) return 0;

	const int32 Screen = Director->GetCurrentScreen();
	const int32 ResetSerial = Director->GetSpriteResetSerial();
	if (Screen != SeenScreen || ResetSerial != SeenResetSerial)
	{
		// the original redraws the background: its corpses go with the screen, and the old screen's sprites did not die
		SeenScreen = Screen;
		SeenResetSerial = ResetSerial;
		Seen.Reset();
		Clear();
	}

	int32 Made = 0;
	TSet<int32, DefaultKeyFuncs<int32>, TInlineSetAllocator<64>> Alive;
	for (const TPair<int32, FDinkSprite>& Pair : Director->GetSprites())
	{
		const FDinkSprite& S = Pair.Value;
		if (Pair.Key == 1 || S.bText || (S.Screen > 0 && S.Screen != Screen)) continue;
		const int32 Brain = S.GetProp(K_Brain);
		const int32 Hp = S.GetProp(K_Hitpoints);
		if (S.bActive)
		{
			if ((Brain == 9 || Brain == 10 || Brain == 16) && Hp >= 1)
			{
				// decided while it lives: a script-made sprite's actor is destroyed before its kill is seen here
				const bool bDraws = CreatureDrawsCorpse(S.Actor.Get(), S.GetProp(K_BaseDeath, -1), DinkCreatureClass::KillDir(Brain, S.Dir),
					S.GetProp(K_BaseWalk, 0));
				FSeen& Entry = Seen.FindOrAdd(Pair.Key);
				Entry.Brain = Brain;
				Entry.Hitpoints = Hp;
				Entry.bCreatureDraws = bDraws;
				Alive.Add(Pair.Key);
			}
			continue;
		}
		const FSeen* Last = Seen.Find(Pair.Key);
		if (!Last) continue;
		// UDinkGameplay::ProcessDamage's kill: the hit points ran out and add_kill_sprite removed the sprite (pill_brain D:12901-12910,
		// people_brain 13099-13109 after brain 0, dragon_brain 13248-13255), whatever the blow count. The last reading may be older than the
		// kill: a goblin made with brain 16 that a single blow kills never ran its `hit` (which makes it brain 9), so the brain may differ
		// from the last reading; any monster or people brain (or 0, people_brain's) counts. Anything else that removes a sprite (sp_active 0,
		// a script's kill with hit points left) leaves nothing, as in 1997.
		const bool bKilled = Hp < 1 && (Brain == 0 || Brain == 9 || Brain == 10 || Brain == 16);
		const FSeen Was = *Last;
		Seen.Remove(Pair.Key);
		if (!bKilled || Was.bCreatureDraws) continue;
		const AActor* Actor = S.Actor.Get();
		const int32 KillDir = DinkCreatureClass::KillDir(Was.Brain, S.Dir);
		const int32 Size = S.GetProp(K_Size, 100);
		const int32 Seq = DeathSequence(S.GetProp(K_BaseDeath, -1), S.GetProp(K_BaseWalk, -1), KillDir,
			[this](int32 Q) { return Q == Explosion ? Animations.Contains(Q) : Pictures.Contains(Q); });
		if (Seq == Explosion && CVarCorpseExplosionCards.GetValueOnGameThread() == 0)
		{
			// The simulation makes the burst itself since 16 Nov 2026 (UDinkGameplay::AddKillSprite: a brain-7 sprite showing 164, as
			// add_kill_sprite does, D:12385-12419); the placed-effect layer draws that sprite. No second card here.
			continue;
		}
		if (Seq == Explosion)
		{
			// brain 7: the frames once, then nothing (D:12384-12385, 12416)
			const TArray<FFrame>* Frames = Animations.Find(Explosion);
			UMaterialInstanceDynamic* M = nullptr;
			UStaticMeshComponent* C = Frames && Frames->Num() > 0
				? LeaveCard((*Frames)[0].Texture, CardSizeCm((*Frames)[0].Width, (*Frames)[0].Height, Size), Screen, S.X, S.Y, Actor, &M) : nullptr;
			if (C)
			{
				FPlay P;
				P.Card = C;
				P.Material = M;
				P.Sequence = Explosion;
				P.SizePercent = Size;
				Playing.Add(P);
				++Made;
				UE_LOG(LogTemp, Display, TEXT("DINK CORPSE CARD: sprite %d explosion %d on screen %d"), Pair.Key, Seq, Screen);
			}
		}
		else if (Seq > 0)
		{
			const FPicture& P = Pictures.FindChecked(Seq);
			const FVector2D Foot = CardFootPx(S.X, S.Y, P.Width, P.Height, P.OriginX, P.OriginY, Size);
			if (LeaveCard(TextureFor(Seq), CardSizeCm(P.Width, P.Height, Size), Screen, Foot.X, Foot.Y, Actor))
			{
				++Made;
				UE_LOG(LogTemp, Display, TEXT("DINK CORPSE CARD: sprite %d picture %d on screen %d"), Pair.Key, Seq, Screen);
			}
		}
	}
	for (auto It = Seen.CreateIterator(); It; ++It) if (!Alive.Contains(It.Key()) && !Director->FindSprite(It.Key())) It.RemoveCurrent();

	// play the explosions: each frame for its dink.ini delay, then the card goes
	for (int32 I = Playing.Num() - 1; I >= 0; --I)
	{
		FPlay& P = Playing[I];
		P.AgeS += DeltaTime;
		const TArray<FFrame>* Frames = Animations.Find(P.Sequence);
		UStaticMeshComponent* C = P.Card.Get();
		double T = 0.0;
		int32 Frame = INDEX_NONE;
		for (int32 F = 0; Frames && F < Frames->Num(); ++F)
		{
			T += (*Frames)[F].DelayMs / 1000.0;
			if (P.AgeS < T) { Frame = F; break; }
		}
		if (!C || Frame == INDEX_NONE)
		{
			if (C) { Cards.Remove(C); C->DestroyComponent(); }
			Playing.RemoveAt(I);
			continue;
		}
		const FFrame& Fr = (*Frames)[Frame];
		if (UMaterialInstanceDynamic* M = P.Material.Get()) M->SetTextureParameterValue(TEXT("Tex"), Fr.Texture);
		const FVector2D Sz = CardSizeCm(Fr.Width, Fr.Height, P.SizePercent);
		C->SetWorldScale3D(FVector(Sz.X / 100.0, 1.0, Sz.Y / 100.0));
	}

	// stand the cards towards the camera, as the greybox turns its sprite cards
	if (!Cards.IsEmpty())
	{
		const APlayerController* PC = Instance->GetFirstLocalPlayerController();
		if (PC && PC->PlayerCameraManager)
		{
			const FVector Eye = PC->PlayerCameraManager->GetCameraLocation();
			for (UStaticMeshComponent* C : Cards)
			{
				if (!C) continue;
				const FVector To = Eye - C->GetComponentLocation();
				C->SetWorldRotation(FRotator(0.0, FMath::RadiansToDegrees(FMath::Atan2(To.Y, To.X)) - 90.0, 0.0));
			}
		}
	}
	return Made;
}

void UDinkCorpsePresenter::LayDownKinematic(USkeletalMeshComponent& Mesh, UCapsuleComponent& Capsule)
{
	if (Mesh.IsSimulatingPhysics())
	{
		Mesh.SetAllBodiesSimulatePhysics(false);
		Mesh.SetSimulatePhysics(false);
		Mesh.bBlendPhysics = false;
		Mesh.AttachToComponent(&Capsule, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
	}
	// face down along his facing, feet where he stood (the last picture of sequence 436), a few cm above the ground
	FTransform Lying = LivingMeshRelative;
	Lying.SetRotation(LivingMeshRelative.GetRotation() * FRotator(0.0, 0.0, -90.0).Quaternion());
	Lying.SetLocation(LivingMeshRelative.GetLocation() + FVector(0.0, 0.0, 12.0));
	Mesh.SetRelativeTransform(Lying);
	bDinkKinematic = true;
}

void UDinkCorpsePresenter::UpdateDinkDeath()
{
	UWorld* World = GetWorld();
	const UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
	const UDinkStorySubsystem* Story = Instance ? Instance->GetSubsystem<UDinkStorySubsystem>() : nullptr;
	const UDinkDirector* Director = Story ? Story->GetDirector() : nullptr;
	const FDinkSprite* Dink = Director ? Director->FindSprite(1) : nullptr;
	ACharacter* Hero = Dink ? Cast<ACharacter>(Dink->Actor.Get()) : nullptr;
	USkeletalMeshComponent* Mesh = Hero ? Hero->GetMesh() : nullptr;
	UCapsuleComponent* Capsule = Hero ? Hero->GetCapsuleComponent() : nullptr;
	const bool bDead = Dink && Mesh && Capsule && IsDinkDeathPicture(Dink->GetProp(K_Seq), Dink->GetProp(K_PSeq))
		&& CVarDinkDeathFall.GetValueOnGameThread() != 0;

	if (bDead && bDinkFallen && Mesh->IsSimulatingPhysics())
	{
		// a body thrown far off or sunk through ground that does not hold physics bodies is laid down at the feet instead
		const FVector Feet = Hero->GetActorLocation() - FVector(0.0, 0.0, Capsule->GetScaledCapsuleHalfHeight());
		const FVector Centre = Mesh->Bounds.Origin;
		if (FVector::Dist2D(Centre, Feet) > DeathBodyMaxDriftCm || Centre.Z < Feet.Z - 40.0) LayDownKinematic(*Mesh, *Capsule);
	}
	if (bDead && !bDinkFallen)
	{
		bDinkFallen = true;
		bDinkKinematic = false;
		FallenMesh = Mesh;
		LivingMeshRelative = Mesh->GetRelativeTransform();
		LivingMeshProfile = Mesh->GetCollisionProfileName();
		LivingCapsulePhysicsResponse = Capsule->GetCollisionResponseToChannel(ECC_PhysicsBody);
		if (Mesh->GetPhysicsAsset())
		{
			Capsule->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Ignore);
			Mesh->SetCollisionProfileName(TEXT("Ragdoll"));
			// only the world holds him: creatures, people, other bodies and missiles pass (a pillbug inside him flung the body away)
			Mesh->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
			Mesh->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Ignore);
			Mesh->SetCollisionResponseToChannel(ECC_Vehicle, ECR_Ignore);
			Mesh->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
			Mesh->SetCollisionResponseToChannel(DinkCollision::Projectile, ECR_Ignore);
			Mesh->SetAllBodiesSimulatePhysics(true);
			Mesh->SetSimulatePhysics(true);
			Mesh->WakeAllRigidBodies();
			Mesh->bBlendPhysics = true;
		}
		else
		{
			LayDownKinematic(*Mesh, *Capsule);
		}
		if (UMaterialInterface* Blood = LoadIfPresent<UMaterialInterface>(DeathPoolMaterialPath))
		{
			EnsureHolder();
			const FVector Feet = Hero->GetActorLocation() - FVector(0.0, 0.0, Capsule->GetScaledCapsuleHalfHeight());
			// not attached to the hero: it stays where he fell while a load moves the capsule
			DeathPool = NewObject<UDecalComponent>(Holder ? static_cast<UObject*>(Holder.Get()) : static_cast<UObject*>(this));
			DeathPool->SetDecalMaterial(Blood);
			DeathPool->DecalSize = FVector(60.0, DeathPoolSizeCm * 0.5, DeathPoolSizeCm * 0.5);
			DeathPool->SetUsingAbsoluteLocation(true);
			DeathPool->SetUsingAbsoluteRotation(true);
			DeathPool->SetWorldLocationAndRotation(Feet, FRotator(-90.0, Hero->GetActorRotation().Yaw, 0.0));
			// the pool spreads after he has fallen (the blood appears in the last frames of 436)
			DeathPool->SetFadeIn(1.0f, 1.6f);
			DeathPool->RegisterComponent();
			UDinkEnvironmentSubsystem::OpenGrassUnder(DeathPool);
		}
		UE_LOG(LogTemp, Display, TEXT("DINK DEATH: the hero falls (sprite picture 436): %s, blood pool %s"),
			Mesh->GetPhysicsAsset() ? TEXT("ragdoll") : TEXT("laid down"), DeathPool ? TEXT("spawned") : TEXT("missing"));
		return;
	}
	if (!bDead && bDinkFallen)
	{
		// alive again (a load or a restart), or the switch turned off: stand him up where the capsule is
		bDinkFallen = false;
		bDinkKinematic = false;
		USkeletalMeshComponent* M = FallenMesh.Get();
		const ACharacter* Owner = M ? Cast<ACharacter>(M->GetOwner()) : nullptr;
		if (M && Owner && Owner->GetCapsuleComponent())
		{
			M->SetAllBodiesSimulatePhysics(false);
			M->SetSimulatePhysics(false);
			M->bBlendPhysics = false;
			M->SetCollisionProfileName(LivingMeshProfile);
			M->AttachToComponent(Owner->GetCapsuleComponent(), FAttachmentTransformRules::SnapToTargetNotIncludingScale);
			M->SetRelativeTransform(LivingMeshRelative);
			Owner->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_PhysicsBody, LivingCapsulePhysicsResponse);
		}
		FallenMesh.Reset();
		if (DeathPool)
		{
			DeathPool->DestroyComponent();
			DeathPool = nullptr;
		}
		UE_LOG(LogTemp, Display, TEXT("DINK DEATH: the hero stands again"));
	}
}
