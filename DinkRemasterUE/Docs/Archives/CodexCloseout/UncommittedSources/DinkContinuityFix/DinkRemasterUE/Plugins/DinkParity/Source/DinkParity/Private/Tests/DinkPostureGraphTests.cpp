#include "DinkTestHelpers.h"
#include "DinkPostureQALibrary.h"
#include "DinkEarlyPostureAnimInstance.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Tests/AutomationEditorCommon.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPostureGraphQA,"Dink.Art.Posture.QAGraphInputEvaluation",DINK_TEST_FLAGS)
bool FDinkPostureGraphQA::RunTest(const FString&)
{
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Dink/Hero/SK_Dink.SK_Dink"));
    auto* Base=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle.MM_Idle"));
    if (!TestNotNull(TEXT("hero mesh"),Mesh) || !TestNotNull(TEXT("stock fixture clip"),Base)) return false;
    const FString Prefix=TEXT("/Game/DinkQA/Posture/Transient_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    // Copy raw animation model data into fresh QA sequences. Imported source metadata
    // is irrelevant to this synthetic test and must not be duplicated with pending load flags.
    auto CopyModel=[&](const TCHAR* Name)
    {
        auto* Sequence=NewObject<UAnimSequence>(CreatePackage(*(Prefix+TEXT("/")+Name)),Name,RF_Public|RF_Standalone);
        Sequence->SetSkeleton(Base->GetSkeleton());
        Sequence->GetController().InitializeModel();
        auto& Controller=Sequence->GetController();
        const auto* Model=Base->GetDataModel();
        Controller.OpenBracket(FText::FromString(TEXT("Synthetic QA bone motion")),false);
        Controller.SetFrameRate(Model->GetFrameRate(),false);
        Controller.SetNumberOfFrames(FFrameNumber(Model->GetNumberOfFrames()),false);
        TArray<FName> Names; Model->GetBoneTrackNames(Names);
        for (const FName Bone:Names)
        {
            TArray<FTransform> Keys; Model->GetBoneTrackTransforms(Bone,Keys);
            TArray<FVector3f> Positions,Scales; TArray<FQuat4f> Rotations;
            for (const auto& Key:Keys) { Positions.Add(FVector3f(Key.GetLocation())); Rotations.Add(FQuat4f(Key.GetRotation())); Scales.Add(FVector3f(Key.GetScale3D())); }
            Controller.AddBoneCurve(Bone,false);
            Controller.SetBoneTrackKeys(Bone,Positions,Rotations,Scales,false);
        }
        Controller.NotifyPopulated(); Controller.CloseBracket(false);
        return Sequence;
    };
    auto* Ref=CopyModel(TEXT("Reference"));
    auto* Target=CopyModel(TEXT("Target"));
    auto* BP=UDinkPostureQALibrary::CreatePostureGraph(Mesh,Target,Ref,Prefix+TEXT("/PostProcess"));
    if (!TestNotNull(TEXT("native graph compiles using explicit mesh89/shared skeleton"),BP)) return false;
    TestTrue(TEXT("native graph/reference/class wiring verified"),UDinkPostureQALibrary::VerifyPostureGraph(BP,Target,Ref));
    TestNull(TEXT("existing destination refused"),UDinkPostureQALibrary::CreatePostureGraph(Mesh,Target,Ref,Prefix+TEXT("/PostProcess")));
    TestNull(TEXT("production target refused"),UDinkPostureQALibrary::CreatePostureGraph(Mesh,Base,Ref,Prefix+TEXT("/Forbidden")));
    UWorld* W=FAutomationEditorCommonUtils::CreateNewMap();
    auto* Actor=W->SpawnActor<AActor>();
    auto* C=NewObject<USkeletalMeshComponent>(Actor);
    Actor->AddInstanceComponent(C); Actor->SetRootComponent(C);
    C->SetSkeletalMeshAsset(Mesh); C->RegisterComponent();
    C->SetAnimationMode(EAnimationMode::AnimationSingleNode); C->PlayAnimation(Base,false);
    C->SetPosition(0.f,false); C->TickAnimation(.016f,false); C->RefreshBoneTransforms();
    TArray<FTransform> Baseline;
    C->SetOverridePostProcessAnimBP(TSubclassOf<UAnimInstance>(BP->GeneratedClass.Get()));
    // Installing an override legitimately reinitializes animation instances once. Establish
    // the action/locomotion input after installation, as normal character setup does.
    C->PlayAnimation(Base,false);
    UAnimInstance* Main=C->GetAnimInstance();
    C->SetDisablePostProcessBlueprint(true);
    C->SetPosition(0.f,false); C->TickAnimation(.016f,false); C->RefreshBoneTransforms();
    Baseline=C->GetComponentSpaceTransforms();
    C->SetDisablePostProcessBlueprint(false);
    auto* Post=Cast<UDinkEarlyPostureAnimInstance>(C->GetPostProcessInstance());
    if (!TestNotNull(TEXT("actual postprocess installed"),Post)) { Actor->Destroy(); return false; }
    auto Sample=[&](float Weight,float Time=0.f)
    {
        C->SetPosition(Time,false); C->TickAnimation(.016f,false);
        // Test-only override after NativeUpdate and before evaluation. Gameplay policy is tested separately.
        Post->PostureWeight=Weight; C->RefreshBoneTransforms();
        return TArray<FTransform>(C->GetComponentSpaceTransforms());
    };
    const auto Zero=Sample(0),Half=Sample(.5f),Full=Sample(1);
    TestTrue(TEXT("SingleNode base instance retained"),Main==C->GetAnimInstance());
    TestEqual(TEXT("same actual mesh bone count"),Zero.Num(),Baseline.Num());
    const auto Changed=Sample(0,Base->GetPlayLength()*.5f);
    double ZeroError=0,ZeroAngle=0,HalfDelta=0,FullDelta=0,InputDelta=0;
    for (int32 I=0;I<Zero.Num() && I<Baseline.Num();++I)
    {
        ZeroError=FMath::Max(ZeroError,FVector::Dist(Zero[I].GetLocation(),Baseline[I].GetLocation()));
        ZeroAngle=FMath::Max(ZeroAngle,Zero[I].GetRotation().AngularDistance(Baseline[I].GetRotation()));
        InputDelta+=FVector::Dist(Changed[I].GetLocation(),Zero[I].GetLocation());
        HalfDelta+=FVector::Dist(Half[I].GetLocation(),Zero[I].GetLocation());
        FullDelta+=FVector::Dist(Full[I].GetLocation(),Zero[I].GetLocation());
    }
    TestTrue(TEXT("weight0 forwards base component pose within .01cm"),ZeroError<.01);
    TestTrue(TEXT("weight0 forwards base rotations"),ZeroAngle<1.e-5);
    TestTrue(TEXT("changed incoming animation time reaches output"),InputDelta>.01);
    TestTrue(TEXT("weight1 evaluates nonzero synthetic additive pose"),FullDelta>.01);
    TestTrue(TEXT("half weight produces intermediate actual pose"),HalfDelta>0 && HalfDelta<FullDelta);
    AddInfo(FString::Printf(TEXT("Synthetic fixture only: zeroMaxCm=%g halfSumCm=%g fullSumCm=%g. Not authored Hero acceptance."),ZeroError,HalfDelta,FullDelta));
    Actor->Destroy();
    return true;
}
