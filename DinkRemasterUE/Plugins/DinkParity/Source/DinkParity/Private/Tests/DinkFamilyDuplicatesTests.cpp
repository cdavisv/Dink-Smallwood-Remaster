// Bug A208: copies of one 1997 object on neighbouring screens get ONE family mesh (DinkFamilyDuplicates.h).
// Rule: the pure decision (which copy is kept, which pairs are two objects, input order does not matter).
// DressOrder: a scratch world with the shipped families.json, dressed screen A then B and B then A through the real
// UDinkArtFamilySubsystem::ApplyScreen: the same copy draws the object, and exactly one object shows at every step.
// DuplicatePictureChange (review R5/R6 of #192): copies are one object only while they show the same picture; when one
// copy's picture changes (dam-fire.c burns a pine to 20/29), the copy of the screen Dink is on draws its own picture.
#include "DinkTestHelpers.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkFamilyDuplicates.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkLayout.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/FileManager.h"
#include "Math/RandomStream.h"
#include "Misc/ScopeExit.h"

namespace
{
	FDinkFamilyCopy Copy(const TCHAR* Origin, int32 Screen, const FDinkFamilyBinding* B, double MapX, double MapY, double SizePx = 120.0, int32 Frame = 1)
	{
		// Screens of the 1997 grid laid out flat at 10 cm per pixel: the ground point follows from the grid position.
		FDinkFamilyCopy C;
		C.Origin = Origin;
		C.Screen = Screen;
		C.Binding = B;
		C.Sequence = 32;
		C.Frame = Frame;
		C.MapPx = FVector2D(MapX, MapY);
		C.GroundCm = DinkFamilyDuplicates::GridPx(Screen, C.MapPx) * 10.0;
		C.SizePx = SizePx;
		return C;
	}

	TMap<FString, FString> Resolved(const TArray<FDinkFamilyCopy>& Copies)
	{
		TMap<FString, FString> Out;
		DinkFamilyDuplicates::Resolve(Copies, Out);
		return Out;
	}

