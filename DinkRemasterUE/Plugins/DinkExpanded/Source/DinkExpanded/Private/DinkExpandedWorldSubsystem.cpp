#include "DinkExpandedWorldSubsystem.h"

#include "DinkCollision.h"
#include "DinkFactSubsystem.h"
#include "DinkOriginComponent.h"
#include "DinkSaveGame.h"
#include "DinkSaveSubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Greybox/DinkWarpComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/CollisionProfile.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "TimerManager.h"

namespace
{
	constexpr double EdgeWallHalfThicknessCm = 10.0;
	constexpr double EdgeWallHalfHeightCm = 150.0;
	constexpr double GroundThicknessCm = 20.0;
	const FName NAME_Expanded(TEXT("expanded"));

	UStaticMesh* BasicShape(const TCHAR* Name)
	{
		return LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("/Engine/BasicShapes/%s.%s"), Name, Name));
	}

	void Tint(UStaticMeshComponent* Mesh, const FLinearColor& Colour)
	{
		if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")))
		{
			UMaterialInstanceDynamic* MID = UMaterialInstanceDynamic::Create(Base, Mesh);
			MID->SetVectorParameterValue(TEXT("Color"), Colour);
			Mesh->SetMaterial(0, MID);
		}
	}

	/** The music file the 1997 engine would play for a raw music value (N or N-1000 plays N.mid; see tools/dinkex). */
	FString MusicFileFor(int32 Raw)
	{
		const int32 N = Raw > 1000 ? Raw - 1000 : Raw;
		return N > 0 ? FString::Printf(TEXT("sound/%d.ogg"), N) : FString();
	}

	/** World transform of a map-pixel rectangle on a screen: centre, yaw of the screen's east axis, half size in cm. */
	void RectToWorld(const FDinkScreenCorners& C, const FDinkPackRect& R, FVector& OutCentre, double& OutYaw, FVector2D& OutHalfCm)
	{
		const FVector2D Mid = R.Centre();
		OutCentre = DinkLayout::MapPixelToUnreal(C, Mid.X, Mid.Y);
		OutYaw = DinkLayout::LocalEastYawDegrees(C, Mid.X, Mid.Y);
		const FVector2D A = DinkLayout::MapPixelToMetres(C, R.X0, Mid.Y);
		const FVector2D B = DinkLayout::MapPixelToMetres(C, R.X1, Mid.Y);
		const FVector2D U = DinkLayout::MapPixelToMetres(C, Mid.X, R.Y0);
		const FVector2D D = DinkLayout::MapPixelToMetres(C, Mid.X, R.Y1);
		OutHalfCm = FVector2D(FVector2D::Distance(A, B), FVector2D::Distance(U, D)) * 50.0;
	}

	AStaticMeshActor* SpawnBlock(UWorld& World, const FVector& Centre, double Yaw, const FVector& SizeCm, const TCHAR* Shape, FName Profile, const FLinearColor& Colour)
	{
		FActorSpawnParameters P;
		P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		P.bDeferConstruction = true;
		const FTransform T(FRotator(0.0, Yaw, 0.0), Centre, SizeCm / 100.0);
		AStaticMeshActor* A = World.SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), T, P);
		if (!A)
		{
			return nullptr;
		}
		UStaticMeshComponent* Mesh = A->GetStaticMeshComponent();
		Mesh->SetMobility(EComponentMobility::Movable);
		Mesh->SetStaticMesh(BasicShape(Shape));
		Mesh->SetCollisionProfileName(Profile);
		A->FinishSpawning(T);
		Tint(Mesh, Colour);
		A->Tags.Add(TEXT("DinkExpanded"));
		return A;
	}
}

ADinkExpandedJoinActor::ADinkExpandedJoinActor()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.1f;
	Warp = CreateDefaultSubobject<UDinkWarpComponent>(TEXT("Warp"));
	RootComponent = Warp;
	Tags.Add(TEXT("DinkExpanded"));
}

void ADinkExpandedJoinActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const UDinkGreyboxSubsystem* Greybox = GetWorld() ? GetWorld()->GetSubsystem<UDinkGreyboxSubsystem>() : nullptr;
	const bool bLocked = Greybox && Warp->SourceScreen != 0 && Greybox->GetLockedScreen() == Warp->SourceScreen;
	Warp->bTriggerEnabled = bConditionMet && !bLocked;
}

bool UDinkExpandedWorldSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	return DinkExpanded::IsEnabled() && Super::ShouldCreateSubsystem(Outer);
}

bool UDinkExpandedWorldSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UDinkExpandedWorldSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	BuildPacks(InWorld);
}

int32 UDinkExpandedWorldSubsystem::BuildPacks(UWorld& World)
{
	const FDinkExpandedRegistry& Registry = DinkExpanded::GetRegistry();
	if (bBuilt || Registry.Packs.Num() == 0)
	{
		return 0;
	}
	// The loaded world's 1997 screens, as they are (whatever scale the layout gave them).
	TArray<DinkExpanded::FBaseScreen> Base;
	for (TActorIterator<ADinkScreenVolume> It(&World); It; ++It)
	{
		if (!Registry.IsPackScreen(It->ScreenNumber))
		{
			Base.Add({It->ScreenNumber, It->Kind, It->Corners});
			BaseCorners.Add(It->ScreenNumber, It->Corners);
		}
	}
	if (Base.Num() == 0)
	{
		UE_LOG(LogDinkExpanded, Warning, TEXT("no 1997 screen volumes in %s: content packs not built into this world"), *World.GetName());
		return 0;
	}
	bBuilt = true;
	PackCorners = DinkExpanded::LayoutPackScreens(Base, Registry);

	const FLinearColor Ground(0.10f, 0.16f, 0.08f);
	const FLinearColor Solid(0.20f, 0.13f, 0.07f);
	for (const FDinkPack& Pack : Registry.Packs)
	{
		for (const FDinkPackScreen& S : Pack.Screens)
		{
			const FDinkScreenCorners* C = PackCorners.Find(S.Screen);
			if (!C)
			{
				continue;
			}
			const FVector Centre = DinkLayout::MapPixelToUnreal(*C, 300.0, 200.0);
			const FVector2D SizeCm(FVector2D::Distance(C->NW, C->NE) * 100.0, FVector2D::Distance(C->NW, C->SW) * 100.0);
			FActorSpawnParameters P;
			P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			P.bDeferConstruction = true;
			const FTransform T(Centre);
			ADinkScreenVolume* V = World.SpawnActor<ADinkScreenVolume>(ADinkScreenVolume::StaticClass(), T, P);
			if (!V)
			{
				continue;
			}
			V->ScreenNumber = S.Screen;
			V->ScreenId = FName(*FString::Printf(TEXT("SCR_%03d"), S.Screen));
			V->Region = S.Region;
			V->RegionName = Pack.Name;
			V->AreaName = S.Name;
			V->Kind = S.Kind;
			V->Sheet = FName(*FString::Printf(TEXT("pack:%s:%s"), *Pack.Id.ToString(), *S.Sheet.ToString()));
			V->bIndoor = S.bIndoor;
			V->MusicRaw = S.MusicRaw;
			V->MusicFile = MusicFileFor(S.MusicRaw);
			V->MusicAction = V->MusicFile.IsEmpty() ? FName(TEXT("none")) : FName(TEXT("play"));
			V->BaseScript = S.BaseScript;
			V->Corners = *C;
			V->Tags.Add(TEXT("DinkExpanded"));
			V->FinishSpawning(T);
			V->Bounds->SetBoxExtent(FVector(SizeCm.X * 0.5, SizeCm.Y * 0.5, 1000.0));
			// Edge walls where the sheet has no neighbour (the pack's own edges; never towards the 1997 world, which is far away).
			const FIntPoint Step[4] = {FIntPoint(0, -1), FIntPoint(1, 0), FIntPoint(0, 1), FIntPoint(-1, 0)};
			const FVector2D Ends[4][2] = {{C->NW, C->NE}, {C->NE, C->SE}, {C->SE, C->SW}, {C->SW, C->NW}};
			for (int32 E = 0; E < 4; ++E)
			{
				const FIntPoint N = S.Grid + Step[E];
				const bool bNeighbour = Pack.Screens.ContainsByPredicate([&](const FDinkPackScreen& O) { return O.Sheet == S.Sheet && O.Grid == N; });
				UBoxComponent* Wall = V->EdgeWalls.IsValidIndex(E) ? V->EdgeWalls[E].Get() : nullptr;
				if (bNeighbour || !Wall)
				{
					continue;
				}
				const FVector2D Mid = (Ends[E][0] + Ends[E][1]) * 0.5;
				const FVector2D Dir = Ends[E][1] - Ends[E][0];
				FVector2D Out(Dir.Y, -Dir.X);
				Out.Normalize();
				if (FVector2D::DotProduct(Out, Mid - DinkLayout::MapPixelToMetres(*C, 300, 200)) < 0)
				{
					Out = -Out;
				}
				Wall->SetWorldLocationAndRotation(DinkLayout::MetresToUnreal(Mid) + FVector(Out.X, Out.Y, 0) * EdgeWallHalfThicknessCm + FVector(0, 0, EdgeWallHalfHeightCm),
					FRotator(0.0, FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X)), 0.0));
				Wall->SetBoxExtent(FVector(Dir.Size() * 50.0 + EdgeWallHalfThicknessCm, EdgeWallHalfThicknessCm, EdgeWallHalfHeightCm));
				Wall->SetCollisionProfileName(DinkCollision::ProfileHardSolid);
			}
			Spawned.Add(V);
			// Greybox ground (top at z = 0, as the 1997 screens' ground) and the hardness rectangles as 3 m blocks.
			if (AStaticMeshActor* G = SpawnBlock(World, Centre - FVector(0, 0, GroundThicknessCm * 0.5), 0.0, FVector(SizeCm.X, SizeCm.Y, GroundThicknessCm),
				TEXT("Cube"), UCollisionProfile::BlockAll_ProfileName, Ground))
			{
				Spawned.Add(G);
			}
			for (const FDinkPackRect& R : S.Solids)
			{
				FVector RC;
				double Yaw;
				FVector2D Half;
				RectToWorld(*C, R, RC, Yaw, Half);
				if (AStaticMeshActor* B = SpawnBlock(World, RC + FVector(0, 0, UDinkGreyboxSubsystem::SolidPrismHeightCm * 0.5), Yaw,
					FVector(Half.X * 2.0, Half.Y * 2.0, UDinkGreyboxSubsystem::SolidPrismHeightCm), TEXT("Cube"), DinkCollision::ProfileHardSolid, Solid))
				{
					Spawned.Add(B);
				}
			}
		}
		// Placements: greybox stand-ins carrying their origin and script, so the director treats them as placements of that screen.
		for (const FDinkPackPlacement& Pl : Pack.Placements)
		{
			const FDinkScreenCorners* C = PackCorners.Find(Pl.Screen);
			if (!C)
			{
				continue;
			}
			const FVector At = DinkLayout::MapPixelToUnreal(*C, Pl.X, Pl.Y);
			FActorSpawnParameters P;
			P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			P.bDeferConstruction = true;
			const FTransform T(At);
			ADinkPlaceholderActor* A = World.SpawnActor<ADinkPlaceholderActor>(ADinkPlaceholderActor::StaticClass(), T, P);
			if (!A)
			{
				continue;
			}
			A->GetRootComponent()->SetMobility(EComponentMobility::Movable);
			A->Card->SetMobility(EComponentMobility::Movable);
			A->Origin->OriginId = FDinkOriginId(Pl.Screen, Pl.Index);
			A->Origin->ScriptName = Pl.Script;
			A->Origin->Sequence = Pl.Seq;
			A->Origin->Frame = Pl.Frame;
			A->Origin->PlacementType = 1;
			A->Origin->Category = Pl.Kind;
			A->DisplayName = Pl.Name;
			A->PlacementKind = Pl.Kind;
			A->Treatment = TEXT("pack_greybox");
			A->Brain = Pl.Brain;
			A->ScreenNumber = Pl.Screen;
			A->bHasHardness = Pl.bHard;
			const bool bPerson = Pl.Kind == TEXT("npc");
			const bool bCreature = Pl.Kind == TEXT("creature");
			const bool bItem = Pl.Kind == TEXT("item");
			A->Card->SetStaticMesh(BasicShape(bPerson ? TEXT("Cylinder") : bCreature ? TEXT("Sphere") : TEXT("Cube")));
			const FVector Size = bPerson ? FVector(60, 60, 180) : bCreature ? FVector(110, 110, 90) : bItem ? FVector(35, 35, 35) : FVector(100, 100, 100);
			A->Card->SetRelativeScale3D(Size / 100.0);
			A->Card->SetRelativeLocation(FVector(0, 0, Size.Z * 0.5));
			A->Tags.Add(TEXT("DinkExpanded"));
			A->FinishSpawning(T);
			Tint(A->Card, bPerson ? FLinearColor(0.75f, 0.55f, 0.35f) : bCreature ? FLinearColor(0.45f, 0.05f, 0.05f) : FLinearColor(0.85f, 0.75f, 0.2f));
			Spawned.Add(A);
		}
		// Designed joins: the 1997 side is an overlay trigger and nothing else.
		for (const FDinkPackJoin& J : Pack.Joins)
		{
			const FDinkScreenCorners* From = BaseCorners.Find(J.FromScreen);
			const FDinkScreenCorners* Back = PackCorners.Find(J.BackScreen);
			FVector ToWorld, ReturnWorld;
			if (!From || !Back || !MapPixelToWorld(J.ToScreen, J.ToPoint, ToWorld) || !MapPixelToWorld(J.ReturnScreen, J.ReturnPoint, ReturnWorld))
			{
				UE_LOG(LogDinkExpanded, Warning, TEXT("join %s: a screen is not in this world; join not built"), *J.Id);
				continue;
			}
			auto Make = [&](const FDinkScreenCorners& C, const FDinkPackRect& R, FName Side, int32 SourceScreen, int32 DestScreen, const FVector2D& DestPixel, const FVector& Dest)
			{
				FVector Centre;
				double Yaw;
				FVector2D Half;
				RectToWorld(C, R, Centre, Yaw, Half);
				FActorSpawnParameters P;
				P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
				P.bDeferConstruction = true;
				const FTransform T(FRotator(0.0, Yaw, 0.0), Centre + FVector(0, 0, 100.0));
				ADinkExpandedJoinActor* A = World.SpawnActor<ADinkExpandedJoinActor>(ADinkExpandedJoinActor::StaticClass(), T, P);
				if (!A)
				{
					return;
				}
				A->JoinId = J.Id;
				A->Side = Side;
				A->Warp->WarpId = FString::Printf(TEXT("XJ_%s_%s"), *J.Id, *Side.ToString());
				A->Warp->Source = TEXT("pack");
				A->Warp->Kind = TEXT("pack_join");
				A->Warp->TriggerMode = TEXT("walk_in");
				A->Warp->SourceScreen = SourceScreen;
				A->Warp->DestScreen = DestScreen;
				A->Warp->DestMapPixel = DestPixel;
				A->Warp->DestLocation = Dest;
				A->Warp->SetBoxExtent(FVector(Half.X, Half.Y, 100.0));
				if (Side == TEXT("in"))
				{
					A->RequiresFact = J.RequiresFact;
					A->RequiresAtLeast = J.RequiresAtLeast;
				}
				A->FinishSpawning(T);
				Joins.Add(A);
				Spawned.Add(A);
			};
			Make(*From, J.FromRect, TEXT("in"), J.FromScreen, J.ToScreen, J.ToPoint, ToWorld);
			Make(*Back, J.BackRect, TEXT("out"), J.BackScreen, J.ReturnScreen, J.ReturnPoint, ReturnWorld);
		}
	}
	RefreshJoinConditions();
	if (UGameInstance* GI = World.GetGameInstance())
	{
		if (UDinkFactSubsystem* Facts = GI->GetSubsystem<UDinkFactSubsystem>())
		{
			FactHandle = Facts->OnAnyFactChangedNative.AddWeakLambda(this, [this](FName, int32, int32) { RefreshJoinConditions(); });
		}
	}
	UE_LOG(LogDinkExpanded, Display, TEXT("content packs built into %s: %d pack screen(s), %d actor(s), %d join trigger(s), beyond %d 1997 screens"),
		*World.GetName(), PackCorners.Num(), Spawned.Num(), Joins.Num(), Base.Num());
	return PackCorners.Num();
}

