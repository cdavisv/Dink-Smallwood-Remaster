#include "DinkHeroBow.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkHeroWeapon.h"
#include "DinkStorySubsystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
TAutoConsoleVariable<float> CVarBowDraw(TEXT("dink.Hero.BowDraw"), -1.0f,
	TEXT("Presentation only, review. -1: the bow's string follows the string hand while the bow is drawn (art row AN-05); 0 or more: the draw in cm, whatever the game does; -2: the string follows the string hand whether the bow is drawn or not (a look at `dink.Hero.Play Bow_Draw hold`)."));
const FName HeldTag(TEXT("DinkHeroWeapon")); // DinkHeroWeapons::Apply's component
const FName PartTag(TEXT("DinkHeroBowPart"));

struct FWorn
{
	FString Mesh;
	FName Bone;
	FVector Location = FVector::ZeroVector;
	FRotator Rotation = FRotator::ZeroRotator;
};
struct FBowTable
{
	TMap<FName, FDinkHeroBowRow> Rows;
	TArray<FName> StringFingers;
	double FollowNear = 6.0, FollowFar = 16.0;
	FString Arrow;
	double ArrowRestZ = 0.0, ArrowAwaySeconds = 0.45;
	FWorn Quiver;
	bool bLoaded = false;
};
FBowTable& Table()
{
	static FBowTable T;
	return T;
}
bool Numbers(const FJsonObject& O, const TCHAR* Name, TArray<double>& Out, int32 Count)
{
	const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
	Out.Reset();
	if (!O.TryGetArrayField(Name, A) || (Count > 0 && A->Num() != Count)) return false;
	for (const TSharedPtr<FJsonValue>& V : *A) Out.Add(V->AsNumber());
	return true;
}
void Load()
{
	FBowTable& T = Table();
	T = FBowTable();
	T.bLoaded = true;
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/hero_weapons.json"))) ||
		!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root) return;
	const TSharedPtr<FJsonObject>* Bows = nullptr;
	if (!Root->TryGetObjectField(TEXT("bows"), Bows) || !Bows) return;
	const TArray<TSharedPtr<FJsonValue>>* Fingers = nullptr;
	if ((*Bows)->TryGetArrayField(TEXT("string_fingers"), Fingers)) for (const TSharedPtr<FJsonValue>& V : *Fingers) T.StringFingers.Add(FName(*V->AsString()));
	TArray<double> N;
	if (Numbers(**Bows, TEXT("follow_cm"), N, 2)) { T.FollowNear = N[0]; T.FollowFar = FMath::Max(N[1], N[0] + 0.1); }
	const TSharedPtr<FJsonObject>* Arrow = nullptr;
	if ((*Bows)->TryGetObjectField(TEXT("arrow"), Arrow) && Arrow)
	{
		(*Arrow)->TryGetStringField(TEXT("mesh"), T.Arrow);
		(*Arrow)->TryGetNumberField(TEXT("rest_z_cm"), T.ArrowRestZ);
		(*Arrow)->TryGetNumberField(TEXT("away_after_shot_s"), T.ArrowAwaySeconds);
	}
	const TSharedPtr<FJsonObject>* Worn = nullptr;
	if ((*Bows)->TryGetObjectField(TEXT("worn"), Worn) && Worn)
	{
		FString Bone;
		TArray<double> L, R;
		if ((*Worn)->TryGetStringField(TEXT("mesh"), T.Quiver.Mesh) && (*Worn)->TryGetStringField(TEXT("bone"), Bone) &&
			Numbers(**Worn, TEXT("location_cm"), L, 3) && Numbers(**Worn, TEXT("rotation_deg"), R, 3))
		{
			T.Quiver.Bone = FName(*Bone);
			T.Quiver.Location = FVector(L[0], L[1], L[2]);
			T.Quiver.Rotation = FRotator(R[0], R[1], R[2]); // pitch, yaw, roll, as the weapon rows
		}
		else T.Quiver = FWorn();
	}
	const TSharedPtr<FJsonObject>* Items = nullptr;
	if (!(*Bows)->TryGetObjectField(TEXT("items"), Items) || !Items) return;
	for (const auto& Pair : (*Items)->Values)
	{
		const TSharedPtr<FJsonObject> O = Pair.Value.IsValid() ? Pair.Value->AsObject() : nullptr;
		const TSharedPtr<FJsonObject>* D = nullptr;
		FDinkHeroBowRow Row;
		if (!O || !O->TryGetStringField(TEXT("parts"), Row.Parts) || !O->TryGetObjectField(TEXT("draw"), D) || !D) continue;
		const TArray<TSharedPtr<FJsonValue>>* Joints = nullptr;
		TArray<double> End;
		if (!(*D)->TryGetArrayField(TEXT("joints_cm"), Joints) || !Numbers(**D, TEXT("weights"), Row.Draw.Weights, Joints->Num()) || Joints->Num() < 1 ||
			!Numbers(**D, TEXT("string_end_cm"), End, 2) || !(*D)->TryGetNumberField(TEXT("nock_up_cm"), Row.Draw.NockUp) ||
			!(*D)->TryGetNumberField(TEXT("max_draw_cm"), Row.Draw.MaxDraw)) continue;
		bool bGood = true;
		for (const TSharedPtr<FJsonValue>& J : *Joints)
		{
			const TArray<TSharedPtr<FJsonValue>>& P = J->AsArray();
			if (P.Num() != 2) { bGood = false; break; }
			Row.Draw.Joints.Add(FVector2D(P[0]->AsNumber(), P[1]->AsNumber()));
		}
		if (!bGood) continue;
		Row.Draw.StringEnd = FVector2D(End[0], End[1]);
		T.Rows.Add(FName(*Pair.Key), Row);
	}
}

