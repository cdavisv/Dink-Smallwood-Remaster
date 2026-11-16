// The narrative layer's Slate overlay: dialogue box, bubbles, captions, choice menu, fade and the inventory screen.
// See DinkNarrativeOverlay.h.

#include "DinkNarrativeOverlay.h"
#include "DinkAudioSubsystem.h"
#include "DinkCombat.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkGameplay.h"
#include "DinkInventoryComponent.h"
#include "DinkPresentationData.h"
#include "DinkStorySubsystem.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "Engine/GameViewportClient.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "HAL/PlatformTime.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"
#include "DinkLayout.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"

namespace DinkOverlay
{
	// Palette: a dark slate panel with a warm accent.
	const FLinearColor PanelFill(0.028f, 0.031f, 0.043f, 0.90f);
	const FLinearColor PanelEdge(1.f, 1.f, 1.f, 0.10f);
	const FLinearColor Accent(0.96f, 0.74f, 0.36f, 1.f);
	const FLinearColor TextMain(0.95f, 0.95f, 0.93f, 1.f);
	const FLinearColor TextDim(0.66f, 0.68f, 0.72f, 1.f);
	const FLinearColor TextDark(0.09f, 0.07f, 0.04f, 1.f);
	const FLinearColor LifeRed(0.86f, 0.27f, 0.24f, 1.f);
	const FLinearColor MagicBlue(0.38f, 0.58f, 0.96f, 1.f);

	FLinearColor WithAlpha(FLinearColor C, float A)
	{
		C.A *= A;
		return C;
	}

	float EaseOut(float T)
	{
		T = FMath::Clamp(T, 0.f, 1.f);
		return 1.f - (1.f - T) * (1.f - T) * (1.f - T);
	}

	FSlateFontInfo Font(const TCHAR* Face, float Size)
	{
		return FCoreStyle::GetDefaultFontStyle(Face, Size);
	}

	/** Draws primitives in increasing layers (Slate batches within a layer, which could put text under a later box). */
	struct FPainter
	{
		const FGeometry& Geometry;
		FSlateWindowElementList& Out;
		int32 Layer;
		/** Multiplies every alpha (fades). */
		float Alpha = 1.f;

		FPainter(const FGeometry& InGeometry, FSlateWindowElementList& InOut, int32 InLayer) : Geometry(InGeometry), Out(InOut), Layer(InLayer) {}

		FVector2f Size() const { return FVector2f(Geometry.GetLocalSize()); }

		void Box(FVector2f Pos, FVector2f BoxSize, const FLinearColor& Fill, float Radius, const FLinearColor& Outline = FLinearColor::Transparent, float OutlineWidth = 0.f)
		{
			if (BoxSize.X <= 0.f || BoxSize.Y <= 0.f)
			{
				return;
			}
			const FLinearColor Tint = WithAlpha(Fill, Alpha);
			const FSlateRoundedBoxBrush Brush(Tint, Radius, WithAlpha(Outline, Alpha), OutlineWidth);
			// MakeBox does not read the brush's TintColor (widgets pass Brush->GetTint themselves): without the explicit tint
			// every panel is drawn opaque white.
			FSlateDrawElement::MakeBox(Out, ++Layer, Geometry.ToPaintGeometry(BoxSize, FSlateLayoutTransform(Pos)), &Brush, ESlateDrawEffect::None, Tint);
		}

		/** A soft shadow under a rounded panel: a few widening, fading boxes. */
		void Shadow(FVector2f Pos, FVector2f BoxSize, float Radius, float Strength = 1.f)
		{
			for (int32 i = 3; i >= 1; --i)
			{
				const float Grow = 4.f * i;
				Box(Pos + FVector2f(-Grow, -Grow + 3.f * i), BoxSize + FVector2f(2.f * Grow, 2.f * Grow), FLinearColor(0.f, 0.f, 0.f, 0.10f * Strength), Radius + Grow);
			}
		}

		void Image(FVector2f Pos, FVector2f ImageSize, const FSlateBrush* Brush)
		{
			FSlateDrawElement::MakeBox(Out, ++Layer, Geometry.ToPaintGeometry(ImageSize, FSlateLayoutTransform(Pos)), Brush, ESlateDrawEffect::None, FLinearColor(1.f, 1.f, 1.f, Alpha));
		}

		static FVector2f Measure(const FString& Text, const FSlateFontInfo& InFont)
		{
			if (!FSlateApplication::IsInitialized())
			{
				return FVector2f(Text.Len() * InFont.Size * 0.6f, InFont.Size * 1.4f);
			}
			return FVector2f(FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(Text, InFont));
		}

		static float LineHeight(const FSlateFontInfo& InFont)
		{
			return Measure(TEXT("Ag"), InFont).Y;
		}

		void Text(FVector2f Pos, const FString& InText, const FSlateFontInfo& InFont, const FLinearColor& Color, bool bShadow = false)
		{
			const FVector2f TextSize = Measure(InText, InFont);
			if (bShadow)
			{
				FSlateDrawElement::MakeText(Out, ++Layer, Geometry.ToPaintGeometry(TextSize, FSlateLayoutTransform(Pos + FVector2f(0.f, 2.f))), InText, InFont, ESlateDrawEffect::None, FLinearColor(0.f, 0.f, 0.f, 0.55f * Alpha * Color.A));
			}
			FSlateDrawElement::MakeText(Out, ++Layer, Geometry.ToPaintGeometry(TextSize, FSlateLayoutTransform(Pos)), InText, InFont, ESlateDrawEffect::None, WithAlpha(Color, Alpha));
		}

		void TextCentered(FVector2f Centre, const FString& InText, const FSlateFontInfo& InFont, const FLinearColor& Color, bool bShadow = false)
		{
			const FVector2f TextSize = Measure(InText, InFont);
			Text(Centre - TextSize * 0.5f, InText, InFont, Color, bShadow);
		}

		void Lines(const TArray<FVector2f>& Points, const FLinearColor& Color, float Thickness)
		{
			FSlateDrawElement::MakeLines(Out, ++Layer, Geometry.ToPaintGeometry(), Points, ESlateDrawEffect::None, WithAlpha(Color, Alpha), true, Thickness);
		}

		/** A key cap ("Enter") followed by what it does; returns the width used. */
		float KeyHint(FVector2f Pos, const TArray<FString>& Keys, const FString& Label, float Scale = 1.f)
		{
			const FSlateFontInfo KeyFont = Font(TEXT("Bold"), 11.f * Scale);
			const FSlateFontInfo LabelFont = Font(TEXT("Regular"), 12.f * Scale);
			const float CapH = 24.f * Scale;
			float X = Pos.X;
			for (int32 i = 0; i < Keys.Num(); ++i)
			{
				const FVector2f KeySize = Measure(Keys[i], KeyFont);
				const float CapW = FMath::Max(CapH, KeySize.X + 14.f * Scale);
				Box(FVector2f(X, Pos.Y), FVector2f(CapW, CapH), FLinearColor(1.f, 1.f, 1.f, 0.08f), 6.f * Scale, FLinearColor(1.f, 1.f, 1.f, 0.28f), 1.f);
				TextCentered(FVector2f(X + CapW * 0.5f, Pos.Y + CapH * 0.5f), Keys[i], KeyFont, TextMain);
				X += CapW + 4.f * Scale;
			}
			const FVector2f LabelSize = Measure(Label, LabelFont);
			Text(FVector2f(X + 4.f * Scale, Pos.Y + (CapH - LabelSize.Y) * 0.5f), Label, LabelFont, TextDim);
			return X + 4.f * Scale + LabelSize.X - Pos.X;
		}

		/** Width a KeyHint would take. */
		static float KeyHintWidth(const TArray<FString>& Keys, const FString& Label, float Scale = 1.f)
		{
			const FSlateFontInfo KeyFont = Font(TEXT("Bold"), 11.f * Scale);
			const FSlateFontInfo LabelFont = Font(TEXT("Regular"), 12.f * Scale);
			const float CapH = 24.f * Scale;
			float W = 0.f;
			for (const FString& K : Keys)
			{
				W += FMath::Max(CapH, Measure(K, KeyFont).X + 14.f * Scale) + 4.f * Scale;
			}
			return W + 4.f * Scale + Measure(Label, LabelFont).X;
		}
	};

	/** Word wrap by measured width (a word wider than the line is broken by characters). */
	TArray<FString> Wrap(const FString& Text, const FSlateFontInfo& InFont, float MaxWidth)
	{
		TArray<FString> Lines;
		TArray<FString> Words;
		Text.ParseIntoArray(Words, TEXT(" "), true);
		FString Line;
		for (FString Word : Words)
		{
			const FString Candidate = Line.IsEmpty() ? Word : Line + TEXT(" ") + Word;
			if (FPainter::Measure(Candidate, InFont).X <= MaxWidth)
			{
				Line = Candidate;
				continue;
			}
			if (!Line.IsEmpty())
			{
				Lines.Add(Line);
				Line.Reset();
			}
			while (FPainter::Measure(Word, InFont).X > MaxWidth && Word.Len() > 1)
			{
				int32 Cut = Word.Len() - 1;
				while (Cut > 1 && FPainter::Measure(Word.Left(Cut), InFont).X > MaxWidth)
				{
					--Cut;
				}
				Lines.Add(Word.Left(Cut));
				Word = Word.Mid(Cut);
			}
			Line = Word;
		}
		if (!Line.IsEmpty() || Lines.Num() == 0)
		{
			Lines.Add(Line);
		}
		return Lines;
	}

	/** "Pig Feed" -> "PF", "Fists" -> "Fi". */
	FString Monogram(const FString& Name)
	{
		TArray<FString> Words;
		Name.ParseIntoArray(Words, TEXT(" "), true);
		if (Words.Num() >= 2)
		{
			return FString::Printf(TEXT("%c%c"), FChar::ToUpper(Words[0][0]), FChar::ToUpper(Words[1][0]));
		}
		return Name.Left(2);
	}

