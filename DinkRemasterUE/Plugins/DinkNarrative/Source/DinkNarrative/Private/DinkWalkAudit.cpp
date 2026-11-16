#include "DinkWalkAudit.h"
#include "DinkGameplay.h"
#include "DinkStorySubsystem.h"
#include "DinkNarrativeTypes.h"
#include "DinkLayout.h"
#include "DinkOriginComponent.h"
#include "DinkArtFamilySubsystem.h"
#if __has_include("DinkPlayerBlockers.h")
#include "DinkPlayerBlockers.h"
#define DINK_WALKAUDIT_BLOCKERS 1
#else
#define DINK_WALKAUDIT_BLOCKERS 0
#endif
#include "DinkCollision.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Components/CapsuleComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Containers/Ticker.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "StaticMeshResources.h"
#include "Materials/MaterialInterface.h"

namespace
{
	// --- slice raster ---------------------------------------------------------------------------------------------------
	void ClipZ(TArray<FVector>& Poly, double Z, bool bKeepAbove)
	{
		TArray<FVector> Out;
		for (int32 I = 0; I < Poly.Num(); ++I)
		{
			const FVector& A = Poly[I];
			const FVector& B = Poly[(I + 1) % Poly.Num()];
			const bool InA = bKeepAbove ? A.Z >= Z : A.Z <= Z;
			const bool InB = bKeepAbove ? B.Z >= Z : B.Z <= Z;
			if (InA) Out.Add(A);
			if (InA != InB)
			{
				const double T = (Z - A.Z) / (B.Z - A.Z);
				Out.Add(A + (B - A) * T);
			}
		}
		Poly = MoveTemp(Out);
	}

	void Mark(TArray<uint8>& Cells, const FIntPoint& Size, int32 X, int32 Y)
	{
		if (X >= 0 && Y >= 0 && X < Size.X && Y < Size.Y) Cells[Y * Size.X + X] = 1;
	}

	bool SoftMaterial(const FString& Name)
	{
		static const TCHAR* Soft[] = { TEXT("Leaf"), TEXT("Leaves"), TEXT("Needle"), TEXT("Foliage"), TEXT("Canopy"), TEXT("Moss"), TEXT("Grass"),
			TEXT("Fern"), TEXT("Frond"), TEXT("Twig"), TEXT("Blossom"), TEXT("Flower"), TEXT("Understory") };
		for (const TCHAR* S : Soft) if (Name.Contains(S)) return true;
		return false;
	}

	FString MeshPath(const UStaticMesh* Mesh) { return Mesh ? Mesh->GetPathName() : FString(); }

	bool SkipMesh(const FString& Path)
	{
		// grass and ground scatter, decals and the greybox's own unit meshes are not obstacles
		static const TCHAR* Skip[] = { TEXT("Grass"), TEXT("grass"), TEXT("Clover"), TEXT("Flower"), TEXT("Decal"), TEXT("LeafLitter"),
			TEXT("/Engine/"), TEXT("_Generated/Meshes/SM_Screen"), TEXT("Ground"), TEXT("Terrain"), TEXT("Water"), TEXT("Sky") };
		for (const TCHAR* S : Skip) if (Path.Contains(S)) return true;
		return false;
	}

	struct FItem
	{
		UStaticMeshComponent* Component = nullptr;
		int32 Instance = INDEX_NONE;
		FTransform Transform;
		FString Kind;
	};

	FString KindOf(const UStaticMeshComponent& C, const AActor& Owner)
	{
		if (C.ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)) return Cast<UInstancedStaticMeshComponent>(&C) ? TEXT("family_instance") : TEXT("family");
		if (Owner.ActorHasTag(TEXT("DinkAuthoredArt"))) return TEXT("authored");
		if (const ADinkPlaceholderActor* P = Cast<ADinkPlaceholderActor>(&Owner)) if (P->Card == &C) return TEXT("card");
		if (Cast<ADinkScreenVolume>(&Owner)) return TEXT("interior");
		if (C.GetName().StartsWith(TEXT("Decor_"))) return TEXT("card");
		return TEXT("environment");
	}

	// Inside a hardness prism (the 3 m tall trimesh the importer builds for hardboxes, tiles and the voids it closes): a
	// downward ray meets its top. The capsule overlaps nothing there, so without this the inside of a closed void counts as free.
	bool UnderPrism(UWorld& World, const FVector2D& XY, double Ground)
	{
		FCollisionObjectQueryParams Hard;
		Hard.AddObjectTypesToQuery(DinkCollision::HardSolid);
		Hard.AddObjectTypesToQuery(DinkCollision::HardLow);
		FHitResult Hit;
		return World.LineTraceSingleByObjectType(Hit, FVector(XY.X, XY.Y, Ground + 450.0), FVector(XY.X, XY.Y, Ground - 50.0), Hard) && Hit.ImpactPoint.Z > Ground + 150.0;
	}

	double GroundAt(UWorld& World, const FVector2D& XY, const AActor* Ignore)
	{
		// The greybox ground is world Z 0; authored land (fitted terrain) is WorldStatic with collision. Roofs, ceilings and
		// furniture with collision are WorldStatic too: the ground is the lowest surface under the body (traced from 2.5 m).
		TArray<FHitResult> Hits;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkWalkAuditGround), true, Ignore);
		const FVector From(XY.X, XY.Y, 250.0), To(XY.X, XY.Y, -1500.0);
		World.LineTraceMultiByObjectType(Hits, From, To, FCollisionObjectQueryParams(ECC_WorldStatic), Params);
		double Lowest = TNumericLimits<double>::Max();
		for (const FHitResult& H : Hits) Lowest = FMath::Min(Lowest, H.ImpactPoint.Z);
		return Lowest == TNumericLimits<double>::Max() ? 0.0 : Lowest;
	}
}

