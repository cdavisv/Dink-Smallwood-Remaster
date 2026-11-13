#include "DinkGameplay.h"
#include "Hardness/DinkRuntimeHardnessSource.h"
#include "DinkCombat.h"
#include "DinkDirector.h"
#include "DinkArtSubsystem.h"
#include "DinkFactSubsystem.h"
#include "DinkWorldStateSubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Algo/StableSort.h"
#include "DinkInventoryComponent.h"
#include "DinkStorySubsystem.h"
#include "DinkNarrativeTypes.h"
#include "Dom/JsonObject.h"
#include "GameFramework/Actor.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
	const FName NAME_Hit(TEXT("hit"));
	const FName NAME_Die(TEXT("die"));
	const FName NAME_DuckDie(TEXT("duckdie"));
	const FName NAME_Touch(TEXT("touch"));
	const FName NAME_Push(TEXT("push"));
	const FName NAME_Use(TEXT("use"));
	const FName NAME_Arm(TEXT("arm"));
	const FName NAME_Disarm(TEXT("disarm"));
	const FName NAME_Pickup(TEXT("pickup"));
	const FName NAME_Drop(TEXT("drop"));
	const FName NAME_HoldingDrop(TEXT("holdingdrop"));
	const FName NAME_Damage(TEXT("damage"));
	const FName NAME_Main(TEXT("main"));
	const FName NAME_Raise(TEXT("raise"));
	const FName P_Brain(TEXT("brain")), P_Hitpoints(TEXT("hitpoints")), P_Strength(TEXT("strength")), P_Defense(TEXT("defense")),
		P_Exp(TEXT("exp")), P_NoHit(TEXT("nohit")), P_TouchDamage(TEXT("touch_damage")), P_Range(TEXT("range")),
		P_BaseAttack(TEXT("base_attack")), P_Target(TEXT("target")), P_Seq(TEXT("seq")), P_Frame(TEXT("frame")),
		P_PSeq(TEXT("pseq")), P_PFrame(TEXT("pframe")), P_Size(TEXT("size")), P_BrainParm(TEXT("brain_parm")),
		P_BrainParm2(TEXT("brain_parm2")), P_Speed(TEXT("speed")), P_Mx(TEXT("mx")), P_My(TEXT("my")),
		P_BaseWalk(TEXT("base_walk")), P_BaseHit(TEXT("base_hit")), P_Follow(TEXT("follow"));

	/** inside_box (dink.cpp): inclusive on all sides. */
	bool Inside(int32 X, int32 Y, int32 L, int32 T, int32 R, int32 B)
	{
		return X >= L && X <= R && Y >= T && Y <= B;
	}

}

// ---------------------------------------------------------------------------------------------
// Data

FString FDinkGameplayData::GetDataPath(const TCHAR* File)
{
	return FPaths::ProjectContentDir() / TEXT("Dink/Data/Gameplay") / File;
}

bool FDinkGameplayData::Load(FString* OutError)
{
	Frames.Reset();
	FrameCounts.Reset();
	Placements.Reset();
	ByScreen.Reset();
	BaseScripts.Reset();
	InitSequences.Reset();
	auto Fail = [OutError](const FString& Message)
	{
		if (OutError)
		{
			*OutError = Message;
		}
		return false;
	};
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *GetDataPath(TEXT("frames.csv"))))
	{
		return Fail(TEXT("cannot read ") + GetDataPath(TEXT("frames.csv")) + TEXT(" (run Scripts/sync_gameplay_data.py)"));
	}
	TArray<FString> Lines;
	Text.ParseIntoArrayLines(Lines);
	for (int32 i = 1; i < Lines.Num(); ++i)
	{
		TArray<FString> F;
		Lines[i].ParseIntoArray(F, TEXT(","), false);
		if (F.Num() < 8)
		{
			continue;
		}
		const int32 Seq = FCString::Atoi(*F[0]);
		const int32 Frame = FCString::Atoi(*F[1]);
		FDinkFrameInfo Info;
		Info.DelayMs = FCString::Atoi(*F[2]);
		Info.bSpecial = FCString::Atoi(*F[3]) != 0;
		Info.Left = FCString::Atoi(*F[4]);
		Info.Top = FCString::Atoi(*F[5]);
		Info.Right = FCString::Atoi(*F[6]);
		Info.Bottom = FCString::Atoi(*F[7]);
		Info.bLoop = F.Num() > 8 && FCString::Atoi(*F[8]) != 0;
		Info.bEmpty = F.Num() > 9 && FCString::Atoi(*F[9]) != 0;
		Info.Width = F.Num() > 10 ? FCString::Atoi(*F[10]) : 0;
		Info.Height = F.Num() > 11 ? FCString::Atoi(*F[11]) : 0;
        if(F.Num()>=15&&!F[12].IsEmpty()&&!F[13].IsEmpty())
        {Info.OriginX=FCString::Atoi(*F[12]);Info.OriginY=FCString::Atoi(*F[13]);Info.PictureDescriptorSha1=F[14];}
		Frames.Add(Key(Seq, Frame), Info);
		int32& Count = FrameCounts.FindOrAdd(Seq);
		Count = FMath::Max(Count, Frame);
	}

	Text.Reset();
	if (!FFileHelper::LoadFileToString(Text, *GetDataPath(TEXT("placements.csv"))))
	{
		return Fail(TEXT("cannot read ") + GetDataPath(TEXT("placements.csv")) + TEXT(" (run Scripts/sync_gameplay_data.py)"));
	}
	Lines.Reset();
	Text.ParseIntoArrayLines(Lines);
	if (Lines.Num() < 2)
	{
		return Fail(TEXT("placements.csv is empty"));
	}
	TArray<FString> Header;
	Lines[0].ParseIntoArray(Header, TEXT(","), false);
	TMap<FString, int32> Col;
	for (int32 c = 0; c < Header.Num(); ++c)
	{
		Col.Add(Header[c], c);
	}
	for (int32 i = 1; i < Lines.Num(); ++i)
	{
		TArray<FString> F;
		Lines[i].ParseIntoArray(F, TEXT(","), false);
		auto Int = [&F, &Col](const TCHAR* Name, int32 Default = 0)
		{
			const int32* C = Col.Find(Name);
			return C && F.IsValidIndex(*C) && !F[*C].IsEmpty() ? FCString::Atoi(*F[*C]) : Default;
		};
		const int32* OriginCol = Col.Find(TEXT("origin"));
		FDinkPlacementInfo P;
		if (!OriginCol || !F.IsValidIndex(*OriginCol) || !FDinkOriginId::Parse(F[*OriginCol], P.Origin))
		{
			continue;
		}
		P.Type = Int(TEXT("type"));
		P.X = Int(TEXT("x"));
		P.Y = Int(TEXT("y"));
		P.Seq = Int(TEXT("seq"));
		P.Frame = Int(TEXT("frame"));
		P.Size = Int(TEXT("size"), 100);
		P.Vision = Int(TEXT("vision"));
		P.Brain = Int(TEXT("brain"));
		const int32* ScriptCol = Col.Find(TEXT("script"));
		if (ScriptCol && F.IsValidIndex(*ScriptCol) && !F[*ScriptCol].IsEmpty())
		{
			P.Script = FName(*F[*ScriptCol].ToLower());
		}
		P.Hitpoints = Int(TEXT("hitpoints"));
		P.Strength = Int(TEXT("strength"));
		P.Defense = Int(TEXT("defense"));
		P.Exp = Int(TEXT("exp"));
		P.NoHit = Int(TEXT("nohit"));
		P.TouchDamage = Int(TEXT("touch_damage"));
		P.Speed = Int(TEXT("speed"));
		P.Timing = Int(TEXT("timing"));
		P.BaseWalk = Int(TEXT("base_walk"), -1);
		P.BaseIdle = Int(TEXT("base_idle"), -1);
		P.BaseAttack = Int(TEXT("base_attack"), -1);
		P.BaseHit = Int(TEXT("base_hit"));
		P.BaseDie = Int(TEXT("base_die"), -1);
		P.Hard = Int(TEXT("hard"));
		P.Sound = Int(TEXT("sound"));
		P.Que = Int(TEXT("que"));
		P.bHasQueSource = Col.Contains(TEXT("que"));
		P.Prop = Int(TEXT("prop"));
		P.WarpMap = Int(TEXT("warp_map"));
		ByScreen.FindOrAdd(P.Origin.Screen).Add(P.Origin);
		Placements.Add(P.Origin, P);
	}
	Text.Reset();
	if (FFileHelper::LoadFileToString(Text, *GetDataPath(TEXT("screens.csv"))))
	{
		Lines.Reset();
		Text.ParseIntoArrayLines(Lines);
		for (int32 i = 1; i < Lines.Num(); ++i)
		{
			TArray<FString> F;
			Lines[i].ParseIntoArray(F, TEXT(","), false);
			if (F.Num() >= 2 && !F[1].IsEmpty())
			{
				BaseScripts.Add(FCString::Atoi(*F[0]), FName(*F[1].ToLower()));
			}
		}
	}
	for (TPair<int32, TArray<FDinkOriginId>>& Pair : ByScreen)
	{
		Pair.Value.Sort([](const FDinkOriginId& A, const FDinkOriginId& B) { return A.Placement < B.Placement; });
	}
	Hardness.Reset();
    EditorHardFlags.Reset();
	return IsLoaded() || Fail(TEXT("frames.csv or placements.csv has no rows"));
}

const FDinkFrameInfo* FDinkGameplayData::FindFrame(int32 Seq, int32 Frame) const
{
	return Frames.Find(Key(Seq, Frame));
}

int32 FDinkGameplayData::FrameCode(int32 Seq, int32 Frame) const
{
	const FDinkFrameInfo* Info = Frame >= 1 ? FindFrame(Seq, Frame) : nullptr;
	if (!Info || Info->bEmpty)
	{
		return 0;
	}
	return Info->bLoop ? -1 : 1;
}

int32 FDinkGameplayData::FrameDelay(int32 Seq, int32 Frame) const
{
	const FDinkFrameInfo* Info = FindFrame(Seq, Frame);
	return Info ? Info->DelayMs : 0;
}

TMap<int32, TSharedPtr<FDinkHardnessMap>> FDinkHardnessMap::ParseFile(int32 Screen, const FString& Text)
{
	TMap<int32, TSharedPtr<FDinkHardnessMap>> Out;
	TArray<FString> Lines;
	Text.ParseIntoArrayLines(Lines);
	TSharedPtr<FDinkHardnessMap> Cur;
	int32 Row = 0;
	TArray<FString> Tokens;
	for (const FString& Line : Lines)
	{
		if (Line.StartsWith(TEXT("#")))
		{
			continue;
		}
		const bool bTiles = Line == TEXT("tiles");
		if (bTiles || Line.StartsWith(TEXT("vision ")))
		{
			Cur = MakeShared<FDinkHardnessMap>();
			Cur->Screen = Screen;
			Cur->Vision = bTiles ? TileLayerVision : FCString::Atoi(*Line.Mid(7));
			Cur->Codes.SetNumZeroed(Width * Height);
			Out.Add(Cur->Vision, Cur);
			Row = 0;
			continue;
		}
		if (!Cur.IsValid() || Row >= Height)
		{
			continue;
		}
		Tokens.Reset();
		Line.ParseIntoArray(Tokens, TEXT(" "));
		int32 X = 0;
		for (const FString& T : Tokens)
		{
			int32 Colon = INDEX_NONE;
			const int32 Count = FCString::Atoi(*T);
			const int32 Code = T.FindChar(TEXT(':'), Colon) ? FCString::Atoi(*T.Mid(Colon + 1)) : 0;
			if (Code != 0)
			{
				for (int32 i = 0; i < Count && X + i < Width; ++i)
				{
					Cur->Codes[Row * Width + X + i] = static_cast<uint8>(FMath::Clamp(Code, 0, 255));
				}
			}
			X += Count;
		}
		++Row;
	}
	return Out;
}

