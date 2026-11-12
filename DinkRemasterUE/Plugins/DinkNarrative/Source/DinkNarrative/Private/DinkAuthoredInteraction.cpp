#include "DinkGameplay.h"
#include "DinkDirector.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "Components/ShapeComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
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
		}
		else
		{
			for (UPrimitiveComponent* Component : Components)
			{
				if (UStaticMeshComponent* Mesh = Cast<UStaticMeshComponent>(Component); Mesh && Mesh->GetStaticMesh() && Mesh->IsVisible() && !Mesh->bHiddenInGame)
				{
					Geometry.Add(Mesh);
				}
			}
		}
	}
	double BestDistance = TNumericLimits<double>::Max();
	for (UPrimitiveComponent* Component : Geometry)
	{
		const bool bElevatedPickup = Kind == EAuthoredInteraction::Touch && Target.GetProp(TEXT("touch_damage")) == -1 &&
			Component->Bounds.GetBox().Min.Z - (From.Z - BodyHalfHeight) >= AuthoredInteraction.ElevatedPickupMinHeightCm;
		const float QueryRadius = bElevatedPickup ? BodyRadius + float(AuthoredInteraction.ElevatedPickupReachCm) : Radius;
		// Extend a hand over furniture without extending vertical reach by the same amount.
		const FCollisionShape Shape = FCollisionShape::MakeCapsule(QueryRadius, FMath::Max(HalfHeight, QueryRadius));
		FHitResult Hit;
		if (!Component->SweepComponent(Hit, Start, End, FQuat::Identity, Shape, Component->IsA<UStaticMeshComponent>())) { continue; }
		FVector Surface = Hit.ImpactPoint;
		if (Hit.bStartPenetrating) { Surface = Component->Bounds.GetBox().GetClosestPointTo(From); }
		if (Kind == EAuthoredInteraction::Push && FVector::DotProduct((Surface - From).GetSafeNormal2D(), Forward) < 0.0) { continue; }
		// A prop across a wall must not answer a nearby hit/talk or be collected through it.
		FVector SightOrigin = From;
		if (bElevatedPickup) { SightOrigin.Z = From.Z - BodyHalfHeight + AuthoredInteraction.PickupShoulderHeightCm; }
		FCollisionQueryParams Params(TEXT("DinkAuthoredInteraction"), true, FromActor);
		FHitResult Blocker;
		if (UWorld* World = FromActor->GetWorld(); World && World->LineTraceSingleByChannel(Blocker, SightOrigin, Surface, ECC_Visibility, Params) &&
			Blocker.GetActor() != TargetActor && Blocker.GetComponent()!=Fitted && Blocker.Distance + 1.f < FVector::Distance(SightOrigin, Surface)) { continue; }
		BestDistance = FMath::Min(BestDistance, FVector::Dist2D(From, Surface));
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
                return Actor->GetWorld()->OverlapBlockingTestByChannel(Body->GetComponentLocation(), Body->GetComponentQuat(), ECC_Pawn, Shape, Params);
            };
            if (Start.Equals(End))
            {
                if (Actor->GetWorld()->OverlapBlockingTestByChannel(End, Rotation, ECC_Pawn, Shape, Params) && !AlreadyOverlapping()) return true;
                continue;
            }
            FHitResult Hit;
            if (!Actor->GetWorld()->SweepSingleByChannel(Hit, Start, End, Rotation, ECC_Pawn, Shape, Params)) continue;
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
        if (Actor->GetWorld()->OverlapBlockingTestByChannel(End, Turn * Body->GetComponentQuat(), ECC_Pawn, Shape, Params))
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
    const FVector Start=Actor->GetActorLocation();FHitResult Hit;
    return Fitted->SweepComponent(Hit,Start,Start+FVector(0,0,.1),FQuat::Identity,FCollisionShape::MakeSphere(Radius),true);
}
