#pragma once

#include "CoreMinimal.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SLeafWidget.h"

class UDinkStorySubsystem;
class UTexture2D;
struct FSlateBrush;

/**
 * The narrative layer's on-screen presentation, painted by one Slate widget over the game viewport (no widget assets;
 * the plugin has no content). It only reads the story subsystem's state and never changes it: what is on screen and for
 * how long stays the story's (the 1997 engine's timing); the widget only decides how it looks.
 *
 *  - Dialogue box: a rounded translucent panel at the bottom with the speaker's name plate (speakers.csv; none when
 *    unknown), text wrapped by measured width, a soft fade/slide in, and a "continue" hint for blocking lines (say_stop).
 *    It shows the newest blocking line; with none, the newest spoken line. When a line times out while its voice recording
 *    is still finishing (UDinkAudioSubsystem::IsVoiceTailPlaying), the box keeps it up until the recording ends or another
 *    line takes the box, so text and voice leave together (presentation only: the text is already gone from the story).
 *  - Bubbles: other characters' non-blocking lines while the box is busy, as compact bubbles over their heads.
 *  - Captions: _xy texts (narration, titles, "Game saved") as centred cards at the original's height.
 *  - Choice menu: the same panel style, highlighted row, number badges and key hints.
 *  - Fade (fade_down / fade_up) and the inventory screen.
 *
 * Slate units: the viewport's DPI scaler maps them to pixels (the project's DPI curve: 1080p = 1.0), so the layout is
 * written for a 1920x1080 reference and scales with the resolution; every placement is relative to the actual local size,
 * so other aspect ratios lay out too.
 */
class SDinkNarrativeOverlay : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SDinkNarrativeOverlay) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs, UDinkStorySubsystem* InStory);

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect, FSlateWindowElementList& OutDrawElements,
		int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;
	virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D::ZeroVector; }

	/** Icon hook for the inventory: the texture named in items.csv, loaded once; null draws the monogram. */
	const FSlateBrush* FindItemIcon(FName Script) const;

private:
	TWeakObjectPtr<UDinkStorySubsystem> Story;

	struct FIcon
	{
		TStrongObjectPtr<UTexture2D> Texture;
		TSharedPtr<FSlateBrush> Brush;
	};
	mutable TMap<FName, FIcon> Icons;

public:
	/** What the dialogue box shows (kept for its fade-out after the text is gone). */
	struct FBoxContent
	{
		int32 Handle = 0;
		/** Ink line id, to find the line's voice recording (UDinkAudioSubsystem::IsVoiceTailPlaying). */
		FString LineId;
		FString Name;
		FString Text;
		bool bBlocking = false;
		/** Real time the text first appeared. */
		double TextSince = 0.0;
	};

private:
	/** Text handle -> (text, real time first seen): appear animations (handles are reused, so the text is part of the key). */
	mutable TMap<int32, TPair<FString, double>> SeenTexts;
	mutable FBoxContent Box;
	/** Real time the box panel appeared (after being hidden) and disappeared (-1 while shown). */
	mutable double BoxSince = 0.0;
	mutable double BoxGoneAt = -1.0;
	mutable int32 SeenMenu = 0;
	mutable double MenuSince = 0.0;

	double SeenAt(int32 Handle, const FString& Text, double Now) const;
	/** The box's line has timed out and its voice recording is still audible. */
	static bool IsVoiceStillSpeaking(const UDinkStorySubsystem& S, const FBoxContent& C);
	/** Fade, dialogue box, bubbles, captions and the menu (Painter: DinkOverlay::FPainter, private to the .cpp). */
	using FPainterRef = void*;
	void PaintNarrative(FPainterRef Painter, const UDinkStorySubsystem& S, double Now) const;
};
