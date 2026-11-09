// Sprite-family art binding (UDinkArtFamilySubsystem, Content/Dink/Data/Art/families.json): the resolver's precedence,
// the fit maths, the shipped manifest, and a PIE check that a bound placement gets its mesh with its collision unchanged.
#include "DinkTestHelpers.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
	TSharedPtr<FJsonObject> ParseObject(const FString& Text)
	{
		TSharedPtr<FJsonObject> Object;
		FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Object);
		return Object;
	}

	FDinkFamilyPlacement Placement(const TCHAR* Origin, int32 Screen, int32 Sequence, const TCHAR* ClassId, bool bScripted = false, bool bHardnessOnly = false)
	{
		FDinkFamilyPlacement P;
		P.Origin = Origin;
		P.Screen = Screen;
		P.Sequence = Sequence;
		P.ClassId = FName(ClassId);
		P.bScripted = bScripted;
		P.bHardnessOnly = bHardnessOnly;
		return P;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkArtFamilyPrecedenceTest, "Dink.Art.Family.ResolverPrecedence", DINK_TEST_FLAGS)
bool FDinkArtFamilyPrecedenceTest::RunTest(const FString&)
{
	TArray<FDinkFamilyBinding> Bindings;
	TArray<FString> Errors;
	const bool bParsed = DinkArtFamily::ParseFamilies(TEXT(R"({"schema":"dink-art-families/1","families":[
		{"family":"173 bonuses/barrels/barel-","mesh":"/Game/Dink/Kits/Stonebrook/SM_Barrel_Oak_01","fit":"footprint"},
		{"family":"barrel_broken","mesh":"/Game/Dink/Test/SM_Broken.SM_Broken","fit":"none","yaw_from_sprite":true},
		{"family":"chair","mesh":"/Game/Dink/Test/SM_Chair","fit":"height","scripted":true}]})"), Bindings, Errors);
	TestTrue(TEXT("test families parse without errors"), bParsed && Errors.IsEmpty());
	if (!TestEqual(TEXT("three bindings"), Bindings.Num(), 3)) return false;
	TestEqual(TEXT("a sequence family keys on its leading number"), Bindings[0].Sequence, 173);
	TestTrue(TEXT("a sequence family has no class"), Bindings[0].ClassId.IsNone());
	TestEqual(TEXT("a package path gets its object name"), Bindings[0].Mesh, FString(TEXT("/Game/Dink/Kits/Stonebrook/SM_Barrel_Oak_01.SM_Barrel_Oak_01")));
	TestEqual(TEXT("an object path is kept"), Bindings[1].Mesh, FString(TEXT("/Game/Dink/Test/SM_Broken.SM_Broken")));
	TestEqual(TEXT("a class family keys on its class id"), Bindings[1].ClassId, FName(TEXT("barrel_broken")));
	TestTrue(TEXT("fit and flags are read"), Bindings[1].Fit == EDinkFamilyFit::None && Bindings[1].bYawFromSprite && Bindings[2].Fit == EDinkFamilyFit::Height && Bindings[2].bScripted);

	TArray<FDinkFamilyBinding> Bad;
	TArray<FString> BadErrors;
	DinkArtFamily::ParseFamilies(TEXT(R"({"schema":"dink-art-families/1","families":[
		{"family":"barrel","mesh":"/Game/A/SM_A"},{"family":"barrel","mesh":"/Game/A/SM_B"},
		{"family":"rock","mesh":"Content/SM_Rock"},{"family":"tree","mesh":"/Game/A/SM_T","fit":"stretch"},{"mesh":"/Game/A/SM_X"}]})"), Bad, BadErrors);
	TestEqual(TEXT("only the first of a duplicate, a bad mesh path, a bad fit and a missing family survive as one row"), Bad.Num(), 1);
	TestTrue(TEXT("fit defaults to none (real size)"), Bad.Num() == 1 && Bad[0].Fit == EDinkFamilyFit::None && !Bad[0].bYawFromSprite);
	TestEqual(TEXT("four rows reported"), BadErrors.Num(), 4);
	TArray<FString> SchemaErrors;
	TestFalse(TEXT("a wrong schema is refused"), DinkArtFamily::ParseFamilies(TEXT(R"({"schema":"dink-art/1","families":[]})"), Bad, SchemaErrors));

	// The manifests the art runtime already applies: an origin-bound replacement, hidden cards, a vision variant, a door
	// trigger, a dressed screen, authored collision, a creature and a character.
	FDinkFamilyPrecedence Precedence;
	Precedence.AddManifest(*ParseObject(TEXT(R"({"schema":"dink-art/1","screen":439,"replacements":[{"origin":"S439_P06","mesh":"/Game/X"}],
		"hide_origins":["S439_P30"],"hide_screen_visuals":[439],"warp_overrides":[{"origin":"S439_P13"}],"elements":[{"mesh":"/Game/Y"}]})")));
	Precedence.AddManifest(*ParseObject(TEXT(R"({"schema":"dink-art/1","screen":2,"hide_origins_by_vision":{"1":["S002_P07"],"2":["S002_P08"]},"authored_collision_screens":[3]})")));
	Precedence.AddManifest(*ParseObject(TEXT(R"({"schema":"dink-art/1","screen":5,"replacements":[{"origin":"S005_P01","mesh":"/Game/Z"}]})")));
	Precedence.AddManifest(*ParseObject(TEXT(R"({"schema":"dink-creatures/1","placements":[{"origin":"S407_P02"}]})")));
	Precedence.AddManifest(*ParseObject(TEXT(R"({"schema":"dink-characters/1","placements":[{"origin":"S001_P26"}],"player":{"mesh":"/Game/P"}})")));
	Precedence.AddManifest(*ParseObject(TEXT(R"({"schema":"dink-art-families/1","families":[{"family":"barrel","mesh":"/Game/A"}]})")));
	Precedence.AddManifest(*ParseObject(TEXT(R"({"schema":"dink-camera/1","hide_screen_visuals":[9]})")));
	for (const TCHAR* Id : {TEXT("S439_P06"), TEXT("S439_P30"), TEXT("S439_P13"), TEXT("S002_P07"), TEXT("S002_P08"), TEXT("S005_P01"), TEXT("S407_P02"), TEXT("S001_P26")})
		TestTrue(FString::Printf(TEXT("%s is handled by an art manifest"), Id), Precedence.Origins.Contains(Id));
	TestTrue(TEXT("hide_screen_visuals, authored collision and element screens are dressed"), Precedence.Screens.Contains(439) && Precedence.Screens.Contains(3));
	TestFalse(TEXT("a replacements-only manifest does not claim its screen"), Precedence.Screens.Contains(5));
	TestFalse(TEXT("a manifest without elements does not claim its screen"), Precedence.Screens.Contains(2));
	TestFalse(TEXT("other schemas add nothing"), Precedence.Screens.Contains(9));

	auto Check = [&](const TCHAR* What, const FDinkFamilyPlacement& P, EDinkFamilyDecision Expected, const FDinkFamilyBinding* ExpectedBinding)
	{
		const FDinkFamilyBinding* B = nullptr;
		const EDinkFamilyDecision D = DinkArtFamily::Decide(P, Precedence, Bindings, B);
		TestEqual(FString(What) + TEXT(": decision"), FString(DinkArtFamily::DecisionName(D)), FString(DinkArtFamily::DecisionName(Expected)));
		TestTrue(FString(What) + TEXT(": binding"), B == ExpectedBinding);
	};
	Check(TEXT("an undressed barrel takes the sequence binding"), Placement(TEXT("S100_P01"), 100, 173, TEXT("barrel")), EDinkFamilyDecision::Bound, &Bindings[0]);
	Check(TEXT("a class row wins over its sequence row"), Placement(TEXT("S100_P02"), 100, 173, TEXT("barrel_broken")), EDinkFamilyDecision::Bound, &Bindings[1]);
	Check(TEXT("an origin-bound barrel is skipped"), Placement(TEXT("S005_P01"), 5, 173, TEXT("barrel")), EDinkFamilyDecision::OriginHandled, nullptr);
	Check(TEXT("a vision-hidden origin is skipped"), Placement(TEXT("S002_P07"), 2, 173, TEXT("barrel")), EDinkFamilyDecision::OriginHandled, nullptr);
	Check(TEXT("a creature origin is skipped"), Placement(TEXT("S407_P02"), 407, 173, TEXT("barrel")), EDinkFamilyDecision::OriginHandled, nullptr);
	Check(TEXT("a character origin is skipped"), Placement(TEXT("S001_P26"), 1, 461, TEXT("chair")), EDinkFamilyDecision::OriginHandled, nullptr);
	Check(TEXT("anything on a dressed screen is skipped"), Placement(TEXT("S439_P50"), 439, 173, TEXT("barrel")), EDinkFamilyDecision::ScreenDressed, nullptr);
	Check(TEXT("a screen with authored collision is skipped"), Placement(TEXT("S003_P01"), 3, 173, TEXT("barrel")), EDinkFamilyDecision::ScreenDressed, nullptr);
	Check(TEXT("a hardness-only proxy is skipped"), Placement(TEXT("S100_P03"), 100, 173, TEXT("barrel"), false, true), EDinkFamilyDecision::HardnessOnly, nullptr);
	Check(TEXT("a scripted barrel keeps its card unless the row allows scripts"), Placement(TEXT("S100_P04"), 100, 173, TEXT("barrel"), true), EDinkFamilyDecision::Scripted, nullptr);
	Check(TEXT("a scripted chair is dressed: its row allows scripts"), Placement(TEXT("S100_P05"), 100, 461, TEXT("chair"), true), EDinkFamilyDecision::Bound, &Bindings[2]);
	Check(TEXT("an unbound family stays a card"), Placement(TEXT("S100_P06"), 100, 32, TEXT("tree_dead_dark")), EDinkFamilyDecision::NoBinding, nullptr);

	// The shipped manifests: the screens and origins they dress are known to the family layer.
	const FDinkFamilyPrecedence Shipped = FDinkFamilyPrecedence::LoadDirectory(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art"), TEXT("families.json"));
	if (Shipped.Screens.IsEmpty())
	{
		AddWarning(TEXT("skipped shipped-manifest checks: no Data/Art manifests"));
		return true;
	}
	for (const int32 Screen : {1, 407, 438, 439, 471})
		TestTrue(FString::Printf(TEXT("shipped art dresses screen %d"), Screen), Shipped.Screens.Contains(Screen));
	for (const TCHAR* Id : {TEXT("S001_P26"), TEXT("S439_P06"), TEXT("S439_P22"), TEXT("S001_P19")})
		TestTrue(FString::Printf(TEXT("shipped art binds %s"), Id), Shipped.Origins.Contains(Id));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkArtFamilyFitTest, "Dink.Art.Family.FootprintFitMaths", DINK_TEST_FLAGS)
bool FDinkArtFamilyFitTest::RunTest(const FString&)
{
	using namespace DinkArtFamily;
	const FVector Barrel(84, 84, 100);  // cm, the kit barrel's box
	// A 420 x 416 cm barrel card (the greybox's layout scale): the height limits the uniform scale.
	TestEqual(TEXT("footprint: the tighter of width and height"), FitScale(EDinkFamilyFit::Footprint, 420, 416, Barrel, false), 4.16f, 1e-4f);
	// A wide, low card: the width limits.
	TestEqual(TEXT("footprint: width-limited"), FitScale(EDinkFamilyFit::Footprint, 168, 1000, Barrel, false), 2.f, 1e-4f);
	// Yaw from the sprite compares the mesh's X extent; a free yaw compares its larger horizontal extent.
	const FVector Table(265, 150, 90);
	TestEqual(TEXT("footprint, sprite yaw: X extent"), FitScale(EDinkFamilyFit::Footprint, 464, 1000, Table, true), 464.f / 265.f, 1e-4f);
	TestEqual(TEXT("footprint, free yaw: larger horizontal extent"), FitScale(EDinkFamilyFit::Footprint, 300, 1000, FVector(150, 300, 90), false), 1.f, 1e-4f);
	TestEqual(TEXT("footprint, sprite yaw ignores Y"), FitScale(EDinkFamilyFit::Footprint, 300, 1000, FVector(150, 300, 90), true), 2.f, 1e-4f);
	TestEqual(TEXT("height: card height over mesh height"), FitScale(EDinkFamilyFit::Height, 100, 1436, FVector(578, 587, 1300), false), 1436.f / 1300.f, 1e-4f);
	TestEqual(TEXT("none: authored size"), FitScale(EDinkFamilyFit::None, 420, 416, Barrel, false), 1.f);
	TestEqual(TEXT("a missing card size falls back to the other side"), FitScale(EDinkFamilyFit::Footprint, 0, 200, Barrel, false), 2.f, 1e-4f);
	TestEqual(TEXT("no sizes at all: scale 1"), FitScale(EDinkFamilyFit::Footprint, 0, 0, FVector::ZeroVector, false), 1.f);
	TestEqual(TEXT("clamped above"), FitScale(EDinkFamilyFit::Height, 0, 100000, FVector(1, 1, 1), false), MaxScale);
	TestEqual(TEXT("clamped below"), FitScale(EDinkFamilyFit::Height, 0, 1, FVector(1, 1, 1000), false), MinScale);

	// Pivot handling: a mesh whose box is off-centre and below its origin still stands centred on the ground point.
	const FBox Bounds(FVector(10, -30, -5), FVector(50, 10, 95));  // centre (30, -10), bottom -5
	const FVector Ground(120, 40, 0);
	for (const double Yaw : {0.0, 90.0, 217.0})
	{
		const FTransform T = MeshTransform(Bounds, Ground, Yaw, 2.f);
		const FVector Anchor = T.TransformPosition(FVector(30, -10, -5));
		TestTrue(FString::Printf(TEXT("yaw %.0f: the box's bottom centre lands on the ground point"), Yaw), Anchor.Equals(Ground, 1e-3));
		TestEqual(FString::Printf(TEXT("yaw %.0f: uniform scale"), Yaw), T.GetScale3D(), FVector(2.0));
		TestEqual(FString::Printf(TEXT("yaw %.0f: yaw only"), Yaw), FRotator::NormalizeAxis(T.Rotator().Yaw), FRotator::NormalizeAxis(Yaw), 1e-3);
		const FBox Placed = Bounds.TransformBy(T);
		TestEqual(FString::Printf(TEXT("yaw %.0f: bottom on the ground"), Yaw), Placed.Min.Z, 0.0, 1e-3);
		TestEqual(FString::Printf(TEXT("yaw %.0f: height scaled"), Yaw), Placed.Max.Z, 200.0, 1e-3);
	}
	// Free yaw is a pure function of the origin ID (no random stream).
	TestEqual(TEXT("stable yaw repeats"), StableYaw(TEXT("S412_P03")), StableYaw(TEXT("S412_P03")));
	TestTrue(TEXT("stable yaw in range"), StableYaw(TEXT("S412_P03")) >= 0.0 && StableYaw(TEXT("S412_P03")) < 360.0);
	TestTrue(TEXT("different origins turn differently"), StableYaw(TEXT("S412_P03")) != StableYaw(TEXT("S412_P04")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkArtFamilyManifestTest, "Dink.Art.Family.ManifestMeshesExist", DINK_TEST_FLAGS)
bool FDinkArtFamilyManifestTest::RunTest(const FString&)
{
	FString Text;
	if (!TestTrue(TEXT("Content/Dink/Data/Art/families.json exists"), FFileHelper::LoadFileToString(Text, *DinkArtFamily::DefaultFamiliesPath()))) return false;
	TArray<FDinkFamilyBinding> Bindings;
	TArray<FString> Errors;
	TestTrue(TEXT("families.json parses without errors"), DinkArtFamily::ParseFamilies(Text, Bindings, Errors));
	for (const FString& Error : Errors) AddError(Error);
	TestTrue(TEXT("families.json binds at least one family"), Bindings.Num() > 0);
	for (const FDinkFamilyBinding& B : Bindings)
	{
		TestTrue(FString::Printf(TEXT("%s: mesh is project art under /Game/Dink"), *B.Family), B.Mesh.StartsWith(TEXT("/Game/Dink/")) && !B.Mesh.StartsWith(TEXT("/Game/Dink/_Generated/")));
		const FString Package = B.Mesh.Left(B.Mesh.Find(TEXT(".")));
		const FString File = FPackageName::LongPackageNameToFilename(Package, FPackageName::GetAssetPackageExtension());
		if (!TestTrue(FString::Printf(TEXT("%s: %s exists"), *B.Family, *File), IFileManager::Get().FileExists(*File))) continue;
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *B.Mesh);
		if (!TestNotNull(FString::Printf(TEXT("%s: %s loads as a static mesh"), *B.Family, *B.Mesh), Mesh)) continue;
		const FVector Size = Mesh->GetBoundingBox().GetSize();
		TestTrue(FString::Printf(TEXT("%s: mesh has a real size"), *B.Family), Size.X > 1 && Size.Y > 1 && Size.Z > 1);
	}
	return true;
}

namespace
{
	struct FCollisionState
	{
		bool bActorCollision = false;
		TMap<FName, TPair<ECollisionEnabled::Type, FName>> Components;
		ECollisionEnabled::Type Solid = ECollisionEnabled::NoCollision;
		ECollisionEnabled::Type Low = ECollisionEnabled::NoCollision;
		bool bBlocksPawn = false;
	};

	FCollisionState Capture(UWorld& World, ADinkPlaceholderActor& Actor)
	{
		FCollisionState S;
		S.bActorCollision = Actor.GetActorEnableCollision();
		TInlineComponentArray<UPrimitiveComponent*> Components(&Actor);
		for (UPrimitiveComponent* C : Components)
		{
			if (!C->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag))
				S.Components.Add(C->GetFName(), TPair<ECollisionEnabled::Type, FName>(C->GetCollisionEnabled(), C->GetCollisionProfileName()));
		}
		for (TActorIterator<ADinkGreyboxScreen> It(&World); It; ++It)
		{
			if (It->ScreenNumber != Actor.ScreenNumber) continue;
			S.Solid = It->CollisionSolid->GetCollisionEnabled();
			S.Low = It->CollisionLow->GetCollisionEnabled();
		}
		S.bBlocksPawn = World.OverlapBlockingTestByChannel(Actor.GetActorLocation() + FVector(0, 0, 100), FQuat::Identity, ECC_Pawn, FCollisionShape::MakeCapsule(28, 96));
		return S;
	}

	class FDinkArtFamilyPIECheck : public IAutomationLatentCommand
	{
	public:
		explicit FDinkArtFamilyPIECheck(FAutomationTestBase* InTest) : Test(InTest) {}

		bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			UDinkStorySubsystem* Story = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
			if (Began == 0) Began = FPlatformTime::Seconds();
			if (FPlatformTime::Seconds() - Began > 120)
			{
				Test->AddError(FString::Printf(TEXT("family art PIE check timed out in phase %d"), Phase));
				return true;
			}
			if (!Story || Story->bNewGamePending) return false;
			UDinkArtFamilySubsystem* Family = World->GetSubsystem<UDinkArtFamilySubsystem>();
			UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
			if (!Test->TestNotNull(TEXT("family subsystem exists in PIE"), Family) || !Test->TestNotNull(TEXT("greybox subsystem"), Greybox)) return true;
			if (Phase == 0)
			{
				FAssetCompilingManager::Get().FinishAllCompilation();
				if (!Test->TestTrue(TEXT("family subsystem is ready (families.json loaded, meshes found)"), Family->IsReady())) return true;
				// The lowest-numbered undressed screen with a bound, ungated placement that the pawn is not on.
				const int32 Current = Greybox->GetCurrentScreen() ? Greybox->GetCurrentScreen()->ScreenNumber : 0;
				for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
				{
					if (!It->Origin || It->Vision != 0 || It->ScreenNumber == Current || Family->IsScreenApplied(It->ScreenNumber) || !It->Card || It->Card->bHiddenInGame) continue;
					FDinkFamilyPlacement P;
					P.Origin = It->Origin->OriginId.ToString();
					P.Screen = It->ScreenNumber;
					P.Sequence = It->Origin->Sequence;
					P.ClassId = It->Origin->ClassId;
					P.bScripted = !It->Origin->ScriptName.IsNone();
					P.bHardnessOnly = It->PlacementKind == TEXT("hardness_only");
					const FDinkFamilyBinding* B = nullptr;
					if (DinkArtFamily::Decide(P, Family->GetPrecedence(), Family->GetBindings(), B) != EDinkFamilyDecision::Bound) continue;
					if (!Target.IsValid() || It->ScreenNumber < Target->ScreenNumber || (It->ScreenNumber == Target->ScreenNumber && P.Origin < Target->Origin->OriginId.ToString()))
					{
						Target = *It;
						Binding = B;
					}
				}
				if (!Test->TestTrue(TEXT("the world has an undressed placement with a bound family"), Target.IsValid())) return true;
				Before = Capture(*World, *Target);
				TargetOrigin = Target->Origin->OriginId.ToString();
				Test->AddInfo(FString::Printf(TEXT("target %s (%s, family %s) on screen %d"), *Target->Origin->OriginId.ToString(),
					*Target->Origin->ClassId.ToString(), *Binding->Family, Target->ScreenNumber));
				Test->TestTrue(TEXT("player moves to the target screen"), Greybox->GotoScreen(Target->ScreenNumber));
				Phase = 1;
				return false;
			}
			if (Phase == 1)
			{
				// Screen activation, not a direct call: the greybox's screen check broadcasts the change.
				if (!Target.IsValid() || !Family->IsScreenApplied(Target->ScreenNumber)) return false;
				ADinkPlaceholderActor& A = *Target;
				UStaticMeshComponent* Mesh = nullptr;
				TInlineComponentArray<UStaticMeshComponent*> Components(&A);
				for (UStaticMeshComponent* C : Components) if (C->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)) Mesh = C;
				if (Test->TestNotNull(TEXT("the placement actor carries the family mesh component"), Mesh))
				{
					Test->TestTrue(TEXT("family mesh is the bound mesh"), Mesh->GetStaticMesh() && Mesh->GetStaticMesh()->GetPathName() == Binding->Mesh);
					Test->TestTrue(TEXT("family mesh hangs off the placement root"), Mesh->GetAttachParent() == A.GetRootComponent());
					Test->TestTrue(TEXT("family mesh has no collision"), Mesh->GetCollisionEnabled() == ECollisionEnabled::NoCollision);
					Test->TestFalse(TEXT("family mesh does not affect navigation"), Mesh->CanEverAffectNavigation());
					Test->TestTrue(TEXT("family mesh is sized (not zero)"), Mesh->Bounds.BoxExtent.Size() > 1.0);
				}
				Test->TestTrue(TEXT("the card is hidden"), A.Card->bHiddenInGame);
				Test->TestTrue(TEXT("the actor is tagged family art"), A.ActorHasTag(UDinkArtFamilySubsystem::FamilyTag));
				Test->TestFalse(TEXT("the actor is not authored art (gameplay keeps the original pixel rules)"), A.ActorHasTag(TEXT("DinkAuthoredArt")));
				Test->TestTrue(TEXT("origin ID unchanged"), A.Origin && A.Origin->OriginId.ToString() == TargetOrigin);
				const FCollisionState After = Capture(*World, A);
				Test->TestTrue(TEXT("actor collision flag unchanged"), After.bActorCollision == Before.bActorCollision);
				Test->TestEqual(TEXT("same collision components"), After.Components.Num(), Before.Components.Num());
				for (const auto& Pair : Before.Components)
				{
					const TPair<ECollisionEnabled::Type, FName>* Now = After.Components.Find(Pair.Key);
					Test->TestTrue(FString::Printf(TEXT("%s collision unchanged"), *Pair.Key.ToString()), Now && Now->Key == Pair.Value.Key && Now->Value == Pair.Value.Value);
				}
				Test->TestTrue(TEXT("screen solid hardness collision unchanged"), After.Solid == Before.Solid);
				Test->TestTrue(TEXT("screen low hardness collision unchanged"), After.Low == Before.Low);
				Test->TestTrue(TEXT("pawn blocking at the placement unchanged"), After.bBlocksPawn == Before.bBlocksPawn);
				// A screen the art manifests dress gets nothing from this layer.
				Family->ApplyScreen(1);
				for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
					if (It->ScreenNumber == 1 && It->ActorHasTag(UDinkArtFamilySubsystem::FamilyTag))
						Test->AddError(FString::Printf(TEXT("%s on the dressed house screen got family art"), *It->Origin->OriginId.ToString()));
				Test->TestTrue(TEXT("family art dressed at least the target"), Family->GetDressedCount() > 0);
				return true;
			}
			return true;
		}

	private:
		FAutomationTestBase* Test;
		double Began = 0;
		int32 Phase = 0;
		TWeakObjectPtr<ADinkPlaceholderActor> Target;
		const FDinkFamilyBinding* Binding = nullptr;
		FCollisionState Before;
		FString TargetOrigin;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkArtFamilyPIETest, "Dink.Art.Family.ScreenActivationDressesBoundPlacement", DINK_TEST_FLAGS)
bool FDinkArtFamilyPIETest::RunTest(const FString&)
{
	if (!IFileManager::Get().FileExists(*DinkArtFamily::DefaultFamiliesPath()))
	{
		AddWarning(TEXT("skipped: no families.json"));
		return true;
	}
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!IFileManager::Get().FileExists(*File))
	{
		AddWarning(TEXT("skipped: greybox world not imported (Scripts/import_greybox.sh --region all)"));
		return true;
	}
	if (!TestNotNull(TEXT("real world map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	FAssetCompilingManager::Get().FinishAllCompilation();
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FDinkArtFamilyPIECheck(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
