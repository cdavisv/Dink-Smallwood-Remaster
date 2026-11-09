#include "DinkGameplay.h"
#include "DinkCombat.h"
#include "DinkDirector.h"
#include "DinkArtSubsystem.h"
#include "DinkFactSubsystem.h"
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
		if (Line.StartsWith(TEXT("vision ")))
		{
			Cur = MakeShared<FDinkHardnessMap>();
			Cur->Screen = Screen;
			Cur->Vision = FCString::Atoi(*Line.Mid(7));
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
	WeaponInstance = MagicInstance = DeathInstance = 0;
	PendingHits.Reset();
	// A new game or a load puts the bow down (dink.cpp:1324 load_game, 17693 the start of a game).
	Bow = FDinkBowStatus();
	bAttackHeld = false;
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
            if (UDinkArtSubsystem* Art = World->GetSubsystem<UDinkArtSubsystem>()) Art->PlayPlayerSequence(Actor, Seq);
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
	RunInstanceProc(MagicInstance, NAME_Use);
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
// Save

TSharedPtr<FJsonObject> UDinkGameplay::SaveState() const
{
	TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
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