void DinkWalkAudit::RasterSlice(const TArray<FVector>& V, const TArray<uint32>& Idx, double ZLow, double ZHigh,
	const FVector2D& Origin, double CellCm, const FIntPoint& Size, TArray<uint8>& Cells)
{
	Cells.Init(0, Size.X * Size.Y);
	TArray<FVector> Poly;
	for (int32 T = 0; T + 2 < Idx.Num(); T += 3)
	{
		const FVector& A = V[Idx[T]];
		const FVector& B = V[Idx[T + 1]];
		const FVector& C = V[Idx[T + 2]];
		if (FMath::Max3(A.Z, B.Z, C.Z) < ZLow || FMath::Min3(A.Z, B.Z, C.Z) > ZHigh) continue;
		Poly.Reset();
		Poly.Add(A); Poly.Add(B); Poly.Add(C);
		ClipZ(Poly, ZLow, true);
		if (Poly.Num() < 2) continue;
		ClipZ(Poly, ZHigh, false);
		if (Poly.Num() < 2) continue;
		// edges (a vertical triangle projects to a line)
		FVector2D Min(DBL_MAX), Max(-DBL_MAX);
		for (int32 I = 0; I < Poly.Num(); ++I)
		{
			const FVector2D P0 = (FVector2D(Poly[I]) - Origin) / CellCm;
			const FVector2D P1 = (FVector2D(Poly[(I + 1) % Poly.Num()]) - Origin) / CellCm;
			Min = FVector2D::Min(Min, P0); Max = FVector2D::Max(Max, P0);
			const int32 Steps = FMath::Max(1, FMath::CeilToInt(FVector2D::Distance(P0, P1) * 2.0));
			for (int32 S = 0; S <= Steps; ++S)
			{
				const FVector2D P = FMath::Lerp(P0, P1, double(S) / Steps);
				Mark(Cells, Size, FMath::FloorToInt(P.X), FMath::FloorToInt(P.Y));
			}
		}
		// interior of a sloped polygon: cell centres inside the convex polygon
		if (Max.X - Min.X < 1.0 && Max.Y - Min.Y < 1.0) continue;
		double Area = 0.0;
		TArray<FVector2D, TInlineAllocator<8>> P2;
		for (const FVector& P : Poly) P2.Add((FVector2D(P) - Origin) / CellCm);
		for (int32 I = 0; I < P2.Num(); ++I) Area += FVector2D::CrossProduct(P2[I], P2[(I + 1) % P2.Num()]);
		if (FMath::Abs(Area) < 1e-3) continue;
		const double Sign = Area > 0.0 ? 1.0 : -1.0;
		for (int32 Y = FMath::Max(0, FMath::FloorToInt(Min.Y)); Y <= FMath::Min(Size.Y - 1, FMath::CeilToInt(Max.Y)); ++Y)
			for (int32 X = FMath::Max(0, FMath::FloorToInt(Min.X)); X <= FMath::Min(Size.X - 1, FMath::CeilToInt(Max.X)); ++X)
			{
				const FVector2D Q(X + 0.5, Y + 0.5);
				bool bIn = true;
				for (int32 I = 0; I < P2.Num() && bIn; ++I) bIn = Sign * FVector2D::CrossProduct(P2[(I + 1) % P2.Num()] - P2[I], Q - P2[I]) >= 0.0;
				if (bIn) Cells[Y * Size.X + X] = 1;
			}
	}
}

TArray<FVector2D> DinkWalkAudit::ConvexHull(TArray<FVector2D> P, int32 MaxPoints)
{
	P.Sort([](const FVector2D& A, const FVector2D& B) { return A.X < B.X || (A.X == B.X && A.Y < B.Y); });
	TArray<FVector2D> H;
	if (P.Num() < 3) return P;
	auto Cross = [](const FVector2D& O, const FVector2D& A, const FVector2D& B) { return FVector2D::CrossProduct(A - O, B - O); };
	for (int32 I = 0; I < P.Num(); ++I)
	{
		while (H.Num() >= 2 && Cross(H[H.Num() - 2], H.Last(), P[I]) <= 0.0) H.Pop();
		H.Add(P[I]);
	}
	const int32 Lower = H.Num() + 1;
	for (int32 I = P.Num() - 2; I >= 0; --I)
	{
		while (H.Num() >= Lower && Cross(H[H.Num() - 2], H.Last(), P[I]) <= 0.0) H.Pop();
		H.Add(P[I]);
	}
	H.Pop();
	// fewer points: drop the vertex whose removal loses the least area (the hull only shrinks, never grows)
	while (H.Num() > MaxPoints)
	{
		int32 Best = 0;
		double BestArea = DBL_MAX;
		for (int32 I = 0; I < H.Num(); ++I)
		{
			const double A = FMath::Abs(Cross(H[(I + H.Num() - 1) % H.Num()], H[I], H[(I + 1) % H.Num()]));
			if (A < BestArea) { BestArea = A; Best = I; }
		}
		H.RemoveAt(Best);
	}
	return H;
}

void DinkWalkAudit::FillHoles(const FIntPoint& Size, TArray<uint8>& Cells)
{
	// flood the outside from the border over unset cells; every unset cell not reached is enclosed
	TArray<uint8> Outside;
	Outside.SetNumZeroed(Size.X * Size.Y);
	TArray<int32> Stack;
	auto Push = [&](int32 X, int32 Y)
	{
		if (X < 0 || Y < 0 || X >= Size.X || Y >= Size.Y) return;
		const int32 I = Y * Size.X + X;
		if (Cells[I] || Outside[I]) return;
		Outside[I] = 1;
		Stack.Add(I);
	};
	for (int32 X = 0; X < Size.X; ++X) { Push(X, 0); Push(X, Size.Y - 1); }
	for (int32 Y = 0; Y < Size.Y; ++Y) { Push(0, Y); Push(Size.X - 1, Y); }
	while (!Stack.IsEmpty())
	{
		const int32 I = Stack.Pop(EAllowShrinking::No);
		const int32 X = I % Size.X, Y = I / Size.X;
		Push(X + 1, Y); Push(X - 1, Y); Push(X, Y + 1); Push(X, Y - 1);
	}
	for (int32 I = 0; I < Cells.Num(); ++I) if (!Cells[I] && !Outside[I]) Cells[I] = 1;
}

