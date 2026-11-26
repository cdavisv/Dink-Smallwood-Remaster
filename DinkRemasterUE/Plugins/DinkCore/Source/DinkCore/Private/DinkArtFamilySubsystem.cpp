#include "DinkArtFamilySubsystem.h"
#include "DinkPerfScope.h"
#include "Components/DecalComponent.h"
#include "Components/MaterialBillboardComponent.h"
#include "Components/PointLightComponent.h"
#include "DinkFlickerLightComponent.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "RHIShaderPlatform.h"
#include "Misc/App.h"
#include "DinkCoreModule.h"
#include "DinkCreatureClassComponent.h"
#include "DinkEnvironmentSubsystem.h"
#include "DinkLandforms.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "DinkPlayerBlockers.h"
#include "DinkFamilyDuplicates.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Engine/CollisionProfile.h"
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
const FName UDinkArtFamilySubsystem::ScriptEffectTag(TEXT("DinkScriptFamilyEffect"));
const FName UDinkArtFamilySubsystem::ScriptPictureTag(TEXT("DinkScriptPictureCard"));

TArray<TWeakObjectPtr<UStaticMeshComponent>>& UDinkArtFamilySubsystem::ScriptPictureCards()
{
	static TArray<TWeakObjectPtr<UStaticMeshComponent>> Cards;
	return Cards;
}

namespace
{
	/** Data/Art/sprite_pictures.json, read once: key -> pixel width, height, origin x, origin y. */
	const TMap<FString, FIntVector4>& DinkSpritePictureTable()
	{
		static TMap<FString, FIntVector4> Pictures;
		static bool bLoaded = false;
		if (!bLoaded)
		{
			bLoaded = true;
			FString Text;
			TSharedPtr<FJsonObject> Root;
			const FString Path = FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/sprite_pictures.json");
			if (FFileHelper::LoadFileToString(Text, *Path) && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) && Root)
			{
				const TSharedPtr<FJsonObject>* Rows = nullptr;
				if (Root->TryGetObjectField(TEXT("pictures"), Rows) && Rows)
				{
					for (const auto& Pair : (*Rows)->Values)
					{
						const TArray<TSharedPtr<FJsonValue>>* V = nullptr;
						if (Pair.Value->TryGetArray(V) && V && V->Num() == 4)
							Pictures.Add(FString(Pair.Key.ToView()), FIntVector4(int32((*V)[0]->AsNumber()), int32((*V)[1]->AsNumber()), int32((*V)[2]->AsNumber()), int32((*V)[3]->AsNumber())));
					}
				}
			}
			if (Pictures.IsEmpty()) UE_LOG(LogDink, Warning, TEXT("Script sprites: no picture sizes in %s; pictures without a mesh keep the marker"), *Path);
		}
		return Pictures;
	}

	TMap<int32, FString>& DinkInitSequencePictures()
	{
		static TMap<int32, FString> Map;
		return Map;
	}

	/** The picture key a script sprite of Sequence shows at Frame: the init file's frame when an init line replaced the sequence. */
	FString ScriptPictureKey(int32 Sequence, int32 Frame)
	{
		const FString* Init = DinkInitSequencePictures().Find(Sequence);
		return Init ? FString::Printf(TEXT("%s_%02d"), **Init, Frame) : FString::Printf(TEXT("%d_%02d"), Sequence, Frame);
	}
}

bool UDinkArtFamilySubsystem::PictureInfo(int32 Sequence, int32 Frame, FIntVector4& Out)
{
	return PictureInfoForKey(FString::Printf(TEXT("%d_%02d"), Sequence, Frame), Out);
}

bool UDinkArtFamilySubsystem::PictureInfoForKey(const FString& Key, FIntVector4& Out)
{
	if (const FIntVector4* Found = DinkSpritePictureTable().Find(Key))
	{
		Out = *Found;
		return true;
	}
	return false;
}

bool UDinkArtFamilySubsystem::RegisterInitSequencePicture(const FString& Line)
{
	TArray<FString> W;
	Line.ParseIntoArrayWS(W);
	if (W.Num() < 3 || !(W[0].Equals(TEXT("load_sequence_now"), ESearchCase::IgnoreCase) || W[0].Equals(TEXT("load_sequence"), ESearchCase::IgnoreCase)))
		return false;
	const int32 Seq = FCString::Atoi(*W[2]);
	FString Path = W[1].Replace(TEXT("\\"), TEXT("/")).ToLower();
	if (Seq <= 0 || !W[2].IsNumeric() || Path.StartsWith(TEXT("graphics/dink/"))) return false;
	FString File;
	if (!Path.Split(TEXT("/"), nullptr, &File, ESearchCase::CaseSensitive, ESearchDir::FromEnd)) File = Path;
	FString Stem;
	for (const TCHAR C : File)
		if (FChar::IsAlnum(C)) Stem.AppendChar(C);
	if (Stem.IsEmpty()) return false;
	DinkInitSequencePictures().Add(Seq, TEXT("init_") + Stem);
	return true;
}

void UDinkArtFamilySubsystem::ClearInitSequencePictures()
{
	DinkInitSequencePictures().Reset();
}

FString UDinkArtFamilySubsystem::InitSequencePicture(int32 Sequence)
{
	const FString* Found = DinkInitSequencePictures().Find(Sequence);
	return Found ? *Found : FString();
}

