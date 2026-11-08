#include "DinkTestHelpers.h"
#include "DinkDirector.h"
#include "DinkHumanoidComponent.h"
#include "DinkScriptSpriteComponent.h"
#include "DinkStorySubsystem.h"
#include "Greybox/DinkGreyboxSubsystem.h"
#include "Greybox/DinkScreenVolume.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkScriptCharacterProfileTest,
								 "Dink.Art.ScriptCharacter.MarkerScaleSizeAndSavedFacing", DINK_TEST_FLAGS)
bool FDinkScriptCharacterProfileTest::RunTest(const FString&)
{
	FString Text;
	TSharedPtr<FJsonObject> Manifest;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/characters.json"))) ||
		!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest)
	{
		AddWarning(TEXT("skipped: character manifest absent"));
		return true;
	}
	const TSharedPtr<FJsonObject>* Profiles = nullptr;
	const TSharedPtr<FJsonObject>* Profile = nullptr;
	if (!Manifest->TryGetObjectField(TEXT("script_profiles"), Profiles) ||
		!(*Profiles)->TryGetObjectField(TEXT("s1-bul"), Profile))
	{
		AddWarning(TEXT("skipped: Milder script profile not imported"));
		return true;
	}
	IConsoleVariable* Enabled = IConsoleManager::Get().FindConsoleVariable(TEXT("dink.ArtEnabled"));
	const int32 Previous = Enabled ? Enabled->GetInt() : 1;
	if (Enabled)
		Enabled->SetWithCurrentPriority(1);
	ON_SCOPE_EXIT
	{
		if (Enabled)
			Enabled->SetWithCurrentPriority(Previous);
	};
	UGameInstance* GI = NewObject<UGameInstance>(GEngine);
	GI->InitializeStandalone();
	UWorld* World = GI->GetWorld();
	UDinkStorySubsystem* Story = GI->GetSubsystem<UDinkStorySubsystem>();
	Story->bRunScreenScripts = false;
	Story->bNewGamePending = false;
	Story->bInstantMode = true;
	Story->GetFacts()->SetFact(TEXT("pig_story"),
							   1); // Exercise attaching the real script without rerunning the long intro.
	UDinkDirector* Director = Story->GetDirector();
	UDinkGreyboxSubsystem* Greybox = World->GetSubsystem<UDinkGreyboxSubsystem>();
	ADinkScreenVolume* Screen = World->SpawnActor<ADinkScreenVolume>();
	Screen->ScreenNumber = 407;
	Screen->Corners.NW = FVector2D(0, 0);
	Screen->Corners.NE = FVector2D(60, 0);
	Screen->Corners.SW = FVector2D(0, 40);
	Screen->Corners.SE = FVector2D(60, 40);
	Greybox->RegisterScreen(Screen);
	FDinkScriptInstance Caller;
	Caller.Id = 900001;
	Caller.Sprite = 1;
	Caller.Screen = 407;
	auto Execute = [&](const FString& Command)
	{ return Director->Execute(Caller, FDinkStoryLine::Parse(TEXT(">> ") + Command, {TEXT("cmd"), TEXT("src:1")})); };
	Execute(TEXT("create_sprite 320 200 0 341 1"));
	int32 Handle = 0;
	for (const auto& Pair : Director->GetSprites())
		if (Pair.Value.bSpawned && Pair.Value.Actor.IsValid())
			Handle = Pair.Key;
	ADinkScriptSpriteActor* Marker = Cast<ADinkScriptSpriteActor>(Director->GetActor(Handle));
	if (!TestNotNull(TEXT("real create_sprite spawns generic marker"), Marker))
	{
		GI->Shutdown();
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
		return false;
	}
	TestTrue(TEXT("unprofiled marker retains original nonuniform scale"),
			 Marker->GetActorScale3D().Equals(FVector(.3, .3, .6), .001));
	Execute(FString::Printf(TEXT("sp_script %d \"s1-bul\""), Handle));
	Story->RunUntilIdle();
	Marker = Cast<ADinkScriptSpriteActor>(Director->GetActor(Handle));
	UDinkHumanoidComponent* Human = Marker->FindComponentByClass<UDinkHumanoidComponent>();
	UCapsuleComponent* Body = Marker->FindComponentByClass<UCapsuleComponent>();
	if (!TestNotNull(TEXT("script attachment applies Milder model"), Human) ||
		!TestNotNull(TEXT("script attachment creates anatomical proxy"), Body))
	{
		Greybox->UnregisterScreen(Screen);
		GI->Shutdown();
		GEngine->DestroyWorldContext(World);
		World->DestroyWorld(false);
		return false;
	}
	TestTrue(TEXT("script profile normalizes old cylinder scale"),
			 Marker->GetActorScale3D().Equals(FVector::OneVector, .001));
	TestTrue(TEXT("cylinder hidden after valid profile"), Marker->Marker->bHiddenInGame);
	TestEqual(TEXT("real attached script retained"), Director->FindSprite(Handle)->Script, FName(TEXT("s1-bul")));
	TestEqual(TEXT("script component mirrors attachment"), Marker->Sprite->Script, FName(TEXT("s1-bul")));
	Director->SpriteProperty(nullptr, TEXT("size"), Handle, 200);
	TestTrue(TEXT("logical size2 retains uniform anatomical scale"),
			 Marker->GetActorScale3D().Equals(FVector(2), .001));
	TestTrue(TEXT("visual feet origin remains atground atsize2"),
			 FMath::IsNearlyZero(Human->GetComponentLocation().Z, .01));
	TestTrue(TEXT("capsule bottom remains atground atsize2"),
			 FMath::IsNearlyZero(Body->GetComponentLocation().Z - Body->GetScaledCapsuleHalfHeight(), .01));
	TestTrue(TEXT("capsule radius follows actual script size"),
			 FMath::IsNearlyEqual(Body->GetScaledCapsuleRadius(),
								  float((*Profile)->GetNumberField(TEXT("capsule_radius_cm")) * 2), .01f));
	TestTrue(TEXT("capsule height follows actual script size"),
			 FMath::IsNearlyEqual(Body->GetScaledCapsuleHalfHeight(),
								  float((*Profile)->GetNumberField(TEXT("capsule_halfheight_cm")) * 2), .01f));
	Director->SpriteProperty(nullptr, TEXT("dir"), Handle, 7);
	Director->StartMove(*Director->FindSprite(Handle), 7, 290);
	const FQuat SavedFacing = Marker->GetActorQuat();
	const TSharedPtr<FJsonObject> Saved = Director->SaveState();
	Director->LoadState(Saved);
	ADinkScriptSpriteActor* Restored = Cast<ADinkScriptSpriteActor>(Director->GetActor(Handle));
	if (TestNotNull(TEXT("saved scripted actor respawns"), Restored))
	{
		UDinkHumanoidComponent* RestoredHuman = Restored->FindComponentByClass<UDinkHumanoidComponent>();
		UCapsuleComponent* RestoredBody = Restored->FindComponentByClass<UCapsuleComponent>();
		TestNotNull(TEXT("save load reapplies script profile model"), RestoredHuman);
		TestNotNull(TEXT("save load reapplies body proxy"), RestoredBody);
		TestEqual(TEXT("restored actor script component mirrors saved script"), Restored->Sprite->Script,
				  FName(TEXT("s1-bul")));
		TestEqual(TEXT("restored actor direction component mirrors saved direction"), Restored->Sprite->Dir, 7);
		TestTrue(TEXT("saved facing restored immediately during active scripted move"),
				 Restored->GetActorQuat().AngularDistance(SavedFacing) < .001);
		TestTrue(TEXT("save keeps active scripted movement"), Director->IsMoving(Handle));
		TestTrue(TEXT("saved size2 remains uniform"), Restored->GetActorScale3D().Equals(FVector(2), .001));
		if (RestoredHuman && RestoredBody)
		{
			TestTrue(TEXT("restored visual feet staygrounded"),
					 FMath::IsNearlyZero(RestoredHuman->GetComponentLocation().Z, .01));
			TestTrue(TEXT("restored capsule staysgrounded"),
					 FMath::IsNearlyZero(
						 RestoredBody->GetComponentLocation().Z - RestoredBody->GetScaledCapsuleHalfHeight(), .01));
			RestoredHuman->TickComponent(.1f, LEVELTICK_All, nullptr);
			Director->Tick(100, 100);
			RestoredHuman->TickComponent(.1f, LEVELTICK_All, nullptr);
			TestTrue(TEXT("restored fast scripted walk uses faster animation cadence"),
					 RestoredHuman->GetSingleNodeInstance()->GetPlayRate() > 1.f);
		}
	}
	Greybox->UnregisterScreen(Screen);
	GI->Shutdown();
	GEngine->DestroyWorldContext(World);
	World->DestroyWorld(false);
	return true;
}
