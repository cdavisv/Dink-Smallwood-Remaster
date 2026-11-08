#include "DinkTestHelpers.h"
#include "DinkCreatureComponent.h"
#include "DinkCreatureSubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkOriginComponent.h"
#include "DinkScriptSpriteComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/BlendSpace.h"
#include "AssetCompilingManager.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPillbugPresentationTest,
    "Dink.Art.CreaturePresentation.OriginalPillbugVisionTouchDeathAndMixedFood", DINK_TEST_FLAGS)
bool FDinkPillbugPresentationTest::RunTest(const FString&)
{
    FString Text;
    TSharedPtr<FJsonObject> Manifest;
    if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/creatures.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest)
    { AddWarning(TEXT("skipped: creature manifest absent")); return true; }
    TMap<FString, TSharedPtr<FJsonObject>> Rows;
    for (const auto& Value : Manifest->GetArrayField(TEXT("placements")))
    {
        const auto Row = Value->AsObject();
        if (Row) Rows.Add(Row->GetStringField(TEXT("origin")), Row);
    }
    if (!Rows.Contains(TEXT("S438_P03")))
    { AddWarning(TEXT("skipped: pillbug art not imported")); return true; }
    for (const int32 Index : {2, 3, 4, 5, 6, 7})
        TestTrue(TEXT("all six original438 placements retained in mixed manifest"), Rows.Contains(FString::Printf(TEXT("S438_P%02d"), Index)));
    for (const int32 Index : {2, 5, 6, 7, 11})
        TestTrue(TEXT("all five existing pigs retained in mixed manifest"), Rows.Contains(FString::Printf(TEXT("S407_P%02d"), Index)));

    IConsoleVariable* Art = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));
    const int32 Previous = Art ? Art->GetInt() : 1;
    if (Art) Art->SetWithCurrentPriority(1);
    ON_SCOPE_EXIT { if (Art) Art->SetWithCurrentPriority(Previous); };
    UGameInstance* GI = NewObject<UGameInstance>(GEngine);
    GI->InitializeStandalone();
    UWorld* World = GI->GetWorld();
    ON_SCOPE_EXIT { GI->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false); };
    UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
    Story->bRunScreenScripts = false;
    Story->bNewGamePending = false;
    Story->bInstantMode = true;
    UDinkDirector* D = Story->GetDirector();
    UDinkGameplay* Game = Story->GetGameplay();
    Game->SetRandomSeed(1997);
    UDinkFactSubsystem* Facts = GI->GetSubsystem<UDinkFactSubsystem>();
    UDinkWorldStateSubsystem* State = GI->GetSubsystem<UDinkWorldStateSubsystem>();
    UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
    TArray<ADinkScreenVolume*> Rooms;
    for (const int32 Screen : {407, 438})
    {
        ADinkScreenVolume* Room = World->SpawnActor<ADinkScreenVolume>();
        Room->ScreenNumber = Screen;
        Room->Corners.NW = FVector2D(0, 0); Room->Corners.NE = FVector2D(6, 0);
        Room->Corners.SW = FVector2D(0, 4); Room->Corners.SE = FVector2D(6, 4);
        Greybox->RegisterScreen(Room); Rooms.Add(Room);
    }
    ON_SCOPE_EXIT { for (ADinkScreenVolume* Room : Rooms) Greybox->UnregisterScreen(Room); };
    TMap<int32, ADinkPlaceholderActor*> Bugs;
    TMap<int32, int32> Handles;
    for (const int32 Index : {2, 3, 4, 5, 6, 7})
    {
        ADinkPlaceholderActor* Actor = World->SpawnActor<ADinkPlaceholderActor>();
        Actor->Origin->OriginId = FDinkOriginId(438, Index);
        const bool Normal = Index == 3 || Index == 4 || Index == 7;
        Actor->Origin->ScriptName = Normal ? FName(TEXT("en-pill")) : NAME_None;
        Actor->ScreenNumber = 438; Actor->Brain = 9; Actor->Vision = Normal ? 0 : 1;
        Actor->GetRootComponent()->SetMobility(EComponentMobility::Movable);
        Actor->SetActorLocation(FVector(Index * 1000, 1000, 0));
        Actor->ApplyScreenVision(0);
        Bugs.Add(Index, Actor);
        const int32 Handle = D->HandleForActor(Actor);
        Handles.Add(Index, Handle);
        const FDinkSprite* Raw = D->FindSprite(Handle);
        TestEqual(TEXT("raw original brain9"), Raw->GetProp(TEXT("brain")), 9);
        TestEqual(TEXT("raw original size100"), Raw->GetProp(TEXT("size")), 100);
        TestEqual(TEXT("raw original HP20 before script"), Raw->GetProp(TEXT("hitpoints")), 20);
        TestEqual(TEXT("raw original touch2 before script"), Raw->GetProp(TEXT("touch_damage")), 2);
        TestEqual(TEXT("raw original speed1"), Raw->GetProp(TEXT("speed")), 1);
        TestEqual(TEXT("raw original timing0"), Raw->GetProp(TEXT("timing")), 0);
        TestEqual(TEXT("raw original no attack sequence"), Raw->GetProp(TEXT("base_attack")), -1);
        if (Normal) { Story->StartProcedure(TEXT("en-pill"), TEXT("main"), Handle); Story->RunUntilIdle(); }
    }
    // Existing pig actors must be present so the real adapter encounters feeding rows before nonfeeding rows.
    for (const int32 Index : {2, 5, 6, 7, 11})
    {
        ADinkPlaceholderActor* Pig = World->SpawnActor<ADinkPlaceholderActor>();
        Pig->Origin->OriginId = FDinkOriginId(407, Index);
        Pig->Origin->ScriptName = TEXT("die"); Pig->Brain = 4;
    }
    UDinkCreatureSubsystem* Creatures = World->GetSubsystem<UDinkCreatureSubsystem>();
    Creatures->OnWorldBeginPlay(*World);
    FAssetCompilingManager::Get().FinishAllCompilation();
    for (const int32 Index : {2, 3, 4, 5, 6, 7})
    {
        ADinkPlaceholderActor* Actor = Bugs[Index];
        const FDinkSprite* Sprite = D->FindSprite(Handles[Index]);
        const bool Normal = Actor->Vision == 0;
        UDinkCreatureComponent* Creature = Actor->FindComponentByClass<UDinkCreatureComponent>();
        if (!TestNotNull(TEXT("same original actor receives pillbug animation"), Creature)) continue;
        USkeletalMesh* Mesh = Creature->GetSkeletalMeshAsset();
        TestTrue(TEXT("actual own43bone rig loaded"), Mesh && Mesh->GetRefSkeleton().GetNum() == 43);
        TestTrue(TEXT("source card replaced only after valid art"), Actor->Card->bHiddenInGame);
        TestTrue(TEXT("origin and script actor preserved"), Sprite->Actor.Get() == Actor && Sprite->Origin == FDinkOriginId(438, Index));
        TestEqual(TEXT("brain9 preserved"), Sprite->GetProp(TEXT("brain")), 9);
        TestEqual(TEXT("original normal/variant HP preserved"), Sprite->GetProp(TEXT("hitpoints")), Normal ? 8 : 20);
        TestEqual(TEXT("original normal/variant touch preserved"), Sprite->GetProp(TEXT("touch_damage")), Normal ? 1 : 2);
        TestEqual(TEXT("original normal/variant exp preserved"), Sprite->GetProp(TEXT("exp")), Normal ? 5 : 0);
        TestEqual(TEXT("original script identity retained"), Sprite->Script, Normal ? FName(TEXT("en-pill")) : NAME_None);
        TestEqual(TEXT("original walk130 retained"), Sprite->GetProp(TEXT("base_walk")), 130);
        TestEqual(TEXT("original death140 retained without invented delay"), Sprite->GetProp(TEXT("base_death")), 140);
        TestEqual(TEXT("art preserves actor vision hiding"), Actor->IsHidden(), !Normal);
        TestEqual(TEXT("art preserves vision collision gating"), Actor->GetActorEnableCollision(), Normal);
        const auto Row = Rows.FindRef(Actor->Origin->OriginId.ToString());
        FString Feed;
        TestTrue(TEXT("pillbug has no invented feed animation"), Row && (!Row->TryGetStringField(TEXT("feed_animation"), Feed) || Feed.IsEmpty()));
        TestFalse(TEXT("nonfeeding pillbug cannot enter feed state"), Creature->IsFeeding());
        bool Proxy = false;
        TInlineComponentArray<UBoxComponent*> Bodies(Actor);
        for (const UBoxComponent* Body : Bodies)
            Proxy |= Body->ComponentHasTag(TEXT("DinkAuthoredInteraction")) && Body->IsRegistered() && Body->bHiddenInGame && Body->GetScaledBoxExtent().X > Body->GetScaledBoxExtent().Z;
        TestTrue(TEXT("low horizontal body has real hidden interaction geometry"), Proxy);
    }
    APawn* Pawn = World->SpawnActor<APawn>();
    UCapsuleComponent* Body = NewObject<UCapsuleComponent>(Pawn);
    Pawn->SetRootComponent(Body); Body->InitCapsuleSize(28, 96);
    Body->SetCollisionProfileName(TEXT("Pawn")); Body->RegisterComponent();
    D->GetDink().Actor = Pawn; D->GetDink().Screen = 438;
    ADinkPlaceholderActor* Target = Bugs[3];
    UBoxComponent* Surface = nullptr;
    TInlineComponentArray<UBoxComponent*> Bodies(Target);
    for (UBoxComponent* Box : Bodies) if (Box->ComponentHasTag(TEXT("DinkAuthoredInteraction"))) { Surface = Box; break; }
    if (!TestNotNull(TEXT("actual pillbug collision edge available"), Surface)) return false;
    Surface->UpdateBounds();
    const FBox Bounds = Surface->Bounds.GetBox();
    const FVector Near(Bounds.Max.X + 27, Bounds.GetCenter().Y, 98);
    D->GetDink().X = D->FindSprite(Handles[3])->X; D->GetDink().Y = D->FindSprite(Handles[3])->Y;
    Facts->SetFact(TEXT("life"), 10); Facts->SetFact(TEXT("defense"), 0); Facts->SetFact(TEXT("strength"), 4); Facts->SetFact(TEXT("exp"), 0);
    Pawn->SetActorLocation(Near + FVector(500, 0, 0));
    Game->RunThroughTouchDamageList(1); Game->ProcessDamage();
    TestEqual(TEXT("legacy pixel overlap cannot damage from far physical edge"), Facts->GetFact(TEXT("life")), 10);
    Pawn->SetActorLocation(Near);
    Game->RunThroughTouchDamageList(1); Game->ProcessDamage();
    TestEqual(TEXT("contact with actual pillbug body deals original touch1"), Facts->GetFact(TEXT("life")), 9);
    Game->RunThroughTouchDamageList(1); Game->ProcessDamage();
    TestEqual(TEXT("original contact immunity prevents immediate repeat"), Facts->GetFact(TEXT("life")), 9);
    Pawn->SetActorRotation(FRotator(0, 180, 0)); D->GetDink().Dir = 4;
    Game->RunThroughTagList(1);
    TestEqual(TEXT("physical fist hit queues rather than immediately applies damage"), D->FindSprite(Handles[3])->GetProp(TEXT("hitpoints")), 8);
    TestTrue(TEXT("actual geometry hit queued pillbug damage"), D->FindSprite(Handles[3])->Damage > 0);
    Game->ProcessDamage(); Story->RunUntilIdle();
    TestTrue(TEXT("original brain9 damage path reducesHP while alive"), D->FindSprite(Handles[3])->GetProp(TEXT("hitpoints")) < 8 && D->FindSprite(Handles[3])->bActive);
    Game->HurtThing(Handles[3], 100); Game->ProcessDamage(); Story->RunUntilIdle();
    TestFalse(TEXT("original death immediately deactivates creature"), D->FindSprite(Handles[3])->bActive);
    TestTrue(TEXT("dead authored actor hidden"), Target->IsHidden());
    TestFalse(TEXT("dead collision proxies cannot leave invisible blocker"), Target->GetActorEnableCollision());
    TestEqual(TEXT("original death writes editor_type6"), State->GetOverrideType(FDinkOriginId(438, 3)), EDinkOverrideType::RemovedReturn5Min);
    TestEqual(TEXT("original player kill awards5exp"), Facts->GetFact(TEXT("exp")), 5);
    const auto Saved = D->SaveState();
    D->FindSprite(Handles[3])->bActive = true; Target->SetActorHiddenInGame(false); Target->SetActorEnableCollision(true);
    D->LoadState(Saved);
    TestTrue(TEXT("saved dead original actor remains hidden"), Target->IsHidden());
    TestFalse(TEXT("saved dead original proxy remains disabled"), Target->GetActorEnableCollision());
    TestEqual(TEXT("death override still timed not permanent"), State->GetOverrideType(FDinkOriginId(438, 3)), EDinkOverrideType::RemovedReturn5Min);
    for (const int32 Index : {2, 5, 6})
    {
        TestTrue(TEXT("save preserves inactive-vision authored actor hiding"), Bugs[Index]->IsHidden());
        TestFalse(TEXT("save preserves inactive-vision authored proxy gating"), Bugs[Index]->GetActorEnableCollision());
        TestEqual(TEXT("save preserves raw variantHP20"), D->FindSprite(Handles[Index])->GetProp(TEXT("hitpoints")), 20);
    }

    FDinkScriptInstance Caller; Caller.Id = 900001; Caller.Sprite = 1; Caller.Screen = 407;
    D->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> create_sprite 320 200 6 430 1"), {TEXT("cmd"), TEXT("src:1")}));
    UStaticMeshComponent* Grain = nullptr;
    for (const auto& Pair : D->GetSprites())
    {
        AActor* Actor = Pair.Value.Actor.Get();
        if (!Pair.Value.bSpawned || !Actor) continue;
        TInlineComponentArray<UStaticMeshComponent*> Meshes(Actor);
        for (UStaticMeshComponent* Mesh : Meshes) if (Mesh->ComponentHasTag(TEXT("DinkAuthoredFood"))) Grain = Mesh;
    }
    if (TestNotNull(TEXT("actual spawned grain retains mixed-manifest adapter"), Grain))
    {
        Grain->UpdateBounds();
        TestTrue(TEXT("nonfeeding rows cannot reset grain bottom0.6cm"), FMath::IsNearlyEqual(Grain->Bounds.GetBox().Min.Z, .6, .02));
        TestTrue(TEXT("legacy dynamic grain actor remainsZ60"), FMath::IsNearlyEqual(Grain->GetOwner()->GetActorLocation().Z, 60., .02));
    }
    return true;
}
