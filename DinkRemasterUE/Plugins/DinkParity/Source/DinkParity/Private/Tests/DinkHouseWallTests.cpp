#include "DinkTestHelpers.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
class FCheckHouseWalls : public IAutomationLatentCommand
{
public:
    FCheckHouseWalls(FAutomationTestBase* InTest, bool InAuthored) : Test(InTest), bAuthored(InAuthored) {}
    bool Update() override
    {
        UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
        UDinkStorySubsystem* Story = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (!Began) Began = FPlatformTime::Seconds();
        if (FPlatformTime::Seconds() - Began > 90) { Test->AddError(TEXT("house wall PIE setup timed out")); return true; }
        if (!Story || Story->bNewGamePending) return false;
        ADinkScreenVolume* Home = World->GetSubsystem<UDinkGreyboxSubsystem>()->FindScreen(1);
        if (!Test->TestNotNull(TEXT("real SCR1 house volume loaded"), Home)) return true;
        int32 Visible = 0, Generated = 0, Blocking = 0;
        TArray<UStaticMeshComponent*> Meshes; Home->GetComponents(Meshes);
        for (UStaticMeshComponent* Mesh : Meshes)
        {
            if (!Mesh->GetName().StartsWith(TEXT("InteriorWall_"))) continue;
            ++Generated;
            Visible += Mesh->IsVisible() && !Mesh->bHiddenInGame ? 1 : 0;
            Test->TestEqual(TEXT("generated wall remains presentation only"), Mesh->GetCollisionEnabled(), ECollisionEnabled::NoCollision);
        }
        for (const UBoxComponent* Edge : Home->EdgeWalls)
            if (Edge && Edge->IsQueryCollisionEnabled()) ++Blocking;
        Test->TestTrue(TEXT("physical house edges remain blocking"), Blocking > 0);
        Test->TestEqual(TEXT("one generated visual per blocking edge"), Generated, Blocking);
        if (bAuthored) Test->TestEqual(TEXT("authored house hides every generated checker wall"), Visible, 0);
        else Test->TestEqual(TEXT("ArtEnabled0 retains original greybox wall visuals"), Visible, Blocking);
        // Exercise both lifecycle orders using real actors in the running PIE world.
        // A deferred actor receives the authored choice before its BeginPlay creates cubes.
        ADinkScreenVolume* Probe = World->SpawnActorDeferred<ADinkScreenVolume>(ADinkScreenVolume::StaticClass(), FTransform(FVector(0,0,100000)));
        if (Test->TestNotNull(TEXT("deferred indoor visual probe exists"), Probe))
        {
            Probe->bIndoor = true;
            Probe->EdgeWalls[0]->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
            Probe->EdgeWalls[0]->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
            Probe->EdgeWalls[0]->SetBoxExtent(FVector(100, 10, 160));
            const auto Collision = Probe->EdgeWalls[0]->GetCollisionEnabled();
            const auto Responses = Probe->EdgeWalls[0]->GetCollisionResponseToChannels();
            const FVector Extent = Probe->EdgeWalls[0]->GetUnscaledBoxExtent();
            const FTransform EdgeTransform = Probe->EdgeWalls[0]->GetRelativeTransform();
            Probe->SetInteriorWallVisualsHidden(true);
            Probe->FinishSpawning(Probe->GetActorTransform());
            TArray<UStaticMeshComponent*> ProbeMeshes; Probe->GetComponents(ProbeMeshes);
            int32 ProbeWalls = 0;
            for (UStaticMeshComponent* Mesh : ProbeMeshes)
            {
                if (!Mesh->GetName().StartsWith(TEXT("InteriorWall_"))) continue;
                ++ProbeWalls;
                Test->TestTrue(TEXT("choice before BeginPlay creates hidden cubes"), Mesh->bHiddenInGame);
                Test->TestEqual(TEXT("lifecycle cube never blocks"), Mesh->GetCollisionEnabled(), ECollisionEnabled::NoCollision);
                Probe->SetInteriorWallVisualsHidden(false);
                Test->TestFalse(TEXT("setter after BeginPlay restores cube"), Mesh->bHiddenInGame);
                Probe->SetInteriorWallVisualsHidden(true);
                Test->TestTrue(TEXT("setter after BeginPlay hides existing cube"), Mesh->bHiddenInGame);
            }
            Test->TestEqual(TEXT("deferred enabled edge generated one cube"), ProbeWalls, 1);
            Test->TestEqual(TEXT("hiding never alters edge collision enabled"), Probe->EdgeWalls[0]->GetCollisionEnabled(), Collision);
            Test->TestTrue(TEXT("hiding never alters edge collision responses"), Probe->EdgeWalls[0]->GetCollisionResponseToChannels() == Responses);
            Test->TestTrue(TEXT("hiding never alters edge collision bounds"), Probe->EdgeWalls[0]->GetUnscaledBoxExtent().Equals(Extent));
            Test->TestTrue(TEXT("hiding never alters edge collision transform"), Probe->EdgeWalls[0]->GetRelativeTransform().Equals(EdgeTransform));
            Probe->Destroy();
        }
        return true;
    }
private:
    FAutomationTestBase* Test;
    bool bAuthored;
    double Began = 0;
};
class FRestoreArt : public IAutomationLatentCommand
{
public:
    explicit FRestoreArt(int32 InValue) : Value(InValue) {}
    bool Update() override { IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"))->Set(Value, ECVF_SetByCode); return true; }
private: int32 Value;
};
bool StartWallTest(FAutomationTestBase& Test, bool bAuthored)
{
    const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
    if (!Test.TestNotNull(TEXT("real world map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    IConsoleVariable* Art = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));
    const int32 Before = Art->GetInt(); Art->Set(bAuthored ? 1 : 0, ECVF_SetByCode);
    Test.AddCommand(new FStartPIECommand(false));
    Test.AddCommand(new FCheckHouseWalls(&Test, bAuthored));
    Test.AddCommand(new FEndPlayMapCommand());
    Test.AddCommand(new FRestoreArt(Before));
    return true;
}
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHouseWallsAuthored, "Dink.Art.HouseWalls.AuthoredSuppressesGeneratedVisuals", DINK_TEST_FLAGS)
bool FDinkHouseWallsAuthored::RunTest(const FString&) { return StartWallTest(*this, true); }
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkHouseWallsGreybox, "Dink.Art.HouseWalls.GreyboxRetainsGeneratedVisuals", DINK_TEST_FLAGS)
bool FDinkHouseWallsGreybox::RunTest(const FString&) { return StartWallTest(*this, false); }
