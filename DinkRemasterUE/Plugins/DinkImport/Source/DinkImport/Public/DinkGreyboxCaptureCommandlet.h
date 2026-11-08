#pragma once

#include "CoreMinimal.h"
#include "Commandlets/Commandlet.h"
#include "DinkGreyboxCaptureCommandlet.generated.h"

/**
 * Renders evidence images of a generated greybox map without a display (needs a GPU RHI, so run
 * with -AllowCommandletRendering and WITHOUT -nullrhi; Scripts/capture_greybox.sh does):
 *
 *   UnrealEditor-Cmd <project> -run=DinkGreyboxCapture -Region=stonebrook [-Out=<dir>] -AllowCommandletRendering
 *
 * Writes <Out>/<region>_top.png (orthographic, north up, the region's outdoor screens) and
 * <Out>/<region>_eye_<n>.png (perspective at eye height from a few screen centres, looking north).
 *
 * STATUS (6 Nov 2026): DOES NOT WORK YET. The Vulkan RHI starts and shaders compile (about 2 min
 * the first time), but USceneCaptureComponent2D::CaptureScene never draws in a commandlet: the
 * render target keeps its red clear colour, and the commandlet now fails with that message.
 * Next thing to try: run inside the full editor (-ExecCmds) or tick the engine between captures.
 */
UCLASS()
class UDinkGreyboxCaptureCommandlet : public UCommandlet
{
	GENERATED_BODY()

public:
	UDinkGreyboxCaptureCommandlet();
	virtual int32 Main(const FString& Params) override;
};
