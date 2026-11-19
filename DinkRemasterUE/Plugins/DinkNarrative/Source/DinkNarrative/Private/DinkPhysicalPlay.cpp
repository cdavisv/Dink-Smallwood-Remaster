// Physical play layer (doc/remaster/PHYSICAL_PLAY_LAYER.md; bug A70, owner confirmed 16 Nov 2026). In play, what Dink himself
// touches follows what is drawn: his collision drops the 1997 sprite hardboxes listed as relaxed (their drawn mesh keeps PR #129's
// player-only blocker), his touches use the drawn geometry (the existing authored-geometry tests of DinkAuthoredInteraction.cpp), and
// living creatures carry a player-only body box (A21). Blows at drawn contact (parts Hits, CreatureReach) exist but are off by default.
// WHAT a hit or touch does is the 1997 path unchanged (RunThroughTagList / RunThroughTouchDamageList,
// dink.cpp:15460-15527, 15629-15651): same damage formula, same rand() draws, same procedures. NPCs, creatures, missiles, brains and
// get_hard keep the 1997 boxes. Off under automation (the probe and the parity tests), so the probe traces do not move.

#include "DinkGameplay.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "DinkNarrativeTypes.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "DinkCollision.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	TAutoConsoleVariable<int32> CVarDinkPhysicalPlay(TEXT("dink.PhysicalPlay"), -1,
		TEXT("Physical play layer: Dink's collision, hits and touches follow the drawn shapes. -1 the ini's Mode (default 1), 0 off, ")
		TEXT("1 auto (on in a rendering game that is not an automation test), 2 on. The probe and parity tests run with it off."));
	// The layer's parts (FDinkPhysicalPlaySettings): -1 the ini's value, 0 off, 1 on. Inert while dink.PhysicalPlay is off.
	TAutoConsoleVariable<int32> CVarDinkPhysicalPlayCollision(TEXT("dink.PhysicalPlay.Collision"), -1,
		TEXT("Physical play part: relaxed hardboxes, Dink walks up to the drawn object. -1 the ini (default on), 0 off, 1 on."));
	TAutoConsoleVariable<int32> CVarDinkPhysicalPlayTouch(TEXT("dink.PhysicalPlay.Touch"), -1,
		TEXT("Physical play part: pickups and touch scripts at the drawn item. -1 the ini (default on), 0 off, 1 on."));
	TAutoConsoleVariable<int32> CVarDinkPhysicalPlayBodies(TEXT("dink.PhysicalPlay.Bodies"), -1,
		TEXT("Physical play part: player-only body box on living creatures (A21). -1 the ini (default on), 0 off, 1 on."));
	TAutoConsoleVariable<int32> CVarDinkPhysicalPlayHits(TEXT("dink.PhysicalPlay.Hits"), -1,
		TEXT("Physical play part: Dink's blows land at drawn contact. -1 the ini (default OFF: the 1997 hit box), 0 off, 1 on."));
	TAutoConsoleVariable<int32> CVarDinkPhysicalPlayCreatureReach(TEXT("dink.PhysicalPlay.CreatureReach"), -1,
		TEXT("Physical play part: creature blows at Dink by their drawn reach. -1 the ini (default OFF: the 1997 hit box), 0 off, 1 on."));
}

FString FDinkPhysicalPlaySettings::DefaultIniPath() { return FPaths::ProjectContentDir() / TEXT("Dink/Data/Play/physical_play.ini"); }
FString FDinkPhysicalPlaySettings::DefaultRelaxedPath() { return FPaths::ProjectContentDir() / TEXT("Dink/Data/Play/relaxed_hardboxes.json"); }

