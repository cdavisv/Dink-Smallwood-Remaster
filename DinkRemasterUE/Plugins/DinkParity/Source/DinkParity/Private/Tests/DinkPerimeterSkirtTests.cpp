#include "DinkTestHelpers.h"
#include "DinkArtContextActor.h"
#include "DinkInteriorCameraComponent.h"
#include "DinkStorySubsystem.h"
#include "DinkDirector.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "AssetCompilingManager.h"
#include "Components/StaticMeshComponent.h"
#include "Editor.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "MeshDescription.h"
#include "Misc/PackageName.h"
#include "StaticMeshAttributes.h"
#include "Tests/AutomationEditorCommon.h"
namespace
{
struct FOriginalFloor
{
    UStaticMeshComponent* Component;
    FTransform Transform;
    FCollisionResponseContainer Responses;
    ECollisionEnabled::Type Enabled;
    TArray<UMaterialInterface*> Materials;
    explicit FOriginalFloor(UStaticMeshComponent* M):Component(M),Transform(M->GetComponentTransform()),
        Responses(M->GetCollisionResponseToChannels()),Enabled(M->GetCollisionEnabled())
    { for(int I=0;I<M->GetNumMaterials();++I)Materials.Add(M->GetMaterial(I)); }
};
class FSkirtPIE : public IAutomationLatentCommand
{
public:
    explicit FSkirtPIE(FAutomationTestBase* InTest):T(InTest){}
    bool Update() override
    {
        if(!Start)Start=FPlatformTime::Seconds();
        if(FPlatformTime::Seconds()-Start>60){T->AddError(TEXT("perimeter skirt PIE timeout"));return true;}
        UWorld* W=GEditor?GEditor->PlayWorld.Get():nullptr;
        APlayerController* PC=W?W->GetFirstPlayerController():nullptr;
        ADinkGreyboxCharacter* H=PC?Cast<ADinkGreyboxCharacter>(PC->GetPawn()):nullptr;
        UDinkStorySubsystem* Story=W&&W->GetGameInstance()?W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>():nullptr;
        if(!H||!Story||Story->bNewGamePending)return false;
        UDinkGreyboxSubsystem* G=W->GetSubsystem<UDinkGreyboxSubsystem>();
        if(!Phase)
        {
            Story->SkipDialogue();if(Story->GetActiveMenu()||Story->GetDirector()->GetDink().bFrozen)return false;
            Home=G->FindScreen(1);Yard=G->FindScreen(439);
            if(!T->TestNotNull(TEXT("house"),Home)||!T->TestNotNull(TEXT("yard"),Yard))return true;
            for(TActorIterator<ADinkArtContextActor> I(W);I;++I)
                if(I->ActorHasTag(TEXT("DinkArtManifest_stonebrook_perimeter_skirt_v1.json")))
                {T->TestNull(TEXT("unique actual skirt context"),Skirt);Skirt=*I;}
            if(!T->TestNotNull(TEXT("published actual skirt context exists"),Skirt))return true;
            TInlineComponentArray<UStaticMeshComponent*> Parts(Skirt);
            if(!T->TestEqual(TEXT("actual skirt is one mesh"),Parts.Num(),1))return true;
            Mesh=Parts[0];
            for(TActorIterator<AActor> I(W);I;++I)if(I->ActorHasTag(TEXT("DinkArtScreen_1")))
                for(UStaticMeshComponent* M:TInlineComponentArray<UStaticMeshComponent*>(*I))
                    if(M->GetStaticMesh()&&M->GetStaticMesh()->GetName()==TEXT("SM_Floor_Oak_2m_01"))Floors.Emplace(M);
            T->TestEqual(TEXT("all original floor modules retained"),Floors.Num(),56);
            CheckGeometry();Move(H,G,Home);Phase=1;At=FPlatformTime::Seconds();return false;
        }
        if(FPlatformTime::Seconds()-At<.45)return false;
        if(Phase==1)
        {
            Check(true);if(auto* C=H->FindComponentByClass<UDinkInteriorCameraComponent>())
                T->TestEqual(TEXT("skirt never adds a camera occluder"),C->ManagedOccluderCount,85);
            else T->AddError(TEXT("real interior camera component missing"));
            Move(H,G,Yard);Phase=2;At=FPlatformTime::Seconds();return false;
        }
        if(Phase==2){Check(false);Move(H,G,Home);Phase=3;At=FPlatformTime::Seconds();return false;}
        Check(true);return true;
    }
private:
    void Move(ADinkGreyboxCharacter* H,UDinkGreyboxSubsystem* G,ADinkScreenVolume* S)
    {H->GetCharacterMovement()->StopMovementImmediately();H->SetActorLocation(S->MapPixelToWorld(S==Home?303.5:300,S==Home?345:350)+FVector(0,0,98),false,nullptr,ETeleportType::TeleportPhysics);G->RefreshCurrentScreen();}
    void Check(bool Visible)
    {
        T->TestEqual(TEXT("actual skirt visibility follows owner screen"),Skirt->IsHidden(),!Visible);
        T->TestEqual(TEXT("actual context owns house1"),Skirt->GetOwnerScreenNumber(),1);
        T->TestFalse(TEXT("context has no actor collision"),Skirt->GetActorEnableCollision());
        T->TestFalse(TEXT("context has no per-frame tick"),Skirt->PrimaryActorTick.bCanEverTick);
        T->TestFalse(TEXT("context never becomes camera occluder"),Skirt->ActorHasTag(TEXT("DinkCameraOccluder")));
        T->TestEqual(TEXT("mesh has no collision"),Mesh->GetCollisionEnabled(),ECollisionEnabled::NoCollision);
        T->TestFalse(TEXT("mesh has no overlaps"),Mesh->GetGenerateOverlapEvents());
        T->TestFalse(TEXT("mesh has no navigation influence"),Mesh->CanEverAffectNavigation());
        T->TestFalse(TEXT("mesh has no hidden shadow"),Mesh->bCastHiddenShadow);
        T->TestFalse(TEXT("mesh has no hidden GI"),Mesh->bAffectIndirectLightingWhileHidden);
        for(const auto& F:Floors)
        {
            T->TestTrue(TEXT("floor transform retained"),F.Component->GetComponentTransform().Equals(F.Transform));
            T->TestEqual(TEXT("floor collision retained"),F.Component->GetCollisionEnabled(),F.Enabled);
            T->TestTrue(TEXT("floor responses retained"),F.Component->GetCollisionResponseToChannels()==F.Responses);
            T->TestEqual(TEXT("floor material count retained"),F.Component->GetNumMaterials(),F.Materials.Num());
            for(int I=0;I<F.Materials.Num();++I)T->TestEqual(TEXT("floor material retained"),F.Component->GetMaterial(I),F.Materials[I]);
        }
    }
    void CheckGeometry()
    {
        UStaticMesh* Asset=Mesh->GetStaticMesh();if(!T->TestNotNull(TEXT("actual skirt asset"),Asset))return;
        const FMeshDescription* D=Asset->GetMeshDescription(0);if(!T->TestNotNull(TEXT("saved source geometry"),D))return;
        T->TestEqual(TEXT("native skirt source vertices"),D->Vertices().Num(),48);
        T->TestEqual(TEXT("native skirt source triangles"),D->Triangles().Num(),96);
        const auto Positions=FStaticMeshConstAttributes(*D).GetVertexPositions();FBox Box(ForceInit);
        for(const FVertexID V:D->Vertices().GetElementIDs())Box+=Mesh->GetComponentTransform().TransformPosition(FVector(Positions[V]));
        T->TestTrue(TEXT("actual top stays below visible floor"),FMath::IsNearlyEqual(Box.Max.Z,-.2,.05));
        T->TestTrue(TEXT("actual base extends below original sheet"),FMath::IsNearlyEqual(Box.Min.Z,-18.,.05));
        if(T->TestNotNull(TEXT("dark material is loaded"),Mesh->GetMaterial(0)))
        T->TestEqual(TEXT("exact existing dark material reused"),Mesh->GetMaterial(0)->GetPathName(),FString(TEXT("/Game/Dink/Materials/Stonebrook/Refinements/M_Stonebrook_Underfloor_DarkOak_V1.M_Stonebrook_Underfloor_DarkOak_V1")));
    }
    FAutomationTestBase* T;int Phase=0;double Start=0,At=0;
    ADinkScreenVolume* Home=nullptr;ADinkScreenVolume* Yard=nullptr;ADinkArtContextActor* Skirt=nullptr;
    UStaticMeshComponent* Mesh=nullptr;TArray<FOriginalFloor> Floors;
};
class FRestoreSkirtArt:public IAutomationLatentCommand
{public:explicit FRestoreSkirtArt(int32 V):Value(V){}bool Update()override{IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"))->Set(Value,ECVF_SetByCode);return true;}private:int32 Value;};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkSkirtTest,"Dink.Art.Underfloor.PerimeterSkirtOwnership",DINK_TEST_FLAGS)
bool FDinkSkirtTest::RunTest(const FString&)
{
    const FString Map=FPackageName::LongPackageNameToFilename(TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World"),FPackageName::GetMapPackageExtension());
    if(!TestNotNull(TEXT("real world loads"),UEditorLoadingAndSavingUtils::LoadMap(Map)))return false;
    FAssetCompilingManager::Get().FinishAllCompilation();auto* Art=IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));int32 Prior=Art->GetInt();Art->Set(1,ECVF_SetByCode);
    AddCommand(new FStartPIECommand(false));AddCommand(new FSkirtPIE(this));AddCommand(new FEndPlayMapCommand());AddCommand(new FRestoreSkirtArt(Prior));return true;
}
