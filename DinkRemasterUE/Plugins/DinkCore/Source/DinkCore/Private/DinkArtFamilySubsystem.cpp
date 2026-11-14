#include "DinkArtFamilySubsystem.h"
#include "DinkCoreModule.h"
#include "DinkEnvironmentSubsystem.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/Crc.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

const FName UDinkArtFamilySubsystem::FamilyTag(TEXT("DinkFamilyArt"));
const FName UDinkArtFamilySubsystem::ScriptSpriteTag(TEXT("DinkScriptFamilyArt"));

namespace
{
	TAutoConsoleVariable<int32> CVarDinkFamilyArt(TEXT("dink.FamilyArt"), 1,
		TEXT("Dress greybox placements by sprite family from Data/Art/families.json at screen activation (0: keep the cards). Read at play start."));

	const TCHAR* FamiliesSchema = TEXT("dink-art-families/1");
	const TCHAR* FamiliesFile = TEXT("families.json");

	FString ArtDirectory()
	{
		return FPaths::ProjectContentDir() / TEXT("Dink/Data/Art");
	}

	/** "/Game/A/B/SM_X" -> "/Game/A/B/SM_X.SM_X"; an explicit object name is kept. */
	FString NormaliseObjectPath(const FString& Path)
	{
		FString Package = Path, Object;
		if (Path.Split(TEXT("."), &Package, &Object, ESearchCase::CaseSensitive, ESearchDir::FromEnd) && !Object.IsEmpty() && !Object.Contains(TEXT("/")))
		{
			return Path;
		}
		return Path + TEXT(".") + FPaths::GetBaseFilename(Path);
	}

	void AddOriginStrings(const TArray<TSharedPtr<FJsonValue>>& Values, TSet<FString>& Out)
	{
		for (const TSharedPtr<FJsonValue>& Value : Values)
		{
			FString Origin;
			if (Value.IsValid() && Value->TryGetString(Origin) && !Origin.IsEmpty()) Out.Add(Origin);
		}
	}

	void AddOriginRows(const FJsonObject& Manifest, const TCHAR* Field, TSet<FString>& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
		if (!Manifest.TryGetArrayField(Field, Rows)) return;
		for (const TSharedPtr<FJsonValue>& Value : *Rows)
		{
			const TSharedPtr<FJsonObject>* Row = nullptr;
			FString Origin;
			if (Value.IsValid() && Value->TryGetObject(Row) && Row && (*Row)->TryGetStringField(TEXT("origin"), Origin) && !Origin.IsEmpty()) Out.Add(Origin);
		}
	}

	void AddScreens(const FJsonObject& Manifest, const TCHAR* Field, TSet<int32>& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		if (!Manifest.TryGetArrayField(Field, Values)) return;
		for (const TSharedPtr<FJsonValue>& Value : *Values)
		{
			double Number = 0;
			if (Value.IsValid() && Value->TryGetNumber(Number)) Out.Add(int32(Number));
		}
	}

	bool ArtEnabled()
	{
		// Codex's art switch (DinkArtSubsystem): a greybox comparison turns family art off too.
		const IConsoleVariable* Art = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));
		return !Art || Art->GetInt() != 0;
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Pure rules (unit tested without a world)

FString DinkArtFamily::DefaultFamiliesPath()
{
	return ArtDirectory() / FamiliesFile;
}

void FDinkFamilyPrecedence::AddManifest(const FJsonObject& Manifest)
{
	FString Schema;
	if (!Manifest.TryGetStringField(TEXT("schema"), Schema)) return;
	if (Schema == TEXT("dink-art/1"))
	{
		AddOriginRows(Manifest, TEXT("replacements"), Origins);
		AddOriginRows(Manifest, TEXT("warp_overrides"), Origins);
		const TArray<TSharedPtr<FJsonValue>>* Hidden = nullptr;
		if (Manifest.TryGetArrayField(TEXT("hide_origins"), Hidden)) AddOriginStrings(*Hidden, Origins);
		// hide_origins_by_vision: {"1": [ids], "2": [ids]} (or a plain list).
		const TSharedPtr<FJsonObject>* ByVision = nullptr;
		if (Manifest.TryGetObjectField(TEXT("hide_origins_by_vision"), ByVision) && ByVision)
		{
			for (const auto& Pair : (*ByVision)->Values)
			{
				const TArray<TSharedPtr<FJsonValue>>* Ids = nullptr;
				if (Pair.Value.IsValid() && Pair.Value->TryGetArray(Ids)) AddOriginStrings(*Ids, Origins);
			}
		}
		else if (Manifest.TryGetArrayField(TEXT("hide_origins_by_vision"), Hidden))
		{
			AddOriginStrings(*Hidden, Origins);
		}
		AddScreens(Manifest, TEXT("hide_screen_visuals"), Screens);
		AddScreens(Manifest, TEXT("authored_collision_screens"), Screens);
		// A manifest that spawns authored elements (render-only context included) owns its screen's look.
		const TArray<TSharedPtr<FJsonValue>>* Elements = nullptr;
		double Screen = 0;
		if (Manifest.TryGetArrayField(TEXT("elements"), Elements) && Elements->Num() > 0 && Manifest.TryGetNumberField(TEXT("screen"), Screen))
		{
			Screens.Add(int32(Screen));
		}
	}
	else if (Schema == TEXT("dink-creatures/1") || Schema == TEXT("dink-characters/1"))
	{
		AddOriginRows(Manifest, TEXT("placements"), Origins);
	}
}

