#include "DinkCreatureEvents.h"
#include "DinkCreatureClassComponent.h"
#include "DinkCreatureOneShots.h"
#include "DinkCreatureSubsystem.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

namespace
{
	const FName E_Brain(TEXT("brain"));
	const FName E_BrainParm(TEXT("brain_parm"));
	const FName E_AttackWait(TEXT("attack_wait"));
	const FName T_Cast(TEXT("cast"));
	const FName T_Missile(TEXT("missile"));
	const FName T_Touch(TEXT("touch"));

	const FDinkCreatureOneShotRow* AttackRow(const UDinkCreatureClassComponent* Body, FName Trigger)
	{
		const FDinkCreatureOneShotRow* Row = Body ? DinkCreatureOneShots::Find(Body->GetClassId()) : nullptr;
		return Row && Row->AttackTrigger == Trigger && Row->Attack.IsSet() ? Row : nullptr;
	}
}

bool UDinkCreatureEventSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{
	return Type == EWorldType::Game || Type == EWorldType::PIE;
}

UDinkCreatureClassComponent* UDinkCreatureEventSubsystem::NearestAttacker(const UDinkDirector& Director, const FVector& At, FName Trigger) const
{
	UDinkCreatureClassComponent* Best = nullptr;
	double BestDist = TNumericLimits<double>::Max();
	const int32 Screen = Director.GetCurrentScreen();
	for (const TPair<int32, FDinkSprite>& Pair : Director.GetSprites())
	{
		const FDinkSprite& S = Pair.Value;
		if (Pair.Key == 1 || !S.bActive || (S.Screen > 0 && S.Screen != Screen)) continue;
		UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(S.Actor.Get());
		const FDinkCreatureOneShotRow* Row = AttackRow(Body, Trigger);
		if (!Row) continue;
		const double D = FVector::Dist2D(Body->GetShownLocation(), At);
		if (D <= Row->AttackRadiusCm && D < BestDist) { BestDist = D; Best = Body; }
	}
	return Best;
}

void UDinkCreatureEventSubsystem::Observe(const UDinkDirector& Director)
{
	const int32 Screen = Director.GetCurrentScreen();
	if (Screen != LastScreen)
	{
		LastScreen = Screen;
		SeenMissiles.Reset();
		LastAttackWait.Reset();
		LastLife = -1;
	}
	TSet<int32> Missiles;
	TMap<int32, int32> AttackWaits;
	for (const TPair<int32, FDinkSprite>& Pair : Director.GetSprites())
	{
		const FDinkSprite& S = Pair.Value;
		if (!S.bActive || (S.Screen > 0 && S.Screen != Screen)) continue;
		// A caster's ATTACK ran: its script set sp_attack_wait forward (en-drag.c attack(): random(5000,3000) ms on).
		if (Pair.Key != 1)
		{
			if (UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(S.Actor.Get()); AttackRow(Body, T_Cast))
			{
				const int32 Wait = S.GetProp(E_AttackWait);
				AttackWaits.Add(Pair.Key, Wait);
				const int32* Before = LastAttackWait.Find(Pair.Key);
				if (Before && Wait > *Before && Body->PlayOneShot(EDinkCreatureOneShot::Attack)) ++Attacks;
			}
		}
		// A missile that was not there last frame, and not one of Dink's (brain_parm 1: it must not hit Dink): whoever
		// spat it strikes.
		const int32 Brain = S.GetProp(E_Brain);
		if (Brain != 11 && Brain != 17) continue;
		Missiles.Add(Pair.Key);
		if (SeenMissiles.Contains(Pair.Key) || !S.Actor.IsValid() || S.GetProp(E_BrainParm) == 1) continue;
		if (UDinkCreatureClassComponent* Body = NearestAttacker(Director, S.Actor->GetActorLocation(), T_Missile))
			if (Body->PlayOneShot(EDinkCreatureOneShot::Attack)) ++Attacks;
	}
	SeenMissiles = MoveTemp(Missiles);
	LastAttackWait = MoveTemp(AttackWaits);
	// Dink lost life to a biter's touch: the touch damage list made that sprite his last_hit and started his touch
	// immunity this frame (UDinkGameplay::RunThroughTouchDamageList). Any other loss of life (a hit, a spell, a load) is not
	// a bite.
	const UGameInstance* Instance = GetWorld() ? GetWorld()->GetGameInstance() : nullptr;
	const UDinkFactSubsystem* Facts = Instance ? Instance->GetSubsystem<UDinkFactSubsystem>() : nullptr;
	const int32 Life = Facts ? Facts->GetFact(TEXT("life")) : -1;
	const FDinkSprite* Dink = Director.FindSprite(1);
	if (LastLife >= 0 && Life >= 0 && Life < LastLife && Dink && Dink->bNoTouch && Dink->LastHit > 1)
	{
		const FDinkSprite* Biter = Director.FindSprite(Dink->LastHit);
		UDinkCreatureClassComponent* Body = Biter && Biter->bActive ? UDinkCreatureSubsystem::FindClassBody(Biter->Actor.Get()) : nullptr;
		if (AttackRow(Body, T_Touch) && Body->PlayOneShot(EDinkCreatureOneShot::Attack)) ++Attacks;
	}
	LastLife = Life;
}

