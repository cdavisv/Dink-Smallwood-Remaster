// Actual generated-template/marked-world acceptance. No private admission seam.
#include "DinkTestHelpers.h"
#include "GameMapsSettings.h"
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
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "AssetCompilingManager.h"
#include "Editor.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/PackageName.h"
#include "Tests/AutomationEditorCommon.h"

class FDinkRealBarrelCheck : public IAutomationLatentCommand
{
public:
    FDinkRealBarrelCheck(FAutomationTestBase* T,int32 N):FDinkRealBarrelCheck(T,FDinkOriginId(N,N==31?3:13)){}
    FDinkRealBarrelCheck(FAutomationTestBase* T,FDinkOriginId Origin,FString ContactMode=FString())
        :DiagnosticMode(MoveTemp(ContactMode)),Test(T),Screen(Origin.Screen),Index(Origin.Placement),Began(FPlatformTime::Seconds()){}
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
               !Test->TestTrue(TEXT("actual source policy requests this origin"),W->GetSubsystem<UDinkArtFamilySubsystem>()->IsCollisionFitRequested(Id))||
               !Test->TestTrue(TEXT("ordinary greybox teleport enters actual screen"),Greybox->GotoScreen(Screen,float(P->X-20+65),float(P->Y))))return true;
            Phase=1;Until=Now+1;return false;
        }
        if(!DiagnosticMode.IsEmpty())return UpdateContactDiagnostic(W,Hero,Story,Greybox,Now);
        if(Phase==1)
        {
            if(!Test->TestEqual(TEXT("actual screen event completed"),D->GetDink().Screen,Screen))return true;
            const int32 H=D->HandleForPlacement(Screen,Index);auto* S=D->FindSprite(H);
            if(!Test->TestTrue(TEXT("actual original template created live barrel"),S&&S->bActive&&S->Origin==Id&&S->Script==P->Script))return true;
            auto* Actor=Cast<ADinkPlaceholderActor>(S->Actor.Get());auto* Body=G->FindHardnessFitPrimitive(*S);
            if(!Test->TestNotNull(TEXT("real initial birth admitted exact fitted body"),Body)||!Test->TestNotNull(TEXT("real original placeholder actor"),Actor))return true;
            Test->TestFalse(TEXT("successful initial fitted publication releases the hardness loading gate"),G->IsHardnessLoading());
            Test->TestFalse(TEXT("successful initial fitted publication releases controller movement"),PC->IsMoveInputIgnored());
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
                FMath::IsNearlyEqual(Body->Bounds.BoxExtent.X*2,ExpectedBounds.GetSize().X,.05)&&FMath::IsNearlyEqual(Body->Bounds.BoxExtent.Y*2,ExpectedBounds.GetSize().Y,.05));
            auto OnlyBody=[&](UPrimitiveComponent* Selected)
            {
                FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkFittedRealCardinal),true);
                for(TActorIterator<AActor> It(W);It;++It)
                {
                    TArray<UPrimitiveComponent*> All;It->GetComponents(All);
                    for(auto* C:All)if(C!=Selected)Params.AddIgnoredComponent(C);
                }
                return Params;
            };
            const auto Query=OnlyBody(Body);
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
            Intact.Capture(*Story);if(!Test->TestFalse(TEXT("actual intact save is nonempty"),Intact.Narrative.IsEmpty()))return true;
            const int32 Before=G->GetHard(Screen,int32(P->X),int32(P->Y-5));
            Test->TestEqual(TEXT("actual fitted body interior owns original code"),Before,100+Index);
            FDinkScriptInstance Caller;Caller.Id=9100;Caller.Sprite=H;
            auto Cmd=[&](const FString& Text){D->Execute(Caller,FDinkStoryLine::Parse(TEXT(">> ")+Text,{TEXT("cmd"),TEXT("src:1")}));};
            Cmd(FString::Printf(TEXT("sp_hard %d 1"),H));
            Test->TestEqual(TEXT("sp_hard is delayed before draw"),G->GetHard(Screen,int32(P->X),int32(P->Y-5)),Before);
            Cmd(FString::Printf(TEXT("sp_hard %d 0"),H));
            G->SetPlacementProp(Id,1);
            auto* InertBody=G->FindHardnessFitPrimitive(*D->FindSprite(H));
            if(!Test->TestNotNull(TEXT("propwalkthrough keeps inert exact interaction body"),InertBody))return true;
            Test->TestFalse(TEXT("accepted prop immediately disables world blocking"),W->SweepSingleByChannel(High,Ground+FVector(-200,0,90),Ground+FVector(0,0,90),FQuat::Identity,ECC_Pawn,Capsule,OnlyBody(InertBody)));
            G->SetPlacementProp(Id,0);
            // Use the real production hit resolver, not StartProcedure(barrel,hit).
            TSet<int32> BeforeHit;
            for (const auto& Pair : D->GetSprites()) BeforeHit.Add(Pair.Key);
            Hero->SetActorLocation(Ground+FVector(-75,0,Hero->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2),false,nullptr,ETeleportType::TeleportPhysics);
            Hero->SetActorRotation(FRotator::ZeroRotator);G->SyncDinkFacingFromActor();
            G->RunThroughTagList(1);G->FlushPendingHits();Story->RunUntilIdle();
            // Verify creation in the hit turn before touch/brain ticks can consume the food.
            FName DropScript;
            int32 DropSequence = 0;
            int32 DropOffsetY = 0;
            if (P->Script == TEXT("bar-gh")) { DropScript = TEXT("gheart"); DropSequence = 53; }
            else if (P->Script == TEXT("bar-f1")) { DropScript = TEXT("sfood"); DropSequence = 421; }
            else if (P->Script == TEXT("bar-sh")) { DropScript = TEXT("sheart"); DropSequence = 54; DropOffsetY = 1; }
            else if (P->Script == TEXT("bar-dp")) { DropScript = TEXT("bpotion"); DropSequence = 178; DropOffsetY = 1; }
            else if (P->Script == TEXT("bar-sp")) { DropScript = TEXT("rpotion"); DropSequence = 178; DropOffsetY = 1; }
            else if (!Test->TestEqual(TEXT("supported no-drop barrel source"), P->Script, FName(TEXT("bar-e"))))
                return true;
            bool Drop = false;
            bool UnexpectedDrop = false;
            FString ObservedDrops;
            for (const auto& Pair : D->GetSprites())
            {
                const auto& Sprite = Pair.Value;
                if (BeforeHit.Contains(Pair.Key) || Sprite.Screen != Screen || !Sprite.bActive) continue;
                if (DropScript.IsNone())
                {
                    UnexpectedDrop |= Sprite.Script == TEXT("gheart") || Sprite.Script == TEXT("sfood") ||
                        Sprite.Script == TEXT("sheart") || Sprite.Script == TEXT("bpotion") || Sprite.Script == TEXT("rpotion");
                    continue;
                }
                if (Sprite.Script != DropScript) continue;
                Drop |= Sprite.X == P->X && Sprite.Y == P->Y + DropOffsetY &&
                    Sprite.GetProp(TEXT("pseq")) == DropSequence;
                ObservedDrops += FString::Printf(TEXT(" xy=(%.9g,%.9g) picture=%d"),
                    double(Sprite.X), double(Sprite.Y), Sprite.GetProp(TEXT("pseq")));
            }
            if (DropScript.IsNone())
                Test->TestFalse(TEXT("empty barrel does not create a bonus"), UnexpectedDrop);
            else
                Test->TestTrue(FString::Printf(TEXT("actual %s drop %s at source coordinates %.9g,%.9g (observed%s)"),
                    *P->Script.ToString(), *DropScript.ToString(), double(P->X), double(P->Y + DropOffsetY),
                    *ObservedDrops), Drop);
            Phase=2;Until=Now+.5;return false;
        }
        if(Phase==2)
        {
            Test->TestEqual(TEXT("actual hit persisted original editor_type3"),int32(Story->GetWorldState()->GetOverrideType(Id)),3);
            const int32 H=D->HandleForPlacement(Screen,Index);auto* S=D->FindSprite(H);
            Test->TestTrue(TEXT("broken actual barrel has no fitted body"),!S||!G->FindHardnessFitPrimitive(*S));
            Broken.Capture(*Story);
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
            if(!Test->TestTrue(TEXT("actual same-screen broken save load"),Broken.Restore(*Story)))return true;
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
            if(!Test->TestTrue(TEXT("actual same-screen intact save load"),Intact.Restore(*Story)))return true;
            const auto* Immediate=D->FindSprite(D->HandleForPlacement(Screen,Index));
            Test->AddInfo(FString::Printf(TEXT("intact reload return: sprite=%d body=%d hardness_loading=%d controller_ignored=%d dink_frozen=%d"),
                Immediate!=nullptr,Immediate&&G->FindHardnessFitPrimitive(*Immediate),G->IsHardnessLoading(),PC->IsMoveInputIgnored(),D->GetDink().bFrozen));
            Phase=6;Until=Now+.5;return false;
        }
        const int32 H=D->HandleForPlacement(Screen,Index);auto* S=D->FindSprite(H);
        Test->TestTrue(TEXT("intact save/load restores the original live sprite"),S&&S->bActive&&S->Origin==Id);
        FString FitError;
        auto* RestoredBody=S?G->FindHardnessFitPrimitive(*S,&FitError):nullptr;
        Test->TestNotNull(FString::Printf(TEXT("intact save/load re-admits the fitted body (%s)"),*FitError),RestoredBody);
        Test->TestFalse(TEXT("intact save/load releases the hardness loading gate"),G->IsHardnessLoading());
        Test->TestFalse(FString::Printf(TEXT("intact save/load releases controller movement (Dink frozen=%d)"),D->GetDink().bFrozen),PC->IsMoveInputIgnored());
        bool FamilyVisible=false;
        auto* RestoredActor=S?Cast<ADinkPlaceholderActor>(S->Actor.Get()):nullptr;
        if(RestoredActor)
        {
            TArray<UStaticMeshComponent*> Meshes;RestoredActor->GetComponents(Meshes);
            for(auto* Mesh:Meshes)
                if(Mesh->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag))
                    FamilyVisible|=Mesh->IsVisible()&&!Mesh->bHiddenInGame;
        }
        Test->TestTrue(TEXT("intact save restores family visibility and hides broken card"),
            RestoredActor&&RestoredActor->Card&&!RestoredActor->Card->IsVisible()&&RestoredActor->Card->bHiddenInGame&&FamilyVisible);
        return true;
    }
