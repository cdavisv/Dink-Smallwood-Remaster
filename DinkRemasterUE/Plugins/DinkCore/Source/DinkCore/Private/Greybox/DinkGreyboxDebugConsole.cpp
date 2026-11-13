// Small, observable controls for manual/desktop playtesting. Movement still comes from normal input.
#include "DinkCoreModule.h"
#include "DinkLayout.h"
#include "DinkOriginComponent.h"
#include "EngineUtils.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"

static FAutoConsoleCommandWithWorld GDinkPlayerCommand(
	TEXT("dink.Player"), TEXT("Print the player's world/map position, physical radius, and camera angles for a reproducible playtest."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		APawn* Pawn = PC ? PC->GetPawn() : nullptr;
		UDinkGreyboxSubsystem* Grey = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
		if (!Pawn || !Grey)
		{
			UE_LOG(LogDink, Display, TEXT("DINK PLAYER: no player"));
			return;
		}
		const FVector Position = Pawn->GetActorLocation();
		const ADinkScreenVolume* Screen = Grey->FindScreenAt(Position);
		double MapX = 0.0, MapY = 0.0;
		if (Screen)
		{
			DinkLayout::MetresToMapPixel(Screen->Corners, DinkLayout::UnrealToMetres(Position), MapX, MapY);
		}
		const UCapsuleComponent* Capsule = Pawn->FindComponentByClass<UCapsuleComponent>();
		const FRotator View = PC->GetControlRotation();
		UE_LOG(LogDink, Display, TEXT("DINK PLAYER: screen=%d map=%.3f,%.3f world=%.3f,%.3f,%.3f yaw=%.3f pitch=%.3f radius=%.1f move_ignored=%d"),
			Screen ? Screen->ScreenNumber : 0, MapX, MapY, Position.X, Position.Y, Position.Z,
			View.Yaw, FRotator::NormalizeAxis(View.Pitch), Capsule ? Capsule->GetScaledCapsuleRadius() : 0.f,
			PC->IsMoveInputIgnored() ? 1 : 0);
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkViewCommand(
	TEXT("dink.View"), TEXT("dink.View <yaw> <pitch>: set the normal third-person camera orientation in degrees; does not move the player."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		if (!PC || Args.Num() != 2 || !Args[0].IsNumeric() || !Args[1].IsNumeric())
		{
			UE_LOG(LogDink, Display, TEXT("usage: dink.View <yaw> <pitch>"));
			return;
		}
		PC->SetControlRotation(FRotator(FMath::Clamp(FCString::Atod(*Args[1]), -80.0, 60.0), FCString::Atod(*Args[0]), 0.0));
	}));


static FAutoConsoleCommandWithWorldAndArgs GDinkOriginCommand(
	TEXT("dink.Origin"), TEXT("dink.Origin <S001_P26>: print an original placement's live world/map position for interaction debugging."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		FDinkOriginId Id;
		if (!World || Args.Num() != 1 || !FDinkOriginId::Parse(Args[0], Id))
		{
			UE_LOG(LogDink, Display, TEXT("usage: dink.Origin <S001_P26>"));
			return;
		}
		UDinkGreyboxSubsystem* Grey = World->GetSubsystem<UDinkGreyboxSubsystem>();
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			const UDinkOriginComponent* Origin = UDinkOriginComponent::FindOnActor(*It);
			if (!Origin || !(Origin->OriginId == Id)) continue;
			const FVector Position = It->GetActorLocation();
			const ADinkScreenVolume* Screen = Grey ? Grey->FindScreenAt(Position) : nullptr;
			double MapX = 0.0, MapY = 0.0;
			if (Screen) DinkLayout::MetresToMapPixel(Screen->Corners, DinkLayout::UnrealToMetres(Position), MapX, MapY);
			UE_LOG(LogDink, Display, TEXT("DINK ORIGIN: %s screen=%d map=%.3f,%.3f world=%.3f,%.3f,%.3f hidden=%d"),
				*Id.ToString(), Screen ? Screen->ScreenNumber : 0, MapX, MapY, Position.X, Position.Y, Position.Z, It->IsHidden() ? 1 : 0);
			return;
		}
		UE_LOG(LogDink, Display, TEXT("DINK ORIGIN: %s not found in this map"), *Id.ToString());
	}));

// ---------------------------------------------------------------------------------------------
// dink.CaptureScript <file>: timed console-command runner for rendered lighting review without any
// keyboard input. One instruction per line: `wait <seconds>`, `shot <png path>` (viewport without
// UI), `fps <label>` (average frame rate since the previous instruction), or any console command.
#include "Containers/Ticker.h"
#include "Engine/Engine.h"
#include "Misc/FileHelper.h"
#include "UnrealClient.h"

