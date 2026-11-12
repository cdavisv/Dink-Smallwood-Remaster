// Tests of the greybox import (pipeline stage 6). They read the import bundle (ImportData/, written
// by Scripts/export_import_bundle.py) and the generated Stonebrook map
// (/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook, Scripts/import_greybox.sh --region stonebrook).
// Expected numbers come from the bundle, never from constants here. Both inputs are git-ignored:
// when they are missing the tests pass with a warning ("skipped"), and Scripts/import_greybox.sh
// runs `Scripts/test.sh Dink.Import` itself and requires zero warnings.

#include "DinkTestHelpers.h"
#include "DinkCollision.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkLayout.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "DinkGameplay.h"
#include "DinkArtFamilySubsystem.h"
#include "Hardness/DinkFamilyCollisionFit.h"
#include "Hardness/DinkHardnessFoundationSource.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"

#include "Dom/JsonObject.h"
#include "Components/PostProcessComponent.h"
#include "Engine/Level.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "HAL/FileManager.h"
#include "MeshDescription.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "StaticMeshAttributes.h"
#include "StaticMeshOperations.h"
#include "Editor.h"
#include "AssetCompilingManager.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Tests/AutomationEditorCommon.h"
#include "UObject/UObjectIterator.h"

namespace DinkImportTest
{
	const TCHAR* StonebrookMap = TEXT("/Game/Dink/_Generated/Maps/L_Greybox_Stonebrook");
	const TCHAR* Region = TEXT("stonebrook");

	FString BundleDir()
	{
		return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("ImportData"));
	}

	TSharedPtr<FJsonObject> ReadJson(const FString& Name)
	{
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *(BundleDir() / Name)))
		{
			return nullptr;
		}
		TSharedPtr<FJsonObject> Root;
		FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root);
		return Root;
	}

	/** Loads a bundle file once per test run; nullptr (with a "skipped" warning) when the bundle is absent. */
	TSharedPtr<FJsonObject> Bundle(FAutomationTestBase& Test, const FString& Name)
	{
		TSharedPtr<FJsonObject> Root = ReadJson(Name);
		if (!Root.IsValid())
		{
			Test.AddWarning(FString::Printf(TEXT("skipped: %s/%s missing (run Scripts/import_greybox.sh)"), *BundleDir(), *Name));
		}
		return Root;
	}

	FVector2D Vec2(const TSharedPtr<FJsonValue>& V)
	{
		const TArray<TSharedPtr<FJsonValue>>& A = V->AsArray();
		return FVector2D(A[0]->AsNumber(), A[1]->AsNumber());
	}

	FDinkScreenCorners Corners(const TSharedPtr<FJsonObject>& Screen)
	{
		const TSharedPtr<FJsonObject> C = Screen->GetObjectField(TEXT("corners"));
		FDinkScreenCorners Out;
		Out.NW = Vec2(C->Values.FindRef(TEXT("nw")));
		Out.NE = Vec2(C->Values.FindRef(TEXT("ne")));
		Out.SW = Vec2(C->Values.FindRef(TEXT("sw")));
		Out.SE = Vec2(C->Values.FindRef(TEXT("se")));
		return Out;
	}

	struct FScreens
	{
		TMap<FString, TSharedPtr<FJsonObject>> ById;
		TMap<FString, FDinkScreenCorners> CornersById;
	};

	bool LoadScreens(FAutomationTestBase& Test, FScreens& Out)
	{
		TSharedPtr<FJsonObject> Root = Bundle(Test, TEXT("screens.json"));
		if (!Root)
		{
			return false;
		}
		for (const TSharedPtr<FJsonValue>& V : Root->GetArrayField(TEXT("screens")))
		{
			const TSharedPtr<FJsonObject> S = V->AsObject();
			const FString Id = S->GetStringField(TEXT("id"));
			Out.ById.Add(Id, S);
			Out.CornersById.Add(Id, Corners(S));
		}
		return true;
	}

	/** Opens a generated map in the editor world (with its always-loaded sublevels); nullptr + "skipped" if absent. */
	UWorld* OpenGenerated(FAutomationTestBase& Test, const FString& Map, const TCHAR* ImportArg)
	{
		const FString File = FPackageName::LongPackageNameToFilename(Map, FPackageName::GetMapPackageExtension());
		if (!IFileManager::Get().FileExists(*File))
		{
			Test.AddWarning(FString::Printf(TEXT("skipped: %s not generated (run Scripts/import_greybox.sh --region %s)"), *Map, ImportArg));
			return nullptr;
		}
		if (GEditor)
		{
			UWorld* Current = GEditor->GetEditorWorldContext().World();
			if (Current && Current->GetOutermost()->GetName() == Map)
			{
				return Current;
			}
		}
		UWorld* World = UEditorLoadingAndSavingUtils::LoadMap(File);
		Test.TestNotNull(TEXT("generated map loads: ") + Map, World);
		// meshes whose render/collision data is not in the DDC yet build asynchronously after load;
		// wait so the traces see every collision mesh
		FAssetCompilingManager::Get().FinishAllCompilation();
		FAssetCompilingManager::Get().ProcessAsyncTasks();
		return World;
	}

	UWorld* OpenStonebrook(FAutomationTestBase& Test)
	{
		return OpenGenerated(Test, StonebrookMap, TEXT("stonebrook"));
	}

	bool IsBlocker(const UPrimitiveComponent* C)
	{
		if (!C)
		{
			return false;
		}
		const ECollisionChannel Type = C->GetCollisionObjectType();
		return Type == DinkCollision::HardSolid || Type == DinkCollision::HardLow;
	}

	/**
	 * Vertical trace through a ground point from z = 3.5 m (above the 3 m blocker prisms; a trace
	 * that starts inside a trimesh does not hit it) down to z = 20 cm (above the ground).
	 */
	bool HitsBlocker(UWorld* World, const FVector2D& Metres, ECollisionChannel Channel, FString* OutWhat = nullptr)
	{
		const FVector Top = DinkLayout::MetresToUnreal(Metres, 3.5);
		const FVector Bottom = DinkLayout::MetresToUnreal(Metres, 0.2);
		FCollisionQueryParams Params(TEXT("DinkImportTest"), /*bTraceComplex*/ true);
		TArray<FHitResult> Hits;
		World->LineTraceMultiByChannel(Hits, Top, Bottom, Channel, Params);
		for (const FHitResult& H : Hits)
		{
			if (H.bBlockingHit && IsBlocker(H.GetComponent()))
			{
				if (OutWhat)
				{
					*OutWhat = (H.GetActor() ? H.GetActor()->GetActorLabel() : FString(TEXT("?"))) + TEXT(".") + GetNameSafe(H.GetComponent());
				}
				return true;
			}
		}
		return false;
	}
}

