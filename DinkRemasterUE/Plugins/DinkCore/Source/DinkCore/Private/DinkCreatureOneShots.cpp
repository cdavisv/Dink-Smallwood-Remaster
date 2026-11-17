#include "DinkCreatureOneShots.h"
#include "DinkCreatureClassComponent.h"
#include "DinkCreatureSubsystem.h"
#include "DinkCoreModule.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AttributesRuntime.h"
#include "BonePose.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/Material.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/StrongObjectPtr.h"

namespace
{
TAutoConsoleVariable<int32> CVarCreatureOneShots(TEXT("dink.Creature.OneShots"), 1,
	TEXT("Presentation only (owner-reversible decision of 16 Nov 2026: 1997 has no hit or death animation). 1: class-bound creature bodies flinch when a hit costs them life, strike when they attack (the dragon's fire), fidget while they stand and play their death into the corpse (creatures.json one_shots); 0: none of it, the 1997 instant swap to the corpse."));
TAutoConsoleVariable<int32> CVarCreatureDeathClips(TEXT("dink.Creature.DeathClips"), 1,
	TEXT("Presentation only, with dink.Creature.OneShots 1. 1: a killed class body plays its death clip where it stood and its corpse mesh is shown when the clip ends (the corpse, its blood and the kill's timing are the simulation's as before); 0: the body goes at once, as in 1997."));

struct FOneShotTable
{
	TMap<FName, FDinkCreatureOneShotRow> Rows;
	TMap<FString, TStrongObjectPtr<UAnimSequence>> Clips;
	bool bLoaded = false;
};
FOneShotTable& Table()
{
	static FOneShotTable T;
	return T;
}

bool ReadSpec(const TSharedPtr<FJsonObject>& O, FDinkCreatureOneShotSpec& Out)
{
	if (!O || !O->TryGetStringField(TEXT("clip"), Out.Clip)) return false;
	double N = 0;
	if (O->TryGetNumberField(TEXT("blend_in_s"), N)) Out.BlendInS = FMath::Clamp(float(N), .01f, 1.f);
	if (O->TryGetNumberField(TEXT("blend_out_s"), N)) Out.BlendOutS = FMath::Clamp(float(N), .01f, 1.f);
	if (O->TryGetNumberField(TEXT("rate"), N)) Out.Rate = FMath::Clamp(float(N), .1f, 4.f);
	FString Mask;
	if (O->TryGetStringField(TEXT("mask"), Mask)) Out.MaskRoot = FName(*Mask);
	const TArray<TSharedPtr<FJsonValue>>* Align = nullptr;
	if (O->TryGetArrayField(TEXT("align_cm"), Align) && Align->Num() == 3)
		Out.AlignCm = FVector((*Align)[0]->AsNumber(), (*Align)[1]->AsNumber(), (*Align)[2]->AsNumber());
	O->TryGetBoolField(TEXT("material_from_corpse"), Out.bMaterialFromCorpse);
	return true;
}
}

bool DinkCreatureOneShots::ParseRow(const FJsonObject& Row, FDinkCreatureOneShotRow& Out)
{
	const TSharedPtr<FJsonObject>* O = nullptr;
	if (!Row.TryGetObjectField(TEXT("one_shots"), O) || !O || !O->IsValid()) return false;
	const TSharedPtr<FJsonObject>* S = nullptr;
	if ((*O)->TryGetObjectField(TEXT("hit"), S)) ReadSpec(*S, Out.Hit);
	if ((*O)->TryGetObjectField(TEXT("death"), S)) ReadSpec(*S, Out.Death);
	if ((*O)->TryGetObjectField(TEXT("burst_death"), S)) ReadSpec(*S, Out.BurstDeath);
	if ((*O)->TryGetObjectField(TEXT("attack"), S) && ReadSpec(*S, Out.Attack))
	{
		FString Trigger;
		if ((*S)->TryGetStringField(TEXT("trigger"), Trigger)) Out.AttackTrigger = FName(*Trigger);
		double N = 0;
		if ((*S)->TryGetNumberField(TEXT("radius_cm"), N)) Out.AttackRadiusCm = FMath::Clamp(float(N), 50.f, 3000.f);
	}
	if ((*O)->TryGetObjectField(TEXT("idle"), S))
	{
		const TArray<TSharedPtr<FJsonValue>>* Clips = nullptr;
		if ((*S)->TryGetArrayField(TEXT("clips"), Clips))
			for (const TSharedPtr<FJsonValue>& V : *Clips)
			{
				FDinkCreatureOneShotSpec Spec;
				Spec.Clip = V->AsString();
				Spec.BlendInS = .2f; Spec.BlendOutS = .3f;
				if (!Spec.Clip.IsEmpty()) Out.Idle.Add(Spec);
			}
		const TArray<TSharedPtr<FJsonValue>>* Every = nullptr;
		if ((*S)->TryGetArrayField(TEXT("every_s"), Every) && Every->Num() == 2)
		{
			Out.IdleEveryMinS = FMath::Max(1.f, float((*Every)[0]->AsNumber()));
			Out.IdleEveryMaxS = FMath::Max(Out.IdleEveryMinS, float((*Every)[1]->AsNumber()));
		}
	}
	return true;
}

