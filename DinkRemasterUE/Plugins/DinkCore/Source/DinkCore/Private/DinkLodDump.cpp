#include "DinkLodDump.h"
#include "DinkCoreModule.h"
#include "DinkCreatureClassComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkinnedAssetCommon.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UObjectIterator.h"

namespace DinkLodDump
{
	float ScreenRadiusSquared(float SphereRadiusCm, float DistanceCm, float HorizontalFovDeg, float Aspect)
	{
		// A perspective projection that keeps the horizontal FOV: M[0][0] = 1 / tan(fov / 2), M[1][1] = aspect / tan(fov / 2).
		const float InvTan = 1.f / FMath::Tan(FMath::DegreesToRadians(FMath::Clamp(HorizontalFovDeg, 1.f, 170.f)) * .5f);
		const float ScreenMultiple = FMath::Max(.5f * InvTan, .5f * InvTan * FMath::Max(Aspect, .01f));
		return FMath::Square(ScreenMultiple * SphereRadiusCm) / FMath::Max(1.f, FMath::Square(DistanceCm));
	}

	int32 PickLod(const TArray<float>& ScreenSizes, float ScreenRadiusSq)
	{
		for (int32 Lod = ScreenSizes.Num() - 1; Lod > 0; --Lod)
			if (FMath::Square(ScreenSizes[Lod] * .5f) > ScreenRadiusSq) return Lod;
		return 0;
	}

	namespace
	{
		struct FMeshRow { FString Path; FString From; float Scale = 1.f; };