bool UDinkExpandedWorldSubsystem::MapPixelToWorld(int32 Screen, const FVector2D& MapPixel, FVector& OutWorld) const
{
	const FDinkScreenCorners* C = PackCorners.Find(Screen);
	if (!C)
	{
		C = BaseCorners.Find(Screen);
	}
	if (!C)
	{
		return false;
	}
	OutWorld = DinkLayout::MapPixelToUnreal(*C, MapPixel.X, MapPixel.Y);
	return true;
}

ADinkExpandedJoinActor* UDinkExpandedWorldSubsystem::FindJoin(const FString& JoinId, FName Side) const
{
	for (ADinkExpandedJoinActor* J : Joins)
	{
		if (J && J->JoinId == JoinId && J->Side == Side)
		{
			return J;
		}
	}
	return nullptr;
}

void UDinkExpandedWorldSubsystem::RefreshJoinConditions()
{
	const UGameInstance* GI = GetWorld() ? GetWorld()->GetGameInstance() : nullptr;
	const UDinkFactSubsystem* Facts = GI ? GI->GetSubsystem<UDinkFactSubsystem>() : nullptr;
	for (ADinkExpandedJoinActor* J : Joins)
	{
		if (J && !J->RequiresFact.IsNone())
		{
			J->bConditionMet = Facts && Facts->GetFact(J->RequiresFact) >= J->RequiresAtLeast;
			J->Warp->bTriggerEnabled = J->bConditionMet;
		}
	}
}

