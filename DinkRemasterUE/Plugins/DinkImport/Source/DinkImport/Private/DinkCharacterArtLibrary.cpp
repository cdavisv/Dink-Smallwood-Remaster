#include "DinkCharacterArtLibrary.h"
#include "Animation/Skeleton.h"
#include "Animation/AnimSequence.h"
#include "Animation/BlendSpace1D.h"
#include "UObject/UnrealType.h"
#include "AssetCompilingManager.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
	TArray<TSharedPtr<FJsonValue>> VectorArray(const FVector& V)
	{
		return {MakeShared<FJsonValueNumber>(V.X), MakeShared<FJsonValueNumber>(V.Y), MakeShared<FJsonValueNumber>(V.Z)};
	}
}

FString UDinkCharacterArtLibrary::InspectRig(USkeletalMesh* Mesh)
{
	if (!Mesh) return TEXT("{}");
	FAssetCompilingManager::Get().FinishAllCompilation();
	TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetStringField(TEXT("mesh"), Mesh->GetPathName());
	Root->SetStringField(TEXT("skeleton"), Mesh->GetSkeleton() ? Mesh->GetSkeleton()->GetPathName() : FString());
	Root->SetArrayField(TEXT("bounds_size_cm"), VectorArray(Mesh->GetBounds().BoxExtent * 2.0));
	Root->SetArrayField(TEXT("bounds_origin_cm"), VectorArray(Mesh->GetBounds().Origin));
	const FReferenceSkeleton& Rig = Mesh->GetRefSkeleton();
	TArray<TSharedPtr<FJsonValue>> Bones;
	TArray<FTransform> ComponentPose;
	ComponentPose.SetNum(Rig.GetNum());
	for (int32 I = 0; I < Rig.GetNum(); ++I)
	{
		TSharedRef<FJsonObject> Bone = MakeShared<FJsonObject>();
		Bone->SetStringField(TEXT("name"), Rig.GetBoneName(I).ToString());
		Bone->SetNumberField(TEXT("parent"), Rig.GetParentIndex(I));
		const FTransform& Transform = Rig.GetRefBonePose()[I];
		ComponentPose[I] = Rig.GetParentIndex(I) >= 0 ? Transform * ComponentPose[Rig.GetParentIndex(I)] : Transform;
		Bone->SetArrayField(TEXT("component_translation_cm"), VectorArray(ComponentPose[I].GetLocation()));
		Bone->SetArrayField(TEXT("translation_cm"), VectorArray(Transform.GetLocation()));
		Bone->SetArrayField(TEXT("scale"), VectorArray(Transform.GetScale3D()));
		const FQuat Q = Transform.GetRotation();
		Bone->SetArrayField(TEXT("rotation_xyzw"), {MakeShared<FJsonValueNumber>(Q.X), MakeShared<FJsonValueNumber>(Q.Y), MakeShared<FJsonValueNumber>(Q.Z), MakeShared<FJsonValueNumber>(Q.W)});
		Bones.Add(MakeShared<FJsonValueObject>(Bone));
	}
	Root->SetArrayField(TEXT("bones"), Bones);
	FString Json;
	FJsonSerializer::Serialize(Root, TJsonWriterFactory<>::Create(&Json));
	return Json;
}


bool UDinkCharacterArtLibrary::AssignMatchingSkeleton(USkeletalMesh* Mesh, USkeletalMesh* Reference)
{
	if (!Mesh || !Reference || !Reference->GetSkeleton()) return false;
	FAssetCompilingManager::Get().FinishAllCompilation();
	const FReferenceSkeleton& Rig = Mesh->GetRefSkeleton();
	const FReferenceSkeleton& Expected = Reference->GetRefSkeleton();
	if (Rig.GetNum() != Expected.GetNum()) return false;
	for (int32 Index = 0; Index < Rig.GetNum(); ++Index)
	{
		const int32 Other = Expected.FindBoneIndex(Rig.GetBoneName(Index));
		if (Other == INDEX_NONE) return false;
		const int32 Parent = Rig.GetParentIndex(Index), OtherParent = Expected.GetParentIndex(Other);
		if ((Parent >= 0 ? Rig.GetBoneName(Parent) : NAME_None) != (OtherParent >= 0 ? Expected.GetBoneName(OtherParent) : NAME_None)) return false;
		const FTransform& Pose = Rig.GetRefBonePose()[Index];
		const FTransform& OtherPose = Expected.GetRefBonePose()[Other];
		if (!Pose.GetLocation().Equals(OtherPose.GetLocation(), .1) ||
			Pose.GetRotation().AngularDistance(OtherPose.GetRotation()) > .002 ||
			!Pose.GetScale3D().Equals(OtherPose.GetScale3D(), .001)) return false;
	}
	Mesh->SetSkeleton(Reference->GetSkeleton());
	Mesh->MarkPackageDirty();
	return true;
}


