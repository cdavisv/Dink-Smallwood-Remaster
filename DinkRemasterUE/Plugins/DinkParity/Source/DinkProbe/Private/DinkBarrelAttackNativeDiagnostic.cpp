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
    static TSharedRef<FJsonObject> Capture(UWorld* World,bool ExactRecordedQueries)
    {
        using namespace DinkAttackMetrology;
        auto O=MakeShared<FJsonObject>();O->SetNumberField(TEXT("schema"),1);O->SetStringField(TEXT("scope"),TEXT("Read-only diagnostic, not hit/drop acceptance; no attack/scheduling changes"));
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
        double PredicateDistance=0;O->SetBoolField(TEXT("production_predicate_at_live_pose"),G->AuthoredGeometryMatches(D->GetDink(),*Target,UDinkGameplay::EAuthoredInteraction::Hit,&PredicateDistance));O->SetNumberField(TEXT("predicate_distance"),PredicateDistance);
        O->SetNumberField(TEXT("runtime_hit_delay106_ms"),G->Data.HitFrameDelayMs(106));O->SetBoolField(TEXT("runtime_sequence106_exists"),G->Data.SeqExists(106));
        TArray<TSharedPtr<FJsonValue>> Frames;for(int32 I=1;I<=8;++I)
        {const auto* F=G->Data.FindFrame(106,I);if(!F)break;auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("frame"),I);R->SetNumberField(TEXT("delay_ms"),F->DelayMs);R->SetBoolField(TEXT("special"),F->bSpecial);R->SetBoolField(TEXT("empty"),F->bEmpty);Frames.Add(MakeShared<FJsonValueObject>(R));}
        O->SetNumberField(TEXT("runtime_contiguous_frames106_observed_up_to8"),Frames.Num());O->SetArrayField(TEXT("runtime_frames106_first8_contiguous"),Frames);
        const auto* Weapon=Story->FindInstance(G->GetWeaponInstance());auto A=MakeShared<FJsonObject>();A->SetNumberField(TEXT("weapon_id"),G->GetWeaponInstance());A->SetBoolField(TEXT("weapon_alive"),Weapon&&Weapon->IsAlive());
        if(Weapon){A->SetStringField(TEXT("weapon_script"),Weapon->Script.ToString());A->SetStringField(TEXT("procedure"),Weapon->Procedure.ToString());A->SetNumberField(TEXT("state"),int32(Weapon->State));A->SetBoolField(TEXT("has_use"),Story->HasProcedure(Weapon->Script,TEXT("use")));}
        A->SetNumberField(TEXT("seq"),D->GetDink().GetProp(TEXT("seq")));A->SetNumberField(TEXT("sprite_frame"),D->GetDink().GetProp(TEXT("frame")));A->SetNumberField(TEXT("nocontrol"),D->GetDink().GetProp(TEXT("nocontrol")));A->SetNumberField(TEXT("range"),D->GetDink().GetProp(TEXT("range")));A->SetNumberField(TEXT("base_hit"),D->GetDink().GetProp(TEXT("base_hit"),100));A->SetBoolField(TEXT("frozen"),D->GetDink().bFrozen);A->SetBoolField(TEXT("move_ignored"),PC->IsMoveInputIgnored());O->SetObjectField(TEXT("attack_state"),A);
        TArray<TSharedPtr<FJsonValue>> Queue;for(const auto& Pending:G->PendingHits)
        {auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("sprite"),Pending.Sprite);R->SetNumberField(TEXT("seq"),Pending.Seq);R->SetNumberField(TEXT("at_ms"),Pending.AtMs);const auto* S=D->FindSprite(Pending.Sprite);R->SetBoolField(TEXT("seq_match_now"),S&&S->bActive&&S->GetProp(TEXT("seq"))==Pending.Seq);Queue.Add(MakeShared<FJsonValueObject>(R));}O->SetArrayField(TEXT("pending_hits"),Queue);
        if(PhysicalCount==1&&Physical)
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
                FHitResult Direct;const bool DirectReturn=Physical->SweepComponent(Direct,Start,End,FQuat::Identity,FCollisionShape::MakeCapsule(Radius,HalfHeight),Complex);
                auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("complex"),Complex);R->SetObjectField(TEXT("direct_independent_component"),Hit(DirectReturn,Direct,Physical));
                FVector Surface=Direct.bStartPenetrating?Physical->Bounds.GetBox().GetClosestPointTo(From):Direct.ImpactPoint;
                FCollisionQueryParams SightParams(SCENE_QUERY_STAT(DinkNativeAttackSight),true,Hero);FHitResult Sight;const bool SightReturn=DirectReturn&&World->LineTraceSingleByChannel(Sight,From,Surface,ECC_Visibility,SightParams);
                R->SetArrayField(TEXT("source_los_surface"),Vec(Surface));R->SetObjectField(TEXT("source_los"),Hit(SightReturn,Sight,Physical));R->SetBoolField(TEXT("source_los_allows"),DirectReturn&&(!SightReturn||Sight.GetActor()==TargetActor||Sight.GetComponent()==Physical||Sight.Distance+1>=FVector::Distance(From,Surface)));
                FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkNativeAttackWorld),Complex,Hero);TArray<FHitResult> WorldHits;
                const bool WorldReturn=World->SweepMultiByObjectType(WorldHits,Start,End,FQuat::Identity,FCollisionObjectQueryParams(Physical->GetCollisionObjectType()),FCollisionShape::MakeCapsule(Radius,HalfHeight),Params);
                R->SetBoolField(TEXT("world_native_return"),WorldReturn);R->SetBoolField(TEXT("world_find_initial_overlaps"),Params.bFindInitialOverlaps);TArray<TSharedPtr<FJsonValue>> WH;for(const auto& H:WorldHits){auto PerHit=Hit(WorldReturn,H,Physical);PerHit->RemoveField(TEXT("native_return"));WH.Add(MakeShared<FJsonValueObject>(PerHit));}R->SetArrayField(TEXT("world_hits"),WH);Sweeps.Add(MakeShared<FJsonValueObject>(R));
            }
            O->SetArrayField(TEXT("direct_vs_world_queries"),Sweeps);
        }
        O->SetObjectField(TEXT("hero_after"),Pose(Hero->GetActorTransform()));O->SetNumberField(TEXT("world_time_after"),World->GetTimeSeconds());O->SetNumberField(TEXT("story_ms_after"),Story->GetNowMs());
        O->SetBoolField(TEXT("observed_pose_clock_life_gold_unchanged"),Before.Equals(Hero->GetActorTransform(),0)&&WorldBefore==World->GetTimeSeconds()&&StoryBefore==Story->GetNowMs()&&LifeBefore==G->GetFact(TEXT("life"))&&GoldBefore==G->GetFact(TEXT("gold")));
        return O;
    }
    static FString Write(UWorld* World,const FString& Label,bool Exact,TSharedPtr<FJsonObject>* Captured=nullptr)
    {
        const auto O=Capture(World,Exact);if(Captured)*Captured=O;
        FString Text;if(!FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Text)))return FString();
        const FString Dir=FPaths::ProjectSavedDir()/TEXT("Automation/BarrelAttackNative");IFileManager::Get().MakeDirectory(*Dir,true);
        const FString File=Dir/(Label+TEXT("-")+FGuid::NewGuid().ToString(EGuidFormats::Digits)+TEXT(".json"));
        return FFileHelper::SaveStringToFile(Text,*File,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_NoReplaceExisting)?File:FString();
    }
};

