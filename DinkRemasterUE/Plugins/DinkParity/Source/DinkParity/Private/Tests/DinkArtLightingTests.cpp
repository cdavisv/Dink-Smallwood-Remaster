#include "DinkTestHelpers.h"
#include "DinkArtSubsystem.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Components/PointLightComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/Light.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include <limits>

struct FDinkArtLightTestAccess
{
    static void Apply(UDinkArtSubsystem& Art, UWorld& World, const TSharedPtr<FJsonObject>& Manifest)
    { Art.ApplyManifest(World, Manifest, TEXT("LightingAutomation")); }
};

namespace
{
TArray<TSharedPtr<FJsonValue>> LightVector(FVector V)
{ return {MakeShared<FJsonValueNumber>(V.X), MakeShared<FJsonValueNumber>(V.Y), MakeShared<FJsonValueNumber>(V.Z)}; }
TSharedPtr<FJsonObject> LightRow(bool Rect = false)
{
    auto R = MakeShared<FJsonObject>();
    R->SetArrayField(TEXT("world_cm"), LightVector(FVector(100, 200, 185)));
    R->SetNumberField(TEXT("lumens"), 170);
    R->SetNumberField(TEXT("kelvin"), 5000);
    R->SetNumberField(TEXT("radius_cm"), 1000);
    if (Rect)
    {
        R->SetStringField(TEXT("kind"), TEXT("rect"));
        R->SetArrayField(TEXT("rotation_deg"), LightVector(FVector(0, 90, 0)));
        R->SetNumberField(TEXT("source_width_cm"), 80);
        R->SetNumberField(TEXT("source_height_cm"), 130);
    }
    return R;
}
TSharedPtr<FJsonObject> LightManifest(const TArray<TSharedPtr<FJsonValue>>& Lights)
{
    auto M = MakeShared<FJsonObject>();
    M->SetStringField(TEXT("schema"), TEXT("dink-art/1"));
    M->SetNumberField(TEXT("screen"), 1);
    M->SetArrayField(TEXT("lights"), Lights);
    return M;
}
struct FLightFixture
{
    UWorld* World;
    UDinkArtSubsystem* Art;
    ADinkGreyboxScreen* Screen;
    FLightFixture()
    {
        World = UWorld::CreateWorld(EWorldType::Game, false);
        GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
        Screen = World->SpawnActor<ADinkGreyboxScreen>(); Screen->ScreenNumber = 1;
        Art = NewObject<UDinkArtSubsystem>(World);
    }
    ~FLightFixture() { GEngine->DestroyWorldContext(World); World->DestroyWorld(false); }
    int32 Actors() const
    { int32 N = 0; for (TActorIterator<AActor> It(World); It; ++It) ++N; return N; }
    ALight* AuthoredLight() const
    {
        for (TActorIterator<ALight> It(World); It; ++It)
            if (It->ActorHasTag(TEXT("DinkAuthoredArt"))) return *It;
        return nullptr;
    }
};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAuthoredLightKinds, "Dink.Art.Lighting.LegacyPointAndRect", DINK_TEST_FLAGS)
bool FDinkAuthoredLightKinds::RunTest(const FString&)
{
    for (int32 Kind = 0; Kind != 3; ++Kind)
    {
        FLightFixture F;
        auto Row = LightRow(Kind == 2);
        if (Kind == 1) Row->SetStringField(TEXT("kind"), TEXT("point"));
        const int32 Before = F.Actors();
        FDinkArtLightTestAccess::Apply(*F.Art, *F.World, LightManifest({MakeShared<FJsonValueObject>(Row)}));
        TestEqual(TEXT("exactly one authored light actor"), F.Actors(), Before + 1);
        ALight* Light = F.AuthoredLight();
        if (!TestNotNull(TEXT("authored light exists"), Light)) return false;
        auto* C = Cast<ULocalLightComponent>(Light->GetLightComponent());
        if (!TestNotNull(TEXT("local light component"), C)) return false;
        TestTrue(TEXT("position retained"), Light->GetActorLocation().Equals(FVector(100, 200, 185)));
        TestTrue(TEXT("movable"), C->Mobility == EComponentMobility::Movable);
        TestTrue(TEXT("lumens units"), C->IntensityUnits == ELightUnits::Lumens);
        TestEqual(TEXT("lumens"), C->Intensity, 170.f);
        TestEqual(TEXT("temperature"), C->Temperature, 5000.f);
        TestTrue(TEXT("temperature enabled"), C->bUseTemperature != 0);
        TestEqual(TEXT("finite local attenuation"), C->AttenuationRadius, 1000.f);
        TestTrue(TEXT("shadows retained"), C->CastShadows && C->CastDynamicShadows);
        TestEqual(TEXT("normal indirect contribution"), C->IndirectLightingIntensity, 1.f);
        TestNull(TEXT("no original gameplay identity invented"), Light->FindComponentByClass<UDinkOriginComponent>());
        if (Kind == 2)
        {
            auto* Rect = Cast<URectLightComponent>(C);
            if (!TestNotNull(TEXT("actual rectangle component"), Rect)) return false;
            TestEqual(TEXT("source width"), Rect->SourceWidth, 80.f);
            TestEqual(TEXT("source height"), Rect->SourceHeight, 130.f);
            TestEqual(TEXT("no fictional barn-door extension"), Rect->BarnDoorLength, 0.f);
            TestTrue(TEXT("local +X emits toward authored +Y"), Light->GetActorForwardVector().Equals(FVector(0, 1, 0), 1e-6));
        }
        else
        {
            auto* Point = Cast<UPointLightComponent>(C);
            if (!TestNotNull(TEXT("omitted/explicit point retains point component"), Point)) return false;
            // Build an independent control using the exact old production setter sequence.
            auto* Control = F.World->SpawnActor<APointLight>(FVector(-10000, 0, 0), FRotator::ZeroRotator);
            auto* Old = CastChecked<UPointLightComponent>(Control->GetLightComponent());
            Old->SetMobility(EComponentMobility::Movable); Old->SetIntensityUnits(ELightUnits::Lumens);
            Old->SetIntensity(170.f); Old->SetUseTemperature(true); Old->SetTemperature(5000.f);
            Old->SetAttenuationRadius(1000.f); Old->SetSourceRadius(18.f);
            TestEqual(TEXT("legacy source sphere"), Point->SourceRadius, Old->SourceRadius);
            TestEqual(TEXT("legacy soft source"), Point->SoftSourceRadius, Old->SoftSourceRadius);
            TestEqual(TEXT("legacy source length"), Point->SourceLength, Old->SourceLength);
            TestEqual(TEXT("legacy falloff"), Point->LightFalloffExponent, Old->LightFalloffExponent);
            TestEqual(TEXT("legacy inverse exposure"), Point->InverseExposureBlend, Old->InverseExposureBlend);
            TestTrue(TEXT("legacy inverse-square"), Point->bUseInverseSquaredFalloff == Old->bUseInverseSquaredFalloff);
            TestTrue(TEXT("legacy color"), Point->LightColor == Old->LightColor);
            TestTrue(TEXT("legacy rotation unchanged"), Light->GetActorRotation().IsNearlyZero());
        }
    }
    FLightFixture Other;
    Other.Screen->ScreenNumber = 2;
    const int32 Before = Other.Actors();
    FDinkArtLightTestAccess::Apply(*Other.Art, *Other.World, LightManifest({MakeShared<FJsonValueObject>(LightRow(true))}));
    TestEqual(TEXT("no lights on unrelated world screen"), Other.Actors(), Before);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkAuthoredLightPreflight, "Dink.Art.Lighting.PreflightBeforeSceneMutation", DINK_TEST_FLAGS)
