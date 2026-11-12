// Read-only developer metrology. No attack, script, actor/physics setter or admission path.
#include "CoreMinimal.h"
#include "DinkGameplay.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Hardness/DinkHardnessPrismComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "PhysicsEngine/BodyInstance.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#if WITH_EDITOR
#include "Editor.h"
#include "FileHelpers.h"
#include "AssetCompilingManager.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/PackageName.h"
#include "Misc/AutomationTest.h"
#include "Tests/AutomationEditorCommon.h"
#endif

#if WITH_DEV_AUTOMATION_TESTS
namespace DinkAttackMetrology
{
using FObject=TSharedRef<FJsonObject>;
TArray<TSharedPtr<FJsonValue>> Vec(const FVector& V)
{return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};}
FObject Pose(const FTransform& T)
{
    auto O=MakeShared<FJsonObject>();O->SetArrayField(TEXT("translation"),Vec(T.GetTranslation()));O->SetArrayField(TEXT("scale"),Vec(T.GetScale3D()));
    const FQuat Q=T.GetRotation();O->SetArrayField(TEXT("quaternion_xyzw"),{MakeShared<FJsonValueNumber>(Q.X),MakeShared<FJsonValueNumber>(Q.Y),MakeShared<FJsonValueNumber>(Q.Z),MakeShared<FJsonValueNumber>(Q.W)});return O;
}
FObject Hit(bool Returned,const FHitResult& H,const UPrimitiveComponent* Expected)
{
    auto O=MakeShared<FJsonObject>();O->SetBoolField(TEXT("native_return"),Returned);O->SetBoolField(TEXT("blocking"),H.bBlockingHit);O->SetBoolField(TEXT("initial_overlap"),H.bStartPenetrating);
    O->SetNumberField(TEXT("time"),H.Time);O->SetNumberField(TEXT("distance"),H.Distance);O->SetNumberField(TEXT("penetration_depth"),H.PenetrationDepth);
    O->SetArrayField(TEXT("impact"),Vec(H.ImpactPoint));O->SetArrayField(TEXT("location"),Vec(H.Location));O->SetArrayField(TEXT("normal"),Vec(H.ImpactNormal));
    O->SetStringField(TEXT("component"),GetPathNameSafe(H.GetComponent()));O->SetStringField(TEXT("actor"),GetPathNameSafe(H.GetActor()));O->SetBoolField(TEXT("expected_component"),H.GetComponent()==Expected);return O;
}
}