void FDinkPhysicalPlaySettings::Load()
{
	FString Text;
	if (FFileHelper::LoadFileToString(Text, *DefaultIniPath()))
	{
		TArray<FString> Lines;
		Text.ParseIntoArrayLines(Lines);
		for (FString Line : Lines)
		{
			Line.TrimStartAndEndInline();
			FString Key, Value;
			if (Line.IsEmpty() || Line.StartsWith(TEXT(";")) || Line.StartsWith(TEXT("[")) || !Line.Split(TEXT("="), &Key, &Value)) continue;
			Key.TrimStartAndEndInline();
			Value.TrimStartAndEndInline();
			if (Key == TEXT("Mode")) Mode = FMath::Clamp(FCString::Atoi(*Value), 0, 2);
			else if (Key == TEXT("Collision")) bCollision = FCString::Atoi(*Value) != 0;
			else if (Key == TEXT("Touch")) bTouch = FCString::Atoi(*Value) != 0;
			else if (Key == TEXT("Bodies")) bBodies = FCString::Atoi(*Value) != 0;
			else if (Key == TEXT("Hits")) bHits = FCString::Atoi(*Value) != 0;
			else if (Key == TEXT("CreatureReach")) bCreatureReach = FCString::Atoi(*Value) != 0;
		}
		Source = DefaultIniPath();
	}
	FString Json;
	if (FFileHelper::LoadFileToString(Json, *DefaultRelaxedPath()) && !ParseRelaxed(Json))
	{
		UE_LOG(LogDinkNarrative, Warning, TEXT("physical play: %s does not parse; no hardbox is relaxed"), *DefaultRelaxedPath());
	}
}

bool FDinkPhysicalPlaySettings::ParseRelaxed(const FString& Json)
{
	Relaxed.Reset();
	TSharedPtr<FJsonObject> Root;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid()) return false;
	const TSharedPtr<FJsonObject>* Screens = nullptr;
	if (!Root->TryGetObjectField(TEXT("screens"), Screens)) return false;
	for (const auto& Pair : (*Screens)->Values)
	{
		const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
		if (!Pair.Value->TryGetArray(List)) continue;
		TSet<int32>& Set = Relaxed.FindOrAdd(FCString::Atoi(*Pair.Key));
		for (const TSharedPtr<FJsonValue>& V : *List) Set.Add(int32(V->AsNumber()));
	}
	return true;
}

bool UDinkGameplay::IsPhysicalPlayActive() const
{
	const int32 Console = CVarDinkPhysicalPlay.GetValueOnGameThread();
	const int32 Mode = Console >= 0 ? Console : PhysicalPlay.Mode;
	return Mode == 2 || (Mode == 1 && !GIsAutomationTesting && FApp::CanEverRender());
}

bool UDinkGameplay::IsPhysicalPlayPartOn(EPhysicalPlayPart Part) const
{
	if (!IsPhysicalPlayActive()) return false;
	const auto Pick = [](const TAutoConsoleVariable<int32>& Var, bool bIni) { const int32 V = Var.GetValueOnGameThread(); return V >= 0 ? V != 0 : bIni; };
	switch (Part)
	{
	case EPhysicalPlayPart::Collision: return Pick(CVarDinkPhysicalPlayCollision, PhysicalPlay.bCollision);
	case EPhysicalPlayPart::Touch: return Pick(CVarDinkPhysicalPlayTouch, PhysicalPlay.bTouch);
	case EPhysicalPlayPart::Bodies: return Pick(CVarDinkPhysicalPlayBodies, PhysicalPlay.bBodies);
	case EPhysicalPlayPart::Hits: return Pick(CVarDinkPhysicalPlayHits, PhysicalPlay.bHits);
	case EPhysicalPlayPart::CreatureReach: return Pick(CVarDinkPhysicalPlayCreatureReach, PhysicalPlay.bCreatureReach);
	}
	return false;
}