const FDinkHardnessMap* FDinkGameplayData::GetHardness(int32 Screen, int32 Vision) const
{
	if (const TSharedPtr<FDinkHardnessMap>* Override = HardnessOverrides.Find(Screen))
	{
		return Override->Get();
	}
	TMap<int32, TSharedPtr<FDinkHardnessMap>>* ByVision = Hardness.Find(Screen);
	if (!ByVision)
	{
		ByVision = &Hardness.Add(Screen);
		FString Text;
		if (FFileHelper::LoadFileToString(Text, *GetDataPath(*FString::Printf(TEXT("Hardness/SCR_%03d.txt"), Screen))))
		{
			*ByVision = FDinkHardnessMap::ParseFile(Screen, Text);
		}
	}
	if (const TSharedPtr<FDinkHardnessMap>* Map = ByVision->Find(Vision))
	{
		return Map->Get();
	}
	const TSharedPtr<FDinkHardnessMap>* Base = ByVision->Find(0);
	return Base ? Base->Get() : nullptr;
}

const FDinkHardnessMap* FDinkGameplayData::GetTileHardness(int32 Screen) const
{
	if (HardnessOverrides.Contains(Screen) || !GetHardness(Screen, 0))
	{
		return nullptr;
	}
	const TSharedPtr<FDinkHardnessMap>* Tiles = Hardness.FindChecked(Screen).Find(FDinkHardnessMap::TileLayerVision);
	return Tiles ? Tiles->Get() : nullptr;
}

const std::array<int,100>* FDinkGameplayData::GetEditorHardFlags(int32 Screen) const
{
    if(const auto* Found=EditorHardFlags.Find(Screen))return Found;
    FDinkEditorHardSource Source;FString Error;
    if(!FDinkEditorHardSource::Load(GetDataPath(*FString::Printf(TEXT("Hardness/SCR_%03d_editor_hard.json"),Screen)),Screen,Source,Error))return nullptr;
    return &EditorHardFlags.Add(Screen,Source.EditorHard);
}

void FDinkGameplayData::SetHardnessOverride(int32 Screen, TSharedPtr<FDinkHardnessMap> Map)
{
	if (Map.IsValid())
	{
		HardnessOverrides.Add(Screen, Map);
	}
	else
	{
		HardnessOverrides.Remove(Screen);
	}
}

FString FDinkAdaptationSettings::DefaultPath()
{
	return FPaths::ProjectContentDir() / TEXT("Dink/Data/AI/adaptation.ini");
}

bool FDinkAdaptationSettings::Load(const FString& Path, FString* OutError)
{
	*this = FDinkAdaptationSettings();
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		if (OutError)
		{
			*OutError = TEXT("cannot read ") + Path;
		}
		return false;
	}
	Source = Path;
	TArray<FString> Lines;
	Text.ParseIntoArrayLines(Lines);
	for (FString Line : Lines)
	{
		Line.TrimStartAndEndInline();
		FString Key, Value;
		if (Line.IsEmpty() || Line.StartsWith(TEXT(";")) || Line.StartsWith(TEXT("#")) || Line.StartsWith(TEXT("[")) || !Line.Split(TEXT("="), &Key, &Value))
		{
			continue;
		}
		Key.TrimStartAndEndInline();
		Value.TrimStartAndEndInline();
		if (Key == TEXT("Enabled")) { bEnabled = FCString::Atoi(*Value) != 0; }
		else if (Key == TEXT("WindUpMs")) { WindUpMs = FMath::Max(0.0, FCString::Atod(*Value)); }
		else if (Key == TEXT("MaxAttackers")) { MaxAttackers = FMath::Max(1, FCString::Atoi(*Value)); }
		else if (Key == TEXT("HoldReaimMs")) { HoldReaimMs = FMath::Max(0.0, FCString::Atod(*Value)); }
	}
	return true;
}

int32 FDinkGameplayData::HitFrameDelayMs(int32 Seq) const
{
	const int32* Count = FrameCounts.Find(Seq);
	if (!Count)
	{
		return INDEX_NONE;
	}
	int32 Ms = 0;
	for (int32 F = 1; F <= *Count; ++F)
	{
		const FDinkFrameInfo* Info = FindFrame(Seq, F);
		if (!Info)
		{
			continue;
		}
		if (Info->bSpecial)
		{
			return Ms;
		}
		Ms += Info->DelayMs;
	}
	return INDEX_NONE;
}

int32 FDinkGameplayData::SequenceDurationMs(int32 Seq) const
{
	const int32* Count = FrameCounts.Find(Seq);
	int32 Ms = 0;
	for (int32 F = 1; Count && F <= *Count; ++F)
	{
		if (const FDinkFrameInfo* Info = FindFrame(Seq, F))
		{
			Ms += Info->DelayMs;
		}
	}
	return Ms;
}

const FDinkPlacementInfo* FDinkGameplayData::FindPlacement(const FDinkOriginId& Origin) const
{
	return Placements.Find(Origin);
}

TArray<const FDinkPlacementInfo*> FDinkGameplayData::GetPlacementsOnScreen(int32 Screen) const
{
	TArray<const FDinkPlacementInfo*> Out;
	if (const TArray<FDinkOriginId>* Ids = ByScreen.Find(Screen))
	{
		for (const FDinkOriginId& Id : *Ids)
		{
			Out.Add(Placements.Find(Id));
		}
	}
	return Out;
}

// ---------------------------------------------------------------------------------------------
// Setup, random

void UDinkGameplay::Init(UDinkStorySubsystem* InStory)
{
	Story = InStory;
	FString Error;
	if (!Data.Load(&Error))
	{
		UE_LOG(LogDinkNarrative, Warning, TEXT("gameplay data not loaded: %s; hit/touch/die rules have no hardboxes"), *Error);
	}
	SetRandomSeed(Seed);
	AuthoredInteraction.Load();
	FString AdaptError;
	if (!Adaptation.Load(FDinkAdaptationSettings::DefaultPath(), &AdaptError))
	{
		UE_LOG(LogDinkNarrative, Log, TEXT("3D adaptation layer off: %s"), *AdaptError);
	}
}

UDinkDirector* UDinkGameplay::Director() const
{
	return Story ? Story->GetDirector() : nullptr;
}

void UDinkGameplay::SetRandomSeed(int32 InSeed)
{
	Seed = InSeed;
	StreamSource = MakeShared<FDinkStreamRandomSource>(InSeed);
	RandomSource = StreamSource;
}

void UDinkGameplay::SetRandomSource(TSharedPtr<IDinkRandomSource> Source)
{
	if (Source.IsValid())
	{
		RandomSource = Source;
	}
	else
	{
		SetRandomSeed(Seed);
	}
}

IDinkRandomSource& UDinkGameplay::Rng()
{
	if (!RandomSource.IsValid())
	{
		SetRandomSeed(Seed);
	}
	return *RandomSource;
}

int32 UDinkGameplay::Random(int32 Range, int32 Base)
{
	if (Range == 0)
	{
		return Base; // "script called random function with range set to 0! returning base value"
	}
	// rand() is never negative, so C's % by a negative range gives the same as by its magnitude.
	return Rng().RandomModulo(FMath::Abs(Range)) + Base;
}

void UDinkGameplay::SyncDinkFromActor()
{
	UDinkDirector* D = Director();
	FDinkSprite& Dink = D->GetDink();
	if (const AActor* Actor = Dink.Actor.Get())
	{
		// The pawn's own screen: right after a teleport the greybox's current screen is still the old one,
		// and pixels computed against the wrong screen's corners would fling Dink away on his next move.
		Dink.Screen = D->ScreenAt(Actor->GetActorLocation());
		D->SyncSpriteFromActor(Dink);
	}
}

void UDinkGameplay::SyncDinkFacingFromActor()
{
	UDinkDirector* D = Director();
	if (!D)
	{
		return;
	}
	SyncDinkFromActor();
	FDinkSprite& Dink = D->GetDink();
	if (const AActor* Actor = Dink.Actor.Get())
	{
		const int32 Dir = D->DirFromWorld(Dink.Screen, Actor->GetActorLocation(), Actor->GetActorForwardVector());
		if (Dir != 0)
		{
			Dink.Dir = Dir;
		}
	}
}

void UDinkGameplay::Note(const FString& E)
{
	Events.Add(E);
	if (Events.Num() > 4096)
	{
		Events.RemoveAt(0, Events.Num() - 4096);
	}
	if (Story)
	{
		Story->AddEvent(TEXT("game"), E);
	}
	UE_LOG(LogDinkDirector, Verbose, TEXT("gameplay: %s"), *E);
}

void UDinkGameplay::SetFact(const TCHAR* Name, int32 Value)
{
	if (UDinkFactSubsystem* F = Story ? Story->GetFacts() : nullptr)
	{
		F->SetFact(Name, Value);
	}
}

int32 UDinkGameplay::GetFact(const TCHAR* Name) const
{
	const UDinkFactSubsystem* F = Story ? Story->GetFacts() : nullptr;
	return F ? F->GetFact(Name) : 0;
}

bool UDinkGameplay::IsFrozenDink() const
{
	UDinkDirector* D = Director();
	return D && D->GetDink().bFrozen;
}

void UDinkGameplay::Reset()
{
    InvalidateRuntimeHardnessForScreenLoad();
    HardnessProjection.Reset(); // save/load/new-game never restores a prior original slot identity
    ResetOriginalSlotHistory();
    EditorHardness.Reset();
	WeaponInstance = MagicInstance = DeathInstance = 0;
	PendingHits.Reset();
	// A new game or a load puts the bow down (dink.cpp:1324 load_game, 17693 the start of a game).
	Bow = FDinkBowStatus();
	bAttackHeld = false;
	AttackGate.Reset();
	NowMs = Story ? Story->GetNowMs() : 0.0;
	NextStatusMs = NowMs + 100.0;
	bPushActive = false;
	PushDir = 0;
	PushStartMs = 0.0;
	StatusTicks = 0;
	Events.Reset();
	BrainClockMs = NowMs;
	BrainCarryMs = 0.0;
	MovePath.Reset();
	// A new game or a load builds the screen's hardness anew (load_map), so nothing a script redrew survives.
	OnScreenLoaded();
	SetRandomSeed(Seed);
}

// ---------------------------------------------------------------------------------------------
// Sprites