void DinkCreatureOneShots::Reload()
{
	FOneShotTable& T = Table();
	T.Rows.Reset();
	T.bLoaded = true;
	FString Text;
	TSharedPtr<FJsonObject> Root;
	const TArray<TSharedPtr<FJsonValue>>* Classes = nullptr;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/creatures.json"))) ||
		!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) || !Root || !Root->TryGetArrayField(TEXT("classes"), Classes)) return;
	for (const TSharedPtr<FJsonValue>& V : *Classes)
	{
		const TSharedPtr<FJsonObject>* Row = nullptr;
		FString Id;
		if (!V->TryGetObject(Row) || !Row || !(*Row)->TryGetStringField(TEXT("class"), Id)) continue;
		FDinkCreatureOneShotRow Shots;
		if (ParseRow(**Row, Shots)) T.Rows.Add(FName(*Id), Shots);
	}
}

const FDinkCreatureOneShotRow* DinkCreatureOneShots::Find(FName ClassId)
{
	FOneShotTable& T = Table();
	if (!T.bLoaded) Reload();
	return T.Rows.Find(ClassId);
}

UAnimSequence* DinkCreatureOneShots::Load(const FDinkCreatureOneShotSpec& Spec)
{
	if (!Spec.IsSet()) return nullptr;
	FOneShotTable& T = Table();
	if (const TStrongObjectPtr<UAnimSequence>* Known = T.Clips.Find(Spec.Clip)) return Known->Get();
	UAnimSequence* Clip = FPackageName::DoesPackageExist(FPackageName::ObjectPathToPackageName(Spec.Clip)) ? LoadObject<UAnimSequence>(nullptr, *Spec.Clip) : nullptr;
	if (!Clip) UE_LOG(LogDink, Warning, TEXT("Creature one-shot clip missing: %s"), *Spec.Clip);
	T.Clips.Add(Spec.Clip, TStrongObjectPtr<UAnimSequence>(Clip));
	return Clip;
}

float DinkCreatureOneShots::Envelope(float Time, float Length, float BlendIn, float BlendOut)
{
	const float In = FMath::SmoothStep(0.f, 1.f, Time / FMath::Max(BlendIn, .001f));
	const float Out = FMath::SmoothStep(0.f, 1.f, (Length - Time) / FMath::Max(BlendOut, .001f));
	return FMath::Clamp(FMath::Min(In, Out), 0.f, 1.f);
}