bool UDinkGameplay::UsesPhysicalPlay(const FDinkSprite& Attacker, const FDinkSprite& Target, EAuthoredInteraction Kind) const
{
	// Dink's own touches (part Touch) and blows (part Hits), and the blows of creatures at Dink (part CreatureReach). Hits and
	// CreatureReach are off by default: the hit decisions stay the 1997 ones (coordinator decision on PR #160, 16 Nov 2026).
	if (Attacker.Handle != 1 && Target.Handle != 1) return false;
	const EPhysicalPlayPart Part = Kind != EAuthoredInteraction::Hit ? EPhysicalPlayPart::Touch
		: Attacker.Handle == 1 ? EPhysicalPlayPart::Hits : EPhysicalPlayPart::CreatureReach;
	if (Kind != EAuthoredInteraction::Hit && Attacker.Handle != 1) return false;
	if (!IsPhysicalPlayPartOn(Part)) return false;
	const AActor* From = Attacker.Actor.Get();
	const AActor* To = Target.Actor.Get();
	if (!From || !To || To->IsHidden() || !From->GetWorld() || From->GetWorld() != To->GetWorld()) return false;
	// A target whose 1997 hardbox still stops Dink (solid, not relaxed: a chest, a scripted rock, a sign) keeps him at that box, out of
	// reach of its smaller drawn body; for such a target his reach ends at the box he can touch, so the 1997 box decides (review of
	// PR #160: the chest S005_P28 could not be opened in play).
	if (Target.GetProp(TEXT("hard"), 1) == 0 && !(Target.Origin.IsValid() && IsRelaxedForPlayer(Target.Origin.Screen, 100 + Target.Origin.Placement))) return false;
	// something drawn to touch: a tagged body, a visible mesh (family art, the 1997 card) or a creature's skinned body
	TInlineComponentArray<UPrimitiveComponent*> Components(To);
	for (const UPrimitiveComponent* C : Components)
	{
		if (!C->IsRegistered()) continue;
		if (C->ComponentHasTag(TEXT("DinkAuthoredInteraction"))) return true;
		if (C->IsVisible() && !C->bHiddenInGame && (C->IsA<UStaticMeshComponent>() || C->IsA<USkinnedMeshComponent>())) return true;
	}
	return false;
}

bool UDinkGameplay::IsRelaxedForPlayer(int32 Screen, int32 Code) const
{
	if (Code < 100 || !IsPhysicalPlayPartOn(EPhysicalPlayPart::Collision)) return false;
	const TSet<int32>* Set = PhysicalPlay.Relaxed.Find(Screen);
	return Set && Set->Contains(Code - 100);
}

void UDinkGameplay::ApplyPhysicalPlayCollision(int32 Screen)
{
	// Only with the layer on and a relaxed box on this screen: otherwise nothing is called, so the 1997 collision path is untouched.
	if (!IsPhysicalPlayPartOn(EPhysicalPlayPart::Collision) || !PhysicalPlay.Relaxed.Contains(Screen)) return;
	SyncGreyboxHardness(Screen);
}

bool UDinkGameplay::DrawnInteractionLands(int32 TargetHandle, bool bHit) const
{
	UDinkDirector* D = Director();
	const FDinkSprite* Dink = D ? D->FindSprite(1) : nullptr;
	const FDinkSprite* Target = D ? D->FindSprite(TargetHandle) : nullptr;
	if (!Dink || !Target) return false;
	const EAuthoredInteraction Kind = bHit ? EAuthoredInteraction::Hit : EAuthoredInteraction::Touch;
	// the layer does not decide it (its part is off, or the target keeps its 1997 box): the 1997 box the bot aimed by decides
	if (!UsesPhysicalPlay(*Dink, *Target, Kind)) return true;
	return AuthoredGeometryMatches(*Dink, *Target, Kind);
}

bool UDinkGameplay::DrawnClosestPoint(int32 TargetHandle, const FVector& From, FVector& Out) const
{
	UDinkDirector* D = Director();
	const FDinkSprite* Target = D ? D->FindSprite(TargetHandle) : nullptr;
	const AActor* A = Target ? Target->Actor.Get() : nullptr;
	if (!A || A->IsHidden()) return false;
	double Best = TNumericLimits<double>::Max();
	TInlineComponentArray<UPrimitiveComponent*> Components(A);
	for (UPrimitiveComponent* C : Components)
	{
		if (!C->IsRegistered() || !C->IsVisible() || C->bHiddenInGame) continue;
		const UStaticMeshComponent* Static = Cast<UStaticMeshComponent>(C);
		if (!(C->IsA<USkinnedMeshComponent>() || (Static && Static->GetStaticMesh()) || C->ComponentHasTag(TEXT("DinkAuthoredInteraction")))) continue;
		FVector P;
		if (C->IsA<USkinnedMeshComponent>() || !C->GetBodyInstance() || !C->GetBodyInstance()->IsValidBodyInstance())
		{
			// the same own box AuthoredGeometryMatches uses for a body without physics
			const FDinkDrawnBody Body = DrawnBodyBox(*C);
			P = Body.Frame.TransformPositionNoScale(FBox(-Body.Extent, Body.Extent).GetClosestPointTo(Body.Frame.InverseTransformPositionNoScale(From)));
		}
		else if (C->GetClosestPointOnCollision(From, P) < 0.f)
		{
			P = C->Bounds.GetBox().GetClosestPointTo(From);
		}
		const double Dist = FVector::DistSquared2D(P, From);
		if (Dist < Best) { Best = Dist; Out = P; }
	}
	return Best < TNumericLimits<double>::Max();
}

