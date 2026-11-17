// Art review tool: puts a static mesh in the hero's hand so a weapon mesh and its grip transform can be judged in a
// capture before the runtime attach by item exists (bug A203, art row DS-04). Not gameplay; not in shipping builds.
#include "DinkCoreModule.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "ReferenceSkeleton.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"

#if !UE_BUILD_SHIPPING
static FAutoConsoleCommandWithWorldAndArgs GDinkHeroHoldCommand(
	TEXT("dink.Hero.Hold"),
	TEXT("dink.Hero.Hold <static mesh object path | off> [bone=hand_r] [x y z pitch yaw roll]: review only; attaches the mesh to the bone of the hero's body with that relative transform (cm, degrees). One mesh per bone; off removes all."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		static const FName HeldTag(TEXT("DinkHeroHoldReview"));
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		APawn* Pawn = PC ? PC->GetPawn() : nullptr;
		if (!Pawn || Args.Num() < 1)
		{
			UE_LOG(LogDink, Display, TEXT("usage: dink.Hero.Hold <mesh path | off> [bone] [x y z pitch yaw roll]"));
			return;
		}
		const FName Bone(Args.Num() > 1 ? *Args[1] : TEXT("hand_r"));
		TArray<UStaticMeshComponent*> Old;
		Pawn->GetComponents<UStaticMeshComponent>(Old);
		const bool bOff = Args[0].Equals(TEXT("off"), ESearchCase::IgnoreCase);
		for (UStaticMeshComponent* C : Old)
		{
			if (C && C->ComponentHasTag(HeldTag) && (bOff || C->GetAttachSocketName() == Bone)) C->DestroyComponent();
		}
		if (bOff) return;
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Args[0], nullptr, LOAD_NoWarn | LOAD_Quiet);
		USkeletalMeshComponent* Body = nullptr;
		TArray<USkeletalMeshComponent*> Bodies;
		Pawn->GetComponents<USkeletalMeshComponent>(Bodies);
		for (USkeletalMeshComponent* C : Bodies)
		{
			if (C && C->IsVisible() && C->GetSkeletalMeshAsset() && C->GetBoneIndex(Bone) != INDEX_NONE && (!Body || !C->LeaderPoseComponent.IsValid()))
			{
				Body = C;
				if (!C->LeaderPoseComponent.IsValid()) break;
			}
		}
		if (!Mesh || !Body)
		{
			UE_LOG(LogDink, Warning, TEXT("dink.Hero.Hold: %s"), !Mesh ? *FString::Printf(TEXT("no static mesh %s"), *Args[0]) : *FString::Printf(TEXT("no visible hero body with bone %s"), *Bone.ToString()));
			return;
		}
		FVector At = FVector::ZeroVector;
		FRotator Turn = FRotator::ZeroRotator;
		if (Args.Num() >= 5) At = FVector(FCString::Atod(*Args[2]), FCString::Atod(*Args[3]), FCString::Atod(*Args[4]));
		if (Args.Num() >= 8) Turn = FRotator(FCString::Atod(*Args[5]), FCString::Atod(*Args[6]), FCString::Atod(*Args[7]));
		UStaticMeshComponent* Held = NewObject<UStaticMeshComponent>(Pawn);
		Held->SetMobility(EComponentMobility::Movable);
		Held->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Held->SetGenerateOverlapEvents(false);
		Held->SetCanEverAffectNavigation(false);
		Held->ComponentTags.Add(HeldTag);
		Held->SetStaticMesh(Mesh);
		Held->SetupAttachment(Body, Bone);
		Held->SetRelativeLocationAndRotation(At, Turn);
		Pawn->AddInstanceComponent(Held);
		Held->RegisterComponent();
		const FTransform BoneWorld = Body->GetSocketTransform(Bone, RTS_Component);
		UE_LOG(LogDink, Display, TEXT("dink.Hero.Hold: %s on %s of %s at (%s) (%s); bone in component space: %s | X %s Y %s Z %s"), *Mesh->GetName(), *Bone.ToString(), *Body->GetName(),
			*At.ToCompactString(), *Turn.ToCompactString(), *BoneWorld.GetLocation().ToCompactString(),
			*BoneWorld.GetUnitAxis(EAxis::X).ToCompactString(), *BoneWorld.GetUnitAxis(EAxis::Y).ToCompactString(), *BoneWorld.GetUnitAxis(EAxis::Z).ToCompactString());
		// The hand's own frame, for whoever derives a grip transform: reference-pose positions of the bone's children in its space.
		const FReferenceSkeleton& Ref = Body->GetSkeletalMeshAsset()->GetRefSkeleton();
		const int32 Parent = Ref.FindBoneIndex(Bone);
		for (int32 I = 0; I < Ref.GetNum(); ++I)
		{
			if (Ref.GetParentIndex(I) == Parent)
			{
				UE_LOG(LogDink, Display, TEXT("dink.Hero.Hold: child %s at (%s) in %s (reference pose)"), *Ref.GetBoneName(I).ToString(), *Ref.GetRefBonePose()[I].GetLocation().ToCompactString(), *Bone.ToString());
			}
		}
	}));
#endif