class FDinkBarrelAttackNativeDiagnostic
{
public:
    static TSharedRef<FJsonObject> Capture(UWorld* World,bool ExactRecordedQueries,bool Passive=false)
    {
        using namespace DinkAttackMetrology;
        auto O=MakeShared<FJsonObject>();O->SetNumberField(TEXT("schema"),1);O->SetStringField(TEXT("capture_mode"),Passive?TEXT("passive"):TEXT("full"));O->SetBoolField(TEXT("passive_no_physics_queries"),Passive);TArray<TSharedPtr<FJsonValue>> QueryOrder;O->SetArrayField(TEXT("query_call_order"),QueryOrder);O->SetStringField(TEXT("scope"),TEXT("Read-only diagnostic, not hit/drop acceptance; no attack/scheduling changes"));
        auto Fail=[&](const TCHAR* Reason){O->SetStringField(TEXT("capture_error"),Reason);return O;};
        if(!World||!World->IsGameWorld())return Fail(TEXT("not an active game world"));
        auto* PC=World->GetFirstPlayerController();auto* Hero=PC?Cast<ADinkGreyboxCharacter>(PC->GetPawn()):nullptr;
        auto* Story=World->GetGameInstance()?World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>():nullptr;
        auto* G=Story?Story->GetGameplay():nullptr;auto* D=Story?Story->GetDirector():nullptr;
        if(!Hero||!Story||!G||!D||!Hero->GetCapsuleComponent())return Fail(TEXT("missing possessed hero/story/gameplay/director/capsule"));
        const FTransform Before=Hero->GetActorTransform();const double WorldBefore=World->GetTimeSeconds(),StoryBefore=Story->GetNowMs();
        const int32 LifeBefore=G->GetFact(TEXT("life")),GoldBefore=G->GetFact(TEXT("gold"));
        O->SetObjectField(TEXT("hero_before"),Pose(Before));O->SetNumberField(TEXT("world_time_before"),WorldBefore);O->SetNumberField(TEXT("story_ms_before"),StoryBefore);O->SetNumberField(TEXT("gameplay_now_ms"),G->NowMs);O->SetNumberField(TEXT("frame"),double(GFrameCounter));
        O->SetStringField(TEXT("world"),World->GetPathName());O->SetBoolField(TEXT("director_actor_matches_possessed_hero"),D->GetDink().Actor.Get()==Hero);O->SetBoolField(TEXT("story_world_matches"),Story->GetWorld()==World);
        O->SetNumberField(TEXT("logical_hero_x"),D->GetDink().X);O->SetNumberField(TEXT("logical_hero_y"),D->GetDink().Y);O->SetNumberField(TEXT("logical_hero_dir"),D->GetDink().Dir);
        O->SetNumberField(TEXT("screen"),D->GetDink().Screen);O->SetBoolField(TEXT("projection31"),G->UsesOriginalHardnessProjection(31));O->SetBoolField(TEXT("hardness_loading"),G->IsHardnessLoading());O->SetBoolField(TEXT("instant_mode"),Story->bInstantMode);
        if(D->GetDink().Screen!=31)return Fail(TEXT("current original screen is not31"));
        const FDinkSprite* Target=nullptr;int32 TargetCount=0;
        for(const auto& Pair:D->GetSprites())if(Pair.Value.bActive&&Pair.Value.Origin==FDinkOriginId(31,3)){Target=&Pair.Value;++TargetCount;}
        O->SetNumberField(TEXT("existing_target_count"),TargetCount);
        if(TargetCount!=1||!Target)return Fail(TEXT("exact existing live origin S031_P03 is unavailable/ambiguous; no handle was allocated"));
        auto* TargetActor=Target->Actor.Get();auto* Origin=TargetActor?TargetActor->FindComponentByClass<UDinkOriginComponent>():nullptr;
        auto T=MakeShared<FJsonObject>();T->SetNumberField(TEXT("handle"),Target->Handle);T->SetStringField(TEXT("origin"),Target->Origin.ToString());T->SetStringField(TEXT("script"),Target->Script.ToString());T->SetStringField(TEXT("actor"),GetPathNameSafe(TargetActor));
        T->SetBoolField(TEXT("actor_valid"),TargetActor!=nullptr);T->SetStringField(TEXT("actor_world"),GetPathNameSafe(TargetActor?TargetActor->GetWorld():nullptr));
        T->SetBoolField(TEXT("hidden"),TargetActor&&TargetActor->IsHidden());T->SetNumberField(TEXT("nohit"),Target->GetProp(TEXT("nohit")));T->SetNumberField(TEXT("pseq"),Target->GetProp(TEXT("pseq")));T->SetNumberField(TEXT("pframe"),Target->GetProp(TEXT("pframe")));
        if(Origin){T->SetStringField(TEXT("source_hash"),Origin->SourceHash);T->SetNumberField(TEXT("placement_type"),Origin->PlacementType);T->SetStringField(TEXT("source_script"),Origin->ScriptName.ToString());}
        TArray<TSharedPtr<FJsonValue>> Tags;if(TargetActor)for(const auto& Tag:TargetActor->Tags)Tags.Add(MakeShared<FJsonValueString>(Tag.ToString()));T->SetArrayField(TEXT("tags"),Tags);O->SetObjectField(TEXT("target"),T);
        FString FitError;UPrimitiveComponent* Private=G->FindHardnessFitPrimitive(*Target,&FitError);
        O->SetBoolField(TEXT("has_fit_instance"),G->HasHardnessFitInstance(*Target));O->SetBoolField(TEXT("uses_authored_geometry"),G->UsesAuthoredGeometry(D->GetDink(),*Target));O->SetStringField(TEXT("private_fit_error"),FitError);O->SetStringField(TEXT("private_fit_primitive"),GetPathNameSafe(Private));
        UPrimitiveComponent* Physical=nullptr;int32 PhysicalCount=0;
        for(TActorIterator<ADinkGreyboxScreen> It(World);It;++It)if(It->ScreenNumber==31)
        {TInlineComponentArray<UDinkHardnessPrismComponent*> Parts(*It);for(auto* C:Parts)if(C->HardnessCode==103&&C->ComponentHasTag(TEXT("DinkHardnessOwnedV1"))){Physical=C;++PhysicalCount;}}
        O->SetNumberField(TEXT("independent_physical_count"),PhysicalCount);O->SetStringField(TEXT("independent_physical_primitive"),GetPathNameSafe(Physical));O->SetBoolField(TEXT("private_matches_independent"),Private&&Private==Physical);
        O->SetBoolField(TEXT("production_predicate_sampled"),!Passive);
        if(!Passive){QueryOrder.Add(MakeShared<FJsonValueString>(TEXT("production_predicate_invocation_at_live_pose_before_independent_queries")));double PredicateDistance=0;O->SetBoolField(TEXT("production_predicate_at_live_pose"),G->AuthoredGeometryMatches(D->GetDink(),*Target,UDinkGameplay::EAuthoredInteraction::Hit,&PredicateDistance));O->SetNumberField(TEXT("predicate_distance"),PredicateDistance);}
        O->SetNumberField(TEXT("runtime_hit_delay106_ms"),G->Data.HitFrameDelayMs(106));O->SetBoolField(TEXT("runtime_sequence106_exists"),G->Data.SeqExists(106));
        TArray<TSharedPtr<FJsonValue>> Frames;for(int32 I=1;I<=8;++I)
        {const auto* F=G->Data.FindFrame(106,I);if(!F)break;auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("frame"),I);R->SetNumberField(TEXT("delay_ms"),F->DelayMs);R->SetBoolField(TEXT("special"),F->bSpecial);R->SetBoolField(TEXT("empty"),F->bEmpty);Frames.Add(MakeShared<FJsonValueObject>(R));}
        O->SetNumberField(TEXT("runtime_contiguous_frames106_observed_up_to8"),Frames.Num());O->SetArrayField(TEXT("runtime_frames106_first8_contiguous"),Frames);
        const auto* Weapon=Story->FindInstance(G->GetWeaponInstance());auto A=MakeShared<FJsonObject>();A->SetNumberField(TEXT("weapon_id"),G->GetWeaponInstance());A->SetBoolField(TEXT("weapon_alive"),Weapon&&Weapon->IsAlive());
        if(Weapon){A->SetStringField(TEXT("weapon_script"),Weapon->Script.ToString());A->SetStringField(TEXT("procedure"),Weapon->Procedure.ToString());A->SetNumberField(TEXT("state"),int32(Weapon->State));A->SetBoolField(TEXT("has_use"),Story->HasProcedure(Weapon->Script,TEXT("use")));}
        A->SetNumberField(TEXT("seq"),D->GetDink().GetProp(TEXT("seq")));A->SetNumberField(TEXT("sprite_frame"),D->GetDink().GetProp(TEXT("frame")));A->SetNumberField(TEXT("nocontrol"),D->GetDink().GetProp(TEXT("nocontrol")));A->SetNumberField(TEXT("range"),D->GetDink().GetProp(TEXT("range")));A->SetNumberField(TEXT("base_hit"),D->GetDink().GetProp(TEXT("base_hit"),100));A->SetBoolField(TEXT("frozen"),D->GetDink().bFrozen);A->SetBoolField(TEXT("move_ignored"),PC->IsMoveInputIgnored());O->SetObjectField(TEXT("attack_state"),A);
        TArray<TSharedPtr<FJsonValue>> Queue;for(const auto& Pending:G->PendingHits)
        {auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("sprite"),Pending.Sprite);R->SetNumberField(TEXT("seq"),Pending.Seq);R->SetNumberField(TEXT("at_ms"),Pending.AtMs);const auto* S=D->FindSprite(Pending.Sprite);R->SetBoolField(TEXT("seq_match_now"),S&&S->bActive&&S->GetProp(TEXT("seq"))==Pending.Seq);Queue.Add(MakeShared<FJsonValueObject>(R));}O->SetArrayField(TEXT("pending_hits"),Queue);
        if(!Passive&&PhysicalCount==1&&Physical)
        {
            auto B=MakeShared<FJsonObject>();B->SetBoolField(TEXT("registered"),Physical->IsRegistered());B->SetBoolField(TEXT("physics_created"),Physical->IsPhysicsStateCreated());B->SetStringField(TEXT("class"),Physical->GetClass()->GetName());B->SetObjectField(TEXT("component_pose"),Pose(Physical->GetComponentTransform()));B->SetArrayField(TEXT("bounds_origin"),Vec(Physical->Bounds.Origin));B->SetArrayField(TEXT("bounds_extent"),Vec(Physical->Bounds.BoxExtent));B->SetStringField(TEXT("profile"),Physical->GetCollisionProfileName().ToString());B->SetNumberField(TEXT("object_type"),int32(Physical->GetCollisionObjectType()));
            const auto* BI=Physical->GetBodyInstance();B->SetBoolField(TEXT("body_instance_valid"),BI&&BI->IsValidBodyInstance());
            if(BI&&BI->IsValidBodyInstance())B->SetObjectField(TEXT("physics_global_pose_no_projection"),Pose(BI->GetUnrealWorldTransform(false,true)));
            B->SetNumberField(TEXT("component_collision_policy"),int32(Physical->GetCollisionEnabled()));B->SetNumberField(TEXT("visibility_response"),int32(Physical->GetCollisionResponseToChannel(ECC_Visibility)));B->SetNumberField(TEXT("pawn_response"),int32(Physical->GetCollisionResponseToChannel(ECC_Pawn)));O->SetObjectField(TEXT("physical"),B);
            const auto* Capsule=Hero->GetCapsuleComponent();const float BodyRadius=Capsule->GetScaledCapsuleRadius(),BodyHalfHeight=Capsule->GetScaledCapsuleHalfHeight();
            const double Scale=D->GetDink().GetProp(TEXT("range"))>0?D->GetDink().GetProp(TEXT("range"))/28.0:1.0;
            const float Radius=FMath::Max(1.f,float(G->AuthoredInteraction.AttackHalfWidthCm*Scale)),HalfHeight=FMath::Max(Radius,BodyHalfHeight-10.f);
            const double Reach=G->AuthoredInteraction.AttackReachCm*Scale;
            const FVector From=ExactRecordedQueries?FVector(221417.23312135597,-157284.77034535745,98):Capsule->GetComponentLocation();
            const FVector Forward=ExactRecordedQueries?FVector(1,0,0):Hero->GetActorForwardVector().GetSafeNormal2D();
            const FVector Start=From+Forward*(BodyRadius+Radius),End=From+Forward*(BodyRadius+FMath::Max(Reach,double(Radius*2))-Radius);
            O->SetNumberField(TEXT("body_radius"),BodyRadius);O->SetNumberField(TEXT("body_half_height"),BodyHalfHeight);O->SetNumberField(TEXT("configured_attack_reach"),G->AuthoredInteraction.AttackReachCm);O->SetNumberField(TEXT("configured_attack_half_width"),G->AuthoredInteraction.AttackHalfWidthCm);O->SetNumberField(TEXT("range_scale"),Scale);
            O->SetArrayField(TEXT("query_forward"),Vec(Forward));O->SetArrayField(TEXT("live_actor_forward"),Vec(Hero->GetActorForwardVector().GetSafeNormal2D()));O->SetArrayField(TEXT("query_minus_live_capsule_center"),Vec(From-Capsule->GetComponentLocation()));
            O->SetBoolField(TEXT("independent_queries_use_recorded_pose_without_moving_actor"),ExactRecordedQueries);O->SetArrayField(TEXT("query_from"),Vec(From));O->SetArrayField(TEXT("query_start"),Vec(Start));O->SetArrayField(TEXT("query_end"),Vec(End));O->SetNumberField(TEXT("attack_radius"),Radius);O->SetNumberField(TEXT("attack_half_height"),HalfHeight);O->SetBoolField(TEXT("production_selects_complex"),Physical->IsA<UStaticMeshComponent>());
            TArray<TSharedPtr<FJsonValue>> Sweeps;
            for(bool Complex:{false,true})
            {
                QueryOrder.Add(MakeShared<FJsonValueString>(Complex?TEXT("direct_component_complex"):TEXT("direct_component_simple")));
                FHitResult Direct;const bool DirectReturn=Physical->SweepComponent(Direct,Start,End,FQuat::Identity,FCollisionShape::MakeCapsule(Radius,HalfHeight),Complex);
                auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("complex"),Complex);R->SetObjectField(TEXT("direct_independent_component"),Hit(DirectReturn,Direct,Physical));
                FVector Surface=Direct.bStartPenetrating?Physical->Bounds.GetBox().GetClosestPointTo(From):Direct.ImpactPoint;
                if(DirectReturn)QueryOrder.Add(MakeShared<FJsonValueString>(Complex?TEXT("derived_los_after_complex_component"):TEXT("derived_los_after_simple_component")));
                FCollisionQueryParams SightParams(SCENE_QUERY_STAT(DinkNativeAttackSight),true,Hero);FHitResult Sight;const bool SightReturn=DirectReturn&&World->LineTraceSingleByChannel(Sight,From,Surface,ECC_Visibility,SightParams);
                R->SetArrayField(TEXT("source_los_surface"),Vec(Surface));R->SetObjectField(TEXT("source_los"),Hit(SightReturn,Sight,Physical));R->SetBoolField(TEXT("source_los_allows"),DirectReturn&&(!SightReturn||Sight.GetActor()==TargetActor||Sight.GetComponent()==Physical||Sight.Distance+1>=FVector::Distance(From,Surface)));
                FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkNativeAttackWorld),Complex,Hero);TArray<FHitResult> WorldHits;
                QueryOrder.Add(MakeShared<FJsonValueString>(Complex?TEXT("world_complex"):TEXT("world_simple")));
                const bool WorldReturn=World->SweepMultiByObjectType(WorldHits,Start,End,FQuat::Identity,FCollisionObjectQueryParams(Physical->GetCollisionObjectType()),FCollisionShape::MakeCapsule(Radius,HalfHeight),Params);
                R->SetBoolField(TEXT("world_native_return"),WorldReturn);R->SetBoolField(TEXT("world_find_initial_overlaps"),Params.bFindInitialOverlaps);TArray<TSharedPtr<FJsonValue>> WH;for(const auto& H:WorldHits){auto PerHit=Hit(WorldReturn,H,Physical);PerHit->RemoveField(TEXT("native_return"));WH.Add(MakeShared<FJsonValueObject>(PerHit));}R->SetArrayField(TEXT("world_hits"),WH);Sweeps.Add(MakeShared<FJsonValueObject>(R));
            }
            O->SetArrayField(TEXT("direct_vs_world_queries"),Sweeps);
        }
        O->SetArrayField(TEXT("query_call_order"),QueryOrder);
        O->SetObjectField(TEXT("hero_after"),Pose(Hero->GetActorTransform()));O->SetNumberField(TEXT("world_time_after"),World->GetTimeSeconds());O->SetNumberField(TEXT("story_ms_after"),Story->GetNowMs());
        O->SetBoolField(TEXT("observed_pose_clock_life_gold_unchanged"),Before.Equals(Hero->GetActorTransform(),0)&&WorldBefore==World->GetTimeSeconds()&&StoryBefore==Story->GetNowMs()&&LifeBefore==G->GetFact(TEXT("life"))&&GoldBefore==G->GetFact(TEXT("gold")));
        return O;
    }
    static FString Write(UWorld* World,const FString& Label,bool Exact,TSharedPtr<FJsonObject>* Captured=nullptr,bool Passive=false)
    {
        const auto O=Capture(World,Exact,Passive);O->SetStringField(TEXT("label"),Label);FString Nonce;FParse::Value(FCommandLine::Get(),TEXT("DinkQARunId="),Nonce);O->SetStringField(TEXT("nonce"),Nonce);if(Captured)*Captured=O;
        FString Text;if(!FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Text)))return FString();
        const FString Dir=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Automation/BarrelAttackNative"));IFileManager::Get().MakeDirectory(*Dir,true);
        const FString File=Dir/(Label+TEXT("-")+FGuid::NewGuid().ToString(EGuidFormats::Digits)+TEXT(".json"));
        return FFileHelper::SaveStringToFile(Text,*File,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_NoReplaceExisting)?File:FString();
    }