	bool SameMap(const TMap<FString, FString>& A, const TMap<FString, FString>& B)
	{
		if (A.Num() != B.Num()) return false;
		for (const auto& Pair : A) if (const FString* Other = B.Find(Pair.Key); !Other || *Other != Pair.Value) return false;
		return true;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFamilyDuplicatesRuleTest, "Dink.Art.Family.Duplicates.Rule", DINK_TEST_FLAGS)
bool FDinkFamilyDuplicatesRuleTest::RunTest(const FString&)
{
	FDinkFamilyBinding Pine, Oak;
	Pine.Family = TEXT("tree_pine_large");
	Oak.Family = TEXT("tree_oak_large");
	using namespace DinkFamilyDuplicates;
	TestEqual(TEXT("inside: 0 px"), OutsidePx(FVector2D(149, 116)), 0.0);
	TestEqual(TEXT("116 px below the bottom edge"), OutsidePx(FVector2D(149, 516)), 116.0);
	TestEqual(TEXT("3-4-5 off a corner"), OutsidePx(FVector2D(603, -4)), 5.0);

	// The willow of SCR_446: S414_P02 at map (149, 516) of screen 414 is S446_P02 at (149, 116) of the screen below.
	const FDinkFamilyCopy Inside = Copy(TEXT("S446_P02"), 446, &Pine, 149, 116);
	const FDinkFamilyCopy Below = Copy(TEXT("S414_P02"), 414, &Pine, 149, 516);
	TestTrue(TEXT("the two copies are one object"), SameObject(Inside, Below));
	for (const TArray<FDinkFamilyCopy>& Order : {TArray<FDinkFamilyCopy>{Inside, Below}, TArray<FDinkFamilyCopy>{Below, Inside}})
	{
		const TMap<FString, FString> D = Resolved(Order);
		TestEqual(TEXT("one copy dropped"), D.Num(), 1);
		TestEqual(TEXT("the copy outside its screen is dropped for the one inside"), D.FindRef(TEXT("S414_P02")), FString(TEXT("S446_P02")));
	}

	// Neither inside (both 3 px above their screens): nearest the interior wins, then the lower screen.
	{
		const TMap<FString, FString> D = Resolved({Copy(TEXT("S010_P01"), 10, &Pine, 605, -3), Copy(TEXT("S011_P01"), 11, &Pine, 5, -3)});
		TestEqual(TEXT("none inside: the copy nearer its interior (3 px vs 5.8 px) is kept"), D.FindRef(TEXT("S010_P01")), FString(TEXT("S011_P01")));
	}
	{
		const TMap<FString, FString> D = Resolved({Copy(TEXT("S011_P01"), 11, &Pine, 0, -3), Copy(TEXT("S010_P01"), 10, &Pine, 600, -3)});
		TestEqual(TEXT("none inside, equally far: the lower screen is kept"), D.FindRef(TEXT("S011_P01")), FString(TEXT("S010_P01")));
	}
	// Both inside (2 px apart across the seam): the lower screen.
	{
		const TMap<FString, FString> D = Resolved({Copy(TEXT("S011_P07"), 11, &Pine, 1, 200), Copy(TEXT("S010_P09"), 10, &Pine, 599, 200)});
		TestEqual(TEXT("both inside: the lower screen is kept"), D.FindRef(TEXT("S011_P07")), FString(TEXT("S010_P09")));
	}
	// Four screens meet: the one copy inside draws it, the other three are dropped for it.
	{
		TArray<FDinkFamilyCopy> Corner{Copy(TEXT("S043_P02"), 43, &Pine, 610, 410), Copy(TEXT("S044_P03"), 44, &Pine, 10, 410),
			Copy(TEXT("S075_P04"), 75, &Pine, 610, 10), Copy(TEXT("S076_P05"), 76, &Pine, 10, 10)};
		const TMap<FString, FString> D = Resolved(Corner);
		TestEqual(TEXT("corner: three dropped"), D.Num(), 3);
		for (const auto& Pair : D) TestEqual(FString::Printf(TEXT("corner: %s dropped for the copy inside"), *Pair.Key), Pair.Value, FString(TEXT("S076_P05")));
		// Order independence: every shuffle gives the same decision.
		FRandomStream Shuffle(208);
		for (int32 Round = 0; Round < 24; ++Round)
		{
			for (int32 I = Corner.Num() - 1; I > 0; --I) Corner.Swap(I, Shuffle.RandRange(0, I));
			TestTrue(FString::Printf(TEXT("corner: shuffle %d decides the same"), Round), SameMap(Resolved(Corner), D));
		}
	}

	// Two objects, not one: each keeps its own mesh.
	const FDinkFamilyCopy A = Copy(TEXT("S177_P04"), 177, &Pine, 300, 450);
	auto KeepsBoth = [this, &A](const TCHAR* What, const FDinkFamilyCopy& B)
	{
		TestFalse(FString::Printf(TEXT("%s: not the same object"), What), DinkFamilyDuplicates::SameObject(A, B));
		TestEqual(FString::Printf(TEXT("%s: nothing dropped"), What), Resolved({A, B}).Num(), 0);
	};
	KeepsBoth(TEXT("5 px apart in 1997"), Copy(TEXT("S209_P08"), 209, &Pine, 305, 50));
	KeepsBoth(TEXT("another frame of the sequence"), Copy(TEXT("S209_P08"), 209, &Pine, 300, 50, 120.0, 2));
	KeepsBoth(TEXT("another families.json row"), Copy(TEXT("S209_P08"), 209, &Oak, 300, 50));
	KeepsBoth(TEXT("another 1997 size (sp size 75)"), Copy(TEXT("S209_P08"), 209, &Pine, 300, 50, 90.0));
	KeepsBoth(TEXT("the same screen (two sprites stacked on purpose)"), Copy(TEXT("S177_P05"), 177, &Pine, 300, 450));
	{
		FDinkFamilyCopy Far = Copy(TEXT("S209_P08"), 209, &Pine, 300, 50);
		Far.GroundCm += FVector2D(0.0, 150.0);  // the same 1997 pixel, but the layout put the screens 1.5 m apart: two visible trees
		KeepsBoth(TEXT("1.5 m apart in the world"), Far);
	}
	const FDinkFamilyCopy Same = Copy(TEXT("S209_P08"), 209, &Pine, 300, 50);
	TestTrue(TEXT("the real pine pair is one object"), SameObject(A, Same));
	TestEqual(TEXT("the pine inside 209 is kept"), Resolved({A, Same}).FindRef(TEXT("S177_P04")), FString(TEXT("S209_P08")));
	return true;
}

namespace
{
	struct FScratchCopies
	{
		ADinkPlaceholderActor* PineOutside = nullptr;  // 177 (300, 450): dropped
		ADinkPlaceholderActor* PineInside = nullptr;   // 209 (300, 50): kept
		ADinkGreyboxScreen* Screen177 = nullptr;       // decor instance at 177 (100, 380): kept
		ADinkPlaceholderActor* MixedOutside = nullptr; // 209 (100, -20): dropped
	};

