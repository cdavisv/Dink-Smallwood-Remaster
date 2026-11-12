#include "CoreMinimal.h"
#include "DinkExteriorPortalTestAccess.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "PhysicsEngine/BodySetup.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInterface.h"

#if WITH_DEV_AUTOMATION_TESTS
namespace
{
// Reads the actual held-W game world; no fixture world, asset load or scene mutation.
void ReadHouse439Owner(const TArray<FString>& Args)
{
    FString StartupNonce;
    if(Args.Num()!=3||!FParse::Value(FCommandLine::Get(),TEXT("DinkQARunId="),StartupNonce)||
       StartupNonce!=Args[0]||StartupNonce.Len()!=32||Args[2].IsEmpty()||Args[2].Len()>64)return;
    for(const TCHAR C:StartupNonce)if(!FChar::IsHexDigit(C))return;
    for(const TCHAR C:Args[2])if(!((C>='a'&&C<='z')||(C>='A'&&C<='Z')||(C>='0'&&C<='9')||C=='-'||C=='_'))return;
    TSharedRef<FJsonObject> Out=MakeShared<FJsonObject>();
    Out->SetStringField(TEXT("nonce"),StartupNonce);Out->SetStringField(TEXT("requested_world"),Args[1]);
    Out->SetBoolField(TEXT("read_only"),true);Out->SetBoolField(TEXT("passed"),false);
    auto Capture=[&]() -> FString
    {
        UWorld* World=nullptr;int32 Matches=0;
        if(!GEngine)return TEXT("engine_unavailable");
        for(const FWorldContext& Context:GEngine->GetWorldContexts())
            if(Context.WorldType==EWorldType::Game&&Context.World()&&Context.World()->GetPathName()==Args[1]){World=Context.World();++Matches;}
        if(Matches!=1)return TEXT("exact_game_world_not_unique");
        APlayerController* PC=World->GetFirstPlayerController();APawn* Pawn=PC?PC->GetPawn():nullptr;
        if(!PC||!Pawn||PC->GetWorld()!=World||Pawn->GetWorld()!=World)return TEXT("live_player_world_mismatch");
        Out->SetStringField(TEXT("world"),World->GetPathName());Out->SetStringField(TEXT("controller"),PC->GetPathName());Out->SetStringField(TEXT("pawn"),Pawn->GetPathName());
        UDinkArtSubsystem* Art=World->GetSubsystem<UDinkArtSubsystem>();
        if(!Art||!Art->HasCompletedInitialApplication())return TEXT("art_not_ready");
        const FDinkExteriorCameraRule* Rule=nullptr;int32 Owners=0;
        for(const auto& Row:FDinkExteriorPortalTestAccess::Rules(*Art))
            if(Row.Manifest==TEXT("stonebrook_exterior.json")&&Row.Element==TEXT("DinksCottage")&&Row.Screen==439){Rule=&Row;++Owners;}
        Out->SetNumberField(TEXT("owner_rule_count"),Owners);
        if(Owners!=1||!Rule||!Rule->Definition.IsValid())return TEXT("owner_rule_not_unique_or_invalid");
        UStaticMeshComponent* Component=Rule->Component.Get();
        if(!Component||!Component->IsRegistered()||Component->IsTemplate()||Component->GetWorld()!=World||!Component->GetOwner()||Component->GetOwner()->IsTemplate()||Component->GetOwner()->GetWorld()!=World)return TEXT("registered_component_world_invalid");
        UStaticMesh* Mesh=Component->GetStaticMesh();UBodySetup* Body=Mesh?Mesh->GetBodySetup():nullptr;
        if(!Mesh||!Body)return TEXT("mesh_or_body_unavailable");
        Out->SetStringField(TEXT("component"),Component->GetPathName());Out->SetStringField(TEXT("actor"),Component->GetOwner()->GetPathName());
        Out->SetStringField(TEXT("manifest"),Rule->Manifest);Out->SetStringField(TEXT("element"),Rule->Element);Out->SetNumberField(TEXT("screen"),Rule->Screen);
        Out->SetStringField(TEXT("rule_mesh"),Rule->Mesh);Out->SetStringField(TEXT("rule_native_sha"),Rule->NativeMeshSHA);Out->SetStringField(TEXT("actual_mesh"),Mesh->GetPathName());
        Out->SetStringField(TEXT("native_min"),Rule->NativeBoundsMin.ToString());Out->SetStringField(TEXT("native_max"),Rule->NativeBoundsMax.ToString());
        auto ExactVector=[&](const TCHAR* Key,const FVector& Value){TArray<TSharedPtr<FJsonValue>> Values;Values.Add(MakeShared<FJsonValueNumber>(Value.X));Values.Add(MakeShared<FJsonValueNumber>(Value.Y));Values.Add(MakeShared<FJsonValueNumber>(Value.Z));Out->SetArrayField(Key,Values);};
        const FTransform ActualTransform=Component->GetComponentTransform();const FQuat ActualRotation=ActualTransform.GetRotation();
        ExactVector(TEXT("native_bounds_min_exact"),Rule->NativeBoundsMin);ExactVector(TEXT("native_bounds_max_exact"),Rule->NativeBoundsMax);
        ExactVector(TEXT("portal_point_exact"),Rule->Definition.Point);ExactVector(TEXT("portal_normal_exact"),Rule->Definition.Normal);ExactVector(TEXT("portal_tangent_exact"),Rule->Definition.Tangent);ExactVector(TEXT("interior_point_exact"),Rule->Definition.InteriorPoint);
        TArray<TSharedPtr<FJsonValue>> PortalMinimum;PortalMinimum.Add(MakeShared<FJsonValueNumber>(Rule->Definition.Minimum.X));PortalMinimum.Add(MakeShared<FJsonValueNumber>(Rule->Definition.Minimum.Y));Out->SetArrayField(TEXT("portal_min_exact"),PortalMinimum);
        TArray<TSharedPtr<FJsonValue>> PortalMaximum;PortalMaximum.Add(MakeShared<FJsonValueNumber>(Rule->Definition.Maximum.X));PortalMaximum.Add(MakeShared<FJsonValueNumber>(Rule->Definition.Maximum.Y));Out->SetArrayField(TEXT("portal_max_exact"),PortalMaximum);
        ExactVector(TEXT("translation"),ActualTransform.GetTranslation());ExactVector(TEXT("scale"),ActualTransform.GetScale3D());
        TArray<TSharedPtr<FJsonValue>> Quaternion;for(const double Value:{ActualRotation.X,ActualRotation.Y,ActualRotation.Z,ActualRotation.W})Quaternion.Add(MakeShared<FJsonValueNumber>(Value));Out->SetArrayField(TEXT("quaternion_xyzw"),Quaternion);
        ExactVector(TEXT("local_bounds_origin"),Mesh->GetBounds().Origin);ExactVector(TEXT("local_bounds_extent"),Mesh->GetBounds().BoxExtent);ExactVector(TEXT("world_bounds_origin"),Component->Bounds.Origin);ExactVector(TEXT("world_bounds_extent"),Component->Bounds.BoxExtent);
        Out->SetStringField(TEXT("world_transform"),Component->GetComponentTransform().ToString());Out->SetStringField(TEXT("relative_transform"),Component->GetRelativeTransform().ToString());
        Out->SetStringField(TEXT("local_bounds"),Mesh->GetBounds().ToString());Out->SetStringField(TEXT("world_bounds"),Component->Bounds.ToString());
        Out->SetStringField(TEXT("portal_point"),Rule->Definition.Point.ToString());Out->SetStringField(TEXT("portal_normal"),Rule->Definition.Normal.ToString());Out->SetStringField(TEXT("portal_tangent"),Rule->Definition.Tangent.ToString());
        Out->SetStringField(TEXT("portal_min"),Rule->Definition.Minimum.ToString());Out->SetStringField(TEXT("portal_max"),Rule->Definition.Maximum.ToString());Out->SetStringField(TEXT("interior_point"),Rule->Definition.InteriorPoint.ToString());
        TArray<TSharedPtr<FJsonValue>> Planes;for(const FPlane& Plane:Rule->Definition.InteriorPlanes)Planes.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("%.17g,%.17g,%.17g,%.17g"),Plane.X,Plane.Y,Plane.Z,Plane.W)));Out->SetArrayField(TEXT("interior_planes"),Planes);
        TArray<TSharedPtr<FJsonValue>> ExactPlanes;for(const FPlane& Plane:Rule->Definition.InteriorPlanes){TArray<TSharedPtr<FJsonValue>> Values;Values.Add(MakeShared<FJsonValueNumber>(Plane.X));Values.Add(MakeShared<FJsonValueNumber>(Plane.Y));Values.Add(MakeShared<FJsonValueNumber>(Plane.Z));Values.Add(MakeShared<FJsonValueNumber>(Plane.W));ExactPlanes.Add(MakeShared<FJsonValueArray>(Values));}Out->SetArrayField(TEXT("interior_planes_exact"),ExactPlanes);
        Out->SetBoolField(TEXT("visible"),Component->IsVisible());Out->SetBoolField(TEXT("hidden_in_game"),Component->bHiddenInGame);
        Out->SetStringField(TEXT("collision_profile"),Component->GetCollisionProfileName().ToString());Out->SetNumberField(TEXT("collision_enabled"),int32(Component->GetCollisionEnabled()));Out->SetNumberField(TEXT("object_type"),int32(Component->GetCollisionObjectType()));
        TArray<TSharedPtr<FJsonValue>> Responses;for(int32 Channel=0;Channel<64;++Channel)Responses.Add(MakeShared<FJsonValueNumber>(int32(Component->GetCollisionResponseToChannel(ECollisionChannel(Channel)))));Out->SetArrayField(TEXT("responses64"),Responses);
        Out->SetBoolField(TEXT("can_affect_navigation"),Component->CanEverAffectNavigation());Out->SetNumberField(TEXT("collision_trace_flag"),int32(Body->CollisionTraceFlag));Out->SetNumberField(TEXT("convex_count"),Body->AggGeom.ConvexElems.Num());
        TArray<TSharedPtr<FJsonValue>> Materials;for(int32 Slot=0;Slot<Component->GetNumMaterials();++Slot){const auto* Material=Component->GetMaterial(Slot);Materials.Add(MakeShared<FJsonValueString>(Material?Material->GetPathName():TEXT("")));}Out->SetArrayField(TEXT("materials"),Materials);
        Out->SetBoolField(TEXT("passed"),true);return TEXT("");
    };
    const FString Error=Capture();Out->SetStringField(TEXT("error"),Error);
    FString Text;FJsonSerializer::Serialize(Out,TJsonWriterFactory<>::Create(&Text));
    const FString Folder=FPaths::ProjectSavedDir()/TEXT("Automation/House439Binding");
    IFileManager::Get().MakeDirectory(*Folder,true);
    const FString File=Folder/(StartupNonce+TEXT("-")+Args[2]+TEXT(".json"));
    const bool Written=FFileHelper::SaveStringToFile(Text,*File,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_NoReplaceExisting);
    UE_LOG(LogTemp,Display,TEXT("DINK_HOUSE439_OWNER written=%d path=%s"),Written,*File);
}
FAutoConsoleCommand House439OwnerCommand(TEXT("dink.QAReadHouse439"),TEXT("Developer QA: nonce exactGameWorld uniqueLabel; read-only registered owner."),FConsoleCommandWithArgsDelegate::CreateStatic(&ReadHouse439Owner));
}
#endif