using namespace DinkImportTest;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkImportAxisTest, "Dink.Import.Layout.AxisMapping", DINK_TEST_FLAGS)
bool FDinkImportAxisTest::RunTest(const FString& Parameters)
{
	// metres x east / y south -> Unreal X / Y in centimetres, height -> Z
	TestEqual(TEXT("east, south, up"), DinkLayout::MetresToUnreal(FVector2D(1.5, -2.0), 3.0), FVector(150.0, -200.0, 300.0));
	TestEqual(TEXT("inverse"), DinkLayout::UnrealToMetres(FVector(150.0, -200.0, 7.0)), FVector2D(1.5, -2.0));
	// Not a mirror: turning right (clockwise seen from above) from east must face south, as on the
	// original map. In Unreal a positive yaw turns +X towards +Y.
	TestTrue(TEXT("yaw +90 turns east into south"), FRotator(0, 90, 0).RotateVector(FVector(1, 0, 0)).Equals(FVector(0, 1, 0), 1e-6));
	TestTrue(TEXT("east x south = up (left-handed, Z up)"), FVector::CrossProduct(FVector(1, 0, 0), FVector(0, 1, 0)).Equals(FVector(0, 0, 1)));

	// bilinear map on a skewed quad: corners, centre, inverse
	FDinkScreenCorners C;
	C.NW = FVector2D(10, 20);
	C.NE = FVector2D(70, 21);
	C.SW = FVector2D(11, 60);
	C.SE = FVector2D(72, 63);
	TestTrue(TEXT("nw"), DinkLayout::MapPixelToMetres(C, 0, 0).Equals(C.NW, 1e-12));
	TestTrue(TEXT("ne"), DinkLayout::MapPixelToMetres(C, 600, 0).Equals(C.NE, 1e-12));
	TestTrue(TEXT("sw"), DinkLayout::MapPixelToMetres(C, 0, 400).Equals(C.SW, 1e-12));
	TestTrue(TEXT("se"), DinkLayout::MapPixelToMetres(C, 600, 400).Equals(C.SE, 1e-12));
	TestTrue(TEXT("centre"), DinkLayout::MapPixelToMetres(C, 300, 200).Equals((C.NW + C.NE + C.SW + C.SE) * 0.25, 1e-12));
	double X = 0, Y = 0;
	TestTrue(TEXT("inverse converges"), DinkLayout::MetresToMapPixel(C, DinkLayout::MapPixelToMetres(C, 123.4, 321.0), X, Y));
	TestTrue(TEXT("inverse x"), FMath::IsNearlyEqual(X, 123.4, 1e-6));
	TestTrue(TEXT("inverse y"), FMath::IsNearlyEqual(Y, 321.0, 1e-6));
	TestTrue(TEXT("contains inside"), DinkLayout::ContainsMetres(C, DinkLayout::MapPixelToMetres(C, 1, 399)));
	TestFalse(TEXT("excludes outside"), DinkLayout::ContainsMetres(C, DinkLayout::MapPixelToMetres(C, -2, 200)));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkImportLayoutMatchTest, "Dink.Import.Layout.MatchesWorldLayout", DINK_TEST_FLAGS)
