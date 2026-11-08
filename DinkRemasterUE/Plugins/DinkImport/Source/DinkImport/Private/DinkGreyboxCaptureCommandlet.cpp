#include "DinkGreyboxCaptureCommandlet.h"
#include "DinkGreyboxImporter.h"
#include "DinkImportBundle.h"
#include "DinkImportLog.h"
#include "DinkLayout.h"
#include "AssetCompilingManager.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/SceneCapture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "HAL/FileManager.h"
#include "ImageUtils.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "RenderingThread.h"
#include "ShaderCompiler.h"
#include "TextureResource.h"

UDinkGreyboxCaptureCommandlet::UDinkGreyboxCaptureCommandlet()
{
	IsClient = false;
	IsEditor = true;
	IsServer = false;
	LogToConsole = true;
}

namespace
{
	bool Capture(UWorld* World, const FString& File, const FVector& Location, const FRotator& Rotation, bool bOrtho, float OrthoWidth,
		int32 Width, int32 Height, float Fov)
	{
		UTextureRenderTarget2D* RT = NewObject<UTextureRenderTarget2D>(GetTransientPackage());
		RT->RenderTargetFormat = RTF_RGBA8_SRGB;
		RT->ClearColor = FLinearColor::Red;  // red = the capture never drew
		RT->bAutoGenerateMips = false;
		RT->InitAutoFormat(Width, Height);
		RT->UpdateResourceImmediate(true);

		FActorSpawnParameters P;
		P.ObjectFlags = RF_Transient;
		ASceneCapture2D* Cam = World->SpawnActor<ASceneCapture2D>(ASceneCapture2D::StaticClass(), Location, Rotation, P);
		USceneCaptureComponent2D* C = Cam->GetCaptureComponent2D();
		C->ProjectionType = bOrtho ? ECameraProjectionMode::Orthographic : ECameraProjectionMode::Perspective;
		C->OrthoWidth = OrthoWidth;
		C->FOVAngle = Fov;
		C->TextureTarget = RT;
		C->CaptureSource = FParse::Param(FCommandLine::Get(), TEXT("FinalColor")) ? ESceneCaptureSource::SCS_FinalColorLDR : ESceneCaptureSource::SCS_BaseColor;
		C->bCaptureEveryFrame = false;
		C->bCaptureOnMovement = false;
		C->ShowFlags.SetFog(!bOrtho);
		C->ShowFlags.SetAtmosphere(!bOrtho);
		for (int32 I = 0; I < 3; ++I)
		{
			// a few passes so auto exposure and temporal effects settle
			C->CaptureScene();
			FlushRenderingCommands();
		}
		TArray<FColor> Pixels;
		FTextureRenderTargetResource* Res = RT->GameThread_GetRenderTargetResource();
		const bool bRead = Res && Res->ReadPixels(Pixels);
		Cam->Destroy();
		int64 Lit = 0, Red = 0;
		for (const FColor& Px : Pixels)
		{
			Lit += (Px.R + Px.G + Px.B) > 30 ? 1 : 0;
			Red += (Px.R > 200 && Px.G < 30 && Px.B < 30) ? 1 : 0;
		}
		UE_LOG(LogDinkImport, Display, TEXT("capture: %s: %lld of %d pixels non-dark, %lld clear-red"), *File, Lit, Pixels.Num(), Red);
		if (bRead && Red == Pixels.Num())
		{
			// verified 6 Nov 2026: in a -run= commandlet with -AllowCommandletRendering the Vulkan RHI
			// starts and shaders compile, but CaptureScene never draws into the target
			UE_LOG(LogDinkImport, Error, TEXT("capture: nothing was rendered into %s (target still at its clear colour)"), *File);
			return false;
		}
		if (!bRead || Pixels.Num() != Width * Height)
		{
			UE_LOG(LogDinkImport, Error, TEXT("capture: could not read pixels for %s"), *File);
			return false;
		}
		for (FColor& Px : Pixels)
		{
			Px.A = 255;
		}
		TArray64<uint8> Png;
		FImageUtils::PNGCompressImageArray(Width, Height, TArrayView64<const FColor>(Pixels.GetData(), Pixels.Num()), Png);
		const bool bSaved = FFileHelper::SaveArrayToFile(Png, *File);
		UE_LOG(LogDinkImport, Display, TEXT("capture: %s %s"), *File, bSaved ? TEXT("written") : TEXT("FAILED"));
		return bSaved;
	}
}

