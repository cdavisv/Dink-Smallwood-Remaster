// Minimal presentation of the narrative layer: floating text over speakers, the menu and the fade,
// drawn on the HUD canvas from C++ (no widget assets). The keyboard/mouse pre-processor is DinkNarrativeInput.cpp.

#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "DinkGameplay.h"
#include "CanvasItem.h"
#include "Engine/Canvas.h"
#include "Engine/Console.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/HUD.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"

namespace
{
	/** Word wrap at roughly the original's text box width (about 40 characters). */
	TArray<FString> Wrap(const FString& Text, int32 Width = 40)
	{
		TArray<FString> Words;
		Text.ParseIntoArray(Words, TEXT(" "), true);
		TArray<FString> Lines;
		FString Line;
		for (const FString& W : Words)
		{
			if (!Line.IsEmpty() && Line.Len() + 1 + W.Len() > Width)
			{
				Lines.Add(Line);
				Line.Reset();
			}
			Line += Line.IsEmpty() ? W : TEXT(" ") + W;
		}
		if (!Line.IsEmpty() || Lines.Num() == 0)
		{
			Lines.Add(Line);
		}
		return Lines;
	}

	/** Text scale for the current canvas: the engine's medium font is about 12 px tall, unreadable at 1080p. */
	float GTextScale = 1.f;

	void DrawCentered(UCanvas* Canvas, UFont* Font, const FString& Text, const FVector2D& Centre, const FLinearColor& Color)
	{
		float W = 0.f, H = 0.f;
		Canvas->StrLen(Font, Text, W, H);
		FCanvasTextItem Item(FVector2D(Centre.X - W * GTextScale * 0.5f, Centre.Y), FText::FromString(Text), Font, Color);
		Item.Scale = FVector2D(GTextScale, GTextScale);
		Item.EnableShadow(FLinearColor::Black);
		Canvas->DrawItem(Item);
	}
}

void UDinkStorySubsystem::DrawHUD(AHUD* HUD, UCanvas* Canvas)
{
	if (!HUD || !Canvas || !IsReady() || HUD->GetWorld() != GetWorld())
	{
		return;
	}
	UFont* Font = GEngine ? GEngine->GetMediumFont() : nullptr;
	if (!Font)
	{
		return;
	}
	const float SizeX = Canvas->ClipX;
	const float SizeY = Canvas->ClipY;

	// Fade (fade_down / fade_up).
	if (const float Alpha = GetFadeAlpha(); Alpha > 0.f)
	{
		FCanvasTileItem Tile(FVector2D::ZeroVector, FVector2D(SizeX, SizeY), FLinearColor(0.f, 0.f, 0.f, Alpha));
		Tile.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(Tile);
	}

	// Spoken lines: over the speaker, in the speaker's colour.
	GTextScale = FMath::Clamp(SizeY / 480.f, 1.5f, 4.f);
	const float LineHeight = (Font->GetMaxCharHeight() + 2.f) * GTextScale;
	for (const FDinkActiveText& T : ActiveTexts)
	{
		FVector2D Anchor;
		if (T.bXY)
		{
			// _xy texts: original 640x480 screen position.
			Anchor = FVector2D(T.X / 640.0 * SizeX + 0.25 * SizeX, T.Y / 480.0 * SizeY);
		}
		else
		{
			AActor* Speaker = Director->GetActor(T.Owner);
			if (!Speaker)
			{
				continue;
			}
			FVector Origin, Extent;
			Speaker->GetActorBounds(/*bOnlyCollidingComponents*/ false, Origin, Extent);
			const FVector Top = Origin + FVector(0, 0, Extent.Z + 40.0);
			const FVector Screen = Canvas->Project(Top, /*bClampToNearPlane*/ false);
			if (Screen.Z <= 0.0)
			{
				continue; // behind the camera
			}
			Anchor = FVector2D(Screen.X, Screen.Y);
		}
		const TArray<FString> Lines = Wrap(T.Text);
		const FLinearColor Color = DinkNarrative::FontColor(T.Color);
		float Y = Anchor.Y - Lines.Num() * LineHeight;
		for (const FString& L : Lines)
		{
			DrawCentered(Canvas, Font, L, FVector2D(Anchor.X, Y), Color);
			Y += LineHeight;
		}
	}

	// Menu.
	if (const FDinkMenu* M = GetActiveMenu())
	{
		const int32 Rows = M->TitleLines.Num() + M->Choices.Num() + 1;
		const float BoxW = SizeX * 0.5f;
		const float BoxH = Rows * LineHeight + 24.f;
		const FVector2D BoxPos((SizeX - BoxW) * 0.5f, (SizeY - BoxH) * 0.5f);
		FCanvasTileItem Box(BoxPos, FVector2D(BoxW, BoxH), FLinearColor(0.05f, 0.04f, 0.02f, 0.85f));
		Box.BlendMode = SE_BLEND_Translucent;
		Canvas->DrawItem(Box);
		float Y = BoxPos.Y + 12.f;
		const FLinearColor TitleColor = M->TitleColor > 0 ? DinkNarrative::FontColor(M->TitleColor) : FLinearColor::White;
		for (const FString& Title : M->TitleLines)
		{
			DrawCentered(Canvas, Font, Title, FVector2D(SizeX * 0.5f, Y), TitleColor);
			Y += LineHeight;
		}
		Y += LineHeight * 0.5f;
		for (int32 i = 0; i < M->Choices.Num(); ++i)
		{
			const bool bSel = i == M->Selected;
			const FString Text = FString::Printf(TEXT("%s%d. %s"), bSel ? TEXT("> ") : TEXT("  "), i + 1, *M->Choices[i].Text);
			DrawCentered(Canvas, Font, Text, FVector2D(SizeX * 0.5f, Y), bSel ? DinkNarrative::FontColor(14) : FLinearColor(0.85f, 0.85f, 0.85f));
			Y += LineHeight;
		}
	}
}
