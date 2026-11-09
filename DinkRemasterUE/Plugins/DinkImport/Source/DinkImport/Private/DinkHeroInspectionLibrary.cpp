#include "DinkHeroInspectionLibrary.h"
#include "Animation/Skeleton.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/TextureDefines.h"
#include "Engine/SkinnedAssetCommon.h"
#include "EditorFramework/AssetImportData.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "Materials/MaterialInterface.h"
#include "ImageCore.h"
#include "Math/Float16Color.h"
#include "Misc/SecureHash.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/UnrealType.h"

namespace DinkHeroInspect
{
using JObject = TSharedRef<FJsonObject>;
using JArray = TArray<TSharedPtr<FJsonValue>>;
JObject Object() { return MakeShared<FJsonObject>(); }
TSharedPtr<FJsonValue> Value(const JObject& O) { return MakeShared<FJsonValueObject>(O); }
FString Json(const JObject& O) { FString S; FJsonSerializer::Serialize(O, TJsonWriterFactory<>::Create(&S)); return S; }
JObject Start(const TCHAR* Schema, const UObject* Asset)
{
    JObject O = Object(); O->SetStringField(TEXT("schema"), Schema);
    O->SetBoolField(TEXT("valid"), Asset != nullptr);
    if (Asset) O->SetStringField(TEXT("asset"), Asset->GetPathName());
    return O;
}
JArray Numbers(std::initializer_list<double> Values)
{
    JArray A; for (double N : Values) { if (FMath::IsFinite(N)) A.Add(MakeShared<FJsonValueNumber>(N)); else A.Add(MakeShared<FJsonValueNull>()); } return A;
}
template<typename V> JArray Vec(const V& P) { return Numbers({P.X,P.Y,P.Z}); }
void Number(const JObject& O, const TCHAR* Key, double N)
{
    if (FMath::IsFinite(N)) O->SetNumberField(Key,N); else O->SetField(Key,MakeShared<FJsonValueNull>());
}
FString BytesHash(const void* Data, uint64 Size)
{
    FSHA1 H;
    const uint8* P = static_cast<const uint8*>(Data);
    while (Size) { const uint32 N = uint32(FMath::Min<uint64>(Size,1u<<28)); H.Update(P,N); P+=N; Size-=N; }
    H.Final(); uint8 Digest[20]; H.GetHash(Digest); return BytesToHex(Digest,20).ToLower();
}
struct Stream
{
    FSHA1 Hash;
    void U32(uint32 N) { uint8 B[4] = {uint8(N),uint8(N>>8),uint8(N>>16),uint8(N>>24)}; Hash.Update(B,4); }
    void Float(float N) { uint32 B; FMemory::Memcpy(&B,&N,4); U32(B); }
    template<typename V> void Vector(const V& V3) { Float(V3.X); Float(V3.Y); Float(V3.Z); }
    FString End() { Hash.Final(); uint8 B[20]; Hash.GetHash(B); return BytesToHex(B,20).ToLower(); }
};
JArray Rig(const FReferenceSkeleton& R)
{
    JArray A;
    for (int32 I=0;I<R.GetNum();++I)
    {
        JObject B=Object(); const FTransform& T=R.GetRefBonePose()[I]; const FQuat Q=T.GetRotation();
        B->SetNumberField(TEXT("index"),I); B->SetStringField(TEXT("name"),R.GetBoneName(I).ToString());
        const int32 Parent=R.GetParentIndex(I); B->SetNumberField(TEXT("parent"),Parent);
        B->SetStringField(TEXT("parent_name"),Parent>=0?R.GetBoneName(Parent).ToString():FString());
        B->SetArrayField(TEXT("translation_cm"),Vec(T.GetTranslation())); B->SetArrayField(TEXT("scale"),Vec(T.GetScale3D()));
        B->SetArrayField(TEXT("rotation_xyzw"),Numbers({Q.X,Q.Y,Q.Z,Q.W})); A.Add(Value(B));
    }
    return A;
}
int32 Material(const USkeletalMesh* Mesh,int32 LOD,int32 SectionIndex,int32 Raw)
{
    const FSkeletalMeshLODInfo* Info=Mesh->GetLODInfo(LOD);
    return Info && Info->LODMaterialMap.IsValidIndex(SectionIndex) && Mesh->GetMaterials().IsValidIndex(Info->LODMaterialMap[SectionIndex]) ? Info->LODMaterialMap[SectionIndex] : Raw;
}
JObject Section(const USkeletalMesh* Mesh,int32 LOD,int32 Index,int32 Raw,uint32 BaseVertex,uint32 Count,uint32 BaseIndex,uint32 Triangles,TConstArrayView<FBoneIndexType> BoneMap)
{
    JObject O=Object(); O->SetNumberField(TEXT("section"),Index); O->SetNumberField(TEXT("material_index"),Raw);
    O->SetNumberField(TEXT("resolved_material_index"),Material(Mesh,LOD,Index,Raw));
    O->SetNumberField(TEXT("base_vertex"),BaseVertex); O->SetNumberField(TEXT("vertices"),Count);
    O->SetNumberField(TEXT("base_index"),BaseIndex); O->SetNumberField(TEXT("triangles"),Triangles);
    JArray Bones; for (FBoneIndexType I:BoneMap) Bones.Add(MakeShared<FJsonValueNumber>(I));
    O->SetArrayField(TEXT("bone_map"),Bones); return O;
}
struct Vertex
{
    FVector3f Position,TangentX,TangentY,Normal;
    TArray<FVector2f> UVs;
    TArray<TPair<int32,uint16>> Weights;
    bool bValidBoneMap=true;
};
struct Scan
{
    Stream Geometry,Weights;
    int32 Count=0,NonFinite=0,ZeroNormals=0,NegativeZNormals=0,MaxInfluences=0,InvalidBoneMaps=0;
    uint32 MinWeightSum=MAX_uint32,MaxWeightSum=0;
    JArray Samples;
    void Add(uint32 Index,const Vertex& V,const TArray<int32>& Requested)
    {
        ++Count; bool Finite= !V.Position.ContainsNaN() && !V.TangentX.ContainsNaN() && !V.TangentY.ContainsNaN() && !V.Normal.ContainsNaN();
        for (const FVector2f& UV:V.UVs) Finite &= !UV.ContainsNaN();
        NonFinite+=!Finite; ZeroNormals+=V.Normal.SizeSquared()<1.e-12f; NegativeZNormals+=V.Normal.Z<0;
        InvalidBoneMaps+=!V.bValidBoneMap; MaxInfluences=FMath::Max(MaxInfluences,V.Weights.Num());
        Geometry.U32(Index); Geometry.Vector(V.Position); Geometry.Vector(V.TangentX); Geometry.Vector(V.TangentY); Geometry.Vector(V.Normal);
        Geometry.U32(V.UVs.Num()); for (const FVector2f& UV:V.UVs) { Geometry.Float(UV.X); Geometry.Float(UV.Y); }
        uint32 Sum=0; Weights.U32(Index); Weights.U32(V.Weights.Num());
        for (const auto& W:V.Weights) { Weights.U32(W.Key); Weights.U32(W.Value); Sum+=W.Value; }
        MinWeightSum=FMath::Min(MinWeightSum,Sum); MaxWeightSum=FMath::Max(MaxWeightSum,Sum);
        if (!Requested.Contains(Index)) return;
        JObject S=Object(); S->SetNumberField(TEXT("vertex"),Index); S->SetArrayField(TEXT("position_cm"),Vec(V.Position));
        S->SetArrayField(TEXT("tangent_x"),Vec(V.TangentX)); S->SetArrayField(TEXT("tangent_y"),Vec(V.TangentY)); S->SetArrayField(TEXT("normal"),Vec(V.Normal));
        JArray UVs,Influences;
        for (const FVector2f& UV:V.UVs) UVs.Add(MakeShared<FJsonValueArray>(Numbers({UV.X,UV.Y})));
        for (const auto& W:V.Weights) { JObject I=Object(); I->SetNumberField(TEXT("mesh_bone"),W.Key); I->SetNumberField(TEXT("weight_u16"),W.Value); I->SetNumberField(TEXT("weight"),double(W.Value)/65535.0); Influences.Add(Value(I)); }
        S->SetArrayField(TEXT("uvs"),UVs); S->SetArrayField(TEXT("influences"),Influences); S->SetBoolField(TEXT("bone_map_valid"),V.bValidBoneMap); Samples.Add(Value(S));
    }
    void Finish(const JObject& O)
    {
        O->SetStringField(TEXT("state"),InvalidBoneMaps?TEXT("invalid_bone_map"):TEXT("available")); O->SetNumberField(TEXT("vertices_scanned"),Count);
        O->SetStringField(TEXT("geometry_sha1"),Geometry.End()); O->SetStringField(TEXT("weights_sha1"),Weights.End());
        O->SetNumberField(TEXT("nonfinite_vertices"),NonFinite); O->SetNumberField(TEXT("zero_normals"),ZeroNormals);
        O->SetNumberField(TEXT("negative_z_normals"),NegativeZNormals); O->SetNumberField(TEXT("max_nonzero_influences"),MaxInfluences);
        O->SetNumberField(TEXT("invalid_bone_map_vertices"),InvalidBoneMaps); O->SetNumberField(TEXT("min_weight_sum_u16"),Count?MinWeightSum:0);
        O->SetNumberField(TEXT("max_weight_sum_u16"),MaxWeightSum); O->SetArrayField(TEXT("samples"),Samples);
    }
};
void Weights(Vertex& V,TConstArrayView<FBoneIndexType> Map,const FReferenceSkeleton& Rig,int32 Local,uint16 Weight)
{
    if (!Weight) return;
    const int32 Bone=Map.IsValidIndex(Local)?int32(Map[Local]):INDEX_NONE;
    V.bValidBoneMap &= Bone>=0 && Bone<Rig.GetNum(); V.Weights.Emplace(Bone,Weight);
}
}