bool FDinkImportLayoutMatchTest::RunTest(const FString& Parameters)
{
	FScreens Screens;
	TSharedPtr<FJsonObject> Placements = Bundle(*this, TEXT("placements.json"));
	if (!LoadScreens(*this, Screens) || !Placements)
	{
		return true;
	}
	// Every placement: the C++ transform of its map pixel against the position tools/analyse wrote
	// into world_layout.json (rounded there to 0.1 mm), and the local east axis against rot_deg.
	double MaxErr = 0.0, MaxYawErr = 0.0;
	FString Worst;
	int32 N = 0;
	for (const TSharedPtr<FJsonValue>& V : Placements->GetArrayField(TEXT("placements")))
	{
		const TSharedPtr<FJsonObject> P = V->AsObject();
		const FString ScreenId = FString::Printf(TEXT("SCR_%03d"), (int32)P->GetNumberField(TEXT("screen")));
		const FDinkScreenCorners* C = Screens.CornersById.Find(ScreenId);
		if (!C)
		{
			AddError(ScreenId + TEXT(" missing from screens.json"));
			continue;
		}
		const double MX = P->GetNumberField(TEXT("map_x"));
		const double MY = P->GetNumberField(TEXT("map_y"));
		const FVector2D Want = Vec2(P->Values.FindRef(TEXT("world")));
		const double Err = (DinkLayout::MapPixelToMetres(*C, MX, MY) - Want).Size();
		if (Err > MaxErr)
		{
			MaxErr = Err;
			Worst = P->GetStringField(TEXT("id"));
		}
		const double YawErr = FMath::Abs(FMath::FindDeltaAngleDegrees(DinkLayout::LocalEastYawDegrees(*C, MX, MY), P->GetNumberField(TEXT("rot_deg"))));
		MaxYawErr = FMath::Max(MaxYawErr, YawErr);
		++N;
	}
	AddInfo(FString::Printf(TEXT("%d placements: max position error %.6f m (%s), max yaw error %.4f deg"), N, MaxErr, *Worst, MaxYawErr));
	TestTrue(TEXT("all placements checked"), N > 5000);
	TestTrue(FString::Printf(TEXT("positions match world_layout.json within 1 mm (max %.6f m at %s)"), MaxErr, *Worst), MaxErr < 1e-3);
	TestTrue(FString::Printf(TEXT("local east axis matches rot_deg within 0.05 deg (max %.4f)"), MaxYawErr), MaxYawErr < 0.05);

	// start position from the bundle (new game: screen 1, map 314,161)
	TSharedPtr<FJsonObject> Manifest = Bundle(*this, TEXT("bundle.json"));
	if (Manifest)
	{
		const TSharedPtr<FJsonObject> Start = Manifest->GetObjectField(TEXT("start"));
		const FDinkScreenCorners* C = Screens.CornersById.Find(FString::Printf(TEXT("SCR_%03d"), (int32)Start->GetNumberField(TEXT("screen"))));
		TestNotNull(TEXT("start screen exists"), C);
		if (C)
		{
			const FVector2D Got = DinkLayout::MapPixelToMetres(*C, Start->GetNumberField(TEXT("x")), Start->GetNumberField(TEXT("y")));
			TestTrue(TEXT("start position"), Got.Equals(Vec2(Start->Values.FindRef(TEXT("world"))), 1e-3));
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkImportContinuityTest, "Dink.Import.Layout.Continuity", DINK_TEST_FLAGS)
bool FDinkImportContinuityTest::RunTest(const FString& Parameters)
{
	FScreens Screens;
	TSharedPtr<FJsonObject> Samples = Bundle(*this, TEXT("samples.json"));
	if (!LoadScreens(*this, Screens) || !Samples)
	{
		return true;
	}
	// Every walkable crossing between two screens of one sheet: points along the shared edge must
	// land on the same world position from both sides (no seam the player could fall into).
	double MaxGap = 0.0;
	int32 Links = 0, Seams = 0, Points = 0, CutUnreached = 0;
	for (const TSharedPtr<FJsonValue>& V : Samples->GetArrayField(TEXT("links")))
	{
		const TSharedPtr<FJsonObject> L = V->AsObject();
		const FDinkScreenCorners* A = Screens.CornersById.Find(L->GetStringField(TEXT("a")));
		const FDinkScreenCorners* B = Screens.CornersById.Find(L->GetStringField(TEXT("b")));
		if (!A || !B)
		{
			continue;
		}
		if (!L->GetBoolField(TEXT("same_sheet")))
		{
			// tools/analyse cuts 22 walkable crossings between sheets; none may be reachable
			Seams += L->GetBoolField(TEXT("reached")) ? 1 : 0;
			++CutUnreached;
			continue;
		}
		++Links;
		const FString Dir = L->GetStringField(TEXT("dir"));
		const double From = L->GetNumberField(TEXT("from")), To = L->GetNumberField(TEXT("to"));
		for (int32 I = 0; I <= 8; ++I)
		{
			const double T = From + (To - From) * I / 8.0;
			FVector2D PA, PB;
			if (Dir == TEXT("right")) { PA = DinkLayout::MapPixelToMetres(*A, 600, T); PB = DinkLayout::MapPixelToMetres(*B, 0, T); }
			else if (Dir == TEXT("left")) { PA = DinkLayout::MapPixelToMetres(*A, 0, T); PB = DinkLayout::MapPixelToMetres(*B, 600, T); }
			else if (Dir == TEXT("down")) { PA = DinkLayout::MapPixelToMetres(*A, T, 400); PB = DinkLayout::MapPixelToMetres(*B, T, 0); }
			else { PA = DinkLayout::MapPixelToMetres(*A, T, 0); PB = DinkLayout::MapPixelToMetres(*B, T, 400); }
			MaxGap = FMath::Max(MaxGap, (PA - PB).Size());
			++Points;
		}
	}
	AddInfo(FString::Printf(TEXT("%d walkable crossings, %d points, max gap %.9f m; %d crossings cut between sheets (%d of them reached)"), Links, Points, MaxGap, CutUnreached, Seams));
	TestTrue(TEXT("crossings found"), Links > 1000);
	TestTrue(FString::Printf(TEXT("continuous across walkable screen edges (max gap %.9f m)"), MaxGap), MaxGap < 1e-6);
	TestEqual(TEXT("no reached walkable crossing is cut between sheets"), Seams, 0);
	return true;
}

namespace DinkImportTest
{
	void CheckCollision(FAutomationTestBase& Test, const FString& Map, const FString& RegionKey);

	void CheckContentIn(FAutomationTestBase& Test, UWorld* World, const TSharedPtr<FJsonObject>& Manifest,
		const TSharedPtr<FJsonObject>& Placements, const FString& RegionKey);

	/**
	 * Content of a generated map against the bundle: one origin-tagged actor or instance per
	 * placement of the region, unique origin IDs, one screen volume per screen, every warp trigger,
	 * vision-gated placements with their condition. RegionKey "all" = the whole world.
	 */
	void CheckContent(FAutomationTestBase& Test, const FString& Map, const FString& RegionKey)
	{
		TSharedPtr<FJsonObject> Manifest = Bundle(Test, TEXT("bundle.json"));
		TSharedPtr<FJsonObject> Placements = Bundle(Test, TEXT("placements.json"));
		if (!Manifest || !Placements)
		{
			return;
		}
		UWorld* World = OpenGenerated(Test, Map, *RegionKey);
		if (!World)
		{
			return;
		}
		CheckContentIn(Test, World, Manifest, Placements, RegionKey);
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkImportStonebrookContentTest, "Dink.Import.Greybox.StonebrookContent", DINK_TEST_FLAGS)
bool FDinkImportStonebrookContentTest::RunTest(const FString& Parameters)
{
	CheckContent(*this, StonebrookMap, Region);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkImportWorldContentTest, "Dink.Import.Greybox.WorldContent", DINK_TEST_FLAGS)
bool FDinkImportWorldContentTest::RunTest(const FString& Parameters)
{
	CheckContent(*this, TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), TEXT("all"));
	return true;
}

void DinkImportTest::CheckContentIn(FAutomationTestBase& Test, UWorld* World, const TSharedPtr<FJsonObject>& Manifest,
	const TSharedPtr<FJsonObject>& Placements, const FString& RegionKey)
{
	const bool bAll = RegionKey == TEXT("all");
	const TSharedPtr<FJsonObject> Expect = Manifest->GetObjectField(TEXT("counts"))->GetObjectField(RegionKey);
	const int32 ExpScreens = (int32)Expect->GetNumberField(TEXT("screens"));
	int32 ExpActors = (int32)Expect->GetNumberField(TEXT("placement_actors"));
	int32 ExpInstances = (int32)Expect->GetNumberField(TEXT("placement_instances"));
	const int32 ExpWarps = (int32)Expect->GetNumberField(TEXT("warps"));
	const int32 ExpVision = (int32)Expect->GetNumberField(TEXT("vision_gated"));

	FString FamiliesText, PolicyError;
	TArray<FDinkFamilyCollisionFitRule> FitRules;
	if (!Test.TestTrue(TEXT("source collision-fit policy loads"),
		FFileHelper::LoadFileToString(FamiliesText, *DinkArtFamily::DefaultFamiliesPath()) &&
		DinkFamilyCollisionFit::ParsePolicy(FamiliesText, FitRules, PolicyError)))
	{
		Test.AddError(PolicyError); return;
	}
	TSet<int32> MarkedScreens;
	for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It)
		if (It->ActorHasTag(TEXT("DinkHardnessWorldV1"))) MarkedScreens.Add(It->ScreenNumber);
	TMap<FString, const FDinkFamilyCollisionFitRule*> Promoted;
	TMap<FString, bool> ExpectedActors;
	TSet<FString> Expected;
	for (const TSharedPtr<FJsonValue>& V : Placements->GetArrayField(TEXT("placements")))
	{
		const TSharedPtr<FJsonObject> P = V->AsObject();
		if ((bAll || P->GetStringField(TEXT("region")) == RegionKey) && P->GetStringField(TEXT("excluded")).IsEmpty())
		{
			const FString Id = P->GetStringField(TEXT("id"));
			Expected.Add(Id);
			const FString Representation = P->GetStringField(TEXT("representation"));
			if (!Test.TestTrue(TEXT("source representation is explicit: ") + Id,
				Representation == TEXT("actor") || Representation == TEXT("instance"))) return;
			const auto* Rule = FitRules.FindByPredicate([&](const auto& R) { return R.Origin.ToString() == Id; });
			const bool Promote = Rule && Rule->IsStaticBackground() && MarkedScreens.Contains(Rule->Origin.Screen);
			if (Promote)
			{
				if (!Test.TestTrue(TEXT("promoted source remains an exact original background: ") + Id,
					Representation == TEXT("instance") && P->GetNumberField(TEXT("type")) == 0 &&
					P->GetStringField(TEXT("hash")) == Rule->SourceHash &&
					FName(*P->GetStringField(TEXT("script"))) == Rule->SourceScript)) return;
				Promoted.Add(Id, Rule); ++ExpActors; --ExpInstances;
			}
			ExpectedActors.Add(Id, Representation == TEXT("actor") || Promote);
		}
	}

	int32 OriginActors = 0, Instances = 0, ScreenVolumes = 0, Warps = 0, VisionActors = 0, VisionWithRule = 0;
	TSet<FString> Seen;
	TSet<int32> ScreenNumbers;
	TArray<FString> Duplicates;
	auto See = [&](const FDinkOriginId& Id)
	{
		const FString S = Id.ToString();
		if (Seen.Contains(S))
		{
			Duplicates.Add(S);
		}
		Seen.Add(S);
	};
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		AActor* A = *It;
		if (const UDinkOriginComponent* O = A->FindComponentByClass<UDinkOriginComponent>())
		{
			++OriginActors;
			See(O->OriginId);
			const FString Id = O->OriginId.ToString();
			Test.TestTrue(TEXT("source expects this placement as an actor: ") + Id, ExpectedActors.FindRef(Id));
			if (const auto* Rule = Promoted.FindRef(Id))
				Test.TestTrue(TEXT("promoted carrier retains type, script, hash and promotion tag: ") + Id,
					O->PlacementType == 0 && O->ScriptName == Rule->SourceScript && O->SourceHash == Rule->SourceHash &&
					A->ActorHasTag(DinkFamilyCollisionFit::PromotedBackgroundTag));
			Test.TestTrue(TEXT("origin has a category"), !O->Category.IsNone());
		}
		if (const UDinkInstanceOriginsComponent* IO = A->FindComponentByClass<UDinkInstanceOriginsComponent>())
		{
			for (const FDinkInstanceOrigin& I : IO->Origins)
			{
				++Instances;
				See(I.OriginId);
				const FString Id = I.OriginId.ToString();
				Test.TestTrue(TEXT("source expects this placement as an instance: ") + Id,
					ExpectedActors.Contains(Id) && !ExpectedActors.FindRef(Id));
			}
		}
		if (const ADinkScreenVolume* S = Cast<ADinkScreenVolume>(A))
		{
			++ScreenVolumes;
			ScreenNumbers.Add(S->ScreenNumber);
			if (!bAll)
			{
				Test.TestEqual(FString::Printf(TEXT("%s region"), *S->ScreenId.ToString()), S->Region.ToString(), RegionKey);
			}
		}
		TInlineComponentArray<UDinkWarpComponent*> WarpComps(A);
		Warps += WarpComps.Num();
		if (const ADinkPlaceholderActor* P = Cast<ADinkPlaceholderActor>(A); P && P->Vision != 0)
		{
			++VisionActors;
			VisionWithRule += (P->VisionCondition.Fact == FName(TEXT("vision")) && P->VisionCondition.Value == P->Vision && P->VisionRules.Num() > 0) ? 1 : 0;
		}
	}
	Test.AddInfo(FString::Printf(TEXT("%d origin actors, %d instances, %d screen volumes, %d warps, %d vision-gated"), OriginActors, Instances, ScreenVolumes, Warps, VisionActors));
	Test.TestEqual(TEXT("placement actors with UDinkOriginComponent"), OriginActors, ExpActors);
	Test.TestEqual(TEXT("background instances with origins"), Instances, ExpInstances);
	Test.TestEqual(TEXT("screen volumes"), ScreenVolumes, ExpScreens);
	Test.TestEqual(TEXT("distinct screens"), ScreenNumbers.Num(), ExpScreens);
	Test.TestEqual(TEXT("warp triggers"), Warps, ExpWarps);
	Test.TestEqual(TEXT("vision-gated placeholders"), VisionActors, ExpVision);
	Test.TestEqual(TEXT("vision-gated placeholders carry their condition and rule"), VisionWithRule, ExpVision);
	Test.TestEqual(TEXT("no duplicate origin IDs"), Duplicates.Num(), 0);
	if (Duplicates.Num())
	{
		Test.AddError(TEXT("duplicates: ") + FString::Join(Duplicates, TEXT(", ")));
	}
	Test.TestEqual(TEXT("every region placement imported exactly once"), Seen.Num(), Expected.Num());
	int32 Missing = 0;
	for (const FString& Id : Expected)
	{
		Missing += Seen.Contains(Id) ? 0 : 1;
	}
	Test.TestEqual(TEXT("no region placement missing"), Missing, 0);
}