void UDinkGameplay::InitPlacementSprite(FDinkSprite& S) const
{
	const FDinkPlacementInfo* P = S.Origin.IsValid() ? Data.FindPlacement(S.Origin) : nullptr;
	if (!P)
	{
		return;
	}
    S.HardnessEditorIndex=P->Origin.Placement;
	S.X = P->X;
	S.Y = P->Y;
	S.Dir = 0; // add_sprite_dumb leaves dir 0 (D:3089)
	if (S.Script.IsNone())
	{
		S.Script = P->Script;
	}
	auto Set = [&S](const FName& Name, int32 Value) { S.Props.Add(Name, Value); };
	Set(P_Brain, P->Brain);
	Set(P_Speed, P->Speed);
	Set(P_BaseWalk, P->BaseWalk);
	Set(TEXT("base_idle"), P->BaseIdle);
	Set(P_BaseAttack, P->BaseAttack);
	Set(P_BaseHit, P->BaseHit);
	Set(TEXT("base_death"), P->BaseDie);
	Set(TEXT("hard"), P->Hard);
	Set(TEXT("que"), P->Que);
	Set(TEXT("timing"), P->Timing);
	Set(P_Strength, P->Strength);
	Set(P_Defense, P->Defense);
	Set(P_Exp, P->Exp);
	Set(P_NoHit, P->NoHit);
	Set(P_TouchDamage, P->TouchDamage);
	Set(P_Hitpoints, P->Hitpoints);
	Set(TEXT("sound"), P->Sound);
	Set(P_PSeq, P->Seq);
	Set(P_PFrame, P->Frame);
	Set(P_Size, P->Size);
}

bool UDinkGameplay::GetHardbox(const FDinkSprite& S, int32& L, int32& T, int32& R, int32& B) const
{
	// getpic(): the picture the sprite shows now. An animating sprite shows seq/frame, a still one pseq/pframe.
	const FDinkFrameInfo* F = nullptr;
	const int32 Seq = S.GetProp(P_Seq);
	if (Seq > 0)
	{
		F = Data.FindFrame(Seq, FMath::Max(1, S.GetProp(P_Frame, 1)));
	}
	if (!F)
	{
		F = Data.FindFrame(S.GetProp(P_PSeq), FMath::Max(1, S.GetProp(P_PFrame, 1)));
	}
	if (!F && Seq > 0)
	{
		F = Data.FindInitSequence(Seq);
	}
	if (!F)
	{
		F = Data.FindInitSequence(S.GetProp(P_PSeq));
	}
	FDinkFrameInfo DinkBox;
	if (!F && S.Handle == 1)
	{
		// Dink's walk/idle pictures (dink.ini ds-w2-, "-14 -9 14 9"): he is a target of missiles and enemy attacks.
		DinkBox.Left = -14;
		DinkBox.Top = -9;
		DinkBox.Right = 14;
		DinkBox.Bottom = 9;
		F = &DinkBox;
	}
	if (!F)
	{
		return false;
	}
	const int32 X = FMath::RoundToInt32(S.X);
	const int32 Y = FMath::RoundToInt32(S.Y);
	L = X + F->Left;
	T = Y + F->Top;
	R = X + F->Right;
	B = Y + F->Bottom;
	return true;
}

bool UDinkGameplay::ApplyInitLine(const FString& Line)
{
	// figure_out (dink.cpp:2318-2344): words 1-10: LOAD_SEQUENCE[_NOW] <file> <seq> <speed> <xoffset> <yoffset> <left> <top> <right> <bottom>.
	TArray<FString> W;
	Line.ParseIntoArrayWS(W);
	if (W.Num() < 3 || !(W[0].Equals(TEXT("load_sequence_now"), ESearchCase::IgnoreCase) || W[0].Equals(TEXT("load_sequence"), ESearchCase::IgnoreCase)))
	{
		return false;
	}
	const int32 Seq = FCString::Atoi(*W[2]);
	// Only a sequence that is not active yet is read from the line (dink.cpp:2338-2342); dink.ini's are (frames.csv).
	if (Seq <= 0 || Data.SeqExists(Seq) || Data.FindInitSequence(Seq))
	{
		return false;
	}
	// ReadFromLoadSequenceString (dink.cpp:2190-2226): BLACK / LEFTALIGN / NOTANIM in word 4 is no animation and gives no hardbox.
	if (W.Num() < 10 || W[3].Equals(TEXT("BLACK"), ESearchCase::IgnoreCase) || W[3].Equals(TEXT("LEFTALIGN"), ESearchCase::IgnoreCase) || W[3].Equals(TEXT("NOTANIM"), ESearchCase::IgnoreCase))
	{
		return false;
	}
	FDinkFrameInfo Box;
	Box.DelayMs = FCString::Atoi(*W[3]);
	Box.Left = FCString::Atoi(*W[6]);
	Box.Top = FCString::Atoi(*W[7]);
	Box.Right = FCString::Atoi(*W[8]);
	Box.Bottom = FCString::Atoi(*W[9]);
	// LoadSpriteSingleFrame (dink.cpp:1899-1922) takes the line's box when right > 0 and bottom > 0; otherwise it is computed from the picture,
	// which the remaster does not have: no box then.
	if (Box.Right <= 0 || Box.Bottom <= 0)
	{
		return false;
	}
	Data.AddInitSequence(Seq, Box); // (no event: the trace records the init command itself)
	return true;
}

TArray<int32> UDinkGameplay::LiveSprites(int32 Screen) const
{
	TArray<int32> Out;
	if (UDinkDirector* D = Director())
	{
		for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
		{
			const FDinkSprite& S = Pair.Value;
			if (S.bActive && !S.bText && Pair.Key != UDinkDirector::HandleNoSprite && (S.Screen == Screen || Pair.Key == 1))
			{
				Out.Add(Pair.Key);
			}
		}
	}
	Out.Sort();
	return Out;
}

void UDinkGameplay::OnSequenceSet(int32 Handle, int32 Seq)
{
    if (Handle == 1)
    {
        AActor* Actor = Director() ? Director()->GetActor(Handle) : nullptr;
        if (UWorld* World = Actor ? Actor->GetWorld() : nullptr)
            if (UDinkArtSubsystem* Art = World->GetSubsystem<UDinkArtSubsystem>())
            {
                // Cosmetic only: which clip shows the attack depends on what is armed (or on a spell being cast).
                const FDinkScriptInstance* Weapon = Story ? Story->FindInstance(WeaponInstance) : nullptr;
                Art->PlayPlayerSequence(Actor, Seq, bCastingMagic ? FName(TEXT("magic")) : (Weapon ? Weapon->Script : FName()));
            }
    }
    // The original PendingHits block below remains the sole authority for damage timing.
	if (Handle != 1 && bBrainsEnabled)
	{
		// Every sprite but Dink is animated by ThinkSprite, which lands the hit on the special frame itself.
		return;
	}
	const int32 Delay = Data.HitFrameDelayMs(Seq);
	PendingHits.RemoveAll([Handle](const FDinkPendingHit& H) { return H.Sprite == Handle; });
	if (Delay >= 0)
	{
		FDinkPendingHit Hit;
		Hit.Sprite = Handle;
		Hit.Seq = Seq;
		Hit.AtMs = (Story ? Story->GetNowMs() : NowMs) + Delay;
		PendingHits.Add(Hit);
	}
}

// ---------------------------------------------------------------------------------------------
// Running procedures

void UDinkGameplay::RunProc(int32 Handle, FName Proc)
{
	UDinkDirector* D = Director();
	const FDinkSprite* S = D ? D->FindSprite(Handle) : nullptr;
	if (!S || S->Script.IsNone() || !Story->HasProcedure(S->Script, Proc))
	{
		return;
	}
	const FName Script = S->Script;
	const int32 Screen = S->Screen > 0 ? S->Screen : INDEX_NONE;
	if (const int32 Id = Story->StartProcedure(Script, Proc, Handle, {}, Screen))
	{
		Story->RunNow(Id);
	}
}

void UDinkGameplay::RunInstanceProc(int32 InstanceId, FName Proc)
{
	const FDinkScriptInstance* I = Story->FindInstance(InstanceId);
	if (!I || !I->IsAlive() || !Story->HasProcedure(I->Script, Proc))
	{
		return;
	}
	if (Story->StartProcedureIn(InstanceId, Proc))
	{
		Story->RunNow(InstanceId);
	}
}

int32 UDinkGameplay::NewItemInstance(FName Script)
{
	return Story->CreateDetachedInstance(Script, UDinkDirector::HandleNoSprite);
}

// ---------------------------------------------------------------------------------------------
// Hit, touch, push

void UDinkGameplay::RunThroughTagList(int32 H)
{
	UDinkDirector* D = Director();
	FDinkSprite* A = D ? D->FindSprite(H) : nullptr;
	if (!A || !A->bActive)
	{
		return;
	}
	const int32 Range = A->GetProp(P_Range);
	const int32 Amount = Range == 0 ? 28 : Range;
	const int32 AmountY = Range == 0 ? 36 : Range + Range / 6;
	const int32 RangeAmount = Range / 8;
	const int32 Ax = FMath::RoundToInt32(A->X);
	const int32 Ay = FMath::RoundToInt32(A->Y);
	const int32 Dir = A->Dir;
	const int32 Strength = H == 1 ? GetFact(TEXT("strength")) : A->GetProp(P_Strength);
	const int32 Screen = A->Screen;
	for (const int32 I : LiveSprites(Screen))
	{
		A = D->FindSprite(H); // a previous hit script may have grown the sprite map
		if (!A || !A->bActive) { break; }
		FDinkSprite* T = D->FindSprite(I);
		if (I == H || !T || !T->bActive)
		{
			continue;
		}
		const bool bScript = !T->Script.IsNone();
		const bool bNoHit = T->GetProp(P_NoHit) == 1;
		if (bNoHit && !bScript)
		{
			continue;
		}
		if (UsesAuthoredGeometry(*A, *T))
		{
			if (!AuthoredGeometryMatches(*A, *T, EAuthoredInteraction::Hit)) { continue; }
		}
		else
		{
			int32 L, Tp, R, B;
			if (!GetHardbox(*T, L, Tp, R, B))
			{
				continue;
			}
			R += 5;
			L -= 5;
			Tp -= 5;
			B += 10;
			switch (Dir)
			{
			case 6:
				Tp -= 10; B += 10;
				if (Range != 0) { Tp -= RangeAmount; B += RangeAmount; }
				L -= Amount;
				break;
			case 4:
				R += Amount;
				Tp -= 10; B += 10;
				if (Range != 0) { Tp -= RangeAmount; B += RangeAmount; }
				break;
			case 2:
				R += 10; L -= 10;
				Tp -= AmountY;
				if (Range != 0) { R += RangeAmount; L -= RangeAmount; }
				break;
			case 8:
				R += 10; L -= 10;
				B += AmountY;
				// The original widens and narrows the right edge here (D:15521-15522): no net change. Kept.
				if (Range != 0) { R += RangeAmount; R -= RangeAmount; }
				break;
			default:
				break;
			}
			if (!Inside(Ax, Ay, L, Tp, R, B))
			{
				continue;
			}
		}
		SetFact(TEXT("missle_source"), H);
		const bool bTargets = T->GetProp(P_BaseAttack, -1) != -1 || T->GetProp(P_TouchDamage) > 0;
		if (bNoHit)
		{
			SetFact(TEXT("enemy_sprite"), H);
			if (bTargets)
			{
				T->Props.Add(P_Target, H);
			}
			Note(FString::Printf(TEXT("hit %d by %d (nohit: script only)"), I, H));
			RunProc(I, NAME_Hit);
			continue;
		}
		D->Audio.Cue(FString::Printf(TEXT("sound:%d speed=22050 hit"), A->GetProp(TEXT("attack_hit_sound")) == 0 ? 9 : A->GetProp(TEXT("attack_hit_sound"))));
		if (bTargets)
		{
			T->Props.Add(P_Target, H);
		}
		int32 Dealt = 0;
		if (Strength != 0 && (T->GetProp(P_Hitpoints) > 0 || I == 1))
		{
			T->LastHit = H;
			Dealt = HurtThing(I, DinkRules::MeleeBaseDamage(Strength, Rng()));
		}
		Note(FString::Printf(TEXT("hit %d by %d strength %d damage %d"), I, H, Strength, Dealt));
		if (bScript)
		{
			if (FDinkSprite* T2 = D->FindSprite(I))
			{
				T2->LastHit = H;
			}
			SetFact(TEXT("enemy_sprite"), H);
			RunProc(I, NAME_Hit);
		}
	}
}

