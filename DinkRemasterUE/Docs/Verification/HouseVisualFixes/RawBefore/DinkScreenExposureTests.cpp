#include "DinkTestHelpers.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PostProcessComponent.h"
#include "Editor.h"
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
#include "UnrealClient.h"

namespace
{
class FScreenExposurePIE : public IAutomationLatentCommand
{
public:
    explicit FScreenExposurePIE(FAutomationTestBase* InTest) : Test(InTest) {}
    bool Update() override
    {
        if (!Began) Began=FPlatformTime::Seconds();
        if (FPlatformTime::Seconds()-Began>80) { Test->AddError(FString::Printf(TEXT("screen exposure timeout phase%d"),Phase)); return true; }
        UWorld* World=GEditor ? GEditor->PlayWorld.Get() : nullptr;
        APlayerController* PC=World ? World->GetFirstPlayerController() : nullptr;
        if (!World || !PC) return false;
        if (Phase==4)
        {
            if (FPlatformTime::Seconds()-At<.35) return false;
            CheckActive(false,TEXT("unpossessed owner"));
            if (!Test->TestTrue(TEXT("existing real pawn remains valid"),SavedHero.IsValid())) return true;
            PC->Possess(SavedHero.Get()); Input=nullptr; Phase=5; At=FPlatformTime::Seconds(); return false;
        }
        ADinkGreyboxCharacter* Hero=Cast<ADinkGreyboxCharacter>(PC->GetPawn());
        UDinkStorySubsystem* Story=World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (!Hero || !Story || Story->bNewGamePending) return false;
        UDinkGreyboxSubsystem* Grey=World->GetSubsystem<UDinkGreyboxSubsystem>();
        if (Phase==0)
        {
            Story->SkipDialogue();
            if (Story->GetActiveMenu() || Story->GetDirector()->GetDink().bFrozen || PC->IsMoveInputIgnored()) return false;
            if (ULocalPlayer* Local=PC->GetLocalPlayer())
                if (FViewport* View=Local->ViewportClient ? Local->ViewportClient->Viewport : nullptr)
                    if (View->GetSizeXY()==FIntPoint::ZeroValue) View->SetInitialSize(FIntPoint(1280,720));
            Home=Grey->FindScreen(1); Yard=Grey->FindScreen(439);
            if (!Test->TestNotNull(TEXT("real house"),Home) || !Test->TestNotNull(TEXT("real yard"),Yard)) return true;
            for (TObjectIterator<UPostProcessComponent> It;It;++It)
                if (It->GetWorld()==World && It->GetFName()==TEXT("ArtExposure")) Exposure=*It;
            if (!Test->TestNotNull(TEXT("actual authored exposure component"),Exposure)) return true;
            Bounds=Cast<UBoxComponent>(Exposure->GetAttachParent());
            if (!Test->TestNotNull(TEXT("original query bounds retained"),Bounds)) return true;
            BoundsTransform=Bounds->GetComponentTransform(); BoundsExtent=Bounds->GetUnscaledBoxExtent();
            SavedHero=Hero; Input=Hero->InputComponent; CapsuleResponses=Hero->GetCapsuleComponent()->GetCollisionResponseToChannels();
            CapsuleEnabled=Hero->GetCapsuleComponent()->GetCollisionEnabled();
            PC->SetControlRotation(FRotator(-18,270,0)); Move(Hero,Grey,Home,303.5,382);
            Phase=1; At=FPlatformTime::Seconds(); return false;
        }
        if (FPlatformTime::Seconds()-At<.45) return false;
        if (Phase==1)
        {
            const FVector Eye=PC->PlayerCameraManager->GetCameraLocation();
            const double Distance=FMath::Sqrt(Bounds->Bounds.GetBox().ComputeSquaredDistanceToPoint(Eye));
            Test->TestTrue(TEXT("actual doorway camera is beyond old volume blend radius"),Distance>Exposure->BlendRadius);
            Test->TestEqual(TEXT("pawn remains physically in house"),Grey->FindScreenAt(Hero->GetActorLocation()),Home);
            Test->AddInfo(FString::Printf(TEXT("doorway eye%s old-bounds distance%.3fcm blend%.3f"),*Eye.ToString(),Distance,Exposure->BlendRadius));
            CheckActive(true,TEXT("doorway camera outside bounds but pawn inside owner")); CheckPreserved(Hero);
            Hero->GetCharacterMovement()->DisableMovement();
            Outside=FVector(Bounds->GetComponentLocation().X+500,Home->MapPixelToWorld(400,400).Y+10,98);
            Test->TestTrue(TEXT("outside-owner fixture remains within former authored bounds"),Bounds->Bounds.GetBox().IsInside(Outside));
            Test->TestNull(TEXT("outside-owner fixture has no physical house membership"),Grey->FindScreenAt(Outside));
            Hero->SetActorLocation(Outside,false,nullptr,ETeleportType::TeleportPhysics);
            // Do not refresh the cached screen: production must also check the physical pawn.
            Phase=2; At=FPlatformTime::Seconds(); return false;
        }
        if (Phase==2)
        {
            Test->TestTrue(TEXT("outside physical fixture did not move"),Hero->GetActorLocation().Equals(Outside,.1));
            CheckActive(false,TEXT("outside pawn inside former box")); CheckPreserved(Hero);
            Hero->GetCharacterMovement()->SetMovementMode(MOVE_Walking); Move(Hero,Grey,Home,303.5,382);
            Phase=3; At=FPlatformTime::Seconds(); return false;
        }
        if (Phase==3)
        {
            CheckActive(true,TEXT("reentry")); CheckPreserved(Hero);
            PC->UnPossess(); Phase=4; At=FPlatformTime::Seconds(); return false;
        }
        if (Phase==5)
        {
            CheckActive(true,TEXT("repossessed same-screen pawn")); CheckPreserved(Hero);
            UClass* ControllerClass=PC->GetClass(); ULocalPlayer* Player=PC->GetLocalPlayer();
            PC->UnPossess(); PC->Destroy();
            APlayerController* Replacement=World->SpawnActor<APlayerController>(ControllerClass);
            if (!Test->TestNotNull(TEXT("replacement controller"),Replacement)) return true;
            if (Player) Replacement->SetPlayer(Player);
            Replacement->Possess(Hero);
            Test->TestEqual(TEXT("controller replacement keeps cached owner screen"),Grey->GetCurrentScreen(),Home);
            Phase=6; At=FPlatformTime::Seconds(); return false;
        }
        if (Phase==6)
        {
            CheckActive(true,TEXT("replacement controller without screen event"));
            Move(Hero,Grey,Yard,300,350); Phase=7; At=FPlatformTime::Seconds(); return false;
        }
        if (Phase==7)
        {
            CheckActive(false,TEXT("real outdoor screen"));
            const int32 Before=CountProviders(*World); Exposure->DestroyComponent();
            Test->TestFalse(TEXT("destroy unregisters postprocess component"),Exposure->IsRegistered());
            Test->TestEqual(TEXT("destroy removes exactly one world postprocess provider"),CountProviders(*World),Before-1);
            Move(Hero,Grey,Home,303.5,382); PC->UnPossess(); PC->Possess(Hero);
            Phase=8; At=FPlatformTime::Seconds(); return false;
        }
        if (Phase==8)
        {
            Test->TestTrue(TEXT("world remains healthy beyond timer period after destruction"),IsValid(Hero));
            Test->TestFalse(TEXT("destroyed exposure never re-registers on possession/screen callbacks"),Exposure->IsRegistered());
            return true;
        }
        return false;
    }
private:
    static int32 CountProviders(UWorld& World)
    { int32 Count=0; for (const auto& Provider : World.GetPostProcessVolumeIterator()) { (void)Provider; ++Count; } return Count; }
    void Move(ADinkGreyboxCharacter* H,UDinkGreyboxSubsystem* G,ADinkScreenVolume* Screen,double X,double Y)
    { H->GetCharacterMovement()->StopMovementImmediately(); H->SetActorLocation(Screen->MapPixelToWorld(X,Y)+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics); G->RefreshCurrentScreen(); }
    void CheckActive(bool Active,const TCHAR* Context)
    {
        Test->TestEqual(FString::Printf(TEXT("%s: exposure enabled"),Context),Exposure->bEnabled,Active);
        Test->TestEqual(FString::Printf(TEXT("%s: view-independent owner exposure"),Context),Exposure->bUnbound,Active);
        Test->TestEqual(TEXT("accepted bias unchanged"),Exposure->Settings.AutoExposureBias,-2.f);
        Test->TestEqual(TEXT("accepted bloom unchanged"),Exposure->Settings.BloomIntensity,.15f);
        Test->TestEqual(TEXT("accepted priority unchanged"),Exposure->Priority,10.f);
    }
    void CheckPreserved(ADinkGreyboxCharacter* H)
    {
        Test->TestTrue(TEXT("original exposure bounds transform unchanged"),Bounds->GetComponentTransform().Equals(BoundsTransform));
        Test->TestTrue(TEXT("original exposure bounds extent unchanged"),Bounds->GetUnscaledBoxExtent().Equals(BoundsExtent));
        Test->TestEqual(TEXT("query-only bounds remain nonblocking"),Bounds->GetCollisionEnabled(),ECollisionEnabled::QueryOnly);
        Test->TestTrue(TEXT("bounds ignore every collision channel"),Bounds->GetCollisionResponseToChannels()==FCollisionResponseContainer(ECR_Ignore));
        Test->TestEqual(TEXT("capsule collision retained"),H->GetCapsuleComponent()->GetCollisionEnabled(),CapsuleEnabled);
        Test->TestTrue(TEXT("capsule responses retained"),H->GetCapsuleComponent()->GetCollisionResponseToChannels()==CapsuleResponses);
        if (Input) Test->TestEqual(TEXT("actual input component retained"),H->InputComponent.Get(),Input);
        else Input=H->InputComponent; // Possession itself may replace the input component.
    }
    FAutomationTestBase* Test; int32 Phase=0; double Began=0,At=0;
    UPostProcessComponent* Exposure=nullptr; UBoxComponent* Bounds=nullptr;
    ADinkScreenVolume* Home=nullptr; ADinkScreenVolume* Yard=nullptr;
    TWeakObjectPtr<ADinkGreyboxCharacter> SavedHero; UInputComponent* Input=nullptr;
    FTransform BoundsTransform; FVector BoundsExtent,Outside;
    FCollisionResponseContainer CapsuleResponses; ECollisionEnabled::Type CapsuleEnabled=ECollisionEnabled::NoCollision;
};
class FRestoreExposureArt : public IAutomationLatentCommand
{
public: explicit FRestoreExposureArt(int32 V):Value(V) {} bool Update() override { IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"))->Set(Value,ECVF_SetByCode); return true; }
private:int32 Value;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkScreenExposureTest,"Dink.Art.Exposure.OwnerScreenLifecycle",DINK_TEST_FLAGS)
bool FDinkScreenExposureTest::RunTest(const FString&)
{
    const FString File=FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"),FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("real gameplay world loads"),UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    IConsoleVariable* Art=IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled")); const int32 Prior=Art->GetInt(); Art->Set(1,ECVF_SetByCode);
    AddCommand(new FStartPIECommand(false)); AddCommand(new FScreenExposurePIE(this)); AddCommand(new FEndPlayMapCommand()); AddCommand(new FRestoreExposureArt(Prior)); return true;
}
