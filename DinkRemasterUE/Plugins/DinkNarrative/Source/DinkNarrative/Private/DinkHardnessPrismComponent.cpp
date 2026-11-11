#include "Hardness/DinkHardnessPrismComponent.h"
#include "Hardness/DinkHardnessShell.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Engine/World.h"
#include "PhysicsEngine/BodySetup.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "Physics/PhysScene.h"
#include "Physics/Experimental/PhysScene_Chaos.h"

UDinkHardnessPrismComponent::UDinkHardnessPrismComponent(const FObjectInitializer& Initializer)
    : Super(Initializer)
{
    bAlwaysCreatePhysicsState = true;
    BodyInstance.bAutoWeld = false;
    bUseArchetypeBodySetup = false;
    SetMobility(EComponentMobility::Static);
    SetGenerateOverlapEvents(false);
    SetCanEverAffectNavigation(false);
    SetVisibility(false); SetHiddenInGame(true); SetCastShadow(false);
}

bool UDinkHardnessPrismComponent::PrepareGeometry(const TArray<TArray<FVector>>& Prisms,
                                                 const UPrimitiveComponent& Reference)
{
    if (IsRegistered() || ShapeBodySetup || Prisms.IsEmpty() || Reference.GetGenerateOverlapEvents()) return false;
    const FBodyInstance* ReferenceBody = Reference.GetBodyInstance();
    if (!ReferenceBody || ReferenceBody->bSimulatePhysics || Reference.GetCollisionEnabled() != ECollisionEnabled::QueryAndPhysics) return false;
    TArray<FVector3f> Vertices;
    TArray<Chaos::TVec3<int32>> Indices;
    for (const auto& Prism : Prisms)
    {
        if (Prism.Num()!=8) return false;
        std::array<DinkHardness::ShellPoint,8> P;
        for(unsigned I=0;I<8;++I) P[I]={float(Prism[I].X),float(Prism[I].Y),float(Prism[I].Z)};
        const auto Shell=DinkHardness::OpenPrismShell(P);
        if(!Shell) return false;
        for(const auto& Triangle:*Shell)
        {
            const int32 First=Vertices.Num();
            for(const auto& Point:Triangle) Vertices.Add(FVector3f(Point.X,Point.Y,Point.Z));
            Indices.Add(Chaos::TVec3<int32>(First,First+1,First+2));
        }
    }
    Chaos::FTriangleMeshImplicitObject::ParticlesType Particles;
    Particles.AddParticles(Vertices.Num());
    FBox Bounds(ForceInit);
    for(int32 I=0;I<Vertices.Num();++I) { Particles.SetX(I,Vertices[I]); Bounds+=FVector(Vertices[I]); }
    TArray<uint16> Materials; Materials.Init(0,Indices.Num());
    Chaos::FTriangleMeshImplicitObjectPtr Mesh(new Chaos::FTriangleMeshImplicitObject(
        MoveTemp(Particles),MoveTemp(Indices),MoveTemp(Materials),nullptr,nullptr,false));
    if(Mesh->Elements().GetNumTriangles()!=Prisms.Num()*10) return false;
    UBodySetup* Setup=NewObject<UBodySetup>(this,NAME_None,RF_Transient);
    Setup->CollisionTraceFlag=CTF_UseComplexAsSimple;
    if(const UBodySetup* RefSetup=ReferenceBody->GetBodySetup()) Setup->bDoubleSidedGeometry=RefSetup->bDoubleSidedGeometry;
    Setup->TriMeshGeometries.Add(MoveTemp(Mesh));
    Setup->bCreatedPhysicsMeshes=true; // actual runtime triangle object above; not a cooked-asset claim
    Setup->bFailedToCreatePhysicsMeshes=false;
    BodyInstance.SetObjectType(Reference.GetCollisionObjectType());
    BodyInstance.CopyRuntimeBodyInstancePropertiesFrom(ReferenceBody);
    BodyInstance.SetPhysMaterialOverride(ReferenceBody->GetSimplePhysicalMaterial());
    // Only this new, unregistered body is disabled. bAlwaysCreatePhysicsState
    // requests an actual inert representation; missing bodies fail preparation.
    BodyInstance.SetCollisionEnabled(ECollisionEnabled::NoCollision,false);
    bDesiredNavigation=Reference.CanEverAffectNavigation();
    CanCharacterStepUpOn=Reference.CanCharacterStepUpOn;
    LocalGeometryBounds=Bounds; ShapeBodySetup=Setup;
    return true;
}