private:
    FString DiagnosticMode;
    bool UpdateContactDiagnostic(UWorld* W,ADinkGreyboxCharacter* Hero,UDinkStorySubsystem* Story,
        UDinkGreyboxSubsystem* Greybox,double Now)
    {
        auto* G=Story->GetGameplay();auto* D=Story->GetDirector();
        const FDinkOriginId Id(Screen,Index);
        auto* Target=D->FindSprite(D->HandleForPlacement(Screen,Index));
        if(Phase==1)
        {
            if(!Test->TestNotNull(TEXT("contact diagnostic has real original sprite"),Target))return true;
            auto* Body=G->FindHardnessFitPrimitive(*Target);
            if(!Test->TestNotNull(TEXT("contact diagnostic has admitted fitted geometry"),Body))return true;
            if(!Test->TestEqual(TEXT("measured fist witness uses default range"),D->GetDink().GetProp(TEXT("range")),0))return true;
            const auto* Capsule=Hero->GetCapsuleComponent();
            const FVector Center=Body->Bounds.Origin;
            // Actual GPU c220... CombatProbe1 origin is (221417.03867542115,
            // -157286.60466988108,98.14999956674819), relative to this body XY.
            const FVector Live(Center.X-70.32132457885,Center.Y-1.00466988108,98.14999956674819);
            const FVector Native75(Center.X-75,Center.Y,Live.Z);
            const FVector Native80(Center.X-80,Center.Y,Live.Z);
            FCollisionQueryParams ContactParams(SCENE_QUERY_STAT(DinkLiveBarrelContact),false,Hero);
            FHitResult Contact;
            const bool ContactHit=W->SweepSingleByChannel(Contact,
                FVector(Center.X-120,Center.Y,Live.Z),FVector(Center.X,Center.Y,Live.Z),
                FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(
                    Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight()),ContactParams);
            Test->AddInfo(FString::Printf(TEXT("UNFILTERED_CONTACT hit=%d component=%s distance=%.17g point=%s"),
                ContactHit,*GetPathNameSafe(Contact.GetComponent()),Contact.Distance,*Contact.Location.ToString()));
            if(!Test->TestTrue(TEXT("unfiltered original-world capsule contact belongs to fitted barrel"),ContactHit&&Contact.GetComponent()==Body))return true;

            auto Place=[&](const FVector& Position,float Yaw)
            {
                Hero->SetActorLocation(Position,false,nullptr,ETeleportType::TeleportPhysics);
                Hero->SetActorRotation(FRotator(0,Yaw,0));
                G->SyncDinkFromActor();G->SyncDinkFacingFromActor();
            };
            auto Measure=[&](const TCHAR* Label,const FVector& Position)
            {
                Place(Position,0);
                const FVector Forward=Hero->GetActorForwardVector().GetSafeNormal2D();
                const float Radius=FMath::Max(1.f,float(G->AuthoredInteraction.AttackHalfWidthCm));
                const float HalfHeight=FMath::Max(Radius,Capsule->GetScaledCapsuleHalfHeight()-10.f);
                const FVector Start=Position+Forward*(Capsule->GetScaledCapsuleRadius()+Radius);
                const FVector End=Position+Forward*(Capsule->GetScaledCapsuleRadius()+
                    FMath::Max(G->AuthoredInteraction.AttackReachCm,double(Radius*2))-Radius);
                double Distance=0;
                const bool Accepted=G->AuthoredGeometryMatches(D->GetDink(),*Target,UDinkGameplay::EAuthoredInteraction::Hit,&Distance);
                Test->AddInfo(FString::Printf(TEXT("ACTUAL_PREDICATE pose=%s accepted=%d distance=%.17g from=(%.17g,%.17g,%.17g) start=%s end=%s radius=%.17g halfheight=%.17g"),
                    Label,Accepted,Distance,Position.X,Position.Y,Position.Z,*Start.ToString(),*End.ToString(),double(Radius),double(HalfHeight)));
                for(bool Complex:{false,true})
                {
                    FHitResult Hit;
                    const bool Swept=Body->SweepComponent(Hit,Start,End,FQuat::Identity,
                        FCollisionShape::MakeCapsule(Radius,HalfHeight),Complex);
                    FVector Surface=Hit.ImpactPoint;
                    if(Hit.bStartPenetrating)Surface=Body->Bounds.GetBox().GetClosestPointTo(Position);
                    FHitResult Wall;FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkLiveBarrelSight),true,Hero);
                    const bool Occluded=Swept&&W->LineTraceSingleByChannel(Wall,Position,Surface,ECC_Visibility,Params);
                    Test->AddInfo(FString::Printf(TEXT("CAPSULE pose=%s complex=%d result=%d blocking=%d penetrating=%d distance=%.17g impact=%s location=%s normal=%s surface=%s LOS=%d blocker=%s blockerDistance=%.17g bodyClass=%s"),
                        Label,Complex,Swept,Hit.bBlockingHit,Hit.bStartPenetrating,Hit.Distance,
                        *Hit.ImpactPoint.ToString(),*Hit.Location.ToString(),*Hit.ImpactNormal.ToString(),
                        *Surface.ToString(),Occluded,*GetPathNameSafe(Wall.GetComponent()),Wall.Distance,*Body->GetClass()->GetName()));
                }
            };
            Measure(TEXT("measured-live"),Live);
            Measure(TEXT("native75"),Native75);
            Measure(TEXT("native80"),Native80);
            Measure(TEXT("unfiltered-contact"),Contact.Location);
            Place(Native75,180);
            Test->TestFalse(TEXT("actual authored predicate rejects facing-away attack"),
                G->AuthoredGeometryMatches(D->GetDink(),*Target,UDinkGameplay::EAuthoredInteraction::Hit));
            Place(Native75,0);
            AActor* WallActor=W->SpawnActor<AActor>();
            if(!Test->TestNotNull(TEXT("owned occlusion control actor"),WallActor))return true;
            auto* Wall=NewObject<UBoxComponent>(WallActor);
            WallActor->SetRootComponent(Wall);WallActor->AddInstanceComponent(Wall);
            Wall->SetBoxExtent(FVector(2,80,140));Wall->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
            Wall->SetCollisionResponseToAllChannels(ECR_Ignore);
            Wall->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
            Wall->RegisterComponent();WallActor->SetActorLocation(Native75+FVector(12,0,0));
            Test->TestFalse(TEXT("actual authored predicate rejects an occluding world wall"),
                G->AuthoredGeometryMatches(D->GetDink(),*Target,UDinkGameplay::EAuthoredInteraction::Hit));
            WallActor->Destroy();
            Place(DiagnosticMode.StartsWith(TEXT("Live"))?Live:Native75,0);
            Story->bInstantMode=false;
            const int32 Delay=G->Data.HitFrameDelayMs(106);
            Test->TestEqual(TEXT("actual sequence106 special hit delay is175ms"),Delay,175);
            if(DiagnosticMode.EndsWith(TEXT("Direct")))
            {
                G->RunThroughTagList(1);
                bool ImmediateDrop=false;
                const auto* Source=G->GetData().FindPlacement(Id);
                for(const auto& Pair:D->GetSprites())
                    if(Pair.Value.bActive&&Pair.Value.Screen==Screen&&Pair.Value.Script==FName(TEXT("gheart")))
                        ImmediateDrop|=Pair.Value.X==Source->X&&Pair.Value.Y==Source->Y&&Pair.Value.GetProp(TEXT("pseq"))==53;
                Test->TestTrue(TEXT("direct actual hit creates original gold heart in the hit turn"),ImmediateDrop);
            }
            else
            {
                const auto* Weapon=Story->FindInstance(G->GetWeaponInstance());
                Test->AddInfo(FString::Printf(TEXT("ARMED_WEAPON id=%d exists=%d alive=%d script=%s hasUse=%d"),
                    G->GetWeaponInstance(),Weapon!=nullptr,Weapon&&Weapon->IsAlive(),
                    Weapon?*Weapon->Script.ToString():TEXT("None"),
                    Weapon&&Story->HasProcedure(Weapon->Script,TEXT("use"))));
                Test->TestTrue(TEXT("production PlayerAttack accepts normal armed fist input"),G->PlayerAttack());
                Test->AddInfo(FString::Printf(TEXT("PLAYER_ATTACK pending=%d now=%.17g seq=%d dir=%d"),
                    G->PendingHits.Num(),Story->GetNowMs(),D->GetDink().GetProp(TEXT("seq")),D->GetDink().Dir));
                for(const auto& Hit:G->PendingHits)Test->AddInfo(FString::Printf(TEXT("PENDING sprite=%d seq=%d at=%.17g"),Hit.Sprite,Hit.Seq,Hit.AtMs));
            }
            Phase=2;Until=Now+1;return false;
        }
        Test->AddInfo(FString::Printf(TEXT("HIT_OUTCOME mode=%s editorType=%d pending=%d seq=%d dir=%d now=%.17g"),
            *DiagnosticMode,int32(Story->GetWorldState()->GetOverrideType(Id)),G->PendingHits.Num(),
            D->GetDink().GetProp(TEXT("seq")),D->GetDink().Dir,Story->GetNowMs()));
        Test->TestEqual(TEXT("real hit dispatch persists broken original editor_type3"),
            int32(Story->GetWorldState()->GetOverrideType(Id)),3);
        Test->TestTrue(TEXT("real hit removes fitted collision"),!Target||!G->FindHardnessFitPrimitive(*Target));
        bool Drop=false;
        const auto* Source=G->GetData().FindPlacement(Id);
        for(const auto& Pair:D->GetSprites())
            if(Pair.Value.bActive&&Pair.Value.Screen==Screen&&Pair.Value.Script==FName(TEXT("gheart")))
                Drop|=Pair.Value.X==Source->X&&Pair.Value.Y==Source->Y&&Pair.Value.GetProp(TEXT("pseq"))==53;
        Test->AddInfo(FString::Printf(TEXT("SETTLED_DROP activeOriginalGoldHeart=%d (natural tick may collect it; direct creation is asserted in hit turn)"),Drop));
        return true;
    }
    FAutomationTestBase* Test;int32 Screen,Index,Phase=0;double Began,Until=0;FVector Ground;struct FSnapshot
    {
        FString Narrative;
        TArray<FDinkWorldOverride> Overrides;
        TArray<FDinkScreenExitTime> ExitTimes;
        int64 GameTimeMs=0;

        void Capture(UDinkStorySubsystem& Story)
        {
            const auto* World=Story.GetWorldState();
            Overrides=World->ExportOverrides();
            ExitTimes=World->ExportScreenExitTimes();
            GameTimeMs=World->GetGameTimeMs();
            Narrative=Story.SaveStateToJson();
        }

        bool Restore(UDinkStorySubsystem& Story) const
        {
            // The save coordinator restores world overrides before the narrative
            // recreates the screen's original placements.
            Story.GetWorldState()->ImportState(Overrides,ExitTimes,GameTimeMs);
            return Story.LoadStateFromJson(Narrative);
        }
    };
    FSnapshot Intact,Broken;
};

