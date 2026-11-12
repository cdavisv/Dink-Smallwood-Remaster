#include "Hardness/DinkFamilyCollisionFit.h"
#include "Hardness/DinkFamilyFitMath.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "PhysicsEngine/BodySetup.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Materials/MaterialInterface.h"
#include "Dom/JsonObject.h"
#include "Misc/SecureHash.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
const FString BarrelMesh(TEXT("/Game/Dink/Kits/Stonebrook/SM_Barrel_Oak_01.SM_Barrel_Oak_01"));
bool ExactFields(const FJsonObject& O,std::initializer_list<const TCHAR*> Names)
{ if(O.Values.Num()!=int32(Names.size()))return false;for(const auto* N:Names)if(!O.HasField(N))return false;return true; }
bool Eligible(const FDinkFamilyFitSpriteState& S)
{ return S.SchemaVersion==DinkFamilyCollisionFit::DescriptorSchemaVersion&&S.Actor.IsValid()&&S.Origin.IsValid()&&FMath::IsFinite(S.EngineX)&&FMath::IsFinite(S.EngineY)&&!S.ScriptName.IsNone()&&S.RuntimeHandle>1&&S.RuntimeHandle!=1000&&S.bActive&&S.Hard==0&&S.Prop==0&&S.DisplayedSequence==173&&S.DisplayedFrame==1; }
bool SameSprite(const FDinkFamilyFitSpriteState& A,const FDinkFamilyFitSpriteState& B)
{ return A.SchemaVersion==B.SchemaVersion&&A.Origin==B.Origin&&A.Actor==B.Actor&&A.EngineX==B.EngineX&&A.EngineY==B.EngineY&&A.ScriptName==B.ScriptName&&A.RuntimeHandle==B.RuntimeHandle&&A.DisplayedSequence==B.DisplayedSequence&&A.DisplayedFrame==B.DisplayedFrame&&A.Hard==B.Hard&&A.Prop==B.Prop&&A.bActive==B.bActive; }
TArray<TWeakObjectPtr<UMaterialInterface>> Materials(const UStaticMeshComponent& C)
{ TArray<TWeakObjectPtr<UMaterialInterface>> R;for(int32 I=0;I<C.GetNumMaterials();++I)R.Add(C.GetMaterial(I));return R; }
bool ExpectedSource(const ADinkPlaceholderActor& A,const FDinkOriginId& Origin)
{
    const FName Script=Origin.Screen==31?FName(TEXT("bar-gh")):FName(TEXT("bar-f1"));
    if(!A.Origin||A.Origin->SourceHash.Len()!=40)return false;
    for(TCHAR C:A.Origin->SourceHash)if(!FChar::IsHexDigit(C))return false;
    return A.Origin->OriginId==Origin&&A.ScreenNumber==Origin.Screen&&A.Origin->Sequence==173&&
        A.Origin->Frame==1&&A.Origin->ClassId==TEXT("barrel")&&A.Origin->ScriptName==Script;
}
}

