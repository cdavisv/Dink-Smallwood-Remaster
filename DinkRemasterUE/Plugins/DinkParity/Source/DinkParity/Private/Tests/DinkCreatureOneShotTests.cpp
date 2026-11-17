// Dink.Creature.OneShots: event one-shots of class-bound creature bodies (DinkCreatureOneShots.h) and the death handover to
// the corpse. Presentation only: the simulation and the corpse's timing are checked unchanged.
#include "DinkTestHelpers.h"
#include "DinkCreatureClass.h"
#include "DinkCreatureClassComponent.h"
#include "DinkCreatureEvents.h"
#include "DinkCreatureOneShots.h"
#include "DinkCreaturePresenter.h"
#include "DinkCreatureSubsystem.h"
#include "DinkDirector.h"
#include "DinkFactSubsystem.h"
#include "DinkGameplay.h"
#include "DinkOriginComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkPlaceholderActor.h"
#include "Greybox/DinkScreenVolume.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureOneShotRowsTest, "Dink.Creature.OneShots.Rows", DINK_TEST_FLAGS)
bool FDinkCreatureOneShotRowsTest::RunTest(const FString&)
{
	DinkCreatureOneShots::Reload();
	int32 Clips = 0, Missing = 0;
	auto Check = [&](FName Class, const FDinkCreatureOneShotSpec& Spec, const TCHAR* What)
	{
		if (!Spec.IsSet()) return;
		++Clips;
		FString Package = Spec.Clip;
		Package.Split(TEXT("."), &Package, nullptr);
		if (!FPackageName::DoesPackageExist(Package)) { ++Missing; AddWarning(FString::Printf(TEXT("%s %s: %s is not imported in this checkout"), *Class.ToString(), What, *Spec.Clip)); }
	};
	for (const FName Class : {FName(TEXT("duck")), FName(TEXT("slime_blue")), FName(TEXT("slime_green")), FName(TEXT("slime_red")), FName(TEXT("bonca_gray")), FName(TEXT("bonca_brown")),
		FName(TEXT("bonca_purple")), FName(TEXT("slayer")), FName(TEXT("stone_giant")), FName(TEXT("dragon")),
		FName(TEXT("goblin_hammer")), FName(TEXT("goblin_horned")), FName(TEXT("goblin_soldier"))})
	{
		const FDinkCreatureOneShotRow* Row = DinkCreatureOneShots::Find(Class);
		if (!TestNotNull(FString::Printf(TEXT("%s has one-shots"), *Class.ToString()), Row)) continue;
		Check(Class, Row->Hit, TEXT("hit")); Check(Class, Row->Attack, TEXT("attack")); Check(Class, Row->Death, TEXT("death")); Check(Class, Row->BurstDeath, TEXT("burst_death"));
		TestTrue(FString::Printf(TEXT("%s: its death clip plays (owner decision 16 Nov 2026)"), *Class.ToString()), Row->Death.IsSet());
		for (const FDinkCreatureOneShotSpec& Idle : Row->Idle) Check(Class, Idle, TEXT("idle"));
	}
	TestNull(TEXT("the pillbug has none (no clip exists)"), DinkCreatureOneShots::Find(TEXT("pillbug")));
	const FDinkCreatureOneShotRow* Dragon = DinkCreatureOneShots::Find(TEXT("dragon"));
	if (Dragon)
	{
		TestEqual(TEXT("the dragon strikes when its fire appears"), Dragon->AttackTrigger, FName(TEXT("missile")));
		TestEqual(TEXT("over its walk: chest, neck and head only"), Dragon->Attack.MaskRoot, FName(TEXT("spine_02")));
	}
	if (const FDinkCreatureOneShotRow* Slime = DinkCreatureOneShots::Find(TEXT("slime_red"))) TestEqual(TEXT("a slime bites when Dink loses life beside it"), Slime->AttackTrigger, FName(TEXT("touch")));
	if (const FDinkCreatureOneShotRow* Duck = DinkCreatureOneShots::Find(TEXT("duck")))
	{
		TestEqual(TEXT("the duck pecks and quacks while it stands"), Duck->Idle.Num(), 2);
		// Owner decision 16 Nov 2026: no creature death or hit clip is withheld.
		TestTrue(TEXT("the duck flinches as its head goes"), Duck->Hit.IsSet());
		TestTrue(TEXT("the headless duck falls before its burst"), Duck->BurstDeath.IsSet());
		TestTrue(TEXT("the duck's own death clip is named"), Duck->Death.IsSet());
	}
	AddInfo(FString::Printf(TEXT("ONE-SHOT ROWS: %d clips named, %d not imported here"), Clips, Missing));
	// Envelope: eased in, held, eased out, zero at both ends.
	TestTrue(TEXT("envelope starts at 0"), DinkCreatureOneShots::Envelope(0.f, 1.f, .1f, .2f) < .001f);
	TestTrue(TEXT("envelope holds 1"), FMath::IsNearlyEqual(DinkCreatureOneShots::Envelope(.5f, 1.f, .1f, .2f), 1.f));
	TestTrue(TEXT("envelope ends at 0"), DinkCreatureOneShots::Envelope(1.f, 1.f, .1f, .2f) < .001f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureOneShotPlayerTest, "Dink.Creature.OneShots.Player", DINK_TEST_FLAGS)
bool FDinkCreatureOneShotPlayerTest::RunTest(const FString&)
{
	DinkCreatureOneShots::Reload();
	const FDinkCreatureOneShotRow* Bonca = DinkCreatureOneShots::Find(TEXT("bonca_gray"));
	if (!Bonca || !DinkCreatureOneShots::Load(Bonca->Hit)) { AddWarning(TEXT("skipped: the bonca's hit clip is not imported")); return true; }
	const float Length = DinkCreatureOneShots::Load(Bonca->Hit)->GetPlayLength();
	FDinkCreatureOneShotPlayer Player;
	TArray<FDinkCreatureOverlay, TInlineAllocator<2>> Out;
	TestTrue(TEXT("a hit plays"), Player.Play(TEXT("bonca_gray"), EDinkCreatureOneShot::Hit));
	float Peak = 0.f, First = -1.f;
	int32 Frames = 0;
	for (float T = 0.f; T < Length + .5f; T += 1.f / 60.f)
	{
		Player.Step(TEXT("bonca_gray"), 1.f / 60.f, false, Out);
		if (Out.Num()) { Peak = FMath::Max(Peak, Out[0].Weight); if (First < 0.f) First = Out[0].Weight; ++Frames; }
	}
	AddInfo(FString::Printf(TEXT("HIT: clip %.2f s, shown %d frames, first weight %.3f, peak %.3f"), Length, Frames, First, Peak));
	TestTrue(TEXT("it eases in (no pop on its first frame)"), First < .5f);
	TestTrue(TEXT("it reaches the full pose"), Peak > .95f);
	TestFalse(TEXT("it ends by itself"), Player.IsPlaying());
	TestFalse(TEXT("a class without that kind plays nothing"), Player.Play(TEXT("pillbug"), EDinkCreatureOneShot::Hit));
	// The duck fidgets while it stands, and stops as it walks off.
	FDinkCreatureOneShotPlayer Duck;
	int32 Fidget = 0;
	for (int32 I = 0; I < 60 * 25; ++I)
	{
		Duck.Step(TEXT("duck"), 1.f / 60.f, true, Out);
		Fidget += Out.Num() > 0;
	}
	AddInfo(FString::Printf(TEXT("DUCK: %d fidgets started in 25 s of standing, %d frames shown"), Duck.GetPlayed(), Fidget));
	if (DinkCreatureOneShots::Find(TEXT("duck")) && DinkCreatureOneShots::Load(DinkCreatureOneShots::Find(TEXT("duck"))->Idle[0]))
	{
		TestTrue(TEXT("a standing duck pecks or quacks now and then (every 4 to 10 s)"), Duck.GetPlayed() >= 2 && Duck.GetPlayed() <= 7);
		Duck.Step(TEXT("duck"), 1.f / 60.f, false, Out);
		TestEqual(TEXT("walking off ends a fidget at once"), Out.Num(), 0);
	}
	// Switched off: nothing.
	IConsoleVariable* Off = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Creature.OneShots"));
	Off->Set(0, ECVF_SetByCode);
	ON_SCOPE_EXIT { Off->Set(1, ECVF_SetByCode); };
	TestFalse(TEXT("dink.Creature.OneShots 0 plays nothing"), Player.Play(TEXT("bonca_gray"), EDinkCreatureOneShot::Hit));
	return true;
}

namespace DinkCreatureOneShotTest
{
	/** A 600 x 400 px screen with three grey boncas running en-bong (brain 9, 40 hit points, base_death 550). */
	struct FBoncaScene
	{
		UGameInstance* GI = nullptr;
		UWorld* World = nullptr;
		UDinkStorySubsystem* Story = nullptr;
		UDinkDirector* D = nullptr;
		UDinkGameplay* Game = nullptr;
		UDinkCreatureSubsystem* Creatures = nullptr;
		UDinkCreaturePresenter* Presenter = nullptr;
		UDinkCreatureDeathSubsystem* Deaths = nullptr;
		ADinkScreenVolume* Room = nullptr;
		TArray<ADinkPlaceholderActor*> Boncas;
		TArray<int32> Handles;
		static constexpr int32 Screen = 999;

		bool Start(UStaticMesh* Plane, FName Class = TEXT("bonca_gray"), int32 Sequence = 601, const TCHAR* Script = TEXT("en-bong"), int32 Count = 3)
		{
			GI = NewObject<UGameInstance>(GEngine);
			GI->InitializeStandalone();
			World = GI->GetWorld();
			Story = GI->GetSubsystem<UDinkStorySubsystem>();
			Story->bRunScreenScripts = false; Story->bNewGamePending = false; Story->bInstantMode = true;
			Story->GetFacts()->SetFact(TEXT("life"), 100); Story->GetFacts()->SetFact(TEXT("lifemax"), 100);
			Story->GetFacts()->SetFact(TEXT("update_status"), 0); Story->GetFacts()->SetFact(TEXT("player_map"), Screen);
			D = Story->GetDirector();
			Game = Story->GetGameplay();
			Game->Adaptation.bEnabled = false;
			Game->SetRandomSeed(1997);
			Room = World->SpawnActor<ADinkScreenVolume>();
			Room->ScreenNumber = Screen;
			Room->Corners.NW = FVector2D(0, 0); Room->Corners.NE = FVector2D(15, 0); Room->Corners.SW = FVector2D(0, 10); Room->Corners.SE = FVector2D(15, 10);
			World->GetSubsystem<UDinkGreyboxSubsystem>()->RegisterScreen(Room);
			AActor* Dink = World->SpawnActor<AActor>();
			USceneComponent* Root = NewObject<USceneComponent>(Dink);
			Dink->SetRootComponent(Root); Root->RegisterComponent();
			Dink->SetActorLocation(Room->MapPixelToWorld(560, 380));
			D->GetDink().Actor = Dink; D->GetDink().Screen = Screen; D->GetDink().X = 560; D->GetDink().Y = 380;
			const FVector2D Starts[] = { FVector2D(126, 108), FVector2D(363, 186), FVector2D(233, 300) };
			for (int32 Index = 0; Index < Count; ++Index)
			{
				ADinkPlaceholderActor* Bonca = World->SpawnActor<ADinkPlaceholderActor>();
				Bonca->Origin->OriginId = FDinkOriginId(Screen, 4 + Index);
				Bonca->Origin->ClassId = Class;
				Bonca->Origin->Sequence = Sequence;
				Bonca->Origin->Frame = 1;
				Bonca->Origin->ScriptName = Script ? FName(Script) : NAME_None;
				Bonca->ScreenNumber = Screen;
				Bonca->PlacementKind = TEXT("live");
				Bonca->Card->SetStaticMesh(Plane);
				Bonca->GetRootComponent()->SetMobility(EComponentMobility::Movable);
				Boncas.Add(Bonca);
				const int32 Handle = D->HandleForActor(Bonca);
				Handles.Add(Handle);
				FDinkSprite* Sprite = D->FindSprite(Handle);
				Sprite->Screen = Screen; Sprite->X = Starts[Index].X; Sprite->Y = Starts[Index].Y;
				D->SyncActorToSprite(*Sprite);
				if (Script)
				{
					Story->StartProcedure(Script, TEXT("main"), Handle);
					Story->RunUntilIdle();
				}
			}
			Creatures = World->GetSubsystem<UDinkCreatureSubsystem>();
			Presenter = World->GetSubsystem<UDinkCreaturePresenter>();
			Deaths = World->GetSubsystem<UDinkCreatureDeathSubsystem>();
			Creatures->OnWorldBeginPlay(*World);
			FAssetCompilingManager::Get().FinishAllCompilation();
			return Presenter && Deaths;
		}
		void Step(float Dt)
		{
			Story->Tick(Dt);
			Presenter->Present();
			for (ADinkPlaceholderActor* Bonca : Boncas)
				if (UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(Bonca)) Body->TickComponent(Dt, LEVELTICK_All, nullptr);
			Creatures->StepGore(Dt);
			Deaths->StepDeaths(Dt);
		}
		void Kill(int32 Index, int32 Damage)
		{
			Game->HurtThing(Handles[Index], Damage);
			Game->ProcessDamage();
			Story->RunUntilIdle();
		}
		void Stop()
		{
			World->GetSubsystem<UDinkGreyboxSubsystem>()->UnregisterScreen(Room);
			GI->Shutdown();
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureOneShotSceneTest, "Dink.Creature.OneShots.HitDeathAndCorpseHandover", DINK_TEST_FLAGS)
bool FDinkCreatureOneShotSceneTest::RunTest(const FString&)
{
	using namespace DinkCreatureOneShotTest;
	DinkCreatureOneShots::Reload();
	const FDinkCreatureOneShotRow* Row = DinkCreatureOneShots::Find(TEXT("bonca_gray"));
	UAnimSequence* DeathClip = Row ? DinkCreatureOneShots::Load(Row->Death) : nullptr;
	if (!DeathClip || !LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Photoreal/Creatures/Bonca/SK_Bonca_PR.SK_Bonca_PR"), nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		AddWarning(TEXT("skipped: the photoreal bonca or its clips are not imported in this checkout"));
		return true;
	}
	IConsoleVariable* Art = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.CreatureClassArt"));
	const int32 ArtBefore = Art->GetInt();
	Art->Set(2, ECVF_SetByCode);
	ON_SCOPE_EXIT { Art->Set(ArtBefore, ECVF_SetByCode); };
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	FBoncaScene Scene;
	if (!TestTrue(TEXT("scene starts"), Scene.Start(Plane))) return false;
	ON_SCOPE_EXIT { Scene.Stop(); };
	for (int32 I = 0; I < 30; ++I) Scene.Step(1.f / 60.f);
	UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(Scene.Boncas[0]);
	if (!TestNotNull(TEXT("the bonca has its body"), Body)) return false;
	// A hit that costs life: the body flinches; the sprite is the simulation's as before.
	const int32 Before = Scene.D->FindSprite(Scene.Handles[0])->GetProp(TEXT("hitpoints"));
	Scene.Kill(0, 5);
	Scene.Step(1.f / 60.f);
	const int32 After = Scene.D->FindSprite(Scene.Handles[0])->GetProp(TEXT("hitpoints"));
	AddInfo(FString::Printf(TEXT("HIT: hit points %d -> %d, one-shots played %d"), Before, After, Body->GetOneShots().GetPlayed()));
	if (After < Before && After >= 1) TestTrue(TEXT("a hit that costs life plays the flinch"), Body->GetOneShots().IsPlaying());
	// The kill: the corpse and its pool are left at once (the original's moment); the body plays its death and the corpse
	// mesh is shown when the clip ends.
	const int32 CorpsesBefore = Scene.Creatures->GetCorpseCount();
	Scene.Kill(0, 1000);
	Scene.Step(1.f / 60.f);
	TestEqual(TEXT("the corpse is left at the kill, as in 1997"), Scene.Creatures->GetCorpseCount(), CorpsesBefore + 1);
	TestEqual(TEXT("its blood pool is on the ground at once"), Scene.Creatures->GetCorpseDecalCount(), CorpsesBefore + 1);
	TestEqual(TEXT("the body plays its death"), Scene.Deaths->GetPlayingCount(), 1);
	UStaticMeshComponent* Corpse = Scene.Creatures->GetNewestCorpse();
	if (TestNotNull(TEXT("corpse"), Corpse)) TestFalse(TEXT("the corpse mesh waits for the end of the clip"), Corpse->IsVisible());
	float Time = 0.f;
	while (Scene.Deaths->GetPlayingCount() > 0 && Time < 10.f) { Scene.Step(1.f / 60.f); Time += 1.f / 60.f; }
	AddInfo(FString::Printf(TEXT("DEATH: clip %.2f s at rate %.2f, corpse shown after %.2f s"), DeathClip->GetPlayLength(), Row->Death.Rate, Time));
	TestTrue(TEXT("the death ends with the clip"), FMath::Abs(Time - DeathClip->GetPlayLength() / Row->Death.Rate) < .1f);
	if (Corpse) TestTrue(TEXT("then the corpse mesh is drawn"), Corpse->IsVisible());
	// A kill and then the screen is left mid-death: the corpse and the dying body go together.
	Scene.Kill(1, 1000);
	Scene.Step(1.f / 60.f);
	TestEqual(TEXT("second death plays"), Scene.Deaths->GetPlayingCount(), 1);
	Scene.D->ResetSprites();
	Scene.Step(1.f / 60.f);
	TestEqual(TEXT("a save restored mid-death: the corpse goes"), Scene.Creatures->GetCorpseCount(), 0);
	TestEqual(TEXT("and the dying body with it"), Scene.Deaths->GetPlayingCount(), 0);
	// Switched off: the 1997 swap, nothing plays.
	IConsoleVariable* Clips = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.Creature.DeathClips"));
	Clips->Set(0, ECVF_SetByCode);
	ON_SCOPE_EXIT { Clips->Set(1, ECVF_SetByCode); };
	TestEqual(TEXT("deaths started in all"), Scene.Deaths->GetStarted(), 2);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureOneShotDuckTest, "Dink.Creature.OneShots.DuckHeadPopAndBurstDeath", DINK_TEST_FLAGS)
bool FDinkCreatureOneShotDuckTest::RunTest(const FString&)
{
	using namespace DinkCreatureOneShotTest;
	DinkCreatureOneShots::Reload();
	const FDinkCreatureOneShotRow* Row = DinkCreatureOneShots::Find(TEXT("duck"));
	UAnimSequence* Fall = Row ? DinkCreatureOneShots::Load(Row->BurstDeath) : nullptr;
	if (!Fall || !LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Dink/Photoreal/Creatures/Duck/SK_Duck_PR.SK_Duck_PR"), nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		AddWarning(TEXT("skipped: the photoreal duck or its clips are not imported in this checkout"));
		return true;
	}
	IConsoleVariable* Art = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.CreatureClassArt"));
	const int32 ArtBefore = Art->GetInt();
	Art->Set(2, ECVF_SetByCode);
	ON_SCOPE_EXIT { Art->Set(ArtBefore, ECVF_SetByCode); };
	UStaticMesh* Plane = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	FBoncaScene Scene;
	if (!TestTrue(TEXT("scene starts"), Scene.Start(Plane, TEXT("duck"), 21, nullptr, 1))) return false;
	ON_SCOPE_EXIT { Scene.Stop(); };
	FDinkSprite* Sprite = Scene.D->FindSprite(Scene.Handles[0]);
	Sprite->Props.Add(TEXT("brain"), 3);
	Sprite->Props.Add(TEXT("base_walk"), 20);
	Sprite->Props.Add(TEXT("hitpoints"), 5);
	for (int32 I = 0; I < 30; ++I) Scene.Step(1.f / 60.f);
	UDinkCreatureClassComponent* Body = UDinkCreatureSubsystem::FindClassBody(Scene.Boncas[0]);
	if (!TestNotNull(TEXT("the duck has its body"), Body)) return false;
	// First hit: duck_brain beheads it (dink.cpp:12748-12775); the head-pop gore is the simulation's, the body flinches.
	const int32 PlayedBefore = Body->GetOneShots().GetPlayed();
	Scene.Kill(0, 5);
	Scene.Step(1.f / 60.f);
	TestTrue(TEXT("the first hit beheads the duck, as in 1997"), Scene.D->FindSprite(Scene.Handles[0]) && Scene.D->FindSprite(Scene.Handles[0])->bHeadless);
	TestTrue(TEXT("the body flinches as the head goes"), Body->GetOneShots().GetPlayed() > PlayedBefore);
	for (int32 I = 0; I < 20; ++I) Scene.Step(1.f / 60.f);
	// Second hit: the burst of sequence 164 (12728-12740), after the headless body has fallen.
	const int32 DecalsBefore = Scene.Creatures->GetBloodDecalsMade();
	Scene.Kill(0, 5);
	Scene.Step(1.f / 60.f);
	TestEqual(TEXT("the headless body falls"), Scene.Deaths->GetPlayingCount(), 1);
	const int32 DecalsAtKill = Scene.Creatures->GetBloodDecalsMade();
	float Time = 0.f;
	while (Scene.Deaths->GetPlayingCount() > 0 && Time < 10.f) { Scene.Step(1.f / 60.f); Time += 1.f / 60.f; }
	Scene.Step(1.f / 60.f);
	AddInfo(FString::Printf(TEXT("DUCK: fall %.2f s, burst after %.2f s; stains made %d before, %d at the kill, %d after"), Fall->GetPlayLength(), Time, DecalsBefore, DecalsAtKill, Scene.Creatures->GetBloodDecalsMade()));
	TestTrue(TEXT("the burst comes where the fall ends"), FMath::Abs(Time - Fall->GetPlayLength() / Row->BurstDeath.Rate) < .1f);
	TestTrue(TEXT("and leaves its stain as before"), Scene.Creatures->GetBloodDecalsMade() > DecalsAtKill);
	return true;
}
