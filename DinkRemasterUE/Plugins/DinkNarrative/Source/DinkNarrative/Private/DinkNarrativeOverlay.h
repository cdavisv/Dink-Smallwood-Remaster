#pragma once

#include "CoreMinimal.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/DeclarativeSyntaxSupport.h"
#include "Widgets/SLeafWidget.h"

class UDinkStorySubsystem;
class UTexture2D;
struct FSlateBrush;

/**
 * The narrative layer's on-screen presentation, painted by one Slate widget over the game viewport (no widget assets;
 * the plugin has no content). It only reads the story subsystem's state and never changes it.
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
};