/**
 * Collision of a generated map against the original hardness maps: sampled walkable pixels are free
 * of blockers and have ground under them; sampled solid pixels block walkers and projectiles; sampled
 * low pixels block walkers only; the new-game start and every warp destination stand on free ground.
 */
void DinkImportTest::CheckCollision(FAutomationTestBase& Test, const FString& Map, const FString& RegionKey)
{
	const bool bAll = RegionKey == TEXT("all");
	FScreens Screens;
	TSharedPtr<FJsonObject> Samples = Bundle(Test, TEXT("samples.json"));
	TSharedPtr<FJsonObject> Warps = Bundle(Test, TEXT("warps.json"));
	TSharedPtr<FJsonObject> Manifest = Bundle(Test, TEXT("bundle.json"));
	if (!LoadScreens(Test, Screens) || !Samples || !Warps || !Manifest)
	{
		return;
	}
	UWorld* World = OpenGenerated(Test, Map, *RegionKey);
	if (!World)
	{
		return;
	}
	// A versioned host stores immutable floor/fill in the editor. Original tile
	// and placement bodies are admitted by the game-world owner, not baked back
	// into these meshes. Verify every actual foundation triangle before using
	// source fill rectangles as the editor's expected collision at sample points.
	TMap<FString, FDinkHardnessFoundationSource> Foundations;
	for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It)
	{
		if (!It->ActorHasTag(TEXT("DinkHardnessWorldV1"))) continue;
		const FString Id = FString::Printf(TEXT("SCR_%03d"), It->ScreenNumber);
		ADinkScreenVolume* Volume = nullptr;
		int32 VolumeCount = 0;
		for (TActorIterator<ADinkScreenVolume> V(World); V; ++V)
			if (V->ScreenNumber == It->ScreenNumber) { Volume = *V; ++VolumeCount; }
		if (!Test.TestTrue(TEXT("versioned editor host has one source volume: ") + Id,
			VolumeCount == 1 && !Foundations.Contains(Id))) return;
		FDinkHardnessFoundationSource Source; FString Error;
		const FString File = FDinkGameplayData::GetDataPath(*FString::Printf(TEXT("Hardness/Foundations/%s.json"), *Id));
		if (!Test.TestTrue(TEXT("complete source-backed editor foundation geometry: ") + Id,
			FDinkHardnessFoundationSource::Load(File, It->ScreenNumber, Source, Error) &&
			Source.VerifyGameplayInputs(Error) && Source.VerifyInstances(*Volume, **It, Error)))
		{ Test.AddError(Error); return; }
		Foundations.Add(Id, MoveTemp(Source));
	}
	int32 Walk = 0, WalkBad = 0, Solid = 0, SolidBad = 0, Low = 0, LowBad = 0, Ground = 0, GroundBad = 0, FoundationSamples = 0;
	TArray<FString> Bad;
	const TSharedPtr<FJsonObject> PerScreen = Samples->GetObjectField(TEXT("screens"));
	for (const auto& Pair : Screens.ById)
	{
		if ((!bAll && Pair.Value->GetStringField(TEXT("region")) != RegionKey) || !Pair.Value->GetStringField(TEXT("excluded")).IsEmpty())
		{
			continue;
		}
		const TSharedPtr<FJsonObject>* S = nullptr;
		if (!PerScreen->TryGetObjectField(Pair.Key, S))
		{
			continue;
		}
		for (const TSharedPtr<FJsonValue>& V : (*S)->GetArrayField(TEXT("walkable")))
		{
			const TSharedPtr<FJsonObject> P = V->AsObject();
			const FVector2D M = Vec2(P->Values.FindRef(TEXT("world")));
			FString What;
			++Walk;
			if (HitsBlocker(World, M, ECC_Pawn, &What))
			{
				++WalkBad;
				Bad.Add(FString::Printf(TEXT("%s walkable (%.1f,%.1f) blocked by %s"), *Pair.Key, P->GetNumberField(TEXT("x")), P->GetNumberField(TEXT("y")), *What));
			}
			// the ground is there and collidable
			FHitResult Hit;
			FCollisionQueryParams Params(TEXT("DinkGround"), true);
			++Ground;
			if (!World->LineTraceSingleByChannel(Hit, DinkLayout::MetresToUnreal(M, 0.1), DinkLayout::MetresToUnreal(M, -0.1), ECC_Pawn, Params) ||
				!IsBlocker(Hit.GetComponent()) || FMath::Abs(Hit.ImpactPoint.Z) > 1.0)
			{
				++GroundBad;
				Bad.Add(FString::Printf(TEXT("%s no ground under (%.1f,%.1f)"), *Pair.Key, P->GetNumberField(TEXT("x")), P->GetNumberField(TEXT("y"))));
			}
		}
		for (const TSharedPtr<FJsonValue>& V : (*S)->GetArrayField(TEXT("blocked")))
		{
			const TSharedPtr<FJsonObject> P = V->AsObject();
			const FVector2D M = Vec2(P->Values.FindRef(TEXT("world")));
			const bool bLow = P->GetStringField(TEXT("class")) == TEXT("low");
			const bool bPawn = HitsBlocker(World, M, ECC_Pawn);
			const bool bProjectile = HitsBlocker(World, M, DinkCollision::Projectile);
			// Legacy hosts retain their full original prisms. Versioned hosts expose
			// only verified immutable fill here; all old samples are still checked,
			// including required clearance outside that fill. Dedicated game-world
			// tests validate admitted original bodies and fitted logical overlays.
			bool ExpectedPawn = true, ExpectedProjectile = !bLow;
			if (const auto* Foundation = Foundations.Find(Pair.Key))
			{
				const FIntPoint Cell(FMath::FloorToInt(P->GetNumberField(TEXT("x"))), FMath::FloorToInt(P->GetNumberField(TEXT("y"))));
				auto Contains = [&](const TArray<FIntRect>& Rects)
				{ for (const auto& Rect : Rects) if (Rect.Contains(Cell)) return true; return false; };
				ExpectedProjectile = Contains(Foundation->SolidFill);
				ExpectedPawn = ExpectedProjectile || Contains(Foundation->WaterFill);
				++FoundationSamples;
			}
			const bool bOk = bPawn == ExpectedPawn && bProjectile == ExpectedProjectile;
			(bLow ? Low : Solid)++;
			if (!bOk)
			{
				(bLow ? LowBad : SolidBad)++;
				Bad.Add(FString::Printf(TEXT("%s %s code %d at (%.1f,%.1f): pawn %d projectile %d expected pawn %d projectile %d"), *Pair.Key, bLow ? TEXT("low") : TEXT("solid"),
					(int32)P->GetNumberField(TEXT("code")), P->GetNumberField(TEXT("x")), P->GetNumberField(TEXT("y")), bPawn, bProjectile, ExpectedPawn, ExpectedProjectile));
			}
		}
	}

	// Point samples cannot detect a passage too narrow for the player. Sweep the complete
	// capsule around the table/bed diagonal: 56 cm fits, the old template width of 84 cm does not.
	for (TActorIterator<ADinkScreenVolume> It(World); It; ++It)
	{
		if (It->ScreenNumber != 1) { continue; }
		const FVector2D Route[] = {{314,161}, {370,161}, {370,248.69}, {344.5,258.5}, {303.5,274.27}, {303.5,370}};
		int32 FixedBlocked = 0, OriginalBlocked = 0;
		for (int32 I = 1; I < UE_ARRAY_COUNT(Route); ++I)
		{
			const FVector A = It->MapPixelToWorld(Route[I-1].X, Route[I-1].Y) + FVector(0,0,98);
			const FVector B = It->MapPixelToWorld(Route[I].X, Route[I].Y) + FVector(0,0,98);
			const FCollisionQueryParams Params(TEXT("DinkHouseCapsuleRoute"), true);
			FixedBlocked += World->SweepTestByChannel(A, B, FQuat::Identity, ECC_Pawn, FCollisionShape::MakeCapsule(28.f,96.f), Params) ? 1 : 0;
			OriginalBlocked += World->SweepTestByChannel(A, B, FQuat::Identity, ECC_Pawn, FCollisionShape::MakeCapsule(42.f,96.f), Params) ? 1 : 0;
		}
		Test.TestEqual(TEXT("56 cm capsule can pass from start around table to front door"), FixedBlocked, 0);
		Test.TestTrue(TEXT("reproduced original 84 cm capsule blocked between table and bed"), OriginalBlocked > 0);
		Test.AddInfo(FString::Printf(TEXT("House route capsule sweeps: fixed width 56 cm %d blocked, original width 84 cm %d blocked"), FixedBlocked, OriginalBlocked));
		break;
	}

	// the new-game start and every enabled warp destination inside the region stand on free ground
	int32 Dest = 0, DestBad = 0;
	const TSharedPtr<FJsonObject> Start = Manifest->GetObjectField(TEXT("start"));
	if (HitsBlocker(World, Vec2(Start->Values.FindRef(TEXT("world"))), ECC_Pawn))
	{
		Test.AddError(TEXT("new-game start is inside a blocker"));
	}
	for (const TSharedPtr<FJsonValue>& V : Warps->GetArrayField(TEXT("warps")))
	{
		const TSharedPtr<FJsonObject> W = V->AsObject();
		const FString Dst = FString::Printf(TEXT("SCR_%03d"), (int32)W->GetNumberField(TEXT("dst_screen")));
		const TSharedPtr<FJsonObject>* DS = Screens.ById.Find(Dst);
		if (!DS || (!bAll && (*DS)->GetStringField(TEXT("region")) != RegionKey) || !W->GetBoolField(TEXT("dst_valid")) ||
			!(*DS)->GetStringField(TEXT("excluded")).IsEmpty())
		{
			continue;
		}
		const double DX = W->GetNumberField(TEXT("dst_x")), DY = W->GetNumberField(TEXT("dst_y"));
		if (DX < 0 || DX > 600 || DY < 0 || DY > 400)
		{
			// SW_s2-culg_L42 sends Dink to y 480 on SCR_066, below the 400 px map (a script quirk;
			// it is an inactive marker in the greybox). Reported by the exporter; not a ground point.
			Test.AddInfo(FString::Printf(TEXT("warp %s destination (%.0f,%.0f) is outside the 600x400 map; not checked"), *W->GetStringField(TEXT("id")), DX, DY));
			continue;
		}
		++Dest;
		FString What;
		const FVector2D DM = Vec2(W->Values.FindRef(TEXT("dst_world")));
		if (HitsBlocker(World, DM, ECC_Pawn, &What))
		{
			++DestBad;
			Bad.Add(FString::Printf(TEXT("warp %s destination blocked by %s"), *W->GetStringField(TEXT("id")), *What));
		}
		FHitResult Floor;
		FCollisionQueryParams FloorParams(TEXT("DinkWarpFloor"), true);
		if (!World->LineTraceSingleByChannel(Floor, DinkLayout::MetresToUnreal(DM, 0.1), DinkLayout::MetresToUnreal(DM, -0.1), ECC_Pawn, FloorParams))
		{
			++DestBad;
			Bad.Add(FString::Printf(TEXT("warp %s destination has no ground"), *W->GetStringField(TEXT("id"))));
		}
	}
	for (int32 I = 0; I < FMath::Min(Bad.Num(), 20); ++I)
	{
		Test.AddError(Bad[I]);
	}
	Test.AddInfo(FString::Printf(TEXT("walkable %d (%d blocked), ground %d (%d missing), solid %d (%d wrong), low %d (%d wrong), warp destinations %d (%d blocked)"),
		Walk, WalkBad, Ground, GroundBad, Solid, SolidBad, Low, LowBad, Dest, DestBad));
	Test.AddInfo(FString::Printf(TEXT("%d versioned editor foundations verified in full; %d old blocked samples checked against immutable fill (game-world bodies tested separately)"), Foundations.Num(), FoundationSamples));
	Test.TestTrue(TEXT("samples present"), Walk > 100 && Solid > 50);
	Test.TestEqual(TEXT("known-walkable points are free"), WalkBad, 0);
	Test.TestEqual(TEXT("ground under walkable points"), GroundBad, 0);
	Test.TestEqual(TEXT("known solid points block walkers and projectiles"), SolidBad, 0);
	Test.TestEqual(TEXT("known low points block walkers only"), LowBad, 0);
	Test.TestEqual(TEXT("warp destinations are free and have ground"), DestBad, 0);
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkImportStonebrookCollisionTest, "Dink.Import.Greybox.StonebrookCollision", DINK_TEST_FLAGS)
bool FDinkImportStonebrookCollisionTest::RunTest(const FString& Parameters)
{
	CheckCollision(*this, StonebrookMap, Region);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkImportWorldCollisionTest, "Dink.Import.Greybox.WorldCollision", DINK_TEST_FLAGS)
