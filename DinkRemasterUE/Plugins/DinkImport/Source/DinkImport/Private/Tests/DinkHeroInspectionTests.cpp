#include "DinkHeroInspectionLibrary.h"
#include "Animation/Skeleton.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/SkinnedAssetCommon.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "ReferenceSkeleton.h"
#include "Misc/AutomationTest.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/Package.h"

#if WITH_DEV_AUTOMATION_TESTS
namespace
{
TSharedPtr<FJsonObject> Parse(const FString& Text)
{
    TSharedPtr<FJsonObject> O;
    FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),O); return O;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHeroSkeletalInspectionTest,"Dink.Import.Inspection.HeroSkeletalReadback",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FDinkHeroSkeletalInspectionTest::RunTest(const FString&)
{
    const auto Null=Parse(UDinkHeroInspectionLibrary::InspectSkeletonReference(nullptr));
    if (!TestTrue(TEXT("null skeleton JSON"),Null.IsValid())) return false;
    TestFalse(TEXT("null explicitly invalid"),Null->GetBoolField(TEXT("valid")));
    const auto NullMesh=Parse(UDinkHeroInspectionLibrary::InspectSkeletalMeshLod(nullptr,0,{}));
    TestFalse(TEXT("null mesh explicitly invalid"),NullMesh->GetBoolField(TEXT("valid")));
    USkeletalMesh* Mesh=NewObject<USkeletalMesh>(GetTransientPackage(),NAME_None,RF_Transient);
    {
        FReferenceSkeletonModifier Modify(Mesh->GetRefSkeleton(),nullptr);
        Modify.Add(FMeshBoneInfo(TEXT("root"),TEXT("root"),INDEX_NONE),FTransform::Identity);
        Modify.Add(FMeshBoneInfo(TEXT("child"),TEXT("child"),0),FTransform(FVector(0,0,12)));
        Modify.Add(FMeshBoneInfo(TEXT("left"),TEXT("left"),1),FTransform(FVector(2,0,0)));
        Modify.Add(FMeshBoneInfo(TEXT("right"),TEXT("right"),1),FTransform(FVector(-2,0,0)));
    }
    USkeleton* Skeleton=NewObject<USkeleton>(GetTransientPackage(),NAME_None,RF_Transient);
    Skeleton->MergeAllBonesToBoneTree(Mesh); // Test-only fixture construction, not inspector behavior.
    Mesh->SetSkeleton(Skeleton);
    const FString RigBefore=UDinkHeroInspectionLibrary::InspectSkeletonReference(Skeleton);
    const bool Dirty=Mesh->GetOutermost()->IsDirty();
    const auto Rig=Parse(RigBefore);
    TestEqual(TEXT("shared skeleton actual inventory"),Rig->GetArrayField(TEXT("bones")).Num(),4);
    TestEqual(TEXT("actual empty virtual bone inventory"),Rig->GetArrayField(TEXT("virtual_bones")).Num(),0);
    FSkeletalMeshLODModel* L=new FSkeletalMeshLODModel(); Mesh->GetImportedModel()->LODModels.Add(L);
    L->NumVertices=3; L->NumTexCoords=1; L->IndexBuffer={0,1,2};
    FSkelMeshSection& Section=L->Sections.AddDefaulted_GetRef();
    Section.MaterialIndex=1; Section.BaseVertexIndex=0; Section.BaseIndex=0; Section.NumTriangles=1; Section.NumVertices=3;
    Section.BoneMap={3,1,0,2}; Section.SoftVertices.SetNumZeroed(3);
    for (int32 I=0;I<3;++I)
    {
        FSoftSkinVertex& V=Section.SoftVertices[I]; V.Position=FVector3f(I==2?0:I,0,0); V.TangentX=FVector3f(1,0,0); V.TangentY=FVector3f(0,-1,0); V.TangentZ=FVector4f(0,0,-1,1); V.UVs[0]=FVector2f(.25f*I,.75f);
        V.InfluenceBones[0]=0; V.InfluenceWeights[0]=32768; V.InfluenceBones[1]=1; V.InfluenceWeights[1]=16384;
        V.InfluenceBones[2]=2; V.InfluenceWeights[2]=8192; V.InfluenceBones[3]=3; V.InfluenceWeights[3]=8191;
    }
    Mesh->GetMaterials().SetNum(3);
    Mesh->GetMaterials()[2].MaterialSlotName=TEXT("remapped_slot");
    FSkeletalMeshLODInfo& Info=Mesh->AddLODInfo(); Info.LODMaterialMap={2}; Info.BuildSettings.bRecomputeNormals=false;
    // Build test-only CPU buffers directly. No mesh build, renderer resource or package save.
    Mesh->AllocateResourceForRendering();
    FSkeletalMeshLODRenderData* R=new FSkeletalMeshLODRenderData(); Mesh->GetResourceForRendering()->LODRenderData.Add(R);
    R->StaticVertexBuffers.PositionVertexBuffer.Init(3,true); R->StaticVertexBuffers.StaticMeshVertexBuffer.Init(3,1,true);
    R->SkinWeightVertexBuffer.SetNeedsCPUAccess(true); R->SkinWeightVertexBuffer.SetMaxBoneInfluences(4); R->SkinWeightVertexBuffer.Init(Section.SoftVertices);
    R->MultiSizeIndexContainer.RebuildIndexBuffer(4,{0,1,2});
    FSkelMeshRenderSection& RS=R->RenderSections.AddDefaulted_GetRef(); RS.MaterialIndex=1; RS.BaseVertexIndex=0; RS.NumVertices=3; RS.BaseIndex=0; RS.NumTriangles=1; RS.BoneMap={3,1,0,2};
    for (uint32 I=0;I<3;++I)
    {
        R->StaticVertexBuffers.PositionVertexBuffer.VertexPosition(I)=Section.SoftVertices[I].Position;
        R->StaticVertexBuffers.StaticMeshVertexBuffer.SetVertexTangents(I,FVector3f(1,0,0),FVector3f(0,-1,0),FVector3f(0,0,-1));
        R->StaticVertexBuffers.StaticMeshVertexBuffer.SetVertexUV(I,0,Section.SoftVertices[I].UVs[0]);
    }
    const FString Text=UDinkHeroInspectionLibrary::InspectSkeletalMeshLod(Mesh,0,{0,2}); const auto O=Parse(Text);
    if (!TestTrue(TEXT("skeletal readback JSON"),O.IsValid())) return false;
    for (const TCHAR* Rep:{TEXT("source"),TEXT("built")})
    {
        const auto Data=O->GetObjectField(Rep); TestEqual(TEXT("CPU representation present"),Data->GetStringField(TEXT("state")),FString(TEXT("available")));
        TestEqual(TEXT("all normal signs preserved"),Data->GetIntegerField(TEXT("negative_z_normals")),3);
        TestEqual(TEXT("actual4nonzero influences"),Data->GetIntegerField(TEXT("max_nonzero_influences")),4);
        TestEqual(TEXT("valid section-local map"),Data->GetIntegerField(TEXT("invalid_bone_map_vertices")),0);
        const auto S=Data->GetArrayField(TEXT("sections"))[0]->AsObject();
        TestEqual(TEXT("raw slot is independent"),S->GetIntegerField(TEXT("material_index")),1);
        TestEqual(TEXT("LOD map indexed by SECTION, not raw material"),S->GetIntegerField(TEXT("resolved_material_index")),2);
        const auto Sample=Data->GetArrayField(TEXT("samples"))[0]->AsObject(); const auto& W=Sample->GetArrayField(TEXT("influences"));
        TestEqual(TEXT("local0 maps to mesh right3"),W[0]->AsObject()->GetIntegerField(TEXT("mesh_bone")),3);
        TestEqual(TEXT("local1 maps to mesh child1"),W[1]->AsObject()->GetIntegerField(TEXT("mesh_bone")),1);
        TestTrue(TEXT("known weight survives source/buffer quantization"),FMath::Abs(W[0]->AsObject()->GetNumberField(TEXT("weight"))-.5)<.005);
        const auto Seam=Data->GetArrayField(TEXT("samples"))[1]->AsObject();
        TestEqual(TEXT("seam vertex shares position"),Sample->GetArrayField(TEXT("position_cm"))[0]->AsNumber(),Seam->GetArrayField(TEXT("position_cm"))[0]->AsNumber());
        TestEqual(TEXT("seam first UV exact"),Sample->GetArrayField(TEXT("uvs"))[0]->AsArray()[0]->AsNumber(),0.0);
        TestEqual(TEXT("seam second UV retained independently"),Seam->GetArrayField(TEXT("uvs"))[0]->AsArray()[0]->AsNumber(),0.5);
    }
    TestEqual(TEXT("readback deterministic"),UDinkHeroInspectionLibrary::InspectSkeletalMeshLod(Mesh,0,{0,2}),Text);
    TestEqual(TEXT("shared rig remains byte-identical JSON"),UDinkHeroInspectionLibrary::InspectSkeletonReference(Skeleton),RigBefore);
    TestEqual(TEXT("dirty flag unchanged"),Mesh->GetOutermost()->IsDirty(),Dirty);
    TestFalse(TEXT("inspector did not change normal setting"),Info.BuildSettings.bRecomputeNormals);
    Section.BoneMap[0]=99; // Invalid section-local mapping must not become a successful empty readback.
    const auto InvalidMap=Parse(UDinkHeroInspectionLibrary::InspectSkeletalMeshLod(Mesh,0,{0}));
    TestEqual(TEXT("invalid BoneMap state is explicit"),InvalidMap->GetObjectField(TEXT("source"))->GetStringField(TEXT("state")),FString(TEXT("invalid_bone_map")));
    TestEqual(TEXT("all invalid weighted vertices counted"),InvalidMap->GetObjectField(TEXT("source"))->GetIntegerField(TEXT("invalid_bone_map_vertices")),3);
    Section.BoneMap[0]=3;
    const auto Missing=Parse(UDinkHeroInspectionLibrary::InspectSkeletalMeshLod(Mesh,4,{}));
    TestEqual(TEXT("missing LOD fails explicitly"),Missing->GetObjectField(TEXT("built"))->GetStringField(TEXT("state")),FString(TEXT("missing_lod_unavailable")));
    const auto Bad=Parse(UDinkHeroInspectionLibrary::InspectSkeletalMeshLod(Mesh,0,{-1}));
    TestEqual(TEXT("negative sample rejects"),Bad->GetStringField(TEXT("state")),FString(TEXT("invalid_request")));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHeroTextureInspectionTest,"Dink.Import.Inspection.HeroTextureReadback",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FDinkHeroTextureInspectionTest::RunTest(const FString&)
{
    const auto Null=Parse(UDinkHeroInspectionLibrary::InspectTexturePixels(nullptr,{})); TestFalse(TEXT("null texture invalid"),Null->GetBoolField(TEXT("valid")));
    UTexture2D* T=UTexture2D::CreateTransient(2,1,PF_A32B32G32R32F);
    if (!TestNotNull(TEXT("transient F32 texture"),T)) return false;
    const FLinearColor Colors[2]={FLinearColor(.75f,.25f,.125f,1),FLinearColor(.5f,.5f,1,1)};
    T->Source.Init(2,1,1,1,TSF_RGBA32F,reinterpret_cast<const uint8*>(Colors));
    T->SRGB=false; T->CompressionSettings=TC_HDR_F32;
    void* Bytes=T->GetPlatformData()->Mips[0].BulkData.Lock(LOCK_READ_WRITE); FMemory::Memcpy(Bytes,Colors,sizeof(Colors)); T->GetPlatformData()->Mips[0].BulkData.Unlock();
    TArray64<uint8> SourceBefore; T->Source.GetMipData(SourceBefore,0);
    auto& Bulk=T->GetPlatformData()->Mips[0].BulkData;
    TArray64<uint8> PlatformBefore; PlatformBefore.SetNumUninitialized(Bulk.GetBulkDataSize());
    const void* Original=Bulk.LockReadOnly(); FMemory::Memcpy(PlatformBefore.GetData(),Original,PlatformBefore.Num()); Bulk.Unlock();
    const bool OriginalSRGB=T->SRGB,OriginalFlip=T->bFlipGreenChannel;
    const auto OriginalCompression=T->CompressionSettings;
    const bool Dirty=T->GetOutermost()->IsDirty(); const FString Text=UDinkHeroInspectionLibrary::InspectTexturePixels(T,{{0,0},{1,0}}); const auto O=Parse(Text);
    if (!TestTrue(TEXT("texture snapshot validJSON"),O.IsValid())) return false;
    for (const TCHAR* Rep:{TEXT("source"),TEXT("platform")})
    {
        const auto Data=O->GetObjectField(Rep); TestEqual(TEXT("source/platform actual readable"),Data->GetStringField(TEXT("state")),FString(TEXT("available")));
        const auto Sample=Data->GetArrayField(TEXT("samples"))[0]->AsObject();
        TestTrue(TEXT("RGB preserves negative decodedZ"),Sample->GetArrayField(TEXT("explicit_rgb_normal_decode"))[2]->AsNumber()<0);
        TestTrue(TEXT("decode flips OpenGL green exactly once"),Sample->GetArrayField(TEXT("explicit_rgb_normal_decode"))[1]->AsNumber()>0);
        TestEqual(TEXT("F32 red exact"),Sample->GetArrayField(TEXT("stored_rgba"))[0]->AsNumber(),.75);
    }
    TestEqual(TEXT("texture repeated deterministic"),UDinkHeroInspectionLibrary::InspectTexturePixels(T,{{0,0},{1,0}}),Text);
    TestEqual(TEXT("texture dirty unchanged"),T->GetOutermost()->IsDirty(),Dirty);
    TArray64<uint8> SourceAfter; T->Source.GetMipData(SourceAfter,0);
    TestTrue(TEXT("actual Source bytes unchanged"),SourceAfter==SourceBefore);
    TestEqual(TEXT("platform bulk size unchanged"),Bulk.GetBulkDataSize(),int64(PlatformBefore.Num()));
    const void* After=Bulk.LockReadOnly();
    TestTrue(TEXT("actual platform bytes unchanged"),FMemory::Memcmp(After,PlatformBefore.GetData(),PlatformBefore.Num())==0); Bulk.Unlock();
    TestEqual(TEXT("sRGB unchanged"),bool(T->SRGB),OriginalSRGB);
    TestEqual(TEXT("green flip unchanged"),bool(T->bFlipGreenChannel),OriginalFlip);
    TestEqual(TEXT("compression unchanged"),T->CompressionSettings,OriginalCompression);
    const auto Bad=Parse(UDinkHeroInspectionLibrary::InspectTexturePixels(T,{{2,0}}));
    TestEqual(TEXT("bounds reject explicit source state"),Bad->GetObjectField(TEXT("source"))->GetStringField(TEXT("state")),FString(TEXT("sample_out_of_bounds")));
    return true;
}
#endif