private:
    struct FQueueObserver
    {
        TWeakObjectPtr<UWorld> World;
        TWeakObjectPtr<ADinkGreyboxCharacter> Hero;
        int32 TargetHandle=0,LastSeq=INDEX_NONE;
        TArray<FDinkPendingHit> LastQueue;
        TArray<TSharedPtr<FJsonValue>> Rows;
        TSharedRef<FJsonObject> Payload=MakeShared<FJsonObject>();
        double StartReal=0;
        FString FinalPath,ArmedPath;
        FDelegateHandle Begin,End,Cleanup,Exit;
    };
    static TUniquePtr<FQueueObserver>& QueueObserver(){static TUniquePtr<FQueueObserver> Value;return Value;}
    static FString& LastObserverReceipt(){static FString Value;return Value;}
    static bool SaveObserverJson(const TSharedRef<FJsonObject>& Value,const FString& Path)
    {
        FString Text;return FJsonSerializer::Serialize(Value,TJsonWriterFactory<>::Create(&Text))&&
            FFileHelper::SaveStringToFile(Text,*Path,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_NoReplaceExisting);
    }
    static void ObserverBegin(){SampleObserver(TEXT("begin"));}
    static void ObserverEnd(){SampleObserver(TEXT("end"));}
    static void ObserverExit(){StopObserver(TEXT("engine_pre_exit"));}
    static void ObserverCleanup(UWorld* World,bool,bool)
    {if(QueueObserver()&&QueueObserver()->World.Get()==World)StopObserver(TEXT("world_cleanup"));}
    static void SampleObserver(const TCHAR* Phase)
    {
        auto* State=QueueObserver().Get();if(!State)return;
        const double Real=FPlatformTime::Seconds();
        if(Real-State->StartReal>=2.0){StopObserver(TEXT("time_limit"));return;}
        auto* World=State->World.Get();auto* Hero=State->Hero.Get();auto* PC=World?World->GetFirstPlayerController():nullptr;
        auto* Story=World&&World->GetGameInstance()?World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>():nullptr;
        auto* G=Story?Story->GetGameplay():nullptr;auto* D=Story?Story->GetDirector():nullptr;
        if(!World||!Hero||Hero->GetWorld()!=World||!PC||PC->GetPawn()!=Hero||!Story||!G||!D){StopObserver(TEXT("invalid_owned_context"));return;}
        if(D->GetDink().Screen!=31){StopObserver(TEXT("screen_changed"));return;}
        const auto& HeroSprite=D->GetDink();const int32 Seq=HeroSprite.GetProp(TEXT("seq"));
        bool Transition=Seq!=State->LastSeq||G->PendingHits.Num()!=State->LastQueue.Num();
        for(int32 I=0;!Transition&&I<G->PendingHits.Num();++I)
        {const auto& A=G->PendingHits[I];const auto& B=State->LastQueue[I];Transition=A.Sprite!=B.Sprite||A.Seq!=B.Seq||A.AtMs!=B.AtMs;}
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("phase"),Phase);Row->SetNumberField(TEXT("frame"),double(GFrameCounter));Row->SetNumberField(TEXT("real_elapsed_ms"),(Real-State->StartReal)*1000);
        Row->SetNumberField(TEXT("world_seconds"),World->GetTimeSeconds());Row->SetNumberField(TEXT("story_now_ms"),Story->GetNowMs());Row->SetNumberField(TEXT("gameplay_now_ms"),G->NowMs);Row->SetBoolField(TEXT("instant_mode"),Story->bInstantMode);
        Row->SetNumberField(TEXT("seq"),Seq);Row->SetNumberField(TEXT("sprite_frame"),HeroSprite.GetProp(TEXT("frame")));Row->SetNumberField(TEXT("nocontrol"),HeroSprite.GetProp(TEXT("nocontrol")));Row->SetBoolField(TEXT("attack_held"),G->bAttackHeld);
        Row->SetArrayField(TEXT("hero_location"),DinkAttackMetrology::Vec(Hero->GetActorLocation()));Row->SetArrayField(TEXT("actor_forward"),DinkAttackMetrology::Vec(Hero->GetActorForwardVector().GetSafeNormal2D()));
        Row->SetNumberField(TEXT("pending_total"),G->PendingHits.Num());TArray<TSharedPtr<FJsonValue>> Queue;
        for(int32 I=0;I<FMath::Min(16,G->PendingHits.Num());++I)
        {const auto& P=G->PendingHits[I];auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("sprite"),P.Sprite);R->SetNumberField(TEXT("seq"),P.Seq);R->SetNumberField(TEXT("at_ms"),P.AtMs);const auto* S=D->FindSprite(P.Sprite);R->SetBoolField(TEXT("current_seq_matches"),S&&S->bActive&&S->GetProp(TEXT("seq"))==P.Seq);Queue.Add(MakeShared<FJsonValueObject>(R));}
        Row->SetArrayField(TEXT("pending"),Queue);Row->SetBoolField(TEXT("pending_truncated"),G->PendingHits.Num()>16);
        const auto* Weapon=Story->FindInstance(G->GetWeaponInstance());Row->SetNumberField(TEXT("weapon_id"),G->GetWeaponInstance());if(Weapon)Row->SetStringField(TEXT("weapon_procedure"),Weapon->Procedure.ToString());
        const FDinkSprite* Target=nullptr;int32 TargetMatches=0;
        for(const auto& Pair:D->GetSprites())if(Pair.Value.Origin==FDinkOriginId(31,3)){Target=&Pair.Value;++TargetMatches;}
        if(TargetMatches!=1)Target=nullptr;
        Row->SetNumberField(TEXT("target_match_count"),TargetMatches);Row->SetNumberField(TEXT("initial_target_handle"),State->TargetHandle);Row->SetNumberField(TEXT("target_handle"),Target?Target->Handle:0);Row->SetBoolField(TEXT("target_present"),Target!=nullptr);Row->SetBoolField(TEXT("target_active"),Target&&Target->bActive);Row->SetNumberField(TEXT("target_nohit"),Target?Target->GetProp(TEXT("nohit")):-1);
        Row->SetBoolField(TEXT("queue_or_seq_transition"),Transition);Row->SetBoolField(TEXT("predicate_sampled"),false);Row->SetBoolField(TEXT("physical_queries_performed"),false);Row->SetBoolField(TEXT("fit_sampled"),Transition&&Target);
        if(Transition&&Target)
        {
            FString Error;auto Fit=MakeShared<FJsonObject>();auto* Primitive=G->FindHardnessFitPrimitive(*Target,&Error);
            Fit->SetBoolField(TEXT("has_instance"),G->HasHardnessFitInstance(*Target));Fit->SetStringField(TEXT("private_error"),Error);Fit->SetStringField(TEXT("primitive"),GetPathNameSafe(Primitive));
            Fit->SetBoolField(TEXT("uses_authored"),G->UsesAuthoredGeometry(HeroSprite,*Target));Row->SetObjectField(TEXT("fit"),Fit);
        }
        State->Rows.Add(MakeShared<FJsonValueObject>(Row));State->LastSeq=Seq;
        if(G->PendingHits.Num()>16){StopObserver(TEXT("pending_queue_exceeds_bound"));return;}
        State->LastQueue=G->PendingHits;
        if(State->Rows.Num()>=180)StopObserver(TEXT("row_limit"));
    }