namespace
{
FAutoConsoleCommandWithWorldAndArgs NativeAttackCommand(TEXT("dink.QAReadAttack031"),TEXT("Read-only developer attack diagnostic: label and exact DinkQARunId nonce; does not attack."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args,UWorld* World)
    {
        FString Nonce;FParse::Value(FCommandLine::Get(),TEXT("DinkQARunId="),Nonce);
        if(Args.Num()!=2||Nonce.IsEmpty()||Args[1]!=Nonce||Args[0].IsEmpty()||Args[0].Len()>64||!World||!World->IsGameWorld())return;
        for(TCHAR C:Args[0])if(!FChar::IsAlnum(C)&&C!=TEXT('-')&&C!=TEXT('_'))return;
        const FString Receipt=FDinkBarrelAttackNativeDiagnostic::Write(World,Args[0],false);
        UE_LOG(LogTemp,Display,TEXT("DINK_NATIVE_ATTACK_RECEIPT %s"),*Receipt);
    }));
}
#endif

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
namespace
{
class FDinkExactAttack031Capture final : public IAutomationLatentCommand
{
public:
    explicit FDinkExactAttack031Capture(FAutomationTestBase* InTest):Test(InTest),Began(FPlatformTime::Seconds()){}
    bool Update() override
    {
        UWorld* World=GEditor?GEditor->PlayWorld.Get():nullptr;
        auto FinishFailure=[&](const TCHAR* Why)
        {
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
    FAutomationTestBase* Test;double Began;bool Entered=false;
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
#endif
