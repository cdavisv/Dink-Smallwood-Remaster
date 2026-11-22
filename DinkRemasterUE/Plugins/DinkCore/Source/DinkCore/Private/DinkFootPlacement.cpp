#include "DinkFootPlacement.h"
#include "DinkCollision.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

float FDinkTwoBoneIK::Solve(const FVector& Hip, const FVector& Knee, const FVector& Ankle, const FVector& Target, const FVector& PoleDirection,
	FVector& OutKnee, FVector& OutAnkle, float SoftShare, float SoftStart)
{
	const double A = FVector::Dist(Hip, Knee), B = FVector::Dist(Knee, Ankle);
	const double Reach = A + B;
	FVector ToTarget = Target - Hip;
	double D = ToTarget.Size();
	if (A < 1e-3 || B < 1e-3 || D < 1e-3)
	{
		OutKnee = Knee; OutAnkle = Ankle;
		return float(FVector::Dist(Ankle, Target));
	}
	const FVector Dir = ToTarget / D;
	// Soft reach: over the last share of the leg's length the ankle approaches full extension asymptotically, so
	// a target at or past the limit never snaps the knee straight (the "pop" of a plain two-bone solver).
	// The soft zone starts no earlier than where the animated ankle already is: a reach the clip makes is kept as it is.
	const double Hard = FMath::Min(FMath::Max(Reach - FMath::Clamp(double(SoftShare), 0.0, .2) * Reach, double(SoftStart)), Reach * .9995);
	const double Soft = Reach - Hard;
	double Dc = D;
	if (Soft > 1e-4 && D > Hard) Dc = Hard + Soft * (1.0 - FMath::Exp(-(D - Hard) / Soft));
	Dc = FMath::Min(Dc, Reach * .9999);
	Dc = FMath::Max(Dc, FMath::Abs(A - B) + 1e-3);
	// The knee bends in the plane of the leg and the pole, towards the pole: never backwards.
	FVector Bend = PoleDirection - Dir * FVector::DotProduct(PoleDirection, Dir);
	if (Bend.SizeSquared() < 1e-6)
	{
		FVector Fallback = Knee - (Hip + Dir * FVector::DotProduct(Knee - Hip, Dir));
		Bend = Fallback.SizeSquared() > 1e-6 ? Fallback : FVector::CrossProduct(Dir, FVector::UpVector);
		if (Bend.SizeSquared() < 1e-6) Bend = FVector::ForwardVector;
	}
	Bend.Normalize();
	const double CosHip = FMath::Clamp((A * A + Dc * Dc - B * B) / (2.0 * A * Dc), -1.0, 1.0);
	const double SinHip = FMath::Sqrt(FMath::Max(0.0, 1.0 - CosHip * CosHip));
	OutKnee = Hip + Dir * (A * CosHip) + Bend * (A * SinHip);
	OutAnkle = Hip + Dir * Dc;
	return float(FMath::Max(0.0, D - Dc));
}

float FDinkTwoBoneIK::Flexion(const FVector& Hip, const FVector& Knee, const FVector& Ankle, const FVector& PoleDirection)
{
	const FVector U = (Hip - Knee).GetSafeNormal(), L = (Ankle - Knee).GetSafeNormal();
	const float Interior = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(float(FVector::DotProduct(U, L)), -1.f, 1.f)));
	const FVector Line = Ankle - Hip;
	const double T = Line.SizeSquared() > 1e-6 ? FVector::DotProduct(Knee - Hip, Line) / Line.SizeSquared() : 0.0;
	const FVector Off = Knee - (Hip + Line * T);
	const float Sign = FVector::DotProduct(Off, PoleDirection) >= -.05 ? 1.f : -1.f;
	return Sign * (180.f - Interior);
}

