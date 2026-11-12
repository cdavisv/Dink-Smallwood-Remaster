#pragma once
#include "DinkProbeLoadOracle.h"
#include "DinkStorySubsystem.h"
#include "DinkGameplay.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Components/SceneComponent.h"
#include "Components/PrimitiveComponent.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/ScopeExit.h"

namespace DinkProbeLoadDiagnostic
{
inline TSharedPtr<FJsonValue> Number(double Value)
{
    uint64 Bits=0;FMemory::Memcpy(&Bits,&Value,sizeof(Bits));
    auto O=MakeShared<FJsonObject>();O->SetStringField(TEXT("decimal17"),FString::Printf(TEXT("%.17g"),Value));
    O->SetStringField(TEXT("bits64"),FString::Printf(TEXT("%016llx"),static_cast<unsigned long long>(Bits)));
    O->SetNumberField(TEXT("value"),Value);return MakeShared<FJsonValueObject>(O);
}
inline TSharedPtr<FJsonObject> Transform(const FTransform& Value)
{
    auto O=MakeShared<FJsonObject>();const auto T=Value.GetTranslation(),S=Value.GetScale3D();const auto Q=Value.GetRotation();
    O->SetArrayField(TEXT("translation"),{Number(T.X),Number(T.Y),Number(T.Z)});
    O->SetArrayField(TEXT("quaternion_xyzw"),{Number(Q.X),Number(Q.Y),Number(Q.Z),Number(Q.W)});
    O->SetArrayField(TEXT("scale"),{Number(S.X),Number(S.Y),Number(S.Z)});
    for(const auto Axis:{EAxis::X,EAxis::Y,EAxis::Z}){const FVector V=Value.GetUnitAxis(Axis);O->SetArrayField(FString::Printf(TEXT("basis_%d"),int32(Axis)),{Number(V.X),Number(V.Y),Number(V.Z)});}
    return O;
}
inline TSharedPtr<FJsonObject> Rotator(const FRotator& R)
{
    auto O=MakeShared<FJsonObject>();O->SetArrayField(TEXT("pitch_yaw_roll"),{Number(R.Pitch),Number(R.Yaw),Number(R.Roll)});return O;
}
struct FBoundary
{
    TSharedPtr<FJsonObject> Json;
    FTransform Actor;
    UClass* RootClass=nullptr;
    UClass* PawnClass=nullptr;
    FName Socket;
    uint64 Frame=0;
    double WorldSeconds=0;
    bool Registered=false;
    FRotator RelativeRotation;
    bool Parent=false,AbsoluteLocation=false,AbsoluteRotation=false,AbsoluteScale=false;
};
inline FBoundary Capture(APawn& Pawn,UDinkStorySubsystem& Story,UDinkGreyboxSubsystem& Greybox)
{
    FBoundary B;B.Actor=Pawn.GetActorTransform();B.PawnClass=Pawn.GetClass();B.Frame=GFrameCounter;B.WorldSeconds=Pawn.GetWorld()->GetTimeSeconds();B.Json=MakeShared<FJsonObject>();auto& O=*B.Json;
    O.SetObjectField(TEXT("actor_transform"),Transform(B.Actor));O.SetObjectField(TEXT("actor_rotator"),Rotator(Pawn.GetActorRotation()));
    O.SetStringField(TEXT("class"),Pawn.GetClass()->GetPathName());O.SetNumberField(TEXT("frame"),double(GFrameCounter));
    O.SetNumberField(TEXT("world_seconds"),Pawn.GetWorld()->GetTimeSeconds());O.SetNumberField(TEXT("story_ms"),Story.GetNowMs());
    O.SetBoolField(TEXT("world_begun"),Pawn.GetWorld()->HasBegunPlay());O.SetBoolField(TEXT("world_paused"),Pawn.GetWorld()->IsPaused());
    O.SetBoolField(TEXT("pawn_begun"),Pawn.HasActorBegunPlay());O.SetBoolField(TEXT("story_ready"),Story.IsReady());
    O.SetBoolField(TEXT("newgame_pending"),Story.bNewGamePending);O.SetBoolField(TEXT("hardness_loading"),Story.GetGameplay()->IsHardnessLoading());
    const auto* Physical=Greybox.FindScreenAt(Pawn.GetActorLocation());const auto* Cached=Greybox.GetCurrentScreen();
    O.SetNumberField(TEXT("physical_screen"),Physical?Physical->ScreenNumber:-1);O.SetNumberField(TEXT("cached_screen"),Cached?Cached->ScreenNumber:-1);
    if(const auto* C=Pawn.GetController())O.SetObjectField(TEXT("controller_rotation"),Rotator(C->GetControlRotation()));
    if(const auto* Root=Pawn.GetRootComponent())
    {
        B.Socket=Root->GetAttachSocketName();B.RootClass=Root->GetClass();B.Registered=Root->IsRegistered();B.RelativeRotation=Root->GetRelativeRotation();B.Parent=Root->GetAttachParent()!=nullptr;
        B.AbsoluteLocation=Root->IsUsingAbsoluteLocation();B.AbsoluteRotation=Root->IsUsingAbsoluteRotation();B.AbsoluteScale=Root->IsUsingAbsoluteScale();
        O.SetObjectField(TEXT("root_relative_transform"),Transform(Root->GetRelativeTransform()));O.SetObjectField(TEXT("root_relative_rotator"),Rotator(B.RelativeRotation));
        O.SetStringField(TEXT("root_class"),Root->GetClass()->GetPathName());O.SetStringField(TEXT("root_parent"),B.Parent?Root->GetAttachParent()->GetPathName():TEXT(""));
        O.SetStringField(TEXT("root_socket"),Root->GetAttachSocketName().ToString());O.SetBoolField(TEXT("root_registered"),Root->IsRegistered());
        if(const auto* Primitive=Cast<UPrimitiveComponent>(Root)){O.SetNumberField(TEXT("root_collision_mode"),int32(Primitive->GetCollisionEnabled()));O.SetStringField(TEXT("root_collision_profile"),Primitive->GetCollisionProfileName().ToString());}
        O.SetBoolField(TEXT("absolute_location"),B.AbsoluteLocation);O.SetBoolField(TEXT("absolute_rotation"),B.AbsoluteRotation);O.SetBoolField(TEXT("absolute_scale"),B.AbsoluteScale);
    }
    if(const auto* Character=Cast<ACharacter>(&Pawn))if(const auto* M=Character->GetCharacterMovement())
    {
        O.SetNumberField(TEXT("movement_mode"),int32(M->MovementMode));O.SetBoolField(TEXT("cached_floor_blocking"),M->CurrentFloor.bBlockingHit);
        O.SetNumberField(TEXT("cached_floor_distance"),M->CurrentFloor.FloorDist);O.SetStringField(TEXT("velocity"),M->Velocity.ToString());
    }
    FCollisionQueryParams Params(SCENE_QUERY_STAT(ProbeLoadGroundEvidence),true);Params.AddIgnoredActor(&Pawn);FHitResult Hit;
    const bool Ground=Pawn.GetWorld()->LineTraceSingleByChannel(Hit,Pawn.GetActorLocation()+FVector(0,0,1),Pawn.GetActorLocation()-FVector(0,0,512),ECC_Pawn,Params);
    O.SetBoolField(TEXT("readonly_ground_pawn_complex_hit"),Ground);O.SetStringField(TEXT("ground_component"),Hit.GetComponent()?Hit.GetComponent()->GetPathName():TEXT(""));
    O.SetStringField(TEXT("ground_impact"),Hit.ImpactPoint.ToString());O.SetNumberField(TEXT("ground_distance"),Hit.Distance);
    return B;
}
// A reference is admitted only from an exact, source-class/root-qualified preload seed.
inline bool StockProjection(APawn& Pawn,const FBoundary& Before,const FTransform& Saved,FTransform& Applied,FString& Reason)
{
    Reason.Reset();const uint64 Frame=GFrameCounter;const double WorldSeconds=Pawn.GetWorld()->GetTimeSeconds();
    if(Before.Parent||!Before.Socket.IsNone()||Before.PawnClass!=Pawn.GetClass()||!Before.RootClass||!Before.Registered){Reason=TEXT("unsupported attached/unregistered preload root");return false;}
    FActorSpawnParameters P;P.bDeferConstruction=true;P.ObjectFlags|=RF_Transient;
    P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    APawn* Control=Pawn.GetWorld()->SpawnActor<APawn>(Pawn.GetClass(),Before.Actor,P);
    ON_SCOPE_EXIT {if(Control)Control->Destroy();};
    auto* Root=Control?Control->GetRootComponent():nullptr;
    if(!Root||Root->GetClass()!=Before.RootClass||Control->GetController()||Control->HasActorBegunPlay()||!Root->IsRegistered())
    {Reason=TEXT("stock reference class/root/registration/controller/BeginPlay mismatch");return false;}
    Control->SetActorEnableCollision(false);
    Root->SetAbsolute(Before.AbsoluteLocation,Before.AbsoluteRotation,Before.AbsoluteScale);
    const bool Seeded=Control->SetActorTransform(Before.Actor,false,nullptr,ETeleportType::TeleportPhysics);
    Root->SetRelativeRotation(Before.RelativeRotation);
    if(!Seeded||Root->GetAttachParent()||!Control->GetActorTransform().Equals(Before.Actor,0)||
       Root->GetRelativeRotation()!=Before.RelativeRotation||Root->IsUsingAbsoluteLocation()!=Before.AbsoluteLocation||
       Root->IsUsingAbsoluteRotation()!=Before.AbsoluteRotation||Root->IsUsingAbsoluteScale()!=Before.AbsoluteScale)
    {Reason=TEXT("stock preload pose/cache/absolute seed mismatch");return false;}
    if(!Control->SetActorTransform(Saved,false,nullptr,ETeleportType::TeleportPhysics)||Control->GetController()||Control->HasActorBegunPlay())
    {Reason=TEXT("stock application failed or unexpectedly began gameplay");return false;}
    if(Frame!=GFrameCounter||WorldSeconds!=Pawn.GetWorld()->GetTimeSeconds())
    {Reason=TEXT("stock reference advanced frame/world time");return false;}
    Applied=Control->GetActorTransform();return true;
}
inline FString RecordQualifiedProjection(const FBoundary& Before,const FTransform& Saved,const FTransform& Applied,const FTransform& Actual)
{
    auto O=MakeShared<FJsonObject>();O->SetObjectField(TEXT("before_load"),Before.Json);
    O->SetObjectField(TEXT("saved"),Transform(Saved));O->SetObjectField(TEXT("stock_expected"),Transform(Applied));O->SetObjectField(TEXT("actual"),Transform(Actual));
    O->SetBoolField(TEXT("preload_and_root_qualified"),true);O->SetBoolField(TEXT("stock_expected_actual_exact"),Applied.Equals(Actual,0));
    FString Text;FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Text));const FString Dir=FPaths::ProjectSavedDir()/TEXT("Automation/ProbeLoadProjection");IFileManager::Get().MakeDirectory(*Dir,true);
    const FString Path=Dir/(FGuid::NewGuid().ToString(EGuidFormats::Digits)+TEXT(".json"));return FFileHelper::SaveStringToFile(Text,*Path)?Path:FString();
}
inline FString Write(const UDinkSaveGame& Saved,const UDinkSaveGame& Actual,APawn& Pawn,UDinkStorySubsystem& Story,
    UDinkGreyboxSubsystem& Greybox,const FBoundary& Before,const FBoundary& Loaded,int32 EventStart)
{
    auto O=MakeShared<FJsonObject>();O->SetObjectField(TEXT("saved"),Transform(Saved.PlayerTransform));O->SetObjectField(TEXT("actual_snapshot"),Transform(Actual.PlayerTransform));
    O->SetObjectField(TEXT("before_load"),Before.Json);O->SetObjectField(TEXT("after_load_before_capture"),Loaded.Json);O->SetObjectField(TEXT("after_capture"),Capture(Pawn,Story,Greybox).Json);
    O->SetBoolField(TEXT("saved_actual_equals_zero"),Saved.PlayerTransform.Equals(Actual.PlayerTransform,0));
    const FVector DT=Actual.PlayerTransform.GetTranslation()-Saved.PlayerTransform.GetTranslation(),DS=Actual.PlayerTransform.GetScale3D()-Saved.PlayerTransform.GetScale3D();
    const FQuat AQ=Actual.PlayerTransform.GetRotation(),SQ=Saved.PlayerTransform.GetRotation();
    O->SetArrayField(TEXT("translation_delta"),{Number(DT.X),Number(DT.Y),Number(DT.Z)});
    O->SetArrayField(TEXT("scale_delta"),{Number(DS.X),Number(DS.Y),Number(DS.Z)});
    O->SetArrayField(TEXT("quaternion_delta_xyzw"),{Number(AQ.X-SQ.X),Number(AQ.Y-SQ.Y),Number(AQ.Z-SQ.Z),Number(AQ.W-SQ.W)});
    O->SetNumberField(TEXT("quaternion_dot"),AQ|SQ);
    O->SetObjectField(TEXT("saved_rotator_roundtrip"),Transform(FTransform(Saved.PlayerTransform.GetRotation().Rotator().Quaternion(),Saved.PlayerTransform.GetTranslation(),Saved.PlayerTransform.GetScale3D())));
    TArray<TSharedPtr<FJsonValue>> Events;
    for(int32 Index=EventStart;Index<Story.Events.Num();++Index){const auto& E=Story.Events[Index];auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("index"),Index);R->SetNumberField(TEXT("ms"),E.TimeMs);R->SetNumberField(TEXT("instance"),E.InstanceId);R->SetStringField(TEXT("kind"),E.Kind.ToString());R->SetStringField(TEXT("text"),E.Text);R->SetStringField(TEXT("detail"),E.Detail);Events.Add(MakeShared<FJsonValueObject>(R));}
    O->SetArrayField(TEXT("load_callback_events"),Events);
    // Owned deferred same-class control: no BeginPlay, controller or narrative.
    // Root setter/cache effects are measured separately from actual load effects.
    if(!Before.Parent)
    {
        FActorSpawnParameters P;P.bDeferConstruction=true;P.ObjectFlags|=RF_Transient;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        AActor* Control=Pawn.GetWorld()->SpawnActor<AActor>(Pawn.GetClass(),Before.Actor,P);
        ON_SCOPE_EXIT {if(Control)Control->Destroy();};
        O->SetBoolField(TEXT("stock_control_created"),Control&&Control->GetRootComponent());
        if(Control&&Control->GetRootComponent())
        {
            Control->SetActorEnableCollision(false);auto* Root=Control->GetRootComponent();Root->SetAbsolute(Before.AbsoluteLocation,Before.AbsoluteRotation,Before.AbsoluteScale);
            Control->SetActorTransform(Before.Actor,false,nullptr,ETeleportType::TeleportPhysics);Root->SetRelativeRotation(Before.RelativeRotation);
            O->SetBoolField(TEXT("stock_preload_matches_zero"),Control->GetActorTransform().Equals(Before.Actor,0));
            O->SetObjectField(TEXT("stock_control_before"),Transform(Control->GetActorTransform()));O->SetBoolField(TEXT("stock_control_registered"),Root->IsRegistered());
            O->SetBoolField(TEXT("stock_control_begun"),Control->HasActorBegunPlay());O->SetBoolField(TEXT("stock_setter_success"),Control->SetActorTransform(Saved.PlayerTransform,false,nullptr,ETeleportType::TeleportPhysics));
            O->SetObjectField(TEXT("stock_control_after"),Transform(Control->GetActorTransform()));O->SetBoolField(TEXT("stock_matches_actual_zero"),Control->GetActorTransform().Equals(Actual.PlayerTransform,0));
        }
    }
    FString Text;FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Text));const FString Dir=FPaths::ProjectSavedDir()/TEXT("Automation/ProbeLoadTransform");IFileManager::Get().MakeDirectory(*Dir,true);
    const FString Path=Dir/(FGuid::NewGuid().ToString(EGuidFormats::Digits)+TEXT(".json"));return FFileHelper::SaveStringToFile(Text,*Path)?Path:FString();
}
}
