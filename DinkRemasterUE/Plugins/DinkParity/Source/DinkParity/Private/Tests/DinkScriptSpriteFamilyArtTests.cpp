// Sprites that scripts create (create_sprite: dropped gold, hearts, potions) have no card and no origin ID; they were
// drawn as the grey marker cylinder. This checks, in the real world in PIE, that such a sprite shows the family mesh of
// its picture when families.json has a row for it, that the mesh follows sp_size and a change of picture, that a
// picture without a row keeps the marker, and that nothing but the look changes (no collision, no authored-art tag).
#include "DinkTestHelpers.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkDirector.h"
#include "DinkOriginComponent.h"
#include "DinkScriptSpriteComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
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
	UStaticMeshComponent* ScriptFamilyMesh(const AActor& Actor)
	{
		return Actor.FindComponentByTag<UStaticMeshComponent>(UDinkArtFamilySubsystem::ScriptSpriteTag);
	}

	class FDinkScriptSpriteFamilyCheck : public IAutomationLatentCommand
	{
	public:
		explicit FDinkScriptSpriteFamilyCheck(FAutomationTestBase* InTest) : Test(InTest) {}

		bool Update() override
		{
			UWorld* World = GEditor ? GEditor->PlayWorld.Get() : nullptr;
			UDinkStorySubsystem* Story = World && World->GetGameInstance() ? World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
			if (Began == 0) Began = FPlatformTime::Seconds();
			if (FPlatformTime::Seconds() - Began > 120)
			{
				Test->AddError(TEXT("script sprite family art check timed out"));
				return true;
			}
			if (!Story || Story->bNewGamePending) return false;
			UDinkArtFamilySubsystem* Family = World->GetSubsystem<UDinkArtFamilySubsystem>();
			UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
			UDinkDirector* Director = Story->GetDirector();
			if (!Test->TestNotNull(TEXT("family subsystem exists in PIE"), Family) || !Test->TestNotNull(TEXT("greybox subsystem"), Greybox) ||
				!Test->TestNotNull(TEXT("director"), Director))
				return true;
			if (!Greybox->GetCurrentScreen()) return false;
			FAssetCompilingManager::Get().FinishAllCompilation();
			if (!Test->TestTrue(TEXT("family subsystem is ready"), Family->IsReady())) return true;

			// A picture with a family row and one without, read from the world's own placements (not from the subsystem's index).
			// The gold heap (178/4) is what enemies drop; any other bound picture serves when the manifest has no gold row.
			int32 BoundSeq = 0, BoundFrame = 0, FreeSeq = 0, FreeFrame = 0;
			const FDinkFamilyBinding* Binding = nullptr;
			for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
			{
				if (!It->Origin || It->Origin->Sequence <= 0 || It->Origin->Frame <= 0) continue;
				const FDinkFamilyBinding* B = DinkArtFamily::Resolve(Family->GetBindings(), It->Origin->Sequence, It->Origin->ClassId, It->Origin->Frame);
				const int32 Key = It->Origin->Sequence << 16 | It->Origin->Frame;
				if (B && LoadObject<UStaticMesh>(nullptr, *B->Mesh, nullptr, LOAD_NoWarn | LOAD_Quiet))
				{
					const bool bGold = It->Origin->Sequence == 178 && It->Origin->Frame == 4;
					const bool bHaveGold = BoundSeq == 178 && BoundFrame == 4;
					if (!Binding || (bGold && !bHaveGold) || (!bHaveGold && Key < (BoundSeq << 16 | BoundFrame)))
					{
						Binding = B;
						BoundSeq = It->Origin->Sequence;
						BoundFrame = It->Origin->Frame;
					}
				}
				else if (!B && (FreeSeq == 0 || Key < (FreeSeq << 16 | FreeFrame)))
				{
					FreeSeq = It->Origin->Sequence;
					FreeFrame = It->Origin->Frame;
				}
			}
			if (!Test->TestNotNull(TEXT("the world places a picture whose family has a mesh"), Binding) ||
				!Test->TestTrue(TEXT("the world places a picture without a family row"), FreeSeq > 0))
				return true;
			Test->AddInfo(FString::Printf(TEXT("bound picture %d/%d (family %s), unbound picture %d/%d"), BoundSeq, BoundFrame, *Binding->Family, FreeSeq, FreeFrame));

			FDinkScriptInstance Caller;
			Caller.Id = 900101;
			Caller.Sprite = 1;
			Caller.Screen = Greybox->GetCurrentScreen()->ScreenNumber;
			auto Create = [&](int32 X, int32 Seq, int32 Frame) -> ADinkScriptSpriteActor*
			{
				TSet<int32> Had;
				for (const auto& Pair : Director->GetSprites()) Had.Add(Pair.Key);
				Director->Execute(Caller, FDinkStoryLine::Parse(FString::Printf(TEXT(">> create_sprite %d 200 6 %d %d"), X, Seq, Frame), {TEXT("cmd"), TEXT("src:1")}));
				for (const auto& Pair : Director->GetSprites())
					if (!Had.Contains(Pair.Key) && Pair.Value.bSpawned && Pair.Value.Actor.IsValid())
					{
						Handle = Pair.Key;
						return Cast<ADinkScriptSpriteActor>(Pair.Value.Actor.Get());
					}
				return nullptr;
			};

			ADinkScriptSpriteActor* Heap = Create(300, BoundSeq, BoundFrame);
			if (!Test->TestNotNull(TEXT("create_sprite spawns the script sprite actor"), Heap)) return true;
			const int32 HeapHandle = Handle;
			UStaticMeshComponent* Mesh = ScriptFamilyMesh(*Heap);
			if (!Test->TestNotNull(TEXT("a created sprite of a bound picture carries the family mesh"), Mesh)) return true;
			const FString Path = Mesh->GetStaticMesh() ? Mesh->GetStaticMesh()->GetPathName() : FString();
			Test->TestTrue(TEXT("the mesh is the family's mesh or one of its variants"), Path == Binding->Mesh || Binding->Variants.Contains(Path));
			Test->TestTrue(TEXT("the grey marker is hidden"), Heap->Marker->bHiddenInGame);
			Test->TestFalse(TEXT("the family mesh is drawn"), Mesh->bHiddenInGame);
			Test->TestFalse(TEXT("the actor itself stays visible"), Heap->IsHidden());
			Test->TestTrue(TEXT("the family mesh has no collision"), Mesh->GetCollisionEnabled() == ECollisionEnabled::NoCollision);
			Test->TestFalse(TEXT("the family mesh makes no overlap events"), Mesh->GetGenerateOverlapEvents());
			Test->TestFalse(TEXT("the family mesh does not affect navigation"), Mesh->CanEverAffectNavigation());
			Test->TestTrue(TEXT("the mesh carries the family tag"), Mesh->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag));
			Test->TestFalse(TEXT("the actor is not authored art (touch keeps the sprite's pixel box)"), Heap->ActorHasTag(TEXT("DinkAuthoredArt")));
			Test->TestTrue(TEXT("the mesh has its real size, not the marker's scale"), Mesh->GetComponentScale().Equals(FVector::OneVector, 0.001));
			const double GroundZ = Heap->GetActorLocation().Z - 60.0;
			Test->TestTrue(TEXT("the mesh stands on the sprite's ground point"), FMath::Abs(Mesh->Bounds.GetBox().Min.Z - GroundZ) < 2.0);
			Test->TestTrue(TEXT("the mesh stands at the sprite's spot"),
				FVector2D::Distance(FVector2D(Mesh->Bounds.Origin), FVector2D(Heap->GetActorLocation())) < 5.0);

			// The twinkle a gold heap creates over itself (brain 15, brain_parm = the heap) has no art: its marker is hidden
			// while it rides on a sprite that shows a family mesh, and only then.
			{
				ADinkScriptSpriteActor* Rider = Create(300, FreeSeq, FreeFrame);
				const int32 RiderHandle = Handle;
				if (Test->TestNotNull(TEXT("a second sprite spawns on the heap"), Rider))
				{
					Test->TestFalse(TEXT("an unbound sprite that follows nothing keeps its marker"), Rider->Marker->bHiddenInGame);
					Director->SpriteProperty(nullptr, TEXT("brain"), RiderHandle, 15);
					Director->SpriteProperty(nullptr, TEXT("brain_parm"), RiderHandle, HeapHandle);
					Test->TestTrue(TEXT("a rider on a dressed sprite hides its marker"), Rider->Marker->bHiddenInGame);
					Test->TestNull(TEXT("the rider gets no mesh of its own"), ScriptFamilyMesh(*Rider));
				}
			}

			// sp_size: the mesh follows the script's size, still on the ground.
			Director->SpriteProperty(nullptr, TEXT("size"), HeapHandle, 200);
			Mesh = ScriptFamilyMesh(*Heap);
			if (Test->TestNotNull(TEXT("the mesh is still there after sp_size"), Mesh))
			{
				Test->TestTrue(TEXT("sp_size 200 doubles the mesh"), Mesh->GetComponentScale().Equals(FVector(2.0), 0.001));
				Test->TestTrue(TEXT("the doubled mesh still stands on the ground"), FMath::Abs(Mesh->Bounds.GetBox().Min.Z - GroundZ) < 2.0);
			}
			Director->SpriteProperty(nullptr, TEXT("size"), HeapHandle, 100);

			// A picture without a row: the marker comes back; and the mesh returns with the bound picture.
			Director->SpriteProperty(nullptr, TEXT("pseq"), HeapHandle, FreeSeq);
			Director->SpriteProperty(nullptr, TEXT("pframe"), HeapHandle, FreeFrame);
			Test->TestNull(TEXT("a picture without a family row drops the mesh"), ScriptFamilyMesh(*Heap));
			Test->TestFalse(TEXT("and shows the marker again"), Heap->Marker->bHiddenInGame);
			Director->SpriteProperty(nullptr, TEXT("pseq"), HeapHandle, BoundSeq);
			Director->SpriteProperty(nullptr, TEXT("pframe"), HeapHandle, BoundFrame);
			Test->TestNotNull(TEXT("the bound picture brings the mesh back"), ScriptFamilyMesh(*Heap));
			Test->TestTrue(TEXT("and hides the marker again"), Heap->Marker->bHiddenInGame);

			// nodraw hides the whole actor, mesh included.
			Director->SpriteProperty(nullptr, TEXT("nodraw"), HeapHandle, 1);
			Test->TestTrue(TEXT("sp_nodraw hides the actor with its mesh"), Heap->IsHidden());
			Director->SpriteProperty(nullptr, TEXT("nodraw"), HeapHandle, 0);

			ADinkScriptSpriteActor* Plain = Create(360, FreeSeq, FreeFrame);
			if (Test->TestNotNull(TEXT("create_sprite of an unbound picture spawns"), Plain))
			{
				Test->TestNull(TEXT("an unbound picture gets no family mesh"), ScriptFamilyMesh(*Plain));
				Test->TestFalse(TEXT("an unbound picture keeps its marker"), Plain->Marker->bHiddenInGame);
				Test->TestTrue(TEXT("an unbound marker keeps its scale"), Plain->GetActorScale3D().Equals(FVector(.3, .3, .6), .001));
			}
			return true;
		}

	private:
		FAutomationTestBase* Test;
		double Began = 0;
		int32 Handle = 0;
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkScriptSpriteFamilyArtTest, "Dink.Art.Family.ScriptSpriteShowsFamilyMesh", DINK_TEST_FLAGS)
bool FDinkScriptSpriteFamilyArtTest::RunTest(const FString&)
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
	ADD_LATENT_AUTOMATION_COMMAND(FDinkScriptSpriteFamilyCheck(this));
	ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
	return true;
}
