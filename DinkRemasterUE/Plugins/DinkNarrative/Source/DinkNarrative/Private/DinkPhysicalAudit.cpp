#include "DinkPhysicalAudit.h"
#include "DinkGameplay.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "DinkNarrativeTypes.h"
#include "DinkLayout.h"
#include "DinkOriginComponent.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkArtFamilySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkWarpComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Containers/Ticker.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "StaticMeshResources.h"

// ---------------------------------------------------------------------------------------------------------------------------
// Pure helpers

void DinkPhysicalAudit::DistanceToSet(const FIntPoint& Size, const TArray<uint8>& Mask, TArray<float>& D)
{
	const float Big = 1e9f;
	D.SetNumUninitialized(Size.X * Size.Y);
	for (int32 I = 0; I < D.Num(); ++I) D[I] = Mask[I] ? 0.f : Big;
	auto At = [&](int32 X, int32 Y) { return (X < 0 || Y < 0 || X >= Size.X || Y >= Size.Y) ? Big : D[Y * Size.X + X]; };
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
	for (float& V : D) V = V >= Big * 0.5f ? Big : V / 3.f;
}

DinkPhysicalAudit::FMaskCompare DinkPhysicalAudit::Compare(const FIntPoint& Size, const TArray<uint8>& H, const TArray<uint8>& F, double TolPx)
{
	FMaskCompare R;
	TArray<float> DF, DH;
	DistanceToSet(Size, F, DF);
	DistanceToSet(Size, H, DH);
	FVector2D SumH(0.0), SumF(0.0);
	int32 Both = 0, Either = 0, Covered = 0, Over = 0;
	for (int32 Y = 0; Y < Size.Y; ++Y)
		for (int32 X = 0; X < Size.X; ++X)
		{
			const int32 I = Y * Size.X + X;
			const bool bH = H[I] != 0, bF = F[I] != 0;
			if (bH) { ++R.HCells; SumH += FVector2D(X, Y); if (DF[I] <= TolPx) ++Covered; R.MaxBareDistance = FMath::Max(R.MaxBareDistance, double(FMath::Min(DF[I], 9999.f))); }
			if (bF) { ++R.FCells; SumF += FVector2D(X, Y); if (DH[I] > TolPx) ++Over; }
			Both += bH && bF;
			Either += bH || bF;
		}
	R.Cover = R.HCells ? double(Covered) / R.HCells : 0.0;
	R.Overhang = R.FCells ? double(Over) / R.FCells : 0.0;
	R.IoU = Either ? double(Both) / Either : 0.0;
	if (R.HCells && R.FCells) R.Offset = SumF / R.FCells - SumH / R.HCells;
	return R;
}

FString DinkPhysicalAudit::OriginCsvHeader()
{
	return TEXT("screen,origin,handle,type,live,brain,script,seq,frame,size,touch_damage,nohit,warp,hard_flag,authored,fitted,class,")
		TEXT("sprite_x,sprite_y,box_l,box_t,box_r,box_b,stamped_px,bare_stamped_px,cm_per_px,items,kinds,mesh,visible,")
		TEXT("own_px,own_l,own_t,own_r,own_b,own_cx,own_cy,cover_own,overhang_own,iou_own,offset_x,offset_y,max_bare_px,cover_all,")
		TEXT("body_px,body_l,body_t,body_r,body_b,inside_other,capsule_blocked,actor_dx,actor_dy");
}

FString DinkPhysicalAudit::WarpCsvHeader()
{
	return TEXT("screen,warp,origin,kind,mode,enabled,dest_screen,box_l,box_t,box_r,box_b,own_px,own_l,own_t,own_r,own_b,gap_px,cm_per_px,box_cover,drawn_near_px");
}

FString DinkPhysicalAudit::TileCsvHeader()
{
	return TEXT("screen,code,pixels,l,t,r,b,cx,cy,max_dist_px,ground_rise_cm,cm_per_px");
}

FString DinkPhysicalAudit::ScreenCsvHeader()
{
	return TEXT("screen,cm_per_px,origins,live,drawn_items,solid_tile_px,bare_tile_px,stamped_px,bare_stamped_px,ms,player_on_screen");
}

