#include "DinkMaterialArtLibrary.h"
#include "Engine/Texture2D.h"
#include "Misc/Base64.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

FString UDinkMaterialArtLibrary::InspectTextureSourcePixels(UTexture2D* Texture)
{
    const TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("schema"),TEXT("dink-texture-source-pixels/1"));
    Root->SetBoolField(TEXT("valid"),false);
    auto Finish = [&Root](const TCHAR* Error = nullptr)
    {
        if (Error) Root->SetStringField(TEXT("error"),Error);
        FString Text; FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Text)); return Text;
    };
    if (!Texture) return Finish(TEXT("null_texture"));
    const bool DirtyBefore = Texture->GetOutermost()->IsDirty();
    const FGuid SourceBefore = Texture->Source.GetId();
    if (Texture->Source.GetNumBlocks()!=1 || Texture->Source.GetNumLayers()!=1 || Texture->Source.GetNumSlices()!=1
        || Texture->Source.GetNumMips()<1) return Finish(TEXT("unsupported_source_layout"));
    const int64 Width=Texture->Source.GetSizeX(),Height=Texture->Source.GetSizeY();
    if (Width<1 || Height<1 || Width>8192 || Height>8192) return Finish(TEXT("unsupported_source_dimensions"));
    FString Format; int32 BytesPerPixel=0;
    switch (Texture->Source.GetFormat())
    {
    case TSF_BGRA8: Format=TEXT("BGRA8"); BytesPerPixel=4; break;
    case TSF_RGBA16: Format=TEXT("RGBA16"); BytesPerPixel=8; break;
    case TSF_RGBA16F: Format=TEXT("RGBA16F"); BytesPerPixel=8; break;
    case TSF_RGBA32F: Format=TEXT("RGBA32F"); BytesPerPixel=16; break;
    default: return Finish(TEXT("unsupported_source_format"));
    }
#if !PLATFORM_LITTLE_ENDIAN
    return Finish(TEXT("unsupported_byte_order"));
#endif
    TArray64<uint8> Bytes;
    if (!Texture->Source.GetMipData(Bytes,0) || Bytes.Num()!=Width*Height*BytesPerPixel
        || Bytes.Num()>256LL*1024*1024) return Finish(TEXT("source_mip_read_failed"));
    if (Texture->GetOutermost()->IsDirty()!=DirtyBefore || Texture->Source.GetId()!=SourceBefore)
        return Finish(TEXT("source_state_changed"));
    Root->SetStringField(TEXT("texture"),Texture->GetPathName());
    Root->SetNumberField(TEXT("width"),Width); Root->SetNumberField(TEXT("height"),Height);
    Root->SetStringField(TEXT("format"),Format); Root->SetBoolField(TEXT("texture_srgb"),Texture->SRGB);
    FString Gamma;
    switch (Texture->Source.GetGammaSpace(0))
    {
    case EGammaSpace::Linear: Gamma=TEXT("Linear"); break;
    case EGammaSpace::sRGB: Gamma=TEXT("sRGB"); break;
    case EGammaSpace::Pow22: Gamma=TEXT("Pow22"); break;
    default: return Finish(TEXT("unsupported_source_gamma"));
    }
    Root->SetStringField(TEXT("source_gamma"),Gamma);
    // GetGammaSpace intentionally does not account for these build overrides.
    Root->SetBoolField(TEXT("source_encoding_override_none"),Texture->SourceColorSettings.EncodingOverride==ETextureSourceEncoding::TSE_None);
    Root->SetBoolField(TEXT("source_color_space_none"),Texture->SourceColorSettings.ColorSpace==ETextureColorSpace::TCS_None);
    Root->SetStringField(TEXT("row_origin"),TEXT("top_left"));
    Root->SetStringField(TEXT("byte_order"),TEXT("little"));
    Root->SetNumberField(TEXT("byte_count"),Bytes.Num());
    Root->SetStringField(TEXT("source_id"),SourceBefore.ToString());
    Root->SetNumberField(TEXT("platform_format_id"),static_cast<int32>(Texture->GetPixelFormat()));
    Root->SetStringField(TEXT("base64"),FBase64::Encode(Bytes.GetData(),static_cast<uint32>(Bytes.Num())));
    Root->SetBoolField(TEXT("valid"),true);
    Root->SetBoolField(TEXT("gpu_pixels_read"),false);
    return Finish();
}

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkTextureSourcePixelInspectionTest,
    "Dink.Art.TextureSourcePixelInspection",EAutomationTestFlags::EditorContext|EAutomationTestFlags::ProductFilter)
bool FDinkTextureSourcePixelInspectionTest::RunTest(const FString& Parameters)
{
    auto Parse=[](const FString& Text)
    {
        TSharedPtr<FJsonObject> Data; FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Data); return Data;
    };
    const auto Null=Parse(UDinkMaterialArtLibrary::InspectTextureSourcePixels(nullptr));
    if (!TestTrue(TEXT("Null rejected"),Null.IsValid()&&!Null->GetBoolField(TEXT("valid")))) return false;
    UTexture2D* Texture=NewObject<UTexture2D>(GetTransientPackage(),NAME_None,RF_Transient);
    const TArray<uint8> Pixels{3,2,1,255,30,20,10,128};
    Texture->Source.Init(2,1,1,1,TSF_BGRA8,Pixels.GetData()); Texture->SRGB=true;
    const bool Dirty=Texture->GetOutermost()->IsDirty(); const FGuid ID=Texture->Source.GetId();
    const auto Result=Parse(UDinkMaterialArtLibrary::InspectTextureSourcePixels(Texture));
    if (!TestTrue(TEXT("Actual scratch mip read"),Result.IsValid()&&Result->GetBoolField(TEXT("valid")))) return false;
    TArray<uint8> Decoded; const bool DecodedOK=FBase64::Decode(Result->GetStringField(TEXT("base64")),Decoded);
    TestTrue(TEXT("All source bytes exact"),DecodedOK&&Decoded==Pixels);
    TestEqual(TEXT("Reader retains source ID"),Texture->Source.GetId(),ID);
    TestEqual(TEXT("Reader retains dirty state"),Texture->GetOutermost()->IsDirty(),Dirty);
    TestFalse(TEXT("Source mip is not a GPU read"),Result->GetBoolField(TEXT("gpu_pixels_read")));
    return true;
}
#endif
