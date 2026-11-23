#include "DinkGameplay.h"
#include "DinkDirector.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "DinkCollision.h"
#include "DinkLandforms.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "Components/ShapeComponent.h"
#include "DinkCreatureSubsystem.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

FString FDinkAuthoredInteractionSettings::DefaultPath()
{
	return FPaths::ProjectContentDir() / TEXT("Dink/Data/Interaction/authored.ini");
}

void FDinkAuthoredInteractionSettings::Load()
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *DefaultPath())) { return; }
	TArray<FString> Lines;
	Text.ParseIntoArrayLines(Lines);
	for (FString Line : Lines)
	{
		Line.TrimStartAndEndInline();
		FString Key, Value;
		if (Line.IsEmpty() || Line.StartsWith(TEXT(";")) || Line.StartsWith(TEXT("[")) || !Line.Split(TEXT("="), &Key, &Value)) { continue; }
		Key.TrimStartAndEndInline();
		Value.TrimStartAndEndInline();
		const double Number = FMath::Clamp(FCString::Atod(*Value), 0.0, 500.0);
		if (Key == TEXT("AttackReachCm")) { AttackReachCm = Number; }
		else if (Key == TEXT("AttackHalfWidthCm")) { AttackHalfWidthCm = Number; }
		else if (Key == TEXT("TalkReachCm")) { TalkReachCm = Number; }
		else if (Key == TEXT("TalkHalfWidthCm")) { TalkHalfWidthCm = Number; }
		else if (Key == TEXT("PickupReachCm")) { PickupReachCm = Number; }
		else if (Key == TEXT("ElevatedPickupReachCm")) { ElevatedPickupReachCm = Number; }
		else if (Key == TEXT("ElevatedPickupMinHeightCm")) { ElevatedPickupMinHeightCm = Number; }
		else if (Key == TEXT("PickupShoulderHeightCm")) { PickupShoulderHeightCm = Number; }
		else if (Key == TEXT("ContactReachCm")) { ContactReachCm = Number; }
	}
}

bool UDinkGameplay::UsesAuthoredGeometry(const FDinkSprite& Attacker, const FDinkSprite& Target) const
{
	// Worldless/virtual parity tests retain the original pixel rules. Headless PIE still has
	// real physics geometry and uses the same checks as a rendered game.
	const AActor* From = Attacker.Actor.Get();
	const AActor* To = Target.Actor.Get();
	return From && To && From->GetWorld() && From->GetWorld() == To->GetWorld() && (To->ActorHasTag(TEXT("DinkAuthoredArt")) || HasHardnessFitInstance(Target));
}

FDinkDrawnBody UDinkGameplay::DrawnBodyBox(const UPrimitiveComponent& Component)
{
	// CalcBounds with the identity: the mesh's own bounds (a skeletal mesh: its asset bounds, not this frame's world box)
	const FBoxSphereBounds Local = Component.CalcBounds(FTransform::Identity);
	const FTransform T = Component.GetComponentTransform();
	const FVector Scale = T.GetScale3D().GetAbs();
	FDinkDrawnBody Body;
	Body.Frame = FTransform(T.GetRotation(), T.TransformPosition(Local.Origin));
	Body.Extent = Local.BoxExtent * Scale;
	Body.LiftCm = DinkLandforms::GeometryLiftCm(&Component);
	return Body;
}