bool DinkFamilyCollisionFit::ParsePolicy(const FString& Json,TArray<FDinkFamilyCollisionFitRule>& Out,FString& Error)
{
    Out.Reset();auto Fail=[&](const TCHAR* Why){Error=Why;return false;};
    TSharedPtr<FJsonObject> Root;FString Schema;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root)||!Root||
        !Root->TryGetStringField(TEXT("schema"),Schema)||Schema!=TEXT("dink-art-families/1"))return Fail(TEXT("family schema invalid"));
    if(!Root->HasField(TEXT("collision_fit"))){Error.Reset();return true;}
    const TSharedPtr<FJsonObject>* Policy=nullptr;
    if(!Root->TryGetObjectField(TEXT("collision_fit"),Policy)||!Policy||!Policy->IsValid()||
        !ExactFields(**Policy,{TEXT("schema"),TEXT("origins")})||
        !(*Policy)->TryGetStringField(TEXT("schema"),Schema)||Schema!=TEXT("dink-family-collision-fit/1"))return Fail(TEXT("fit policy schema invalid"));
    const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
    if(!(*Policy)->TryGetArrayField(TEXT("origins"),Rows)||Rows->IsEmpty()||Rows->Num()>2)return Fail(TEXT("one or two explicit audited origins required"));
    TArray<FDinkFamilyCollisionFitRule> Rules;TSet<FString> Seen;
    for(const auto& V:*Rows)
    {
        const TSharedPtr<FJsonObject>* O=nullptr;FString Id,Family,Anchor,Geometry,Raster;FDinkFamilyCollisionFitRule R;
        if(!V||!V->TryGetObject(O)||!O||!O->IsValid()||!ExactFields(**O,{TEXT("origin"),TEXT("family"),TEXT("mesh"),TEXT("geometry_sha1"),TEXT("anchor"),TEXT("geometry"),TEXT("raster")})||
            !(*O)->TryGetStringField(TEXT("origin"),Id)||!FDinkOriginId::Parse(Id,R.Origin)||R.Origin.ToString()!=Id||
            !DinkFamilyFit::ScopedOrigin(R.Origin.Screen,R.Origin.Placement)||Seen.Contains(Id)||
            !(*O)->TryGetStringField(TEXT("family"),Family)||Family!=TEXT("barrel")||
            !(*O)->TryGetStringField(TEXT("mesh"),R.Mesh)||R.Mesh!=BarrelMesh||
            !(*O)->TryGetStringField(TEXT("geometry_sha1"),R.GeometrySha1)||R.GeometrySha1.Len()!=40||
            !(*O)->TryGetStringField(TEXT("anchor"),Anchor)||Anchor!=TEXT("sprite_ground")||
            !(*O)->TryGetStringField(TEXT("geometry"),Geometry)||Geometry!=TEXT("cooked_complex")||
            !(*O)->TryGetStringField(TEXT("raster"),Raster)||Raster!=TEXT("cell_center"))return Fail(TEXT("fit rule is foreign, duplicate, incomplete or unreviewed"));
        for(TCHAR C:R.GeometrySha1)if(!FChar::IsHexDigit(C))return Fail(TEXT("invalid cooked geometry digest"));
        R.GeometrySha1=R.GeometrySha1.ToLower();Seen.Add(Id);Rules.Add(MoveTemp(R));
    }
    Out=MoveTemp(Rules);Error.Reset();return true;
}

