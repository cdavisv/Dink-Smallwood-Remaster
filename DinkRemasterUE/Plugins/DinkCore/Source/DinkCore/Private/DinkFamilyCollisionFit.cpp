#include "Hardness/DinkFamilyCollisionFit.h"
#include "Hardness/DinkFamilyFitMath.h"
#include "Hardness/DinkCanonicalSurface.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "Engine/Texture2D.h"
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
const FString PhotoBarrelMesh(TEXT("/Game/Dink/Props/Stonebrook/PhotorealBarrelV1/SM_Barrel_Oak_01.SM_Barrel_Oak_01"));
const FString SurfaceAlgorithm(TEXT("DinkOrientedTrianglesF32LEMaterialU16LE/1"));
const FString PhotoSurfaceSha1(TEXT("de0f514e0172077e7bbd9dc0b30c75f5c40939e6"));
bool PolicyGeometryMatches(const FDinkFamilyCollisionFitRule& Rule, const FDinkFamilyFittedGeometry& Geometry)
{
    return Rule.CanonicalSurfaceSha1.IsEmpty()
        ? Rule.GeometrySha1 == Geometry.CookedGeometrySha1
        : Rule.CanonicalSurfaceSha1 == Geometry.CanonicalSurfaceSha1;
}
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
    const bool Canonical = Schema == TEXT("dink-family-collision-fit/3");
    const bool SourcePinned = Canonical || Schema == TEXT("dink-family-collision-fit/2");
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
        if (Canonical
            ? !ExactFields(Row, {TEXT("origin"), TEXT("family"), TEXT("mesh"), TEXT("surface_sha1"),
                TEXT("surface_algorithm"), TEXT("anchor"), TEXT("geometry"), TEXT("raster"), TEXT("source_hash"),
                TEXT("source_script"), TEXT("source_type"), TEXT("source_representation")})
            : SourcePinned ? !ExactFields(Row, {TEXT("origin"), TEXT("family"), TEXT("mesh"), TEXT("geometry_sha1"),
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
            !Row.TryGetStringField(TEXT("mesh"), Rule.Mesh) || Rule.Mesh != (Canonical ? PhotoBarrelMesh : BarrelMesh) ||
            !Row.TryGetStringField(TEXT("anchor"), Anchor) || Anchor != TEXT("sprite_ground") ||
            !Row.TryGetStringField(TEXT("geometry"), Geometry) || Geometry != TEXT("cooked_complex") ||
            !Row.TryGetStringField(TEXT("raster"), Raster) || Raster != TEXT("cell_center"))
            return Fail(TEXT("fit rule is foreign, duplicate, incomplete or unreviewed"));

        if (Canonical)
        {
            FString Algorithm;
            if (!Row.TryGetStringField(TEXT("surface_algorithm"), Algorithm) || Algorithm != SurfaceAlgorithm ||
                !Row.TryGetStringField(TEXT("surface_sha1"), Rule.CanonicalSurfaceSha1) ||
                Rule.CanonicalSurfaceSha1 != PhotoSurfaceSha1)
                return Fail(TEXT("unreviewed canonical photoreal surface contract"));
        }
        else if (!Row.TryGetStringField(TEXT("geometry_sha1"), Rule.GeometrySha1) || !IsSha1(Rule.GeometrySha1))
            return Fail(TEXT("legacy ordered cooked digest invalid"));

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
    if((Mesh.GetPathName()!=BarrelMesh && Mesh.GetPathName()!=PhotoBarrelMesh)||!Body||Body->CollisionTraceFlag!=CTF_UseComplexAsSimple||Body->TriMeshGeometries.Num()!=1||!Body->TriMeshGeometries[0]||
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
    if (Mesh.GetPathName() == PhotoBarrelMesh && G.Triangles.Num() != 16648)
        return Fail(TEXT("approved photoreal collision must retain all16648 source triangles"));
    std::vector<DinkCanonicalSurface::Triangle> Surface;
    Surface.reserve(G.Triangles.Num());
    for (int32 Index = 0; Index < G.Triangles.Num(); ++Index)
    {
        DinkCanonicalSurface::Triangle Triangle;
        const auto& Indices = G.Triangles[Index];
        for (int32 Corner = 0; Corner < 3; ++Corner)
        {
            const auto& Vertex = G.Vertices[Indices[Corner]];
            Triangle.Points[Corner] = {Vertex.X, Vertex.Y, Vertex.Z};
        }
        Triangle.Material = G.MaterialIndices[Index];
        Surface.push_back(Triangle);
    }
    const auto CanonicalBytes = DinkCanonicalSurface::Bytes(Surface, G.bCullsBackFaceRaycast);
    FSHA1::HashBuffer(CanonicalBytes.data(), CanonicalBytes.size(), Digest);
    G.CanonicalSurfaceSha1 = BytesToHex(Digest, 20).ToLower();
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

namespace
{
bool PublishedReleaseMatches(const ADinkPlaceholderActor& Actor,const FDinkFamilyCollisionFitCandidate& W,
    const FDinkLegacyPictureDescriptor& SourcePicture,FString& Error)
{
    const auto* Card=Actor.Card.Get();const auto* Source=W.SourceActor.Get();
    if(!DinkFamilyCollisionFit::ValidatePictureDescriptor(SourcePicture)||
       !Actor.bHasImportedCardBaseline||!Actor.bHasPublishedLegacyPicture||
       Actor.PublishedLegacyReleaseWitness.Get()!=&W||W.Actor.Get()!=&Actor||W.World.Get()!=Actor.GetWorld()||W.Card.Get()!=Card||
       !Card||!Actor.Origin||!Source||!Source->Origin||W.Origin!=Source->Origin->OriginId||Source->Origin->SourceHash!=W.SourceHash||
       Source->Origin->ScriptName!=W.ScriptName||
       !W.BeforeCardMesh.IsValid()||Card->GetStaticMesh()!=W.BeforeCardMesh.Get()||Card->GetAttachParent()!=Actor.GetRootComponent()||
       !Card->GetAttachSocketName().IsNone()||Card->IsUsingAbsoluteLocation()||Card->IsUsingAbsoluteRotation()||Card->IsUsingAbsoluteScale()||
       !Actor.ImportedCardRelativeTransform.Equals(W.ImportedCardBaseline,0)||
       !Actor.PublishedImportedCardBaseline.Equals(W.ImportedCardBaseline,0)||
       SourcePicture.Sha1!=W.Sprite.SourcePicture.Sha1||Actor.PublishedSourcePictureSha1!=W.Sprite.SourcePicture.Sha1||
       !Actor.PublishedLegacyCardRelative.Equals(W.ReleaseCardRelative,0)||
       !Card->GetRelativeTransform().GetTranslation().Equals(W.ReleaseCardRelative.GetTranslation(),0)||
       !Card->GetRelativeTransform().GetScale3D().Equals(W.ReleaseCardRelative.GetScale3D(),0)||
       !Card->GetComponentQuat().GetUpVector().Equals(FVector::UpVector,0)||
       !W.ReleaseMaterial||Actor.PublishedLegacyCardMaterial!=W.ReleaseMaterial->Get()||Card->GetMaterial(0)!=W.ReleaseMaterial->Get())
    {Error=TEXT("published release identity/geometry/baseline witness changed");return false;}
    return DinkFamilyCollisionFit::ValidateReleasedPictureAssets(W,Error);
}
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
        !Actor->Card||Actor->Card->GetAttachParent()!=Actor->GetRootComponent()||!Actor->Card->GetAttachSocketName().IsNone()||
        Actor->Card->IsUsingAbsoluteLocation()||Actor->Card->IsUsingAbsoluteRotation()||Actor->Card->IsUsingAbsoluteScale()||Actor->Card->GetCollisionEnabled()!=ECollisionEnabled::NoCollision||
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
        Family->CanEverAffectNavigation()||Family->GetGenerateOverlapEvents())
        return Fail(TEXT("real-size exclusive noncolliding family binding changed"));
    if(Actor->bHasPublishedLegacyPicture!=Actor->PublishedLegacyReleaseWitness.IsValid())
        return Fail(TEXT("published release flag/witness disagree"));
    if(Actor->PublishedLegacyReleaseWitness)
    {
        if(Actor->PublishedLegacyReleaseWitness->FamilyComponent.Get()!=Family||Actor->PublishedLegacyReleaseWitness->SourceActor.Get()!=Source)
            return Fail(TEXT("published release family/source identity changed"));
        if(!PublishedReleaseMatches(*Actor,*Actor->PublishedLegacyReleaseWitness,Sprite.SourcePicture,Error))return false;
    }
    if(!Release)
    {
        const bool IntactPresentation=Actor->Card->bHiddenInGame&&!Family->bHiddenInGame&&Family->IsVisible();
        const bool RestoringPrebirth=Sprite.bPrebirth&&Actor==Source&&Actor->Card->IsVisible()&&
            !Actor->Card->bHiddenInGame&&Family->bHiddenInGame&&!Family->IsVisible();
        const bool RestoringPublished=Actor->PublishedLegacyReleaseWitness.IsValid()&&Actor->Card->IsVisible()&&
            !Actor->Card->bHiddenInGame&&Family->bHiddenInGame&&!Family->IsVisible();
        if(!IntactPresentation&&!RestoringPrebirth&&!RestoringPublished)return Fail(TEXT("unexpected fitted family presentation"));
    }
    FDinkFamilyCollisionFitCandidate C;C.Origin=Id;C.Sprite=Sprite;C.World=GetWorld();C.Actor=Actor;C.SourceActor=Source;C.FamilyComponent=Family;C.Card=Actor->Card;
    C.RestoreReleaseWitness=Actor->PublishedLegacyReleaseWitness;
    C.bReleaseOnly=Release;C.BeforeFamilyHidden=Family->bHiddenInGame;C.BeforeCardHidden=Actor->Card->bHiddenInGame;C.BeforeCardVisible=Actor->Card->IsVisible();
    C.BeforeCardMesh=Actor->Card->GetStaticMesh();C.Corners=Volume->Corners;C.BeforeActor=Actor->GetActorTransform();
    C.BeforeFamily=Family->GetComponentTransform();C.BeforeCard=Actor->Card->GetComponentTransform();
    C.ImportedCardBaseline=Actor->ImportedCardRelativeTransform;C.bImportedCardBaselinePresent=Actor->bHasImportedCardBaseline;
    C.BeforeMaterials=Materials(*Family);C.BeforeCardMaterials=Materials(*Actor->Card);C.SourceHash=Source->Origin->SourceHash;C.ScriptName=Source->Origin->ScriptName;
    C.BeforeProfile=Family->GetCollisionProfileName();C.BeforeResponses=Family->GetCollisionResponseToChannels();C.BeforeCollision=Family->GetCollisionEnabled();
    C.BeforeObjectType=Family->GetCollisionObjectType();C.BeforeNavigation=Family->CanEverAffectNavigation();C.BeforeOverlaps=Family->GetGenerateOverlapEvents();C.BeforeVisible=Family->IsVisible();C.BeforeActorCollision=Actor->GetActorEnableCollision();C.BeforeActorHidden=Actor->IsHidden();C.BeforeMobility=uint8(Family->Mobility);
    if(!DinkFamilyCollisionFit::ReadCookedGeometry(*Family->GetStaticMesh(),C.Geometry,Error))return false;
    if(!PolicyGeometryMatches(*Rule,C.Geometry))return Fail(TEXT("actual cooked geometry does not match reviewed policy digest"));
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
        A->GetWorld()!=GetWorld()||A->bHasImportedCardBaseline!=C.bImportedCardBaselinePresent||
        !A->ImportedCardRelativeTransform.Equals(C.ImportedCardBaseline,0)||
        !((A->GetActorEnableCollision()==C.BeforeActorCollision&&A->IsHidden()==C.BeforeActorHidden)||
          (C.Sprite.bPrebirth&&A->GetActorEnableCollision()&&!A->IsHidden()))||!A->GetActorTransform().Equals(C.BeforeActor,0)||Source->Origin->SourceHash!=C.SourceHash||Source->Origin->ScriptName!=C.ScriptName||
        !F->GetStaticMesh()||F->GetOwner()!=A||uint8(F->Mobility)!=C.BeforeMobility||F->GetAttachParent()!=A->GetRootComponent()||F->GetStaticMesh()!=C.Geometry.Mesh.Get()||F->GetStaticMesh()->GetBodySetup()!=C.Geometry.BodySetup.Get()||
        !F->GetComponentTransform().Equals(C.bVisualApplied?C.ProposedWorld:C.BeforeFamily,C.bVisualApplied?1.e-4:0.)||!F->IsRegistered()||
        F->GetCollisionProfileName()!=C.BeforeProfile||F->GetCollisionEnabled()!=C.BeforeCollision||F->GetCollisionObjectType()!=C.BeforeObjectType||
        F->GetCollisionResponseToChannels()!=C.BeforeResponses||F->CanEverAffectNavigation()!=C.BeforeNavigation||F->GetGenerateOverlapEvents()!=C.BeforeOverlaps||F->IsVisible()!=(C.bVisualApplied?true:C.BeforeVisible)||F->bHiddenInGame!=(C.bVisualApplied?false:C.BeforeFamilyHidden)||
        Card!=A->Card.Get()||Card->GetAttachParent()!=A->GetRootComponent()||!Card->GetAttachSocketName().IsNone()||
        Card->IsUsingAbsoluteLocation()||Card->IsUsingAbsoluteRotation()||Card->IsUsingAbsoluteScale()||Card->GetCollisionEnabled()!=ECollisionEnabled::NoCollision||Card->CanEverAffectNavigation()||Card->GetGenerateOverlapEvents()||Card->GetStaticMesh()!=C.BeforeCardMesh.Get()||!Card->GetComponentTransform().Equals(C.BeforeCard,0)||Card->bHiddenInGame!=(C.bVisualApplied?true:C.BeforeCardHidden)||Card->IsVisible()!=(!C.bVisualApplied&&C.BeforeCardVisible)||
        Materials(*F)!=C.BeforeMaterials||Materials(*Card)!=C.BeforeCardMaterials)
    {
        if(A&&F&&Card)
        {
            Error=FString::Printf(TEXT("fit candidate stale: applied=%d actor_hidden=%d/%d actor_collision=%d/%d actor_pose=%d family_pose=%d family_visible=%d/%d family_hidden=%d/%d card_pose=%d card_visible=%d/%d card_hidden=%d/%d card_mesh=%d family_materials=%d card_materials=%d"),
                C.bVisualApplied,A->IsHidden(),C.BeforeActorHidden,A->GetActorEnableCollision(),C.BeforeActorCollision,
                A->GetActorTransform().Equals(C.BeforeActor,0),
                F->GetComponentTransform().Equals(C.bVisualApplied?C.ProposedWorld:C.BeforeFamily,C.bVisualApplied?1.e-4:0.),
                F->IsVisible(),C.bVisualApplied||C.BeforeVisible,F->bHiddenInGame,!C.bVisualApplied&&C.BeforeFamilyHidden,
                Card->GetComponentTransform().Equals(C.BeforeCard,0),Card->IsVisible(),!C.bVisualApplied&&C.BeforeCardVisible,
                Card->bHiddenInGame,C.bVisualApplied||C.BeforeCardHidden,Card->GetStaticMesh()==C.BeforeCardMesh.Get(),
                Materials(*F)==C.BeforeMaterials,Materials(*Card)==C.BeforeCardMaterials);
            return false;
        }
        return Fail(TEXT("fit candidate world, actor or component no longer valid"));
    }
    if(A->bHasPublishedLegacyPicture!=A->PublishedLegacyReleaseWitness.IsValid()||
       C.RestoreReleaseWitness!=A->PublishedLegacyReleaseWitness)return Fail(TEXT("prepared published release witness changed"));
    if(C.RestoreReleaseWitness&&(!A->PublishedLegacyReleaseWitness.IsValid()||
       C.RestoreReleaseWitness!=A->PublishedLegacyReleaseWitness||C.RestoreReleaseWitness->Origin!=C.Origin||
       !PublishedReleaseMatches(*A,*C.RestoreReleaseWitness,Current.SourcePicture,Error)))return false;
    int32 FamilyComponents=0,Volumes=0;
    if(A->ScreenNumber!=Current.CurrentScreen)return Fail(TEXT("current owner screen changed"));
    TInlineComponentArray<UStaticMeshComponent*> Components(A);for(auto* X:Components)if(X->ComponentHasTag(FamilyTag))++FamilyComponents;
    for(TActorIterator<ADinkScreenVolume> It(GetWorld());It;++It)if(It->ScreenNumber==Current.CurrentScreen){++Volumes;if(!(It->Corners==C.Corners))return Fail(TEXT("screen corners changed"));}
    if(FamilyComponents!=1||Volumes!=1||Precedence.Screens.Contains(C.Origin.Screen)||Precedence.Origins.Contains(C.Origin.ToString()))return Fail(TEXT("fit ownership/precedence became ambiguous"));
    FDinkFamilyFittedGeometry Actual;
    if(!DinkFamilyCollisionFit::ReadCookedGeometry(*F->GetStaticMesh(),Actual,Error))return false;
    if(Actual.BodySetupGuid!=C.Geometry.BodySetupGuid||Actual.CookedGeometrySha1!=C.Geometry.CookedGeometrySha1||
        Actual.CanonicalSurfaceSha1!=C.Geometry.CanonicalSurfaceSha1||
        Actual.Vertices!=C.Geometry.Vertices||Actual.Triangles!=C.Geometry.Triangles||Actual.MaterialIndices!=C.Geometry.MaterialIndices||Actual.bCullsBackFaceRaycast!=C.Geometry.bCullsBackFaceRaycast||Actual.AuthoredUCXVertices!=C.Geometry.AuthoredUCXVertices||
        Actual.bDoubleSided!=C.Geometry.bDoubleSided||!Actual.RenderBounds.Equals(C.Geometry.RenderBounds,0))return Fail(TEXT("actual cooked geometry identity changed"));
    const FBox& B=Actual.RenderBounds;const FQuat Rotation=C.BeforeFamily.GetRotation();
    const FTransform Expected(Rotation,A->GetActorLocation()-Rotation.RotateVector(FVector(B.GetCenter().X,B.GetCenter().Y,B.Min.Z)),FVector::OneVector);
    TArray<FVector2D> Polygon;TArray<FIntPoint> Cells;double Low=0,High=0,Boundary=0;
    if(!C.ProposedWorld.Equals(Expected,0)||!DinkFamilyCollisionFit::BuildFootprint(Actual,Expected,C.Corners,Polygon,Cells,Low,High,Boundary,Error)||
        Polygon!=C.WorldFootprint||Cells!=C.LogicalCells||Low!=C.MinWorldZ||High!=C.MaxWorldZ||Boundary!=C.MaximumRasterBoundaryErrorCm)
        return Fail(TEXT("prepared transform/footprint/height payload changed"));
    if (Rule->Mesh != F->GetStaticMesh()->GetPathName() || !PolicyGeometryMatches(*Rule,Actual))return Fail(TEXT("explicit unique reviewed fit policy no longer present"));
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
    // An intact save can reuse the original actor after the broken card was
    // exposed. Restore the fitted presentation only after body admission.
    C.FamilyComponent->SetVisibility(true);
    C.FamilyComponent->SetHiddenInGame(false);
    C.Card->SetVisibility(false);
    C.Card->SetHiddenInGame(true);
    C.bVisualApplied=true;
    if(!C.FamilyComponent->GetComponentTransform().Equals(C.ProposedWorld,1.e-4)||
       !C.FamilyComponent->IsVisible()||C.FamilyComponent->bHiddenInGame||
       C.Card->IsVisible()||!C.Card->bHiddenInGame)
    {Error=TEXT("fitted presentation did not publish; coordinator must retain loading gate");return false;}
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
    if(!C.bReleasePicturePrepared||!C.ReleaseMaterial||!C.ReleaseMaterial->IsValid()||
       Current.DisplayedSequence!=C.ReleasePicture.Sequence||Current.DisplayedFrame!=C.ReleasePicture.Frame||
       Current.DisplayedPicture.Sha1!=C.ReleasePicture.Sha1||!DinkFamilyCollisionFit::ValidatePictureDescriptor(Current.DisplayedPicture)||
       Current.SourcePicture.Sha1!=C.Sprite.SourcePicture.Sha1)
    {Error=TEXT("effective legacy picture was not preflighted before fit release");return false;}
    if(!DinkFamilyCollisionFit::ValidateReleasedPictureAssets(C,Error))return false;
    // Exact prepublication snapshots remain authoritative; a changed card/material is never repaired silently.
    auto Prior=C;Prior.bVisualApplied=true;
    if(!ValidateCollisionFit(Prior,Prior.Sprite,Error))
    {
        Prior.bVisualApplied=false;
        if(!ValidateCollisionFit(Prior,Prior.Sprite,Error))return false;
    }
    auto* Card=C.Card.Get();auto* Family=C.FamilyComponent.Get();auto* Actor=C.Actor.Get();
    auto* Parent=Actor->GetRootComponent();
    const auto SupportedParent=[&](){return Parent&&Actor->GetRootComponent()==Parent&&Card->GetAttachParent()==Parent&&
        Card->GetAttachSocketName().IsNone()&&!Card->IsUsingAbsoluteLocation()&&!Card->IsUsingAbsoluteRotation()&&!Card->IsUsingAbsoluteScale();};
    if(!SupportedParent()){Error=TEXT("released card requires actor-root parent/no socket/no absolute channels");return false;}
    const FTransform ParentWorld=Parent->GetComponentTransform();
    const FTransform RequestedWorld=C.ReleaseCardRelative*ParentWorld; // BEFORE mobility/pose setters.
    // Construct only the retained picture epoch, not cooked geometry/cells or a recursive restore chain.
    auto Witness=MakeShared<FDinkFamilyCollisionFitCandidate>();
    Witness->Origin=C.Origin;Witness->World=C.World;Witness->Actor=C.Actor;Witness->SourceActor=C.SourceActor;Witness->Card=C.Card;Witness->FamilyComponent=C.FamilyComponent;
    Witness->BeforeCardMesh=C.BeforeCardMesh;Witness->SourceHash=C.SourceHash;Witness->ScriptName=C.ScriptName;
    Witness->bImportedCardBaselinePresent=C.bImportedCardBaselinePresent;Witness->ImportedCardBaseline=C.ImportedCardBaseline;Witness->Sprite.SourcePicture=C.Sprite.SourcePicture;
    Witness->ReleasePicture=C.ReleasePicture;Witness->bReleasePicturePrepared=C.bReleasePicturePrepared;
    Witness->ReleaseMaterial=C.ReleaseMaterial;Witness->ReleaseTexture=C.ReleaseTexture;
    Witness->SourcePictureMaterial=C.SourcePictureMaterial;Witness->SourcePictureTexture=C.SourcePictureTexture;
    // All validation/allocation is complete before publication. Resolve geometry/material BEFORE exposing the card.
    // Registered imported cards can still be Static after hidden-card billboarding was skipped.
    // This is presentation-only: existing strict NoCollision/navigation/overlap guards already passed.
    if(Card->Mobility!=EComponentMobility::Movable)Card->SetMobility(EComponentMobility::Movable);
    Card->SetRelativeTransform(C.ReleaseCardRelative,false,nullptr,ETeleportType::TeleportPhysics);
    Card->SetMaterial(0,C.ReleaseMaterial->Get());
    const auto WorldMatches=[&](){return SupportedParent()&&Parent->GetComponentTransform().Equals(ParentWorld,0)&&
        Card->GetComponentTransform().Equals(RequestedWorld,0)&&Card->GetMaterial(0)==C.ReleaseMaterial->Get();};
    if(!WorldMatches()){Error=TEXT("effective legacy picture world/parent/material publication failed; retain loading gate");return false;}
    Family->SetVisibility(false);Family->SetHiddenInGame(true);
    Card->SetVisibility(true);Card->SetHiddenInGame(false);
    if(!WorldMatches()||!Card->IsVisible()||Card->bHiddenInGame||Family->IsVisible()||!Family->bHiddenInGame)
    {Error=TEXT("effective legacy picture publication failed; retain loading gate");return false;}
    // Stock setters can round-trip local coordinates while producing the EXACT requested world pose.
    // Freeze the observed relative epoch, never the unrepresentable ideal local request.
    Actor->PublishedLegacyCardRelative=Card->GetRelativeTransform();
    Actor->PublishedLegacyCardMaterial=C.ReleaseMaterial->Get();
    Actor->PublishedImportedCardBaseline=C.ImportedCardBaseline;Actor->PublishedSourcePictureSha1=C.Sprite.SourcePicture.Sha1;
    Witness->ReleaseCardRelative=Card->GetRelativeTransform();
    Actor->PublishedLegacyReleaseWitness=Witness;
    Actor->bHasPublishedLegacyPicture=true;
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
    auto Source=Current;Source.Hard=0;Source.bActive=true;
    const auto* SourceActor=Current.SourceActor.IsValid()?Current.SourceActor.Get():Current.Actor.Get();
    if(!SourceActor||!SourceActor->Origin){Error=TEXT("release source identity is unavailable");return false;}
    Source.DisplayedSequence=SourceActor->Origin->Sequence;Source.DisplayedFrame=SourceActor->Origin->Frame;
    Source.DisplayedPicture=Current.SourcePicture;Source.AnimationSequence=0;Source.Brain=0;Source.NoHit=0;
    FDinkFamilyCollisionFitCandidate Prepared;
    if(!PrepareCollisionFitImpl(Origin,Source,Prepared,Error,true))return false;
    auto* Actor=Prepared.Actor.Get();
    // Ordinary billboard authority writes WORLD upright yaw only (FaceCardsToCamera).
    // Do not launder pitch/roll tampering into the next released presentation.
    if(Actor&&!Actor->Card->GetComponentQuat().GetUpVector().Equals(FVector::UpVector,0))
    {Error=TEXT("effective legacy card has unsupported non-yaw world rotation");return false;}
    if(Actor&&Actor->bHasPublishedLegacyPicture&&
       (!Actor->PublishedLegacyReleaseWitness||!PublishedReleaseMatches(*Actor,*Actor->PublishedLegacyReleaseWitness,Current.SourcePicture,Error)))
    {if(Error.IsEmpty())Error=TEXT("published release witness missing");return false;}
    if(!Actor||!Actor->bHasImportedCardBaseline||!Actor->Origin||
       Current.SourcePicture.Sequence!=Actor->Origin->Sequence||Current.SourcePicture.Frame!=Actor->Origin->Frame||
       Current.DisplayedPicture.Sequence!=Current.DisplayedSequence||Current.DisplayedPicture.Frame!=Current.DisplayedFrame||
       !DinkFamilyCollisionFit::ProjectLegacyCard(Current.SourcePicture,Current.DisplayedPicture,Actor->ImportedCardRelativeTransform,Prepared.ReleaseCardRelative,Error))
    {if(Error.IsEmpty())Error=TEXT("missing/mismatched immutable imported card/picture baseline");return false;}
    auto ResolvePicture=[&](const TCHAR* Role,const FDinkLegacyPictureDescriptor& Picture,UTexture*& Texture)->UMaterialInterface*
    {
        if(!DinkFamilyCollisionFit::ValidatePictureDescriptor(Picture))
        {if(Error.IsEmpty())Error=FString(Role)+TEXT(" picture descriptor invalid");return nullptr;}
        const FString Key=FString::Printf(TEXT("%d_%02d"),Picture.Sequence,Picture.Frame);
        const FString MaterialPath=FString::Printf(TEXT("/Game/Dink/_Generated/Sprites/MI_Sprite_%s.MI_Sprite_%s"),*Key,*Key);
        const FString TexturePath=FString::Printf(TEXT("/Game/Dink/_Generated/Sprites/T_Sprite_%s.T_Sprite_%s"),*Key,*Key);
        auto* Material=LoadObject<UMaterialInterface>(nullptr,*MaterialPath);Texture=nullptr;
        const bool MaterialMatches=Material&&Material->GetPathName()==MaterialPath;
        const bool ParameterFound=MaterialMatches&&Material->GetTextureParameterValue(FMaterialParameterInfo(TEXT("Tex")),Texture);
        const auto* Texture2D=Cast<UTexture2D>(Texture);
        const bool TextureMatches=ParameterFound&&Texture2D&&Texture->GetPathName()==TexturePath;
        const uint32 ExpectedWidth=FMath::Min(1024u,FMath::RoundUpToPowerOfTwo(uint32(Picture.Width)));
        const uint32 ExpectedHeight=FMath::Min(1024u,FMath::RoundUpToPowerOfTwo(uint32(Picture.Height)));
        FIntPoint ActualSize=FIntPoint::ZeroValue;bool DimensionsMatch=false,DimensionsRead=false;
        bool CompilingObserved=false,CompilingBeforeDimensions=false;
        if(TextureMatches)
        {
            #if WITH_EDITOR
            CompilingObserved=true;CompilingBeforeDimensions=Texture->IsCompiling();
            #endif
            // Authoring size is independent of optional rendered platform resources in ALL contexts.
            DimensionsRead=true;DimensionsMatch=DinkFamilyCollisionFit::MatchesLegacyPictureImportedSize(Picture,*Texture2D,&ActualSize);
        }
        if(!TextureMatches||!DimensionsMatch)
        {
            if(Error.IsEmpty())Error=FString::Printf(
                TEXT("%s picture asset preflight failed: expectedMI=%s actualMI=%s materialMatch=%d parameterFound=%d expectedTex=%s actualTex=%s textureMatch=%d importedDimensionsRead=%d actualImportedWidth=%d expectedWidth=%u actualImportedHeight=%d expectedHeight=%u compilingObserved=%d compilingBeforeDimensions=%d"),
                Role,*MaterialPath,*GetPathNameSafe(Material),MaterialMatches,ParameterFound,*TexturePath,*GetPathNameSafe(Texture),TextureMatches,
                DimensionsRead,ActualSize.X,ExpectedWidth,ActualSize.Y,ExpectedHeight,CompilingObserved,CompilingBeforeDimensions);
            return nullptr;
        }
        return Material;
    };
    // The ordinary exporter resamples the WHOLE image to power-of-two texture sizes;
    // UV0 remains0..1, so logical source width/pivot drive geometry without UV cropping.
    UTexture* SourceTexture=nullptr;UTexture* TargetTexture=nullptr;
    auto* SourceMaterial=ResolvePicture(TEXT("Source"),Current.SourcePicture,SourceTexture);
    auto* Material=ResolvePicture(TEXT("Target"),Current.DisplayedPicture,TargetTexture);
    if(!SourceMaterial||!Material)
    {if(Error.IsEmpty())Error=TEXT("missing/wrong source or effective-frame material/Tex identity or resampled dimensions");return false;}
    // Position/scale come from source pixels; retain the currently legitimate billboard yaw.
    Prepared.ReleaseCardRelative.SetRotation(Actor->Card->GetRelativeTransform().GetRotation());
    Prepared.ReleaseMaterial=MakeShared<TStrongObjectPtr<UMaterialInterface>>(Material);
    Prepared.SourcePictureMaterial=MakeShared<TStrongObjectPtr<UMaterialInterface>>(SourceMaterial);
    Prepared.ReleaseTexture=MakeShared<TStrongObjectPtr<UTexture>>(TargetTexture);
    Prepared.SourcePictureTexture=MakeShared<TStrongObjectPtr<UTexture>>(SourceTexture);
    Prepared.ReleasePicture=Current.DisplayedPicture;Prepared.bReleasePicturePrepared=true;
    Out=MoveTemp(Prepared);
    Out.bReleaseOnly=true;return true;
}


bool DinkFamilyCollisionFit::ValidatePictureDescriptor(const FDinkLegacyPictureDescriptor& P)
{
    if(P.Sequence<=0||P.Frame<=0||P.Width<=0||P.Height<=0||P.Width>16384||P.Height>16384||P.Sha1.Len()!=40)return false;
    const FString Text=FString::Printf(TEXT("DinkPictureDescriptor/1:%d,%d,%d,%d,%d,%d"),P.Sequence,P.Frame,P.Width,P.Height,P.OriginX,P.OriginY);
    FTCHARToUTF8 Bytes(*Text);uint8 Digest[20];FSHA1::HashBuffer(Bytes.Get(),Bytes.Length(),Digest);
    return P.Sha1==BytesToHex(Digest,20).ToLower();
}
bool DinkFamilyCollisionFit::ProjectLegacyCard(const FDinkLegacyPictureDescriptor& Source,
    const FDinkLegacyPictureDescriptor& Displayed,const FTransform& Baseline,FTransform& Out,FString& Error)
{
    if(!ValidatePictureDescriptor(Source)||!ValidatePictureDescriptor(Displayed)||Baseline.ContainsNaN()||
        !Baseline.GetRotation().Equals(FQuat::Identity,0)||Baseline.GetScale3D().X<=0||Baseline.GetScale3D().Z<=0||Baseline.GetScale3D().Y!=1)
    {Error=TEXT("missing/invalid source-backed legacy picture descriptor/baseline");return false;}
    // Each result starts at the immutable importer baseline: repeated load/reentry cannot compound scale.
    const double X=Baseline.GetScale3D().X/Source.Width,Z=Baseline.GetScale3D().Z/Source.Height;
    FVector At=Baseline.GetLocation();
    At.X+=((Displayed.Width-Source.Width)/2.0-(Displayed.OriginX-Source.OriginX))*X*100;
    At.Z+=(-(Displayed.Height-Source.Height)+(Displayed.OriginY-Source.OriginY))*Z*100;
    Out=FTransform(Baseline.GetRotation(),At,FVector(Displayed.Width*X,1,Displayed.Height*Z));
    if(Out.ContainsNaN()){Error=TEXT("nonfinite projected legacy card");return false;}
    Error.Reset();return true;
}


bool DinkFamilyCollisionFit::ValidateReleasedPictureAssets(const FDinkFamilyCollisionFitCandidate& C,FString& Error)
{
    auto Matches=[](const FDinkLegacyPictureDescriptor& P,const TSharedPtr<TStrongObjectPtr<UMaterialInterface>>& Material,
        const TSharedPtr<TStrongObjectPtr<UTexture>>& Texture)
    {
        if(!ValidatePictureDescriptor(P)||!Material||!Material->IsValid()||!Texture||!Texture->IsValid())return false;
        const FString Key=FString::Printf(TEXT("%d_%02d"),P.Sequence,P.Frame);
        const FString MI=FString::Printf(TEXT("/Game/Dink/_Generated/Sprites/MI_Sprite_%s.MI_Sprite_%s"),*Key,*Key);
        const FString Tex=FString::Printf(TEXT("/Game/Dink/_Generated/Sprites/T_Sprite_%s.T_Sprite_%s"),*Key,*Key);
        UTexture* Parameter=nullptr;
        const auto* Texture2D=Cast<UTexture2D>(Texture->Get());
        return Material->Get()->GetPathName()==MI&&Texture->Get()->GetPathName()==Tex&&Texture2D&&
            Material->Get()->GetTextureParameterValue(FMaterialParameterInfo(TEXT("Tex")),Parameter)&&Parameter==Texture->Get()&&
            MatchesLegacyPictureImportedSize(P,*Texture2D);
    };
    if(!C.bReleasePicturePrepared||!Matches(C.Sprite.SourcePicture,C.SourcePictureMaterial,C.SourcePictureTexture)||
       !Matches(C.ReleasePicture,C.ReleaseMaterial,C.ReleaseTexture))
    {Error=TEXT("prepared source/effective picture material/Tex identity or dimensions changed");return false;}
    Error.Reset();return true;
}


bool DinkFamilyCollisionFit::MatchesLegacyPictureImportedSize(const FDinkLegacyPictureDescriptor& P,
    const UTexture2D& Texture,FIntPoint* Observed)
{
    // GetImportedSize reads editor source logical size or the persisted cooked ImportedSize.
    // GetSurfaceWidth/Height instead depend on optional platform data and can both be0 in commandlets.
    const FIntPoint Size=Texture.GetImportedSize();if(Observed)*Observed=Size;
    return ValidatePictureDescriptor(P)&&Size.X==int32(FMath::Min(1024u,FMath::RoundUpToPowerOfTwo(uint32(P.Width))))&&
        Size.Y==int32(FMath::Min(1024u,FMath::RoundUpToPowerOfTwo(uint32(P.Height))));
}