bool UDinkGameplay::CreatureDrawnBody(const AActor& Actor, FDinkDrawnBody& Out)
{
	// The authored body boxes of a creatures.json placement (what its touches and hits use), else its skinned body, else a visible mesh.
	FBox Union(ForceInit);
	FTransform Frame = FTransform::Identity;
	bool bAuthored = false;
	float AuthoredLift = 0.f;
	TInlineComponentArray<UPrimitiveComponent*> Components(&Actor);
	for (const UPrimitiveComponent* C : Components)
	{
		const UBoxComponent* Box = Cast<UBoxComponent>(C);
		if (!Box || !Box->IsRegistered() || !Box->ComponentHasTag(TEXT("DinkAuthoredInteraction"))) continue;
		if (!bAuthored) { Frame = FTransform(Box->GetComponentQuat(), Box->GetComponentLocation()); bAuthored = true; AuthoredLift = DinkLandforms::GeometryLiftCm(Box); }
		const FVector E = Box->GetScaledBoxExtent();
		for (int32 I = 0; I < 8; ++I)
		{
			const FVector Corner(I & 1 ? E.X : -E.X, I & 2 ? E.Y : -E.Y, I & 4 ? E.Z : -E.Z);
			Union += Frame.InverseTransformPositionNoScale(Box->GetComponentTransform().TransformPositionNoScale(Corner));
		}
	}
	if (bAuthored && Union.IsValid)
	{
		Out.Frame = FTransform(Frame.GetRotation(), Frame.TransformPositionNoScale(Union.GetCenter()));
		Out.Extent = Union.GetExtent();
		Out.LiftCm = AuthoredLift;
		return true;
	}
	const UPrimitiveComponent* Static = nullptr;
	for (const UPrimitiveComponent* C : Components)
	{
		if (!C->IsRegistered() || !C->IsVisible() || C->bHiddenInGame || C->ComponentHasTag(TEXT("DinkCreatureBodyBlocker")) || C->ComponentHasTag(TEXT("DinkCreatureCorpse"))) continue;
		if (C->IsA<USkinnedMeshComponent>()) { Out = DrawnBodyBox(*C); return true; }
		if (!Static && Cast<UStaticMeshComponent>(C) && Cast<UStaticMeshComponent>(C)->GetStaticMesh()) Static = C;
	}
	if (Static) { Out = DrawnBodyBox(*Static); return true; }
	return false;
}