FString UDinkHeroInspectionLibrary::InspectSkeletonReference(USkeleton* Skeleton)
{
    using namespace DinkHeroInspect;
    JObject O=Start(TEXT("dink-skeleton-reference/1"),Skeleton);
    if (!Skeleton) return Json(O);
    O->SetArrayField(TEXT("bones"),Rig(Skeleton->GetReferenceSkeleton()));
    JArray Virtual;
    for (const FVirtualBone& B:Skeleton->GetVirtualBones())
    {
        JObject V=Object(); V->SetStringField(TEXT("name"),B.VirtualBoneName.ToString());
        V->SetStringField(TEXT("source"),B.SourceBoneName.ToString()); V->SetStringField(TEXT("target"),B.TargetBoneName.ToString()); Virtual.Add(Value(V));
    }
    O->SetArrayField(TEXT("virtual_bones"),Virtual); return Json(O);
}

FString UDinkHeroInspectionLibrary::InspectSkeletalMeshLod(USkeletalMesh* Mesh,int32 LODIndex,const TArray<int32>& SampleVertices)
{
    using namespace DinkHeroInspect;
    JObject O=Start(TEXT("dink-skeletal-lod/1"),Mesh); O->SetNumberField(TEXT("lod"),LODIndex);
    if (!Mesh) return Json(O);
    if (SampleVertices.Num()>64 || SampleVertices.ContainsByPredicate([](int32 I){return I<0;}) || LODIndex<0)
    { O->SetStringField(TEXT("state"),TEXT("invalid_request")); return Json(O); }
    if (Mesh->IsCompiling()) { O->SetStringField(TEXT("state"),TEXT("compiling_unavailable")); return Json(O); }
    O->SetStringField(TEXT("skeleton"),GetPathNameSafe(Mesh->GetSkeleton())); O->SetStringField(TEXT("physics_asset"),GetPathNameSafe(Mesh->GetPhysicsAsset()));
    O->SetArrayField(TEXT("mesh_bones"),Rig(Mesh->GetRefSkeleton()));
    O->SetStringField(TEXT("hash_encoding"),TEXT("SHA1; ordered LEuint32/IEEEfloat32; geometry(index,position,TX,TY,N,UVcount,UVs); weights(index,count,meshBone,u16weight asuint32)"));
    JArray Materials;
    for (const FSkeletalMaterial& M:Mesh->GetMaterials())
    {
        JObject S=Object(); S->SetStringField(TEXT("slot"),M.MaterialSlotName.ToString()); S->SetStringField(TEXT("imported_slot"),M.ImportedMaterialSlotName.ToString());
        S->SetStringField(TEXT("material"),GetPathNameSafe(M.MaterialInterface)); Materials.Add(Value(S));
    }
    O->SetArrayField(TEXT("materials"),Materials);
    if (const UAssetImportData* Import=Mesh->GetAssetImportData())
    {
        JObject I=Object(); I->SetStringField(TEXT("class"),Import->GetClass()->GetPathName());
        TArray<FString> Names; Import->ExtractFilenames(Names); JArray Files; for (const FString& N:Names) Files.Add(MakeShared<FJsonValueString>(N)); I->SetArrayField(TEXT("resolved_files"),Files);
        // Read all reflected scalar import options, including inherited FBX mesh settings.
        JObject Options=Object();
        for (TFieldIterator<FProperty> P(Import->GetClass());P;++P)
        {
            if (const FBoolProperty* B=CastField<FBoolProperty>(*P)) Options->SetBoolField(P->GetName(),B->GetPropertyValue_InContainer(Import));
            else if (const FNumericProperty* N=CastField<FNumericProperty>(*P))
            {
                const void* Address=N->ContainerPtrToValuePtr<void>(Import);
                if (N->IsFloatingPoint()) Number(Options,*P->GetName(),N->GetFloatingPointPropertyValue(Address));
                else if (N->IsInteger()) Options->SetNumberField(P->GetName(),double(N->GetSignedIntPropertyValue(Address)));
            }
            else if (const FEnumProperty* Enum=CastField<FEnumProperty>(*P)) Options->SetNumberField(P->GetName(),double(Enum->GetUnderlyingProperty()->GetSignedIntPropertyValue(Enum->ContainerPtrToValuePtr<void>(Import))));
        }
        I->SetObjectField(TEXT("scalar_options"),Options); O->SetObjectField(TEXT("import_data"),I);
    }
    if (const FSkeletalMeshLODInfo* L=Mesh->GetLODInfo(LODIndex))
    {
        JObject B=Object(); const FSkeletalMeshBuildSettings& S=L->BuildSettings;
        B->SetBoolField(TEXT("recompute_normals"),S.bRecomputeNormals); B->SetBoolField(TEXT("recompute_tangents"),S.bRecomputeTangents);
        B->SetBoolField(TEXT("mikk_tspace"),S.bUseMikkTSpace); B->SetBoolField(TEXT("weighted_normals"),S.bComputeWeightedNormals);
        B->SetBoolField(TEXT("remove_degenerates"),S.bRemoveDegenerates); B->SetBoolField(TEXT("full_precision_uvs"),S.bUseFullPrecisionUVs);
        B->SetBoolField(TEXT("high_precision_tangents"),S.bUseHighPrecisionTangentBasis); B->SetBoolField(TEXT("high_precision_weights"),S.bUseHighPrecisionSkinWeights);
        B->SetNumberField(TEXT("bone_influence_limit"),S.BoneInfluenceLimit); Number(B,TEXT("threshold_position"),S.ThresholdPosition);
        Number(B,TEXT("threshold_normal"),S.ThresholdTangentNormal); Number(B,TEXT("threshold_uv"),S.ThresholdUV);
        JArray Map; for (int32 M:L->LODMaterialMap) Map.Add(MakeShared<FJsonValueNumber>(M)); B->SetArrayField(TEXT("lod_material_map"),Map); O->SetObjectField(TEXT("build"),B);
    }
    JObject Source=Object(); Source->SetStringField(TEXT("state"),TEXT("missing_lod_unavailable"));
    const FSkeletalMeshModel* Model=Mesh->GetImportedModel(); O->SetNumberField(TEXT("source_lods"),Model?Model->LODModels.Num():0);
    if (Model && Model->LODModels.IsValidIndex(LODIndex))
    {
        const FSkeletalMeshLODModel& L=Model->LODModels[LODIndex]; JArray Sections; Scan S; Stream Indices;
        for (int32 SI=0;SI<L.Sections.Num();++SI)
        {
            const FSkelMeshSection& Section=L.Sections[SI];
            Sections.Add(Value(DinkHeroInspect::Section(Mesh,LODIndex,SI,Section.MaterialIndex,Section.BaseVertexIndex,Section.NumVertices,Section.BaseIndex,Section.NumTriangles,Section.BoneMap)));
            for (int32 VI=0;VI<Section.SoftVertices.Num();++VI)
            {
                const FSoftSkinVertex& X=Section.SoftVertices[VI]; Vertex V; V.Position=X.Position; V.TangentX=X.TangentX; V.TangentY=X.TangentY; V.Normal=FVector3f(X.TangentZ.X,X.TangentZ.Y,X.TangentZ.Z);
                for (uint32 UV=0;UV<FMath::Min<uint32>(L.NumTexCoords,MAX_TEXCOORDS);++UV) V.UVs.Add(X.UVs[UV]);
                for (int32 W=0;W<MAX_TOTAL_INFLUENCES;++W) Weights(V,Section.BoneMap,Mesh->GetRefSkeleton(),X.InfluenceBones[W],X.InfluenceWeights[W]);
                S.Add(Section.BaseVertexIndex+VI,V,SampleVertices);
            }
        }
        for (uint32 I:L.IndexBuffer) Indices.U32(I);
        S.Finish(Source); Source->SetNumberField(TEXT("declared_vertices"),L.NumVertices); Source->SetNumberField(TEXT("indices"),L.IndexBuffer.Num());
        Source->SetNumberField(TEXT("uv_channels"),L.NumTexCoords); Source->SetStringField(TEXT("indices_sha1"),Indices.End()); Source->SetArrayField(TEXT("sections"),Sections);
        if (S.Count!=int32(L.NumVertices)) Source->SetStringField(TEXT("state"),TEXT("source_vertices_incomplete"));
    }
    O->SetObjectField(TEXT("source"),Source);
    JObject Built=Object(); Built->SetStringField(TEXT("state"),TEXT("missing_lod_unavailable"));
    const FSkeletalMeshRenderData* Render=Mesh->GetResourceForRendering(); O->SetNumberField(TEXT("built_lods"),Render?Render->LODRenderData.Num():0);
    if (Render && Render->LODRenderData.IsValidIndex(LODIndex))
    {
        const FSkeletalMeshLODRenderData& L=Render->LODRenderData[LODIndex]; const auto& Pos=L.StaticVertexBuffers.PositionVertexBuffer; const auto& Tangent=L.StaticVertexBuffers.StaticMeshVertexBuffer;
        const FSkinWeightVertexBuffer* W=L.GetSkinWeightVertexBuffer(); const auto* Index=L.MultiSizeIndexContainer.GetIndexBuffer();
        Built->SetBoolField(TEXT("weight_profile_override"),W!=&L.SkinWeightVertexBuffer);
        const bool Ready=Pos.GetVertexData() && Tangent.GetTangentData() && Tangent.GetTexCoordData() && W && W->GetDataVertexBuffer()->GetWeightData() && (!W->GetVariableBonesPerVertex() || W->GetLookupVertexBuffer()->GetLookupData()) && Index && Index->GetResourceDataSize()>0 && Pos.GetNumVertices()==Tangent.GetNumVertices() && Pos.GetNumVertices()==W->GetNumVertices();
        Built->SetStringField(TEXT("state"),TEXT("cpu_buffers_unavailable"));
        if (Ready)
        {
            JArray Sections; Scan S; Stream Indices;
            for (int32 SI=0;SI<L.RenderSections.Num();++SI)
            {
                const FSkelMeshRenderSection& Sec=L.RenderSections[SI]; const TConstArrayView<FBoneIndexType> Map=Sec.HasUnifiedBoneMap()?L.UnifiedBoneMap:TConstArrayView<FBoneIndexType>(Sec.BoneMap);
                JObject SO=Section(Mesh,LODIndex,SI,Sec.MaterialIndex,Sec.BaseVertexIndex,Sec.GetNumVertices(),Sec.BaseIndex,Sec.NumTriangles,Map); SO->SetBoolField(TEXT("unified_bone_map"),Sec.HasUnifiedBoneMap()); Sections.Add(Value(SO));
                for (int32 J=0;J<Sec.GetNumVertices();++J)
                {
                    const uint32 VI=Sec.BaseVertexIndex+J;
                    if (VI>=Pos.GetNumVertices()) { Built->SetStringField(TEXT("state"),TEXT("invalid_section_range")); O->SetObjectField(TEXT("built"),Built); return Json(O); }
                    Vertex V; V.Position=Pos.VertexPosition(VI); V.TangentX=FVector3f(Tangent.VertexTangentX(VI)); V.TangentY=FVector3f(Tangent.VertexTangentY(VI)); V.Normal=FVector3f(Tangent.VertexTangentZ(VI));
                    for (uint32 U=0;U<Tangent.GetNumTexCoords();++U) V.UVs.Add(Tangent.GetVertexUV(VI,U));
                    const FSkinWeightInfo Info=W->GetVertexSkinWeights(VI);
                    for (int32 K=0;K<MAX_TOTAL_INFLUENCES;++K) Weights(V,Map,Mesh->GetRefSkeleton(),Info.InfluenceBones[K],Info.InfluenceWeights[K]);
                    S.Add(VI,V,SampleVertices);
                }
            }
            for (int32 I=0;I<Index->Num();++I) Indices.U32(Index->Get(I));
            S.Finish(Built); Built->SetNumberField(TEXT("indices"),Index->Num()); Built->SetStringField(TEXT("indices_sha1"),Indices.End()); Built->SetArrayField(TEXT("sections"),Sections);
            Built->SetNumberField(TEXT("uv_channels"),Tangent.GetNumTexCoords()); Built->SetNumberField(TEXT("weight_bytes"),W->GetBoneWeightByteSize());
            if (S.Count!=int32(Pos.GetNumVertices())) Built->SetStringField(TEXT("state"),TEXT("section_vertices_incomplete"));
        }
    }
    O->SetObjectField(TEXT("built"),Built); O->SetStringField(TEXT("state"),TEXT("inspected")); return Json(O);
}