	FDinkScreenCorners Corners(int32 Screen)
	{
		// 10 cm per pixel, laid out on the 1997 grid.
		const FVector2D NW = DinkFamilyDuplicates::GridPx(Screen, FVector2D::ZeroVector) * 0.1;
		FDinkScreenCorners C;
		C.NW = NW;
		C.NE = NW + FVector2D(60.0, 0.0);
		C.SW = NW + FVector2D(0.0, 40.0);
		C.SE = NW + FVector2D(60.0, 40.0);
		return C;
	}

	ADinkPlaceholderActor* Placement(UWorld& World, UStaticMesh& Card, int32 Screen, int32 Index, double MapX, double MapY)
	{
		const FVector At = DinkLayout::MapPixelToUnreal(Corners(Screen), MapX, MapY);
		ADinkPlaceholderActor* A = World.SpawnActor<ADinkPlaceholderActor>(At, FRotator::ZeroRotator);
		A->ScreenNumber = Screen;
		A->Card->SetStaticMesh(&Card);
		A->Card->SetRelativeLocation(FVector(0.0, 0.0, 500.0));
		A->Card->SetRelativeScale3D(FVector(10.0, 1.0, 10.0));
		A->Origin->OriginId = FDinkOriginId(Screen, Index);  // 1997 screens hold at most 99 sprites: Index < 100
		A->Origin->Sequence = 32;
		A->Origin->Frame = 1;
		A->Origin->ClassId = TEXT("tree_pine_large");
		return A;
	}

	FScratchCopies Populate(UWorld& World, UStaticMesh& Card)
	{
		FScratchCopies S;
		for (const int32 Screen : {177, 209})
		{
			ADinkScreenVolume* V = World.SpawnActor<ADinkScreenVolume>();
			V->ScreenNumber = Screen;
			V->Corners = Corners(Screen);
			ADinkGreyboxScreen* G = World.SpawnActor<ADinkGreyboxScreen>(DinkLayout::MapPixelToUnreal(Corners(Screen), 0, 0), FRotator::ZeroRotator);
			G->ScreenNumber = Screen;
			if (Screen == 177) S.Screen177 = G;
		}
		S.PineOutside = Placement(World, Card, 177, 91, 300, 450);
		S.PineInside = Placement(World, Card, 209, 92, 300, 50);
		S.MixedOutside = Placement(World, Card, 209, 93, 100, -20);
		// The decor instance of 177 that S.MixedOutside repeats: a background (type 0) placement.
		UInstancedStaticMeshComponent* Decor = NewObject<UInstancedStaticMeshComponent>(S.Screen177, TEXT("Decor_32_1"));
		Decor->SetupAttachment(S.Screen177->GetRootComponent());
		Decor->SetStaticMesh(&Card);
		S.Screen177->AddInstanceComponent(Decor);
		Decor->RegisterComponent();
		const FVector Ground = DinkLayout::MapPixelToUnreal(Corners(177), 100, 380) - S.Screen177->GetActorLocation();
		const int32 Index = Decor->AddInstance(FTransform(FRotator::ZeroRotator, Ground + FVector(0, 0, 500), FVector(10.0, 1.0, 10.0)), /*bWorldSpace*/ false);
		FDinkInstanceOrigin O;
		O.OriginId = FDinkOriginId(177, 94);
		O.Sequence = 32;
		O.Frame = 1;
		O.ClassId = TEXT("tree_pine_large");
		O.ComponentName = Decor->GetFName();
		O.InstanceIndex = Index;
		S.Screen177->InstanceOrigins->Origins.Add(O);
		return S;
	}

