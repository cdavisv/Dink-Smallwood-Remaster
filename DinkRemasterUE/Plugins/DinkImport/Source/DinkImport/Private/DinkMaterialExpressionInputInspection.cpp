#include "DinkMaterialArtLibrary.h"
#include "Materials/MaterialExpression.h"
#include "MaterialExpressionIO.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

FString UDinkMaterialArtLibrary::InspectMaterialExpressionInputs(UMaterialExpression* Expression)
{
    const TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetStringField(TEXT("schema"), TEXT("dink-expression-inputs/1"));
    Root->SetBoolField(TEXT("valid"), Expression != nullptr);
    TArray<TSharedPtr<FJsonValue>> Inputs;
    if (Expression)
    {
        Root->SetStringField(TEXT("expression"), Expression->GetPathName());
        for (FExpressionInputIterator It{Expression}; It; ++It)
        {
            const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
            Row->SetNumberField(TEXT("input_index"), It.Index);
            Row->SetStringField(TEXT("input_name"), Expression->GetInputName(It.Index).ToString());
            Row->SetStringField(TEXT("source"), It.Input->Expression ? It.Input->Expression->GetPathName() : FString());
            Row->SetNumberField(TEXT("output_index"), It.Input->OutputIndex);
            Inputs.Add(MakeShared<FJsonValueObject>(Row));
        }
    }
    Root->SetArrayField(TEXT("inputs"), Inputs);
    FString Result;
    FJsonSerializer::Serialize(Root, TJsonWriterFactory<>::Create(&Result));
    return Result;
}

#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Materials/MaterialExpressionAdd.h"
#include "Materials/MaterialExpressionVertexColor.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkExpressionInputInspectionTest,
    "Dink.Art.MaterialExpressionInputInspection",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
bool FDinkExpressionInputInspectionTest::RunTest(const FString& Parameters)
{
    auto Parse = [](const FString& Text)
    {
        TSharedPtr<FJsonObject> Data;
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Data);
        return Data;
    };
    const auto Null = Parse(UDinkMaterialArtLibrary::InspectMaterialExpressionInputs(nullptr));
    if (!TestTrue(TEXT("Null is rejected"), Null.IsValid() && !Null->GetBoolField(TEXT("valid")))) return false;
    UMaterialExpressionVertexColor* Source = NewObject<UMaterialExpressionVertexColor>(GetTransientPackage());
    UMaterialExpressionAdd* Target = NewObject<UMaterialExpressionAdd>(GetTransientPackage());
    Target->A.Connect(0, Source);
    Target->B.Connect(4, Source);
    const bool DirtyBefore = Target->GetOutermost()->IsDirty();
    const FString Before = UDinkMaterialArtLibrary::InspectMaterialExpressionInputs(Target);
    const auto Data = Parse(Before);
    if (!TestTrue(TEXT("Live scratch snapshot valid"), Data.IsValid() && Data->GetBoolField(TEXT("valid")))) return false;
    const auto& Rows = Data->GetArrayField(TEXT("inputs"));
    if (!TestEqual(TEXT("Both Add inputs read"), Rows.Num(), 2)) return false;
    TestEqual(TEXT("A source output RGB index"), Rows[0]->AsObject()->GetNumberField(TEXT("output_index")), 0.0);
    TestEqual(TEXT("B same source alpha index"), Rows[1]->AsObject()->GetNumberField(TEXT("output_index")), 4.0);
    TestEqual(TEXT("Both inputs retain same source"), Rows[0]->AsObject()->GetStringField(TEXT("source")), Rows[1]->AsObject()->GetStringField(TEXT("source")));
    Data->SetBoolField(TEXT("valid"), false);
    TestEqual(TEXT("Detached edits preserve live inputs"), UDinkMaterialArtLibrary::InspectMaterialExpressionInputs(Target), Before);
    TestEqual(TEXT("Reader preserves dirty state"), Target->GetOutermost()->IsDirty(), DirtyBefore);
    return true;
}
#endif