bool UDinkGameplay::CreatureReachMatches(const FDinkSprite& Attacker, const FDinkSprite& Target, double* OutDistanceCm, bool* OutSightBlocked) const
{
	if (OutSightBlocked) *OutSightBlocked = false;
	// Part CreatureReach (owner decision 19 Nov 2026: drawn contact for both sides). A creature's blow lands when Dink's capsule meets
	// the region in front of its drawn body: from its back to its front face plus its reach (AttackReachCm x max(range, 28) / 28) along
	// its 1997 facing, as wide as the body plus AttackHalfWidthCm on each side. Review of PR #160, finding 5: the reach starts at the
	// body's depth along the facing (not its longest half-size: a Bonca turned sideways swung at air 80 cm past its front), Dink inside
	// or against the body counts, and a wide body (stone giant, dragon) reaches across its whole front. The target is Dink's capsule
	// (never a held item's mesh). Something solid between the two (sight from the body's centre) stops the blow.
	const AActor* FromActor = Attacker.Actor.Get();
	const AActor* DinkActor = Target.Actor.Get();
	const UCapsuleComponent* Capsule = DinkActor ? DinkActor->FindComponentByClass<UCapsuleComponent>() : nullptr;
	UDinkDirector* D = Director();
	FDinkDrawnBody Body;
	if (!FromActor || !Capsule || !D || !CreatureDrawnBody(*FromActor, Body)) return false;
	static const FIntPoint Step[10] = { {0,0}, {-1,1}, {0,1}, {1,1}, {-1,0}, {0,0}, {1,0}, {-1,-1}, {0,-1}, {1,-1} };
	const int32 Dir = FMath::Clamp(Attacker.Dir, 0, 9);
	FVector A, B;
	if (Step[Dir] == FIntPoint::ZeroValue || !D->PixelToWorld(Attacker.Screen, Attacker.X, Attacker.Y, A) ||
		!D->PixelToWorld(Attacker.Screen, Attacker.X + Step[Dir].X * 20.0, Attacker.Y + Step[Dir].Y * 20.0, B)) return false;
	const FVector Forward = (B - A).GetSafeNormal2D();
	if (Forward.IsNearlyZero()) return false;
	const FVector Left(-Forward.Y, Forward.X, 0.0);
	// the body box's support along the facing and across it
	const FVector AxisX = Body.Frame.GetUnitAxis(EAxis::X), AxisY = Body.Frame.GetUnitAxis(EAxis::Y), AxisZ = Body.Frame.GetUnitAxis(EAxis::Z);
	const auto Support = [&](const FVector& Dir2) { return FMath::Abs(FVector::DotProduct(AxisX, Dir2)) * Body.Extent.X + FMath::Abs(FVector::DotProduct(AxisY, Dir2)) * Body.Extent.Y + FMath::Abs(FVector::DotProduct(AxisZ, Dir2)) * Body.Extent.Z; };
	const double Depth = Support(Forward), Width = Support(Left);
	const int32 Range = Attacker.GetProp(TEXT("range"));
	const double Scale = FMath::Max(Range, 28) / 28.0;
	const double Reach = AuthoredInteraction.AttackReachCm * Scale;
	const double HalfWidth = Width + AuthoredInteraction.AttackHalfWidthCm * Scale;
	// landforms (review of 22 Nov 2026, finding 2): the drawn body stands on the drawn ground, Dink's capsule and the hardness on the
	// flat 1997 floor; the body is taken down to the flat floor for the height test and the sight line
	// (the lift of the component the body came from: authored body boxes are held flat already; review of the delta, 23 Nov, B)
	const FVector Centre = Body.Frame.GetLocation() - FVector(0.0, 0.0, Body.LiftCm);
	const FVector P = Capsule->GetComponentLocation();
	const double F = FVector::DotProduct(P - Centre, Forward), L = FVector::DotProduct(P - Centre, Left);
	// the capsule's circle against the rectangle F in [-Depth, Depth + Reach], |L| <= HalfWidth
	const double DF = F < -Depth ? -Depth - F : F > Depth + Reach ? F - (Depth + Reach) : 0.0;
	const double DL = FMath::Max(0.0, FMath::Abs(L) - HalfWidth);
	const double Gap = FMath::Sqrt(DF * DF + DL * DL) - Capsule->GetScaledCapsuleRadius();
	if (Gap > 0.0) return false;
	// heights overlap (a flyer far above, Dink on a ledge)
	const double BodyBottom = Centre.Z - Support(FVector::UpVector), BodyTop = Centre.Z + Support(FVector::UpVector);
	const double DinkBottom = P.Z - Capsule->GetScaledCapsuleHalfHeight(), DinkTop = P.Z + Capsule->GetScaledCapsuleHalfHeight();
	if (DinkBottom > BodyTop + Reach || DinkTop < BodyBottom - Reach) return false;
	// sight: solid hardness and the drawn walls (player-only hulls), not other creatures. Review of 22 Nov 2026, finding 3: the same
	// line as Dink's blow at it (his capsule's centre to the closest point of its drawn body), so neither side hits through a trunk
	// the other cannot hit through (a head showing past a pine)
	UWorld* World = FromActor->GetWorld();
	if (!World) return false;
	FCollisionQueryParams Params(TEXT("DinkCreatureReach"), false, FromActor);
	Params.AddIgnoredActor(DinkActor);
	FHitResult Wall;
	const FVector LocalP = Body.Frame.InverseTransformPositionNoScale(P + FVector(0.0, 0.0, Body.LiftCm));
	FVector Closest = Body.Frame.TransformPositionNoScale(FBox(-Body.Extent, Body.Extent).GetClosestPointTo(LocalP)) - FVector(0.0, 0.0, Body.LiftCm);
	const FVector SightTo(P.X, P.Y, FMath::Clamp(P.Z, BodyBottom + 30.0, FMath::Max(BodyBottom + 30.0, BodyTop)));
	const FVector SightFrom(Closest.X, Closest.Y, SightTo.Z);
	const auto Blocked = [&]()
	{
		if (FVector::DistSquared2D(SightFrom, SightTo) < 1.0) return false;
		if (World->LineTraceSingleByChannel(Wall, SightFrom, SightTo, ECC_Visibility, Params) && Wall.Distance + 1.f < FVector::Distance(SightFrom, SightTo))
		{
			const UPrimitiveComponent* C = Wall.GetComponent();
			if (!(C && C->GetOwner() && (C->GetOwner()->ActorHasTag(TEXT("DinkCreature")) || UDinkCreatureSubsystem::FindClassBody(C->GetOwner())))) return true;
		}
		TArray<FHitResult> Hulls;
		FCollisionQueryParams SimpleParams = Params;
		SimpleParams.bTraceComplex = false;
		if (World->LineTraceMultiByObjectType(Hulls, SightFrom, SightTo, FCollisionObjectQueryParams(DinkCollision::PlayerBlock), SimpleParams))
		{
			for (const FHitResult& Hull : Hulls)
			{
				const UPrimitiveComponent* C = Hull.GetComponent();
				if (C && !C->ComponentHasTag(TEXT("DinkCreatureBodyBlocker")) && Hull.Distance + 1.f < FVector::Distance(SightFrom, SightTo)) return true;
			}
		}
		return false;
	};
	if (Blocked())
	{
		if (OutSightBlocked) *OutSightBlocked = true;
		return false;
	}
	if (OutDistanceCm) *OutDistanceCm = FMath::Max(0.0, F - Depth);
	UE_LOG(LogTemp, Log, TEXT("DINK CREATURE REACH: sprite %d dir %d meets Dink: along %.0f (depth %.0f reach %.0f) across %.0f (half width %.0f), body %.0f x %.0f cm"),
		Attacker.Handle, Dir, F, Depth, Reach, L, HalfWidth, Body.Extent.X * 2, Body.Extent.Y * 2);
	return true;
}

