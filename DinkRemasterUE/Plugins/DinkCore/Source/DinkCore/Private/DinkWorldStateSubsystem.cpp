#include "DinkWorldStateSubsystem.h"
#include "DinkCoreModule.h"

void UDinkWorldStateSubsystem::AdvanceGameTime(int64 DeltaMs)
{
	if (DeltaMs > 0)
	{
		GameTimeMs += DeltaMs;
	}
}

void UDinkWorldStateSubsystem::SetOverride(const FDinkOriginId& Origin, EDinkOverrideType Type, FName Variant)
{
	if (!Origin.IsValid())
	{
		UE_LOG(LogDink, Warning, TEXT("UDinkWorldStateSubsystem::SetOverride: invalid origin %d/%d"), Origin.Screen, Origin.Placement);
		return;
	}
	if (Type == EDinkOverrideType::None)
	{
		ClearOverride(Origin);
		return;
	}

	FDinkWorldOverride& Entry = Overrides.FindOrAdd(Origin);
	Entry.Origin = Origin;
	Entry.Type = Type;
	Entry.SetAtMs = GameTimeMs;
	Entry.Variant = Variant;
	Broadcast(Origin, Type);
}

void UDinkWorldStateSubsystem::ClearOverride(const FDinkOriginId& Origin)
{
	if (Overrides.Remove(Origin) > 0)
	{
		Broadcast(Origin, EDinkOverrideType::None);
	}
}

EDinkOverrideType UDinkWorldStateSubsystem::GetOverrideType(const FDinkOriginId& Origin) const
{
	const FDinkWorldOverride* Found = Overrides.Find(Origin);
	return Found ? Found->Type : EDinkOverrideType::None;
}

bool UDinkWorldStateSubsystem::TryGetOverride(const FDinkOriginId& Origin, FDinkWorldOverride& OutOverride) const
{
	if (const FDinkWorldOverride* Found = Overrides.Find(Origin))
	{
		OutOverride = *Found;
		return true;
	}
	return false;
}

bool UDinkWorldStateSubsystem::IsPlacementRemoved(const FDinkOriginId& Origin) const
{
	return IsRemovedType(GetOverrideType(Origin));
}

TArray<FDinkWorldOverride> UDinkWorldStateSubsystem::GetOverridesOnScreen(int32 Screen) const
{
	TArray<FDinkWorldOverride> Result;
	for (const TPair<FDinkOriginId, FDinkWorldOverride>& Pair : Overrides)
	{
		if (Pair.Key.Screen == Screen)
		{
			Result.Add(Pair.Value);
		}
	}
	Result.Sort([](const FDinkWorldOverride& A, const FDinkWorldOverride& B) { return A.Origin < B.Origin; });
	return Result;
}

void UDinkWorldStateSubsystem::NotifyScreenExited(int32 Screen)
{
	ScreenExitMs.Add(Screen, GameTimeMs);
}

int64 UDinkWorldStateSubsystem::GetScreenExitTimeMs(int32 Screen) const
{
	const int64* Found = ScreenExitMs.Find(Screen);
	return Found ? *Found : INDEX_NONE;
}

TArray<FDinkOriginId> UDinkWorldStateSubsystem::ProcessRespawns(int32 Screen)
{
	const int64 ExitMs = GetScreenExitTimeMs(Screen);
	TArray<FDinkOriginId> Respawned;
	for (const TPair<FDinkOriginId, FDinkWorldOverride>& Pair : Overrides)
	{
		if (Pair.Key.Screen == Screen && ShouldRespawn(Pair.Value, ExitMs, GameTimeMs))
		{
			Respawned.Add(Pair.Key);
		}
	}
	Respawned.Sort();
	for (const FDinkOriginId& Origin : Respawned)
	{
		ClearOverride(Origin);
	}
	return Respawned;
}

TArray<FDinkWorldOverride> UDinkWorldStateSubsystem::ExportOverrides() const
{
	TArray<FDinkWorldOverride> Result;
	Overrides.GenerateValueArray(Result);
	Result.Sort([](const FDinkWorldOverride& A, const FDinkWorldOverride& B) { return A.Origin < B.Origin; });
	return Result;
}

