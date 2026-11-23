#include "DinkHeroWeapon.h"
#include "DinkBodyAnimInstance.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkGameplay.h"
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
TAutoConsoleVariable<int32> CVarHeroWeapons(TEXT("dink.Hero.Weapons"), 1,
	TEXT("Presentation only. 1: the armed weapon's mesh is in Dink's hand while it is armed (hero_weapons.json, bug A203); 0: empty hands."));
const FName HeldTag(TEXT("DinkHeroWeapon"));

// The hand that holds the mesh closes round its grip (art row AN-05): told to the body's animation, which owns the pose.
void SetGrip(USceneComponent* Body, FName Hand)
{
	const USkeletalMeshComponent* Mesh = Cast<USkeletalMeshComponent>(Body);
	if (UDinkBodyAnimInstance* Anim = Mesh ? Cast<UDinkBodyAnimInstance>(Mesh->GetAnimInstance()) : nullptr) Anim->SetGrip(Hand);
}

struct FWeaponTable
{
	TMap<FName, FDinkHeroWeaponRow> Rows;
	bool bLoaded = false;
};
FWeaponTable& Table()
{
	static FWeaponTable T;
	return T;
}
bool Numbers(const FJsonObject& O, const TCHAR* Name, double Out[3])
{
	const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
	if (!O.TryGetArrayField(Name, A) || A->Num() != 3) return false;
	for (int32 I = 0; I < 3; ++I) Out[I] = (*A)[I]->AsNumber();
	return true;
}
void Load()
{
	FWeaponTable& T = Table();
	T.Rows.Reset();
	T.bLoaded = true;
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/hero_weapons.json"))) ||
		!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root) return;
	const TSharedPtr<FJsonObject>* Items = nullptr;
	if (!Root->TryGetObjectField(TEXT("items"), Items) || !Items) return;
	for (const auto& Pair : (*Items)->Values)
	{
		const TSharedPtr<FJsonObject> O = Pair.Value.IsValid() ? Pair.Value->AsObject() : nullptr;
		FDinkHeroWeaponRow Row;
		FString Bone;
		double L[3], R[3];
		if (!O || !O->TryGetStringField(TEXT("mesh"), Row.Mesh) || !O->TryGetStringField(TEXT("bone"), Bone) ||
			!Numbers(*O, TEXT("location_cm"), L) || !Numbers(*O, TEXT("rotation_deg"), R)) continue;
		Row.Bone = FName(*Bone);
		Row.Location = FVector(L[0], L[1], L[2]);
		Row.Rotation = FRotator(R[0], R[1], R[2]); // pitch, yaw, roll as the art kit gives them
		T.Rows.Add(FName(*Pair.Key), Row);
	}
}
}

const FDinkHeroWeaponRow* DinkHeroWeapons::Find(FName ItemScript)
{
	if (!Table().bLoaded) Load();
	return ItemScript.IsNone() ? nullptr : Table().Rows.Find(ItemScript);
}

void DinkHeroWeapons::Reload()
{
	Load();
}

USkeletalMeshComponent* DinkHeroWeapons::FindBody(AActor* Hero, FName Bone)
{
	if (!Hero) return nullptr;
	TArray<USkeletalMeshComponent*> Bodies;
	Hero->GetComponents<USkeletalMeshComponent>(Bodies);
	USkeletalMeshComponent* Best = nullptr;
	for (USkeletalMeshComponent* C : Bodies)
	{
		if (!C || !C->IsVisible() || !C->GetSkeletalMeshAsset() || C->GetBoneIndex(Bone) == INDEX_NONE) continue;
		if (!C->LeaderPoseComponent.IsValid()) return C;
		if (!Best) Best = C;
	}
	return Best;
}