FString UDinkHeroInspectionLibrary::InspectTexturePixels(UTexture2D* Texture,const TArray<FIntPoint>& Pixels)
{
    using namespace DinkHeroInspect;
    JObject O=Start(TEXT("dink-texture-pixels/1"),Texture); if (!Texture) return Json(O);
    if (Pixels.Num()>64 || Pixels.ContainsByPredicate([](const FIntPoint& P){return P.X<0||P.Y<0;})) { O->SetStringField(TEXT("state"),TEXT("invalid_request")); return Json(O); }
    if (Texture->IsCompiling()) { O->SetStringField(TEXT("state"),TEXT("compiling_unavailable")); return Json(O); }
    O->SetBoolField(TEXT("srgb"),Texture->SRGB); O->SetNumberField(TEXT("compression"),Texture->CompressionSettings);
    O->SetBoolField(TEXT("flip_green"),Texture->bFlipGreenChannel);
    JObject Source=Object(); Source->SetStringField(TEXT("state"),TEXT("source_unavailable"));
    Source->SetNumberField(TEXT("format"),Texture->Source.GetFormat()); Source->SetNumberField(TEXT("mips"),Texture->Source.GetNumMips());
    FImage Image;
    if (Texture->Source.IsValid() && Texture->Source.GetMipImage(Image,0))
    {
        Source->SetNumberField(TEXT("width"),Image.SizeX); Source->SetNumberField(TEXT("height"),Image.SizeY); Source->SetNumberField(TEXT("image_format"),Image.Format);
        Source->SetStringField(TEXT("mip0_bytes_sha1"),BytesHash(Image.RawData.GetData(),Image.RawData.Num())); JArray Samples;
        bool All=true;
        for (const FIntPoint& P:Pixels)
        {
            JObject S=Object(); S->SetArrayField(TEXT("xy"),Numbers({double(P.X),double(P.Y)}));
            if (P.X>=Image.SizeX || P.Y>=Image.SizeY) { S->SetStringField(TEXT("state"),TEXT("out_of_bounds")); All=false; }
            else
            {
                const FLinearColor C=ERawImageFormat::GetOnePixelLinear(Image.GetPixelPointer(P.X,P.Y),Image.Format,EGammaSpace::Linear);
                S->SetArrayField(TEXT("stored_rgba"),Numbers({C.R,C.G,C.B,C.A})); const FVector N=FVector(2*C.R-1,1-2*C.G,2*C.B-1).GetSafeNormal(); S->SetArrayField(TEXT("explicit_rgb_normal_decode"),Vec(N));
            }
            Samples.Add(Value(S));
        }
        Source->SetArrayField(TEXT("samples"),Samples); Source->SetStringField(TEXT("state"),All?TEXT("available"):TEXT("sample_out_of_bounds"));
    }
    O->SetObjectField(TEXT("source"),Source);
    JObject Platform=Object(); Platform->SetStringField(TEXT("state"),TEXT("platform_unavailable"));
    const FTexturePlatformData* Data=Texture->GetPlatformData();
    if (Data)
    {
        const EPixelFormat Format=Data->PixelFormat; Platform->SetNumberField(TEXT("pixel_format"),Format); Platform->SetStringField(TEXT("pixel_format_name"),GPixelFormats[Format].Name);
        JArray Mips; for (const FTexture2DMipMap& M:Data->Mips) { JObject MI=Object(); MI->SetNumberField(TEXT("width"),M.SizeX); MI->SetNumberField(TEXT("height"),M.SizeY); MI->SetNumberField(TEXT("bulk_bytes"),M.BulkData.GetBulkDataSize()); Mips.Add(Value(MI)); } Platform->SetArrayField(TEXT("mips"),Mips);
        if (Data->Mips.Num()>0)
        {
            const FTexture2DMipMap& M=Data->Mips[0]; const void* Bytes=M.BulkData.LockReadOnly();
            if (Bytes)
            {
                Platform->SetStringField(TEXT("mip0_bytes_sha1"),BytesHash(Bytes,M.BulkData.GetBulkDataSize())); JArray Samples; const bool Supported=Format==PF_A32B32G32R32F || Format==PF_FloatRGBA || Format==PF_B8G8R8A8 || Format==PF_R8G8B8A8;
                Platform->SetStringField(TEXT("state"),Supported?TEXT("available"):TEXT("pixel_decode_unsupported"));
                const int32 Stride=Format==PF_A32B32G32R32F?16:Format==PF_FloatRGBA?8:4;
                for (const FIntPoint& P:Pixels)
                {
                    JObject S=Object(); S->SetArrayField(TEXT("xy"),Numbers({double(P.X),double(P.Y)})); const int64 Offset=(int64(P.Y)*M.SizeX+P.X)*Stride;
                    if (P.X>=M.SizeX || P.Y>=M.SizeY || Offset+Stride>M.BulkData.GetBulkDataSize()) S->SetStringField(TEXT("state"),TEXT("out_of_bounds"));
                    else if (!Supported) S->SetStringField(TEXT("state"),TEXT("pixel_decode_unsupported"));
                    else
                    {
                        const uint8* B=static_cast<const uint8*>(Bytes)+Offset; FLinearColor C;
                        if (Format==PF_A32B32G32R32F) FMemory::Memcpy(&C,B,16);
                        else if (Format==PF_FloatRGBA) { FFloat16Color H; FMemory::Memcpy(&H,B,8); C=H.GetFloats(); }
                        else if (Format==PF_B8G8R8A8) C=FLinearColor(B[2]/255.f,B[1]/255.f,B[0]/255.f,B[3]/255.f);
                        else C=FLinearColor(B[0]/255.f,B[1]/255.f,B[2]/255.f,B[3]/255.f);
                        S->SetArrayField(TEXT("stored_rgba"),Numbers({C.R,C.G,C.B,C.A})); S->SetArrayField(TEXT("explicit_rgb_normal_decode"),Vec(FVector(2*C.R-1,1-2*C.G,2*C.B-1).GetSafeNormal()));
                    }
                    Samples.Add(Value(S));
                }
                Platform->SetArrayField(TEXT("samples"),Samples);
            }
            M.BulkData.Unlock();
        }
    }
    O->SetObjectField(TEXT("platform"),Platform); return Json(O);
}
