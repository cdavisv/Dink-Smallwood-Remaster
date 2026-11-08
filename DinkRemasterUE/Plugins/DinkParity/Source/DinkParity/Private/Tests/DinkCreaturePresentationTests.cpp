#include "DinkTestHelpers.h"
#include "DinkCreatureComponent.h"
#include "DinkCreatureSubsystem.h"
#include "DinkDirector.h"
#include "DinkScriptSpriteComponent.h"
#include "DinkGameplay.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/BlendSpace.h"
#include "AssetCompilingManager.h"
#include "Components/BoxComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
namespace
{
struct FCreatureWorld
{
	UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
	FCreatureWorld()
	{
		GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
	}
	~FCreatureWorld()
	{
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
	}
	AActor* Actor(FVector At = FVector::ZeroVector)
	{
		AActor* A = World->SpawnActor<AActor>();
		USceneComponent* Root = NewObject<USceneComponent>(A);
		A->SetRootComponent(Root);
		Root->RegisterComponent();
		A->SetActorLocation(At);
		return A;
	}
};
} // namespace
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureLocomotionTest,
								 "Dink.Art.CreaturePresentation.ActorLocomotionAndPhysicalFood", DINK_TEST_FLAGS)
bool FDinkCreatureLocomotionTest::RunTest(const FString&)
{
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(
		nullptr, TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
	UBlendSpace* BS = LoadObject<UBlendSpace>(
		nullptr, TEXT("/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run.BS_Idle_Walk_Run"));
	if (!Mesh || !BS)
	{
		AddWarning(TEXT("skipped: template rig missing"));
		return true;
	}
	FAssetCompilingManager::Get().FinishAllCompilation();
	UAnimSequence* Feed = BS->GetBlendSamples().Num() ? Cast<UAnimSequence>(BS->GetBlendSample(0).Animation) : nullptr;
	if (!TestNotNull(TEXT("compatible feed fixture sequence"), Feed))
		return false;
	FCreatureWorld E;
	AActor* Owner = E.Actor();
	UDinkCreatureComponent* Creature = NewObject<UDinkCreatureComponent>(Owner);
	Creature->SetupAttachment(Owner->GetRootComponent());
	Creature->RegisterComponent();
	FDinkCreaturePresentation Settings;
	Settings.NominalRunSpeedCmS = 400;
	TestTrue(TEXT("component accepts compatible arbitrary skeleton"), Creature->Configure(Mesh, BS, Feed, Settings));
	Creature->TickComponent(.1f, LEVELTICK_All, nullptr);
	TestEqual(TEXT("first sample idle"), Creature->GetLocomotionSpeed(), 0.f);
	Owner->SetActorLocation(FVector(100, 0, 0));
	Creature->TickComponent(.1f, LEVELTICK_All, nullptr);
	TestTrue(TEXT("measures actual world speed"), FMath::IsNearlyEqual(Creature->GetLocomotionSpeed(), 1000.f, .01f));
	TestTrue(TEXT("fast movement plays400cm run at2.5rate"),
			 FMath::IsNearlyEqual(Creature->GetSingleNodeInstance()->GetPlayRate(), 2.5f));
	FVector Position, Filtered;
	Creature->GetSingleNodeInstance()->GetBlendSpaceState(Position, Filtered);
	bool bNamedSpeed = false;
	for (int32 Axis = 0; Axis < 3; ++Axis)
	{
		if (BS->GetBlendParameter(Axis).DisplayName.Contains(TEXT("Speed")))
		{
			bNamedSpeed = true;
			TestTrue(TEXT("actual speed axis reaches highest available gait"),
					 FMath::IsNearlyEqual(Position[Axis], double(BS->GetBlendParameter(Axis).Max), .01));
		}
		else
			TestTrue(TEXT("world speed never drives direction or unused axis"), FMath::IsNearlyZero(Position[Axis]));
	}
	TestTrue(TEXT("locomotion fixture exposes speed axis"), bNamedSpeed);
	Owner->SetActorLocation(FVector(1100, 0, 0));
	Creature->TickComponent(.1f, LEVELTICK_All, nullptr);
	TestEqual(TEXT("teleport resets idle instead of gallop burst"), Creature->GetLocomotionSpeed(), 0.f);
	Creature->TickComponent(.1f, LEVELTICK_All, nullptr);
	const FVector Head = Creature->GetSocketLocation(TEXT("head"));
	TestFalse(TEXT("food beyond70cm head reach rejected"), Creature->CanFeedAt(Head + FVector(80, 0, 0)));
	TestFalse(TEXT("nearby food behind the head rejected"), Creature->CanFeedAt(Head - FVector(40, 0, 0)));
	TestTrue(TEXT("nearby food in front of head reachable"), Creature->CanFeedAt(Head + FVector(40, 0, 0)));
	AActor* Food = E.Actor(Head + FVector(40, 0, 0));
	Food->SetActorHiddenInGame(true);
	TestFalse(TEXT("hidden grain cannot start feeding"), Creature->TryFeed(Food));
	Food->SetActorHiddenInGame(false);
	TestTrue(TEXT("real visible grain starts one shot"), Creature->TryFeed(Food));
	TestTrue(TEXT("feed animation asset actually plays"),
			 Creature->IsFeeding() && Creature->GetSingleNodeInstance()->GetAnimationAsset() == Feed);
	TestEqual(TEXT("feed always plays at natural rate"), Creature->GetSingleNodeInstance()->GetPlayRate(), 1.f);
	Owner->AddActorWorldOffset(FVector(10, 0, 0));
	Creature->TickComponent(.1f, LEVELTICK_All, nullptr);
	TestFalse(TEXT("movement interrupts feed without freezing brain"), Creature->IsFeeding());
	Creature->TickComponent(.1f, LEVELTICK_All, nullptr);
	TestFalse(TEXT("same grain does not retrigger a repeated fake feed"), Creature->TryFeed(Food));
	TestTrue(TEXT("locomotion asset resumes after feed"), Creature->GetSingleNodeInstance()->GetAnimationAsset() == BS);
	TestFalse(TEXT("missing mesh rejected without replacing current animation"),
			  Creature->Configure(nullptr, BS, Feed, Settings));
	TestTrue(TEXT("failed configuration leaves existing locomotion intact"),
			 Creature->GetSingleNodeInstance()->GetAnimationAsset() == BS);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureOriginalActorsTest,
								 "Dink.Art.CreaturePresentation.OriginalPigActorsAndDeathPersistence", DINK_TEST_FLAGS)
bool FDinkCreatureOriginalActorsTest::RunTest(const FString&)
{
	FString Text;
	TSharedPtr<FJsonObject> Manifest;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/creatures.json"))))
	{
		AddWarning(TEXT("skipped: creature manifest not imported"));
		return true;
	}
	if (!TestTrue(TEXT("creature manifest parses"),
				  FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) && Manifest.IsValid()))
		return false;
	IConsoleVariable* Art = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));
	const int32 Old = Art ? Art->GetInt() : 1;
	if (Art)
		Art->SetWithCurrentPriority(1);
	ON_SCOPE_EXIT
	{
		if (Art)
			Art->SetWithCurrentPriority(Old);
	};
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	Story->bRunScreenScripts = false;
	Story->bInstantMode = true;
	UDinkDirector* D = Story->GetDirector();
	TArray<ADinkPlaceholderActor*> Pigs;
	TArray<int32> Handles;
	for (int32 Index : {2, 5, 6, 7, 11})
	{
		ADinkPlaceholderActor* Pig = World->SpawnActor<ADinkPlaceholderActor>();
		Pig->Origin->OriginId = FDinkOriginId(407, Index);
		Pig->Origin->ScriptName = TEXT("die");
		Pig->Brain = 4;
		Pigs.Add(Pig);
		Handles.Add(D->HandleForActor(Pig));
	}
	UDinkCreatureSubsystem* Creatures = World->GetSubsystem<UDinkCreatureSubsystem>();
	Creatures->OnWorldBeginPlay(*World);
	USkeletalMesh* Manny = LoadObject<USkeletalMesh>(
		nullptr, TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
	for (int32 I = 0; I < Pigs.Num(); ++I)
	{
		UDinkCreatureComponent* Creature = Pigs[I]->FindComponentByClass<UDinkCreatureComponent>();
		if (!TestNotNull(TEXT("original pig received animated component"), Creature))
			continue;
		TestTrue(TEXT("pig uses own nonManny skeleton"),
				 Manny && Creature->GetSkeletalMeshAsset()->GetSkeleton() != Manny->GetSkeleton());
		TestTrue(TEXT("source card hidden only after valid replacement"), Pigs[I]->Card->bHiddenInGame);
		TestEqual(TEXT("pig brain4 retained"), D->FindSprite(Handles[I])->GetProp(TEXT("brain")), 4);
		TestEqual(TEXT("original die script retained"), D->FindSprite(Handles[I])->Script, FName(TEXT("die")));
		TestTrue(TEXT("same original actor retained"), D->FindSprite(Handles[I])->Actor.Get() == Pigs[I]);
		TInlineComponentArray<UBoxComponent*> Bodies(Pigs[I]);
		bool bProxy = false;
		for (const UBoxComponent* Body : Bodies)
			if (Body->ComponentHasTag(TEXT("DinkAuthoredInteraction")))
				bProxy |= Body->IsRegistered() && Body->bHiddenInGame &&
						  Body->GetScaledBoxExtent().X > Body->GetScaledBoxExtent().Y;
		TestTrue(TEXT("pig has hidden horizontal body footprint"), bProxy);
	}
	Story->GetGameplay()->HurtThing(Handles[0], 100);
	Story->GetGameplay()->ProcessDamage();
	Story->RunUntilIdle();
	TestTrue(TEXT("pig death hides entire authored actor"), Pigs[0]->IsHidden());
	TestFalse(TEXT("dead pig cannot leave invisible body collision"), Pigs[0]->GetActorEnableCollision());
	TestTrue(TEXT("original die persists placement removal"),
			 GI->GetSubsystem<UDinkWorldStateSubsystem>()->IsPlacementRemoved(FDinkOriginId(407, 2)));
	const TSharedPtr<FJsonObject> Saved = D->SaveState();
	D->FindSprite(Handles[0])->bActive = true;
	Pigs[0]->SetActorHiddenInGame(false);
	Pigs[0]->SetActorEnableCollision(true);
	D->LoadState(Saved);
	TestTrue(TEXT("restoring consumed/dead pig remains hidden"), Pigs[0]->IsHidden());
	TestFalse(TEXT("save restore keeps dead proxy disabled"), Pigs[0]->GetActorEnableCollision());
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureGroundFoodTest,
								 "Dink.Art.CreaturePresentation.VisibleGroundGrainOcclusion", DINK_TEST_FLAGS)
