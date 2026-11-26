#include "Misc/AutomationTest.h"
#include "DinkTestHelpers.h"
#include "DinkHeroBow.h"
#include "DinkHeroWeapon.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

// Art row AN-05, the bending bow: the limbs bend so that the string keeps its length, the string halves reach from the limb
// tips to the pull point, the arrow rides on the string and the quiver is on Dink's back while a bow is armed.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHeroBowBendsTest, "Dink.Art.HeroBow.BendsWithTheDraw", DINK_TEST_FLAGS)
bool FDinkHeroBowBendsTest::RunTest(const FString&)
{
	DinkHeroWeapons::Reload();
	DinkHeroBow::Reload();
	TestNull(TEXT("a sword has no bow row"), DinkHeroBow::Find(TEXT("item-sw1")));
	for (const TCHAR* Item : {TEXT("item-b1"), TEXT("item-b2"), TEXT("item-b3")})
	{
		const FDinkHeroBowRow* Row = DinkHeroBow::Find(FName(Item));
		if (!TestNotNull(FString::Printf(TEXT("%s has a bow row"), Item), Row)) continue;
		const FDinkHeroBowDraw& D = Row->Draw;
		const double Length = 2.0 * D.StringEnd.X;
		const FDinkHeroBowPose Rest = DinkHeroBow::Solve(D, 0.0);
		TestTrue(FString::Printf(TEXT("%s: at rest nothing bends (%.4f rad)"), Item, Rest.Bend), Rest.Bend < 1e-3 && FVector2D::Distance(Rest.Tip, D.StringEnd) < 0.02);
		TestEqual(FString::Printf(TEXT("%s: one segment a joint"), Item), Rest.Segments.Num(), D.Joints.Num());
		double Last = 0.0;
		for (const double Draw : {14.0, 28.0, 42.0, D.MaxDraw, D.MaxDraw + 30.0})
		{
			const FDinkHeroBowPose P = DinkHeroBow::Solve(D, Draw);
			const double Halves = FVector2D::Distance(P.Tip, P.Apex) + FVector2D::Distance(FVector2D(-P.Tip.X, P.Tip.Y), P.Apex);
			AddInfo(FString::Printf(TEXT("BOW %s draw %.1f cm: bend %.1f deg, tip (%.1f, %.1f), string %.2f of %.2f cm"), Item, Draw, FMath::RadiansToDegrees(P.Bend), P.Tip.X, P.Tip.Y, Halves, Length));
			TestTrue(FString::Printf(TEXT("%s draw %.0f: the string keeps its length (%.3f of %.3f cm)"), Item, Draw, Halves, Length), FMath::Abs(Halves - Length) < 0.05);
			TestTrue(FString::Printf(TEXT("%s draw %.0f: the limb bends further (%.3f after %.3f rad), the tip comes in and back"), Item, Draw, P.Bend, Last),
				P.Bend >= Last - 1e-6 && P.Tip.X < D.StringEnd.X && P.Tip.Y > D.StringEnd.Y);
			TestTrue(FString::Printf(TEXT("%s draw %.0f: the pull point is never further back than the furthest draw"), Item, Draw), P.Apex.Y <= D.StringEnd.Y + D.MaxDraw + 1e-6);
			Last = P.Bend;
		}
		TestTrue(FString::Printf(TEXT("%s: the full draw bends a limb between 20 and 45 degrees (%.1f)"), Item, FMath::RadiansToDegrees(Last)), Last > FMath::DegreesToRadians(20.0) && Last < FMath::DegreesToRadians(45.0));
	}
	USkeletalMesh* HeroMesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Hero/Refinements/SK_Dink_Hands.SK_Dink_Hands"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	const FDinkHeroWeaponRow* Hand = DinkHeroWeapons::Find(TEXT("item-b1"));
	if (!HeroMesh || !Hand || !LoadObject<UStaticMesh>(nullptr, *Hand->Mesh, nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		AddWarning(TEXT("dressing part skipped: the hero or the bow parts are not imported in this checkout"));
		return true;
	}
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
	AActor* Stage = World->SpawnActor<AActor>();
	USkeletalMeshComponent* Body = NewObject<USkeletalMeshComponent>(Stage);
	Stage->SetRootComponent(Body);
	Body->SetSkeletalMesh(HeroMesh);
	Body->RegisterComponent();
	for (const TCHAR* Item : {TEXT("item-b1"), TEXT("item-b2")})
	{
		const FDinkHeroBowRow* Row = DinkHeroBow::Find(FName(Item));
		UStaticMeshComponent* Held = DinkHeroWeapons::Apply(Stage, FName(Item), true);
		if (!Row || !TestNotNull(FString::Printf(TEXT("%s is in his hand"), Item), Held)) continue;
		TestTrue(FString::Printf(TEXT("%s: the hand holds the bow's middle part (%s)"), Item, *GetNameSafe(Held->GetStaticMesh())), Held->GetStaticMesh() && Held->GetStaticMesh()->GetName().EndsWith(TEXT("_Grip_PR")));
		for (const double Draw : {0.0, 40.0, Row->Draw.MaxDraw})
		{
			TestTrue(FString::Printf(TEXT("%s draw %.0f: the bow is dressed"), Item, Draw), DinkHeroBow::Apply(Stage, FName(Item), Draw, true));
			const FDinkHeroBowPose P = DinkHeroBow::Solve(Row->Draw, Draw);
			const double RestHalf[2] = {Row->Draw.StringEnd.X - Row->Draw.NockUp, Row->Draw.StringEnd.X + Row->Draw.NockUp};
			for (int32 Side = 0; Side < 2; ++Side)
			{
				const UStaticMeshComponent* S = DinkHeroBow::FindPart(Stage, Side == 0 ? TEXT("StringU") : TEXT("StringL"));
				if (!TestTrue(FString::Printf(TEXT("%s draw %.0f: string half %d is drawn"), Item, Draw, Side), S && S->IsVisible() && S->GetStaticMesh() && S->GetAttachParent() == Held)) continue;
				// the half's mesh runs from its origin along +X for its rest length: its far end, stretched and turned, is the pull point
				const FBox Box = S->GetStaticMesh()->GetBoundingBox();
				TestTrue(FString::Printf(TEXT("%s: string half %d runs %.1f cm along +X from its origin (%.1f to %.1f)"), Item, Side, RestHalf[Side], Box.Min.X, Box.Max.X),
					FMath::Abs(Box.Min.X) < 0.5 && FMath::Abs(Box.Max.X - RestHalf[Side]) < 0.5 && Box.GetSize().Y < 1.0 && Box.GetSize().Z < 1.0);
				const FVector End = S->GetRelativeTransform().TransformPosition(FVector(RestHalf[Side], 0.0, 0.0));
				const FVector Tie = S->GetRelativeLocation();
				TestTrue(FString::Printf(TEXT("%s draw %.0f: string half %d ends at the pull point (%.2f, %.2f, %.2f)"), Item, Draw, Side, End.X, End.Y, End.Z),
					FVector::Dist(End, FVector(P.Apex.X, P.Apex.Y, 0.0)) < 0.05);
				TestTrue(FString::Printf(TEXT("%s draw %.0f: string half %d starts at its limb tip"), Item, Draw, Side), FVector::Dist(Tie, FVector(Side == 0 ? P.Tip.X : -P.Tip.X, P.Tip.Y, 0.0)) < 0.01);
			}
			for (int32 K = 0; K < Row->Draw.Joints.Num(); ++K)
			{
				const UStaticMeshComponent* U = DinkHeroBow::FindPart(Stage, FName(*FString::Printf(TEXT("LimbU%d"), K + 1)));
				const UStaticMeshComponent* L = DinkHeroBow::FindPart(Stage, FName(*FString::Printf(TEXT("LimbL%d"), K + 1)));
				if (!TestTrue(FString::Printf(TEXT("%s draw %.0f: limb segment %d is drawn on both limbs"), Item, Draw, K + 1), U && L && U->IsVisible() && L->IsVisible() && U->GetStaticMesh() && L->GetStaticMesh())) continue;
				TestTrue(FString::Printf(TEXT("%s draw %.0f: the lower segment %d mirrors the upper"), Item, Draw, K + 1),
					FMath::IsNearlyEqual(U->GetRelativeLocation().X, -L->GetRelativeLocation().X, 1e-3) && FMath::IsNearlyEqual(U->GetRelativeRotation().Yaw, -L->GetRelativeRotation().Yaw, 1e-3));
				// each segment's mesh reaches from its joint to the next joint (or the string's tie) with the overlap that hides the cut
				const FVector2D Next = K + 1 < Row->Draw.Joints.Num() ? Row->Draw.Joints[K + 1] : Row->Draw.StringEnd;
				const FBox Box = U->GetStaticMesh()->GetBoundingBox();
				TestTrue(FString::Printf(TEXT("%s: upper segment %d spans its joint and the next (%.1f to %.1f cm, next at %.1f)"), Item, K + 1, Box.Min.X, Box.Max.X, Next.X - Row->Draw.Joints[K].X),
					Box.Min.X < -0.2 && Box.Min.X > -1.5 && Box.Max.X > Next.X - Row->Draw.Joints[K].X + 0.2);
			}
			const UStaticMeshComponent* Arrow = DinkHeroBow::FindPart(Stage, TEXT("Arrow"));
			if (TestTrue(FString::Printf(TEXT("%s draw %.0f: an arrow is on the string"), Item, Draw), Arrow && Arrow->IsVisible() && Arrow->GetStaticMesh()))
			{
				TestTrue(TEXT("its nock at the pull point"), FVector::Dist(Arrow->GetRelativeLocation(), FVector(P.Apex.X, P.Apex.Y, 0.0)) < 0.01);
				const FVector Point = Arrow->GetRelativeTransform().TransformPosition(FVector(Arrow->GetStaticMesh()->GetBoundingBox().Max.X, 0.0, 0.0));
				TestTrue(FString::Printf(TEXT("%s draw %.0f: its point is ahead of the stave (Y %.1f cm) and beside it (Z %.1f)"), Item, Draw, Point.Y, Point.Z), Point.Y < -1.0 && FMath::Abs(Point.Z) < 12.0); // at rest the shaft leans 7 degrees round the stave (1.9 cm aside over the 15 cm brace height): 10 cm at the point
			}
			const UStaticMeshComponent* Quiver = DinkHeroBow::FindPart(Stage, TEXT("Quiver"));
			TestTrue(FString::Printf(TEXT("%s: the quiver is on his back"), Item), Quiver && Quiver->IsVisible() && Quiver->GetStaticMesh() && Quiver->GetAttachParent() == Body && Quiver->GetAttachSocketName() == FName(TEXT("spine_03")));
		}
		TestTrue(TEXT("no arrow while it flies"), DinkHeroBow::Apply(Stage, FName(Item), 0.0, false) && DinkHeroBow::FindPart(Stage, TEXT("Arrow")) && !DinkHeroBow::FindPart(Stage, TEXT("Arrow"))->IsVisible());
		const double Hand0 = DinkHeroBow::DrawFromHand(Stage, FName(Item));
		TestTrue(FString::Printf(TEXT("%s: the string hand's pull is within the draw (%.1f cm in the reference pose)"), Item, Hand0), Hand0 >= 0.0 && Hand0 <= Row->Draw.MaxDraw);
	}
	// Another weapon, or none: every bow part goes.
	DinkHeroWeapons::Apply(Stage, TEXT("item-sw1"), true);
	TestFalse(TEXT("a sword dresses no bow"), DinkHeroBow::Apply(Stage, TEXT("item-sw1"), 0.0, true));
	TArray<UStaticMeshComponent*> Comps;
	Stage->GetComponents<UStaticMeshComponent>(Comps);
	int32 Shown = 0, Parts = 0;
	for (const UStaticMeshComponent* C : Comps) if (C->ComponentHasTag(TEXT("DinkHeroBowPart"))) { ++Parts; Shown += C->IsVisible() ? 1 : 0; }
	TestEqual(TEXT("with the sword armed no bow part, arrow or quiver is drawn"), Shown, 0);
	const FDinkHeroBowRow* Wood = DinkHeroBow::Find(TEXT("item-b1"));
	TestEqual(TEXT("the parts are made once: a segment a joint on both limbs, two string halves, the arrow, the quiver"), Parts, Wood ? 2 * Wood->Draw.Joints.Num() + 4 : 0);
	DinkHeroWeapons::Apply(Stage, TEXT("item-b1"), false);
	TestFalse(TEXT("a dead Dink's bow is not dressed"), DinkHeroBow::Apply(Stage, TEXT("item-b1"), 0.0, true));
	return true;
}