// ---------------------------------------------------------------------------------------------------------------------------
namespace
{
	// --- body-height slice raster (the same method as the walk-through audit of PR #129, kept here so this audit stands alone) ---
	constexpr double BandLowCm = 15.0;
	constexpr double BandHighCm = 120.0;
	/** Trees (trunks) are sliced up to here: below the lowest limbs of the big pines and willows. */
	constexpr double TrunkBandHighCm = 60.0;

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
			if (InA != InB) Out.Add(A + (B - A) * ((Z - A.Z) / (B.Z - A.Z)));
		}
		Poly = MoveTemp(Out);
	}

	/** Cells (CellCm, grid at Origin, Size cells) covered by the triangles' part between ZLow and ZHigh: edges and sloped interiors. */
	void RasterSlice(const TArray<FVector>& V, const TArray<uint32>& Idx, double ZLow, double ZHigh, const FVector2D& Origin, double CellCm,
		const FIntPoint& Size, TArray<uint8>& Cells)
	{
		Cells.Init(0, Size.X * Size.Y);
		auto Mark = [&](int32 X, int32 Y) { if (X >= 0 && Y >= 0 && X < Size.X && Y < Size.Y) Cells[Y * Size.X + X] = 1; };
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
					Mark(FMath::FloorToInt(P.X), FMath::FloorToInt(P.Y));
				}
			}
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

	/** Unset cells enclosed by set ones become set (a closed shell's slice is a ring; its inside is solid). */
	void FillHoles(const FIntPoint& Size, TArray<uint8>& Cells)
	{
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

	bool SoftMaterial(const FString& Name)
	{
		static const TCHAR* Soft[] = { TEXT("Leaf"), TEXT("Leaves"), TEXT("Needle"), TEXT("Foliage"), TEXT("Canopy"), TEXT("Moss"), TEXT("Grass"),
			TEXT("Fern"), TEXT("Frond"), TEXT("Twig"), TEXT("Blossom"), TEXT("Flower"), TEXT("Understory") };
		for (const TCHAR* S : Soft) if (Name.Contains(S)) return true;
		return false;
	}

	bool SkipMesh(const FString& Path)
	{
		static const TCHAR* Skip[] = { TEXT("Grass"), TEXT("grass"), TEXT("Clover"), TEXT("Flower"), TEXT("Decal"), TEXT("LeafLitter"),
			TEXT("/Engine/"), TEXT("_Generated/Meshes/SM_Screen"), TEXT("Ground"), TEXT("Terrain"), TEXT("Water"), TEXT("Sky") };
		for (const TCHAR* S : Skip) if (Path.Contains(S)) return true;
		return false;
	}

	bool IsTreePath(const FString& P)
	{
		return P.Contains(TEXT("/Vegetation/")) && (P.Contains(TEXT("Pine")) || P.Contains(TEXT("Oak")) || P.Contains(TEXT("Willow")) ||
			P.Contains(TEXT("Tree")) || P.Contains(TEXT("Stump")));
	}

	double GroundAt(UWorld& World, const FVector2D& XY, const AActor* Ignore)
	{
		TArray<FHitResult> Hits;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkPhysAuditGround), true, Ignore);
		World.LineTraceMultiByObjectType(Hits, FVector(XY.X, XY.Y, 250.0), FVector(XY.X, XY.Y, -1500.0), FCollisionObjectQueryParams(ECC_WorldStatic), Params);
		double Lowest = TNumericLimits<double>::Max();
		for (const FHitResult& H : Hits) Lowest = FMath::Min(Lowest, H.ImpactPoint.Z);
		return Lowest == TNumericLimits<double>::Max() ? 0.0 : Lowest;
	}

	/** A map-pixel mask over a window of the screen (the window may reach past the map's edges). */
	struct FPxMask
	{
		FIntPoint Min = FIntPoint(0, 0);
		FIntPoint Size = FIntPoint(0, 0);
		TArray<uint8> Cells;
		void Init(const FIntPoint& InMin, const FIntPoint& InSize) { Min = InMin; Size = InSize; Cells.Init(0, Size.X * Size.Y); }
		bool Get(int32 X, int32 Y) const { X -= Min.X; Y -= Min.Y; return X >= 0 && Y >= 0 && X < Size.X && Y < Size.Y && Cells[Y * Size.X + X]; }
	};

	/** What draws one placement or sprite, gathered from the world. */
	struct FDrawn
	{
		TArray<FIntPoint> Px; // footprint pixels (map pixels; duplicates allowed)
		FBox2D BodyPx = FBox2D(ForceInit); // skeletal bodies (bounds)
		int32 Items = 0;
		TSet<FString> Kinds;
		FString Mesh;
		bool bVisible = false;
	};

	/** Local affine map world XY (cm) -> map pixel, exact at Centre (the layout is a bilinear sheet, near-affine over metres). */
	struct FPxAffine
	{
		FVector2D C = FVector2D::ZeroVector, P = FVector2D::ZeroVector, Ax = FVector2D::ZeroVector, Ay = FVector2D::ZeroVector;
		FVector2D operator()(const FVector& W) const { return P + Ax * (W.X - C.X) + Ay * (W.Y - C.Y); }
	};

	struct FScreenCtx
	{
		UWorld* World = nullptr;
		ADinkScreenVolume* Volume = nullptr;
		const UDinkGameplay* Gameplay = nullptr;
		int32 Screen = 0;
		double CmPerPx = 1.0;
		TFunction<FVector2D(const FVector&)> ToPx;
		FPxAffine AffineAt(const FVector& Centre) const
		{
			FPxAffine A;
			A.C = FVector2D(Centre);
			A.P = ToPx(Centre);
			A.Ax = (ToPx(Centre + FVector(100.0, 0, 0)) - A.P) / 100.0;
			A.Ay = (ToPx(Centre + FVector(0, 100.0, 0)) - A.P) / 100.0;
			return A;
		}
	};

	/** Footprint (map pixels) of one static mesh (instance) at body height; appended to Out. */
	void StaticFootprint(const FScreenCtx& Ctx, UStaticMeshComponent& C, const FTransform& T, FDrawn& Out)
	{
		UStaticMesh* Mesh = C.GetStaticMesh();
		const FBox Local = Mesh->GetBoundingBox();
		const FBox World3 = Local.TransformBy(T);
		const FVector Ext = World3.GetSize();
		if (Ext.X > 3000.0 || Ext.Y > 3000.0) return; // land, sheets, whole-screen sets
		const FString Path = Mesh->GetPathName();
		const double Ground = GroundAt(*Ctx.World, FVector2D(World3.GetCenter()), C.GetOwner());
		const bool bTree = IsTreePath(Path);
		const double Height = World3.Max.Z - Ground;
		// small things (pickups, a potion on the floor) are measured from just above the ground
		const double ZLow = Ground + (Height < 40.0 ? 1.0 : BandLowCm);
		const double ZHigh = Ground + (bTree ? TrunkBandHighCm : BandHighCm);
		if (World3.Max.Z < ZLow || World3.Min.Z > ZHigh + 400.0) return;
		const FPxAffine A = Ctx.AffineAt(World3.GetCenter());

		TArray<FVector> Verts;
		TArray<uint32> Indices;
		const FStaticMeshRenderData* RD = Mesh->GetRenderData();
		if (RD && RD->LODResources.Num() > 0)
		{
			const FStaticMeshLODResources& LOD = RD->LODResources[0];
			const FPositionVertexBuffer& PB = LOD.VertexBuffers.PositionVertexBuffer;
			if (PB.GetNumVertices() > 0 && PB.GetVertexData() && LOD.IndexBuffer.GetNumIndices() > 0 && LOD.IndexBuffer.GetArrayView().Num() > 0)
			{
				Verts.SetNumUninitialized(PB.GetNumVertices());
				for (uint32 I = 0; I < PB.GetNumVertices(); ++I)
				{
					const FVector W = T.TransformPosition(FVector(PB.VertexPosition(I)));
					const FVector2D Px = A(W);
					Verts[I] = FVector(Px.X, Px.Y, W.Z);
				}
				TArray<uint32> All;
				LOD.IndexBuffer.GetCopy(All);
				int32 Soft = 0;
				for (const FStaticMeshSection& Section : LOD.Sections)
				{
					const UMaterialInterface* M = C.GetMaterial(Section.MaterialIndex);
					const FString Name = (M ? M->GetName() : FString()) + TEXT("|") +
						(Mesh->GetStaticMaterials().IsValidIndex(Section.MaterialIndex) ? Mesh->GetStaticMaterials()[Section.MaterialIndex].MaterialSlotName.ToString() : FString());
					if (SoftMaterial(Name)) { ++Soft; continue; }
					for (uint32 K = 0; K < Section.NumTriangles * 3; ++K) Indices.Add(All[Section.FirstIndex + K]);
				}
				if (Indices.IsEmpty() && Soft > 0) return; // all foliage
			}
		}
		if (Indices.IsEmpty())
		{
			FVector Corners[8];
			Local.GetVertices(Corners);
			for (const FVector& V : Corners) { const FVector W = T.TransformPosition(V); const FVector2D Px = A(W); Verts.Add(FVector(Px.X, Px.Y, W.Z)); }
			static const uint32 Box[36] = { 0,1,2, 1,3,2, 4,6,5, 5,6,7, 0,4,1, 1,4,5, 2,3,6, 3,7,6, 0,2,4, 2,6,4, 1,5,3, 3,5,7 };
			Indices.Append(Box, 36);
		}
		FBox2D B(ForceInit);
		for (const FVector& V : Verts) B += FVector2D(V);
		const FIntPoint Min(FMath::FloorToInt(B.Min.X) - 2, FMath::FloorToInt(B.Min.Y) - 2);
		const FIntPoint Size(FMath::Clamp(FMath::CeilToInt(B.Max.X) - Min.X + 3, 1, 2000), FMath::Clamp(FMath::CeilToInt(B.Max.Y) - Min.Y + 3, 1, 2000));
		TArray<uint8> Cells;
		RasterSlice(Verts, Indices, ZLow, ZHigh, FVector2D(Min), 1.0, Size, Cells);
		FillHoles(Size, Cells);
		int32 N = 0;
		for (int32 Y = 0; Y < Size.Y; ++Y)
			for (int32 X = 0; X < Size.X; ++X)
				if (Cells[Y * Size.X + X]) { Out.Px.Add(FIntPoint(Min.X + X, Min.Y + Y)); ++N; }
		if (N > 0)
		{
			++Out.Items;
			if (Out.Mesh.IsEmpty()) Out.Mesh = FPaths::GetBaseFilename(Path);
		}
	}

	void SkeletalFootprint(const FScreenCtx& Ctx, USkeletalMeshComponent& C, FDrawn& Out)
	{
		const FBox Box = C.Bounds.GetBox();
		if (!Box.IsValid || Box.GetSize().X > 3000.0) return;
		const FVector Corners[4] = { FVector(Box.Min.X, Box.Min.Y, 0), FVector(Box.Max.X, Box.Min.Y, 0), FVector(Box.Min.X, Box.Max.Y, 0), FVector(Box.Max.X, Box.Max.Y, 0) };
		for (const FVector& P : Corners) Out.BodyPx += Ctx.ToPx(P);
		++Out.Items;
		Out.Kinds.Add(TEXT("skeletal"));
		if (Out.Mesh.IsEmpty() && C.GetSkeletalMeshAsset()) Out.Mesh = C.GetSkeletalMeshAsset()->GetName();
	}

	FString KindOf(const UStaticMeshComponent& C, const AActor& Owner)
	{
		if (C.ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)) return Cast<UInstancedStaticMeshComponent>(&C) ? TEXT("family_instance") : TEXT("family");
		if (Owner.ActorHasTag(TEXT("DinkAuthoredArt"))) return TEXT("authored");
		if (const ADinkPlaceholderActor* P = Cast<ADinkPlaceholderActor>(&Owner)) if (P->Card == &C) return TEXT("card");
		if (Cast<ADinkScreenVolume>(&Owner)) return TEXT("interior");
		if (C.GetName().StartsWith(TEXT("Decor_"))) return TEXT("card");
		return TEXT("environment");
	}

	FString ClassOf(const FDinkSprite* S, const FDinkPlacementInfo* P, int32 Brain, int32 Touch, int32 Warp, const FString& Script, int32 Type)
	{
		if (Warp) return TEXT("warp");
		const FString L = Script.ToLower();
		if (Touch == -1 || L.StartsWith(TEXT("item-")) || L.Contains(TEXT("heart")) || L.Contains(TEXT("potion")) || L.Contains(TEXT("gold")) || L.Contains(TEXT("pot")) || L == TEXT("sbelt"))
			if (Brain != 9 && Brain != 10) return TEXT("pickup");
		if (Brain == 9 || Brain == 10 || Brain == 3 || Brain == 4 || Brain == 15 || Brain == 11 || Brain == 17) return TEXT("creature");
		if (Brain == 16 || Brain == 5 || Brain == 6) return TEXT("npc");
		if (!Script.IsEmpty() && S) return TEXT("scripted_prop");
		return Type == 1 ? TEXT("sprite_prop") : TEXT("background");
	}
}