#if !UE_BUILD_SHIPPING
// Review: the drawn bodies the layer hits and touches, with their sizes (a skinned body's own box against its world bounds).
static FAutoConsoleCommandWithWorld GDinkPhysicalPlayBodiesCommand(
	TEXT("dink.PhysicalPlayBodies"),
	TEXT("Review only: for every live sprite with a drawn skinned body, logs its own box (what the physical play layer hits) and its world bounds, in cm, and Dink's distance to the box."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
		UDinkStorySubsystem* Story = GI ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		UDinkDirector* D = Story ? Story->GetDirector() : nullptr;
		if (!D) return;
		const AActor* DinkActor = D->GetDink().Actor.Get();
		for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
		{
			const AActor* A = Pair.Value.Actor.Get();
			if (Pair.Key == 1 || !A || A->IsHidden()) continue;
			TInlineComponentArray<USkinnedMeshComponent*> Skins(A);
			for (const USkinnedMeshComponent* Skin : Skins)
			{
				if (!Skin->IsRegistered() || !Skin->IsVisible() || Skin->bHiddenInGame) continue;
				const FDinkDrawnBody Body = UDinkGameplay::DrawnBodyBox(*Skin);
				const FVector World3 = Skin->Bounds.BoxExtent * 2.0;
				double Gap = -1.0;
				if (DinkActor)
				{
					const FVector L = Body.Frame.InverseTransformPositionNoScale(DinkActor->GetActorLocation());
					Gap = FVector::Dist2D(FVector(L.X, L.Y, 0), FBox(-Body.Extent, Body.Extent).GetClosestPointTo(FVector(L.X, L.Y, 0)));
				}
				UE_LOG(LogDinkNarrative, Display, TEXT("DINK PHYSICAL BODY: sprite %d script=%s brain=%d hp=%d own box %.0f x %.0f x %.0f cm, world bounds %.0f x %.0f x %.0f cm, bounds scale %.2f, Dink centre to box %.0f cm"),
					Pair.Key, *Pair.Value.Script.ToString(), Pair.Value.GetProp(TEXT("brain")), Pair.Value.GetProp(TEXT("hitpoints")),
					Body.Extent.X * 2, Body.Extent.Y * 2, Body.Extent.Z * 2, World3.X, World3.Y, World3.Z, Skin->BoundsScale, Gap);
			}
		}
	}));