public:
    static bool ObserverActive(){return QueueObserver().IsValid();}
    static FString ObserverReceipt(){return LastObserverReceipt();}
    static bool ArmObserver(UWorld* World,const FString& Label,FString& FinalPath,FString& Error,bool NoInputControl=false)
    {
        Error.Reset();if(ObserverActive()){Error=TEXT("already_armed_no_implicit_rearm");return false;}
        FString Nonce;FParse::Value(FCommandLine::Get(),TEXT("DinkQARunId="),Nonce);
        if(!World||!World->IsGameWorld()||(!NoInputControl&&Nonce.IsEmpty())){Error=TEXT("invalid_world_or_missing_nonce");return false;}
        auto* PC=World->GetFirstPlayerController();auto* Hero=PC?Cast<ADinkGreyboxCharacter>(PC->GetPawn()):nullptr;
        auto* Story=World->GetGameInstance()?World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>():nullptr;auto* D=Story?Story->GetDirector():nullptr;
        if(!Hero||!D||!Story->GetGameplay()||D->GetDink().Screen!=31){Error=TEXT("missing_owned031_context");return false;}
        int32 Handle=0,Count=0;for(const auto& Pair:D->GetSprites())if(Pair.Value.bActive&&Pair.Value.Origin==FDinkOriginId(31,3)){Handle=Pair.Key;++Count;}
        if(Count!=1){Error=TEXT("missing_or_ambiguous_existing_target");return false;}
        auto State=MakeUnique<FQueueObserver>();State->World=World;State->Hero=Hero;State->TargetHandle=Handle;
        const FString Dir=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Automation/BarrelAttackNative"));IFileManager::Get().MakeDirectory(*Dir,true);
        const FString Stem=Dir/(TEXT("observer-")+Label+TEXT("-")+FGuid::NewGuid().ToString(EGuidFormats::Digits));State->FinalPath=Stem+TEXT(".json");State->ArmedPath=Stem+TEXT(".armed.json");FinalPath=State->FinalPath;LastObserverReceipt()=FinalPath;
        State->Payload->SetNumberField(TEXT("schema"),1);State->Payload->SetStringField(TEXT("label"),Label);State->Payload->SetStringField(TEXT("nonce"),Nonce);State->Payload->SetStringField(TEXT("arming_authority"),NoInputControl?TEXT("native_no_input_control"):TEXT("explicit_nonce_console"));State->Payload->SetStringField(TEXT("scope"),TEXT("passive read-only begin/end snapshots; no sweeps/predicates during window; intra-frame dispatch not proven; no synthesized input, dispatch hook or gameplay mutation"));
        State->Payload->SetNumberField(TEXT("max_real_seconds"),2);State->Payload->SetNumberField(TEXT("max_rows"),180);State->Payload->SetStringField(TEXT("final_receipt"),State->FinalPath);
        State->StartReal=FPlatformTime::Seconds();State->Payload->SetNumberField(TEXT("armed_real_seconds"),State->StartReal);
        if(!SaveObserverJson(State->Payload,State->ArmedPath)){Error=TEXT("arm_receipt_write_failed");return false;}
        QueueObserver()=MoveTemp(State);auto* Active=QueueObserver().Get();
        Active->Begin=FCoreDelegates::OnBeginFrame.AddStatic(&FDinkBarrelAttackNativeDiagnostic::ObserverBegin);Active->End=FCoreDelegates::OnEndFrame.AddStatic(&FDinkBarrelAttackNativeDiagnostic::ObserverEnd);
        Active->Cleanup=FWorldDelegates::OnWorldCleanup.AddStatic(&FDinkBarrelAttackNativeDiagnostic::ObserverCleanup);Active->Exit=FCoreDelegates::OnEnginePreExit.AddStatic(&FDinkBarrelAttackNativeDiagnostic::ObserverExit);
        UE_LOG(LogTemp,Display,TEXT("DINK_ATTACK_OBSERVER_ARMED final=%s armed=%s"),*Active->FinalPath,*Active->ArmedPath);return true;
    }
    static void StopObserver(const TCHAR* Reason)
    {
        auto* State=QueueObserver().Get();if(!State)return;
        FCoreDelegates::OnBeginFrame.Remove(State->Begin);FCoreDelegates::OnEndFrame.Remove(State->End);FWorldDelegates::OnWorldCleanup.Remove(State->Cleanup);FCoreDelegates::OnEnginePreExit.Remove(State->Exit);
        State->Begin.Reset();State->End.Reset();State->Cleanup.Reset();State->Exit.Reset();
        State->Payload->SetStringField(TEXT("termination_reason"),Reason);State->Payload->SetNumberField(TEXT("finished_real_seconds"),FPlatformTime::Seconds());State->Payload->SetBoolField(TEXT("delegates_removed"),true);State->Payload->SetArrayField(TEXT("rows"),State->Rows);
        if(!SaveObserverJson(State->Payload,State->FinalPath))
        {FString Evidence;FJsonSerializer::Serialize(State->Payload,TJsonWriterFactory<>::Create(&Evidence));UE_LOG(LogTemp,Error,TEXT("DINK_ATTACK_OBSERVER_WRITE_FAILURE %s %s"),*State->FinalPath,*Evidence);}
        else UE_LOG(LogTemp,Display,TEXT("DINK_ATTACK_OBSERVER_COMPLETE %s"),*State->FinalPath);
        QueueObserver().Reset();
    }
};

