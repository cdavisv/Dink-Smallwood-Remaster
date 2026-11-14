// Mounted family rows (families.json `mount`: on, crown, wall) stand their mesh on, in or against another dressed
// placement instead of on the ground. The audit (Scripts/art_coverage.py) counts every placement of such a row on the
// screens the row names as final, without knowing whether a host was found. This checks, in the real world in PIE, that
// the game agrees: on each of those screens every placement the row binds is dressed, above the ground, with no collision.
#include "DinkTestHelpers.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "AssetCompilingManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Editor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "HAL/FileManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
	class FDinkMountedFamilyCheck : public IAutomationLatentCommand
	{
	public:
		explicit FDinkMountedFamilyCheck(FAutomationTestBase* InTest) : Test(InTest) {}

		bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			UDinkStorySubsystem* Story = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
			if (Began == 0) Began = FPlatformTime::Seconds();
			if (FPlatformTime::Seconds() - Began > 120)
			{
				Test->AddError(TEXT("mounted family art check timed out"));
				return true;
			}
			if (!Story || Story->bNewGamePending) return false;
			UDinkArtFamilySubsystem* Family = World->GetSubsystem<UDinkArtFamilySubsystem>();
			UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
			if (!Test->TestNotNull(TEXT("family subsystem exists in PIE"), Family) || !Test->TestNotNull(TEXT("greybox subsystem"), Greybox)) return true;
			if (!Greybox->GetCurrentScreen()) return false;
			FAssetCompilingManager::Get().FinishAllCompilation();
			if (!Test->TestTrue(TEXT("family subsystem is ready"), Family->IsReady())) return true;

			int32 Rows = 0, Wanted = 0, Dressed = 0;
			for (const FDinkFamilyBinding& B : Family->GetBindings())
			{
				if (B.Mount == 0) continue;
				++Rows;
				Test->TestTrue(FString::Printf(TEXT("%s: a mounted row names its screens"), *B.Family), !B.Screens.IsEmpty());
				if (!LoadObject<UStaticMesh>(nullptr, *B.Mesh, nullptr, LOAD_NoWarn | LOAD_Quiet))
				{
					Test->AddError(FString::Printf(TEXT("%s: mesh %s is missing"), *B.Family, *B.Mesh));
					continue;
				}
				for (const int32 Screen : B.Screens) Family->ApplyScreen(Screen);
				// actor placements
				for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
				{
					if (!It->Origin || !B.Screens.Contains(It->ScreenNumber) || It->PlacementKind == TEXT("hardness_only")) continue;
					FDinkFamilyPlacement P;
					P.Origin = It->Origin->OriginId.ToString();
					P.Screen = It->ScreenNumber;
					P.Sequence = It->Origin->Sequence;
					P.Frame = It->Origin->Frame;
					P.ClassId = It->Origin->ClassId;
					P.bScripted = !It->Origin->ScriptName.IsNone();
					const FDinkFamilyBinding* Found = nullptr;
					if (DinkArtFamily::Decide(P, Family->GetPrecedence(), Family->GetBindings(), Found) != EDinkFamilyDecision::Bound || Found != &B) continue;
					++Wanted;
					UStaticMeshComponent* Shown = nullptr;
					TInlineComponentArray<UStaticMeshComponent*> Parts(*It);
					for (UStaticMeshComponent* C : Parts) if (C != It->Card && C->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)) Shown = C;
					if (!Test->TestNotNull(FString::Printf(TEXT("%s (%s): found its host and shows a mesh"), *P.Origin, *B.Family), Shown)) continue;
					++Dressed;
					Test->TestTrue(FString::Printf(TEXT("%s: its card is hidden"), *P.Origin), It->Card && It->Card->bHiddenInGame);
					Test->TestTrue(FString::Printf(TEXT("%s: the mesh is above the ground"), *P.Origin), Shown->Bounds.GetBox().Min.Z > 20.0);
					Test->TestTrue(FString::Printf(TEXT("%s: the mesh has no collision"), *P.Origin), Shown->GetCollisionEnabled() == ECollisionEnabled::NoCollision);
					Test->TestFalse(FString::Printf(TEXT("%s: not authored art (gameplay keeps the pixel rules)"), *P.Origin), It->ActorHasTag(TEXT("DinkAuthoredArt")));
				}
				// background placements: the decor component of each is hidden and a family component stands in for it
				for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It)
				{
					if (!It->InstanceOrigins || !B.Screens.Contains(It->ScreenNumber)) continue;
					TInlineComponentArray<UInstancedStaticMeshComponent*> Components(*It);
					for (const FDinkInstanceOrigin& O : It->InstanceOrigins->Origins)
					{
						FDinkFamilyPlacement P;
						P.Origin = O.OriginId.ToString();
						P.Screen = It->ScreenNumber;
						P.Sequence = O.Sequence;
						P.Frame = O.Frame;
						P.ClassId = O.ClassId;
						P.bScripted = !O.ScriptName.IsNone();
						const FDinkFamilyBinding* Found = nullptr;
						if (DinkArtFamily::Decide(P, Family->GetPrecedence(), Family->GetBindings(), Found) != EDinkFamilyDecision::Bound || Found != &B) continue;
						++Wanted;
						UInstancedStaticMeshComponent* Decor = nullptr;
						UInstancedStaticMeshComponent* Shown = nullptr;
						const FString Prefix = FString::Printf(TEXT("FamilyArt_%s_"), *O.ComponentName.ToString());
						for (UInstancedStaticMeshComponent* C : Components)
						{
							if (C->GetFName() == O.ComponentName) Decor = C;
							if (C->GetName().StartsWith(Prefix)) Shown = C;
						}
						if (!Test->TestTrue(FString::Printf(TEXT("%s (%s): its decor component is hidden and a family component stands in"), *P.Origin, *B.Family),
							Decor && Decor->bHiddenInGame && Shown && Shown->GetInstanceCount() > 0)) continue;
						++Dressed;
						Test->TestTrue(FString::Printf(TEXT("%s: the mesh is above the ground"), *P.Origin), Shown->Bounds.GetBox().Min.Z > 20.0);
						Test->TestTrue(FString::Printf(TEXT("%s: the mesh has no collision"), *P.Origin), Shown->GetCollisionEnabled() == ECollisionEnabled::NoCollision);
					}
				}
			}
			Test->AddInfo(FString::Printf(TEXT("mounted rows %d, placements they bind %d, dressed %d"), Rows, Wanted, Dressed));
			if (Rows > 0) Test->TestTrue(TEXT("the mounted rows bind placements of the world"), Wanted > 0);
			return true;
		}

	private:
		FAutomationTestBase* Test;
		double Began = 0;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkMountedFamilyArtTest, "Dink.Art.Family.MountedPlacementsFindTheirHost", DINK_TEST_FLAGS)
bool FDinkMountedFamilyArtTest::RunTest(const FString&)
{
	if (!IFileManager::Get().FileExists(*DinkArtFamily::DefaultFamiliesPath()))
	{
		AddWarning(TEXT("skipped: no families.json"));
		return true;
	}
	const FString File = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"), FPackageName::GetMapPackageExtension());
	if (!IFileManager::Get().FileExists(*File))
	{
		AddWarning(TEXT("skipped: greybox world not imported (Scripts/import_greybox.sh --region all)"));
		return true;
	}
	if (!TestNotNull(TEXT("real world map loads"), UEditorLoadingAndSavingUtils::LoadMap(File))) return false;
	FAssetCompilingManager::Get().FinishAllCompilation();
	ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
	ADD_LATENT_AUTOMATION_COMMAND(FDinkMountedFamilyCheck(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