	/** Pulse 0..1 for the cursor (the original alternates its selector frames every 400 ms, dink.cpp:16456-16461). */
	float Pulse(double Now)
	{
		return 0.5f + 0.5f * FMath::Sin(static_cast<float>(Now) * 2.f * PI / 0.8f);
	}
}

using namespace DinkOverlay;

void SDinkNarrativeOverlay::Construct(const FArguments& InArgs, UDinkStorySubsystem* InStory)
{
	Story = InStory;
	SetVisibility(EVisibility::HitTestInvisible);
}

const FSlateBrush* SDinkNarrativeOverlay::FindItemIcon(FName Script) const
{
	if (FIcon* Found = Icons.Find(Script))
	{
		return Found->Brush.Get();
	}
	FIcon& Icon = Icons.Add(Script);
	const FSoftObjectPath Path = FDinkPresentationData::Get().ItemIcon(Script);
	if (Path.IsValid())
	{
		if (UTexture2D* Texture = Cast<UTexture2D>(Path.TryLoad()))
		{
			Icon.Texture.Reset(Texture);
			Icon.Brush = MakeShared<FSlateBrush>();
			Icon.Brush->SetResourceObject(Texture);
			Icon.Brush->ImageSize = FVector2f(Texture->GetSizeX(), Texture->GetSizeY());
			Icon.Brush->DrawAs = ESlateBrushDrawType::Image;
		}
	}
	return Icon.Brush.Get();
}

namespace DinkOverlay
{
	struct FInventoryPainter
	{
		FPainter& P;
		const SDinkNarrativeOverlay& Overlay;
		const UDinkStorySubsystem& S;
		double Now;

		static constexpr float PanelW = 1180.f;
		static constexpr float PanelH = 668.f;
		static constexpr float Tile = 104.f;
		static constexpr float Gap = 12.f;

		void Paint()
		{
			const FDinkInventoryScreen& Screen = S.GetInventoryScreen();
			const float T = EaseOut(static_cast<float>((Now - Screen.ChangedAt) / 0.16));
			const FVector2f View = P.Size();
			const float Scale = FMath::Min3(1.f, (View.X - 48.f) / PanelW, (View.Y - 48.f) / PanelH);
			const float BaseAlpha = P.Alpha;
			P.Alpha = BaseAlpha * T;
			P.Box(FVector2f::ZeroVector, View, FLinearColor(0.f, 0.f, 0.f, 0.55f), 0.f);

			const FVector2f Size(PanelW * Scale, PanelH * Scale);
			const FVector2f Origin = (View - Size) * 0.5f + FVector2f(0.f, (1.f - T) * 18.f);
			auto At = [&](float X, float Y) { return Origin + FVector2f(X, Y) * Scale; };
			P.Shadow(Origin, Size, 22.f * Scale);
			P.Box(Origin, Size, PanelFill, 22.f * Scale, PanelEdge, 1.f);

			// Header.
			P.Text(At(40.f, 30.f), TEXT("Inventory"), Font(TEXT("Bold"), 26.f * Scale), TextMain);
			{
				const float W = FPainter::KeyHintWidth({ TEXT("Enter"), TEXT("I"), TEXT("Esc") }, TEXT("Close"), Scale);
				P.KeyHint(At(PanelW - 40.f, 38.f) - FVector2f(W, 0.f), { TEXT("Enter"), TEXT("I"), TEXT("Esc") }, TEXT("Close"), Scale);
			}
			P.Box(At(40.f, 86.f), FVector2f((PanelW - 80.f) * Scale, 1.f), FLinearColor(1.f, 1.f, 1.f, 0.08f), 0.f);

			UDinkDirector* D = S.GetDirector();
			UDinkInventoryComponent* Inv = D ? D->GetInventory() : nullptr;
			if (!Inv)
			{
				P.Alpha = BaseAlpha;
				return;
			}

			// The original's layout: magic (2 x 4) left of the items (4 x 4).
			const float GridTop = 132.f;
			const float MagicX = 40.f;
			const float ItemsX = MagicX + 2.f * Tile + Gap + 44.f;
			const FSlateFontInfo SectionFont = Font(TEXT("Bold"), 12.f * Scale);
			P.Text(At(MagicX, 104.f), TEXT("MAGIC"), SectionFont, TextDim);
			P.Text(At(ItemsX, 104.f), TEXT("ITEMS"), SectionFont, TextDim);
			for (int32 i = 0; i < FDinkInventoryState::NumMagicSlots; ++i)
			{
				const FVector2f Pos = At(MagicX + (i % 2) * (Tile + Gap), GridTop + (i / 2) * (Tile + Gap));
				PaintSlot(Pos, Scale, Inv->GetMagicAt(i), i + 1, true, Inv->GetArmedMagicSlot() == i, Screen.bMagic && Screen.Cursor == i + 1);
			}
			for (int32 i = 0; i < FDinkInventoryState::NumItemSlots; ++i)
			{
				const FVector2f Pos = At(ItemsX + (i % 4) * (Tile + Gap), GridTop + (i / 4) * (Tile + Gap));
				PaintSlot(Pos, Scale, Inv->GetItemAt(i), i + 1, false, Inv->GetArmedItemSlot() == i, !Screen.bMagic && Screen.Cursor == i + 1);
			}

			// Dink's status (the original's status bar: level, life, strength, defense, magic, exp, gold).
			const float StatsX = ItemsX + 4.f * Tile + 3.f * Gap + 48.f;
			const float StatsW = PanelW - 40.f - StatsX;
			PaintStats(At(StatsX, 104.f), StatsW, Scale, Inv);

			// The slot under the cursor and the keys.
			const FName Selected = Screen.bMagic ? Inv->GetMagicAt(Screen.Cursor - 1) : Inv->GetItemAt(Screen.Cursor - 1);
			const float FootY = GridTop + 4.f * Tile + 3.f * Gap + 26.f;
			P.Box(At(40.f, FootY - 12.f), FVector2f((PanelW - 80.f) * Scale, 1.f), FLinearColor(1.f, 1.f, 1.f, 0.08f), 0.f);
			const FString Title = Selected.IsNone() ? FString(TEXT("Empty slot")) : FDinkPresentationData::Get().ItemName(Selected);
			P.Text(At(40.f, FootY + 4.f), Title, Font(TEXT("Bold"), 18.f * Scale), Selected.IsNone() ? TextDim : TextMain);
			const FString Where = FString::Printf(TEXT("%s slot %d"), Screen.bMagic ? TEXT("Magic") : TEXT("Item"), Screen.Cursor);
			P.Text(At(40.f, FootY + 34.f), Where, Font(TEXT("Regular"), 12.f * Scale), TextDim);
			float X = PanelW - 40.f;
			struct FHint { TArray<FString> Keys; FString Label; };
			const FHint Hints[] = {
				{ { TEXT("F"), TEXT("Space"), TEXT("Click") }, TEXT("Arm") },
				{ { TEXT("1-0") }, TEXT("Quick-arm") },
				{ { TEXT("WASD"), TEXT("Arrows") }, TEXT("Move") },
			};
			for (const FHint& H : Hints)
			{
				const float W = FPainter::KeyHintWidth(H.Keys, H.Label, Scale) / Scale;
				X -= W;
				P.KeyHint(At(X, FootY + 12.f), H.Keys, H.Label, Scale);
				X -= 28.f;
			}
			P.Alpha = BaseAlpha;
		}

		void PaintSlot(FVector2f Pos, float Scale, FName Script, int32 Number, bool bMagic, bool bArmed, bool bCursor)
		{
			const FVector2f Size(Tile * Scale, Tile * Scale);
			const float R = 14.f * Scale;
			if (bCursor)
			{
				const float Glow = 0.10f + 0.12f * Pulse(Now);
				P.Box(Pos - FVector2f(5.f, 5.f) * Scale, Size + FVector2f(10.f, 10.f) * Scale, FLinearColor(1.f, 1.f, 1.f, Glow), R + 5.f * Scale);
			}
			const bool bFilled = !Script.IsNone();
			P.Box(Pos, Size, FLinearColor(1.f, 1.f, 1.f, bFilled ? 0.075f : 0.035f), R,
				bArmed ? Accent : (bCursor ? FLinearColor(1.f, 1.f, 1.f, 0.85f) : FLinearColor(1.f, 1.f, 1.f, 0.06f)), bArmed || bCursor ? 2.f * Scale : 1.f);
			if (bArmed && bCursor)
			{
				P.Box(Pos - FVector2f(3.f, 3.f) * Scale, Size + FVector2f(6.f, 6.f) * Scale, FLinearColor::Transparent, R + 3.f * Scale, FLinearColor(1.f, 1.f, 1.f, 0.85f), 2.f * Scale);
			}
			// Quick-arm number for items 1-10.
			if (!bMagic && Number <= 10)
			{
				P.Text(Pos + FVector2f(9.f, 6.f) * Scale, FString::FromInt(Number % 10), Font(TEXT("Bold"), 10.f * Scale), FLinearColor(1.f, 1.f, 1.f, 0.35f));
			}
			if (!bFilled)
			{
				return;
			}
			const FString Name = FDinkPresentationData::Get().ItemName(Script);
			const FVector2f IconCentre = Pos + FVector2f(Tile * 0.5f, 40.f) * Scale;
			if (const FSlateBrush* Icon = Overlay.FindItemIcon(Script))
			{
				P.Image(IconCentre - FVector2f(30.f, 30.f) * Scale, FVector2f(60.f, 60.f) * Scale, Icon);
			}
			else
			{
				// Icons are an art follow-up (items.csv icon column): until then a monogram disc.
				const FLinearColor Disc = bMagic ? MagicBlue : Accent;
				P.Box(IconCentre - FVector2f(25.f, 25.f) * Scale, FVector2f(50.f, 50.f) * Scale, WithAlpha(Disc, 0.20f), 25.f * Scale, WithAlpha(Disc, 0.65f), 1.5f * Scale);
				P.TextCentered(IconCentre, Monogram(Name), Font(TEXT("Bold"), 17.f * Scale), Disc);
			}
			const FSlateFontInfo NameFont = Font(TEXT("Regular"), 11.f * Scale);
			TArray<FString> Lines = Wrap(Name, NameFont, (Tile - 12.f) * Scale);
			if (Lines.Num() > 2)
			{
				Lines.SetNum(2);
				Lines[1] += TEXT("...");
			}
			float Y = Pos.Y + (Lines.Num() > 1 ? 70.f : 76.f) * Scale;
			for (const FString& L : Lines)
			{
				P.TextCentered(FVector2f(Pos.X + Tile * 0.5f * Scale, Y + 7.f * Scale), L, NameFont, TextMain);
				Y += 14.f * Scale;
			}
			if (bArmed)
			{
				const FSlateFontInfo TagFont = Font(TEXT("Bold"), 8.f * Scale);
				const FVector2f TagSize = FPainter::Measure(TEXT("ARMED"), TagFont) + FVector2f(10.f, 4.f) * Scale;
				const FVector2f TagPos = Pos + FVector2f(Tile * Scale - TagSize.X - 6.f * Scale, 6.f * Scale);
				P.Box(TagPos, TagSize, Accent, TagSize.Y * 0.5f);
				P.TextCentered(TagPos + TagSize * 0.5f, TEXT("ARMED"), TagFont, TextDark);
			}
		}

