#pragma once

#include "CoreMinimal.h"
#include "DinkImportBundle.h"

class UMaterial;
class UMaterialInterface;
class UMaterialInstanceConstant;
class UStaticMesh;
class UTexture2D;

/**
 * Generated assets under /Game/Dink/_Generated. Each asset has a content hash recorded in
 * Content/Dink/_Generated/import_manifest.json; an asset whose file exists and whose hash matches
 * is left untouched (so a second import writes nothing), otherwise it is rebuilt in place (same
 * object path, so maps referencing it stay valid) and saved.
 */
namespace DinkGreybox
{
	/** Bump to force every generated asset to rebuild (change of generator code). */
	inline const TCHAR* AssetGeneratorVersion = TEXT("greybox-assets/3");

	inline const TCHAR* GeneratedRoot = TEXT("/Game/Dink/_Generated");

	/** Heights (metres) of the visible blocker prisms and of all collision prisms. */
	inline constexpr double SolidVisualHeightM = 1.0;
	inline constexpr double LowVisualHeightM = 0.35;
	inline constexpr double CollisionHeightM = 3.0;
	inline constexpr double WaterSurfaceHeightM = 0.03;

	struct FAssetStats
	{
		int32 Created = 0;
		int32 Updated = 0;
		int32 Unchanged = 0;
		int32 Deleted = 0;
		TArray<FString> Changed;  // package paths built this run
	};

	class FAssetSet
	{
	public:
		explicit FAssetSet(const FDinkBundle& InBundle);

		bool LoadManifest();
		bool SaveManifest() const;

		/** Shared materials, material instances and the card mesh. */
		bool EnsureShared(FString& OutError);

		/** Texture + material instance of one sprite picture. */
		bool EnsureSprite(const FString& Key, FString& OutError);

		/** Ground texture/material and the three meshes of one screen. */
		bool EnsureScreen(const FDinkBundleScreen& Screen, FString& OutError);

		/** Removes generated screen/sprite assets whose screen or sprite is no longer in the bundle. */
		void DeleteOrphans();

		/** Saves every package built this run and waits for texture/mesh compilation. */
		bool SaveAll(FString& OutError);

		UStaticMesh* CardMesh() const;
		UMaterialInterface* SpriteMaterial(const FString& Key) const;
		UStaticMesh* ScreenMesh(int32 Screen, const TCHAR* Which) const;  // Visual | CollSolid | CollLow

		static FString ScreenFolder(int32 Screen);
		static FString SpritePackage(const TCHAR* Prefix, const FString& Key);
		/** Screen centre in Unreal cm: pivot of the screen's meshes. */
		static FVector ScreenPivot(const FDinkBundleScreen& Screen);

		const FAssetStats& Stats() const { return AssetStats; }
		const TMap<FString, FString>& Manifest() const { return ManifestHashes; }

	private:
		const FDinkBundle& Bundle;
		TMap<FString, FString> ManifestHashes;   // package path -> hash (from disk)
		TMap<FString, FString> NewHashes;        // package path -> hash (this run)
		TArray<UObject*> ToSave;
		FAssetStats AssetStats;

		bool IsUpToDate(const FString& Package, const FString& Hash) const;
		void MarkBuilt(UObject* Asset, const FString& Package, const FString& Hash, bool bExisted);
		void MarkUnchanged(const FString& Package, const FString& Hash);

		UMaterial* BuildBaseMaterial(const FString& Package, int32 Kind, bool& bExisted);
		UMaterialInstanceConstant* BuildMaterialInstance(const FString& Package, UMaterialInterface* Parent, bool& bExisted);
		UTexture2D* BuildTexture(const FString& Package, const FString& PngFile, bool bStretchToPow2, bool& bExisted, FString& OutError);
	};

	/** Loads an asset by package path (/Game/.../Name), nullptr if absent. */
	UObject* LoadGenerated(const FString& Package);

	FString HashStrings(const TArray<FString>& Parts);
}