void DinkWalkAudit::InsideDistance(const FIntPoint& Size, double CellCm, const TArray<uint8>& Cells, TArray<float>& D)
{
	// two-pass 3-4 chamfer; cells outside the grid count as unset
	const float Big = 1e9f;
	D.SetNumUninitialized(Size.X * Size.Y);
	for (int32 I = 0; I < D.Num(); ++I) D[I] = Cells[I] ? Big : 0.f;
	auto At = [&](int32 X, int32 Y) { return (X < 0 || Y < 0 || X >= Size.X || Y >= Size.Y) ? 0.f : D[Y * Size.X + X]; };
	for (int32 Y = 0; Y < Size.Y; ++Y)
		for (int32 X = 0; X < Size.X; ++X)
		{
			float& V = D[Y * Size.X + X];
			if (V == 0.f) continue;
			V = FMath::Min(V, FMath::Min(FMath::Min(At(X - 1, Y) + 3.f, At(X, Y - 1) + 3.f), FMath::Min(At(X - 1, Y - 1) + 4.f, At(X + 1, Y - 1) + 4.f)));
		}
	for (int32 Y = Size.Y - 1; Y >= 0; --Y)
		for (int32 X = Size.X - 1; X >= 0; --X)
		{
			float& V = D[Y * Size.X + X];
			if (V == 0.f) continue;
			V = FMath::Min(V, FMath::Min(FMath::Min(At(X + 1, Y) + 3.f, At(X, Y + 1) + 3.f), FMath::Min(At(X + 1, Y + 1) + 4.f, At(X - 1, Y + 1) + 4.f)));
		}
	// a set cell next to the edge is half a cell inside: distance in cells minus a half
	for (float& V : D) V = V > 0.f ? float((V / 3.f - 0.5f) * CellCm) : 0.f;
}