FDinkFootLock::FOutput FDinkFootLock::Update(const FInput& In, float DeltaTime, const FDinkFootLockSettings& S)
{
	const float Dt = FMath::IsFinite(DeltaTime) ? FMath::Clamp(DeltaTime, 0.f, .1f) : 0.f;
	FOutput Out;
	bWantsStep = false;
	const bool bPlantedByPose = In.Height < S.LockHeight && In.GroundSpeed < S.LockSpeed;
	// A foot the pose has lifted since it was last set down: its next pin is a footstep.
	if (In.Height >= S.LockHeight) bLifted = true;
	auto Current = [this, &In]() { return FMath::Lerp(In.Desired, FVector(Pin.X, Pin.Y, In.Desired.Z), Weight); };
	if (!In.bAllowed)
	{
		State = EState::Free;
		Weight = 0.f;
	}
	switch (State)
	{
	case EState::Free:
		// Let go: the pin fades into the pose's own foot. A foot the pose sets down is pinned where it is drawn now.
		Weight = FMath::Max(0.f, Weight - (S.ReleaseTime > 0.f ? Dt / S.ReleaseTime : 1.f));
		if (In.bAllowed && In.bNewPins && bPlantedByPose)
		{
			const FVector At = Current();
			Pin = At;
			PinYaw = Weight > 0.f ? PinYaw + FMath::FindDeltaAngleDegrees(PinYaw, In.DesiredYaw) * (1.f - Weight) : In.DesiredYaw;
			Weight = 1.f;
			State = EState::Locked;
			FastFrames = 0;
			if (bLifted) { ++Plants; bLifted = false; }
		}
		break;
	case EState::Locked:
	{
		const float Error = float(FVector::Dist2D(Pin, In.Desired));
		const float YawError = FMath::Abs(FMath::FindDeltaAngleDegrees(PinYaw, In.DesiredYaw));
		// Hysteresis: the pin holds until the pose lifts the foot, or (walking) the pose's foot runs off over the ground
		// for two frames running; LockSpeed is only the threshold to engage.
		FastFrames = In.GroundSpeed > 3.f * S.LockSpeed ? FastFrames + 1 : 0;
		if (In.Height >= S.LockHeight + 1.f || (!In.bStanding && FastFrames >= 3))
		{
			// The pose lifts the foot (a step of the gait or of an action): follow it, blending out of the pin.
			State = EState::Free;
			++Releases[In.Height >= S.LockHeight + 1.f ? 0 : 1];
		}
		else if (Error > S.MaxError)
		{
			State = EState::Free;
			++Releases[2];
		}
		else if (!In.bStanding && Error > S.PinSlack)
		{
			// Walking or running: the clip's own drift under a planted foot is let through beyond the slack only.
			const FVector2D D = FVector2D(Pin - In.Desired).GetSafeNormal() * S.PinSlack;
			Pin.X = In.Desired.X + D.X;
			Pin.Y = In.Desired.Y + D.Y;
		}
		else if (In.bStanding && (Error > S.StepDistance || YawError > S.StepYaw))
		{
			bWantsStep = true;
			if (In.bOtherPinned)
			{
				State = EState::Stepping;
				StepFrom = Pin; StepFromYaw = PinYaw; StepT = 0.f;
				StepDist = Error;
				StepTime = FMath::Lerp(S.StepTimeMin, S.StepTimeMax, FMath::Clamp(Error / 30.f, 0.f, 1.f)) * FMath::Clamp(In.StepTimeScale, .5f, 2.f);
				++Steps;
			}
		}
		break;
	}
	case EState::Stepping:
		StepT = FMath::Min(1.f, StepT + Dt / FMath::Max(.05f, StepTime));
		if (StepT >= 1.f)
		{
			Pin = In.Desired; PinYaw = In.DesiredYaw;
			State = EState::Locked;
			FastFrames = 0;
			++Plants;
			bLifted = false;
		}
		break;
	}
	if (State == EState::Stepping)
	{
		// Eased travel towards where the pose wants the foot now (it may still be moving), lifted on an arc.
		const float E = FMath::SmoothStep(0.f, 1.f, StepT);
		const FVector To(In.Desired.X, In.Desired.Y, In.Desired.Z);
		Pin = FMath::Lerp(FVector(StepFrom.X, StepFrom.Y, To.Z), To, E);
		PinYaw = StepFromYaw + FMath::FindDeltaAngleDegrees(StepFromYaw, In.DesiredYaw) * E;
		Out.Lift = S.StepLift * FMath::Clamp(StepDist / 20.f, .35f, 1.2f) * FMath::Sin(PI * StepT);
		Weight = 1.f;
	}
	if (State == EState::Locked)
	{
		// The pin keeps its yaw, within what the ankle and knee can twist.
		const float D = FMath::FindDeltaAngleDegrees(In.DesiredYaw, PinYaw);
		if (FMath::Abs(D) > S.MaxPinnedYaw) PinYaw = In.DesiredYaw + FMath::Sign(D) * S.MaxPinnedYaw;
	}
	Out.Weight = Weight;
	Out.Position = Current();
	Out.Position.Z = In.Desired.Z + Out.Lift;
	Out.Yaw = Weight > 0.f ? In.DesiredYaw + FMath::FindDeltaAngleDegrees(In.DesiredYaw, PinYaw) * Weight : In.DesiredYaw;
	return Out;
}

FDinkGaitStyle FDinkGaitStyle::Lerp(const FDinkGaitStyle& A, const FDinkGaitStyle& B, float T)
{
	T = FMath::Clamp(T, 0.f, 1.f);
	FDinkGaitStyle R;
	R.Stride = FMath::Lerp(A.Stride, B.Stride, T);
	R.WidthCm = FMath::Lerp(A.WidthCm, B.WidthCm, T);
	R.Uneven = FMath::Lerp(A.Uneven, B.Uneven, T);
	R.StepTime = FMath::Lerp(A.StepTime, B.StepTime, T);
	R.ChestSwing = FMath::Lerp(A.ChestSwing, B.ChestSwing, T);
	R.CadenceShare = FMath::Lerp(A.CadenceShare, B.CadenceShare, T);
	return R;
}

