#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "DinkFloatingNumbers.generated.h"

class UTextRenderComponent;

/** What a floating number shows (the 1997 text_draw colours, dink.cpp:11712-11785). */
enum class EDinkFloatingNumber : uint8
{
	/** draw_damage (dink.cpp:12339-12356): the damage a monster, a duck, a dragon or a person took; white (font colour 15). */
	Damage,
	/** add_exp (dink.cpp:623-644): experience Dink earned, 30 px higher; yellow (brain_parm 5000 -> font colour 14). */
	Experience,
};

/**
 * The original's floating numbers (alpha mechanics QA, 15 Nov 2026): every hit on a monster showed the damage done over it, and
 * every kill the experience earned, as a number that rises one pixel a frame for one second (speed 1, my -1, kill 1000) and is
 * gone. The 1997 engine made each one a text sprite (brain 8); here they are presentation only, world-space text that faces the
 * camera and is never a sprite of the simulation, so script sprite numbers and probe traces stay as they were.
 */
UCLASS()
class DINKNARRATIVE_API UDinkFloatingNumbers : public UTickableWorldSubsystem
{
	GENERATED_BODY()
public:
	/** Starts a number at At (world, the top of the sprite that took the hit). */
	void Show(const FVector& At, int32 Value, EDinkFloatingNumber Kind);
	/** Numbers on screen now (tests). */
	int32 Num() const { return Live.Num(); }
	/** The text of the newest number (tests). */
	FString NewestText() const;

	/** One second on screen, as kill 1000. */
	static constexpr float LifeSeconds = 1.f;
	/** Rise over that second: the original's 60 px is a little more than a monster's height; here about one body. */
	static constexpr float RiseCm = 80.f;
	/** The experience number starts higher (30 px in the original). */
	static constexpr float ExperienceLiftCm = 40.f;

	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void Deinitialize() override;

private:
	struct FLive
	{
		TWeakObjectPtr<AActor> Actor;
		TWeakObjectPtr<UTextRenderComponent> Text, Shadow;
		FVector Start = FVector::ZeroVector;
		float Age = 0.f;
	};
	TArray<FLive> Live;
};