UStaticMeshComponent* DinkHeroWeapons::Apply(AActor* Hero, FName ItemScript, bool bShow)
{
	if (!Hero) return nullptr;
	UStaticMeshComponent* Held = nullptr;
	TArray<UStaticMeshComponent*> Comps;
	Hero->GetComponents<UStaticMeshComponent>(Comps);
	for (UStaticMeshComponent* C : Comps) if (C && C->ComponentHasTag(HeldTag)) { Held = C; break; }
	const FDinkHeroWeaponRow* Row = bShow ? Find(ItemScript) : nullptr;
	UStaticMesh* Mesh = Row ? LoadObject<UStaticMesh>(nullptr, *Row->Mesh, nullptr, LOAD_NoWarn | LOAD_Quiet) : nullptr;
	USkeletalMeshComponent* Body = Mesh ? FindBody(Hero, Row->Bone) : nullptr;
	if (!Body)
	{
		if (Held)
		{
			SetGrip(Held->GetAttachParent(), NAME_None);
			Held->SetVisibility(false);
		}
		return nullptr;
	}
	if (!Held)
	{
		Held = NewObject<UStaticMeshComponent>(Hero);
		Held->SetMobility(EComponentMobility::Movable);
		Held->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Held->SetGenerateOverlapEvents(false);
		Held->SetCanEverAffectNavigation(false);
		Held->ComponentTags.Add(HeldTag);
		Hero->AddInstanceComponent(Held);
		Held->SetupAttachment(Body, Row->Bone);
		Held->RegisterComponent();
	}
	if (Held->GetAttachParent() != Body || Held->GetAttachSocketName() != Row->Bone)
	{
		SetGrip(Held->GetAttachParent(), NAME_None);
		Held->AttachToComponent(Body, FAttachmentTransformRules::KeepRelativeTransform, Row->Bone);
	}
	SetGrip(Body, Row->Bone);
	if (Held->GetStaticMesh() != Mesh) Held->SetStaticMesh(Mesh);
	Held->SetRelativeLocationAndRotation(Row->Location, Row->Rotation);
	Held->SetVisibility(true);
	return Held;
}

void UDinkHeroWeaponSubsystem::Tick(float)
{
	UWorld* World = GetWorld();
	const UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
	UDinkStorySubsystem* Story = Instance ? Instance->GetSubsystem<UDinkStorySubsystem>() : nullptr;
	UDinkDirector* Director = Story ? Story->GetDirector() : nullptr;
	const UDinkGameplay* Game = Story ? Story->GetGameplay() : nullptr;
	AActor* Hero = Director ? Director->GetDink().Actor.Get() : nullptr;
	if (!Hero || !Game) return;
	FName Item;
	if (const FDinkScriptInstance* Weapon = Story->FindInstance(Game->GetWeaponInstance()); Weapon && Weapon->IsAlive()) Item = Weapon->Script;
	// A dead Dink drops nothing in 1997 either: his death pictures (436) carry no weapon.
	const UDinkFactSubsystem* Facts = Story->GetFacts();
	const bool bAlive = !Facts || Facts->GetFact(TEXT("life")) > 0;
	const bool bShow = CVarHeroWeapons.GetValueOnGameThread() != 0 && bAlive;
	Shown = DinkHeroWeapons::Apply(Hero, Item, bShow) ? Item : NAME_None;
}

namespace
{
// Review only (captures of A203): puts an item in the pack and arms it, as buying it and choosing it on the item screen do.
FAutoConsoleCommandWithWorldAndArgs HeroGiveWeapon(TEXT("dink.Hero.GiveWeapon"),
	TEXT("dink.Hero.GiveWeapon <item script>: review only. add_item of that item (its pickup runs) and arm it (ArmItemSlot), as buying and choosing it would."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
{
	const UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
	UDinkStorySubsystem* Story = Instance ? Instance->GetSubsystem<UDinkStorySubsystem>() : nullptr;
	UDinkGameplay* Game = Story ? Story->GetGameplay() : nullptr;
	if (!Game || Args.Num() < 1) return;
	const int32 Slot = Game->AddItem(FName(*Args[0]), false);
	const bool bArmed = Slot >= 0 && Game->ArmItemSlot(Slot + 1); // AddItem gives the 0-based slot, ArmItemSlot takes 1-16
	Story->RunUntilIdle();
	UE_LOG(LogTemp, Display, TEXT("dink.Hero.GiveWeapon %s: slot %d %s"), *Args[0], Slot + 1, bArmed ? TEXT("armed") : TEXT("not armed"));
}));
}