namespace
{
	/** The 1997 picture of a script sprite on a camera-facing card (SM_DinkCard: 1 m square, bottom-centre pivot, face +Y). */
	bool ShowScriptPictureCard(AActor* Actor, int32 Sequence, int32 Frame, const FVector& Ground, float Size)
	{
		FIntVector4 Pic;
		const int32 Shown = FMath::Max(1, Frame);
		const FString Key = ScriptPictureKey(Sequence, Shown);
		if (Sequence <= 0 || !UDinkArtFamilySubsystem::PictureInfoForKey(Key, Pic) || Pic.X <= 0 || Pic.Y <= 0) return false;
		UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr,
			*FString::Printf(TEXT("/Game/Dink/_Generated/Sprites/MI_Sprite_%s.MI_Sprite_%s"), *Key, *Key), nullptr, LOAD_NoWarn | LOAD_Quiet);
		static TWeakObjectPtr<UStaticMesh> CardMesh;
		if (!CardMesh.IsValid())
			CardMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Dink/_Generated/Shared/SM_DinkCard.SM_DinkCard"), nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (!Material || !CardMesh.IsValid()) return false;
		UStaticMeshComponent* Card = Actor->FindComponentByTag<UStaticMeshComponent>(UDinkArtFamilySubsystem::ScriptPictureTag);
		if (!Card)
		{
			Card = NewObject<UStaticMeshComponent>(Actor, TEXT("ScriptPictureCard"));
			Card->SetMobility(EComponentMobility::Movable);
			Card->SetupAttachment(Actor->GetRootComponent());
			Card->SetUsingAbsoluteRotation(true);
			Card->SetUsingAbsoluteScale(true);
			Card->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
			Card->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Card->SetCanEverAffectNavigation(false);
			Card->SetGenerateOverlapEvents(false);
			Card->ComponentTags.Add(UDinkArtFamilySubsystem::ScriptPictureTag);
			Card->SetStaticMesh(CardMesh.Get());
			Actor->AddInstanceComponent(Card);
			Card->RegisterComponent();
			UDinkArtFamilySubsystem::ScriptPictureCards().Add(Card);
		}
		Card->SetMaterial(0, Material);
		Card->SetHiddenInGame(false);
		// True size, as the importer's "base" cards of characters and loose items: 0.025 m per 1997 pixel times sp_size.
		const double Cm = 2.5 * FMath::Max(double(Size), 0.05);
		const FRotator Facing = Card->GetComponentRotation();
		const FVector Right = FRotationMatrix(Facing).GetUnitAxis(EAxis::X);
		// The picture's origin pixel stands on the ground point; the card's pivot is its bottom centre.
		Card->SetWorldScale3D(FVector(Pic.X * Cm / 100.0, 1.0, Pic.Y * Cm / 100.0));
		Card->SetWorldLocation(Ground + Right * ((Pic.X * 0.5 - Pic.Z) * Cm) - FVector(0.0, 0.0, (Pic.Y - Pic.W) * Cm));
		return true;
	}

	/** Removes a script sprite's picture card; true when there was one. */
	bool RemoveScriptPictureCard(AActor* Actor)
	{
		UStaticMeshComponent* Card = Actor ? Actor->FindComponentByTag<UStaticMeshComponent>(UDinkArtFamilySubsystem::ScriptPictureTag) : nullptr;
		if (!Card) return false;
		UDinkArtFamilySubsystem::ScriptPictureCards().Remove(Card);
		Card->DestroyComponent();
		return true;
	}
}

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
	else if (Schema.StartsWith(TEXT("dink-town-houses/")))
	{
		// A structure set that says so (structure_sets.json, "families_yield": true) owns the placements its sets stand for: a fence
		// sprite laid as a run of modules must not get the family layer's single fence module as well. town_houses.json does not set it.
		bool bYield = false;
		const TSharedPtr<FJsonObject>* ScreensObject = nullptr;
		if (!Manifest.TryGetBoolField(TEXT("families_yield"), bYield) || !bYield || !Manifest.TryGetObjectField(TEXT("screens"), ScreensObject) || !ScreensObject) return;
		for (const auto& Pair : (*ScreensObject)->Values)
		{
			const TSharedPtr<FJsonObject>* Row = nullptr;
			const TSharedPtr<FJsonObject>* Stands = nullptr;
			if (!Pair.Value.IsValid() || !Pair.Value->TryGetObject(Row) || !Row || !(*Row)->TryGetObjectField(TEXT("stands_for"), Stands) || !Stands) continue;
			for (const auto& Origin : (*Stands)->Values) Origins.Add(FString(Origin.Key.ToView()));
		}
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
		if ((*Row)->TryGetStringField(TEXT("effect"), B.Effect) && B.Effect.StartsWith(TEXT("/Game/")) && !(*Row)->HasField(TEXT("mesh")))
		{
			B.Effect = NormaliseObjectPath(B.Effect);
			(*Row)->TryGetNumberField(TEXT("effect_size_cm"), B.EffectSizeCm);
			B.EffectSizeCm = FMath::Clamp(B.EffectSizeCm, 1.0, 1000.0);
			const TArray<TSharedPtr<FJsonValue>>* CardOffset = nullptr;
			if ((*Row)->TryGetArrayField(TEXT("effect_offset_cm"), CardOffset) && CardOffset && CardOffset->Num() == 3)
			{
				B.EffectOffsetCm = FVector(FMath::Clamp((*CardOffset)[0]->AsNumber(), -1000.0, 1000.0), FMath::Clamp((*CardOffset)[1]->AsNumber(), -1000.0, 1000.0), FMath::Clamp((*CardOffset)[2]->AsNumber(), -1000.0, 1000.0));
			}
			(*Row)->TryGetBoolField(TEXT("effect_placed"), B.bEffectPlaced);
			const TArray<TSharedPtr<FJsonValue>>* FitRow = nullptr;
			if ((*Row)->TryGetArrayField(TEXT("effect_fit"), FitRow) && FitRow && FitRow->Num() == 2)
			{
				B.EffectFit = FVector2D(FMath::Clamp((*FitRow)[0]->AsNumber(), 0.05, 1.0), FMath::Clamp((*FitRow)[1]->AsNumber(), 0.05, 1.0));
			}
			(*Row)->TryGetBoolField(TEXT("effect_ground"), B.bEffectGround);
			(*Row)->TryGetNumberField(TEXT("effect_sink"), B.EffectSink);
			B.EffectSink = FMath::Clamp(B.EffectSink, 0.0, 0.5);
			(*Row)->TryGetNumberField(TEXT("effect_light_height"), B.EffectLightHeight);
			B.EffectLightHeight = FMath::Clamp(B.EffectLightHeight, 0.0, 2.0);
			(*Row)->TryGetNumberField(TEXT("effect_light_flicker"), B.EffectLightFlicker);
			B.EffectLightFlicker = FMath::Clamp(B.EffectLightFlicker, 0.0, 0.9);
			const TArray<TSharedPtr<FJsonValue>>* Light = nullptr;
			if ((*Row)->TryGetArrayField(TEXT("effect_light"), Light) && Light && Light->Num() == 5)
			{
				B.EffectLight = FLinearColor(float((*Light)[0]->AsNumber()), float((*Light)[1]->AsNumber()), float((*Light)[2]->AsNumber()));
				B.EffectLightCandela = FMath::Clamp((*Light)[3]->AsNumber(), 0.0, 100000.0);
				B.EffectLightRadiusCm = FMath::Clamp((*Light)[4]->AsNumber(), 0.0, 5000.0);
			}
			const TSharedPtr<FJsonObject>* Plume = nullptr;
			if ((*Row)->TryGetObjectField(TEXT("effect_plume"), Plume) && Plume && Plume->IsValid())
			{
				FString Material;
				const TArray<TSharedPtr<FJsonValue>>* Size = nullptr;
				const TArray<TSharedPtr<FJsonValue>>* Origins = nullptr;
				if ((*Plume)->TryGetStringField(TEXT("material"), Material) && Material.StartsWith(TEXT("/Game/")) &&
					(*Plume)->TryGetArrayField(TEXT("size_cm"), Size) && Size && Size->Num() == 2)
				{
					B.EffectPlume = NormaliseObjectPath(Material);
					B.EffectPlumeSizeCm = FVector2D(FMath::Clamp((*Size)[0]->AsNumber(), 10.0, 3000.0), FMath::Clamp((*Size)[1]->AsNumber(), 10.0, 3000.0));
					if ((*Plume)->TryGetArrayField(TEXT("origins"), Origins) && Origins)
					{
						for (const TSharedPtr<FJsonValue>& V : *Origins) if (V.IsValid() && !V->AsString().IsEmpty()) B.EffectPlumeOrigins.Add(FName(*V->AsString()));
					}
				}
			}
			const TArray<TSharedPtr<FJsonValue>>* Layers = nullptr;
			if ((*Row)->TryGetArrayField(TEXT("effect_layers"), Layers) && Layers)
			{
				for (const TSharedPtr<FJsonValue>& V : *Layers)
				{
					const TArray<TSharedPtr<FJsonValue>>* L = nullptr;
					if (!V.IsValid() || !V->TryGetArray(L) || !L || L->Num() < 5 || B.EffectLayers.Num() >= 8) continue;
					FDinkFamilyEffectLayer Layer;
					Layer.OffsetCm = FVector(FMath::Clamp((*L)[0]->AsNumber(), -1000.0, 1000.0), FMath::Clamp((*L)[1]->AsNumber(), -1000.0, 1000.0), FMath::Clamp((*L)[2]->AsNumber(), -1000.0, 1000.0));
					Layer.Scale = FMath::Clamp((*L)[3]->AsNumber(), 0.1, 4.0);
					Layer.PhaseSeconds = FMath::Clamp((*L)[4]->AsNumber(), 0.0, 60.0);
					Layer.bMirror = L->Num() > 5 && (*L)[5]->AsNumber() != 0.0;
					B.EffectLayers.Add(Layer);
				}
			}
			const TSharedPtr<FJsonObject>* Decal = nullptr;
			if ((*Row)->TryGetObjectField(TEXT("effect_decal"), Decal) && Decal && Decal->IsValid())
			{
				static const TSet<FName> Directions = {TEXT("down"), TEXT("north"), TEXT("south"), TEXT("east"), TEXT("west")};
				const TArray<TSharedPtr<FJsonValue>>* Size = nullptr;
				if ((*Decal)->TryGetArrayField(TEXT("size_cm"), Size) && Size && Size->Num() == 2)
				{
					B.bEffectDecal = true;
					B.EffectDecalSizeCm = FVector2D(FMath::Clamp((*Size)[0]->AsNumber(), 5.0, 3000.0), FMath::Clamp((*Size)[1]->AsNumber(), 5.0, 3000.0));
					(*Decal)->TryGetNumberField(TEXT("depth_cm"), B.EffectDecalDepthCm);
					B.EffectDecalDepthCm = FMath::Clamp(B.EffectDecalDepthCm, 5.0, 1000.0);
					FString Towards;
					if ((*Decal)->TryGetStringField(TEXT("towards"), Towards) && Directions.Contains(FName(*Towards))) B.EffectDecalTowards = FName(*Towards);
					const TSharedPtr<FJsonObject>* Single = nullptr;
					if ((*Decal)->TryGetObjectField(TEXT("origins"), Single) && Single && Single->IsValid())
					{
						for (const auto& Pair : (*Single)->Values)
						{
							if (Pair.Value.IsValid() && Directions.Contains(FName(*Pair.Value->AsString()))) B.EffectDecalOrigins.Add(FName(*Pair.Key), FName(*Pair.Value->AsString()));
						}
					}
				}
			}
		}
		else if (!(*Row)->TryGetStringField(TEXT("mesh"), B.Mesh) || !B.Mesh.StartsWith(TEXT("/Game/")))
		{
			Errors.Add(FString::Printf(TEXT("%s: mesh must be a /Game/ object path"), *B.Family));
			continue;
		}
		if (B.Effect.IsEmpty()) B.Mesh = NormaliseObjectPath(B.Mesh);
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
			if ((*Row)->TryGetStringField(TEXT("stands_as"), B.StandsAs))
			{
				if (!B.StandsAs.StartsWith(TEXT("/Game/")))
				{
					Errors.Add(FString::Printf(TEXT("%s: stands_as must be a /Game/ object path"), *B.Family));
					continue;
				}
				B.StandsAs = NormaliseObjectPath(B.StandsAs);
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
		// "offset_cm": {"S439_P05": [x, y, z]}: single placements moved in world axes after everything else
		const TSharedPtr<FJsonObject>* Offsets = nullptr;
		if ((*Row)->TryGetObjectField(TEXT("offset_cm"), Offsets) && Offsets && Offsets->IsValid())
		{
			for (const auto& Pair : (*Offsets)->Values)
			{
				const TArray<TSharedPtr<FJsonValue>>* V = nullptr;
				if (Pair.Value.IsValid() && Pair.Value->TryGetArray(V) && V && (V->Num() == 3 || V->Num() == 4))
				{
					B.OffsetCm.Add(FName(*Pair.Key), FVector(FMath::Clamp((*V)[0]->AsNumber(), -2000.0, 2000.0),
						FMath::Clamp((*V)[1]->AsNumber(), -2000.0, 2000.0), FMath::Clamp((*V)[2]->AsNumber(), -2000.0, 2000.0)));
					if (V->Num() == 4) B.OffsetScale.Add(FName(*Pair.Key), FMath::Clamp((*V)[3]->AsNumber(), 0.1, 10.0));
				}
			}
		}
		(*Row)->TryGetBoolField(TEXT("yaw_from_sprite"), B.bYawFromSprite);
		(*Row)->TryGetBoolField(TEXT("scripted"), B.bScripted);
		{
			const TArray<TSharedPtr<FJsonValue>>* Scripts = nullptr;
			if ((*Row)->TryGetArrayField(TEXT("scripted_scripts"), Scripts) && Scripts)
			{
				for (const TSharedPtr<FJsonValue>& V : *Scripts)
				{
					FString Name;
					if (V.IsValid() && V->TryGetString(Name) && !Name.TrimStartAndEnd().IsEmpty()) B.ScriptedScripts.AddUnique(FName(*Name.TrimStartAndEnd()));
				}
			}
		}
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
		{
			FString AnchorText;
			if ((*Row)->TryGetStringField(TEXT("anchor"), AnchorText) && !DinkFamilyAnchor::Parse(AnchorText, B.Anchor))
			{
				Errors.Add(FString::Printf(TEXT("%s: anchor must be card, hardbox or hardbox_inner"), *B.Family));
				continue;
			}
		}
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
	if (P.bScripted && !B->bScripted && !B->ScriptedScripts.Contains(P.ScriptName)) return EDinkFamilyDecision::Scripted;
	OutBinding = B;
	return EDinkFamilyDecision::Bound;
}

const FDinkFamilyBinding* DinkArtFamily::ResolveScriptSprite(const TArray<FDinkFamilyBinding>& Bindings, int32 Sequence, FName ClassId, int32 Frame)
{
	const FDinkFamilyBinding* B = Resolve(Bindings, Sequence, ClassId, Frame);
	if (B && B->bEffectPlaced)
	{
		B = Resolve(Bindings, Sequence, NAME_None, Frame);
		if (B && B->bEffectPlaced) B = nullptr;
	}
	return B;
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
		if (!B.Effect.IsEmpty())
		{
			if (UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, *B.Effect, nullptr, LOAD_NoWarn | LOAD_Quiet)) Effects.Add(B.Effect, M);
			else UE_LOG(LogDink, Warning, TEXT("Family art: missing effect material %s for %s"), *B.Effect, *B.Family);
			if (!B.EffectPlume.IsEmpty() && !Effects.Contains(B.EffectPlume))
			{
				if (UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, *B.EffectPlume, nullptr, LOAD_NoWarn | LOAD_Quiet)) Effects.Add(B.EffectPlume, M);
				else UE_LOG(LogDink, Warning, TEXT("Family art: missing plume material %s for %s"), *B.EffectPlume, *B.Family);
			}
			continue;
		}
		MeshFor(B);
		for (const FString& Variant : B.Variants) LoadFamilyMesh(Variant, B.Family);
		if (!B.StandsAs.IsEmpty()) LoadFamilyMesh(B.StandsAs, B.Family);
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
	if (!Screen) return;  // between screens: Dink is still on the last one
	CurrentScreen = Screen->ScreenNumber;
	WarmEffects();
	ApplyScreen(Screen->ScreenNumber);
	// A208 copies showing different pictures (or a card): the copy of the screen Dink is on draws their object now.
	UDinkFamilyDuplicatesSubsystem::ScreenChanged(*this);
}

