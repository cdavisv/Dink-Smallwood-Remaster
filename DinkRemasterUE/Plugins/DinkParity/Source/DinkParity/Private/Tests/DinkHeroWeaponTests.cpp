#include "Misc/AutomationTest.h"
#include "DinkTestHelpers.h"
#include "DinkHeroWeapon.h"
#include "DinkBodyAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "GameFramework/Actor.h"
#include "Misc/PackageName.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHeroWeaponRowsTest, "Dink.Art.HeroWeapon.RowsAndAttach", DINK_TEST_FLAGS)
bool FDinkHeroWeaponRowsTest::RunTest(const FString&)
{
	DinkHeroWeapons::Reload();
	// Every weapon item of the 1997 game that 1997 draws in Dink's hand has a mesh row; fists and the bomb carry nothing.
	int32 Missing = 0;
	for (const TCHAR* Item : {TEXT("item-sw1"), TEXT("item-sw2"), TEXT("item-sw3"), TEXT("item-axe"), TEXT("item-b1"), TEXT("item-b2"), TEXT("item-b3")})
	{
		const FDinkHeroWeaponRow* Row = DinkHeroWeapons::Find(FName(Item));
		if (!TestNotNull(FString::Printf(TEXT("%s has a hand mesh"), Item), Row)) continue;
		FString Package = Row->Mesh;
		Package.Split(TEXT("."), &Package, nullptr);
		if (!FPackageName::DoesPackageExist(Package)) { ++Missing; AddWarning(FString::Printf(TEXT("%s: %s is not imported here"), Item, *Row->Mesh)); }
		TestEqual(FString::Printf(TEXT("%s: a bow is held in the left hand, a blade in the right"), Item), Row->Bone, FName(FString(Item).StartsWith(TEXT("item-b")) ? TEXT("hand_l") : TEXT("hand_r")));
	}
	TestNull(TEXT("fists carry nothing"), DinkHeroWeapons::Find(TEXT("item-fst")));
	TestNull(TEXT("a bomb is not held"), DinkHeroWeapons::Find(TEXT("item-bom")));
	// Attach to a hero body: arm, swap, disarm.
	USkeletalMesh* Hero = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Hero/Refinements/SK_Dink_Hands.SK_Dink_Hands"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (Missing > 0 || !Hero)
	{
		AddWarning(TEXT("attach part skipped: the hero or the weapon meshes are not imported in this checkout"));
		return true;
	}
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
	AActor* Stage = World->SpawnActor<AActor>();
	USkeletalMeshComponent* Body = NewObject<USkeletalMeshComponent>(Stage);
	Stage->SetRootComponent(Body);
	Body->SetSkeletalMesh(Hero);
	Body->RegisterComponent();
	UStaticMeshComponent* Held = DinkHeroWeapons::Apply(Stage, TEXT("item-sw1"), true);
	if (TestNotNull(TEXT("the longsword is in his hand"), Held))
	{
		TestEqual(TEXT("on the right hand"), Held->GetAttachSocketName(), FName(TEXT("hand_r")));
		TestTrue(TEXT("the longsword's mesh"), Held->GetStaticMesh() && Held->GetStaticMesh()->GetName() == TEXT("SM_Hero_Sword_Long_PR"));
		TestTrue(TEXT("it is drawn"), Held->IsVisible());
		TestEqual(TEXT("no collision"), Held->GetCollisionEnabled(), ECollisionEnabled::NoCollision);
	}
	UStaticMeshComponent* Bow = DinkHeroWeapons::Apply(Stage, TEXT("item-b2"), true);
	TestTrue(TEXT("arming the bow swaps the same component to the left hand"), Bow == Held && Bow && Bow->GetAttachSocketName() == FName(TEXT("hand_l")));
	TestNull(TEXT("fists: the hand is empty"), DinkHeroWeapons::Apply(Stage, TEXT("item-fst"), true));
	TestTrue(TEXT("and the mesh is hidden"), Held && !Held->IsVisible());
	TestNull(TEXT("dead or switched off: empty"), DinkHeroWeapons::Apply(Stage, TEXT("item-sw1"), false));
	TArray<UStaticMeshComponent*> Comps;
	Stage->GetComponents<UStaticMeshComponent>(Comps);
	TestEqual(TEXT("one weapon component per hero, however often it is re-armed"), Comps.Num(), 1);
	return true;
}

