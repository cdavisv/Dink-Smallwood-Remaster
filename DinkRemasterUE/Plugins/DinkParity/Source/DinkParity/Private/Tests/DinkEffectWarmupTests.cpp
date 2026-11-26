// One-shot effect materials ready before their first use (23 Nov 2026): the 161 fire burst that s7-mil.c:125 creates on
// SCR_086 showed as a white card at its first use in the rendered game (its material's shaders were still compiling and the
// engine drew its default material). UDinkArtFamilySubsystem::WarmEffects runs at each screen entry: it finishes such
// compiles and keeps one hidden card holding every effect material so their PSOs are requested ahead of use.
#include "DinkTestHelpers.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "AssetCompilingManager.h"
#include "Components/MaterialBillboardComponent.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "HAL/FileManager.h"
#include "Materials/MaterialInterface.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
	class FDinkEffectWarmupCheck : public IAutomationLatentCommand
	{
	public:
		explicit FDinkEffectWarmupCheck(FAutomationTestBase* InTest) : Test(InTest) {}
		bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			UDinkStorySubsystem* Story = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
			if (Began == 0) Began = FPlatformTime::Seconds();
			if (FPlatformTime::Seconds() - Began > 120) { Test->AddError(TEXT("effect warm-up check timed out")); return true; }
			if (!Story || Story->bNewGamePending) return false;
			UDinkArtFamilySubsystem* Family = World->GetSubsystem<UDinkArtFamilySubsystem>();
			UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
			if (!Test->TestNotNull(TEXT("family subsystem"), Family) || !Test->TestNotNull(TEXT("greybox subsystem"), Greybox)) return true;
			if (!Greybox->GetCurrentScreen()) return false;
			if (!Test->TestTrue(TEXT("family subsystem is ready"), Family->IsReady())) return true;
			// every effect material of the rows (the one-shots scripts create among them), each once
			TSet<FString> Paths;
			TSet<FString> OneShots;
			for (const FDinkFamilyBinding& B : Family->GetBindings())
			{
				if (B.Effect.IsEmpty()) continue;
				if (LoadObject<UMaterialInterface>(nullptr, *B.Effect, nullptr, LOAD_NoWarn | LOAD_Quiet)) Paths.Add(B.Effect);
				if (!B.EffectPlume.IsEmpty() && LoadObject<UMaterialInterface>(nullptr, *B.EffectPlume, nullptr, LOAD_NoWarn | LOAD_Quiet)) Paths.Add(B.EffectPlume);
				if (!B.bEffectPlaced) OneShots.Add(B.Effect);
			}
			const UMaterialBillboardComponent* Card = Family->GetWarmCard();
			if (!Test->TestNotNull(TEXT("the warm-up card exists after the first screen entry"), Card)) return true;
			TSet<FString> Held;
			for (const FMaterialSpriteElement& E : Card->Elements) if (E.Material) Held.Add(E.Material->GetPathName());
			Test->TestEqual(TEXT("it holds every effect material once"), Card->Elements.Num(), Paths.Num());
			for (const FString& Path : Paths) Test->TestTrue(FString::Printf(TEXT("held: %s"), *Path), Held.Contains(Path));
			Test->TestTrue(TEXT("the 161 fire burst (s7-mil.c:125) is among the one-shots"),
				OneShots.Contains(TEXT("/Game/Dink/Photoreal/Unclaimed/MI_FX_Atomic.MI_FX_Atomic")));
			Test->TestFalse(TEXT("never drawn"), Card->IsVisible() || !Card->bHiddenInGame);
			Test->TestFalse(TEXT("no collision"), Card->IsCollisionEnabled());
			// a second warm-up has nothing left to compile and makes no second card
			Test->TestEqual(TEXT("nothing left compiling"), Family->WarmEffects(), 0);
			Test->TestTrue(TEXT("one card"), Family->GetWarmCard() == Card);
			return true;
		}
	private:
		FAutomationTestBase* Test;
		double Began = 0;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkEffectWarmupTest, "Dink.Art.Family.EffectMaterialsWarmedAtScreenEntry", DINK_TEST_FLAGS)
bool FDinkEffectWarmupTest::RunTest(const FString&)
{
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!IFileManager::Get().FileExists(*File))
	{
		AddWarning(TEXT("skipped: greybox world not imported (Scripts/import_greybox.sh --region all)"));
		return true;
	}
	if (!TestNotNull(TEXT("real world map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	FAssetCompilingManager::Get().FinishAllCompilation();
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FDinkEffectWarmupCheck(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