bool DinkWalkAudit::AuditScreen(UWorld& World, int32 ScreenNumber, TArray<FDinkWalkAuditRow>& OutRows, TArray<FDinkWalkAuditWall>& OutWalls, TArray<FString>& OutBlockers)
{
	UDinkGreyboxSubsystem* Grey = World.GetSubsystem<UDinkGreyboxSubsystem>();
	ADinkScreenVolume* Volume = Grey ? Grey->FindScreen(ScreenNumber) : nullptr;
	APlayerController* PC = World.GetFirstPlayerController();
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	const UCapsuleComponent* Capsule = Pawn ? Pawn->FindComponentByClass<UCapsuleComponent>() : nullptr;
	if (!Volume || !Capsule) return false;
	UGameInstance* GI = World.GetGameInstance();
	UDinkStorySubsystem* Story = GI ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
	const UDinkGameplay* Gameplay = Story ? Story->GetGameplay() : nullptr;
	auto ToPx = [&](const FVector& P)
	{
		double X = 0, Y = 0;
		DinkLayout::MetresToMapPixel(Volume->Corners, DinkLayout::UnrealToMetres(P), X, Y);
		return FVector2D(X, Y);
	};
	auto Hard = [&](const FVector2D& Px) { return Gameplay ? Gameplay->GetHard(ScreenNumber, FMath::FloorToInt(Px.X) + 20, FMath::FloorToInt(Px.Y)) : -1; };

	const float Radius = Capsule->GetScaledCapsuleRadius();
	const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
	const FCollisionShape Shape = FCollisionShape::MakeCapsule(Radius, HalfHeight);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkWalkAudit), false, Pawn);
	const FCollisionResponseParams Responses(Capsule->GetCollisionResponseToChannels());
	const ECollisionChannel Channel = Capsule->GetCollisionObjectType();
	// foot above the step height (35 cm), as a capsule that has walked up to the spot would be
	const double FootLift = 36.0;

	// --- items: every visible static mesh (and instance) whose centre is on this screen ---
	TArray<FItem> Items;
	for (TActorIterator<AActor> It(&World); It; ++It)
	{
		AActor* Owner = *It;
		if (Owner == Pawn || Owner->IsHidden()) continue;
		TInlineComponentArray<UStaticMeshComponent*> Components(Owner);
		for (UStaticMeshComponent* C : Components)
		{
			if (!C->IsRegistered() || !C->IsVisible() || C->bHiddenInGame || !C->GetStaticMesh()) continue;
			if (const ADinkGreyboxScreen* GS = Cast<ADinkGreyboxScreen>(Owner))
				if (C == GS->Visual || C == GS->CollisionSolid || C == GS->CollisionLow || C == GS->DebugBlockers) continue;
			if (C->GetAttachParent() && C->GetAttachParent()->GetOwner() == Pawn) continue;
			if (SkipMesh(MeshPath(C->GetStaticMesh()))) continue;
			const FString Kind = KindOf(*C, *Owner);
			if (UInstancedStaticMeshComponent* ISM = Cast<UInstancedStaticMeshComponent>(C))
			{
				for (int32 I = 0; I < ISM->GetInstanceCount(); ++I)
				{
					FTransform T;
					if (!ISM->GetInstanceTransform(I, T, true) || !Volume->ContainsWorldLocation(T.GetLocation())) continue;
					Items.Add({ C, I, T, Kind });
				}
			}
			else if (Volume->ContainsWorldLocation(C->Bounds.Origin))
			{
				Items.Add({ C, INDEX_NONE, C->GetComponentTransform(), Kind });
			}
		}
	}

	// screen occupancy at map-pixel resolution (for the invisible-wall check)
	TArray<uint8> Occupied;
	Occupied.SetNumZeroed(FDinkHardnessMap::Width * FDinkHardnessMap::Height);
	const double CmPerPx = FVector::Dist(Volume->MapPixelToWorld(0, 200), Volume->MapPixelToWorld(600, 200)) / 600.0;

	TArray<FVector> Verts;
	TArray<uint32> Indices;
	TArray<uint8> Cells;
	TArray<float> Depth;
	for (const FItem& Item : Items)
	{
		UStaticMesh* Mesh = Item.Component->GetStaticMesh();
		const FBox Local = Mesh->GetBoundingBox();
		const FBox World3 = Local.TransformBy(Item.Transform);
		const FVector Ext = World3.GetSize();
		if (Ext.X > 3000.0 || Ext.Y > 3000.0) continue; // land, sheets, whole-screen sets
		const double Ground = GroundAt(World, FVector2D(World3.GetCenter()), Item.Component->GetOwner());
		// A tree's body is its trunk: low limbs (drawn with the bark) reach into the body band of big pines and willows, and
		// walking under a branch is not walking into a tree. Trees are sliced below the lowest limbs.
		const FString TreePath = MeshPath(Mesh);
		const bool bTree = TreePath.Contains(TEXT("/Vegetation/")) && (TreePath.Contains(TEXT("Pine")) || TreePath.Contains(TEXT("Oak")) ||
			TreePath.Contains(TEXT("Willow")) || TreePath.Contains(TEXT("Tree")) || TreePath.Contains(TEXT("Stump")));
		const double ZLow = Ground + DinkWalkAudit::BandLowCm, ZHigh = Ground + (bTree ? DinkWalkAudit::TrunkBandHighCm : DinkWalkAudit::BandHighCm);
		if (World3.Max.Z < ZLow || World3.Min.Z > ZHigh + 400.0) continue;

		FDinkWalkAuditRow Row;
		Row.Screen = ScreenNumber;
		Row.Actor = Item.Component->GetOwner()->GetName();
		Row.Component = Item.Component->GetName();
		Row.Mesh = MeshPath(Mesh);
		Row.Kind = Item.Kind;
		Row.Instance = Item.Instance;
		if (const UDinkOriginComponent* O = UDinkOriginComponent::FindOnActor(Item.Component->GetOwner())) Row.Origin = O->OriginId.ToString();
		Row.Centre = World3.GetCenter();
		Row.CentrePx = ToPx(Row.Centre);
		Row.GroundZ = Ground;
		Row.SizeCm = FVector2D(Ext.X, Ext.Y);
		Row.HeightCm = World3.Max.Z - Ground;
		Row.CellCm = FMath::Max(5.0, FMath::Max(Ext.X, Ext.Y) / 300.0);
		const FVector2D Origin = FVector2D(World3.Min) - FVector2D(2.0 * Row.CellCm);
		const FIntPoint Size(FMath::CeilToInt(Ext.X / Row.CellCm) + 4, FMath::CeilToInt(Ext.Y / Row.CellCm) + 4);

		// triangles of LOD 0 (the Nanite fallback for Nanite meshes), in world space
		Verts.Reset(); Indices.Reset();
		const FStaticMeshRenderData* RD = Mesh->GetRenderData();
		if (RD && RD->LODResources.Num() > 0)
		{
			const FStaticMeshLODResources& LOD = RD->LODResources[0];
			const FPositionVertexBuffer& PB = LOD.VertexBuffers.PositionVertexBuffer;
			if (PB.GetNumVertices() > 0 && PB.GetVertexData() && LOD.IndexBuffer.GetNumIndices() > 0 && LOD.IndexBuffer.GetArrayView().Num() > 0)
			{
				Verts.SetNumUninitialized(PB.GetNumVertices());
				for (uint32 I = 0; I < PB.GetNumVertices(); ++I) Verts[I] = Item.Transform.TransformPosition(FVector(PB.VertexPosition(I)));
				// only the solid parts: sections drawn with foliage materials (needles, leaves, moss) are soft to walk through
				TArray<uint32> All;
				LOD.IndexBuffer.GetCopy(All);
				for (const FStaticMeshSection& Section : LOD.Sections)
				{
					const UMaterialInterface* M = Item.Component->GetMaterial(Section.MaterialIndex);
					const FString Name = (M ? M->GetName() : FString()) + TEXT("|") +
						(Mesh->GetStaticMaterials().IsValidIndex(Section.MaterialIndex) ? Mesh->GetStaticMaterials()[Section.MaterialIndex].MaterialSlotName.ToString() : FString());
					if (SoftMaterial(Name)) { ++Row.SoftSections; continue; }
					for (uint32 K = 0; K < Section.NumTriangles * 3; ++K) Indices.Add(All[Section.FirstIndex + K]);
				}
				if (Indices.IsEmpty() && Row.SoftSections > 0) continue; // all foliage
			}
		}
		if (Indices.IsEmpty())
		{
			// no CPU geometry: the bounds box (8 corners, 12 triangles)
			Row.bBoundsOnly = true;
			FVector Corners[8];
			Local.GetVertices(Corners);
			for (const FVector& V : Corners) Verts.Add(Item.Transform.TransformPosition(V));
			static const uint32 Box[36] = { 0,1,2, 1,3,2, 4,6,5, 5,6,7, 0,4,1, 1,4,5, 2,3,6, 3,7,6, 0,2,4, 2,6,4, 1,5,3, 3,5,7 };
			Indices.Append(Box, 36);
		}
		DinkWalkAudit::RasterSlice(Verts, Indices, ZLow, ZHigh, Origin, Row.CellCm, Size, Cells);
		{
			// the slice's vertices in the mesh's own space: the hull a player-only blocker would use
			TArray<FVector2D> LocalPoints;
			TArray<FVector> Poly;
			for (int32 T = 0; T + 2 < Indices.Num(); T += 3)
			{
				Poly.Reset();
				Poly.Add(Verts[Indices[T]]); Poly.Add(Verts[Indices[T + 1]]); Poly.Add(Verts[Indices[T + 2]]);
				ClipZ(Poly, ZLow, true);
				if (Poly.Num() >= 2) ClipZ(Poly, ZHigh, false);
				for (const FVector& V : Poly) LocalPoints.Add(FVector2D(Item.Transform.InverseTransformPosition(V)));
			}
			Row.LocalHull = DinkWalkAudit::ConvexHull(MoveTemp(LocalPoints));
			if (bTree)
			{
				// A tree's body is its trunk: the narrowest of its cross-sections between 20 and 140 cm, taken near the
				// mesh's own axis (limbs and roots further out are left to the eye), as a 12-sided prism.
				FVector2D BestCentre(0.0);
				double BestRadius = TNumericLimits<double>::Max();
				for (double Lo = 20.0; Lo < 140.0; Lo += 20.0)
				{
					FBox2D Box(ForceInit);
					TArray<FVector2D> Near;
					for (int32 T = 0; T + 2 < Indices.Num(); T += 3)
					{
						Poly.Reset();
						Poly.Add(Verts[Indices[T]]); Poly.Add(Verts[Indices[T + 1]]); Poly.Add(Verts[Indices[T + 2]]);
						ClipZ(Poly, Ground + Lo, true);
						if (Poly.Num() >= 2) ClipZ(Poly, Ground + Lo + 20.0, false);
						for (const FVector& V : Poly)
						{
							const FVector2D L(Item.Transform.InverseTransformPosition(V));
							if (L.Size() <= 120.0) { Near.Add(L); Box += L; }
						}
					}
					if (Near.Num() < 6) continue;
					const FVector2D C = Box.GetCenter();
					double R = 0.0;
					for (const FVector2D& L : Near) R = FMath::Max(R, FVector2D::Distance(L, C));
					if (R < BestRadius) { BestRadius = R; BestCentre = C; }
				}
				if (BestRadius < 200.0)
				{
					Row.LocalHull.Reset();
					for (int32 K = 0; K < 12; ++K) Row.LocalHull.Add(BestCentre + FVector2D(FMath::Cos(K * PI / 6.0), FMath::Sin(K * PI / 6.0)) * BestRadius);
					// the footprint is that trunk too: walking under the limbs is not walking into the tree
					TArray<FVector> Trunk;
					TArray<uint32> Fan;
					for (const FVector2D& L : Row.LocalHull)
					{
						Trunk.Add(Item.Transform.TransformPosition(FVector(L.X, L.Y, 0.0)) + FVector(0, 0, ZLow + 1.0 - Item.Transform.TransformPosition(FVector(L.X, L.Y, 0.0)).Z));
						Trunk.Add(Trunk.Last() + FVector(0, 0, 10.0));
					}
					for (int32 K = 1; K + 1 < Row.LocalHull.Num(); ++K) Fan.Append({ 0u, uint32(2 * K), uint32(2 * K + 2) });
					DinkWalkAudit::RasterSlice(Trunk, Fan, ZLow, ZHigh, Origin, Row.CellCm, Size, Cells);
				}
			}
			Row.LocalZLow = Item.Transform.InverseTransformPosition(FVector(Row.Centre.X, Row.Centre.Y, Ground - 10.0)).Z;
			Row.LocalZHigh = Item.Transform.InverseTransformPosition(FVector(Row.Centre.X, Row.Centre.Y, Ground + 160.0)).Z;
		}
		DinkWalkAudit::FillHoles(Size, Cells);
		DinkWalkAudit::InsideDistance(Size, Row.CellCm, Cells, Depth);
		for (uint8 C : Cells) Row.FootprintCells += C;
		Row.FootprintM2 = Row.FootprintCells * FMath::Square(Row.CellCm / 100.0);
		if (Row.FootprintCells == 0) continue;
		Row.HardAtCentre = Hard(Row.CentrePx);

		// mark the screen occupancy (every drawn thing, cards included)
		for (int32 Y = 0; Y < Size.Y; ++Y)
			for (int32 X = 0; X < Size.X; ++X)
			{
				if (!Cells[Y * Size.X + X]) continue;
				const FVector2D Px = ToPx(FVector(Origin.X + (X + 0.5) * Row.CellCm, Origin.Y + (Y + 0.5) * Row.CellCm, 0.0));
				const int32 PX = FMath::FloorToInt(Px.X), PY = FMath::FloorToInt(Px.Y);
				if (PX >= 0 && PY >= 0 && PX < FDinkHardnessMap::Width && PY < FDinkHardnessMap::Height) Occupied[PY * FDinkHardnessMap::Width + PX] = 1;
			}
		if (Row.Kind == TEXT("card")) { OutRows.Add(Row); continue; }

		// Where may the capsule centre stand inside the footprint? The hardness collision is a trimesh of prisms: a capsule
		// wholly inside a prism touches no triangle, so an overlap test alone calls the inside of a wide hardbox free. Cells are
		// therefore free only when reachable: a flood from the free (get_hard 0) edge of a grid around the footprint, through
		// cells where the capsule overlaps nothing, in steps of at most 15 cm (a wall's blocked band is the capsule's width).
		{
			const int32 Step = FMath::Max(1, FMath::FloorToInt(15.0 / Row.CellCm));
			const int32 Margin = FMath::CeilToInt(80.0 / (Row.CellCm * Step));
			const int32 GX = FMath::CeilToInt(double(Size.X) / Step) + 2 * Margin, GY = FMath::CeilToInt(double(Size.Y) / Step) + 2 * Margin;
			auto CellAt = [&](int32 X, int32 Y) { return FVector(Origin.X + ((X - Margin) * Step + 0.5) * Row.CellCm, Origin.Y + ((Y - Margin) * Step + 0.5) * Row.CellCm, 0.0); };
			TArray<int8> Free; // -1 unknown, 0 blocked, 1 free
			Free.Init(-1, GX * GY);
			TArray<double> GroundZ;
			GroundZ.Init(0.0, GX * GY);
			auto IsFree = [&](int32 X, int32 Y)
			{
				int8& F = Free[Y * GX + X];
				if (F < 0)
				{
					const FVector At = CellAt(X, Y);
					const double G = GroundAt(World, FVector2D(At), nullptr);
					GroundZ[Y * GX + X] = G;
					F = World.OverlapBlockingTestByChannel(FVector(At.X, At.Y, G + FootLift + HalfHeight), FQuat::Identity, Channel, Shape, Params, Responses) ||
						UnderPrism(World, FVector2D(At), G) ? 0 : 1;
				}
				return F == 1;
			};
			TArray<uint8> Reached;
			Reached.Init(0, GX * GY);
			TArray<int32> Stack;
			for (int32 Y = 0; Y < GY; ++Y)
				for (int32 X = 0; X < GX; ++X)
				{
					if (X != 0 && Y != 0 && X != GX - 1 && Y != GY - 1) continue;
					if (Hard(ToPx(CellAt(X, Y))) != 0 || !IsFree(X, Y)) continue;
					Reached[Y * GX + X] = 1;
					Stack.Add(Y * GX + X);
				}
			// a grid larger than ~12,000 cells (a whole wall run) is flooded only near its free edge: the overlap tests are the cost
			int32 Budget = 12000;
			while (!Stack.IsEmpty() && Budget-- > 0)
			{
				const int32 I = Stack.Pop(EAllowShrinking::No);
				const int32 X = I % GX, Y = I / GX;
				const FIntPoint N[4] = { {X + 1, Y}, {X - 1, Y}, {X, Y + 1}, {X, Y - 1} };
				for (const FIntPoint& Q : N)
				{
					if (Q.X < 0 || Q.Y < 0 || Q.X >= GX || Q.Y >= GY || Reached[Q.Y * GX + Q.X] || !IsFree(Q.X, Q.Y)) continue;
					Reached[Q.Y * GX + Q.X] = 1;
					Stack.Add(Q.Y * GX + Q.X);
				}
			}
			for (int32 Y = 0; Y < GY; ++Y)
				for (int32 X = 0; X < GX; ++X)
				{
					const int32 FX = (X - Margin) * Step, FY = (Y - Margin) * Step;
					if (FX < 0 || FY < 0 || FX >= Size.X || FY >= Size.Y || !Cells[FY * Size.X + FX]) continue;
					++Row.TestedCells;
					if (!Reached[Y * GX + X]) continue;
					++Row.AllowedCells;
					if (Depth[FY * Size.X + FX] > Row.DepthCm)
					{
						Row.DepthCm = Depth[FY * Size.X + FX];
						Row.DeepestAt = FVector(CellAt(X, Y).X, CellAt(X, Y).Y, GroundZ[Y * GX + X]);
					}
				}
		}
		if (Row.AllowedCells > 0)
		{
			Row.DeepestPx = ToPx(Row.DeepestAt);
			Row.HardAtDeepest = Hard(Row.DeepestPx);
		}
		OutRows.Add(Row);
	}

	// --- player-only blockers on this screen, as map-pixel polygons (Scripts: the connectivity check) ---
