#include "DinkPhysicsAssetLibrary.h"

#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"

namespace
{
	// Half-angles in degrees as the engine stores them (each side of the reference pose); the same table as the test
	// Dink.Report.PhysicsConstraints. Hinges (elbow, knee) are only bounded here, not reduced to one axis: which swing axis
	// is the hinge depends on the constraint frames, which this helper does not change.
	struct FRange { const TCHAR* Prefix; float Swing1, Swing2, Twist; };
	const FRange Ranges[] = {
		{ TEXT("spine"), 35.f, 35.f, 35.f }, { TEXT("neck"), 50.f, 50.f, 70.f }, { TEXT("head"), 50.f, 50.f, 70.f },
		{ TEXT("clavicle"), 30.f, 30.f, 30.f }, { TEXT("upperarm"), 100.f, 100.f, 90.f }, { TEXT("lowerarm"), 80.f, 80.f, 90.f },
		{ TEXT("hand"), 75.f, 75.f, 35.f }, { TEXT("thigh"), 90.f, 90.f, 50.f }, { TEXT("calf"), 80.f, 80.f, 20.f },
		{ TEXT("foot"), 50.f, 50.f, 30.f }, { TEXT("ball"), 45.f, 45.f, 10.f },
	};
	const TCHAR* Motion(EAngularConstraintMotion M) { return M == ACM_Free ? TEXT("free") : M == ACM_Locked ? TEXT("locked") : TEXT("limited"); }
}

FString UDinkPhysicsAssetLibrary::DescribeConstraints(UPhysicsAsset* Asset)
{
	if (!Asset) return FString();
	FString Out;
	for (const UPhysicsConstraintTemplate* C : Asset->ConstraintSetup)
	{
		if (!C) continue;
		const FConstraintInstance& I = C->DefaultInstance;
		const FConeConstraint& Cone = I.ProfileInstance.ConeLimit;
		const FTwistConstraint& Twist = I.ProfileInstance.TwistLimit;
		Out += FString::Printf(TEXT("%s-%s swing1 %s %.0f swing2 %s %.0f twist %s %.0f\n"), *I.ConstraintBone1.ToString(), *I.ConstraintBone2.ToString(),
			Motion(Cone.Swing1Motion), Cone.Swing1LimitDegrees, Motion(Cone.Swing2Motion), Cone.Swing2LimitDegrees, Motion(Twist.TwistMotion), Twist.TwistLimitDegrees);
	}
	return Out;
}

int32 UDinkPhysicsAssetLibrary::ClampHumanJointLimits(UPhysicsAsset* Asset)
{
	if (!Asset) return 0;
	int32 Changed = 0;
	for (UPhysicsConstraintTemplate* C : Asset->ConstraintSetup)
	{
		if (!C) continue;
		FConstraintInstance& I = C->DefaultInstance;
		const FString Bone = I.ConstraintBone1.ToString();
		C->Modify();
		const FRange* R = nullptr;
		for (const FRange& Candidate : Ranges) if (Bone.StartsWith(Candidate.Prefix)) { R = &Candidate; break; }
		if (!R) continue;
		bool bChanged = false;
		auto Clamp = [&bChanged](TEnumAsByte<EAngularConstraintMotion>& M, float& Deg, float Max)
		{
			if (M == ACM_Free) { M = ACM_Limited; Deg = Max; bChanged = true; }
			else if (M == ACM_Limited && Deg > Max + .5f) { Deg = Max; bChanged = true; }
		};
		FConeConstraint& Cone = I.ProfileInstance.ConeLimit;
		FTwistConstraint& Twist = I.ProfileInstance.TwistLimit;
		Clamp(Cone.Swing1Motion, Cone.Swing1LimitDegrees, R->Swing1);
		Clamp(Cone.Swing2Motion, Cone.Swing2LimitDegrees, R->Swing2);
		Clamp(Twist.TwistMotion, Twist.TwistLimitDegrees, R->Twist);
		FLinearConstraint& Linear = I.ProfileInstance.LinearLimit;
		if (Linear.XMotion != LCM_Locked || Linear.YMotion != LCM_Locked || Linear.ZMotion != LCM_Locked)
		{
			Linear.XMotion = Linear.YMotion = Linear.ZMotion = LCM_Locked;
			bChanged = true;
		}
		if (bChanged) { ++Changed; C->UpdateProfileInstance(); }
	}
	if (Changed > 0) Asset->MarkPackageDirty();
	return Changed;
}
