#include "Modules/ModuleManager.h"
#include "Editor.h"
#include "Editor/EditorEngine.h"

// Tests register themselves through IMPLEMENT_SIMPLE_AUTOMATION_TEST in Private/Tests.

DEFINE_LOG_CATEGORY_STATIC(LogDinkParity, Log, All);

// Works around an engine shutdown-order crash (UE 5.8.4): if the editor exits while Play-In-Editor is
// still running (e.g. a headless automation run is interrupted by SIGINT/SIGTERM or Quit mid-test),
// UEditorEngine::PreExit deinitializes the editor subsystems first, and the PIE world is only ended
// later, when Slate destroys the level viewport. EndPlayMap() then calls
// GetEditorSubsystem<UAssetEditorSubsystem>(), which is null by then -> SIGSEGV at 0x60.
// OnEditorPreExit fires just before GEngine->PreExit(), so ending PIE here keeps the normal order.
class FDinkParityModule : public FDefaultModuleImpl
{
public:
	virtual void StartupModule() override
	{
		PreExitHandle = FEditorDelegates::OnEditorPreExit.AddLambda([]()
		{
			if (GEditor && GEditor->PlayWorld)
			{
				UE_LOG(LogDinkParity, Display, TEXT("Editor exiting with PIE still running; ending PIE before editor subsystems shut down."));
				GEditor->EndPlayMap();
			}
		});
	}

	virtual void ShutdownModule() override
	{
		FEditorDelegates::OnEditorPreExit.Remove(PreExitHandle);
	}

private:
	FDelegateHandle PreExitHandle;
};

IMPLEMENT_MODULE(FDinkParityModule, DinkParity)