void UDinkGameplay::RunThroughTouchDamageList(int32 H)
{
	UDinkDirector* D = Director();
	FDinkSprite* Dink = D ? D->FindSprite(H) : nullptr;
	if (!Dink)
	{
		return;
	}
	const int32 Hx = FMath::RoundToInt32(Dink->X);
	const int32 Hy = FMath::RoundToInt32(Dink->Y);
	const int32 Screen = Dink->Screen;
	const int32 Margin = 2 + CapsuleMarginPixels(*Dink);
	for (const int32 I : LiveSprites(Screen))
	{
		FDinkSprite* S = D->FindSprite(I);
		if (I == H || !S || !S->bActive)
		{
			continue;
		}
		const int32 Touch = S->GetProp(P_TouchDamage);
		if (Touch == 0)
		{
			continue;
		}
		Dink = D->FindSprite(H);
		if (!Dink) { return; }
		if (Touch != -1 && Dink && Dink->bNoTouch)
		{
			return; // the original leaves the whole list here (D:15639)
		}
		int32 L, T, R, B;
		if (UsesAuthoredGeometry(*Dink, *S)
			? !AuthoredGeometryMatches(*Dink, *S, EAuthoredInteraction::Touch)
			: (!GetHardbox(*S, L, T, R, B) || !Inside(Hx, Hy, L - Margin, T - Margin, R + Margin, B + Margin)))
		{
			continue;
		}
		const bool bScript = !S->Script.IsNone();
		if (Touch == -1)
		{
			if (bScript)
			{
				Note(FString::Printf(TEXT("touch %d (%s)"), I, *S->Script.ToString()));
				RunProc(I, NAME_Touch);
			}
			continue;
		}
		if (Dink)
		{
			Dink->bNoTouch = true;
			Dink->NoTouchUntilMs = NowMs + DinkRules::TouchImmunityMs;
			Dink->LastHit = I;
		}
		Note(FString::Printf(TEXT("touch damage %d from %d"), Touch, I));
		if (bScript)
		{
			RunProc(I, NAME_Touch);
		}
		HurtThing(H, Touch);
	}
}

void UDinkGameplay::RunThroughTagListPush(int32 H)
{
	UDinkDirector* D = Director();
	const FDinkSprite* Dink = D ? D->FindSprite(H) : nullptr;
	if (!Dink)
	{
		return;
	}
	const int32 Margin = 2 + CapsuleMarginPixels(*Dink);
	const int32 Hx = FMath::RoundToInt32(Dink->X);
	const int32 Hy = FMath::RoundToInt32(Dink->Y);
	for (const int32 I : LiveSprites(Dink->Screen))
	{
		Dink = D->FindSprite(H);
		if (!Dink) { return; }
		const FDinkSprite* S = D->FindSprite(I);
		int32 L, T, R, B;
		if (I == H || !S || !S->bActive || S->Script.IsNone())
		{
			continue;
		}
		if (UsesAuthoredGeometry(*Dink, *S)
			? AuthoredGeometryMatches(*Dink, *S, EAuthoredInteraction::Push)
			: (GetHardbox(*S, L, T, R, B) && Inside(Hx, Hy, L - Margin, T - Margin, R + Margin, B + Margin)))
		{
			Note(FString::Printf(TEXT("push %d (%s)"), I, *S->Script.ToString()));
			RunProc(I, NAME_Push);
		}
	}
}

int32 UDinkGameplay::FindTalkTarget(int32 H)
{
	UDinkDirector* D = Director();
	if (D && H == 1)
	{
		SyncDinkFacingFromActor();
	}
	FDinkSprite* Dink = D ? D->FindSprite(H) : nullptr;
	if (!Dink)
	{
		return 0;
	}
	if (const AActor* Actor = H != 1 ? Dink->Actor.Get() : nullptr)
	{
		const int32 Dir = D->DirFromWorld(Dink->Screen, Actor->GetActorLocation(), Actor->GetActorForwardVector());
		if (Dir != 0)
		{
			Dink->Dir = Dir;
		}
	}
	const int32 Margin = 10 + CapsuleMarginPixels(*Dink);
	const int32 Hx = FMath::RoundToInt32(Dink->X);
	const int32 Hy = FMath::RoundToInt32(Dink->Y);
	const int32 Dir = Dink->Dir;
	int32 BestAuthored = 0;
	double BestDistance = TNumericLimits<double>::Max();
	for (const int32 I : LiveSprites(Dink->Screen))
	{
		const FDinkSprite* S = D->FindSprite(I);
		int32 L, T, R, B;
		if (I == H || !S || !S->bActive || S->GetProp(P_Brain) == 8)
		{
			continue;
		}
		if (UsesAuthoredGeometry(*Dink, *S))
		{
			double Distance = 0.0;
			if (!S->Script.IsNone() && Story->HasProcedure(S->Script, TEXT("talk")) &&
				AuthoredGeometryMatches(*Dink, *S, EAuthoredInteraction::Talk, &Distance) && Distance < BestDistance)
			{
				BestAuthored = I;
				BestDistance = Distance;
			}
			continue;
		}
		if (!GetHardbox(*S, L, T, R, B)) { continue; }
		L -= Margin; T -= Margin; R += Margin; B += Margin;
		if (Dir == 6) { L -= 50; }
		if (Dir == 4) { R += 50; }
		if (Dir == 2) { T -= 35; }
		if (Dir == 8) { B += 35; }
		if (Inside(Hx, Hy, L, T, R, B) && !S->Script.IsNone() && Story->HasProcedure(S->Script, TEXT("talk")))
		{
			return I;
		}
	}
	return BestAuthored;
}

int32 UDinkGameplay::CapsuleMarginPixels(const FDinkSprite& Dink) const
{
	// The original's Dink is a point that stops at the hardness edge; the 3D capsule stops a radius
	// earlier, so touch and push tests (hardbox +2 px) also get the radius in pixels of that screen.
	const AActor* Actor = Dink.Actor.Get();
	UDinkDirector* D = Director();
	FVector A, B;
	if (!Actor || !D || !D->PixelToWorld(Dink.Screen, Dink.X, Dink.Y, A) || !D->PixelToWorld(Dink.Screen, Dink.X + 10.0, Dink.Y, B))
	{
		return 0;
	}
	const double CmPerPixel = FVector::Dist2D(A, B) / 10.0;
	return CmPerPixel > KINDA_SMALL_NUMBER ? FMath::CeilToInt32(Actor->GetSimpleCollisionRadius() / CmPerPixel) : 0;
}

void UDinkGameplay::UpdatePush(bool bBlockedByHardness, int32 Dir, double InNowMs)
{
	if (!bBlockedByHardness || IsFrozenDink())
	{
		bPushActive = false;
		return;
	}
	if (Dir != 0)
	{
		Director()->GetDink().Dir = Dir; // the walking direction is Dink's dir; push scripts read sp_dir(1, -1)
	}
	if (!bPushActive)
	{
		if (Dir == 2 || Dir == 4 || Dir == 6 || Dir == 8)
		{
			bPushActive = true;
			PushDir = Dir;
			PushStartMs = InNowMs;
		}
		return;
	}
	if (PushDir != Dir)
	{
		bPushActive = false;
		return;
	}
	if (PushStartMs + 600.0 < InNowMs)
	{
		RunThroughTagListPush(1);
	}
}

// ---------------------------------------------------------------------------------------------
// Damage and death

int32 UDinkGameplay::HurtThing(int32 Target, int32 Damage)
{
	UDinkDirector* D = Director();
	FDinkSprite* T = D ? D->FindSprite(Target) : nullptr;
	if (!T || Damage < 1)
	{
		return 0;
	}
	const int32 Defense = Target == 1 ? GetFact(TEXT("defense")) : T->GetProp(P_Defense);
	const int32 Num = DinkRules::ApplyDefense(Damage, Defense, Rng());
	T->Damage += Num;
	return Num;
}

void UDinkGameplay::AddExp(int32 Amount, int32 Sprite, bool bAlways)
{
	UDinkDirector* D = Director();
	const FDinkSprite* S = D ? D->FindSprite(Sprite) : nullptr;
	if (!bAlways && (!S || S->LastHit != 1))
	{
		return;
	}
	if (Amount > 0)
	{
		SetFact(TEXT("exp"), DinkRules::AddExperience(GetFact(TEXT("exp")), Amount));
		Note(FString::Printf(TEXT("exp +%d from %d"), Amount, Sprite));
	}
}

void UDinkGameplay::AddKillSprite(int32 Handle)
{
	UDinkDirector* D = Director();
	const FDinkSprite* S = D->FindSprite(Handle);
	if (!S)
	{
		return;
	}
	// add_kill_sprite (D:12359): a corpse sprite (not shown in the greybox) and add_exp.
	AddExp(S->GetProp(P_Exp), Handle);
	D->DeactivateSprite(Handle, 0, /*bEndScripts*/ false);
	Note(FString::Printf(TEXT("killed %d"), Handle));
}

