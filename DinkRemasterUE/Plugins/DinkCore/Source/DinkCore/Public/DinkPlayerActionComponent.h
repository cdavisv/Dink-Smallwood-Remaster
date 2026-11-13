#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DinkPlayerActionComponent.generated.h"

class USkeletalMeshComponent;

/** What the combo layer decided for one attack: pure, so it can be tested without a world. */
struct DINKCORE_API FDinkAttackCombo
{
    /** Seconds after an attack started within which the next one continues the combo. */
    float WindowSeconds = .95f;
    /** Returns the step (0, 1, 2, 0...) of an attack that starts at Now with this weapon family. */
    int32 Advance(double Now, FName Family);
    void Reset() { Step = -1; LastStart = -1.e9; LastFamily = NAME_None; }
    int32 GetStep() const { return Step; }
    static constexpr int32 Steps = 3;
private:
    double LastStart = -1.e9;
    int32 Step = -1;
    FName LastFamily;
};

/**
 * Cosmetic player attacks. The original script sequence and its pending hit stay the only
 * authority on damage and timing: this component only chooses which authored clip shows the
 * attack that gameplay already started (jab, cross, heavier swing when attacks follow each other
 * inside the combo window; the sword's cuts when a sword is armed) and plays it on the body
 * animation instance. It reads nothing back into gameplay.
 */
UCLASS(ClassGroup = Dink, meta = (BlueprintSpawnableComponent))
class DINKCORE_API UDinkPlayerActionComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    bool Configure(USkeletalMeshComponent* Mesh);
    bool PlaySequence(int32 Sequence, FName Weapon = NAME_None);
    void Cancel();
    static bool IsReviewedSequence(int32 Sequence);
    /** Clip base name for a weapon script and combo step; NAME_None when the weapon has no clips. */
    static FName ClipFor(FName Weapon, int32 Step);
    static FName FamilyFor(FName Weapon);
    bool IsActionActive() const;
    int32 GetActiveSequence() const { return IsActionActive() ? ActiveSequence : 0; }
    double GetElapsedSeconds() const;
    int32 GetComboStep() const { return Combo.GetStep(); }
    FName GetActiveClip() const { return IsActionActive() ? ActiveClip : NAME_None; }
private:
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> Target;
    FDinkAttackCombo Combo;
    FName ActiveClip;
    int32 ActiveSequence = 0;
};
