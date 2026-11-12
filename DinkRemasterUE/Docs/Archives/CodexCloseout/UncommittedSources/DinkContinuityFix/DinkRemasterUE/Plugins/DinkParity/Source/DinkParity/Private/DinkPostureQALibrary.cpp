#include "DinkPostureQALibrary.h"
#if WITH_EDITOR
#include "DinkEarlyPostureAnimInstance.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Engine/SkeletalMesh.h"
#include "AnimGraphNode_ApplyAdditive.h"
#include "AnimGraphNode_LinkedInputPose.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_SequenceEvaluator.h"
#include "AnimationGraphSchema.h"
#include "Factories/AnimBlueprintFactory.h"
#include "K2Node_VariableGet.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Misc/PackageName.h"
#include "AssetCompilingManager.h"

namespace
{
const FString QAPrefix=TEXT("/Game/DinkQA/Posture/");
bool IsQAAsset(const UObject* Object)
{
    return Object && Object->GetOutermost()->GetName().StartsWith(QAPrefix);
}
template<class T> T* AddNode(UEdGraph* Graph)
{
    FGraphNodeCreator<T> Creator(*Graph);
    T* Node=Creator.CreateNode(); Creator.Finalize(); return Node;
}
UEdGraphPin* Output(UEdGraphNode* Node)
{
    for (auto* Pin:Node->Pins) if (Pin->Direction==EGPD_Output) return Pin;
    return nullptr;
}
}
UAnimBlueprint* UDinkPostureQALibrary::CreatePostureGraph(USkeletalMesh* ReferenceMesh,UAnimSequence* Target,UAnimSequence* Reference,const FString& PackageName)
{
    // Target/reference must be explicitly imported QA copies. Never modify production clips.
    if (!IsQAAsset(Target) || !IsQAAsset(Reference) || Target==Reference ||
        !Target->GetSkeleton() || Target->GetSkeleton()!=Reference->GetSkeleton() ||
        !ReferenceMesh || ReferenceMesh->GetRefSkeleton().GetNum()!=89 ||
        ReferenceMesh->GetSkeleton()!=Target->GetSkeleton() ||
        !PackageName.StartsWith(QAPrefix) || !FPackageName::IsValidLongPackageName(PackageName) ||
        FindPackage(nullptr,*PackageName) || FPackageName::DoesPackageExist(PackageName) ||
        Target->GetPlayLength()<=0 || Reference->GetNumberOfSampledKeys()<1) { UE_LOG(LogTemp,Display,TEXT("PostureQA preflight refused: target=%s reference=%s bones=%d dest=%s"),*GetNameSafe(Target),*GetNameSafe(Reference),Target && Target->GetSkeleton()?Target->GetSkeleton()->GetReferenceSkeleton().GetNum():-1,*PackageName); return nullptr; }
    Target->Modify();
    Target->AdditiveAnimType=AAT_LocalSpaceBase;
    Target->RefPoseType=ABPT_AnimFrame;
    Target->RefPoseSeq=Reference; Target->RefFrameIndex=0; Target->bEnableRootMotion=false;
    Target->PostEditChange();
    FAssetCompilingManager::Get().FinishAllCompilation();
    if (!Target->IsValidAdditive()) return nullptr;
    auto* Factory=NewObject<UAnimBlueprintFactory>();
    Factory->ParentClass=UDinkEarlyPostureAnimInstance::StaticClass();
    Factory->TargetSkeleton=Target->GetSkeleton();
    auto* Package=CreatePackage(*PackageName);
    auto* BP=Cast<UAnimBlueprint>(Factory->FactoryCreateNew(UAnimBlueprint::StaticClass(),Package,
        *FPackageName::GetLongPackageAssetName(PackageName),RF_Public|RF_Standalone,nullptr,GWarn));
    if (!BP) return nullptr;
    TArray<UEdGraph*> Graphs; BP->GetAllGraphs(Graphs);
    UEdGraph* Graph=nullptr; UAnimGraphNode_Root* Root=nullptr;
    for (auto* Candidate:Graphs)
        for (const auto& Node:Candidate->Nodes)
            if (auto* R=Cast<UAnimGraphNode_Root>(Node.Get())) { Graph=Candidate; Root=R; }
    if (!Graph || !Root) { UE_LOG(LogTemp,Display,TEXT("PostureQA missing root graph")); return nullptr; }
    auto* Input=AddNode<UAnimGraphNode_LinkedInputPose>(Graph);
    Input->Node.Name=FAnimNode_LinkedInputPose::DefaultInputPoseName;
    auto* Eval=AddNode<UAnimGraphNode_SequenceEvaluator>(Graph);
    Eval->Node.SetSequence(Target); Eval->Node.SetExplicitTime(Target->GetPlayLength());
    Eval->Node.SetShouldLoop(false); Eval->Node.SetGroupMethod(EAnimSyncMethod::DoNotSync);
    auto* Add=AddNode<UAnimGraphNode_ApplyAdditive>(Graph);
    auto* Weight=AddNode<UK2Node_VariableGet>(Graph);
    Weight->VariableReference.SetSelfMember(GET_MEMBER_NAME_CHECKED(UDinkEarlyPostureAnimInstance,PostureWeight));
    Weight->ReconstructNode();
    const auto* Schema=Graph->GetSchema();
    auto Connect=[Schema](UEdGraphPin* A,UEdGraphPin* B){ return A && B && Schema->TryCreateConnection(A,B); };
    if (!Connect(Output(Input),Add->FindPin(TEXT("Base"))) ||
        !Connect(Output(Eval),Add->FindPin(TEXT("Additive"))) ||
        !Connect(Output(Weight),Add->FindPin(TEXT("Alpha"))) ||
        !Connect(Output(Add),Root->FindPin(TEXT("Result"))))
    { for (auto* N:TArray<UEdGraphNode*>{Input,Eval,Add,Weight,Root}) for (auto* P:N->Pins) UE_LOG(LogTemp,Display,TEXT("PostureQA pin %s.%s direction%d"),*N->GetClass()->GetName(),*P->PinName.ToString(),int32(P->Direction)); return nullptr; }
    // ExplicitTime is a shown pin; set it too so compilation does not replace the configured value with zero.
    auto* TimePin=Eval->FindPin(TEXT("ExplicitTime"));
    if (!TimePin) { UE_LOG(LogTemp,Display,TEXT("PostureQA missing evaluator time pin")); return nullptr; }
    Schema->TrySetDefaultValue(*TimePin,FString::Printf(TEXT("%.9g"),double(Target->GetPlayLength())));
    if (!FMath::IsNearlyEqual(FCString::Atod(*TimePin->DefaultValue),double(Target->GetPlayLength()),1.e-6) ||
        !Eval->Node.GetTeleportToExplicitTime()) { UE_LOG(LogTemp,Display,TEXT("PostureQA evaluator time=%s expected=%f teleport=%d"),*TimePin->DefaultValue,Target->GetPlayLength(),Eval->Node.GetTeleportToExplicitTime()); return nullptr; }
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
    FKismetEditorUtilities::CompileBlueprint(BP);
    UE_LOG(LogTemp,Display,TEXT("PostureQA compiled status=%d"),int32(BP->Status));
    return BP->Status==BS_UpToDate ? BP : nullptr;
}
bool UDinkPostureQALibrary::VerifyPostureGraph(UAnimBlueprint* BP,UAnimSequence* Target,UAnimSequence* Reference)
{
    if (!IsQAAsset(BP) || !IsQAAsset(Target) || !IsQAAsset(Reference) || !BP->GeneratedClass ||
        BP->ParentClass!=UDinkEarlyPostureAnimInstance::StaticClass() ||
        BP->GeneratedClass->GetSuperClass()!=UDinkEarlyPostureAnimInstance::StaticClass() ||
        BP->TargetSkeleton!=Target->GetSkeleton() || Target->GetSkeleton()!=Reference->GetSkeleton() ||
        Target->AdditiveAnimType!=AAT_LocalSpaceBase || Target->RefPoseType!=ABPT_AnimFrame ||
        Target->RefPoseSeq!=Reference || Target->RefFrameIndex!=0 || Target->bEnableRootMotion) return false;
    TArray<UEdGraph*> Graphs; BP->GetAllGraphs(Graphs);
    UAnimGraphNode_LinkedInputPose* Input=nullptr; UAnimGraphNode_SequenceEvaluator* Eval=nullptr;
    UAnimGraphNode_ApplyAdditive* Add=nullptr; UAnimGraphNode_Root* Root=nullptr; UK2Node_VariableGet* Weight=nullptr;
    for (auto* G:Graphs) for (const auto& N:G->Nodes)
    {
        if (auto* P=Cast<UAnimGraphNode_LinkedInputPose>(N.Get())) Input=P;
        if (auto* P=Cast<UAnimGraphNode_SequenceEvaluator>(N.Get())) Eval=P;
        if (auto* P=Cast<UAnimGraphNode_ApplyAdditive>(N.Get())) Add=P;
        if (auto* P=Cast<UAnimGraphNode_Root>(N.Get())) Root=P;
        if (auto* P=Cast<UK2Node_VariableGet>(N.Get())) Weight=P;
    }
    if (!Input || !Eval || !Add || !Root || !Weight ||
        Input->Node.Name!=FAnimNode_LinkedInputPose::DefaultInputPoseName ||
        Eval->Node.IsLooping() || Eval->Node.GetSequence()!=Target ||
        !Eval->Node.GetTeleportToExplicitTime() || Eval->Node.GetGroupMethod()!=EAnimSyncMethod::DoNotSync ||
        Weight->VariableReference.GetMemberName()!=GET_MEMBER_NAME_CHECKED(UDinkEarlyPostureAnimInstance,PostureWeight)) return false;
    auto Linked=[](UEdGraphPin* A,UEdGraphPin* B){return A && B && A->LinkedTo.Num()==1 && B->LinkedTo.Num()==1 && A->LinkedTo[0]==B && B->LinkedTo[0]==A;};
    auto* Time=Eval->FindPin(TEXT("ExplicitTime"));
    return Time && Time->LinkedTo.IsEmpty() && FMath::IsNearlyEqual(FCString::Atod(*Time->DefaultValue),double(Target->GetPlayLength()),1.e-6) &&
        Linked(Output(Input),Add->FindPin(TEXT("Base"))) && Linked(Output(Eval),Add->FindPin(TEXT("Additive"))) &&
        Linked(Output(Weight),Add->FindPin(TEXT("Alpha"))) && Linked(Output(Add),Root->FindPin(TEXT("Result")));
}
#endif
