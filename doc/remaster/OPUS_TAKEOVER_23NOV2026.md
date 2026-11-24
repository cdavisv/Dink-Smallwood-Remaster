# Takeover list for Opus agents (written 23 November 2026, evening)

The Fable 5.2 art agents stopped on 23 November 2026 at about 20:00 PT because the week's Fable usage ran out. This file lists
what is left, split by who may do it. The owner's rule stands: **art design, meshes, textures, looks and art review are done only
in Fable 5.2 sessions; code, physics, gameplay, tests, tooling and mechanical work are done by Opus.** An Opus agent may build,
import, test, rebase, scrub and CAPTURE frames of art, but it does not judge whether art is good enough and does not merge an art
PR on its own judgement. Where an item says "frames for Fable", the Opus job ends with a contact sheet (the 1997 picture beside
the game at the play camera and close up) in the PR's evidence folder.

Local paths below are on the owner's machine. `<coord>` is `DinkRemasterUE/Saved/Gate2Coord/` in the shared checkout (git-ignored):
`COMMON_RULES.md` (rules and the Master log; every push or merge gets a dated line at its END), `RESTART_16NOV.md` (binding
rules), `unreal_turn.sh` (every build, import, test and capture goes through it), `gpu_turn.sh`. `<notes>` is
`~/Work/Restart16Nov/`: one folder per stream with `NOTES.md` ending in a HANDOFF section, `RENDER_PENDING.md`, `merge_pr2.sh`,
`merge_master_docs.sh`, `lfs_private_check.sh`.

## State

- Master `4e5fcb4c5`. Sixteen art PRs were merged on 23 November from in-game review: #221, #219, #220, #217, #212, #211, #222,
  #216, #224, #215, #210, #236, #223, #218, #235, #214.
- Open pull requests: #233 invisible blockages (ready, code coordinator's), #229 effect-material warm-up (ready, conflicts with
  master), #213 explosion outline (art draft), #232 bow, arrow and quiver (art draft).
- Rendered Unreal is allowed again since 23 November 11:40 by the owner ("Keep it, risk it"): the memory setting stays at EXPO
  6000. Conditions are at the top of `<notes>/RENDER_PENDING.md`: rendered steps only through `unreal_turn.sh`, work committed
  and notes written before each rendered step, one short capture section at a time, nothing rendered after a kernel Oops until
  a reboot. No kernel fault occurred on 23 November.

## A. Code work raised by the art streams (Opus, now)

Each has a fuller line in the Master log under the date given.

1. **`dink.HurtSprite` and Mog (23 Nov 19:20).** On SCR_680 the command kills only the first of the four goblins; the other
   three log 498/499 damage dealt and stay standing, so `s3-mog` never spawns and Mog's remains (picture 785) cannot be captured.
2. **`Botch_Faceplant` (23 Nov 18:50).** Through the mannerism runtime of #230 the clip ends propped on the fists with the shins
   in the air; the clip itself lies flat (sheet `07` in `Docs/Verification/HeroMannerismClips_23Nov2026/`). A procedural layer on
   top of the clip is the suspect.
3. **A held attack for capture scripts (23 Nov, art-fx-5).** `dink.Attack` is a tap, so a real bow shot (draw held, then
   release) cannot be captured for #232.
4. **Old man keeps his stoop while walking (23 Nov 14:45).** `AN_Stoop_Stand` is an idle clip only; `npc_old_man` uses body set
   NpcM and straightens in the shared walk. Needs a posture row for his body set.
5. **Skeletal LOD screen sizes (23 Nov 14:45).** A C++ dump of the skeletal LOD screen sizes, to settle which LOD the play
   camera shows for the townsfolk (their LOD1 to LOD3 are hair-heavy).
6. **Seth's red cast flash (23 Nov 09:25).** A `CastFlash` scalar hook on his material while he casts; check whether stream
   code-art-hooks already delivered it before starting.