#if DINK_WALKAUDIT_BLOCKERS
	for (TActorIterator<AActor> It(&World); It; ++It)
	{
		TInlineComponentArray<UDinkPlayerBlockerComponent*> Blockers(*It);
		for (const UDinkPlayerBlockerComponent* B : Blockers)
		{
			const FDinkPlayerBlockerShape* S = B->Mesh.IsValid() ? DinkPlayerBlockers::Find(B->Mesh.Get()) : nullptr;
			if (!S || !Volume->ContainsWorldLocation(B->GetComponentLocation())) continue;
			FString Poly;
			for (const FVector2D& P : S->HullCm)
			{
				const FVector2D Px = ToPx(B->GetComponentTransform().TransformPosition(FVector(P.X, P.Y, 0.0)));
				Poly += FString::Printf(TEXT("%s%.1f:%.1f"), Poly.IsEmpty() ? TEXT("") : TEXT(";"), Px.X, Px.Y);
			}
			OutBlockers.Add(FString::Printf(TEXT("%d,%s,%s,%d,%s"), ScreenNumber, *It->GetName(), *S->Mesh, B->IsDrawnShown() ? 1 : 0, *Poly));
		}
	}
#endif

	// --- invisible walls: stamped sprite hardboxes (100 + n) away from every footprint ---
	if (Gameplay)
	{
		// distance (px) to the nearest occupied pixel, chamfer over the map
		TArray<float> Free;
		{
			TArray<uint8> NotOcc;
			NotOcc.SetNumUninitialized(Occupied.Num());
			for (int32 I = 0; I < Occupied.Num(); ++I) NotOcc[I] = Occupied[I] ? 0 : 1;
			DinkWalkAudit::InsideDistance(FIntPoint(FDinkHardnessMap::Width, FDinkHardnessMap::Height), CmPerPx, NotOcc, Free);
		}
		TMap<int32, FDinkWalkAuditWall> Walls;
		for (int32 Y = 0; Y < FDinkHardnessMap::Height; ++Y)
			for (int32 X = 0; X < FDinkHardnessMap::Width; ++X)
			{
				const int32 Code = Gameplay->GetHard(ScreenNumber, X + 20, Y);
				if (Code < 100) continue;
				FDinkWalkAuditWall& W = Walls.FindOrAdd(Code - 100);
				if (W.Pixels == 0) { W.Screen = ScreenNumber; W.Placement = Code - 100; W.MinPx = FVector2D(X, Y); W.MaxPx = FVector2D(X, Y); }
				++W.Pixels;
				W.MinPx = FVector2D::Min(W.MinPx, FVector2D(X, Y));
				W.MaxPx = FVector2D::Max(W.MaxPx, FVector2D(X, Y));
				const double Cm = Free[Y * FDinkHardnessMap::Width + X];
				if (Cm > DinkWalkAudit::WallToleranceCm) ++W.BarePixels;
				W.MaxDistanceCm = FMath::Max(W.MaxDistanceCm, Cm);
			}
		for (auto& Pair : Walls)
		{
			Pair.Value.CentrePx = (Pair.Value.MinPx + Pair.Value.MaxPx) * 0.5;
			OutWalls.Add(Pair.Value);
		}
	}
	return true;
}

