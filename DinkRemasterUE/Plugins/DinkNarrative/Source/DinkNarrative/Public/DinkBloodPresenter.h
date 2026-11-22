#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkBloodPresenter.generated.h"

class UDecalComponent;
class UMaterialInterface;

/**
 * Draws the original's hit blood (random_blood, dink.cpp:6675-6700) as ground decals.
 *
 * In 1997 every damaging hit (a melee blow either way, a missile, touch damage, the DinkC hurt command) adds a blood spurt
 * sprite, sequence 187-189 (or sp_blood_seq), played once by brain 5 and then drawn into the screen's background, where the
 * last frame stays until the screen is drawn again (one_time_brain, D:15741-15768). The remaster's simulation records those
 * calls (UDinkGameplay::GetBloodEvents, FDinkBloodEvent); this layer turns each new one into a blood decal on the ground
 * under the hit sprite, at least as large as the spurt's last 1997 picture, and removes them all when the screen changes
 * or the director recreates its sprites (a load), as the original's background redraw does.
 *
 * Strictly one way: reads the director and the gameplay object, never writes to a sprite, never draws from the
 * simulation's random stream (the spurt sequence is the one the simulation drew, as 1997's random_blood; the decal cell
 * and turn come from a hash of the event). Data:
 * Content/Dink/Data/Environment/environment.json `hit_blood`. Off in a process that cannot render, and with dink.HitBlood 0.
 */
UCLASS()
class DINKNARRATIVE_API UDinkBloodPresenter : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual void Deinitialize() override;

	/** One pass over new blood events. Tick calls it; tests call it directly. Returns decals made. */
	int32 Present(float DeltaTime = 0.f);
	/** dink.HitBlood 0: clears the decals and consumes the blood events made so far. Tick calls it while the switch is off. */
	void Suppress();
	int32 GetDecalCount() const { return Decals.Num(); }
	const TArray<TObjectPtr<UDecalComponent>>& GetDecals() const { return Decals; }

	/**
	 * Fallback spurt sequence for an event that carries none (FDinkBloodEvent::Seq 0): BloodSeq + (hash % BloodNum) when the
	 * sprite sets both, else 187 + (hash % 3). Events from the simulation carry the sequence its rand() draw chose (D:6693).
	 */
	static int32 SpurtSequence(int32 BloodSeq, int32 BloodNum, uint32 Hash);
	/**
	 * Side of the square decal (cm) for a spurt picture of WidthPx x HeightPx engine pixels: the longer side at the
	 * original's 2.5 cm per pixel (the greybox's "base" card scale of the placed blood splats) times Margin, so the decal
	 * never covers less ground than the 1997 picture.
	 */
	static double DecalSideCm(int32 WidthPx, int32 HeightPx, double CmPerPx = 2.5, double Margin = 1.15);

	/** Decals kept on one screen; the oldest goes first beyond this (1997 draws into the background without a limit). */
	static constexpr int32 MaxDecals = 400;

private:
	void LoadConfig();
	void Clear();

	bool bConfigLoaded = false;
	/** Last-frame picture size (px) of each spurt sequence. */
	TMap<int32, FIntPoint> PictureSize;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInterface>> Materials;
	double CmPerPx = 2.5;
	double Margin = 1.15;
	/** Half the depth of the projection box (cm). */
	double DepthCm = 20.0;
	/** Seconds a new decal takes to spread to its full size (the spurt's animation, 1997 frames 1..last). */
	double SpreadS = 0.25;

	uint32 SeenSerial = 0;
	int32 SeenScreen = -1;
	int32 SeenResetSerial = -1;
	UPROPERTY(Transient)
	TObjectPtr<AActor> Holder;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UDecalComponent>> Decals;
	/** Full half-size and age of each decal (parallel to Decals) while it spreads. */
	TArray<FVector2D> Spreading;
};