IMPLEMENT_COMPLEX_AUTOMATION_TEST(FDinkRealFittedBarrels,"Dink.Gameplay.FittedBarrelAcceptance",DINK_TEST_FLAGS)
void FDinkRealFittedBarrels::GetTests(TArray<FString>& Names,TArray<FString>& Commands) const
{
    for(int32 N:{31,209})
    {Names.Add(FString::Printf(TEXT("Default%03d"),N));Commands.Add(FString::Printf(TEXT("Default:%d"),N));}
}
bool FDinkRealFittedBarrels::RunTest(const FString& Parameters)
{
    FString Kind,Number;if(!Parameters.Split(TEXT(":"),&Kind,&Number))return false;
    if(Kind!=TEXT("Default"))return false;
    const FString Package=UGameMapsSettings::GetGameDefaultMap();
    const FString File=FPackageName::LongPackageNameToFilename(Package,FPackageName::GetMapPackageExtension());
    if(!TestTrue(TEXT("ordinary default world exists, no fixture-only skip"),IFileManager::Get().FileExists(*File))||!TestNotNull(TEXT("actual acceptance world loads"),UEditorLoadingAndSavingUtils::LoadMap(File)))return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkRealBarrelCheck(this,FCString::Atoi(*Number)));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());return true;
}


