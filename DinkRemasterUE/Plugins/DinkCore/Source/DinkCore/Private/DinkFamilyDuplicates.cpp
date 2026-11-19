#include "DinkFamilyDuplicates.h"
#include "DinkArtFamilySubsystem.h"
#include "DinkCoreModule.h"
#include "DinkInstanceOriginsComponent.h"
#include "DinkLayout.h"
#include "DinkOriginComponent.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"

const FName UDinkFamilyDuplicatesSubsystem::DroppedTag(TEXT("DinkFamilyDuplicate"));

static TAutoConsoleVariable<int32> CVarDinkFamilyDuplicates(TEXT("dink.FamilyDuplicates"), 1,
	TEXT("1 = of the copies of one object that 1997 maps place on neighbouring screens, the family layer dresses one (bug A208); ")
	TEXT("0 = every copy gets its own mesh (master before A208). Read when a screen is dressed."));

double DinkFamilyDuplicates::OutsidePx(const FVector2D& MapPx)
{
	const double Dx = FMath::Max3(0.0 - MapPx.X, 0.0, MapPx.X - DinkLayout::ScreenWidthPx);
	const double Dy = FMath::Max3(0.0 - MapPx.Y, 0.0, MapPx.Y - DinkLayout::ScreenHeightPx);
	return FMath::Sqrt(Dx * Dx + Dy * Dy);
}

FVector2D DinkFamilyDuplicates::GridPx(int32 Screen, const FVector2D& MapPx)
{
	const int32 N = FMath::Max(Screen, 1) - 1;
	return FVector2D((N % 32) * DinkLayout::ScreenWidthPx + MapPx.X, (N / 32) * DinkLayout::ScreenHeightPx + MapPx.Y);
}

bool DinkFamilyDuplicates::SameObject(const FDinkFamilyCopy& A, const FDinkFamilyCopy& B)
{
	if (A.Screen == B.Screen || A.Binding != B.Binding || !A.Binding || A.Sequence != B.Sequence || A.Frame != B.Frame) return false;
	if (FVector2D::Distance(A.GroundCm, B.GroundCm) > MaxWorldCm) return false;
	if (FVector2D::Distance(GridPx(A.Screen, A.MapPx), GridPx(B.Screen, B.MapPx)) > MaxMapPx) return false;
	return A.SizePx > 0.0 && B.SizePx > 0.0 && FMath::Abs(A.SizePx / B.SizePx - 1.0) <= SizeTolerance;
}

bool DinkFamilyDuplicates::Before(const FDinkFamilyCopy& A, const FDinkFamilyCopy& B)
{
	// Map pixels are compared at 1/1000 px so a float difference in the layout maths never decides.
	const int64 OutA = FMath::RoundToInt64(OutsidePx(A.MapPx) * 1000.0), OutB = FMath::RoundToInt64(OutsidePx(B.MapPx) * 1000.0);
	if (OutA != OutB) return OutA < OutB;
	if (A.Screen != B.Screen) return A.Screen < B.Screen;
	return A.Origin < B.Origin;
}

void DinkFamilyDuplicates::Resolve(const TArray<FDinkFamilyCopy>& Copies, TMap<FString, FString>& OutDropped)
{
	OutDropped.Reset();
	TArray<int32> Order;
	Order.Reserve(Copies.Num());
	for (int32 Index = 0; Index < Copies.Num(); ++Index) Order.Add(Index);
	Order.Sort([&Copies](int32 L, int32 R) { return Before(Copies[L], Copies[R]); });
	// Kept copies by 1 m cell of their ground point; a partner is at most MaxWorldCm away, so the 3 x 3 cells around suffice.
	TMap<FIntPoint, TArray<int32>> Kept;
	auto Cell = [](const FVector2D& P) { return FIntPoint(FMath::FloorToInt32(P.X / MaxWorldCm), FMath::FloorToInt32(P.Y / MaxWorldCm)); };
	for (const int32 Index : Order)
	{
		const FDinkFamilyCopy& C = Copies[Index];
		const FIntPoint At = Cell(C.GroundCm);
		const FDinkFamilyCopy* Best = nullptr;
		for (int32 Dx = -1; Dx <= 1; ++Dx) for (int32 Dy = -1; Dy <= 1; ++Dy)
			if (const TArray<int32>* There = Kept.Find(At + FIntPoint(Dx, Dy)))
				for (const int32 K : *There)
					if (SameObject(Copies[K], C) && (!Best || Before(Copies[K], *Best))) Best = &Copies[K];
		if (Best) OutDropped.Add(C.Origin, Best->Origin);
		else Kept.FindOrAdd(At).Add(Index);
	}
}

