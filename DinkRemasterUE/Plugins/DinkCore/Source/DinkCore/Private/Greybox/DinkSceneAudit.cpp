// dink.SceneAudit <file>: review only (Scripts/PhotorealQA/visual_sweep.py). Appends one JSON line that describes
// every visible primitive whose bounds centre lies on the player's current screen: actor class, origin ID, mesh,
// materials and their base materials, bounds, what a downward trace under the centre hits first, and per static mesh
// the LOD0 vertex/triangle counts and the share of hard-shaded vertices (positions whose normals differ by more than
// 20 degrees, the faceting measure). Instanced components report each instance's bounds and support. The lights of
// the screen are listed too. Nothing here changes the world; gameplay never calls it.
#include "DinkCoreModule.h"
#include "DinkOriginComponent.h"
#include "DinkInstanceOriginsComponent.h"
#include "EngineUtils.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/LightComponent.h"
#include "Components/LocalLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstance.h"
#include "Materials/MaterialInterface.h"
#include "Materials/Material.h"
#include "Misc/FileHelper.h"
#include "StaticMeshResources.h"

namespace
{
	struct FDinkMeshStats { int32 Vertices = 0, Triangles = 0; float Hard = -1.f, Facet = -1.f; bool bNanite = false; };
	TMap<TWeakObjectPtr<UStaticMesh>, FDinkMeshStats> GDinkAuditMeshCache;

	FString Esc(const FString& In) { return In.Replace(TEXT("\\"), TEXT("\\\\")).Replace(TEXT("\""), TEXT("\\\"")); }
	FString Vec(const FVector& V) { return FString::Printf(TEXT("[%.1f,%.1f,%.1f]"), V.X, V.Y, V.Z); }

	FDinkMeshStats MeshStats(UStaticMesh* Mesh)
	{
		if (const FDinkMeshStats* Hit = GDinkAuditMeshCache.Find(Mesh)) return *Hit;
		FDinkMeshStats S;
		S.bNanite = Mesh->HasValidNaniteData();
		const FStaticMeshRenderData* RD = Mesh->GetRenderData();
		if (RD && RD->LODResources.Num() > 0)
		{
			const FStaticMeshLODResources& LOD = RD->LODResources[0];
			S.Vertices = LOD.GetNumVertices();
			S.Triangles = LOD.GetNumTriangles();
			const FPositionVertexBuffer& Pos = LOD.VertexBuffers.PositionVertexBuffer;
			const FStaticMeshVertexBuffer& Tan = LOD.VertexBuffers.StaticMeshVertexBuffer;
			if (S.Vertices > 0 && S.Vertices < 2000000 && Pos.GetVertexData() && Tan.GetTangentData())
			{
				// quantise positions to 0.05 cm. A position is hard when two of its vertices' normals differ by more than
				// 20 degrees, and a facet when they differ by 8 to 55 degrees: the soft creases that show as polygons
				// (the 90 degree edges of a plank or a box are hard but not facets).
				TMap<FIntVector, int32> First;
				TSet<int32> HardPositions, FacetPositions;
				TArray<FVector3f> Normals;
				Normals.SetNumUninitialized(S.Vertices);
				int32 Positions = 0;
				for (int32 I = 0; I < S.Vertices; ++I)
				{
					const FVector3f P = Pos.VertexPosition(I);
					Normals[I] = FVector3f(Tan.VertexTangentZ(I)).GetSafeNormal();
					const FIntVector Key(FMath::RoundToInt(P.X * 20.f), FMath::RoundToInt(P.Y * 20.f), FMath::RoundToInt(P.Z * 20.f));
					if (int32* Prev = First.Find(Key))
					{
						const float Dot = FVector3f::DotProduct(Normals[*Prev], Normals[I]);
						if (Dot < 0.94f) HardPositions.Add(*Prev);
						if (Dot < 0.990f && Dot > 0.574f) FacetPositions.Add(*Prev);
					}
					else
					{
						First.Add(Key, I);
						++Positions;
					}
				}
				S.Facet = Positions > 0 ? float(FacetPositions.Num()) / float(Positions) : -1.f;
				S.Hard = Positions > 0 ? float(HardPositions.Num()) / float(Positions) : -1.f;
			}
		}
		GDinkAuditMeshCache.Add(Mesh, S);
		return S;
	}

