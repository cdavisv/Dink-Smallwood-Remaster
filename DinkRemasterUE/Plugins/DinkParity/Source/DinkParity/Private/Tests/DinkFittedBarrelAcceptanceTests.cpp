// Actual generated-template/marked-world acceptance. No private admission seam.
#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkStorySubsystem.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkLayout.h"
#include "DinkOriginComponent.h"
#include "DinkWorldStateSubsystem.h"
#include "Hardness/DinkFamilyCollisionFit.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Hardness/DinkRuntimeHardnessWorldSubsystem.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "AssetCompilingManager.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

namespace
{
class FDinkRealBarrelCheck : public IAutomationLatentCommand
{
public:
    FDinkRealBarrelCheck(FAutomationTestBase* T,int32 N):Test(T),Screen(N),Index(N==31?3:13),Began(FPlatformTime::Seconds()){}
    bool Update() override
    {
        if(FPlatformTime::Seconds()-Began>180){Test->AddError(FString::Printf(TEXT("actual fitted barrel SCR_%03d phase%d timed out"),Screen,Phase));return true;}
        UWorld* W=GEditor?GEditor->PlayWorld.Get():nullptr;
        auto* PC=W?W->GetFirstPlayerController():nullptr;
        auto* Hero=PC?Cast<ADinkGreyboxCharacter>(PC->GetPawn()):nullptr;
        auto* Story=W&&W->GetGameInstance()?W->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>():nullptr;
        auto* Greybox=W?W->GetSubsystem<UDinkGreyboxSubsystem>():nullptr;
        if(!Hero||!Story||!Story->IsReady()||!Greybox)return false;
        auto* G=Story->GetGameplay();auto* D=Story->GetDirector();
        const FDinkOriginId Id(Screen,Index);const auto* P=G->GetData().FindPlacement(Id);
        if(!P){Test->AddError(TEXT("actual original barrel placement missing"));return true;}
        const double Now=W->GetTimeSeconds();
        if(Now<Until)return false;
        if(Phase==0)
        {
            Story->bNewGamePending=false;Story->bInstantMode=true;
            if(!Test->TestTrue(TEXT("real map has explicitly marked capability"),W->GetSubsystem<UDinkRuntimeHardnessWorldSubsystem>()->RequiresScreenCapability(Screen))||
               !Test->TestTrue(TEXT("strict actual two-origin policy is requested"),W->GetSubsystem<UDinkArtFamilySubsystem>()->IsCollisionFitRequested(Id))||
               !Test->TestTrue(TEXT("ordinary greybox teleport enters actual screen"),Greybox->GotoScreen(Screen,float(P->X-20+65),float(P->Y))))return true;
            Phase=1;Until=Now+1;return false;
        }
        if(Phase==1)
        {
            if(!Test->TestEqual(TEXT("actual screen event completed"),D->GetDink().Screen,Screen))return true;
            const int32 H=D->HandleForPlacement(Screen,Index);auto* S=D->FindSprite(H);
            if(!Test->TestTrue(TEXT("actual original template created live barrel"),S&&S->bActive&&S->Origin==Id&&S->Script==FName(Screen==31?TEXT("bar-gh"):TEXT("bar-f1"))))return true;
            auto* Actor=Cast<ADinkPlaceholderActor>(S->Actor.Get());auto* Body=G->FindHardnessFitPrimitive(*S);
            if(!Test->TestNotNull(TEXT("real initial birth admitted exact fitted body"),Body)||!Test->TestNotNull(TEXT("real original placeholder actor"),Actor))return true;
            Ground=Greybox->FindScreen(Screen)->MapPixelToWorld(float(S->X-20),float(S->Y));
            Test->TestTrue(TEXT("barrel body height fits source instead of legacy300cm prism"),Body->Bounds.BoxExtent.Z*2<110&&Body->Bounds.BoxExtent.Z*2>99);
            Test->TestTrue(TEXT("script coordinates stayed original"),S->X==P->X&&S->Y==P->Y);
            bool Visual=false;UStaticMeshComponent* Family=nullptr;TArray<UStaticMeshComponent*> Components;Actor->GetComponents(Components);
            for(auto* C:Components)if(C->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)&&C->GetStaticMesh())
            {Family=C;Visual|=C->IsVisible()&&!C->bHiddenInGame&&FVector::Dist2D(C->GetComponentLocation(),Ground)<.01;}
            if(!Test->TestTrue(TEXT("actual family body is aligned to script ground anchor"),Visual))return true;
            FDinkFamilyFittedGeometry Geometry;FString GeometryError;
            if(!Family||!Test->TestTrue(TEXT("actual visual mesh cooked geometry readable"),DinkFamilyCollisionFit::ReadCookedGeometry(*Family->GetStaticMesh(),Geometry,GeometryError))){Test->AddError(GeometryError);return true;}
            FBox ExpectedBounds(ForceInit);for(const auto& V:Geometry.Vertices)ExpectedBounds+=Family->GetComponentTransform().TransformPosition(FVector(V));
            Test->TestTrue(TEXT("registered fitted XY extent matches ACTUAL cooked geometry, not oversized original hardbox"),
                FMath::IsNearlyEqual(Body->Bounds.BoxExtent.X*2,ExpectedBounds.GetSize().X,.05)&&FMath::IsNearlyEqual(Body->Bounds.BoxExtent.Y*2,ExpectedBounds.GetSize().Y,.05)&&ExpectedBounds.GetSize().X<90&&ExpectedBounds.GetSize().Y<90);
            FCollisionQueryParams Query(SCENE_QUERY_STAT(DinkFittedRealCardinal),true);
            for(TActorIterator<AActor> It(W);It;++It){TArray<UPrimitiveComponent*> All;It->GetComponents(All);for(auto* C:All)if(C!=Body)Query.AddIgnoredComponent(C);}
            const FCollisionShape Capsule=FCollisionShape::MakeCapsule(Hero->GetCapsuleComponent()->GetScaledCapsuleRadius(),Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
            for(const FVector V:{FVector(1,0,0),FVector(-1,0,0),FVector(0,1,0),FVector(0,-1,0)})
            {
                FHitResult WorldHit,ExactHit;const FVector From=Ground+V*200+FVector(0,0,90),To=Ground+FVector(0,0,90);
                Test->TestTrue(TEXT("four-side actual world Pawn capsule hits exact registered barrel (other components query-ignored only)"),W->SweepSingleByChannel(WorldHit,From,To,FQuat::Identity,ECC_Pawn,Capsule,Query)&&WorldHit.GetComponent()==Body);
                Test->TestTrue(TEXT("four-side exact interaction sweep matches actual registered geometry"),Body->SweepComponent(ExactHit,From,To,FQuat::Identity,Capsule,true));
                Test->TestTrue(TEXT("world and exact-query component/contact/distance agree within1mm"),WorldHit.GetComponent()==Body&&ExactHit.GetComponent()==Body&&FMath::Abs(WorldHit.Distance-ExactHit.Distance)<=.1&&WorldHit.ImpactPoint.Equals(ExactHit.ImpactPoint,.1));
            }
            FHitResult High;Test->TestFalse(TEXT("no old300cm wall above body"),W->LineTraceSingleByChannel(High,Ground+FVector(-200,0,150),Ground+FVector(200,0,150),ECC_Pawn,Query));
            int32 OldL,OldT,OldR,OldB;bool GapFound=false;FVector Gap;
            if(G->GetHardbox(*S,OldL,OldT,OldR,OldB))for(int32 Y=OldT+1;Y<OldB&&!GapFound;++Y)for(int32 X=OldL+1;X<OldR&&!GapFound;++X)
            {
                const FVector Point=Greybox->FindScreen(Screen)->MapPixelToWorld(float(X-20),float(Y))+FVector(0,0,90);
                if(ExpectedBounds.ComputeSquaredDistanceToPoint(Point)>FMath::Square(Capsule.GetCapsuleRadius()+2))
                {Gap=Point;GapFound=true;Test->TestNotEqual(TEXT("gap inside original hardbox no longer owns barrel logical code"),G->GetHard(Screen,X,Y),100+Index);}
            }
            Test->TestTrue(TEXT("actual old hardbox contains a capsule-sized gap outside real mesh"),GapFound);
            if(GapFound)Test->TestFalse(TEXT("real-world Pawn capsule fits gap inside OLD hardbox outside actual fitted surface"),W->OverlapBlockingTestByChannel(Gap,FQuat::Identity,ECC_Pawn,Capsule,Query));
            Intact=Story->SaveStateToJson();if(!Test->TestFalse(TEXT("actual intact save is nonempty"),Intact.IsEmpty()))return true;
            const int32 Before=G->GetHard(Screen,int32(P->X),int32(P->Y-5));
            Test->TestEqual(TEXT("actual fitted body interior owns original code"),Before,100+Index);
            FDinkScriptInstance Caller;Caller.Id=9100;Caller.Sprite=H;
            auto Cmd=[&](const FString& Text){D->Execute(Caller,FDinkStoryLine::Parse(TEXT(">> ")+Text,{TEXT("cmd"),TEXT("src:1")}));};
            Cmd(FString::Printf(TEXT("sp_hard %d 1"),H));
            Test->TestEqual(TEXT("sp_hard is delayed before draw"),G->GetHard(Screen,int32(P->X),int32(P->Y-5)),Before);
            Cmd(FString::Printf(TEXT("sp_hard %d 0"),H));
            G->SetPlacementProp(Id,1);Test->TestNotNull(TEXT("propwalkthrough keeps inert exact interaction body"),G->FindHardnessFitPrimitive(*D->FindSprite(H)));
            Test->TestFalse(TEXT("accepted prop immediately disables world blocking"),W->SweepSingleByChannel(High,Ground+FVector(-200,0,90),Ground+FVector(0,0,90),FQuat::Identity,ECC_Pawn,Capsule,Query));
            G->SetPlacementProp(Id,0);
            // Use the real production hit resolver, not StartProcedure(barrel,hit).
            Hero->SetActorLocation(Ground+FVector(-75,0,Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),false,nullptr,ETeleportType::TeleportPhysics);
            Hero->SetActorRotation(FRotator::ZeroRotator);G->SyncDinkFacingFromActor();
            G->RunThroughTagList(1);G->FlushPendingHits();Story->RunUntilIdle();
            Phase=2;Until=Now+.5;return false;
        }
        if(Phase==2)
        {
            Test->TestEqual(TEXT("actual hit persisted original editor_type3"),int32(Story->GetWorldState()->GetOverrideType(Id)),3);
            bool Drop=false;
            for(int32 H:G->LiveSprites(Screen))if(auto* S=D->FindSprite(H))if(S->bActive&&S->Script==FName(Screen==31?TEXT("gheart"):TEXT("sfood")))
                Drop|=S->X==P->X&&S->Y==P->Y&&S->GetProp(TEXT("pseq"))==(Screen==31?53:421);
            Test->TestTrue(TEXT("actual bar-gh goldHEART or bar-f1 food drop at original script coordinates"),Drop);
            const int32 H=D->HandleForPlacement(Screen,Index);auto* S=D->FindSprite(H);
            Test->TestTrue(TEXT("broken actual barrel has no fitted body"),!S||!G->FindHardnessFitPrimitive(*S));
            Broken=Story->SaveStateToJson();
            if(!Test->TestTrue(TEXT("ordinary leave enters other real screen"),Greybox->GotoScreen(Screen==31?209:31)))return true;
            Phase=3;Until=Now+.5;return false;
        }
        if(Phase==3)
        {
            if(!Test->TestTrue(TEXT("ordinary reentry"),Greybox->GotoScreen(Screen,float(P->X-20+65),float(P->Y))))return true;
            Phase=4;Until=Now+.5;return false;
        }
        if(Phase==4)
        {
            const int32 H=D->HandleForPlacement(Screen,Index);auto* S=D->FindSprite(H);
            Test->TestTrue(TEXT("reentry cannot resurrect broken collision"),!S||!G->FindHardnessFitPrimitive(*S));
            bool IntactVisible=false,CardExposed=false;for(TActorIterator<ADinkPlaceholderActor> It(W);It;++It)if(It->Origin&&It->Origin->OriginId==Id)
            {CardExposed|=It->Card&&It->Card->IsVisible()&&!It->Card->bHiddenInGame&&!It->IsHidden();TArray<UStaticMeshComponent*> Cs;It->GetComponents(Cs);for(auto* C:Cs)if(C->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag))IntactVisible|=C->IsVisible()&&!C->bHiddenInGame;}
            Test->TestFalse(TEXT("persisted broken state hides intact family"),IntactVisible);
            Test->TestTrue(TEXT("persisted broken state exposes original card (rendered frame acceptance separate)"),CardExposed);
            Test->TestTrue(TEXT("persistent editor picture is actual173/6"),G->EditorHardnessPicture(Id,true,-1)==173&&G->EditorHardnessPicture(Id,false,-1)==6);
            if(!Test->TestTrue(TEXT("actual same-screen broken save load"),Story->LoadStateFromJson(Broken)))return true;
            Phase=5;Until=Now+.5;return false;
        }
        if(Phase==5)
        {
            const int32 LoadedHandle=D->HandleForPlacement(Screen,Index);const auto* Loaded=D->FindSprite(LoadedHandle);
            Test->TestTrue(TEXT("broken SAVE LOAD does not resurrect fitted body"),!Loaded||!G->FindHardnessFitPrimitive(*Loaded));
            bool LoadedIntactVisible=false,LoadedCardExposed=false;for(TActorIterator<ADinkPlaceholderActor> It(W);It;++It)if(It->Origin&&It->Origin->OriginId==Id)
            {LoadedCardExposed|=It->Card&&It->Card->IsVisible()&&!It->Card->bHiddenInGame&&!It->IsHidden();TArray<UStaticMeshComponent*> Cs;It->GetComponents(Cs);for(auto* C:Cs)if(C->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag))LoadedIntactVisible|=C->IsVisible()&&!C->bHiddenInGame;}
            Test->TestFalse(TEXT("broken SAVE LOAD keeps intact family hidden"),LoadedIntactVisible);
            Test->TestTrue(TEXT("broken SAVE LOAD exposes original card and preserves173/6 (rendered frame separate)"),LoadedCardExposed&&G->EditorHardnessPicture(Id,true,-1)==173&&G->EditorHardnessPicture(Id,false,-1)==6);
            if(!Test->TestTrue(TEXT("actual same-screen intact save load"),Story->LoadStateFromJson(Intact)))return true;
            Phase=6;Until=Now+.5;return false;
        }
        const int32 H=D->HandleForPlacement(Screen,Index);auto* S=D->FindSprite(H);
        Test->TestTrue(TEXT("real save/load re-admits intact barrel and releases movement gate"),S&&G->FindHardnessFitPrimitive(*S)&&!PC->IsMoveInputIgnored());
        return true;
    }