bool UDinkGameplay::AuthoredGeometryMatches(const FDinkSprite& Attacker, const FDinkSprite& Target,
	EAuthoredInteraction Kind, double* OutDistanceCm) const
{
	AActor* FromActor = Attacker.Actor.Get();
	AActor* TargetActor = Target.Actor.Get();
	if (!FromActor || !TargetActor || TargetActor->IsHidden()) { return false; }
	const UCapsuleComponent* Body = FromActor->FindComponentByClass<UCapsuleComponent>();
	const float BodyRadius = Body ? Body->GetScaledCapsuleRadius() : 28.f;
	const float BodyHalfHeight = Body ? Body->GetScaledCapsuleHalfHeight() : 96.f;
	const FVector From = Body ? Body->GetComponentLocation() : FromActor->GetActorLocation();
	const FVector Forward = FromActor->GetActorForwardVector().GetSafeNormal2D();
	// Physical play layer, a creature's blow at Dink (part CreatureReach): its own test (review of PR #160, finding 5)
	if (Kind == EAuthoredInteraction::Hit && Attacker.Handle != 1 && Target.Handle == 1 && UsesPhysicalPlay(Attacker, Target, Kind))
	{
		return CreatureReachMatches(Attacker, Target, OutDistanceCm);
	}
	FVector Start = From, End = From;
	float Radius = BodyRadius, HalfHeight = BodyHalfHeight;
	const bool bDirectional = Kind == EAuthoredInteraction::Hit || Kind == EAuthoredInteraction::Talk;
	if (bDirectional)
	{
		const double Scale = Kind == EAuthoredInteraction::Hit && Attacker.GetProp(TEXT("range")) > 0
			? Attacker.GetProp(TEXT("range")) / 28.0 : 1.0;
		const double Reach = Kind == EAuthoredInteraction::Hit ? AuthoredInteraction.AttackReachCm * Scale : AuthoredInteraction.TalkReachCm;
		Radius = FMath::Max(1.f, float(Kind == EAuthoredInteraction::Hit ? AuthoredInteraction.AttackHalfWidthCm * Scale : AuthoredInteraction.TalkHalfWidthCm));
		HalfHeight = FMath::Max(Radius, BodyHalfHeight + (Kind == EAuthoredInteraction::Hit ? -10.f : 20.f));
		// The whole swept shape begins in front of the body. A facing-away attack cannot
		// hit a prop behind the player merely because the original hardbox contains him.
		Start += Forward * (BodyRadius + Radius);
		End += Forward * (BodyRadius + FMath::Max(Reach, double(Radius * 2)) - Radius);
	}
	else
	{
		const double Reach = Kind == EAuthoredInteraction::Touch && Target.GetProp(TEXT("touch_damage")) == -1
			? AuthoredInteraction.PickupReachCm : AuthoredInteraction.ContactReachCm;
		Radius += float(Reach);
		HalfHeight += float(Reach);
		End.Z += 0.1; // retain initial-overlap hits with a nonzero sweep direction
	}
	UPrimitiveComponent* Fitted=FindHardnessFitPrimitive(Target);
    if(HasHardnessFitInstance(Target)&&!Fitted)return false;
	TArray<UPrimitiveComponent*, TInlineAllocator<4>> Geometry;
	if(Fitted)Geometry.Add(Fitted);
	TInlineComponentArray<UPrimitiveComponent*> Components(TargetActor);
	for (UPrimitiveComponent* Component : Components)
	{
        if(Fitted)break;
		if (Component->IsRegistered() && Component->ComponentHasTag(TEXT("DinkAuthoredInteraction")) &&
			(!Component->bHiddenInGame || Component->IsA<UShapeComponent>()))
		{
			Geometry.Add(Component);
		}
	}
	// Props use the actual visible mesh component, including its authored offset from
	// the legacy placement origin. NPCs explicitly tag their body capsule instead.
	if (Geometry.IsEmpty())
	{
		if (const ADinkPlaceholderActor* Placeholder = Cast<ADinkPlaceholderActor>(TargetActor))
		{
			if (Placeholder->Card && !Placeholder->Card->bHiddenInGame && Placeholder->Card->IsVisible() && Placeholder->Card->GetStaticMesh())
			{
				Geometry.Add(Placeholder->Card);
			}
			else if (UsesPhysicalPlay(Attacker, Target, Kind))
			{
				// physical play layer: the card is hidden, the placement is drawn by family art or a creature's skinned body
				for (UPrimitiveComponent* Component : Components)
				{
					if (Component->IsRegistered() && Component->IsVisible() && !Component->bHiddenInGame &&
						((Cast<UStaticMeshComponent>(Component) && Cast<UStaticMeshComponent>(Component)->GetStaticMesh()) || Component->IsA<USkinnedMeshComponent>()))
					{
						Geometry.Add(Component);
					}
				}
			}
		}
		else
		{
			// physical play layer (Codex review of PR #160): a class-bound script creature hides its markers and is drawn by its
			// skinned body only, which must count too
			const bool bSkinned = UsesPhysicalPlay(Attacker, Target, Kind);
			for (UPrimitiveComponent* Component : Components)
			{
				if (UStaticMeshComponent* Mesh = Cast<UStaticMeshComponent>(Component); Mesh && Mesh->GetStaticMesh() && Mesh->IsVisible() && !Mesh->bHiddenInGame)
				{
					Geometry.Add(Mesh);
				}
				else if (bSkinned && Component->IsA<USkinnedMeshComponent>() && Component->IsRegistered() && Component->IsVisible() && !Component->bHiddenInGame)
				{
					Geometry.Add(Component);
				}
			}
		}
	}
	const bool bPhysicalPlay = UsesPhysicalPlay(Attacker, Target, Kind);
	double BestDistance = TNumericLimits<double>::Max();
	// Landforms are a visual layer: a drawn target stands on the ground, the body's collision (the player's capsule, held
	// body shapes) on the 1997 floor. Query each target in its own frame (the body raised by the target's lift) so the
	// result is the flat world's.
	const float FromLift = Body ? DinkLandforms::GeometryLiftCm(Body) : DinkLandforms::ActorLiftCm(FromActor);
	const FVector FlatFrom = From, FlatStart = Start, FlatEnd = End;
	for (UPrimitiveComponent* Component : Geometry)
	{
		const FVector Lift(0.0, 0.0, DinkLandforms::GeometryLiftCm(Component) - FromLift);
		const FVector QFrom = FlatFrom + Lift, QStart = FlatStart + Lift, QEnd = FlatEnd + Lift;
		const bool bElevatedPickup = Kind == EAuthoredInteraction::Touch && Target.GetProp(TEXT("touch_damage")) == -1 &&
			Component->Bounds.GetBox().Min.Z - (QFrom.Z - BodyHalfHeight) >= AuthoredInteraction.ElevatedPickupMinHeightCm;
		const float QueryRadius = bElevatedPickup ? BodyRadius + float(AuthoredInteraction.ElevatedPickupReachCm) : Radius;
		// Extend a hand over furniture without extending vertical reach by the same amount.
		const FCollisionShape Shape = FCollisionShape::MakeCapsule(QueryRadius, FMath::Max(HalfHeight, QueryRadius));
		FHitResult Hit;
		FVector Surface;
		if (bPhysicalPlay && (Component->IsA<USkinnedMeshComponent>() || !Component->GetBodyInstance() || !Component->GetBodyInstance()->IsValidBodyInstance()))
		{
			// a skinned creature body or a mesh without physics (the physical play layer's drawn bodies): its OWN box (the mesh's
			// local bounds in the component's frame, so it turns with the body; never the world bounds, which a turned, long body or
			// an animation-extended skeletal bound makes metres too wide), grown by the query's radius, against the swept segment
			const FDinkDrawnBody Drawn = DrawnBodyBox(*Component);
			const FVector LocalStart = Drawn.Frame.InverseTransformPositionNoScale(QStart);
			const FVector LocalEnd = Drawn.Frame.InverseTransformPositionNoScale(QEnd);
			const FBox Grown = FBox(-Drawn.Extent, Drawn.Extent).ExpandBy(FVector(QueryRadius, QueryRadius, FMath::Max(HalfHeight, QueryRadius)));
			FVector HitLocation, HitNormal;
			float HitTime = 0.f;
			const bool bInside = Grown.IsInside(LocalStart);
			if (!bInside && !FMath::LineExtentBoxIntersection(Grown, LocalStart, LocalEnd, FVector::ZeroVector, HitLocation, HitNormal, HitTime)) { continue; }
			Surface = Drawn.Frame.TransformPositionNoScale(FBox(-Drawn.Extent, Drawn.Extent).GetClosestPointTo(Drawn.Frame.InverseTransformPositionNoScale(QFrom)));
		}
		else
		{
			if (!Component->SweepComponent(Hit, QStart, QEnd, FQuat::Identity, Shape, Component->IsA<UStaticMeshComponent>())) { continue; }
			Surface = Hit.ImpactPoint;
			if (Hit.bStartPenetrating) { Surface = Component->Bounds.GetBox().GetClosestPointTo(QFrom); }
		}
		if (Kind == EAuthoredInteraction::Push && FVector::DotProduct((Surface - QFrom).GetSafeNormal2D(), Forward) < 0.0) { continue; }
		// A prop across a wall must not answer a nearby hit/talk or be collected through it.
		FVector SightOrigin = QFrom;
		if (bElevatedPickup) { SightOrigin.Z = QFrom.Z - BodyHalfHeight + AuthoredInteraction.PickupShoulderHeightCm; }
		FCollisionQueryParams Params(TEXT("DinkAuthoredInteraction"), true, FromActor);
		FHitResult Blocker;
		if (UWorld* World = FromActor->GetWorld(); World && World->LineTraceSingleByChannel(Blocker, SightOrigin, Surface, ECC_Visibility, Params) &&
			Blocker.GetActor() != TargetActor && Blocker.GetComponent()!=Fitted && Blocker.Distance + 1.f < FVector::Distance(SightOrigin, Surface)) { continue; }
		// physical play layer (Codex review of PR #160): a relaxed box no longer stands in the hard-solid mesh, so the drawn thing's
		// player-only blocker (which ignores Visibility) is the wall a touch must not pass through
		if (bPhysicalPlay)
		{
			// Review of PR #160, finding 3: PR #129's hulls are convex-only procedural meshes that answer SIMPLE queries only (a
			// complex trace passes through them), so this trace is simple. The creature body boxes (A21) on the same channel are
			// not walls: a creature between Dink and a pickup or a second foe does not shield it (1997 hits every target in the box).
			FCollisionQueryParams SimpleParams = Params;
			SimpleParams.bTraceComplex = false;
			TArray<FHitResult> Walls;
			bool bWall = false;
			if (UWorld* World = FromActor->GetWorld(); World && World->LineTraceMultiByObjectType(Walls, SightOrigin, Surface, FCollisionObjectQueryParams(DinkCollision::PlayerBlock), SimpleParams))
			{
				const double Length = FVector::Distance(SightOrigin, Surface);
				for (const FHitResult& Wall : Walls)
				{
					const UPrimitiveComponent* C = Wall.GetComponent();
					if (Wall.GetActor() == TargetActor || (C && C->ComponentHasTag(TEXT("DinkCreatureBodyBlocker"))) || Wall.Distance + 1.f >= Length) continue;
					bWall = true;
					break;
				}
			}
			if (bWall) { continue; }
		}
		BestDistance = FMath::Min(BestDistance, FVector::Dist2D(QFrom, Surface));
	}
	if (OutDistanceCm) { *OutDistanceCm = BestDistance; }
	return BestDistance < TNumericLimits<double>::Max();
}

