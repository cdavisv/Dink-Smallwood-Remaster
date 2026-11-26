// Landforms (15-16 Nov 2026): the world heightfield's data, and that it is a VISUAL layer: the simulation (Dink's 2D
// position, scripted moves, timing, collision) is the same with it on and off (DinkLandforms.h).
#include "DinkTestHelpers.h"
#include "DinkCollision.h"
#include "DinkLandforms.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "ProceduralMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DinkPlayerBlockers.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Editor.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkLandformsDataTest, "Dink.Movement.Landforms.Data", DINK_TEST_FLAGS)
bool FDinkLandformsDataTest::RunTest(const FString&)
{
	// sampling is exact at the vertices and smooth between them
	const TArray<float> G = {0.f, 1.f, 2.f, 3.f, 0.f, 1.f, 2.f, 3.f, 0.f, 1.f, 2.f, 3.f};
	TestEqual(TEXT("vertex value"), DinkLandforms::SampleGrid(G, 4, 3, 2.0, 1.0), 2.f, 1e-5f);
	TestEqual(TEXT("linear ramp between vertices"), DinkLandforms::SampleGrid(G, 4, 3, 1.5, 0.5), 1.5f, 1e-4f);

	const FString Path = DinkLandforms::DefaultPath();
	FString Json; TArray<uint8> Png;
	if (!FFileHelper::LoadFileToString(Json, *Path) || !FFileHelper::LoadFileToArray(Png, *(FPaths::GetPath(Path) / TEXT("landforms.png"))))
	{
		AddError(TEXT("no landforms data at ") + Path);
		return false;
	}
	FDinkLandformsData Data;
	FString Error;
	if (!TestTrue(TEXT("landforms data loads: ") + Error, Data.Load(Json, Png, Error))) return false;
	TestTrue(TEXT("some screens have height"), Data.Screens.Num() > 0);
	// neighbours that share an edge in the world share its heights (one raster of the whole map)
	int32 Edges = 0;
	float Worst = 0.f;
	for (const TPair<int32, FDinkLandformsScreen>& Pair : Data.Screens)
	{
		const FDinkLandformsScreen& A = Pair.Value;
		TestTrue(FString::Printf(TEXT("SCR_%03d heights in range"), A.Screen), A.HeightsM.Num() == Data.GridW * Data.GridH);
		for (const float H : A.HeightsM)
		{
			if (H < -3.f || H > 9.f) { AddError(FString::Printf(TEXT("SCR_%03d height %.2f m out of range"), A.Screen, H)); break; }
		}
		const bool bLastColumn = (A.Screen - 1) % 32 == 31;
		const FDinkLandformsScreen* E = bLastColumn ? nullptr : Data.Screens.Find(A.Screen + 1);
		if (E && E->Corners.NW.Equals(A.Corners.NE, 1e-3) && E->Corners.SW.Equals(A.Corners.SE, 1e-3))
		{
			++Edges;
			for (int32 J = 0; J < Data.GridH; ++J)
				Worst = FMath::Max(Worst, FMath::Abs(A.HeightsM[J * Data.GridW + Data.GridW - 1] - E->HeightsM[J * Data.GridW]));
		}
		const FDinkLandformsScreen* S = Data.Screens.Find(A.Screen + 32);
		if (S && S->Corners.NW.Equals(A.Corners.SW, 1e-3) && S->Corners.NE.Equals(A.Corners.SE, 1e-3))
		{
			++Edges;
			for (int32 I = 0; I < Data.GridW; ++I)
				Worst = FMath::Max(Worst, FMath::Abs(A.HeightsM[(Data.GridH - 1) * Data.GridW + I] - S->HeightsM[I]));
		}
	}
	AddInfo(FString::Printf(TEXT("%d screens, %d shared edges, worst edge step %.4f m"), Data.Screens.Num(), Edges, Worst));
	TestTrue(TEXT("shared edges have the same heights"), Worst < 0.0015f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkLandformsVisualOnlyTest, "Dink.Movement.Landforms.VisualOnly", DINK_TEST_FLAGS)
bool FDinkLandformsVisualOnlyTest::RunTest(const FString&)
{
	// the drawn ground collides with nothing (the player's capsule included); a lifted actor's invisible collision (warp box,
	// player-only blocker, body shape) stays on the flat floor while what is drawn rises
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	if (!TestNotNull(TEXT("world"), World)) return false;
	AActor* Holder = World->SpawnActor<AActor>();
	UProceduralMeshComponent* Ground = NewObject<UProceduralMeshComponent>(Holder, TEXT("Ground"));
	Holder->SetRootComponent(Ground);
	Ground->bUseAsyncCooking = false;
	DinkLandforms::ConfigureGround(*Ground);
	Ground->RegisterComponent();
	const TArray<FVector> V = {FVector(-500, -500, 50), FVector(500, -500, 50), FVector(500, 500, 50), FVector(-500, 500, 50)};
	Ground->CreateMeshSection_LinearColor(0, V, {0, 2, 1, 0, 3, 2}, TArray<FVector>(), TArray<FVector2D>(), TArray<FLinearColor>(), TArray<FProcMeshTangent>(), false);
	const FCollisionShape Body = FCollisionShape::MakeCapsule(28.f, 96.f);
	FHitResult Hit;
	FCollisionQueryParams NpcParams(TEXT("LandformsNpc"), true);
	TestFalse(TEXT("an NPC/creature move sweep passes through"),
		World->SweepSingleByChannel(Hit, FVector(0, 0, 400), FVector(0, 0, -400), FQuat::Identity, ECC_Pawn, Body, NpcParams, DinkCollision::IgnorePlayerBlockers()));
	TestFalse(TEXT("missiles pass through"), World->LineTraceSingleByChannel(Hit, FVector(0, 0, 400), FVector(0, 0, -400), DinkCollision::Projectile));
	TestFalse(TEXT("sight passes through"), World->LineTraceSingleByChannel(Hit, FVector(0, 0, 400), FVector(0, 0, -400), ECC_Visibility));
	TestFalse(TEXT("the camera passes through"), World->LineTraceSingleByChannel(Hit, FVector(0, 0, 400), FVector(0, 0, -400), ECC_Camera));
	FActorSpawnParameters Spawn;
	Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ADinkGreyboxCharacter* Hero = World->SpawnActor<ADinkGreyboxCharacter>(FVector(0, 0, 400), FRotator::ZeroRotator, Spawn);
	if (TestNotNull(TEXT("hero"), Hero))
	{
		const UCapsuleComponent* Capsule = Hero->GetCapsuleComponent();
		FCollisionQueryParams Params(TEXT("LandformsHero"), false, Hero);
		TestFalse(TEXT("the player capsule does not stand on the drawn ground either (it walks on the 1997 floor)"),
			World->SweepSingleByChannel(Hit, FVector(0, 0, 400), FVector(0, 0, -400), FQuat::Identity, Capsule->GetCollisionObjectType(), Body,
				Params, FCollisionResponseParams(Capsule->GetCollisionResponseToChannels())));
	}

	// a lifted placement: the drawn card rises, its warp box, blocker and body shape stay; moving it again keeps them there
	AActor* Prop = World->SpawnActor<AActor>(FVector(300, 0, 0), FRotator::ZeroRotator, Spawn);
	USceneComponent* Root = NewObject<USceneComponent>(Prop, TEXT("Root"));
	Prop->SetRootComponent(Root);
	Root->SetMobility(EComponentMobility::Movable);
	Root->RegisterComponent();
	UStaticMeshComponent* Card = NewObject<UStaticMeshComponent>(Prop, TEXT("Card"));
	Card->SetupAttachment(Root);
	Card->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Card->RegisterComponent();
	UBoxComponent* Shape = NewObject<UBoxComponent>(Prop, TEXT("Body"));
	Shape->SetupAttachment(Root);
	Shape->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Shape->SetRelativeLocation(FVector(0, 0, 40));
	Shape->RegisterComponent();
	UStaticMeshComponent* Blocker = NewObject<UStaticMeshComponent>(Prop, TEXT("Blocker"));
	Blocker->SetupAttachment(Card);
	Blocker->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	Blocker->ComponentTags.Add(DinkPlayerBlockers::Tag);
	Blocker->RegisterComponent();
	const double ShapeZ = Shape->GetComponentLocation().Z, BlockerZ = Blocker->GetComponentLocation().Z;
	Prop->AddActorWorldOffset(FVector(0, 0, 37.5));
	DinkLandforms::KeepCollisionFlat(*Prop, 0.f, 37.5f);
	TestEqual(TEXT("the drawn card rises"), Card->GetComponentLocation().Z, 37.5, 1e-3);
	TestEqual(TEXT("the body shape stays on the flat floor"), Shape->GetComponentLocation().Z, ShapeZ, 1e-3);
	TestEqual(TEXT("the player-only blocker stays on the flat floor"), Blocker->GetComponentLocation().Z, BlockerZ, 1e-3);
	TestTrue(TEXT("both held ones are tagged"), Shape->ComponentHasTag(DinkLandforms::FlatTag) && Blocker->ComponentHasTag(DinkLandforms::FlatTag));
	TestEqual(TEXT("held collision has no lift"), DinkLandforms::GeometryLiftCm(Shape), 0.f);
	Prop->AddActorWorldOffset(FVector(0, 0, -50.0));
	DinkLandforms::KeepCollisionFlat(*Prop, 37.5f, -12.5f);
	TestEqual(TEXT("after a second move the body shape is still on the flat floor"), Shape->GetComponentLocation().Z, ShapeZ, 1e-3);
	TestEqual(TEXT("and the blocker"), Blocker->GetComponentLocation().Z, BlockerZ, 1e-3);
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

namespace DinkLandformsTest
{
	/** One run on the yard of SCR_439: the bot's kind of walk (movement input), then Dink's scripted move. */
	struct FRun
	{
		TArray<FVector2D> Walk;        // capsule XY per frame of the walk
		TArray<FIntPoint> Move;        // Dink's sprite pixel per frame of the scripted move
		TArray<double> CapsuleZ;       // capsule Z per frame (walk and move)
		TArray<float> Ground;          // landforms height under the capsule per frame
		FVector End = FVector::ZeroVector;
		double DrawnLift = 0.0;        // mesh Z minus capsule Z at the end, minus the same of the flat run
		float GroundAtEnd = 0.f;
	};

	/** A hill with a ripple across the whole screen: 0 .. 0.6 m, a dip to -0.2 m (a ford's depth), slopes up to ~20 degrees. */
	FDinkLandformsData Relief(const ADinkScreenVolume& Screen)
	{
		FDinkLandformsData D;
		FDinkLandformsScreen S;
		S.Screen = Screen.ScreenNumber;
		S.Corners = Screen.Corners;
		for (const FVector2D& P : {S.Corners.NW, S.Corners.NE, S.Corners.SW, S.Corners.SE}) S.BoundsCm += P * DinkLayout::CentimetresPerMetre;
		S.HeightsM.SetNumZeroed(D.GridW * D.GridH);
		for (int32 J = 0; J < D.GridH; ++J)
			for (int32 I = 0; I < D.GridW; ++I)
				S.HeightsM[J * D.GridW + I] = 0.45f * FMath::Sin(UE_PI * I / (D.GridW - 1)) * FMath::Sin(UE_PI * J / (D.GridH - 1))
					+ 0.2f * FMath::Sin(I * 0.45f + J * 0.3f);
		D.Screens.Add(S.Screen, MoveTemp(S));
		return D;
	}
}

class FDinkLandformsMovePIE : public IAutomationLatentCommand
{
public:
	explicit FDinkLandformsMovePIE(FAutomationTestBase* T) : Test(T) {}
	bool Update() override
	{
		if (!Began) Began = FPlatformTime::Seconds();
		if (FPlatformTime::Seconds() - Began > 120) { Test->AddError(TEXT("landforms move PIE timeout")); Cleanup(); return true; }
		UWorld* W = GEditor ? GEditor->PlayWorld.Get() : nullptr;
		APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
		ADinkGreyboxCharacter* H = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
		UDinkStorySubsystem* Story = W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		if (!H || !Story || Story->bNewGamePending) return false;
		World = W;
		UDinkDirector* D = Story->GetDirector();
		UCharacterMovementComponent* Move = H->GetCharacterMovement();
		UDinkLandformsSubsystem* Landforms = W->GetSubsystem<UDinkLandformsSubsystem>();
		ADinkScreenVolume* Yard = W->GetSubsystem<UDinkGreyboxSubsystem>()->FindScreen(439);
		if (!Test->TestNotNull(TEXT("landforms subsystem"), Landforms) || !Test->TestNotNull(TEXT("yard fixture SCR_439"), Yard)) return true;
		auto Cmd = [&](const FString& Line) { FDinkScriptInstance Caller; D->Execute(Caller, FDinkStoryLine::Parse(Line, {TEXT("cmd")})); };
		DinkLandformsTest::FRun& R = Runs[Run];
		switch (Phase)
		{
		case 0:
			Story->bRunScreenScripts = false;
			Cmd(TEXT(">> unfreeze 1"));
			Story->ResetRuntime();
			Story->GetGameplay()->bBrainsEnabled = false;
			Cmd(TEXT(">> unfreeze 1"));
			// run 0 settles the harness (flat), run 1 is over relief, run 2 flat again: 1 and 2 must be equal
			if (Run == 2) Landforms->SetDataForTest(FDinkLandformsData(), false);
			if (Run == 1)
			{
				Landforms->SetDataForTest(DinkLandformsTest::Relief(*Yard), true);
				if (!Test->TestTrue(TEXT("relief on under the yard"), Landforms->IsActive() && FMath::Abs(Landforms->HeightCmAtPixel(439, 300, 200)) > 20.f)) { Cleanup(); return true; }
			}
			H->SetActorLocation(Yard->MapPixelToWorld(120, 220) + FVector(0, 0, 100), false, nullptr, ETeleportType::TeleportPhysics);
			H->SetActorRotation(FRotator::ZeroRotator);
			Move->StopMovementImmediately();
			Frames = 0; Phase = 1; return false;
		case 1:
			// settle on the floor for a fixed number of frames
			if (++Frames < 30 || !Move->IsMovingOnGround()) return false;
			Frames = 0; Phase = 2; return false;
		case 2:
			// the bot's way of walking: movement input, the capsule's own sweeps against the 1997 collision
			H->AddMovementInput(FVector(1.0, 0.35, 0.0));
			R.Walk.Add(FVector2D(H->GetActorLocation()));
			R.Ground.Add(Landforms->HeightCmAt(FVector2D(H->GetActorLocation())));
			R.CapsuleZ.Add(H->GetActorLocation().Z);
			if (++Frames < 75) return false;
			Move->StopMovementImmediately();
			Frames = 0; Phase = 3; return false;
		case 3:
			if (++Frames < 5) return false;
			{
				// a scripted move of Dink across the hill (the move starts from where his capsule stands)
				Story->GetGameplay()->SyncDinkFromActor();
				FDinkSprite& Dink = D->GetDink();
				Cmd(FString::Printf(TEXT(">> move 1 2 %d 1"), FMath::RoundToInt(Dink.Y) + 120));
			}
			Frames = 0; Phase = 4; return false;
		case 4:
		{
			FDinkSprite& Dink = D->GetDink();
			R.Move.Add(FIntPoint(FMath::RoundToInt(Dink.X * 1000.0), FMath::RoundToInt(Dink.Y * 1000.0)));
			R.Ground.Add(Landforms->HeightCmAt(FVector2D(H->GetActorLocation())));
			R.CapsuleZ.Add(H->GetActorLocation().Z);
			if (Dink.bMoving && ++Frames < 600) return false;
			R.End = H->GetActorLocation();
			R.DrawnLift = H->GetMesh()->GetComponentLocation().Z - H->GetActorLocation().Z;
			R.GroundAtEnd = Landforms->HeightCmAt(FVector2D(R.End));
			if (Run < 2) { ++Run; Phase = 0; return false; }
			Compare();
			Cleanup();
			return true;
		}
		default: return true;
		}
	}

private:
	void Compare()
	{
		const DinkLandformsTest::FRun& Flat = Runs[2];
		const DinkLandformsTest::FRun& Hill = Runs[1];
		int32 Settle = 0;
		for (int32 I = 0; I < FMath::Min(Runs[0].Walk.Num(), Flat.Walk.Num()); ++I) Settle += Runs[0].Walk[I] != Flat.Walk[I];
		Test->AddInfo(FString::Printf(TEXT("first flat run vs second flat run: %d of %d walk frames differ (harness settling); walk starts %s / %s / %s"),
			Settle, Flat.Walk.Num(), *Runs[0].Walk[0].ToString(), *Hill.Walk[0].ToString(), *Flat.Walk[0].ToString()));
		float MaxGround = 0.f;
		for (const float G : Hill.Ground) MaxGround = FMath::Max(MaxGround, FMath::Abs(G));
		// The editor's PIE frame step is not bit-deterministic (two FLAT runs from the same start already differ by float
		// noise; the probe's fixed 60 Hz step is, and it is the bit-exact proof). So: the hill run may differ from the flat
		// run by no more than two flat runs differ from each other, plus 1 mm; the capsule's height is the flat floor's.
		auto MaxWalk = [](const DinkLandformsTest::FRun& A, const DinkLandformsTest::FRun& B)
		{
			double M = 0.0;
			for (int32 I = 0; I < FMath::Min(A.Walk.Num(), B.Walk.Num()); ++I) M = FMath::Max(M, FVector2D::Distance(A.Walk[I], B.Walk[I]));
			return M;
		};
		const double Noise = MaxWalk(Runs[0], Flat), Diff = MaxWalk(Hill, Flat);
		Test->TestEqual(TEXT("walk frames"), Hill.Walk.Num(), Flat.Walk.Num());
		Test->TestTrue(FString::Printf(TEXT("the walk's capsule XY over relief stays within the flat runs' own noise (%.4f cm, noise %.4f cm)"), Diff, Noise),
			Diff <= Noise + 0.1);
		const int32 MoveNoise = FMath::Abs(Runs[0].Move.Num() - Flat.Move.Num());
		Test->TestTrue(FString::Printf(TEXT("the scripted move takes as many frames (%d flat, %d over relief, flat runs %d apart)"), Flat.Move.Num(), Hill.Move.Num(), MoveNoise),
			FMath::Abs(Flat.Move.Num() - Hill.Move.Num()) <= MoveNoise && Flat.Move.Num() > 5);
		const double EndNoise = FVector::Dist2D(Runs[0].End, Flat.End);
		Test->TestTrue(FString::Printf(TEXT("the move ends at the same place (%.4f cm apart, flat runs %.4f cm)"), FVector::Dist2D(Hill.End, Flat.End), EndNoise),
			FVector::Dist2D(Hill.End, Flat.End) <= EndNoise + 0.1);
		double MaxZ = 0.0;
		for (int32 I = 0; I < FMath::Min(Flat.CapsuleZ.Num(), Hill.CapsuleZ.Num()); ++I) MaxZ = FMath::Max(MaxZ, FMath::Abs(Flat.CapsuleZ[I] - Hill.CapsuleZ[I]));
		Test->TestTrue(FString::Printf(TEXT("the capsule's height is the flat floor's on every frame (max %.4f cm off)"), MaxZ), MaxZ < 0.01);
		Test->TestTrue(FString::Printf(TEXT("the run crossed real relief (up to %.1f cm under the capsule)"), MaxGround), MaxGround > 20.f);
		Test->TestEqual(TEXT("only the drawn body stands on the ground"), Hill.DrawnLift - Flat.DrawnLift, double(Hill.GroundAtEnd), 3.0);
		int32 FirstWalk = -1;
		for (int32 I = 0; I < FMath::Min(Flat.Walk.Num(), Hill.Walk.Num()) && FirstWalk < 0; ++I) if (Flat.Walk[I] != Hill.Walk[I]) FirstWalk = I;
		if (FirstWalk >= 0) Test->AddInfo(FString::Printf(TEXT("first walk difference at frame %d: flat %s hill %s (ground %.1f cm)"), FirstWalk,
			*Flat.Walk[FirstWalk].ToString(), *Hill.Walk[FirstWalk].ToString(), Hill.Ground[FirstWalk]));
		Test->AddInfo(FString::Printf(TEXT("walk %d frames, move %d frames, end (%.2f, %.2f), ground %.1f cm"), Hill.Walk.Num(), Hill.Move.Num(), Hill.End.X, Hill.End.Y, Hill.GroundAtEnd));
	}
	void Cleanup()
	{
		if (UWorld* W = World.Get())
			if (UDinkLandformsSubsystem* L = W->GetSubsystem<UDinkLandformsSubsystem>()) L->SetDataForTest(FDinkLandformsData(), false);
	}
	FAutomationTestBase* Test;
	TWeakObjectPtr<UWorld> World;
	double Began = 0.0;
	int32 Phase = 0, Frames = 0, Run = 0;
	DinkLandformsTest::FRun Runs[3];
};

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkLandformsScriptedMoveTest, "Dink.Movement.Landforms.ScriptedMoveAcrossRelief", DINK_TEST_FLAGS)
bool FDinkLandformsScriptedMoveTest::RunTest(const FString&)
{
	// Coordinator decision 16 Nov 2026: a slope never displaces Dink's map XY, never shortens or lengthens a scripted move.
	// The same walk and scripted move on SCR_439, flat and over a synthetic hill, must give the same capsule path, pixels
	// and frame count; only the drawn body rises.
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook"), FPackageName::GetMapPackageExtension());
	if (!TestNotNull(TEXT("real map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	AddCommand(new FStartPIECommand(false));
	AddCommand(new FDinkLandformsMovePIE(this));
	AddCommand(new FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkLandformsHolesTest, "Dink.Movement.Landforms.Holes", DINK_TEST_FLAGS)
bool FDinkLandformsHolesTest::RunTest(const FString&)
{
	// A10 (25 Nov 2026): the opening list of landform_holes.json cuts the ground's triangles inside each polygon, and the surface
	// the drawn bodies stand on follows the row (its floor_cm, or the ground's own height without one). Empty on master: no change.
	FDinkLandformsData D;
	FDinkLandformsScreen S;
	S.Screen = 7;
	S.Corners.NW = FVector2D(0, 0); S.Corners.NE = FVector2D(60, 0); S.Corners.SW = FVector2D(0, 40); S.Corners.SE = FVector2D(60, 40);
	S.HeightsM.Init(0.5f, D.GridW * D.GridH);
	D.Screens.Add(7, MoveTemp(S));
	const FString Json = TEXT("{\"schema\": \"dink-landform-holes/1\", \"holes\": [")
		TEXT("{\"id\": \"square\", \"screen\": 7, \"polygon_px\": [[100, 100], [200, 100], [200, 200], [100, 200]], \"floor_cm\": -40},")
		TEXT("{\"id\": \"crack\", \"screen\": 7, \"polygon_px\": [[400, 300], [500, 300], [450, 350]]},")
		TEXT("{\"id\": \"elsewhere\", \"screen\": 9999, \"polygon_px\": [[0, 0], [10, 0], [0, 10]]}]}");
	FString Error;
	int32 Skipped = -1;
	if (!TestTrue(TEXT("holes load: ") + Error, D.LoadHoles(Json, Error, Skipped))) return false;
	TestEqual(TEXT("two openings on the screen with data"), D.NumHoles(), 2);
	TestEqual(TEXT("the row on a screen without landforms is skipped"), Skipped, 1);
	TestNotNull(TEXT("a pixel inside the square is in an opening"), D.HoleAtPixel(7, 150, 150));
	TestNull(TEXT("a pixel outside is not"), D.HoleAtPixel(7, 250, 150));
	TestEqual(TEXT("inside an opening with a floor the surface is the floor"), D.HeightMAtPixel(7, 150, 150), -0.4f, 1e-4f);
	TestEqual(TEXT("the ground's own height is kept for the mesh"), D.SurfaceMAtPixel(7, 150, 150), 0.5f, 1e-4f);
	TestEqual(TEXT("inside an opening without a floor nothing moves"), D.HeightMAtPixel(7, 450, 310), 0.5f, 1e-4f);
	TestEqual(TEXT("outside every opening the surface is the ground"), D.HeightMAtPixel(7, 300, 50), 0.5f, 1e-4f);

	// the mesh: a 10 px grid as BuildScreen's far step
	const int32 Step = 10, NX = 600 / Step + 1, NY = 400 / Step + 1;
	TArray<FVector> V;
	for (int32 J = 0; J < NY; ++J)
		for (int32 I = 0; I < NX; ++I) V.Add(FVector(I * Step, J * Step, 50.0));
	TArray<int32> Full, Cut;
	int32 NumCut = -1;
	DinkLandforms::GridTriangles(V, NX, NY, Step, nullptr, Full, &NumCut);
	TestEqual(TEXT("without openings every cell has its two triangles"), Full.Num(), (NX - 1) * (NY - 1) * 6);
	TestEqual(TEXT("and nothing is cut"), NumCut, 0);
	DinkLandforms::GridTriangles(V, NX, NY, Step, D.Screens.Find(7), Cut, &NumCut);
	int32 Crack = 0;
	for (int32 K = 0; K < Cut.Num(); K += 3)
	{
		const double X = (V[Cut[K]].X + V[Cut[K + 1]].X + V[Cut[K + 2]].X) / 3.0, Y = (V[Cut[K]].Y + V[Cut[K + 1]].Y + V[Cut[K + 2]].Y) / 3.0;
		if (D.HoleAtPixel(7, X, Y)) { AddError(FString::Printf(TEXT("a kept triangle lies in an opening at %.1f,%.1f"), X, Y)); break; }
	}
	for (int32 K = 0; K < Full.Num(); K += 3)
	{
		const double X = (V[Full[K]].X + V[Full[K + 1]].X + V[Full[K + 2]].X) / 3.0, Y = (V[Full[K]].Y + V[Full[K + 1]].Y + V[Full[K + 2]].Y) / 3.0;
		Crack += (X > 400 && Y > 300 && D.HoleAtPixel(7, X, Y)) ? 1 : 0;
	}
	TestEqual(TEXT("the square opening takes its 10 x 10 cells' 200 triangles plus the crack's"), NumCut, 200 + Crack);
	TestTrue(TEXT("the crack takes some triangles"), Crack > 0);
	TestEqual(TEXT("cut + kept = the full grid"), Cut.Num() / 3 + NumCut, Full.Num() / 3);

	// malformed rows are refused as a whole (the layer then cuts nothing)
	TestFalse(TEXT("a polygon of two points is refused"), D.LoadHoles(TEXT("{\"schema\": \"dink-landform-holes/1\", \"holes\": [{\"screen\": 7, \"polygon_px\": [[0, 0], [1, 1]]}]}"), Error, Skipped));
	TestFalse(TEXT("another schema is refused"), D.LoadHoles(TEXT("{\"schema\": \"x\", \"holes\": []}"), Error, Skipped));

	// the shipped list: loads, and is empty until art adds rows (so the ground is the same as before)
	FString Shipped;
	if (TestTrue(TEXT("landform_holes.json is shipped"), FFileHelper::LoadFileToString(Shipped, *DinkLandforms::HolesPath())))
	{
		FDinkLandformsData Real;
		FString Json2; TArray<uint8> Png;
		const FString Path = DinkLandforms::DefaultPath();
		if (TestTrue(TEXT("landforms data"), FFileHelper::LoadFileToString(Json2, *Path) && FFileHelper::LoadFileToArray(Png, *(FPaths::GetPath(Path) / TEXT("landforms.png")))
			&& Real.Load(Json2, Png, Error)))
		{
			TestTrue(TEXT("the shipped list loads: ") + Error, Real.LoadHoles(Shipped, Error, Skipped));
			AddInfo(FString::Printf(TEXT("shipped openings: %d (rows on screens without landforms: %d)"), Real.NumHoles(), Skipped));
			TestEqual(TEXT("no row names a screen without landforms"), Skipped, 0);
		}
	}
	return true;
}
