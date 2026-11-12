#include "DinkRoofSourceMetadataLibrary.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSourceData.h"
#include "Engine/Texture2D.h"
#include "EditorFramework/AssetImportData.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace
{
const FString RoofNamespace=TEXT("/Game/Dink/Refinements/RoofChimneyV12d/");
const TSet<FString> RoofMeshes={TEXT("SM_Chimney_Stonebrook_V8"),TEXT("SM_Fireplace_Stonebrook_V3Contact"),TEXT("SM_IndoorRoof_EN_01"),TEXT("SM_IndoorRoof_ES_01"),TEXT("SM_IndoorRoof_Gable_EN_01"),TEXT("SM_IndoorRoof_Gable_ES_01"),TEXT("SM_IndoorRoof_Gable_WN_01"),TEXT("SM_IndoorRoof_Gable_WS_01"),TEXT("SM_IndoorRoof_WN_01"),TEXT("SM_IndoorRoof_WS_01")};
const TSet<FString> RoofTextures={TEXT("T_FireplaceV2_Atlas_BC"),TEXT("T_FireplaceV2_Atlas_E"),TEXT("T_FireplaceV2_Atlas_N"),TEXT("T_FireplaceV2_Atlas_ORM"),TEXT("T_InteriorRoof_GablePlaster_BC"),TEXT("T_InteriorRoof_GablePlaster_N"),TEXT("T_InteriorRoof_GablePlaster_ORM"),TEXT("T_InteriorRoof_OakEndgrain_BC"),TEXT("T_InteriorRoof_OakEndgrain_N"),TEXT("T_InteriorRoof_OakEndgrain_ORM"),TEXT("T_InteriorRoof_OakLonggrain_BC"),TEXT("T_InteriorRoof_OakLonggrain_N"),TEXT("T_InteriorRoof_OakLonggrain_ORM"),TEXT("T_InteriorRoof_RoofBoards_BC"),TEXT("T_InteriorRoof_RoofBoards_N"),TEXT("T_InteriorRoof_RoofBoards_ORM"),TEXT("T_V8_CoursedLimestone_BC"),TEXT("T_V8_CoursedLimestone_N"),TEXT("T_V8_CoursedLimestone_ORM"),TEXT("T_V8_DullZinc_BC"),TEXT("T_V8_DullZinc_N"),TEXT("T_V8_DullZinc_ORM"),TEXT("T_V8_SootLining_BC"),TEXT("T_V8_SootLining_N"),TEXT("T_V8_SootLining_ORM")};
const FString SharedRoofNamespace=TEXT("/Game/Dink/Refinements/InteriorRoofSharedV1/Meshes/");
const FString SharedTextureNamespace=TEXT("/Game/Dink/Materials/Shared/Textures/");
const TSet<FString> SharedRoofMeshes={TEXT("SM_IndoorRoof_EN_01"),TEXT("SM_IndoorRoof_ES_01"),TEXT("SM_IndoorRoof_Gable_EN_01"),TEXT("SM_IndoorRoof_Gable_ES_01"),TEXT("SM_IndoorRoof_Gable_WN_01"),TEXT("SM_IndoorRoof_Gable_WS_01"),TEXT("SM_IndoorRoof_WN_01"),TEXT("SM_IndoorRoof_WS_01")};
const TSet<FString> SharedRoofTextures={TEXT("T_Shared_OakLonggrain2m_BC"),TEXT("T_Shared_OakLonggrain2m_N_GL"),TEXT("T_Shared_OakLonggrain2m_ORM"),TEXT("T_Shared_OakEndgrain2m_BC"),TEXT("T_Shared_OakEndgrain2m_N_GL"),TEXT("T_Shared_OakEndgrain2m_ORM"),TEXT("T_Shared_LimePlaster2m_BC"),TEXT("T_Shared_LimePlaster2m_N_GL"),TEXT("T_Shared_LimePlaster2m_ORM")};
UAssetImportData* ImportData(UObject* Asset)
{
 if (UStaticMesh* Mesh=Cast<UStaticMesh>(Asset)) return Mesh->GetAssetImportData();
 if (UTexture2D* Texture=Cast<UTexture2D>(Asset)) return Texture->AssetImportData;
 return nullptr;
}
FString Full(const FString& In)
{
 FString Result=FPaths::ConvertRelativePathToFull(In);FPaths::NormalizeFilename(Result);FPaths::CollapseRelativeDirectories(Result);return Result;
}
}

