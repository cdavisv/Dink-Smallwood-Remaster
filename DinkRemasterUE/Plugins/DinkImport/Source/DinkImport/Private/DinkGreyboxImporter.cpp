#include "DinkGreyboxImporter.h"
#include "DinkGreyboxAssets.h"
#include "DinkHardnessFoundationBuilder.h"
#include "DinkArtFamilySubsystem.h"
#include "Hardness/DinkHardnessFoundationSource.h"
#include "DinkImportBundle.h"
#include "DinkImportLog.h"
#include "DinkCollision.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkLayout.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkGreyboxCharacter.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"

#include "Components/BoxComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EditorLevelUtils.h"
#include "Engine/CollisionProfile.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/Level.h"
#include "Engine/LevelStreaming.h"
#include "Engine/LevelStreamingAlwaysLoaded.h"
#include "Engine/PostProcessVolume.h"
#include "Components/VolumetricCloudComponent.h"
#include "Materials/MaterialInterface.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/SavePackage.h"
#include "Components/SkyAtmosphereComponent.h"
#include "FileHelpers.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"

DEFINE_LOG_CATEGORY(LogDinkImport);

// Outdoor lighting constants of the photoreal pass; bump the env actor hash suffix (sun/N ...) when changing.
namespace DinkEnv
{
	const double SunPitch = -42.0;          // 42 degrees above the horizon
	const double SunYaw = -55.0;            // light travels north-east: an afternoon sun in the south-west
	const float SunIntensity = 10.f;        // scene-referred; see the note at the env actors
	const float SunKelvin = 5700.f;
	const float SunSourceAngle = 0.75f;     // degrees; real sun 0.53, slightly wide for softer distant penumbra
	const float ContactShadowLength = 0.035f;
	const float CloudShadowStrength = 0.55f;
	const float SunVolumetricScattering = 1.f;
	const float SkyLightIntensity = 1.0f;        // physical ratio to the sun; 1.5 over-filled shade (foliage calibration against Cycles, 12 Nov 2026)
	const FLinearColor SkyLowerHemisphere(0.11f, 0.105f, 0.075f);
	const double PlanetTopZ = -10000.0;     // cm
	const float MieScatteringScale = 0.0045f;
	const float AerialPerspectiveScale = 2.5f;
	const float CloudBottomKm = 2.2f;
	const float CloudHeightKm = 3.5f;
	const float FogDensity = 0.004f;
	const FLinearColor FogInscatter(0.42f, 0.52f, 0.68f);     // horizon-sky luminance in scene units
	const FLinearColor FogSunInscatter(0.70f, 0.60f, 0.45f);  // forward glow towards the sun
	const float FogHeightFalloff = 0.12f;
	const float VolumetricFogDistance = 9000.f;
	const float ExposureMinEV = -6.f;            // -2.5 clamped the house interior to black
	const float ExposureMaxEV = 2.4f;
	const float ExposureBias = 0.f;             // was 0.4: with the darker, calibrated foliage the metering lifted meadow scenes until the sky washed out
	const float BloomIntensity = 0.28f;
	const float VignetteIntensity = 0.22f;
	const float FilmToe = 0.55f;
	const float Saturation = 0.96f;
	const float Contrast = 1.f;
	const float LocalExposureShadow = 0.8f;      // local exposure: lift shade (backlit figures, banks)
	const float LocalExposureHighlight = 0.9f;
	const float LumenFinalGatherQuality = 2.f;
	const float LumenSceneDetail = 2.f;
	const float LumenReflectionQuality = 1.5f;
}

namespace
{
	using namespace DinkGreybox;

	/** Bump when the way actors are configured changes, to force every generated actor to respawn. */
	const TCHAR* ActorGeneratorVersion = TEXT("greybox-actors/3");

	const FName TagGenerated(TEXT("DinkGenerated"));
	const TCHAR* TagKeyPrefix = TEXT("DinkKey=");
	const TCHAR* TagHashPrefix = TEXT("DinkHash=");

	/** Extra size of a walk-in warp trigger around its (solid) hardbox, so the overlap fires on contact. */
	constexpr double WarpTriggerPadCm = 30.0;
	constexpr double WarpTriggerHalfHeightCm = 150.0;
	constexpr double EdgeWallHalfThicknessCm = 10.0;
	constexpr double EdgeWallHalfHeightCm = 150.0;

	FString TagValue(const AActor* A, const TCHAR* Prefix)
	{
		for (const FName& T : A->Tags)
		{
			FString S = T.ToString();
			if (S.StartsWith(Prefix))
			{
				return S.Mid(FCString::Strlen(Prefix));
			}
		}
		return FString();
	}

	void SetGeneratedTags(AActor* A, const FString& Key, const FString& Hash)
	{
		A->Tags = {TagGenerated, FName(*(FString(TagKeyPrefix) + Key)), FName(*(FString(TagHashPrefix) + Hash))};
	}

	struct FFittedScreen
	{
		FDinkHardnessFoundationSource Source;
		FDinkHardnessFoundationCandidate Candidate;
        TSet<FString> PictureKeys;
	};

