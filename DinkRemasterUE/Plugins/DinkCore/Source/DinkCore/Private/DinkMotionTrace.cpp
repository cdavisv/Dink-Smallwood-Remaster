// dink.Motion.Trace <seconds> [file] [radius cm]: review only. One CSV row per rendered frame, per animated body near
// the player (the hero, humanoid NPC bodies, creature bodies) and per bone of interest: the bone's world position and
// rotation as drawn, and for feet the height of the visible ground under them. Scripts/AnimationQA/motion_report.py
// turns it into foot slide, ground contact, joint angles, pelvis and trunk motion. Nothing is changed.
#include "DinkCoreModule.h"
#include "DinkFootPlacement.h"
#include "DinkBodyAnimInstance.h"
#include "DinkHumanoidComponent.h"
#include "DinkCreatureClassComponent.h"
#include "DinkCreatureComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Containers/Ticker.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include <limits>

#if !UE_BUILD_SHIPPING
namespace
{
	const TCHAR* const HumanBones[] = {
		TEXT("root"), TEXT("pelvis"), TEXT("spine_01"), TEXT("spine_03"), TEXT("spine_05"), TEXT("neck_01"), TEXT("head"),
		TEXT("clavicle_l"), TEXT("clavicle_r"), TEXT("upperarm_l"), TEXT("upperarm_r"), TEXT("lowerarm_l"), TEXT("lowerarm_r"),
		TEXT("hand_l"), TEXT("hand_r"), TEXT("thigh_l"), TEXT("thigh_r"), TEXT("calf_l"), TEXT("calf_r"),
		TEXT("foot_l"), TEXT("foot_r"), TEXT("ball_l"), TEXT("ball_r")};

	struct FDinkMotionTrace
	{
		TWeakObjectPtr<UWorld> World;
		FString Path;
		TArray<FString> Rows;
		double EndTime = 0.0;
		float Radius = 2500.f;
		uint64 Frame = 0;
		int32 Written = 0;
		bool bStarted = false;
	};

	bool IsFootBone(const FString& Name)
	{
		const FString L = Name.ToLower();
		return L.StartsWith(TEXT("foot")) || L.StartsWith(TEXT("ball")) || L.Contains(TEXT("toe")) || L.Contains(TEXT("hoof")) || L.Contains(TEXT("paw"));
	}

	/** Height of the visible ground under a point, as the leg layer sees it (FDinkFootGround); NaN when there is none. */
	float GroundUnder(UWorld* World, const FVector& At, float FloorZ, const AActor* Ignore, FString& OutWhat)
	{
		float Z = 0.f;
		FVector N;
		return FDinkFootGround::Trace(World, At, FloorZ, Ignore, Z, N, &OutWhat) ? Z : std::numeric_limits<float>::quiet_NaN();
	}

	void TraceBody(FDinkMotionTrace& T, UWorld* World, const FString& Label, const TCHAR* Kind, USkeletalMeshComponent* Mesh, double Now, float Floor)
	{
		if (!Mesh || !Mesh->GetSkeletalMeshAsset() || !Mesh->IsVisible()) return;
		AActor* Owner = Mesh->GetOwner();
		const FTransform C = Mesh->GetComponentTransform();
		const FVector V = Owner ? Owner->GetVelocity() : FVector::ZeroVector;
		const UDinkBodyAnimInstance* Body = Cast<UDinkBodyAnimInstance>(Mesh->GetAnimInstance());
		const FString Prefix = FString::Printf(TEXT("%llu,%.5f,%.5f,%s,%s"), T.Frame, Now, World->GetDeltaSeconds(), *Label, Kind);
		T.Rows.Add(FString::Printf(TEXT("%s,_comp,%.3f,%.3f,%.3f,%.5f,%.5f,%.5f,%.5f,%.3f,%s"), *Prefix, C.GetLocation().X, C.GetLocation().Y, C.GetLocation().Z,
			C.GetRotation().X, C.GetRotation().Y, C.GetRotation().Z, C.GetRotation().W, Floor, TEXT("-")));
		const FVector A = Owner ? Owner->GetActorLocation() : C.GetLocation();
		T.Rows.Add(FString::Printf(TEXT("%s,_actor,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%s"), *Prefix, A.X, A.Y, A.Z, V.X, V.Y, V.Z,
			Owner ? Owner->GetActorRotation().Yaw : 0., Floor, TEXT("-")));
		if (Body)
		{
			T.Rows.Add(FString::Printf(TEXT("%s,_anim,%.3f,%.4f,%.4f,%.3f,%d,%.3f,0,%.3f,%s"), *Prefix, Body->GetSpeed(), Body->GetPhase(), Body->GetCyclesPerSecond(),
				Body->GetBlendedStrideCm(), Body->IsActionActive() ? 1 : 0, Body->GetActionTime(), Floor, *Body->GetActionName().ToString()));
		}
		TArray<FName, TInlineAllocator<48>> Names;
		if (Body)
			for (const TCHAR* Name : HumanBones) Names.Add(Name);
		else
			for (int32 i = 0; i < Mesh->GetNumBones() && i < 64; ++i) Names.Add(Mesh->GetBoneName(i));
		for (const FName Name : Names)
		{
			const int32 Index = Mesh->GetBoneIndex(Name);
			if (Index == INDEX_NONE) continue;
			const FTransform B = Mesh->GetBoneTransform(Index);
			const FString S = Name.ToString();
			FString What = TEXT("-");
			const float Ground = IsFootBone(S) ? GroundUnder(World, B.GetLocation(), float(C.GetLocation().Z), Owner, What) : std::numeric_limits<float>::quiet_NaN();
			T.Rows.Add(FString::Printf(TEXT("%s,%s,%.3f,%.3f,%.3f,%.5f,%.5f,%.5f,%.5f,%.3f,%s"), *Prefix, *S, B.GetLocation().X, B.GetLocation().Y, B.GetLocation().Z,
				B.GetRotation().X, B.GetRotation().Y, B.GetRotation().Z, B.GetRotation().W, Ground, *What));
		}
	}

