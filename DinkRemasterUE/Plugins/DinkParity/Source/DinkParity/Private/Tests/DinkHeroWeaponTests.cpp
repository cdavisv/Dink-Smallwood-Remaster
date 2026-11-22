#include "Misc/AutomationTest.h"
#include "DinkTestHelpers.h"
#include "DinkHeroWeapon.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
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
