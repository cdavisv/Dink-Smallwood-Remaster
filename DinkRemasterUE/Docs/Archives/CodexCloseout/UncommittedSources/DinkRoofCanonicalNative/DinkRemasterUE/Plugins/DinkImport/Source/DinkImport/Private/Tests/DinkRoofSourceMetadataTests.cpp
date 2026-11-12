#include "DinkRoofSourceMetadataLibrary.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/StaticMeshSourceData.h"
#include "Factories/FbxStaticMeshImportData.h"
#include "EditorFramework/AssetImportData.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"
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
 return true;
}
#endif