void UDinkGameplay::ProcessDamage()
{
	UDinkDirector* D = Director();
	if (!D)
	{
		return;
	}
	TArray<int32> Handles;
	for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
	{
		if (Pair.Value.Damage > 0)
		{
			Handles.Add(Pair.Key);
		}
	}
	Handles.Sort();
	for (const int32 H : Handles)
	{
		FDinkSprite* S = D->FindSprite(H);
		if (!S || S->Damage <= 0)
		{
			continue;
		}
		const int32 Dmg = S->Damage;
		S->Damage = 0;
		if (!S->bActive)
		{
			continue;
		}
		if (H == 1)
		{
			// human_brain (D:14697): &life -= damage, not below 0.
			SetFact(TEXT("life"), FMath::Max(0, GetFact(TEXT("life")) - Dmg));
			Note(FString::Printf(TEXT("dink -%d life"), Dmg));
			continue;
		}
		const int32 Brain = S->GetProp(P_Brain);
		switch (Brain)
		{
		case 9:  // pill_brain
		case 10: // dragon_brain
		case 16: // people_brain
		{
			int32 Hp = S->GetProp(P_Hitpoints);
			if (Hp <= 0)
			{
				break;
			}
			Hp -= FMath::Min(Dmg, Hp);
			S->Props.Add(P_Hitpoints, Hp);
			if (Hp < 1)
			{
				Note(FString::Printf(TEXT("die %d (%s)"), H, *S->Script.ToString()));
				RunProc(H, NAME_Die); // check_for_kill_script
				FDinkSprite* After = D->FindSprite(H);
				if (After && After->GetProp(P_Brain) == Brain)
				{
					if (Brain == 16)
					{
						After->Props.Add(P_Brain, 0);
					}
					AddKillSprite(H);
				}
			}
			break;
		}
		case 3: // duck_brain (D:12723)
			if (S->bHeadless)
			{
				Note(FString::Printf(TEXT("duckdie %d"), H));
				RunProc(H, NAME_DuckDie);
				if (FDinkSprite* After = D->FindSprite(H))
				{
					AddExp(After->GetProp(P_Exp), H);
					D->DeactivateSprite(H, 0, /*bEndScripts*/ true);
				}
			}
			else
			{
				AddExp(S->GetProp(P_Exp), H);
				Note(FString::Printf(TEXT("die %d (%s), head flies off"), H, *S->Script.ToString()));
				RunProc(H, NAME_Die);
				if (FDinkSprite* After = D->FindSprite(H))
				{
					// The body runs on headless (base walk 110, speed 1, every frame), D:12748-12775.
					After->bHeadless = true;
					After->Props.Add(P_Follow, 0);
					After->Props.Add(P_BaseWalk, 110);
					After->Props.Add(P_Speed, 1);
					After->Props.Add(TEXT("timing"), 0);
					After->WaitMs = 0.0;
					After->Props.Add(P_Frame, 0);
					if (After->Dir == 0) { After->Dir = 1; }
					if (After->Dir == 4) { After->Dir = 7; }
					if (After->Dir == 6) { After->Dir = 3; }
					ChangeDir(*After, After->Dir, 110);
				}
			}
			break;
		case 4: // pig_brain (D:13370)
		{
			const int32 Hp = S->GetProp(P_Hitpoints) - Dmg;
			S->Props.Add(P_Hitpoints, Hp);
			if (Hp < 1)
			{
				AddExp(S->GetProp(P_Exp), H);
				Note(FString::Printf(TEXT("die %d (%s)"), H, *S->Script.ToString()));
				RunProc(H, NAME_Die);
				if (FDinkSprite* After = D->FindSprite(H))
				{
					After->Props.Add(P_Brain, 7); // a one-time corpse animation, then gone
					D->DeactivateSprite(H, 0, /*bEndScripts*/ false);
				}
			}
			break;
		}
		default:
			// no_brain and the others never apply damage (it is cleared here instead of piling up).
			break;
		}
	}
}

// ---------------------------------------------------------------------------------------------
// Status, missiles, scale

void UDinkGameplay::StatusTick()
{
	++StatusTicks;
	if (GetFact(TEXT("update_status")) != 1)
	{
		return;
	}
	// Spell charge (D:5935): never while the inventory is open; there is no inventory screen yet.
	const int32 Level = GetFact(TEXT("magic_level"));
	const int32 Cost = GetFact(TEXT("magic_cost"));
	if (Level < Cost)
	{
		SetFact(TEXT("magic_level"), DinkRules::MagicChargeStep(Level, GetFact(TEXT("magic")), Cost));
	}
	// Level-up (D:5856-5874): the original's counter catches up 10 exp per update and pauses while
	// Dink talks, is frozen or the item screen is open; here the threshold is checked directly.
	const bool bBusy = IsFrozenDink() || (Story && Story->GetActiveMenu());
	const int32 Next = DinkRules::ExpForNextLevel(GetFact(TEXT("level")));
	if (!bBusy && GetFact(TEXT("exp")) >= Next)
	{
		SetFact(TEXT("exp"), GetFact(TEXT("exp")) - Next);
		Note(FString::Printf(TEXT("level-up (lraise) at %d exp"), Next));
		if (const int32 Id = Story->StartProcedure(TEXT("lraise"), NAME_Raise, 1, {}, INDEX_NONE, /*bNewInstance*/ true))
		{
			Story->RunNow(Id);
		}
	}
	// Death (D:5958): dinfo `die` (it sets &update_status 0, so it starts once).
	if (GetFact(TEXT("life")) < 1)
	{
		const FDinkScriptInstance* Death = Story->FindInstance(DeathInstance);
		if (!Death || !Death->IsAlive())
		{
			Note(TEXT("dink died (dinfo)"));
			DeathInstance = Story->CreateDetachedInstance(TEXT("dinfo"), UDinkDirector::HandleNoSprite);
			RunInstanceProc(DeathInstance, NAME_Die);
		}
	}
}

// ---------------------------------------------------------------------------------------------
// Time

void UDinkGameplay::FlushPendingHits()
{
	UDinkDirector* D = Director();
	TArray<FDinkPendingHit> Due = MoveTemp(PendingHits);
	PendingHits.Reset();
	for (const FDinkPendingHit& Hit : Due)
	{
		const FDinkSprite* S = D ? D->FindSprite(Hit.Sprite) : nullptr;
		if (S && S->bActive && S->GetProp(P_Seq) == Hit.Seq)
		{
			RunThroughTagList(Hit.Sprite);
		}
	}
}

void UDinkGameplay::Tick(double DeltaMs, double InNowMs)
{
	UDinkDirector* D = Director();
	if (!D || !Story)
	{
		return;
	}
	NowMs = InNowMs;
	SyncDinkFromActor();
	for (TPair<int32, FDinkSprite>& Pair : D->Sprites)
	{
		if (Pair.Value.bNoTouch && NowMs > Pair.Value.NoTouchUntilMs)
		{
			Pair.Value.bNoTouch = false;
		}
	}
	// Attacks that reach their hit frame.
	TArray<FDinkPendingHit> Due;
	for (int32 i = PendingHits.Num() - 1; i >= 0; --i)
	{
		if (PendingHits[i].AtMs <= NowMs)
		{
			Due.Insert(PendingHits[i], 0);
			PendingHits.RemoveAt(i);
		}
	}
	for (const FDinkPendingHit& Hit : Due)
	{
		const FDinkSprite* S = D->FindSprite(Hit.Sprite);
		if (S && S->bActive && S->GetProp(P_Seq) == Hit.Seq)
		{
			RunThroughTagList(Hit.Sprite);
		}
	}
	// Dink's brain (1) runs the touch list every frame (D:16852).
	if (D->GetDink().GetProp(P_Brain, 1) == 1)
	{
		RunThroughTouchDamageList(1);
	}
	// A player's remembered attack press (never set by the bot or the console: those call PlayerAttack directly).
	if (AttackGate.TakeBuffered(NowMs))
	{
		StartGatedAttack();
	}
	if (bBrainsEnabled)
	{
		TickBrains(DeltaMs);
	}
	ProcessDamage();
	if (NextStatusMs > NowMs + 1000.0)
	{
		NextStatusMs = NowMs + 100.0; // clock went back (load)
	}
	int32 Guard = 0;
	while (NowMs >= NextStatusMs && Guard++ < 100000)
	{
		// The 100 ms timer (D:17339-17344) sets the bow's hitme whatever &update_status is; the pull adds power only after it.
		if (Bow.bActive)
		{
			Bow.bHitMe = true;
		}
		StatusTick();
		NextStatusMs += 100.0;
	}
}

// ---------------------------------------------------------------------------------------------
// Player actions and items

bool UDinkGameplay::PlayerAttack()
{
	UDinkDirector* D = Director();
	// While the bow is drawn Dink's brain runs process_bow and returns (D:14761-14766): the attack key does not start another `use`.
	if (!D || IsFrozenDink() || Bow.bActive)
	{
		return false;
	}
	const FDinkScriptInstance* Weapon = Story->FindInstance(WeaponInstance);
	if (!Weapon || !Weapon->IsAlive() || !Story->HasProcedure(Weapon->Script, NAME_Use) || D->GetDink().GetProp(P_BaseHit, 100) <= 0)
	{
		return false;
	}
	SyncDinkFacingFromActor();
	const FDinkSprite& Dink = D->GetDink();
	Note(FString::Printf(TEXT("attack with %s facing %d"), *Weapon->Script.ToString(), Dink.Dir));
	RunInstanceProc(WeaponInstance, NAME_Use);
	if (Story->bInstantMode)
	{
		FlushPendingHits();
	}
	return true;
}

bool UDinkGameplay::PlayerCastMagic()
{
	// The magic key is not read while the bow is drawn either (D:14761-14766 return before D:14941).
	if (IsFrozenDink() || Bow.bActive)
	{
		return false;
	}
	const FDinkScriptInstance* Magic = Story->FindInstance(MagicInstance);
	if (!Magic || !Magic->IsAlive() || GetFact(TEXT("magic_level")) < GetFact(TEXT("magic_cost")))
	{
		return false;
	}
	// The spell flies where Dink faces (item-fb.c reads sp_dir(1, -1)): the pawn's facing, as for the attack key.
	// (Without this the cast used whatever dir a script or the last attack had left, e.g. s2-auntp's sp_dir(1, 1).)
	SyncDinkFacingFromActor();
	Note(FString::Printf(TEXT("cast %s facing %d"), *Magic->Script.ToString(), Director() ? Director()->GetDink().Dir : 0));
	bCastingMagic = true;
	RunInstanceProc(MagicInstance, NAME_Use);
	bCastingMagic = false;
	return true;
}

bool UDinkGameplay::PlayerAttackPress()
{
	bAttackHeld = true;
	return PlayerAttack();
}

void UDinkGameplay::PlayerAttackRelease()
{
	bAttackHeld = false;
}

namespace
{
	TAutoConsoleVariable<float> CVarAttackLockMs(TEXT("dink.Attack.LockMs"), 0.f,
		TEXT("How long a player attack locks the attack key, ms. 0: the attack sequence's own length (the original's 400 ms for the fists)."));
	TAutoConsoleVariable<int32> CVarAttackBuffer(TEXT("dink.Attack.BufferPress"), 1,
		TEXT("1: a press during an attack is remembered and starts the next attack when the lock ends (combo); 0: it is dropped."));
}

bool UDinkGameplay::StartGatedAttack()
{
	// The key is "held" for the bow only while it really is down (a buffered press may already be up again).
	const bool bStarted = AttackGate.IsHeld() ? PlayerAttackPress() : PlayerAttack();
	if (!bStarted)
	{
		return false;
	}
	double LockMs = CVarAttackLockMs.GetValueOnGameThread();
	if (LockMs <= 0.)
	{
		UDinkDirector* D = Director();
		const int32 Seq = D ? D->GetDink().GetProp(P_Seq) : 0;
		// Only the attack sequences lock (100 + direction); an item whose `use` plays nothing (the bow's draw, pig feed) does not.
		LockMs = Seq > 100 && Seq < 110 ? Data.SequenceDurationMs(Seq) : 0;
	}
	AttackGate.Started(NowMs, LockMs);
	return true;
}

bool UDinkGameplay::InputAttackPressed()
{
	const FDinkAttackGate::EPress Result = AttackGate.Press(NowMs);
	if (Result == FDinkAttackGate::EPress::Buffered && CVarAttackBuffer.GetValueOnGameThread() == 0)
	{
		AttackGate.Started(AttackGate.GetLockUntilMs(), 0.); // forget it; the lock itself is unchanged
	}
	if (Result != FDinkAttackGate::EPress::Start)
	{
		return false;
	}
	return StartGatedAttack();
}

void UDinkGameplay::InputAttackReleased()
{
	AttackGate.Release();
	PlayerAttackRelease();
}

