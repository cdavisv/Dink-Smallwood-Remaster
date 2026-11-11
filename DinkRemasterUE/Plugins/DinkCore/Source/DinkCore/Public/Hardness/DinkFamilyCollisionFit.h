#pragma once
#include "CoreMinimal.h"
#include "DinkOriginId.h"
#include "DinkLayout.h"
#include "Engine/EngineTypes.h"

class ADinkPlaceholderActor;
class UStaticMesh;
class UStaticMeshComponent;
class UBodySetup;
class UMaterialInterface;
class UWorld;
namespace DinkFamilyCollisionFit
{
    inline constexpr int32 DescriptorSchemaVersion = 2;
    inline constexpr TCHAR PromotedBackgroundTag[] = TEXT("DinkFitPromotedBackground");
}

/** Explicit origin policy under families.json. Schema 1 retains the original pair. */
struct DINKCORE_API FDinkFamilyCollisionFitRule
{
    FDinkOriginId Origin;
    FString Mesh;
    FString GeometrySha1;
    FString SourceHash; // Empty only for the legacy schema 1 pair.
    FName SourceScript;
    int32 SourceType = 1;
    bool IsStaticBackground() const { return SourceType == 0; }
};
struct DINKCORE_API FDinkFamilyFitSpriteState
{
    int32 SchemaVersion=DinkFamilyCollisionFit::DescriptorSchemaVersion;
    FDinkOriginId Origin;
    TWeakObjectPtr<ADinkPlaceholderActor> Actor;
    TWeakObjectPtr<ADinkPlaceholderActor> SourceActor;
    FName ScriptName;
    int32 RuntimeHandle=0;
    int32 CurrentScreen=0; // current owner/map; Origin remains immutable source identity
    bool bPrebirth=false; // handle0, explicit source actor, no main executed
    double EngineX=0,EngineY=0;
    int32 DisplayedSequence=0,DisplayedFrame=0,Hard=1,Prop=0;
    bool bActive=false;
    int32 AnimationSequence=0,Brain=0,NoHit=0;
};
/** Exact cooked query triangles, not a guessed box and not a300cm raster prism.
 * UCX is separately retained provenance and is NOT the selected query shape. */
struct DINKCORE_API FDinkFamilyFittedGeometry
{
    int32 SchemaVersion=DinkFamilyCollisionFit::DescriptorSchemaVersion;
    TWeakObjectPtr<UStaticMesh> Mesh;
    TWeakObjectPtr<UBodySetup> BodySetup;
    FGuid BodySetupGuid;
    bool bDoubleSided=false,bCullsBackFaceRaycast=false; // EFFECTIVE active policy: !DoubleSided
    bool bSourceCullsBackFaceRaycast=false; // raw cache diagnostic only, not policy identity
    TArray<FVector3f> Vertices;
    TArray<FIntVector> Triangles;
    TArray<uint16> MaterialIndices;
    TArray<FVector> AuthoredUCXVertices;
    FBox RenderBounds;
    FString CookedGeometrySha1;
};
/** Prepared descriptor only. The physical coordinator must replace the original
 * owner layer, physical body, logical/hit footprint and clear semantics together.
 * Cell-centre raster is an approximation; WorldFootprint/actual triangles remain
 * the geometry authority. No producer creates/changes a physical body. */
struct DINKCORE_API FDinkFamilyCollisionFitCandidate
{
    int32 SchemaVersion=DinkFamilyCollisionFit::DescriptorSchemaVersion;
    FDinkOriginId Origin;
    FDinkFamilyFitSpriteState Sprite;
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<ADinkPlaceholderActor> Actor,SourceActor;
    TWeakObjectPtr<UStaticMeshComponent> FamilyComponent,Card;
    TWeakObjectPtr<UStaticMesh> BeforeCardMesh;
    FDinkScreenCorners Corners;
    FTransform BeforeActor,BeforeFamily,BeforeCard,ProposedWorld;
    TArray<TWeakObjectPtr<UMaterialInterface>> BeforeMaterials,BeforeCardMaterials;
    FString SourceHash;
    FName ScriptName,BeforeProfile;
    FCollisionResponseContainer BeforeResponses;
    ECollisionEnabled::Type BeforeCollision=ECollisionEnabled::NoCollision;
    ECollisionChannel BeforeObjectType=ECC_WorldStatic;
    bool BeforeNavigation=false,BeforeOverlaps=false,BeforeVisible=true;
    bool BeforeActorCollision=true,BeforeActorHidden=false;
    bool BeforeFamilyHidden=false,BeforeCardHidden=true,BeforeCardVisible=true;
    uint8 BeforeMobility=0;
    FDinkFamilyFittedGeometry Geometry;
    TArray<FVector2D> WorldFootprint; // CCW, ordered from lexicographically first point
    TArray<FIntPoint> LogicalCells; // map pixel centres, Y-major then X; no conservative dilation
    double MinWorldZ=0,MaxWorldZ=0,MaximumRasterBoundaryErrorCm=0;
    bool bVisualApplied=false;
    bool bReleaseOnly=false;
};
/** Implemented by the ONE admitted owner coordinator, not by the family layer.
 * The implementation must verify held loading gate and matching committed
 * logical+physical descriptor. No boolean caller approval substitutes for it. */
struct DINKCORE_API IDinkFamilyFitVisualAuthority
{
    virtual ~IDinkFamilyFitVisualAuthority()=default;
    virtual int32 GetSchemaVersion() const=0;
    virtual bool CanPublishVisual(const FDinkFamilyCollisionFitCandidate& Candidate,FString& Error) const=0;
    virtual bool CanReleaseVisual(const FDinkFamilyCollisionFitCandidate&,const FDinkFamilyFitSpriteState&,FString&) const { return false; }
};
namespace DinkFamilyCollisionFit
{
    DINKCORE_API bool ParsePolicy(const FString& FamiliesJson,TArray<FDinkFamilyCollisionFitRule>& Out,FString& Error);
    DINKCORE_API bool ReadCookedGeometry(UStaticMesh& Mesh,FDinkFamilyFittedGeometry& Out,FString& Error);
    DINKCORE_API bool BuildFootprint(const FDinkFamilyFittedGeometry& Geometry,const FTransform& Proposed,
        const FDinkScreenCorners& Corners,TArray<FVector2D>& Polygon,TArray<FIntPoint>& Cells,
        double& MinZ,double& MaxZ,double& BoundaryErrorCm,FString& Error);
}
