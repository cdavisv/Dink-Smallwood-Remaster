#include "DinkMaterialArtLibrary.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "Materials/MaterialInterface.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include <initializer_list>

namespace
{
using FValues = TArray<TSharedPtr<FJsonValue>>;
FValues Numbers(std::initializer_list<double> Values)
{
 FValues Result;Result.Reserve(static_cast<int32>(Values.size()));
 for (double Value : Values) Result.Add(MakeShared<FJsonValueNumber>(Value));
 return Result;
}
void Number(FValues& Values,double Value) { Values.Add(MakeShared<FJsonValueNumber>(Value)); }
bool Finite(const FValues& Values)
{
 for (const auto& Value : Values) if (!FMath::IsFinite(Value->AsNumber())) return false;
 return true;
}
}

FString UDinkMaterialArtLibrary::InspectStaticMeshGeometry(UStaticMesh* Mesh,int32 LODIndex)
{
 TSharedRef<FJsonObject> Root=MakeShared<FJsonObject>();
 Root->SetStringField(TEXT("schema"),TEXT("dink-static-mesh-geometry/1"));
 Root->SetBoolField(TEXT("valid"),false);Root->SetNumberField(TEXT("lod"),LODIndex);
 auto Finish=[&Root](const TCHAR* Error=nullptr)
 {
  if (Error) Root->SetStringField(TEXT("error"),Error);
  FString Result;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Result));return Result;
 };
 if (!Mesh) return Finish(TEXT("null_mesh"));
 Root->SetStringField(TEXT("mesh"),Mesh->GetPathName());
 if (LODIndex<0||LODIndex>=Mesh->GetNumSourceModels()) return Finish(TEXT("invalid_lod"));
 const FMeshDescription* Description=Mesh->GetMeshDescription(LODIndex);
 if (!Description) return Finish(TEXT("missing_raw_mesh_description"));
 const FStaticMeshRenderData* Render=Mesh->GetRenderData();
 if (!Render||!Render->LODResources.IsValidIndex(LODIndex)) return Finish(TEXT("missing_built_lod"));
 const FStaticMeshLODResources& LOD=Render->LODResources[LODIndex];
 const auto& Position=LOD.VertexBuffers.PositionVertexBuffer;
 const auto& Vertex=LOD.VertexBuffers.StaticMeshVertexBuffer;
 const auto& Color=LOD.VertexBuffers.ColorVertexBuffer;
 if (!Mesh->bAllowCPUAccess||!Position.GetAllowCPUAccess()||!Vertex.GetAllowCPUAccess()||!LOD.IndexBuffer.GetAllowCPUAccess()) return Finish(TEXT("cpu_buffers_not_retained"));
 if (!Position.GetVertexData()||LOD.IndexBuffer.GetNumIndices()==0||LOD.IndexBuffer.GetIndexDataSize()==0) return Finish(TEXT("missing_cpu_buffer_data"));
 const uint32 Count=Position.GetNumVertices();
 if (Count==0||Vertex.GetNumVertices()!=Count||Vertex.GetNumTexCoords()==0) return Finish(TEXT("incomplete_built_attributes"));
 if (Color.GetNumVertices()!=0&&(Color.GetNumVertices()!=Count||!Color.GetAllowCPUAccess())) return Finish(TEXT("incomplete_built_colors"));
 const FStaticMeshConstAttributes Attributes(*Description);
 const auto P=Attributes.GetVertexPositions();const auto N=Attributes.GetVertexInstanceNormals();
 const auto T=Attributes.GetVertexInstanceTangents();const auto S=Attributes.GetVertexInstanceBinormalSigns();
 const auto C=Attributes.GetVertexInstanceColors();const auto UV=Attributes.GetVertexInstanceUVs();
 const auto Names=Attributes.GetPolygonGroupMaterialSlotNames();
 if (!P.IsValid()||!N.IsValid()||!T.IsValid()||!S.IsValid()||!C.IsValid()||!UV.IsValid()||!Names.IsValid()||UV.GetNumChannels()==0) return Finish(TEXT("incomplete_raw_attributes"));
 TMap<FName,int32> NamedSlots;FValues Slots;
 const auto& Materials=Mesh->GetStaticMaterials();
 for (int32 Index=0;Index<Materials.Num();++Index)
 {
  const auto& Material=Materials[Index];const FName Imported=Material.ImportedMaterialSlotName;
  if (Imported.IsNone()||NamedSlots.Contains(Imported)) return Finish(TEXT("ambiguous_imported_material_slot"));
  NamedSlots.Add(Imported,Index);TSharedRef<FJsonObject> Row=MakeShared<FJsonObject>();
  Row->SetNumberField(TEXT("slot"),Index);Row->SetStringField(TEXT("imported_name"),Imported.ToString());
  Row->SetStringField(TEXT("material_path"),Material.MaterialInterface?Material.MaterialInterface->GetPathName():FString());Slots.Add(MakeShared<FJsonValueObject>(Row));
 }
 TSharedRef<FJsonObject> Raw=MakeShared<FJsonObject>();FValues Instances,Triangles,ExpectedBuiltColors;
 Raw->SetStringField(TEXT("instance_layout"),TEXT("id,p_xyz,n_xyz,t_xyz,binormal_sign,color0_linear_rgba,all_uv_pairs"));
 Raw->SetNumberField(TEXT("uv_channels"),UV.GetNumChannels());
 Instances.Reserve(Description->VertexInstances().Num());
 for (const FVertexInstanceID Instance : Description->VertexInstances().GetElementIDs())
 {
  const FVector3f V=P[Description->GetVertexInstanceVertex(Instance)],Normal=N[Instance],Tangent=T[Instance];const FVector4f Tint=C[Instance];
  FValues Row=Numbers({double(Instance.GetValue()),V.X,V.Y,V.Z,Normal.X,Normal.Y,Normal.Z,Tangent.X,Tangent.Y,Tangent.Z,S[Instance],Tint.X,Tint.Y,Tint.Z,Tint.W});
  for (int32 Channel=0;Channel<UV.GetNumChannels();++Channel) { const FVector2f Value=UV.Get(Instance,Channel);Number(Row,Value.X);Number(Row,Value.Y); }
  if (!Finite(Row)) return Finish(TEXT("nonfinite_raw_attribute"));
  const FColor Encoded=FLinearColor(Tint).ToFColor(true);
  ExpectedBuiltColors.Add(MakeShared<FJsonValueArray>(Numbers({double(Instance.GetValue()),double(Encoded.R),double(Encoded.G),double(Encoded.B),double(Encoded.A)})));
  Instances.Add(MakeShared<FJsonValueArray>(Row));
 }
 for (const FTriangleID Triangle : Description->Triangles().GetElementIDs())
 {
  const auto Corners=Description->GetTriangleVertexInstances(Triangle);
  const int32* Slot=NamedSlots.Find(Names[Description->GetTrianglePolygonGroup(Triangle)]);
  if (!Slot||Corners.Num()!=3) return Finish(TEXT("unresolved_raw_triangle_slot"));
  Triangles.Add(MakeShared<FJsonValueArray>(Numbers({double(Corners[0].GetValue()),double(Corners[1].GetValue()),double(Corners[2].GetValue()),double(*Slot)})));
 }
 Raw->SetArrayField(TEXT("instances"),Instances);Raw->SetArrayField(TEXT("triangles"),Triangles);
 Raw->SetArrayField(TEXT("expected_built_color_rgba8"),ExpectedBuiltColors);
 TSharedRef<FJsonObject> Built=MakeShared<FJsonObject>();FValues Vertices,Indices,Sections;
 Built->SetStringField(TEXT("vertex_layout"),TEXT("p_xyz,n_xyz,t_xyz,b_xyz,stored_tangentZ_w,color0_rgba8,all_uv_pairs"));
 Built->SetNumberField(TEXT("uv_channels"),Vertex.GetNumTexCoords());
 Built->SetBoolField(TEXT("color0_present"),Color.GetNumVertices()==Count);
 Built->SetBoolField(TEXT("high_precision_tangent_basis"),Vertex.GetUseHighPrecisionTangentBasis());
 Built->SetBoolField(TEXT("full_precision_uvs"),Vertex.GetUseFullPrecisionUVs());
 Vertices.Reserve(Count);
 for (uint32 Index=0;Index<Count;++Index)
 {
  const FVector3f V=Position.VertexPosition(Index),Y=Vertex.VertexTangentY(Index);const FVector4f X=Vertex.VertexTangentX(Index);
  const FVector4f Z=Vertex.VertexTangentZ(Index);const FColor Tint=Color.GetNumVertices()?Color.VertexColor(Index):FColor::White;
  FValues Row=Numbers({V.X,V.Y,V.Z,Z.X,Z.Y,Z.Z,X.X,X.Y,X.Z,Y.X,Y.Y,Y.Z,Z.W,double(Tint.R),double(Tint.G),double(Tint.B),double(Tint.A)});
  for (uint32 Channel=0;Channel<Vertex.GetNumTexCoords();++Channel) { const FVector2f Value=Vertex.GetVertexUV(Index,Channel);Number(Row,Value.X);Number(Row,Value.Y); }
  if (!Finite(Row)) return Finish(TEXT("nonfinite_built_attribute"));
  Vertices.Add(MakeShared<FJsonValueArray>(Row));
 }
 Indices.Reserve(LOD.IndexBuffer.GetNumIndices());
 for (int32 Index=0;Index<LOD.IndexBuffer.GetNumIndices();++Index)
 {
  const uint32 Value=LOD.IndexBuffer.GetIndex(Index);if (Value>=Count) return Finish(TEXT("invalid_built_index"));Number(Indices,Value);
 }
 for (const FStaticMeshSection& Section : LOD.Sections)
 {
  if (!Materials.IsValidIndex(Section.MaterialIndex)||uint64(Section.FirstIndex)+uint64(Section.NumTriangles)*3>uint64(LOD.IndexBuffer.GetNumIndices())) return Finish(TEXT("invalid_built_section"));
  TSharedRef<FJsonObject> Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("first_index"),Section.FirstIndex);Row->SetNumberField(TEXT("triangles"),Section.NumTriangles);Row->SetNumberField(TEXT("slot"),Section.MaterialIndex);Sections.Add(MakeShared<FJsonValueObject>(Row));
 }
 Built->SetArrayField(TEXT("vertices"),Vertices);Built->SetArrayField(TEXT("indices"),Indices);Built->SetArrayField(TEXT("sections"),Sections);
 Root->SetArrayField(TEXT("slots"),Slots);Root->SetObjectField(TEXT("raw"),Raw);Root->SetObjectField(TEXT("built"),Built);Root->SetBoolField(TEXT("valid"),true);
 return Finish();
}

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkStaticMeshGeometryInspectionTest,"Dink.Art.StaticMeshGeometryInspection",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FDinkStaticMeshGeometryInspectionTest::RunTest(const FString& Parameters)
{
 auto Parse=[](const FString& Text) { TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data);return Data; };
 const auto Null=Parse(UDinkMaterialArtLibrary::InspectStaticMeshGeometry(nullptr));
 if (!TestTrue(TEXT("null rejected"),Null.IsValid()&&!Null->GetBoolField(TEXT("valid")))) return false;
 UStaticMesh* Mesh=NewObject<UStaticMesh>(GetTransientPackage(),NAME_None,RF_Transient);Mesh->AddSourceModel();Mesh->bAllowCPUAccess=true;
 Mesh->GetStaticMaterials().Add(FStaticMaterial(nullptr,TEXT("PublicName"),TEXT("ImportedFixture")));
 FMeshDescription Fixture;FMeshDescription* Description=&Fixture;FStaticMeshAttributes Attributes(*Description);Attributes.Register();
 auto UV=Attributes.GetVertexInstanceUVs();UV.SetNumChannels(2);const auto Group=Description->CreatePolygonGroup();Attributes.GetPolygonGroupMaterialSlotNames()[Group]=TEXT("ImportedFixture");
 TArray<FVertexInstanceID> Corners;
 for (int32 Index=0;Index<3;++Index)
 {
  const auto Vertex=Description->CreateVertex();Attributes.GetVertexPositions()[Vertex]=FVector3f(Index==1?10.f:0.f,Index==2?10.f:0.f,0.f);
  const auto Instance=Description->CreateVertexInstance(Vertex);Corners.Add(Instance);Attributes.GetVertexInstanceNormals()[Instance]=FVector3f(0,0,1);Attributes.GetVertexInstanceTangents()[Instance]=FVector3f(1,0,0);Attributes.GetVertexInstanceBinormalSigns()[Instance]=1.f;Attributes.GetVertexInstanceColors()[Instance]=FVector4f(.2f,.4f,.6f,.8f);
  UV.Set(Instance,0,FVector2f(Index==1?1.f:0.f,Index==2?1.f:0.f));UV.Set(Instance,1,FVector2f(1.f,.99f));
 }
 Description->CreateTriangle(Group,Corners);
 // Exercise the ordinary Editor mesh builder used by imported candidates.
 // UV1 carries material selectors, so it must not become generated lightmap UVs.
 FMeshBuildSettings& Settings=Mesh->GetSourceModel(0).BuildSettings;
 Settings.bGenerateLightmapUVs=false;Settings.bRecomputeNormals=false;Settings.bRecomputeTangents=false;
 UStaticMesh::FBuildMeshDescriptionsParams Build;Build.bFastBuild=false;Build.bAllowCpuAccess=true;Build.bCommitMeshDescription=true;Build.bMarkPackageDirty=false;
 if (!TestTrue(TEXT("ordinary scratch mesh build succeeds"),Mesh->BuildFromMeshDescriptions({Description},Build))) return false;
 const bool Dirty=Mesh->GetOutermost()->IsDirty();
 const FString Before=UDinkMaterialArtLibrary::InspectStaticMeshGeometry(Mesh);const auto Result=Parse(Before);
 if (!TestTrue(TEXT("actual scratch mesh RAW+built snapshot valid"),Result.IsValid()&&Result->GetBoolField(TEXT("valid")))) return false;
 const auto Raw=Result->GetObjectField(TEXT("raw"));const auto Built=Result->GetObjectField(TEXT("built"));
 TestEqual(TEXT("raw two UV channels"),Raw->GetNumberField(TEXT("uv_channels")),2.0);TestEqual(TEXT("built two UV channels"),Built->GetNumberField(TEXT("uv_channels")),2.0);
 const auto& Row=Raw->GetArrayField(TEXT("instances"))[0]->AsArray();TestTrue(TEXT("raw linear color remains .2"),FMath::IsNearlyEqual(Row[11]->AsNumber(),.2,1.e-6));TestTrue(TEXT("raw UV1 semantic V retained"),FMath::IsNearlyEqual(Row[18]->AsNumber(),.99,1.e-6));
 const auto& BuiltRow=Built->GetArrayField(TEXT("vertices"))[0]->AsArray();
 TestEqual(TEXT("built raw color byte exact"),BuiltRow[13]->AsNumber(),double(Mesh->GetRenderData()->LODResources[0].VertexBuffers.ColorVertexBuffer.VertexColor(0).R));
 TestTrue(TEXT("stored TangentZ.W sign exposed"),BuiltRow[12]->AsNumber()>0.0);
 TestTrue(TEXT("built Color0 is exposed"),Built->GetBoolField(TEXT("color0_present")));TestEqual(TEXT("triangle index count"),Built->GetArrayField(TEXT("indices")).Num(),3);
 Result->SetBoolField(TEXT("valid"),false);TestEqual(TEXT("detached edits cannot affect source"),UDinkMaterialArtLibrary::InspectStaticMeshGeometry(Mesh),Before);TestEqual(TEXT("reader preserves dirty state"),Mesh->GetOutermost()->IsDirty(),Dirty);
 TestFalse(TEXT("invalid LOD refused"),Parse(UDinkMaterialArtLibrary::InspectStaticMeshGeometry(Mesh,9))->GetBoolField(TEXT("valid")));
 return true;
}
#endif