7. **`dink.Goto` under raised ground.** `dink.Goto` onto the bank splat on screen 94 puts Dink and the camera under the
   landforms (README of #224).
8. **`dink.FamilyArt 0` at run time** has no effect on fire cards (README of #215); a capture cannot hide them.
9. **Kit importer stamp (23 Nov 12:22).** The stamp holds the FBX's mtime, so a kit import in another copy re-imports every
   mesh; master's corpse meshes each hold one LOD since the 16 November import (the A200 LODs were lost).
10. **Ground holes, VS-08 (art-gore-4's handoff).** The landforms mesh is one procedural mesh per screen with an opaque
    material: nothing can cut an opening and nothing drapes a mesh. Twenty-five placements (cracks, the pit, cave mouths) wait.
    Either a hole list in `DinkLandforms.cpp` `BuildScreen`, or a decal master with parallax pit code and Specular 0 in the
    importer for a Fable trial. Decide with the code coordinator; the art trial is in section C.
11. **Queue and packaging tools.** `unreal_turn.sh` does not count `RunUAT` under bwrap as a running Unreal step, so lane 2
    stays shut during a packaged run; waiters lose their queue line now and then; the packaged run of 23 November hung on
    "Reading oplog from Zen" with no zenserver running (three attempts failed; see `RENDER_PENDING.md`).
12. **Bring the coordinator's tools into the repository.** `merge_pr2.sh`, `merge_master_docs.sh` and `lfs_private_check.sh`
    live only in `<notes>`. `lfs_private_check.sh` was hardened on 23 November (it unsets `GIT_LFS_SKIP_SMUDGE`, reads inside
    zstd `.blend` files, fails on unread pointers) after three branches went up with the machine's home path while the old
    version said 0 hits. Put them under `tools/` with a CI step that runs the private check on a PR's LFS files.
13. **Sprites parked outside the playfield (SP-08 in `FABLE_ART_QUEUE.md`).** 1997 parks placements outside the 400 px
    playfield; the remaster draws them on the neighbouring screen (the red knight S241_P03 stands inside a pine).

The code coordinator's own list (merged code PRs still to look at in the rendered game, the packaged probe run on the newest
master, #233, #229) is in the second section of `<notes>/RENDER_PENDING.md`.

## B. Mechanical finishing of art work in progress (Opus, now; no art judgement)

For each: fetch, pin `BASE=$(git rev-parse origin/master)`, real LFS files in the worktree (`git lfs checkout`), one clean
commit on master, clean build with 0 warnings, the stream's test filter green, the probe's twenty md5s equal to the table in
`DinkRemasterUE/Plugins/DinkParity/Docs/packaged_probe.md`, scrub, then after the push `lfs_private_check.sh origin/<branch>`
(0 hits) and `tools/lfs_audit.py origin/<branch>` (0 missing). Leave every art PR a DRAFT with "frames for Fable".

| Work | Where | State | Opus job |
|---|---|---|---|
| #213 explosions 161/167/70 | `~/Work/DinkFableG` branch `art/explosion-outline`, local `5ee4477d5` on `55ab3ae8d`, NOT pushed (the PR holds an older commit that conflicts with master); `<notes>/art-fx-5/NOTES.md` | all three caught in game; a thin pale rim on the last dark frames in slow motion; no headless proof | rebase on master (kit manifest by `make_kit_manifest.py`), proof, push, frames for Fable |
| #232 bow, arrow, quiver | same worktree, branch `art/bow-bends-quiver`, local `630bab83f`, NOT pushed | hooked string fingers and quiver straps seen in game; no held shot; no headless proof | rebase, proof, push; capture the shot once A3 exists; frames for Fable |
| Ground burn marks of 533/536 | same worktree, branch `art/ground-burn-marks`, local `27a7c74d3`, no PR | black scorch seen in game in place of the grey slab; no headless proof | rebase, proof, draft PR, frames for Fable |
| Stair pit | integration tree `~/Work/DinkFableD` only | compile fault fixed, then made unlit; the unlit look is unseen (`cap/sec_stairs6.txt` not run) | run that capture, frames for Fable; draft PR only if a flight going down is visible |
| Burn marks on the merged cottage | master | #214's marks never seen on #215's burning roof | capture SCR_439 vision 1 on master, frames for Fable |
| `art/gore-review-fixes` | `~/Work/FableGoreFix`, 3 WIP commits on `55ab3ae8d` | matt outside the blood, soaked pool rim (importer kind `soak`), pleated dragon wing, round cottage hole with ember material: seen in Blender only | clean build of copy `Saved/FableA` first (it holds an overlay without a build), import, tests, captures, frames for Fable |
| `art/gore-q7-rest` | `~/Work/FableQ7Rest`, `47831b460` | pillbug and duck-head rows, not seen | import, capture S098_P04, S100_P25/P26 and a duck screen, frames for Fable |
| Townsfolk 2a (gnome, merchants) | `~/Work/DinkPeople2b` branch `art/people-int8` (everything), `~/Work/DinkPeople7` (sources and docs only: do not push as is) | read as their 1997 pictures in game; brows were black; the brow fix is captured in `CharQA/t2b` (140 frames, unseen) | build the contact sheet from `t2b`, scrub, headless proof, draft PR, frames for Fable |
| Ice set of `gate2-snow-ice` | old branch, 251 commits behind | art-gore-6: worth bringing as art-only files | copy the art-only files onto master as a draft; no C++ from that branch |
| RimFade of `terrain-layers-material` | old branch, second commit (17 lines) | art-gore-6: not made moot by the landforms | rebase as a small draft, capture one terrain edge before and after |

## C. Waits for a Fable 5.2 session (art judgement)

Review of every "frames for Fable" item in section B comes first. Then, by stream; entry points are in the named NOTES files.

**Characters (`<notes>/art-people-7/NOTES.md`, and the HANDOFFs of art-people-3 to -6):**
- Townsfolk 2: the girl (child proportions), the soldier and the silver knight of 408-410.
- Knights: plate edges, wear and straps; the inherited Knight creature class (`~/Work/FableA_Monsters`, copy the knight files,
  do not rebase) against #199's `npc_knight_*` rows.
- Follow-ups from the reviews of merged PRs: the Mother (sunlit back of the head too pale, steps at the temples, face sterner
  than 1997's, pale lips, thin brows, back neckline notch); the maiden (brows a drawn arc, spiky fringe, wide mane cards at one
  metre, rigid hair); Milder (ragged tabard armholes at the back); the countryman's pole free beside his fist; the mannerism
  clips not fully seen (`RunArms_Timid`, `Fidget_Proud`, `Fidget_Nose` from the front, timid cuts with a sword armed).
- Seth second pass; castle interior seams and walls; the church; trees.

**Gore (`<notes>/art-gore-6/NOTES.md`, art-gore-5, art-gore-4):**
- Duck corpse mesh (127), stone giant paler than 821/825, bonca face, slayer skin.
- Mog's remains 785, once A1 is fixed.
- The ground-hole trial (one crack, one cave mouth) once A10 gives it a decal master or an opening.
- AN-03 (corpse materials need skinned-mesh usage) and AN-04 (dragon hand-over).

**Effects and props (`<notes>/art-fx-5/NOTES.md`, art-fx-4, art-fx-2):**
- AN-06 axe throw; the smoke phase of explosions 161/167/70 lit by the scene; char under the roof fires of 439.
- `art/gate2-static-nuttree` (props mounted on counters and walls, the nut tree), every mesh looked at.
- The list of #194: scripted pines (burnt-pine mesh and a burning phase), a single gold coin, brick fireplaces for screens
  38/129/163, signs.
- The gold heart about 1.2 m across beside the knight on screen 157: check its size against the 1997 pickup.

The whole art backlog by family is `ALPHA_GATE2_BACKLOG.md`; the row-by-row queue is `FABLE_ART_QUEUE.md`.

## D. Waits for the owner

- **Burnt interior of Dink's room (screen 1 after the fire).** 1997 changes nothing in the room but the burn holes; a soot line
  on the walls and ash on the floor would go beyond the original. Not built without a yes.
- **World scale (#161, merged with its switch off).** Turning it on changes screen shapes (`WORLD_SCALE.md`, sections 11, 12).
- **The 1997 `rand()%2` hurt-sound draw** (raised by the code sessions).

## Rules that bit on 23 November

- A "ready" line in the Master log wakes nobody. An agent that needs a merge or a decision messages the coordinator.
- Run the privacy check on `origin/<branch>` AFTER the push, with real LFS files in the worktree. After a rebase in a
  skip-smudge worktree the LFS files are pointers; the scrub skips pointers and says clean without reading anything.
- Do not point `TMPDIR` into a scratch folder under the home directory before an import or export: the path lands in the asset.
- A script that reports "merged" must ask GitHub for the PR's state; `merge_pr.sh` printed a false line once (`merge_pr2.sh`
  does not).
- Merge branches into an integration tree; laying one branch's `environment.json` over another's silently drops rows.
- Judge blood and pale albedo colours only in the game: in the sun red above sRGB 100 clips to poster red.
- Never kill by pattern or by `kill $(pgrep ...)`: three agents killed their own shells that way.
- When a look in the game is wrong, put the frame beside the 1997 picture first: the "blocky decal" of #214 was the 1997
  picture itself, shown again on its card.