bool FDinkImportWorldCollisionTest::RunTest(const FString& Parameters)
{
	CheckCollision(*this, TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), TEXT("all"));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkImportMeshTest, "Dink.Import.Greybox.Meshes", DINK_TEST_FLAGS)
bool FDinkImportMeshTest::RunTest(const FString& Parameters)
{
	// Face orientation as Unreal computes it (FStaticMeshOperations, the same code the mesh build
	// runs): the ground must face up and the sprite card must face south (+Y).
	auto CheckFacing = [this](const TCHAR* Path, const FVector3f& Want, const TCHAR* What)
	{
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (!Mesh)
		{
			AddWarning(FString::Printf(TEXT("skipped: %s not generated"), Path));
			return;
		}
		FMeshDescription Desc = *Mesh->GetMeshDescription(0);
		FStaticMeshOperations::ComputeTriangleTangentsAndNormals(Desc);
		TTriangleAttributesRef<FVector3f> Normals = Desc.TriangleAttributes().GetAttributesRef<FVector3f>(MeshAttribute::Triangle::Normal);
		const FPolygonGroupID First = *Desc.PolygonGroups().GetElementIDs().begin();
		int32 Good = 0, Total = 0;
		for (const FTriangleID T : Desc.Triangles().GetElementIDs())
		{
			if (Desc.GetTrianglePolygonGroup(T) != First)
			{
				continue;
			}
			++Total;
			Good += FVector3f::DotProduct(Normals[T], Want) > 0.99f ? 1 : 0;
		}
		TestTrue(FString::Printf(TEXT("%s has triangles"), What), Total > 0);
		TestEqual(FString::Printf(TEXT("%s triangles facing %s"), What, *Want.ToString()), Good, Total);
	};
	CheckFacing(TEXT("/Game/Dink/_Generated/Screens/SCR_001/SM_SCR_001_Visual.SM_SCR_001_Visual"), FVector3f(0, 0, 1), TEXT("ground of SCR_001"));
	CheckFacing(TEXT("/Game/Dink/_Generated/Shared/SM_DinkCard.SM_DinkCard"), FVector3f(0, 1, 0), TEXT("sprite card"));
	return true;
}