	FString MaterialJson(UPrimitiveComponent* C, bool& bDefault)
	{
		FString Out = TEXT("[");
		const int32 N = C->GetNumMaterials();
		for (int32 I = 0; I < N; ++I)
		{
			UMaterialInterface* M = C->GetMaterial(I);
			UMaterial* Base = M ? M->GetMaterial() : nullptr;
			const FString BaseName = Base ? Base->GetPathName() : FString();
			const bool bEngineDefault = !M || BaseName.Contains(TEXT("WorldGridMaterial")) || BaseName.Contains(TEXT("/Engine/EngineMaterials/DefaultMaterial"))
				|| BaseName.Contains(TEXT("DefaultDeferredDecalMaterial")) || BaseName.Contains(TEXT("BasicShapeMaterial"));
			bDefault |= bEngineDefault;
			// texture parameters that are empty or the engine's default texture
			FString BadTex;
			if (const UMaterialInstance* MI = Cast<UMaterialInstance>(M))
			{
				for (const FTextureParameterValue& T : MI->TextureParameterValues)
				{
					const FString TexName = T.ParameterValue ? T.ParameterValue->GetPathName() : FString(TEXT("null"));
					if (!T.ParameterValue || TexName.StartsWith(TEXT("/Engine/EngineResources/Default")) || TexName.Contains(TEXT("DefaultTexture")))
					{
						BadTex += (BadTex.IsEmpty() ? TEXT("") : TEXT("|")) + T.ParameterInfo.Name.ToString() + TEXT("=") + TexName;
					}
				}
			}
			Out += FString::Printf(TEXT("%s{\"m\":\"%s\",\"b\":\"%s\"%s%s}"), I ? TEXT(",") : TEXT(""), M ? *Esc(M->GetPathName()) : TEXT(""), *Esc(BaseName),
				bEngineDefault ? TEXT(",\"default\":1") : TEXT(""), BadTex.IsEmpty() ? TEXT("") : *FString::Printf(TEXT(",\"badtex\":\"%s\""), *Esc(BadTex)));
		}
		return Out + TEXT("]");
	}

	/** First blocking surfaces under (X, Y) from Top downward, ignoring the component itself: [[z, "actor class", "component", "material"], ...]. */
	FString Support(UWorld* World, const UPrimitiveComponent* Self, double X, double Y, double Top, double Bottom)
	{
		FCollisionQueryParams Params(SCENE_QUERY_STAT(DinkSceneAudit), true);
		Params.AddIgnoredComponent(Self);
		// the first blocking hit, then up to two more below it (each hit component is ignored for the next trace)
		FString Out = TEXT("[");
		int32 Count = 0;
		double From = Top;
		for (int32 Step = 0; Step < 4; ++Step)
		{
			FHitResult Hit;
			if (!World->LineTraceSingleByChannel(Hit, FVector(X, Y, From), FVector(X, Y, Bottom - 3000.0), ECC_Visibility, Params)) break;
			const UPrimitiveComponent* HC = Hit.GetComponent();
			const UMaterialInterface* HM = HC ? HC->GetMaterial(0) : nullptr;
			Out += FString::Printf(TEXT("%s[%.1f,\"%s\",\"%s\",\"%s\"]"), Count++ ? TEXT(",") : TEXT(""), Hit.ImpactPoint.Z,
				Hit.GetActor() ? *Hit.GetActor()->GetClass()->GetName() : TEXT(""), HC ? *Esc(HC->GetName()) : TEXT(""), HM ? *Esc(HM->GetName()) : TEXT(""));
			// a hit on another mesh is ignored for the next trace; under the top of a hardness prism of the greybox
			// screen's collision the trace goes on from just below the hit, so it still finds the ground plane
			if (HC && !(Hit.GetActor() && Hit.GetActor()->IsA<ADinkGreyboxScreen>())) Params.AddIgnoredComponent(HC);
			From = Hit.ImpactPoint.Z - 0.5;
		}
		return Out + TEXT("]");
	}
}