namespace
{
	struct FDinkCaptureScript
	{
		TArray<FString> Lines;
		int32 Next = 0;
		double WaitUntil = 0.0;
		double MarkTime = 0.0;
		uint64 MarkFrame = 0;
		TWeakObjectPtr<UWorld> World;
	};

	bool TickCaptureScript(TSharedRef<FDinkCaptureScript> S)
	{
		const double Now = FPlatformTime::Seconds();
		while (S->Next < S->Lines.Num())
		{
			if (Now < S->WaitUntil) return true;
			UWorld* World = S->World.Get();
			if (!World) return false;
			FString Line = S->Lines[S->Next++].TrimStartAndEnd();
			if (Line.IsEmpty() || Line.StartsWith(TEXT("#"))) continue;
			FString Rest;
			if (Line.Split(TEXT(" "), nullptr, &Rest) && Line.StartsWith(TEXT("wait ")))
			{
				S->WaitUntil = Now + FCString::Atod(*Rest);
				S->MarkTime = Now;
				S->MarkFrame = GFrameCounter;
				return true;
			}
			if (Line.StartsWith(TEXT("shot ")))
			{
				FScreenshotRequest::RequestScreenshot(Rest.TrimStartAndEnd(), false, false);
				UE_LOG(LogDink, Display, TEXT("DINK CAPTURE: shot %s"), *Rest);
				S->WaitUntil = Now + 0.5;
				return true;
			}
			if (Line.StartsWith(TEXT("fps ")))
			{
				const double Seconds = Now - S->MarkTime;
				const uint64 Frames = GFrameCounter - S->MarkFrame;
				UE_LOG(LogDink, Display, TEXT("DINK CAPTURE: fps %s %.1f (%llu frames in %.2fs)"), *Rest,
					Seconds > 0.0 ? double(Frames) / Seconds : 0.0, Frames, Seconds);
				continue;
			}
			UE_LOG(LogDink, Display, TEXT("DINK CAPTURE: exec %s"), *Line);
			if (GEngine) GEngine->Exec(World, *Line);
		}
		return false;
	}
}

static FAutoConsoleCommandWithWorldAndArgs GDinkCaptureScriptCommand(
	TEXT("dink.CaptureScript"), TEXT("dink.CaptureScript <file>: run timed console commands and viewport screenshots (wait/shot/fps lines)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		TSharedRef<FDinkCaptureScript> S = MakeShared<FDinkCaptureScript>();
		if (!World || Args.Num() != 1 || !FFileHelper::LoadFileToStringArray(S->Lines, *Args[0]))
		{
			UE_LOG(LogDink, Display, TEXT("usage: dink.CaptureScript <file>"));
			return;
		}
		S->World = World;
		S->MarkTime = FPlatformTime::Seconds();
		S->MarkFrame = GFrameCounter;
		FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([S](float) { return TickCaptureScript(S); }));
	}));

// ---------------------------------------------------------------------------------------------
// Lighting review helpers (photoreal pass): live tweaks of the importer's unbound post volume and
// sky light so several candidate values can be captured in one session, and an audit of the
// camera-occluder materials. None of them is used by gameplay.
#include "Components/PostProcessComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/LightComponent.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"

