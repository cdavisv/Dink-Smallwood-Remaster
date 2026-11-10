#include "DinkGreyboxAssets.h"
#include "DinkHardnessFoundationBuilder.h"
#include "Hardness/DinkHardnessShell.h"
#include "UObject/MetaData.h"
#include "DinkCollision.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Chaos/ImplicitObjectScaled.h"
#include "Chaos/ShapeInstance.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "DinkImportLog.h"
#include "AssetCompilingManager.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "HAL/FileManager.h"
#include "IImageWrapper.h"
#include "IImageWrapperModule.h"
#include "MaterialEditingLibrary.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpressionConstant.h"
#include "Materials/MaterialExpressionScalarParameter.h"
#include "Materials/MaterialExpressionTextureSampleParameter2D.h"
#include "Materials/MaterialExpressionVectorParameter.h"
#include "Materials/MaterialInstanceConstant.h"
#include "MeshDescription.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "PhysicsEngine/BodySetup.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "StaticMeshAttributes.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"

namespace DinkGreybox
{
	namespace
	{
		enum EBaseMaterial : int32
		{
			MatGround = 0,
			MatSprite = 1,
			MatFlat = 2,
			MatWater = 3,
		};

		const TCHAR* SharedFolder = TEXT("/Game/Dink/_Generated/Shared");

		FString SharedPackage(const TCHAR* Name)
		{
			return FString(SharedFolder) / Name;
		}

		FString ManifestFile()
		{
			return FPaths::ProjectContentDir() / TEXT("Dink/_Generated/import_manifest.json");
		}

		FString PackageFile(const FString& Package)
		{
			return FPackageName::LongPackageNameToFilename(Package, FPackageName::GetAssetPackageExtension());
		}

		template <typename T>
		T* FindOrCreate(const FString& Package, bool& bExisted)
		{
			const FString Name = FPackageName::GetShortName(Package);
			UPackage* Pkg = FindPackage(nullptr, *Package);
			if (!Pkg && FPackageName::DoesPackageExist(Package))
			{
				Pkg = LoadPackage(nullptr, *Package, LOAD_None);
			}
			if (!Pkg)
			{
				Pkg = CreatePackage(*Package);
			}
			Pkg->FullyLoad();
			T* Obj = FindObject<T>(Pkg, *Name);
			bExisted = Obj != nullptr;
			if (!Obj)
			{
				if (UObject* Other = FindObject<UObject>(Pkg, *Name))
				{
					Other->Rename(nullptr, GetTransientPackage(), REN_DontCreateRedirectors | REN_NonTransactional);
				}
				Obj = NewObject<T>(Pkg, FName(*Name), RF_Public | RF_Standalone | RF_Transactional);
				FAssetRegistryModule::AssetCreated(Obj);
			}
			return Obj;
		}

		bool DecodePng(const FString& File, TArray64<uint8>& OutBGRA, int32& OutW, int32& OutH, FString& OutError)
		{
			TArray<uint8> Bytes;
			if (!FFileHelper::LoadFileToArray(Bytes, *File))
			{
				OutError = FString::Printf(TEXT("cannot read %s"), *File);
				return false;
			}
			IImageWrapperModule& Module = FModuleManager::LoadModuleChecked<IImageWrapperModule>(TEXT("ImageWrapper"));
			TSharedPtr<IImageWrapper> Wrapper = Module.CreateImageWrapper(EImageFormat::PNG);
			if (!Wrapper.IsValid() || !Wrapper->SetCompressed(Bytes.GetData(), Bytes.Num()) || !Wrapper->GetRaw(ERGBFormat::BGRA, 8, OutBGRA))
			{
				OutError = FString::Printf(TEXT("cannot decode PNG %s"), *File);
				return false;
			}
			OutW = (int32)Wrapper->GetWidth();
			OutH = (int32)Wrapper->GetHeight();
			return true;
		}

		/**
		 * Writes quads into a FMeshDescription. UE computes a triangle's normal as
		 * (P2 - P0) x (P1 - P0) (StaticMeshOperations.cpp: "left-handed coordinate system, but a
		 * counter-clockwise winding order"), so a quad P0..P3 whose cross(P1-P0, P3-P0) points
		 * outward is emitted as triangles (0,2,1) and (0,3,2). Dink.Import.Greybox.Meshes checks
		 * the built normals point up.
		 */
		class FMeshWriter
		{
		public:
			FMeshWriter()
				: Attributes(Desc)
			{
				Attributes.Register();
				Positions = Attributes.GetVertexPositions();
				UVs = Attributes.GetVertexInstanceUVs();
				UVs.SetNumChannels(1);
				SlotNames = Attributes.GetPolygonGroupMaterialSlotNames();
			}

			FMeshDescription Desc;
			FStaticMeshAttributes Attributes;
			TVertexAttributesRef<FVector3f> Positions;
			TVertexInstanceAttributesRef<FVector2f> UVs;
			TPolygonGroupAttributesRef<FName> SlotNames;
			TMap<FName, FPolygonGroupID> Groups;
			TArray<FName> GroupOrder;
			int32 Triangles = 0;

			FPolygonGroupID Group(FName Slot)
			{
				if (const FPolygonGroupID* Found = Groups.Find(Slot))
				{
					return *Found;
				}
				const FPolygonGroupID Id = Desc.CreatePolygonGroup();
				SlotNames[Id] = Slot;
				Groups.Add(Slot, Id);
				GroupOrder.Add(Slot);
				return Id;
			}

			void Quad(FName Slot, FVector3f P[4], FVector2f T[4], const FVector3f& Outward)
			{
				const FVector3f Cross = FVector3f::CrossProduct(P[1] - P[0], P[3] - P[0]);
				if (FVector3f::DotProduct(Cross, Outward) < 0.f)
				{
					Swap(P[1], P[3]);
					Swap(T[1], T[3]);
				}
				const FPolygonGroupID G = Group(Slot);
				FVertexInstanceID VI[4];
				for (int32 I = 0; I < 4; ++I)
				{
					const FVertexID V = Desc.CreateVertex();
					Positions[V] = P[I];
					VI[I] = Desc.CreateVertexInstance(V);
					UVs.Set(VI[I], 0, T[I]);
				}
				Desc.CreateTriangle(G, {VI[0], VI[2], VI[1]});
				Desc.CreateTriangle(G, {VI[0], VI[3], VI[2]});
				Triangles += 2;
			}