bool UDinkCharacterArtLibrary::ConfigureCreatureLocomotion(UBlendSpace* Blend, UAnimSequence* Idle, UAnimSequence* Walk, float WalkSpeed, UAnimSequence* Run, float RunSpeed)
{
	if (!Blend || !Blend->IsA<UBlendSpace1D>() || !Idle || !Walk || WalkSpeed <= 0.f ||
		!Blend->GetSkeleton() || Blend->GetSkeleton() != Idle->GetSkeleton() || Blend->GetSkeleton() != Walk->GetSkeleton() ||
		(Run && (RunSpeed <= WalkSpeed || Run->GetSkeleton() != Blend->GetSkeleton()))) return false;
	FStructProperty* AxisProperty = FindFProperty<FStructProperty>(UBlendSpace::StaticClass(), TEXT("BlendParameters"));
	if (!AxisProperty) return false;
	Blend->Modify();
	FBlendParameter* Speed = AxisProperty->ContainerPtrToValuePtr<FBlendParameter>(Blend, 0);
	Speed->DisplayName = TEXT("Speed"); Speed->Min = 0.f; Speed->Max = Run ? RunSpeed : WalkSpeed; Speed->GridNum = 4;
	for (int32 Index = Blend->GetNumberOfBlendSamples() - 1; Index >= 0; --Index) Blend->DeleteSample(Index);
	if (Blend->AddSample(Idle, FVector::ZeroVector) == INDEX_NONE || Blend->AddSample(Walk, FVector(WalkSpeed, 0, 0)) == INDEX_NONE) return false;
	if (Run && Blend->AddSample(Run, FVector(RunSpeed, 0, 0)) == INDEX_NONE) return false;
	Blend->ValidateSampleData();
	Blend->ResampleData();
	Blend->PostEditChange();
	Blend->MarkPackageDirty();
	return Blend->GetNumberOfBlendSamples() == (Run ? 3 : 2);
}


FString UDinkCharacterArtLibrary::InspectCreatureAnimation(UAnimSequence* Animation)
{
	if (!Animation || !Animation->GetSkeleton()) return TEXT("{}");
	FAssetCompilingManager::Get().FinishAllCompilation();
	TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
	Report->SetStringField(TEXT("animation"), Animation->GetPathName());
	Report->SetStringField(TEXT("skeleton"), Animation->GetSkeleton()->GetPathName());
	const double Length = Animation->GetPlayLength();
	Report->SetNumberField(TEXT("duration_s"), Length);
	double RootDistance = 0, MotionAngle = 0, LoopAngle = 0, LoopDistance = 0, ScaleError = 0;
	bool bFinite = true;
	const int32 BoneCount = Animation->GetSkeleton()->GetReferenceSkeleton().GetNum();
	for (int32 Bone = 0; Bone < BoneCount; ++Bone)
	{
		FTransform First;
		Animation->GetBoneTransform(First, FSkeletonPoseBoneIndex(Bone), FAnimExtractContext(0.0, false), true);
		for (int32 Sample = 0; Sample <= 8; ++Sample)
		{
			FTransform Pose;
			Animation->GetBoneTransform(Pose, FSkeletonPoseBoneIndex(Bone), FAnimExtractContext(Length * Sample / 8.0, false), true);
			bFinite &= !Pose.ContainsNaN();
			ScaleError = FMath::Max(ScaleError, (Pose.GetScale3D() - FVector::OneVector).GetAbsMax());
			MotionAngle = FMath::Max(MotionAngle, double(First.GetRotation().AngularDistance(Pose.GetRotation())));
			if (Bone == 0) RootDistance = FMath::Max(RootDistance, FVector::Distance(First.GetLocation(), Pose.GetLocation()));
			if (Sample == 8)
			{
				LoopAngle = FMath::Max(LoopAngle, double(First.GetRotation().AngularDistance(Pose.GetRotation())));
				LoopDistance = FMath::Max(LoopDistance, FVector::Distance(First.GetLocation(), Pose.GetLocation()));
			}
		}
	}
	Report->SetBoolField(TEXT("finite_poses"), bFinite);
	Report->SetNumberField(TEXT("bone_count"), BoneCount);
	Report->SetNumberField(TEXT("max_scale_error"), ScaleError);
	Report->SetNumberField(TEXT("root_motion_cm"), RootDistance);
	Report->SetNumberField(TEXT("max_pose_rotation_rad"), MotionAngle);
	Report->SetNumberField(TEXT("loop_seam_rotation_rad"), LoopAngle);
	Report->SetNumberField(TEXT("loop_seam_translation_cm"), LoopDistance);
	FString Json;
	FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
	return Json;
}
