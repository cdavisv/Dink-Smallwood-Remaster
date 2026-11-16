#include "DinkFamilyAnchor.h"
#include "DinkLayout.h"
#include "Greybox/DinkScreenVolume.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
	struct FFrameBox
	{
		FIntRect Box;
		int32 Width = 0;
		int32 OriginX = 0;
	};

	TMap<int64, FFrameBox>& Table()
	{
		static TMap<int64, FFrameBox> T;
		return T;
	}

	bool bLoaded = false;

	int64 Key(int32 Seq, int32 Frame) { return (int64(Seq) << 16) | int64(Frame & 0xffff); }
}

int32 DinkFamilyAnchor::LoadFramesCsv(const FString& Text)
{
	TMap<int64, FFrameBox>& T = Table();
	T.Reset();
	TArray<FString> Lines;
	Text.ParseIntoArrayLines(Lines);
	// seq,frame,delay_ms,special,left,top,right,bottom,loop,empty,width,height,origin_x,origin_y,...
	for (int32 I = 1; I < Lines.Num(); ++I)
	{
		TArray<FString> C;
		Lines[I].ParseIntoArray(C, TEXT(","), false);
		if (C.Num() < 13) continue;
		FFrameBox B;
		B.Box = FIntRect(FCString::Atoi(*C[4]), FCString::Atoi(*C[5]), FCString::Atoi(*C[6]), FCString::Atoi(*C[7]));
		B.Width = FCString::Atoi(*C[10]);
		B.OriginX = FCString::Atoi(*C[12]);
		T.Add(Key(FCString::Atoi(*C[0]), FCString::Atoi(*C[1])), B);
	}
	bLoaded = true;
	return T.Num();
}

bool DinkFamilyAnchor::Parse(const FString& Text, EDinkFamilyAnchor& Out)
{
	if (Text == TEXT("card")) { Out = EDinkFamilyAnchor::Card; return true; }
	if (Text == TEXT("hardbox")) { Out = EDinkFamilyAnchor::Hardbox; return true; }
	if (Text == TEXT("hardbox_inner")) { Out = EDinkFamilyAnchor::HardboxInner; return true; }
	return false;
}

bool DinkFamilyAnchor::FrameHardbox(int32 Sequence, int32 Frame, FIntRect& OutBox, int32& OutWidth, int32& OutOriginX)
{
	if (!bLoaded)
	{
		FString Text;
		if (FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Gameplay/frames.csv")))) LoadFramesCsv(Text);
		bLoaded = true;
	}
	const FFrameBox* B = Table().Find(Key(Sequence, FMath::Max(1, Frame)));
	if (!B || B->Box.Max.X <= B->Box.Min.X || B->Box.Max.Y <= B->Box.Min.Y) return false;
	OutBox = B->Box;
	OutWidth = B->Width;
	OutOriginX = B->OriginX;
	return true;
}

bool DinkFamilyAnchor::TargetPixel(EDinkFamilyAnchor Mode, const FVector2D& Placement, const FIntRect& Box, const FVector2D& Half, FVector2D& Out)
{
	if (Mode == EDinkFamilyAnchor::Card || Box.Max.X <= Box.Min.X || Box.Max.Y <= Box.Min.Y) return false;
	const FVector2D Min = Placement + FVector2D(Box.Min.X, Box.Min.Y), Max = Placement + FVector2D(Box.Max.X, Box.Max.Y);
	Out = (Min + Max) * 0.5;
	if (Mode == EDinkFamilyAnchor::HardboxInner)
	{
		// the thin axis of the hardbox is the wall's thickness; the inner face is the one towards the screen's middle (300, 200)
		const FVector2D Size = Max - Min;
		if (Size.Y >= Size.X)
		{
			if (Half.X * 2.0 < Size.X) Out.X = Out.X < 300.0 ? Max.X - Half.X : Min.X + Half.X;
		}
		else
		{
			if (Half.Y * 2.0 < Size.Y) Out.Y = Out.Y < 200.0 ? Max.Y - Half.Y : Min.Y + Half.Y;
		}
	}
	return true;
}

bool DinkFamilyAnchor::AnchorWorld(const ADinkScreenVolume& Volume, EDinkFamilyAnchor Mode, int32 Sequence, int32 Frame, const FVector& CardWorld,
	double CardWidthCm, double Yaw, const FVector& MeshSizeCm, FVector& OutWorld)
{
	if (Mode == EDinkFamilyAnchor::Card) return false;
	FIntRect Box;
	int32 Width = 0, OriginX = 0;
	if (!FrameHardbox(Sequence, Frame, Box, Width, OriginX) || Width <= 0) return false;
	double CX = 0, CY = 0;
	if (!DinkLayout::MetresToMapPixel(Volume.Corners, DinkLayout::UnrealToMetres(CardWorld), CX, CY)) return false;
	const FVector P0 = Volume.MapPixelToWorld(float(CX), float(CY));
	const double CmX = FVector::Dist2D(P0, Volume.MapPixelToWorld(float(CX + 10.0), float(CY))) / 10.0;
	const double CmY = FVector::Dist2D(P0, Volume.MapPixelToWorld(float(CX), float(CY + 10.0))) / 10.0;
	if (CmX <= KINDA_SMALL_NUMBER || CmY <= KINDA_SMALL_NUMBER) return false;
	// the card's scaled picture pixels (size %): its width over the picture's width at this screen's scale
	const double SizeFactor = CardWidthCm > 0.0 ? CardWidthCm / (Width * CmX) : 1.0;
	const FVector2D Placement(CX - (Width * 0.5 - OriginX) * SizeFactor, CY);
	const double R = FMath::DegreesToRadians(Yaw);
	const double Ex = FMath::Abs(FMath::Cos(R)) * MeshSizeCm.X + FMath::Abs(FMath::Sin(R)) * MeshSizeCm.Y;
	const double Ey = FMath::Abs(FMath::Sin(R)) * MeshSizeCm.X + FMath::Abs(FMath::Cos(R)) * MeshSizeCm.Y;
	FVector2D Px;
	if (!TargetPixel(Mode, Placement, Box, FVector2D(Ex * 0.5 / CmX, Ey * 0.5 / CmY), Px)) return false;
	OutWorld = Volume.MapPixelToWorld(float(Px.X), float(Px.Y));
	return true;
}
