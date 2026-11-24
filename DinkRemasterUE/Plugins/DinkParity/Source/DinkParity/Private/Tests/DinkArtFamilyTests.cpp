// Sprite-family art binding (UDinkArtFamilySubsystem, Content/Dink/Data/Art/families.json): the resolver's precedence,
// the fit maths, the shipped manifest, a PIE check that a bound placement gets its mesh with its collision unchanged, and
// a placed fire's light and smoke following its card off the current screen (EffectFollowsCard).
#include "DinkTestHelpers.h"
#include "Materials/MaterialInterface.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkFlickerLightComponent.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "DinkWorldLifeSubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Components/BoxComponent.h"
#include "Components/MaterialBillboardComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ScopeExit.h"
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
		{"family":"barrel_broken","mesh":"/Game/Dink/Test/SM_Broken.SM_Broken","fit":"none","yaw_from_sprite":true,"stands_as":"/Game/Dink/Test/SM_Whole"},
		{"family":"chair","mesh":"/Game/Dink/Test/SM_Chair","fit":"height","scripted":true}]})"), Bindings, Errors);
	TestTrue(TEXT("test families parse without errors"), bParsed && Errors.IsEmpty());
	if (!TestEqual(TEXT("three bindings"), Bindings.Num(), 3)) return false;
	TestEqual(TEXT("a sequence family keys on its leading number"), Bindings[0].Sequence, 173);
	TestTrue(TEXT("a sequence family has no class"), Bindings[0].ClassId.IsNone());
	// "stands_as": a state mesh is placed by its base mesh's bounds (a chest with its lid up stands where the closed one stands)
	TestEqual(TEXT("stands_as is read as an object path"), Bindings[1].StandsAs, FString(TEXT("/Game/Dink/Test/SM_Whole.SM_Whole")));
	TestTrue(TEXT("a row without stands_as stands by its own bounds"), Bindings[0].StandsAs.IsEmpty());
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
	// Sequence-and-frame rows: one picture of a sequence, with its own yaw; they win over the class row.
	TArray<FDinkFamilyBinding> Framed;
	TArray<FString> FramedErrors;
	TestTrue(TEXT("frame rows parse"), DinkArtFamily::ParseFamilies(TEXT(R"({"schema":"dink-art-families/1","families":[
		{"family":"wall_curve","mesh":"/Game/A/SM_Class"},
		{"family":"80 walls curve NE","frame":7,"mesh":"/Game/A/SM_Curve","yaw_offset":-90,"anchor_front":1},
		{"family":"80 walls curve SE","frame":9,"mesh":"/Game/A/SM_Curve"},
		{"family":"80 walls","mesh":"/Game/A/SM_Seq"}]})"), Framed, FramedErrors) && Framed.Num() == 4);
	if (Framed.Num() == 4)
	{
		const FDinkFamilyBinding* Seven = DinkArtFamily::Resolve(Framed, 80, TEXT("wall_curve"), 7);
		TestTrue(TEXT("frame 7 takes its frame row over the class row, with its yaw and front anchor"), Seven == &Framed[1] && Seven->YawOffset == -90.0 && Seven->AnchorFront == 1.0);
		TestTrue(TEXT("frame 9 takes the other frame row"), DinkArtFamily::Resolve(Framed, 80, TEXT("wall_curve"), 9) == &Framed[2]);
		TestTrue(TEXT("a frame without a row falls back to the class row"), DinkArtFamily::Resolve(Framed, 80, TEXT("wall_curve"), 8) == &Framed[0]);
		TestTrue(TEXT("without a class the plain sequence row binds, never a frame row"), DinkArtFamily::Resolve(Framed, 80, NAME_None, 3) == &Framed[3]);
		TestTrue(TEXT("the frame-less call keeps the old precedence"), DinkArtFamily::Resolve(Framed, 80, TEXT("wall_curve")) == &Framed[0]);
	}
	TArray<FDinkFamilyBinding> BadFrame;
	TArray<FString> BadFrameErrors;
	DinkArtFamily::ParseFamilies(TEXT(R"({"schema":"dink-art-families/1","families":[{"family":"barrel","frame":2,"mesh":"/Game/A/SM_A"}]})"), BadFrame, BadFrameErrors);
	TestTrue(TEXT("a frame on a class row is refused"), BadFrame.IsEmpty() && BadFrameErrors.Num() == 1);
	// The optional size multiplier of small things (shells, flasks): read, 1 by default, refused outside 0.05..20.
	TArray<FDinkFamilyBinding> Sized;
	TArray<FString> SizedErrors;
	DinkArtFamily::ParseFamilies(TEXT(R"({"schema":"dink-art-families/1","families":[
		{"family":"starfish","mesh":"/Game/A/SM_Star","scale":2.5},{"family":"clam","mesh":"/Game/A/SM_Clam"},
		{"family":"flask","mesh":"/Game/A/SM_Flask","scale":0},{"family":"urn","mesh":"/Game/A/SM_Urn","scale":50}]})"), Sized, SizedErrors);
	TestTrue(TEXT("scale is read and defaults to 1"), Sized.Num() == 2 && Sized[0].Scale == 2.5 && Sized[1].Scale == 1.0);
	TestEqual(TEXT("a scale outside 0.05..20 is refused"), SizedErrors.Num(), 2);
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

	// "scripted_scripts": a row that keeps scripted placements as cards may still dress the ones whose script is listed
	// (read to never change its own picture: the talking pine s2-sec2), while the others (s2-sec1 burns the tree) keep theirs.
	{
		TArray<FDinkFamilyBinding> Allowed;
		TArray<FString> AllowedErrors;
		TestTrue(TEXT("scripted_scripts parses"), DinkArtFamily::ParseFamilies(TEXT(R"({"schema":"dink-art-families/1","families":[
			{"family":"tree_pine_large","mesh":"/Game/A/SM_Pine","scripted_scripts":["s2-sec2"," big ",""]},
			{"family":"cabinet_wood","mesh":"/Game/A/SM_Cabinet"}]})"), Allowed, AllowedErrors) && AllowedErrors.IsEmpty() && Allowed.Num() == 2);
		if (Allowed.Num() == 2)
		{
			TestEqual(TEXT("empty names are dropped, names are trimmed"), Allowed[0].ScriptedScripts.Num(), 2);
			TestTrue(TEXT("the row itself stays unscripted"), !Allowed[0].bScripted && Allowed[1].ScriptedScripts.IsEmpty());
			auto Scripted = [](const TCHAR* Origin, const TCHAR* ClassId, const TCHAR* Script)
			{
				FDinkFamilyPlacement P = Placement(Origin, 534, 32, ClassId, true);
				P.ScriptName = FName(Script);
				return P;
			};
			auto CheckAllowed = [&](const TCHAR* What, const FDinkFamilyPlacement& P, EDinkFamilyDecision Expected, const FDinkFamilyBinding* ExpectedBinding)
			{
				const FDinkFamilyBinding* B = nullptr;
				const EDinkFamilyDecision D = DinkArtFamily::Decide(P, Precedence, Allowed, B);
				TestEqual(FString(What) + TEXT(": decision"), FString(DinkArtFamily::DecisionName(D)), FString(DinkArtFamily::DecisionName(Expected)));
				TestTrue(FString(What) + TEXT(": binding"), B == ExpectedBinding);
			};
			CheckAllowed(TEXT("a placement whose script is listed is dressed"), Scripted(TEXT("S534_P10"), TEXT("tree_pine_large"), TEXT("s2-sec2")), EDinkFamilyDecision::Bound, &Allowed[0]);
			CheckAllowed(TEXT("script names match without case"), Scripted(TEXT("S534_P11"), TEXT("tree_pine_large"), TEXT("S2-SEC2")), EDinkFamilyDecision::Bound, &Allowed[0]);
			CheckAllowed(TEXT("a trimmed listed name matches"), Scripted(TEXT("S534_P13"), TEXT("tree_pine_large"), TEXT("big")), EDinkFamilyDecision::Bound, &Allowed[0]);
			CheckAllowed(TEXT("a placement whose script is not listed keeps its card"), Scripted(TEXT("S307_P13"), TEXT("tree_pine_large"), TEXT("s2-sec1")), EDinkFamilyDecision::Scripted, nullptr);
			CheckAllowed(TEXT("a listed script does not open another row"), Scripted(TEXT("S003_P15"), TEXT("cabinet_wood"), TEXT("s2-sec2")), EDinkFamilyDecision::Scripted, nullptr);
			CheckAllowed(TEXT("an unscripted placement is dressed as before"), Placement(TEXT("S534_P12"), 534, 32, TEXT("tree_pine_large")), EDinkFamilyDecision::Bound, &Allowed[0]);
			FDinkFamilyPlacement Dressed = Scripted(TEXT("S439_P51"), TEXT("tree_pine_large"), TEXT("s2-sec2"));
			Dressed.Screen = 439;
			CheckAllowed(TEXT("a dressed screen still wins over a listed script"), Dressed, EDinkFamilyDecision::ScreenDressed, nullptr);
		}
	}

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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkArtFamilyPlacedEffectRowTest, "Dink.Art.Family.PlacedEffectRow", DINK_TEST_FLAGS)
bool FDinkArtFamilyPlacedEffectRowTest::RunTest(const FString&)
{
	// An effect row draws on script sprites only, unless it says "effect_placed": then placed sprites take it too
	// (the fires of the burning house), sized from their own card by "effect_fit".
	TArray<FDinkFamilyBinding> Rows;
	TArray<FString> Errors;
	TestTrue(TEXT("effect rows parse"), DinkArtFamily::ParseFamilies(TEXT(R"({"schema":"dink-art-families/1","families":[
		{"family":"sparkle_fx","effect":"/Game/Dink/A/MI_A","effect_size_cm":70,"effect_offset_cm":[77,0,-5]},
		{"family":"fire_fx","effect":"/Game/Dink/A/MI_B","effect_placed":true,"effect_fit":[0.5,0.25],"effect_sink":0.03,"effect_ground":true,
		 "effect_light":[1.0,0.5,0.1,300,600],"effect_light_height":0.4,"effect_light_flicker":0.3,"offset_cm":{"S439_P05":[10,-20,350],"S439_P09":[1,2],"S439_P11":[0,0,500,2.2]},
		 "effect_plume":{"material":"/Game/Dink/A/MI_Smoke","size_cm":[350,700],"origins":["S439_P05"]},
		 "effect_layers":[[30,-40,0,1.15,0.8,1],[-25,30,-10,0.7,1.7],[1,2,3]]},
		{"family":"small_fire_fx","effect":"/Game/Dink/A/MI_C","effect_placed":true,"effect_fit":[7,-1],"effect_sink":9,"effect_light":[1,1,1]}]})"), Rows, Errors));
	TestEqual(TEXT("no errors"), Errors.Num(), 0);
	if (Rows.Num() != 3) return false;
	TestFalse(TEXT("a plain effect row stays off placed sprites"), Rows[0].bEffectPlaced);
	TestTrue(TEXT("effect_offset_cm moves a script sprite's card"), Rows[0].EffectOffsetCm.Equals(FVector(77.0, 0.0, -5.0)) && Rows[1].EffectOffsetCm.IsZero());
	TestTrue(TEXT("effect_placed is read"), Rows[1].bEffectPlaced && Rows[1].Mesh.IsEmpty());
	TestEqual(TEXT("effect_fit width"), Rows[1].EffectFit.X, 0.5);
	TestEqual(TEXT("effect_fit height"), Rows[1].EffectFit.Y, 0.25);
	TestEqual(TEXT("effect_sink"), Rows[1].EffectSink, 0.03);
	TestTrue(TEXT("effect_ground"), Rows[1].bEffectGround && !Rows[2].bEffectGround);
	TestEqual(TEXT("light candela"), Rows[1].EffectLightCandela, 300.0);
	TestEqual(TEXT("light radius"), Rows[1].EffectLightRadiusCm, 600.0);
	TestEqual(TEXT("light height"), Rows[1].EffectLightHeight, 0.4);
	TestEqual(TEXT("light flicker"), Rows[1].EffectLightFlicker, 0.3);
	TestEqual(TEXT("two placement offsets are read, the short one is dropped"), Rows[1].OffsetCm.Num(), 2);
	TestTrue(TEXT("a fourth number is that placement's size factor"), Rows[1].OffsetScale.Num() == 1 && FMath::IsNearlyEqual(Rows[1].OffsetScale.FindRef(TEXT("S439_P11")), 2.2));
	TestEqual(TEXT("plume material"), Rows[1].EffectPlume, FString(TEXT("/Game/Dink/A/MI_Smoke.MI_Smoke")));
	TestTrue(TEXT("plume size and its one placement"), Rows[1].EffectPlumeSizeCm.Equals(FVector2D(350.0, 700.0)) && Rows[1].EffectPlumeOrigins.Num() == 1 && Rows[1].EffectPlumeOrigins.Contains(TEXT("S439_P05")));
	TestTrue(TEXT("a row without a plume has none"), Rows[2].EffectPlume.IsEmpty());
	// "effect_layers": further cards of the same flipbook (a fire with depth); a short entry is dropped
	TestEqual(TEXT("two layers are read"), Rows[1].EffectLayers.Num(), 2);
	if (Rows[1].EffectLayers.Num() == 2)
	{
		TestTrue(TEXT("layer offset, size, phase and mirror"), Rows[1].EffectLayers[0].OffsetCm.Equals(FVector(30.0, -40.0, 0.0)) && FMath::IsNearlyEqual(Rows[1].EffectLayers[0].Scale, 1.15) &&
			FMath::IsNearlyEqual(Rows[1].EffectLayers[0].PhaseSeconds, 0.8) && Rows[1].EffectLayers[0].bMirror && !Rows[1].EffectLayers[1].bMirror);
	}
	TestTrue(TEXT("a row without layers has none"), Rows[0].EffectLayers.IsEmpty() && Rows[2].EffectLayers.IsEmpty());
	const FVector* Lift = Rows[1].OffsetCm.Find(TEXT("S439_P05"));
	TestTrue(TEXT("offset in cm, world axes"), Lift && Lift->Equals(FVector(10.0, -20.0, 350.0)));
	TestEqual(TEXT("a row without flicker gives a steady light"), Rows[2].EffectLightFlicker, 0.0);
	float Low = 10.f, High = -10.f;
	for (int32 Step = 0; Step < 2000; ++Step)
	{
		const float F = UDinkFlickerLightComponent::Factor(Step * 0.013, 0.3f, 5.f);
		Low = FMath::Min(Low, F);
		High = FMath::Max(High, F);
	}
	TestTrue(TEXT("firelight wavers within its depth"), Low >= 0.7f - KINDA_SMALL_NUMBER && High <= 1.3f + KINDA_SMALL_NUMBER && High - Low > 0.2f);
	TestEqual(TEXT("depth 0 is steady"), UDinkFlickerLightComponent::Factor(3.7, 0.f, 0.f), 1.f);
	TestEqual(TEXT("fit width is clamped to the frame"), Rows[2].EffectFit.X, 1.0);
	TestEqual(TEXT("fit height is clamped"), Rows[2].EffectFit.Y, 0.05);
	TestEqual(TEXT("sink is clamped"), Rows[2].EffectSink, 0.5);
	TestEqual(TEXT("a short light row gives no light"), Rows[2].EffectLightCandela, 0.0);
	// A sprite a script creates never takes a placed-effect row: its picture's own row, or none (the 1997 picture).
	TArray<FDinkFamilyBinding> Mixed;
	TestTrue(TEXT("mixed rows parse"), DinkArtFamily::ParseFamilies(TEXT(R"({"schema":"dink-art-families/1","families":[
		{"family":"fire_burst_fx","effect":"/Game/Dink/A/MI_Wall","effect_placed":true},
		{"family":"161 effects/atomic/atomc-","effect":"/Game/Dink/A/MI_Burst","effect_size_cm":360},
		{"family":"86 inside/details/fire-","effect":"/Game/Dink/A/MI_Hearth","effect_placed":true}]})"), Mixed, Errors) && Mixed.Num() == 3);
	if (Mixed.Num() != 3) return false;
	TestTrue(TEXT("a placed sprite of the class takes the placed-effect class row"), DinkArtFamily::Resolve(Mixed, 161, TEXT("fire_burst_fx"), 1) == &Mixed[0]);
	TestTrue(TEXT("a script-created sprite of that picture takes the sequence row"), DinkArtFamily::ResolveScriptSprite(Mixed, 161, TEXT("fire_burst_fx"), 1) == &Mixed[1]);
	TestTrue(TEXT("a script-created sprite whose only row is a placed effect takes none"), DinkArtFamily::ResolveScriptSprite(Mixed, 86, TEXT("hearth_fire"), 1) == nullptr);
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
		if (!B.Effect.IsEmpty())
		{
			// an effect row: a material on a camera-facing card instead of a mesh
			TestTrue(FString::Printf(TEXT("%s: effect is project art under /Game/Dink"), *B.Family), B.Effect.StartsWith(TEXT("/Game/Dink/")) && B.Mesh.IsEmpty());
			TestNotNull(FString::Printf(TEXT("%s: %s loads as a material"), *B.Family, *B.Effect), LoadObject<UMaterialInterface>(nullptr, *B.Effect));
			continue;
		}
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
					P.Frame = It->Origin->Frame;
					P.ClassId = It->Origin->ClassId;
					P.bScripted = !It->Origin->ScriptName.IsNone();
					P.bHardnessOnly = It->PlacementKind == TEXT("hardness_only");
					const FDinkFamilyBinding* B = nullptr;
					if (DinkArtFamily::Decide(P, Family->GetPrecedence(), Family->GetBindings(), B) != EDinkFamilyDecision::Bound) continue;
					if (B && !B->Effect.IsEmpty()) continue;  // an effect row reskins the card instead of adding a mesh
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
				// A screen the art manifests dress gets nothing from this layer, except the cards of "effect_placed" rows
				// (the fires of the burning house: no manifest draws effects).
				Family->ApplyScreen(1);
				for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
				{
					if (It->ScreenNumber != 1 || !It->ActorHasTag(UDinkArtFamilySubsystem::FamilyTag)) continue;
					const FDinkFamilyBinding* Fx = It->Origin ? DinkArtFamily::Resolve(Family->GetBindings(), It->Origin->Sequence, It->Origin->ClassId, It->Origin->Frame) : nullptr;
					if (Fx && Fx->bEffectPlaced && !Fx->Effect.IsEmpty()) continue;
					Test->AddError(FString::Printf(TEXT("%s on the dressed house screen got family art"), *It->Origin->OriginId.ToString()));
				}
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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkArtFamilyEffectFollowsCardTest, "Dink.Art.Family.EffectFollowsCard", DINK_TEST_FLAGS)
bool FDinkArtFamilyEffectFollowsCardTest::RunTest(const FString&)
{
	// Review R11/R12 of #166/#193: DressPlacedEffect hangs a placed fire's flicker light and smoke column under its card, and
	// dink.LegacyCardsCurrentScreen renders cards only on the current screen without propagating to children. Seen from 438,
	// 440, 407 or 471 the flames of 439 were gone but the 7 m smoke columns and every fire's light still drew over the roof, and
	// the world-life layer took the fires for unowned and drew a second fire at their 1997 ground point.
	if (!IFileManager::Get().FileExists(*DinkArtFamily::DefaultFamiliesPath()))
	{
		AddWarning(TEXT("skipped: no families.json"));
		return true;
	}
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	if (!TestNotNull(TEXT("engine card mesh"), Plane)) return false;
	if (!LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Dink/Photoreal/FableF/MI_FX_Fire_Wall.MI_FX_Fire_Wall"), nullptr, LOAD_NoWarn | LOAD_Quiet) ||
		!LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Dink/Photoreal/FableF/MI_FX_Smoke_Plume.MI_FX_Smoke_Plume"), nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		AddWarning(TEXT("skipped: the fire_fx materials are not imported"));
		return true;
	}
	IConsoleVariable* Rule = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.LegacyCardsCurrentScreen"));
	if (!TestNotNull(TEXT("card rule registered"), Rule)) return false;
	const int32 Previous = Rule->GetInt();
	Rule->SetWithCurrentPriority(1);
	ON_SCOPE_EXIT { Rule->SetWithCurrentPriority(Previous); };
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
	UDinkArtFamilySubsystem* Family = World->GetSubsystem<UDinkArtFamilySubsystem>();
	TArray<ADinkScreenVolume*> Rooms;
	ON_SCOPE_EXIT
	{
		for (ADinkScreenVolume* V : Rooms) if (Greybox) Greybox->UnregisterScreen(V);
		GI->Shutdown();
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
	};
	if (!TestNotNull(TEXT("greybox subsystem"), Greybox) || !TestNotNull(TEXT("family subsystem"), Family)) return false;
	APlayerController* PC = World->GetFirstPlayerController();
	if (!PC)
	{
		PC = World->SpawnActor<APlayerController>();
		World->AddController(PC);
	}
	APawn* Pawn = World->SpawnActor<APawn>();
	USceneComponent* PawnRoot = NewObject<USceneComponent>(Pawn);
	Pawn->SetRootComponent(PawnRoot);
	PawnRoot->RegisterComponent();
	PC->Possess(Pawn);
	auto Room = [&](int32 Number, double X)
	{
		ADinkScreenVolume* V = World->SpawnActor<ADinkScreenVolume>();
		V->ScreenNumber = Number;
		V->Corners.NW = FVector2D(X, 0);
		V->Corners.NE = FVector2D(X + 6, 0);
		V->Corners.SW = FVector2D(X, 4);
		V->Corners.SE = FVector2D(X + 6, 4);
		FBox Box(ForceInit);
		Box += V->MapPixelToWorld(0, 0);
		Box += V->MapPixelToWorld(600, 400);
		V->Bounds->SetMobility(EComponentMobility::Movable);
		V->SetActorLocation(Box.GetCenter());
		V->Bounds->SetBoxExtent(Box.GetExtent() + FVector(0, 0, 1000));
		V->Bounds->UpdateBounds();
		Greybox->RegisterScreen(V);
		Rooms.Add(V);
		return V;
	};
	ADinkScreenVolume* House = Room(439, 0);
	ADinkScreenVolume* West = Room(438, 10);
	ADinkGreyboxScreen* Ground = World->SpawnActor<ADinkGreyboxScreen>();  // the family layer runs only in a world with greybox screens
	Ground->ScreenNumber = 439;
	auto Fire = [&](const ADinkScreenVolume& Screen, int32 Index)
	{
		ADinkPlaceholderActor* A = World->SpawnActor<ADinkPlaceholderActor>(Screen.MapPixelToWorld(300, 200), FRotator::ZeroRotator);
		A->ScreenNumber = Screen.ScreenNumber;
		A->Card->SetStaticMesh(Plane);
		A->Card->SetRelativeLocation(FVector(0.0, 0.0, 50.0));
		A->Origin->OriginId = FDinkOriginId(Screen.ScreenNumber, Index);
		A->Origin->Sequence = 427;  // graphics/effects/fire, class fire_fx (sprite_classes.csv)
		A->Origin->Frame = 1;
		A->Origin->ClassId = TEXT("fire_fx");
		return A;
	};
	ADinkPlaceholderActor* Roof = Fire(*House, 5);  // S439_P05: a roof fire with a smoke column (families.json effect_plume)
	ADinkPlaceholderActor* Late = Fire(*West, 97);  // a fire of 438, dressed while its card is not rendered
	Family->OnWorldBeginPlay(*World);
	if (!TestTrue(TEXT("family layer ready with the shipped families.json"), Family->IsReady())) return false;
	auto Stand = [&](const ADinkScreenVolume& Screen)
	{
		Pawn->SetActorLocation(Screen.MapPixelToWorld(300, 200));
		Greybox->RefreshCurrentScreen();
	};

	Stand(*House);
	if (!TestTrue(TEXT("Dink is on 439"), Greybox->GetCurrentScreen() == House)) return false;
	UDinkFlickerLightComponent* Light = Roof->FindComponentByClass<UDinkFlickerLightComponent>();
	UMaterialBillboardComponent* Plume = Roof->FindComponentByClass<UMaterialBillboardComponent>();
	if (!TestNotNull(TEXT("the roof fire is dressed with its light"), Light) || !TestNotNull(TEXT("and with its smoke column"), Plume)) return false;
	TestTrue(TEXT("on 439: card, light and smoke draw"), Roof->Card->GetVisibleFlag() && Light->GetVisibleFlag() && Plume->GetVisibleFlag());
	TestTrue(TEXT("on 439: the art layer owns the fire"), DinkWorldLife::IsFamilyEffect(Roof));
	// Children of a card that are not the effect's keep their own flag: one shown, one hidden by whoever made it.
	auto Child = [&](const TCHAR* Name, bool bVisible)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(Roof, Name);
		C->SetMobility(EComponentMobility::Movable);
		C->SetupAttachment(Roof->Card);
		Roof->AddInstanceComponent(C);
		C->RegisterComponent();
		C->SetVisibility(bVisible);
		return C;
	};
	UStaticMeshComponent* OtherShown = Child(TEXT("OtherShown"), true);
	UStaticMeshComponent* OtherHidden = Child(TEXT("OtherHidden"), false);
	TestFalse(TEXT("438's card is not rendered while Dink is on 439"), Late->Card->GetVisibleFlag());
	Family->ApplyScreen(438);  // what the environment layer's neighbour dressing does
	UDinkFlickerLightComponent* LateLight = Late->FindComponentByClass<UDinkFlickerLightComponent>();
	if (!TestNotNull(TEXT("the 438 fire is dressed with its light"), LateLight)) return false;
	TestFalse(TEXT("dressed off its screen: its light starts as its card is, not rendered"), LateLight->GetVisibleFlag());

	Stand(*West);
	TestFalse(TEXT("on 438: 439's card is not rendered"), Roof->Card->GetVisibleFlag());
	TestFalse(TEXT("on 438: nor its light"), Light->GetVisibleFlag());
	TestFalse(TEXT("on 438: nor its smoke column"), Plume->GetVisibleFlag());
	TestTrue(TEXT("on 438: another child of the card keeps its flag (shown)"), OtherShown->GetVisibleFlag());
	TestFalse(TEXT("on 438: another child of the card keeps its flag (hidden)"), OtherHidden->GetVisibleFlag());
	TestTrue(TEXT("on 438: the art layer still owns 439's fire (the world-life layer adds none)"), DinkWorldLife::IsFamilyEffect(Roof));
	TestTrue(TEXT("on 438: 438's fire and its light draw"), Late->Card->GetVisibleFlag() && LateLight->GetVisibleFlag());

	Stand(*House);
	TestTrue(TEXT("back on 439: card, light and smoke draw again"), Roof->Card->GetVisibleFlag() && Light->GetVisibleFlag() && Plume->GetVisibleFlag());
	TestFalse(TEXT("back on 439: 438's light is not rendered"), LateLight->GetVisibleFlag());
	TestTrue(TEXT("back on 439: the other children are as they were"), OtherShown->GetVisibleFlag() && !OtherHidden->GetVisibleFlag());

	Rule->SetWithCurrentPriority(0);
	Greybox->RefreshCurrentScreen();
	TestTrue(TEXT("rule off: every fire, light and smoke column draws as dressed"),
		Roof->Card->GetVisibleFlag() && Light->GetVisibleFlag() && Plume->GetVisibleFlag() && Late->Card->GetVisibleFlag() && LateLight->GetVisibleFlag());
	TestTrue(TEXT("rule off: the other children are as they were"), OtherShown->GetVisibleFlag() && !OtherHidden->GetVisibleFlag());
	return true;
}
