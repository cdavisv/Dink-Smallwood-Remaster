#include "DinkPlayerActionComponent.h"
#include "DinkBodyAnimInstance.h"
#include "DinkCoreModule.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"

namespace
{
TAutoConsoleVariable<float> CVarComboWindow(TEXT("dink.Attack.ComboWindowMs"), 950.f,
    TEXT("An attack that starts within this many ms of the previous attack's start continues the combo (cosmetic)."));
TAutoConsoleVariable<float> CVarAttackBlendIn(TEXT("dink.Attack.BlendInMs"), 70.f,
    TEXT("Blend from the current pose into an attack clip, ms (cosmetic)."));
TAutoConsoleVariable<float> CVarAttackBlendOut(TEXT("dink.Attack.BlendOutMs"), 220.f,
    TEXT("Blend from the end of an attack clip back into locomotion, ms (cosmetic)."));
}

int32 FDinkAttackCombo::Advance(double Now, FName Family)
{
    const bool bContinues = Step >= 0 && Family == LastFamily && Now >= LastStart && Now - LastStart <= WindowSeconds;
    Step = bContinues ? (Step + 1) % Steps : 0;
    LastStart = Now;
    LastFamily = Family;
    return Step;
}

bool UDinkPlayerActionComponent::IsReviewedSequence(int32 Sequence)
{
    return Sequence == 102 || Sequence == 104 || Sequence == 106 || Sequence == 108;
}

FName UDinkPlayerActionComponent::FamilyFor(FName Weapon)
{
    const FString Name = Weapon.ToString().ToLower();
    if (Name.StartsWith(TEXT("item-sw"))) return TEXT("Sword");
    if (Name.StartsWith(TEXT("item-fst")) || Weapon.IsNone()) return TEXT("Fist");
    return NAME_None; // bow, magic, thrown items: no authored clip yet, so nothing plays
}

FName UDinkPlayerActionComponent::ClipFor(FName Weapon, int32 Step)
{
    static const FName Fist[] = {TEXT("Fist_Jab"), TEXT("Fist_Cross"), TEXT("Fist_Swing")};
    static const FName Sword[] = {TEXT("Sword_Slash_1"), TEXT("Sword_Slash_2"), TEXT("Sword_Chop")};
    const FName Family = FamilyFor(Weapon);
    Step = FMath::Clamp(Step, 0, FDinkAttackCombo::Steps - 1);
    if (Family == TEXT("Fist")) return Fist[Step];
    if (Family == TEXT("Sword")) return Sword[Step];
    return NAME_None;
}

bool UDinkPlayerActionComponent::Configure(USkeletalMeshComponent* Mesh)
{
    Cancel();
    const UDinkBodyAnimInstance* Body = Mesh ? Cast<UDinkBodyAnimInstance>(Mesh->GetAnimInstance()) : nullptr;
    if (!Body || !Body->IsConfigured() || !Body->HasClip(TEXT("Fist_Jab"))) { Target = nullptr; return false; }
    Target = Mesh;
    Combo.Reset();
    return true;
}

bool UDinkPlayerActionComponent::PlaySequence(int32 Sequence, FName Weapon)
{
    UDinkBodyAnimInstance* Body = Target ? Cast<UDinkBodyAnimInstance>(Target->GetAnimInstance()) : nullptr;
    if (!Body || !IsReviewedSequence(Sequence) || !GetWorld()) return false;
    const FName Family = FamilyFor(Weapon);
    if (Family.IsNone()) return false;
    Combo.WindowSeconds = CVarComboWindow.GetValueOnGameThread() / 1000.f;
    const int32 Before = Combo.GetStep();
    int32 Step = Combo.Advance(GetWorld()->GetTimeSeconds(), Family);
    FName Clip = ClipFor(Weapon, Step);
    // A weapon whose later combo clips are not imported repeats what it has; a sword without
    // any sword clip falls back to the punches rather than standing still.
    if (!Body->HasClip(Clip)) Clip = ClipFor(Weapon, 0);
    if (!Body->HasClip(Clip)) Clip = ClipFor(NAME_None, Step);
    if (!Body->PlayAction(Clip, false, 1.f, CVarAttackBlendIn.GetValueOnGameThread() / 1000.f, CVarAttackBlendOut.GetValueOnGameThread() / 1000.f))
        return false;
    ActiveClip = Clip;
    ActiveSequence = Sequence;
    UE_LOG(LogDink, Verbose, TEXT("Player cosmetic action seq=%d clip=%s combo %d -> %d"), Sequence, *Clip.ToString(), Before, Step);
    return true;
}

void UDinkPlayerActionComponent::Cancel()
{
    if (UDinkBodyAnimInstance* Body = Target ? Cast<UDinkBodyAnimInstance>(Target->GetAnimInstance()) : nullptr)
        if (Body->GetActionName() == ActiveClip && !ActiveClip.IsNone()) Body->StopActions();
    ActiveClip = NAME_None;
    ActiveSequence = 0;
}

bool UDinkPlayerActionComponent::IsActionActive() const
{
    const UDinkBodyAnimInstance* Body = Target ? Cast<UDinkBodyAnimInstance>(Target->GetAnimInstance()) : nullptr;
    return Body && !ActiveClip.IsNone() && Body->IsActionActive() && Body->GetActionName() == ActiveClip;
}

double UDinkPlayerActionComponent::GetElapsedSeconds() const
{
    const UDinkBodyAnimInstance* Body = Target ? Cast<UDinkBodyAnimInstance>(Target->GetAnimInstance()) : nullptr;
    return IsActionActive() ? Body->GetActionTime() : 0.;
}
