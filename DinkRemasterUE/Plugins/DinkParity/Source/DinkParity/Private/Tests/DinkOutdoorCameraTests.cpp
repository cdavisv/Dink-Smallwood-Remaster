#include "DinkTestHelpers.h"
#include "DinkInteriorCameraComponent.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Editor.h"
#include "Engine/StaticMesh.h"
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
namespace
{
class FOutdoorCameraPIE : public IAutomationLatentCommand
{
public:
 explicit FOutdoorCameraPIE(FAutomationTestBase* T):Test(T){}
 bool Update() override
 {
  if (!Began) Began=FPlatformTime::Seconds();
  if (FPlatformTime::Seconds()-Began>150) { Test->AddError(FString::Printf(TEXT("outdoor camera regression timed out phase%d"),Phase)); return true; }
  UWorld* W=GEditor ? GEditor->PlayWorld.Get() : nullptr;
  APlayerController* PC=W ? W->GetFirstPlayerController() : nullptr;
  auto* Hero=PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
  auto* Story=W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
  if (Phase==7)
  {
   if (FPlatformTime::Seconds()-At<.7) return false;
   Test->TestEqual(TEXT("unpossess preserves external named collision profile"),Cottage->GetCollisionProfileName(),FName(TEXT("OverlapAllDynamic")));
   Test->TestTrue(TEXT("unpossess preserves every externally owned collision response"),Cottage->GetCollisionResponseToChannels()==ForeignResponses);
   Test->TestEqual(TEXT("unpossess preserves foreign material slot"),Cottage->GetMaterial(0),Materials[1].Get());
   for(int32 I=1;I<Materials.Num();++I)Test->TestEqual(TEXT("unpossess releases all camera-owned material slots"),Cottage->GetMaterial(I),Materials[I].Get());
   // Restore only changes deliberately made by this ownership fixture.
   Cottage->OverrideMaterials=Overrides;Cottage->MarkRenderStateDirty();Cottage->SetCollisionProfileName(Profile);
   CheckRestored();PC->Possess(SavedHero);Phase=8;At=FPlatformTime::Seconds();return false;
  }
  if (!Hero || !Story || Story->bNewGamePending) return false;
  auto* Grey=W->GetSubsystem<UDinkGreyboxSubsystem>();
  auto* Camera=Hero->FindComponentByClass<UDinkInteriorCameraComponent>();
  if (Phase==0)
  {
   Story->SkipDialogue(); if (Story->GetActiveMenu() || Story->GetDirector()->GetDink().bFrozen || PC->IsMoveInputIgnored()) return false;
   if (!Test->TestNotNull(TEXT("actual character camera policy"),Camera)) return true;
   Camera->bEnableWallCutaway=true; // explicit historical comparison, before leaving the room
   auto* Local=PC->GetLocalPlayer(); auto* Viewport=Local && Local->ViewportClient ? Local->ViewportClient->Viewport : nullptr;
   if (!Test->TestNotNull(TEXT("real PIE local viewport"),Viewport)) return true;
   if (Viewport->GetSizeXY()==FIntPoint::ZeroValue) Viewport->SetInitialSize(FIntPoint(1280,720));
   Home=Grey->FindScreen(1); Yard=Grey->FindScreen(439);
   if (!Test->TestNotNull(TEXT("house1 exists"),Home) || !Test->TestNotNull(TEXT("yard439 exists"),Yard)) return true;
   for (TActorIterator<AActor> It(W); It; ++It)
   {
    if (!It->ActorHasTag(TEXT("DinkArtScreen_439"))) continue;
    TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
    for (auto* Mesh:Meshes) if (Mesh->GetStaticMesh() && Mesh->GetStaticMesh()->GetName()==TEXT("SM_Cottage_Stonebrook_01")) Cottage=Mesh;
   }
   if (!Test->TestNotNull(TEXT("actual original exterior cottage exists"),Cottage)) return true;
   Responses=Cottage->GetCollisionResponseToChannels(); Profile=Cottage->GetCollisionProfileName(); Enabled=Cottage->GetCollisionEnabled(); ObjectType=Cottage->GetCollisionObjectType();
   Overrides=Cottage->OverrideMaterials; Transform=Cottage->GetComponentTransform(); Extent=Cottage->Bounds.BoxExtent; Asset=Cottage->GetStaticMesh();
   for(int32 I=0;I<Cottage->GetNumMaterials();++I) Materials.Add(Cottage->GetMaterial(I));
   Test->TestEqual(TEXT("actual cottage five material slots"),Materials.Num(),5);
   CapsuleResponses=Hero->GetCapsuleComponent()->GetCollisionResponseToChannels(); CapsuleEnabled=Hero->GetCapsuleComponent()->GetCollisionEnabled(); Input=Hero->InputComponent;
   PC->SetControlRotation(ExpectedControl);
   Hero->GetCharacterMovement()->StopMovementImmediately(); Hero->SetActorLocation(Home->MapPixelToWorld(303.5,370)+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics); Grey->RefreshCurrentScreen();
   Phase=1;At=FPlatformTime::Seconds();return false;
  }
  if (Phase==1)
  {
   if (Grey->GetCurrentScreen()==Yard)
   {
    Hero->GetCharacterMovement()->StopMovementImmediately(); ExitPosition=Hero->GetActorLocation(); Phase=2;At=FPlatformTime::Seconds();return false;
   }
   // Fixture establishes an interior approach only; normal movement activates the real door warp.
   Hero->AddMovementInput(FVector(0,1,0)); return false;
  }
  if (FPlatformTime::Seconds()-At<.7) return false;
  if (Phase==2)
  {
   Test->TestEqual(TEXT("real movement triggered original outdoor439 exit"),Grey->GetCurrentScreen(),Yard);
   Test->TestTrue(TEXT("stationary exit camera readback does not walk away to evade jamb"),Hero->GetActorLocation().Equals(ExitPosition,2));
   Test->TestFalse(TEXT("exit retains outdoor camera mode"),Camera->bInteriorMode);
   Test->TestEqual(TEXT("only explicitly qualified exterior cottage managed"),Camera->ManagedOccluderCount,1);
   const double Distance=FVector::Dist(Hero->GetActorLocation(),Hero->FollowCamera->GetComponentLocation());
   Test->AddInfo(FString::Printf(TEXT("actual outdoor exit pawn%s eye%s distance%.3f requested%.3f"),*Hero->GetActorLocation().ToCompactString(),*Hero->FollowCamera->GetComponentLocation().ToCompactString(),Distance,Hero->CameraBoom->TargetArmLength));
   Test->TestTrue(TEXT("stationary immediate exterior exit has readable full400cm camera"),FMath::Abs(Distance-400.)<1.);
   Test->TestTrue(TEXT("qualified cottage actually fades at obstructed exit"),Camera->FadingOccluderCount>0);
   for(int32 I=0;I<Materials.Num();++I)
   {
    auto* MID=Cast<UMaterialInstanceDynamic>(Cottage->GetMaterial(I)); float Opacity=1;
    Test->TestTrue(TEXT("every cottage slot uses owned masked fade material"),MID && MID->GetOuter()==Camera && MID->GetBlendMode()==BLEND_Masked);
    if (MID) MID->GetScalarParameterValue(FMaterialParameterInfo(TEXT("DinkCameraOpacity")),Opacity);
    Test->TestTrue(TEXT("all cottage slots visibly fade, preserving opaque shadows"),Opacity<.1f);
   }
   CheckPhysical(Hero,PC,true); CheckOutdoorPreset(Hero,Camera);
   Blocker=W->SpawnActor<AActor>(); Blocker->Tags.Add(TEXT("DinkArtScreen_439"));
   auto* M=NewObject<UStaticMeshComponent>(Blocker); Blocker->SetRootComponent(M);Blocker->AddInstanceComponent(M);
   M->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));M->SetMaterial(0,Materials[2]);M->SetWorldScale3D(FVector(.4));M->SetCollisionProfileName(TEXT("BlockAll"));M->RegisterComponent();
   Blocker->SetActorLocation(Hero->GetActorLocation()-PC->GetControlRotation().Vector()*200.); Ordinary=M;
   Phase=3;At=FPlatformTime::Seconds();return false;
  }
  if (Phase==3)
  {
   Test->TestFalse(TEXT("ordinary outdoor blocker has no opt-in occluder tag"),Blocker->ActorHasTag(TEXT("DinkCameraOccluder")));
   Test->TestEqual(TEXT("ordinary supported-material blocker keeps original material"),Ordinary->GetMaterial(0),Materials[2].Get());
   Test->TestEqual(TEXT("ordinary outdoor blocker still blocksCamera"),Ordinary->GetCollisionResponseToChannel(ECC_Camera),ECR_Block);
   Test->TestTrue(TEXT("ordinary outdoor physical surface retracts camera"),FVector::Dist(Hero->GetActorLocation(),Hero->FollowCamera->GetComponentLocation())<220.);
   Blocker->Destroy(); Blocker=nullptr;
   Hero->SetActorLocation(Home->MapPixelToWorld(303.5,370)+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics);Grey->RefreshCurrentScreen();
   Phase=4;At=FPlatformTime::Seconds();return false;
  }
  if (Phase==4)
  {
   CheckRestored();
   Hero->SetActorLocation(ExitPosition,false,nullptr,ETeleportType::TeleportPhysics);Grey->RefreshCurrentScreen();Phase=5;At=FPlatformTime::Seconds();return false;
  }
  if (Phase==5)
  {
   Test->TestEqual(TEXT("exterior reacquires only qualified cottage"),Camera->ManagedOccluderCount,1);
   Cottage->SetMaterial(0,Materials[1]);Cottage->SetCollisionProfileName(TEXT("OverlapAllDynamic"));ForeignResponses=Cottage->GetCollisionResponseToChannels();
   SavedHero=Hero;PC->UnPossess();Phase=7;At=FPlatformTime::Seconds();return false;
  }
  if (Phase==8)
  {
   Test->TestEqual(TEXT("repossess reacquires exterior cottage after ownership release"),Camera->ManagedOccluderCount,1);
   // Possession is this fixture's deliberate input lifecycle; capture its resulting input component.
   Input=Hero->InputComponent;ExpectedControl=PC->GetControlRotation();
   Test->AddInfo(FString::Printf(TEXT("Post-Possess fixture baseline: control%s actor%s input%s"),*ExpectedControl.ToString(),*Hero->GetActorRotation().ToString(),*GetNameSafe(Input)));
   Test->TestTrue(TEXT("deliberate Possess fixture adopts pawn rotation per PlayerController lifecycle"),ExpectedControl.Equals(Hero->GetActorRotation(),.001));
   Camera->DestroyComponent();Phase=6;At=FPlatformTime::Seconds();return false;
  }
  if (Phase==6)
  {
   CheckRestored();Test->TestTrue(TEXT("destroy restores outdoor400cm arm"),FMath::IsNearlyEqual(Hero->CameraBoom->TargetArmLength,400.f));
   Test->TestTrue(TEXT("destroy restores outdoorFOV90"),FMath::IsNearlyEqual(Hero->FollowCamera->FieldOfView,90.f));CheckPhysical(Hero,PC,false);return true;
  }
  return false;
 }
