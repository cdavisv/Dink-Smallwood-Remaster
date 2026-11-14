#include "DinkImportBundle.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
	TSharedPtr<FJsonObject> ReadJson(const FString& Path, FString& OutError)
	{
		FString Text;
		if (!FFileHelper::LoadFileToString(Text, *Path))
		{
			OutError = FString::Printf(TEXT("cannot read %s (run Scripts/export_import_bundle.py)"), *Path);
			return nullptr;
		}
		TSharedPtr<FJsonObject> Root;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
		if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
		{
			OutError = FString::Printf(TEXT("cannot parse %s: %s"), *Path, *Reader->GetErrorMessage());
			return nullptr;
		}
		return Root;
	}

	FString Str(const TSharedPtr<FJsonObject>& O, const TCHAR* Key)
	{
		FString V;
		if (O.IsValid())
		{
			O->TryGetStringField(Key, V);
		}
		return V;
	}

	double Num(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, double Default = 0.0)
	{
		double V = Default;
		if (O.IsValid())
		{
			O->TryGetNumberField(Key, V);
		}
		return V;
	}

	bool Bool(const TSharedPtr<FJsonObject>& O, const TCHAR* Key)
	{
		bool V = false;
		if (O.IsValid())
		{
			O->TryGetBoolField(Key, V);
		}
		return V;
	}

	TSharedPtr<FJsonObject> Obj(const TSharedPtr<FJsonObject>& O, const TCHAR* Key)
	{
		const TSharedPtr<FJsonObject>* V = nullptr;
		return O.IsValid() && O->TryGetObjectField(Key, V) && V ? *V : nullptr;
	}

	FVector2D Vec2(const TArray<TSharedPtr<FJsonValue>>& A)
	{
		return A.Num() >= 2 ? FVector2D(A[0]->AsNumber(), A[1]->AsNumber()) : FVector2D::ZeroVector;
	}

	FVector2D Vec2Field(const TSharedPtr<FJsonObject>& O, const TCHAR* Key)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		return O.IsValid() && O->TryGetArrayField(Key, A) && A ? Vec2(*A) : FVector2D::ZeroVector;
	}

	TArray<FString> StrArray(const TSharedPtr<FJsonObject>& O, const TCHAR* Key)
	{
		TArray<FString> Out;
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (O.IsValid() && O->TryGetArrayField(Key, A) && A)
		{
			for (const TSharedPtr<FJsonValue>& V : *A)
			{
				Out.Add(V->AsString());
			}
		}
		return Out;
	}

	template <typename T>
	FString KeyString(const T& Key)
	{
		if constexpr (std::is_same_v<T, FString>)
		{
			return Key;
		}
		else
		{
			return FString(Key.ToView());
		}
	}

	FIntRect ReadRect(const TArray<TSharedPtr<FJsonValue>>& A)
	{
		return A.Num() >= 4 ? FIntRect((int32)A[0]->AsNumber(), (int32)A[1]->AsNumber(), (int32)A[2]->AsNumber(), (int32)A[3]->AsNumber())
		                    : FIntRect();
	}
}

FString FDinkBundle::DefaultDir()
{
	return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("ImportData"));
}

