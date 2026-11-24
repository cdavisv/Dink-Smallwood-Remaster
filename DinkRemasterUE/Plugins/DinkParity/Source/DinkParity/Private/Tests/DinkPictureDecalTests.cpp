// Ground decals of environment.json `decals`: a blood or burn decal drawn from one 1997 picture frame (`pictures`) lies where
// that picture lay and is as large as its card, so the remaster never shows less blood than 1997 (owner's rule); every decal
// sits on the landforms' raised ground (#153), not on the flat floor under it.
#include "DinkTestHelpers.h"
#include "DinkEnvironmentSubsystem.h"
#include "Dom/JsonObject.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPictureDecalSquare, "Dink.Art.PictureDecal.SquareFromCard", DINK_TEST_FLAGS)
bool FDinkPictureDecalSquare::RunTest(const FString&)
{
	FVector Centre;
	double Half = 0.0, Yaw = 0.0;
	// S091_P09: picture 188 frame 4 enlarged to 2.37 x 3.40 m, its bottom edge 30 cm below the placement row
	UDinkEnvironmentSubsystem::CardDecalSquare(FTransform(FRotator::ZeroRotator, FVector(1000.0, 2000.0, -30.0), FVector(2.37, 1.0, 3.40)), 0.0, 0.0, 1.15, Centre, Half, Yaw);
	TestTrue(TEXT("the decal covers the whole card and its margin"), FMath::IsNearlyEqual(Half, 0.5 * 340.0 * 1.15, 0.01));
	TestTrue(TEXT("never smaller than the card"), 2.0 * Half >= 340.0);
	// rows above the placement point lie to the north (-Y): bottom edge 30 cm south, middle 170 cm north of that
	TestTrue(TEXT("middle of the picture on the ground"), Centre.Equals(FVector(1000.0, 2000.0 - (-30.0 + 170.0), 0.0), 0.01));
	TestTrue(TEXT("an unturned screen leaves the decal unturned"), FMath::IsNearlyZero(Yaw, 0.001));
	// a small enlargement gives a small decal: a picture decal has no class size (S094_P05: 0.53 x 0.30 m)
	UDinkEnvironmentSubsystem::CardDecalSquare(FTransform(FRotator::ZeroRotator, FVector::ZeroVector, FVector(0.37, 1.0, 0.53)), 0.0, 0.0, 1.15, Centre, Half, Yaw);
	TestTrue(TEXT("small pictures stay small"), FMath::IsNearlyEqual(Half, 0.5 * 53.0 * 1.15, 0.01));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkDecalOnRaisedGround, "Dink.Art.PictureDecal.OnRaisedGround", DINK_TEST_FLAGS)
bool FDinkDecalOnRaisedGround::RunTest(const FString&)
{
	double Lift = 0.0, Depth = 0.0;
	// flat floor: no lift, the box keeps its flat depth
	UDinkEnvironmentSubsystem::DecalGroundFit([](const FVector2D&) { return 0.0; }, FVector(100.0, 200.0, 0.0), 80.0, 60.0, 0.0, 18.0, Lift, Depth);
	TestTrue(TEXT("flat ground"), FMath::IsNearlyZero(Lift, 1e-6) && FMath::IsNearlyEqual(Depth, 18.0, 1e-6));
	// a level rise of 42 cm (a knoll's top): the decal rises with it and stays as shallow
	UDinkEnvironmentSubsystem::DecalGroundFit([](const FVector2D&) { return 42.0; }, FVector(100.0, 200.0, 0.0), 80.0, 60.0, 0.0, 18.0, Lift, Depth);
	TestTrue(TEXT("on a level rise"), FMath::IsNearlyEqual(Lift, 42.0, 1e-6) && FMath::IsNearlyEqual(Depth, 18.0, 1e-6));
	// a bank rising 0.25 cm per cm to the north (-Y), 30 cm high at the decal's middle: the box sits at the height of its middle and
	// is deep enough for its north edge (+20 cm) and its south edge (-20 cm)
	auto Bank = [](const FVector2D& P) { return 30.0 + 0.25 * (200.0 - P.Y); };
	UDinkEnvironmentSubsystem::DecalGroundFit(Bank, FVector(100.0, 200.0, 0.0), 80.0, 60.0, 0.0, 18.0, Lift, Depth);
	TestTrue(TEXT("middle height on a bank"), FMath::IsNearlyEqual(Lift, 30.0, 1e-6));
	TestTrue(TEXT("deep enough for the slope"), FMath::IsNearlyEqual(Depth, 18.0 + 20.0, 1e-6));
	TestTrue(TEXT("the whole footprint is inside the box"), Bank(FVector2D(100.0, 120.0)) <= Lift + Depth && Bank(FVector2D(100.0, 280.0)) >= Lift - Depth);
	// a turned screen turns the footprint: north is +X at yaw 90
	UDinkEnvironmentSubsystem::DecalGroundFit([](const FVector2D& P) { return 0.5 * P.X; }, FVector(0.0, 0.0, 0.0), 80.0, 10.0, 90.0, 18.0, Lift, Depth);
	TestTrue(TEXT("turned with the screen"), FMath::IsNearlyZero(Lift, 1e-6) && FMath::IsNearlyEqual(Depth, 18.0 + 40.0, 1e-3));
	// a cliff under one corner does not make a box that paints the cliff face from top to bottom
	UDinkEnvironmentSubsystem::DecalGroundFit([](const FVector2D& P) { return P.X > 150.0 ? 900.0 : 0.0; }, FVector(100.0, 200.0, 0.0), 80.0, 60.0, 0.0, 18.0, Lift, Depth);
	TestTrue(TEXT("at the foot of a cliff: on its own ground, depth capped"), FMath::IsNearlyZero(Lift, 1e-6) && FMath::IsNearlyEqual(Depth, 90.0, 1e-6));
	// tilted onto the slope (asked for with OutNormal): on the same bank the box lies along the ground, so it needs no extra depth,
	// and its normal is the bank's (rising to the north, -Y: the normal leans south, +Y)
	FVector Normal = FVector::ZeroVector;
	UDinkEnvironmentSubsystem::DecalGroundFit(Bank, FVector(100.0, 200.0, 0.0), 80.0, 60.0, 0.0, 18.0, Lift, Depth, &Normal);
	TestTrue(TEXT("tilted: middle height"), FMath::IsNearlyEqual(Lift, 30.0, 1e-6));
	TestTrue(TEXT("tilted: the flat depth is enough on an even slope"), FMath::IsNearlyEqual(Depth, 18.0, 1e-6));
	TestTrue(TEXT("tilted: the bank's normal"), Normal.Equals(FVector(0.0, 0.25, 1.0).GetSafeNormal(), 1e-6));
	// level ground gives an upright normal; a cliff is not followed past the cap (50 degrees), and the depth cap holds
	UDinkEnvironmentSubsystem::DecalGroundFit([](const FVector2D&) { return 42.0; }, FVector(100.0, 200.0, 0.0), 80.0, 60.0, 0.0, 18.0, Lift, Depth, &Normal);
	TestTrue(TEXT("tilted: upright on level ground"), Normal.Equals(FVector::UpVector, 1e-6) && FMath::IsNearlyEqual(Depth, 18.0, 1e-6));
	UDinkEnvironmentSubsystem::DecalGroundFit([](const FVector2D& P) { return P.X > 150.0 ? 900.0 : 0.0; }, FVector(100.0, 200.0, 0.0), 80.0, 60.0, 0.0, 18.0, Lift, Depth, &Normal);
	TestTrue(TEXT("tilted: never past the cap"), Normal.Z >= FMath::Cos(FMath::DegreesToRadians(50.0)) - 1e-6 && Depth <= 90.0 + 1e-6);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPictureDecalData, "Dink.Art.PictureDecal.ShippedDecalsLoad", DINK_TEST_FLAGS)