	int32 FamilyParts(const AActor& A)
	{
		int32 N = 0;
		TInlineComponentArray<UStaticMeshComponent*> Cs(&A);
		for (const UStaticMeshComponent* C : Cs)
		{
			if (!C->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)) continue;
			const UInstancedStaticMeshComponent* I = Cast<UInstancedStaticMeshComponent>(C);
			N += I ? I->GetInstanceCount() : 1;
		}
		return N;
	}

	/** What draws an object here: visible card(s) plus family meshes. */
	int32 Shown(const ADinkPlaceholderActor& A) { return (A.Card && !A.Card->bHiddenInGame ? 1 : 0) + FamilyParts(A); }
	int32 Shown(const ADinkGreyboxScreen& S)
	{
		const UInstancedStaticMeshComponent* Decor = nullptr;
		TInlineComponentArray<UInstancedStaticMeshComponent*> Cs(&S);
		for (const UInstancedStaticMeshComponent* C : Cs) if (C->GetFName() == TEXT("Decor_32_1")) Decor = C;
		return (Decor && !Decor->bHiddenInGame ? Decor->GetInstanceCount() : 0) + FamilyParts(S);
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFamilyDuplicatesDressOrderTest, "Dink.Art.Family.Duplicates.DressOrder", DINK_TEST_FLAGS)
bool FDinkFamilyDuplicatesDressOrderTest::RunTest(const FString&)
{
	if (!IFileManager::Get().FileExists(*DinkArtFamily::DefaultFamiliesPath()))
	{
		AddWarning(TEXT("skipped: no families.json"));
		return true;
	}
	UStaticMesh* Card = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	if (!TestNotNull(TEXT("engine card mesh"), Card)) return false;
	for (const bool bKeptFirst : {false, true})
	{
		const TCHAR* Order = bKeptFirst ? TEXT("209 then 177") : TEXT("177 then 209");
		UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
		if (!TestNotNull(TEXT("scratch world"), World)) return false;
		GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
		ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); World->MarkObjectsPendingKill(); };
		const FScratchCopies S = Populate(*World, *Card);
		UDinkArtFamilySubsystem* Family = World->GetSubsystem<UDinkArtFamilySubsystem>();
		UDinkFamilyDuplicatesSubsystem* Dupes = World->GetSubsystem<UDinkFamilyDuplicatesSubsystem>();
		if (!TestNotNull(TEXT("family subsystem"), Family) || !TestNotNull(TEXT("duplicates subsystem"), Dupes)) return false;
		Family->OnWorldBeginPlay(*World);
		if (!TestTrue(TEXT("family layer ready with the shipped families.json"), Family->IsReady())) return false;
		TArray<int32> Steps = bKeptFirst ? TArray<int32>{209, 177} : TArray<int32>{177, 209};
		for (int32 Step = 0; Step < Steps.Num(); ++Step)
		{
			Family->ApplyScreen(Steps[Step]);
			const FString When = FString::Printf(TEXT("%s, after %d"), Order, Steps[Step]);
			TestEqual(FString::Printf(TEXT("%s: the pine shows exactly once"), *When), Shown(*S.PineOutside) + Shown(*S.PineInside), 1);
			TestEqual(FString::Printf(TEXT("%s: the actor/instance pair shows exactly once (kept instance undressed: its card)"), *When),
				Shown(*S.MixedOutside) + Shown(*S.Screen177), 1);
			TestEqual(FString::Printf(TEXT("%s: the dropped pine never gets a mesh"), *When), FamilyParts(*S.PineOutside), 0);
			TestEqual(FString::Printf(TEXT("%s: the dropped mixed copy never gets a mesh"), *When), FamilyParts(*S.MixedOutside), 0);
		}
		TestEqual(FString::Printf(TEXT("%s: two dropped"), Order), Dupes->GetDropped().Num(), 2);
		TestEqual(FString::Printf(TEXT("%s: S177_P91 is drawn by S209_P92"), Order), Dupes->GetDropped().FindRef(TEXT("S177_P91")), FString(TEXT("S209_P92")));
		TestEqual(FString::Printf(TEXT("%s: S209_P93 is drawn by S177_P94"), Order), Dupes->GetDropped().FindRef(TEXT("S209_P93")), FString(TEXT("S177_P94")));
		TestEqual(FString::Printf(TEXT("%s: the kept pine has its mesh"), Order), FamilyParts(*S.PineInside), 1);
		TestEqual(FString::Printf(TEXT("%s: the kept decor instance has its mesh"), Order), FamilyParts(*S.Screen177), 1);
		TestTrue(FString::Printf(TEXT("%s: dropped actors are tagged"), Order),
			S.PineOutside->ActorHasTag(UDinkFamilyDuplicatesSubsystem::DroppedTag) && S.MixedOutside->ActorHasTag(UDinkFamilyDuplicatesSubsystem::DroppedTag));
		TestFalse(FString::Printf(TEXT("%s: kept actor not tagged dropped"), Order), S.PineInside->ActorHasTag(UDinkFamilyDuplicatesSubsystem::DroppedTag));
		TestTrue(FString::Printf(TEXT("%s: origin IDs unchanged"), Order), S.PineOutside->Origin->OriginId.ToString() == TEXT("S177_P91"));
	}
	return true;
}