bool FDinkBundle::Load(const FString& InDir, FString& OutError)
{
	Dir = InDir;
	TSharedPtr<FJsonObject> Manifest = ReadJson(Dir / TEXT("bundle.json"), OutError);
	if (!Manifest)
	{
		return false;
	}
	Schema = Str(Manifest, TEXT("schema"));
	if (!Schema.StartsWith(TEXT("dink-bundle/1")))
	{
		OutError = FString::Printf(TEXT("unsupported bundle schema '%s'"), *Schema);
		return false;
	}
	SourceCommit = Str(Obj(Manifest, TEXT("source")), TEXT("data_repo_commit"));
	BaseMetresPerPixel = Num(Manifest, TEXT("base_m_per_px"), 0.025);
	const TSharedPtr<FJsonObject> Start = Obj(Manifest, TEXT("start"));
	StartScreen = (int32)Num(Start, TEXT("screen"), 1);
	StartX = Num(Start, TEXT("x"));
	StartY = Num(Start, TEXT("y"));
	StartDir = (int32)Num(Start, TEXT("dir"), 4);
	StartWorld = Vec2Field(Start, TEXT("world"));
	StartNote = Str(Start, TEXT("note"));
	Regions = StrArray(Manifest, TEXT("regions"));
	Problems = StrArray(Manifest, TEXT("problems"));
	{
		const TSharedPtr<FJsonObject> Files = Obj(Manifest, TEXT("files"));
		TArray<FString> Keys;
		if (Files)
		{
			for (const auto& Pair : Files->Values)
			{
				Keys.Add(KeyString(Pair.Key));
			}
		}
		Keys.Sort();
		FString Joined;
		for (const FString& K : Keys)
		{
			Joined += K + TEXT("=") + Str(Files, *K) + TEXT(";");
		}
		FilesHash = FMD5::HashAnsiString(*Joined);
	}

	// screens
	{
		TSharedPtr<FJsonObject> Root = ReadJson(Dir / TEXT("screens.json"), OutError);
		if (!Root)
		{
			return false;
		}
		for (const TSharedPtr<FJsonValue>& V : Root->GetArrayField(TEXT("screens")))
		{
			const TSharedPtr<FJsonObject> O = V->AsObject();
			FDinkBundleScreen S;
			S.Id = Str(O, TEXT("id"));
			S.Screen = (int32)Num(O, TEXT("screen"));
			S.Col = (int32)Num(O, TEXT("col"));
			S.Row = (int32)Num(O, TEXT("row"));
			S.Region = Str(O, TEXT("region"));
			S.RegionName = Str(O, TEXT("region_name"));
			S.Name = Str(O, TEXT("name"));
			S.Kind = Str(O, TEXT("kind"));
			S.Sheet = Str(O, TEXT("sheet"));
			S.Group = Str(O, TEXT("group"));
			S.bIndoor = Bool(O, TEXT("indoor"));
			const TSharedPtr<FJsonObject> Music = Obj(O, TEXT("music"));
			S.MusicRaw = (int32)Num(Music, TEXT("raw"));
			S.MusicAction = Str(Music, TEXT("action"));
			S.MusicFile = Str(Music, TEXT("file"));
			S.BaseScript = Str(O, TEXT("base_script"));
			const TSharedPtr<FJsonObject> Enc = Obj(O, TEXT("encounter"));
			S.bScreenlock = Bool(Enc, TEXT("screenlock"));
			S.bLocking = Bool(Enc, TEXT("locking"));
			S.EncounterScripts = StrArray(Enc, TEXT("scripts"));
			if (const TSharedPtr<FJsonObject> Int = Obj(O, TEXT("interior")))
			{
				S.InteriorId = Str(Int, TEXT("id"));
				S.InteriorName = Str(Int, TEXT("name"));
			}
			if (const TSharedPtr<FJsonObject> Vis = Obj(O, TEXT("vision")))
			{
				for (const TSharedPtr<FJsonValue>& VV : Vis->GetArrayField(TEXT("values")))
				{
					S.VisionValues.Add((int32)VV->AsNumber());
				}
				if (const TSharedPtr<FJsonObject> Rules = Obj(Vis, TEXT("rules")))
				{
					for (const auto& Pair : Rules->Values)
					{
						TArray<FString>& Out = S.VisionRules.FindOrAdd(FCString::Atoi(*KeyString(Pair.Key)));
						for (const TSharedPtr<FJsonValue>& R : Pair.Value->AsArray())
						{
							Out.Add(R->AsString());
						}
					}
				}
			}
			const TSharedPtr<FJsonObject> C = Obj(O, TEXT("corners"));
			S.Corners.NW = Vec2Field(C, TEXT("nw"));
			S.Corners.NE = Vec2Field(C, TEXT("ne"));
			S.Corners.SW = Vec2Field(C, TEXT("sw"));
			S.Corners.SE = Vec2Field(C, TEXT("se"));
			S.GroundImage = Str(O, TEXT("ground_image"));
			S.GroundHash = Str(O, TEXT("ground_hash"));
			S.CollisionHash = Str(O, TEXT("collision_hash"));
			S.GroundMask = Str(O, TEXT("ground_mask"));
			S.GroundMaskHash = Str(O, TEXT("ground_mask_hash"));
			{
				const TArray<TSharedPtr<FJsonValue>>* GroundLayerRows = nullptr;
				if (O->TryGetArrayField(TEXT("ground_layers"), GroundLayerRows) && GroundLayerRows)
				{
					for (const TSharedPtr<FJsonValue>& LayerValue : *GroundLayerRows)
					{
						const TSharedPtr<FJsonObject> LayerObject = LayerValue->AsObject();
						FDinkBundleGroundLayer Layer;
						Layer.Name = Str(LayerObject, TEXT("name"));
						Layer.TileCm = Num(LayerObject, TEXT("tile_cm"), 400.0);
						Layer.NormalStrength = Num(LayerObject, TEXT("normal_strength"), 1.0);
						Layer.Backlight = Num(LayerObject, TEXT("backlight"), 0.0);
						Layer.Emissive = Num(LayerObject, TEXT("emissive"), 0.0);
						Layer.Structured = Num(LayerObject, TEXT("structured"), 0.0);
						Layer.Drift = Num(LayerObject, TEXT("drift"), 1.0);
						S.GroundLayers.Add(Layer);
					}
				}
			}
			S.Hash = Str(O, TEXT("hash"));
			S.Excluded = Str(O, TEXT("excluded"));
			ScreenIndex.Add(S.Screen, Screens.Num());
			Screens.Add(MoveTemp(S));
		}
	}

	// placements
	{
		TSharedPtr<FJsonObject> Root = ReadJson(Dir / TEXT("placements.json"), OutError);
		if (!Root)
		{
			return false;
		}
		for (const TSharedPtr<FJsonValue>& V : Root->GetArrayField(TEXT("placements")))
		{
			const TSharedPtr<FJsonObject> O = V->AsObject();
			FDinkBundlePlacement P;
			P.Id = Str(O, TEXT("id"));
			P.Screen = (int32)Num(O, TEXT("screen"));
			P.Index = (int32)Num(O, TEXT("index"));
			P.MapX = Num(O, TEXT("map_x"));
			P.MapY = Num(O, TEXT("map_y"));
			P.World = Vec2Field(O, TEXT("world"));
			P.MPerPx = Num(O, TEXT("m_per_px"));
			P.ScaleX = Num(O, TEXT("scale_x"));
			P.ScaleY = Num(O, TEXT("scale_y"));
			P.RotDeg = Num(O, TEXT("rot_deg"));
			P.Seq = (int32)Num(O, TEXT("seq"));
			P.Frame = (int32)Num(O, TEXT("frame"));
			P.Type = (int32)Num(O, TEXT("type"));
			P.SizePercent = (int32)Num(O, TEXT("size_percent"), 100);
			P.Brain = (int32)Num(O, TEXT("brain"));
			P.Vision = (int32)Num(O, TEXT("vision"));
			P.Kind = Str(O, TEXT("kind"));
			P.Script = Str(O, TEXT("script"));
			P.ScriptKind = Str(O, TEXT("script_kind"));
			P.ClassId = Str(O, TEXT("class_id"));
			P.Category = Str(O, TEXT("category"));
			P.Name = Str(O, TEXT("name"));
			P.Treatment = Str(O, TEXT("treatment"));
			P.Representation = Str(O, TEXT("representation"));
			P.Group = Str(O, TEXT("group"));
			P.Region = Str(O, TEXT("region"));
			P.Hash = Str(O, TEXT("hash"));
			P.VisionRule = StrArray(O, TEXT("vision_rule"));
			P.bIsWarp = Bool(O, TEXT("is_warp"));
			if (const TSharedPtr<FJsonObject> Card = Obj(O, TEXT("card")))
			{
				P.bHasCard = true;
				P.Card.Sprite = Str(Card, TEXT("sprite"));
				P.Card.ScaleMode = Str(Card, TEXT("scale_mode"));
				P.Card.WidthM = Num(Card, TEXT("width_m"));
				P.Card.HeightM = Num(Card, TEXT("height_m"));
				P.Card.OffsetXM = Num(Card, TEXT("offset_x_m"));
				P.Card.OffsetZM = Num(Card, TEXT("offset_z_m"));
			}
			if (const TSharedPtr<FJsonObject> Hard = Obj(O, TEXT("hardness")))
			{
				P.bHasHardness = true;
				P.HardRect = ReadRect(Hard->GetArrayField(TEXT("rect")));
			}
			Placements.Add(MoveTemp(P));
		}
	}

	// warps
	{
		TSharedPtr<FJsonObject> Root = ReadJson(Dir / TEXT("warps.json"), OutError);
		if (!Root)
		{
			return false;
		}
		for (const TSharedPtr<FJsonValue>& V : Root->GetArrayField(TEXT("warps")))
		{
			const TSharedPtr<FJsonObject> O = V->AsObject();
			FDinkBundleWarp W;
			W.Id = Str(O, TEXT("id"));
			W.Source = Str(O, TEXT("source"));
			W.Placement = Str(O, TEXT("placement"));
			W.TriggerMode = Str(O, TEXT("trigger_mode"));
			W.Kind = Str(O, TEXT("kind"));
			W.Script = Str(O, TEXT("script"));
			W.Note = Str(O, TEXT("note"));
			W.Hash = Str(O, TEXT("hash"));
			W.SrcScreen = (int32)Num(O, TEXT("src_screen"));
			W.DstScreen = (int32)Num(O, TEXT("dst_screen"));
			W.DstX = Num(O, TEXT("dst_x"));
			W.DstY = Num(O, TEXT("dst_y"));
			W.bDstValid = Bool(O, TEXT("dst_valid"));
			W.DstWorld = Vec2Field(O, TEXT("dst_world"));
			W.AnimSeq = (int32)Num(O, TEXT("anim_seq"));
			W.Vision = (int32)Num(O, TEXT("vision"));
			W.ReturnWarps = StrArray(O, TEXT("return_warps"));
			W.bOneWay = Bool(O, TEXT("one_way"));
			const TArray<TSharedPtr<FJsonValue>>* Quad = nullptr;
			if (O->TryGetArrayField(TEXT("trigger_quad"), Quad) && Quad && Quad->Num() == 4)
			{
				W.bHasQuad = true;
				for (int32 I = 0; I < 4; ++I)
				{
					W.Quad[I] = Vec2((*Quad)[I]->AsArray());
				}
			}
			Warps.Add(MoveTemp(W));
		}
	}

	// sprites
	{
		TSharedPtr<FJsonObject> Root = ReadJson(Dir / TEXT("sprites.json"), OutError);
		if (!Root)
		{
			return false;
		}
		for (const auto& Pair : Root->GetObjectField(TEXT("sprites"))->Values)
		{
			const TSharedPtr<FJsonObject> O = Pair.Value->AsObject();
			FDinkBundleSprite S;
			S.Key = KeyString(Pair.Key);
			S.File = Str(O, TEXT("file"));
			S.Hash = Str(O, TEXT("hash"));
			S.Width = (int32)Num(O, TEXT("width"));
			S.Height = (int32)Num(O, TEXT("height"));
			S.TexWidth = (int32)Num(O, TEXT("tex_width"));
			S.TexHeight = (int32)Num(O, TEXT("tex_height"));
			Sprites.Add(S.Key, MoveTemp(S));
		}
	}

	// collision
	{
		TSharedPtr<FJsonObject> Root = ReadJson(Dir / TEXT("collision.json"), OutError);
		if (!Root)
		{
			return false;
		}
		for (const auto& ScreenPair : Root->GetObjectField(TEXT("screens"))->Values)
		{
			FDinkBundleCollision& C = Collision.Add(KeyString(ScreenPair.Key));
			for (const auto& ClassPair : ScreenPair.Value->AsObject()->Values)
			{
				TArray<FIntRect>& Rects = C.ByClass.Add(KeyString(ClassPair.Key));
				const TArray<TSharedPtr<FJsonValue>>& Arr = ClassPair.Value->AsArray();
				Rects.Reserve(Arr.Num());
				for (const TSharedPtr<FJsonValue>& R : Arr)
				{
					Rects.Add(ReadRect(R->AsArray()));
				}
			}
		}
	}

	if (Screens.Num() == 0 || Placements.Num() == 0)
	{
		OutError = TEXT("bundle has no screens or placements");
		return false;
	}
	return true;
}