bool FDinkAuthoredLightPreflight::RunTest(const FString&)
{
    TArray<TSharedPtr<FJsonValue>> Bad;
    auto Add = [&Bad](TSharedPtr<FJsonObject> R) { Bad.Add(MakeShared<FJsonValueObject>(R)); };
    Bad.Add(MakeShared<FJsonValueString>(TEXT("not object")));
    { auto R = LightRow(); R->SetStringField(TEXT("kind"), TEXT("spot")); Add(R); }
    { auto R = LightRow(); R->SetNumberField(TEXT("kind"), 1); Add(R); }
    { auto R = LightRow(); R->SetStringField(TEXT("lumens"), TEXT("170")); Add(R); }
    { auto R = LightRow(); R->SetBoolField(TEXT("lumens"), true); Add(R); }
    for (double N : {-1., std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::infinity(), 1e300})
    { auto R = LightRow(); R->SetNumberField(TEXT("lumens"), N); Add(R); }
    for (const TCHAR* Key : {TEXT("radius_cm"), TEXT("kelvin")})
    { auto R = LightRow(); R->SetNumberField(Key, 0); Add(R); }
    { auto R = LightRow(); R->SetArrayField(TEXT("world_cm"), {}); Add(R); }
    { auto R = LightRow(); R->SetArrayField(TEXT("world_cm"), {MakeShared<FJsonValueBool>(true), MakeShared<FJsonValueNumber>(0), MakeShared<FJsonValueNumber>(0)}); Add(R); }
    { auto R = LightRow(); R->SetNumberField(TEXT("source_width_cm"), 80); Add(R); }
    { auto R = LightRow(true); R->RemoveField(TEXT("source_width_cm")); Add(R); }
    { auto R = LightRow(true); R->SetNumberField(TEXT("source_width_cm"), -80); Add(R); }
    { auto R = LightRow(true); R->SetNumberField(TEXT("source_height_cm"), 0); Add(R); }
    { auto R = LightRow(true); R->SetArrayField(TEXT("rotation_deg"), {}); Add(R); }
    for (const auto& Value : Bad)
    {
        FLightFixture F;
        auto* Existing = F.World->SpawnActor<ADinkPlaceholderActor>();
        Existing->Origin->OriginId = FDinkOriginId(1, 19);
        Existing->Card->SetRelativeLocation(FVector(11, 22, 33));
        const auto Transform = Existing->Card->GetRelativeTransform();
        const int32 Before = F.Actors();
        auto M = LightManifest({MakeShared<FJsonValueObject>(LightRow()), Value});
        auto Replacement = MakeShared<FJsonObject>();
        Replacement->SetStringField(TEXT("origin"), TEXT("S001_P19"));
        Replacement->SetStringField(TEXT("mesh"), TEXT("/Engine/BasicShapes/Cube.Cube"));
        M->SetArrayField(TEXT("replacements"), {MakeShared<FJsonValueObject>(Replacement)});
        M->SetArrayField(TEXT("hide_origins"), {MakeShared<FJsonValueString>(TEXT("S001_P19"))});
        M->SetArrayField(TEXT("hide_screen_visuals"), {MakeShared<FJsonValueNumber>(1)});
        AddExpectedMessage(TEXT("Art: invalid lights; retaining scene"), EAutomationExpectedMessageFlags::Contains, 1);
        FDinkArtLightTestAccess::Apply(*F.Art, *F.World, M);
        TestEqual(TEXT("all rows validated before first actor spawns"), F.Actors(), Before);
        TestNull(TEXT("replacement unchanged"), Existing->Card->GetStaticMesh());
        TestTrue(TEXT("replacement pose unchanged"), Existing->Card->GetRelativeTransform().Equals(Transform));
        TestFalse(TEXT("placement not hidden"), Existing->Card->bHiddenInGame);
        TestFalse(TEXT("screen not hidden"), F.Screen->Visual->bHiddenInGame);
        TestFalse(TEXT("placement not retagged"), Existing->ActorHasTag(TEXT("DinkAuthoredArt")));
    }
    FLightFixture F;
    auto Malformed = LightManifest({}); Malformed->SetStringField(TEXT("lights"), TEXT("not array"));
    const int32 Before = F.Actors();
    AddExpectedMessage(TEXT("Art: invalid lights; retaining scene"), EAutomationExpectedMessageFlags::Contains, 1);
    FDinkArtLightTestAccess::Apply(*F.Art, *F.World, Malformed);
    TestEqual(TEXT("malformed list rejected"), F.Actors(), Before);
    return true;
}