#include "DinkGameplay.h"
#include "DinkStorySubsystem.h"
#include "HAL/IConsoleManager.h"
#include "EngineUtils.h"

namespace
{
// Review only (captures of the creature one-shots): the creature's own kill path of the simulation, run on demand, because
// at the play camera Dink's 1997 reach seldom lands a blow on a held creature (bug A70). It hurts the sprite through
// UDinkGameplay::HurtThing + ProcessDamage, exactly as a hit of Dink's would, so it changes the game state: never in play.
FAutoConsoleCommandWithWorldAndArgs CreatureHurt(TEXT("dink.Creature.Hurt"),
	TEXT("dink.Creature.Hurt <class> <damage>: review only. Hurts the live sprite of the nearest shown body of that class through the simulation's own damage path (HurtThing, ProcessDamage), as a hit of Dink's would."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
{
	if (!World || Args.Num() < 2 || !World->GetGameInstance()) return;
	UDinkStorySubsystem* Story = World->GetGameInstance()->GetSubsystem<UDinkStorySubsystem>();
	UDinkDirector* Director = Story ? Story->GetDirector() : nullptr;
	UDinkGameplay* Game = Story ? Story->GetGameplay() : nullptr;
	if (!Director || !Game) return;
	const FName Class(*Args[0]);
	const AActor* Dink = Director->GetDink().Actor.Get();
	const FVector From = Dink ? Dink->GetActorLocation() : FVector::ZeroVector;
	// Placed creatures are actors first; their sprite handle comes from the director (HandleForActor), as in the tests.
	AActor* BestActor = nullptr;
	double BestDist = TNumericLimits<double>::Max();
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		const UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(*It);
		if (!Body || It->IsHidden() || Body->GetClassId() != Class) continue;
		const double D = FVector::DistSquared(Body->GetShownLocation(), From);
		if (D < BestDist) { BestDist = D; BestActor = *It; }
	}
	const int32 Best = BestActor ? Director->HandleForActor(BestActor) : 0;
	const FDinkSprite* Sprite = Best ? Director->FindSprite(Best) : nullptr;
	if (Sprite && !Sprite->bActive) { UE_LOG(LogTemp, Display, TEXT("dink.Creature.Hurt %s: the nearest body is not alive"), *Class.ToString()); return; }
	if (!Best) { UE_LOG(LogTemp, Display, TEXT("dink.Creature.Hurt %s: no live body of that class"), *Class.ToString()); return; }
	Game->HurtThing(Best, FCString::Atoi(*Args[1]));
	Game->ProcessDamage();
	Story->RunUntilIdle();
	UE_LOG(LogTemp, Display, TEXT("dink.Creature.Hurt %s: sprite %d hurt"), *Class.ToString(), Best);
}));
}
