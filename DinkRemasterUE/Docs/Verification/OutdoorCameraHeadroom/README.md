# Outdoor camera headroom

A Camera-blocking cottage edge retracted the outdoor boom to about 106 cm and clipped Dink’s head. The component adds bounded vertical pivot headroom derived from the actual capsule top, camera basis and projection. It sweeps both pivot and raised boom on the existing Camera channel, preserving the original blocking component and exterior face clearance. Interior framing and the unobstructed 400 cm outdoor arm remain intact.

The tested combined source is `73ccdbe`, including HeroGrowth and the East Wilds booth join (`e417231`). Own Editor and Development Game builds passed; focused camera tests passed 3/3 without warnings on this combined source. Full Dink automation completed all 192 registered tests with zero failures: 160 clean and 32 with warnings, comprising 4,283 HTTP and 18 EOS connectivity messages. All 12,618 protected inputs and own modules remained unchanged. Cache use was warm. See [full-regression.json](full-regression.json).

The latest actual GPU run completed normally in 147.32 seconds: eight screenshots, all 12,634 inputs unchanged, real held-W exit `1 → 439` and return `439 → 1`, scripts enabled and input unlocked. At its exit pose, lift 49.2714 cm puts the capsule top at pixel Y 73.8677/720. Dink’s full head is visible; the same cottage still blocks Camera and sweep prediction error is zero. Interior return and clear outdoor control reset lift to zero; clear outdoor distance remains 400 cm. Owned processes and the private display closed normally. See [gpu-results.json](gpu-results.json) and [screenshot hashes](screenshots.sha256).

![Door exit](door-exit.png)

![Interior return](door-return-settled.png)

![Unobstructed outdoor control](outside-free.png)

Independent source review passed on the exact four camera source-file hashes, unchanged through upstream integration. This is a bounded fix for the default no-lag spring-arm path and measured/native fixtures, not a guarantee for every custom camera trajectory or final photoreal art approval. No actor, warp, input, collision response, art or Data change is included.

Historical evidence remains preserved externally: the earlier fbf-scoped GPU run used 52.1176 cm lift at a different pose, and its successful builds retained a nonfatal cache-store diagnostic; one earlier focused test had 39 HTTP warnings. Current full raw run: `DinkQA/OutdoorCameraHeadroomNativePreparation/Candidate2/Runs/4263fa39322049bd80b611645496cc35`; latest GPU: `DinkQA/OutdoorCameraHeadroomGPUPreparationV2/Runs/566fd899-559a-40e0-9c4a-831349c14346`. These local evidence paths are not runtime dependencies.
