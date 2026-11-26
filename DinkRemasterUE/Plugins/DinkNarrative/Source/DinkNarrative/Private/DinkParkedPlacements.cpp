// Bug A13 (SP-08, 25 Nov 2026): placements that 1997 parks outside the 600 x 400 playfield are not drawn and collide with nothing
// (UDinkGameplay::UpdateParkedPlacements, DinkGameplay.h). Presentation and 3D collision only.
#include "DinkGameplay.h"
#include "DinkDirector.h"
#include "DinkStorySubsystem.h"
#include "DinkNarrativeTypes.h"
#include "DinkOriginComponent.h"
#include "DinkPlayerBlockers.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Components/PrimitiveComponent.h"
#include "Components/ShapeComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"

namespace
{
	TAutoConsoleVariable<int32> CVarDinkParkedPlacements(TEXT("dink.ParkedPlacements"), 1,
		TEXT("1: a placement whose whole 1997 picture lies outside its screen's 600 x 400 playfield (1997 parks it there) is not drawn and ")
		TEXT("collides with nothing until a script moves it in (bug A13). 0: drawn on the neighbouring screen as before. Presentation only."));
}

bool UDinkGameplay::PictureOutsideField(double X, double Y, int32 Width, int32 Height, int32 OriginX, int32 OriginY, int32 SizePercent)
{
	const double MapX = X - 20.0;
	if (Width <= 0 || Height <= 0)
	{
		return MapX < 0.0 || MapX >= 600.0 || Y < 0.0 || Y >= 400.0;
	}
	const double S = double(SizePercent > 0 ? SizePercent : 100) / 100.0;
	const double L = MapX - OriginX * S, T = Y - OriginY * S;
	const double R = L + Width * S, B = T + Height * S;
	return R <= 0.0 || L >= 600.0 || B <= 0.0 || T >= 400.0;
}

bool UDinkGameplay::IsParked(const AActor* Actor)
{
	return Actor && Actor->ActorHasTag(DinkPlayerBlockers::ParkedTag);
}

void UDinkGameplay::UpdateParkedPlacements()
{
	UWorld* World = Story ? Story->GetWorld() : nullptr;
	if (!World)
	{
		return;
	}
	if (ParkCandidatesWorld.Get() != World)
	{
		// once per world: the placement actors whose imported picture (map.dat's seq/frame/size at its x/y) lies outside the field
		ParkCandidates.Reset();
		ParkedDraw.Reset();
		ParkedCollision.Reset();
		ParkCandidatesWorld = World;
		for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
		{
			const FDinkPlacementInfo* P = It->Origin ? Data.FindPlacement(It->Origin->OriginId) : nullptr;
			if (!P)
			{
				continue;
			}
			const FDinkFrameInfo* F = Data.FindFrame(P->Seq, FMath::Max(1, P->Frame));
			if (PictureOutsideField(P->X, P->Y, F ? F->Width : 0, F ? F->Height : 0, F ? F->OriginX : 0, F ? F->OriginY : 0, P->Size))
			{
				ParkCandidates.Add(*It);
			}
		}
		UE_LOG(LogDinkNarrative, Log, TEXT("parked placements (A13): %d placement actors whose 1997 picture lies outside the playfield"), ParkCandidates.Num());
	}
	if (ParkCandidates.IsEmpty())
	{
		return;
	}
	const bool bOn = CVarDinkParkedPlacements.GetValueOnGameThread() != 0;
	// the live sprites of the current screen: a script may have moved one (sp_x/sp_y, move) or changed its picture
	TMap<const AActor*, const FDinkSprite*> Live;
	if (const UDinkDirector* D = Director())
	{
		for (const TPair<int32, FDinkSprite>& Pair : D->GetSprites())
		{
			if (const AActor* A = Pair.Value.Actor.Get())
			{
				Live.Add(A, &Pair.Value);
			}
		}
	}
	for (const TWeakObjectPtr<AActor>& Weak : ParkCandidates)
	{
		AActor* A = Weak.Get();
		if (!A)
		{
			continue;
		}
		bool bPark = bOn;
		if (const FDinkSprite* const* Found = bPark ? Live.Find(A) : nullptr)
		{
			const FDinkSprite& S = **Found;
			// getpic(): an animating sprite shows seq/frame, a still one pseq/pframe (as GetHardbox)
			const FDinkFrameInfo* F = S.GetProp(TEXT("seq")) > 0 ? Data.FindFrame(S.GetProp(TEXT("seq")), FMath::Max(1, S.GetProp(TEXT("frame"), 1))) : nullptr;
			if (!F)
			{
				F = Data.FindFrame(S.GetProp(TEXT("pseq")), FMath::Max(1, S.GetProp(TEXT("pframe"), 1)));
			}
			bPark = PictureOutsideField(S.X, S.Y, F ? F->Width : 0, F ? F->Height : 0, F ? F->OriginX : 0, F ? F->OriginY : 0, S.GetProp(TEXT("size"), 100));
		}
		TInlineComponentArray<UPrimitiveComponent*> Components(A);
		if (bPark)
		{
			A->Tags.AddUnique(DinkPlayerBlockers::ParkedTag);
			// every drawn part (card, family mesh, character body; ones made later by the art layers on the next tick) leaves the
			// render passes; its own body shapes stop colliding; its player-only blockers follow the tag (IsDrawnShown)
			for (UPrimitiveComponent* C : Components)
			{
				if (C->ComponentHasTag(DinkPlayerBlockers::Tag))
				{
					continue;
				}
				if (Cast<UShapeComponent>(C))
				{
					if (!ParkedCollision.Contains(C))
					{
						ParkedCollision.Add(C, uint8(C->GetCollisionEnabled()));
						C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
					}
					continue;
				}
				if (!ParkedDraw.Contains(C))
				{
					FParkedDraw Was;
					Was.bMainPass = C->bRenderInMainPass;
					Was.bDepthPass = C->bRenderInDepthPass;
					Was.bShadow = C->CastShadow;
					Was.bIndirect = C->bAffectDynamicIndirectLighting;
					Was.bRayTracing = C->bVisibleInRayTracing;
					ParkedDraw.Add(C, Was);
					C->SetRenderInMainPass(false);
					C->SetRenderInDepthPass(false);
					C->SetCastShadow(false);
					C->SetAffectDynamicIndirectLighting(false);
					C->SetVisibleInRayTracing(false);
				}
			}
		}
		else if (A->ActorHasTag(DinkPlayerBlockers::ParkedTag))
		{
			A->Tags.Remove(DinkPlayerBlockers::ParkedTag);
			for (UPrimitiveComponent* C : Components)
			{
				FParkedDraw Was;
				if (ParkedDraw.RemoveAndCopyValue(C, Was))
				{
					C->SetRenderInMainPass(Was.bMainPass);
					C->SetRenderInDepthPass(Was.bDepthPass);
					C->SetCastShadow(Was.bShadow);
					C->SetAffectDynamicIndirectLighting(Was.bIndirect);
					C->SetVisibleInRayTracing(Was.bRayTracing);
				}
				uint8 Collision = 0;
				if (ParkedCollision.RemoveAndCopyValue(C, Collision))
				{
					C->SetCollisionEnabled(ECollisionEnabled::Type(Collision));
				}
			}
		}
	}
}