bool DinkFamilyCollisionFit::ReadCookedGeometry(UStaticMesh& Mesh,FDinkFamilyFittedGeometry& Out,FString& Error)
{
    auto Fail=[&](const TCHAR* Why){Error=Why;return false;};
    UBodySetup* Body=Mesh.GetBodySetup();
    if(Mesh.GetPathName()!=BarrelMesh||!Body||Body->CollisionTraceFlag!=CTF_UseComplexAsSimple||Body->TriMeshGeometries.Num()!=1||!Body->TriMeshGeometries[0]||
        !Body->bCreatedPhysicsMeshes||Body->bFailedToCreatePhysicsMeshes||Body->bDoubleSidedGeometry)
        return Fail(TEXT("reviewed barrel actual cooked complex geometry unavailable; no implicit cook or UCX substitute"));
    const FBox Bounds=Mesh.GetBoundingBox();const FVector Size=Bounds.GetSize();
    if(!Bounds.IsValid||!Size.Equals(FVector(83.946647644,84.459892273,100.750007629),.01)||!FMath::IsNearlyZero(Bounds.Min.Z,.01))
        return Fail(TEXT("barrel render bounds differ from reviewed real-size source"));
    if(Body->AggGeom.ConvexElems.Num()!=1)return Fail(TEXT("retained authored UCX provenance changed"));
    const auto& UCX=Body->AggGeom.ConvexElems[0];
    if(UCX.VertexData.Num()!=8||!UCX.GetTransform().Equals(FTransform::Identity,0))return Fail(TEXT("authored UCX transform/vertices changed"));
    TSet<FString> Seen;
    for(const FVector& V:UCX.VertexData)
    {
        if(V.ContainsNaN()||!FMath::IsNearlyEqual(FMath::Abs(V.X),37.5,.001)||!FMath::IsNearlyEqual(FMath::Abs(V.Y),37.5,.001)||
            !(FMath::IsNearlyZero(V.Z,.001)||FMath::IsNearlyEqual(V.Z,100.,.001)))return Fail(TEXT("authored UCX differs from75x75x100 provenance"));
        Seen.Add(FString::Printf(TEXT("%d,%d,%d"),V.X>0,V.Y>0,V.Z>50));
    }
    if(Seen.Num()!=8)return Fail(TEXT("authored UCX duplicate corners"));
    FDinkFamilyFittedGeometry G;G.Mesh=&Mesh;G.BodySetup=Body;G.BodySetupGuid=Body->BodySetupGuid;
    G.bDoubleSided=Body->bDoubleSidedGeometry;G.RenderBounds=Bounds;G.AuthoredUCXVertices=UCX.VertexData;
    const auto& TriMesh=*Body->TriMeshGeometries[0];G.bCullsBackFaceRaycast=TriMesh.GetCullsBackFaceRaycast();FSHA1 Hash;
    const uint8 Cull=G.bCullsBackFaceRaycast?1:0;Hash.Update(&Cull,1);
    auto Read=[&](const auto& Rows)
    {
        for(const auto& I:Rows)
        {
            const int32 Base=G.Vertices.Num();
            for(int32 K=0;K<3;++K)
            {
                const FVector3f V(TriMesh.Particles().GetX(I[K]));
                if(V.ContainsNaN()||!Bounds.ExpandBy(.01).IsInsideOrOn(FVector(V)))return false;
                G.Vertices.Add(V);const float P[3]={V.X,V.Y,V.Z};Hash.Update(reinterpret_cast<const uint8*>(P),sizeof(P));
            }
            if(FVector3f::CrossProduct(G.Vertices[Base+1]-G.Vertices[Base],G.Vertices[Base+2]-G.Vertices[Base]).SizeSquared()==0)return false;
            const uint16 Material=TriMesh.GetMaterialIndex(G.Triangles.Num());
            Hash.Update(reinterpret_cast<const uint8*>(&Material),sizeof(Material));G.MaterialIndices.Add(Material);
            G.Triangles.Add(FIntVector(Base,Base+1,Base+2));
        }
        return !G.Triangles.IsEmpty();
    };
    const bool ReadOK=TriMesh.Elements().RequiresLargeIndices()?Read(TriMesh.Elements().GetLargeIndexBuffer()):Read(TriMesh.Elements().GetSmallIndexBuffer());
    if(!ReadOK)return Fail(TEXT("actual cooked triangles invalid, empty or outside reviewed bounds"));
    Hash.Final();uint8 Digest[20];Hash.GetHash(Digest);G.CookedGeometrySha1=BytesToHex(Digest,20).ToLower();
    Out=MoveTemp(G);Error.Reset();return true;
}

