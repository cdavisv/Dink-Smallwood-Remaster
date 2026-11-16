# Title screen, save/Continue and the dialogue skip rule, seen in the game (16 Nov 2026)

Branch `feat/title-menu` (bug rows A300-A303). Rendered check in an editor game (`-game`, private Xvfb display, no sound)
started with `-DinkTitle`, so the title, which is never shown under automation, is forced on. Input is real keyboard and
mouse events (XTest), not console shortcuts, except `dink.Goto` (to reach the save machine), `dink.Run` (to start a
known line), `dink.View` and `dink.TimeDilation 0.25` (so a capture lands inside a line). Every sheet was looked at.

## What changed
- Title screen (New Game / Continue / Controls / Quit) over a slow camera at Dink's house, before any script runs.
- Status HUD (level, life, experience, gold, weapon, magic), the world map for `show_bmp`, RB opens the items.
- Skip rule (owner, 15 Nov): while Dink can move freely a line is skipped only by Space or gamepad A; Enter, E, F and the
  click keep their own jobs (items, talk, attack). While Dink is held (`freeze`, `wait_for_button`) Enter, E and the click
  skip too, as in 1997. Movement and attacks follow 1997: free during a line in passing, blocked while frozen.
- Controls page: columns sized to their longest entry (the long action names ran into the keys), the skip rule in two rows.

## Sheets
- `01_title_controls_newgame.jpg`: title with no saves (Continue greyed and skipped by Down), Controls, New Game,
  the intro (Mother's two held lines: Enter skipped the first, Space the second, then Dink is free).
- `02_save_continue.jpg`: SCR_408 save machine: talk opens the choice, slot menu, "Game saved"
  (`Saved/SaveGames/dink_save1.sav` written); relaunch: the title now selects Continue, the Continue page shows
  "Slot 1 - 0:00 - Level 1 - Stonebrook village", and the game loads on SCR_408 at the machine (dink.Player 133.1, 191.9,
  the position saved).
- `03_dialogue_free_line.jpg`: a line in passing (`s1-roc` talk: `say_stop`, no freeze). A left click made Dink swing and
  the line stayed; holding D walked him 7.5 map px (dink.Player 300.0 -> 307.5) with the line still up; Space skipped it.
- `04_dialogue_held_line.jpg`: a held line (`s2-sale` talk: `freeze(1)`, two `say_stop`). dink.Player move_ignored=1,
  holding D for 1.5 s moved him 0 px; the click skipped to the next line; Enter skipped that one; then move_ignored=0.

- `05_dialogue_hint_free_vs_held.jpg` (follow-up commit, run on 84e045b0): the hint on a free line reads "Space", on a held line "Space / Enter / Click".

## Tests and probe
- Targeted: `Dink.Narrative.Title+Dink.Input+Dink.Gameplay.Controls+Dink.Narrative.Presentation+Dink.Audio.InventoryPausesEveryVoice+Dink.Gameplay.Probe`
  50/50 on master 3a7b4451c + branch, world regenerated; all twenty probe trace md5s equal `Plugins/DinkParity/Docs/packaged_probe.md`.
  Final-tree line (master 5d8a4a1f + branch): see the PR.
- The predecessor's full `Dink` suite (303/303) and Python suite (903 OK) ran on 9cc796b6 + branch.

## Not checked
- Gamepad buttons (no pad on the test display); the RB item button and stick in menus are covered by tests only.
- Audio (title music, line voices) was off (`-nosound`).
- The packaged build; the title in a packaged build was not opened.
- The world map picture (`show_bmp`) was not opened in this run (test `Dink.Narrative.Presentation.ShowBmpMap` only).
- Seen in passing, not this branch: pixel-card trees (orange chequered cards) beside the fence on SCR_408 east.