// ---------------------------------------------------------------------------------------------
// The bow

void UDinkGameplay::ActivateBow(int32 InstanceId)
{
	// activate_bow (D:9397-9408): Dink's animation stops on the first frame of the draw (seq 0, pseq 100 + dir, pframe 1), the bow is
	// active for this script, hitme false, time 0; the script waits (ugly_return(2)) until process_bow runs it again at the release.
	UDinkDirector* D = Director();
	if (D)
	{
		FDinkSprite& Dink = D->GetDink();
		Dink.Props.Add(P_Seq, 0);
		Dink.Props.Add(P_PSeq, 100 + Dink.Dir);
		Dink.Props.Add(P_PFrame, 1);
	}
	Bow.bActive = true;
	Bow.Instance = InstanceId;
	Bow.bHitMe = false;
	Bow.Time = 0;
	Note(TEXT("bow drawn (activate_bow)"));
}

void UDinkGameplay::ProcessBow(double TickMs)
{
	if (!Bow.bActive || !Story)
	{
		return;
	}
	UDinkDirector* D = Director();
	FDinkScriptInstance* Instance = Story->FindInstance(Bow.Instance);
	if (!D || !Instance || !Instance->IsAlive())
	{
		// The script that drew the bow is gone (its item was disarmed: item-b1.c `disarm` is kill_this_task). The original would run_script a dead
		// slot at the release; there is nothing to run on here, so the bow is put down. (The original cannot get here from play: the inventory key
		// is not read while the bow is drawn.)
		Bow.bActive = false;
		Note(TEXT("bow put down (its script ended)"));
		return;
	}
	// human_brain (D:14690-14766): a scripted move of Dink, an open menu (talk_info) and freeze all come before the bow and return. (Dink's
	// nocontrol is not modelled for the pawn: the remaster has no animator for Dink that would clear it again.)
	FDinkSprite& Dink = D->GetDink();
	if (Dink.bMoving || Dink.bFrozen || Story->GetActiveMenu())
	{
		return;
	}
	// The arrow keys turn Dink while he draws (D:14568-14598); here the pawn's facing is the direction input, as for the attack key.
	SyncDinkFacingFromActor();
	FDinkSprite& Drawer = D->GetDink();
	Drawer.Props.Add(P_PSeq, 100 + Drawer.Dir);
	// The pull (D:14600-14612): every 10 ms of engine time, 7 power once hitme is set, at most 500; the picture follows the draw.
	if (Bow.PullWaitMs < TickMs)
	{
		Bow.PullWaitMs = TickMs + BowPullTickMs;
		if (Bow.bHitMe)
		{
			Bow.Time += BowPullPerTick;
		}
		if (Bow.Time > BowMaxPower)
		{
			Bow.Time = BowMaxPower;
		}
		const float Progress = float(Bow.Time) / float(BowMaxPower);
		Drawer.Props.Add(P_PFrame, static_cast<int32>((4.0f * Progress) + 1.0f));
	}
	// The release (D:14615-14620): the attack key is up: the bow is put down, its power kept, and the script runs on at once (run_script).
	if (!bAttackHeld)
	{
		Bow.bActive = false;
		Bow.LastPower = Bow.Time;
		Note(FString::Printf(TEXT("bow released at power %d"), Bow.LastPower));
		if (Instance->State == EDinkInstanceState::Blocked && Instance->Block == EDinkBlock::Bow)
		{
			Instance->State = EDinkInstanceState::Running;
			Instance->Block = EDinkBlock::None;
			Story->RunNow(Bow.Instance);
		}
	}
}

void UDinkGameplay::EndBowBlock(int32 InstanceId)
{
	if (Bow.bActive && Bow.Instance == InstanceId)
	{
		Bow.bActive = false;
		Bow.LastPower = Bow.Time;
	}
}

int32 UDinkGameplay::AddItem(FName Script, bool bMagic)
{
	UDinkDirector* D = Director();
	UDinkInventoryComponent* Inv = D ? D->GetInventory() : nullptr;
	if (!Inv || Script.IsNone())
	{
		return INDEX_NONE;
	}
	Script = FName(*Script.ToString().ToLower());
	const int32 Slot = bMagic ? Inv->AddMagic(Script) : Inv->AddItem(Script);
	if (Slot == INDEX_NONE)
	{
		return Slot;
	}
	Note(FString::Printf(TEXT("%s %s in slot %d"), bMagic ? TEXT("magic") : TEXT("item"), *Script.ToString(), Slot + 1));
	if (const int32 Id = NewItemInstance(Script))
	{
		RunInstanceProc(Id, NAME_Pickup);
	}
	return Slot;
}

void UDinkGameplay::ArmWeapon()
{
	UDinkDirector* D = Director();
	UDinkInventoryComponent* Inv = D ? D->GetInventory() : nullptr;
	if (!Inv)
	{
		return;
	}
	RunInstanceProc(WeaponInstance, NAME_Disarm);
	WeaponInstance = 0;
	const int32 Slot = GetFact(TEXT("cur_weapon")) - 1;
	const FName Item = Inv->GetItemAt(Slot);
	if (Item.IsNone() || !Inv->ArmItem(Slot))
	{
		Inv->DisarmItem();
		return;
	}
	WeaponInstance = NewItemInstance(Item);
	Note(FString::Printf(TEXT("arm %s"), *Item.ToString()));
	RunInstanceProc(WeaponInstance, NAME_Arm);
}

void UDinkGameplay::ArmMagic()
{
	UDinkDirector* D = Director();
	UDinkInventoryComponent* Inv = D ? D->GetInventory() : nullptr;
	if (!Inv)
	{
		return;
	}
	RunInstanceProc(MagicInstance, NAME_Disarm);
	MagicInstance = 0;
	const int32 Slot = GetFact(TEXT("cur_magic")) - 1;
	const FName Spell = Inv->GetMagicAt(Slot);
	if (Spell.IsNone() || !Inv->ArmMagic(Slot))
	{
		Inv->DisarmMagic();
		return;
	}
	MagicInstance = NewItemInstance(Spell);
	Note(FString::Printf(TEXT("arm magic %s"), *Spell.ToString()));
	RunInstanceProc(MagicInstance, NAME_Arm);
}

bool UDinkGameplay::ArmItemSlot(int32 Slot)
{
	UDinkDirector* D = Director();
	if (!D || D->GetInventory()->GetItemAt(Slot - 1).IsNone())
	{
		return false;
	}
	SetFact(TEXT("cur_weapon"), Slot);
	ArmWeapon();
	return true;
}

bool UDinkGameplay::ArmMagicSlot(int32 Slot)
{
	UDinkDirector* D = Director();
	if (!D || D->GetInventory()->GetMagicAt(Slot - 1).IsNone())
	{
		return false;
	}
	SetFact(TEXT("cur_magic"), Slot);
	ArmMagic();
	return true;
}

void UDinkGameplay::KillCurItem()
{
	UDinkDirector* D = Director();
	UDinkInventoryComponent* Inv = D ? D->GetInventory() : nullptr;
	const int32 Slot = GetFact(TEXT("cur_weapon")) - 1;
	const FName Item = Inv ? Inv->GetItemAt(Slot) : NAME_None;
	if (Item.IsNone())
	{
		UE_LOG(LogDinkDirector, Log, TEXT("kill_cur_item: none armed"));
		return;
	}
	RunInstanceProc(WeaponInstance, NAME_Disarm);
	WeaponInstance = 0;
	Inv->RemoveItemAt(Slot);
	SetFact(TEXT("cur_weapon"), 0);
	Note(FString::Printf(TEXT("kill_cur_item %s"), *Item.ToString()));
	const int32 Drop = Story->CreateDetachedInstance(Item, 0);
	RunInstanceProc(Drop, NAME_HoldingDrop);
	RunInstanceProc(Drop, NAME_Drop);
}

void UDinkGameplay::KillThisItem(FName Script)
{
	UDinkDirector* D = Director();
	UDinkInventoryComponent* Inv = D ? D->GetInventory() : nullptr;
	if (!Inv)
	{
		return;
	}
	Script = FName(*Script.ToString().ToLower());
	int32 Slot = INDEX_NONE;
	for (int32 i = 0; i < FDinkInventoryState::NumItemSlots; ++i)
	{
		if (Inv->GetItemAt(i) == Script)
		{
			Slot = i;
			break;
		}
	}
	if (Slot == INDEX_NONE)
	{
		return;
	}
	if (GetFact(TEXT("cur_weapon")) - 1 == Slot)
	{
		RunInstanceProc(WeaponInstance, NAME_HoldingDrop);
		RunInstanceProc(WeaponInstance, NAME_Disarm);
		SetFact(TEXT("cur_weapon"), 0);
		WeaponInstance = 0;
	}
	Inv->RemoveItemAt(Slot);
	Note(FString::Printf(TEXT("kill_this_item %s"), *Script.ToString()));
	const int32 Drop = Story->CreateDetachedInstance(Script, 0);
	RunInstanceProc(Drop, NAME_Drop);
}

void UDinkGameplay::StartNewGame()
{
	Note(TEXT("new game (newgame main)"));
	if (const int32 Id = Story->CreateDetachedInstance(TEXT("newgame"), UDinkDirector::HandleNoSprite))
	{
		RunInstanceProc(Id, NAME_Main);
	}
}

// ---------------------------------------------------------------------------------------------
// Hardness the scripts change (sp_hard, draw_hard_sprite, draw_hard_map)
//
// The engine keeps one hardness map, g_hitmap, built when a screen loads (fill_whole_hard, then place_sprites_game stamps the hardbox of every
// placement whose hard flag is 0 as 100 + its index, D:6076/6136) and changed afterwards only by these two commands. GetHard reads the data's
// loaded map until a script redraws it; from then on (until the next screen load) the redrawn map, built here as the engine builds it.

void UDinkGameplay::SetPlacementHard(const FDinkOriginId& Origin, int32 Hard)
{
	VisitPlacementHard.Add(Origin, Hard);
}

const FDinkHardnessMap* UDinkGameplay::GetLiveHardness(int32 Screen) const
{
	const FLiveHardness* Live = LiveHardness.Find(Screen);
	return Live ? Live->Map.Get() : nullptr;
}

void UDinkGameplay::OnScreenLoaded()
{
	RestoreGreyboxHardness();
	LiveHardness.Reset();
	VisitPlacementHard.Reset();
	VisitPlacementProp.Reset();
}

