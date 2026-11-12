# Movement work handoff

Updated 8 November 2026. This is the original movement authoring checkout, not the active art delivery checkout.

## Delivery state

- Original checkout: `<HOME>/Work/DinkPhotorealVisualQA`, branch `fix/photoreal-visual-qa`, base `067b3cb`. Its uncommitted changes include already delivered movement work and unrelated art-direction memory. Preserve them; do not reset, clean, or treat them as unpublished new work.
- Third-person controls were reviewed and merged in PR #9, merge `e53cae950e0748ff1c72b4111767e07eca7d34b0`.
- Clumsy Dink was reviewed and merged in PR #10, merge `3b5653c4f396983b14efd82a5439ff915ea89745`. CI passed on its exact head.
- Current inspected integrated checkout: `<HOME>/Work/DinkPhotorealArtIntegration`, branch `art/photoreal-props-native`, head `7a22c2f608e4d848d823eb7870442eadf8c3618a`. Another session owns that checkout and combined lighting work. Do not modify its sources, rebuild its loaded modules, or assume a GPU lease.
- On continuation, all five clumsy-Dink delivered files match this integrated checkout byte for byte. Receipt: `Saved/ClumsyDink/continuation-audit.json`.

## Implemented behavior

Default run 600 cm/s; hold Shift walks at 200 cm/s; Space makes a small variable-height hop; wheel zooms. Q casts spells. Dialogue Space confirmation takes priority. Gamepad controls are documented in README.

Dink alone has an uneven shuffle, slight hunch, shoulder sway, slower acceleration/braking/turning, and a roughly 45 cm hop instead of the earlier 108 cm jump. Eligible landings have a private cosmetic 30% stumble roll, 700 ms recovery and 1.6 s cooldown. No forced capsule movement or input lock. NPC shared movement and combat/story randomness are preserved.

## Verification and evidence

- Clumsy final build passed with zero compiler warnings.
- Focused movement tests: 5/5, zero warnings, 18 seconds.
- Full native suite: 144/144, zero warnings, 458 seconds. Report: `Saved/Automation/clumsy_dink_all/index.html`.
- All 8,902 pre-run source/runtime/content/module pins remained unchanged after that full run.
- Delivery packet: `Saved/ClumsyDink/{clumsy-dink.patch,delivery.json,input-pins.json,final-verification.json}`. Frozen patch targets PR #9 merge; SHA256 `fe9d8761c2ba7482519bd725d1add7ddf6e82598e7f5e9fe6c3ddb45ec0ae0c4`.
- Actual private rendered input: 1,126 frames, 45.2 cm hop, one forced and one normal-chance stumble. `Saved/ClumsyDink/visual/{motion.json,summary.json,stumble.png}`.
- Root-motion qualification: 55 grounded stationary samples have zero 3D capsule drift. A later actual Space jump during recovery raises the capsule; zero displacement is not claimed throughout the entire recovery window. Recovery leaves input available.
- Authoring GPU game 67559 and Xvfb 67553 closed normally and the lease was released. Later root-session leases are separate; re-coordinate before launching a renderer.
- Current published evidence is also in the integrated project's `Docs/Verification/{MovementControls,ClumsyDink}`. The combined furniture integration subsequently passed 147 native checks, per its AGENTS.md; that is a separate integration run.

## Remaining work

Continuation validation: standalone `DinkRemaster Linux Development` target builds successfully in39.33seconds,82actions,zero compiler warnings. No runtime source changes were made. Log/receipt: `Saved/ClumsyDink/{game-build.log,game-build-verification.json}`. This verifies game-target compilation only; cooking and packaged input remain pending.

The requested implementation and publication are complete. Useful next validation is wider-world jump/ledge traversal, packaged-game controls, and rendered moving-stumble/low-frame-rate behavior. No general traversal or packaged acceptance has been established. Combined house lighting and wardrobe polish belong to the separate art session.

The user said "continue" on this resumption. Current files were verified and a choice of broader movement playtesting, stronger clumsy animation, or continuing house visual polish was requested asynchronously. Until clarified, preserve the delivered tuning and avoid duplicating the art session's active work.

## Live owner playtest

On8Nov2026 at19:30UTC, owner requested a visible game launch. OriginalQA UnrealEditor `-game` PID153304 is running on the normal Wayland desktop with audio,45FPS cap and serial RHI/Vulkan submission. Its specific window was verified visible/input-capable and focused. Receipt/log: `Saved/ClumsyDink/host-test/{launch.json,game.log}`. This is the verified clumsy movement build with its existing art, not the latest furniture/lighting integration stage. Do not rebuild or replace this checkout’s loaded modules/assets while the owner is testing. No other game/display was signaled. Recheck PID rather than assuming it stays alive.
