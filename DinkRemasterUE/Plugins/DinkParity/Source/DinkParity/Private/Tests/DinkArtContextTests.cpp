#include "DinkInteriorCameraComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "AssetCompilingManager.h"
#include "Components/StaticMeshComponent.h"
#include "DinkArtContextActor.h"
#include "DinkOriginComponent.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "DinkTestHelpers.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/StaticMesh.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"
#include <limits>
namespace
{
TSharedPtr<FJsonObject> Spec(int32 Owner, const FVector &Position, const FString &Mesh)
{
    auto M = MakeShared<FJsonObject>(), C = MakeShared<FJsonObject>(), R = MakeShared<FJsonObject>();
    M->SetStringField(TEXT("schema"), TEXT("dink-art/1"));
    M->SetNumberField(TEXT("screen"), Owner);
    C->SetStringField(TEXT("visibility"), TEXT("owner_screen_only"));
    C->SetBoolField(TEXT("render_only"), true);
    M->SetObjectField(TEXT("context"), C);
    R->SetStringField(TEXT("mesh"), Mesh);
    R->SetBoolField(TEXT("collision"), false);
    R->SetBoolField(TEXT("camera_occluder"), false);
    auto V = [](FVector X)
    {
        return TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(X.X), MakeShared<FJsonValueNumber>(X.Y),
                                              MakeShared<FJsonValueNumber>(X.Z)};
    };
    R->SetArrayField(TEXT("world_cm"), V(Position));
    R->SetArrayField(TEXT("rotation_deg"), V(FVector::ZeroVector));
    R->SetArrayField(TEXT("scale"), V(FVector::OneVector));
    M->SetArrayField(TEXT("elements"), {MakeShared<FJsonValueObject>(R)});
    return M;
}
struct FOriginal
{
    UStaticMeshComponent *M;
    FTransform Transform;
    FCollisionResponseContainer Responses;
    ECollisionEnabled::Type Enabled;
    bool Hidden, Visible;
    AActor *Owner;
    USceneComponent *Parent;
    TArray<TObjectPtr<UMaterialInterface>> Overrides, Materials;
    explicit FOriginal(UStaticMeshComponent *X)
        : M(X), Transform(X->GetComponentTransform()), Responses(X->GetCollisionResponseToChannels()),
          Enabled(X->GetCollisionEnabled()), Hidden(X->GetOwner()->IsHidden()), Visible(X->IsVisible()),
          Owner(X->GetOwner()), Parent(X->GetAttachParent()), Overrides(X->OverrideMaterials)
    {
        for (int32 I = 0; I < X->GetNumMaterials(); ++I)
            Materials.Add(X->GetMaterial(I));
    }
};
class FContextPIE : public IAutomationLatentCommand
{
    FAutomationTestBase *T;
    int Phase = 0;
    double Start = 0, At = 0, LastDiagnostic = 0;
    ADinkScreenVolume *Home = nullptr, *Other = nullptr, *Yard = nullptr;
    ADinkArtContextActor *C = nullptr, *C2 = nullptr, *Early = nullptr;
    AStaticMeshActor *Ordinary = nullptr;
    UStaticMesh *Cube = nullptr;
    TMap<FString, UStaticMesh *> Meshes;
    TArray<FOriginal> Originals;
    FVector ExpectedContextPosition;
    ADinkArtContextActor* RuntimeContext=nullptr;
    TArray<TSharedPtr<FJsonValue>> RuntimeRows;
    int32 BaselineContextCount=0;
    bool HasRuntimeManifest=false;
    void Move(ADinkGreyboxCharacter *H, UDinkGreyboxSubsystem *G, ADinkScreenVolume *S)
    {
        H->GetCharacterMovement()->StopMovementImmediately();
        H->SetActorLocation(S->MapPixelToWorld(S == Home ? 303.5 : 300, S == Home ? 345 : 200) + FVector(0, 0, 98),
                            false, nullptr, ETeleportType::TeleportPhysics);
        G->RefreshCurrentScreen();
    }
    int Count(UWorld &W)
    {
        int N = 0;
        for (TActorIterator<ADinkArtContextActor> I(&W); I; ++I)
            if (!I->IsActorBeingDestroyed())
                ++N;
        return N;
    }
    void Rejections(UWorld &W, FVector P)
    {
        int Before = Count(W);
        auto Reject = [&](const TSharedPtr<FJsonObject> &M)
        {
            T->TestNull(TEXT("invalid context rejected by production factory"),
                        ADinkArtContextActor::CreateFromManifest(W, M, Meshes, 1));
            T->TestEqual(TEXT("rejected context never mutates scene"), Count(W), Before);
        };
        for (const TCHAR *K : {TEXT("replacements"), TEXT("warp_overrides"), TEXT("hide_origins"),
                               TEXT("hide_screen_visuals"), TEXT("authored_collision_screens"),
                               TEXT("preserve_low_collision_screens"), TEXT("lights"), TEXT("postprocess")})
        {
            auto M = Spec(1, P, Cube->GetPathName());
            M->SetArrayField(K, {});
            Reject(M);
        }
        for (const TCHAR *K : {TEXT("collision"), TEXT("camera_occluder")})
        {
            auto M = Spec(1, P, Cube->GetPathName());
            M->GetArrayField(TEXT("elements"))[0]->AsObject()->SetBoolField(K, true);
            Reject(M);
        }
        Reject(Spec(1, P, TEXT("unknown")));
        Reject(Spec(2, P, Cube->GetPathName()));
        Reject(Spec(1, FVector(std::numeric_limits<double>::quiet_NaN(), 0, 0), Cube->GetPathName()));
        auto M = Spec(1, P, Cube->GetPathName());
        M->GetObjectField(TEXT("context"))->SetStringField(TEXT("visibility"), TEXT("always"));
        Reject(M);
        M = Spec(1, P, Cube->GetPathName());
        M->SetArrayField(TEXT("elements"), {MakeShared<FJsonValueString>(TEXT("not object"))});
        Reject(M);
    }
    void Physical()
    {
        T->TestFalse(TEXT("context has no actor tick"), C->PrimaryActorTick.bCanEverTick);
        T->TestFalse(TEXT("context actor has no collision"), C->GetActorEnableCollision());
        T->TestFalse(TEXT("context never joins camera occluders"), C->ActorHasTag(TEXT("DinkCameraOccluder")));
        TInlineComponentArray<UStaticMeshComponent *> Ms(C);
        T->TestEqual(TEXT("fixture owns exactly one primitive"), Ms.Num(), 1);
        for (auto M : Ms)
        {
            T->TestTrue(TEXT("manifest world placement retained"), M->GetComponentLocation().Equals(ExpectedContextPosition, .001));
            T->TestEqual(TEXT("shared mesh reference retained without replacement"), M->GetStaticMesh().Get(), Cube);
            T->TestFalse(TEXT("no mesh tick"), M->PrimaryComponentTick.bCanEverTick);
            T->TestEqual(TEXT("NoCollision primitive"), M->GetCollisionEnabled(), ECollisionEnabled::NoCollision);
            T->TestFalse(TEXT("no overlaps"), M->GetGenerateOverlapEvents());
            T->TestFalse(TEXT("no navigation"), M->CanEverAffectNavigation());
            T->TestFalse(TEXT("no hidden shadow"), M->bCastHiddenShadow);
            T->TestFalse(TEXT("no hidden GI"), M->bAffectIndirectLightingWhileHidden);
            FHitResult Hit;
            C->GetWorld()->LineTraceSingleByChannel(Hit, M->Bounds.Origin + FVector(0, 0, 100),
                                                    M->Bounds.Origin - FVector(0, 0, 100), ECC_Visibility);
            T->TestTrue(TEXT("actual world trace ignores render-only context"), Hit.GetActor() != C);
        }
    }
    void CheckRuntime(bool ExpectedVisible)
    {
        if (!HasRuntimeManifest) return;
        if (!T->TestNotNull(TEXT("published private real-manifest context exists"),RuntimeContext)) return;
        T->TestEqual(TEXT("real context owner screen remains1"),RuntimeContext->GetOwnerScreenNumber(),1);
        T->TestEqual(TEXT("real359 context visibility follows current owner"),RuntimeContext->IsHidden(),!ExpectedVisible);
        T->TestFalse(TEXT("real context never ticks"),RuntimeContext->PrimaryActorTick.bCanEverTick);
        T->TestFalse(TEXT("real context actor has no collision"),RuntimeContext->GetActorEnableCollision());
        T->TestNull(TEXT("cosmetic context has no original save/script identity"),RuntimeContext->FindComponentByClass<UDinkOriginComponent>());
        T->TestFalse(TEXT("real context never joins camera occluders"),RuntimeContext->ActorHasTag(TEXT("DinkCameraOccluder")));
        TInlineComponentArray<UStaticMeshComponent*> Components(RuntimeContext);
        T->TestEqual(TEXT("actual manifest creates359 components"),Components.Num(),359);
        T->TestEqual(TEXT("actual fixture has359 source rows"),RuntimeRows.Num(),359);
        TSet<UStaticMesh*> Assets;TArray<bool> Matched;Matched.Init(false,RuntimeRows.Num());
        for (auto M:Components)
        {
            Assets.Add(M->GetStaticMesh());
            T->TestFalse(TEXT("all359 components have no ticks"),M->PrimaryComponentTick.bCanEverTick);
            T->TestEqual(TEXT("all359 components are NoCollision"),M->GetCollisionEnabled(),ECollisionEnabled::NoCollision);
            T->TestFalse(TEXT("all359 have no overlap events"),M->GetGenerateOverlapEvents());
            T->TestFalse(TEXT("all359 have no navigation influence"),M->CanEverAffectNavigation());
            T->TestFalse(TEXT("all359 cast no hidden shadow"),M->bCastHiddenShadow);
            T->TestFalse(TEXT("all359 contribute no hidden GI"),M->bAffectIndirectLightingWhileHidden);
            bool Found=false;
            for (int32 I=0;I<RuntimeRows.Num();++I)
            {
                if (Matched[I]) continue;
                const auto R=RuntimeRows[I]->AsObject();
                if (!M->GetStaticMesh() || !M->GetStaticMesh()->GetPathName().Equals(R->GetStringField(TEXT("mesh")),ESearchCase::IgnoreCase)) continue;
                const auto Vec=[&](const TCHAR* Key){const auto& A=R->GetArrayField(Key);return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());};
                const FVector Position=Vec(TEXT("world_cm")),Scale=Vec(TEXT("scale")),Rotation=Vec(TEXT("rotation_deg"));
                if (!M->GetComponentLocation().Equals(Position,.01) || !M->GetComponentScale().Equals(Scale,.0001) || !M->GetComponentRotation().Equals(FRotator(Rotation.X,Rotation.Y,Rotation.Z),.01))continue;
                Matched[I]=true;Found=true;break;
            }
            T->TestTrue(TEXT("every actual component matches a unique source mesh/world transform"),Found);
            FHitResult Hit;RuntimeContext->GetWorld()->LineTraceSingleByChannel(Hit,M->Bounds.Origin+FVector(0,0,100),M->Bounds.Origin-FVector(0,0,100),ECC_Visibility);
            T->TestTrue(TEXT("world trace never hits any actual render-only vista component"),Hit.GetActor()!=RuntimeContext);
        }
        T->TestEqual(TEXT("actual359 component set references62 meshes"),Assets.Num(),62);
    }
    void CheckOriginals()
    {
        for (const auto &B : Originals)
        {
            T->TestEqual(TEXT("exterior hidden unchanged"), B.M->GetOwner()->IsHidden(), B.Hidden);
            T->TestEqual(TEXT("exterior visibility unchanged"), B.M->IsVisible(), B.Visible);
            T->TestEqual(TEXT("exterior owner unchanged"), B.M->GetOwner(), B.Owner);
            T->TestEqual(TEXT("exterior parent unchanged"), B.M->GetAttachParent(), B.Parent);
            T->TestTrue(TEXT("exterior transform unchanged"), B.M->GetComponentTransform().Equals(B.Transform, .001));
            T->TestEqual(TEXT("exterior collision unchanged"), B.M->GetCollisionEnabled(), B.Enabled);
            auto W=B.M->GetWorld(); auto PC=W->GetFirstPlayerController(); auto H=PC ? PC->GetPawn() : nullptr;
            auto Camera=H ? H->FindComponentByClass<UDinkInteriorCameraComponent>() : nullptr;
            auto Grey=W->GetSubsystem<UDinkGreyboxSubsystem>();
            const bool ManagedCottage=B.M->GetStaticMesh() && B.M->GetStaticMesh()->GetName()==TEXT("SM_Cottage_Stonebrook_01") &&
                B.M->GetOwner()->ActorHasTag(TEXT("DinkCameraOccluder")) && Grey->GetCurrentScreen()==Yard && Camera && !Camera->bInteriorMode;
            if (ManagedCottage)
            {
                auto Expected=B.Responses;Expected.SetResponse(ECC_Camera,ECR_Ignore);
                T->TestTrue(TEXT("qualified cottage changes only Camera response"),B.M->GetCollisionResponseToChannels()==Expected);
                T->TestEqual(TEXT("qualified cottage has exactly five managed material overrides"),B.M->OverrideMaterials.Num(),B.Materials.Num());
                for(int I=0;I<B.Materials.Num();++I)
                {
                    auto MID=Cast<UMaterialInstanceDynamic>(B.M->GetMaterial(I));
                    T->TestTrue(TEXT("cottage material changes belong solely to native camera policy"),MID && MID->GetOuter()==Camera && MID->GetBlendMode()==BLEND_Masked);
                }
            }
            else
            {
                T->TestTrue(TEXT("foreign exterior responses unchanged / cottage restores when unmanaged"), B.M->GetCollisionResponseToChannels() == B.Responses);
                T->TestTrue(TEXT("foreign exterior overrides unchanged / cottage restores when unmanaged"), B.M->OverrideMaterials == B.Overrides);
                for (int I = 0; I < B.Materials.Num(); ++I)
                    T->TestEqual(TEXT("foreign exterior material unchanged / cottage restores when unmanaged"), B.M->GetMaterial(I), B.Materials[I].Get());
            }
        }
        T->TestFalse(TEXT("ordinary screen-tagged art never globally hidden"), Ordinary->IsHidden());
    }

  public:
    explicit FContextPIE(FAutomationTestBase *Test) : T(Test)
    {
    }
    bool Update() override
    {
        if (!Start)
            Start = FPlatformTime::Seconds();
        if (FPlatformTime::Seconds() - Start > (Phase==0 ? 240 : 90))
        {
            T->AddError(TEXT("context PIE timed out"));
            return true;
        }
        UWorld *W = GEditor ? GEditor->PlayWorld.Get() : nullptr;
        auto PC = W ? W->GetFirstPlayerController() : nullptr;
        auto H = PC ? Cast<ADinkGreyboxCharacter>(PC->GetPawn()) : nullptr;
        auto Story = W && W->GetGameInstance() ? W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>() : nullptr;
        if (FPlatformTime::Seconds()-LastDiagnostic>5)
        {
            LastDiagnostic=FPlatformTime::Seconds();
            T->AddInfo(FString::Printf(TEXT("Context startup phase%d hero%d story%d pending%d tickable%d commandlet%d paused%d worldtime%.3f menu%d frozen%d ignored%d"), Phase,H!=nullptr,Story!=nullptr,Story ? Story->bNewGamePending : -1,Story ? Story->IsTickable() : -1,IsRunningCommandlet(),W ? W->IsPaused() : -1,W ? W->GetTimeSeconds() : -1.,Story ? Story->GetActiveMenu()!=nullptr : -1,Story && Story->GetDirector() ? Story->GetDirector()->GetDink().bFrozen : -1,PC ? PC->IsMoveInputIgnored() : -1));
        }
        if (!H || !Story || Story->bNewGamePending)
            return false;
        auto G = W->GetSubsystem<UDinkGreyboxSubsystem>();
        if (Phase == 0)
        {
            Story->SkipDialogue();
            if (Story->GetActiveMenu() || Story->GetDirector()->GetDink().bFrozen || PC->IsMoveInputIgnored())
                return false;
            Home = G->FindScreen(1);
            Other = G->FindScreen(2);
            Yard = G->FindScreen(439);
            if (!T->TestNotNull(TEXT("home"), Home) || !T->TestNotNull(TEXT("other room"), Other) ||
                !T->TestNotNull(TEXT("yard"), Yard))
                return true;
            Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
            if (!T->TestNotNull(TEXT("real cube loads"), Cube))
                return true;
            Meshes.Add(Cube->GetPathName(), Cube);
            for (TActorIterator<AStaticMeshActor> I(W); I; ++I)
                if (I->ActorHasTag(TEXT("DinkArtScreen_439")))
                    Originals.Emplace(I->GetStaticMeshComponent());
            T->TestTrue(TEXT("real persistent exterior captured"), Originals.Num() > 10);
            Move(H, G, Yard);
            Phase = 1;
            At = FPlatformTime::Seconds();
            Start = At; // Cold-cache readiness is separate from the functional fixture deadline.
            return false;
        }
        if (FPlatformTime::Seconds() - At < .35)
            return false;
        if (Phase == 1)
        {
            const FString ManifestPath=FPaths::ProjectContentDir()/TEXT("Dink/Data/Art/stonebrook_vista_v4.json");
            FString Text;HasRuntimeManifest=FFileHelper::LoadFileToString(Text,*ManifestPath);
            if (HasRuntimeManifest)
            {
                TSharedPtr<FJsonObject> Json;
                if (!T->TestTrue(TEXT("private actual manifest parses"),FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Json)))return true;
                RuntimeRows=Json->GetArrayField(TEXT("elements"));
                for(TActorIterator<ADinkArtContextActor> I(W);I;++I)
                    if(I->ActorHasTag(TEXT("DinkArtManifest_stonebrook_vista_v4.json")))
                    {T->TestNull(TEXT("only one real-manifest context root"),RuntimeContext);RuntimeContext=*I;}
                CheckRuntime(false);
            }
            BaselineContextCount=Count(*W);

            Ordinary = W->SpawnActor<AStaticMeshActor>();
            Ordinary->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
            Ordinary->GetStaticMeshComponent()->SetStaticMesh(Cube);
            Ordinary->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("NoCollision"));
            Ordinary->Tags.Add(TEXT("DinkArtScreen_1"));
            Ordinary->SetActorHiddenInGame(false);
            auto P = Home->MapPixelToWorld(303.5, 345) + FVector(0, 0, 1000);
            ExpectedContextPosition = P;
            Rejections(*W, P);
            C = ADinkArtContextActor::CreateFromManifest(*W, Spec(1, P, Cube->GetPathName()), Meshes, 1);
            C2 = ADinkArtContextActor::CreateFromManifest(
                *W, Spec(2, Other->MapPixelToWorld(300, 200) + FVector(0, 0, 1000), Cube->GetPathName()), Meshes, 2);
            if (!T->TestNotNull(TEXT("context1"), C) || !T->TestNotNull(TEXT("context2"), C2))
                return true;
            T->TestTrue(TEXT("context starts hidden on439"), C->IsHidden());
            Physical();
            Move(H, G, Home);
            Phase = 2;
            At = FPlatformTime::Seconds();
            return false;
        }
        if (Phase == 2)
        {
            T->TestFalse(TEXT("screen1 visible"), C->IsHidden());
            CheckRuntime(true);
            T->TestTrue(TEXT("screen2 context hidden"), C2->IsHidden());
            CheckOriginals();
            Early =
                W->SpawnActorDeferred<ADinkArtContextActor>(ADinkArtContextActor::StaticClass(), FTransform::Identity);
            T->TestTrue(TEXT("hidden before BeginPlay"), Early->IsHidden());
            Early->ConfigureOwnerScreen(1);
            T->TestTrue(TEXT("configured unfinished actor remains hidden"), Early->IsHidden());
            Early->FinishSpawning(FTransform::Identity);
            T->TestFalse(TEXT("before-BeginPlay owner setting reads current room"), Early->IsHidden());
            PC->UnPossess();
            T->TestEqual(TEXT("actual stale screen on unpossess"), G->GetCurrentScreen(), Home);
            T->TestTrue(TEXT("unpossess hides immediately without tick"), C->IsHidden());
            CheckRuntime(false);
            T->TestTrue(TEXT("early actor also hides without tick"), Early->IsHidden());
            H->SetActorLocation(Yard->MapPixelToWorld(300, 200) + FVector(0, 0, 98), false, nullptr,
                                ETeleportType::TeleportPhysics);
            PC->Possess(H);
            T->TestTrue(TEXT("repossess elsewhere never exposes stale context"), C->IsHidden());
            G->RefreshCurrentScreen();
            Move(H, G, Other);
            Phase = 3;
            At = FPlatformTime::Seconds();
            return false;
        }
        if (Phase == 3)
        {
            T->TestTrue(TEXT("screen2 hides1"), C->IsHidden());
            CheckRuntime(false);
            T->TestFalse(TEXT("screen2 shows2"), C2->IsHidden());
            Physical();
            CheckOriginals();
            H->GetCharacterMovement()->StopMovementImmediately();
            H->SetActorLocation(FVector(1e8, 1e8, 98), false, nullptr, ETeleportType::TeleportPhysics);
            G->RefreshCurrentScreen();
            T->TestNull(TEXT("outside is no screen"), G->GetCurrentScreen());
            T->TestTrue(TEXT("no screen hides1"), C->IsHidden());
            T->TestTrue(TEXT("no screen hides2"), C2->IsHidden());
            CheckRuntime(false);
            Move(H, G, Home);
            Phase = 4;
            At = FPlatformTime::Seconds();
            return false;
        }
        if (Phase == 4)
        {
            T->TestFalse(TEXT("return shows1"), C->IsHidden());
            CheckRuntime(true);
            Physical();
            CheckOriginals();
            UClass* ControllerClass=PC->GetClass();
            ULocalPlayer* Player=PC->GetLocalPlayer();
            PC->UnPossess();
            PC->Destroy();
            APlayerController* Replacement=W->SpawnActor<APlayerController>(ControllerClass);
            if (!T->TestNotNull(TEXT("replacement first player controller spawned"),Replacement)) return true;
            if (Player) Replacement->SetPlayer(Player);
            Replacement->Possess(H);
            T->TestEqual(TEXT("same-screen replacement never changes current room"),G->GetCurrentScreen(),Home);
            T->TestEqual(TEXT("existing pawn now belongs to new first controller"),W->GetFirstPlayerController(),Replacement);
            // No refresh/configure call or screen transition: only game time advances.
            Phase=5; At=FPlatformTime::Seconds(); return false;
        }
        if (Phase==5)
        {
            T->TestEqual(TEXT("same room remains selected after controller replacement"),G->GetCurrentScreen(),Home);
            T->TestFalse(TEXT("context recovers from first-controller replacement without screen event"),C->IsHidden());
            T->TestFalse(TEXT("preconfigured context also rebinds replacement controller"),Early->IsHidden());
            CheckRuntime(true);
            CheckOriginals();
            TInlineComponentArray<UStaticMeshComponent *> Ms(C);
            C->Destroy();
            C2->Destroy();
            Early->Destroy();
            for (auto M : Ms)
                T->TestFalse(TEXT("destroy unregisters owned geometry"), M->IsRegistered());
            Move(H, G, Yard);
            PC->UnPossess();
            PC->Possess(H);
            G->RefreshCurrentScreen();
            CheckOriginals();
            T->TestTrue(TEXT("post-destroy delegates remain healthy"), IsValid(H));
            Phase=6; At=FPlatformTime::Seconds(); return false;
        }
        if (Phase==6)
        {
            // Advance beyond the refresh period after destruction: no stale work.
            CheckOriginals();
            T->TestEqual(TEXT("only original runtime contexts remain after fixture destruction"),Count(*W),BaselineContextCount);
            CheckRuntime(false);
            T->TestTrue(TEXT("world remains healthy after context timer cleanup"),IsValid(H));
            Ordinary->Destroy();
            return true;
        }
        return false;
    }
};
class FRestoreArt : public IAutomationLatentCommand
{
    int32 V;

  public:
    explicit FRestoreArt(int32 X) : V(X)
    {
    }
    bool Update() override
    {
        IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"))->Set(V, ECVF_SetByCode);
        return true;
    }
};
} // namespace
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkArtContextTest, "Dink.Art.Context.OwnerScreenVisibility", DINK_TEST_FLAGS)
bool FDinkArtContextTest::RunTest(const FString &)
{
    const FString P = FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"),
                                                              FPackageName::GetMapPackageExtension());
    if (!TestNotNull(TEXT("real world loads"), UEditorLoadingAndSavingUtils::LoadMap(P)))
        return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    auto A = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));
    int32 Prior = A->GetInt();
    A->Set(1, ECVF_SetByCode);
    AddCommand(new FStartPIECommand(false));
    AddCommand(new FContextPIE(this));
    AddCommand(new FEndPlayMapCommand());
    AddCommand(new FRestoreArt(Prior));
    return true;
}
