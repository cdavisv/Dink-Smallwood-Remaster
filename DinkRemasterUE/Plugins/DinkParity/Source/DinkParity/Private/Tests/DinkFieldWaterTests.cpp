#include "DinkTestHelpers.h"
#include "DinkCollision.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
class FDinkFieldWaterCheck : public IAutomationLatentCommand
{
public:
    explicit FDinkFieldWaterCheck(FAutomationTestBase* InTest) : Test(InTest) {}
    bool Update() override
    {
        UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
        UDinkStorySubsystem* Story = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (Began == 0) Began = FPlatformTime::Seconds();
        // Cold imported meshes can consume the first PIE frame compiling render/physics resources.
        if (FPlatformTime::Seconds() - Began > 90) { Test->AddError(TEXT("field water PIE setup timed out")); return true; }
        if (!Story || Story->bNewGamePending) return false;
        FAssetCompilingManager::Get().FinishAllCompilation();
        UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
        const FCollisionShape Player = FCollisionShape::MakeCapsule(28, 96);
        for (const int32 Id : {438, 471})
        {
            ADinkScreenVolume* Screen = Greybox->FindScreen(Id);
            ADinkGreyboxScreen* Source = nullptr;
            for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It) if (It->ScreenNumber == Id) Source = *It;
            if (!Test->TestNotNull(TEXT("real field screen loaded"), Screen) || !Test->TestNotNull(TEXT("real field collision owner loaded"), Source)) continue;
            UStaticMeshComponent* Low = Source->CollisionLow;
            Test->TestTrue(TEXT("authored field replaced original solid collider"), Source->CollisionSolid->GetCollisionEnabled() == ECollisionEnabled::NoCollision);
            Test->TestTrue(TEXT("original low-water collider retained"), Low && Low->IsQueryCollisionEnabled());
            if (!Low) continue;
            Test->TestEqual(TEXT("retained low collider blocks player"), Low->GetCollisionResponseToChannel(ECC_Pawn), ECR_Block);
            Test->TestEqual(TEXT("retained low collider passes original projectiles"), Low->GetCollisionResponseToChannel(DinkCollision::Projectile), ECR_Ignore);
            auto At = [&](double X, double Y, double Z) { FVector P = Screen->MapPixelToWorld(X, Y); P.Z = Z; return P; };
            auto Dry = [&](double X, double Y)
            {
                const FString Label = FString::Printf(TEXT("SCR%d dry%.0f,%.0f"), Id, X, Y);
                Test->TestFalse(Label + TEXT(" remains free for actual player body"), World->OverlapBlockingTestByChannel(At(X, Y, 100), FQuat::Identity, ECC_Pawn, Player));
                FHitResult Floor;
                Test->TestTrue(Label + TEXT(" has authored walking support"), World->LineTraceSingleByChannel(Floor, At(X, Y, 200), At(X, Y, -10), ECC_Pawn));
                Test->TestTrue(Label + TEXT(" support stays near original ground height"), Floor.bBlockingHit && Floor.ImpactPoint.Z >= -.1 && Floor.ImpactPoint.Z < 5);
            };
            if (Id == 471)
            {
                Dry(150, 100); Dry(500, 300);
                // Generated collision prisms are3m tall. Starting fully inside a trimesh has no surface overlap.
                FHitResult Wet;
                Test->TestTrue(TEXT("471 original filled-water blocks incoming actual body"), World->SweepSingleByChannel(Wet, At(150, 300, 500), At(150, 300, 100), FQuat::Identity, ECC_Pawn, Player));
                Test->TestTrue(TEXT("471 filled-water stop is retained original Low"), Wet.GetComponent() == Low);
                FHitResult WetProjectile;
                Test->TestFalse(TEXT("471 projectile passes filled-water from outside its trimesh"), World->LineTraceSingleByChannel(WetProjectile, At(150, 300, 350), At(150, 300, 20), DinkCollision::Projectile));
                FHitResult Bank;
                Test->TestTrue(TEXT("471 dry-to-water player sweep stops at retained bank"), World->SweepSingleByChannel(Bank, At(150, 100, 100), At(150, 300, 100), FQuat::Identity, ECC_Pawn, Player));
                Test->TestTrue(TEXT("471 bank block is original low-water geometry"), Bank.GetComponent() == Low);
                FHitResult Projectile;
                Test->TestFalse(TEXT("471 projectile crosses low bank without new art obstruction"), World->LineTraceSingleByChannel(Projectile, At(150, 100, 20), At(150, 300, 20), DinkCollision::Projectile));
            }
            else
            {
                Dry(300, 160); Dry(300, 210); Dry(300, 270); Dry(500, 300);
                for (const double X : {325., 479.})
                    Test->TestTrue(TEXT("438 original pond ring blocks actual player body"), World->OverlapBlockingTestByChannel(At(X, 290, 100), FQuat::Identity, ECC_Pawn, Player));
                FHitResult Bank;
                Test->TestTrue(TEXT("438 dry-to-pond player sweep stops at source ring"), World->SweepSingleByChannel(Bank, At(300, 290, 100), At(400, 290, 100), FQuat::Identity, ECC_Pawn, Player));
                Test->TestTrue(TEXT("438 ring block is original low geometry"), Bank.GetComponent() == Low);
                FHitResult Projectile;
                Test->TestFalse(TEXT("438 projectile crosses low pond ring"), World->LineTraceSingleByChannel(Projectile, At(300, 290, 20), At(400, 290, 20), DinkCollision::Projectile));
                FHitResult Corridor;
                Test->TestFalse(TEXT("438 original north-south dry corridor stays open"), World->SweepSingleByChannel(Corridor, At(300, 160, 100), At(300, 270, 100), FQuat::Identity, ECC_Pawn, Player));
                FHitResult Interior;
                Test->TestFalse(TEXT("438 unfilled pond interior gains no invented walkable floor"), World->LineTraceSingleByChannel(Interior, At(400, 290, 50), At(400, 290, -10), ECC_Pawn));
            }
        }
        return true;
    }
private:
    FAutomationTestBase* Test;
    double Began = 0;
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkFieldWaterTest, "Dink.Import.Fields.RetainedLowWaterAndDryCorridors", DINK_TEST_FLAGS)
bool FDinkFieldWaterTest::RunTest(const FString&)
{
    TSet<int32> Preserved;
    const FString Directory = FPaths::ProjectContentDir() / TEXT("Dink/Data/Art");
    TArray<FString> Files;
    IFileManager::Get().FindFiles(Files, *(Directory / TEXT("*.json")), true, false);
    for (const FString& File : Files)
    {
        FString Text; TSharedPtr<FJsonObject> Manifest;
        if (!FFileHelper::LoadFileToString(Text, *(Directory / File)) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest) continue;
        const TArray<TSharedPtr<FJsonValue>>* Screens = nullptr;
        if (Manifest->TryGetArrayField(TEXT("preserve_low_collision_screens"), Screens))
            for (const auto& Screen : *Screens) if (int32(Screen->AsNumber()) == 438 || int32(Screen->AsNumber()) == 471) Preserved.Add(int32(Screen->AsNumber()));
    }
    if (Preserved.IsEmpty()) { AddWarning(TEXT("skipped: authored field manifests not imported")); return true; }
    if (!TestTrue(TEXT("both authored fields preserve original low collision"), Preserved.Contains(438) && Preserved.Contains(471))) return false;
    const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
    if (!TestTrue(TEXT("real world map available"), IFileManager::Get().FileExists(*File))) return false;
    if (!TestNotNull(TEXT("real world map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkFieldWaterCheck(this));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
    return true;
}