FString DinkWalkAudit::WalkMask(UWorld& World, int32 ScreenNumber, int32 Step)
{
	// Where the player's capsule centre may stand on the screen without the player-only blockers: free of every overlap
	// (blockers ignored) and not under a hardness prism. One character per Step x Step map pixels, row by row, run-length
	// coded as <count><F|B> pairs (F free, B blocked). Scripts/check_player_blockers.py adds the blockers back to see what they cut off.
	UDinkGreyboxSubsystem* Grey = World.GetSubsystem<UDinkGreyboxSubsystem>();
	ADinkScreenVolume* Volume = Grey ? Grey->FindScreen(ScreenNumber) : nullptr;
	APlayerController* PC = World.GetFirstPlayerController();
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	const UCapsuleComponent* Capsule = Pawn ? Pawn->FindComponentByClass<UCapsuleComponent>() : nullptr;
	if (!Volume || !Capsule) return FString();
	FCollisionResponseContainer R = Capsule->GetCollisionResponseToChannels();
#if DINK_WALKAUDIT_BLOCKERS
	R.SetResponse(DinkCollision::PlayerBlock, ECR_Ignore);
#endif
	const FCollisionResponseParams Responses(R);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkWalkMask), false, Pawn);
	const FCollisionShape Shape = FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight());
	FString Out;
	TCHAR Last = 0;
	int32 Run = 0;
	auto Emit = [&](TCHAR C) { if (C == Last) { ++Run; return; } if (Run) Out += FString::Printf(TEXT("%d%c"), Run, Last); Last = C; Run = 1; };
	for (int32 Y = 0; Y < FDinkHardnessMap::Height; Y += Step)
		for (int32 X = 0; X < FDinkHardnessMap::Width; X += Step)
		{
			const FVector At = Volume->MapPixelToWorld(X + Step * 0.5, Y + Step * 0.5);
			const double G = GroundAt(World, FVector2D(At), nullptr);
			const bool bFree = !UnderPrism(World, FVector2D(At), G) &&
				!World.OverlapBlockingTestByChannel(FVector(At.X, At.Y, G + 36.0 + Capsule->GetScaledCapsuleHalfHeight()), FQuat::Identity,
					Capsule->GetCollisionObjectType(), Shape, Params, Responses);
			Emit(bFree ? TEXT('F') : TEXT('B'));
		}
	Emit(0);
	return Out;
}

