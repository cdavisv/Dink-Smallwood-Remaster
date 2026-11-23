// Seth's cast flash (SP-06, 23 Nov 2026): s7-boss.c:46-66 flickers his standing picture 580 between frame 1 and frame 2,
// which shows his face and hands lit red. The class row's `flash` drives a scalar material parameter (CastFlash) on the
// figure while the sprite stands on that frame. Presentation only: the sprite and the simulation are never touched.
#include "DinkTestHelpers.h"
#include "DinkCreatureClass.h"
#include "DinkCreatureClassComponent.h"
#include "DinkCreatureSubsystem.h"
#include "AssetCompilingManager.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace DinkCreatureFlashTest
{
	TSharedPtr<FJsonObject> Parse(const FString& Text)
	{
		TSharedPtr<FJsonObject> Object;
		FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Object);
		return Object;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureFlashRowsTest, "Dink.Art.CreatureClass.FlashRowsAndEasing", DINK_TEST_FLAGS)
bool FDinkCreatureFlashRowsTest::RunTest(const FString&)
{
	using namespace DinkCreatureFlashTest;
	const TCHAR* Json = TEXT(R"({"schema":"dink-creatures/1","classes":[
		{"class":"caster","mesh":"/Game/A/SK_C.SK_C","locomotion":{"idle":"/Game/A/I.I","gaits":[{"clip":"/Game/A/W.W","speed_cm_s":80}]},
		 "roles":{"walk":{"sequences":[581,583],"locomotion":true}},
		 "flash":{"parameter":"CastFlash","pseq":580,"pframe":2,"rise_s":0.1,"fall_s":0.2}},
		{"class":"plain","mesh":"/Game/A/SK_P.SK_P","locomotion":{"idle":"/Game/A/I.I","gaits":[{"clip":"/Game/A/W.W","speed_cm_s":80}]},
		 "roles":{"walk":{"sequences":[700],"locomotion":true}}},
		{"class":"noparameter","mesh":"/Game/A/SK_X.SK_X","locomotion":{"idle":"/Game/A/I.I","gaits":[{"clip":"/Game/A/W.W","speed_cm_s":80}]},
		 "roles":{"walk":{"sequences":[800],"locomotion":true}},"flash":{"pseq":580,"pframe":2}}]})");
	TArray<FDinkCreatureClassBinding> Rows;
	TArray<FString> Problems;
	TestEqual(TEXT("the row without a parameter is refused"), DinkCreatureClass::ParseBindings(*Parse(Json), Rows, &Problems), 2);
	TestEqual(TEXT("one reason"), Problems.Num(), 1);
	if (Rows.Num() != 2) return false;
	const FDinkCreatureFlash& F = Rows[0].Flash;
	TestTrue(TEXT("flash read"), F.IsValid() && F.Parameter == FName(TEXT("CastFlash")) && F.PSeq == 580 && F.PFrame == 2 &&
		FMath::IsNearlyEqual(F.RiseS, .1f) && FMath::IsNearlyEqual(F.FallS, .2f));
	TestFalse(TEXT("a row without one has none"), Rows[1].Flash.IsValid());

	// easing: up at 1/rise per second while the sprite stands still on picture 580 frame 2, down at 1/fall otherwise
	TestTrue(TEXT("half way up after half the rise"), FMath::IsNearlyEqual(DinkCreatureClass::StepFlash(F, 0, 580, 2, 0.f, .05f), .5f, 1.e-4f));
	TestEqual(TEXT("full after the rise"), DinkCreatureClass::StepFlash(F, 0, 580, 2, 0.f, .2f), 1.f);
	TestTrue(TEXT("frame 1 lets it fall"), FMath::IsNearlyEqual(DinkCreatureClass::StepFlash(F, 0, 580, 1, 1.f, .1f), .5f, 1.e-4f));
	TestEqual(TEXT("an animating sequence is no still picture"), DinkCreatureClass::StepFlash(F, 581, 580, 2, 0.f, .2f), 0.f);
	TestEqual(TEXT("another picture: nothing"), DinkCreatureClass::StepFlash(F, 0, 581, 2, 0.f, .2f), 0.f);
	TestEqual(TEXT("a row without a flash stays 0"), DinkCreatureClass::StepFlash(Rows[1].Flash, 0, 580, 2, 0.f, 1.f), 0.f);

	// the shipped Seth row (Scripts/bind_people_classes.py FLASH)
	FString Text;
	TArray<FDinkCreatureClassBinding> Shipped;
	if (TestTrue(TEXT("creatures.json"), FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/creatures.json")))))
		DinkCreatureClass::ParseBindings(*Parse(Text), Shipped);
	const FDinkCreatureClassBinding* Seth = Shipped.FindByPredicate([](const FDinkCreatureClassBinding& B) { return B.ClassId == FName(TEXT("seth")); });
	if (TestNotNull(TEXT("seth row"), Seth))
		TestTrue(TEXT("Seth flashes CastFlash on picture 580 frame 2"), Seth->Flash.IsValid() && Seth->Flash.Parameter == FName(TEXT("CastFlash")) &&
			Seth->Flash.PSeq == 580 && Seth->Flash.PFrame == 2);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCreatureFlashSethTest, "Dink.Art.CreatureClass.SethCastFlashFollowsHisPicture", DINK_TEST_FLAGS)
bool FDinkCreatureFlashSethTest::RunTest(const FString&)
{
	IConsoleVariable* ClassArt = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.CreatureClassArt"));
	IConsoleVariable* ArtOn = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));
	const int32 ClassBefore = ClassArt ? ClassArt->GetInt() : 1, ArtBefore = ArtOn ? ArtOn->GetInt() : 1;
	if (ClassArt) ClassArt->SetWithCurrentPriority(2);
	if (ArtOn) ArtOn->SetWithCurrentPriority(1);
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	ON_SCOPE_EXIT
	{
		GI->Shutdown(); GEngine->DestroyWorldContext(World); World->DestroyWorld(false);
		if (ClassArt) ClassArt->SetWithCurrentPriority(ClassBefore);
		if (ArtOn) ArtOn->SetWithCurrentPriority(ArtBefore);
	};
	UDinkCreatureSubsystem* Creatures = World->GetSubsystem<UDinkCreatureSubsystem>();
	if (!TestNotNull(TEXT("creature subsystem"), Creatures)) return false;
	Creatures->OnWorldBeginPlay(*World);
	FAssetCompilingManager::Get().FinishAllCompilation();
	// Milder's scene makes Seth with create_sprite(320, 150, 0, 580, 1) (s7-mil.c:97): the class body of picture 580.
	AActor* Actor = World->SpawnActor<AActor>();
	USceneComponent* Root = NewObject<USceneComponent>(Actor);
	Actor->SetRootComponent(Root);
	Root->RegisterComponent();
	DinkCreatureClass::FSpriteView View;
	View.PSeq = 580;
	UDinkCreatureClassComponent* Body = Creatures->PresentScriptSprite(Actor, View, 0.f, 0.f, 100);
	if (!TestNotNull(TEXT("Seth's figure dresses the sprite"), Body)) return false;
	TestEqual(TEXT("class"), Body->GetClassId(), FName(TEXT("seth")));
	const float Dt = 1.f / 60.f;
	auto Hold = [&](int32 PFrame, float Seconds, float& Peak)
	{
		FDinkCreatureSpriteState State;
		State.PSeq = 580;
		State.PFrame = PFrame;
		State.Dir = 2;
		for (float T = 0.f; T < Seconds - .5f * Dt; T += Dt)
		{
			Body->ApplySpriteState(State);
			Body->Present(Dt);
			Peak = FMath::Max(Peak, Body->GetFlashLevel());
		}
		return Body->GetFlashLevel();
	};
	float Peak = 0.f;
	TestEqual(TEXT("standing (frame 1): no flash"), Hold(1, .5f, Peak), 0.f);
	// the cast: 200 ms frame 2, 200 ms frame 1, 200 ms frame 2, 200 ms frame 1 (s7-boss.c:55-66)
	TestEqual(TEXT("frame 2 for 200 ms: full"), Hold(2, .2f, Peak), 1.f);
	const float AfterFirst = Hold(1, .2f, Peak);
	TestTrue(TEXT("frame 1 for 200 ms: mostly gone (0.25 s fall)"), AfterFirst > 0.f && AfterFirst < .3f);
	TestEqual(TEXT("second flicker full"), Hold(2, .2f, Peak), 1.f);
	TestEqual(TEXT("gone 0.3 s after the cast"), Hold(1, .3f, Peak), 0.f);
	TestEqual(TEXT("peak"), Peak, 1.f);
	// walking (an animating sequence) never flashes
	float WalkPeak = 0.f;
	FDinkCreatureSpriteState Walk;
	Walk.Seq = 582; Walk.PSeq = 580; Walk.PFrame = 2; Walk.Dir = 2;
	for (int32 I = 0; I < 30; ++I) { Body->ApplySpriteState(Walk); Body->Present(Dt); WalkPeak = FMath::Max(WalkPeak, Body->GetFlashLevel()); }
	TestEqual(TEXT("a walking Seth does not flash"), WalkPeak, 0.f);
	return true;
}