// ---------------------------------------------------------------------------------------------
// Saves

bool UDinkExpandedGameSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	return DinkExpanded::IsEnabled() && Super::ShouldCreateSubsystem(Outer);
}

void UDinkExpandedGameSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	if (UDinkSaveSubsystem* Saves = Collection.InitializeDependency<UDinkSaveSubsystem>())
	{
		CapturedHandle = Saves->OnSnapshotCaptured.AddUObject(this, &UDinkExpandedGameSubsystem::HandleCaptured);
		AppliedHandle = Saves->OnSnapshotApplied.AddUObject(this, &UDinkExpandedGameSubsystem::HandleApplied);
	}
}

void UDinkExpandedGameSubsystem::Deinitialize()
{
	if (UDinkSaveSubsystem* Saves = GetGameInstance() ? GetGameInstance()->GetSubsystem<UDinkSaveSubsystem>() : nullptr)
	{
		Saves->OnSnapshotCaptured.Remove(CapturedHandle);
		Saves->OnSnapshotApplied.Remove(AppliedHandle);
	}
	Super::Deinitialize();
}

bool UDinkExpandedGameSubsystem::FindReturnPoint(const FDinkExpandedRegistry& Registry, int32 PackScreen, int32& OutScreen, FVector2D& OutPoint)
{
	const FDinkPack* Pack = nullptr;
	if (!Registry.FindScreen(PackScreen, &Pack) || !Pack || Pack->Joins.Num() == 0)
	{
		return false;
	}
	OutScreen = Pack->Joins[0].ReturnScreen;
	OutPoint = Pack->Joins[0].ReturnPoint;
	return true;
}

