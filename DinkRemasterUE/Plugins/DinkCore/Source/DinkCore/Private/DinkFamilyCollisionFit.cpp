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
bool IsSha1(const FString& Value)
{
    if (Value.Len() != 40) return false;
    for (TCHAR C : Value)
        if (!FChar::IsHexDigit(C)) return false;
    return true;
}
const FDinkFamilyCollisionFitRule* FindRule(
    const TArray<FDinkFamilyCollisionFitRule>& Rules, const FDinkOriginId& Origin)
{
    const FDinkFamilyCollisionFitRule* Match = nullptr;
    for (const auto& Rule : Rules)
    {
        if (Rule.Origin != Origin) continue;
        if (Match) return nullptr;
        Match = &Rule;
    }
    return Match;
}
bool Eligible(const FDinkFamilyFitSpriteState& S, const FDinkFamilyCollisionFitRule& Rule)
{
    const bool ValidHandle = S.bPrebirth
        ? S.RuntimeHandle == 0
        : !Rule.IsStaticBackground() && S.RuntimeHandle > 1 && S.RuntimeHandle != 1000;
    return S.SchemaVersion == DinkFamilyCollisionFit::DescriptorSchemaVersion &&
        S.Actor.IsValid() && S.Origin == Rule.Origin &&
        FMath::IsFinite(S.EngineX) && FMath::IsFinite(S.EngineY) &&
        S.ScriptName == Rule.SourceScript && ValidHandle &&
        S.CurrentScreen >= 1 && S.CurrentScreen <= 768 &&
        (!Rule.IsStaticBackground() || S.CurrentScreen == Rule.Origin.Screen) &&
        S.bActive && !(S.AnimationSequence == 173 && S.Brain == 5 && S.NoHit != 0) &&
        S.DisplayedSequence == 173 && S.DisplayedFrame == 1;
}
bool SameSprite(const FDinkFamilyFitSpriteState& A,const FDinkFamilyFitSpriteState& B)
{ return A.SchemaVersion==B.SchemaVersion&&A.Origin==B.Origin&&A.Actor==B.Actor&&A.SourceActor==B.SourceActor&&A.EngineX==B.EngineX&&A.EngineY==B.EngineY&&A.ScriptName==B.ScriptName&&A.RuntimeHandle==B.RuntimeHandle&&A.CurrentScreen==B.CurrentScreen&&A.bPrebirth==B.bPrebirth&&A.DisplayedSequence==B.DisplayedSequence&&A.DisplayedFrame==B.DisplayedFrame&&A.Hard==B.Hard&&A.Prop==B.Prop&&A.bActive==B.bActive&&A.AnimationSequence==B.AnimationSequence&&A.Brain==B.Brain&&A.NoHit==B.NoHit; }
TArray<TWeakObjectPtr<UMaterialInterface>> Materials(const UStaticMeshComponent& C)
{ TArray<TWeakObjectPtr<UMaterialInterface>> R;for(int32 I=0;I<C.GetNumMaterials();++I)R.Add(C.GetMaterial(I));return R; }
bool ExpectedSource(const ADinkPlaceholderActor& Actor, const FDinkFamilyCollisionFitRule& Rule)
{
    const auto* Origin = Actor.Origin.Get();
    if (!Origin || !IsSha1(Origin->SourceHash)) return false;
    if (!Rule.SourceHash.IsEmpty() &&
        (!Origin->SourceHash.Equals(Rule.SourceHash, ESearchCase::IgnoreCase) ||
         Origin->PlacementType != Rule.SourceType ||
         Actor.ActorHasTag(DinkFamilyCollisionFit::PromotedBackgroundTag) != Rule.IsStaticBackground()))
        return false;
    return Origin->OriginId == Rule.Origin && Actor.ScreenNumber == Rule.Origin.Screen &&
        Origin->Sequence == 173 && Origin->Frame == 1 && Origin->ClassId == TEXT("barrel") &&
        Origin->ScriptName == Rule.SourceScript;
}
bool SourceBinding(const ADinkPlaceholderActor& Actor, const ADinkPlaceholderActor& Source,
    const FDinkFamilyCollisionFitRule& Rule)
{
    if (!ExpectedSource(Source, Rule) || Actor.GetWorld() != Source.GetWorld() || !Actor.Origin)
        return false;
    if (&Actor == &Source) return Actor.Origin->OriginId == Rule.Origin;
    return !Rule.IsStaticBackground() &&
        Actor.ActorHasTag(TEXT("DinkRetainedLiveSprite")) && !Actor.Origin->OriginId.IsValid() &&
        Actor.Origin->ScriptName.IsNone() && Actor.Origin->SourceHash == Source.Origin->SourceHash &&
        Actor.Origin->Sequence == Source.Origin->Sequence && Actor.Origin->Frame == Source.Origin->Frame &&
        Actor.Origin->ClassId == Source.Origin->ClassId;
}
}