bool DinkPhysicalAudit::AuditScreen(UWorld& World, int32 ScreenNumber, TArray<FString>& OutOrigins, TArray<FString>& OutWarps, TArray<FString>& OutTiles, FString& OutScreen, FString* OutOccupancy)
{
	const double T0 = FPlatformTime::Seconds();
	UDinkGreyboxSubsystem* Grey = World.GetSubsystem<UDinkGreyboxSubsystem>();
	ADinkScreenVolume* Volume = Grey ? Grey->FindScreen(ScreenNumber) : nullptr;
	APlayerController* PC = World.GetFirstPlayerController();
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	const UCapsuleComponent* Capsule = Pawn ? Pawn->FindComponentByClass<UCapsuleComponent>() : nullptr;
	UGameInstance* GI = World.GetGameInstance();
	UDinkStorySubsystem* Story = GI ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
	const UDinkGameplay* Gameplay = Story ? Story->GetGameplay() : nullptr;
	const UDinkDirector* Director = Story ? Story->GetDirector() : nullptr;
	if (!Volume || !Capsule || !Gameplay || !Director) return false;

	FScreenCtx Ctx;
	Ctx.World = &World;
	Ctx.Volume = Volume;
	Ctx.Gameplay = Gameplay;
	Ctx.Screen = ScreenNumber;
	Ctx.ToPx = [Volume](const FVector& P)
	{
		double X = 0, Y = 0;
		DinkLayout::MetresToMapPixel(Volume->Corners, DinkLayout::UnrealToMetres(P), X, Y);
		return FVector2D(X, Y);
	};
	Ctx.CmPerPx = FVector::Dist(Volume->MapPixelToWorld(0, 200), Volume->MapPixelToWorld(600, 200)) / 600.0;
	const double TolPx = ToleranceCm / Ctx.CmPerPx;
	const int32 W = FDinkHardnessMap::Width, H = FDinkHardnessMap::Height;

	// hardness codes as the engine reads them now (get_hard)
	TArray<uint8> Codes;
	Codes.SetNumZeroed(W * H);
	for (int32 Y = 0; Y < H; ++Y)
		for (int32 X = 0; X < W; ++X) Codes[Y * W + X] = uint8(FMath::Clamp(Gameplay->GetHard(ScreenNumber, X + 20, Y), 0, 255));

	// --- drawn things: per origin key ("S001_P05", or "H<handle>" for a sprite without a placement), and all together ---
	TMap<FString, FDrawn> ByKey;
	FDrawn All;
	TMap<const AActor*, FString> ActorKey;
	for (const TPair<int32, FDinkSprite>& Pair : Director->GetSprites())
	{
		const FDinkSprite& S = Pair.Value;
		if (!S.bActive || S.bText || S.Screen != ScreenNumber || Pair.Key == 1 || !S.Actor.IsValid()) continue;
		ActorKey.Add(S.Actor.Get(), S.Origin.IsValid() ? S.Origin.ToString() : FString::Printf(TEXT("H%d"), Pair.Key));
	}
	int32 DrawnItems = 0;
	for (TActorIterator<AActor> It(&World); It; ++It)
	{
		AActor* Owner = *It;
		if (Owner == Pawn || Owner->IsHidden()) continue;
		FString Key;
		if (const FString* K = ActorKey.Find(Owner)) Key = *K;
		else if (const UDinkOriginComponent* O = UDinkOriginComponent::FindOnActor(Owner)) Key = O->OriginId.ToString();
		const ADinkGreyboxScreen* GS = Cast<ADinkGreyboxScreen>(Owner);
		// family instances: nearest card instance of the decor component they replace
		TMap<FName, TArray<TPair<FVector, FString>>> DecorCards;
		if (GS && GS->InstanceOrigins)
		{
			TInlineComponentArray<UInstancedStaticMeshComponent*> Isms(Owner);
			for (const FDinkInstanceOrigin& O : GS->InstanceOrigins->Origins)
				for (UInstancedStaticMeshComponent* C : Isms)
					if (C->GetFName() == O.ComponentName)
					{
						FTransform T;
						if (C->GetInstanceTransform(O.InstanceIndex, T, true)) DecorCards.FindOrAdd(O.ComponentName).Add({ T.GetLocation(), O.OriginId.ToString() });
					}
		}
		TInlineComponentArray<UPrimitiveComponent*> Components(Owner);
		for (UPrimitiveComponent* Prim : Components)
		{
			if (!Prim->IsRegistered() || !Prim->IsVisible() || Prim->bHiddenInGame) continue;
			if (Prim->GetAttachParent() && Prim->GetAttachParent()->GetOwner() == Pawn) continue;
			if (USkeletalMeshComponent* Sk = Cast<USkeletalMeshComponent>(Prim))
			{
				if (!Volume->ContainsWorldLocation(Sk->Bounds.Origin)) continue;
				FDrawn& D = ByKey.FindOrAdd(Key.IsEmpty() ? FString(TEXT("~")) : Key);
				SkeletalFootprint(Ctx, *Sk, D);
				D.bVisible = true;
				++DrawnItems;
				continue;
			}
			UStaticMeshComponent* C = Cast<UStaticMeshComponent>(Prim);
			if (!C || !C->GetStaticMesh()) continue;
			if (GS && (C == GS->Visual || C == GS->CollisionSolid || C == GS->CollisionLow || C == GS->DebugBlockers)) continue;
			if (SkipMesh(C->GetStaticMesh()->GetPathName())) continue;
			const FString Kind = KindOf(*C, *Owner);
			if (UInstancedStaticMeshComponent* ISM = Cast<UInstancedStaticMeshComponent>(C))
			{
				// FamilyArt_<decor>_<k> replaces the decor component <decor>; a decor component's instances are cards
				FName Decor = ISM->GetFName();
				FString Name = Decor.ToString();
				if (Name.StartsWith(TEXT("FamilyArt_")))
				{
					Name.RightChopInline(10);
					int32 Us = INDEX_NONE;
					if (Name.FindLastChar(TEXT('_'), Us)) Name.LeftInline(Us);
					Decor = FName(*Name);
				}
				const TArray<TPair<FVector, FString>>* Cards = DecorCards.Find(Decor);
				for (int32 I = 0; I < ISM->GetInstanceCount(); ++I)
				{
					FTransform T;
					if (!ISM->GetInstanceTransform(I, T, true) || !Volume->ContainsWorldLocation(T.GetLocation())) continue;
					FString IKey = Key;
					if (Cards)
					{
						double Best = DBL_MAX;
						for (const TPair<FVector, FString>& Card : *Cards)
						{
							const double D2 = FVector::DistSquared2D(Card.Key, T.GetLocation());
							if (D2 < Best) { Best = D2; IKey = Card.Value; }
						}
					}
					FDrawn& D = ByKey.FindOrAdd(IKey.IsEmpty() ? FString(TEXT("~")) : IKey);
					const int32 Before = D.Px.Num();
					StaticFootprint(Ctx, *C, T, D);
					D.Kinds.Add(Kind);
					D.bVisible = true;
					All.Px.Append(D.Px.GetData() + Before, D.Px.Num() - Before);
					++DrawnItems;
				}
			}
			else if (Volume->ContainsWorldLocation(C->Bounds.Origin))
			{
				FDrawn& D = ByKey.FindOrAdd(Key.IsEmpty() ? FString(TEXT("~")) : Key);
				const int32 Before = D.Px.Num();
				StaticFootprint(Ctx, *C, C->GetComponentTransform(), D);
				D.Kinds.Add(Kind);
				D.bVisible = true;
				All.Px.Append(D.Px.GetData() + Before, D.Px.Num() - Before);
				++DrawnItems;
			}
		}
	}

	// screen-wide occupancy and its distance field (cards count as drawn: a card is a visible thing too)
	TArray<uint8> Occ;
	Occ.SetNumZeroed(W * H);
	for (const FIntPoint& P : All.Px) if (P.X >= 0 && P.Y >= 0 && P.X < W && P.Y < H) Occ[P.Y * W + P.X] = 1;
	for (const TPair<FString, FDrawn>& Pair : ByKey)
		if (Pair.Value.BodyPx.bIsValid)
			for (int32 Y = FMath::Max(0, FMath::FloorToInt(Pair.Value.BodyPx.Min.Y)); Y <= FMath::Min(H - 1, FMath::CeilToInt(Pair.Value.BodyPx.Max.Y)); ++Y)
				for (int32 X = FMath::Max(0, FMath::FloorToInt(Pair.Value.BodyPx.Min.X)); X <= FMath::Min(W - 1, FMath::CeilToInt(Pair.Value.BodyPx.Max.X)); ++X) Occ[Y * W + X] = 1;
	TArray<float> OccDist;
	DistanceToSet(FIntPoint(W, H), Occ, OccDist);
	if (OutOccupancy)
	{
		// drawn (within the tolerance) per 3 x 3 map pixels, run-length coded <count><D|E> row by row (as walk_mask.csv)
		FString Out;
		TCHAR Last = 0;
		int32 Run = 0;
		auto Emit = [&](TCHAR C) { if (C == Last) { ++Run; return; } if (Run) Out += FString::Printf(TEXT("%d%c"), Run, Last); Last = C; Run = 1; };
		for (int32 Y = 0; Y < H; Y += 3)
			for (int32 X = 0; X < W; X += 3)
			{
				const int32 Cx = FMath::Min(X + 1, W - 1), Cy = FMath::Min(Y + 1, H - 1);
				Emit(OccDist[Cy * W + Cx] <= TolPx ? TEXT('D') : TEXT('E'));
			}
		Emit(0);
		*OutOccupancy = FString::Printf(TEXT("%d,3,%s"), ScreenNumber, *Out);
	}

	// --- per placement / live sprite ---
	struct FSubject
	{
		FString Key;
		int32 Handle = 0;
		const FDinkSprite* Sprite = nullptr;
		const FDinkPlacementInfo* Placement = nullptr;
		int32 N = 0;
	};
	TArray<FSubject> Subjects;
	TSet<FString> Seen;
	for (const TPair<int32, FDinkSprite>& Pair : Director->GetSprites())
	{
		const FDinkSprite& S = Pair.Value;
		if (!S.bActive || S.bText || S.Screen != ScreenNumber || Pair.Key == 1 || Pair.Key == UDinkDirector::HandleNoSprite) continue;
		FSubject Sub;
		Sub.Key = S.Origin.IsValid() ? S.Origin.ToString() : FString::Printf(TEXT("H%d"), Pair.Key);
		Sub.Handle = Pair.Key;
		Sub.Sprite = &S;
		Sub.Placement = S.Origin.IsValid() ? Gameplay->GetData().FindPlacement(S.Origin) : nullptr;
		Sub.N = S.Origin.IsValid() && S.Origin.Screen == ScreenNumber ? S.Origin.Placement : 0;
		Seen.Add(Sub.Key);
		Subjects.Add(Sub);
	}
	TArray<int32> StampedCount;
	StampedCount.SetNumZeroed(256);
	for (uint8 C : Codes) ++StampedCount[C];
	for (const FDinkPlacementInfo* P : Gameplay->GetData().GetPlacementsOnScreen(ScreenNumber))
	{
		if (!P || Seen.Contains(P->Origin.ToString())) continue;
		const bool bStamped = P->Origin.Placement > 0 && P->Origin.Placement < 156 && StampedCount[100 + P->Origin.Placement] > 0;
		const FDrawn* D = ByKey.Find(P->Origin.ToString());
		if (!bStamped && !(D && D->bVisible)) continue; // another vision, or a live placement whose sprite is gone
		FSubject Sub;
		Sub.Key = P->Origin.ToString();
		Sub.Placement = P;
		Sub.N = P->Origin.Placement;
		Subjects.Add(Sub);
	}

	FCollisionQueryParams CapParams(SCENE_QUERY_STAT(DinkPhysAuditCapsule), false, Pawn);
	const FCollisionShape CapShape = FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius() * 0.6f, Capsule->GetScaledCapsuleHalfHeight());
	int32 StampedTotal = 0, BareStampedTotal = 0;
	for (const FSubject& Sub : Subjects)
	{
		const FDinkSprite* S = Sub.Sprite;
		const FDinkPlacementInfo* P = Sub.Placement;
		int32 X = P ? P->X : 0, Y = P ? P->Y : 0, Seq = P ? P->Seq : 0, Frame = P ? P->Frame : 0, Brain = P ? P->Brain : 0, Touch = P ? P->TouchDamage : 0;
		int32 NoHit = P ? P->NoHit : 0, Size = P ? P->Size : 100, Type = P ? P->Type : 1, HardFlag = P ? P->Hard : 1;
		const int32 Warp = P ? (Gameplay->GetPlacementProp(P->Origin) != 0 ? 1 : 0) : 0;
		FString Script = P ? P->Script.ToString() : FString();
		if (Script == TEXT("None")) Script.Reset();
		int32 L = 0, T = 0, R = -1, B = -1;
		bool bBox = false;
		if (S)
		{
			X = FMath::RoundToInt32(S->X); Y = FMath::RoundToInt32(S->Y);
			Seq = S->GetProp(TEXT("pseq")); Frame = S->GetProp(TEXT("pframe"));
			Brain = S->GetProp(TEXT("brain")); Touch = S->GetProp(TEXT("touch_damage")); NoHit = S->GetProp(TEXT("nohit"));
			Size = S->GetProp(TEXT("size"), 100);
			Script = S->Script.IsNone() ? FString() : S->Script.ToString();
			bBox = Gameplay->GetHardbox(*S, L, T, R, B);
		}
		else if (const FDinkFrameInfo* F = Gameplay->GetData().FindFrame(Seq, FMath::Max(1, Frame)))
		{
			L = X + F->Left; T = Y + F->Top; R = X + F->Right; B = Y + F->Bottom;
			bBox = true;
		}
		// to map pixels
		L -= 20; R -= 20;
		const int32 Mx = X - 20, My = Y;
		const int32 Code = Sub.N > 0 && Sub.N < 156 ? 100 + Sub.N : -1;
		int32 Stamped = 0, BareStamped = 0;
		FBox2D StampBox(ForceInit);
		if (Code > 0)
			for (int32 I = 0; I < Codes.Num(); ++I)
				if (Codes[I] == Code)
				{
					++Stamped;
					StampBox += FVector2D(I % W, I / W);
					if (OccDist[I] > TolPx) ++BareStamped;
				}
		StampedTotal += Stamped;
		BareStampedTotal += BareStamped;
		if (!bBox && Stamped > 0) { L = FMath::FloorToInt(StampBox.Min.X); T = FMath::FloorToInt(StampBox.Min.Y); R = FMath::CeilToInt(StampBox.Max.X); B = FMath::CeilToInt(StampBox.Max.Y); bBox = true; }

		const FDrawn* D = ByKey.Find(Sub.Key);
		const bool bAuthored = S && S->Actor.IsValid() && S->Actor->ActorHasTag(TEXT("DinkAuthoredArt"));
		const bool bFitted = D && D->Kinds.Contains(TEXT("family")) ; // family-dressed placeholder
		const FString Class = ClassOf(S, P, Brain, Touch, Warp, Script, Type);

		// window around box and footprint
		FBox2D Win(ForceInit);
		if (bBox && R >= L && B >= T) { Win += FVector2D(L, T); Win += FVector2D(R, B); }
		FBox2D Own(ForceInit);
		if (D) for (const FIntPoint& Q : D->Px) Own += FVector2D(Q);
		if (Own.bIsValid) { Win += Own.Min; Win += Own.Max; }
		FMaskCompare Cmp;
		double CoverAll = 0.0;
		if (Win.bIsValid && bBox && R >= L && B >= T)
		{
			const int32 Margin = FMath::CeilToInt(TolPx) + 4;
			const FIntPoint Min(FMath::FloorToInt(Win.Min.X) - Margin, FMath::FloorToInt(Win.Min.Y) - Margin);
			const FIntPoint Sz(FMath::Min(1400, FMath::CeilToInt(Win.Max.X) - Min.X + Margin + 1), FMath::Min(1000, FMath::CeilToInt(Win.Max.Y) - Min.Y + Margin + 1));
			TArray<uint8> HM, FM;
			HM.Init(0, Sz.X * Sz.Y);
			FM.Init(0, Sz.X * Sz.Y);
			int32 InMap = 0, CovAll = 0;
			for (int32 Yy = T; Yy <= B; ++Yy)
				for (int32 Xx = L; Xx <= R; ++Xx)
				{
					const int32 LX = Xx - Min.X, LY = Yy - Min.Y;
					if (LX >= 0 && LY >= 0 && LX < Sz.X && LY < Sz.Y) HM[LY * Sz.X + LX] = 1;
					if (Xx >= 0 && Yy >= 0 && Xx < W && Yy < H) { ++InMap; CovAll += OccDist[Yy * W + Xx] <= TolPx; }
				}
			CoverAll = InMap ? double(CovAll) / InMap : 0.0;
			if (D)
			{
				for (const FIntPoint& Q : D->Px)
				{
					const int32 LX = Q.X - Min.X, LY = Q.Y - Min.Y;
					if (LX >= 0 && LY >= 0 && LX < Sz.X && LY < Sz.Y) FM[LY * Sz.X + LX] = 1;
				}
				if (D->BodyPx.bIsValid)
					for (int32 Yy = FMath::FloorToInt(D->BodyPx.Min.Y); Yy <= FMath::CeilToInt(D->BodyPx.Max.Y); ++Yy)
						for (int32 Xx = FMath::FloorToInt(D->BodyPx.Min.X); Xx <= FMath::CeilToInt(D->BodyPx.Max.X); ++Xx)
						{
							const int32 LX = Xx - Min.X, LY = Yy - Min.Y;
							if (LX >= 0 && LY >= 0 && LX < Sz.X && LY < Sz.Y) FM[LY * Sz.X + LX] = 1;
						}
			}
			Cmp = Compare(Sz, HM, FM, TolPx);
		}
		int32 OwnPx = 0;
		if (D) { TSet<FIntPoint> U(D->Px); OwnPx = U.Num(); }

		// a live sprite: what stands at its feet (another placement's drawn body, or the player's capsule cannot stand there)
		FString InsideOther;
		int32 CapsuleBlocked = -1;
		FVector2D ActorD(0.0);
		if (S)
		{
			for (const TPair<FString, FDrawn>& Other : ByKey)
			{
				if (Other.Key == Sub.Key || Other.Key == TEXT("~")) continue;
				bool bIn = false;
				for (const FIntPoint& Q : Other.Value.Px) if (FMath::Abs(Q.X - Mx) <= 1 && FMath::Abs(Q.Y - My) <= 1) { bIn = true; break; }
				if (bIn) { InsideOther += (InsideOther.IsEmpty() ? TEXT("") : TEXT("|")) + Other.Key; }
			}
			const FVector At = Volume->MapPixelToWorld(Mx, My);
			const double G = GroundAt(World, FVector2D(At), S->Actor.Get());
			FCollisionQueryParams Q2 = CapParams;
			if (S->Actor.IsValid()) Q2.AddIgnoredActor(S->Actor.Get());
			CapsuleBlocked = World.OverlapBlockingTestByChannel(FVector(At.X, At.Y, G + 36.0 + Capsule->GetScaledCapsuleHalfHeight()), FQuat::Identity,
				Capsule->GetCollisionObjectType(), CapShape, Q2, FCollisionResponseParams(Capsule->GetCollisionResponseToChannels())) ? 1 : 0;
			if (S->Actor.IsValid()) ActorD = Ctx.ToPx(S->Actor->GetActorLocation()) - FVector2D(Mx, My);
		}
		FString Kinds = D ? FString::Join(D->Kinds.Array(), TEXT("+")) : FString();
		FString Mesh = D ? D->Mesh : FString();
		Mesh.ReplaceInline(TEXT(","), TEXT(";"));
		Script.ReplaceInline(TEXT(","), TEXT(";"));
		const FBox2D Body = D ? D->BodyPx : FBox2D(ForceInit);
		OutOrigins.Add(FString::Printf(TEXT("%d,%s,%d,%d,%d,%d,%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s,%d,%d,%d,%d,%d,%d,%d,%d,%.3f,%d,%s,%s,%d,")
			TEXT("%d,%.0f,%.0f,%.0f,%.0f,%.1f,%.1f,%.3f,%.3f,%.3f,%.1f,%.1f,%.1f,%.3f,%d,%.0f,%.0f,%.0f,%.0f,%s,%d,%.1f,%.1f"),
			ScreenNumber, *Sub.Key, Sub.Handle, Type, S ? 1 : 0, Brain, *Script, Seq, Frame, Size, Touch, NoHit, Warp, HardFlag, bAuthored ? 1 : 0, bFitted ? 1 : 0, *Class,
			Mx, My, L, T, R, B, Stamped, BareStamped, Ctx.CmPerPx, D ? D->Items : 0, *Kinds, *Mesh, D && D->bVisible ? 1 : 0,
			OwnPx, Own.bIsValid ? Own.Min.X : 0.0, Own.bIsValid ? Own.Min.Y : 0.0, Own.bIsValid ? Own.Max.X : 0.0, Own.bIsValid ? Own.Max.Y : 0.0,
			Own.bIsValid ? Own.GetCenter().X : 0.0, Own.bIsValid ? Own.GetCenter().Y : 0.0, Cmp.Cover, Cmp.Overhang, Cmp.IoU, Cmp.Offset.X, Cmp.Offset.Y, Cmp.MaxBareDistance, CoverAll,
			Body.bIsValid ? 1 : 0, Body.bIsValid ? Body.Min.X : 0.0, Body.bIsValid ? Body.Min.Y : 0.0, Body.bIsValid ? Body.Max.X : 0.0, Body.bIsValid ? Body.Max.Y : 0.0,
			*InsideOther, CapsuleBlocked, ActorD.X, ActorD.Y));
	}

	// --- warps: trigger box vs the drawn door/exit ---
	for (TActorIterator<AActor> It(&World); It; ++It)
	{
		TInlineComponentArray<UDinkWarpComponent*> Warps(*It);
		for (const UDinkWarpComponent* Wc : Warps)
		{
			if (!Volume->ContainsWorldLocation(Wc->GetComponentLocation())) continue;
			const FVector E = Wc->GetScaledBoxExtent();
			FBox2D Box(ForceInit);
			for (int32 K = 0; K < 4; ++K)
				Box += Ctx.ToPx(Wc->GetComponentTransform().TransformPosition(FVector((K & 1) ? E.X : -E.X, (K & 2) ? E.Y : -E.Y, 0.0) / Wc->GetComponentScale()));
			FString Origin;
			if (const UDinkOriginComponent* O = UDinkOriginComponent::FindOnActor(*It)) Origin = O->OriginId.ToString();
			const FDrawn* D = Origin.IsEmpty() ? nullptr : ByKey.Find(Origin);
			FBox2D Own(ForceInit);
			int32 OwnPx = 0;
			if (D) { for (const FIntPoint& Q : D->Px) Own += FVector2D(Q); OwnPx = D->Px.Num(); }
			// gap: distance between the box and the drawn door (0 when they touch or overlap)
			double Gap = -1.0;
			if (Own.bIsValid)
			{
				const double Dx = FMath::Max3(0.0, Own.Min.X - Box.Max.X, Box.Min.X - Own.Max.X);
				const double Dy = FMath::Max3(0.0, Own.Min.Y - Box.Max.Y, Box.Min.Y - Own.Max.Y);
				Gap = FMath::Sqrt(Dx * Dx + Dy * Dy);
			}
			// share of the box with something drawn (anything) within the tolerance, and the nearest drawn pixel to the box centre
			int32 In = 0, Cov = 0;
			for (int32 Yy = FMath::FloorToInt(Box.Min.Y); Yy <= FMath::CeilToInt(Box.Max.Y); ++Yy)
				for (int32 Xx = FMath::FloorToInt(Box.Min.X); Xx <= FMath::CeilToInt(Box.Max.X); ++Xx)
					if (Xx >= 0 && Yy >= 0 && Xx < W && Yy < H) { ++In; Cov += OccDist[Yy * W + Xx] <= TolPx; }
			const FIntPoint C(FMath::Clamp(FMath::RoundToInt(Box.GetCenter().X), 0, W - 1), FMath::Clamp(FMath::RoundToInt(Box.GetCenter().Y), 0, H - 1));
			OutWarps.Add(FString::Printf(TEXT("%d,%s,%s,%s,%s,%d,%d,%.0f,%.0f,%.0f,%.0f,%d,%.0f,%.0f,%.0f,%.0f,%.1f,%.3f,%.3f,%.1f"),
				ScreenNumber, *Wc->WarpId.Replace(TEXT(","), TEXT(";")), *Origin, *Wc->Kind.ToString(), *Wc->TriggerMode.ToString(), Wc->bTriggerEnabled ? 1 : 0, Wc->DestScreen,
				Box.Min.X, Box.Min.Y, Box.Max.X, Box.Max.Y, OwnPx, Own.bIsValid ? Own.Min.X : 0.0, Own.bIsValid ? Own.Min.Y : 0.0, Own.bIsValid ? Own.Max.X : 0.0, Own.bIsValid ? Own.Max.Y : 0.0,
				Gap, Ctx.CmPerPx, In ? double(Cov) / In : 0.0, FMath::Min(OccDist[C.Y * W + C.X], 9999.f)));
		}
	}

	// --- solid tile hardness (1, 3) with nothing drawn within the tolerance, as connected blobs ---
	int32 SolidTile = 0, BareTile = 0;
	{
		TArray<uint8> Bare;
		Bare.SetNumZeroed(W * H);
		for (int32 I = 0; I < W * H; ++I)
			if (Codes[I] == 1 || Codes[I] == 2 || Codes[I] == 3) { SolidTile += Codes[I] != 2; if (OccDist[I] > TolPx) { Bare[I] = Codes[I]; BareTile += Codes[I] != 2; } }
		TArray<int32> Stack;
		for (int32 I = 0; I < W * H; ++I)
		{
			if (!Bare[I]) continue;
			const uint8 Code = Bare[I];
			int32 N = 0;
			FBox2D Bb(ForceInit);
			double MaxD = 0.0;
			FVector2D Sum(0.0);
			Stack.Reset();
			Stack.Add(I);
			Bare[I] = 0;
			while (!Stack.IsEmpty())
			{
				const int32 J = Stack.Pop(EAllowShrinking::No);
				const int32 Xx = J % W, Yy = J / W;
				++N; Bb += FVector2D(Xx, Yy); Sum += FVector2D(Xx, Yy);
				MaxD = FMath::Max(MaxD, double(FMath::Min(OccDist[J], 9999.f)));
				const int32 Nb[4] = { Xx > 0 ? J - 1 : -1, Xx < W - 1 ? J + 1 : -1, Yy > 0 ? J - W : -1, Yy < H - 1 ? J + W : -1 };
				for (int32 K : Nb) if (K >= 0 && Bare[K] == Code) { Bare[K] = 0; Stack.Add(K); }
			}
			if (N < 30) continue;
			// is the blob drawn as raised ground (a cliff relief)? the ground under its centre vs the screen's base
			const FVector2D Cn = Sum / N;
			const FVector At = Volume->MapPixelToWorld(Cn.X, Cn.Y);
			const double Rise = GroundAt(World, FVector2D(At), nullptr) - Volume->GetActorLocation().Z;
			OutTiles.Add(FString::Printf(TEXT("%d,%d,%d,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.1f,%.1f,%.3f"), ScreenNumber, Code, N, Bb.Min.X, Bb.Min.Y, Bb.Max.X, Bb.Max.Y,
				Cn.X, Cn.Y, MaxD, Rise, Ctx.CmPerPx));
		}
	}
	int32 Live = 0;
	for (const FSubject& Sub : Subjects) Live += Sub.Sprite != nullptr;
	// the teleport can be refused (a point in filled water, dink.Goto): then the screen's live state is not the one measured
	const bool bOnScreen = Volume->ContainsWorldLocation(Pawn->GetActorLocation());
	OutScreen = FString::Printf(TEXT("%d,%.3f,%d,%d,%d,%d,%d,%d,%d,%.0f,%d"), ScreenNumber, Ctx.CmPerPx, Subjects.Num(), Live, DrawnItems, SolidTile, BareTile,
		StampedTotal, BareStampedTotal, (FPlatformTime::Seconds() - T0) * 1000.0, bOnScreen ? 1 : 0);
	return true;
}