bool FDinkPictureDecalData::RunTest(const FString&)
{
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!TestTrue(TEXT("environment.json reads"), FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Environment/environment.json")))
		&& FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) && Root.IsValid())) return false;
	const TSharedPtr<FJsonObject>* Decals = nullptr;
	if (!TestTrue(TEXT("decals section"), Root->TryGetObjectField(TEXT("decals"), Decals) && Decals)) return false;
	int32 Pictures = 0, Cells = 0;
	// a decal the renderer cannot place (wrong domain) would be drawn as a surface material or not at all; a row whose
	// material is missing silently leaves the 1997 card standing
	auto Check = [&](const FString& What, const FString& Path) -> bool
	{
		UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, *Path);
		if (!TestNotNull(*FString::Printf(TEXT("%s loads: %s"), *What, *Path), M)) return false;
		TestTrue(*FString::Printf(TEXT("%s is a deferred decal material"), *Path), M->GetMaterial() && M->GetMaterial()->MaterialDomain == MD_DeferredDecal);
		return true;
	};
	for (const auto& Pair : (*Decals)->Values)
	{
		const TSharedPtr<FJsonObject>* Row = nullptr;
		if (!Pair.Value->TryGetObject(Row) || !Row) continue;
		const FString Class(Pair.Key.ToView());
		const TSharedPtr<FJsonObject>* Pics = nullptr;
		if ((*Row)->TryGetObjectField(TEXT("pictures"), Pics) && Pics)
		{
			for (const auto& Pic : (*Pics)->Values)
			{
				FString Sequence, Frame;
				const FString Key(Pic.Key.ToView());
				TestTrue(*FString::Printf(TEXT("%s picture key %s is <sequence>_<frame>"), *Class, *Key), Key.Split(TEXT("_"), &Sequence, &Frame) && FCString::Atoi(*Sequence) > 0 && FCString::Atoi(*Frame) > 0);
				if (Check(FString::Printf(TEXT("%s picture decal %s"), *Class, *Key), Pic.Value->AsString())) ++Pictures;
			}
		}
		const TArray<TSharedPtr<FJsonValue>>* Materials = nullptr;
		if ((*Row)->TryGetArrayField(TEXT("materials"), Materials) && Materials)
		{
			for (const TSharedPtr<FJsonValue>& V : *Materials) if (Check(Class + TEXT(" decal"), V->AsString())) ++Cells;
		}
	}
	TestTrue(TEXT("the eight placed blood pictures (187/1-3, 188/2, 188/4, 189/1, 189/2, 189/4) have their decals"), Pictures >= 8);
	TestTrue(TEXT("blood and burn each have their four class cells"), Cells >= 8);
	return true;
}
