#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Engine/EngineBaseTypes.h"
#include "DinkWorldLifePresenter.generated.h"

/**
 * The world-life effects that follow the director's sprites (stream world-alive, 15 Nov 2026), drawn through
 * UDinkWorldLifeSubsystem (DinkCore): fire on burning sprites (seq 20 trees, 155-157 small fires, 86 hearths,
 * 425/427 torches and flames: world_life.json `fire.sequences`), the fireball's glow, trail and light, the burst of an
 * explosion (seq 70, 161, 167, 171; never 164, which the creature layer draws as a blood burst), staves and dust when a barrel breaks (its sprite turns to seq 173),
 * dust and grit while Dink pushes (seq 312-318) and at the foot of a pushed rock that moves.
 *
 * Strictly one way, like UDinkCreaturePresenter: it reads the director and the gameplay data as const, never sets a
 * sprite property, never moves an actor, never draws from the simulation's random stream. The only thing it changes
 * outside its own particles is the visibility of the grey placeholder marker of a create_sprite actor while it draws
 * that sprite itself (a fireball, an explosion), and it shows the marker again when it stops. Its end-of-frame step is
 * registered only in a world that can render; dink.World.Life 0 stops it.
 */
struct FDinkWorldLifePresentTickFunction : public FTickFunction
{
	class UDinkWorldLifePresenter* Target = nullptr;
	virtual void ExecuteTick(float DeltaTime, ELevelTick TickType, ENamedThreads::Type CurrentThread, const FGraphEventRef& MyCompletionGraphEvent) override;
	virtual FString DiagnosticMessage() override { return TEXT("FDinkWorldLifePresentTickFunction"); }
	virtual FName DiagnosticContext(bool bDetailed) override { return FName(TEXT("DinkWorldLifePresent")); }
};

/** What the presenter makes of one sprite this frame (pure, tested). */
enum class EDinkLifeSpriteRole : uint8
{
	None,
	Fire,        // a fire sequence
	Fireball,    // a missile brain (11/17) on a fireball sequence
	Missile,     // any other missile (arrows, axes): a faint trail only
	Burst,       // an explosion sequence
	Barrel,      // a barrel's break sequence
};

namespace DinkWorldLifeRoles
{
	struct FTables
	{
		TSet<int32> Fire;
		TSet<int32> Fireball;
		TSet<int32> Bursts;
		TSet<int32> BarrelBreak;
		TSet<int32> MissileBrains;
		TSet<int32> PushSeqs;
	};
	/** The 1997 defaults (dink.ini / the item and damage scripts); world_life.json may extend them. */
	DINKNARRATIVE_API FTables Defaults();
	DINKNARRATIVE_API EDinkLifeSpriteRole RoleOf(const FTables& T, int32 Seq, int32 PSeq, int32 Brain);
}

UCLASS()
class DINKNARRATIVE_API UDinkWorldLifePresenter : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	bool IsPresenting() const { return PresentTick.IsTickFunctionRegistered(); }

	/** One pass over the director's sprites. Tick calls it. */
	void Present(float DeltaTime);
	int32 GetFollowedCount() const { return Followed.Num(); }
	/** Review only (dink.World.Demo): one of the presenter's effects at a ground point. */
	void Demo(const FString& Kind, const FVector& Ground);

private:
	struct FFollow
	{
		EDinkLifeSpriteRole Role = EDinkLifeSpriteRole::None;
		int32 Seq = 0;
		FVector Last = FVector::ZeroVector;
		float Trail = 0.f;
		bool bMarkerHidden = false;
		TWeakObjectPtr<AActor> Actor;
	};
	void LoadTables();
	void Burst(const FVector& At, bool bBig);
	void BarrelBreak(const FVector& At);
	void RestoreMarker(FFollow& F);
	void TickDemos(float DeltaTime);
	struct FDemoFire { FVector Base; float Height; float Scale; float Until; };
	struct FDemoBall { FVector From; FVector To; float Start; float Seconds; };
	TArray<FDemoFire> DemoFire;
	FDemoBall DemoBall;
	bool bDemoBall = false;

	FDinkWorldLifePresentTickFunction PresentTick;
	DinkWorldLifeRoles::FTables Tables;
	TMap<int32, FFollow> Followed;
	int32 SeenScreen = 0;
	int32 SeenResetSerial = 0;
	float PushTimer = 0.f;
	uint32 Rand = 0x2545F491u;
	float Frand();
};