#if !UE_BUILD_SHIPPING
// ---------------------------------------------------------------------------------------------------------------------------
// dink.PhysAudit <first> <last> <out dir> [quit]: visits each screen, audits it, appends to the CSV files. Development builds only
// (a shipping build has no console; cooked meshes may also lack the CPU vertex data the slice reads: not tested packaged).
namespace
{
	struct FPhysAuditRun
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

	bool FreePixel(const UDinkGameplay* G, int32 Screen, FVector2D& Out)
	{
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

	void Append(const FString& File, const FString& Text)
	{
		if (Text.IsEmpty()) return;
		FFileHelper::SaveStringToFile(Text, *File, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
	}

	bool TickPhysAudit(TSharedRef<FPhysAuditRun> Run)
	{
		UWorld* World = Run->World.Get();
		if (!World) return false;
		UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
		if (!Grey) return false;
		if (Run->Next >= Run->Screens.Num())
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("DINK PHYSAUDIT: done, %d screens"), Run->Screens.Num());
			if (Run->bQuit && GEngine) GEngine->Exec(World, TEXT("quit"));
			return false;
		}
		const int32 Screen = Run->Screens[Run->Next];
		UGameInstance* GI = World->GetGameInstance();
		UDinkStorySubsystem* Story = GI ? GI->GetSubsystem<UDinkStorySubsystem>() : nullptr;
		const UDinkGameplay* G = Story ? Story->GetGameplay() : nullptr;
		if (Run->Phase == 0)
		{
			FVector2D Px;
			FreePixel(G, Screen, Px);
			Grey->GotoScreen(Screen, Px.X, Px.Y);
			Run->Phase = 1;
			Run->ArriveFrame = GFrameCounter;
			Run->ArriveTime = FPlatformTime::Seconds();
			return true;
		}
		if (GFrameCounter - Run->ArriveFrame < 20 || FPlatformTime::Seconds() - Run->ArriveTime < 0.6) return true;
		if (UDinkArtFamilySubsystem* F = World->GetSubsystem<UDinkArtFamilySubsystem>()) if (F->IsReady() && !F->IsScreenApplied(Screen)) F->ApplyScreen(Screen);
		TArray<FString> Origins, Warps, Tiles;
		FString ScreenLine, Occupancy;
		if (DinkPhysicalAudit::AuditScreen(*World, Screen, Origins, Warps, Tiles, ScreenLine, &Occupancy))
		{
			Append(Run->Dir / TEXT("phys_drawn_mask.csv"), Occupancy + TEXT("\n"));
			auto Join = [](const TArray<FString>& A) { return A.IsEmpty() ? FString() : FString::Join(A, TEXT("\n")) + TEXT("\n"); };
			Append(Run->Dir / TEXT("phys_origins.csv"), Join(Origins));
			Append(Run->Dir / TEXT("phys_warps.csv"), Join(Warps));
			Append(Run->Dir / TEXT("phys_tiles.csv"), Join(Tiles));
			Append(Run->Dir / TEXT("phys_screens.csv"), ScreenLine + TEXT("\n"));
			UE_LOG(LogDinkNarrative, Display, TEXT("DINK PHYSAUDIT: SCR_%03d %s"), Screen, *ScreenLine);
		}
		else
		{
			UE_LOG(LogDinkNarrative, Warning, TEXT("DINK PHYSAUDIT: SCR_%03d not audited"), Screen);
		}
		++Run->Next;
		Run->Phase = 0;
		return true;
	}
}

