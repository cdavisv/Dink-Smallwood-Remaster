# Clumsier Dink movement

Dink now walks and runs with uneven shoulder sway and a deeper drooping stance. His torso lags when he starts or rounds a corner, then pitches into an awkward stop. A stumble dips further and makes two uncoordinated corrections before settling. Jumping during recovery cancels the grounded catch-step immediately.

Player acceleration is 900 cm/s², braking is 850 cm/s², and turn rate is 300°/s. Default running remains 600 cm/s; holding Left Shift walks at 200 cm/s. The existing low hop remains 280 cm/s with gravity 1.45 and an 80 ms hold cap. Eligible landings have a 45% cosmetic stumble chance, 850 ms recovery, and 1.8 s cooldown. Its private seeded random stream stays separate from gameplay randomness.

The player mesh layer is bounded to pitch −20..6°, roll ±9°, yaw ±8°, and a 12 cm offset magnitude, in addition to shared secondary motion. It does not drive the capsule or lock controls. The optional authored posture replaces only the baseline −2.4° pitch. Shared NPC dynamics, clips, and rig assets are unchanged; this delivery does not establish acceptance of the separate new hero/art work.

Validation receipts are in this folder; raw runs remain under `Saved/ClumsyV2` in `/home/davisc/Work/DinkClumsyV2/DinkRemasterUE`:

- Independent source review finds no material blockers; all four reviewed source hashes match the compiled/tested files.
- Native movement checks pass 7/7 without warnings, including real input during landing recovery, transition resets, frame-rate bounds, and capsule stability.
- Before the PR28 reconciliation, the full native suite passes 164/164 in 1857.30 s, including 3 tests with warnings (five HTTP connectivity-check timeouts). All 11,720 recorded inputs remain unchanged and all seven custom editor modules resolve to this checkout.
- Editor and standalone Development Game builds pass with zero compiler warnings. The Game build retains all seven editor module hashes. UBA cache-store notes remain in the build logs.
- All 490 Python checks and the full source audit pass. The first audit overlapped deliberately invalid temporary Python unittest fixtures; that failure is retained and the sequential audit passed after test cleanup.
- A private 45 FPS game run used real Left Shift/W, W, diagonal movement, and Space inputs. Telemetry reached 200/600 cm/s, observed a 33.91 cm hop and 3.00 cm landing mesh dip, with 0.00 cm grounded XY capsule drift. One landing fixture used chance 1, then the normal .45 setting was restored by console; this is not a frequency estimate. Twelve PNGs and frame samples remain in the raw render folder. The owned game closed normally with all 11,720 pinned inputs unchanged, and the preexisting private display was preserved.

Render limitations: the first helper refused input because it expected seven editor modules; game mode correctly loads five owned runtime modules. An initial snake-case property read failed before the observer started; using the native reflected `LandingStumbleChance` property succeeded. Both failures remain in raw logs. The action receipt was overwritten per helper invocation and retains the final quit commands only; the phase-labelled frame telemetry spans the movement and landing checks. Frame sampling and screenshots are bounded evidence on the existing hero, not a new skeleton, cloth, all-angle camera, or outdoor-art review. Fixture setup used console placement/camera commands; locomotion and jumps used actual keys.

Teleport cancellation retains the existing 200 cm observed-displacement heuristic. The previous 144-test delivery is historical evidence in the sibling `ClumsyDink` folder and does not prove this stronger iteration. Final verification documentation is written after the native/render input snapshots; source/runtime files retain their tested hashes.

PR28 integration: preserved the new read-only editor inspection APIs and both handoff records. The combined Editor and Development Game builds pass without compiler warnings; movement7/7 and inspector2/2 checks pass without warnings, with all11,735 recorded inputs unchanged and all seven custom editor DLLs owned. All four reviewed movement source hashes remain exact. `integration_results.json` records the reconciled build. The earlier full164 and GPU receipts precede this reconciliation; a combined full166/GPU rerun is not claimed.
