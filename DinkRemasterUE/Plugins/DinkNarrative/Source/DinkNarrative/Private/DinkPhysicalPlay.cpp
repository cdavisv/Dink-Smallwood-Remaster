// Physical play layer (doc/remaster/PHYSICAL_PLAY_LAYER.md; bug A70, owner confirmed 16 Nov 2026). In play, what Dink himself
// touches follows what is drawn: his collision drops the 1997 sprite hardboxes listed as relaxed (their drawn mesh keeps PR #129's
// player-only blocker), his touches use the drawn geometry (the existing authored-geometry tests of DinkAuthoredInteraction.cpp), and
// living creatures carry a player-only body box (A21), and blows land at drawn contact both ways (parts Hits, CreatureReach: on,
// owner decision 19 Nov 2026).
// WHAT a hit or touch does is the 1997 path unchanged (RunThroughTagList / RunThroughTouchDamageList,
// dink.cpp:15460-15527, 15629-15651): same damage formula, same rand() draws, same procedures. NPCs, creatures, missiles (but those at
// Dink with part CreatureReach: MissileHitsTarget) and brains keep the 1997 boxes; get_hard keeps them but where part Collision
// relaxes a box outside its drawn footprint or opens a painted tile (PlayHardness). Off under automation (the probe and the parity tests), so the probe traces do not move.

#include "DinkGameplay.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "DinkNarrativeTypes.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "DinkCollision.h"
#include "DinkCreatureSubsystem.h"
#include "DinkCreatureClassComponent.h"
#include "DinkLandforms.h"
#include "DinkPlayerBlockers.h"
#include "DinkArtFamilySubsystem.h"
#include "UObject/UObjectIterator.h"
#include "Components/BoxComponent.h"
#include "Components/ShapeComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
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
		TEXT("Physical play part: Dink's blows land at drawn contact. -1 the ini (default on), 0 off (the 1997 hit box), 1 on."));
	TAutoConsoleVariable<int32> CVarDinkPhysicalPlayCreatureReach(TEXT("dink.PhysicalPlay.CreatureReach"), -1,
		TEXT("Physical play part: creature blows and missiles at Dink by drawn reach and body. -1 the ini (default on), 0 off (the 1997 boxes), 1 on."));
}

FString FDinkPhysicalPlaySettings::DefaultIniPath() { return FPaths::ProjectContentDir() / TEXT("Dink/Data/Play/physical_play.ini"); }
FString FDinkPhysicalPlaySettings::DefaultSealedPath() { return FPaths::ProjectContentDir() / TEXT("Dink/Data/Play/sealed_gaps.json"); }
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
			else if (Key == TEXT("StillBodies"))
			{
				TArray<FString> Ids;
				Value.ParseIntoArray(Ids, TEXT(","));
				StillBodies.Reset();
				for (FString& Id : Ids) { Id.TrimStartAndEndInline(); if (!Id.IsEmpty()) StillBodies.Add(FName(*Id)); }
			}
		}
		Source = DefaultIniPath();
	}
	FString Json;
	if (FFileHelper::LoadFileToString(Json, *DefaultRelaxedPath()) && !ParseRelaxed(Json))
	{
		UE_LOG(LogDinkNarrative, Warning, TEXT("physical play: %s does not parse; no hardbox is relaxed"), *DefaultRelaxedPath());
	}
	Sealed.Reset();
	if (FFileHelper::LoadFileToString(Json, *DefaultSealedPath()) && !ParseSealed(Json))
	{
		UE_LOG(LogDinkNarrative, Warning, TEXT("physical play: %s does not parse; no gap is sealed"), *DefaultSealedPath());
	}
}