FDinkFamilyPrecedence FDinkFamilyPrecedence::LoadDirectory(const FString& Directory, const FString& SkipFile)
{
	FDinkFamilyPrecedence Result;
	TArray<FString> Files;
	IFileManager::Get().FindFiles(Files, *(Directory / TEXT("*.json")), true, false);
	Files.Sort();
	for (const FString& File : Files)
	{
		if (File.Equals(SkipFile, ESearchCase::IgnoreCase)) continue;
		FString Text;
		TSharedPtr<FJsonObject> Manifest;
		if (FFileHelper::LoadFileToString(Text, *(Directory / File)) && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) && Manifest.IsValid())
		{
			Result.AddManifest(*Manifest);
		}
	}
	return Result;
}

bool DinkArtFamily::ParseFamilies(const FString& Json, TArray<FDinkFamilyBinding>& Out, TArray<FString>& Errors)
{
	Out.Reset();
	TSharedPtr<FJsonObject> Root;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid())
	{
		Errors.Add(TEXT("families.json is not valid JSON"));
		return false;
	}
	FString Schema;
	if (!Root->TryGetStringField(TEXT("schema"), Schema) || Schema != FamiliesSchema)
	{
		Errors.Add(FString::Printf(TEXT("families.json schema must be %s"), FamiliesSchema));
		return false;
	}
	const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
	if (!Root->TryGetArrayField(TEXT("families"), Rows))
	{
		Errors.Add(TEXT("families.json has no families list"));
		return false;
	}
	TSet<FString> Seen;
	for (int32 Index = 0; Index < Rows->Num(); ++Index)
	{
		const TSharedPtr<FJsonObject>* Row = nullptr;
		if (!(*Rows)[Index].IsValid() || !(*Rows)[Index]->TryGetObject(Row) || !Row)
		{
			Errors.Add(FString::Printf(TEXT("row %d is not an object"), Index));
			continue;
		}
		FDinkFamilyBinding B;
		FString Fit = TEXT("none");  // real size by default; footprint/height are opt-in
		if (!(*Row)->TryGetStringField(TEXT("family"), B.Family) || B.Family.TrimStartAndEnd().IsEmpty())
		{
			Errors.Add(FString::Printf(TEXT("row %d has no family"), Index));
			continue;
		}
		B.Family = B.Family.TrimStartAndEnd();
		if (!(*Row)->TryGetStringField(TEXT("mesh"), B.Mesh) || !B.Mesh.StartsWith(TEXT("/Game/")))
		{
			Errors.Add(FString::Printf(TEXT("%s: mesh must be a /Game/ object path"), *B.Family));
			continue;
		}
		B.Mesh = NormaliseObjectPath(B.Mesh);
		{
			const TArray<TSharedPtr<FJsonValue>>* VariantRows = nullptr;
			bool bBadVariant = false;
			if ((*Row)->TryGetArrayField(TEXT("variants"), VariantRows) && VariantRows)
			{
				for (const TSharedPtr<FJsonValue>& V : *VariantRows)
				{
					FString Path;
					if (!V.IsValid() || !V->TryGetString(Path) || !Path.StartsWith(TEXT("/Game/"))) { bBadVariant = true; break; }
					B.Variants.Add(NormaliseObjectPath(Path));
				}
			}
			if (bBadVariant)
			{
				Errors.Add(FString::Printf(TEXT("%s: variants must be /Game/ object paths"), *B.Family));
				continue;
			}
		}
		(*Row)->TryGetStringField(TEXT("fit"), Fit);
		if (Fit == TEXT("footprint")) B.Fit = EDinkFamilyFit::Footprint;
		else if (Fit == TEXT("height")) B.Fit = EDinkFamilyFit::Height;
		else if (Fit == TEXT("none")) B.Fit = EDinkFamilyFit::None;
		else
		{
			Errors.Add(FString::Printf(TEXT("%s: fit must be footprint, height or none"), *B.Family));
			continue;
		}
		(*Row)->TryGetBoolField(TEXT("yaw_from_sprite"), B.bYawFromSprite);
		(*Row)->TryGetBoolField(TEXT("scripted"), B.bScripted);
		(*Row)->TryGetNumberField(TEXT("yaw_offset"), B.YawOffset);
		if ((*Row)->TryGetNumberField(TEXT("scale"), B.Scale) && (B.Scale < DinkArtFamily::MinScale || B.Scale > DinkArtFamily::MaxScale))
		{
			Errors.Add(FString::Printf(TEXT("%s: scale %g is outside %g..%g"), *B.Family, B.Scale, double(DinkArtFamily::MinScale), double(DinkArtFamily::MaxScale)));
			continue;
		}
		(*Row)->TryGetNumberField(TEXT("anchor_front"), B.AnchorFront);
		{
			FString Span, End;
			if ((*Row)->TryGetStringField(TEXT("span"), Span)) B.Span = Span == TEXT("width") ? 1 : Span == TEXT("height") ? 2 : Span == TEXT("stretch") ? 3 : 0;
			if ((*Row)->TryGetStringField(TEXT("span_fill"), B.SpanFill) && B.SpanFill.StartsWith(TEXT("/Game/"))) B.SpanFill = NormaliseObjectPath(B.SpanFill); else B.SpanFill.Reset();
			if ((*Row)->TryGetStringField(TEXT("span_end"), End)) B.SpanEnd = End == TEXT("left") ? -1 : End == TEXT("right") ? 1 : 0;
		}
		B.AnchorFront = FMath::Clamp(B.AnchorFront, 0.0, 1.0);
		(*Row)->TryGetStringField(TEXT("note"), B.Note);
		double FrameNumber = 0.0;
		const bool bHasFrame = (*Row)->TryGetNumberField(TEXT("frame"), FrameNumber);
		if (FChar::IsDigit(B.Family[0]))
		{
			int32 End = 0;
			while (End < B.Family.Len() && FChar::IsDigit(B.Family[End])) ++End;
			B.Sequence = FCString::Atoi(*B.Family.Left(End));
		}
		else
		{
			B.ClassId = FName(*B.Family);
		}
		if (bHasFrame)
		{
			if (B.Sequence == INDEX_NONE || FrameNumber < 1.0)
			{
				Errors.Add(FString::Printf(TEXT("%s: frame needs a sequence family (leading number) and a frame of 1 or more"), *B.Family));
				continue;
			}
			B.Frame = int32(FrameNumber);
		}
		const FString Key = B.Sequence != INDEX_NONE ? FString::Printf(TEXT("seq %d frame %d"), B.Sequence, B.Frame) : B.ClassId.ToString().ToLower();
		if (Seen.Contains(Key))
		{
			Errors.Add(FString::Printf(TEXT("%s: bound twice"), *B.Family));
			continue;
		}
		Seen.Add(Key);
		Out.Add(MoveTemp(B));
	}
	return Errors.IsEmpty();
}