bool FDinkCreatureGroundFoodTest::RunTest(const FString&)
{
	FString Text;
	TSharedPtr<FJsonObject> Manifest;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/creatures.json"))) ||
		!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest)
	{
		AddWarning(TEXT("skipped: creature manifest absent"));
		return true;
	}
	TSharedPtr<FJsonObject> Row;
    for (const auto& Value : Manifest->GetArrayField(TEXT("placements")))
    {
        const auto Candidate = Value->AsObject();
        if (Candidate && Candidate->GetStringField(TEXT("origin")).StartsWith(TEXT("S407_")) && Candidate->HasField(TEXT("food_mesh")))
        { Row = Candidate; break; }
    }
    if (!TestTrue(TEXT("pig feeding placement selected from mixed creature manifest"), Row.IsValid())) return false;
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *Row->GetStringField(TEXT("mesh")));
	UBlendSpace* BS = LoadObject<UBlendSpace>(nullptr, *Row->GetStringField(TEXT("locomotion")));
	UAnimSequence* Feed = LoadObject<UAnimSequence>(nullptr, *Row->GetStringField(TEXT("feed_animation")));
	UStaticMesh* Grain = LoadObject<UStaticMesh>(nullptr, *Row->GetStringField(TEXT("food_mesh")));
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (!TestNotNull(TEXT("real imported grain geometry"), Grain) || !Mesh || !BS || !Feed || !Cube)
		return false;
	FAssetCompilingManager::Get().FinishAllCompilation();
	FCreatureWorld E;
	TestNotNull(TEXT("real physics query scene"), E.World->GetPhysicsScene());
	AActor* Pig = E.Actor();
	UDinkCreatureComponent* Creature = NewObject<UDinkCreatureComponent>(Pig);
	Creature->SetupAttachment(Pig->GetRootComponent());
	Creature->RegisterComponent();
	FDinkCreaturePresentation Settings;
	Settings.NominalRunSpeedCmS = 400;
	TestTrue(TEXT("real pig rig configured"), Creature->Configure(Mesh, BS, Feed, Settings));
	Creature->TickComponent(.1f, LEVELTICK_All, nullptr);
	auto Food = [&](const FVector& Head)
	{
		ADinkScriptSpriteActor* Actor =
			E.World->SpawnActor<ADinkScriptSpriteActor>(FVector(Head.X + 50, Head.Y, 60), FRotator::ZeroRotator);
		Actor->Marker->SetHiddenInGame(true);
		UStaticMeshComponent* Visual = NewObject<UStaticMeshComponent>(Actor, TEXT("ActualKernels"));
		Actor->AddInstanceComponent(Visual);
		Visual->SetupAttachment(Actor->GetRootComponent());
		Visual->SetStaticMesh(Grain);
		Visual->SetMobility(EComponentMobility::Movable);
		Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Visual->ComponentTags.Add(TEXT("DinkAuthoredFood"));
		Visual->RegisterComponent();
		Visual->SetWorldTransform(FTransform(FRotator::ZeroRotator,
											 FVector(Actor->GetActorLocation().X, Actor->GetActorLocation().Y, .6),
											 FVector::OneVector));
		Visual->UpdateBounds();
		return Actor;
	};
	const FVector Head = Creature->GetSocketLocation(TEXT("head"));
	ADinkScriptSpriteActor* First = Food(Head);
	UStaticMeshComponent* Kernels = First->FindComponentByTag<UStaticMeshComponent>(TEXT("DinkAuthoredFood"));
	const FVector Contact = Kernels->Bounds.Origin;
	TestTrue(TEXT("fixture grain is on ground rather than legacy root"),
			 Contact.Z < 3. && FMath::IsNearlyEqual(First->GetActorLocation().Z, 60., .001));
	TestTrue(TEXT("true3D distance exceeds70cm to expose vertical-radius bug"), FVector::Distance(Head, Contact) > 70.);
	TestTrue(TEXT("ground grain within50cm horizontal head reach is reachable"), Creature->CanFeedAt(Contact));
	AStaticMeshActor* Rail = E.World->SpawnActor<AStaticMeshActor>();
	Rail->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
	Rail->GetStaticMeshComponent()->SetStaticMesh(Cube);
	Rail->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
	Rail->SetActorScale3D(FVector(.1, .6, .16));
	Rail->SetActorLocation(FVector((Head.X + Contact.X) * .5, (Head.Y + Contact.Y) * .5, (Head.Z + 60.) * .5));
	FCollisionQueryParams Params(TEXT("FoodHeightRegression"), true, Pig);
	Params.AddIgnoredActor(First);
	FHitResult Hit;
	TestTrue(TEXT("old raised-root ray falsely hits an overhead rail"),
			 E.World->LineTraceSingleByChannel(Hit, Head, First->GetActorLocation(), ECC_Visibility, Params));
	TestFalse(TEXT("actual visible floor-grain ray passes below that rail"),
			  E.World->LineTraceSingleByChannel(Hit, Head, Contact, ECC_Visibility, Params));
	TestTrue(TEXT("feeding uses actual visible kernels instead of raised actor root"), Creature->TryFeed(First));
	TestTrue(TEXT("successful presentation keeps original grain root trajectory"),
			 FMath::IsNearlyEqual(First->GetActorLocation().Z, 60., .001));
	Pig->AddActorWorldOffset(FVector(1, 0, 0));
	Creature->TickComponent(.1f, LEVELTICK_All, nullptr);
	Creature->TickComponent(.1f, LEVELTICK_All, nullptr);
	const FVector NextHead = Creature->GetSocketLocation(TEXT("head"));
	ADinkScriptSpriteActor* Second = Food(NextHead);
	TestTrue(TEXT("negative occlusion case has fresh unconsumed grain"), Second != First && !Creature->IsFeeding());
	const FVector SecondPoint =
		Second->FindComponentByTag<UStaticMeshComponent>(TEXT("DinkAuthoredFood"))->Bounds.Origin;
	TestTrue(TEXT("fresh blocked grain otherwise remains in physical reach"), Creature->CanFeedAt(SecondPoint));
	Rail->SetActorScale3D(FVector(.1, .6, 1.4));
	Rail->SetActorLocation(FVector((NextHead.X + SecondPoint.X) * .5, (NextHead.Y + SecondPoint.Y) * .5, 35));
	TestFalse(TEXT("real floor-level occlusion still rejects fresh food"), Creature->TryFeed(Second));
	Rail->Destroy();
	ADinkScriptSpriteActor* Hidden = Food(NextHead);
	Hidden->FindComponentByTag<UStaticMeshComponent>(TEXT("DinkAuthoredFood"))->SetHiddenInGame(true);
	TestFalse(TEXT("hidden authored kernels cannot fall back to invisible root"), Creature->TryFeed(Hidden));
	return true;
}