namespace DinkImportTest
{
	/**
	 * Walks the actual route around the table, through the front door and back. Never teleports
	 * into a trigger: the old test did that and missed the capsule sealing the table/bed passage.
	 */
	class FDinkPlayCheckCommand : public IAutomationLatentCommand
	{
	public:
		FDinkPlayCheckCommand(FAutomationTestBase* InTest, FVector2D InStartMetres)
			: Test(InTest), StartMetres(InStartMetres), Began(FPlatformTime::Seconds()) {}

		virtual bool Update() override
		{
			const double Now = FPlatformTime::Seconds();
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
			ADinkGreyboxCharacter* Hero = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
			if (Now - Began > 75.0)
			{
				Test->AddError(FString::Printf(TEXT("Walking door test timed out at stage %d waypoint %d, position %s"),
					Stage, Waypoint, Hero ? *Hero->GetActorLocation().ToString() : TEXT("no pawn")));
				return true;
			}
			if (!Hero) { return false; }
			if (Hero->GetActorLocation().Z < -100.0)
			{
				Test->AddError(FString::Printf(TEXT("Player fell below the floor at stage %d waypoint %d: %s"),
					Stage, Waypoint, *Hero->GetActorLocation().ToString()));
				return true;
			}
			UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
			UDinkStorySubsystem* Story = World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>();
			if (!Greybox || !Story || Story->bNewGamePending) { return false; }
			ADinkScreenVolume* Screen = Greybox->FindScreenAt(Hero->GetActorLocation());
			if (Stage == 0)
			{
				const FVector2D At = DinkLayout::UnrealToMetres(Hero->GetActorLocation());
				Test->TestTrue(TEXT("spawned at the new-game start"), (At - StartMetres).Size() < 1.0);
				Test->TestEqual(TEXT("run speed 6 m/s"), Hero->GetCharacterMovement()->MaxWalkSpeed, 600.f);
				Test->TestNotNull(TEXT("template mannequin mesh loaded"), Hero->GetMesh()->GetSkeletalMeshAsset());
				// Exposure volumes need a real query shape; a NoCollision parent makes
				// EncompassesPoint fail even when the component is enabled and correctly placed.
				bool bAuthoredRoom = false;
				for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It) { bAuthoredRoom |= It->ScreenNumber == 1 && It->ActorHasTag(TEXT("DinkAuthoredArt")); }
				if (bAuthoredRoom)
				{
					int32 Volumes = 0;
					for (TObjectIterator<UPostProcessComponent> It; It; ++It)
					{
						if (It->GetWorld() != World || It->GetFName() != TEXT("ArtExposure")) { continue; }
						++Volumes;
						Test->TestTrue(TEXT("authored exposure contains the player at start"), It->EncompassesPoint(Hero->GetActorLocation(), 0.f, nullptr));
						// Owner-scoped exposure deliberately follows a camera outside these bounds.
                        // Keep testing the physical query shape; dedicated lifecycle tests cover
                        // disabling the provider when the actual pawn leaves the owner room.
                        const UPrimitiveComponent* Parent=Cast<UPrimitiveComponent>(It->GetAttachParent());
                        Test->TestNotNull(TEXT("exposure keeps its architectural query bounds"),Parent);
                        if (Parent) Test->TestFalse(TEXT("architectural exposure bounds remain local"),Parent->Bounds.GetBox().IsInside(Hero->GetActorLocation()+FVector(10000,10000,0)));
					}
					Test->TestTrue(TEXT("authored house exposure volume exists"), Volumes > 0);
				}
				int32 Gated = 0, Hidden = 0;
				for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
				{
					if (It->Vision != 0 && It->ScreenNumber == 1)
					{
						++Gated;
						Hidden += It->IsHidden() ? 1 : 0;
					}
				}
				Test->TestTrue(TEXT("SCR_001 has vision-gated placements"), Gated > 0);
				Test->TestEqual(TEXT("vision-gated placements start hidden"), Hidden, Gated);
				Test->TestTrue(TEXT("dink.Vision 1 1 shows burning-house set"), Greybox->SetScreenVision(1, 1) > 0);
				Greybox->SetScreenVision(1, 0);
				for (TObjectIterator<UDinkWarpComponent> It; It; ++It)
				{
					if (It->GetWorld() == World && It->WarpId == TEXT("S001_P25")) { Exit = *It; }
					if (It->GetWorld() == World && It->WarpId == TEXT("S439_P13")) { Entrance = *It; }
				}
				Test->TestNotNull(TEXT("front door exit present"), Exit);
				Test->TestNotNull(TEXT("front door entrance present"), Entrance);
				if (!Exit || !Entrance) { return true; }
				Home = Greybox->FindScreen(1);
				Outside = Greybox->FindScreen(439);
				if (!Home || !Outside) { Test->AddError(TEXT("House screens missing")); return true; }
				Stage = 1;
			}
			if (Stage == 1)
			{
				// This is the same action as the player's Space key; no freeze flags or facts are bypassed.
				Story->SkipDialogue();
				if (PC->IsMoveInputIgnored() || World->GetTimeSeconds() < 2.0) { return false; }
				Hero->GetCharacterMovement()->MaxWalkSpeed = 150.f;
				Stage = 2;
			}
			if (Stage == 2)
			{
				if (Screen && Screen->ScreenNumber == 439)
				{
					Test->TestTrue(TEXT("walked through exit to its destination"),
						FVector2D(Hero->GetActorLocation() - Exit->DestLocation).Size() < 100.0);
					Hero->GetCharacterMovement()->StopMovementImmediately();
					Hero->GetCharacterMovement()->MaxWalkSpeed = 600.f;
					Wait = World->GetTimeSeconds() + 1.5;
					Stage = 3;
					return false;
				}
				static const FVector2D Route[] = {{370,161}, {370,248.69}, {344.5,258.5}, {303.5,274.27}, {303.5,390}};
				if (Waypoint < UE_ARRAY_COUNT(Route))
				{
					if (WalkTo(*Hero, Home->MapPixelToWorld(Route[Waypoint].X, Route[Waypoint].Y))) { ++Waypoint; }
				}
				return false;
			}
			if (Stage == 3)
			{
				if (World->GetTimeSeconds() < Wait)
				{
					Hero->AddMovementInput(FVector(0,1,0));
					MaxSpeed = FMath::Max(MaxSpeed, Hero->GetVelocity().Size2D());
					return false;
				}
				Test->TestTrue(FString::Printf(TEXT("run speed reached %.0f cm/s"), MaxSpeed), FMath::Abs(MaxSpeed - 600.0) < 15.0);
				Hero->GetCharacterMovement()->StopMovementImmediately();
				Hero->GetCharacterMovement()->MaxWalkSpeed = 150.f;
				Stage = 4;
			}
			if (Stage == 4)
			{
				if (Screen && Screen->ScreenNumber == 1)
				{
					Test->TestTrue(TEXT("walked back through entrance to its destination"),
						FVector2D(Hero->GetActorLocation() - Entrance->DestLocation).Size() < 100.0);
					Hero->GetCharacterMovement()->StopMovementImmediately();
					Waypoint = 0;
					Stage = 5;
				}
				else
				{
					// Aim at the actual doorway center, including authored-art overrides.
					WalkTo(*Hero, Entrance->GetComponentLocation());
					return false;
				}
			}
			if (Stage == 5)
			{
				static const FVector2D Route[] = {{303.5,335}, {303.5,274.27}, {344.5,258.5}, {370,248.69}, {370,161}, {314,161}};
				if (Waypoint < UE_ARRAY_COUNT(Route))
				{
					if (WalkTo(*Hero, Home->MapPixelToWorld(Route[Waypoint].X, Route[Waypoint].Y))) { ++Waypoint; }
					return false;
				}
				Test->TestTrue(TEXT("returned to starting side of the table without teleporting"), Screen && Screen->ScreenNumber == 1);
				Hero->GetCharacterMovement()->MaxWalkSpeed = 600.f;
				return true;
			}
			return false;
		}