FString DinkWalkAudit::RowCsvHeader()
{
	return TEXT("screen,kind,origin,actor,component,instance,mesh,centre_px_x,centre_px_y,centre_x,centre_y,ground_z,size_x_cm,size_y_cm,height_cm,cell_cm,footprint_m2,tested,allowed,depth_cm,deepest_px_x,deepest_px_y,deepest_x,deepest_y,hard_at_deepest,hard_at_centre,bounds_only,soft_sections");
}

FString DinkWalkAudit::RowCsv(const FDinkWalkAuditRow& R)
{
	return FString::Printf(TEXT("%d,%s,%s,%s,%s,%d,%s,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.3f,%d,%d,%.1f,%.1f,%.1f,%.1f,%.1f,%d,%d,%d,%d"),
		R.Screen, *R.Kind, *R.Origin, *R.Actor, *R.Component, R.Instance, *R.Mesh, R.CentrePx.X, R.CentrePx.Y, R.Centre.X, R.Centre.Y, R.GroundZ,
		R.SizeCm.X, R.SizeCm.Y, R.HeightCm, R.CellCm, R.FootprintM2, R.TestedCells, R.AllowedCells, R.DepthCm, R.DeepestPx.X, R.DeepestPx.Y,
		R.DeepestAt.X, R.DeepestAt.Y, R.HardAtDeepest, R.HardAtCentre, R.bBoundsOnly ? 1 : 0, R.SoftSections);
}

FString DinkWalkAudit::HullCsvHeader() { return TEXT("mesh,screen,origin,instance,local_z_low,local_z_high,hull"); }

FString DinkWalkAudit::HullCsv(const FDinkWalkAuditRow& R)
{
	FString Hull;
	for (const FVector2D& P : R.LocalHull) Hull += FString::Printf(TEXT("%s%.1f:%.1f"), Hull.IsEmpty() ? TEXT("") : TEXT(";"), P.X, P.Y);
	return FString::Printf(TEXT("%s,%d,%s,%d,%.1f,%.1f,%s"), *R.Mesh, R.Screen, *R.Origin, R.Instance, R.LocalZLow, R.LocalZHigh, *Hull);
}

FString DinkWalkAudit::MaskCsvHeader() { return TEXT("screen,step,mask"); }

FString DinkWalkAudit::WallCsvHeader() { return TEXT("screen,placement,pixels,bare_pixels,max_distance_cm,centre_px_x,centre_px_y,min_px_x,min_px_y,max_px_x,max_px_y"); }

FString DinkWalkAudit::WallCsv(const FDinkWalkAuditWall& W)
{
	return FString::Printf(TEXT("%d,%d,%d,%d,%.1f,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f"), W.Screen, W.Placement, W.Pixels, W.BarePixels, W.MaxDistanceCm,
		W.CentrePx.X, W.CentrePx.Y, W.MinPx.X, W.MinPx.Y, W.MaxPx.X, W.MaxPx.Y);
}

// ---------------------------------------------------------------------------------------------------------------------------
// dink.WalkAudit <first> <last> <out dir> [quit]: visits each screen (teleport to a free pixel near the middle, then waits
// for the art layers that dress a screen in range), audits it and appends to <out dir>/walk_audit.csv and walk_walls.csv.
namespace
{
	struct FWalkAuditRun
	{
		TWeakObjectPtr<UWorld> World;
		TArray<int32> Screens;
		int32 Next = 0;
		int32 Phase = 0;
		uint64 ArriveFrame = 0;
		double ArriveTime = 0.0;
		FString Dir;
		bool bQuit = false;
	};

	bool FreePixel(UWorld& World, int32 Screen, FVector2D& Out)
	{
		UGameInstance* GI = World.GetGameInstance();
		UDinkStorySubsystem* Story = GI ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		const UDinkGameplay* G = Story ? Story->GetGameplay() : nullptr;
		for (int32 R = 0; R < 200; R += 6)
			for (int32 A = 0; A < 16; ++A)
			{
				const double Ang = A * PI / 8.0;
				const int32 X = 300 + FMath::RoundToInt(R * FMath::Cos(Ang) * 1.4), Y = 200 + FMath::RoundToInt(R * FMath::Sin(Ang));
				if (X < 30 || Y < 30 || X > 570 || Y > 370) continue;
				bool bFree = true;
				for (int32 DY = -12; DY <= 12 && bFree; DY += 4)
					for (int32 DX = -12; DX <= 12 && bFree; DX += 4) bFree = !G || G->GetHard(Screen, X + DX + 20, Y + DY) == 0;
				if (bFree) { Out = FVector2D(X, Y); return true; }
			}
		Out = FVector2D(300, 200);
		return false;
	}