bool FDinkPhysicalPlaySettings::ParseSealed(const FString& Json)
{
	Sealed.Reset();
	TSharedPtr<FJsonObject> Root;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid()) return false;
	const TSharedPtr<FJsonObject>* Screens = nullptr;
	if (!Root->TryGetObjectField(TEXT("screens"), Screens)) return false;
	for (const auto& Pair : (*Screens)->Values)
	{
		const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
		if (!Pair.Value->TryGetArray(List)) continue;
		for (const TSharedPtr<FJsonValue>& V : *List)
		{
			const TSharedPtr<FJsonObject>* Row = nullptr;
			const TArray<TSharedPtr<FJsonValue>>* R = nullptr;
			if (!V->TryGetObject(Row) || !(*Row)->TryGetArrayField(TEXT("rect"), R) || R->Num() != 4) continue;
			Sealed.FindOrAdd(FCString::Atoi(*Pair.Key)).Add(FIntRect(int32((*R)[0]->AsNumber()), int32((*R)[1]->AsNumber()), int32((*R)[2]->AsNumber()), int32((*R)[3]->AsNumber())));
		}
	}
	return true;
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
	// schema 2: "feet" {screen: {placement: [l, t, r, b]}} (map pixels, inclusive) and "open_tiles" {screen: [cell, ...]}
	Feet.Reset();
	OpenTiles.Reset();
	const TSharedPtr<FJsonObject>* FeetObject = nullptr;
	if (Root->TryGetObjectField(TEXT("feet"), FeetObject))
	{
		for (const auto& ScreenPair : (*FeetObject)->Values)
		{
			const TSharedPtr<FJsonObject>* ByPlacement = nullptr;
			if (!ScreenPair.Value->TryGetObject(ByPlacement)) continue;
			for (const auto& Pair : (*ByPlacement)->Values)
			{
				const TArray<TSharedPtr<FJsonValue>>* R = nullptr;
				if (!Pair.Value->TryGetArray(R) || R->Num() != 4) continue;
				Feet.Add(FCString::Atoi(*ScreenPair.Key) * 1000 + FCString::Atoi(*Pair.Key),
					FIntRect(int32((*R)[0]->AsNumber()), int32((*R)[1]->AsNumber()), int32((*R)[2]->AsNumber()), int32((*R)[3]->AsNumber())));
			}
		}
	}
	Trimmed.Reset();
	TrimAlongX.Reset();
	const TSharedPtr<FJsonObject>* TrimmedObject = nullptr;
	if (Root->TryGetObjectField(TEXT("trimmed"), TrimmedObject))
	{
		// {screen: {placement: [box l, t, r, b]}}
		for (const auto& ScreenPair : (*TrimmedObject)->Values)
		{
			const TSharedPtr<FJsonObject>* ByPlacement = nullptr;
			if (!ScreenPair.Value->TryGetObject(ByPlacement)) continue;
			for (const auto& Pair : (*ByPlacement)->Values)
			{
				const TArray<TSharedPtr<FJsonValue>>* R = nullptr;
				if (!Pair.Value->TryGetArray(R) || R->Num() != 4) continue;
				const int32 Key = FCString::Atoi(*ScreenPair.Key) * 1000 + FCString::Atoi(*Pair.Key);
				Trimmed.Add(Key, FIntRect(int32((*R)[0]->AsNumber()), int32((*R)[1]->AsNumber()), int32((*R)[2]->AsNumber()), int32((*R)[3]->AsNumber())));
				// the wall's run: along x unless the generator says y ("across" of schema: the trim rect's long side)
				if (const FIntRect* F = Feet.Find(Key); !F || F->Width() >= F->Height()) TrimAlongX.Add(Key);
			}
		}
	}
	const TSharedPtr<FJsonObject>* Tiles = nullptr;
	if (Root->TryGetObjectField(TEXT("open_tiles"), Tiles))
	{
		for (const auto& Pair : (*Tiles)->Values)
		{
			const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
			if (!Pair.Value->TryGetArray(List)) continue;
			TSet<int32>& Set = OpenTiles.FindOrAdd(FCString::Atoi(*Pair.Key));
			for (const TSharedPtr<FJsonValue>& V : *List) Set.Add(int32(V->AsNumber()));
		}
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
	// Dink's own touches (part Touch) and blows (part Hits), and the blows of creatures at Dink (part CreatureReach), all on in play
	// (Hits and CreatureReach: owner decision of 19 Nov 2026); a part off leaves its decisions to the 1997 boxes.
	if (Attacker.Handle != 1 && Target.Handle != 1) return false;
	const EPhysicalPlayPart Part = Kind != EAuthoredInteraction::Hit ? EPhysicalPlayPart::Touch
		: Attacker.Handle == 1 ? EPhysicalPlayPart::Hits : EPhysicalPlayPart::CreatureReach;
	if (Kind != EAuthoredInteraction::Hit && Attacker.Handle != 1) return false;
	if (!IsPhysicalPlayPartOn(Part)) return false;
	const AActor* From = Attacker.Actor.Get();
	const AActor* To = Target.Actor.Get();
	if (!From || !To || To->IsHidden() || !From->GetWorld() || From->GetWorld() != To->GetWorld()) return false;
	// a creature's blow at Dink (part CreatureReach): by the creature's drawn body against his capsule (CreatureReachMatches)
	if (Target.Handle == 1)
	{
		FDinkDrawnBody Body;
		return CreatureDrawnBody(*From, Body);
	}
	// A target whose 1997 hardbox still stops Dink (solid, not relaxed: a chest, a scripted rock, a sign) keeps him at that box, out of
	// reach of its smaller drawn body; for such a target his reach ends at the box he can touch, so the 1997 box decides (review of
	// PR #160: the chest S005_P28 could not be opened in play).
	// Only a still target (no brain): a creature's 1997 box moves with it and stops no one (21 Nov 2026: the cave Bonca, hard 0, bit
	// Dink by its 1997 touch box 40 cm off its drawn body).
	if (Target.GetProp(TEXT("brain")) == 0 && Target.GetProp(TEXT("hard"), 1) == 0 &&
		!(Target.Origin.IsValid() && IsRelaxedForPlayer(Target.Origin.Screen, 100 + Target.Origin.Placement))) return false;
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

bool UDinkGameplay::CreatureReachesDink(const FDinkSprite& Creature, int32 Dir, bool* OutSightBlocked) const
{
	if (OutSightBlocked) *OutSightBlocked = false;
	UDinkDirector* D = Director();
	const FDinkSprite* Dink = D ? D->FindSprite(1) : nullptr;
	if (!Dink) return false;
	FDinkSprite Facing = Creature;
	Facing.Dir = Dir;
	return CreatureReachMatches(Facing, *Dink, nullptr, OutSightBlocked);
}

double UDinkGameplay::CreatureReachRadiusCm(const FDinkSprite& Creature) const
{
	UDinkDirector* D = Director();
	const FDinkSprite* Dink = D ? D->FindSprite(1) : nullptr;
	const AActor* A = Creature.Actor.Get();
	FDinkDrawnBody Body;
	if (!Dink || !A || !UsesPhysicalPlay(Creature, *Dink, EAuthoredInteraction::Hit) || !CreatureDrawnBody(*A, Body)) return 0.0;
	const double Scale = FMath::Max(Creature.GetProp(TEXT("range")), 28) / 28.0;
	const double Half = FMath::Max(Body.Extent.X, Body.Extent.Y);
	const AActor* DinkActor = Dink->Actor.Get();
	const UCapsuleComponent* Capsule = DinkActor ? DinkActor->FindComponentByClass<UCapsuleComponent>() : nullptr;
	return FMath::Sqrt(FMath::Square(Half + AuthoredInteraction.AttackReachCm * Scale) + FMath::Square(Half + AuthoredInteraction.AttackHalfWidthCm * Scale)) +
		(Capsule ? Capsule->GetScaledCapsuleRadius() : 28.0);
}

bool UDinkGameplay::IsRelaxedForPlayer(int32 Screen, int32 Code) const
{
	// (review of 22 Nov 2026, nit 15: an original-hardness screen keeps its 1997 boxes for collision, so for hits and touches too)
	if (Code < 100 || !IsPhysicalPlayPartOn(EPhysicalPlayPart::Collision) || RequiresOriginalHardnessScreen(Screen)) return false;
	const TSet<int32>* Set = PhysicalPlay.Relaxed.Find(Screen);
	return Set && Set->Contains(Code - 100) && !RelaxedWithoutBlocker.Contains(Screen * 1000 + Code - 100);
}

void UDinkGameplay::CheckRelaxedBlockers(int32 Screen)
{
	for (auto It = RelaxedWithoutBlocker.CreateIterator(); It; ++It) if (*It / 1000 == Screen) It.RemoveCurrent();
	const TSet<int32>* Set = PhysicalPlay.Relaxed.Find(Screen);
	UDinkDirector* D = Director();
	UWorld* World = Story ? Story->GetWorld() : nullptr;
	if (!Set || !D || !World) return;
	// the screen's art first (idempotent: its family meshes and their player-only hulls), then every hull's plan
	if (UDinkArtFamilySubsystem* Families = World->GetSubsystem<UDinkArtFamilySubsystem>()) Families->ApplyScreen(Screen);
	TArray<FBox, TInlineAllocator<64>> Hulls;
	TArray<UStaticMeshComponent*, TInlineAllocator<64>> Walls;
	for (TObjectIterator<UPrimitiveComponent> It; It; ++It)
	{
		if (It->GetWorld() != World || !It->IsRegistered()) continue;
		if (It->ComponentHasTag(DinkPlayerBlockers::Tag)) Hulls.Add(It->Bounds.GetBox());
		// A71: a trimmed wall needs its drawn wall module there (it keeps its box inside the drawn strip, no hull; shown or not: the
		// interior camera hides walls between it and Dink)
		if (UStaticMeshComponent* M = Cast<UStaticMeshComponent>(*It); M && M->GetStaticMesh() && M->GetStaticMesh()->GetName().Contains(TEXT("Wall"))) Walls.Add(M);
	}
	for (const int32 N : *Set)
	{
		if (const FIntRect* WallBox = PhysicalPlay.Trimmed.Find(Screen * 1000 + N))
		{
			if (!MeasureWallStrip(Screen, N, *WallBox, PhysicalPlay.TrimAlongX.Contains(Screen * 1000 + N), Walls))
			{
				RelaxedWithoutBlocker.Add(Screen * 1000 + N);
				UE_LOG(LogDinkNarrative, Display, TEXT("DINK PHYSICAL PLAY: wall S%03d_P%02d keeps its 1997 box (no drawn wall module across it)"), Screen, N);
			}
			continue;
		}
		const FIntRect* Foot = PhysicalPlay.Feet.Find(Screen * 1000 + N);
		if (!Foot) continue;
		FBox Plan(ForceInit);
		bool bMapped = true;
		for (const FIntPoint C : { Foot->Min, Foot->Max, FIntPoint(Foot->Min.X, Foot->Max.Y), FIntPoint(Foot->Max.X, Foot->Min.Y) })
		{
			FVector P;
			bMapped &= D->PixelToWorld(Screen, C.X + 20.0, C.Y, P);
			Plan += P;
		}
		if (!bMapped) continue;
		Plan = Plan.ExpandBy(FVector(15.0, 15.0, 1e6));
		bool bBlocker = false;
		for (const FBox& Hull : Hulls) bBlocker |= Hull.Intersect(Plan);
		if (!bBlocker)
		{
			RelaxedWithoutBlocker.Add(Screen * 1000 + N);
			UE_LOG(LogDinkNarrative, Display, TEXT("DINK PHYSICAL PLAY: S%03d_P%02d keeps its 1997 box (no player-only blocker over its drawn footprint)"), Screen, N);
		}
	}
}

bool UDinkGameplay::MeasureWallStrip(int32 Screen, int32 N, const FIntRect& Box, bool bAlongX, const TArray<UStaticMeshComponent*, TInlineAllocator<64>>& Walls)
{
	// A71: the drawn strip of a trimmed wall, measured on the wall meshes as the world stands: the vertices of their lowest 1.2 m (LOD 0,
	// mesh space: the wall's faces where they meet the floor; a cornice or an arch overhead does not count) that fall inside its 1997
	// box give the strip's extent across the wall; the strip runs on along the wall to the box's ends. Map pixels from world by the
	// box's own corners (an affine fit over one box). Family meshes have no collision of their own, so no trace can find them.
	UDinkDirector* D = Director();
	FVector P00, P10, P01;
	if (!D || !D->PixelToWorld(Screen, Box.Min.X + 20.0, Box.Min.Y, P00) || !D->PixelToWorld(Screen, Box.Max.X + 20.0, Box.Min.Y, P10) ||
		!D->PixelToWorld(Screen, Box.Min.X + 20.0, Box.Max.Y, P01)) return false;
	const FVector2D Ex(FVector2D(P10 - P00) / FMath::Max(1, Box.Width())), Ey(FVector2D(P01 - P00) / FMath::Max(1, Box.Height()));
	const double Det = Ex.X * Ey.Y - Ex.Y * Ey.X;
	if (FMath::Abs(Det) < 1e-6) return false;
	const auto ToPixel = [&](const FVector& W) { const FVector2D R = FVector2D(W) - FVector2D(P00); return FVector2D(Box.Min.X + (R.X * Ey.Y - R.Y * Ey.X) / Det, Box.Min.Y + (Ex.X * R.Y - Ex.Y * R.X) / Det); };
	FBox Plan(ForceInit);
	for (const FVector& C : { P00, P10, P01, P10 + (P01 - P00) }) Plan += C;
	Plan = Plan.ExpandBy(FVector(20.0, 20.0, 1e5));
	const double A0 = bAlongX ? Box.Min.X : Box.Min.Y, A1 = bAlongX ? Box.Max.X : Box.Max.Y; // along the wall
	const double C0 = bAlongX ? Box.Min.Y : Box.Min.X, C1 = bAlongX ? Box.Max.Y : Box.Max.X; // across it
	double Lo = TNumericLimits<double>::Max(), Hi = TNumericLimits<double>::Lowest(), ALo = Lo, AHi = Hi;
	const auto Take = [&](const UStaticMesh& Mesh, const FTransform& T)
	{
		const double Floor = Mesh.GetBounds().Origin.Z - Mesh.GetBounds().BoxExtent.Z; // the mesh's foot, wherever its pivot is
		const FStaticMeshRenderData* RD = Mesh.GetRenderData();
		if (!RD || RD->LODResources.Num() == 0) return;
		const FPositionVertexBuffer& PB = RD->LODResources[0].VertexBuffers.PositionVertexBuffer;
		if (!PB.GetVertexData()) return;
		for (uint32 I = 0; I < PB.GetNumVertices(); ++I)
		{
			const FVector V(PB.VertexPosition(I));
			if (V.Z > Floor + 120.0) continue;
			const FVector2D Px = ToPixel(T.TransformPosition(V));
			const double A = bAlongX ? Px.X : Px.Y, C = bAlongX ? Px.Y : Px.X;
			if (A < A0 || A > A1 || C < C0 - 2 || C > C1 + 2) continue;
			Lo = FMath::Min(Lo, C); Hi = FMath::Max(Hi, C); ALo = FMath::Min(ALo, A); AHi = FMath::Max(AHi, A);
		}
	};
	for (UStaticMeshComponent* M : Walls)
	{
		if (!M || !M->GetStaticMesh() || !M->Bounds.GetBox().Intersect(Plan)) continue;
		if (const UInstancedStaticMeshComponent* I = Cast<UInstancedStaticMeshComponent>(M))
		{
			for (int32 K = 0; K < I->GetInstanceCount(); ++K)
			{
				FTransform T;
				if (I->GetInstanceTransform(K, T, true) && M->GetStaticMesh()->GetBounds().GetBox().TransformBy(T).Intersect(Plan)) Take(*M->GetStaticMesh(), T);
			}
		}
		else Take(*M->GetStaticMesh(), M->GetComponentTransform());
	}
	// a wall that runs at least 40 % of the box (a module drawn shorter than its box still closes the line: the strip runs on); a wall
	// module over the box whose vertices cannot be read (no CPU copy, a cooked build) keeps the generator's strip (the 15 Nov audit slice)
	if (Hi < Lo || AHi - ALo < 0.4 * (A1 - A0))
	{
		bool bModule = false;
		for (UStaticMeshComponent* M : Walls) bModule |= M && M->Bounds.GetBox().Intersect(Plan);
		return bModule && PhysicalPlay.Feet.Contains(Screen * 1000 + N);
	}
	const int32 L = FMath::Clamp(FMath::FloorToInt(Lo), int32(C0), int32(C1)), R = FMath::Clamp(FMath::CeilToInt(Hi), int32(C0), int32(C1));
	PhysicalPlay.Feet.Add(Screen * 1000 + N, bAlongX ? FIntRect(Box.Min.X, L, Box.Max.X, R) : FIntRect(L, Box.Min.Y, R, Box.Max.Y));
	return true;
}

int32 UDinkGameplay::PlayHardness(int32 Screen, int32 MapX, int32 MapY, int32 Code) const
{
	if (Code == 0 || (PhysicalPlay.Relaxed.IsEmpty() && PhysicalPlay.OpenTiles.IsEmpty()) || !IsPhysicalPlayPartOn(EPhysicalPlayPart::Collision)) return Code;
	if (Code > 100)
	{
		// a relaxed placement's box stands only where its mesh is drawn (no footprint known: the 1997 box, as before the layer)
		if (!IsRelaxedForPlayer(Screen, Code)) return Code;
		const FIntRect* Foot = PhysicalPlay.Feet.Find(Screen * 1000 + Code - 100);
		return !Foot || (MapX >= Foot->Min.X && MapX <= Foot->Max.X && MapY >= Foot->Min.Y && MapY <= Foot->Max.Y) ? Code : 0;
	}
	if (Code < 100 && MapX >= 0 && MapY >= 0 && MapX < FDinkHardnessMap::Width && MapY < FDinkHardnessMap::Height)
	{
		if (const TSet<int32>* Open = PhysicalPlay.OpenTiles.Find(Screen); Open && Open->Contains((MapY / 50) * 12 + MapX / 50)) return 0;
	}
	return Code;
}

bool UDinkGameplay::HasOpenTilesForPlayer(int32 Screen) const
{
	return PhysicalPlay.OpenTiles.Contains(Screen) && IsPhysicalPlayPartOn(EPhysicalPlayPart::Collision) && !RequiresOriginalHardnessScreen(Screen);
}

bool UDinkGameplay::HasSealsForPlayer(int32 Screen) const
{
	return PhysicalPlay.Sealed.Contains(Screen) && IsPhysicalPlayPartOn(EPhysicalPlayPart::Collision) && !RequiresOriginalHardnessScreen(Screen);
}

bool UDinkGameplay::IsSealedForPlayer(int32 Screen, int32 MapX, int32 MapY) const
{
	const TArray<FIntRect>* Rects = PhysicalPlay.Sealed.Find(Screen);
	if (!Rects || !HasSealsForPlayer(Screen)) return false;
	for (const FIntRect& R : *Rects)
	{
		if (MapX >= R.Min.X && MapX <= R.Max.X && MapY >= R.Min.Y && MapY <= R.Max.Y) return true;
	}
	return false;
}

void UDinkGameplay::ApplyPhysicalPlayCollision(int32 Screen)
{
	// Only with the layer on and a relaxed box or an open tile on this screen: otherwise nothing is called, so the 1997 collision
	// path is untouched.
	if (!IsPhysicalPlayPartOn(EPhysicalPlayPart::Collision) || RequiresOriginalHardnessScreen(Screen)) return;
	if (!PhysicalPlay.Relaxed.Contains(Screen) && !PhysicalPlay.OpenTiles.Contains(Screen) && !PhysicalPlay.Sealed.Contains(Screen)) return;
	// review of 22 Nov 2026, finding 4: what a screen entry costs (the collision rebuilds), logged per entry
	const double Begin = FPlatformTime::Seconds();
	CheckRelaxedBlockers(Screen);
	SyncGreyboxHardness(Screen);
	const double Solid = FPlatformTime::Seconds();
	if (HasOpenTilesForPlayer(Screen) || HasSealsForPlayer(Screen)) SyncGreyboxLowHardness(Screen);
	UE_LOG(LogDinkNarrative, Display, TEXT("DINK PHYSICAL PLAY ENTRY: screen %d collision %.1f ms (solid %.1f, low %.1f)"), Screen,
		(FPlatformTime::Seconds() - Begin) * 1000.0, (Solid - Begin) * 1000.0, (FPlatformTime::Seconds() - Solid) * 1000.0);
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
	if (AuthoredGeometryMatches(*Dink, *Target, Kind)) return true;
	// a pickup no one can stand at, or a target no one can stand within reach of: its 1997 box decides (RunThroughTouchDamageList,
	// RunThroughTagList), which the bot aimed by
	if (bHit) return DrawnTargetUnreachableInPlay(*Target, AuthoredInteraction.AttackReachCm * FMath::Max(Dink->GetProp(TEXT("range")), 28) / 28.0 * 0.8);
	return Target->GetProp(TEXT("touch_damage")) == -1 && PickupUnreachableInPlay(*Target);
}

bool UDinkGameplay::PickupUnreachableInPlay(const FDinkSprite& Pickup) const
{
	return DrawnTargetUnreachableInPlay(Pickup, AuthoredInteraction.PickupReachCm * 0.5);
}

bool UDinkGameplay::DrawnTargetUnreachableInPlay(const FDinkSprite& Pickup, double MaxGapCm) const
{
	UDinkDirector* D = Director();
	const FDinkSprite* Dink = D ? D->FindSprite(1) : nullptr;
	const AActor* DinkActor = Dink ? Dink->Actor.Get() : nullptr;
	const AActor* Item = Pickup.Actor.Get();
	const UCapsuleComponent* Capsule = DinkActor ? DinkActor->FindComponentByClass<UCapsuleComponent>() : nullptr;
	UWorld* World = DinkActor ? DinkActor->GetWorld() : nullptr;
	FVector Near;
	if (!Capsule || !Item || !World || !DrawnClosestPoint(Pickup.Handle, Capsule->GetComponentLocation(), Near)) return false;
	const double Radius = Capsule->GetScaledCapsuleRadius();
	const FCollisionShape Shape = FCollisionShape::MakeCapsule(Radius - 2.0, Capsule->GetScaledCapsuleHalfHeight() - 2.0);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkPickupReachable), false, DinkActor);
	Params.AddIgnoredActor(Item);
	const FVector Base = Capsule->GetComponentLocation();
	// Review of the delta (23 Nov 2026, A): never through a wall. Something solid between Dink and the target (solid hardness or a
	// drawn hull, at his height) means it is reachable by walking round, not by the 1997 box from here: no blow or pickup through a
	// fence, pine or wall. Low hardness (a ditch, water) ignores Visibility, so SCR_190's duck-bugs in the ditch still count.
	{
		const FVector To(Near.X, Near.Y, Base.Z);
		FCollisionQueryParams Sight(SCENE_QUERY_STAT(DinkUnreachableSight), false, DinkActor);
		Sight.AddIgnoredActor(Item);
		// (a hull or mesh the target itself stands in, a potion drawn into a decoration, is no wall between them)
		const auto Between = [&](const FHitResult& H)
		{
			const UPrimitiveComponent* C = H.GetComponent();
			if (!C || C->ComponentHasTag(TEXT("DinkCreatureBodyBlocker")) || H.Distance + 1.f >= FVector::Distance(Base, To)) return false;
			const FBox Own = C->Bounds.GetBox();
			return !(Near.X >= Own.Min.X - 5.0 && Near.X <= Own.Max.X + 5.0 && Near.Y >= Own.Min.Y - 5.0 && Near.Y <= Own.Max.Y + 5.0);
		};
		TArray<FHitResult> Walls;
		World->LineTraceMultiByChannel(Walls, Base, To, ECC_Visibility, Sight);
		for (const FHitResult& Wall : Walls) if (Wall.bBlockingHit && Between(Wall)) return false;
		TArray<FHitResult> Hulls;
		World->LineTraceMultiByObjectType(Hulls, Base, To, FCollisionObjectQueryParams(DinkCollision::PlayerBlock), Sight);
		for (const FHitResult& Hull : Hulls) if (Between(Hull)) return false;
	}
	for (const double Gap : { 2.0, MaxGapCm * 0.5, MaxGapCm })
	{
		for (int32 K = 0; K < 16; ++K)
		{
			const FVector Dir = FVector::ForwardVector.RotateAngleAxis(22.5 * K, FVector::UpVector);
			const FVector Spot(Near.X + Dir.X * (Radius + Gap), Near.Y + Dir.Y * (Radius + Gap), Base.Z);
			if (World->OverlapBlockingTestByChannel(Spot, Capsule->GetComponentQuat(), ECC_Pawn, Shape, Params)) continue;
			// and reached by walking straight from where Dink stands (an overlap does not see the screen's hardness trimesh, a sweep
			// does: a spot inside a ditch's low collision is no spot)
			FHitResult Walk;
			if (World->SweepSingleByChannel(Walk, Base, Spot, Capsule->GetComponentQuat(), ECC_Pawn, Shape, Params) && Walk.bBlockingHit &&
				(Walk.bStartPenetrating || FVector::Dist2D(Walk.Location, Spot) > 5.0)) continue;
			// nothing solid between the spot and the pickup (a wall, a drawn hull)
			const FVector To(Near.X, Near.Y, Base.Z);
			FHitResult Wall;
			if (World->LineTraceSingleByObjectType(Wall, Spot, To, FCollisionObjectQueryParams(DinkCollision::PlayerBlock), Params) ||
				World->LineTraceSingleByChannel(Wall, Spot, To, ECC_Visibility, Params)) continue;
			return false;
		}
	}
	return true;
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
	/** The blocker follows its body's bounds when they change by more than this (cm). */
	constexpr double BodyBlockerResizeCm = 4.0;

	/** The actor carries an authored body (creatures.json / characters.json): a Pawn-profile shape that already stops Dink. */
	bool HasAuthoredPawnBody(const AActor& Actor)
	{
		TInlineComponentArray<UShapeComponent*> Shapes(&Actor);
		for (const UShapeComponent* Shape : Shapes)
		{
			if (Shape->IsRegistered() && Shape->ComponentHasTag(TEXT("DinkAuthoredInteraction")) && Shape->GetCollisionEnabled() != ECollisionEnabled::NoCollision &&
				Shape->GetCollisionResponseToChannel(ECC_Pawn) == ECR_Block)
			{
				return true;
			}
		}
		return false;
	}

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
		// the capsule's circle against the box's plan (review of 22 Nov 2026, nit 12: a per-axis test counted a capsule off a corner)
		const double DX = FMath::Max(0.0, FMath::Abs(Local.X) - Extent.X), DY = FMath::Max(0.0, FMath::Abs(Local.Y) - Extent.Y);
		return FMath::Sqrt(DX * DX + DY * DY) < R - In && FMath::Abs(Local.Z) < Extent.Z + H - In;
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
			// living, drawn creatures only: a dead one (brain 0, its corpse), a hidden one or an untouchable one (nohit: a frozen
			// cut-scene body that must not seal a doorway) blocks nothing
			// P8 (playtest 20 Nov 2026): a still class-bound body that is solid in 1997 (brain 0, sp_hard 0: the seated King of the
			// ending, S070_P03) blocks at its drawn body too; its 1997 box is smaller than the drawn King and throne, so Dink walked into him
			// (only the class rows listed in physical_play.ini StillBodies: a still cut-scene body elsewhere must not stand in Dink's way)
			const UDinkCreatureClassComponent* StillClass = A && S.GetProp(TEXT("brain")) == 0 && S.GetProp(TEXT("hard"), 1) == 0 ? UDinkCreatureSubsystem::FindClassBody(A) : nullptr;
			const bool bStillSolid = StillClass && PhysicalPlay.StillBodies.Contains(StillClass->GetClassId());
			// a body 1997 parks outside the playfield (A13) is drawn nowhere and blocks nothing
			if (Pair.Key == 1 || !A || !S.bActive || A->IsHidden() || IsParked(A) || (S.GetProp(TEXT("brain")) == 0 && !bStillSolid) || S.GetProp(TEXT("nohit")) != 0) continue;
			// Review of PR #160, finding 1: the creatures of creatures.json's placement rows (tag DinkCreature) AND every class-bound
			// creature (its UDinkCreatureClassComponent: script-made and placed foes, ducks, pigs), but not people (brain 16, the
			// smart people of dink.cpp; their 1997 boxes are their own) nor a placement row whose authored body boxes (Pawn profile,
			// DinkAuthoredInteraction: what its touches and hits use) already stop Dink at its drawn body (finding 4).
			const bool bClassBody = UDinkCreatureSubsystem::FindClassBody(A) != nullptr;
			if (!bClassBody && !A->ActorHasTag(TEXT("DinkCreature"))) continue;
			if (bStillSolid && !bClassBody) continue;
			if (S.GetProp(TEXT("brain")) == 16 || HasAuthoredPawnBody(*A)) continue;
			// Review of 22 Nov 2026, finding 7: a body that may stand still in a doorway or on a bridge for good blocks nothing: a frozen
			// one (sp_freeze, a cut-scene) and a harmless one (no touch damage, no attack, not after Dink: a duck, a pig). A foe
			// moves on to fight him, so its body never seals a way.
			if (!bStillSolid && (S.bFrozen || (S.GetProp(TEXT("touch_damage")) <= 0 && S.GetProp(TEXT("base_attack"), -1) == -1 && S.GetProp(TEXT("target")) != 1))) continue;
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
				// landforms (review of 22 Nov 2026, finding 2): collision stays on the flat 1997 floor with Dink's capsule
				Box->ComponentTags.Add(DinkLandforms::FlatTag);
				Box->SetupAttachment(Body);
				A->AddInstanceComponent(Box);
				Box->RegisterComponent();
				CreatureBodyBlockers.Add(Box);
			}
			else if (Box->GetAttachParent() != Body)
			{
				Box->AttachToComponent(Body, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
			}
			// The body's own plan (component space, so it turns with the body: the box the layer's touches and hits use, DrawnBodyBox),
			// inset, and at least BodyBlockerMinHeightCm tall. Set again only when it changes by more than BodyBlockerResizeCm (review
			// finding 8: a skinned body's bounds follow its pose; a physics shape rebuilt every tick for every creature is waste).
			const FBoxSphereBounds Local = Body->CalcBounds(FTransform::Identity);
			const FVector Scale = Body->GetComponentScale().GetAbs().ComponentMax(FVector(0.01));
			const auto Inset = [](double HalfLocal, double ScaleAxis)
			{
				const double World = HalfLocal * ScaleAxis;
				return (World - FMath::Min(BodyBlockerInsetCm, World * 0.5)) / ScaleAxis;
			};
			const double HalfZ = FMath::Max(Local.BoxExtent.Z, BodyBlockerMinHeightCm * 0.5 / Scale.Z);
			const FVector Extent(Inset(Local.BoxExtent.X, Scale.X), Inset(Local.BoxExtent.Y, Scale.Y), HalfZ);
			// in the flat frame: the drawn body is lifted by the landforms, its blocker is not (KeepCollisionFlat holds FlatTag boxes there)
			const FVector Centre(Local.Origin.X, Local.Origin.Y, Local.Origin.Z - Local.BoxExtent.Z + HalfZ - DinkLandforms::GeometryLiftCm(Body) / Scale.Z);
			if (!Box->GetUnscaledBoxExtent().Equals(Extent, BodyBlockerResizeCm / Scale.GetMax()) || !Box->GetRelativeLocation().Equals(Centre, BodyBlockerResizeCm / Scale.GetMax()))
			{
				Box->SetBoxExtent(Extent, false);
				Box->SetRelativeLocation(Centre);
			}
			if (!Box->GetRelativeRotation().IsNearlyZero()) Box->SetRelativeRotation(FRotator::ZeroRotator);
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