bool DinkFamilyCollisionFit::BuildFootprint(const FDinkFamilyFittedGeometry& G,const FTransform& Proposed,
    const FDinkScreenCorners& Corners,TArray<FVector2D>& Polygon,TArray<FIntPoint>& Cells,
    double& MinZ,double& MaxZ,double& BoundaryError,FString& Error)
{
    auto Fail=[&](const TCHAR* Why){Error=Why;return false;};
    if(G.SchemaVersion!=DescriptorSchemaVersion||Proposed.ContainsNaN()||!Proposed.GetScale3D().Equals(FVector::OneVector,0)||G.Vertices.IsEmpty()||G.Triangles.IsEmpty())
        return Fail(TEXT("only finite real-size cooked geometry transforms supported"));
    std::vector<DinkFamilyFit::Point> Points;double Low=MAX_dbl,High=-MAX_dbl;
    for(const auto& V:G.Vertices){const FVector W=Proposed.TransformPosition(FVector(V));Points.push_back({W.X,W.Y});Low=FMath::Min(Low,W.Z);High=FMath::Max(High,W.Z);}
    const auto Hull=DinkFamilyFit::ConvexHull(std::move(Points));
    auto C=[](FVector2D V){return DinkFamilyFit::Point{V.X*100,V.Y*100};};
    const DinkFamilyFit::Map Map{C(Corners.NW),C(Corners.NE),C(Corners.SW),C(Corners.SE)};
    if(!Hull||!DinkFamilyFit::ValidMap(Map)||High<=Low)return Fail(TEXT("invalid fitted footprint or map"));
    const auto ScreenHull=DinkFamilyFit::ConvexHull({Map.NW,Map.NE,Map.SW,Map.SE});
    if(!ScreenHull)return Fail(TEXT("screen hull invalid"));
    for(auto P:*Hull)if(!DinkFamilyFit::Inside(*ScreenHull,P))return Fail(TEXT("fitted body crosses screen boundary; explicit migration required"));
    const auto Raster=DinkFamilyFit::RasterizeCellCentres(Map,*Hull);
    if(!Raster)return Fail(TEXT("fitted footprint has no logical cells in this screen"));
    TArray<FVector2D> NewPolygon;TArray<FIntPoint> NewCells;
    for(auto P:*Hull)NewPolygon.Add(FVector2D(P.X,P.Y));
    for(auto P:*Raster)NewCells.Add(FIntPoint(P.X,P.Y));
    Polygon=MoveTemp(NewPolygon);Cells=MoveTemp(NewCells);MinZ=Low;MaxZ=High;
    BoundaryError=DinkFamilyFit::MaximumCellRadiusCm(Map);Error.Reset();return true;
}

