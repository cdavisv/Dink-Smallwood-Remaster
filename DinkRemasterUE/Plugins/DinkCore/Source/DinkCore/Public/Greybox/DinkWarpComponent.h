#pragma once

#include "CoreMinimal.h"
#include "Components/BoxComponent.h"
#include "DinkWarpComponent.generated.h"

class APawn;

/**
 * A warp of the original game: walking into the trigger moves the player to another screen.
 *
 * Sprite warps (placements with prop = 1, 93 in the base game) block and fire when Dink walks
 * into their hardbox; the importer puts the hardbox into the screen's solid collision and makes
 * this box a little larger so the overlap fires on contact. Script warps (`&player_map = N`
 * in DinkC) are approximated: placed ones fire on contact with their placement, others are
 * markers with the trigger disabled. Story conditions, door animations and fades are not
 * modelled yet (greybox).
 */
UCLASS(ClassGroup = (Dink), meta = (BlueprintSpawnableComponent))
class DINKCORE_API UDinkWarpComponent : public UBoxComponent
{
	GENERATED_BODY()

public:
	UDinkWarpComponent();

	/** "S001_P25" for sprite warps, "SW_s6-hole_L22@S243_P05" for a source of a script warp. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	FString WarpId;

	/** "sprite" or "script". */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	FName Source;

	/** door, exit, stairs, hole, cave_mouth, pit, teleport_machine, script_transition, ... (tools/analyse warps.json). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	FName Kind;

	/** walk_in (sprite warp), touch_approx (placed script warp), script_only (inactive marker). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	FName TriggerMode;

	/** DinkC script that performs the warp (script warps), or the placement's script. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	FName Script;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	int32 SourceScreen = 0;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	int32 DestScreen = 0;

	/** Destination in original map pixels (warp_x minus 20, warp_y). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	FVector2D DestMapPixel = FVector2D::ZeroVector;

	/** Destination on the ground, Unreal world space (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	FVector DestLocation = FVector::ZeroVector;

	/** False when the destination screen was not part of this import (region import) or the trigger is a marker. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	bool bTriggerEnabled = true;

	/** Sprite sequence the original plays before the fade (doors), 0 if none. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	int32 AnimSequence = 0;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	bool bOneWay = false;

	/** Warps on the destination screen that lead back (nearest first). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	TArray<FString> ReturnWarps;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dink|Warp")
	FString Note;

	/** Moves Pawn to the destination if the trigger is enabled and the pawn is not in its post-warp cooldown. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Warp")
	bool TryWarp(APawn* Pawn);

    /** Direction into this overlap captured on entry, retained past its centre until exit. */
    FVector GetRetryApproachDirection(const APawn* Pawn) const;

protected:
	virtual void BeginPlay() override;

	UFUNCTION()
	void HandleBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
    UFUNCTION()
    void HandleEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
        UPrimitiveComponent* OtherComp, int32 OtherBodyIndex);
private:
    TMap<TWeakObjectPtr<APawn>, FVector> RetryApproachDirections;
};
