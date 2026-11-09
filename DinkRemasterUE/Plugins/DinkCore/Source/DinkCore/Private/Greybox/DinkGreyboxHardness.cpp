// The greybox's solid collision when a script redraws a screen's hardness (draw_hard_sprite / draw_hard_map, dink.cpp:8089-8104 and
// 8224-8232; the hardness itself is DinkNarrative's UDinkGameplay). The importer bakes each screen's solid collision into one complex-as-simple
// trimesh (SM_SCR_nnn_CollSolid: the ground quad plus a 3 m prism for every rectangle of solid pixels, DinkGreyboxAssets.cpp), which cannot
// lose a part at run time. So the first change on a screen reads which pixels the baked mesh covers (a line trace at every pixel centre),
// applies the changes and builds a runtime mesh the same way; the baked one is switched off until the screen loads again.

#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "DinkCollision.h"
#include "DinkCoreModule.h"
#include "DinkLayout.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/PlatformTime.h"
#include "ProceduralMeshComponent.h"

namespace
{
	constexpr int32 MapW = 600;
	constexpr int32 MapH = 400;

	/** Rectangles covering the set pixels (runs per row, extended downwards while a run repeats exactly). */
	TArray<FIntRect> MergeRects(const TBitArray<>& Mask)
	{
		TArray<FIntRect> Rects;
		TMap<int64, int32> Open;
		for (int32 Y = 0; Y < MapH; ++Y)
		{
			TMap<int64, int32> Next;
			int32 X = 0;
			while (X < MapW)
			{
				if (!Mask[Y * MapW + X])
				{
					++X;
					continue;
				}
				const int32 X0 = X;
				while (X < MapW && Mask[Y * MapW + X])
				{
					++X;
				}
				const int64 Key = (static_cast<int64>(X0) << 16) | X;
				if (const int32* Index = Open.Find(Key))
				{
					Rects[*Index].Max.Y = Y + 1;
					Next.Add(Key, *Index);
				}
				else
				{
					Next.Add(Key, Rects.Add(FIntRect(X0, Y, X, Y + 1)));
				}
			}
			Open = MoveTemp(Next);
		}
		return Rects;
	}

	/** FMeshWriter::Quad of the importer (DinkGreyboxAssets.cpp): the same corner order and triangles, facing Outward. */
	void AddQuad(TArray<FVector>& V, TArray<int32>& T, FVector P0, FVector P1, FVector P2, FVector P3, const FVector& Outward)
	{
		if (FVector::DotProduct(FVector::CrossProduct(P1 - P0, P3 - P0), Outward) < 0.0)
		{
			Swap(P1, P3);
		}
		const int32 B = V.Num();
		V.Append({ P0, P1, P2, P3 });
		T.Append({ B, B + 2, B + 1, B, B + 3, B + 2 });
	}
}

ADinkGreyboxScreen* UDinkGreyboxSubsystem::FindGreyboxScreen(int32 ScreenNumber) const
{
	for (TActorIterator<ADinkGreyboxScreen> It(GetWorld()); It; ++It)
	{
		if (It->ScreenNumber == ScreenNumber)
		{
			return *It;
		}
	}
	return nullptr;
}

const TBitArray<>* UDinkGreyboxSubsystem::BakedSolidMask(int32 ScreenNumber)
{
	if (const TBitArray<>* Found = BakedSolidMasks.Find(ScreenNumber))
	{
		return Found;
	}
	const ADinkGreyboxScreen* Screen = FindGreyboxScreen(ScreenNumber);
	const ADinkScreenVolume* Volume = FindScreen(ScreenNumber);
	UPrimitiveComponent* Baked = Screen ? Screen->CollisionSolid.Get() : nullptr;
	if (!Volume || !Baked || Baked->GetCollisionEnabled() == ECollisionEnabled::NoCollision)
	{
		return nullptr;
	}
	// A prism stands on every solid rectangle's corners, 3 m high; the ground lies at height 0. A trace from 10 m down to 1 m above a pixel
	// centre meets a prism's top exactly when the pixel is solid in the baked mesh (half a pixel from any prism edge).
	const double Started = FPlatformTime::Seconds();
	TBitArray<> Mask(false, MapW * MapH);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkBakedSolidMask), /*bTraceComplex*/ true);
	FHitResult Hit;
	int32 Solid = 0;
	for (int32 Y = 0; Y < MapH; ++Y)
	{
		for (int32 X = 0; X < MapW; ++X)
		{
			const FVector Top = DinkLayout::MapPixelToUnreal(Volume->Corners, X + 0.5, Y + 0.5, 10.0);
			const FVector Bottom = DinkLayout::MapPixelToUnreal(Volume->Corners, X + 0.5, Y + 0.5, 1.0);
			if (Baked->LineTraceComponent(Hit, Top, Bottom, Params))
			{
				Mask[Y * MapW + X] = true;
				++Solid;
			}
		}
	}
	UE_LOG(LogDink, Log, TEXT("SCR_%03d: baked solid collision read, %d solid pixels (%.0f ms)"), ScreenNumber, Solid, (FPlatformTime::Seconds() - Started) * 1000.0);
	return &BakedSolidMasks.Add(ScreenNumber, MoveTemp(Mask));
}

