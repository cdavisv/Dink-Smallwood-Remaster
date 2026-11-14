// The narrative layer's Slate overlay: the inventory screen. See DinkNarrativeOverlay.h.

#include "DinkNarrativeOverlay.h"
#include "DinkCombat.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkGameplay.h"
#include "DinkInventoryComponent.h"
#include "DinkPresentationData.h"
#include "DinkStorySubsystem.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "Engine/Texture2D.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "HAL/PlatformTime.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"

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
			const FSlateRoundedBoxBrush Brush(WithAlpha(Fill, Alpha), Radius, WithAlpha(Outline, Alpha), OutlineWidth);
			FSlateDrawElement::MakeBox(Out, ++Layer, Geometry.ToPaintGeometry(BoxSize, FSlateLayoutTransform(Pos)), &Brush);
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
	if (Inv.bOpen || Now - Inv.ChangedAt < 0.16)
	{
		if (!Inv.bOpen)
		{
			P.Alpha = 1.f - EaseOut(static_cast<float>((Now - Inv.ChangedAt) / 0.16));
		}
		FInventoryPainter{ P, *this, *S, Inv.bOpen ? Now : Inv.ChangedAt + 0.16 }.Paint();
	}
	return P.Layer;
}