namespace
{
	/** Family meshes of the copy that draw now (not hidden in game). */
	int32 DrawnMeshes(const ADinkPlaceholderActor& A)
	{
		int32 N = 0;
		TInlineComponentArray<UStaticMeshComponent*> Cs(&A);
		for (const UStaticMeshComponent* C : Cs)
			if (C != A.Card && C->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag) && !C->bHiddenInGame) ++N;
		return N;
	}

	/** What of the copy draws now: its card unless hidden in game, plus its family meshes that are not. */
	int32 Drawn(const ADinkPlaceholderActor& A) { return (A.Card && !A.Card->bHiddenInGame ? 1 : 0) + DrawnMeshes(A); }

	/** The scratch world of DressOrder with the family layer begun, as at play start. */
	struct FPictureWorld
	{
		UWorld* World = nullptr;
		FScratchCopies S;
		UDinkArtFamilySubsystem* Family = nullptr;
		UDinkFamilyDuplicatesSubsystem* Dupes = nullptr;
		UDinkGreyboxSubsystem* Greybox = nullptr;
	};

	bool BeginPictureWorld(FAutomationTestBase& Test, UWorld& World, UStaticMesh& Card, FPictureWorld& Out)
	{
		Out.World = &World;
		Out.S = Populate(World, Card);
		Out.Family = World.GetSubsystem<UDinkArtFamilySubsystem>();
		Out.Dupes = World.GetSubsystem<UDinkFamilyDuplicatesSubsystem>();
		Out.Greybox = World.GetSubsystem<UDinkGreyboxSubsystem>();
		if (!Test.TestNotNull(TEXT("family subsystem"), Out.Family) || !Test.TestNotNull(TEXT("duplicates subsystem"), Out.Dupes) ||
			!Test.TestNotNull(TEXT("greybox subsystem"), Out.Greybox)) return false;
		Out.Family->OnWorldBeginPlay(World);
		return Test.TestTrue(TEXT("family layer ready with the shipped families.json"), Out.Family->IsReady());
	}

	/** The greybox's screen change, as when Dink walks onto Screen (the family layer dresses it and the copies pick their drawer). */
	void Enter(FAutomationTestBase& Test, const FPictureWorld& W, int32 Screen)
	{
		for (TActorIterator<ADinkScreenVolume> It(W.World); It; ++It) if (It->ScreenNumber == Screen) W.Greybox->OnScreenChanged.Broadcast(*It);
		Test.TestEqual(FString::Printf(TEXT("the family layer knows Dink is on %d"), Screen), W.Family->GetCurrentScreen(), Screen);
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkDuplicatePictureChangeDroppedTest, "Dink.Art.Family.DuplicatePictureChange.DroppedCopy", DINK_TEST_FLAGS)
bool FDinkDuplicatePictureChangeDroppedTest::RunTest(const FString&)
{
	if (!IFileManager::Get().FileExists(*DinkArtFamily::DefaultFamiliesPath()))
	{
		AddWarning(TEXT("skipped: no families.json"));
		return true;
	}
	UStaticMesh* Card = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	if (!TestNotNull(TEXT("engine card mesh"), Card)) return false;
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	if (!TestNotNull(TEXT("scratch world"), World)) return false;
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); World->MarkObjectsPendingKill(); };
	FPictureWorld W;
	if (!BeginPictureWorld(*this, *World, *Card, W)) return false;
	ADinkPlaceholderActor& Dropped = *W.S.PineOutside;  // S177_P91, outside 177: dropped
	ADinkPlaceholderActor& Kept = *W.S.PineInside;      // S209_P92, inside 209: kept
	const FTransform DroppedAt = Dropped.GetActorTransform();
	const bool bDroppedCollides = Dropped.GetActorEnableCollision();

	Enter(*this, W, 209);
	W.Family->ApplyScreen(177);  // the environment layer dresses the neighbour screens in view
	TestEqual(TEXT("on 209: the pine draws once"), Drawn(Kept) + Drawn(Dropped), 1);
	TestEqual(TEXT("on 209: by the kept copy's mesh"), DrawnMeshes(Kept), 1);
	Enter(*this, W, 177);
	TestEqual(TEXT("on 177, one picture: still the kept mesh (no other variant or yaw at the seam)"), DrawnMeshes(Kept), 1);
	TestEqual(TEXT("on 177, one picture: the dropped copy stays hidden"), Drawn(Dropped), 0);

	// dam-fire.c on the 177 copy (a pine without a script): editor_type 4, editor_seq 20, editor_frame 29. On the next entry
	// update_play_changes gives the placement that picture (dink.cpp:5829-5830); UDinkGameplay::PresentPlacementPicture passes it on.
	W.Family->SetPlacementPicture(Dropped, 20, 29, false);
	TestFalse(TEXT("on 177, burnt: the 177 copy draws its own picture (its card)"), Dropped.Card->bHiddenInGame);
	TestEqual(TEXT("on 177, burnt: no family mesh (20/29 has no families.json row)"), DrawnMeshes(Dropped), 0);
	TestEqual(TEXT("on 177, burnt: the kept copy's green pine no longer draws over it"), Drawn(Kept), 0);
	TestEqual(TEXT("on 177, burnt: the 177 copy draws the object"), W.Dupes->GetDrawer(TEXT("S209_P92")), FString(TEXT("S177_P91")));
	TestFalse(TEXT("on 177, burnt: not tagged as drawn by another copy"), Dropped.ActorHasTag(UDinkFamilyDuplicatesSubsystem::DroppedTag));
	TestTrue(TEXT("on 177, burnt: the kept copy is the one drawn by another copy now"), Kept.ActorHasTag(UDinkFamilyDuplicatesSubsystem::DroppedTag));

	Enter(*this, W, 209);
	TestEqual(TEXT("back on 209: 1997 shows 209's copy, unburnt: its own pine mesh"), DrawnMeshes(Kept), 1);
	TestEqual(TEXT("back on 209: the burnt 177 copy does not draw"), Drawn(Dropped), 0);
	Enter(*this, W, 177);
	TestFalse(TEXT("177 again: the burnt card"), Dropped.Card->bHiddenInGame);
	TestEqual(TEXT("177 again: one object"), Drawn(Dropped) + Drawn(Kept), 1);

	// A load of a save in which the tree never burnt: the imported picture again, so one object again, drawn by the kept mesh.
	W.Family->SetPlacementPicture(Dropped, 0, 0, false);
	TestEqual(TEXT("one picture again: the kept mesh draws"), DrawnMeshes(Kept), 1);
	TestEqual(TEXT("one picture again: the dropped copy is hidden"), Drawn(Dropped), 0);
	TestEqual(TEXT("one picture again: the kept copy draws the object"), W.Dupes->GetDrawer(TEXT("S177_P91")), FString(TEXT("S209_P92")));

	// The actor/instance pair (a background instance never changes picture) keeps its kept copy throughout.
	TestEqual(TEXT("the dropped copy of the actor/instance pair stays hidden"), Drawn(*W.S.MixedOutside), 0);
	// Presentation only: the placement's actor, collision and origin are what they were.
	TestTrue(TEXT("the dropped copy did not move"), Dropped.GetActorTransform().Equals(DroppedAt));
	TestEqual(TEXT("its collision is untouched"), Dropped.GetActorEnableCollision(), bDroppedCollides);
	TestEqual(TEXT("its origin is unchanged"), Dropped.Origin->OriginId.ToString(), FString(TEXT("S177_P91")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkDuplicatePictureChangeKeptTest, "Dink.Art.Family.DuplicatePictureChange.KeptCopy", DINK_TEST_FLAGS)
bool FDinkDuplicatePictureChangeKeptTest::RunTest(const FString&)
{
	if (!IFileManager::Get().FileExists(*DinkArtFamily::DefaultFamiliesPath()))
	{
		AddWarning(TEXT("skipped: no families.json"));
		return true;
	}
	UStaticMesh* Card = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	if (!TestNotNull(TEXT("engine card mesh"), Card)) return false;
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	if (!TestNotNull(TEXT("scratch world"), World)) return false;
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); World->MarkObjectsPendingKill(); };
	FPictureWorld W;
	if (!BeginPictureWorld(*this, *World, *Card, W)) return false;
	ADinkPlaceholderActor& Dropped = *W.S.PineOutside;  // S177_P91
	ADinkPlaceholderActor& Kept = *W.S.PineInside;      // S209_P92

	Enter(*this, W, 209);
	W.Family->ApplyScreen(177);
	// dam-fire.c on the kept 209 copy; its saved picture 20/29 on the next entry of 209.
	W.Family->SetPlacementPicture(Kept, 20, 29, false);
	TestEqual(TEXT("on 209, burnt kept copy: its pine mesh is gone"), DrawnMeshes(Kept), 0);
	TestFalse(TEXT("on 209, burnt kept copy: its burnt card draws"), Kept.Card->bHiddenInGame);
	TestEqual(TEXT("on 209: the 177 copy draws nothing"), Drawn(Dropped), 0);

	// Walk to 177. The kept card renders only on its own screen (dink.LegacyCardsCurrentScreen), so A208's dropped copy left
	// nothing there; 1997 shows 177's own green tree.
	Enter(*this, W, 177);
	TestEqual(TEXT("on 177: the 177 copy's own pine mesh draws"), DrawnMeshes(Dropped), 1);
	TestTrue(TEXT("on 177: its card is replaced by that mesh"), Dropped.Card->bHiddenInGame);
	TestEqual(TEXT("on 177: the burnt 209 copy draws nothing here"), Drawn(Kept), 0);
	TestEqual(TEXT("on 177: the copy of the current screen draws the object"), W.Dupes->GetDrawer(TEXT("S209_P92")), FString(TEXT("S177_P91")));
	Enter(*this, W, 209);
	TestFalse(TEXT("209 again: the burnt card"), Kept.Card->bHiddenInGame);
	TestEqual(TEXT("209 again: one object"), Drawn(Kept) + Drawn(Dropped), 1);

	// Both copies burnt: one picture again, but drawn by a card, which renders only on its own screen: each screen draws its copy.
	W.Family->SetPlacementPicture(Dropped, 20, 29, false);
	TestFalse(TEXT("both burnt, on 209: the 209 card"), Kept.Card->bHiddenInGame);
	TestEqual(TEXT("both burnt, on 209: one object"), Drawn(Kept) + Drawn(Dropped), 1);
	Enter(*this, W, 177);
	TestFalse(TEXT("both burnt, on 177: the 177 card"), Dropped.Card->bHiddenInGame);
	TestEqual(TEXT("both burnt, on 177: one object"), Drawn(Kept) + Drawn(Dropped), 1);
	return true;
}
