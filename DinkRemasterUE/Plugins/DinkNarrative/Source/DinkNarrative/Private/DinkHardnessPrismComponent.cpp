#include "Hardness/DinkHardnessPrismComponent.h"
#include "Hardness/DinkHardnessShell.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Engine/World.h"
#include "PhysicsEngine/BodySetup.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "Physics/PhysScene.h"
#include "Physics/Experimental/PhysScene_Chaos.h"

namespace
{
DinkCookedMeshIdentity::Snapshot CookedIdentity(const Chaos::FTriangleMeshImplicitObject& Mesh)
{
    DinkCookedMeshIdentity::Snapshot Result;
    Result.LargeIndices=Mesh.Elements().RequiresLargeIndices();
    Result.Particles.reserve(Mesh.Particles().Size());
    for(int32 Index=0;Index<Mesh.Particles().Size();++Index)
    {
        DinkCookedMeshIdentity::ParticleBits Bits;
        for(int32 Axis=0;Axis<3;++Axis)
        {
            const float Value=Mesh.Particles().GetX(Index)[Axis];
            FMemory::Memcpy(&Bits[Axis],&Value,sizeof(Value));
        }
        Result.Particles.push_back(Bits);
    }
    auto Read=[&](const auto& Elements)
    {
        int32 Number=0;
        for(const auto& Triangle:Elements)
        {
            DinkCookedMeshIdentity::Face Item;
            for(int32 Corner=0;Corner<3;++Corner)Item.Indices[Corner]=uint32(Triangle[Corner]);
            Item.Material=Mesh.GetMaterialIndex(Number);Item.ExternalFace=Mesh.GetExternalFaceIndexFromInternal(Number++);
            Result.Faces.push_back(Item);
        }
    };
    if(Result.LargeIndices)Read(Mesh.Elements().GetLargeIndexBuffer());else Read(Mesh.Elements().GetSmallIndexBuffer());
    return Result;
}
bool MatchesCookedIdentity(const DinkCookedMeshIdentity::Snapshot& Frozen,
                           const Chaos::FTriangleMeshImplicitObject& Mesh)
{
    // Called from readiness/commit paths: stream fixed values, allocate nothing.
    if(Frozen.LargeIndices!=Mesh.Elements().RequiresLargeIndices() ||
       Frozen.Particles.size()!=static_cast<SIZE_T>(Mesh.Particles().Size()) ||
       Frozen.Faces.size()!=static_cast<SIZE_T>(Mesh.Elements().GetNumTriangles()))return false;
    for(int32 Index=0;Index<Mesh.Particles().Size();++Index)
        for(int32 Axis=0;Axis<3;++Axis)
        {
            const float Value=Mesh.Particles().GetX(Index)[Axis];uint32 Bits;
            FMemory::Memcpy(&Bits,&Value,sizeof(Bits));
            if(Frozen.Particles[Index][Axis]!=Bits)return false;
        }
    auto Match=[&](const auto& Elements)
    {
        int32 Number=0;
        for(const auto& Triangle:Elements)
        {
            const auto& Item=Frozen.Faces[Number];
            for(int32 Corner=0;Corner<3;++Corner)if(Item.Indices[Corner]!=uint32(Triangle[Corner]))return false;
            if(Item.Material!=Mesh.GetMaterialIndex(Number) || Item.ExternalFace!=Mesh.GetExternalFaceIndexFromInternal(Number))return false;
            ++Number;
        }
        return true;
    };
    return Frozen.LargeIndices?Match(Mesh.Elements().GetLargeIndexBuffer()):Match(Mesh.Elements().GetSmallIndexBuffer());
}
}

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
    LocalGeometryBounds=Bounds;ShapeBodySetup=Setup;
    // CopySlowImpl legitimately rebuilds BVH face order. Verify every exact
    // association BEFORE publishing an admitted pair of ordered epoch snapshots.
    auto Admission=DinkCookedMeshIdentity::Admit(CookedIdentity(*Source.TriMeshGeometries[0]),CookedIdentity(*Copy));
    if(!Admission)return false;
    PreparedSourceGuid=Source.BodySetupGuid;PreparedSourceDoubleSided=Source.bDoubleSidedGeometry;
    PreparedSourceImplicit=Source.TriMeshGeometries[0].GetReference();PreparedOwnedImplicit=Copy;PreparedOwnedSetup=Setup;
    PreparedIdentity=MoveTemp(Admission);
    return ValidateCookedMeshGeometry(Source);
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
    if(CookedSource.Get()!=&Source || PreparedOwnedSetup.Get()!=ShapeBodySetup ||
       Source.BodySetupGuid!=PreparedSourceGuid || Source.bDoubleSidedGeometry!=PreparedSourceDoubleSided ||
       &A!=PreparedSourceImplicit || &B!=PreparedOwnedImplicit ||
       !PreparedIdentity)return false;
    // No later reordering/mutation is admitted in either epoch. Raw cache cull
    // is excluded only for the documented stock source-initialization transition;
    // owned cull is checked against the existing inert/registered policy above.
    if(!MatchesCookedIdentity(PreparedIdentity->Source,A) || !MatchesCookedIdentity(PreparedIdentity->Owned,B))return false;
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