// Review (doc/remaster/COMBAT_REACH_OPTIONS.md): how far from the drawn bodies the 1997 blow boxes register. For every live sprite on
// Dink's screen with a drawn body, for the fist (range 0) and the sword (40) and the four facings: the farthest pixel in front of it
// (on the line through its sprite point, against the facing) where the 1997 box of RunThroughTagList (D:15460-15527) still holds
// Dink, and how far his capsule's surface then is from its drawn own box (cm). The other way round, for its own sp_range: the
// farthest it can stand from Dink and still hit him by the 1997 box, as the gap between its drawn box and his capsule.
static FAutoConsoleCommandWithWorld GDinkPhysicalPlayReachCommand(
	TEXT("dink.PhysicalPlayReach"),
	TEXT("Review only: logs, per live drawn sprite on Dink's screen, how far from its drawn body the 1997 blow boxes register (fist, sword, its own range at Dink), in px and cm."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
		UDinkStorySubsystem* Story = GI ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		UDinkDirector* D = Story ? Story->GetDirector() : nullptr;
		UDinkGameplay* G = Story ? Story->GetGameplay() : nullptr;
		if (!D || !G) return;
		const FDinkSprite& Me = D->GetDink();
		const AActor* DinkActor = Me.Actor.Get();
		const UCapsuleComponent* Capsule = DinkActor ? DinkActor->FindComponentByClass<UCapsuleComponent>() : nullptr;
		const double Radius = Capsule ? Capsule->GetScaledCapsuleRadius() : 28.0;
		static const FIntPoint Step[10] = { {0,0}, {-1,1}, {0,1}, {1,1}, {-1,0}, {0,0}, {1,0}, {-1,-1}, {0,-1}, {1,-1} };
		const auto GapTo = [](const FDinkDrawnBody& Body, const FVector& Centre, const FVector& At)
		{
			// Body moved so its centre is at Centre (same turn): the 2D distance from At to that box
			const FTransform Frame(Body.Frame.GetRotation(), FVector(Centre.X, Centre.Y, Body.Frame.GetLocation().Z));
			const FVector L = Frame.InverseTransformPositionNoScale(FVector(At.X, At.Y, Body.Frame.GetLocation().Z));
			const FVector C = FBox(-Body.Extent, Body.Extent).GetClosestPointTo(L);
			return FVector::Dist2D(L, C);
		};
		for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
		{
			const FDinkSprite& T = Pair.Value;
			const AActor* A = T.Actor.Get();
			if (Pair.Key == 1 || !A || A->IsHidden() || !T.bActive || T.Screen != Me.Screen) continue;
			const UPrimitiveComponent* Drawn = nullptr;
			TInlineComponentArray<UPrimitiveComponent*> Components(A);
			for (const UPrimitiveComponent* C : Components)
			{
				if (!C->IsRegistered() || !C->IsVisible() || C->bHiddenInGame || C->ComponentHasTag(TEXT("DinkCreatureBodyBlocker"))) continue;
				if (C->IsA<USkinnedMeshComponent>()) { Drawn = C; break; }
			}
			if (!Drawn) continue;
			const FDinkDrawnBody Body = UDinkGameplay::DrawnBodyBox(*Drawn);
			FVector TWorld;
			if (!D->PixelToWorld(T.Screen, T.X, T.Y, TWorld)) continue;
			FString Line = FString::Printf(TEXT("DINK PHYSICAL REACH: sprite %d script=%s brain=%d hp=%d range=%d own box %.0f x %.0f cm:"),
				Pair.Key, *T.Script.ToString(), T.GetProp(TEXT("brain")), T.GetProp(TEXT("hitpoints")), T.GetProp(TEXT("range")), Body.Extent.X * 2, Body.Extent.Y * 2);
			for (const int32 Range : { 0, 40 })
			{
				Line += Range == 0 ? TEXT(" FIST") : TEXT(" SWORD");
				for (const int32 Dir : { 2, 4, 6, 8 })
				{
					int32 Far = -1;
					for (int32 Dpx = 0; Dpx <= 400; ++Dpx)
					{
						if (G->LegacyHitBoxContains(T, FMath::RoundToInt32(T.X) - Step[Dir].X * Dpx, FMath::RoundToInt32(T.Y) - Step[Dir].Y * Dpx, Dir, Range)) Far = Dpx;
					}
					FVector At;
					if (Far < 0 || !D->PixelToWorld(T.Screen, T.X - Step[Dir].X * Far, T.Y - Step[Dir].Y * Far, At)) { Line += FString::Printf(TEXT(" d%d -"), Dir); continue; }
					Line += FString::Printf(TEXT(" d%d %dpx=%.0fcm"), Dir, Far, GapTo(Body, TWorld, At) - Radius);
				}
			}
			// its blow at Dink: Dink is the target, the creature stands Dpx behind its facing
			const int32 OwnRange = T.GetProp(TEXT("range"));
			FVector MeWorld;
			if (D->PixelToWorld(Me.Screen, Me.X, Me.Y, MeWorld))
			{
				Line += TEXT(" AT-DINK");
				for (const int32 Dir : { 2, 4, 6, 8 })
				{
					int32 Far = -1;
					for (int32 Dpx = 0; Dpx <= 400; ++Dpx)
					{
						if (G->LegacyHitBoxContains(Me, FMath::RoundToInt32(Me.X) - Step[Dir].X * Dpx, FMath::RoundToInt32(Me.Y) - Step[Dir].Y * Dpx, Dir, OwnRange)) Far = Dpx;
					}
					FVector At;
					if (Far < 0 || !D->PixelToWorld(Me.Screen, Me.X - Step[Dir].X * Far, Me.Y - Step[Dir].Y * Far, At)) { Line += FString::Printf(TEXT(" d%d -"), Dir); continue; }
					Line += FString::Printf(TEXT(" d%d %dpx=%.0fcm"), Dir, Far, GapTo(Body, At, MeWorld) - Radius);
				}
			}
			UE_LOG(LogDinkNarrative, Display, TEXT("%s"), *Line);
		}
	}));
