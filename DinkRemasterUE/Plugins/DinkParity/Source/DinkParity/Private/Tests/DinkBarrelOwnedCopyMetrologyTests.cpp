#include "DinkTestHelpers.h"
#include "DinkCollision.h"
#include "Hardness/DinkFamilyCollisionFit.h"
#include "Hardness/DinkHardnessPrismComponent.h"
#include "AssetCompilingManager.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Components/BoxComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "PhysicsEngine/BodySetup.h"
#include "PhysicsEngine/BodyInstance.h"
#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
FString LE32(uint32 Value)
{
    const uint8 Bytes[4]={uint8(Value),uint8(Value>>8),uint8(Value>>16),uint8(Value>>24)};
    return BytesToHex(Bytes,4);
}
FString FloatBits(float Value)
{ uint32 Bits;FMemory::Memcpy(&Bits,&Value,sizeof(Bits));return LE32(Bits); }
struct FCopyObservation
{
    bool Cull=false,Large=false;
    TArray<FString> ParticleBits,RawIndices,SurfaceAssociations,IndexAssociations;
    TArray<uint16> Materials;
    TArray<int32> ExternalFaces;
    TSharedRef<FJsonObject> Json() const
    {
        auto Result=MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("raw_cull"),Cull);Result->SetBoolField(TEXT("large_indices"),Large);
        auto Strings=[&](const TCHAR* Name,const TArray<FString>& Values)
        {TArray<TSharedPtr<FJsonValue>> Rows;for(const auto& Value:Values)Rows.Add(MakeShared<FJsonValueString>(Value));Result->SetArrayField(Name,Rows);};
        Strings(TEXT("particle_f32le_xyz_hex"),ParticleBits);Strings(TEXT("ordered_indices_u32le_hex"),RawIndices);
        Strings(TEXT("counted_oriented_surface42_hex"),SurfaceAssociations);Strings(TEXT("counted_oriented_index18_hex"),IndexAssociations);
        TArray<TSharedPtr<FJsonValue>> MaterialRows,FaceRows;
        for(uint16 Value:Materials)MaterialRows.Add(MakeShared<FJsonValueNumber>(Value));
        for(int32 Value:ExternalFaces)FaceRows.Add(MakeShared<FJsonValueNumber>(Value));
        Result->SetArrayField(TEXT("ordered_material_u16"),MaterialRows);Result->SetArrayField(TEXT("ordered_external_face_i32"),FaceRows);
        return Result;
    }
};
FCopyObservation Observe(const Chaos::FTriangleMeshImplicitObject& Mesh)
{
    FCopyObservation Result;Result.Cull=Mesh.GetCullsBackFaceRaycast();Result.Large=Mesh.Elements().RequiresLargeIndices();
    for(int32 I=0;I<Mesh.Particles().Size();++I)
    {
        const auto& V=Mesh.Particles().GetX(I);
        Result.ParticleBits.Add(FloatBits(V[0])+FloatBits(V[1])+FloatBits(V[2]));
    }
    auto Read=[&](const auto& Triangles)
    {
        int32 Number=0;
        for(const auto& Triangle:Triangles)
        {
            const uint16 Material=Mesh.GetMaterialIndex(Number);
            const int32 Face=Mesh.GetExternalFaceIndexFromInternal(Number++);
            const uint8 MatBytes[2]={uint8(Material),uint8(Material>>8)};
            const FString Suffix=BytesToHex(MatBytes,2)+LE32(uint32(Face));
            FString IndexRecord,SurfaceRecord;
            for(int32 Rotation=0;Rotation<3;++Rotation)
            {
                FString Indices,Positions;
                for(int32 Corner=0;Corner<3;++Corner)
                {
                    const int32 Index=Triangle[(Corner+Rotation)%3];
                    Indices+=LE32(uint32(Index));Positions+=Result.ParticleBits.IsValidIndex(Index)?Result.ParticleBits[Index]:TEXT("INVALID_INDEX");
                }
                Indices+=Suffix;Positions+=Suffix;
                if(Rotation==0||Indices<IndexRecord)IndexRecord=Indices;
                if(Rotation==0||Positions<SurfaceRecord)SurfaceRecord=Positions;
            }
            Result.RawIndices.Add(LE32(uint32(Triangle[0]))+LE32(uint32(Triangle[1]))+LE32(uint32(Triangle[2])));
            Result.Materials.Add(Material);Result.ExternalFaces.Add(Face);
            Result.IndexAssociations.Add(IndexRecord);Result.SurfaceAssociations.Add(SurfaceRecord);
        }
    };
    if(Result.Large)Read(Mesh.Elements().GetLargeIndexBuffer());else Read(Mesh.Elements().GetSmallIndexBuffer());
    Result.IndexAssociations.Sort();Result.SurfaceAssociations.Sort();return Result;
}
bool ExactObservation(const FCopyObservation& A,const FCopyObservation& B)
{
    return A.Cull==B.Cull&&A.Large==B.Large&&A.ParticleBits==B.ParticleBits&&A.RawIndices==B.RawIndices&&
        A.Materials==B.Materials&&A.ExternalFaces==B.ExternalFaces;
}
void Compare(FJsonObject& Result,const TCHAR* Name,const FCopyObservation& A,const FCopyObservation& B)
{
    auto Values=MakeShared<FJsonObject>();
    Values->SetBoolField(TEXT("particles_bits_equal"),A.ParticleBits==B.ParticleBits);
    Values->SetBoolField(TEXT("index_width_equal"),A.Large==B.Large);
    Values->SetBoolField(TEXT("raw_index_order_equal"),A.RawIndices==B.RawIndices);
    Values->SetBoolField(TEXT("raw_material_order_equal"),A.Materials==B.Materials);
    Values->SetBoolField(TEXT("raw_external_face_order_equal"),A.ExternalFaces==B.ExternalFaces);
    Values->SetBoolField(TEXT("counted_oriented_index_material_face_equal"),A.IndexAssociations==B.IndexAssociations);
    Values->SetBoolField(TEXT("counted_oriented_surface_material_face_equal"),A.SurfaceAssociations==B.SurfaceAssociations);
    Values->SetBoolField(TEXT("raw_cull_equal"),A.Cull==B.Cull);
    Result.SetObjectField(Name,Values);
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkBarrelOwnedCopyMetrology,
    "Dink.Art.Family.BarrelOwnedCopyMetrology",DINK_TEST_FLAGS)