namespace
{
	/** Metres per 1997 pixel along the screen's east axis at a map point. */
	double CmPerPx(const FDinkScreenCorners& Corners, const FVector2D& MapPx)
	{
		const FVector2D L = DinkLayout::MapPixelToMetres(Corners, MapPx.X - 0.5, MapPx.Y);
		const FVector2D R = DinkLayout::MapPixelToMetres(Corners, MapPx.X + 0.5, MapPx.Y);
		return FVector2D::Distance(L, R) * DinkLayout::CentimetresPerMetre;
	}

	bool MakeCopy(const TMap<int32, const ADinkScreenVolume*>& Volumes, const FString& Origin, int32 Screen, const FDinkFamilyBinding* B,
		int32 Sequence, int32 Frame, const FVector& GroundWorld, double CardWidthCm, FDinkFamilyCopy& Out)
	{
		const ADinkScreenVolume* const* Volume = Volumes.Find(Screen);
		if (!Volume || !*Volume) return false;
		double X = 0.0, Y = 0.0;
		if (!DinkLayout::MetresToMapPixel((*Volume)->Corners, DinkLayout::UnrealToMetres(GroundWorld), X, Y)) return false;
		Out.Origin = Origin;
		Out.Screen = Screen;
		Out.Binding = B;
		Out.Sequence = Sequence;
		Out.Frame = Frame;
		Out.GroundCm = FVector2D(GroundWorld.X, GroundWorld.Y);
		Out.MapPx = FVector2D(X, Y);
		const double Scale = CmPerPx((*Volume)->Corners, Out.MapPx);
		Out.SizePx = Scale > UE_SMALL_NUMBER ? CardWidthCm / Scale : 0.0;
		return true;
	}
}

void DinkFamilyDuplicates::Gather(UWorld& World, const TArray<FDinkFamilyBinding>& Bindings, const FDinkFamilyPrecedence& Precedence,
	TFunctionRef<bool(const ADinkPlaceholderActor&)> IsFitted, TArray<FDinkFamilyCopy>& Out)
{
	TMap<int32, const ADinkScreenVolume*> Volumes;
	for (TActorIterator<ADinkScreenVolume> It(&World); It; ++It) Volumes.Add(It->ScreenNumber, *It);
	// Placement actors: the gates of UDinkArtFamilySubsystem::DressActor that do not change at run time.
	for (TActorIterator<ADinkPlaceholderActor> It(&World); It; ++It)
	{
		const ADinkPlaceholderActor& A = **It;
		const UStaticMeshComponent* Card = A.Card;
		if (!A.Origin || !A.Origin->OriginId.IsValid() || !Card || !Card->GetStaticMesh() || !A.GetRootComponent() || A.ActorHasTag(TEXT("DinkAuthoredArt")) ||
			A.ActorHasTag(TEXT("DinkHumanoid")) || A.ActorHasTag(TEXT("DinkCreature")) || A.Vision != 0 || IsFitted(A)) continue;
		FDinkFamilyPlacement P;
		P.Origin = A.Origin->OriginId.ToString();
		P.Screen = A.ScreenNumber;
		P.Sequence = A.Origin->Sequence;
		P.Frame = A.Origin->Frame;
		P.ClassId = A.Origin->ClassId;
		P.bScripted = !A.Origin->ScriptName.IsNone();
		P.bHardnessOnly = A.PlacementKind == TEXT("hardness_only");
		const FDinkFamilyBinding* B = nullptr;
		// effect rows (#166 placed fires and sparkles: a card per placement, not a mesh) are never merged
		if (DinkArtFamily::Decide(P, Precedence, Bindings, B) != EDinkFamilyDecision::Bound || !B || B->Mesh.IsEmpty() || !B->Effect.IsEmpty()) continue;
		// DressActor stands the mesh on (card x, card y, 0) of the actor (before its anchor_front shift, the same for every copy).
		const FVector CardAt = Card->GetRelativeLocation();
		const FVector Ground = A.GetActorTransform().TransformPosition(FVector(CardAt.X, CardAt.Y, 0.0));
		FDinkFamilyCopy C;
		if (MakeCopy(Volumes, P.Origin, P.Screen, B, P.Sequence, P.Frame, Ground, Card->GetRelativeScale3D().X * 100.0, C)) Out.Add(MoveTemp(C));
	}
	// Background instances: the gates of DressInstances (a decor component is dressed only when all its instances share one row).
	for (TActorIterator<ADinkGreyboxScreen> It(&World); It; ++It)
	{
		const ADinkGreyboxScreen& Screen = **It;
		if (!Screen.InstanceOrigins || Screen.ActorHasTag(TEXT("DinkAuthoredArt")) || !Screen.GetRootComponent()) continue;
		TMap<FName, TArray<const FDinkInstanceOrigin*>> ByComponent;
		for (const FDinkInstanceOrigin& O : Screen.InstanceOrigins->Origins) ByComponent.FindOrAdd(O.ComponentName).Add(&O);
		TInlineComponentArray<UInstancedStaticMeshComponent*> Components(&Screen);
		for (const auto& Pair : ByComponent)
		{
			const UInstancedStaticMeshComponent* Decor = nullptr;
			for (const UInstancedStaticMeshComponent* Each : Components) if (Each->GetFName() == Pair.Key) Decor = Each;
			if (!Decor) continue;
			const FDinkFamilyBinding* Shared = nullptr;
			bool bAll = true;
			for (const FDinkInstanceOrigin* O : Pair.Value)
			{
				FDinkFamilyPlacement P;
				P.Origin = O->OriginId.ToString();
				P.Screen = Screen.ScreenNumber;
				P.Sequence = O->Sequence;
				P.Frame = O->Frame;
				P.ClassId = O->ClassId;
				P.bScripted = !O->ScriptName.IsNone();
				const FDinkFamilyBinding* B = nullptr;
				DinkArtFamily::Decide(P, Precedence, Bindings, B);
				if (!B || (Shared && B != Shared)) bAll = false;
				Shared = B;
			}
			if (!bAll || !Shared || Shared->Mesh.IsEmpty() || !Shared->Effect.IsEmpty()) continue;
			for (const FDinkInstanceOrigin* O : Pair.Value)
			{
				if (!O->OriginId.IsValid()) continue;
				FTransform Card;
				if (!Decor->GetInstanceTransform(O->InstanceIndex, Card, /*bWorldSpace*/ true)) continue;
				FDinkFamilyCopy C;
				if (MakeCopy(Volumes, O->OriginId.ToString(), Screen.ScreenNumber, Shared, O->Sequence, O->Frame, Card.GetLocation(),
					Card.GetScale3D().X * 100.0, C)) Out.Add(MoveTemp(C));
			}
		}
	}
}