static FAutoConsoleCommandWithWorldAndArgs GDinkEnvPostCommand(
	TEXT("dink.EnvPost"), TEXT("dink.EnvPost <minev|maxev|bias|shadow|highlight|detail|leak|toe|gather|sky|artbias|sunshadow|sunyaw|sunpitch> <value>: live lighting tweak for review captures."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || Args.Num() != 2) return;
		const float V = FCString::Atof(*Args[1]);
		const FString& K = Args[0];
		if (K == TEXT("sky"))
		{
			for (TActorIterator<ASkyLight> It(World); It; ++It) It->GetLightComponent()->SetIntensity(V);
			return;
		}
		if (K == TEXT("sunshadow") || K == TEXT("sunyaw") || K == TEXT("sunpitch"))
		{
			for (TActorIterator<ADirectionalLight> It(World); It; ++It)
			{
				if (K == TEXT("sunshadow")) { It->GetLightComponent()->SetCastShadows(V != 0.f); continue; }
				FRotator R = It->GetActorRotation();
				(K == TEXT("sunyaw") ? R.Yaw : R.Pitch) = V;
				It->SetActorRotation(R);
			}
			return;
		}
		if (K.StartsWith(TEXT("fog")))
		{
			for (TActorIterator<AExponentialHeightFog> It(World); It; ++It)
			{
				UExponentialHeightFogComponent* F = It->GetComponent();
				if (K == TEXT("fogdensity")) F->SetFogDensity(V);
				else if (K == TEXT("fog2")) F->SetSecondFogDensity(V);
				else if (K == TEXT("fogstart")) F->SetStartDistance(V);
				else if (K == TEXT("fogvol")) F->SetVolumetricFog(V != 0.f);
				else if (K == TEXT("fogz")) { It->GetRootComponent()->SetMobility(EComponentMobility::Movable); It->SetActorLocation(FVector(0, 0, V)); }
			}
			return;
		}
		if (K == TEXT("artbias"))
		{
			for (TObjectIterator<UPostProcessComponent> It; It; ++It)
				if (It->GetWorld() == World && It->GetFName() == TEXT("ArtExposure")) It->Settings.AutoExposureBias = V;
			return;
		}
		for (TActorIterator<APostProcessVolume> It(World); It; ++It)
		{
			if (!It->bUnbound) continue;
			FPostProcessSettings& S = It->Settings;
			if (K == TEXT("minev")) { S.bOverride_AutoExposureMinBrightness = true; S.AutoExposureMinBrightness = V; }
			else if (K == TEXT("maxev")) { S.bOverride_AutoExposureMaxBrightness = true; S.AutoExposureMaxBrightness = V; }
			else if (K == TEXT("bias")) { S.bOverride_AutoExposureBias = true; S.AutoExposureBias = V; }
			else if (K == TEXT("shadow")) { S.bOverride_LocalExposureShadowContrastScale = true; S.LocalExposureShadowContrastScale = V; }
			else if (K == TEXT("highlight")) { S.bOverride_LocalExposureHighlightContrastScale = true; S.LocalExposureHighlightContrastScale = V; }
			else if (K == TEXT("detail")) { S.bOverride_LocalExposureDetailStrength = true; S.LocalExposureDetailStrength = V; }
			else if (K == TEXT("leak")) { S.bOverride_LumenSkylightLeaking = true; S.LumenSkylightLeaking = V; }
			else if (K == TEXT("toe")) { S.bOverride_FilmToe = true; S.FilmToe = V; }
			else if (K == TEXT("gather")) { S.bOverride_LumenFinalGatherQuality = true; S.LumenFinalGatherQuality = V; }
		}
	}));

static FAutoConsoleCommandWithWorld GDinkOccluderAuditCommand(
	TEXT("dink.OccluderAudit"), TEXT("Print every camera-occluder mesh of screen 1 with its material paths (for the camera fade mapping)."),
	FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
	{
		if (!World) return;
		for (TActorIterator<AActor> It(World); It; ++It)
		{
			if (!It->ActorHasTag(TEXT("DinkArtScreen_1")) || !It->ActorHasTag(TEXT("DinkCameraOccluder"))) continue;
			TInlineComponentArray<UStaticMeshComponent*> Meshes(*It);
			for (const UStaticMeshComponent* M : Meshes)
			{
				FString Line = FString::Printf(TEXT("DINK OCCLUDER: %s"), M->GetStaticMesh() ? *M->GetStaticMesh()->GetPathName() : TEXT("none"));
				for (int32 Slot = 0; Slot < M->GetNumMaterials(); ++Slot)
					Line += TEXT(" | ") + (M->GetMaterial(Slot) ? M->GetMaterial(Slot)->GetPathName() : FString(TEXT("null")));
				UE_LOG(LogDink, Display, TEXT("%s"), *Line);
			}
		}
	}));

#include "GameFramework/SpringArmComponent.h"

static FAutoConsoleCommandWithWorldAndArgs GDinkCameraDistanceCommand(
	TEXT("dink.CameraDistance"), TEXT("dink.CameraDistance <cm>: review-only camera boom length of the player's third-person camera."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		APawn* Pawn = PC ? PC->GetPawn() : nullptr;
		if (!Pawn || Args.Num() != 1) return;
		if (USpringArmComponent* Boom = Pawn->FindComponentByClass<USpringArmComponent>()) Boom->TargetArmLength = FMath::Clamp(FCString::Atof(*Args[0]), 60.f, 2000.f);
	}));

#include "GameFramework/WorldSettings.h"