void DinkCreatureOneShots::ApplyOverlays(FPoseContext& Output, TConstArrayView<FDinkCreatureOverlay> Overlays)
{
	FCompactPose& Out = Output.Pose;
	const int32 NumBones = Out.GetNumBones();
	const FBoneContainer& Bones = Out.GetBoneContainer();
	const FReferenceSkeleton& Reference = Bones.GetReferenceSkeleton();
	for (const FDinkCreatureOverlay& Overlay : Overlays)
	{
		if (!Overlay.Sequence || Overlay.Weight <= .001f) continue;
		FCompactPose Pose;
		Pose.SetBoneContainer(&Bones);
		FBlendedCurve Curve;
		Curve.InitFrom(Output.Curve);
		UE::Anim::FStackAttributeContainer Attributes;
		FAnimationPoseData Data(Pose, Curve, Attributes);
		Overlay.Sequence->GetAnimationPose(Data, FAnimExtractContext(double(Overlay.Time), false));
		// The bones from the mask root down (all of them without a mask, or when the rig has no such bone).
		int32 Root = INDEX_NONE;
		if (!Overlay.MaskRoot.IsNone())
			for (FCompactPoseBoneIndex B(0); B.GetInt() < NumBones; ++B)
				if (Reference.GetBoneName(Bones.MakeMeshPoseIndex(B).GetInt()) == Overlay.MaskRoot) { Root = B.GetInt(); break; }
		for (FCompactPoseBoneIndex B(0); B.GetInt() < NumBones; ++B)
		{
			bool bIn = Root == INDEX_NONE;
			for (FCompactPoseBoneIndex P = B; !bIn && P.GetInt() != INDEX_NONE; P = Out.GetParentBoneIndex(P)) bIn = P.GetInt() == Root;
			// The root bone never moves: the body's place and facing belong to the sprite.
			if (!bIn || B.GetInt() == 0) continue;
			FTransform Base = Out[B];
			Out[B].Blend(Base, Pose[B], Overlay.Weight);
		}
	}
}

bool FDinkCreatureOneShotPlayer::Play(FName ClassId, EDinkCreatureOneShot Kind)
{
	if (CVarCreatureOneShots.GetValueOnGameThread() == 0) return false;
	const FDinkCreatureOneShotRow* Row = DinkCreatureOneShots::Find(ClassId);
	if (!Row) return false;
	FShot Shot;
	Shot.Kind = Kind;
	if (Kind == EDinkCreatureOneShot::Hit) Shot.Spec = Row->Hit;
	else if (Kind == EDinkCreatureOneShot::Attack) Shot.Spec = Row->Attack;
	else if (Row->Idle.Num() > 0) Shot.Spec = Row->Idle[Random.RandHelper(Row->Idle.Num())];
	Shot.Clip = DinkCreatureOneShots::Load(Shot.Spec);
	if (!Shot.Clip) return false;
	// One shot of a kind at a time: a second hit starts the flinch again; a hit or an attack cuts an idle fidget short.
	Active.RemoveAll([Kind](const FShot& S) { return S.Kind == Kind || S.Kind == EDinkCreatureOneShot::Idle; });
	if (Active.Num() >= 2) Active.RemoveAt(0);
	Active.Add(Shot);
	++Played;
	return true;
}

void FDinkCreatureOneShotPlayer::Step(FName ClassId, float DeltaTime, bool bStanding, TArray<FDinkCreatureOverlay, TInlineAllocator<2>>& Out)
{
	Out.Reset();
	if (CVarCreatureOneShots.GetValueOnGameThread() == 0) { Active.Reset(); return; }
	const FDinkCreatureOneShotRow* Row = DinkCreatureOneShots::Find(ClassId);
	// Fidgets: now and then while it stands, never while something else plays.
	StandTime = bStanding ? StandTime + DeltaTime : 0.f;
	if (Row && Row->Idle.Num() > 0)
	{
		if (NextIdle < 0.f) NextIdle = Random.FRandRange(Row->IdleEveryMinS, Row->IdleEveryMaxS);
		if (StandTime >= NextIdle && Active.IsEmpty())
		{
			Play(ClassId, EDinkCreatureOneShot::Idle);
			StandTime = 0.f;
			NextIdle = Random.FRandRange(Row->IdleEveryMinS, Row->IdleEveryMaxS);
		}
	}
	for (int32 i = Active.Num() - 1; i >= 0; --i)
	{
		FShot& S = Active[i];
		const float Length = FMath::Max(S.Clip->GetPlayLength(), .01f);
		S.Time += DeltaTime * S.Spec.Rate;
		// A fidget is let go the moment the body walks off.
		if (S.Time >= Length || (S.Kind == EDinkCreatureOneShot::Idle && !bStanding)) { Active.RemoveAt(i); continue; }
		Out.Add({S.Clip, S.Time, DinkCreatureOneShots::Envelope(S.Time, Length, S.Spec.BlendInS, S.Spec.BlendOutS), S.Spec.MaskRoot});
	}
}

