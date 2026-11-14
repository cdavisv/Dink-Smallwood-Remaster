#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Engine/EngineBaseTypes.h"
#include "DinkCreaturePresenter.generated.h"

/**
 * Shows the director's sprites through their class-bound creatures (creatures.json `classes`, DinkCreatureClass.h).
 *
 * At the end of every frame, after the story has run its scripts and brains (UDinkStorySubsystem is a tickable object,
 * ticked after the actor tick groups; this step runs in TG_PostUpdateWork and every body ticks after it), it reads each
 * sprite of the current screen (sequence, frame, direction, size) and hands that to the
 * creature body on the sprite's actor; a script-made sprite whose picture belongs to a bound class gets its body here.
 * When the simulation kills a sprite (ProcessDamage -> add_kill_sprite), the class's corpse is left where the body
 * stood, until the screen changes, as the original's corpse sprite.
 *
 * Strictly one way: it holds the director and the gameplay object as const, never sets a sprite property, never moves
 * an actor, never draws from the simulation's random stream. With the layer off (dink.CreatureClassArt 0, or 1 in a
 * process that does not render) its step is not registered at all.
 */
struct FDinkCreaturePresentTickFunction : public FTickFunction
{
	class UDinkCreaturePresenter* Target = nullptr;
	virtual void ExecuteTick(float DeltaTime, ELevelTick TickType, ENamedThreads::Type CurrentThread, const FGraphEventRef& MyCompletionGraphEvent) override;
	virtual FString DiagnosticMessage() override { return TEXT("FDinkCreaturePresentTickFunction"); }
	virtual FName DiagnosticContext(bool bDetailed) override { return FName(TEXT("DinkCreaturePresent")); }
};

UCLASS()
class DINKNARRATIVE_API UDinkCreaturePresenter : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	/** The end-of-frame step is registered (the layer is allowed in this process). */
	bool IsPresenting() const { return PresentTick.IsTickFunctionRegistered(); }

	/** One pass over the director's sprites. Tick calls it; tests call it after stepping the story. */
	void Present();
	/** Sprites followed on the current screen. */
	int32 GetFollowedCount() const { return Seen.Num(); }

	/** Script-made sprite actors stand 60 cm above the ground point of their pixel (UDinkDirector::SpawnSpriteActor). */
	static constexpr float ScriptSpriteLiftCm = 60.f;

private:
	/** A followed sprite as last seen alive: what the corpse needs once the sprite is gone. */
	struct FSeen
	{
		FName ClassId;
		FVector Ground = FVector::ZeroVector;
		float Yaw = 0.f;
		int32 Hitpoints = 0;
		int32 Brain = 0;
		int32 SizePercent = 100;
	};
	float SequenceDuration(const class UDinkGameplay& Game, int32 Sequence);
	FDinkCreaturePresentTickFunction PresentTick;
	TMap<int32, FSeen> Seen;
	TMap<int32, float> Durations;
	int32 SeenScreen = 0;
	/** UDinkDirector::GetSpriteResetSerial as of the last step. */
	int32 SeenResetSerial = 0;
};