const FDinkFamilyBinding* DinkArtFamily::Resolve(const TArray<FDinkFamilyBinding>& Bindings, int32 Sequence, FName ClassId, int32 Frame)
{
	if (Frame > 0)
	{
		for (const FDinkFamilyBinding& B : Bindings)
		{
			if (B.Frame == Frame && B.Sequence != INDEX_NONE && B.Sequence == Sequence) return &B;
		}
	}
	if (!ClassId.IsNone())
	{
		for (const FDinkFamilyBinding& B : Bindings)
		{
			if (!B.ClassId.IsNone() && B.ClassId == ClassId) return &B;
		}
	}
	for (const FDinkFamilyBinding& B : Bindings)
	{
		if (B.Frame == 0 && B.Sequence != INDEX_NONE && B.Sequence == Sequence) return &B;
	}
	return nullptr;
}

EDinkFamilyDecision DinkArtFamily::Decide(const FDinkFamilyPlacement& P, const FDinkFamilyPrecedence& Precedence,
	const TArray<FDinkFamilyBinding>& Bindings, const FDinkFamilyBinding*& OutBinding)
{
	OutBinding = nullptr;
	if (P.bHardnessOnly) return EDinkFamilyDecision::HardnessOnly;
	if (Precedence.Screens.Contains(P.Screen)) return EDinkFamilyDecision::ScreenDressed;
	if (Precedence.Origins.Contains(P.Origin)) return EDinkFamilyDecision::OriginHandled;
	const FDinkFamilyBinding* B = Resolve(Bindings, P.Sequence, P.ClassId, P.Frame);
	if (!B) return EDinkFamilyDecision::NoBinding;
	if (P.bScripted && !B->bScripted) return EDinkFamilyDecision::Scripted;
	OutBinding = B;
	return EDinkFamilyDecision::Bound;
}

float DinkArtFamily::FitScale(EDinkFamilyFit Fit, double SpriteWidthCm, double SpriteHeightCm, const FVector& MeshSizeCm, bool bYawFromSprite)
{
	constexpr double Tiny = 0.01;
	const double Width = bYawFromSprite ? MeshSizeCm.X : FMath::Max(MeshSizeCm.X, MeshSizeCm.Y);
	const double Height = MeshSizeCm.Z;
	double Scale = 1.0;
	switch (Fit)
	{
	case EDinkFamilyFit::None:
		return 1.f;
	case EDinkFamilyFit::Height:
		if (Height > Tiny && SpriteHeightCm > Tiny) Scale = SpriteHeightCm / Height;
		break;
	case EDinkFamilyFit::Footprint:
	{
		const bool bW = Width > Tiny && SpriteWidthCm > Tiny;
		const bool bH = Height > Tiny && SpriteHeightCm > Tiny;
		if (bW && bH) Scale = FMath::Min(SpriteWidthCm / Width, SpriteHeightCm / Height);
		else if (bW) Scale = SpriteWidthCm / Width;
		else if (bH) Scale = SpriteHeightCm / Height;
		break;
	}
	}
	return float(FMath::Clamp(Scale, double(MinScale), double(MaxScale)));
}

FTransform DinkArtFamily::MeshTransform(const FBox& MeshBounds, const FVector& Ground, double YawDegrees, float Scale)
{
	const FQuat Rotation = FRotator(0.0, YawDegrees, 0.0).Quaternion();
	const FVector Anchor(MeshBounds.GetCenter().X, MeshBounds.GetCenter().Y, MeshBounds.Min.Z);
	return FTransform(Rotation, Ground - Rotation.RotateVector(Anchor * double(Scale)), FVector(Scale));
}