void DinkStopAttackQueueObserver(){FDinkBarrelAttackNativeDiagnostic::StopObserver(TEXT("module_shutdown"));}

namespace
{
FAutoConsoleCommandWithWorldAndArgs NativeAttackCommand(TEXT("dink.QAReadAttack031"),TEXT("Read-only031: label nonce passive|full; passive before F, full only after observer completes; never attacks."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args,UWorld* World)
    {
        FString Nonce;FParse::Value(FCommandLine::Get(),TEXT("DinkQARunId="),Nonce);
        if(Args.Num()!=3||Nonce.IsEmpty()||Args[1]!=Nonce||Args[0].IsEmpty()||Args[0].Len()>64||!World||!World->IsGameWorld()||(Args[2]!=TEXT("passive")&&Args[2]!=TEXT("full")))return;
        for(TCHAR C:Args[0])if(!FChar::IsAlnum(C)&&C!=TEXT('-')&&C!=TEXT('_'))return;
        if(Args[2]==TEXT("full")&&FDinkBarrelAttackNativeDiagnostic::ObserverActive()){UE_LOG(LogTemp,Warning,TEXT("DINK_NATIVE_ATTACK_FULL_REFUSED observer_active"));return;}
        const FString Receipt=FDinkBarrelAttackNativeDiagnostic::Write(World,Args[0],false,nullptr,Args[2]==TEXT("passive"));
        UE_LOG(LogTemp,Display,TEXT("DINK_NATIVE_ATTACK_RECEIPT %s"),*Receipt);
    }));