TArray<FDinkScreenExitTime> UDinkWorldStateSubsystem::ExportScreenExitTimes() const
{
	TArray<FDinkScreenExitTime> Result;
	for (const TPair<int32, int64>& Pair : ScreenExitMs)
	{
		FDinkScreenExitTime& Entry = Result.AddDefaulted_GetRef();
		Entry.Screen = Pair.Key;
		Entry.ExitedAtMs = Pair.Value;
	}
	Result.Sort([](const FDinkScreenExitTime& A, const FDinkScreenExitTime& B) { return A.Screen < B.Screen; });
	return Result;
}

void UDinkWorldStateSubsystem::ImportState(const TArray<FDinkWorldOverride>& InOverrides, const TArray<FDinkScreenExitTime>& InExitTimes, int64 InGameTimeMs)
{
	Overrides.Reset();
	ScreenExitMs.Reset();
	GameTimeMs = InGameTimeMs;
	for (const FDinkWorldOverride& Entry : InOverrides)
	{
		if (Entry.Origin.IsValid() && Entry.Type != EDinkOverrideType::None)
		{
			Overrides.Add(Entry.Origin, Entry);
		}
		else
		{
			UE_LOG(LogDink, Warning, TEXT("UDinkWorldStateSubsystem::ImportState: dropped override %s type %d"),
				*Entry.Origin.ToString(), static_cast<int32>(Entry.Type));
		}
	}
	for (const FDinkScreenExitTime& Exit : InExitTimes)
	{
		ScreenExitMs.Add(Exit.Screen, Exit.ExitedAtMs);
	}
}

void UDinkWorldStateSubsystem::ResetState()
{
	Overrides.Reset();
	ScreenExitMs.Reset();
	GameTimeMs = 0;
}

int64 UDinkWorldStateSubsystem::GetRespawnDelayMs(EDinkOverrideType Type)
{
	switch (Type)
	{
	case EDinkOverrideType::RemovedReturn5Min: return Respawn5MinMs;
	case EDinkOverrideType::RemovedReturn3Min: return Respawn3MinMs;
	case EDinkOverrideType::RemovedReturn1Min: return Respawn1MinMs;
	default: return INDEX_NONE;
	}
}

bool UDinkWorldStateSubsystem::IsRemovedType(EDinkOverrideType Type)
{
	return Type == EDinkOverrideType::RemovedForever || IsTimedType(Type);
}

bool UDinkWorldStateSubsystem::ForcesHardness(EDinkOverrideType Type)
{
	// update_play_changes: 4 and 5 set hard = 0, which in the original means "has hardness".
	return Type == EDinkOverrideType::LiveHard || Type == EDinkOverrideType::BackgroundHard;
}

bool UDinkWorldStateSubsystem::IsBackgroundType(EDinkOverrideType Type)
{
	// update_play_changes: 3 and 5 set type = 0 (background).
	return Type == EDinkOverrideType::BackgroundNoHardness || Type == EDinkOverrideType::BackgroundHard;
}

bool UDinkWorldStateSubsystem::ShouldRespawn(const FDinkWorldOverride& Override, int64 InScreenExitMs, int64 NowMs)
{
	const int64 Delay = GetRespawnDelayMs(Override.Type);
	if (Delay == INDEX_NONE)
	{
		return false;
	}
	const int64 Reference = FMath::Max(Override.SetAtMs, InScreenExitMs);

	// dink.cpp D:932/943/953: g_dinkTick > last_time + delay (strictly greater).
	if (NowMs > Reference + Delay)
	{
		return true;
	}
	// dink.cpp D:933, type 6 only: g_dinkTick + 400000 < last_time + 300000.
	if (Override.Type == EDinkOverrideType::RemovedReturn5Min && NowMs + 400000 < Reference + Respawn5MinMs)
	{
		return true;
	}
	return false;
}

void UDinkWorldStateSubsystem::Broadcast(const FDinkOriginId& Origin, EDinkOverrideType Type)
{
	OnOverrideChangedNative.Broadcast(Origin, Type);
	OnOverrideChanged.Broadcast(Origin, Type);
}