private:
    FAutomationTestBase* Test;int32 Screen,Index,Phase=0;double Began,Until=0;FVector Ground;FString Intact,Broken;
};
}

IMPLEMENT_COMPLEX_AUTOMATION_TEST(FDinkRealFittedBarrels,"Dink.Gameplay.FittedBarrelAcceptance",DINK_TEST_FLAGS)
void FDinkRealFittedBarrels::GetTests(TArray<FString>& Names,TArray<FString>& Commands) const
{
    for(const FString Kind:{FString(TEXT("Candidate")),FString(TEXT("Default"))})for(int32 N:{31,209})
    {Names.Add(FString::Printf(TEXT("%s%03d"),*Kind,N));Commands.Add(FString::Printf(TEXT("%s:%d"),*Kind,N));}
}
bool FDinkRealFittedBarrels::RunTest(const FString& Parameters)
{
    FString Kind,Number;if(!Parameters.Split(TEXT(":"),&Kind,&Number))return false;
    const FString Package=Kind==TEXT("Candidate")?TEXT("/Game/Dink/RuntimeHardnessV1/Worlds/L_Barrel031209V1"):TEXT("/Game/Dink/_Generated/Maps/L_Greybox_World");
    const FString File=FPackageName::LongPackageNameToFilename(Package,FPackageName::GetMapPackageExtension());
    if(!TestTrue(TEXT("actual staged/default world exists, no fixture-only skip"),IFileManager::Get().FileExists(*File))||!TestNotNull(TEXT("actual acceptance world loads"),UEditorLoadingAndSavingUtils::LoadMap(File)))return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkRealBarrelCheck(this,FCString::Atoi(*Number)));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());return true;
}