	private:
		static bool WalkTo(ADinkGreyboxCharacter& Hero, const FVector& Target)
		{
			FVector Delta = Target - Hero.GetActorLocation();
			Delta.Z = 0;
			if (Delta.Size2D() < 1.0)
			{
				Hero.GetCharacterMovement()->StopMovementImmediately();
				return true;
			}
			// Slow down near a waypoint to avoid stepping past the narrow diagonal on a long frame.
			const float Speed = FMath::Clamp(float(Delta.Size2D() * 4.0), 5.f, 150.f);
			Hero.GetCharacterMovement()->MaxWalkSpeed = Speed;
			Hero.AddMovementInput(Delta.GetSafeNormal2D());
			return false;
		}
		FAutomationTestBase* Test;
		FVector2D StartMetres;
		double Began;
		double Wait = 0;
		double MaxSpeed = 0;
		int32 Stage = 0;
		int32 Waypoint = 0;
		UDinkWarpComponent* Exit = nullptr;
		UDinkWarpComponent* Entrance = nullptr;
		ADinkScreenVolume* Home = nullptr;
		ADinkScreenVolume* Outside = nullptr;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkImportStonebrookPlayTest, "Dink.Import.Greybox.StonebrookPlay", DINK_TEST_FLAGS)
bool FDinkImportStonebrookPlayTest::RunTest(const FString& Parameters)
{
	TSharedPtr<FJsonObject> Manifest = Bundle(*this, TEXT("bundle.json"));
	if (!Manifest || !OpenStonebrook(*this))
	{
		return true;
	}
	const FVector2D Start = Vec2(Manifest->GetObjectField(TEXT("start"))->Values.FindRef(TEXT("world")));
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FDinkPlayCheckCommand(this, Start));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkImportNoOverlapTest, "Dink.Import.Layout.NoOverlap", DINK_TEST_FLAGS)
bool FDinkImportNoOverlapTest::RunTest(const FString& Parameters)
{
	// No two imported screens may cover the same ground: an overlap puts one screen's blockers on
	// the other's walkable ground. Sampled with the exact quad test on a 7 x 5 grid per screen.
	FScreens Screens;
	if (!LoadScreens(*this, Screens))
	{
		return true;
	}
	TArray<FString> Ids;
	for (const auto& Pair : Screens.ById)
	{
		if (Pair.Value->GetStringField(TEXT("excluded")).IsEmpty())
		{
			Ids.Add(Pair.Key);
		}
	}
	int32 Overlaps = 0;
	for (const FString& A : Ids)
	{
		const FDinkScreenCorners& CA = Screens.CornersById[A];
		for (int32 I = 1; I < 8; ++I)
		{
			for (int32 J = 1; J < 6; ++J)
			{
				const FVector2D P = DinkLayout::MapPixelToMetres(CA, 600.0 * I / 8.0, 400.0 * J / 6.0);
				for (const FString& B : Ids)
				{
					if (B != A && DinkLayout::ContainsMetres(Screens.CornersById[B], P, -0.5))
					{
						if (++Overlaps <= 10)
						{
							AddError(FString::Printf(TEXT("%s point (%d/8, %d/6) lies inside %s"), *A, I, J, *B));
						}
					}
				}
			}
		}
	}
	AddInfo(FString::Printf(TEXT("%d imported screens, %d overlapping sample points"), Ids.Num(), Overlaps));
	TestEqual(TEXT("imported screens do not overlap"), Overlaps, 0);
	return true;
}
