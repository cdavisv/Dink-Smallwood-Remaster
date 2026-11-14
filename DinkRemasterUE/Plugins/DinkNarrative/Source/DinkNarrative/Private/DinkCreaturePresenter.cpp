#include "DinkCreaturePresenter.h"
#include "DinkCreatureClassComponent.h"
#include "DinkCreatureSubsystem.h"
#include "DinkDirector.h"
#include "DinkGameplay.h"
#include "DinkScriptSpriteComponent.h"
#include "DinkStorySubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

namespace
{
	const FName C_Seq(TEXT("seq")), C_PSeq(TEXT("pseq")), C_Frame(TEXT("frame")), C_BaseWalk(TEXT("base_walk")), C_BaseDeath(TEXT("base_death")),
		C_Size(TEXT("size")), C_Hitpoints(TEXT("hitpoints")), C_Brain(TEXT("brain"));
}

bool UDinkCreaturePresenter::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void FDinkCreaturePresentTickFunction::ExecuteTick(float DeltaTime, ELevelTick TickType, ENamedThreads::Type CurrentThread, const FGraphEventRef& MyCompletionGraphEvent)
{
	if (IsValid(Target) && TickType != LEVELTICK_ViewportsOnly) Target->Present();
}

void UDinkCreaturePresenter::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	if (!UDinkCreatureSubsystem::IsClassArtAllowed() || !InWorld.PersistentLevel || PresentTick.IsTickFunctionRegistered()) return;
	PresentTick.Target = this;
	PresentTick.TickGroup = TG_PostUpdateWork;
	PresentTick.bCanEverTick = true;
	PresentTick.bStartWithTickEnabled = true;
	PresentTick.RegisterTickFunction(InWorld.PersistentLevel);
}

void UDinkCreaturePresenter::Deinitialize()
{
	if (PresentTick.IsTickFunctionRegistered()) PresentTick.UnRegisterTickFunction();
	Super::Deinitialize();
}

float UDinkCreaturePresenter::SequenceDuration(const UDinkGameplay& Game, int32 Sequence)
{
	if (Sequence <= 0) return 0.f;
	if (const float* Known = Durations.Find(Sequence)) return *Known;
	// The animator shows frame f for its delay and ends at the first slot without a picture (UDinkGameplay::Animate).
	const FDinkGameplayData& Data = Game.GetData();
	int32 Ms = 0;
	for (int32 Frame = 1; Frame <= 64 && Data.FrameCode(Sequence, Frame) >= 1; ++Frame) Ms += FMath::Max(0, Data.FrameDelay(Sequence, Frame));
	return Durations.Add(Sequence, Ms / 1000.f);
}