bool FDinkBarrelOwnedCopyMetrology::RunTest(const FString&)
{
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.SM_Barrel_Oak_01"));
    FAssetCompilingManager::Get().FinishAllCompilation();
    if(!TestNotNull(TEXT("actual saved Photo mesh"),Mesh))return false;
    auto* Source=Mesh->GetBodySetup();if(!TestNotNull(TEXT("actual Photo body setup"),Source))return false;
    Source->CreatePhysicsMeshes(); // Editor test readiness only, not production/cook/save.
    FDinkFamilyFittedGeometry Geometry;FString Error;
    if(!TestTrue(TEXT("actual reviewed source geometry ready"),DinkFamilyCollisionFit::ReadCookedGeometry(*Mesh,Geometry,Error)))
    {AddError(Error);return false;}
    const FGuid SourceGuid=Source->BodySetupGuid;
    const auto Before=Observe(*Source->TriMeshGeometries[0]);
    auto Report=MakeShared<FJsonObject>();Report->SetStringField(TEXT("mesh"),Mesh->GetPathName());
    Report->SetStringField(TEXT("source_guid"),SourceGuid.ToString());Report->SetStringField(TEXT("source_surface_sha1"),Geometry.CanonicalSurfaceSha1);
    Report->SetBoolField(TEXT("per_poly_support"),Chaos::TriMeshPerPolySupport);
    Report->SetObjectField(TEXT("source_before"),Before.Json());
    auto Direct=Source->TriMeshGeometries[0]->DeepCopyGeometry();
    auto* DirectMesh=Direct?Direct->AsA<Chaos::FTriangleMeshImplicitObject>():nullptr;
    if(!TestNotNull(TEXT("actual Engine DeepCopyGeometry returns a mesh"),DirectMesh))return false;
    const auto DirectObservation=Observe(*DirectMesh);Report->SetObjectField(TEXT("direct_copy"),DirectObservation.Json());
    Compare(*Report,TEXT("source_vs_direct_copy"),Before,DirectObservation);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false);GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    ON_SCOPE_EXIT{GEngine->DestroyWorldContext(World);World->DestroyWorld(false);};
    auto* Host=World->SpawnActor<AActor>();auto* Root=NewObject<USceneComponent>(Host);Root->SetMobility(EComponentMobility::Static);
    Host->SetRootComponent(Root);Root->RegisterComponent();
    auto* Policy=NewObject<UBoxComponent>(Host);Policy->SetCollisionProfileName(DinkCollision::ProfileHardSolid);
    Policy->SetGenerateOverlapEvents(false);Policy->SetCanEverAffectNavigation(false);
    auto* Body=NewObject<UDinkHardnessPrismComponent>(Host);Body->SetupAttachment(Root);
    auto Inputs=MakeShared<FJsonObject>();
    Inputs->SetBoolField(TEXT("component_registered"),Body->IsRegistered());Inputs->SetBoolField(TEXT("component_setup_exists"),Body->GetBodySetup()!=nullptr);
    Inputs->SetBoolField(TEXT("source_complex_as_simple"),Source->CollisionTraceFlag==CTF_UseComplexAsSimple);
    Inputs->SetBoolField(TEXT("source_created"),Source->bCreatedPhysicsMeshes);Inputs->SetBoolField(TEXT("source_failed"),Source->bFailedToCreatePhysicsMeshes);
    Inputs->SetBoolField(TEXT("reference_overlaps"),Policy->GetGenerateOverlapEvents());Inputs->SetBoolField(TEXT("reference_body_exists"),Policy->GetBodyInstance()!=nullptr);
    Inputs->SetBoolField(TEXT("reference_simulates"),Policy->GetBodyInstance()&&Policy->GetBodyInstance()->bSimulatePhysics);
    Inputs->SetBoolField(TEXT("reference_query_and_physics"),Policy->GetCollisionEnabled()==ECollisionEnabled::QueryAndPhysics);
    Report->SetObjectField(TEXT("actual_preparation_inputs"),Inputs);
    const bool Prepared=Body->PrepareCookedMeshGeometry(*Source,*Policy);Report->SetBoolField(TEXT("production_prepare_accepted"),Prepared);
    auto* Owned=Body->GetBodySetup();Report->SetBoolField(TEXT("owned_setup_after_prepare"),Owned!=nullptr);
    if(Owned&&Owned->TriMeshGeometries.Num()==1&&Owned->TriMeshGeometries[0])
    {
        const auto Observation=Observe(*Owned->TriMeshGeometries[0]);Report->SetObjectField(TEXT("actual_owned_after_prepare"),Observation.Json());
        Compare(*Report,TEXT("source_vs_actual_owned"),Before,Observation);
        FString FirstGuard=TEXT("none");
        if(Owned==Source||Owned->bDoubleSidedGeometry!=Source->bDoubleSidedGeometry)FirstGuard=TEXT("setup_alias_or_double_sided");
        else if(Before.ParticleBits.Num()!=Observation.ParticleBits.Num()||Before.Large!=Observation.Large||Before.RawIndices.Num()!=Observation.RawIndices.Num())FirstGuard=TEXT("particle_triangle_count_or_index_width");
        else if(Before.Cull!=Observation.Cull)FirstGuard=TEXT("unregistered_copy_cull");
        else if(Before.ParticleBits!=Observation.ParticleBits)FirstGuard=TEXT("indexed_particle_bits");
        else if(Before.RawIndices!=Observation.RawIndices)FirstGuard=TEXT("same_internal_index_triplets");
        else if(Before.Materials!=Observation.Materials||Before.ExternalFaces!=Observation.ExternalFaces)FirstGuard=TEXT("same_internal_material_or_external_face");
        Report->SetStringField(TEXT("first_failed_actual_validate_guard_in_source_order"),FirstGuard);
    }
    // Never register an instance refused by production preparation.
    Report->SetBoolField(TEXT("registration_attempted"),Prepared);
    if(Prepared)
    {
        Host->AddInstanceComponent(Body);Body->RegisterComponent();
        Report->SetBoolField(TEXT("production_finalized"),Body->FinalizeRegisteredPreparation(*Policy));
        Report->SetObjectField(TEXT("actual_owned_after_registration"),Observe(*Body->GetBodySetup()->TriMeshGeometries[0]).Json());
    }
    const auto After=Observe(*Source->TriMeshGeometries[0]);Report->SetObjectField(TEXT("source_after"),After.Json());
    TestTrue(TEXT("all source indexed arrays/cull/GUID unchanged"),Source->BodySetupGuid==SourceGuid&&ExactObservation(Before,After));
    Report->SetStringField(TEXT("external_vertex_remap_scope"),TEXT("private/no public getter: preservation follows primary CopySlowImpl exact-copy/move with measured per-poly flag; no actual private-map observation claimed"));
    const FString Directory=FPaths::ProjectSavedDir()/TEXT("Automation/BarrelOwnedCopyMetrology");IFileManager::Get().MakeDirectory(*Directory,true);
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
    return TestTrue(TEXT("complete actual copy metrology saved"),FFileHelper::SaveStringToFile(Text,*(Directory/TEXT("PhotoOwnedCopy.json"))));
}