bool UDinkGameplay::AuthoredActorMoveBlocked(const FDinkSprite& Sprite, const FIntPoint& From,
    const FIntPoint& To, FQuat* OutFacing) const
{
    AActor* Actor = Sprite.Actor.Get();
    UDinkDirector* D = Director();
    if (!Actor || (!Actor->ActorHasTag(TEXT("DinkHumanoid")) && !Actor->ActorHasTag(TEXT("DinkCreature"))) || Sprite.bMoving || !D) return false;
    FVector A, B;
    if (!D->PixelToWorld(Sprite.Screen, From.X, From.Y, A) || !D->PixelToWorld(Sprite.Screen, To.X, To.Y, B)) return false;
    const FQuat Current = Actor->GetActorQuat();
    FQuat Wanted = Current;
    D->GetSpriteFacingRotation(Sprite, Wanted);
    if (OutFacing) *OutFacing = Wanted;
    const bool Turning = Wanted.AngularDistance(Current) > 1.e-4;
    TInlineComponentArray<UShapeComponent*> Bodies(Actor);
    FCollisionQueryParams Params(TEXT("DinkAuthoredActorMovement"), true, Actor);
    // NPC and creature bodies: everything the default query blocks on, but not the player-only blockers (a drawn boulder's
    // outline stops Dink, never a pillbug or a villager: their 1997 hardness is unchanged).
    const FCollisionResponseParams BodyResponses = DinkCollision::IgnorePlayerBlockers();
    auto ShapeFor = [](UShapeComponent* Body, FCollisionShape& Shape)
    {
        if (!Body->IsRegistered() || !Body->ComponentHasTag(TEXT("DinkAuthoredInteraction")) || Body->GetCollisionEnabled() == ECollisionEnabled::NoCollision) return false;
        if (const UCapsuleComponent* Capsule = Cast<UCapsuleComponent>(Body))
            Shape = FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(), FMath::Max(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight() - 2.f));
        else if (const UBoxComponent* Box = Cast<UBoxComponent>(Body))
        {
            FVector Extent = Box->GetScaledBoxExtent();
            Extent.Z = FMath::Max(1., Extent.Z - 2.);
            Shape = FCollisionShape::MakeBox(Extent);
        }
        else return false;
        return true;
    };
    auto PoseBlocked = [&](const FQuat& Facing, bool RejectNewTurnOverlap)
    {
        const FQuat Turn = Facing * Current.Inverse();
        for (UShapeComponent* Body : Bodies)
        {
            FCollisionShape Shape;
            if (!ShapeFor(Body, Shape)) continue;
            const FVector Offset = Turn.RotateVector(Body->GetComponentLocation() - Actor->GetActorLocation());
            FVector Start = A + Offset, End = B + Offset;
            Start.Z = End.Z = Body->GetComponentLocation().Z;
            const FQuat Rotation = Turn * Body->GetComponentQuat();
            const auto AlreadyOverlapping = [&]()
            {
                return Actor->GetWorld()->OverlapBlockingTestByChannel(Body->GetComponentLocation(), Body->GetComponentQuat(), ECC_Pawn, Shape, Params, BodyResponses);
            };
            if (Start.Equals(End))
            {
                if (Actor->GetWorld()->OverlapBlockingTestByChannel(End, Rotation, ECC_Pawn, Shape, Params, BodyResponses) && !AlreadyOverlapping()) return true;
                continue;
            }
            FHitResult Hit;
            if (!Actor->GetWorld()->SweepSingleByChannel(Hit, Start, End, Rotation, ECC_Pawn, Shape, Params, BodyResponses)) continue;
            // A turn cannot introduce a penetration and call that first movement an old-save escape.
            if (Hit.bStartPenetrating && RejectNewTurnOverlap && !AlreadyOverlapping()) return true;
            // Preserve the separate old-save escape rule: motion must point out of an existing overlap.
            if (!Hit.bStartPenetrating || FVector::DotProduct(End - Start, Hit.Normal) <= 0.) return true;
        }
        return false;
    };
    if (!PoseBlocked(Wanted, Turning)) return false;
    if (!Turning || PoseBlocked(Current, false)) return true;

    // Preserve the original XY step while postponing only an unsafe presentation turn.
    // A long, off-centre body can reach a pond edge safely but need two retreating steps
    // before its rear clears a180-degree turn. Logical Dir/target/brain/random are untouched.
    bool WantedEndClear = true;
    const FQuat Turn = Wanted * Current.Inverse();
    for (UShapeComponent* Body : Bodies)
    {
        FCollisionShape Shape;
        if (!ShapeFor(Body, Shape)) continue;
        FVector End = B + Turn.RotateVector(Body->GetComponentLocation() - Actor->GetActorLocation());
        End.Z = Body->GetComponentLocation().Z;
        if (Actor->GetWorld()->OverlapBlockingTestByChannel(End, Turn * Body->GetComponentQuat(), ECC_Pawn, Shape, Params, BodyResponses))
        { WantedEndClear = false; break; }
    }
    if (OutFacing) *OutFacing = WantedEndClear ? Wanted : Current;
    return false;
}