void DinkArtFamily::SpanPieces(const FDinkFamilyBinding& Binding, double SpanCm, double ModuleCm, TArray<FSpanPiece>& Out)
{
	Out.Reset();
	if (Binding.Span == 0 || SpanCm <= 1.0 || ModuleCm <= 1.0)
	{
		Out.AddDefaulted();
		return;
	}
	const int32 Count = Binding.Span == 3 ? 1 : FMath::Clamp(FMath::RoundToInt32(SpanCm / ModuleCm), 1, 16);
	const double Length = SpanCm / Count;
	for (int32 Index = 0; Index < Count; ++Index)
	{
		FSpanPiece& Piece = Out.AddDefaulted_GetRef();
		Piece.OffsetCm = (Index + 0.5 - Count * 0.5) * Length;
		Piece.LengthCm = Length;
		// the main mesh (a corner post, a free end) stands at its end of the run; plain modules fill the rest
		const bool bMainHere = Binding.SpanEnd == 0 || (Binding.SpanEnd < 0 && Index == 0) || (Binding.SpanEnd > 0 && Index == Count - 1);
		Piece.bFill = !Binding.SpanFill.IsEmpty() && !bMainHere;
	}
}

FTransform DinkArtFamily::SpanTransform(const FBox& MeshBounds, const FVector& Ground, double YawDegrees, float Scale, const FSpanPiece& Piece)
{
	if (Piece.LengthCm <= 0.0) return MeshTransform(MeshBounds, Ground, YawDegrees, Scale);
	const FQuat Rotation = FRotator(0.0, YawDegrees, 0.0).Quaternion();
	const double Along = Piece.LengthCm / FMath::Max(MeshBounds.GetSize().X * double(Scale), 1.0);
	const FVector Anchor(MeshBounds.GetCenter().X * Scale * Along, MeshBounds.GetCenter().Y * Scale, MeshBounds.Min.Z * Scale);
	return FTransform(Rotation, Ground + Rotation.RotateVector(FVector(Piece.OffsetCm, 0.0, 0.0) - Anchor), FVector(Scale * Along, Scale, Scale));
}

double DinkArtFamily::StableYaw(const FString& Origin)
{
	return double(FCrc::StrCrc32(*Origin) % 360u);
}

int32 DinkArtFamily::StableVariant(const FString& Origin, int32 Count)
{
	return Count > 1 ? int32((FCrc::StrCrc32(*Origin, 0x5EED1E57u) >> 8) % uint32(Count)) : 0;
}

double DinkArtFamily::DepthAfterYaw(const FVector& MeshSizeCm, double YawDegrees, float Scale)
{
	const double Radians = FMath::DegreesToRadians(YawDegrees);
	return (FMath::Abs(FMath::Sin(Radians)) * MeshSizeCm.X + FMath::Abs(FMath::Cos(Radians)) * MeshSizeCm.Y) * double(Scale);
}

const TCHAR* DinkArtFamily::DecisionName(EDinkFamilyDecision Decision)
{
	switch (Decision)
	{
	case EDinkFamilyDecision::Bound: return TEXT("bound");
	case EDinkFamilyDecision::HardnessOnly: return TEXT("hardness-only");
	case EDinkFamilyDecision::ScreenDressed: return TEXT("screen dressed by an art manifest");
	case EDinkFamilyDecision::OriginHandled: return TEXT("origin bound by an art manifest");
	case EDinkFamilyDecision::NoBinding: return TEXT("no family binding");
	case EDinkFamilyDecision::Scripted: return TEXT("scripted");
	}
	return TEXT("?");
}

// ---------------------------------------------------------------------------------------------------------------------
// Runtime

bool UDinkArtFamilySubsystem::DoesSupportWorldType(EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

UStaticMeshComponent* UDinkArtFamilySubsystem::MakeUnpublishedReleasedVisual(ADinkPlaceholderActor& Actor,UStaticMesh& Mesh)
{
    // Same render-only policy as DressActor, but no owner/registration/publication yet.
    // A transient outer prevents abandoned prepared candidates entering the actor component inventory.
    auto* Child=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None);
    Child->SetMobility(EComponentMobility::Movable);Child->SetupAttachment(Actor.GetRootComponent());
    Child->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);Child->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Child->SetCanEverAffectNavigation(false);Child->SetGenerateOverlapEvents(false);
    Child->ComponentTags.Add(TEXT("DinkReleasedFamilyVisual"));
    Child->SetVisibility(false);Child->SetHiddenInGame(true);Child->SetStaticMesh(&Mesh);
    for(int32 I=0;I<Mesh.GetStaticMaterials().Num();++I)Child->SetMaterial(I,Mesh.GetMaterial(I));
    return Child;
}

bool UDinkArtFamilySubsystem::LoadCollisionFitPolicy(const FString& File,FString& Text,FString& Error)
{
    // An unreadable file is not a successfully loaded legacy policy. Clear any
    // previous rows before attempting a read so failure cannot retain old fits.
    bCollisionFitPolicyError=true;
    CollisionFitRules.Reset();ReleasedVisualBinding={};Text.Reset();Error.Reset();
    if(!FFileHelper::LoadFileToString(Text,*File))
    {Error=TEXT("mandatory family policy unavailable: ")+File;return false;}
    bCollisionFitPolicyError=!DinkFamilyCollisionFit::ParsePolicy(Text,CollisionFitRules,Error)||
        !DinkFamilyCollisionFit::ParseReleasedVisual(Text,ReleasedVisualBinding,Error);
    return !bCollisionFitPolicyError;
}