bool UDinkGreyboxSubsystem::ApplyScreenSolidChanges(int32 ScreenNumber, const TArray<uint8>& Changes)
{
	if (Changes.Num() != MapW * MapH)
	{
		return false;
	}
	ADinkGreyboxScreen* Screen = FindGreyboxScreen(ScreenNumber);
	const ADinkScreenVolume* Volume = FindScreen(ScreenNumber);
	FRuntimeSolid* Runtime = RuntimeSolids.Find(ScreenNumber);
	if (!Screen || !Volume || (!Runtime && Screen->CollisionSolid && Screen->CollisionSolid->GetCollisionEnabled() == ECollisionEnabled::NoCollision))
	{
		// Not in this world, or its land collision is authored (UDinkArtSubsystem switched the baked mesh off): nothing to follow.
		return false;
	}
	const TBitArray<>* Baked = BakedSolidMask(ScreenNumber);
	if (!Baked)
	{
		return false;
	}
	TBitArray<> Solid = *Baked;
	for (int32 i = 0; i < Changes.Num(); ++i)
	{
		if (Changes[i] == 1)
		{
			Solid[i] = true;
		}
		else if (Changes[i] == 2)
		{
			Solid[i] = false;
		}
	}
	// The importer's collision mesh (DinkGreyboxAssets.cpp, "collision: solid"): the ground quad, then a prism (four sides and a top, no
	// bottom) on every rectangle, through the same transform (DinkLayout::MapPixelToUnreal of the screen's corners).
	auto At = [Volume](double X, double Y) { return DinkLayout::MapPixelToUnreal(Volume->Corners, X, Y, 0.0); };
	const FVector Up(0.0, 0.0, SolidPrismHeightCm);
	TArray<FVector> Vertices;
	TArray<int32> Triangles;
	AddQuad(Vertices, Triangles, At(0, 0), At(MapW, 0), At(MapW, MapH), At(0, MapH), FVector::UpVector);
	const TArray<FIntRect> Rects = MergeRects(Solid);
	for (const FIntRect& R : Rects)
	{
		const FVector Base[4] = { At(R.Min.X, R.Min.Y), At(R.Max.X, R.Min.Y), At(R.Max.X, R.Max.Y), At(R.Min.X, R.Max.Y) };
		const FVector Centre = (Base[0] + Base[1] + Base[2] + Base[3]) * 0.25;
		AddQuad(Vertices, Triangles, Base[0] + Up, Base[1] + Up, Base[2] + Up, Base[3] + Up, FVector::UpVector);
		for (int32 I = 0; I < 4; ++I)
		{
			const FVector A = Base[I];
			const FVector B = Base[(I + 1) % 4];
			FVector Out = (A + B) * 0.5 - Centre;
			Out.Z = 0.0;
			AddQuad(Vertices, Triangles, A, B, B + Up, A + Up, Out);
		}
	}
	if (!Runtime)
	{
		Runtime = &RuntimeSolids.Add(ScreenNumber);
		UProceduralMeshComponent* Mesh = NewObject<UProceduralMeshComponent>(Screen, NAME_None, RF_Transient);
		Mesh->bUseComplexAsSimpleCollision = true;
		Mesh->bUseAsyncCooking = false;
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetupAttachment(Screen->GetRootComponent());
		Mesh->SetUsingAbsoluteLocation(true);
		Mesh->SetUsingAbsoluteRotation(true);
		Mesh->SetUsingAbsoluteScale(true);
		Mesh->SetWorldTransform(FTransform::Identity);
		Mesh->SetCollisionProfileName(DinkCollision::ProfileHardSolid);
		Mesh->SetHiddenInGame(true);
		Mesh->SetVisibility(false);
		Mesh->SetCastShadow(false);
		Mesh->SetGenerateOverlapEvents(false);
		Mesh->SetCanEverAffectNavigation(false);
		Mesh->RegisterComponent();
		Runtime->Mesh = Mesh;
		Runtime->Baked = Screen->CollisionSolid.Get();
		Screen->CollisionSolid->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	}
	UProceduralMeshComponent* Mesh = Runtime->Mesh.Get();
	if (!Mesh)
	{
		return false;
	}
	Mesh->CreateMeshSection(0, Vertices, Triangles, {}, {}, {}, {}, /*bCreateCollision*/ true);
	int32 Added = 0, Removed = 0;
	for (const uint8 C : Changes)
	{
		Added += C == 1;
		Removed += C == 2;
	}
	UE_LOG(LogDink, Log, TEXT("SCR_%03d: runtime solid collision, %d rectangles (%d pixels now solid, %d no longer)"), ScreenNumber, Rects.Num(), Added, Removed);
	return true;
}

void UDinkGreyboxSubsystem::RestoreScreenSolidCollision(int32 ScreenNumber)
{
	for (auto It = RuntimeSolids.CreateIterator(); It; ++It)
	{
		if (ScreenNumber != 0 && It->Key != ScreenNumber)
		{
			continue;
		}
		if (UProceduralMeshComponent* Mesh = It->Value.Mesh.Get())
		{
			Mesh->DestroyComponent();
		}
		if (UPrimitiveComponent* Baked = It->Value.Baked.Get())
		{
			// ADinkGreyboxScreen's CollisionSolid is query and physics (its profile, DinkHardSolid).
			Baked->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
		}
		UE_LOG(LogDink, Log, TEXT("SCR_%03d: baked solid collision back"), It->Key);
		It.RemoveCurrent();
	}
}

UPrimitiveComponent* UDinkGreyboxSubsystem::GetRuntimeSolidCollision(int32 ScreenNumber) const
{
	const FRuntimeSolid* Runtime = RuntimeSolids.Find(ScreenNumber);
	return Runtime ? Runtime->Mesh.Get() : nullptr;
}
