#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"
#include "HAL/PlatformProperties.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"
#include "Serialization/Csv/CsvParser.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "Engine/Texture2D.h"
#include "Materials/MaterialInterface.h"
#include "UObject/Package.h"
#include "Hardness/DinkFamilyCollisionFit.h"

// Client-only deliberately excludes Editor: uncooked PIE must not produce a cooked-data pass.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCookedReleasedPictures,
    "Dink.Art.Family.CookedReleasedPictureAssets",
    EAutomationTestFlags::ClientContext|EAutomationTestFlags::ProductFilter)
bool FDinkCookedReleasedPictures::RunTest(const FString&)
{
    if(!TestTrue(TEXT("actual Game platform requires cooked data"),FPlatformProperties::RequiresCookedData()))return false;
    const FString Directory=FPaths::ProjectSavedDir()/TEXT("Automation");
    const FString Output=Directory/TEXT("CookedReleasedPictureAssets.json");
    if(!TestFalse(TEXT("preserve prior cooked-picture receipt"),IFileManager::Get().FileExists(*Output)))return false;
    FString Csv;
    if(!TestTrue(TEXT("actual staged frame source facts load"),FFileHelper::LoadFileToString(Csv,*(FPaths::ProjectContentDir()/TEXT("Dink/Data/Gameplay/frames.csv")))))return false;
    const FCsvParser Parser(Csv);const auto& Rows=Parser.GetRows();
    if(!TestTrue(TEXT("actual CSV has header/data"),Rows.Num()>1))return false;
    auto Column=[&](const TCHAR* Name)->int32{int32 Found=INDEX_NONE;for(int32 I=0;I<Rows[0].Num();++I)if(FString(Rows[0][I])==Name){if(Found!=INDEX_NONE)return INDEX_NONE;Found=I;}return Found;};
    const TArray<FString> Fields={TEXT("seq"),TEXT("frame"),TEXT("width"),TEXT("height"),TEXT("origin_x"),TEXT("origin_y"),TEXT("picture_descriptor_sha1")};
    TArray<int32> Columns;for(const auto& Name:Fields){const int32 I=Column(*Name);if(!TestTrue(TEXT("required CSV column exists exactly once"),I!=INDEX_NONE))return false;Columns.Add(I);}
    struct FExpected{int32 Frame,Width,Height;const TCHAR* Digest;FIntPoint Imported;};
    const FExpected Expected[]={{1,56,55,TEXT("b89b9bd0f6829a4c377345a7a3fe79793660dbfc"),FIntPoint(64,64)},
        {6,84,64,TEXT("31f8a48f1ae2bafe331f21acd5b8da64a4fa6ad9"),FIntPoint(128,64)}};
    FDinkFamilyCollisionFitCandidate Candidate;Candidate.bReleasePicturePrepared=true;
    TArray<TSharedPtr<FJsonValue>> Facts;
    for(const auto& E:Expected)
    {
        TArray<const TArray<const TCHAR*>*> Matches;
        for(int32 I=1;I<Rows.Num();++I)if(Rows[I].Num()==Rows[0].Num()&&FString(Rows[I][Columns[0]])==TEXT("173")&&FString(Rows[I][Columns[1]])==LexToString(E.Frame))Matches.Add(&Rows[I]);
        if(!TestEqual(TEXT("one actual source frame row"),Matches.Num(),1))return false;
        const auto& R=*Matches[0];const TArray<FString> Exact={TEXT("173"),LexToString(E.Frame),LexToString(E.Width),LexToString(E.Height),TEXT("41"),TEXT("44"),E.Digest};
        for(int32 I=0;I<Exact.Num();++I)if(!TestEqual(TEXT("staged source frame facts equal independently frozen authored facts"),FString(R[Columns[I]]),Exact[I]))return false;
        FDinkLegacyPictureDescriptor P;P.Sequence=173;P.Frame=E.Frame;P.Width=E.Width;P.Height=E.Height;P.OriginX=41;P.OriginY=44;P.Sha1=E.Digest;
        const FString Key=FString::Printf(TEXT("173_%02d"),E.Frame);
        const FString MIPath=TEXT("/Game/Dink/_Generated/Sprites/MI_Sprite_")+Key+TEXT(".MI_Sprite_")+Key;
        const FString TexPath=TEXT("/Game/Dink/_Generated/Sprites/T_Sprite_")+Key+TEXT(".T_Sprite_")+Key;
        auto* MI=LoadObject<UMaterialInterface>(nullptr,*MIPath);auto* Texture=LoadObject<UTexture2D>(nullptr,*TexPath);
        if(!TestNotNull(TEXT("actual selected cooked MIC loads"),MI)||!TestNotNull(TEXT("actual selected cooked texture loads"),Texture))return false;
        if(!TestTrue(TEXT("both actual packages are cooked"),MI->GetPackage()->HasAnyPackageFlags(PKG_Cooked)&&Texture->GetPackage()->HasAnyPackageFlags(PKG_Cooked))||
           !TestEqual(TEXT("actual material identity"),MI->GetPathName(),MIPath)||!TestEqual(TEXT("actual texture identity"),Texture->GetPathName(),TexPath))return false;
        UTexture* Parameter=nullptr;
        if(!TestTrue(TEXT("actual cooked material Tex resolves the exact loaded texture"),MI->GetTextureParameterValue(FMaterialParameterInfo(TEXT("Tex")),Parameter)&&Parameter==Texture))return false;
        FIntPoint Observed;
        if(!TestTrue(TEXT("production imported-size matcher accepts actual cooked metadata"),DinkFamilyCollisionFit::MatchesLegacyPictureImportedSize(P,*Texture,&Observed))||
           !TestEqual(TEXT("actual serialized imported dimensions"),Observed,E.Imported))return false;
        // Valid alternate descriptors isolate dimension rejection, rather than a stale descriptor-hash failure.
        for(const bool Width:{true,false})
        {
            auto Wrong=P;if(Width)Wrong.Width=E.Imported.X+1;else Wrong.Height=E.Imported.Y+1;
            const FString Text=FString::Printf(TEXT("DinkPictureDescriptor/1:%d,%d,%d,%d,%d,%d"),Wrong.Sequence,Wrong.Frame,Wrong.Width,Wrong.Height,Wrong.OriginX,Wrong.OriginY);
            FTCHARToUTF8 Utf8(*Text);uint8 Hash[FSHA1::DigestSize];FSHA1::HashBuffer(Utf8.Get(),Utf8.Length(),Hash);Wrong.Sha1=BytesToHex(Hash,FSHA1::DigestSize).ToLower();
            TestTrue(TEXT("negative descriptor is independently valid"),DinkFamilyCollisionFit::ValidatePictureDescriptor(Wrong));
            TestFalse(TEXT("actual cooked dimensions reject valid wrong-axis descriptor"),DinkFamilyCollisionFit::MatchesLegacyPictureImportedSize(Wrong,*Texture));
        }
        auto Material=MakeShared<TStrongObjectPtr<UMaterialInterface>>(MI);auto Image=MakeShared<TStrongObjectPtr<UTexture>>(Texture);
        if(E.Frame==1){Candidate.Sprite.SourcePicture=P;Candidate.SourcePictureMaterial=Material;Candidate.SourcePictureTexture=Image;}
        else {Candidate.ReleasePicture=P;Candidate.ReleaseMaterial=Material;Candidate.ReleaseTexture=Image;}
        auto F=MakeShared<FJsonObject>();F->SetStringField(TEXT("material"),MIPath);F->SetStringField(TEXT("texture"),TexPath);F->SetBoolField(TEXT("package_cooked"),true);F->SetNumberField(TEXT("frame"),E.Frame);F->SetNumberField(TEXT("imported_width"),Observed.X);F->SetNumberField(TEXT("imported_height"),Observed.Y);F->SetNumberField(TEXT("platform_surface_width_diagnostic"),Texture->GetSurfaceWidth());F->SetNumberField(TEXT("platform_surface_height_diagnostic"),Texture->GetSurfaceHeight());F->SetStringField(TEXT("descriptor_sha1"),P.Sha1);Facts.Add(MakeShared<FJsonValueObject>(F));
    }
    FString Error;
    if(!TestTrue(TEXT("actual cooked source/released pair passes production publication asset guard"),DinkFamilyCollisionFit::ValidateReleasedPictureAssets(Candidate,Error))){AddError(Error);return false;}
    auto Wrong=Candidate;Wrong.ReleaseTexture=Candidate.SourcePictureTexture;
    TestFalse(TEXT("actual source texture cannot impersonate released-frame asset"),DinkFamilyCollisionFit::ValidateReleasedPictureAssets(Wrong,Error));
    Wrong=Candidate;Wrong.SourcePictureMaterial=Candidate.ReleaseMaterial;
    TestFalse(TEXT("actual released MIC cannot impersonate immutable source material"),DinkFamilyCollisionFit::ValidateReleasedPictureAssets(Wrong,Error));
    Wrong=Candidate;Wrong.bReleasePicturePrepared=false;
    TestFalse(TEXT("unprepared actual assets cannot pass publication guard"),DinkFamilyCollisionFit::ValidateReleasedPictureAssets(Wrong,Error));
    TestTrue(TEXT("negative candidates never mutate the original actual pair"),DinkFamilyCollisionFit::ValidateReleasedPictureAssets(Candidate,Error));
    auto Receipt=MakeShared<FJsonObject>();Receipt->SetBoolField(TEXT("requires_cooked"),true);Receipt->SetArrayField(TEXT("actual_frames"),Facts);Receipt->SetBoolField(TEXT("production_pair_guard"),true);Receipt->SetStringField(TEXT("scope"),TEXT("Actual cooked asset/ImportedSize proof only; no release lifecycle, pixels, fresh-generation or full-suite acceptance"));
    FString Json;FJsonSerializer::Serialize(Receipt,TJsonWriterFactory<>::Create(&Json));
    IFileManager::Get().MakeDirectory(*Directory,true);
    TestTrue(TEXT("new actual cooked-picture receipt written"),FFileHelper::SaveStringToFile(Json,*Output,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_NoReplaceExisting));
    return true;
}