	// Pure source preflight completes for every explicit rule before any native
	// foundation is loaded/built. Dry runs need no generated packages.
	bool PrepareFittedGeneration(const FDinkBundle& Bundle, const TSet<int32>& Selected,
		TMap<int32, FFittedScreen>& Screens, TMap<FString, const FDinkBundlePlacement*>& Promoted,
		FString& Error, const FString& Families = DinkArtFamily::DefaultFamiliesPath())
	{
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *Families))
		{
			Error = TEXT("cannot read families manifest: ") + Families;
			return false;
		}

		TArray<FDinkFamilyCollisionFitRule> Rules;
		FDinkReleasedFamilyVisualBinding ReleasedVisual;
		if (!DinkFamilyCollisionFit::ParsePolicy(Text, Rules, Error) ||
            !DinkFamilyCollisionFit::ParseReleasedVisual(Text, ReleasedVisual, Error)) return false;
		TArray<FDinkFamilyBinding> Bindings;
		TArray<FString> BindingErrors;
		if (!DinkArtFamily::ParseFamilies(Text, Bindings, BindingErrors) || !BindingErrors.IsEmpty())
		{
			Error = TEXT("invalid family bindings: ") + FString::Join(BindingErrors, TEXT("; "));
			return false;
		}
		// ParsePolicy returns no rows for an absent optional policy. Only the
		// original v1 pair has rows without a pinned source hash.
		if (Rules.IsEmpty() || Rules[0].SourceHash.IsEmpty()) return true;

		const auto Precedence = FDinkFamilyPrecedence::LoadDirectory(FPaths::GetPath(Families), FPaths::GetCleanFilename(Families));
		TMap<FString, const FDinkBundlePlacement*> Placements;
		for (const auto& Placement : Bundle.Placements) Placements.Add(Placement.Id, &Placement);

		for (const auto& Rule : Rules)
		{
			const FString Id = Rule.Origin.ToString();
			const auto* Screen = Bundle.FindScreen(Rule.Origin.Screen);
			if (!Screen || !Screen->Excluded.IsEmpty())
			{
				Error = TEXT("fitted source screen missing or excluded: ") + Id;
				return false;
			}
			const auto* Placement = Placements.FindRef(Id);
			if (!Placement || Placement->Screen != Rule.Origin.Screen || Placement->Index != Rule.Origin.Placement ||
				!Placement->Hash.Equals(Rule.SourceHash, ESearchCase::IgnoreCase) ||
				Placement->Type != Rule.SourceType || FName(*Placement->Script) != Rule.SourceScript ||
				Placement->Representation != (Rule.IsStaticBackground() ? TEXT("instance") : TEXT("actor")) ||
				Placement->ClassId != TEXT("barrel") || Placement->Seq != 173 || Placement->Frame != 1 ||
				Placement->Brain != 0 || Placement->Vision != 0 || Placement->bIsWarp ||
				!Placement->bHasHardness || !Placement->bHasCard)
			{
				Error = TEXT("fitted source placement mismatch: ") + Id;
				return false;
			}

			FDinkFamilyPlacement FamilyPlacement;
			FamilyPlacement.Origin = Id;
			FamilyPlacement.Screen = Placement->Screen;
			FamilyPlacement.Sequence = Placement->Seq;
			FamilyPlacement.ClassId = FName(*Placement->ClassId);
			FamilyPlacement.bScripted = !Placement->Script.IsEmpty();
			FamilyPlacement.bHardnessOnly = Placement->Kind == TEXT("hardness_only");
			const FDinkFamilyBinding* Binding = nullptr;
			if (DinkArtFamily::Decide(FamilyPlacement, Precedence, Bindings, Binding) != EDinkFamilyDecision::Bound ||
				!Binding || Binding->Mesh != Rule.Mesh || Binding->Fit != EDinkFamilyFit::None ||
				!Binding->bScripted || Binding->bYawFromSprite)
			{
				Error = TEXT("fitted source conflicts with family or authored precedence: ") + Id;
				return false;
			}

			// A partial import selects foundations only for its region. Every
			// explicit rule still has to match the complete bundle.
			if (Selected.Contains(Rule.Origin.Screen) && Rule.IsStaticBackground()) Promoted.Add(Id, Placement);
			if (Screens.Contains(Placement->Screen)) continue;

			auto& Prepared = Screens.Add(Placement->Screen);
			const FString Descriptor = FPaths::ProjectContentDir() / FString::Printf(
				TEXT("Dink/Data/Gameplay/Hardness/Foundations/SCR_%03d.json"), Placement->Screen);
			if (!FDinkHardnessFoundationSource::Load(Descriptor, Placement->Screen, Prepared.Source, Error) ||
				!Prepared.Source.VerifyGameplayInputs(Error))
				return false;
			auto& Candidate = Prepared.Candidate;
			Candidate.Screen = Placement->Screen;
			Candidate.CollisionSourceHash = Prepared.Source.CollisionSourceHash;
			Candidate.Pivot = FAssetSet::ScreenPivot(*Screen);
			const auto* Collision = Bundle.Collision.Find(Screen->Id);
			const TArray<FIntRect> Empty;
			const auto* SolidFill = Collision ? Collision->ByClass.Find(TEXT("fill_solid")) : nullptr;
			const auto* WaterFill = Collision ? Collision->ByClass.Find(TEXT("fill_water")) : nullptr;
			if (!Collision || Prepared.Source.CollisionSourceHash != Screen->CollisionHash ||
				!(Prepared.Source.Corners == Screen->Corners) ||
				Prepared.Source.SolidFill != (SolidFill ? *SolidFill : Empty) ||
				Prepared.Source.WaterFill != (WaterFill ? *WaterFill : Empty))
			{
				Error = TEXT("foundation descriptor differs from bundle source: ") + Screen->Id;
				return false;
			}
		}
		for (auto It = Screens.CreateIterator(); It; ++It)
			if (!Selected.Contains(It.Key())) It.RemoveCurrent();
        // Require every nonempty canonical frame before any foundation/native write.
        FString FrameText;
        if(!FFileHelper::LoadFileToString(FrameText,*(FPaths::ProjectContentDir()/TEXT("Dink/Data/Gameplay/frames.csv"))))
        {Error=TEXT("missing source frame metadata for fitted release pictures");return false;}
        TSet<int32> SourceSequences;
        for(const auto& Rule:Rules)if(Selected.Contains(Rule.Origin.Screen))
            for(const auto& Placement:Bundle.Placements)if(Placement.Id==Rule.Origin.ToString())SourceSequences.Add(Placement.Seq);
        TArray<FString> FrameLines;FrameText.ParseIntoArrayLines(FrameLines);
        TSet<int32> FoundSequences;
        for(int32 I=1;I<FrameLines.Num();++I)
        {
            TArray<FString> Fields;FrameLines[I].ParseIntoArray(Fields,TEXT(","),false);
            if(Fields.Num()<12||!SourceSequences.Contains(FCString::Atoi(*Fields[0])))continue;
            const int32 Seq=FCString::Atoi(*Fields[0]),Frame=FCString::Atoi(*Fields[1]);
            FoundSequences.Add(Seq);
            if(FCString::Atoi(*Fields[9])!=0||FCString::Atoi(*Fields[10])<=0||FCString::Atoi(*Fields[11])<=0)continue;
            if(Fields.Num()<15||Fields[12].IsEmpty()||Fields[13].IsEmpty()||Fields[14].Len()!=40)
            {Error=TEXT("missing canonical release picture pivot/descriptor");return false;}
            FDinkLegacyPictureDescriptor Descriptor;Descriptor.Sequence=Seq;Descriptor.Frame=Frame;
            Descriptor.Width=FCString::Atoi(*Fields[10]);Descriptor.Height=FCString::Atoi(*Fields[11]);
            Descriptor.OriginX=FCString::Atoi(*Fields[12]);Descriptor.OriginY=FCString::Atoi(*Fields[13]);Descriptor.Sha1=Fields[14];
            if(!DinkFamilyCollisionFit::ValidatePictureDescriptor(Descriptor))
            {Error=TEXT("invalid canonical release picture descriptor");return false;}
            const FString Key=FString::Printf(TEXT("%d_%02d"),Seq,Frame);
            const auto* Picture=Bundle.Sprites.Find(Key);
            if(!Picture||Picture->Width!=FCString::Atoi(*Fields[10])||Picture->Height!=FCString::Atoi(*Fields[11]))
            {Error=TEXT("missing/mismatched ordinary release picture in bundle: ")+Key;return false;}
            for(auto& Pair:Screens)Pair.Value.PictureKeys.Add(Key);
        }
        if(FoundSequences.Num()!=SourceSequences.Num())
        {Error=TEXT("missing canonical fitted release sequence");return false;}
		return true;
	}

	bool ResolveFittedFoundations(const FDinkBundle& Bundle, TMap<int32, FFittedScreen>& Screens,
		TArray<TStrongObjectPtr<UStaticMesh>>& KeepMeshes, TArray<UStaticMesh*>& NewMeshes, FString& Error)
	{
		TArray<int32> Numbers; Screens.GetKeys(Numbers); Numbers.Sort();
		TArray<int32> Missing;
		for (int32 Number : Numbers)
		{
			auto& Prepared = Screens[Number];
			auto& Candidate = Prepared.Candidate;
			const FString SolidPackage = FPackageName::ObjectPathToPackageName(Prepared.Source.SolidMesh);
			const FString LowPackage = SolidPackage.Replace(TEXT("FixedSolidV1"), TEXT("FixedLowV1"));
			auto Exists = [](const FString& Package)
			{ return FindPackage(nullptr, *Package) || FPackageName::DoesPackageExist(Package); };
			const bool SolidExists = Exists(SolidPackage), LowExists = Exists(LowPackage);
			if (!SolidExists && !LowExists) { Missing.Add(Number); continue; }
			if (!SolidExists || LowExists != !Prepared.Source.LowMesh.IsEmpty())
			{
				Error = TEXT("partial or unexpected immutable foundation targets; refusing overwrite: ") + SolidPackage;
				return false;
			}
			Candidate.FixedSolid = LoadObject<UStaticMesh>(nullptr, *Prepared.Source.SolidMesh);
			Candidate.FixedLow = Prepared.Source.LowMesh.IsEmpty() ? nullptr : LoadObject<UStaticMesh>(nullptr, *Prepared.Source.LowMesh);
			if (Candidate.FixedSolid) KeepMeshes.Emplace(Candidate.FixedSolid);
			if (Candidate.FixedLow) KeepMeshes.Emplace(Candidate.FixedLow);
			if (!VerifyRuntimeHardnessFoundationSourceV1(Bundle, Candidate, Error)) return false;
		}
		// No invalid later source/existing package can follow the first producer.
		for (int32 Number : Missing)
		{
			auto& Prepared = Screens[Number];
			if (!BuildRuntimeHardnessFoundationV1(Bundle, Number, Prepared.Candidate, Error) ||
				!VerifyRuntimeHardnessFoundationSourceV1(Bundle, Prepared.Candidate, Error)) return false;
			if (!Prepared.Candidate.FixedSolid || Prepared.Candidate.FixedSolid->GetPathName() != Prepared.Source.SolidMesh ||
				GetPathNameSafe(Prepared.Candidate.FixedLow) != (Prepared.Source.LowMesh.IsEmpty() ? TEXT("None") : Prepared.Source.LowMesh))
			{ Error = TEXT("foundation producer path differs from preflight descriptor"); return false; }
			KeepMeshes.Emplace(Prepared.Candidate.FixedSolid); NewMeshes.Add(Prepared.Candidate.FixedSolid);
			if (Prepared.Candidate.FixedLow)
			{ KeepMeshes.Emplace(Prepared.Candidate.FixedLow); NewMeshes.Add(Prepared.Candidate.FixedLow); }
		}
		return true;
	}

	struct FDesiredActor
	{
		FString Key;
		FString Hash;
		FString Group;   // "" = persistent level
		FString Folder;
		FTransform Transform;
		TArray<FName> AdditionalTags;
		TFunction<AActor*(UWorld&, ULevel&, const FTransform&)> Spawn;
	};

	struct FCoverageRow
	{
		FString OriginId, Type, Screen, Region, Became, Unreal, Detail;
	};

	FString CsvField(const FString& In)
	{
		if (In.Contains(TEXT(",")) || In.Contains(TEXT("\"")) || In.Contains(TEXT("\n")))
		{
			return TEXT("\"") + In.Replace(TEXT("\""), TEXT("\"\"")) + TEXT("\"");
		}
		return In;
	}

	FVector QuadCentreCm(const FVector2D Q[4])
	{
		return DinkLayout::MetresToUnreal((Q[0] + Q[1] + Q[2] + Q[3]) * 0.25);
	}

	/** Oriented box (centre, yaw, half extents in cm) around a near-parallelogram quad in metres. */
	void QuadBox(const FVector2D Q[4], double PadCm, double HalfHeightCm, FVector& OutCentre, FRotator& OutRot, FVector& OutExtent)
	{
		const FVector2D AxisX = ((Q[1] - Q[0]) + (Q[2] - Q[3])) * 0.5;
		const FVector2D AxisY = ((Q[3] - Q[0]) + (Q[2] - Q[1])) * 0.5;
		OutCentre = QuadCentreCm(Q) + FVector(0, 0, HalfHeightCm);
		OutRot = FRotator(0.0, FMath::RadiansToDegrees(FMath::Atan2(AxisX.Y, AxisX.X)), 0.0);
		OutExtent = FVector(AxisX.Size() * 50.0 + PadCm, AxisY.Size() * 50.0 + PadCm, HalfHeightCm);
	}

	FTransform PlacementTransform(const FDinkBundlePlacement& P, const FDinkBundleScreen& S)
	{
		const double Yaw = DinkLayout::LocalEastYawDegrees(S.Corners, P.MapX, P.MapY);
		return FTransform(FRotator(0.0, Yaw, 0.0), DinkLayout::MetresToUnreal(P.World));
	}

	FTransform CardRelative(const FDinkBundleCard& C)
	{
		return FTransform(FRotator::ZeroRotator, FVector(C.OffsetXM * 100.0, 0.0, C.OffsetZM * 100.0), FVector(C.WidthM, 1.0, C.HeightM));
	}

	ULevelStreaming* FindStreaming(UWorld* World, const FString& Package)
	{
		for (ULevelStreaming* LS : World->GetStreamingLevels())
		{
			if (LS && LS->GetWorldAssetPackageName() == Package)
			{
				return LS;
			}
		}
		return nullptr;
	}
}

FString FDinkGreyboxImporter::PascalCase(const FString& Key)
{
	TArray<FString> Parts;
	Key.ParseIntoArray(Parts, TEXT("_"));
	FString Out;
	for (FString& P : Parts)
	{
		if (!P.IsEmpty())
		{
			Out += P.Left(1).ToUpper() + P.Mid(1);
		}
	}
	return Out;
}

