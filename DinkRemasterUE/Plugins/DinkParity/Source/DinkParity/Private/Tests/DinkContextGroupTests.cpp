#include "DinkTestHelpers.h"
#include "DinkArtContextActor.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
namespace
{
TSharedPtr<FJsonObject> GroupSpec(const TArray<TSharedPtr<FJsonValue>>& Screens)
{
    auto Spec=MakeShared<FJsonObject>(),Context=MakeShared<FJsonObject>(),Row=MakeShared<FJsonObject>();
    Spec->SetStringField(TEXT("schema"),TEXT("dink-art/1")); Spec->SetNumberField(TEXT("screen"),439);
    Context->SetStringField(TEXT("visibility"),TEXT("screen_set")); Context->SetBoolField(TEXT("render_only"),true);
    Context->SetArrayField(TEXT("screens"),Screens); Spec->SetObjectField(TEXT("context"),Context);
    Row->SetStringField(TEXT("mesh"),TEXT("/Engine/BasicShapes/Cube.Cube"));
    Row->SetBoolField(TEXT("collision"),false); Row->SetBoolField(TEXT("camera_occluder"),false);
    for (const TCHAR* Key:{TEXT("world_cm"),TEXT("rotation_deg"),TEXT("scale")})
    {
        const double V=FCString::Strcmp(Key,TEXT("scale"))==0 ? 1. : 0.;
        Row->SetArrayField(Key,{MakeShared<FJsonValueNumber>(V),MakeShared<FJsonValueNumber>(V),MakeShared<FJsonValueNumber>(V)});
    }
    Spec->SetArrayField(TEXT("elements"),{MakeShared<FJsonValueObject>(Row)});
    return Spec;
}
class FContextGroupCheck : public IAutomationLatentCommand
{
public:
    explicit FContextGroupCheck(FAutomationTestBase* T):Test(T) {}
    bool Update() override
    {
        if (!Start) Start=FPlatformTime::Seconds();
        if (FPlatformTime::Seconds()-Start>90) { Test->AddError(TEXT("shared context fixture timed out")); return true; }
        UWorld* W=GEditor ? GEditor->PlayWorld.Get() : nullptr;
        auto* PC=W ? W->GetFirstPlayerController() : nullptr;
        auto* H=PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
        auto* Story=W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (!H || !Story || Story->bNewGamePending) return false;
        auto* G=W->GetSubsystem<UDinkGreyboxSubsystem>();
        if (!Phase)
        {
            Story->SkipDialogue(); if (PC->IsMoveInputIgnored()) return false;
            Story->bRunScreenScripts=false;
            UStaticMesh* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
            TMap<FString,UStaticMesh*> Meshes; Meshes.Add(Cube->GetPathName(),Cube);
            auto Number=[](double N){return MakeShared<FJsonValueNumber>(N);};
            for (const auto& Invalid:TArray<TArray<TSharedPtr<FJsonValue>>>{{},{Number(439),Number(439)},
                {Number(439),Number(471.5)},{Number(439),Number(769)},{Number(439),Number(0)},
                {Number(471)},{Number(439),MakeShared<FJsonValueString>(TEXT("471"))}})
                Test->TestNull(TEXT("invalid shared visibility set rejected before spawn"),ADinkArtContextActor::CreateFromManifest(*W,GroupSpec(Invalid),Meshes,439));
            auto Spec=GroupSpec({Number(439),Number(471)});
            Context=ADinkArtContextActor::CreateFromManifest(*W,Spec,Meshes,439);
            if (!Test->TestNotNull(TEXT("strict shared context factory accepts bounded set"),Context)) return true;
            Test->TestTrue(TEXT("cached439 physical471 retains shared scenery"),Context->IncludesScreenPair(439,471));
            Test->TestTrue(TEXT("cached471 physical439 retains shared scenery"),Context->IncludesScreenPair(471,439));
            Test->TestFalse(TEXT("physical uncovered screen disables shared scenery"),Context->IncludesScreenPair(439,1));
            Test->TestFalse(TEXT("missing cached screen disables shared scenery"),Context->IncludesScreenPair(0,439));
            const auto* Yard=G->FindScreen(439);
            H->SetActorLocation(Yard->MapPixelToWorld(450,350)+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics);
            H->GetCharacterMovement()->StopMovementImmediately(); G->RefreshCurrentScreen();
            Context->ConfigureScreenSet({439,471});
            Test->TestFalse(TEXT("real covered yard makes context visible"),Context->IsHidden());
            Before=Context->GetActorTransform();
            ++Phase; return false;
        }
        if (Phase==1)
        {
            const auto* Neighbor=G->FindScreen(471);
            H->SetActorLocation(Neighbor->MapPixelToWorld(300,200)+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics);
            Context->ConfigureScreenSet({439,471});
            Test->TestFalse(TEXT("real cross-screen move does not hide shared scenery during cache lag"),Context->IsHidden());
            G->RefreshCurrentScreen(); Context->ConfigureScreenSet({439,471});
            Test->TestFalse(TEXT("updated cache still displays same context"),Context->IsHidden());
            Test->TestTrue(TEXT("context never relocates to another coordinate frame while walking"),Context->GetActorTransform().Equals(Before));
            PC->UnPossess(); Context->ConfigureScreenSet({439,471});
            Test->TestTrue(TEXT("missing pawn hides shared scenery"),Context->IsHidden()); PC->Possess(H);
            const auto* Yard=G->FindScreen(439);
            H->SetActorLocation(Yard->MapPixelToWorld(300,200)+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics);
            G->RefreshCurrentScreen();
            auto* Duplicate=W->SpawnActor<ADinkScreenVolume>();
            Duplicate->ScreenNumber=439; Duplicate->Corners=Yard->Corners;
            const FVector2D Offset(100000,100000);
            Duplicate->Corners.NW+=Offset; Duplicate->Corners.NE+=Offset;
            Duplicate->Corners.SW+=Offset; Duplicate->Corners.SE+=Offset;
            const FVector DuplicateCenter=Duplicate->MapPixelToWorld(300,200);
            Duplicate->SetActorLocation(DuplicateCenter);
            Duplicate->Bounds->SetBoxExtent(FVector(10000,10000,1000));
            H->SetActorLocation(DuplicateCenter+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics);
            Test->TestTrue(TEXT("fixture physical volume differs from cached volume despite same ID"),G->FindScreenAt(H->GetActorLocation())==Duplicate && G->GetCurrentScreen()==Yard);
            Context->ConfigureOwnerScreen(439);
            Test->TestTrue(TEXT("owner-only context preserves strict volume identity during duplicate-ID cache lag"),Context->IsHidden());
            G->RefreshCurrentScreen(); Context->ConfigureOwnerScreen(439);
            Test->TestFalse(TEXT("owner-only context resumes when actual cached volume matches"),Context->IsHidden());
            Duplicate->Destroy();
            const auto* Home=G->FindScreen(1);
            H->SetActorLocation(Home->MapPixelToWorld(370,161)+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics);
            G->RefreshCurrentScreen(); Context->ConfigureScreenSet({439,471});
            Test->TestTrue(TEXT("separate interior never displays exterior-world context"),Context->IsHidden());
            Context->ConfigureOwnerScreen(439);
            Test->TestFalse(TEXT("restoring old owner-only policy removes shared screen membership"),Context->IncludesScreenPair(439,471));
            Context->Destroy(); return true;
        }
        return false;
    }
private:
    FAutomationTestBase* Test;
    ADinkArtContextActor* Context=nullptr;
    FTransform Before;
    double Start=0;
    int32 Phase=0;
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkContextGroupTest,"Dink.Art.Context.SharedOutdoorVisibility",DINK_TEST_FLAGS)
bool FDinkContextGroupTest::RunTest(const FString&)
{
    const FString File=FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"),FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("real world loads"),UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    AddCommand(new FStartPIECommand(false)); AddCommand(new FContextGroupCheck(this)); AddCommand(new FEndPlayMapCommand()); return true;
}