// The upper limb at a bend: each segment turns about its joint by its share more than the one before (+Z: X towards the string side).
FVector2D Limb(const FDinkHeroBowDraw& D, double Bend, TArray<FVector>* Segments)
{
	FVector2D At = D.Joints[0];
	double Turn = 0.0;
	for (int32 K = 0; K < D.Joints.Num(); ++K)
	{
		Turn += Bend * D.Weights[K];
		const FVector2D Next = K + 1 < D.Joints.Num() ? D.Joints[K + 1] : D.StringEnd;
		const FVector2D V = Next - D.Joints[K];
		if (Segments) Segments->Add(FVector(At.X, At.Y, FMath::RadiansToDegrees(Turn)));
		At += FVector2D(V.X * FMath::Cos(Turn) - V.Y * FMath::Sin(Turn), V.X * FMath::Sin(Turn) + V.Y * FMath::Cos(Turn));
	}
	return At;
}

UStaticMeshComponent* Part(AActor* Hero, FName Key, bool bMake)
{
	TArray<UStaticMeshComponent*> Comps;
	Hero->GetComponents<UStaticMeshComponent>(Comps);
	for (UStaticMeshComponent* C : Comps) if (C && C->ComponentHasTag(PartTag) && C->ComponentHasTag(Key)) return C;
	if (!bMake) return nullptr;
	UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(Hero);
	C->SetMobility(EComponentMobility::Movable);
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	C->SetGenerateOverlapEvents(false);
	C->SetCanEverAffectNavigation(false);
	C->ComponentTags.Add(PartTag);
	C->ComponentTags.Add(Key);
	Hero->AddInstanceComponent(C);
	return C;
}
void Hide(AActor* Hero)
{
	TArray<UStaticMeshComponent*> Comps;
	Hero->GetComponents<UStaticMeshComponent>(Comps);
	for (UStaticMeshComponent* C : Comps) if (C && C->ComponentHasTag(PartTag)) C->SetVisibility(false);
}
// One part on its parent with a mesh and a relative place; false (and hidden) when the mesh is not imported.
bool Place(AActor* Hero, FName Key, const FString& MeshPath, USceneComponent* Parent, FName Socket, const FTransform& Relative)
{
	UStaticMesh* Mesh = MeshPath.IsEmpty() ? nullptr : LoadObject<UStaticMesh>(nullptr, *MeshPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	UStaticMeshComponent* C = Part(Hero, Key, Mesh != nullptr);
	if (!C) return false;
	if (!Mesh) { C->SetVisibility(false); return false; }
	if (!C->IsRegistered())
	{
		C->SetupAttachment(Parent, Socket);
		C->RegisterComponent();
	}
	else if (C->GetAttachParent() != Parent || C->GetAttachSocketName() != Socket) C->AttachToComponent(Parent, FAttachmentTransformRules::KeepRelativeTransform, Socket);
	if (C->GetStaticMesh() != Mesh) C->SetStaticMesh(Mesh);
	C->SetRelativeTransform(Relative);
	C->SetVisibility(true);
	return true;
}
UStaticMeshComponent* HeldBow(AActor* Hero)
{
	TArray<UStaticMeshComponent*> Comps;
	Hero->GetComponents<UStaticMeshComponent>(Comps);
	for (UStaticMeshComponent* C : Comps) if (C && C->ComponentHasTag(HeldTag)) return C->IsVisible() ? C : nullptr;
	return nullptr;
}
FString PartPath(const FDinkHeroBowRow& Row, const FString& Name)
{
	const FString Package = Row.Parts.Replace(TEXT("%s"), *Name);
	return Package + TEXT(".") + FPaths::GetBaseFilename(Package);
}
}

