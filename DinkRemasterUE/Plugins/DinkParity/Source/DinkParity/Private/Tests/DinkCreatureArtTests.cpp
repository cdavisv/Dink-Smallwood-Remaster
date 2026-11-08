#include "DinkTestHelpers.h"
#include <cfloat>
#include "AssetCompilingManager.h"
#include "Animation/AnimSequence.h"
#include "Animation/BlendSpace.h"
#include "Animation/Skeleton.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "Materials/Material.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureAssetTest, "Dink.Art.CreatureRigMaterialsAndMotion", DINK_TEST_FLAGS)
bool FDinkCreatureAssetTest::RunTest(const FString&)
{
	FString Text;
	TSharedPtr<FJsonObject> Manifest;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/creatures.json"))))
	{
		AddWarning(TEXT("creature art not imported; run Scripts/import_creature_art.sh"));
		return true;
	}
	if (!TestTrue(TEXT("creature manifest parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest)) || !Manifest) return false;
	TestEqual(TEXT("creature schema"), Manifest->GetStringField(TEXT("schema")), FString(TEXT("dink-creatures/1")));
	int32 PigCount = 0;
	for (const auto& Value : Manifest->GetArrayField(TEXT("placements")))
		if (Value->AsObject()->GetStringField(TEXT("mesh")).Contains(TEXT("/Pig/SK_Pig."))) ++PigCount;
	TestEqual(TEXT("incremental imports retain five original pigs"), PigCount, 5);
	for (const TSharedPtr<FJsonValue>& Value : Manifest->GetArrayField(TEXT("assets")))
	{
		const TSharedPtr<FJsonObject> Row = Value->AsObject();
		USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *Row->GetStringField(TEXT("mesh")));
		if (!TestNotNull(TEXT("own-rig creature loads"), Mesh)) continue;
		FAssetCompilingManager::Get().FinishAllCompilation();
		if (!TestNotNull(TEXT("own creature skeleton exists"), Mesh->GetSkeleton())) continue;
		TestFalse(TEXT("creature never uses human reference skeleton"), Mesh->GetSkeleton()->GetPathName().StartsWith(TEXT("/Game/Characters/Mannequins/")));
		TestEqual(TEXT("actual creature bone count"), Mesh->GetRefSkeleton().GetNum(), int32(Row->GetNumberField(TEXT("bone_count"))));
		TestEqual(TEXT("actual three LODs"), Mesh->GetLODNum(), 3);
		const TArray<TSharedPtr<FJsonValue>>& Size = Row->GetArrayField(TEXT("expected_size_cm"));
		TestTrue(TEXT("real animal centimetre dimensions"), (Mesh->GetBounds().BoxExtent * 2).Equals(FVector(Size[0]->AsNumber(),Size[1]->AsNumber(),Size[2]->AsNumber()),1.));
		const bool bPig = Mesh->GetPathName().Contains(TEXT("/Pig/SK_Pig."));
		TestTrue(TEXT("creature respects class material budget"), Mesh->GetMaterials().Num() <= (bPig ? 4 : 6));
		TestNotNull(TEXT("creature physics asset persisted"), Mesh->GetPhysicsAsset());
		for (const FSkeletalMaterial& Slot : Mesh->GetMaterials())
		{
			if (TestNotNull(TEXT("assigned creature material"), Slot.MaterialInterface.Get()))
				TestTrue(TEXT("skeletal shader usage saved"), Slot.MaterialInterface->GetMaterial()->GetUsageByFlag(MATUSAGE_SkeletalMesh));
		}
		UBlendSpace* Blend = LoadObject<UBlendSpace>(nullptr,*Row->GetStringField(TEXT("locomotion")));
		if (!TestNotNull(TEXT("own-rig locomotion blend space"), Blend)) continue;
		TestEqual(TEXT("blend uses animal skeleton"), Blend->GetSkeleton(), Mesh->GetSkeleton());
		TestEqual(TEXT("speed axis drives locomotion"), Blend->GetBlendParameter(0).DisplayName, FString(TEXT("Speed")));
		TMap<FString,UAnimSequence*> Clips;
		for (const auto& Pair : Row->GetObjectField(TEXT("animation_reports"))->Values)
		{
			const TSharedPtr<FJsonObject> Report = Pair.Value->AsObject();
			UAnimSequence* Clip = LoadObject<UAnimSequence>(nullptr,*Report->GetStringField(TEXT("animation")));
			if (!TestNotNull(TEXT("imported action"), Clip)) continue;
			Clips.Add(FString(Pair.Key.ToView()),Clip);
			TestEqual(TEXT("action shares exact animal skeleton"), Clip->GetSkeleton(), Mesh->GetSkeleton());
			TestTrue(TEXT("action duration matches actual imported report"), FMath::Abs(Clip->GetPlayLength()-Report->GetNumberField(TEXT("duration_s"))) < .002);
			FTransform Start, Middle;
			Clip->GetBoneTransform(Start, FSkeletonPoseBoneIndex(0), FAnimExtractContext(0.,false),true);
			Clip->GetBoneTransform(Middle, FSkeletonPoseBoneIndex(0), FAnimExtractContext(Clip->GetPlayLength()*.5,false),true);
			TestTrue(TEXT("in-place action has no root drift"), Start.GetLocation().Equals(Middle.GetLocation(),.1));
		}
		// Exercise the engine's resampled blend data, not only names in the manifest.
		double WalkSpeed = 80., RunSpeed = 400.;
		Row->TryGetNumberField(TEXT("nominal_walk_speed_cm_s"), WalkSpeed);
		Row->TryGetNumberField(TEXT("nominal_run_speed_cm_s"), RunSpeed);
		TArray<TPair<FString,float>> Endpoints = {{TEXT("Idle"),0},{TEXT("Walk"),float(WalkSpeed)}};
		if (Clips.Contains(TEXT("Run"))) Endpoints.Emplace(TEXT("Run"),float(RunSpeed));
		for (const TPair<FString,float>& Point : Endpoints)
		{
			UAnimSequence* Expected = Clips.FindRef(Point.Key);
			if (!TestNotNull(TEXT("required locomotion action"), Expected)) continue;
			TArray<FBlendSampleData> Samples; int32 Cached = INDEX_NONE;
			TestTrue(TEXT("engine finds speed sample"), Blend->GetSamplesFromBlendInput(FVector(Point.Value,0,0),Samples,Cached,true));
			float Weight = 0;
			for (const FBlendSampleData& Sample : Samples)
				if (Blend->GetBlendSample(Sample.SampleDataIndex).Animation == Expected) Weight += Sample.TotalWeight;
			TestTrue(TEXT("actual idle/walk/gallop endpoint resolves correctly"), Weight > .999f);
		}
	}
	return true;
}


IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPigPenFeedAssetTest, "Dink.Art.PigPenFeedScatterLODAndMaterial", DINK_TEST_FLAGS)
bool FDinkPigPenFeedAssetTest::RunTest(const FString&)
{
    FString Text;
    TSharedPtr<FJsonObject> Manifest;
    if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/pigpen.json"))))
    {
        AddWarning(TEXT("pig pen art not imported; run Scripts/import_pigpen_art.sh"));
        return true;
    }
    if (!TestTrue(TEXT("pig pen manifest parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest)) || !Manifest) return false;
    TestEqual(TEXT("environment manifest schema"), Manifest->GetStringField(TEXT("schema")), FString(TEXT("dink-art/1")));
    const FString Path(TEXT("/Game/Dink/Kits/PigPen/SM_FeedScatter_Wheat_01.SM_FeedScatter_Wheat_01"));
    bool bRecorded = false;
    for (const auto& Value : Manifest->GetArrayField(TEXT("assets")))
    {
        const auto Row = Value->AsObject();
        if (Row->GetStringField(TEXT("mesh")) != Path) continue;
        bRecorded = true;
        TestEqual(TEXT("non-foliage grain still records three source LODs"), int32(Row->GetNumberField(TEXT("expected_lods"))), 3);
    }
    TestTrue(TEXT("grain import dimensions and LOD contract recorded"), bRecorded);
    UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Path);
    if (!TestNotNull(TEXT("original loose wheat mesh loads"), Mesh)) return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    TestTrue(TEXT("grain has real25x18cm dimensions without opaque backing"), (Mesh->GetBounds().BoxExtent * 2).Equals(FVector(25,18,.309383), .1));
    // Compare delivered surface bounds, not merely a guessed presentation offset.
    UStaticMesh* Soil = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Dink/Kits/StonebrookExterior/SM_Path_Earth_8m_01.SM_Path_Earth_8m_01"));
    if (TestNotNull(TEXT("reused soil mesh loads"), Soil))
    {
        double HighestSoil = -DBL_MAX;
        for (const auto& Value : Manifest->GetArrayField(TEXT("elements")))
        {
            const auto Row = Value->AsObject();
            if (!Row->GetStringField(TEXT("mesh")).Contains(TEXT("SM_Path_Earth_8m_01"))) continue;
            const double Z=Row->GetArrayField(TEXT("world_cm"))[2]->AsNumber();
            const double ScaleZ=Row->GetArrayField(TEXT("scale"))[2]->AsNumber();
            HighestSoil=FMath::Max(HighestSoil,Z+(Soil->GetBounds().Origin.Z+Soil->GetBounds().BoxExtent.Z)*ScaleZ);
        }
        TestTrue(TEXT("soil surface measured from delivered patches"), HighestSoil>-100.);
        const double KernelBottom=Mesh->GetBounds().Origin.Z-Mesh->GetBounds().BoxExtent.Z;
        for (const auto& Value : Manifest->GetArrayField(TEXT("elements")))
        {
            const auto Row=Value->AsObject();
            if (Row->GetStringField(TEXT("mesh"))==Path)
                TestTrue(TEXT("static kernels remain above the soil"), Row->GetArrayField(TEXT("world_cm"))[2]->AsNumber()+KernelBottom>HighestSoil+.03);
        }
        FString CreaturesText;
        TSharedPtr<FJsonObject> Creatures;
        const bool bRead=FFileHelper::LoadFileToString(CreaturesText,*(FPaths::ProjectContentDir()/TEXT("Dink/Data/Art/creatures.json")));
        if (TestTrue(TEXT("creature food presentation manifest loads"), bRead && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(CreaturesText),Creatures)) && Creatures)
            for (const auto& Value:Creatures->GetArrayField(TEXT("placements")))
            {
                const auto Row=Value->AsObject();
                FString FoodPath;
                if (Row->TryGetStringField(TEXT("food_mesh"), FoodPath) && FoodPath==Path)
                    TestTrue(TEXT("transient kernels remain above the soil while actor root stays60cm"),60.+Row->GetArrayField(TEXT("food_mesh_offset_cm"))[2]->AsNumber()+KernelBottom>HighestSoil+.03);
            }
    }
    TestEqual(TEXT("three loaded grain LODs"), Mesh->GetNumLODs(), 3);
    TestFalse(TEXT("tiny grain uses conventional LODs"), Mesh->GetNaniteSettings().bEnabled);
    TestEqual(TEXT("one grain material"), Mesh->GetStaticMaterials().Num(), 1);
    for (const auto& Slot : Mesh->GetStaticMaterials()) TestNotNull(TEXT("grain material assigned"), Slot.MaterialInterface.Get());
    if (const FStaticMeshRenderData* Data = Mesh->GetRenderData())
    {
        const int32 Triangles[] = {1280,672,208};
        TestEqual(TEXT("all three grain LOD render buffers exist"), Data->LODResources.Num(), 3);
        for (int32 LOD = 0; LOD < FMath::Min(3, Data->LODResources.Num()); ++LOD)
        {
            const auto& Resource = Data->LODResources[LOD];
            TestEqual(FString::Printf(TEXT("grain LOD%d has independent source geometry"), LOD), Resource.GetNumTriangles(), Triangles[LOD]);
            const auto& Vertices = Resource.VertexBuffers.StaticMeshVertexBuffer;
            int32 BadNormals = 0;
            for (uint32 Index=0; Index<Vertices.GetNumVertices(); ++Index)
            {
                const auto N=Vertices.VertexTangentZ(Index);
                const FVector3f Normal(N.X,N.Y,N.Z);
                BadNormals += Normal.ContainsNaN() || Normal.SizeSquared()<.8f ? 1 : 0;
            }
            TestEqual(FString::Printf(TEXT("grain LOD%d normals remain usable"), LOD), BadNormals, 0);
        }
    }
    else AddError(TEXT("grain render buffers missing"));
    return true;
}