		void Bar(FVector2f Pos, float W, float Scale, float Fraction, const FLinearColor& Color)
		{
			const float H = 8.f * Scale;
			P.Box(Pos, FVector2f(W, H), FLinearColor(1.f, 1.f, 1.f, 0.08f), H * 0.5f);
			const float Fill = W * FMath::Clamp(Fraction, 0.f, 1.f);
			if (Fill >= H)
			{
				P.Box(Pos, FVector2f(Fill, H), Color, H * 0.5f);
			}
		}

		void PaintStats(FVector2f Pos, float W, float Scale, UDinkInventoryComponent* Inv)
		{
			const UDinkFactSubsystem* F = S.GetFacts();
			auto Fact = [F](const TCHAR* Name) { return F ? F->GetFact(Name) : 0; };
			const FSlateFontInfo Label = Font(TEXT("Regular"), 13.f * Scale);
			const FSlateFontInfo Value = Font(TEXT("Bold"), 13.f * Scale);
			const float Wd = W * Scale;
			P.Text(Pos, TEXT("STATUS"), Font(TEXT("Bold"), 12.f * Scale), TextDim);
			float Y = Pos.Y + 28.f * Scale;
			P.Text(FVector2f(Pos.X, Y), TEXT("Dink Smallwood"), Font(TEXT("Bold"), 20.f * Scale), TextMain);
			Y += 32.f * Scale;
			P.Text(FVector2f(Pos.X, Y), FString::Printf(TEXT("Level %d"), Fact(TEXT("level"))), Font(TEXT("Regular"), 14.f * Scale), Accent);
			Y += 34.f * Scale;

			auto Row = [&](const FString& Name, const FString& Val)
			{
				P.Text(FVector2f(Pos.X, Y), Name, Label, TextDim);
				const FVector2f VS = FPainter::Measure(Val, Value);
				P.Text(FVector2f(Pos.X + Wd - VS.X, Y), Val, Value, TextMain);
				Y += 22.f * Scale;
			};
			const int32 Life = Fact(TEXT("life"));
			const int32 LifeMax = FMath::Max(1, Fact(TEXT("lifemax")));
			Row(TEXT("Life"), FString::Printf(TEXT("%d / %d"), Life, LifeMax));
			Bar(FVector2f(Pos.X, Y), Wd, Scale, static_cast<float>(Life) / LifeMax, LifeRed);
			Y += 22.f * Scale;
			const int32 Level = Fact(TEXT("level"));
			const int32 Next = FMath::Max(1, DinkRules::ExpForNextLevel(Level));
			Row(TEXT("Experience"), FString::Printf(TEXT("%d / %d"), Fact(TEXT("exp")), Next));
			Bar(FVector2f(Pos.X, Y), Wd, Scale, static_cast<float>(Fact(TEXT("exp"))) / Next, Accent);
			Y += 22.f * Scale;
			const int32 Cost = Fact(TEXT("magic_cost"));
			if (Cost > 0)
			{
				Row(TEXT("Magic charge"), FString::Printf(TEXT("%d%%"), FMath::Clamp(Fact(TEXT("magic_level")) * 100 / Cost, 0, 100)));
				Bar(FVector2f(Pos.X, Y), Wd, Scale, static_cast<float>(Fact(TEXT("magic_level"))) / Cost, MagicBlue);
				Y += 22.f * Scale;
			}
			Y += 6.f * Scale;
			Row(TEXT("Strength"), FString::FromInt(Fact(TEXT("strength"))));
			Row(TEXT("Defense"), FString::FromInt(Fact(TEXT("defense"))));
			Row(TEXT("Magic"), FString::FromInt(Fact(TEXT("magic"))));
			Row(TEXT("Gold"), FString::FromInt(Fact(TEXT("gold"))));
			Y += 14.f * Scale;
			P.Box(FVector2f(Pos.X, Y), FVector2f(Wd, 1.f), FLinearColor(1.f, 1.f, 1.f, 0.08f), 0.f);
			Y += 14.f * Scale;
			const FName Weapon = Inv->GetArmedItem();
			const FName Spell = Inv->GetArmedMagic();
			Row(TEXT("Weapon"), Weapon.IsNone() ? FString(TEXT("-")) : FDinkPresentationData::Get().ItemName(Weapon));
			Row(TEXT("Spell"), Spell.IsNone() ? FString(TEXT("-")) : FDinkPresentationData::Get().ItemName(Spell));
		}
	};
}

double SDinkNarrativeOverlay::SeenAt(int32 Handle, const FString& Text, double Now) const
{
	TPair<FString, double>& Seen = SeenTexts.FindOrAdd(Handle, TPair<FString, double>(Text, Now));
	if (Seen.Key != Text)
	{
		Seen = TPair<FString, double>(Text, Now);
	}
	return Seen.Value;
}

namespace DinkOverlay
{
	constexpr double AppearSeconds = 0.18;
	constexpr double BoxFadeOutSeconds = 0.16;

	/** The "continue" chevron, bobbing. */
	void Chevron(FPainter& P, FVector2f Centre, float Size, double Now, const FLinearColor& Color)
	{
		const float Bob = 2.5f * FMath::Sin(static_cast<float>(Now) * 5.f);
		const FVector2f C = Centre + FVector2f(0.f, Bob);
		P.Lines({ C + FVector2f(-Size, -Size * 0.5f), C + FVector2f(0.f, Size * 0.5f), C + FVector2f(Size, -Size * 0.5f) }, Color, 2.2f);
	}

	struct FDialoguePainter
	{
		FPainter& P;
		const UDinkStorySubsystem& S;
		double Now;
		/** Top of the dialogue box when it is drawn this frame (menus and captions keep above it). */
		float BoxTop = -1.f;

		FVector2f View() const { return P.Size(); }

		float BoxWidth() const { return FMath::Min(1080.f, View().X - 96.f); }

		/** The dialogue box: name plate, wrapped text, continue hint. */
		void PaintBox(const SDinkNarrativeOverlay::FBoxContent& C, float PanelAlpha, float PanelSlide)
		{
			const float BaseAlpha = P.Alpha;
			const FSlateFontInfo Body = Font(TEXT("Regular"), 21.f);
			const float W = BoxWidth();
			const float PadX = 34.f;
			const float PadTop = C.Name.IsEmpty() ? 24.f : 30.f;
			const float PadBottom = C.bBlocking ? 34.f : 24.f;
			const float LineH = FPainter::LineHeight(Body) * 1.12f;
			const TArray<FString> Lines = Wrap(C.Text, Body, W - 2.f * PadX);
			const float H = PadTop + FMath::Max(2, Lines.Num()) * LineH + PadBottom;
			const FVector2f Pos((View().X - W) * 0.5f, View().Y - 40.f - H + PanelSlide);
			BoxTop = Pos.Y;

			P.Alpha = BaseAlpha * PanelAlpha;
			P.Shadow(Pos, FVector2f(W, H), 20.f);
			P.Box(Pos, FVector2f(W, H), PanelFill, 20.f, PanelEdge, 1.f);
			const float TextAlpha = EaseOut(static_cast<float>((Now - C.TextSince) / AppearSeconds));
			if (!C.Name.IsEmpty())
			{
				const FSlateFontInfo NameFont = Font(TEXT("Bold"), 14.f);
				const FVector2f NameSize = FPainter::Measure(C.Name, NameFont);
				const FVector2f Pill(NameSize.X + 32.f, NameSize.Y + 12.f);
				const FVector2f PillPos(Pos.X + 26.f, Pos.Y - Pill.Y * 0.5f);
				P.Box(PillPos, Pill, Accent, Pill.Y * 0.5f, FLinearColor(0.f, 0.f, 0.f, 0.25f), 1.f);
				P.TextCentered(PillPos + Pill * 0.5f, C.Name, NameFont, TextDark);
			}
			P.Alpha = BaseAlpha * PanelAlpha * TextAlpha;
			float Y = Pos.Y + PadTop + (1.f - TextAlpha) * 6.f;
			for (const FString& L : Lines)
			{
				P.Text(FVector2f(Pos.X + PadX, Y), L, Body, TextMain, true);
				Y += LineH;
			}
			if (C.bBlocking)
			{
				const FSlateFontInfo HintFont = Font(TEXT("Regular"), 12.f);
				const FString Hint = TEXT("Space / Enter / Click");
				const FVector2f HintSize = FPainter::Measure(Hint, HintFont);
				const FVector2f ChevronCentre(Pos.X + W - 30.f, Pos.Y + H - 18.f);
				// Measured widths come out a little short at small pixel sizes (hinting): keep a clear gap before the chevron.
				P.Text(FVector2f(ChevronCentre.X - 28.f - HintSize.X, ChevronCentre.Y - HintSize.Y * 0.5f), Hint, HintFont, TextDim);
				Chevron(P, ChevronCentre, 6.f, Now, Accent);
			}
			P.Alpha = BaseAlpha;
		}