IMPLEMENT_COMPLEX_AUTOMATION_TEST(FDinkRolloutScriptHits,"Dink.Gameplay.BarrelRollout.ScriptedHits",DINK_TEST_FLAGS)
void FDinkRolloutScriptHits::GetTests(TArray<FString>& Names,TArray<FString>& Commands) const
{
    for (const TCHAR* Origin : {TEXT("S031_P03"), TEXT("S209_P13"), TEXT("S161_P24"),
        TEXT("S034_P51"), TEXT("S156_P05"), TEXT("S177_P03")})
    {
        Names.Add(Origin);
        Commands.Add(Origin);
    }
}
bool FDinkRolloutScriptHits::RunTest(const FString& Parameters)
{
    FDinkOriginId Origin;
    if (!TestTrue(TEXT("rollout scripted origin parses"), FDinkOriginId::Parse(Parameters, Origin)))
        return false;
    const FString Package = UGameMapsSettings::GetGameDefaultMap();
    const FString File = FPackageName::LongPackageNameToFilename(Package, FPackageName::GetMapPackageExtension());
    if (!TestTrue(TEXT("ordinary saved rollout world exists"), IFileManager::Get().FileExists(*File)) ||
        !TestNotNull(TEXT("ordinary saved rollout world loads"), UEditorLoadingAndSavingUtils::LoadMap(File)))
        return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkRealBarrelCheck(this, Origin));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());
    return true;
}


