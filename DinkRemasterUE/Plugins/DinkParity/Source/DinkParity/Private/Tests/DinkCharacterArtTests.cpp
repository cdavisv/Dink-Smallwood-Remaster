#include "DinkTestHelpers.h"
#include "AssetCompilingManager.h"
#include "Animation/Skeleton.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/Material.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkCharacterArtAssetTest, "Dink.Art.CharacterBindPoseAndMaterials", DINK_TEST_FLAGS)
bool FDinkCharacterArtAssetTest::RunTest(const FString& Parameters)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Dink/Data/Art/characters.json"))))
	{
		AddWarning(TEXT("skipped: character art not imported (Scripts/import_character_art.sh)"));
		return true;
	}
	TSharedPtr<FJsonObject> Manifest;
	if (!TestTrue(TEXT("character manifest parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest)) || !Manifest) return false;
	USkeletalMesh* Reference = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
	if (!TestNotNull(TEXT("installed animation reference mesh"), Reference)) return false;
	const FReferenceSkeleton& ExpectedRig = Reference->GetRefSkeleton();
	TestEqual(TEXT("supported character schema"), Manifest->GetStringField(TEXT("schema")), FString(TEXT("dink-characters/1")));
	TestTrue(TEXT("contains authored character models"), Manifest->GetArrayField(TEXT("assets")).Num() > 0);
	const TSharedPtr<FJsonObject>* Player = nullptr;
	if (Manifest->TryGetObjectField(TEXT("player"), Player) && Player && Player->IsValid())
	{
		USkeletalMesh* Hero = LoadObject<USkeletalMesh>(nullptr, *(*Player)->GetStringField(TEXT("mesh")));
		if (TestNotNull(TEXT("authored player mesh loads"), Hero))
		{
			TestEqual(TEXT("player compatible with existing locomotion"), Hero->GetSkeleton(), Reference->GetSkeleton());
			TestTrue(TEXT("player replaces mannequin geometry"), Hero != Reference);
		}
	}
	bool bMotherMapped = false;
	for (const TSharedPtr<FJsonValue>& Placement : Manifest->GetArrayField(TEXT("placements")))
	{
		bMotherMapped |= Placement->AsObject()->GetStringField(TEXT("origin")) == TEXT("S001_P26");
	}
	TestTrue(TEXT("starting mother keeps original placement identity"), bMotherMapped);
	for (const TSharedPtr<FJsonValue>& Value : Manifest->GetArrayField(TEXT("assets")))
	{
		const TSharedPtr<FJsonObject> Row = Value->AsObject();
		const FString Path = Row->GetStringField(TEXT("mesh"));
		USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, *Path);
		if (!TestNotNull(TEXT("character mesh loads: ") + Path, Mesh)) continue;
		FAssetCompilingManager::Get().FinishAllCompilation();
		TestEqual(TEXT("uses existing animation Skeleton: ") + Path, Mesh->GetSkeleton(), Reference->GetSkeleton());
		TestNotNull(TEXT("character has a Physics Asset: ") + Path, Mesh->GetPhysicsAsset());
		const TArray<TSharedPtr<FJsonValue>>& Size = Row->GetArrayField(TEXT("expected_size_cm"));
		const FVector ExpectedSize(Size[0]->AsNumber(), Size[1]->AsNumber(), Size[2]->AsNumber());
		TestTrue(TEXT("character import has real centimetre dimensions: ") + Path, (Mesh->GetBounds().BoxExtent * 2.0).Equals(ExpectedSize, 1.0));
		const FReferenceSkeleton& Rig = Mesh->GetRefSkeleton();
		TestEqual(TEXT("complete reference bone count: ") + Path, Rig.GetNum(), ExpectedRig.GetNum());
		for (int32 Index = 0; Index < Rig.GetNum(); ++Index)
		{
			const FName Name = Rig.GetBoneName(Index);
			const int32 ExpectedIndex = ExpectedRig.FindBoneIndex(Name);
			if (!TestTrue(TEXT("reference bone retained: ") + Name.ToString(), ExpectedIndex != INDEX_NONE)) continue;
			const int32 Parent = Rig.GetParentIndex(Index);
			const int32 ExpectedParent = ExpectedRig.GetParentIndex(ExpectedIndex);
			TestEqual(TEXT("bone parent retained: ") + Name.ToString(), Parent >= 0 ? Rig.GetBoneName(Parent) : NAME_None,
				ExpectedParent >= 0 ? ExpectedRig.GetBoneName(ExpectedParent) : NAME_None);
			const FTransform& Actual = Rig.GetRefBonePose()[Index];
			const FTransform& Expected = ExpectedRig.GetRefBonePose()[ExpectedIndex];
			TestTrue(TEXT("bind position retained: ") + Name.ToString(), Actual.GetLocation().Equals(Expected.GetLocation(), 0.1));
			TestTrue(TEXT("bind orientation retained: ") + Name.ToString(), Actual.GetRotation().AngularDistance(Expected.GetRotation()) <= 0.002);
			TestTrue(TEXT("bind scale retained: ") + Name.ToString(), Actual.GetScale3D().Equals(Expected.GetScale3D(), 0.001));
		}
		TestEqual(TEXT("all authored character LODs retained: ") + Path, Mesh->GetLODNum(), int32(Row->GetNumberField(TEXT("expected_lods"))));
		TestTrue(TEXT("humanoid has distance LODs: ") + Path, Mesh->GetLODNum() >= 4);
		TestTrue(TEXT("humanoid respects five-material budget: ") + Path, Mesh->GetMaterials().Num() <= 5);
		for (const FSkeletalMaterial& Slot : Mesh->GetMaterials())
		{
			UMaterialInterface* Material = Slot.MaterialInterface;
			if (!TestNotNull(TEXT("assigned character material: ") + Slot.MaterialSlotName.ToString(), Material)) continue;
			TestTrue(TEXT("skeletal material usage saved: ") + Slot.MaterialSlotName.ToString(), Material->GetMaterial()->GetUsageByFlag(MATUSAGE_SkeletalMesh));
			if (Slot.MaterialSlotName.ToString().Contains(TEXT("Hair")) || Slot.MaterialSlotName.ToString().Contains(TEXT("BrowLash")))
			{
				TestEqual(TEXT("hair alpha uses masked shading"), Material->GetBlendMode(), BLEND_Masked);
				TestTrue(TEXT("hair alpha is two sided"), Material->IsTwoSided());
			}
		}
	}
	return true;
}