static FAutoConsoleCommandWithWorldAndArgs GDinkTimeDilationCommand(
	TEXT("dink.TimeDilation"), TEXT("dink.TimeDilation <0.01..4>: review-only game speed, for frame-by-frame animation captures (Scripts/AnimationQA)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (World && World->IsGameWorld() && Args.Num() == 1)
			World->GetWorldSettings()->SetTimeDilation(FMath::Clamp(FCString::Atof(*Args[0]), .01f, 4.f));
	}));

// ---------------------------------------------------------------------------------------------
// Calibration stage (photoreal pass): put one mesh on the ground near the player and look at it
// through a fixed camera that matches a Blender reference render, and override material
// parameters live so several candidate values fit in one capture session. Review only.
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Components/PrimitiveComponent.h"

namespace
{
	FVector GDinkCalAnchor = FVector::ZeroVector;
	TWeakObjectPtr<ACameraActor> GDinkCalCamera;
	TArray<TWeakObjectPtr<AActor>> GDinkCalActors;
}

static FAutoConsoleCommandWithWorldAndArgs GDinkCalAnchorCommand(
	TEXT("dink.CalAnchor"), TEXT("dink.CalAnchor [dx dy]: calibration origin = the player's ground point plus an offset in cm; removes earlier calibration meshes."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		APawn* Pawn = PC ? PC->GetPawn() : nullptr;
		if (!Pawn) return;
		const UCapsuleComponent* Capsule = Pawn->FindComponentByClass<UCapsuleComponent>();
		GDinkCalAnchor = Pawn->GetActorLocation() - FVector(0, 0, Capsule ? Capsule->GetScaledCapsuleHalfHeight() : 0.f);
		if (Args.Num() >= 2) GDinkCalAnchor += FVector(FCString::Atod(*Args[0]), FCString::Atod(*Args[1]), 0.0);
		for (const TWeakObjectPtr<AActor>& A : GDinkCalActors) if (A.IsValid()) A->Destroy();
		GDinkCalActors.Reset();
		UE_LOG(LogDink, Display, TEXT("DINK CAL: anchor %s"), *GDinkCalAnchor.ToString());
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkCalSpawnCommand(
	TEXT("dink.CalSpawn"), TEXT("dink.CalSpawn <mesh object path> <x> <y> <z> <yaw> <scale>: a mesh without collision at anchor + offset (cm)."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || Args.Num() != 6) return;
		UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Args[0]);
		if (!Mesh) { UE_LOG(LogDink, Display, TEXT("DINK CAL: no mesh %s"), *Args[0]); return; }
		FActorSpawnParameters SP;
		SP.ObjectFlags |= RF_Transient;
		const float Scale = FCString::Atof(*Args[5]);
		AStaticMeshActor* A = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),
			FTransform(FRotator(0.0, FCString::Atod(*Args[4]), 0.0), GDinkCalAnchor + FVector(FCString::Atod(*Args[1]), FCString::Atod(*Args[2]), FCString::Atod(*Args[3])), FVector(Scale)), SP);
		if (!A) return;
		A->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
		A->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		A->GetStaticMeshComponent()->SetStaticMesh(Mesh);
		GDinkCalActors.Add(A);
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkCalCamCommand(
	TEXT("dink.CalCam"), TEXT("dink.CalCam <x y z> <tx ty tz> <hfov> [1]: fixed camera at anchor + offset looking at anchor + target (cm), player hidden unless the eighth argument is 1; dink.CalCam off restores."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		APawn* Pawn = PC ? PC->GetPawn() : nullptr;
		if (!Pawn) return;
		if (Args.Num() != 7 && Args.Num() != 8)
		{
			PC->SetViewTarget(Pawn);
			Pawn->SetActorHiddenInGame(false);
			return;
		}
		double V[7];
		for (int32 I = 0; I < 7; ++I) V[I] = FCString::Atod(*Args[I]);
		const FVector From = GDinkCalAnchor + FVector(V[0], V[1], V[2]);
		const FVector To = GDinkCalAnchor + FVector(V[3], V[4], V[5]);
		ACameraActor* Camera = GDinkCalCamera.Get();
		if (!Camera)
		{
			FActorSpawnParameters SP;
			SP.ObjectFlags |= RF_Transient;
			Camera = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), FTransform(From), SP);
			GDinkCalCamera = Camera;
		}
		if (!Camera) return;
		Camera->GetCameraComponent()->bConstrainAspectRatio = false;
		Camera->GetCameraComponent()->SetFieldOfView(float(V[6]));
		Camera->SetActorLocationAndRotation(From, (To - From).Rotation());
		PC->SetViewTarget(Camera);
		Pawn->SetActorHiddenInGame(Args.Num() != 8 || Args[7] != TEXT("1"));
	}));

