#include "DinkTestHelpers.h"
#include "DinkArtSubsystem.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "AssetCompilingManager.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"

// Exercises the same in-memory manifest path as the file reader, without writing Data.
struct FDinkArtNavigationTestAccess
{
    static void Apply(UDinkArtSubsystem& Art, UWorld& World, const TSharedPtr<FJsonObject>& Manifest)
    {
        Art.ApplyManifest(World, Manifest, TEXT("NavigationAutomation"));
    }
};

namespace
{
constexpr const TCHAR* CubePath = TEXT("/Engine/BasicShapes/Cube.Cube");
TArray<TSharedPtr<FJsonValue>> Vector(FVector V)
{
    return {MakeShared<FJsonValueNumber>(V.X), MakeShared<FJsonValueNumber>(V.Y), MakeShared<FJsonValueNumber>(V.Z)};
}
TSharedPtr<FJsonObject> Element(FVector Position)
{
    auto Row = MakeShared<FJsonObject>();
    Row->SetStringField(TEXT("mesh"), CubePath);
    Row->SetArrayField(TEXT("world_cm"), Vector(Position));
    Row->SetArrayField(TEXT("rotation_deg"), Vector(FVector(0, 25, 0)));
    Row->SetArrayField(TEXT("scale"), Vector(FVector(2, 3, 1)));
    Row->SetBoolField(TEXT("camera_occluder"), true);
    return Row;
}
TSharedPtr<FJsonObject> Manifest(const TArray<TSharedPtr<FJsonValue>>& Elements)
{
    auto Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("schema"), TEXT("dink-art/1"));
    Root->SetNumberField(TEXT("screen"), 1);
    Root->SetArrayField(TEXT("elements"), Elements);
    return Root;
}
struct FFixture
{
    UWorld* World;
    UDinkArtSubsystem* Art;
    ADinkGreyboxScreen* Screen;
    UStaticMesh* Cube;
    FFixture()
    {
        Cube = LoadObject<UStaticMesh>(nullptr, CubePath);
        FAssetCompilingManager::Get().FinishAllCompilation();
        World = UWorld::CreateWorld(EWorldType::Game, false);
        GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
        Screen = World->SpawnActor<ADinkGreyboxScreen>();
        Screen->ScreenNumber = 1;
        Art = NewObject<UDinkArtSubsystem>(World);
    }
    ~FFixture() { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); }
    int32 CountActors() const
    {
        int32 Count = 0;
        for (TActorIterator<AActor> It(World); It; ++It) ++Count;
        return Count;
    }
    AStaticMeshActor* Authored() const
    {
        for (TActorIterator<AStaticMeshActor> It(World); It; ++It)
            if (It->ActorHasTag(TEXT("DinkAuthoredArt"))) return *It;
        return nullptr;
    }
};

}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkArtNavigationPolicy, "Dink.Art.Navigation.OptionalPolicy", DINK_TEST_FLAGS)
bool FDinkArtNavigationPolicy::RunTest(const FString&)
{
    const TOptional<bool> Policies[] = {TOptional<bool>(), false, true};
    for (const TOptional<bool>& Policy : Policies)
    {
        FFixture F;
        if (!TestNotNull(TEXT("engine cube available"), F.Cube)) return false;
        // Observe the actual legacy spawn result, rather than assuming a runtime
        // edit to a CDO subobject is inherited by a newly constructed component.
        AStaticMeshActor* Legacy = F.World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),
            FTransform(FVector(-10000, 0, 0)));
        UStaticMeshComponent* LegacyMesh = Legacy->GetStaticMeshComponent();
        LegacyMesh->SetStaticMesh(F.Cube);
        LegacyMesh->SetCollisionProfileName(TEXT("BlockAll"));
        LegacyMesh->SetGenerateOverlapEvents(false);
        const bool ExpectedNavigation = Policy.Get(LegacyMesh->CanEverAffectNavigation());
        auto Row = Element(FVector(200, 400, 350));
        if (Policy.IsSet()) Row->SetBoolField(TEXT("can_affect_navigation"), Policy.GetValue());
        auto Root = Manifest({MakeShared<FJsonValueObject>(Row)});
        // The optional element field must not start controlling replacement cards.
        ADinkPlaceholderActor* Existing = F.World->SpawnActor<ADinkPlaceholderActor>();
        Existing->Origin->OriginId = FDinkOriginId(1, 19);
        Existing->Card->SetCollisionProfileName(TEXT("BlockAll"));
        const auto Responses = Existing->Card->GetCollisionResponseToChannels();
        auto Replacement = MakeShared<FJsonObject>();
        Replacement->SetStringField(TEXT("origin"), TEXT("S001_P19"));
        Replacement->SetStringField(TEXT("mesh"), CubePath);
        Replacement->SetBoolField(TEXT("can_affect_navigation"), true);
        Root->SetArrayField(TEXT("replacements"), {MakeShared<FJsonValueObject>(Replacement)});
        FDinkArtNavigationTestAccess::Apply(*F.Art, *F.World, Root);
        AStaticMeshActor* A = F.Authored();
        if (!TestNotNull(TEXT("physical element spawned"), A)) continue;
        UStaticMeshComponent* M = A->GetStaticMeshComponent();
        AddInfo(FString::Printf(TEXT("Navigation policy present=%d value=%d legacy=%d actual=%d"), Policy.IsSet(), Policy.Get(false), LegacyMesh->CanEverAffectNavigation(), M->CanEverAffectNavigation()));
        TestEqual(TEXT("optional policy respects inherited/default or explicit value"), M->CanEverAffectNavigation(), ExpectedNavigation);
        TestTrue(TEXT("same selected mesh"), M->GetStaticMesh() == F.Cube);
        TestTrue(TEXT("world placement preserved"), A->GetActorLocation().Equals(FVector(200, 400, 350)));
        TestTrue(TEXT("rotation preserved"), A->GetActorRotation().Equals(FRotator(0, 25, 0)));
        TestTrue(TEXT("scale preserved"), A->GetActorScale3D().Equals(FVector(2, 3, 1)));
        TestEqual(TEXT("collision profile remains BlockAll"), M->GetCollisionProfileName(), FName(TEXT("BlockAll")));
        TestEqual(TEXT("query and physics retained"), M->GetCollisionEnabled(), ECollisionEnabled::QueryAndPhysics);
        TestTrue(TEXT("all collision channel responses retained"), M->GetCollisionResponseToChannels() == LegacyMesh->GetCollisionResponseToChannels());
        TestEqual(TEXT("camera still blocked"), M->GetCollisionResponseToChannel(ECC_Camera), ECR_Block);
        TestEqual(TEXT("pawn still blocked"), M->GetCollisionResponseToChannel(ECC_Pawn), ECR_Block);
        TestFalse(TEXT("overlap events remain disabled"), M->GetGenerateOverlapEvents());
        TestTrue(TEXT("camera tag retained"), A->ActorHasTag(TEXT("DinkCameraOccluder")));
        TestTrue(TEXT("screen tag retained"), A->ActorHasTag(TEXT("DinkArtScreen_1")));
        TestTrue(TEXT("component remains registered"), M->IsRegistered());
        if (!ExpectedNavigation) TestFalse(TEXT("disabled component not navigation relevant"), M->IsNavigationRelevant());
        TestFalse(TEXT("replacement card navigation unchanged"), Existing->Card->CanEverAffectNavigation());
        TestFalse(TEXT("replacement overlap unchanged"), Existing->Card->GetGenerateOverlapEvents());
        TestTrue(TEXT("replacement responses unchanged"), Existing->Card->GetCollisionResponseToChannels() == Responses);
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkArtNavigationAtomic, "Dink.Art.Navigation.InvalidIsAtomic", DINK_TEST_FLAGS)
bool FDinkArtNavigationAtomic::RunTest(const FString&)
{
    const TArray<TSharedPtr<FJsonValue>> Invalid = {
        MakeShared<FJsonValueString>(TEXT("false")), MakeShared<FJsonValueString>(TEXT("true")),
        MakeShared<FJsonValueNumber>(0), MakeShared<FJsonValueNumber>(1), MakeShared<FJsonValueNull>(),
        MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{}), MakeShared<FJsonValueObject>(MakeShared<FJsonObject>())};
    for (const auto& Value : Invalid)
    {
        FFixture F;
        ADinkPlaceholderActor* Existing = F.World->SpawnActor<ADinkPlaceholderActor>();
        Existing->Origin->OriginId = FDinkOriginId(1, 19);
        Existing->Card->SetRelativeLocation(FVector(11, 22, 33));
        const FTransform Before = Existing->Card->GetRelativeTransform();
        const auto Profile = Existing->Card->GetCollisionProfileName();
        const auto Responses = Existing->Card->GetCollisionResponseToChannels();
        const int32 Count = F.CountActors();
        auto First = Element(FVector(200, 0, 350));
        First->SetBoolField(TEXT("can_affect_navigation"), false);
        auto Bad = Element(FVector(400, 0, 350));
        Bad->SetField(TEXT("can_affect_navigation"), Value);
        auto Root = Manifest({MakeShared<FJsonValueObject>(First), MakeShared<FJsonValueObject>(Bad)});
        auto Replacement = MakeShared<FJsonObject>();
        Replacement->SetStringField(TEXT("origin"), TEXT("S001_P19"));
        Replacement->SetStringField(TEXT("mesh"), CubePath);
        Replacement->SetArrayField(TEXT("offset_cm"), Vector(FVector(100, 200, 300)));
        Root->SetArrayField(TEXT("replacements"), {MakeShared<FJsonValueObject>(Replacement)});
        Root->SetArrayField(TEXT("hide_origins"), {MakeShared<FJsonValueString>(TEXT("S001_P19"))});
        Root->SetArrayField(TEXT("hide_screen_visuals"), {MakeShared<FJsonValueNumber>(1)});
        AddExpectedMessage(TEXT("Art: can_affect_navigation must be a boolean; retaining scene"), EAutomationExpectedMessageFlags::Contains, 1);
        FDinkArtNavigationTestAccess::Apply(*F.Art, *F.World, Root);
        TestEqual(TEXT("no earlier element or later actors spawned"), F.CountActors(), Count);
        TestNull(TEXT("no authored element admitted"), F.Authored());
        TestNull(TEXT("replacement mesh was not changed"), Existing->Card->GetStaticMesh());
        TestTrue(TEXT("replacement transform not changed"), Existing->Card->GetRelativeTransform().Equals(Before));
        TestEqual(TEXT("replacement profile not changed"), Existing->Card->GetCollisionProfileName(), Profile);
        TestTrue(TEXT("replacement channel responses not changed"), Existing->Card->GetCollisionResponseToChannels() == Responses);
        TestFalse(TEXT("replacement navigation remains disabled"), Existing->Card->CanEverAffectNavigation());
        TestFalse(TEXT("replacement overlap remains disabled"), Existing->Card->GetGenerateOverlapEvents());
        TestFalse(TEXT("replacement not hidden"), Existing->Card->bHiddenInGame);
        TestFalse(TEXT("screen not hidden"), F.Screen->Visual->bHiddenInGame);
        TestFalse(TEXT("replacement not tagged"), Existing->ActorHasTag(TEXT("DinkAuthoredArt")));
    }
    return true;
}
