#include "Hardness/DinkHardnessPrismComponent.h"
#include "Hardness/DinkHardnessShell.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Engine/World.h"
#include "PhysicsEngine/BodySetup.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "Physics/PhysScene.h"

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

bool UDinkHardnessPrismComponent::FinalizeRegisteredPreparation(const UPrimitiveComponent& Reference)
{
    if(!ValidateRegisteredInert() || !GetWorld() || !Reference.GetBodyInstance()) return false;
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
    return Configured && ValidateRegisteredInert();
}

void UDinkHardnessPrismComponent::UpdateBodySetup() {}
FBoxSphereBounds UDinkHardnessPrismComponent::CalcBounds(const FTransform& LocalToWorld) const
{ return FBoxSphereBounds(LocalGeometryBounds).TransformBy(LocalToWorld); }

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