		/** A compact bubble over a speaker's head (ScreenTop: the head's projection in local units). */
		void PaintBubble(FVector2f ScreenTop, const FString& Name, const FString& Text, float Alpha)
		{
			const float BaseAlpha = P.Alpha;
			P.Alpha = BaseAlpha * Alpha;
			const FSlateFontInfo Body = Font(TEXT("Regular"), 15.f);
			const FSlateFontInfo NameFont = Font(TEXT("Bold"), 11.f);
			const TArray<FString> Lines = Wrap(Text, Body, 340.f);
			float TextW = 0.f;
			for (const FString& L : Lines)
			{
				TextW = FMath::Max(TextW, FPainter::Measure(L, Body).X);
			}
			const float NameH = Name.IsEmpty() ? 0.f : FPainter::LineHeight(NameFont) + 2.f;
			TextW = FMath::Max(TextW, Name.IsEmpty() ? 0.f : FPainter::Measure(Name, NameFont).X);
			const float LineH = FPainter::LineHeight(Body) * 1.08f;
			const FVector2f Size(TextW + 28.f, NameH + Lines.Num() * LineH + 18.f);
			FVector2f Pos(ScreenTop.X - Size.X * 0.5f, ScreenTop.Y - Size.Y - 14.f + (1.f - Alpha) * 8.f);
			Pos.X = FMath::Clamp(Pos.X, 16.f, View().X - 16.f - Size.X);
			Pos.Y = FMath::Clamp(Pos.Y, 16.f, View().Y - 16.f - Size.Y);
			P.Shadow(Pos, Size, 14.f, 0.6f);
			// Tail: a small rotated square under the bubble, towards the head.
			const float TailX = FMath::Clamp(ScreenTop.X, Pos.X + 18.f, Pos.X + Size.X - 18.f);
			const float Tail = 12.f;
			const FSlateRoundedBoxBrush TailBrush(WithAlpha(PanelFill, P.Alpha), 2.f);
			FSlateDrawElement::MakeBox(P.Out, ++P.Layer,
				P.Geometry.ToPaintGeometry(FVector2f(Tail, Tail), FSlateLayoutTransform(FVector2f(TailX - Tail * 0.5f, Pos.Y + Size.Y - Tail * 0.5f - 1.f)), FSlateRenderTransform(FQuat2f(FMath::DegreesToRadians(45.f))), FVector2f(0.5f, 0.5f)),
				&TailBrush, ESlateDrawEffect::None, WithAlpha(PanelFill, P.Alpha));
			P.Box(Pos, Size, PanelFill, 14.f, PanelEdge, 1.f);
			float Y = Pos.Y + 9.f;
			if (!Name.IsEmpty())
			{
				P.Text(FVector2f(Pos.X + 14.f, Y), Name, NameFont, Accent);
				Y += NameH;
			}
			for (const FString& L : Lines)
			{
				P.Text(FVector2f(Pos.X + 14.f, Y), L, Body, TextMain);
				Y += LineH;
			}
			P.Alpha = BaseAlpha;
		}

		/** An _xy text: a centred card at the original's height (x and y on the 640x480 screen). */
		float PaintCaption(const FDinkActiveText& T, float Alpha, float AvoidBottom)
		{
			const float BaseAlpha = P.Alpha;
			P.Alpha = BaseAlpha * Alpha;
			const FSlateFontInfo Body = Font(TEXT("Light"), 24.f);
			const float MaxW = FMath::Min(1100.f, View().X - 96.f);
			const TArray<FString> Lines = Wrap(T.Text, Body, MaxW - 64.f);
			float TextW = 0.f;
			for (const FString& L : Lines)
			{
				TextW = FMath::Max(TextW, FPainter::Measure(L, Body).X);
			}
			const float LineH = FPainter::LineHeight(Body) * 1.1f;
			const FVector2f Size(TextW + 64.f, Lines.Num() * LineH + (T.bBlocking ? 46.f : 32.f));
			// The original centres an _xy text in a box that starts at x and is about 620 px wide.
			const float CentreX = FMath::Clamp((T.X + 310.f) / 640.f * View().X, Size.X * 0.5f + 24.f, View().X - Size.X * 0.5f - 24.f);
			float Top = T.Y / 480.f * View().Y - Size.Y * 0.5f;
			Top = FMath::Clamp(Top, 24.f, View().Y - 24.f - Size.Y);
			if (AvoidBottom > 0.f && Top + Size.Y > AvoidBottom - 16.f)
			{
				Top = AvoidBottom - 16.f - Size.Y;
			}
			const FVector2f Pos(CentreX - Size.X * 0.5f, Top + (1.f - Alpha) * 8.f);
			P.Shadow(Pos, Size, 18.f, 0.8f);
			P.Box(Pos, Size, FLinearColor(0.02f, 0.022f, 0.03f, 0.80f), 18.f, PanelEdge, 1.f);
			P.Box(FVector2f(Pos.X + Size.X * 0.5f - 24.f, Pos.Y + 10.f), FVector2f(48.f, 2.f), WithAlpha(Accent, 0.8f), 1.f);
			float Y = Pos.Y + 18.f;
			for (const FString& L : Lines)
			{
				P.TextCentered(FVector2f(CentreX, Y + LineH * 0.5f), L, Body, TextMain, true);
				Y += LineH;
			}
			if (T.bBlocking)
			{
				Chevron(P, FVector2f(CentreX, Pos.Y + Size.Y - 14.f), 5.f, Now, Accent);
			}
			P.Alpha = BaseAlpha;
			return Pos.Y;
		}

		/** The choice menu: title, rows with number badges, the highlighted row, key hints. */
		void PaintMenu(const FDinkMenu& M, float Alpha)
		{
			const float BaseAlpha = P.Alpha;
			P.Alpha = BaseAlpha * Alpha;
			const float W = FMath::Min(780.f, View().X - 96.f);
			const float PadX = 30.f;
			const FSlateFontInfo TitleFont = Font(TEXT("Regular"), 19.f);
			const FSlateFontInfo RowFont = Font(TEXT("Regular"), 18.f);
			const FSlateFontInfo BadgeFont = Font(TEXT("Bold"), 12.f);
			TArray<FString> Title;
			for (const FString& L : M.TitleLines)
			{
				if (!L.TrimStartAndEnd().IsEmpty())
				{
					Title.Append(Wrap(L, TitleFont, W - 2.f * PadX));
				}
			}
			// escape.c's Help > Keyboard commands is the 1997 text (verbatim: Ctrl, Space talk, Shift magic). Below it, the keys
			// this remaster actually uses, so the in-game help does not leave a player stuck.
			if (Title.Num() > 0 && Title[0].StartsWith(TEXT("Ctrl = Attack")))
			{
				Title.Add(TEXT(" "));
				for (const TCHAR* L : { TEXT("In this remaster: F, Left Ctrl or left click attack and choose; E talks; Q casts magic;"),
					TEXT("Enter or I opens the items; Space skips text (in cutscenes Enter too); Esc is this menu; M is the map; Shift walks slowly."),
					TEXT("Gamepad: X attack, B talk, Y magic, RB items, A choose and skip, Start menu, Back map, LB walk.") })
				{
					Title.Append(Wrap(L, TitleFont, W - 2.f * PadX));
				}
			}
			const float TitleLineH = FPainter::LineHeight(TitleFont) * 1.1f;
			const float RowH = 46.f;
			TArray<TArray<FString>> Rows;
			float RowsH = 0.f;
			for (const FDinkStoryChoice& C : M.Choices)
			{
				Rows.Add(Wrap(C.Text, RowFont, W - 2.f * PadX - 64.f));
				RowsH += FMath::Max(RowH, Rows.Last().Num() * FPainter::LineHeight(RowFont) + 18.f) + 6.f;
			}
			const float TitleH = Title.Num() > 0 ? Title.Num() * TitleLineH + 18.f : 0.f;
			const float H = 24.f + TitleH + RowsH + 8.f + 44.f;
			const float Bottom = BoxTop > 0.f ? BoxTop - 26.f : View().Y - 40.f;
			const FVector2f Pos((View().X - W) * 0.5f, FMath::Max(16.f, Bottom - H) + (1.f - Alpha) * 12.f);
			P.Shadow(Pos, FVector2f(W, H), 20.f);
			P.Box(Pos, FVector2f(W, H), PanelFill, 20.f, PanelEdge, 1.f);
			float Y = Pos.Y + 22.f;
			for (const FString& L : Title)
			{
				P.Text(FVector2f(Pos.X + PadX, Y), L, TitleFont, TextMain, true);
				Y += TitleLineH;
			}
			if (Title.Num() > 0)
			{
				Y += 6.f;
				P.Box(FVector2f(Pos.X + PadX, Y), FVector2f(W - 2.f * PadX, 1.f), FLinearColor(1.f, 1.f, 1.f, 0.08f), 0.f);
				Y += 12.f;
			}
			for (int32 i = 0; i < Rows.Num(); ++i)
			{
				const bool bSel = i == M.Selected;
				const float ThisH = FMath::Max(RowH, Rows[i].Num() * FPainter::LineHeight(RowFont) + 18.f);
				const FVector2f RowPos(Pos.X + 16.f, Y);
				const FVector2f RowSize(W - 32.f, ThisH);
				if (bSel)
				{
					P.Box(RowPos, RowSize, WithAlpha(Accent, 0.16f), 12.f, WithAlpha(Accent, 0.85f), 1.5f);
				}
				const FVector2f Badge(28.f, 28.f);
				const FVector2f BadgePos(RowPos.X + 14.f, RowPos.Y + (ThisH - Badge.Y) * 0.5f);
				if (i < 9)
				{
					P.Box(BadgePos, Badge, bSel ? Accent : FLinearColor(1.f, 1.f, 1.f, 0.09f), 8.f);
					P.TextCentered(BadgePos + Badge * 0.5f, FString::FromInt(i + 1), BadgeFont, bSel ? TextDark : TextDim);
				}
				float TY = RowPos.Y + (ThisH - Rows[i].Num() * FPainter::LineHeight(RowFont)) * 0.5f;
				for (const FString& L : Rows[i])
				{
					P.Text(FVector2f(BadgePos.X + Badge.X + 16.f, TY), L, RowFont, bSel ? TextMain : FLinearColor(0.82f, 0.83f, 0.85f, 1.f));
					TY += FPainter::LineHeight(RowFont);
				}
				Y += ThisH + 6.f;
			}
			Y += 8.f;
			P.Box(FVector2f(Pos.X + PadX, Y), FVector2f(W - 2.f * PadX, 1.f), FLinearColor(1.f, 1.f, 1.f, 0.08f), 0.f);
			float X = Pos.X + PadX;
			X += P.KeyHint(FVector2f(X, Y + 10.f), { TEXT("W"), TEXT("S") }, TEXT("Move")) + 22.f;
			X += P.KeyHint(FVector2f(X, Y + 10.f), { TEXT("1-9") }, TEXT("Pick")) + 22.f;
			P.KeyHint(FVector2f(X, Y + 10.f), { TEXT("Enter"), TEXT("Space"), TEXT("Click") }, TEXT("Choose"));
			P.Alpha = BaseAlpha;
		}
	};
}