void UDinkGameplay::SetPlacementProp(const FDinkOriginId& Origin, int32 Prop)
{
    const int32* Previous=VisitPlacementProp.Find(Origin);
    const TOptional<int32> PreviousVisit=Previous?TOptional<int32>(*Previous):TOptional<int32>();
	// g_smallMap.sprite[n].prop = Prop (owner decision OD1: no 1997 command writes it). get_hard and special_block read the flag whenever they
	// run (dink.cpp:569-575, 15339), so unlike sp_hard it needs no redraw: it acts at once and until the screen loads again.
	const FDinkPlacementInfo* P = Data.FindPlacement(Origin);
	const int32 MapProp = P ? P->Prop : 0;
	if (Prop == MapProp)
	{
		VisitPlacementProp.Remove(Origin);
	}
	else
	{
		VisitPlacementProp.Add(Origin, Prop);
	}
    if(RequiresOriginalHardnessScreen(Origin.Screen))
    {
        FString Error;
        if(!RefreshOriginalHardnessProp(Origin.Screen,Error))
        {
            if(PreviousVisit.IsSet())VisitPlacementProp.Add(Origin,PreviousVisit.GetValue());else VisitPlacementProp.Remove(Origin);
            GateOriginalHardnessTransition();UE_LOG(LogDinkDirector,Warning,TEXT("marked sp_prop refused: %s"),*Error);return;
        }
    }
	Note(FString::Printf(TEXT("prop %s %d"), *Origin.ToString(), Prop));
	UWorld* World = Story ? Story->GetWorld() : nullptr;
	UDinkGreyboxSubsystem* Greybox = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
	if (Greybox && MapProp == 1)
	{
		// A sprite warp: special_block runs only while its prop is 1 (D:15339). Its hardbox is solid in the greybox either way (the importer's
		// approximation of a warp: block and fire on contact), which is what a prop-0 placement's stamped hardbox is.
		Greybox->SetSpriteWarpOn(Origin.ToString(), GetPlacementProp(Origin) == 1);
	}
	if (Origin.Screen > 0)
	{
		SyncGreyboxHardness(Origin.Screen);
	}
}

int32 UDinkGameplay::GetPlacementProp(const FDinkOriginId& Origin) const
{
	if (const int32* Visit = VisitPlacementProp.Find(Origin))
	{
		return *Visit;
	}
	const FDinkPlacementInfo* P = Data.FindPlacement(Origin);
	return P ? P->Prop : 0;
}

bool UDinkGameplay::IsWalkThroughByProp(int32 Screen, int32 Code) const
{
	// get_hard (D:569-575): a stamped hardbox whose placement's prop is not 0 reads 0. Only a prop an sp_prop of this visit gave a placement that
	// map.dat has at 0: the 93 map.dat warps keep the greybox's warp approximation (solid, the trigger fires on contact).
	if (Code <= 100 || VisitPlacementProp.Num() == 0)
	{
		return false;
	}
	const FDinkOriginId Origin(Screen, Code - 100);
	const int32* Visit = VisitPlacementProp.Find(Origin);
	const FDinkPlacementInfo* P = Visit ? Data.FindPlacement(Origin) : nullptr;
	return Visit && *Visit != 0 && (!P || P->Prop == 0);
}

bool UDinkGameplay::BuildLoadedCodes(int32 Screen, TArray<uint8>& OutCodes, int32& OutVision) const
{
	OutCodes.Reset();
	OutCodes.SetNumZeroed(FDinkHardnessMap::Width * FDinkHardnessMap::Height);
	OutVision = 0;
	const UDinkFactSubsystem* Facts = Story ? Story->GetFacts() : nullptr;
	const FDinkHardnessMap* Loaded = Data.GetHardness(Screen, Facts ? Facts->GetFact(TEXT("vision")) : 0);
	const FDinkHardnessMap* Tiles = Data.GetTileHardness(Screen);
	const bool bLoaded = Loaded && Loaded->Codes.Num() == OutCodes.Num();
	if (bLoaded)
	{
		OutVision = Loaded->Vision;
		OutCodes = Loaded->Codes;
	}
	// The map the engine holds now: the loaded one, where a placement that was removed when the screen loaded was never stamped (place_sprites_game
	// skips it after update_play_changes, D:5974, 5784), so its pixels show the tile layer. (GetHard reads them as 0 until a redraw.)
	if (const UDinkWorldStateSubsystem* World = Story ? Story->GetWorldState() : nullptr)
	{
		for (int32 i = 0; i < OutCodes.Num(); ++i)
		{
			const int32 Code = OutCodes[i];
			if (Code > 100 && World->IsPlacementRemoved(FDinkOriginId(Screen, Code - 100)))
			{
				OutCodes[i] = Tiles && Tiles->Codes.IsValidIndex(i) ? Tiles->Codes[i] : 0;
			}
		}
	}
	return bLoaded;
}

FDinkHardnessMap& UDinkGameplay::EnsureLiveHardness(int32 Screen)
{
	if (FLiveHardness* Found = LiveHardness.Find(Screen))
	{
		return *Found->Map;
	}
	FLiveHardness& Live = LiveHardness.Add(Screen);
	Live.Map = MakeShared<FDinkHardnessMap>();
	Live.Map->Screen = Screen;
	BuildLoadedCodes(Screen, Live.Map->Codes, Live.Map->Vision);
	Live.Base = Live.Map->Codes;
	return *Live.Map;
}

bool UDinkGameplay::MapPlacement(const FDinkPlacementInfo& P, bool& bActive, int32& Type, int32& Hard, int32& Seq, int32& Frame) const
{
	bActive = true;
	Type = P.Type;
	const int32* VisitHard = VisitPlacementHard.Find(P.Origin);
	Hard = VisitHard ? *VisitHard : P.Hard;
	Seq = P.Seq;
	Frame = P.Frame;
	const UDinkWorldStateSubsystem* World = Story ? Story->GetWorldState() : nullptr;
	FDinkWorldOverride Override;
	if (!World || !World->TryGetOverride(P.Origin, Override) || Override.Type == EDinkOverrideType::None)
	{
		return true;
	}
	// update_play_changes (D:5773-5832), which draw_hard_sprite and draw_hard_map run first (D:8096, 8228): the editor_type of the save
	// overrides the placement's type, hard flag and activity, and its stored editor_seq/editor_frame its picture.
	bActive = !World->IsPlacementRemoved(P.Origin);
	switch (Override.Type)
	{
	case EDinkOverrideType::LiveNoHardness: Type = 1; Hard = 1; break;        // D:5787-5791
	case EDinkOverrideType::BackgroundNoHardness: Type = 0; Hard = 1; break;  // D:5792-5798
	case EDinkOverrideType::LiveHard: Type = 1; Hard = 0; break;              // D:5801-5805
	case EDinkOverrideType::BackgroundHard: Type = 0; Hard = 0; break;        // D:5807-5811
	default: break;
	}
	// D:5829-5830. The remaster keeps only the last of editor_seq / editor_frame (the override's Variant, "seq173" or "frame6"); the other
	// part stays map.dat's.
	const FString Variant = Override.Variant.ToString();
	if (Variant.StartsWith(TEXT("seq")))
	{
		Seq = FCString::Atoi(*Variant.Mid(3));
	}
	else if (Variant.StartsWith(TEXT("frame")))
	{
		Frame = FCString::Atoi(*Variant.Mid(5));
	}
	return true;
}

void UDinkGameplay::AddHardness(FDinkHardnessMap& Map, int32 L, int32 T, int32 R, int32 B, uint8 Code)
{
	// add_hardness (D:487-501): xx from x + hardbox.left to x + hardbox.right (exclusive), likewise y; pixels with xx - 20 > 600, < 0, yy > 400
	// or < 0 are skipped (the engine's map also has a column 600 and a row 400 outside the play field, which FDinkHardnessMap drops).
	for (int32 XX = L; XX < R; ++XX)
	{
		for (int32 YY = T; YY < B; ++YY)
		{
			if (XX - 20 > 600 || XX - 20 < 0 || YY > 400 || YY < 0)
			{
				continue;
			}
			Map.Set(XX - 20, YY, Code);
		}
	}
}

void UDinkGameplay::FillBackSprites(FDinkHardnessMap& Map, int32 Screen) const
{
	// fill_back_sprites (D:6832-6895): the map's placements that are active, not live sprites (type != 1) and hard (flag 0), ranked by
	// que (or y when que is 0; keys of 20000 and more are never ranked) with the lower index first on a tie (D:6845-6868); each of the
	// current &vision (or vision 0) stamps its picture's hardbox at its map position as 100 + index (add_sprite_dumb + add_hardness, D:6879-6891).
	struct FCandidate { const FDinkPlacementInfo* P; int32 Key; int32 Seq; int32 Frame; };
	TArray<FCandidate> Rank;
	for (const FDinkPlacementInfo* P : Data.GetPlacementsOnScreen(Screen))
	{
		bool bActive = false;
		int32 Type = 0, Hard = 0, Seq = 0, Frame = 0;
		if (!P || P->Origin.Placement < 1 || P->Origin.Placement > 99 || !MapPlacement(*P, bActive, Type, Hard, Seq, Frame) || !bActive || Type == 1 || Hard != 0)
		{
			continue;
		}
		const int32 Key = P->Que != 0 ? P->Que : P->Y;
		if (Key < 20000)
		{
			Rank.Add({ P, Key, Seq, Frame });
		}
	}
	Algo::StableSortBy(Rank, [](const FCandidate& C) { return C.Key; });
	const UDinkFactSubsystem* Facts = Story ? Story->GetFacts() : nullptr;
	const int32 Vision = Facts ? Facts->GetFact(TEXT("vision")) : 0;
	for (const FCandidate& C : Rank)
	{
		if (C.P->Vision != 0 && C.P->Vision != Vision)
		{
			continue;
		}
		const FDinkFrameInfo* Box = Data.FindFrame(C.Seq, C.Frame);
		if (!Box)
		{
			Box = Data.FindInitSequence(C.Seq);
		}
		if (Box)
		{
			AddHardness(Map, C.P->X + Box->Left, C.P->Y + Box->Top, C.P->X + Box->Right, C.P->Y + Box->Bottom, static_cast<uint8>(100 + C.P->Origin.Placement));
		}
	}
}

void UDinkGameplay::FillHardSprites(FDinkHardnessMap& Map, int32 Screen) const
{
	// fill_hard_sprites (D:6972-7031): every active sprite, ranked by que (or y; keys of 22024 and more never), lower handle first on a tie;
	// a placement's sprite stamps its current picture's hardbox at its current position as 100 + its index when the map's flag for it is 0
	// (g_smallMap.sprite[sp_index].hard, D:7016-7021); any other sprite as 1 when its own flag is 0 (D:7024-7029).
	UDinkDirector* D = Director();
	if (!D)
	{
		return;
	}
	static const FName P_Que(TEXT("que")), P_Hard(TEXT("hard"));
	struct FCandidate { const FDinkSprite* S; int32 Key; };
	TArray<FCandidate> Rank;
	TArray<int32> Handles;
	D->GetSprites().GetKeys(Handles);
	Handles.Sort();
	for (const int32 H : Handles)
	{
		const FDinkSprite& S = D->GetSprites().FindChecked(H);
		if (!S.bActive || S.bText || H == UDinkDirector::HandleNoSprite || (S.Screen != Screen && H != 1))
		{
			continue;
		}
		const FDinkPlacementInfo* P = S.Origin.IsValid() ? Data.FindPlacement(S.Origin) : nullptr;
		const int32* Que = S.Props.Find(P_Que);
		const int32 Q = Que ? *Que : (P ? P->Que : 0);
		const int32 Key = Q != 0 ? Q : FMath::RoundToInt32(S.Y);
		if (Key < 22024)
		{
			Rank.Add({ &S, Key });
		}
	}
	Algo::StableSortBy(Rank, [](const FCandidate& C) { return C.Key; });
	for (const FCandidate& C : Rank)
	{
		const FDinkSprite& S = *C.S;
		uint8 Code = 0;
        if(S.bRetainedOriginalEditor)
        {
            const FDinkOriginId Owner=OriginalHardnessOwnerOrigin(S);int32 Hard=1;
            if(!OriginalEditorHardFlag(Screen,Owner.Placement,Hard))return; // preflight already validated flags
            if(Hard==0)Code=static_cast<uint8>(100+Owner.Placement);
        }
		else if (S.Origin.IsValid() && S.Origin.Screen == Screen)
		{
			const FDinkPlacementInfo* P = Data.FindPlacement(S.Origin);
			bool bActive = false;
			int32 Type = 0, Hard = 1, Seq = 0, Frame = 0;
			if (P && MapPlacement(*P, bActive, Type, Hard, Seq, Frame) && Hard == 0)
			{
				Code = static_cast<uint8>(100 + S.Origin.Placement);
			}
		}
		else if (S.GetProp(P_Hard, 1) == 0)
		{
			Code = 1;
		}
		int32 L = 0, T = 0, R = 0, B = 0;
		if (Code != 0 && GetHardbox(S, L, T, R, B))
		{
			AddHardness(Map, L, T, R, B, Code);
		}
	}
}