void UDinkArtFamilySubsystem::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);
    FString Text,CollisionFitError;
    // Collision authority is independent of whether optional family graphics
    // are enabled. A marked world must never silently substitute old hardboxes.
    if(!LoadCollisionFitPolicy(DinkArtFamily::DefaultFamiliesPath(),Text,CollisionFitError))
        UE_LOG(LogDink,Warning,TEXT("Family collision fit policy refused: %s"),*CollisionFitError);
    if (!CVarDinkFamilyArt.GetValueOnGameThread() || !ArtEnabled()) return;
    if(Text.IsEmpty())return;
    TArray<FString> Errors;
    DinkArtFamily::ParseFamilies(Text, Bindings, Errors);
	for (const FString& Error : Errors) UE_LOG(LogDink, Warning, TEXT("Family art: %s"), *Error);
	if (Bindings.IsEmpty()) return;
	// No greybox screens (a test or an unrelated map): nothing to dress.
	bool bHasGreybox = false;
	for (TActorIterator<ADinkGreyboxScreen> It(&World); It && !bHasGreybox; ++It) bHasGreybox = true;
	if (!bHasGreybox) return;
	Precedence = FDinkFamilyPrecedence::LoadDirectory(ArtDirectory(), FamiliesFile);
	// Load every bound mesh once, now, so a screen change never waits on a package load.
	for (const FDinkFamilyBinding& B : Bindings)
	{
		MeshFor(B);
		for (const FString& Variant : B.Variants) LoadFamilyMesh(Variant, B.Family);
		if (!B.SpanFill.IsEmpty()) LoadFamilyMesh(B.SpanFill, B.Family);
	}
	bReady = true;
	if (UDinkGreyboxSubsystem* Grey = World.GetSubsystem<UDinkGreyboxSubsystem>())
	{
		Greybox = Grey;
		ScreenHandle = Grey->OnScreenChanged.AddUObject(this, &UDinkArtFamilySubsystem::ScreenChanged);
		if (ADinkScreenVolume* Current = Grey->GetCurrentScreen()) ScreenChanged(Current);
	}
	UE_LOG(LogDink, Display, TEXT("DINK FAMILY ART READY: %d family bindings, %d meshes, %d origins and %d screens left to the art manifests"),
		Bindings.Num(), Meshes.Num(), Precedence.Origins.Num(), Precedence.Screens.Num());
}

void UDinkArtFamilySubsystem::Deinitialize()
{
	if (UDinkGreyboxSubsystem* Grey = Greybox.Get()) Grey->OnScreenChanged.Remove(ScreenHandle);
	ScreenHandle.Reset();
	Super::Deinitialize();
}

void UDinkArtFamilySubsystem::ScreenChanged(ADinkScreenVolume* Screen)
{
	if (Screen) ApplyScreen(Screen->ScreenNumber);
}

void UDinkArtFamilySubsystem::BuildIndex(UWorld& World)
{
	bIndexed = true;
	for (TActorIterator<ADinkPlaceholderActor> It(&World); It; ++It) ActorsByScreen.FindOrAdd(It->ScreenNumber).Add(*It);
	for (TActorIterator<ADinkGreyboxScreen> It(&World); It; ++It) GreyboxByScreen.FindOrAdd(It->ScreenNumber).Add(*It);
	// Which class each sprite picture belongs to: sprites that scripts create name only a sequence and a frame.
	auto Learn = [this](int32 Sequence, int32 Frame, FName ClassId)
	{
		if (Sequence <= 0 || Frame <= 0 || Frame > 0xffff || ClassId.IsNone()) return;
		ClassByPicture.Add(Sequence << 16 | Frame, ClassId);
		FName& Whole = ClassByPicture.FindOrAdd(Sequence << 16, ClassId);
		if (Whole != ClassId) Whole = NAME_None;
	};
	for (TActorIterator<ADinkPlaceholderActor> It(&World); It; ++It)
		if (It->Origin) Learn(It->Origin->Sequence, It->Origin->Frame, It->Origin->ClassId);
	for (TActorIterator<ADinkGreyboxScreen> It(&World); It; ++It)
		if (It->InstanceOrigins)
			for (const FDinkInstanceOrigin& Origin : It->InstanceOrigins->Origins) Learn(Origin.Sequence, Origin.Frame, Origin.ClassId);
}

FName UDinkArtFamilySubsystem::ClassOfPicture(int32 Sequence, int32 Frame) const
{
	if (Sequence <= 0 || Frame < 0 || Frame > 0xffff) return NAME_None;
	const FName* Found = ClassByPicture.Find(Sequence << 16 | Frame);
	return Found ? *Found : NAME_None;
}