bool UDinkArtFamilySubsystem::PrepareCollisionFit(const FDinkOriginId& Id,const FDinkFamilyFitSpriteState& Sprite,
    FDinkFamilyCollisionFitCandidate& Out,FString& Error) const
{
    auto Fail=[&](const TCHAR* Why){Error=Why;return false;};
    if(!IsInGameThread()||!bReady||bCollisionFitPolicyError||!GetWorld()||Sprite.Origin!=Id||!Eligible(Sprite)||!DinkFamilyFit::ScopedOrigin(Id.Screen,Id.Placement)||
        Precedence.Screens.Contains(Id.Screen)||Precedence.Origins.Contains(Id.ToString()))return Fail(TEXT("ineligible/unready/authored fit request"));
    const FDinkFamilyCollisionFitRule* Rule=nullptr;
    for(const auto& R:CollisionFitRules)if(R.Origin==Id){if(Rule)return Fail(TEXT("duplicate fit authority"));Rule=&R;}
    if(!Rule)return Fail(TEXT("no explicit opt-in fit policy; PR40/41 unchanged"));
    ADinkPlaceholderActor* Actor=nullptr;ADinkScreenVolume* Volume=nullptr;
    for(TActorIterator<ADinkPlaceholderActor> It(GetWorld());It;++It)if(It->Origin&&It->Origin->OriginId==Id)
    {if(Actor)return Fail(TEXT("ambiguous origin actor"));Actor=*It;}
    for(TActorIterator<ADinkScreenVolume> It(GetWorld());It;++It)if(It->ScreenNumber==Id.Screen)
    {if(Volume)return Fail(TEXT("ambiguous screen map"));Volume=*It;}
    if(!Actor||!Volume||Sprite.Actor.Get()!=Actor||!Actor->Origin||Sprite.ScriptName!=Actor->Origin->ScriptName||Actor->IsHidden()||!Actor->GetActorEnableCollision()||!ExpectedSource(*Actor,Id)||!Actor->ActorHasTag(FamilyTag)||Actor->ActorHasTag(TEXT("DinkAuthoredArt"))||
        !Actor->Card||!Actor->Card->bHiddenInGame||Actor->Card->GetCollisionEnabled()!=ECollisionEnabled::NoCollision||
        Actor->Card->CanEverAffectNavigation()||Actor->Card->GetGenerateOverlapEvents())return Fail(TEXT("actual audited family placement unavailable"));
    const FVector ScriptGround=DinkLayout::MapPixelToUnreal(Volume->Corners,Sprite.EngineX-20,Sprite.EngineY);
    if(!FVector2D(Actor->GetActorLocation().X,Actor->GetActorLocation().Y).Equals(FVector2D(ScriptGround.X,ScriptGround.Y),.05))
        return Fail(TEXT("current script coordinates and actual actor ground disagree"));
    UStaticMeshComponent* Family=nullptr;
    TInlineComponentArray<UStaticMeshComponent*> Components(Actor);
    for(auto* C:Components)if(C->ComponentHasTag(FamilyTag)){if(Family)return Fail(TEXT("ambiguous/shared family component"));Family=C;}
    const auto* Binding=DinkArtFamily::Resolve(Bindings,173,TEXT("barrel"));
    if(!Family||Family->Mobility!=EComponentMobility::Movable||!Family->IsRegistered()||!Family->GetStaticMesh()||Family->GetStaticMesh()->GetPathName()!=Rule->Mesh||
        !Binding||Binding->Mesh!=Rule->Mesh||Binding->Fit!=EDinkFamilyFit::None||!Binding->bScripted||Binding->bYawFromSprite||
        Family->GetAttachParent()!=Actor->GetRootComponent()||Family->GetCollisionEnabled()!=ECollisionEnabled::NoCollision||
        Family->CanEverAffectNavigation()||Family->GetGenerateOverlapEvents()||Family->bHiddenInGame||!Family->IsVisible())
        return Fail(TEXT("real-size exclusive noncolliding family binding changed"));
    FDinkFamilyCollisionFitCandidate C;C.Origin=Id;C.Sprite=Sprite;C.World=GetWorld();C.Actor=Actor;C.FamilyComponent=Family;C.Card=Actor->Card;
    C.BeforeCardMesh=Actor->Card->GetStaticMesh();C.Corners=Volume->Corners;C.BeforeActor=Actor->GetActorTransform();
    C.BeforeFamily=Family->GetComponentTransform();C.BeforeCard=Actor->Card->GetComponentTransform();
    C.BeforeMaterials=Materials(*Family);C.BeforeCardMaterials=Materials(*Actor->Card);C.SourceHash=Actor->Origin->SourceHash;C.ScriptName=Actor->Origin->ScriptName;
    C.BeforeProfile=Family->GetCollisionProfileName();C.BeforeResponses=Family->GetCollisionResponseToChannels();C.BeforeCollision=Family->GetCollisionEnabled();
    C.BeforeObjectType=Family->GetCollisionObjectType();C.BeforeNavigation=Family->CanEverAffectNavigation();C.BeforeOverlaps=Family->GetGenerateOverlapEvents();C.BeforeVisible=Family->IsVisible();C.BeforeActorCollision=Actor->GetActorEnableCollision();C.BeforeActorHidden=Actor->IsHidden();C.BeforeMobility=uint8(Family->Mobility);
    if(!DinkFamilyCollisionFit::ReadCookedGeometry(*Family->GetStaticMesh(),C.Geometry,Error))return false;
    if(C.Geometry.CookedGeometrySha1!=Rule->GeometrySha1)return Fail(TEXT("actual cooked geometry does not match reviewed policy digest"));
    const auto Rotation=Family->GetComponentQuat();
    if(!C.BeforeActor.GetScale3D().Equals(FVector::OneVector,0)||!C.BeforeFamily.GetScale3D().Equals(FVector::OneVector,0)||
        !FMath::IsNearlyZero(Rotation.Rotator().Pitch,.001)||!FMath::IsNearlyZero(Rotation.Rotator().Roll,.001))return Fail(TEXT("only upright unscaled barrel fit supported"));
    const FBox& B=C.Geometry.RenderBounds;const FVector Anchor(B.GetCenter().X,B.GetCenter().Y,B.Min.Z);
    // Original173/1 pivot41,44 is at the main barrel ground point. The whole
    // card's centre28 includes transparent left image margin and is not this anchor.
    C.ProposedWorld=FTransform(Rotation,Actor->GetActorLocation()-Rotation.RotateVector(Anchor),FVector::OneVector);
    if(!DinkFamilyCollisionFit::BuildFootprint(C.Geometry,C.ProposedWorld,C.Corners,C.WorldFootprint,C.LogicalCells,C.MinWorldZ,C.MaxWorldZ,C.MaximumRasterBoundaryErrorCm,Error))return false;
    Out=MoveTemp(C);Error.Reset();return true;
}