int32 UDinkArtFamilySubsystem::WarmEffects()
{
	UWorld* World = GetWorld();
	if (!World || !bReady || Effects.IsEmpty()) return 0;
	DINK_PERF_SCOPE(Dink_Family_WarmEffects);
	int32 Finished = 0;
#if WITH_EDITOR
	// FMaterial::IsCompilationFinished / FinishCompilation exist only in editor builds: the packaged game (cooked shader maps) skips this.
	if (FApp::CanEverRender())
	{
		// Uncooked: finish the shader maps still compiling (a cooked game has them all; IsCompilationFinished is then true).
		TArray<FMaterial*> Compiling;
		for (const TPair<FString, TObjectPtr<UMaterialInterface>>& Pair : Effects)
			if (UMaterialInterface* Material = Pair.Value.Get())
				if (FMaterialResource* Resource = Material->GetMaterialResource(GMaxRHIShaderPlatform))
					if (!Resource->IsCompilationFinished()) Compiling.AddUnique(Resource);
		if (Compiling.Num())
		{
			FMaterial::FinishCompilation(TEXT("Dink effect warm-up"), Compiling);
			Finished = Compiling.Num();
			UE_LOG(LogDink, Display, TEXT("Family art: finished the shader compile of %d effect materials before their first use"), Finished);
		}
	}
#endif
	if (!WarmCard)
	{
		// The same component and vertex factory as the effect cards (DressScriptSprite), so the same PSOs; never drawn.
		FActorSpawnParameters Params;
		Params.Name = MakeUniqueObjectName(World->PersistentLevel, AActor::StaticClass(), TEXT("DinkEffectWarmup"));
		Params.ObjectFlags |= RF_Transient;
		AActor* Holder = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, Params);
		if (!Holder) return Finished;
		Holder->SetActorHiddenInGame(true);
		WarmCard = NewObject<UMaterialBillboardComponent>(Holder, TEXT("EffectWarmupCard"));
		Holder->SetRootComponent(WarmCard);
		WarmCard->SetMobility(EComponentMobility::Movable);
		WarmCard->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		WarmCard->SetCanEverAffectNavigation(false);
		WarmCard->SetGenerateOverlapEvents(false);
		WarmCard->SetCastShadow(false);
		WarmCard->SetHiddenInGame(true);
		WarmCard->SetVisibility(false);
		WarmCard->RegisterComponent();
		TArray<FString> Keys;
		Effects.GetKeys(Keys);
		Keys.Sort();
		for (const FString& Key : Keys)
			if (UMaterialInterface* Material = Effects[Key].Get()) WarmCard->AddElement(Material, nullptr, false, 1.f, 1.f, nullptr);
	}
	return Finished;
}