bool UDinkArtFamilySubsystem::DressScriptSprite(AActor* Actor, int32 Sequence, int32 Frame, const FVector& GroundOffset, float Size)
{
	UWorld* World = GetWorld();
	if (!Actor || !World || !Actor->GetRootComponent()) return false;
	UStaticMeshComponent* Shown = Actor->FindComponentByTag<UStaticMeshComponent>(ScriptSpriteTag);
	// Script characters, creatures and food are presented by their own layers.
	const bool bOtherLayer = Actor->ActorHasTag(TEXT("DinkAuthoredArt")) || Actor->ActorHasTag(TEXT("DinkHumanoid")) ||
		Actor->ActorHasTag(TEXT("DinkScriptHumanoid")) || Actor->ActorHasTag(TEXT("DinkCreature")) ||
		Actor->FindComponentByTag<UStaticMeshComponent>(TEXT("DinkAuthoredFood")) != nullptr;
	const FDinkFamilyBinding* B = nullptr;
	UStaticMesh* Mesh = nullptr;
	const FVector Ground = Actor->GetActorLocation() + GroundOffset;
	// No origin ID: the spot stands in for it, so heaps dropped side by side differ in variant and yaw, the same every run.
	const FString Key = FString::Printf(TEXT("script:%d:%d:%d:%d"), Sequence, Frame, FMath::RoundToInt(Ground.X), FMath::RoundToInt(Ground.Y));
	if (bReady && !bOtherLayer && Sequence > 0)
	{
		if (!bIndexed) BuildIndex(*World);
		B = DinkArtFamily::Resolve(Bindings, Sequence, ClassOfPicture(Sequence, Frame), Frame);
		Mesh = B ? MeshFor(*B, Key) : nullptr;
	}
	UStaticMeshComponent* Marker = Cast<UStaticMeshComponent>(Actor->GetRootComponent());
	if (!Mesh)
	{
		if (Shown)
		{
			Shown->DestroyComponent();
			if (Marker && !bOtherLayer) Marker->SetHiddenInGame(false);
		}
		return false;
	}
	if (Shown && Shown->GetStaticMesh() != Mesh)
	{
		Shown->DestroyComponent();
		Shown = nullptr;
	}
	if (!Shown)
	{
		Shown = NewObject<UStaticMeshComponent>(Actor, TEXT("ScriptFamilyArt"));
		Shown->SetMobility(EComponentMobility::Movable);
		Shown->SetupAttachment(Actor->GetRootComponent());
		// The marker root is scaled (0.3, 0.3, 0.6, or sp_size): the mesh keeps its own size and turn.
		Shown->SetUsingAbsoluteRotation(true);
		Shown->SetUsingAbsoluteScale(true);
		Shown->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
		Shown->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Shown->SetCanEverAffectNavigation(false);
		Shown->SetGenerateOverlapEvents(false);
		Shown->ComponentTags.Add(FamilyTag);
		Shown->ComponentTags.Add(ScriptSpriteTag);
		Shown->SetStaticMesh(Mesh);
		Actor->AddInstanceComponent(Shown);
		Shown->RegisterComponent();
	}
	const double Yaw = (B->bYawFromSprite ? 0.0 : DinkArtFamily::StableYaw(Key)) + B->YawOffset;
	Shown->SetWorldTransform(DinkArtFamily::MeshTransform(Mesh->GetBoundingBox(), Ground, Yaw, FMath::Max(Size * float(B->Scale), DinkArtFamily::MinScale)));
	if (Marker) Marker->SetHiddenInGame(true);
	return true;
}

UStaticMesh* UDinkArtFamilySubsystem::LoadFamilyMesh(const FString& Path, const FString& Family)
{
	if (const TObjectPtr<UStaticMesh>* Found = Meshes.Find(Path)) return *Found;
	if (MissingMeshes.Contains(Path)) return nullptr;
	UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!Mesh)
	{
		MissingMeshes.Add(Path);
		UE_LOG(LogDink, Warning, TEXT("Family art: missing mesh %s for %s; its placements keep their cards"), *Path, *Family);
		return nullptr;
	}
	Meshes.Add(Path, Mesh);
	return Mesh;
}

UStaticMesh* UDinkArtFamilySubsystem::MeshFor(const FDinkFamilyBinding& Binding)
{
	return LoadFamilyMesh(Binding.Mesh, Binding.Family);
}

UStaticMesh* UDinkArtFamilySubsystem::MeshFor(const FDinkFamilyBinding& Binding, const FString& Origin)
{
	UStaticMesh* Main = MeshFor(Binding);
	if (!Main || Binding.Variants.IsEmpty()) return Main;
	const int32 Pick = DinkArtFamily::StableVariant(Origin, Binding.Variants.Num() + 1);
	UStaticMesh* Variant = Pick == 0 ? Main : LoadFamilyMesh(Binding.Variants[Pick - 1], Binding.Family);
	return Variant ? Variant : Main;
}

int32 UDinkArtFamilySubsystem::ApplyScreen(int32 ScreenNumber)
{
	UWorld* World = GetWorld();
	if (!bReady || !World || AppliedScreens.Contains(ScreenNumber)) return 0;
	AppliedScreens.Add(ScreenNumber);
	if (!bIndexed) BuildIndex(*World);
	int32 Count = 0;
	if (const TArray<TWeakObjectPtr<ADinkPlaceholderActor>>* Actors = ActorsByScreen.Find(ScreenNumber))
	{
		for (const TWeakObjectPtr<ADinkPlaceholderActor>& Actor : *Actors)
		{
			if (Actor.IsValid() && DressActor(*Actor.Get())) ++Count;
		}
	}
	if (const TArray<TWeakObjectPtr<ADinkGreyboxScreen>>* Screens = GreyboxByScreen.Find(ScreenNumber))
	{
		for (const TWeakObjectPtr<ADinkGreyboxScreen>& Screen : *Screens)
		{
			if (Screen.IsValid()) Count += DressInstances(*Screen.Get());
		}
	}
	Dressed += Count;
	UE_LOG(LogDink, Log, TEXT("Family art: screen %d, %d placements dressed (%d in all)"), ScreenNumber, Count, Dressed);
	return Count;
}