FAutoConsoleCommandWithWorldAndArgs QueueObserverCommand(TEXT("dink.QAObserveAttack031"),TEXT("Arm read-only031 queue observer for2real seconds/180rows; label nonce. Does NOT press F."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args,UWorld* World)
    {
        FString Nonce;FParse::Value(FCommandLine::Get(),TEXT("DinkQARunId="),Nonce);
        if(Args.Num()!=2||Nonce.IsEmpty()||Args[1]!=Nonce||Args[0].IsEmpty()||Args[0].Len()>64)return;
        for(TCHAR C:Args[0])if(!FChar::IsAlnum(C)&&C!=TEXT('-')&&C!=TEXT('_'))return;
        FString Receipt,Error;if(!FDinkBarrelAttackNativeDiagnostic::ArmObserver(World,Args[0],Receipt,Error))UE_LOG(LogTemp,Warning,TEXT("DINK_ATTACK_OBSERVER_ARM_REFUSED %s"),*Error);
    }));
}
#endif

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
namespace
{
class FDinkExactAttack031Capture final : public IAutomationLatentCommand
{
public:
    explicit FDinkExactAttack031Capture(FAutomationTestBase* InTest,bool Control=false):Test(InTest),Began(FPlatformTime::Seconds()),ObserveNoInput(Control){}
    bool Update() override
    {
        UWorld* World=GEditor?GEditor->PlayWorld.Get():nullptr;
        auto FinishFailure=[&](const TCHAR* Why)
        {
            if(FDinkBarrelAttackNativeDiagnostic::ObserverActive())FDinkBarrelAttackNativeDiagnostic::StopObserver(TEXT("fixture_failure"));
            const FString Receipt=FDinkBarrelAttackNativeDiagnostic::Write(World,TEXT("fixture-failure"),true);
            Test->AddInfo(TEXT("native attack diagnostic receipt: ")+Receipt);Test->AddError(Why);return true;
        };
        if(FPlatformTime::Seconds()-Began>180)return FinishFailure(TEXT("read-only diagnostic setup timed out; no Story/clock flags changed"));
        auto* PC=World?World->GetFirstPlayerController():nullptr;
        auto* Hero=PC?Cast<ADinkGreyboxCharacter>(PC->GetPawn()):nullptr;
        auto* Story=World&&World->GetGameInstance()?World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>():nullptr;
        auto* Greybox=World?World->GetSubsystem<UDinkGreyboxSubsystem>():nullptr;
        if(!Hero||!Story||!Story->IsReady()||!Greybox||!World->HasBegunPlay()||World->IsPaused()||!Hero->HasActorBegunPlay()||
            !Hero->GetCapsuleComponent()->IsRegistered()||Story->bNewGamePending||FAssetCompilingManager::Get().GetNumRemainingAssets()!=0)return false;
        auto* G=Story->GetGameplay();auto* D=Story->GetDirector();if(!G||!D||G->IsHardnessLoading())return false;
        const auto* Physical=Greybox->FindScreenAt(Hero->GetActorLocation());
        if(!Physical||Greybox->GetCurrentScreen()!=Physical||D->GetDink().Screen!=Physical->ScreenNumber)return false;
        if(!Entered)
        {
            // Setup only: normal checked public entry, no direct actor transform,
            // fabricated handle, manual screen admission, instant mode or attack.
            if(!Greybox->GotoScreen(31,289.79972674268623f,316.1206770389154f))return FinishFailure(TEXT("public checked SCR031 entry refused"));
            Entered=true;return false;
        }
        if(D->GetDink().Screen!=31||Physical->ScreenNumber!=31||!G->UsesOriginalHardnessProjection(31))return false;
        if(ObserveNoInput)
        {
            if(!ObserverStarted)
            {
                FString Error;if(!FDinkBarrelAttackNativeDiagnostic::ArmObserver(World,TEXT("fixture-no-input"),ObserverPath,Error,true)){Test->AddError(Error);return true;}
                ObserverStarted=true;ObserverStart=FPlatformTime::Seconds();FString RefusedPath,RefusedError;
                Test->TestFalse(TEXT("an active observer cannot implicitly rearm"),FDinkBarrelAttackNativeDiagnostic::ArmObserver(World,TEXT("must-not-rearm"),RefusedPath,RefusedError,true));
                return false;
            }
            if(FDinkBarrelAttackNativeDiagnostic::ObserverActive())
            {
                if(FPlatformTime::Seconds()-ObserverStart>3){FDinkBarrelAttackNativeDiagnostic::StopObserver(TEXT("native_control_deadline"));Test->AddError(TEXT("observer exceeded own real-time bound"));return true;}
                return false;
            }
            FString Text;TSharedPtr<FJsonObject> Receipt;
            if(!Test->TestTrue(TEXT("finished observer receipt retained"),FFileHelper::LoadFileToString(Text,*ObserverPath)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Receipt)))return true;
            Test->AddInfo(TEXT("no-input observer receipt: ")+ObserverPath);
            const auto& Rows=Receipt->GetArrayField(TEXT("rows"));const FString Reason=Receipt->GetStringField(TEXT("termination_reason"));
            Test->TestTrue(TEXT("observer ends at own time/row cap without gameplay input"),Reason==TEXT("time_limit")||Reason==TEXT("row_limit"));
            Test->TestTrue(TEXT("observer rows are bounded and nonempty"),Rows.Num()>1&&Rows.Num()<=180);Test->TestTrue(TEXT("observer removes delegates before completion"),Receipt->GetBoolField(TEXT("delegates_removed")));
            bool Begin=false,End=false,NoInput=true,Within=true;
            for(const auto& Value:Rows)
            {const auto R=Value->AsObject();Begin|=R->GetStringField(TEXT("phase"))==TEXT("begin");End|=R->GetStringField(TEXT("phase"))==TEXT("end");NoInput&=!R->GetBoolField(TEXT("attack_held"))&&R->GetNumberField(TEXT("pending_total"))==0&&R->GetBoolField(TEXT("target_active"))&&R->GetNumberField(TEXT("target_nohit"))==0&&!R->GetBoolField(TEXT("predicate_sampled"))&&!R->GetBoolField(TEXT("physical_queries_performed"));Within&=R->GetNumberField(TEXT("real_elapsed_ms"))<2000;}
            Test->TestTrue(TEXT("actual begin and end frame phases sampled"),Begin&&End);Test->TestTrue(TEXT("no-input control keeps queue empty and barrel intact"),NoInput);Test->TestTrue(TEXT("all samples remain inside two real seconds"),Within);
            FDinkBarrelAttackNativeDiagnostic::StopObserver(TEXT("idempotent-control-stop"));FString After;
            Test->TestTrue(TEXT("completed observer cannot append/overwrite after stop"),!FDinkBarrelAttackNativeDiagnostic::ObserverActive()&&FFileHelper::LoadFileToString(After,*ObserverPath)&&After==Text);
            return true;
        }
        TSharedPtr<FJsonObject> Captured;
        const FString Receipt=FDinkBarrelAttackNativeDiagnostic::Write(World,TEXT("exact-recorded-query-fixture"),true,&Captured);
        // All assertions follow writing actual evidence. This is not an attack test.
        Test->AddInfo(TEXT("native attack diagnostic receipt: ")+Receipt);
        if(!Test->TestFalse(TEXT("actual diagnostic receipt saved without overwrite"),Receipt.IsEmpty())||!Captured)return true;
        if(Captured->HasField(TEXT("capture_error"))){Test->AddError(Captured->GetStringField(TEXT("capture_error")));return true;}
        Test->TestTrue(TEXT("read-only measurement preserves observed pose/clocks/life/gold"),Captured->GetBoolField(TEXT("observed_pose_clock_life_gold_unchanged")));
        Test->TestEqual(TEXT("runtime metadata special frame106 delay"),int32(Captured->GetNumberField(TEXT("runtime_hit_delay106_ms"))),175);
        Test->TestEqual(TEXT("independently registered source103 body is unique"),int32(Captured->GetNumberField(TEXT("independent_physical_count"))),1);
        const TArray<TSharedPtr<FJsonValue>>* Measurements=nullptr;
        if(!Captured->TryGetArrayField(TEXT("direct_vs_world_queries"),Measurements)||!Measurements)Test->AddError(TEXT("independent geometry measurements unavailable; receipt retained"));
        else Test->TestEqual(TEXT("both exact-recorded simple/complex measurements retained"),Measurements->Num(),2);
        Test->AddInfo(TEXT("Capture-only fixture: queries use exact recorded GPU coordinates; production predicate separately uses the live actor pose. No hit/drop success asserted."));
        return true;
    }
private:
    FAutomationTestBase* Test;double Began;bool Entered=false;bool ObserveNoInput=false,ObserverStarted=false;double ObserverStart=0;FString ObserverPath;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAttack031ReadOnlyMetrology,"Dink.Gameplay.BarrelAttackMetrology.ExactGPU031ReadOnly",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FDinkAttack031ReadOnlyMetrology::RunTest(const FString& Parameters)
{
    FString Map;GConfig->GetString(TEXT("/Script/EngineSettings.GameMapsSettings"),TEXT("GameDefaultMap"),Map,GEngineIni);
    const FString File=FPackageName::LongPackageNameToFilename(Map,FPackageName::GetMapPackageExtension());
    if(!TestTrue(TEXT("ordinary GameDefaultMap generated world exists"),!Map.IsEmpty()&&IFileManager::Get().FileExists(*File)))return false;
    if(!TestNotNull(TEXT("ordinary generated world loads"),UEditorLoadingAndSavingUtils::LoadMap(File)))return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkExactAttack031Capture(this));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAttack031QueueControl,"Dink.Gameplay.BarrelAttackMetrology.QueueObserverNoInput",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FDinkAttack031QueueControl::RunTest(const FString& Parameters)
{
    FString Map;GConfig->GetString(TEXT("/Script/EngineSettings.GameMapsSettings"),TEXT("GameDefaultMap"),Map,GEngineIni);
    if(!TestFalse(TEXT("ordinary GameDefaultMap is configured"),Map.IsEmpty()))return false;
    const FString File=FPackageName::LongPackageNameToFilename(Map,FPackageName::GetMapPackageExtension());
    if(!TestTrue(TEXT("ordinary generated world exists"),IFileManager::Get().FileExists(*File))||!TestNotNull(TEXT("ordinary world loads"),UEditorLoadingAndSavingUtils::LoadMap(File)))return false;
    FAssetCompilingManager::Get().FinishAllCompilation();ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkExactAttack031Capture(this,true));ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());return true;
}
#endif
