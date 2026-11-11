#include "DinkTestHelpers.h"
#include "AssetCompilingManager.h"
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/BodySetup.h"
#include "StaticMeshResources.h"
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/EngineVersion.h"

namespace
{
FString TriangleRecord(const FVector3f& A,const FVector3f& B,const FVector3f& C,uint16 Material)
{
    const float Positions[9]={A.X,A.Y,A.Z,B.X,B.Y,B.Z,C.X,C.Y,C.Z};
    FString Hex;
    for(const uint8 Byte:TArrayView<const uint8>(reinterpret_cast<const uint8*>(Positions),sizeof(Positions)))
        Hex+=FString::Printf(TEXT("%02x"),Byte);
    for(const uint8 Byte:TArrayView<const uint8>(reinterpret_cast<const uint8*>(&Material),sizeof(Material)))
        Hex+=FString::Printf(TEXT("%02x"),Byte);
    return Hex;
}
void Add(TArray<TSharedPtr<FJsonValue>>& Rows,const FVector3f& A,const FVector3f& B,const FVector3f& C,uint16 Material)
{Rows.Add(MakeShared<FJsonValueString>(TriangleRecord(A,B,C,Material)));}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBarrelCookMetrology,"Dink.Art.Family.BarrelCookMetrology",DINK_TEST_FLAGS)
bool FDinkBarrelCookMetrology::RunTest(const FString&)
{
    for(const TCHAR* Path:{TEXT("/Game/Dink/Kits/Stonebrook/SM_Barrel_Oak_01.SM_Barrel_Oak_01"),
        TEXT("/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.SM_Barrel_Oak_01")})
    {
        auto* Mesh=LoadObject<UStaticMesh>(nullptr,Path);
        if(!TestNotNull(TEXT("actual saved barrel mesh loads"),Mesh))return false;
        FAssetCompilingManager::Get().FinishAllCompilation();
        auto* Body=Mesh->GetBodySetup();
        const auto* Render=Mesh->GetRenderData();
        const auto* Description=Mesh->GetMeshDescription(0);
        if(!TestTrue(TEXT("actual source/render/cooked geometry already available"),
            Body&&Render&&Description&&Body->bCreatedPhysicsMeshes&&Body->TriMeshGeometries.Num()==1&&Body->TriMeshGeometries[0]))return false;
        auto Report=MakeShared<FJsonObject>();
        Report->SetStringField(TEXT("mesh"),Mesh->GetPathName());
        Report->SetStringField(TEXT("engine_version"),FEngineVersion::Current().ToString());
        Report->SetStringField(TEXT("render_derived_data_key"),Render->DerivedDataKey);
        Report->SetStringField(TEXT("body_guid"),Body->BodySetupGuid.ToString());
        Report->SetBoolField(TEXT("double_sided"),Body->bDoubleSidedGeometry);
        const auto& Settings=Mesh->GetNaniteSettings();
        Report->SetBoolField(TEXT("nanite_enabled"),Settings.bEnabled);
        Report->SetNumberField(TEXT("fallback_target"),int32(Settings.FallbackTarget));
        Report->SetNumberField(TEXT("fallback_percent_triangles"),Settings.FallbackPercentTriangles);
        Report->SetNumberField(TEXT("fallback_relative_error"),Settings.FallbackRelativeError);
        Report->SetNumberField(TEXT("source_lods"),Mesh->GetNumSourceModels());
        for(const TCHAR* Name:{TEXT("r.Nanite.Builder.FallbackTriangleThreshold"),TEXT("r.Nanite.Builder.FallbackTargetAutoRelativeError")})
        {
            const auto* Variable=IConsoleManager::Get().FindConsoleVariable(Name);
            Report->SetStringField(Name,Variable?Variable->GetString():TEXT("UNAVAILABLE"));
        }
        TArray<TSharedPtr<FJsonValue>> SourceRows,SelectedRows,CookedRows;
        FStaticMeshConstAttributes Attributes(*Description);
        const auto Positions=Attributes.GetVertexPositions();
        for(const auto Triangle:Description->Triangles().GetElementIDs())
        {
            const auto Instances=Description->GetTriangleVertexInstances(Triangle);
            const int32 Group=Description->GetTrianglePolygonGroup(Triangle).GetValue();
            if(!TestEqual(TEXT("reviewed one-material source group"),Group,0))return false;
            Add(SourceRows,Positions[Description->GetVertexInstanceVertex(Instances[0])],
                Positions[Description->GetVertexInstanceVertex(Instances[1])],
                Positions[Description->GetVertexInstanceVertex(Instances[2])],uint16(Group));
        }
        FTriMeshCollisionData Selected;
        if(!TestTrue(TEXT("actual selected collision data readable"),Mesh->GetPhysicsTriMeshData(&Selected,Body->bMeshCollideAll)))return false;
        if(!TestEqual(TEXT("selected material coverage"),Selected.MaterialIndices.Num(),Selected.Indices.Num()))return false;
        for(int32 I=0;I<Selected.Indices.Num();++I)
        {
            const auto T=Selected.Indices[I];
            Add(SelectedRows,FVector3f(Selected.Vertices[T.v0]),FVector3f(Selected.Vertices[T.v1]),
                FVector3f(Selected.Vertices[T.v2]),Selected.MaterialIndices[I]);
        }
        const auto& Cooked=*Body->TriMeshGeometries[0];
        Report->SetBoolField(TEXT("raw_cooked_cull"),Cooked.GetCullsBackFaceRaycast());
        auto Read=[&](const auto& Triangles)
        {
            int32 I=0;
            for(const auto& T:Triangles)
            {
                Add(CookedRows,FVector3f(Cooked.Particles().GetX(T[0])),FVector3f(Cooked.Particles().GetX(T[1])),
                    FVector3f(Cooked.Particles().GetX(T[2])),Cooked.GetMaterialIndex(I++));
            }
        };
        if(Cooked.Elements().RequiresLargeIndices())Read(Cooked.Elements().GetLargeIndexBuffer());
        else Read(Cooked.Elements().GetSmallIndexBuffer());
        Report->SetArrayField(TEXT("source_triangle_float_material_records"),SourceRows);
        Report->SetArrayField(TEXT("selected_triangle_float_material_records"),SelectedRows);
        Report->SetArrayField(TEXT("cooked_triangle_float_material_records"),CookedRows);
        const bool Photo=Mesh->GetPathName().Contains(TEXT("/PhotorealBarrelV1/"));
        if(Photo)
        {
            TestEqual(TEXT("approved photoreal source triangle count"),SourceRows.Num(),16648);
            TestEqual(TEXT("full photo fallback selected triangle count"),SelectedRows.Num(),16648);
            TestEqual(TEXT("full photo cooked triangle count"),CookedRows.Num(),16648);
        }
        AddInfo(FString::Printf(TEXT("COOK_METROLOGY mesh=%s source=%d selected=%d cooked=%d key=%s"),
            *Mesh->GetPathName(),SourceRows.Num(),SelectedRows.Num(),CookedRows.Num(),*Render->DerivedDataKey));
        const FString Directory=FPaths::ProjectSavedDir()/TEXT("Automation/BarrelCookMetrology");
        IFileManager::Get().MakeDirectory(*Directory,true);
        FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
        if(!TestTrue(TEXT("actual geometry metrology saved privately"),
            FFileHelper::SaveStringToFile(Text,*(Directory/(Photo?TEXT("Photo.json"):TEXT("Kit.json"))))))return false;
    }
    return true;
}