IMPLEMENT_COMPLEX_AUTOMATION_TEST(FDinkLiveBarrelContact,"Dink.Gameplay.BarrelLiveContact",DINK_TEST_FLAGS)
void FDinkLiveBarrelContact::GetTests(TArray<FString>& Names,TArray<FString>& Commands) const
{
    for(const TCHAR* Mode:{TEXT("LiveTimed"),TEXT("LiveDirect"),TEXT("Native75Timed"),TEXT("Native75Direct")})
    {Names.Add(Mode);Commands.Add(Mode);}
}
bool FDinkLiveBarrelContact::RunTest(const FString& Parameters)
{
    const FString File=FPackageName::LongPackageNameToFilename(UGameMapsSettings::GetGameDefaultMap(),FPackageName::GetMapPackageExtension());
    if(!TestTrue(TEXT("ordinary saved world exists"),IFileManager::Get().FileExists(*File))||
       !TestNotNull(TEXT("ordinary saved world loads"),UEditorLoadingAndSavingUtils::LoadMap(File)))return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    ADD_LATENT_AUTOMATION_COMMAND(FStartPIECommand(false));
    ADD_LATENT_AUTOMATION_COMMAND(FDinkRealBarrelCheck(this,FDinkOriginId(31,3),Parameters));
    ADD_LATENT_AUTOMATION_COMMAND(FEndPlayMapCommand());return true;
}