bool UDinkFamilyDuplicatesSubsystem::DoesSupportWorldType(EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UDinkFamilyDuplicatesSubsystem::EnsureBuilt(UDinkArtFamilySubsystem& Families)
{
	UWorld* World = GetWorld();
	if (bBuilt || !World) return;
	bBuilt = true;
	const double Start = FPlatformTime::Seconds();
	TArray<FDinkFamilyCopy> All;
	DinkFamilyDuplicates::Gather(*World, Families.GetBindings(), Families.GetPrecedence(),
		[&Families](const ADinkPlaceholderActor& A) { return A.Origin && Families.IsCollisionFitRequested(A.Origin->OriginId); }, All);
	DinkFamilyDuplicates::Resolve(All, Dropped);
	Copies = All.Num();
	// Groups: the kept copy first, then its dropped copies (sorted, so the order never depends on the actor iteration).
	TArray<FString> DroppedOrigins;
	Dropped.GenerateKeyArray(DroppedOrigins);
	DroppedOrigins.Sort();
	for (const FString& Origin : DroppedOrigins)
	{
		const FString& Kept = Dropped[Origin];
		int32 Index = GroupOf.FindRef(Kept, INDEX_NONE);
		if (Index == INDEX_NONE)
		{
			Index = Groups.Num();
			FGroup& Group = Groups.AddDefaulted_GetRef();
			Group.Members.Add(Kept);
			Group.Drawer = Kept;
			GroupOf.Add(Kept, Index);
		}
		Groups[Index].Members.Add(Origin);
		GroupOf.Add(Origin, Index);
	}
	for (TActorIterator<ADinkPlaceholderActor> It(World); It; ++It)
	{
		if (!It->Origin) continue;
		const FString Origin = It->Origin->OriginId.ToString();
		if (GroupOf.Contains(Origin)) MemberActors.Add(Origin, *It);
	}
	for (FGroup& Group : Groups)
		for (const FString& Member : Group.Members) Group.bHasInstance |= !MemberActors.Contains(Member);
	// Dropped placement actors lose their card now, whichever screen is dressed first: until the kept copy's screen is
	// dressed the kept card shows the object, after that its mesh. (A dropped background instance belongs to a decor
	// component that is hidden as a whole only when its own screen is dressed; until then that card shows too.)
	// Refresh applies the drawer rule (DinkFamilyDuplicates.h): pictures registered before this build count already.
	for (FGroup& Group : Groups) Refresh(Families, Group);
	BuildMs = (FPlatformTime::Seconds() - Start) * 1000.0;
	UE_LOG(LogDink, Display, TEXT("DINK FAMILY DUPLICATES: %d family copies, %d dropped as the same object as a kept copy on a neighbour screen (%d groups, %d placement-actor copies hidden now; %.1f ms, once)"),
		Copies, Dropped.Num(), Groups.Num(), Hidden.Num(), BuildMs);
}

FString UDinkFamilyDuplicatesSubsystem::GetDrawer(const FString& Origin) const
{
	const int32* Index = GroupOf.Find(Origin);
	return Index ? Groups[*Index].Drawer : Origin;
}

FString UDinkFamilyDuplicatesSubsystem::PickDrawer(UDinkArtFamilySubsystem& Families, const FGroup& Group) const
{
	const FString& Kept = Group.Members[0];
	ADinkPlaceholderActor* KeptActor = MemberActors.FindRef(Kept).Get();
	if (Group.bHasInstance || !KeptActor) return Kept;
	// One object while every copy shows the kept copy's picture (the saved editor_seq/editor_frame of dink.cpp:5829-5830
	// or an animation picture with its own row count; a picture no layer registered is the imported one).
	int32 KeptSequence = 0, KeptFrame = 0;
	Families.ShownPicture(*KeptActor, KeptSequence, KeptFrame);
	bool bReleased = false;
	for (int32 Index = 1; Index < Group.Members.Num() && !bReleased; ++Index)
	{
		if (ADinkPlaceholderActor* Copy = MemberActors.FindRef(Group.Members[Index]).Get())
		{
			int32 Sequence = 0, Frame = 0;
			Families.ShownPicture(*Copy, Sequence, Frame);
			bReleased = Sequence != KeptSequence || Frame != KeptFrame;
		}
	}
	// The kept copy's mesh draws everywhere; a card renders only on the current screen (dink.LegacyCardsCurrentScreen).
	if (!bReleased && Families.WouldDressMesh(*KeptActor)) return Kept;
	// 1997 shows the copy of the screen Dink is on, with its own picture.
	const int32 Here = Families.GetCurrentScreen();
	for (const FString& Member : Group.Members)
	{
		const ADinkPlaceholderActor* Copy = MemberActors.FindRef(Member).Get();
		if (Copy && Here > 0 && Copy->ScreenNumber == Here) return Member;
	}
	return Kept;
}

void UDinkFamilyDuplicatesSubsystem::Refresh(UDinkArtFamilySubsystem& Families, FGroup& Group)
{
	const FString Drawer = PickDrawer(Families, Group);
	if (Drawer != Group.Drawer)
	{
		UE_LOG(LogDink, Log, TEXT("Family duplicates: %s draws the object of %s now (%s)"), *Drawer, *FString::Join(Group.Members, TEXT(" ")),
			Drawer == Group.Members[0] ? TEXT("the kept copy") : TEXT("the copy of the current screen, its own picture"));
	}
	// The drawer is set first: DressActor (from Unsuppress) asks DropActor, which reads it.
	Group.Drawer = Drawer;
	for (const FString& Member : Group.Members)
	{
		if (Member == Drawer) continue;
		if (ADinkPlaceholderActor* Copy = MemberActors.FindRef(Member).Get()) Suppress(*Copy, Member);
	}
	if (ADinkPlaceholderActor* Copy = MemberActors.FindRef(Drawer).Get()) Unsuppress(Families, *Copy, Drawer, /*bDress*/ true);
}

void UDinkFamilyDuplicatesSubsystem::Suppress(ADinkPlaceholderActor& Actor, const FString& Origin)
{
	// Idempotent: whatever of the copy draws now (its card, its family parts) is hidden in game and remembered. Hidden, never
	// destroyed: the copy that draws again later shows exactly what it showed (its variant, its player blocker, which follows it).
	FHidden& Record = Hidden.FindOrAdd(Origin);
	Actor.Tags.AddUnique(DroppedTag);
	if (!Actor.ActorHasTag(UDinkArtFamilySubsystem::FamilyTag))
	{
		Actor.Tags.Add(UDinkArtFamilySubsystem::FamilyTag);  // DressActor leaves it alone
		Record.bTagged = true;
	}
	auto Hide = [&Record](USceneComponent* Component)
	{
		if (!Component || Component->bHiddenInGame) return;
		Component->SetHiddenInGame(true);
		Record.Components.AddUnique(Component);
	};
	Hide(Actor.Card);
	TInlineComponentArray<USceneComponent*> Parts(&Actor);
	for (USceneComponent* Part : Parts)
		if (Part != Actor.Card && Part->ComponentHasTag(UDinkArtFamilySubsystem::FamilyTag)) Hide(Part);
}

void UDinkFamilyDuplicatesSubsystem::Unsuppress(UDinkArtFamilySubsystem& Families, ADinkPlaceholderActor& Actor, const FString& Origin, bool bDress)
{
	Actor.Tags.Remove(DroppedTag);
	FHidden Record;
	if (!Hidden.RemoveAndCopyValue(Origin, Record)) return;
	for (const TWeakObjectPtr<USceneComponent>& Component : Record.Components)
		if (USceneComponent* Shown = Component.Get()) Shown->SetHiddenInGame(false);
	if (Record.bTagged) Actor.Tags.Remove(UDinkArtFamilySubsystem::FamilyTag);
	// A copy hidden before it was dressed (the dropped copy at the build) gets its family mesh now, from its own picture.
	if (bDress && !Actor.ActorHasTag(UDinkArtFamilySubsystem::FamilyTag) && Families.IsScreenApplied(Actor.ScreenNumber)) Families.DressActor(Actor);
}

UDinkFamilyDuplicatesSubsystem* UDinkFamilyDuplicatesSubsystem::For(UDinkArtFamilySubsystem& Families)
{
	if (!CVarDinkFamilyDuplicates.GetValueOnGameThread()) return nullptr;
	UWorld* World = Families.GetWorld();
	UDinkFamilyDuplicatesSubsystem* Self = World ? World->GetSubsystem<UDinkFamilyDuplicatesSubsystem>() : nullptr;
	if (Self) Self->EnsureBuilt(Families);
	return Self;
}

void UDinkFamilyDuplicatesSubsystem::Build(UDinkArtFamilySubsystem& Families)
{
	For(Families);
}

bool UDinkFamilyDuplicatesSubsystem::DropActor(UDinkArtFamilySubsystem& Families, ADinkPlaceholderActor& Actor, const FString& Origin)
{
	UDinkFamilyDuplicatesSubsystem* Self = For(Families);
	const int32* Index = Self ? Self->GroupOf.Find(Origin) : nullptr;
	if (!Index || Self->Groups[*Index].Drawer == Origin) return false;
	// Another copy draws this object now (the kept copy: its card until its own screen is dressed, then its mesh); this stays hidden.
	Self->Suppress(Actor, Origin);
	return true;
}

bool UDinkFamilyDuplicatesSubsystem::IsDroppedInstance(UDinkArtFamilySubsystem& Families, const FString& Origin)
{
	UDinkFamilyDuplicatesSubsystem* Self = For(Families);
	return Self && Self->Dropped.Contains(Origin);
}

void UDinkFamilyDuplicatesSubsystem::Restore(UDinkArtFamilySubsystem& Families, ADinkPlaceholderActor& Actor)
{
	UDinkFamilyDuplicatesSubsystem* Self = For(Families);
	if (!Self || !Actor.Origin) return;
	const FString Origin = Actor.Origin->OriginId.ToString();
	if (Self->GroupOf.Contains(Origin)) Self->Unsuppress(Families, Actor, Origin, /*bDress*/ false);
}

void UDinkFamilyDuplicatesSubsystem::PictureChanged(UDinkArtFamilySubsystem& Families, ADinkPlaceholderActor& Actor)
{
	UDinkFamilyDuplicatesSubsystem* Self = For(Families);
	if (!Self || !Actor.Origin) return;
	if (const int32* Index = Self->GroupOf.Find(Actor.Origin->OriginId.ToString())) Self->Refresh(Families, Self->Groups[*Index]);
}

void UDinkFamilyDuplicatesSubsystem::ScreenChanged(UDinkArtFamilySubsystem& Families)
{
	// About 170 groups of two to four copies (the build log): no world iteration.
	if (UDinkFamilyDuplicatesSubsystem* Self = For(Families))
		for (FGroup& Group : Self->Groups) Self->Refresh(Families, Group);
}
