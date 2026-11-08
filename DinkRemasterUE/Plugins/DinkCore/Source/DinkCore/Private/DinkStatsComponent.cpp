#include "DinkStatsComponent.h"
#include "DinkCombat.h"
#include "DinkFactSubsystem.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"

UDinkStatsComponent::UDinkStatsComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UDinkStatsComponent::SetRandomSource(TSharedPtr<IDinkRandomSource> InSource)
{
	RandomSource = MoveTemp(InSource);
}

IDinkRandomSource& UDinkStatsComponent::GetRandomSource()
{
	if (!RandomSource.IsValid())
	{
		RandomSource = MakeShared<FDinkStreamRandomSource>(RandomSeed);
	}
	return *RandomSource;
}

void UDinkStatsComponent::SetFactMirrorTarget(UDinkFactSubsystem* InFacts)
{
	FactMirror = InFacts;
	BindFactMirror(InFacts);
	NotifyChanged();
}

const TArray<FName>& UDinkStatsComponent::GetMirroredFactNames()
{
	static const TArray<FName> Names = {
		TEXT("strength"), TEXT("defense"), TEXT("magic"), TEXT("life"), TEXT("lifemax"),
		TEXT("level"), TEXT("exp"), TEXT("gold"), TEXT("magic_level"), TEXT("magic_cost") };
	return Names;
}

bool UDinkStatsComponent::ApplyFactToStats(FDinkStats& S, FName Fact, int32 Value)
{
	static const FName Strength(TEXT("strength")), Defense(TEXT("defense")), Magic(TEXT("magic")), Life(TEXT("life")),
		LifeMax(TEXT("lifemax")), Level(TEXT("level")), Exp(TEXT("exp")), Gold(TEXT("gold")),
		MagicLevel(TEXT("magic_level")), MagicCost(TEXT("magic_cost"));
	if (Fact == Strength) { S.Strength = Value; }
	else if (Fact == Defense) { S.Defense = Value; }
	else if (Fact == Magic) { S.Magic = Value; }
	else if (Fact == Life) { S.Life = Value; }
	else if (Fact == LifeMax) { S.LifeMax = Value; }
	else if (Fact == Level) { S.Level = Value; }
	else if (Fact == Exp) { S.Exp = Value; }
	else if (Fact == Gold) { S.Gold = Value; }
	else if (Fact == MagicLevel) { S.MagicLevel = Value; }
	else if (Fact == MagicCost) { S.MagicCost = Value; }
	else { return false; }
	return true;
}

void UDinkStatsComponent::BeginPlay()
{
	Super::BeginPlay();
	if (bMirrorToFacts)
	{
		BindFactMirror(ResolveFactMirror());
		NotifyChanged();
	}
}

void UDinkStatsComponent::EndPlay(const EEndPlayReason::Type Reason)
{
	UnbindFactMirror();
	Super::EndPlay(Reason);
}

void UDinkStatsComponent::BindFactMirror(UDinkFactSubsystem* Facts)
{
	if (!Facts || BoundFacts.Get() == Facts)
	{
		return;
	}
	UnbindFactMirror();
	BoundFacts = Facts;
	FactChangedHandle = Facts->OnAnyFactChangedNative.AddUObject(this, &UDinkStatsComponent::HandleFactChanged);
	FactsResetHandle = Facts->OnFactsResetNative.AddUObject(this, &UDinkStatsComponent::HandleFactsReset);
}

void UDinkStatsComponent::UnbindFactMirror()
{
	if (UDinkFactSubsystem* Facts = BoundFacts.Get())
	{
		Facts->OnAnyFactChangedNative.Remove(FactChangedHandle);
		Facts->OnFactsResetNative.Remove(FactsResetHandle);
	}
	BoundFacts.Reset();
	FactChangedHandle.Reset();
	FactsResetHandle.Reset();
}

void UDinkStatsComponent::HandleFactChanged(FName Fact, int32 OldValue, int32 NewValue)
{
	if (!bMirrorToFacts || bWritingFacts)
	{
		return;
	}
	FDinkStats Updated = Stats;
	if (ApplyFactToStats(Updated, Fact, NewValue) && Updated != Stats)
	{
		Stats = Updated;
		NotifyChanged();
	}
}

void UDinkStatsComponent::HandleFactsReset()
{
	UDinkFactSubsystem* Facts = BoundFacts.Get();
	if (!bMirrorToFacts || bWritingFacts || !Facts)
	{
		return;
	}
	FDinkStats Updated = Stats;
	for (const FName& Name : GetMirroredFactNames())
	{
		int32 Value = 0;
		if (Facts->TryGetFact(Name, Value))
		{
			ApplyFactToStats(Updated, Name, Value);
		}
	}
	if (Updated != Stats)
	{
		Stats = Updated;
		NotifyChanged();
	}
}

void UDinkStatsComponent::SetStats(const FDinkStats& NewStats)
{
	Stats = NewStats;
	NotifyChanged();
}

int32 UDinkStatsComponent::TakeMeleeHit(int32 AttackerStrength)
{
	return LoseLife(DinkRules::ResolveMeleeHit(AttackerStrength, Stats.Defense, GetRandomSource()));
}