namespace DinkOverlay
{
	/**
	 * The title screen (FDinkTitleScreen): the world behind a darkened left column, the name, the rows of the page, and key
	 * hints. Writes each row's absolute rectangle back for the mouse (FDinkTitleScreen::RowScreenRects).
	 */
	struct FTitlePainter
	{
		FPainter& P;
		const UDinkStorySubsystem& S;
		double Now;

		static constexpr float ColumnW = 760.f;

		void Paint()
		{
			const FDinkTitleScreen& T = S.GetTitleScreen();
			const FVector2f View = P.Size();
			const float Scale = FMath::Clamp(FMath::Min(View.X / 1920.f, View.Y / 1080.f), 0.55f, 1.6f);
			const float BaseAlpha = P.Alpha;

			// The column: dark at the left edge, fading out towards the picture (a few stacked bands).
			const float ColW = FMath::Min(ColumnW * Scale, View.X * 0.62f);
			for (int32 i = 0; i < 8; ++i)
			{
				const float W = ColW * (1.f - i * 0.085f);
				P.Box(FVector2f::ZeroVector, FVector2f(W, View.Y), FLinearColor(0.012f, 0.014f, 0.02f, 0.11f), 0.f);
			}
			// A light vignette over the whole picture.
			P.Box(FVector2f::ZeroVector, View, FLinearColor(0.f, 0.f, 0.f, 0.12f), 0.f);

			const float X = 96.f * Scale;
			float Y = View.Y * 0.16f;
			FSlateFontInfo Logo = Font(TEXT("Bold"), 64.f * Scale);
			Logo.LetterSpacing = 160;
			P.Text(FVector2f(X, Y), TEXT("DINK"), Logo, TextMain, true);
			Y += FPainter::LineHeight(Logo) * 0.92f;
			P.Text(FVector2f(X, Y), TEXT("SMALLWOOD"), Logo, Accent, true);
			Y += FPainter::LineHeight(Logo) * 1.02f;
			FSlateFontInfo Sub = Font(TEXT("Regular"), 15.f * Scale);
			Sub.LetterSpacing = 220;
			P.Text(FVector2f(X + 4.f * Scale, Y), TEXT("REMASTERED"), Sub, TextDim, true);
			Y += 70.f * Scale;

			// The page, sliding in when it changes.
			const float In = EaseOut(static_cast<float>((Now - T.PageChangedAt) / 0.22));
			P.Alpha = BaseAlpha * In;
			const float PageX = X + (1.f - In) * 18.f * Scale;
			T.RowScreenRects.Reset();
			if (T.Page == EDinkTitlePage::Main)
			{
				PaintRows(FVector2f(PageX, Y), Scale, 30.f, 62.f, 380.f);
			}
			else if (T.Page == EDinkTitlePage::Continue)
			{
				P.Text(FVector2f(PageX, Y - 30.f * Scale), TEXT("CONTINUE"), Font(TEXT("Bold"), 13.f * Scale), TextDim);
				PaintRows(FVector2f(PageX, Y), Scale, 18.f, 42.f, ColumnW - 160.f);
			}
			else
			{
				PaintControls(FVector2f(PageX, Y - 30.f * Scale), Scale);
			}
			P.Alpha = BaseAlpha;

			// Key hints and the build line.
			const float HintY = View.Y - 64.f * Scale;
			float HX = X;
			HX += P.KeyHint(FVector2f(HX, HintY), { TEXT("W"), TEXT("S") }, TEXT("Move"), Scale) + 26.f * Scale;
			HX += P.KeyHint(FVector2f(HX, HintY), { TEXT("Enter"), TEXT("Click") }, TEXT("Select"), Scale) + 26.f * Scale;
			if (T.Page != EDinkTitlePage::Main)
			{
				P.KeyHint(FVector2f(HX, HintY), { TEXT("Esc") }, TEXT("Back"), Scale);
			}
			const FSlateFontInfo Small = Font(TEXT("Regular"), 11.f * Scale);
			const FString Build = TEXT("Alpha build  -  based on Dink Smallwood (1997) by Robinson Technologies");
			const FVector2f BS = FPainter::Measure(Build, Small);
			P.Text(FVector2f(View.X - BS.X - 40.f * Scale, View.Y - 40.f * Scale), Build, Small, FLinearColor(1.f, 1.f, 1.f, 0.45f), true);
		}

		void PaintRows(FVector2f Pos, float Scale, float TextSize, float RowH, float RowW)
		{
			const FDinkTitleScreen& T = S.GetTitleScreen();
			const TArray<FString> Rows = S.GetTitleRows();
			const FSlateFontInfo RowFont = Font(TEXT("Regular"), TextSize * Scale);
			const FSlateFontInfo SelFont = Font(TEXT("Bold"), TextSize * Scale);
			const float H = RowH * Scale;
			const float W = RowW * Scale;
			float Y = Pos.Y;
			for (int32 i = 0; i < Rows.Num(); ++i)
			{
				const bool bSel = i == T.Selected;
				const bool bEnabled = S.IsTitleRowEnabled(i);
				const bool bBack = T.Page == EDinkTitlePage::Continue && i == Rows.Num() - 1;
				if (bBack)
				{
					Y += 10.f * Scale; // a little room before Back
				}
				const FVector2f RowPos(Pos.X - 22.f * Scale, Y);
				const FVector2f RowSize(W, H - 6.f * Scale);
				if (bSel)
				{
					const float Glow = 0.12f + 0.05f * Pulse(Now);
					P.Box(RowPos, RowSize, WithAlpha(Accent, Glow), 10.f * Scale);
					P.Box(RowPos + FVector2f(0.f, 8.f * Scale), FVector2f(4.f * Scale, RowSize.Y - 16.f * Scale), Accent, 2.f * Scale);
				}
				const FLinearColor Color = !bEnabled ? FLinearColor(1.f, 1.f, 1.f, 0.30f) : (bSel ? TextMain : FLinearColor(0.80f, 0.81f, 0.84f, 1.f));
				const FSlateFontInfo& F = bSel ? SelFont : RowFont;
				const float TY = Y + (RowSize.Y - FPainter::LineHeight(F)) * 0.5f;
				P.Text(FVector2f(Pos.X, TY), Rows[i], F, Color, true);
				// Absolute rectangle for the mouse.
				const FVector2D A = P.Geometry.LocalToAbsolute(FVector2D(RowPos));
				const FVector2D B = P.Geometry.LocalToAbsolute(FVector2D(RowPos + RowSize));
				T.RowScreenRects.Add(FBox2D(A, B));
				Y += H;
			}
		}

