#include "DinkPlayerBlockers.h"
#include "DinkCollision.h"
#include "DinkCoreModule.h"
#include "ProceduralMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

const FName DinkPlayerBlockers::Tag(TEXT("DinkPlayerBlocker"));

static TAutoConsoleVariable<int32> CVarDinkPlayerBlockers(TEXT("dink.PlayerBlockers"), 1,
	TEXT("1 = drawn solid meshes larger than their 1997 hardness block the player (Data/Art/player_blockers.json; player only); 0 = off. Read when a mesh is placed."));

FString DinkPlayerBlockers::DefaultPath() { return FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/player_blockers.json"); }

bool DinkPlayerBlockers::Parse(const FString& Json, TMap<FString, FDinkPlayerBlockerShape>& Out, TArray<FString>& Errors, TSet<FString>* OutSkip)
{
	TSharedPtr<FJsonObject> Root;
	FString Schema;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root || !Root->TryGetStringField(TEXT("schema"), Schema) ||
		Schema != TEXT("dink-player-blockers/1"))
	{
		Errors.Add(TEXT("not a dink-player-blockers/1 file"));
		return false;
	}
	const TArray<TSharedPtr<FJsonValue>>* Skip = nullptr;
	if (OutSkip && Root->TryGetArrayField(TEXT("skip_origins"), Skip))
		for (const TSharedPtr<FJsonValue>& V : *Skip) OutSkip->Add(V->AsString());
	const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
	if (!Root->TryGetArrayField(TEXT("meshes"), Rows)) { Errors.Add(TEXT("no meshes array")); return false; }
	for (const TSharedPtr<FJsonValue>& V : *Rows)
	{
		const TSharedPtr<FJsonObject> Row = V->AsObject();
		FDinkPlayerBlockerShape S;
		const TArray<TSharedPtr<FJsonValue>>* Hull = nullptr;
		const TArray<TSharedPtr<FJsonValue>>* Z = nullptr;
		if (!Row || !Row->TryGetStringField(TEXT("mesh"), S.Mesh) || !S.Mesh.StartsWith(TEXT("/Game/")) ||
			!Row->TryGetArrayField(TEXT("hull_cm"), Hull) || Hull->Num() < 3 || !Row->TryGetArrayField(TEXT("z_cm"), Z) || Z->Num() != 2)
		{
			Errors.Add(FString::Printf(TEXT("row %d: needs mesh, hull_cm (3+ points) and z_cm [low, high]"), Out.Num()));
			continue;
		}
		bool bOk = true;
		for (const TSharedPtr<FJsonValue>& P : *Hull)
		{
			const TArray<TSharedPtr<FJsonValue>>& XY = P->AsArray();
			if (XY.Num() != 2) { bOk = false; break; }
			S.HullCm.Add(FVector2D(XY[0]->AsNumber(), XY[1]->AsNumber()));
		}
		S.ZLowCm = (*Z)[0]->AsNumber();
		S.ZHighCm = (*Z)[1]->AsNumber();
		if (!bOk || S.ZHighCm <= S.ZLowCm) { Errors.Add(FString::Printf(TEXT("%s: bad hull or z range"), *S.Mesh)); continue; }
		Out.Add(S.Mesh, MoveTemp(S));
	}
	return true;
}

static TSet<FString> GDinkBlockerSkip;

const TMap<FString, FDinkPlayerBlockerShape>& DinkPlayerBlockers::Table()
{
	static TMap<FString, FDinkPlayerBlockerShape> Loaded;
	static bool bLoaded = false;
	if (!bLoaded)
	{
		bLoaded = true;
		FString Text;
		TArray<FString> Errors;
		if (FFileHelper::LoadFileToString(Text, *DefaultPath())) Parse(Text, Loaded, Errors, &GDinkBlockerSkip);
		for (const FString& E : Errors) UE_LOG(LogDink, Warning, TEXT("player_blockers.json: %s"), *E);
		UE_LOG(LogDink, Log, TEXT("Player blockers: %d meshes"), Loaded.Num());
	}
	return Loaded;
}

const FDinkPlayerBlockerShape* DinkPlayerBlockers::Find(const UStaticMesh* Mesh)
{
	if (!Mesh || CVarDinkPlayerBlockers.GetValueOnGameThread() == 0) return nullptr;
	return Table().Find(Mesh->GetPathName());
}

const TSet<FString>& DinkPlayerBlockers::SkipOrigins() { Table(); return GDinkBlockerSkip; }

UPrimitiveComponent* DinkPlayerBlockers::Add(AActor& Owner, USceneComponent& AttachTo, const FTransform& Relative, const UStaticMesh* Mesh, const FString& Origin)
{
	const FDinkPlayerBlockerShape* S = Find(Mesh);
	if (!S || (!Origin.IsEmpty() && SkipOrigins().Contains(Origin))) return nullptr;
	return AddShape(Owner, AttachTo, Relative, *S, Mesh);
}

UPrimitiveComponent* DinkPlayerBlockers::AddShape(AActor& Owner, USceneComponent& AttachTo, const FTransform& Relative, const FDinkPlayerBlockerShape& Shape,
	const UStaticMesh* Mesh)
{
	if (Shape.HullCm.Num() < 3 || Shape.ZHighCm <= Shape.ZLowCm) return nullptr;
	TArray<FVector> Points;
	for (const FVector2D& P : Shape.HullCm)
	{
		Points.Add(FVector(P.X, P.Y, Shape.ZLowCm));
		Points.Add(FVector(P.X, P.Y, Shape.ZHighCm));
	}
	UDinkPlayerBlockerComponent* Block = NewObject<UDinkPlayerBlockerComponent>(&Owner, NAME_None, RF_Transient);
	Block->Drawn = &AttachTo;
	Block->Mesh = Mesh;
	Block->bUseAsyncCooking = false;
	Block->bUseComplexAsSimpleCollision = false;
	Block->SetMobility(EComponentMobility::Movable);
	Block->SetupAttachment(&AttachTo);
	Block->SetRelativeTransform(Relative);
	Block->SetVisibility(false);
	Block->SetHiddenInGame(true);
	Block->SetCastShadow(false);
	Block->SetCanEverAffectNavigation(false);
	Block->SetGenerateOverlapEvents(false);
	Block->ComponentTags.Add(Tag);
	Block->AddCollisionConvexMesh(Points);
	Block->SetCollisionProfileName(DinkCollision::ProfilePlayerBlock);
	Owner.AddInstanceComponent(Block);
	Block->RegisterComponent();
	return Block;
}

UDinkPlayerBlockerComponent::UDinkPlayerBlockerComponent(const FObjectInitializer& ObjectInitializer) : Super(ObjectInitializer)
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickInterval = 0.2f;
}

bool UDinkPlayerBlockerComponent::IsDrawnShown() const
{
	const USceneComponent* D = Drawn.Get();
	const AActor* O = D ? D->GetOwner() : nullptr;
	return D && O && D->IsVisible() && !D->bHiddenInGame && !O->IsHidden();
}

void UDinkPlayerBlockerComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	const ECollisionEnabled::Type Want = IsDrawnShown() ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision;
	if (GetCollisionEnabled() != Want) SetCollisionEnabled(Want);
}