		void ReadRows(const TCHAR* File, const TCHAR* ArrayField, TArray<FMeshRow>& Out, bool bPeopleOnly)
		{
			FString Text;
			TSharedPtr<FJsonObject> Manifest;
			if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art") / File)) ||
				!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest) return;
			const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
			if (!Manifest->TryGetArrayField(ArrayField, Rows)) return;
			for (const TSharedPtr<FJsonValue>& Value : *Rows)
			{
				const TSharedPtr<FJsonObject> Row = Value.IsValid() ? Value->AsObject() : nullptr;
				FString Mesh, Id;
				if (!Row || !Row->TryGetStringField(TEXT("mesh"), Mesh)) continue;
				if (bPeopleOnly && !Mesh.StartsWith(TEXT("/Game/Dink/Photoreal/Characters/NPC/"))) continue;
				if (!Row->TryGetStringField(TEXT("class"), Id)) Row->TryGetStringField(TEXT("origin"), Id);
				double Scale = 1.0;
				Row->TryGetNumberField(TEXT("scale"), Scale);
				if (FMeshRow* Known = Out.FindByPredicate([&](const FMeshRow& R) { return R.Path == Mesh; })) { Known->From += TEXT(",") + Id; continue; }
				Out.Add({Mesh, Id, float(Scale)});
			}
		}
	}

	FString Write(UWorld* World, const TArray<float>& DistancesCm)
	{
		float Fov = 90.f, Aspect = 16.f / 9.f;
		FVector CameraAt = FVector::ZeroVector;
		bool bLiveCamera = false;
		if (World)
		{
			if (APlayerController* PC = World->GetFirstPlayerController())
			{
				if (APlayerCameraManager* Camera = PC->PlayerCameraManager)
				{
					Fov = Camera->GetFOVAngle();
					const FMinimalViewInfo& View = Camera->GetCameraCacheView();
					if (View.AspectRatio > .1f) Aspect = View.AspectRatio;
					CameraAt = Camera->GetCameraLocation();
					bLiveCamera = true;
				}
			}
		}
		const float RadiusScale = [] { const IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(TEXT("r.SkeletalMeshLODRadiusScale")); return V ? FMath::Clamp(V->GetFloat(), .25f, 1.f) : 1.f; }();
		TArray<FString> Lines;
		Lines.Add(FString::Printf(TEXT("DINK LOD DUMP: camera %s, horizontal FOV %.1f, aspect %.3f, r.SkeletalMeshLODRadiusScale %.2f"),
			bLiveCamera ? TEXT("live (player camera)") : TEXT("default (follow camera, no player)"), Fov, Aspect, RadiusScale));
		Lines.Add(TEXT("rule: FSkeletalMeshObject::UpdateMinDesiredLODLevel, the worst LOD whose (ScreenSize/2)^2 > bounds screen radius^2 (hysteresis left out)"));
		TArray<FMeshRow> Rows;
		ReadRows(TEXT("creatures.json"), TEXT("classes"), Rows, true);
		ReadRows(TEXT("characters.json"), TEXT("placements"), Rows, false);
		Rows.Add({TEXT("/Game/Dink/Hero/Refinements/SK_Dink_Hands.SK_Dink_Hands"), TEXT("hero"), 1.f});
		FString Header = TEXT("mesh | rows | LODs: screen size / hysteresis / triangles | bounds radius cm (x row scale) | LOD at");
		for (const float D : DistancesCm) Header += FString::Printf(TEXT(" %.0f"), D);
		Lines.Add(Header + TEXT(" cm"));
		for (const FMeshRow& Row : Rows)
		{
			USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *Row.Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
			if (!Mesh) { Lines.Add(FString::Printf(TEXT("%s | %s | not loaded"), *Row.Path, *Row.From)); continue; }
			const FSkeletalMeshRenderData* Render = Mesh->GetResourceForRendering();
			TArray<float> Sizes;
			FString Lods;
			for (int32 Lod = 0; Lod < Mesh->GetLODNum(); ++Lod)
			{
				const FSkeletalMeshLODInfo* Info = Mesh->GetLODInfo(Lod);
				const float Size = Info ? Info->ScreenSize.GetValue() : 0.f;
				Sizes.Add(Size);
				const int32 Tris = Render && Render->LODRenderData.IsValidIndex(Lod) ? int32(Render->LODRenderData[Lod].GetTotalFaces()) : -1;
				Lods += FString::Printf(TEXT("%sLOD%d %.3f/%.3f/%d"), Lod ? TEXT(", ") : TEXT(""), Lod, Size, Info ? Info->LODHysteresis : 0.f, Tris);
			}
			const float Radius = float(Mesh->GetBounds().SphereRadius) * Row.Scale;
			FString Picks;
			for (const float D : DistancesCm)
				Picks += FString::Printf(TEXT(" %d"), PickLod(Sizes, ScreenRadiusSquared(Radius, D, Fov, Aspect) * RadiusScale * RadiusScale));
			Lines.Add(FString::Printf(TEXT("%s | %s | %s | %.1f |%s"), *FPaths::GetBaseFilename(Row.Path), *Row.From, *Lods, Radius, *Picks));
		}
		if (World)
		{
			int32 Figures = 0;
			for (TObjectIterator<UDinkCreatureClassComponent> It; It; ++It)
			{
				if (It->GetWorld() != World || !It->GetSkeletalMeshAsset()) continue;
				const USkeletalMesh* Mesh = It->GetSkeletalMeshAsset();
				if (!Mesh->GetPathName().StartsWith(TEXT("/Game/Dink/Photoreal/Characters/NPC/"))) continue;
				TArray<float> Sizes;
				for (int32 Lod = 0; Lod < Mesh->GetLODNum(); ++Lod) Sizes.Add(Mesh->GetLODInfo(Lod) ? Mesh->GetLODInfo(Lod)->ScreenSize.GetValue() : 0.f);
				const float Distance = bLiveCamera ? float(FVector::Dist(CameraAt, It->Bounds.Origin)) : 0.f;
				const int32 Rule = PickLod(Sizes, ScreenRadiusSquared(float(It->Bounds.SphereRadius), Distance, Fov, Aspect) * RadiusScale * RadiusScale);
				if (Figures++ < 200)
					Lines.Add(FString::Printf(TEXT("figure %s (%s): %.0f cm from the camera, bounds radius %.1f, rule LOD %d, renderer LOD %d%s"), *It->GetClassId().ToString(),
						*FPaths::GetBaseFilename(Mesh->GetPathName()), Distance, It->Bounds.SphereRadius, Rule, It->GetPredictedLODLevel(),
						It->WasRecentlyRendered(.5f) ? TEXT("") : TEXT(" (not rendered: the renderer LOD is not a reading)")));
			}
			Lines.Add(FString::Printf(TEXT("%d people figures in the world"), Figures));
		}
		const FString Text = FString::Join(Lines, TEXT("\n")) + TEXT("\n");
		FFileHelper::SaveStringToFile(Text, *(FPaths::ProjectSavedDir() / TEXT("Art/lod_screen_sizes.txt")));
		return Text;
	}

	static FAutoConsoleCommandWithWorldAndArgs GLodDumpCommand(TEXT("dink.LodDump"),
		TEXT("dink.LodDump [distance_cm ...]: review only: the skeletal LOD screen sizes of the people meshes and the LOD the play camera shows at those distances (default 300 500 800 1200 2000), and the people figures in the world; writes Saved/Art/lod_screen_sizes.txt."),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			TArray<float> Distances;
			for (const FString& A : Args) if (A.IsNumeric()) Distances.Add(FCString::Atof(*A));
			if (Distances.IsEmpty()) Distances = {300.f, 500.f, 800.f, 1200.f, 2000.f};
			TArray<FString> Lines;
			Write(World, Distances).ParseIntoArrayLines(Lines);
			for (const FString& L : Lines) UE_LOG(LogDink, Display, TEXT("%s"), *L);
		}));
}