bool DinkFamilyCollisionFit::ParsePolicy(const FString& Json,TArray<FDinkFamilyCollisionFitRule>& Out,FString& Error)
{
    Out.Reset();auto Fail=[&](const TCHAR* Why){Error=Why;return false;};
    TSharedPtr<FJsonObject> Root;FString Schema;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root)||!Root||
        !Root->TryGetStringField(TEXT("schema"),Schema)||Schema!=TEXT("dink-art-families/1"))return Fail(TEXT("family schema invalid"));
    if(!Root->HasField(TEXT("collision_fit"))){Error.Reset();return true;}
    const TSharedPtr<FJsonObject>* Policy = nullptr;
    if (!Root->TryGetObjectField(TEXT("collision_fit"), Policy) || !Policy || !Policy->IsValid() ||
        !ExactFields(**Policy, {TEXT("schema"), TEXT("origins")}) ||
        !(*Policy)->TryGetStringField(TEXT("schema"), Schema))
        return Fail(TEXT("fit policy schema invalid"));
    const bool SourcePinned = Schema == TEXT("dink-family-collision-fit/2");
    if (!SourcePinned && Schema != TEXT("dink-family-collision-fit/1"))
        return Fail(TEXT("fit policy schema invalid"));

    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    if (!(*Policy)->TryGetArrayField(TEXT("origins"), Rows) || Rows->IsEmpty() ||
        Rows->Num() > (SourcePinned ? 85 : 2))
        return Fail(TEXT("fit policy requires an explicit bounded set of origins"));

    TArray<FDinkFamilyCollisionFitRule> Rules;
    TSet<FString> Seen;
    for (const auto& Value : *Rows)
    {
        const TSharedPtr<FJsonObject>* Object = nullptr;
        if (!Value || !Value->TryGetObject(Object) || !Object || !Object->IsValid())
            return Fail(TEXT("fit rule must be an object"));
        const FJsonObject& Row = **Object;
        if (SourcePinned
            ? !ExactFields(Row, {TEXT("origin"), TEXT("family"), TEXT("mesh"), TEXT("geometry_sha1"),
                TEXT("anchor"), TEXT("geometry"), TEXT("raster"), TEXT("source_hash"), TEXT("source_script"),
                TEXT("source_type"), TEXT("source_representation")})
            : !ExactFields(Row, {TEXT("origin"), TEXT("family"), TEXT("mesh"), TEXT("geometry_sha1"),
                TEXT("anchor"), TEXT("geometry"), TEXT("raster")}))
            return Fail(TEXT("fit rule fields do not match its schema"));

        FString Id, Family, Anchor, Geometry, Raster;
        FDinkFamilyCollisionFitRule Rule;
        if (!Row.TryGetStringField(TEXT("origin"), Id) || !FDinkOriginId::Parse(Id, Rule.Origin) ||
            !Rule.Origin.IsValid() || Rule.Origin.ToString() != Id ||
            Rule.Origin.Screen > 768 || Rule.Origin.Placement > 99 || Seen.Contains(Id) ||
            !Row.TryGetStringField(TEXT("family"), Family) || Family != TEXT("barrel") ||
            !Row.TryGetStringField(TEXT("mesh"), Rule.Mesh) || Rule.Mesh != BarrelMesh ||
            !Row.TryGetStringField(TEXT("geometry_sha1"), Rule.GeometrySha1) || !IsSha1(Rule.GeometrySha1) ||
            !Row.TryGetStringField(TEXT("anchor"), Anchor) || Anchor != TEXT("sprite_ground") ||
            !Row.TryGetStringField(TEXT("geometry"), Geometry) || Geometry != TEXT("cooked_complex") ||
            !Row.TryGetStringField(TEXT("raster"), Raster) || Raster != TEXT("cell_center"))
            return Fail(TEXT("fit rule is foreign, duplicate, incomplete or unreviewed"));

        if (SourcePinned)
        {
            static const TSet<FString> SupportedScripts = {TEXT(""), TEXT("bar-sh"), TEXT("bar-e"),
                TEXT("bar-f1"), TEXT("bar-dp"), TEXT("bar-sp"), TEXT("bar-gh")};
            FString Script, Representation;
            double Type = -1;
            if (!Row.TryGetStringField(TEXT("source_hash"), Rule.SourceHash) || !IsSha1(Rule.SourceHash) ||
                !Row.TryGetStringField(TEXT("source_script"), Script) ||
                !Row.HasTypedField<EJson::Number>(TEXT("source_type")) ||
                !Row.TryGetNumberField(TEXT("source_type"), Type) || (Type != 0 && Type != 1) ||
                !Row.TryGetStringField(TEXT("source_representation"), Representation) ||
                Representation != (Type == 0 ? TEXT("instance") : TEXT("actor")))
                return Fail(TEXT("fit rule source identity is invalid"));
            if (!SupportedScripts.Contains(Script) || (Type == 0 && !Script.IsEmpty() && Script != TEXT("bar-sh")))
                return Fail(TEXT("fit rule script does not match a supported source lifecycle"));
            Rule.SourceType = static_cast<int32>(Type);
            Rule.SourceScript = Script.IsEmpty() ? NAME_None : FName(*Script);
            Rule.SourceHash = Rule.SourceHash.ToLower();
        }
        else
        {
            if (!DinkFamilyFit::ScopedOrigin(Rule.Origin.Screen, Rule.Origin.Placement))
                return Fail(TEXT("legacy fit policy only accepts the original pair"));
            Rule.SourceScript = Rule.Origin.Screen == 31 ? FName(TEXT("bar-gh")) : FName(TEXT("bar-f1"));
        }
        Rule.GeometrySha1 = Rule.GeometrySha1.ToLower();
        Seen.Add(Id);
        Rules.Add(MoveTemp(Rule));
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
    const auto& TriMesh=*Body->TriMeshGeometries[0];G.bSourceCullsBackFaceRaycast=TriMesh.GetCullsBackFaceRaycast();G.bCullsBackFaceRaycast=!Body->bDoubleSidedGeometry;FSHA1 Hash;
    const uint8 Cull=G.bCullsBackFaceRaycast?1:0;Hash.Update(&Cull,1);
    // Diagnose the complete ACTUAL cooked mesh before refusing. Do not skip
    // faces, reconstruct collision, expand tolerance or publish partial output.
    const int32 ParticleCount=static_cast<int32>(TriMesh.Particles().Size());
    FBox CookedBounds(ForceInit);int32 NonfiniteParticles=0;
    for(int32 N=0;N<ParticleCount;++N)
    {
        const FVector V(TriMesh.Particles().GetX(N));
        if(V.ContainsNaN())++NonfiniteParticles;else CookedBounds+=V;
    }
    int32 BadIndices=0,NonfiniteReferenced=0,OutsideReferenced=0,ZeroArea=0;
    double MaximumBoundsExcess=0;FString FirstBad;
    auto Position=[](const FVector3f& V){return FString::Printf(TEXT("(%.9g,%.9g,%.9g)"),double(V.X),double(V.Y),double(V.Z));};
    auto Read=[&](const auto& Rows)
    {
        int32 TriangleNumber=0;
        for(const auto& I:Rows)
        {
            const int32 Number=TriangleNumber++;
            bool IndicesValid=true;
            for(int32 K=0;K<3;++K)if(static_cast<int64>(I[K])<0 || static_cast<int64>(I[K])>=ParticleCount)
                {++BadIndices;IndicesValid=false;}
            if(!IndicesValid)
            {
                if(FirstBad.IsEmpty())FirstBad=FString::Printf(TEXT("triangle=%d invalid indices=(%lld,%lld,%lld) particles=%d"),
                    Number,static_cast<long long>(I[0]),static_cast<long long>(I[1]),static_cast<long long>(I[2]),ParticleCount);
                continue;
            }
            const int32 Base=G.Vertices.Num();
            bool BadVertex=false;
            for(int32 K=0;K<3;++K)
            {
                const FVector3f V(TriMesh.Particles().GetX(I[K]));
                if(V.ContainsNaN()){++NonfiniteReferenced;BadVertex=true;}
                else
                {
                    if(!DinkFamilyFit::WithinCookedRenderEnvelope(
                        {double(V.X),double(V.Y),double(V.Z)},
                        {Bounds.Min.X,Bounds.Min.Y,Bounds.Min.Z},{Bounds.Max.X,Bounds.Max.Y,Bounds.Max.Z})){++OutsideReferenced;BadVertex=true;}
                    for(int32 Axis=0;Axis<3;++Axis)
                        MaximumBoundsExcess=FMath::Max(MaximumBoundsExcess,FMath::Max(
                            double(Bounds.Min[Axis])-double(V[Axis]),double(V[Axis])-double(Bounds.Max[Axis])));
                }
                G.Vertices.Add(V);const float P[3]={V.X,V.Y,V.Z};Hash.Update(reinterpret_cast<const uint8*>(P),sizeof(P));
            }
            const auto& A=G.Vertices[Base];const auto& B=G.Vertices[Base+1];const auto& C=G.Vertices[Base+2];
            const float FloatAreaSquared=FVector3f::CrossProduct(B-A,C-A).SizeSquared();
            const double DoubleAreaSquared=FVector::CrossProduct(FVector(B)-FVector(A),FVector(C)-FVector(A)).SizeSquared();
            if(FloatAreaSquared==0){++ZeroArea;BadVertex=true;}
            if(BadVertex&&FirstBad.IsEmpty())FirstBad=FString::Printf(
                TEXT("triangle=%d indices=(%lld,%lld,%lld) vertices=%s/%s/%s floatAreaSquared=%.17g doubleAreaSquared=%.17g"),
                Number,static_cast<long long>(I[0]),static_cast<long long>(I[1]),static_cast<long long>(I[2]),
                *Position(A),*Position(B),*Position(C),double(FloatAreaSquared),DoubleAreaSquared);
            const uint16 Material=TriMesh.GetMaterialIndex(Number);
            Hash.Update(reinterpret_cast<const uint8*>(&Material),sizeof(Material));G.MaterialIndices.Add(Material);
            G.Triangles.Add(FIntVector(Base,Base+1,Base+2));
        }
    };
    if(TriMesh.Elements().RequiresLargeIndices())Read(TriMesh.Elements().GetLargeIndexBuffer());
    else Read(TriMesh.Elements().GetSmallIndexBuffer());
    if(BadIndices||NonfiniteReferenced||OutsideReferenced||ZeroArea||G.Triangles.IsEmpty())
    {
        Error=FString::Printf(TEXT("actual cooked triangles REFUSED: envelopeCm=0.02 particles=%d triangles=%d nonfiniteParticles=%d invalidIndices=%d nonfiniteReferenced=%d outsideReferenced=%d zeroFloatArea=%d maxBoundsExcessCm=%.17g renderBounds=%s cookedBounds=%s firstBad={%s}"),
            ParticleCount,TriMesh.Elements().GetNumTriangles(),NonfiniteParticles,BadIndices,NonfiniteReferenced,
            OutsideReferenced,ZeroArea,MaximumBoundsExcess,*Bounds.ToString(),*CookedBounds.ToString(),*FirstBad);
        return false;
    }
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
{ return PrepareCollisionFitImpl(Id,Sprite,Out,Error,false); }

bool UDinkArtFamilySubsystem::PrepareCollisionFitImpl(const FDinkOriginId& Id,const FDinkFamilyFitSpriteState& Sprite,
    FDinkFamilyCollisionFitCandidate& Out,FString& Error,bool Release) const
{
    auto Fail=[&](const TCHAR* Why){Error=Why;return false;};
    if(!IsInGameThread()||!bReady||bCollisionFitPolicyError||!GetWorld()||Sprite.Origin!=Id||
        Precedence.Screens.Contains(Id.Screen)||Precedence.Origins.Contains(Id.ToString()))return Fail(TEXT("ineligible/unready/authored fit request"));
    const auto* Rule = FindRule(CollisionFitRules, Id);
    if (!Rule || !Eligible(Sprite, *Rule)) return Fail(TEXT("no eligible explicit opt-in fit policy"));
    ADinkPlaceholderActor* Actor=Sprite.Actor.Get();
    ADinkPlaceholderActor* Source=Sprite.SourceActor.IsValid()?Sprite.SourceActor.Get():Actor;ADinkScreenVolume* Volume=nullptr;
    if(!Actor||!Source||!SourceBinding(*Actor,*Source,*Rule)||Actor->ScreenNumber!=Sprite.CurrentScreen) return Fail(TEXT("explicit actor/source/current screen binding required"));
    for(TActorIterator<ADinkScreenVolume> It(GetWorld());It;++It)if(It->ScreenNumber==Sprite.CurrentScreen)
    {if(Volume)return Fail(TEXT("ambiguous screen map"));Volume=*It;}
    if(!Actor||!Volume||Sprite.Actor.Get()!=Actor||!Actor->Origin||Sprite.ScriptName!=Source->Origin->ScriptName||(!Sprite.bPrebirth&&(Actor->IsHidden()||!Actor->GetActorEnableCollision()))||!SourceBinding(*Actor,*Source,*Rule)||!Actor->ActorHasTag(FamilyTag)||Actor->ActorHasTag(TEXT("DinkAuthoredArt"))||
        !Actor->Card||(!Release&&!Actor->Card->bHiddenInGame)||Actor->Card->GetCollisionEnabled()!=ECollisionEnabled::NoCollision||
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
        Family->CanEverAffectNavigation()||Family->GetGenerateOverlapEvents()||(!Release&&(Family->bHiddenInGame||!Family->IsVisible())))
        return Fail(TEXT("real-size exclusive noncolliding family binding changed"));
    FDinkFamilyCollisionFitCandidate C;C.Origin=Id;C.Sprite=Sprite;C.World=GetWorld();C.Actor=Actor;C.SourceActor=Source;C.FamilyComponent=Family;C.Card=Actor->Card;
    C.bReleaseOnly=Release;C.BeforeFamilyHidden=Family->bHiddenInGame;C.BeforeCardHidden=Actor->Card->bHiddenInGame;C.BeforeCardVisible=Actor->Card->IsVisible();
    C.BeforeCardMesh=Actor->Card->GetStaticMesh();C.Corners=Volume->Corners;C.BeforeActor=Actor->GetActorTransform();
    C.BeforeFamily=Family->GetComponentTransform();C.BeforeCard=Actor->Card->GetComponentTransform();
    C.BeforeMaterials=Materials(*Family);C.BeforeCardMaterials=Materials(*Actor->Card);C.SourceHash=Source->Origin->SourceHash;C.ScriptName=Source->Origin->ScriptName;
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
    const auto* A=C.Actor.Get();const auto* Source=C.SourceActor.Get();const auto* F=C.FamilyComponent.Get();const auto* Card=C.Card.Get();
    if (!IsInGameThread()) return Fail(TEXT("fit validation requires the game thread"));
    const auto* Rule = FindRule(CollisionFitRules, C.Origin);
    if(C.SchemaVersion!=DinkFamilyCollisionFit::DescriptorSchemaVersion||C.Geometry.SchemaVersion!=DinkFamilyCollisionFit::DescriptorSchemaVersion||bCollisionFitPolicyError||C.World.Get()!=GetWorld()||!A||!Source||!F||!Card||!SameSprite(C.Sprite,Current)||!Rule||!Eligible(Current,*Rule)||!SourceBinding(*A,*Source,*Rule)||
        A->GetWorld()!=GetWorld()||
        !((A->GetActorEnableCollision()==C.BeforeActorCollision&&A->IsHidden()==C.BeforeActorHidden)||
          (C.Sprite.bPrebirth&&A->GetActorEnableCollision()&&!A->IsHidden()))||!A->GetActorTransform().Equals(C.BeforeActor,0)||Source->Origin->SourceHash!=C.SourceHash||Source->Origin->ScriptName!=C.ScriptName||
        !F->GetStaticMesh()||F->GetOwner()!=A||uint8(F->Mobility)!=C.BeforeMobility||F->GetAttachParent()!=A->GetRootComponent()||F->GetStaticMesh()!=C.Geometry.Mesh.Get()||F->GetStaticMesh()->GetBodySetup()!=C.Geometry.BodySetup.Get()||
        !F->GetComponentTransform().Equals(C.bVisualApplied?C.ProposedWorld:C.BeforeFamily,C.bVisualApplied?1.e-4:0.)||!F->IsRegistered()||
        F->GetCollisionProfileName()!=C.BeforeProfile||F->GetCollisionEnabled()!=C.BeforeCollision||F->GetCollisionObjectType()!=C.BeforeObjectType||
        F->GetCollisionResponseToChannels()!=C.BeforeResponses||F->CanEverAffectNavigation()!=C.BeforeNavigation||F->GetGenerateOverlapEvents()!=C.BeforeOverlaps||F->IsVisible()!=C.BeforeVisible||F->bHiddenInGame!=C.BeforeFamilyHidden||
        Card!=A->Card.Get()||Card->GetCollisionEnabled()!=ECollisionEnabled::NoCollision||Card->CanEverAffectNavigation()||Card->GetGenerateOverlapEvents()||Card->GetStaticMesh()!=C.BeforeCardMesh.Get()||!Card->GetComponentTransform().Equals(C.BeforeCard,0)||Card->bHiddenInGame!=C.BeforeCardHidden||Card->IsVisible()!=C.BeforeCardVisible||
        Materials(*F)!=C.BeforeMaterials||Materials(*Card)!=C.BeforeCardMaterials)return Fail(TEXT("fit candidate world/origin/frame/transform/material/policy became stale"));
    int32 FamilyComponents=0,Volumes=0;
    if(A->ScreenNumber!=Current.CurrentScreen)return Fail(TEXT("current owner screen changed"));
    TInlineComponentArray<UStaticMeshComponent*> Components(A);for(auto* X:Components)if(X->ComponentHasTag(FamilyTag))++FamilyComponents;
    for(TActorIterator<ADinkScreenVolume> It(GetWorld());It;++It)if(It->ScreenNumber==Current.CurrentScreen){++Volumes;if(!(It->Corners==C.Corners))return Fail(TEXT("screen corners changed"));}
    if(FamilyComponents!=1||Volumes!=1||Precedence.Screens.Contains(C.Origin.Screen)||Precedence.Origins.Contains(C.Origin.ToString()))return Fail(TEXT("fit ownership/precedence became ambiguous"));
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
    if (Rule->Mesh != F->GetStaticMesh()->GetPathName() || Rule->GeometrySha1 != Actual.CookedGeometrySha1)return Fail(TEXT("explicit unique reviewed fit policy no longer present"));
    Error.Reset();return true;
}

bool UDinkArtFamilySubsystem::ApplyCollisionFitVisual(FDinkFamilyCollisionFitCandidate& C,
    const FDinkFamilyFitSpriteState& Current,const IDinkFamilyFitVisualAuthority& Authority,FString& Error)
{
    if(C.bReleaseOnly||Authority.GetSchemaVersion()!=DinkFamilyCollisionFit::DescriptorSchemaVersion){Error=TEXT("fit visual authority schema/release mismatch");return false;}
    if(!ValidateCollisionFit(C,Current,Error)||!Authority.CanPublishVisual(C,Error)||!ValidateCollisionFit(C,Current,Error))return false;
    // The authority must hold its gameplay loading gate and already bind the
    // matching mesh body/logical layer. No source origin or collision setter.
    C.FamilyComponent->SetWorldTransform(C.ProposedWorld,false,nullptr,ETeleportType::TeleportPhysics);
    C.bVisualApplied=true;
    if(!C.FamilyComponent->GetComponentTransform().Equals(C.ProposedWorld,1.e-4))
    {Error=TEXT("visual transform did not publish; coordinator must retain loading gate");return false;}
    Error.Reset();return true;
}

bool UDinkArtFamilySubsystem::IsCollisionFitRequested(const FDinkOriginId& Origin) const
{
    for(const auto& Rule:CollisionFitRules)if(Rule.Origin==Origin)return true;
    return false;
}
bool UDinkArtFamilySubsystem::ReleaseCollisionFitVisual(const FDinkFamilyCollisionFitCandidate& C,
    const FDinkFamilyFitSpriteState& Current,const IDinkFamilyFitVisualAuthority& Authority,FString& Error)
{
    if(Authority.GetSchemaVersion()!=DinkFamilyCollisionFit::DescriptorSchemaVersion ||
       Current.Actor!=C.Actor || Current.Origin!=C.Origin || Current.CurrentScreen!=C.Sprite.CurrentScreen ||
       !Authority.CanReleaseVisual(C,Current,Error))return false;
    // Snapshot validation pins source/mesh/policy; runtime hard/frame may have
    // deliberately changed. Caller owns the current frame's card presentation.
    auto Prior=C;Prior.bVisualApplied=true;
    if(!ValidateCollisionFit(Prior,Prior.Sprite,Error))
    {
        Prior.bVisualApplied=false;
        if(!ValidateCollisionFit(Prior,Prior.Sprite,Error))
        {
            FDinkFamilyCollisionFitCandidate Released;
            if(!C.FamilyComponent.IsValid() || !C.Card.IsValid() || !C.FamilyComponent->bHiddenInGame ||
               C.FamilyComponent->IsVisible() || C.Card->bHiddenInGame || !C.Card->IsVisible() ||
               !PrepareCollisionFitReleaseCandidate(C.Origin,Current,Released,Error) ||
               Released.Geometry.CookedGeometrySha1!=C.Geometry.CookedGeometrySha1 || Released.SourceHash!=C.SourceHash)return false;
            Error.Reset();return true; // already-published broken presentation
        }
    }
    C.FamilyComponent->SetVisibility(false);C.FamilyComponent->SetHiddenInGame(true);
    C.Card->SetVisibility(true);C.Card->SetHiddenInGame(false);
    Error.Reset();return true;
}

bool UDinkArtFamilySubsystem::PrepareCollisionFitReleaseCandidate(const FDinkOriginId& Origin,
    const FDinkFamilyFitSpriteState& Current,FDinkFamilyCollisionFitCandidate& Out,FString& Error) const
{
    if(Current.Origin!=Origin || !Current.Actor.IsValid() ||
       !((Current.DisplayedSequence==173 && Current.DisplayedFrame==6) ||
         (Current.AnimationSequence==173 && Current.Brain==5 && Current.NoHit!=0)))
    {Error=TEXT("release candidate requires an actually removed/broken original barrel");return false;}
    // This qualifies source geometry/presentation ONLY. It never enters a body
    // request: the consumer must use actual Current for CanReleaseVisual.
    auto Source=Current;Source.Hard=0;Source.bActive=true;Source.DisplayedSequence=173;Source.DisplayedFrame=1;Source.AnimationSequence=0;Source.Brain=0;Source.NoHit=0;
    if(!PrepareCollisionFitImpl(Origin,Source,Out,Error,true))return false;
    Out.bReleaseOnly=true;return true;
}