bool UDinkArtFamilySubsystem::ValidateCollisionFit(const FDinkFamilyCollisionFitCandidate& C,
    const FDinkFamilyFitSpriteState& Current,FString& Error) const
{
    auto Fail=[&](const TCHAR* Why){Error=Why;return false;};
    const auto* A=C.Actor.Get();const auto* F=C.FamilyComponent.Get();const auto* Card=C.Card.Get();
    if(!IsInGameThread()||C.SchemaVersion!=DinkFamilyCollisionFit::DescriptorSchemaVersion||C.Geometry.SchemaVersion!=DinkFamilyCollisionFit::DescriptorSchemaVersion||bCollisionFitPolicyError||C.World.Get()!=GetWorld()||!A||!F||!Card||!SameSprite(C.Sprite,Current)||!Eligible(Current)||!ExpectedSource(*A,C.Origin)||
        A->GetWorld()!=GetWorld()||A->GetActorEnableCollision()!=C.BeforeActorCollision||A->IsHidden()!=C.BeforeActorHidden||!A->GetActorTransform().Equals(C.BeforeActor,0)||A->Origin->SourceHash!=C.SourceHash||A->Origin->ScriptName!=C.ScriptName||
        !F->GetStaticMesh()||F->GetOwner()!=A||uint8(F->Mobility)!=C.BeforeMobility||F->GetAttachParent()!=A->GetRootComponent()||F->GetStaticMesh()!=C.Geometry.Mesh.Get()||F->GetStaticMesh()->GetBodySetup()!=C.Geometry.BodySetup.Get()||
        !F->GetComponentTransform().Equals(C.bVisualApplied?C.ProposedWorld:C.BeforeFamily,C.bVisualApplied?1.e-4:0.)||!F->IsRegistered()||
        F->GetCollisionProfileName()!=C.BeforeProfile||F->GetCollisionEnabled()!=C.BeforeCollision||F->GetCollisionObjectType()!=C.BeforeObjectType||
        F->GetCollisionResponseToChannels()!=C.BeforeResponses||F->CanEverAffectNavigation()!=C.BeforeNavigation||F->GetGenerateOverlapEvents()!=C.BeforeOverlaps||F->IsVisible()!=C.BeforeVisible||F->bHiddenInGame||
        Card!=A->Card.Get()||Card->GetCollisionEnabled()!=ECollisionEnabled::NoCollision||Card->CanEverAffectNavigation()||Card->GetGenerateOverlapEvents()||Card->GetStaticMesh()!=C.BeforeCardMesh.Get()||!Card->GetComponentTransform().Equals(C.BeforeCard,0)||!Card->bHiddenInGame||
        Materials(*F)!=C.BeforeMaterials||Materials(*Card)!=C.BeforeCardMaterials)return Fail(TEXT("fit candidate world/origin/frame/transform/material/policy became stale"));
    int32 Origins=0,FamilyComponents=0,Volumes=0;
    for(TActorIterator<ADinkPlaceholderActor> It(GetWorld());It;++It)if(It->Origin&&It->Origin->OriginId==C.Origin)++Origins;
    TInlineComponentArray<UStaticMeshComponent*> Components(A);for(auto* X:Components)if(X->ComponentHasTag(FamilyTag))++FamilyComponents;
    for(TActorIterator<ADinkScreenVolume> It(GetWorld());It;++It)if(It->ScreenNumber==C.Origin.Screen){++Volumes;if(!(It->Corners==C.Corners))return Fail(TEXT("screen corners changed"));}
    if(Origins!=1||FamilyComponents!=1||Volumes!=1||Precedence.Screens.Contains(C.Origin.Screen)||Precedence.Origins.Contains(C.Origin.ToString()))return Fail(TEXT("fit ownership/precedence became ambiguous"));
    FDinkFamilyFittedGeometry Actual;
    if(!DinkFamilyCollisionFit::ReadCookedGeometry(*F->GetStaticMesh(),Actual,Error))return false;
    if(Actual.BodySetupGuid!=C.Geometry.BodySetupGuid||Actual.CookedGeometrySha1!=C.Geometry.CookedGeometrySha1||
        Actual.Vertices!=C.Geometry.Vertices||Actual.Triangles!=C.Geometry.Triangles||Actual.MaterialIndices!=C.Geometry.MaterialIndices||Actual.bCullsBackFaceRaycast!=C.Geometry.bCullsBackFaceRaycast||Actual.AuthoredUCXVertices!=C.Geometry.AuthoredUCXVertices||
        Actual.bDoubleSided!=C.Geometry.bDoubleSided||!Actual.RenderBounds.Equals(C.Geometry.RenderBounds,0))return Fail(TEXT("actual cooked geometry identity changed"));
    const FBox& B=Actual.RenderBounds;const FQuat Rotation=C.BeforeFamily.GetRotation();
    const FTransform Expected(Rotation,A->GetActorLocation()-Rotation.RotateVector(FVector(B.GetCenter().X,B.GetCenter().Y,B.Min.Z)),FVector::OneVector);
    TArray<FVector2D> Polygon;TArray<FIntPoint> Cells;double Low=0,High=0,Boundary=0;
    if(!C.ProposedWorld.Equals(Expected,0)||!DinkFamilyCollisionFit::BuildFootprint(Actual,Expected,C.Corners,Polygon,Cells,Low,High,Boundary,Error)||
        Polygon!=C.WorldFootprint||Cells!=C.LogicalCells||Low!=C.MinWorldZ||High!=C.MaxWorldZ||Boundary!=C.MaximumRasterBoundaryErrorCm)
        return Fail(TEXT("prepared transform/footprint/height payload changed"));
    int32 PolicyFound=0;for(const auto& R:CollisionFitRules)if(R.Origin==C.Origin&&R.Mesh==F->GetStaticMesh()->GetPathName()&&R.GeometrySha1==Actual.CookedGeometrySha1)++PolicyFound;
    if(PolicyFound!=1)return Fail(TEXT("explicit unique reviewed fit policy no longer present"));
    Error.Reset();return true;
}

bool UDinkArtFamilySubsystem::ApplyCollisionFitVisual(FDinkFamilyCollisionFitCandidate& C,
    const FDinkFamilyFitSpriteState& Current,const IDinkFamilyFitVisualAuthority& Authority,FString& Error)
{
    if(Authority.GetSchemaVersion()!=DinkFamilyCollisionFit::DescriptorSchemaVersion){Error=TEXT("fit visual authority schema mismatch");return false;}
    if(!ValidateCollisionFit(C,Current,Error)||!Authority.CanPublishVisual(C,Error)||!ValidateCollisionFit(C,Current,Error))return false;
    // The authority must hold its gameplay loading gate and already bind the
    // matching mesh body/logical layer. No source origin or collision setter.
    C.FamilyComponent->SetWorldTransform(C.ProposedWorld,false,nullptr,ETeleportType::TeleportPhysics);
    C.bVisualApplied=true;
    if(!C.FamilyComponent->GetComponentTransform().Equals(C.ProposedWorld,1.e-4))
    {Error=TEXT("visual transform did not publish; coordinator must retain loading gate");return false;}
    Error.Reset();return true;
}