		void PaintControls(FVector2f Pos, float Scale)
		{
			P.Text(Pos, TEXT("CONTROLS"), Font(TEXT("Bold"), 13.f * Scale), TextDim);
			struct FRow { const TCHAR* Action; const TCHAR* Keys; const TCHAR* Pad; };
			static const FRow Rows[] = {
				{ TEXT("Move"), TEXT("WASD / arrows"), TEXT("Left stick") },
				{ TEXT("Walk slowly"), TEXT("Shift"), TEXT("LB") },
				{ TEXT("Attack / use item"), TEXT("F, Left Ctrl, left click"), TEXT("X, right trigger") },
				{ TEXT("Talk"), TEXT("E"), TEXT("B") },
				{ TEXT("Choose in a menu"), TEXT("Enter, Space, E, F, click"), TEXT("A") },
				{ TEXT("Skip a line"), TEXT("Space"), TEXT("A") },
				{ TEXT("Skip a line in a cutscene"), TEXT("Space, Enter, E, click"), TEXT("A") },
				{ TEXT("Cast magic"), TEXT("Q"), TEXT("Y") },
				{ TEXT("Inventory"), TEXT("Enter, I"), TEXT("RB") },
				{ TEXT("Quick-arm item 1-10"), TEXT("1-9, 0"), TEXT("") },
				{ TEXT("Menu (load, restart, quit, help)"), TEXT("Esc"), TEXT("Start") },
				{ TEXT("Map"), TEXT("M"), TEXT("Back / View") },
			};
			const FSlateFontInfo A = Font(TEXT("Bold"), 15.f * Scale);
			const FSlateFontInfo K = Font(TEXT("Regular"), 15.f * Scale);
			float Y = Pos.Y + 34.f * Scale;
			// Columns as wide as their longest entry (fixed offsets let the long action names run into the keys).
			float WAction = 0.f, WKeys = 0.f;
			for (const FRow& R : Rows)
			{
				WAction = FMath::Max(WAction, FPainter::Measure(R.Action, A).X);
				WKeys = FMath::Max(WKeys, FPainter::Measure(R.Keys, K).X);
			}
			const float C1 = Pos.X, C2 = C1 + WAction + 28.f * Scale, C3 = C2 + WKeys + 28.f * Scale;
			P.Text(FVector2f(C2, Y), TEXT("KEYBOARD / MOUSE"), Font(TEXT("Bold"), 10.f * Scale), TextDim);
			P.Text(FVector2f(C3, Y), TEXT("GAMEPAD"), Font(TEXT("Bold"), 10.f * Scale), TextDim);
			Y += 24.f * Scale;
			for (const FRow& R : Rows)
			{
				P.Text(FVector2f(C1, Y), R.Action, A, TextMain, true);
				P.Text(FVector2f(C2, Y), R.Keys, K, FLinearColor(0.82f, 0.83f, 0.86f, 1.f), true);
				P.Text(FVector2f(C3, Y), R.Pad, K, FLinearColor(0.82f, 0.83f, 0.86f, 1.f), true);
				Y += 31.f * Scale;
			}
			P.Text(FVector2f(C1, Y + 6.f * Scale), TEXT("Save your game at the save machines you find on your travels."), Font(TEXT("Italic"), 13.f * Scale), TextDim, true);
			Y += 56.f * Scale;
			// The one row: Back.
			const FDinkTitleScreen& T = S.GetTitleScreen();
			T.RowScreenRects.Reset();
			const FVector2f RowPos(C1 - 22.f * Scale, Y);
			const FVector2f RowSize(220.f * Scale, 40.f * Scale);
			P.Box(RowPos, RowSize, WithAlpha(Accent, 0.12f + 0.05f * Pulse(Now)), 10.f * Scale);
			P.Box(RowPos + FVector2f(0.f, 8.f * Scale), FVector2f(4.f * Scale, RowSize.Y - 16.f * Scale), Accent, 2.f * Scale);
			P.Text(FVector2f(C1, Y + (RowSize.Y - FPainter::LineHeight(A)) * 0.5f), TEXT("Back"), A, TextMain, true);
			const FVector2D PA = P.Geometry.LocalToAbsolute(FVector2D(RowPos));
			const FVector2D PB = P.Geometry.LocalToAbsolute(FVector2D(RowPos + RowSize));
			T.RowScreenRects.Add(FBox2D(PA, PB));
		}
	};

	/**
	 * The status HUD: the original's always-on status bar (life, experience, magic charge, gold, the armed weapon and spell,
	 * dink.cpp draw_status_all) as a compact panel in the top left, from the same facts the inventory's status column reads.
	 */
	struct FStatusPainter
	{
		FPainter& P;
		const SDinkNarrativeOverlay& Overlay;
		const UDinkStorySubsystem& S;

		void Bar(FVector2f Pos, FVector2f Size, float Fraction, const FLinearColor& Color)
		{
			P.Box(Pos, Size, FLinearColor(1.f, 1.f, 1.f, 0.10f), Size.Y * 0.5f);
			const float Fill = Size.X * FMath::Clamp(Fraction, 0.f, 1.f);
			if (Fill >= Size.Y)
			{
				P.Box(Pos, FVector2f(Fill, Size.Y), Color, Size.Y * 0.5f);
			}
		}

		void Slot(FVector2f Pos, float Size, FName Script, bool bMagic, float Scale)
		{
			P.Box(Pos, FVector2f(Size, Size), FLinearColor(1.f, 1.f, 1.f, Script.IsNone() ? 0.04f : 0.08f), 10.f * Scale, FLinearColor(1.f, 1.f, 1.f, 0.10f), 1.f);
			if (Script.IsNone())
			{
				return;
			}
			const FVector2f C = Pos + FVector2f(Size, Size) * 0.5f;
			if (const FSlateBrush* Icon = Overlay.FindItemIcon(Script))
			{
				P.Image(C - FVector2f(Size, Size) * 0.36f, FVector2f(Size, Size) * 0.72f, Icon);
			}
			else
			{
				const FLinearColor Disc = bMagic ? MagicBlue : Accent;
				P.TextCentered(C, Monogram(FDinkPresentationData::Get().ItemName(Script)), Font(TEXT("Bold"), 15.f * Scale), Disc);
			}
		}

		void Paint()
		{
			const UDinkFactSubsystem* F = S.GetFacts();
			UDinkDirector* D = S.GetDirector();
			UDinkInventoryComponent* Inv = D ? D->GetInventory() : nullptr;
			if (!F)
			{
				return;
			}
			auto Fact = [F](const TCHAR* Name) { return F->GetFact(Name); };
			const FVector2f View = P.Size();
			const float Scale = FMath::Clamp(FMath::Min(View.X / 1920.f, View.Y / 1080.f), 0.6f, 1.5f);
			const FVector2f Pos(28.f * Scale, 24.f * Scale);
			const FVector2f Size(392.f * Scale, 112.f * Scale);
			P.Shadow(Pos, Size, 16.f * Scale, 0.6f);
			P.Box(Pos, Size, WithAlpha(PanelFill, 0.80f), 16.f * Scale, PanelEdge, 1.f);

			// Level badge.
			const FVector2f Badge = Pos + FVector2f(14.f, 14.f) * Scale;
			const float BadgeS = 52.f * Scale;
			P.Box(Badge, FVector2f(BadgeS, BadgeS), WithAlpha(Accent, 0.18f), 12.f * Scale, WithAlpha(Accent, 0.7f), 1.5f);
			P.TextCentered(Badge + FVector2f(BadgeS * 0.5f, BadgeS * 0.36f), FString::FromInt(Fact(TEXT("level"))), Font(TEXT("Bold"), 20.f * Scale), Accent);
			P.TextCentered(Badge + FVector2f(BadgeS * 0.5f, BadgeS * 0.78f), TEXT("LEVEL"), Font(TEXT("Bold"), 7.f * Scale), TextDim);

			// Life and experience.
			const float BX = Badge.X + BadgeS + 14.f * Scale;
			const float BW = 196.f * Scale;
			const int32 Life = Fact(TEXT("life"));
			const int32 LifeMax = FMath::Max(1, Fact(TEXT("lifemax")));
			const FSlateFontInfo Label = Font(TEXT("Bold"), 10.f * Scale);
			const FSlateFontInfo Val = Font(TEXT("Regular"), 10.f * Scale);
			P.Text(FVector2f(BX, Badge.Y - 2.f * Scale), TEXT("LIFE"), Label, TextDim);
			const FString LifeText = FString::Printf(TEXT("%d / %d"), FMath::Max(0, Life), LifeMax);
			P.Text(FVector2f(BX + BW - FPainter::Measure(LifeText, Val).X, Badge.Y - 2.f * Scale), LifeText, Val, TextMain);
			Bar(FVector2f(BX, Badge.Y + 15.f * Scale), FVector2f(BW, 9.f * Scale), static_cast<float>(Life) / LifeMax, LifeRed);
			const int32 Level = Fact(TEXT("level"));
			const int32 Next = FMath::Max(1, DinkRules::ExpForNextLevel(Level));
			P.Text(FVector2f(BX, Badge.Y + 30.f * Scale), TEXT("EXP"), Label, TextDim);
			const FString ExpText = FString::Printf(TEXT("%d / %d"), Fact(TEXT("exp")), Next);
			P.Text(FVector2f(BX + BW - FPainter::Measure(ExpText, Val).X, Badge.Y + 30.f * Scale), ExpText, Val, TextMain);
			Bar(FVector2f(BX, Badge.Y + 46.f * Scale), FVector2f(BW, 5.f * Scale), static_cast<float>(Fact(TEXT("exp"))) / Next, Accent);

			// Gold and magic charge on the bottom line.
			const float LineY = Pos.Y + Size.Y - 30.f * Scale;
			P.Box(FVector2f(Badge.X + 2.f * Scale, LineY + 3.f * Scale), FVector2f(12.f, 12.f) * Scale, FLinearColor(0.98f, 0.80f, 0.28f, 1.f), 6.f * Scale);
			P.Text(FVector2f(Badge.X + 22.f * Scale, LineY), FString::Printf(TEXT("%d gold"), Fact(TEXT("gold"))), Font(TEXT("Regular"), 12.f * Scale), TextMain);
			const int32 Cost = Fact(TEXT("magic_cost"));
			if (Cost > 0)
			{
				P.Text(FVector2f(BX + 34.f * Scale, LineY + 1.f * Scale), TEXT("MAGIC"), Label, TextDim);
				Bar(FVector2f(BX + 80.f * Scale, LineY + 5.f * Scale), FVector2f(BW - 80.f * Scale, 7.f * Scale), static_cast<float>(Fact(TEXT("magic_level"))) / Cost,
					Fact(TEXT("magic_level")) >= Cost ? FLinearColor(0.55f, 0.75f, 1.f, 1.f) : MagicBlue);
			}

			// The armed weapon and spell.
			if (Inv)
			{
				const float SlotS = 46.f * Scale;
				const float SX = Pos.X + Size.X - 2.f * SlotS - 22.f * Scale;
				Slot(FVector2f(SX, Badge.Y), SlotS, Inv->GetArmedItem(), false, Scale);
				Slot(FVector2f(SX + SlotS + 8.f * Scale, Badge.Y), SlotS, Inv->GetArmedMagic(), true, Scale);
				P.TextCentered(FVector2f(SX + SlotS * 0.5f, Badge.Y + SlotS + 12.f * Scale), TEXT("WEAPON"), Font(TEXT("Bold"), 7.f * Scale), TextDim);
				P.TextCentered(FVector2f(SX + SlotS * 1.5f + 8.f * Scale, Badge.Y + SlotS + 12.f * Scale), TEXT("MAGIC"), Font(TEXT("Bold"), 7.f * Scale), TextDim);
			}
		}
	};
}