	bool TickMotionTrace(TSharedRef<FDinkMotionTrace> T)
	{
		UWorld* World = T->World.Get();
		const double Now = World ? World->GetTimeSeconds() : 0.0;
		auto Flush = [&T]()
		{
			if (T->Rows.IsEmpty()) return;
			T->Written += T->Rows.Num();
			FFileHelper::SaveStringToFile(FString::Join(T->Rows, TEXT("\n")) + TEXT("\n"), *T->Path, FFileHelper::EEncodingOptions::AutoDetect,
				&IFileManager::Get(), T->bStarted ? FILEWRITE_Append : FILEWRITE_None);
			T->bStarted = true;
			T->Rows.Reset();
		};
		if (!World || Now >= T->EndTime)
		{
			Flush();
			UE_LOG(LogDink, Display, TEXT("DINK MOTION TRACE: %d rows -> %s"), T->Written - 1, *T->Path);
			return false;
		}
		if (T->Rows.Num() > 4000) Flush();
		++T->Frame;
		APlayerController* PC = World->GetFirstPlayerController();
		ACharacter* Hero = PC ? Cast<ACharacter>(PC->GetPawn()) : nullptr;
		const FVector Here = Hero ? Hero->GetActorLocation() : FVector::ZeroVector;
		if (Hero)
		{
			const UCapsuleComponent* Capsule = Hero->GetCapsuleComponent();
			TraceBody(*T, World, TEXT("hero"), TEXT("hero"), Hero->GetMesh(), Now, float(Here.Z - (Capsule ? Capsule->GetScaledCapsuleHalfHeight() : 0.f)));
		}
		for (TObjectIterator<USkeletalMeshComponent> It; It; ++It)
		{
			USkeletalMeshComponent* Mesh = *It;
			if (Mesh->GetWorld() != World || !Mesh->IsRegistered() || (Hero && Mesh == Hero->GetMesh())) continue;
			const TCHAR* Kind = Cast<UDinkHumanoidComponent>(Mesh) ? TEXT("npc") : Cast<UDinkCreatureClassComponent>(Mesh) ? TEXT("creature_class")
				: Cast<UDinkCreatureComponent>(Mesh) ? TEXT("creature") : nullptr;
			if (!Kind || FVector::Dist2D(Mesh->GetComponentLocation(), Here) > T->Radius) continue;
			const AActor* Owner = Mesh->GetOwner();
			TraceBody(*T, World, Owner ? Owner->GetName() : Mesh->GetName(), Kind, Mesh, Now, float(Owner ? Owner->GetActorLocation().Z : 0.));
		}
		return true;
	}
}

static FAutoConsoleCommandWithWorldAndArgs GDinkMotionTraceCommand(
	TEXT("dink.Motion.Trace"),
	TEXT("dink.Motion.Trace <seconds> [file] [radius cm]: review only. Per rendered frame, the drawn bones of the hero and of every humanoid/creature body within the radius (default 2500 cm), with the visible ground under the feet, as CSV (default Saved/AnimationPass/motion_trace.csv)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World) return;
		TSharedRef<FDinkMotionTrace> T = MakeShared<FDinkMotionTrace>();
		T->World = World;
		T->EndTime = World->GetTimeSeconds() + (Args.Num() > 0 ? FMath::Max(.1f, FCString::Atof(*Args[0])) : 10.f);
		T->Path = Args.Num() > 1 ? Args[1] : FPaths::ProjectSavedDir() / TEXT("AnimationPass/motion_trace.csv");
		if (Args.Num() > 2) T->Radius = FMath::Max(100.f, FCString::Atof(*Args[2]));
		T->Rows.Add(TEXT("frame,time,dt,body,kind,bone,x,y,z,qx,qy,qz,qw,ground_z,ground_what"));
		UE_LOG(LogDink, Display, TEXT("DINK MOTION TRACE: start %.1fs -> %s"), T->EndTime - World->GetTimeSeconds(), *T->Path);
		FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([T](float) { return TickMotionTrace(T); }));
	}));
#endif
