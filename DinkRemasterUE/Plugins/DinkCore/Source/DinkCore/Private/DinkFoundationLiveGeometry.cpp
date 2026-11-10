#include "Hardness/DinkFoundationLiveGeometry.h"

#include "Chaos/ImplicitObjectScaled.h"
#include "Chaos/ShapeInstance.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "PhysicsEngine/BodyInstance.h"

namespace DinkFoundationLiveGeometry
{
    FString TriangleSignature(const FVector3f& A, const FVector3f& B, const FVector3f& C)
    {
        const FVector3f Vertices[] = {A, B, C};
        FString Best;
        for (int32 Rotation = 0; Rotation < 3; ++Rotation)
        {
            FString Signature;
            for (int32 Index = 0; Index < 3; ++Index)
            {
                const FVector3f& Position = Vertices[(Index + Rotation) % 3];
                Signature += FString::Printf(TEXT("%.9g,%.9g,%.9g;"),
                    Position.X == 0 ? 0.f : Position.X,
                    Position.Y == 0 ? 0.f : Position.Y,
                    Position.Z == 0 ? 0.f : Position.Z);
            }
            if (Rotation == 0 || Signature < Best)
            {
                Best = MoveTemp(Signature);
            }
        }
        return Best;
    }

    bool ReadTriangleSignatures(const FBodyInstance& Body, const FTransform* ExpectedBodyPose,
        TArray<FString>& Out, FString& Error)
    {
        TArray<FString> Triangles;
        bool bReadTriangles = false;
        Error.Reset();
        FPhysicsCommand::ExecuteRead(Body.GetPhysicsActorHandle(), [&](const FPhysicsActorHandle& Actor)
        {
            if (ExpectedBodyPose &&
                !FPhysicsInterface::GetGlobalPose_AssumesLocked(Actor).Equals(*ExpectedBodyPose, 1e-4))
            {
                Error = TEXT("live physics body pose differs");
                return;
            }

            TArray<FPhysicsShapeHandle> Shapes;
            if (FPhysicsInterface::GetAllShapes_AssumedLocked(Actor, Shapes) != 1 ||
                Shapes.Num() != 1 || !Shapes[0].IsValid() ||
                !FPhysicsInterface::IsQueryShape(Shapes[0]) ||
                !FPhysicsInterface::IsSimulationShape(Shapes[0]))
            {
                Error = TEXT("requires one live query and simulation shape");
                return;
            }

            // Chaos registers unit-scale static mesh shapes as instanced
            // triangle meshes. GetTriMeshGeometry uses a checked dispatcher
            // that does not handle triangle meshes in the installed engine.
            const Chaos::FImplicitObjectRef Geometry = Shapes[0].Shape->GetGeometry();
            if (!Geometry)
            {
                Error = TEXT("live shape has no geometry");
                return;
            }

            Chaos::FVec3 Scale(1);
            Chaos::FReal Margin = 0;
            const auto* TriangleMesh = Chaos::UnwrapImplicit<Chaos::FTriangleMeshImplicitObject>(
                *Geometry, Scale, Margin);
            // The expected triangles are in the fixed component's local
            // frame. Transformed shapes or actual scale/margin cannot match.
            if (!TriangleMesh || Scale != Chaos::FVec3(1) || Margin != 0)
            {
                Error = FString::Printf(
                    TEXT("unsupported live triangle geometry type=%u scale=(%.17g,%.17g,%.17g) margin=%.17g"),
                    static_cast<uint32>(Geometry->GetType()),
                    double(Scale.X), double(Scale.Y), double(Scale.Z), double(Margin));
                return;
            }

            const uint64 ParticleCount = TriangleMesh->Particles().Size();
            auto ReadIndices = [&](const auto& Indices)
            {
                for (const auto& Index : Indices)
                {
                    if (uint64(Index[0]) >= ParticleCount || uint64(Index[1]) >= ParticleCount ||
                        uint64(Index[2]) >= ParticleCount)
                    {
                        Error = TEXT("live triangle has an invalid vertex index");
                        return false;
                    }
                    Triangles.Add(TriangleSignature(FVector3f(TriangleMesh->Particles().GetX(Index[0])),
                        FVector3f(TriangleMesh->Particles().GetX(Index[1])),
                        FVector3f(TriangleMesh->Particles().GetX(Index[2]))));
                }
                return true;
            };
            const auto& Elements = TriangleMesh->Elements();
            bReadTriangles = Elements.RequiresLargeIndices()
                ? ReadIndices(Elements.GetLargeIndexBuffer())
                : ReadIndices(Elements.GetSmallIndexBuffer());
        });
        if (!bReadTriangles)
        {
            if (Error.IsEmpty())
            {
                Error = TEXT("live physics read did not complete");
            }
            return false;
        }
        Out = MoveTemp(Triangles);
        return true;
    }
}