bool UDinkArtFamilySubsystem::DressActor(ADinkPlaceholderActor& Actor)
{
	UStaticMeshComponent* Card = Actor.Card;
	if (!Actor.Origin || !Card || !Card->GetStaticMesh() || !Actor.GetRootComponent()) return false;
	// Whatever the art runtime already took over at play start, whatever this layer dressed before.
	if (Actor.ActorHasTag(FamilyTag) || Actor.ActorHasTag(TEXT("DinkAuthoredArt")) || Actor.ActorHasTag(TEXT("DinkHumanoid")) ||
		Actor.ActorHasTag(TEXT("DinkCreature")) || Card->bHiddenInGame)
	{
		return false;
	}
	FDinkFamilyPlacement P;
	P.Origin = Actor.Origin->OriginId.ToString();
	P.Screen = Actor.ScreenNumber;
	P.Sequence = Actor.Origin->Sequence;
	P.Frame = Actor.Origin->Frame;
	P.ClassId = Actor.Origin->ClassId;
	P.bScripted = !Actor.Origin->ScriptName.IsNone();
	P.bHardnessOnly = Actor.PlacementKind == TEXT("hardness_only");
	const FDinkFamilyBinding* B = nullptr;
	const EDinkFamilyDecision Decision = DinkArtFamily::Decide(P, Precedence, Bindings, B);
	DecisionCounts.FindOrAdd(Decision)++;
	UStaticMesh* Mesh = B ? MeshFor(*B, P.Origin) : nullptr;
	if (!Mesh) return false;

	// The card is the sprite at its imported size: relative scale (width, 1, height) in metres of a 1 m unit card.
	const FVector CardLocation = Card->GetRelativeLocation();
	const FVector CardScale = Card->GetRelativeScale3D();
	const float Scale = float(B->Scale) * DinkArtFamily::FitScale(B->Fit, CardScale.X * 100.0, CardScale.Z * 100.0, Mesh->GetBoundingBox().GetSize(), B->bYawFromSprite);
	const double Yaw = (B->bYawFromSprite ? 0.0 : DinkArtFamily::StableYaw(P.Origin)) + B->YawOffset;

	// +Y is south, towards the original camera: a front-anchored mesh moves back by half its depth
	const double Back = B->AnchorFront * 0.5 * DinkArtFamily::DepthAfterYaw(Mesh->GetBoundingBox().GetSize(), Yaw, Scale);
	// a spanning module (interior wall runs) is repeated along its run until it fills the layout-scaled card
	TArray<DinkArtFamily::FSpanPiece> Pieces;
	DinkArtFamily::SpanPieces(*B, (B->Span == 2 ? CardScale.Z : CardScale.X) * 100.0, Mesh->GetBoundingBox().GetSize().X * Scale, Pieces);
	UStaticMeshComponent* Component = nullptr;
	for (int32 Index = 0; Index < Pieces.Num(); ++Index)
	{
		UStaticMesh* PieceMesh = Pieces[Index].bFill ? LoadFamilyMesh(B->SpanFill, B->Family) : Index == 0 ? Mesh : MeshFor(*B, P.Origin + FString::Printf(TEXT("#%d"), Index));
		if (!PieceMesh) PieceMesh = Mesh;
		UStaticMeshComponent* Part = NewObject<UStaticMeshComponent>(&Actor, Index == 0 ? FName(TEXT("FamilyArt")) : FName(*FString::Printf(TEXT("FamilyArt_%d"), Index)));
		Part->SetMobility(EComponentMobility::Movable);
		Part->SetupAttachment(Actor.GetRootComponent());
		Part->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
		Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Part->SetCanEverAffectNavigation(false);
		Part->SetGenerateOverlapEvents(false);
		Part->ComponentTags.Add(FamilyTag);
		Part->SetStaticMesh(PieceMesh);
		Part->SetRelativeTransform(DinkArtFamily::SpanTransform(PieceMesh->GetBoundingBox(), FVector(CardLocation.X, CardLocation.Y - Back, 0.0), Yaw, Scale, Pieces[Index]));
		Actor.AddInstanceComponent(Part);
		Part->RegisterComponent();
		if (!Component) Component = Part;
	}
	// Trunk feet blend toward the soil under them (bark materials read custom primitive data 0-2; rendering only).
	if (UDinkEnvironmentSubsystem* Env = Actor.GetWorld() ? Actor.GetWorld()->GetSubsystem<UDinkEnvironmentSubsystem>() : nullptr)
	{
		FLinearColor Soil;
		if (Env->GroundColourAt(FVector2D(Component->GetComponentLocation()), Soil)) Component->SetCustomPrimitiveDataVector3(0, FVector(Soil.R, Soil.G, Soil.B));
	}
	Card->SetHiddenInGame(true);
	Actor.Tags.AddUnique(FamilyTag);
	return true;
}

