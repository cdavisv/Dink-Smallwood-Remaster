# Photoreal feed sack native verification

The original S001_P52 grain pickup now uses the reviewed Blender feed sack. Exactly two mesh strings change: its asset row and placement. Scripts, transforms, the decorative woven basket and all other scene data remain unchanged. Six new packages contain one 19,644-triangle mesh, two materials and three shared 2048 BC/N/ORM textures.

The mesh retains the original 72.283 × 55.469 × 75 cm bounds and complex-as-simple collision policy. The original offset 65 × 52 × 75 cm UCX hull is retained and verified, but it is not the active query geometry. Source art remains the immutable PR17 bundle with distinct SourceCheckpoint and ExportIteration manifests.

Native preflight, import and independent saved verification exit successfully in 19.260, 47.193 and 36.385 seconds. All oriented geometry, UVs and triangle-material assignments match: 14,852 jute faces and 4,792 cord faces, with maximum position error 0.000003815 cm and UV error 0.00000002981. A read-only C++ bridge resolves imported material names through actual static slots, including sparse polygon-group IDs. Texture.Source pixels, native source filenames, hidden material inputs and scalar getters are checked. Normal evidence combines source normals, imported-normal/Mikk tangent settings and native geometric fronts; it does not claim an unavailable Python stored-normal getter.

| Material | Source IOR / IOR level | Intended UE specular | Actual native getter |
|---|---|---|---|
| Jute | 1.46 / 0.22 | 0.19231277678630443 | 0.19231277704238892 |
| Cord | 1.5 / 0.22 | 0.22 | 0.2199999988079071 |

These values reproduce normal-incidence F0 targets, not complete Blender/Unreal BRDF identity.

Full native tests pass **152/152 with zero test warnings** in 517.259 seconds. All 9,240 inputs remain unchanged through that run; 40 inventoried older root Saved slots retain their bytes, and ten new probes use an isolated directory. All 490 Python tests pass. The checkpoint source audit verifies 2,117 binaries, 379 Python files, 22 shell files and 1,664 ledger rows without errors or secret flags. The prior 1,658 ledger rows and 483 audio rows retain their raw bytes. Six candidate native rows are appended; their historical pre-gameplay notes remain unchanged, with current results recorded here.

Fresh published-state verification exits successfully in 38.262 seconds without a private author import receipt. Publisher default and `--apply` both write nothing across 9,256 declared inputs. These checks do not grant scene approval. Native import logs retain environment warnings; the zero-warning claim applies to the automation report.

Real keyboard tests pass pickup, traversal through the removed sack, doorway exit/return and the original feeding scene. A 200 ms W touch grants exactly one feed item. Further W movement reaches map 450.631/128.758 while the sack remains hidden and collision disabled. Real F runs the original item-pig.use and s1-bul scripts, sets pig_story to 1 and restores movement. Loading the earlier pickup save through the real native SaveSubsystem API restores screen 1, one feed item, hidden sack and pig_story 0. Save bytes remain unchanged. This tests the save/load API, not the save-machine UI.

The initial pickup setup is an explicit teleport to 423/130. Subsequent routes and feeding use actual keys; fixtures do not assign quest facts, grant items or invoke story procedures. Two shortened re-exit attempts fail while still within the arrival trigger. Walking clear and re-entering succeeds. This exposed an existing doorway overlap bug being fixed separately. The original route driver also exhausts its 35-attempt budget near map 53.644 toward 50 while Dink is still moving. Same-game continuation with 100 attempts and maximum 0.8-second W holds passes. The production helper now matches that tested route function after normalizing its owned data path. This Python-only helper update follows full152; C++, native packages, import tools and ledger still match that full run. The 490 Python tests are rerun afterward.

Both private sessions close normally, with all 6,931 runtime inputs unchanged in each. The fresh photo session confirms one visible native sack at the original transform with both intended materials. Default-corner screenshots remain dark. A separately labeled temporary inspection light makes the folds, seam, cord and material readable; its original transform, intensity and radius are restored before shutdown. This is not approval of default room lighting or final house art. Hero, roof, canonical exterior and overall lighting remain unfinished.

Runtime and Visual retain raw failures, successful continuations, state readback and selected screenshots. HistoricalDrivers are captured text with historical PIDs and absolute paths; re-establish ownership before adapting them. An initial read-only snapshot used an unavailable transform getter, corrected to the installed get_world_transform. A deferred-spawn API was also absent from installed Python and created no actor; the diagnostic instead used an existing owned light. These fixture failures are preserved.

Independent reviews cover the bridge, tools, native packages, published state and final delivery scope. Receipts retain their historical scope and exact input hashes. The full-run ledger prefix was commit 9cf4558, before the later candidate commit. Do not substitute historical private source paths for the selected portable bundle.