// ---------------------------------------------------------------------------------------------
// Deaths

bool UDinkCreatureDeathSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{
	return Type == EWorldType::Game || Type == EWorldType::PIE;
}

int32 UDinkCreatureDeathSubsystem::CurrentEpoch() const
{
	const UWorld* World = GetWorld();
	const UDinkCreatureSubsystem* Creatures = World ? World->GetSubsystem<UDinkCreatureSubsystem>() : nullptr;
	return Creatures ? Creatures->GetClearCount() : 0;
}

USkeletalMeshComponent* UDinkCreatureDeathSubsystem::SpawnDying(const UDinkCreatureClassComponent& Body, const FDinkCreatureOneShotSpec& Spec, UStaticMeshComponent* BloodFrom)
{
	UWorld* World = GetWorld();
	if (!World || !Body.GetSkeletalMeshAsset()) return nullptr;
	if (!Holder)
	{
		FActorSpawnParameters Params;
		Params.ObjectFlags |= RF_Transient;
		Holder = World->SpawnActor<AActor>(Params);
		if (!Holder) return nullptr;
		USceneComponent* Root = NewObject<USceneComponent>(Holder);
		Holder->SetRootComponent(Root);
		Root->RegisterComponent();
	}
	// A copy of the body as it stands, from its last pose into the death clip.
	USkeletalMeshComponent* Dying = NewObject<USkeletalMeshComponent>(Holder);
	Dying->SetMobility(EComponentMobility::Movable);
	Dying->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Dying->SetGenerateOverlapEvents(false);
	Dying->SetCanEverAffectNavigation(false);
	Dying->bAllowClothActors = false;
	Dying->SetUsingAbsoluteLocation(true);
	Dying->SetUsingAbsoluteRotation(true);
	Dying->SetUsingAbsoluteScale(true);
	Dying->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
	Dying->SetSkeletalMeshAsset(Body.GetSkeletalMeshAsset());
	// The blood of the remains is on the body from the kill frame on, when the corpse shares its texture layout.
	// Only a material compiled for skinned meshes can be worn by the dying body: any other draws as the engine's grey default
	// (and in a cooked game can never be compiled for it), so the body keeps its own skin then (seen 16 Nov: grey boncas).
	bool bBloody = Spec.bMaterialFromCorpse && BloodFrom && BloodFrom->GetNumMaterials() >= 1;
	for (int32 Slot = 0; bBloody && Slot < BloodFrom->GetNumMaterials(); ++Slot)
	{
		const UMaterialInterface* M = BloodFrom->GetMaterial(Slot);
		const UMaterial* Base = M ? M->GetMaterial_Concurrent() : nullptr;
		if (!Base || !Base->GetUsageByFlag(MATUSAGE_SkeletalMesh)) bBloody = false;
	}
	for (int32 Slot = 0; Slot < Body.GetNumMaterials(); ++Slot)
		Dying->SetMaterial(Slot, bBloody ? BloodFrom->GetMaterial(FMath::Min(Slot, BloodFrom->GetNumMaterials() - 1)) : Body.GetMaterial(Slot));
	Dying->SetupAttachment(Holder->GetRootComponent());
	Dying->RegisterComponent();
	Dying->SetWorldTransform(Body.GetComponentTransform());
	Dying->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	Dying->SetAnimInstanceClass(UDinkCreatureAnimInstance::StaticClass());
	Bodies.Add(Dying);
	return Dying;
}