#endif
// ---- Creature bodies (bug A21, owner decision 16 Nov 2026) ----

namespace
{
	const FName CreatureBodyBlockerTag(TEXT("DinkCreatureBodyBlocker"));
	/**
	 * The blocker is the drawn body's bounds (what the layer's hits and touches use for a skinned body) less this much on each side
	 * (cm): Dink stops at the body, never short of it, and stays inside the layer's touch reach (ContactReachCm, default 5), so a
	 * creature's touch damage still lands when he walks up to it, as in 1997.
	 */
	constexpr double BodyBlockerInsetCm = 3.0;
	/** Dink counts as inside a body (it walked into him) when he is this far (cm) past its blocker's surface. */
	constexpr double BodyBlockerInsideCm = 2.0;
	/** The blocker is at least this tall (cm): a low pillbug is not a step Dink climbs onto (CharacterMovement steps ~45 cm). */
	constexpr double BodyBlockerMinHeightCm = 120.0;

	/** The drawn body of a creature actor: its visible skinned mesh, else a visible static mesh (not a blocker, not a corpse). */
	UPrimitiveComponent* DrawnCreatureBody(const AActor& Actor)
	{
		UPrimitiveComponent* Static = nullptr;
		TInlineComponentArray<UPrimitiveComponent*> Components(&Actor);
		for (UPrimitiveComponent* C : Components)
		{
			if (!C->IsRegistered() || !C->IsVisible() || C->bHiddenInGame || C->ComponentHasTag(CreatureBodyBlockerTag) || C->ComponentHasTag(TEXT("DinkCreatureCorpse"))) continue;
			if (C->IsA<USkinnedMeshComponent>()) return C;
			if (!Static && C->IsA<UStaticMeshComponent>()) Static = C;
		}
		return Static;
	}

	/** Dink's capsule overlaps the blocker's box (plan within box + radius, heights overlapping): the body walked into him. */
	bool CapsuleOverlapsBox(const UCapsuleComponent& Capsule, const UBoxComponent& Box)
	{
		const FTransform T = Box.GetComponentTransform();
		const FVector Local = T.InverseTransformPositionNoScale(Capsule.GetComponentLocation());
		const FVector Extent = Box.GetScaledBoxExtent();
		const double R = Capsule.GetScaledCapsuleRadius();
		const double H = Capsule.GetScaledCapsuleHalfHeight();
		const double In = BodyBlockerInsideCm;
		return FMath::Abs(Local.X) < Extent.X + R - In && FMath::Abs(Local.Y) < Extent.Y + R - In && FMath::Abs(Local.Z) < Extent.Z + H - In;
	}
}

UBoxComponent* UDinkGameplay::FindCreatureBodyBlocker(const AActor* Actor)
{
	if (!Actor) return nullptr;
	TInlineComponentArray<UBoxComponent*> Boxes(Actor);
	for (UBoxComponent* B : Boxes) if (B->ComponentHasTag(CreatureBodyBlockerTag)) return B;
	return nullptr;
}