FDinkHeroBowPose DinkHeroBow::Solve(const FDinkHeroBowDraw& D, double DrawCm)
{
	FDinkHeroBowPose Out;
	if (D.Joints.Num() < 1 || D.Weights.Num() != D.Joints.Num()) return Out;
	Out.Apex = FVector2D(D.NockUp, D.StringEnd.Y + FMath::Clamp(DrawCm, 0.0, D.MaxDraw));
	const double Length = 2.0 * D.StringEnd.X; // the two halves at rest: (end - nock) + (end + nock)
	const auto Slack = [&](double Bend)
	{
		const FVector2D Tip = Limb(D, Bend, nullptr);
		return FVector2D::Distance(Tip, Out.Apex) + FVector2D::Distance(FVector2D(-Tip.X, Tip.Y), Out.Apex) - Length;
	};
	double Lo = 0.0, Hi = 1.6;
	for (int32 I = 0; I < 40; ++I)
	{
		const double Mid = 0.5 * (Lo + Hi);
		(Slack(Mid) > 0.0 ? Lo : Hi) = Mid;
	}
	Out.Bend = 0.5 * (Lo + Hi);
	Out.Tip = Limb(D, Out.Bend, &Out.Segments);
	return Out;
}

const FDinkHeroBowRow* DinkHeroBow::Find(FName ItemScript)
{
	if (!Table().bLoaded) Load();
	return ItemScript.IsNone() ? nullptr : Table().Rows.Find(ItemScript);
}

void DinkHeroBow::Reload()
{
	Load();
}

UStaticMeshComponent* DinkHeroBow::FindPart(AActor* Hero, FName Key)
{
	return Hero ? Part(Hero, Key, false) : nullptr;
}

bool DinkHeroBow::Apply(AActor* Hero, FName ItemScript, double DrawCm, bool bArrow)
{
	if (!Hero) return false;
	const FDinkHeroBowRow* Row = Find(ItemScript);
	UStaticMeshComponent* Held = Row ? HeldBow(Hero) : nullptr;
	if (!Held)
	{
		Hide(Hero);
		return false;
	}
	const FBowTable& T = Table();
	const FDinkHeroBowPose Pose = Solve(Row->Draw, DrawCm);
	for (int32 K = 0; K < Pose.Segments.Num(); ++K)
	{
		const FVector& S = Pose.Segments[K];
		Place(Hero, FName(*FString::Printf(TEXT("LimbU%d"), K + 1)), PartPath(*Row, FString::Printf(TEXT("LimbU%d"), K + 1)), Held, NAME_None,
			FTransform(FRotator(0.0, S.Z, 0.0), FVector(S.X, S.Y, 0.0)));
		Place(Hero, FName(*FString::Printf(TEXT("LimbL%d"), K + 1)), PartPath(*Row, FString::Printf(TEXT("LimbL%d"), K + 1)), Held, NAME_None,
			FTransform(FRotator(0.0, -S.Z, 0.0), FVector(-S.X, S.Y, 0.0)));
	}
	// The string: each half runs from its limb tip (its origin, +X along it) to the pull point, stretched to reach it.
	const double Rest[2] = {Row->Draw.StringEnd.X - Row->Draw.NockUp, Row->Draw.StringEnd.X + Row->Draw.NockUp};
	for (int32 Side = 0; Side < 2; ++Side)
	{
		const FVector2D Tip(Side == 0 ? Pose.Tip.X : -Pose.Tip.X, Pose.Tip.Y);
		const FVector2D To = Pose.Apex - Tip;
		const FName Key(Side == 0 ? TEXT("StringU") : TEXT("StringL"));
		Place(Hero, Key, PartPath(*Row, Key.ToString()), Held, NAME_None,
			FTransform(FRotator(0.0, FMath::RadiansToDegrees(FMath::Atan2(To.Y, To.X)), 0.0), FVector(Tip.X, Tip.Y, 0.0), FVector(To.Size() / FMath::Max(Rest[Side], 1.0), 1.0, 1.0)));
	}
	// The arrow: its nock (the mesh origin) on the string at the pull point, its shaft past the side of the stave.
	const FVector Nock(Pose.Apex.X, Pose.Apex.Y, 0.0);
	const FVector PastStave(Row->Draw.NockUp, 0.0, T.ArrowRestZ);
	if (!bArrow || !Place(Hero, TEXT("Arrow"), T.Arrow, Held, NAME_None, FTransform(FRotationMatrix::MakeFromXZ(PastStave - Nock, FVector::XAxisVector).Rotator(), Nock)))
	{
		if (UStaticMeshComponent* Arrow = Part(Hero, TEXT("Arrow"), false)) Arrow->SetVisibility(false);
	}
	// The quiver, on the body the bow hangs on.
	USkeletalMeshComponent* Body = Cast<USkeletalMeshComponent>(Held->GetAttachParent());
	if (!Body || T.Quiver.Bone.IsNone() || Body->GetBoneIndex(T.Quiver.Bone) == INDEX_NONE ||
		!Place(Hero, TEXT("Quiver"), T.Quiver.Mesh, Body, T.Quiver.Bone, FTransform(T.Quiver.Rotation, T.Quiver.Location)))
	{
		if (UStaticMeshComponent* Quiver = Part(Hero, TEXT("Quiver"), false)) Quiver->SetVisibility(false);
	}
	return true;
}

