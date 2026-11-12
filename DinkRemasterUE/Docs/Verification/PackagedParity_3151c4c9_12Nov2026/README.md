# Packaged parity on master 3151c4c9 (12 Nov 2026)

**Result: alpha gate 1 still holds.** The story probe (`Dink.Gameplay.Probe`, twenty chapters covering `&story` 0-16)
passes in the editor (PIE, 22/22) and in a packaged Linux Development build (20/20, one game process per chapter), and the
twenty trace md5s are identical in both runs and identical to the known hashes from the last packaged proof
(master 9758852 / e417231, PR #44/#50; `Plugins/DinkParity/Docs/packaged_probe.md`).

## What was tested

- Commit: `3151c4c9d09d93b97a8d04b6685deb43fdb017ef` (master, 12 Nov 2026 09:05 -0800: hero fixes PR #51/#74/#75, house
  window lights 80 cm PR #77). The shared checkout's tracked files were clean at that commit (`git status` showed only
  untracked files under `SourceAssets/Art/`), and no LFS pointer files were in the tree.
- Work copy: `DinkRemasterUE/Saved/PackagedParity3151/DinkRemasterUE`, a `cp -a --reflink=always` of every top-level entry
  of `DinkRemasterUE/` except `Saved/` (copying the whole folder into its own `Saved/` would recurse into itself), so the copy
  started from an empty `Saved/` (no cooked data, no old traces). The copy is kept in place.
- Machine: Linux 7.2.15, 12 threads, 30 GB RAM, UE 5.8.4. Each heavy step waited until the name-based editor gate
  (`ps -eo comm,args`, AGENTS.md pitfall 81) had read 0 for 20 consecutive seconds and `MemAvailable` was at least 9 GB.
  The build waited about 6 minutes for another session's `Dink.Art` editor run to finish.
- Note: origin/master moved to `cf27f930` (PR #78, the gate-2 backlog doc, `Scripts/gate2_backlog.py` and its test) while this
  ran. That change touches no game code or content, so the result applies to `cf27f930` too. This branch is cut from it.

## Steps and times (all 12 Nov 2026, PST)

| Step | Command (in the work copy) | Started | Result | Time |
|---|---|---|---|---|
| 1 | `Scripts/build.sh` (WAYLAND_DISPLAY/DISPLAY unset) | 09:14:52 | `BUILD OK`, 0 warnings (relink of the copy's editor libraries) | 94 s |
| 2 | `DINK_TEST_RUN=parity_pie DINK_TEST_TIMEOUT=3600 Scripts/test.sh Dink.Gameplay.Probe` | 09:16:56 | `TESTS PASSED: 22/22`, 0 warnings | 651 s |
| 3a | `Scripts/package.sh` | 09:31:51 | `PACKAGE OK`, UAT exit 0, 0 warnings, 6,013 packages cooked (cook 144 s, from empty `Saved/Cooked`), `Dink/Data` staged in `DinkRemaster-Linux.pak`, stage 1.6 GB | 258 s |
| 3b | `DINK_TEST_TIMEOUT=3600 Scripts/run_packaged_tests.sh` | 09:36:09 | `TESTS PASSED`: all twenty chapters, one packaged game process each; twenty `PARITY OK` | 92 s |

## Trace md5s (first 10 hex digits)

PIE traces are the copy's `Saved/Narrative/*probe*_trace.txt` after step 2. Packaged traces are
`Saved/StagedBuilds/Linux/DinkRemaster/Saved/Narrative/` after step 3b. "Known" is the list from the 9 Nov proof.

| Chapter | Test | Trace file | Known | PIE (step 2) | Packaged (step 3b) | PIE time | Packaged time |
|---|---|---|---|---|---|---|---|
| 1 | Ch1Stonebrook | stonebrook_probe_trace.txt | 0ba0ba5b7e | 0ba0ba5b7e | 0ba0ba5b7e | 62.3 s | 10 s |
| 2 | Ch2Terris | probe_ch2_trace.txt | ce04e3bd3b | ce04e3bd3b | ce04e3bd3b | 43.6 s | 7 s |
| 3 | Ch3Roads | probe_ch3_trace.txt | f494822cad | f494822cad | f494822cad | 15.6 s | 2 s |
| 4 | Ch4Gold | probe_ch4_trace.txt | ae86ef33c8 | ae86ef33c8 | ae86ef33c8 | 38.0 s | 8 s |
| 5 | Ch5Bow | probe_ch5_trace.txt | 86794bccac | 86794bccac | 86794bccac | 6.7 s | 1 s |
| 6 | Ch6Goblins | probe_ch6_trace.txt | 8517d2eced | 8517d2eced | 8517d2eced | 6.0 s | 2 s |
| 7 | Ch7Sanctuary | probe_ch7_trace.txt | b5d649bc14 | b5d649bc14 | b5d649bc14 | 46.1 s | 8 s |
| 8 | Ch8Knights | probe_ch8_trace.txt | d4b45b0834 | d4b45b0834 | d4b45b0834 | 19.5 s | 4 s |
| 9 | Ch9Windemere | probe_ch9_trace.txt | 85eeac1fff | 85eeac1fff | 85eeac1fff | 16.6 s | 3 s |
| 10 | ChAJoppa | probe_ch10_trace.txt | 8f29d08d8d | 8f29d08d8d | 8f29d08d8d | 9.8 s | 2 s |
| 11 | ChBKit | probe_ch11_trace.txt | 5a5fa26db2 | 5a5fa26db2 | 5a5fa26db2 | 85.2 s | 15 s |
| 12 | ChCDragons | probe_ch12_trace.txt | fee1bf79a6 | fee1bf79a6 | fee1bf79a6 | 11.1 s | 2 s |
| 13 | ChDCastle | probe_ch13_trace.txt | 0ca00d888f | 0ca00d888f | 0ca00d888f | 9.0 s | 1 s |
| 14 | ChEEdge | probe_ch14_trace.txt | df7e479d7b | df7e479d7b | df7e479d7b | 6.3 s | 2 s |
| 15 | ChFDarklands | probe_ch15_trace.txt | 463bce5fed | 463bce5fed | 463bce5fed | 8.7 s | 2 s |
| 16 | ChGSlayers | probe_ch16_trace.txt | 1604da6d56 | 1604da6d56 | 1604da6d56 | 15.5 s | 3 s |
| 17 | ChHDucks | probe_ch17_trace.txt | dba045baa4 | dba045baa4 | dba045baa4 | 9.3 s | 3 s |
| 18 | ChISeth | probe_ch18_trace.txt | dbfaba7399 | dbfaba7399 | dbfaba7399 | 7.8 s | 2 s |
| 19 | ChJBowLore | probe_ch19_trace.txt | bec655a025 | bec655a025 | bec655a025 | 55.6 s | 10 s |
| 20 | ChKSeth | probe_ch20_trace.txt | 7fdc482332 | 7fdc482332 | 7fdc482332 | 38.0 s | 5 s |

The PIE run's two other tests also passed: `Dink.Gameplay.Probe.Repeatable` (41.3 s) and `Dink.Gameplay.Probe.RepeatableChapter`
(81.8 s). These two are not packaged.

## Anything odd

- Nothing failed or needed a retry. There were no warnings in the build, the PIE run, the package or the packaged run.
- The hero mesh fixes (PR #51, #74, #75) and the 80 cm window lights (PR #77) moved no trace, in PIE or packaged.
- The first cook in a fresh copy took 258 s (an incremental cook in the shared checkout takes 26-76 s). The shader DDC was shared.
- Not checked here: the full `Scripts/test.sh` suite, frame rate, and anything visual. This run only re-proves gate 1.