void UDinkArtFamilySubsystem::BuildIndex(UWorld& World)
{
	DINK_PERF_SCOPE(Dink_Family_BuildIndex);
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
	UDinkFamilyDuplicatesSubsystem::Build(*this);  // A208: which copy of a cross-screen duplicate draws it, once, from placement data
}

FName UDinkArtFamilySubsystem::ClassOfPicture(int32 Sequence, int32 Frame) const
{
	if (Sequence <= 0 || Frame < 0 || Frame > 0xffff) return NAME_None;
	const FName* Found = ClassByPicture.Find(Sequence << 16 | Frame);
	return Found ? *Found : NAME_None;
}

bool UDinkArtFamilySubsystem::DressScriptSprite(AActor* Actor, int32 Sequence, int32 Frame, const FVector& GroundOffset, float Size, bool bAllowPictureCard)
{
	UWorld* World = GetWorld();
	if (!Actor || !World || !Actor->GetRootComponent()) return false;
	UStaticMeshComponent* Shown = Actor->FindComponentByTag<UStaticMeshComponent>(ScriptSpriteTag);
	// Script characters, creatures and food are presented by their own layers.
	// A class row's body (creatures.json `classes`: a script-made duck, townsman or Seth) adds no actor tag; without this test
	// the sprite's 1997 picture card was drawn through its figure at the next change of frame.
	const bool bOtherLayer = Actor->ActorHasTag(TEXT("DinkAuthoredArt")) || Actor->ActorHasTag(TEXT("DinkHumanoid")) ||
		Actor->ActorHasTag(TEXT("DinkScriptHumanoid")) || Actor->ActorHasTag(TEXT("DinkCreature")) ||
		Actor->FindComponentByTag<UStaticMeshComponent>(TEXT("DinkAuthoredFood")) != nullptr ||
		Actor->FindComponentByClass<UDinkCreatureClassComponent>() != nullptr;
	const FDinkFamilyBinding* B = nullptr;
	UStaticMesh* Mesh = nullptr;
	const FVector Ground = Actor->GetActorLocation() + GroundOffset;
	// No origin ID: the spot stands in for it, so heaps dropped side by side differ in variant and yaw, the same every run.
	const FString Key = FString::Printf(TEXT("script:%d:%d:%d:%d"), Sequence, Frame, FMath::RoundToInt(Ground.X), FMath::RoundToInt(Ground.Y));
	// A sequence an init line replaced (Seth over the green gnome, s7-mil.c) no longer shows dink.ini's picture: no family mesh of it.
	if (bReady && !bOtherLayer && Sequence > 0 && !DinkInitSequencePictures().Contains(Sequence))
	{
		if (!bIndexed) BuildIndex(*World);
		// A frame no placement of the world uses (an animation's other frames) takes the class of its sequence.
		FName Class = ClassOfPicture(Sequence, Frame);
		if (Class.IsNone()) Class = ClassOfPicture(Sequence, 0);
		// never an "effect_placed" row: the class row of the burning house's placed fire bursts must not swallow the
		// explosion a script creates with the same picture
		B = DinkArtFamily::ResolveScriptSprite(Bindings, Sequence, Class, Frame);
		Mesh = B ? MeshFor(*B, Key) : nullptr;
	}
	UStaticMeshComponent* Marker = Cast<UStaticMeshComponent>(Actor->GetRootComponent());
	// A picture that is light, not a thing (the twinkle on gold): a camera-facing card with the row's effect material.
	UMaterialBillboardComponent* Card = Actor->FindComponentByClass<UMaterialBillboardComponent>();
	const TObjectPtr<UMaterialInterface>* Effect = B && !B->Effect.IsEmpty() ? Effects.Find(B->Effect) : nullptr;
	if (Effect && *Effect)
	{
		RemoveScriptPictureCard(Actor);
		if (Shown) Shown->DestroyComponent();
		if (!Card)
		{
			// A unique name: a card destroyed earlier (DestroyComponent) keeps its name until garbage collection, and NewObject under
			// that name rebuilds the dead object in place (the engine's "UObject overwrite": a render-fence stall, and every weak
			// pointer to the old component then resolves to the new one).
			Card = NewObject<UMaterialBillboardComponent>(Actor, MakeUniqueObjectName(Actor, UMaterialBillboardComponent::StaticClass(), TEXT("ScriptFamilyEffect")));
			Card->SetMobility(EComponentMobility::Movable);
			Card->SetupAttachment(Actor->GetRootComponent());
			Card->SetUsingAbsoluteScale(true);
			Card->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Card->SetCanEverAffectNavigation(false);
			Card->SetGenerateOverlapEvents(false);
			Card->SetCastShadow(false);
			Card->ComponentTags.Add(FamilyTag);
			Card->ComponentTags.Add(ScriptEffectTag);
			Actor->AddInstanceComponent(Card);
			Card->RegisterComponent();
		}
		const float Half = float(B->EffectSizeCm * 0.5 * FMath::Max(double(Size) * B->Scale, double(DinkArtFamily::MinScale)));
		// A one-shot flipbook (an explosion) must start at its first frame when the sprite appears: the card draws a
		// dynamic instance that knows its start time (scalar StartTime, read by M_FX_Flipbook*; world seconds).
		UMaterialInstanceDynamic* Playing = Card->Elements.Num() == 1 ? Cast<UMaterialInstanceDynamic>(Card->Elements[0].Material) : nullptr;
		if (!Playing || Playing->Parent != *Effect)
		{
			Playing = UMaterialInstanceDynamic::Create(*Effect, Card);
			if (Playing) Playing->SetScalarParameterValue(TEXT("StartTime"), float(World->GetTimeSeconds()));
		}
		Card->SetElements({});
		Card->AddElement(Playing ? static_cast<UMaterialInterface*>(Playing) : Effect->Get(), nullptr, false, Half, Half, nullptr);
		Card->SetWorldLocation(Ground + FVector(0.0, 0.0, Half * 0.9) + B->EffectOffsetCm);
		// "effect_light" on a script-created sprite: the fire lights what it passes (no shadows; gone with the sprite)
		static const FName ScriptEffectLightTag(TEXT("DinkScriptFamilyEffectLight"));
		UDinkFlickerLightComponent* Glow = Actor->FindComponentByTag<UDinkFlickerLightComponent>(ScriptEffectLightTag);
		const bool bLit = B->EffectLightCandela > 0.0 && B->EffectLightRadiusCm > 0.0;
		if (Glow && !bLit)
		{
			Glow->DestroyComponent();
			Glow = nullptr;
		}
		if (bLit)
		{
			if (!Glow)
			{
				Glow = NewObject<UDinkFlickerLightComponent>(Actor, MakeUniqueObjectName(Actor, UDinkFlickerLightComponent::StaticClass(), TEXT("ScriptFamilyEffectLight")));
				Glow->SetMobility(EComponentMobility::Movable);
				Glow->SetupAttachment(Card);
				Glow->SetUsingAbsoluteScale(true);
				Glow->SetIntensityUnits(ELightUnits::Candelas);
				Glow->SetCastShadows(false);
				Glow->ComponentTags.Add(FamilyTag);
				Glow->ComponentTags.Add(ScriptEffectLightTag);
				Actor->AddInstanceComponent(Glow);
				Glow->RegisterComponent();
			}
			Glow->SetIntensity(float(B->EffectLightCandela));
			Glow->SetLightColor(B->EffectLight);
			Glow->SetAttenuationRadius(float(B->EffectLightRadiusCm));
			Glow->SetSourceRadius(Half * 0.15f);
			Glow->SetSoftSourceRadius(Half * 0.25f);
			Glow->SetFlicker(float(B->EffectLightCandela), float(B->EffectLightFlicker), float(FMath::Fmod(FMath::Abs(Ground.X * 0.013 + Ground.Y * 0.007), 97.0)));
			Glow->SetWorldLocation(Card->GetComponentLocation());
		}
		if (Marker) Marker->SetHiddenInGame(true);
		return true;
	}
	if (Card && Card->ComponentHasTag(ScriptEffectTag))
	{
		if (UDinkFlickerLightComponent* Glow = Actor->FindComponentByTag<UDinkFlickerLightComponent>(TEXT("DinkScriptFamilyEffectLight"))) Glow->DestroyComponent();
		Card->DestroyComponent();
		if (Marker && !bOtherLayer) Marker->SetHiddenInGame(false);
	}
	if (!Mesh)
	{
		if (Shown) Shown->DestroyComponent();
		// No family mesh: the 1997 picture on a card, never the grey marker, when that picture was imported (A53).
		if (!bOtherLayer && bAllowPictureCard && ShowScriptPictureCard(Actor, Sequence, Frame, Ground, Size))
		{
			if (Marker) Marker->SetHiddenInGame(true);
			return true;
		}
		const bool bHadCard = RemoveScriptPictureCard(Actor);
		if ((Shown || bHadCard) && Marker && !bOtherLayer) Marker->SetHiddenInGame(false);
		return false;
	}
	RemoveScriptPictureCard(Actor);
	if (Shown && Shown->GetStaticMesh() != Mesh)
	{
		Shown->DestroyComponent();
		Shown = nullptr;
	}
	if (!Shown)
	{
		// A unique name: the mesh just destroyed above keeps "ScriptFamilyArt" until garbage collection (see the effect card).
		Shown = NewObject<UStaticMeshComponent>(Actor, MakeUniqueObjectName(Actor, UStaticMeshComponent::StaticClass(), TEXT("ScriptFamilyArt")));
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
	if (Binding.Mesh.IsEmpty()) return nullptr;  // an effect row
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

bool UDinkArtFamilySubsystem::SetPlacementPicture(ADinkPlaceholderActor& Actor, int32 Sequence, int32 Frame, bool bScripted)
{
	UWorld* World = GetWorld();
	if (!World || !Actor.Origin || IsCollisionFitRequested(Actor.Origin->OriginId)) return false;
	const FPlacementPicture* Known = PlacementPictures.Find(&Actor);
	const bool bImported = Sequence <= 0 || (Sequence == Actor.Origin->Sequence && Frame == Actor.Origin->Frame && bScripted == !Actor.Origin->ScriptName.IsNone());
	if (bImported ? !Known : (Known && Known->Sequence == Sequence && Known->Frame == Frame && Known->bScripted == bScripted))
	{
		return Actor.ActorHasTag(FamilyTag) && !Actor.ActorHasTag(UDinkFamilyDuplicatesSubsystem::DroppedTag);
	}
	if (bImported) PlacementPictures.Remove(&Actor);
	else PlacementPictures.Add(&Actor, FPlacementPicture{Sequence, Frame, bScripted});
	if (!bReady) return false;
	if (!bIndexed) BuildIndex(*World);
	// A208 (review R5/R6 of #192): a copy of a cross-screen duplicate gets back what that rule hid on it, so it is undressed and
	// dressed below like any placement; PictureChanged then decides again which copy draws the object.
	UDinkFamilyDuplicatesSubsystem::Restore(*this, Actor);
	// Undo what DressActor did for the old picture (its FamilyArt parts and the hidden card), then dress from the new one.
	TInlineComponentArray<UStaticMeshComponent*> Parts(&Actor);
	bool bUndressed = false;
	for (UStaticMeshComponent* Part : Parts)
	{
		if (Part && Part != Actor.Card && Part->ComponentHasTag(FamilyTag) && !Part->ComponentHasTag(ScriptSpriteTag) && Part->GetName().StartsWith(TEXT("FamilyArt")))
		{
			Actor.RemoveInstanceComponent(Part);
			Part->DestroyComponent();
			bUndressed = true;
		}
	}
	if (bUndressed)
	{
		Actor.Tags.Remove(FamilyTag);
		if (Actor.Card) Actor.Card->SetHiddenInGame(false);
	}
	// Copies that showed one picture may show two now (1997 then draws the copy of the screen Dink is on, with its own picture),
	// or one again: the duplicate rule hides every copy but the one that draws, and dresses that one if it was hidden undressed.
	UDinkFamilyDuplicatesSubsystem::PictureChanged(*this, Actor);
	if (Actor.ActorHasTag(UDinkFamilyDuplicatesSubsystem::DroppedTag)) return false;
	// A screen not yet activated is dressed by ApplyScreen, from the picture registered above.
	return AppliedScreens.Contains(Actor.ScreenNumber) && DressActor(Actor);
}

bool UDinkArtFamilySubsystem::FollowPlacementPicture(ADinkPlaceholderActor& Actor, int32 Sequence, int32 Frame)
{
	if (!bReady || !Actor.Origin || Sequence <= 0 || Frame <= 0) return false;
	const FDinkFamilyBinding* Row = DinkArtFamily::Resolve(Bindings, Sequence, NAME_None, Frame);
	if (!Row || Row->Sequence != Sequence || Row->Frame != Frame) return false;
	// The binding the placement is dressed from now: its registered picture, else the imported one.
	int32 ShownSequence = Actor.Origin->Sequence, ShownFrame = Actor.Origin->Frame;
	FName ShownClass = Actor.Origin->ClassId;
	if (const FPlacementPicture* Known = PlacementPictures.Find(&Actor))
	{
		ShownSequence = Known->Sequence;
		ShownFrame = Known->Frame;
		ShownClass = ClassOfPicture(Known->Sequence, Known->Frame);
	}
	// Already dressed with that mesh (175/4 -> 175/5: the lid stays up): nothing to do, no component is rebuilt.
	const FDinkFamilyBinding* Shown = DinkArtFamily::Resolve(Bindings, ShownSequence, ShownClass, ShownFrame);
	if (Actor.ActorHasTag(FamilyTag) && Shown && (Shown == Row || (Shown->Mesh == Row->Mesh && Shown->Variants == Row->Variants && Shown->Scale == Row->Scale &&
		Shown->AnchorFront == Row->AnchorFront && Shown->bYawFromSprite == Row->bYawFromSprite && Shown->YawOffset == Row->YawOffset))) return false;
	const bool bShown = SetPlacementPicture(Actor, Sequence, Frame, !Actor.Origin->ScriptName.IsNone());
	UE_LOG(LogDink, Log, TEXT("Family art: %s follows its animation to %d/%d (%s)"), *Actor.Origin->OriginId.ToString(), Sequence, Frame,
		bShown ? *Row->Mesh : TEXT("not shown"));
	return bShown;
}

int32 UDinkArtFamilySubsystem::ApplyScreen(int32 ScreenNumber)
{
	DINK_PERF_SCOPE(Dink_Family_ApplyScreen);
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
			if (!Screen.IsValid()) continue;
			Count += DressInstances(*Screen.Get());
			// the family meshes and their player-only blockers are made at the flat ground: on the landforms' ground with the rest
			if (UDinkLandformsSubsystem* Landforms = World->GetSubsystem<UDinkLandformsSubsystem>()) Landforms->SnapScreenDecor(*Screen.Get());
		}
	}
	Dressed += Count;
	UE_LOG(LogDink, Log, TEXT("Family art: screen %d, %d placements dressed (%d in all)"), ScreenNumber, Count, Dressed);
	return Count;
}