FString UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(UObject* Asset)
{
 TSharedRef<FJsonObject> Root=MakeShared<FJsonObject>();
 Root->SetStringField(TEXT("schema"),TEXT("dink-roof-source-filenames/1"));
 UAssetImportData* Data=ImportData(Asset);Root->SetBoolField(TEXT("valid"),Data!=nullptr);
 TArray<TSharedPtr<FJsonValue>> Files,LODs;
 if (Data)
 {
  Root->SetStringField(TEXT("asset"),Asset->GetPathName());
  for (const FAssetImportInfo::FSourceFile& File:Data->GetSourceData().SourceFiles)
  {
   TSharedRef<FJsonObject> Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("stored"),File.RelativeFilename);
   Row->SetBoolField(TEXT("relative"),FPaths::IsRelative(File.RelativeFilename));
   Row->SetStringField(TEXT("resolved"),Full(UAssetImportData::ResolveImportFilename(File.RelativeFilename,Asset->GetOutermost())));
   Files.Add(MakeShared<FJsonValueObject>(Row));
  }
  if (UStaticMesh* Mesh=Cast<UStaticMesh>(Asset)) for (int32 Index=0;Index<Mesh->GetNumSourceModels();++Index)
  {
   const FString& Stored=Mesh->GetSourceModel(Index).SourceImportFilename;
   TSharedRef<FJsonObject> Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("LOD"),Index);
   Row->SetStringField(TEXT("stored"),Stored);Row->SetBoolField(TEXT("relative"),FPaths::IsRelative(Stored));
   Row->SetStringField(TEXT("resolved"),Stored.IsEmpty()?FString():Full(UAssetImportData::ResolveImportFilename(Stored,Asset->GetOutermost())));
   LODs.Add(MakeShared<FJsonValueObject>(Row));
  }
 }
 Root->SetArrayField(TEXT("files"),Files);Root->SetArrayField(TEXT("LODs"),LODs);
 FString Result;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Result));return Result;
}

bool UDinkRoofSourceMetadataLibrary::SupportsSharedRoofSourceFilenames()
{
 return true; // Read-only capability check, so old DLLs refuse before any import.
}

bool UDinkRoofSourceMetadataLibrary::SupportsInteriorGableRecessSourceFilenames()
{
 return true; // A missing/old module must refuse before any candidate import.
}

bool UDinkRoofSourceMetadataLibrary::SetInteriorGableRecessSourceFilenamesRelative(UObject* Asset,const TArray<FString>& ExpectedAbsoluteFiles)
{
 UStaticMesh* Mesh=Cast<UStaticMesh>(Asset);if (!Mesh||Mesh->IsTemplate()) return false;
 UAssetImportData* Data=Mesh->GetAssetImportData();
 if (!Data||Data->GetOuter()!=Mesh||Data->IsTemplate()||Data->GetSourceFileCount()!=1||Mesh->GetNumSourceModels()!=1||ExpectedAbsoluteFiles.Num()!=1) return false;
 static const TSet<FString> Gables={TEXT("SM_IndoorRoof_Gable_EN_01"),TEXT("SM_IndoorRoof_Gable_ES_01"),TEXT("SM_IndoorRoof_Gable_WN_01"),TEXT("SM_IndoorRoof_Gable_WS_01")};
 const FString Name=Mesh->GetName();const FString Package=Mesh->GetOutermost()->GetName();
 if (!Gables.Contains(Name)||Package!=TEXT("/Game/Dink/Refinements/InteriorGableRecessV1/Meshes/")+Name||FPackageName::DoesPackageExist(Package)) return false;
 const FString Canonical=Full(FPaths::ProjectDir()/TEXT("SourceAssets/Art/Stonebrook/Refinements/InteriorGableRecessV1/FBX")/(Name+TEXT(".fbx")));
 const FString& File=ExpectedAbsoluteFiles[0];
 if (FPaths::IsRelative(File)||Full(File)!=File||File!=Canonical||!FPaths::FileExists(File)) return false;
 const FString Stored=UAssetImportData::SanitizeImportFilename(File,Mesh->GetOutermost());
 if (Stored.IsEmpty()||!FPaths::IsRelative(Stored)||Full(UAssetImportData::ResolveImportFilename(Stored,Mesh->GetOutermost()))!=File) return false;
 return ApplyFilenameTransaction(Mesh,ExpectedAbsoluteFiles);
}