void UDinkGameplay::UpdateCreatureBodyBlockers()
{
	const bool bOn = IsPhysicalPlayPartOn(EPhysicalPlayPart::Bodies);
	if (!bOn && CreatureBodyBlockers.IsEmpty()) return; // the 1997 path: nothing made, nothing touched
	UDinkDirector* D = Director();
	TSet<UBoxComponent*> Keep;
	if (bOn && D)
	{
		const AActor* DinkActor = D->GetDink().Actor.Get();
		const UCapsuleComponent* DinkCapsule = DinkActor ? Cast<UCapsuleComponent>(DinkActor->GetRootComponent()) : nullptr;
		for (const TPair<int32, FDinkSprite>& Pair : D->Sprites)
		{
			const FDinkSprite& S = Pair.Value;
			AActor* A = S.Actor.Get();
			// living, drawn creatures only: a dead one (brain 0, its corpse) or a hidden one blocks nothing
			if (Pair.Key == 1 || !A || !S.bActive || A->IsHidden() || !A->ActorHasTag(TEXT("DinkCreature")) || S.GetProp(TEXT("brain")) == 0) continue;
			UPrimitiveComponent* Body = DrawnCreatureBody(*A);
			if (!Body) continue;
			UBoxComponent* Box = FindCreatureBodyBlocker(A);
			if (!Box)
			{
				Box = NewObject<UBoxComponent>(A, MakeUniqueObjectName(A, UBoxComponent::StaticClass(), TEXT("CreatureBodyBlocker")));
				Box->SetMobility(EComponentMobility::Movable);
				Box->SetCollisionProfileName(DinkCollision::ProfilePlayerBlock);
				Box->SetGenerateOverlapEvents(false);
				Box->SetCanEverAffectNavigation(false);
				Box->CanCharacterStepUpOn = ECB_No;
				Box->SetHiddenInGame(true);
				Box->ComponentTags.Add(CreatureBodyBlockerTag);
				Box->SetupAttachment(Body);
				A->AddInstanceComponent(Box);
				Box->RegisterComponent();
				CreatureBodyBlockers.Add(Box);
			}
			else if (Box->GetAttachParent() != Body)
			{
				Box->AttachToComponent(Body, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
			}
			// The body's own plan (component space, so it turns with the body), inset, and at least BodyBlockerMinHeightCm tall.
			const FBoxSphereBounds Local = Body->CalcBounds(FTransform::Identity);
			const FVector Scale = Body->GetComponentScale().GetAbs().ComponentMax(FVector(0.01));
			const auto Inset = [](double HalfLocal, double ScaleAxis)
			{
				const double World = HalfLocal * ScaleAxis;
				return (World - FMath::Min(BodyBlockerInsetCm, World * 0.5)) / ScaleAxis;
			};
			const double HalfZ = FMath::Max(Local.BoxExtent.Z, BodyBlockerMinHeightCm * 0.5 / Scale.Z);
			const FVector Extent(Inset(Local.BoxExtent.X, Scale.X), Inset(Local.BoxExtent.Y, Scale.Y), HalfZ);
			Box->SetBoxExtent(Extent, false);
			Box->SetRelativeLocation(FVector(Local.Origin.X, Local.Origin.Y, Local.Origin.Z - Local.BoxExtent.Z + HalfZ));
			Box->SetRelativeRotation(FRotator::ZeroRotator);
			// Never a trap: a body that walked into Dink lets him go until he is clear of it.
			const bool bInside = DinkCapsule && CapsuleOverlapsBox(*DinkCapsule, *Box);
			Box->SetCollisionEnabled(bInside ? ECollisionEnabled::NoCollision : ECollisionEnabled::QueryAndPhysics);
			Keep.Add(Box);
		}
	}
	for (int32 I = CreatureBodyBlockers.Num() - 1; I >= 0; --I)
	{
		UBoxComponent* Box = CreatureBodyBlockers[I].Get();
		if (Box && Keep.Contains(Box)) continue;
		if (Box) Box->DestroyComponent();
		CreatureBodyBlockers.RemoveAt(I);
	}
}