FDinkFamilyPlacement UDinkArtFamilySubsystem::PlacementOf(ADinkPlaceholderActor& Actor) const
{
	FDinkFamilyPlacement P;
	if (!Actor.Origin) return P;
	P.Origin = Actor.Origin->OriginId.ToString();
	P.Screen = Actor.ScreenNumber;
	P.Sequence = Actor.Origin->Sequence;
	P.Frame = Actor.Origin->Frame;
	P.ClassId = Actor.Origin->ClassId;
	P.bScripted = !Actor.Origin->ScriptName.IsNone();
	P.ScriptName = Actor.Origin->ScriptName;
	P.bHardnessOnly = Actor.PlacementKind == TEXT("hardness_only");
	// The picture the save gave this placement (SetPlacementPicture), and with it its class and its (cleared) script.
	if (const FPlacementPicture* Saved = PlacementPictures.Find(&Actor))
	{
		P.Sequence = Saved->Sequence;
		P.Frame = Saved->Frame;
		P.ClassId = ClassOfPicture(Saved->Sequence, Saved->Frame);
		P.bScripted = Saved->bScripted;
	}
	return P;
}

void UDinkArtFamilySubsystem::ShownPicture(ADinkPlaceholderActor& Actor, int32& OutSequence, int32& OutFrame) const
{
	OutSequence = Actor.Origin ? Actor.Origin->Sequence : 0;
	OutFrame = Actor.Origin ? Actor.Origin->Frame : 0;
	if (const FPlacementPicture* Saved = PlacementPictures.Find(&Actor))
	{
		OutSequence = Saved->Sequence;
		OutFrame = Saved->Frame;
	}
}

