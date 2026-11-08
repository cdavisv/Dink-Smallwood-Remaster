#include "DinkTestHelpers.h"
#include "Audio.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundWave.h"

namespace
{
TSharedPtr<FJsonObject> LoadAudioTestJson(FAutomationTestBase& Test, const FString& Path)
{
	FString Text;
	if (!Test.TestTrue(TEXT("audio manifest exists: ") + Path, FFileHelper::LoadFileToString(Text, *Path))) return nullptr;
	TSharedPtr<FJsonObject> Object;
	if (!Test.TestTrue(TEXT("audio manifest parses: ") + Path,
		FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Object) && Object.IsValid())) return nullptr;
	return Object;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkApprovedAudioAssetsTest, "Dink.Audio.ApprovedAssets", DINK_TEST_FLAGS)
bool FDinkApprovedAudioAssetsTest::RunTest(const FString& Parameters)
{
	const TSharedPtr<FJsonObject> Selection = LoadAudioTestJson(*this, FPaths::ProjectDir() / TEXT("SourceAssets/Audio/selection_manifest.json"));
	const TSharedPtr<FJsonObject> Runtime = LoadAudioTestJson(*this, FPaths::ProjectContentDir() / TEXT("Dink/Data/Audio/approved.json"));
	if (!Selection || !Runtime) return false;
	TestEqual(TEXT("approved selection schema"), Selection->GetStringField(TEXT("schema")), FString(TEXT("dink-audio-selection/1")));
	TestEqual(TEXT("published runtime schema"), Runtime->GetStringField(TEXT("schema")), FString(TEXT("dink-audio/1")));
	const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
	if (!TestTrue(TEXT("selection has approved assets"), Selection->TryGetArrayField(TEXT("assets"), Rows)) || !Rows) return false;
	TestEqual(TEXT("review selected exactly 72 assets"), Rows->Num(), 72);
	TMap<FString, USoundWave*> Approved;
	TSet<USoundWave*> UniqueWaves;
	for (const TSharedPtr<FJsonValue>& Value : *Rows)
	{
		const TSharedPtr<FJsonObject> Row = Value->AsObject();
		if (!TestTrue(TEXT("selection row is an object"), Row.IsValid())) continue;
		const FString Name = Row->GetStringField(TEXT("name"));
		const FString ObjectPath = Row->GetStringField(TEXT("folder")) / Name + TEXT(".") + Name;
		TestFalse(TEXT("unique approved asset identity: ") + ObjectPath, Approved.Contains(ObjectPath));
		USoundWave* Sound = LoadObject<USoundWave>(nullptr, *ObjectPath);
		if (!TestNotNull(TEXT("approved SoundWave loads: ") + ObjectPath, Sound)) continue;
		Approved.Add(ObjectPath, Sound);
		UniqueWaves.Add(Sound);
		TestEqual(TEXT("selected loop policy: ") + Name, bool(Sound->bLooping), Row->GetBoolField(TEXT("loop")));
		TArray<uint8> Bytes;
		const FString Source = FPaths::ProjectDir() / Row->GetStringField(TEXT("source"));
		if (!TestTrue(TEXT("selected WAV source exists: ") + Name, FFileHelper::LoadFileToArray(Bytes, *Source))) continue;
		FWaveModInfo Wave;
		FString Error;
		if (!TestTrue(TEXT("source is a valid WAV: ") + Name, Wave.ReadWaveInfo(Bytes.GetData(), Bytes.Num(), &Error))) continue;
		if (!TestTrue(TEXT("source WAV has a valid byte rate: ") + Name, Wave.pAvgBytesPerSec && *Wave.pAvgBytesPerSec > 0)) continue;
		const double SourceDuration = double(Wave.SampleDataSize) / *Wave.pAvgBytesPerSec;
		TestTrue(TEXT("selected duration matches source WAV: ") + Name,
			FMath::Abs(SourceDuration - Row->GetNumberField(TEXT("duration_s"))) <= 0.001);
		// GetDuration() returns an infinite-loop sentinel for looping music; Duration is its actual imported length.
		TestTrue(TEXT("imported duration matches source WAV: ") + Name,
			FMath::Abs(double(Sound->Duration) - SourceDuration) <= 0.02);
	}
	TestEqual(TEXT("72 unique imported SoundWave paths"), Approved.Num(), 72);
	TestEqual(TEXT("72 distinct SoundWave objects"), UniqueWaves.Num(), 72);
	TSet<FString> Referenced;
	for (const FString& Section : {FString(TEXT("sounds")), FString(TEXT("music")), FString(TEXT("screen_music"))})
	{
		const TSharedPtr<FJsonObject>* Table = nullptr;
		if (!TestTrue(TEXT("runtime section exists: ") + Section, Runtime->TryGetObjectField(Section, Table)) || !Table || !Table->IsValid()) continue;
		for (const auto& Pair : (*Table)->Values)
		{
			const TSharedPtr<FJsonObject> Entry = Pair.Value->AsObject();
			if (!TestTrue(TEXT("runtime audio entry is an object: ") + FString(Pair.Key.ToView()), Entry.IsValid())) continue;
			const FString Path = Entry->GetStringField(TEXT("asset"));
			USoundWave* const* Wave = Approved.Find(Path);
			if (!TestTrue(TEXT("runtime references an approved imported asset: ") + Section + TEXT("/") + FString(Pair.Key.ToView()), Wave != nullptr)) continue;
			TestEqual(TEXT("runtime loop matches imported SoundWave: ") + Section + TEXT("/") + FString(Pair.Key.ToView()),
				bool((*Wave)->bLooping), Entry->GetBoolField(TEXT("loop")));
			Referenced.Add(Path);
		}
	}
	TestEqual(TEXT("every approved SoundWave is reachable from runtime routing"), Referenced.Num(), 72);
	const TSharedPtr<FJsonObject> Sounds = Runtime->GetObjectField(TEXT("sounds"));
	for (const FString& Rejected : {FString(TEXT("9")), FString(TEXT("44")), FString(TEXT("48")), FString(TEXT("49"))})
	{
		TestFalse(TEXT("rejected sound ID has no runtime mapping: ") + Rejected, Sounds->HasField(Rejected));
		const FString Prefix = FString::Printf(TEXT("SFX_%02d_"), FCString::Atoi(*Rejected));
		for (const TPair<FString, USoundWave*>& Pair : Approved)
			TestFalse(TEXT("rejected sound was not imported: ") + Prefix, Pair.Value->GetName().StartsWith(Prefix));
	}
	TestEqual(TEXT("four explicit review rejections preserved"), Runtime->GetArrayField(TEXT("rejected")).Num(), 4);
	const TSharedPtr<FJsonObject> Music = Runtime->GetObjectField(TEXT("music"));
	if (TestTrue(TEXT("5.ogg music alias retained"), Music->HasField(TEXT("5.ogg"))) &&
		TestTrue(TEXT("5.mid music alias retained"), Music->HasField(TEXT("5.mid"))))
	{
		TestNotEqual(TEXT("OGG and MIDI aliases select different tracks"),
			Music->GetObjectField(TEXT("5.ogg"))->GetStringField(TEXT("asset")),
			Music->GetObjectField(TEXT("5.mid"))->GetStringField(TEXT("asset")));
		TestTrue(TEXT("5.ogg selects Terris"), Music->GetObjectField(TEXT("5.ogg"))->GetStringField(TEXT("asset")).Contains(TEXT("MUS_04_terris_town")));
		TestTrue(TEXT("5.mid selects story"), Music->GetObjectField(TEXT("5.mid"))->GetStringField(TEXT("asset")).Contains(TEXT("MUS_28_story")));
	}
	return true;
}
