// Dink.Gameplay.OverridePicture.*: a placement whose save holds an editor_type 2-5 SHOWS the save's picture on the next visit.
//
// update_play_changes (dink.cpp:5773-5832) gives such a placement the save's editor_seq / editor_frame (5829-5830) before place_sprites_game
// reads the screen's sprite table (5974); place_sprites_game then draws a type 3/5 placement into the background with that picture
// (6036-6054) and makes a type 2/4 placement a live sprite born with it (6083ff). PR #115 made the simulation follow this; the placement
// actor's look did not (a flattened barrel came back whole, an opened chest closed). UDinkGameplay::PresentPlacementPictures now gives the
// placement actor's card the saved picture's sprite material, at that picture's size and pivot, on every screen entry, and puts the
// imported picture back when the save no longer holds an override.
//
// A game instance with a world (no greybox map): the story's screen entry finds the placement actors spawned here. SCR_060's barrel P08
// (bar-sh: editor_type 3, 173/6, the flat barrel) and SCR_536's chest P31 (ch1-ap: editor_type 4, 175/4, the open small chest; the
// placement itself is the large chest 177/1). The save is written by the DinkC commands themselves, as the scripts' hit procedures do.
// Needs the imported sprite materials (Scripts/import_greybox.sh after Scripts/export_import_bundle.py exports the saved pictures).

#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"

namespace DinkOverridePictureTest
{
	FString MaterialPath(int32 Seq, int32 Frame)
	{
		const FString Key = FString::Printf(TEXT("%d_%02d"), Seq, Frame);
		return FString::Printf(TEXT("/Game/Dink/_Generated/Sprites/MI_Sprite_%s.MI_Sprite_%s"), *Key, *Key);
	}

	FString Shown(const ADinkPlaceholderActor* A)
	{
		const UMaterialInterface* M = A && A->Card ? A->Card->GetMaterial(0) : nullptr;
		return M ? M->GetPathName() : FString(TEXT("(none)"));
	}

	/** A placement actor as the importer makes it: origin, imported picture, card baseline and the picture's sprite material. */
	ADinkPlaceholderActor* Spawn(UWorld* World, const UDinkGameplay& G, const FDinkOriginId& Origin)
	{
		const FDinkPlacementInfo* P = G.GetData().FindPlacement(Origin);
		if (!P)
		{
			return nullptr;
		}
		ADinkPlaceholderActor* A = World->SpawnActor<ADinkPlaceholderActor>();
		A->ScreenNumber = Origin.Screen;
		A->Origin->OriginId = Origin;
		A->Origin->Sequence = P->Seq;
		A->Origin->Frame = P->Frame;
		A->Origin->ScriptName = P->Script;
		A->ImportedCardRelativeTransform = FTransform(FRotator::ZeroRotator, FVector(-90.0, 0.0, -75.0), FVector(3.8, 1.0, 3.8));
		A->bHasImportedCardBaseline = true;
		A->Card->SetRelativeTransform(A->ImportedCardRelativeTransform);
		A->Card->SetMaterial(0, LoadObject<UMaterialInterface>(nullptr, *MaterialPath(P->Seq, P->Frame), nullptr, LOAD_NoWarn | LOAD_Quiet));
		return A;
	}

	/** Runs DinkC command lines (as the converted story emits them) in a script instance on Screen. */
	void Run(UDinkStorySubsystem* Story, int32 Screen, const TArray<FString>& Commands)
	{
		const int32 Id = Story->StartProcedure(TEXT("pdie"), TEXT("main"), 1, {}, Screen, /*bNewInstance*/ true);
		FDinkScriptInstance* Instance = Story->FindInstance(Id);
		if (!Instance)
		{
			return;
		}
		for (const FString& C : Commands)
		{
			Story->GetDirector()->Execute(*Instance, FDinkStoryLine::Parse(TEXT(">> ") + C, { TEXT("cmd"), TEXT("src:1") }));
		}
		Story->RunUntilIdle();
	}

	/** Leaves the screen and comes back (load_map, update_play_changes, place_sprites_game). */
	void Revisit(UDinkStorySubsystem* Story, int32 Screen, int32 Elsewhere)
	{
		Story->OnScreenEntered(Elsewhere);
		Story->RunUntilIdle();
		Story->OnScreenEntered(Screen);
		Story->RunUntilIdle();
	}

	const FDinkSprite* SpriteFor(UDinkDirector* D, const FDinkOriginId& Origin)
	{
		for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
		{
			if (Pair.Value.bActive && Pair.Value.Origin == Origin)
			{
				return &Pair.Value;
			}
		}
		return nullptr;
	}