bool UDinkRoofSourceMetadataLibrary::SetRoofSourceFilenamesRelative(UObject* Asset,const TArray<FString>& ExpectedAbsoluteFiles)
{
 UAssetImportData* Data=ImportData(Asset);if (!Data||Data->GetSourceFileCount()!=1) return false;
 UStaticMesh* Mesh=Cast<UStaticMesh>(Asset);const FString Name=Asset->GetName();
 const FString Package=Asset->GetOutermost()->GetName();
 const bool Legacy=(Mesh?RoofMeshes:RoofTextures).Contains(Name)&&Package==RoofNamespace+(Mesh?TEXT("Meshes/"):TEXT("Textures/"))+Name;
 const bool Shared=Mesh ? SharedRoofMeshes.Contains(Name)&&Package==SharedRoofNamespace+Name : SharedRoofTextures.Contains(Name)&&Package==SharedTextureNamespace+Name;
 if (!Legacy&&!Shared) return false;
 const bool Fireplace=Legacy&&Mesh&&Name==TEXT("SM_Fireplace_Stonebrook_V3Contact");
 const int32 Count=Mesh?Mesh->GetNumSourceModels():1;
 if (Count!=(Fireplace?3:1)||ExpectedAbsoluteFiles.Num()!=Count) return false;
 if (FPackageName::DoesPackageExist(Package)) return false; // Never rewrite a published/saved asset.
 const FString SourceRoot=Legacy ? TEXT("SourceAssets/Art/Stonebrook/Refinements/RoofChimneyV12d/ExportV12d_Run01") : Mesh ? TEXT("SourceAssets/Art/Stonebrook/Refinements/InteriorRoofSharedV1") : TEXT("SourceAssets/Art/SharedMaterials/OakLime2mV1");
 const FString Packet=Full(FPaths::ProjectDir()/SourceRoot);
 TArray<FString> Relative;
 for (int32 Index=0;Index<Count;++Index)
 {
  const FString& File=ExpectedAbsoluteFiles[Index];if (FPaths::IsRelative(File)||Full(File)!=File||!FPaths::FileExists(File)) return false;
  FString Expected;
  if (Mesh) Expected=Packet/TEXT("FBX")/(Name+(Fireplace?FString::Printf(TEXT("_LOD%d"),Index):FString())+TEXT(".fbx"));
  else
  {
   const FString Single=Packet/TEXT("Textures")/(Name+TEXT(".png"));
   const FString Double=Packet/TEXT("Textures")/(Name+TEXT(".png.png"));
   if (File!=Single&&(!Legacy||File!=Double)) return false;
   Expected=File;
  }
  if (File!=Expected) return false;
  const FString Stored=UAssetImportData::SanitizeImportFilename(File,Asset->GetOutermost());
  if (Stored.IsEmpty()||!FPaths::IsRelative(Stored)||Full(UAssetImportData::ResolveImportFilename(Stored,Asset->GetOutermost()))!=File) return false;
  Relative.Add(Stored);
 }
 return ApplyFilenameTransaction(Asset,ExpectedAbsoluteFiles);
}

bool UDinkRoofSourceMetadataLibrary::ApplyFilenameTransaction(UObject* Asset,const TArray<FString>& ExpectedAbsoluteFiles)
{
 UAssetImportData* Data=ImportData(Asset);if (!Data||Data->GetSourceFileCount()!=1) return false;
 UStaticMesh* Mesh=Cast<UStaticMesh>(Asset);const int32 Count=Mesh?Mesh->GetNumSourceModels():1;
 if (Count<1||ExpectedAbsoluteFiles.Num()!=Count) return false;
 TArray<FString> Relative;
 for (const FString& File:ExpectedAbsoluteFiles)
 {
  if (FPaths::IsRelative(File)||Full(File)!=File||!FPaths::FileExists(File)) return false;
  const FString Stored=UAssetImportData::SanitizeImportFilename(File,Asset->GetOutermost());
  if (Stored.IsEmpty()||!FPaths::IsRelative(Stored)||Full(UAssetImportData::ResolveImportFilename(Stored,Asset->GetOutermost()))!=File) return false;
  Relative.Add(Stored);
 }
 // All transaction validation precedes the first mutation. Public entry has
 // additionally validated exact canonical scope/name/file roles and disk absence.
 Asset->Modify();Data->Modify();Data->UpdateFilenameOnly(ExpectedAbsoluteFiles[0],0);
 if (Mesh) for (int32 Index=0;Index<Count;++Index) Mesh->GetSourceModel(Index).SourceImportFilename=Relative[Index];
 Asset->MarkPackageDirty();return true;
}