bool UDinkCreatureDeathSubsystem::BeginDeath(const UDinkCreatureClassComponent& Body, UStaticMeshComponent* Corpse)
{
	if (CVarCreatureOneShots.GetValueOnGameThread() == 0 || CVarCreatureDeathClips.GetValueOnGameThread() == 0 || !Corpse) return false;
	const FDinkCreatureOneShotRow* Row = DinkCreatureOneShots::Find(Body.GetClassId());
	UAnimSequence* Clip = Row ? DinkCreatureOneShots::Load(Row->Death) : nullptr;
	if (!Clip) return false;
	USkeletalMeshComponent* Dying = SpawnDying(Body, Row->Death, Corpse);
	if (!Dying) return false;
	FDeath Death;
	Death.Body = Dying;
	Death.Corpse = Corpse;
	Death.Clip = Clip;
	Death.Rate = Row->Death.Rate;
	Death.BlendIn = Row->Death.BlendInS;
	Death.AlignCm = Row->Death.AlignCm;
	for (const FDinkCreaturePoseLayer& Layer : Body.GetLayers()) Death.From.Add({Layer.Sequence, Layer.Time, Layer.Weight});
	// The corpse (and its blood pool, a separate decal) is left now, as in 1997; its mesh is drawn when the clip ends.
	Corpse->SetVisibility(false);
	Deaths.Add(MoveTemp(Death));
	++Started;
	StepDeaths(0.f);
	return true;
}

bool UDinkCreatureDeathSubsystem::BeginBurstDeath(const UDinkCreatureClassComponent& Body, TFunction<void(const FVector& Ground)> AtEnd)
{
	if (CVarCreatureOneShots.GetValueOnGameThread() == 0 || CVarCreatureDeathClips.GetValueOnGameThread() == 0 || !AtEnd) return false;
	const FDinkCreatureOneShotRow* Row = DinkCreatureOneShots::Find(Body.GetClassId());
	UAnimSequence* Clip = Row ? DinkCreatureOneShots::Load(Row->BurstDeath) : nullptr;
	if (!Clip) return false;
	USkeletalMeshComponent* Dying = SpawnDying(Body, Row->BurstDeath, nullptr);
	if (!Dying) return false;
	FDeath Death;
	Death.Body = Dying;
	Death.Clip = Clip;
	Death.Rate = Row->BurstDeath.Rate;
	Death.BlendIn = Row->BurstDeath.BlendInS;
	Death.bNoCorpse = true;
	Death.AtEnd = MoveTemp(AtEnd);
	Death.Ground = Body.GetShownLocation();
	Death.Epoch = CurrentEpoch();
	for (const FDinkCreaturePoseLayer& Layer : Body.GetLayers()) Death.From.Add({Layer.Sequence, Layer.Time, Layer.Weight});
	Deaths.Add(MoveTemp(Death));
	++Started;
	StepDeaths(0.f);
	return true;
}

bool UDinkCreatureDeathSubsystem::ShowDeath(const UDinkCreatureClassComponent& Body, bool bBurst, const FVector& Offset)
{
	const FDinkCreatureOneShotRow* Row = DinkCreatureOneShots::Find(Body.GetClassId());
	if (!Row) return false;
	const FDinkCreatureOneShotSpec& Spec = bBurst ? Row->BurstDeath : Row->Death;
	UAnimSequence* Clip = DinkCreatureOneShots::Load(Spec);
	USkeletalMeshComponent* Dying = Clip ? SpawnDying(Body, Spec, nullptr) : nullptr;
	if (!Dying) return false;
	Dying->SetWorldLocation(Dying->GetComponentLocation() + Offset);
	FDeath Death;
	Death.Body = Dying;
	Death.Clip = Clip;
	Death.Rate = Spec.Rate;
	Death.BlendIn = Spec.BlendInS;
	Death.bNoCorpse = true;
	Death.Epoch = CurrentEpoch();
	for (const FDinkCreaturePoseLayer& Layer : Body.GetLayers()) Death.From.Add({Layer.Sequence, Layer.Time, Layer.Weight});
	Deaths.Add(MoveTemp(Death));
	StepDeaths(0.f);
	return true;
}