namespace DinkOverlay
{
	/**
	 * show_bmp("tiles\\map1.bmp", 1, 0) (button6.c, the map item): the 1997 picture is a painted map of the mainland with the
	 * place names and, because showdot is 1, a pulsing dot on Dink's last outdoor screen (process_show_bmp, dink.cpp:16745-16762).
	 * The remaster draws the same from its own world layout: every outdoor screen of the mainland sheet by kind (land, town,
	 * sea), the region names, and the dot where Dink last stood outdoors.
	 */
	struct FMapPainter
	{
		FPainter& P;
		const UDinkStorySubsystem& S;
		const SDinkNarrativeOverlay::FMapData& Map;
		FVector2D DinkMetres;
		bool bHasDink;
		double Now;
		double Since;

		void Paint()
		{
			const FVector2f View = P.Size();
			const float In = EaseOut(static_cast<float>((Now - Since) / 0.2));
			const float BaseAlpha = P.Alpha;
			P.Alpha = BaseAlpha * In;
			P.Box(FVector2f::ZeroVector, View, FLinearColor(0.f, 0.f, 0.f, 0.7f), 0.f);
			const FVector2f PanelPos(48.f, 40.f);
			const FVector2f PanelSize(View.X - 96.f, View.Y - 80.f);
			P.Shadow(PanelPos, PanelSize, 22.f);
			P.Box(PanelPos, PanelSize, FLinearColor(0.10f, 0.09f, 0.07f, 0.97f), 22.f, PanelEdge, 1.f);
			P.Text(PanelPos + FVector2f(32.f, 22.f), TEXT("Map"), Font(TEXT("Bold"), 26.f), TextMain);
			{
				const float W = FPainter::KeyHintWidth({ TEXT("Enter"), TEXT("Esc"), TEXT("M") }, TEXT("Close"));
				P.KeyHint(PanelPos + FVector2f(PanelSize.X - 32.f - W, 28.f), { TEXT("Enter"), TEXT("Esc"), TEXT("M") }, TEXT("Close"));
			}
			if (Map.Screens.Num() == 0 || !Map.Bounds.bIsValid)
			{
				P.TextCentered(PanelPos + PanelSize * 0.5f, TEXT("No map of this land."), Font(TEXT("Regular"), 18.f), TextDim);
				P.Alpha = BaseAlpha;
				return;
			}
			// Fit the land into the panel, keeping its shape.
			const FVector2f AreaPos = PanelPos + FVector2f(32.f, 78.f);
			const FVector2f AreaSize = PanelSize - FVector2f(64.f, 110.f);
			const FVector2D Extent = Map.Bounds.GetSize();
			const float K = FMath::Min(AreaSize.X / static_cast<float>(Extent.X), AreaSize.Y / static_cast<float>(Extent.Y));
			const FVector2f Offset = AreaPos + (AreaSize - FVector2f(static_cast<float>(Extent.X), static_cast<float>(Extent.Y)) * K) * 0.5f;
			auto ToPanel = [&](const FVector2D& M) { return Offset + FVector2f(static_cast<float>(M.X - Map.Bounds.Min.X), static_cast<float>(M.Y - Map.Bounds.Min.Y)) * K; };

			for (const SDinkNarrativeOverlay::FMapScreen& Sc : Map.Screens)
			{
				const FVector2f A = ToPanel(Sc.Min);
				const FVector2f B = ToPanel(Sc.Max);
				FLinearColor C = Sc.Kind == 2 ? FLinearColor(0.15f, 0.30f, 0.46f, 1.f) : (Sc.Kind == 1 ? FLinearColor(0.56f, 0.46f, 0.30f, 1.f) : FLinearColor(0.25f, 0.36f, 0.19f, 1.f));
				// A little variation per screen so the land reads as land, not a grid of one colour.
				const float V = 0.94f + 0.06f * static_cast<float>((Sc.Screen * 7919) % 13) / 12.f;
				C = FLinearColor(C.R * V, C.G * V, C.B * V, 1.f);
				P.Box(A, (B - A) + FVector2f(0.6f, 0.6f), C, 0.f);
			}
			// Place names.
			const FSlateFontInfo LabelFont = Font(TEXT("Bold"), 15.f);
			for (const TPair<FString, FVector2D>& L : Map.Labels)
			{
				P.TextCentered(ToPanel(L.Value), L.Key, LabelFont, FLinearColor(0.98f, 0.92f, 0.70f, 1.f), true);
			}
			// The compass, as on the painted map.
			const FVector2f Compass = AreaPos + FVector2f(40.f, 40.f);
			P.TextCentered(Compass + FVector2f(0.f, -22.f), TEXT("N"), Font(TEXT("Bold"), 16.f), Accent, true);
			P.Lines({ Compass + FVector2f(0.f, -10.f), Compass + FVector2f(0.f, 18.f) }, Accent, 2.f);
			P.Lines({ Compass + FVector2f(-12.f, 4.f), Compass + FVector2f(12.f, 4.f) }, Accent, 2.f);
			// Dink's dot (showdot).
			if (bHasDink)
			{
				const FVector2f D = ToPanel(DinkMetres);
				const float R = 7.f + 3.f * Pulse(Now);
				P.Box(D - FVector2f(R + 4.f, R + 4.f), FVector2f(2.f * (R + 4.f), 2.f * (R + 4.f)), FLinearColor(1.f, 0.85f, 0.35f, 0.25f), R + 4.f);
				P.Box(D - FVector2f(R, R), FVector2f(2.f * R, 2.f * R), FLinearColor(0.95f, 0.22f, 0.16f, 1.f), R, FLinearColor::White, 1.5f);
				P.Text(D + FVector2f(R + 8.f, -10.f), TEXT("Dink"), Font(TEXT("Bold"), 13.f), TextMain, true);
			}
			P.Alpha = BaseAlpha;
		}
	};
}

void SDinkNarrativeOverlay::EnsureMapData(const UWorld* World) const
{
	if (MapData.World.Get() == World && MapData.Screens.Num() > 0)
	{
		return;
	}
	MapData = FMapData();
	MapData.World = World;
	if (!World)
	{
		return;
	}
	static const FName Mainland(TEXT("mainland"));
	TMap<FString, TPair<FVector2D, int32>> Regions;
	for (TActorIterator<ADinkScreenVolume> It(const_cast<UWorld*>(World)); It; ++It)
	{
		const ADinkScreenVolume* V = *It;
		if (V->Sheet != Mainland || V->bIndoor)
		{
			continue;
		}
		const FDinkScreenCorners& C = V->Corners;
		FMapScreen& Sc = MapData.Screens.AddDefaulted_GetRef();
		Sc.Screen = V->ScreenNumber;
		Sc.Min = FVector2D(FMath::Min(FMath::Min(C.NW.X, C.SW.X), FMath::Min(C.NE.X, C.SE.X)), FMath::Min(FMath::Min(C.NW.Y, C.NE.Y), FMath::Min(C.SW.Y, C.SE.Y)));
		Sc.Max = FVector2D(FMath::Max(FMath::Max(C.NW.X, C.SW.X), FMath::Max(C.NE.X, C.SE.X)), FMath::Max(FMath::Max(C.NW.Y, C.NE.Y), FMath::Max(C.SW.Y, C.SE.Y)));
		Sc.Kind = V->Kind == FName(TEXT("sea")) ? 2 : (V->Kind == FName(TEXT("settlement")) ? 1 : 0);
		MapData.Bounds += FBox2D(Sc.Min, Sc.Max);
		const FString Name = V->RegionName;
		if (!Name.IsEmpty() && Sc.Kind != 2)
		{
			TPair<FVector2D, int32>& R = Regions.FindOrAdd(Name, TPair<FVector2D, int32>(FVector2D::ZeroVector, 0));
			R.Key += (Sc.Min + Sc.Max) * 0.5;
			++R.Value;
		}
	}
	for (const TPair<FString, TPair<FVector2D, int32>>& R : Regions)
	{
		if (R.Value.Value > 0)
		{
			MapData.Labels.Add(R.Key, R.Value.Key / R.Value.Value);
		}
	}
}

bool SDinkNarrativeOverlay::IsVoiceStillSpeaking(const UDinkStorySubsystem& S, const FBoxContent& C)
{
	const UWorld* World = S.GetWorld();
	const UDinkAudioSubsystem* Audio = World ? World->GetSubsystem<UDinkAudioSubsystem>() : nullptr;
	return Audio && !C.LineId.IsEmpty() && Audio->IsVoiceTailPlaying(C.Handle, C.LineId);
}