int32 UDinkArtFamilySubsystem::DressInstances(ADinkGreyboxScreen& Screen)
{
	if (!Screen.InstanceOrigins || Screen.ActorHasTag(TEXT("DinkAuthoredArt")) || !Screen.GetRootComponent()) return 0;
	TMap<FName, TArray<const FDinkInstanceOrigin*>> ByComponent;
	for (const FDinkInstanceOrigin& Origin : Screen.InstanceOrigins->Origins) ByComponent.FindOrAdd(Origin.ComponentName).Add(&Origin);
	TInlineComponentArray<UInstancedStaticMeshComponent*> Components(&Screen);
	int32 Count = 0;
	for (const auto& Pair : ByComponent)
	{
		UInstancedStaticMeshComponent* Decor = nullptr;
		for (UInstancedStaticMeshComponent* C : Components) if (C->GetFName() == Pair.Key) Decor = C;
		if (!Decor || Decor->bHiddenInGame) continue;
		// One decor component draws one sprite frame, so its instances share a binding; any exception keeps the whole
		// component (hiding single instances would mean editing the greybox's instance data).
		const FDinkFamilyBinding* Shared = nullptr;
		bool bAll = true;
		for (const FDinkInstanceOrigin* O : Pair.Value)
		{
			FDinkFamilyPlacement P;
			P.Origin = O->OriginId.ToString();
			P.Screen = Screen.ScreenNumber;
			P.Sequence = O->Sequence;
			P.Frame = O->Frame;
			P.ClassId = O->ClassId;
			P.bScripted = !O->ScriptName.IsNone();
			const FDinkFamilyBinding* B = nullptr;
			const EDinkFamilyDecision Decision = DinkArtFamily::Decide(P, Precedence, Bindings, B);
			DecisionCounts.FindOrAdd(Decision)++;
			if (!B || (Shared && B != Shared)) bAll = false;
			Shared = B;
		}
		if (!bAll || !Shared || !MeshFor(*Shared)) continue;
		// One instanced component per variant mesh; each instance goes to the variant its origin ID selects.
		TMap<UStaticMesh*, UInstancedStaticMeshComponent*> ByMesh;
		for (const FDinkInstanceOrigin* O : Pair.Value)
		{
			FTransform Card;
			if (!Decor->GetInstanceTransform(O->InstanceIndex, Card, /*bWorldSpace*/ false)) continue;
			UStaticMesh* MainMesh = MeshFor(*Shared, O->OriginId.ToString());
			if (!MainMesh) continue;
			TArray<DinkArtFamily::FSpanPiece> Pieces;
			{
				const float MainScale = float(Shared->Scale) * DinkArtFamily::FitScale(Shared->Fit, Card.GetScale3D().X * 100.0, Card.GetScale3D().Z * 100.0, MainMesh->GetBoundingBox().GetSize(), Shared->bYawFromSprite);
				DinkArtFamily::SpanPieces(*Shared, (Shared->Span == 2 ? Card.GetScale3D().Z : Card.GetScale3D().X) * 100.0, MainMesh->GetBoundingBox().GetSize().X * MainScale, Pieces);
			}
			for (int32 PieceIndex = 0; PieceIndex < Pieces.Num(); ++PieceIndex)
			{
			UStaticMesh* Mesh = Pieces[PieceIndex].bFill ? LoadFamilyMesh(Shared->SpanFill, Shared->Family) : PieceIndex == 0 ? MainMesh : MeshFor(*Shared, O->OriginId.ToString() + FString::Printf(TEXT("#%d"), PieceIndex));
			if (!Mesh) Mesh = MainMesh;
			UInstancedStaticMeshComponent*& Family = ByMesh.FindOrAdd(Mesh);
			if (!Family)
			{
				Family = NewObject<UInstancedStaticMeshComponent>(&Screen, FName(*FString::Printf(TEXT("FamilyArt_%s_%d"), *Pair.Key.ToString(), ByMesh.Num() - 1)));
				Family->SetMobility(EComponentMobility::Movable);
				Family->SetupAttachment(Screen.GetRootComponent());
				Family->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
				Family->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				Family->SetCanEverAffectNavigation(false);
				Family->SetGenerateOverlapEvents(false);
				Family->ComponentTags.Add(FamilyTag);
				Family->SetStaticMesh(Mesh);
				Screen.AddInstanceComponent(Family);
				Family->RegisterComponent();
			}
			const FBox Bounds = Mesh->GetBoundingBox();
			// Instance = card relative to the screen root: placement yaw, card centre, scale (width, 1, height) in metres.
			const FVector At = Card.GetLocation();
			const float Scale = float(Shared->Scale) * DinkArtFamily::FitScale(Shared->Fit, Card.GetScale3D().X * 100.0, Card.GetScale3D().Z * 100.0, Bounds.GetSize(), Shared->bYawFromSprite);
			const double Yaw = Card.Rotator().Yaw + (Shared->bYawFromSprite ? 0.0 : DinkArtFamily::StableYaw(O->OriginId.ToString())) + Shared->YawOffset;
			// The greybox ground is world Z 0; the screen root sits on it.
			const double Back = Shared->AnchorFront * 0.5 * DinkArtFamily::DepthAfterYaw(Bounds.GetSize(), Yaw - Card.Rotator().Yaw, Scale);
			const FVector Ground = FVector(At.X, At.Y, -Screen.GetActorLocation().Z) - FRotator(0.0, Card.Rotator().Yaw, 0.0).RotateVector(FVector(0.0, Back, 0.0));
			Family->AddInstance(DinkArtFamily::SpanTransform(Bounds, Ground, Yaw, Scale, Pieces[PieceIndex]), /*bWorldSpace*/ false);
			}
			++Count;
		}
		// One soil colour per instanced component (the mean under its instances): trunk feet blend toward it.
		if (UDinkEnvironmentSubsystem* Env = Screen.GetWorld() ? Screen.GetWorld()->GetSubsystem<UDinkEnvironmentSubsystem>() : nullptr)
		{
			for (const auto& Made : ByMesh)
			{
				FLinearColor Sum(0, 0, 0, 0);
				int32 Hits = 0;
				for (int32 Index = 0; Index < Made.Value->GetInstanceCount(); ++Index)
				{
					FTransform At;
					FLinearColor Soil;
					if (Made.Value->GetInstanceTransform(Index, At, /*bWorldSpace*/ true) && Env->GroundColourAt(FVector2D(At.GetLocation()), Soil)) { Sum += Soil; ++Hits; }
				}
				if (Hits > 0) Made.Value->SetCustomPrimitiveDataVector3(0, FVector(Sum.R, Sum.G, Sum.B) / double(Hits));
			}
		}
		Decor->SetHiddenInGame(true);
		Screen.Tags.AddUnique(FamilyTag);
	}
	return Count;
}