	/** One case: hit placement Index of Screen (its script's editor_* lines), revisit, check the card; then clear the override and revisit. */
	void Check(FAutomationTestBase& T, UDinkStorySubsystem* Story, UWorld* World, int32 Screen, int32 Index, int32 Type, int32 Seq, int32 Frame, int32 Elsewhere)
	{
		UDinkGameplay* G = Story->GetGameplay();
		const FDinkOriginId Origin(Screen, Index);
		ADinkPlaceholderActor* A = Spawn(World, *G, Origin);
		if (!T.TestNotNull(*FString::Printf(TEXT("%s is in map.dat"), *Origin.ToString()), A))
		{
			return;
		}
		const int32 OldSeq = A->Origin->Sequence, OldFrame = A->Origin->Frame;
		const FDinkFrameInfo* Old = G->GetData().FindFrame(OldSeq, OldFrame);
		const FDinkFrameInfo* New = G->GetData().FindFrame(Seq, Frame);
		if (!T.TestTrue(TEXT("both pictures have frame data (sizes, pivots)"), Old && New && Old->Width > 0 && New->Width > 0) ||
			!T.TestNotNull(*FString::Printf(TEXT("the saved picture's sprite material is imported (%s)"), *MaterialPath(Seq, Frame)),
				LoadObject<UMaterialInterface>(nullptr, *MaterialPath(Seq, Frame), nullptr, LOAD_NoWarn | LOAD_Quiet)))
		{
			return;
		}
		Story->OnScreenEntered(Screen);
		Story->RunUntilIdle();
		T.TestEqual(*FString::Printf(TEXT("%s shows its imported picture before the hit"), *Origin.ToString()), Shown(A), MaterialPath(OldSeq, OldFrame));

		Run(Story, Screen, { FString::Printf(TEXT("editor_type %d %d"), Index, Type), FString::Printf(TEXT("editor_seq %d %d"), Index, Seq),
			FString::Printf(TEXT("editor_frame %d %d"), Index, Frame) });
		if (Type == 3 || Type == 5)
		{
			// The smashed barrel's sprite ends its brain 5 animation killed, which hides its actor for the rest of the visit.
			A->SetActorHiddenInGame(true);
		}
		Revisit(Story, Screen, Elsewhere);
		const FString What = FString::Printf(TEXT("%s with saved editor_type %d, %d/%d"), *Origin.ToString(), Type, Seq, Frame);
		T.TestEqual(*FString::Printf(TEXT("%s: the card shows the saved picture on the next visit (D:5829-5830, %s)"), *What,
			Type == 3 || Type == 5 ? TEXT("drawn into the background, D:6036-6054") : TEXT("the live sprite's picture, D:6083ff")), Shown(A), MaterialPath(Seq, Frame));
		const FVector Scale = A->Card->GetRelativeScale3D();
		const FVector Base = A->ImportedCardRelativeTransform.GetScale3D();
		T.TestTrue(*FString::Printf(TEXT("%s: card width follows the picture's width (%d px instead of %d: %.3f, expected %.3f)"), *What, New->Width, Old->Width,
			Scale.X, Base.X * New->Width / Old->Width), FMath::IsNearlyEqual(Scale.X, Base.X * New->Width / Old->Width, 1e-3));
		T.TestTrue(*FString::Printf(TEXT("%s: card height follows the picture's height (%d px instead of %d)"), *What, New->Height, Old->Height),
			FMath::IsNearlyEqual(Scale.Z, Base.Z * New->Height / Old->Height, 1e-3));
		T.TestTrue(*FString::Printf(TEXT("%s: the importer's baseline is untouched"), *What), A->bHasImportedCardBaseline);
		T.TestFalse(*FString::Printf(TEXT("%s: the actor is shown (drawn into the background or live)"), *What), A->IsHidden());
		if (Type == 2 || Type == 4)
		{
			const FDinkSprite* S = SpriteFor(Story->GetDirector(), Origin);
			if (T.TestNotNull(*FString::Printf(TEXT("%s: a live sprite (D:6083)"), *What), S))
			{
				T.TestEqual(*FString::Printf(TEXT("%s: its pseq is the picture the card shows"), *What), S->GetProp(TEXT("pseq")), Seq);
				T.TestEqual(*FString::Printf(TEXT("%s: its pframe too"), *What), S->GetProp(TEXT("pframe")), Frame);
			}
		}
		else
		{
			T.TestNull(*FString::Printf(TEXT("%s: no sprite (background)"), *What), SpriteFor(Story->GetDirector(), Origin));
		}

		// A save without the override (editor_type 0: update_play_changes leaves the placement alone): the imported picture again.
		Run(Story, Screen, { FString::Printf(TEXT("editor_type %d 0"), Index) });
		Revisit(Story, Screen, Elsewhere);
		T.TestEqual(*FString::Printf(TEXT("%s: without the override the imported picture is back"), *Origin.ToString()), Shown(A), MaterialPath(OldSeq, OldFrame));
		T.TestTrue(*FString::Printf(TEXT("%s: at the imported card's size"), *Origin.ToString()),
			A->Card->GetRelativeScale3D().Equals(A->ImportedCardRelativeTransform.GetScale3D(), 1e-4));
		A->Destroy();
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkOverridePictureTest, "Dink.Gameplay.OverridePicture.RevisitShowsSavedPicture", DINK_TEST_FLAGS)
bool FDinkOverridePictureTest::RunTest(const FString& Parameters)
{
	using namespace DinkOverridePictureTest;
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	ON_SCOPE_EXIT
	{
		GI->Shutdown();
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
	};
	if (!TestTrue(TEXT("story and gameplay data load (Scripts/sync_story.py, Scripts/sync_gameplay_data.py)"), Story && Story->IsReady() && Story->GetGameplay() && Story->GetGameplay()->HasData()))
	{
		return false;
	}
	Story->StorySeed = 1997;
	Story->ResetRuntime();
	Story->bInstantMode = true;
	Story->GetGameplay()->Adaptation.bEnabled = false;
	Story->GetGameplay()->StartNewGame();
	Story->RunUntilIdle();
	// bar-sh.c `hit`: editor_type 3, editor_seq 173, editor_frame 6 (the barrel stays flat).
	Check(*this, Story, World, 60, 8, 3, 173, 6, 61);
	// ch1-ap.c `hit`: editor_type 4, editor_seq 175, editor_frame 4 (the chest stays open).
	Check(*this, Story, World, 536, 31, 4, 175, 4, 535);
	return true;
}
