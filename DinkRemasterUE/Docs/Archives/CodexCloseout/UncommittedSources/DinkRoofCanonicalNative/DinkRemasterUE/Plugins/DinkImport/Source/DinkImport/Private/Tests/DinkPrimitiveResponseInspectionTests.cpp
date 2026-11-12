#include "DinkMaterialArtLibrary.h"
#include "Components/BoxComponent.h"
#include "Misc/AutomationTest.h"
#include "UObject/Package.h"

#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkPrimitiveResponseInspectionTest,
    "Dink.Import.Inspection.PrimitiveCollisionResponses",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDinkPrimitiveResponseInspectionTest::RunTest(const FString&)
{
    TestEqual(TEXT("null component has no inferred responses"),
        UDinkMaterialArtLibrary::InspectPrimitiveCollisionResponses(nullptr).Num(), 0);
    UPackage* Package = CreatePackage(TEXT("/Game/DinkQA/TransientPrimitiveResponsesInspection"));
    UBoxComponent* Component = NewObject<UBoxComponent>(Package, NAME_None, RF_Transient);
    Component->SetCollisionProfileName(TEXT("BlockAll"));
    Component->SetCanEverAffectNavigation(false);
    Component->SetGenerateOverlapEvents(false);
    for (int32 Index = 0; Index < 64; ++Index)
        Component->SetCollisionResponseToChannel(static_cast<ECollisionChannel>(Index), static_cast<ECollisionResponse>(Index % 3));
    Component->SetCollisionResponseToChannel(ECC_GameTraceChannel50, ECR_Overlap);
    const FCollisionResponseContainer Before = Component->GetCollisionResponseToChannels();
    const auto Profile = Component->GetCollisionProfileName();
    const auto ObjectType = Component->GetCollisionObjectType();
    const auto Enabled = Component->GetCollisionEnabled();
    const auto Transform = Component->GetComponentTransform();
    const bool Dirty = Package->IsDirty();
    TArray<int32> Snapshot = UDinkMaterialArtLibrary::InspectPrimitiveCollisionResponses(Component);
    if (!TestEqual(TEXT("exact64 serialized live responses returned"), Snapshot.Num(), 64)) return false;
    for (int32 Index = 0; Index < 64; ++Index)
        TestEqual(FString::Printf(TEXT("live channel%d is queried, not profile-derived"), Index),
            Snapshot[Index], static_cast<int32>(Before.GetResponse(static_cast<ECollisionChannel>(Index))));
    TestEqual(TEXT("highest hidden channel is included"), Snapshot[static_cast<int32>(ECC_GameTraceChannel50)], static_cast<int32>(ECR_Overlap));
    Snapshot[static_cast<int32>(ECC_GameTraceChannel50)] = static_cast<int32>(ECR_Block);
    TestEqual(TEXT("returned values are detached from component state"),
        UDinkMaterialArtLibrary::InspectPrimitiveCollisionResponses(Component)[static_cast<int32>(ECC_GameTraceChannel50)], static_cast<int32>(ECR_Overlap));
    TestTrue(TEXT("inspection preserves all64 responses"), Component->GetCollisionResponseToChannels() == Before);
    TestEqual(TEXT("inspection preserves profile"), Component->GetCollisionProfileName(), Profile);
    TestEqual(TEXT("inspection preserves object type"), Component->GetCollisionObjectType(), ObjectType);
    TestEqual(TEXT("inspection preserves enabled state"), Component->GetCollisionEnabled(), Enabled);
    TestTrue(TEXT("inspection preserves transform"), Component->GetComponentTransform().Equals(Transform));
    TestFalse(TEXT("inspection preserves navigation false"), Component->CanEverAffectNavigation());
    TestFalse(TEXT("inspection preserves overlap false"), Component->GetGenerateOverlapEvents());
    TestEqual(TEXT("inspection does not dirty package"), Package->IsDirty(), Dirty);
    return true;
}
#endif