void UDinkCreatureDeathSubsystem::Finish(int32 Index, bool bComplete)
{
	FDeath& D = Deaths[Index];
	if (bComplete && D.Corpse.IsValid())
	{
		// The corpse takes the place of the clip's last pose (it was recentred on its pool when it was made).
		if (!D.AlignCm.IsNearlyZero())
		{
			const FTransform T = D.Corpse->GetComponentTransform();
			// On the ground plane only: the corpse stays set on the ground whatever height the clip ends at.
			FVector Shift = T.GetRotation().RotateVector(D.AlignCm * T.GetScale3D());
			Shift.Z = 0.0;
			D.Corpse->SetWorldLocation(T.GetLocation() + Shift);
		}
		D.Corpse->SetVisibility(true);
	}
	// A burst death: the 1997 burst where the body lies, as the body goes.
	TFunction<void(const FVector&)> AtEnd = bComplete ? MoveTemp(D.AtEnd) : TFunction<void(const FVector&)>();
	const FVector Ground = D.Ground;
	if (USkeletalMeshComponent* Body = D.Body.Get())
	{
		Bodies.Remove(Body);
		Body->DestroyComponent();
	}
	Deaths.RemoveAt(Index);
	if (AtEnd) AtEnd(Ground);
}

void UDinkCreatureDeathSubsystem::StepDeaths(float DeltaTime)
{
	const int32 Epoch = CurrentEpoch();
	for (int32 i = Deaths.Num() - 1; i >= 0; --i)
	{
		FDeath& D = Deaths[i];
		// The screen was left or a save loaded: the corpse is gone, and the dying body with it (a burst is not made).
		if ((!D.bNoCorpse && !D.Corpse.IsValid()) || (D.bNoCorpse && D.Epoch != Epoch) || !D.Body.IsValid()) { Finish(i, false); continue; }
		const float Length = FMath::Max(D.Clip->GetPlayLength(), .01f);
		D.Time += DeltaTime * D.Rate;
		if (D.Time >= Length) { Finish(i, true); continue; }
		const float E = FMath::SmoothStep(0.f, 1.f, D.Time / FMath::Max(D.BlendIn, .001f));
		TArray<FDinkCreaturePoseLayer, TInlineAllocator<8>> Layers;
		for (const FDinkCreatureLayerCopy& L : D.From) if (L.Sequence && L.Weight * (1.f - E) > .001f) Layers.Add({L.Sequence, L.Time, L.Weight * (1.f - E)});
		Layers.Add({D.Clip, D.Time, E});
		if (UDinkCreatureAnimInstance* Animation = Cast<UDinkCreatureAnimInstance>(D.Body->GetAnimInstance())) Animation->SetLayers(Layers);
	}
}

void UDinkCreatureDeathSubsystem::Deinitialize()
{
	// The world goes: corpses are shown (as before), no burst is made any more.
	while (Deaths.Num() > 0) { Deaths.Last().AtEnd = nullptr; Finish(Deaths.Num() - 1, true); }
	Super::Deinitialize();
}

namespace
{
FAutoConsoleCommandWithWorldAndArgs CreatureShowDeath(TEXT("dink.Creature.ShowDeath"),
	TEXT("dink.Creature.ShowDeath <class> [burst]: review only. A copy of the first shown body of that class plays its death clip (burst: its burst_death clip) 150 cm to its right; the creature, its sprite and the simulation are untouched and nothing follows the clip."),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
{
	if (!World || Args.Num() < 1) return;
	UDinkCreatureDeathSubsystem* Deaths = World->GetSubsystem<UDinkCreatureDeathSubsystem>();
	const FName Class(*Args[0]);
	const bool bBurst = Args.Num() > 1 && Args[1] == TEXT("burst");
	for (TActorIterator<AActor> It(World); It && Deaths; ++It)
	{
		const UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(*It);
		if (!Body || It->IsHidden() || Body->GetClassId() != Class) continue;
		const bool bOk = Deaths->ShowDeath(*Body, bBurst, Body->GetRightVector() * 150.f);
		UE_LOG(LogDink, Display, TEXT("dink.Creature.ShowDeath %s %s: %s"), *Class.ToString(), bBurst ? TEXT("burst") : TEXT("death"), bOk ? TEXT("playing") : TEXT("no clip"));
		return;
	}
	UE_LOG(LogDink, Display, TEXT("dink.Creature.ShowDeath %s: no shown body of that class"), *Class.ToString());
}));
}
