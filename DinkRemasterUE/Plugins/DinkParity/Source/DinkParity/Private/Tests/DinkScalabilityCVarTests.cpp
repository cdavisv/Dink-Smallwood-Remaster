// Dink.Config.ScalabilityCVars: every dink.* variable that Config/DefaultScalability.ini sets must carry ECVF_Scalability; the
// engine ignores any other (and raises an ensure: "Scalability.ini can only set ECVF_Scalability console variables
// ('dink.GrassDensity'='1.0' is ignored)", seen at every start of the packaged game, playthrough QA 15 Nov 2026).
#include "DinkTestHelpers.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDinkScalabilityCVarTest, "Dink.Config.ScalabilityCVars", DINK_TEST_FLAGS)
bool FDinkScalabilityCVarTest::RunTest(const FString&)
{
	TArray<FString> Lines;
	if (!TestTrue(TEXT("DefaultScalability.ini reads"), FFileHelper::LoadFileToStringArray(Lines, *(FPaths::ProjectConfigDir() / TEXT("DefaultScalability.ini"))))) return false;
	TSet<FString> Names;
	for (const FString& Line : Lines)
	{
		FString Name, Value;
		if (Line.StartsWith(TEXT("dink.")) && Line.Split(TEXT("="), &Name, &Value)) Names.Add(Name.TrimStartAndEnd());
	}
	TestTrue(TEXT("the ini sets at least one dink.* variable"), Names.Num() > 0);
	for (const FString& Name : Names)
	{
		IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(*Name);
		if (!TestNotNull(*FString::Printf(TEXT("%s exists"), *Name), Var)) continue;
		TestTrue(*FString::Printf(TEXT("%s is a scalability variable"), *Name), (Var->GetFlags() & ECVF_Scalability) != 0);
	}
	return true;
}