bool UDinkHardnessPrismComponent::PrepareCookedMeshGeometry(UBodySetup& Source,const UPrimitiveComponent& Reference)
{
    if(IsRegistered() || ShapeBodySetup || Source.CollisionTraceFlag!=CTF_UseComplexAsSimple ||
       Source.TriMeshGeometries.Num()!=1 || !Source.TriMeshGeometries[0] || !Source.bCreatedPhysicsMeshes ||
       Source.bFailedToCreatePhysicsMeshes || Reference.GetGenerateOverlapEvents())return false;
    const auto* Body=Reference.GetBodyInstance();
    if(!Body || Body->bSimulatePhysics || Reference.GetCollisionEnabled()!=ECollisionEnabled::QueryAndPhysics)return false;
    auto* Setup=NewObject<UBodySetup>(this,NAME_None,RF_Transient);
    Setup->CollisionTraceFlag=CTF_UseComplexAsSimple;
    Setup->bDoubleSidedGeometry=Source.bDoubleSidedGeometry;
    // Engine registration writes the implicit's cull flag. Never share that
    // mutable cache with the source asset. Installed DeepCopyGeometry preserves
    // particles/elements/materials/remaps; it does not cook/reconstruct faces.
    if(!Chaos::TriMeshPerPolySupport)return false; // required to retain an existing vertex remap
    auto Copied=Source.TriMeshGeometries[0]->DeepCopyGeometry();
    auto* Copy=Copied?Copied->AsA<Chaos::FTriangleMeshImplicitObject>():nullptr;
    if(!Copy || Copy==Source.TriMeshGeometries[0].GetReference())return false;
    Setup->TriMeshGeometries.Add(Chaos::FTriangleMeshImplicitObjectPtr(Copy));
    CookedSource=&Source;SourceRawCullBeforeRegistration=Source.TriMeshGeometries[0]->GetCullsBackFaceRaycast();
    Setup->bCreatedPhysicsMeshes=true;Setup->bFailedToCreatePhysicsMeshes=false;
    FBox Bounds(ForceInit);
    const auto& Particles=Source.TriMeshGeometries[0]->Particles();
    for(int32 I=0;I<Particles.Size();++I)Bounds+=FVector(Particles.GetX(I));
    if(!Bounds.IsValid)return false;
    BodyInstance.SetObjectType(Reference.GetCollisionObjectType());
    BodyInstance.CopyRuntimeBodyInstancePropertiesFrom(Body);
    BodyInstance.SetPhysMaterialOverride(Body->GetSimplePhysicalMaterial());
    BodyInstance.SetCollisionEnabled(ECollisionEnabled::NoCollision,false);
    bDesiredNavigation=Reference.CanEverAffectNavigation();CanCharacterStepUpOn=Reference.CanCharacterStepUpOn;
    LocalGeometryBounds=Bounds;ShapeBodySetup=Setup;return ValidateCookedMeshGeometry(Source);
}

bool UDinkHardnessPrismComponent::ValidateCookedMeshGeometry(const UBodySetup& Source) const
{
    if(!ShapeBodySetup || ShapeBodySetup==&Source || Source.TriMeshGeometries.Num()!=1 ||
       ShapeBodySetup->TriMeshGeometries.Num()!=1 || !Source.TriMeshGeometries[0] || !ShapeBodySetup->TriMeshGeometries[0] ||
       ShapeBodySetup->bDoubleSidedGeometry!=Source.bDoubleSidedGeometry)return false;
    const auto& A=*Source.TriMeshGeometries[0];const auto& B=*ShapeBodySetup->TriMeshGeometries[0];
    if(&A==&B || A.Particles().Size()!=B.Particles().Size() ||
       A.Elements().RequiresLargeIndices()!=B.Elements().RequiresLargeIndices() ||
       A.Elements().GetNumTriangles()!=B.Elements().GetNumTriangles() ||
       B.GetCullsBackFaceRaycast()!=(IsRegistered()?!Source.bDoubleSidedGeometry:SourceRawCullBeforeRegistration))return false;
    for(int32 I=0;I<A.Particles().Size();++I)
        for(int32 K=0;K<3;++K)
        {const float X=A.Particles().GetX(I)[K],Y=B.Particles().GetX(I)[K];if(FMemory::Memcmp(&X,&Y,sizeof(float))!=0)return false;}
    auto SameIndices=[](const auto& X,const auto& Y){
        if(X.Num()!=Y.Num())return false;
        for(int32 I=0;I<X.Num();++I)for(int32 K=0;K<3;++K)if(X[I][K]!=Y[I][K])return false;
        return true;
    };
    const bool Same=A.Elements().RequiresLargeIndices()?
        SameIndices(A.Elements().GetLargeIndexBuffer(),B.Elements().GetLargeIndexBuffer()):
        SameIndices(A.Elements().GetSmallIndexBuffer(),B.Elements().GetSmallIndexBuffer());
    if(!Same)return false;
    for(int32 I=0;I<A.Elements().GetNumTriangles();++I)
        if(A.GetMaterialIndex(I)!=B.GetMaterialIndex(I) ||
           A.GetExternalFaceIndexFromInternal(I)!=B.GetExternalFaceIndexFromInternal(I))return false;
    return true;
}