private:
 void CheckOutdoorPreset(ADinkGreyboxCharacter* H,UDinkInteriorCameraComponent* C)
 {
  Test->TestTrue(TEXT("outdoor arm remains400"),FMath::IsNearlyEqual(H->CameraBoom->TargetArmLength,400.f));
  Test->TestTrue(TEXT("outdoor FOV remains90"),FMath::IsNearlyEqual(H->FollowCamera->FieldOfView,90.f));
  Test->TestTrue(TEXT("outdoor target/socket offsets stayoriginal"),H->CameraBoom->TargetOffset.IsZero() && H->CameraBoom->SocketOffset.IsZero());
  Test->TestFalse(TEXT("outdoor never enables interior floor framing"),C->bFloorFramingAvailable);Test->TestTrue(TEXT("outdoor floor shift stayszero"),C->FloorFramingShift.IsZero());
 }
 void CheckPhysical(ADinkGreyboxCharacter* H,APlayerController* PC,bool Managed)
 {
  Test->TestEqual(TEXT("original cottage geometry asset retained"),Cottage->GetStaticMesh().Get(),Asset);
  Test->TestTrue(TEXT("original cottage transform/extents retained"),Cottage->GetComponentTransform().Equals(Transform,.001) && Cottage->Bounds.BoxExtent.Equals(Extent,.001));
  Test->TestEqual(TEXT("original collisionenabled preserved"),Cottage->GetCollisionEnabled(),Enabled);Test->TestEqual(TEXT("original objecttype preserved"),Cottage->GetCollisionObjectType(),ObjectType);
  auto Expected=Responses;if(Managed)Expected.SetResponse(ECC_Camera,ECR_Ignore);
  Test->TestTrue(TEXT("qualified cottage changes only Camera response"),Cottage->GetCollisionResponseToChannels()==Expected);
  Test->TestTrue(TEXT("original pawn collision remainsunchanged"),H->GetCapsuleComponent()->GetCollisionResponseToChannels()==CapsuleResponses && H->GetCapsuleComponent()->GetCollisionEnabled()==CapsuleEnabled);
  Test->AddInfo(FString::Printf(TEXT("Input/control phase%d actual%s expected%s inputmatches%d"),Phase,*PC->GetControlRotation().ToString(),*ExpectedControl.ToString(),H->InputComponent==Input));
  Test->TestTrue(TEXT("inputcomponent/controlrotation remainoriginal"),H->InputComponent==Input && PC->GetControlRotation().Equals(ExpectedControl,.001));
  Test->TestFalse(TEXT("movement/look stayenabled"),PC->IsMoveInputIgnored() || PC->IsLookInputIgnored());
 }
 void CheckRestored()
 {
  Test->TestEqual(TEXT("leaving/destroy restores exact cottage profile"),Cottage->GetCollisionProfileName(),Profile);
  Test->TestTrue(TEXT("leaving/destroy restores every cottage response"),Cottage->GetCollisionResponseToChannels()==Responses);
  Test->TestTrue(TEXT("leaving/destroy restores exact override array"),Cottage->OverrideMaterials==Overrides);
  for(int32 I=0;I<Materials.Num();++I)Test->TestEqual(TEXT("leaving/destroy restores original effective material"),Cottage->GetMaterial(I),Materials[I].Get());
 }
 FAutomationTestBase* Test;int32 Phase=0;double Began=0,At=0;ADinkScreenVolume *Home=nullptr,*Yard=nullptr;
 UStaticMeshComponent *Cottage=nullptr,*Ordinary=nullptr;AActor* Blocker=nullptr;UStaticMesh* Asset=nullptr;UInputComponent* Input=nullptr;
 FRotator ExpectedControl=FRotator(-18,90,0);ADinkGreyboxCharacter* SavedHero=nullptr;FVector ExitPosition,Extent;FTransform Transform;FCollisionResponseContainer Responses,CapsuleResponses,ForeignResponses;ECollisionEnabled::Type Enabled,CapsuleEnabled;ECollisionChannel ObjectType;FName Profile;
 TArray<TObjectPtr<UMaterialInterface>> Materials,Overrides;
};
class FRestoreOutdoorArt : public IAutomationLatentCommand
{public:explicit FRestoreOutdoorArt(int32 V):Value(V){}bool Update()override{IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"))->Set(Value,ECVF_SetByCode);return true;}private:int32 Value;};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkOutdoorCameraTest,"Dink.Art.OutdoorCamera.ReadableExitAndOwnership",DINK_TEST_FLAGS)
bool FDinkOutdoorCameraTest::RunTest(const FString&)
{
 const auto File=FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"),FPackageName::GetMapPackageExtension());
 if (!TestNotNull(TEXT("actual gameplay map loads"),UEditorLoadingAndSavingUtils::LoadMap(File)))return false;
 FAssetCompilingManager::Get().FinishAllCompilation();auto* Art=IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));const int32 Prior=Art->GetInt();Art->Set(1,ECVF_SetByCode);
 AddCommand(new FStartPIECommand(false));AddCommand(new FOutdoorCameraPIE(this));AddCommand(new FEndPlayMapCommand());AddCommand(new FRestoreOutdoorArt(Prior));return true;
}
