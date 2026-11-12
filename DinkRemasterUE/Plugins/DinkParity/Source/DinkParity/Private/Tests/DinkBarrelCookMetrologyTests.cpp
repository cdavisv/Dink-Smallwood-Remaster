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
        Report->SetBoolField(TEXT("mesh_collide_all"),Body->bMeshCollideAll);
        Report->SetNumberField(TEXT("lod_for_collision"),Mesh->LODForCollision);
        Report->SetStringField(TEXT("complex_collision_mesh"),GetPathNameSafe(Mesh->ComplexCollisionMesh.Get()));
        const bool Photo=Mesh->GetPathName().Contains(TEXT("/PhotorealBarrelV1/"));
        TArray<TSharedPtr<FJsonValue>> SourceRows,SelectedRows,CookedRows;
        FStaticMeshConstAttributes Attributes(*Description);
        const auto Positions=Attributes.GetVertexPositions();
        const auto SlotNames=Attributes.GetPolygonGroupMaterialSlotNames();
        TMap<FPolygonGroupID,uint16> Materials;
        TArray<TSharedPtr<FJsonValue>> MaterialMappings;
        for(const auto Group:Description->PolygonGroups().GetElementIDs())
        {
            TSet<int32> Matches;
            const FName Name=SlotNames[Group];
            for(int32 I=0;I<Mesh->GetStaticMaterials().Num();++I)
            {
                const auto& Slot=Mesh->GetStaticMaterials()[I];
                if(Slot.MaterialSlotName==Name||Slot.ImportedMaterialSlotName==Name)Matches.Add(I);
            }
            if(!TestEqual(TEXT("source polygon group has one exact static material slot"),Matches.Num(),1))return false;
            const int32 Material=*Matches.CreateConstIterator();
            if(!TestTrue(TEXT("actual material index fits record"),Material>=0&&Material<=MAX_uint16))return false;
            Materials.Add(Group,uint16(Material));
            auto Mapping=MakeShared<FJsonObject>();
            Mapping->SetNumberField(TEXT("source_group"),Group.GetValue());
            Mapping->SetStringField(TEXT("source_slot"),Name.ToString());
            Mapping->SetNumberField(TEXT("material_index"),Material);
            Mapping->SetStringField(TEXT("material_slot"),Mesh->GetStaticMaterials()[Material].MaterialSlotName.ToString());
            Mapping->SetStringField(TEXT("imported_slot"),Mesh->GetStaticMaterials()[Material].ImportedMaterialSlotName.ToString());
            MaterialMappings.Add(MakeShared<FJsonValueObject>(Mapping));
        }
        Report->SetArrayField(TEXT("source_material_mappings"),MaterialMappings);
        Report->SetStringField(TEXT("record_byte_order"),PLATFORM_LITTLE_ENDIAN?TEXT("little"):TEXT("big"));
        if(Photo&&!TestEqual(TEXT("photoreal source has one material group"),Materials.Num(),1))return false;
        for(const auto Triangle:Description->Triangles().GetElementIDs())
        {
            const auto Instances=Description->GetTriangleVertexInstances(Triangle);
            const auto Group=Description->GetTrianglePolygonGroup(Triangle);
            Add(SourceRows,Positions[Description->GetVertexInstanceVertex(Instances[0])],
                Positions[Description->GetVertexInstanceVertex(Instances[1])],
                Positions[Description->GetVertexInstanceVertex(Instances[2])],Materials.FindChecked(Group));
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
        Report->SetBoolField(TEXT("selected_flip_normals"),Selected.bFlipNormals);
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