bool UDinkHardnessPrismComponent::FinalizeRegisteredPreparation(const UPrimitiveComponent& Reference)
{
    if(!ValidateRegisteredInert() || !GetWorld() || !Reference.GetBodyInstance()) return false;
    if(CookedSource.IsValid() &&
       (!ValidateCookedMeshGeometry(*CookedSource.Get()) ||
        CookedSource->TriMeshGeometries[0]->GetCullsBackFaceRaycast()!=SourceRawCullBeforeRegistration))return false;
    bool Configured=false;
    // Supported profile restoration updates the actual triangle filters. It may
    // allocate, so stays in PREPARATION. Nested writer locks are recursive in
    // installed default editor/game Chaos locks (Framework/Threading.h).
    FPhysicsCommand::ExecuteWrite(GetWorld()->GetPhysicsScene(),[&]() {
        BodyInstance.CopyRuntimeBodyInstancePropertiesFrom(Reference.GetBodyInstance());
        const auto Actor=BodyInstance.GetPhysicsActorHandle();
        TArray<FPhysicsShapeHandle> Shapes;
        FPhysicsInterface::GetAllShapes_AssumedLocked(Actor,Shapes);
        for(const auto& Shape:Shapes)
        {
            FPhysicsInterface::SetIsQueryShape(Shape,false);
            FPhysicsInterface::SetIsSimulationShape(Shape,false);
        }
        GetWorld()->GetPhysicsScene()->UpdateActorInAccelerationStructure(Actor);
        Configured=Shapes.Num()==1;
    });
    return Configured && ValidateRegisteredInert() &&
        (!CookedSource.IsValid() || (ValidateCookedMeshGeometry(*CookedSource.Get()) &&
         CookedSource->TriMeshGeometries[0]->GetCullsBackFaceRaycast()==SourceRawCullBeforeRegistration));
}

void UDinkHardnessPrismComponent::UpdateBodySetup() {}
FBoxSphereBounds UDinkHardnessPrismComponent::CalcBounds(const FTransform& LocalToWorld) const
{
    if (CookedSource.IsValid() && ShapeBodySetup && ShapeBodySetup->TriMeshGeometries.Num()==1 &&
        ShapeBodySetup->TriMeshGeometries[0])
    {
        // The cooked copy is installed before registration. Transform its triangle
        // vertices so an angled barrel does not inherit its rotated local AABB.
        const auto& Mesh=*ShapeBodySetup->TriMeshGeometries[0];
        FBox WorldBounds(ForceInit);
        auto AddVertices=[&](const auto& Triangles)
        {
            for(const auto& Triangle:Triangles)
                for(int32 Corner=0;Corner<3;++Corner)
                    WorldBounds+=LocalToWorld.TransformPosition(FVector(Mesh.Particles().GetX(Triangle[Corner])));
        };
        if(Mesh.Elements().RequiresLargeIndices())AddVertices(Mesh.Elements().GetLargeIndexBuffer());
        else AddVertices(Mesh.Elements().GetSmallIndexBuffer());
        if(WorldBounds.IsValid)return FBoxSphereBounds(WorldBounds);
    }
    return FBoxSphereBounds(LocalGeometryBounds).TransformBy(LocalToWorld);
}

bool UDinkHardnessPrismComponent::ValidateRegisteredInert() const
{
    if(!IsRegistered() || !IsPhysicsStateCreated() || !ShapeBodySetup || ShapeBodySetup->TriMeshGeometries.Num()!=1 ||
        GetGenerateOverlapEvents() || CanEverAffectNavigation() || !BodyInstance.IsValidBodyInstance()) return false;
    bool Valid=false;
    FPhysicsCommand::ExecuteRead(BodyInstance.GetPhysicsActorHandle(),[&](const FPhysicsActorHandle& Actor) {
        TArray<FPhysicsShapeHandle> Shapes;
        Valid=FPhysicsInterface::GetAllShapes_AssumedLocked(Actor,Shapes)==1 &&
            FPhysicsInterface::GetGlobalPose_AssumesLocked(Actor).Equals(GetComponentTransform(),1e-4);
        for(const auto& Shape:Shapes) Valid &= FPhysicsInterface::GetShapeType(Shape)==ECollisionShapeType::Trimesh &&
            !FPhysicsInterface::IsQueryShape(Shape) && !FPhysicsInterface::IsSimulationShape(Shape);
    });
    return Valid;
}
