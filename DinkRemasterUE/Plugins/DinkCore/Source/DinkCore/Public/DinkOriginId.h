#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DinkOriginId.generated.h"

/**
 * Identity of one sprite placement in the original 1997 game: the screen it was placed on
 * (1..768, the number used by map.dat and by &player_map) and its placement index on that
 * screen (1..99, the editor sprite slot that the original save's spmap[screen].type[index]
 * is keyed by).
 *
 * Every actor converted from the original carries one of these (through UDinkOriginComponent)
 * so the remaster's world state, coverage reports and parity tests can be matched to the
 * original data mechanically.
 *
 * Text form: "S412_P03" (screen zero-padded to 3 digits, placement to 2). This is the same
 * form the extraction tools in the data repo use (tools/dinkex: Snnn_Pnn).
 */
USTRUCT(BlueprintType)
struct DINKCORE_API FDinkOriginId
{
	GENERATED_BODY()

	/** Valid screen numbers (map.dat holds 768 screens; dink.h: spmap[769], index 0 unused). */
	static constexpr int32 MinScreen = 1;
	static constexpr int32 MaxScreen = 768;

	/** Valid placement indices (the original loops placements 1..99, dink.cpp fix_dead_sprites). */
	static constexpr int32 MinPlacement = 1;
	static constexpr int32 MaxPlacement = 99;

	/** Original screen number, 1..768. 0 means "no origin". */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Origin")
	int32 Screen = 0;

	/** Original placement (editor sprite) index on that screen, 1..99. 0 means "no origin". */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category = "Dink|Origin")
	int32 Placement = 0;

	FDinkOriginId() = default;
	FDinkOriginId(int32 InScreen, int32 InPlacement) : Screen(InScreen), Placement(InPlacement) {}

	/** True when both parts are inside their valid ranges. */
	bool IsValid() const
	{
		return Screen >= MinScreen && Screen <= MaxScreen && Placement >= MinPlacement && Placement <= MaxPlacement;
	}

	/** "S412_P03" for valid IDs, "None" otherwise. */
	FString ToString() const;

	/**
	 * Parses "S412_P03". Case-insensitive, 1-3 digits per part ("S7_P3" is accepted), no other
	 * characters. Fails (and leaves Out untouched) on malformed text or out-of-range numbers.
	 */
	static bool Parse(const FString& Text, FDinkOriginId& Out);

	bool operator==(const FDinkOriginId& Other) const { return Screen == Other.Screen && Placement == Other.Placement; }
	bool operator!=(const FDinkOriginId& Other) const { return !(*this == Other); }

	/** Sort by screen, then placement. */
	bool operator<(const FDinkOriginId& Other) const
	{
		return Screen != Other.Screen ? Screen < Other.Screen : Placement < Other.Placement;
	}

	friend uint32 GetTypeHash(const FDinkOriginId& Id)
	{
		return HashCombine(::GetTypeHash(Id.Screen), ::GetTypeHash(Id.Placement));
	}
};

/** Blueprint access to FDinkOriginId parsing and formatting. */
UCLASS()
class DINKCORE_API UDinkOriginIdLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Formats as "S412_P03" ("None" if invalid). */
	UFUNCTION(BlueprintPure, Category = "Dink|Origin", meta = (DisplayName = "To String (Dink Origin Id)", CompactNodeTitle = "->", BlueprintAutocast))
	static FString OriginIdToString(const FDinkOriginId& Id) { return Id.ToString(); }

	/** Parses "S412_P03"; returns false on malformed or out-of-range input. */
	UFUNCTION(BlueprintCallable, Category = "Dink|Origin")
	static bool ParseOriginId(const FString& Text, FDinkOriginId& OutId) { return FDinkOriginId::Parse(Text, OutId); }

	UFUNCTION(BlueprintPure, Category = "Dink|Origin")
	static bool IsOriginIdValid(const FDinkOriginId& Id) { return Id.IsValid(); }
};
