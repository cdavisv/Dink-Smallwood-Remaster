#include "DinkTestHelpers.h"
#include "DinkOriginId.h"
#include "DinkOriginComponent.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkOriginIdFormatTest, "Dink.Core.OriginId.Format", DINK_TEST_FLAGS)
bool FDinkOriginIdFormatTest::RunTest(const FString& Parameters)
{
	TestEqual(TEXT("S412_P03"), FDinkOriginId(412, 3).ToString(), FString(TEXT("S412_P03")));
	TestEqual(TEXT("lowest"), FDinkOriginId(1, 1).ToString(), FString(TEXT("S001_P01")));
	TestEqual(TEXT("highest"), FDinkOriginId(768, 99).ToString(), FString(TEXT("S768_P99")));
	TestEqual(TEXT("invalid formats as None"), FDinkOriginId().ToString(), FString(TEXT("None")));
	TestEqual(TEXT("screen 769 is invalid"), FDinkOriginId(769, 1).ToString(), FString(TEXT("None")));
	TestFalse(TEXT("placement 0 invalid"), FDinkOriginId(1, 0).IsValid());
	TestFalse(TEXT("placement 100 invalid"), FDinkOriginId(1, 100).IsValid());
	TestTrue(TEXT("S412_P03 valid"), FDinkOriginId(412, 3).IsValid());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkOriginIdParseTest, "Dink.Core.OriginId.Parse", DINK_TEST_FLAGS)
bool FDinkOriginIdParseTest::RunTest(const FString& Parameters)
{
	FDinkOriginId Id;
	TestTrue(TEXT("parse S412_P03"), FDinkOriginId::Parse(TEXT("S412_P03"), Id));
	TestEqual(TEXT("screen"), Id.Screen, 412);
	TestEqual(TEXT("placement"), Id.Placement, 3);

	TestTrue(TEXT("lower case accepted"), FDinkOriginId::Parse(TEXT("s001_p01"), Id));
	TestTrue(TEXT("lower case value"), Id == FDinkOriginId(1, 1));

	TestTrue(TEXT("unpadded accepted"), FDinkOriginId::Parse(TEXT("S7_P3"), Id));
	TestTrue(TEXT("unpadded value"), Id == FDinkOriginId(7, 3));

	TestTrue(TEXT("3-digit placement accepted"), FDinkOriginId::Parse(TEXT("S768_P099"), Id));
	TestTrue(TEXT("3-digit placement value"), Id == FDinkOriginId(768, 99));

	const TCHAR* Bad[] = {
		TEXT(""), TEXT("S412"), TEXT("S412_"), TEXT("S412_P"), TEXT("412_P03"), TEXT("S0_P01"), TEXT("S769_P01"),
		TEXT("S412_P00"), TEXT("S412_P100"), TEXT("S412-P03"), TEXT("S412_P03x"), TEXT(" S412_P03"),
		TEXT("S412_P03 "), TEXT("S1234_P01"), TEXT("SX_P1"), TEXT("S12_Q01"), TEXT("S-12_P01"), TEXT("SCR_412")
	};
	const FDinkOriginId Sentinel(5, 5);
	for (const TCHAR* Text : Bad)
	{
		FDinkOriginId Out = Sentinel;
		TestFalse(FString::Printf(TEXT("rejects '%s'"), Text), FDinkOriginId::Parse(Text, Out));
		TestTrue(FString::Printf(TEXT("'%s' leaves output untouched"), Text), Out == Sentinel);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkOriginIdRoundTripTest, "Dink.Core.OriginId.RoundTripAndHash", DINK_TEST_FLAGS)
bool FDinkOriginIdRoundTripTest::RunTest(const FString& Parameters)
{
	TSet<FDinkOriginId> Seen;
	int32 Failures = 0;
	for (int32 Screen = FDinkOriginId::MinScreen; Screen <= FDinkOriginId::MaxScreen; ++Screen)
	{
		for (int32 Placement : { 1, 9, 10, 50, 99 })
		{
			const FDinkOriginId Id(Screen, Placement);
			FDinkOriginId Parsed;
			if (!FDinkOriginId::Parse(Id.ToString(), Parsed) || Parsed != Id)
			{
				++Failures;
			}
			Seen.Add(Id);
			Seen.Add(Parsed);
		}
	}
	TestEqual(TEXT("every ID survives format -> parse"), Failures, 0);
	TestEqual(TEXT("hash/equality: one set entry per ID"), Seen.Num(), 768 * 5);

	TestTrue(TEXT("ordering by screen first"), FDinkOriginId(2, 99) < FDinkOriginId(3, 1));
	TestTrue(TEXT("then by placement"), FDinkOriginId(3, 1) < FDinkOriginId(3, 2));

	UDinkOriginComponent* Component = NewObject<UDinkOriginComponent>(GetTransientPackage());
	Component->OriginId = FDinkOriginId(412, 3);
	TestEqual(TEXT("component string"), Component->GetOriginString(), FString(TEXT("S412_P03")));
	TestNull(TEXT("FindOnActor(nullptr)"), UDinkOriginComponent::FindOnActor(nullptr));
	return true;
}