namespace
{
	struct FStyleTable
	{
		TMap<FName, TPair<FDinkGaitStyle, FDinkGaitStyle>> Rows;
		bool bLoaded = false;
	};
	FStyleTable& Styles()
	{
		static FStyleTable Table;
		return Table;
	}
	FDinkGaitStyle ReadStyle(const TSharedPtr<FJsonObject>& O)
	{
		FDinkGaitStyle S;
		if (!O) return S;
		double N = 0;
		if (O->TryGetNumberField(TEXT("stride"), N)) S.Stride = FMath::Clamp(float(N), .6f, 1.4f);
		if (O->TryGetNumberField(TEXT("width_cm"), N)) S.WidthCm = FMath::Clamp(float(N), -8.f, 12.f);
		if (O->TryGetNumberField(TEXT("uneven"), N)) S.Uneven = FMath::Clamp(float(N), 0.f, .15f);
		if (O->TryGetNumberField(TEXT("step_time"), N)) S.StepTime = FMath::Clamp(float(N), .5f, 2.f);
		if (O->TryGetNumberField(TEXT("chest_swing"), N)) S.ChestSwing = FMath::Clamp(float(N), 0.f, 3.f);
		if (O->TryGetNumberField(TEXT("cadence_share"), N)) S.CadenceShare = FMath::Clamp(float(N), 0.f, 1.f);
		return S;
	}
}

void FDinkGaitStyle::Reload()
{
	FStyleTable& T = Styles();
	T.Rows.Reset();
	T.bLoaded = true;
	FString Text;
	TSharedPtr<FJsonObject> Root;
	const TSharedPtr<FJsonObject>* Rows = nullptr;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/animation_natural.json"))) ||
		!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root || !Root->TryGetObjectField(TEXT("style"), Rows) || !Rows) return;
	for (const auto& Pair : (*Rows)->Values)
	{
		const TSharedPtr<FJsonObject>* Row = nullptr;
		if (!Pair.Value->TryGetObject(Row) || !Row) continue;
		const TSharedPtr<FJsonObject>* Timid = nullptr;
		const TSharedPtr<FJsonObject>* Confident = nullptr;
		(*Row)->TryGetObjectField(TEXT("timid"), Timid);
		(*Row)->TryGetObjectField(TEXT("confident"), Confident);
		const FDinkGaitStyle A = ReadStyle(Timid ? *Timid : *Row);
		const FDinkGaitStyle B = Confident ? ReadStyle(*Confident) : A;
		T.Rows.Add(FName(*Pair.Key), {A, B});
	}
}

FDinkGaitStyle FDinkGaitStyle::For(FName Set, float Confidence)
{
	FStyleTable& T = Styles();
	if (!T.bLoaded) Reload();
	const TPair<FDinkGaitStyle, FDinkGaitStyle>* Row = T.Rows.Find(Set);
	return Row ? Lerp(Row->Key, Row->Value, Confidence) : FDinkGaitStyle();
}

bool FDinkFootGround::Trace(UWorld* World, const FVector& At, float FloorZ, const AActor* Ignore, float& OutZ, FVector& OutNormal, FString* OutWhat)
{
	if (!World) return false;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkFootGround), false, Ignore);
	// The 1997 hardness prisms (DinkHardSolid blocks Visibility; they are 3 m tall and hidden) and the player-only
	// blockers are not ground: a foot beside a wall, a river edge or a door's warp hardbox must not stand on them.
	FCollisionResponseParams Responses;
	Responses.CollisionResponse.SetResponse(DinkCollision::HardSolid, ECR_Ignore);
	Responses.CollisionResponse.SetResponse(DinkCollision::HardLow, ECR_Ignore);
	Responses.CollisionResponse.SetResponse(DinkCollision::PlayerBlock, ECR_Ignore);
	const FVector Start(At.X, At.Y, FloorZ + 45.f), End(At.X, At.Y, FloorZ - 50.f);
	for (int32 Try = 0; Try < 3; ++Try)
	{
		FHitResult Hit;
		if (!World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params, Responses)) break;
		const UPrimitiveComponent* C = Hit.GetComponent();
		const AActor* A = Hit.GetActor();
		if (C && !Hit.bStartPenetrating && C->IsVisible() && !C->bHiddenInGame && !(A && (A->IsHidden() || Cast<APawn>(A))) && !Cast<USkinnedMeshComponent>(C))
		{
			OutZ = float(Hit.ImpactPoint.Z);
			OutNormal = Hit.ImpactNormal;
			if (OutWhat) *OutWhat = A ? A->GetName() : C->GetName();
			return true;
		}
		if (!C) break;
		Params.AddIgnoredComponent(C);
	}
	if (OutWhat) *OutWhat = TEXT("-");
	return false;
}