static FAutoConsoleCommandWithWorldAndArgs GDinkMatParamCommand(
	TEXT("dink.MatParam"), TEXT("dink.MatParam <material name part> <parameter> <value> [g b]: live scalar (one value) or colour (three) override on every component using a matching material."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		if (!World || (Args.Num() != 3 && Args.Num() != 5)) return;
		int32 Count = 0;
		for (TObjectIterator<UPrimitiveComponent> It; It; ++It)
		{
			if (It->GetWorld() != World) continue;
			for (int32 Slot = 0; Slot < It->GetNumMaterials(); ++Slot)
			{
				UMaterialInterface* M = It->GetMaterial(Slot);
				if (!M) continue;
				bool bMatch = false;
				for (const UMaterialInterface* Walk = M; Walk && !bMatch; )
				{
					bMatch = Walk->GetName().Contains(Args[0]);
					const UMaterialInstance* Instance = Cast<UMaterialInstance>(Walk);
					Walk = Instance ? Instance->Parent.Get() : nullptr;
				}
				if (!bMatch) continue;
				UMaterialInstanceDynamic* Dynamic = Cast<UMaterialInstanceDynamic>(M);
				if (!Dynamic) Dynamic = It->CreateAndSetMaterialInstanceDynamic(Slot);
				if (!Dynamic) continue;
				if (Args.Num() == 3) Dynamic->SetScalarParameterValue(FName(*Args[1]), FCString::Atof(*Args[2]));
				else Dynamic->SetVectorParameterValue(FName(*Args[1]), FLinearColor(FCString::Atof(*Args[2]), FCString::Atof(*Args[3]), FCString::Atof(*Args[4])));
				++Count;
			}
		}
		UE_LOG(LogDink, Display, TEXT("DINK CAL: %s.%s set on %d slots"), *Args[0], *Args[1], Count);
	}));

// Review captures: walk the pawn with ordinary movement input (real collision, real overlaps, so door warps fire
// exactly as for a player) toward a map pixel of the screen it stands on.
static FAutoConsoleCommandWithWorldAndArgs GDinkWalkToCommand(
	TEXT("dink.WalkTo"), TEXT("dink.WalkTo <mapx> <mapy> [seconds]: walk the player by movement input toward a map pixel of the current screen; logs DINK WALK when it arrives, changes screen or times out."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
	{
		UDinkGreyboxSubsystem* Grey = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
		const ADinkScreenVolume* Screen = Grey ? Grey->GetCurrentScreen() : nullptr;
		APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
		if (!Screen || !PC || !PC->GetPawn() || Args.Num() < 2) return;
		const FVector Target = DinkLayout::MapPixelToUnreal(Screen->Corners, FCString::Atod(*Args[0]), FCString::Atod(*Args[1]));
		const int32 StartScreen = Screen->ScreenNumber;
		const double Until = FPlatformTime::Seconds() + (Args.Num() > 2 ? FCString::Atod(*Args[2]) : 8.0);
		TWeakObjectPtr<UWorld> WeakWorld(World);
		UE_LOG(LogDink, Display, TEXT("DINK WALK: from %s toward %s on screen %d"), *PC->GetPawn()->GetActorLocation().ToString(), *Target.ToString(), StartScreen);
		FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([WeakWorld, Target, StartScreen, Until](float)
		{
			UWorld* W = WeakWorld.Get();
			APlayerController* Controller = W ? W->GetFirstPlayerController() : nullptr;
			APawn* Pawn = Controller ? Controller->GetPawn() : nullptr;
			UDinkGreyboxSubsystem* G = W ? W->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
			if (!Pawn || !G) return false;
			const ADinkScreenVolume* Now = G->GetCurrentScreen();
			const FVector To = Target - Pawn->GetActorLocation();
			const TCHAR* Result = nullptr;
			if (Now && Now->ScreenNumber != StartScreen) Result = TEXT("screen changed");
			else if (To.Size2D() < 12.0) Result = TEXT("arrived");
			else if (FPlatformTime::Seconds() > Until) Result = TEXT("timed out (blocked?)");
			if (Result)
			{
				UE_LOG(LogDink, Display, TEXT("DINK WALK: %s; now on screen %d at %s, %.0f cm from the target"), Result, Now ? Now->ScreenNumber : -1, *Pawn->GetActorLocation().ToString(), To.Size2D());
				return false;
			}
			Pawn->AddMovementInput(To.GetSafeNormal2D(), 1.f);
			return true;
		}));
	}));
