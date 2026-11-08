#include "DinkTestHelpers.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkWorldStateSubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/BoxComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ScopeExit.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkLegacyCardVisibilityTest, "Dink.Core.Greybox.LegacyCardsCurrentScreen",
								 DINK_TEST_FLAGS)
bool FDinkLegacyCardVisibilityTest::RunTest(const FString&)
{
	IConsoleVariable* Rule = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.LegacyCardsCurrentScreen"));
	if (!TestNotNull(TEXT("presentation rule registered"), Rule))
		return false;
	const int32 Previous = Rule->GetInt();
	Rule->SetWithCurrentPriority(1);
	ON_SCOPE_EXIT
	{
		Rule->SetWithCurrentPriority(Previous);
	};
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
	APlayerController* PC = World->GetFirstPlayerController();
	if (!PC)
	{
		PC = World->SpawnActor<APlayerController>();
		World->AddController(PC);
	}
	APawn* Pawn = World->SpawnActor<APawn>();
	USceneComponent* Root = NewObject<USceneComponent>(Pawn);
	Pawn->SetRootComponent(Root);
	Root->RegisterComponent();
	PC->Possess(Pawn);
	auto Room = [&](int32 Number, double X)
	{
		ADinkScreenVolume* V = World->SpawnActor<ADinkScreenVolume>();
		V->ScreenNumber = Number;
		V->Corners.NW = FVector2D(X, 0);
		V->Corners.NE = FVector2D(X + 6, 0);
		V->Corners.SW = FVector2D(X, 4);
		V->Corners.SE = FVector2D(X + 6, 4);
		FBox Box(ForceInit);
		Box += V->MapPixelToWorld(0, 0);
		Box += V->MapPixelToWorld(600, 400);
		V->Bounds->SetMobility(EComponentMobility::Movable);
		V->SetActorLocation(Box.GetCenter());
		V->Bounds->SetBoxExtent(Box.GetExtent() + FVector(0, 0, 1000));
		V->Bounds->UpdateBounds();
		Greybox->RegisterScreen(V);
		return V;
	};
	ADinkScreenVolume* One = Room(1, 0);
	ADinkScreenVolume* Two = Room(2, 10);
	auto Card = [&](int32 Screen)
	{
		ADinkPlaceholderActor* A = World->SpawnActor<ADinkPlaceholderActor>();
		A->ScreenNumber = Screen;
		return A;
	};
	ADinkPlaceholderActor* Current = Card(1);
	ADinkPlaceholderActor* Neighbor = Card(2);
	ADinkPlaceholderActor* Authored = Card(2);
	Authored->Tags.Add(TEXT("DinkAuthoredArt"));
	ADinkPlaceholderActor* Upgrade = Card(2);
	ADinkPlaceholderActor* HiddenCard = Card(1);
	HiddenCard->Card->SetHiddenInGame(true);
	ADinkPlaceholderActor* InitiallyInvisible = Card(1);
	InitiallyInvisible->Card->SetVisibility(false);
	ADinkPlaceholderActor* Vision = Card(1);
	Vision->Vision = 2;
	Vision->ApplyScreenVision(0);
	ADinkPlaceholderActor* NoDraw = Card(2);
	NoDraw->SetActorHiddenInGame(true);
	ADinkGreyboxScreen* Background = World->SpawnActor<ADinkGreyboxScreen>();
	Background->ScreenNumber = 2;
	auto Instances = [&](const TCHAR* Name, bool bOriginal)
	{
		UInstancedStaticMeshComponent* C = NewObject<UInstancedStaticMeshComponent>(Background, FName(Name));
		C->SetupAttachment(Background->GetRootComponent());
		Background->AddInstanceComponent(C);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->RegisterComponent();
		if (bOriginal)
		{
			FDinkInstanceOrigin Origin;
			Origin.OriginId = FDinkOriginId(2, 1);
			Origin.ComponentName = C->GetFName();
			Background->InstanceOrigins->Origins.Add(Origin);
		}
		return C;
	};
	UInstancedStaticMeshComponent* Decor = Instances(TEXT("Decor_Source"), true);
	UInstancedStaticMeshComponent* AuthoredInstances = Instances(TEXT("AuthoredGrass"), false);
	UInstancedStaticMeshComponent* HiddenDecor = Instances(TEXT("Decor_HiddenByArt"), true);
	HiddenDecor->SetHiddenInGame(true);
	UDinkWorldStateSubsystem* State = GI->GetSubsystem<UDinkWorldStateSubsystem>();
	State->SetGameTimeMs(1234);
	State->NotifyScreenExited(99);
	Pawn->SetActorLocation(One->MapPixelToWorld(300, 200));
	Greybox->RefreshCurrentScreen();
	TestTrue(TEXT("fixture current screen follows registered player"),Greybox->GetCurrentScreen()==One);
	TestTrue(TEXT("current legacy card remains visible"), Current->Card->GetVisibleFlag());
	TestFalse(TEXT("neighbor legacy card culled from horizon"), Neighbor->Card->GetVisibleFlag());
	TestFalse(TEXT("neighbor original background cards culled"), Decor->GetVisibleFlag());
	TestTrue(TEXT("authored neighboring geometry remains visible"), Authored->Card->GetVisibleFlag());
	TestTrue(TEXT("authored instances are never hidden with source backgrounds"), AuthoredInstances->GetVisibleFlag());
	TestFalse(TEXT("culling preserves original prehidden visibility flag"), InitiallyInvisible->Card->GetVisibleFlag());
	TestTrue(TEXT("authored hidden-card flag preserved"), HiddenCard->Card->bHiddenInGame);
	TestTrue(TEXT("background hidden-by-art flag preserved"), HiddenDecor->bHiddenInGame);
	TestTrue(TEXT("vision actor remains hidden"), Vision->IsHidden());
	TestFalse(TEXT("vision collision state untouched"), Vision->GetActorEnableCollision());
	TestTrue(TEXT("neighbor logical actor stays active and collidable"),
			 Neighbor->GetActorEnableCollision() && !Neighbor->IsHidden());
	TestTrue(TEXT("original ground stays visible"), Background->Visual->GetVisibleFlag());
	Vision->ApplyScreenVision(2);
	Greybox->RefreshCurrentScreen();
	TestTrue(TEXT("current screen vision becomes visible without culling override"),
			 !Vision->IsHidden() && Vision->GetActorEnableCollision() && Vision->Card->GetVisibleFlag());
	Upgrade->Tags.Add(TEXT("DinkAuthoredArt"));
	Greybox->RefreshCurrentScreen();
	TestTrue(TEXT("newly authored card restores managed baseline"), Upgrade->Card->GetVisibleFlag());
	Pawn->SetActorLocation(Two->MapPixelToWorld(300, 200));
	Greybox->RefreshCurrentScreen();
	TestFalse(TEXT("old screen card culled after actual screen transition"), Current->Card->GetVisibleFlag());
	TestTrue(TEXT("new current-screen source cards appear"), Neighbor->Card->GetVisibleFlag());
	TestTrue(TEXT("new current-screen original background appears"), Decor->GetVisibleFlag());
	TestTrue(TEXT("nodraw actor remains hidden even when its card is current"), NoDraw->IsHidden());
	TestTrue(TEXT("out-of-screen vision actor collision stays unchanged"), Vision->GetActorEnableCollision());
	TestEqual(TEXT("presentation cannot advance respawn clock"), State->GetGameTimeMs(), int64(1234));
	TestEqual(TEXT("presentation cannot invent exit timestamps"), State->GetScreenExitTimeMs(99), int64(1234));
	Rule->SetWithCurrentPriority(0);
	Greybox->RefreshCurrentScreen();
	TestTrue(TEXT("disabled rule restores original neighboring card visibility"), Current->Card->GetVisibleFlag());
	TestTrue(TEXT("disabled rule keeps original current card visibility"), Neighbor->Card->GetVisibleFlag());
	TestFalse(TEXT("disabled rule restores original invisible component exactly"),
			  InitiallyInvisible->Card->GetVisibleFlag());
	TestTrue(TEXT("disabled rule never clears hidden-by-art flags"),
			 HiddenCard->Card->bHiddenInGame && HiddenDecor->bHiddenInGame);
	TestTrue(TEXT("disabled rule never clears nodraw"), NoDraw->IsHidden());
	Greybox->UnregisterScreen(One);
	Greybox->UnregisterScreen(Two);
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}
