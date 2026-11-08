#include "DinkMaterialArtLibrary.h"
#include "Materials/Material.h"

TArray<int32> UDinkMaterialArtLibrary::GetConnectedMaterialProperties(UMaterial* Material)
{
	TArray<int32> Connected;
	if (!Material) return Connected;
	for (int32 Index = 0; Index < MP_MAX; ++Index)
	{
		const FExpressionInput* Input = Material->GetExpressionInputForProperty(static_cast<EMaterialProperty>(Index));
		if (Input && Input->Expression) Connected.Add(Index);
	}
	return Connected;
}

#if WITH_DEV_AUTOMATION_TESTS
#include "Materials/MaterialExpressionConstant3Vector.h"
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkMaterialPropertyInspectionTest,
	"Dink.Art.MaterialPropertyInspection", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)

bool FDinkMaterialPropertyInspectionTest::RunTest(const FString& Parameters)
{
	UMaterial* Material = NewObject<UMaterial>();
	UMaterialExpressionConstant3Vector* Node = NewObject<UMaterialExpressionConstant3Vector>(Material);
	TestTrue(TEXT("empty graph has no connected properties"),
		UDinkMaterialArtLibrary::GetConnectedMaterialProperties(Material).IsEmpty());
	const TArray<EMaterialProperty> Properties = {MP_BaseColor, MP_EmissiveColor, MP_WorldPositionOffset,
		MP_CustomizedUVs0, MP_CustomizedUVs7, MP_Displacement, MP_PixelDepthOffset};
	TArray<int32> Expected;
	for (EMaterialProperty Property : Properties)
	{
		FExpressionInput* Input = Material->GetExpressionInputForProperty(Property);
		if (!TestNotNull(TEXT("supported material input exists"), Input)) return false;
		Input->Expression = Node;
		Input->OutputIndex = 0;
		Expected.Add(static_cast<int32>(Property));
	}
	Expected.Sort();
	TestTrue(TEXT("includes reused nodes on displacement and hidden UV pins"),
		UDinkMaterialArtLibrary::GetConnectedMaterialProperties(Material) == Expected);
	for (EMaterialProperty Property : Properties)
	{
		FExpressionInput* Input = Material->GetExpressionInputForProperty(Property);
		TestTrue(TEXT("inspection preserves the original connection"), Input->Expression == Node && Input->OutputIndex == 0);
	}
	TestTrue(TEXT("null material is handled without a dereference"),
		UDinkMaterialArtLibrary::GetConnectedMaterialProperties(nullptr).IsEmpty());
	return true;
}
#endif