// The fitted target uses the same admitted cooked mesh as movement. This is a
// bounded actual component query, not a legacy card AABB or a second collider.
bool UDinkGameplay::FittedMissileMatches(const FDinkSprite& Missile,const FDinkSprite& Target,int32 Range) const
{
    UPrimitiveComponent* Fitted=FindHardnessFitPrimitive(Target);
    const AActor* Actor=Missile.Actor.Get();
    if(!Fitted||!Actor||Actor->GetWorld()!=Fitted->GetWorld())return false;
    FVector A,B;
    const auto* D=Director();
    if(!D||!D->PixelToWorld(Missile.Screen,Missile.X,Missile.Y,A)||
        !D->PixelToWorld(Missile.Screen,Missile.X+FMath::Max(0,Range),Missile.Y,B))return false;
    const float Radius=FMath::Max(1.f,float(FVector::Dist2D(A,B)));
    // landforms: the missile and the fitted geometry in one frame (visual layer: the flat world's answer)
    const FVector Start=Actor->GetActorLocation()+FVector(0,0,DinkLandforms::GeometryLiftCm(Fitted)-DinkLandforms::ActorLiftCm(Actor));FHitResult Hit;
    return Fitted->SweepComponent(Hit,Start,Start+FVector(0,0,.1),FQuat::Identity,FCollisionShape::MakeSphere(Radius),true);
}
