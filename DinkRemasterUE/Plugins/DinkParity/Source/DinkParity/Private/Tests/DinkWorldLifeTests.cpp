// Stream world-alive (15 Nov 2026): the pure parts of the world life layer (shared wind, walk-through pushers, ground
// dust, sprite roles) and its data file. The layer itself draws nothing in a process that cannot render (these tests,
// the probe): Dink.World.Headless checks that, so the probe traces cannot move.
#include "DinkTestHelpers.h"
#include "DinkWorldLifeSubsystem.h"
#include "DinkWorldLifePresenter.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include <limits>

static const float DinkWorldLifeTestNaN = std::numeric_limits<float>::quiet_NaN();

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldWindStrengthTest, "Dink.World.Wind.EffectiveStrength", DINK_TEST_FLAGS)
bool FDinkWorldWindStrengthTest::RunTest(const FString&)
{
	TestEqual(TEXT("indoors is still"), DinkWorldLife::EffectiveStrength(1.2f, 1.f, true, 3), 0.f);
	TestEqual(TEXT("Low foliage scalability is still"), DinkWorldLife::EffectiveStrength(1.2f, 1.f, false, 0), 0.f);
	TestEqual(TEXT("dink.World.Wind 0 is still"), DinkWorldLife::EffectiveStrength(1.2f, 0.f, false, 3), 0.f);
	TestEqual(TEXT("profile times the console multiplier"), DinkWorldLife::EffectiveStrength(0.8f, 1.5f, false, 2), 1.2f, 1e-5f);
	TestEqual(TEXT("clamped to a gale"), DinkWorldLife::EffectiveStrength(1.6f, 4.f, false, 3), 2.f);
	TestEqual(TEXT("negative inputs are still air"), DinkWorldLife::EffectiveStrength(-1.f, 1.f, false, 3), 0.f);
	TestEqual(TEXT("NaN is still air"), DinkWorldLife::EffectiveStrength(DinkWorldLifeTestNaN, 1.f, false, 3), 0.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldGustTest, "Dink.World.Wind.GlobalGust", DINK_TEST_FLAGS)
bool FDinkWorldGustTest::RunTest(const FString&)
{
	double Sum = 0.0, Min = 10.0, Max = 0.0, MaxStep = 0.0;
	float Prev = DinkWorldLife::GlobalGust(0.0, 1.f);
	const int32 N = 60 * 600;   // ten minutes at 60 fps
	for (int32 I = 1; I <= N; ++I)
	{
		const float G = DinkWorldLife::GlobalGust(I / 60.0, 1.f);
		if (!FMath::IsFinite(G)) { AddError(FString::Printf(TEXT("gust not finite at frame %d"), I)); return false; }
		Sum += G; Min = FMath::Min<double>(Min, G); Max = FMath::Max<double>(Max, G);
		MaxStep = FMath::Max<double>(MaxStep, FMath::Abs(G - Prev));
		Prev = G;
	}
	TestTrue(FString::Printf(TEXT("gust stays in 0.3..1.8 (%.3f..%.3f)"), Min, Max), Min >= 0.3 && Max <= 1.8);
	TestTrue(FString::Printf(TEXT("gust averages about 1 (%.3f)"), Sum / N), FMath::Abs(Sum / N - 1.0) < 0.08);
	TestTrue(FString::Printf(TEXT("gust swings (range %.3f)"), Max - Min), Max - Min > 0.6);
	TestTrue(FString::Printf(TEXT("gust is smooth frame to frame (max step %.4f)"), MaxStep), MaxStep < 0.02);
	TestEqual(TEXT("no gustiness, no gust"), DinkWorldLife::GlobalGust(123.4, 0.f), 1.f, 1e-6f);
	TestTrue(TEXT("a NaN time is safe"), FMath::IsFinite(DinkWorldLife::GlobalGust(DinkWorldLifeTestNaN, 1.f)));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldEaseTest, "Dink.World.Wind.EaseShortestTurn", DINK_TEST_FLAGS)
bool FDinkWorldEaseTest::RunTest(const FString&)
{
	FDinkWindProfile A, B;
	A.DirectionDeg = 350.f; A.Strength = 1.f; A.Gustiness = 0.f;
	B.DirectionDeg = 10.f; B.Strength = 2.f; B.Gustiness = 1.f;
	const FDinkWindProfile H = DinkWorldLife::EaseProfile(A, B, 0.5f);
	TestEqual(TEXT("halfway from 350 to 10 degrees is 0, not 180"), FMath::Abs(FMath::FindDeltaAngleDegrees(H.DirectionDeg, 0.f)), 0.f, 1e-3f);
	TestEqual(TEXT("strength blends"), H.Strength, 1.5f, 1e-5f);
	TestEqual(TEXT("alpha clamps"), DinkWorldLife::EaseProfile(A, B, 7.f).Strength, 2.f, 1e-5f);
	const FVector2D D = DinkWorldLife::DirectionOf(90.f);
	TestTrue(TEXT("90 degrees blows to +Y"), FMath::IsNearlyEqual(D.Y, 1.0, 1e-5) && FMath::IsNearlyZero(D.X, 1e-5));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldPushersTest, "Dink.World.Pushers.Nearest", DINK_TEST_FLAGS)
bool FDinkWorldPushersTest::RunTest(const FString&)
{
	TArray<FVector4f> C = {
		FVector4f(900.f, 0.f, 70.f, 1.f),     // far
		FVector4f(100.f, 0.f, 95.f, 0.45f),   // Dink standing
		FVector4f(300.f, 0.f, 70.f, 0.f),     // a creature standing still: no push
		FVector4f(200.f, 0.f, 70.f, 1.f),
		FVector4f(5000.f, 0.f, 70.f, 1.f),    // out of reach
		FVector4f(250.f, 0.f, 70.f, 0.7f),
		FVector4f(DinkWorldLifeTestNaN, 0.f, 70.f, 1.f),       // broken: ignored
	};
	TArray<FVector4f> Out;
	DinkWorldLife::PickPushers(FVector2D(0, 0), C, 2500.f, 4, Out);
	TestEqual(TEXT("four slots"), Out.Num(), 4);
	if (Out.Num() == 4)
	{
		TestEqual(TEXT("nearest first"), Out[0].X, 100.f);
		TestEqual(TEXT("then 200"), Out[1].X, 200.f);
		TestEqual(TEXT("then 250"), Out[2].X, 250.f);
		TestEqual(TEXT("then the far one within reach"), Out[3].X, 900.f);
	}
	DinkWorldLife::PickPushers(FVector2D(0, 0), C, 2500.f, 2, Out);
	TestEqual(TEXT("max slots respected"), Out.Num(), 2);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldDustTest, "Dink.World.Ground.Dustiness", DINK_TEST_FLAGS)
bool FDinkWorldDustTest::RunTest(const FString&)
{
	// colours like ground_colour.json's linear means
	TestTrue(TEXT("meadow turf makes no dust"), DinkWorldLife::DustinessOfGround(FLinearColor(0.09f, 0.13f, 0.04f)) < 0.1f);
	TestTrue(TEXT("forest floor moss makes little"), DinkWorldLife::DustinessOfGround(FLinearColor(0.07f, 0.09f, 0.04f)) < 0.35f);
	TestTrue(TEXT("an earth path does"), DinkWorldLife::DustinessOfGround(FLinearColor(0.20f, 0.15f, 0.10f)) > 0.9f);
	TestTrue(TEXT("dry sand does"), DinkWorldLife::DustinessOfGround(FLinearColor(0.45f, 0.38f, 0.26f)) > 0.9f);
	TestTrue(TEXT("snow does"), DinkWorldLife::DustinessOfGround(FLinearColor(0.8f, 0.82f, 0.85f)) > 0.9f);
	TestEqual(TEXT("black (no data) does not"), DinkWorldLife::DustinessOfGround(FLinearColor::Black), 0.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldRolesTest, "Dink.World.SpriteRoles", DINK_TEST_FLAGS)
bool FDinkWorldRolesTest::RunTest(const FString&)
{
	using namespace DinkWorldLifeRoles;
	const FTables T = Defaults();
	TestTrue(TEXT("item-fb.c fireball (brain 11, seq 504)"), RoleOf(T, 504, 504, 11) == EDinkLifeSpriteRole::Fireball);
	TestTrue(TEXT("item-sfb.c hellfire ball (brain 11, seq 514)"), RoleOf(T, 514, 0, 11) == EDinkLifeSpriteRole::Fireball);
	TestTrue(TEXT("arrow (brain 11, seq 25) is a plain missile"), RoleOf(T, 25, 25, 11) == EDinkLifeSpriteRole::Missile);
	TestTrue(TEXT("axe (brain 17, seq 85) is a plain missile"), RoleOf(T, 85, 85, 17) == EDinkLifeSpriteRole::Missile);
	TestTrue(TEXT("dam-fire.c explosion (seq 70, brain 7)"), RoleOf(T, 70, 0, 7) == EDinkLifeSpriteRole::Burst);
	TestTrue(TEXT("barrel break (seq 173, brain 5)"), RoleOf(T, 173, 173, 5) == EDinkLifeSpriteRole::Barrel);
	TestTrue(TEXT("a broken barrel at rest (pseq 173 only) is not a new break"), RoleOf(T, 0, 173, 0) == EDinkLifeSpriteRole::None);
	TestTrue(TEXT("a burning tree (seq 20)"), RoleOf(T, 20, 32, 0) == EDinkLifeSpriteRole::Fire);
	TestTrue(TEXT("a walking pillbug is nothing here"), RoleOf(T, 131, 0, 9) == EDinkLifeSpriteRole::None);
	TestFalse(TEXT("154 (burn mark) is not fire"), T.Fire.Contains(154));
	TestTrue(TEXT("164 (a kill's blood burst in the creature layer) is never drawn as fire"), RoleOf(T, 164, 0, 7) == EDinkLifeSpriteRole::None);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldConfigTest, "Dink.World.Config", DINK_TEST_FLAGS)
bool FDinkWorldConfigTest::RunTest(const FString&)
{
	const FString Path = FPaths::ProjectContentDir() / TEXT("Dink/Data/Environment/world_life.json");
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!TestTrue(TEXT("world_life.json reads"), FFileHelper::LoadFileToString(Text, *Path)) ||
		!TestTrue(TEXT("world_life.json parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) && Root.IsValid())) return false;
	const TSharedPtr<FJsonObject>* Wind = nullptr;
	const TSharedPtr<FJsonObject>* Regions = nullptr;
	if (!TestTrue(TEXT("wind.regions"), Root->TryGetObjectField(TEXT("wind"), Wind) && Wind && (*Wind)->TryGetObjectField(TEXT("regions"), Regions) && Regions)) return false;
	TestTrue(TEXT("every outdoor region of the world has a wind (20)"), (*Regions)->Values.Num() >= 20);
	for (const auto& Pair : (*Regions)->Values)
	{
		const TSharedPtr<FJsonObject>* O = nullptr;
		if (!TestTrue(*Pair.Key, Pair.Value->TryGetObject(O) && O)) continue;
		const double S = (*O)->GetNumberField(TEXT("strength")), G = (*O)->GetNumberField(TEXT("gustiness"));
		TestTrue(FString::Printf(TEXT("%s strength %.2f in 0..2"), *Pair.Key, S), S >= 0.0 && S <= 2.0);
		TestTrue(FString::Printf(TEXT("%s gustiness %.2f in 0..1"), *Pair.Key, G), G >= 0.0 && G <= 1.0);
	}
	const TSharedPtr<FJsonObject>* Fire = nullptr;
	TestTrue(TEXT("fire table"), Root->TryGetObjectField(TEXT("fire"), Fire) && Fire);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkWorldHeadlessTest, "Dink.World.Headless", DINK_TEST_FLAGS)
bool FDinkWorldHeadlessTest::RunTest(const FString&)
{
	// A game world in this process: the layer must stay off when nothing can be drawn (tests, the probe).
	if (FApp::CanEverRender())
	{
		AddInfo(TEXT("process renders: the headless guarantee is checked in the headless runs"));
		return true;
	}
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
	if (UDinkWorldLifeSubsystem* L = World->GetSubsystem<UDinkWorldLifeSubsystem>()) L->OnWorldBeginPlay(*World);
	if (UDinkWorldLifePresenter* P = World->GetSubsystem<UDinkWorldLifePresenter>()) P->OnWorldBeginPlay(*World);
	const UDinkWorldLifeSubsystem* Life = World->GetSubsystem<UDinkWorldLifeSubsystem>();
	if (!TestNotNull(TEXT("subsystem exists in a game world"), Life)) return false;
	TestFalse(TEXT("inactive without rendering"), Life->IsActive());
	TestEqual(TEXT("no particles"), Life->GetLiveParticles(), 0);
	const UDinkWorldLifePresenter* Presenter = World->GetSubsystem<UDinkWorldLifePresenter>();
	TestTrue(TEXT("presenter step not registered"), !Presenter || !Presenter->IsPresenting());
	return true;
}
