#include "DinkRoofSourceMetadataLibrary.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/StaticMeshSourceData.h"
#include "Factories/FbxStaticMeshImportData.h"
#include "EditorFramework/AssetImportData.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "Misc/FileHelper.h"
#include "Misc/ScopeExit.h"
#include "Misc/SecureHash.h"
#include "HAL/FileManager.h"
#include "UObject/Package.h"
#if WITH_DEV_AUTOMATION_TESTS
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkRoofSourceMetadataTest,"Dink.Import.Inspection.RoofRelativeSourceFilenames",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FDinkRoofSourceMetadataTest::RunTest(const FString&)
{
 TestFalse(TEXT("null rejected"),UDinkRoofSourceMetadataLibrary::SetRoofSourceFilenamesRelative(nullptr,{}));
 const FString ScratchPackageName=TEXT("/Game/DinkQA/TransientRoofMetadata_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
 UPackage* Package=CreatePackage(*ScratchPackageName);
 UStaticMesh* Mesh=NewObject<UStaticMesh>(Package,TEXT("SM_Fireplace_Stonebrook_V3Contact"),RF_Transient);
 UFbxStaticMeshImportData* Data=NewObject<UFbxStaticMeshImportData>(Mesh,NAME_None,RF_Transient);Mesh->SetAssetImportData(Data);TArray<FString> Files;
 for(int32 LOD=0;LOD<3;++LOD)
 {
  Mesh->AddSourceModel();Files.Add(FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/Art/Stonebrook/Refinements/RoofChimneyV12d/ExportV12d_Run01/FBX")/FString::Printf(TEXT("SM_Fireplace_Stonebrook_V3Contact_LOD%d.fbx"),LOD)));Mesh->GetSourceModel(LOD).SourceImportFilename=Files.Last();
 }
 TArray<FAssetImportInfo::FSourceFile> Sources;Sources.Emplace(Files[0],FDateTime(2020,1,2),FMD5Hash());Data->SetSourceFiles(MoveTemp(Sources));
 const auto Before=Data->GetSourceData().SourceFiles[0];const FString Raw=UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(Mesh);const bool Dirty=Package->IsDirty();
 TestFalse(TEXT("public canonical setter refuses scratch scope"),UDinkRoofSourceMetadataLibrary::SetRoofSourceFilenamesRelative(Mesh,Files));
 TArray<FString> Bad=Files;Bad[2]+=TEXT(".missing");TestFalse(TEXT("late invalid LOD rejected atomically"),UDinkRoofSourceMetadataLibrary::ApplyFilenameTransaction(Mesh,Bad));
 TestEqual(TEXT("all raw state unchanged"),UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(Mesh),Raw);TestEqual(TEXT("dirty state unchanged"),Package->IsDirty(),Dirty);
 TestTrue(TEXT("scratch3LOD transaction normalized"),UDinkRoofSourceMetadataLibrary::ApplyFilenameTransaction(Mesh,Files));
 const auto After=Data->GetSourceData().SourceFiles[0];TestTrue(TEXT("timestamp retained"),After.Timestamp==Before.Timestamp);TestTrue(TEXT("MD5 retained"),After.FileHash==Before.FileHash);TestTrue(TEXT("base raw relative"),FPaths::IsRelative(After.RelativeFilename));
 for(int32 LOD=0;LOD<3;++LOD){const FString Stored=Mesh->GetSourceModel(LOD).SourceImportFilename;TestTrue(TEXT("raw LOD nonempty relative"),!Stored.IsEmpty()&&FPaths::IsRelative(Stored));TestEqual(TEXT("LOD resolves canonical"),FPaths::ConvertRelativePathToFull(UAssetImportData::ResolveImportFilename(Stored,Package)),Files[LOD]);}
 const FString Snapshot=UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(Mesh);TestEqual(TEXT("inspector read only"),UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(Mesh),Snapshot);TestEqual(TEXT("source model count unchanged"),Mesh->GetNumSourceModels(),3);TestTrue(TEXT("no render geometry created"),Mesh->GetMeshDescription(0)==nullptr);
 UPackage* TexturePackage=CreatePackage(*(ScratchPackageName+TEXT("_Texture")));
 UTexture2D* Texture=NewObject<UTexture2D>(TexturePackage,TEXT("T_FireplaceV2_Atlas_BC"),RF_Transient);Texture->AssetImportData=NewObject<UAssetImportData>(Texture,NAME_None,RF_Transient);
 const FString PNG=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/Art/Stonebrook/Refinements/RoofChimneyV12d/ExportV12d_Run01/Textures/T_FireplaceV2_Atlas_BC.png"));
 TArray<FAssetImportInfo::FSourceFile> TextureSources;TextureSources.Emplace(PNG,FDateTime(2020,1,2),FMD5Hash());Texture->AssetImportData->SetSourceFiles(MoveTemp(TextureSources));
 const auto TextureBefore=Texture->AssetImportData->GetSourceData().SourceFiles[0];
 const FString TextureRawBefore=UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(Texture);const bool TextureDirty=TexturePackage->IsDirty();
 TestFalse(TEXT("public texture setter refuses scratch scope"),UDinkRoofSourceMetadataLibrary::SetRoofSourceFilenamesRelative(Texture,{PNG}));
 TestEqual(TEXT("public rejection leaves texture metadata exact"),UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(Texture),TextureRawBefore);TestEqual(TEXT("public rejection leaves texture dirty state exact"),TexturePackage->IsDirty(),TextureDirty);
 TestTrue(TEXT("scratch texture transaction normalized"),UDinkRoofSourceMetadataLibrary::ApplyFilenameTransaction(Texture,{PNG}));
 const auto TextureAfter=Texture->AssetImportData->GetSourceData().SourceFiles[0];TestTrue(TEXT("texture raw filename relative"),FPaths::IsRelative(TextureAfter.RelativeFilename));TestTrue(TEXT("texture source hash retained"),TextureAfter.FileHash==TextureBefore.FileHash);TestTrue(TEXT("texture timestamp retained"),TextureAfter.Timestamp==TextureBefore.Timestamp);TestFalse(TEXT("metadata setter does not initialize pixels"),Texture->Source.IsValid());
 TestTrue(TEXT("dedicated four-gable capability"),UDinkRoofSourceMetadataLibrary::SupportsInteriorGableRecessSourceFilenames());
 TestFalse(TEXT("gable null refused"),UDinkRoofSourceMetadataLibrary::SetInteriorGableRecessSourceFilenamesRelative(nullptr,{}));
 TestFalse(TEXT("gable texture class refused"),UDinkRoofSourceMetadataLibrary::SetInteriorGableRecessSourceFilenamesRelative(Texture,{PNG}));
 TestFalse(TEXT("gable wrong namespace refused"),UDinkRoofSourceMetadataLibrary::SetInteriorGableRecessSourceFilenamesRelative(Mesh,{Files[0]}));
 const TArray<FString> Gables={TEXT("SM_IndoorRoof_Gable_EN_01"),TEXT("SM_IndoorRoof_Gable_ES_01"),TEXT("SM_IndoorRoof_Gable_WN_01"),TEXT("SM_IndoorRoof_Gable_WS_01")};
 const FString ScopeFile=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/Art/Stonebrook/Refinements/InteriorGableRecessV1/FBX")/(Gables[0]+TEXT(".fbx")));
 UStaticMesh* WrongNamespace=NewObject<UStaticMesh>(Package,*Gables[0],RF_Transient);WrongNamespace->AddSourceModel();UFbxStaticMeshImportData* ScopeData=NewObject<UFbxStaticMeshImportData>(WrongNamespace,NAME_None,RF_Transient);WrongNamespace->SetAssetImportData(ScopeData);TArray<FAssetImportInfo::FSourceFile> ScopeSources;ScopeSources.Emplace(ScopeFile,FDateTime(2020,1,2),FMD5Hash());ScopeData->SetSourceFiles(MoveTemp(ScopeSources));
 const FString WrongNamespaceBefore=UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(WrongNamespace);const bool WrongNamespaceDirty=Package->IsDirty();
 TestFalse(TEXT("exact gable name in scratch namespace refused"),UDinkRoofSourceMetadataLibrary::SetInteriorGableRecessSourceFilenamesRelative(WrongNamespace,{ScopeFile}));TestEqual(TEXT("wrong namespace metadata unchanged"),UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(WrongNamespace),WrongNamespaceBefore);TestEqual(TEXT("wrong namespace dirty unchanged"),Package->IsDirty(),WrongNamespaceDirty);
 for (const FString& Name:Gables)
 {
  const FString GablePackageName=TEXT("/Game/Dink/Refinements/InteriorGableRecessV1/Meshes/")+Name;
  if (!TestFalse(TEXT("gable target not already loaded"),FindPackage(nullptr,*GablePackageName)!=nullptr)||!TestFalse(TEXT("gable target not already saved"),FPackageName::DoesPackageExist(GablePackageName))) return false;
  const FString File=FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()/TEXT("SourceAssets/Art/Stonebrook/Refinements/InteriorGableRecessV1/FBX")/(Name+TEXT(".fbx")));
  if (!TestTrue(TEXT("actual canonical gable FBX staged"),FPaths::FileExists(File))) return false;
  UPackage* GablePackage=CreatePackage(*GablePackageName);
  UStaticMesh* Gable=NewObject<UStaticMesh>(GablePackage,*Name,RF_Transient);Gable->AddSourceModel();Gable->GetSourceModel(0).SourceImportFilename=File;
  UFbxStaticMeshImportData* GableData=NewObject<UFbxStaticMeshImportData>(Gable,NAME_None,RF_Transient);Gable->SetAssetImportData(GableData);
  TArray<FAssetImportInfo::FSourceFile> GableSources;GableSources.Emplace(File,FDateTime(2020,1,2),FMD5Hash::HashFile(*File));GableData->SetSourceFiles(MoveTemp(GableSources));
  auto RefusedWithoutMutation=[&](const TArray<FString>& Requested,const TCHAR* Label)
  {
   const FString Prior=UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(Gable);const bool PriorDirty=GablePackage->IsDirty();
   TestFalse(Label,UDinkRoofSourceMetadataLibrary::SetInteriorGableRecessSourceFilenamesRelative(Gable,Requested));
   TestEqual(TEXT("gable rejection metadata unchanged"),UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(Gable),Prior);TestEqual(TEXT("gable rejection dirty unchanged"),GablePackage->IsDirty(),PriorDirty);
  };
  RefusedWithoutMutation({},TEXT("gable zero paths refused"));RefusedWithoutMutation({File,File},TEXT("gable two paths refused"));
  RefusedWithoutMutation({Files[0]},TEXT("gable other canonical source refused"));RefusedWithoutMutation({Name+TEXT(".fbx")},TEXT("gable relative input refused"));
  Gable->AddSourceModel();RefusedWithoutMutation({File},TEXT("gable second LOD refused"));Gable->RemoveSourceModel(1);
  TArray<FAssetImportInfo::FSourceFile> SavedSources=GableData->GetSourceData().SourceFiles;TArray<FAssetImportInfo::FSourceFile> ExtraSources=SavedSources;ExtraSources.Add(SavedSources[0]);GableData->SetSourceFiles(MoveTemp(ExtraSources));
  RefusedWithoutMutation({File},TEXT("gable multiple source rows refused"));GableData->SetSourceFiles(MoveTemp(SavedSources));
  Gable->SetAssetImportData(Data);RefusedWithoutMutation({File},TEXT("gable foreign import-data owner refused"));Gable->SetAssetImportData(GableData);
  UStaticMesh* WrongName=NewObject<UStaticMesh>(GablePackage,*(Name+TEXT("_Wrong")),RF_Transient);WrongName->AddSourceModel();UFbxStaticMeshImportData* WrongData=NewObject<UFbxStaticMeshImportData>(WrongName,NAME_None,RF_Transient);WrongName->SetAssetImportData(WrongData);TArray<FAssetImportInfo::FSourceFile> WrongSources;WrongSources.Emplace(File,FDateTime(2020,1,2),FMD5Hash());WrongData->SetSourceFiles(MoveTemp(WrongSources));
  const FString WrongNameBefore=UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(WrongName);const bool WrongNameDirty=GablePackage->IsDirty();
  TestFalse(TEXT("gable wrong object name refused"),UDinkRoofSourceMetadataLibrary::SetInteriorGableRecessSourceFilenamesRelative(WrongName,{File}));TestEqual(TEXT("wrong name metadata unchanged"),UDinkRoofSourceMetadataLibrary::InspectRoofSourceFilenames(WrongName),WrongNameBefore);TestEqual(TEXT("wrong name dirty unchanged"),GablePackage->IsDirty(),WrongNameDirty);
  TestFalse(TEXT("old setter remains closed to gable namespace"),UDinkRoofSourceMetadataLibrary::SetRoofSourceFilenamesRelative(Gable,{File}));
  const auto Prior=GableData->GetSourceData().SourceFiles[0];
  if (!TestTrue(TEXT("exact unsaved gable metadata transaction"),UDinkRoofSourceMetadataLibrary::SetInteriorGableRecessSourceFilenamesRelative(Gable,{File}))) return false;
  const auto Updated=GableData->GetSourceData().SourceFiles[0];const FString StoredLOD=Gable->GetSourceModel(0).SourceImportFilename;
  TestTrue(TEXT("gable MD5 retained"),Updated.FileHash==Prior.FileHash);TestTrue(TEXT("gable timestamp retained"),Updated.Timestamp==Prior.Timestamp);
  TestTrue(TEXT("gable base raw relative"),FPaths::IsRelative(Updated.RelativeFilename));TestTrue(TEXT("gable LOD raw relative"),!StoredLOD.IsEmpty()&&FPaths::IsRelative(StoredLOD));
  TestEqual(TEXT("gable base resolves canonical"),FPaths::ConvertRelativePathToFull(UAssetImportData::ResolveImportFilename(Updated.RelativeFilename,GablePackage)),File);
  TestEqual(TEXT("gable LOD resolves canonical"),FPaths::ConvertRelativePathToFull(UAssetImportData::ResolveImportFilename(StoredLOD,GablePackage)),File);
  TestEqual(TEXT("gable one LOD retained"),Gable->GetNumSourceModels(),1);TestTrue(TEXT("gable metadata does not build geometry"),Gable->GetMeshDescription(0)==nullptr);
  if (Name==Gables[0])
  {
   // Owned Saved-only existence sentinel, not an asset save or project mutation.
   const FString Mount=TEXT("/Game/Dink/Refinements/InteriorGableRecessV1/");
   FString TempRoot=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("Automation/GableMetadataExistence")/FGuid::NewGuid().ToString(EGuidFormats::Digits));TempRoot+=TEXT("/");
   IFileManager::Get().MakeDirectory(*(TempRoot/TEXT("Meshes")),true);FPackageName::RegisterMountPoint(Mount,TempRoot);
   ON_SCOPE_EXIT { FPackageName::UnRegisterMountPoint(Mount,TempRoot);IFileManager::Get().DeleteDirectory(*TempRoot,false,true); };
   const FString Sentinel=TempRoot/TEXT("Meshes")/(Name+TEXT(".uasset"));
   if (!TestTrue(TEXT("owned package-existence marker written"),FFileHelper::SaveStringToFile(TEXT("metadata refusal sentinel; never loaded"),*Sentinel))||!TestTrue(TEXT("saved-package guard sees owned marker"),FPackageName::DoesPackageExist(GablePackageName))) return false;
   RefusedWithoutMutation({File},TEXT("already-on-disk gable refused"));
  }
 }
 return true;
}
#endif