bool UDinkExpandedGameSubsystem::MakeSaveSafe(UDinkSaveGame* Save, const FDinkExpandedRegistry& Registry, const FTransform& ReturnTransform, int32 ReturnScreen)
{
	if (!Save || !Registry.IsPackScreen(Save->CurrentScreen))
	{
		return false;
	}
	const TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
	O->SetNumberField(TEXT("version"), 1);
	O->SetNumberField(TEXT("screen"), Save->CurrentScreen);
	const FVector L = Save->PlayerTransform.GetLocation();
	O->SetNumberField(TEXT("x"), L.X);
	O->SetNumberField(TEXT("y"), L.Y);
	O->SetNumberField(TEXT("z"), L.Z);
	O->SetNumberField(TEXT("yaw"), Save->PlayerTransform.Rotator().Yaw);
	FString Text;
	FJsonSerializer::Serialize(O, TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
	Save->SubsystemState.Add(NAME_Expanded, Text);
	Save->CurrentScreen = ReturnScreen;
	Save->PlayerTransform = ReturnTransform;
	return true;
}

void UDinkExpandedGameSubsystem::HandleCaptured(UDinkSaveGame* Save)
{
	const FDinkExpandedRegistry& Registry = DinkExpanded::GetRegistry();
	if (!Save || !Registry.IsPackScreen(Save->CurrentScreen))
	{
		return;
	}
	int32 ReturnScreen = 0;
	FVector2D ReturnPoint;
	UWorld* World = GetGameInstance() ? GetGameInstance()->GetWorld() : nullptr;
	UDinkExpandedWorldSubsystem* Packs = World ? World->GetSubsystem<UDinkExpandedWorldSubsystem>() : nullptr;
	FVector Where;
	if (!FindReturnPoint(Registry, Save->CurrentScreen, ReturnScreen, ReturnPoint) || !Packs || !Packs->MapPixelToWorld(ReturnScreen, ReturnPoint, Where))
	{
		UE_LOG(LogDinkExpanded, Warning, TEXT("save on pack screen %d: no 1997 return point; the save keeps the pack position"), Save->CurrentScreen);
		return;
	}
	FTransform Safe = Save->PlayerTransform;
	Safe.SetLocation(Where + FVector(0, 0, Save->PlayerTransform.GetLocation().Z));
	MakeSaveSafe(Save, Registry, Safe, ReturnScreen);
}

void UDinkExpandedGameSubsystem::HandleApplied(const UDinkSaveGame* Save)
{
	const FString* Text = Save ? Save->SubsystemState.Find(NAME_Expanded) : nullptr;
	TSharedPtr<FJsonObject> O;
	if (!Text || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(*Text), O) || !O.IsValid() ||
		!DinkExpanded::GetRegistry().IsPackScreen(O->GetIntegerField(TEXT("screen"))))
	{
		return;
	}
	const FVector L(O->GetNumberField(TEXT("x")), O->GetNumberField(TEXT("y")), O->GetNumberField(TEXT("z")));
	const FRotator R(0.0, O->GetNumberField(TEXT("yaw")), 0.0);
	UWorld* World = GetGameInstance() ? GetGameInstance()->GetWorld() : nullptr;
	if (!World)
	{
		return;
	}
	// After the 1997 load settled on the return point's screen: back to where the save was made (its screen's scripts start fresh,
	// as a 1997 load_game starts a screen).
	World->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateWeakLambda(this, [this, L, R]()
	{
		UWorld* W = GetGameInstance() ? GetGameInstance()->GetWorld() : nullptr;
		APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
		if (APawn* Pawn = PC ? PC->GetPawn() : nullptr)
		{
			Pawn->TeleportTo(L, R);
			if (UDinkGreyboxSubsystem* Greybox = W->GetSubsystem<UDinkGreyboxSubsystem>())
			{
				Greybox->RefreshCurrentScreen();
			}
		}
	}));
}