double DinkHeroBow::DrawFromHand(AActor* Hero, FName ItemScript)
{
	const FDinkHeroBowRow* Row = Hero ? Find(ItemScript) : nullptr;
	UStaticMeshComponent* Held = Row ? HeldBow(Hero) : nullptr;
	USkeletalMeshComponent* Body = Held ? Cast<USkeletalMeshComponent>(Held->GetAttachParent()) : nullptr;
	const FBowTable& T = Table();
	if (!Body || T.StringFingers.Num() == 0) return 0.0;
	FVector Sum = FVector::ZeroVector;
	for (const FName& Bone : T.StringFingers)
	{
		if (Body->GetBoneIndex(Bone) == INDEX_NONE) return 0.0;
		Sum += Body->GetSocketLocation(Bone);
	}
	// The fingers in the bow's own axes: beside the string's line they hold nothing; on it, the string is where they are.
	const FVector Hook = Held->GetComponentTransform().InverseTransformPosition(Sum / T.StringFingers.Num());
	const double Beside = FMath::Sqrt(FMath::Square(Hook.X - Row->Draw.NockUp) + FMath::Square(Hook.Z));
	const double Holds = 1.0 - FMath::SmoothStep(T.FollowNear, T.FollowFar, Beside);
	return FMath::Clamp(Hook.Y - Row->Draw.StringEnd.Y, 0.0, Row->Draw.MaxDraw) * Holds;
}

void UDinkHeroBowSubsystem::Tick(float DeltaTime)
{
	UWorld* World = GetWorld();
	const UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
	UDinkStorySubsystem* Story = Instance ? Instance->GetSubsystem<UDinkStorySubsystem>() : nullptr;
	UDinkDirector* Director = Story ? Story->GetDirector() : nullptr;
	const UDinkGameplay* Game = Story ? Story->GetGameplay() : nullptr;
	const UDinkHeroWeaponSubsystem* Weapons = World ? World->GetSubsystem<UDinkHeroWeaponSubsystem>() : nullptr;
	AActor* Hero = Director ? Director->GetDink().Actor.Get() : nullptr;
	if (!Hero || !Game || !Weapons) return;
	const FName Item = Weapons->GetShownItem();
	const bool bActive = Game->IsBowActive();
	const double Now = World->GetTimeSeconds();
	const float Forced = CVarBowDraw.GetValueOnGameThread();
	if (Forced >= 0.0f) DrawCm = Forced;
	else if (bActive || Forced < -1.5f) DrawCm = DinkHeroBow::DrawFromHand(Hero, Item);
	else DrawCm = DrawCm < 0.5 ? 0.0 : FMath::FInterpTo(DrawCm, 0.0, DeltaTime, 90.0); // the loosed string is back in two frames
	// 1997: under 100 the script leaves without an arrow (item-b1.c use); above it the arrow is the missile for a moment.
	if (bWasActive && !bActive && Game->GetLastBowPower() >= 100) ArrowBackAt = Now + Table().ArrowAwaySeconds;
	bWasActive = bActive;
	DinkHeroBow::Apply(Hero, Item, DrawCm, Now >= ArrowBackAt);
}
