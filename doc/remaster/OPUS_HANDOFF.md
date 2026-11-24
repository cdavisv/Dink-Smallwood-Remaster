# Opus handoff (written 23 Nov 2026, coordinator session f3713b19)

The owner stopped work for the week on 23 Nov 2026 and asked for this list so Opus agents can take over.
Code, merges, probe and tests are Opus work. Art design is Fable 5.2 only (owner rule); the art coordinator
is a separate session (e8f64224) and owns the art PRs.

Read before starting: `AGENTS.md`, `doc/remaster/ALPHA_BUG_LIST.md`, `doc/remaster/PHYSICAL_PLAY_LAYER.md`,
`doc/remaster/WORLD_SCALE.md`, and the Master log `DinkRemasterUE/Saved/Gate2Coord/COMMON_RULES.md`
(local, not in git). Each stream's notes are under `~/Work/Restart16Nov/<stream>/NOTES.md`.

## Rules that still hold

- **Probe gate:** the layer-off probe's 20 chapter md5s must equal the newest table in
  `Plugins/DinkParity/Docs/packaged_probe.md` (A41 table, Ch1 cff64df9d1 ... Ch20 b27010b31e).
  - The only planned exception is the world-scale re-baseline below.
  - The layer-on chained probe (Mode=2 bot) must finish 20/20 chapters.
- **Merge gates:** clean build with 0 warnings, full `Dink` suite, `Dink.PhysicalPlay`, both probes,
  Python suite, private-path scrub, LFS checks and CI source-audit.
  - `Dink.Movement.Landforms.ScriptedMoveAcrossRelief` is known to fail under load; rerun it on its own.
- **Kernel check:** run `journalctl -k -b | grep -iE 'oops|BUG:'` before every push. It must be clean.
- **Merging:** merge only with `~/Work/Restart16Nov/merge_pr.sh <pr>`.
  - Commits carry no Co-Authored-By or other attribution lines.
  - PR bodies end with the Claude Code line.
- **Hits:** the hit rule is drawn contact for both Dink and the monsters (#160). The layer-off probe keeps the 1997 rule.
- **Gore:** keep all original gore. Never sanitise.
- **Rendered Unreal:** allowed on EXPO 6000 at the owner's risk (23 Nov). Every rendered step goes only through
  `DinkRemasterUE/Saved/Gate2Coord/unreal_turn.sh`.
  - Commit WIP and update notes first.
  - Keep runs short (15 min or less).
  - After any Oops, stop until reboot.
  - Rendered checks live in `~/Work/Restart16Nov/RENDER_PENDING.md`.
- **Copies:** each agent works in its own reflink copy under `DinkRemasterUE/Saved/`.
  - Run `rm -rf Content/Dink/_Generated` before `import_greybox.sh --region all`.
  - Headless runs use `-nullrhi`.

## Task list, in order

1. **Merge PR #233 (invisible blockages: A71 interior walls, A92 painted rocks, A20 pond teleport, A354 King's body).**
   - Every gate passed except the layer-on chained probe (19/20: ch20 Seth bow duel).
   - Agent blockages-6 had a fix giving layer-on 20/20 and was running the last gates at the stop.
   - Read `~/Work/Restart16Nov/blockages-6/NOTES.md`, confirm every gate on the pushed head, then merge.
   - Then look at its rendered frames in `~/Work/Restart16Nov/blockages-5/render/`:
     - the walls, rocks and King walks;
     - the A94 shore walks;
     - the A62/A61/A354 camera.
   - Move those `RENDER_PENDING.md` lines to Done.
   - Propose (don't ship) an A62 camera change if the frames need one.
2. **Turn the enlarged world on** (owner decision 23 Nov: "Yes, approved ratios").
   - This is option A: the approved per-kind ratios, ONE deliberate re-baseline of the md5 table, and a bot re-tune
     at ch8 step 1 (layer off) and ch12 step 3 (layer on, two dragons on SCR_419). The 1997 rules stay unchanged.
   - Why a re-baseline: the md5 change comes from sub-pixel readback rounding of Dink's position, not from the
     rules (WORLD_SCALE.md s13, on branch `world-scale/option-b`).
   - Option B (one ratio for every kind) was tested and rejected.
   - Agent world-scale-4, branch `world-scale/enable` (draft PR if pushed); notes in `~/Work/Restart16Nov/world-scale-4/`.
   - Done: switch on, import, PhysAudit, relaxed hardbox list (506 boxes on 262 screens).
   - Left:
     - bot stops;
     - full gates;
     - the new md5 table, taken AFTER #233 merges, from two identical runs and documented in `packaged_probe.md`;
     - rendered before/after captures and `dink.WalkAudit`.
3. **Packaged probe run on the newest master.** It has never run. `package.sh` refuses while any other
   UnrealEditor-Cmd runs.
   - Book a window with the art coordinator through the Master log and write PACKAGED RUN START/END lines.
   - Start and check zenserver first: a run hung on a missing zenserver.
   - `unreal_turn.sh` does not count RunUAT under bwrap.
4. **PR #229 (effect material warm-up, the white card).** The rendered check was inconclusive: the shared DDC at
   `~/.config/Epic/UnrealEngine/Common/DerivedDataCache` was warm.
   - Rerun with an isolated, empty DDC.
   - Merge if the burst never shows a white or grey card.
5. **#230 mannerisms rendered look.** It waits for art PR #218's clips (Fable side).
6. **Rendered lines still pending** for the code side in `RENDER_PENDING.md`:
   - #200 packaged before/after route;
   - the A66 talk to the mother in a real game (only proven by the PIE test);
   - `dink.Goto` into SCR_001 and Terris 530 from outdoors silently does nothing. Investigate.
7. **Owner questions still open:**
   - the `rand()%2` hurt sound;
   - code-art-hooks item 7 (interior state swap).

   Ask the owner. Don't decide these.

## Not this list's job

Art drafts (#213, #232 and the others) and art rows belong to the Fable 5.2 art coordinator.
Code hooks the art asks for go to Opus as separate PRs (see the `code-art-hooks` notes for the pattern).