			/** Prism standing on Base (4 points at z = Base z, ordered around), top at +Height, no bottom face. */
			void Prism(FName Slot, const FVector3f Base[4], float Height, bool bSides = true)
			{
				const FVector3f Up(0.f, 0.f, Height);
				FVector3f Centre = (Base[0] + Base[1] + Base[2] + Base[3]) * 0.25f;
				{
					FVector3f P[4] = {Base[0] + Up, Base[1] + Up, Base[2] + Up, Base[3] + Up};
					FVector2f T[4] = {{0, 0}, {1, 0}, {1, 1}, {0, 1}};
					Quad(Slot, P, T, FVector3f(0, 0, 1));
				}
				if (!bSides)
				{
					return;
				}
				for (int32 I = 0; I < 4; ++I)
				{
					const FVector3f A = Base[I];
					const FVector3f B = Base[(I + 1) % 4];
					FVector3f Out = (A + B) * 0.5f - Centre;
					Out.Z = 0.f;
					FVector3f P[4] = {A, B, B + Up, A + Up};
					FVector2f T[4] = {{0, 1}, {1, 1}, {1, 0}, {0, 0}};
					Quad(Slot, P, T, Out);
				}
			}
		};

		UStaticMesh* CommitMesh(const FString& Package, FMeshWriter& Writer, const TMap<FName, UMaterialInterface*>& Materials,
			bool bCollision, bool& bExisted)
		{
			UStaticMesh* Mesh = FindOrCreate<UStaticMesh>(Package, bExisted);
			Mesh->PreEditChange(nullptr);
			TArray<FStaticMaterial> Slots;
			for (const FName& Slot : Writer.GroupOrder)
			{
				UMaterialInterface* const* Mat = Materials.Find(Slot);
				Slots.Add(FStaticMaterial(Mat ? *Mat : nullptr, Slot, Slot));
			}
			Mesh->SetStaticMaterials(Slots);
			Mesh->SetNumSourceModels(1);
			FMeshBuildSettings& Build = Mesh->GetSourceModel(0).BuildSettings;
			Build.bRecomputeNormals = true;
			Build.bRecomputeTangents = true;
			Build.bUseMikkTSpace = false;
			Build.bGenerateLightmapUVs = false;
			Build.bRemoveDegenerates = false;
			Build.bBuildReversedIndexBuffer = false;
			Build.bUseFullPrecisionUVs = false;
			Build.DistanceFieldResolutionScale = 0.f;
			Mesh->CreateMeshDescription(0, MoveTemp(Writer.Desc));
			Mesh->CommitMeshDescription(0);

			FMeshSectionInfoMap Sections;
			for (int32 I = 0; I < Writer.GroupOrder.Num(); ++I)
			{
				FMeshSectionInfo Info(I);
				Info.bEnableCollision = bCollision;
				Info.bCastShadow = !bCollision;
				Sections.Set(0, I, Info);
			}
			Mesh->GetSectionInfoMap().CopyFrom(Sections);
			Mesh->GetOriginalSectionInfoMap().CopyFrom(Sections);
			Mesh->GetNaniteSettings().bEnabled = false;
			Mesh->SetLightMapCoordinateIndex(0);
			Mesh->SetLightMapResolution(4);
			Mesh->CreateBodySetup();
			UBodySetup* Body = Mesh->GetBodySetup();
			Body->CollisionTraceFlag = bCollision ? CTF_UseComplexAsSimple : CTF_UseSimpleAsComplex;
			Body->bNeverNeedsCookedCollisionData = !bCollision;
			Mesh->bAllowCPUAccess = false;
			Mesh->MarkPackageDirty();
			Mesh->PostEditChange();
			return Mesh;
		}
	}

	FString HashStrings(const TArray<FString>& Parts)
	{
		FString Joined = AssetGeneratorVersion;
		for (const FString& P : Parts)
		{
			Joined += TEXT("|");
			Joined += P;
		}
		return FMD5::HashAnsiString(*Joined);
	}

	UObject* LoadGenerated(const FString& Package)
	{
		if (!FindPackage(nullptr, *Package) && !FPackageName::DoesPackageExist(Package))
		{
			return nullptr;
		}
		const FString Path = Package + TEXT(".") + FPackageName::GetShortName(Package);
		return LoadObject<UObject>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
	}

	FAssetSet::FAssetSet(const FDinkBundle& InBundle)
		: Bundle(InBundle)
	{
	}

	FString FAssetSet::ScreenFolder(int32 Screen)
	{
		return FString::Printf(TEXT("%s/Screens/SCR_%03d"), GeneratedRoot, Screen);
	}

	FString FAssetSet::SpritePackage(const TCHAR* Prefix, const FString& Key)
	{
		return FString::Printf(TEXT("%s/Sprites/%s_%s"), GeneratedRoot, Prefix, *Key);
	}

	FVector FAssetSet::ScreenPivot(const FDinkBundleScreen& Screen)
	{
		return DinkLayout::MapPixelToUnreal(Screen.Corners, 300.0, 200.0);
	}