namespace
{
	// Where a finger tip is in its hand's own space, from a clip (the chain of local transforms below the hand). The
	// clip's tracks are read by the SKELETON's bone indices, which are not the mesh's.
	FVector TipInHand(const UAnimSequence* Seq, FName TipName, FName HandName, double Time)
	{
		const FReferenceSkeleton& Ref = Seq->GetSkeleton()->GetReferenceSkeleton();
		const int32 Tip = Ref.FindBoneIndex(TipName), Hand = Ref.FindBoneIndex(HandName);
		if (Tip == INDEX_NONE || Hand == INDEX_NONE) return FVector(1e6);
		FTransform Out = FTransform::Identity;
		for (int32 B = Tip; B != INDEX_NONE && B != Hand; B = Ref.GetParentIndex(B))
		{
			FTransform Local;
			Seq->GetBoneTransform(Local, FSkeletonPoseBoneIndex(B), FAnimExtractContext(Time, false), false);
			Out = Out * Local;
		}
		return Out.GetLocation();
	}
	// The same from the posed body.
	FVector TipInHand(const USkeletalMeshComponent* Body, FName Tip, FName Hand)
	{
		return Body->GetBoneTransform(Hand, RTS_Component).InverseTransformPosition(Body->GetBoneTransform(Tip, RTS_Component).GetLocation());
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHeroWeaponGripTest, "Dink.Art.HeroWeapon.GripClosesTheHand", DINK_TEST_FLAGS)
bool FDinkHeroWeaponGripTest::RunTest(const FString&)
{
	// Art row AN-05: the hand that holds a weapon is closed round its grip under every clip; the other hand is not touched.
	const TCHAR* Folder = TEXT("/Game/Dink/Hero/Animations/Pass1/");
	auto Clip = [Folder](const TCHAR* Name) { return LoadObject<UAnimSequence>(nullptr, *(FString(Folder) + Name + TEXT(".") + Name), nullptr, LOAD_NoWarn | LOAD_Quiet); };
	UAnimSequence* Grip[2] = {Clip(TEXT("AN_Grip_L")), Clip(TEXT("AN_Grip_R"))};
	UAnimSequence* Idle = Clip(TEXT("AN_Idle_Timid"));
	UAnimSequence* Walk = Clip(TEXT("AN_Walk_Timid"));
	USkeletalMesh* Hero = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Hero/Refinements/SK_Dink_Hands.SK_Dink_Hands"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!Grip[0] || !Grip[1] || !Idle || !Walk || !Hero)
	{
		AddWarning(TEXT("skipped: the hero, the grip poses or the pass-1 idle and walk are not imported in this checkout"));
		return true;
	}
	const FReferenceSkeleton& Ref = Hero->GetRefSkeleton();
	const TCHAR* Side[2] = {TEXT("_l"), TEXT("_r")};
	// The clips themselves: the named hand closes (the last joint of every finger comes at least 1 cm nearer the wrist), the other stays open.
	for (int32 S = 0; S < 2; ++S)
	{
		for (int32 H = 0; H < 2; ++H)
		{
			const FName Hand(*(FString(TEXT("hand")) + Side[H]));
			for (const TCHAR* Finger : {TEXT("thumb_03"), TEXT("index_03"), TEXT("middle_03"), TEXT("ring_03"), TEXT("pinky_03")})
			{
				const FName Tip(*(FString(Finger) + Side[H]));
				if (!TestTrue(FString::Printf(TEXT("the hero has %s%s below its hand"), Finger, Side[H]), Ref.FindBoneIndex(Tip) != INDEX_NONE && Ref.FindBoneIndex(Hand) != INDEX_NONE)) return false;
				const double Open = TipInHand(Grip[S], Tip, Hand, 0.).Size(), Closed = TipInHand(Grip[S], Tip, Hand, Grip[S]->GetPlayLength()).Size();
				if (!TestTrue(FString::Printf(TEXT("%s has tracks for %s%s"), *Grip[S]->GetName(), Finger, Side[H]), Open < 1e5)) return false;
				if (H == S && FCString::Strcmp(Finger, TEXT("thumb_03")) != 0)
					TestTrue(FString::Printf(TEXT("%s: %s%s closes (%.1f -> %.1f cm from the wrist)"), *Grip[S]->GetName(), Finger, Side[H], Open, Closed), Closed < Open - 1.);
				if (H != S)
					TestTrue(FString::Printf(TEXT("%s: %s%s of the other hand stays as the stand has it (%.2f -> %.2f cm)"), *Grip[S]->GetName(), Finger, Side[H], Open, Closed), FMath::Abs(Closed - Open) < .5);
			}
		}
	}
	// The layer: a body that plays the idle, told which hand holds something.
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	ON_SCOPE_EXIT { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
	AActor* Stage = World->SpawnActor<AActor>();
	USkeletalMeshComponent* Body = NewObject<USkeletalMeshComponent>(Stage);
	Stage->SetRootComponent(Body);
	Body->SetSkeletalMesh(Hero);
	Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Body->SetAnimInstanceClass(UDinkBodyAnimInstance::StaticClass());
	Body->RegisterComponent();
	Body->InitAnim(true);
	UDinkBodyAnimInstance* Anim = Cast<UDinkBodyAnimInstance>(Body->GetAnimInstance());
	if (!TestNotNull(TEXT("the body runs the native body animation"), Anim)) return false;
	TMap<FName, FDinkBodyClip> Library;
	auto Add = [&Library](const TCHAR* Name, UAnimSequence* Seq, float Speed, float Stride)
	{
		FDinkBodyClip C;
		C.Sequence = Seq; C.Duration = Seq->GetPlayLength(); C.SpeedCm = Speed; C.StrideCm = Stride; C.bLoop = Speed > 0.f;
		Library.Add(Name, C);
	};
	Add(TEXT("Idle"), Idle, 0.f, 0.f);
	Add(TEXT("Walk"), Walk, 140.f, 130.f);
	Add(TEXT("Grip_L"), Grip[0], 0.f, 0.f);
	Add(TEXT("Grip_R"), Grip[1], 0.f, 0.f);
	if (!TestTrue(TEXT("the hero set configures from idle, walk and the two grip poses"), Anim->Configure(Library, TEXT("Hero")))) return false;
	auto Pose = [Body, Anim](FName Hand)
	{
		Anim->SetGrip(Hand);
		Anim->SetMotion(0.f, false, 0.f);
		for (int32 I = 0; I < 3; ++I) Body->TickAnimation(.1f, false); // longer than the blend: the weight has arrived
		Body->RefreshBoneTransforms();
	};
	const FName HandName[2] = {TEXT("hand_l"), TEXT("hand_r")};
	const FName TipName[2] = {TEXT("middle_03_l"), TEXT("middle_03_r")};
	Pose(NAME_None);
	const FVector Free[2] = {TipInHand(Body, TipName[0], HandName[0]), TipInHand(Body, TipName[1], HandName[1])};
	TestEqual(TEXT("empty hands: no grip pose is layered"), Anim->GetFrame().Grip[0].Weight + Anim->GetFrame().Grip[1].Weight, 0.f);
	for (int32 S = 0; S < 2; ++S)
	{
		Pose(HandName[S]);
		const FDinkBodyFrame& Frame = Anim->GetFrame();
		TestEqual(FString::Printf(TEXT("%s holds: its grip pose is fully in"), *HandName[S].ToString()), Frame.Grip[S].Weight, 1.f);
		TestTrue(TEXT("and it is the clip's held last frame"), Frame.Grip[S].Sequence == Grip[S] && FMath::IsNearlyEqual(Frame.Grip[S].Time, Grip[S]->GetPlayLength(), .001f));
		TestEqual(TEXT("the other hand's pose is out"), Frame.Grip[1 - S].Weight, 0.f);
		const FVector Want = TipInHand(Grip[S], TipName[S], HandName[S], Grip[S]->GetPlayLength());
		const FVector Got = TipInHand(Body, TipName[S], HandName[S]), Other = TipInHand(Body, TipName[1 - S], HandName[1 - S]);
		TestTrue(FString::Printf(TEXT("%s: the posed finger tip is where the grip pose has it (%.2f cm off)"), *HandName[S].ToString(), FVector::Dist(Got, Want)), FVector::Dist(Got, Want) < .1);
		TestTrue(FString::Printf(TEXT("that is a closed hand, not the idle's (%.1f cm from the open tip)"), FVector::Dist(Got, Free[S])), FVector::Dist(Got, Free[S]) > 2.);
		TestTrue(FString::Printf(TEXT("the other hand keeps the idle's fingers (%.2f cm off)"), FVector::Dist(Other, Free[1 - S])), FVector::Dist(Other, Free[1 - S]) < .1);
	}
	Pose(NAME_None);
	TestTrue(TEXT("disarmed: the hand opens again"), FVector::Dist(TipInHand(Body, TipName[1], HandName[1]), Free[1]) < .1);
	// The weapon in the hand tells the body which hand: sword right, bow left, fists none.
	DinkHeroWeapons::Reload();
	// The closed fingers lie round the handle, not in it: with the weapon where its row puts it (+X along the grip, the
	// handles 1.3 to 1.7 cm in radius), every finger joint past the knuckle is 1.9 to 3.4 cm from the grip's axis.
	for (const TCHAR* Item : {TEXT("item-sw1"), TEXT("item-axe"), TEXT("item-b1")})
	{
		const FDinkHeroWeaponRow* Row = DinkHeroWeapons::Find(FName(Item));
		if (!TestNotNull(FString::Printf(TEXT("%s has a row"), Item), Row)) continue;
		Pose(Row->Bone);
		const FTransform Handle = FTransform(Row->Rotation, Row->Location) * Body->GetBoneTransform(Row->Bone, RTS_Component);
		const TCHAR* Sd = Row->Bone == FName(TEXT("hand_l")) ? TEXT("_l") : TEXT("_r");
		FString Line;
		for (const TCHAR* Finger : {TEXT("thumb"), TEXT("index"), TEXT("middle"), TEXT("ring"), TEXT("pinky")})
		{
			for (const TCHAR* Joint : {TEXT("_02"), TEXT("_03")})
			{
				const FVector P = Handle.InverseTransformPosition(Body->GetBoneTransform(FName(*(FString(Finger) + Joint + Sd)), RTS_Component).GetLocation());
				const double R = FMath::Sqrt(P.Y * P.Y + P.Z * P.Z);
				Line += FString::Printf(TEXT(" %s%s x %.1f r %.1f |"), Finger, Joint, P.X, R);
				TestTrue(FString::Printf(TEXT("%s: %s%s%s lies round the handle (%.2f cm from its axis)"), Item, Finger, Joint, Sd, R), R > 1.9 && R < 3.4);
			}
		}
		AddInfo(FString::Printf(TEXT("GRIP %s on %s:%s"), Item, *Row->Bone.ToString(), *Line));
	}
	// The carry: with no action playing, the arm that holds the weapon stands on guard as the armed Dink of 1997 does
	// (hand at the waist, blade up); dink.Anim.WeaponCarry 0 leaves the arm to the clip (it hangs, the blade about level).
	IConsoleVariable* CarryVar = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Anim.WeaponCarry"));
	const FDinkHeroWeaponRow* Sword = DinkHeroWeapons::Find(TEXT("item-sw1"));
	if (TestNotNull(TEXT("dink.Anim.WeaponCarry exists"), CarryVar) && Sword)
	{
		auto Blade = [Body, Sword]()
		{
			const FTransform Handle = FTransform(Sword->Rotation, Sword->Location) * Body->GetBoneTransform(Sword->Bone, RTS_Component);
			return FVector2D(Handle.GetUnitAxis(EAxis::X).Z, Handle.GetLocation().Z);
		};
		const int32 Was = CarryVar->GetInt();
		CarryVar->Set(0);
		Pose(Sword->Bone);
		const FVector2D Hanging = Blade();
		CarryVar->Set(1);
		Pose(Sword->Bone);
		const FVector2D Guard = Blade();
		CarryVar->Set(Was);
		AddInfo(FString::Printf(TEXT("CARRY item-sw1: blade up-component %.2f at grip height %.0f cm on guard; %.2f at %.0f cm with the carry off"), Guard.X, Guard.Y, Hanging.X, Hanging.Y));
		TestTrue(FString::Printf(TEXT("on guard the blade stands up (up-component %.2f)"), Guard.X), Guard.X > .75);
		TestTrue(FString::Printf(TEXT("and the hand is raised to the waist (%.0f cm above where it hangs)"), Guard.Y - Hanging.Y), Guard.Y - Hanging.Y > 12.);
		TestTrue(FString::Printf(TEXT("carry off: the arm is the clip's again, the blade lower and flatter (up-component %.2f)"), Hanging.X), Hanging.X < Guard.X - .2);
	}
	Pose(NAME_None);
	if (DinkHeroWeapons::Apply(Stage, TEXT("item-sw1"), true))
	{
		TestEqual(TEXT("the longsword closes the right hand"), Anim->GetGrip(), FName(TEXT("hand_r")));
		DinkHeroWeapons::Apply(Stage, TEXT("item-b1"), true);
		TestEqual(TEXT("a bow closes the left hand"), Anim->GetGrip(), FName(TEXT("hand_l")));
		DinkHeroWeapons::Apply(Stage, TEXT("item-fst"), true);
		TestEqual(TEXT("fists: no hand is held closed by the layer"), Anim->GetGrip(), FName(NAME_None));
	}
	else AddWarning(TEXT("weapon part skipped: the weapon meshes are not imported in this checkout"));
	return true;
}
