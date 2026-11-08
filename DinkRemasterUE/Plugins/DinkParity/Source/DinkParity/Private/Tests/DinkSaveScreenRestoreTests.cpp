#include "DinkTestHelpers.h"
#include "DinkSaveGame.h"
#include "DinkSaveSubsystem.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "DinkWorldStateSubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Components/SceneComponent.h"
#include "Components/BoxComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkSaveScreenRestoreTest, "Dink.Core.Save.ScreenCacheBeforeNarrativeRestore", DINK_TEST_FLAGS)
bool FDinkSaveScreenRestoreTest::RunTest(const FString&)
{
 UGameInstance* GI = NewObject<UGameInstance>(GEngine); GI->InitializeStandalone();
 UWorld* World = GI->GetWorld();
 UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
 UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
 UDinkWorldStateSubsystem* State = GI->GetSubsystem<UDinkWorldStateSubsystem>();
 UDinkFactSubsystem* Facts = GI->GetSubsystem<UDinkFactSubsystem>();
 UDinkSaveSubsystem* Saves = GI->GetSubsystem<UDinkSaveSubsystem>();
 Story->bRunScreenScripts = false; Story->bNewGamePending = false;
 APlayerController* PC = World->GetFirstPlayerController();
 if (!PC) { PC = World->SpawnActor<APlayerController>(); World->AddController(PC); }
 APawn* Pawn = World->SpawnActor<APawn>();
 USceneComponent* Root = NewObject<USceneComponent>(Pawn); Pawn->SetRootComponent(Root); Root->RegisterComponent(); PC->Possess(Pawn);
 TestTrue(TEXT("fixture controller is world first controller"),World->GetFirstPlayerController()==PC);
 TestTrue(TEXT("fixture controller possesses test pawn"),PC->GetPawn()==Pawn);
 auto AddScreen = [&](int32 Number, double X)
 {
  ADinkScreenVolume* Volume = World->SpawnActor<ADinkScreenVolume>(); Volume->ScreenNumber = Number;
  Volume->Corners.NW = FVector2D(X,0); Volume->Corners.NE = FVector2D(X+6,0);
  Volume->Corners.SW = FVector2D(X,4); Volume->Corners.SE = FVector2D(X+6,4);
  // The imported volumes have both precise corners and a broad-phase world box.
  FBox Box(ForceInit); Box += Volume->MapPixelToWorld(0,0); Box += Volume->MapPixelToWorld(600,400);
  Volume->Bounds->SetMobility(EComponentMobility::Movable);
  Volume->SetActorLocation(Box.GetCenter()); Volume->Bounds->SetBoxExtent(Box.GetExtent()+FVector(0,0,1000));
  Volume->Bounds->UpdateBounds();
  Greybox->RegisterScreen(Volume); return Volume;
 };
 ADinkScreenVolume* House = AddScreen(1,0);
 ADinkScreenVolume* SavedScreen = AddScreen(625,10);
 Pawn->SetActorLocation(SavedScreen->MapPixelToWorld(300,200));
 TestTrue(TEXT("fixture saved room is discoverable"),Greybox->FindScreenAt(Pawn->GetActorLocation())==SavedScreen);
 Greybox->RefreshCurrentScreen(); Story->OnScreenEntered(625);
 Story->GetDirector()->GetDink().Screen = 625;
 Story->GetDirector()->SyncSpriteFromActor(Story->GetDirector()->GetDink());
 Facts->SetFact(TEXT("story"),7);
 State->SetGameTimeMs(50000); State->NotifyScreenExited(1);
 State->SetGameTimeMs(60000); State->NotifyScreenExited(625);
 State->SetGameTimeMs(123456);
 UDinkSaveGame* Saved = Saves->CaptureSnapshot(Pawn,625);
 Pawn->SetActorLocation(House->MapPixelToWorld(300,200)); Greybox->RefreshCurrentScreen(); Story->OnScreenEntered(1);
 Facts->SetFact(TEXT("story"),1); State->AdvanceGameTime(1000);
 bool bObservedCorrectScreen = false;
 const FDelegateHandle Observer = Saves->OnSnapshotApplied.AddLambda([&](const UDinkSaveGame*)
 { bObservedCorrectScreen = Greybox->GetCurrentScreen() == SavedScreen; });
 TestTrue(TEXT("snapshot applies"), Saves->ApplySnapshot(Saved,Pawn));
 TestTrue(TEXT("snapshot subscribers already see saved physical screen"), bObservedCorrectScreen);
 TestTrue(TEXT("cached volume restores synchronously"), Greybox->GetCurrentScreen() == SavedScreen);
 TestEqual(TEXT("saved map fact exact immediately"), Facts->GetFact(TEXT("player_map")),625);
 TestEqual(TEXT("story fact restored"), Facts->GetFact(TEXT("story")),7);
 TestEqual(TEXT("clock exact immediately"),State->GetGameTimeMs(),int64(123456));
 TestEqual(TEXT("house exit exact immediately"),State->GetScreenExitTimeMs(1),int64(50000));
 TestEqual(TEXT("saved-screen exit exact immediately"),State->GetScreenExitTimeMs(625),int64(60000));
 Story->Tick(.016f);
 TestEqual(TEXT("first tick keeps saved map"),Facts->GetFact(TEXT("player_map")),625);
 TestTrue(TEXT("clock advances normally on first tick"),State->GetGameTimeMs()>123456 && State->GetGameTimeMs()<=123473);
 TestEqual(TEXT("first tick cannot invent a house exit"),State->GetScreenExitTimeMs(1),int64(50000));
 TestEqual(TEXT("first tick cannot invent a saved-screen exit"),State->GetScreenExitTimeMs(625),int64(60000));
 Saves->OnSnapshotApplied.Remove(Observer);
 Greybox->UnregisterScreen(House); Greybox->UnregisterScreen(SavedScreen);
 GI->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false);
 return true;
}