	bool FAssetSet::LoadManifest()
	{
		ManifestHashes.Reset();
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *ManifestFile()))
		{
			return false;
		}
		TSharedPtr<FJsonObject> Root;
		if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root.IsValid())
		{
			return false;
		}
		const TSharedPtr<FJsonObject>* Assets = nullptr;
		if (Root->TryGetObjectField(TEXT("assets"), Assets) && Assets)
		{
			for (const auto& Pair : (*Assets)->Values)
			{
				ManifestHashes.Add(FString(Pair.Key.ToView()), Pair.Value->AsString());
			}
		}
		return true;
	}

	bool FAssetSet::SaveManifest() const
	{
		TMap<FString, FString> All = ManifestHashes;
		for (const auto& Pair : NewHashes)
		{
			All.Add(Pair.Key, Pair.Value);
		}
		All.KeySort(TLess<FString>());
		FString Text = TEXT("{\n  \"schema\": \"dink-greybox-manifest/1\",\n  \"note\": \"written by DinkImport; never edit. Delete Content/Dink/_Generated to rebuild everything.\",\n  \"assets\": {\n");
		int32 I = 0;
		for (const auto& Pair : All)
		{
			Text += FString::Printf(TEXT("    \"%s\": \"%s\"%s\n"), *Pair.Key, *Pair.Value, ++I < All.Num() ? TEXT(",") : TEXT(""));
		}
		Text += TEXT("  }\n}\n");
		FString Existing;
		if (FFileHelper::LoadFileToString(Existing, *ManifestFile()) && Existing == Text)
		{
			return true;
		}
		return FFileHelper::SaveStringToFile(Text, *ManifestFile(), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	}

	bool FAssetSet::IsUpToDate(const FString& Package, const FString& Hash) const
	{
		const FString* Known = ManifestHashes.Find(Package);
		return Known && *Known == Hash && IFileManager::Get().FileExists(*PackageFile(Package));
	}

	void FAssetSet::MarkBuilt(UObject* Asset, const FString& Package, const FString& Hash, bool bExisted)
	{
		NewHashes.Add(Package, Hash);
		ToSave.Add(Asset);
		AssetStats.Changed.Add(Package);
		(bExisted || IFileManager::Get().FileExists(*PackageFile(Package)) ? AssetStats.Updated : AssetStats.Created)++;
	}

	void FAssetSet::MarkUnchanged(const FString& Package, const FString& Hash)
	{
		NewHashes.Add(Package, Hash);
		AssetStats.Unchanged++;
	}

	UMaterial* FAssetSet::BuildBaseMaterial(const FString& Package, int32 Kind, bool& bExisted)
	{
		UMaterial* M = FindOrCreate<UMaterial>(Package, bExisted);
		M->PreEditChange(nullptr);
		UMaterialEditingLibrary::DeleteAllMaterialExpressions(M);
		UTexture* DefaultTex = LoadObject<UTexture>(nullptr, TEXT("/Engine/EngineResources/DefaultTexture.DefaultTexture"));
		auto NewTex = [&]()
		{
			auto* T = Cast<UMaterialExpressionTextureSampleParameter2D>(
				UMaterialEditingLibrary::CreateMaterialExpression(M, UMaterialExpressionTextureSampleParameter2D::StaticClass(), -400, 0));
			T->ParameterName = TEXT("Tex");
			T->Texture = DefaultTex;
			T->SamplerType = SAMPLERTYPE_Color;
			return T;
		};
		auto NewConst = [&](float Value, int32 Y)
		{
			auto* C = Cast<UMaterialExpressionConstant>(UMaterialEditingLibrary::CreateMaterialExpression(M, UMaterialExpressionConstant::StaticClass(), -300, Y));
			C->R = Value;
			return C;
		};
		auto NewColor = [&](FLinearColor Default)
		{
			auto* V = Cast<UMaterialExpressionVectorParameter>(
				UMaterialEditingLibrary::CreateMaterialExpression(M, UMaterialExpressionVectorParameter::StaticClass(), -400, 0));
			V->ParameterName = TEXT("Color");
			V->DefaultValue = Default;
			return V;
		};
		switch (Kind)
		{
		case MatGround:
		{
			auto* T = NewTex();
			UMaterialEditingLibrary::ConnectMaterialProperty(T, TEXT(""), MP_BaseColor);
			UMaterialEditingLibrary::ConnectMaterialProperty(NewConst(1.f, 200), TEXT(""), MP_Roughness);
			UMaterialEditingLibrary::ConnectMaterialProperty(NewConst(0.1f, 300), TEXT(""), MP_Specular);
			M->BlendMode = BLEND_Opaque;
			M->SetShadingModel(MSM_DefaultLit);
			M->TwoSided = false;
			break;
		}
		case MatSprite:
		{
			auto* T = NewTex();
			UMaterialEditingLibrary::ConnectMaterialProperty(T, TEXT(""), MP_EmissiveColor);
			UMaterialEditingLibrary::ConnectMaterialProperty(T, TEXT("A"), MP_OpacityMask);
			M->BlendMode = BLEND_Masked;
			M->SetShadingModel(MSM_Unlit);
			M->TwoSided = true;
			M->OpacityMaskClipValue = 0.5f;
			M->SetUsageByFlag(MATUSAGE_InstancedStaticMeshes, true);
			break;
		}
		case MatFlat:
		{
			UMaterialEditingLibrary::ConnectMaterialProperty(NewColor(FLinearColor(0.4f, 0.4f, 0.4f)), TEXT(""), MP_BaseColor);
			UMaterialEditingLibrary::ConnectMaterialProperty(NewConst(0.9f, 200), TEXT(""), MP_Roughness);
			M->BlendMode = BLEND_Opaque;
			M->SetShadingModel(MSM_DefaultLit);
			M->TwoSided = false;
			break;
		}
		case MatWater:
		default:
		{
			UMaterialEditingLibrary::ConnectMaterialProperty(NewColor(FLinearColor(0.05f, 0.2f, 0.45f)), TEXT(""), MP_BaseColor);
			auto* O = Cast<UMaterialExpressionScalarParameter>(
				UMaterialEditingLibrary::CreateMaterialExpression(M, UMaterialExpressionScalarParameter::StaticClass(), -400, 200));
			O->ParameterName = TEXT("Opacity");
			O->DefaultValue = 0.55f;
			UMaterialEditingLibrary::ConnectMaterialProperty(O, TEXT(""), MP_Opacity);
			UMaterialEditingLibrary::ConnectMaterialProperty(NewConst(0.1f, 300), TEXT(""), MP_Roughness);
			M->BlendMode = BLEND_Translucent;
			M->SetShadingModel(MSM_DefaultLit);
			M->TwoSided = false;
			break;
		}
		}
		M->PostEditChange();
		M->MarkPackageDirty();
		return M;
	}

	UMaterialInstanceConstant* FAssetSet::BuildMaterialInstance(const FString& Package, UMaterialInterface* Parent, bool& bExisted)
	{
		UMaterialInstanceConstant* MI = FindOrCreate<UMaterialInstanceConstant>(Package, bExisted);
		MI->PreEditChange(nullptr);
		MI->ClearParameterValuesEditorOnly();
		MI->SetParentEditorOnly(Parent);
		return MI;
	}

	UTexture2D* FAssetSet::BuildTexture(const FString& Package, const FString& PngFile, bool bStretchToPow2, bool& bExisted, FString& OutError)
	{
		TArray64<uint8> Pixels;
		int32 W = 0, H = 0;
		if (!DecodePng(PngFile, Pixels, W, H, OutError))
		{
			return nullptr;
		}
		UTexture2D* T = FindOrCreate<UTexture2D>(Package, bExisted);
		T->PreEditChange(nullptr);
		T->Source.Init(W, H, 1, 1, TSF_BGRA8, Pixels.GetData());
		T->SRGB = true;
		T->CompressionSettings = TC_Default;
		T->LODGroup = TEXTUREGROUP_World;
		T->MipGenSettings = TMGS_FromTextureGroup;
		T->PowerOfTwoMode = bStretchToPow2 ? ETexturePowerOfTwoSetting::StretchToPowerOfTwo : ETexturePowerOfTwoSetting::None;
		T->AddressX = TA_Clamp;
		T->AddressY = TA_Clamp;
		T->PostEditChange();
		T->MarkPackageDirty();
		return T;
	}

	bool FAssetSet::EnsureShared(FString& OutError)
	{
		struct FBase
		{
			const TCHAR* Name;
			int32 Kind;
		};
		const FBase Bases[] = {{TEXT("M_DinkGround"), MatGround}, {TEXT("M_DinkSprite"), MatSprite}, {TEXT("M_DinkFlat"), MatFlat}, {TEXT("M_DinkWater"), MatWater}};
		for (const FBase& B : Bases)
		{
			const FString Pkg = SharedPackage(B.Name);
			const FString Hash = HashStrings({TEXT("material"), B.Name, FString::FromInt(B.Kind)});
			if (IsUpToDate(Pkg, Hash))
			{
				MarkUnchanged(Pkg, Hash);
				continue;
			}
			bool bExisted = false;
			MarkBuilt(BuildBaseMaterial(Pkg, B.Kind, bExisted), Pkg, Hash, bExisted);
		}

		struct FFlat
		{
			const TCHAR* Name;
			const TCHAR* Parent;
			FLinearColor Color;
			float Opacity;
		};
		const FFlat Flats[] = {
			{TEXT("MI_DinkBlocker_Solid"), TEXT("M_DinkFlat"), FLinearColor(0.32f, 0.30f, 0.27f), 1.f},
			{TEXT("MI_DinkBlocker_Low"), TEXT("M_DinkFlat"), FLinearColor(0.25f, 0.45f, 0.65f), 1.f},
			{TEXT("MI_DinkBlocker_Sprite"), TEXT("M_DinkFlat"), FLinearColor(0.60f, 0.42f, 0.20f), 1.f},
			{TEXT("MI_DinkBlocker_Warp"), TEXT("M_DinkFlat"), FLinearColor(0.80f, 0.15f, 0.80f), 1.f},
			{TEXT("MI_DinkWater"), TEXT("M_DinkWater"), FLinearColor(0.05f, 0.22f, 0.50f), 0.55f},
		};
		for (const FFlat& F : Flats)
		{
			const FString Pkg = SharedPackage(F.Name);
			const FString Hash = HashStrings({TEXT("mi"), F.Name, F.Parent, F.Color.ToString(), FString::SanitizeFloat(F.Opacity)});
			if (IsUpToDate(Pkg, Hash))
			{
				MarkUnchanged(Pkg, Hash);
				continue;
			}
			UMaterialInterface* Parent = Cast<UMaterialInterface>(LoadGenerated(SharedPackage(F.Parent)));
			if (!Parent)
			{
				OutError = FString::Printf(TEXT("parent material %s missing"), F.Parent);
				return false;
			}
			bool bExisted = false;
			UMaterialInstanceConstant* MI = BuildMaterialInstance(Pkg, Parent, bExisted);
			MI->SetVectorParameterValueEditorOnly(FMaterialParameterInfo(TEXT("Color")), F.Color);
			if (F.Opacity < 1.f)
			{
				MI->SetScalarParameterValueEditorOnly(FMaterialParameterInfo(TEXT("Opacity")), F.Opacity);
			}
			MI->PostEditChange();
			MI->MarkPackageDirty();
			MarkBuilt(MI, Pkg, Hash, bExisted);
		}

		// unit card: 1 m wide (x -50..50), 1 m tall (z 0..100), facing south (+Y), UV v = 0 at the top
		{
			const FString Pkg = SharedPackage(TEXT("SM_DinkCard"));
			const FString Hash = HashStrings({TEXT("card"), TEXT("1m xz +y")});
			if (IsUpToDate(Pkg, Hash))
			{
				MarkUnchanged(Pkg, Hash);
			}
			else
			{
				FMeshWriter W;
				FVector3f P[4] = {{-50, 0, 100}, {50, 0, 100}, {50, 0, 0}, {-50, 0, 0}};
				FVector2f T[4] = {{0, 0}, {1, 0}, {1, 1}, {0, 1}};
				W.Quad(TEXT("Card"), P, T, FVector3f(0, 1, 0));
				TMap<FName, UMaterialInterface*> Mats;
				Mats.Add(TEXT("Card"), Cast<UMaterialInterface>(LoadGenerated(SharedPackage(TEXT("M_DinkSprite")))));
				bool bExisted = false;
				MarkBuilt(CommitMesh(Pkg, W, Mats, false, bExisted), Pkg, Hash, bExisted);
			}
		}
		return true;
	}

	bool FAssetSet::EnsureSprite(const FString& Key, FString& OutError)
	{
		const FDinkBundleSprite* S = Bundle.Sprites.Find(Key);
		if (!S)
		{
			OutError = FString::Printf(TEXT("sprite %s not in bundle"), *Key);
			return false;
		}
		const FString TexPkg = SpritePackage(TEXT("T_Sprite"), Key);
		const FString MiPkg = SpritePackage(TEXT("MI_Sprite"), Key);
		const FString TexHash = HashStrings({TEXT("sprite"), S->Hash, FString::FromInt(S->TexWidth), FString::FromInt(S->TexHeight)});
		if (IsUpToDate(TexPkg, TexHash))
		{
			MarkUnchanged(TexPkg, TexHash);
		}
		else
		{
			bool bExisted = false;
			UTexture2D* T = BuildTexture(TexPkg, Bundle.Dir / S->File, false, bExisted, OutError);
			if (!T)
			{
				return false;
			}
			MarkBuilt(T, TexPkg, TexHash, bExisted);
		}
		const FString MiHash = HashStrings({TEXT("sprite-mi"), TexPkg});
		if (IsUpToDate(MiPkg, MiHash))
		{
			MarkUnchanged(MiPkg, MiHash);
		}
		else
		{
			bool bExisted = false;
			UMaterialInstanceConstant* MI = BuildMaterialInstance(MiPkg, Cast<UMaterialInterface>(LoadGenerated(SharedPackage(TEXT("M_DinkSprite")))), bExisted);
			MI->SetTextureParameterValueEditorOnly(FMaterialParameterInfo(TEXT("Tex")), Cast<UTexture>(LoadGenerated(TexPkg)));
			MI->PostEditChange();
			MI->MarkPackageDirty();
			MarkBuilt(MI, MiPkg, MiHash, bExisted);
		}
		return true;
	}

	bool FAssetSet::EnsureScreen(const FDinkBundleScreen& Screen, FString& OutError)
	{
		const FString Folder = ScreenFolder(Screen.Screen);
		const FString Sid = Screen.Id;
		const FString TexPkg = Folder / (TEXT("T_Ground_") + Sid);
		const FString MiPkg = Folder / (TEXT("MI_Ground_") + Sid);
		const FString VisualPkg = Folder / (TEXT("SM_") + Sid + TEXT("_Visual"));
		const FString SolidPkg = Folder / (TEXT("SM_") + Sid + TEXT("_CollSolid"));
		const FString LowPkg = Folder / (TEXT("SM_") + Sid + TEXT("_CollLow"));

		const FString TexHash = HashStrings({TEXT("ground"), Screen.GroundHash});
		if (IsUpToDate(TexPkg, TexHash))
		{
			MarkUnchanged(TexPkg, TexHash);
		}
		else
		{
			bool bExisted = false;
			UTexture2D* T = BuildTexture(TexPkg, Bundle.Dir / Screen.GroundImage, true, bExisted, OutError);
			if (!T)
			{
				return false;
			}
			MarkBuilt(T, TexPkg, TexHash, bExisted);
		}
		const FString MiHash = HashStrings({TEXT("ground-mi"), TexPkg});
		if (IsUpToDate(MiPkg, MiHash))
		{
			MarkUnchanged(MiPkg, MiHash);
		}
		else
		{
			bool bExisted = false;
			UMaterialInstanceConstant* MI = BuildMaterialInstance(MiPkg, Cast<UMaterialInterface>(LoadGenerated(SharedPackage(TEXT("M_DinkGround")))), bExisted);
			MI->SetTextureParameterValueEditorOnly(FMaterialParameterInfo(TEXT("Tex")), Cast<UTexture>(LoadGenerated(TexPkg)));
			MI->PostEditChange();
			MI->MarkPackageDirty();
			MarkBuilt(MI, MiPkg, MiHash, bExisted);
		}

		const FDinkBundleCollision* Coll = Bundle.Collision.Find(Sid);
		if (!Coll)
		{
			OutError = FString::Printf(TEXT("%s has no collision record"), *Sid);
			return false;
		}
		const FString Corners = FString::Printf(TEXT("%s %s %s %s"), *Screen.Corners.NW.ToString(), *Screen.Corners.NE.ToString(),
			*Screen.Corners.SW.ToString(), *Screen.Corners.SE.ToString());
		const FString GeoHash = HashStrings({Screen.CollisionHash, Corners, FString::SanitizeFloat(SolidVisualHeightM),
			FString::SanitizeFloat(LowVisualHeightM), FString::SanitizeFloat(CollisionHeightM), FString::SanitizeFloat(WaterSurfaceHeightM)});

		const FVector Pivot = ScreenPivot(Screen);
		auto At = [&](double X, double Y, double ZM)
		{
			return FVector3f(DinkLayout::MapPixelToUnreal(Screen.Corners, X, Y, ZM) - Pivot);
		};
		auto RectBase = [&](const FIntRect& R, FVector3f Out[4], double ZM)
		{
			Out[0] = At(R.Min.X, R.Min.Y, ZM);
			Out[1] = At(R.Max.X, R.Min.Y, ZM);
			Out[2] = At(R.Max.X, R.Max.Y, ZM);
			Out[3] = At(R.Min.X, R.Max.Y, ZM);
		};
		auto Rects = [&](const TCHAR* Class) -> const TArray<FIntRect>&
		{
			static const TArray<FIntRect> Empty;
			const TArray<FIntRect>* R = Coll->ByClass.Find(Class);
			return R ? *R : Empty;
		};

		// visual: ground grid (12x8 tiles, so the texture follows the bilinear map), blockers, water
		const FString VisualHash = HashStrings({TEXT("visual"), GeoHash, MiPkg});
		if (IsUpToDate(VisualPkg, VisualHash))
		{
			MarkUnchanged(VisualPkg, VisualHash);
		}
		else
		{
			FMeshWriter W;
			for (int32 Row = 0; Row < 8; ++Row)
			{
				for (int32 Col = 0; Col < 12; ++Col)
				{
					const double X0 = Col * 50.0, Y0 = Row * 50.0, X1 = X0 + 50.0, Y1 = Y0 + 50.0;
					FVector3f P[4] = {At(X0, Y0, 0), At(X1, Y0, 0), At(X1, Y1, 0), At(X0, Y1, 0)};
					FVector2f T[4] = {{float(X0 / 600.0), float(Y0 / 400.0)}, {float(X1 / 600.0), float(Y0 / 400.0)},
						{float(X1 / 600.0), float(Y1 / 400.0)}, {float(X0 / 600.0), float(Y1 / 400.0)}};
					W.Quad(TEXT("Ground"), P, T, FVector3f(0, 0, 1));
				}
			}
			FVector3f Base[4];
			const float SolidH = float(SolidVisualHeightM * 100.0), LowH = float(LowVisualHeightM * 100.0);
			for (const FIntRect& R : Rects(TEXT("solid"))) { RectBase(R, Base, 0); W.Prism(TEXT("Solid"), Base, SolidH); }
			for (const FIntRect& R : Rects(TEXT("low"))) { RectBase(R, Base, 0); W.Prism(TEXT("Low"), Base, LowH); }
			for (const FIntRect& R : Rects(TEXT("sprite"))) { RectBase(R, Base, 0); W.Prism(TEXT("Sprite"), Base, SolidH); }
			for (const FIntRect& R : Rects(TEXT("warp"))) { RectBase(R, Base, 0); W.Prism(TEXT("Warp"), Base, SolidH); }
			for (const FIntRect& R : Rects(TEXT("fill_water"))) { RectBase(R, Base, 0); W.Prism(TEXT("Water"), Base, float(WaterSurfaceHeightM * 100.0), false); }
			TMap<FName, UMaterialInterface*> Mats;
			Mats.Add(TEXT("Ground"), Cast<UMaterialInterface>(LoadGenerated(MiPkg)));
			Mats.Add(TEXT("Solid"), Cast<UMaterialInterface>(LoadGenerated(SharedPackage(TEXT("MI_DinkBlocker_Solid")))));
			Mats.Add(TEXT("Low"), Cast<UMaterialInterface>(LoadGenerated(SharedPackage(TEXT("MI_DinkBlocker_Low")))));
			Mats.Add(TEXT("Sprite"), Cast<UMaterialInterface>(LoadGenerated(SharedPackage(TEXT("MI_DinkBlocker_Sprite")))));
			Mats.Add(TEXT("Warp"), Cast<UMaterialInterface>(LoadGenerated(SharedPackage(TEXT("MI_DinkBlocker_Warp")))));
			Mats.Add(TEXT("Water"), Cast<UMaterialInterface>(LoadGenerated(SharedPackage(TEXT("MI_DinkWater")))));
			bool bExisted = false;
			MarkBuilt(CommitMesh(VisualPkg, W, Mats, false, bExisted), VisualPkg, VisualHash, bExisted);
		}

		// collision: solid = ground + tall prisms (codes 1,3,100,200 + canopy/void fill); low = code 2 + water fill
		const float CollH = float(CollisionHeightM * 100.0);
		const FString SolidHash = HashStrings({TEXT("coll-solid"), GeoHash});
		if (IsUpToDate(SolidPkg, SolidHash))
		{
			MarkUnchanged(SolidPkg, SolidHash);
		}
		else
		{
			FMeshWriter W;
			{
				FVector3f P[4] = {At(0, 0, 0), At(600, 0, 0), At(600, 400, 0), At(0, 400, 0)};
				FVector2f T[4] = {{0, 0}, {1, 0}, {1, 1}, {0, 1}};
				W.Quad(TEXT("Collision"), P, T, FVector3f(0, 0, 1));
			}
			FVector3f Base[4];
			for (const TCHAR* Class : {TEXT("solid"), TEXT("sprite"), TEXT("warp"), TEXT("fill_solid")})
			{
				for (const FIntRect& R : Rects(Class))
				{
					RectBase(R, Base, 0);
					W.Prism(TEXT("Collision"), Base, CollH);
				}
			}
			bool bExisted = false;
			MarkBuilt(CommitMesh(SolidPkg, W, {}, true, bExisted), SolidPkg, SolidHash, bExisted);
		}

		const int32 LowCount = Rects(TEXT("low")).Num() + Rects(TEXT("fill_water")).Num();
		const FString LowHash = HashStrings({TEXT("coll-low"), GeoHash});
		if (LowCount == 0)
		{
			// nothing low on this screen: no asset (a stale one is deleted by DeleteOrphans)
		}
		else if (IsUpToDate(LowPkg, LowHash))
		{
			MarkUnchanged(LowPkg, LowHash);
		}
		else
		{
			FMeshWriter W;
			FVector3f Base[4];
			for (const TCHAR* Class : {TEXT("low"), TEXT("fill_water")})
			{
				for (const FIntRect& R : Rects(Class))
				{
					RectBase(R, Base, 0);
					W.Prism(TEXT("Collision"), Base, CollH);
				}
			}
			bool bExisted = false;
			MarkBuilt(CommitMesh(LowPkg, W, {}, true, bExisted), LowPkg, LowHash, bExisted);
		}
		return true;
	}

	void FAssetSet::DeleteOrphans()
	{
		// An asset in the manifest that this run did not produce is an orphan only if its screen or
		// sprite left the bundle or was excluded (a region import does not touch other regions' assets).
		TSet<FString> Valid;
		for (const FDinkBundleScreen& S : Bundle.Screens)
		{
			if (S.Excluded.IsEmpty())
			{
				Valid.Add(ScreenFolder(S.Screen) + TEXT("/"));
			}
		}
		TArray<FString> Remove;
		for (const auto& Pair : ManifestHashes)
		{
			if (NewHashes.Contains(Pair.Key))
			{
				continue;
			}
			bool bKeep = false;
			if (Pair.Key.Contains(TEXT("/Screens/")))
			{
				for (const FString& Prefix : Valid)
				{
					if (Pair.Key.StartsWith(Prefix))
					{
						// still a valid screen; drop only a CollLow that is no longer needed
						const FDinkBundleCollision* C = nullptr;
						for (const FDinkBundleScreen& S : Bundle.Screens)
						{
							if (Pair.Key.StartsWith(ScreenFolder(S.Screen) + TEXT("/")))
							{
								C = Bundle.Collision.Find(S.Id);
							}
						}
						const bool bLowGone = Pair.Key.EndsWith(TEXT("_CollLow")) && C && (!C->ByClass.Contains(TEXT("low")) ||
							C->ByClass[TEXT("low")].Num() + (C->ByClass.Contains(TEXT("fill_water")) ? C->ByClass[TEXT("fill_water")].Num() : 0) == 0);
						bKeep = !bLowGone;
						break;
					}
				}
			}
			else if (Pair.Key.Contains(TEXT("/Sprites/")))
			{
				const FString Short = FPackageName::GetShortName(Pair.Key);
				FString Key = Short;
				Key.RemoveFromStart(TEXT("T_Sprite_"));
				Key.RemoveFromStart(TEXT("MI_Sprite_"));
				bKeep = Bundle.Sprites.Contains(Key);
			}
			else
			{
				bKeep = true;  // shared assets
			}
			if (!bKeep)
			{
				Remove.Add(Pair.Key);
			}
		}
		for (const FString& Package : Remove)
		{
			const FString File = PackageFile(Package);
			if (IFileManager::Get().Delete(*File, false, true, true))
			{
				UE_LOG(LogDinkImport, Display, TEXT("deleted orphan %s"), *Package);
			}
			ManifestHashes.Remove(Package);
			AssetStats.Deleted++;
		}
	}

	bool FAssetSet::SaveAll(FString& OutError)
	{
		FAssetCompilingManager::Get().FinishAllCompilation();
		int32 Saved = 0;
		for (UObject* Asset : ToSave)
		{
			UPackage* Pkg = Asset->GetOutermost();
			const FString File = PackageFile(Pkg->GetName());
			FSavePackageArgs Args;
			Args.TopLevelFlags = RF_Public | RF_Standalone;
			Args.SaveFlags = SAVE_NoError;
			if (!UPackage::SavePackage(Pkg, Asset, *File, Args))
			{
				OutError = FString::Printf(TEXT("failed to save %s"), *File);
				return false;
			}
			++Saved;
		}
		ToSave.Reset();
		UE_LOG(LogDinkImport, Display, TEXT("saved %d asset packages"), Saved);
		return SaveManifest();
	}

	UStaticMesh* FAssetSet::CardMesh() const
	{
		return Cast<UStaticMesh>(LoadGenerated(SharedPackage(TEXT("SM_DinkCard"))));
	}

	UMaterialInterface* FAssetSet::SpriteMaterial(const FString& Key) const
	{
		return Cast<UMaterialInterface>(LoadGenerated(SpritePackage(TEXT("MI_Sprite"), Key)));
	}

	UStaticMesh* FAssetSet::ScreenMesh(int32 Screen, const TCHAR* Which) const
	{
		return Cast<UStaticMesh>(LoadGenerated(FString::Printf(TEXT("%s/SM_SCR_%03d_%s"), *ScreenFolder(Screen), Screen, Which)));
	}
    bool BuildRuntimeHardnessFoundationV1(const FDinkBundle& Bundle, int32 ScreenNumber,
        FDinkHardnessFoundationCandidate& Out, FString& Error)
    {
        const FDinkBundleScreen* Screen = Bundle.FindScreen(ScreenNumber);
        const FDinkBundleCollision* Collision = Screen ? Bundle.Collision.Find(Screen->Id) : nullptr;
        if (!Screen || !Collision) { Error = TEXT("source screen/collision missing"); return false; }
        const FString Folder = FString::Printf(TEXT("/Game/Dink/RuntimeHardnessV1/SCR_%03d"), ScreenNumber);
        const FString SolidPath = Folder / FString::Printf(TEXT("SM_SCR_%03d_FixedSolidV1"), ScreenNumber);
        const FString LowPath = Folder / FString::Printf(TEXT("SM_SCR_%03d_FixedLowV1"), ScreenNumber);
        // Refuse all targets before creating anything. A changed candidate needs
        // a declared successor generation, never overwrite historical packages.
        for (const FString& Path : {SolidPath, LowPath})
            if (FindPackage(nullptr, *Path) || FPackageName::DoesPackageExist(Path))
            { Error = TEXT("foundation candidate target already exists: ") + Path; return false; }
        const FVector Pivot = FAssetSet::ScreenPivot(*Screen);
        auto At = [&](double X, double Y, double HeightM) {
            return FVector3f(DinkLayout::MapPixelToUnreal(Screen->Corners, X, Y, HeightM) - Pivot);
        };
        auto AddFill = [&](FMeshWriter& Writer, const TCHAR* Class) {
            if (const auto* Rects = Collision->ByClass.Find(Class))
                for (const auto& R : *Rects)
                {
                    FVector3f Points[4] = {At(R.Min.X,R.Min.Y,0),At(R.Max.X,R.Min.Y,0),
                        At(R.Max.X,R.Max.Y,0),At(R.Min.X,R.Max.Y,0)};
                    Writer.Prism(TEXT("Collision"), Points, float(CollisionHeightM * 100.0));
                }
        };
        FMeshWriter Solid;
        FVector3f Ground[4] = {At(0,0,0),At(600,0,0),At(600,400,0),At(0,400,0)};
        FVector2f UVs[4] = {{0,0},{1,0},{1,1},{0,1}};
        Solid.Quad(TEXT("Collision"), Ground, UVs, FVector3f(0,0,1));
        AddFill(Solid, TEXT("fill_solid"));
        FDinkHardnessFoundationCandidate Candidate;
        Candidate.Screen = ScreenNumber; Candidate.Pivot = Pivot;
        Candidate.CollisionSourceHash = Screen->CollisionHash;
        bool Existed = false;
        Candidate.FixedSolid = CommitMesh(SolidPath, Solid, {}, true, Existed);
        if (!Candidate.FixedSolid || Existed) { Error = TEXT("new solid foundation creation failed"); return false; }
        const auto* Water = Collision->ByClass.Find(TEXT("fill_water"));
        if (Water && !Water->IsEmpty())
        {
            FMeshWriter Low; AddFill(Low, TEXT("fill_water"));
            Candidate.FixedLow = CommitMesh(LowPath, Low, {}, true, Existed);
            if (!Candidate.FixedLow || Existed) { Error = TEXT("new low foundation creation failed"); return false; }
        }
        auto Provenance = [&](UStaticMesh* Mesh, const TCHAR* Role) {
            if (!Mesh) return;
            auto& Meta = Mesh->GetOutermost()->GetMetaData();
            Meta.SetValue(Mesh, TEXT("DinkHardnessSchema"), TEXT("foundation/1"));
            Meta.SetValue(Mesh, TEXT("DinkHardnessRole"), Role);
            Meta.SetValue(Mesh, TEXT("DinkHardnessScreen"), *FString::FromInt(ScreenNumber));
            Meta.SetValue(Mesh, TEXT("DinkHardnessCollisionSource"), *Screen->CollisionHash);
        };
        Provenance(Candidate.FixedSolid, TEXT("ground+fill_solid"));
        Provenance(Candidate.FixedLow, TEXT("fill_water"));
        if (!VerifyRuntimeHardnessFoundationSourceV1(Bundle, Candidate, Error)) return false;
        Out = Candidate; Error.Reset(); return true;
        // Deliberately no SavePackage, old manifest update, orphan deletion or
        // default importer call. Stage/geometry/profile verification precedes save.
    }

    bool VerifyRuntimeHardnessFoundationSourceV1(const FDinkBundle& Bundle,
        const FDinkHardnessFoundationCandidate& Candidate, FString& Error)
    {
        const auto* Screen = Bundle.FindScreen(Candidate.Screen);
        const auto* Collision = Screen ? Bundle.Collision.Find(Screen->Id) : nullptr;
        if (!Screen || !Collision || Candidate.CollisionSourceHash != Screen->CollisionHash ||
            !Candidate.Pivot.Equals(FAssetSet::ScreenPivot(*Screen), 0))
        { Error = TEXT("foundation source binding mismatch"); return false; }
        auto Signature = [](FVector3f A, FVector3f B, FVector3f C) {
            FString Best;
            const FVector3f V[3] = {A,B,C};
            for (int32 Rotation=0;Rotation<3;++Rotation)
            {
                FString S;
                for (int32 I=0;I<3;++I)
                {
                    const auto& P=V[(I+Rotation)%3];
                    S+=FString::Printf(TEXT("%.9g,%.9g,%.9g;"), P.X==0?0.f:P.X,P.Y==0?0.f:P.Y,P.Z==0?0.f:P.Z);
                }
                if (Rotation==0 || S<Best) Best=MoveTemp(S);
            }
            return Best;
        };
        auto At = [&](double X,double Y,double HeightM) {
            return FVector3f(DinkLayout::MapPixelToUnreal(Screen->Corners,X,Y,HeightM)-Candidate.Pivot);
        };
        auto Verify = [&](UStaticMesh* Mesh, const TCHAR* Role, const TCHAR* FillClass, bool Floor) {
            TArray<FString> Expected;
            if (Floor)
            {
                FVector3f P[4]={At(0,0,0),At(600,0,0),At(600,400,0),At(0,400,0)};
                if (FVector3f::CrossProduct(P[1]-P[0],P[3]-P[0]).Z<0) Swap(P[1],P[3]);
                Expected.Add(Signature(P[0],P[2],P[1])); Expected.Add(Signature(P[0],P[3],P[2]));
            }
            if (const auto* Rects=Collision->ByClass.Find(FillClass))
                for (const auto& R:*Rects)
                {
                    std::array<DinkHardness::ShellPoint,8> Points;
                    const FVector3f P[4]={At(R.Min.X,R.Min.Y,0),At(R.Max.X,R.Min.Y,0),
                        At(R.Max.X,R.Max.Y,0),At(R.Min.X,R.Max.Y,0)};
                    for (int32 I=0;I<4;++I)
                    {
                        Points[I]={P[I].X,P[I].Y,P[I].Z};
                        Points[I+4]={P[I].X,P[I].Y,P[I].Z+float(CollisionHeightM*100.0)};
                    }
                    const auto Shell=DinkHardness::OpenPrismShell(Points);
                    if (!Shell) return false;
                    for (const auto& T:*Shell)
                    {
                        auto V=[](const DinkHardness::ShellPoint& P) { return FVector3f(P.X,P.Y,P.Z); };
                        // Source MeshDescription precedes StaticMesh's cooking flip.
                        Expected.Add(Signature(V(T[1]),V(T[0]),V(T[2])));
                    }
                }
            if (Expected.IsEmpty()) return Mesh==nullptr;
            if (!Mesh || !Mesh->GetPathName().Contains(TEXT("/RuntimeHardnessV1/")) ||
                !Mesh->GetBodySetup() || Mesh->GetBodySetup()->CollisionTraceFlag!=CTF_UseComplexAsSimple ||
                Mesh->GetNaniteSettings().bEnabled) return false;
            auto& Meta=Mesh->GetOutermost()->GetMetaData();
            if (Meta.GetValue(Mesh,TEXT("DinkHardnessSchema"))!=TEXT("foundation/1") ||
                Meta.GetValue(Mesh,TEXT("DinkHardnessRole"))!=Role ||
                Meta.GetValue(Mesh,TEXT("DinkHardnessScreen"))!=FString::FromInt(Candidate.Screen) ||
                Meta.GetValue(Mesh,TEXT("DinkHardnessCollisionSource"))!=Screen->CollisionHash) return false;
            const FMeshDescription* Description=Mesh->GetMeshDescription(0);
            if (!Description || Description->Triangles().Num()!=Expected.Num()) return false;
            const FStaticMeshConstAttributes Attributes(*Description);
            const auto Positions=Attributes.GetVertexPositions();
            TArray<FString> Actual;
            for (const FTriangleID Triangle:Description->Triangles().GetElementIDs())
            {
                const auto Instances=Description->GetTriangleVertexInstances(Triangle);
                Actual.Add(Signature(Positions[Description->GetVertexInstanceVertex(Instances[0])],
                    Positions[Description->GetVertexInstanceVertex(Instances[1])],Positions[Description->GetVertexInstanceVertex(Instances[2])]));
            }
            Expected.Sort(); Actual.Sort(); return Actual==Expected;
        };
        if (!Verify(Candidate.FixedSolid,TEXT("ground+fill_solid"),TEXT("fill_solid"),true) ||
            !Verify(Candidate.FixedLow,TEXT("fill_water"),TEXT("fill_water"),false))
        { Error = TEXT("actual source triangles/provenance do not match floor/fill-only authority"); return false; }
        Error.Reset(); return true;
    }

    bool VerifyRuntimeHardnessFoundationInstanceV1(const FDinkBundle& Bundle,
        const FDinkHardnessFoundationCandidate& Candidate, UStaticMeshComponent& Solid,
        UStaticMeshComponent* Low, FString& Error)
    {
        if (!VerifyRuntimeHardnessFoundationSourceV1(Bundle,Candidate,Error)) return false;
        auto Signature=[](const FVector3f& A,const FVector3f& B,const FVector3f& C) {
            const FVector3f V[3]={A,B,C}; FString Best;
            for(int32 R=0;R<3;++R)
            {
                FString S;
                for(int32 I=0;I<3;++I) { const auto& P=V[(I+R)%3];
                    S+=FString::Printf(TEXT("%.9g,%.9g,%.9g;"),P.X==0?0.f:P.X,P.Y==0?0.f:P.Y,P.Z==0?0.f:P.Z); }
                if(R==0 || S<Best) Best=MoveTemp(S);
            }
            return Best;
        };
        FString GeometryFailure;
        auto Verify=[&](UStaticMeshComponent* C,UStaticMesh* Mesh,FName Profile,ECollisionChannel Channel,const TCHAR* RoleTag) {
            if(!Mesh) return C==nullptr || C->GetStaticMesh()==nullptr;
            FCollisionResponseTemplate Template;
            if(!C || C->GetStaticMesh()!=Mesh || !C->IsRegistered() || !C->IsPhysicsStateCreated() ||
                !C->GetBodyInstance() || !C->GetBodyInstance()->IsValidBodyInstance() || C->GetBodyInstance()->bSimulatePhysics ||
                !C->ComponentHasTag(RoleTag) || C->Mobility!=EComponentMobility::Static ||
                !C->GetComponentTransform().Equals(FTransform(Candidate.Pivot),0) || C->GetGenerateOverlapEvents() ||
                !C->CanEverAffectNavigation() || !UCollisionProfile::Get()->GetProfileTemplate(Profile,Template) ||
                C->GetCollisionProfileName()!=Profile || C->GetCollisionEnabled()!=ECollisionEnabled::QueryAndPhysics ||
                C->GetCollisionObjectType()!=Channel || Template.ObjectType!=Channel ||
                C->GetCollisionResponseToChannels()!=Template.ResponseToChannels) return false;
            const FMeshDescription* Description=Mesh->GetMeshDescription(0);
            if(!Description) return false;
            const FStaticMeshConstAttributes Attributes(*Description);
            const auto Positions=Attributes.GetVertexPositions();
            TArray<FString> Expected;
            for(const FTriangleID T:Description->Triangles().GetElementIDs())
            {
                const auto VI=Description->GetTriangleVertexInstances(T);
                // StaticMesh cooks by swapping first two vertices.
                Expected.Add(Signature(Positions[Description->GetVertexInstanceVertex(VI[1])],
                    Positions[Description->GetVertexInstanceVertex(VI[0])],Positions[Description->GetVertexInstanceVertex(VI[2])]));
            }
            TArray<FString> Actual;
            bool bReadTriangles = false;
            FPhysicsCommand::ExecuteRead(C->GetBodyInstance()->GetPhysicsActorHandle(),
                [&](const FPhysicsActorHandle& Actor)
            {
                TArray<FPhysicsShapeHandle> Shapes;
                if (FPhysicsInterface::GetAllShapes_AssumedLocked(Actor, Shapes) != 1 ||
                    Shapes.Num() != 1 || !Shapes[0].IsValid() ||
                    !FPhysicsInterface::IsQueryShape(Shapes[0]) ||
                    !FPhysicsInterface::IsSimulationShape(Shapes[0]))
                {
                    GeometryFailure = FString::Printf(TEXT("%s requires one live query and simulation shape"), RoleTag);
                    return;
                }

                // Unit-scale static meshes are registered as instanced triangle
                // meshes. The physics collection's checked getter uses a cast
                // dispatcher that does not handle triangle meshes in this engine.
                const Chaos::FImplicitObjectRef Geometry = Shapes[0].Shape->GetGeometry();
                if (!Geometry)
                {
                    GeometryFailure = FString::Printf(TEXT("%s live shape has no geometry"), RoleTag);
                    return;
                }

                Chaos::FVec3 Scale(1);
                Chaos::FReal Margin = 0;
                const auto* TriangleMesh = Chaos::UnwrapImplicit<Chaos::FTriangleMeshImplicitObject>(
                    *Geometry, Scale, Margin);
                // Fixed geometry is already in the expected local frame.
                // Reject transformed/unknown wrappers and any actual scale or margin.
                if (!TriangleMesh || Scale != Chaos::FVec3(1) || Margin != 0)
                {
                    GeometryFailure = FString::Printf(
                        TEXT("%s unsupported live triangle geometry type=%u scale=(%.17g,%.17g,%.17g) margin=%.17g"),
                        RoleTag, static_cast<uint32>(Geometry->GetType()),
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
                            GeometryFailure = FString::Printf(TEXT("%s live triangle has an invalid vertex index"), RoleTag);
                            return false;
                        }
                        Actual.Add(Signature(FVector3f(TriangleMesh->Particles().GetX(Index[0])),
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
                if (GeometryFailure.IsEmpty())
                {
                    GeometryFailure = FString::Printf(TEXT("%s live physics read did not complete"), RoleTag);
                }
                return false;
            }
            Expected.Sort();
            Actual.Sort();
            if (Actual != Expected)
            {
                GeometryFailure = FString::Printf(TEXT("%s live oriented triangle mismatch expected=%d actual=%d"),
                    RoleTag, Expected.Num(), Actual.Num());
                return false;
            }
            return true;
        };
        if(!Verify(&Solid,Candidate.FixedSolid,DinkCollision::ProfileHardSolid,DinkCollision::HardSolid,TEXT("DinkHardnessFixedFloorFillV1")) ||
            !Verify(Low,Candidate.FixedLow,DinkCollision::ProfileHardLow,DinkCollision::HardLow,TEXT("DinkHardnessFixedWaterV1")))
        {
            Error = TEXT("actual foundation instance geometry/channel/profile/nav/overlap proof failed");
            if (!GeometryFailure.IsEmpty()) Error += TEXT(": ") + GeometryFailure;
            return false;
        }
        Error.Reset(); return true;
    }

}