int32 UDinkStatsComponent::TakeMissileHit(int32 MissileStrength)
{
	return LoseLife(DinkRules::ResolveMissileHit(MissileStrength, Stats.Defense, GetRandomSource(), FixesLevel));
}

int32 UDinkStatsComponent::TakeTouchDamage(int32 TouchDamage, int64 NowMs)
{
	// D:15639: "if (touch_damage != -1) if (notouch) return;"
	if (TouchDamage <= 0 || IsTouchImmune(NowMs))
	{
		return 0;
	}
	TouchImmuneUntilMs = NowMs + DinkRules::TouchImmunityMs;
	return LoseLife(DinkRules::ResolveTouchDamage(TouchDamage, Stats.Defense, GetRandomSource()));
}

int32 UDinkStatsComponent::TakeScriptedDamage(int32 Damage)
{
	return LoseLife(DinkRules::ApplyDefense(Damage, Stats.Defense, GetRandomSource()));
}

int32 UDinkStatsComponent::LoseLife(int32 Amount)
{
	if (Amount <= 0)
	{
		return 0;
	}
	const bool bWasDead = IsDead();
	const int32 Lost = FMath::Min(Amount, FMath::Max(Stats.Life, 0));
	Stats.Life = FMath::Max(Stats.Life - Amount, 0);
	NotifyChanged();
	if (!bWasDead && IsDead())
	{
		OnDiedNative.Broadcast(this);
		OnDied.Broadcast(this);
	}
	return Lost;
}

int32 UDinkStatsComponent::AddExperience(int32 Amount)
{
	const int32 NewExp = DinkRules::AddExperience(Stats.Exp, Amount);
	if (NewExp != Stats.Exp)
	{
		Stats.Exp = NewExp;
		NotifyChanged();
	}
	return Stats.Exp;
}

bool UDinkStatsComponent::CanLevelUp() const
{
	return DinkRules::CanLevelUp(Stats);
}

int32 UDinkStatsComponent::GetExpForNextLevel() const
{
	return DinkRules::ExpForNextLevel(Stats.Level);
}

EDinkLevelUpOutcome UDinkStatsComponent::LevelUp(EDinkStatChoice Choice)
{
	const EDinkLevelUpOutcome Outcome = DinkRules::ApplyLevelUp(Stats, Choice);
	if (Outcome != EDinkLevelUpOutcome::NotReady)
	{
		NotifyChanged();
	}
	return Outcome;
}

void UDinkStatsComponent::AddGold(int32 Amount)
{
	if (Amount != 0)
	{
		Stats.Gold += Amount;
		NotifyChanged();
	}
}

void UDinkStatsComponent::SetMagicCost(int32 Cost)
{
	Stats.MagicCost = FMath::Max(Cost, 0);
	Stats.MagicLevel = FMath::Min(Stats.MagicLevel, Stats.MagicCost);
	NotifyChanged();
}

void UDinkStatsComponent::TickMagicCharge(bool bInventoryOpen)
{
	if (bInventoryOpen)
	{
		return;
	}
	const int32 NewLevel = DinkRules::MagicChargeStep(Stats.MagicLevel, Stats.Magic, Stats.MagicCost);
	if (NewLevel != Stats.MagicLevel)
	{
		Stats.MagicLevel = NewLevel;
		NotifyChanged();
	}
}

bool UDinkStatsComponent::CanCastSpell() const
{
	return Stats.MagicCost > 0 && DinkRules::CanCastSpell(Stats.MagicLevel, Stats.MagicCost);
}

bool UDinkStatsComponent::TryCastSpell()
{
	if (!CanCastSpell())
	{
		return false;
	}
	Stats.MagicLevel = 0;
	NotifyChanged();
	return true;
}

UDinkFactSubsystem* UDinkStatsComponent::ResolveFactMirror() const
{
	if (FactMirror.IsValid())
	{
		return FactMirror.Get();
	}
	const UWorld* World = GetWorld();
	const UGameInstance* GameInstance = World ? World->GetGameInstance() : nullptr;
	return GameInstance ? GameInstance->GetSubsystem<UDinkFactSubsystem>() : nullptr;
}

void UDinkStatsComponent::NotifyChanged()
{
	if (bMirrorToFacts)
	{
		if (UDinkFactSubsystem* Facts = ResolveFactMirror())
		{
			BindFactMirror(Facts);
			TGuardValue<bool> Writing(bWritingFacts, true);
			Facts->SetFact(TEXT("strength"), Stats.Strength);
			Facts->SetFact(TEXT("defense"), Stats.Defense);
			Facts->SetFact(TEXT("magic"), Stats.Magic);
			Facts->SetFact(TEXT("life"), Stats.Life);
			Facts->SetFact(TEXT("lifemax"), Stats.LifeMax);
			Facts->SetFact(TEXT("level"), Stats.Level);
			Facts->SetFact(TEXT("exp"), Stats.Exp);
			Facts->SetFact(TEXT("gold"), Stats.Gold);
			Facts->SetFact(TEXT("magic_level"), Stats.MagicLevel);
			Facts->SetFact(TEXT("magic_cost"), Stats.MagicCost);
		}
	}
	OnStatsChangedNative.Broadcast(this);
	OnStatsChanged.Broadcast(this);
}