void UDinkGameplay::DrawHardSprite(int32 Handle)
{
    if(const auto* D=Director())if(const auto* S=D->FindSprite(Handle))
        if(RequiresOriginalHardnessScreen(S->Screen))
        {if(!UsesOriginalHardnessProjection(S->Screen))GateOriginalHardnessTransition();FString Error;if(!RedrawRuntimeHardness(Handle,Error))UE_LOG(LogDinkDirector,Warning,TEXT("marked draw_hard_sprite refused: %s"),*Error);return;}
	UDinkDirector* D = Director();
	const FDinkSprite* S = D ? D->FindSprite(Handle) : nullptr;
	if (!S)
	{
		return;
	}
	const int32 Screen = S->Screen;
    FString FlagError;if(!ValidateRetainedLegacyEditorFlags(Screen,FlagError))
    {GateOriginalHardnessTransition();UE_LOG(LogDinkDirector,Warning,TEXT("retained legacy draw refused: %s"),*FlagError);return;}
	FDinkHardnessMap& Map = EnsureLiveHardness(Screen);
	// fill_hardxy (D:597-614) of the sprite's picture's hardbox at its position (D:8098-8102): the tile layer comes back there (get_hard_map,
	// D:582: 0 outside the map), with the engine's clamps (right > 599 -> 600, bottom > 399 -> 400, top and left at least 0).
	int32 L = 0, T = 0, R = 0, B = 0;
	if (GetHardbox(*S, L, T, R, B))
	{
		L -= 20;
		R -= 20;
		if (R > 599) { R = 600; }
		if (T < 0) { T = 0; }
		if (B > 399) { B = 400; }
		if (L < 0) { L = 0; }
		const FDinkHardnessMap* Tiles = Data.GetTileHardness(Screen);
		for (int32 X1 = L; X1 < R; ++X1)
		{
			for (int32 Y1 = T; Y1 < B; ++Y1)
			{
				Map.Set(X1, Y1, static_cast<uint8>(Tiles ? Tiles->Get(X1, Y1) : 0));
			}
		}
	}
	FillBackSprites(Map, Screen);
	FillHardSprites(Map, Screen);
	UE_LOG(LogDinkDirector, Verbose, TEXT("draw_hard_sprite %d: SCR_%03d box %d,%d-%d,%d"), Handle, Screen, L, T, R, B);
	SyncGreyboxHardness(Screen);
}

void UDinkGameplay::DrawHardMap(int32 Screen)
{
    if(RequiresOriginalHardnessScreen(Screen))
    {if(!UsesOriginalHardnessProjection(Screen))GateOriginalHardnessTransition();FString Error;if(!RedrawRuntimeHardnessMap(Screen,Error))UE_LOG(LogDinkDirector,Warning,TEXT("marked draw_hard_map refused: %s"),*Error);return;}
    FString FlagError;if(!ValidateRetainedLegacyEditorFlags(Screen,FlagError))
    {GateOriginalHardnessTransition();UE_LOG(LogDinkDirector,Warning,TEXT("retained legacy draw refused: %s"),*FlagError);return;}
	FDinkHardnessMap& Map = EnsureLiveHardness(Screen);
	// fill_whole_hard (D:654-681): the tile layer over the whole map; then fill_hard_sprites and fill_back_sprites (D:8229-8231).
	const FDinkHardnessMap* Tiles = Data.GetTileHardness(Screen);
	if (Tiles && Tiles->Codes.Num() == Map.Codes.Num())
	{
		Map.Codes = Tiles->Codes;
	}
	else
	{
		FMemory::Memzero(Map.Codes.GetData(), Map.Codes.Num());
	}
	FillHardSprites(Map, Screen);
	FillBackSprites(Map, Screen);
	UE_LOG(LogDinkDirector, Verbose, TEXT("draw_hard_map: SCR_%03d"), Screen);
	SyncGreyboxHardness(Screen);
}

void UDinkGameplay::SyncGreyboxHardness(int32 Screen)
{
    if(RequiresOriginalHardnessScreen(Screen))return; // one physical owner, never PR41 proxy too
	UWorld* World = Story ? Story->GetWorld() : nullptr;
	UDinkGreyboxSubsystem* Greybox = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
	if (!Greybox)
	{
		return;
	}
	// The greybox's solid collision was baked from the loaded map: pass on only what the draws changed and what sp_prop made walk-through
	// (1 now solid, 2 no longer solid).
	const FLiveHardness* Live = LiveHardness.Find(Screen);
	TArray<uint8> Loaded;
	if (!Live)
	{
		int32 Vision = 0;
		if (!BuildLoadedCodes(Screen, Loaded, Vision))
		{
			return;
		}
	}
	const TArray<uint8>& Base = Live ? Live->Base : Loaded;
	const TArray<uint8>& Now = Live ? Live->Map->Codes : Loaded;
	if (Base.Num() != Now.Num())
	{
		return;
	}
	TArray<uint8> Changes;
	Changes.SetNumZeroed(Base.Num());
	bool bAny = false;
	for (int32 i = 0; i < Changes.Num(); ++i)
	{
		const bool bWas = FDinkHardnessMap::IsSolidCode(Base[i]);
		const bool bNow = FDinkHardnessMap::IsSolidCode(Now[i]) && !IsWalkThroughByProp(Screen, Now[i]);
		if (bWas != bNow)
		{
			Changes[i] = bNow ? 1 : 2;
			bAny = true;
		}
	}
	if (bAny)
	{
		Greybox->ApplyScreenSolidChanges(Screen, Changes);
	}
	else
	{
		Greybox->RestoreScreenSolidCollision(Screen);
	}
}

void UDinkGameplay::RestoreGreyboxHardness()
{
	UWorld* World = Story ? Story->GetWorld() : nullptr;
	if (UDinkGreyboxSubsystem* Greybox = World ? World->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr)
	{
		Greybox->RestoreScreenSolidCollision(0);
		// sp_prop's switched-off sprite warps are on again: load_map reads map.dat's prop anew.
		Greybox->RestoreSpriteWarps();
	}
}

// ---------------------------------------------------------------------------------------------
// Save

TSharedPtr<FJsonObject> UDinkGameplay::SaveState() const
{
	TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
    SaveEditorPictures(O);
	O->SetNumberField(TEXT("weapon"), WeaponInstance);
	O->SetNumberField(TEXT("magic"), MagicInstance);
	O->SetNumberField(TEXT("death"), DeathInstance);
	O->SetNumberField(TEXT("nextStatusMs"), NextStatusMs);
	O->SetNumberField(TEXT("seed"), Seed);
	O->SetNumberField(TEXT("brainClockMs"), BrainClockMs);
	O->SetNumberField(TEXT("brainCarryMs"), BrainCarryMs);
	if (StreamSource.IsValid() && RandomSource == StreamSource)
	{
		O->SetNumberField(TEXT("rngSeed"), StreamSource->GetStream().GetCurrentSeed());
	}
	TArray<TSharedPtr<FJsonValue>> Hits;
	for (const FDinkPendingHit& H : PendingHits)
	{
		TSharedRef<FJsonObject> HO = MakeShared<FJsonObject>();
		HO->SetNumberField(TEXT("sprite"), H.Sprite);
		HO->SetNumberField(TEXT("seq"), H.Seq);
		HO->SetNumberField(TEXT("atMs"), H.AtMs);
		Hits.Add(MakeShared<FJsonValueObject>(HO));
	}
	O->SetArrayField(TEXT("pendingHits"), Hits);
	// The bow (only when it has been used, so saves of games that never drew it are unchanged).
	if (Bow.bActive || Bow.LastPower != 0)
	{
		TSharedRef<FJsonObject> BO = MakeShared<FJsonObject>();
		BO->SetBoolField(TEXT("active"), Bow.bActive);
		BO->SetNumberField(TEXT("instance"), Bow.Instance);
		BO->SetBoolField(TEXT("hitme"), Bow.bHitMe);
		BO->SetNumberField(TEXT("time"), Bow.Time);
		BO->SetNumberField(TEXT("lastPower"), Bow.LastPower);
		BO->SetNumberField(TEXT("pullWaitMs"), Bow.PullWaitMs);
		O->SetObjectField(TEXT("bow"), BO);
	}
	return O;
}

void UDinkGameplay::LoadState(const TSharedPtr<FJsonObject>& State)
{
	Reset();
	if (!State.IsValid())
	{
		return;
	}
    LoadEditorPictures(State);
	WeaponInstance = State->GetIntegerField(TEXT("weapon"));
	MagicInstance = State->GetIntegerField(TEXT("magic"));
	DeathInstance = State->GetIntegerField(TEXT("death"));
	NextStatusMs = State->GetNumberField(TEXT("nextStatusMs"));
	Seed = State->GetIntegerField(TEXT("seed"));
	SetRandomSeed(Seed);
	State->TryGetNumberField(TEXT("brainClockMs"), BrainClockMs);
	State->TryGetNumberField(TEXT("brainCarryMs"), BrainCarryMs);
	int32 RngSeed = 0;
	if (State->TryGetNumberField(TEXT("rngSeed"), RngSeed))
	{
		StreamSource->GetStream().Initialize(RngSeed);
	}
	const TSharedPtr<FJsonObject>* BowObject = nullptr;
	if (State->TryGetObjectField(TEXT("bow"), BowObject) && BowObject && BowObject->IsValid())
	{
		const FJsonObject& BO = **BowObject;
		Bow.bActive = BO.GetBoolField(TEXT("active"));
		Bow.Instance = BO.GetIntegerField(TEXT("instance"));
		Bow.bHitMe = BO.GetBoolField(TEXT("hitme"));
		Bow.Time = BO.GetIntegerField(TEXT("time"));
		Bow.LastPower = BO.GetIntegerField(TEXT("lastPower"));
		Bow.PullWaitMs = BO.GetNumberField(TEXT("pullWaitMs"));
	}
	const TArray<TSharedPtr<FJsonValue>>* Hits = nullptr;
	if (State->TryGetArrayField(TEXT("pendingHits"), Hits))
	{
		for (const TSharedPtr<FJsonValue>& V : *Hits)
		{
			FDinkPendingHit H;
			H.Sprite = V->AsObject()->GetIntegerField(TEXT("sprite"));
			H.Seq = V->AsObject()->GetIntegerField(TEXT("seq"));
			H.AtMs = V->AsObject()->GetNumberField(TEXT("atMs"));
			PendingHits.Add(H);
		}
	}
}
