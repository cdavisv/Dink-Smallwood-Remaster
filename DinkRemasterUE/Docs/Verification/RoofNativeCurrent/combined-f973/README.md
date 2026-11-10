# Combined roof and accepted hero verification

Tested source: `f97349ed95b05b81a1f24d117279b97ed152126e`, branch `art/roof-native-current`. These receipts supersede prior-base runtime results only for this combined snapshot; no production assets or code change in this evidence update.

- Own Editor/Game builds passed (34.869/17.139 seconds). Focused wall-clearance test passed.
- Full native suite passed all 195 tests (163 clean, 32 HTTP/EOS warning successes, zero failures/skips; 709.513 seconds). The 4,496 report warning entries were HTTP/EOS; they are retained, not hidden.
- Current Editor game captured 17 screenshots and 23 diagnostic states. Actual held-W travel left screen 1 for 439 and returned to 1; no route teleports. Headroom/camera/input diagnostics reported zero errors. Five representative original captures are included; all 17 raw captures remain in the indexed local run.
- Cook and stage passed. Actual IoStore inventory contains all 23 shared roof packages, 50 retained roof packages and seven maps. Three extracted Art JSON files match current source bytes exactly.
- Packaged CH1 passed one clean test and exactly matched the native trace (SHA256 `20227a637e1b3872c7b82494023a8224225b285462739113e9f3e799524c1d02`).

**Packaged rendered startup is not accepted.** Both actual attempts crashed before any input or screenshot, in the Radeon Vulkan compute-pipeline path. The second attempt proved the early single-worker PSO settings and still crashed, so that hypothesis did not fix it. Both attempts kept all 12,940 measured source/stage inputs unchanged and closed their private displays normally. Core dumps and authentication files are not included. Symbol diagnosis continues; the stack alone does not establish a driver root cause.

The current screenshots also expose generated walls from other interior rooms. A separate `fix/generated-interior-visibility` branch addresses that issue; its first focused test failed at scratch controller registration before reaching visibility assertions, and fixture correction is pending. This evidence does not claim that fix, global barrel collision rollout, new fireplace/exterior native import, final photorealistic art, or whole-game visual coverage is complete. PR45 remains draft pending packaged rendered verification.

`INDEX.json` pins each original receipt/capture. Historical source and roof activation receipts remain unchanged; the accepted hero source changes were qualified with a separate explicit epoch successor rather than relaxing old checks.