	bool TickWalkAudit(TSharedRef<FWalkAuditRun> Run)
	{
		UWorld* World = Run->World.Get();
		if (!World) return false;
		UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
		if (!Grey) return false;
		if (Run->Next >= Run->Screens.Num())
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("DINK WALKAUDIT: done, %d screens"), Run->Screens.Num());
			if (Run->bQuit && GEngine) GEngine->Exec(World, TEXT("quit"));
			return false;
		}
		const int32 Screen = Run->Screens[Run->Next];
		if (Run->Phase == 0)
		{
			FVector2D Px;
			FreePixel(*World, Screen, Px);
			Grey->GotoScreen(Screen, Px.X, Px.Y);
			Run->Phase = 1;
			Run->ArriveFrame = GFrameCounter;
			Run->ArriveTime = FPlatformTime::Seconds();
			return true;
		}
		if (GFrameCounter - Run->ArriveFrame < 20 || FPlatformTime::Seconds() - Run->ArriveTime < 0.6) return true;
		// the family layer dresses a screen in range; make sure this one is dressed whatever the teleport did
		if (UDinkArtFamilySubsystem* F = World->GetSubsystem<UDinkArtFamilySubsystem>()) if (F->IsReady() && !F->IsScreenApplied(Screen)) F->ApplyScreen(Screen);
		TArray<FDinkWalkAuditRow> Rows;
		TArray<FDinkWalkAuditWall> Walls;
		TArray<FString> Blockers;
		const double T0 = FPlatformTime::Seconds();
		DinkWalkAudit::AuditScreen(*World, Screen, Rows, Walls, Blockers);
		FFileHelper::SaveStringToFile(FString::Printf(TEXT("%d,3,%s\n"), Screen, *DinkWalkAudit::WalkMask(*World, Screen, 3)), *(Run->Dir / TEXT("walk_mask.csv")),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
		FFileHelper::SaveStringToFile(FString::Join(Blockers, TEXT("\n")) + (Blockers.IsEmpty() ? TEXT("") : TEXT("\n")), *(Run->Dir / TEXT("walk_blockers.csv")),
			FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
		FString Text, WallText, HullText;
		int32 Deep = 0;
		for (const FDinkWalkAuditRow& R : Rows) { Text += DinkWalkAudit::RowCsv(R) + TEXT("\n"); Deep += R.DepthCm >= 20.0 && R.Kind != TEXT("card"); }
		for (const FDinkWalkAuditRow& R : Rows) if (R.DepthCm >= 10.0 && R.Kind != TEXT("card")) HullText += DinkWalkAudit::HullCsv(R) + TEXT("\n");
		FFileHelper::SaveStringToFile(HullText, *(Run->Dir / TEXT("walk_hulls.csv")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
		for (const FDinkWalkAuditWall& W : Walls) WallText += DinkWalkAudit::WallCsv(W) + TEXT("\n");
		FFileHelper::SaveStringToFile(Text, *(Run->Dir / TEXT("walk_audit.csv")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
		FFileHelper::SaveStringToFile(WallText, *(Run->Dir / TEXT("walk_walls.csv")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
		UE_LOG(LogDinkNarrative, Display, TEXT("DINK WALKAUDIT: SCR_%03d items %d, walk-in >= 20 cm %d, hardboxes %d (%.0f ms)"),
			Screen, Rows.Num(), Deep, Walls.Num(), (FPlatformTime::Seconds() - T0) * 1000.0);
		++Run->Next;
		Run->Phase = 0;
		return true;
	}
}

static FAutoConsoleCommandWithWorldAndArgs GDinkWalkAuditCommand(
	TEXT("dink.WalkAudit"),
	TEXT("dink.WalkAudit <first> <last> <out dir> [quit]: per screen, where the player's capsule can stand inside a drawn mesh's body-height footprint, and stamped hardboxes with nothing drawn (walk_audit.csv, walk_walls.csv)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || Args.Num() < 3)
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("usage: dink.WalkAudit <first> <last> <out dir> [quit]"));
			return;
		}
		TSharedRef<FWalkAuditRun> Run = MakeShared<FWalkAuditRun>();
		Run->World = World;
		Run->Dir = Args[2];
		Run->bQuit = Args.Num() > 3 && Args[3] == TEXT("quit");
		UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
		for (int32 S = FCString::Atoi(*Args[0]); S <= FCString::Atoi(*Args[1]); ++S) if (Grey && Grey->FindScreen(S)) Run->Screens.Add(S);
		IFileManager::Get().MakeDirectory(*Run->Dir, true);
		FFileHelper::SaveStringToFile(DinkWalkAudit::RowCsvHeader() + TEXT("\n"), *(Run->Dir / TEXT("walk_audit.csv")));
		FFileHelper::SaveStringToFile(DinkWalkAudit::WallCsvHeader() + TEXT("\n"), *(Run->Dir / TEXT("walk_walls.csv")));
		FFileHelper::SaveStringToFile(DinkWalkAudit::HullCsvHeader() + TEXT("\n"), *(Run->Dir / TEXT("walk_hulls.csv")));
		FFileHelper::SaveStringToFile(TEXT("screen,actor,mesh,enabled,polygon_px\n"), *(Run->Dir / TEXT("walk_blockers.csv")));
		FFileHelper::SaveStringToFile(DinkWalkAudit::MaskCsvHeader() + TEXT("\n"), *(Run->Dir / TEXT("walk_mask.csv")));
		UE_LOG(LogDinkNarrative, Display, TEXT("DINK WALKAUDIT: %d screens"), Run->Screens.Num());
		FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Run](float) { return TickWalkAudit(Run); }));
	}));