static FAutoConsoleCommandWithWorldAndArgs GDinkPhysAuditCommand(
	TEXT("dink.PhysAudit"),
	TEXT("dink.PhysAudit <first> <last> <out dir> [quit]: per screen, 1997 hardboxes / touch and hit boxes / warps / tile hardness against the drawn meshes (phys_*.csv)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || Args.Num() < 3)
		{
			UE_LOG(LogDinkNarrative, Display, TEXT("usage: dink.PhysAudit <first> <last> <out dir> [quit]"));
			return;
		}
		TSharedRef<FPhysAuditRun> Run = MakeShared<FPhysAuditRun>();
		Run->World = World;
		Run->Dir = Args[2];
		Run->bQuit = Args.Num() > 3 && Args[3] == TEXT("quit");
		UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
		for (int32 S = FCString::Atoi(*Args[0]); S <= FCString::Atoi(*Args[1]); ++S) if (Grey && Grey->FindScreen(S)) Run->Screens.Add(S);
		IFileManager::Get().MakeDirectory(*Run->Dir, true);
		FFileHelper::SaveStringToFile(DinkPhysicalAudit::OriginCsvHeader() + TEXT("\n"), *(Run->Dir / TEXT("phys_origins.csv")));
		FFileHelper::SaveStringToFile(DinkPhysicalAudit::WarpCsvHeader() + TEXT("\n"), *(Run->Dir / TEXT("phys_warps.csv")));
		FFileHelper::SaveStringToFile(DinkPhysicalAudit::TileCsvHeader() + TEXT("\n"), *(Run->Dir / TEXT("phys_tiles.csv")));
		FFileHelper::SaveStringToFile(DinkPhysicalAudit::ScreenCsvHeader() + TEXT("\n"), *(Run->Dir / TEXT("phys_screens.csv")));
		FFileHelper::SaveStringToFile(TEXT("screen,step,mask\n"), *(Run->Dir / TEXT("phys_drawn_mask.csv")));
		UE_LOG(LogDinkNarrative, Display, TEXT("DINK PHYSAUDIT: %d screens -> %s"), Run->Screens.Num(), *Run->Dir);
		FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Run](float) { return TickPhysAudit(Run); }));
	}));
#endif // !UE_BUILD_SHIPPING