void UDinkCreaturePresenter::Present()
{
	UWorld* World = GetWorld();
	UDinkCreatureSubsystem* Creatures = World ? World->GetSubsystem<UDinkCreatureSubsystem>() : nullptr;
	const UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
	const UDinkStorySubsystem* Story = Instance ? Instance->GetSubsystem<UDinkStorySubsystem>() : nullptr;
	// const: this layer reads the simulation and writes only to its own bodies.
	const UDinkDirector* Director = Story ? Story->GetDirector() : nullptr;
	const UDinkGameplay* Game = Story ? Story->GetGameplay() : nullptr;
	if (!Creatures || !Director || !Game || Creatures->GetClassBindings().IsEmpty()) return;

	const int32 Screen = Director->GetCurrentScreen();
	if (Screen != SeenScreen)
	{
		// The original redraws the screen: its corpse sprites go, and the sprites of the old screen did not die.
		SeenScreen = Screen;
		Seen.Reset();
		Creatures->ClearCorpses();
	}
	TSet<int32, DefaultKeyFuncs<int32>, TInlineSetAllocator<64>> Alive;
	for (const TPair<int32, FDinkSprite>& Pair : Director->GetSprites())
	{
		const FDinkSprite& Sprite = Pair.Value;
		AActor* Actor = Sprite.Actor.Get();
		if (Pair.Key == 1 || Sprite.bText || !Sprite.bActive || !Actor || (Sprite.Screen > 0 && Sprite.Screen != Screen)) continue;
		const int32 Seq = Sprite.GetProp(C_Seq), PSeq = Sprite.GetProp(C_PSeq), Size = Sprite.GetProp(C_Size, 100);
		UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(Actor);
		if (!Body && Sprite.bSpawned && Actor->IsA<ADinkScriptSpriteActor>())
		{
			DinkCreatureClass::FSpriteView View;
			View.Seq = Seq;
			View.PSeq = PSeq;
			View.BaseWalk = Sprite.GetProp(C_BaseWalk, -1);
			const float Yaw = float(DinkCreatureClass::DirYawDegrees(DinkCreatureClass::DirOfSequence(Seq > 0 ? Seq : PSeq)));
			Body = Creatures->PresentScriptSprite(Actor, View, -ScriptSpriteLiftCm, Yaw, Size > 0 ? Size : 100);
		}
		if (!Body) continue;
		// The body shows this frame's sprite: it ticks after this step (both are in TG_PostUpdateWork).
		if (!Seen.Contains(Pair.Key) && PresentTick.IsTickFunctionRegistered()) Body->PrimaryComponentTick.AddPrerequisite(this, PresentTick);
		FDinkCreatureSpriteState State;
		State.Seq = Seq;
		State.PSeq = PSeq;
		State.Frame = Sprite.GetProp(C_Frame);
		State.Dir = Sprite.Dir;
		State.SizePercent = Size > 0 ? Size : 100;
		State.SequenceDurationS = SequenceDuration(*Game, Seq);
		FQuat Facing;
		if (Director->GetSpriteFacingRotation(Sprite, Facing))
		{
			State.bHasFacing = true;
			State.FacingYawDeg = float(Facing.Rotator().Yaw);
		}
		Body->ApplySpriteState(State);
		FSeen& Entry = Seen.FindOrAdd(Pair.Key);
		Entry.ClassId = Body->GetClassId();
		Entry.Ground = Body->GetShownLocation();
		Entry.Yaw = Body->GetShownYaw();
		Entry.Hitpoints = Sprite.GetProp(C_Hitpoints);
		Entry.Brain = Sprite.GetProp(C_Brain);
		Entry.SizePercent = State.SizePercent;
		Alive.Add(Pair.Key);
	}
	for (auto It = Seen.CreateIterator(); It; ++It)
	{
		if (Alive.Contains(It.Key())) continue;
		const FSeen& Last = It.Value();
		const FDinkSprite* Sprite = Director->FindSprite(It.Key());
		// The kill path of UDinkGameplay::ProcessDamage (pill_brain 9, dragon_brain 10): the hit points ran out, `die` ran
		// and left the brain alone, add_kill_sprite (dink.cpp:12359) removed the sprite. Anything else that removes a
		// sprite (sp_active, sp_kill, a script's own handling) leaves no corpse, as in the original.
		const bool bKilled = Sprite && !Sprite->bActive && Last.Hitpoints >= 1 && Sprite->GetProp(C_Hitpoints) < 1 &&
			(Last.Brain == 9 || Last.Brain == 10) && Sprite->GetProp(C_Brain) == Last.Brain;
		// The port removes the sprite without the direction change the engine makes for the corpse; it is made here.
		if (bKilled)
		{
			// Where the body is shown now: it moved once more after this step last read it (the bodies tick after the
			// presenter), and it stays put once its actor is hidden. A sprite whose actor is gone keeps the last reading.
			const UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(Sprite->Actor.Get());
			Creatures->LeaveCorpse(Last.ClassId, Sprite->GetProp(C_BaseDeath, -1), DinkCreatureClass::KillDir(Last.Brain, Sprite->Dir),
				Body ? Body->GetShownLocation() : Last.Ground, Body ? Body->GetShownYaw() : Last.Yaw, Last.SizePercent);
		}
		It.RemoveCurrent();
	}
}