FString FDinkGreyboxImporter::MapPackageFor(const FString& Region)
{
	const FString Name = Region == TEXT("all") ? TEXT("World") : PascalCase(Region);
	return FString(GeneratedRoot) + TEXT("/Maps/L_Greybox_") + Name;
}

FString FDinkGreyboxImporter::SublevelPackageFor(const FString& Region, const FString& Group)
{
	return MapPackageFor(Region) + TEXT("_") + PascalCase(Group);
}

FDinkGreyboxImportResult FDinkGreyboxImporter::Run(const FDinkGreyboxImportOptions& Options)
{
	FDinkGreyboxImportResult Result;
	const double T0 = FPlatformTime::Seconds();
	auto Fail = [&](const FString& Error)
	{
		Result.bOk = false;
		Result.Error = Error;
		UE_LOG(LogDinkImport, Error, TEXT("%s"), *Error);
		return Result;
	};

	// ------------------------------------------------------------------ bundle and selection
	FDinkBundle Bundle;
	FString Error;
	if (!Bundle.Load(Options.BundleDir.IsEmpty() ? FDinkBundle::DefaultDir() : Options.BundleDir, Error))
	{
		return Fail(TEXT("bundle: ") + Error);
	}
	const FString Region = Options.Region.ToLower();
	const bool bAll = Region == TEXT("all");
	if (!bAll && !Bundle.Regions.Contains(Region))
	{
		return Fail(FString::Printf(TEXT("unknown region '%s'; regions in the bundle: %s, or all"), *Region, *FString::Join(Bundle.Regions, TEXT(", "))));
	}
	TSet<int32> Selected;
	TArray<FString> Groups;
	for (const FDinkBundleScreen& S : Bundle.Screens)
	{
		if ((bAll || S.Region == Region) && S.Excluded.IsEmpty())
		{
			Selected.Add(S.Screen);
			Groups.AddUnique(S.Group);
		}
	}
	Groups.Sort();
	Result.MapPackage = MapPackageFor(Region);
	UE_LOG(LogDinkImport, Display, TEXT("import %s: %d screens in groups %s (bundle from data repo %s)"), *Region, Selected.Num(),
		*FString::Join(Groups, TEXT(", ")), *Bundle.SourceCommit);

	TMap<FString, const FDinkBundleWarp*> SpriteWarpByPlacement;
	for (const FDinkBundleWarp& W : Bundle.Warps)
	{
		if (W.Source == TEXT("sprite"))
		{
			SpriteWarpByPlacement.Add(W.Placement, &W);
		}
	}

	TMap<int32, FFittedScreen> FittedScreens;
	TMap<FString, const FDinkBundlePlacement*> PromotedBarrels;
	TArray<TStrongObjectPtr<UStaticMesh>> KeepFittedMeshes;
	TArray<UStaticMesh*> NewFoundationMeshes;
	if (!PrepareFittedGeneration(Bundle, Selected, FittedScreens, PromotedBarrels, Error))
		return Fail(TEXT("fitted generation preflight: ") + Error);
	if (!Options.bDryRun && !ResolveFittedFoundations(Bundle, FittedScreens, KeepFittedMeshes, NewFoundationMeshes, Error))
		return Fail(TEXT("fitted foundation generation: ") + Error);

	// ------------------------------------------------------------------ assets
	FAssetSet Assets(Bundle);
	Assets.LoadManifest();
	if (!Options.bDryRun)
	{
		if (!Assets.EnsureShared(Error))
		{
			return Fail(TEXT("shared assets: ") + Error);
		}
		TSet<FString> SpriteKeys;
		for (const FDinkBundlePlacement& P : Bundle.Placements)
		{
			if (Selected.Contains(P.Screen) && P.bHasCard)
			{
				SpriteKeys.Add(P.Card.Sprite);
			}
		}
        for(const auto& Screen:FittedScreens)for(const FString& Key:Screen.Value.PictureKeys)SpriteKeys.Add(Key);
		TArray<FString> SortedKeys = SpriteKeys.Array();
		SortedKeys.Sort();
		for (const FString& Key : SortedKeys)
		{
			if (!Assets.EnsureSprite(Key, Error))
			{
				return Fail(TEXT("sprite assets: ") + Error);
			}
		}
		int32 Done = 0;
		for (const FDinkBundleScreen& S : Bundle.Screens)
		{
			if (!Selected.Contains(S.Screen))
			{
				continue;
			}
			if (!Assets.EnsureScreen(S, Error))
			{
				return Fail(TEXT("screen assets: ") + Error);
			}
			if (++Done % 50 == 0)
			{
				UE_LOG(LogDinkImport, Display, TEXT("  screen assets %d/%d"), Done, Selected.Num());
			}
		}
		if (bAll)
		{
			Assets.DeleteOrphans();
		}
		if (!Assets.SaveAll(Error))
		{
			return Fail(TEXT("saving assets: ") + Error);
		}
	}
	Result.AssetsCreated = Assets.Stats().Created + NewFoundationMeshes.Num();
	Result.AssetsUpdated = Assets.Stats().Updated;
	Result.AssetsDeleted = Assets.Stats().Deleted;
	Result.AssetsUnchanged = Assets.Stats().Unchanged;
	UE_LOG(LogDinkImport, Display, TEXT("assets: %d created, %d updated, %d unchanged, %d deleted"), Result.AssetsCreated,
		Result.AssetsUpdated, Result.AssetsUnchanged, Result.AssetsDeleted);

	// ------------------------------------------------------------------ desired actors
	TArray<FDesiredActor> Desired;
	TArray<FCoverageRow> Coverage;
	const FString MapShort = FPackageName::GetShortName(Result.MapPackage);

	UStaticMesh* CardMesh = nullptr;
	auto GetCard = [&]()
	{
		if (!CardMesh)
		{
			CardMesh = Assets.CardMesh();
		}
		return CardMesh;
	};

	// screens: volume + greybox geometry
	for (const FDinkBundleScreen& S : Bundle.Screens)
	{
		if (!Selected.Contains(S.Screen))
		{
			Coverage.Add({S.Id, TEXT("screen"), S.Id, S.Region, TEXT("skipped"), TEXT(""),
				S.Excluded.IsEmpty() ? FString::Printf(TEXT("not in region import '%s'"), *Region) : S.Excluded});
			continue;
		}
		const FString Folder = FString::Printf(TEXT("%s/%s"), *FDinkGreyboxImporter::PascalCase(S.Group), *S.Id);

		// edge walls where the grid neighbour is missing, on another sheet, or not imported
		struct FEdge
		{
			int32 DCol, DRow;
			FVector2D A, B;
		};
		const FEdge Edges[4] = {
			{0, -1, S.Corners.NW, S.Corners.NE}, {1, 0, S.Corners.NE, S.Corners.SE},
			{0, 1, S.Corners.SE, S.Corners.SW}, {-1, 0, S.Corners.SW, S.Corners.NW}};
		bool bWall[4];
		FString WallKey;
		for (int32 E = 0; E < 4; ++E)
		{
			const int32 C = S.Col + Edges[E].DCol, R = S.Row + Edges[E].DRow;
			const FDinkBundleScreen* N = (C >= 0 && C < 32 && R >= 0 && R < 24) ? Bundle.FindScreen(R * 32 + C + 1) : nullptr;
			bWall[E] = !N || N->Sheet != S.Sheet || !Selected.Contains(N->Screen);
			WallKey += bWall[E] ? TEXT("1") : TEXT("0");
		}

		FVector2D Min(S.Corners.NW), Max(S.Corners.NW);
		for (const FVector2D& P : {S.Corners.NE, S.Corners.SW, S.Corners.SE})
		{
			Min = FVector2D(FMath::Min(Min.X, P.X), FMath::Min(Min.Y, P.Y));
			Max = FVector2D(FMath::Max(Max.X, P.X), FMath::Max(Max.Y, P.Y));
		}
		const FVector VolumeCentre = DinkLayout::MetresToUnreal((Min + Max) * 0.5, 5.0);
		const FVector VolumeExtent((Max.X - Min.X) * 50.0, (Max.Y - Min.Y) * 50.0, 500.0);

		{
			FDesiredActor D;
			D.Key = S.Id + TEXT(":Screen");
			D.Hash = HashStrings({ActorGeneratorVersion, S.Hash, WallKey});
			D.Group = S.Group;
			D.Folder = Folder;
			D.Transform = FTransform(VolumeCentre);
			const FDinkBundleScreen* SP = &S;
			TArray<bool> Walls = {bWall[0], bWall[1], bWall[2], bWall[3]};
			D.Spawn = [SP, Walls, Edges, VolumeExtent](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
			{
				FActorSpawnParameters P;
				P.OverrideLevel = &Level;
				P.bNoFail = true;
				ADinkScreenVolume* A = World.SpawnActor<ADinkScreenVolume>(ADinkScreenVolume::StaticClass(), T, P);
				const FDinkBundleScreen& S = *SP;
				A->Bounds->SetBoxExtent(VolumeExtent);
				A->ScreenNumber = S.Screen;
				A->ScreenId = FName(*S.Id);
				A->Region = FName(*S.Region);
				A->RegionName = S.RegionName;
				A->AreaName = S.Name;
				A->Kind = FName(*S.Kind);
				A->Sheet = FName(*S.Sheet);
				A->bIndoor = S.bIndoor;
				A->MusicRaw = S.MusicRaw;
				A->MusicAction = FName(*S.MusicAction);
				A->MusicFile = S.MusicFile;
				A->BaseScript = S.BaseScript.IsEmpty() ? NAME_None : FName(*S.BaseScript);
				A->bEncounter = S.bScreenlock;
				A->bLocksScreen = S.bLocking;
				for (const FString& E : S.EncounterScripts)
				{
					A->EncounterScripts.Add(FName(*E));
				}
				A->InteriorId = S.InteriorId.IsEmpty() ? NAME_None : FName(*S.InteriorId);
				A->InteriorName = S.InteriorName;
				A->VisionValues = S.VisionValues;
				for (const int32 V : S.VisionValues)
				{
					if (const TArray<FString>* Rules = S.VisionRules.Find(V))
					{
						for (const FString& R : *Rules)
						{
							A->VisionRules.Add(FString::Printf(TEXT("vision %d: %s"), V, *R));
						}
					}
				}
				A->Corners = S.Corners;
				const FVector2D Centre = DinkLayout::MapPixelToMetres(S.Corners, 300, 200);
				for (int32 E = 0; E < 4; ++E)
				{
					UBoxComponent* Wall = A->EdgeWalls[E];
					if (!Walls[E])
					{
						continue;
					}
					const FVector2D Mid = (Edges[E].A + Edges[E].B) * 0.5;
					const FVector2D Dir = Edges[E].B - Edges[E].A;
					FVector2D Out(Dir.Y, -Dir.X);
					Out.Normalize();
					if (FVector2D::DotProduct(Out, Mid - Centre) < 0)
					{
						Out = -Out;
					}
					Wall->SetWorldLocationAndRotation(DinkLayout::MetresToUnreal(Mid) + FVector(Out.X, Out.Y, 0) * EdgeWallHalfThicknessCm + FVector(0, 0, EdgeWallHalfHeightCm),
						FRotator(0.0, FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X)), 0.0));
					Wall->SetBoxExtent(FVector(Dir.Size() * 50.0 + EdgeWallHalfThicknessCm, EdgeWallHalfThicknessCm, EdgeWallHalfHeightCm));
					Wall->SetCollisionProfileName(DinkCollision::ProfileHardSolid);
				}
				return A;
			};
			Desired.Add(MoveTemp(D));
		}

		// greybox geometry + background decoration as instances
		TArray<const FDinkBundlePlacement*> Instanced;
		for (const FDinkBundlePlacement& P : Bundle.Placements)
		{
			if (P.Screen == S.Screen && P.Representation == TEXT("instance") && !PromotedBarrels.Contains(P.Id))
			{
				Instanced.Add(&P);
			}
		}
		{
			TArray<FString> HashParts = {ActorGeneratorVersion, S.Hash, S.CollisionHash};
			for (const FDinkBundlePlacement* P : Instanced)
			{
				HashParts.Add(P->Hash);
			}
			const auto* Fitted = FittedScreens.Find(S.Screen);
			if (Fitted) HashParts.Add(Fitted->Source.SourceTextSha1);
			FDesiredActor D;
			HashParts.Add(TEXT("greybox-ground-water-debug-split/1"));
			D.Key = S.Id + TEXT(":Greybox");
			D.Hash = HashStrings(HashParts);
			D.Group = S.Group;
			D.Folder = Folder;
			D.Transform = FTransform(FAssetSet::ScreenPivot(S));
			const FDinkBundleScreen* SP = &S;
			D.Spawn = [SP, Instanced, Fitted, &Assets, GetCard, &Bundle](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
			{
				FActorSpawnParameters P;
				P.OverrideLevel = &Level;
				P.bNoFail = true;
				ADinkGreyboxScreen* A = World.SpawnActor<ADinkGreyboxScreen>(ADinkGreyboxScreen::StaticClass(), T, P);
				const FDinkBundleScreen& S = *SP;
				A->ScreenNumber = S.Screen;
				A->Visual->SetStaticMesh(Assets.ScreenMesh(S.Screen, TEXT("Visual")));
				A->DebugBlockers->SetStaticMesh(Assets.ScreenMesh(S.Screen, TEXT("DebugBlockers")));
				if (Fitted)
				{
					A->CollisionSolid->SetStaticMesh(Fitted->Candidate.FixedSolid);
					A->CollisionLow->SetStaticMesh(Fitted->Candidate.FixedLow);
					A->CollisionSolid->ComponentTags.AddUnique(TEXT("DinkHardnessFixedFloorFillV1"));
					A->CollisionLow->ComponentTags.AddUnique(TEXT("DinkHardnessFixedWaterV1"));
				}
				else
				{
					A->CollisionSolid->SetStaticMesh(Assets.ScreenMesh(S.Screen, TEXT("CollSolid")));
					A->CollisionLow->SetStaticMesh(Assets.ScreenMesh(S.Screen, TEXT("CollLow")));
				}
				const FVector Pivot = T.GetLocation();
				TMap<FString, UInstancedStaticMeshComponent*> ByKey;
				for (const FDinkBundlePlacement* Pl : Instanced)
				{
					UInstancedStaticMeshComponent*& ISM = ByKey.FindOrAdd(Pl->Card.Sprite);
					const FString CompName = TEXT("Decor_") + Pl->Card.Sprite;
					if (!ISM)
					{
						ISM = NewObject<UInstancedStaticMeshComponent>(A, FName(*CompName), RF_Transactional);
						ISM->SetupAttachment(A->GetRootComponent());
						ISM->SetMobility(EComponentMobility::Static);
						ISM->SetStaticMesh(GetCard());
						ISM->SetMaterial(0, Assets.SpriteMaterial(Pl->Card.Sprite));
						ISM->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
						ISM->SetCanEverAffectNavigation(false);
						A->AddInstanceComponent(ISM);
						ISM->RegisterComponent();
					}
					const FTransform Place = PlacementTransform(*Pl, S);
					const FTransform CardWorld = CardRelative(Pl->Card) * Place;
					const FTransform Local(CardWorld.GetRotation(), CardWorld.GetLocation() - Pivot, CardWorld.GetScale3D());
					const int32 Index = ISM->AddInstance(Local, /*bWorldSpace*/ false);
					FDinkInstanceOrigin O;
					FDinkOriginId::Parse(Pl->Id, O.OriginId);
					O.ScriptName = Pl->Script.IsEmpty() ? NAME_None : FName(*Pl->Script);
					O.Sequence = Pl->Seq;
					O.Frame = Pl->Frame;
					O.ClassId = FName(*Pl->ClassId);
					O.Category = FName(*Pl->Category);
					O.ComponentName = FName(*CompName);
					O.InstanceIndex = Index;
					O.SourceHash = Pl->Hash;
					A->InstanceOrigins->Origins.Add(O);
				}
				return A;
			};
			Desired.Add(MoveTemp(D));
		}
		Coverage.Add({S.Id, TEXT("screen"), S.Id, S.Region, TEXT("screen_volume+greybox"), S.Id + TEXT(":Screen, ") + S.Id + TEXT(":Greybox"),
			FString::Printf(TEXT("%s/%s; %s%s; music %d; walls %s"), *MapShort, *FDinkGreyboxImporter::PascalCase(S.Group), *S.Kind,
				S.bIndoor ? TEXT(" indoor") : TEXT(""), S.MusicRaw, *WallKey)});
	}

	// placements
	for (const FDinkBundlePlacement& P : Bundle.Placements)
	{
		const FDinkBundleScreen* S = Bundle.FindScreen(P.Screen);
		if (!S || !Selected.Contains(P.Screen))
		{
			Coverage.Add({P.Id, TEXT("placement"), FString::Printf(TEXT("SCR_%03d"), P.Screen), P.Region, TEXT("skipped"), TEXT(""),
				S && !S->Excluded.IsEmpty() ? S->Excluded : FString::Printf(TEXT("screen not in region import '%s'"), *Region)});
			continue;
		}
		const bool PromoteBarrel = PromotedBarrels.Contains(P.Id);
		if (P.Representation == TEXT("instance") && !PromoteBarrel)
		{
			Result.PlacementInstances++;
			Coverage.Add({P.Id, TEXT("placement"), S->Id, P.Region, TEXT("instance"), S->Id + TEXT(":Greybox/Decor_") + P.Card.Sprite,
				FString::Printf(TEXT("background (type 0) %s %s"), *P.ClassId, *P.Category)});
			continue;
		}
		Result.PlacementActors++;
		const FDinkBundleWarp* Warp = P.bIsWarp ? SpriteWarpByPlacement.FindRef(P.Id) : nullptr;
		const bool bDestIn = Warp && Warp->bDstValid && Selected.Contains(Warp->DstScreen);
		FDesiredActor D;
		D.Key = P.Id;
		D.Hash = HashStrings({ActorGeneratorVersion, P.Hash, Warp ? Warp->Hash : FString(), bDestIn ? TEXT("dest-in") : TEXT("dest-out")});
		if (PromoteBarrel)
		{
			D.AdditionalTags.Add(DinkFamilyCollisionFit::PromotedBackgroundTag);
			D.Hash = HashStrings({D.Hash, TEXT("fitted-background-actor/1")});
		}

		D.Group = P.Group;
		D.Folder = FString::Printf(TEXT("%s/%s%s"), *FDinkGreyboxImporter::PascalCase(S->Group), *S->Id,
			P.Vision ? *FString::Printf(TEXT("/Vision_%d"), P.Vision) : TEXT(""));
		D.Transform = PlacementTransform(P, *S);
		const FDinkBundlePlacement* PP = &P;
		D.Spawn = [PP, Warp, bDestIn, &Assets, GetCard](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
		{
			const FDinkBundlePlacement& P = *PP;
			FActorSpawnParameters SP;
			SP.OverrideLevel = &Level;
			SP.bNoFail = true;
			UClass* Class = Warp ? ADinkWarpPlaceholderActor::StaticClass() : ADinkPlaceholderActor::StaticClass();
			ADinkPlaceholderActor* A = World.SpawnActor<ADinkPlaceholderActor>(Class, T, SP);
			UDinkOriginComponent* O = A->Origin;
			FDinkOriginId::Parse(P.Id, O->OriginId);
			O->ScriptName = P.Script.IsEmpty() ? NAME_None : FName(*P.Script);
			O->SourceHash = P.Hash;
			O->Sequence = P.Seq;
			O->Frame = P.Frame;
			O->PlacementType = P.Type;
			O->ClassId = FName(*P.ClassId);
			O->Category = FName(*P.Category);
			O->ScriptKind = P.ScriptKind.IsEmpty() ? NAME_None : FName(*P.ScriptKind);
			A->DisplayName = P.Name;
			A->Treatment = FName(*P.Treatment);
			A->PlacementKind = FName(*P.Kind);
			A->Brain = P.Brain;
			A->ScreenNumber = P.Screen;
			A->bHasHardness = P.bHasHardness;
			A->Vision = P.Vision;
			if (P.Vision != 0)
			{
				A->VisionCondition = FDinkFactCondition(TEXT("vision"), EDinkCompareOp::Equal, P.Vision);
				A->VisionRules = P.VisionRule;
			}
			if (P.bHasCard)
			{
				A->CardScaleMode = FName(*P.Card.ScaleMode);
				A->Card->SetStaticMesh(GetCard());
				A->Card->SetMaterial(0, Assets.SpriteMaterial(P.Card.Sprite));
				A->ImportedCardRelativeTransform=CardRelative(P.Card);
                A->bHasImportedCardBaseline=true;
                A->Card->SetRelativeTransform(A->ImportedCardRelativeTransform);
				A->Card->SetHiddenInGame(P.Kind == TEXT("hardness_only"));
			}
			if (Warp)
			{
				UDinkWarpComponent* W = CastChecked<ADinkWarpPlaceholderActor>(A)->Warp;
				W->WarpId = Warp->Id;
				W->Source = FName(*Warp->Source);
				W->Kind = FName(*Warp->Kind);
				W->TriggerMode = FName(*Warp->TriggerMode);
				W->Script = Warp->Script.IsEmpty() ? NAME_None : FName(*Warp->Script);
				W->SourceScreen = Warp->SrcScreen;
				W->DestScreen = Warp->DstScreen;
				W->DestMapPixel = FVector2D(Warp->DstX, Warp->DstY);
				W->DestLocation = DinkLayout::MetresToUnreal(Warp->DstWorld);
				W->AnimSequence = Warp->AnimSeq;
				W->bOneWay = Warp->bOneWay;
				W->ReturnWarps = Warp->ReturnWarps;
				W->bTriggerEnabled = bDestIn;
				W->Note = bDestIn ? Warp->Note : FString::Printf(TEXT("disabled: destination SCR_%03d is not part of this import"), Warp->DstScreen);
				if (Warp->bHasQuad)
				{
					FVector C;
					FRotator R;
					FVector E;
					QuadBox(Warp->Quad, WarpTriggerPadCm, WarpTriggerHalfHeightCm, C, R, E);
					W->SetWorldLocationAndRotation(C, R);
					W->SetBoxExtent(E);
				}
			}
			return A;
		};
		Desired.Add(MoveTemp(D));
		FString Became = Warp ? TEXT("actor+warp") : TEXT("actor");
		FString Detail = FString::Printf(TEXT("%s %s %s"), *P.Kind, *P.ClassId, *P.Category);
		if (PromoteBarrel) Detail += TEXT(" (source type 0 represented by a fitted actor)");
		if (P.Vision)
		{
			Detail += FString::Printf(TEXT("; vision %d (hidden until &vision = %d): %s"), P.Vision, P.Vision, *FString::Join(P.VisionRule, TEXT(" | ")));
		}
		if (!P.bHasCard)
		{
			Detail += TEXT("; no picture (seq 0 / missing frame): marker only");
		}
		Coverage.Add({P.Id, TEXT("placement"), S->Id, P.Region, Became, P.Id, Detail});
	}

	// warps: sprite warps live on their placement actor; script warps get their own actors
	for (const FDinkBundleWarp& W : Bundle.Warps)
	{
		const FDinkBundleScreen* S = Bundle.FindScreen(W.SrcScreen);
		if (!S || !Selected.Contains(W.SrcScreen))
		{
			Coverage.Add({W.Id, TEXT("warp"), FString::Printf(TEXT("SCR_%03d"), W.SrcScreen), S ? S->Region : FString(), TEXT("skipped"), TEXT(""),
				FString::Printf(TEXT("source screen not in region import '%s'"), *Region)});
			continue;
		}
		Result.Warps++;
		const bool bDestIn = W.bDstValid && Selected.Contains(W.DstScreen);
		const FString DestText = FString::Printf(TEXT("-> SCR_%03d (%.0f,%.0f)%s"), W.DstScreen, W.DstX, W.DstY, bDestIn ? TEXT("") : TEXT(" [destination not imported: trigger disabled]"));
		if (W.Source == TEXT("sprite"))
		{
			Coverage.Add({W.Id, TEXT("warp"), S->Id, S->Region, TEXT("warp trigger on placement actor"), W.Placement, W.Kind + TEXT(" ") + DestText});
			continue;
		}
		FDesiredActor D;
		D.Key = W.Id;
		D.Hash = HashStrings({ActorGeneratorVersion, W.Hash, bDestIn ? TEXT("dest-in") : TEXT("dest-out")});
		D.Group = S->Group;
		D.Folder = FString::Printf(TEXT("%s/%s"), *FDinkGreyboxImporter::PascalCase(S->Group), *S->Id);
		FVector Centre;
		FRotator Rot;
		FVector Extent;
		if (W.bHasQuad)
		{
			QuadBox(W.Quad, WarpTriggerPadCm, WarpTriggerHalfHeightCm, Centre, Rot, Extent);
		}
		else
		{
			Centre = DinkLayout::MapPixelToUnreal(S->Corners, 300, 200, 1.5);
			Rot = FRotator::ZeroRotator;
			Extent = FVector(100, 100, WarpTriggerHalfHeightCm);
		}
		D.Transform = FTransform(Rot, Centre);
		const FDinkBundleWarp* WP = &W;
		D.Spawn = [WP, bDestIn, Extent](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
		{
			const FDinkBundleWarp& W = *WP;
			FActorSpawnParameters SP;
			SP.OverrideLevel = &Level;
			SP.bNoFail = true;
			ADinkScriptWarpActor* A = World.SpawnActor<ADinkScriptWarpActor>(ADinkScriptWarpActor::StaticClass(), T, SP);
			UDinkWarpComponent* C = A->Warp;
			C->SetBoxExtent(Extent);
			C->WarpId = W.Id;
			C->Source = FName(*W.Source);
			C->Kind = FName(*W.Kind);
			C->TriggerMode = FName(*W.TriggerMode);
			C->Script = FName(*W.Script);
			C->SourceScreen = W.SrcScreen;
			C->DestScreen = W.DstScreen;
			C->DestMapPixel = FVector2D(W.DstX, W.DstY);
			C->DestLocation = DinkLayout::MetresToUnreal(W.DstWorld);
			C->bOneWay = W.bOneWay;
			C->ReturnWarps = W.ReturnWarps;
			C->bTriggerEnabled = bDestIn && W.TriggerMode != TEXT("script_only");
			C->Note = bDestIn ? W.Note : FString::Printf(TEXT("disabled: destination SCR_%03d is not part of this import. %s"), W.DstScreen, *W.Note);
			return A;
		};
		Desired.Add(MoveTemp(D));
		Coverage.Add({W.Id, TEXT("warp"), S->Id, S->Region,
			W.TriggerMode == TEXT("script_only") ? TEXT("inactive script-warp marker") : TEXT("script warp trigger (touch, approximated)"), W.Id,
			W.Kind + TEXT(" ") + DestText + TEXT("; ") + W.Note});
	}
	Result.Screens = Selected.Num();

	// persistent level: start, lighting, fog
	{
		const FDinkBundleScreen* StartScreen = Bundle.FindScreen(Bundle.StartScreen);
		const bool bStartIn = StartScreen && Selected.Contains(Bundle.StartScreen);
		FVector StartLoc = DinkLayout::MetresToUnreal(Bundle.StartWorld, 1.0);
		if (!bStartIn)
		{
			// region import without the start screen: start in the middle of the first imported screen
			for (const FDinkBundleScreen& S : Bundle.Screens)
			{
				if (Selected.Contains(S.Screen) && !S.bIndoor)
				{
					StartLoc = DinkLayout::MapPixelToUnreal(S.Corners, 300, 200, 1.0);
					break;
				}
			}
		}
		// original direction 4 = west (numpad layout) -> Unreal yaw 180
		const double StartYaw = Bundle.StartDir == 4 ? 180.0 : Bundle.StartDir == 6 ? 0.0 : Bundle.StartDir == 8 ? -90.0 : 90.0;
		FDesiredActor Start;
		Start.Key = TEXT("Env:PlayerStart");
		Start.Hash = HashStrings({ActorGeneratorVersion, TEXT("start"), StartLoc.ToString(), FString::SanitizeFloat(StartYaw)});
		Start.Folder = TEXT("Env");
		Start.Transform = FTransform(FRotator(0, StartYaw, 0), StartLoc);
		Start.Spawn = [](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
		{
			FActorSpawnParameters SP;
			SP.OverrideLevel = &Level;
			SP.bNoFail = true;
			return World.SpawnActor<APlayerStart>(APlayerStart::StaticClass(), T, SP);
		};
		Desired.Add(MoveTemp(Start));

		// --- Photographic outdoor lighting (photoreal pass, 11 Nov 2026). Values were tuned from
		// rendered captures (Saved/PhotorealPass/lighting). Unit convention: the sun stays in the
		// project's scene-referred scale (10 = a clear-sky sun of about 100 klux) because the authored
		// interior lights are 40-170 lm against that scale; sky, clouds and fog all derive from the
		// sun through the atmosphere, so every outdoor ratio is physical.
		FDesiredActor Sun;
		Sun.Key = TEXT("Env:Sun");
		Sun.Hash = HashStrings({ActorGeneratorVersion, TEXT("sun/10")});
		Sun.Folder = TEXT("Env");
		Sun.Transform = FTransform(FRotator(DinkEnv::SunPitch, DinkEnv::SunYaw, 0.0), FVector(0, 0, 1000));
		Sun.Spawn = [](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
		{
			FActorSpawnParameters SP;
			SP.OverrideLevel = &Level;
			SP.bNoFail = true;
			ADirectionalLight* A = World.SpawnActor<ADirectionalLight>(ADirectionalLight::StaticClass(), T, SP);
			UDirectionalLightComponent* L = CastChecked<UDirectionalLightComponent>(A->GetLightComponent());
			L->SetMobility(EComponentMobility::Movable);
			L->SetAtmosphereSunLight(true);
			L->SetIntensity(DinkEnv::SunIntensity);
			L->SetUseTemperature(true);
			L->SetTemperature(DinkEnv::SunKelvin);
			L->SetLightSourceAngle(DinkEnv::SunSourceAngle);
			L->SetLightSourceSoftAngle(0.f);
			L->ContactShadowLength = DinkEnv::ContactShadowLength;
			L->ContactShadowLengthInWS = false;
			L->ContactShadowCastingIntensity = 1.f;
			L->ContactShadowNonCastingIntensity = 0.f;
			L->bCastCloudShadows = true;
			L->CloudShadowStrength = DinkEnv::CloudShadowStrength;
			L->CloudShadowExtent = 60.f;
			L->bCastShadowsOnClouds = true;
			L->bCastShadowsOnAtmosphere = true;
			L->bPerPixelAtmosphereTransmittance = true;
			L->VolumetricScatteringIntensity = DinkEnv::SunVolumetricScattering;
			L->SetIndirectLightingIntensity(1.f);
			L->MarkRenderStateDirty();
			return A;
		};
		Desired.Add(MoveTemp(Sun));

		FDesiredActor Sky;
		Sky.Key = TEXT("Env:SkyLight");
		Sky.Hash = HashStrings({ActorGeneratorVersion, TEXT("sky/11")});
		Sky.Folder = TEXT("Env");
		Sky.Transform = FTransform(FVector(0, 0, 1000));
		Sky.Spawn = [](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
		{
			FActorSpawnParameters SP;
			SP.OverrideLevel = &Level;
			SP.bNoFail = true;
			ASkyLight* A = World.SpawnActor<ASkyLight>(ASkyLight::StaticClass(), T, SP);
			USkyLightComponent* C = A->GetLightComponent();
			C->SetMobility(EComponentMobility::Movable);
			C->bRealTimeCapture = true;
			C->SetIntensity(DinkEnv::SkyLightIntensity);
			C->bLowerHemisphereIsBlack = false;
			C->SetLowerHemisphereColor(DinkEnv::SkyLowerHemisphere);
			C->bCloudAmbientOcclusion = true;
			C->CloudAmbientOcclusionStrength = 0.6f;
			C->VolumetricScatteringIntensity = 1.f;
			return A;
		};
		Desired.Add(MoveTemp(Sky));

		FDesiredActor Atmo;
		Atmo.Key = TEXT("Env:SkyAtmosphere");
		Atmo.Hash = HashStrings({ActorGeneratorVersion, TEXT("atmo/11")});
		Atmo.Folder = TEXT("Env");
		// The planet surface sits 100 m under the grid. With it at z = 0 every surface below ground level
		// (the authored pond banks) was "inside the planet": the sun's per-pixel atmosphere transmittance
		// is zero there, so the banks got no direct light and a grey aerial-perspective veil.
		Atmo.Transform = FTransform(FVector(0, 0, DinkEnv::PlanetTopZ));
		Atmo.Spawn = [](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
		{
			FActorSpawnParameters SP;
			SP.OverrideLevel = &Level;
			SP.bNoFail = true;
			AActor* A = World.SpawnActor<AActor>(AActor::StaticClass(), T, SP);
			USkyAtmosphereComponent* C = NewObject<USkyAtmosphereComponent>(A, TEXT("SkyAtmosphere"), RF_Transactional);
			A->SetRootComponent(C);
			A->AddInstanceComponent(C);
			C->TransformMode = ESkyAtmosphereTransformMode::PlanetTopAtComponentTransform;
			C->MieScatteringScale = DinkEnv::MieScatteringScale;
			C->MieAnisotropy = 0.8f;
			C->MieExponentialDistribution = 1.2f;
			C->AerialPespectiveViewDistanceScale = DinkEnv::AerialPerspectiveScale;
			C->HeightFogContribution = 1.f;
			C->MultiScatteringFactor = 1.f;
			C->RegisterComponent();
			return A;
		};
		Desired.Add(MoveTemp(Atmo));

		FDesiredActor Clouds;
		Clouds.Key = TEXT("Env:VolumetricCloud");
		Clouds.Hash = HashStrings({ActorGeneratorVersion, TEXT("cloud/10")});
		Clouds.Folder = TEXT("Env");
		Clouds.Transform = FTransform::Identity;
		Clouds.Spawn = [](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
		{
			FActorSpawnParameters SP;
			SP.OverrideLevel = &Level;
			SP.bNoFail = true;
			AVolumetricCloud* A = World.SpawnActor<AVolumetricCloud>(AVolumetricCloud::StaticClass(), T, SP);
			UVolumetricCloudComponent* C = A->FindComponentByClass<UVolumetricCloudComponent>();
			UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Dink/Materials/Environment/MI_Env_Clouds.MI_Env_Clouds"));
			if (!Material) Material = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst.m_SimpleVolumetricCloud_Inst"));
			if (C)
			{
				if (Material) C->SetMaterial(Material);
				C->SetLayerBottomAltitude(DinkEnv::CloudBottomKm);
				C->SetLayerHeight(DinkEnv::CloudHeightKm);
				C->SetTracingStartMaxDistance(350.f);
				C->SetTracingMaxDistance(50.f);
				C->SetViewSampleCountScale(1.f);
				C->SetReflectionViewSampleCountScale(0.5f);
				C->SetShadowViewSampleCountScale(1.f);
				C->SetShadowTracingDistance(15.f);
				C->SetbUsePerSampleAtmosphericLightTransmittance(true);
				C->SetSkyLightCloudBottomOcclusion(0.5f);
			}
			return A;
		};
		Desired.Add(MoveTemp(Clouds));

		FDesiredActor Fog;
		Fog.Key = TEXT("Env:HeightFog");
		Fog.Hash = HashStrings({ActorGeneratorVersion, TEXT("fog/12")});
		Fog.Folder = TEXT("Env");
		Fog.Transform = FTransform(FVector(0, 0, 0));
		Fog.Spawn = [](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
		{
			FActorSpawnParameters SP;
			SP.OverrideLevel = &Level;
			SP.bNoFail = true;
			AExponentialHeightFog* A = World.SpawnActor<AExponentialHeightFog>(AExponentialHeightFog::StaticClass(), T, SP);
			UExponentialHeightFogComponent* C = A->GetComponent();
			// Gentle aerial perspective: colour comes from the sky atmosphere (inscattering left black),
			// (explicit horizon colours: the atmosphere-driven fog colour came out black here) a thin ground layer plus a thinner high layer; sight lines stay several hundred metres.
			C->SetFogDensity(DinkEnv::FogDensity);
			C->SetFogHeightFalloff(DinkEnv::FogHeightFalloff);
			// Single layer; a second, higher layer added nothing visible in the captures.
			C->SetSecondFogDensity(0.f);
			C->SetSecondFogHeightFalloff(0.03f);
			C->SetSecondFogHeightOffset(0.f);
			C->SetStartDistance(0.f);
			C->SetFogMaxOpacity(0.92f);
			C->SetFogInscatteringColor(DinkEnv::FogInscatter);
			C->SetDirectionalInscatteringColor(DinkEnv::FogSunInscatter);
			C->SetDirectionalInscatteringExponent(6.f);
			C->SetDirectionalInscatteringStartDistance(2000.f);
			C->SetVolumetricFog(true);
			C->SetVolumetricFogScatteringDistribution(0.65f);
			C->SetVolumetricFogExtinctionScale(1.f);
			C->SetVolumetricFogDistance(DinkEnv::VolumetricFogDistance);
			C->SetVolumetricFogAlbedo(FColor(235, 240, 250));
			return A;
		};
		Desired.Add(MoveTemp(Fog));

		FDesiredActor Post;
		Post.Key = TEXT("Env:PostProcess");
		Post.Hash = HashStrings({ActorGeneratorVersion, TEXT("post/11")});
		Post.Folder = TEXT("Env");
		Post.Transform = FTransform::Identity;
		Post.Spawn = [](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
		{
			FActorSpawnParameters SP;
			SP.OverrideLevel = &Level;
			SP.bNoFail = true;
			APostProcessVolume* A = World.SpawnActor<APostProcessVolume>(APostProcessVolume::StaticClass(), T, SP);
			A->bUnbound = true;
			A->Priority = 0.f;
			A->BlendWeight = 1.f;
			FPostProcessSettings& S = A->Settings;
			// Camera: histogram metering clamped to a photographic range. The upper bound is the
			// "sunny day" exposure, so a bright sky cannot drag the ground dark; the lower bound still
			// lets the authored interiors (their own volume adds a -2 bias) open up.
			S.bOverride_AutoExposureMethod = true;
			S.AutoExposureMethod = AEM_Histogram;
			S.bOverride_AutoExposureMinBrightness = true;
			S.AutoExposureMinBrightness = DinkEnv::ExposureMinEV;
			S.bOverride_AutoExposureMaxBrightness = true;
			S.AutoExposureMaxBrightness = DinkEnv::ExposureMaxEV;
			S.bOverride_AutoExposureBias = true;
			S.AutoExposureBias = DinkEnv::ExposureBias;
			S.bOverride_LocalExposureShadowContrastScale = true;
			S.LocalExposureShadowContrastScale = DinkEnv::LocalExposureShadow;
			S.bOverride_LocalExposureHighlightContrastScale = true;
			S.LocalExposureHighlightContrastScale = DinkEnv::LocalExposureHighlight;
			S.bOverride_AutoExposureSpeedUp = true;
			S.AutoExposureSpeedUp = 2.5f;
			S.bOverride_AutoExposureSpeedDown = true;
			S.AutoExposureSpeedDown = 1.2f;
			S.bOverride_AutoExposureLowPercent = true;
			S.AutoExposureLowPercent = 10.f;
			S.bOverride_AutoExposureHighPercent = true;
			S.AutoExposureHighPercent = 90.f;
			// Lens: slight bloom, subtle vignette, no grain, no chromatic aberration.
			S.bOverride_BloomIntensity = true;
			S.BloomIntensity = DinkEnv::BloomIntensity;
			S.bOverride_BloomThreshold = true;
			S.BloomThreshold = -1.f;
			S.bOverride_VignetteIntensity = true;
			S.VignetteIntensity = DinkEnv::VignetteIntensity;
			S.bOverride_FilmGrainIntensity = true;
			S.FilmGrainIntensity = 0.f;
			S.bOverride_SceneFringeIntensity = true;
			S.SceneFringeIntensity = 0.f;
			S.bOverride_LensFlareIntensity = true;
			S.LensFlareIntensity = 0.f;
			// Film: the engine's ACES-fitted filmic curve with a slightly firmer toe; neutral grade.
			S.bOverride_FilmSlope = true;
			S.FilmSlope = 0.88f;
			S.bOverride_FilmToe = true;
			S.FilmToe = DinkEnv::FilmToe;
			S.bOverride_FilmShoulder = true;
			S.FilmShoulder = 0.26f;
			S.bOverride_FilmBlackClip = true;
			S.FilmBlackClip = 0.f;
			S.bOverride_FilmWhiteClip = true;
			S.FilmWhiteClip = 0.04f;
			S.bOverride_ColorSaturation = true;
			S.ColorSaturation = FVector4(DinkEnv::Saturation, DinkEnv::Saturation, DinkEnv::Saturation, 1.0);
			S.bOverride_ColorContrast = true;
			S.ColorContrast = FVector4(DinkEnv::Contrast, DinkEnv::Contrast, DinkEnv::Contrast, 1.0);
			S.bOverride_WhiteTemp = true;
			S.WhiteTemp = 6500.f;
			// Global illumination and reflections: Lumen (software tracing), raised gather quality.
			S.bOverride_DynamicGlobalIlluminationMethod = true;
			S.DynamicGlobalIlluminationMethod = EDynamicGlobalIlluminationMethod::Lumen;
			S.bOverride_ReflectionMethod = true;
			S.ReflectionMethod = EReflectionMethod::Lumen;
			S.bOverride_LumenFinalGatherQuality = true;
			S.LumenFinalGatherQuality = DinkEnv::LumenFinalGatherQuality;
			S.bOverride_LumenSceneDetail = true;
			S.LumenSceneDetail = DinkEnv::LumenSceneDetail;
			S.bOverride_LumenSceneLightingQuality = true;
			S.LumenSceneLightingQuality = 1.5f;
			S.bOverride_LumenSceneViewDistance = true;
			S.LumenSceneViewDistance = 20000.f;
			S.bOverride_LumenReflectionQuality = true;
			S.LumenReflectionQuality = DinkEnv::LumenReflectionQuality;
			S.bOverride_LumenSkylightLeaking = true;
			S.LumenSkylightLeaking = 0.f;
			S.bOverride_AmbientOcclusionIntensity = true;
			S.AmbientOcclusionIntensity = 0.f; // SSAO off: Lumen's short-range AO does this job
			return A;
		};
		Desired.Add(MoveTemp(Post));

		if (FPackageName::DoesPackageExist(TEXT("/Game/Dink/_Generated/Shared/SM_DinkBackdrop")))
		{
			FDesiredActor Backdrop;
			Backdrop.Key = TEXT("Env:Backdrop");
			Backdrop.Hash = HashStrings({ActorGeneratorVersion, TEXT("backdrop/3")});
			Backdrop.Folder = TEXT("Env");
			// 1.5 m below the grid: under every authored pond bed, so it also closes the void beneath them.
			Backdrop.Transform = FTransform(FVector(0, 0, -150));
			Backdrop.Spawn = [](UWorld& World, ULevel& Level, const FTransform& T) -> AActor*
			{
				FActorSpawnParameters SP;
				SP.OverrideLevel = &Level;
				SP.bNoFail = true;
				AStaticMeshActor* A = World.SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), T, SP);
				A->Tags.Add(TEXT("DinkEnvBackdrop"));
				UStaticMeshComponent* C = A->GetStaticMeshComponent();
				C->SetMobility(EComponentMobility::Movable);
				C->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Dink/_Generated/Shared/SM_DinkBackdrop.SM_DinkBackdrop")));
				C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				C->SetCollisionResponseToAllChannels(ECR_Ignore);
				C->SetGenerateOverlapEvents(false);
				C->SetCanEverAffectNavigation(false);
				C->SetCastShadow(false);
				C->bAffectDistanceFieldLighting = false;
				C->bAffectDynamicIndirectLighting = false;
				C->bReceivesDecals = false;
				return A;
			};
			Desired.Add(MoveTemp(Backdrop));
		}

		Coverage.Add({FString::Printf(TEXT("START")), TEXT("start"), FString::Printf(TEXT("SCR_%03d"), Bundle.StartScreen), StartScreen ? StartScreen->Region : FString(),
			bStartIn ? TEXT("player start") : TEXT("player start (fallback: start screen not imported)"), TEXT("Env:PlayerStart"), Bundle.StartNote});
	}

	if (Options.bDryRun)
	{
		Result.bOk = true;
		Result.Seconds = FPlatformTime::Seconds() - T0;
		UE_LOG(LogDinkImport, Display, TEXT("dry run: %d desired actors; %d fitted screens planned (no native foundation build/save)"), Desired.Num(), FittedScreens.Num());
		return Result;
	}

	// ------------------------------------------------------------------ map and sublevels
	const FString MapFile = FPackageName::LongPackageNameToFilename(Result.MapPackage, FPackageName::GetMapPackageExtension());
	UWorld* World = nullptr;
	bool bPersistentDirty = false;
	if (IFileManager::Get().FileExists(*MapFile))
	{
		World = UEditorLoadingAndSavingUtils::LoadMap(MapFile);
	}
	else
	{
		World = UEditorLoadingAndSavingUtils::NewBlankMap(false);
		if (World && !UEditorLoadingAndSavingUtils::SaveMap(World, Result.MapPackage))
		{
			return Fail(TEXT("cannot save new map ") + Result.MapPackage);
		}
		bPersistentDirty = true;
	}
	if (!World)
	{
		return Fail(TEXT("cannot open map ") + Result.MapPackage);
	}
	if (World->GetWorldSettings()->DefaultGameMode != ADinkGreyboxGameMode::StaticClass())
	{
		World->GetWorldSettings()->DefaultGameMode = ADinkGreyboxGameMode::StaticClass();
		World->GetWorldSettings()->MarkPackageDirty();
		bPersistentDirty = true;
	}

	TMap<FString, ULevel*> GroupLevels;
	GroupLevels.Add(FString(), World->PersistentLevel);
	for (const FString& Group : Groups)
	{
		const FString SubPackage = SublevelPackageFor(Region, Group);
		ULevelStreaming* LS = FindStreaming(World, SubPackage);
		if (!LS)
		{
			const FString SubFile = FPackageName::LongPackageNameToFilename(SubPackage, FPackageName::GetMapPackageExtension());
			if (IFileManager::Get().FileExists(*SubFile))
			{
				LS = UEditorLevelUtils::AddLevelToWorld(World, *SubPackage, ULevelStreamingAlwaysLoaded::StaticClass());
			}
			else
			{
				LS = UEditorLevelUtils::CreateNewStreamingLevelForWorld(*World, ULevelStreamingAlwaysLoaded::StaticClass(), SubFile, false, nullptr, false);
			}
			bPersistentDirty = true;
		}
		ULevel* Level = LS ? LS->GetLoadedLevel() : nullptr;
		if (!Level)
		{
			return Fail(TEXT("cannot create or load sublevel ") + SubPackage);
		}
		GroupLevels.Add(Group, Level);
	}
	// sublevels of groups no longer in this import
	for (ULevelStreaming* LS : TArray<ULevelStreaming*>(World->GetStreamingLevels()))
	{
		bool bWanted = false;
		for (const FString& Group : Groups)
		{
			bWanted |= LS && LS->GetWorldAssetPackageName() == SublevelPackageFor(Region, Group);
		}
		if (LS && !bWanted && LS->GetWorldAssetPackageName().StartsWith(Result.MapPackage + TEXT("_")))
		{
			if (ULevel* L = LS->GetLoadedLevel())
			{
				UEditorLevelUtils::RemoveLevelFromWorld(L, false, false);
			}
			else
			{
				World->RemoveStreamingLevel(LS);
			}
			bPersistentDirty = true;
		}
	}

	// ------------------------------------------------------------------ reconcile actors per level
	TMap<FString, TArray<const FDesiredActor*>> ByGroup;
	for (const FDesiredActor& D : Desired)
	{
		ByGroup.FindOrAdd(D.Group).Add(&D);
	}
	TArray<ULevel*> DirtyLevels;
	for (const auto& GL : GroupLevels)
	{
		ULevel* Level = GL.Value;
		TMap<FString, AActor*> Existing;
		TArray<AActor*> Duplicates;
		for (AActor* A : Level->Actors)
		{
			if (!IsValid(A) || A->IsA<AWorldSettings>() || A->HasAnyFlags(RF_Transient))
			{
				continue;
			}
			if (A->Tags.Contains(TagGenerated))
			{
				const FString Key = TagValue(A, TagKeyPrefix);
				if (Existing.Contains(Key))
				{
					Duplicates.Add(A);
				}
				else
				{
					Existing.Add(Key, A);
				}
			}
			else if (!A->IsA<ABrush>())
			{
				Result.ForeignActors++;
				UE_LOG(LogDinkImport, Display, TEXT("leaving foreign (hand-placed) actor alone: %s (%s)"), *A->GetActorNameOrLabel(), *A->GetClass()->GetName());
			}
		}
		int32 Changes = 0;
		for (AActor* A : Duplicates)
		{
			World->EditorDestroyActor(A, false);
			Result.ActorsDeleted++;
			Changes++;
		}
		const TArray<const FDesiredActor*>* Wanted = ByGroup.Find(GL.Key);
		TSet<FString> WantedKeys;
		if (Wanted)
		{
			for (const FDesiredActor* D : *Wanted)
			{
				WantedKeys.Add(D->Key);
				AActor** Found = Existing.Find(D->Key);
				if (Found && *Found)
				{
					const bool bSameHash = TagValue(*Found, TagHashPrefix) == D->Hash;
					const FTransform Have = (*Found)->GetActorTransform();
					const bool bSameTransform = Have.GetLocation().Equals(D->Transform.GetLocation(), 0.01) &&
						Have.GetScale3D().Equals(D->Transform.GetScale3D(), 1e-4) &&
						Have.GetRotation().AngularDistance(D->Transform.GetRotation()) < 1e-4;  // q and -q are the same rotation
					if (bSameHash && bSameTransform)
					{
						Result.ActorsUnchanged++;
						continue;
					}
					if (bSameHash && !bSameTransform)
					{
						Result.ActorsMovedByHand++;
						UE_LOG(LogDinkImport, Warning, TEXT("drift: %s was moved in the editor (%s, want %s); resetting it"), *D->Key,
							*Have.ToString(), *D->Transform.ToString());
					}
					World->EditorDestroyActor(*Found, false);
					Result.ActorsUpdated++;
				}
				else
				{
					Result.ActorsCreated++;
				}
				AActor* A = D->Spawn(*World, *Level, D->Transform);
				if (!A)
				{
					return Fail(TEXT("failed to spawn ") + D->Key);
				}
				if (A->GetRootComponent())
				{
					// some engine actors (directional light) ignore the spawn transform's rotation/scale
					A->GetRootComponent()->SetWorldTransform(D->Transform);
				}
				SetGeneratedTags(A, D->Key, D->Hash);
				A->Tags.Append(D->AdditionalTags);
				A->SetActorLabel(D->Key);
				A->SetFolderPath(FName(*D->Folder));
				A->MarkPackageDirty();
				Changes++;
			}
		}
		for (const auto& Pair : Existing)
		{
			if (!WantedKeys.Contains(Pair.Key) && Pair.Value)
			{
				UE_LOG(LogDinkImport, Display, TEXT("deleting generated actor no longer in the import: %s"), *Pair.Key);
				World->EditorDestroyActor(Pair.Value, false);
				Result.ActorsDeleted++;
				Changes++;
			}
		}
		if (Changes > 0)
		{
			DirtyLevels.Add(Level);
		}
	}

	if (!FittedScreens.IsEmpty())
	{
		TMap<int32, ADinkGreyboxScreen*> Hosts;
		TMap<int32, ADinkScreenVolume*> Volumes;
		for (TActorIterator<ADinkGreyboxScreen> It(World); It; ++It)
		{
			if (It->InstanceOrigins)
			{
				for (const auto& Instance : It->InstanceOrigins->Origins)
					if (PromotedBarrels.Contains(Instance.OriginId.ToString()))
						return Fail(TEXT("fitted background origin also remains an instance"));
			}
			if (!FittedScreens.Contains(It->ScreenNumber)) continue;
			if (Hosts.Contains(It->ScreenNumber)) return Fail(TEXT("duplicate fitted screen host"));
			Hosts.Add(It->ScreenNumber, *It);
		}
		for (TActorIterator<ADinkScreenVolume> It(World); It; ++It)
		{
			if (!FittedScreens.Contains(It->ScreenNumber)) continue;
			if (Volumes.Contains(It->ScreenNumber)) return Fail(TEXT("duplicate fitted screen volume"));
			Volumes.Add(It->ScreenNumber, *It);
		}
		TSet<FString> FoundPromotions;
		for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
		{
			const auto* Origin = It->Origin.Get();
			if (!Origin) continue;
			const FString Id = Origin->OriginId.ToString();
			const auto* Placement = PromotedBarrels.FindRef(Id);
			if (!Placement) continue;
			if (FoundPromotions.Contains(Id) || Origin->PlacementType != 0 ||
				!It->ActorHasTag(DinkFamilyCollisionFit::PromotedBackgroundTag) ||
				Origin->SourceHash != Placement->Hash || Origin->ScriptName != FName(*Placement->Script))
				return Fail(TEXT("generated fitted background origin differs: ") + Id);
			FoundPromotions.Add(Id);
		}
		if (FoundPromotions.Num() != PromotedBarrels.Num())
			return Fail(TEXT("generated fitted background origin missing"));

		for (const auto& Pair : FittedScreens)
		{
			auto* Host = Hosts.FindRef(Pair.Key);
			auto* Volume = Volumes.FindRef(Pair.Key);
			const auto& Fitted = Pair.Value;
			if (!Host || !Volume || !Host->CollisionSolid || !Host->CollisionLow)
				return Fail(TEXT("missing generated fitted screen host/volume"));
			if (!VerifyRuntimeHardnessFoundationInstanceV1(Bundle, Fitted.Candidate, *Host->CollisionSolid,
				Host->CollisionLow.Get(), Error) || !Fitted.Source.VerifyInstances(*Volume, *Host, Error, false))
				return Fail(TEXT("generated fitted screen verification: ") + Error);
		}
		for (const auto& Pair : Hosts)
		{
			auto* Host = Pair.Value;
			if (Host->ActorHasTag(TEXT("DinkHardnessWorldV1"))) continue;
			Host->Tags.Add(TEXT("DinkHardnessWorldV1"));
			Host->MarkPackageDirty();
			DirtyLevels.AddUnique(Host->GetLevel());
		}
	}

	// All selected generated hosts, actual registered foundation triangles and
	// source descriptors passed above. Save only newly built immutable assets,
	// before worlds can persist references to them; valid existing assets stay untouched.
	for (UStaticMesh* Mesh : NewFoundationMeshes)
	{
		UPackage* Package = Mesh->GetOutermost();
		const FString File = FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension());
		if (IFileManager::Get().FileExists(*File)) return Fail(TEXT("new foundation destination appeared during import: ") + File);
		FSavePackageArgs SaveArgs; SaveArgs.TopLevelFlags = RF_Public | RF_Standalone; SaveArgs.SaveFlags = SAVE_NoError;
		if (!UPackage::SavePackage(Package, Mesh, *File, SaveArgs)) return Fail(TEXT("failed to save generated foundation: ") + File);
	}

	// ------------------------------------------------------------------ save
	for (ULevel* Level : DirtyLevels)
	{
		if (Level == World->PersistentLevel)
		{
			bPersistentDirty = true;
			continue;
		}
		if (!FEditorFileUtils::SaveLevel(Level))
		{
			return Fail(TEXT("failed to save sublevel ") + Level->GetOutermost()->GetName());
		}
		Result.LevelsSaved++;
	}
	if (bPersistentDirty)
	{
		if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
		{
			return Fail(TEXT("failed to save map ") + Result.MapPackage);
		}
		Result.LevelsSaved++;
	}

	// ------------------------------------------------------------------ coverage + report
	const FString ImportDir = FPaths::ProjectSavedDir() / TEXT("Import");
	IFileManager::Get().MakeDirectory(*ImportDir, true);
	Coverage.Sort([](const FCoverageRow& A, const FCoverageRow& B) { return A.Type != B.Type ? A.Type < B.Type : A.OriginId < B.OriginId; });
	FString Csv = TEXT("origin_id,type,screen,region,became,unreal,detail\n");
	for (const FCoverageRow& R : Coverage)
	{
		Csv += FString::Printf(TEXT("%s,%s,%s,%s,%s,%s,%s\n"), *CsvField(R.OriginId), *CsvField(R.Type), *CsvField(R.Screen), *CsvField(R.Region),
			*CsvField(R.Became), *CsvField(R.Unreal), *CsvField(R.Detail));
	}
	FFileHelper::SaveStringToFile(Csv, *(ImportDir / TEXT("coverage.csv")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	FFileHelper::SaveStringToFile(Csv, *(ImportDir / FString::Printf(TEXT("coverage_%s.csv"), *Region)), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);

	Result.Seconds = FPlatformTime::Seconds() - T0;
	Result.bOk = true;
	const FString Report = FString::Printf(TEXT(
		"{\n  \"region\": \"%s\",\n  \"map\": \"%s\",\n  \"bundle_commit\": \"%s\",\n  \"screens\": %d,\n  \"placement_actors\": %d,\n"
		"  \"placement_instances\": %d,\n  \"warps\": %d,\n  \"actors\": {\"created\": %d, \"updated\": %d, \"deleted\": %d, \"unchanged\": %d, \"moved_by_hand\": %d, \"foreign\": %d},\n"
		"  \"assets\": {\"created\": %d, \"updated\": %d, \"deleted\": %d, \"unchanged\": %d},\n  \"levels_saved\": %d,\n  \"drift\": %d,\n  \"seconds\": %.1f,\n"
		"  \"coverage_rows\": %d\n}\n"),
		*Region, *Result.MapPackage, *Bundle.SourceCommit, Result.Screens, Result.PlacementActors, Result.PlacementInstances, Result.Warps,
		Result.ActorsCreated, Result.ActorsUpdated, Result.ActorsDeleted, Result.ActorsUnchanged, Result.ActorsMovedByHand, Result.ForeignActors,
		Result.AssetsCreated, Result.AssetsUpdated, Result.AssetsDeleted, Result.AssetsUnchanged, Result.LevelsSaved, Result.Drift(), Result.Seconds,
		Coverage.Num());
	FFileHelper::SaveStringToFile(Report, *(ImportDir / FString::Printf(TEXT("import_%s.json"), *Region)), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	return Result;
}

#if WITH_DEV_AUTOMATION_TESTS
#include "Tests/DinkFittedGenerationPreflightTests.inl"
#endif