bool UDinkArtFamilySubsystem::WouldDressMesh(ADinkPlaceholderActor& Actor) const
{
	if (!bReady || !Actor.Origin) return false;
	const FDinkFamilyBinding* B = nullptr;
	if (DinkArtFamily::Decide(PlacementOf(Actor), Precedence, Bindings, B) != EDinkFamilyDecision::Bound || !B || !B->Effect.IsEmpty() || B->Mesh.IsEmpty()) return false;
	return Meshes.Contains(B->Mesh);  // every bound mesh was loaded at begin play; a missing one leaves the card
}

void UDinkArtFamilySubsystem::FollowCardVisibility(const USceneComponent* Card)
{
	if (!Card) return;
	const bool bVisible = Card->GetVisibleFlag();
	for (USceneComponent* Child : Card->GetAttachChildren())
	{
		if (Child && Child->ComponentHasTag(FamilyTag) && Child->GetVisibleFlag() != bVisible) Child->SetVisibility(bVisible);
	}
}

bool UDinkArtFamilySubsystem::DressActor(ADinkPlaceholderActor& Actor)
{
	DINK_PERF_SCOPE(Dink_Family_DressActor);
	UStaticMeshComponent* Card = Actor.Card;
	if (!Actor.Origin || !Card || !Card->GetStaticMesh() || !Actor.GetRootComponent()) return false;
	// Whatever the art runtime already took over at play start, whatever this layer dressed before.
	if (Actor.ActorHasTag(FamilyTag) || Actor.ActorHasTag(TEXT("DinkAuthoredArt")) || Actor.ActorHasTag(TEXT("DinkHumanoid")) ||
		Actor.ActorHasTag(TEXT("DinkCreature")) || Card->bHiddenInGame)
	{
		return false;
	}
	const FDinkFamilyPlacement P = PlacementOf(Actor);
	const FDinkFamilyBinding* B = nullptr;
	const EDinkFamilyDecision Decision = DinkArtFamily::Decide(P, Precedence, Bindings, B);
	DecisionCounts.FindOrAdd(Decision)++;
	if (Decision == EDinkFamilyDecision::ScreenDressed && !Precedence.Origins.Contains(P.Origin))
	{
		// An art manifest dresses this screen's things; nothing but this layer draws effects (the fires of screen 1).
		const FDinkFamilyBinding* Fx = DinkArtFamily::Resolve(Bindings, P.Sequence, P.ClassId, P.Frame);
		if (Fx && Fx->bEffectPlaced && !Fx->Effect.IsEmpty() && (!P.bScripted || Fx->bScripted)) B = Fx;
	}
	if (B && !B->Effect.IsEmpty()) return B->bEffectPlaced && DressPlacedEffect(Actor, *B);
	if (B && UDinkFamilyDuplicatesSubsystem::DropActor(*this, Actor, P.Origin)) return false;  // A208: another copy draws it
	UStaticMesh* Mesh = B ? MeshFor(*B, P.Origin) : nullptr;
	if (!Mesh) return false;

	// The card is the sprite at its imported size: relative scale (width, 1, height) in metres of a 1 m unit card.
	FVector CardLocation = Card->GetRelativeLocation();
	FVector CardScale = Card->GetRelativeScale3D();
	// "stands_as": the states of one thing stand where its base mesh stands (same pivot), whatever their own bounds are
	UStaticMesh* StandsAs = B->StandsAs.IsEmpty() ? nullptr : LoadFamilyMesh(B->StandsAs, B->Family);
	const FBox PlaceBounds = StandsAs ? StandsAs->GetBoundingBox() : Mesh->GetBoundingBox();
	// ... and where and how the placement's OWN picture stands, not the picture of the moment: the script that opens a 177
	// chest plays the pictures of 175 (the chest seen from its other side, another width and origin) and saves one of
	// them; in 3D the opened chest must be the closed one with its lid up, on the same spot, turned the same way.
	int32 AnchorSequence = P.Sequence, AnchorFrame = P.Frame;
	double YawOffset = B->YawOffset;
	FVector CardWorld = Card->GetComponentLocation();
	if (StandsAs)
	{
		if (Actor.bHasImportedCardBaseline)
		{
			CardLocation = Actor.ImportedCardRelativeTransform.GetLocation();
			CardScale = Actor.ImportedCardRelativeTransform.GetScale3D();
			CardWorld = Actor.GetActorTransform().TransformPosition(CardLocation);
		}
		AnchorSequence = Actor.Origin->Sequence;
		AnchorFrame = Actor.Origin->Frame;
		if (const FDinkFamilyBinding* Own = DinkArtFamily::Resolve(Bindings, Actor.Origin->Sequence, Actor.Origin->ClassId, Actor.Origin->Frame)) YawOffset = Own->YawOffset;
	}
	const double* Larger = B->OffsetScale.Find(FName(*P.Origin));      // "offset_cm" fourth number: this placement's size factor
	const float Scale = float(B->Scale * (Larger ? *Larger : 1.0)) * DinkArtFamily::FitScale(B->Fit, CardScale.X * 100.0, CardScale.Z * 100.0, PlaceBounds.GetSize(), B->bYawFromSprite);
	const double Yaw = (B->bYawFromSprite ? 0.0 : DinkArtFamily::StableYaw(P.Origin)) + YawOffset;

	// +Y is south, towards the original camera: a front-anchored mesh moves back by half its depth
	const double Back = B->AnchorFront * 0.5 * DinkArtFamily::DepthAfterYaw(PlaceBounds.GetSize(), Yaw, Scale);
	// a spanning module (interior wall runs) is repeated along its run until it fills the layout-scaled card
	TArray<DinkArtFamily::FSpanPiece> Pieces;
	DinkArtFamily::SpanPieces(*B, (B->Span == 2 ? CardScale.Z : CardScale.X) * 100.0, PlaceBounds.GetSize().X * Scale, Pieces);
	// families.json "anchor": stand the mesh on the placement's 1997 hardbox (presentation only, DinkFamilyAnchor.h)
	FVector2D Stand(CardLocation.X, CardLocation.Y - Back);
	if (B->Anchor != EDinkFamilyAnchor::Card)
	{
		const UDinkGreyboxSubsystem* Grey = Actor.GetWorld() ? Actor.GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
		const ADinkScreenVolume* Volume = Grey ? Grey->FindScreen(Actor.ScreenNumber) : nullptr;
		FVector Target;
		if (Volume && DinkFamilyAnchor::AnchorWorld(*Volume, B->Anchor, AnchorSequence, AnchorFrame, CardWorld, CardScale.X * 100.0,
			Actor.GetActorRotation().Yaw - Volume->GetActorRotation().Yaw + Yaw, PlaceBounds.GetSize() * Scale, Target))
		{
			const FVector Local = Actor.GetActorTransform().InverseTransformPosition(Target);
			Stand = FVector2D(Local.X, Local.Y);
		}
	}
	// families.json "offset_cm": this one placement stands elsewhere (a flight of stairs against the drawn wall)
	double Lift = 0.0;
	if (const FVector* Offset = B->OffsetCm.Find(FName(*P.Origin)))
	{
		const FVector Local = Actor.GetActorTransform().InverseTransformVector(*Offset);
		Stand += FVector2D(Local.X, Local.Y);
		Lift = Local.Z;
	}
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
		DinkPerf::CacheVegetationShadows(*Part, PieceMesh);   // perf-stutter: wind-swayed trees and bushes keep cached rest-pose shadows
		Part->SetRelativeTransform(DinkArtFamily::SpanTransform(StandsAs && PieceMesh == Mesh ? PlaceBounds : PieceMesh->GetBoundingBox(), FVector(Stand.X, Stand.Y, Lift), Yaw, Scale, Pieces[Index]));
		Actor.AddInstanceComponent(Part);
		Part->RegisterComponent();
		// A drawn solid body larger than the placement's 1997 hardbox stops the player (player only; unscripted placements,
		// whose scripts never move or remove them; scripted barrels keep the fitted barrel lifecycle of DinkFamilyCollisionFit,
		// which checks the barrel actor's components, untouched).
		if (!P.bScripted) DinkPlayerBlockers::Add(Actor, *Part, FTransform::Identity, PieceMesh, P.Origin);
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

bool UDinkArtFamilySubsystem::DressPlacedEffect(ADinkPlaceholderActor& Actor, const FDinkFamilyBinding& Binding)
{
	const TObjectPtr<UMaterialInterface>* Effect = Effects.Find(Binding.Effect);
	UStaticMeshComponent* Card = Actor.Card;
	if (!Effect || !*Effect || !Card || !Card->GetStaticMesh()) return false;
	// The unit card scaled (width, 1, height) in metres: keep the middle of its bottom edge, change its size.
	const FBox Unit = Card->GetStaticMesh()->GetBoundingBox();
	const FVector OldScale = Card->GetRelativeScale3D();
	const FVector OldLocation = Card->GetRelativeLocation();
	const FName OriginName = Actor.Origin ? FName(*Actor.Origin->OriginId.ToString()) : NAME_None;
	const double* Larger = Binding.OffsetScale.Find(OriginName);      // "offset_cm" fourth number: this placement's size factor
	const double Grow = Larger ? *Larger : 1.0;
	const FVector NewScale(OldScale.X / Binding.EffectFit.X * Grow, OldScale.Y, OldScale.Z / Binding.EffectFit.Y * Grow);
	const double Width = Unit.GetSize().X * NewScale.X;
	const double Height = Unit.GetSize().Z * NewScale.Z;
	const double Bottom = OldLocation.Z + Unit.Min.Z * OldScale.Z;
	const double CentreX = OldLocation.X + Unit.GetCenter().X * OldScale.X;
	if (Card->Mobility != EComponentMobility::Movable) Card->SetMobility(EComponentMobility::Movable);
	Card->SetRelativeScale3D(NewScale);
	// +Y is south: what floated above its sort point stands that far to the north
	const double NewBottom = Binding.bEffectGround ? 0.0 : Bottom;
	const double NewY = Binding.bEffectGround ? OldLocation.Y - Bottom : OldLocation.Y;
	Card->SetRelativeLocation(FVector(CentreX - Unit.GetCenter().X * NewScale.X, NewY, NewBottom - Height * Binding.EffectSink - Unit.Min.Z * NewScale.Z));
	// A fire the 1997 picture paints on a roof stands on the ground point under that pixel; the row moves it onto the roof.
	if (const FVector* Offset = Binding.OffsetCm.Find(OriginName)) Card->AddWorldOffset(*Offset);
	Card->SetCastShadow(false);
	Card->ComponentTags.AddUnique(FamilyTag);
	if (Binding.bEffectDecal)
	{
		// A burn on a roof or a wall: the effect is projected onto what stands there; the camera-facing card is not drawn.
		// The card stays the placement's card and keeps its visible flag and bHiddenInGame: both belong to the screen and
		// vision rules (UDinkGreyboxSubsystem::UpdateLegacyCardVisibility records the flag at first sight and sets it again
		// on the card's own screen, so a SetVisibility(false) here was undone: the magnified 1997 picture stood upright in
		// front of the roof with the decal smeared down it). It is taken out of the render passes instead, and the decal
		// and the light follow its flag as its children (FollowCardVisibility).
		const FName* Single = Binding.EffectDecalOrigins.Find(OriginName);
		const FName Towards = Single ? *Single : Binding.EffectDecalTowards;
		// a decal projects along its local +X; the texture's top is the decal's +Z
		const FRotator Aim = Towards == TEXT("north") ? FRotator(0.0, -90.0, 0.0) : Towards == TEXT("south") ? FRotator(0.0, 90.0, 0.0) :
			Towards == TEXT("east") ? FRotator(0.0, 0.0, 0.0) : Towards == TEXT("west") ? FRotator(0.0, 180.0, 0.0) : FRotator(-90.0, 90.0, 0.0);
		UDecalComponent* Decal = NewObject<UDecalComponent>(&Actor, TEXT("FamilyEffectDecal"));
		Decal->SetMobility(EComponentMobility::Movable);
		Decal->SetupAttachment(Card);
		Decal->SetUsingAbsoluteLocation(true);   // the card turns to the camera; the mark stays where it is
		Decal->SetUsingAbsoluteRotation(true);
		Decal->SetUsingAbsoluteScale(true);
		Decal->SetDecalMaterial(*Effect);
		Decal->DecalSize = FVector(Binding.EffectDecalDepthCm, Binding.EffectDecalSizeCm.X * 0.5 * Grow, Binding.EffectDecalSizeCm.Y * 0.5 * Grow);
		Decal->SetFadeScreenSize(0.f);
		Decal->ComponentTags.Add(FamilyTag);
		Actor.AddInstanceComponent(Decal);
		Decal->RegisterComponent();
		Decal->SetWorldLocationAndRotation(Card->GetComponentLocation() + Card->GetComponentRotation().RotateVector(
			FVector(Unit.GetCenter().X * NewScale.X, 0.0, Unit.GetCenter().Z * NewScale.Z)), Aim);
		Card->SetRenderInMainPass(false);
		Card->SetRenderInDepthPass(false);
		Card->SetReceivesDecals(false);
		Card->SetAffectDynamicIndirectLighting(false);
		Card->SetVisibleInRayTracing(false);
	}
	else
	{
		for (int32 Slot = 0; Slot < Card->GetNumMaterials(); ++Slot) Card->SetMaterial(Slot, *Effect);
		// "effect_layers": the same flipbook again, behind and in front, each at another place in its loop
		for (int32 Index = 0; Index < Binding.EffectLayers.Num(); ++Index)
		{
			const FDinkFamilyEffectLayer& L = Binding.EffectLayers[Index];
			UStaticMeshComponent* Layer = NewObject<UStaticMeshComponent>(&Actor, FName(*FString::Printf(TEXT("FamilyEffectLayer_%d"), Index)));
			Layer->SetMobility(EComponentMobility::Movable);
			Layer->SetupAttachment(Card);
			Layer->SetStaticMesh(Card->GetStaticMesh());
			Layer->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
			Layer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Layer->SetCanEverAffectNavigation(false);
			Layer->SetGenerateOverlapEvents(false);
			Layer->SetCastShadow(false);
			Layer->ComponentTags.Add(FamilyTag);
			// The card's own scale is (width, 1, height): offsets in cm are divided by it. The layer keeps the card's
			// bottom middle (plus its offset) whatever its size; the card's face normal is local +Y.
			const double Side = L.bMirror ? -L.Scale : L.Scale;
			Layer->SetRelativeScale3D(FVector(Side, 1.0, L.Scale));
			// (a placement's size factor, "offset_cm" fourth number, spreads its layers too)
			Layer->SetRelativeLocation(FVector(Unit.GetCenter().X * (1.0 - Side) + L.OffsetCm.X * Grow / FMath::Max(NewScale.X, 1e-3), L.OffsetCm.Y * Grow,
				Unit.Min.Z * (1.0 - L.Scale) + L.OffsetCm.Z * Grow / FMath::Max(NewScale.Z, 1e-3)));
			UMaterialInstanceDynamic* Playing = UMaterialInstanceDynamic::Create(*Effect, Layer);
			if (Playing) Playing->SetScalarParameterValue(TEXT("StartTime"), -float(L.PhaseSeconds));
			for (int32 Slot = 0; Slot < Card->GetNumMaterials(); ++Slot) Layer->SetMaterial(Slot, Playing ? static_cast<UMaterialInterface*>(Playing) : Effect->Get());
			Actor.AddInstanceComponent(Layer);
			Layer->RegisterComponent();
		}
	}
	if (Binding.EffectLightCandela > 0.0 && Binding.EffectLightRadiusCm > 0.0)
	{
		UDinkFlickerLightComponent* Light = NewObject<UDinkFlickerLightComponent>(&Actor, TEXT("FamilyEffectLight"));
		Light->SetMobility(EComponentMobility::Movable);
		Light->SetupAttachment(Card);
		Light->SetUsingAbsoluteScale(true);
		Light->SetIntensityUnits(ELightUnits::Candelas);
		Light->SetIntensity(float(Binding.EffectLightCandela));
		Light->SetLightColor(Binding.EffectLight);
		Light->SetAttenuationRadius(float(Binding.EffectLightRadiusCm));
		Light->SetSourceRadius(float(Width * 0.2));
		Light->SetSoftSourceRadius(float(Width * 0.3));
		Light->SetCastShadows(false);
		Light->ComponentTags.Add(FamilyTag);
		Actor.AddInstanceComponent(Light);
		Light->RegisterComponent();
		// firelight wavers; the phase comes from where the fire stands, so neighbouring fires do not pulse together
		Light->SetFlicker(float(Binding.EffectLightCandela), float(Binding.EffectLightFlicker), float(FMath::Fmod(FMath::Abs(Actor.GetActorLocation().X * 0.013 + Actor.GetActorLocation().Y * 0.007), 97.0)));
		// in front of the card (the card's face normal is local +Y), so the card never shades its own light
		Light->SetWorldLocation(Card->GetComponentLocation() + Card->GetComponentRotation().RotateVector(FVector(Unit.GetCenter().X * NewScale.X, 12.0, Unit.Min.Z * NewScale.Z + Height * (Binding.EffectSink + Binding.EffectLightHeight))));
	}
	// The smoke that rolls up from this one fire (outdoors: under a roof it would stand in the rafters): a camera-facing
	// card of its own, its foot in the upper flames.
	const TObjectPtr<UMaterialInterface>* Plume = Binding.EffectPlume.IsEmpty() || !Actor.Origin || !Binding.EffectPlumeOrigins.Contains(OriginName)
		? nullptr : Effects.Find(Binding.EffectPlume);
	if (Plume && *Plume)
	{
		UMaterialBillboardComponent* Smoke = NewObject<UMaterialBillboardComponent>(&Actor, TEXT("FamilyEffectPlume"));
		Smoke->SetMobility(EComponentMobility::Movable);
		Smoke->SetupAttachment(Card);
		Smoke->SetUsingAbsoluteScale(true);
		Smoke->SetCastShadow(false);
		Smoke->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Smoke->ComponentTags.Add(FamilyTag);
		Smoke->AddElement(*Plume, nullptr, false, float(Binding.EffectPlumeSizeCm.X * 0.5), float(Binding.EffectPlumeSizeCm.Y * 0.5), nullptr);
		Actor.AddInstanceComponent(Smoke);
		Smoke->RegisterComponent();
		// the column's lit foot stands inside the flames' upper half (0.55 left a gap of sky between fire and smoke)
		const double FlameTop = Height * Binding.EffectFit.Y * 0.28;
		Smoke->SetWorldLocation(Card->GetComponentLocation() + Card->GetComponentRotation().RotateVector(
			FVector(Unit.GetCenter().X * NewScale.X, -6.0, Unit.Min.Z * NewScale.Z + Height * Binding.EffectSink + FlameTop + Binding.EffectPlumeSizeCm.Y * 0.5)));
	}
	// A neighbour screen is dressed while its cards are not rendered (dink.LegacyCardsCurrentScreen): the light and the smoke
	// column start as the card is, never as a lit 7 m column over flames that are not drawn (review R11 of #166).
	FollowCardVisibility(Card);
	Actor.Tags.AddUnique(FamilyTag);
	return true;
}

int32 UDinkArtFamilySubsystem::DressInstances(ADinkGreyboxScreen& Screen)
{
	DINK_PERF_SCOPE(Dink_Family_DressInstances);
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
			P.ScriptName = O->ScriptName;
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
			if (UDinkFamilyDuplicatesSubsystem::IsDroppedInstance(*this, O->OriginId.ToString())) continue;  // A208: another copy draws it
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
				DinkPerf::CacheVegetationShadows(*Family, Mesh);   // perf-stutter: as above
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
			FVector Ground = FVector(At.X, At.Y, -Screen.GetActorLocation().Z) - FRotator(0.0, Card.Rotator().Yaw, 0.0).RotateVector(FVector(0.0, Back, 0.0));
			if (Shared->Anchor != EDinkFamilyAnchor::Card)
			{
				// families.json "anchor": stand the mesh on the placement's 1997 hardbox (presentation only, DinkFamilyAnchor.h)
				const UDinkGreyboxSubsystem* Grey = Screen.GetWorld() ? Screen.GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
				const ADinkScreenVolume* Volume = Grey ? Grey->FindScreen(Screen.ScreenNumber) : nullptr;
				FVector Target;
				if (Volume && DinkFamilyAnchor::AnchorWorld(*Volume, Shared->Anchor, O->Sequence, O->Frame, Screen.GetActorTransform().TransformPosition(At),
					Card.GetScale3D().X * 100.0, Yaw - Volume->GetActorRotation().Yaw + Screen.GetActorRotation().Yaw, Bounds.GetSize() * Scale, Target))
				{
					const FVector Local = Screen.GetActorTransform().InverseTransformPosition(Target);
					Ground = FVector(Local.X, Local.Y, -Screen.GetActorLocation().Z);
				}
			}
			// families.json "offset_cm": this one placement stands elsewhere (hangings on the drawn wall)
			if (const FVector* Offset = Shared->OffsetCm.Find(FName(*O->OriginId.ToString()))) Ground += Screen.GetActorTransform().InverseTransformVector(*Offset);
			const FTransform InstanceTransform = DinkArtFamily::SpanTransform(Bounds, Ground, Yaw, Scale, Pieces[PieceIndex]);
			Family->AddInstance(InstanceTransform, /*bWorldSpace*/ false);
			// instance transforms are relative to the screen root, as the family component is (player-only blocker, see above)
			if (O->ScriptName.IsNone()) DinkPlayerBlockers::Add(Screen, *Family, InstanceTransform, Mesh, O->OriginId.ToString());
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