void SDinkNarrativeOverlay::PaintNarrative(FPainterRef PRef, const UDinkStorySubsystem& S, double Now) const
{
	FPainter& P = *static_cast<FPainter*>(PRef);
	// Fade (fade_down / fade_up) under the texts, as in the original.
	if (const float Fade = S.GetFadeAlpha(); Fade > 0.f)
	{
		P.Box(FVector2f::ZeroVector, P.Size(), FLinearColor(0.f, 0.f, 0.f, Fade), 0.f);
	}

	const TArray<FDinkActiveText>& Texts = S.GetActiveTexts();
	// Forget texts that are gone (their handles get reused).
	for (auto It = SeenTexts.CreateIterator(); It; ++It)
	{
		if (!Texts.ContainsByPredicate([&](const FDinkActiveText& T) { return T.Handle == It.Key(); }))
		{
			It.RemoveCurrent();
		}
	}

	// The box: the newest blocking line; with none, the newest spoken line.
	int32 BoxIdx = INDEX_NONE;
	for (int32 i = Texts.Num() - 1; i >= 0 && BoxIdx == INDEX_NONE; --i)
	{
		BoxIdx = !Texts[i].bXY && Texts[i].bBlocking ? i : INDEX_NONE;
	}
	for (int32 i = Texts.Num() - 1; i >= 0 && BoxIdx == INDEX_NONE; --i)
	{
		BoxIdx = !Texts[i].bXY ? i : INDEX_NONE;
	}

	FDialoguePainter D{ P, S, Now };
	if (BoxIdx != INDEX_NONE)
	{
		const FDinkActiveText& T = Texts[BoxIdx];
		const double Since = SeenAt(T.Handle, T.Text, Now);
		if (BoxGoneAt >= 0.0 && Now - BoxGoneAt > BoxFadeOutSeconds)
		{
			BoxSince = Now; // the panel was hidden: it slides in again
		}
		else if (Box.Handle == 0)
		{
			BoxSince = Now;
		}
		BoxGoneAt = -1.0;
		Box.Handle = T.Handle;
		Box.LineId = T.LineId;
		Box.Name = FDinkPresentationData::Get().SpeakerName(T.LineId, T.Owner);
		Box.Text = T.Text;
		Box.bBlocking = T.bBlocking;
		Box.TextSince = Since;
		const float In = EaseOut(static_cast<float>((Now - BoxSince) / AppearSeconds));
		D.PaintBox(Box, In, (1.f - In) * 16.f);
	}
	else if (Box.Handle != 0 && IsVoiceStillSpeaking(S, Box))
	{
		// The text timed out but its recording is still finishing: the words stay up with the voice (no continue hint).
		SDinkNarrativeOverlay::FBoxContent Speaking = Box;
		Speaking.bBlocking = false;
		const float In = EaseOut(static_cast<float>((Now - BoxSince) / AppearSeconds));
		D.PaintBox(Speaking, In, (1.f - In) * 16.f);
	}
	else if (Box.Handle != 0)
	{
		if (BoxGoneAt < 0.0)
		{
			BoxGoneAt = Now;
		}
		const float Out = 1.f - EaseOut(static_cast<float>((Now - BoxGoneAt) / BoxFadeOutSeconds));
		if (Out > 0.f)
		{
			SDinkNarrativeOverlay::FBoxContent Fading = Box;
			Fading.bBlocking = false;
			Fading.TextSince = 0.0;
			D.PaintBox(Fading, Out, 0.f);
		}
		else
		{
			Box = FBoxContent();
		}
	}

	// Bubbles: the other spoken lines, over their speakers' heads.
	const UWorld* World = S.GetWorld();
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	FVector2D ViewportPx(0.0, 0.0);
	if (World && World->GetGameViewport())
	{
		World->GetGameViewport()->GetViewportSize(ViewportPx);
	}
	UDinkDirector* Director = S.GetDirector();
	for (int32 i = 0; i < Texts.Num(); ++i)
	{
		const FDinkActiveText& T = Texts[i];
		if (i == BoxIdx || T.bXY || !PC || !Director || ViewportPx.X <= 0.0)
		{
			continue;
		}
		AActor* Speaker = Director->GetActor(T.Owner);
		if (!Speaker)
		{
			continue;
		}
		FVector Origin, Extent;
		Speaker->GetActorBounds(/*bOnlyCollidingComponents*/ false, Origin, Extent);
		FVector2D ScreenPx;
		if (!UGameplayStatics::ProjectWorldToScreen(PC, Origin + FVector(0, 0, Extent.Z + 20.0), ScreenPx, false))
		{
			continue; // behind the camera
		}
		const FVector2f Local(ScreenPx.X / ViewportPx.X * P.Size().X, ScreenPx.Y / ViewportPx.Y * P.Size().Y);
		const float In = EaseOut(static_cast<float>((Now - SeenAt(T.Handle, T.Text, Now)) / AppearSeconds));
		D.PaintBubble(Local, FDinkPresentationData::Get().SpeakerName(T.LineId, T.Owner), T.Text, In);
	}

	// Captions (_xy texts).
	float AvoidBottom = D.BoxTop;
	for (const FDinkActiveText& T : Texts)
	{
		if (T.bXY)
		{
			const float In = EaseOut(static_cast<float>((Now - SeenAt(T.Handle, T.Text, Now)) / AppearSeconds));
			const float Top = D.PaintCaption(T, In, AvoidBottom);
			AvoidBottom = AvoidBottom > 0.f ? FMath::Min(AvoidBottom, Top) : -1.f;
		}
	}

	// The choice menu.
	if (const FDinkMenu* M = S.GetActiveMenu())
	{
		if (M->InstanceId != SeenMenu)
		{
			SeenMenu = M->InstanceId;
			MenuSince = Now;
		}
		D.PaintMenu(*M, EaseOut(static_cast<float>((Now - MenuSince) / AppearSeconds)));
	}
	else
	{
		SeenMenu = 0;
	}
}

int32 SDinkNarrativeOverlay::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect, FSlateWindowElementList& OutDrawElements,
	int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	const UDinkStorySubsystem* S = Story.Get();
	if (!S || !S->IsReady())
	{
		return LayerId;
	}
	FPainter P(AllottedGeometry, OutDrawElements, LayerId);
	const double Now = FPlatformTime::Seconds();
	const FDinkInventoryScreen& Inv = S->GetInventoryScreen();
	const FDinkTitleScreen& Title = S->GetTitleScreen();
	if (Title.bOpen)
	{
		// Fade in from black over the first moment (the camera settles), then the title.
		const float Black = 1.f - EaseOut(static_cast<float>((Now - Title.OpenedAt) / 0.9));
		FTitlePainter{ P, *S, Now }.Paint();
		if (Black > 0.f)
		{
			P.Box(FVector2f::ZeroVector, P.Size(), FLinearColor(0.f, 0.f, 0.f, Black), 0.f);
		}
		return P.Layer;
	}
	// The status bar, under the fades and the texts (the original draws it beside the play area all game).
	if (!Inv.bOpen && !S->bNewGamePending)
	{
		FStatusPainter{ P, *this, *S }.Paint();
	}
	// The original draws no text while the item screen is up (dink.cpp:17364, bRenderDinkText = false).
	if (!Inv.bOpen)
	{
		PaintNarrative(&P, *S, Now);
	}
	// Where Dink stands outdoors (the map's dot), and a show_bmp map on top of everything (the original draws only the
	// picture while it is up, dink.cpp:17370).
	if (const UWorld* World = S->GetWorld())
	{
		const UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
		const ADinkScreenVolume* Screen = Greybox ? Greybox->GetCurrentScreen() : nullptr;
		const APlayerController* PC = World->GetFirstPlayerController();
		const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
		if (const FDinkShownBitmap* Bitmap = S->GetShownBitmap(); Bitmap && Bitmap->IsWorldMap())
		{
			EnsureMapData(World);
			// The dot: where Dink stands when he is outdoors on the mainland, else the middle of his last outdoor screen (the
			// story's last_map, which is saved with the game), when that screen is on the mainland map.
			FVector2D Dot = FVector2D::ZeroVector;
			bool bDot = false;
			static const FName Mainland(TEXT("mainland"));
			if (Screen && Pawn && !Screen->bIndoor && Screen->Sheet == Mainland)
			{
				Dot = DinkLayout::UnrealToMetres(Pawn->GetActorLocation());
				bDot = true;
			}
			else if (const ADinkScreenVolume* Last = Greybox ? Greybox->FindScreen(S->GetLastOutdoorScreen()) : nullptr; Last && Last->Sheet == Mainland)
			{
				Dot = DinkLayout::MapPixelToMetres(Last->Corners, 300.0, 200.0);
				bDot = true;
			}
			FMapPainter{ P, *S, MapData, Dot, bDot, Now, Bitmap->Since }.Paint();
		}
	}
	// The title fades out over the game after New Game / Continue.
	if (Title.ClosedAt >= 0.0 && Now - Title.ClosedAt < 0.45)
	{
		P.Alpha = 1.f - EaseOut(static_cast<float>((Now - Title.ClosedAt) / 0.45));
		FTitlePainter{ P, *S, Now }.Paint();
		P.Alpha = 1.f;
	}
	if (Inv.bOpen || Now - Inv.ChangedAt < 0.16)
	{
		P.Alpha = Inv.bOpen ? 1.f : 1.f - EaseOut(static_cast<float>((Now - Inv.ChangedAt) / 0.16));
		FInventoryPainter{ P, *this, *S, Inv.bOpen ? Now : Inv.ChangedAt + 0.16 }.Paint();
	}
	return P.Layer;
}