static FAutoConsoleCommandWithWorldAndArgs GDinkSceneAuditCommand(
	TEXT("dink.SceneAudit"), TEXT("dink.SceneAudit <file>: review only; appends a JSON line with every visible primitive and light of the player's screen (meshes, materials, bounds, support under each, faceting)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		APawn* Pawn = PC ? PC->GetPawn() : nullptr;
		UDinkGreyboxSubsystem* Grey = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
		const ADinkScreenVolume* Screen = (Pawn && Grey) ? Grey->FindScreenAt(Pawn->GetActorLocation()) : nullptr;
		if (!Screen || Args.Num() != 1)
		{
			UE_LOG(LogDink, Display, TEXT("DINK AUDIT: usage dink.SceneAudit <file> (needs the player on a screen)"));
			return;
		}
		FString Line = FString::Printf(TEXT("{\"screen\":%d,\"player\":%s,\"prims\":["), Screen->ScreenNumber, *Vec(Pawn->GetActorLocation()));
		int32 Prims = 0, Defaults = 0;
		FString Lights;
		int32 LightCount = 0;
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			AActor* A = *It;
			if (!A || A->IsHidden() || A == Pawn) continue;
			const UDinkOriginComponent* Origin = UDinkOriginComponent::FindOnActor(A);
			const UDinkInstanceOriginsComponent* InstanceOrigins = A->FindComponentByClass<UDinkInstanceOriginsComponent>();
			TInlineComponentArray<UActorComponent*> Components(A);
			for (UActorComponent* AC : Components)
			{
				if (ULightComponent* L = Cast<ULightComponent>(AC))
				{
					if (!L->IsVisible() || !L->IsRegistered()) continue;
					const bool bLocal = L->IsA<ULocalLightComponent>();
					if (bLocal && !Screen->ContainsWorldLocation(L->GetComponentLocation())) continue;
					const FLinearColor Col = L->GetLightColor();
					Lights += FString::Printf(TEXT("%s{\"a\":\"%s\",\"c\":\"%s\",\"at\":%s,\"i\":%.2f,\"col\":[%.2f,%.2f,%.2f],\"r\":%.0f,\"shadow\":%d}"),
						LightCount++ ? TEXT(",") : TEXT(""), *A->GetClass()->GetName(), *L->GetClass()->GetName(), *Vec(L->GetComponentLocation()), L->Intensity,
						Col.R, Col.G, Col.B, bLocal ? Cast<ULocalLightComponent>(L)->AttenuationRadius : 0.f, L->CastShadows ? 1 : 0);
					continue;
				}
				UPrimitiveComponent* C = Cast<UPrimitiveComponent>(AC);
				if (!C || !C->IsRegistered() || !C->IsVisible() || C->bHiddenInGame) continue;
				const bool bStatic = C->IsA<UStaticMeshComponent>(), bSkel = C->IsA<USkeletalMeshComponent>();
				if (!bStatic && !bSkel) continue;
				const FBoxSphereBounds B = C->Bounds;
				if (!Screen->ContainsWorldLocation(B.Origin)) continue;
				if (B.BoxExtent.GetMax() > 40000.0) continue;   // sky, atmosphere and sheet-wide meshes
				FString MeshPath;
				FString Extra;
				if (UStaticMeshComponent* SM = Cast<UStaticMeshComponent>(C))
				{
					if (UStaticMesh* Mesh = SM->GetStaticMesh())
					{
						MeshPath = Mesh->GetPathName();
						const FDinkMeshStats S = MeshStats(Mesh);
						Extra += FString::Printf(TEXT(",\"v\":%d,\"t\":%d,\"hard\":%.3f,\"facet\":%.3f,\"nanite\":%d"), S.Vertices, S.Triangles, S.Hard, S.Facet, S.bNanite ? 1 : 0);
						if (UInstancedStaticMeshComponent* ISM = Cast<UInstancedStaticMeshComponent>(SM))
						{
							const int32 N = ISM->GetInstanceCount();
							Extra += FString::Printf(TEXT(",\"inst\":%d"), N);
							if (N > 0 && N <= 300)
							{
								const FBox Local = Mesh->GetBoundingBox();
								Extra += TEXT(",\"is\":[");
								for (int32 I = 0; I < N; ++I)
								{
									FTransform T;
									ISM->GetInstanceTransform(I, T, true);
									const FBox W = Local.TransformBy(T);
									FString Id;
									if (InstanceOrigins)
									{
										for (const FDinkInstanceOrigin& O : InstanceOrigins->Origins)
										{
											if (O.ComponentName == ISM->GetFName() && O.InstanceIndex == I) { Id = O.OriginId.ToString(); break; }
										}
									}
									const FVector Ctr = W.GetCenter();
									Extra += FString::Printf(TEXT("%s{\"o\":\"%s\",\"min\":%s,\"max\":%s,\"g\":%s}"), I ? TEXT(",") : TEXT(""), *Id, *Vec(W.Min), *Vec(W.Max),
										*Support(World, C, Ctr.X, Ctr.Y, W.Max.Z + 5.0, W.Min.Z));
								}
								Extra += TEXT("]");
							}
						}
					}
				}
				else if (USkeletalMeshComponent* SK = Cast<USkeletalMeshComponent>(C))
				{
					if (SK->GetSkeletalMeshAsset()) MeshPath = SK->GetSkeletalMeshAsset()->GetPathName();
				}
				bool bDefault = false;
				const FString Mats = MaterialJson(C, bDefault);
				Defaults += bDefault ? 1 : 0;
				const FVector Min = B.Origin - B.BoxExtent, Max = B.Origin + B.BoxExtent;
				Line += FString::Printf(TEXT("%s{\"a\":\"%s\",\"n\":\"%s\",\"o\":\"%s\",\"c\":\"%s\",\"cn\":\"%s\",\"mesh\":\"%s\",\"mats\":%s%s,\"min\":%s,\"max\":%s,\"g\":%s%s}"),
					Prims++ ? TEXT(",") : TEXT(""), *A->GetClass()->GetName(), *Esc(A->GetName()), Origin ? *Origin->OriginId.ToString() : TEXT(""),
					*C->GetClass()->GetName(), *Esc(C->GetName()), *Esc(MeshPath), *Mats, bDefault ? TEXT(",\"default\":1") : TEXT(""), *Vec(Min), *Vec(Max),
					*Support(World, C, B.Origin.X, B.Origin.Y, Max.Z + 5.0, Min.Z), *Extra);
			}
		}
		Line += FString::Printf(TEXT("],\"lights\":[%s]}\n"), *Lights);
		FFileHelper::SaveStringToFile(Line, *Args[0], FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
		UE_LOG(LogDink, Display, TEXT("DINK AUDIT: screen %d, %d primitives, %d with an engine default material, %d lights"), Screen->ScreenNumber, Prims, Defaults, LightCount);
	}));