int32 UDinkGreyboxCaptureCommandlet::Main(const FString& Params)
{
	FString Region = TEXT("stonebrook");
	FString Out = FPaths::ProjectSavedDir() / TEXT("Import/Captures");
	FParse::Value(*Params, TEXT("Region="), Region);
	FParse::Value(*Params, TEXT("Out="), Out);
	IFileManager::Get().MakeDirectory(*Out, true);

	FDinkBundle Bundle;
	FString Error;
	if (!Bundle.Load(FDinkBundle::DefaultDir(), Error))
	{
		UE_LOG(LogDinkImport, Display, TEXT("DINK CAPTURE FAILED: %s"), *Error);
		return 1;
	}
	const FString Map = FDinkGreyboxImporter::MapPackageFor(Region);
	UWorld* World = UEditorLoadingAndSavingUtils::LoadMap(FPackageName::LongPackageNameToFilename(Map, FPackageName::GetMapPackageExtension()));
	if (!World)
	{
		UE_LOG(LogDinkImport, Display, TEXT("DINK CAPTURE FAILED: cannot load %s"), *Map);
		return 1;
	}
	const double T0 = FPlatformTime::Seconds();
	FAssetCompilingManager::Get().FinishAllCompilation();
	if (GShaderCompilingManager)
	{
		GShaderCompilingManager->FinishAllCompilation();
	}
	UE_LOG(LogDinkImport, Display, TEXT("capture: assets and shaders ready after %.1f s"), FPlatformTime::Seconds() - T0);

	// bounds of the region's outdoor screens on the main sheet of the region
	FBox2D Box(ForceInit);
	TArray<const FDinkBundleScreen*> Outdoor;
	for (const FDinkBundleScreen& S : Bundle.Screens)
	{
		if ((Region == TEXT("all") ? S.Group == TEXT("mainland") : S.Region == Region) && !S.bIndoor && S.Excluded.IsEmpty())
		{
			Box += S.Corners.NW;
			Box += S.Corners.NE;
			Box += S.Corners.SW;
			Box += S.Corners.SE;
			Outdoor.Add(&S);
		}
	}
	int32 Written = 0;
	if (Box.bIsValid)
	{
		const FVector2D Size = Box.GetSize();
		const int32 W = 2048;
		const int32 H = FMath::Clamp(int32(W * Size.Y / Size.X), 256, 4096);
		// looking straight down, north (-Y) at the top of the image
		Written += Capture(World, Out / (Region + TEXT("_top.png")), DinkLayout::MetresToUnreal(Box.GetCenter(), 400.0), FRotator(-90.0, -90.0, 0.0),
			true, float(Size.X * 100.0), W, H, 90.f) ? 1 : 0;
	}
	// eye-level views: the start, and the screens of the region whose centres are nearest the
	// region centre (settlement first), looking north
	TArray<FVector> Eyes;
	Eyes.Add(DinkLayout::MetresToUnreal(Bundle.StartWorld, 1.7));
	Outdoor.Sort([&](const FDinkBundleScreen& A, const FDinkBundleScreen& B)
	{
		if ((A.Kind == TEXT("settlement")) != (B.Kind == TEXT("settlement")))
		{
			return A.Kind == TEXT("settlement");
		}
		return (DinkLayout::MapPixelToMetres(A.Corners, 300, 200) - Box.GetCenter()).SizeSquared() <
			(DinkLayout::MapPixelToMetres(B.Corners, 300, 200) - Box.GetCenter()).SizeSquared();
	});
	for (int32 I = 0; I < FMath::Min(3, Outdoor.Num()); ++I)
	{
		Eyes.Add(DinkLayout::MapPixelToUnreal(Outdoor[I]->Corners, 300, 380, 1.7));
	}
	for (int32 I = 0; I < Eyes.Num(); ++I)
	{
		Written += Capture(World, Out / FString::Printf(TEXT("%s_eye_%d.png"), *Region, I), Eyes[I], FRotator(-8.0, -90.0, 0.0), false, 0.f, 1600, 900, 75.f) ? 1 : 0;
	}
	UE_LOG(LogDinkImport, Display, TEXT("DINK CAPTURE %s: %d images in %s"), Written > 0 ? TEXT("OK") : TEXT("FAILED"), Written, *Out);
	return Written > 0 ? 0 : 1;
}
